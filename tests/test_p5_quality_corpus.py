"""Eight-case v2 corpus evidence against live trusted synthetic Briefs."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.ai_brief.adapter import load_context
from src.ai_brief.validation import resolve_source
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.eight_call_campaign import CASE_IDS
from src.ai_copilot.provider import build_request
from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results
from src.synthetic_context import SyntheticHarness


ROOT = Path(__file__).resolve().parents[1] / "docs/ai_copilot/p5_offline_evaluation"


class QualityCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = json.loads((ROOT / "cases.v1.json").read_text())
        cls.v2 = json.loads((ROOT / "cases.v2.json").read_text())
        cls.original = SyntheticHarness()
        cls.low = SyntheticHarness(fixture_id="p5_low_risk_v1")
        cls.outcomes = {}
        try:
            for case in cls.v2["cases"]:
                harness = cls.low if case["fixture_id"] == "p5_low_risk_v1" else cls.original
                key = (case["fixture_id"], case["scenario"], case["max_records"], case["comparison"])
                if key in cls.outcomes:
                    continue
                context = harness.issue(case["scenario"])
                comparison = None
                if case["comparison"]:
                    bundle = load_context(harness, context)
                    manifest, tables = bundle.manifest(), bundle.tables()
                    scope = ComparisonScope(tuple(manifest["Scope"]["Product_IDs"]),
                                            tuple(tables["initial_state"].Plant_ID.unique()),
                                            *manifest["Scope"]["Planning_Horizon"], (3,))
                    comparison = compare_published_results(
                        ComparisonInput(manifest, tables, "Baseline"),
                        ComparisonInput(manifest, tables, "Demand_Surge"), scope)
                cls.outcomes[key] = prepare_brief(harness, context, comparison=comparison,
                                                  max_records=case["max_records"])
        except BaseException:
            cls.original.close()
            cls.low.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.original.close()
        cls.low.close()

    def test_versioned_roster_preserves_seven_and_adds_genuine_low_risk(self):
        self.assertEqual(self.v2["dataset_version"], "p5-offline-evaluation-2")
        self.assertEqual(tuple(c["id"] for c in self.v2["cases"]), CASE_IDS)
        self.assertEqual(len(self.v2["cases"]), 8)
        for original, revised in zip(self.v1["cases"][:7], self.v2["cases"][:7]):
            for key, value in original.items():
                self.assertEqual(revised[key], value)
        self.assertEqual(self.v1["cases"][-1]["id"], "EV-08")
        self.assertEqual(self.v2["cases"][-1]["fixture_id"], "p5_low_risk_v1")

    def test_all_expected_evidence_matches_live_briefs_and_requests(self):
        for case in self.v2["cases"]:
            with self.subTest(case=case["id"]):
                key = (case["fixture_id"], case["scenario"], case["max_records"], case["comparison"])
                outcome = self.outcomes[key]
                self.assertEqual(outcome.status, "VALIDATED")
                brief = outcome.review.verify()
                self.assertEqual(brief["run_context"]["Scenario"], case["scenario"])
                self.assertEqual(bool(brief["run_context"]["Comparison_ID"]), case["comparison"])
                self.assertTrue(case["expected_findings"])
                self.assertTrue(case["unsupported_conclusions"])
                for item in case["evidence"]:
                    record = next(r for r in brief[item["section"]]["records"]
                                  if r["source_ref"] == item["source_ref"])
                    self.assertEqual(record["kind"], item["kind"])
                    value, source = resolve_source(outcome.review, item["source_ref"], item["field"])
                    self.assertEqual(value, item["expected"])
                    self.assertIn(item["field"], source["field_names"])
                request = build_request(outcome.review, model_snapshot="offline-test-snapshot",
                                        max_output_tokens=500, timeout_seconds=10)
                self.assertEqual(request.brief_digest, outcome.review.content_digest)
                self.assertEqual(len(request.request_digest), 64)

    def test_low_risk_has_two_healthy_products_and_no_false_escalation_basis(self):
        case = self.v2["cases"][-1]
        outcome = self.outcomes[("p5_low_risk_v1", "Baseline", 4, False)]
        brief = outcome.review.verify()
        risk = [r for r in brief["risk_analysis"]["records"] if r["kind"] == "risk"]
        self.assertEqual(len(risk), 2)
        self.assertEqual({r["values"]["Risk_Category"] for r in risk}, {"Healthy"})
        self.assertTrue(all(r["values"]["Ending_Backlog"] == 0 for r in risk))
        self.assertTrue(all(r["values"]["Lost_Sales_Qty"] == 0 for r in risk))
        self.assertEqual(case["numerical_slot_ref"], "s14")


if __name__ == "__main__":
    unittest.main()
