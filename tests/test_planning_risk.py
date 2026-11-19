"""Focused tests for risk summaries built from published sequential artifacts."""

import unittest
import json
import tempfile
from pathlib import Path

import pandas as pd

from src.planning_risk import (
    filter_investigation_evidence,
    investigation_evidence_csv,
    investigation_views,
    plant_bottleneck_summary,
    product_risk_ranking,
    risk_driver_details,
    scenario_plant_deterioration,
    scenario_product_deterioration,
    scenario_risk_comparison,
)
from src.run_planning import run_csv_planning


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "planning"


WEEKS = pd.to_datetime(["2026-01-04", "2026-01-11"])


def allocation_fixture() -> pd.DataFrame:
    rows = [
        # Plant 1, product A: one unit misses its demand week but is later served.
        ("P1", "SKU-A", 0, 3, 4, 4, 2, 3, 0, 1, 3, 0, 0, 2, 1, 1),
        ("P1", "SKU-A", 1, 3, 4, 5, 4, 4, 1, 0, 2, 0, 0, 0, 1, 1),
        # Plant 2, product A: final plant states are summed, weekly states are not.
        ("P2", "SKU-A", 0, 3, 1, 1, 0, 1, 0, 0, 5, 0, 0, 0, 0, 1),
        ("P2", "SKU-A", 1, 3, 1, 1, 1, 1, 0, 0, 7, 0, 0, 0, 0, 1),
        # Product B has same-week misses and lost sales.
        ("P1", "001", 0, 1, 3, 3, 2, 2, 0, 1, 6, 0, 0, 0, 0, 2),
        ("P1", "001", 1, 1, 2, 2, 1, 1, 0, 1, 4, 0, 1, 0, 0, 2),
    ]
    baseline = pd.DataFrame([
        {"Scenario": "Baseline", "Plant_ID": plant, "Product Card Id": product,
         "Product Name": "Widget A" if product == "SKU-A" else "Widget B", "Order_Date": WEEKS[week_index],
         "Planning_Priority": priority, "Scenario_Qualified_Demand": demand,
         "Required_Production_Qty": required, "Internal_Production_Qty": production,
         "Unmet_Production_Qty": max(required - production, 0),
         "Fulfilled_Current_Qty": current_fulfilled, "Fulfilled_Horizon_Backlog_Qty": horizon_backlog,
         "Current_Unfulfilled_Qty": unfulfilled, "Ending_Inventory": ending_inventory,
         "Ending_Backlog": ending_backlog, "Lost_Sales_Qty": lost,
         "Allocated_Workload": production * factor, "Unmet_Workload": unmet_workload,
         "Workload_Factor": factor, "Workload_Unit": "EqWU",
         "Beginning_Inventory": beginning_inventory, "Beginning_Backlog": 0,
         "Allocation_Order": 1 if product == "SKU-A" else 2, "Incremental_Demand": 0,
         "Backlog_Policy": "CARRY_FORWARD"}
        for plant, product, week_index, priority, demand, required, production, current_fulfilled,
            horizon_backlog, unfulfilled, ending_inventory, ending_backlog, lost, unmet_workload,
            beginning_inventory, factor in rows
    ])
    stress = baseline.copy()
    stress["Scenario"] = "Combined_Stress"
    stress["Scenario_Qualified_Demand"] += 1
    stress["Incremental_Demand"] = 1
    stress["Current_Unfulfilled_Qty"] += 1
    stress["Ending_Backlog"] += 1
    stress["Lost_Sales_Qty"] += 1
    return pd.concat([baseline, stress], ignore_index=True)


def pools_fixture() -> pd.DataFrame:
    return pd.DataFrame([
        {"Scenario": scenario, "Plant_ID": plant, "Order_Date": week,
         "Baseline_Workload_Capacity": cap, "Available_Workload_Capacity": cap,
         "Allocated_Workload": used, "Remaining_Workload_Capacity": cap - used,
         "Unmet_Workload": unmet, "Workload_Shortage": unmet > 0}
        for scenario in ["Baseline", "Combined_Stress"]
        for plant, weeks in {
            "P1": [(WEEKS[0], 10., 6., 2.), (WEEKS[1], 30., 9., 0.)],
            "P2": [(WEEKS[0], 0., 0., 2.), (WEEKS[1], 5., 2., 0.)],
        }.items()
        for week, cap, used, unmet in weeks
    ])


