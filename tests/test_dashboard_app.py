import tempfile
import unittest
from pathlib import Path

import pandas as pd

from dashboard.scenario_planning_app import (
    allocation_plant_summary,
    comparison_display_table,
    format_percentage_points,
    load_dashboard_outputs,
    scenario_comparison,
    scenario_insights,
    scenario_kpis,
)


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

    def test_change_formatting_uses_percentage_points(self):
        self.assertEqual(format_percentage_points(0.0023), "+0.23 percentage points")
        display = comparison_display_table(self.performance)
        self.assertIn("percentage points", display["Service_Level_Change"].iloc[0])

    def test_insights_are_deterministic_and_use_stage5_values(self):
        first = scenario_insights(self.performance)
        second = scenario_insights(self.performance)
        self.assertEqual(first, second)
        self.assertTrue(any("capacity pressure" in value for value in first))
        self.assertTrue(any("No alternative scenario creates backlog" in value for value in first))

    def test_allocation_plant_summary_uses_prepared_plant_kpis(self):
        outputs = load_dashboard_outputs(self.output_dir)
        summary = allocation_plant_summary(outputs["allocation"], outputs["performance"])
        self.assertEqual(len(summary), 9)
        self.assertTrue({"Total_Scenario_Capacity", "Remaining_Capacity", "Performance_Status"}.issubset(summary.columns))

    def test_missing_output_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_dashboard_outputs(directory)


if __name__ == "__main__":
    unittest.main()
