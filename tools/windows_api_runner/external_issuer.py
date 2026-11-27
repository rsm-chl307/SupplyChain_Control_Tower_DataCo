"""Host-only Fake External Issuer qualification seam.

The issuer accepts only Host-controlled evidence sources. No production evidence
source or formal key loader is wired here; a Container package cannot register
its own Ledger Claim or Archive Intent by supplying status fields.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import os
import sqlite3
import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from tools.windows_api_runner.api_runner import RunnerError, canonical_json_bytes
from tools.windows_api_runner.generation_authorization import (
    AUTH_FIELDS, verify_owner_authorization,
)
from tools.windows_api_runner.generation_permit import (
    PERMIT_FIELDS, PERMIT_OPERATION, PERMIT_VERSION, _decode_unique, sign_dispatch_permit,
    verify_signed_permit, verify_signed_proposal,
)


ISSUER_REQUEST_VERSION = "p5-external-issuer-request-1"
ISSUER_RESPONSE_VERSION = "p5-external-issuer-response-1"
MAX_ISSUER_REQUEST_BYTES = 1_100_000


@dataclass(frozen=True)
class EvidenceStatus:
    claim_state: str
    intent_state: str


class FakeHostEvidenceStore:
    """Isolated Host-owned test state; never populated from a Container package."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS fake_claims(
                    request_id TEXT PRIMARY KEY, proposal_sha256 TEXT NOT NULL,
                    ledger_attempt_id TEXT NOT NULL, state TEXT NOT NULL,
                    issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS fake_intents(
                    request_id TEXT PRIMARY KEY, proposal_sha256 TEXT NOT NULL,
                    archive_intent_digest TEXT NOT NULL, state TEXT NOT NULL,
                    issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS issuer_uses(
                    request_id TEXT PRIMARY KEY, nonce TEXT NOT NULL UNIQUE,
                    proposal_sha256 TEXT NOT NULL, permit_sha256 TEXT NOT NULL,
                    issued_at INTEGER NOT NULL);
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def register_fake_evidence(self, *, request_id: str, proposal_sha256: str,
                               ledger_attempt_id: str, archive_intent_digest: str,
                               claim_state: str = "CLAIMED",
                               intent_state: str = "GENERATION_INTENT",
                               issued_at: int | None = None,
                               expires_at: int | None = None) -> None:
        """Test setup only; no production CLI or exchange route calls this method."""
        issued = int(time.time()) if issued_at is None else issued_at
        expires = issued + 300 if expires_at is None else expires_at
        if (type(issued) is not int or type(expires) is not int
                or expires <= issued or expires - issued > 300):
            raise RunnerError("Fake evidence validity window is invalid")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO fake_claims VALUES (?,?,?,?,?,?)",
                       (request_id, proposal_sha256, ledger_attempt_id, claim_state, issued, expires))
            db.execute("INSERT INTO fake_intents VALUES (?,?,?,?,?,?)",
                       (request_id, proposal_sha256, archive_intent_digest, intent_state, issued, expires))
            db.commit()

    def claim_issuance(self, *, request_id: str, nonce: str, proposal_sha256: str,
                       ledger_attempt_id: str, archive_intent_digest: str,
                       permit_sha256: str, now: int) -> EvidenceStatus:
        """Atomically check independent Host state and consume the request/nonce."""
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                claim = db.execute("SELECT proposal_sha256,ledger_attempt_id,state,issued_at,expires_at FROM fake_claims WHERE request_id=?",
                                   (request_id,)).fetchone()
                intent = db.execute("SELECT proposal_sha256,archive_intent_digest,state,issued_at,expires_at FROM fake_intents WHERE request_id=?",
                                    (request_id,)).fetchone()
                if (claim is None or claim[:3] != (proposal_sha256, ledger_attempt_id, "CLAIMED")
                        or not claim[3] <= now < claim[4]):
                    raise RunnerError("Independent Ledger Claim evidence is missing or inconsistent")
                if (intent is None or intent[:3] != (proposal_sha256, archive_intent_digest, "GENERATION_INTENT")
                        or not intent[3] <= now < intent[4]):
                    raise RunnerError("Independent Archive Intent evidence is missing or inconsistent")
                db.execute("INSERT INTO issuer_uses VALUES (?,?,?,?,?)",
                           (request_id, nonce, proposal_sha256, permit_sha256, now))
                db.commit()
                return EvidenceStatus(claim[2], intent[2])
            except sqlite3.IntegrityError:
                db.rollback()
                raise RunnerError("External Issuer request or nonce already consumed") from None
            except (sqlite3.Error, RunnerError):
                db.rollback()
                raise


