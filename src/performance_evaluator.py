"""Transparent Stage 5 performance status rules."""

from __future__ import annotations

import pandas as pd


def evaluate_performance(kpis: pd.DataFrame) -> pd.DataFrame:
    """Assign Healthy, Watch, or At Risk without numerical KPI recalculation."""
    result = kpis.copy(deep=True)
    if (result["Service_Level"] < 0).any() or (result["Service_Level"] > 1 + 1e-9).any():
        raise ValueError("Service_Level must be between 0 and 1")
    if (result["Capacity_Utilization"] < 0).any() or (result["Capacity_Utilization"] > 1 + 1e-9).any():
        raise ValueError("Capacity_Utilization must be between 0 and 1")
    if (result["Allocation_Rate"] < 0).any() or (result["Allocation_Rate"] > 1 + 1e-9).any():
        raise ValueError("Allocation_Rate must be between 0 and 1")
    at_risk = result["Total_Backlog"] > 0
    watch = (~at_risk) & (result["Capacity_Utilization"] >= 1 - 1e-9)
    result["Service_Risk"] = at_risk.map({True: "At Risk", False: "Healthy"})
    result["Capacity_Risk"] = "Healthy"
    result.loc[watch, "Capacity_Risk"] = "Watch"
    result.loc[at_risk, "Capacity_Risk"] = "At Risk"
    result["Performance_Status"] = "Healthy"
    result.loc[watch, "Performance_Status"] = "Watch"
    result.loc[at_risk, "Performance_Status"] = "At Risk"
    result["Status_Reason"] = "No backlog and utilization below 100%"
    result.loc[watch, "Status_Reason"] = "No backlog and capacity fully utilized"
    result.loc[at_risk, "Status_Reason"] = "Backlog remains after allocation"
    return result

