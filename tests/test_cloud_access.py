"""Synthetic Cloud access tests; no real passwords, keys or API calls."""
import unittest
from unittest.mock import patch

from src.ai_copilot.cloud_access import (
    AccessConfigurationError, ai_access_authorized, authenticate_ai_access,
    check_ai_access_attempt, password_verifier, verify_ai_access,
)


class CloudAccessTests(unittest.TestCase):
    def setUp(self):
        self.password = "offline-test-password-only"
        salt = bytes(range(32))
        self.settings = {
            "AI_ACCESS_SALT_HEX": salt.hex(),
            "AI_ACCESS_SCRYPT_HEX": password_verifier(self.password, salt).hex(),
        }

    def test_exact_password_only(self):
        self.assertTrue(verify_ai_access(self.password, self.settings))
        self.assertFalse(verify_ai_access("incorrect", self.settings))
        self.assertFalse(verify_ai_access("", self.settings))

    def test_missing_and_malformed_configuration_fails_closed(self):
        for settings in ({}, {"AI_ACCESS_SALT_HEX": "00"},
                         {"AI_ACCESS_SALT_HEX": "zz", "AI_ACCESS_SCRYPT_HEX": "zz"}):
            with self.subTest(settings=list(settings)):
                with self.assertRaises(AccessConfigurationError):
                    verify_ai_access(self.password, settings)

    def test_scope_is_exact_verifier_not_plaintext(self):
        altered = dict(self.settings, AI_ACCESS_SCRYPT_HEX="00" * 32)
        self.assertFalse(verify_ai_access(self.password, altered))
        self.assertNotIn(self.password, repr(self.settings))

    def test_five_failures_lock_session_without_storing_password(self):
        session = {}
        for _ in range(5):
            self.assertFalse(check_ai_access_attempt("bad", self.settings, session, now=100.0))
        self.assertFalse(check_ai_access_attempt(self.password, self.settings, session, now=101.0))
        self.assertNotIn(self.password, repr(session))
        self.assertTrue(check_ai_access_attempt(self.password, self.settings, session, now=1001.0))

    def test_signed_grant_rejects_mutable_session_flags_expiry_and_rotation(self):
        session = {"_ai_access_until": 99999}
        self.assertFalse(ai_access_authorized(session, self.settings, now=100))
        self.assertTrue(authenticate_ai_access(self.password, self.settings, session, now=100))
        self.assertTrue(ai_access_authorized(session, self.settings, now=101))
        self.assertNotIn(self.password, repr(session))
        original = dict(session)
        session["_ai_access_until"] = 99999
        self.assertFalse(ai_access_authorized(session, self.settings, now=101))
        session = dict(original)
        session["_ai_access_grant"] = "0" * 64
        self.assertFalse(ai_access_authorized(session, self.settings, now=101))
        self.assertFalse(ai_access_authorized(original, self.settings, now=1900))
        self.assertFalse(ai_access_authorized(original, {}, now=101))
        rotated = dict(self.settings, AI_ACCESS_SCRYPT_HEX="11" * 32)
        self.assertFalse(ai_access_authorized(original, rotated, now=101))
        self.assertFalse(ai_access_authorized({"_ai_access_until": "bad"}, self.settings, now=101))
        with patch("src.ai_copilot.cloud_access._GRANT_KEY", b"different-process-test-key" * 2):
            self.assertFalse(ai_access_authorized(original, self.settings, now=101))


if __name__ == "__main__":
    unittest.main()
