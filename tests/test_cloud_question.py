"""Offline question binding and Responses request preparation."""
import json
import unittest
from types import SimpleNamespace

from src.synthetic_context import SyntheticHarness
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.cloud_question import (
    CloudOpenAIProvider, cloud_response_arguments, prepare_cloud_question,
)
from src.ai_copilot.provider_base import OfflineMockTransport, ProviderBlocked
from dashboard.copilot_view import fake_result


class CloudQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SyntheticHarness()
        cls.context = cls.harness.issue("Baseline")
        cls.review = prepare_brief(cls.harness, cls.context).review

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def test_question_and_history_bind_to_validated_context(self):
        first = prepare_cloud_question(self.review, "Why has service declined?")
        later = prepare_cloud_question(self.review, "What should management review?",
                                       prior_turns=((first.question, "Review validated evidence."),))
        self.assertNotEqual(first.request_digest, later.request_digest)
        arguments = cloud_response_arguments(later)
        self.assertEqual(arguments["model"], "offline-fixture-only")
        self.assertEqual(arguments["tools"], [])
        body = json.loads(arguments["input"])
        self.assertEqual(body["question"], later.question)
        self.assertEqual(body["prior_turns"][0][0], first.question)
        self.assertEqual(body["validated_brief"], json.loads(later.provider_request.canonical_body)["brief"])
        self.assertEqual(len(body["business_context"]), 2)

    def test_invalid_question_and_tampered_digest_rejected(self):
        with self.assertRaises(ProviderBlocked):
            prepare_cloud_question(None, "Inspect demand risk")
        for question in ("", " " * 3, "x" * 501, "bad\x00question"):
            with self.subTest(question_length=len(question)), self.assertRaises(ProviderBlocked):
                prepare_cloud_question(self.review, question)
        request = prepare_cloud_question(self.review, "Inspect demand risk")
        from dataclasses import replace
        with self.assertRaises(ProviderBlocked):
            cloud_response_arguments(replace(request, question="different"))

    def test_real_provider_lock_precedes_credential_lookup(self):
        class ForbiddenCredentials:
            def get_api_key(self):
                raise AssertionError("Credential lookup must not occur")

        request = prepare_cloud_question(self.review, "Inspect capacity")
        with self.assertRaisesRegex(ProviderBlocked, "locked"):
            CloudOpenAIProvider(ForbiddenCredentials()).execute(request)

    def test_mock_transport_validation_error_and_timeout(self):
        request = prepare_cloud_question(self.review, "Inspect capacity")

        def response(text):
            return SimpleNamespace(status="completed", _request_id="req_fake_stage4",
                                   usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                                   output=[SimpleNamespace(type="message", content=[
                                       SimpleNamespace(type="output_text", text=text)])])

        good = OfflineMockTransport(response(fake_result(self.review, request.question).raw_response.decode()))
        self.assertEqual(CloudOpenAIProvider.execute_mock(request, self.review, good).status, "SUCCEEDED")
        self.assertEqual(good.calls, 1)
        bad = OfflineMockTransport(response("{}"))
        self.assertEqual(CloudOpenAIProvider.execute_mock(request, self.review, bad).status, "DEFINITIVE_ERROR")
        uncertain = OfflineMockTransport(TimeoutError())
        self.assertEqual(CloudOpenAIProvider.execute_mock(request, self.review, uncertain).status, "UNKNOWN_OUTCOME")


if __name__ == "__main__":
    unittest.main()
