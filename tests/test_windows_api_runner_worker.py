"""Offline Worker/policy tests. Every transport and credential is synthetic."""
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked, TokenCountWorkflowState,
)
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV
from src.synthetic_context import SyntheticHarness
from tests.test_windows_api_runner import FakeCredentials, FakeTransport
from tools.windows_api_runner.api_runner import (
    ALLOWED_MODEL, OPERATION, ApiRunner, ExecutionStateStore, HttpResult,
    RunnerError, canonical_json_bytes,
)
from tools.windows_api_runner.auto_run_policy import LocalAutoRunPolicy
from tools.windows_api_runner.worker import DockerCliExchange, WindowsRunnerWorker


def request_package(case_id="EV-01", run_id="run-synthetic-01"):
    payload = {"model": ALLOWED_MODEL, "input": "synthetic worker fixture", "store": False}
    return {
        "request_id": "00000000-0000-4000-8000-000000000101",
        "case_id": case_id, "run_id": run_id, "operation": OPERATION,
        "model": ALLOWED_MODEL, "payload": payload,
        "payload_digest": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def enabled_policy(*, cases=("EV-01",), daily=1):
    return LocalAutoRunPolicy(True, (OPERATION,), (ALLOWED_MODEL,), tuple(cases),
                              daily, 1_048_576, 786_432)


class DockerCliExchangeTests(unittest.TestCase):
    def test_response_upload_is_read_back_and_byte_verified_without_docker(self):
        temp = tempfile.TemporaryDirectory(prefix="docker-cli-exchange-test-")
        self.addCleanup(temp.cleanup)
        remote_files = {}
        container = "codex-sandbox-lab-005"
        root = "/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange"

        def fake_command(args, **_kwargs):
            if args[:3] == ["docker", "exec", container]:
                return SimpleNamespace(returncode=0 if args[-1] in remote_files else 1)
            if args[:2] == ["docker", "cp"]:
                source, destination = args[2], args[3]
                if source.startswith(container + ":"):
                    remote = source.split(":", 1)[1]
                    Path(destination).write_bytes(remote_files[remote])
                elif destination.startswith(container + ":"):
                    remote_dir = destination.split(":", 1)[1]
                    remote_files[remote_dir.rstrip("/") + "/" + Path(source).name] = Path(source).read_bytes()
                else:
                    raise AssertionError("Unexpected synthetic Docker CLI arguments")
                return SimpleNamespace(returncode=0)
            raise AssertionError("Unexpected synthetic Docker CLI command")

        exchange = DockerCliExchange(
            container, root, Path(temp.name) / "host-exchange",
            command_runner=fake_command)
        request_id = "00000000-0000-4000-8000-000000000222"
        response = exchange.responses_dir / f"{request_id}.json"
        response.write_bytes(b'{"synthetic":true}\n')
        exchange.upload_response(response, request_id)
        remote = f"{root}/responses/{request_id}.json"
        self.assertEqual(remote_files[remote], response.read_bytes())


class FakeExchange:
    def __init__(self, root: Path, container_response_dir: Path | None = None):
        self.root = root
        self.container_response_dir = container_response_dir
        self.requests_dir = root / "requests"
        self.responses_dir = root / "responses"
        self.requests_dir.mkdir(parents=True)
        self.responses_dir.mkdir(parents=True)
        self.container_requests = []
        self.container_responses = {}
        self.fetches = 0
        self.uploads = []

    def fetch_requests(self):
        self.fetches += 1
        for package in self.container_requests:
            path = self.requests_dir / f"{package['request_id']}.json"
            if not path.exists():
                path.write_bytes(canonical_json_bytes(package) + b"\n")
        return tuple(sorted(self.requests_dir.glob("*.json")))

    def upload_response(self, response_path, request_id):
        raw = Path(response_path).read_bytes()
        existing = self.container_responses.get(request_id)
        if existing is not None and existing != raw:
            raise RunnerError("A different Container response already exists")
        self.container_responses[request_id] = raw
        self.uploads.append(request_id)
        if self.container_response_dir is not None:
            self.container_response_dir.mkdir(parents=True, exist_ok=True)
            destination = self.container_response_dir / f"{request_id}.json"
            if destination.exists() and destination.read_bytes() != raw:
                raise RunnerError("Conflicting response exists in the Container exchange")
            if not destination.exists():
                destination.write_bytes(raw)


class WindowsRunnerWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="windows-runner-worker-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exchange = FakeExchange(self.root / "exchange")
        self.credentials = FakeCredentials("synthetic-only-test-key")
        self.transport = FakeTransport()
        self.state = ExecutionStateStore(self.root / "private" / "runner.sqlite3")
        self.runner = ApiRunner(self.credentials, self.transport, self.state)
        self.policy_path = self.root / "local-policy.json"
        self.policy_path.write_text("{}", encoding="utf-8")
        self.policy = enabled_policy()
        self.worker = WindowsRunnerWorker(
            exchange=self.exchange, runner=self.runner, policy_path=self.policy_path,
            policy_loader=lambda _path: self.policy)

    def test_wrong_request_filename_is_rejected_without_dispatch(self):
        package = request_package()
        wrong_path = self.exchange.requests_dir / "00000000-0000-4000-8000-000000000099.json"
        wrong_path.write_bytes(canonical_json_bytes(package) + b"\n")
        captured = io.StringIO()
        logger = logging.Logger("synthetic-filename-rejection")
        logger.addHandler(logging.StreamHandler(captured))
        self.worker.logger = logger
        self.assertEqual(self.worker._process_path(wrong_path, self.policy), 0)
        self.assertIn("filename does not match its UUID", captured.getvalue())
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])
        self.assertIsNone(self.state.execution(package["request_id"]))

    def test_missing_policy_defaults_disabled_and_does_not_poll_or_read_credentials(self):
        worker = WindowsRunnerWorker(
            exchange=self.exchange, runner=self.runner,
            policy_path=self.root / "missing-policy.json")
        self.exchange.container_requests.append(request_package())
        self.assertEqual(worker.poll_once(), 0)
        self.assertEqual(self.exchange.fetches, 0)
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])

    def test_allowed_request_auto_runs_once_and_duplicate_poll_only_recovers_response(self):
        package = request_package()
        self.exchange.container_requests.append(package)
        self.assertEqual(self.worker.poll_once(), 1)
        self.assertEqual(self.credentials.calls, 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(len(self.exchange.uploads), 1)
        raw = self.exchange.container_responses[package["request_id"]]
        self.assertNotIn(b"synthetic-only-test-key", raw)
        self.assertNotIn(b"synthetic-only-test-key", canonical_json_bytes(package))
        self.assertEqual(self.worker.poll_once(), 1)
        self.assertEqual(self.credentials.calls, 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.state.execution(package["request_id"])[5], "SUCCEEDED")

    def test_policy_denial_is_recorded_before_dispatch_and_returns_safe_status(self):
        package = request_package(case_id="EV-02")
        self.exchange.container_requests.append(package)
        self.worker.policy = enabled_policy(cases=("EV-01",))
        self.assertEqual(self.worker.poll_once(), 1)
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])
        response = json.loads(self.exchange.container_responses[package["request_id"]])
        self.assertEqual(response["runner_execution_status"], "FAILED_BEFORE_DISPATCH")
        self.assertIsNone(response["http_status"])
        self.assertNotIn("synthetic-only-test-key", json.dumps(response))
        self.assertEqual(self.state.execution(package["request_id"])[5], "FAILED_BEFORE_DISPATCH")

    def test_daily_request_cap_blocks_before_credential_or_transport(self):
        first = request_package(run_id="run-prior")
        from tools.windows_api_runner.api_runner import validate_request_package
        first_valid = validate_request_package(canonical_json_bytes(first))
        self.runner.execute(first_valid, self.exchange.responses_dir, confirm=True)
        second = request_package()
        second["request_id"] = "00000000-0000-4000-8000-000000000102"
        self.exchange.container_requests.append(second)
        self.credentials.calls = 0
        self.transport.calls.clear()
        self.worker.policy = enabled_policy(daily=1)
        self.assertEqual(self.worker.poll_once(), 1)
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])
        response = json.loads(self.exchange.container_responses[second["request_id"]])
        self.assertEqual(response["runner_execution_status"], "FAILED_BEFORE_DISPATCH")
        self.assertIn("Daily", response["runner_error"])

    def test_daily_dispatch_claim_is_atomic_across_workers(self):
        from tools.windows_api_runner.api_runner import validate_request_package
        packages = []
        for index in (201, 202):
            package = request_package(run_id=f"run-concurrent-{index}")
            package["request_id"] = f"00000000-0000-4000-8000-{index:012d}"
            packages.append(validate_request_package(canonical_json_bytes(package)))

        def claim(request):
            return self.state.claim_auto_dispatch(
                request, utc_date=datetime.now(timezone.utc).date().isoformat(),
                max_requests=1)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, packages))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.state.dispatched_today(
            datetime.now(timezone.utc).date().isoformat()), 1)
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])

    def test_unknown_transport_is_persisted_and_never_retried_after_restart(self):
        package = request_package()
        self.exchange.container_requests.append(package)
        self.transport.error = TimeoutError("synthetic uncertain transport")
        self.assertEqual(self.worker.poll_once(), 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.state.execution(package["request_id"])[5], "UNKNOWN")
        response = json.loads(self.exchange.container_responses[package["request_id"]])
        self.assertEqual(response["runner_execution_status"], "UNKNOWN")
        restarted = WindowsRunnerWorker(
            exchange=self.exchange, runner=self.runner, policy_path=self.policy_path,
            policy_loader=lambda _path: self.policy)
        restarted.poll_once()
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.credentials.calls, 1)

    def test_transport_exception_text_cannot_leak_fake_credential_to_worker_logs(self):
        package = request_package()
        self.exchange.container_requests.append(package)
        self.transport.error = RuntimeError("synthetic-only-test-key in fake transport error")
        output = io.StringIO()
        logger = logging.Logger("synthetic-worker-log-test")
        logger.addHandler(logging.StreamHandler(output))
        worker = WindowsRunnerWorker(
            exchange=self.exchange, runner=self.runner, policy_path=self.policy_path,
            policy_loader=lambda _path: self.policy, logger=logger)
        worker.poll_once()
        self.assertEqual(self.state.execution(package["request_id"])[5], "UNKNOWN")
        self.assertNotIn("synthetic-only-test-key", output.getvalue())
        self.assertNotIn("synthetic-only-test-key",
                         self.exchange.container_responses[package["request_id"]].decode())

    def test_in_progress_restart_becomes_unknown_without_transport(self):
        package = request_package()
        from tools.windows_api_runner.api_runner import validate_request_package
        validated = validate_request_package(canonical_json_bytes(package))
        self.state.receive(validated)
        self.state.transition(package["request_id"], "RECEIVED", "IN_PROGRESS")
        self.exchange.container_requests.append(package)
        self.worker.poll_once()
        self.assertEqual(self.state.execution(package["request_id"])[5], "UNKNOWN")
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.credentials.calls, 0)

    def test_invalid_package_is_rejected_without_credentials_or_provider(self):
        package = request_package()
        package["payload_digest"] = "0" * 64
        self.exchange.container_requests.append(package)
        self.worker.poll_once()
        self.assertEqual(self.credentials.calls, 0)
        self.assertEqual(self.transport.calls, [])

    def test_worker_stop_event_and_single_poll(self):
        stop = threading.Event()
        self.worker.poll_once = lambda: stop.set() or 0
        self.worker.run_forever(poll_seconds=1, stop_event=stop)


