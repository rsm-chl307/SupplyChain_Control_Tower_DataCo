"""Offline, disposable synthetic harness tests; no historical Run adoption."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.synthetic_context import ContextRejected, SyntheticContext, SyntheticHarness


class HarnessSmokeTests(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_valid_fixed_synthetic_context(self):
        with SyntheticHarness() as harness:
            context = harness.issue('Baseline')
            result = harness.verify(context)
            self.assertEqual(result.run_id, context.run_id)
            self.assertEqual(result.scenario, 'Baseline')
            self.assertEqual(len(result.artifact_hashes), 12)
            self.assertFalse(hasattr(result, 'path'))

    def test_context_is_immutable(self):
        with SyntheticHarness() as harness:
            context = harness.issue('Baseline')
            with self.assertRaises(FrozenInstanceError):
                context.scenario = 'Combined_Stress'

    def test_no_path_or_configuration_import_api(self):
        with self.assertRaises(TypeError):
            SyntheticHarness('/some/historical/run')
        with self.assertRaises(TypeError):
            SyntheticHarness(config={'data_mode': 'SYNTHETIC_DEMO'})


class HarnessSecurityTests(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.harness = SyntheticHarness()
        self.addCleanup(self.harness.close)
        self.context = self.harness.issue('Baseline')
        self.run = self.harness._run_path  # White-box tampering ONLY inside owned test workspace.

    def manifest_change(self, callback):
        path = self.run / 'run_manifest.json'
        data = json.loads(path.read_text())
        callback(data)
        path.write_text(json.dumps(data))

    def rejected_without_inspection(self, context):
        with patch.object(self.harness, '_inspect', side_effect=AssertionError('No access before auth')) as read:
            with self.assertRaises(ContextRejected):
                self.harness.verify(context)
            read.assert_not_called()

    def test_constructed_context_rejected(self):
        self.rejected_without_inspection(replace(self.context))

    def test_forged_signature_rejected(self):
        self.rejected_without_inspection(replace(self.context, signature='0' * 64))

    def test_arbitrary_path_is_not_a_context(self):
        self.rejected_without_inspection('/some/historical/run')

    def test_cross_harness_rejected(self):
        with SyntheticHarness() as other:
            with patch.object(other, '_inspect', side_effect=AssertionError('Unauthorized file access')):
                with self.assertRaises(ContextRejected):
                    other.verify(self.context)

    def test_cross_run_rejected(self):
        self.rejected_without_inspection(replace(self.context, run_id='another-run'))

    def test_registered_context_tampering_rejected(self):
        object.__setattr__(self.context, 'scenario', 'Combined_Stress')
        self.rejected_without_inspection(self.context)

    def test_expiry_checked_before_access(self):
        with patch('src.synthetic_context.time.monotonic', return_value=self.context.expires_at + 1):
            self.rejected_without_inspection(self.context)

    def test_closed_harness_revokes_context(self):
        self.harness.close()
        self.rejected_without_inspection(self.context)

    def test_scenario_not_approved(self):
        with self.assertRaises(ContextRejected):
            self.harness.issue('../other-run')

    def test_changed_manifest_invalidates_context(self):
        self.manifest_change(lambda m: m.update(Finished_At='2099-01-01T00:00:00Z'))
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_modified_artifact_invalidates_context(self):
        with (self.run / 'allocation_result.csv').open('ab') as f:
            f.write(b'\n')
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_updated_artifact_and_manifest_hash_still_rejected(self):
        p = self.run / 'allocation_result.csv'
        p.write_bytes(p.read_bytes() + b'\n')
        self.manifest_change(lambda m: m['Artifacts']['allocation_result'].update(
            SHA256=hashlib.sha256(p.read_bytes()).hexdigest()))
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_user_data_rejected(self):
        self.manifest_change(lambda m: m.update(Data_Mode='USER_DATA'))
        with self.assertRaises(ContextRejected):
            self.harness.issue('Baseline')

    def test_missing_publication_rejected(self):
        self.manifest_change(lambda m: m.pop('Publication_Status'))
        with self.assertRaises(ContextRejected):
            self.harness.issue('Baseline')

    def test_failed_lifecycle_rejected(self):
        self.manifest_change(lambda m: m.update(Execution_Status='FAILED'))
        with self.assertRaises(ContextRejected):
            self.harness.issue('Baseline')

    def test_unpublished_rejected(self):
        self.manifest_change(lambda m: m.update(Publication_Status='UNPUBLISHED'))
        with self.assertRaises(ContextRejected):
            self.harness.issue('Baseline')

    def test_missing_artifact_rejected(self):
        (self.run / 'initial_state.csv').unlink()
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_row_count_rejected(self):
        self.manifest_change(lambda m: m['Artifacts']['allocation_result'].update(Rows=999))
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_path_traversal_rejected(self):
        self.manifest_change(lambda m: m['Artifacts']['allocation_result'].update(Path='../escape.csv'))
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_artifact_symlink_rejected(self):
        p = self.run / 'allocation_result.csv'
        outside = self.run.parent / 'outside.csv'
        outside.write_bytes(p.read_bytes())
        p.unlink()
        p.symlink_to(outside)
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_manifest_symlink_rejected(self):
        p = self.run / 'run_manifest.json'
        outside = self.run.parent / 'outside.json'
        outside.write_bytes(p.read_bytes())
        p.unlink()
        p.symlink_to(outside)
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_run_directory_symlink_rejected(self):
        p = self.run
        moved = p.with_name(p.name + '-moved')
        p.rename(moved)
        p.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_verification_is_read_only(self):
        before = {p.name: p.read_bytes() for p in self.run.iterdir()}
        self.harness.verify(self.context)
        after = {p.name: p.read_bytes() for p in self.run.iterdir()}
        self.assertEqual(before, after)

    def test_fixture_label_does_not_establish_provenance(self):
        import shutil
        import tempfile
        from src.synthetic_context import _FIXTURE
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for p in _FIXTURE.iterdir():
                if p.is_file():
                    shutil.copyfile(p, root / p.name)
            with (root / 'products.csv').open('ab') as f:
                f.write(b'\n')
            with patch('src.synthetic_context._FIXTURE', root), patch('src.run_planning.run_csv_planning') as runner:
                with self.assertRaises(ContextRejected):
                    SyntheticHarness()
                runner.assert_not_called()

    def test_invalid_publication_never_issues_first_context(self):
        from src.run_planning import run_csv_planning
        def corrupt(*args, **kwargs):
            result = run_csv_planning(*args, **kwargs)
            path = result['run_manifest']
            m = json.loads(path.read_text())
            m['Data_Mode'] = 'USER_DATA'
            path.write_text(json.dumps(m))
            return result
        with patch('src.run_planning.run_csv_planning', side_effect=corrupt):
            with self.assertRaises(ContextRejected):
                SyntheticHarness()

    def test_malformed_registered_nonce_is_rejected_without_access(self):
        object.__setattr__(self.context, 'nonce', [])
        self.rejected_without_inspection(self.context)

    def test_cross_run_manifest_identity_is_rejected(self):
        self.manifest_change(lambda m: m.update(Run_ID='unrelated-run'))
        with self.assertRaises(ContextRejected):
            self.harness.verify(self.context)

    def test_invalid_schema_is_rejected(self):
        self.manifest_change(lambda m: m.update(Schema_Version='unapproved_schema'))
        with self.assertRaises(ContextRejected):
            self.harness.issue('Baseline')
