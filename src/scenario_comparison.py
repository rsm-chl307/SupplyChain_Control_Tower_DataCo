"""Pure, same-run comparison contracts for published sequential planning results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.planning_inputs import require_frame, weekly_dates

SCHEMA = "sequential_v1"
ARTIFACT_TABLES = {
    "allocation_result": "allocation", "capacity_pools": "pools",
    "performance_result": "performance", "scenario_snapshot": "scenario",
    **{name: name for name in ("eligibility_ledger", "weekly_demand", "demand_coverage",
                              "initial_state", "external_receipts", "workload_factors",
                              "capacity_baseline", "validation_result")},
}
KEYS = {
    "allocation": ["Scenario", "Plant_ID", "Product Card Id", "Order_Date"],
    "scenario": ["Scenario", "Plant_ID", "Product Card Id", "Order_Date"],
    "pools": ["Scenario", "Plant_ID", "Order_Date"],
    "performance": ["Aggregation_Level", "Scenario", "Plant_ID", "Order_Date"],
    "initial_state": ["Plant_ID", "Product Card Id"],
    "weekly_demand": ["Plant_ID", "Product Card Id", "Order_Date"],
    "demand_coverage": ["Plant_ID", "Product Card Id", "Order_Date"],
    "workload_factors": ["Product Card Id"],
    "capacity_baseline": ["Plant_ID"],
}


@dataclass(frozen=True)
class ComparisonInput:
    """One explicit scenario and validated published tables; never selects a default."""
    manifest: dict[str, Any]
    tables: dict[str, pd.DataFrame]
    scenario: str

    @property
    def run_id(self) -> str:
        return self.manifest["Run_ID"]


@dataclass(frozen=True)
class ComparisonScope:
    """Explicit product universe, plant scope and complete Sunday-ending horizon."""
    product_ids: tuple[str, ...]
    plant_ids: tuple[str, ...]
    start_week: str
    end_week: str
    selected_priorities: tuple[int, ...] = ()
    cohort_basis: str = "FIXED_REFERENCE_PRIORITY"
    metric_ids: tuple[str, ...] = ()
    output_grain: str = "Scenario"


@dataclass
class ComparisonResult:
    """Reusable result for presentation, export and future read-only consumers."""
    context: dict[str, Any]
    cohort_membership: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    evidence_refs: pd.DataFrame = field(default_factory=pd.DataFrame)


def validate_comparison_input(value: ComparisonInput) -> None:
    """Check manifest/table identity and native keys without IO or mutation.

    Missing metric values/coverage are handled per metric by the comparison;
    invalid publication identities and ambiguous business keys reject the input.
    """
    m = value.manifest
    for key, expected in (("Schema_Version", SCHEMA), ("Execution_Status", "SUCCEEDED"),
                          ("Validation_Status", "PASSED"), ("Publication_Status", "PUBLISHED")):
        if m.get(key) != expected:
            raise ValueError(f"Invalid published manifest: {key}")
    if not isinstance(m.get("Run_ID"), str) or not m["Run_ID"].strip():
        raise ValueError("Invalid Run_ID")
    if m.get("Data_Mode") not in {"USER_DATA", "SYNTHETIC_DEMO"}:
        raise ValueError("Unsupported Data_Mode")
    if not value.scenario or not isinstance(value.scenario, str):
        raise ValueError("Explicit scenario selection required")
    for artifact, name in ARTIFACT_TABLES.items():
        if artifact not in m.get("Artifacts", {}) or name not in value.tables:
            raise ValueError(f"Missing published artifact: {artifact}")
        f = value.tables[name]
        if not {"Run_ID", "Schema_Version"}.issubset(f):
            raise ValueError(f"Missing run identity: {artifact}")
        if not f.Run_ID.eq(value.run_id).all() or not f.Schema_Version.eq(SCHEMA).all():
            raise ValueError(f"Invalid Run/schema identity: {artifact}")
        if name in KEYS:
            key = list(KEYS[name])
            if name == "capacity_baseline" and "Order_Date" in f:
                key.append("Order_Date")
            if name == "performance":
                if not set(key).issubset(f) or f.duplicated(key).any():
                    raise ValueError("Invalid or duplicate performance grain key")
                grains = {"Scenario": [], "Scenario × Plant": ["Plant_ID"],
                          "Scenario × Week": ["Order_Date"],
                          "Scenario × Plant × Week": ["Plant_ID", "Order_Date"]}
                if not f.Aggregation_Level.isin(grains).all():
                    raise ValueError("Unsupported performance grain")
                for level, dimensions in grains.items():
                    rows = f.loc[f.Aggregation_Level.eq(level)]
                    require_frame(rows, ["Scenario"] + dimensions,
                                  ["Scenario"] + dimensions, level)
                    if "Order_Date" in dimensions:
                        weekly_dates(rows)
            else:
                require_frame(f, key, key, artifact)
        if "Order_Date" in f and name != "performance":
            weekly_dates(f)
        for identifier in ("Product Card Id", "Plant_ID", "Run_ID", "Scenario"):
            if identifier in f:
                rows = f
                if name == "performance" and identifier == "Plant_ID":
                    rows = f.loc[f.Aggregation_Level.str.contains("Plant")]
                nonnull = rows[identifier].dropna()
                if not nonnull.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
                    raise ValueError(f"String identifiers required: {artifact}.{identifier}")
    for name in ("allocation", "pools", "scenario", "performance"):
        if value.scenario not in set(value.tables[name].Scenario):
            raise ValueError(f"Scenario {value.scenario!r} absent from {name}")

# Metric identifiers are deliberately separate from display labels.
KPI_METRICS = {
    "Horizon_Service_Level": "Demand_Fulfillment_Rate",
    "Weekly_Service_Level": "Demand_Fulfillment_Rate",
    "Fulfilled_Quantity": "Demand_Fulfillment_Numerator",
    "Terminal_Backlog": "Ending_Backlog",
    "Terminal_Opening_Backlog": "Ending_Opening_Backlog",
    "Terminal_Horizon_Backlog": "Ending_Horizon_Backlog",
    "Lost_Sales": "Lost_Sales_Qty",
}
FLOW_METRICS = {"Allocated_Workload": "Allocated_Workload", "Unmet_Workload": "Unmet_Workload",
                "Current_Unfulfilled_Quantity": "Current_Unfulfilled_Qty"}
DEFAULT_METRICS = tuple(KPI_METRICS) + tuple(FLOW_METRICS)
GRAINS = ("Scenario", "Scenario × Plant", "Scenario × Week", "Scenario × Plant × Week")
HORIZON_METRICS = {"Horizon_Service_Level", "Fulfilled_Quantity", "Terminal_Backlog",
                   "Terminal_Opening_Backlog", "Terminal_Horizon_Backlog"}


def _selected(value: ComparisonInput, name: str, scope: ComparisonScope) -> pd.DataFrame:
    """Return a native-grain copy; evidence detail is never joined to measures."""
    f = value.tables[name]
    mask = pd.Series(True, index=f.index)
    for column, allowed in (("Scenario", (value.scenario,)), ("Plant_ID", scope.plant_ids),
                            ("Product Card Id", scope.product_ids)):
        if column in f:
            mask &= f[column].isin(allowed)
    result = f.loc[mask].copy(deep=True)
    # Fix summation order as well as output order, including floating-point tails.
    key = [column for column in KEYS.get(name, []) if column in result]
    if key:
        result = result.sort_values(key, kind="mergesort", na_position="first")
    return result.reset_index(drop=True)


def _coverage_reason(value: ComparisonInput, scope: ComparisonScope) -> str:
    """Validate against declared opening items and full horizon, never an intersection."""
    from src.planning_inputs import horizon
    weeks = set(horizon(scope.start_week, scope.end_week))
    bounds = value.manifest.get("Scope", {}).get("Planning_Horizon", [])
    if len(bounds) != 2 or list(pd.to_datetime(bounds)) != [min(weeks), max(weeks)]:
        return "Scope must use the complete published planning horizon"
    initial = _selected(value, "initial_state", scope)
    items = set(initial[["Plant_ID", "Product Card Id"]].itertuples(index=False, name=None))
    if {p for _, p in items} != set(scope.product_ids):
        return "Product Universe is incomplete in declared initial state / plant scope"
    expected = {(plant, product, week) for plant, product in items for week in weeks}
    key = ["Plant_ID", "Product Card Id", "Order_Date"]
    for name in ("allocation", "scenario", "demand_coverage"):
        frame = _selected(value, name, scope)
        if name == "demand_coverage":
            # Published coverage also retains historical OUT_OF_SCOPE evidence.
            frame = frame.loc[pd.to_datetime(frame.Order_Date).isin(weeks)]
        actual = set(weekly_dates(frame)[key].itertuples(index=False, name=None))
        if actual != expected:
            return f"{name}: missing/extra product, plant or week coverage (including horizon endpoint)"
        if "Coverage_Status" not in frame or not frame.Coverage_Status.isin(["OBSERVED_DEMAND", "OBSERVED_ZERO"]).all():
            return f"{name}: missing or UNKNOWN demand coverage"
    pools = _selected(value, "pools", scope)
    expected_pools = {(p, w) for p in scope.plant_ids for w in weeks}
    actual_pools = set(weekly_dates(pools)[["Plant_ID", "Order_Date"]].itertuples(index=False, name=None))
    if actual_pools != expected_pools:
        return "capacity_pools: missing/extra plant-week coverage"
    return ""


def _priority(value: ComparisonInput, scope: ComparisonScope, product: str) -> tuple[Any, str]:
    rows = _selected(value, "allocation", scope)
    rows = rows.loc[rows["Product Card Id"].eq(product)]
    if "Planning_Priority" not in rows or rows.empty:
        return None, "Missing Planning_Priority"
    vals = rows.Planning_Priority
    if (not pd.api.types.is_numeric_dtype(vals) or pd.api.types.is_bool_dtype(vals)
            or vals.isna().any() or not vals.isin([1, 2, 3]).all() or vals.nunique() != 1):
        return None, "Missing, invalid or inconsistent Planning_Priority"
    return int(vals.iloc[0]), ""


def _membership(reference: ComparisonInput, candidate: ComparisonInput,
                scope: ComparisonScope) -> pd.DataFrame:
    rows = []
    for product in sorted(scope.product_ids):
        a, ar = _priority(reference, scope, product)
        b, br = _priority(candidate, scope, product)
        rows.append({"Product Card Id": product, "Reference Priority": a, "Candidate Priority": b,
                     "Cohort Membership": ("UNAVAILABLE" if ar or br else
                                           "SELECTED" if a in scope.selected_priorities else "COMPLEMENT"),
                     "Priority Changed": pd.NA if ar or br else a != b,
                     "Reason": "; ".join(x for x in [ar, br] if x)})
    return pd.DataFrame(rows)


def _unit(value: ComparisonInput, scope: ComparisonScope, products: tuple[str, ...],
          workload: bool) -> tuple[str, str]:
    frame = _selected(value, "allocation", scope)
    frame = frame.loc[frame["Product Card Id"].isin(products)]
    column = "Workload_Unit" if workload else "Quantity_Unit"
    if column not in frame:
        fallback = value.manifest.get("Scope", {}).get(column)
        if not workload and isinstance(fallback, str) and fallback.strip():
            return fallback, ""
        return "Unavailable", f"Missing {column}"
    vals = frame[column]
    if vals.isna().any() or vals.astype(str).str.strip().eq("").any() or vals.nunique() != 1:
        return "Unavailable", f"Mixed or missing {column}"
    return str(vals.iloc[0]), ""


def _metric_values(value: ComparisonInput, scope: ComparisonScope, products: tuple[str, ...],
                   metric: str, grain: str, plant: str | None, week: Any,
                   prepared: tuple[pd.DataFrame | None, str]) -> tuple[float, float, float, str]:
    """Use the existing sequential KPI engine; only workload/miss flows sum directly."""
    import numpy as np
    from src.planning_inputs import numeric

    rows = _selected(value, "allocation", scope)
    rows = rows.loc[rows["Product Card Id"].isin(products)]
    if not products or rows.empty:
        return np.nan, np.nan, np.nan, "Empty cohort / unavailable rows"
    if metric in FLOW_METRICS:
        if plant is not None:
            rows = rows.loc[rows.Plant_ID.eq(plant)]
        if week is not None:
            rows = rows.loc[pd.to_datetime(rows.Order_Date).eq(week)]
        column = FLOW_METRICS[metric]
        if column not in rows:
            return np.nan, np.nan, np.nan, f"Missing {column}"
        try:
            numeric(rows, [column])
        except ValueError as exc:
            return np.nan, np.nan, np.nan, str(exc)
        if rows.empty:
            return np.nan, np.nan, np.nan, "Empty cohort in plant scope"
        return float(rows[column].sum()), np.nan, np.nan, ""
    if metric in HORIZON_METRICS and "Week" in grain:
        return np.nan, np.nan, np.nan, "Metric requires full horizon grain"
    try:
        kpis, error = prepared
        if kpis is None:
            return np.nan, np.nan, np.nan, error
        selected = kpis.loc[kpis.Aggregation_Level.eq(grain)]
        if plant is not None:
            selected = selected.loc[selected.Plant_ID.eq(plant)]
        if week is not None:
            selected = selected.loc[selected.Order_Date.eq(week)]
        if len(selected) != 1:
            return np.nan, np.nan, np.nan, "Metric grain unavailable or ambiguous"
        row = selected.iloc[0]
        result = float(row[KPI_METRICS[metric]])
        if metric.endswith("Service_Level"):
            numerator, denominator = float(row.Demand_Fulfillment_Numerator), float(row.Demand_Fulfillment_Denominator)
            reason = "Zero denominator; rate is N/A" if denominator == 0 else ""
            return result, numerator, denominator, reason
        return result, np.nan, np.nan, ""
    except (ValueError, KeyError, TypeError) as exc:
        return np.nan, np.nan, np.nan, f"KPI inputs unavailable: {exc}"


def _policy(value: ComparisonInput, scope: ComparisonScope) -> tuple[str, str]:
    rows = _selected(value, "allocation", scope)
    if "Backlog_Policy" not in rows or rows.empty or rows.Backlog_Policy.isna().any():
        return "Unavailable", "Missing Backlog_Policy"
    policies = set(rows.Backlog_Policy)
    if len(policies) != 1 or not policies.issubset({"CARRY_FORWARD", "LOST_SALES"}):
        return "Unavailable", "Invalid or inconsistent Backlog_Policy"
    return str(rows.Backlog_Policy.iloc[0]), ""


def _signatures(frame: pd.DataFrame, key: list[str], columns: list[str]) -> str:
    """Canonical values for difference checks, independent of original row order."""
    if not set(columns + key).issubset(frame):
        return "MISSING:" + ",".join(sorted(set(columns + key) - set(frame)))
    f = frame[key + columns].copy().sort_values(key, kind="mergesort")
    return f.to_json(orient="records", date_format="iso", double_precision=15)


def _input_differences(reference: ComparisonInput, candidate: ComparisonInput,
                       scope: ComparisonScope) -> list[str]:
    """Disclose changed conditioning inputs; scenario demand/capacity are comparison axes."""
    a, b = [_selected(v, "allocation", scope) for v in (reference, candidate)]
    key = ["Plant_ID", "Product Card Id", "Order_Date"]
    findings = []
    checks = {
        "Receipts": ["External_Receipts_Qty"],
        "Priority": ["Planning_Priority"],
        "Eligibility": ["Gross_Demand", "Qualified_Demand", "Excluded_Demand", "Eligibility_Version", "Coverage_Basis"],
        "Allocation policy / quantity step": ["Allocation_Policy", "Quantity_Step"],
        "Workload definition": ["Workload_Factor", "Factor_Version", "Workload_Unit"],
    }
    for label, columns in checks.items():
        signatures = [_signatures(f, key, columns) for f in (a, b)]
        if any(s.startswith("MISSING:") for s in signatures):
            findings.append(f"{label} inputs unavailable")
        elif signatures[0] != signatures[1]:
            findings.append(f"{label} changed")
    openings = [f.loc[pd.to_datetime(f.Order_Date).eq(pd.Timestamp(scope.start_week))] for f in (a, b)]
    signatures = [_signatures(f, key, ["Beginning_Inventory", "Beginning_Backlog", "Beginning_Opening_Backlog"])
                  for f in openings]
    if any(s.startswith("MISSING:") for s in signatures):
        findings.append("Opening state inputs unavailable")
    elif signatures[0] != signatures[1]:
        findings.append("Opening state changed")
    columns = ["Baseline_Workload_Capacity", "Capacity_Version", "Factor_Version", "Workload_Unit"]
    signatures = [_signatures(_selected(v, "pools", scope), ["Plant_ID", "Order_Date"], columns)
                  for v in (reference, candidate)]
    if any(s.startswith("MISSING:") for s in signatures):
        findings.append("Capacity basis inputs unavailable")
    elif signatures[0] != signatures[1]:
        findings.append("Capacity basis changed")
    return sorted(findings)


def _workload_reason(reference: ComparisonInput, candidate: ComparisonInput, scope: ComparisonScope) -> str:
    """Reject incompatible factor/calibration definitions without blocking quantity metrics."""
    import numpy as np
    signatures = []
    for value in (reference, candidate):
        f = _selected(value, "allocation", scope)
        columns = ["Workload_Factor", "Factor_Version", "Workload_Unit"]
        if not set(columns).issubset(f):
            return "Missing workload factor / calibration definition"
        if f[columns].isna().any().any():
            return "Missing workload factor / calibration definition"
        factors = pd.to_numeric(f.Workload_Factor, errors="coerce")
        if not np.isfinite(factors).all() or factors.le(0).any():
            return "Invalid workload factors"
        for column in columns:
            if f.groupby('Product Card Id')[column].nunique().gt(1).any():
                return "Inconsistent workload definitions within product trajectory"
        pools = _selected(value, "pools", scope)
        if not {"Workload_Unit", "Factor_Version"}.issubset(pools):
            return "Missing capacity calibration definition"
        for column in ("Workload_Unit", "Factor_Version"):
            if pools[column].isna().any() or set(pools[column]) != set(f[column]):
                return "Workload factors and capacity calibration are incompatible"
        signatures.append(_signatures(f, ["Plant_ID", "Product Card Id", "Order_Date"], columns))
    if signatures[0] != signatures[1]:
        return "Incompatible workload factor / calibration definitions between scenarios"
    return ""


def _evidence(reference: ComparisonInput, candidate: ComparisonInput,
              context: dict[str, Any]) -> pd.DataFrame:
    """Describe native evidence, retaining both identities without any detail joins."""
    import json
    grains = {
        "allocation_result": "Scenario × Plant × Product × Week",
        "scenario_snapshot": "Scenario × Plant × Product × Week",
        "capacity_pools": "Scenario × Plant × Week",
        "performance_result": "Aggregation_Level (four independent grains)",
        "initial_state": "Plant × Product (horizon opening)",
        "eligibility_ledger": "Source record / order line",
        "external_receipts": "Receipt_ID (optionally Scenario)",
        "weekly_demand": "Plant × Product × Week",
        "demand_coverage": "Plant × Product × Week",
        "workload_factors": "Product",
        "capacity_baseline": "Plant (optionally Week)",
        "validation_result": "Run validation check",
    }
    rows = []
    for side, value in (("REFERENCE", reference), ("CANDIDATE", candidate)):
        provenance = {"Data_Mode": value.manifest['Data_Mode'],
                      "Sources": value.manifest.get('Input_Validation', {}).get('Sources', []),
                      "Assumptions": value.manifest.get('Input_Validation', {}).get('Assumptions', []),
                      "Source_Hashes": value.manifest.get('Source_Hashes', {})}
        for name in sorted(ARTIFACT_TABLES):
            artifact = value.manifest['Artifacts'][name]
            rows.append({"Comparison_ID": context['Comparison_ID'], "Side": side,
                         "Run_ID": value.run_id, "Scenario": value.scenario,
                         "Artifact_Name": name, "Artifact_Path": artifact['Path'],
                         "Artifact_SHA256": artifact['SHA256'], "Native_Grain": grains[name],
                         "Key_Filter": json.dumps({"Run_ID": value.run_id, "Scenario_Context": value.scenario,
                                                    "Scope": context['Scope'],
                                                    "Scenario_Independent": 'Scenario' not in value.tables[ARTIFACT_TABLES[name]]},
                                                   sort_keys=True),
                         "Provenance": json.dumps(provenance, sort_keys=True),
                         "Metric_Definition_Reference": "docs/wp2_scenario_tradeoff_analysis_specification.md#6-kpi-and-metric-definitions; src/kpi_engine.py:calculate_sequential_kpis"})
    return pd.DataFrame(rows)


def compare_published_results(reference: ComparisonInput, candidate: ComparisonInput,
                              scope: ComparisonScope) -> ComparisonResult:
    """Compare two explicit published scenarios without IO, simulation or mutation."""
    import hashlib
    import json
    from dataclasses import asdict
    import numpy as np
    from src.planning_inputs import horizon

    for value in (reference, candidate):
        validate_comparison_input(value)
    if reference.run_id != candidate.run_id or reference.manifest != candidate.manifest:
        raise ValueError("Reference and Candidate must belong to the same published Run")
    if reference.scenario == candidate.scenario:
        raise ValueError("Select two different explicit scenarios")
    if scope.cohort_basis != "FIXED_REFERENCE_PRIORITY" or scope.output_grain not in GRAINS:
        raise ValueError("Unsupported cohort basis or output grain")
    for ids, label in ((scope.product_ids, "Product Universe"), (scope.plant_ids, "Plant Scope")):
        if not ids or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i.strip() for i in ids):
            raise ValueError(f"Explicit unique string {label} required")
    if any(type(p) is not int or p not in [1, 2, 3] for p in scope.selected_priorities):
        raise ValueError("Selected priorities must be integers 1, 2 or 3")
    requested = tuple(scope.metric_ids or DEFAULT_METRICS)
    if set(requested) - set(DEFAULT_METRICS) or len(set(requested)) != len(requested):
        raise ValueError("Unknown or duplicate metric IDs")
    weeks = horizon(scope.start_week, scope.end_week)
    normalized_scope = asdict(scope)
    for name in ("product_ids", "plant_ids", "selected_priorities"):
        normalized_scope[name] = sorted(set(normalized_scope[name]))
    normalized_scope["metric_ids"] = sorted(requested)
    context = {"Comparison_Schema_Version": "comparison_v1", "Reference_Run_ID": reference.run_id,
               "Candidate_Run_ID": candidate.run_id, "Reference_Scenario": reference.scenario,
               "Candidate_Scenario": candidate.scenario, "Schema_Version": SCHEMA,
               "Data_Mode": reference.manifest["Data_Mode"], "Scope": normalized_scope}
    digest = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:20]
    context["Comparison_ID"] = "comparison_" + digest
    context["Manifest_SHA256"] = hashlib.sha256(json.dumps(reference.manifest, sort_keys=True).encode()).hexdigest()
    pool_context = []
    for side, value in (("REFERENCE", reference), ("CANDIDATE", candidate)):
        pools = _selected(value, "pools", scope).sort_values(["Plant_ID", "Order_Date"])
        for _, row in pools.iterrows():
            pool_context.append({"Side": side, "Run_ID": value.run_id, "Scenario": value.scenario,
                                 "Plant_ID": row.Plant_ID, "Order_Date": pd.Timestamp(row.Order_Date).date().isoformat(),
                                 **{column: row.get(column) for column in
                                    ("Workload_Unit", "Available_Workload_Capacity", "Allocated_Workload",
                                     "Remaining_Workload_Capacity", "Unmet_Workload")}})
    context["Plant_Capacity_Pool_Context"] = pool_context
    policies = [_policy(v, scope) for v in (reference, candidate)]
    context['Reference_Backlog_Policy'], context['Candidate_Backlog_Policy'] = [p[0] for p in policies]
    contrast = not any(p[1] for p in policies) and policies[0][0] != policies[1][0]
    context['Policy_Comparison'] = ('POLICY_CONTRAST' if contrast else
                                    'UNAVAILABLE' if any(p[1] for p in policies) else 'SAME_POLICY')
    differences = _input_differences(reference, candidate, scope)
    context['Input_Differences'] = differences
    workload_reason = _workload_reason(reference, candidate, scope)
    members = _membership(reference, candidate, scope)
    coverage = [_coverage_reason(v, scope) for v in (reference, candidate)]
    membership_issue = members.Reason.ne("").any()
    records = []
    for group in ("ALL", "SELECTED", "COMPLEMENT"):
        products = tuple(scope.product_ids) if group == "ALL" else tuple(
            members.loc[members['Cohort Membership'].eq(group), 'Product Card Id'])
        prepared = []
        from src.kpi_engine import calculate_sequential_kpis
        for v in (reference, candidate):
            rows = _selected(v, "allocation", scope)
            rows = rows.loc[rows['Product Card Id'].isin(products)]
            try:
                prepared.append((calculate_sequential_kpis(rows, _selected(v, "pools", scope)), ""))
            except (ValueError, KeyError, TypeError) as exc:
                prepared.append((None, f"KPI inputs unavailable: {exc}"))
        for metric in sorted(requested):
            grain = scope.output_grain
            if metric == "Weekly_Service_Level" and "Week" not in grain:
                grain += " × Week"
            plants = sorted(scope.plant_ids) if "Plant" in grain else [None]
            dates = weeks if "Week" in grain else [None]
            workload = metric in {"Allocated_Workload", "Unmet_Workload"}
            units = [_unit(v, scope, products, workload) if products else ("Unavailable", "Empty cohort")
                     for v in (reference, candidate)]
            for plant in plants:
                for week in dates:
                    values = [_metric_values(v, scope, products, metric, grain, plant, week, prepared[i])
                              if not coverage[i] else (np.nan, np.nan, np.nan, coverage[i])
                              for i, v in enumerate((reference, candidate))]
                    reasons = [r for r in coverage if r]
                    reasons += [u[1] for u in units if u[1]]
                    reasons += [v[3] for v in values if v[3]]
                    reasons += [p[1] for p in policies if p[1]]
                    if workload and workload_reason:
                        reasons.append(workload_reason)
                    if membership_issue:
                        reasons.append("Priority data issue: cohort membership unavailable")
                    if units[0][0] != units[1][0]:
                        reasons.append("Incompatible units between scenarios")
                    blocked = bool(reasons) or not all(np.isfinite(v[0]) for v in values)
                    descriptive = list(differences)
                    if contrast:
                        descriptive.append(f"POLICY_CONTRAST: {policies[0][0]} → {policies[1][0]}; backlog reduction is not service improvement")
                    if descriptive:
                        reasons.extend(descriptive)
                    rate = metric.endswith("Service_Level")
                    records.append({"Comparison_ID": context['Comparison_ID'], "Cohort_ID": group,
                                    "Metric_ID": metric, "Aggregation_Level": grain, "Plant_ID": plant,
                                    "Order_Date": week, "Unit": "ratio" if rate else units[0][0],
                                    "Fulfillment_Basis": "CURRENT_WEEK_COHORT" if metric == "Weekly_Service_Level" else
                                        "HORIZON_ORIGIN_COHORT" if metric in ("Horizon_Service_Level", "Fulfilled_Quantity") else None,
                                    "Reference_Value": values[0][0], "Candidate_Value": values[1][0],
                                    "Reference_Unit": units[0][0], "Candidate_Unit": units[1][0],
                                    "Reference_Numerator": values[0][1], "Reference_Denominator": values[0][2],
                                    "Candidate_Numerator": values[1][1], "Candidate_Denominator": values[1][2],
                                    "Delta": np.nan if blocked else (values[1][0] - values[0][0]) * (100 if rate else 1),
                                    "Delta_Unit": "percentage points" if rate else units[0][0],
                                    "Comparability_Status": "BLOCKED" if blocked else "DESCRIPTIVE_ONLY" if descriptive else "COMPARABLE",
                                    "Reason": "; ".join(sorted(set(reasons)))})
    metrics = pd.DataFrame(records).sort_values(['Cohort_ID', 'Metric_ID', 'Plant_ID', 'Order_Date'],
                                               na_position='first', kind='mergesort').reset_index(drop=True)
    context["Comparability_Summary"] = metrics.Comparability_Status.value_counts().sort_index().to_dict()
    context["Priority_Changed_Product_Count"] = int(members['Priority Changed'].eq(True).sum())
    return ComparisonResult(context, members, metrics, _evidence(reference, candidate, context))
