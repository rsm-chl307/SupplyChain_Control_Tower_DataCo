"""Isolated paid Ledger tests for Host-signed Owner intent and atomic claim."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import (
    CaseSlot, EightCallCampaign, OWNER_PAID_POLICY, CampaignBlocked,
)
from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive, _wire
from src.ai_copilot.evaluation_namespace import CAMPAIGN_ID, NAMESPACE_ID
from src.ai_copilot.evaluation_namespace import EvaluationNamespace
from src.ai_copilot.p5_token_count_orchestrator import P5TokenCountOrchestrator
from src.ai_copilot.windows_generation_dispatch import (
    prepare_generation_proposal, finalize_generation_dispatch,
)
from src.ai_copilot.provider import build_request
from src.ai_copilot.windows_runner_exchange import WindowsHostTokenCountExchange
from src.synthetic_context import SyntheticHarness
from tests.test_ai_copilot_eight_call_campaign import PASSWORD, plan
from tools.windows_api_runner.api_runner import canonical_json_bytes
from tools.windows_api_runner.generation_authorization import (
    AUTH_FIELDS, new_authorization_body, sign_owner_authorization,
)
from tools.windows_api_runner.generation_permit import verify_signed_permit


class HostClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-host-claim-fake-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.review = prepare_brief(self.harness, self.harness.issue("Baseline"),
                                    max_records=2).review
        self.case = json.loads((Path(__file__).resolve().parents[1] /
                                "docs/ai_copilot/p5_offline_evaluation/cases.v2.json").read_text())["cases"][0]
        cases = json.loads((Path(__file__).resolve().parents[1] /
                            "docs/ai_copilot/p5_offline_evaluation/cases.v2.json").read_text())["cases"]
        slots = tuple(CaseSlot(c["id"], c["case_version"], c["fixture_id"], c["scenario"],
                               c["max_records"], c["comparison"]) for c in cases)
        self.policy = replace(plan(), campaign_id=CAMPAIGN_ID,
                              corpus_version="p5-offline-evaluation-2", slots=slots,
                              model_policy=OWNER_PAID_POLICY, model_snapshot="gpt-6-luna",
                              max_output_tokens=25000, timeout_seconds=180,
                              per_slot_ceiling_micro=20000, total_ceiling_micro=160000)
        self.ledger_path = str(self.root / "test-ledger.sqlite3")
        self.archive_path = str(self.root / "test-archive.sqlite3")
        verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
        env = patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                      "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex})
        env.start()
        self.addCleanup(env.stop)
        EightCallCampaign.provision_paid_draft(self.ledger_path, self.policy, PASSWORD)
        self.campaign = EightCallCampaign(self.ledger_path)
        self.request = build_request(self.review, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_PAID_ACCEPTANCE")
        self.campaign.authorize_paid_acceptance(PASSWORD, self.policy.digest())
        self.approval = self.campaign.approve_slot(
            "EV-01", self.review, self.request, PASSWORD, estimated_micro=15000)
        GenerationEvaluationArchive.provision(self.archive_path)
        self.archive = GenerationEvaluationArchive(self.archive_path)
        exchange = WindowsHostTokenCountExchange(self.root / "exchange")
        prepared = exchange.prepare("EV-01", self.review, self.request)
        response = {
            "request_id": prepared.request_id, "case_id": prepared.case_id,
            "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
            "operation": "input_token_count", "http_status": 200,
            "openai_request_id": "synthetic-count-id", "model": "gpt-6-luna",
            "returned_model_id": "gpt-6-luna", "usage": None,
            "response_body": {"input_tokens": 4000, "model": "gpt-6-luna"},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": "SUCCEEDED",
            "brief_digest": prepared.brief_digest,
            "provider_request_digest": prepared.provider_request_digest,
            "count_projection_digest": prepared.count_projection_digest,
            "run_manifest_sha256": prepared.run_manifest_sha256,
        }
        response_path = self.root / "exchange" / "responses" / f"{prepared.request_id}.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_bytes(canonical_json_bytes(response) + b"\n")
        self.count = exchange.collect(prepared, self.review, self.request)
        self.campaign.reserve_paid("EV-01", self.review, self.request, self.approval,
                                   token_evidence=self.count)
        self.campaign.start_paid_attempt("EV-01", self.review, self.request,
                                         token_evidence=self.count)
        self.host_private = Ed25519PrivateKey.generate()
        self.host_public_path = self.root / "host-owner-public.bin"
        self.host_public_path.write_bytes(self.host_private.public_key().public_bytes_raw())
        anchor = patch("src.ai_copilot.eight_call_campaign.HOST_OWNER_PUBLIC_KEY_PATH",
                       self.host_public_path)
        anchor.start()
        self.addCleanup(anchor.stop)
        self.uuid = str(uuid.uuid4())

    def scope(self):
        _, payload_digest, projection_digest = _wire(self.request)
        evidence = asdict(self.count)
        evidence["evidence_refs"] = list(self.count.evidence_refs)
        return {
            "namespace": NAMESPACE_ID, "campaign_id": CAMPAIGN_ID,
            "case_id": "EV-01", "run_id": self.review._draft._bundle._context.run_id,
            "request_id": self.uuid, "model": "gpt-6-luna",
            "payload_sha256": payload_digest,
            "count_evidence_sha256": hashlib.sha256(canonical_bytes(evidence)).hexdigest(),
            "count_projection_sha256": projection_digest,
            "provider_request_digest": self.request.request_digest,
            "brief_digest": self.request.brief_digest,
            "token_cap": 25000, "cost_limit_micro_usd": 20000,
        }

    def signed(self, scope=None):
        body = new_authorization_body(self.scope() if scope is None else scope)
        return sign_owner_authorization(body, self.host_private)

    def intent(self):
        return self.archive.append_generation_intent(
            dispatch_id=self.uuid, case=self.case, review=self.review,
            request=self.request, token_evidence=self.count, campaign=self.campaign)

    def claim(self, authorization):
        return self.campaign.claim_paid_dispatch_host_authorized(
            "EV-01", self.review, self.request, request_id=self.uuid,
            namespace=NAMESPACE_ID, host_authorization=authorization,
            token_evidence=self.count, archive=self.archive, dispatch_id=self.uuid)

    def counts(self):
        with sqlite3.connect(self.ledger_path) as db:
            return (db.execute("SELECT COUNT(*) FROM host_owner_claims").fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0])

    def namespace(self):
        legacy = self.root / "legacy-exchange"
        legacy.mkdir(exist_ok=True)
        P5TokenCountOrchestrator(exchange_path=legacy)._connect().close()
        namespace = EvaluationNamespace.mapping(legacy_exchange=legacy)
        namespace.create()
        return namespace

    def prepare_signed(self):
        namespace = self.namespace()
        issuer = Ed25519PrivateKey.generate()
        prepared = prepare_generation_proposal(
            namespace=namespace, campaign=self.campaign, archive=self.archive,
            case=self.case, review=self.review, request=self.request,
            token_evidence=self.count, signer=issuer)
        proposal = json.loads(prepared.proposal_path.read_bytes())["body"]
        scope_fields = AUTH_FIELDS - {"version", "purpose", "nonce", "issued_at", "expires_at"}
        scope = {key: proposal[key] for key in scope_fields}
        proof = sign_owner_authorization(new_authorization_body(scope), self.host_private)
        return namespace, issuer, prepared, proof

    def test_valid_host_proof_claims_once_and_restarts(self):
        self.intent()
        proof = self.signed()
        attempt = self.claim(proof)
        self.assertTrue(attempt)
        self.assertEqual(self.counts(), (1, 1))
        restarted = EightCallCampaign(self.ledger_path)
        with self.assertRaises(CampaignBlocked):
            restarted.claim_paid_dispatch_host_authorized(
                "EV-01", self.review, self.request, request_id=self.uuid,
                namespace=NAMESPACE_ID, host_authorization=proof,
                token_evidence=self.count, archive=self.archive, dispatch_id=self.uuid)
        self.assertEqual(self.counts(), (1, 1))

    def test_missing_invalid_or_cross_request_proof_never_claims(self):
        self.intent()
        for proof in (b"", self.signed({**self.scope(), "case_id": "EV-02"}),
                      self.signed({**self.scope(), "payload_sha256": "0" * 64}),
                      self.signed({**self.scope(), "run_id": "other-run"}),
                      self.signed({**self.scope(), "request_id": str(uuid.uuid4())})):
            with self.subTest(proof=proof[:20]), self.assertRaises(CampaignBlocked):
                self.claim(proof)
        self.assertEqual(self.counts(), (0, 0))

    def test_intent_failure_and_ledger_rollback(self):
        proof = self.signed()
        with self.assertRaises(CampaignBlocked):
            self.claim(proof)
        self.assertEqual(self.counts(), (0, 0))
        self.intent()
        with sqlite3.connect(self.ledger_path) as db:
            db.execute("DROP TABLE host_owner_claims")
        with self.assertRaises(sqlite3.Error):
            self.claim(proof)
        with sqlite3.connect(self.ledger_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0], 0)

    def test_trusted_proposal_to_final_permit_uses_same_identity(self):
        namespace, issuer, prepared, proof = self.prepare_signed()
        final = finalize_generation_dispatch(
            prepared=prepared, host_authorization=proof,
            namespace=namespace, campaign=self.campaign, archive=self.archive,
            case=self.case, review=self.review, request=self.request,
            token_evidence=self.count, signer=issuer)
        package = json.loads(final.package_path.read_bytes())
        permit_raw = canonical_json_bytes(package["permit"])
        verified = verify_signed_permit(permit_raw, issuer.public_key())
        self.assertEqual(verified.body["request_id"], prepared.request_id)
        self.assertEqual(verified.body["count_request_id"], self.count.runner_request_id)
        self.assertEqual(verified.body["proposal_sha256"], prepared.proposal_sha256)
        self.assertEqual(verified.body["host_authorization_sha256"],
                         hashlib.sha256(proof).hexdigest())
        self.assertEqual(self.counts(), (1, 1))
        with self.assertRaises(CampaignBlocked):
            self.claim(proof)

    def test_invalid_host_proof_never_issues_final_package(self):
        namespace, issuer, prepared, proof = self.prepare_signed()
        with self.assertRaises(CampaignBlocked):
            finalize_generation_dispatch(
                prepared=prepared, host_authorization=b"{}",
                namespace=namespace, campaign=self.campaign, archive=self.archive,
                case=self.case, review=self.review, request=self.request,
                token_evidence=self.count, signer=issuer)
        self.assertEqual(self.counts(), (0, 0))
        self.assertFalse((namespace.container_exchange / "generation" / "requests" /
                          f"{prepared.request_id}.json").exists())
        with self.assertRaises(Exception):
            prepare_generation_proposal(
                namespace=namespace, campaign=self.campaign, archive=self.archive,
                case=self.case, review=self.review, request=self.request,
                token_evidence=self.count, signer=issuer)


if __name__ == "__main__":
    unittest.main()