class ExternalIssuer:
    """Issue only after signed Owner proof and Host-owned Claim/Intent evidence."""

    def __init__(self, *, issuer_key: Ed25519PrivateKey,
                 owner_public_key: Ed25519PublicKey, evidence: FakeHostEvidenceStore):
        if issuer_key.public_key().public_bytes_raw() == owner_public_key.public_bytes_raw():
            raise RunnerError("External Issuer and Host Owner keys must differ")
        self.issuer_key = issuer_key
        self.owner_public_key = owner_public_key
        self.evidence = evidence

    def issue(self, raw: bytes, *, now: int | None = None) -> bytes:
        if type(raw) is not bytes or not raw or len(raw) > MAX_ISSUER_REQUEST_BYTES:
            raise RunnerError("External Issuer request is missing or oversized")
        try:
            request = _decode_unique(raw)
            if (type(request) is not dict or set(request) != {
                    "version", "request_id", "nonce", "issued_at", "expires_at",
                    "proposal", "host_authorization"}
                    or request["version"] != ISSUER_REQUEST_VERSION
                    or canonical_json_bytes(request) != raw):
                raise ValueError
            if str(uuid.UUID(request["request_id"])) != request["request_id"]:
                raise ValueError
            if (type(request["nonce"]) is not str
                    or re.fullmatch(r"[0-9a-f]{48}", request["nonce"]) is None):
                raise ValueError
            current = int(time.time()) if now is None else now
            if (type(request["issued_at"]) is not int
                    or type(request["expires_at"]) is not int
                    or not request["issued_at"] <= current < request["expires_at"]
                    or request["expires_at"] - request["issued_at"] > 300):
                raise ValueError
            proposal_raw = canonical_json_bytes(request["proposal"])
            auth_raw = canonical_json_bytes(request["host_authorization"])
        except (UnicodeError, ValueError, TypeError, KeyError, RunnerError):
            raise RunnerError("External Issuer request contract is invalid") from None
        proposal = verify_signed_proposal(proposal_raw, self.issuer_key.public_key(), now=current)
        body = proposal.body
        if body["request_id"] != request["request_id"]:
            raise RunnerError("External Issuer request UUID differs from proposal")
        expected = {key: body[key] for key in AUTH_FIELDS - {
            "version", "purpose", "nonce", "issued_at", "expires_at"}}
        proof = verify_owner_authorization(auth_raw, self.owner_public_key,
                                           expected=expected, now=current)
        permit_body = {key: body[key] for key in PERMIT_FIELDS if key in body}
        permit_body.update({
            "version": PERMIT_VERSION, "operation": PERMIT_OPERATION,
            "host_authorization_sha256": proof.envelope_sha256,
            "proposal_sha256": proposal.proposal_sha256,
            "issued_at": current, "expires_at": min(current + 300, request["expires_at"]),
        })
        permit_raw = sign_dispatch_permit(permit_body, self.issuer_key, now=current)
        self.evidence.claim_issuance(
            request_id=request["request_id"], nonce=request["nonce"],
            proposal_sha256=proposal.proposal_sha256,
            ledger_attempt_id=body["ledger_attempt_id"],
            archive_intent_digest=body["archive_intent_digest"],
            permit_sha256=hashlib.sha256(permit_raw).hexdigest(), now=current)
        return canonical_json_bytes({
            "version": ISSUER_RESPONSE_VERSION,
            "request_id": request["request_id"],
            "request_sha256": hashlib.sha256(raw).hexdigest(),
            "issuer_key_id": hashlib.sha256(
                self.issuer_key.public_key().public_bytes_raw()).hexdigest(),
            "permit": json.loads(permit_raw),
        })


