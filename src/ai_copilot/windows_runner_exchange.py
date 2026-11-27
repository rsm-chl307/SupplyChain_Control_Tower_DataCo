"""P5 Input Token Count bridge to the manual Windows host-runner exchange.

This module prepares and reconciles one-shot count packages. It contains no
credential access, HTTP transport, Ledger mutation, or Generation operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.quality_evaluation import CORPUS_VERSION
from src.ai_copilot.provider import ProviderRequest, OpenAIResponsesAdapter
from src.ai_copilot.eight_call_campaign import CASE_IDS
from src.ai_copilot.token_count_evidence import (
    ExactTokenCount, _register_verified_runner_evidence,
)
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from tools.windows_api_runner.api_runner import (
    ALLOWED_MODEL, OPERATION, MAX_PACKAGE_BYTES, canonical_json_bytes,
    validate_request_package,
)

EXCHANGE_PATH_ENV = "P5_WINDOWS_RUNNER_EXCHANGE_PATH"
DEFAULT_EXCHANGE_PATH = Path(__file__).resolve().parents[2] / "tmp" / "windows_runner_exchange"


class RunnerExchangeBlocked(RuntimeError):
    """Package validation or host-runner reconciliation failed closed."""


class RunnerResponsePending(RunnerExchangeBlocked):
    """The operator has not yet processed the prepared package on Windows."""


class RunnerResponseIdentityMismatch(RunnerExchangeBlocked):
    """Response package identity does not match the prepared P5 request."""


class RunnerResponseDigestMismatch(RunnerExchangeBlocked):
    """Response or reconstructed payload digest does not match preparation."""


class RunnerHTTPStatusError(RunnerExchangeBlocked):
    """The host Runner returned a non-success HTTP status."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class RunnerExecutionFailure(RunnerExchangeBlocked):
    """The host Runner did not report a successful execution state."""


class RunnerMissingInputTokens(RunnerExchangeBlocked):
    """A successful count response did not contain an exact input_tokens value."""


@dataclass(frozen=True)
class PreparedCountRequest:
    request_id: str
    package_path: Path
    case_id: str
    run_id: str
    run_manifest_sha256: str
    brief_digest: str
    provider_request_digest: str
    payload_digest: str
    count_projection_digest: str


def _wire_digests(request: ProviderRequest) -> tuple[bytes, str, str]:
    return input_token_count_wire(request)


