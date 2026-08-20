"""In-memory Stage 5 KPI, status, and scenario-comparison orchestration."""

from __future__ import annotations

import pandas as pd

from src.allocation_validator import validate_allocation_results
from src.kpi_engine import KPI_COLUMNS, calculate_kpis
from src.performance_evaluator import evaluate_performance


PERFORMANCE_COLUMNS = KPI_COLUMNS + [
    "Service_Risk",
    "Capacity_Risk",
    "Performance_Status",
    "Status_Reason",
    "Baseline_Scenario",
    "Service_Level_Change",
    "Capacity_Utilization_Change",
    "Backlog_Change",
    "Allocation_Rate_Change",
]


def evaluate_allocation(allocation_results: pd.DataFrame) -> pd.DataFrame:
    """Evaluate Stage 4 results and return one consolidated performance table."""
    validate_allocation_results(allocation_results)
    kpis = calculate_kpis(allocation_results)
    evaluated = evaluate_performance(kpis)
    evaluated["Baseline_Scenario"] = pd.NA
    for column in ("Service_Level_Change", "Capacity_Utilization_Change", "Backlog_Change", "Allocation_Rate_Change"):
        evaluated[column] = pd.NA

    scenario_rows = evaluated["Aggregation_Level"] == "Scenario"
    baseline = evaluated[scenario_rows & (evaluated["Scenario"] == "Baseline")]
    if len(baseline) != 1:
        raise ValueError("exactly one Baseline scenario KPI row is required")
    reference = baseline.iloc[0]
    for index in evaluated.index[scenario_rows]:
        evaluated.loc[index, "Baseline_Scenario"] = "Baseline"
        evaluated.loc[index, "Service_Level_Change"] = evaluated.loc[index, "Service_Level"] - reference["Service_Level"]
        evaluated.loc[index, "Capacity_Utilization_Change"] = evaluated.loc[index, "Capacity_Utilization"] - reference["Capacity_Utilization"]
        evaluated.loc[index, "Backlog_Change"] = evaluated.loc[index, "Total_Backlog"] - reference["Total_Backlog"]
        evaluated.loc[index, "Allocation_Rate_Change"] = evaluated.loc[index, "Allocation_Rate"] - reference["Allocation_Rate"]
    return evaluated[PERFORMANCE_COLUMNS].sort_values(
        ["Aggregation_Level", "Scenario", "Plant_ID", "Order_Date"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)

