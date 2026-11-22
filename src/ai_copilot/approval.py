"""Local owner authentication and one-use, digest-bound approvals.

The owner verifier is supplied by local configuration, never by Demo login.
This module contains no provider dispatch or session-state authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import json
from pathlib import Path
from urllib.parse import quote

from src.ai_copilot.provider import ProviderRequest, ProviderBlocked

POLICY_VERSION = "local-owner-approval-v1"


class ApprovalBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class OwnerVerifier:
    """Scrypt verifier provisioned outside source control (salt and hash hex)."""

    salt_hex: str
    digest_hex: str

    @staticmethod
    def from_environment() -> "OwnerVerifier":
        """Read only a separate owner verifier; the Demo password is never used."""
        salt = os.environ.get("COPILOT_OWNER_SALT_HEX")
        digest = os.environ.get("COPILOT_OWNER_SCRYPT_HEX")
        if not salt or not digest:
            raise ApprovalBlocked("Local owner verifier is not configured")
        verifier = OwnerVerifier(salt, digest)
        try:
            if len(bytes.fromhex(salt)) != 16 or len(bytes.fromhex(digest)) != 64:
                raise ValueError("Invalid verifier")
        except ValueError as exc:
            raise ApprovalBlocked("Local owner verifier is invalid") from exc
        return verifier

    @staticmethod
    def derive(password: str, salt: bytes | None = None) -> "OwnerVerifier":
        """Provision a verifier; callers must store it outside source control."""
        if not isinstance(password, str) or len(password) < 16:
            raise ApprovalBlocked("Owner password must have at least 16 characters")
        salt = salt or secrets.token_bytes(16)
        if len(salt) != 16:
            raise ApprovalBlocked("Invalid owner verifier salt")
        return OwnerVerifier(salt.hex(), hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex())

    def authenticate(self, password: str) -> bool:
        if not isinstance(password, str):
            return False
        try:
            salt = bytes.fromhex(self.salt_hex)
            expected = bytes.fromhex(self.digest_hex)
            if len(salt) != 16 or len(expected) != 64:
                return False
            actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False


def verify_request(request: ProviderRequest) -> None:
    """Reject a changed body even if caller duplicates stale request fields."""
    from src.ai_copilot.provider import OpenAIResponsesAdapter
    from src.ai_brief.contract import canonical_bytes
    import json
    try:
        body = json.loads(request.canonical_body)
        if canonical_bytes(body) != request.canonical_body:
            raise ApprovalBlocked("Request is not canonical")
        if (hashlib.sha256(canonical_bytes(body["brief"])).hexdigest() != body["provider_brief_digest"]
                or body["provider_brief_digest"] != request.provider_brief_digest
                or body["brief_digest"] != request.brief_digest):
            raise ApprovalBlocked("Brief digest mismatch")
        OpenAIResponsesAdapter.call_arguments(request)
    except (ProviderBlocked, KeyError, ValueError, TypeError) as exc:
        raise ApprovalBlocked("Request provenance invalid") from exc


@dataclass(frozen=True)
class ApprovalRecord:
    reference: str
    request_digest: str
    approved_at: int
    expires_at: int
    policy_version: str
    revoked_at: int | None
    consumed_at: int | None
    approved_cost_usd: str | None
    pricing_basis: str | None

    def valid_for(self, request: ProviderRequest, now: int | None = None) -> bool:
        verify_request(request)
        current = int(time.time()) if now is None else now
        return (self.request_digest == request.request_digest and self.approved_at <= current < self.expires_at
                and self.policy_version == POLICY_VERSION and self.revoked_at is None and self.consumed_at is None)


class ApprovalStore:
    """SQLite record. Approval is created only by an explicit authenticated call."""

    def __init__(self, db_path: str):
        if not db_path or db_path == ":memory:":
            raise ApprovalBlocked("Durable local database path required")
        self.db_path = str(Path(db_path).absolute())
        marker = Path(self.db_path + ".identity")
        path = Path(self.db_path)
        try:
            db_stat, marker_stat = path.lstat(), marker.lstat()
            if not path.is_file() or path.is_symlink() or not marker.is_file() or marker.is_symlink():
                raise ApprovalBlocked("Ledger identity is not a regular file")
            identity = json.loads(marker.read_text())
            if (identity.get("version") != 1 or identity.get("device") != db_stat.st_dev
                    or identity.get("inode") != db_stat.st_ino
                    or db_stat.st_mode & 0o077 or marker_stat.st_mode & 0o077):
                raise ApprovalBlocked("Ledger identity or permissions changed")
            self._identity = identity
            with self.connect() as db:
                row = db.execute("SELECT store_id,owner_salt,owner_digest FROM store_identity").fetchone()
                if row is None or row[0] != identity["store_id"]:
                    raise ApprovalBlocked("Ledger identity mismatch")
                self._verifier = OwnerVerifier(row[1], row[2])
                if db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                    raise ApprovalBlocked("Ledger integrity check failed")
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raise ApprovalBlocked("Ledger is missing, corrupt or unprovisioned") from exc

    @staticmethod
    def provision(db_path: str, verifier: OwnerVerifier) -> None:
        """Explicit one-time local provisioning; loss of either file fails closed."""
        if type(verifier) is not OwnerVerifier:
            raise ApprovalBlocked("Owner verifier required for provisioning")
        path = Path(db_path).absolute()
        if (path.exists() or path.is_symlink() or Path(str(path) + ".identity").exists()
                or Path(str(path) + ".identity").is_symlink() or not path.parent.is_dir()):
            raise ApprovalBlocked("Store already exists or parent is unavailable")
        store_id = secrets.token_hex(32)
        marker = Path(str(path) + ".identity")
        try:
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            with sqlite3.connect(str(path)) as db:
                os.chmod(path, 0o600)
                db.execute("""CREATE TABLE store_identity (
                    store_id TEXT NOT NULL PRIMARY KEY, owner_salt TEXT NOT NULL,
                    owner_digest TEXT NOT NULL)""")
                db.execute("INSERT INTO store_identity VALUES (?,?,?)",
                           (store_id, verifier.salt_hex, verifier.digest_hex))
                db.execute("""CREATE TABLE owner_approvals (
                reference TEXT PRIMARY KEY, request_digest TEXT NOT NULL,
                approved_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                policy_version TEXT NOT NULL, revoked_at INTEGER, consumed_at INTEGER,
                approved_cost_usd TEXT, pricing_basis TEXT)""")
            stat = path.stat()
            marker.write_text(json.dumps({"version": 1, "store_id": store_id,
                                          "device": stat.st_dev, "inode": stat.st_ino}, sort_keys=True))
        except (OSError, sqlite3.Error) as exc:
            raise ApprovalBlocked("Provisioning failed; manual recovery required") from exc

    def _check_file(self) -> None:
        try:
            stat = Path(self.db_path).lstat()
            marker = Path(self.db_path + ".identity")
            marker_stat = marker.lstat()
            current_identity = json.loads(marker.read_text())
            if (not Path(self.db_path).is_file() or Path(self.db_path).is_symlink()
                    or stat.st_dev != self._identity["device"] or stat.st_ino != self._identity["inode"]
                    or stat.st_mode & 0o077 or marker.is_symlink()
                    or marker_stat.st_mode & 0o077 or current_identity != self._identity):
                raise ApprovalBlocked("Ledger file changed or is missing")
        except (OSError, ValueError, TypeError) as exc:
            raise ApprovalBlocked("Ledger file changed or is missing") from exc

    def connect(self) -> sqlite3.Connection:
        if hasattr(self, "_identity"):
            self._check_file()
        db = sqlite3.connect("file:" + quote(self.db_path) + "?mode=rw", uri=True,
                             timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def approve(self, request: ProviderRequest, password: str,
                *, ttl_seconds: int = 300, now: int | None = None,
                approved_cost_usd: str | None = None, pricing_basis: str | None = None) -> ApprovalRecord:
        verify_request(request)
        if not self._verifier.authenticate(password):
            raise ApprovalBlocked("Separate owner authentication failed")
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 900:
            raise ApprovalBlocked("Approval lifetime invalid")
        current = int(time.time()) if now is None else now
        ref = secrets.token_hex(24)
        with self.connect() as db:
            db.execute("INSERT INTO owner_approvals VALUES (?,?,?,?,?,NULL,NULL,?,?)",
                       (ref, request.request_digest, current, current + ttl_seconds, POLICY_VERSION,
                        approved_cost_usd, pricing_basis))
        return self.get(ref)

    def get(self, reference: str) -> ApprovalRecord | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM owner_approvals WHERE reference=?", (reference,)).fetchone()
        return ApprovalRecord(*row) if row else None

    def revoke(self, reference: str, *, now: int | None = None) -> None:
        current = int(time.time()) if now is None else now
        with self.connect() as db:
            db.execute("UPDATE owner_approvals SET revoked_at=? WHERE reference=? AND consumed_at IS NULL AND revoked_at IS NULL",
                       (current, reference))
