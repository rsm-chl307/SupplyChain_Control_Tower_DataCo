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

from dashboard.i18n import t, localize, diagnostic, current_locale
from dashboard.display_metadata import label as display_label, help_text, METRICS, STATUS, COHORTS
from dashboard.copilot_locale import render_copilot_locale_selector
from dashboard.copilot_view import render as render_copilot

from src.run_planning import PlanningRunError, run_csv_planning, run_planning, run_sequential_planning
from src.planning_risk import (
    filter_investigation_evidence,
    investigation_evidence_csv,
    investigation_views,
    plant_bottleneck_summary,
    product_risk_ranking,
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
        card.metric(localize(label), value)


def _run_controls() -> None:
    st.sidebar.header(t('ui.run_controls.6d1271759214'))
    start = st.sidebar.date_input(t('ui.run_controls.41a591c1a92a'), value=pd.Timestamp("2017-01-01").date(), key='ui_run_controls_date_input_2')
    end = st.sidebar.date_input(t('ui.run_controls.f2f154d87898'), value=pd.Timestamp("2017-12-31").date(), key='ui_run_controls_date_input_3')
    demand_pct = st.sidebar.number_input(t('ui.run_controls.3f4ea5cf5e11'), min_value=0.0, value=10.0, step=1.0, key='ui_run_controls_number_input_4')
    capacity_pct = st.sidebar.number_input(
        t('ui.run_controls.135bc0b63887'), min_value=0.0, max_value=100.0, value=20.0, step=1.0
    , key='ui_run_controls_number_input_5')
    if not (PROCESSED_ROOT / "planning_snapshot.csv").exists():
        st.sidebar.info(t('ui.run_controls.0b25b0d4b035'))
        return
    plants = pd.read_csv(PROCESSED_ROOT / "planning_snapshot.csv", usecols=["Plant_ID"])["Plant_ID"].dropna().unique().tolist()
    disruption_plant = st.sidebar.selectbox(t('ui.run_controls.39b3fb4803d5'), sorted(plants), index=0, key='ui_run_controls_selectbox_6')
    if st.sidebar.button(t('ui.run_controls.b18bba05ab1d'), type="primary", key='ui_run_controls_button_7'):
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
            st.sidebar.success(t('ui.run_controls.add943564be9'))
        except (PlanningRunError, FileNotFoundError, ValueError) as exc:
            st.sidebar.error(diagnostic(str(exc)))


def _overview(performance: pd.DataFrame, scenario: pd.DataFrame) -> None:
    st.subheader(t('nav.scenario_overview'))
    selected = st.selectbox(t('ui.overview.2fcb5d374697'), scenario["Scenario"].tolist(), key='ui_overview_selectbox_2')
    row = scenario.loc[scenario["Scenario"].eq(selected)].iloc[0]
    _render_kpi_cards(row)
    st.caption(t('ui.overview.44e116cb23c9'))
    plant_rows = performance[
        (performance["Aggregation_Level"] == "Scenario × Plant")
        & (performance["Scenario"] == selected)
    ]
    if not plant_rows.empty and px is not None:
        fig = _plotly_bar(plant_rows, x="Plant_ID", y="Capacity_Utilization", color="Performance_Status", title="Capacity utilization by plant")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)



def _display_scenario_insight(message: str, *, locale: str | None = None) -> str:
    """Translate owned legacy summary templates; keep dynamic IDs/statuses raw."""
    import re
    patterns = [
        (r'Greatest capacity pressure: (.*) \((.*) utilization versus Baseline\)\.',
         'insight.pressure', ('scenario', 'change')),
        (r'Backlog is created by: (.*)\.', 'insight.backlog', ('scenarios',)),
        (r'Performance status: (.*)\.', 'insight.status', ('statuses',)),
    ]
    for pattern, key, names in patterns:
        match = re.fullmatch(pattern, message)
        if match:
            params = dict(zip(names, match.groups()))
            if 'change' in params:
                params['change'] = params['change'].replace(
                    ' percentage points', ' ' + t('unit.percentage_points', locale=locale))
            return t(key, locale=locale, **params)
    return localize(message, locale=locale)


