"""Synthetic-only offline campaign tests; never dispatches a provider."""
from __future__ import annotations

from dataclasses import replace
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import (
    CASE_IDS, CampaignBlocked, CaseSlot, EightCallCampaign, OfflineCampaignPlan,
)
from src.ai_copilot.ledger import ProviderAccounting
from src.ai_copilot.provider import OpenAIResponsesAdapter, ProviderBlocked, build_request
from src.synthetic_context import SyntheticHarness


PASSWORD = "eight-call-test-owner-password"


def plan(*, total: int = 80000) -> OfflineCampaignPlan:
    scenarios = ("Baseline", "Demand_Surge", "Capacity_Disruption", "Combined_Stress",
                 "Baseline", "Baseline", "Baseline", "Baseline")
    return OfflineCampaignPlan(
        campaign_id="offline-eight-case-test", corpus_version="synthetic-test-corpus-1",
        slots=tuple(CaseSlot(cid, "case-v1", "p5_low_risk_v1" if cid == "EV-08-LR" else "v1_1",
                             scenario, 4 if cid == "EV-08-LR" else 2,
                             cid in {"EV-05", "EV-06"})
                    for cid, scenario in zip(CASE_IDS, scenarios)),
        model_id="gpt-6-luna", model_policy="UNVERIFIED_OFFLINE_TEST",
        model_snapshot="offline-test-snapshot", max_output_tokens=500,
        timeout_seconds=10, pricing_basis="offline-test-prices-only",
        per_slot_ceiling_micro=10000, total_ceiling_micro=total,
    )


class EightCallCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = SyntheticHarness()
        cls.low = SyntheticHarness(fixture_id="p5_low_risk_v1")
        cls.review = prepare_brief(cls.original, cls.original.issue("Baseline"), max_records=2).review
        cls.low_review = prepare_brief(cls.low, cls.low.issue("Baseline"), max_records=4).review
        assert cls.review is not None and cls.low_review is not None
        cls.request = build_request(cls.review, model_snapshot="offline-test-snapshot",
                                    max_output_tokens=500, timeout_seconds=10)
        cls.low_request = build_request(cls.low_review, model_snapshot="offline-test-snapshot",
                                        max_output_tokens=500, timeout_seconds=10)

    @classmethod
    def tearDownClass(cls):
        cls.original.close()
        cls.low.close()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="p5-eight-offline-")
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / "campaign.db")
        verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
        env = patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                   "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex})
        env.start()
        self.addCleanup(env.stop)
        self.plan = plan()
        EightCallCampaign.provision_offline(self.path, self.plan, PASSWORD)
        self.ledger = EightCallCampaign(self.path)

    def approve(self, case_id="EV-01", review=None, request=None, **kwargs):
        return self.ledger.approve_slot(case_id, review or self.review,
                                        request or self.request, PASSWORD,
                                        estimated_micro=8000, **kwargs)

    def test_provision_exact_roster_and_separate_p3_store(self):
        self.assertEqual(tuple(s.case_id for s in self.ledger.plan().slots), CASE_IDS)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT mode FROM campaign").fetchone()[0], "OFFLINE_TEST")
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_ledger'").fetchone())
        with self.assertRaises(Exception):
            EightCallCampaign.provision_offline(self.path, self.plan, PASSWORD)
        bad = replace(self.plan, slots=self.plan.slots[:-1])
        with self.assertRaises(CampaignBlocked):
            bad.validate()

    def test_owner_verifier_cannot_be_substituted(self):
        with self.assertRaises(CampaignBlocked):
            self.ledger.approve_slot("EV-01", self.review, self.request, "demo-password",
                                     estimated_micro=8000)
        other = OwnerVerifier.derive("other-owner-test-password", b"fedcba9876543210")
        with patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": other.salt_hex,
                                         "COPILOT_OWNER_SCRYPT_HEX": other.digest_hex}):
            with self.assertRaises(CampaignBlocked):
                EightCallCampaign(self.path)

    def test_same_request_digest_needs_two_independent_approvals(self):
        first = self.approve("EV-01")
        second = self.approve("EV-07")
        self.assertNotEqual(first, second)
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-07", self.review, self.request, first)
        a = self.ledger.reserve_offline("EV-01", self.review, self.request, first)
        b = self.ledger.reserve_offline("EV-07", self.review, self.request, second)
        self.assertEqual(a["request_digest"], b["request_digest"])
        self.assertNotEqual(a["approval_reference"], b["approval_reference"])
        self.assertEqual(self.ledger.plan().total_ceiling_micro, 80000)
        self.assertEqual(self.ledger.summary()["estimated_micro"], 16000)
        self.assertEqual(self.ledger.summary()["missing_charge_slots"], 2)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT reserved_micro FROM campaign").fetchone()[0], 20000)
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-01", self.review, self.request, first)

    def test_just_in_time_rebuild_rejects_stale_modified_and_wrong_fixture(self):
        ref = self.approve()
        changed = build_request(self.review, model_snapshot="offline-test-snapshot",
                                max_output_tokens=501, timeout_seconds=10)
        for request in (changed, replace(self.request, request_digest="0" * 64)):
            with self.subTest(request=request.request_digest), self.assertRaises(Exception):
                self.ledger.reserve_offline("EV-01", self.review, request, ref)
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-08-LR", self.review, self.request, ref)
        low_ref = self.approve("EV-08-LR", self.low_review, self.low_request)
        self.assertEqual(self.ledger.reserve_offline("EV-08-LR", self.low_review,
                                                    self.low_request, low_ref)["state"], "NOT_STARTED")

    def test_expired_revoked_and_cross_slot_approval_rejected(self):
        ref = self.approve(now=100, ttl_seconds=10)
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-01", self.review, self.request, ref, now=110)
        self.ledger.revoke_approval(ref, PASSWORD, now=105)
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-01", self.review, self.request, ref, now=106)
        fresh = self.approve()
        with self.assertRaises(CampaignBlocked):
            self.ledger.reserve_offline("EV-07", self.review, self.request, fresh)

    def test_atomic_concurrent_duplicate_reservation(self):
        ref = self.approve()
        def attempt(_):
            try:
                self.ledger.reserve_offline("EV-01", self.review, self.request, ref)
                return True
            except CampaignBlocked:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(attempt, range(4)))
        self.assertEqual(outcomes.count(True), 1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT reserved_micro FROM campaign").fetchone()[0], 10000)

    def test_interprocess_reservation_uses_one_allowance(self):
        ref = self.approve()
        context = multiprocessing.get_context("fork")
        queue = context.Queue()
        def attempt():
            try:
                EightCallCampaign(self.path).reserve_offline("EV-01", self.review, self.request, ref)
                queue.put("reserved")
            except CampaignBlocked:
                queue.put("blocked")
        workers = [context.Process(target=attempt) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=15)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(sorted(queue.get(timeout=1) for _ in workers), ["blocked", "reserved"])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT reserved_micro FROM campaign").fetchone()[0], 10000)

    def test_aggregate_limit_and_transaction_rollback(self):
        constrained = replace(self.plan, total_ceiling_micro=10000)
        # Different isolated store; never modifies the first store.
        path = str(Path(self.path).with_name("constrained.db"))
        EightCallCampaign.provision_offline(path, constrained, PASSWORD)
        ledger = EightCallCampaign(path)
        first = ledger.approve_slot("EV-01", self.review, self.request, PASSWORD,
                                    estimated_micro=8000)
        second = ledger.approve_slot("EV-07", self.review, self.request, PASSWORD,
                                     estimated_micro=8000)
        ledger.reserve_offline("EV-01", self.review, self.request, first)
        with self.assertRaises(CampaignBlocked):
            ledger.reserve_offline("EV-07", self.review, self.request, second)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT reserved_micro FROM campaign").fetchone()[0], 10000)
            self.assertIsNone(db.execute("SELECT consumed_at FROM slot_approvals WHERE reference=?",
                                         (second,)).fetchone()[0])

    def test_offline_states_missing_accounting_unknown_and_restart(self):
        ref = self.approve()
        self.ledger.reserve_offline("EV-01", self.review, self.request, ref)
        reopened = EightCallCampaign(self.path)
        self.assertEqual(reopened.reservation("EV-01")["state"], "NOT_STARTED")
        reopened.start_offline_attempt("EV-01", self.review, self.request)
        with self.assertRaises(CampaignBlocked):
            reopened.start_offline_attempt("EV-01", self.review, self.request)
        with self.assertRaises(CampaignBlocked):
            reopened.record_offline_outcome("EV-01", "SUCCEEDED")
        reopened.record_offline_outcome("EV-01", "UNKNOWN")
        restarted = EightCallCampaign(self.path)
        self.assertEqual(restarted.reservation("EV-01")["state"], "UNKNOWN")
        with self.assertRaises(CampaignBlocked):
            restarted.start_offline_attempt("EV-01", self.review, self.request)
        with self.assertRaises(CampaignBlocked):
            restarted.reconcile("EV-01", "demo-password", "Review pending")
        entry = restarted.reconcile("EV-01", PASSWORD, "Provider status unresolved")
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertIsNone(entry["charge_micro"])
        self.assertEqual(entry["ceiling_micro"], 10000)

    def test_restart_with_in_progress_blocks_other_reservations(self):
        first = self.approve("EV-01")
        second = self.approve("EV-07")
        self.ledger.reserve_offline("EV-01", self.review, self.request, first)
        self.ledger.start_offline_attempt("EV-01", self.review, self.request)
        reopened = EightCallCampaign(self.path)
        self.assertEqual(reopened.reservation("EV-01")["state"], "IN_PROGRESS")
        with self.assertRaises(CampaignBlocked):
            reopened.reserve_offline("EV-07", self.review, self.request, second)
        self.assertEqual(reopened.summary()["reserved_micro"], 10000)

    def test_reserved_undispatched_is_not_released(self):
        ref = self.approve()
        self.ledger.reserve_offline("EV-01", self.review, self.request, ref)
        restarted = EightCallCampaign(self.path)
        with self.assertRaises(CampaignBlocked):
            restarted.reserve_offline("EV-01", self.review, self.request, ref)
        entry = restarted.reconcile("EV-01", PASSWORD, "Dispatch unproven")
        self.assertEqual(entry["state"], "UNKNOWN")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT reserved_micro FROM campaign").fetchone()[0], 10000)

    def test_definitive_failure_requires_accounting_and_keeps_allowance(self):
        ref = self.approve()
        self.ledger.reserve_offline("EV-01", self.review, self.request, ref)
        self.ledger.start_offline_attempt("EV-01", self.review, self.request)
        with self.assertRaises(CampaignBlocked):
            self.ledger.record_offline_outcome("EV-01", "FAILED", ProviderAccounting(note="No usage"))
        entry = self.ledger.record_offline_outcome("EV-01", "FAILED", ProviderAccounting(
            usage={"input_tokens": 0, "output_tokens": 0}, provider_charge_usd="0",
            note="Definitive offline failure"))
        self.assertEqual(entry["state"], "FAILED")
        self.assertEqual(entry["ceiling_micro"], 10000)
        with self.assertRaises(CampaignBlocked):
            self.ledger.start_offline_attempt("EV-01", self.review, self.request)

    def test_definitive_outcomes_and_over_ceiling_hold(self):
        ref = self.approve()
        self.ledger.reserve_offline("EV-01", self.review, self.request, ref)
        self.ledger.start_offline_attempt("EV-01", self.review, self.request)
        observed = ProviderAccounting(usage={"input_tokens": 2, "output_tokens": 3},
                                      provider_charge_usd="0.011", note="Offline observed metadata")
        entry = self.ledger.record_offline_outcome("EV-01", "SUCCEEDED", observed)
        self.assertEqual(entry["charge_micro"], 11000)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT status FROM campaign").fetchone()[0], "HELD")
        with self.assertRaises(CampaignBlocked):
            self.ledger.record_offline_outcome("EV-01", "FAILED", observed)
        self.assertTrue(any(e[1] == "SUCCEEDED" for e in self.ledger.events()))

    def test_missing_replaced_corrupt_store_and_event_append_only(self):
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM campaign_events")
        replacement = str(Path(self.path).with_name("replacement.db"))
        Path(replacement).write_bytes(Path(self.path).read_bytes())
        with self.assertRaises(Exception):
            EightCallCampaign(replacement)
        copied = Path(self.path).read_bytes()
        moved = Path(self.path).with_name("moved.db")
        os.replace(self.path, moved)
        Path(self.path).write_bytes(copied)
        with self.assertRaises(Exception):
            self.ledger.plan()
        os.replace(moved, self.path)
        Path(self.path).write_bytes(b"not a sqlite database")
        with self.assertRaises(Exception):
            EightCallCampaign(self.path)

    def test_adapter_remains_blocked(self):
        with self.assertRaises(ProviderBlocked):
            OpenAIResponsesAdapter().execute(self.request)
        self.assertFalse(hasattr(self.ledger, "execute"))


if __name__ == "__main__":
    unittest.main()