def performance_fixture() -> pd.DataFrame:
    rows = []
    for scenario, demand_rate, coverage, backlog, lost, utilization in [
        ("Baseline", .9, .7, 2., 0., .6),
        ("Combined_Stress", .7, .5, 6., 2., .9),
    ]:
        rows.append({"Aggregation_Level": "Scenario", "Scenario": scenario, "Plant_ID": None,
                     "Scenario_Qualified_Demand": 20., "Demand_Fulfillment_Rate": demand_rate,
                     "Production_Coverage_Rate": coverage, "Ending_Backlog": backlog,
                     "Lost_Sales_Qty": lost, "Capacity_Utilization": utilization,
                     "Bottleneck_Plant_Weeks": 1 if scenario == "Baseline" else 2,
                     "Backlog_Policy": "CARRY_FORWARD"})
        for plant, offset in [("P1", 0.), ("P2", .1)]:
            rows.append({"Aggregation_Level": "Scenario × Plant", "Scenario": scenario, "Plant_ID": plant,
                         "Scenario_Qualified_Demand": 10., "Demand_Fulfillment_Rate": demand_rate - offset,
                         "Production_Coverage_Rate": coverage - offset, "Ending_Backlog": backlog + offset,
                         "Lost_Sales_Qty": lost + offset, "Capacity_Utilization": utilization - offset,
                         "Bottleneck_Plant_Weeks": 1 if scenario == "Baseline" else 2,
                         "Backlog_Policy": "CARRY_FORWARD"})
    return pd.DataFrame(rows)


