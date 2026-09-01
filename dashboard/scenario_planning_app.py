"""Streamlit decision-support view for the frozen Scenario Planning backend.

The app is intentionally a presentation/orchestration layer. Scenario,
allocation, and KPI calculations remain in ``src.run_planning`` and the
completed Stage 1–5 modules.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Mapping

import pandas as pd
import plotly.express as px
import streamlit as st

# Streamlit executes a script with its containing directory first on
# sys.path. Add the repository root so the project-local ``src`` namespace
# is importable from the documented repository-root launch command.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.run_planning import PlanningRunError, run_planning


DATA_ROOT = REPOSITORY_ROOT / "data"
PROCESSED_ROOT = DATA_ROOT / "processed"
PERFORMANCE_COLUMNS = {
    "Aggregation_Level",
    "Scenario",
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
    "Performance_Status",
}
ALLOCATION_COLUMNS = {
    "Scenario",
    "Plant_ID",
    "Product Card Id",
    "Product Name",
    "Order_Date",
    "Planning_Priority",
    "Net_Demand",
    "Allocated_Qty",
    "Backlog",
    "Remaining_Capacity",
    "Allocation_Reason",
}


def load_dashboard_outputs(output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load and minimally validate the three dashboard-facing outputs."""
    directory = Path(output_dir)
    paths = {
        "performance": directory / "performance_result.csv",
        "allocation": directory / "allocation_result.csv",
        "scenario": directory / "scenario_snapshot.csv",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing dashboard output(s): " + ", ".join(missing))
    outputs = {
        name: pd.read_csv(path, parse_dates=["Order_Date"])
        for name, path in paths.items()
    }
    if not PERFORMANCE_COLUMNS.issubset(outputs["performance"].columns):
        raise ValueError("performance_result.csv does not match the Stage 5 contract")
    if not ALLOCATION_COLUMNS.issubset(outputs["allocation"].columns):
        raise ValueError("allocation_result.csv does not match the Stage 4 contract")
    return outputs


def scenario_kpis(performance: pd.DataFrame) -> pd.DataFrame:
    """Return only scenario-level KPI rows for comparison visuals."""
    return performance.loc[
        performance["Aggregation_Level"].eq("Scenario")
    ].sort_values("Scenario", kind="mergesort").reset_index(drop=True)


def scenario_comparison(performance: pd.DataFrame) -> pd.DataFrame:
    """Return the prepared Baseline comparison values from Stage 5."""
    columns = [
        "Scenario",
        "Service_Level",
        "Capacity_Utilization",
        "Allocation_Rate",
        "Total_Backlog",
        "Service_Level_Change",
        "Capacity_Utilization_Change",
        "Allocation_Rate_Change",
        "Backlog_Change",
        "Performance_Status",
    ]
    available = [column for column in columns if column in performance.columns]
    return scenario_kpis(performance)[available]


def _default_output_dir() -> Path:
    """Use the approved 2017 run when it is already available."""
    candidate = PROCESSED_ROOT / "scenario_runs" / "20170101_20171231"
    if (candidate / "performance_result.csv").exists():
        return candidate
    return PROCESSED_ROOT


def _render_kpi_cards(row: pd.Series) -> None:
    cards = st.columns(5)
    values = [
        ("Service Level", f"{row['Service_Level']:.1%}"),
        ("Capacity Utilization", f"{row['Capacity_Utilization']:.1%}"),
        ("Allocation Rate", f"{row['Allocation_Rate']:.1%}"),
        ("Backlog", f"{row['Total_Backlog']:,.0f}"),
        ("Status", str(row["Performance_Status"])),
    ]
    for card, (label, value) in zip(cards, values):
        card.metric(label, value)


def _run_controls() -> None:
    st.sidebar.header("Planning run")
    start = st.sidebar.date_input("Planning start week", value=pd.Timestamp("2017-01-01").date())
    end = st.sidebar.date_input("Planning end week", value=pd.Timestamp("2017-12-31").date())
    demand_pct = st.sidebar.number_input("Demand surge (%)", min_value=0.0, value=10.0, step=1.0)
    capacity_pct = st.sidebar.number_input(
        "Capacity disruption (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0
    )
    plants = pd.read_csv(PROCESSED_ROOT / "planning_snapshot.csv", usecols=["Plant_ID"])["Plant_ID"].dropna().unique().tolist()
    disruption_plant = st.sidebar.selectbox("Disruption plant", sorted(plants), index=0)
    if st.sidebar.button("Run planning", type="primary"):
        try:
            outputs = run_planning(
                DATA_ROOT,
                start,
                end,
                demand_surge_pct=demand_pct,
                capacity_disruption_pct=capacity_pct,
                disruption_plant=disruption_plant,
            )
            st.session_state["scenario_output_dir"] = str(outputs["performance_result"].parent)
            st.sidebar.success("Planning run completed")
        except (PlanningRunError, FileNotFoundError, ValueError) as exc:
            st.sidebar.error(str(exc))


def _overview(performance: pd.DataFrame, scenario: pd.DataFrame) -> None:
    st.subheader("Scenario Overview")
    selected = st.selectbox("Scenario", scenario["Scenario"].tolist())
    row = scenario.loc[scenario["Scenario"].eq(selected)].iloc[0]
    _render_kpi_cards(row)
    st.caption("Scenario assumptions are generated by the backend runner; Power BI/UI does not recalculate them.")
    plant_rows = performance[
        (performance["Aggregation_Level"] == "Scenario × Plant")
        & (performance["Scenario"] == selected)
    ]
    if not plant_rows.empty:
        fig = px.bar(plant_rows, x="Plant_ID", y="Capacity_Utilization", color="Performance_Status", title="Capacity utilization by plant")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)


