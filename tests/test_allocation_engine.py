import unittest

import pandas as pd

from src.allocation_manager import run_allocation
from src.allocation_validator import AllocationValidationError, validate_allocation_results


class AllocationEngineTests(unittest.TestCase):
    def setUp(self):
        rows = [
            ["P1", 10, "Product 10", "2017-01-01", 5, 10, 10, 5, "A", 3, "P1|10|2017-01-01", "Baseline", 5, 10],
            ["P1", 20, "Product 20", "2017-01-01", 12, 0, 10, 5, "B", 2, "P1|20|2017-01-01", "Baseline", 12, 10],
            ["P1", 30, "Product 30", "2017-01-01", 4, 0, 10, 5, "C", 1, "P1|30|2017-01-01", "Baseline", 4, 10],
            ["P2", 40, "Product 40", "2017-01-01", 7, 0, 8, 4, "A", 3, "P2|40|2017-01-01", "Baseline", 7, 8],
            ["P1", 10, "Product 10", "2017-01-01", 5, 10, 10, 5, "A", 3, "P1|10|2017-01-01", "Demand_Surge_10pct", 5.5, 10],
            ["P1", 20, "Product 20", "2017-01-01", 12, 0, 10, 5, "B", 2, "P1|20|2017-01-01", "Demand_Surge_10pct", 13.2, 10],
            ["P1", 30, "Product 30", "2017-01-01", 4, 0, 10, 5, "C", 1, "P1|30|2017-01-01", "Demand_Surge_10pct", 4.4, 10],
            ["P2", 40, "Product 40", "2017-01-01", 7, 0, 8, 4, "A", 3, "P2|40|2017-01-01", "Demand_Surge_10pct", 7.7, 8],
        ]
        columns = ["Plant_ID", "Product Card Id", "Product Name", "Order_Date", "Weekly_Demand", "Beginning_Inventory", "Weekly_Capacity", "Baseline_Available_Capacity", "ABC_Class", "Planning_Priority", "Planning_Key", "Scenario", "Scenario_Demand", "Scenario_Capacity"]
        self.snapshot = pd.DataFrame(rows, columns=columns)
        self.snapshot["Order_Date"] = pd.to_datetime(self.snapshot["Order_Date"])

    def test_inventory_covered_demand_requires_no_production(self):
        result = run_allocation(self.snapshot)
        row = result[(result.Scenario == "Baseline") & (result["Product Card Id"] == 10)].iloc[0]
        self.assertEqual(row.Net_Demand, 0)
        self.assertEqual(row.Allocated_Qty, 0)
        self.assertEqual(row.Backlog, 0)
        self.assertEqual(row.Allocation_Reason, "No Production Required")

    def test_demand_requiring_production(self):
        result = run_allocation(self.snapshot)
        row = result[(result.Scenario == "Baseline") & (result["Product Card Id"] == 20)].iloc[0]
        self.assertEqual(row.Net_Demand, 12)
        self.assertEqual(row.Allocated_Qty, 10)

    def test_capacity_sufficient_for_all_requirements(self):
        snapshot = self.snapshot.copy()
        snapshot.loc[snapshot.Plant_ID == "P1", "Scenario_Capacity"] = 100
        result = run_allocation(snapshot)
        p1 = result[(result.Scenario == "Baseline") & (result.Plant_ID == "P1")]
        self.assertEqual(p1.Backlog.sum(), 0)

    def test_capacity_shortage(self):
        result = run_allocation(self.snapshot)
        p1 = result[(result.Scenario == "Baseline") & (result.Plant_ID == "P1")]
        self.assertEqual(p1.Allocated_Qty.sum(), 10)
        self.assertGreater(p1.Backlog.sum(), 0)

    def test_priority_ordering(self):
        result = run_allocation(self.snapshot)
        p1 = result[(result.Scenario == "Baseline") & (result.Plant_ID == "P1")]
        self.assertEqual(list(p1.sort_values("Allocation_Order")["Product Card Id"]), [10, 20, 30])

    def test_same_priority_uses_net_demand_then_product_id(self):
        snapshot = self.snapshot.iloc[[1, 2]].copy()
        snapshot.loc[:, "Planning_Priority"] = 2
        snapshot.loc[:, "Scenario_Demand"] = [5, 5]
        result = run_allocation(snapshot)
        self.assertEqual(list(result.sort_values("Allocation_Order")["Product Card Id"]), [20, 30])

    def test_capacity_cannot_be_over_allocated(self):
        result = run_allocation(self.snapshot)
        validate_allocation_results(result, self.snapshot)
        group = result[(result.Scenario == "Baseline") & (result.Plant_ID == "P1")]
        self.assertLessEqual(group.Allocated_Qty.sum(), 10)

    def test_backlog_equals_unmet_net_demand(self):
        result = run_allocation(self.snapshot)
        self.assertTrue(((result.Allocated_Qty + result.Backlog - result.Net_Demand).abs() < 1e-9).all())

    def test_zero_capacity(self):
        snapshot = self.snapshot.copy()
        snapshot["Scenario_Capacity"] = 0
        result = run_allocation(snapshot)
        self.assertEqual(result.Allocated_Qty.sum(), 0)
        self.assertEqual(result.Backlog.sum(), result.Net_Demand.sum())

    def test_zero_demand(self):
        snapshot = self.snapshot.copy()
        snapshot["Scenario_Demand"] = 0
        result = run_allocation(snapshot)
        self.assertEqual(result.Net_Demand.sum(), 0)
        self.assertEqual(result.Allocated_Qty.sum(), 0)

    def test_invalid_input_schema_fails(self):
        with self.assertRaises(AllocationValidationError):
            run_allocation(self.snapshot.drop(columns=["Scenario_Capacity"]))

    def test_invalid_plant_product_relationship_fails(self):
        snapshot = self.snapshot.copy()
        snapshot.loc[snapshot["Product Card Id"] == 10, "Plant_ID"] = "P2"
        with self.assertRaises(AllocationValidationError):
            run_allocation(snapshot)

    def test_inconsistent_group_capacity_fails(self):
        snapshot = self.snapshot.copy()
        snapshot.loc[(snapshot.Plant_ID == "P1") & (snapshot.Scenario == "Baseline") & (snapshot["Product Card Id"] == 20), "Scenario_Capacity"] = 9
        with self.assertRaises(AllocationValidationError):
            run_allocation(snapshot)

    def test_baseline_and_scenario_use_same_engine(self):
        result = run_allocation(self.snapshot)
        baseline = result[result.Scenario == "Baseline"]
        surge = result[result.Scenario == "Demand_Surge_10pct"]
        self.assertEqual(set(baseline["Planning_Key"]), set(surge["Planning_Key"]))
        self.assertTrue((surge["Scenario_Capacity"] == baseline["Scenario_Capacity"].to_numpy()).all())

    def test_sparse_input_rows_are_preserved(self):
        result = run_allocation(self.snapshot)
        self.assertEqual(len(result), len(self.snapshot))
        self.assertEqual(set(result["Planning_Key"]), set(self.snapshot["Planning_Key"]))

    def test_deterministic_repeated_execution(self):
        first = run_allocation(self.snapshot).to_csv(index=False, date_format="%Y-%m-%d")
        second = run_allocation(self.snapshot).to_csv(index=False, date_format="%Y-%m-%d")
        self.assertEqual(first, second)

    def test_input_is_not_mutated(self):
        original = self.snapshot.copy(deep=True)
        run_allocation(self.snapshot)
        pd.testing.assert_frame_equal(self.snapshot, original)

    def test_remaining_capacity_reconciles(self):
        result = run_allocation(self.snapshot)
        for _, group in result.groupby(["Scenario", "Plant_ID", "Order_Date"]):
            final = group.sort_values("Allocation_Order").iloc[-1]
            expected = final.Scenario_Capacity - group.Allocated_Qty.sum()
            self.assertAlmostEqual(final.Remaining_Capacity, expected)


if __name__ == "__main__":
    unittest.main()
