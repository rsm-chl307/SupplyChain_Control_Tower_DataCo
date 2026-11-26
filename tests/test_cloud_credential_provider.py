"""Offline tests only: fake credentials and no runner/API dispatch."""
import unittest
import sys
import types
from unittest.mock import patch

from src.ai_copilot.credential_provider import (
    CredentialUnavailable, StreamlitSecretsCredential, credential_provider,
)


class CredentialProviderTests(unittest.TestCase):
    def test_cloud_provider_reads_only_explicit_fake_secret(self):
        fake = "sk-fake-credential-for-offline-unit-test"
        provider = credential_provider("streamlit_cloud", secrets={"OPENAI_API_KEY": fake})
        self.assertEqual(provider.get_api_key(), fake)
        self.assertIsInstance(provider, StreamlitSecretsCredential)

    def test_missing_cloud_secret_fails_closed(self):
        with self.assertRaisesRegex(CredentialUnavailable, "Streamlit Secrets") as caught:
            credential_provider("streamlit_cloud", secrets={}).get_api_key()
        self.assertNotIn("sk-", str(caught.exception))

    def test_invalid_secret_fails_closed(self):
        for value in (None, "", "has spaces", "has\nnewline", 42):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(CredentialUnavailable):
                    credential_provider("streamlit_cloud", secrets={"OPENAI_API_KEY": value}).get_api_key()

    def test_provider_selection_has_no_fallback(self):
        class FakeWindowsCredentialManager:
            pass

        fake_runner = types.ModuleType("tools.windows_api_runner.api_runner")
        fake_runner.WindowsCredentialManager = FakeWindowsCredentialManager
        fake_package = types.ModuleType("tools.windows_api_runner")
        with patch.dict(sys.modules, {
            "tools.windows_api_runner": fake_package,
            "tools.windows_api_runner.api_runner": fake_runner,
        }):
            self.assertIsInstance(credential_provider("windows"), FakeWindowsCredentialManager)
        with self.assertRaises(ValueError):
            credential_provider("windows", secrets={})
        with self.assertRaises(ValueError):
            credential_provider("unknown")


if __name__ == "__main__":
    unittest.main()
