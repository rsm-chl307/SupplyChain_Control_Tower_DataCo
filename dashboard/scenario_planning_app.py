"""Streamlit decision-support view for the frozen Scenario Planning backend.

The app is intentionally a presentation/orchestration layer. Scenario,
allocation, and KPI calculations remain in ``src.run_planning`` and the
completed Stage 1–5 modules.
"""

from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import pandas as pd
try:
    import plotly.express as px
except ImportError:
    px = None  # Prepared tables and sequential views need no optional chart dependency.
import streamlit as st

# Streamlit executes a script with its containing directory first on
# sys.path. Add the repository root so the project-local ``src`` namespace
# is importable from the documented repository-root launch command.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.run_planning import PlanningRunError, run_csv_planning, run_planning, run_sequential_planning
from src.planning_risk import (
    plant_bottleneck_summary,
    product_risk_ranking,
    risk_driver_details,
    scenario_plant_deterioration,
    scenario_product_deterioration,
    scenario_risk_comparison,
)


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

CSV_INPUT_SCHEMAS = {
    "products": ("Products", ["Product_ID", "Product_Name"], ["Quantity_Unit", "Planning_Priority"]),
    "plants": ("Plants", ["Plant_ID"], ["Plant_Name"]),
    "product_plant_mapping": ("Product to plant mapping", ["Product_ID", "Plant_ID"], []),
    "demand": ("Demand", [], ["Product_ID", "Plant_ID", "Week", "Demand_Qty", "Status", "Quantity_Unit",
                                  "Order_Line_ID", "Date", "Quantity", "Coverage_Status"]),
    "priorities": ("Optional planning priorities", ["Product_ID", "Planning_Priority"], []),
    "weekly_capacity": ("Weekly workload capacity", ["Plant_ID", "Week", "Capacity", "Workload_Unit"],
                        ["Capacity_Version", "Factor_Version"]),
    "workload_factors": ("Product workload factors", ["Product_ID", "Workload_Factor", "Workload_Unit"],
                         ["Factor_Version", "Quantity_Unit"]),
    "initial_inventory": ("Initial inventory", ["Plant_ID", "Product_ID", "Beginning_Inventory"],
                          ["Week", "Quantity_Unit", "Beginning_Backlog"]),
    "opening_backlog": ("Opening backlog", ["Plant_ID", "Product_ID", "Beginning_Backlog"], ["Quantity_Unit"]),
    "external_receipts": ("External receipts", ["Receipt_ID", "Plant_ID", "Product_ID", "Week", "External_Receipts_Qty"],
                          ["Scenario", "Quantity_Unit"]),
}
CSV_FIELD_ALIASES = {
    "Product_ID": ["sku", "product_id", "Product Card Id", "Product ID"],
    "Product_Name": ["title", "product_name", "Product Name"],
    "Plant_ID": ["site", "plant_id", "Plant ID"],
    "Plant_Name": ["label", "plant_name", "Plant Name"],
    "Quantity_Unit": ["uom", "unit", "quantity_unit"],
    "Planning_Priority": ["rank", "priority", "planning_priority"],
    "Week": ["week_ending", "week_end", "usable_week", "week"],
    "Demand_Qty": ["units", "qty", "demand_qty"],
    "Status": ["state", "status", "Order Status"],
    "Order_Line_ID": ["order_line_id", "Order Item Id", "order_id"],
    "Date": ["order date (DateOrders)", "order_date", "date"],
    "Quantity": ["quantity", "Order Item Quantity", "units"],
    "Capacity": ["available_load", "capacity"],
    "Workload_Unit": ["load_unit", "workload_unit"],
    "Workload_Factor": ["load_per_unit", "workload_factor"],
    "Beginning_Inventory": ["stock", "beginning_inventory"],
    "Beginning_Backlog": ["open_qty", "beginning_backlog"],
    "Receipt_ID": ["event", "receipt", "receipt_id"],
    "External_Receipts_Qty": ["received_units", "qty", "external_receipts_qty"],
}

_USER_UPLOAD_DATA_KEY = "_user_csv_upload_data"
_USER_UPLOAD_WIDGET_STATE_KEY = "_user_csv_upload_widget_state"


