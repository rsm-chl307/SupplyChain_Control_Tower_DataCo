"""Bounded shared-module regression using only approved synthetic data."""
import json,unittest
from pathlib import Path
import pandas as pd
from src.synthetic_context import SyntheticHarness
from src.ai_brief.adapter import load_context
from src.csv_planning_inputs import load_csv_planning_inputs
from src.kpi_engine import calculate_sequential_kpis
from src.planning_risk import product_risk_ranking
from src.ai_brief.workflow import prepare_brief

class SyntheticRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.h=SyntheticHarness();cls.c=cls.h.issue('Baseline');cls.bundle=load_context(cls.h,cls.c)
    @classmethod
    def tearDownClass(cls):cls.h.close()
    def test_csv_readiness_and_coverage(self):
        fixture=Path(__file__).resolve().parents[1]/'examples/planning/synthetic_demo'
        config=json.loads((fixture/'config.json').read_text());self.assertEqual(config['data_mode'],'SYNTHETIC_DEMO')
        source=load_csv_planning_inputs(config,fixture)
        self.assertEqual(source.report['Status'],'READY')
        self.assertTrue(source.demand.Coverage_Status.isin(['OBSERVED_ZERO','OBSERVED_DEMAND']).all())
    def test_published_kpi_engine_preserved(self):
        t=self.bundle.tables();expected=calculate_sequential_kpis(t['allocation'],t['pools'])
        actual=t['performance'][expected.columns]
        # CSV represents non-applicable aggregation identifiers as empty cells.
        # Normalize only these keys; compare every authoritative KPI unchanged.
        for key in ('Plant_ID','Product_ID'):
            if key in expected:
                expected[key]=expected[key].fillna('')
                actual=actual.copy()
                actual[key]=actual[key].fillna('')
        pd.testing.assert_frame_equal(expected,actual,check_dtype=False,rtol=1e-12,atol=1e-12)
    def test_risk_categories_remain_deterministic(self):
        t=self.bundle.tables();risk=product_risk_ranking(t['allocation'].loc[t['allocation'].Scenario.eq('Baseline')])
        self.assertTrue(risk.Risk_Category.isin(['At Risk','Watch','Healthy']).all())
        result=prepare_brief(self.h,self.c);self.assertEqual(result.status,'VALIDATED')
        row=json.loads(result.review.canonical_json)['risk_analysis']['records'][0]
        self.assertEqual(row['values']['Risk_Category'],risk.Risk_Category.iloc[0])
    def test_native_grains_not_multiplied(self):
        t=self.bundle.tables();p=t['pools']
        self.assertFalse(p.duplicated(['Scenario','Plant_ID','Order_Date']).any())
        b=json.loads(prepare_brief(self.h,self.c).review.canonical_json)
        self.assertEqual(b['capacity_analysis']['records'][1]['values']['Available_Workload_Capacity'],p.loc[p.Scenario.eq('Baseline')].iloc[0].Available_Workload_Capacity)
