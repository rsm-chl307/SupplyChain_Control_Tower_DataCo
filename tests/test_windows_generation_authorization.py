"""Synthetic Host Owner Authorization signature and exact-scope tests."""
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes
from tools.windows_api_runner.generation_authorization import (
    new_authorization_body, sign_owner_authorization, verify_owner_authorization,
)


def scope():
    return {
        "namespace": "p5-eight-scenario-evaluation-v1",
        "campaign_id": "paid-p5-eight-scenario-evaluation-v1",
        "case_id": "EV-01", "run_id": "synthetic-run-001",
        "request_id": "00000000-0000-4000-8000-000000000001",
        "model": "gpt-6-luna", "payload_sha256": "a" * 64,
        "count_evidence_sha256": "b" * 64,
        "count_projection_sha256": "c" * 64,
        "provider_request_digest": "d" * 64, "brief_digest": "e" * 64,
        "token_cap": 25000, "cost_limit_micro_usd": 20000,
    }


class HostAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000000
        self.key = Ed25519PrivateKey.generate()
        self.body = new_authorization_body(scope(), now=self.now)
        self.raw = sign_owner_authorization(self.body, self.key, now=self.now)

    def test_valid_signature_and_unique_nonce(self):
        verified = verify_owner_authorization(self.raw, self.key.public_key(),
                                               expected=scope(), now=self.now)
        self.assertEqual(verified.body["request_id"], scope()["request_id"])
        self.assertNotEqual(self.body["nonce"], new_authorization_body(scope(), now=self.now)["nonce"])

    def test_tamper_and_cross_request_rejected(self):
        for key, value in (("case_id", "EV-02"), ("run_id", "other-run"),
                           ("payload_sha256", "f" * 64),
                           ("request_id", "00000000-0000-4000-8000-000000000002")):
            with self.subTest(key=key):
                expected = {**scope(), key: value}
                with self.assertRaisesRegex(RunnerError, "current request"):
                    verify_owner_authorization(self.raw, self.key.public_key(),
                                               expected=expected, now=self.now)
        envelope = json.loads(self.raw)
        envelope["body"]["case_id"] = "EV-02"
        with self.assertRaisesRegex(RunnerError, "signature"):
            verify_owner_authorization(canonical_json_bytes(envelope), self.key.public_key(),
                                       expected={**scope(), "case_id": "EV-02"}, now=self.now)

    def test_wrong_key_expiry_and_invalid_purpose(self):
        with self.assertRaises(RunnerError):
            verify_owner_authorization(self.raw, Ed25519PrivateKey.generate().public_key(),
                                       expected=scope(), now=self.now)
        with self.assertRaisesRegex(RunnerError, "expired"):
            verify_owner_authorization(self.raw, self.key.public_key(),
                                       expected=scope(), now=self.now + 300)
        changed = dict(self.body, purpose="general-session")
        with self.assertRaises(RunnerError):
            sign_owner_authorization(changed, self.key, now=self.now)


if __name__ == "__main__":
    unittest.main()
