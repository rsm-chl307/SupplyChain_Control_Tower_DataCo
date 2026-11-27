"""Offline tests for the single-command P5 local token-count operator flow."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.ai_copilot.local_token_count_e2e import main
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator,
    TokenCountWorkflowState,
)
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV
from tests.test_windows_api_runner import FakeCredentials, FakeTransport
from tools.windows_api_runner.api_runner import (
    ApiRunner,
    ExecutionStateStore,
    read_request_file,
)


class LocalTokenCountOperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-local-e2e-operator-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exchange = self.root / "container-exchange"
        self.host_exchange = self.root / "fake-windows-exchange"
        self.host_state = self.root / "fake-windows-state.sqlite3"
        self.env = patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(self.exchange)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _fake_host_response(self):
        requests = list((self.exchange / "requests").glob("*.json"))
        self.assertEqual(len(requests), 1)
        request = read_request_file(requests[0])
        (self.host_exchange / "responses").mkdir(parents=True, exist_ok=True)
        runner = ApiRunner(
            FakeCredentials("synthetic-test-credential"),
            FakeTransport(),
            ExecutionStateStore(self.host_state),
        )
        result = runner.execute(
            request, self.host_exchange / "responses", confirm=True)
        self.assertEqual(result["runner_execution_status"], "SUCCEEDED")
        shutil.copy2(
            self.host_exchange / "responses" / f"{request.package['request_id']}.json",
            self.exchange / "responses" / f"{request.package['request_id']}.json")
        return request.package["request_id"]

    def test_one_command_waits_and_collects_fake_runner_evidence(self):
        observed = {}
        calls = 0

        def worker_tick(_seconds):
            nonlocal calls
            calls += 1
            observed["request_id"] = self._fake_host_response()

        stdout, stderr = StringIO(), StringIO()
        with patch("src.ai_copilot.local_token_count_e2e.time.sleep", side_effect=worker_tick), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--case", "EV-01", "--windows-exchange",
                              r"C:\SupplyChainCopilot\api_exchange"])

        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertIn("P5 Input Token Count workflow collected successfully", stdout.getvalue())
        self.assertIn("Exact input_tokens: 1234", stdout.getvalue())
        self.assertIn("Evidence gate: PASS", stdout.getvalue())
        self.assertIn("background Worker", stdout.getvalue())
        self.assertEqual(calls, 1)
        self.assertIn(observed["request_id"], stdout.getvalue())
        self.assertNotIn("EXECUTE", stdout.getvalue())
        workflow = P5TokenCountOrchestrator(exchange_path=self.exchange)
        record = workflow.record_for_request(observed["request_id"])
        self.assertEqual(record.state, TokenCountWorkflowState.COLLECTED)
        self.assertEqual(record.case_id, "EV-01")

    def test_interrupt_marks_original_uuid_unknown_and_restart_cannot_replace_it(self):
        stdout, stderr = StringIO(), StringIO()
        with patch("src.ai_copilot.local_token_count_e2e.time.sleep", side_effect=KeyboardInterrupt), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--case", "EV-01"])
        self.assertEqual(exit_code, 130)
        self.assertIn("UNKNOWN", stderr.getvalue())

        workflow = P5TokenCountOrchestrator(exchange_path=self.exchange)
        rows = workflow.records()
        self.assertEqual(len(rows), 1)
        original_id = rows[0].request_id
        self.assertEqual(rows[0].state, TokenCountWorkflowState.UNKNOWN)

        with patch("src.ai_copilot.local_token_count_e2e.SyntheticHarness") as harness:
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                retry_exit = main(["--case", "EV-01"])
            harness.assert_not_called()
        self.assertEqual(retry_exit, 2)
        self.assertIn(original_id, stderr.getvalue())
        self.assertEqual(workflow.records()[0].request_id, original_id)
        self.assertEqual(workflow.records()[0].state, TokenCountWorkflowState.UNKNOWN)

    def test_status_does_not_create_a_run(self):
        stdout = StringIO()
        with patch("src.ai_copilot.local_token_count_e2e.SyntheticHarness") as harness, \
                redirect_stdout(stdout):
            exit_code = main(["--status"])
        harness.assert_not_called()
        self.assertEqual(exit_code, 0)
        self.assertIn("no recorded requests", stdout.getvalue())
        self.assertFalse((self.exchange / ".p5_token_count_workflow.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
