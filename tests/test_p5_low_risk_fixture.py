"""Independent P5 low-risk fixture check; no V1.1 trust issuer changes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.planning_risk import product_risk_ranking
from src.run_planning import run_csv_planning


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "p5_low_risk_v1"


class P5LowRiskFixtureTests(unittest.TestCase):
    def test_pinned_independent_fixture_produces_healthy_baseline(self):
        manifest = json.loads((FIXTURE / "MANIFEST.json").read_text())
        self.assertEqual(manifest["fixture_version"], "p5-low-risk-v1")
        self.assertEqual(manifest["data_mode"], "SYNTHETIC_DEMO")
        config = json.loads((FIXTURE / "config.json").read_text())
        self.assertEqual(config["data_mode"], "SYNTHETIC_DEMO")
        self.assertEqual(set(manifest["files_sha256"]), {"config.json"} |
                         {item["path"] for item in config["files"].values()})
        for name, expected in manifest["files_sha256"].items():
            path = FIXTURE / name
            self.assertEqual(path.name, name)
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

        with tempfile.TemporaryDirectory(prefix="p5-low-risk-test-") as workspace:
            outputs = run_csv_planning(
                config, inputs_dir=FIXTURE, output_root=Path(workspace) / "runs"
            )
            run_path = outputs["run_manifest"].parent
            self.assertTrue(run_path.is_relative_to(Path(workspace)))
            published = json.loads(outputs["run_manifest"].read_text())
            self.assertEqual(published["Data_Mode"], "SYNTHETIC_DEMO")
            self.assertEqual(published["Execution_Status"], "SUCCEEDED")
            self.assertEqual(published["Validation_Status"], "PASSED")
            self.assertEqual(published["Publication_Status"], "PUBLISHED")
            allocation = pd.read_csv(outputs["allocation_result"])
            baseline = allocation.loc[allocation.Scenario.eq("Baseline")]
            risk = product_risk_ranking(baseline)
            self.assertEqual(len(risk), 2)
            self.assertEqual(set(risk.Risk_Category), {"Healthy"})
            self.assertTrue(risk.Ending_Backlog.eq(0).all())
            self.assertTrue(risk.Lost_Sales_Qty.eq(0).all())
            self.assertTrue(risk.Demand_Fulfillment_Rate.eq(1).all())
            self.assertTrue(risk.Ending_Inventory.gt(0).all())
        self.assertFalse(Path(workspace).exists())


if __name__ == "__main__":
    unittest.main()
