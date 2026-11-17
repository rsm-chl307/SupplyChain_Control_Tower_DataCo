"""Focused input and workload tests; fixture assumptions are synthetic."""

import unittest

import pandas as pd

from src.allocation_engine import allocate_workload
from src.demand_preparation import build_demand_coverage, prepare_demand
from src.workload_model import calibrate_workload_capacity


class PlanningInputsUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.mapping = pd.DataFrame({"Product Card Id": [1], "Plant_ID": ["P1"]})
        # Complete explicit coverage dates with a no-order week inside lifespan.
        self.raw = pd.DataFrame({
            "Order Item Id": [1, 2, 3, 4],
            "Product Card Id": [1] * 4,
            "Order Status": ["COMPLETE", "CANCELED", "COMPLETE", "SUSPECTED_FRAUD"],
            "order date (DateOrders)": ["2017-01-02", "2017-01-08", "2017-01-22", "2017-01-22"],
            "Order Item Quantity": [10, 3, 7, 2],
        })
        self.statuses = {"COMPLETE": True, "CANCELED": False, "SUSPECTED_FRAUD": False}
        self.factors = pd.DataFrame({
            "Product Card Id": [1], "Workload_Factor": [2.0],
            "Factor_Version": ["test"], "Provenance_Type": ["SYNTHETIC_TEST"], "Workload_Unit": ["EqWU"],
        })

    def prepare(self, **kwargs):
        return prepare_demand(self.raw, self.mapping, self.statuses, eligibility_version="test", source_is_complete=kwargs.get("complete", True))

    def test_dual_demand_reconciles_with_traceable_exclusions(self):
        ledger, demand = self.prepare()
        self.assertEqual(ledger.Gross_Demand.sum(), 22)
        self.assertEqual(ledger.Qualified_Demand.sum(), 17)
        self.assertTrue((demand.Gross_Demand == demand.Qualified_Demand + demand.Excluded_Demand).all())
        self.assertEqual(set(ledger.loc[~ledger.Is_Qualified, "Exclusion_Reason"]), {"CANCELED", "SUSPECTED_FRAUD"})

    def test_internal_zero_requires_explicit_complete_extract(self):
        _, covered = self.prepare()
        _, sparse = self.prepare(complete=False)
        self.assertEqual(len(covered), 3)
        self.assertEqual(len(sparse), 2)
        self.assertEqual(covered.iloc[1].Coverage_Status, "OBSERVED_ZERO")
        calendar = build_demand_coverage(sparse, self.mapping, "2017-01-08", "2017-01-22")
        self.assertEqual(calendar.iloc[1].Coverage_Status, "UNKNOWN")

    def test_outside_coverage_unknown_and_outside_horizon_labeled(self):
        _, demand = self.prepare()
        result = build_demand_coverage(demand, self.mapping, "2017-01-15", "2017-01-29")
        self.assertEqual(result[result.Order_Date == pd.Timestamp("2017-01-29")].Coverage_Status.iloc[0], "UNKNOWN")
        self.assertEqual(result[result.Order_Date == pd.Timestamp("2017-01-08")].Coverage_Status.iloc[0], "OUT_OF_SCOPE")

    def test_partial_source_week_is_unknown(self):
        self.raw.loc[0, "order date (DateOrders)"] = "2017-01-04"
        _, demand = self.prepare()
        self.assertEqual(demand.iloc[0].Coverage_Status, "UNKNOWN")

    def test_status_ambiguity_does_not_qualify_silently(self):
        self.raw.loc[0, "Order Status"] = "PENDING"
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.prepare()

    def test_forbidden_status_cannot_be_qualified(self):
        self.statuses["CANCELED"] = True
        with self.assertRaisesRegex(ValueError, "must be excluded"):
            self.prepare()

    def test_duplicate_source_and_unmapped_product_rejected(self):
        self.raw.loc[1, "Order Item Id"] = 1
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.prepare()
        self.raw.loc[1, "Order Item Id"] = 2
        self.raw.loc[0, "Product Card Id"] = 999
        with self.assertRaisesRegex(ValueError, "mapping"):
            self.prepare()

    def test_invalid_quantity_and_date_rejected(self):
        self.raw["Order Item Quantity"] = self.raw["Order Item Quantity"].astype(float)
        for value in [-1, float("inf"), float("nan")]:
            raw = self.raw.copy()
            self.raw.loc[0, "Order Item Quantity"] = value
            with self.assertRaises(ValueError):
                self.prepare()
            self.raw = raw
        self.raw.loc[0, "order date (DateOrders)"] = "invalid"
        with self.assertRaises(ValueError):
            self.prepare()

    def test_calibration_uses_workload_not_old_quantity_capacity(self):
        _, demand = self.prepare()
        capacity = calibrate_workload_capacity(
            demand, self.factors, calibration_start="2017-01-08", calibration_end="2017-01-22",
            target_utilization=0.5, capacity_version="test",
        )
        self.assertAlmostEqual(capacity.Baseline_Workload_Capacity.iloc[0], 17 * 2 / 3 / 0.5)
        self.assertEqual(capacity.Provenance_Type.iloc[0], "SYNTHETIC_DEMAND_CALIBRATED")

    def test_calibration_rejects_unknown_and_missing_factor(self):
        _, demand = self.prepare()
        demand.loc[0, "Coverage_Status"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            calibrate_workload_capacity(demand, self.factors, calibration_start="2017-01-08", calibration_end="2017-01-22", target_utilization=0.5, capacity_version="test")

    def requirements(self):
        return pd.DataFrame({"Product Card Id": [1, 2], "Planning_Priority": [3, 2], "Required_Production_Qty": [4.0, 6.0], "Workload_Factor": [2.0, 1.0]})

    def test_shared_workload_pool_and_priority(self):
        result = allocate_workload(self.requirements(), 10, quantity_step=0)
        self.assertEqual(result.Internal_Production_Qty.tolist(), [4, 2])
        self.assertEqual(result.Allocated_Workload.sum(), 10)

    def test_zero_and_inventory_covered_requirement(self):
        source = self.requirements()
        source["Required_Production_Qty"] = 0.0
        self.assertEqual(allocate_workload(source, 10, quantity_step=0).Internal_Production_Qty.sum(), 0)
        self.assertEqual(allocate_workload(self.requirements(), 0, quantity_step=0).Internal_Production_Qty.sum(), 0)

    def test_pack_rounding_is_explicit_and_capacity_safe(self):
        result = allocate_workload(self.requirements(), 5, quantity_step=1)
        self.assertEqual(result.Internal_Production_Qty.tolist(), [2, 1])
        self.assertEqual(result.Allocated_Workload.sum(), 5)

    def test_decimal_factor_does_not_lose_one_pack_to_float_roundoff(self):
        source = self.requirements().iloc[[0]].copy()
        source["Workload_Factor"] = 0.1
        result = allocate_workload(source, 0.3, quantity_step=1)
        self.assertEqual(result.Internal_Production_Qty.iloc[0], 3)
        self.assertLessEqual(result.Allocated_Workload.sum(), 0.3 + 1e-9)

    def test_deterministic_and_immutable(self):
        source = self.requirements()
        old = source.copy(deep=True)
        a = allocate_workload(source, 10, quantity_step=0)
        b = allocate_workload(source.sample(frac=1, random_state=2), 10, quantity_step=0)
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_frame_equal(source, old)


if __name__ == "__main__":
    unittest.main()
