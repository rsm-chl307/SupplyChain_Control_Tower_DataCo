"""Owner-policy campaign behavior using synthetic Briefs and an offline database only."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import (
    CampaignBlocked, CaseSlot, EightCallCampaign, OWNER_MOCK_POLICY, OWNER_PAID_POLICY,
)
from src.ai_copilot.ledger import ProviderAccounting
from src.ai_copilot.provider import build_request
from src.ai_copilot.quality_evaluation import CaseResult, DIMENSIONS, Provenance
from src.synthetic_context import SyntheticHarness
from tests.test_ai_copilot_eight_call_campaign import PASSWORD, plan


class OwnerPolicyLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SyntheticHarness()
        cls.review = prepare_brief(cls.harness, cls.harness.issue("Baseline"), max_records=2).review
        assert cls.review is not None
        cls.request = build_request(cls.review, model_snapshot="gpt-6-luna",
                                    max_output_tokens=25000, timeout_seconds=180,
                                    execution_profile="P5_ACCEPTANCE_MOCK")

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="p5-owner-policy-offline-")
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / "campaign.db")
        verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
        env = patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                   "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex})
        env.start()
        self.addCleanup(env.stop)
        self.policy = replace(plan(), model_policy=OWNER_MOCK_POLICY,
                              model_snapshot="gpt-6-luna", max_output_tokens=25000,
                              timeout_seconds=180, per_slot_ceiling_micro=20000,
                              total_ceiling_micro=160000)
        EightCallCampaign.provision_offline(self.path, self.policy, PASSWORD)
        self.ledger = EightCallCampaign(self.path)

    def _reserve(self, case_id="EV-01"):
        ref = self.ledger.approve_slot(case_id, self.review, self.request, PASSWORD,
                                       estimated_micro=15000)
        return self.ledger.reserve_offline(case_id, self.review, self.request, ref)

    def _passed_review(self):
        p = Provenance(self.policy.campaign_id, self.policy.corpus_version,
                       "a" * 64, "EV-01", "case-v1", self.request.brief_digest,
                       self.request.provider_brief_digest, self.request.request_digest,
                       "b" * 64, "gpt-6-luna", self.request.schema_version,
                       self.request.instructions_version, self.request.privacy_version,
                       25000, 180)
        scores = {dimension: 4 for dimension in DIMENSIONS}
        rationales = {dimension: "Verified against synthetic source." for dimension in DIMENSIONS}
        return CaseResult(p, "VALIDATED", Decimal(80), "PASS", (), (),
                          ("reviewer-a", "reviewer-b"), "adjudicator", scores,
                          rationales, (), True, "Reviewed and accepted.")

    def test_sequential_review_and_budget_reservation(self):
        with self.assertRaises(CampaignBlocked):
            self._reserve("EV-07")
        self._reserve()
        self.assertEqual(self.ledger.summary()["reserved_micro"], 20000)
        with self.assertRaises(CampaignBlocked):
            self._reserve("EV-07")
        self.ledger.start_offline_attempt("EV-01", self.review, self.request)
        self.ledger.record_offline_outcome("EV-01", "SUCCEEDED",
            ProviderAccounting({"input_tokens": 3000, "output_tokens": 500,
                                "total_tokens": 3500}, "mock-request", "0.010000"))
        with self.assertRaises(CampaignBlocked):
            self._reserve("EV-07")
        self.ledger.record_case_review("EV-01", self._passed_review(), PASSWORD)
        self.assertEqual(self.ledger.reservation("EV-01")["state"], "SUCCEEDED")
        with self.assertRaises(CampaignBlocked):
            self.ledger.record_case_review("EV-01", self._passed_review(), PASSWORD)

    def test_missing_accounting_becomes_unknown_and_holds(self):
        self._reserve()
        self.ledger.start_offline_attempt("EV-01", self.review, self.request)
        row = self.ledger.record_offline_outcome("EV-01", "SUCCEEDED")
        self.assertEqual(row["state"], "UNKNOWN")
        self.assertEqual(EightCallCampaign(self.path).summary()["status"], "HELD")
        with self.assertRaises(CampaignBlocked):
            self.ledger.start_offline_attempt("EV-01", self.review, self.request)

    def test_exact_owner_limits_and_modified_request_rejected(self):
        for value in (replace(self.policy, per_slot_ceiling_micro=20001),
                      replace(self.policy, total_ceiling_micro=160001),
                      replace(self.policy, max_output_tokens=24999)):
            with self.assertRaises(CampaignBlocked):
                value.validate()
        ref = self.ledger.approve_slot("EV-01", self.review, self.request, PASSWORD,
                                       estimated_micro=15000)
        changed = build_request(self.review, model_snapshot="gpt-6-luna",
                                max_output_tokens=25000, timeout_seconds=180,
                                execution_profile="P5_ACCEPTANCE_MOCK")
        self.assertEqual(changed.request_digest, self.request.request_digest)
        with self.assertRaises(Exception):
            self.ledger.reserve_offline("EV-01", self.review,
                                        replace(changed, request_digest="0" * 64), ref)

    def test_paid_draft_owner_and_token_gate(self):
        corpus_path = Path(__file__).resolve().parents[1] / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json"
        cases = json.loads(corpus_path.read_text())["cases"]
        slots = tuple(CaseSlot(item["id"], item["case_version"], item["fixture_id"],
                               item["scenario"], item["max_records"], item["comparison"])
                      for item in cases)
        paid_plan = replace(self.policy, campaign_id="paid-synthetic-test-only",
                            model_policy=OWNER_PAID_POLICY,
                            corpus_version="p5-offline-evaluation-2", slots=slots)
        paid_path = str(Path(self.path).with_name("paid-test-draft.db"))
        EightCallCampaign.provision_paid_draft(paid_path, paid_plan, PASSWORD)
        paid = EightCallCampaign(paid_path)
        paid_request = build_request(self.review, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_PAID_ACCEPTANCE")
        self.assertEqual(paid.summary()["status"], "DRAFT")
        with self.assertRaises(CampaignBlocked):
            paid.approve_slot("EV-01", self.review, paid_request, PASSWORD,
                              estimated_micro=15000)
        with self.assertRaises(CampaignBlocked):
            paid.authorize_paid_acceptance("demo-password", paid_plan.digest())
        with self.assertRaises(CampaignBlocked):
            paid.authorize_paid_acceptance(PASSWORD, "0" * 64)
        with self.assertRaises(CampaignBlocked):
            paid.authorize_paid_acceptance(PASSWORD, paid_plan.digest(), now=100)
        paid.authorize_paid_acceptance(PASSWORD, paid_plan.digest())
        with self.assertRaises(CampaignBlocked):
            paid.approve_slot("EV-01", self.review, paid_request, PASSWORD,
                              estimated_micro=15000, now=100)
        ref = paid.approve_slot("EV-01", self.review, paid_request, PASSWORD,
                                estimated_micro=15000)
        with self.assertRaises(CampaignBlocked):
            paid.reserve_paid("EV-01", self.review, paid_request, ref, now=100)
        with self.assertRaisesRegex(CampaignBlocked, "Exact input-token evidence missing, stale"):
            paid.reserve_paid("EV-01", self.review, paid_request, ref)
        self.assertIsNone(paid.reservation("EV-01"))
        self.assertEqual(paid.summary()["reserved_micro"], 0)
        with paid._connect() as db:
            self.assertIsNone(db.execute(
                "SELECT consumed_at FROM slot_approvals WHERE reference=?", (ref,)
            ).fetchone()[0])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0], 0)
        self.assertEqual(paid.summary()["mode"], "PAID_ACCEPTANCE")


if __name__ == "__main__":
    unittest.main()
