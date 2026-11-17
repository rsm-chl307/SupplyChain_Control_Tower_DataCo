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



def allocate_workload(
    requirements: pd.DataFrame, available_workload: float, *, quantity_step: float
) -> pd.DataFrame:
    """Allocate a product group in equivalent workload, preserving unit ranking.

    The caller prepares explicitly defined uncovered obligation quantities.
    quantity_step=0 means continuous units; a positive step enforces pack units.
    This interface does not change the legacy allocate_capacity contract.
    """
    import math

    from src.planning_inputs import numeric, require_frame

    require_frame(
        requirements,
        ["Product Card Id", "Planning_Priority", "Required_Production_Qty", "Workload_Factor"],
        ["Product Card Id"],
        "workload requirements",
    )
    numeric(requirements, ["Required_Production_Qty", "Planning_Priority"])
    numeric(requirements, ["Workload_Factor"], positive=True)
    if not requirements.Planning_Priority.isin([1, 2, 3]).all():
        raise ValueError("planning priority must be 1, 2 or 3")
    if isinstance(available_workload, bool) or not math.isfinite(available_workload) or available_workload < 0:
        raise ValueError("capacity must be finite nonnegative workload")
    if isinstance(quantity_step, bool) or not math.isfinite(quantity_step) or quantity_step < 0:
        raise ValueError("quantity_step must explicitly be zero (continuous) or a positive pack size")
    result = requirements.copy(deep=True).sort_values(
        ["Planning_Priority", "Required_Production_Qty", "Product Card Id"],
        ascending=[False, False, True], kind="mergesort",
    ).reset_index(drop=True)
    remaining = float(available_workload)
    quantities, loads, balances = [], [], []
    for _, row in result.iterrows():
        feasible = min(float(row.Required_Production_Qty), remaining / float(row.Workload_Factor))
        if quantity_step:
            feasible = math.floor(math.nextafter(feasible / quantity_step, math.inf)) * quantity_step
        load = feasible * float(row.Workload_Factor)
        # Reject, rather than hide, a floating point over-allocation.
        if load > remaining + 1e-9:
            raise ValueError("workload capacity arithmetic overflow")
        remaining = max(remaining - load, 0.0)
        quantities.append(feasible)
        loads.append(load)
        balances.append(remaining)
    result["Internal_Production_Qty"] = quantities
    result["Allocated_Workload"] = loads
    result["Remaining_Workload_After_Row"] = balances
    result["Unmet_Production_Qty"] = result.Required_Production_Qty - result.Internal_Production_Qty
    result["Unmet_Workload"] = result.Unmet_Production_Qty * result.Workload_Factor
    result["Allocation_Order"] = range(1, len(result) + 1)
    return result
