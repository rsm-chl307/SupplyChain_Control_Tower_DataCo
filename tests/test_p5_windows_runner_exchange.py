from datetime import datetime, timezone
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.provider import build_request
from src.ai_copilot.input_token_count_payload import input_token_count_wire
from src.ai_copilot.token_count_evidence import require_exact_token_count
from src.ai_copilot.windows_runner_exchange import (
    DEFAULT_EXCHANGE_PATH, EXCHANGE_PATH_ENV, RunnerExchangeBlocked,
    RunnerResponsePending, WindowsHostTokenCountExchange,
    collect_configured_count_response, configured_windows_token_count_exchange,
    prepare_configured_count_request,
)
from src.synthetic_context import SyntheticHarness
from tools.windows_api_runner.api_runner import canonical_json_bytes


class WindowsRunnerP5ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-windows-exchange-test-only-")
        self.addCleanup(self.temp.cleanup)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.review = prepare_brief(self.harness, self.harness.issue("Baseline"),
                                    max_records=2).review
        self.request = build_request(self.review, model_snapshot="gpt-6-luna",
                                     max_output_tokens=25000, timeout_seconds=180,
                                     execution_profile="P5_PAID_ACCEPTANCE")
        self.exchange = WindowsHostTokenCountExchange(self.temp.name)

    def _response_package(self, prepared, *, input_tokens=3200, changes=None,
                          exchange_root=None):
        package = {
            "request_id": prepared.request_id, "case_id": prepared.case_id,
            "run_id": prepared.run_id, "payload_digest": prepared.payload_digest,
            "operation": "input_token_count", "http_status": 200,
            "openai_request_id": "req-host-count-001", "model": "gpt-6-luna",
            "returned_model_id": "gpt-6-luna", "usage": None,
            "response_body": {"input_tokens": input_tokens, "model": "gpt-6-luna"},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": "SUCCEEDED",
            "brief_digest": prepared.brief_digest,
            "provider_request_digest": prepared.provider_request_digest,
            "count_projection_digest": prepared.count_projection_digest,
            "run_manifest_sha256": prepared.run_manifest_sha256,
        }
        package.update(changes or {})
        root = Path(exchange_root) if exchange_root is not None else Path(self.temp.name)
        path = root / "responses" / f"{prepared.request_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(package) + b"\n")
        return path

    def test_prepares_exact_p5_payload_and_projection_with_run_identity(self):
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        wire, full_digest, projection_digest = input_token_count_wire(self.request)
        package = json.loads(prepared.package_path.read_text(encoding="utf-8"))
        reloaded = WindowsHostTokenCountExchange(self.temp.name).load_prepared(
            prepared.request_id, "EV-01", self.review, self.request)
        self.assertEqual(prepared.run_id, self.review._draft._bundle._context.run_id)
        self.assertEqual(prepared.payload_digest, full_digest)
        self.assertEqual(prepared.count_projection_digest, projection_digest)
        self.assertEqual(package["payload_digest"], full_digest)
        self.assertEqual(canonical_json_bytes(package["payload"]), wire)
        for generation_only in ("background", "max_output_tokens", "store", "stream",
                                "temperature", "top_p"):
            self.assertNotIn(generation_only, package["payload"])
        self.assertEqual(package["brief_digest"], self.request.brief_digest)
        self.assertEqual(package["provider_request_digest"], self.request.request_digest)
        self.assertEqual(reloaded, prepared)

    def test_load_prepared_revalidates_trusted_case_brief_and_request_profile(self):
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        invalid_requests = (
            replace(self.request, execution_profile="P2_OFFLINE"),
            replace(self.request, model_snapshot="unapproved-model"),
            replace(self.request, brief_digest="0" * 64),
        )
        for invalid_request in invalid_requests:
            with self.subTest(request=invalid_request):
                with self.assertRaises(RunnerExchangeBlocked):
                    self.exchange.load_prepared(prepared.request_id, "EV-01",
                                                self.review, invalid_request)
        with self.assertRaises(RunnerExchangeBlocked):
            self.exchange.load_prepared(prepared.request_id, "EV-99",
                                        self.review, self.request)
        with self.assertRaises(RunnerExchangeBlocked):
            self.exchange.load_prepared(prepared.request_id, "EV-01",
                                        object(), self.request)

    def test_load_prepared_rejects_persisted_run_identity_change(self):
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        package = json.loads(prepared.package_path.read_text(encoding="utf-8"))
        package["run_id"] = "different-run"
        prepared.package_path.write_bytes(canonical_json_bytes(package) + b"\n")
        with self.assertRaisesRegex(RunnerExchangeBlocked, "Persisted request differs"):
            self.exchange.load_prepared(prepared.request_id, "EV-01",
                                        self.review, self.request)

    def test_configured_exchange_resolves_absolute_override_and_rejects_relative_path(self):
        configured_root = Path(self.temp.name) / "configured-exchange"
        with patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(configured_root)}):
            exchange = configured_windows_token_count_exchange()
            self.assertEqual(exchange.exchange_path, configured_root.resolve())
        with patch.dict(os.environ, {EXCHANGE_PATH_ENV: "relative/exchange"}):
            with self.assertRaisesRegex(RunnerExchangeBlocked, "absolute container path"):
                configured_windows_token_count_exchange()

    def test_configured_production_entrypoints_prepare_and_collect_exact_paths(self):
        configured_root = Path(self.temp.name) / "configured-exchange"
        with patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(configured_root)}):
            prepared = prepare_configured_count_request("EV-01", self.review, self.request)
            self.assertEqual(prepared.package_path,
                             configured_root.resolve() / "requests" / f"{prepared.request_id}.json")
            self.assertTrue((configured_root.resolve() / "responses").is_dir())
            self._response_package(prepared, input_tokens=3200,
                                  exchange_root=configured_root)
            evidence = collect_configured_count_response(
                prepared.request_id, "EV-01", self.review, self.request)
        self.assertEqual(evidence.input_tokens, 3200)
        self.assertEqual(evidence.full_payload_sha256, prepared.payload_digest)

    def test_default_exchange_path_is_repository_local_and_stable(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.assertEqual(DEFAULT_EXCHANGE_PATH,
                         repository_root / "tmp" / "windows_runner_exchange")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_windows_token_count_exchange().exchange_path,
                             DEFAULT_EXCHANGE_PATH.resolve())

    def test_response_reconstructs_digest_bound_exact_token_evidence(self):
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        self._response_package(prepared, input_tokens=3200)
        evidence = self.exchange.collect(prepared, self.review, self.request)
        self.assertEqual(evidence.input_tokens, 3200)
        self.assertEqual(evidence.evidence_source, "WINDOWS_HOST_RUNNER")
        self.assertEqual(evidence.runner_request_id, prepared.request_id)
        self.assertEqual(evidence.run_id, prepared.run_id)
        self.assertEqual(evidence.full_payload_sha256, prepared.payload_digest)
        self.assertEqual(evidence.count_projection_sha256, prepared.count_projection_digest)
        self.assertRegex(evidence.response_package_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(require_exact_token_count("EV-01", self.request,
                         evidence=evidence, review=self.review), 3200)

    def test_missing_runner_response_is_pending_not_resubmitted(self):
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        with self.assertRaises(RunnerResponsePending):
            self.exchange.collect(prepared, self.review, self.request)
        self.assertTrue(prepared.package_path.exists())

    def test_mismatched_case_run_digest_or_request_identity_rejected(self):
        for field, value in (("case_id", "EV-02"), ("run_id", "other-run"),
                             ("payload_digest", "0" * 64),
                             ("count_projection_digest", "1" * 64)):
            with self.subTest(field=field):
                prepared = self.exchange.prepare("EV-01", self.review, self.request)
                self._response_package(prepared, changes={field: value})
                with self.assertRaises(RunnerExchangeBlocked):
                    self.exchange.collect(prepared, self.review, self.request)

    def test_bad_http_status_count_and_returned_model_rejected(self):
        for changes in ({"http_status": 500},
                        {"response_body": {"input_tokens": 25001}},
                        {"returned_model_id": "unapproved-model"}):
            with self.subTest(changes=changes):
                prepared = self.exchange.prepare("EV-01", self.review, self.request)
                self._response_package(prepared, changes=changes)
                with self.assertRaises(RunnerExchangeBlocked):
                    self.exchange.collect(prepared, self.review, self.request)

    def test_http_400_is_categorized_without_accepting_error_body(self):
        from src.ai_copilot.windows_runner_exchange import RunnerHTTPStatusError
        prepared = self.exchange.prepare("EV-01", self.review, self.request)
        self._response_package(prepared, changes={
            "http_status": 400,
            "runner_execution_status": "FAILED_AFTER_DISPATCH",
            "response_body": {"error": {"message": "synthetic rejection", "param": "background"}},
        })
        with self.assertRaisesRegex(RunnerHTTPStatusError, "HTTP 400"):
            self.exchange.collect(prepared, self.review, self.request)

    def test_collect_distinguishes_identity_digest_runner_and_missing_count_errors(self):
        from src.ai_copilot.windows_runner_exchange import (
            RunnerExecutionFailure, RunnerMissingInputTokens,
            RunnerResponseDigestMismatch, RunnerResponseIdentityMismatch,
        )
        cases = (
            ({"case_id": "EV-02"}, RunnerResponseIdentityMismatch),
            ({"payload_digest": "0" * 64}, RunnerResponseDigestMismatch),
            ({"runner_execution_status": "FAILED_AFTER_DISPATCH"}, RunnerExecutionFailure),
            ({"response_body": {"model": "gpt-6-luna"}}, RunnerMissingInputTokens),
        )
        for changes, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                prepared = self.exchange.prepare("EV-01", self.review, self.request)
                self._response_package(prepared, changes=changes)
                with self.assertRaises(expected_error):
                    self.exchange.collect(prepared, self.review, self.request)


if __name__ == "__main__":
    unittest.main()
