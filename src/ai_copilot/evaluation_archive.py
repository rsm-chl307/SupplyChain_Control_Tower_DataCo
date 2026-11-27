"""Separate append-only P5 generation/evaluation evidence archive. No provider calls."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat

from jsonschema import Draft202012Validator

from src.ai_brief.contract import canonical_bytes
from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.eight_call_campaign import (
    EightCallCampaign, OWNER_MOCK_POLICY, OWNER_PAID_POLICY,
)
from src.ai_copilot.provider import (
    OpenAIResponsesAdapter, ProviderRequest, ProviderResult, build_request,
    luna_model_id_acceptable,
)
from src.ai_copilot.quality_evaluation import (
    CORPUS_VERSION, DIMENSIONS, CaseResult, TechnicalAssessment,
    _registered_case, aggregate_campaign, assess_technical,
)
from src.ai_copilot.response_contract import MAX_RESPONSE_BYTES, classify_response
from src.ai_copilot.token_count_evidence import (
    COUNT_FIELDS, ExactTokenCount, require_exact_token_count,
)
from src.ai_copilot.input_token_count_payload import input_token_count_wire


SCHEMA_PATH = (Path(__file__).resolve().parents[2] /
               "docs/ai_copilot/p5_offline_evaluation/GENERATION_EVALUATION_RECORD_SCHEMA.json")
ARCHIVE_VERSION = "p5-evaluation-archive-1"


class ArchiveBlocked(ValueError):
    """Archive input, identity, linkage or integrity failed closed."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc(epoch: int | None = None) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat() if epoch is not None else datetime.now(timezone.utc).isoformat()


def _schema() -> tuple[Draft202012Validator, str]:
    raw = SCHEMA_PATH.read_bytes()
    schema = json.loads(raw)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema), _digest(raw)


def _create_dispatch_event_schema(db: sqlite3.Connection) -> None:
    """Idempotently add only the WP4.6.2 event extension objects."""
    statements = (
        """CREATE TABLE IF NOT EXISTS archive_dispatch_events(
          event_id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL CHECK(event_type IN ('GENERATION_INTENT','GENERATION_RESULT')),
          dispatch_id TEXT NOT NULL, record_id TEXT NOT NULL, case_id TEXT NOT NULL,
          run_id TEXT NOT NULL, brief_digest TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
          projection_sha256 TEXT NOT NULL, token_evidence_ref TEXT NOT NULL,
          request_digest TEXT NOT NULL, model_alias TEXT NOT NULL,
          token_count INTEGER NOT NULL CHECK(token_count BETWEEN 0 AND 25000),
          previous_digest TEXT, event_digest TEXT NOT NULL UNIQUE, event_json BLOB NOT NULL,
          raw_response BLOB, created_at_utc TEXT NOT NULL,
          UNIQUE(dispatch_id,event_type))""",
        "CREATE UNIQUE INDEX IF NOT EXISTS archive_dispatch_one_terminal ON archive_dispatch_events(dispatch_id) WHERE event_type='GENERATION_RESULT'",
        "CREATE UNIQUE INDEX IF NOT EXISTS archive_dispatch_one_intent_per_record ON archive_dispatch_events(record_id) WHERE event_type='GENERATION_INTENT'",
        "CREATE INDEX IF NOT EXISTS archive_dispatch_record_order ON archive_dispatch_events(record_id,created_at_utc,event_id)",
        """CREATE TRIGGER IF NOT EXISTS archive_dispatch_no_update
          BEFORE UPDATE ON archive_dispatch_events
          BEGIN SELECT RAISE(ABORT,'append-only archive events'); END""",
        """CREATE TRIGGER IF NOT EXISTS archive_dispatch_no_delete
          BEFORE DELETE ON archive_dispatch_events
          BEGIN SELECT RAISE(ABORT,'append-only archive events'); END""",
    )
    for statement in statements:
        db.execute(statement)


def _wire(request: ProviderRequest) -> tuple[bytes, str, str]:
    args = OpenAIResponsesAdapter.call_arguments(request)
    full = json.dumps(args, sort_keys=True, separators=(",", ":")).encode()
    projection = json.dumps({name: args[name] for name in COUNT_FIELDS},
                            sort_keys=True, separators=(",", ":")).encode()
    return full, _digest(full), _digest(projection)


def _record_id(record: dict) -> str:
    return _digest(canonical_bytes({
        "corpus_version": record["corpus_version"],
        "case_id": record["evaluation_case_id"],
        "run_id": record["run"]["run_id"],
        "model": record["payload"]["model_alias"],
        "full_payload_sha256": record["payload"]["full_responses_sha256"],
    }))


def _validate_record(record: dict, validator: Draft202012Validator) -> None:
    errors = list(validator.iter_errors(record))
    if errors or record["record_id"] != _record_id(record):
        raise ArchiveBlocked("Archive record schema or stable identity invalid")


def _ledger_snapshot(campaign: EightCallCampaign, case_id: str) -> tuple[dict, dict, dict | None, dict | None, dict | None]:
    if type(campaign) is not EightCallCampaign:
        raise ArchiveBlocked("Trusted local campaign service required")
    # Read the existing Ledger; this module never changes its schema or accounting.
    with campaign._connect() as db:
        db.execute("BEGIN")
        plan = campaign._check(db)
        campaign._slot(plan, case_id)
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM reservations WHERE campaign_id=? AND case_id=?",
                         (plan.campaign_id, case_id)).fetchone()
        review = db.execute("SELECT * FROM case_reviews WHERE campaign_id=? AND case_id=?",
                            (plan.campaign_id, case_id)).fetchone()
        observed = db.execute("SELECT * FROM provider_observations WHERE campaign_id=? AND case_id=?",
                              (plan.campaign_id, case_id)).fetchone()
        claim = db.execute("SELECT * FROM dispatch_claims WHERE campaign_id=? AND case_id=?",
                           (plan.campaign_id, case_id)).fetchone()
    if row is None:
        raise ArchiveBlocked("Matching Ledger reservation required")
    return (plan.payload(), dict(row), dict(review) if review else None,
            dict(observed) if observed else None, dict(claim) if claim else None)


