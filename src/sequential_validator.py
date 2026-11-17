"""Independent checks of sequential results; never imports planning engines."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.planning_inputs import ITEM_KEY, WEEK_KEY, numeric, require_frame, weekly_dates


def validate_sequential_results(
    states: pd.DataFrame,
    pool_results: pd.DataFrame,
    expected_demand: pd.DataFrame,
    expected_pools: pd.DataFrame,
    initial_state: pd.DataFrame,
    receipts: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    quantity_step: float,
) -> pd.DataFrame:
    """Recompute requirements, order, fulfillment and state from source inputs.

    Returns a structured passed-check report; failures raise with the check ID.
    No engine/transition helper is used to manufacture expected results.
    """
    key = ["Scenario"] + WEEK_KEY
    columns = ["Beginning_Inventory", "Beginning_Backlog", "Beginning_Opening_Backlog",
               "Required_Production_Qty", "Internal_Production_Qty", "Allocated_Workload",
               "External_Receipts_Qty", "Ending_Inventory", "Ending_Backlog",
               "Fulfilled_Current_Qty", "Fulfilled_Backlog_Qty",
               "Fulfilled_Opening_Backlog_Qty", "Fulfilled_Horizon_Backlog_Qty",
               "Ending_Opening_Backlog", "Ending_Horizon_Backlog",
               "Current_Unfulfilled_Qty", "Lost_Sales_Qty", "Unmet_Production_Qty",
               "Unmet_Workload", "Remaining_Workload_After_Row"]
    actual = weekly_dates(states)
    source = weekly_dates(expected_demand)
    supplied_pools = weekly_dates(expected_pools)
    pools = weekly_dates(pool_results)
    arrivals = weekly_dates(receipts)
    require_frame(actual, key + columns, key, "sequential result")
    require_frame(pools, ["Scenario", "Plant_ID", "Order_Date", "Allocated_Workload", "Available_Workload_Capacity"], ["Scenario", "Plant_ID", "Order_Date"], "pool result")
    numeric(actual, columns)
    numeric(pools, ["Allocated_Workload", "Available_Workload_Capacity", "Remaining_Workload_Capacity", "Unmet_Workload"])
    report = []

    def check(check_id: str, condition: bool, message: str, checked_rows: int) -> None:
        if not condition:
            raise ValueError(f"{check_id}: {message}")
        report.append({"Check_ID": check_id, "Passed": True, "Rows_Checked": checked_rows, "Message": message})

    def close(a: float, b: float) -> bool:
        return bool(np.isclose(a, b, rtol=1e-10, atol=1e-8))

    check("SEQ-IDENTITY", set(actual[key].itertuples(index=False, name=None)) == set(source[key].itertuples(index=False, name=None)), "preserve exact source scenario/product/week identity", len(actual))
    left = actual.set_index(key).sort_index()
    right = source.set_index(key).sort_index()
    for column in source.columns.difference(key):
        if column not in actual:
            raise ValueError(f"SEQ-SOURCE: missing preserved field {column}")
        a, b = left[column], right[column]
        if pd.api.types.is_numeric_dtype(b):
            same = np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), rtol=1e-10, atol=1e-8, equal_nan=False)
        else:
            same = a.equals(b)
        check("SEQ-SOURCE", bool(same), f"preserve {column}", len(actual))
    pool_key = ["Scenario", "Plant_ID", "Order_Date"]
    check("SEQ-POOL-IDENTITY", set(pools[pool_key].itertuples(index=False, name=None)) == set(supplied_pools[pool_key].itertuples(index=False, name=None)), "preserve unique pool identities", len(pools))
    pool_lookup = supplied_pools.set_index(pool_key)
    result_pools = pools.set_index(pool_key)
    for column in supplied_pools.columns.difference(pool_key):
        check("SEQ-POOL-SOURCE", column in pools.columns, f"pool source column {column} present", len(pools))
        original = pool_lookup[column].sort_index()
        candidate = result_pools[column].sort_index()
        same = np.allclose(candidate.to_numpy(dtype=float), original.to_numpy(dtype=float), rtol=1e-10, atol=1e-8) if pd.api.types.is_numeric_dtype(original) else candidate.equals(original)
        check("SEQ-POOL-SOURCE", bool(same), f"pool source column {column} preserved", len(pools))

    factor_lookup = factors.set_index("Product Card Id")
    initial = initial_state.set_index(ITEM_KEY)
    for scenario, group in actual.groupby("Scenario", sort=True):
        policies = source[source.Scenario.eq(scenario)].Backlog_Policy.unique()
        check("SEQ-POLICY", len(policies) == 1 and policies[0] in {"LOST_SALES", "CARRY_FORWARD"}, "explicit consistent source policy", len(group))
        policy = policies[0]
        delivery = arrivals if "Scenario" not in arrivals else arrivals[arrivals.Scenario.eq(scenario)]
        receipt_lookup = delivery.groupby(WEEK_KEY).External_Receipts_Qty.sum().to_dict()
        previous = {}
        for (week, plant), sub in group.groupby(["Order_Date", "Plant_ID"], sort=True):
            capacity = float(pool_lookup.loc[(scenario, plant, week), "Available_Workload_Capacity"])
            expected = []
            for _, row in sub.iterrows():
                product = row["Product Card Id"]
                identity = (plant, product)
                opening = previous.get(identity)
                if opening is None:
                    init = initial.loc[identity]
                    opening = (float(init.Beginning_Inventory), float(init.Beginning_Backlog), float(init.Beginning_Backlog))
                inventory, backlog, old_origin = opening
                receipt = float(receipt_lookup.get((plant, product, week), 0))
                q = float(row.Scenario_Qualified_Demand)
                requirement = max(backlog + q - inventory - receipt, 0)
                factor = float(factor_lookup.loc[product, "Workload_Factor"])
                check("SEQ-OPENING", close(row.Beginning_Inventory, inventory) and close(row.Beginning_Backlog, backlog) and close(row.Beginning_Opening_Backlog, old_origin), "opening state continuity", 1)
                check("SEQ-RECEIPT", close(row.External_Receipts_Qty, receipt), "declared available-week receipts only", 1)
                check("SEQ-REQUIREMENT", close(row.Required_Production_Qty, requirement), "independent uncovered-obligation requirement", 1)
                check("SEQ-FACTOR", close(row.Workload_Factor, factor) and row.Factor_Version == factor_lookup.loc[product, "Factor_Version"] and row.Workload_Unit == factor_lookup.loc[product, "Workload_Unit"], "factor value/unit/version from source", 1)
                expected.append((int(row.Planning_Priority), requirement, product, row, inventory, backlog, old_origin, receipt, factor))
            expected.sort(key=lambda x: (-x[0], -x[1], x[2]))
            remaining = capacity
            used, unmet = 0.0, 0.0
            for order, (_, requirement, product, row, inventory, backlog, old_origin, receipt, factor) in enumerate(expected, 1):
                quantity = min(requirement, remaining / factor)
                if quantity_step:
                    quantity = math.floor(math.nextafter(quantity / quantity_step, math.inf)) * quantity_step
                load = quantity * factor
                remaining = max(remaining - load, 0)
                check("SEQ-ALLOCATION", row.Allocation_Order == order and close(row.Internal_Production_Qty, quantity) and close(row.Allocated_Workload, load) and close(row.Remaining_Workload_After_Row, remaining), "independent priority and greedy workload allocation", 1)
                supply = inventory + receipt + quantity
                fback = min(backlog, supply)
                fopening = min(old_origin, fback)
                fcurrent = min(float(row.Scenario_Qualified_Demand), supply - fback)
                unfilled = float(row.Scenario_Qualified_Demand) - fcurrent
                end_stock = supply - fback - fcurrent
                end_backlog = backlog - fback + unfilled if policy == "CARRY_FORWARD" else 0
                losses = unfilled if policy == "LOST_SALES" else 0
                expected_values = {
                    "Fulfilled_Backlog_Qty": fback, "Fulfilled_Current_Qty": fcurrent,
                    "Fulfilled_Opening_Backlog_Qty": fopening, "Fulfilled_Horizon_Backlog_Qty": fback - fopening,
                    "Current_Unfulfilled_Qty": unfilled, "Ending_Inventory": end_stock,
                    "Ending_Backlog": end_backlog, "Lost_Sales_Qty": losses,
                    "Ending_Opening_Backlog": old_origin - fopening,
                    "Ending_Horizon_Backlog": end_backlog - (old_origin - fopening),
                    "Unmet_Production_Qty": requirement - quantity, "Unmet_Workload": (requirement - quantity) * factor,
                }
                check("SEQ-CONSERVATION", all(close(float(row[k]), v) for k, v in expected_values.items()), "independent stock, obligation and cohort fulfillment balances", 1)
                if policy == "LOST_SALES":
                    check("SEQ-LOSS-MODE", backlog == 0 and row.Fulfilled_Backlog_Qty == 0, "loss mode has no carried obligations", 1)
                previous[(plant, product)] = (end_stock, end_backlog, old_origin - fopening)
                used += load
                unmet += (requirement - quantity) * factor
            candidate = result_pools.loc[(scenario, plant, week)]
            check("SEQ-POOL", close(candidate.Available_Workload_Capacity, capacity) and close(candidate.Allocated_Workload, used) and close(candidate.Remaining_Workload_Capacity, capacity - used) and close(candidate.Unmet_Workload, unmet) and used <= capacity + 1e-8 and bool(candidate.Workload_Shortage) == (unmet > 1e-9), "unique shared workload pool balances", len(sub))
    return pd.DataFrame(report).groupby(["Check_ID", "Message"], as_index=False, sort=True).agg(Passed=("Passed", "all"), Rows_Checked=("Rows_Checked", "sum"))
