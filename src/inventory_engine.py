"""One product's approved same-week supply and backlog transition, without I/O."""

from __future__ import annotations

import math


def transition_inventory(
    *,
    beginning_inventory: float,
    beginning_backlog: float,
    current_demand: float,
    external_receipts: float,
    internal_production: float,
    backlog_policy: str,
    opening_origin_backlog: float,
) -> dict[str, float]:
    """Fulfill older backlog before current demand and conserve product units.

    Receipt quantity means supply explicitly declared usable in this week.
    opening_origin_backlog tracks obligations that predate the planning horizon;
    it is part of, not additional to, beginning_backlog.
    """
    values = [beginning_inventory, beginning_backlog, current_demand, external_receipts, internal_production, opening_origin_backlog]
    if any(isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("inventory transition inputs must be finite nonnegative quantities")
    if backlog_policy not in {"LOST_SALES", "CARRY_FORWARD"}:
        raise ValueError("explicit LOST_SALES or CARRY_FORWARD policy required")
    if opening_origin_backlog > beginning_backlog + 1e-9:
        raise ValueError("opening-origin backlog cannot exceed total backlog")
    if backlog_policy == "LOST_SALES" and beginning_backlog != 0:
        raise ValueError("LOST_SALES cannot silently discard opening backlog")
    supply = beginning_inventory + external_receipts + internal_production
    fulfilled_old = min(beginning_backlog, supply)
    fulfilled_opening = min(opening_origin_backlog, fulfilled_old)
    fulfilled_current = min(current_demand, supply - fulfilled_old)
    ending_inventory = max(supply - fulfilled_old - fulfilled_current, 0.0)
    current_unfilled = current_demand - fulfilled_current
    ending_backlog = beginning_backlog - fulfilled_old + current_unfilled if backlog_policy == "CARRY_FORWARD" else 0.0
    return {
        "Fulfilled_Current_Qty": fulfilled_current,
        "Fulfilled_Backlog_Qty": fulfilled_old,
        "Fulfilled_Opening_Backlog_Qty": fulfilled_opening,
        "Fulfilled_Horizon_Backlog_Qty": fulfilled_old - fulfilled_opening,
        "Current_Unfulfilled_Qty": current_unfilled,
        "Ending_Inventory": ending_inventory,
        "Ending_Backlog": ending_backlog,
        "Ending_Opening_Backlog": opening_origin_backlog - fulfilled_opening,
        "Ending_Horizon_Backlog": ending_backlog - (opening_origin_backlog - fulfilled_opening),
        "Lost_Sales_Qty": current_unfilled if backlog_policy == "LOST_SALES" else 0.0,
    }
