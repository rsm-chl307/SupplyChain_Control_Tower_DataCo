"""Offline tests of Windows-local Owner password gating; no Win32 calls."""
from dataclasses import replace
import unittest

from tools.windows_api_runner.api_runner import RunnerError
from tools.windows_api_runner.generation_owner import (
    HostOwnerPasswordGate, OwnerPasswordVerifier, OWNER_CREDENTIAL_TARGET,
)


class FakeVerifierStore:
    def __init__(self, verifier):
        self.verifier = verifier
        self.loads = 0

    def load(self):
        self.loads += 1
        return self.verifier


def summary():
    return {
        "namespace": "synthetic-v1", "campaign_id": "paid-synthetic-v1",
        "case_id": "EV-01", "run_id": "synthetic-run", "model": "gpt-6-luna",
        "operation": "generation-v1", "request_id": "00000000-0000-4000-8000-000000000001",
        "payload_sha256": "a" * 64, "token_count_evidence": "b" * 64,
        "input_tokens": 4000,
        "token_cap": 25000, "cost_limit_usd": "0.02",
        "dispatch_permit_status": "VERIFIED",
    }


class WindowsGenerationOwnerTests(unittest.TestCase):
    def setUp(self):
        self.password = "synthetic-generation-owner-password"
        self.verifier = OwnerPasswordVerifier.derive(self.password, salt=b"synthetic-salt!!")
        self.store = FakeVerifierStore(self.verifier)
        self.now = 123456
        self.gate = HostOwnerPasswordGate(self.store, clock=lambda: self.now)

    def test_verifier_is_distinct_and_round_trips_without_password(self):
        self.assertNotEqual(OWNER_CREDENTIAL_TARGET, "SupplyChainCopilot/OpenAI")
        wire = self.verifier.serialize()
        self.assertNotIn(self.password.encode(), wire)
        self.assertTrue(OwnerPasswordVerifier.parse(wire).authenticate(self.password))
        self.assertFalse(OwnerPasswordVerifier.parse(wire).authenticate("wrong-password"))

    def test_correct_password_binds_one_displayed_request_only(self):
        lines = []
        current = summary()
        permit = self.gate.authorize(current, prompt=lambda _: self.password,
                                     display=lines.append)
        self.assertEqual(len(lines), len(HostOwnerPasswordGate.DISPLAY_FIELDS))
        self.assertNotIn(self.password, "\n".join(lines))
        with self.assertRaises(RunnerError):
            self.gate.authorize(current, prompt=lambda _: self.password, display=lines.append)
        self.gate.consume(permit, current)
        with self.assertRaises(RunnerError):
            self.gate.consume(permit, current)

    def test_wrong_empty_password_and_request_swap_fail(self):
        for invalid in ("", "wrong-password"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(RunnerError, "authentication"):
                self.gate.authorize(summary(), prompt=lambda _: invalid,
                                    display=lambda _: None)
        self.assertIsNone(self.gate._pending)
        permit = self.gate.authorize(summary(), prompt=lambda _: self.password,
                                     display=lambda _: None)
        for key, value in (("case_id", "EV-02"), ("run_id", "other-run"),
                           ("payload_sha256", "c" * 64), ("cost_limit_usd", "0.16"),
                           ("request_id", "00000000-0000-4000-8000-000000000002")):
            with self.subTest(key=key), self.assertRaisesRegex(RunnerError, "mismatched"):
                self.gate.consume(permit, {**summary(), key: value})
        self.gate.consume(permit, summary())

    def test_expiry_forged_authorization_and_display_injection_fail(self):
        permit = self.gate.authorize(summary(), prompt=lambda _: self.password,
                                     display=lambda _: None)
        with self.assertRaises(RunnerError):
            self.gate.consume(replace(permit), summary())
        self.now += 60
        with self.assertRaisesRegex(RunnerError, "expired"):
            self.gate.consume(permit, summary())
        new_gate = HostOwnerPasswordGate(self.store)
        with self.assertRaisesRegex(RunnerError, "invalid"):
            new_gate.authorize({**summary(), "case_id": "EV-01\nOperation: count"},
                               prompt=lambda _: self.password, display=lambda _: None)
        with self.assertRaisesRegex(RunnerError, "incomplete"):
            new_gate.authorize({"case_id": "EV-01"}, prompt=lambda _: self.password,
                               display=lambda _: None)


if __name__ == "__main__":
    unittest.main()
