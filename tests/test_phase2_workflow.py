"""Guarded existing-Run UI integration using disposable synthetic Runs."""
from pathlib import Path
from datetime import date
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'dashboard/scenario_planning_app.py'


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Publish disposable Run inputs from tracked fixtures for UI-only tests."""
        from src.run_planning import run_csv_planning
        fixtures = (
            (ROOT/'examples/planning/user_data', ROOT/'tmp/user_data_acceptance_2026-11-17/runs'),
            (ROOT/'examples/planning/synthetic_demo', ROOT/'tmp/planning_source_runs'),
        )
        runs = []
        for source, output_root in fixtures:
            output_root.mkdir(parents=True, exist_ok=True)
            temporary = tempfile.TemporaryDirectory(dir=output_root)
            cls.addClassCleanup(temporary.cleanup)
            config = json.loads((source/'config.json').read_text())
            outputs = run_csv_planning(config, inputs_dir=source, output_root=temporary.name)
            runs.append(outputs['run_manifest'].parent)
        cls.primary, cls.synthetic = runs

    def setUp(self):
        self.guards=[]
        for name in ['run_csv_planning','run_sequential_planning','run_planning']:
            p=patch('src.run_planning.'+name,side_effect=AssertionError('Phase 2 must not execute planning'))
            self.guards.append(p.start());self.addCleanup(p.stop)
        from streamlit.testing.v1 import AppTest
        self.app=AppTest.from_file(str(APP),default_timeout=60).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.assertTrue(all(g.call_count==0 for g in self.guards))

    def load(self, path=None):
        path = self.primary if path is None else path
        self.app.text_input(key='ui_published_run_path').set_value(str(path)).run()
        self.assertFalse(self.app.exception)

    def pair(self):
        self.load()
        self.app.selectbox(key='wp2_reference').set_value('Baseline').run()
        self.app.selectbox(key='wp2_candidate').set_value('Combined_Stress').run()
        self.app.multiselect(key='wp2_priorities').set_value([3]).run()
        self.assertFalse(self.app.exception)

    def form_locale(self,locale):
        self.app.selectbox(key='ui_language_request').set_value(locale).run()
        self.assertFalse(self.app.exception)

    def test_default_empty_and_guidance(self):
        self.assertTrue(any('Analyze saved results' in c.value for c in self.app.markdown))
        self.load()
        self.assertIsNone(self.app.selectbox(key='wp2_reference').value)
        self.assertIsNone(self.app.selectbox(key='wp2_candidate').value)

    def test_pair_and_language_round_trip_keep_state_and_canonical_tables(self):
        self.pair()
        before=next(d.value for d in self.app.dataframe if 'Reference_Value' in d.value).copy()
        self.form_locale('zh-TW')
        self.assertEqual(self.app.selectbox(key='wp2_candidate').value,'Combined_Stress')
        self.assertEqual(self.app.multiselect(key='wp2_priorities').value,[3])
        self.assertTrue(any('情境取捨分析' in t.label for t in self.app.get('tab')))
        import pandas as pd
        pd.testing.assert_frame_equal(before,next(d.value for d in self.app.dataframe if 'Reference_Value' in d.value))
        self.form_locale('en')
        self.assertEqual(self.app.selectbox(key='wp2_reference').value,'Baseline')

    def test_invalid_candidate_clears_and_valid_candidate_retained(self):
        self.pair()
        self.app.selectbox(key='wp2_reference').set_value('Demand_Surge').run()
        self.assertEqual(self.app.selectbox(key='wp2_candidate').value,'Combined_Stress')
        self.app.selectbox(key='wp2_reference').set_value('Combined_Stress').run()
        self.assertIsNone(self.app.selectbox(key='wp2_candidate').value)
        self.assertTrue(self.app.selectbox(key='wp2_candidate').proto.set_value)

    def test_run_round_trip_clears_pair(self):
        self.pair()
        for path in [self.synthetic,self.primary]:
            self.load(path)
            self.assertIsNone(self.app.selectbox(key='wp2_reference').value)
            self.assertIsNone(self.app.selectbox(key='wp2_candidate').value)
            self.assertEqual(self.app.multiselect(key='wp2_priorities').value,[])

    def test_global_language_change_preserves_pending_settings_without_planning(self):
        self.app.number_input(key='upload_surge_pct').set_value(17.0)
        self.app.number_input(key='upload_disruption_pct').set_value(31.0)
        self.app.selectbox(key='upload_interpretation').set_value('RETROSPECTIVE')
        self.app.text_input(key='upload_quantity_unit').set_value('case')
        self.app.checkbox(key='upload_zero_inventory').check()
        self.form_locale('zh-TW')
        self.assertEqual(self.app.number_input(key='upload_surge_pct').value,17.0)
        self.assertEqual(self.app.number_input(key='upload_disruption_pct').value,31.0)
        self.assertEqual(self.app.selectbox(key='upload_interpretation').value,'RETROSPECTIVE')
        self.assertEqual(self.app.text_input(key='upload_quantity_unit').value,'case')
        self.assertTrue(self.app.checkbox(key='upload_zero_inventory').value)
        self.assertEqual(self.app.selectbox(key='ui_planning_model').value,'Sequential workload')
        self.assertFalse(any(s.key == 'upload_language_request' for s in self.app.selectbox))
        self.assertFalse(any('Apply language and keep form inputs' in str(b.label) for b in self.app.button))
        self.assertFalse(any('Data readiness:' in str(x.value) for x in self.app.success))

    def test_global_language_round_trip_and_model_labels_keep_machine_values(self):
        from dashboard.scenario_planning_app import _planning_model_label, _planning_model_help
        from dashboard.i18n import t
        selector = self.app.selectbox(key='ui_language_request')
        self.assertEqual(selector.value, 'en')
        self.form_locale('zh-TW')
        self.assertEqual(self.app.session_state['ui_locale'], 'zh-TW')
        self.assertTrue(any('情境規劃決策支援' in str(title.value) for title in self.app.title))
        self.assertEqual(_planning_model_label('Sequential workload', 'zh-TW'), '連續週次規劃')
        self.assertEqual(_planning_model_label('Legacy independent weeks', 'zh-TW'), '單週獨立分析')
        self.assertIn('carrying ending inventory and unfulfilled orders', _planning_model_help('Sequential workload'))
        self.assertIn('each week separately', _planning_model_help('Legacy independent weeks'))
        self.assertEqual(t('model.sequential.label', locale='en'), 'Sequential weekly planning')
        self.assertEqual(self.app.selectbox(key='ui_planning_model').value, 'Sequential workload')
        self.form_locale('en')
        self.assertEqual(self.app.session_state['ui_locale'], 'en')
        self.assertTrue(any('Scenario Planning Decision Support' in str(title.value) for title in self.app.title))

    def test_wp1_side_handoff_retains_comparison(self):
        self.pair()
        self.app.selectbox(key='wp2_product').set_value('SKU-A').run()
        self.app.button(key='wp2_investigate_candidate').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.selectbox(key='sequential_scenario').value,'Combined_Stress')
        self.assertEqual(self.app.selectbox(key='investigation_product').value,'SKU-A')
        self.assertEqual(self.app.selectbox(key='wp2_reference').value,'Baseline')

    def test_unknown_run_rejected_without_stale_exports(self):
        self.pair()
        self.load(ROOT/'NO_SUCH_RUN_DO_NOT_CREATE')
        self.assertFalse(any(b.label=='Download Comparison CSV' for b in self.app.get('download_button')))

    def test_sidebar_locale_retains_manual_run_and_pair(self):
        self.app.radio(key='ui_planning_input_method').set_value('Use existing JSON configuration').run()
        config_path='examples/planning/synthetic_demo/config.json'
        self.app.text_input(key='ui_sequential_config_path').set_value(config_path).run()
        self.pair()
        self.form_locale('zh-TW')
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input(key='ui_published_run_path').value,str(self.primary))
        self.assertEqual(self.app.text_input(key='ui_sequential_config_path').value,config_path)
        self.assertEqual(self.app.selectbox(key='wp2_candidate').value,'Combined_Stress')

    def test_retained_existing_upload_mapping_survives_language_and_model_round_trip(self):
        folder=ROOT/'examples/planning/user_data'
        self.app.session_state['_user_csv_upload_data']={'products':('products.csv',(folder/'products.csv').read_bytes())}
        self.app.run()
        mapping='map_products_Product_ID_products.csv'
        self.assertEqual(self.app.selectbox(key=mapping).value,'sku')
        horizon_key=next(w.key for w in self.app.date_input if w.key.startswith('upload_start_week_'))
        self.app.date_input(key=horizon_key).set_value(date(2026, 12, 6))
        self.app.number_input(key='upload_surge_pct').set_value(19.0)
        self.form_locale('zh-TW')
        self.assertEqual(self.app.selectbox(key=mapping).value,'sku')
        self.assertEqual(self.app.date_input(key=horizon_key).value,date(2026, 12, 6))
        optional_mapping = self.app.selectbox(key='map_products_Quantity_Unit_products.csv')
        self.assertIn('— 未提供 —', optional_mapping.options)
        self.assertEqual(optional_mapping.value, 'uom')
        optional_mapping.set_value('— not provided —').run()
        self.assertEqual(self.app.selectbox(key='map_products_Quantity_Unit_products.csv').value,
                         '— not provided —')
        optional_mapping = self.app.selectbox(key='map_products_Quantity_Unit_products.csv')
        optional_mapping.set_value('uom').run()
        self.app.selectbox(key='ui_planning_model').set_value('Legacy independent weeks').run()
        self.app.selectbox(key='ui_planning_model').set_value('Sequential workload').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.selectbox(key=mapping).value,'sku')
        self.assertEqual(self.app.number_input(key='upload_surge_pct').value,19.0)
        self.assertEqual(self.app.session_state['_user_csv_upload_data']['products'][1],(folder/'products.csv').read_bytes())
