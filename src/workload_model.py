"""Product equivalent workload and explicitly calibrated capacity (no I/O)."""

from __future__ import annotations

import math

import pandas as pd

from src.planning_inputs import ITEM_KEY, WEEK_KEY, horizon, numeric, require_frame, weekly_dates


def validate_workload_factors(factors: pd.DataFrame, products: set[int]) -> None:
    """Require one versioned product factor; plant-specific factors are excluded."""
    require_frame(factors, ["Product Card Id", "Workload_Factor", "Factor_Version", "Provenance_Type", "Workload_Unit"], ["Product Card Id"], "workload factors")
    numeric(factors, ["Workload_Factor"], positive=True)
    if "Plant_ID" in factors.columns:
        raise ValueError("plant-specific workload factors are outside this upgrade")
    if products - set(factors["Product Card Id"]):
        raise ValueError("missing product workload factors")
    for column in ["Factor_Version", "Provenance_Type", "Workload_Unit"]:
        if factors[column].isna().any() or factors[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"missing factor provenance: {column}")
    if factors.Workload_Unit.nunique() != 1 or factors.Factor_Version.nunique() != 1:
        raise ValueError("one compatible workload unit and factor version required")


def calibrate_workload_capacity(
    demand: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    calibration_start: object,
    calibration_end: object,
    target_utilization: float,
    capacity_version: str,
) -> pd.DataFrame:
    """Derive a labeled synthetic baseline from complete qualified workload.

    The caller supplies the calibration cohort/window and target. No legacy
    quantity capacity, target utilization or capacity multiplier is reused.
    """
    if isinstance(target_utilization, bool) or not math.isfinite(target_utilization) or not 0 < target_utilization <= 1:
        raise ValueError("target_utilization must be in (0, 1]")
    if not capacity_version:
        raise ValueError("capacity version required")
    weeks = horizon(calibration_start, calibration_end)
    source = weekly_dates(demand)
    require_frame(source, WEEK_KEY + ["Qualified_Demand", "Coverage_Status"], WEEK_KEY, "calibration demand")
    numeric(source, ["Qualified_Demand"])
    source = source[source.Order_Date.isin(weeks)].copy()
    if source.empty or not source.Coverage_Status.isin(["OBSERVED_DEMAND", "OBSERVED_ZERO"]).all():
        raise ValueError("complete calibration demand coverage required")
    counts = source.groupby(ITEM_KEY).Order_Date.nunique()
    if counts.ne(len(weeks)).any():
        raise ValueError("every calibration item must cover the full calibration window")
    validate_workload_factors(factors, set(source["Product Card Id"]))
    source = source.merge(factors[["Product Card Id", "Workload_Factor"]], validate="many_to_one")
    source["Workload"] = source.Qualified_Demand * source.Workload_Factor
    totals = source.groupby(["Plant_ID", "Order_Date"]).Workload.sum().reset_index()
    result = totals.groupby("Plant_ID").Workload.mean().div(target_utilization).rename("Baseline_Workload_Capacity").reset_index()
    result["Capacity_Version"] = capacity_version
    result["Provenance_Type"] = "SYNTHETIC_DEMAND_CALIBRATED"
    result["Target_Utilization"] = target_utilization
    result["Calibration_Start"] = weeks[0]
    result["Calibration_End"] = weeks[-1]
    result["Workload_Unit"] = factors.Workload_Unit.iloc[0]
    result["Factor_Version"] = factors.Factor_Version.iloc[0]
    return result


def expand_capacity_calendar(capacity: pd.DataFrame, start: object, end: object) -> pd.DataFrame:
    """Expand only plant capacity pools over an explicit requested calendar."""
    require_frame(capacity, ["Plant_ID", "Baseline_Workload_Capacity"], ["Plant_ID"], "capacity baseline")
    numeric(capacity, ["Baseline_Workload_Capacity"])
    if capacity.empty:
        raise ValueError("nonempty capacity required")
    weeks = pd.DataFrame({"Order_Date": horizon(start, end)})
    return capacity.merge(weeks, how="cross")
