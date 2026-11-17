"""Focused sequential planning orchestration; no CSV I/O or hidden supply."""

from __future__ import annotations

import pandas as pd

from src.allocation_engine import allocate_workload
from src.inventory_engine import transition_inventory
from src.planning_inputs import ITEM_KEY, WEEK_KEY, WORKLOAD_ALLOCATION_POLICY, horizon, numeric, require_frame, weekly_dates
from src.workload_model import validate_workload_factors

ALLOCATION_POLICY = WORKLOAD_ALLOCATION_POLICY


def simulate_sequential(
    demand: pd.DataFrame,
    capacity_pools: pd.DataFrame,
    initial_state: pd.DataFrame,
    receipts: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    quantity_step: float,
    allocation_policy: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run isolated chronological scenarios with the retained product priority.

    All quantities are product units. Capacity/debits are equivalent workload.
    Receipts are explicitly usable in their declared Order_Date week.
    No product starts, unknown-demand filling or weekly stock resets are inferred.
    """
    if allocation_policy != ALLOCATION_POLICY:
        raise ValueError("unapproved/unsupported cross-product allocation policy")
    source = weekly_dates(demand)
    pools = weekly_dates(capacity_pools)
    deliveries = weekly_dates(receipts)
    require_frame(source, ["Scenario", "Backlog_Policy", "Scenario_Qualified_Demand", "Coverage_Status", "Planning_Priority"] + WEEK_KEY, ["Scenario"] + WEEK_KEY, "sequential demand")
    require_frame(pools, ["Scenario", "Plant_ID", "Order_Date", "Available_Workload_Capacity"], ["Scenario", "Plant_ID", "Order_Date"], "workload pools")
    require_frame(initial_state, ITEM_KEY + ["Beginning_Inventory", "Beginning_Backlog"], ITEM_KEY, "initial state")
    receipt_key = ["Scenario", "Receipt_ID"] if "Scenario" in deliveries else ["Receipt_ID"]
    require_frame(deliveries, ["Receipt_ID", "External_Receipts_Qty"] + WEEK_KEY, receipt_key, "external receipts")
    numeric(source, ["Scenario_Qualified_Demand", "Planning_Priority"])
    numeric(pools, ["Available_Workload_Capacity"])
    numeric(initial_state, ["Beginning_Inventory", "Beginning_Backlog"])
    numeric(deliveries, ["External_Receipts_Qty"])
    if source.empty or initial_state.empty:
        raise ValueError("nonempty demand and explicit opening state required")
    if not source.Coverage_Status.isin(["OBSERVED_ZERO", "OBSERVED_DEMAND"]).all():
        raise ValueError("UNKNOWN or OUT_OF_SCOPE demand cannot be simulated")
    if (source.Coverage_Status.eq("OBSERVED_ZERO") & source.Scenario_Qualified_Demand.ne(0)).any():
        raise ValueError("OBSERVED_ZERO must have zero demand")
    if not source.Planning_Priority.isin([1, 2, 3]).all():
        raise ValueError("priority must be 1, 2 or 3")
    if source.groupby(["Scenario"] + ITEM_KEY).Planning_Priority.nunique().gt(1).any():
        raise ValueError("changing product priority within a trajectory is outside scope")
    validate_workload_factors(factors, set(source["Product Card Id"]))
    scenarios = sorted(source.Scenario.unique())
    if set(pools.Scenario) != set(scenarios):
        raise ValueError("capacity and demand scenarios must match")
    if "Scenario" in deliveries and set(deliveries.Scenario) - set(scenarios):
        raise ValueError("receipt references an unknown scenario")
    weeks = horizon(source.Order_Date.min(), source.Order_Date.max())
    items = set(initial_state[ITEM_KEY].itertuples(index=False, name=None))
    plants = {p for p, _ in items}
    expected_pool_keys = {(scenario, plant, week) for scenario in scenarios for plant in plants for week in weeks}
    if set(pools[["Scenario", "Plant_ID", "Order_Date"]].itertuples(index=False, name=None)) != expected_pool_keys:
        raise ValueError("missing or extra scenario plant-week capacity pool")
    for scenario, group in source.groupby("Scenario"):
        expected = {(plant, product, week) for plant, product in items for week in weeks}
        if set(group[WEEK_KEY].itertuples(index=False, name=None)) != expected:
            raise ValueError(f"{scenario}: every initialized item needs explicit full-horizon coverage")
        if group.Backlog_Policy.nunique() != 1 or group.Backlog_Policy.iloc[0] not in {"LOST_SALES", "CARRY_FORWARD"}:
            raise ValueError("one explicit backlog policy required per scenario")
        if group.Backlog_Policy.iloc[0] == "LOST_SALES" and initial_state.Beginning_Backlog.ne(0).any():
            raise ValueError("LOST_SALES cannot accept opening backlog")
    if any((plant, product) not in items or week not in weeks for plant, product, week in deliveries[WEEK_KEY].itertuples(index=False, name=None)):
        raise ValueError("receipt outside declared planning items/horizon")
    resolved = source.merge(factors[["Product Card Id", "Workload_Factor", "Factor_Version", "Workload_Unit"]], on="Product Card Id", validate="many_to_one")
    if "Workload_Unit" in pools and set(pools.Workload_Unit) != set(factors.Workload_Unit):
        raise ValueError("capacity and product workload units must agree")
    if "Factor_Version" in pools and set(pools.Factor_Version) != set(factors.Factor_Version):
        raise ValueError("capacity calibration and factor version must agree")
    if "Workload_Unit" not in pools or "Factor_Version" not in pools:
        raise ValueError("capacity pools require workload unit and factor version")
    state_rows, pool_rows = [], []
    for scenario in scenarios:
        # New dictionary/scalars for every scenario, even when sources are shared.
        state = {
            (row["Plant_ID"], row["Product Card Id"]): (
                float(row["Beginning_Inventory"]), float(row["Beginning_Backlog"]), float(row["Beginning_Backlog"])
            )
            for _, row in initial_state.iterrows()
        }
        receipts_for_scenario = deliveries if "Scenario" not in deliveries else deliveries[deliveries.Scenario.eq(scenario)]
        arrival = receipts_for_scenario.groupby(WEEK_KEY).External_Receipts_Qty.sum().to_dict()
        for week in weeks:
            for plant in sorted(plants):
                group = resolved[(resolved.Scenario == scenario) & (resolved.Order_Date == week) & (resolved.Plant_ID == plant)].copy()
                pool = pools[(pools.Scenario == scenario) & (pools.Order_Date == week) & (pools.Plant_ID == plant)].iloc[0]
                openings = [state[(plant, product)] for product in group["Product Card Id"]]
                group["Beginning_Inventory"] = [s[0] for s in openings]
                group["Beginning_Backlog"] = [s[1] for s in openings]
                group["Beginning_Opening_Backlog"] = [s[2] for s in openings]
                group["External_Receipts_Qty"] = [float(arrival.get((plant, product, week), 0.0)) for product in group["Product Card Id"]]
                group["Required_Production_Qty"] = (
                    group.Beginning_Backlog + group.Scenario_Qualified_Demand
                    - group.Beginning_Inventory - group.External_Receipts_Qty
                ).clip(lower=0)
                allocated = allocate_workload(group, float(pool.Available_Workload_Capacity), quantity_step=quantity_step)
                for _, row in allocated.iterrows():
                    values = transition_inventory(
                        beginning_inventory=float(row.Beginning_Inventory),
                        beginning_backlog=float(row.Beginning_Backlog),
                        opening_origin_backlog=float(row.Beginning_Opening_Backlog),
                        current_demand=float(row.Scenario_Qualified_Demand),
                        external_receipts=float(row.External_Receipts_Qty),
                        internal_production=float(row.Internal_Production_Qty),
                        backlog_policy=row.Backlog_Policy,
                    )
                    record = row.to_dict()
                    record.update(values)
                    record["Allocation_Policy"] = allocation_policy
                    record["Quantity_Step"] = quantity_step
                    state_rows.append(record)
                    state[(plant, row["Product Card Id"])] = (values["Ending_Inventory"], values["Ending_Backlog"], values["Ending_Opening_Backlog"])
                record = pool.to_dict()
                record["Allocated_Workload"] = float(allocated.Allocated_Workload.sum())
                balance = float(pool.Available_Workload_Capacity) - record["Allocated_Workload"]
                if balance < -1e-8:
                    raise ValueError("shared workload capacity exceeded beyond numeric tolerance")
                # Normalize machine roundoff only; real over-allocation still fails.
                record["Remaining_Workload_Capacity"] = max(balance, 0.0)
                record["Unmet_Workload"] = float(allocated.Unmet_Workload.sum())
                record["Workload_Shortage"] = record["Unmet_Workload"] > 1e-9
                pool_rows.append(record)
    return (
        pd.DataFrame(state_rows).sort_values(["Scenario", "Order_Date", "Plant_ID", "Allocation_Order"]).reset_index(drop=True),
        pd.DataFrame(pool_rows).sort_values(["Scenario", "Order_Date", "Plant_ID"]).reset_index(drop=True),
    )
