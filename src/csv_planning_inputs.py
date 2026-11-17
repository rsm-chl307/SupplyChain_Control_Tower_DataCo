"""Small CSV adapters for synthetic/user data, feeding one canonical engine."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import math
from pathlib import Path

import pandas as pd

from src.demand_preparation import build_demand_coverage, prepare_order_demand
from src.planning_inputs import CanonicalPlanningInputs, ITEM_KEY, WEEK_KEY, WORKLOAD_ALLOCATION_POLICY, horizon, numeric, require_frame, weekly_dates
from src.workload_model import calibrate_workload_capacity, validate_workload_factors

DATA_MODES = {"SYNTHETIC_DEMO", "USER_DATA"}
CAPABILITIES = ["Demand_Qualification", "Workload_Planning", "Sequential_Inventory", "Backlog_Planning", "Scenario_Comparison"]


class InputValidationError(ValueError):
    """Blocked intake with a machine-readable capability/assumption report."""

    def __init__(self, message: str, report: dict):
        super().__init__(message)
        self.report = report


def load_csv_planning_inputs(
    config: dict,
    inputs_dir: str | Path,
    *,
    reader: Callable[[Path, str], pd.DataFrame] | None = None,
) -> CanonicalPlanningInputs:
    """Validate CSVs and return source-independent planning facts.

    Column mappings run canonical name -> source column. IDs remain strings.
    No DataCo file, department, ABC table or order-status spelling is required.
    Optional inputs need explicit safe assumptions when their absence matters.
    """
    report = {
        "Status": "VALIDATING", "Data_Mode": config.get("data_mode"),
        "Sources": [], "Assumptions": [], "Derived_Values": [],
        "Unavailable_Capabilities": [], "Errors": [], "Warnings": [],
    }
    directory = Path(inputs_dir)
    files = config.get("files", {})
    assumptions = config.get("assumptions", {})
    version_value = config.get("assumption_version")
    version = version_value.strip() if isinstance(version_value, str) else ""
    mode = config.get("data_mode")
    context = "configuration"

    def fail(message: str, capabilities: list[str] | None = None) -> None:
        report["Status"] = "BLOCKED"
        report["Errors"].append(message)
        report["Unavailable_Capabilities"] = capabilities or CAPABILITIES.copy()
        raise InputValidationError(message, report)

    def assumption(name: str, value: object, reason: str) -> None:
        report["Assumptions"].append({"Name": name, "Value": value, "Reason": reason, "Classification": "SYNTHETIC_ASSUMPTION"})

    def table(name: str, required: list[str], *, optional: bool = False) -> pd.DataFrame | None:
        nonlocal context
        context = name
        entry = files.get(name)
        if entry is None:
            if optional:
                return None
            fail(f"{name}: required CSV is missing")
        if isinstance(entry, str):
            entry = {"path": entry}
        if not isinstance(entry, dict) or not entry.get("path"):
            fail(f"{name}: specify a CSV path")
        path = directory / entry["path"]
        encoding = entry.get("encoding", "utf-8")
        frame = reader(path, encoding) if reader else pd.read_csv(BytesIO(path.read_bytes()), dtype=str, keep_default_na=False, encoding=encoding)
        mapping = entry.get("columns", {})
        if not isinstance(mapping, dict) or len(set(mapping.values())) != len(mapping):
            fail(f"{name}: column mapping must be canonical -> distinct source columns")
        if set(mapping.values()) - set(frame.columns):
            fail(f"{name}: mapped source columns absent: {sorted(set(mapping.values()) - set(frame.columns))}")
        frame = frame.rename(columns={source: canonical for canonical, source in mapping.items()}).copy(deep=True)
        if frame.columns.duplicated().any():
            fail(f"{name}: column mapping creates duplicate canonical columns")
        missing = set(required) - set(frame.columns)
        if missing:
            fail(f"{name}: missing required columns {sorted(missing)}")
        report["Sources"].append({
            "Dataset": name, "Path": str(path.resolve()), "Rows": len(frame),
            "Columns": list(frame.columns), "Column_Mapping": mapping,
            "Classification": "SYNTHETIC_DEMO" if mode == "SYNTHETIC_DEMO" else entry.get("provenance", "USER_PROVIDED"),
            "Version": str(entry.get("version", version)),
        })
        return frame

    def numbers(frame: pd.DataFrame, columns: list[str], *, positive: bool = False) -> None:
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        numeric(frame, columns, positive=positive)

    def identifiers(frame: pd.DataFrame, columns: list[str]) -> None:
        for column in columns:
            frame[column] = frame[column].astype(str)
            if frame[column].str.strip().eq("").any() or frame[column].str.strip().ne(frame[column]).any():
                fail(f"{context}: {column} must be nonempty without surrounding whitespace")

    def provenance(name: str) -> str:
        return next(row["Classification"] for row in report["Sources"] if row["Dataset"] == name)

    def check_quantity_units(frame: pd.DataFrame) -> None:
        if "Quantity_Unit" not in frame:
            return  # The schema explicitly inherits the product master's unit.
        matched = frame.merge(products[["Product_ID", "Quantity_Unit"]], on="Product_ID",
                              suffixes=("_input", "_master"), how="left", validate="many_to_one")
        if matched.Quantity_Unit_input.ne(matched.Quantity_Unit_master).any():
            fail(f"{context}: quantity unit differs from product master")

    def engine_ids(frame: pd.DataFrame) -> pd.DataFrame:
        return frame.rename(columns={"Product_ID": "Product Card Id", "Week": "Order_Date"})

    def item_set(frame: pd.DataFrame) -> set:
        return set(frame[["Plant_ID", "Product_ID"]].itertuples(index=False, name=None))

    def attach_plant(frame: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
        if "Plant_ID" in frame:
            identifiers(frame, ["Plant_ID"])
            if not item_set(frame).issubset(item_set(mapping)):
                fail(f"{context}: plant/product assignment conflicts with mapping")
            return frame
        result = frame.merge(mapping[["Plant_ID", "Product_ID"]], on="Product_ID", how="left", validate="many_to_one")
        if result.Plant_ID.isna().any():
            fail(f"{context}: product has no plant mapping")
        return result

    try:
        if mode not in DATA_MODES:
            fail("data_mode must be SYNTHETIC_DEMO or USER_DATA")
        if not version or not isinstance(files, dict) or not isinstance(assumptions, dict):
            fail("versioned configuration, files and assumptions objects required")
        if config.get("planning_interpretation") not in {"RETROSPECTIVE", "USER_PROVIDED_PLAN"}:
            fail("declare RETROSPECTIVE or USER_PROVIDED_PLAN; no forecast is generated")
        weeks = horizon(config["planning_start_week"], config["planning_end_week"])
        step = config.get("quantity_step")
        if isinstance(step, bool) or not isinstance(step, (int, float)) or not math.isfinite(step) or step < 0:
            fail("explicit finite nonnegative quantity_step required")
        if config.get("allocation_policy") != WORKLOAD_ALLOCATION_POLICY:
            fail("unsupported allocation_policy")
        definitions = config.get("scenarios")
        if not isinstance(definitions, list) or not definitions:
            fail("nonempty explicit scenarios required", ["Scenario_Comparison"])
        scenario_names = set()
        for definition in definitions:
            needed = {"Scenario", "Demand_Multiplier", "Capacity_Multiplier", "Disruption_Plants", "Disruption_Weeks", "Backlog_Policy"}
            if not isinstance(definition, dict) or not needed.issubset(definition):
                fail("scenario definition missing required fields", ["Scenario_Comparison"])
            name = definition["Scenario"]
            if not isinstance(name, str) or not name.strip() or name in scenario_names:
                fail("distinct nonempty scenario names required", ["Scenario_Comparison"])
            scenario_names.add(name)
            dm, cm = definition["Demand_Multiplier"], definition["Capacity_Multiplier"]
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in [dm, cm]) or dm < 0 or not 0 <= cm <= 1:
                fail("invalid scenario multipliers", ["Scenario_Comparison"])
            if name == "Baseline" and (dm != 1 or cm != 1):
                fail("Baseline must preserve source demand and capacity", ["Scenario_Comparison"])
            if definition["Backlog_Policy"] not in {"LOST_SALES", "CARRY_FORWARD"}:
                fail("explicit backlog policy required", ["Backlog_Planning"])
        if "Baseline" not in scenario_names:
            fail("Baseline scenario required", ["Scenario_Comparison"])
        products = table("products", ["Product_ID", "Product_Name"])
        plants = table("plants", ["Plant_ID"])
        mapping = table("product_plant_mapping", ["Product_ID", "Plant_ID"])
        identifiers(products, ["Product_ID"])
        identifiers(plants, ["Plant_ID"])
        identifiers(mapping, ["Product_ID", "Plant_ID"])
        require_frame(products, ["Product_ID", "Product_Name"], ["Product_ID"], "products")
        require_frame(plants, ["Plant_ID"], ["Plant_ID"], "plants")
        # Existing single-plant eligibility is deliberately retained.
        require_frame(mapping, ["Product_ID", "Plant_ID"], ["Product_ID"], "one-plant-per-product mapping")
        if products.empty or plants.empty or mapping.empty:
            fail("nonempty product, plant and mapping masters required")
        if set(mapping.Product_ID) - set(products.Product_ID) or set(mapping.Plant_ID) - set(plants.Plant_ID):
            fail("product/plant mapping contains unknown master identifiers")
        if products.Product_Name.isna().any() or products.Product_Name.astype(str).str.strip().eq("").any():
            fail("product names must be nonempty")
        cohort = config.get("product_ids", mapping.Product_ID.tolist())
        if not isinstance(cohort, list) or not cohort or len({str(p) for p in cohort}) != len(cohort):
            fail("product_ids must be a nonempty distinct cohort when supplied")
        cohort = [str(p) for p in cohort]
        if set(cohort) - set(mapping.Product_ID):
            fail("cohort contains unmapped products")
        items = mapping[mapping.Product_ID.isin(cohort)].copy()
        product_info = products[products.Product_ID.isin(cohort)].copy()
        if "Quantity_Unit" not in product_info:
            unit = assumptions.get("quantity_unit")
            if not isinstance(unit, str) or not unit.strip():
                fail("products require Quantity_Unit or explicit assumptions.quantity_unit")
            products["Quantity_Unit"] = unit
            product_info["Quantity_Unit"] = unit
            assumption("quantity_unit", unit, "Product quantity unit absent from supplied master")
        if product_info.Quantity_Unit.isna().any() or product_info.Quantity_Unit.astype(str).str.strip().eq("").any():
            fail("blank product quantity unit")
        if product_info.Quantity_Unit.nunique() != 1:
            fail("mixed quantity units require separate runs or explicit upstream conversion; aggregate quantity KPIs unavailable",
                 ["Scenario_Comparison", "Demand_Qualification"])
        priorities = table("priorities", ["Product_ID", "Planning_Priority"], optional=True)
        if priorities is not None:
            identifiers(priorities, ["Product_ID"])
            require_frame(priorities, ["Product_ID", "Planning_Priority"], ["Product_ID"], "priorities")
            if set(priorities.Product_ID) - set(products.Product_ID):
                fail("priority product missing from master")
            if "Planning_Priority" in product_info:
                fail("supply priority in product master or priorities file, not both")
            value_map = config.get("priority_value_mapping")
            if value_map is not None:
                priorities["Planning_Priority"] = priorities.Planning_Priority.map(value_map)
            product_info = product_info.merge(priorities, on="Product_ID", how="left", validate="one_to_one")
        if "Planning_Priority" not in product_info:
            if "planning_priority" not in assumptions:
                fail("planning priority unavailable; provide 1/2/3 or explicit assumptions.planning_priority", ["Workload_Planning", "Backlog_Planning", "Scenario_Comparison"])
            product_info["Planning_Priority"] = assumptions["planning_priority"]
            assumption("planning_priority", assumptions["planning_priority"], "Priority not supplied; no ABC inference")
        numbers(product_info, ["Planning_Priority"])
        if not product_info.Planning_Priority.isin([1, 2, 3]).all():
            fail("Planning_Priority must be 1, 2 or 3")
        product_info["Planning_Priority"] = product_info.Planning_Priority.astype(int)

        demand_format = config.get("demand_format")
        required_demand = ["Product_ID", "Demand_Qty", "Week"] if demand_format == "WEEKLY" else ["Product_ID", "Quantity", "Date", "Status", "Order_Line_ID"]
        raw_demand = table("demand", required_demand)
        identifiers(raw_demand, ["Product_ID"])
        if set(raw_demand.Product_ID) - set(products.Product_ID):
            fail("demand contains product missing from master")
        raw_demand = attach_plant(raw_demand, mapping)
        check_quantity_units(raw_demand)
        status_mapping = config.get("status_eligibility")
        if "Status" in raw_demand:
            if not isinstance(status_mapping, dict) or any(type(value) is not bool for value in status_mapping.values()):
                fail("explicit status_eligibility bool mapping required", ["Demand_Qualification"])
            if raw_demand.Status.astype(str).str.strip().eq("").any():
                fail("blank demand status", ["Demand_Qualification"])
            unknown = set(raw_demand.Status) - set(status_mapping)
            policy = config.get("unknown_status_policy", "ERROR")
            if policy not in {"ERROR", "EXCLUDE"}:
                fail("unknown_status_policy must be ERROR or EXCLUDE")
            if unknown and policy == "ERROR":
                fail(f"unmapped demand statuses: {sorted(unknown)}", ["Demand_Qualification"])
            status_mapping = dict(status_mapping)
            if unknown:
                status_mapping.update({status: False for status in unknown})
                report["Derived_Values"].append({"Name": "Default_Excluded_Statuses", "Statuses": sorted(unknown), "Basis": "EXPLICIT_EXCLUDE_POLICY"})
            forced = config.get("forced_excluded_statuses", [])
            if not isinstance(forced, list) or any(not isinstance(status, str) for status in forced):
                fail("forced_excluded_statuses must be a list of status labels")
            if any(status_mapping.get(status, False) for status in forced):
                fail("status mapping conflicts with configured forced_excluded_statuses", ["Demand_Qualification"])
        elif demand_format == "WEEKLY":
            if config.get("qualification_basis") != "ALREADY_QUALIFIED_INPUT":
                fail("status-free weekly demand requires explicit qualification_basis=ALREADY_QUALIFIED_INPUT", ["Demand_Qualification"])
            report["Derived_Values"].append({"Name": "Qualification", "Basis": "DECLARED_ALREADY_QUALIFIED_INPUT_POPULATION", "Limitation": "Gross covers supplied records only; exclusions outside this population are unknown."})
        if demand_format == "ORDER_LINES":
            identifiers(raw_demand, ["Order_Line_ID"])
            numbers(raw_demand, ["Quantity"])
            mapped = raw_demand.rename(columns={"Product_ID": "Product Card Id", "Order_Line_ID": "Order Item Id", "Quantity": "Order Item Quantity", "Date": "order date (DateOrders)", "Status": "Order Status"}).drop(columns="Plant_ID")
            ledger, weekly = prepare_order_demand(
                mapped, engine_ids(mapping), status_mapping,
                eligibility_version=str(config.get("eligibility_version", version)),
                source_is_complete=config.get("source_is_complete", False),
            )
            if config.get("source_is_complete") is True:
                assumption("complete_order_extract", True, "No-order internal-lifespan weeks treated as covered zero; edge/outside-lifespan weeks remain UNKNOWN")
        elif demand_format == "WEEKLY":
            numbers(raw_demand, ["Demand_Qty"])
            ledger = engine_ids(raw_demand)
            ledger = weekly_dates(ledger)
            require_frame(ledger, WEEK_KEY, WEEK_KEY + (["Status"] if "Status" in ledger else []), "weekly demand")
            ledger["Source_Record_ID"] = [f"csv-record-{n + 1}" for n in range(len(ledger))]
            ledger["Gross_Demand"] = ledger.Demand_Qty
            ledger["Is_Qualified"] = raw_demand.Status.map(status_mapping).to_numpy() if "Status" in raw_demand else True
            ledger["Qualified_Demand"] = ledger.Gross_Demand.where(ledger.Is_Qualified, 0)
            ledger["Excluded_Demand"] = ledger.Gross_Demand - ledger.Qualified_Demand
            ledger["Exclusion_Reason"] = raw_demand.Status.where(~ledger.Is_Qualified.to_numpy(), "").to_numpy() if "Status" in raw_demand else ""
            weekly = ledger.groupby(WEEK_KEY, as_index=False, sort=True)[["Gross_Demand", "Qualified_Demand", "Excluded_Demand"]].sum()
            derived_status = weekly.Qualified_Demand.gt(0).map({True: "OBSERVED_DEMAND", False: "OBSERVED_ZERO"})
            if "Coverage_Status" in ledger:
                labels = ledger.groupby(WEEK_KEY, sort=True).Coverage_Status
                if labels.nunique().gt(1).any():
                    fail("conflicting coverage labels within a product-week")
                weekly = weekly.merge(labels.first().reset_index(), on=WEEK_KEY, validate="one_to_one")
            else:
                weekly["Coverage_Status"] = derived_status
            allowed = {"OBSERVED_ZERO", "OBSERVED_DEMAND", "UNKNOWN", "OUT_OF_SCOPE"}
            if not weekly.Coverage_Status.isin(allowed).all():
                fail("unsupported Coverage_Status")
            known = weekly.Coverage_Status.isin(["OBSERVED_ZERO", "OBSERVED_DEMAND"])
            if weekly.loc[known, "Coverage_Status"].ne(derived_status[known]).any():
                fail("coverage label conflicts with qualified demand")
            weekly["Coverage_Basis"] = "EXPLICIT_WEEKLY_ROWS"
            weekly["Eligibility_Version"] = str(config.get("eligibility_version", version))
        else:
            fail("demand_format must be WEEKLY or ORDER_LINES")
        if weekly.empty:
            fail("nonempty demand required")
        if not (weekly.Gross_Demand - weekly.Qualified_Demand - weekly.Excluded_Demand).abs().le(1e-9).all():
            fail("gross != qualified + excluded")
        coverage = build_demand_coverage(weekly, engine_ids(items), weeks[0], weeks[-1])
        current = coverage[coverage.Order_Date.isin(weeks)].copy()
        if not current.Coverage_Status.isin(["OBSERVED_ZERO", "OBSERVED_DEMAND"]).all():
            fail("UNKNOWN or unavailable demand coverage blocks sequential planning; provide explicit zero rows rather than filling gaps",
                 ["Sequential_Inventory", "Backlog_Planning", "Scenario_Comparison"])
        current = current.merge(engine_ids(product_info[["Product_ID", "Product_Name", "Planning_Priority", "Quantity_Unit"]]), on="Product Card Id", validate="many_to_one").rename(columns={"Product_Name": "Product Name"})

        factor_input = table("workload_factors", ["Product_ID", "Workload_Factor", "Workload_Unit"], optional=True)
        if factor_input is None:
            if "uniform_workload_factor" not in assumptions or not assumptions.get("workload_unit"):
                fail("workload factors missing; supply a factor table or explicit uniform_workload_factor and workload_unit assumption", ["Workload_Planning", "Scenario_Comparison"])
            factors = engine_ids(items[["Product_ID"]].drop_duplicates())
            factors["Workload_Factor"] = assumptions["uniform_workload_factor"]
            factors["Workload_Unit"] = assumptions["workload_unit"]
            factors["Provenance_Type"] = "SYNTHETIC_ASSUMPTION"
            factors["Factor_Version"] = version
            assumption("uniform_workload_factor", assumptions["uniform_workload_factor"], "Relative workload assumption, not actual production standards")
        else:
            identifiers(factor_input, ["Product_ID"])
            check_quantity_units(factor_input)
            if set(factor_input.Product_ID) - set(products.Product_ID):
                fail("factor product missing from master")
            factors = engine_ids(factor_input)
            if "Factor_Version" not in factors:
                factors["Factor_Version"] = str(files["workload_factors"].get("version", version)) if isinstance(files["workload_factors"], dict) else version
            factors["Provenance_Type"] = provenance("workload_factors")
        numbers(factors, ["Workload_Factor"], positive=True)
        validate_workload_factors(factors, set(cohort))

        opening = table("initial_inventory", ["Product_ID", "Plant_ID", "Beginning_Inventory"], optional=True)
        if opening is None:
            if assumptions.get("initial_inventory") != "ZERO":
                fail("initial inventory missing; explicit ZERO assumption or input required", ["Sequential_Inventory", "Backlog_Planning", "Scenario_Comparison"])
            opening = items.copy()
            opening["Beginning_Inventory"] = 0.0
            assumption("initial_inventory", "ZERO", "Explicit synthetic planning initialization; no historical stock replay")
            initial_provenance = "SYNTHETIC_ASSUMPTION"
        else:
            initial_provenance = provenance("initial_inventory")
        identifiers(opening, ["Product_ID", "Plant_ID"])
        check_quantity_units(opening)
        require_frame(opening, ["Beginning_Inventory"], ["Plant_ID", "Product_ID"], "initial inventory")
        if not item_set(opening).issubset(item_set(mapping)):
            fail("initial inventory has invalid product/plant assignment")
        opening = opening[opening.Product_ID.isin(cohort)].copy()
        if item_set(opening) != item_set(items):
            fail("initial inventory must cover every initialized item exactly once", ["Sequential_Inventory"])
        numbers(opening, ["Beginning_Inventory"])
        if "Week" in opening and not weekly_dates(engine_ids(opening)).Order_Date.eq(weeks[0]).all():
            fail("initial inventory Week must match the first planning week")
        backlog = table("opening_backlog", ["Plant_ID", "Product_ID", "Beginning_Backlog"], optional=True)
        if backlog is not None:
            if "Beginning_Backlog" in opening:
                fail("opening backlog supplied twice")
            identifiers(backlog, ["Product_ID", "Plant_ID"])
            check_quantity_units(backlog)
            numbers(backlog, ["Beginning_Backlog"])
            require_frame(backlog, ["Beginning_Backlog"], ["Plant_ID", "Product_ID"], "opening backlog")
            if not item_set(backlog).issubset(item_set(mapping)):
                fail("opening backlog has invalid product/plant assignment")
            backlog = backlog[backlog.Product_ID.isin(cohort)]
            if item_set(backlog) != item_set(items):
                fail("opening backlog must cover the initialized cohort; do not infer missing balances", ["Backlog_Planning"])
            opening = opening.merge(backlog, on=["Plant_ID", "Product_ID"], validate="one_to_one")
        elif "Beginning_Backlog" not in opening:
            if assumptions.get("opening_backlog") != "ZERO":
                fail("opening backlog missing; configure explicit ZERO or provide balances", ["Backlog_Planning"])
            opening["Beginning_Backlog"] = 0.0
            assumption("opening_backlog", "ZERO", "Opening obligations unknown; explicit zero scenario assumption")
        numbers(opening, ["Beginning_Backlog"])
        initial = engine_ids(opening)
        initial["Provenance_Type"] = initial_provenance
        initial["Initial_State_Version"] = version

        receipt_input = table("external_receipts", ["Receipt_ID", "Plant_ID", "Product_ID", "Week", "External_Receipts_Qty"], optional=True)
        if receipt_input is None:
            if assumptions.get("external_receipts") != "NONE":
                fail("external receipts not supplied; declare NONE or supply usable-week events", ["Sequential_Inventory"])
            receipts = pd.DataFrame(columns=["Receipt_ID"] + WEEK_KEY + ["External_Receipts_Qty"])
            assumption("external_receipts", "NONE", "No external supply modeled; not a claim about historical procurement")
            receipt_provenance = "SYNTHETIC_ASSUMPTION"
        else:
            identifiers(receipt_input, ["Receipt_ID", "Plant_ID", "Product_ID"])
            check_quantity_units(receipt_input)
            if not item_set(receipt_input).issubset(item_set(mapping)):
                fail("external receipt has invalid product/plant assignment")
            receipts = weekly_dates(engine_ids(receipt_input))
            numbers(receipts, ["External_Receipts_Qty"])
            keys = ["Scenario", "Receipt_ID"] if "Scenario" in receipts else ["Receipt_ID"]
            require_frame(receipts, ["External_Receipts_Qty"], keys, "receipts")
            selected_receipts = receipts.Order_Date.isin(weeks) & receipts["Product Card Id"].isin(cohort)
            report["Derived_Values"].append({"Name": "Out_Of_Scope_Receipt_Rows", "Rows": int((~selected_receipts).sum())})
            receipts = receipts[selected_receipts].copy()
            receipt_provenance = provenance("external_receipts")
        receipts["Provenance_Type"] = receipt_provenance
        receipts["Receipt_Schedule_Version"] = version
        receipts = weekly_dates(receipts)
        numbers(receipts, ["External_Receipts_Qty"])

        capacity_input = table("weekly_capacity", ["Plant_ID", "Week", "Capacity", "Workload_Unit"], optional=True)
        if capacity_input is None:
            recipe = config.get("capacity_calibration")
            if not isinstance(recipe, dict):
                fail("weekly workload capacity missing; provide pools or explicit synthetic calibration", ["Workload_Planning", "Scenario_Comparison"])
            if not {"start_week", "end_week", "target_utilization", "capacity_version"}.issubset(recipe):
                fail("capacity calibration requires window, target utilization and version")
            calibration = build_demand_coverage(weekly, engine_ids(items), recipe["start_week"], recipe["end_week"])
            calibration = calibration[calibration.Coverage_Status.ne("OUT_OF_SCOPE")]
            baseline = calibrate_workload_capacity(calibration, factors, calibration_start=recipe["start_week"], calibration_end=recipe["end_week"],
                                                  target_utilization=recipe["target_utilization"], capacity_version=recipe["capacity_version"])
            calendar = baseline.merge(pd.DataFrame({"Order_Date": weeks}), how="cross")
            assumption("capacity_calibration", recipe, "Demand-calibrated workload capacity is synthetic, not measured production capacity")
        else:
            identifiers(capacity_input, ["Plant_ID"])
            if set(capacity_input.Plant_ID) - set(plants.Plant_ID):
                fail("capacity plant missing from master")
            calendar = weekly_dates(capacity_input.rename(columns={"Week": "Order_Date", "Capacity": "Baseline_Workload_Capacity"}))
            numbers(calendar, ["Baseline_Workload_Capacity"])
            require_frame(calendar, ["Workload_Unit"], ["Plant_ID", "Order_Date"], "weekly capacity")
            selected = calendar.Order_Date.isin(weeks) & calendar.Plant_ID.isin(items.Plant_ID)
            report["Derived_Values"].append({"Name": "Out_Of_Scope_Capacity_Rows", "Rows": int((~selected).sum())})
            calendar = calendar[selected].copy()
            expected = {(plant, week) for plant in set(items.Plant_ID) for week in weeks}
            if set(calendar[["Plant_ID", "Order_Date"]].itertuples(index=False, name=None)) != expected:
                fail("capacity must explicitly cover each selected plant/week, including zero capacity", ["Workload_Planning"])
            if calendar.Workload_Unit.isna().any() or set(calendar.Workload_Unit) != set(factors.Workload_Unit):
                fail("capacity and factors have incompatible workload units", ["Workload_Planning"])
            if "Factor_Version" in calendar and set(calendar.Factor_Version) != set(factors.Factor_Version):
                fail("capacity factor-version mismatch")
            calendar["Factor_Version"] = factors.Factor_Version.iloc[0]
            if "Capacity_Version" not in calendar:
                calendar["Capacity_Version"] = version
            calendar["Provenance_Type"] = provenance("weekly_capacity")
            baseline = calendar.copy()
        if "Scenario" in receipts and set(receipts.Scenario) - scenario_names:
            fail("receipt references an unknown scenario", ["Sequential_Inventory", "Scenario_Comparison"])
        for definition in definitions:
            affected = definition["Disruption_Plants"]
            if not isinstance(affected, list) or any(not isinstance(v, str) for v in affected) or len(set(affected)) != len(affected) or set(affected) - set(items.Plant_ID):
                fail("disruption plants must be distinct selected plant IDs", ["Scenario_Comparison"])
            if definition["Capacity_Multiplier"] != 1 and not affected:
                fail("capacity disruption requires explicit affected plants", ["Scenario_Comparison"])
            selected_weeks = definition["Disruption_Weeks"]
            if selected_weeks is not None:
                if not isinstance(selected_weeks, list):
                    fail("Disruption_Weeks must be a list or null", ["Scenario_Comparison"])
                parsed = weekly_dates(pd.DataFrame({"Order_Date": selected_weeks})).Order_Date
                if set(parsed) - set(weeks):
                    fail("disruption weeks outside planning horizon", ["Scenario_Comparison"])
            if definition["Backlog_Policy"] == "LOST_SALES" and initial.Beginning_Backlog.ne(0).any():
                fail("LOST_SALES cannot discard nonzero opening backlog", ["Backlog_Planning"])
        report["Canonical_Datasets"] = {
            name: {"Rows": len(frame), "Columns": list(frame.columns), "Dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()}, "Business_Key": key}
            for name, frame, key in [
                ("weekly_demand", weekly, WEEK_KEY), ("planning_demand", current, WEEK_KEY),
                ("capacity_pools", calendar, ["Plant_ID", "Order_Date"]), ("initial_state", initial, ITEM_KEY),
                ("external_receipts", receipts, (["Scenario"] if "Scenario" in receipts else []) + ["Receipt_ID"]),
                ("workload_factors", factors, ["Product Card Id"]),
            ]
        }
        report["Status"] = "READY"
        report["Capabilities"] = {name: "READY_WITH_ASSUMPTIONS" if report["Assumptions"] else "READY" for name in CAPABILITIES}
        report["Warnings"].append("USER_PROVIDED means supplied by the user, not independently verified historical fact.")
        current_ledger = ledger[ledger.Order_Date.isin(weeks)]
        scope = {
            "Product_IDs": cohort, "Selected_Products": len(cohort), "Planning_Horizon": [str(weeks[0].date()), str(weeks[-1].date())],
            "Input_Gross_Demand": float(ledger.Gross_Demand.sum()), "Input_Qualified_Demand": float(ledger.Qualified_Demand.sum()),
            "Input_Excluded_Demand": float(ledger.Excluded_Demand.sum()),
            "Horizon_Gross_All_Source": float(current_ledger.Gross_Demand.sum()), "Horizon_Qualified_All_Source": float(current_ledger.Qualified_Demand.sum()),
            "Horizon_Gross_Selected_Cohort": float(current.Gross_Demand.sum()), "Horizon_Qualified_Selected_Cohort": float(current.Qualified_Demand.sum()),
            "Horizon_Qualified_Outside_Cohort": float(current_ledger.Qualified_Demand.sum() - current.Qualified_Demand.sum()),
            "Coverage_Status_Counts": {str(k): int(v) for k, v in coverage.Coverage_Status.value_counts().items()},
            "Quantity_Unit": product_info.Quantity_Unit.iloc[0], "Demand_Basis": config["planning_interpretation"],
        }
        return CanonicalPlanningInputs(ledger, weekly, coverage, current, initial, receipts, factors, baseline, calendar, mode, report, scope)
    except InputValidationError:
        raise
    except (ValueError, TypeError, KeyError, OSError) as exc:
        fail(f"{context}: {exc}")