class _StoredCSVUpload:
    """Keep an uploaded CSV usable after Streamlit removes its uploader widget."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def _capture_user_upload_state() -> None:
    """Copy upload bytes and form values before model switching cleans widgets."""
    widget_state = st.session_state.setdefault(_USER_UPLOAD_WIDGET_STATE_KEY, {})
    for key in list(st.session_state.keys()):
        if key.startswith(("map_", "provenance_", "eligibility_", "upload_")) and not key.startswith("upload_widget_"):
            widget_state[key] = st.session_state[key]

    uploads = st.session_state.setdefault(_USER_UPLOAD_DATA_KEY, {})
    for dataset in CSV_INPUT_SCHEMAS:
        uploaded = st.session_state.get(f"upload_widget_{dataset}")
        if uploaded is not None:
            uploads[dataset] = (uploaded.name, uploaded.getvalue())


def _restore_user_upload_state() -> None:
    """Restore saved upload form values before their widgets are rendered."""
    for key, value in st.session_state.get(_USER_UPLOAD_WIDGET_STATE_KEY, {}).items():
        st.session_state[key] = value


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


def format_percentage_points(value: object) -> str:
    """Format a ratio change as business-friendly percentage points."""
    if pd.isna(value):
        return "—"
    number = float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number * 100:.2f} percentage points"


def comparison_display_table(performance: pd.DataFrame) -> pd.DataFrame:
    """Create a presentation-only comparison table; source values stay numeric."""
    table = scenario_comparison(performance).copy()
    for column in ("Service_Level_Change", "Capacity_Utilization_Change", "Allocation_Rate_Change"):
        table[column] = table[column].map(format_percentage_points)
    table["Backlog_Change"] = table["Backlog_Change"].map(
        lambda value: "—" if pd.isna(value) else f"{float(value):+,.0f}"
    )
    return table


def scenario_insights(performance: pd.DataFrame) -> list[str]:
    """Return deterministic decision-support observations from Stage 5 rows."""
    table = scenario_kpis(performance)
    alternatives = table[table["Scenario"].ne("Baseline")]
    if alternatives.empty:
        return ["No alternative scenario is available for comparison."]
    pressure = alternatives.sort_values(
        ["Capacity_Utilization_Change", "Scenario"], ascending=[False, True], kind="mergesort"
    ).iloc[0]
    insights = [
        f"Greatest capacity pressure: {pressure['Scenario']} ({format_percentage_points(pressure['Capacity_Utilization_Change'])} utilization versus Baseline)."
    ]
    backlog_rows = alternatives[alternatives["Total_Backlog"] > 0]
    if backlog_rows.empty:
        insights.append("No alternative scenario creates backlog in the selected horizon.")
    else:
        affected = ", ".join(backlog_rows["Scenario"].astype(str))
        insights.append(f"Backlog is created by: {affected}.")
    statuses = ", ".join(
        f"{row.Scenario}: {row.Performance_Status}" for row in alternatives.itertuples()
    )
    insights.append(f"Performance status: {statuses}.")
    return insights


def allocation_plant_summary(allocation: pd.DataFrame, performance: pd.DataFrame) -> pd.DataFrame:
    """Combine allocation totals with authoritative Stage 5 plant KPIs."""
    allocated = allocation.groupby(["Scenario", "Plant_ID"], as_index=False).agg(
        Allocated_Qty=("Allocated_Qty", "sum"), Backlog=("Backlog", "sum")
    )
    plant_kpis = performance.loc[
        performance["Aggregation_Level"].eq("Scenario × Plant"),
        ["Scenario", "Plant_ID", "Total_Scenario_Capacity", "Remaining_Capacity", "Performance_Status"],
    ]
    return allocated.merge(plant_kpis, on=["Scenario", "Plant_ID"], how="left").sort_values(
        ["Scenario", "Plant_ID"], kind="mergesort"
    ).reset_index(drop=True)


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
    if not (PROCESSED_ROOT / "planning_snapshot.csv").exists():
        st.sidebar.info("Legacy reference inputs are unavailable. The sequential CSV modes remain available.")
        return
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
    if not plant_rows.empty and px is not None:
        fig = px.bar(plant_rows, x="Plant_ID", y="Capacity_Utilization", color="Performance_Status", title="Capacity utilization by plant")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)


def _comparison(performance: pd.DataFrame) -> None:
    st.subheader("Scenario Comparison")
    comparison = scenario_comparison(performance)
    st.caption("Baseline is the reference. Changes are shown as percentage-point deltas; backlog is an absolute quantity.")
    st.dataframe(comparison_display_table(performance), use_container_width=True, hide_index=True)
    if px is None:
        st.caption("Plotly is unavailable; prepared comparison values remain available in the table.")
        for insight in scenario_insights(performance):
            st.write(f"- {insight}")
        return
    chart = comparison.melt(
        id_vars="Scenario",
        value_vars=["Service_Level", "Capacity_Utilization", "Allocation_Rate"],
        var_name="KPI",
        value_name="Value",
    )
    fig = px.bar(
        chart, x="Scenario", y="Value", color="Scenario", facet_col="KPI", facet_col_wrap=2,
        title="Scenario KPI levels (independent scales)",
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    changes = comparison.melt(
        id_vars="Scenario",
        value_vars=["Service_Level_Change", "Capacity_Utilization_Change", "Allocation_Rate_Change"],
        var_name="KPI",
        value_name="Change",
    )
    changes["KPI"] = changes["KPI"].str.replace("_Change", "", regex=False).str.replace("_", " ")
    changes = changes[changes["Scenario"].ne("Baseline")]
    change_fig = px.bar(
        changes, x="KPI", y="Change", color="Scenario", barmode="group",
        title="Scenario impact versus Baseline (percentage points)",
    )
    change_fig.update_yaxes(tickformat="+.2%")
    st.plotly_chart(change_fig, use_container_width=True)
    st.markdown("**Decision-support insights**")
    for insight in scenario_insights(performance):
        st.write(f"- {insight}")
    backlog_fig = px.bar(
        comparison, x="Scenario", y="Total_Backlog", color="Scenario",
        title="Backlog impact by scenario",
    )
    st.plotly_chart(backlog_fig, use_container_width=True)


def _allocation_detail(allocation: pd.DataFrame) -> None:
    st.subheader("Capacity Allocation Detail")
    scenarios = sorted(allocation["Scenario"].unique())
    scenario = st.selectbox("Detail scenario", scenarios, key="detail_scenario")
    frame = allocation[allocation["Scenario"].eq(scenario)]
    plants = sorted(frame["Plant_ID"].unique())
    plant = st.selectbox("Plant", plants, key="detail_plant")
    frame = frame[frame["Plant_ID"].eq(plant)]
    # Capacity is shared at Scenario × Plant × Week; use prepared Stage 5
    # plant KPIs rather than summing repeated row capacity.
    try:
        output_dir = Path(st.session_state.get("scenario_output_dir", _default_output_dir()))
        performance = load_dashboard_outputs(output_dir)["performance"]
        summary = allocation_plant_summary(allocation, performance)
        st.dataframe(
            summary[(summary["Scenario"] == scenario) & (summary["Plant_ID"] == plant)],
            use_container_width=True, hide_index=True,
        )
    except (FileNotFoundError, ValueError):
        st.warning("Plant performance summary is unavailable for this run.")
    columns = [
        "Order_Date", "Product Card Id", "Product Name", "Planning_Priority",
        "Net_Demand", "Allocated_Qty", "Backlog", "Remaining_Capacity", "Allocation_Reason",
    ]
    st.dataframe(frame[columns].sort_values(["Order_Date", "Planning_Priority", "Product Card Id"], ascending=[True, False, True]), use_container_width=True, hide_index=True)



def _csv_preview(uploaded_file) -> tuple[pd.DataFrame | None, str | None]:
    """Read an uploaded CSV for headers and status choices without saving it."""
    if uploaded_file is None:
        return None, None
    try:
        frame = pd.read_csv(BytesIO(uploaded_file.getvalue()), dtype=str, keep_default_na=False)
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        return None, f"{uploaded_file.name}: could not read CSV: {exc}"
    if frame.columns.duplicated().any():
        return None, f"{uploaded_file.name}: duplicate column names are not supported. Rename them before upload."
    if frame.empty:
        return None, f"{uploaded_file.name}: CSV has a header but no data rows."
    return frame, None


def _suggested_column(canonical: str, columns: list[str]) -> str:
    candidates = [canonical, *CSV_FIELD_ALIASES.get(canonical, [])]
    by_casefold = {column.casefold(): column for column in columns}
    for candidate in candidates:
        if candidate in columns:
            return candidate
        if candidate.casefold() in by_casefold:
            return by_casefold[candidate.casefold()]
    return ""


def _render_column_mapping(dataset: str, preview: pd.DataFrame | None, demand_format: str,
                           uploaded_file=None) -> dict[str, str]:
    """Render required/optional canonical field mappings for one uploaded file."""
    uploaded = uploaded_file or st.session_state.get(f"upload_widget_{dataset}")
    if preview is None or uploaded is None:
        return {}
    columns = [str(column) for column in preview.columns]
    if dataset == "demand":
        required = (["Product_ID", "Demand_Qty", "Week"] if demand_format == "WEEKLY"
                    else ["Product_ID", "Order_Line_ID", "Date", "Quantity", "Status"])
        optional = (["Plant_ID", "Status", "Quantity_Unit", "Coverage_Status"] if demand_format == "WEEKLY"
                    else ["Plant_ID", "Quantity_Unit"])
    else:
        _, required, optional = CSV_INPUT_SCHEMAS[dataset]
    mapping: dict[str, str] = {}
    with st.expander(f"Map columns: {CSV_INPUT_SCHEMAS[dataset][0]} ({len(preview):,} rows)", expanded=False):
        st.caption("Select the matching source column for each canonical field. Required mappings are marked *.")
        st.selectbox("Source classification", ["USER_PROVIDED", "SYNTHETIC", "SYNTHETIC_EXAMPLE", "DERIVED", "REFERENCE_INPUT"],
                     key=f"provenance_{dataset}", help="This describes source provenance; user-provided data is not independently verified.")
        for canonical in [*required, *optional]:
            suggested = _suggested_column(canonical, columns)
            options = ["— not provided —", *columns]
            index = options.index(suggested) if suggested else 0
            selected = st.selectbox(
                f"{canonical}{' *' if canonical in required else ''}", options,
                index=index, key=f"map_{dataset}_{canonical}_{uploaded.name}",
            )
            if selected != "— not provided —":
                mapping[canonical] = selected
    return mapping


def _preview_identifiers(preview: pd.DataFrame | None, column: str | None) -> list[str]:
    if preview is None or not column:
        return []
    return sorted(preview[column].astype(str).unique().tolist())


def _suggested_horizon(preview: pd.DataFrame | None, mapping: dict[str, str], demand_format: str) -> tuple[date, date]:
    """Suggest a Sunday-ending horizon from the mapped demand dates."""
    today = date.today()
    fallback = today + timedelta(days=(6 - today.weekday()) % 7)
    column = mapping.get("Week" if demand_format == "WEEKLY" else "Date")
    if preview is None or not column:
        return fallback, fallback
    dates = pd.to_datetime(preview[column], errors="coerce").dropna()
    if dates.empty:
        return fallback, fallback
    weeks = dates + pd.to_timedelta(6 - dates.dt.weekday, unit="D")
    return weeks.min().date(), weeks.max().date()


def _render_readiness_report(report: dict) -> None:
    """Display validation findings, provenance, assumptions, and coverage."""
    if report.get("Status") == "READY":
        st.success("Data readiness: READY — inputs passed the planning validator.")
    else:
        st.error("Data readiness: BLOCKED — resolve the reported issues before planning.")
    for error in report.get("Errors", []):
        st.write(f"- {error}")
    for warning in report.get("Warnings", []):
        st.caption(f"Note: {warning}")
    capabilities = report.get("Capabilities", {})
    if capabilities:
        st.dataframe(pd.DataFrame([{"Capability": key, "Status": value} for key, value in capabilities.items()]),
                     hide_index=True, use_container_width=True)
    sources = report.get("Sources", [])
    if sources:
        st.markdown("**Datasets inspected**")
        view = pd.DataFrame(sources)
        columns = [column for column in ["Dataset", "Rows", "Columns", "Classification", "Version"] if column in view]
        st.dataframe(view[columns], hide_index=True, use_container_width=True)
    assumptions = report.get("Assumptions", [])
    if assumptions:
        st.markdown("**Explicit assumptions**")
        st.dataframe(pd.DataFrame(assumptions), hide_index=True, use_container_width=True)
    derived = report.get("Derived_Values", [])
    if derived:
        with st.expander("Coverage and derived-value details"):
            st.json(derived)
    configured = report.get("Explicit_Configuration")
    if configured:
        with st.expander("Demand mapping and scenario configuration"):
            st.json(configured)
    unavailable = report.get("Unavailable_Capabilities", [])
    if unavailable:
        st.caption("Unavailable capabilities: " + ", ".join(unavailable))


def _build_upload_config(*, uploads: dict, mappings: dict, demand_format: str, status_eligibility: dict,
                         already_qualified: bool, source_is_complete: bool, quantity_step: float,
                         assumption_version: str, start_week: date, end_week: date, interpretation: str,
                         surge_pct: float, disruption_pct: float, disrupted_plants: list[str], backlog_policy: str,
                         assumptions: dict) -> tuple[dict, list[str]]:
    """Build the established JSON config shape from the upload form values."""
    errors: list[str] = []
    for dataset in ["products", "plants", "product_plant_mapping", "demand"]:
        if uploads.get(dataset) is None:
            errors.append(f"Upload the required {CSV_INPUT_SCHEMAS[dataset][0]} CSV.")
    if start_week > end_week:
        errors.append("Planning start week must be on or before end week.")
    if start_week.weekday() != 6 or end_week.weekday() != 6:
        errors.append("Planning horizon dates must be Sundays (week-ending dates).")
    files = {}
    for dataset, uploaded in uploads.items():
        if uploaded is None:
            continue
        mapping = mappings.get(dataset, {})
        required = CSV_INPUT_SCHEMAS[dataset][1]
        if dataset == "demand":
            required = (["Product_ID", "Demand_Qty", "Week"] if demand_format == "WEEKLY"
                        else ["Product_ID", "Order_Line_ID", "Date", "Quantity", "Status"])
        errors.extend(f"{CSV_INPUT_SCHEMAS[dataset][0]}: map required field {field}."
                      for field in required if field not in mapping)
        if len(set(mapping.values())) != len(mapping):
            errors.append(f"{CSV_INPUT_SCHEMAS[dataset][0]}: a source column is mapped more than once.")
        if mapping:
            files[dataset] = {
                "path": f"{dataset}.csv", "columns": mapping,
                "provenance": st.session_state.get(f"provenance_{dataset}", "USER_PROVIDED"),
            }

    assumptions_out: dict[str, object] = {}
    if uploads.get("products") is not None:
        if "Quantity_Unit" not in mappings.get("products", {}) and assumptions["quantity_unit"].strip():
            assumptions_out["quantity_unit"] = assumptions["quantity_unit"].strip()
        priority_provided = "Planning_Priority" in mappings.get("products", {}) or uploads.get("priorities") is not None
        if not priority_provided and assumptions["use_priority"]:
            assumptions_out["planning_priority"] = int(assumptions["planning_priority"])
        elif not priority_provided:
            errors.append("Provide Planning_Priority in Products or upload Priorities, or explicitly enable the common priority assumption.")
    if uploads.get("workload_factors") is None:
        if assumptions["use_factor"] and assumptions["workload_unit"].strip():
            assumptions_out["uniform_workload_factor"] = float(assumptions["uniform_factor"])
            assumptions_out["workload_unit"] = assumptions["workload_unit"].strip()
        else:
            errors.append("Upload workload factors or explicitly enable the uniform synthetic factor and workload unit.")
    if uploads.get("initial_inventory") is None:
        if assumptions["zero_inventory"]:
            assumptions_out["initial_inventory"] = "ZERO"
        else:
            errors.append("Upload Initial inventory or explicitly assume zero initial inventory.")
    backlog_embedded = uploads.get("initial_inventory") is not None and "Beginning_Backlog" in mappings.get("initial_inventory", {})
    if uploads.get("opening_backlog") is None and not backlog_embedded:
        if assumptions["zero_backlog"]:
            assumptions_out["opening_backlog"] = "ZERO"
        else:
            errors.append("Upload Opening backlog or explicitly assume zero opening backlog.")
    if uploads.get("external_receipts") is None:
        if assumptions["no_receipts"]:
            assumptions_out["external_receipts"] = "NONE"
        else:
            errors.append("Upload External receipts or explicitly declare that no external receipts are modeled.")
    if uploads.get("weekly_capacity") is None:
        if assumptions["capacity_calibration"]:
            assumptions_out["capacity_calibration"] = {
                "start_week": start_week.isoformat(), "end_week": end_week.isoformat(),
                "target_utilization": float(assumptions["target_utilization"]),
                "capacity_version": "ui-synthetic-calibration-v1",
            }
        else:
            errors.append("Upload Weekly workload capacity or explicitly choose synthetic demand-calibrated capacity.")

    config = {
        "data_mode": "USER_DATA", "assumption_version": assumption_version.strip(),
        "planning_interpretation": interpretation,
        "planning_start_week": start_week.isoformat(), "planning_end_week": end_week.isoformat(),
        "quantity_step": float(quantity_step), "allocation_policy": "PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT",
        "demand_format": demand_format, "files": files, "assumptions": assumptions_out,
        "scenarios": [
            {"Scenario": "Baseline", "Demand_Multiplier": 1.0, "Capacity_Multiplier": 1.0,
             "Disruption_Plants": [], "Disruption_Weeks": None, "Backlog_Policy": backlog_policy},
            {"Scenario": "Demand_Surge", "Demand_Multiplier": 1 + surge_pct / 100, "Capacity_Multiplier": 1.0,
             "Disruption_Plants": [], "Disruption_Weeks": None, "Backlog_Policy": backlog_policy},
            {"Scenario": "Capacity_Disruption", "Demand_Multiplier": 1.0, "Capacity_Multiplier": 1 - disruption_pct / 100,
             "Disruption_Plants": disrupted_plants, "Disruption_Weeks": None, "Backlog_Policy": backlog_policy},
            {"Scenario": "Combined_Stress", "Demand_Multiplier": 1 + surge_pct / 100,
             "Capacity_Multiplier": 1 - disruption_pct / 100,
             "Disruption_Plants": disrupted_plants, "Disruption_Weeks": None, "Backlog_Policy": backlog_policy},
        ],
    }
    if status_eligibility:
        config["status_eligibility"] = status_eligibility
        config["eligibility_version"] = "streamlit-status-map-v1"
    elif demand_format == "WEEKLY" and already_qualified:
        config["qualification_basis"] = "ALREADY_QUALIFIED_INPUT"
    elif demand_format == "ORDER_LINES":
        errors.append("Map and classify every source order status before validating order-line demand.")
    if demand_format == "ORDER_LINES":
        config["source_is_complete"] = source_is_complete
    if not assumption_version.strip():
        errors.append("Provide an assumption version to identify this input and scenario bundle.")
    return config, errors


def _blocked_upload_report(errors: list[str]) -> dict:
    return {"Status": "BLOCKED", "Data_Mode": "USER_DATA", "Sources": [], "Assumptions": [],
            "Derived_Values": [], "Unavailable_Capabilities": ["Demand_Qualification", "Workload_Planning",
            "Sequential_Inventory", "Backlog_Planning", "Scenario_Comparison"], "Errors": errors,
            "Warnings": [], "Capabilities": {}}


def _upload_configuration_summary(config: dict) -> dict:
    return {
        "Demand_Format": config.get("demand_format"),
        "Qualification_Basis": config.get("qualification_basis", "STATUS_MAPPING"),
        "Status_Eligibility": config.get("status_eligibility", {}),
        "Planning_Horizon": [config.get("planning_start_week"), config.get("planning_end_week")],
        "Planning_Interpretation": config.get("planning_interpretation"),
        "Quantity_Step": config.get("quantity_step"),
        "Assumption_Version": config.get("assumption_version"),
        "Scenarios": config.get("scenarios", []),
    }


def _validate_uploaded_config(config: dict, uploads: dict) -> dict:
    """Run the canonical intake validator directly against uploaded bytes."""
    from src.csv_planning_inputs import InputValidationError, load_csv_planning_inputs

    payloads = {f"{dataset}.csv": uploaded.getvalue() for dataset, uploaded in uploads.items() if uploaded is not None}

    def reader(path: Path, encoding: str) -> pd.DataFrame:
        try:
            return pd.read_csv(BytesIO(payloads[path.name]), dtype=str, keep_default_na=False, encoding=encoding)
        except KeyError as exc:
            raise OSError(f"{path.name}: uploaded file bytes are unavailable") from exc

    try:
        report = load_csv_planning_inputs(config, Path("."), reader=reader).report
    except InputValidationError as exc:
        report = exc.report
    report["Explicit_Configuration"] = _upload_configuration_summary(config)
    return report


def _write_upload_inputs(upload_dir: Path, config: dict, uploads: dict) -> None:
    """Materialize only for the runner's existing path-based CSV interface."""
    for dataset, uploaded in uploads.items():
        if uploaded is not None:
            (upload_dir / f"{dataset}.csv").write_bytes(uploaded.getvalue())
    (upload_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def _user_csv_upload_workflow() -> None:
    """Upload, map, validate, and execute user CSVs through the existing runner."""
    st.subheader("Prepare your planning data")
    st.caption("Uploads stay in memory for validation and are staged in a temporary folder only while a planning run executes.")
    demand_format = st.radio("Demand file format", ["WEEKLY", "ORDER_LINES"], horizontal=True, key="upload_demand_format")
    required_uploads = {"products", "plants", "product_plant_mapping", "demand"}
    st.markdown("**Always required:** Products, Plants, Product to plant mapping, Demand. Initial inventory, workload factors, capacity, receipts, and opening backlog are required unless you explicitly select an allowed assumption.")
    with st.expander("Download CSV templates"):
        template_columns = st.columns(3)
        template_names = ["products", "plants", "product_plant_mapping", "demand", "weekly_capacity",
                          "initial_inventory", "workload_factors", "external_receipts", "opening_backlog"]
        for index, name in enumerate(template_names):
            path = REPOSITORY_ROOT / "examples" / "planning" / "templates" / f"{name}.csv"
            template_columns[index % 3].download_button(f"{CSV_INPUT_SCHEMAS[name][0]} template",
                path.read_bytes(), file_name=f"{name}.csv", mime="text/csv", key=f"download_template_{name}")

    uploads: dict[str, object] = {}
    previews: dict[str, pd.DataFrame | None] = {}
    parse_errors: list[str] = []
    upload_columns = st.columns(2)
    for index, (dataset, (label, _, _)) in enumerate(CSV_INPUT_SCHEMAS.items()):
        with upload_columns[index % 2]:
            st.file_uploader(f"{label} {'(required)' if dataset in required_uploads else '(optional)'}",
                             type=["csv"], accept_multiple_files=False, key=f"upload_widget_{dataset}")
        uploaded = st.session_state.get(f"upload_widget_{dataset}")
        if uploaded is not None:
            st.session_state.setdefault(_USER_UPLOAD_DATA_KEY, {})[dataset] = (uploaded.name, uploaded.getvalue())
        else:
            retained = st.session_state.get(_USER_UPLOAD_DATA_KEY, {}).get(dataset)
            if retained is not None:
                uploaded = _StoredCSVUpload(*retained)
                st.caption(f"Retained upload: {uploaded.name} — re-upload here to replace it.")
        uploads[dataset] = uploaded
        if uploaded is not None:
            previews[dataset], error = _csv_preview(uploaded)
            if error:
                parse_errors.append(error)

    status_rows = [
        {"Dataset": label, "Requirement": "Required" if dataset in required_uploads else "Optional / assumption may replace",
         "Status": "Uploaded" if uploads[dataset] is not None else "Missing"}
        for dataset, (label, _, _) in CSV_INPUT_SCHEMAS.items()
    ]
    st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)
    for error in parse_errors:
        st.error(error)

    already_qualified = False
    source_is_complete = False
    with st.form("user_csv_planning_form"):
        st.markdown("#### Column mapping")
        mappings = {
            dataset: _render_column_mapping(dataset, previews.get(dataset), demand_format, uploads[dataset])
            for dataset, uploaded in uploads.items() if uploaded is not None and previews.get(dataset) is not None
        }
        demand_preview = previews.get("demand")
        status_source = mappings.get("demand", {}).get("Status")
        status_values = sorted(demand_preview[status_source].astype(str).unique().tolist()) if demand_preview is not None and status_source else []
        status_eligibility: dict[str, bool] = {}
        if status_values:
            st.markdown("#### Demand qualification")
            st.caption("Choose which statuses count as qualified demand. Every source status must be classified.")
            for index, status in enumerate(status_values):
                choice = st.selectbox(f"Status: {status}", ["Choose…", "Qualified", "Excluded"],
                                      key=f"eligibility_{index}_{status}")
                if choice != "Choose…":
                    status_eligibility[status] = choice == "Qualified"
        elif demand_format == "WEEKLY" and demand_preview is not None:
            already_qualified = st.checkbox("This weekly demand CSV contains only already-qualified demand", value=False)
        elif demand_format == "ORDER_LINES" and demand_preview is not None:
            source_is_complete = st.checkbox("This order-line file is a complete extract for the stated planning history", value=False,
                                               help="Only this explicit assertion allows internal no-order weeks to be treated as covered zero demand.")

        st.markdown("#### Planning horizon and scenarios")
        start_default, end_default = _suggested_horizon(demand_preview, mappings.get("demand", {}), demand_format)
        horizon_widget_key = f"{demand_format}_{start_default.isoformat()}_{end_default.isoformat()}"
        date_cols = st.columns(2)
        with date_cols[0]:
            start_week = st.date_input("First planning week (Sunday)", value=start_default, key=f"upload_start_week_{horizon_widget_key}")
        with date_cols[1]:
            end_week = st.date_input("Last planning week (Sunday)", value=end_default, key=f"upload_end_week_{horizon_widget_key}")
        interpretation = st.selectbox("Demand interpretation", ["USER_PROVIDED_PLAN", "RETROSPECTIVE"], key="upload_interpretation")
        assumption_version = st.text_input("Input/assumption version", value="streamlit-user-upload-v1", key="upload_assumption_version")
        quantity_step = st.number_input("Product quantity step (0 = continuous)", min_value=0.0, value=0.0, step=1.0, key="upload_quantity_step")
        surge_pct = st.number_input("Demand surge scenario (%)", min_value=0.0, value=10.0, step=1.0, key="upload_surge_pct")
        disruption_pct = st.number_input("Capacity disruption scenario (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0, key="upload_disruption_pct")
        plants = _preview_identifiers(previews.get("plants"), mappings.get("plants", {}).get("Plant_ID"))
        plants_key = "_".join(plants) or "none"
        disrupted_plants = st.multiselect("Plant(s) affected by capacity disruption", plants, default=plants[:1], key=f"upload_disrupted_plants_{plants_key}")
        backlog_policy = st.selectbox("Shortage policy", ["CARRY_FORWARD", "LOST_SALES"], key="upload_backlog_policy")

        with st.expander("Explicit assumptions for optional or missing inputs"):
            st.caption("Assumptions are labeled SYNTHETIC_ASSUMPTION in the readiness report and run manifest.")
            quantity_unit = st.text_input("Fallback product quantity unit", value="", key="upload_quantity_unit")
            use_priority = st.checkbox("Use one assumed priority if product priority is absent", value=False, key="upload_use_priority")
            assumed_priority = st.selectbox("Assumed priority (1=lower, 3=higher)", [1, 2, 3], index=1, key="upload_assumed_priority")
            use_factor = st.checkbox("Use a uniform synthetic workload factor if factors are absent", value=False, key="upload_use_factor")
            uniform_factor = st.number_input("Workload factor per product unit", min_value=0.000001, value=1.0, step=0.25, key="upload_uniform_factor")
            workload_unit = st.text_input("Workload unit", value="EqWU", key="upload_workload_unit")
            zero_inventory = st.checkbox("Assume zero initial inventory if no inventory CSV is uploaded", value=False, key="upload_zero_inventory")
            zero_backlog = st.checkbox("Assume zero opening backlog if no backlog balance is supplied", value=False, key="upload_zero_backlog")
            no_receipts = st.checkbox("Declare that no external receipts are modeled if no receipts CSV is uploaded", value=False, key="upload_no_receipts")
            calibrate_capacity = st.checkbox("Use synthetic demand-calibrated capacity if no capacity CSV is uploaded", value=False, key="upload_calibrate_capacity")
            target_utilization = st.number_input("Synthetic capacity target utilization", min_value=0.01, max_value=1.0, value=0.75, step=0.05, key="upload_target_utilization")

        validate_clicked = st.form_submit_button("Validate inputs")
        run_clicked = st.form_submit_button("Validate and run planning", type="primary")

    if not (validate_clicked or run_clicked):
        return
    config, config_errors = _build_upload_config(
        uploads=uploads, mappings=mappings, demand_format=demand_format, status_eligibility=status_eligibility,
        already_qualified=already_qualified, source_is_complete=source_is_complete,
        quantity_step=quantity_step, assumption_version=assumption_version,
        start_week=start_week, end_week=end_week, interpretation=interpretation,
        surge_pct=surge_pct, disruption_pct=disruption_pct, disrupted_plants=disrupted_plants,
        backlog_policy=backlog_policy,
        assumptions={"quantity_unit": quantity_unit, "use_priority": use_priority, "planning_priority": assumed_priority,
                    "use_factor": use_factor, "uniform_factor": uniform_factor, "workload_unit": workload_unit,
                    "zero_inventory": zero_inventory, "zero_backlog": zero_backlog, "no_receipts": no_receipts,
                    "capacity_calibration": calibrate_capacity, "target_utilization": target_utilization},
    )
    config_errors.extend(parse_errors)
    if demand_format == "ORDER_LINES" and not status_eligibility:
        config_errors.append("Map and classify every source order status before validating order-line demand.")
    if config_errors:
        report = _blocked_upload_report(config_errors)
        report["Explicit_Configuration"] = _upload_configuration_summary(config)
    else:
        report = _validate_uploaded_config(config, uploads)
    _render_readiness_report(report)
    if run_clicked and report.get("Status") != "READY":
        st.warning("Planning was not run because data readiness is BLOCKED.")
    if run_clicked and report.get("Status") == "READY":
        output_root = REPOSITORY_ROOT / "tmp" / "planning_upgrade_runs"
        input_root = REPOSITORY_ROOT / "tmp"
        input_root.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="control_tower_upload_", dir=input_root) as temporary:
                upload_dir = Path(temporary)
                _write_upload_inputs(upload_dir, config, uploads)
                paths = run_csv_planning(config, inputs_dir=upload_dir, output_root=output_root)
            st.session_state["sequential_run_dir"] = str(paths["run_manifest"].parent)
            st.success("Planning run completed and published successfully.")
            st.caption(f"Published run: {paths['run_manifest'].parent.name}")
            st.download_button("Download run manifest", paths["run_manifest"].read_bytes(),
                               file_name="run_manifest.json", mime="application/json", key="upload_run_manifest_download")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.error(f"Planning run failed; no successful publication was produced: {exc}")
            if hasattr(exc, "report"):
                _render_readiness_report(exc.report)


