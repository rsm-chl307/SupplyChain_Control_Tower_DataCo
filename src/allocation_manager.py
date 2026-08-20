"""In-memory orchestration of Stage 4 allocation across all groups."""

from __future__ import annotations

import pandas as pd

from src.allocation_engine import allocate_capacity
from src.allocation_validator import ALLOCATION_COLUMNS, validate_allocation_results, validate_scenario_snapshot


def run_allocation(scenario_snapshot: pd.DataFrame) -> pd.DataFrame:
    """Allocate every Scenario × Plant × Week group deterministically."""
    validate_scenario_snapshot(scenario_snapshot)
    source = scenario_snapshot.copy(deep=True)
    source["Order_Date"] = pd.to_datetime(source["Order_Date"], errors="coerce").dt.normalize()
    source = source.sort_values(["Scenario", "Plant_ID", "Order_Date", "Product Card Id"], kind="mergesort")
    outputs = [
        allocate_capacity(group.copy(deep=True))
        for _, group in source.groupby(["Scenario", "Plant_ID", "Order_Date"], sort=False)
    ]
    result = pd.concat(outputs, ignore_index=True)[ALLOCATION_COLUMNS]
    result = result.sort_values(
        ["Scenario", "Plant_ID", "Order_Date", "Allocation_Order", "Product Card Id"],
        kind="mergesort",
    ).reset_index(drop=True)
    validate_allocation_results(result, scenario_snapshot)
    return result

