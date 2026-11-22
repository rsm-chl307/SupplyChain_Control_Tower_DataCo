"""Offline P5-D quality rubric tests with trusted synthetic Briefs only."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import unittest

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.quality_evaluation import (
    DIMENSIONS, Adjudication, CampaignResult, EvaluationBlocked, HumanReview,
    TechnicalAssessment, aggregate_campaign, assess_technical, score_case,
)
from src.synthetic_context import SyntheticHarness


CASES = Path(__file__).resolve().parents[1] / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json"


def review(name: str, score: int = 5, *, critical=(), met=True) -> HumanReview:
    return HumanReview(name, {d: score for d in DIMENSIONS},
                       {d: "Reviewed source-backed synthetic evidence." for d in DIMENSIONS},
                       tuple(critical), (), met, "Case-specific expectations were checked.")


def response(reviewed, refs: list[str], numeric_ref: str, field: str) -> bytes:
    brief = reviewed.verify()
    record = next(r for section in ("capacity_analysis", "service_analysis", "inventory_analysis",
                                    "risk_analysis", "scenario_comparison")
                  for r in brief[section]["records"] if r["source_ref"] == numeric_ref)
    source = next(s for s in brief["source_manifest"] if s["source_ref_id"] == numeric_ref)
    value = record["values"][field]
    if record["kind"] == "comparison_metric":
        unit = record["values"]["Unit"]
    elif field.endswith("Rate") or field == "Capacity_Utilization":
        unit = "ratio"
    elif "Workload" in field:
        unit = record["values"].get("Workload_Unit", "EqWU")
    else:
        unit = record["values"].get("Quantity_Unit", brief["data_scope"]["Quantity_Unit"])
    item = {
        "response_version": "1.0", "brief_digest": reviewed.content_digest,
        "executive_assessment": {"summary": "Review the selected published evidence.",
                                 "principal_concern": "Interpretation needs human review.",
                                 "evidence_refs": refs},
        "key_findings": [{"finding_id": "F1", "description": "Published evidence supports review.",
                          "evidence_refs": [numeric_ref],
                          "numerical_evidence": [{"source_ref_id": numeric_ref, "field_name": field,
                                                  "value": value, "unit": unit,
                                                  "grain": source["native_grain"]}],
                          "potential_operational_impact": "Bounded synthetic planning context.",
                          "severity": "Low", "severity_rationale": "No automatic action."}],
        "root_cause_interpretation": {key: [] for key in (
            "observed_facts", "system_identified_drivers", "ai_interpretations",
            "unverified_hypotheses", "missing_evidence")},
        "recommendations": [], "decision_trade_offs": [], "further_investigation": [],
        "limitations_and_confidence": {
            "data_completeness": "Selected synthetic evidence only.",
            "evidence_quality": "Locally validated source.",
            "directly_supported_conclusions": [], "inferences": [],
            "unsupported_questions": [], "confidence": "Limited",
            "confidence_rationale": "Human review remains necessary."},
    }
    return json.dumps(item, sort_keys=True).encode()


class P5QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(CASES.read_text())
        cls.original = SyntheticHarness()
        cls.low = SyntheticHarness(fixture_id="p5_low_risk_v1")
        cls.case = cls.dataset["cases"][0]
        cls.low_case = cls.dataset["cases"][-1]
        cls.brief = prepare_brief(cls.original, cls.original.issue("Baseline"), max_records=2).review
        cls.low_brief = prepare_brief(cls.low, cls.low.issue("Baseline"), max_records=4).review
        cls.request = build_request(cls.brief, model_snapshot="offline-test-snapshot",
                                    max_output_tokens=500, timeout_seconds=10)
        cls.low_request = build_request(cls.low_brief, model_snapshot="offline-test-snapshot",
                                        max_output_tokens=500, timeout_seconds=10)
        assert cls.brief is not None and cls.low_brief is not None

    @classmethod
    def tearDownClass(cls):
        cls.original.close()
        cls.low.close()

    def packet(self, *, low=False, refs=None, raw=None):
        case = self.low_case if low else self.case
        brief = self.low_brief if low else self.brief
        request = self.low_request if low else self.request
        refs = refs if refs is not None else sorted({x["source_ref"] for x in case["evidence"]})
        if raw is None:
            raw = response(brief, refs, case["numerical_slot_ref"], case["numerical_slot_field"])
        return assess_technical(case, dataset_version=self.dataset["dataset_version"],
                                campaign_id="offline-test-campaign", review=brief,
                                request=request, raw_response=raw, provider_status="SUCCEEDED")

    def result(self, packet=None, score=5, critical=(), met=True):
        packet = packet or self.packet()
        a, b, final = review("analyst-a", score), review("analyst-b", score), review("final", score,
                                                                                     critical=critical, met=met)
        return score_case(packet, a, b, Adjudication("owner-adjudicator", final, ""))

    def test_all_dimensions_and_exact_weighted_extremes(self):
        packet = self.packet()
        maximum = self.result(packet, 5)
        minimum = self.result(packet, 1)
        self.assertEqual(len(DIMENSIONS), 6)
        self.assertEqual(maximum.score, Decimal(100))
        self.assertEqual(maximum.status, "PASS")
        self.assertEqual(minimum.score, Decimal(20))
        self.assertEqual(minimum.status, "FAIL")
        mixed = review("mixed", 5)
        values = dict(mixed.scores)
        values["communication_quality"] = 4
        mixed = replace(mixed, scores=values)
        result = score_case(packet, review("a"), review("b"),
                            Adjudication("owner", mixed, "Communication reduced after review."))
        self.assertEqual(result.score, Decimal(98))

    def test_invalid_missing_and_noninteger_scores_rejected(self):
        for value in (0, 6, 3.5, True, None):
            with self.subTest(value=value):
                item = review("r")
                scores = dict(item.scores)
                scores["factual_accuracy"] = value
                with self.assertRaises(EvaluationBlocked):
                    replace(item, scores=scores).validate()
        item = review("r")
        with self.assertRaises(EvaluationBlocked):
            replace(item, scores={"factual_accuracy": 5}).validate()
        with self.assertRaises(EvaluationBlocked):
            replace(item, rationales={}).validate()
        self.assertEqual(score_case(self.packet(), None, None, None).status, "INCOMPLETE")

    def test_critical_failure_and_low_risk_restraint_override(self):
        self.assertEqual(self.result(critical=("FABRICATED_NUMBER",)).status, "FAIL")
        low = self.packet(low=True)
        self.assertEqual(low.p1_status, "VALIDATED")
        self.assertEqual(low.missing_expected_refs, ())
        self.assertEqual(self.result(low).status, "PASS")
        self.assertEqual(self.result(low, critical=("LOW_RISK_FALSE_ESCALATION",)).status, "FAIL")
        self.assertEqual(self.result(low, met=False).status, "FAIL")

    def test_missing_expected_evidence_and_unstructured_quantity(self):
        missing = self.packet(low=True, refs=["s14"])
        self.assertTrue(missing.missing_expected_refs)
        self.assertEqual(self.result(missing).status, "FAIL")
        raw = response(self.brief, ["s7"], "s7", "Capacity_Utilization")
        changed = json.loads(raw)
        changed["executive_assessment"]["summary"] = "Capacity rose by seven units."
        packet = self.packet(raw=json.dumps(changed).encode())
        self.assertEqual(packet.p1_status, "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(score_case(packet, review("a"), review("b"),
                                    Adjudication("owner", review("final"), "")).status, "INCOMPLETE")

    def test_reviewer_disagreement_requires_adjudication(self):
        packet = self.packet()
        with self.assertRaises(EvaluationBlocked):
            score_case(packet, review("a", 5), review("b", 4),
                       Adjudication("owner", review("final", 5), ""))
        accepted = score_case(packet, review("a", 5), review("b", 4),
                              Adjudication("owner", review("final", 5), "Reviewed disagreement."))
        self.assertEqual(accepted.status, "PASS")
        with self.assertRaises(EvaluationBlocked):
            score_case(packet, review("same"), review("same"),
                       Adjudication("owner", review("final"), ""))

    def test_campaign_coverage_mean_critical_and_deterministic_export(self):
        base = self.result()
        results = tuple(replace(base, provenance=replace(base.provenance, case_id=case_id))
                        for case_id in ("EV-01", "EV-02", "EV-03", "EV-04", "EV-05", "EV-06", "EV-07", "EV-08-LR"))
        campaign = aggregate_campaign(results)
        self.assertEqual(campaign.status, "PASS")
        self.assertEqual(campaign.mean_score, Decimal(100))
        self.assertEqual(campaign.as_json(), aggregate_campaign(tuple(reversed(results))).as_json())
        boundary = self.result(score=4)
        self.assertEqual(boundary.score, Decimal(80))
        self.assertEqual(boundary.status, "PASS")
        self.assertEqual(aggregate_campaign(tuple(replace(boundary, provenance=replace(
            boundary.provenance, case_id=case_id)) for case_id in (
            "EV-01", "EV-02", "EV-03", "EV-04", "EV-05", "EV-06", "EV-07", "EV-08-LR"))).status,
            "PASS WITH LIMITATIONS")
        limited_scores = {d: 4 for d in DIMENSIONS}
        limited_scores["communication_quality"] = 3
        limited_final = replace(review("final", 4), scores=limited_scores)
        limited = score_case(self.packet(), review("a", 4), review("b", 4),
                             Adjudication("owner", limited_final, "Communication needs revision."))
        self.assertEqual(limited.score, Decimal(78))
        self.assertEqual(limited.status, "PASS WITH LIMITATIONS")
        self.assertEqual(aggregate_campaign(results[:-1] + (replace(
            limited, provenance=replace(limited.provenance, case_id="EV-08-LR")),)).status,
            "PASS WITH LIMITATIONS")
        self.assertIn("final_rationales", campaign.as_json())
        self.assertEqual(aggregate_campaign(results[:-1]).status, "INCOMPLETE")
        bad = replace(results[-1], status="FAIL", critical_failures=("UNSUPPORTED_FACT",))
        self.assertEqual(aggregate_campaign(results[:-1] + (bad,)).status, "FAIL")
        technical_fail = replace(results[-1], technical_status="VALIDATION_FAILED",
                                 score=None, status="FAIL", reviewer_ids=None,
                                 adjudicator_id=None, final_scores=None, final_rationales=None,
                                 case_requirements_met=None)
        self.assertEqual(aggregate_campaign(results[:-1] + (technical_fail,)).status, "FAIL")
        with self.assertRaises(EvaluationBlocked):
            aggregate_campaign((results[0], results[0]))
        forged = replace(results[-1], reviewer_ids=None)
        with self.assertRaises(EvaluationBlocked):
            aggregate_campaign(results[:-1] + (forged,))
        forged_score = replace(results[-1], score=Decimal(99))
        with self.assertRaises(EvaluationBlocked):
            aggregate_campaign(results[:-1] + (forged_score,))
        low_factual = {d: 5 for d in DIMENSIONS}
        low_factual["factual_accuracy"] = 3
        forged_limited = replace(results[-1], final_scores=low_factual,
                                 score=Decimal(90), status="PASS WITH LIMITATIONS")
        with self.assertRaises(EvaluationBlocked):
            aggregate_campaign(results[:-1] + (forged_limited,))
        with self.assertRaises(EvaluationBlocked):
            aggregate_campaign(results[:-1] + (replace(results[-1], status="PASS WITH LIMITATIONS"),))

    def test_unsupported_claim_prevents_clean_pass(self):
        packet = self.packet()
        final = replace(review("final"), unsupported_claims=("Unverified causal assertion.",))
        result = score_case(packet, review("a"), review("b"),
                            Adjudication("owner", final, "Reviewed claim as noncritical."))
        self.assertEqual(result.status, "PASS WITH LIMITATIONS")

    def test_stale_request_and_wrong_case_provenance_rejected(self):
        changed = replace(self.request, request_digest="0" * 64)
        with self.assertRaises(Exception):
            assess_technical(self.case, dataset_version=self.dataset["dataset_version"],
                             campaign_id="offline-test-campaign", review=self.brief,
                             request=changed, raw_response=b"{}", provider_status="SUCCEEDED")
        with self.assertRaises(EvaluationBlocked):
            assess_technical(self.low_case, dataset_version=self.dataset["dataset_version"],
                             campaign_id="offline-test-campaign", review=self.brief,
                             request=self.request, raw_response=b"{}", provider_status="SUCCEEDED")
        changed_case = dict(self.case)
        changed_case["evidence"] = []
        with self.assertRaises(EvaluationBlocked):
            assess_technical(changed_case, dataset_version=self.dataset["dataset_version"],
                             campaign_id="offline-test-campaign", review=self.brief,
                             request=self.request, raw_response=b"{}", provider_status="SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
