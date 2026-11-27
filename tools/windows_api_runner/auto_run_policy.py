"""Strict Windows-local policy for the opt-in Input Token Count worker."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from tools.windows_api_runner.api_runner import (
    ALLOWED_MODEL, MAX_PACKAGE_BYTES, MAX_PAYLOAD_BYTES, OPERATION, RunnerError,
    canonical_json_bytes,
)


KNOWN_CASES = frozenset({"EV-01", "EV-02", "EV-03", "EV-04", "EV-05",
                         "EV-06", "EV-07", "EV-08-LR"})
POLICY_FIELDS = frozenset({
    "schema_version", "enabled", "allowed_operations", "allowed_models",
    "allowed_case_ids", "max_requests_per_utc_day", "max_request_bytes",
    "max_payload_bytes",
})


@dataclass(frozen=True)
class LocalAutoRunPolicy:
    enabled: bool
    allowed_operations: tuple[str, ...]
    allowed_models: tuple[str, ...]
    allowed_case_ids: tuple[str, ...]
    max_requests_per_utc_day: int
    max_request_bytes: int
    max_payload_bytes: int

    @classmethod
    def disabled(cls) -> "LocalAutoRunPolicy":
        return cls(False, (OPERATION,), (ALLOWED_MODEL,), (), 1,
                   MAX_PACKAGE_BYTES, MAX_PAYLOAD_BYTES)

    @classmethod
    def load(cls, path: str | Path) -> "LocalAutoRunPolicy":
        """Load only the exact local schema. Missing or malformed policy denies all."""
        target = Path(path)
        if not target.exists():
            return cls.disabled()
        try:
            if target.is_symlink() or not target.is_file():
                raise RunnerError("Local auto-run policy must be a regular host file")
            raw = target.read_bytes()
            if len(raw) > 32_768:
                raise RunnerError("Local auto-run policy exceeds its size limit")
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
        except FileNotFoundError:
            return cls.disabled()
        except RunnerError:
            raise
        except Exception as exc:
            raise RunnerError("Local auto-run policy is invalid or unavailable") from exc
        if type(value) is not dict or set(value) != POLICY_FIELDS:
            raise RunnerError("Local auto-run policy fields are invalid")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise RunnerError("Unsupported local auto-run policy version")
        if type(value["enabled"]) is not bool:
            raise RunnerError("Local auto-run enabled flag must be boolean")
        operations = _string_tuple(value["allowed_operations"], "allowed_operations")
        models = _string_tuple(value["allowed_models"], "allowed_models")
        cases = _string_tuple(value["allowed_case_ids"], "allowed_case_ids")
        if (any(item != OPERATION for item in operations)
                or any(item != ALLOWED_MODEL for item in models)
                or any(item not in KNOWN_CASES for item in cases)):
            raise RunnerError("Local policy contains an unsupported operation, model, or Case")
        daily = _bounded_int(value["max_requests_per_utc_day"], 1, 100,
                             "max_requests_per_utc_day")
        request_bytes = _bounded_int(value["max_request_bytes"], 1, MAX_PACKAGE_BYTES,
                                     "max_request_bytes")
        payload_bytes = _bounded_int(value["max_payload_bytes"], 1, MAX_PAYLOAD_BYTES,
                                     "max_payload_bytes")
        return cls(value["enabled"], operations, models, cases, daily,
                   request_bytes, payload_bytes)

    def denial_reason(self, package: dict, raw_size: int,
                      dispatched_today: int) -> str | None:
        """Return a safe local denial reason; never trusts request policy fields."""
        if not self.enabled:
            return "Auto-run policy is disabled"
        if package.get("operation") not in self.allowed_operations:
            return "Operation is not allowed by local policy"
        if package.get("model") not in self.allowed_models:
            return "Model is not allowed by local policy"
        if package.get("case_id") not in self.allowed_case_ids:
            return "Case is not allowed by local policy"
        if raw_size > self.max_request_bytes:
            return "Request package exceeds local policy size limit"
        try:
            payload_size = len(canonical_json_bytes(package["payload"]))
        except (KeyError, RunnerError):
            return "Request payload is invalid"
        if payload_size > self.max_payload_bytes:
            return "Request payload exceeds local policy size limit"
        if dispatched_today >= self.max_requests_per_utc_day:
            return "Daily local API request limit reached"
        return None


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate policy field")
        result[key] = value
    return result


def _string_tuple(value, name: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise RunnerError(f"Local policy {name} must be a string array")
    if len(value) != len(set(value)):
        raise RunnerError(f"Local policy {name} contains duplicates")
    return tuple(value)


def _bounded_int(value, minimum: int, maximum: int, name: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise RunnerError(f"Local policy {name} is outside the allowed range")
    return value
