"""Host-signed, request-specific Owner intent; no API or Ledger access."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import re
import secrets
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes
from tools.windows_api_runner.generation_permit import (
    APPROVED_CAMPAIGN, APPROVED_CASES, APPROVED_NAMESPACE,
    _b64_decode, _decode_unique, _HASH,
)


AUTH_VERSION = "p5-host-owner-authorization-1"
AUTH_PURPOSE = "generation-dispatch-intent"
AUTH_FIELDS = frozenset({
    "version", "purpose", "namespace", "campaign_id", "case_id", "run_id",
    "request_id", "model", "payload_sha256", "count_evidence_sha256",
    "count_projection_sha256", "provider_request_digest", "brief_digest",
    "token_cap", "cost_limit_micro_usd", "nonce", "issued_at", "expires_at",
})


@dataclass(frozen=True)
class VerifiedHostOwnerAuthorization:
    body: dict
    envelope_sha256: str
    key_id: str


def validate_authorization_body(body: object, *, now: int | None = None) -> dict:
    if type(body) is not dict or set(body) != AUTH_FIELDS:
        raise RunnerError("Host Owner Authorization fields are incomplete")
    if (body["version"] != AUTH_VERSION or body["purpose"] != AUTH_PURPOSE
            or body["namespace"] != APPROVED_NAMESPACE
            or body["campaign_id"] != APPROVED_CAMPAIGN
            or body["case_id"] not in APPROVED_CASES
            or body["model"] != "gpt-6-luna"):
        raise RunnerError("Host Owner Authorization is outside the approved scope")
    for field in ("payload_sha256", "count_evidence_sha256",
                  "count_projection_sha256", "provider_request_digest", "brief_digest"):
        if type(body[field]) is not str or not _HASH.fullmatch(body[field]):
            raise RunnerError("Host Owner Authorization digest is invalid")
    for field in ("run_id", "nonce"):
        if (type(body[field]) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", body[field])):
            raise RunnerError("Host Owner Authorization identity is invalid")
    try:
        if str(uuid.UUID(body["request_id"])) != body["request_id"]:
            raise ValueError
    except (TypeError, ValueError, AttributeError):
        raise RunnerError("Host Owner Authorization UUID is invalid") from None
    if (type(body["token_cap"]) is not int or body["token_cap"] != 25000
            or type(body["cost_limit_micro_usd"]) is not int
            or body["cost_limit_micro_usd"] != 20000):
        raise RunnerError("Host Owner Authorization limits are invalid")
    issued, expires = body["issued_at"], body["expires_at"]
    current = int(time.time()) if now is None else now
    if (type(issued) is not int or type(expires) is not int
            or not issued <= current < expires or expires - issued > 300):
        raise RunnerError("Host Owner Authorization expired or is not yet valid")
    return body


def sign_owner_authorization(body: dict, private_key: Ed25519PrivateKey, *,
                             now: int | None = None) -> bytes:
    """Sign only after the Host has independently authenticated its Owner."""
    validate_authorization_body(body, now=now)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RunnerError("Host signing key is unavailable")
    public_raw = private_key.public_key().public_bytes_raw()
    signature = private_key.sign(canonical_json_bytes(body))
    return canonical_json_bytes({
        "body": body,
        "key_id": hashlib.sha256(public_raw).hexdigest(),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode(),
    })


def verify_owner_authorization(raw: bytes, public_key: Ed25519PublicKey, *,
                               expected: dict, now: int | None = None
                               ) -> VerifiedHostOwnerAuthorization:
    if type(raw) is not bytes or len(raw) > 8192:
        raise RunnerError("Host Owner Authorization is missing or oversized")
    envelope = _decode_unique(raw)
    if set(envelope) != {"body", "key_id", "signature"}:
        raise RunnerError("Host Owner Authorization envelope is invalid")
    body = validate_authorization_body(envelope["body"], now=now)
    if (type(expected) is not dict or set(expected) != AUTH_FIELDS - {
            "version", "purpose", "nonce", "issued_at", "expires_at"}
            or any(body[key] != expected[key] for key in expected)):
        raise RunnerError("Host Owner Authorization does not bind the current request")
    key_id = hashlib.sha256(public_key.public_bytes_raw()).hexdigest()
    if envelope["key_id"] != key_id:
        raise RunnerError("Host Owner Authorization signer differs from pinned key")
    try:
        public_key.verify(_b64_decode(envelope["signature"], 64),
                          canonical_json_bytes(body))
    except InvalidSignature:
        raise RunnerError("Host Owner Authorization signature is invalid") from None
    if raw != canonical_json_bytes(envelope):
        raise RunnerError("Host Owner Authorization is not canonical")
    return VerifiedHostOwnerAuthorization(body, hashlib.sha256(raw).hexdigest(), key_id)


def new_authorization_body(scope: dict, *, now: int | None = None) -> dict:
    """Prepare an exact, fresh Host-side authorization body after request display."""
    required = AUTH_FIELDS - {"version", "purpose", "nonce", "issued_at", "expires_at"}
    if type(scope) is not dict or set(scope) != required:
        raise RunnerError("Host Owner Authorization scope is incomplete")
    current = int(time.time()) if now is None else now
    body = {**scope, "version": AUTH_VERSION, "purpose": AUTH_PURPOSE,
            "nonce": secrets.token_hex(24), "issued_at": current,
            "expires_at": current + 300}
    return validate_authorization_body(body, now=current)
