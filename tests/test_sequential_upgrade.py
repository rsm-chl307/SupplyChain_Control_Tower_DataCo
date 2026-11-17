"""Hand-calculated multiweek fixtures; no assumed production business defaults."""

import unittest

import pandas as pd

from src.kpi_engine import calculate_sequential_kpis
from src.scenario_generator import generate_sequential_scenarios
from src.sequential_planner import ALLOCATION_POLICY, simulate_sequential
from src.sequential_validator import validate_sequential_results


class SequentialUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.weeks = pd.date_range("2017-01-08", periods=3, freq="W-SUN")
        self.demand = pd.DataFrame([
            ["P1", product, week, float(q), float(q), 0., "OBSERVED_DEMAND" if q else "OBSERVED_ZERO", priority]
            for product, priority, quantities in [(1, 3, [6, 1, 1]), (2, 1, [4, 1, 0])]
            for week, q in zip(self.weeks, quantities)
        ], columns=["Plant_ID", "Product Card Id", "Order_Date", "Gross_Demand", "Qualified_Demand", "Excluded_Demand", "Coverage_Status", "Planning_Priority"])
        self.capacity = pd.DataFrame({"Plant_ID": ["P1"] * 3, "Order_Date": self.weeks, "Baseline_Workload_Capacity": [4., 6., 0.],
                                      "Factor_Version": ["fixture"] * 3, "Workload_Unit": ["EqWU"] * 3})
        self.factors = pd.DataFrame({"Product Card Id": [1, 2], "Workload_Factor": [2., 1.], "Factor_Version": ["fixture"] * 2,
                                     "Provenance_Type": ["SYNTHETIC_TEST"] * 2, "Workload_Unit": ["EqWU"] * 2})
        self.initial = pd.DataFrame({"Plant_ID": ["P1", "P1"], "Product Card Id": [1, 2], "Beginning_Inventory": [1., 0.], "Beginning_Backlog": [0., 0.]})
        self.receipts = pd.DataFrame({"Receipt_ID": ["r1"], "Plant_ID": ["P1"], "Product Card Id": [2],
                                     "Order_Date": [self.weeks[-1]], "External_Receipts_Qty": [2.]})

    def inputs(self, policy="CARRY_FORWARD", four=False):
        kinds = [("Baseline", 1., 1.)]
        if four:
            kinds += [("Demand_Surge", 1.1, 1.), ("Capacity_Disruption", 1., .8), ("Combined_Stress", 1.1, .8)]
        definitions = [
            dict(Scenario=name, Demand_Multiplier=dm, Capacity_Multiplier=cm,
                 Disruption_Plants=["P1"], Disruption_Weeks=None, Backlog_Policy=policy)
            for name, dm, cm in kinds
        ]
        return generate_sequential_scenarios(self.demand, self.capacity, definitions)

    def run_case(self, policy="CARRY_FORWARD", four=False):
        demand, pools = self.inputs(policy, four)
        states, result_pools = simulate_sequential(demand, pools, self.initial, self.receipts, self.factors, quantity_step=0, allocation_policy=ALLOCATION_POLICY)
        report = validate_sequential_results(states, result_pools, demand, pools, self.initial, self.receipts, self.factors, quantity_step=0)
        return states, result_pools, report

    def test_hand_calculated_carry_backlog_and_receipts(self):
        states, pools, report = self.run_case()
        one = states[states["Product Card Id"].eq(1)]
        two = states[states["Product Card Id"].eq(2)]
        self.assertEqual(one.Ending_Backlog.tolist(), [3., 1., 2.])
        self.assertEqual(two.Ending_Backlog.tolist(), [4., 5., 3.])
        self.assertEqual(one.Fulfilled_Backlog_Qty.tolist(), [0., 3., 0.])
        self.assertEqual(one.Fulfilled_Current_Qty.tolist(), [3., 0., 0.])
        self.assertEqual(two.External_Receipts_Qty.tolist(), [0., 0., 2.])
        self.assertEqual(pools.Allocated_Workload.tolist(), [4., 6., 0.])
        self.assertTrue(report.Passed.all())

    def test_lost_sales_never_carries(self):
        states, _, _ = self.run_case("LOST_SALES")
        self.assertTrue(states.Beginning_Backlog.eq(0).all())
        self.assertTrue(states.Ending_Backlog.eq(0).all())
        self.assertGreater(states.Lost_Sales_Qty.sum(), 0)
        self.assertEqual(states.Fulfilled_Backlog_Qty.sum(), 0)

    def test_scenario_state_isolation_and_repeatability(self):
        alone, _, _ = self.run_case()
        together, _, _ = self.run_case(four=True)
        pd.testing.assert_frame_equal(alone.reset_index(drop=True), together[together.Scenario.eq("Baseline")].reset_index(drop=True))
        again, _, _ = self.run_case(four=True)
        pd.testing.assert_frame_equal(together, again)

    def test_inventory_conservation_all_rows(self):
        states, _, _ = self.run_case(four=True)
        supply = states.Beginning_Inventory + states.External_Receipts_Qty + states.Internal_Production_Qty
        served = states.Fulfilled_Current_Qty + states.Fulfilled_Backlog_Qty + states.Ending_Inventory
        self.assertTrue((supply - served).abs().lt(1e-8).all())

    def test_unknown_missing_and_out_of_scope_never_zero_filled(self):
        for status in ["UNKNOWN", "OUT_OF_SCOPE"]:
            demand, pools = self.inputs()
            demand.loc[0, "Coverage_Status"] = status
            with self.assertRaisesRegex(ValueError, "demand cannot"):
                simulate_sequential(demand, pools, self.initial, self.receipts, self.factors, quantity_step=0, allocation_policy=ALLOCATION_POLICY)
        demand, pools = self.inputs()
        with self.assertRaisesRegex(ValueError, "full-horizon"):
            simulate_sequential(demand.iloc[1:], pools, self.initial, self.receipts, self.factors, quantity_step=0, allocation_policy=ALLOCATION_POLICY)

    def test_no_missing_or_duplicate_capacity_pool(self):
        demand, pools = self.inputs()
        for bad in [pools.iloc[1:], pd.concat([pools, pools.iloc[[0]]], ignore_index=True)]:
            with self.assertRaises(ValueError):
                simulate_sequential(demand, bad, self.initial, self.receipts, self.factors, quantity_step=0, allocation_policy=ALLOCATION_POLICY)

    def test_no_early_receipts_and_no_receipt_capacity_consumption(self):
        states, pools, _ = self.run_case()
        two = states[states["Product Card Id"].eq(2)]
        self.assertEqual(two.iloc[0].External_Receipts_Qty, 0)
        self.assertEqual(two.iloc[-1].Fulfilled_Backlog_Qty, 2)
        self.assertEqual(pools.iloc[-1].Allocated_Workload, 0)

    def test_forged_requirement_and_balanced_wrong_cohort_rejected(self):
        demand, pools = self.inputs()
        states, result_pools, _ = self.run_case()
        bad = states.copy()
        bad.loc[0, "Required_Production_Qty"] = 0.
        with self.assertRaisesRegex(ValueError, "REQUIREMENT"):
            validate_sequential_results(bad, result_pools, demand, pools, self.initial, self.receipts, self.factors, quantity_step=0)
        bad = states.copy()
        idx = bad[(bad["Product Card Id"] == 1) & (bad.Order_Date == self.weeks[1])].index[0]
        bad.loc[idx, "Fulfilled_Current_Qty"] = 3.
        bad.loc[idx, "Fulfilled_Backlog_Qty"] = 0.
        with self.assertRaisesRegex(ValueError, "CONSERVATION"):
            validate_sequential_results(bad, result_pools, demand, pools, self.initial, self.receipts, self.factors, quantity_step=0)

    def test_stocks_not_summed_and_horizon_fulfillment_includes_later_backlog_service(self):
        states, pools, _ = self.run_case()
        kpis = calculate_sequential_kpis(states, pools)
        summary = kpis[kpis.Aggregation_Level.eq("Scenario")].iloc[0]
        self.assertEqual(summary.Ending_Backlog, 5)
        self.assertEqual(summary.Scenario_Qualified_Demand, 13)
        self.assertEqual(summary.Demand_Fulfillment_Numerator, 8)
        self.assertAlmostEqual(summary.Demand_Fulfillment_Rate, 8 / 13)
        self.assertEqual(summary.Available_Workload_Capacity, 10)
        self.assertEqual(summary.Capacity_Utilization, 1)

    def test_combined_treatments_preserve_historical_demand(self):
        demand, pools = self.inputs(four=True)
        combined = demand[demand.Scenario.eq("Combined_Stress")]
        self.assertTrue((combined.Scenario_Qualified_Demand == combined.Qualified_Demand * 1.1).all())
        self.assertEqual(combined.Gross_Demand.sum(), 13)
        self.assertEqual(pools[pools.Scenario.eq("Combined_Stress")].Available_Workload_Capacity.sum(), 8.)

    def test_opening_backlog_not_counted_as_horizon_demand_fulfillment(self):
        self.initial.loc[0, "Beginning_Backlog"] = 3.
        states, pools, _ = self.run_case()
        summary = calculate_sequential_kpis(states, pools).query("Aggregation_Level == 'Scenario'").iloc[0]
        self.assertEqual(summary.Fulfilled_Opening_Backlog_Qty, 3)
        self.assertLessEqual(summary.Demand_Fulfillment_Numerator, 13)

    def test_zero_demand_zero_capacity_and_inventory_covered(self):
        self.demand[["Gross_Demand", "Qualified_Demand"]] = 0.
        self.demand["Coverage_Status"] = "OBSERVED_ZERO"
        self.capacity["Baseline_Workload_Capacity"] = 0.
        states, pools, _ = self.run_case()
        self.assertEqual(states.Internal_Production_Qty.sum(), 0)
        kpis = calculate_sequential_kpis(states, pools)
        self.assertTrue(kpis.Demand_Fulfillment_Rate.isna().all())
        self.assertTrue(kpis.Capacity_Utilization.isna().all())
        self.assertTrue(states.Ending_Backlog.eq(0).all())

    def test_machine_roundoff_pool_balance_is_zero_not_negative(self):
        quantities = [270.6, 143.0, 116.4217948717951, 24.2, 53.900000000000006,
                      51.70000000000001, 34.1, 30.55982905982931, 26.400000000000006, 22.857264957265038]
        ids = ["365", "191", "403", "276", "172", "235", "273", "278", "249", "282"]
        priorities = [3, 3, 2, 2, 1, 1, 1, 1, 1, 1]
        factors = [1., 1.5, 1., 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
        self.demand = pd.DataFrame({"Plant_ID": ["P1"] * 10, "Product Card Id": ids, "Order_Date": ["2017-01-08"] * 10,
                                   "Gross_Demand": quantities, "Qualified_Demand": quantities, "Excluded_Demand": [0.] * 10,
                                   "Coverage_Status": ["OBSERVED_DEMAND"] * 10, "Planning_Priority": priorities})
        self.capacity = self.capacity.iloc[[0]].copy()
        self.capacity["Baseline_Workload_Capacity"] = 683.2820512820513
        self.initial = pd.DataFrame({"Plant_ID": ["P1"] * 10, "Product Card Id": ids, "Beginning_Inventory": [0.] * 10, "Beginning_Backlog": [0.] * 10})
        self.factors = pd.DataFrame({"Product Card Id": ids, "Workload_Factor": factors,
                                    "Factor_Version": ["fixture"] * 10, "Workload_Unit": ["EqWU"] * 10, "Provenance_Type": ["SYNTHETIC_TEST"] * 10})
        self.receipts = self.receipts.iloc[:0].copy()
        states, pools, _ = self.run_case()
        self.assertEqual(pools.Remaining_Workload_Capacity.iloc[0], 0)
        kpis = calculate_sequential_kpis(states, pools)
        self.assertTrue(kpis.Remaining_Workload_Capacity.ge(0).all())
        self.assertTrue(kpis.Capacity_Utilization.le(1).all())

    def test_inputs_immutable(self):
        demand, pools = self.inputs()
        frames = [demand, pools, self.initial, self.receipts, self.factors]
        copies = [f.copy(deep=True) for f in frames]
        simulate_sequential(*frames, quantity_step=0, allocation_policy=ALLOCATION_POLICY)
        for frame, old in zip(frames, copies):
            pd.testing.assert_frame_equal(frame, old)


if __name__ == "__main__":
    unittest.main()
