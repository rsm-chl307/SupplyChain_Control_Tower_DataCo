"""Host-owned Fake evidence and ephemeral-key External Issuer tests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import secrets
import sqlite3
import time
import unittest

from tools.windows_api_runner.api_runner import HttpResult, RunnerError, canonical_json_bytes
from tools.windows_api_runner.external_issuer import (
    ExternalIssuer, FakeHostEvidenceStore, ISSUER_REQUEST_VERSION,
    process_fake_exchange_once, verify_external_issuer_response,
)
from tools.windows_api_runner.generation_permit import verify_signed_permit
from tests.test_windows_generation_ledger import HostClaimTests
from src.ai_copilot.generation_issuer_setup import provision_issuer_key
from src.ai_copilot.windows_generation_dispatch import (
    GenerationDispatchBlocked, load_p5_issuer_signer, prepare_generation_proposal,
)


class ExternalIssuerFakeTests(unittest.TestCase):
    def setUp(self):
        fixture = HostClaimTests("test_valid_host_proof_claims_once_and_restarts")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.namespace, self.issuer_key, self.prepared, self.proof = fixture.prepare_signed()
        self.proposal = json.loads(self.prepared.proposal_path.read_bytes())
        self.body = self.proposal["body"]
        self.evidence_path = fixture.root / "host-owned-fake-evidence.sqlite3"
        self.evidence = FakeHostEvidenceStore(self.evidence_path)
        self.service = ExternalIssuer(
            issuer_key=self.issuer_key,
            owner_public_key=fixture.host_private.public_key(),
            evidence=self.evidence)

    def request(self, **changes):
        current = int(time.time())
        body = {
            "version": ISSUER_REQUEST_VERSION, "request_id": self.prepared.request_id,
            "nonce": secrets.token_hex(24), "issued_at": current,
            "expires_at": current + 180,
            "proposal": self.proposal,
            "host_authorization": json.loads(self.proof),
        }
        body.update(changes)
        return canonical_json_bytes(body)

    def register(self, **changes):
        fields = {
            "request_id": self.prepared.request_id,
            "proposal_sha256": self.prepared.proposal_sha256,
            "ledger_attempt_id": self.body["ledger_attempt_id"],
            "archive_intent_digest": self.body["archive_intent_digest"],
        }
        fields.update(changes)
        self.evidence.register_fake_evidence(**fields)

    def test_signed_permit_requires_independent_claim_and_intent(self):
        raw = self.request()
        with self.assertRaisesRegex(RunnerError, "Ledger Claim"):
            self.service.issue(raw)
        self.register()
        response = self.service.issue(raw)
        permit_raw = verify_external_issuer_response(
            response, raw, self.issuer_key.public_key())
        permit = verify_signed_permit(permit_raw, self.issuer_key.public_key())
        self.assertEqual(permit.body["request_id"], self.prepared.request_id)
        self.assertEqual(permit.body["archive_intent_digest"], self.body["archive_intent_digest"])
        with self.assertRaisesRegex(RunnerError, "already consumed"):
            self.service.issue(raw)
        reopened = FakeHostEvidenceStore(self.evidence_path)
        restarted = ExternalIssuer(issuer_key=self.issuer_key,
            owner_public_key=self.fixture.host_private.public_key(), evidence=reopened)
        with self.assertRaisesRegex(RunnerError, "already consumed"):
            restarted.issue(raw)

    def test_claim_and_intent_mismatch_fail_closed(self):
        self.register(ledger_attempt_id="wrong-attempt",
                      archive_intent_digest="0" * 64)
        with self.assertRaisesRegex(RunnerError, "Ledger Claim"):
            self.service.issue(self.request())
        with sqlite3.connect(self.evidence_path) as db:
            db.execute("UPDATE fake_claims SET ledger_attempt_id=?",
                       (self.body["ledger_attempt_id"],))
        with self.assertRaisesRegex(RunnerError, "Archive Intent"):
            self.service.issue(self.request())
        with sqlite3.connect(self.evidence_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM issuer_uses").fetchone()[0], 0)

    def test_expired_host_owned_claim_and_intent_fail_closed(self):
        self.register(issued_at=1, expires_at=2)
        raw = self.request()
        with self.assertRaisesRegex(RunnerError, "Ledger Claim"):
            self.service.issue(raw)
        current = int(time.time())
        with sqlite3.connect(self.evidence_path) as db:
            db.execute("UPDATE fake_claims SET issued_at=?,expires_at=?",
                       (current, current + 180))
        with self.assertRaisesRegex(RunnerError, "Archive Intent"):
            self.service.issue(raw)

    def test_corrupt_request_owner_proof_and_response_rejected(self):
        self.register()
        for changed in ({"version": "unknown"},
                        {"request_id": "00000000-0000-4000-8000-000000000001"},
                        {"expires_at": 1}):
            with self.subTest(changed=changed), self.assertRaises(RunnerError):
                self.service.issue(self.request(**changed))
        request = json.loads(self.request())
        request["host_authorization"]["signature"] = "invalid"
        with self.assertRaises(RunnerError):
            self.service.issue(canonical_json_bytes(request))
        raw = self.request()
        response = self.service.issue(raw)
        corrupted = json.loads(response)
        corrupted["request_sha256"] = "0" * 64
        with self.assertRaises(RunnerError):
            verify_external_issuer_response(canonical_json_bytes(corrupted),
                                            raw, self.issuer_key.public_key())

    def test_concurrent_duplicate_issuance_has_one_durable_winner(self):
        self.register()
        raw = self.request()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self._attempt(raw), range(2)))
        self.assertEqual(sorted(results), ["REJECTED", "SIGNED"])
        with sqlite3.connect(self.evidence_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM issuer_uses").fetchone()[0], 1)

    def test_response_persistence_failure_keeps_one_use_claim(self):
        self.register()
        raw = self.request()
        root = self.fixture.root / "isolated-issuer-exchange"
        inbox = root / "requests"
        inbox.mkdir(parents=True)
        (inbox / f"{self.prepared.request_id}.json").write_bytes(raw)
        # An invalid outbox simulates a failure after durable permit issuance.
        (root / "responses").write_text("blocked", encoding="utf-8")
        with self.assertRaisesRegex(RunnerError, "persistence is uncertain"):
            process_fake_exchange_once(self.service, root, self.prepared.request_id)
        with sqlite3.connect(self.evidence_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM issuer_uses").fetchone()[0], 1)
        with self.assertRaisesRegex(RunnerError, "already consumed"):
            self.service.issue(raw)

    def test_issued_permit_is_accepted_by_existing_fake_generation_host(self):
        from tests.test_windows_generation_host import (
            FakeCredentials, FakeTransport, FakeVerifierStore,
        )
        from tools.windows_api_runner.generation_host import HostGenerationExecutor
        from tools.windows_api_runner.generation_owner import HostOwnerPasswordGate
        from tools.windows_api_runner.generation_permit import HostGenerationPermitState

        self.register()
        raw = self.request()
        response = self.service.issue(raw)
        permit_raw = verify_external_issuer_response(
            response, raw, self.issuer_key.public_key())
        package = canonical_json_bytes({
            "version": "p5-generation-execution-package-1",
            "proposal": self.proposal,
            "host_authorization": json.loads(self.proof),
            "permit": json.loads(permit_raw),
        })
        credentials = FakeCredentials()
        transport = FakeTransport(HttpResult(200, "req-synthetic-issuer",
            canonical_json_bytes({
                "id": "resp-synthetic-issuer", "model": "gpt-6-luna",
                "status": "completed", "output": [],
                "usage": {"input_tokens": 4000, "output_tokens": 50,
                          "total_tokens": 4050},
            })))
        executor = HostGenerationExecutor(
            issuer_public_key=self.issuer_key.public_key(),
            signing_key=self.fixture.host_private,
            owner_gate=HostOwnerPasswordGate(FakeVerifierStore()),
            state=HostGenerationPermitState(self.fixture.root / "fake-host.sqlite3"),
            credential_store=credentials, transport=transport,
            exchange=self.fixture.root / "fake-host-exchange")
        result = executor.dispatch(package)
        self.assertEqual(result["request_id"], self.prepared.request_id)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(credentials.calls, 1)
        with self.assertRaises(RunnerError):
            executor.dispatch(package)
        self.assertEqual(transport.calls, 1)

    def _attempt(self, raw):
        try:
            self.service.issue(raw)
            return "SIGNED"
        except RunnerError:
            return "REJECTED"


class LegacyFormalSignerDisabledTests(unittest.TestCase):
    def test_container_formal_key_loading_and_provisioning_fail_closed(self):
        with self.assertRaisesRegex(GenerationDispatchBlocked, "disabled"):
            load_p5_issuer_signer()
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            provision_issuer_key(None)

    def test_prepare_without_external_issuer_cannot_sign_or_append_intent(self):
        fixture = HostClaimTests("test_valid_host_proof_claims_once_and_restarts")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        namespace = fixture.namespace()
        with self.assertRaisesRegex(GenerationDispatchBlocked, "disabled"):
            prepare_generation_proposal(
                namespace=namespace, campaign=fixture.campaign, archive=fixture.archive,
                case=fixture.case, review=fixture.review, request=fixture.request,
                token_evidence=fixture.count)
        with sqlite3.connect(fixture.archive_path) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM archive_dispatch_events").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
