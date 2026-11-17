"""Source-preserving dual demand and explicit extract-coverage preparation."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from src.planning_inputs import ITEM_KEY, WEEK_KEY, horizon, numeric, require_frame, weekly_dates

DATACO_REFERENCE_EXCLUSIONS = {"CANCELED", "SUSPECTED_FRAUD"}


def prepare_demand(
    orders: pd.DataFrame,
    product_plant_mapping: pd.DataFrame,
    status_mapping: Mapping[str, bool],
    *,
    eligibility_version: str,
    source_is_complete: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compatibility adapter for the former DataCo-reference input API.

    The source-independent CSV adapter uses prepare_order_demand instead;
    cancellation/fraud status names are not universal engine business rules.
    """
    if any(status_mapping.get(status, False) for status in DATACO_REFERENCE_EXCLUSIONS):
        raise ValueError("CANCELED and SUSPECTED_FRAUD must be excluded")
    return prepare_order_demand(
        orders, product_plant_mapping, status_mapping,
        eligibility_version=eligibility_version, source_is_complete=source_is_complete,
    )


def prepare_order_demand(
    orders: pd.DataFrame,
    product_plant_mapping: pd.DataFrame,
    status_mapping: Mapping[str, bool],
    *,
    eligibility_version: str,
    source_is_complete: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prepare mapped order lines with caller-defined status semantics only.

    Historical field labels are accepted for compatibility at this adapter
    boundary; weekly canonical facts and the planning engine are source-neutral.
    """
    required = ["Order Item Id", "Product Card Id", "Order Status", "order date (DateOrders)", "Order Item Quantity"]
    require_frame(orders, required, ["Order Item Id"], "orders")
    require_frame(product_plant_mapping, ITEM_KEY, ["Product Card Id"], "product mapping")
    numeric(orders, ["Order Item Quantity"])
    if orders.empty or not eligibility_version or type(source_is_complete) is not bool:
        raise ValueError("nonempty orders, eligibility version and explicit completeness bool required")
    statuses = set(orders["Order Status"].dropna())
    if orders["Order Status"].isna().any() or statuses - set(status_mapping):
        raise ValueError(f"unresolved status eligibility: {sorted(statuses - set(status_mapping))}")
    if any(type(v) is not bool for v in status_mapping.values()):
        raise ValueError("status mapping values must be explicit booleans")
    source_dates = pd.to_datetime(orders["order date (DateOrders)"], errors="coerce")
    if source_dates.isna().any():
        raise ValueError("invalid source Order Date")
    source = orders[required].copy(deep=True)
    source["Source_Order_Date"] = source_dates
    source["Order_Date"] = source_dates.dt.to_period("W-SUN").dt.end_time.dt.normalize()
    ledger = source.merge(product_plant_mapping[ITEM_KEY], on="Product Card Id", how="left", validate="many_to_one")
    if ledger["Plant_ID"].isna().any():
        raise ValueError("source product missing plant mapping")
    ledger["Is_Qualified"] = ledger["Order Status"].map(status_mapping)
    ledger["Exclusion_Reason"] = ledger["Order Status"].where(~ledger["Is_Qualified"], "")
    ledger["Eligibility_Version"] = eligibility_version
    ledger["Gross_Demand"] = ledger["Order Item Quantity"]
    ledger["Qualified_Demand"] = ledger["Gross_Demand"].where(ledger["Is_Qualified"], 0)
    ledger["Excluded_Demand"] = ledger["Gross_Demand"] - ledger["Qualified_Demand"]
    values = ["Gross_Demand", "Qualified_Demand", "Excluded_Demand"]
    grouped = ledger.groupby(WEEK_KEY, sort=True)[values].sum().reset_index()
    min_day, max_day = source_dates.min().normalize(), source_dates.max().normalize()
    rows = []
    for _, group in grouped.groupby(ITEM_KEY, sort=True):
        if source_is_complete:
            weeks = pd.date_range(group.Order_Date.min(), group.Order_Date.max(), freq="W-SUN")
            expanded = group.set_index("Order_Date").reindex(weeks)
            expanded["Plant_ID"] = group.Plant_ID.iloc[0]
            expanded["Product Card Id"] = group["Product Card Id"].iloc[0]
            expanded[values] = expanded[values].fillna(0)
            expanded.index.name = "Order_Date"
            group = expanded.reset_index()
        group = group.copy()
        group["Coverage_Status"] = group["Qualified_Demand"].gt(0).map(
            {True: "OBSERVED_DEMAND", False: "OBSERVED_ZERO"}
        )
        complete_week = (group.Order_Date - pd.Timedelta(days=6) >= min_day) & (group.Order_Date <= max_day)
        group.loc[~complete_week, "Coverage_Status"] = "UNKNOWN"
        rows.append(group)
    demand = pd.concat(rows, ignore_index=True).sort_values(WEEK_KEY).reset_index(drop=True)
    demand["Coverage_Basis"] = "COMPLETE_EXTRACT_WITHIN_OBSERVED_LIFESPAN" if source_is_complete else "EXPLICIT_SOURCE_ORDERS_ONLY"
    demand["Eligibility_Version"] = eligibility_version
    return ledger, demand


def build_demand_coverage(
    demand: pd.DataFrame, items: pd.DataFrame, start: object, end: object
) -> pd.DataFrame:
    """Build a small state-calendar view without inventing sparse demand facts.

    Missing rows in the supplied horizon are UNKNOWN. Supplied rows outside it
    are OUT_OF_SCOPE. The source demand frame is never densified in place.
    """
    source = weekly_dates(demand)
    require_frame(source, WEEK_KEY + ["Coverage_Status"], WEEK_KEY, "weekly demand")
    require_frame(items, ITEM_KEY, ITEM_KEY, "planning items")
    weeks = horizon(start, end)
    index = pd.MultiIndex.from_tuples(
        [(plant, product, week) for plant, product in items[ITEM_KEY].itertuples(index=False, name=None) for week in weeks],
        names=WEEK_KEY,
    )
    result = source.set_index(WEEK_KEY).reindex(index).reset_index()
    result["Coverage_Status"] = result["Coverage_Status"].fillna("UNKNOWN")
    # OUT_OF_SCOPE labels are informative only; they are not simulated.
    outside = source[(source.Order_Date < weeks[0]) | (source.Order_Date > weeks[-1])].merge(items[ITEM_KEY], on=ITEM_KEY)
    outside = outside.copy()
    outside["Coverage_Status"] = "OUT_OF_SCOPE"
    return pd.concat([result, outside], ignore_index=True).sort_values(WEEK_KEY).reset_index(drop=True)
