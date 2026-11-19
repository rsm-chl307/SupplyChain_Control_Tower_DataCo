"""Phase 1 R1–R3 focused reliability tests; no planning or publication.

Fixtures are disposable, invalid copies of the approved existing input. They
never invoke a planning runner or mutate an existing Run. The Run-switch AppTest
is a selector-only fixture and is not Published Run browser E2E evidence.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
PRIMARY = REPO / 'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'
EVIDENCE = Path(os.environ.get('PHASE1_EVIDENCE_ROOT', str(
    REPO / 'tmp/phase_1_reliability/20261119T034337Z_f91753')))
_GUARDS = []
_RUNNER_MOCKS = []


def setUpModule():
    """Guard before importing the dashboard or comparison loader."""
    for name in ['run_csv_planning', 'run_sequential_planning']:
        guard = patch('src.run_planning.' + name,
                      side_effect=AssertionError('Phase 1 risk tests must not execute planning'))
        _RUNNER_MOCKS.append(guard.start())
        _GUARDS.append(guard)


def tearDownModule():
    for guard in reversed(_GUARDS):
        guard.stop()
    _GUARDS.clear()


class ManifestShapeTests(unittest.TestCase):
    """Exercise the real loader against independent malformed shapes."""

    def setUp(self):
        from dashboard.scenario_planning_app import load_sequential_outputs
        self.load = load_sequential_outputs
        self.manifest = json.loads((PRIMARY / 'run_manifest.json').read_text())
        # Only ephemeral fixture directories are written; native inputs stay intact.
        self.temporary = tempfile.TemporaryDirectory(prefix='r1_', dir=EVIDENCE / 'fixtures')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        for record in self.manifest['Artifacts'].values():
            shutil.copyfile(PRIMARY / record['Path'], self.folder / record['Path'])

    def assert_rejected(self, manifest, field):
        (self.folder / 'run_manifest.json').write_text(json.dumps(manifest))
        # ValueError is the published loader/UI's controlled rejection contract.
        # Matching the relevant field prevents an unrelated hash/file failure
        # from accidentally satisfying a shape test.
        with self.assertRaisesRegex(ValueError, field):
            self.load(self.folder, include_evidence=True)

    def test_valid_existing_manifest_still_loads(self):
        (self.folder / 'run_manifest.json').write_text(json.dumps(self.manifest))
        actual = self.load(self.folder, include_evidence=True)
        self.assertEqual(len(actual['allocation']), 60)
        self.assertEqual(set(actual['allocation'].Run_ID), {self.manifest['Run_ID']})

    def test_null_root_is_controlled_rejection(self):
        self.assert_rejected(None, '(?i)manifest')

    def test_list_root_is_controlled_rejection(self):
        self.assert_rejected([], '(?i)manifest')

    def test_scalar_root_is_controlled_rejection(self):
        self.assert_rejected('not-an-object', '(?i)manifest')

    def test_artifacts_list_is_controlled_rejection(self):
        self.manifest['Artifacts'] = list(self.manifest['Artifacts'])
        self.assert_rejected(self.manifest, '(?i)artifacts')

    def test_artifact_record_null_is_controlled_rejection(self):
        self.manifest['Artifacts']['allocation_result'] = None
        self.assert_rejected(self.manifest, '(?i)artifact')

    def test_configuration_list_is_controlled_rejection(self):
        self.manifest['Configuration'] = []
        self.assert_rejected(self.manifest, '(?i)configuration')

    def test_scenarios_scalar_is_controlled_rejection(self):
        self.manifest['Configuration']['scenarios'] = 'Baseline'
        self.assert_rejected(self.manifest, '(?i)scenario')

    def test_scenario_record_scalar_is_controlled_rejection(self):
        self.manifest['Configuration']['scenarios'] = ['Baseline']
        self.assert_rejected(self.manifest, '(?i)scenario')

    def test_scope_list_is_controlled_rejection(self):
        self.manifest['Scope'] = []
        self.assert_rejected(self.manifest, '(?i)scope')

    def test_horizon_scalar_is_controlled_rejection(self):
        self.manifest['Scope']['Planning_Horizon'] = '2017-01-08'
        self.assert_rejected(self.manifest, '(?i)horizon|scope')

    def test_product_ids_scalar_is_controlled_rejection(self):
        self.manifest['Scope']['Product_IDs'] = 'SKU-A'
        self.assert_rejected(self.manifest, '(?i)product|scope')

    def test_run_id_container_is_controlled_rejection(self):
        for invalid in [[], {}]:
            with self.subTest(run_id=invalid):
                manifest = copy.deepcopy(self.manifest)
                manifest['Run_ID'] = invalid
                self.assert_rejected(manifest, '(?i)run_id')


class RunSwitchWireTests(unittest.TestCase):
    """Same scenario names, distinct Run identities, no artifact-loader bypass claim."""

    def selected_app(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string('''
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from dashboard.scenario_planning_app import _scenario_tradeoff_analysis

run = st.selectbox("Test fixture Run", ["Run-A", "Run-B"], key="fixture_run")
manifest = {"Run_ID": run, "Configuration": {"scenarios": [
    {"Scenario": s} for s in ["Baseline", "Combined_Stress", "Demand_Surge"]
]}}
with patch("src.comparison_io.load_comparison_input", side_effect=ValueError("Selector-only fixture; no Run is generated")):
    _scenario_tradeoff_analysis(Path("unused-selector-fixture"), manifest)
''', default_timeout=30).run()
        self.assertFalse(app.exception)
        app.selectbox(key='wp2_reference').set_value('Baseline').run()
        app.selectbox(key='wp2_candidate').set_value('Combined_Stress').run()
        app.multiselect(key='wp2_priorities').set_value([3]).run()
        self.assertFalse(app.exception)
        return app

    def test_run_switch_reference_sends_explicit_clear(self):
        app = self.selected_app()
        app.selectbox(key='fixture_run').set_value('Run-B').run()
        self.assertFalse(app.exception)
        box = app.selectbox(key='wp2_reference')
        self.assertIsNone(box.value)
        self.assertTrue(box.proto.set_value)
        self.assertEqual(box.proto.raw_value, '')

    def test_run_switch_priorities_sends_explicit_clear(self):
        app = self.selected_app()
        app.selectbox(key='fixture_run').set_value('Run-B').run()
        self.assertFalse(app.exception)
        priorities = app.multiselect(key='wp2_priorities')
        self.assertEqual(priorities.value, [])
        self.assertTrue(priorities.proto.set_value)
        self.assertEqual(list(priorities.proto.raw_values), [])

    def test_round_trip_never_silently_reselects_old_pair(self):
        app = self.selected_app()
        for run in ['Run-B', 'Run-A']:
            app.selectbox(key='fixture_run').set_value(run).run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.selectbox(key='wp2_reference').value)
            self.assertIsNone(app.selectbox(key='wp2_candidate').value)
            self.assertEqual(app.multiselect(key='wp2_priorities').value, [])
            self.assertNotIn('Download Comparison CSV', [x.label for x in app.get('download_button')])


class PriorityTypeTests(unittest.TestCase):
    def value(self, values):
        from src.scenario_comparison import ComparisonInput, ComparisonScope
        frame = pd.DataFrame({'Scenario': ['Baseline'] * len(values), 'Plant_ID': ['P'] * len(values),
                              'Product Card Id': ['SKU'] * len(values),
                              'Order_Date': pd.date_range('2017-01-08', periods=len(values), freq='W-SUN'),
                              'Planning_Priority': values})
        return ComparisonInput({'Run_ID': 'memory-only'}, {'allocation': frame}, 'Baseline'), ComparisonScope(
            ('SKU',), ('P',), '2017-01-08', str(frame.Order_Date.iloc[-1].date()), (1,))

    def assert_invalid(self, values):
        from src.scenario_comparison import _priority
        value, scope = self.value(values)
        before = value.tables['allocation'].copy(deep=True)
        priority, reason = _priority(value, scope, 'SKU')
        self.assertIsNone(priority)
        self.assertRegex(reason, '(?i)priority')
        assert_frame_equal(before, value.tables['allocation'])

    def test_true_priority_is_not_integer_one(self):
        self.assert_invalid([True])

    def test_mixed_boolean_integer_priority_is_invalid(self):
        self.assert_invalid(pd.Series([1, True], dtype=object))

    def test_other_invalid_priority_values_are_explicit(self):
        for value in [False, None, float('nan'), float('inf'), '1', '3', 0, 4, 1.5]:
            with self.subTest(value=repr(value)):
                self.assert_invalid([value])

    def test_inconsistent_priority_trajectory_is_invalid(self):
        self.assert_invalid([1, 3])

    def test_valid_numeric_priorities_remain_valid(self):
        from src.scenario_comparison import _priority
        for value in [1, 2, 3, 1.0, 3.0]:
            with self.subTest(value=value):
                data, scope = self.value([value])
                self.assertEqual(_priority(data, scope, 'SKU'), (int(value), ''))

    def test_planner_numeric_contract_rejects_boolean_dtype(self):
        from src.planning_inputs import numeric
        with self.assertRaisesRegex(ValueError, 'numeric dtype'):
            numeric(pd.DataFrame({'Planning_Priority': [True]}), ['Planning_Priority'])


def execution_allowlist():
    """AST-only inventory: includes setup and same-class helper call effects."""
    names = ['test_inventory_transition.py', 'test_independent_validation_upgrade.py',
             'test_planning_inputs_upgrade.py', 'test_sequential_upgrade.py', 'test_planning_risk.py',
             'test_dashboard_app.py', 'test_scenario_comparison.py', 'test_comparison_dashboard.py',
             'test_comparison_acceptance.py']
    result = []
    forbidden = {'run_csv_planning', 'run_sequential_planning', 'run_planning'}
    for filename in names:
        tree = ast.parse((REPO / 'tests' / filename).read_text())
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        methods = {c: {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                   for c, node in classes.items()}
        def calls(node):
            return {n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                    for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
        def effects(c, method, seen=None):
            seen = set() if seen is None else set(seen)
            if (c, method) in seen:return set()
            seen.add((c, method))
            node = methods[c].get(method)
            if node is None:
                out = set()
                for base in classes[c].bases:
                    if isinstance(base, ast.Name) and base.id in classes:
                        out |= effects(base.id, method, seen)
                return out
            out = calls(node)
            for call in list(out):
                if call in methods[c]:out |= effects(c, call, seen)
            return out
        for c, own in methods.items():
            for method in own:
                if not method.startswith('test_'):continue
                callset = effects(c, method) | effects(c, 'setUpClass') | effects(c, 'setUp')
                blocked = sorted(callset & forbidden)
                writes = sorted(callset & {'to_csv', 'write_text', 'write_bytes', 'copytree', 'unlink'})
                result.append({'test': 'tests.' + filename[:-3] + '.' + c + '.' + method,
                    'line': own[method].lineno, 'runner_calls_in_test_or_setup': blocked,
                    'other_write_calls_require_fixture_review': writes,
                    'classification': 'EXCLUDE_RUNNER_SETUP_OR_BODY' if blocked else
                        'REVIEW_ISOLATED_WRITES' if writes else 'SAFE_CANDIDATE_MANUAL_REVIEW',
                    'memory_simulation_calls': sorted(callset & {'simulate_sequential', 'run_case', 'allocate_capacity'})})
    return {'method_inventory': result,
            'limits': 'Static inventory, not a permission to run whole classes; inherited and helper calls included where local. Dynamic imports/aliases still require manual review.',
            'excluded_original_classes': ['tests.test_scenario_comparison.PublishedFixture and subclasses',
                'tests.test_comparison_dashboard.ComparisonDashboardTests',
                'tests.test_dashboard_app.InvestigationAppTests', 'tests.test_comparison_acceptance.ComparisonAcceptanceTests'],
            'safe_selector_class': 'tests.test_comparison_dashboard.CandidateSelectionSyncTests',
            'historical_adapter': 'tmp/wp2_browser_uat_phase_2/safe_python_regression.py (reuse design, never overwrite outputs)'}


def run_report(label):
    records = []
    class RecordingResult(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test); records.append({'test': test.id(), 'status': 'PASS'})
        def addFailure(self, test, error):
            super().addFailure(test, error); records.append({'test': test.id(), 'status': 'FAIL',
                'details': self._exc_info_to_string(error, test)})
        def addError(self, test, error):
            super().addError(test, error); records.append({'test': test.id(), 'status': 'ERROR',
                'details': self._exc_info_to_string(error, test)})
        def addSubTest(self, test, subtest, error):
            super().addSubTest(test, subtest, error)
            if error:records.append({'test': test.id(), 'status': 'FAIL', 'subtest': str(subtest),
                'details': self._exc_info_to_string(error, test)})
    suite = unittest.TestSuite()
    for cls in [ManifestShapeTests, RunSwitchWireTests, PriorityTypeTests]:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    # An explicit suite preserves module fixtures while excluding unrelated tests.
    with (EVIDENCE / 'logs' / ('risk_' + label + '.log')).open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordingResult).run(suite)
    report = {'label': label, 'tests_run': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped), 'records': records,
              'planning_runner_attempts': sum(mock.call_count for mock in _RUNNER_MOCKS),
              'planning_runner_executed': False,
              'fixtures': 'Disposable copies under evidence/fixtures, auto-cleanup; no historical Run mutation',
              'browser_coverage': False}
    (EVIDENCE / 'reports' / ('risk_' + label + '_results.json')).write_text(json.dumps(report, indent=2))
    (EVIDENCE / 'reports' / ('test_allowlist_' + label + '.json')).write_text(json.dumps(execution_allowlist(), indent=2))
    print(json.dumps({k: report[k] for k in ['label', 'tests_run', 'failures', 'errors', 'skipped']}, indent=2))
    return result.wasSuccessful()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', choices=['red', 'green'], default='red')
    args = parser.parse_args()
    raise SystemExit(0 if run_report(args.label) else 1)
