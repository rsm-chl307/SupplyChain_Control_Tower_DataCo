"""Offline-only, separately provisioned P5 evaluation campaign ledger.

There is deliberately no paid campaign mode and no provider dispatch API.
The existing P3 one-allowance database and service are untouched.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
import secrets
import sqlite3
import stat
import time
from pathlib import Path

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.approval import ApprovalStore, OwnerVerifier, verify_request
from src.ai_copilot.ledger import ProviderAccounting
from src.ai_copilot.provider import (ProviderRequest, ProviderResult, build_request,
                                      luna_model_id_acceptable)
from tools.windows_api_runner.api_runner import RunnerError


CASE_IDS = ("EV-01", "EV-02", "EV-03", "EV-04", "EV-05", "EV-06", "EV-07", "EV-08-LR")
POLICY_VERSION = "p5-eight-call-offline-1"
OWNER_MOCK_POLICY = "OWNER_DECISIONS_1_TO_6_MOCK"
OWNER_PAID_POLICY = "OWNER_DECISIONS_1_TO_6_PAID"
OWNER_PER_CALL_MICRO = 20000
OWNER_TOTAL_MICRO = 160000
PAID_CORPUS_VERSION = "p5-offline-evaluation-2"
PAID_CORPUS_SHA256 = "08a34585b1cb819c82093adb4828734cb05507ea6b6cd6448efc5cc0d819ff50"
HOST_OWNER_PUBLIC_KEY_PATH = Path("/root/.config/supplychain_copilot/generation_owner_public.bin")


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
        if (type(self.campaign_id) is not str or not self.campaign_id.startswith(
                "paid-" if self.model_policy == OWNER_PAID_POLICY else "offline-")
                or len(self.campaign_id) > 100 or not self.corpus_version
                or type(self.slots) is not tuple or len(self.slots) != 8
                or tuple(slot.case_id for slot in self.slots) != CASE_IDS
                or any(type(s) is not CaseSlot or not s.case_version or
                       s.fixture_id != ("p5_low_risk_v1" if s.case_id == "EV-08-LR" else "v1_1")
                       or not s.scenario or type(s.max_records) is not int
                       or not 1 <= s.max_records <= 20 or type(s.comparison) is not bool
                       for s in self.slots)
                or self.model_id != "gpt-6-luna"
                or self.model_policy not in {"UNVERIFIED_OFFLINE_TEST", OWNER_MOCK_POLICY,
                                             OWNER_PAID_POLICY}
                or not self.pricing_basis or len(self.pricing_basis) > 120
                or type(self.per_slot_ceiling_micro) is not int
                or type(self.total_ceiling_micro) is not int
                or self.per_slot_ceiling_micro <= 0
                or self.total_ceiling_micro <= 0
                or self.total_ceiling_micro > 8 * self.per_slot_ceiling_micro):
            raise CampaignBlocked("Explicit eight-slot offline campaign policy required")
        if self.model_policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}:
            if (self.model_snapshot != "gpt-6-luna" or type(self.max_output_tokens) is not int
                    or self.max_output_tokens != 25000
                    or type(self.timeout_seconds) not in (int, float)
                    or float(self.timeout_seconds) != 180.0
                    or self.per_slot_ceiling_micro != OWNER_PER_CALL_MICRO
                    or self.total_ceiling_micro != OWNER_TOTAL_MICRO):
                raise CampaignBlocked("Owner mock policy limits changed")
            if self.model_policy == OWNER_PAID_POLICY:
                _verify_paid_corpus(self)
        elif (not self.model_snapshot or type(self.max_output_tokens) is not int
                or not 1 <= self.max_output_tokens <= 2500
                or type(self.timeout_seconds) not in (int, float)
                or not 0 < self.timeout_seconds <= 60):
            raise CampaignBlocked("Request configuration is unset or outside P2 bounds")


def _verify_paid_corpus(plan: OfflineCampaignPlan) -> None:
    """Paid roster must match the fixed, hash-pinned eight-case definitions."""
    if plan.corpus_version != PAID_CORPUS_VERSION:
        raise CampaignBlocked("Paid corpus version differs from Owner decision")
    path = Path(__file__).resolve().parents[2] / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 200000:
                raise CampaignBlocked("Paid case corpus is unsafe")
            raw = os.read(fd, 200001)
        finally:
            os.close(fd)
        if hashlib.sha256(raw).hexdigest() != PAID_CORPUS_SHA256:
            raise CampaignBlocked("Paid case corpus bytes changed")
        cases = json.loads(raw)["cases"]
        expected = tuple(CaseSlot(case["id"], case["case_version"], case["fixture_id"],
                                  case["scenario"], case["max_records"], case["comparison"])
                         for case in cases)
        if plan.slots != expected:
            raise CampaignBlocked("Paid case roster differs from pinned corpus")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CampaignBlocked("Paid case corpus unavailable or invalid") from exc


def _binding(review: ValidatedBrief, request: ProviderRequest, slot: CaseSlot,
             plan: OfflineCampaignPlan) -> str:
    """Rebuild from a live validator-issued Brief; never trust supplied digests."""
    if type(review) is not ValidatedBrief or type(request) is not ProviderRequest:
        raise CampaignBlocked("Live validated Brief and exact request required")
    brief = review.verify()
    rebuilt = build_request(review, model_snapshot=plan.model_snapshot,
                            max_output_tokens=plan.max_output_tokens,
                            timeout_seconds=plan.timeout_seconds,
                            execution_profile=("P5_ACCEPTANCE_MOCK" if plan.model_policy == OWNER_MOCK_POLICY
                                               else "P5_PAID_ACCEPTANCE" if plan.model_policy == OWNER_PAID_POLICY
                                               else "P2_OFFLINE"))
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
        "execution_profile": request.execution_profile,
        "max_input_tokens": request.max_input_tokens,
        "reasoning_effort": request.reasoning_effort,
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
    """Identity-bound local eight-slot store; paid mode requires a separate gate."""

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
        if plan.model_policy == OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid policy cannot use offline provisioning")
        EightCallCampaign._provision(db_path, plan, owner_password, "OFFLINE_TEST", now=now)

    @staticmethod
    def provision_paid_draft(db_path: str, plan: OfflineCampaignPlan, owner_password: str,
                             *, now: int | None = None) -> None:
        """Create a non-executable paid draft; never activate or dispatch by itself."""
        if plan.model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Exact paid policy required")
        EightCallCampaign._provision(db_path, plan, owner_password, "PAID_ACCEPTANCE", now=now)

    @staticmethod
    def _provision(db_path: str, plan: OfflineCampaignPlan, owner_password: str,
                   mode: str, *, now: int | None = None) -> None:
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
                      plan_json TEXT NOT NULL, mode TEXT NOT NULL
                        CHECK(mode IN ('OFFLINE_TEST','PAID_ACCEPTANCE')),
                      status TEXT NOT NULL CHECK(status IN ('DRAFT','OPEN','HELD','CLOSED')),
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
                    CREATE TABLE case_reviews (
                      campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
                      request_digest TEXT NOT NULL, response_digest TEXT NOT NULL,
                      score TEXT NOT NULL, verdict TEXT NOT NULL,
                      reviewer_ids_json TEXT NOT NULL,
                      adjudicator_id TEXT NOT NULL, reviewed_at INTEGER NOT NULL,
                      PRIMARY KEY(campaign_id,case_id),
                      FOREIGN KEY(campaign_id,case_id) REFERENCES reservations(campaign_id,case_id));
                    CREATE TABLE paid_authorizations (
                      reference TEXT PRIMARY KEY, campaign_id TEXT NOT NULL,
                      manifest_digest TEXT NOT NULL, authorized_at INTEGER NOT NULL,
                      expires_at INTEGER NOT NULL, revoked_at INTEGER,
                      policy_version TEXT NOT NULL,
                      FOREIGN KEY(campaign_id) REFERENCES campaign(campaign_id));
                    CREATE TABLE provider_observations (
                      campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
                      result_status TEXT NOT NULL, returned_model_id TEXT,
                      response_digest TEXT, observed_at INTEGER NOT NULL,
                      PRIMARY KEY(campaign_id,case_id),
                      FOREIGN KEY(campaign_id,case_id) REFERENCES reservations(campaign_id,case_id));
                    CREATE TABLE dispatch_claims (
                      campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
                      attempt_id TEXT NOT NULL UNIQUE, claimed_at INTEGER NOT NULL,
                      PRIMARY KEY(campaign_id,case_id),
                      FOREIGN KEY(campaign_id,case_id) REFERENCES reservations(campaign_id,case_id));
                    CREATE TABLE host_owner_claims (
                      nonce TEXT PRIMARY KEY, authorization_sha256 TEXT NOT NULL UNIQUE,
                      request_id TEXT NOT NULL UNIQUE, campaign_id TEXT NOT NULL,
                      case_id TEXT NOT NULL, run_id TEXT NOT NULL,
                      claimed_at INTEGER NOT NULL,
                      FOREIGN KEY(campaign_id,case_id) REFERENCES reservations(campaign_id,case_id));
                    CREATE TRIGGER events_no_update BEFORE UPDATE ON campaign_events
                      BEGIN SELECT RAISE(ABORT,'append-only events'); END;
                    CREATE TRIGGER events_no_delete BEFORE DELETE ON campaign_events
                      BEGIN SELECT RAISE(ABORT,'append-only events'); END;
                """)
                db.execute("INSERT INTO campaign VALUES (?,?,?,?,?,?,?)",
                           (plan.campaign_id, plan.digest(), canonical_bytes(plan.payload()).decode(),
                            mode, "DRAFT" if mode == "PAID_ACCEPTANCE" else "OPEN", 0, current))
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
            if len(row) != 1 or row[0][3] not in {"OFFLINE_TEST", "PAID_ACCEPTANCE"}:
                raise CampaignBlocked("Campaign identity or mode invalid")
            raw = json.loads(row[0][2])
            plan = OfflineCampaignPlan(slots=tuple(CaseSlot(**s) for s in raw.pop("slots")), **raw)
            plan.validate()
            if row[0][3] != ("PAID_ACCEPTANCE" if plan.model_policy == OWNER_PAID_POLICY
                             else "OFFLINE_TEST"):
                raise CampaignBlocked("Campaign mode does not match immutable policy")
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

    def authorize_paid_acceptance(self, owner_password: str, manifest_digest: str,
                                  *, ttl_seconds: int = 28800,
                                  now: int | None = None) -> str:
        """Separate, explicit Owner action; never called by application reruns."""
        if now is not None:
            raise CampaignBlocked("Paid authorization uses the service clock")
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Separate Owner authentication required")
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 28800:
            raise CampaignBlocked("Paid authorization lifetime invalid")
        current = int(time.time()) if now is None else now
        reference = secrets.token_hex(24)
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                mode, status = db.execute("SELECT mode,status FROM campaign").fetchone()
                if (mode != "PAID_ACCEPTANCE" or status != "DRAFT"
                        or plan.digest() != manifest_digest):
                    raise CampaignBlocked("Paid draft or exact manifest authorization missing")
                db.execute("INSERT INTO paid_authorizations VALUES (?,?,?,?,?,NULL,?)",
                           (reference, plan.campaign_id, manifest_digest, current,
                            current + ttl_seconds, POLICY_VERSION))
                db.execute("UPDATE campaign SET status='OPEN'")
                self._event(db, plan, None, "PAID_ACCEPTANCE_AUTHORIZED", current,
                            actor="OWNER", note="Exact campaign manifest authorized",
                            reference=reference)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return reference

    @staticmethod
    def _paid_authorized(db: sqlite3.Connection, plan: OfflineCampaignPlan,
                         current: int) -> bool:
        return db.execute("""SELECT 1 FROM paid_authorizations WHERE campaign_id=?
            AND manifest_digest=? AND authorized_at<=? AND expires_at>?
            AND revoked_at IS NULL AND policy_version=?""",
            (plan.campaign_id, plan.digest(), current, current, POLICY_VERSION)).fetchone() is not None

    def _slot(self, plan: OfflineCampaignPlan, case_id: str) -> CaseSlot:
        for slot in plan.slots:
            if slot.case_id == case_id:
                return slot
        raise CampaignBlocked("Unknown case slot")

    def approve_slot(self, case_id: str, review: ValidatedBrief, request: ProviderRequest,
                     owner_password: str, *, estimated_micro: int,
                     ttl_seconds: int = 300, now: int | None = None) -> str:
        plan = self.plan()
        if plan.model_policy == OWNER_PAID_POLICY and now is not None:
            raise CampaignBlocked("Paid approval uses the service clock")
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
                if plan.model_policy == OWNER_PAID_POLICY and not self._paid_authorized(db, plan, current):
                    raise CampaignBlocked("Separate paid acceptance authorization missing or expired")
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
        if self.plan().model_policy == OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid campaign cannot use offline reservation")
        return self._reserve(case_id, review, request, reference, now=now)

    def reserve_paid(self, case_id: str, review: ValidatedBrief, request: ProviderRequest,
                     reference: str, *, token_evidence=None,
                     now: int | None = None) -> dict:
        if self.plan().model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid reservation requires paid implementation mode")
        return self._reserve(case_id, review, request, reference,
                             token_evidence=token_evidence, now=now)

    def _reserve(self, case_id: str, review: ValidatedBrief, request: ProviderRequest,
                 reference: str, *, token_evidence=None,
                 now: int | None = None) -> dict:
        plan = self.plan()
        if plan.model_policy == OWNER_PAID_POLICY and now is not None:
            raise CampaignBlocked("Paid reservation uses the service clock")
        slot = self._slot(plan, case_id)
        binding = _binding(review, request, slot, plan)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                if plan.model_policy == OWNER_PAID_POLICY and not self._paid_authorized(db, plan, current):
                    raise CampaignBlocked("Separate paid acceptance authorization missing or expired")
                approval = db.execute("SELECT * FROM slot_approvals WHERE reference=?", (reference,)).fetchone()
                if (approval is None or approval[1:6] != (plan.campaign_id, case_id, plan.digest(),
                                                         binding, request.request_digest)
                        or approval[8] > current or approval[9] <= current or approval[10] is not None
                        or approval[11] is not None or approval[12] != POLICY_VERSION
                        or approval[7] != plan.per_slot_ceiling_micro):
                    raise CampaignBlocked("Approval missing, stale, revoked, reused or mismatched")
                if plan.model_policy == OWNER_PAID_POLICY:
                    from src.ai_copilot.token_count_evidence import require_exact_token_count
                    require_exact_token_count(case_id, request, evidence=token_evidence,
                                             review=review)
                if (db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"
                        or db.execute("SELECT 1 FROM reservations WHERE state IN ('IN_PROGRESS','UNKNOWN') LIMIT 1").fetchone()):
                    raise CampaignBlocked("Campaign held")
                if plan.model_policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}:
                    prior = CASE_IDS[:CASE_IDS.index(case_id)]
                    later = CASE_IDS[CASE_IDS.index(case_id) + 1:]
                    if (db.execute("SELECT 1 FROM reservations WHERE case_id IN ({})".format(
                            ",".join("?" for _ in later)), later).fetchone() if later else False):
                        raise CampaignBlocked("Sequential case order violated")
                    for prior_id in prior:
                        completed = db.execute("""SELECT 1 FROM reservations r JOIN case_reviews v
                            ON v.campaign_id=r.campaign_id AND v.case_id=r.case_id
                            WHERE r.case_id=? AND r.state='SUCCEEDED' AND r.usage_json IS NOT NULL
                            AND r.charge_micro IS NOT NULL""", (prior_id,)).fetchone()
                        if completed is None:
                            raise CampaignBlocked("Prior case lacks accounting and human review")
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
        if self.plan().model_policy == OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid campaign cannot use offline attempt")
        return self._start_attempt(case_id, review, request, "OFFLINE_ATTEMPT_STARTED", now=now)

    def start_paid_attempt(self, case_id: str, review: ValidatedBrief,
                           request: ProviderRequest, *, token_evidence=None,
                           now: int | None = None) -> dict:
        """Consume one paid attempt marker before future dispatch; no network here."""
        if self.plan().model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid attempt requires paid implementation mode")
        from src.ai_copilot.token_count_evidence import require_exact_token_count
        require_exact_token_count(case_id, request, evidence=token_evidence, review=review)
        return self._start_attempt(case_id, review, request, "PAID_DISPATCH_STARTED", now=now)

    def _start_attempt(self, case_id: str, review: ValidatedBrief,
                       request: ProviderRequest, event_name: str,
                       *, now: int | None = None) -> dict:
        plan = self.plan()
        if plan.model_policy == OWNER_PAID_POLICY and now is not None:
            raise CampaignBlocked("Paid attempt uses the service clock")
        binding = _binding(review, request, self._slot(plan, case_id), plan)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                if plan.model_policy == OWNER_PAID_POLICY and not self._paid_authorized(db, plan, current):
                    raise CampaignBlocked("Separate paid acceptance authorization missing or expired")
                if db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN":
                    raise CampaignBlocked("Campaign held")
                changed = db.execute("""UPDATE reservations SET state='IN_PROGRESS',
                    dispatch_started_at=?,attempt_id=?,updated_at=? WHERE campaign_id=?
                    AND case_id=? AND state='NOT_STARTED' AND binding_digest=?""",
                    (current, secrets.token_hex(24), current, plan.campaign_id, case_id, binding)).rowcount
                if changed != 1:
                    raise CampaignBlocked("Reserved slot missing, stale or already attempted")
                self._event(db, plan, case_id, event_name, current,
                            digest=request.request_digest)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        return self.reservation(case_id)

    def claim_paid_dispatch(self, case_id: str, review: ValidatedBrief,
                            request: ProviderRequest, owner_password: str,
                            *, token_evidence=None, now: int | None = None) -> str:
        """Atomically burn the one network-submit claim before any transport call."""
        if now is not None:
            raise CampaignBlocked("Paid dispatch uses the service clock")
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner gate required for paid dispatch claim")
        return self._claim_paid_dispatch(case_id, review, request,
                                         token_evidence=token_evidence,
                                         host_authorization=None, now=now)

    def claim_paid_dispatch_host_authorized(self, case_id: str,
                                            review: ValidatedBrief,
                                            request: ProviderRequest, *,
                                            request_id: str,
                                            namespace: str,
                                            host_authorization: bytes,
                                            token_evidence,
                                            archive,
                                            dispatch_id: str,
                                            now: int | None = None) -> str:
        """Claim after a pinned Host signature, without the Host password in Container.

        The proof replaces only the immediate Owner password check. Every paid
        Ledger, token, budget and one-use claim check remains in the same write
        transaction. Existing Ledger files without the new nonce table fail closed.
        """
        if now is not None:
            raise CampaignBlocked("Paid dispatch uses the service clock")
        from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive, _wire
        from src.ai_copilot.token_count_evidence import ExactTokenCount, require_exact_token_count
        from tools.windows_api_runner.generation_authorization import verify_owner_authorization
        from tools.windows_api_runner.generation_permit import load_host_trust_anchor
        from src.ai_copilot.evaluation_namespace import NAMESPACE_ID, CAMPAIGN_ID
        if (type(archive) is not GenerationEvaluationArchive
                or type(token_evidence) is not ExactTokenCount
                or namespace != NAMESPACE_ID or type(host_authorization) is not bytes
                or not dispatch_id or dispatch_id != request_id):
            raise CampaignBlocked("Host authorization inputs are invalid")
        plan = self.plan()
        if plan.model_policy != OWNER_PAID_POLICY or plan.campaign_id != CAMPAIGN_ID:
            raise CampaignBlocked("Approved paid campaign namespace required")
        require_exact_token_count(case_id, request, evidence=token_evidence, review=review)
        _, full_digest, projection_digest = _wire(request)
        context = review._draft._bundle._context
        evidence_record = asdict(token_evidence)
        evidence_record["evidence_refs"] = list(token_evidence.evidence_refs)
        evidence_digest = hashlib.sha256(canonical_bytes(evidence_record)).hexdigest()
        expected = {
            "namespace": namespace, "campaign_id": plan.campaign_id,
            "case_id": case_id, "run_id": context.run_id,
            "request_id": request_id, "model": request.model_snapshot,
            "payload_sha256": full_digest, "count_evidence_sha256": evidence_digest,
            "count_projection_sha256": projection_digest,
            "provider_request_digest": request.request_digest,
            "brief_digest": request.brief_digest,
            "token_cap": request.max_input_tokens,
            "cost_limit_micro_usd": plan.per_slot_ceiling_micro,
        }
        try:
            public_key = load_host_trust_anchor(HOST_OWNER_PUBLIC_KEY_PATH)
            verified = verify_owner_authorization(host_authorization, public_key,
                                                   expected=expected)
            events = archive.dispatch_events(dispatch_id)
            reservation = self.reservation(case_id)
        except Exception as exc:
            raise CampaignBlocked("Host authorization or Archive Intent invalid") from exc
        if (len(events) != 1 or events[0]["event_type"] != "GENERATION_INTENT"
                or events[0]["dispatch_id"] != request_id
                or events[0]["case_id"] != case_id
                or events[0]["run_id"] != context.run_id
                or events[0]["payload_sha256"] != full_digest
                or events[0]["projection_sha256"] != projection_digest
                or events[0]["token_evidence_sha256"] != evidence_digest
                or events[0]["request_digest"] != request.request_digest
                or events[0]["campaign_id"] != plan.campaign_id
                or reservation is None
                or events[0]["ledger_attempt_id"] != reservation["attempt_id"]
                or reservation["ceiling_micro"] != plan.per_slot_ceiling_micro):
            raise CampaignBlocked("Archive Intent does not bind the Host authorization")
        return self._claim_paid_dispatch(case_id, review, request,
                                         token_evidence=token_evidence,
                                         host_authorization=(host_authorization, public_key,
                                                             expected, verified), now=now)

    def _claim_paid_dispatch(self, case_id: str, review: ValidatedBrief,
                             request: ProviderRequest, *, token_evidence,
                             host_authorization, now: int | None) -> str:
        """Shared atomic claim rules for the original and Host-authenticated paths."""
        plan = self.plan()
        if plan.model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid dispatch implementation mode is disabled")
        binding = _binding(review, request, self._slot(plan, case_id), plan)
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                if (not self._paid_authorized(db, plan, current)
                        or db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"):
                    raise CampaignBlocked("Separate paid authorization is unavailable")
                row = db.execute("""SELECT state,attempt_id,request_digest,binding_digest
                    FROM reservations WHERE case_id=?""", (case_id,)).fetchone()
                if (row is None or row[0] != "IN_PROGRESS" or not row[1]
                        or row[2] != request.request_digest or row[3] != binding):
                    raise CampaignBlocked("No exact one-use paid attempt exists")
                from src.ai_copilot.token_count_evidence import require_exact_token_count
                require_exact_token_count(case_id, request, evidence=token_evidence,
                                         review=review)
                if host_authorization is not None:
                    from tools.windows_api_runner.generation_authorization import verify_owner_authorization
                    raw_auth, public_key, expected, verified = host_authorization
                    if verify_owner_authorization(raw_auth, public_key,
                                                  expected=expected, now=current) != verified:
                        raise CampaignBlocked("Host Owner Authorization changed before claim")
                    db.execute("""INSERT INTO host_owner_claims VALUES (?,?,?,?,?,?,?)""",
                               (verified.body["nonce"], verified.envelope_sha256,
                                verified.body["request_id"], plan.campaign_id,
                                case_id, verified.body["run_id"], current))
                db.execute("INSERT INTO dispatch_claims VALUES (?,?,?,?)",
                           (plan.campaign_id, case_id, row[1], current))
                self._event(db, plan, case_id, "PAID_DISPATCH_CLAIMED", current,
                            digest=request.request_digest)
                db.commit()
                return row[1]
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise CampaignBlocked("Paid dispatch claim already consumed") from exc
            except (sqlite3.Error, CampaignBlocked, RunnerError):
                db.rollback()
                raise

    def record_offline_outcome(self, case_id: str, target: str,
                               accounting: ProviderAccounting | None = None,
                               *, now: int | None = None) -> dict:
        if self.plan().model_policy == OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid campaign cannot use caller-selected offline outcome")
        return self._record_outcome(case_id, target, accounting, now=now)

    def _record_outcome(self, case_id: str, target: str,
                        accounting: ProviderAccounting | None = None,
                        *, now: int | None = None) -> dict:
        if target not in {"SUCCEEDED", "FAILED", "UNKNOWN"}:
            raise CampaignBlocked("Invalid offline outcome")
        usage, provider_id, charge, note = accounting.checked() if accounting else (None, None, None, "")
        charge_micro = _micro(charge)
        with self._connect() as check_db:
            policy = self._check(check_db).model_policy
        if target in {"SUCCEEDED", "FAILED"} and (usage is None or charge_micro is None):
            if policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}:
                target = "UNKNOWN"
            else:
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
                if (target == "UNKNOWN" or (plan.model_policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}
                                           and target == "FAILED")
                        or (charge_micro is not None and
                            (charge_micro > row[1] or
                             (plan.model_policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}
                              and charge_micro == row[1])))
                        or observed_total > plan.total_ceiling_micro
                        or (plan.model_policy in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}
                            and observed_total == plan.total_ceiling_micro)):
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

    def validate_paid_dispatch_preflight(self, case_id: str, review: ValidatedBrief,
                                         request: ProviderRequest,
                                         owner_password: str, *, token_evidence=None) -> None:
        """Read-only paid gate used before an archive intent is appended.

        ``claim_paid_dispatch`` repeats every mutable authorization and reservation
        check inside its write transaction, so this preflight never substitutes for
        the atomic one-use dispatch claim.
        """
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner gate required for paid dispatch claim")
        plan = self.plan()
        if plan.model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid dispatch implementation mode is disabled")
        binding = _binding(review, request, self._slot(plan, case_id), plan)
        from src.ai_copilot.token_count_evidence import require_exact_token_count
        require_exact_token_count(case_id, request, evidence=token_evidence,
                                 review=review)
        current = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN")
            self._check(db)
            if (not self._paid_authorized(db, plan, current)
                    or db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"):
                raise CampaignBlocked("Separate paid authorization is unavailable")
            row = db.execute("""SELECT state,attempt_id,request_digest,binding_digest
                FROM reservations WHERE case_id=?""", (case_id,)).fetchone()
            if (row is None or row[0] != "IN_PROGRESS" or not row[1]
                    or row[2] != request.request_digest or row[3] != binding):
                raise CampaignBlocked("No exact one-use paid attempt exists")

    def validate_host_generation_candidate(self, case_id: str,
                                           review: ValidatedBrief,
                                           request: ProviderRequest, *,
                                           token_evidence) -> tuple[dict, str]:
        """Read-only P5 preflight before Host Owner authentication.

        This never authorizes dispatch. The Host-signed proof and the atomic
        claim remain mandatory in ``claim_paid_dispatch_host_authorized``.
        """
        plan = self.plan()
        if plan.model_policy != OWNER_PAID_POLICY:
            raise CampaignBlocked("Paid campaign policy required")
        binding = _binding(review, request, self._slot(plan, case_id), plan)
        from src.ai_copilot.token_count_evidence import require_exact_token_count
        require_exact_token_count(case_id, request, evidence=token_evidence, review=review)
        current = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN")
            self._check(db)
            if (not self._paid_authorized(db, plan, current)
                    or db.execute("SELECT status FROM campaign").fetchone()[0] != "OPEN"):
                raise CampaignBlocked("Paid authorization or budget is unavailable")
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM reservations WHERE case_id=?",
                             (case_id,)).fetchone()
            auth = db.execute("""SELECT reference FROM paid_authorizations
                WHERE campaign_id=? AND manifest_digest=? AND authorized_at<=?
                AND expires_at>? AND revoked_at IS NULL AND policy_version=?""",
                (plan.campaign_id, plan.digest(), current, current, POLICY_VERSION)).fetchone()
            claim = db.execute("SELECT 1 FROM dispatch_claims WHERE case_id=?",
                               (case_id,)).fetchone()
            if (row is None or row["state"] != "IN_PROGRESS" or not row["attempt_id"]
                    or row["request_digest"] != request.request_digest
                    or row["binding_digest"] != binding or claim is not None
                    or auth is None):
                raise CampaignBlocked("Host Generation candidate is stale or already claimed")
            return dict(row), auth["reference"]

    def record_paid_result(self, case_id: str, result: ProviderResult,
                           accounting: ProviderAccounting | None = None,
                           *, now: int | None = None) -> dict:
        """Record a single sanitized provider result; absent charge holds UNKNOWN."""
        if now is not None:
            raise CampaignBlocked("Paid result uses the service clock")
        plan = self.plan()
        if plan.model_policy != OWNER_PAID_POLICY or type(result) is not ProviderResult:
            raise CampaignBlocked("Paid result requires paid mode and typed outcome")
        if accounting is not None:
            checked_usage, checked_id, checked_charge, _ = accounting.checked()
            if checked_charge is not None:
                raise CampaignBlocked("Response metadata cannot prove the billed charge")
            if (checked_usage is not None and checked_usage != json.dumps(result.usage, sort_keys=True)):
                raise CampaignBlocked("Supplied usage differs from provider result")
            if checked_id is not None and checked_id != result.provider_request_id:
                raise CampaignBlocked("Supplied provider ID differs from result")
        if result.status not in {"SUCCEEDED", "REFUSED", "INCOMPLETE",
                                 "DEFINITIVE_ERROR", "UNKNOWN_OUTCOME"}:
            raise CampaignBlocked("Provider result status is invalid")
        observed = ProviderAccounting(
            usage=result.usage if isinstance(result.usage, dict) else None,
            provider_request_id=result.provider_request_id,
            note="Provider response observed; billing requires Owner reconciliation")
        observed.checked()
        current = int(time.time()) if now is None else now
        response_digest = hashlib.sha256(result.raw_response).hexdigest() if result.raw_response else None
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check(db)
                row = db.execute("SELECT state FROM reservations WHERE case_id=?", (case_id,)).fetchone()
                if row is None or row[0] != "IN_PROGRESS":
                    raise CampaignBlocked("Paid result has no unique in-progress attempt")
                db.execute("INSERT INTO provider_observations VALUES (?,?,?,?,?,?)",
                           (plan.campaign_id, case_id, result.status, result.returned_model_id,
                            response_digest, current))
                self._event(db, plan, case_id, "PROVIDER_RESULT_OBSERVED", current,
                            note=result.status)
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise
        # Responses usage is not a final billed charge. Keep the slot and campaign
        # UNKNOWN until an Owner supplies separate billing evidence.
        return self._record_outcome(case_id, "UNKNOWN", observed, now=current)

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

    def record_case_review(self, case_id: str, result, owner_password: str,
                           *, now: int | None = None) -> None:
        """Record independent human adjudication before the next mock case."""
        if self.plan().model_policy == OWNER_PAID_POLICY and now is not None:
            raise CampaignBlocked("Paid human review uses the service clock")
        from src.ai_copilot.quality_evaluation import CaseResult, aggregate_campaign
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner gate required for human review record")
        if type(result) is not CaseResult:
            raise CampaignBlocked("Adjudicated case result required")
        aggregate_campaign((result,))  # Recheck scores, reviewer identities and verdict.
        if (result.technical_status != "VALIDATED" or result.score is None
                or result.status not in {"PASS", "PASS WITH LIMITATIONS", "FAIL"}
                or result.provenance.response_digest is None):
            raise CampaignBlocked("Incomplete or unvalidated case cannot be reviewed")
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                if plan.model_policy not in {OWNER_MOCK_POLICY, OWNER_PAID_POLICY}:
                    raise CampaignBlocked("Owner mock review policy unavailable")
                self._slot(plan, case_id)
                row = db.execute("""SELECT request_digest,state,usage_json,charge_micro,
                    brief_digest,projection_digest,model_snapshot,schema_version,
                    instructions_version,privacy_version,max_output_tokens,timeout_seconds
                    FROM reservations WHERE case_id=?""", (case_id,)).fetchone()
                if (row is None or row[1] != "SUCCEEDED" or row[2] is None or row[3] is None
                        or result.provenance.campaign_id != plan.campaign_id
                        or result.provenance.dataset_version != plan.corpus_version
                        or result.provenance.case_id != case_id
                        or result.provenance.case_version != self._slot(plan, case_id).case_version
                        or (result.provenance.request_digest, result.provenance.brief_digest,
                            result.provenance.projection_digest, result.provenance.model_snapshot,
                            result.provenance.schema_version, result.provenance.instructions_version,
                            result.provenance.privacy_version, result.provenance.max_output_tokens,
                            result.provenance.timeout_seconds) !=
                           (row[0], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11])):
                    raise CampaignBlocked("Review does not match completed accounted slot")
                if plan.model_policy == OWNER_PAID_POLICY:
                    observation = db.execute("SELECT response_digest FROM provider_observations WHERE case_id=?",
                                             (case_id,)).fetchone()
                    if observation is None or result.provenance.response_digest != observation[0]:
                        raise CampaignBlocked("Review response digest differs from provider result")
                if db.execute("SELECT 1 FROM case_reviews WHERE campaign_id=? AND case_id=?",
                              (plan.campaign_id, case_id)).fetchone():
                    raise CampaignBlocked("Case review is already recorded")
                db.execute("""INSERT INTO case_reviews VALUES (?,?,?,?,?,?,?,?,?)""",
                           (plan.campaign_id, case_id, row[0], result.provenance.response_digest,
                            str(result.score), result.status,
                            json.dumps(result.reviewer_ids), result.adjudicator_id, current))
                if result.status != "PASS":
                    db.execute("UPDATE campaign SET status='HELD'")
                self._event(db, plan, case_id, "CASE_HUMAN_REVIEWED", current,
                            actor="OWNER", note=result.status, digest=row[0])
                db.commit()
            except (sqlite3.Error, CampaignBlocked):
                db.rollback()
                raise

    def reconcile_paid_unknown(self, case_id: str, owner_password: str,
                               accounting: ProviderAccounting, note: str,
                               *, now: int | None = None) -> dict:
        """Owner-attested accounting resolution; never creates a new allowance."""
        if now is not None:
            raise CampaignBlocked("Paid reconciliation uses the service clock")
        if not self.approvals._verifier.authenticate(owner_password):
            raise CampaignBlocked("Owner authentication required")
        if not note or not ProviderAccounting.safe_note(note):
            raise CampaignBlocked("Sanitized Owner attestation required")
        usage, provider_id, charge, _ = accounting.checked()
        charge_micro = _micro(charge)
        if usage is None or charge_micro is None:
            raise CampaignBlocked("Both observed usage and charge required")
        current = int(time.time()) if now is None else now
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                plan = self._check(db)
                if plan.model_policy != OWNER_PAID_POLICY:
                    raise CampaignBlocked("Paid reconciliation requires paid mode")
                row = db.execute("SELECT state,ceiling_micro FROM reservations WHERE case_id=?",
                                 (case_id,)).fetchone()
                observation = db.execute("""SELECT result_status,returned_model_id,response_digest
                    FROM provider_observations WHERE case_id=?""", (case_id,)).fetchone()
                if (row is None or row[0] != "UNKNOWN" or observation is None
                        or not luna_model_id_acceptable(observation[1])):
                    raise CampaignBlocked("Definitive provider result is not proven")
                if observation[0] == "SUCCEEDED" and observation[2] is not None:
                    target = "SUCCEEDED"
                elif observation[0] in {"REFUSED", "INCOMPLETE", "DEFINITIVE_ERROR"}:
                    target = "FAILED"
                else:
                    raise CampaignBlocked("Ambiguous provider outcome cannot become definitive")
                db.execute("""UPDATE reservations SET state=?,usage_json=?,
                    charge_micro=?,provider_request_id=COALESCE(?,provider_request_id),
                    updated_at=? WHERE case_id=?""",
                    (target, usage, charge_micro, provider_id, current, case_id))
                total = db.execute("SELECT COALESCE(SUM(charge_micro),0) FROM reservations").fetchone()[0]
                if (target == "SUCCEEDED" and charge_micro < row[1]
                        and total < plan.total_ceiling_micro):
                    db.execute("UPDATE campaign SET status='OPEN'")
                self._event(db, plan, case_id, "OWNER_ACCOUNTING_RECONCILED", current,
                            actor="OWNER", note=note + " Outcome=" + target,
                            usage=usage, charge=charge_micro)
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
            mode = db.execute("SELECT mode FROM campaign").fetchone()[0]
            return {"campaign_id": plan.campaign_id, "mode": mode, "status": status,
                    "reserved_slots": count, "estimated_micro": estimated,
                    "reserved_micro": reserved, "observed_charge_micro": observed,
                    "missing_charge_slots": missing or 0,
                    "total_ceiling_micro": plan.total_ceiling_micro}
