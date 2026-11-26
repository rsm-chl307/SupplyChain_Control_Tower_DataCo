"""Stage 4 UI E2E with synthetic password and FakeProvider only."""
import socket
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from dashboard import copilot_view
from src.ai_copilot.cloud_access import password_verifier
from src.ai_copilot.provider import FakeProvider, ProviderResult


APP = "dashboard/scenario_planning_app.py"
SUBMIT = "FormSubmitter:copilot_ai_access-Unlock AI preview"
TEST_PASSWORD = "offline-test-password-only"


class Stage4CloudAITests(unittest.TestCase):
    def setUp(self):
        deny = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        deny.start()
        self.addCleanup(deny.stop)
        salt = bytes(range(32))
        settings = {"AI_ACCESS_SALT_HEX": salt.hex(),
                    "AI_ACCESS_SCRYPT_HEX": password_verifier(TEST_PASSWORD, salt).hex()}
        self.fake_verifier = settings["AI_ACCESS_SCRYPT_HEX"]
        setting_patch = patch.object(copilot_view, "ai_settings", return_value=settings)
        setting_patch.start()
        self.addCleanup(setting_patch.stop)
        self.app = AppTest.from_file(APP, default_timeout=60).run()

    def _enter(self):
        self.app.radio(key="ui_workspace").set_value("Decision Copilot").run()
        self.assertFalse(self.app.exception)

    def _submit(self, password):
        self.app.text_input(key="copilot_ai_password").set_value(password)
        self.app.button(key=SUBMIT).click().run()
        self.assertFalse(self.app.exception)

    def _prepare(self):
        self.app.button(key="copilot_start").click().run()
        self.app.button(key="copilot_prepare").click().run()
        self.assertFalse(self.app.exception)

    def test_public_dashboard_wrong_password_then_fake_question_and_followup(self):
        self.assertEqual(self.app.radio(key="ui_workspace").value, "Planning")
        self._enter()
        self.assertFalse(any(button.key == "copilot_start" for button in self.app.button))
        with patch.object(FakeProvider, "execute", side_effect=AssertionError("Provider called before auth")):
            self._submit("incorrect")
        self.assertFalse(any(button.key == "copilot_start" for button in self.app.button))
        self._submit(TEST_PASSWORD)
        self.assertNotIn(TEST_PASSWORD, repr(self.app.session_state))
        self.assertNotIn(self.fake_verifier, repr(self.app.session_state))
        self.assertFalse(any(button.key == "copilot_ask" for button in self.app.button))
        self._prepare()
        self.app.text_area(key="copilot_question").set_value("Why has service level declined?")
        self.app.button(key="copilot_ask").click().run()
        self.assertEqual(self.app.session_state["copilot_result"].status, "VALIDATED")
        first = self.app.session_state["copilot_chat"][0]
        self.assertEqual(len(first["digest"]), 64)
        self.app.text_area(key="copilot_question").set_value("What should management review next?")
        self.app.button(key="copilot_ask").click().run()
        self.assertEqual(len(self.app.session_state["copilot_chat"]), 2)
        self.assertNotEqual(first["digest"], self.app.session_state["copilot_chat"][1]["digest"])
        self.assertFalse(self.app.exception)

    def test_lockout_and_expiry_fail_closed(self):
        self._enter()
        for _ in range(5):
            self._submit("incorrect")
        self.assertFalse(any(button.key == "copilot_start" for button in self.app.button))
        self.assertFalse(any(button.key == "copilot_ask" for button in self.app.button))
        self.assertNotIn("incorrect", repr(self.app.session_state))
        # A fresh browser session is not authenticated either.
        fresh = AppTest.from_file(APP, default_timeout=60).run()
        fresh.radio(key="ui_workspace").set_value("Decision Copilot").run()
        self.assertFalse(any(button.key == "copilot_start" for button in fresh.button))

    def test_missing_config_and_session_expiration(self):
        with patch.object(copilot_view, "ai_settings", return_value={}):
            self._enter()
            self._submit(TEST_PASSWORD)
            self.assertFalse(any(button.key == "copilot_start" for button in self.app.button))
        self._submit(TEST_PASSWORD)
        self.assertTrue(any(button.key == "copilot_start" for button in self.app.button))
        self._prepare()
        self.assertIn("copilot_harness", self.app.session_state)
        self.app.session_state["_ai_access_until"] = 0
        self.app.run()
        self.assertFalse(any(button.key == "copilot_start" for button in self.app.button))
        self.assertNotIn("copilot_harness", self.app.session_state)

    def test_malformed_response_and_timeout_are_not_advisory_success(self):
        self._enter()
        self._submit(TEST_PASSWORD)
        self._prepare()
        self.app.text_area(key="copilot_question").set_value("Inspect capacity")
        with patch.object(copilot_view, "fake_result", return_value=ProviderResult("SUCCEEDED", b"{}")):
            self.app.button(key="copilot_ask").click().run()
        # Stage 5 backend gate discards an invalid result instead of retaining
        # a response object that the UI could accidentally render later.
        self.assertNotIn("copilot_result", self.app.session_state)
        self.app.text_area(key="copilot_question").set_value("Inspect service risk")
        with patch.object(copilot_view.FakeProvider, "execute", side_effect=TimeoutError):
            self.app.button(key="copilot_ask").click().run()
        self.assertNotIn("copilot_result", self.app.session_state)
        self.assertFalse(self.app.exception)


if __name__ == "__main__":
    unittest.main()
