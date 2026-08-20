import unittest

import pandas as pd

from src.performance_manager import PERFORMANCE_COLUMNS, evaluate_allocation


class PerformanceEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        columns = [
            "Plant_ID", "Product Card Id", "Product Name", "Order_Date", "Weekly_Demand",
            "Beginning_Inventory", "Weekly_Capacity", "Baseline_Available_Capacity", "ABC_Class",
            "Planning_Priority", "Planning_Key", "Scenario", "Scenario_Demand", "Scenario_Capacity",
            "Net_Demand", "Allocated_Qty", "Backlog", "Remaining_Capacity", "Allocation_Order",
            "Allocation_Strategy", "Allocation_Reason",
        ]
        rows = []
        scenarios = [
            ("Baseline", 5, 0, 10, 5, 0, 5),
            ("Stress", 15, 0, 10, 10, 5, 0),
            ("Watch", 5, 0, 5, 5, 0, 0),
            ("Zero_Capacity", 5, 0, 0, 0, 5, 0),
            ("Zero_Demand", 0, 0, 10, 0, 0, 10),
        ]
        for scenario, demand, inventory, capacity, allocated, backlog, remaining in scenarios:
            rows.append(["P1", 1, "Product 1", "2017-01-01", demand, inventory, capacity, 1, "A", 3, f"P1|1|2017-01-01", scenario, demand, capacity, max(demand - inventory, 0), allocated, backlog, remaining, 1, "Priority First", "Demand Fully Satisfied" if allocated else ("Capacity Exhausted" if backlog else "No Production Required")])
        # Inventory-covered and zero-demand observations share the Baseline group.
        rows.extend([
            ["P1", 2, "Product 2", "2017-01-01", 5, 10, 10, 1, "B", 2, "P1|2|2017-01-01", "Baseline", 5, 10, 0, 0, 0, 5, 2, "Priority First", "No Production Required"],
            ["P1", 3, "Product 3", "2017-01-01", 0, 0, 10, 1, "C", 1, "P1|3|2017-01-01", "Baseline", 0, 10, 0, 0, 0, 5, 3, "Priority First", "No Production Required"],
        ])
        cls.allocation = pd.DataFrame(rows, columns=columns)
        cls.allocation["Order_Date"] = pd.to_datetime(cls.allocation["Order_Date"])

    def test_fully_satisfied_demand(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Baseline")].iloc[0]
        self.assertEqual(row.Service_Level, 1.0)

    def test_partial_allocation_and_backlog(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Stress")].iloc[0]
        self.assertAlmostEqual(row.Service_Level, 10 / 15)
        self.assertEqual(row.Total_Backlog, 5)

    def test_zero_demand_policy(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Zero_Demand")].iloc[0]
        self.assertEqual(row.Allocation_Rate, 1.0)

    def test_zero_capacity_policy(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Zero_Capacity")].iloc[0]
        self.assertEqual(row.Capacity_Utilization, 0.0)

    def test_inventory_covered_demand_is_excluded_from_net_requirement(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario × Plant") & (result.Scenario == "Baseline")].iloc[0]
        self.assertEqual(row.Total_Net_Demand, 5)

    def test_service_level_is_bounded_and_full_case_is_one(self):
        result = evaluate_allocation(self.allocation)
        self.assertTrue(result.Service_Level.between(0, 1).all())

    def test_partial_service_level(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Stress")].iloc[0]
        self.assertLess(row.Service_Level, 1)

    def test_capacity_utilization_uses_ratio_of_sums(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Baseline")].iloc[0]
        self.assertAlmostEqual(row.Capacity_Utilization, 5 / 10)

    def test_scenario_comparison_against_baseline(self):
        result = evaluate_allocation(self.allocation)
        row = result[(result.Aggregation_Level == "Scenario") & (result.Scenario == "Stress")].iloc[0]
        self.assertAlmostEqual(row.Service_Level_Change, 10 / 15 - 1)
        self.assertEqual(row.Backlog_Change, 5)

    def test_status_healthy_watch_and_at_risk(self):
        result = evaluate_allocation(self.allocation)
        statuses = result[result.Aggregation_Level == "Scenario"].set_index("Scenario").Performance_Status
        self.assertEqual(statuses["Baseline"], "Healthy")
        self.assertEqual(statuses["Watch"], "Watch")
        self.assertEqual(statuses["Stress"], "At Risk")

    def test_zero_denominators_do_not_create_nan(self):
        result = evaluate_allocation(self.allocation)
        metrics = ["Service_Level", "Capacity_Utilization", "Allocation_Rate"]
        self.assertFalse(result[metrics].isna().any().any())

    def test_invalid_stage4_input_fails(self):
        with self.assertRaises(ValueError):
            evaluate_allocation(self.allocation.drop(columns=["Backlog"]))

    def test_aggregation_levels_are_exact(self):
        result = evaluate_allocation(self.allocation)
        self.assertEqual(set(result.Aggregation_Level), {"Scenario", "Scenario × Plant", "Scenario × Week"})

    def test_repeated_execution_is_deterministic(self):
        first = evaluate_allocation(self.allocation).to_csv(index=False, date_format="%Y-%m-%d")
        second = evaluate_allocation(self.allocation).to_csv(index=False, date_format="%Y-%m-%d")
        self.assertEqual(first, second)

    def test_stage4_input_is_preserved(self):
        original = self.allocation.copy(deep=True)
        evaluate_allocation(self.allocation)
        pd.testing.assert_frame_equal(self.allocation, original)

    def test_consolidated_schema(self):
        result = evaluate_allocation(self.allocation)
        self.assertEqual(list(result.columns), PERFORMANCE_COLUMNS)


if __name__ == "__main__":
    unittest.main()
