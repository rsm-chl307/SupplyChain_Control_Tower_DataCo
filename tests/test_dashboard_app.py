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


@unittest.skipUnless(all((ROOT / "data/processed" / name).is_file() for name in ["performance_result.csv", "allocation_result.csv", "scenario_snapshot.csv"]), "optional legacy reference dashboard artifacts unavailable")
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


class InvestigationAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        from src.run_planning import run_csv_planning

        allowed_root = ROOT / "tmp/planning_source_runs"
        allowed_root.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=allowed_root)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.runs = {}
        for mode in ["synthetic_demo", "user_data"]:
            directory = ROOT / "examples/planning" / mode
            config = json.loads((directory / "config.json").read_text())
            paths = run_csv_planning(config, inputs_dir=directory, output_root=cls.temporary.name)
            cls.runs[mode] = paths["run_manifest"].parent

    def open_run(self, directory):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "dashboard/scenario_planning_app.py"), default_timeout=60).run()
        next(item for item in app.sidebar.text_input if item.label == "Published sequential run folder").set_value(str(directory)).run()
        self.assertFalse(app.exception)
        return app

    def test_both_modes_paths_scenarios_week_and_exports_without_planning_or_file_changes(self):
        from unittest.mock import patch
        from src.planning_risk import investigation_views
        from dashboard.scenario_planning_app import load_sequential_outputs

        for mode, directory in self.runs.items():
            with self.subTest(mode=mode):
                before = {p.name: p.read_bytes() for p in directory.iterdir()}
                with patch("src.run_planning.run_csv_planning", side_effect=AssertionError("unexpected planning")), \
                     patch("src.run_planning.run_sequential_planning", side_effect=AssertionError("unexpected planning")):
                    app = self.open_run(directory)
                    tables = load_sequential_outputs(directory)
                    for scenario in ["Baseline", "Combined_Stress"]:
                        next(item for item in app.selectbox if item.label == "Sequential scenario").set_value(scenario).run()
                        for path in ["Product → Plant → Week", "Plant → Week → Product"]:
                            app.selectbox(key="investigation_path").set_value(path).run()
                            app.selectbox(key="investigation_week").select_index(len(app.selectbox(key="investigation_week").options) - 1).run()
                            self.assertFalse(app.exception)
                            key = dict(run_id=tables["allocation"].Run_ID.iloc[0], scenario=scenario,
                                       plant_id=app.selectbox(key="investigation_plant").value,
                                       product_id=app.selectbox(key="investigation_product").value,
                                       week=app.selectbox(key="investigation_week").value)
                            expected = investigation_views(tables["allocation"], tables["pools"], **key)
                            frames = [item.value for item in app.dataframe]
                            for name in ["selected_week", "shared_capacity", "adjacent_weeks", "allocation_peers"]:
                                self.assertTrue(any(frame.reset_index(drop=True).equals(expected[name].reset_index(drop=True))
                                                    for frame in frames), (mode, scenario, path, name))
                            self.assertIn("Download selected_week investigation evidence",
                                          [item.label for item in app.get("download_button")])
                    app.button(key="investigate_plant").click().run()
                    self.assertEqual(app.selectbox(key="investigation_path").value, "Plant → Week → Product")
                    app.button(key="investigate_product").click().run()
                    self.assertEqual(app.selectbox(key="investigation_path").value, "Product → Plant → Week")
                self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})

    def test_switching_runs_resets_invalid_context(self):
        app = self.open_run(self.runs["synthetic_demo"])
        app.selectbox(key="investigation_week").select_index(2).run()
        next(item for item in app.sidebar.text_input if item.label == "Published sequential run folder").set_value(str(self.runs["user_data"])).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="investigation_plant").value, "SITE-1")
        self.assertEqual(pd.Timestamp(app.selectbox(key="investigation_week").value), pd.Timestamp("2017-01-08"))


if __name__ == "__main__":
    unittest.main()
