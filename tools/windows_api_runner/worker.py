"""Opt-in Windows worker: fixed Docker exchange, fixed count endpoint, local policy."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path, PurePosixPath
import subprocess
import threading
import time
import uuid

from tools.windows_api_runner.api_runner import (
    ApiRunner, ExecutionStateStore, RunnerError, UrllibTransport,
    WindowsCredentialManager, read_request_file,
)
from tools.windows_api_runner.auto_run_policy import LocalAutoRunPolicy


DEFAULT_CONTAINER = "codex-sandbox-lab-005"
DEFAULT_CONTAINER_EXCHANGE = (
    "/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange")
DEFAULT_WINDOWS_EXCHANGE = Path(r"C:\SupplyChainCopilot\api_exchange")
DEFAULT_POLL_SECONDS = 3.0


class DockerCliExchange:
    """Only performs fixed docker cp/exists commands; requests cannot choose paths."""

    def __init__(self, container: str, container_exchange: str,
                 local_exchange: str | Path, *, command_runner=subprocess.run):
        if not container or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in container):
            raise RunnerError("Container name is invalid")
        remote = PurePosixPath(container_exchange)
        if (not remote.is_absolute() or ".." in remote.parts
                or str(remote) != container_exchange.rstrip("/")):
            raise RunnerError("Container exchange path must be a normalized absolute path")
        self.container = container
        self.container_exchange = str(remote)
        self.local_exchange = Path(local_exchange).resolve()
        self.requests_dir = self.local_exchange / "requests"
        self.responses_dir = self.local_exchange / "responses"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        self.command_runner = command_runner

    def _run(self, args: list[str], *, check: bool = True):
        try:
            result = self.command_runner(args, capture_output=True, text=True,
                                        timeout=30, check=False)
        except Exception as exc:
            raise RunnerError("Docker CLI exchange is unavailable") from None
        if check and result.returncode != 0:
            raise RunnerError("Docker CLI exchange command failed")
        return result

    def fetch_requests(self) -> tuple[Path, ...]:
        source = f"{self.container}:{self.container_exchange}/requests/."
        self._run(["docker", "cp", source, str(self.requests_dir)])
        return tuple(sorted(path for path in self.requests_dir.iterdir()
                            if path.name.endswith(".json")))

    def has_response(self, request_id: str) -> bool:
        _uuid(request_id)
        remote = f"{self.container_exchange}/responses/{request_id}.json"
        result = self._run(["docker", "exec", self.container, "test", "-e", remote], check=False)
        if result.returncode not in (0, 1):
            raise RunnerError("Container response check failed")
        return result.returncode == 0

    def upload_response(self, response_path: str | Path, request_id: str) -> None:
        _uuid(request_id)
        source = Path(response_path).resolve(strict=True)
        if source.parent != self.responses_dir.resolve():
            raise RunnerError("Response is outside the host exchange")
        remote = f"{self.container_exchange}/responses/{request_id}.json"
        if self.has_response(request_id):
            if not self._remote_response_matches(remote, source.read_bytes(), request_id):
                raise RunnerError("A different Container response already exists")
            return
        self._run(["docker", "cp", str(source),
                   f"{self.container}:{self.container_exchange}/responses/"])
        if not self.has_response(request_id):
            raise RunnerError("Response transfer could not be verified")
        if not self._remote_response_matches(remote, source.read_bytes(), request_id):
            raise RunnerError("Response transfer content does not match the host result")

    def _remote_response_matches(self, remote: str, expected: bytes, request_id: str) -> bool:
        temp_dir = self.local_exchange / "verify"
        temp_dir.mkdir(exist_ok=True)
        remote_copy = temp_dir / f"{request_id}.json"
        remote_copy.unlink(missing_ok=True)
        self._run(["docker", "cp", f"{self.container}:{remote}", str(remote_copy)])
        try:
            return remote_copy.is_file() and remote_copy.read_bytes() == expected
        finally:
            remote_copy.unlink(missing_ok=True)


class WindowsRunnerWorker:
    """Poll and process packages once each; durable Runner state prevents retries."""

    def __init__(self, *, exchange: DockerCliExchange, runner: ApiRunner,
                 policy_path: str | Path, logger: logging.Logger | None = None,
                 policy_loader=LocalAutoRunPolicy.load):
        self.exchange = exchange
        self.runner = runner
        self.policy_path = Path(policy_path)
        self.policy_loader = policy_loader
        self.logger = logger or logging.getLogger("supplychain.windows_runner.worker")
        self._poll_lock = threading.Lock()

    def poll_once(self) -> int:
        """Return processed/collected count; disabled policy causes no Docker or credential access."""
        if not self._poll_lock.acquire(blocking=False):
            return 0
        try:
            try:
                policy = self.policy_loader(self.policy_path)
            except RunnerError as exc:
                self.logger.error("Auto-run policy rejected: %s", str(exc))
                return 0
            if not policy.enabled:
                return 0
            try:
                requests = self.exchange.fetch_requests()
            except RunnerError as exc:
                self.logger.warning("Exchange poll failed: %s", str(exc))
                return 0
            completed = 0
            for path in requests:
                try:
                    completed += self._process_path(path, policy)
                except RunnerError as exc:
                    # RunnerError messages are intentionally credential-scrubbed.
                    self.logger.error("Request processing stopped: %s", str(exc))
                except Exception as exc:
                    # Do not log exception values or stack locals on the credential host.
                    self.logger.error("Request processing stopped (%s)", type(exc).__name__)
            return completed
        finally:
            self._poll_lock.release()

    def _process_path(self, path: Path, policy: LocalAutoRunPolicy) -> int:
        try:
            request = read_request_file(path)
        except RunnerError as exc:
            self.logger.error("Rejected invalid Request Package (%s)", type(exc).__name__)
            return 0
        package = request.package
        request_id = package["request_id"]
        if path.name != f"{request_id}.json":
            self.logger.error("Rejected request whose filename does not match its UUID")
            return 0

        state = self.runner.state_store.execution(request_id)
        if state is not None:
            expected = (package["case_id"], package["run_id"], package["operation"],
                        request.payload_digest)
            actual = (state[1], state[2], state[3], state[4])
            if expected != actual:
                self.logger.error("Existing UUID has different identity; no redispatch")
                return 0
            return self._recover_existing(request, state)

        day = datetime.now(timezone.utc).date().isoformat()
        deny = policy.denial_reason(
            package, path.stat().st_size,
            self.runner.state_store.dispatched_today(day))
        if deny:
            self._record_pre_dispatch_failure(request, deny)
            return 1

        day = datetime.now(timezone.utc).date().isoformat()
        if not self.runner.state_store.claim_auto_dispatch(
                request, utc_date=day,
                max_requests=policy.max_requests_per_utc_day):
            self.runner.write_local_status_response(
                request, self.exchange.responses_dir,
                status="FAILED_BEFORE_DISPATCH",
                safe_error="Daily local API request limit reached")
            self.exchange.upload_response(
                self.exchange.responses_dir / f"{request_id}.json", request_id)
            return 1

        try:
            self.runner.execute(request, self.exchange.responses_dir, confirm=True,
                                already_received=True)
        except RunnerError as exc:
            state = self.runner.state_store.execution(request_id)
            if state is None:
                self.logger.error("Runner stopped before recording request")
                return 0
            if state[5] == "FAILED_BEFORE_DISPATCH":
                self.runner.write_local_status_response(
                    request, self.exchange.responses_dir,
                    status="FAILED_BEFORE_DISPATCH", safe_error=str(exc))
            elif state[5] == "UNKNOWN":
                self.runner.write_local_status_response(
                    request, self.exchange.responses_dir,
                    status="UNKNOWN", safe_error="Transport or response outcome is uncertain")
        response = self.exchange.responses_dir / f"{request_id}.json"
        if response.is_file():
            self.exchange.upload_response(response, request_id)
            return 1
        return 0

    def _record_pre_dispatch_failure(self, request, reason: str) -> None:
        try:
            self.runner.state_store.receive(request)
        except RunnerError:
            # Case/Run/operation/payload duplicate under another UUID is denied too.
            pass
        else:
            self.runner.state_store.transition(
                request.package["request_id"], "RECEIVED", "FAILED_BEFORE_DISPATCH",
                safe_error=reason[:500])
        response_path = self.exchange.responses_dir / f"{request.package['request_id']}.json"
        if not response_path.exists():
            self.runner.write_local_status_response(
                request, self.exchange.responses_dir,
                status="FAILED_BEFORE_DISPATCH", safe_error=reason)
        self.exchange.upload_response(response_path, request.package["request_id"])

    def _recover_existing(self, request, state: tuple) -> int:
        request_id, saved_state = state[0], state[5]
        response = self.exchange.responses_dir / f"{request_id}.json"
        saved_path = Path(state[7]) if state[7] else None
        if not response.exists() and saved_path and saved_path.is_file():
            response.write_bytes(saved_path.read_bytes())
        if saved_state == "IN_PROGRESS":
            self.runner.state_store.transition(
                request_id, "IN_PROGRESS", "UNKNOWN",
                safe_error="Worker restart found a dispatch with no terminal record")
            saved_state = "UNKNOWN"
        elif saved_state == "RECEIVED":
            self.runner.state_store.transition(
                request_id, "RECEIVED", "FAILED_BEFORE_DISPATCH",
                safe_error="Worker restart found a request not dispatched")
            saved_state = "FAILED_BEFORE_DISPATCH"
        if not response.exists() and saved_state in {"UNKNOWN", "FAILED_BEFORE_DISPATCH"}:
            self.runner.write_local_status_response(
                request, self.exchange.responses_dir, status=saved_state,
                safe_error=("Prior dispatch outcome is uncertain" if saved_state == "UNKNOWN"
                            else "Request was not dispatched"))
        if response.is_file():
            self.exchange.upload_response(response, request_id)
            return 1
        self.logger.error("Existing request has no recoverable response; no redispatch")
        return 0

    def run_forever(self, *, poll_seconds: float = DEFAULT_POLL_SECONDS,
                    stop_event: threading.Event | None = None) -> None:
        if not 1 <= poll_seconds <= 60:
            raise RunnerError("Worker poll interval is outside its allowed range")
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            self.poll_once()
            stop_event.wait(poll_seconds)


def _uuid(value: str) -> None:
    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise RunnerError("Request UUID is invalid") from None


def _host_paths() -> tuple[Path, Path, Path, Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RunnerError("LOCALAPPDATA is unavailable")
    root = Path(local_app_data) / "SupplyChainCopilot"
    exchange = DEFAULT_WINDOWS_EXCHANGE
    state = root / "runner_state.sqlite3"
    policy = root / "auto_run_policy.json"
    log_dir = root / "logs"
    exchange.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return exchange, state, policy, log_dir


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Local Windows Input Token Count background worker")
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--container-exchange", default=DEFAULT_CONTAINER_EXCHANGE)
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--once", action="store_true", help="Run one safe poll for diagnostics")
    args = parser.parse_args(argv)
    try:
        exchange_root, state_path, policy_path, log_dir = _host_paths()
        logger = logging.getLogger("supplychain.windows_runner.worker")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.FileHandler(log_dir / "worker.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        file_exchange = DockerCliExchange(args.container, args.container_exchange,
                                         exchange_root)
        state = ExecutionStateStore(state_path)
        runner = ApiRunner(WindowsCredentialManager(), UrllibTransport(), state)
        worker = WindowsRunnerWorker(exchange=file_exchange, runner=runner,
                                     policy_path=policy_path, logger=logger)
        if args.once:
            print(f"Worker poll complete; handled {worker.poll_once()} response(s).")
            return 0
        worker.run_forever(poll_seconds=args.poll_seconds)
        return 0
    except RunnerError as exc:
        print(f"Worker stopped: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
