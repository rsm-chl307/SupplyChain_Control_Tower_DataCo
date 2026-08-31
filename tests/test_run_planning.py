import hashlib
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.run_planning import PlanningRunError, run_planning


ROOT = Path(__file__).parents[1]
DATA_ROOT = ROOT / "data"


class EndToEndRunnerTests(unittest.TestCase):
    def protected_hashes(self):
        paths = [
            DATA_ROOT / "processed/planning_snapshot.csv",
            DATA_ROOT / "processed/planning_snapshot_20170101_20171231.csv",
            DATA_ROOT / "processed/scenario_snapshot.csv",
            DATA_ROOT / "processed/allocation_result.csv",
            DATA_ROOT / "processed/performance_result.csv",
        ]
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    def execute(self, **kwargs):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        disruption_plant = kwargs.pop("disruption_plant", "P1")
        return run_planning(
            DATA_ROOT,
            "2017-01-01",
            "2017-12-31",
            output_dir=Path(temp.name) / "run",
            disruption_plant=disruption_plant,
            **kwargs,
        )

    def test_valid_end_to_end_execution(self):
        outputs = self.execute()
        self.assertTrue(all(path.exists() for path in outputs.values()))
        self.assertEqual(len(pd.read_csv(outputs["planning_snapshot"])), 1977)
        self.assertEqual(len(pd.read_csv(outputs["scenario_snapshot"])), 5931)
        self.assertEqual(len(pd.read_csv(outputs["allocation_result"])), 5931)
        self.assertGreater(len(pd.read_csv(outputs["performance_result"])), 0)

    def test_invalid_planning_horizon_fails(self):
        with self.assertRaises(PlanningRunError):
            run_planning(DATA_ROOT, "2014-01-01", "2017-12-31", disruption_plant="P1")

    def test_reversed_planning_horizon_fails(self):
        with self.assertRaises(PlanningRunError):
            run_planning(DATA_ROOT, "2017-12-31", "2017-01-01", disruption_plant="P1")

    def test_demand_surge_parameter_validation(self):
        with self.assertRaises(ValueError):
            self.execute(demand_surge_pct=-1)

    def test_capacity_disruption_parameter_validation(self):
        with self.assertRaises(ValueError):
            self.execute(capacity_disruption_pct=101)

    def test_missing_disruption_plant_fails(self):
        with self.assertRaises(PlanningRunError):
            run_planning(DATA_ROOT, "2017-01-01", "2017-12-31")

    def test_invalid_disruption_plant_fails(self):
        with self.assertRaises(ValueError):
            self.execute(disruption_plant="UNKNOWN")

    def test_parameters_propagate_to_scenarios(self):
        outputs = self.execute(demand_surge_pct=25.0, capacity_disruption_pct=50.0, disruption_plant="P2")
        scenarios = pd.read_csv(outputs["scenario_snapshot"])
        surge = scenarios[scenarios.Scenario == "Demand_Surge_25pct"]
        disruption = scenarios[scenarios.Scenario == "Capacity_Disruption_P2_50pct"]
        self.assertTrue((surge.Scenario_Demand == surge.Weekly_Demand * 1.25).all())
        self.assertTrue((disruption.loc[disruption.Plant_ID == "P2", "Scenario_Capacity"] == disruption.loc[disruption.Plant_ID == "P2", "Weekly_Capacity"] * 0.5).all())

    def test_expected_output_artifacts_and_names(self):
        outputs = self.execute()
        self.assertTrue(outputs["planning_snapshot"].name.startswith("planning_snapshot_20170101_20171231"))
        self.assertEqual(outputs["scenario_snapshot"].name, "scenario_snapshot.csv")
        self.assertEqual(outputs["allocation_result"].name, "allocation_result.csv")
        self.assertEqual(outputs["performance_result"].name, "performance_result.csv")

    def test_repeated_execution_is_deterministic(self):
        first = self.execute()
        second = self.execute()
        for name in first:
            self.assertEqual(first[name].read_bytes(), second[name].read_bytes())

    def test_completed_stage_artifacts_are_preserved(self):
        before = self.protected_hashes()
        self.execute()
        self.assertEqual(before, self.protected_hashes())


if __name__ == "__main__":
    unittest.main()
