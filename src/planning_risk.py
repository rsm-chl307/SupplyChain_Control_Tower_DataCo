"""Presentation-level risk summaries derived from published sequential outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required risk fields: {', '.join(missing)}")


def _require_finite_values(frame: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
    """Return a copy with numeric columns parsed, rejecting missing/invalid values."""
    result = frame.copy()
    for column in columns:
        parsed = pd.to_numeric(result[column], errors="coerce")
        invalid = parsed.isna() | ~np.isfinite(parsed)
        if invalid.any():
            raise ValueError(f"{label} contains missing or non-finite values in {column}")
        result[column] = parsed
    return result


def product_risk_ranking(allocation: pd.DataFrame) -> pd.DataFrame:
    """Rank products by explicit service, backlog, loss, and production signals.

    Flows are summed across weeks. Ending stock/backlog is taken only from each
    Plant × Product's final week, then summed across plants. Rates use the same
    horizon-origin definitions as ``src.kpi_engine``.
    """
    required = [
        "Scenario", "Plant_ID", "Product Card Id", "Product Name", "Order_Date",
        "Planning_Priority", "Scenario_Qualified_Demand", "Required_Production_Qty",
        "Internal_Production_Qty", "Fulfilled_Current_Qty", "Fulfilled_Horizon_Backlog_Qty",
        "Current_Unfulfilled_Qty", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty",
        "Allocated_Workload", "Unmet_Workload", "Workload_Factor", "Beginning_Inventory",
        "Workload_Unit", "Beginning_Backlog", "Allocation_Order", "Backlog_Policy",
    ]
    _require_columns(allocation, required, "allocation_result")
    if allocation.empty:
        return pd.DataFrame()

    numeric_fields = [
        "Planning_Priority", "Scenario_Qualified_Demand", "Required_Production_Qty",
        "Internal_Production_Qty", "Fulfilled_Current_Qty", "Fulfilled_Horizon_Backlog_Qty",
        "Current_Unfulfilled_Qty", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty",
        "Allocated_Workload", "Unmet_Workload", "Workload_Factor", "Beginning_Inventory",
        "Beginning_Backlog", "Allocation_Order",
    ]
    source = _require_finite_values(allocation, numeric_fields, "allocation_result")
    source["Order_Date"] = pd.to_datetime(source["Order_Date"], errors="coerce")
    if source.Order_Date.isna().any():
        raise ValueError("allocation_result contains invalid Order_Date values")
    group_keys = ["Scenario", "Product Card Id"]
    for column in ["Product Name", "Planning_Priority", "Workload_Factor", "Backlog_Policy"]:
        if source.groupby(group_keys, dropna=False)[column].nunique(dropna=False).gt(1).any():
            raise ValueError(f"allocation_result has inconsistent {column} within a product scenario")

    flows = source.groupby(group_keys, as_index=False, sort=True, dropna=False).agg(
        Product_Name=("Product Name", "first"),
        Planning_Priority=("Planning_Priority", "first"),
        Backlog_Policy=("Backlog_Policy", "first"),
        Qualified_Demand=("Scenario_Qualified_Demand", "sum"),
        Required_Production_Qty=("Required_Production_Qty", "sum"),
        Internal_Production_Qty=("Internal_Production_Qty", "sum"),
        Fulfilled_Current_Qty=("Fulfilled_Current_Qty", "sum"),
        Fulfilled_Horizon_Backlog_Qty=("Fulfilled_Horizon_Backlog_Qty", "sum"),
        Current_Demand_Unfulfilled_Qty=("Current_Unfulfilled_Qty", "sum"),
        Lost_Sales_Qty=("Lost_Sales_Qty", "sum"),
        Allocated_Workload=("Allocated_Workload", "sum"),
        Unmet_Workload=("Unmet_Workload", "sum"),
        Workload_Factor=("Workload_Factor", "first"),
        Workload_Unit=("Workload_Unit", "first"),
        Plants=("Plant_ID", lambda values: ", ".join(sorted(set(values.astype(str))))),
    )

    per_plant_product = source.sort_values("Order_Date").groupby(
        ["Scenario", "Plant_ID", "Product Card Id"], sort=False, dropna=False
    )
    openings = per_plant_product.head(1).groupby(group_keys, as_index=False, sort=True, dropna=False).agg(
        Opening_Inventory_Qty=("Beginning_Inventory", "sum"),
        Opening_Backlog_Qty=("Beginning_Backlog", "sum"),
    )
    endings = per_plant_product.tail(1).groupby(group_keys, as_index=False, sort=True, dropna=False).agg(
        Ending_Inventory=("Ending_Inventory", "sum"),
        Ending_Backlog=("Ending_Backlog", "sum"),
    )
    result = flows.merge(openings, on=group_keys, validate="one_to_one").merge(
        endings, on=group_keys, validate="one_to_one"
    )
    numerator = result.Fulfilled_Current_Qty + result.Fulfilled_Horizon_Backlog_Qty
    result["Demand_Fulfillment_Rate"] = numerator.div(result.Qualified_Demand.where(result.Qualified_Demand.ne(0)))
    result["Production_Coverage_Rate"] = result.Internal_Production_Qty.div(
        result.Required_Production_Qty.where(result.Required_Production_Qty.ne(0))
    )

    at_risk = (
        result.Current_Demand_Unfulfilled_Qty.gt(1e-9)
        | result.Ending_Backlog.gt(1e-9)
        | result.Lost_Sales_Qty.gt(1e-9)
        | result.Demand_Fulfillment_Rate.lt(1 - 1e-9)
    )
    watch = ~at_risk & (
        result.Production_Coverage_Rate.lt(1 - 1e-9)
        | ((result.Qualified_Demand.gt(0)) & result.Ending_Inventory.le(1e-9))
    )
    result["Risk_Category"] = np.select([at_risk, watch], ["At Risk", "Watch"], default="Healthy")
    result["Risk_Reason"] = result.apply(_product_risk_reason, axis=1)
    result["_Risk_Order"] = result.Risk_Category.map({"At Risk": 0, "Watch": 1, "Healthy": 2})
    return result.sort_values(
        ["_Risk_Order", "Current_Demand_Unfulfilled_Qty", "Ending_Backlog", "Lost_Sales_Qty",
         "Demand_Fulfillment_Rate", "Planning_Priority", "Product Card Id"],
        ascending=[True, False, False, False, True, False, True], na_position="last", kind="mergesort",
    ).drop(columns="_Risk_Order").reset_index(drop=True)


def _product_risk_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if row.Current_Demand_Unfulfilled_Qty > 1e-9:
        reasons.append(f"{row.Current_Demand_Unfulfilled_Qty:g} units were not fulfilled in their demand week")
    if row.Ending_Backlog > 1e-9:
        reasons.append(f"{row.Ending_Backlog:g} units of backlog remain at horizon end")
    if row.Lost_Sales_Qty > 1e-9:
        reasons.append(f"{row.Lost_Sales_Qty:g} units are lost sales")
    if pd.notna(row.Demand_Fulfillment_Rate) and row.Demand_Fulfillment_Rate < 1 - 1e-9:
        reasons.append(f"horizon demand fulfillment is {row.Demand_Fulfillment_Rate:.1%}")
    if row.Unmet_Workload > 1e-9:
        reasons.append(f"{row.Unmet_Workload:g} {row.Workload_Unit} of production requirement was unmet")
    if row.Risk_Category == "Watch" and row.Production_Coverage_Rate < 1 - 1e-9:
        reasons.append("internal production covered less than the calculated requirement; inventory/receipts may have covered demand")
    if row.Risk_Category == "Watch" and row.Qualified_Demand > 0 and row.Ending_Inventory <= 1e-9:
        reasons.append("no inventory remains at horizon end")
    return "; ".join(reasons) if reasons else "No modeled service, backlog, loss, or production-coverage risk signal"


def plant_bottleneck_summary(capacity_pools: pd.DataFrame) -> pd.DataFrame:
    """Summarize unique plant-week pools without counting product rows as capacity."""
    required = ["Scenario", "Plant_ID", "Order_Date", "Available_Workload_Capacity",
                "Allocated_Workload", "Remaining_Workload_Capacity", "Unmet_Workload"]
    _require_columns(capacity_pools, required, "capacity_pools")
    if capacity_pools.empty:
        return pd.DataFrame()
    keys = ["Scenario", "Plant_ID", "Order_Date"]
    if capacity_pools.duplicated(keys).any():
        raise ValueError("capacity_pools must contain one row per Scenario × Plant × Week")
    numeric_fields = ["Available_Workload_Capacity", "Allocated_Workload",
                      "Remaining_Workload_Capacity", "Unmet_Workload"]
    source = _require_finite_values(capacity_pools, numeric_fields, "capacity_pools")
    if "Workload_Shortage" not in source:
        source["Workload_Shortage"] = source.Unmet_Workload.gt(1e-9)
    else:
        source["Workload_Shortage"] = source.Workload_Shortage.where(
            source.Workload_Shortage.notna(), source.Unmet_Workload.gt(1e-9)
        )
    source["Workload_Shortage"] = source.Workload_Shortage.astype(bool)
    summary = source.groupby(["Scenario", "Plant_ID"], as_index=False, sort=True).agg(
        Available_Workload_Capacity=("Available_Workload_Capacity", "sum"),
        Allocated_Workload=("Allocated_Workload", "sum"),
        Remaining_Workload_Capacity=("Remaining_Workload_Capacity", "sum"),
        Unmet_Workload=("Unmet_Workload", "sum"),
        Bottleneck_Weeks=("Workload_Shortage", "sum"),
        Plant_Weeks=("Order_Date", "nunique"),
    )
    summary["Capacity_Utilization"] = summary.Allocated_Workload.div(
        summary.Available_Workload_Capacity.where(summary.Available_Workload_Capacity.ne(0))
    )
    return summary.sort_values(
        ["Scenario", "Bottleneck_Weeks", "Unmet_Workload", "Capacity_Utilization", "Plant_ID"],
        ascending=[True, False, False, False, True], na_position="last", kind="mergesort",
    ).reset_index(drop=True)


def risk_driver_details(allocation: pd.DataFrame, capacity_pools: pd.DataFrame) -> pd.DataFrame:
    """Join product-week outcomes to shared plant-week context for drill-down."""
    allocation_fields = ["Scenario", "Plant_ID", "Product Card Id", "Order_Date", "Product Name",
                         "Planning_Priority", "Scenario_Qualified_Demand", "Incremental_Demand",
                         "Beginning_Inventory", "Beginning_Backlog", "Workload_Factor", "Allocation_Order",
                         "Workload_Unit",
                         "Required_Production_Qty", "Internal_Production_Qty", "Unmet_Production_Qty",
                         "Allocated_Workload", "Unmet_Workload", "Ending_Backlog", "Lost_Sales_Qty",
                         "Current_Unfulfilled_Qty"]
    pool_fields = ["Scenario", "Plant_ID", "Order_Date", "Baseline_Workload_Capacity",
                   "Available_Workload_Capacity", "Allocated_Workload", "Remaining_Workload_Capacity",
                   "Unmet_Workload"]
    _require_columns(allocation, allocation_fields, "allocation_result")
    _require_columns(capacity_pools, pool_fields, "capacity_pools")
    allocation_numeric = ["Planning_Priority", "Scenario_Qualified_Demand", "Incremental_Demand",
                          "Beginning_Inventory", "Beginning_Backlog", "Workload_Factor",
                          "Allocation_Order", "Required_Production_Qty", "Internal_Production_Qty",
                          "Unmet_Production_Qty", "Allocated_Workload", "Unmet_Workload",
                          "Ending_Backlog", "Lost_Sales_Qty", "Current_Unfulfilled_Qty"]
    allocation = _require_finite_values(allocation, allocation_numeric, "allocation_result")
    pool_numeric = ["Baseline_Workload_Capacity", "Available_Workload_Capacity", "Allocated_Workload",
                    "Remaining_Workload_Capacity", "Unmet_Workload"]
    capacity_pools = _require_finite_values(capacity_pools, pool_numeric, "capacity_pools")
    keys = ["Scenario", "Plant_ID", "Order_Date"]
    if capacity_pools.duplicated(keys).any():
        raise ValueError("capacity_pools must contain one row per Scenario × Plant × Week")
    product = allocation[allocation_fields].rename(columns={
        "Unmet_Workload": "Product_Unmet_Workload",
        "Allocated_Workload": "Product_Allocated_Workload",
    })
    pools = capacity_pools[pool_fields].rename(columns={
        "Allocated_Workload": "Plant_Week_Allocated_Workload",
        "Unmet_Workload": "Plant_Week_Unmet_Workload",
    })
    result = product.merge(pools, on=keys, how="left", validate="many_to_one")
    result["Plant_Week_Capacity_Utilization"] = result.Plant_Week_Allocated_Workload.div(
        result.Available_Workload_Capacity.where(result.Available_Workload_Capacity.ne(0))
    )
    result["Capacity_Reduction_From_Baseline"] = (
        result.Baseline_Workload_Capacity - result.Available_Workload_Capacity
    ).clip(lower=0)
    pool_available = result.Plant_Week_Unmet_Workload.notna()
    result["Capacity_Shortage"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result.loc[pool_available, "Capacity_Shortage"] = result.loc[
        pool_available, "Plant_Week_Unmet_Workload"
    ].gt(1e-9)
    result["Risk_Signals"] = result.apply(_risk_signals, axis=1)
    return result.sort_values(
        ["Scenario", "Plant_Week_Unmet_Workload", "Product_Unmet_Workload", "Incremental_Demand",
         "Order_Date", "Allocation_Order"],
        ascending=[True, False, False, False, True, True], na_position="last", kind="mergesort",
    ).reset_index(drop=True)


def _risk_signals(row: pd.Series) -> str:
    signals: list[str] = []
    if pd.isna(row.Plant_Week_Unmet_Workload):
        signals.append("Plant-week capacity pool is unavailable")
    elif row.Plant_Week_Unmet_Workload > 1e-9:
        signals.append("Plant-week capacity pool had unmet workload")
    if row.Capacity_Reduction_From_Baseline > 1e-9:
        signals.append("Scenario capacity is below the run baseline")
    if row.Incremental_Demand > 1e-9:
        signals.append("Scenario demand exceeds baseline demand")
    if row.Beginning_Backlog > 1e-9:
        signals.append("Backlog was already open at the start of this week")
    if row.Beginning_Inventory <= 1e-9 and row.Scenario_Qualified_Demand > 0:
        signals.append("No inventory was available at the start of this week")
    signals.append(f"Workload factor: {row.Workload_Factor:g} workload units per product unit")
    signals.append(f"Priority: {row.Planning_Priority}; allocation order: {row.Allocation_Order}")
    return "; ".join(signals)


def scenario_risk_comparison(performance: pd.DataFrame) -> pd.DataFrame:
    """Present existing scenario KPIs and explicit Baseline deltas."""
    required = ["Aggregation_Level", "Scenario", "Scenario_Qualified_Demand", "Demand_Fulfillment_Rate",
                "Production_Coverage_Rate", "Ending_Backlog", "Lost_Sales_Qty", "Capacity_Utilization"]
    _require_columns(performance, required, "performance_result")
    optional = [column for column in ["Backlog_Policy", "Bottleneck_Plant_Weeks", "Gross_Demand", "Excluded_Demand"]
                if column in performance]
    rows = performance.loc[performance.Aggregation_Level.eq("Scenario"), required[1:] + optional].copy()
    baseline = rows.loc[rows.Scenario.eq("Baseline")]
    delta_fields = ["Scenario_Qualified_Demand", "Demand_Fulfillment_Rate", "Production_Coverage_Rate",
                    "Ending_Backlog", "Lost_Sales_Qty", "Capacity_Utilization", "Bottleneck_Plant_Weeks"]
    for field in delta_fields:
        if field not in rows:
            continue
        change = field + "_Change"
        rows[change] = np.nan
        if not baseline.empty:
            rows[change] = rows[field] - float(baseline.iloc[0][field])
    return rows.sort_values("Scenario", kind="mergesort").reset_index(drop=True)


def scenario_product_deterioration(product_risk: pd.DataFrame, scenario: str,
                                   baseline: str = "Baseline") -> pd.DataFrame:
    """Compare existing product-level outcomes for one scenario against Baseline."""
    if product_risk.empty or scenario == baseline:
        return pd.DataFrame()
    _require_columns(product_risk, ["Scenario", "Product Card Id", "Demand_Fulfillment_Rate",
                                   "Ending_Backlog", "Lost_Sales_Qty"], "product risk summary")
    base = product_risk.loc[product_risk.Scenario.eq(baseline)].set_index("Product Card Id")
    current = product_risk.loc[product_risk.Scenario.eq(scenario)].copy()
    if base.empty or current.empty:
        return pd.DataFrame()
    reference = base[["Demand_Fulfillment_Rate", "Ending_Backlog", "Lost_Sales_Qty"]].rename(columns={
        "Demand_Fulfillment_Rate": "Baseline_Demand_Fulfillment_Rate",
        "Ending_Backlog": "Baseline_Ending_Backlog",
        "Lost_Sales_Qty": "Baseline_Lost_Sales_Qty",
    })
    current = current.join(reference, on="Product Card Id", how="left", validate="many_to_one")
    if "Backlog_Policy" in current and "Backlog_Policy" in base:
        policy = base.Backlog_Policy.rename("Baseline_Backlog_Policy")
        current = current.join(policy, on="Product Card Id", how="left", validate="many_to_one")
        current["Backlog_Policy_Changed"] = current.Backlog_Policy.ne(current.Baseline_Backlog_Policy)
    else:
        current["Baseline_Backlog_Policy"] = "Unavailable"
        current["Backlog_Policy_Changed"] = False
    current["Demand_Fulfillment_Change"] = current.Demand_Fulfillment_Rate - current.Baseline_Demand_Fulfillment_Rate
    current["Ending_Backlog_Change"] = current.Ending_Backlog - current.Baseline_Ending_Backlog
    current["Lost_Sales_Change"] = current.Lost_Sales_Qty - current.Baseline_Lost_Sales_Qty
    return current.sort_values(
        ["Demand_Fulfillment_Change", "Ending_Backlog_Change", "Lost_Sales_Change", "Planning_Priority"],
        ascending=[True, False, False, False], na_position="last", kind="mergesort",
    ).reset_index(drop=True)


def scenario_plant_deterioration(performance: pd.DataFrame, scenario: str,
                                 baseline: str = "Baseline") -> pd.DataFrame:
    """Compare existing plant KPI rows for one scenario against Baseline."""
    if scenario == baseline:
        return pd.DataFrame()
    fields = ["Scenario", "Plant_ID", "Demand_Fulfillment_Rate", "Production_Coverage_Rate",
              "Ending_Backlog", "Lost_Sales_Qty", "Capacity_Utilization"]
    optional = [column for column in ["Backlog_Policy", "Bottleneck_Plant_Weeks"] if column in performance]
    fields.extend(optional)
    _require_columns(performance, ["Aggregation_Level", *fields], "performance_result")
    rows = performance.loc[performance.Aggregation_Level.eq("Scenario × Plant"), fields]
    base = rows.loc[rows.Scenario.eq(baseline)].set_index("Plant_ID")
    current = rows.loc[rows.Scenario.eq(scenario)].copy()
    if base.empty or current.empty:
        return pd.DataFrame()
    compare_metrics = ["Demand_Fulfillment_Rate", "Production_Coverage_Rate", "Ending_Backlog",
                       "Lost_Sales_Qty", "Capacity_Utilization"]
    if "Bottleneck_Plant_Weeks" in base:
        compare_metrics.append("Bottleneck_Plant_Weeks")
    reference = base[compare_metrics].rename(columns={
        column: f"Baseline_{column}" for column in compare_metrics
    })
    current = current.join(reference, on="Plant_ID", how="left", validate="many_to_one")
    if "Backlog_Policy" in current:
        policy = base.Backlog_Policy.rename("Baseline_Backlog_Policy")
        current = current.join(policy, on="Plant_ID", how="left", validate="many_to_one")
        current["Backlog_Policy_Changed"] = current.Backlog_Policy.ne(current.Baseline_Backlog_Policy)
    else:
        current["Baseline_Backlog_Policy"] = "Unavailable"
        current["Backlog_Policy_Changed"] = False
    for column in ["Demand_Fulfillment_Rate", "Production_Coverage_Rate", "Ending_Backlog",
                   "Lost_Sales_Qty", "Capacity_Utilization"]:
        current[f"{column}_Change"] = current[column] - current[f"Baseline_{column}"]
    if "Bottleneck_Plant_Weeks" in current:
        current["Bottleneck_Plant_Weeks_Change"] = current.Bottleneck_Plant_Weeks - current.Baseline_Bottleneck_Plant_Weeks
    return current.sort_values(
        ["Demand_Fulfillment_Rate_Change", "Ending_Backlog_Change", "Lost_Sales_Qty_Change", "Plant_ID"],
        ascending=[True, False, False, True], na_position="last", kind="mergesort",
    ).reset_index(drop=True)
