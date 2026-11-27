"""Isolated checks for the approved eight-case state namespace."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.ai_copilot.evaluation_namespace import (
    EvaluationNamespace, NamespaceBlocked, NAMESPACE_ID, _approved_registry,
)
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator, TokenCountWorkflowBlocked,
)
from src.ai_copilot.local_token_count_e2e import _load_case, _make_trusted_request
from src.ai_copilot.windows_runner_exchange import PreparedCountRequest
from src.ai_copilot.windows_runner_exchange import EXCHANGE_PATH_ENV


class EvaluationNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p5-namespace-")
        self.addCleanup(self.temp.cleanup)
        self.legacy = Path(self.temp.name) / "legacy"
        self.legacy.mkdir()
        self.namespace = EvaluationNamespace.mapping(legacy_exchange=self.legacy)

    def _legacy_state(self, state="UNKNOWN", request_id="00000000-0000-4000-8000-000000000001"):
        db_path = self.legacy / ".p5_token_count_workflow.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.execute("""CREATE TABLE token_count_workflow (
                case_id TEXT PRIMARY KEY, state TEXT NOT NULL,
                request_id TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL,
                run_manifest_sha256 TEXT NOT NULL, brief_digest TEXT NOT NULL,
                provider_request_digest TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                count_projection_sha256 TEXT NOT NULL, created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL)""")
            db.execute("INSERT INTO token_count_workflow VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       ("EV-01", state, request_id, "historical-run", *("a" * 64,)*5,
                        "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
        return db_path

    def test_pinned_identity_mapping_and_restart(self):
        self._legacy_state("COLLECTED")
        registry, corpus = _approved_registry()
        self.namespace.create()
        self.namespace.verify()
        data = json.loads((self.namespace.container_exchange / "namespace.json").read_text())
        self.assertEqual((data["registry_sha256"], data["corpus_sha256"]),
                         (registry, corpus))
        self.assertEqual(data["model"], "gpt-6-luna")
        self.assertEqual(data["case_ids"],
                         [f"EV-{number:02d}" for number in range(1, 8)] + ["EV-08-LR"])
        self.assertEqual(self.namespace.container_exchange,
                         self.legacy / "evaluations" / NAMESPACE_ID)
        self.assertTrue(str(self.namespace.windows_exchange).endswith(
            "\\evaluations\\" + NAMESPACE_ID))
        self.assertEqual(self.namespace.count_environment(),
                         {EXCHANGE_PATH_ENV: str(self.namespace.container_exchange)})
        self.namespace.assert_legacy_resolved()
        EvaluationNamespace.mapping(legacy_exchange=self.legacy).verify()
        with self.assertRaises(NamespaceBlocked):
            self.namespace.create()

    def test_unresolved_history_cannot_be_hidden_by_namespace(self):
        db_path = self._legacy_state()
        before = db_path.read_bytes()
        self.namespace.create()
        with self.assertRaisesRegex(NamespaceBlocked, "unresolved"):
            self.namespace.assert_legacy_resolved()
        with self.assertRaisesRegex(NamespaceBlocked, "unresolved"):
            self.namespace.count_environment()
        workflow = P5TokenCountOrchestrator(exchange_path=self.namespace.container_exchange)
        with self.assertRaisesRegex(TokenCountWorkflowBlocked, "Historical count workflow"):
            workflow.assert_new_workflow_allowed("EV-02")
        self.assertFalse(workflow.state_path.exists())
        self.assertEqual(db_path.read_bytes(), before)
        with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as db:
            self.assertEqual(db.execute("SELECT state FROM token_count_workflow").fetchone()[0],
                             "UNKNOWN")

    def test_collision_and_tampered_metadata_fail_closed(self):
        old_id = "00000000-0000-4000-8000-000000000001"
        self._legacy_state("COLLECTED", old_id)
        self.namespace.create()
        with self.assertRaisesRegex(NamespaceBlocked, "collides"):
            self.namespace.assert_request_id_unshared(old_id)
        sibling = self.legacy / "evaluations" / "other-version" / "requests"
        sibling.mkdir(parents=True)
        sibling_id = "00000000-0000-4000-8000-000000000002"
        (sibling / (sibling_id + ".json")).write_text("synthetic")
        with self.assertRaisesRegex(NamespaceBlocked, "collides"):
            self.namespace.assert_request_id_unshared(sibling_id)
        self.namespace.assert_request_id_unshared("00000000-0000-4000-8000-000000000003")
        target = self.namespace.container_exchange / "namespace.json"
        changed = target.read_bytes().replace(b"gpt-6-luna", b"wrong-model")
        target.write_bytes(changed)
        with self.assertRaises(NamespaceBlocked):
            self.namespace.verify()

    def test_production_prepare_rejects_historical_uuid_collision(self):
        old_id = "00000000-0000-4000-8000-000000000001"
        self._legacy_state("COLLECTED", old_id)
        self.namespace.create()
        with patch.dict("os.environ", {EXCHANGE_PATH_ENV: str(self.namespace.container_exchange)}):
            workflow = P5TokenCountOrchestrator(exchange_path=self.namespace.container_exchange)
            harness, review, request = _make_trusted_request(_load_case("EV-02"))
            self.addCleanup(harness.close)
            prepared = PreparedCountRequest(old_id,
                self.namespace.container_exchange / "requests" / (old_id + ".json"),
                "EV-02", "synthetic-run", *("a" * 64,)*5)
            with patch("src.ai_copilot.p5_token_count_orchestrator.prepare_configured_count_request",
                       return_value=prepared):
                with self.assertRaisesRegex(TokenCountWorkflowBlocked, "UUID collides"):
                    workflow.prepare("EV-02", review, request)
            self.assertEqual(workflow.records(), ())

    def test_registry_change_and_missing_history_fail_closed(self):
        self.namespace.create()
        with self.assertRaisesRegex(NamespaceBlocked, "unavailable"):
            self.namespace.assert_legacy_resolved()
        with patch("src.ai_copilot.evaluation_namespace.PAID_CORPUS_SHA256", "0" * 64):
            with self.assertRaisesRegex(NamespaceBlocked, "corpus changed"):
                self.namespace.verify()


if __name__ == "__main__":
    unittest.main()
