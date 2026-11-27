"""Contract tests for endpoint-specific Responses input-token serialization."""
from datetime import datetime, timezone
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.input_token_count_payload import (
    COUNT_FIELDS, INPUT_TOKEN_COUNT_FIELDS, input_token_count_payload,
    input_token_count_wire,
)
from src.ai_copilot.provider import OpenAIResponsesAdapter, build_request
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked, TokenCountWorkflowState,
)
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV
from src.synthetic_context import SyntheticHarness
from tools.windows_api_runner.api_runner import canonical_json_bytes


class InputTokenCountPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="count-payload-contract-test-")
        self.addCleanup(self.temp.cleanup)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.review = prepare_brief(
            self.harness, self.harness.issue("Baseline"), max_records=2).review
        self.request = build_request(
            self.review, model_snapshot="gpt-6-luna", max_output_tokens=25000,
            timeout_seconds=180, execution_profile="P5_PAID_ACCEPTANCE")

    def test_generation_only_fields_are_excluded_from_count_payload(self):
        payload = input_token_count_payload(self.request)
        self.assertNotIn("background", payload)
        self.assertNotIn("max_output_tokens", payload)
        for field in ("store", "stream", "temperature", "top_p"):
            self.assertNotIn(field, payload)
        self.assertTrue(set(payload).issubset(INPUT_TOKEN_COUNT_FIELDS))

    def test_supported_endpoint_fields_are_preserved(self):
        supported = {
            "conversation": {"id": "conv_synthetic"}, "input": "synthetic input",
            "instructions": "synthetic instructions", "model": "gpt-6-luna",
            "parallel_tool_calls": False, "personality": "pragmatic",
            "previous_response_id": "resp_synthetic", "reasoning": {"effort": "medium"},
            "text": {"format": {"type": "text"}, "verbosity": "low"},
            "tool_choice": "none", "tools": [], "truncation": "disabled",
            "background": False, "max_output_tokens": 123,
            "store": False, "stream": False, "temperature": 0, "top_p": 1,
        }
        with patch("src.ai_copilot.input_token_count_payload.OpenAIResponsesAdapter.call_arguments",
                   return_value=supported):
            self.assertEqual(input_token_count_payload(self.request), {
                key: value for key, value in supported.items()
                if key in INPUT_TOKEN_COUNT_FIELDS
            })

    def test_count_payload_digests_use_exact_canonical_payload_and_projection(self):
        wire, full_digest, projection_digest = input_token_count_wire(self.request)
        payload = json.loads(wire)
        expected_projection = {key: payload[key] for key in COUNT_FIELDS}
        self.assertEqual(wire, canonical_json_bytes(payload))
        self.assertEqual(full_digest, hashlib.sha256(canonical_json_bytes(payload)).hexdigest())
        self.assertEqual(projection_digest,
                         hashlib.sha256(canonical_json_bytes(expected_projection)).hexdigest())

    def test_generation_payload_is_unchanged_and_still_contains_generation_fields(self):
        generation = OpenAIResponsesAdapter.call_arguments(self.request)
        self.assertIsInstance(generation, dict)
        self.assertIs(generation["background"], False)
        self.assertIs(generation["store"], False)
        self.assertIs(generation["stream"], False)
        self.assertEqual(generation["max_output_tokens"], 25000)
        self.assertNotEqual(canonical_json_bytes(generation), input_token_count_wire(self.request)[0])

    def test_fake_200_collects_count_and_passes_evidence_gate(self):
        from tests.test_p5_windows_runner_exchange import WindowsRunnerP5ExchangeTests

        # Reuse the existing end-to-end fixture helper without making any transport call.
        helper = WindowsRunnerP5ExchangeTests(methodName="test_response_reconstructs_digest_bound_exact_token_evidence")
        helper.setUp()
        try:
            prepared = helper.exchange.prepare("EV-01", helper.review, helper.request)
            helper._response_package(prepared, input_tokens=4321)
            evidence = helper.exchange.collect(prepared, helper.review, helper.request)
            from src.ai_copilot.token_count_evidence import require_exact_token_count
            self.assertEqual(require_exact_token_count(
                "EV-01", helper.request, evidence=evidence, review=helper.review), 4321)
            package = json.loads(prepared.package_path.read_text(encoding="utf-8"))
            self.assertEqual(package["payload_digest"], evidence.full_payload_sha256)
            self.assertEqual(package["count_projection_digest"], evidence.count_projection_sha256)
        finally:
            helper.doCleanups()

    def test_orchestrator_http_400_fails_closed_and_preserves_request_uuid(self):
        import os
        from unittest.mock import patch as mock_patch
        from src.ai_copilot.p5_token_count_orchestrator import P5TokenCountOrchestrator

        exchange_root = f"{self.temp.name}/exchange"
        with mock_patch.dict(os.environ, {EXCHANGE_PATH_ENV: exchange_root}):
            workflow = P5TokenCountOrchestrator(
                exchange_path=exchange_root, state_path=f"{self.temp.name}/workflow.sqlite3")
            prepared = workflow.prepare("EV-01", self.review, self.request)
            workflow.create_windows_handoff(prepared.request_id)
            response = {
                "request_id": prepared.request_id, "case_id": "EV-01",
                "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
                "operation": "input_token_count", "http_status": 400,
                "openai_request_id": "req_synthetic_400", "model": "gpt-6-luna",
                "returned_model_id": None, "usage": None,
                "response_body": {"error": {"message": "synthetic"}},
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "runner_execution_status": "FAILED_AFTER_DISPATCH",
                "brief_digest": prepared.brief_digest,
                "provider_request_digest": prepared.provider_request_digest,
                "count_projection_digest": prepared.count_projection_digest,
                "run_manifest_sha256": prepared.run_manifest_sha256,
            }
            from pathlib import Path
            response_path = Path(exchange_root) / "responses" / f"{prepared.request_id}.json"
            response_path.parent.mkdir(parents=True, exist_ok=True)
            response_path.write_bytes(canonical_json_bytes(response))
            workflow.mark_response_pending(prepared.request_id)
            with self.assertRaisesRegex(TokenCountWorkflowBlocked, "HTTP 400"):
                workflow.collect_response(prepared.request_id, "EV-01", self.review, self.request)
            self.assertEqual(workflow.record_for_request(prepared.request_id).request_id,
                             prepared.request_id)
            self.assertEqual(workflow.record_for_request(prepared.request_id).state,
                             TokenCountWorkflowState.FAILED)
            self.assertFalse(workflow.workflow_resolved(prepared.request_id))

    def test_orchestrator_names_evidence_gate_rejection(self):
        import os
        from pathlib import Path
        from unittest.mock import patch as mock_patch
        from src.ai_copilot.eight_call_campaign import CampaignBlocked
        exchange_root = f"{self.temp.name}/evidence-gate-exchange"
        with mock_patch.dict(os.environ, {EXCHANGE_PATH_ENV: exchange_root}):
            workflow = P5TokenCountOrchestrator(
                exchange_path=exchange_root,
                state_path=f"{self.temp.name}/evidence-gate-workflow.sqlite3")
            prepared = workflow.prepare("EV-01", self.review, self.request)
            workflow.create_windows_handoff(prepared.request_id)
            response = {
                "request_id": prepared.request_id, "case_id": "EV-01",
                "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
                "operation": "input_token_count", "http_status": 200,
                "openai_request_id": "req_synthetic_evidence_gate", "model": "gpt-6-luna",
                "returned_model_id": "gpt-6-luna", "usage": None,
                "response_body": {"input_tokens": 4321, "model": "gpt-6-luna"},
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "runner_execution_status": "SUCCEEDED",
                "brief_digest": prepared.brief_digest,
                "provider_request_digest": prepared.provider_request_digest,
                "count_projection_digest": prepared.count_projection_digest,
                "run_manifest_sha256": prepared.run_manifest_sha256,
            }
            response_path = Path(exchange_root) / "responses" / f"{prepared.request_id}.json"
            response_path.parent.mkdir(parents=True, exist_ok=True)
            response_path.write_bytes(canonical_json_bytes(response))
            workflow.mark_response_pending(prepared.request_id)
            with mock_patch(
                "src.ai_copilot.p5_token_count_orchestrator.require_exact_token_count",
                side_effect=CampaignBlocked("synthetic gate rejection"),
            ):
                with self.assertRaisesRegex(TokenCountWorkflowBlocked,
                                            "Evidence Gate rejection"):
                    workflow.collect_response(prepared.request_id, "EV-01",
                                              self.review, self.request)
            self.assertEqual(workflow.record_for_request(prepared.request_id).state,
                             TokenCountWorkflowState.FAILED)


if __name__ == "__main__":
    unittest.main()
