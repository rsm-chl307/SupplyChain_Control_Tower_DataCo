"""Isolated end-to-end tests with explicitly synthetic fixture assumptions."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from dashboard.scenario_planning_app import load_sequential_outputs
from src.run_planning import run_sequential_planning
from src.sequential_planner import ALLOCATION_POLICY


class SequentialPipelineUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ["raw", "master", "processed", "inputs"]:
            (self.root / folder).mkdir()
        self.inputs = self.root / "inputs"
        pd.DataFrame({"Product Card Id": [1, 2], "Plant_ID": ["P1", "P1"]}).to_csv(self.root / "master/product_plant_mapping.csv", index=False)
        pd.DataFrame({"Product Card Id": [1, 2], "Product Name": ["One", "Two"]}).to_csv(self.root / "master/dim_product.csv", index=False)
        pd.DataFrame({"Plant_ID": ["P1"]}).to_csv(self.root / "master/dim_plant.csv", index=False)
        pd.DataFrame({"Product Card Id": [1, 2], "ABC_Class": ["A", "C"]}).to_csv(self.root / "processed/product_abc_classification.csv", index=False)
        raw = pd.DataFrame([
            [1, 1, "COMPLETE", "2017-01-02", 6],
            [2, 2, "COMPLETE", "2017-01-02", 4],
            [3, 1, "COMPLETE", "2017-01-09", 1],
            [4, 2, "COMPLETE", "2017-01-09", 1],
            [5, 1, "COMPLETE", "2017-01-22", 1],
            [6, 2, "CANCELED", "2017-01-22", 2],
            [7, 1, "SUSPECTED_FRAUD", "2017-01-22", 3],
        ], columns=["Order Item Id", "Product Card Id", "Order Status", "order date (DateOrders)", "Order Item Quantity"])
        raw.to_csv(self.root / "raw/orders.csv", index=False)
        pd.DataFrame({"Product Card Id": [1, 2], "Workload_Factor": [2., 1.], "Factor_Version": ["fixture"] * 2,
                      "Workload_Unit": ["EqWU"] * 2, "Provenance_Type": ["SYNTHETIC_TEST"] * 2}).to_csv(self.inputs / "factors.csv", index=False)
        pd.DataFrame({"Plant_ID": ["P1"] * 2, "Product Card Id": [1, 2], "Beginning_Inventory": [1., 0.], "Beginning_Backlog": [0., 0.],
                      "Provenance_Type": ["SYNTHETIC_TEST"] * 2, "Initial_State_Version": ["fixture"] * 2}).to_csv(self.inputs / "opening.csv", index=False)
        pd.DataFrame(columns=["Receipt_ID", "Plant_ID", "Product Card Id", "Order_Date", "External_Receipts_Qty",
                              "Provenance_Type", "Receipt_Schedule_Version"]).to_csv(self.inputs / "receipts.csv", index=False)
        pd.DataFrame({"Plant_ID": ["P1"], "Baseline_Workload_Capacity": [4.], "Capacity_Version": ["fixture"],
                      "Provenance_Type": ["SYNTHETIC_TEST"], "Factor_Version": ["fixture"], "Workload_Unit": ["EqWU"]}).to_csv(self.inputs / "capacity.csv", index=False)
        self.config = {
            "assumption_version": "SYNTHETIC_TEST", "planning_interpretation": "RETROSPECTIVE",
            "planning_start_week": "2017-01-08", "planning_end_week": "2017-01-22",
            "product_ids": [1, 2], "status_eligibility": {"COMPLETE": True, "CANCELED": False, "SUSPECTED_FRAUD": False},
            "eligibility_version": "fixture", "source_is_complete": True, "orders_file": "raw/orders.csv",
            "workload_factors_file": "factors.csv", "initial_state_file": "opening.csv", "external_receipts_file": "receipts.csv",
            "quantity_step": 0, "allocation_policy": ALLOCATION_POLICY, "capacity_file": "capacity.csv",
            "scenarios": [
                dict(Scenario=name, Demand_Multiplier=dm, Capacity_Multiplier=cm,
                     Disruption_Plants=["P1"], Disruption_Weeks=None, Backlog_Policy="CARRY_FORWARD")
                for name, dm, cm in [("Baseline", 1., 1.), ("Demand_Surge", 1.1, 1.), ("Capacity_Disruption", 1., .8), ("Combined_Stress", 1.1, .8)]
            ],
        }

    def execute(self):
        return run_sequential_planning(self.root, self.config, inputs_dir=self.inputs, output_root=self.root / "runs")

    def test_complete_raw_to_four_scenario_kpi_flow_and_loader(self):
        outputs = self.execute()
        manifest = json.loads(outputs["run_manifest"].read_text())
        self.assertEqual(manifest["Publication_Status"], "PUBLISHED")
        self.assertEqual(manifest["Validation_Status"], "PASSED")
        self.assertEqual(len(manifest["Artifacts"]), 12)
        tables = load_sequential_outputs(outputs["run_manifest"].parent)
        self.assertEqual(tables["allocation"].Scenario.nunique(), 4)
        self.assertEqual(len(tables["allocation"]), 24)
        self.assertEqual(tables["performance"].query("Aggregation_Level == 'Scenario'").shape[0], 4)

    def test_unique_runs_semantically_reproducible(self):
        first, second = self.execute(), self.execute()
        self.assertNotEqual(first["run_manifest"].parent, second["run_manifest"].parent)
        a = pd.read_csv(first["allocation_result"]).drop(columns=["Run_ID"])
        b = pd.read_csv(second["allocation_result"]).drop(columns=["Run_ID"])
        pd.testing.assert_frame_equal(a, b)

    def test_unknown_demand_blocks_publication(self):
        self.config["planning_end_week"] = "2017-01-29"
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            self.execute()
        manifest = json.loads(next((self.root / "runs").glob("*/run_manifest.json")).read_text())
        self.assertEqual(manifest["Publication_Status"], "UNPUBLISHED")
        self.assertEqual(manifest["Execution_Status"], "FAILED")

    def test_unresolved_status_is_not_qualified(self):
        self.config["status_eligibility"].pop("COMPLETE")
        with self.assertRaisesRegex(ValueError, "unresolved status"):
            self.execute()

    def test_failed_late_stage_does_not_publish_or_overwrite_previous_run(self):
        good = self.execute()
        before = good["run_manifest"].read_bytes()
        with patch("src.kpi_engine.calculate_sequential_kpis", side_effect=ValueError("injected failure")):
            with self.assertRaisesRegex(ValueError, "injected"):
                self.execute()
        self.assertEqual(before, good["run_manifest"].read_bytes())
        manifests = [json.loads(p.read_text()) for p in (self.root / "runs").glob("*/run_manifest.json")]
        self.assertEqual(sum(m["Publication_Status"] == "PUBLISHED" for m in manifests), 1)
        failed = next(p for p in (self.root / "runs").glob("*/run_manifest.json") if json.loads(p.read_text())["Publication_Status"] == "UNPUBLISHED")
        with self.assertRaisesRegex(ValueError, "unpublished"):
            load_sequential_outputs(failed.parent)

    def test_loader_rejects_modified_artifact(self):
        outputs = self.execute()
        with outputs["allocation_result"].open("a") as stream:
            stream.write("tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_sequential_outputs(outputs["run_manifest"].parent)

    def test_explicit_workload_calibration_path(self):
        del self.config["capacity_file"]
        self.config["capacity_calibration"] = dict(start_week="2017-01-08", end_week="2017-01-22", target_utilization=0.75, capacity_version="fixture-calibrated")
        outputs = self.execute()
        capacity = pd.read_csv(outputs["capacity_baseline"])
        self.assertEqual(capacity.Provenance_Type.iloc[0], "SYNTHETIC_DEMAND_CALIBRATED")
        self.assertAlmostEqual(capacity.Baseline_Workload_Capacity.iloc[0], (8 * 2 + 5) / 3 / .75)

    def test_both_shortage_modes_via_same_pipeline(self):
        for scenario in self.config["scenarios"]:
            scenario["Backlog_Policy"] = "LOST_SALES"
        tables = load_sequential_outputs(self.execute()["run_manifest"].parent)
        self.assertTrue(tables["allocation"].Ending_Backlog.eq(0).all())
        self.assertGreater(tables["allocation"].Lost_Sales_Qty.sum(), 0)


if __name__ == "__main__":
    unittest.main()