def _json_no_duplicates(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RunnerExchangeBlocked("Response package has duplicate fields")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RunnerExchangeBlocked("Response package is not valid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise RunnerExchangeBlocked("Response package must be an object")
    return value


def _validate_case_run(case_id: str, review: ValidatedBrief) -> dict:
    corpus_path = (Path(__file__).resolve().parents[2] /
                   "docs/ai_copilot/p5_offline_evaluation/cases.v2.json")
    try:
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        if corpus.get("dataset_version") != CORPUS_VERSION:
            raise ValueError("P5 case corpus version mismatch")
        case = next(item for item in corpus["cases"] if item.get("id") == case_id)
        brief = review.verify()
        draft = review._draft
        context = draft._bundle._context
        if (draft._bundle._harness._fixture_id != case["fixture_id"]
                or draft.max_records != case["max_records"]
                or brief["run_context"]["Scenario"] != case["scenario"]
                or bool(brief["run_context"]["Comparison_ID"]) != case["comparison"]):
            raise ValueError("P5 case and Trusted Run differ")
        return {"run_id": context.run_id, "manifest_sha256": context.manifest_sha256}
    except Exception as exc:
        raise RunnerExchangeBlocked("Case definition or Trusted Run identity is invalid") from exc


class WindowsHostTokenCountExchange:
    """Write a P5-bound count request and reconcile the host-written response."""

    def __init__(self, exchange_path: str | Path):
        self.exchange_path = Path(exchange_path).resolve()

    def prepare(self, case_id: str, review: ValidatedBrief,
                request: ProviderRequest) -> PreparedCountRequest:
        if (type(review) is not ValidatedBrief or type(request) is not ProviderRequest
                or request.execution_profile != "P5_PAID_ACCEPTANCE"
                or request.model_snapshot != ALLOWED_MODEL):
            raise RunnerExchangeBlocked("Trusted P5 Brief and approved model are required")
        try:
            identity = _validate_case_run(case_id, review)
            full_wire, full_digest, projection_digest = _wire_digests(request)
        except Exception as exc:
            raise RunnerExchangeBlocked("P5 payload or Run identity could not be verified") from exc
        if (case_id not in CASE_IDS
                or request.brief_digest != review.content_digest
                or len(full_wire) > 786432):
            raise RunnerExchangeBlocked("P5 Case, Brief or payload identity is invalid")
        request_id = str(uuid.uuid4())
        package = {
            "request_id": request_id, "case_id": case_id,
            "run_id": identity["run_id"], "operation": OPERATION,
            "model": request.model_snapshot, "payload": json.loads(full_wire),
            "payload_digest": full_digest, "created_at": datetime.now(timezone.utc).isoformat(),
            "brief_digest": request.brief_digest,
            "provider_request_digest": request.request_digest,
            "count_projection_digest": projection_digest,
            "run_manifest_sha256": identity["manifest_sha256"],
        }
        try:
            raw = canonical_json_bytes(package)
            if len(raw) > MAX_PACKAGE_BYTES:
                raise RunnerExchangeBlocked("P5 request package exceeds Runner limit")
            validated = validate_request_package(raw)
            request_dir = self.exchange_path / "requests"
            response_dir = self.exchange_path / "responses"
            request_dir.mkdir(parents=True, exist_ok=True)
            response_dir.mkdir(parents=True, exist_ok=True)
            package_path = request_dir / f"{request_id}.json"
            temporary_path = package_path.with_suffix(".json.tmp")
            with temporary_path.open("xb") as stream:
                stream.write(raw + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary_path, package_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            if validated.payload_digest != full_digest:
                raise RunnerExchangeBlocked("Runner package serializer changed the payload digest")
        except RunnerExchangeBlocked:
            raise
        except Exception as exc:
            raise RunnerExchangeBlocked("P5 request package could not be safely written") from exc
        return PreparedCountRequest(request_id, package_path, case_id, identity["run_id"],
                                    identity["manifest_sha256"], request.brief_digest,
                                    request.request_digest, full_digest, projection_digest)

    def load_prepared(self, request_id: str, case_id: str, review: ValidatedBrief,
                      request: ProviderRequest) -> PreparedCountRequest:
        """Rehydrate a pending package after restart; never creates or resends it."""
        try:
            uuid.UUID(request_id)
            if (type(review) is not ValidatedBrief or type(request) is not ProviderRequest
                    or request.execution_profile != "P5_PAID_ACCEPTANCE"
                    or request.model_snapshot != ALLOWED_MODEL):
                raise RunnerExchangeBlocked("Trusted P5 Brief and approved model are required")
            review.verify()
            if request.brief_digest != review.content_digest:
                raise RunnerExchangeBlocked("Persisted request Brief identity is stale")
            identity = _validate_case_run(case_id, review)
            package_path = self.exchange_path / "requests" / f"{request_id}.json"
            info = package_path.lstat()
            if package_path.is_symlink() or not package_path.is_file() or info.st_size > MAX_PACKAGE_BYTES:
                raise RunnerExchangeBlocked("Prepared request must be a regular bounded package")
            runner_package = validate_request_package(package_path.read_bytes()).package
            full_wire, full_digest, projection_digest = _wire_digests(request)
        except RunnerExchangeBlocked:
            raise
        except Exception as exc:
            raise RunnerExchangeBlocked("Prepared count request could not be reloaded") from exc
        expected = {
            "request_id": request_id, "case_id": case_id, "run_id": identity["run_id"],
            "operation": OPERATION, "model": ALLOWED_MODEL,
            "payload_digest": full_digest, "brief_digest": request.brief_digest,
            "provider_request_digest": request.request_digest,
            "count_projection_digest": projection_digest,
            "run_manifest_sha256": identity["manifest_sha256"],
        }
        if (any(runner_package.get(key) != value for key, value in expected.items())
                or canonical_json_bytes(runner_package.get("payload")) != full_wire):
            raise RunnerExchangeBlocked("Persisted request differs from current Run or payload")
        return PreparedCountRequest(request_id, package_path, case_id, identity["run_id"],
                                    identity["manifest_sha256"], request.brief_digest,
                                    request.request_digest, full_digest, projection_digest)

    def collect(self, prepared: PreparedCountRequest, review: ValidatedBrief,
                request: ProviderRequest) -> ExactTokenCount:
        response_path = self.exchange_path / "responses" / f"{prepared.request_id}.json"
        try:
            info = response_path.lstat()
            if response_path.is_symlink() or not response_path.is_file() or info.st_size > MAX_PACKAGE_BYTES:
                raise RunnerExchangeBlocked("Runner response must be a regular bounded file")
            raw = response_path.read_bytes()
        except FileNotFoundError as exc:
            raise RunnerResponsePending("Host Runner response is not available yet") from exc
        except OSError as exc:
            raise RunnerExchangeBlocked("Runner response package could not be read") from exc
        response = _json_no_duplicates(raw)
        required = {
            "request_id", "case_id", "run_id", "payload_digest", "operation", "http_status",
            "openai_request_id", "model", "returned_model_id", "usage", "response_body",
            "executed_at", "runner_execution_status", "brief_digest", "provider_request_digest",
            "count_projection_digest", "run_manifest_sha256",
        }
        identity = {
            "request_id": prepared.request_id, "case_id": prepared.case_id,
            "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
            "operation": OPERATION, "model": ALLOWED_MODEL,
            "brief_digest": prepared.brief_digest,
            "provider_request_digest": prepared.provider_request_digest,
            "count_projection_digest": prepared.count_projection_digest,
            "run_manifest_sha256": prepared.run_manifest_sha256,
        }
        allowed_fields = (required, required | {"runner_error"})
        if set(response) not in allowed_fields:
            raise RunnerResponseIdentityMismatch("Runner response schema or identity fields mismatch")
        digest_fields = ("payload_digest", "count_projection_digest")
        if any(response.get(key) != identity[key] for key in digest_fields):
            raise RunnerResponseDigestMismatch("Runner response payload digest mismatch")
        identity_fields = set(identity) - set(digest_fields)
        if any(response.get(key) != identity[key] for key in identity_fields):
            raise RunnerResponseIdentityMismatch("Runner response identity mismatch")
        status = response["http_status"]
        runner_state = response["runner_execution_status"]
        if runner_state == "UNKNOWN":
            raise RunnerExecutionFailure("Windows Runner outcome is UNKNOWN; do not retry")
        if runner_state == "FAILED_BEFORE_DISPATCH":
            raise RunnerExecutionFailure("Windows Runner rejected request before dispatch")
        if status is None or type(status) is not int:
            raise RunnerExecutionFailure("Windows Runner did not provide a confirmed HTTP outcome")
        if status != 200:
            raise RunnerHTTPStatusError(f"Input Token Count endpoint returned HTTP {status}", status)
        if runner_state != "SUCCEEDED":
            raise RunnerExecutionFailure("Windows Runner reports execution failure or uncertainty")
        if (not isinstance(response["openai_request_id"], str)
                or not response["openai_request_id"]
                or not isinstance(response["executed_at"], str)):
            raise RunnerExecutionFailure("Successful Runner response lacks request metadata")
        body = response["response_body"]
        count = body.get("input_tokens") if type(body) is dict else None
        if type(count) is not int:
            raise RunnerMissingInputTokens("Successful count response is missing input_tokens")
        if not 0 <= count <= 25000:
            raise RunnerMissingInputTokens("input_tokens exceeds the approved 25000-token cap")
        returned_model = response["returned_model_id"]
        if (returned_model is not None and (not isinstance(returned_model, str)
                or not (returned_model == ALLOWED_MODEL or returned_model.startswith(ALLOWED_MODEL + "-")))):
            raise RunnerResponseIdentityMismatch("Returned model is outside the approved model family")
        if (type(review) is not ValidatedBrief or type(request) is not ProviderRequest
                or request.execution_profile != "P5_PAID_ACCEPTANCE"
                or request.request_digest != prepared.provider_request_digest
                or request.brief_digest != prepared.brief_digest
                or review.content_digest != prepared.brief_digest):
            raise RunnerExchangeBlocked("Current P5 request no longer matches the prepared request")
        review.verify()
        full_wire, full_digest, projection_digest = _wire_digests(request)
        identity = _validate_case_run(prepared.case_id, review)
        if (full_digest != prepared.payload_digest
                or projection_digest != prepared.count_projection_digest
                or identity["run_id"] != prepared.run_id
                or identity["manifest_sha256"] != prepared.run_manifest_sha256):
            raise RunnerResponseDigestMismatch("P5 payload or count projection digest changed after host count")
        evidence = ExactTokenCount(
            case_id=prepared.case_id, model=ALLOWED_MODEL, input_tokens=count,
            full_payload_sha256=full_digest,
            count_projection_sha256=projection_digest,
            request_id=response["openai_request_id"],
            run_id=prepared.run_id, run_manifest_sha256=prepared.run_manifest_sha256,
            brief_digest=prepared.brief_digest,
            provider_brief_digest=request.provider_brief_digest,
            provider_request_digest=request.request_digest,
            payload_bytes=len(full_wire), timestamp_utc=response["executed_at"],
            http_status=response["http_status"], runner_request_id=prepared.request_id,
            response_package_sha256=hashlib.sha256(raw).hexdigest(),
            returned_model_id=returned_model, evidence_source="WINDOWS_HOST_RUNNER")
        try:
            _register_verified_runner_evidence(evidence)
        except ValueError as exc:
            raise RunnerExchangeBlocked("Validated count evidence could not be registered") from exc
        return evidence


def configured_windows_token_count_exchange() -> WindowsHostTokenCountExchange:
    """Create the production file bridge from an explicit env path or repo default."""
    configured = os.environ.get(EXCHANGE_PATH_ENV)
    if configured is None:
        path = DEFAULT_EXCHANGE_PATH
    else:
        configured = configured.strip()
        if not configured or not Path(configured).is_absolute():
            raise RunnerExchangeBlocked(
                f"{EXCHANGE_PATH_ENV} must be a non-empty absolute container path")
        path = Path(configured)
    return WindowsHostTokenCountExchange(path)


def prepare_configured_count_request(case_id: str, review: ValidatedBrief,
                                     request: ProviderRequest) -> PreparedCountRequest:
    """Production entry point: prepare the exact request in the configured exchange."""
    return configured_windows_token_count_exchange().prepare(case_id, review, request)


def collect_configured_count_response(request_id: str, case_id: str,
                                      review: ValidatedBrief,
                                      request: ProviderRequest) -> ExactTokenCount:
    """Production entry point: reload and reconcile a copied-back host response."""
    exchange = configured_windows_token_count_exchange()
    prepared = exchange.load_prepared(request_id, case_id, review, request)
    return exchange.collect(prepared, review, request)