def _comparison(performance: pd.DataFrame) -> None:
    st.subheader("Scenario Comparison")
    comparison = scenario_comparison(performance)
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    chart = comparison.melt(
        id_vars="Scenario",
        value_vars=["Service_Level", "Capacity_Utilization", "Allocation_Rate"],
        var_name="KPI",
        value_name="Value",
    )
    fig = px.bar(chart, x="Scenario", y="Value", color="KPI", barmode="group", title="Baseline and alternative KPI comparison")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)


def _allocation_detail(allocation: pd.DataFrame) -> None:
    st.subheader("Capacity Allocation Detail")
    scenarios = sorted(allocation["Scenario"].unique())
    scenario = st.selectbox("Detail scenario", scenarios, key="detail_scenario")
    frame = allocation[allocation["Scenario"].eq(scenario)]
    plants = sorted(frame["Plant_ID"].unique())
    plant = st.selectbox("Plant", plants, key="detail_plant")
    frame = frame[frame["Plant_ID"].eq(plant)]
    columns = [
        "Order_Date", "Product Card Id", "Product Name", "Planning_Priority",
        "Net_Demand", "Allocated_Qty", "Backlog", "Remaining_Capacity", "Allocation_Reason",
    ]
    st.dataframe(frame[columns].sort_values(["Order_Date", "Planning_Priority", "Product Card Id"], ascending=[True, False, True]), use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Scenario Planning Decision Support", layout="wide")
    st.title("Scenario Planning Decision Support")
    st.info("Use the existing Control Tower PBIX for operational monitoring and root-cause analysis. This page adds scenario planning and capacity decision support.")
    _run_controls()
    output_dir = Path(st.session_state.get("scenario_output_dir", _default_output_dir()))
    try:
        outputs = load_dashboard_outputs(output_dir)
    except (FileNotFoundError, ValueError) as exc:
        st.warning(f"No dashboard run is available yet: {exc}")
        return
    performance = outputs["performance"]
    scenario = scenario_kpis(performance)
    tabs = st.tabs(["Scenario Overview", "Scenario Comparison", "Capacity Allocation Detail"])
    with tabs[0]:
        _overview(performance, scenario)
    with tabs[1]:
        _comparison(performance)
    with tabs[2]:
        _allocation_detail(outputs["allocation"])


if __name__ == "__main__":
    main()
