"""Durable local one-allowance reservation ledger. No provider dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import re
import sqlite3
import time

from src.ai_copilot.approval import ApprovalStore, ApprovalBlocked, OwnerVerifier, POLICY_VERSION, verify_request
from src.ai_copilot.provider import ProviderRequest, build_request
from src.ai_brief.validation import ValidatedBrief


class LedgerBlocked(RuntimeError):
    pass


CAMPAIGN_ID = "v1.2-first-paid-acceptance"


@dataclass(frozen=True)
class CostPolicy:
    """Explicit future acceptance settings. None means paid execution is blocked."""

    model_snapshot: str | None = None
    max_cost_usd: str | None = None
    pricing_basis: str | None = None
    estimated_cost_usd: str | None = None

    def validate(self, request: ProviderRequest) -> str:
        if not self.model_snapshot or self.model_snapshot != request.model_snapshot:
            raise LedgerBlocked("Approved model snapshot is unset or mismatched")
        if not self.pricing_basis or not self.pricing_basis.strip():
            raise LedgerBlocked("Pricing basis is unset")
        try:
            cost = Decimal(self.max_cost_usd) if self.max_cost_usd is not None else None
        except (InvalidOperation, TypeError):
            cost = None
        if cost is None or not cost.is_finite() or cost <= 0:
            raise LedgerBlocked("Approved cost ceiling is unset or invalid")
        return str(cost)

    def estimate(self, request: ProviderRequest) -> str:
        ceiling = Decimal(self.validate(request))
        try:
            estimate = Decimal(self.estimated_cost_usd) if self.estimated_cost_usd is not None else None
        except (InvalidOperation, TypeError):
            estimate = None
        if estimate is None or not estimate.is_finite() or estimate < 0 or estimate > ceiling:
            raise LedgerBlocked("Explicit estimated cost is missing or above the approved ceiling")
        return str(estimate)


@dataclass(frozen=True)
class ProviderAccounting:
    """Sanitized provider metadata, never request/response bodies or raw errors."""
    usage: dict[str, int] | None = None
    provider_request_id: str | None = None
    provider_charge_usd: str | None = None
    note: str = ""

    @staticmethod
    def safe_note(note: str) -> bool:
        return (isinstance(note, str) and len(note) <= 500 and '\n' not in note
                and not re.search(r'(?i)(api[_ -]?key|password|secret|sk-[a-z0-9]|https?://|/tmp/|/workspace/|@)', note))

    def checked(self) -> tuple[str | None, str | None, str | None, str]:
        if not self.safe_note(self.note):
            raise LedgerBlocked("Sanitized reconciliation note required")
        if self.provider_request_id is not None and (not isinstance(self.provider_request_id, str)
                or len(self.provider_request_id) > 128 or not self.provider_request_id.isascii()):
            raise LedgerBlocked("Provider request ID invalid")
        if self.usage is not None and (not isinstance(self.usage, dict) or not self.usage
                or not set(self.usage) <= {"input_tokens", "output_tokens", "total_tokens"}
                or any(type(v) is not int or v < 0 or v > 10**9 for v in self.usage.values())):
            raise LedgerBlocked("Provider usage must be sanitized token counts")
        charge = None
        if self.provider_charge_usd is not None:
            try:
                amount = Decimal(self.provider_charge_usd)
            except (InvalidOperation, TypeError) as exc:
                raise LedgerBlocked("Provider charge invalid") from exc
            if not amount.is_finite() or amount < 0:
                raise LedgerBlocked("Provider charge invalid")
            charge = str(amount)
        return (json.dumps(self.usage, sort_keys=True) if self.usage is not None else None,
                self.provider_request_id, charge, self.note)


@dataclass(frozen=True)
class LedgerEntry:
    campaign: str
    state: str
    request_digest: str
    approval_reference: str
    model_snapshot: str
    max_cost_usd: str
    pricing_basis: str
    allowance: int
    reserved_at: int
    updated_at: int
    estimated_cost_usd: str
    provider_charge_usd: str | None
    provider_request_id: str | None
    usage_json: str | None

    @property
    def over_ceiling(self) -> bool:
        return (self.provider_charge_usd is not None
                and Decimal(self.provider_charge_usd) > Decimal(self.max_cost_usd))


class ExecutionLedger:
    """SQLite BEGIN IMMEDIATE serializes reservations across local processes."""

    def __init__(self, db_path: str):
        self.approvals = ApprovalStore(db_path)
        self.db_path = db_path
        with self.approvals.connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='execution_ledger'").fetchone():
                raise LedgerBlocked("Ledger schema is missing; explicit provisioning required")

    @staticmethod
    def provision(db_path: str, verifier: OwnerVerifier) -> None:
        ApprovalStore.provision(db_path, verifier)
        with ApprovalStore(db_path).connect() as db:
            db.execute("""CREATE TABLE execution_ledger (
                campaign TEXT PRIMARY KEY, state TEXT NOT NULL,
                request_digest TEXT NOT NULL, approval_reference TEXT NOT NULL UNIQUE,
                model_snapshot TEXT NOT NULL, max_cost_usd TEXT NOT NULL,
                pricing_basis TEXT NOT NULL, allowance INTEGER NOT NULL CHECK(allowance=1),
                reserved_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
                estimated_cost_usd TEXT NOT NULL, provider_charge_usd TEXT,
                provider_request_id TEXT, usage_json TEXT)""")
            db.execute("""CREATE TABLE ledger_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, campaign TEXT NOT NULL,
                event_time INTEGER NOT NULL, event_type TEXT NOT NULL,
                from_state TEXT, to_state TEXT, usage_json TEXT,
                provider_request_id TEXT, provider_charge_usd TEXT, note TEXT NOT NULL)""")

    def get(self, campaign: str = CAMPAIGN_ID) -> LedgerEntry | None:
        with self.approvals.connect() as db:
            row = db.execute("SELECT * FROM execution_ledger WHERE campaign=?", (campaign,)).fetchone()
        return LedgerEntry(*row) if row else None

    def status(self, campaign: str = CAMPAIGN_ID) -> str:
        entry = self.get(campaign)
        return entry.state if entry else "NOT_STARTED"

    def reserve(self, review: ValidatedBrief, request: ProviderRequest, approval_reference: str, policy: CostPolicy,
                *, campaign: str = CAMPAIGN_ID, now: int | None = None) -> LedgerEntry:
        """Consume approval and reserve the one campaign allowance in one transaction."""
        if type(review) is not ValidatedBrief or build_request(
                review, model_snapshot=request.model_snapshot,
                max_output_tokens=request.max_output_tokens,
                timeout_seconds=request.timeout_seconds) != request:
            raise LedgerBlocked("Live validated Brief and exact request required")
        verify_request(request)
        cost = policy.validate(request)
        estimate = policy.estimate(request)
        current = int(time.time()) if now is None else now
        if campaign != CAMPAIGN_ID or not approval_reference:
            raise LedgerBlocked("Fixed campaign and approval reference required")
        with self.approvals.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM owner_approvals WHERE reference=?", (approval_reference,)).fetchone()
                if (row is None or row[1] != request.request_digest or row[2] > current or row[3] <= current
                    or row[4] != POLICY_VERSION or row[5] is not None or row[6] is not None
                    or row[7] != cost or row[8] != policy.pricing_basis):
                    raise LedgerBlocked("Approval missing, stale, revoked, reused or mismatched")
                if db.execute("SELECT 1 FROM execution_ledger WHERE campaign=?", (campaign,)).fetchone():
                    raise LedgerBlocked("Execution allowance already reserved")
                db.execute("INSERT INTO execution_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (campaign, "NOT_STARTED", request.request_digest, approval_reference,
                            request.model_snapshot, cost, policy.pricing_basis, 1, current, current,
                            estimate, None, None, None))
                if db.execute("UPDATE owner_approvals SET consumed_at=? WHERE reference=? AND consumed_at IS NULL",
                              (current, approval_reference)).rowcount != 1:
                    raise LedgerBlocked("Approval already consumed")
                db.execute("INSERT INTO ledger_events(campaign,event_time,event_type,from_state,to_state,note) VALUES (?,?,?,?,?,?)",
                           (campaign, current, "RESERVED", None, "NOT_STARTED", "Explicit cost estimate and ceiling reserved"))
                db.commit()
            except (sqlite3.Error, LedgerBlocked):
                db.rollback()
                raise
        entry = self.get(campaign)
        assert entry is not None
        return entry

    def transition(self, campaign: str, expected: str, target: str, *, now: int | None = None,
                   accounting: ProviderAccounting | None = None) -> LedgerEntry:
        allowed = {("NOT_STARTED", "IN_PROGRESS"), ("IN_PROGRESS", "SUCCEEDED"),
                   ("IN_PROGRESS", "FAILED"), ("IN_PROGRESS", "UNKNOWN")}
        if (expected, target) not in allowed:
            raise LedgerBlocked("Illegal ledger transition")
        if target in {"SUCCEEDED", "FAILED"} and accounting is None:
            raise LedgerBlocked("Terminal outcome requires durable accounting evidence")
        usage, request_id, charge, note = accounting.checked() if accounting else (None, None, None, "")
        if target == "SUCCEEDED" and (usage is None or charge is None):
            raise LedgerBlocked("Success requires usage and observed charge")
        current = int(time.time()) if now is None else now
        with self.approvals.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                changed = db.execute("""UPDATE execution_ledger SET state=?,updated_at=?,
                    usage_json=COALESCE(?,usage_json),provider_request_id=COALESCE(?,provider_request_id),
                    provider_charge_usd=COALESCE(?,provider_charge_usd) WHERE campaign=? AND state=?""",
                                     (target, current, usage, request_id, charge, campaign, expected)).rowcount
                if changed != 1:
                    raise LedgerBlocked("Ledger state changed or reservation missing")
                db.execute("""INSERT INTO ledger_events(campaign,event_time,event_type,from_state,to_state,
                    usage_json,provider_request_id,provider_charge_usd,note) VALUES (?,?,?,?,?,?,?,?,?)""",
                           (campaign, current, "TRANSITION", expected, target, usage, request_id, charge, note))
                db.commit()
            except (sqlite3.Error, LedgerBlocked):
                db.rollback()
                raise
        entry = self.get(campaign)
        assert entry is not None
        return entry

    def reconcile(self, campaign: str, owner_password: str, note: str,
                  accounting: ProviderAccounting | None = None, *, now: int | None = None) -> LedgerEntry:
        """Owner-attested manual reconciliation; never restores an allowance."""
        if not self.approvals._verifier.authenticate(owner_password):
            raise LedgerBlocked("Owner authentication required for reconciliation")
        if not note or not ProviderAccounting.safe_note(note):
            raise LedgerBlocked("Sanitized reconciliation note required")
        usage, request_id, charge, _ = accounting.checked() if accounting else (None, None, None, "")
        current = int(time.time()) if now is None else now
        with self.approvals.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT state FROM execution_ledger WHERE campaign=?", (campaign,)).fetchone()
                if row is None or row[0] not in {"IN_PROGRESS", "UNKNOWN"}:
                    raise LedgerBlocked("Only ambiguous work can be reconciled")
                prior = row[0]
                db.execute("""UPDATE execution_ledger SET state='UNKNOWN',updated_at=?,
                    usage_json=COALESCE(?,usage_json),provider_request_id=COALESCE(?,provider_request_id),
                    provider_charge_usd=COALESCE(?,provider_charge_usd) WHERE campaign=?""",
                           (current, usage, request_id, charge, campaign))
                db.execute("""INSERT INTO ledger_events(campaign,event_time,event_type,from_state,to_state,
                    usage_json,provider_request_id,provider_charge_usd,note) VALUES (?,?,?,?,?,?,?,?,?)""",
                           (campaign, current, "MANUAL_RECONCILIATION", prior, "UNKNOWN",
                            usage, request_id, charge, note))
                db.commit()
            except (sqlite3.Error, LedgerBlocked):
                db.rollback()
                raise
        return self.get(campaign)

    def events(self, campaign: str = CAMPAIGN_ID) -> list[tuple]:
        with self.approvals.connect() as db:
            return db.execute("SELECT event_time,event_type,from_state,to_state,usage_json,provider_request_id,provider_charge_usd,note FROM ledger_events WHERE campaign=? ORDER BY event_id", (campaign,)).fetchall()
