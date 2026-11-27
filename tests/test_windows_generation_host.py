"""Isolated Host Generation handshake and Fake transport; no Win32 or HTTP."""
import base64
import hashlib
import json
import unittest
from unittest.mock import patch

from tools.windows_api_runner.api_runner import HttpResult, RunnerError, canonical_json_bytes
from tools.windows_api_runner.generation_host import (
    FixedGenerationTransport, HostGenerationExecutor, REAL_GENERATION_DISPATCH_LOCKED,
)
from tools.windows_api_runner.generation_owner import HostOwnerPasswordGate, OwnerPasswordVerifier
from tools.windows_api_runner.generation_permit import HostGenerationPermitState
from src.ai_copilot.windows_generation_dispatch import (
    collect_generation_response, finalize_generation_dispatch,
)
from tests import test_windows_generation_ledger as ledger_tests


class FakeVerifierStore:
    def load(self):
        return OwnerPasswordVerifier.derive("synthetic-owner-password-long", salt=b"0123456789abcdef")


class FakeCredentials:
    def __init__(self):
        self.calls = 0

    def get_api_key(self):
        self.calls += 1
        return "synthetic-in-memory-only"


class FakeTransport:
    def __init__(self, result=None, error=None):
        self.calls = 0
        self.result = result
        self.error = error

    def post(self, body, api_key):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class HostGenerationTests(unittest.TestCase):
    def setUp(self):
        fixture = ledger_tests.HostClaimTests("test_valid_host_proof_claims_once_and_restarts")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.namespace, self.issuer, self.prepared, _ = fixture.prepare_signed()
        self.credentials = FakeCredentials()
        self.transport = FakeTransport()
        self.host_exchange = fixture.root / "host-generation-exchange"
        self.state_path = fixture.root / "host-generation-state.sqlite3"
        self.executor = HostGenerationExecutor(
            issuer_public_key=self.issuer.public_key(), signing_key=fixture.host_private,
            owner_gate=HostOwnerPasswordGate(FakeVerifierStore()),
            state=HostGenerationPermitState(self.state_path),
            credential_store=self.credentials, transport=self.transport,
            exchange=self.host_exchange)

    def authorized_package(self):
        proof = self.executor.authorize(self.prepared.proposal_path.read_bytes(),
                                        prompt=lambda _: "synthetic-owner-password-long",
                                        display=lambda _: None)
        final = finalize_generation_dispatch(
            prepared=self.prepared, host_authorization=proof,
            namespace=self.namespace, campaign=self.fixture.campaign,
            archive=self.fixture.archive, case=self.fixture.case,
            review=self.fixture.review, request=self.fixture.request,
            token_evidence=self.fixture.count, signer=self.issuer)
        return final, final.package_path.read_bytes()

    def test_real_host_transport_is_locked_before_credential_access(self):
        self.assertTrue(REAL_GENERATION_DISPATCH_LOCKED)
        executor = HostGenerationExecutor(
            issuer_public_key=self.issuer.public_key(),
            signing_key=self.fixture.host_private,
            owner_gate=HostOwnerPasswordGate(FakeVerifierStore()),
            state=HostGenerationPermitState(self.fixture.root / "locked-host-state.sqlite3"),
            credential_store=self.credentials,
            transport=FixedGenerationTransport(),
            exchange=self.host_exchange,
        )
        with patch.object(FixedGenerationTransport, "post",
                          side_effect=AssertionError("network")):
            with self.assertRaisesRegex(RunnerError, "separate Owner authorization"):
                executor.dispatch(b"invalid package")
        self.assertEqual(self.credentials.calls, 0)

    def test_one_password_proof_and_one_fake_dispatch(self):
        final, package = self.authorized_package()
        fake_body = {"id": "resp-fake-1", "model": "gpt-6-luna", "status": "completed",
                     "usage": {"input_tokens": 4000, "output_tokens": 50,
                               "total_tokens": 4050}, "output": []}
        self.transport.result = HttpResult(200, "req-fake-generation-1",
                                           canonical_json_bytes(fake_body))
        record = self.executor.dispatch(package)
        self.assertEqual(record["request_id"], final.request_id)
        self.assertEqual(self.credentials.calls, 1)
        self.assertEqual(self.transport.calls, 1)
        self.assertIsNone(record["charge"])
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "SUCCEEDED")
        with self.assertRaises(RunnerError):
            self.executor.dispatch(package)
        self.assertEqual(self.transport.calls, 1)
        self.assertNotIn(b"synthetic-in-memory-only",
                         (self.host_exchange / "generation" / "responses" /
                          f"{final.request_id}.json").read_bytes())

    def test_changed_package_and_wrong_owner_password_fail_before_transport(self):
        with self.assertRaises(RunnerError):
            self.executor.authorize(self.prepared.proposal_path.read_bytes(),
                                    prompt=lambda _: "incorrect", display=lambda _: None)
        self.assertEqual(self.credentials.calls, 0)
        final, package = self.authorized_package()
        changed = json.loads(package)
        changed["proposal"]["body"]["payload"]["input"] = "tampered"
        with self.assertRaises(RunnerError):
            self.executor.dispatch(canonical_json_bytes(changed))
        self.assertEqual(self.transport.calls, 0)
        self.assertEqual(self.credentials.calls, 0)

    def test_transport_uncertain_and_restart_never_redispatch(self):
        final, package = self.authorized_package()
        self.transport.error = TimeoutError("synthetic timeout")
        with self.assertRaisesRegex(RunnerError, "UNKNOWN"):
            self.executor.dispatch(package)
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "UNKNOWN")
        second = HostGenerationExecutor(
            issuer_public_key=self.issuer.public_key(),
            signing_key=self.fixture.host_private,
            owner_gate=HostOwnerPasswordGate(FakeVerifierStore()),
            state=HostGenerationPermitState(self.state_path),
            credential_store=self.credentials, transport=self.transport,
            exchange=self.host_exchange)
        with self.assertRaises(RunnerError):
            second.dispatch(package)
        self.assertEqual(self.transport.calls, 1)

    def test_missing_host_response_holds_ledger_without_redispatch(self):
        final, package = self.authorized_package()
        with self.assertRaisesRegex(Exception, "response missing"):
            collect_generation_response(
                final=final, namespace=self.namespace, campaign=self.fixture.campaign,
                archive=self.fixture.archive, case=self.fixture.case,
                review=self.fixture.review, request=self.fixture.request,
                token_evidence=self.fixture.count,
                signer_public_key=self.issuer.public_key())
        self.assertEqual(self.fixture.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.transport.calls, 0)

    def test_missing_credential_consumes_permit_before_transport(self):
        final, package = self.authorized_package()
        class MissingCredential:
            def get_api_key(self):
                raise RuntimeError("synthetic unavailable")
        self.executor.credential_store = MissingCredential()
        with self.assertRaisesRegex(RunnerError, "credential is unavailable"):
            self.executor.dispatch(package)
        self.assertEqual(self.transport.calls, 0)
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "FAILED_BEFORE_DISPATCH")
        with self.assertRaises(RunnerError):
            self.executor.dispatch(package)

    def test_invalid_credential_fails_before_transport_and_cannot_retry(self):
        final, package = self.authorized_package()
        class InvalidCredential:
            def get_api_key(self):
                return " synthetic-invalid-value\n"
        self.executor.credential_store = InvalidCredential()
        with self.assertRaisesRegex(RunnerError, "credential is invalid"):
            self.executor.dispatch(package)
        self.assertEqual(self.transport.calls, 0)
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "FAILED_BEFORE_DISPATCH")
        with self.assertRaises(RunnerError):
            self.executor.dispatch(package)

    def test_signed_response_tampering_is_rejected_and_held(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(200, "req-fake-generation-3",
            canonical_json_bytes({"id": "resp-fake-3", "model": "gpt-6-luna",
                                  "status": "completed", "output": []}))
        record = self.executor.dispatch(package)
        record["model"] = "different-model"
        destination = self.namespace.container_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(canonical_json_bytes(record))
        with self.assertRaisesRegex(Exception, "signature"):
            collect_generation_response(
                final=final, namespace=self.namespace, campaign=self.fixture.campaign,
                archive=self.fixture.archive, case=self.fixture.case,
                review=self.fixture.review, request=self.fixture.request,
                token_evidence=self.fixture.count,
                signer_public_key=self.issuer.public_key())
        self.assertEqual(self.fixture.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.transport.calls, 1)

    def test_archive_failure_holds_ledger_without_second_dispatch(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(400, "req-fake-generation-4",
            canonical_json_bytes({"error": {"type": "invalid_request_error"}}))
        self.executor.dispatch(package)
        source = self.host_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination = self.namespace.container_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        with patch.object(self.fixture.archive, "append_generation_result",
                          side_effect=RuntimeError("synthetic archive failure")):
            with self.assertRaisesRegex(Exception, "archive failed"):
                collect_generation_response(
                    final=final, namespace=self.namespace, campaign=self.fixture.campaign,
                    archive=self.fixture.archive, case=self.fixture.case,
                    review=self.fixture.review, request=self.fixture.request,
                    token_evidence=self.fixture.count,
                    signer_public_key=self.issuer.public_key())
        self.assertEqual(self.fixture.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.transport.calls, 1)

    def test_host_response_write_failure_is_unknown_and_not_retried(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(200, "req-fake-generation-5",
            canonical_json_bytes({"id": "resp-fake-5", "model": "gpt-6-luna",
                                  "status": "completed", "output": []}))
        with patch("tools.windows_api_runner.generation_host._write_once",
                   side_effect=OSError("synthetic write failure")):
            with self.assertRaisesRegex(RunnerError, "UNKNOWN"):
                self.executor.dispatch(package)
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "UNKNOWN")
        with self.assertRaises(RunnerError):
            self.executor.dispatch(package)
        self.assertEqual(self.transport.calls, 1)

    def test_fake_response_collects_with_ledger_held_for_charge(self):
        final, package = self.authorized_package()
        # Use a synthetic P1-shaped output tied to this exact trusted Brief.
        p1 = {"response_version": "1.0", "brief_digest": self.fixture.review.content_digest,
              "executive_assessment": {"summary": "Review capacity.",
                  "principal_concern": "Service pressure.", "evidence_refs": []},
              "key_findings": [], "root_cause_interpretation": {key: [] for key in
                  ("observed_facts", "system_identified_drivers", "ai_interpretations",
                   "unverified_hypotheses", "missing_evidence")},
              "recommendations": [], "decision_trade_offs": [], "further_investigation": [],
              "limitations_and_confidence": {"data_completeness": "Bounded evidence.",
                  "evidence_quality": "Published evidence.",
                  "directly_supported_conclusions": [], "inferences": [],
                  "unsupported_questions": [], "confidence": "Limited",
                  "confidence_rationale": "Evidence is bounded."}}
        fake = {"id": "resp-fake-2", "model": "gpt-6-luna", "status": "completed",
                "usage": {"input_tokens": 4000, "output_tokens": 50,
                          "total_tokens": 4050,
                          "input_tokens_details": {"cached_tokens": 0}},
                "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": json.dumps(p1)}]}]}
        self.transport.result = HttpResult(200, "req-fake-generation-2",
                                           canonical_json_bytes(fake))
        record = self.executor.dispatch(package)
        host_path = self.host_exchange / "generation" / "responses" / f"{final.request_id}.json"
        container_path = self.namespace.container_exchange / "generation" / "responses" / f"{final.request_id}.json"
        container_path.parent.mkdir(parents=True, exist_ok=True)
        container_path.write_bytes(host_path.read_bytes())
        result = collect_generation_response(
            final=final, namespace=self.namespace, campaign=self.fixture.campaign,
            archive=self.fixture.archive, case=self.fixture.case, review=self.fixture.review,
            request=self.fixture.request, token_evidence=self.fixture.count,
            signer_public_key=self.issuer.public_key())
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(self.fixture.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.fixture.archive.dispatch_events(final.request_id)[-1]["event_type"],
                         "GENERATION_RESULT")
        self.assertEqual(record["raw_response_sha256"],
                         hashlib.sha256(canonical_json_bytes(fake)).hexdigest())

    def test_claim_failure_and_revocation_never_reach_credentials(self):
        final, package = self.authorized_package()
        with patch.object(self.executor.state, "claim", side_effect=RunnerError("synthetic claim failure")):
            with self.assertRaisesRegex(RunnerError, "claim failure"):
                self.executor.dispatch(package)
        self.assertIsNone(HostGenerationPermitState(self.state_path).state(final.permit_sha256))
        self.assertEqual((self.credentials.calls, self.transport.calls), (0, 0))
        self.executor.state.revoke(final.permit_sha256)
        with self.assertRaisesRegex(RunnerError, "revoked"):
            self.executor.dispatch(package)
        self.assertEqual((self.credentials.calls, self.transport.calls), (0, 0))

    def test_signed_response_with_wrong_raw_digest_is_held(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(200, "req-fake-digest",
            canonical_json_bytes({"id": "resp-fake-digest", "model": "gpt-6-luna",
                                  "status": "completed", "output": []}))
        record = self.executor.dispatch(package)
        record["raw_response_sha256"] = "0" * 64
        signed = {key: value for key, value in record.items()
                  if key not in {"host_signature", "host_key_id"}}
        record["host_signature"] = base64.urlsafe_b64encode(
            self.fixture.host_private.sign(canonical_json_bytes(signed))).rstrip(b"=").decode()
        destination = self.namespace.container_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(canonical_json_bytes(record))
        with self.assertRaisesRegex(Exception, "digest mismatch"):
            collect_generation_response(
                final=final, namespace=self.namespace, campaign=self.fixture.campaign,
                archive=self.fixture.archive, case=self.fixture.case, review=self.fixture.review,
                request=self.fixture.request, token_evidence=self.fixture.count,
                signer_public_key=self.issuer.public_key())
        self.assertEqual(self.fixture.campaign.reservation("EV-01")["state"], "UNKNOWN")
        self.assertEqual(self.transport.calls, 1)

    def test_missing_usage_and_charge_remain_null_and_duplicate_collect_rejected(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(400, "req-fake-no-usage",
            canonical_json_bytes({"error": {"type": "synthetic_invalid_request"}}))
        record = self.executor.dispatch(package)
        self.assertIsNone(record["usage"])
        self.assertIsNone(record["charge"])
        self.assertIsNone(record["charge_source"])
        source = self.host_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination = self.namespace.container_exchange / "generation" / "responses" / f"{final.request_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        collect_generation_response(
            final=final, namespace=self.namespace, campaign=self.fixture.campaign,
            archive=self.fixture.archive, case=self.fixture.case, review=self.fixture.review,
            request=self.fixture.request, token_evidence=self.fixture.count,
            signer_public_key=self.issuer.public_key())
        with self.assertRaises(Exception):
            collect_generation_response(
                final=final, namespace=self.namespace, campaign=self.fixture.campaign,
                archive=self.fixture.archive, case=self.fixture.case, review=self.fixture.review,
                request=self.fixture.request, token_evidence=self.fixture.count,
                signer_public_key=self.issuer.public_key())
        self.assertEqual(len(self.fixture.archive.dispatch_events(final.request_id)), 2)
        self.assertEqual(self.transport.calls, 1)

    def test_credential_like_provider_body_is_not_persisted_or_retried(self):
        final, package = self.authorized_package()
        self.transport.result = HttpResult(200, "req-fake-secret-body",
                                           b'{"message":"Bearer synthetic-in-memory-only"}')
        with self.assertRaisesRegex(RunnerError, "credential-like"):
            self.executor.dispatch(package)
        self.assertEqual(HostGenerationPermitState(self.state_path).state(final.permit_sha256),
                         "UNKNOWN")
        self.assertFalse((self.host_exchange / "generation" / "responses" /
                          f"{final.request_id}.json").exists())
        with self.assertRaises(RunnerError):
            self.executor.dispatch(package)
        self.assertEqual(self.transport.calls, 1)


if __name__ == "__main__":
    unittest.main()