def _accounting(row: dict, model_policy: str) -> tuple[dict | None, str | None, str | None]:
    usage = json.loads(row["usage_json"]) if row["usage_json"] is not None else None
    if usage is not None and (type(usage) is not dict or set(usage) != {
            "input_tokens", "output_tokens", "total_tokens"}
            or any(type(value) is not int or value < 0 for value in usage.values())
            or usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]):
        raise ArchiveBlocked("Ledger usage is incomplete or invalid")
    charge = row["charge_micro"]
    if charge is not None and (type(charge) is not int or charge < 0):
        raise ArchiveBlocked("Ledger charge is invalid")
    source = ("OWNER_ATTESTED_BILLING" if model_policy == OWNER_PAID_POLICY
              else "SYNTHETIC_TEST_ACCOUNTING") if charge is not None else None
    amount = format(Decimal(charge) / Decimal(1000000), ".6f") if charge is not None else None
    return usage, amount, source


def _phase_integrity(record: dict, phase: str, raw: bytes | None,
                     parsed: bytes | None) -> None:
    generation = record["generation"]
    if phase == "GENERATION":
        if (parsed is not None or generation["parsed_output_ref"] is not None
                or generation["parsed_output_sha256"] is not None
                or record["p1_validation"]["status"] != "NOT_RUN"
                or record["evidence_validation"]["status"] != "NOT_RUN"
                or record["human_evaluation"]["status"] != "NOT_RUN"
                or record["human_evaluation"]["scores"] is not None
                or record["human_evaluation"]["reviewer_ids"]
                or (raw is None) != (generation["raw_output_sha256"] is None)
                or generation["raw_output_sha256"] != (_digest(raw) if raw is not None else None)
                or (raw is not None and generation["raw_output_ref"] !=
                    f"archive:{record['record_id']}:raw")):
            raise ArchiveBlocked("Generation entry is partial or mislabeled")
    elif phase == "EVALUATION":
        if (raw is not None or parsed is None
                or generation["status"] != "SUCCEEDED"
                or generation["parsed_output_ref"] != f"archive:{record['record_id']}:parsed"
                or generation["parsed_output_sha256"] != _digest(parsed)
                or record["p1_validation"]["status"] != "PASS"
                or record["evidence_validation"]["status"] != "PASS"
                or record["human_evaluation"]["status"] != "COMPLETE"
                or set(record["human_evaluation"]["scores"] or {}) != set(DIMENSIONS)
                or len(record["human_evaluation"]["reviewer_ids"]) != 2
                or not record["human_evaluation"]["adjudicator_id"]
                or record["human_evaluation"]["adjudicator_id"] in
                   record["human_evaluation"]["reviewer_ids"]
                or record["human_evaluation"]["verdict"] not in
                   {"PASS", "PASS WITH LIMITATIONS", "FAIL"}
                or not record["human_evaluation"]["review_ref"]
                or generation["usage"] is None
                or generation["actual_charge_usd"] is None
                or generation["charge_source"] is None):
            raise ArchiveBlocked("Evaluation entry is incomplete or mislabeled")
    else:
        raise ArchiveBlocked("Unknown archive phase")


@dataclass(frozen=True)
class ArchiveEntry:
    entry_id: int
    phase: str
    entry_digest: str
    record: dict
    raw_response: bytes | None
    parsed_response: dict | None
    ledger_campaign_id: str
    ledger_state_at_write: str
    provider_status: str
    reviewed_at_utc: str | None


