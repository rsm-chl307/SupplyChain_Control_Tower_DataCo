import unittest
from pathlib import Path

import pandas as pd

from src.scenario_generator import (
    SCENARIO_COLUMNS,
    ScenarioValidationError,
    generate_scenarios,
)


INPUT_PATH = Path(__file__).parents[1] / "data/processed/planning_snapshot_20170101_20171231.csv"


class ScenarioGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = pd.read_csv(INPUT_PATH, parse_dates=["Order_Date"])

    def params(self):
        return [
            {"scenario": "Baseline"},
            {"scenario": "Demand_Surge", "demand_increase_pct": 10.0},
            {
                "scenario": "Capacity_Disruption",
                "capacity_reduction_pct": 20.0,
                "plant_ids": ["P1"],
            },
        ]

    def generate(self, params=None):
        return generate_scenarios(self.snapshot, params or self.params())

    def test_baseline_values_unchanged(self):
        output = self.generate()
        baseline = output[output.Scenario == "Baseline"].sort_values("Planning_Key")
        source = self.snapshot.sort_values("Planning_Key")
        pd.testing.assert_series_equal(baseline.Weekly_Demand.reset_index(drop=True), source.Weekly_Demand.reset_index(drop=True))
        self.assertTrue((baseline.Scenario_Demand.reset_index(drop=True) == source.Weekly_Demand.reset_index(drop=True)).all())
        self.assertTrue((baseline.Scenario_Capacity.reset_index(drop=True) == source.Weekly_Capacity.reset_index(drop=True)).all())

    def test_demand_surge_increases_demand_by_ten_percent(self):
        output = self.generate()
        surge = output[output.Scenario == "Demand_Surge_10pct"]
        self.assertTrue((surge.Scenario_Demand == surge.Weekly_Demand * 1.10).all())

    def test_demand_surge_leaves_capacity_unchanged(self):
        output = self.generate()
        surge = output[output.Scenario == "Demand_Surge_10pct"]
        self.assertTrue((surge.Scenario_Capacity == surge.Weekly_Capacity).all())

    def test_capacity_disruption_reduces_capacity_by_twenty_percent(self):
        output = self.generate()
        disrupted = output[output.Scenario == "Capacity_Disruption_P1_20pct"]
        p1 = disrupted.Plant_ID == "P1"
        self.assertTrue((disrupted.loc[p1, "Scenario_Capacity"] == disrupted.loc[p1, "Weekly_Capacity"] * 0.8).all())

    def test_capacity_disruption_affects_only_selected_plants(self):
        output = self.generate()
        disrupted = output[output.Scenario == "Capacity_Disruption_P1_20pct"]
        other = disrupted.Plant_ID != "P1"
        self.assertTrue((disrupted.loc[other, "Scenario_Capacity"] == disrupted.loc[other, "Weekly_Capacity"]).all())

    def test_capacity_disruption_week_range_affects_only_selected_weeks(self):
        params = [{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 20, "plant_ids": ["P1"], "week_start": "2017-03-01", "week_end": "2017-06-30"}]
        output = self.generate(params)
        disrupted = output.iloc[:]
        affected = (disrupted.Plant_ID == "P1") & disrupted.Order_Date.between("2017-03-01", "2017-06-30")
        self.assertTrue((disrupted.loc[affected, "Scenario_Capacity"] == disrupted.loc[affected, "Weekly_Capacity"] * 0.8).all())
        unaffected = ~affected
        self.assertTrue((disrupted.loc[unaffected, "Scenario_Capacity"] == disrupted.loc[unaffected, "Weekly_Capacity"]).all())

    def test_capacity_disruption_without_week_range_covers_horizon(self):
        output = self.generate([{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 20, "plant_ids": ["P1"]}])
        self.assertTrue((output.Scenario_Capacity == output.Weekly_Capacity * 0.8).where(output.Plant_ID == "P1", True).all())

    def test_capacity_disruption_leaves_demand_unchanged(self):
        output = self.generate()
        disrupted = output[output.Scenario == "Capacity_Disruption_P1_20pct"]
        self.assertTrue((disrupted.Scenario_Demand == disrupted.Weekly_Demand).all())

    def test_invalid_scenario_name_fails(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Unknown"}])

    def test_missing_required_parameters_fail(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Demand_Surge"}])
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Capacity_Disruption", "plant_ids": ["P1"]}])

    def test_invalid_percentage_fails(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Demand_Surge", "demand_increase_pct": -1}])
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 101, "plant_ids": ["P1"]}])

    def test_unknown_plant_fails(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 20, "plant_ids": ["UNKNOWN"]}])

    def test_invalid_week_range_fails(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 20, "plant_ids": ["P1"], "week_start": "2017-06-01", "week_end": "2017-05-01"}])
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Capacity_Disruption", "capacity_reduction_pct": 20, "plant_ids": ["P1"], "week_start": "2014-01-01", "week_end": "2017-05-01"}])

    def test_priority_shift_is_rejected(self):
        with self.assertRaises(ScenarioValidationError):
            self.generate([{"scenario": "Priority_Shift", "priority": "A"}])

    def test_sparse_row_count_is_preserved(self):
        output = self.generate()
        self.assertEqual(len(output), len(self.snapshot) * 3)
        self.assertEqual(len(output[output.Scenario == "Baseline"]), len(self.snapshot))

    def test_scenario_key_is_unique(self):
        output = self.generate()
        self.assertFalse(output.duplicated(["Scenario", "Planning_Key"]).any())

    def test_repeated_execution_is_deterministic(self):
        first = self.generate().to_csv(index=False, date_format="%Y-%m-%d")
        second = self.generate().to_csv(index=False, date_format="%Y-%m-%d")
        self.assertEqual(first, second)

    def test_input_snapshot_remains_unchanged(self):
        original = self.snapshot.copy(deep=True)
        self.generate()
        pd.testing.assert_frame_equal(self.snapshot, original)

    def test_exact_schema_and_no_allocation_fields(self):
        output = self.generate()
        self.assertEqual(list(output.columns), SCENARIO_COLUMNS)
        self.assertFalse({"Allocated", "Net_Demand", "Backlog", "Service_Level", "Utilization"}.intersection(output.columns))


if __name__ == "__main__":
    unittest.main()
