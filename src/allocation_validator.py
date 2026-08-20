"""Validation rules for Stage 4 allocation inputs and results."""

from __future__ import annotations

import pandas as pd

from src.scenario_generator import SCENARIO_COLUMNS


ALLOCATION_COLUMNS = SCENARIO_COLUMNS + [
    "Net_Demand",
    "Allocated_Qty",
    "Backlog",
    "Remaining_Capacity",
    "Allocation_Order",
    "Allocation_Strategy",
    "Allocation_Reason",
]
VALID_PRIORITIES = {1, 2, 3}


class AllocationValidationError(ValueError):
    """Raised when a Stage 4 allocation business rule fails."""


def _require_nonnegative(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any() or (values < 0).any():
            raise AllocationValidationError(f"{column} must be numeric and non-negative")


def validate_scenario_snapshot(snapshot: pd.DataFrame) -> None:
    """Validate the exact Stage 3 input contract without modifying it."""
    if list(snapshot.columns) != SCENARIO_COLUMNS:
        raise AllocationValidationError("input does not match the exact Stage 3 schema")
    if snapshot.duplicated(["Scenario", "Planning_Key"]).any():
        raise AllocationValidationError("Scenario + Planning_Key must be unique")
    if snapshot[["Scenario", "Plant_ID", "Product Card Id", "Planning_Key"]].isna().any().any():
        raise AllocationValidationError("Scenario, Plant_ID, Product Card Id, and Planning_Key are required")
    dates = pd.to_datetime(snapshot["Order_Date"], errors="coerce")
    if dates.isna().any():
        raise AllocationValidationError("Order_Date contains invalid dates")
    _require_nonnegative(snapshot, ("Scenario_Demand", "Scenario_Capacity", "Beginning_Inventory"))
    priorities = pd.to_numeric(snapshot["Planning_Priority"], errors="coerce")
    if priorities.isna().any() or (priorities % 1 != 0).any() or not set(priorities.astype(int)).issubset(VALID_PRIORITIES):
        raise AllocationValidationError("Planning_Priority must contain only integer values 1, 2, or 3")
    # The observed Stage 1 mapping is one product to one eligible plant.
    product_plant_counts = snapshot.groupby("Product Card Id")["Plant_ID"].nunique()
    if (product_plant_counts > 1).any():
        raise AllocationValidationError("Product Card Id has multiple Plant_ID eligibility mappings")
    group_capacity_counts = snapshot.groupby(["Scenario", "Plant_ID", "Order_Date"])["Scenario_Capacity"].nunique()
    if (group_capacity_counts > 1).any():
        raise AllocationValidationError("Scenario_Capacity is inconsistent within Scenario × Plant × Week")


def validate_allocation_results(
    results: pd.DataFrame,
    scenario_snapshot: pd.DataFrame | None = None,
) -> None:
    """Validate allocation arithmetic, capacity use, and sparse identity."""
    if list(results.columns) != ALLOCATION_COLUMNS:
        raise AllocationValidationError("allocation results do not match the approved schema")
    if results.duplicated(["Scenario", "Planning_Key"]).any():
        raise AllocationValidationError("Scenario + Planning_Key must be unique in allocation results")
    _require_nonnegative(
        results,
        ("Scenario_Demand", "Scenario_Capacity", "Beginning_Inventory", "Net_Demand", "Allocated_Qty", "Backlog", "Remaining_Capacity"),
    )
    if (results["Allocated_Qty"] > results["Net_Demand"] + 1e-9).any():
        raise AllocationValidationError("Allocated_Qty cannot exceed Net_Demand")
    if ((results["Allocated_Qty"] + results["Backlog"] - results["Net_Demand"]).abs() > 1e-9).any():
        raise AllocationValidationError("Allocated_Qty + Backlog must equal Net_Demand")
    if scenario_snapshot is not None:
        validate_scenario_snapshot(scenario_snapshot)
        expected = set(zip(scenario_snapshot["Scenario"], scenario_snapshot["Planning_Key"]))
        actual = set(zip(results["Scenario"], results["Planning_Key"]))
        if expected != actual:
            raise AllocationValidationError("allocation results must preserve sparse input rows")

    for group_key, group in results.groupby(["Scenario", "Plant_ID", "Order_Date"], sort=False):
        capacities = group["Scenario_Capacity"].unique()
        if len(capacities) != 1:
            raise AllocationValidationError(f"inconsistent Scenario_Capacity in group {group_key}")
        capacity = float(capacities[0])
        if float(group["Allocated_Qty"].sum()) > capacity + 1e-9:
            raise AllocationValidationError(f"capacity over-allocation in group {group_key}")
        ordered = group.sort_values("Allocation_Order")
        expected_remaining = capacity
        for row in ordered.itertuples():
            expected_remaining -= float(row.Allocated_Qty)
            if abs(float(row.Remaining_Capacity) - expected_remaining) > 1e-9:
                raise AllocationValidationError("Remaining_Capacity does not reconcile with allocation")

