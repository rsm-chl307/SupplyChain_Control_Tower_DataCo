"""P5 adapter mock outcomes; no SDK, credential or network capability."""
from __future__ import annotations

import json
from types import SimpleNamespace as NS
import unittest

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import (
    OfflineMockTransport, OpenAIResponsesAdapter, ProviderBlocked, build_request,
)
from src.synthetic_context import SyntheticHarness


class OwnerPolicyAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = SyntheticHarness()
        cls.review = prepare_brief(cls.harness, cls.harness.issue("Baseline"), max_records=2).review
        assert cls.review is not None
        cls.request = build_request(cls.review, model_snapshot="gpt-6-luna",
                                    max_output_tokens=25000, timeout_seconds=180,
                                    execution_profile="P5_ACCEPTANCE_MOCK")

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def _response(self, status="completed", text=None, *, model="gpt-6-luna"):
        output = [] if text is None else [NS(type="message", content=[NS(type="output_text", text=text)])]
        return NS(status=status, output=output, model=model,
                  _request_id="mock-response-id",
                  usage={"input_tokens": 3000, "output_tokens": 500, "total_tokens": 3500})

    def _valid(self):
        return {"response_version": "1.0", "brief_digest": self.review.content_digest,
                "executive_assessment": {"summary": "Review capacity.",
                                         "principal_concern": "Service pressure.", "evidence_refs": []},
                "key_findings": [], "root_cause_interpretation": {k: [] for k in
                    ("observed_facts", "system_identified_drivers", "ai_interpretations",
                     "unverified_hypotheses", "missing_evidence")},
                "recommendations": [], "decision_trade_offs": [], "further_investigation": [],
                "limitations_and_confidence": {"data_completeness": "Bounded evidence.",
                    "evidence_quality": "Published evidence.", "directly_supported_conclusions": [],
                    "inferences": [], "unsupported_questions": [], "confidence": "Limited",
                    "confidence_rationale": "Evidence is bounded."}}

    def test_owner_configuration_and_real_dispatch_block(self):
        args = OpenAIResponsesAdapter.call_arguments(self.request)
        outbound = json.loads(args["input"])
        self.assertEqual(outbound["brief_digest"], self.review.content_digest)
        self.assertIn("brief", outbound)
        self.assertNotIn("artifact_sha256", args["input"])
        self.assertEqual(args["model"], "gpt-6-luna")
        self.assertEqual(args["reasoning"], {"effort": "medium"})
        self.assertEqual(args["max_output_tokens"], 25000)
        self.assertEqual(args["tools"], [])
        self.assertEqual(args["tool_choice"], "none")
        self.assertFalse(args["store"])
        self.assertFalse(args["stream"])
        self.assertFalse(args["background"])
        self.assertEqual(OpenAIResponsesAdapter.required_client_options(self.request),
                         {"max_retries": 0, "timeout": 180.0})
        self.assertEqual(self.request.max_input_tokens, 25000)
        with self.assertRaises(ProviderBlocked):
            OpenAIResponsesAdapter().execute(self.request)
        paid = build_request(self.review, model_snapshot="gpt-6-luna",
                             max_output_tokens=25000, timeout_seconds=180,
                             execution_profile="P5_PAID_ACCEPTANCE")
        with self.assertRaisesRegex(ProviderBlocked, "separate Owner authorization"):
            OpenAIResponsesAdapter.execute_authorized(
                paid, self.review, campaign=None, case_id="EV-01",
                owner_password="", api_key=None)

    def test_success_and_no_retry(self):
        response = self._response(text=json.dumps(self._valid()))
        transport = OfflineMockTransport(response)
        result = OpenAIResponsesAdapter.execute_mock(self.request, self.review, transport)
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.returned_model_id, "gpt-6-luna")
        self.assertEqual(result.usage["total_tokens"], 3500)
        self.assertEqual(transport.calls, 1)
        with self.assertRaises(ProviderBlocked):
            OpenAIResponsesAdapter.execute_mock(self.request, self.review, transport)

    def test_refusal_incomplete_failed_and_unknown(self):
        refusal = self._response(text=None)
        refusal.output = [NS(type="message", content=[NS(type="refusal", refusal="declined")])]
        for response, expected in ((refusal, "REFUSED"),
                                   (self._response(status="incomplete"), "INCOMPLETE"),
                                   (self._response(status="failed"), "DEFINITIVE_ERROR"),
                                   (self._response(status="in_progress"), "UNKNOWN_OUTCOME")):
            with self.subTest(expected=expected):
                result = OpenAIResponsesAdapter.execute_mock(self.request, self.review,
                                                               OfflineMockTransport(response))
                self.assertEqual(result.status, expected)

    def test_invalid_json_duplicate_keys_schema_and_model_id(self):
        invalid = self._valid()
        del invalid["recommendations"]
        for raw in ("{", '{"a":1,"a":2}', json.dumps(invalid)):
            with self.subTest(raw=raw[:20]):
                result = OpenAIResponsesAdapter.execute_mock(self.request, self.review,
                    OfflineMockTransport(self._response(text=raw)))
                self.assertEqual(result.status, "DEFINITIVE_ERROR")
        for model in (None, "unexpected-model"):
            result = OpenAIResponsesAdapter.execute_mock(self.request, self.review,
                OfflineMockTransport(self._response(text=json.dumps(self._valid()), model=model)))
            self.assertEqual(result.status, "UNKNOWN_OUTCOME")
        dated = OpenAIResponsesAdapter.execute_mock(self.request, self.review,
            OfflineMockTransport(self._response(text=json.dumps(self._valid()),
                                                model="gpt-6-luna-2026-11-22")))
        self.assertEqual(dated.status, "SUCCEEDED")
        self.assertEqual(dated.returned_model_id, "gpt-6-luna-2026-11-22")

    def test_timeout_connection_and_arbitrary_transport_rejected(self):
        for error in (TimeoutError("mock timeout"), ConnectionError("mock connection")):
            transport = OfflineMockTransport(error)
            self.assertEqual(OpenAIResponsesAdapter.execute_mock(self.request, self.review,
                             transport).status, "UNKNOWN_OUTCOME")
            self.assertEqual(transport.calls, 1)
        with self.assertRaises(ProviderBlocked):
            OpenAIResponsesAdapter.execute_mock(self.request, self.review, object())


if __name__ == "__main__":
    unittest.main()
