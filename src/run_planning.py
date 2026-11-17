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
    parser.add_argument("--data-root", default="data", help="Legacy reference directory; CSV data modes use config-relative paths")
    parser.add_argument("--planning-start-week")
    parser.add_argument("--planning-end-week")
    parser.add_argument("--demand-surge-pct", type=float, default=10.0)
    parser.add_argument("--capacity-disruption-pct", type=float, default=20.0)
    parser.add_argument("--disruption-plant", action="append")
    parser.add_argument("--output-dir")
    parser.add_argument("--sequential-config", help="Explicit JSON config for the sequential planning path")
    parser.add_argument("--validate-inputs", action="store_true", help="Validate generic CSV configuration without running the engine")
    args = parser.parse_args()
    if args.sequential_config:
        import json
        config_path = Path(args.sequential_config).resolve()
        config = json.loads(config_path.read_text())
        if args.validate_inputs:
            from src.csv_planning_inputs import InputValidationError, load_csv_planning_inputs
            try:
                bundle = load_csv_planning_inputs(config, config_path.parent)
            except InputValidationError as exc:
                print(json.dumps(exc.report, indent=2))
                raise SystemExit(2) from exc
            print(json.dumps(bundle.report, indent=2))
            return
        outputs = run_sequential_planning(args.data_root, config, inputs_dir=config_path.parent, output_root=args.output_dir)
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return
    if args.validate_inputs:
        parser.error("--validate-inputs requires --sequential-config")
    if not args.planning_start_week or not args.planning_end_week or not args.disruption_plant:
        parser.error("legacy mode requires start/end weeks and disruption plant")
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




