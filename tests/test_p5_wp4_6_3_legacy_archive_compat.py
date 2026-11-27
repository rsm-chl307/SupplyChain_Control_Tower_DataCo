"""Focused, temporary-SQLite verification of the WP4.6.2 archive extension."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.ai_copilot.evaluation_archive import (
    GenerationEvaluationArchive,
)


class LegacyArchiveCompatibilityTests(unittest.TestCase):
    def _legacy_with_history(self):
        from tests.test_p5_evaluation_archive import EvaluationArchiveTests
        fixture = EvaluationArchiveTests("test_complete_lineage_persists_across_restart")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture._accounted()
        generation = fixture._generation()
        technical, case_result = fixture._assessment()
        fixture.ledger.record_case_review("EV-01", case_result,
                                         "eight-call-test-owner-password")
        evaluation = fixture.archive.append_evaluation(
            generation.record["record_id"], review=fixture.brief,
            technical=technical, result=case_result, campaign=fixture.ledger)
        with sqlite3.connect(fixture.archive_path) as db:
            db.execute("DROP TABLE archive_dispatch_events")
        return fixture, generation, evaluation

    def test_legacy_archive_is_identified_by_missing_event_table(self):
        with tempfile.TemporaryDirectory(prefix="p5-wp463-identify-") as folder:
            path = str(Path(folder) / "archive.sqlite")
            GenerationEvaluationArchive.provision(path)
            with sqlite3.connect(path) as db:
                db.execute("DROP TABLE archive_dispatch_events")
            self.assertEqual(GenerationEvaluationArchive.dispatch_event_schema_state(path),
                             "LEGACY_MISSING")

    def test_event_table_is_added_to_legacy_archive(self):
        with tempfile.TemporaryDirectory(prefix="p5-wp463-extend-") as folder:
            path = str(Path(folder) / "archive.sqlite")
            GenerationEvaluationArchive.provision(path)
            with sqlite3.connect(path) as db:
                db.execute("DROP TABLE archive_dispatch_events")
            self.assertEqual(GenerationEvaluationArchive.extend_legacy_event_schema(path),
                             "EXTENDED")
            self.assertEqual(GenerationEvaluationArchive.dispatch_event_schema_state(path),
                             "PRESENT")

    def test_generation_and_evaluation_data_remain_byte_identical(self):
        fixture, generation, evaluation = self._legacy_with_history()
        before = fixture.archive.history(generation.record["record_id"])
        self.assertEqual([entry.phase for entry in before], ["GENERATION", "EVALUATION"])
        self.assertEqual(GenerationEvaluationArchive.extend_legacy_event_schema(
            fixture.archive_path), "EXTENDED")
        after = GenerationEvaluationArchive(fixture.archive_path).history(
            generation.record["record_id"])
        self.assertEqual([entry.entry_digest for entry in after],
                         [generation.entry_digest, evaluation.entry_digest])
        self.assertEqual([entry.record for entry in after],
                         [entry.record for entry in before])
        self.assertEqual([entry.raw_response for entry in after],
                         [entry.raw_response for entry in before])

    def test_extended_legacy_archive_remains_readable_after_restart(self):
        fixture, generation, evaluation = self._legacy_with_history()
        GenerationEvaluationArchive.extend_legacy_event_schema(fixture.archive_path)
        restarted = GenerationEvaluationArchive(fixture.archive_path)
        entries = restarted.history(generation.record["record_id"])
        self.assertEqual(tuple(entry.phase for entry in entries), ("GENERATION", "EVALUATION"))
        self.assertEqual(entries[0].entry_digest, generation.entry_digest)
        self.assertEqual(entries[1].entry_digest, evaluation.entry_digest)

    def test_extended_legacy_archive_accepts_fake_dispatch_lifecycle(self):
        from tests.test_p5_wp4_6_2_archive_lifecycle import ArchiveLifecycleTests
        fixture, generation, evaluation = self._legacy_with_history()
        GenerationEvaluationArchive.extend_legacy_event_schema(fixture.archive_path)
        lifecycle = ArchiveLifecycleTests("test_success_appends_response_result_and_preserves_lineage")
        lifecycle.setUp()
        self.addCleanup(lifecycle.doCleanups)
        lifecycle.archive = GenerationEvaluationArchive(fixture.archive_path)
        result = lifecycle._dispatch(lifecycle._valid_transport())
        self.assertEqual(result.status, "SUCCEEDED")
        with sqlite3.connect(lifecycle.archive.path) as db:
            dispatch_id = db.execute(
                "SELECT dispatch_id FROM archive_dispatch_events LIMIT 1").fetchone()[0]
        events = lifecycle.archive.dispatch_events(dispatch_id)
        self.assertEqual([event["event_type"] for event in events],
                         ["GENERATION_INTENT", "GENERATION_RESULT"])
        legacy = lifecycle.archive.history(generation.record["record_id"])
        self.assertEqual([entry.entry_digest for entry in legacy],
                         [generation.entry_digest, evaluation.entry_digest])

    def test_repeating_extension_is_idempotent_and_preserves_history(self):
        fixture, generation, evaluation = self._legacy_with_history()
        self.assertEqual(GenerationEvaluationArchive.extend_legacy_event_schema(
            fixture.archive_path), "EXTENDED")
        first = GenerationEvaluationArchive(fixture.archive_path).history(
            generation.record["record_id"])
        self.assertEqual(GenerationEvaluationArchive.extend_legacy_event_schema(
            fixture.archive_path), "ALREADY_PRESENT")
        second = GenerationEvaluationArchive(fixture.archive_path).history(
            generation.record["record_id"])
        self.assertEqual([entry.entry_digest for entry in second],
                         [entry.entry_digest for entry in first])
        self.assertEqual([entry.entry_digest for entry in second],
                         [generation.entry_digest, evaluation.entry_digest])


if __name__ == "__main__":
    unittest.main()
