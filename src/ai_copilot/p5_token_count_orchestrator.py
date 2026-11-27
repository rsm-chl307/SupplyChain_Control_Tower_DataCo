"""Fail-closed orchestration for manual P5 Input Token Count requests.

This module accepts an already trusted Run/Brief and an exact ProviderRequest.
It never creates business context, runs a provider, or changes the paid Ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pathlib import PureWindowsPath
import hashlib
import hmac
import json
import os
import re
import stat
import sqlite3
import secrets
import time
from contextlib import closing
import uuid

from src.ai_copilot.approval import ApprovalBlocked, ApprovalStore, OwnerVerifier
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.eight_call_campaign import CASE_IDS
from src.ai_copilot.input_token_count_payload import COUNT_FIELDS
from src.ai_copilot.provider import ProviderRequest
from src.ai_copilot.windows_runner_exchange import (
    PreparedCountRequest,
    RunnerExecutionFailure,
    RunnerHTTPStatusError,
    RunnerMissingInputTokens,
    RunnerResponseDigestMismatch,
    RunnerResponseIdentityMismatch,
    RunnerExchangeBlocked,
    RunnerResponsePending,
    configured_windows_token_count_exchange,
    collect_configured_count_response,
    prepare_configured_count_request,
)
from src.ai_copilot.token_count_evidence import require_exact_token_count
from tools.windows_api_runner.api_runner import (
    ALLOWED_MODEL, MAX_PACKAGE_BYTES, OPERATION, RunnerError,
    canonical_json_bytes, validate_request_package,
)


class TokenCountWorkflowBlocked(RuntimeError):
    """The count workflow cannot safely advance from its current state."""


class TokenCountWorkflowState(str, Enum):
    NOT_PREPARED = "NOT_PREPARED"
    PREPARED = "PREPARED"
    AWAITING_HOST_EXECUTION = "AWAITING_HOST_EXECUTION"
    RESPONSE_PENDING = "RESPONSE_PENDING"
    COLLECTED = "COLLECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CONFIRMED_FAILED = "CONFIRMED_FAILED"


@dataclass(frozen=True)
class TokenCountWorkflowRecord:
    case_id: str
    state: TokenCountWorkflowState
    request_id: str
    run_id: str
    run_manifest_sha256: str
    brief_digest: str
    provider_request_digest: str
    payload_sha256: str
    count_projection_sha256: str
    created_at_utc: str
    updated_at_utc: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TokenCountWorkflowRecord":
        return cls(
            case_id=row["case_id"], state=TokenCountWorkflowState(row["state"]),
            request_id=row["request_id"], run_id=row["run_id"],
            run_manifest_sha256=row["run_manifest_sha256"],
            brief_digest=row["brief_digest"],
            provider_request_digest=row["provider_request_digest"],
            payload_sha256=row["payload_sha256"],
            count_projection_sha256=row["count_projection_sha256"],
            created_at_utc=row["created_at_utc"], updated_at_utc=row["updated_at_utc"],
        )


@dataclass(frozen=True)
class ReconciliationAuthorization:
    """Short-lived, purpose-bound authentication of the configured local Owner."""

    reference: str
    owner_identity_ref: str
    purpose: str
    request_id: str
    case_id: str
    run_id: str
    request_sha256: str
    response_sha256: str
    disposition: str
    reason: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True)
class WindowsRunnerHandoff:
    case_id: str
    run_id: str
    request_id: str
    operation: str
    model: str
    payload_sha256: str
    count_projection_sha256: str
    brief_digest: str
    provider_request_digest: str
    run_manifest_sha256: str
    container_exchange_path: str
    windows_exchange_path: str
    request_container_path: str
    response_container_path: str
    request_windows_path: str
    response_windows_path: str
    windows_directory_setup: str
    docker_copy_to_windows: str
    runner_invocation: str
    docker_copy_to_container: str

    def to_markdown(self) -> str:
        """Render only request metadata and operator commands, never payload data."""
        return "\n".join((
            f"Case: {self.case_id}", f"Run: {self.run_id}",
            f"Request UUID: {self.request_id}", f"Operation: {self.operation}",
            f"Model: {self.model}", f"Payload SHA-256: {self.payload_sha256}",
            f"Count projection SHA-256: {self.count_projection_sha256}",
            f"Brief SHA-256: {self.brief_digest}",
            f"ProviderRequest SHA-256: {self.provider_request_digest}",
            f"Run manifest SHA-256: {self.run_manifest_sha256}", "",
            "Create local exchange folders:", f"`{self.windows_directory_setup}`", "",
            "Copy request to Windows:", f"`{self.docker_copy_to_windows}`", "",
            "Run manually on Windows; review metadata and keep the existing EXECUTE confirmation:",
            f"`{self.runner_invocation}`", "",
            "Copy response back to the same Container exchange:",
            f"`{self.docker_copy_to_container}`", "",
            "A copied response is untrusted until P5 collection validates it.",
        ))


class P5TokenCountOrchestrator:
    """Prepare one exact count request and retain its original identity/state.

    One unresolved workflow blocks all later Case preparations. Workflow state
    is stored in a dedicated SQLite file beside the exchange, separate from the
    paid campaign Ledger and from files copied to the Windows host.
    """

    _TRANSITIONS = {
        TokenCountWorkflowState.PREPARED: {
            TokenCountWorkflowState.AWAITING_HOST_EXECUTION,
            TokenCountWorkflowState.FAILED,
            TokenCountWorkflowState.UNKNOWN,
        },
        TokenCountWorkflowState.AWAITING_HOST_EXECUTION: {
            TokenCountWorkflowState.RESPONSE_PENDING,
            TokenCountWorkflowState.FAILED,
            TokenCountWorkflowState.UNKNOWN,
        },
        TokenCountWorkflowState.RESPONSE_PENDING: {
            TokenCountWorkflowState.COLLECTED,
            TokenCountWorkflowState.FAILED,
            TokenCountWorkflowState.UNKNOWN,
            TokenCountWorkflowState.CONFIRMED_FAILED,
        },
    }
    CONTAINER_NAME = "codex-sandbox-lab-005"
    WINDOWS_EXCHANGE_DEFAULT = r"C:\SupplyChainCopilot\api_exchange"
    RUNNER_OPERATION = "input_token_count"
    RECONCILIATION_TABLE = "token_count_reconciliation_events"
    FAILURE_CONFIRMATION_PREFIX = "CONFIRM_FAILED"

    def __init__(self, *, exchange_path: str | Path | None = None,
                 state_path: str | Path | None = None):
        # Resolve configuration through the same bridge factory used by the
        # production prepare/collect entrypoints. A test may inject a temp root.
        if exchange_path is None:
            from src.ai_copilot.windows_runner_exchange import configured_windows_token_count_exchange
            self.exchange_path = configured_windows_token_count_exchange().exchange_path
        else:
            self.exchange_path = Path(exchange_path).resolve()
        self.state_path = (Path(state_path).resolve() if state_path is not None
                           else self.exchange_path / ".p5_token_count_workflow.sqlite3")

    def _connect(self) -> sqlite3.Connection:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.state_path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("""CREATE TABLE IF NOT EXISTS token_count_workflow (
            case_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            request_id TEXT NOT NULL UNIQUE,
            run_id TEXT NOT NULL,
            run_manifest_sha256 TEXT NOT NULL,
            brief_digest TEXT NOT NULL,
            provider_request_digest TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            count_projection_sha256 TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )""")
        return db

    def state_for_case(self, case_id: str) -> TokenCountWorkflowState:
        if not isinstance(case_id, str) or case_id not in CASE_IDS:
            raise TokenCountWorkflowBlocked("Unknown P5 Evaluation Case")
        with closing(self._connect()) as db:
            row = db.execute("SELECT state FROM token_count_workflow WHERE case_id=?",
                             (case_id,)).fetchone()
        return (TokenCountWorkflowState(row["state"]) if row is not None
                else TokenCountWorkflowState.NOT_PREPARED)

    def record_for_case(self, case_id: str) -> TokenCountWorkflowRecord | None:
        if not isinstance(case_id, str) or case_id not in CASE_IDS:
            raise TokenCountWorkflowBlocked("Unknown P5 Evaluation Case")
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM token_count_workflow WHERE case_id=?",
                             (case_id,)).fetchone()
        return TokenCountWorkflowRecord.from_row(row) if row is not None else None

    def record_for_request(self, request_id: str) -> TokenCountWorkflowRecord | None:
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                             (request_id,)).fetchone()
        return TokenCountWorkflowRecord.from_row(row) if row is not None else None

    def records(self) -> tuple[TokenCountWorkflowRecord, ...]:
        """Return persisted workflow metadata for an operator status display."""
        if not self.state_path.exists():
            return ()
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT * FROM token_count_workflow ORDER BY rowid").fetchall()
        return tuple(TokenCountWorkflowRecord.from_row(row) for row in rows)

    @staticmethod
    def _read_regular_file(path: Path, max_bytes: int) -> bytes:
        """Read a bounded regular file without following a final symlink."""
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = None
        try:
            fd = os.open(path, flags)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > max_bytes:
                raise TokenCountWorkflowBlocked("Reconciliation evidence file is unsafe or oversized")
            chunks = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > max_bytes:
                raise TokenCountWorkflowBlocked("Reconciliation evidence file is oversized")
            return raw
        except TokenCountWorkflowBlocked:
            raise
        except OSError as exc:
            raise TokenCountWorkflowBlocked("Reconciliation evidence file is unavailable") from exc
        finally:
            if fd is not None:
                os.close(fd)

    @staticmethod
    def _decode_unique_json(raw: bytes, label: str) -> dict:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        try:
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise TokenCountWorkflowBlocked(f"{label} is not strict UTF-8 JSON") from exc
        if type(value) is not dict:
            raise TokenCountWorkflowBlocked(f"{label} must be a JSON object")
        return value

    def _validated_failure_evidence(self, record: sqlite3.Row,
                                    expected_request_sha256: str,
                                    expected_response_sha256: str) -> dict:
        """Validate the original 400 evidence against the persisted workflow row."""
        if (not re.fullmatch(r"[0-9a-f]{64}", expected_request_sha256 or "")
                or not re.fullmatch(r"[0-9a-f]{64}", expected_response_sha256 or "")):
            raise TokenCountWorkflowBlocked("Expected evidence SHA-256 values are required")
        request_path = self.exchange_path / "requests" / f"{record['request_id']}.json"
        response_path = self.exchange_path / "responses" / f"{record['request_id']}.json"
        request_raw = self._read_regular_file(request_path, MAX_PACKAGE_BYTES)
        response_raw = self._read_regular_file(response_path, MAX_PACKAGE_BYTES)
        request_sha256 = hashlib.sha256(request_raw).hexdigest()
        response_sha256 = hashlib.sha256(response_raw).hexdigest()
        if (not hmac.compare_digest(request_sha256, expected_request_sha256)
                or not hmac.compare_digest(response_sha256, expected_response_sha256)):
            raise TokenCountWorkflowBlocked("Original Request or Response SHA-256 mismatch")

        try:
            validated = validate_request_package(request_raw)
        except RunnerError as exc:
            raise TokenCountWorkflowBlocked("Original Request package failed Runner validation") from exc
        request = validated.package
        identity_fields = {
            "request_id": record["request_id"], "case_id": record["case_id"],
            "run_id": record["run_id"], "operation": OPERATION, "model": ALLOWED_MODEL,
            "payload_digest": record["payload_sha256"],
            "count_projection_digest": record["count_projection_sha256"],
            "brief_digest": record["brief_digest"],
            "provider_request_digest": record["provider_request_digest"],
            "run_manifest_sha256": record["run_manifest_sha256"],
        }
        if any(request.get(key) != value for key, value in identity_fields.items()):
            raise TokenCountWorkflowBlocked("Original Request identity differs from workflow row")
        payload = request.get("payload")
        if type(payload) is not dict:
            raise TokenCountWorkflowBlocked("Original Request payload is invalid")
        try:
            projection = {field: payload[field] for field in COUNT_FIELDS}
            projection_sha256 = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        except (KeyError, RunnerError) as exc:
            raise TokenCountWorkflowBlocked("Request count projection cannot be verified") from exc
        if projection_sha256 != record["count_projection_sha256"]:
            raise TokenCountWorkflowBlocked("Original Request count projection digest mismatch")

        response = self._decode_unique_json(response_raw, "Original Response package")
        response_fields = {
            "request_id", "case_id", "run_id", "payload_digest", "operation", "http_status",
            "openai_request_id", "model", "returned_model_id", "usage", "response_body",
            "executed_at", "runner_execution_status", "brief_digest", "provider_request_digest",
            "count_projection_digest", "run_manifest_sha256",
        }
        if set(response) != response_fields or any(
                response.get(key) != value for key, value in identity_fields.items()):
            raise TokenCountWorkflowBlocked("Original Response identity or schema mismatch")
        body = response.get("response_body")
        error = body.get("error") if type(body) is dict else None
        if (type(body) is not dict or set(body) != {"error"} or type(error) is not dict
                or error.get("type") != "invalid_request_error"
                or error.get("code") != "unknown_parameter"
                or error.get("param") != "background"
                or error.get("message") != "Unknown parameter: 'background'."
                or "input_tokens" in body):
            raise TokenCountWorkflowBlocked("Response does not prove the expected non-retryable HTTP 400")
        if (response.get("http_status") != 400
                or response.get("runner_execution_status") != "FAILED_AFTER_DISPATCH"
                or response.get("model") != ALLOWED_MODEL
                or response.get("returned_model_id") is not None
                or response.get("usage") is not None
                or type(response.get("openai_request_id")) is not str
                or not re.fullmatch(r"req_[A-Za-z0-9]+", response["openai_request_id"])
                or type(response.get("executed_at")) is not str
                or not response["executed_at"]):
            raise TokenCountWorkflowBlocked("HTTP status or Runner failure evidence is invalid")
        return {
            "request_package_sha256": request_sha256,
            "response_package_sha256": response_sha256,
            "payload_sha256": record["payload_sha256"],
            "count_projection_sha256": record["count_projection_sha256"],
            "http_status": response["http_status"],
            "openai_request_id": response["openai_request_id"],
            "runner_execution_status": response["runner_execution_status"],
            "error_type": error["type"], "error_code": error["code"],
            "error_param": error["param"],
        }

    @staticmethod
    def _ensure_reconciliation_schema(db: sqlite3.Connection) -> None:
        """Create the event extension only as part of an explicit reconciliation."""
        db.execute(f"""CREATE TABLE IF NOT EXISTS {P5TokenCountOrchestrator.RECONCILIATION_TABLE} (
            request_id TEXT NOT NULL UNIQUE,
            event_sha256 TEXT NOT NULL PRIMARY KEY,
            event_json BLOB NOT NULL,
            created_at_utc TEXT NOT NULL
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS token_count_reconciliation_no_update
            BEFORE UPDATE ON {P5TokenCountOrchestrator.RECONCILIATION_TABLE}
            BEGIN SELECT RAISE(ABORT,'append-only token-count reconciliation'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS token_count_reconciliation_no_delete
            BEFORE DELETE ON {P5TokenCountOrchestrator.RECONCILIATION_TABLE}
            BEGIN SELECT RAISE(ABORT,'append-only token-count reconciliation'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS token_count_reconciliation_no_replace
            BEFORE INSERT ON {P5TokenCountOrchestrator.RECONCILIATION_TABLE}
            WHEN EXISTS (SELECT 1 FROM {P5TokenCountOrchestrator.RECONCILIATION_TABLE}
                         WHERE request_id=NEW.request_id OR event_sha256=NEW.event_sha256)
            BEGIN SELECT RAISE(ABORT,'duplicate append-only token-count reconciliation'); END""")

    def _valid_reconciliation_event(self, db: sqlite3.Connection,
                                   record: sqlite3.Row) -> bool:
        if record["state"] != TokenCountWorkflowState.CONFIRMED_FAILED.value:
            return False
        try:
            event_row = db.execute(
                f"SELECT event_sha256,event_json FROM {self.RECONCILIATION_TABLE} WHERE request_id=?",
                (record["request_id"],)).fetchone()
        except sqlite3.OperationalError:
            return False
        if event_row is None:
            return False
        raw_event = bytes(event_row["event_json"])
        if not hmac.compare_digest(hashlib.sha256(raw_event).hexdigest(), event_row["event_sha256"]):
            return False
        try:
            event = self._decode_unique_json(raw_event, "Reconciliation audit event")
            authenticated_actor = (isinstance(event.get("actor"), str)
                                   and event["actor"].startswith("OWNER_VERIFIER_SHA256:")
                                   and re.fullmatch(r"[0-9a-f]{64}", event["actor"][len("OWNER_VERIFIER_SHA256:"):])
                                   and re.fullmatch(r"[0-9a-f]{48}", event.get("authorization_ref", ""))
                                   and event.get("authorization_purpose") == "TOKEN_COUNT_CONFIRMED_FAILURE"
                                   and type(event.get("authorization_issued_at")) is int
                                   and type(event.get("authorization_expires_at")) is int
                                   and event["authorization_issued_at"] < event["authorization_expires_at"])
            # Historical unauthenticated events remain in the archive, but
            # cannot release a gate that now requires authenticated ownership.
            if (event.get("event_type") != "TOKEN_COUNT_FAILURE_CLOSED"
                    or event.get("resolution") != TokenCountWorkflowState.CONFIRMED_FAILED.value
                    or event.get("request_id") != record["request_id"]
                    or event.get("case_id") != record["case_id"]
                    or event.get("run_id") != record["run_id"]
                    or event.get("payload_sha256") != record["payload_sha256"]
                    or event.get("count_projection_sha256") != record["count_projection_sha256"]
                    or not authenticated_actor
                    or event.get("owner_confirmation") !=
                       f"CONFIRM_FAILED {record['request_id']}"
                    or not event.get("reason")):
                return False
            evidence = self._validated_failure_evidence(
                record, event["request_package_sha256"], event["response_package_sha256"])
            return all(event.get(key) == value for key, value in evidence.items())
        except (KeyError, TypeError, TokenCountWorkflowBlocked, OSError):
            return False

    def workflow_resolved(self, request_id: str) -> bool:
        """Return whether this request is collected or has a valid close-out event."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                             (request_id,)).fetchone()
            if row is None:
                raise TokenCountWorkflowBlocked("Unknown count request UUID")
            return (row["state"] == TokenCountWorkflowState.COLLECTED.value
                    or self._valid_reconciliation_event(db, row))

    def inspect_reconciliation(self, request_id: str) -> dict:
        """Read and summarize failure evidence without changing workflow state."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                             (request_id,)).fetchone()
        if row is None:
            raise TokenCountWorkflowBlocked("Unknown count request UUID")
        evidence = self._validated_failure_evidence(
            row,
            hashlib.sha256(self._read_regular_file(
                self.exchange_path / "requests" / f"{request_id}.json", MAX_PACKAGE_BYTES)).hexdigest(),
            hashlib.sha256(self._read_regular_file(
                self.exchange_path / "responses" / f"{request_id}.json", MAX_PACKAGE_BYTES)).hexdigest(),
        )
        return {"request_id": request_id, "case_id": row["case_id"],
                "run_id": row["run_id"], "state": row["state"], **evidence}

    @staticmethod
    def _owner_identity_ref(verifier: OwnerVerifier) -> str:
        material = bytes.fromhex(verifier.salt_hex) + bytes.fromhex(verifier.digest_hex)
        return "OWNER_VERIFIER_SHA256:" + hashlib.sha256(material).hexdigest()

    @staticmethod
    def _configured_owner_verifier() -> OwnerVerifier:
        """Require the same Owner identity pinned by the existing ApprovalStore."""
        store_path = os.environ.get("COPILOT_LEDGER_PATH")
        if not store_path:
            raise TokenCountWorkflowBlocked("Configured Owner approval store is unavailable")
        try:
            verifier = OwnerVerifier.from_environment()
            store = ApprovalStore(store_path)
        except ApprovalBlocked as exc:
            raise TokenCountWorkflowBlocked("Configured Owner identity is unavailable") from exc
        if verifier != store._verifier:
            raise TokenCountWorkflowBlocked("Owner identity differs from provisioned approval store")
        return verifier

    def authorize_confirmed_failure(self, request_id: str, *,
                                    expected_request_sha256: str,
                                    expected_response_sha256: str,
                                    reason: str, owner_password: str,
                                    ttl_seconds: int = 300) -> ReconciliationAuthorization:
        """Authenticate the existing Owner identity without using a paid approval."""
        if (type(reason) is not str or not 12 <= len(reason.strip()) <= 1000
                or any(ord(char) < 32 for char in reason)
                or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 900):
            raise TokenCountWorkflowBlocked("A bounded reason and authorization lifetime are required")
        verifier = self._configured_owner_verifier()
        if not verifier.authenticate(owner_password):
            raise TokenCountWorkflowBlocked("Owner authentication failed")
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                             (request_id,)).fetchone()
        if row is None or row["state"] != TokenCountWorkflowState.UNKNOWN.value:
            raise TokenCountWorkflowBlocked("Only the original UNKNOWN request can be authorized")
        self._validated_failure_evidence(row, expected_request_sha256,
                                         expected_response_sha256)
        now = int(time.time())
        return ReconciliationAuthorization(
            secrets.token_hex(24), self._owner_identity_ref(verifier),
            "TOKEN_COUNT_CONFIRMED_FAILURE", request_id, row["case_id"], row["run_id"],
            expected_request_sha256, expected_response_sha256,
            TokenCountWorkflowState.CONFIRMED_FAILED.value, reason.strip(),
            now, now + ttl_seconds)

    def reconcile_confirmed_failure(self, request_id: str, *,
                                    expected_request_sha256: str,
                                    expected_response_sha256: str,
                                    reason: str,
                                    confirmation: str,
                                    authorization: ReconciliationAuthorization | None = None,
                                    owner_password: str | None = None) -> TokenCountWorkflowRecord:
        """Operator-confirmed, evidence-bound close-out; never dispatches or retries."""
        reason = reason.strip() if isinstance(reason, str) else ""
        if (len(reason) < 12 or len(reason) > 1000
                or any(ord(char) < 32 for char in reason)):
            raise TokenCountWorkflowBlocked("A 12–1000 character reconciliation reason is required")
        if confirmation != f"{self.FAILURE_CONFIRMATION_PREFIX} {request_id}":
            raise TokenCountWorkflowBlocked("Explicit UUID confirmation did not match")
        verifier = self._configured_owner_verifier()
        now_seconds = int(time.time())
        if (type(authorization) is not ReconciliationAuthorization
                or not verifier.authenticate(owner_password)
                or authorization.owner_identity_ref != self._owner_identity_ref(verifier)
                or authorization.purpose != "TOKEN_COUNT_CONFIRMED_FAILURE"
                or authorization.request_id != request_id
                or authorization.request_sha256 != expected_request_sha256
                or authorization.response_sha256 != expected_response_sha256
                or authorization.disposition != TokenCountWorkflowState.CONFIRMED_FAILED.value
                or authorization.reason != reason
                or not authorization.issued_at <= now_seconds < authorization.expires_at
                or not re.fullmatch(r"[0-9a-f]{48}", authorization.reference)):
            raise TokenCountWorkflowBlocked("Owner reconciliation authorization missing, expired or mismatched")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                record = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                                    (request_id,)).fetchone()
                if record is None or record["state"] not in {
                        TokenCountWorkflowState.UNKNOWN.value,
                        TokenCountWorkflowState.CONFIRMED_FAILED.value}:
                    raise TokenCountWorkflowBlocked(
                        "Only an UNKNOWN or evidence-confirmed failed request can be closed")
                if (authorization.case_id != record["case_id"]
                        or authorization.run_id != record["run_id"]):
                    raise TokenCountWorkflowBlocked("Owner authorization Case or Run mismatch")
                evidence = self._validated_failure_evidence(
                    record, expected_request_sha256, expected_response_sha256)
                self._ensure_reconciliation_schema(db)
                for existing in db.execute(f"SELECT event_json FROM {self.RECONCILIATION_TABLE}"):
                    prior = self._decode_unique_json(bytes(existing[0]), "Prior reconciliation event")
                    if prior.get("authorization_ref") == authorization.reference:
                        raise TokenCountWorkflowBlocked("Owner authorization has already been used")
                if db.execute(f"SELECT 1 FROM {self.RECONCILIATION_TABLE} WHERE request_id=?",
                              (request_id,)).fetchone():
                    raise TokenCountWorkflowBlocked("This request already has a reconciliation event")
                now = datetime.now(timezone.utc).isoformat()
                event = {
                    "event_type": "TOKEN_COUNT_FAILURE_CLOSED",
                    "resolution": TokenCountWorkflowState.CONFIRMED_FAILED.value,
                    "request_id": request_id, "case_id": record["case_id"],
                    "run_id": record["run_id"],
                    "run_manifest_sha256": record["run_manifest_sha256"],
                    "brief_digest": record["brief_digest"],
                    "provider_request_digest": record["provider_request_digest"],
                    "payload_sha256": record["payload_sha256"],
                    "count_projection_sha256": record["count_projection_sha256"],
                    **evidence,
                    "actor": authorization.owner_identity_ref,
                    "authorization_ref": authorization.reference,
                    "authorization_purpose": authorization.purpose,
                    "authorization_issued_at": authorization.issued_at,
                    "authorization_expires_at": authorization.expires_at,
                    "owner_confirmation": confirmation,
                    "reason": reason,
                    "reconciled_at_utc": now,
                }
                event_raw = canonical_json_bytes(event)
                event_sha256 = hashlib.sha256(event_raw).hexdigest()
                db.execute(f"INSERT INTO {self.RECONCILIATION_TABLE} VALUES (?,?,?,?)",
                           (request_id, event_sha256, event_raw, now))
                db.execute("UPDATE token_count_workflow SET state=?,updated_at_utc=? WHERE request_id=?",
                           (TokenCountWorkflowState.CONFIRMED_FAILED.value, now, request_id))
                db.commit()
            except TokenCountWorkflowBlocked:
                db.rollback()
                raise
            except sqlite3.Error as exc:
                db.rollback()
                raise TokenCountWorkflowBlocked("Reconciliation audit transaction failed") from exc
        return self.record_for_request(request_id)

    def assert_new_workflow_allowed(self, case_id: str) -> None:
        """Fail before trusted Run creation when prior work needs reconciliation."""
        if not isinstance(case_id, str) or case_id not in CASE_IDS:
            raise TokenCountWorkflowBlocked("Unknown P5 Evaluation Case")
        self._assert_legacy_namespace_gate()
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute(
                    "SELECT * FROM token_count_workflow ORDER BY rowid").fetchall()
                if any(not self._workflow_is_resolved(db, row) for row in existing):
                    raise TokenCountWorkflowBlocked(
                        "An earlier count request is unresolved; inspect status and reconcile its original UUID")
                if any(row["case_id"] == case_id for row in existing):
                    raise TokenCountWorkflowBlocked(
                        "This Case already has a count workflow; replacement UUIDs are forbidden")
                tracked_ids = {row[0] for row in db.execute(
                    "SELECT request_id FROM token_count_workflow").fetchall()}
                self._reject_untracked_request_files(tracked_ids)
                db.commit()
            except Exception:
                db.rollback()
                raise

    def prepare(self, case_id: str, review: ValidatedBrief,
                request: ProviderRequest) -> PreparedCountRequest:
        """Create exactly one package for an already validated trusted context."""
        if not isinstance(case_id, str) or case_id not in CASE_IDS:
            raise TokenCountWorkflowBlocked("Unknown P5 Evaluation Case")
        if type(review) is not ValidatedBrief or type(request) is not ProviderRequest:
            raise TokenCountWorkflowBlocked("Validated Brief and ProviderRequest are required")
        self._assert_legacy_namespace_gate()
        if configured_windows_token_count_exchange().exchange_path != self.exchange_path:
            raise TokenCountWorkflowBlocked(
                "Orchestrator state root differs from the configured request exchange")

        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute(
                    "SELECT * FROM token_count_workflow ORDER BY rowid").fetchall()
                if any(not self._workflow_is_resolved(db, row) for row in existing):
                    raise TokenCountWorkflowBlocked(
                        "An earlier count request is unresolved; no new Case may be prepared")
                if any(row["case_id"] == case_id for row in existing):
                    raise TokenCountWorkflowBlocked(
                        "This Case already has a count workflow; replacement UUIDs are forbidden")
                tracked_ids = {row[0] for row in db.execute(
                    "SELECT request_id FROM token_count_workflow").fetchall()}
                self._reject_untracked_request_files(tracked_ids)

                # Keep the DB write lock while the bridge atomically creates the
                # JSON package. Competing orchestrators cannot create a second ID.
                prepared = prepare_configured_count_request(case_id, review, request)
                from src.ai_copilot.evaluation_namespace import NAMESPACE_ID
                if (self.exchange_path.parent.name == "evaluations"
                        and self.exchange_path.name == NAMESPACE_ID):
                    from src.ai_copilot.evaluation_namespace import EvaluationNamespace, NamespaceBlocked
                    namespace = EvaluationNamespace.mapping(
                        legacy_exchange=self.exchange_path.parent.parent)
                    try:
                        namespace.assert_request_id_unshared(prepared.request_id)
                    except NamespaceBlocked as exc:
                        raise TokenCountWorkflowBlocked(
                            "Prepared UUID collides with another workflow namespace") from exc
                now = datetime.now(timezone.utc).isoformat()
                db.execute("""INSERT INTO token_count_workflow VALUES
                    (?,?,?,?,?,?,?,?,?,?,?)""",
                    (case_id, TokenCountWorkflowState.PREPARED.value,
                     prepared.request_id, prepared.run_id, prepared.run_manifest_sha256,
                     prepared.brief_digest, prepared.provider_request_digest,
                     prepared.payload_digest, prepared.count_projection_digest, now, now))
                db.commit()
                return prepared
            except Exception:
                db.rollback()
                raise

    def _assert_legacy_namespace_gate(self) -> None:
        """A versioned count state cannot bypass unresolved historical attempts."""
        from src.ai_copilot.evaluation_namespace import EvaluationNamespace, NAMESPACE_ID, NamespaceBlocked
        if (self.exchange_path.parent.name == "evaluations"
                and self.exchange_path.name == NAMESPACE_ID):
            namespace = EvaluationNamespace.mapping(legacy_exchange=self.exchange_path.parent.parent)
            try:
                namespace.assert_legacy_resolved()
            except NamespaceBlocked as exc:
                raise TokenCountWorkflowBlocked("Historical count workflow remains unresolved or unverifiable") from exc

    def mark_awaiting_host_execution(self, request_id: str) -> TokenCountWorkflowRecord:
        return self._transition(request_id, TokenCountWorkflowState.AWAITING_HOST_EXECUTION)

    def create_windows_handoff(self, request_id: str, *,
                               windows_exchange_path: str = WINDOWS_EXCHANGE_DEFAULT
                               ) -> WindowsRunnerHandoff:
        """Validate the exact prepared file and return manual docker-cp commands."""
        try:
            uuid.UUID(request_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise TokenCountWorkflowBlocked("Request UUID is malformed") from exc
        record = self.record_for_request(request_id)
        if record is None or record.state not in {
                TokenCountWorkflowState.PREPARED,
                TokenCountWorkflowState.AWAITING_HOST_EXECUTION}:
            raise TokenCountWorkflowBlocked("Request is not available for host handoff")
        if not isinstance(windows_exchange_path, str) or any(
                ord(char) < 32 for char in windows_exchange_path):
            raise TokenCountWorkflowBlocked("Windows exchange path is invalid")
        windows_root = PureWindowsPath(windows_exchange_path)
        if not windows_root.is_absolute() or not windows_root.drive:
            raise TokenCountWorkflowBlocked("Windows exchange path must be absolute")

        request_path = self.exchange_path / "requests" / f"{request_id}.json"
        try:
            info = request_path.lstat()
            if (request_path.is_symlink() or not request_path.is_file()
                    or info.st_size > MAX_PACKAGE_BYTES):
                raise TokenCountWorkflowBlocked("Prepared request file is not a bounded regular file")
            package = validate_request_package(request_path.read_bytes()).package
        except TokenCountWorkflowBlocked:
            raise
        except Exception as exc:
            raise TokenCountWorkflowBlocked("Prepared request file is unavailable or invalid") from exc
        expected = {
            "request_id": record.request_id, "case_id": record.case_id,
            "run_id": record.run_id, "operation": self.RUNNER_OPERATION,
            "model": "gpt-6-luna", "payload_digest": record.payload_sha256,
            "brief_digest": record.brief_digest,
            "provider_request_digest": record.provider_request_digest,
            "count_projection_digest": record.count_projection_sha256,
            "run_manifest_sha256": record.run_manifest_sha256,
        }
        if any(package.get(key) != value for key, value in expected.items()):
            raise TokenCountWorkflowBlocked("Prepared package does not match workflow identity")

        container_root = str(self.exchange_path)
        request_container = f"{container_root}/requests/{request_id}.json"
        response_container = f"{container_root}/responses/{request_id}.json"
        request_windows = str(windows_root / "requests" / f"{request_id}.json")
        response_windows = str(windows_root / "responses" / f"{request_id}.json")
        windows_setup = (
            "New-Item -ItemType Directory -Force "
            f"{self._ps_literal(str(windows_root / 'requests'))}; "
            "New-Item -ItemType Directory -Force "
            f"{self._ps_literal(str(windows_root / 'responses'))}")
        docker_to_windows = (
            f"docker cp {self._ps_literal(f'{self.CONTAINER_NAME}:{request_container}')} "
            f"{self._ps_literal(request_windows)}")
        runner_command = (
            "py -3 -m tools.windows_api_runner.api_runner "
            f"{self._ps_literal(request_windows)} --exchange "
            f"{self._ps_literal(str(windows_root))}")
        docker_to_container = (
            f"docker cp {self._ps_literal(response_windows)} "
            f"{self._ps_literal(f'{self.CONTAINER_NAME}:{container_root}/responses/')}")
        handoff = WindowsRunnerHandoff(
            case_id=record.case_id, run_id=record.run_id, request_id=record.request_id,
            operation=self.RUNNER_OPERATION, model="gpt-6-luna",
            payload_sha256=record.payload_sha256,
            count_projection_sha256=record.count_projection_sha256,
            brief_digest=record.brief_digest,
            provider_request_digest=record.provider_request_digest,
            run_manifest_sha256=record.run_manifest_sha256,
            container_exchange_path=container_root,
            windows_exchange_path=str(windows_root),
            request_container_path=request_container,
            response_container_path=response_container,
            request_windows_path=request_windows, response_windows_path=response_windows,
            windows_directory_setup=windows_setup,
            docker_copy_to_windows=docker_to_windows,
            runner_invocation=runner_command,
            docker_copy_to_container=docker_to_container,
        )
        if record.state == TokenCountWorkflowState.PREPARED:
            self._transition(request_id, TokenCountWorkflowState.AWAITING_HOST_EXECUTION)
        return handoff

    def mark_response_pending(self, request_id: str) -> TokenCountWorkflowRecord:
        """Mark only that a candidate file exists; it remains untrusted/uncollected."""
        record = self.record_for_request(request_id)
        if record is None or record.state != TokenCountWorkflowState.AWAITING_HOST_EXECUTION:
            raise TokenCountWorkflowBlocked("Request is not awaiting a host response")
        response_path = self.exchange_path / "responses" / f"{request_id}.json"
        try:
            info = response_path.lstat()
        except OSError as exc:
            raise TokenCountWorkflowBlocked("Expected response file is not present") from exc
        if (response_path.is_symlink() or not response_path.is_file()
                or info.st_size > MAX_PACKAGE_BYTES):
            raise TokenCountWorkflowBlocked("Expected response path is not a bounded regular file")
        return self._transition(request_id, TokenCountWorkflowState.RESPONSE_PENDING)

    def collect_response(self, request_id: str, case_id: str,
                         review: ValidatedBrief, request: ProviderRequest):
        """Collect and gate the response for the same persisted workflow identity.

        A missing response leaves the workflow pending. Invalid or mismatched
        response material fails the workflow closed. No request is recreated.
        """
        record = self.record_for_request(request_id)
        if (record is None or record.state != TokenCountWorkflowState.RESPONSE_PENDING
                or case_id != record.case_id):
            raise TokenCountWorkflowBlocked(
                "Only the original response-pending Case may be collected")
        if type(review) is not ValidatedBrief or type(request) is not ProviderRequest:
            raise TokenCountWorkflowBlocked(
                "The original validated Brief and ProviderRequest are required for collection")
        if (review.content_digest != record.brief_digest
                or request.brief_digest != record.brief_digest
                or request.request_digest != record.provider_request_digest):
            self._transition(request_id, TokenCountWorkflowState.FAILED)
            raise TokenCountWorkflowBlocked(
                "Current Brief or ProviderRequest differs from the prepared workflow")
        if configured_windows_token_count_exchange().exchange_path != self.exchange_path:
            raise TokenCountWorkflowBlocked(
                "Orchestrator state root differs from the configured response exchange")

        try:
            evidence = collect_configured_count_response(
                request_id, case_id, review, request)
            expected = (
                evidence.run_id == record.run_id
                and evidence.run_manifest_sha256 == record.run_manifest_sha256
                and evidence.brief_digest == record.brief_digest
                and evidence.provider_request_digest == record.provider_request_digest
                and evidence.full_payload_sha256 == record.payload_sha256
                and evidence.count_projection_sha256 == record.count_projection_sha256
                and evidence.runner_request_id == record.request_id
            )
            if not expected:
                raise RunnerExchangeBlocked(
                    "Collected evidence differs from persisted workflow identity")
            require_exact_token_count(case_id, request, evidence=evidence, review=review)
        except RunnerResponsePending:
            # Waiting is safe: the original UUID remains active and blocks all
            # later Case preparations. This path never creates another package.
            raise
        except Exception as exc:
            target = self._failed_or_unknown_response_state(request_id)
            try:
                self._transition(request_id, target)
            except TokenCountWorkflowBlocked:
                pass
            if isinstance(exc, TokenCountWorkflowBlocked):
                raise
            from src.ai_copilot.eight_call_campaign import CampaignBlocked
            if isinstance(exc, RunnerResponseIdentityMismatch):
                category = "identity mismatch"
            elif isinstance(exc, RunnerResponseDigestMismatch):
                category = "digest mismatch"
            elif isinstance(exc, RunnerHTTPStatusError):
                category = str(exc)
            elif isinstance(exc, RunnerExecutionFailure):
                category = "Runner execution failure or UNKNOWN outcome"
            elif isinstance(exc, RunnerMissingInputTokens):
                category = "missing or invalid input_tokens"
            elif isinstance(exc, CampaignBlocked):
                category = "Evidence Gate rejection"
            elif isinstance(exc, RunnerExchangeBlocked):
                category = str(exc)
            else:
                category = "response validation failure"
            raise TokenCountWorkflowBlocked(
                f"P5 Collect blocked: {category}") from exc

        return self._transition(request_id, TokenCountWorkflowState.COLLECTED), evidence

    def _failed_or_unknown_response_state(self, request_id: str) -> TokenCountWorkflowState:
        """Distinguish a verified explicit HTTP 400 from uncertain dispatch outcomes."""
        response_path = self.exchange_path / "responses" / f"{request_id}.json"
        try:
            info = response_path.lstat()
            if response_path.is_symlink() or not response_path.is_file() \
                    or info.st_size > MAX_PACKAGE_BYTES:
                return TokenCountWorkflowState.FAILED
            import json
            package = json.loads(response_path.read_text(encoding="utf-8"))
            if type(package) is dict and package.get("runner_execution_status") in {
                    "UNKNOWN", "IN_PROGRESS"}:
                return TokenCountWorkflowState.UNKNOWN
            if (type(package) is dict
                    and package.get("runner_execution_status") == "FAILED_AFTER_DISPATCH"):
                if (package.get("http_status") == 400
                        and self._response_proves_confirmed_failure(request_id)):
                    return TokenCountWorkflowState.CONFIRMED_FAILED
                return TokenCountWorkflowState.FAILED
            if (type(package) is dict
                    and package.get("runner_execution_status") == "FAILED_BEFORE_DISPATCH"):
                return TokenCountWorkflowState.FAILED
        except Exception:
            pass
        return TokenCountWorkflowState.FAILED

    def _response_proves_confirmed_failure(self, request_id: str) -> bool:
        with closing(self._connect()) as db:
            record = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                                (request_id,)).fetchone()
            if record is None:
                return False
        try:
            request_raw = self._read_regular_file(
                self.exchange_path / "requests" / f"{request_id}.json", MAX_PACKAGE_BYTES)
            response_raw = self._read_regular_file(
                self.exchange_path / "responses" / f"{request_id}.json", MAX_PACKAGE_BYTES)
            return bool(self._validated_failure_evidence(
                record, hashlib.sha256(request_raw).hexdigest(),
                hashlib.sha256(response_raw).hexdigest()))
        except (TokenCountWorkflowBlocked, OSError):
            return False

    def mark_failed(self, request_id: str) -> TokenCountWorkflowRecord:
        return self._transition(request_id, TokenCountWorkflowState.FAILED)

    def mark_unknown(self, request_id: str) -> TokenCountWorkflowRecord:
        return self._transition(request_id, TokenCountWorkflowState.UNKNOWN)

    def _transition(self, request_id: str,
                    target: TokenCountWorkflowState) -> TokenCountWorkflowRecord:
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                                 (request_id,)).fetchone()
                if row is None:
                    raise TokenCountWorkflowBlocked("Unknown count request UUID")
                current = TokenCountWorkflowState(row["state"])
                if target not in self._TRANSITIONS.get(current, set()):
                    raise TokenCountWorkflowBlocked(
                        f"Invalid workflow transition: {current.value} to {target.value}")
                now = datetime.now(timezone.utc).isoformat()
                db.execute("UPDATE token_count_workflow SET state=?,updated_at_utc=? WHERE request_id=?",
                           (target.value, now, request_id))
                db.commit()
                updated = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                                     (request_id,)).fetchone()
                return TokenCountWorkflowRecord.from_row(updated)
            except Exception:
                db.rollback()
                raise

    def _reject_untracked_request_files(self, tracked_ids: set[str]) -> None:
        request_dir = self.exchange_path / "requests"
        if not request_dir.exists():
            return
        for path in request_dir.iterdir():
            if path.is_dir():
                raise TokenCountWorkflowBlocked(
                    "Unrecognized entry in request directory requires reconciliation")
            request_id = path.name[:-5] if path.name.endswith(".json") else None
            if request_id not in tracked_ids:
                raise TokenCountWorkflowBlocked(
                    "Untracked request file exists; reconcile it before preparing another Case")

    def _workflow_is_resolved(self, db: sqlite3.Connection,
                              record: sqlite3.Row) -> bool:
        """Only collection or evidence-validated owner close-out releases the global gate."""
        return (record["state"] == TokenCountWorkflowState.COLLECTED.value
                or self._valid_reconciliation_event(db, record))

    @staticmethod
    def _ps_literal(value: str) -> str:
        """Quote a PowerShell literal; embedded apostrophes are doubled."""
        if any(ord(char) < 32 for char in value):
            raise TokenCountWorkflowBlocked("Control characters are invalid in handoff paths")
        return "'" + value.replace("'", "''") + "'"