def verify_external_issuer_response(raw: bytes, request_raw: bytes,
                                    public_key: Ed25519PublicKey, *,
                                    now: int | None = None) -> bytes:
    """Verify issuer identity, exact request and signed Permit before handoff."""
    if (type(raw) is not bytes or not raw or len(raw) > 16384
            or type(request_raw) is not bytes or not request_raw):
        raise RunnerError("External Issuer response is missing or oversized")
    try:
        response = _decode_unique(raw)
        request = _decode_unique(request_raw)
        if (type(response) is not dict or set(response) != {
                "version", "request_id", "request_sha256", "issuer_key_id", "permit"}
                or response["version"] != ISSUER_RESPONSE_VERSION
                or canonical_json_bytes(response) != raw
                or response["request_id"] != request["request_id"]
                or response["request_sha256"] != hashlib.sha256(request_raw).hexdigest()
                or response["issuer_key_id"] != hashlib.sha256(
                    public_key.public_bytes_raw()).hexdigest()):
            raise ValueError
        permit_raw = canonical_json_bytes(response["permit"])
        proposal_raw = canonical_json_bytes(request["proposal"])
        auth_raw = canonical_json_bytes(request["host_authorization"])
    except (UnicodeError, ValueError, TypeError, KeyError, RunnerError):
        raise RunnerError("External Issuer response identity is invalid") from None
    permit = verify_signed_permit(permit_raw, public_key, now=now)
    proposal = verify_signed_proposal(proposal_raw, public_key, now=now)
    if (permit.body["request_id"] != response["request_id"]
            or permit.body["proposal_sha256"] != proposal.proposal_sha256
            or permit.body["host_authorization_sha256"] != hashlib.sha256(auth_raw).hexdigest()):
        raise RunnerError("External Issuer Permit differs from request")
    return permit_raw


def process_fake_exchange_once(issuer: ExternalIssuer, exchange_root: str | Path,
                               request_id: str, *, now: int | None = None) -> Path:
    """Process one isolated Fake inbox file; never overwrite or retry a claim.

    A crash after issuance can leave a missing or partial response. The durable
    one-use row then blocks reissue; an operator must reconcile that ambiguity.
    This function has no formal key loader or production evidence source.
    """
    if type(issuer) is not ExternalIssuer or type(request_id) is not str:
        raise RunnerError("Fake exchange issuer or request identity is invalid")
    try:
        if str(uuid.UUID(request_id)) != request_id:
            raise ValueError
    except ValueError:
        raise RunnerError("Fake exchange request UUID is invalid") from None
    root = Path(exchange_root)
    inbox = root / "requests"
    outbox = root / "responses"
    request_path = inbox / f"{request_id}.json"
    response_path = outbox / f"{request_id}.json"
    if (root.is_symlink() or inbox.is_symlink() or outbox.is_symlink()
            or request_path.is_symlink() or response_path.is_symlink()
            or not request_path.is_file() or response_path.exists()):
        raise RunnerError("Fake exchange path is missing or already processed")
    raw = request_path.read_bytes()
    try:
        if _decode_unique(raw)["request_id"] != request_id:
            raise RunnerError("Fake exchange filename differs from request UUID")
    except (KeyError, TypeError, RunnerError):
        raise RunnerError("Fake exchange filename or request UUID is invalid") from None
    response = issuer.issue(raw, now=now)
    try:
        outbox.mkdir(parents=True, exist_ok=True)
        with response_path.open("xb") as stream:
            stream.write(response)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        # Do not retry: the issuer claim may already have committed.
        raise RunnerError("Fake issuer response persistence is uncertain") from None
    return response_path
