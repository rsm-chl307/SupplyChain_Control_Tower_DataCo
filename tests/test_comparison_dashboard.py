"""WP2.4 UI gates: explicit selections, exports and WP1 handoff in both modes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.run_planning import run_csv_planning

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'dashboard/scenario_planning_app.py'


class CandidateSelectionSyncTests(unittest.TestCase):
    """Exercise only WP2 selectors; no planning, artifacts or Run creation."""

    def open_selectors(self):
        app = AppTest.from_string('''
from pathlib import Path
from unittest.mock import patch
from dashboard.scenario_planning_app import _scenario_tradeoff_analysis

manifest = {"Run_ID": "selector-test", "Configuration": {"scenarios": [
    {"Scenario": name} for name in ["Baseline", "Combined_Stress", "Demand_Surge"]
]}}
with patch("src.comparison_io.load_comparison_input", side_effect=ValueError("Selector-only test")):
    _scenario_tradeoff_analysis(Path("unused-selector-test"), manifest)
''', default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def test_initial_selections_are_empty(self):
        app = self.open_selectors()
        self.assertIsNone(app.selectbox(key='wp2_reference').value)
        self.assertIsNone(app.selectbox(key='wp2_candidate').value)

    def test_invalid_candidate_sends_explicit_clear_to_browser(self):
        app = self.open_selectors()
        app.selectbox(key='wp2_reference').set_value('Baseline').run()
        app.selectbox(key='wp2_candidate').set_value('Combined_Stress').run()
        app.selectbox(key='wp2_reference').set_value('Combined_Stress').run()
        self.assertFalse(app.exception)
        candidate = app.selectbox(key='wp2_candidate')
        self.assertIsNone(candidate.value)
        self.assertNotIn('Combined_Stress', candidate.options)
        self.assertTrue(candidate.proto.set_value)
        self.assertEqual(candidate.proto.raw_value, '')
        self.assertTrue(any('Select both Reference and Candidate.' in x.value for x in app.info))
        app.selectbox(key='wp2_candidate').set_value('Baseline').run()
        self.assertEqual(app.selectbox(key='wp2_candidate').value, 'Baseline')
        self.assertFalse(app.exception)

    def test_valid_candidate_survives_reference_change(self):
        app = self.open_selectors()
        app.selectbox(key='wp2_reference').set_value('Baseline').run()
        app.selectbox(key='wp2_candidate').set_value('Combined_Stress').run()
        app.selectbox(key='wp2_reference').set_value('Demand_Surge').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='wp2_candidate').value, 'Combined_Stress')


class ComparisonDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        allowed_root = ROOT / 'tmp/planning_source_runs'
        allowed_root.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=allowed_root)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.runs = {}
        for mode in ['synthetic_demo', 'user_data']:
            folder = ROOT / 'examples/planning' / mode
            config = json.loads((folder / 'config.json').read_text())
            paths = run_csv_planning(config, inputs_dir=folder, output_root=cls.temp.name)
            cls.runs[mode] = paths['run_manifest'].parent
        folder = ROOT / 'examples/planning/synthetic_demo'
        config = json.loads((folder/'config.json').read_text())
        config['scenarios'][-1]['Backlog_Policy'] = 'LOST_SALES'
        paths = run_csv_planning(config, inputs_dir=folder, output_root=cls.temp.name)
        cls.policy_run = paths['run_manifest'].parent

    def open_run(self, directory):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        next(x for x in app.sidebar.text_input if x.label == 'Published sequential run folder').set_value(str(directory)).run()
        self.assertFalse(app.exception)
        return app

    def select_pair(self, app):
        app.selectbox(key='wp2_reference').set_value('Baseline').run()
        app.selectbox(key='wp2_candidate').set_value('Combined_Stress').run()
        self.assertFalse(app.exception)
        return app

    def test_explicit_selection_no_default_scenario_or_priority_both_modes(self):
        for mode, directory in self.runs.items():
            with self.subTest(mode=mode):
                app = self.open_run(directory)
                self.assertIn('Scenario Trade-off Analysis', [x.label for x in app.get('tab')])
                self.assertIsNone(app.selectbox(key='wp2_reference').value)
                self.assertIsNone(app.selectbox(key='wp2_candidate').value)
                self.assertEqual(app.multiselect(key='wp2_priorities').value, [])
                self.assertNotIn('Download Comparison CSV', [x.label for x in app.get('download_button')])
                self.select_pair(app)
                self.assertIn('Download Comparison CSV', [x.label for x in app.get('download_button')])
                self.assertTrue(any(x.value.astype(str).eq('N/A').any().any() for x in app.dataframe))

    def test_render_cohorts_metrics_evidence_exports_and_wp1_handoff_both_modes(self):
        for mode, directory in self.runs.items():
            with self.subTest(mode=mode):
                before = {p.name:p.read_bytes() for p in directory.iterdir()}
                with patch('src.run_planning.run_csv_planning', side_effect=AssertionError('unexpected planning')), \
                     patch('src.run_planning.run_sequential_planning', side_effect=AssertionError('unexpected planning')):
                    app = self.select_pair(self.open_run(directory))
                    app.multiselect(key='wp2_priorities').set_value([3]).run()
                    self.assertFalse(app.exception)
                    frames = [x.value for x in app.dataframe]
                    membership = next(f for f in frames if 'Cohort Membership' in f)
                    self.assertTrue(membership['Cohort Membership'].isin(['SELECTED','COMPLEMENT']).all())
                    summary = next(f for f in frames if 'Cohort_ID' in f and 'Delta' in f and len(f)==15)
                    self.assertEqual(set(summary.Cohort_ID), {'ALL','SELECTED','COMPLEMENT'})
                    self.assertIn('Comparability_Status', summary)
                    self.assertIn('Reason', summary)
                    self.assertTrue(any('Artifact_SHA256' in f for f in frames))
                    for label in ['Download Comparison CSV', 'Download Comparison Cohort',
                                  'Download Comparison Evidence References', 'Download Comparison Context']:
                        self.assertIn(label, [x.label for x in app.get('download_button')])
                    product = str(membership['Product Card Id'].iloc[0])
                    app.selectbox(key='wp2_product').set_value(product).run()
                    for side, scenario in [('candidate','Combined_Stress'), ('reference','Baseline')]:
                        app.button(key=f'wp2_investigate_{side}').click().run()
                        self.assertFalse(app.exception)
                        self.assertEqual(app.selectbox(key='sequential_scenario').value, scenario)
                        self.assertEqual(app.selectbox(key='investigation_product').value, product)
                        for path in ['Product → Plant → Week','Plant → Week → Product']:
                            app.selectbox(key='investigation_path').set_value(path).run()
                            self.assertFalse(app.exception)
                            self.assertIn('Download selected_week investigation evidence',
                                          [x.label for x in app.get('download_button')])
                self.assertEqual(before, {p.name:p.read_bytes() for p in directory.iterdir()})

    def test_policy_contrast_reasons_and_na_are_visible(self):
        app = self.select_pair(self.open_run(self.policy_run))
        app.multiselect(key='wp2_priorities').set_value([3]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('POLICY_CONTRAST' in x.value for x in app.warning))
        frames = [x.value for x in app.dataframe]
        self.assertTrue(any('Comparability_Status' in f and f.Comparability_Status.eq('DESCRIPTIVE_ONLY').any() for f in frames))
        self.assertTrue(any('Reason' in f and f.Reason.astype(str).str.contains('POLICY_CONTRAST').any() for f in frames))

    def test_reference_change_clears_invalid_candidate_and_run_switch_resets_scope(self):
        app = self.select_pair(self.open_run(self.runs['synthetic_demo']))
        app.selectbox(key='wp2_reference').set_value('Combined_Stress').run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.selectbox(key='wp2_candidate').value)
        app.multiselect(key='wp2_priorities').set_value([3]).run()
        next(x for x in app.sidebar.text_input if x.label == 'Published sequential run folder').set_value(str(self.runs['user_data'])).run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.selectbox(key='wp2_reference').value)
        self.assertIsNone(app.selectbox(key='wp2_candidate').value)
        self.assertEqual(app.multiselect(key='wp2_priorities').value, [])

    def test_invalid_run_is_rejected_without_comparison(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/planning_source_runs') as temp:
            manifest = json.loads((self.runs['synthetic_demo']/'run_manifest.json').read_text())
            manifest['Publication_Status']='UNPUBLISHED'
            (Path(temp)/'run_manifest.json').write_text(json.dumps(manifest))
            app = self.open_run(temp)
            self.assertTrue(any('unpublished' in x.value for x in app.warning))
            self.assertNotIn('Download Comparison CSV',[x.label for x in app.get('download_button')])
