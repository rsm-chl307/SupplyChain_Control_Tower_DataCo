"""One durable, default-disabled local budget for Count and Generation.

The Host must use the same database for both fixed network transports. This
ledger is a local pre-dispatch ceiling, not proof of the Provider's final bill.
No constructor or import provisions, enables, or reads an API credential.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid
from typing import Protocol


TRIAL_LIMIT_MICRO = 1_000_000
SAFETY_BUFFER_MICRO = 200_000
GENERATION_LIMIT_MICRO = 20_000
OPERATIONS = frozenset({"input_token_count", "responses_generation"})
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class TrialBudgetBlocked(RuntimeError):
    """No new network request may be made; messages contain no payloads."""


class OwnerAuthenticator(Protocol):
    def authenticate(self, password: str) -> bool: ...


@dataclass(frozen=True)
class BudgetReservation:
    request_id: str
    operation: str
    campaign_id: str
    model: str
    payload_sha256: str
    estimated_micro: int
    reserved_micro: int
    price_version: str

    def validate(self) -> None:
        try:
            uuid.UUID(self.request_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise TrialBudgetBlocked("Trial request identity is invalid") from exc
        if (not isinstance(self.request_id, str) or len(self.request_id) > 128
                or not isinstance(self.campaign_id, str) or not 1 <= len(self.campaign_id) <= 100
                or self.operation not in OPERATIONS or self.model != "gpt-6-luna"
                or not isinstance(self.payload_sha256, str)
                or _DIGEST.fullmatch(self.payload_sha256) is None
                or not isinstance(self.price_version, str)
                or not 1 <= len(self.price_version) <= 100
                or type(self.estimated_micro) is not int
                or type(self.reserved_micro) is not int
                or not 0 < self.estimated_micro <= self.reserved_micro
                or self.reserved_micro != GENERATION_LIMIT_MICRO):
            raise TrialBudgetBlocked("Trial reservation identity or price basis is invalid")


class TrialBudgetController:
    """SQLite BEGIN IMMEDIATE serializes claims across local Host processes.

    Reservations are never refunded. UNKNOWN, missing usage, an overrun, or a
    crash after claim holds the trial until separate Owner reconciliation.
    Moving to another Host requires its copy of the authoritative database;
    a missing database fails closed rather than starting a new allowance.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.is_symlink() or not self.path.is_file():
            raise TrialBudgetBlocked("Existing local Trial budget database required")
        if os.name != "nt":
            mode = self.path.stat().st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                raise TrialBudgetBlocked("Trial budget database permissions are unsafe")
        with closing(self._connect()) as db:
            self._check(db)

    @classmethod
    def provision(cls, path: str | Path, trial_id: str,
                  *, price_version: str) -> "TrialBudgetController":
        """Create a disabled single-trial store; never replace an existing one."""
        target = Path(path)
        if (not target.is_absolute() or target.is_symlink() or not target.parent.is_dir()
                or not isinstance(trial_id, str) or not 1 <= len(trial_id) <= 100
                or not isinstance(price_version, str) or not 1 <= len(price_version) <= 100):
            raise TrialBudgetBlocked("Trial budget provisioning inputs are invalid")
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            with closing(sqlite3.connect(target)) as db:
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
                db.execute("""CREATE TABLE trial (
                    id INTEGER PRIMARY KEY CHECK(id=1), trial_id TEXT NOT NULL,
                    price_version TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                    held INTEGER NOT NULL CHECK(held IN (0,1)),
                    limit_micro INTEGER NOT NULL, buffer_micro INTEGER NOT NULL)""")
                db.execute("""CREATE TABLE requests (
                    request_id TEXT PRIMARY KEY, operation TEXT NOT NULL,
                    campaign_id TEXT NOT NULL, model TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, estimated_micro INTEGER NOT NULL,
                    reserved_micro INTEGER NOT NULL, price_version TEXT NOT NULL,
                    state TEXT NOT NULL, actual_micro INTEGER, usage_json TEXT,
                    billing_source TEXT, latency_ms INTEGER,
                    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""")
                db.execute("INSERT INTO trial VALUES (1,?,?,0,0,?,?)",
                           (trial_id, price_version, TRIAL_LIMIT_MICRO, SAFETY_BUFFER_MICRO))
                db.commit()
        except (OSError, sqlite3.Error) as exc:
            raise TrialBudgetBlocked("Trial budget database could not be provisioned") from exc
        return cls(target)

    def _connect(self) -> sqlite3.Connection:
        try:
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                 timeout=30, isolation_level=None)
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA synchronous=FULL")
            return db
        except sqlite3.Error as exc:
            raise TrialBudgetBlocked("Trial budget database unavailable") from exc

    @staticmethod
    def _check(db: sqlite3.Connection) -> tuple:
        try:
            row = db.execute("SELECT trial_id,price_version,enabled,held,limit_micro,buffer_micro "
                             "FROM trial WHERE id=1").fetchone()
            if (row is None or len(row) != 6 or row[4] != TRIAL_LIMIT_MICRO
                    or row[5] != SAFETY_BUFFER_MICRO or row[2] not in (0, 1)
                    or row[3] not in (0, 1)):
                raise TrialBudgetBlocked("Trial budget policy differs from approved limit")
            return row
        except sqlite3.Error as exc:
            raise TrialBudgetBlocked("Trial budget database schema is invalid") from exc

    def enable(self, verifier: OwnerAuthenticator, password: str) -> None:
        """Owner action only. This does not unlock either real transport."""
        if not verifier.authenticate(password):
            raise TrialBudgetBlocked("Owner authorization required for local Trial")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._check(db)
            if row[3]:
                raise TrialBudgetBlocked("Trial is held")
            db.execute("UPDATE trial SET enabled=1 WHERE id=1 AND enabled=0")
            db.commit()

    def reserve(self, item: BudgetReservation) -> None:
        item.validate()
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = self._check(db)
                if (not row[2] or row[3] or item.price_version != row[1]
                        or db.execute("SELECT 1 FROM requests WHERE state IN ('CLAIMED','UNKNOWN') "
                                      "LIMIT 1").fetchone()):
                    raise TrialBudgetBlocked("Trial disabled, held or price version differs")
                if db.execute("SELECT 1 FROM requests WHERE request_id=?",
                              (item.request_id,)).fetchone():
                    raise TrialBudgetBlocked("Request identity was already used")
                spent = db.execute("SELECT COALESCE(SUM(reserved_micro),0) FROM requests").fetchone()[0]
                if spent + item.reserved_micro > row[4] - row[5]:
                    raise TrialBudgetBlocked("Combined Count and Generation budget exhausted")
                now = int(time.time())
                db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,?,?)",
                           (item.request_id, item.operation, item.campaign_id,
                            item.model, item.payload_sha256, item.estimated_micro,
                            item.reserved_micro, item.price_version, "RESERVED", now, now))
                db.commit()
            except (sqlite3.Error, TrialBudgetBlocked):
                db.rollback()
                raise

    def claim(self, request_id: str, operation: str, payload_sha256: str,
              *, campaign_id: str, model: str,
              cost_limit_micro: int | None = None) -> None:
        """Burn one matching claim before credential access or transport."""
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                trial = self._check(db)
                item = db.execute("SELECT operation,campaign_id,model,payload_sha256,"
                                  "reserved_micro,state FROM requests WHERE request_id=?",
                                  (request_id,)).fetchone()
                if (not trial[2] or trial[3] or item is None
                        or item[:4] != (operation, campaign_id, model, payload_sha256)
                        or (cost_limit_micro is not None and item[4] != cost_limit_micro)
                        or item[5] != "RESERVED"
                        or db.execute("SELECT 1 FROM requests WHERE state IN ('CLAIMED','UNKNOWN') "
                                      "LIMIT 1").fetchone()):
                    raise TrialBudgetBlocked("Trial claim missing, mismatched or held")
                db.execute("UPDATE requests SET state='CLAIMED',updated_at=? WHERE request_id=?",
                           (int(time.time()), request_id))
                db.commit()
            except (sqlite3.Error, TrialBudgetBlocked):
                db.rollback()
                raise

    def finish(self, request_id: str, *, actual_micro: int | None,
               usage_json: str | None, billing_source: str | None,
               latency_ms: int | None = None) -> None:
        """Only authoritative billing evidence can settle; otherwise hold."""
        valid = (type(actual_micro) is int and actual_micro >= 0
                 and isinstance(usage_json, str) and 1 <= len(usage_json) <= 4096
                 and isinstance(billing_source, str) and 1 <= len(billing_source) <= 100)
        if latency_ms is not None and (type(latency_ms) is not int or latency_ms < 0):
            raise TrialBudgetBlocked("Trial latency is invalid")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                row = db.execute("SELECT state,reserved_micro FROM requests WHERE request_id=?",
                                 (request_id,)).fetchone()
                if row is None or row[0] != "CLAIMED":
                    raise TrialBudgetBlocked("Only one claimed request may be finalized")
                state = "SETTLED" if valid and actual_micro <= row[1] else "UNKNOWN"
                db.execute("UPDATE requests SET state=?,actual_micro=?,usage_json=?,billing_source=?,"
                           "latency_ms=?,updated_at=? "
                           "WHERE request_id=?",
                           (state, actual_micro if valid else None,
                            usage_json if valid else None,
                            billing_source if valid else None,
                            latency_ms, int(time.time()), request_id))
                if state == "UNKNOWN":
                    db.execute("UPDATE trial SET held=1 WHERE id=1")
                db.commit()
            except (sqlite3.Error, TrialBudgetBlocked):
                db.rollback()
                raise

    def snapshot(self) -> dict:
        with closing(self._connect()) as db:
            trial = self._check(db)
            reserved, actual = db.execute(
                "SELECT COALESCE(SUM(reserved_micro),0),COALESCE(SUM(actual_micro),0) "
                "FROM requests").fetchone()
            return {"trial_id": trial[0], "price_version": trial[1],
                    "enabled": bool(trial[2]), "held": bool(trial[3]),
                    "limit_micro": trial[4], "buffer_micro": trial[5],
                    "reserved_micro": reserved, "known_actual_micro": actual}


def windows_trial_budget() -> TrialBudgetController:
    """Open only the fixed Host-local store; missing store blocks real calls."""
    if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
        raise TrialBudgetBlocked("Windows local Trial budget unavailable")
    path = Path(os.environ["LOCALAPPDATA"]) / "SupplyChainCopilot" / "trial_budget.sqlite3"
    return TrialBudgetController(path)