def _comparison(performance: pd.DataFrame) -> None:
    st.subheader(t('nav.scenario_comparison'))
    comparison = scenario_comparison(performance)
    st.caption(t('ui.comparison.b49820e435da'))
    display_table = comparison_display_table(performance)
    for column in ('Service_Level_Change', 'Capacity_Utilization_Change', 'Allocation_Rate_Change'):
        display_table[column] = display_table[column].str.replace(
            'percentage points', t('unit.percentage_points'), regex=False)
    _display_dataframe(display_table, use_container_width=True, hide_index=True)
    if px is None:
        st.caption(t('ui.comparison.72250b005b4e'))
        for insight in scenario_insights(performance):
            st.write(t('ui.render_readiness_report.9a4a817443e2' , p0=_display_scenario_insight(insight)))
        return
    chart = comparison.melt(
        id_vars="Scenario",
        value_vars=["Service_Level", "Capacity_Utilization", "Allocation_Rate"],
        var_name="KPI",
        value_name="Value",
    )
    fig = _plotly_bar(
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
    change_fig = _plotly_bar(
        changes, x="KPI", y="Change", color="Scenario", barmode="group",
        title="Scenario impact versus Baseline (percentage points)",
    )
    change_fig.update_yaxes(tickformat="+.2%")
    st.plotly_chart(change_fig, use_container_width=True)
    st.markdown(t('ui.comparison.d22f11ca25a3'))
    for insight in scenario_insights(performance):
        st.write(t('ui.render_readiness_report.9a4a817443e2' , p0=_display_scenario_insight(insight)))
    backlog_fig = _plotly_bar(
        comparison, x="Scenario", y="Total_Backlog", color="Scenario",
        title="Backlog impact by scenario",
    )
    st.plotly_chart(backlog_fig, use_container_width=True)


def _allocation_detail(allocation: pd.DataFrame) -> None:
    st.subheader(t('nav.capacity_allocation_detail'))
    scenarios = sorted(allocation["Scenario"].unique())
    scenario = st.selectbox(t('ui.allocation_detail.96f7a6b3a027'), scenarios, key="detail_scenario")
    frame = allocation[allocation["Scenario"].eq(scenario)]
    plants = sorted(frame["Plant_ID"].unique())
    plant = st.selectbox(t('ui.allocation_detail.0bd287f6ce17'), plants, key="detail_plant")
    frame = frame[frame["Plant_ID"].eq(plant)]
    # Capacity is shared at Scenario × Plant × Week; use prepared Stage 5
    # plant KPIs rather than summing repeated row capacity.
    try:
        output_dir = Path(st.session_state.get("scenario_output_dir", _default_output_dir()))
        performance = load_dashboard_outputs(output_dir)["performance"]
        summary = allocation_plant_summary(allocation, performance)
        _display_dataframe(
            summary[(summary["Scenario"] == scenario) & (summary["Plant_ID"] == plant)],
            use_container_width=True, hide_index=True,
        )
    except (FileNotFoundError, ValueError):
        st.warning(t('ui.allocation_detail.40a0b2213a9f'))
    columns = [
        "Order_Date", "Product Card Id", "Product Name", "Planning_Priority",
        "Net_Demand", "Allocated_Qty", "Backlog", "Remaining_Capacity", "Allocation_Reason",
    ]
    _display_dataframe(frame[columns].sort_values(["Order_Date", "Planning_Priority", "Product Card Id"], ascending=[True, False, True]), use_container_width=True, hide_index=True)



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
    with st.expander(t('ui.render_column_mapping.1aa8bdd83602' , p0=localize(CSV_INPUT_SCHEMAS[dataset][0]), p1=len(preview)), expanded=False):
        st.caption(t('ui.render_column_mapping.1f745027bf3c'))
        st.selectbox(t('ui.render_column_mapping.168dc92a7edb'), ["USER_PROVIDED", "SYNTHETIC", "SYNTHETIC_EXAMPLE", "DERIVED", "REFERENCE_INPUT"],
                     key=f"provenance_{dataset}", help=t('ui.render_column_mapping.3e1ff823b2c1'), format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
        for canonical in [*required, *optional]:
            suggested = _suggested_column(canonical, columns)
            options = ["— not provided —", *columns]
            index = options.index(suggested) if suggested else 0
            selected = st.selectbox(
                t('ui.render_column_mapping.380e3dbd6730' , p0=canonical, p1=' *' if canonical in required else ''), options,
                index=index, key=f"map_{dataset}_{canonical}_{uploaded.name}",
                format_func=lambda value, locale=current_locale(): (
                    localize(value, locale=locale) if value == "— not provided —" else value),
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
        st.success(t('ui.render_readiness_report.83046a7eb880'))
    else:
        st.error(t('ui.render_readiness_report.58708ef07aaf'))
    for error in report.get("Errors", []):
        st.write(t('ui.render_readiness_report.9a4a817443e2' , p0=error))
    for warning in report.get("Warnings", []):
        st.caption(t('ui.render_readiness_report.4f8744d1dc3a' , p0=localize(warning)))
    capabilities = report.get("Capabilities", {})
    if capabilities:
        _display_dataframe(pd.DataFrame([{"Capability": key, "Status": value} for key, value in capabilities.items()]),
                     hide_index=True, use_container_width=True)
    sources = report.get("Sources", [])
    if sources:
        st.markdown(t('ui.render_readiness_report.2271a9da1e2f'))
        view = pd.DataFrame(sources)
        columns = [column for column in ["Dataset", "Rows", "Columns", "Classification", "Version"] if column in view]
        _display_dataframe(view[columns], hide_index=True, use_container_width=True)
    assumptions = report.get("Assumptions", [])
    if assumptions:
        st.markdown(t('ui.render_readiness_report.82be97b2a77c'))
        _display_dataframe(pd.DataFrame(assumptions), hide_index=True, use_container_width=True)
    derived = report.get("Derived_Values", [])
    if derived:
        with st.expander(t('ui.render_readiness_report.b5effd83e40f')):
            st.json(derived)
    configured = report.get("Explicit_Configuration")
    if configured:
        with st.expander(t('ui.render_readiness_report.05fa93f3271e')):
            st.json(configured)
    unavailable = report.get("Unavailable_Capabilities", [])
    if unavailable:
        st.caption(localize("Unavailable capabilities: ") + (", ".join(unavailable)))


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
    st.subheader(t('ui.user_csv_upload_workflow.9cc5634cda5d'))
    st.caption(t('ui.user_csv_upload_workflow.7f92cfa151a3'))
    demand_format = st.radio(t('ui.user_csv_upload_workflow.b95a1f51b901'), ["WEEKLY", "ORDER_LINES"], horizontal=True, key="upload_demand_format", format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
    required_uploads = {"products", "plants", "product_plant_mapping", "demand"}
    st.markdown(t('ui.user_csv_upload_workflow.2098ebab834b'))
    with st.expander(t('ui.user_csv_upload_workflow.02d310afbef5')):
        template_columns = st.columns(3)
        template_names = ["products", "plants", "product_plant_mapping", "demand", "weekly_capacity",
                          "initial_inventory", "workload_factors", "external_receipts", "opening_backlog"]
        for index, name in enumerate(template_names):
            path = REPOSITORY_ROOT / "examples" / "planning" / "templates" / f"{name}.csv"
            template_columns[index % 3].download_button(t('ui.user_csv_upload_workflow.6fa9e12bf7fc' , p0=localize(CSV_INPUT_SCHEMAS[name][0])),
                path.read_bytes(), file_name=f"{name}.csv", mime="text/csv", key=f"download_template_{name}")

    uploads: dict[str, object] = {}
    previews: dict[str, pd.DataFrame | None] = {}
    parse_errors: list[str] = []
    upload_columns = st.columns(2)
    for index, (dataset, (label, _, _)) in enumerate(CSV_INPUT_SCHEMAS.items()):
        with upload_columns[index % 2]:
            st.file_uploader(t('ui.user_csv_upload_workflow.8cbaa55a52ef' , p0=localize(label), p1=t('upload.required') if dataset in required_uploads else t('upload.optional')),
                             type=["csv"], accept_multiple_files=False, key=f"upload_widget_{dataset}")
        uploaded = st.session_state.get(f"upload_widget_{dataset}")
        if uploaded is not None:
            st.session_state.setdefault(_USER_UPLOAD_DATA_KEY, {})[dataset] = (uploaded.name, uploaded.getvalue())
        else:
            retained = st.session_state.get(_USER_UPLOAD_DATA_KEY, {}).get(dataset)
            if retained is not None:
                uploaded = _StoredCSVUpload(*retained)
                st.caption(t('ui.user_csv_upload_workflow.3de7154cc847' , p0=uploaded.name))
        uploads[dataset] = uploaded
        if uploaded is not None:
            previews[dataset], error = _csv_preview(uploaded)
            if error:
                parse_errors.append(error)

    status_rows = [
        {"Dataset": localize(label), "Requirement": localize("Required" if dataset in required_uploads else "Optional / assumption may replace"),
         "Status": localize("Uploaded" if uploads[dataset] is not None else "Missing")}
        for dataset, (label, _, _) in CSV_INPUT_SCHEMAS.items()
    ]
    _display_dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)
    for error in parse_errors:
        st.error(diagnostic(error))

    already_qualified = False
    source_is_complete = False
    with st.form("user_csv_planning_form"):
        st.markdown(t('ui.user_csv_upload_workflow.6ef555493380'))
        mappings = {
            dataset: _render_column_mapping(dataset, previews.get(dataset), demand_format, uploads[dataset])
            for dataset, uploaded in uploads.items() if uploaded is not None and previews.get(dataset) is not None
        }
        demand_preview = previews.get("demand")
        status_source = mappings.get("demand", {}).get("Status")
        status_values = sorted(demand_preview[status_source].astype(str).unique().tolist()) if demand_preview is not None and status_source else []
        status_eligibility: dict[str, bool] = {}
        if status_values:
            st.markdown(t('ui.user_csv_upload_workflow.b5718aaa4a47'))
            st.caption(t('ui.user_csv_upload_workflow.74f27912d7a7'))
            for index, status in enumerate(status_values):
                choice = st.selectbox(t('ui.user_csv_upload_workflow.7f61c6cb867b' , p0=status), ["Choose…", "Qualified", "Excluded"],
                                      key=f"eligibility_{index}_{status}", format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
                if choice != "Choose…":
                    status_eligibility[status] = choice == "Qualified"
        elif demand_format == "WEEKLY" and demand_preview is not None:
            already_qualified = st.checkbox(t('ui.user_csv_upload_workflow.49d6ae885be6'), value=False, key='upload_ui_user_csv_upload_workflow_checkbox_43')
        elif demand_format == "ORDER_LINES" and demand_preview is not None:
            source_is_complete = st.checkbox(t('ui.user_csv_upload_workflow.2982f08bede9'), value=False,
                                               help=t('ui.user_csv_upload_workflow.12ba9cf2e711'), key='upload_ui_user_csv_upload_workflow_checkbox_45')

        st.markdown(t('ui.user_csv_upload_workflow.7cf9fcf017be'))
        start_default, end_default = _suggested_horizon(demand_preview, mappings.get("demand", {}), demand_format)
        horizon_widget_key = f"{demand_format}_{start_default.isoformat()}_{end_default.isoformat()}"
        date_cols = st.columns(2)
        with date_cols[0]:
            start_week = st.date_input(t('ui.user_csv_upload_workflow.3e0fd01065a6'), value=start_default, key=f"upload_start_week_{horizon_widget_key}")
        with date_cols[1]:
            end_week = st.date_input(t('ui.user_csv_upload_workflow.c2e1866609b6'), value=end_default, key=f"upload_end_week_{horizon_widget_key}")
        interpretation = st.selectbox(t('ui.user_csv_upload_workflow.f1b413244e48'), ["USER_PROVIDED_PLAN", "RETROSPECTIVE"], key="upload_interpretation", format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
        assumption_version = st.text_input(t('ui.user_csv_upload_workflow.838b1873c8ea'), value="streamlit-user-upload-v1", key="upload_assumption_version")
        quantity_step = st.number_input(t('ui.user_csv_upload_workflow.b0fa4241919e'), min_value=0.0, value=0.0, step=1.0, key="upload_quantity_step")
        surge_pct = st.number_input(t('ui.user_csv_upload_workflow.363490b8991e'), min_value=0.0, value=10.0, step=1.0, key="upload_surge_pct")
        disruption_pct = st.number_input(t('ui.user_csv_upload_workflow.8571395c8005'), min_value=0.0, max_value=100.0, value=20.0, step=1.0, key="upload_disruption_pct")
        plants = _preview_identifiers(previews.get("plants"), mappings.get("plants", {}).get("Plant_ID"))
        plants_key = "_".join(plants) or "none"
        disrupted_plants = st.multiselect(t('ui.user_csv_upload_workflow.955fc3a56a5a'), plants, default=plants[:1], key=f"upload_disrupted_plants_{plants_key}")
        backlog_policy = st.selectbox(t('ui.user_csv_upload_workflow.3d234b7e424e'), ["CARRY_FORWARD", "LOST_SALES"], key="upload_backlog_policy", format_func=lambda value, locale=current_locale(): localize(value, locale=locale))

        with st.expander(t('ui.user_csv_upload_workflow.53f5e4818535')):
            st.caption(t('ui.user_csv_upload_workflow.984844251384'))
            quantity_unit = st.text_input(t('ui.user_csv_upload_workflow.52a08ee9a085'), value="", key="upload_quantity_unit")
            use_priority = st.checkbox(t('ui.user_csv_upload_workflow.350885b217bf'), value=False, key="upload_use_priority")
            assumed_priority = st.selectbox(t('ui.user_csv_upload_workflow.c7bb626a504f'), [1, 2, 3], index=1, key="upload_assumed_priority", format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
            use_factor = st.checkbox(t('ui.user_csv_upload_workflow.0d92b4c13ed0'), value=False, key="upload_use_factor")
            uniform_factor = st.number_input(t('ui.user_csv_upload_workflow.540c922746b5'), min_value=0.000001, value=1.0, step=0.25, key="upload_uniform_factor")
            workload_unit = st.text_input(t('ui.user_csv_upload_workflow.2cfdc8a6fe8f'), value="EqWU", key="upload_workload_unit")
            zero_inventory = st.checkbox(t('ui.user_csv_upload_workflow.92ca2fc427c4'), value=False, key="upload_zero_inventory")
            zero_backlog = st.checkbox(t('ui.user_csv_upload_workflow.99caf326c4ba'), value=False, key="upload_zero_backlog")
            no_receipts = st.checkbox(t('ui.user_csv_upload_workflow.c67ea6e1d864'), value=False, key="upload_no_receipts")
            calibrate_capacity = st.checkbox(t('ui.user_csv_upload_workflow.e10917b8fa24'), value=False, key="upload_calibrate_capacity")
            target_utilization = st.number_input(t('ui.user_csv_upload_workflow.a73f263428d9'), min_value=0.01, max_value=1.0, value=0.75, step=0.05, key="upload_target_utilization")

        _language_form()
        validate_clicked = st.form_submit_button(t('ui.user_csv_upload_workflow.9e85075f0c01'))
        run_clicked = st.form_submit_button(t('ui.user_csv_upload_workflow.6e3fe7846156'), type="primary")

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
        st.warning(t('ui.user_csv_upload_workflow.9c7c07f5dd1a'))
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
            st.success(t('ui.user_csv_upload_workflow.126182d571c2'))
            st.caption(t('ui.user_csv_upload_workflow.5bfc977fc3da' , p0=paths['run_manifest'].parent.name))
            st.download_button(t('ui.user_csv_upload_workflow.9632aff0f596'), paths["run_manifest"].read_bytes(),
                               file_name="run_manifest.json", mime="application/json", key="upload_run_manifest_download")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.error(t('ui.user_csv_upload_workflow.528c97a07ea8' , p0=exc))
            if hasattr(exc, "report"):
                _render_readiness_report(exc.report)


# Evidence stays at its published grain; receipts may legitimately have no rows.
INVESTIGATION_EVIDENCE_COLUMNS = {
    "eligibility_ledger": ["Plant_ID", "Product Card Id", "Order_Date", "Gross_Demand",
                           "Qualified_Demand", "Excluded_Demand", "Is_Qualified", "Exclusion_Reason"],
    "weekly_demand": ["Plant_ID", "Product Card Id", "Order_Date", "Qualified_Demand", "Coverage_Status"],
    "demand_coverage": ["Plant_ID", "Product Card Id", "Order_Date", "Coverage_Status"],
    "initial_state": ["Plant_ID", "Product Card Id", "Beginning_Inventory", "Beginning_Backlog"],
    "external_receipts": ["Receipt_ID", "Plant_ID", "Product Card Id", "Order_Date", "External_Receipts_Qty"],
    "workload_factors": ["Product Card Id", "Workload_Factor", "Workload_Unit", "Factor_Version"],
    "capacity_baseline": ["Plant_ID", "Baseline_Workload_Capacity"],
    "validation_result": ["Check_ID", "Message", "Passed", "Rows_Checked"],
}


def investigation_source_status(manifest: dict) -> pd.DataFrame:
    """Report source availability/integrity without using source files as results."""
    from hashlib import sha256

    hashes = manifest.get("Source_Hashes", {})
    sources = manifest.get("Input_Validation", {}).get("Sources", [])
    if not sources:
        sources = [{"Dataset": "source", "Path": path} for path in hashes]
    rows = []
    for source in sources:
        row = dict(source)
        path = Path(source.get("Path", ""))
        expected = hashes.get(str(path))
        row["Source_SHA256"] = expected or "Unavailable"
        try:
            if not source.get("Path") or not path.is_file():
                status = "Unavailable: original source file is missing"
            elif not expected:
                status = "Unavailable: no recorded source hash"
            elif sha256(path.read_bytes()).hexdigest() != expected:
                status = "Invalid: original source hash mismatch"
            else:
                status = "Available: source hash matches"
        except OSError:
            status = "Unavailable: original source cannot be read"
        row["Source_Status"] = status
        # Mappings are descriptive JSON rather than an object-valued table cell.
        if "Column_Mapping" in row:
            row["Column_Mapping"] = json.dumps(row["Column_Mapping"], ensure_ascii=False)
        rows.append(row)
    return pd.DataFrame(rows)


def load_sequential_outputs(output_dir: str | Path, *, include_evidence: bool = False) -> dict[str, pd.DataFrame]:
    """Verify a complete published run and load a consistent new-schema bundle."""
    import json
    from hashlib import sha256

    directory = Path(output_dir).resolve()
    manifest = json.loads((directory / "run_manifest.json").read_text())
    if not isinstance(manifest, dict):
        raise ValueError("sequential manifest must be a JSON object")
    if not isinstance(manifest.get("Run_ID"), str) or not manifest["Run_ID"].strip():
        raise ValueError("manifest Run_ID must be a nonempty string")
    if (manifest.get("Schema_Version") != "sequential_v1"
            or manifest.get("Execution_Status") != "SUCCEEDED"
            or manifest.get("Validation_Status") != "PASSED"
            or manifest.get("Publication_Status") != "PUBLISHED"):
        raise ValueError("sequential run is incomplete, failed or unpublished")
    artifacts = manifest.get("Artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest Artifacts must be an object")
    for name, artifact in artifacts.items():
        if (not isinstance(artifact, dict)
                or not isinstance(artifact.get("Path"), str)
                or not isinstance(artifact.get("SHA256"), str)):
            raise ValueError(f"manifest artifact {name}: object with Path and SHA256 strings required")
    configuration = manifest.get("Configuration")
    if not isinstance(configuration, dict):
        raise ValueError("manifest Configuration must be an object")
    scenarios = configuration.get("scenarios")
    if (not isinstance(scenarios, list) or not scenarios
            or any(not isinstance(item, dict) or not isinstance(item.get("Scenario"), str)
                   or not item["Scenario"].strip() for item in scenarios)):
        raise ValueError("manifest Configuration.scenarios must be a list of scenario objects")
    for field in ("assumption_version", "planning_interpretation"):
        if not isinstance(configuration.get(field), str):
            raise ValueError(f"manifest Configuration.{field} must be a string")
    scope = manifest.get("Scope")
    if not isinstance(scope, dict):
        raise ValueError("manifest Scope must be an object")
    bounds = scope.get("Planning_Horizon")
    if not isinstance(bounds, list) or len(bounds) != 2 or not all(isinstance(v, str) for v in bounds):
        raise ValueError("manifest Scope.Planning_Horizon must contain two date strings")
    products = scope.get("Product_IDs")
    if not isinstance(products, list) or not products:
        raise ValueError("manifest Scope.Product_IDs must be a nonempty list")
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
    if include_evidence:
        names.update({name: name for name in sorted(required - set(names.values()))})
    outputs = {}
    for name, artifact_name in names.items():
        path = directory / manifest["Artifacts"][artifact_name]["Path"]
        header = pd.read_csv(path, nrows=0)
        identifiers = ["Product Card Id", "Plant_ID", "Scenario", "Run_ID", "Schema_Version",
                       "Product Name", "Factor_Version", "Workload_Unit", "Order Item Id",
                       "Source_Record_ID", "Receipt_ID", "Order Status", "Status", "Quantity_Unit"]
        identifiers.extend(column for column in header if column.endswith("_Version"))
        frame = pd.read_csv(path, parse_dates=["Order_Date"] if "Order_Date" in header else [],
                            converters={column: str for column in identifiers})
        if frame.empty and artifact_name != "external_receipts":
            raise ValueError(f"published sequential artifact is empty: {artifact_name}")
        if "Run_ID" not in frame or "Schema_Version" not in frame or (not frame.empty and (set(frame.Run_ID) != {manifest["Run_ID"]} or set(frame.Schema_Version) != {"sequential_v1"})):
            raise ValueError(f"mixed or invalid sequential run identity: {artifact_name}")
        if "Order_Date" in frame:
            frame["Order_Date"] = pd.to_datetime(frame.Order_Date, errors="raise")
            if artifact_name != "performance_result" and frame.Order_Date.isna().any():
                raise ValueError(f"invalid evidence week: {artifact_name}")
        if include_evidence and artifact_name in INVESTIGATION_EVIDENCE_COLUMNS:
            missing = set(INVESTIGATION_EVIDENCE_COLUMNS[artifact_name]) - set(frame.columns)
            if missing:
                raise ValueError(f"investigation evidence schema mismatch: {artifact_name}: {', '.join(sorted(missing))}")
            from src.planning_inputs import numeric

            quantities = [column for column in ["Gross_Demand", "Qualified_Demand", "Excluded_Demand",
                          "Beginning_Inventory", "Beginning_Backlog", "External_Receipts_Qty",
                          "Workload_Factor", "Baseline_Workload_Capacity"] if column in frame]
            if artifact_name != "demand_coverage":
                numeric(frame, quantities)
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


def _investigation_select(label: str, values: list, key: str):
    """Reset stale dependent selections after changing run/scenario/parent."""
    if st.session_state.get(key) not in values:
        st.session_state[key] = values[0]
    return st.selectbox(localize(label), values, key=key, format_func=(lambda value, locale=current_locale(): localize(value, locale=locale)) if key == "investigation_path" else str)


def _root_cause_investigation(outputs: dict[str, pd.DataFrame], scenario: str,
                             manifest: dict | None) -> None:
    """Explore published observations; widget reruns never execute planning."""
    st.caption(t('ui.root_cause_investigation.c3a4a7323672'))
    source = outputs["allocation"]
    run_id = manifest["Run_ID"] if manifest else str(source.Run_ID.iloc[0])
    source = source.loc[source.Run_ID.eq(run_id) & source.Scenario.eq(scenario)]
    if source.empty:
        st.info(t('ui.root_cause_investigation.f0fbb975f965'))
        return
    scope = (run_id, scenario)
    if st.session_state.get("investigation_scope") != scope:
        st.session_state["investigation_scope"] = scope
        st.session_state.pop("investigation_entry", None)
        for key in ["investigation_path", "investigation_product", "investigation_plant", "investigation_week"]:
            st.session_state.pop(key, None)
    entry = st.session_state.pop("investigation_entry", None)
    if entry:
        path, identifier = entry
        st.session_state["investigation_path"] = path
        st.session_state["investigation_product" if path.startswith("Product") else "investigation_plant"] = identifier
    path = _investigation_select("Investigation path", ["Product → Plant → Week", "Plant → Week → Product"],
                                 "investigation_path")
    if path.startswith("Product"):
        product = _investigation_select("Investigation product", sorted(source["Product Card Id"].unique()), "investigation_product")
        product_rows = source.loc[source["Product Card Id"].eq(product)]
        plant = _investigation_select("Investigation plant", sorted(product_rows.Plant_ID.unique()), "investigation_plant")
        candidates = product_rows.loc[product_rows.Plant_ID.eq(plant)]
        week = _investigation_select("Investigation week (Sunday ending)", sorted(candidates.Order_Date.unique()), "investigation_week")
    else:
        plant = _investigation_select("Investigation plant", sorted(source.Plant_ID.unique()), "investigation_plant")
        plant_rows = source.loc[source.Plant_ID.eq(plant)]
        week = _investigation_select("Investigation week (Sunday ending)", sorted(plant_rows.Order_Date.unique()), "investigation_week")
        candidates = plant_rows.loc[plant_rows.Order_Date.eq(week)]
        product = _investigation_select("Investigation product", sorted(candidates["Product Card Id"].unique()), "investigation_product")
    selection = {"Run_ID": run_id, "Scenario": scenario, "Plant_ID": plant,
                 "Product Card Id": product, "Order_Date": pd.Timestamp(week)}
    try:
        views = investigation_views(outputs["allocation"], outputs["pools"], run_id=run_id,
                                    scenario=scenario, plant_id=plant, product_id=product, week=week)
    except (KeyError, ValueError) as exc:
        st.warning(t('ui.root_cause_investigation.b58419aedc5a' , p0=exc))
        return
    st.markdown(t('ui.root_cause_investigation.706e9d569554'))
    st.caption(t('ui.root_cause_investigation.5ba1b5ffa0dc' , p0=run_id, p1=scenario, p2=plant, p3=product, p4=pd.Timestamp(week)))
    selected = views["selected_week"]
    st.caption(t('ui.root_cause_investigation.64bd21a3ebc3' , p0=selected.iloc[0]['Product Name']))
    _display_dataframe(selected, hide_index=True, use_container_width=True)
    st.markdown(t('ui.root_cause_investigation.47ec66cf1ad5'))
    st.caption(t('ui.root_cause_investigation.cb672d4fb462'))
    _display_dataframe(views["shared_capacity"], hide_index=True, use_container_width=True)
    st.markdown(t('ui.root_cause_investigation.bc6f98c71a62'))
    st.write(localize(views["observed_signals"].iloc[0].Risk_Signals))
    st.markdown(t('ui.root_cause_investigation.4991f413c316'))
    st.caption(t('ui.root_cause_investigation.0bae0c0202b7'))
    _display_dataframe(views["adjacent_weeks"], hide_index=True, use_container_width=True)
    st.markdown(t('ui.root_cause_investigation.80211168d8dd'))
    st.caption(t('ui.root_cause_investigation.ae48b46f3ca1'))
    _display_dataframe(views["allocation_peers"], hide_index=True, use_container_width=True)
    st.markdown(t('ui.root_cause_investigation.1263147d9ad0'))
    st.caption(t('ui.root_cause_investigation.4018265c1bf5'))
    evidence = dict(views)
    for name in ["scenario", "performance", *INVESTIGATION_EVIDENCE_COLUMNS]:
        if name not in outputs:
            st.info(t('ui.root_cause_investigation.cc09462add8b' , p0=name))
            continue
        evidence[name] = filter_investigation_evidence(outputs[name], run_id=run_id, scenario=scenario,
                                                       plant_id=plant, product_id=product, week=week)
    notes = {
        "initial_state": "Horizon opening state, not a weekly stock reset.",
        "eligibility_ledger": "Scenario-independent source demand records. No matching records may reflect covered zero demand; inspect coverage.",
        "external_receipts": "Scheduled supply usable in the selected week. No matching rows means no scheduled external receipts for this selection.",
        "performance": "Published plant-week KPIs, not product-week KPIs. 0/0 ratios remain N/A; weekly fulfillment is the current-week cohort.",
        "validation_result": "Run-level independent validation checks, not product-specific checks.",
    }
    if manifest:
        st.caption(t('ui.root_cause_investigation.f80d05b3c651' , p0=manifest.get('Data_Mode', 'Unavailable'), p1=manifest['Configuration'].get('planning_interpretation', 'Unavailable')))
        evidence["source_status"] = investigation_source_status(manifest)
        statuses = evidence["source_status"]
        if not statuses.empty:
            if statuses.Source_Status.str.startswith("Unavailable").any():
                st.info(t('ui.root_cause_investigation.bad654eb4a3d'))
            if statuses.Source_Status.str.startswith("Invalid").any():
                st.warning(t('ui.root_cause_investigation.c7485499ec36'))
        with st.expander(t('ui.root_cause_investigation.f2b170376a90')):
            st.json({"Sources": manifest.get("Input_Validation", {}).get("Sources", []),
                     "Assumptions": manifest.get("Input_Validation", {}).get("Assumptions", []),
                     "Configuration": manifest["Configuration"], "Artifacts": manifest["Artifacts"]})
    artifact_names = {"selected_week": "allocation_result.csv", "adjacent_weeks": "allocation_result.csv",
                      "allocation_peers": "allocation_result.csv", "shared_capacity": "capacity_pools.csv",
                      "observed_signals": "derived from allocation_result.csv + capacity_pools.csv",
                      "scenario": "scenario_snapshot.csv", "performance": "performance_result.csv",
                      "source_status": "run_manifest.json"}
    for name, frame in evidence.items():
        with st.expander(t('ui.root_cause_investigation.a4f8e29dd2a8' , p0=name)):
            artifact = artifact_names.get(name, name + ".csv")
            st.caption(t('ui.root_cause_investigation.35bd85700ac8' , p0=artifact))
            if name in notes:
                st.caption(localize(notes[name]))
            if frame.empty:
                st.info(localize("No scheduled external receipts for this selection." if name == "external_receipts"
                        else "No matching published evidence rows; no records have been inferred."))
            else:
                _display_dataframe(frame, hide_index=True, use_container_width=True)
            st.download_button(t('ui.root_cause_investigation.4dea83904a8a' , p0=name), investigation_evidence_csv(frame, selection, artifact),
                               file_name=f"investigation_{name}.csv", mime="text/csv", key=f"evidence_download_{name}")


def _planning_risk_summary(outputs: dict[str, pd.DataFrame], selected_scenario: str,
                           manifest: dict | None = None) -> None:
    """Render risk views from the already-published result artifacts."""
    try:
        product_risks = product_risk_ranking(outputs["allocation"])
        plants = plant_bottleneck_summary(outputs["pools"])
        scenario_comparison = scenario_risk_comparison(outputs["performance"])
    except (KeyError, ValueError) as exc:
        st.warning(t('ui.planning_risk_summary.86545cf46740' , p0=exc))
        return
    if product_risks.empty or plants.empty:
        st.info(t('ui.planning_risk_summary.91c42de7a28e'))
        return

    product_tab, plant_tab, driver_tab, scenario_tab = st.tabs(
        [t('nav.product_risk'), t('nav.plant_bottlenecks'), t('nav.root_cause_investigation'), t('nav.scenario_risk')]
    )
    current_products = product_risks[product_risks.Scenario.eq(selected_scenario)].copy()
    with product_tab:
        st.caption(t('ui.planning_risk_summary.0d67cc257fa2'))
        columns = ["Risk_Category", "Product_Name", "Product Card Id", "Planning_Priority", "Plants",
                   "Qualified_Demand", "Demand_Fulfillment_Rate", "Current_Demand_Unfulfilled_Qty",
                   "Production_Coverage_Rate", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty",
                   "Unmet_Workload", "Backlog_Policy", "Risk_Reason"]
        _display_dataframe(current_products[columns], hide_index=True, use_container_width=True)
        product_ids = current_products["Product Card Id"].astype(str).tolist()
        if product_ids:
            selected_product = st.selectbox(t('ui.planning_risk_summary.fc629b4f441b'), product_ids, key=f"risk_product_{selected_scenario}")
            detail = current_products[current_products["Product Card Id"].astype(str).eq(selected_product)].iloc[0]
            metrics = st.columns(5)
            for card, column in zip(metrics, ["Demand_Fulfillment_Rate", "Production_Coverage_Rate", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]):
                value = detail[column]
                rendered = "N/A" if pd.isna(value) else (f"{value:.1%}" if column.endswith("Rate") else f"{value:,.2f}")
                card.metric(display_label(column, current_locale()), rendered)
            st.caption(diagnostic(detail.Risk_Reason))
            if st.button(t('ui.planning_risk_summary.cd5bf6fd2ea6'), key="investigate_product"):
                st.session_state["investigation_entry"] = ("Product → Plant → Week", selected_product)

    current_plants = plants[plants.Scenario.eq(selected_scenario)].copy()
    with plant_tab:
        _display_dataframe(current_plants, hide_index=True, use_container_width=True)
        plant_ids = current_plants.Plant_ID.astype(str).tolist()
        if plant_ids:
            selected_plant = st.selectbox(t('ui.planning_risk_summary.5b95e6edfd45'), plant_ids, key=f"risk_plant_{selected_scenario}")
            if st.button(t('ui.planning_risk_summary.f3de97961801'), key="investigate_plant"):
                st.session_state["investigation_entry"] = ("Plant → Week → Product", selected_plant)
            weekly = outputs["pools"].loc[
                outputs["pools"].Scenario.eq(selected_scenario)
                & outputs["pools"].Plant_ID.astype(str).eq(selected_plant)
            ].copy().sort_values("Order_Date")
            weekly["Capacity_Utilization"] = weekly.Allocated_Workload.div(
                weekly.Available_Workload_Capacity.where(weekly.Available_Workload_Capacity.ne(0))
            )
            weekly_columns = ["Order_Date", "Available_Workload_Capacity", "Allocated_Workload",
                              "Remaining_Workload_Capacity", "Capacity_Utilization", "Unmet_Workload", "Workload_Shortage"]
            _display_dataframe(weekly[weekly_columns], hide_index=True, use_container_width=True)
            chart = weekly.set_index("Order_Date")["Capacity_Utilization"]
            _display_bar_chart(chart)
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
            st.markdown(t('ui.planning_risk_summary.a394e9e5b9c1'))
            _display_dataframe(contributors, hide_index=True, use_container_width=True)

    with driver_tab:
        _root_cause_investigation(outputs, selected_scenario, manifest)

    with scenario_tab:
        st.caption(t('ui.planning_risk_summary.6633c852c384'))
        _display_dataframe(scenario_comparison, hide_index=True, use_container_width=True)
        if selected_scenario != "Baseline":
            product_changes = scenario_product_deterioration(product_risks, selected_scenario)
            plant_changes = scenario_plant_deterioration(outputs["performance"], selected_scenario)
            st.markdown(t('ui.planning_risk_summary.b21b25c166bb'))
            if product_changes.empty:
                st.info(t('ui.planning_risk_summary.81410b91ff2c'))
            else:
                _display_dataframe(product_changes[["Product_Name", "Product Card Id", "Demand_Fulfillment_Change",
                                              "Ending_Backlog_Change", "Lost_Sales_Change", "Baseline_Backlog_Policy",
                                              "Backlog_Policy", "Backlog_Policy_Changed", "Risk_Category", "Risk_Reason"]].head(10),
                             hide_index=True, use_container_width=True)
            st.markdown(t('ui.planning_risk_summary.3f6ef62a835c'))
            if plant_changes.empty:
                st.info(t('ui.planning_risk_summary.3a5f3bbb7287'))
            else:
                plant_change_columns = ["Plant_ID", "Demand_Fulfillment_Rate_Change", "Production_Coverage_Rate_Change",
                                        "Ending_Backlog_Change", "Lost_Sales_Qty_Change", "Capacity_Utilization_Change",
                                        "Baseline_Backlog_Policy", "Backlog_Policy", "Backlog_Policy_Changed"]
                if "Bottleneck_Plant_Weeks_Change" in plant_changes:
                    plant_change_columns.insert(6, "Bottleneck_Plant_Weeks_Change")
                _display_dataframe(plant_changes[plant_change_columns].head(10),
                             hide_index=True, use_container_width=True)


def _comparison_investigation_entry(run_id: str, scenario: str, product: str) -> None:
    """Seed the existing WP1 navigation using an explicitly chosen comparison side."""
    st.session_state["sequential_scenario"] = scenario
    st.session_state["investigation_scope"] = (run_id, scenario)
    for key in ["investigation_path", "investigation_product", "investigation_plant", "investigation_week"]:
        st.session_state.pop(key, None)
    st.session_state["investigation_entry"] = ("Product → Plant → Week", product)
    st.session_state["ui_handoff"] = (run_id, scenario, product)


def _comparison_display(frame: pd.DataFrame) -> pd.DataFrame:
    """Make unavailable comparison values explicit without altering numeric results."""
    result = frame.copy(deep=True)
    for column in result:
        if result[column].isna().any():
            result[column] = result[column].map(
                lambda value: "N/A" if pd.isna(value) else str(value))
    return result


def _scenario_tradeoff_analysis(run_dir: Path, manifest: dict) -> None:
    """Render WP2 from the pure comparison API; no planning is executed here."""
    from src.comparison_io import comparison_csv_exports, load_comparison_input
    from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results

    st.subheader(t('nav.scenario_trade_off_analysis'))
    st.caption(t('ui.scenario_tradeoff_analysis.95cf7d4c2eff'))
    scenarios = sorted(d["Scenario"] for d in manifest["Configuration"]["scenarios"])
    if st.session_state.get("wp2_run") != manifest["Run_ID"]:
        st.session_state["wp2_run"] = manifest["Run_ID"]
        # Explicit assignments synchronize the browser as well as server state.
        for key in ["wp2_reference", "wp2_candidate", "wp2_product"]:
            st.session_state[key] = None
        st.session_state["wp2_priorities"] = []
    if st.session_state.get("wp2_reference") not in scenarios:
        st.session_state["wp2_reference"] = None
    reference = st.selectbox(t('ui.scenario_tradeoff_analysis.d085d703e7f0'), scenarios, index=None,
                             placeholder=t('ui.scenario_tradeoff_analysis.45aceec1ed9a'), key="wp2_reference")
    candidates = [s for s in scenarios if s != reference]
    if st.session_state.get("wp2_candidate") not in candidates:
        # Explicit state assignment also clears the browser's displayed value.
        st.session_state["wp2_candidate"] = None
    candidate = st.selectbox(t('ui.scenario_tradeoff_analysis.be83d15cbcbd'), candidates, index=None,
                             placeholder=t('ui.scenario_tradeoff_analysis.0d9aedfe4240'), key="wp2_candidate")
    priorities = st.multiselect(t('ui.scenario_tradeoff_analysis.ce18aa647d9e'), [1, 2, 3],
                               format_func=lambda p, locale=current_locale(): t("priority.label", locale=locale, value=p), key="wp2_priorities")
    st.caption(localize("Selected reference priorities: ") + (", ".join(map(str, sorted(priorities))) if priorities else
                                                  localize("None — SELECTED is empty / N/A")))
    if reference is None or candidate is None:
        st.info(t('ui.scenario_tradeoff_analysis.b8286fc9f389'))
        return
    try:
        a = load_comparison_input(run_dir, reference)
        b = ComparisonInput(a.manifest, a.tables, candidate)
        bounds = manifest["Scope"]["Planning_Horizon"]
        scope = ComparisonScope(tuple(str(p) for p in manifest["Scope"]["Product_IDs"]),
                                tuple(sorted(a.tables["initial_state"].Plant_ID.unique())),
                                bounds[0], bounds[1], tuple(sorted(priorities)))
        result = compare_published_results(a, b, scope)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        st.error(t('ui.scenario_tradeoff_analysis.b0bbd9d34b9c' , p0=exc))
        return
    st.markdown(t('ui.scenario_tradeoff_analysis.5f1a54c23f19'))
    st.json({k: v for k, v in result.context.items() if k != "Plant_Capacity_Pool_Context"})
    if result.context['Policy_Comparison'] == 'POLICY_CONTRAST':
        st.warning(t('ui.scenario_tradeoff_analysis.2255a08a7ddc'))
    if result.context['Input_Differences']:
        st.info(localize("Changed conditioning inputs: ") + ("; ".join(result.context['Input_Differences'])))
    st.metric(t('ui.scenario_tradeoff_analysis.fd7ebbcae50b'), result.context['Priority_Changed_Product_Count'])
    st.markdown(t('ui.scenario_tradeoff_analysis.fe1b3d2b174c'))
    _display_dataframe(_comparison_display(result.cohort_membership), hide_index=True, use_container_width=True)
    st.markdown(t('ui.scenario_tradeoff_analysis.2a8de18b4368'))
    _display_dataframe(_comparison_display(result.cohort_membership.loc[
        result.cohort_membership['Priority Changed'].eq(True)]), hide_index=True, use_container_width=True)
    summary_metrics = ["Horizon_Service_Level", "Terminal_Backlog", "Lost_Sales", "Allocated_Workload", "Unmet_Workload"]
    st.markdown(t('ui.scenario_tradeoff_analysis.107667359ca6'))
    summary = result.metrics.loc[result.metrics.Metric_ID.isin(summary_metrics)]
    _display_dataframe(_comparison_display(summary), hide_index=True, use_container_width=True)
    for group, label in [("ALL", "All Products"), ("SELECTED", "Selected Cohort"), ("COMPLEMENT", "Complement")]:
        with st.expander(localize(label)):
            _display_dataframe(_comparison_display(result.metrics.loc[result.metrics.Cohort_ID.eq(group)]),
                         hide_index=True, use_container_width=True)
    with st.expander(t('ui.scenario_tradeoff_analysis.76f4ed6440a1')):
        _display_dataframe(_comparison_display(result.metrics[["Cohort_ID", "Metric_ID", "Order_Date",
                                                       "Comparability_Status", "Reason"]]),
                     hide_index=True, use_container_width=True)
    with st.expander(t('ui.scenario_tradeoff_analysis.5d1162605ac3')):
        st.caption(t('ui.scenario_tradeoff_analysis.7ad0bb282529'))
        _display_dataframe(_comparison_display(pd.DataFrame(result.context['Plant_Capacity_Pool_Context'])),
                     hide_index=True, use_container_width=True)
    with st.expander(t('ui.scenario_tradeoff_analysis.3d6692708ba7')):
        _display_dataframe(result.evidence_refs, hide_index=True, use_container_width=True)
    exports = comparison_csv_exports(result)
    for name, label in [('metrics', 'Download Comparison CSV'), ('cohort_membership', 'Download Comparison Cohort'),
                        ('evidence_refs', 'Download Comparison Evidence References'), ('context', 'Download Comparison Context')]:
        st.download_button(localize(label), exports[name], file_name=f"{result.context['Comparison_ID']}_{name}.csv",
                           mime="text/csv", key=f"wp2_download_{name}")
    st.markdown(t('ui.scenario_tradeoff_analysis.323f3bd1ba18'))
    product = st.selectbox(t('ui.scenario_tradeoff_analysis.438a10baeecb'), sorted(scope.product_ids), index=None,
                           key="wp2_product")
    for side, scenario in [('Reference', reference), ('Candidate', candidate)]:
        st.button(t('ui.scenario_tradeoff_analysis.825974e2ff04' , p0=t('side.' + side.lower())), key=f"wp2_investigate_{side.lower()}", disabled=product is None,
                  on_click=_comparison_investigation_entry, args=(manifest['Run_ID'], scenario, product))
    st.caption(t('ui.scenario_tradeoff_analysis.f6b6bb772951'))


def _sequential_views() -> None:
    """Expose the upgraded prepared outputs without another dashboard redesign."""
    st.caption(t('ui.sequential_views.0844b57f1d86'))
    st.caption(t("workflow.prepare"))
    st.caption(t("workflow.analyze"))
    st.caption(t("workflow.views"))
    input_method = st.radio(t('ui.sequential_views.523611cca3e9'), ["Upload CSV data", "Use existing JSON configuration"], horizontal=True, key='ui_planning_input_method', format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
    if input_method == "Upload CSV data":
        _restore_user_upload_state()
        _user_csv_upload_workflow()
    else:
        config_text = st.sidebar.text_input(t('ui.sequential_views.8ac82fd8e33c'), value="examples/planning/synthetic_demo/config.json", key='ui_sequential_config_path')
        if st.sidebar.button(t('ui.sequential_views.674b67e4a20b'), type="primary", key='ui_sequential_views_button_10'):
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
                st.sidebar.success(t('ui.sequential_views.c4663e34ece9'))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                st.sidebar.error(diagnostic(str(exc)))
                if hasattr(exc, "report"):
                    _render_readiness_report(exc.report)
    st.sidebar.caption(t("workflow.path"))
    selected_path = st.sidebar.text_input(t('ui.sequential_views.e1694cb96dd8'), value=st.session_state.get("sequential_run_dir", ""), key='ui_published_run_path')
    if not selected_path:
        st.info(t('ui.sequential_views.65e8612e1a67'))
        return
    try:
        run_dir = Path(selected_path)
        run_dir = run_dir if run_dir.is_absolute() else REPOSITORY_ROOT / run_dir
        outputs = load_sequential_outputs(run_dir, include_evidence=True)
        manifest = json.loads((run_dir / "run_manifest.json").read_text())
    except (OSError, ValueError, KeyError) as exc:
        st.warning(diagnostic(str(exc)))
        return
    st.caption(t('ui.sequential_views.8a560f0492ce' , p0=manifest['Run_ID'], p1=manifest.get('Data_Mode', 'reference input'), p2=manifest['Configuration']['assumption_version'], p3=manifest['Configuration']['planning_interpretation']))
    handoff = st.session_state.get("ui_handoff")
    if handoff and handoff[0] == manifest["Run_ID"]:
        st.info(t("workflow.handoff", scenario=handoff[1], product=handoff[2]))
    st.markdown(t('ui.sequential_views.1658927c5cc2'))
    downloads = st.columns(3)
    for column, filename, label, mime in [
        (downloads[0], "performance_result.csv", "Download KPI results", "text/csv"),
        (downloads[1], "allocation_result.csv", "Download allocation detail", "text/csv"),
        (downloads[2], "run_manifest.json", "Download run manifest", "application/json"),
    ]:
        column.download_button(localize(label), (run_dir / filename).read_bytes(), file_name=filename, mime=mime, key=f'ui_published_download_{filename}')
    with st.expander(t('ui.sequential_views.c4f973bed87a')):
        st.json({"Configuration": manifest["Configuration"], "Scope": manifest.get("Scope", {}), "Input_Validation": manifest.get("Input_Validation", {}), "Limitations": manifest["Limitations"]})
    performance = outputs["performance"]
    summary = scenario_kpis(performance)
    scenario = st.selectbox(t('ui.sequential_views.0f624371985d'), summary.Scenario.tolist(), key="sequential_scenario")
    st.caption(t("workflow.global", scenario=scenario))
    row = summary[summary.Scenario.eq(scenario)].iloc[0]
    cards = st.columns(5)
    for card, column in zip(cards, ["Production_Coverage_Rate", "Demand_Fulfillment_Rate", "Capacity_Utilization", "Ending_Backlog", "Lost_Sales_Qty"]):
        value = row[column]
        card.metric(display_label(column, current_locale()), "N/A" if pd.isna(value) else (f"{value:.1%}" if column.endswith("Rate") or column == "Capacity_Utilization" else f"{value:,.2f}"))
    st.caption(t('ui.sequential_views.1414d57755db'))
    overview, comparison, detail, risk, tradeoff = st.tabs(
        [t('nav.scenario_overview'), t('nav.scenario_comparison'), t('nav.capacity_allocation_detail'), t('nav.planning_risk_summary'), t('nav.scenario_trade_off_analysis')]
    )
    with overview:
        weekly = performance[performance.Aggregation_Level.eq("Scenario × Week") & performance.Scenario.eq(scenario)]
        _display_line_chart(weekly.set_index("Order_Date")[["Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]])
        _display_dataframe(outputs["pools"][outputs["pools"].Scenario.eq(scenario)], hide_index=True, use_container_width=True)
    with comparison:
        _display_dataframe(summary, hide_index=True, use_container_width=True)
    with detail:
        frame = outputs["allocation"][outputs["allocation"].Scenario.eq(scenario)]
        columns = ["Order_Date", "Plant_ID", "Product Card Id", "Planning_Priority", "Allocation_Order",
                   "Scenario_Qualified_Demand", "Beginning_Inventory", "Beginning_Backlog", "External_Receipts_Qty",
                   "Required_Production_Qty", "Internal_Production_Qty", "Workload_Factor", "Allocated_Workload",
                   "Fulfilled_Backlog_Qty", "Fulfilled_Current_Qty", "Ending_Inventory", "Ending_Backlog", "Lost_Sales_Qty"]
        _display_dataframe(frame[columns].sort_values(["Order_Date", "Plant_ID", "Allocation_Order"]), hide_index=True, use_container_width=True)
    with risk:
        _planning_risk_summary(outputs, scenario, manifest)
    with tradeoff:
        _scenario_tradeoff_analysis(run_dir, manifest)



def _plotly_bar(frame, **kwargs):
    view = frame.copy(deep=True)
    kwargs["title"] = localize(kwargs.get("title", ""))
    kwargs["labels"] = {str(c): display_label(str(c), current_locale()) for c in view.columns}
    if current_locale() == "zh-TW":
        if "KPI" in view:
            view["KPI"] = view["KPI"].map(lambda value: display_label(str(value), current_locale()))
        if "Performance_Status" in view:
            view["Performance_Status"] = view["Performance_Status"].map(localize)
    return px.bar(view, **kwargs)

def _display_dataframe(frame, **kwargs):
    """Label columns using Streamlit display configuration, not renamed data."""
    if hasattr(frame, "columns"):
        kwargs.setdefault("column_config", {
            str(column): st.column_config.Column(
                localize(display_label(str(column), current_locale())),
                help=help_text(str(column), current_locale()) + " · " + str(column))
            for column in frame.columns
        })
    return st.dataframe(frame, **kwargs)


def _chart_copy(frame):
    view = frame.copy(deep=True)
    if current_locale() == "zh-TW":
        view = (view.rename(columns={c: display_label(str(c), current_locale()) for c in view.columns})
                if hasattr(view, "columns") else view.rename(display_label(str(view.name), current_locale())))
        if view.index.name:
            view.index.name = display_label(str(view.index.name), current_locale())
    return view


def _display_line_chart(frame, **kwargs):
    return st.line_chart(_chart_copy(frame), **kwargs)


def _display_bar_chart(frame, **kwargs):
    return st.bar_chart(_chart_copy(frame), **kwargs)


def _apply_locale(request_key):
    """Only a locale change: capture submitted form values, never plan/validate."""
    _capture_user_upload_state()
    prefixes = ("upload_", "map_", "provenance_", "eligibility_", "wp2_",
                "investigation_", "risk_", "detail_", "ui_", "sequential_")
    snapshot = {key: value for key, value in st.session_state.items()
                if key.startswith(prefixes) and not key.startswith("upload_widget_")
                and key not in {"ui_locale", "ui_locale_restore", "ui_language_request", "upload_language_request", request_key}
                and "_button_" not in key
                and "_download_" not in key
                and not key.startswith("wp2_investigate_")}
    st.session_state["ui_locale_restore"] = snapshot
    requested = st.session_state.get(request_key, "en")
    st.session_state["ui_locale"] = requested if requested in ("en", "zh-TW") else "en"
    st.session_state["ui_language_request"] = st.session_state["ui_locale"]
    st.session_state["upload_language_request"] = st.session_state["ui_locale"]
    st.session_state.setdefault(_USER_UPLOAD_WIDGET_STATE_KEY, {})["upload_language_request"] = st.session_state["ui_locale"]


def _restore_locale_state():
    for key, value in st.session_state.pop("ui_locale_restore", {}).items():
        st.session_state[key] = value


def _language_form():
    st.caption(t("locale.form_help"))
    if "upload_language_request" not in st.session_state:
        st.session_state["upload_language_request"] = current_locale()
    st.selectbox(t("locale.label"), ["en", "zh-TW"], key="upload_language_request",
                 format_func=lambda value: "English" if value == "en" else "繁體中文")
    st.form_submit_button(t("locale.apply"), on_click=_apply_locale,
                          args=("upload_language_request",))


def _language_sidebar(model):
    # A sidebar rerun cannot safely flush unsubmitted browser form buffers.
    # In CSV mode the selector is inside the existing form instead.
    if model == "Sequential workload" and st.session_state.get(
            "ui_planning_input_method", "Upload CSV data") == "Upload CSV data":
        st.sidebar.caption(t("locale.sidebar_help"))
    else:
        st.session_state.setdefault("ui_language_request", current_locale())
        st.sidebar.selectbox(t("locale.label"), ["en", "zh-TW"], key="ui_language_request",
                             format_func=lambda value: "English" if value == "en" else "繁體中文",
                             on_change=_apply_locale, args=("ui_language_request",))
    st.caption(t("display.raw"))
    with st.expander(t("display.technical")):
        _display_dataframe(pd.DataFrame([
            {"Metric_ID": key, "Label": display_label(key, current_locale()),
             "Definition": help_text(key, current_locale())} for key in METRICS
        ]), hide_index=True)
        for code, values in STATUS.items():
            st.caption(code + " · " + values[3 if current_locale() == "zh-TW" else 2])
        for code, values in COHORTS.items():
            st.caption(code + " · " + values[1 if current_locale() == "zh-TW" else 0])

def main() -> None:
    st.set_page_config(page_title="Scenario Planning Decision Support", layout="wide")
    _restore_locale_state()
    _capture_user_upload_state()
    st.title(t('ui.main.cd9e13535d7b'))
    st.info(t('ui.main.acf52dd61a47'))
    workspace = st.sidebar.radio('Workspace / 工作區', ['Planning', 'Decision Copilot'],
                                 key='ui_workspace', horizontal=True)
    if workspace == 'Decision Copilot':
        render_copilot_locale_selector(_apply_locale)
        render_copilot()
        return
    model = st.sidebar.selectbox(t('ui.main.914d526ec39a'), ["Sequential workload", "Legacy independent weeks"], key='ui_planning_model', format_func=lambda value, locale=current_locale(): localize(value, locale=locale))
    _language_sidebar(model)
    if model == "Sequential workload":
        _sequential_views()
        return
    _run_controls()
    output_dir = Path(st.session_state.get("scenario_output_dir", _default_output_dir()))
    try:
        outputs = load_dashboard_outputs(output_dir)
    except (FileNotFoundError, ValueError) as exc:
        st.warning(t('ui.main.f3794f1bb357' , p0=exc))
        return
    performance = outputs["performance"]
    scenario = scenario_kpis(performance)
    tabs = st.tabs([t('nav.scenario_overview'), t('nav.scenario_comparison'), t('nav.capacity_allocation_detail')])
    with tabs[0]:
        _overview(performance, scenario)
    with tabs[1]:
        _comparison(performance)
    with tabs[2]:
        _allocation_detail(outputs["allocation"])


if __name__ == "__main__":
    main()
