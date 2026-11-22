"""Offline-only, separately provisioned P5 evaluation campaign ledger.

There is deliberately no paid campaign mode and no provider dispatch API.
The existing P3 one-allowance database and service are untouched.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import secrets
import sqlite3
import time

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.approval import ApprovalStore, OwnerVerifier, verify_request
from src.ai_copilot.ledger import ProviderAccounting
from src.ai_copilot.provider import ProviderRequest, build_request


CASE_IDS = ("EV-01", "EV-02", "EV-03", "EV-04", "EV-05", "EV-06", "EV-07", "EV-08-LR")
POLICY_VERSION = "p5-eight-call-offline-1"


class CampaignBlocked(RuntimeError):
    """A campaign safety or authorization condition failed."""


@dataclass(frozen=True)
class CaseSlot:
    case_id: str
    case_version: str
    fixture_id: str
    scenario: str
    max_records: int
    comparison: bool


@dataclass(frozen=True)
class OfflineCampaignPlan:
    """Explicit offline test policy. Money values are test ceilings, not paid authority."""
    campaign_id: str
    corpus_version: str
    slots: tuple[CaseSlot, ...]
    model_id: str
    model_policy: str
    model_snapshot: str
    max_output_tokens: int
    timeout_seconds: float
    pricing_basis: str
    per_slot_ceiling_micro: int
    total_ceiling_micro: int

    def payload(self) -> dict:
        value = asdict(self)
        value["slots"] = [asdict(slot) for slot in self.slots]
        return value

    def digest(self) -> str:
        return hashlib.sha256(canonical_bytes(self.payload())).hexdigest()

    def validate(self) -> None:
        if (type(self.campaign_id) is not str or not self.campaign_id.startswith("offline-")
                or len(self.campaign_id) > 100 or not self.corpus_version
                or type(self.slots) is not tuple or len(self.slots) != 8
                or tuple(slot.case_id for slot in self.slots) != CASE_IDS
                or any(type(s) is not CaseSlot or not s.case_version or
                       s.fixture_id != ("p5_low_risk_v1" if s.case_id == "EV-08-LR" else "v1_1")
                       or not s.scenario or type(s.max_records) is not int
                       or not 1 <= s.max_records <= 20 or type(s.comparison) is not bool
                       for s in self.slots)
                or self.model_id != "gpt-6-luna"
                or self.model_policy != "UNVERIFIED_OFFLINE_TEST"
                or not self.pricing_basis or len(self.pricing_basis) > 120
                or type(self.per_slot_ceiling_micro) is not int
                or type(self.total_ceiling_micro) is not int
                or self.per_slot_ceiling_micro <= 0
                or self.total_ceiling_micro <= 0
                or self.total_ceiling_micro > 8 * self.per_slot_ceiling_micro):
            raise CampaignBlocked("Explicit eight-slot offline campaign policy required")
        # Reuse the existing bounded request builder, including model/timeout limits.
        if (not self.model_snapshot or type(self.max_output_tokens) is not int
                or not 1 <= self.max_output_tokens <= 2500
                or type(self.timeout_seconds) not in (int, float)
                or not 0 < self.timeout_seconds <= 60):
            raise CampaignBlocked("Request configuration is unset or outside P2 bounds")


def _binding(review: ValidatedBrief, request: ProviderRequest, slot: CaseSlot,
             plan: OfflineCampaignPlan) -> str:
    """Rebuild from a live validator-issued Brief; never trust supplied digests."""
    if type(review) is not ValidatedBrief or type(request) is not ProviderRequest:
        raise CampaignBlocked("Live validated Brief and exact request required")
    brief = review.verify()
    rebuilt = build_request(review, model_snapshot=plan.model_snapshot,
                            max_output_tokens=plan.max_output_tokens,
                            timeout_seconds=plan.timeout_seconds)
    verify_request(request)
    if rebuilt != request:
        raise CampaignBlocked("Brief, privacy projection or request changed")
    # These fields come from the registered validator draft, not from UI labels.
    draft = review._draft
    bundle = draft._bundle
    if (bundle._harness._fixture_id != slot.fixture_id
            or brief["run_context"]["Scenario"] != slot.scenario
            or draft.max_records != slot.max_records
            or bool(brief["run_context"]["Comparison_ID"]) != slot.comparison):
        raise CampaignBlocked("Trusted case selection does not match immutable slot")
    return hashlib.sha256(canonical_bytes({
        "campaign_id": plan.campaign_id, "manifest_digest": plan.digest(),
        "case_id": slot.case_id, "case_version": slot.case_version,
        "brief_digest": request.brief_digest,
        "projection_digest": request.provider_brief_digest,
        "request_digest": request.request_digest,
        "model_snapshot": request.model_snapshot,
        "schema_version": request.schema_version,
        "instructions_version": request.instructions_version,
        "privacy_version": request.privacy_version,
        "max_output_tokens": request.max_output_tokens,
        "timeout_seconds": request.timeout_seconds,
    })).hexdigest()


def _micro(charge: str | None) -> int | None:
    if charge is None:
        return None
    try:
        amount = Decimal(charge) * 1000000
    except (InvalidOperation, TypeError) as exc:
        raise CampaignBlocked("Charge is invalid") from exc
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise CampaignBlocked("Charge needs exact nonnegative micro-USD precision")
    return int(amount)


class EightCallCampaign:
    """Local SQLite service for offline synthetic test doubles only."""

    def __init__(self, db_path: str):
        self.approvals = ApprovalStore(db_path)
        if self.approvals._verifier != OwnerVerifier.from_environment():
            raise CampaignBlocked("Trusted local Owner verifier differs from provisioned store")
        with self.approvals.connect() as db:
            self._check(db)

    @staticmethod
    def provision_offline(db_path: str, plan: OfflineCampaignPlan, owner_password: str,
                          *, now: int | None = None) -> None:
        """Explicit new-file provisioning. Cannot create an executable paid campaign."""
        plan.validate()
        verifier = OwnerVerifier.from_environment()
        if not verifier.authenticate(owner_password):
            raise CampaignBlocked("Separate Owner authentication required")
        ApprovalStore.provision(db_path, verifier)
        current = int(time.time()) if now is None else now
        store = ApprovalStore(db_path)
        with store.connect() as db:
            try:
                db.execute("PRAGMA foreign_keys=ON")
                db.executescript("""BEGIN IMMEDIATE;
                    CREATE TABLE campaign (
                      campaign_id TEXT PRIMARY KEY, manifest_digest TEXT NOT NULL,
                      plan_json TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode='OFFLINE_TEST'),
                      status TEXT NOT NULL CHECK(status IN ('OPEN','HELD','CLOSED')),
                      reserved_micro INTEGER NOT NULL DEFAULT 0 CHECK(reserved_micro>=0),
                      owner_approved_at INTEGER NOT NULL);
                    CREATE TABLE slots (
                      campaign_id TEXT NOT NULL REFERENCES campaign(campaign_id),
                      case_id TEXT NOT NULL, template_json TEXT NOT NULL,
                      PRIMARY KEY(campaign_id,case_id));
                    CREATE TABLE slot_approvals (
                      reference TEXT PRIMARY KEY, campaign_id TEXT NOT NULL,
                      case_id TEXT NOT NULL, manifest_digest TEXT NOT NULL,
                      binding_digest TEXT NOT NULL, request_digest TEXT NOT NULL,
                      estimated_micro INTEGER NOT NULL, ceiling_micro INTEGER NOT NULL,
                      approved_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                      revoked_at INTEGER, consumed_at INTEGER,
                      policy_version TEXT NOT NULL,
                      FOREIGN KEY(campaign_id,case_id) REFERENCES slots(campaign_id,case_id));
                    CREATE TABLE reservations (
                      campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
                      approval_reference TEXT NOT NULL UNIQUE,
                      binding_digest TEXT NOT NULL, brief_digest TEXT NOT NULL,
                      projection_digest TEXT NOT NULL, request_digest TEXT NOT NULL,
                      model_snapshot TEXT NOT NULL, schema_version TEXT NOT NULL,
                      instructions_version TEXT NOT NULL, privacy_version TEXT NOT NULL,
                      max_output_tokens INTEGER NOT NULL, timeout_seconds REAL NOT NULL,
                      estimated_micro INTEGER NOT NULL, ceiling_micro INTEGER NOT NULL,
                      state TEXT NOT NULL CHECK(state IN
                        ('NOT_STARTED','IN_PROGRESS','SUCCEEDED','FAILED','UNKNOWN')),
                      reserved_at INTEGER NOT NULL, dispatch_started_at INTEGER,
                      attempt_id TEXT UNIQUE, usage_json TEXT, charge_micro INTEGER,
                      provider_request_id TEXT, updated_at INTEGER NOT NULL,
                      PRIMARY KEY(campaign_id,case_id),
                      FOREIGN KEY(campaign_id,case_id) REFERENCES slots(campaign_id,case_id),
                      FOREIGN KEY(approval_reference) REFERENCES slot_approvals(reference));
                    CREATE TABLE campaign_events (
                      event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      campaign_id TEXT NOT NULL, case_id TEXT,
                      event_type TEXT NOT NULL, event_time INTEGER NOT NULL,
                      actor TEXT NOT NULL, note TEXT NOT NULL,
                      request_digest TEXT, approval_reference TEXT,
                      usage_json TEXT, charge_micro INTEGER,
                      FOREIGN KEY(campaign_id) REFERENCES campaign(campaign_id));
                    CREATE TRIGGER events_no_update BEFORE UPDATE ON campaign_events
                      BEGIN SELECT RAISE(ABORT,'append-only events'); END;
                    CREATE TRIGGER events_no_delete BEFORE DELETE ON campaign_events
                      BEGIN SELECT RAISE(ABORT,'append-only events'); END;
                """)
                db.execute("INSERT INTO campaign VALUES (?,?,?,?,?,?,?)",
                           (plan.campaign_id, plan.digest(), canonical_bytes(plan.payload()).decode(),
                            "OFFLINE_TEST", "OPEN", 0, current))
                db.executemany("INSERT INTO slots VALUES (?,?,?)",
                               [(plan.campaign_id, s.case_id, canonical_bytes(asdict(s)).decode())
                                for s in plan.slots])
                db.execute("INSERT INTO campaign_events(campaign_id,event_type,event_time,actor,note) VALUES (?,?,?,?,?)",
                           (plan.campaign_id, "PROVISIONED", current, "OWNER", "Offline campaign and eight slots"))
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise

    @staticmethod
    def _event(db: sqlite3.Connection, plan: OfflineCampaignPlan, case_id: str | None,
               kind: str, current: int, *, actor: str = "SERVICE", note: str = "",
               digest: str | None = None, reference: str | None = None,
               usage: str | None = None, charge: int | None = None) -> None:
        db.execute("""INSERT INTO campaign_events(campaign_id,case_id,event_type,event_time,actor,note,
                    request_digest,approval_reference,usage_json,charge_micro) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (plan.campaign_id, case_id, kind, current, actor, note, digest, reference, usage, charge))

    @staticmethod
    def _check(db: sqlite3.Connection) -> OfflineCampaignPlan:
        try:
            if db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                raise CampaignBlocked("Campaign database corrupt")
            row = db.execute("SELECT campaign_id,manifest_digest,plan_json,mode,status,reserved_micro FROM campaign").fetchall()
            if len(row) != 1 or row[0][3] != "OFFLINE_TEST":
                raise CampaignBlocked("Campaign identity or mode invalid")
            raw = json.loads(row[0][2])
            plan = OfflineCampaignPlan(slots=tuple(CaseSlot(**s) for s in raw.pop("slots")), **raw)
            plan.validate()
            if row[0][0] != plan.campaign_id or row[0][1] != plan.digest():
                raise CampaignBlocked("Campaign manifest changed")
            slots = db.execute("SELECT case_id,template_json FROM slots WHERE campaign_id=? ORDER BY case_id",
                               (plan.campaign_id,)).fetchall()
            if slots != [(s.case_id, canonical_bytes(asdict(s)).decode()) for s in plan.slots]:
                raise CampaignBlocked("Campaign slot roster changed")
            reservations = db.execute("SELECT case_id,ceiling_micro,approval_reference,binding_digest,request_digest FROM reservations WHERE campaign_id=?",
                                      (plan.campaign_id,)).fetchall()
            if (row[0][5] != sum(r[1] for r in reservations)
                    or row[0][5] > plan.total_ceiling_micro
                    or any(r[0] not in CASE_IDS for r in reservations)
                    or any(db.execute("""SELECT 1 FROM slot_approvals WHERE reference=?
                            AND campaign_id=? AND case_id=? AND manifest_digest=?
                            AND binding_digest=? AND request_digest=? AND consumed_at IS NOT NULL
                            AND ceiling_micro=?""",
                                      (r[2], plan.campaign_id, r[0], plan.digest(), r[3], r[4], r[1])).fetchone() is None
                           for r in reservations)):
                raise CampaignBlocked("Campaign reservation accounting inconsistent")
            return plan
        except (sqlite3.Error, KeyError, TypeError, ValueError) as exc:
            raise CampaignBlocked("Campaign database missing, corrupt or inconsistent") from exc

    def _connect(self) -> sqlite3.Connection:
        try:
            db = self.approvals.connect()
            db.execute("PRAGMA foreign_keys=ON")
            return db
        except sqlite3.Error as exc:
            raise CampaignBlocked("Campaign store unavailable") from exc

    def plan(self) -> OfflineCampaignPlan:
        with self._connect() as db:
            return self._check(db)

    def _slot(self, plan: OfflineCampaignPlan, case_id: str) -> CaseSlot:
        for slot in plan.slots:
            if slot.case_id == case_id:
                return slot
        raise CampaignBlocked("Unknown case slot")

    def approve_slot(self, case_id: str, review: ValidatedBrief, request: ProviderRequest,
                     owner_password: str, *, estimated_micro: int,
                     ttl_seconds: int = 300, now: int | None = None) -> str:
        plan = self.plan()
        slot = self._slot(plan, case_id)
        binding = _binding(review, request, slot, plan)
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Separate Owner authentication required")
        if (type(estimated_micro) is not int or not 0 <= estimated_micro <= plan.per_slot_ceiling_micro
                or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 900):
            raise CampaignBlocked("Explicit estimate or approval lifetime invalid")
        current = int(time.time()) if now is None else now
        reference = secrets.token_hex(24)
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                if (db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"
                        or db.execute("SELECT 1 FROM reservations WHERE case_id=?", (case_id,)).fetchone()):
                    raise CampaignBlocked("Slot or campaign is unavailable")
                db.execute("INSERT INTO slot_approvals VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?)",
                           (reference, plan.campaign_id, case_id, plan.digest(), binding,
                            request.request_digest, estimated_micro, plan.per_slot_ceiling_micro,
                            current, current + ttl_seconds, POLICY_VERSION))
                self._event(db, plan, case_id, "SLOT_APPROVED", current, actor="OWNER",
                            digest=request.request_digest, reference=reference)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return reference

    def revoke_approval(self, reference: str, owner_password: str, *, now: int | None = None) -> None:
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner authentication required")
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                row = db.execute("SELECT case_id FROM slot_approvals WHERE reference=? AND consumed_at IS NULL AND revoked_at IS NULL",
                                 (reference,)).fetchone()
                if row is None:
                    raise CampaignBlocked("Approval unavailable")
                db.execute("UPDATE slot_approvals SET revoked_at=? WHERE reference=?", (current, reference))
                self._event(db, plan, row[0], "APPROVAL_REVOKED", current, actor="OWNER", reference=reference)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise

    def reserve_offline(self, case_id: str, review: ValidatedBrief, request: ProviderRequest,
                        reference: str, *, now: int | None = None) -> dict:
        plan = self.plan()
        slot = self._slot(plan, case_id)
        binding = _binding(review, request, slot, plan)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                approval = db.execute("SELECT * FROM slot_approvals WHERE reference=?", (reference,)).fetchone()
                if (approval is None or approval[1:6] != (plan.campaign_id, case_id, plan.digest(),
                                                         binding, request.request_digest)
                        or approval[8] > current or approval[9] <= current or approval[10] is not None
                        or approval[11] is not None or approval[12] != POLICY_VERSION
                        or approval[7] != plan.per_slot_ceiling_micro):
                    raise CampaignBlocked("Approval missing, stale, revoked, reused or mismatched")
                if (db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"
                        or db.execute("SELECT 1 FROM reservations WHERE state IN ('IN_PROGRESS','UNKNOWN') LIMIT 1").fetchone()):
                    raise CampaignBlocked("Campaign held")
                changed = db.execute("""UPDATE campaign SET reserved_micro=reserved_micro+?
                    WHERE campaign_id=? AND reserved_micro+?<=?""",
                    (approval[7], plan.campaign_id, approval[7], plan.total_ceiling_micro)).rowcount
                if changed != 1:
                    raise CampaignBlocked("Aggregate ceiling exceeded")
                db.execute("""INSERT INTO reservations VALUES
                    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (plan.campaign_id, case_id, reference, binding, request.brief_digest,
                     request.provider_brief_digest, request.request_digest,
                     request.model_snapshot, request.schema_version, request.instructions_version,
                     request.privacy_version, request.max_output_tokens, request.timeout_seconds,
                     approval[6], approval[7], "NOT_STARTED", current, None, None, None,
                     None, None, current))
                if db.execute("UPDATE slot_approvals SET consumed_at=? WHERE reference=? AND consumed_at IS NULL",
                              (current, reference)).rowcount != 1:
                    raise CampaignBlocked("Approval already consumed")
                self._event(db, plan, case_id, "DIGEST_VERIFIED", current,
                            digest=request.request_digest, reference=reference)
                self._event(db, plan, case_id, "RESERVED", current,
                            digest=request.request_digest, reference=reference)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return self.reservation(case_id)

    def reservation(self, case_id: str) -> dict | None:
        with self._connect() as db:
            plan = self._check(db)
            self._slot(plan, case_id)
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM reservations WHERE campaign_id=? AND case_id=?",
                             (plan.campaign_id, case_id)).fetchone()
            return dict(row) if row else None

    def start_offline_attempt(self, case_id: str, review: ValidatedBrief,
                              request: ProviderRequest, *, now: int | None = None) -> dict:
        """Record only a synthetic test-double attempt; never submit a request."""
        plan = self.plan()
        binding = _binding(review, request, self._slot(plan, case_id), plan)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                if db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN":
                    raise CampaignBlocked("Campaign held")
                changed = db.execute("""UPDATE reservations SET state='IN_PROGRESS',
                    dispatch_started_at=?,attempt_id=?,updated_at=? WHERE campaign_id=?
                    AND case_id=? AND state='NOT_STARTED' AND binding_digest=?""",
                    (current, secrets.token_hex(24), current, plan.campaign_id, case_id, binding)).rowcount
                if changed != 1:
                    raise CampaignBlocked("Reserved slot missing, stale or already attempted")
                self._event(db, plan, case_id, "OFFLINE_ATTEMPT_STARTED", current,
                            digest=request.request_digest)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return self.reservation(case_id)

    def record_offline_outcome(self, case_id: str, target: str,
                               accounting: ProviderAccounting | None = None,
                               *, now: int | None = None) -> dict:
        if target not in {"SUCCEEDED", "FAILED", "UNKNOWN"}:
            raise CampaignBlocked("Invalid offline outcome")
        usage, provider_id, charge, note = accounting.checked() if accounting else (None, None, None, "")
        charge_micro = _micro(charge)
        if target in {"SUCCEEDED", "FAILED"} and (usage is None or charge_micro is None):
            raise CampaignBlocked("Definitive outcome requires observed usage and charge")
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                self._slot(plan, case_id)
                row = db.execute("SELECT state,ceiling_micro FROM reservations WHERE case_id=?",
                                 (case_id,)).fetchone()
                if row is None or row[0] != "IN_PROGRESS":
                    raise CampaignBlocked("Only an attempted slot can receive an outcome")
                db.execute("""UPDATE reservations SET state=?,usage_json=COALESCE(?,usage_json),
                    charge_micro=COALESCE(?,charge_micro),provider_request_id=COALESCE(?,provider_request_id),
                    updated_at=? WHERE case_id=?""",
                    (target, usage, charge_micro, provider_id, current, case_id))
                observed_total = db.execute("SELECT COALESCE(SUM(charge_micro),0) FROM reservations").fetchone()[0]
                if (target == "UNKNOWN" or (charge_micro is not None and charge_micro > row[1])
                        or observed_total > plan.total_ceiling_micro):
                    db.execute("UPDATE campaign SET status='HELD'")
                if usage is not None:
                    self._event(db, plan, case_id, "USAGE_OBSERVED", current, usage=usage)
                if charge_micro is not None:
                    self._event(db, plan, case_id, "CHARGE_OBSERVED", current, charge=charge_micro)
                self._event(db, plan, case_id, target, current, note=note,
                            usage=usage, charge=charge_micro)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return self.reservation(case_id)

    def reconcile(self, case_id: str, owner_password: str, note: str,
                  accounting: ProviderAccounting | None = None,
                  *, now: int | None = None) -> dict:
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner authentication required")
        if not note or not ProviderAccounting.safe_note(note):
            raise CampaignBlocked("Sanitized Owner attestation required")
        usage, provider_id, charge, _ = accounting.checked() if accounting else (None, None, None, "")
        charge_micro = _micro(charge)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                self._slot(plan, case_id)
                row = db.execute("SELECT state FROM reservations WHERE case_id=?", (case_id,)).fetchone()
                if row is None or row[0] not in {"NOT_STARTED", "IN_PROGRESS", "UNKNOWN"}:
                    raise CampaignBlocked("Only reserved or ambiguous work can be reconciled")
                db.execute("""UPDATE reservations SET state='UNKNOWN',usage_json=COALESCE(?,usage_json),
                    charge_micro=COALESCE(?,charge_micro),provider_request_id=COALESCE(?,provider_request_id),
                    updated_at=? WHERE case_id=?""",
                    (usage, charge_micro, provider_id, current, case_id))
                db.execute("UPDATE campaign SET status='HELD'")
                if usage is not None:
                    self._event(db, plan, case_id, "USAGE_RECONCILED", current,
                                actor="OWNER", usage=usage)
                if charge_micro is not None:
                    self._event(db, plan, case_id, "CHARGE_RECONCILED", current,
                                actor="OWNER", charge=charge_micro)
                self._event(db, plan, case_id, "MANUAL_RECONCILIATION", current,
                            actor="OWNER", note=note, usage=usage, charge=charge_micro)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return self.reservation(case_id)

    def events(self) -> list[tuple]:
        with self._connect() as db:
            plan = self._check(db)
            return db.execute("SELECT case_id,event_type,event_time,actor,note,request_digest,approval_reference,usage_json,charge_micro FROM campaign_events WHERE campaign_id=? ORDER BY event_id",
                              (plan.campaign_id,)).fetchall()

    def summary(self) -> dict:
        """Durable offline accounting; observed charges are never inferred from estimates."""
        with self._connect() as db:
            plan = self._check(db)
            status, reserved = db.execute("SELECT status,reserved_micro FROM campaign").fetchone()
            count, estimated, observed, missing = db.execute("""SELECT COUNT(*),
                COALESCE(SUM(estimated_micro),0),COALESCE(SUM(charge_micro),0),
                SUM(CASE WHEN charge_micro IS NULL THEN 1 ELSE 0 END)
                FROM reservations""").fetchone()
            return {"campaign_id": plan.campaign_id, "mode": "OFFLINE_TEST", "status": status,
                    "reserved_slots": count, "estimated_micro": estimated,
                    "reserved_micro": reserved, "observed_charge_micro": observed,
                    "missing_charge_slots": missing or 0,
                    "total_ceiling_micro": plan.total_ceiling_micro}
