"""Stage 2 reproducible Planning Snapshot pipeline."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import warnings

import pandas as pd

from src.planning_snapshot import (
    SNAPSHOT_COLUMNS,
    ValidationReport,
    build_planning_snapshot,
    validate_planning_snapshot,
)

SOURCE_FILES = {
    "demand": Path("processed/plant_product_weekly_demand.csv"),
    "capacity": Path("processed/capacity_utilization_weekly.csv"),
    "inventory": Path("processed/inventory_snapshot_weekly.csv"),
    "abc": Path("processed/product_abc_classification.csv"),
    "product_plant_mapping": Path("master/product_plant_mapping.csv"),
}
_OUTPUT_PATTERN = re.compile(
    r"^planning_snapshot_(?P<start>\d{8})_(?P<end>\d{8})\.csv$"
)


class PlanningPipelineError(ValueError):
    """Raised when pipeline configuration or horizon validation fails."""


def load_planning_sources(data_root: str | Path) -> dict[str, pd.DataFrame]:
    """Load the approved Stage 1 source datasets from a data directory."""

    root = Path(data_root)
    sources: dict[str, pd.DataFrame] = {}
    for name, relative_path in SOURCE_FILES.items():
        path = root / relative_path
        if not path.exists():
            raise PlanningPipelineError(f"Required planning source is missing: {path}")
        sources[name] = pd.read_csv(path)
    return sources


def _parse_horizon_date(value: object, parameter_name: str) -> pd.Timestamp:
    if value is None or value == "":
        raise PlanningPipelineError(f"{parameter_name} is required")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        raise PlanningPipelineError(f"{parameter_name} must be a date, not a number")
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise PlanningPipelineError(
            f"{parameter_name} has invalid date format: {value!r}"
        ) from exc
    if pd.isna(parsed):
        raise PlanningPipelineError(f"{parameter_name} has invalid date format: {value!r}")
    return parsed.normalize()


def _validate_output_path(output_path: Path, start: pd.Timestamp, end: pd.Timestamp) -> None:
    expected_name = f"planning_snapshot_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    if output_path.name != expected_name:
        raise PlanningPipelineError(
            f"output_path must be named {expected_name!r} for the selected horizon"
        )


def _validate_horizon(
    snapshot: pd.DataFrame,
    planning_start_week: object,
    planning_end_week: object,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = _parse_horizon_date(planning_start_week, "planning_start_week")
    end = _parse_horizon_date(planning_end_week, "planning_end_week")
    if start > end:
        raise PlanningPipelineError("planning_start_week must not be after planning_end_week")

    available_dates = pd.to_datetime(snapshot["Order_Date"], errors="coerce").dropna()
    if available_dates.empty:
        raise PlanningPipelineError("Planning Snapshot has no valid Order_Date values")
    available_start = available_dates.min().normalize()
    available_end = available_dates.max().normalize()
    available_range = f"{available_start:%Y-%m-%d} through {available_end:%Y-%m-%d}"
    if start < available_start:
        raise PlanningPipelineError(
            f"planning_start_week {start:%Y-%m-%d} is before available source range "
            f"({available_range})"
        )
    if end > available_end:
        raise PlanningPipelineError(
            f"planning_end_week {end:%Y-%m-%d} is after available source range "
            f"({available_range})"
        )
    return start, end


def _raise_for_hard_errors(report: ValidationReport, stage: str) -> None:
    if report.hard_errors:
        raise PlanningPipelineError(
            f"{stage} validation failed: " + "; ".join(report.hard_errors)
        )


def run_planning_pipeline(
    data_root: str | Path,
    planning_start_week: object,
    planning_end_week: object,
    output_path: str | Path,
) -> pd.DataFrame:
    """Build, filter, validate, and persist one horizon-specific snapshot.

    ``data_root`` is the repository ``data`` directory. The full baseline
    artifact is never overwritten by this function.
    """

    output = Path(output_path)
    if output.name == "planning_snapshot.csv":
        raise PlanningPipelineError("Stage 2 cannot overwrite the canonical baseline artifact")

    sources = load_planning_sources(data_root)
    baseline = build_planning_snapshot(
        sources["demand"],
        sources["capacity"],
        sources["inventory"],
        sources["abc"],
        sources["product_plant_mapping"],
    )
    baseline_report = validate_planning_snapshot(baseline)
    _raise_for_hard_errors(baseline_report, "Baseline")

    start, end = _validate_horizon(baseline, planning_start_week, planning_end_week)
    _validate_output_path(output, start, end)
    baseline["Order_Date"] = pd.to_datetime(baseline["Order_Date"])
    filtered = baseline[
        baseline["Order_Date"].between(start, end, inclusive="both")
    ].copy()
    if filtered.empty:
        raise PlanningPipelineError(
            f"Selected horizon {start:%Y-%m-%d} through {end:%Y-%m-%d} contains no observations"
        )

    filtered_report = validate_planning_snapshot(filtered)
    _raise_for_hard_errors(filtered_report, "Filtered snapshot")
    if filtered_report.warnings:
        warnings.warn("; ".join(filtered_report.warnings), UserWarning, stacklevel=2)

    filtered = filtered.sort_values(
        ["Plant_ID", "Product Card Id", "Order_Date"],
        kind="mergesort",
    )[SNAPSHOT_COLUMNS]
    output.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(output, index=False, date_format="%Y-%m-%d")
    return filtered
