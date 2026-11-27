from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.windows_runner_exchange import (
    EXCHANGE_PATH_ENV, RunnerExchangeBlocked, prepare_configured_count_request,
)
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked, TokenCountWorkflowState,
)
from src.synthetic_context import SyntheticHarness
from tools.windows_api_runner.api_runner import canonical_json_bytes


class P5TokenCountOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-count-orchestrator-test-only-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "exchange"
        self.db_path = Path(self.temp.name) / "workflow.sqlite3"
        self.env = patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        outcome = prepare_brief(self.harness, self.harness.issue("Baseline"), max_records=2)
        self.review = outcome.review
        self.request = build_request(self.review, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_PAID_ACCEPTANCE")
        self.workflow = P5TokenCountOrchestrator(exchange_path=self.root,
                                                 state_path=self.db_path)

    def test_valid_preparation_preserves_uuid_and_exact_identity_without_api(self):
        with patch("tools.windows_api_runner.api_runner.UrllibTransport.post") as post:
            prepared = self.workflow.prepare("EV-01", self.review, self.request)
        post.assert_not_called()
        record = self.workflow.record_for_case("EV-01")
        self.assertEqual(record.state, TokenCountWorkflowState.PREPARED)
        self.assertEqual(record.request_id, prepared.request_id)
        self.assertEqual(record.run_id, prepared.run_id)
        self.assertEqual(record.brief_digest, prepared.brief_digest)
        self.assertEqual(record.provider_request_digest, prepared.provider_request_digest)
        self.assertEqual(record.payload_sha256, prepared.payload_digest)
        self.assertEqual(record.count_projection_sha256, prepared.count_projection_digest)
        self.assertTrue(prepared.package_path.is_file())
        self.assertTrue((self.root / "responses").is_dir())

    def test_missing_or_invalid_context_fails_before_preparation(self):
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.prepare("EV-01", None, self.request)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.NOT_PREPARED)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.prepare("EV-99", self.review, self.request)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.prepare("EV-01", self.review, object())
        self.assertFalse((self.root / "requests").exists())

    def test_brief_provider_request_and_profile_mismatches_fail_closed(self):
        for bad_request in (
                replace(self.request, brief_digest="0" * 64),
                replace(self.request, execution_profile="P2_OFFLINE"),
                replace(self.request, model_snapshot="unapproved-model")):
            with self.subTest(request=bad_request):
                with self.assertRaises(RunnerExchangeBlocked):
                    self.workflow.prepare("EV-01", self.review, bad_request)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.NOT_PREPARED)
        self.assertFalse((self.root / "requests").exists())

    def test_duplicate_preparation_and_unresolved_workflow_block_new_uuid(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        restarted = P5TokenCountOrchestrator(exchange_path=self.root,
                                             state_path=self.db_path)
        self.assertEqual(restarted.record_for_request(prepared.request_id).state,
                         TokenCountWorkflowState.PREPARED)
        with self.assertRaises(TokenCountWorkflowBlocked):
            restarted.prepare("EV-01", self.review, self.request)
        restarted.mark_awaiting_host_execution(prepared.request_id)
        restarted.mark_unknown(prepared.request_id)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            restarted.prepare("EV-02", self.review, self.request)
        self.assertEqual(restarted.state_for_case("EV-02"),
                         TokenCountWorkflowState.NOT_PREPARED)

    def test_orphan_request_package_without_workflow_row_blocks_new_preparation(self):
        # Simulate a crash after the bridge atomically writes the request but
        # before the orchestrator can persist its workflow row.
        orphan = prepare_configured_count_request("EV-01", self.review, self.request)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "Untracked request file"):
            self.workflow.prepare("EV-01", self.review, self.request)
        self.assertIsNone(self.workflow.record_for_case("EV-01"))
        self.assertEqual(tuple((self.root / "requests").iterdir()), (orphan.package_path,))

    def test_invalid_state_transition_is_rejected(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.mark_response_pending(prepared.request_id)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.PREPARED)

    def test_handoff_uses_configured_path_uuid_and_non_secret_commands(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        handoff = self.workflow.create_windows_handoff(prepared.request_id)
        self.assertEqual(handoff.request_id, prepared.request_id)
        self.assertEqual(handoff.container_exchange_path, str(self.root.resolve()))
        self.assertEqual(handoff.request_container_path,
                         str(self.root.resolve() / "requests" / f"{prepared.request_id}.json"))
        self.assertIn(prepared.request_id, handoff.runner_invocation)
        self.assertIn("docker cp", handoff.docker_copy_to_windows)
        self.assertIn("docker cp", handoff.docker_copy_to_container)
        self.assertIn("--exchange", handoff.runner_invocation)
        self.assertNotIn("test-secret-value", handoff.to_markdown())
        self.assertNotIn('"input"', handoff.to_markdown())
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.AWAITING_HOST_EXECUTION)

    def test_handoff_rejects_unknown_uuid_wrong_package_and_invalid_windows_path(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.create_windows_handoff("not-a-uuid")
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.create_windows_handoff(prepared.request_id,
                                                 windows_exchange_path="relative")
        package_path = prepared.package_path
        package_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.create_windows_handoff(prepared.request_id)

    def test_response_file_arrival_is_pending_only_not_collected(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        response_path = self.root / "responses" / f"{prepared.request_id}.json"
        response_path.write_text('{"not":"validated"}', encoding="utf-8")
        record = self.workflow.mark_response_pending(prepared.request_id)
        self.assertEqual(record.state, TokenCountWorkflowState.RESPONSE_PENDING)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.prepare("EV-02", self.review, self.request)

    def _write_response(self, prepared, *, changes=None):
        package = {
            "request_id": prepared.request_id, "case_id": prepared.case_id,
            "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
            "operation": "input_token_count", "http_status": 200,
            "openai_request_id": "req-fake-count-01", "model": "gpt-6-luna",
            "returned_model_id": "gpt-6-luna", "usage": None,
            "response_body": {"input_tokens": 3200, "model": "gpt-6-luna"},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": "SUCCEEDED",
            "brief_digest": prepared.brief_digest,
            "provider_request_digest": prepared.provider_request_digest,
            "count_projection_digest": prepared.count_projection_digest,
            "run_manifest_sha256": prepared.run_manifest_sha256,
        }
        package.update(changes or {})
        response_path = self.root / "responses" / f"{prepared.request_id}.json"
        response_path.write_bytes(canonical_json_bytes(package) + b"\n")
        return response_path

    def test_collection_validates_exact_evidence_and_is_terminal(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        self._write_response(prepared)
        self.workflow.mark_response_pending(prepared.request_id)
        record, evidence = self.workflow.collect_response(
            prepared.request_id, "EV-01", self.review, self.request)
        self.assertEqual(record.state, TokenCountWorkflowState.COLLECTED)
        self.assertEqual(evidence.runner_request_id, prepared.request_id)
        self.assertEqual(evidence.run_id, prepared.run_id)
        self.assertEqual(evidence.full_payload_sha256, prepared.payload_digest)
        self.assertEqual(evidence.count_projection_sha256, prepared.count_projection_digest)
        from src.ai_copilot.token_count_evidence import require_exact_token_count
        self.assertEqual(require_exact_token_count(
            "EV-01", self.request, evidence=evidence, review=self.review), 3200)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.collect_response(prepared.request_id, "EV-01",
                                           self.review, self.request)

    def test_collection_failure_and_explicit_unknown_fail_closed(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        self._write_response(prepared, changes={"run_id": "different-run"})
        self.workflow.mark_response_pending(prepared.request_id)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.collect_response(prepared.request_id, "EV-01",
                                           self.review, self.request)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.FAILED)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            self.workflow.prepare("EV-02", self.review, self.request)

    def test_unknown_host_response_remains_unknown_across_reopen(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        self._write_response(prepared, changes={"runner_execution_status": "UNKNOWN"})
        self.workflow.mark_response_pending(prepared.request_id)
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.collect_response(prepared.request_id, "EV-01",
                                           self.review, self.request)
        restarted = P5TokenCountOrchestrator(exchange_path=self.root,
                                             state_path=self.db_path)
        self.assertEqual(restarted.state_for_case("EV-01"),
                         TokenCountWorkflowState.UNKNOWN)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            restarted.prepare("EV-02", self.review, self.request)


if __name__ == "__main__":
    unittest.main()
