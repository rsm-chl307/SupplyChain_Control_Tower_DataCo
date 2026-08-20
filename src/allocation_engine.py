"""Deterministic rule-based allocation for one planning group."""

from __future__ import annotations

import pandas as pd

from src.allocation_validator import ALLOCATION_COLUMNS, AllocationValidationError, validate_scenario_snapshot


def allocate_capacity(planning_group: pd.DataFrame) -> pd.DataFrame:
    """Allocate one Scenario × Plant × Week group without file I/O."""
    validate_scenario_snapshot(planning_group)
    if planning_group["Scenario"].nunique() != 1 or planning_group["Plant_ID"].nunique() != 1 or planning_group["Order_Date"].nunique() != 1:
        raise AllocationValidationError("allocate_capacity requires one Scenario × Plant × Week group")
    capacity_values = planning_group["Scenario_Capacity"].unique()
    if len(capacity_values) != 1:
        raise AllocationValidationError("Scenario_Capacity must be consistent within the allocation group")

    result = planning_group.copy(deep=True)
    result["Net_Demand"] = (result["Scenario_Demand"] - result["Beginning_Inventory"]).clip(lower=0)
    result = result.sort_values(
        ["Planning_Priority", "Net_Demand", "Product Card Id"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    remaining = float(capacity_values[0])
    allocated = []
    backlog = []
    remaining_values = []
    reasons = []
    for row in result.itertuples():
        requirement = float(row.Net_Demand)
        if requirement <= 0:
            quantity = 0.0
            reason = "No Production Required"
        elif remaining <= 0:
            quantity = 0.0
            reason = "Capacity Exhausted"
        else:
            quantity = min(requirement, remaining)
            reason = "Demand Fully Satisfied" if quantity >= requirement else "Remaining Capacity"
        remaining = max(remaining - quantity, 0.0)
        allocated.append(quantity)
        backlog.append(requirement - quantity)
        remaining_values.append(remaining)
        reasons.append(reason)
    result["Allocated_Qty"] = allocated
    result["Backlog"] = backlog
    result["Remaining_Capacity"] = remaining_values
    result["Allocation_Order"] = range(1, len(result) + 1)
    result["Allocation_Strategy"] = "Priority First"
    result["Allocation_Reason"] = reasons
    return result[ALLOCATION_COLUMNS]

