"""Offline checks for the shared Count and Generation trial budget."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
import uuid

from tools.windows_api_runner.trial_budget import (
    BudgetReservation, TrialBudgetBlocked, TrialBudgetController,
)


class _Verifier:
    def authenticate(self, password: str) -> bool:
        return password == "owner-test-password"


class TrialBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "budget.sqlite3"
        self.budget = TrialBudgetController.provision(
            self.path, "trial-offline", price_version="synthetic-v1")

    def item(self, *, operation="input_token_count", amount=20_000,
             request_id=None, digest=None):
        return BudgetReservation(
            request_id=request_id or str(uuid.uuid4()), operation=operation,
            campaign_id="p5-local-trial-count" if operation == "input_token_count"
            else "paid-p5-eight-scenario-evaluation-v1",
            model="gpt-6-luna", payload_sha256=digest or "a" * 64,
            estimated_micro=amount // 2, reserved_micro=amount,
            price_version="synthetic-v1")

    def test_default_off_and_owner_enable(self):
        item = self.item()
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(item)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.enable(_Verifier(), "wrong")
        self.budget.enable(_Verifier(), "owner-test-password")
        self.budget.reserve(item)
        self.assertEqual(self.budget.snapshot()["reserved_micro"], 20_000)

    def test_combined_limit_and_duplicate_across_restart(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        for index in range(40):
            item = self.item(operation="input_token_count" if index % 2 else
                             "responses_generation")
            self.budget.reserve(item)
        reopened = TrialBudgetController(self.path)
        self.assertEqual(reopened.snapshot()["reserved_micro"], 800_000)
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(self.item())
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(item)

    def test_concurrent_last_slot(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        for _ in range(39):
            self.budget.reserve(self.item())

        def attempt(_):
            try:
                TrialBudgetController(self.path).reserve(self.item())
                return True
            except TrialBudgetBlocked:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, range(2))), [False, True])

    def test_claim_binds_payload_and_is_one_use(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.claim(item.request_id, item.operation, "b" * 64,
                              campaign_id=item.campaign_id, model=item.model)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, model=item.model)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                              campaign_id=item.campaign_id, model=item.model)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item())

    def test_unknown_usage_and_overrun_hold(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=None, usage_json=None,
                           billing_source=None)
        self.assertTrue(TrialBudgetController(self.path).snapshot()["held"])
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item())

    def test_estimate_actual_separation_and_overrun(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=21_000,
                           usage_json='{"input_tokens":1}',
                           billing_source="synthetic-test")
        self.assertTrue(self.budget.snapshot()["held"])
        self.assertEqual(self.budget.snapshot()["known_actual_micro"], 21_000)

    def test_actual_above_estimate_below_reservation_is_recorded(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=15_000,
                           usage_json='{"input_tokens":100}',
                           billing_source="synthetic-test", latency_ms=21)
        snapshot = TrialBudgetController(self.path).snapshot()
        self.assertFalse(snapshot["held"])
        self.assertEqual(snapshot["known_actual_micro"], 15_000)
        self.assertEqual(snapshot["reserved_micro"], 20_000)

    def test_crash_after_claim_stays_blocked_after_restart(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, model=item.model)
        reopened = TrialBudgetController(self.path)
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(self.item())


if __name__ == "__main__":
    unittest.main()
