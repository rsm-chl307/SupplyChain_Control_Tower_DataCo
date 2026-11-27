"""Offline checks for the shared Count and Generation trial budget."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

from tools.windows_api_runner.trial_budget import (
    BudgetReservation, PRICE_VERSION, TrialBudgetBlocked,
    TrialBudgetController, estimate_generation_micro,
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
            self.path, "trial-offline", price_version=PRICE_VERSION)

    def item(self, *, operation="input_token_count", request_id=None,
             digest=None, count=None, run_id="synthetic-run"):
        return BudgetReservation(
            request_id=request_id or str(uuid.uuid4()), operation=operation,
            campaign_id="p5-local-trial-count" if operation == "input_token_count"
            else "paid-p5-eight-scenario-evaluation-v1",
            model="gpt-6-luna", payload_sha256=digest or "a" * 64,
            estimated_micro=(20_000 if operation == "input_token_count" else
                             estimate_generation_micro(4_000, 25_000)),
            reserved_micro=20_000, price_version=PRICE_VERSION,
            case_id="EV-01", run_id=run_id,
            count_request_id=count.request_id if count else None,
            count_payload_sha256=count.payload_sha256 if count else None)

    def confirmed_count(self):
        count = self.item()
        self.budget.reserve(count)
        self.budget.claim(count.request_id, count.operation, count.payload_sha256,
                          campaign_id=count.campaign_id, case_id=count.case_id,
                          run_id=count.run_id, model=count.model)
        self.budget.confirm_count(count.request_id, input_tokens=4_000, latency_ms=10)
        return count

    def test_default_off_and_owner_enable(self):
        item = self.item()
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(item)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.enable(_Verifier(), "wrong")
        self.budget.enable(_Verifier(), "owner-test-password")
        self.budget.reserve(item)
        self.assertEqual(self.budget.snapshot()["reserved_micro"], 20_000)

    def test_combined_count_generation_and_duplicate_across_restart(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        item = self.item(operation="responses_generation", count=count)
        self.budget.reserve(item)
        reopened = TrialBudgetController(self.path)
        self.assertEqual(reopened.snapshot()["reserved_micro"], 40_000)
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(self.item())
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(item)

    def test_concurrent_generation_reservation_allows_only_one(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()

        def attempt(_):
            try:
                TrialBudgetController(self.path).reserve(
                    self.item(operation="responses_generation", count=count))
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
                              campaign_id=item.campaign_id, case_id=item.case_id,
                              run_id=item.run_id, model=item.model)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                              campaign_id=item.campaign_id, case_id=item.case_id,
                              run_id="another-run", model=item.model)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, case_id=item.case_id,
                          run_id=item.run_id, model=item.model)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                              campaign_id=item.campaign_id, case_id=item.case_id,
                              run_id=item.run_id, model=item.model)
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item())

    def test_unknown_usage_and_overrun_hold(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, case_id=item.case_id,
                          run_id=item.run_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=None, usage_json=None,
                           billing_source=None)
        self.assertTrue(TrialBudgetController(self.path).snapshot()["held"])
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item())

    def test_estimate_actual_separation_and_overrun(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        item = self.item(operation="responses_generation", count=count)
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, case_id=item.case_id,
                          run_id=item.run_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=21_000,
                           usage_json='{"input_tokens":1}',
                           billing_source="synthetic-test")
        self.assertTrue(self.budget.snapshot()["held"])
        self.assertEqual(self.budget.snapshot()["known_actual_micro"], 21_000)

    def test_actual_above_estimate_below_reservation_is_recorded(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        item = self.item(operation="responses_generation", count=count)
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, case_id=item.case_id,
                          run_id=item.run_id, model=item.model)
        self.budget.finish(item.request_id, actual_micro=15_000,
                           usage_json='{"input_tokens":100}',
                           billing_source="synthetic-test", latency_ms=21)
        snapshot = TrialBudgetController(self.path).snapshot()
        self.assertFalse(snapshot["held"])
        self.assertEqual(snapshot["known_actual_micro"], 15_000)
        self.assertEqual(snapshot["reserved_micro"], 40_000)

    def test_crash_after_claim_stays_blocked_after_restart(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        item = self.item()
        self.budget.reserve(item)
        self.budget.claim(item.request_id, item.operation, item.payload_sha256,
                          campaign_id=item.campaign_id, case_id=item.case_id,
                          run_id=item.run_id, model=item.model)
        reopened = TrialBudgetController(self.path)
        with self.assertRaises(TrialBudgetBlocked):
            reopened.reserve(self.item())

    def test_confirmed_count_keeps_actual_unknown_but_allows_linked_generation(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        snapshot = self.budget.snapshot()
        self.assertEqual(snapshot["reserved_micro"], 20_000)
        self.assertEqual(snapshot["known_actual_micro"], 0)
        self.assertFalse(snapshot["held"])
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item(operation="responses_generation",
                                          count=count, run_id="different-run"))
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(BudgetReservation(**{
                **self.item(operation="responses_generation", count=count).__dict__,
                "count_payload_sha256": "b" * 64}))
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(BudgetReservation(**{
                **self.item(operation="responses_generation", count=count).__dict__,
                "estimated_micro": 10_000}))
        self.budget.reserve(self.item(operation="responses_generation", count=count))

    def test_insufficient_combined_budget_rejects_generation(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        # Synthetic already-incurred reservation tests the arithmetic branch.
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET reserved_micro=795000 WHERE request_id=?",
                       (count.request_id,))
        with self.assertRaisesRegex(TrialBudgetBlocked, "budget exhausted"):
            self.budget.reserve(self.item(operation="responses_generation", count=count))

    def test_ev02_and_unrelated_count_are_rejected(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(BudgetReservation(**{
                **self.item().__dict__, "case_id": "EV-02"}))
        self.confirmed_count()
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item())

    def test_versioned_quote_and_caps(self):
        self.assertEqual(estimate_generation_micro(4_000, 25_000), 14_190)
        self.assertEqual(estimate_generation_micro(25_000, 25_000), 16_500)
        with self.assertRaises(TrialBudgetBlocked):
            estimate_generation_micro(25_001, 25_000)
        with self.assertRaises(TrialBudgetBlocked):
            estimate_generation_micro(4_000, 30_000)

    def test_generation_usage_and_later_owner_actual_keep_trial_held(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        generation = self.item(operation="responses_generation", count=count)
        self.budget.reserve(generation)
        self.budget.claim(generation.request_id, generation.operation,
                          generation.payload_sha256, campaign_id=generation.campaign_id,
                          case_id=generation.case_id, run_id=generation.run_id,
                          model=generation.model, cost_limit_micro=20_000)
        self.budget.finish(generation.request_id, actual_micro=None,
                           usage_json=None, billing_source=None, latency_ms=45)
        self.budget.record_usage(generation.request_id, {
            "input_tokens": 4_000, "output_tokens": 2_000, "total_tokens": 6_000})
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.record_usage(generation.request_id, {"secret": "no"})
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.record_actual(generation.request_id, actual_micro=1_500,
                                      billing_source="owner-verified-platform-billing",
                                      verifier=_Verifier(), password="wrong")
        self.budget.record_actual(generation.request_id, actual_micro=1_500,
                                  billing_source="owner-verified-platform-billing",
                                  verifier=_Verifier(), password="owner-test-password")
        self.assertEqual(self.budget.snapshot()["known_actual_micro"], 1_500)
        self.assertTrue(self.budget.snapshot()["held"])
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.record_actual(generation.request_id, actual_micro=1_500,
                                      billing_source="owner-verified-platform-billing",
                                      verifier=_Verifier(), password="owner-test-password")

    def test_count_bill_above_reserve_holds_before_generation(self):
        self.budget.enable(_Verifier(), "owner-test-password")
        count = self.confirmed_count()
        self.budget.record_actual(count.request_id, actual_micro=21_000,
                                  billing_source="owner-verified-platform-billing",
                                  verifier=_Verifier(), password="owner-test-password")
        self.assertTrue(self.budget.snapshot()["held"])
        with self.assertRaises(TrialBudgetBlocked):
            self.budget.reserve(self.item(operation="responses_generation", count=count))


if __name__ == "__main__":
    unittest.main()
