"""WP4.6.2 paid-workflow controls using isolated SQLite and Fake Transport only."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import (
    CaseSlot, EightCallCampaign, OWNER_PAID_POLICY, CampaignBlocked,
)
from src.ai_copilot.evaluation_archive import (
    ArchiveBlocked, GenerationEvaluationArchive, _wire,
)
from src.ai_copilot.provider import (
    REAL_PROVIDER_DISPATCH_LOCKED, OfflineMockTransport, OpenAIResponsesAdapter,
    ProviderBlocked, build_request,
)
from src.ai_copilot.windows_runner_exchange import WindowsHostTokenCountExchange
from src.synthetic_context import SyntheticHarness
from tools.windows_api_runner.api_runner import canonical_json_bytes
from tests.test_ai_copilot_eight_call_campaign import PASSWORD, plan
from tests.test_p5_quality_evaluation import response as valid_response


class ArchiveLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-wp4-6-2-test-only-")
        self.addCleanup(self.temp.cleanup)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.review = prepare_brief(self.harness, self.harness.issue("Baseline"), max_records=2).review
        self.cases = json.loads((Path(__file__).resolve().parents[1] /
                                "docs/ai_copilot/p5_offline_evaluation/cases.v2.json").read_text())["cases"]
        self.case = self.cases[0]
        slots = tuple(CaseSlot(c["id"], c["case_version"], c["fixture_id"], c["scenario"],
                               c["max_records"], c["comparison"]) for c in self.cases)
        self.policy = replace(plan(), campaign_id="paid-wp4-6-2-test-only",
                              corpus_version="p5-offline-evaluation-2", slots=slots,
                              model_policy=OWNER_PAID_POLICY, model_snapshot="gpt-6-luna",
                              max_output_tokens=25000, timeout_seconds=180,
                              per_slot_ceiling_micro=20000, total_ceiling_micro=160000)
        self.db_path = str(Path(self.temp.name) / "test-ledger.sqlite")
        self.archive_path = str(Path(self.temp.name) / "test-archive.sqlite")
        verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
        self.env = patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                           "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex})
        self.env.start()
        self.addCleanup(self.env.stop)
        EightCallCampaign.provision_paid_draft(self.db_path, self.policy, PASSWORD)
        self.campaign = EightCallCampaign(self.db_path)
        self.request = build_request(self.review, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_PAID_ACCEPTANCE")
        self.campaign.authorize_paid_acceptance(PASSWORD, self.policy.digest())
        self.approval = self.campaign.approve_slot("EV-01", self.review, self.request,
                                                   PASSWORD, estimated_micro=15000)
        self.archive = self._archive()
        self.exchange = WindowsHostTokenCountExchange(Path(self.temp.name) / "host-exchange")
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        response_package = {
            "request_id": prepared.request_id, "case_id": prepared.case_id,
            "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
            "operation": "input_token_count", "http_status": 200,
            "openai_request_id": "synthetic-test-count-ev01", "model": "gpt-6-luna",
            "returned_model_id": "gpt-6-luna", "usage": None,
            "response_body": {"input_tokens": 3992, "model": "gpt-6-luna"},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": "SUCCEEDED",
            "brief_digest": prepared.brief_digest,
            "provider_request_digest": prepared.provider_request_digest,
            "count_projection_digest": prepared.count_projection_digest,
            "run_manifest_sha256": prepared.run_manifest_sha256,
        }
        response_path = Path(self.temp.name) / "host-exchange" / "responses" / f"{prepared.request_id}.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_bytes(canonical_json_bytes(response_package) + b"\n")
        self.count = self.exchange.collect(prepared, self.review, self.request)
        self.campaign.reserve_paid("EV-01", self.review, self.request, self.approval,
                                   token_evidence=self.count)
        self.campaign.start_paid_attempt("EV-01", self.review, self.request,
                                         token_evidence=self.count)

    def _archive(self):
        GenerationEvaluationArchive.provision(self.archive_path)
        return GenerationEvaluationArchive(self.archive_path)

    def _valid_transport(self):
        payload = valid_response(self.review, ["s7"], self.case["numerical_slot_ref"],
                                 self.case["numerical_slot_field"]).decode()
        response = SimpleNamespace(
            status="completed", model="gpt-6-luna", _request_id="fake-request-ev01",
            usage={"input_tokens": 3992, "output_tokens": 120, "total_tokens": 4112},
            output=[SimpleNamespace(type="message", content=[
                SimpleNamespace(type="output_text", text=payload)])])
        return OfflineMockTransport(response)

    def _dispatch(self, transport):
        return OpenAIResponsesAdapter.execute_authorized(
            self.request, self.review, campaign=self.campaign, case_id="EV-01",
            owner_password=PASSWORD, archive=self.archive, case=self.case,
            token_evidence=self.count, transport=transport)

    def test_intent_is_appended_and_bound_before_dispatch(self):
        transport = OfflineMockTransport(TimeoutError("synthetic interruption"))
        result = self._dispatch(transport)
        self.assertEqual(result.status, "UNKNOWN_OUTCOME")
        events = self.archive.dispatch_events(
            self._dispatch_id_from_archive())
        self.assertEqual([e["event_type"] for e in events],
                         ["GENERATION_INTENT", "GENERATION_RESULT"])
        intent, outcome = events
        self.assertEqual(intent["run_id"], self.count.run_id)
        _, generation_digest, generation_projection = _wire(self.request)
        self.assertEqual(intent["payload_sha256"], generation_digest)
        self.assertNotEqual(intent["payload_sha256"], self.count.full_payload_sha256)
        self.assertEqual(intent["projection_sha256"], generation_projection)
        self.assertEqual(intent["projection_sha256"], self.count.count_projection_sha256)
        self.assertEqual(intent["token_evidence_ref"], self.count.request_id)
        self.assertEqual(intent["campaign_id"], self.policy.campaign_id)
        self.assertTrue(intent["ledger_attempt_id"])
        self.assertEqual(outcome["dispatch_id"], intent["dispatch_id"])
        self.assertEqual(transport.calls, 1)

    def _dispatch_id_from_archive(self):
        with sqlite3.connect(self.archive_path) as db:
            return db.execute("SELECT dispatch_id FROM archive_dispatch_events LIMIT 1").fetchone()[0]

    def test_intent_failure_prevents_claim_and_transport(self):
        transport = self._valid_transport()
        with patch.object(self.archive, "append_generation_intent",
                          side_effect=ArchiveBlocked("synthetic archive write failure")):
            with self.assertRaises(ProviderBlocked):
                self._dispatch(transport)
        self.assertEqual(transport.calls, 0)
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0], 0)
        # A later Ledger claim rejection also occurs before Fake Transport.
        transport = self._valid_transport()
        with patch.object(self.campaign, "claim_paid_dispatch",
                          side_effect=CampaignBlocked("synthetic claim rejection")):
            with self.assertRaises(CampaignBlocked):
                self._dispatch(transport)
        self.assertEqual(transport.calls, 0)

    def test_success_appends_response_result_and_preserves_lineage(self):
        transport = self._valid_transport()
        result = self._dispatch(transport)
        events = self.archive.dispatch_events(self._dispatch_id_from_archive())
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(self.archive.history(events[0]["record_id"])[0].phase, "GENERATION")
        self.assertEqual(events[1]["request_id"], "fake-request-ev01")
        self.assertEqual(events[1]["returned_model_id"], "gpt-6-luna")
        self.assertEqual(events[1]["usage_source"], "PROVIDER_RESPONSE")
        self.assertIsNone(events[1]["charge_usd"])
        self.assertIsNone(events[1]["charge_source"])
        self.assertEqual(transport.calls, 1)

    def test_result_archive_failure_holds_campaign_and_never_redispatches(self):
        transport = self._valid_transport()
        with patch.object(self.archive, "append_generation_result",
                          side_effect=ArchiveBlocked("synthetic result archive failure")):
            with self.assertRaises(ProviderBlocked):
                self._dispatch(transport)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(self.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.campaign.summary()["status"], "HELD")
        with sqlite3.connect(self.db_path) as db:
            response_digest = db.execute(
                "SELECT response_digest FROM provider_observations WHERE case_id='EV-01'").fetchone()[0]
        self.assertTrue(response_digest)
        restarted = EightCallCampaign(self.db_path)
        retry = self._valid_transport()
        with self.assertRaises((CampaignBlocked, ProviderBlocked)):
            OpenAIResponsesAdapter.execute_authorized(
                self.request, self.review, campaign=restarted, case_id="EV-01",
                owner_password=PASSWORD, archive=self.archive, case=self.case,
                token_evidence=self.count, transport=retry)
        self.assertEqual(retry.calls, 0)

    def test_unknown_restart_preserves_dispatch_identity_and_blocks_resend(self):
        first = OfflineMockTransport(TimeoutError("synthetic timeout"))
        self.assertEqual(self._dispatch(first).status, "UNKNOWN_OUTCOME")
        dispatch_id = self._dispatch_id_from_archive()
        before = self.archive.dispatch_events(dispatch_id)
        restarted = EightCallCampaign(self.db_path)
        retry = self._valid_transport()
        with self.assertRaises((CampaignBlocked, ProviderBlocked)):
            OpenAIResponsesAdapter.execute_authorized(
                self.request, self.review, campaign=restarted, case_id="EV-01",
                owner_password=PASSWORD, archive=self.archive, case=self.case,
                token_evidence=self.count, transport=retry)
        self.assertEqual(retry.calls, 0)
        after = self.archive.dispatch_events(dispatch_id)
        self.assertEqual(after, before)
        self.assertEqual(restarted.reservation("EV-01")["state"], "UNKNOWN")

    def test_synthetic_approval_is_bound_to_test_ledger_and_locked_real_provider(self):
        # A production-principal simulation in another temporary DB cannot consume it.
        other_password = "different-test-owner-password"
        other_verifier = OwnerVerifier.derive(other_password, b"fedcba9876543210")
        other_path = str(Path(self.temp.name) / "production-principal-simulation.sqlite")
        other_policy = replace(self.policy, campaign_id="paid-production-principal-simulation")
        with patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": other_verifier.salt_hex,
                                     "COPILOT_OWNER_SCRYPT_HEX": other_verifier.digest_hex}):
            EightCallCampaign.provision_paid_draft(other_path, other_policy, other_password)
            other = EightCallCampaign(other_path)
            other.authorize_paid_acceptance(other_password, other_policy.digest())
            with self.assertRaises(CampaignBlocked):
                other.reserve_paid("EV-01", self.review, self.request, self.approval)
        self.assertTrue(REAL_PROVIDER_DISPATCH_LOCKED)
        with self.assertRaises(ProviderBlocked):
            OpenAIResponsesAdapter.execute_authorized(
                self.request, self.review, campaign=self.campaign, case_id="EV-01",
                owner_password=PASSWORD, archive=self.archive, case=self.case,
                token_evidence=self.count, transport=None)


if __name__ == "__main__":
    unittest.main()
