"""Stage 6 fixed-endpoint provider tests; all transport and credentials are fake."""
import hashlib
import json
import socket
import unittest
from dataclasses import replace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.cloud_access import authenticate_ai_access, password_verifier
from src.ai_copilot.cloud_ai_service import CloudAIRejected, CloudAIService
from src.ai_copilot.cloud_question import (
    CloudHTTPResponse, CloudOpenAIProvider, CloudProviderFailure,
    HTTPSResponsesTransport, prepare_cloud_question,
)
from src.ai_copilot.credential_provider import StreamlitSecretsCredential
from dashboard.copilot_view import fake_result
from dashboard import copilot_view


class RecordingTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, payload, *, api_key, timeout_seconds):
        self.calls.append((payload, api_key, timeout_seconds))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class Stage6CloudProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SyntheticHarness()
        cls.review = prepare_brief(cls.harness, cls.harness.issue("Baseline")).review

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def setUp(self):
        denied = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        denied.start()
        self.addCleanup(denied.stop)
        salt = bytes(range(32))
        self.settings = {
            "AI_ACCESS_SALT_HEX": salt.hex(),
            "AI_ACCESS_SCRYPT_HEX": password_verifier("fake-password", salt).hex(),
            "AI_REAL_PROVIDER_ENABLED": True,
            "AI_MODEL_ID": "fake-model",
            "AI_PRICE_MODEL_ID": "fake-model",
            "AI_PRICE_INPUT_USD_PER_MILLION": "1",
            "AI_PRICE_OUTPUT_USD_PER_MILLION": "1",
            "AI_SESSION_ESTIMATED_USD_LIMIT": "1",
        }
        self.session = {}
        self.assertTrue(authenticate_ai_access("fake-password", self.settings, self.session, now=100))
        self.service = CloudAIService()
        self.question = "Why has service level declined?"
        self.secret = "synthetic-sentinel-only"

    def response(self, *, status="completed", model="fake-model", text=None, usage=None):
        if text is None:
            text = fake_result(self.review, self.question).raw_response.decode()
        if usage is None:
            usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        return CloudHTTPResponse(200, json.dumps({
            "status": status, "model": model, "usage": usage,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        }).encode(), "req_fake_stage6")

    def provider(self, transport, credential=None):
        return CloudOpenAIProvider(credential or StreamlitSecretsCredential({"OPENAI_API_KEY": self.secret}),
                                   self.review, transport=transport, enabled=True)

    def ask(self, transport, *, settings=None, credential=None, question=None, now=101):
        return self.service.ask(self.session, self.settings if settings is None else settings,
                                self.review, self.question if question is None else question,
                                self.provider(transport, credential).execute, now=now)

    def rejected(self, code, transport, **kwargs):
        with self.assertRaises(CloudAIRejected) as caught:
            self.ask(transport, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_exact_bounded_bytes_and_reported_usage(self):
        transport = RecordingTransport(self.response())
        answer = self.ask(transport)
        self.assertEqual(answer.outcome.status, "VALIDATED")
        self.assertEqual(answer.provider_usage, {"input_tokens": 10, "output_tokens": 20})
        self.assertGreater(answer.estimated_usd_reserved, 0)
        self.assertEqual(len(transport.calls), 1)
        payload, key, timeout = transport.calls[0]
        self.assertEqual(len(payload), answer.input_bytes)
        self.assertEqual(key, self.secret)
        self.assertEqual(timeout, 10)
        wire = json.loads(payload)
        self.assertEqual(wire["model"], "fake-model")
        self.assertEqual(wire["max_output_tokens"], 500)
        self.assertEqual(wire["tools"], [])
        self.assertEqual(json.loads(wire["input"])["question"], self.question)
        self.assertNotIn(self.secret, payload.decode())
        self.assertNotIn(self.secret, repr(answer))
        self.assertNotIn(self.secret, repr(self.session))

    def test_rejected_preflight_never_uses_credentials_or_transport(self):
        class ForbiddenCredentials:
            def get_api_key(self):
                raise AssertionError("Key read before service preflight")

        transport = RecordingTransport(self.response())
        bad = dict(self.settings, AI_SESSION_ESTIMATED_USD_LIMIT="0.000001")
        self.rejected("USAGE_BUDGET_EXCEEDED", transport, settings=bad,
                      credential=ForbiddenCredentials())
        self.assertEqual(transport.calls, [])
        missing_price = dict(self.settings)
        missing_price.pop("AI_PRICE_MODEL_ID")
        self.rejected("CONFIGURATION_UNAVAILABLE", transport, settings=missing_price,
                      credential=ForbiddenCredentials())
        self.assertEqual(transport.calls, [])

    def test_missing_key_and_provider_http_errors_are_sanitized(self):
        transport = RecordingTransport(self.response())
        self.rejected("MISSING_API_KEY", transport,
                      credential=StreamlitSecretsCredential({}))
        self.assertEqual(transport.calls, [])
        for status, expected in ((401, "AUTHENTICATION_FAILURE"),
                                 (429, "PROVIDER_RATE_LIMIT"),
                                 (400, "INVALID_CONFIGURATION"),
                                 (503, "PROVIDER_SERVICE_ERROR")):
            self.service = CloudAIService()
            bad_transport = RecordingTransport(CloudHTTPResponse(status, b"private-provider-error"))
            self.rejected(expected, bad_transport)
            self.assertEqual(len(bad_transport.calls), 1)

    def test_payload_change_and_disabled_provider_fail_before_key(self):
        request = prepare_cloud_question(self.review, self.question, model_snapshot="fake-model")
        provider = self.provider(RecordingTransport(self.response()))
        with self.assertRaises(CloudProviderFailure):
            provider.execute(request)
        with self.assertRaisesRegex(Exception, "locked"):
            CloudOpenAIProvider(StreamlitSecretsCredential({}), self.review).execute(request)
        transport = RecordingTransport(self.response())
        with self.assertRaises(CloudAIRejected) as caught:
            self.service.ask(self.session, self.settings, self.review, self.question,
                             lambda bound: self.provider(transport).execute(
                                 replace(bound, wire_body=bound.wire_body + b" ")), now=101)
        self.assertEqual(caught.exception.code, "INVALID_CONFIGURATION")
        self.assertEqual(transport.calls, [])

    def test_service_ticket_is_one_use_even_with_same_request(self):
        transport = RecordingTransport(self.response())

        def twice(bound):
            result = self.provider(transport).execute(bound)
            with self.assertRaises(CloudProviderFailure):
                self.provider(transport).execute(bound)
            return result

        self.assertEqual(self.service.ask(self.session, self.settings, self.review,
                                          self.question, twice, now=101).outcome.status, "VALIDATED")
        self.assertEqual(len(transport.calls), 1)

    def test_unknown_no_retry_and_invalid_response(self):
        transport = RecordingTransport(TimeoutError("synthetic-secret"))
        self.rejected("PROVIDER_OUTCOME_UNKNOWN", transport)
        self.rejected("DUPLICATE_OR_TOO_FAST", transport, now=104)
        self.assertEqual(len(transport.calls), 1)
        self.service = CloudAIService()
        wrong_model = RecordingTransport(self.response(model="other-model"))
        self.rejected("PROVIDER_OUTCOME_UNKNOWN", wrong_model)
        self.service = CloudAIService()
        malformed = RecordingTransport(CloudHTTPResponse(200, b"not-json"))
        self.rejected("PROVIDER_OUTCOME_UNKNOWN", malformed)
        self.service = CloudAIService()
        invalid = RecordingTransport(self.response(text="{}"))
        self.rejected("PROVIDER_ERROR", invalid)
        self.service = CloudAIService()
        oversized = RecordingTransport(CloudHTTPResponse(200, b"x" * 128_001))
        self.rejected("PROVIDER_OUTCOME_UNKNOWN", oversized)
        self.assertEqual(len(oversized.calls), 1)

    def test_incomplete_missing_usage_and_reported_cap(self):
        incomplete = RecordingTransport(self.response(status="incomplete"))
        self.rejected("OUTPUT_LIMIT_EXCEEDED", incomplete)
        self.service = CloudAIService()
        absent = json.loads(self.response().body)
        absent.pop("usage")
        unknown_usage = RecordingTransport(CloudHTTPResponse(200, json.dumps(absent).encode()))
        answer = self.ask(unknown_usage)
        self.assertIsNone(answer.provider_usage)
        self.assertGreater(answer.estimated_usd_reserved, 0)
        self.service = CloudAIService()
        excessive = RecordingTransport(self.response(
            usage={"input_tokens": 10, "output_tokens": 501, "total_tokens": 511}))
        self.rejected("USAGE_BUDGET_EXCEEDED", excessive)

    def test_rehashed_changed_payload_is_rejected_before_transport(self):
        transport = RecordingTransport(self.response())

        def altered(bound):
            changed = bound.wire_body.replace(b'"store":false', b'"store":true')
            self.assertNotEqual(changed, bound.wire_body)
            bad = replace(bound, wire_body=changed,
                          wire_digest=hashlib.sha256(changed).hexdigest())
            return self.provider(transport).execute(bad)

        with self.assertRaises(CloudAIRejected) as caught:
            self.service.ask(self.session, self.settings, self.review,
                             self.question, altered, now=101)
        self.assertEqual(caught.exception.code, "INVALID_CONFIGURATION")
        self.assertEqual(transport.calls, [])

    def test_transport_has_fixed_endpoint_no_redirect_and_no_retry(self):
        calls = []

        class FakeHTTPResponse:
            status = 302

            def read(self, _limit):
                return b"redirect"

            def getheader(self, _name):
                return "req_fake"

        class FakeConnection:
            def __init__(self, host, timeout):
                calls.append((host, timeout))

            def request(self, method, path, body, headers):
                calls.append((method, path, body, headers["Content-Type"]))

            def getresponse(self):
                return FakeHTTPResponse()

            def close(self):
                calls.append("closed")

        with patch("src.ai_copilot.cloud_question.http.client.HTTPSConnection", FakeConnection):
            response = HTTPSResponsesTransport().create(b"{}", api_key=self.secret, timeout_seconds=10)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(calls[0], ("api.openai.com", 10))
        self.assertEqual(calls[1][:2], ("POST", "/v1/responses"))
        self.assertEqual(calls[-1], "closed")
        self.assertEqual(len([item for item in calls if isinstance(item, tuple) and item[0] == "POST"]), 1)


class Stage6CloudUITests(unittest.TestCase):
    def setUp(self):
        denied = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        denied.start()
        self.addCleanup(denied.stop)
        salt = bytes(range(32))
        self.settings = {
            "AI_ACCESS_SALT_HEX": salt.hex(),
            "AI_ACCESS_SCRYPT_HEX": password_verifier("fake-password", salt).hex(),
            "AI_REAL_PROVIDER_ENABLED": True, "AI_MODEL_ID": "fake-model",
            "AI_PRICE_MODEL_ID": "fake-model", "AI_PRICE_INPUT_USD_PER_MILLION": "1",
            "AI_PRICE_OUTPUT_USD_PER_MILLION": "1", "AI_SESSION_ESTIMATED_USD_LIMIT": "1",
            "OPENAI_API_KEY": "synthetic-sentinel-only",
        }
        settings_patch = patch.object(copilot_view, "ai_settings", return_value=self.settings)
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        self.transport = None

        def factory(credentials, review, *, enabled):
            text = fake_result(review).raw_response.decode()
            body = json.dumps({"status": "completed", "model": "fake-model",
                               "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                               "output": [{"type": "message", "content": [{
                                   "type": "output_text", "text": text}]}]}).encode()
            self.transport = RecordingTransport(CloudHTTPResponse(200, body, "req_fake_ui"))
            return CloudOpenAIProvider(credentials, review, transport=self.transport, enabled=enabled)

        provider_patch = patch.object(copilot_view, "CloudOpenAIProvider", side_effect=factory)
        provider_patch.start()
        self.addCleanup(provider_patch.stop)
        self.app = AppTest.from_file("dashboard/scenario_planning_app.py", default_timeout=60).run()

    def test_public_planning_and_password_to_mock_transport(self):
        self.assertEqual(self.app.radio(key="ui_workspace").value, "Planning")
        self.app.radio(key="ui_workspace").set_value("Decision Copilot").run()
        self.assertFalse(any(button.key == "copilot_ask" for button in self.app.button))
        self.app.text_input(key="copilot_ai_password").set_value("fake-password")
        self.app.button(key="FormSubmitter:copilot_ai_access-Unlock AI preview").click().run()
        self.app.button(key="copilot_start").click().run()
        self.app.button(key="copilot_prepare").click().run()
        self.app.text_area(key="copilot_question").set_value("Why has service level declined?")
        self.app.button(key="copilot_ask").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["copilot_result"].status, "VALIDATED")
        self.assertEqual(len(self.transport.calls), 1)
        accounting = self.app.session_state["copilot_last_usage"]
        self.assertEqual(accounting["provider_usage"], {"input_tokens": 10, "output_tokens": 20})
        self.assertEqual(accounting["provider_request_id"], "req_fake_ui")
        self.assertIsNotNone(accounting["estimated_usd_reserved"])
        self.assertNotIn("synthetic-sentinel-only", repr(self.app.session_state))

    def test_missing_key_does_not_break_public_planning(self):
        self.settings.pop("OPENAI_API_KEY")
        self.assertEqual(self.app.radio(key="ui_workspace").value, "Planning")
        self.assertFalse(self.app.exception)
        self.app.radio(key="ui_workspace").set_value("Decision Copilot").run()
        self.app.text_input(key="copilot_ai_password").set_value("fake-password")
        self.app.button(key="FormSubmitter:copilot_ai_access-Unlock AI preview").click().run()
        self.app.button(key="copilot_start").click().run()
        self.app.button(key="copilot_prepare").click().run()
        self.app.text_area(key="copilot_question").set_value("Inspect service risk")
        self.app.button(key="copilot_ask").click().run()
        self.assertFalse(self.app.exception)
        self.assertNotIn("copilot_result", self.app.session_state)
        self.assertNotIn("copilot_last_usage", self.app.session_state)
        self.assertEqual(self.transport.calls, [])


if __name__ == "__main__":
    unittest.main()
