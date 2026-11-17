"""Corruption tests for the frozen legacy validator; no self-oracle comparisons."""

import unittest

import pandas as pd

from src.allocation_engine import allocate_capacity
from src.allocation_validator import validate_allocation_results, validate_scenario_snapshot
from src.scenario_generator import SCENARIO_COLUMNS


class IndependentValidationUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.source = pd.DataFrame([
            ["P1", 1, "One", "2017-01-08", 8., 0., 10., 0., "A", 3, "P1|1|2017-01-08", "Baseline", 8., 10.],
            ["P1", 2, "Two", "2017-01-08", 6., 0., 10., 0., "B", 2, "P1|2|2017-01-08", "Baseline", 6., 10.],
        ], columns=SCENARIO_COLUMNS)
        self.good = allocate_capacity(self.source)

    def test_false_net_demand_rejected(self):
        bad = self.good.copy()
        bad[["Net_Demand", "Allocated_Qty", "Backlog"]] = 0.
        bad["Remaining_Capacity"] = 10.
        with self.assertRaisesRegex(ValueError, "Net_Demand"):
            validate_allocation_results(bad, self.source)

    def test_priority_inversion_rejected_with_balanced_arithmetic(self):
        bad = self.good.copy()
        bad["Allocated_Qty"] = [4., 6.]
        bad["Backlog"] = [4., 0.]
        bad["Allocation_Order"] = [2, 1]
        bad["Remaining_Capacity"] = [0., 4.]
        with self.assertRaisesRegex(ValueError, "priority"):
            validate_allocation_results(bad, self.source)

    def test_underallocation_with_slack_rejected(self):
        bad = self.good.copy()
        bad["Allocated_Qty"] = [0., 0.]
        bad["Backlog"] = bad.Net_Demand
        bad["Remaining_Capacity"] = 10.
        with self.assertRaisesRegex(ValueError, "greedy"):
            validate_allocation_results(bad)

    def test_forged_string_key_duplicate_rejected(self):
        extra = self.source.iloc[[0]].copy()
        extra["Planning_Key"] = "forged"
        with self.assertRaisesRegex(ValueError, "canonical"):
            validate_scenario_snapshot(pd.concat([self.source, extra], ignore_index=True))

    def test_infinity_rejected(self):
        bad = self.source.copy()
        bad.loc[0, "Scenario_Demand"] = float("inf")
        with self.assertRaises(ValueError):
            validate_scenario_snapshot(bad)

    def test_small_numeric_source_edit_is_not_hidden_by_default_relative_tolerance(self):
        bad = self.good.copy()
        bad.loc[0, "Weekly_Demand"] += 0.000001
        with self.assertRaisesRegex(ValueError, "preserved"):
            validate_allocation_results(bad, self.source)

    def test_preserved_source_edit_rejected(self):
        bad = self.good.copy()
        bad.loc[0, "Product Name"] = "Wrong"
        with self.assertRaisesRegex(ValueError, "preserved"):
            validate_allocation_results(bad, self.source)


if __name__ == "__main__":
    unittest.main()
