"""Negative UI presentation only; memory fixtures do not prove loader E2E."""
from pathlib import Path
import json
import os
import sys
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
ROOT=Path(os.environ['P1_EVIDENCE_ROOT']).resolve()


class NegativePresentationTests(unittest.TestCase):
    def app(self,variant):
        from streamlit.testing.v1 import AppTest
        script='''
from pathlib import Path
from unittest.mock import patch
import copy
from tests.test_phase1_coverage import memory_tableau
from src.scenario_comparison import ComparisonInput
from dashboard.scenario_planning_app import _scenario_tradeoff_analysis
variant = VARIANT
kwargs = {'zero': {'demand': 0.0}, 'inventory': {'inventory': 100.0, 'capacity': 0.0}, 'opening': {'opening_backlog': 2.0}}.get(variant,{})
a,b,scope=memory_tableau(**kwargs)
tables={k:v.copy(deep=True) for k,v in a.tables.items()}
candidate=tables['allocation'].Scenario.eq('CAND')
if variant=='priority':
    tables['allocation'].loc[candidate & tables['allocation']['Product Card Id'].eq('001'),'Planning_Priority']=1
    tables['allocation'].loc[candidate & tables['allocation']['Product Card Id'].eq('NA'),'Planning_Priority']=3
elif variant=='invalid_priority':
    tables['allocation'].loc[candidate,'Planning_Priority']=4
elif variant=='factor':
    tables['allocation'].loc[candidate,'Factor_Version']='INCOMPATIBLE'
elif variant=='endpoint':
    tables['allocation']=tables['allocation'].loc[~(candidate & tables['allocation'].Order_Date.eq('2026-01-11') & tables['allocation']['Product Card Id'].eq('NA'))].copy()
ref=ComparisonInput(a.manifest,tables,'REF')
with patch('src.comparison_io.load_comparison_input',return_value=ref):
    _scenario_tradeoff_analysis(Path('MEMORY_ONLY_NOT_LOADER_E2E'),a.manifest)
'''.replace('VARIANT',repr(variant))
        app=AppTest.from_string(script,default_timeout=30).run()
        app.selectbox(key='wp2_reference').set_value('REF').run()
        app.selectbox(key='wp2_candidate').set_value('CAND').run()
        app.multiselect(key='wp2_priorities').set_value([3]).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('download_button')),4)
        return app

    def metrics(self,app):
        return next(x.value for x in app.dataframe if {'Metric_ID','Reference_Numerator','Cohort_ID'}<=set(x.value))

    def metric(self,app,name):
        data=self.metrics(app)
        return data.loc[data.Cohort_ID.eq('ALL') & data.Metric_ID.eq(name)].iloc[0]

    def test_priority_change_fixed_membership_display(self):
        app=self.app('priority')
        members=next(x.value for x in app.dataframe if 'Cohort Membership' in x.value)
        self.assertEqual(set(members.loc[members['Cohort Membership'].eq('SELECTED'),'Product Card Id']),{'001'})
        self.assertTrue(members['Priority Changed'].all())

    def test_invalid_priority_has_unavailable_and_blocked_display(self):
        app=self.app('invalid_priority')
        members=next(x.value for x in app.dataframe if 'Cohort Membership' in x.value)
        self.assertEqual(set(members['Cohort Membership']),{'UNAVAILABLE'})
        row=self.metric(app,'Horizon_Service_Level')
        self.assertEqual(row.Comparability_Status,'BLOCKED');self.assertEqual(row.Delta,'N/A')

    def test_nonempty_zero_demand_display_is_na(self):
        row=self.metric(self.app('zero'),'Horizon_Service_Level')
        self.assertEqual(row.Reference_Value,'N/A');self.assertEqual(row.Delta,'N/A')

    def test_inventory_covered_display(self):
        app=self.app('inventory')
        self.assertEqual(float(self.metric(app,'Horizon_Service_Level').Reference_Value),1)
        self.assertEqual(float(self.metric(app,'Allocated_Workload').Reference_Value),0)

    def test_opening_origin_excluded_display(self):
        row=self.metric(self.app('opening'),'Horizon_Service_Level')
        self.assertEqual(float(row.Reference_Numerator),8)
        self.assertEqual(float(row.Reference_Value),.5)

    def test_factor_mismatch_has_metric_reason(self):
        row=self.metric(self.app('factor'),'Allocated_Workload')
        self.assertEqual(row.Comparability_Status,'BLOCKED');self.assertEqual(row.Delta,'N/A');self.assertTrue(row.Reason)

    def test_missing_endpoint_has_blocked_display(self):
        row=self.metric(self.app('endpoint'),'Horizon_Service_Level')
        self.assertEqual(row.Comparability_Status,'BLOCKED');self.assertEqual(row.Delta,'N/A');self.assertIn('coverage',row.Reason)


def main():
    records=[]
    class Recorder(unittest.TextTestResult):
        def addSuccess(self,t):super().addSuccess(t);records.append({'id':t.id(),'status':'PASS'})
        def addFailure(self,t,e):super().addFailure(t,e);records.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t)})
        def addError(self,t,e):super().addError(t,e);records.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t)})
    with patch('src.run_planning.run_csv_planning',side_effect=AssertionError('No planning')) as a,patch('src.run_planning.run_sequential_planning',side_effect=AssertionError('No planning')) as b:
        with (ROOT/'logs/negative_ui_layers.log').open('w') as log:r=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Recorder).run(unittest.defaultTestLoader.loadTestsFromTestCase(NegativePresentationTests))
        report={'run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'records':records,'runner_guard_calls':[a.call_count,b.call_count],
            'layer':'AppTest UI presentation, mocked loader, MEMORY_ONLY_NOT_LOADER_E2E; not real browser or Published Run E2E'}
    (ROOT/'reports/negative_ui_layers.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['run','failures','errors','runner_guard_calls']}))
    return 0 if r.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
