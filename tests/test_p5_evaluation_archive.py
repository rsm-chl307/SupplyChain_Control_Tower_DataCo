"""Synthetic-only persistence and failure tests for the separate P5 archive."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import CaseSlot, EightCallCampaign, OWNER_MOCK_POLICY
from src.ai_copilot.evaluation_archive import (
    ArchiveBlocked, GenerationEvaluationArchive, _wire,
)
from src.ai_copilot.ledger import ProviderAccounting
from src.ai_copilot.provider import ProviderResult, build_request
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from src.ai_copilot.quality_evaluation import Adjudication, assess_technical, score_case
from src.ai_copilot.token_count_evidence import ExactTokenCount
from src.synthetic_context import SyntheticHarness
from tests.test_ai_copilot_eight_call_campaign import PASSWORD, plan
from tests.test_p5_quality_evaluation import response, review as human_review


class EvaluationArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-archive-offline-")
        self.addCleanup(self.temp.cleanup)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.context = self.harness.issue("Baseline")
        self.brief = prepare_brief(self.harness, self.context, max_records=2).review
        self.assertIsNotNone(self.brief)
        cases = json.loads((Path(__file__).resolve().parents[1] /
                            "docs/ai_copilot/p5_offline_evaluation/cases.v2.json").read_text())["cases"]
        self.case = cases[0]
        slots = tuple(CaseSlot(c["id"], c["case_version"], c["fixture_id"],
                               c["scenario"], c["max_records"], c["comparison"])
                      for c in cases)
        self.policy = replace(plan(), campaign_id="offline-archive-test",
                              corpus_version="p5-offline-evaluation-2", slots=slots,
                              model_policy=OWNER_MOCK_POLICY, model_snapshot="gpt-6-luna",
                              max_output_tokens=25000, timeout_seconds=180,
                              per_slot_ceiling_micro=20000, total_ceiling_micro=160000)
        verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
        env = patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                   "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex})
        env.start()
        self.addCleanup(env.stop)
        self.ledger_path = str(Path(self.temp.name) / "ledger.db")
        EightCallCampaign.provision_offline(self.ledger_path, self.policy, PASSWORD)
        self.ledger = EightCallCampaign(self.ledger_path)
        self.request = build_request(self.brief, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_ACCEPTANCE_MOCK")
        approval = self.ledger.approve_slot("EV-01", self.brief, self.request, PASSWORD,
                                            estimated_micro=15000)
        self.ledger.reserve_offline("EV-01", self.brief, self.request, approval)
        self.ledger.start_offline_attempt("EV-01", self.brief, self.request)
        self.archive_path = str(Path(self.temp.name) / "archive.db")
        GenerationEvaluationArchive.provision(self.archive_path)
        self.archive = GenerationEvaluationArchive(self.archive_path)
        _, full, projection = input_token_count_wire(self.request)
        self.count = ExactTokenCount(
            "EV-01", "gpt-6-luna", 100, full, projection, "synthetic-test-count",
            run_id=self.context.run_id, run_manifest_sha256=self.context.manifest_sha256,
            brief_digest=self.request.brief_digest,
            provider_brief_digest=self.request.provider_brief_digest,
            provider_request_digest=self.request.request_digest,
            fixture_id="v1_1", evidence_refs=("s7",),
            timestamp_utc=datetime.now(timezone.utc).isoformat(), http_status=None)
        self.raw = response(self.brief, ["s7"], self.case["numerical_slot_ref"],
                            self.case["numerical_slot_field"])
        self.usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        self.provider_result = ProviderResult("SUCCEEDED", self.raw, "synthetic-generation-1",
                                              self.usage, returned_model_id="gpt-6-luna")

    def _accounted(self):
        self.ledger.record_offline_outcome(
            "EV-01", "SUCCEEDED",
            ProviderAccounting(self.usage, "synthetic-generation-1", "0.010000"))

    def _generation(self, **changes):
        return self.archive.append_generation(
            case=self.case, review=self.brief, request=self.request,
            token_evidence=changes.get("count", self.count),
            result=changes.get("result", self.provider_result), campaign=self.ledger)

    def _assessment(self):
        technical = assess_technical(
            self.case, dataset_version="p5-offline-evaluation-2",
            campaign_id=self.policy.campaign_id, review=self.brief,
            request=self.request, raw_response=self.raw, provider_status="SUCCEEDED")
        case_result = score_case(
            technical, human_review("reviewer-a"), human_review("reviewer-b"),
            Adjudication("adjudicator", human_review("final"), ""))
        return technical, case_result

    def test_complete_lineage_persists_across_restart(self):
        self._accounted()
        generation = self._generation()
        technical, case_result = self._assessment()
        self.ledger.record_case_review("EV-01", case_result, PASSWORD)
        with patch.object(self.archive, "_append", side_effect=ArchiveBlocked("fake evaluation write failure")):
            with self.assertRaises(ArchiveBlocked):
                self.archive.append_evaluation(generation.record["record_id"], review=self.brief,
                                               technical=technical, result=case_result,
                                               campaign=self.ledger)
        self.assertEqual(len(self.archive.history(generation.record["record_id"])), 1)
        evaluation = self.archive.append_evaluation(
            generation.record["record_id"], review=self.brief,
            technical=technical, result=case_result, campaign=self.ledger)
        self.assertEqual(generation.record["run"]["run_id"], self.context.run_id)
        self.assertEqual(generation.record["brief"]["content_sha256"], self.brief.content_digest)
        _, generation_digest, _ = _wire(self.request)
        self.assertEqual(generation.record["payload"]["full_responses_sha256"], generation_digest)
        self.assertNotEqual(generation.record["payload"]["full_responses_sha256"],
                            self.count.full_payload_sha256)
        self.assertEqual(generation.record["generation"]["request_id"], "synthetic-generation-1")
        self.assertEqual(generation.record["generation"]["returned_model_id"], "gpt-6-luna")
        self.assertEqual(evaluation.record["generation"]["usage"], self.usage)
        self.assertEqual(evaluation.record["generation"]["actual_charge_usd"], "0.010000")
        self.assertEqual(evaluation.record["generation"]["charge_source"], "SYNTHETIC_TEST_ACCOUNTING")
        self.assertEqual(evaluation.record["p1_validation"]["status"], "PASS")
        self.assertEqual(evaluation.record["evidence_validation"]["status"], "PASS")
        self.assertEqual(evaluation.record["human_evaluation"]["status"], "COMPLETE")
        self.assertIsNotNone(evaluation.reviewed_at_utc)
        self.assertEqual(evaluation.raw_response, self.raw)
        self.assertIsInstance(evaluation.parsed_response, dict)
        restarted = GenerationEvaluationArchive(self.archive_path)
        history = restarted.history(generation.record["record_id"])
        self.assertEqual([entry.phase for entry in history], ["GENERATION", "EVALUATION"])
        self.assertEqual(history[1].entry_digest, evaluation.entry_digest)
        with self.assertRaises(ArchiveBlocked):
            self._generation()
        with self.assertRaises(ArchiveBlocked):
            restarted.append_evaluation(generation.record["record_id"], review=self.brief,
                                        technical=technical, result=case_result, campaign=self.ledger)
        with sqlite3.connect(self.archive_path) as db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE archive_entries SET phase='GENERATION' WHERE entry_id=?",
                           (generation.entry_id,))
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM archive_entries WHERE entry_id=?", (generation.entry_id,))
        self.harness.close()
        self.assertEqual(GenerationEvaluationArchive(self.archive_path).history(
            generation.record["record_id"])[1].entry_digest, evaluation.entry_digest)

    def test_later_run_appends_without_replacing_history(self):
        self._accounted()
        first = self._generation()
        with SyntheticHarness() as later_harness:
            later_context = later_harness.issue("Baseline")
            later_brief = prepare_brief(later_harness, later_context, max_records=2).review
            self.assertIsNotNone(later_brief)
            later_request = build_request(later_brief, model_snapshot="gpt-6-luna",
                                          max_output_tokens=25000, timeout_seconds=180,
                                          execution_profile="P5_ACCEPTANCE_MOCK")
            later_policy = replace(self.policy, campaign_id="offline-archive-later-run")
            later_path = str(Path(self.temp.name) / "later-ledger.db")
            EightCallCampaign.provision_offline(later_path, later_policy, PASSWORD)
            later_ledger = EightCallCampaign(later_path)
            approval = later_ledger.approve_slot("EV-01", later_brief, later_request,
                                                  PASSWORD, estimated_micro=15000)
            later_ledger.reserve_offline("EV-01", later_brief, later_request, approval)
            later_ledger.start_offline_attempt("EV-01", later_brief, later_request)
            later_raw = response(later_brief, ["s7"], self.case["numerical_slot_ref"],
                                 self.case["numerical_slot_field"])
            later_ledger.record_offline_outcome(
                "EV-01", "SUCCEEDED",
                ProviderAccounting(self.usage, "synthetic-generation-2", "0.010000"))
            _, full, projection = input_token_count_wire(later_request)
            later_count = replace(
                self.count, full_payload_sha256=full, count_projection_sha256=projection,
                run_id=later_context.run_id,
                run_manifest_sha256=later_context.manifest_sha256,
                brief_digest=later_request.brief_digest,
                provider_brief_digest=later_request.provider_brief_digest,
                provider_request_digest=later_request.request_digest)
            later_result = ProviderResult("SUCCEEDED", later_raw, "synthetic-generation-2",
                                          self.usage, returned_model_id="gpt-6-luna")
            later = self.archive.append_generation(
                case=self.case, review=later_brief, request=later_request,
                token_evidence=later_count, result=later_result, campaign=later_ledger)
            self.assertNotEqual(first.record["record_id"], later.record["record_id"])
            self.assertEqual(self.archive.history(first.record["record_id"])[0].entry_digest,
                             first.entry_digest)
            self.assertEqual(self.archive.history(later.record["record_id"])[0].entry_digest,
                             later.entry_digest)

    def test_payload_token_and_ledger_mismatch_rejected(self):
        self._accounted()
        with self.assertRaises(ArchiveBlocked):
            self._generation(count=replace(self.count, full_payload_sha256="0" * 64))
        with self.assertRaises(ArchiveBlocked):
            self._generation(count=replace(self.count, count_projection_sha256="0" * 64))
        with self.assertRaises(ArchiveBlocked):
            self._generation(count=replace(self.count, run_id="wrong-run"))
        with self.assertRaises(ArchiveBlocked):
            self._generation(count=replace(self.count, input_tokens=25001))
        with self.assertRaises(ArchiveBlocked):
            self._generation(count=replace(self.count, model="wrong-model"))
        with self.assertRaises(ArchiveBlocked):
            self._generation(result=replace(self.provider_result, provider_request_id="wrong-id"))
        with sqlite3.connect(self.archive_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM archive_entries").fetchone()[0], 0)

    def test_unknown_and_missing_accounting_stay_incomplete(self):
        self.ledger.record_offline_outcome("EV-01", "UNKNOWN")
        unknown = ProviderResult("UNKNOWN_OUTCOME")
        generation = self._generation(result=unknown)
        self.assertEqual(generation.record["generation"]["status"], "UNKNOWN")
        self.assertIsNone(generation.record["generation"]["usage"])
        self.assertIsNone(generation.record["generation"]["actual_charge_usd"])
        self.assertEqual(generation.ledger_state_at_write, "UNKNOWN")
        technical, case_result = self._assessment()
        with self.assertRaises(ArchiveBlocked):
            self.archive.append_evaluation(generation.record["record_id"], review=self.brief,
                                           technical=technical, result=case_result, campaign=self.ledger)
        self.assertEqual(len(GenerationEvaluationArchive(self.archive_path).history(
            generation.record["record_id"])), 1)

    def test_evaluation_requires_revalidated_evidence_and_review(self):
        self._accounted()
        generation = self._generation()
        technical, case_result = self._assessment()
        with self.assertRaises(ArchiveBlocked):
            self.archive.append_evaluation(generation.record["record_id"], review=self.brief,
                                           technical=technical, result=case_result, campaign=self.ledger)
        self.ledger.record_case_review("EV-01", case_result, PASSWORD)
        with self.assertRaises(ArchiveBlocked):
            self.archive.append_evaluation(
                generation.record["record_id"], review=self.brief,
                technical=replace(technical, cited_refs=()),
                result=case_result, campaign=self.ledger)
        self.assertEqual(len(self.archive.history(generation.record["record_id"])), 1)

    def test_archive_failure_never_changes_ledger_or_completes_record(self):
        self._accounted()
        before = self.ledger.reservation("EV-01")
        with patch.object(self.archive, "_connect", side_effect=sqlite3.OperationalError("fake disk failure")):
            with self.assertRaises(ArchiveBlocked):
                self._generation()
        with sqlite3.connect(self.archive_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM archive_entries").fetchone()[0], 0)
        self.assertEqual(self.ledger.reservation("EV-01"), before)
        generation = self._generation()
        technical, case_result = self._assessment()
        with self.assertRaises(ArchiveBlocked):
            self.archive.append_evaluation(generation.record["record_id"], review=self.brief,
                                           technical=technical, result=case_result, campaign=self.ledger)
        self.assertEqual(len(self.archive.history(generation.record["record_id"])), 1)


if __name__ == "__main__":
    unittest.main()
