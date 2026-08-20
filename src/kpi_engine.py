"""Numerical Stage 5 KPI calculations for Stage 4 allocation results."""

from __future__ import annotations

import pandas as pd

from src.allocation_validator import validate_allocation_results


KPI_COLUMNS = [
    "Aggregation_Level",
    "Scenario",
    "Plant_ID",
    "Order_Date",
    "Total_Scenario_Demand",
    "Total_Net_Demand",
    "Total_Allocated_Qty",
    "Total_Backlog",
    "Total_Scenario_Capacity",
    "Remaining_Capacity",
    "Capacity_Gap",
    "Service_Level",
    "Capacity_Utilization",
    "Allocation_Rate",
]


def _ratio(numerator: float, denominator: float, zero_value: float) -> float:
    return zero_value if denominator == 0 else numerator / denominator


def calculate_kpis(allocation_results: pd.DataFrame) -> pd.DataFrame:
    """Return KPI rows at Scenario, Scenario × Plant, and Scenario × Week."""
    validate_allocation_results(allocation_results)
    source = allocation_results.copy(deep=True)
    dates = pd.to_datetime(source["Order_Date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("Order_Date contains invalid dates")
    source["Order_Date"] = dates.dt.normalize()
    specifications = [
        ("Scenario", ["Scenario"]),
        ("Scenario × Plant", ["Scenario", "Plant_ID"]),
        ("Scenario × Week", ["Scenario", "Order_Date"]),
    ]
    records: list[dict[str, object]] = []
    measures = ["Scenario_Demand", "Net_Demand", "Allocated_Qty", "Backlog", "Scenario_Capacity"]
    for level, keys in specifications:
        grouped = source.groupby(keys, sort=True, dropna=False)
        for key_values, group in grouped:
            if not isinstance(key_values, tuple):
                key_values = (key_values,)
            values = dict(zip(keys, key_values))
            totals = group[["Scenario_Demand", "Net_Demand", "Allocated_Qty", "Backlog"]].sum()
            demand = float(totals["Scenario_Demand"])
            net_demand = float(totals["Net_Demand"])
            allocated = float(totals["Allocated_Qty"])
            backlog = float(totals["Backlog"])
            # Scenario_Capacity is repeated on each product row. Count each
            # Scenario × Plant × Week capacity pool exactly once.
            capacity_rows = group[["Scenario", "Plant_ID", "Order_Date", "Scenario_Capacity"]].drop_duplicates(
                ["Scenario", "Plant_ID", "Order_Date"]
            )
            capacity = float(capacity_rows["Scenario_Capacity"].sum())
            records.append(
                {
                    "Aggregation_Level": level,
                    "Scenario": values["Scenario"],
                    "Plant_ID": values.get("Plant_ID"),
                    "Order_Date": values.get("Order_Date"),
                    "Total_Scenario_Demand": demand,
                    "Total_Net_Demand": net_demand,
                    "Total_Allocated_Qty": allocated,
                    "Total_Backlog": backlog,
                    "Total_Scenario_Capacity": capacity,
                    "Remaining_Capacity": capacity - allocated,
                    "Capacity_Gap": capacity - allocated,
                    "Service_Level": _ratio(allocated, net_demand, 1.0),
                    "Capacity_Utilization": _ratio(allocated, capacity, 0.0),
                    "Allocation_Rate": _ratio(allocated, demand, 1.0),
                }
            )
    result = pd.DataFrame(records, columns=KPI_COLUMNS)
    return result.sort_values(
        ["Aggregation_Level", "Scenario", "Plant_ID", "Order_Date"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)

