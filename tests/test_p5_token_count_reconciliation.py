"""Offline owner reconciliation tests using synthetic evidence and temp SQLite."""
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import json
import os
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ai_copilot.local_token_count_e2e import _load_case, _make_trusted_request
from src.ai_copilot.local_token_count_e2e import main as operator_main
from src.ai_copilot.approval import ApprovalStore, OwnerVerifier
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked, TokenCountWorkflowState,
)
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV
from tools.windows_api_runner.api_runner import canonical_json_bytes


class TokenCountReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-token-reconcile-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exchange = self.root / "exchange"
        self.db_path = self.root / "workflow.sqlite3"
        self.env = patch.dict(os.environ, {
            EXCHANGE_PATH_ENV: str(self.exchange),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.owner_password = "synthetic-owner-test-password-2026"
        verifier = OwnerVerifier.derive(self.owner_password, b"synthetic-salt!!")
        self.owner_store = self.root / "synthetic-owner-approval.sqlite3"
        ApprovalStore.provision(str(self.owner_store), verifier)
        self.owner_env = patch.dict(os.environ, {
            "COPILOT_OWNER_SALT_HEX": verifier.salt_hex,
            "COPILOT_OWNER_SCRYPT_HEX": verifier.digest_hex,
            "COPILOT_LEDGER_PATH": str(self.owner_store),
        })
        self.owner_env.start()
        self.addCleanup(self.owner_env.stop)
        self.workflow = P5TokenCountOrchestrator(
            exchange_path=self.exchange, state_path=self.db_path)
        self.harness, self.review, self.request = _make_trusted_request(_load_case("EV-01"))
        self.addCleanup(self.harness.close)
        self.prepared = self.workflow.prepare("EV-01", self.review, self.request)
        self.workflow.mark_awaiting_host_execution(self.prepared.request_id)
        self.workflow.mark_unknown(self.prepared.request_id)
        self.request_path = self.exchange / "requests" / f"{self.prepared.request_id}.json"
        self.response_path = self.exchange / "responses" / f"{self.prepared.request_id}.json"
        # Recreate the immutable historical pre-serializer package shape in
        # this isolated fixture. The repaired serializer omits this field.
        original = json.loads(self.request_path.read_text(encoding="utf-8"))
        original["payload"]["background"] = False
        original["payload_digest"] = hashlib.sha256(
            canonical_json_bytes(original["payload"])).hexdigest()
        self.request_path.write_bytes(canonical_json_bytes(original) + b"\n")
        with __import__("sqlite3").connect(self.db_path) as db:
            db.execute("UPDATE token_count_workflow SET payload_sha256=? WHERE request_id=?",
                       (original["payload_digest"], self.prepared.request_id))
        self._write_failure_response()

    def _write_failure_response(self, **updates):
        request_package = json.loads(self.request_path.read_text(encoding="utf-8"))
        response = {
            "request_id": self.prepared.request_id,
            "case_id": self.prepared.case_id,
            "run_id": self.prepared.run_id,
            "payload_digest": request_package["payload_digest"],
            "operation": "input_token_count",
            "http_status": 400,
            "openai_request_id": "req_synthetic400evidence",
            "model": "gpt-6-luna",
            "returned_model_id": None,
            "usage": None,
            "response_body": {"error": {
                "type": "invalid_request_error",
                "code": "unknown_parameter",
                "param": "background",
                "message": "Unknown parameter: 'background'.",
            }},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runner_execution_status": "FAILED_AFTER_DISPATCH",
            "brief_digest": self.prepared.brief_digest,
            "provider_request_digest": self.prepared.provider_request_digest,
            "count_projection_digest": self.prepared.count_projection_digest,
            "run_manifest_sha256": self.prepared.run_manifest_sha256,
        }
        response.update(updates)
        self.response_path.parent.mkdir(parents=True, exist_ok=True)
        self.response_path.write_bytes(canonical_json_bytes(response) + b"\n")
        return response

    def _digests(self):
        return (hashlib.sha256(self.request_path.read_bytes()).hexdigest(),
                hashlib.sha256(self.response_path.read_bytes()).hexdigest())

    def _reconcile(self, *, request_sha=None, response_sha=None, **kwargs):
        request_sha_default, response_sha_default = self._digests()
        request_sha = request_sha or request_sha_default
        response_sha = response_sha or response_sha_default
        reason = kwargs.pop("reason", "Confirmed original HTTP 400 rejection.")
        password = kwargs.pop("owner_password", self.owner_password)
        authorization = kwargs.pop("authorization", None)
        if authorization is None and password:
            authorization = self.workflow.authorize_confirmed_failure(
                self.prepared.request_id,
                expected_request_sha256=request_sha,
                expected_response_sha256=response_sha,
                reason=reason, owner_password=password)
        return self.workflow.reconcile_confirmed_failure(
            self.prepared.request_id,
            expected_request_sha256=request_sha,
            expected_response_sha256=response_sha,
            reason=reason,
            confirmation=kwargs.pop(
                "confirmation", f"CONFIRM_FAILED {self.prepared.request_id}"),
            authorization=authorization,
            owner_password=password,
        )

    def test_verified_http_400_closeout_is_atomic_append_only_and_restart_safe(self):
        request_before = self.request_path.read_bytes()
        response_before = self.response_path.read_bytes()
        with patch("tools.windows_api_runner.api_runner.UrllibTransport.post") as transport, \
                patch("tools.windows_api_runner.api_runner.ApiRunner.execute") as execute:
            record = self._reconcile()
        transport.assert_not_called()
        execute.assert_not_called()
        self.assertEqual(record.state, TokenCountWorkflowState.CONFIRMED_FAILED)
        self.assertEqual(record.request_id, self.prepared.request_id)
        self.assertEqual(record.run_id, self.prepared.run_id)
        self.assertEqual(self.request_path.read_bytes(), request_before)
        self.assertEqual(self.response_path.read_bytes(), response_before)
        self.assertTrue(self.workflow.workflow_resolved(self.prepared.request_id))

        restarted = P5TokenCountOrchestrator(exchange_path=self.exchange,
                                             state_path=self.db_path)
        self.assertTrue(restarted.workflow_resolved(self.prepared.request_id))
        self.assertEqual(restarted.record_for_request(self.prepared.request_id).state,
                         TokenCountWorkflowState.CONFIRMED_FAILED)
        with self.assertRaises(TokenCountWorkflowBlocked):
            restarted.reconcile_confirmed_failure(
                self.prepared.request_id,
                expected_request_sha256=self._digests()[0],
                expected_response_sha256=self._digests()[1],
                reason="duplicate close-out rejected",
                confirmation=f"CONFIRM_FAILED {self.prepared.request_id}")

        # The Case remains reserved, but a distinct trusted Case can proceed.
        self.workflow.assert_new_workflow_allowed("EV-02")
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "already has a count workflow"):
            restarted.prepare("EV-01", self.review, self.request)
        harness2, review2, request2 = _make_trusted_request(_load_case("EV-02"))
        self.addCleanup(harness2.close)
        prepared2 = restarted.prepare("EV-02", review2, request2)
        self.assertEqual(restarted.record_for_request(prepared2.request_id).case_id, "EV-02")

        # Append-only event rows reject ordinary UPDATE and DELETE.
        import sqlite3
        with sqlite3.connect(self.db_path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE token_count_reconciliation_events SET event_json=event_json")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM token_count_reconciliation_events")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT OR REPLACE INTO token_count_reconciliation_events "
                           "SELECT request_id,event_sha256,event_json,created_at_utc "
                           "FROM token_count_reconciliation_events")

    def test_unresolved_unknown_still_blocks_global_gate(self):
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            self.workflow.assert_new_workflow_allowed("EV-02")
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            self.workflow.prepare("EV-02", self.review, self.request)

    def test_only_exact_http_400_evidence_is_classified_confirmed_failed(self):
        # The valid synthetic evidence mirrors the immutable historical failure.
        self.assertEqual(
            self.workflow._failed_or_unknown_response_state(self.prepared.request_id),
            TokenCountWorkflowState.CONFIRMED_FAILED)
        self._write_failure_response(response_body={"error": {
            "type": "invalid_request_error", "code": "unknown_parameter",
            "param": "store", "message": "Unknown parameter: 'store'."}})
        self.assertEqual(
            self.workflow._failed_or_unknown_response_state(self.prepared.request_id),
            TokenCountWorkflowState.FAILED)
        self.assertFalse(self.workflow.workflow_resolved(self.prepared.request_id))

    def test_wrong_request_or_response_digest_is_rejected(self):
        good_request, good_response = self._digests()
        request_before, response_before = self.request_path.read_bytes(), self.response_path.read_bytes()
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "SHA-256 mismatch"):
            self._reconcile(request_sha="0" * 64)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "SHA-256 mismatch"):
            self._reconcile(response_sha="0" * 64)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.UNKNOWN)
        self.assertEqual((self.request_path.read_bytes(), self.response_path.read_bytes()),
                         (request_before, response_before))
        self.assertEqual(len(good_request), 64)
        self.assertEqual(len(good_response), 64)

    def test_wrong_uuid_response_identity_and_http_error_semantics_rejected(self):
        wrong_uuid = "00000000-0000-4000-8000-000000000000"
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.reconcile_confirmed_failure(
                wrong_uuid, expected_request_sha256="0" * 64,
                expected_response_sha256="0" * 64, reason="Wrong UUID is rejected.",
                confirmation=f"CONFIRM_FAILED {wrong_uuid}")
        for changes in (
                {"request_id": wrong_uuid},
                {"run_id": "wrong-run"},
                {"case_id": "EV-02"},
                {"model": "unapproved-model"},
                {"payload_digest": "0" * 64},
                {"count_projection_digest": "0" * 64},
                {"http_status": 200},
                {"runner_execution_status": "SUCCEEDED"},
                {"response_body": {"error": {"type": "invalid_request_error",
                    "code": "unknown_parameter", "param": "store",
                    "message": "Unknown parameter: 'store'."}}},
                {"response_body": {"input_tokens": 7471}},
        ):
            with self.subTest(changes=changes):
                self._write_failure_response(**changes)
                with self.assertRaises(TokenCountWorkflowBlocked):
                    self._reconcile()
                self.assertEqual(self.workflow.state_for_case("EV-01"),
                                 TokenCountWorkflowState.UNKNOWN)

    def test_explicit_confirmation_reason_and_owner_identity_are_mandatory(self):
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "confirmation"):
            self._reconcile(confirmation="CONFIRM_FAILED another-uuid")
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "reason"):
            self._reconcile(reason="short")
        with patch.dict(os.environ, {"COPILOT_OWNER_SALT_HEX": "", "COPILOT_OWNER_SCRYPT_HEX": ""}):
            with self.assertRaisesRegex(TokenCountWorkflowBlocked, "Owner identity"):
                self._reconcile()
        with patch.dict(os.environ, {"COPILOT_LEDGER_PATH": ""}):
            with self.assertRaisesRegex(TokenCountWorkflowBlocked, "approval store"):
                self._reconcile()
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.UNKNOWN)

    def test_operator_cli_requires_digests_and_uses_explicit_confirmation(self):
        request_sha, response_sha = self._digests()
        output = StringIO()
        with patch("src.ai_copilot.local_token_count_e2e.P5TokenCountOrchestrator",
                   return_value=self.workflow), \
                patch("builtins.input", return_value=f"CONFIRM_FAILED {self.prepared.request_id}"), \
                patch("getpass.getpass", return_value=self.owner_password), \
                redirect_stdout(output):
            result = operator_main([
                "--reconcile-failed", self.prepared.request_id,
                "--request-sha256", request_sha,
                "--response-sha256", response_sha,
                "--reason", "Owner reviewed the original HTTP 400 evidence.",
            ])
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("CONFIRMED_FAILED", output.getvalue())
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.CONFIRMED_FAILED)

    def test_request_package_with_tampered_payload_digest_is_rejected(self):
        package = json.loads(self.request_path.read_text(encoding="utf-8"))
        package["payload_digest"] = "0" * 64
        self.request_path.write_bytes(canonical_json_bytes(package) + b"\n")
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "Runner validation"):
            self._reconcile()
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.UNKNOWN)

    def test_plain_failed_state_does_not_release_global_lock(self):
        other_exchange, other_db = self.root / "plain-failed-exchange", self.root / "plain-failed.sqlite3"
        with patch.dict(os.environ, {EXCHANGE_PATH_ENV: str(other_exchange)}):
            other = P5TokenCountOrchestrator(exchange_path=other_exchange, state_path=other_db)
            harness, review, request = _make_trusted_request(_load_case("EV-02"))
            self.addCleanup(harness.close)
            prepared = other.prepare("EV-02", review, request)
            other.mark_failed(prepared.request_id)
            self.assertEqual(other.state_for_case("EV-02"), TokenCountWorkflowState.FAILED)
            with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
                other.assert_new_workflow_allowed("EV-03")

    def test_authorization_binding_expiry_and_owner_identity_fail_closed(self):
        request_sha, response_sha = self._digests()
        reason = "Owner reviewed synthetic HTTP 400 evidence."
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "Owner authentication"):
            self.workflow.authorize_confirmed_failure(
                self.prepared.request_id, expected_request_sha256=request_sha,
                expected_response_sha256=response_sha, reason=reason,
                owner_password="wrong synthetic owner password")
        permit = self.workflow.authorize_confirmed_failure(
            self.prepared.request_id, expected_request_sha256=request_sha,
            expected_response_sha256=response_sha, reason=reason,
            owner_password=self.owner_password, ttl_seconds=1)
        common = dict(expected_request_sha256=request_sha,
                      expected_response_sha256=response_sha, reason=reason,
                      confirmation=f"CONFIRM_FAILED {self.prepared.request_id}",
                      owner_password=self.owner_password)
        for changed in (replace(permit, request_id="wrong-uuid"),
                        replace(permit, case_id="EV-02"),
                        replace(permit, run_id="wrong-run"),
                        replace(permit, request_sha256="0" * 64),
                        replace(permit, response_sha256="0" * 64),
                        replace(permit, disposition="COLLECTED"),
                        replace(permit, purpose="GENERATION"),
                        replace(permit, reason="Different reason")):
            with self.subTest(changed=changed):
                with self.assertRaises(TokenCountWorkflowBlocked):
                    self.workflow.reconcile_confirmed_failure(
                        self.prepared.request_id, authorization=changed, **common)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "authorization"):
            self.workflow.reconcile_confirmed_failure(
                self.prepared.request_id, authorization=None, **common)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "authorization"):
            self.workflow.reconcile_confirmed_failure(
                self.prepared.request_id, authorization=permit,
                owner_password="wrong synthetic owner password",
                **{k: v for k, v in common.items() if k != "owner_password"})
        with patch("src.ai_copilot.p5_token_count_orchestrator.time.time",
                   return_value=permit.expires_at):
            with self.assertRaisesRegex(TokenCountWorkflowBlocked, "expired"):
                self.workflow.reconcile_confirmed_failure(
                    self.prepared.request_id, authorization=permit, **common)
        self.assertEqual(self.workflow.state_for_case("EV-01"),
                         TokenCountWorkflowState.UNKNOWN)
        with __import__("sqlite3").connect(self.db_path) as db:
            self.assertFalse(db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='token_count_reconciliation_events'").fetchone())

    def test_authenticated_event_records_reference_and_rejects_reuse(self):
        request_sha, response_sha = self._digests()
        reason = "Owner reviewed synthetic HTTP 400 evidence."
        permit = self.workflow.authorize_confirmed_failure(
            self.prepared.request_id, expected_request_sha256=request_sha,
            expected_response_sha256=response_sha, reason=reason,
            owner_password=self.owner_password)
        self.workflow.reconcile_confirmed_failure(
            self.prepared.request_id, expected_request_sha256=request_sha,
            expected_response_sha256=response_sha, reason=reason,
            confirmation=f"CONFIRM_FAILED {self.prepared.request_id}",
            authorization=permit, owner_password=self.owner_password)
        with __import__("sqlite3").connect(self.db_path) as db:
            raw = db.execute("SELECT event_json FROM token_count_reconciliation_events").fetchone()[0]
        event = json.loads(raw)
        self.assertEqual(event["authorization_ref"], permit.reference)
        self.assertEqual(event["actor"], permit.owner_identity_ref)
        self.assertEqual(event["authorization_purpose"], permit.purpose)
        self.assertTrue(P5TokenCountOrchestrator(
            exchange_path=self.exchange, state_path=self.db_path).workflow_resolved(
                self.prepared.request_id))
        with self.assertRaises(TokenCountWorkflowBlocked):
            self.workflow.reconcile_confirmed_failure(
                self.prepared.request_id, expected_request_sha256=request_sha,
                expected_response_sha256=response_sha, reason=reason,
                confirmation=f"CONFIRM_FAILED {self.prepared.request_id}",
                authorization=permit, owner_password=self.owner_password)

    def test_legacy_unauthenticated_event_cannot_release_gate(self):
        request_sha, response_sha = self._digests()
        import sqlite3
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM token_count_workflow WHERE request_id=?",
                             (self.prepared.request_id,)).fetchone()
            evidence = self.workflow._validated_failure_evidence(row, request_sha, response_sha)
            event = {
                "event_type": "TOKEN_COUNT_FAILURE_CLOSED",
                "resolution": "CONFIRMED_FAILED",
                "request_id": self.prepared.request_id,
                "case_id": row["case_id"], "run_id": row["run_id"],
                "payload_sha256": row["payload_sha256"],
                "count_projection_sha256": row["count_projection_sha256"],
                "actor": "LOCAL_OPERATOR_CONFIRMATION",
                "owner_confirmation": f"CONFIRM_FAILED {self.prepared.request_id}",
                "reason": "Synthetic historical unauthenticated event.",
                **evidence,
            }
            raw = canonical_json_bytes(event)
            self.workflow._ensure_reconciliation_schema(db)
            db.execute("INSERT INTO token_count_reconciliation_events VALUES (?,?,?,?)",
                       (self.prepared.request_id, hashlib.sha256(raw).hexdigest(),
                        raw, "2026-01-01T00:00:00Z"))
            db.execute("UPDATE token_count_workflow SET state='CONFIRMED_FAILED' WHERE request_id=?",
                       (self.prepared.request_id,))
        self.assertFalse(P5TokenCountOrchestrator(
            exchange_path=self.exchange, state_path=self.db_path).workflow_resolved(
                self.prepared.request_id))
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "unresolved"):
            self.workflow.assert_new_workflow_allowed("EV-02")


if __name__ == "__main__":
    unittest.main()