def load_sequential_outputs(output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Verify a complete published run and load a consistent new-schema bundle."""
    import json
    from hashlib import sha256

    directory = Path(output_dir).resolve()
    manifest = json.loads((directory / "run_manifest.json").read_text())
    if (manifest.get("Schema_Version") != "sequential_v1"
            or manifest.get("Execution_Status") != "SUCCEEDED"
            or manifest.get("Validation_Status") != "PASSED"
            or manifest.get("Publication_Status") != "PUBLISHED"):
        raise ValueError("sequential run is incomplete, failed or unpublished")
    required = {"eligibility_ledger", "weekly_demand", "demand_coverage", "initial_state",
                "external_receipts", "workload_factors", "capacity_baseline",
                "scenario_snapshot", "capacity_pools", "allocation_result",
                "performance_result", "validation_result"}
    if not required.issubset(manifest.get("Artifacts", {})):
        raise ValueError("manifest lacks required sequential artifacts")
    for name, artifact in manifest["Artifacts"].items():
        path = (directory / artifact["Path"]).resolve()
        if path.parent != directory or not path.is_file() or sha256(path.read_bytes()).hexdigest() != artifact["SHA256"]:
            raise ValueError(f"artifact missing or hash mismatch: {name}")
    names = {"performance": "performance_result", "allocation": "allocation_result",
             "pools": "capacity_pools", "scenario": "scenario_snapshot"}
    outputs = {}
    for name, artifact_name in names.items():
        frame = pd.read_csv(directory / manifest["Artifacts"][artifact_name]["Path"], parse_dates=["Order_Date"], converters={name: str for name in ["Product Card Id", "Plant_ID", "Scenario", "Run_ID", "Schema_Version", "Product Name", "Factor_Version", "Workload_Unit"]})
        if frame.empty:
            raise ValueError(f"published sequential artifact is empty: {artifact_name}")
        if "Run_ID" not in frame or "Schema_Version" not in frame or set(frame.Run_ID) != {manifest["Run_ID"]} or set(frame.Schema_Version) != {"sequential_v1"}:
            raise ValueError(f"mixed or invalid sequential run identity: {artifact_name}")
        outputs[name] = frame
    required_allocation = {
        "Scenario", "Plant_ID", "Product Card Id", "Product Name", "Order_Date", "Planning_Priority",
        "Allocation_Order", "Scenario_Qualified_Demand", "Incremental_Demand", "Beginning_Inventory",
        "Beginning_Backlog", "External_Receipts_Qty", "Required_Production_Qty", "Internal_Production_Qty",
        "Workload_Factor", "Workload_Unit", "Allocated_Workload", "Unmet_Workload", "Unmet_Production_Qty",
        "Fulfilled_Backlog_Qty", "Fulfilled_Current_Qty", "Fulfilled_Horizon_Backlog_Qty",
        "Current_Unfulfilled_Qty", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty", "Backlog_Policy",
    }
    missing_allocation = sorted(required_allocation - set(outputs["allocation"].columns))
    if missing_allocation:
        raise ValueError(f"sequential allocation schema mismatch; missing fields: {', '.join(missing_allocation)}")
    required_pools = {"Scenario", "Plant_ID", "Order_Date", "Baseline_Workload_Capacity",
                      "Available_Workload_Capacity", "Allocated_Workload", "Remaining_Workload_Capacity",
                      "Unmet_Workload"}
    missing_pools = sorted(required_pools - set(outputs["pools"].columns))
    if missing_pools:
        raise ValueError(f"sequential capacity pool schema mismatch; missing fields: {', '.join(missing_pools)}")
    required_metrics = {"Production_Coverage_Rate", "Demand_Fulfillment_Rate", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"}
    if not required_metrics.issubset(outputs["performance"]):
        raise ValueError("sequential KPI schema mismatch")
    return outputs


def _planning_risk_summary(outputs: dict[str, pd.DataFrame], selected_scenario: str) -> None:
    """Render risk views from the already-published result artifacts."""
    try:
        product_risks = product_risk_ranking(outputs["allocation"])
        plants = plant_bottleneck_summary(outputs["pools"])
        drivers = risk_driver_details(outputs["allocation"], outputs["pools"])
        scenario_comparison = scenario_risk_comparison(outputs["performance"])
    except (KeyError, ValueError) as exc:
        st.warning(f"Planning risk summary is unavailable for this run: {exc}")
        return
    if product_risks.empty or plants.empty:
        st.info("This run has no product or plant-week records to summarize.")
        return

    product_tab, plant_tab, driver_tab, scenario_tab = st.tabs(
        ["Product Risk", "Plant Bottlenecks", "Risk Drivers", "Scenario Risk"]
    )
    current_products = product_risks[product_risks.Scenario.eq(selected_scenario)].copy()
    with product_tab:
        st.caption("Risk order uses visible service, backlog, lost-sales, and production-coverage indicators; there is no composite risk score.")
        columns = ["Risk_Category", "Product_Name", "Product Card Id", "Planning_Priority", "Plants",
                   "Qualified_Demand", "Demand_Fulfillment_Rate", "Current_Demand_Unfulfilled_Qty",
                   "Production_Coverage_Rate", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty",
                   "Unmet_Workload", "Backlog_Policy", "Risk_Reason"]
        st.dataframe(current_products[columns], hide_index=True, use_container_width=True)
        product_ids = current_products["Product Card Id"].astype(str).tolist()
        if product_ids:
            selected_product = st.selectbox("Product drill-down", product_ids, key=f"risk_product_{selected_scenario}")
            detail = current_products[current_products["Product Card Id"].astype(str).eq(selected_product)].iloc[0]
            metrics = st.columns(5)
            for card, column in zip(metrics, ["Demand_Fulfillment_Rate", "Production_Coverage_Rate", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]):
                value = detail[column]
                rendered = "N/A" if pd.isna(value) else (f"{value:.1%}" if column.endswith("Rate") else f"{value:,.2f}")
                card.metric(column.replace("_", " "), rendered)
            st.caption(detail.Risk_Reason)

    current_plants = plants[plants.Scenario.eq(selected_scenario)].copy()
    with plant_tab:
        st.dataframe(current_plants, hide_index=True, use_container_width=True)
        plant_ids = current_plants.Plant_ID.astype(str).tolist()
        if plant_ids:
            selected_plant = st.selectbox("Plant drill-down", plant_ids, key=f"risk_plant_{selected_scenario}")
            weekly = outputs["pools"].loc[
                outputs["pools"].Scenario.eq(selected_scenario)
                & outputs["pools"].Plant_ID.astype(str).eq(selected_plant)
            ].copy().sort_values("Order_Date")
            weekly["Capacity_Utilization"] = weekly.Allocated_Workload.div(
                weekly.Available_Workload_Capacity.where(weekly.Available_Workload_Capacity.ne(0))
            )
            weekly_columns = ["Order_Date", "Available_Workload_Capacity", "Allocated_Workload",
                              "Remaining_Workload_Capacity", "Capacity_Utilization", "Unmet_Workload", "Workload_Shortage"]
            st.dataframe(weekly[weekly_columns], hide_index=True, use_container_width=True)
            chart = weekly.set_index("Order_Date")["Capacity_Utilization"]
            st.bar_chart(chart)
            contributors = outputs["allocation"].loc[
                outputs["allocation"].Scenario.eq(selected_scenario)
                & outputs["allocation"].Plant_ID.astype(str).eq(selected_plant)
            ].groupby(["Product Card Id", "Product Name", "Planning_Priority"], as_index=False).agg(
                Allocated_Workload=("Allocated_Workload", "sum"),
                Unmet_Workload=("Unmet_Workload", "sum"),
                Required_Production_Qty=("Required_Production_Qty", "sum"),
                Internal_Production_Qty=("Internal_Production_Qty", "sum"),
            ).sort_values(["Unmet_Workload", "Allocated_Workload", "Planning_Priority"],
                          ascending=[False, False, False], kind="mergesort")
            st.markdown("**Products associated with this plant's workload pressure**")
            st.dataframe(contributors, hide_index=True, use_container_width=True)

    current_drivers = drivers[drivers.Scenario.eq(selected_scenario)].copy()
    with driver_tab:
        st.caption("Signals show conditions observed in the same product/plant/week. They are not validated causal attributions. Workload factors and capacity baselines retain the run's declared provenance and assumptions.")
        products = current_drivers[["Product Card Id", "Product Name"]].drop_duplicates().sort_values("Product Name")
        if not products.empty:
            selected_product = st.selectbox(
                "Product whose risk signals to inspect", products["Product Card Id"].astype(str).tolist(),
                key=f"risk_driver_product_{selected_scenario}",
            )
            selected_rows = current_drivers[
                current_drivers["Product Card Id"].astype(str).eq(selected_product)
            ].sort_values(["Order_Date", "Plant_ID", "Allocation_Order"])
            driver_columns = ["Order_Date", "Plant_ID", "Product Card Id", "Planning_Priority", "Allocation_Order",
                              "Scenario_Qualified_Demand", "Incremental_Demand", "Beginning_Inventory", "Beginning_Backlog",
                              "Workload_Factor", "Workload_Unit", "Required_Production_Qty", "Internal_Production_Qty",
                              "Unmet_Production_Qty", "Product_Allocated_Workload", "Product_Unmet_Workload",
                              "Available_Workload_Capacity", "Plant_Week_Allocated_Workload", "Remaining_Workload_Capacity",
                              "Plant_Week_Unmet_Workload", "Plant_Week_Capacity_Utilization",
                              "Capacity_Reduction_From_Baseline", "Ending_Backlog", "Lost_Sales_Qty", "Risk_Signals"]
            st.dataframe(selected_rows[driver_columns], hide_index=True, use_container_width=True)
            constrained = selected_rows[selected_rows.Plant_Week_Unmet_Workload.gt(1e-9)]
            if not constrained.empty:
                pressure = constrained.sort_values(["Plant_Week_Unmet_Workload", "Order_Date"],
                                                   ascending=[False, True]).iloc[0]
                peers = current_drivers[
                    current_drivers.Plant_ID.eq(pressure.Plant_ID)
                    & current_drivers.Order_Date.eq(pressure.Order_Date)
                ].sort_values("Allocation_Order")
                st.markdown(f"**Priority allocation context: {pressure.Plant_ID}, {pressure.Order_Date:%Y-%m-%d}**")
                st.dataframe(peers[["Product Name", "Product Card Id", "Planning_Priority", "Allocation_Order",
                                    "Required_Production_Qty", "Internal_Production_Qty", "Product_Unmet_Workload",
                                    "Product_Allocated_Workload", "Risk_Signals"]], hide_index=True, use_container_width=True)

    with scenario_tab:
        st.caption("Deltas are descriptive comparisons to Baseline. Backlog_Policy is shown because policy changes also affect service, backlog, and lost-sales outcomes.")
        st.dataframe(scenario_comparison, hide_index=True, use_container_width=True)
        if selected_scenario != "Baseline":
            product_changes = scenario_product_deterioration(product_risks, selected_scenario)
            plant_changes = scenario_plant_deterioration(outputs["performance"], selected_scenario)
            st.markdown("**Largest product deterioration versus Baseline**")
            if product_changes.empty:
                st.info("A Baseline or matching product outcome is unavailable for this comparison.")
            else:
                st.dataframe(product_changes[["Product_Name", "Product Card Id", "Demand_Fulfillment_Change",
                                              "Ending_Backlog_Change", "Lost_Sales_Change", "Baseline_Backlog_Policy",
                                              "Backlog_Policy", "Backlog_Policy_Changed", "Risk_Category", "Risk_Reason"]].head(10),
                             hide_index=True, use_container_width=True)
            st.markdown("**Largest plant deterioration versus Baseline**")
            if plant_changes.empty:
                st.info("A Baseline or matching plant KPI is unavailable for this comparison.")
            else:
                plant_change_columns = ["Plant_ID", "Demand_Fulfillment_Rate_Change", "Production_Coverage_Rate_Change",
                                        "Ending_Backlog_Change", "Lost_Sales_Qty_Change", "Capacity_Utilization_Change",
                                        "Baseline_Backlog_Policy", "Backlog_Policy", "Backlog_Policy_Changed"]
                if "Bottleneck_Plant_Weeks_Change" in plant_changes:
                    plant_change_columns.insert(6, "Bottleneck_Plant_Weeks_Change")
                st.dataframe(plant_changes[plant_change_columns].head(10),
                             hide_index=True, use_container_width=True)


def _sequential_views() -> None:
    """Expose the upgraded prepared outputs without another dashboard redesign."""
    st.caption("Sequential model: explicit demand eligibility, workload, starting stock and receipt assumptions. Historical independent-week outputs remain separate.")
    input_method = st.radio("Planning input", ["Upload CSV data", "Use existing JSON configuration"], horizontal=True)
    if input_method == "Upload CSV data":
        _restore_user_upload_state()
        _user_csv_upload_workflow()
    else:
        config_text = st.sidebar.text_input("Sequential configuration JSON", value="examples/planning/synthetic_demo/config.json")
        if st.sidebar.button("Run sequential planning", type="primary"):
            try:
                path = Path(config_text)
                path = path if path.is_absolute() else REPOSITORY_ROOT / path
                configuration = json.loads(path.read_text())
                if "data_mode" in configuration:
                    paths = run_csv_planning(configuration, inputs_dir=path.parent,
                                             output_root=REPOSITORY_ROOT / "tmp/planning_upgrade_runs")
                else:
                    paths = run_sequential_planning(DATA_ROOT, configuration, inputs_dir=path.parent,
                                                   output_root=REPOSITORY_ROOT / "tmp/planning_upgrade_runs")
                st.session_state["sequential_run_dir"] = str(paths["run_manifest"].parent)
                st.sidebar.success("Planning run completed and published.")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                st.sidebar.error(str(exc))
                if hasattr(exc, "report"):
                    _render_readiness_report(exc.report)
    selected_path = st.sidebar.text_input("Published sequential run folder", value=st.session_state.get("sequential_run_dir", ""))
    if not selected_path:
        st.info("Provide explicit configuration or select a published sequential run. No business assumptions are applied automatically.")
        return
    try:
        run_dir = Path(selected_path)
        run_dir = run_dir if run_dir.is_absolute() else REPOSITORY_ROOT / run_dir
        outputs = load_sequential_outputs(run_dir)
        manifest = json.loads((run_dir / "run_manifest.json").read_text())
    except (OSError, ValueError, KeyError) as exc:
        st.warning(str(exc))
        return
    st.caption(f"Active results: {manifest['Run_ID']} · {manifest.get('Data_Mode', 'reference input')} · {manifest['Configuration']['assumption_version']} · {manifest['Configuration']['planning_interpretation']}")
    st.markdown("**Published outputs**")
    downloads = st.columns(3)
    for column, filename, label, mime in [
        (downloads[0], "performance_result.csv", "Download KPI results", "text/csv"),
        (downloads[1], "allocation_result.csv", "Download allocation detail", "text/csv"),
        (downloads[2], "run_manifest.json", "Download run manifest", "application/json"),
    ]:
        column.download_button(label, (run_dir / filename).read_bytes(), file_name=filename, mime=mime)
    with st.expander("Active assumptions and planning scope"):
        st.json({"Configuration": manifest["Configuration"], "Scope": manifest.get("Scope", {}), "Input_Validation": manifest.get("Input_Validation", {}), "Limitations": manifest["Limitations"]})
    performance = outputs["performance"]
    summary = scenario_kpis(performance)
    scenario = st.selectbox("Sequential scenario", summary.Scenario.tolist())
    row = summary[summary.Scenario.eq(scenario)].iloc[0]
    cards = st.columns(5)
    for card, column in zip(cards, ["Production_Coverage_Rate", "Demand_Fulfillment_Rate", "Capacity_Utilization", "Ending_Backlog", "Lost_Sales_Qty"]):
        value = row[column]
        card.metric(column.replace("_", " "), "N/A" if pd.isna(value) else (f"{value:.1%}" if column.endswith("Rate") or column == "Capacity_Utilization" else f"{value:,.2f}"))
    st.caption("0/0 ratios are N/A. Scenario fulfillment includes later service of horizon-origin backlog; weekly fulfillment refers to that week's current-demand cohort. Ending stocks are never summed across weeks.")
    overview, comparison, detail, risk = st.tabs(
        ["Scenario Overview", "Scenario Comparison", "Capacity Allocation Detail", "Planning Risk Summary"]
    )
    with overview:
        weekly = performance[performance.Aggregation_Level.eq("Scenario × Week") & performance.Scenario.eq(scenario)]
        st.line_chart(weekly.set_index("Order_Date")[["Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]])
        st.dataframe(outputs["pools"][outputs["pools"].Scenario.eq(scenario)], hide_index=True, use_container_width=True)
    with comparison:
        st.dataframe(summary, hide_index=True, use_container_width=True)
    with detail:
        frame = outputs["allocation"][outputs["allocation"].Scenario.eq(scenario)]
        columns = ["Order_Date", "Plant_ID", "Product Card Id", "Planning_Priority", "Allocation_Order",
                   "Scenario_Qualified_Demand", "Beginning_Inventory", "Beginning_Backlog", "External_Receipts_Qty",
                   "Required_Production_Qty", "Internal_Production_Qty", "Workload_Factor", "Allocated_Workload",
                   "Fulfilled_Backlog_Qty", "Fulfilled_Current_Qty", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]
        st.dataframe(frame[columns].sort_values(["Order_Date", "Plant_ID", "Allocation_Order"]), hide_index=True, use_container_width=True)
    with risk:
        _planning_risk_summary(outputs, scenario)

def main() -> None:
    st.set_page_config(page_title="Scenario Planning Decision Support", layout="wide")
    _capture_user_upload_state()
    st.title("Scenario Planning Decision Support")
    st.info("Sequential planning accepts the portable synthetic demo or your CSV data. The existing monitoring PBIX and DataCo reference are optional.")
    if st.sidebar.selectbox("Planning model", ["Sequential workload", "Legacy independent weeks"]) == "Sequential workload":
        _sequential_views()
        return
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
