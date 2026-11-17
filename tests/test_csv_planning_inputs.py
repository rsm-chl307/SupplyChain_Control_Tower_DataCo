"""Portable sources share one engine; user business semantics stay configurable."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from dashboard.scenario_planning_app import load_sequential_outputs
from src.csv_planning_inputs import InputValidationError, load_csv_planning_inputs
from src.run_planning import run_csv_planning, run_sequential_planning
from src.sequential_planner import simulate_sequential

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/planning"


class CSVPlanningInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        shutil.copytree(EXAMPLES / "user_data", self.inputs)
        self.config = json.loads((self.inputs / "config.json").read_text())

    def load(self):
        return load_csv_planning_inputs(self.config, self.inputs)

    def edit(self, filename, change):
        p = self.inputs / filename
        frame = pd.read_csv(p, dtype=str, keep_default_na=False)
        updated = change(frame)
        (frame if updated is None else updated).to_csv(p, index=False)

    def run_case(self):
        return run_csv_planning(self.config, inputs_dir=self.inputs, output_root=self.root / "runs")

    def test_custom_columns_sku_and_leading_zero_ids(self):
        bundle = self.load()
        self.assertEqual(bundle.report["Status"], "READY")
        self.assertEqual(set(bundle.demand["Product Card Id"]), {"SKU-A", "001"})
        self.assertEqual(bundle.demand.Qualified_Demand.sum(), 13)
        self.assertEqual(bundle.capacity_calendar.Baseline_Workload_Capacity.sum(), 10)
        self.assertEqual(bundle.initial.Beginning_Backlog.sum(), 0)
        self.assertEqual(bundle.receipts.External_Receipts_Qty.sum(), 2)

    def test_user_run_never_needs_dataco_or_abc(self):
        with patch("src.sequential_planner.simulate_sequential", wraps=simulate_sequential) as engine:
            outputs = run_sequential_planning(self.root / "DATACO_DOES_NOT_EXIST", self.config,
                                              inputs_dir=self.inputs, output_root=self.root / "runs")
        self.assertEqual(engine.call_count, 1)
        manifest = json.loads(outputs["run_manifest"].read_text())
        self.assertEqual(manifest["Data_Mode"], "USER_DATA")
        self.assertTrue(all(str(self.inputs) in p for p in manifest["Source_Hashes"]))
        loaded = load_sequential_outputs(outputs["run_manifest"].parent)
        self.assertIn("001", set(loaded["allocation"]["Product Card Id"]))
        self.assertEqual(manifest["Input_Validation"]["Status"], "READY")

    def test_both_data_modes_feed_identical_engine_inputs(self):
        source = EXAMPLES / "synthetic_demo"
        config = json.loads((source / "config.json").read_text())
        demo = load_csv_planning_inputs(config, source)
        config["data_mode"] = "USER_DATA"
        user = load_csv_planning_inputs(config, source)
        pd.testing.assert_frame_equal(demo.demand, user.demand)
        pd.testing.assert_frame_equal(demo.capacity_calendar.drop(columns=["Provenance_Type"]), user.capacity_calendar.drop(columns=["Provenance_Type"]))
        with patch("src.sequential_planner.simulate_sequential", wraps=simulate_sequential) as engine:
            a = run_csv_planning({**config, "data_mode": "SYNTHETIC_DEMO"}, inputs_dir=source, output_root=self.root / "runs")
            b = run_csv_planning(config, inputs_dir=source, output_root=self.root / "runs")
        self.assertEqual(engine.call_count, 2)
        x = pd.read_csv(a["allocation_result"]).drop(columns="Run_ID")
        y = pd.read_csv(b["allocation_result"]).drop(columns="Run_ID")
        pd.testing.assert_frame_equal(x, y)

    def test_missing_optional_inputs_require_explicit_assumptions(self):
        self.config["files"].pop("workload_factors")
        with self.assertRaises(InputValidationError) as error:
            self.load()
        self.assertIn("Workload_Planning", error.exception.report["Unavailable_Capabilities"])
        self.config["assumptions"] = {"uniform_workload_factor": 1.0, "workload_unit": "EqWU"}
        self.config["files"].pop("external_receipts")
        with self.assertRaisesRegex(InputValidationError, "receipts"):
            self.load()
        self.config["assumptions"]["external_receipts"] = "NONE"
        self.config["files"].pop("opening_backlog")
        with self.assertRaisesRegex(InputValidationError, "backlog"):
            self.load()
        self.config["assumptions"]["opening_backlog"] = "ZERO"
        bundle = self.load()
        self.assertEqual(bundle.report["Status"], "READY")
        self.assertEqual(len(bundle.receipts), 0)
        self.assertEqual(bundle.initial.Beginning_Backlog.sum(), 0)
        self.assertTrue(bundle.factors.Provenance_Type.eq("SYNTHETIC_ASSUMPTION").all())
        self.assertEqual({a["Name"] for a in bundle.report["Assumptions"]},
                         {"uniform_workload_factor", "external_receipts", "opening_backlog"})

    def test_explicit_zero_initialization_is_labeled_not_historical(self):
        self.config["files"].pop("initial_inventory")
        with self.assertRaisesRegex(InputValidationError, "initial inventory"):
            self.load()
        self.config["assumptions"] = {"initial_inventory": "ZERO"}
        bundle = self.load()
        self.assertEqual(bundle.initial.Beginning_Inventory.sum(), 0)
        self.assertTrue(bundle.initial.Provenance_Type.eq("SYNTHETIC_ASSUMPTION").all())

    def test_missing_demand_week_never_becomes_zero(self):
        self.edit("demand.csv", lambda f: f.iloc[:-1].copy())
        with self.assertRaises(InputValidationError) as error:
            self.load()
        self.assertIn("UNKNOWN", str(error.exception))
        self.assertIn("Sequential_Inventory", error.exception.report["Unavailable_Capabilities"])

    def test_status_mapping_has_no_universal_dataco_exclusions(self):
        source = EXAMPLES / "synthetic_demo"
        config = json.loads((source / "config.json").read_text())
        config["data_mode"] = "USER_DATA"
        config["status_eligibility"]["CANCELED"] = True
        bundle = load_csv_planning_inputs(config, source)
        self.assertEqual(bundle.weekly.Qualified_Demand.sum(), 15)
        config["forced_excluded_statuses"] = ["CANCELED"]
        with self.assertRaisesRegex(InputValidationError, "forced_excluded"):
            load_csv_planning_inputs(config, source)

    def test_unknown_status_errors_unless_explicit_exclude_policy(self):
        self.edit("demand.csv", lambda f: f.assign(state="NEW_STATUS"))
        with self.assertRaisesRegex(InputValidationError, "unmapped"):
            self.load()
        self.config["unknown_status_policy"] = "EXCLUDE"
        bundle = self.load()
        self.assertEqual(bundle.weekly.Qualified_Demand.sum(), 0)
        self.assertEqual(bundle.weekly.Excluded_Demand.sum(), 13)
        self.assertTrue(any(v["Name"] == "Default_Excluded_Statuses" for v in bundle.report["Derived_Values"]))

    def test_status_free_weekly_input_needs_declared_basis(self):
        self.config["files"]["demand"]["columns"].pop("Status")
        self.edit("demand.csv", lambda f: f.drop(columns="state"))
        with self.assertRaisesRegex(InputValidationError, "ALREADY_QUALIFIED"):
            self.load()
        self.config["qualification_basis"] = "ALREADY_QUALIFIED_INPUT"
        bundle = self.load()
        self.assertEqual(bundle.weekly.Gross_Demand.sum(), bundle.weekly.Qualified_Demand.sum())
        self.assertTrue(any(v["Name"] == "Qualification" for v in bundle.report["Derived_Values"]))

    def test_unknown_product_plant_and_duplicate_mapping_rejected(self):
        self.edit("mapping.csv", lambda f: f.assign(site="BAD_SITE"))
        with self.assertRaisesRegex(InputValidationError, "unknown master"):
            self.load()
        self.edit("mapping.csv", lambda f: f.assign(site="SITE-1"))
        self.edit("mapping.csv", lambda f: pd.concat([f, f.iloc[[0]]], ignore_index=True))
        with self.assertRaisesRegex(InputValidationError, "duplicate"):
            self.load()

    def test_invalid_quantities_and_incompatible_workload_units(self):
        original = (self.inputs / "demand.csv").read_text()
        for value in ["bad", "-1", "inf", "nan"]:
            (self.inputs / "demand.csv").write_text(original)
            self.edit("demand.csv", lambda f, v=value: f.assign(units=v))
            with self.assertRaises(InputValidationError):
                self.load()
        (self.inputs / "demand.csv").write_text(original)
        self.edit("capacity.csv", lambda f: f.assign(load_unit="HOURS"))
        with self.assertRaisesRegex(InputValidationError, "incompatible workload units"):
            self.load()

    def test_quantity_unit_mismatch_and_mixed_units_rejected(self):
        self.edit("demand.csv", lambda f: f.assign(uom="KG"))
        with self.assertRaisesRegex(InputValidationError, "quantity unit"):
            self.load()
        self.edit("products.csv", lambda f: f.assign(uom=["EA", "KG"]))
        with self.assertRaisesRegex(InputValidationError, "mixed quantity"):
            self.load()

    def test_optional_supply_quantity_units_cannot_conflict_with_master(self):
        for dataset, filename in [("initial_inventory", "initial_inventory.csv"),
                                  ("opening_backlog", "opening_backlog.csv"),
                                  ("external_receipts", "receipts.csv"),
                                  ("workload_factors", "factors.csv")]:
            with self.subTest(dataset=dataset):
                self.config["files"][dataset]["columns"]["Quantity_Unit"] = "uom"
                self.edit(filename, lambda frame: frame.assign(uom="KG"))
                with self.assertRaisesRegex(InputValidationError, "quantity unit"):
                    self.load()
                self.config["files"][dataset]["columns"].pop("Quantity_Unit")
                self.edit(filename, lambda frame: frame.drop(columns="uom"))

    def test_missing_capacity_week_is_not_inferred(self):
        self.edit("capacity.csv", lambda f: f.iloc[:-1])
        with self.assertRaises(InputValidationError) as error:
            self.load()
        self.assertIn("Workload_Planning", error.exception.report["Unavailable_Capabilities"])

    def test_duplicate_weekly_demand_and_partial_openings_rejected(self):
        self.edit("demand.csv", lambda f: pd.concat([f, f.iloc[[0]]], ignore_index=True))
        with self.assertRaisesRegex(InputValidationError, "duplicate"):
            self.load()
        shutil.copyfile(EXAMPLES / "user_data/demand.csv", self.inputs / "demand.csv")
        self.edit("initial_inventory.csv", lambda f: f.iloc[:1])
        with self.assertRaisesRegex(InputValidationError, "cover every"):
            self.load()

    def test_blocked_intake_is_never_published_and_report_is_retained(self):
        self.config["files"].pop("workload_factors")
        with self.assertRaises(InputValidationError):
            self.run_case()
        manifest = json.loads(next((self.root / "runs").glob("*/run_manifest.json")).read_text())
        self.assertEqual(manifest["Publication_Status"], "UNPUBLISHED")
        self.assertEqual(manifest["Input_Validation"]["Status"], "BLOCKED")
        self.assertIn("Workload_Planning", manifest["Input_Validation"]["Unavailable_Capabilities"])

    def test_future_user_supplied_plan_is_not_forced_to_dataco_dates(self):
        replacements = {"2017-01-08": "2027-01-03", "2017-01-15": "2027-01-10", "2017-01-22": "2027-01-17"}
        for filename in ["demand.csv", "capacity.csv", "receipts.csv"]:
            self.edit(filename, lambda f: f.replace(replacements))
        self.config["planning_start_week"] = "2027-01-03"
        self.config["planning_end_week"] = "2027-01-17"
        bundle = self.load()
        self.assertEqual(bundle.demand.Order_Date.min(), pd.Timestamp("2027-01-03"))
        outputs = self.run_case()
        self.assertEqual(json.loads(outputs["run_manifest"].read_text())["Publication_Status"], "PUBLISHED")

    def test_declared_initial_week_and_bad_dates_rejected(self):
        self.edit("initial_inventory.csv", lambda f: f.assign(Week="2017-01-15"))
        with self.assertRaisesRegex(InputValidationError, "first planning"):
            self.load()

    def test_weekly_status_totals_reconcile_without_double_counting(self):
        self.edit("demand.csv", lambda f: pd.concat([f, f.iloc[[0]].assign(state="BLOCKED", units="5")], ignore_index=True))
        bundle = self.load()
        self.assertEqual(len(bundle.demand), 6)
        self.assertEqual(len(bundle.ledger), 7)
        self.assertEqual(bundle.demand.Gross_Demand.sum(), 18)
        self.assertEqual(bundle.demand.Qualified_Demand.sum(), 13)
        self.assertEqual(bundle.demand.Excluded_Demand.sum(), 5)

    def test_validation_only_rejects_unusable_scenario_and_loss_policy(self):
        self.config["scenarios"][0]["Demand_Multiplier"] = 2
        with self.assertRaisesRegex(InputValidationError, "Baseline"):
            self.load()
        self.config["scenarios"][0]["Demand_Multiplier"] = 1
        self.config["scenarios"][0]["Disruption_Plants"] = ["BAD"]
        with self.assertRaisesRegex(InputValidationError, "plant IDs"):
            self.load()
        self.config["scenarios"][0]["Disruption_Plants"] = ["SITE-1"]
        self.config["scenarios"][0]["Backlog_Policy"] = "LOST_SALES"
        self.edit("opening_backlog.csv", lambda f: f.assign(open_qty="1"))
        with self.assertRaisesRegex(InputValidationError, "nonzero opening"):
            self.load()

    def test_literal_na_identifier_survives_input_and_published_output(self):
        for filename in ["products.csv", "mapping.csv", "demand.csv", "factors.csv",
                         "initial_inventory.csv", "opening_backlog.csv", "receipts.csv"]:
            self.edit(filename, lambda frame: frame.assign(sku=frame.sku.replace({"001": "NA"})))
        output = self.run_case()
        loaded = load_sequential_outputs(output["run_manifest"].parent)
        self.assertEqual(set(loaded["allocation"]["Product Card Id"]), {"SKU-A", "NA"})

    def test_dataco_whitelist_is_only_an_optional_profile_configuration(self):
        profile = json.loads((EXAMPLES / "dataco_reference/config.json").read_text())
        self.assertEqual(profile["data_mode"], "USER_DATA")
        self.assertEqual({s for s, eligible in profile["status_eligibility"].items() if eligible},
                         {"COMPLETE", "CLOSED", "PROCESSING"})
        self.assertEqual(set(profile["forced_excluded_statuses"]), {"CANCELED", "SUSPECTED_FRAUD"})
        self.assertEqual(profile["unknown_status_policy"], "EXCLUDE")
        self.assertEqual(profile["files"]["initial_inventory"]["provenance"], "SYNTHETIC_ASSUMPTION")

    def test_receipt_scenario_reference_is_checked_during_intake(self):
        self.edit("receipts.csv", lambda frame: frame.assign(Scenario="NOT_CONFIGURED"))
        with self.assertRaisesRegex(InputValidationError, "unknown scenario"):
            self.load()

    def test_unknown_mode_and_bad_column_mappings_rejected(self):
        self.config["data_mode"] = "DATACO_REQUIRED"
        with self.assertRaisesRegex(InputValidationError, "data_mode"):
            self.load()
        self.config["data_mode"] = "USER_DATA"
        self.config["files"]["products"]["columns"]["Product_Name"] = "not_a_column"
        with self.assertRaisesRegex(InputValidationError, "mapped source columns absent"):
            self.load()


if __name__ == "__main__":
    unittest.main()
