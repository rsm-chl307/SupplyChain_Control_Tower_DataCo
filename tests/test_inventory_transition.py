"""Hand-calculated state transitions, independent of allocation and I/O."""

import unittest

from src.inventory_engine import transition_inventory


class InventoryTransitionTests(unittest.TestCase):
    def transition(self, **overrides):
        params = dict(beginning_inventory=2.0, beginning_backlog=5.0, current_demand=7.0,
                      external_receipts=3.0, internal_production=4.0,
                      backlog_policy="CARRY_FORWARD", opening_origin_backlog=3.0)
        params.update(overrides)
        return transition_inventory(**params)

    def test_backlog_before_current_and_opening_origin(self):
        result = self.transition()
        self.assertEqual(result["Fulfilled_Backlog_Qty"], 5)
        self.assertEqual(result["Fulfilled_Current_Qty"], 4)
        self.assertEqual(result["Ending_Backlog"], 3)
        self.assertEqual(result["Fulfilled_Opening_Backlog_Qty"], 3)
        self.assertEqual(result["Fulfilled_Horizon_Backlog_Qty"], 2)
        self.assertEqual(result["Ending_Opening_Backlog"], 0)

    def test_same_week_production_and_stock_conservation(self):
        result = self.transition()
        self.assertEqual(2 + 3 + 4, result["Fulfilled_Current_Qty"] + result["Fulfilled_Backlog_Qty"] + result["Ending_Inventory"])
        self.assertEqual(5 + 7, result["Fulfilled_Current_Qty"] + result["Fulfilled_Backlog_Qty"] + result["Ending_Backlog"])

    def test_lost_sales_not_backlog(self):
        result = self.transition(beginning_backlog=0, opening_origin_backlog=0, beginning_inventory=0, external_receipts=0, internal_production=2, backlog_policy="LOST_SALES")
        self.assertEqual(result["Fulfilled_Current_Qty"], 2)
        self.assertEqual(result["Lost_Sales_Qty"], 5)
        self.assertEqual(result["Ending_Backlog"], 0)

    def test_inventory_surplus_and_zero_demand(self):
        result = self.transition(beginning_backlog=0, opening_origin_backlog=0, current_demand=0)
        self.assertEqual(result["Ending_Inventory"], 9)
        self.assertEqual(result["Lost_Sales_Qty"], 0)

    def test_zero_supply_and_following_week_recovery(self):
        first = self.transition(beginning_inventory=0, external_receipts=0, internal_production=0)
        self.assertEqual(first["Ending_Backlog"], 12)
        second = self.transition(beginning_inventory=first["Ending_Inventory"], beginning_backlog=first["Ending_Backlog"],
                                 opening_origin_backlog=first["Ending_Opening_Backlog"], external_receipts=15, internal_production=0, current_demand=2)
        self.assertEqual(second["Fulfilled_Backlog_Qty"], 12)
        self.assertEqual(second["Fulfilled_Current_Qty"], 2)
        self.assertEqual(second["Ending_Inventory"], 1)

    def test_invalid_mode_and_incompatible_opening_backlog(self):
        with self.assertRaises(ValueError):
            self.transition(backlog_policy="LOST_SALES")
        with self.assertRaises(ValueError):
            self.transition(backlog_policy="DEFAULT")
        with self.assertRaises(ValueError):
            self.transition(opening_origin_backlog=6)
        with self.assertRaises(ValueError):
            self.transition(internal_production=float("inf"))


if __name__ == "__main__":
    unittest.main()
