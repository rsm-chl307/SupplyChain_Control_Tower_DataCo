"""One-shot paid claim exercised only against a disposable synthetic test Ledger."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.approval import OwnerVerifier
from src.ai_copilot.eight_call_campaign import (
    CampaignBlocked, CaseSlot, EightCallCampaign, OWNER_PAID_POLICY,
)
from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive, _wire
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from src.ai_copilot.provider import (OfflineMockTransport, OpenAIResponsesAdapter,
                                     ProviderBlocked, build_request)
from src.ai_copilot.token_count_evidence import ExactTokenCount
from src.synthetic_context import SyntheticHarness
from tests.test_ai_copilot_eight_call_campaign import PASSWORD, plan


class OfflinePaidClaimSafetyTests(unittest.TestCase):
    def test_concurrent_claim_timeout_restart_and_unknown_never_resend(self):
        with tempfile.TemporaryDirectory(prefix="p5-wp4-1-dispatch-") as folder, SyntheticHarness() as harness:
            case_path = (Path(__file__).resolve().parents[1] /
                         "docs/ai_copilot/p5_offline_evaluation/cases.v2.json")
            cases = json.loads(case_path.read_text())["cases"]
            slots = tuple(CaseSlot(c["id"], c["case_version"], c["fixture_id"],
                                   c["scenario"], c["max_records"], c["comparison"])
                          for c in cases)
            policy = replace(plan(), campaign_id="paid-wp4-1-test-only",
                             corpus_version="p5-offline-evaluation-2",
                             slots=slots, model_policy=OWNER_PAID_POLICY,
                             model_snapshot="gpt-6-luna", max_output_tokens=25000,
                             timeout_seconds=180, per_slot_ceiling_micro=20000,
                             total_ceiling_micro=160000)
            db_path = str(Path(folder) / "test-campaign.db")
            verifier = OwnerVerifier.derive(PASSWORD, b"0123456789abcdef")
            with patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
                                      "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex}):
                EightCallCampaign.provision_paid_draft(db_path, policy, PASSWORD)
                campaign = EightCallCampaign(db_path)
                review = prepare_brief(harness, harness.issue("Baseline"), max_records=2).review
                self.assertIsNotNone(review)
                request = build_request(review, model_snapshot="gpt-6-luna",
                                        max_output_tokens=25000, timeout_seconds=180,
                                        execution_profile="P5_PAID_ACCEPTANCE")
                case = next(item for item in cases if item["id"] == "EV-01")
                archive_path = str(Path(folder) / "test-archive.db")
                GenerationEvaluationArchive.provision(archive_path)
                archive = GenerationEvaluationArchive(archive_path)
                _, full_digest, projection_digest = input_token_count_wire(request)
                token_evidence = ExactTokenCount(
                    "EV-01", "gpt-6-luna", 3992, full_digest, projection_digest,
                    "synthetic-test-count", run_id=review._draft._bundle._context.run_id,
                    run_manifest_sha256=review._draft._bundle._context.manifest_sha256,
                    brief_digest=request.brief_digest,
                    provider_brief_digest=request.provider_brief_digest,
                    provider_request_digest=request.request_digest,
                    fixture_id="v1_1", evidence_refs=("s7",), http_status=200)
                campaign.authorize_paid_acceptance(PASSWORD, policy.digest())
                approval = campaign.approve_slot("EV-01", review, request, PASSWORD,
                                                 estimated_micro=15000)
                # Dispatch behavior is isolated from the independently tested exact-count gate.
                # The stub is test-local and never becomes production token evidence.
                with patch("src.ai_copilot.token_count_evidence.require_exact_token_count",
                           return_value=3992), patch(
                               "src.ai_copilot.evaluation_archive.require_exact_token_count",
                               return_value=3992):
                    campaign.reserve_paid("EV-01", review, request, approval)
                    campaign.start_paid_attempt("EV-01", review, request)
                    transports = [OfflineMockTransport(TimeoutError("fake timeout"))
                                  for _ in range(4)]

                    def attempt(transport):
                        try:
                            return OpenAIResponsesAdapter.execute_authorized(
                                request, review, campaign=campaign, case_id="EV-01",
                                owner_password=PASSWORD, archive=archive, case=case,
                                token_evidence=token_evidence, transport=transport)
                        except ProviderBlocked as exc:
                            return exc.__cause__ or exc
                        except CampaignBlocked as exc:
                            return exc

                    with ThreadPoolExecutor(max_workers=4) as pool:
                        results = list(pool.map(attempt, transports))
                    winners = [result for result in results if not isinstance(result, Exception)]
                    self.assertEqual(len(winners), 1, repr(results))
                    self.assertEqual(winners[0].status, "UNKNOWN_OUTCOME")
                    self.assertEqual(sum(t.calls for t in transports), 1)

                    # Restart after the archive and UNKNOWN Ledger hold were persisted.
                    restarted = EightCallCampaign(db_path)
                    self.assertEqual(restarted.reservation("EV-01")["state"], "UNKNOWN")
                    retry = OfflineMockTransport(TimeoutError("must not run"))
                    with self.assertRaises(CampaignBlocked):
                        OpenAIResponsesAdapter.execute_authorized(
                            request, review, campaign=restarted, case_id="EV-01",
                            owner_password=PASSWORD, archive=archive, case=case,
                            token_evidence=token_evidence, transport=retry)
                    self.assertEqual(retry.calls, 0)

                    row = restarted.reservation("EV-01")
                    self.assertEqual(row["state"], "UNKNOWN")
                    self.assertEqual(restarted.summary()["status"], "HELD")
                    with self.assertRaises(CampaignBlocked):
                        restarted.claim_paid_dispatch("EV-01", review, request, PASSWORD)
                    with sqlite3.connect(db_path) as db:
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch_claims").fetchone()[0], 1)
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM provider_observations").fetchone()[0], 1)
                    self.assertEqual(restarted.summary()["reserved_micro"], 20000)


if __name__ == "__main__":
    unittest.main()
