"""Deterministic, offline human quality scoring for P5 synthetic responses.

This module does not call a provider, approve spending, or judge prose with an LLM.
P1 technical validation is an independent gate before human scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Mapping

from src.ai_brief.validation import ValidatedBrief, resolve_source
from src.ai_copilot.approval import verify_request
from src.ai_copilot.eight_call_campaign import CASE_IDS
from src.ai_copilot.provider import ProviderRequest, build_request
from src.ai_copilot.response_contract import classify_response


POLICY_VERSION = "p5-quality-proposal-1"
CORPUS_VERSION = "p5-offline-evaluation-2"
CORPUS_SHA256 = "08a34585b1cb819c82093adb4828734cb05507ea6b6cd6448efc5cc0d819ff50"
DIMENSIONS = (
    "factual_accuracy", "root_cause_analysis", "recommendation_quality",
    "decision_trade_off", "context_risk_awareness", "communication_quality",
)
WEIGHTS = (25, 20, 20, 15, 10, 10)
CRITICAL_CATEGORIES = frozenset({
    "FABRICATED_NUMBER", "FABRICATED_EVIDENCE", "DETERMINISTIC_CONTRADICTION",
    "UNSUPPORTED_FACT", "CONFIRMED_CAUSE_WITHOUT_PROOF", "PROHIBITED_ACTION",
    "MATERIAL_LIMITATION_OMITTED", "WRONG_RUN_SCENARIO", "LOW_RISK_FALSE_ESCALATION",
})


class EvaluationBlocked(ValueError):
    pass


def _registered_case(case: dict, dataset_version: str) -> None:
    """Verify the fixed synthetic corpus; callers cannot replace expectations."""
    if dataset_version != CORPUS_VERSION or type(case) is not dict:
        raise EvaluationBlocked("Approved offline corpus version required")
    path = Path(__file__).resolve().parents[2] / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 200000:
                raise EvaluationBlocked("Offline corpus file is unsafe")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(200001)
        finally:
            os.close(fd)
        if hashlib.sha256(raw).hexdigest() != CORPUS_SHA256:
            raise EvaluationBlocked("Offline corpus bytes changed")
        data = json.loads(raw)
        if (data.get("dataset_version") != CORPUS_VERSION
                or [c["id"] for c in data["cases"]] != list(CASE_IDS)
                or next((c for c in data["cases"] if c["id"] == case.get("id")), None) != case):
            raise EvaluationBlocked("Case does not match pinned corpus")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EvaluationBlocked("Pinned offline corpus unavailable or invalid") from exc


def _hex64(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _text(value: str, name: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 1000:
        raise EvaluationBlocked(f"{name} needs a bounded explicit value")


@dataclass(frozen=True)
class Provenance:
    campaign_id: str
    dataset_version: str
    corpus_digest: str
    case_id: str
    case_version: str
    brief_digest: str
    projection_digest: str
    request_digest: str
    response_digest: str | None
    model_snapshot: str
    schema_version: str
    instructions_version: str
    privacy_version: str
    max_output_tokens: int
    timeout_seconds: float

    def validate(self) -> None:
        for name in ("campaign_id", "dataset_version", "case_version", "model_snapshot",
                     "schema_version", "instructions_version", "privacy_version"):
            _text(getattr(self, name), name)
        if self.case_id not in CASE_IDS:
            raise EvaluationBlocked("Unknown evaluation case")
        for name in ("corpus_digest", "brief_digest", "projection_digest", "request_digest"):
            if not _hex64(getattr(self, name)):
                raise EvaluationBlocked("Invalid provenance digest")
        if self.response_digest is not None and not _hex64(self.response_digest):
            raise EvaluationBlocked("Invalid response digest")
        if (type(self.max_output_tokens) is not int or self.max_output_tokens <= 0
                or type(self.timeout_seconds) not in (int, float) or self.timeout_seconds <= 0):
            raise EvaluationBlocked("Invalid request limits")


@dataclass(frozen=True)
class TechnicalAssessment:
    provenance: Provenance
    p1_status: str
    cited_refs: tuple[str, ...]
    missing_expected_refs: tuple[str, ...]
    raw_response: bytes | None = field(repr=False)
    # The exact raw bytes are retained locally; machine-readable exports use its digest.


def assess_technical(case: dict, *, dataset_version: str, campaign_id: str,
                     review: ValidatedBrief, request: ProviderRequest,
                     raw_response: bytes | None, provider_status: str) -> TechnicalAssessment:
    """Build provenance from a live Brief and actual P1 result; no reviewer score."""
    if type(review) is not ValidatedBrief or type(request) is not ProviderRequest:
        raise EvaluationBlocked("Live validated Brief and request required")
    if type(case) is not dict or case.get("id") not in CASE_IDS or not case.get("case_version"):
        raise EvaluationBlocked("Versioned eight-case definition required")
    _registered_case(case, dataset_version)
    _text(dataset_version, "dataset_version")
    _text(campaign_id, "campaign_id")
    rebuilt = build_request(review, model_snapshot=request.model_snapshot,
                            max_output_tokens=request.max_output_tokens,
                            timeout_seconds=request.timeout_seconds)
    verify_request(request)
    if rebuilt != request:
        raise EvaluationBlocked("Brief or request provenance changed")
    brief = review.verify()
    if brief["run_context"]["Scenario"] != case.get("scenario"):
        raise EvaluationBlocked("Case scenario differs from trusted Brief")
    if (review._draft.max_records != case.get("max_records")
            or bool(brief["run_context"]["Comparison_ID"]) != case.get("comparison")
            or review._draft._bundle._harness._fixture_id != case.get("fixture_id")):
        raise EvaluationBlocked("Case selection or fixture differs from trusted Brief")
    for item in case.get("evidence", ()):
        ref, field = item["source_ref"], item["field"]
        value, _ = resolve_source(review, ref, field)
        if value != item["expected"]:
            raise EvaluationBlocked("Case expectation differs from trusted evidence")
    outcome = classify_response(raw_response, review, provider_status=provider_status)
    cited: set[str] = set()
    if outcome.response is not None:
        def walk(node):
            if isinstance(node, dict):
                if "evidence_refs" in node:
                    cited.update(node["evidence_refs"])
                if "numerical_evidence" in node:
                    cited.update(s["source_ref_id"] for s in node["numerical_evidence"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(outcome.response)
    expected = {item["source_ref"] for item in case.get("evidence", ())}
    provenance = Provenance(
        campaign_id, dataset_version, CORPUS_SHA256, case["id"], case["case_version"],
        review.content_digest, request.provider_brief_digest, request.request_digest,
        hashlib.sha256(raw_response).hexdigest() if raw_response is not None else None,
        request.model_snapshot, request.schema_version, request.instructions_version,
        request.privacy_version, request.max_output_tokens, request.timeout_seconds,
    )
    provenance.validate()
    return TechnicalAssessment(provenance, outcome.status, tuple(sorted(cited)),
                               tuple(sorted(expected - cited)), raw_response)


@dataclass(frozen=True)
class HumanReview:
    reviewer_id: str
    scores: Mapping[str, int]
    rationales: Mapping[str, str]
    critical_failures: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    case_requirements_met: bool
    case_rationale: str

    def validate(self) -> None:
        _text(self.reviewer_id, "reviewer_id")
        _text(self.case_rationale, "case_rationale")
        if type(self.case_requirements_met) is not bool:
            raise EvaluationBlocked("Case requirement judgment is missing")
        if set(self.scores) != set(DIMENSIONS) or set(self.rationales) != set(DIMENSIONS):
            raise EvaluationBlocked("All six dimension scores and rationales are required")
        for dimension in DIMENSIONS:
            if type(self.scores[dimension]) is not int or not 1 <= self.scores[dimension] <= 5:
                raise EvaluationBlocked("Dimension score must be an integer from 1 to 5")
            _text(self.rationales[dimension], dimension + " rationale")
        if any(item not in CRITICAL_CATEGORIES for item in self.critical_failures):
            raise EvaluationBlocked("Unknown critical failure category")
        for item in self.unsupported_claims:
            _text(item, "unsupported_claim")


@dataclass(frozen=True)
class Adjudication:
    adjudicator_id: str
    final: HumanReview
    disagreement_resolution: str

    def validate(self, first: HumanReview, second: HumanReview) -> None:
        _text(self.adjudicator_id, "adjudicator_id")
        self.final.validate()
        if self.adjudicator_id in {first.reviewer_id, second.reviewer_id}:
            raise EvaluationBlocked("Independent adjudicator required")
        differs = (dict(first.scores) != dict(second.scores)
                   or first.critical_failures != second.critical_failures
                   or first.unsupported_claims != second.unsupported_claims
                   or first.case_requirements_met != second.case_requirements_met)
        if differs:
            _text(self.disagreement_resolution, "disagreement_resolution")
        if ((set(first.critical_failures) | set(second.critical_failures)) - set(self.final.critical_failures)
                or (set(first.unsupported_claims) | set(second.unsupported_claims)) - set(self.final.unsupported_claims)):
            # A reviewer flag may be dismissed only with an explicit adjudication note.
            if not self.disagreement_resolution.strip():
                raise EvaluationBlocked("Critical-failure dismissal needs explanation")


@dataclass(frozen=True)
class CaseResult:
    provenance: Provenance
    technical_status: str
    score: Decimal | None
    status: str
    critical_failures: tuple[str, ...]
    missing_expected_refs: tuple[str, ...]
    reviewer_ids: tuple[str, str] | None
    adjudicator_id: str | None
    final_scores: Mapping[str, int] | None
    final_rationales: Mapping[str, str] | None
    unsupported_claims: tuple[str, ...]
    case_requirements_met: bool | None
    adjudication_note: str | None

    def as_record(self) -> dict:
        """Stable machine-readable summary; raw response stays in local evidence."""
        from dataclasses import asdict
        value = asdict(self)
        value["score"] = str(self.score) if self.score is not None else None
        return value


def _quality_status(score: Decimal, critical: tuple[str, ...], missing_refs: tuple[str, ...],
                    requirements_met: bool, scores: Mapping[str, int],
                    unsupported_claims: tuple[str, ...]) -> str:
    if critical or missing_refs or not requirements_met or scores["factual_accuracy"] < 4:
        return "FAIL"
    if (score >= 80 and all(scores[d] >= 3 for d in DIMENSIONS)
            and not unsupported_claims):
        return "PASS"
    if score >= 75:
        return "PASS WITH LIMITATIONS"
    return "FAIL"


def score_case(technical: TechnicalAssessment, first: HumanReview | None,
               second: HumanReview | None, decision: Adjudication | None) -> CaseResult:
    p = technical.provenance
    p.validate()
    if technical.p1_status not in {"VALIDATED", "HUMAN_REVIEW_REQUIRED", "VALIDATION_FAILED",
                                   "REFUSED", "INCOMPLETE", "DEFINITIVE_ERROR", "UNKNOWN_OUTCOME"}:
        raise EvaluationBlocked("Unknown P1 outcome")
    if technical.p1_status != "VALIDATED":
        status = "INCOMPLETE" if technical.p1_status in {"HUMAN_REVIEW_REQUIRED", "INCOMPLETE", "UNKNOWN_OUTCOME"} else "FAIL"
        return CaseResult(p, technical.p1_status, None, status, (),
                          technical.missing_expected_refs, None, None, None, None, (), None, None)
    if first is None or second is None or decision is None:
        return CaseResult(p, technical.p1_status, None, "INCOMPLETE", (),
                          technical.missing_expected_refs, None, None, None, None, (), None, None)
    first.validate()
    second.validate()
    if first.reviewer_id == second.reviewer_id:
        raise EvaluationBlocked("Two independent reviewers required")
    decision.validate(first, second)
    final = decision.final
    score = sum((Decimal(weight) * Decimal(final.scores[dimension]) / Decimal(5)
                 for dimension, weight in zip(DIMENSIONS, WEIGHTS)), Decimal(0))
    critical = tuple(sorted(set(final.critical_failures)))
    status = _quality_status(score, critical, technical.missing_expected_refs,
                             final.case_requirements_met, final.scores, final.unsupported_claims)
    return CaseResult(p, technical.p1_status, score, status, critical,
                      technical.missing_expected_refs,
                      (first.reviewer_id, second.reviewer_id), decision.adjudicator_id,
                      dict(final.scores), dict(final.rationales), final.unsupported_claims,
                      final.case_requirements_met,
                      decision.disagreement_resolution)


@dataclass(frozen=True)
class CampaignResult:
    status: str
    mean_score: Decimal | None
    case_results: tuple[CaseResult, ...]

    def as_json(self) -> str:
        return json.dumps({"policy_version": POLICY_VERSION, "status": self.status,
                           "mean_score": str(self.mean_score) if self.mean_score is not None else None,
                           "cases": [r.as_record() for r in self.case_results]},
                          sort_keys=True, separators=(",", ":"))


def aggregate_campaign(results: tuple[CaseResult, ...]) -> CampaignResult:
    if type(results) is not tuple or any(type(r) is not CaseResult for r in results):
        raise EvaluationBlocked("Explicit case results required")
    ids = [r.provenance.case_id for r in results]
    if len(set(ids)) != len(ids) or any(i not in CASE_IDS for i in ids):
        raise EvaluationBlocked("Duplicate or unknown case result")
    ordered = tuple(sorted(results, key=lambda r: CASE_IDS.index(r.provenance.case_id)))
    for result in ordered:
        result.provenance.validate()
        if result.status not in {"PASS", "PASS WITH LIMITATIONS", "FAIL", "INCOMPLETE"}:
            raise EvaluationBlocked("Invalid case verdict")
        if result.status != "INCOMPLETE" and result.score is not None:
            if (result.technical_status != "VALIDATED" or result.reviewer_ids is None
                    or len(set(result.reviewer_ids)) != 2 or not result.adjudicator_id
                    or result.adjudicator_id in result.reviewer_ids
                    or result.final_scores is None or result.final_rationales is None
                    or result.case_requirements_met is None
                    or set(result.final_scores) != set(DIMENSIONS)
                    or set(result.final_rationales) != set(DIMENSIONS)
                    or any(type(result.final_scores[d]) is not int
                           or not 1 <= result.final_scores[d] <= 5
                           or not result.final_rationales[d].strip() for d in DIMENSIONS)):
                raise EvaluationBlocked("Complete independent adjudication required")
            calculated = sum((Decimal(weight) * Decimal(result.final_scores[d]) / Decimal(5)
                              for d, weight in zip(DIMENSIONS, WEIGHTS)), Decimal(0))
            if calculated != result.score:
                raise EvaluationBlocked("Case score differs from adjudicated dimensions")
            expected_status = _quality_status(result.score, result.critical_failures,
                                              result.missing_expected_refs,
                                              result.case_requirements_met, result.final_scores,
                                              result.unsupported_claims)
            if result.status != expected_status:
                raise EvaluationBlocked("Case verdict contradicts quality gates")
    if ordered:
        campaigns = {r.provenance.campaign_id for r in ordered}
        versions = {r.provenance.dataset_version for r in ordered}
        if len(campaigns) != 1 or len(versions) != 1:
            raise EvaluationBlocked("Mixed campaign or dataset provenance")
    if any(r.status == "FAIL" or r.critical_failures for r in ordered):
        if set(ids) != set(CASE_IDS) or any(r.score is None for r in ordered):
            return CampaignResult("FAIL", None, ordered)
    if set(ids) != set(CASE_IDS) or any(r.status == "INCOMPLETE" or r.score is None for r in ordered):
        return CampaignResult("INCOMPLETE", None, ordered)
    mean = sum((r.score for r in ordered), Decimal(0)) / Decimal(8)
    if any(r.status == "FAIL" or r.critical_failures for r in ordered):
        status = "FAIL"
    elif all(r.status == "PASS" for r in ordered) and mean >= 85:
        status = "PASS"
    elif mean >= 80 and all(r.score >= 75 for r in ordered):
        status = "PASS WITH LIMITATIONS"
    else:
        status = "FAIL"
    return CampaignResult(status, mean, ordered)