class P5WorkerEndToEndTests(unittest.TestCase):
    def test_fake_prepare_worker_exchange_collect_and_evidence_gate(self):
        from unittest.mock import patch
        temp = tempfile.TemporaryDirectory(prefix="p5-worker-e2e-test-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        container_exchange = root / "container-exchange"
        state_path = root / "workflow.sqlite3"
        host_exchange = FakeExchange(
            root / "windows-exchange", container_response_dir=container_exchange / "responses")
        env = patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(container_exchange)})
        env.start()
        self.addCleanup(env.stop)
        harness = SyntheticHarness()
        self.addCleanup(harness.close)
        review = prepare_brief(harness, harness.issue("Baseline"), max_records=2).review
        request = build_request(review, model_snapshot=ALLOWED_MODEL,
                                max_output_tokens=25000, timeout_seconds=180,
                                execution_profile="P5_PAID_ACCEPTANCE")
        orchestrator = P5TokenCountOrchestrator(exchange_path=container_exchange,
                                                state_path=state_path)
        prepared = orchestrator.prepare("EV-01", review, request)
        orchestrator.create_windows_handoff(prepared.request_id)
        package = json.loads(prepared.package_path.read_text(encoding="utf-8"))
        host_exchange.container_requests.append(package)
        credentials = FakeCredentials("e2e-synthetic-credential")
        transport = FakeTransport(HttpResult(
            200, "req_synthetic_count", b'{"model":"gpt-6-luna","input_tokens":1234}'))
        host_state = ExecutionStateStore(root / "host-state.sqlite3")
        runner = ApiRunner(credentials, transport, host_state)
        policy_path = root / "policy.json"
        policy_path.write_text("synthetic local policy fixture", encoding="utf-8")
        worker = WindowsRunnerWorker(
            exchange=host_exchange, runner=runner, policy_path=policy_path,
            policy_loader=lambda _path: enabled_policy())

        self.assertEqual(worker.poll_once(), 1)
        self.assertIn(prepared.request_id, host_exchange.container_responses)
        response_path = container_exchange / "responses" / f"{prepared.request_id}.json"
        self.assertTrue(response_path.is_file())
        orchestrator.mark_response_pending(prepared.request_id)
        record, evidence = orchestrator.collect_response(
            prepared.request_id, "EV-01", review, request)
        self.assertEqual(record.state, TokenCountWorkflowState.COLLECTED)
        self.assertEqual(evidence.input_tokens, 1234)
        self.assertEqual(evidence.runner_request_id, prepared.request_id)
        self.assertEqual(evidence.full_payload_sha256, prepared.payload_digest)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(credentials.calls, 1)


if __name__ == "__main__":
    unittest.main()
