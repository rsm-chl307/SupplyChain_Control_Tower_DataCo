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



def calculate_sequential_kpis(states: pd.DataFrame, pools: pd.DataFrame) -> pd.DataFrame:
    """Aggregate new workload/fulfillment facts without changing legacy KPIs.

    0/0 is explicitly undefined (NaN), not a hidden 100% service assertion.
    Horizon fulfillment includes later service of horizon-origin backlog and
    excludes fulfillment of pre-horizon obligations. Stock totals use the last
    selected period for each product, never a sum of weekly stock balances.
    """
    import numpy as np

    from src.planning_inputs import WEEK_KEY, numeric, require_frame, weekly_dates

    source = weekly_dates(states)
    capacity = weekly_dates(pools)
    require_frame(source, ["Scenario", "Backlog_Policy"] + WEEK_KEY, ["Scenario"] + WEEK_KEY, "KPI states")
    require_frame(capacity, ["Scenario", "Plant_ID", "Order_Date", "Available_Workload_Capacity", "Allocated_Workload"], ["Scenario", "Plant_ID", "Order_Date"], "KPI capacity")
    required_values = ["Scenario_Qualified_Demand", "Required_Production_Qty", "Internal_Production_Qty", "External_Receipts_Qty",
                       "Fulfilled_Current_Qty", "Fulfilled_Horizon_Backlog_Qty", "Fulfilled_Opening_Backlog_Qty",
                       "Ending_Inventory", "Ending_Backlog", "Ending_Horizon_Backlog", "Ending_Opening_Backlog", "Lost_Sales_Qty"]
    require_frame(source, required_values, ["Scenario"] + WEEK_KEY, "KPI measures")
    numeric(source, required_values)
    require_frame(capacity, ["Remaining_Workload_Capacity"], ["Scenario", "Plant_ID", "Order_Date"], "KPI pool balance")
    numeric(capacity, ["Available_Workload_Capacity", "Allocated_Workload", "Remaining_Workload_Capacity", "Unmet_Workload"])
    if (capacity.Allocated_Workload > capacity.Available_Workload_Capacity + 1e-8).any():
        raise ValueError("KPI workload pool over-allocation")
    if (capacity.Available_Workload_Capacity.eq(0) & capacity.Allocated_Workload.ne(0)).any():
        raise ValueError("nonzero workload cannot use zero capacity")
    if not np.allclose(capacity.Remaining_Workload_Capacity, capacity.Available_Workload_Capacity - capacity.Allocated_Workload, rtol=0, atol=1e-8):
        raise ValueError("KPI workload balance does not reconcile")
    if source.empty:
        raise ValueError("nonempty sequential KPI inputs required")
    records = []
    specifications = [
        ("Scenario", ["Scenario"]),
        ("Scenario × Plant", ["Scenario", "Plant_ID"]),
        ("Scenario × Week", ["Scenario", "Order_Date"]),
        ("Scenario × Plant × Week", ["Scenario", "Plant_ID", "Order_Date"]),
    ]
    for level, keys in specifications:
        for values, group in source.groupby(keys, sort=True):
            values = values if isinstance(values, tuple) else (values,)
            identity = dict(zip(keys, values))
            selected_pools = capacity
            for key, value in identity.items():
                selected_pools = selected_pools[selected_pools[key].eq(value)]
            terminal = group.sort_values("Order_Date").groupby(["Plant_ID", "Product Card Id"], sort=False).tail(1)
            q = float(group.Scenario_Qualified_Demand.sum())
            p = float(group.Internal_Production_Qty.sum())
            r = float(group.Required_Production_Qty.sum())
            current_fulfillment = float(group.Fulfilled_Current_Qty.sum())
            horizon_fulfillment = current_fulfillment + float(group.Fulfilled_Horizon_Backlog_Qty.sum())
            available = float(selected_pools.Available_Workload_Capacity.sum())
            allocated_load = float(selected_pools.Allocated_Workload.sum())
            # Week views report same-week current cohort service separately:
            # backlog fulfilled in this week can originate in an earlier week.
            numerator = current_fulfillment if "Order_Date" in keys else horizon_fulfillment
            if group.Backlog_Policy.nunique() != 1:
                raise ValueError("cannot combine different shortage policies in one scenario KPI")
            record = {
                "Aggregation_Level": level, "Scenario": identity["Scenario"],
                "Plant_ID": identity.get("Plant_ID"), "Order_Date": identity.get("Order_Date"),
                "Backlog_Policy": group.Backlog_Policy.iloc[0],
                "Scenario_Qualified_Demand": q, "Required_Production_Qty": r,
                "Internal_Production_Qty": p, "External_Receipts_Qty": float(group.External_Receipts_Qty.sum()),
                "Fulfilled_Current_Qty": current_fulfillment,
                "Fulfilled_Horizon_Backlog_Qty": float(group.Fulfilled_Horizon_Backlog_Qty.sum()),
                "Fulfilled_Opening_Backlog_Qty": float(group.Fulfilled_Opening_Backlog_Qty.sum()),
                "Demand_Fulfillment_Numerator": numerator, "Demand_Fulfillment_Denominator": q,
                "Fulfillment_Basis": "CURRENT_WEEK_COHORT" if "Order_Date" in keys else "HORIZON_ORIGIN_COHORT",
                "Production_Coverage_Rate": p / r if r else np.nan,
                "Demand_Fulfillment_Rate": numerator / q if q else np.nan,
                "Available_Workload_Capacity": available, "Allocated_Workload": allocated_load,
                "Capacity_Utilization": min(allocated_load / available, 1.0) if available else np.nan,
                "Remaining_Workload_Capacity": float(selected_pools.Remaining_Workload_Capacity.sum()),
                "Ending_Inventory": float(terminal.Ending_Inventory.sum()),
                "Ending_Backlog": float(terminal.Ending_Backlog.sum()),
                "Ending_Horizon_Backlog": float(terminal.Ending_Horizon_Backlog.sum()),
                "Ending_Opening_Backlog": float(terminal.Ending_Opening_Backlog.sum()),
                "Lost_Sales_Qty": float(group.Lost_Sales_Qty.sum()),
                "Bottleneck_Plant_Weeks": int(selected_pools.Workload_Shortage.sum()),
                "Ratio_Zero_Policy": "UNDEFINED_WHEN_DENOMINATOR_ZERO",
            }
            for column in ["Gross_Demand", "Qualified_Demand", "Excluded_Demand"]:
                if column in group:
                    record[column] = float(group[column].sum())
            records.append(record)
    result = pd.DataFrame(records)
    # Deltas are calculated only at the same grain and shortage policy.
    for column in ["Demand_Fulfillment_Rate", "Capacity_Utilization", "Ending_Backlog", "Lost_Sales_Qty"]:
        result[column + "_Change"] = np.nan
    keys = ["Aggregation_Level", "Plant_ID", "Order_Date", "Backlog_Policy"]
    baseline = result[result.Scenario.eq("Baseline")].set_index(keys)
    for idx, row in result.iterrows():
        lookup = tuple(row[k] for k in keys)
        # pandas multi-index lookup handles intentionally missing grain fields.
        try:
            reference = baseline.loc[lookup]
        except KeyError:
            continue
        if isinstance(reference, pd.DataFrame):
            raise ValueError("ambiguous Baseline KPI reference")
        for column in ["Demand_Fulfillment_Rate", "Capacity_Utilization", "Ending_Backlog", "Lost_Sales_Qty"]:
            result.loc[idx, column + "_Change"] = row[column] - reference[column]
    return result
