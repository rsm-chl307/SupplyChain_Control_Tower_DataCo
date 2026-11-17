"""Validation rules for Stage 4 allocation inputs and results."""

from __future__ import annotations

import numpy as np
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
        if not pd.api.types.is_numeric_dtype(frame[column]) or not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any():
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
    canonical = snapshot[["Scenario", "Plant_ID", "Product Card Id"]].copy()
    canonical["Order_Date"] = dates.dt.normalize()
    if canonical.duplicated().any():
        raise AllocationValidationError("duplicate canonical Scenario × Plant × Product × Week")
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
    validate_scenario_snapshot(results[SCENARIO_COLUMNS])
    expected_net = (results["Scenario_Demand"] - results["Beginning_Inventory"]).clip(lower=0)
    if not np.allclose(results["Net_Demand"], expected_net, rtol=0, atol=1e-9):
        raise AllocationValidationError("Net_Demand must equal uncovered scenario demand")
    if scenario_snapshot is not None:
        validate_scenario_snapshot(scenario_snapshot)
        expected = set(zip(scenario_snapshot["Scenario"], scenario_snapshot["Planning_Key"]))
        actual = set(zip(results["Scenario"], results["Planning_Key"]))
        if expected != actual:
            raise AllocationValidationError("allocation results must preserve sparse input rows")
        keys = ["Scenario", "Planning_Key"]
        original = scenario_snapshot.copy(deep=True)
        preserved = results[SCENARIO_COLUMNS].copy(deep=True)
        for frame in (original, preserved):
            frame["Order_Date"] = pd.to_datetime(frame["Order_Date"]).dt.normalize()
        original = original.set_index(keys).sort_index()
        preserved = preserved.set_index(keys).sort_index()
        try:
            pd.testing.assert_frame_equal(original, preserved, check_dtype=False, check_exact=True)
        except AssertionError as exc:
            raise AllocationValidationError("allocation changed preserved source fields") from exc


    for group_key, group in results.groupby(["Scenario", "Plant_ID", "Order_Date"], sort=False):
        capacities = group["Scenario_Capacity"].unique()
        if len(capacities) != 1:
            raise AllocationValidationError(f"inconsistent Scenario_Capacity in group {group_key}")
        capacity = float(capacities[0])
        if float(group["Allocated_Qty"].sum()) > capacity + 1e-9:
            raise AllocationValidationError(f"capacity over-allocation in group {group_key}")
        rank = group.sort_values(
            ["Planning_Priority", "Net_Demand", "Product Card Id"],
            ascending=[False, False, True], kind="mergesort",
        )
        order_values = pd.to_numeric(rank["Allocation_Order"], errors="coerce").to_numpy()
        if not np.array_equal(order_values, np.arange(1, len(rank) + 1)):
            raise AllocationValidationError("Allocation_Order violates frozen priority sequence")
        ordered = rank
        expected_remaining = capacity
        for row in ordered.itertuples():
            expected_quantity = min(float(row.Net_Demand), expected_remaining)
            if abs(float(row.Allocated_Qty) - expected_quantity) > 1e-9:
                raise AllocationValidationError("allocation violates independent greedy capacity check")
            expected_remaining -= expected_quantity
            if abs(float(row.Remaining_Capacity) - expected_remaining) > 1e-9:
                raise AllocationValidationError("Remaining_Capacity does not reconcile with allocation")

