"""Synthetic-only checks for the currently unavailable exact token-count gate."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from src.ai_brief.adapter import load_context
from src.ai_brief.contract import canonical_bytes
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import (
    OpenAIResponsesAdapter, ProviderBlocked, build_request,
)
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from src.ai_copilot.eight_call_campaign import CampaignBlocked
from src.ai_copilot.token_count_evidence import (
    EV05_COUNT, NEW_COUNTS, COUNT_FIELDS, require_exact_token_count,
)
from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results
from src.synthetic_context import SyntheticHarness
from tests.test_p5_quality_corpus import ROOT


class TokenCountingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / "cases.v2.json").read_text())["cases"]
        cls.original = SyntheticHarness()
        cls.low_risk = SyntheticHarness(fixture_id="p5_low_risk_v1")
        cls.requests = {}
        try:
            for case in cls.cases:
                harness = cls.low_risk if case["fixture_id"] == "p5_low_risk_v1" else cls.original
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
                outcome = prepare_brief(harness, context, comparison=comparison,
                                        max_records=case["max_records"])
                if outcome.status != "VALIDATED" or outcome.review is None:
                    raise AssertionError("Synthetic case did not produce a ValidatedBrief")
                request = build_request(outcome.review, model_snapshot="gpt-6-luna",
                                        max_output_tokens=25000, timeout_seconds=180,
                                        execution_profile="P5_PAID_ACCEPTANCE")
                cls.requests[case["id"]] = (outcome.review, request)
        except BaseException:
            cls.original.close()
            cls.low_risk.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.original.close()
        cls.low_risk.close()

    def test_all_eight_exact_request_shapes_include_instructions_and_schema(self):
        self.assertEqual(len(self.requests), 8)
        for case_id, (review, request) in self.requests.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(request.brief_digest, review.content_digest)
                self.assertEqual(request.request_digest,
                                 hashlib.sha256(request.canonical_body).hexdigest())
                args = OpenAIResponsesAdapter.call_arguments(request)
                self.assertEqual(args["model"], "gpt-6-luna")
                self.assertTrue(args["instructions"])
                self.assertTrue(args["text"]["format"]["strict"])
                self.assertTrue(args["text"]["format"]["schema"])
                self.assertEqual(json.loads(args["input"])["brief_digest"], review.content_digest)
                self.assertEqual(args["reasoning"], {"effort": "medium"})

    def test_no_local_count_fails_before_campaign_claim_or_transport(self):
        review, request = self.requests["EV-01"]
        class ClaimSpy:
            def claim_paid_dispatch(self, *args, **kwargs):
                raise AssertionError("Campaign claim must not occur before exact counting")
        with patch("src.ai_copilot.provider.REAL_PROVIDER_DISPATCH_LOCKED", False):
            with self.assertRaisesRegex(ProviderBlocked, "Trusted exact input-token count"):
                OpenAIResponsesAdapter.execute_authorized(
                    request, review, campaign=ClaimSpy(), case_id="EV-01",
                    owner_password="unused")

    def test_input_cap_configuration_boundary_and_changed_payload(self):
        _, request = self.requests["EV-01"]
        self.assertEqual(request.max_input_tokens, 25000)
        OpenAIResponsesAdapter.call_arguments(request)
        for cap in (24999, 25001, None):
            with self.subTest(cap=cap), self.assertRaises(ProviderBlocked):
                OpenAIResponsesAdapter.call_arguments(replace(request, max_input_tokens=cap))
        for changed in (replace(request, canonical_body=request.canonical_body + b" "),
                        replace(request, request_digest="0" * 64)):
            with self.assertRaises(ProviderBlocked):
                OpenAIResponsesAdapter.call_arguments(changed)

    def test_every_case_fails_closed_without_exact_count(self):
        with patch("src.ai_copilot.provider.REAL_PROVIDER_DISPATCH_LOCKED", False):
            for case_id, (review, request) in self.requests.items():
                with self.subTest(case_id=case_id):
                    with self.assertRaisesRegex(ProviderBlocked,
                                                "Trusted exact input-token count"):
                        OpenAIResponsesAdapter.execute_authorized(
                            request, review, campaign=None, case_id=case_id,
                            owner_password="unused")

    def test_ev05_live_evidence_is_preserved_and_fresh_run_is_stale(self):
        self.assertEqual(EV05_COUNT.case_id, "EV-05")
        self.assertEqual(EV05_COUNT.model, "gpt-6-luna")
        self.assertEqual(EV05_COUNT.input_tokens, 7471)
        self.assertEqual(EV05_COUNT.full_payload_sha256,
                         "e163dbcfe524984ae23bc4084ea85007ec66b8b4f83ef7f12eefd45d1677a69c")
        self.assertEqual(EV05_COUNT.count_projection_sha256,
                         "e1ccdfb7e31f0a5331fe616e807f40fdc421dc02ee1f53731c4174358212b72f")
        self.assertEqual(EV05_COUNT.request_id, "req_dc236dcf5d604305a7e587eaae14e7a8")
        request = self.requests["EV-05"][1]
        with self.assertRaisesRegex(CampaignBlocked, "stale"):
            require_exact_token_count("EV-05", request)
        self.assertEqual(tuple(e.case_id for e in NEW_COUNTS), tuple(self.requests))
        self.assertEqual([e.input_tokens for e in NEW_COUNTS],
                         [3992, 4075, 4063, 4062, 7477, 7473, 3989, 6356])
        self.assertEqual(len({e.full_payload_sha256 for e in NEW_COUNTS}), 8)
        for case_id in self.requests:
            with self.subTest(case_id=case_id), self.assertRaisesRegex(CampaignBlocked, "stale"):
                require_exact_token_count(case_id, self.requests[case_id][1])

    def test_exact_body_projection_model_and_cap_are_checked(self):
        request = self.requests["EV-05"][1]
        _, full_digest, projection_digest = input_token_count_wire(request)
        # Test-only evidence checks the gate independently of the transient live Run.
        matching = replace(EV05_COUNT, full_payload_sha256=full_digest,
                           count_projection_sha256=projection_digest)
        with patch("src.ai_copilot.token_count_evidence.EV05_COUNT", matching):
            self.assertEqual(require_exact_token_count("EV-05", request), 7471)
            with patch("src.ai_copilot.token_count_evidence.EV05_COUNT",
                       replace(matching, input_tokens=25001)):
                with self.assertRaisesRegex(CampaignBlocked, "invalid"):
                    require_exact_token_count("EV-05", request)
            with patch("src.ai_copilot.token_count_evidence.EV05_COUNT",
                       replace(matching, count_projection_sha256="0" * 64)):
                with self.assertRaisesRegex(CampaignBlocked, "stale"):
                    require_exact_token_count("EV-05", request)
            with patch("src.ai_copilot.token_count_evidence.EV05_COUNT",
                       replace(matching, model="other-model")):
                with self.assertRaisesRegex(CampaignBlocked, "invalid"):
                    require_exact_token_count("EV-05", request)

    def test_each_case_accepts_only_exact_digest_bound_evidence(self):
        for case_id, (_, request) in self.requests.items():
            with self.subTest(case_id=case_id):
                _, full_digest, projection_digest = input_token_count_wire(request)
                original = next(e for e in NEW_COUNTS if e.case_id == case_id)
                matching = replace(original,
                    full_payload_sha256=full_digest,
                    count_projection_sha256=projection_digest,
                    brief_digest=request.brief_digest,
                    provider_brief_digest=request.provider_brief_digest,
                    provider_request_digest=request.request_digest)
                with patch("src.ai_copilot.token_count_evidence.NEW_COUNTS", (matching,)):
                    self.assertEqual(require_exact_token_count(case_id, request), original.input_tokens)
                    with patch("src.ai_copilot.token_count_evidence.NEW_COUNTS",
                               (replace(matching, input_tokens=25001),)):
                        with self.assertRaisesRegex(CampaignBlocked, "invalid"):
                            require_exact_token_count(case_id, request)
                    with patch("src.ai_copilot.token_count_evidence.NEW_COUNTS",
                               (replace(matching, provider_request_digest="0" * 64),)):
                        with self.assertRaisesRegex(CampaignBlocked, "invalid"):
                            require_exact_token_count(case_id, request)

    def test_count_history_and_future_record_schema(self):
        schema_path = (Path(__file__).resolve().parents[1] / "docs/ai_copilot/p5_offline_evaluation"
                       / "GENERATION_EVALUATION_RECORD_SCHEMA.json")
        schema = json.loads(schema_path.read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        self.assertEqual(len(NEW_COUNTS), 8)
        for evidence in NEW_COUNTS:
            with self.subTest(case_id=evidence.case_id):
                self.assertEqual(evidence.model, "gpt-6-luna")
                self.assertEqual(evidence.http_status, 200)
                self.assertTrue(0 <= evidence.input_tokens <= 25000)
                self.assertTrue(evidence.run_id and evidence.run_manifest_sha256)
                self.assertTrue(evidence.brief_digest and evidence.provider_brief_digest)
                self.assertTrue(evidence.provider_request_digest and evidence.evidence_refs)
                self.assertTrue(evidence.payload_bytes and evidence.timestamp_utc)
                identity = {"corpus_version": "p5-offline-evaluation-2",
                            "case_id": evidence.case_id, "run_id": evidence.run_id,
                            "model": evidence.model,
                            "full_payload_sha256": evidence.full_payload_sha256}
                record = {
                    "record_version": "p5-generation-evaluation-record-1",
                    "record_id": hashlib.sha256(canonical_bytes(identity)).hexdigest(),
                    "corpus_version": "p5-offline-evaluation-2",
                    "evaluation_case_id": evidence.case_id,
                    "created_at_utc": evidence.timestamp_utc,
                    "run": {"fixture_id": evidence.fixture_id, "run_id": evidence.run_id,
                            "manifest_sha256": evidence.run_manifest_sha256,
                            "brief_run_alias": "R-1",
                            "comparison_alias": "C-1" if evidence.case_id in {"EV-05", "EV-06"} else None,
                            "evidence_refs": list(evidence.evidence_refs)},
                    "brief": {"content_sha256": evidence.brief_digest,
                              "provider_projection_sha256": evidence.provider_brief_digest},
                    "payload": {"model_alias": evidence.model,
                                "provider_request_sha256": evidence.provider_request_digest,
                                "full_responses_sha256": evidence.full_payload_sha256,
                                "count_projection_sha256": evidence.count_projection_sha256,
                                "byte_length": evidence.payload_bytes},
                    "token_count": {"status": "SUCCESS", "http_status": 200,
                                    "request_id": evidence.request_id,
                                    "input_tokens": evidence.input_tokens,
                                    "timestamp_utc": evidence.timestamp_utc,
                                    "returned_usage": None, "returned_cost": None},
                    "generation": {"status": "NOT_RUN", "raw_output_ref": None,
                                   "raw_output_sha256": None, "parsed_output_ref": None,
                                   "parsed_output_sha256": None, "returned_model_id": None,
                                   "request_id": None, "usage": None, "actual_charge_usd": None,
                                   "charge_source": None, "timestamp_utc": None},
                    "p1_validation": {"status": "NOT_RUN", "result_ref": None,
                                      "checked_at_utc": None},
                    "evidence_validation": {"status": "NOT_RUN", "result_ref": None,
                                            "checked_at_utc": None},
                    "human_evaluation": {"status": "NOT_RUN", "reviewer_ids": [],
                                         "adjudicator_id": None, "scores": None,
                                         "critical_failures": [], "verdict": None,
                                         "review_ref": None},
                }
                self.assertEqual(list(validator.iter_errors(record)), [])
                record["payload"]["full_responses_sha256"] = "0"
                self.assertTrue(list(validator.iter_errors(record)))


if __name__ == "__main__":
    unittest.main()
