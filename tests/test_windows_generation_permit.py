"""Fake key/temporary SQLite checks for the Host permit boundary."""
import base64
import hashlib
import tempfile
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes
from tools.windows_api_runner.generation_permit import (
    HostGenerationPermitState, PERMIT_OPERATION, PERMIT_VERSION,
    load_host_trust_anchor, verify_signed_permit,
)


def body(now):
    return {
        "version": PERMIT_VERSION, "operation": PERMIT_OPERATION,
        "namespace": "p5-eight-scenario-evaluation-v1",
        "campaign_id": "paid-p5-eight-scenario-evaluation-v1",
        "case_id": "EV-01", "run_id": "synthetic-run-001",
        "request_id": "00000000-0000-4000-8000-000000000001",
        "dispatch_id": "synthetic-dispatch-001", "model": "gpt-6-luna",
        "payload_sha256": "a" * 64, "count_payload_sha256": "b" * 64,
        "count_projection_sha256": "c" * 64,
        "count_evidence_sha256": "d" * 64, "count_request_id": "synthetic-count-001",
        "input_tokens": 4000, "token_cap": 25000,
        "provider_request_digest": "e" * 64, "brief_digest": "f" * 64,
        "approval_reference": "synthetic-approval-001",
        "paid_authorization_reference": "synthetic-paid-001",
        "ledger_attempt_id": "synthetic-attempt-001",
        "archive_intent_digest": "1" * 64,
        "host_authorization_sha256": "2" * 64,
        "proposal_sha256": "3" * 64,
        "cost_limit_micro_usd": 20000, "issued_at": now, "expires_at": now + 180,
    }


def sign(private, data):
    public = private.public_key()
    signature = private.sign(canonical_json_bytes(data))
    return canonical_json_bytes({
        "body": data,
        "key_id": hashlib.sha256(public.public_bytes_raw()).hexdigest(),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode(),
    })


class GenerationPermitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="generation-permit-fake-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key()
        self.now = 1000000
        self.raw = sign(self.private, body(self.now))
        self.state_path = self.root / "host-state.sqlite3"

    def test_signature_and_host_anchor(self):
        anchor = self.root / "pinned-public-key.bin"
        anchor.write_bytes(self.public.public_bytes_raw())
        key = load_host_trust_anchor(anchor)
        permit = verify_signed_permit(self.raw, key, now=self.now)
        self.assertEqual(permit.body["request_id"], body(self.now)["request_id"])
        self.assertEqual(permit.permit_sha256, hashlib.sha256(self.raw).hexdigest())
        with self.assertRaises(RunnerError):
            verify_signed_permit(self.raw, Ed25519PrivateKey.generate().public_key(), now=self.now)
        with self.assertRaises(RunnerError):
            load_host_trust_anchor(self.root / "missing-public-key.bin")

    def test_tampering_expiry_and_wrong_operation_fail(self):
        for changed in (
            {"payload_sha256": "2" * 64}, {"case_id": "EV-02"},
            {"request_id": "00000000-0000-4000-8000-000000000002"},
        ):
            import json
            envelope = json.loads(self.raw)
            envelope["body"].update(changed)
            with self.subTest(changed=changed), self.assertRaises(RunnerError):
                verify_signed_permit(canonical_json_bytes(envelope), self.public, now=self.now)
        with self.assertRaisesRegex(RunnerError, "expired"):
            verify_signed_permit(self.raw, self.public, now=self.now + 180)
        wrong = body(self.now)
        wrong["operation"] = "input_token_count"
        with self.assertRaises(RunnerError):
            verify_signed_permit(sign(self.private, wrong), self.public, now=self.now)
        for field, value in (("namespace", "other-namespace"),
                             ("campaign_id", "other-campaign"),
                             ("case_id", "EV-99")):
            wrong = body(self.now)
            wrong[field] = value
            with self.subTest(field=field), self.assertRaises(RunnerError):
                verify_signed_permit(sign(self.private, wrong), self.public, now=self.now)

    def test_claim_is_durable_one_use_after_restart(self):
        permit = verify_signed_permit(self.raw, self.public, now=self.now)
        store = HostGenerationPermitState(self.state_path)
        store.claim(permit, now=self.now)
        self.assertEqual(store.state(permit.permit_sha256), "CLAIMED")
        restarted = HostGenerationPermitState(self.state_path)
        with self.assertRaisesRegex(RunnerError, "already claimed"):
            restarted.claim(permit, now=self.now)
        restarted.transition(permit.permit_sha256, "CLAIMED", "IN_PROGRESS")
        self.assertEqual(store.state(permit.permit_sha256), "IN_PROGRESS")
        restarted.transition(permit.permit_sha256, "IN_PROGRESS", "UNKNOWN")
        with self.assertRaises(RunnerError):
            restarted.transition(permit.permit_sha256, "UNKNOWN", "IN_PROGRESS")
        with self.assertRaises(RunnerError):
            restarted.claim(permit, now=self.now)

    def test_revocation_and_cross_request_replay_rejected(self):
        permit = verify_signed_permit(self.raw, self.public, now=self.now)
        store = HostGenerationPermitState(self.state_path)
        store.revoke(permit.permit_sha256)
        with self.assertRaisesRegex(RunnerError, "revoked"):
            store.claim(permit, now=self.now)
        second = body(self.now)
        second["request_id"] = "00000000-0000-4000-8000-000000000002"
        second_permit = verify_signed_permit(sign(self.private, second), self.public,
                                              now=self.now)
        store.claim(second_permit, now=self.now)
        with self.assertRaises(RunnerError):
            store.revoke(second_permit.permit_sha256)
        third = body(self.now)
        third["request_id"] = "00000000-0000-4000-8000-000000000003"
        third_permit = verify_signed_permit(sign(self.private, third), self.public,
                                             now=self.now)
        with self.assertRaisesRegex(RunnerError, "already claimed"):
            store.claim(third_permit, now=self.now)

    def test_restart_reconciles_unfinished_claim_without_retry(self):
        permit = verify_signed_permit(self.raw, self.public, now=self.now)
        store = HostGenerationPermitState(self.state_path)
        store.claim(permit, now=self.now)
        restarted = HostGenerationPermitState(self.state_path)
        self.assertEqual(restarted.recover_unfinished(), 1)
        self.assertEqual(restarted.state(permit.permit_sha256), "UNKNOWN")
        self.assertEqual(restarted.recover_unfinished(), 0)
        with self.assertRaises(RunnerError):
            restarted.claim(permit, now=self.now)

    def test_restart_reconciles_in_progress_after_ambiguous_dispatch(self):
        permit = verify_signed_permit(self.raw, self.public, now=self.now)
        store = HostGenerationPermitState(self.state_path)
        store.claim(permit, now=self.now)
        store.transition(permit.permit_sha256, "CLAIMED", "IN_PROGRESS")
        restarted = HostGenerationPermitState(self.state_path)
        self.assertEqual(restarted.recover_unfinished(), 1)
        self.assertEqual(restarted.state(permit.permit_sha256), "UNKNOWN")
        with self.assertRaises(RunnerError):
            restarted.claim(permit, now=self.now)
        with self.assertRaises(RunnerError):
            restarted.transition(permit.permit_sha256, "UNKNOWN", "IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()
