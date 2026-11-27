"""Read-only P5 store qualification and isolated, WAL-safe migration rehearsal.

No function here opens a production database for writing. Schema extension is
limited to a newly created backup copy supplied by the caller.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class QualificationBlocked(RuntimeError):
    """A store is absent, incompatible, corrupt, or cannot be copied safely."""


_PAID_TABLES = frozenset({
    "campaign", "slots", "slot_approvals", "reservations", "campaign_events",
    "paid_authorizations", "provider_observations", "dispatch_claims",
})
_HOST_CLAIM_COLUMNS = frozenset({
    "nonce", "authorization_sha256", "request_id", "campaign_id",
    "case_id", "run_id", "claimed_at",
})


@dataclass(frozen=True)
class StoreSchemaState:
    path: Path
    integrity: str
    sqlite_user_version: int
    tables: frozenset[str]
    missing_paid_tables: frozenset[str]
    host_claim_state: str


@dataclass(frozen=True)
class PublicKeyPair:
    host_key_id: str
    issuer_key_id: str


def inspect_public_key_pair(host_public: str | Path,
                            issuer_public: str | Path) -> PublicKeyPair:
    """Read only explicitly supplied public pins; never inspect private keys."""
    identifiers = []
    for location in (host_public, issuer_public):
        path = Path(location)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != 32:
                raise QualificationBlocked("Pinned public key file is unavailable or invalid")
            raw = path.read_bytes()
        except OSError as exc:
            raise QualificationBlocked("Pinned public key file is unavailable or invalid") from exc
        try:
            Ed25519PublicKey.from_public_bytes(raw)
        except ValueError as exc:
            raise QualificationBlocked("Pinned public key bytes are invalid") from exc
        identifiers.append(hashlib.sha256(raw).hexdigest())
    if identifiers[0] == identifiers[1]:
        raise QualificationBlocked("Host and issuer trust anchors must differ")
    return PublicKeyPair(*identifiers)


@dataclass(frozen=True)
class ArchiveSchemaState:
    path: Path
    integrity: str
    archive_version: str
    contract_matches_source: bool
    event_table_state: str
    append_only_triggers_present: bool


def inspect_archive_schema(path: str | Path) -> ArchiveSchemaState:
    """Read-only structural check; it cannot assert historical event authenticity."""
    from src.ai_copilot.evaluation_archive import ARCHIVE_VERSION, _schema
    target = Path(path).absolute()
    required = {"archive_no_update", "archive_no_delete",
                "archive_dispatch_no_update", "archive_dispatch_no_delete"}
    try:
        with closing(_read_only(target)) as db:
            integrity = db.execute("PRAGMA quick_check(1)").fetchone()[0]
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"archive_meta", "archive_entries"}.issubset(tables):
                raise QualificationBlocked("Archive base schema is incomplete")
            meta = db.execute("SELECT version,schema_digest FROM archive_meta").fetchall()
            if len(meta) != 1:
                raise QualificationBlocked("Archive contract metadata is invalid")
            _, expected_digest = _schema()
            triggers = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'")}
            state = ("PRESENT" if "archive_dispatch_events" in tables else
                     "LEGACY_MISSING")
            return ArchiveSchemaState(target, integrity, meta[0][0],
                                      meta[0] == (ARCHIVE_VERSION, expected_digest), state,
                                      required.issubset(triggers) if state == "PRESENT"
                                      else {"archive_no_update", "archive_no_delete"}.issubset(triggers))
    except sqlite3.Error as exc:
        raise QualificationBlocked("Archive schema inspection failed") from exc


def _read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file() or path.is_symlink():
        raise QualificationBlocked("Existing regular SQLite file required")
    try:
        return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise QualificationBlocked("SQLite store cannot be opened read-only") from exc


def inspect_paid_ledger_schema(path: str | Path) -> StoreSchemaState:
    """Inspect only structural metadata; never return approval or secret rows."""
    target = Path(path).absolute()
    try:
        with closing(_read_only(target)) as db:
            integrity = db.execute("PRAGMA quick_check(1)").fetchone()[0]
            user_version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = frozenset(row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"))
            columns = (frozenset(row[1] for row in db.execute(
                "PRAGMA table_info(host_owner_claims)"))
                if "host_owner_claims" in tables else frozenset())
            unique_sets = set()
            if "host_owner_claims" in tables:
                for index in db.execute("PRAGMA index_list(host_owner_claims)"):
                    if index[2]:
                        quoted = index[1].replace("'", "''")
                        unique_sets.add(frozenset(row[2] for row in db.execute(
                            f"PRAGMA index_info('{quoted}')")))
            required_unique = {frozenset({name}) for name in
                               ("nonce", "authorization_sha256", "request_id")}
            fk_targets = ({row[2] for row in db.execute(
                "PRAGMA foreign_key_list(host_owner_claims)")}
                if "host_owner_claims" in tables else set())
            host_state = ("ABSENT" if "host_owner_claims" not in tables else
                          "PRESENT" if (_HOST_CLAIM_COLUMNS.issubset(columns)
                          and required_unique.issubset(unique_sets)
                          and "reservations" in fk_targets) else "PARTIAL")
            return StoreSchemaState(target, integrity, user_version, tables,
                                    _PAID_TABLES - tables, host_state)
    except sqlite3.Error as exc:
        raise QualificationBlocked("SQLite schema inspection failed") from exc


def backup_and_rehearse_paid_claim_extension(source: str | Path,
                                             destination: str | Path) -> StoreSchemaState:
    """Use SQLite online backup, then extend only the fresh copy, never source.

    Explicitly refuses an existing destination, symlink, incomplete paid schema,
    partial host table, or corrupt source. The caller retains the copy on error.
    """
    original = inspect_paid_ledger_schema(source)
    if (original.integrity != "ok" or original.missing_paid_tables
            or original.host_claim_state == "PARTIAL"):
        raise QualificationBlocked("Paid Ledger schema is incompatible")
    target = Path(destination).absolute()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    resolved_parent = target.parent.resolve()
    repository_root = Path(__file__).resolve().parents[2]
    if (target.exists() or target.is_symlink() or target == original.path
            or not target.parent.is_dir()
            or resolved_parent == repository_root
            or repository_root in resolved_parent.parents
            or not (resolved_parent == temporary_root or
                    temporary_root in resolved_parent.parents)):
        raise QualificationBlocked("Fresh isolated backup path required")
    try:
        # Reserve the exact path before SQLite connects, avoiding accidental overwrite.
        target.touch(mode=0o600, exist_ok=False)
        with closing(_read_only(original.path)) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                raise QualificationBlocked("Backup rehearsal integrity failed")
            if original.host_claim_state == "ABSENT":
                try:
                    dst.execute("BEGIN IMMEDIATE")
                    dst.execute("""CREATE TABLE host_owner_claims (
                    nonce TEXT PRIMARY KEY, authorization_sha256 TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL UNIQUE, campaign_id TEXT NOT NULL,
                    case_id TEXT NOT NULL, run_id TEXT NOT NULL,
                    claimed_at INTEGER NOT NULL,
                    FOREIGN KEY(campaign_id,case_id)
                        REFERENCES reservations(campaign_id,case_id))""")
                    dst.commit()
                except sqlite3.Error:
                    dst.rollback()
                    raise
        result = inspect_paid_ledger_schema(target)
        if result.integrity != "ok" or result.host_claim_state != "PRESENT":
            raise QualificationBlocked("Backup rehearsal integrity failed")
        return result
    except (OSError, sqlite3.Error) as exc:
        raise QualificationBlocked("Backup rehearsal failed; inspect retained copy") from exc