def run_sequential_planning(
    data_root: str | Path | None,
    config: dict,
    *,
    inputs_dir: str | Path,
    output_root: str | Path | None = None,
) -> dict[str, Path]:
    """Execute the reduced raw-to-sequential-KPI vertical slice.

    Every business input is explicit. New unique runs never overwrite legacy
    outputs. Only a complete independently validated run is marked PUBLISHED.
    Paths for assumptions are resolved relative to the JSON configuration.
    """
    from datetime import datetime, timezone
    from hashlib import sha256
    from io import BytesIO
    import json
    import platform
    from uuid import uuid4

    from src.demand_preparation import build_demand_coverage, prepare_demand
    from src.kpi_engine import calculate_sequential_kpis
    from src.planning_inputs import ITEM_KEY, numeric, require_frame
    from src.scenario_generator import generate_sequential_scenarios
    from src.sequential_planner import simulate_sequential
    from src.sequential_validator import validate_sequential_results
    from src.workload_model import calibrate_workload_capacity, expand_capacity_calendar

    generic_csv = "data_mode" in config
    required = {
        "assumption_version", "planning_interpretation", "planning_start_week", "planning_end_week",
        "product_ids", "status_eligibility", "eligibility_version", "source_is_complete",
        "workload_factors_file", "initial_state_file", "external_receipts_file",
        "quantity_step", "allocation_policy", "scenarios", "orders_file",
    }
    if generic_csv:
        required = {"assumption_version", "planning_interpretation", "planning_start_week", "planning_end_week", "quantity_step", "allocation_policy", "scenarios", "files", "data_mode"}
    missing = required - set(config)
    if missing:
        raise PlanningRunError(f"sequential configuration missing {sorted(missing)}")
    if not generic_csv and config["planning_interpretation"] != "RETROSPECTIVE":
        raise PlanningRunError("this input adapter supports explicitly retrospective historical replay only")
    if not config["assumption_version"]:
        raise PlanningRunError("assumption version required")
    if not generic_csv:
        products = config["product_ids"]
        if not isinstance(products, list) or not products or len(set(products)) != len(products):
            raise PlanningRunError("explicit unique nonempty product cohort required")
        if any(type(p) is not int for p in products):
            raise PlanningRunError("product_ids must be source integer IDs")
    root, assumption_root = Path(data_root) if data_root is not None else Path("."), Path(inputs_dir)
    start, end = config["planning_start_week"], config["planning_end_week"]
    run_id = "sequential_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:12]
    target_root = Path(output_root) if output_root is not None else (Path("tmp/planning_upgrade_runs") if generic_csv else root / "processed" / "planning_runs")
    target = target_root / run_id
    target.mkdir(parents=True, exist_ok=False)
    manifest_path = target / "run_manifest.json"
    manifest = {
        "Run_ID": run_id, "Schema_Version": "sequential_v1",
        "Execution_Status": "RUNNING", "Validation_Status": "NOT_EVALUATED", "Publication_Status": "UNPUBLISHED",
        "Started_At": datetime.now(timezone.utc).isoformat(),
        "Configuration": config, "Source_Hashes": {}, "Artifacts": {},
        "Environment": {"Python": platform.python_version(), "Pandas": pd.__version__},
        "Limitations": ["Demand basis is declared by the source configuration; no forecast model is generated.", "Synthetic workload standards and capacity recipes must be labeled in input assumptions.",
                        "Cross-product ranking retains product priority; backlog is served first within each product.",
                        "Receipt Order_Date is explicitly the week supply is usable.", "No production lead-time configuration or procurement optimization."],
    }

    def save_manifest() -> None:
        pending = target / ".manifest.pending"
        pending.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        pending.replace(manifest_path)

    def read(path: Path, *, latin1: bool = False, columns: list[str] | None = None, strings: bool = False, encoding: str | None = None) -> pd.DataFrame:
        payload = path.read_bytes()
        manifest["Source_Hashes"][str(path.resolve())] = sha256(payload).hexdigest()
        return pd.read_csv(BytesIO(payload), encoding=encoding or ("latin1" if latin1 else "utf-8"), usecols=columns, **({"dtype": str, "keep_default_na": False} if strings else {}))

    outputs: dict[str, Path] = {}
    try:
        save_manifest()
        if generic_csv:
            from src.csv_planning_inputs import load_csv_planning_inputs
            bundle = load_csv_planning_inputs(
                config, assumption_root,
                reader=lambda path, encoding: read(path, strings=True, encoding=encoding),
            )
            ledger, weekly, full_coverage, coverage = bundle.ledger, bundle.weekly, bundle.coverage, bundle.demand
            initial, receipts, factors = bundle.initial, bundle.receipts, bundle.factors
            capacity, cap_calendar = bundle.capacity, bundle.capacity_calendar
            manifest["Data_Mode"] = bundle.data_mode
            manifest["Input_Validation"] = bundle.report
            manifest["Scope"] = bundle.scope
        else:
            manifest["Data_Mode"] = "USER_DATA"
            manifest["Source_Profile"] = "LEGACY_REFERENCE_ADAPTER"
            orders = read(root / config["orders_file"], latin1=True, columns=["Order Item Id", "Product Card Id", "Order Status", "order date (DateOrders)", "Order Item Quantity"])
            mapping = read(root / "master/product_plant_mapping.csv")
            product_master = read(root / "master/dim_product.csv")
            plant_master = read(root / "master/dim_plant.csv")
            abc = read(root / "processed/product_abc_classification.csv")
            require_frame(product_master, ["Product Card Id", "Product Name"], ["Product Card Id"], "product master")
            require_frame(plant_master, ["Plant_ID"], ["Plant_ID"], "plant master")
            require_frame(mapping, ITEM_KEY, ["Product Card Id"], "mapping")
            require_frame(abc, ["Product Card Id", "ABC_Class"], ["Product Card Id"], "ABC")
            if set(orders["Product Card Id"]) - set(product_master["Product Card Id"]) or set(mapping.Plant_ID) - set(plant_master.Plant_ID) or set(mapping["Product Card Id"]) - set(product_master["Product Card Id"]):
                raise PlanningRunError("raw/master referential integrity failed")
            if set(products) - set(mapping["Product Card Id"]):
                raise PlanningRunError("planning cohort includes unmapped products")
            ledger, weekly = prepare_demand(
                orders, mapping, config["status_eligibility"],
                eligibility_version=config["eligibility_version"], source_is_complete=config["source_is_complete"],
            )
            selected_items = mapping[mapping["Product Card Id"].isin(products)][ITEM_KEY].copy()
            full_coverage = build_demand_coverage(weekly, selected_items, start, end)
            coverage = full_coverage[full_coverage.Coverage_Status.ne("OUT_OF_SCOPE")].copy()
            unknown = coverage.Coverage_Status.eq("UNKNOWN")
            if unknown.any():
                examples = coverage.loc[unknown, ["Plant_ID", "Product Card Id", "Order_Date"]].head(5).astype(str).to_dict("records")
                raise PlanningRunError(f"{int(unknown.sum())} UNKNOWN product-weeks block simulation; examples: {examples}")
            coverage = coverage.merge(product_master[["Product Card Id", "Product Name"]], on="Product Card Id", validate="many_to_one")
            coverage = coverage.merge(abc[["Product Card Id", "ABC_Class"]], on="Product Card Id", how="left", validate="many_to_one")
            coverage["Planning_Priority"] = coverage.ABC_Class.map({"A": 3, "B": 2, "C": 1})
            if coverage.Planning_Priority.isna().any():
                raise PlanningRunError("unresolved ABC product priority")
            factors = read(assumption_root / config["workload_factors_file"])
            initial = read(assumption_root / config["initial_state_file"])
            receipts = read(assumption_root / config["external_receipts_file"])
            require_frame(initial, ITEM_KEY + ["Beginning_Inventory", "Beginning_Backlog", "Provenance_Type", "Initial_State_Version"], ITEM_KEY, "opening input")
            require_frame(receipts, ["Receipt_ID", "Provenance_Type", "Receipt_Schedule_Version"] + ITEM_KEY + ["Order_Date", "External_Receipts_Qty"],
                          ["Scenario", "Receipt_ID"] if "Scenario" in receipts else ["Receipt_ID"], "receipt input")
            for frame, cols in [(initial, ["Provenance_Type", "Initial_State_Version"]), (receipts, ["Provenance_Type", "Receipt_Schedule_Version"])]:
                for column in cols:
                    if frame[column].isna().any() or frame[column].astype(str).str.strip().eq("").any():
                        raise PlanningRunError(f"explicit supply provenance required: {column}")
            if "capacity_file" in config and "capacity_calibration" in config:
                raise PlanningRunError("choose explicit workload capacity or calibration, not both")
            if "capacity_file" in config:
                capacity = read(assumption_root / config["capacity_file"])
                require_frame(capacity, ["Plant_ID", "Baseline_Workload_Capacity", "Capacity_Version", "Provenance_Type", "Factor_Version", "Workload_Unit"], ["Plant_ID"], "capacity input")
            elif "capacity_calibration" in config:
                calibration = config["capacity_calibration"]
                required_calibration = {"start_week", "end_week", "target_utilization", "capacity_version"}
                if not required_calibration.issubset(calibration):
                    raise PlanningRunError("explicit calibration window, target and version required")
                calibration_coverage = build_demand_coverage(weekly, selected_items, calibration["start_week"], calibration["end_week"])
                calibration_coverage = calibration_coverage[calibration_coverage.Coverage_Status.ne("OUT_OF_SCOPE")]
                capacity = calibrate_workload_capacity(
                    calibration_coverage, factors, calibration_start=calibration["start_week"], calibration_end=calibration["end_week"],
                    target_utilization=calibration["target_utilization"], capacity_version=calibration["capacity_version"],
                )
            else:
                raise PlanningRunError("explicit workload capacity input or calibration required")
            numeric(capacity, ["Baseline_Workload_Capacity"])
            cap_calendar = expand_capacity_calendar(capacity, start, end)
        scenario_demand, scenario_pools = generate_sequential_scenarios(coverage, cap_calendar, config["scenarios"])
        states, pool_results = simulate_sequential(
            scenario_demand, scenario_pools, initial, receipts, factors,
            quantity_step=config["quantity_step"], allocation_policy=config["allocation_policy"],
        )
        validation = validate_sequential_results(
            states, pool_results, scenario_demand, scenario_pools, initial, receipts, factors,
            quantity_step=config["quantity_step"],
        )
        performance = calculate_sequential_kpis(states, pool_results)
        if not generic_csv:
            horizon_ledger = ledger[ledger.Order_Date.between(pd.Timestamp(start), pd.Timestamp(end))]
            manifest["Scope"] = {
                "Product_IDs": products, "Selected_Products": len(products),
                "Unselected_Source_Products": len(set(orders["Product Card Id"]) - set(products)),
                "Historical_Gross_All_Source": float(ledger.Gross_Demand.sum()),
                "Historical_Qualified_All_Source": float(ledger.Qualified_Demand.sum()),
                "Historical_Excluded_All_Source": float(ledger.Excluded_Demand.sum()),
                "Planning_Horizon": [str(start), str(end)],
                "Horizon_Gross_All_Source": float(horizon_ledger.Gross_Demand.sum()),
                "Horizon_Qualified_All_Source": float(horizon_ledger.Qualified_Demand.sum()),
                "Horizon_Gross_Selected_Cohort": float(coverage.Gross_Demand.sum()),
                "Horizon_Qualified_Selected_Cohort": float(coverage.Qualified_Demand.sum()),
                "Horizon_Qualified_Outside_Cohort": float(horizon_ledger.Qualified_Demand.sum() - coverage.Qualified_Demand.sum()),
                "Coverage_Status_Counts": {str(k): int(v) for k, v in full_coverage.Coverage_Status.value_counts().items()},
            }
        artifacts = {
            "eligibility_ledger": ledger, "weekly_demand": weekly, "demand_coverage": full_coverage,
            "initial_state": initial, "external_receipts": receipts, "workload_factors": factors,
            "capacity_baseline": capacity, "scenario_snapshot": scenario_demand,
            "capacity_pools": pool_results, "allocation_result": states,
            "performance_result": performance, "validation_result": validation,
        }
        for name, frame in artifacts.items():
            frame = frame.copy(deep=True)
            frame["Run_ID"] = run_id
            frame["Schema_Version"] = "sequential_v1"
            path = target / f"{name}.csv"
            frame.to_csv(path, index=False, date_format="%Y-%m-%d")
            manifest["Artifacts"][name] = {"Path": path.name, "SHA256": sha256(path.read_bytes()).hexdigest(), "Rows": len(frame)}
            outputs[name] = path
        manifest["Execution_Status"] = "SUCCEEDED"
        manifest["Validation_Status"] = "PASSED"
        manifest["Publication_Status"] = "PUBLISHED"
        manifest["Finished_At"] = datetime.now(timezone.utc).isoformat()
        save_manifest()  # Publish only after every artifact and validation pass.
        outputs["run_manifest"] = manifest_path
        return outputs
    except Exception as exc:
        manifest["Execution_Status"] = "FAILED"
        manifest["Validation_Status"] = "FAILED"
        manifest["Publication_Status"] = "UNPUBLISHED"
        manifest["Failure_Detail"] = f"{type(exc).__name__}: {exc}"
        if hasattr(exc, "report"):
            manifest["Input_Validation"] = exc.report
        try:
            save_manifest()
        except OSError:
            pass
        raise


def run_csv_planning(config: dict, *, inputs_dir: str | Path, output_root: str | Path | None = None) -> dict[str, Path]:
    """Run SYNTHETIC_DEMO or USER_DATA without any repository data-root dependency."""
    if "data_mode" not in config:
        raise PlanningRunError("CSV planning requires an explicit data_mode")
    return run_sequential_planning(None, config, inputs_dir=inputs_dir, output_root=output_root)


if __name__ == "__main__":
    main()
