"""Windows host runner for manually approved OpenAI Input Token Count calls.

The runner deliberately supports one fixed operation and endpoint. Its core is
transport- and credential-store-injectable so safety behavior can be tested
offline on non-Windows hosts.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
from datetime import datetime, timezone
import ctypes
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid
from typing import Protocol

API_URL = "https://api.openai.com/v1/responses/input_tokens"
REAL_TOKEN_COUNT_DISPATCH_LOCKED = True
CREDENTIAL_TARGET = "SupplyChainCopilot/OpenAI"
ALLOWED_MODEL = "gpt-6-luna"
OPERATION = "input_token_count"
MAX_PACKAGE_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 1_048_576
MAX_PAYLOAD_BYTES = 786_432
TIMEOUT_SECONDS = 60
REQUEST_FIELDS = frozenset({
    "request_id", "case_id", "run_id", "operation", "model", "payload",
    "payload_digest", "created_at",
})
P5_REQUEST_FIELDS = frozenset({
    "brief_digest", "provider_request_digest", "count_projection_digest",
    "run_manifest_sha256",
})
STATES = frozenset({
    "RECEIVED", "IN_PROGRESS", "SUCCEEDED", "FAILED_BEFORE_DISPATCH",
    "FAILED_AFTER_DISPATCH", "UNKNOWN",
})
SECRET_PATTERN = re.compile(r"(?i)(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+\S+)")


class RunnerError(RuntimeError):
    """Safe-to-display runner failure; messages must never contain secrets."""


class CredentialStore(Protocol):
    def get_api_key(self) -> str: ...


class Transport(Protocol):
    def post(self, body: bytes, api_key: str) -> "HttpResult": ...


@dataclass(frozen=True)
class HttpResult:
    status: int
    request_id: str | None
    body: bytes


@dataclass(frozen=True)
class ValidatedRequest:
    package: dict
    payload_bytes: bytes
    payload_digest: str


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RunnerError("Duplicate JSON fields are not allowed")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    try:
        # Match the P5 payload serializer (json.dumps default ensure_ascii=True).
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RunnerError("Payload is not valid canonical JSON") from exc


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def _contains_credential_field(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower().replace("-", "_") in {
                    "api_key", "openai_api_key", "authorization", "auth_header"}:
                return True
            if _contains_credential_field(item):
                return True
    elif isinstance(value, list):
        return any(_contains_credential_field(item) for item in value)
    return False


def validate_request_package(raw: bytes) -> ValidatedRequest:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_PACKAGE_BYTES:
        raise RunnerError("Request package is empty or exceeds the size limit")
    try:
        package = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, RunnerError):
            raise
        raise RunnerError("Request package is not valid UTF-8 JSON") from exc
    if not isinstance(package, dict) or set(package) not in (REQUEST_FIELDS,
                                                               REQUEST_FIELDS | P5_REQUEST_FIELDS):
        raise RunnerError("Request package fields do not match the strict schema")
    for key in ("request_id", "case_id", "run_id"):
        value = package[key]
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(ord(c) < 32 for c in value):
            raise RunnerError(f"Invalid {key}")
    try:
        uuid.UUID(package["request_id"])
    except (ValueError, AttributeError) as exc:
        raise RunnerError("request_id must be a UUID") from exc
    if package["operation"] != OPERATION:
        raise RunnerError("Unsupported operation")
    if package["model"] != ALLOWED_MODEL:
        raise RunnerError("Unsupported model")
    if P5_REQUEST_FIELDS.issubset(package):
        for key in P5_REQUEST_FIELDS:
            if not isinstance(package[key], str) or not re.fullmatch(r"[0-9a-f]{64}", package[key]):
                raise RunnerError(f"Invalid {key}")
    if not _valid_timestamp(package["created_at"]):
        raise RunnerError("created_at must be an ISO timestamp with timezone")
    if not isinstance(package["payload"], dict):
        raise RunnerError("payload must be a JSON object")
    payload_bytes = canonical_json_bytes(package["payload"])
    if len(payload_bytes) > MAX_PAYLOAD_BYTES:
        raise RunnerError("Payload exceeds the size limit")
    if package["payload"].get("model") != package["model"]:
        raise RunnerError("Payload model does not match request model")
    if (_contains_credential_field(package["payload"])
            or SECRET_PATTERN.search(payload_bytes.decode("utf-8"))):
        raise RunnerError("Credential-like content is forbidden in API payloads")
    digest = hashlib.sha256(payload_bytes).hexdigest()
    claimed = package["payload_digest"]
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise RunnerError("payload_digest must be a lowercase SHA-256 digest")
    if not hmac.compare_digest(digest, claimed):
        raise RunnerError("Payload digest mismatch")
    return ValidatedRequest(package, payload_bytes, digest)


def read_request_file(path: str | Path) -> ValidatedRequest:
    target = Path(path)
    try:
        info = target.lstat()
        if target.is_symlink() or not target.is_file() or info.st_size > MAX_PACKAGE_BYTES:
            raise RunnerError("Request must be a regular, bounded file")
        with target.open("rb") as stream:
            raw = stream.read(MAX_PACKAGE_BYTES + 1)
    except OSError as exc:
        raise RunnerError("Request package could not be read") from exc
    return validate_request_package(raw)


class WindowsCredentialManager:
    """Read one Generic Credential from the current Windows user profile."""

    def get_api_key(self) -> str:
        if os.name != "nt":
            raise RunnerError("Windows Credential Manager is available only on Windows")
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            pass

        PCREDENTIALW = ctypes.POINTER(CREDENTIALW)
        CREDENTIALW._fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]
        advapi = ctypes.WinDLL("Advapi32.dll")
        read = advapi.CredReadW
        read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                         ctypes.POINTER(PCREDENTIALW)]
        read.restype = wintypes.BOOL
        free = advapi.CredFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
        credential = PCREDENTIALW()
        if not read(CREDENTIAL_TARGET, 1, 0, ctypes.byref(credential)):
            raise RunnerError("OpenAI credential is not available in Windows Credential Manager")
        try:
            blob_size = credential.contents.CredentialBlobSize
            if not blob_size or blob_size > 4096:
                raise RunnerError("Stored OpenAI credential is invalid")
            raw = ctypes.string_at(credential.contents.CredentialBlob, blob_size)
            try:
                value = raw.decode("utf-8")
            except UnicodeError as exc:
                raise RunnerError("Stored OpenAI credential encoding is invalid") from exc
            if not value:
                raise RunnerError("Stored OpenAI credential is empty")
            return value
        finally:
            free(credential)


class UrllibTransport:
    """Fixed-destination HTTP transport; no caller-controlled URLs or headers."""

    def post(self, body: bytes, api_key: str) -> HttpResult:
        request = urllib.request.Request(
            API_URL, data=body,
            headers={"Authorization": "Bearer " + api_key,
                     "Content-Type": "application/json"}, method="POST")
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise RunnerError("Response exceeds the size limit")
                return HttpResult(response.status, response.headers.get("x-request-id"), raw)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raw = b""
                return HttpResult(exc.code, exc.headers.get("x-request-id"), raw)
            finally:
                exc.close()
        except RunnerError:
            raise
        except Exception as exc:
            # No exception text: urllib errors can include request metadata.
            raise RunnerError("Transport outcome is uncertain") from None


def _sanitize(value: object, api_key: str) -> object:
    if isinstance(value, str):
        value = value.replace(api_key, "[REDACTED]") if api_key else value
        return SECRET_PATTERN.sub("[REDACTED]", value)[:20000]
    if isinstance(value, list):
        return [_sanitize(item, api_key) for item in value[:1000]]
    if isinstance(value, dict):
        return {str(_sanitize(str(key), api_key))[:200]: _sanitize(item, api_key)
                for key, item in list(value.items())[:1000]}
    if value is None or type(value) in (bool, int, float):
        return value
    return "[UNSUPPORTED_VALUE]"


def _response_body(raw: bytes, api_key: str) -> object:
    try:
        decoded = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates)
    except (UnicodeError, json.JSONDecodeError, RunnerError):
        text = raw.decode("utf-8", errors="replace")
        return {"raw_text": _sanitize(text, api_key)}
    return _sanitize(decoded, api_key)


class ExecutionStateStore:
    """Host-local request state; keep this database outside the Docker exchange."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS executions (
                request_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, run_id TEXT NOT NULL,
                operation TEXT NOT NULL, payload_digest TEXT NOT NULL, state TEXT NOT NULL,
                created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
                http_status INTEGER, response_path TEXT, safe_error TEXT)""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                executions_case_payload_once ON executions(case_id,run_id,operation,payload_digest)""")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def receive(self, request: ValidatedRequest) -> None:
        p = request.package
        now = datetime.now(timezone.utc).isoformat()
        try:
            with closing(self._connect()) as db:
                db.execute("INSERT INTO executions VALUES (?,?,?,?,?,'RECEIVED',?,?,NULL,NULL,NULL)",
                           (p["request_id"], p["case_id"], p["run_id"], p["operation"],
                            request.payload_digest, now, now))
        except sqlite3.IntegrityError as exc:
            raise RunnerError("Request ID was already recorded; automatic redispatch is forbidden") from exc

    def claim_auto_dispatch(self, request: ValidatedRequest, *, utc_date: str,
                            max_requests: int) -> bool:
        """Atomically reserve one daily local-policy slot and the request identity.

        A persisted RECEIVED claim is counted conservatively until recovery proves
        that dispatch never started. This closes the cross-process quota race.
        """
        p = request.package
        now = datetime.now(timezone.utc).isoformat()
        try:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT COUNT(*) FROM executions WHERE substr(created_at_utc,1,10)=? "
                    "AND state IN ('RECEIVED','IN_PROGRESS','SUCCEEDED',"
                    "'FAILED_AFTER_DISPATCH','UNKNOWN')", (utc_date,)).fetchone()
                allowed = int(row[0]) < max_requests
                state = "RECEIVED" if allowed else "FAILED_BEFORE_DISPATCH"
                error = None if allowed else "Daily local API request limit reached"
                db.execute("INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,NULL,NULL,?)",
                           (p["request_id"], p["case_id"], p["run_id"], p["operation"],
                            request.payload_digest, state, now, now, error))
                db.commit()
                return allowed
        except sqlite3.IntegrityError as exc:
            raise RunnerError("Request identity was already recorded; automatic redispatch is forbidden") from exc

    def execution(self, request_id: str) -> tuple | None:
        with closing(self._connect()) as db:
            return db.execute(
                "SELECT request_id,case_id,run_id,operation,payload_digest,state,"
                "created_at_utc,response_path,safe_error FROM executions WHERE request_id=?",
                (request_id,)).fetchone()

    def dispatched_today(self, utc_date: str) -> int:
        """Count durable dispatch claims, including unexamined RECEIVED rows."""
        states = ("RECEIVED", "IN_PROGRESS", "SUCCEEDED", "FAILED_AFTER_DISPATCH", "UNKNOWN")
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT COUNT(*) FROM executions WHERE substr(created_at_utc,1,10)=? "
                "AND state IN (?,?,?,?,?)", (utc_date, *states)).fetchone()
        return int(row[0])

    def transition_existing(self, request_id: str, expected: str, state: str,
                            *, safe_error: str) -> None:
        self.transition(request_id, expected, state, safe_error=safe_error)

    def transition(self, request_id: str, expected: str, state: str, *,
                   http_status: int | None = None, response_path: str | None = None,
                   safe_error: str | None = None) -> None:
        if state not in STATES:
            raise RunnerError("Invalid execution state")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db:
            cursor = db.execute("""UPDATE executions SET state=?, updated_at_utc=?,
                http_status=COALESCE(?,http_status), response_path=COALESCE(?,response_path),
                safe_error=COALESCE(?,safe_error) WHERE request_id=? AND state=?""",
                (state, now, http_status, response_path, safe_error, request_id, expected))
            if cursor.rowcount != 1:
                raise RunnerError("Execution state changed unexpectedly; manual reconciliation required")


class ApiRunner:
    def __init__(self, credential_store: CredentialStore, transport: Transport,
                 state_store: ExecutionStateStore):
        self.credential_store = credential_store
        self.transport = transport
        self.state_store = state_store

    def execute(self, request: ValidatedRequest, response_dir: str | Path,
                *, confirm: bool, already_received: bool = False) -> dict:
        if already_received:
            saved = self.state_store.execution(request.package["request_id"])
            expected = (request.package["case_id"], request.package["run_id"],
                        request.package["operation"], request.payload_digest)
            if (saved is None or saved[5] != "RECEIVED"
                    or tuple(saved[index] for index in (1, 2, 3, 4)) != expected):
                raise RunnerError("Preclaimed request identity or state is invalid")
        else:
            self.state_store.receive(request)
        package = request.package
        if isinstance(self.transport, UrllibTransport) and REAL_TOKEN_COUNT_DISPATCH_LOCKED:
            self.state_store.transition(package["request_id"], "RECEIVED", "FAILED_BEFORE_DISPATCH",
                                        safe_error="Real token count is locked")
            raise RunnerError("Real token count awaits separate Owner authorization")
        if not confirm:
            self.state_store.transition(package["request_id"], "RECEIVED", "FAILED_BEFORE_DISPATCH",
                                        safe_error="Manual confirmation was not provided")
            raise RunnerError("Manual confirmation required; request was not dispatched")
        try:
            api_key = self.credential_store.get_api_key()
            if (not isinstance(api_key, str) or not api_key or not api_key.isascii()
                    or len(api_key) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in api_key)):
                raise RunnerError("Credential Manager returned no credential")
            if api_key.encode("ascii") in canonical_json_bytes(package):
                raise RunnerError("Credential-like content is forbidden in request packages")
        except Exception as exc:
            self.state_store.transition(package["request_id"], "RECEIVED", "FAILED_BEFORE_DISPATCH",
                                        safe_error="Credential unavailable")
            if isinstance(exc, RunnerError):
                raise
            raise RunnerError("Credential unavailable") from None

        self.state_store.transition(package["request_id"], "RECEIVED", "IN_PROGRESS")
        try:
            result = self.transport.post(request.payload_bytes, api_key)
        except Exception:
            self.state_store.transition(package["request_id"], "IN_PROGRESS", "UNKNOWN",
                                        safe_error="Transport outcome uncertain")
            raise RunnerError("Outcome UNKNOWN; do not resubmit this request") from None

        response = {
            "request_id": package["request_id"], "case_id": package["case_id"],
            "run_id": package["run_id"], "payload_digest": request.payload_digest,
            "operation": package["operation"], "http_status": result.status,
            "openai_request_id": _sanitize(result.request_id, api_key) if result.request_id else None,
            "model": package["model"], "returned_model_id": None,
            "usage": None, "response_body": _response_body(result.body, api_key),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        for field in P5_REQUEST_FIELDS:
            if field in package:
                response[field] = package[field]
        final_state = "SUCCEEDED" if 200 <= result.status < 300 else "FAILED_AFTER_DISPATCH"
        response["runner_execution_status"] = final_state
        body = response["response_body"]
        if isinstance(body, dict):
            response["returned_model_id"] = _sanitize(body.get("model"), api_key) if body.get("model") else None
            response["usage"] = _sanitize(body.get("usage"), api_key) if body.get("usage") is not None else None
        response_dir = Path(response_dir)
        response_path = response_dir / f"{package['request_id']}.json"
        temp_path = response_path.with_suffix(".json.tmp")
        try:
            response_dir.mkdir(parents=True, exist_ok=True)
            if response_path.exists() or response_path.is_symlink():
                raise RunnerError("Response package already exists")
            encoded = canonical_json_bytes(response) + b"\n"
            with temp_path.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temp_path, response_path)
            temp_path.unlink()
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            self.state_store.transition(package["request_id"], "IN_PROGRESS", "UNKNOWN",
                                        http_status=result.status,
                                        safe_error="Response package persistence failed after dispatch")
            raise RunnerError("Response persistence failed after dispatch; do not resubmit") from None

        self.state_store.transition(package["request_id"], "IN_PROGRESS", final_state,
                                    http_status=result.status, response_path=str(response_path))
        return response

    def write_local_status_response(self, request: ValidatedRequest,
                                    response_dir: str | Path, *,
                                    status: str, safe_error: str) -> dict:
        """Persist a host-generated pre-dispatch or UNKNOWN status without secrets."""
        if status not in {"FAILED_BEFORE_DISPATCH", "UNKNOWN"}:
            raise RunnerError("Invalid local worker response status")
        package = request.package
        response = {
            "request_id": package["request_id"], "case_id": package["case_id"],
            "run_id": package["run_id"], "payload_digest": request.payload_digest,
            "operation": package["operation"], "http_status": None,
            "openai_request_id": None, "model": package["model"],
            "returned_model_id": None, "usage": None,
            "response_body": {"error": {"type": "local_runner_error",
                                           "code": status.lower(),
                                           "message": safe_error[:500]}},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": status,
            "runner_error": safe_error[:500],
        }
        for field in P5_REQUEST_FIELDS:
            if field in package:
                response[field] = package[field]
        self._write_response(response, response_dir, package["request_id"])
        return response

    @staticmethod
    def _write_response(response: dict, response_dir: str | Path,
                        request_id: str) -> Path:
        response_dir = Path(response_dir)
        response_path = response_dir / f"{request_id}.json"
        temp_path = response_path.with_suffix(".json.tmp")
        try:
            response_dir.mkdir(parents=True, exist_ok=True)
            if response_path.exists() or response_path.is_symlink():
                raise RunnerError("Response package already exists")
            encoded = canonical_json_bytes(response) + b"\n"
            with temp_path.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temp_path, response_path)
            temp_path.unlink()
        except RunnerError:
            raise
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise RunnerError("Response package could not be persisted") from None
        return response_path


def _host_state_path() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RunnerError("LOCALAPPDATA is unavailable")
    return Path(local) / "SupplyChainCopilot" / "runner_state.sqlite3"


def _confirm_prompt(request: ValidatedRequest) -> bool:
    package = request.package
    print("Manual API execution confirmation")
    print(f"Case ID: {package['case_id']}")
    print(f"Request ID: {package['request_id']}")
    print(f"Operation: {package['operation']}")
    print(f"Model: {package['model']}")
    print(f"Payload SHA-256: {request.payload_digest}")
    print(f"Destination: {API_URL}")
    return input("Type EXECUTE to continue: ") == "EXECUTE"


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Manual P5 Input Token Count runner")
    parser.add_argument("request_file", help="Validated package from the host/Docker exchange")
    parser.add_argument("--exchange", required=True, help="Exchange directory containing requests/ and responses/")
    args = parser.parse_args(argv)
    try:
        exchange_arg = Path(args.exchange)
        request_arg = Path(args.request_file)
        if exchange_arg.is_symlink() or request_arg.is_symlink():
            raise RunnerError("Exchange and request paths must not be symbolic links")
        exchange = exchange_arg.resolve(strict=True)
        requests_dir = exchange / "requests"
        responses_dir = exchange / "responses"
        if (not exchange.is_dir() or requests_dir.is_symlink() or responses_dir.is_symlink()
                or not requests_dir.is_dir() or not responses_dir.is_dir()):
            raise RunnerError("Exchange requires regular requests and responses directories")
        request_path = request_arg.resolve(strict=True)
        if request_path.parent != requests_dir:
            raise RunnerError("Request file must be directly inside the exchange requests directory")
        request = read_request_file(request_path)
        state_path = _host_state_path().resolve()
        if state_path == exchange or exchange in state_path.parents:
            raise RunnerError("Runner state must remain outside the Docker exchange")
        state = ExecutionStateStore(state_path)
        approved = _confirm_prompt(request)
        runner = ApiRunner(WindowsCredentialManager(), UrllibTransport(), state)
        runner.execute(request, responses_dir, confirm=approved)
        print("Execution completed; response package saved.")
        return 0
    except RunnerError as exc:
        print(f"Runner stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
