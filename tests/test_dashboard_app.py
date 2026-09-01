import tempfile
import unittest
from pathlib import Path

import pandas as pd

from dashboard.scenario_planning_app import load_dashboard_outputs, scenario_comparison, scenario_kpis


ROOT = Path(__file__).parents[1]


class DashboardIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_dir = ROOT / "data/processed"
        cls.performance = pd.read_csv(cls.output_dir / "performance_result.csv")

    def test_loads_approved_backend_outputs(self):
        outputs = load_dashboard_outputs(self.output_dir)
        self.assertEqual(len(outputs["performance"]), 171)
        self.assertEqual(len(outputs["allocation"]), 5931)
        self.assertEqual(len(outputs["scenario"]), 5931)

    def test_scenario_kpis_filters_aggregation_level(self):
        result = scenario_kpis(self.performance)
        self.assertEqual(set(result["Aggregation_Level"]), {"Scenario"})
        self.assertEqual(len(result), 3)

    def test_comparison_uses_prepared_baseline_deltas(self):
        result = scenario_comparison(self.performance)
        self.assertIn("Service_Level_Change", result.columns)
        self.assertIn("Backlog_Change", result.columns)
        baseline = result[result["Scenario"] == "Baseline"].iloc[0]
        self.assertEqual(float(baseline["Service_Level_Change"]), 0.0)

    def test_missing_output_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_dashboard_outputs(directory)


if __name__ == "__main__":
    unittest.main()