class PlanningRiskTests(unittest.TestCase):
    def test_risk_views_accept_both_published_data_modes(self):
        """Exercise risk summaries against actual outputs from both input modes."""
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "runs"
            for mode in ["synthetic_demo", "user_data"]:
                inputs = EXAMPLES / mode
                config = json.loads((inputs / "config.json").read_text())
                outputs = run_csv_planning(config, inputs_dir=inputs, output_root=output_root)
                allocation = pd.read_csv(outputs["allocation_result"])
                pools = pd.read_csv(outputs["capacity_pools"])
                performance = pd.read_csv(outputs["performance_result"])

                products = product_risk_ranking(allocation)
                plants = plant_bottleneck_summary(pools)
                drivers = risk_driver_details(allocation, pools)
                scenarios = scenario_risk_comparison(performance)

                self.assertFalse(products.empty, mode)
                self.assertFalse(plants.empty, mode)
                self.assertEqual(len(drivers), len(allocation), mode)
                self.assertEqual(set(scenarios.Scenario), {"Baseline", "Demand_Surge", "Capacity_Disruption", "Combined_Stress"})

    def test_product_risk_uses_rates_and_terminal_state_at_correct_grain(self):
        result = product_risk_ranking(allocation_fixture())
        baseline = result[result.Scenario.eq("Baseline")].set_index("Product Card Id")
        product_a = baseline.loc["SKU-A"]
        self.assertAlmostEqual(product_a.Demand_Fulfillment_Rate, 1.0)
        self.assertAlmostEqual(product_a.Production_Coverage_Rate, 7 / 11)
        self.assertEqual(product_a.Current_Demand_Unfulfilled_Qty, 1)
        self.assertEqual(product_a.Opening_Inventory_Qty, 1)
        self.assertEqual(product_a.Ending_Inventory, 9)  # P1 final 2 + P2 final 7, not all weeks.
        self.assertEqual(product_a.Risk_Category, "At Risk")
        self.assertIn("not fulfilled in their demand week", product_a.Risk_Reason)
        product_b = baseline.loc["001"]
        self.assertAlmostEqual(product_b.Demand_Fulfillment_Rate, 3 / 5)
        self.assertAlmostEqual(product_b.Production_Coverage_Rate, 3 / 5)
        self.assertEqual(product_b.Ending_Backlog, 0)
        self.assertEqual(product_b.Lost_Sales_Qty, 1)

    def test_full_utilization_is_distinct_from_capacity_shortage_and_aggregates_once(self):
        pools = pd.DataFrame([
            {"Scenario": scenario, "Plant_ID": "P1", "Order_Date": week,
             "Available_Workload_Capacity": 10., "Allocated_Workload": allocated,
             "Remaining_Workload_Capacity": 10. - allocated, "Unmet_Workload": unmet}
            for scenario, weeks in {
                "Baseline": [(WEEKS[0], 10., 4.), (WEEKS[1], 6., 0.)],
                "Healthy": [(WEEKS[0], 10., 0.), (WEEKS[1], 8., 0.)],
            }.items()
            for week, allocated, unmet in weeks
        ])
        summary = plant_bottleneck_summary(pools).set_index(["Scenario", "Plant_ID"])
        baseline = summary.loc[("Baseline", "P1")]
        self.assertEqual(baseline.Available_Workload_Capacity, 20.)
        self.assertEqual(baseline.Allocated_Workload, 16.)
        self.assertEqual(baseline.Remaining_Workload_Capacity, 4.)
        self.assertAlmostEqual(baseline.Capacity_Utilization, .8)
        self.assertEqual(baseline.Bottleneck_Weeks, 1)
        healthy = summary.loc[("Healthy", "P1")]
        self.assertAlmostEqual(healthy.Capacity_Utilization, .9)
        self.assertEqual(healthy.Bottleneck_Weeks, 0)
        fully_used_week = pools.loc[pools.Scenario.eq("Healthy") & pools.Order_Date.eq(WEEKS[0])].iloc[0]
        self.assertEqual(fully_used_week.Available_Workload_Capacity, 10.)
        self.assertEqual(fully_used_week.Remaining_Workload_Capacity, 0.)

        # The pool fixture has one row per plant-week, not one row per product.
        self.assertEqual(len(pools.loc[pools.Scenario.eq("Healthy")]), 2)
        self.assertEqual(healthy.Available_Workload_Capacity, 20.)

    def test_healthy_product_at_full_utilization_has_no_shortage_risk(self):
        row = allocation_fixture().iloc[[0]].copy()
        row["Scenario"] = "Healthy"
        row["Scenario_Qualified_Demand"] = 3
        row["Required_Production_Qty"] = 3
        row["Internal_Production_Qty"] = 3
        row["Fulfilled_Current_Qty"] = 3
        row["Fulfilled_Horizon_Backlog_Qty"] = 0
        row["Current_Unfulfilled_Qty"] = 0
        row["Ending_Inventory"] = 1
        row["Ending_Backlog"] = 0
        row["Lost_Sales_Qty"] = 0
        row["Allocated_Workload"] = 3
        row["Unmet_Workload"] = 0
        product = product_risk_ranking(row).iloc[0]
        self.assertEqual(product.Risk_Category, "Healthy")
        self.assertEqual(product.Ending_Backlog, 0)
        self.assertEqual(product.Demand_Fulfillment_Rate, 1)

        pool = pd.DataFrame([{
            "Scenario": "Healthy", "Plant_ID": "P1", "Order_Date": WEEKS[0],
            "Available_Workload_Capacity": 3., "Allocated_Workload": 3.,
            "Remaining_Workload_Capacity": 0., "Unmet_Workload": 0.,
        }])
        plant = plant_bottleneck_summary(pool).iloc[0]
        self.assertEqual(plant.Capacity_Utilization, 1)
        self.assertEqual(plant.Bottleneck_Weeks, 0)

    def test_significant_unmet_demand_and_horizon_backlog_are_visible(self):
        result = product_risk_ranking(allocation_fixture())
        product = result.loc[
            result.Scenario.eq("Combined_Stress") & result["Product Card Id"].eq("SKU-A")
        ].iloc[0]
        self.assertEqual(product.Current_Demand_Unfulfilled_Qty, 5)
        self.assertEqual(product.Ending_Backlog, 2)
        self.assertEqual(product.Risk_Category, "At Risk")
        self.assertIn("backlog remain at horizon end", product.Risk_Reason)

    def test_plant_capacity_uses_unique_plant_week_pools_and_weighted_utilization(self):
        result = plant_bottleneck_summary(pools_fixture())
        p1 = result[(result.Scenario == "Baseline") & result.Plant_ID.eq("P1")].iloc[0]
        self.assertAlmostEqual(p1.Capacity_Utilization, 15 / 40)
        self.assertEqual(p1.Bottleneck_Weeks, 1)
        p2 = result[(result.Scenario == "Baseline") & result.Plant_ID.eq("P2")].iloc[0]
        self.assertAlmostEqual(p2.Capacity_Utilization, .4)
        self.assertEqual(p2.Bottleneck_Weeks, 1)
        weekly = pools_fixture()
        p2_zero_capacity_week = weekly[(weekly.Scenario == "Baseline") & weekly.Plant_ID.eq("P2")
                                       & weekly.Order_Date.eq(WEEKS[0])]
        self.assertEqual(p2_zero_capacity_week.Available_Workload_Capacity.iloc[0], 0)

    def test_duplicate_plant_week_pool_is_rejected_to_prevent_capacity_double_count(self):
        pools = pools_fixture()
        with self.assertRaisesRegex(ValueError, "one row per Scenario"):
            plant_bottleneck_summary(pd.concat([pools, pools.iloc[[0]]], ignore_index=True))

    def test_missing_numeric_values_are_not_silently_summed_as_zero(self):
        allocation = allocation_fixture()
        allocation.loc[0, "Scenario_Qualified_Demand"] = float("nan")
        with self.assertRaisesRegex(ValueError, "missing or non-finite values in Scenario_Qualified_Demand"):
            product_risk_ranking(allocation)

        pools = pools_fixture()
        pools.loc[0, "Available_Workload_Capacity"] = float("nan")
        with self.assertRaisesRegex(ValueError, "missing or non-finite values in Available_Workload_Capacity"):
            plant_bottleneck_summary(pools)

    def test_unmatched_capacity_pool_is_reported_as_unavailable(self):
        allocation = allocation_fixture()
        pools = pools_fixture()
        row = allocation.iloc[0]
        pools = pools.loc[~(
            pools.Scenario.eq(row.Scenario) & pools.Plant_ID.eq(row.Plant_ID)
            & pools.Order_Date.eq(row.Order_Date)
        )]
        details = risk_driver_details(allocation, pools)
        matching = details.loc[
            details.Scenario.eq(row.Scenario) & details.Plant_ID.eq(row.Plant_ID)
            & details["Product Card Id"].eq(row["Product Card Id"])
            & details.Order_Date.eq(row.Order_Date)
        ].iloc[0]
        self.assertTrue(pd.isna(matching.Capacity_Shortage))
        self.assertIn("capacity pool is unavailable", matching.Risk_Signals)

    def test_missing_optional_shortage_flag_is_derived_from_unmet_workload(self):
        pools = pools_fixture()
        pools["Workload_Shortage"] = pools.Workload_Shortage.astype(object)
        pools.loc[0, "Workload_Shortage"] = float("nan")
        summary = plant_bottleneck_summary(pools)
        plant = summary.loc[summary.Scenario.eq("Baseline") & summary.Plant_ID.eq("P1")].iloc[0]
        self.assertEqual(plant.Bottleneck_Weeks, 1)

    def test_risk_drivers_join_product_rows_to_shared_capacity_and_scenario_signals(self):
        allocation = allocation_fixture()
        pools = pools_fixture()
        details = risk_driver_details(allocation, pools)
        self.assertEqual(len(details), len(allocation))
        stress = details[(details.Scenario == "Combined_Stress") & details.Plant_ID.eq("P1")].iloc[0]
        self.assertEqual(stress.Plant_Week_Allocated_Workload, 6)
        self.assertEqual(stress.Incremental_Demand, 1)
        self.assertTrue(stress.Capacity_Shortage)
        self.assertIn("Scenario demand exceeds baseline", stress.Risk_Signals)
        self.assertIn("allocation order", stress.Risk_Signals)
        shared_pool_rows = details[
            details.Scenario.eq("Baseline") & details.Plant_ID.eq("P1")
            & details.Order_Date.eq(WEEKS[0])
        ]
        self.assertEqual(shared_pool_rows["Product Card Id"].nunique(), 2)
        self.assertEqual(shared_pool_rows.Plant_Week_Allocated_Workload.nunique(), 1)

    def test_scenario_summaries_reuse_existing_kpis_and_show_product_and_plant_deltas(self):
        performance = performance_fixture()
        summary = scenario_risk_comparison(performance)
        self.assertEqual(summary.Scenario.tolist(), ["Baseline", "Combined_Stress"])
        stress_kpis = summary.set_index("Scenario").loc["Combined_Stress"]
        self.assertAlmostEqual(stress_kpis.Demand_Fulfillment_Rate_Change, -.2)
        self.assertAlmostEqual(stress_kpis.Production_Coverage_Rate_Change, -.2)
        self.assertEqual(stress_kpis.Bottleneck_Plant_Weeks_Change, 1)
        changes = scenario_product_deterioration(product_risk_ranking(allocation_fixture()), "Combined_Stress")
        self.assertTrue((changes.Demand_Fulfillment_Change < 0).all())
        product_a = changes.set_index("Product Card Id").loc["SKU-A"]
        self.assertEqual(product_a.Ending_Backlog_Change, 2)
        self.assertEqual(product_a.Lost_Sales_Change, 4)
        self.assertNotEqual(product_a.Ending_Backlog_Change, product_a.Lost_Sales_Change)
        plant_changes = scenario_plant_deterioration(performance, "Combined_Stress")
        self.assertTrue((plant_changes.Demand_Fulfillment_Rate_Change < 0).all())
        self.assertTrue((plant_changes.Bottleneck_Plant_Weeks_Change == 1).all())
        self.assertTrue(scenario_product_deterioration(product_risk_ranking(allocation_fixture()), "Baseline").empty)

    def test_missing_metrics_fail_with_a_direct_message(self):
        with self.assertRaisesRegex(ValueError, "missing required risk fields: Workload_Factor"):
            product_risk_ranking(allocation_fixture().drop(columns="Workload_Factor"))
        with self.assertRaisesRegex(ValueError, "missing required risk fields: Production_Coverage_Rate"):
            scenario_risk_comparison(performance_fixture().drop(columns="Production_Coverage_Rate"))

    def test_optional_bottleneck_metric_can_be_absent_from_plant_comparison(self):
        performance = performance_fixture().drop(columns="Bottleneck_Plant_Weeks")
        changes = scenario_plant_deterioration(performance, "Combined_Stress")
        self.assertFalse(changes.empty)
        self.assertNotIn("Bottleneck_Plant_Weeks_Change", changes.columns)
        self.assertTrue((changes.Demand_Fulfillment_Rate_Change < 0).all())


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.allocation = allocation_fixture().assign(Run_ID="run-1", Schema_Version="sequential_v1")
        self.pools = pools_fixture().assign(Run_ID="run-1", Schema_Version="sequential_v1")
        self.selection = dict(run_id="run-1", scenario="Baseline", plant_id="P1", product_id="SKU-A", week=WEEKS[0])

    def test_selection_isolates_full_key_and_reconciles_peer_pool(self):
        # Unrelated run values must not leak into Phase 2's pool join.
        other = self.allocation.assign(Run_ID="run-2", Internal_Production_Qty=999)
        other_pools = self.pools.assign(Run_ID="run-2", Allocated_Workload=999)
        for scenario in ["Baseline", "Combined_Stress"]:
            selection = dict(self.selection, scenario=scenario)
            result = investigation_views(pd.concat([self.allocation, other]),
                                         pd.concat([self.pools, other_pools]), **selection)
            row = result["selected_week"].iloc[0]
            self.assertEqual(len(result["selected_week"]), 1)
            self.assertEqual((row.Run_ID, row.Scenario, row.Plant_ID, row["Product Card Id"], row.Order_Date),
                             ("run-1", scenario, "P1", "SKU-A", WEEKS[0]))
            self.assertEqual(len(result["shared_capacity"]), 1)
            peers = result["allocation_peers"]
            self.assertEqual(peers["Product Card Id"].tolist(), ["SKU-A", "001"])
            self.assertEqual(peers.Allocation_Order.tolist(), [1, 2])
            self.assertEqual(peers.Allocated_Workload.sum(), result["shared_capacity"].Allocated_Workload.iloc[0])
            self.assertEqual(peers.Unmet_Workload.sum(), result["shared_capacity"].Unmet_Workload.iloc[0])
            self.assertEqual(result["observed_signals"].Run_ID.iloc[0], "run-1")

    def test_trajectory_preserves_inventory_backlog_and_input_frames(self):
        before = self.allocation.copy(deep=True)
        pools_before = self.pools.copy(deep=True)
        result = investigation_views(self.allocation, self.pools, **self.selection)
        expected = self.allocation.loc[self.allocation.Scenario.eq("Baseline") & self.allocation.Plant_ID.eq("P1")
                                       & self.allocation["Product Card Id"].eq("SKU-A")].reset_index(drop=True)
        pd.testing.assert_frame_equal(result["adjacent_weeks"].reset_index(drop=True), expected)
        again = investigation_views(self.allocation.sample(frac=1, random_state=7), self.pools, **self.selection)
        for name in result:
            pd.testing.assert_frame_equal(result[name].reset_index(drop=True), again[name].reset_index(drop=True))
        pd.testing.assert_frame_equal(self.allocation, before)
        pd.testing.assert_frame_equal(self.pools, pools_before)

    def test_missing_duplicate_and_wrong_week_are_explicit(self):
        for changes in [{"run_id": "missing"}, {"product_id": "missing"}, {"plant_id": "P2", "product_id": "001"},
                        {"week": "2030-01-06"}]:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                investigation_views(self.allocation, self.pools, **dict(self.selection, **changes))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            investigation_views(pd.concat([self.allocation, self.allocation.iloc[[0]]]), self.pools, **self.selection)
        with self.assertRaisesRegex(ValueError, "pool.*unavailable"):
            investigation_views(self.allocation, self.pools.iloc[1:], **self.selection)

    def test_evidence_retains_multiple_source_rows_without_inflating_outcomes_and_exports_context(self):
        import io

        evidence = pd.DataFrame({"Run_ID": ["run-1"] * 3 + ["run-2"], "Schema_Version": ["sequential_v1"] * 4,
                                 "Plant_ID": ["P1"] * 4, "Product Card Id": ["SKU-A"] * 4,
                                 "Order_Date": [WEEKS[0]] * 2 + [WEEKS[1], WEEKS[0]],
                                 "Receipt_ID": ["001", "NA", "later", "other"], "External_Receipts_Qty": [2, 3, 10, 999]})
        selected = filter_investigation_evidence(evidence, **self.selection)
        self.assertEqual(selected.Receipt_ID.tolist(), ["001", "NA"])
        self.assertEqual(selected.External_Receipts_Qty.sum(), 5)
        view = investigation_views(self.allocation, self.pools, **self.selection)
        self.assertEqual(len(view["selected_week"]), 1)
        key = dict(zip(["Run_ID", "Scenario", "Plant_ID", "Product Card Id", "Order_Date"],
                       ["run-1", "Baseline", "P1", "SKU-A", WEEKS[0]]))
        export = pd.read_csv(io.StringIO(investigation_evidence_csv(selected, key, "external_receipts")),
                             dtype=str, keep_default_na=False)
        self.assertEqual(export.Receipt_ID.tolist(), ["001", "NA"])
        self.assertEqual(export.Investigation_Order_Date.tolist(), ["2026-01-04"] * 2)
        self.assertEqual(export.Investigation_Scenario.tolist(), ["Baseline"] * 2)
        self.assertNotIn("Scenario", selected)  # Context must not fabricate a native scenario.
        empty = selected.iloc[:0]
        self.assertTrue(filter_investigation_evidence(empty, **self.selection).empty)
        self.assertIn("Investigation_Run_ID", investigation_evidence_csv(empty, key, "external_receipts"))

    def test_zero_capacity_zero_demand_inventory_receipts_and_backlog_observations(self):
        for demand, capacity, inventory, receipts, backlog, policy in [
            (4, 0, 0, 0, 0, "CARRY_FORWARD"), (0, 0, 0, 0, 0, "CARRY_FORWARD"),
            (4, 0, 4, 0, 0, "CARRY_FORWARD"), (4, 0, 0, 4, 0, "CARRY_FORWARD"),
            (4, 0, 0, 0, 2, "CARRY_FORWARD"), (4, 0, 0, 0, 0, "LOST_SALES"),
        ]:
            from src.inventory_engine import transition_inventory

            row = self.allocation.iloc[[0]].copy()
            row["Scenario_Qualified_Demand"] = demand
            row["Beginning_Inventory"] = inventory
            row["Beginning_Backlog"] = backlog
            row["External_Receipts_Qty"] = receipts
            row["Internal_Production_Qty"] = 0
            row["Required_Production_Qty"] = max(backlog + demand - inventory - receipts, 0)
            row["Allocated_Workload"] = 0
            row["Unmet_Workload"] = row.Required_Production_Qty
            row["Unmet_Production_Qty"] = row.Required_Production_Qty
            row["Backlog_Policy"] = policy
            values = transition_inventory(beginning_inventory=inventory, beginning_backlog=backlog,
                                          current_demand=demand, external_receipts=receipts,
                                          internal_production=0, backlog_policy=policy, opening_origin_backlog=backlog)
            for field, value in values.items():
                row[field] = value
            pool = self.pools.iloc[[0]].copy()
            pool["Available_Workload_Capacity"] = capacity
            pool["Allocated_Workload"] = 0
            pool["Remaining_Workload_Capacity"] = 0
            pool["Unmet_Workload"] = row.Unmet_Workload.iloc[0]
            views = investigation_views(row, pool, **self.selection)
            pd.testing.assert_frame_equal(views["selected_week"], row)
            self.assertEqual(len(views["shared_capacity"]), 1)
            self.assertEqual(views["selected_week"].Current_Unfulfilled_Qty.iloc[0], values["Current_Unfulfilled_Qty"])

    def test_both_published_modes_all_keys_and_kpi_grain(self):
        from dashboard.scenario_planning_app import load_sequential_outputs

        with tempfile.TemporaryDirectory() as temporary:
            for mode in ["synthetic_demo", "user_data"]:
                directory = EXAMPLES / mode
                config = json.loads((directory / "config.json").read_text())
                paths = run_csv_planning(config, inputs_dir=directory, output_root=temporary)
                tables = load_sequential_outputs(paths["run_manifest"].parent, include_evidence=True)
                for scenario in ["Baseline", "Combined_Stress"]:
                    for _, row in tables["allocation"].loc[tables["allocation"].Scenario.eq(scenario)].iterrows():
                        selection = dict(run_id=row.Run_ID, scenario=row.Scenario, plant_id=row.Plant_ID,
                                         product_id=row["Product Card Id"], week=row.Order_Date)
                        views = investigation_views(tables["allocation"], tables["pools"], **selection)
                        peers, pool = views["allocation_peers"], views["shared_capacity"].iloc[0]
                        self.assertAlmostEqual(peers.Allocated_Workload.sum(), pool.Allocated_Workload)
                        self.assertAlmostEqual(peers.Unmet_Workload.sum(), pool.Unmet_Workload)
                        self.assertEqual(len(views["selected_week"]), 1)
                        kpis = filter_investigation_evidence(tables["performance"], **selection)
                        self.assertEqual(len(kpis), 1)
                        self.assertEqual(kpis.Aggregation_Level.iloc[0], "Scenario × Plant × Week")
                        for name in ["eligibility_ledger", "external_receipts", "initial_state", "workload_factors"]:
                            evidence = filter_investigation_evidence(tables[name], **selection)
                            self.assertTrue(evidence.Run_ID.eq(row.Run_ID).all())


if __name__ == "__main__":
    unittest.main()
