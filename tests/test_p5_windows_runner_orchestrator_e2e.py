"""Offline end-to-end tests for the P5 to Windows Runner handoff."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked, TokenCountWorkflowState,
)
from src.ai_copilot.provider import build_request
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV
from src.synthetic_context import SyntheticHarness
from tests.test_windows_api_runner import FakeCredentials, FakeTransport
from tools.windows_api_runner.api_runner import (
    ApiRunner, ExecutionStateStore, RunnerError, read_request_file,
)


class P5WindowsRunnerEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-runner-e2e-test-only-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.container_exchange = self.base / "container" / "exchange"
        self.workflow_db = self.base / "container" / "workflow.sqlite3"
        self.host_exchange = self.base / "windows" / "exchange"
        self.host_state = self.base / "windows" / "runner-state.sqlite3"
        self.env = patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(self.container_exchange)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.review = prepare_brief(
            self.harness, self.harness.issue("Baseline"), max_records=2).review
        self.request = build_request(
            self.review, model_snapshot="gpt-6-luna", max_output_tokens=25000,
            timeout_seconds=180, execution_profile="P5_PAID_ACCEPTANCE")
        self.workflow = P5TokenCountOrchestrator(
            exchange_path=self.container_exchange, state_path=self.workflow_db)

    def _host_execute(self, request_id, *, transport=None, response_dir=None):
        request_source = self.container_exchange / "requests" / f"{request_id}.json"
        host_request = self.host_exchange / "requests" / request_source.name
        host_request.parent.mkdir(parents=True, exist_ok=True)
        (self.host_exchange / "responses").mkdir(parents=True, exist_ok=True)
        shutil.copy2(request_source, host_request)
        validated = read_request_file(host_request)
        credentials = FakeCredentials()
        fake_transport = transport or FakeTransport()
        state = ExecutionStateStore(self.host_state)
        runner = ApiRunner(credentials, fake_transport, state)
        result = runner.execute(
            validated,
            response_dir if response_dir is not None else self.host_exchange / "responses",
            confirm=True)
        self.assertEqual(credentials.calls, 1)
        self.assertEqual(len(fake_transport.calls), 1)
        self.assertEqual(result["request_id"], request_id)
        self.assertEqual(result["run_id"], self.review._draft._bundle._context.run_id)
        return result, fake_transport

    def test_complete_fake_runner_exchange_collects_digest_bound_evidence(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        handoff = self.workflow.create_windows_handoff(prepared.request_id)
        self.assertEqual(handoff.request_id, prepared.request_id)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.AWAITING_HOST_EXECUTION)

        result, transport = self._host_execute(prepared.request_id)
        self.assertEqual(result["runner_execution_status"], "SUCCEEDED")
        self.assertEqual(len(transport.calls), 1)
        shutil.copy2(self.host_exchange / "responses" / f"{prepared.request_id}.json",
                     self.container_exchange / "responses" / f"{prepared.request_id}.json")
        self.workflow.mark_response_pending(prepared.request_id)
        record, evidence = self.workflow.collect_response(
            prepared.request_id, "EV-01", self.review, self.request)
        self.assertEqual(record.state, TokenCountWorkflowState.COLLECTED)
        self.assertEqual(evidence.runner_request_id, prepared.request_id)
        self.assertEqual(evidence.full_payload_sha256, prepared.payload_digest)
        self.assertEqual(evidence.count_projection_sha256,
                         prepared.count_projection_digest)

    def test_restart_without_trusted_context_does_not_advance_or_replace_request(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        self._host_execute(prepared.request_id)
        shutil.copy2(self.host_exchange / "responses" / f"{prepared.request_id}.json",
                     self.container_exchange / "responses" / f"{prepared.request_id}.json")
        self.workflow.mark_response_pending(prepared.request_id)

        restarted = P5TokenCountOrchestrator(
            exchange_path=self.container_exchange, state_path=self.workflow_db)
        with self.assertRaises(TokenCountWorkflowBlocked):
            restarted.collect_response(prepared.request_id, "EV-01", None, None)
        self.assertEqual(restarted.state_for_case("EV-01"),
                         TokenCountWorkflowState.RESPONSE_PENDING)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            restarted.prepare("EV-02", self.review, self.request)

        # Model a fresh P5 process: volatile evidence-registration memory is
        # gone, while the persisted workflow and copied response remain.
        from src.ai_copilot import token_count_evidence
        token_count_evidence._VERIFIED_RUNNER_EVIDENCE.clear()
        record, evidence = restarted.collect_response(
            prepared.request_id, "EV-01", self.review, self.request)
        self.assertEqual(record.state, TokenCountWorkflowState.COLLECTED)
        self.assertEqual(evidence.runner_request_id, prepared.request_id)

    def test_unknown_transport_and_response_persistence_failure_never_retry(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        timeout_transport = FakeTransport(error=TimeoutError("synthetic uncertain transport"))
        with self.assertRaisesRegex(RunnerError, "UNKNOWN"):
            self._host_execute(prepared.request_id, transport=timeout_transport)
        self.assertEqual(len(timeout_transport.calls), 1)
        self.workflow.mark_unknown(prepared.request_id)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            self.workflow.prepare("EV-02", self.review, self.request)

    def test_runner_known_identity_cannot_be_redispatched_after_response_write_failure(self):
        prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.create_windows_handoff(prepared.request_id)
        blocked_response_parent = self.base / "not-a-directory"
        blocked_response_parent.write_text("occupied", encoding="utf-8")
        fake_transport = FakeTransport()
        with self.assertRaisesRegex(RunnerError, "do not resubmit"):
            self._host_execute(prepared.request_id, transport=fake_transport,
                               response_dir=blocked_response_parent / "responses")
        self.assertEqual(len(fake_transport.calls), 1)
        # Runner state itself rejects the same request identity on restart.
        source = self.host_exchange / "requests" / f"{prepared.request_id}.json"
        validated = read_request_file(source)
        restarted_runner = ApiRunner(
            FakeCredentials(), FakeTransport(), ExecutionStateStore(self.host_state))
        with self.assertRaisesRegex(RunnerError, "already recorded"):
            restarted_runner.execute(validated, self.host_exchange / "responses", confirm=True)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.AWAITING_HOST_EXECUTION)


if __name__ == "__main__":
    unittest.main()
