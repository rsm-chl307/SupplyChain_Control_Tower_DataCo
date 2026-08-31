"""Lightweight end-to-end Scenario Planning runner.

This module orchestrates the completed Stage 2–5 in-memory components. It
owns file I/O at the boundary and writes each run beneath a run-specific
directory so approved historical artifacts are not overwritten.
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.allocation_manager import run_allocation
from src.performance_manager import evaluate_allocation
from src.planning_pipeline import PlanningPipelineError, run_planning_pipeline
from src.scenario_generator import generate_scenarios


class PlanningRunError(ValueError):
    """Raised when the end-to-end run configuration is invalid."""


def _run_dates(start: object, end: object) -> tuple[pd.Timestamp, pd.Timestamp]:
    if start is None or end is None:
        raise PlanningRunError("planning_start_week and planning_end_week are required")
    try:
        parsed_start = pd.Timestamp(start).normalize()
        parsed_end = pd.Timestamp(end).normalize()
    except (TypeError, ValueError) as exc:
        raise PlanningRunError("planning horizon must contain valid dates") from exc
    if pd.isna(parsed_start) or pd.isna(parsed_end):
        raise PlanningRunError("planning horizon must contain valid dates")
    if parsed_start > parsed_end:
        raise PlanningRunError("planning_start_week must not be after planning_end_week")
    return parsed_start, parsed_end




def _validate_percentage(value: object, name: str, *, maximum: float | None = None) -> None:
    if isinstance(value, bool):
        raise PlanningRunError(f"{name} must be a finite numeric percentage")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PlanningRunError(f"{name} must be a finite numeric percentage") from exc
    if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
        limit = f" and <= {maximum:g}" if maximum is not None else ""
        raise PlanningRunError(f"{name} must be finite, >= 0{limit}")

def _safe_output_dir(data_root: Path, output_dir: Path) -> None:
    processed = (data_root / "processed").resolve()
    target = output_dir.resolve()
    if target == processed:
        raise PlanningRunError("output_dir must be a run-specific directory, not data/processed")


def run_planning(
    data_root: str | Path,
    planning_start_week: object,
    planning_end_week: object,
    *,
    demand_surge_pct: object = 10.0,
    capacity_disruption_pct: object = 20.0,
    disruption_plant: str | Sequence[str] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Run Stages 2–5 and write deterministic, run-specific artifacts."""
    root = Path(data_root)
    start, end = _run_dates(planning_start_week, planning_end_week)
    _validate_percentage(demand_surge_pct, "demand_surge_pct")
    _validate_percentage(capacity_disruption_pct, "capacity_disruption_pct", maximum=100)
    if disruption_plant is None or disruption_plant == "" or disruption_plant == []:
        raise PlanningRunError("disruption_plant is required for the Capacity Disruption scenario")
    if isinstance(disruption_plant, str):
        plants = [disruption_plant]
    elif isinstance(disruption_plant, Sequence):
        plants = [str(p) for p in disruption_plant]
    else:
        raise PlanningRunError("disruption_plant must be a plant identifier or sequence of identifiers")
    if not plants or any(not p for p in plants):
        raise PlanningRunError("disruption_plant must identify at least one plant")

    if output_dir is None:
        target = root / "processed" / "scenario_runs" / f"{start:%Y%m%d}_{end:%Y%m%d}"
    else:
        target = Path(output_dir)
    _safe_output_dir(root, target)
    target.mkdir(parents=True, exist_ok=True)

    horizon_path = target / f"planning_snapshot_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    scenario_path = target / "scenario_snapshot.csv"
    allocation_path = target / "allocation_result.csv"
    performance_path = target / "performance_result.csv"

    try:
        run_planning_pipeline(root, start, end, horizon_path)
    except PlanningPipelineError as exc:
        raise PlanningRunError(str(exc)) from exc
    planning_snapshot = pd.read_csv(horizon_path, parse_dates=["Order_Date"])

    scenario_snapshot = generate_scenarios(
        planning_snapshot,
        [
            {"scenario": "Baseline"},
            {"scenario": "Demand_Surge", "demand_increase_pct": demand_surge_pct},
            {
                "scenario": "Capacity_Disruption",
                "capacity_reduction_pct": capacity_disruption_pct,
                "plant_ids": plants,
            },
        ],
    )
    scenario_snapshot.to_csv(scenario_path, index=False, date_format="%Y-%m-%d")

    allocation_result = run_allocation(scenario_snapshot)
    allocation_result.to_csv(allocation_path, index=False, date_format="%Y-%m-%d")

    performance_result = evaluate_allocation(allocation_result)
    performance_result.to_csv(performance_path, index=False, date_format="%Y-%m-%d")

    return {
        "planning_snapshot": horizon_path,
        "scenario_snapshot": scenario_path,
        "allocation_result": allocation_path,
        "performance_result": performance_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete Scenario Planning workflow")
    parser.add_argument("--data-root", default="data", help="Repository data directory")
    parser.add_argument("--planning-start-week", required=True)
    parser.add_argument("--planning-end-week", required=True)
    parser.add_argument("--demand-surge-pct", type=float, default=10.0)
    parser.add_argument("--capacity-disruption-pct", type=float, default=20.0)
    parser.add_argument("--disruption-plant", action="append", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    outputs = run_planning(
        args.data_root,
        args.planning_start_week,
        args.planning_end_week,
        demand_surge_pct=args.demand_surge_pct,
        capacity_disruption_pct=args.capacity_disruption_pct,
        disruption_plant=args.disruption_plant,
        output_dir=args.output_dir,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()

