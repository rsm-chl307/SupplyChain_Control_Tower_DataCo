"""Closed advisory response contract and evidence-bound offline validation."""
import json
import math
import re
from dataclasses import dataclass
from jsonschema import Draft202012Validator
from src.ai_brief.validation import ValidatedBrief
from src.ai_brief.contract import canonical_bytes

VERSION = "1.0"
MAX_RESPONSE_BYTES = 32768

def obj(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}

def arr(item, maximum):
    return {"type": "array", "items": item, "maxItems": maximum}

TEXT = {"type": "string", "minLength": 1, "maxLength": 500}
SHORT = {"type": "string", "minLength": 1, "maxLength": 160}
REF = {"type": "string", "pattern": "^s[1-9][0-9]*$"}
REFS = arr(REF, 8)
EVIDENCE = obj({"source_ref_id": REF, "field_name": SHORT, "value": {"type": "number"},
                "unit": SHORT, "grain": SHORT})
CLAIM = obj({"text": TEXT, "evidence_refs": REFS})
FINDING = obj({"finding_id": {"type": "string", "pattern": "^F[1-5]$"},
               "description": TEXT, "evidence_refs": REFS,
               "numerical_evidence": arr(EVIDENCE, 6),
               "potential_operational_impact": TEXT,
               "severity": {"enum": ["High", "Medium", "Low"]},
               "severity_rationale": TEXT})
RECOMMENDATION = obj({"recommendation_id": {"type": "string", "pattern": "^A[1-3]$"},
                      "priority": {"enum": ["High", "Medium", "Low"]},
                      "proposed_action": TEXT, "rationale": TEXT,
                      "expected_impact": TEXT, "trade_offs": TEXT,
                      "required_validation": TEXT, "evidence_refs": REFS})
TRADEOFF = obj({"description": TEXT, "evidence_refs": REFS,
                "comparability": {"enum": ["COMPARABLE", "DESCRIPTIVE_ONLY", "BLOCKED", "UNAVAILABLE"]}})
QUESTION = obj({"question": TEXT, "reason": TEXT, "missing_evidence": TEXT})
SCHEMA = obj({
    "response_version": {"enum": [VERSION]},
    "brief_digest": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "executive_assessment": obj({"summary": TEXT, "principal_concern": TEXT, "evidence_refs": REFS}),
    "key_findings": arr(FINDING, 5),
    "root_cause_interpretation": obj({
        "observed_facts": arr(CLAIM, 5), "system_identified_drivers": arr(CLAIM, 5),
        "ai_interpretations": arr(CLAIM, 5), "unverified_hypotheses": arr(CLAIM, 5),
        "missing_evidence": arr(CLAIM, 5)}),
    "recommendations": arr(RECOMMENDATION, 3),
    "decision_trade_offs": arr(TRADEOFF, 5),
    "further_investigation": arr(QUESTION, 5),
    "limitations_and_confidence": obj({
        "data_completeness": TEXT, "evidence_quality": TEXT,
        "directly_supported_conclusions": arr(CLAIM, 5),
        "inferences": arr(CLAIM, 5), "unsupported_questions": arr(SHORT, 5),
        "confidence": {"enum": ["Limited", "Moderate", "Strong"]},
        "confidence_rationale": TEXT})})
VALIDATOR = Draft202012Validator(SCHEMA)

class ResponseRejected(ValueError):
    pass


class ResponseNeedsReview(ResponseRejected):
    """Free-text quantity or claim needs a human; no advisory success."""
    pass


QUANTITY_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|"
    r"fifty|sixty|seventy|eighty|ninety|dozen|hundred|thousand|million|billion|"
    r"half|quarter|third|twice|double|doubled|triple|tripled|"
    r"percent|percentage|per\s+cent)\b|百分之|[一二三四五六七八九十百千萬億]+(?:成|倍|個|週)",
    re.IGNORECASE,
)

@dataclass(frozen=True)
class ResponseOutcome:
    status: str
    response: dict | None = None
    reason: str | None = None


def _unit(record, field, brief):
    values = record["values"]
    if record["kind"] == "comparison_metric":
        return values["Unit"]
    if field.endswith("Rate") or field == "Capacity_Utilization":
        return "ratio"
    if "Workload" in field or field == "Capacity_Reduction_From_Baseline":
        units = {r["values"]["Workload_Unit"] for r in brief["capacity_analysis"]["records"]
                 if r["kind"] == "pool"}
        return values.get("Workload_Unit") or (next(iter(units)) if len(units) == 1 else None)
    return values.get("Quantity_Unit") or brief["data_scope"]["Quantity_Unit"]