class GenerationEvaluationArchive:
    """Immutable snapshots in a separate SQLite file; no dispatch or retry capability."""

    @staticmethod
    def provision(path: str) -> None:
        target = Path(path).absolute()
        if not target.parent.is_dir() or target.exists() or target.is_symlink():
            raise ArchiveBlocked("New dedicated archive path required")
        _, schema_digest = _schema()
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        try:
            with sqlite3.connect(target) as db:
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
                db.executescript("""
                    CREATE TABLE archive_meta(version TEXT PRIMARY KEY, schema_digest TEXT NOT NULL);
                    CREATE TABLE archive_entries(
                      entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      record_id TEXT NOT NULL, phase TEXT NOT NULL CHECK(phase IN ('GENERATION','EVALUATION')),
                      previous_digest TEXT, entry_digest TEXT NOT NULL UNIQUE,
                      record_json BLOB NOT NULL, raw_response BLOB, parsed_json BLOB,
                      ledger_campaign_id TEXT NOT NULL, ledger_request_digest TEXT NOT NULL,
                      ledger_state_at_write TEXT NOT NULL, provider_status TEXT NOT NULL,
                      reviewed_at_utc TEXT, written_at_utc TEXT NOT NULL,
                      UNIQUE(record_id,phase));
                    CREATE TRIGGER archive_no_update BEFORE UPDATE ON archive_entries
                      BEGIN SELECT RAISE(ABORT,'append-only archive'); END;
                    CREATE TRIGGER archive_no_delete BEFORE DELETE ON archive_entries
                      BEGIN SELECT RAISE(ABORT,'append-only archive'); END;
                    CREATE TRIGGER archive_meta_no_update BEFORE UPDATE ON archive_meta
                      BEGIN SELECT RAISE(ABORT,'append-only archive'); END;
                    CREATE TRIGGER archive_meta_no_delete BEFORE DELETE ON archive_meta
                      BEGIN SELECT RAISE(ABORT,'append-only archive'); END;
                """)
                _create_dispatch_event_schema(db)
                db.execute("INSERT INTO archive_meta VALUES (?,?)", (ARCHIVE_VERSION, schema_digest))
                db.commit()
        except (OSError, sqlite3.Error):
            # A failed provision leaves an unusable file; never auto-replace it.
            raise ArchiveBlocked("Archive provision failed; inspect the dedicated path")

    def __init__(self, path: str):
        self.path = Path(path).absolute()
        self.validator, self.schema_digest = _schema()
        self._inode = self._identity()
        with self._connect() as db:
            if db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                raise ArchiveBlocked("Archive integrity check failed")
            if db.execute("SELECT version,schema_digest FROM archive_meta").fetchall() != [
                    (ARCHIVE_VERSION, self.schema_digest)]:
                raise ArchiveBlocked("Archive schema version or record contract changed")

    @classmethod
    def dispatch_event_schema_state(cls, path: str) -> str:
        """Return PRESENT, LEGACY_MISSING, or PARTIAL after validating archive identity."""
        archive = cls(path)
        expected_columns = {
            "event_id", "event_type", "dispatch_id", "record_id", "case_id", "run_id",
            "brief_digest", "payload_sha256", "projection_sha256", "token_evidence_ref",
            "request_digest", "model_alias", "token_count", "previous_digest",
            "event_digest", "event_json", "raw_response", "created_at_utc",
        }
        required_objects = {
            ("index", "archive_dispatch_one_terminal"),
            ("index", "archive_dispatch_one_intent_per_record"),
            ("index", "archive_dispatch_record_order"),
            ("trigger", "archive_dispatch_no_update"),
            ("trigger", "archive_dispatch_no_delete"),
        }
        with archive._connect() as db:
            table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_dispatch_events'").fetchone()
            if table is None:
                return "LEGACY_MISSING"
            columns = {row[1] for row in db.execute("PRAGMA table_info(archive_dispatch_events)")}
            objects = set(db.execute("SELECT type,name FROM sqlite_master WHERE name LIKE 'archive_dispatch_%'"))
        if not expected_columns.issubset(columns):
            return "PARTIAL"
        return "PRESENT" if required_objects.issubset(objects) else "PARTIAL"

    @classmethod
    def extend_legacy_event_schema(cls, path: str) -> str:
        """Explicitly and idempotently extend a compatible archive without touching entries.

        Returns ``EXTENDED`` when event schema objects were added/repaired and
        ``ALREADY_PRESENT`` when the complete extension was already present.
        This method is intentionally not called by ``__init__``.
        """
        state = cls.dispatch_event_schema_state(path)
        archive = cls(path)
        if state == "PRESENT":
            return "ALREADY_PRESENT"
        if state == "PARTIAL":
            raise ArchiveBlocked("Archive contains a partial/incompatible event extension")
        try:
            with archive._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                meta = db.execute("SELECT version,schema_digest FROM archive_meta").fetchall()
                if meta != [(ARCHIVE_VERSION, archive.schema_digest)]:
                    raise ArchiveBlocked("Legacy archive contract changed during extension")
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_entries'").fetchone() is None:
                    raise ArchiveBlocked("Compatible legacy archive entries table is missing")
                _create_dispatch_event_schema(db)
                db.commit()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Legacy event schema extension failed; existing entries were retained") from exc
        return "EXTENDED"

    def _identity(self) -> tuple[int, int]:
        try:
            info = self.path.lstat()
        except OSError as exc:
            raise ArchiveBlocked("Archive file missing") from exc
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                or self.path.is_symlink()):
            raise ArchiveBlocked("Archive identity or permissions invalid")
        return info.st_dev, info.st_ino

    def _connect(self) -> sqlite3.Connection:
        if self._identity() != self._inode:
            raise ArchiveBlocked("Archive file replaced")
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _entry_digest(record: dict, raw: bytes | None, parsed: bytes | None,
                      *, phase: str, previous: str | None, campaign_id: str,
                      request_digest: str, ledger_state: str, provider_status: str,
                      reviewed_at: str | None, written_at: str) -> str:
        return _digest(canonical_bytes({
            "record": record, "raw_sha256": _digest(raw) if raw is not None else None,
            "parsed_sha256": _digest(parsed) if parsed is not None else None,
            "phase": phase, "previous": previous, "campaign_id": campaign_id,
            "request_digest": request_digest, "ledger_state": ledger_state,
            "provider_status": provider_status, "reviewed_at": reviewed_at,
            "written_at": written_at,
        }))

    def _append(self, record: dict, *, phase: str, previous: str | None,
                raw: bytes | None, parsed: bytes | None, campaign_id: str,
                request_digest: str, ledger_state: str, provider_status: str,
                reviewed_at: str | None = None) -> ArchiveEntry:
        _validate_record(record, self.validator)
        _phase_integrity(record, phase, raw, parsed)
        if (request_digest != record["payload"]["provider_request_sha256"]
                or phase == "EVALUATION" and record["human_evaluation"]["review_ref"] !=
                   f"ledger:{campaign_id}:{record['evaluation_case_id']}:review"):
            raise ArchiveBlocked("Archive Ledger reference differs from record")
        written_at = _utc()
        entry_digest = self._entry_digest(
            record, raw, parsed, phase=phase, previous=previous,
            campaign_id=campaign_id, request_digest=request_digest,
            ledger_state=ledger_state, provider_status=provider_status,
            reviewed_at=reviewed_at, written_at=written_at)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT phase,entry_digest FROM archive_entries WHERE record_id=? ORDER BY entry_id",
                                      (record["record_id"],)).fetchall()
                expected = [] if phase == "GENERATION" else [("GENERATION", previous)]
                if existing != expected:
                    raise ArchiveBlocked("Archive phase already exists or predecessor changed")
                cursor = db.execute("""INSERT INTO archive_entries
                    (record_id,phase,previous_digest,entry_digest,record_json,raw_response,parsed_json,
                     ledger_campaign_id,ledger_request_digest,ledger_state_at_write,provider_status,
                     reviewed_at_utc,written_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (record["record_id"], phase, previous, entry_digest, canonical_bytes(record),
                     raw, parsed, campaign_id, request_digest, ledger_state, provider_status,
                     reviewed_at, written_at))
                entry_id = cursor.lastrowid
                db.commit()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Archive write failed; no provider retry is permitted") from exc
        return ArchiveEntry(entry_id, phase, entry_digest, deepcopy(record), raw,
                            json.loads(parsed) if parsed is not None else None,
                            campaign_id, ledger_state, provider_status, reviewed_at)

    @staticmethod
    def _event_digest(event: dict, raw: bytes | None, previous: str | None) -> str:
        return _digest(canonical_bytes({"event": event,
                                        "raw_sha256": _digest(raw) if raw is not None else None,
                                        "previous": previous}))

    def append_generation_intent(self, *, dispatch_id: str, case: dict,
                                 review: ValidatedBrief, request: ProviderRequest,
                                 token_evidence: ExactTokenCount,
                                 campaign: EightCallCampaign) -> dict:
        """Append the immutable archive gate record before the Ledger claim."""
        from src.ai_copilot.token_count_evidence import require_exact_token_count
        if (type(dispatch_id) is not str or not dispatch_id or len(dispatch_id) > 120
                or type(review) is not ValidatedBrief or type(request) is not ProviderRequest
                or type(token_evidence) is not ExactTokenCount
                or type(campaign) is not EightCallCampaign):
            raise ArchiveBlocked("Typed dispatch intent inputs required")
        case_id = case.get("id") if type(case) is dict else None
        plan, row, _, _, _ = _ledger_snapshot(campaign, case_id)
        if plan["model_policy"] != OWNER_PAID_POLICY:
            raise ArchiveBlocked("Paid archive intent requires isolated paid policy")
        _registered_case(case, plan["corpus_version"])
        brief = review.verify()
        context = review._draft._bundle._context
        full, full_digest, projection_digest = _wire(request)
        count_wire, count_digest, count_projection_digest = input_token_count_wire(request)
        if (request.execution_profile != "P5_PAID_ACCEPTANCE"
                or request.model_snapshot != plan["model_snapshot"]
                or request.brief_digest != review.content_digest
                or row["request_digest"] != request.request_digest
                or row["brief_digest"] != request.brief_digest
                or row["projection_digest"] != request.provider_brief_digest
                or context.run_id != review._draft._bundle.manifest()["Run_ID"]
                or review._draft._bundle._harness._fixture_id != case["fixture_id"]
                or review._draft.max_records != case["max_records"]
                or brief["run_context"]["Scenario"] != case["scenario"]
                or bool(brief["run_context"]["Comparison_ID"]) != case["comparison"]):
            raise ArchiveBlocked("Intent Run, Brief, Ledger or payload identity mismatch")
        if (token_evidence.case_id != case_id or token_evidence.model != request.model_snapshot
                or token_evidence.full_payload_sha256 != count_digest
                or token_evidence.count_projection_sha256 != count_projection_digest
                or not token_evidence.request_id
                or type(token_evidence.input_tokens) is not int
                or not 0 <= token_evidence.input_tokens <= request.max_input_tokens == 25000
                or require_exact_token_count(case_id, request, evidence=token_evidence,
                                              review=review) != token_evidence.input_tokens
                or (token_evidence.run_id is not None and token_evidence.run_id != context.run_id)
                or (token_evidence.run_manifest_sha256 is not None
                    and token_evidence.run_manifest_sha256 != context.manifest_sha256)
                or (token_evidence.brief_digest is not None
                    and token_evidence.brief_digest != request.brief_digest)
                or (token_evidence.provider_brief_digest is not None
                    and token_evidence.provider_brief_digest != request.provider_brief_digest)
                or (token_evidence.provider_request_digest is not None
                    and token_evidence.provider_request_digest != request.request_digest)
                or (token_evidence.fixture_id is not None
                    and token_evidence.fixture_id != case["fixture_id"])
                or (token_evidence.payload_bytes is not None
                    and token_evidence.payload_bytes != len(count_wire))
                or (token_evidence.evidence_refs and set(token_evidence.evidence_refs) !=
                    {item["source_ref"] for item in case["evidence"]})):
            raise ArchiveBlocked("Trusted exact token evidence does not bind to intent")
        if token_evidence.http_status != 200:
            raise ArchiveBlocked("Token evidence is not in the trusted case-bound evidence set")
        record_id = _digest(canonical_bytes({
            "corpus_version": CORPUS_VERSION, "case_id": case_id,
            "run_id": context.run_id, "model": request.model_snapshot,
            "full_payload_sha256": full_digest,
        }))
        evidence_record = asdict(token_evidence)
        evidence_record["evidence_refs"] = list(token_evidence.evidence_refs)
        event = {
            "event_type": "GENERATION_INTENT", "dispatch_id": dispatch_id,
            "record_id": record_id, "case_id": case_id, "run_id": context.run_id,
            "campaign_id": plan["campaign_id"], "ledger_attempt_id": row["attempt_id"],
            "brief_digest": request.brief_digest, "payload_sha256": full_digest,
            "projection_sha256": projection_digest,
            "token_evidence_ref": token_evidence.request_id,
            "token_evidence_sha256": _digest(canonical_bytes(evidence_record)),
            "request_digest": request.request_digest, "model_alias": request.model_snapshot,
            "token_count": token_evidence.input_tokens,
        }
        timestamp = _utc()
        digest = self._event_digest(event, None, None)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                pending = db.execute("""SELECT 1 FROM archive_dispatch_events i
                    WHERE i.record_id=? AND i.event_type='GENERATION_INTENT'
                    AND NOT EXISTS (SELECT 1 FROM archive_dispatch_events r
                        WHERE r.dispatch_id=i.dispatch_id AND r.event_type='GENERATION_RESULT')""",
                    (record_id,)).fetchone()
                if pending:
                    raise ArchiveBlocked("Unresolved dispatch intent blocks another dispatch")
                db.execute("""INSERT INTO archive_dispatch_events
                    (event_id,event_type,dispatch_id,record_id,case_id,run_id,brief_digest,
                     payload_sha256,projection_sha256,token_evidence_ref,request_digest,
                     model_alias,token_count,previous_digest,event_digest,event_json,raw_response,
                     created_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (secrets.token_hex(16), "GENERATION_INTENT", dispatch_id, record_id,
                     case_id, context.run_id, request.brief_digest, full_digest,
                     projection_digest, token_evidence.request_id, request.request_digest,
                     request.model_snapshot, token_evidence.input_tokens, None, digest,
                     canonical_bytes(event), None, timestamp))
                db.commit()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Intent archive failed; dispatch is forbidden") from exc
        return {**event, "event_digest": digest, "created_at_utc": timestamp}

    def append_generation_result(self, *, dispatch_id: str, result: ProviderResult,
                                 campaign_id: str) -> dict:
        """Append one terminal response event linked to a prior intent."""
        if type(result) is not ProviderResult:
            raise ArchiveBlocked("Typed provider result required")
        try:
            with self._connect() as db:
                db.row_factory = sqlite3.Row
                intent = db.execute("""SELECT * FROM archive_dispatch_events
                    WHERE dispatch_id=? AND event_type='GENERATION_INTENT'""",
                    (dispatch_id,)).fetchone()
                terminal = db.execute("SELECT 1 FROM archive_dispatch_events WHERE dispatch_id=? AND event_type='GENERATION_RESULT'",
                                      (dispatch_id,)).fetchone()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Archive event extension is unavailable; no retry permitted") from exc
        if intent is None or terminal is not None:
            raise ArchiveBlocked("Dispatch intent missing or already has a result")
        intent_body = json.loads(intent["event_json"])
        if campaign_id != intent_body.get("campaign_id"):
            raise ArchiveBlocked("Result Ledger campaign differs from its intent")
        if any(intent_body.get(key) != intent[column] for key, column in (
                ("record_id", "record_id"), ("case_id", "case_id"),
                ("run_id", "run_id"), ("brief_digest", "brief_digest"),
                ("payload_sha256", "payload_sha256"),
                ("projection_sha256", "projection_sha256"),
                ("token_evidence_ref", "token_evidence_ref"),
                ("request_digest", "request_digest"), ("model_alias", "model_alias"),
                ("token_count", "token_count"))):
            raise ArchiveBlocked("Intent columns differ from its immutable event body")
        if result.raw_response is not None and (type(result.raw_response) is not bytes
                                                or len(result.raw_response) > MAX_RESPONSE_BYTES):
            raise ArchiveBlocked("Provider raw response is invalid or oversized")
        if result.usage is not None and (type(result.usage) is not dict
                or set(result.usage) != {"input_tokens", "output_tokens", "total_tokens"}
                or any(type(x) is not int or x < 0 for x in result.usage.values())
                or result.usage["input_tokens"] + result.usage["output_tokens"] != result.usage["total_tokens"]):
            raise ArchiveBlocked("Provider usage is invalid")
        event = {
            "event_type": "GENERATION_RESULT", "dispatch_id": dispatch_id,
            "record_id": intent_body["record_id"], "case_id": intent_body["case_id"],
            "run_id": intent_body["run_id"], "brief_digest": intent_body["brief_digest"],
            "payload_sha256": intent_body["payload_sha256"],
            "projection_sha256": intent_body["projection_sha256"],
            "token_evidence_ref": intent_body["token_evidence_ref"],
            "token_evidence_sha256": intent_body.get("token_evidence_sha256"),
            "request_digest": intent_body["request_digest"],
            "model_alias": intent_body["model_alias"], "token_count": intent_body["token_count"],
            "campaign_id": intent_body["campaign_id"],
            "status": result.status, "request_id": result.provider_request_id,
            "returned_model_id": result.returned_model_id, "usage": result.usage,
            "usage_source": "PROVIDER_RESPONSE" if result.usage is not None else None,
            "charge_usd": None, "charge_source": None,
            "raw_sha256": _digest(result.raw_response) if result.raw_response is not None else None,
            "reason": result.reason,
        }
        timestamp = _utc()
        previous = intent["event_digest"]
        digest = self._event_digest(event, result.raw_response, previous)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM archive_dispatch_events WHERE dispatch_id=? AND event_type='GENERATION_RESULT'",
                              (dispatch_id,)).fetchone():
                    raise ArchiveBlocked("Dispatch result already exists")
                cursor = db.execute("""INSERT INTO archive_dispatch_events
                    (event_id,event_type,dispatch_id,record_id,case_id,run_id,brief_digest,
                     payload_sha256,projection_sha256,token_evidence_ref,request_digest,
                     model_alias,token_count,previous_digest,event_digest,event_json,raw_response,
                     created_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (secrets.token_hex(16), "GENERATION_RESULT", dispatch_id,
                     intent["record_id"], intent["case_id"], intent["run_id"],
                     intent["brief_digest"], intent["payload_sha256"],
                     intent["projection_sha256"], intent["token_evidence_ref"],
                     intent["request_digest"], intent["model_alias"], intent["token_count"],
                     previous, digest, canonical_bytes(event), result.raw_response, timestamp))
                db.commit()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Result archive failed; dispatch will not be retried") from exc
        return {**event, "event_digest": digest, "created_at_utc": timestamp,
                "campaign_id": campaign_id}

    def dispatch_events(self, dispatch_id: str) -> list[dict]:
        """Read and verify a dispatch event chain without exposing payload contents."""
        try:
            with self._connect() as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT * FROM archive_dispatch_events WHERE dispatch_id=? ORDER BY rowid",
                                  (dispatch_id,)).fetchall()
        except sqlite3.Error as exc:
            raise ArchiveBlocked("Archive event extension is unavailable") from exc
        if not rows or rows[0]["event_type"] != "GENERATION_INTENT":
            raise ArchiveBlocked("Dispatch event intent missing")
        output = []
        previous = None
        for row in rows:
            event = json.loads(row["event_json"])
            if (row["previous_digest"] != previous
                    or self._event_digest(event, row["raw_response"], previous) != row["event_digest"]
                    or event.get("dispatch_id") != dispatch_id
                    or any(event.get(key) != row[column] for key, column in (
                        ("record_id", "record_id"), ("case_id", "case_id"),
                        ("run_id", "run_id"), ("brief_digest", "brief_digest"),
                        ("payload_sha256", "payload_sha256"),
                        ("projection_sha256", "projection_sha256"),
                        ("token_evidence_ref", "token_evidence_ref"),
                        ("request_digest", "request_digest"), ("model_alias", "model_alias"),
                        ("token_count", "token_count")))):
                raise ArchiveBlocked("Dispatch event chain integrity failed")
            output.append({**event, "event_digest": row["event_digest"],
                           "created_at_utc": row["created_at_utc"]})
            previous = row["event_digest"]
        if len(output) > 2 or (len(output) == 2 and output[1]["event_type"] != "GENERATION_RESULT"):
            raise ArchiveBlocked("Dispatch event sequence is invalid")
        return output

    def append_generation(self, *, case: dict, review: ValidatedBrief,
                          request: ProviderRequest, token_evidence: ExactTokenCount,
                          result: ProviderResult, campaign: EightCallCampaign) -> ArchiveEntry:
        if (type(review) is not ValidatedBrief or type(request) is not ProviderRequest
                or type(token_evidence) is not ExactTokenCount or type(result) is not ProviderResult):
            raise ArchiveBlocked("Typed trusted generation inputs required")
        plan, row, _, observation, claim = _ledger_snapshot(campaign, case.get("id"))
        if plan["corpus_version"] != CORPUS_VERSION:
            raise ArchiveBlocked("Pinned P5 corpus required")
        _registered_case(case, plan["corpus_version"])
        brief = review.verify()
        context = review._draft._bundle._context
        if (review._draft._bundle._harness._fixture_id != case["fixture_id"]
                or brief["run_context"]["Scenario"] != case["scenario"]
                or review._draft.max_records != case["max_records"]
                or bool(brief["run_context"]["Comparison_ID"]) != case["comparison"]
                or context.run_id != review._draft._bundle.manifest()["Run_ID"]):
            raise ArchiveBlocked("Case, Run or Brief identity mismatch")
        expected_profile = ("P5_PAID_ACCEPTANCE" if plan["model_policy"] == OWNER_PAID_POLICY
                            else "P5_ACCEPTANCE_MOCK" if plan["model_policy"] == OWNER_MOCK_POLICY
                            else None)
        full, full_digest, projection_digest = _wire(request)
        count_wire, count_digest, count_projection_digest = input_token_count_wire(request)
        if (expected_profile is None or request.execution_profile != expected_profile
                or request.brief_digest != review.content_digest
                or row["brief_digest"] != request.brief_digest
                or row["projection_digest"] != request.provider_brief_digest
                or row["request_digest"] != request.request_digest
                or row["model_snapshot"] != request.model_snapshot
                or request.model_snapshot != plan["model_snapshot"]):
            raise ArchiveBlocked("Ledger, Brief or request binding mismatch")
        if (token_evidence.case_id != case["id"] or token_evidence.model != request.model_snapshot
                or token_evidence.full_payload_sha256 != count_digest
                or token_evidence.count_projection_sha256 != count_projection_digest
                or type(token_evidence.input_tokens) is not int
                or not 0 <= token_evidence.input_tokens <= request.max_input_tokens == 25000
                or not token_evidence.request_id
                or (token_evidence.brief_digest is not None
                    and token_evidence.brief_digest != request.brief_digest)
                or (token_evidence.provider_brief_digest is not None
                    and token_evidence.provider_brief_digest != request.provider_brief_digest)
                or (token_evidence.provider_request_digest is not None
                    and token_evidence.provider_request_digest != request.request_digest)
                or (token_evidence.run_id is not None and token_evidence.run_id != context.run_id)
                or (token_evidence.run_manifest_sha256 is not None
                    and token_evidence.run_manifest_sha256 != context.manifest_sha256)
                or (token_evidence.fixture_id is not None
                    and token_evidence.fixture_id != case["fixture_id"])
                or (token_evidence.payload_bytes is not None
                    and token_evidence.payload_bytes != len(count_wire))
                or (token_evidence.evidence_refs
                    and set(token_evidence.evidence_refs) !=
                    {item["source_ref"] for item in case["evidence"]})):
            raise ArchiveBlocked("Exact token evidence differs from payload or Run")
        if expected_profile == "P5_PAID_ACCEPTANCE":
            if (token_evidence.http_status != 200
                    or require_exact_token_count(case["id"], request,
                                                 evidence=token_evidence,
                                                 review=review) != token_evidence.input_tokens):
                raise ArchiveBlocked("Paid exact count is not trusted")
            if claim is None or observation is None or observation["result_status"] != result.status:
                raise ArchiveBlocked("Paid dispatch claim and provider observation required")
        if result.status not in {"SUCCEEDED", "REFUSED", "INCOMPLETE",
                                 "DEFINITIVE_ERROR", "UNKNOWN_OUTCOME"}:
            raise ArchiveBlocked("Provider outcome invalid")
        status = ("SUCCEEDED" if result.status == "SUCCEEDED" else
                  "UNKNOWN" if result.status in {"UNKNOWN_OUTCOME", "INCOMPLETE"} else "FAILED")
        if (row["state"] not in {"IN_PROGRESS", "UNKNOWN", "SUCCEEDED", "FAILED"}
                or (row["state"] == "SUCCEEDED" and status != "SUCCEEDED")
                or (row["state"] == "FAILED" and status != "FAILED")):
            raise ArchiveBlocked("Ledger outcome conflicts with generation")
        raw = result.raw_response
        if (raw is not None and (type(raw) is not bytes or len(raw) > MAX_RESPONSE_BYTES)):
            raise ArchiveBlocked("Raw response invalid or oversized")
        if status == "SUCCEEDED" and (not raw or not luna_model_id_acceptable(result.returned_model_id)
                                      or not result.provider_request_id):
            raise ArchiveBlocked("Successful response lacks raw bytes or provider identity")
        if result.returned_model_id is not None and not luna_model_id_acceptable(result.returned_model_id):
            raise ArchiveBlocked("Returned model differs from approved family")
        usage = result.usage
        if usage is not None and (type(usage) is not dict
                                  or set(usage) != {"input_tokens", "output_tokens", "total_tokens"}
                                  or any(type(x) is not int or x < 0 for x in usage.values())
                                  or usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]):
            raise ArchiveBlocked("Provider usage invalid")
        ledger_usage, charge, charge_source = _accounting(row, plan["model_policy"])
        if (ledger_usage is not None and usage != ledger_usage
                or row["provider_request_id"] is not None
                and result.provider_request_id != row["provider_request_id"]
                or observation is not None and (
                    observation["returned_model_id"] not in (None, result.returned_model_id)
                    or observation["response_digest"] not in (None, _digest(raw) if raw else None))):
            raise ArchiveBlocked("Provider result conflicts with Ledger observation")
        evidence_refs = sorted({item["source_ref"] for item in case["evidence"]})
        now = _utc()
        record = {
            "record_version": "p5-generation-evaluation-record-1",
            "corpus_version": CORPUS_VERSION, "evaluation_case_id": case["id"],
            "created_at_utc": now,
            "run": {"fixture_id": case["fixture_id"], "run_id": context.run_id,
                    "manifest_sha256": context.manifest_sha256,
                    "brief_run_alias": brief["run_context"]["Run_ID"],
                    "comparison_alias": brief["run_context"]["Comparison_ID"],
                    "evidence_refs": evidence_refs},
            "brief": {"content_sha256": request.brief_digest,
                      "provider_projection_sha256": request.provider_brief_digest},
            "payload": {"model_alias": request.model_snapshot,
                        "provider_request_sha256": request.request_digest,
                        "full_responses_sha256": full_digest,
                        "count_projection_sha256": projection_digest,
                        "byte_length": len(full)},
            "token_count": {"status": "SUCCESS", "http_status": token_evidence.http_status,
                            "request_id": token_evidence.request_id,
                            "input_tokens": token_evidence.input_tokens,
                            "timestamp_utc": token_evidence.timestamp_utc,
                            "returned_usage": None, "returned_cost": None},
            "generation": {"status": status,
                           "raw_output_ref": None, "raw_output_sha256": None,
                           "parsed_output_ref": None, "parsed_output_sha256": None,
                           "returned_model_id": result.returned_model_id,
                           "request_id": result.provider_request_id,
                           "usage": usage, "actual_charge_usd": charge,
                           "charge_source": charge_source, "timestamp_utc": now},
            "p1_validation": {"status": "NOT_RUN", "result_ref": None,
                              "checked_at_utc": None},
            "evidence_validation": {"status": "NOT_RUN", "result_ref": None,
                                    "checked_at_utc": None},
            "human_evaluation": {"status": "NOT_RUN", "reviewer_ids": [],
                                 "adjudicator_id": None, "scores": None,
                                 "critical_failures": [], "verdict": None,
                                 "review_ref": None},
        }
        record["record_id"] = _record_id(record)
        if raw is not None:
            record["generation"]["raw_output_ref"] = f"archive:{record['record_id']}:raw"
            record["generation"]["raw_output_sha256"] = _digest(raw)
        return self._append(record, phase="GENERATION", previous=None,
                            raw=raw, parsed=None, campaign_id=plan["campaign_id"],
                            request_digest=request.request_digest, ledger_state=row["state"],
                            provider_status=result.status)

    def append_evaluation(self, record_id: str, *, review: ValidatedBrief,
                          technical: TechnicalAssessment, result: CaseResult,
                          campaign: EightCallCampaign) -> ArchiveEntry:
        history = self.history(record_id)
        if len(history) != 1 or history[0].phase != "GENERATION":
            raise ArchiveBlocked("One unevaluated generation entry required")
        generated = history[0]
        record = deepcopy(generated.record)
        if (type(review) is not ValidatedBrief or type(technical) is not TechnicalAssessment
                or type(result) is not CaseResult or generated.raw_response is None
                or record["generation"]["status"] != "SUCCEEDED"):
            raise ArchiveBlocked("Successful raw generation and typed assessment required")
        plan, row, ledger_review, observation, claim = _ledger_snapshot(campaign, record["evaluation_case_id"])
        if (plan["campaign_id"] != generated.ledger_campaign_id
                or row["request_digest"] != record["payload"]["provider_request_sha256"]
                or row["brief_digest"] != record["brief"]["content_sha256"]
                or row["state"] != "SUCCEEDED" or ledger_review is None):
            raise ArchiveBlocked("Completed accounted Ledger review required")
        ledger_usage, charge, charge_source = _accounting(row, plan["model_policy"])
        if (ledger_usage is None or charge is None or charge_source is None
                or record["generation"]["usage"] != ledger_usage
                or record["generation"]["request_id"] != row["provider_request_id"]
                or technical.raw_response != generated.raw_response
                or technical.provenance != result.provenance
                or technical.provenance.campaign_id != plan["campaign_id"]
                or technical.provenance.case_id != record["evaluation_case_id"]
                or technical.provenance.brief_digest != record["brief"]["content_sha256"]
                or technical.provenance.projection_digest != record["brief"]["provider_projection_sha256"]
                or technical.provenance.request_digest != row["request_digest"]
                or technical.provenance.model_snapshot != record["payload"]["model_alias"]
                or technical.provenance.response_digest != record["generation"]["raw_output_sha256"]
                or technical.p1_status != "VALIDATED" or technical.missing_expected_refs
                or result.score is None or result.status not in {"PASS", "PASS WITH LIMITATIONS", "FAIL"}
                or ledger_review["request_digest"] != row["request_digest"]
                or ledger_review["response_digest"] != technical.provenance.response_digest
                or ledger_review["score"] != str(result.score)
                or ledger_review["verdict"] != result.status
                or json.loads(ledger_review["reviewer_ids_json"]) != list(result.reviewer_ids or ())
                or ledger_review["adjudicator_id"] != result.adjudicator_id
                or observation is not None and observation["response_digest"] != technical.provenance.response_digest
                or plan["model_policy"] == OWNER_PAID_POLICY and (claim is None or observation is None)):
            raise ArchiveBlocked("Evaluation, response or accounting lineage mismatch")
        aggregate_campaign((result,))  # Recheck complete adjudication and verdict.
        context = review._draft._bundle._context
        if (review.content_digest != technical.provenance.brief_digest
                or context.run_id != record["run"]["run_id"]
                or context.manifest_sha256 != record["run"]["manifest_sha256"]):
            raise ArchiveBlocked("Trusted Brief changed")
        corpus = json.loads((SCHEMA_PATH.parent / "cases.v2.json").read_bytes())
        case = next((item for item in corpus["cases"]
                     if item["id"] == record["evaluation_case_id"]), None)
        if case is None:
            raise ArchiveBlocked("Pinned evaluation case missing")
        rebuilt = build_request(
            review, model_snapshot=row["model_snapshot"],
            max_output_tokens=row["max_output_tokens"],
            timeout_seconds=row["timeout_seconds"],
            execution_profile=("P5_PAID_ACCEPTANCE" if plan["model_policy"] == OWNER_PAID_POLICY
                               else "P5_ACCEPTANCE_MOCK"))
        if (rebuilt.request_digest != row["request_digest"]
                or assess_technical(case, dataset_version=CORPUS_VERSION,
                                    campaign_id=plan["campaign_id"], review=review,
                                    request=rebuilt, raw_response=generated.raw_response,
                                    provider_status="SUCCEEDED") != technical):
            raise ArchiveBlocked("Technical assessment differs from trusted evidence")
        parsed = classify_response(generated.raw_response, review, provider_status="SUCCEEDED")
        if parsed.status != "VALIDATED" or parsed.response is None:
            raise ArchiveBlocked("P1 strict response validation failed")
        parsed_bytes = canonical_bytes(parsed.response)
        record["generation"]["actual_charge_usd"] = charge
        record["generation"]["charge_source"] = charge_source
        record["generation"]["parsed_output_ref"] = f"archive:{record_id}:parsed"
        record["generation"]["parsed_output_sha256"] = _digest(parsed_bytes)
        now = _utc()
        record["p1_validation"] = {"status": "PASS", "result_ref": f"archive:{record_id}:parsed",
                                   "checked_at_utc": now}
        record["evidence_validation"] = {"status": "PASS", "result_ref": f"archive:{record_id}:parsed",
                                         "checked_at_utc": now}
        record["human_evaluation"] = {
            "status": "COMPLETE", "reviewer_ids": list(result.reviewer_ids or ()),
            "adjudicator_id": result.adjudicator_id,
            "scores": dict(result.final_scores or {}),
            "critical_failures": list(result.critical_failures),
            "verdict": result.status,
            "review_ref": f"ledger:{plan['campaign_id']}:{record['evaluation_case_id']}:review",
        }
        reviewed_at = _utc(ledger_review["reviewed_at"])
        entry = self._append(record, phase="EVALUATION", previous=generated.entry_digest,
                             raw=None, parsed=parsed_bytes, campaign_id=plan["campaign_id"],
                             request_digest=row["request_digest"], ledger_state=row["state"],
                             provider_status=generated.provider_status, reviewed_at=reviewed_at)
        return ArchiveEntry(entry.entry_id, entry.phase, entry.entry_digest, entry.record,
                            generated.raw_response, entry.parsed_response,
                            entry.ledger_campaign_id, entry.ledger_state_at_write,
                            entry.provider_status, entry.reviewed_at_utc)

    def history(self, record_id: str) -> tuple[ArchiveEntry, ...]:
        if type(record_id) is not str or len(record_id) != 64 or any(c not in "0123456789abcdef" for c in record_id):
            raise ArchiveBlocked("Stable record ID invalid")
        with self._connect() as db:
            if db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
                raise ArchiveBlocked("Archive integrity check failed")
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM archive_entries WHERE record_id=? ORDER BY entry_id",
                              (record_id,)).fetchall()
        if not rows:
            raise ArchiveBlocked("Archive record missing")
        entries = []
        previous = None
        for index, row in enumerate(rows):
            record = json.loads(row["record_json"])
            if canonical_bytes(record) != row["record_json"]:
                raise ArchiveBlocked("Archive canonical record changed")
            _validate_record(record, self.validator)
            raw, parsed_bytes = row["raw_response"], row["parsed_json"]
            phase = "GENERATION" if index == 0 else "EVALUATION"
            if row["phase"] != phase or row["previous_digest"] != previous:
                raise ArchiveBlocked("Archive phase or raw-response identity changed")
            _phase_integrity(record, phase, raw, parsed_bytes)
            if (row["ledger_request_digest"] != record["payload"]["provider_request_sha256"]
                    or phase == "EVALUATION" and record["human_evaluation"]["review_ref"] !=
                       f"ledger:{row['ledger_campaign_id']}:{record['evaluation_case_id']}:review"):
                raise ArchiveBlocked("Archive Ledger reference changed")
            calculated = self._entry_digest(
                record, raw, parsed_bytes, phase=phase, previous=previous,
                campaign_id=row["ledger_campaign_id"],
                request_digest=row["ledger_request_digest"],
                ledger_state=row["ledger_state_at_write"],
                provider_status=row["provider_status"],
                reviewed_at=row["reviewed_at_utc"], written_at=row["written_at_utc"])
            if calculated != row["entry_digest"]:
                raise ArchiveBlocked("Archive audit digest mismatch")
            if index and (record["record_id"] != entries[0].record["record_id"]
                          or record["run"] != entries[0].record["run"]
                          or record["brief"] != entries[0].record["brief"]
                          or record["payload"] != entries[0].record["payload"]
                          or record["token_count"] != entries[0].record["token_count"]
                          or any(record["generation"][name] != entries[0].record["generation"][name]
                                 for name in ("status", "raw_output_ref", "raw_output_sha256",
                                              "returned_model_id", "request_id", "usage",
                                              "timestamp_utc"))
                          or any(entries[0].record["generation"][name] is not None
                                 and record["generation"][name] != entries[0].record["generation"][name]
                                 for name in ("actual_charge_usd", "charge_source"))):
                raise ArchiveBlocked("Evaluation altered immutable generation lineage")
            entries.append(ArchiveEntry(
                row["entry_id"], phase, calculated, record,
                raw if phase == "GENERATION" else entries[0].raw_response,
                json.loads(parsed_bytes) if parsed_bytes is not None else None,
                row["ledger_campaign_id"], row["ledger_state_at_write"],
                row["provider_status"], row["reviewed_at_utc"]))
            previous = calculated
        return tuple(entries)
