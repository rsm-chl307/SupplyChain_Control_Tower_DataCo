"""WP3.6 schema and WAL backup rehearsal; all stores are isolated synthetic files."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.ai_copilot.wp36_qualification import (
    QualificationBlocked, backup_and_rehearse_paid_claim_extension,
    inspect_archive_schema, inspect_paid_ledger_schema, inspect_public_key_pair,
)
from src.ai_copilot.evaluation_archive import GenerationEvaluationArchive


PAID_TABLES = (
    "campaign", "slots", "slot_approvals", "reservations", "campaign_events",
    "paid_authorizations", "provider_observations", "dispatch_claims",
)


class PaidLedgerCopyRehearsalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="wp36-schema-fake-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "synthetic-ledger.sqlite3"
        self.writer = sqlite3.connect(self.source)
        self.addCleanup(self.writer.close)
        self.writer.execute("PRAGMA journal_mode=WAL")
        for name in PAID_TABLES:
            self.writer.execute(f"CREATE TABLE {name}(campaign_id TEXT, case_id TEXT)")
        self.writer.execute("INSERT INTO campaign VALUES ('synthetic-campaign','EV-99')")
        self.writer.commit()

    def test_online_backup_includes_uncheckpointed_wal_and_preserves_source(self):
        before = inspect_paid_ledger_schema(self.source)
        self.assertEqual(before.host_claim_state, "ABSENT")
        destination = self.root / "rehearsal.sqlite3"
        after = backup_and_rehearse_paid_claim_extension(self.source, destination)
        self.assertEqual(after.host_claim_state, "PRESENT")
        self.assertEqual(after.integrity, "ok")
        with sqlite3.connect(destination) as db:
            self.assertEqual(db.execute("SELECT * FROM campaign").fetchall(),
                             [("synthetic-campaign", "EV-99")])
            self.assertIn("host_owner_claims", {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")})
        self.assertEqual(inspect_paid_ledger_schema(self.source).host_claim_state,
                         "ABSENT")
        with self.assertRaises(QualificationBlocked):
            backup_and_rehearse_paid_claim_extension(self.source, destination)
        repository_output = (Path(__file__).resolve().parents[1] /
                             f"wp36-never-create-{self.root.name}.sqlite3")
        with self.assertRaises(QualificationBlocked):
            backup_and_rehearse_paid_claim_extension(self.source, repository_output)
        self.assertFalse(repository_output.exists())

    def test_partial_or_missing_schema_fails_before_copy(self):
        self.writer.execute("CREATE TABLE host_owner_claims(nonce TEXT)")
        self.writer.commit()
        self.assertEqual(inspect_paid_ledger_schema(self.source).host_claim_state,
                         "PARTIAL")
        target = self.root / "blocked.sqlite3"
        with self.assertRaises(QualificationBlocked):
            backup_and_rehearse_paid_claim_extension(self.source, target)
        self.assertFalse(target.exists())
        self.writer.execute("DROP TABLE host_owner_claims")
        self.writer.execute("DROP TABLE dispatch_claims")
        self.writer.commit()
        with self.assertRaises(QualificationBlocked):
            backup_and_rehearse_paid_claim_extension(self.source, target)
        self.assertFalse(target.exists())

    def test_missing_source_and_symlink_are_rejected(self):
        target = self.root / "out.sqlite3"
        with self.assertRaises(QualificationBlocked):
            backup_and_rehearse_paid_claim_extension(self.root / "missing", target)
        link = self.root / "link.sqlite3"
        link.symlink_to(self.source)
        with self.assertRaises(QualificationBlocked):
            inspect_paid_ledger_schema(link)
        self.assertFalse(target.exists())

    def test_public_key_roles_are_distinct_and_only_public_pins_are_read(self):
        host = self.root / "host-public.bin"
        issuer = self.root / "issuer-public.bin"
        host.write_bytes(Ed25519PrivateKey.generate().public_key().public_bytes_raw())
        issuer.write_bytes(Ed25519PrivateKey.generate().public_key().public_bytes_raw())
        pair = inspect_public_key_pair(host, issuer)
        self.assertEqual(len(pair.host_key_id), 64)
        self.assertNotEqual(pair.host_key_id, pair.issuer_key_id)
        with self.assertRaises(QualificationBlocked):
            inspect_public_key_pair(host, host)
        issuer.write_bytes(b"short")
        with self.assertRaises(QualificationBlocked):
            inspect_public_key_pair(host, issuer)

    def test_archive_structure_is_read_only_and_checks_append_only_triggers(self):
        archive = self.root / "synthetic-archive.sqlite3"
        GenerationEvaluationArchive.provision(str(archive))
        state = inspect_archive_schema(archive)
        self.assertEqual(state.integrity, "ok")
        self.assertTrue(state.contract_matches_source)
        self.assertEqual(state.event_table_state, "PRESENT")
        self.assertTrue(state.append_only_triggers_present)
        with sqlite3.connect(archive) as db:
            db.execute("DROP TRIGGER archive_dispatch_no_update")
        self.assertFalse(inspect_archive_schema(archive).append_only_triggers_present)

    def test_rehearsal_accepts_real_synthetic_paid_draft_schema(self):
        from tests.test_windows_generation_ledger import HostClaimTests
        fixture = HostClaimTests("test_valid_host_proof_claims_once_and_restarts")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = Path(fixture.ledger_path)
        self.assertEqual(inspect_paid_ledger_schema(source).host_claim_state,
                         "PRESENT")
        destination = self.root / "actual-contract-copy.sqlite3"
        result = backup_and_rehearse_paid_claim_extension(source, destination)
        self.assertEqual(result.host_claim_state, "PRESENT")
        self.assertEqual(result.integrity, "ok")
        with sqlite3.connect(source) as original, sqlite3.connect(destination) as copied:
            self.assertEqual(original.execute("SELECT COUNT(*) FROM campaign_events").fetchone(),
                             copied.execute("SELECT COUNT(*) FROM campaign_events").fetchone())
        with sqlite3.connect(destination) as legacy_copy:
            legacy_copy.execute("DROP TABLE host_owner_claims")
        extended = self.root / "legacy-contract-extension.sqlite3"
        result = backup_and_rehearse_paid_claim_extension(destination, extended)
        self.assertEqual(result.host_claim_state, "PRESENT")
        self.assertEqual(inspect_paid_ledger_schema(destination).host_claim_state, "ABSENT")
        with sqlite3.connect(source) as original, sqlite3.connect(extended) as copied:
            self.assertEqual(original.execute("SELECT COUNT(*) FROM campaign_events").fetchone(),
                             copied.execute("SELECT COUNT(*) FROM campaign_events").fetchone())


if __name__ == "__main__":
    unittest.main()