def validate_response(raw: bytes, review: ValidatedBrief) -> dict:
    """Reject unsupported evidence and prose numbers; never repair a paid response."""
    if type(review) is not ValidatedBrief:
        raise ResponseRejected("Validator-issued Brief required")
    brief = review.verify()
    if type(raw) is not bytes or len(raw) > MAX_RESPONSE_BYTES:
        raise ResponseRejected("Response size or type invalid")
    try:
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ResponseRejected("Duplicate JSON field")
                result[key] = value
            return result
        response = json.loads(raw, object_pairs_hook=unique_pairs)
        canonical_bytes(response)  # rejects non-finite JSON values
    except (ValueError, UnicodeDecodeError) as exc:
        raise ResponseRejected("Malformed response") from exc
    errors = list(VALIDATOR.iter_errors(response))
    if errors:
        raise ResponseRejected("Response schema invalid")
    if response["brief_digest"] != review.content_digest:
        raise ResponseRejected("Brief digest mismatch")
    refs = {}
    for section in ("run_context", "data_scope"):
        refs[brief[section]["source_ref"]] = (None, brief[section])
    for section, envelope in brief.items():
        if isinstance(envelope, dict) and "records" in envelope:
            for record in envelope["records"]:
                refs[record["source_ref"]] = (section, record)
    def check_ref(ref):
        if ref not in refs:
            raise ResponseRejected("Unknown evidence reference")
        section, record = refs[ref]
        if section and (not record or brief[section]["availability"] == "NOT_AVAILABLE"):
            raise ResponseRejected("Unavailable evidence")
    def walk(node, key=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "evidence_refs":
                    for ref in v: check_ref(ref)
                elif k == "numerical_evidence":
                    for slot in v:
                        ref = slot["source_ref_id"]
                        check_ref(ref)
                        section, record = refs[ref]
                        values = record["values"] if section else record
                        field = slot["field_name"]
                        source = next((s for s in brief["source_manifest"] if s["source_ref_id"] == ref), None)
                        value = values.get(field)
                        if (source is None or field not in source["field_names"] or type(value) not in (int, float)
                            or isinstance(value, bool) or slot["value"] != value
                            or slot["grain"] != source["native_grain"]
                            or (section and slot["unit"] != _unit(record, field, brief))):
                            raise ResponseRejected("Numerical evidence mismatch")
                else: walk(v, k)
        elif isinstance(node, list):
            for item in node: walk(item, key)
        elif isinstance(node, str) and key not in {"brief_digest", "source_ref_id", "field_name", "unit", "grain", "finding_id", "recommendation_id", "response_version"}:
            if "<" in node or ">" in node or "```" in node or "http" in node.lower():
                raise ResponseRejected("Unsafe response text")
            if key in {"text", "summary", "principal_concern", "description", "potential_operational_impact", "severity_rationale", "proposed_action", "rationale", "expected_impact", "trade_offs", "required_validation", "question", "reason", "missing_evidence", "data_completeness", "evidence_quality", "confidence_rationale"} and (re.search(r"\d", node) or QUANTITY_WORDS.search(node)):
                raise ResponseNeedsReview("Unstructured quantity requires human review")
    walk(response)
    if len({x["finding_id"] for x in response["key_findings"]}) != len(response["key_findings"]):
        raise ResponseRejected("Duplicate finding IDs")
    if len({x["recommendation_id"] for x in response["recommendations"]}) != len(response["recommendations"]):
        raise ResponseRejected("Duplicate recommendation IDs")
    if response["decision_trade_offs"] and brief["run_context"]["Comparison_ID"] is None:
        raise ResponseRejected("Comparison unavailable")
    return response


def classify_response(raw: bytes | None, review: ValidatedBrief, *, provider_status: str) -> ResponseOutcome:
    if provider_status in {"REFUSED", "INCOMPLETE", "DEFINITIVE_ERROR", "UNKNOWN_OUTCOME"}:
        return ResponseOutcome(provider_status, reason="No validated advisory response")
    if provider_status != "SUCCEEDED" or raw is None:
        return ResponseOutcome("VALIDATION_FAILED", reason="Provider result unavailable")
    try:
        return ResponseOutcome("VALIDATED", validate_response(raw, review))
    except ResponseNeedsReview:
        return ResponseOutcome("HUMAN_REVIEW_REQUIRED", reason="Unstructured quantity needs human review")
    except (ResponseRejected, ValueError):
        return ResponseOutcome("VALIDATION_FAILED", reason="Response failed local validation")
