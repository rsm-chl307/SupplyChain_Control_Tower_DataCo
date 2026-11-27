"""Versioned, signed, one-use Windows Generation dispatch permits.

The Host trusts a pinned P5 issuer public key, never a Container-supplied flag.
This module is independent of Container P5 imports and the count package format.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes


PERMIT_VERSION = "p5-generation-dispatch-permit-1"
PERMIT_OPERATION = "responses_generation"
PROPOSAL_VERSION = "p5-generation-proposal-1"
PROPOSAL_OPERATION = "responses_generation_proposal"
APPROVED_NAMESPACE = "p5-eight-scenario-evaluation-v1"
APPROVED_CAMPAIGN = "paid-p5-eight-scenario-evaluation-v1"
APPROVED_CASES = frozenset({f"EV-{index:02d}" for index in range(1, 8)} | {"EV-08-LR"})
PERMIT_FIELDS = frozenset({
    "version", "operation", "namespace", "campaign_id", "case_id", "run_id",
    "request_id", "dispatch_id", "model", "payload_sha256",
    "count_payload_sha256", "count_projection_sha256", "count_evidence_sha256",
    "count_request_id", "input_tokens", "token_cap", "provider_request_digest",
    "brief_digest", "approval_reference", "paid_authorization_reference",
    "ledger_attempt_id", "archive_intent_digest", "cost_limit_micro_usd",
    "host_authorization_sha256", "proposal_sha256", "issued_at", "expires_at",
})
PROPOSAL_FIELDS = (PERMIT_FIELDS - {"host_authorization_sha256", "proposal_sha256"}) | {"payload"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REF = re.compile(r"[0-9a-zA-Z_.:-]{1,128}\Z")


def _decode_unique(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RunnerError("Duplicate permit fields are forbidden")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise RunnerError("Permit is not strict UTF-8 JSON") from None
    if type(value) is not dict:
        raise RunnerError("Permit must be an object")
    return value


def _b64_decode(value: object, length: int) -> bytes:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise RunnerError("Permit signature encoding is invalid")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error):
        raise RunnerError("Permit signature encoding is invalid") from None
    if len(raw) != length or base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != value:
        raise RunnerError("Permit signature encoding is invalid")
    return raw


@dataclass(frozen=True)
class VerifiedGenerationPermit:
    body: dict
    permit_sha256: str
    key_id: str


@dataclass(frozen=True)
class VerifiedGenerationProposal:
    body: dict
    proposal_sha256: str
    key_id: str


def validate_permit_body(body: object, *, now: int | None = None) -> dict:
    if type(body) is not dict or set(body) != PERMIT_FIELDS:
        raise RunnerError("Generation permit fields are incomplete")
    if body["version"] != PERMIT_VERSION or body["operation"] != PERMIT_OPERATION:
        raise RunnerError("Generation permit version or operation is invalid")
    if (body["namespace"] != APPROVED_NAMESPACE
            or body["campaign_id"] != APPROVED_CAMPAIGN
            or body["case_id"] not in APPROVED_CASES):
        raise RunnerError("Generation permit is outside the approved campaign")
    for field in ("payload_sha256", "count_payload_sha256", "count_projection_sha256",
                  "count_evidence_sha256", "provider_request_digest", "brief_digest",
                  "archive_intent_digest", "host_authorization_sha256", "proposal_sha256"):
        if type(body[field]) is not str or not _HASH.fullmatch(body[field]):
            raise RunnerError("Generation permit digest is invalid")
    for field in ("namespace", "campaign_id", "case_id", "run_id", "dispatch_id",
                  "model", "count_request_id", "approval_reference",
                  "paid_authorization_reference", "ledger_attempt_id"):
        if type(body[field]) is not str or not _REF.fullmatch(body[field]):
            raise RunnerError("Generation permit identity is invalid")
    try:
        if str(uuid.UUID(body["request_id"])) != body["request_id"]:
            raise ValueError
    except (TypeError, ValueError, AttributeError):
        raise RunnerError("Generation permit request UUID is invalid") from None
    if (body["model"] != "gpt-6-luna"
            or body["token_cap"] != 25000 or type(body["token_cap"]) is not int
            or type(body["input_tokens"]) is not int
            or not 0 <= body["input_tokens"] <= body["token_cap"]
            or type(body["cost_limit_micro_usd"]) is not int
            or body["cost_limit_micro_usd"] != 20000):
        raise RunnerError("Generation permit model, token or cost limit is invalid")
    issued, expires = body["issued_at"], body["expires_at"]
    current = int(time.time()) if now is None else now
    if (type(issued) is not int or type(expires) is not int
            or not issued <= current < expires or expires - issued > 300):
        raise RunnerError("Generation permit is expired or not yet valid")
    return body


def _signed_envelope(body: dict, private_key: Ed25519PrivateKey) -> bytes:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RunnerError("P5 issuer signing key is unavailable")
    public_raw = private_key.public_key().public_bytes_raw()
    signature = private_key.sign(canonical_json_bytes(body))
    return canonical_json_bytes({
        "body": body, "key_id": hashlib.sha256(public_raw).hexdigest(),
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode(),
    })


def sign_dispatch_permit(body: dict, private_key: Ed25519PrivateKey, *,
                         now: int | None = None) -> bytes:
    validate_permit_body(body, now=now)
    return _signed_envelope(body, private_key)


def validate_proposal_body(body: object, *, now: int | None = None) -> dict:
    if type(body) is not dict or set(body) != PROPOSAL_FIELDS:
        raise RunnerError("Generation proposal fields are incomplete")
    if body["version"] != PROPOSAL_VERSION or body["operation"] != PROPOSAL_OPERATION:
        raise RunnerError("Generation proposal version or operation is invalid")
    permit_view = {key: body[key] for key in PERMIT_FIELDS
                   if key not in {"host_authorization_sha256", "proposal_sha256"}}
    permit_view.update({"version": PERMIT_VERSION, "operation": PERMIT_OPERATION,
                        "host_authorization_sha256": "0" * 64,
                        "proposal_sha256": "0" * 64})
    validate_permit_body(permit_view, now=now)
    payload = body["payload"]
    allowed = {"model", "instructions", "input", "text", "max_output_tokens",
               "store", "background", "stream", "tool_choice", "tools",
               "reasoning", "truncation"}
    if (type(payload) is not dict or set(payload) != allowed
            or payload["model"] != body["model"]
            or type(payload["instructions"]) is not str or not payload["instructions"]
            or type(payload["input"]) is not str or not payload["input"]
            or payload["max_output_tokens"] != 25000
            or any(payload[field] is not False for field in ("store", "background", "stream"))
            or payload["tool_choice"] != "none" or payload["tools"] != []
            or payload["reasoning"] != {"effort": "medium"}
            or payload["truncation"] != "disabled"
            or type(payload["text"]) is not dict
            or type(payload["text"].get("format")) is not dict
            or payload["text"]["format"].get("type") != "json_schema"
            or payload["text"]["format"].get("strict") is not True):
        raise RunnerError("Generation payload does not match the strict P5 profile")
    payload_wire = canonical_json_bytes(payload)
    if len(payload_wire) > 786432 or hashlib.sha256(payload_wire).hexdigest() != body["payload_sha256"]:
        raise RunnerError("Generation payload digest or size is invalid")
    count_allowed = {"conversation", "input", "instructions", "model",
                     "parallel_tool_calls", "personality", "previous_response_id",
                     "reasoning", "text", "tool_choice", "tools", "truncation"}
    count = {key: payload[key] for key in count_allowed if key in payload}
    projection_fields = ("model", "input", "instructions", "text", "reasoning",
                         "truncation", "tools", "tool_choice")
    if (hashlib.sha256(canonical_json_bytes(count)).hexdigest()
            != body["count_payload_sha256"]
            or hashlib.sha256(canonical_json_bytes(
                {key: count[key] for key in projection_fields})).hexdigest()
            != body["count_projection_sha256"]):
        raise RunnerError("Generation payload differs from counted payload")
    return body


def sign_generation_proposal(body: dict, private_key: Ed25519PrivateKey, *,
                             now: int | None = None) -> bytes:
    validate_proposal_body(body, now=now)
    return _signed_envelope(body, private_key)


def verify_signed_proposal(raw: bytes, public_key: Ed25519PublicKey, *,
                           now: int | None = None) -> VerifiedGenerationProposal:
    if type(raw) is not bytes or len(raw) > 1_048_576:
        raise RunnerError("Generation proposal is missing or oversized")
    envelope = _decode_unique(raw)
    if set(envelope) != {"body", "signature", "key_id"}:
        raise RunnerError("Signed Generation proposal envelope is invalid")
    body = validate_proposal_body(envelope["body"], now=now)
    key_id = hashlib.sha256(public_key.public_bytes_raw()).hexdigest()
    if envelope["key_id"] != key_id:
        raise RunnerError("Generation proposal issuer differs from Host trust anchor")
    try:
        public_key.verify(_b64_decode(envelope["signature"], 64), canonical_json_bytes(body))
    except InvalidSignature:
        raise RunnerError("Generation proposal signature is invalid") from None
    if raw != canonical_json_bytes(envelope):
        raise RunnerError("Generation proposal is not canonical")
    return VerifiedGenerationProposal(body, hashlib.sha256(raw).hexdigest(), key_id)


def verify_signed_permit(raw: bytes, public_key: Ed25519PublicKey, *,
                         now: int | None = None) -> VerifiedGenerationPermit:
    if type(raw) is not bytes or len(raw) > 8192:
        raise RunnerError("Generation permit is missing or oversized")
    envelope = _decode_unique(raw)
    if set(envelope) != {"body", "signature", "key_id"}:
        raise RunnerError("Signed generation permit envelope is invalid")
    body = validate_permit_body(envelope["body"], now=now)
    key_raw = public_key.public_bytes_raw()
    key_id = hashlib.sha256(key_raw).hexdigest()
    if envelope["key_id"] != key_id:
        raise RunnerError("Generation permit issuer key differs from Host trust anchor")
    body_wire = canonical_json_bytes(body)
    try:
        public_key.verify(_b64_decode(envelope["signature"], 64), body_wire)
    except InvalidSignature:
        raise RunnerError("Generation permit signature is invalid") from None
    if raw != canonical_json_bytes(envelope):
        raise RunnerError("Generation permit is not canonically serialized")
    return VerifiedGenerationPermit(body, hashlib.sha256(raw).hexdigest(), key_id)


def load_host_trust_anchor(path: str | Path) -> Ed25519PublicKey:
    """Read a separately provisioned Host-local public key, never an exchange file."""
    target = Path(path)
    try:
        info = target.lstat()
        if target.is_symlink() or not target.is_file() or info.st_size != 32:
            raise RunnerError("Host generation trust anchor is invalid")
        return Ed25519PublicKey.from_public_bytes(target.read_bytes())
    except OSError:
        raise RunnerError("Host generation trust anchor is unavailable") from None


class HostGenerationPermitState:
    """Durable Host-local one-use claim/revocation tables in Runner SQLite."""

    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS generation_permit_claims (
                permit_sha256 TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                campaign_id TEXT NOT NULL, case_id TEXT NOT NULL, run_id TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL, state TEXT NOT NULL,
                claimed_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS generation_case_run_once
                ON generation_permit_claims(campaign_id,case_id,run_id)""")
            db.execute("""CREATE TABLE IF NOT EXISTS generation_permit_revocations (
                permit_sha256 TEXT PRIMARY KEY, revoked_at INTEGER NOT NULL)""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def revoke(self, permit_sha256: str) -> None:
        if type(permit_sha256) is not str or not _HASH.fullmatch(permit_sha256):
            raise RunnerError("Revocation identity is invalid")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM generation_permit_claims WHERE permit_sha256=?",
                              (permit_sha256,)).fetchone():
                    raise RunnerError("Claimed permit cannot be revoked into a retryable state")
                db.execute("INSERT INTO generation_permit_revocations VALUES (?,?)",
                           (permit_sha256, int(time.time())))
                db.commit()
            except (sqlite3.Error, RunnerError) as exc:
                db.rollback()
                raise RunnerError("Permit revocation failed or already recorded") from None

    def claim(self, permit: VerifiedGenerationPermit, *, now: int | None = None) -> None:
        body = validate_permit_body(permit.body, now=now)
        current = int(time.time()) if now is None else now
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM generation_permit_revocations WHERE permit_sha256=?",
                              (permit.permit_sha256,)).fetchone():
                    raise RunnerError("Generation permit has been revoked")
                db.execute("""INSERT INTO generation_permit_claims VALUES
                    (?,?,?,?,?,?, 'CLAIMED', ?,?)""",
                    (permit.permit_sha256, body["request_id"], body["campaign_id"],
                     body["case_id"], body["run_id"], body["payload_sha256"],
                     current, current))
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                raise RunnerError("Generation permit or Request was already claimed") from None
            except (sqlite3.Error, RunnerError):
                db.rollback()
                raise

    def transition(self, permit_sha256: str, expected: str, target: str) -> None:
        if (expected, target) not in {
            ("CLAIMED", "IN_PROGRESS"), ("CLAIMED", "FAILED_BEFORE_DISPATCH"),
            ("IN_PROGRESS", "SUCCEEDED"), ("IN_PROGRESS", "FAILED_AFTER_DISPATCH"),
            ("IN_PROGRESS", "UNKNOWN"),
        }:
            raise RunnerError("Generation permit state transition is invalid")
        with closing(self._connect()) as db:
            changed = db.execute("""UPDATE generation_permit_claims
                SET state=?,updated_at=? WHERE permit_sha256=? AND state=?""",
                (target, int(time.time()), permit_sha256, expected)).rowcount
            if changed != 1:
                raise RunnerError("Generation permit state changed; no redispatch")

    def state(self, permit_sha256: str) -> str | None:
        with closing(self._connect()) as db:
            row = db.execute("SELECT state FROM generation_permit_claims WHERE permit_sha256=?",
                             (permit_sha256,)).fetchone()
        return row[0] if row else None

    def recover_unfinished(self) -> int:
        """On Host process restart, make uncertain claims permanently non-retryable."""
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                changed = db.execute("""UPDATE generation_permit_claims
                    SET state='UNKNOWN',updated_at=?
                    WHERE state IN ('CLAIMED','IN_PROGRESS')""",
                    (int(time.time()),)).rowcount
                db.commit()
                return changed
            except sqlite3.Error:
                db.rollback()
                raise RunnerError("Unfinished Generation recovery failed") from None
