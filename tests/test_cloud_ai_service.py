"""Stage 5 backend gate tests; synthetic Brief and Fake Provider only."""
import socket
import json
import unittest
from unittest.mock import patch

from dashboard.copilot_view import fake_result
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.cloud_access import authenticate_ai_access, password_verifier
from src.ai_copilot.cloud_ai_service import CloudAIRejected, CloudAIService, CloudProviderFailure
from src.ai_copilot.provider_base import FakeProvider, ProviderResult
from src.synthetic_context import SyntheticHarness


class CloudAIServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SyntheticHarness()
        cls.context = cls.harness.issue("Baseline")
        cls.review = prepare_brief(cls.harness, cls.context).review

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def setUp(self):
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        self.network.start()
        self.addCleanup(self.network.stop)
        salt = bytes(range(32))
        self.settings = {"AI_ACCESS_SALT_HEX": salt.hex(),
                         "AI_ACCESS_SCRYPT_HEX": password_verifier("test-only-password", salt).hex()}
        self.session = {}
        self.service = CloudAIService()
        self.provider = FakeProvider(fake_result(self.review, "Inspect capacity"))
        self.execute = lambda bound: self.provider.execute(bound.provider_request)

    def authorize(self, now=100.0):
        self.assertTrue(authenticate_ai_access("test-only-password", self.settings,
                                               self.session, now=now))

    def ask(self, question="Inspect capacity", now=101.0, execute=None, settings=None, session=None):
        return self.service.ask(self.session if session is None else session,
                                self.settings if settings is None else settings, self.review,
                                question, self.execute if execute is None else execute, now=now)

    def rejected(self, code, **kwargs):
        with self.assertRaises(CloudAIRejected) as caught:
            self.ask(**kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_password_grant_is_required_by_backend_not_just_ui(self):
        self.session["_ai_access_until"] = 1900
        self.rejected("ACCESS_DENIED")
        self.assertEqual(self.provider.calls, [])
        self.assertFalse(authenticate_ai_access("wrong", self.settings, self.session, now=100))
        self.rejected("ACCESS_DENIED")
        self.authorize()
        answer = self.ask()
        self.assertEqual(answer.outcome.status, "VALIDATED")
        self.assertEqual(len(self.provider.calls), 1)
        self.assertNotIn("test-only-password", repr(self.session))
        self.session["_ai_access_grant"] = "0" * 64
        self.rejected("ACCESS_DENIED", question="Other question", now=104)
        self.assertEqual(len(self.provider.calls), 1)

    def test_new_session_expiry_config_rotation_and_lockout(self):
        self.authorize()
        self.rejected("ACCESS_DENIED", session={"_ai_access_until": 1900})
        self.rejected("ACCESS_DENIED", now=1901)
        self.rejected("ACCESS_DENIED", settings={"AI_ACCESS_SALT_HEX": self.settings["AI_ACCESS_SALT_HEX"]})
        rotated = dict(self.settings, AI_ACCESS_SCRYPT_HEX="11" * 32)
        self.rejected("ACCESS_DENIED", settings=rotated)
        self.session["_ai_access_locked_until"] = 2000
        self.rejected("ACCESS_DENIED")
        self.assertEqual(self.provider.calls, [])

    def test_duplicate_fast_window_and_process_daily_limit(self):
        self.authorize()
        self.ask()
        self.rejected("DUPLICATE_OR_TOO_FAST", question="Different question", now=101.2)
        self.rejected("DUPLICATE_OR_TOO_FAST", now=103)
        self.ask("What is service risk?", now=104)
        self.ask("How much inventory?", now=106)
        self.rejected("RATE_LIMIT_EXCEEDED", question="Any demand risk?", now=108)
        self.assertEqual(len(self.provider.calls), 3)
        self.service._daily_requests = 30
        self.rejected("RATE_LIMIT_EXCEEDED", question="New question", now=170)

    def test_question_context_and_session_budget_rejected_before_provider(self):
        self.authorize()
        self.rejected("CONTEXT_INVALID", question="x" * 501)
        self.assertEqual(self.provider.calls, [])
        low = dict(self.settings, AI_PRICE_MODEL_ID="offline-fixture-only",
                   AI_PRICE_INPUT_USD_PER_MILLION="1", AI_PRICE_OUTPUT_USD_PER_MILLION="1",
                   AI_SESSION_ESTIMATED_USD_LIMIT="0.00001")
        self.rejected("USAGE_BUDGET_EXCEEDED", settings=low)
        self.assertEqual(self.provider.calls, [])
        malformed = dict(low, AI_PRICE_INPUT_USD_PER_MILLION="not-a-price")
        self.rejected("CONFIGURATION_UNAVAILABLE", settings=malformed)
        wrong_model = dict(low, AI_PRICE_MODEL_ID="another-model")
        self.rejected("CONFIGURATION_UNAVAILABLE", settings=wrong_model)
        from src.ai_copilot import cloud_ai_service
        from src.ai_copilot.cloud_question import cloud_response_arguments
        with patch.object(cloud_ai_service, "cloud_response_arguments",
                          side_effect=lambda bound: dict(cloud_response_arguments(bound), input="x" * 31000)):
            self.rejected("INPUT_LIMIT_EXCEEDED")
        self.assertEqual(self.provider.calls, [])

    def test_priced_reservation_is_configurable_and_conservative(self):
        self.authorize()
        priced = dict(self.settings, AI_PRICE_MODEL_ID="offline-fixture-only",
                      AI_PRICE_INPUT_USD_PER_MILLION="1",
                      AI_PRICE_OUTPUT_USD_PER_MILLION="1",
                      AI_SESSION_ESTIMATED_USD_LIMIT="0.03")
        first = self.ask(settings=priced)
        self.assertGreater(first.estimated_usd_reserved, 0)
        self.rejected("USAGE_BUDGET_EXCEEDED", question="What is service risk?",
                      now=104, settings=priced)
        self.assertEqual(len(self.provider.calls), 1)

    def test_session_request_limit_rejects_ninth_call(self):
        self.authorize()
        for index in range(8):
            self.assertEqual(self.ask(f"Review risk {index}", now=101 + 61 * index).outcome.status,
                             "VALIDATED")
        self.rejected("RATE_LIMIT_EXCEEDED", question="Review ninth risk", now=101 + 61 * 8)
        self.assertEqual(len(self.provider.calls), 8)

    def test_provider_timeout_consumes_one_use_reservation_without_retry(self):
        self.authorize()
        calls = []

        def uncertain(bound):
            calls.append(bound.request_digest)
            raise TimeoutError("secret-internal-detail")

        self.rejected("PROVIDER_OUTCOME_UNKNOWN", execute=uncertain)
        self.rejected("DUPLICATE_OR_TOO_FAST", execute=uncertain, now=104)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("secret-internal-detail", repr(self.session))

    def test_response_errors_output_limit_and_usage(self):
        self.authorize()
        self.rejected("PROVIDER_ERROR", execute=lambda bound: ProviderResult("DEFINITIVE_ERROR"))
        self.rejected("OUTPUT_LIMIT_EXCEEDED", question="Other", now=104,
                      execute=lambda bound: ProviderResult("INCOMPLETE"))
        self.rejected("OUTPUT_LIMIT_EXCEEDED", question="Next", now=106,
                      execute=lambda bound: ProviderResult("SUCCEEDED", b"x" * 16001))
        self.rejected("RATE_LIMIT_EXCEEDED", question="Fourth", now=108)
        other = CloudAIService()
        self.service = other
        self.rejected("INVALID_RESPONSE", question="Malformed", now=170,
                      execute=lambda bound: ProviderResult("SUCCEEDED", b"{}"))
        self.rejected("USAGE_BUDGET_EXCEEDED", question="Usage", now=172,
                      execute=lambda bound: ProviderResult("SUCCEEDED", b"{}",
                                                          usage={"input_tokens": 10, "output_tokens": 501}))

    def test_safe_provider_failure_categories_and_redacted_log(self):
        self.authorize()
        for index, code in enumerate(("MISSING_API_KEY", "AUTHENTICATION_FAILURE",
                                      "PROVIDER_RATE_LIMIT", "PROVIDER_SERVICE_ERROR",
                                      "INVALID_CONFIGURATION", "NETWORK_ERROR")):
            self.service = CloudAIService()

            def fail(_bound):
                raise CloudProviderFailure(code)

            with self.assertLogs("src.ai_copilot.cloud_ai_service", level="WARNING") as logs:
                self.rejected(code, question=f"Question {index}", now=101 + index * 2,
                              execute=fail)
            self.assertNotIn(self.settings["AI_ACCESS_SCRYPT_HEX"], repr(logs.output))
            self.assertNotIn("test-only-password", repr(logs.output))

    def test_validator_exception_is_sanitized_and_ui_can_continue(self):
        self.authorize()
        from src.ai_copilot import cloud_ai_service
        with patch.object(cloud_ai_service, "classify_response",
                          side_effect=RuntimeError("synthetic-sensitive-detail")):
            with self.assertLogs("src.ai_copilot.cloud_ai_service", level="WARNING") as logs:
                self.rejected("INVALID_RESPONSE")
        self.assertNotIn("synthetic-sensitive-detail", repr(logs.output))

    def test_context_and_secret_are_never_sent_to_provider(self):
        self.authorize()
        captured = []

        def inspect(bound):
            from src.ai_copilot.cloud_question import cloud_response_arguments
            arguments = cloud_response_arguments(bound)
            captured.append(arguments)
            return fake_result(self.review, bound.question)

        answer = self.ask(execute=inspect)
        self.assertEqual(answer.outcome.status, "VALIDATED")
        self.assertEqual(len(json.dumps(captured[0], sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":")).encode()), answer.input_bytes)
        self.assertNotIn("AI_ACCESS_SCRYPT_HEX", repr(captured))
        self.assertNotIn(self.settings["AI_ACCESS_SCRYPT_HEX"], repr(captured))
        self.assertNotIn("OPENAI_API_KEY", repr(captured))
        self.assertIsNone(answer.estimated_usd_reserved)
        self.assertIsNone(answer.provider_usage)


if __name__ == "__main__":
    unittest.main()
