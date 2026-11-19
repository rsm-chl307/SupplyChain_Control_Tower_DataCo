"""Independent hand-calculated WP2 cases with explicit non-Baseline comparison sides."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.comparison_io import comparison_csv_exports, load_comparison_input
from src.run_planning import run_csv_planning
from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results


class ComparisonAcceptanceTests(unittest.TestCase):
    def fixture(self, capacity=5., demand=4., inventory=0., opening_backlog=0., policy='CARRY_FORWARD'):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        frames = {
            'products': pd.DataFrame({'Product_ID':['001','NA'], 'Product_Name':['Widget','Widget'],
                                      'Quantity_Unit':['EA','EA'], 'Planning_Priority':[3,1]}),
            'plants': pd.DataFrame({'Plant_ID':['P'], 'Plant_Name':['Plant']}),
            'product_plant_mapping': pd.DataFrame({'Product_ID':['001','NA'], 'Plant_ID':['P','P']}),
            'demand': pd.DataFrame([{'Order_Line_ID':str(i), 'Product_ID':p, 'Status':'RELEASED',
                                     'Date':w, 'Quantity':demand}
                                    for i,(w,p) in enumerate((w,p) for w in ['2025-12-29','2026-01-11'] for p in ['001','NA'])]),
            'workload_factors': pd.DataFrame({'Product_ID':['001','NA'], 'Workload_Factor':[1.,1.],
                                              'Factor_Version':['test','test'], 'Workload_Unit':['WU','WU'],
                                              'Provenance_Type':['SYNTHETIC_TEST']*2}),
            'initial_inventory': pd.DataFrame({'Plant_ID':['P','P'], 'Product_ID':['001','NA'],
                                                'Beginning_Inventory':[inventory,inventory],
                                                'Beginning_Backlog':[0.,opening_backlog],
                                                'Initial_State_Version':['test']*2, 'Provenance_Type':['SYNTHETIC_TEST']*2}),
            'weekly_capacity': pd.DataFrame({'Plant_ID':['P','P'], 'Week':['2026-01-04','2026-01-11'],
                                             'Capacity':[capacity*2]*2, 'Workload_Unit':['WU']*2,
                                             'Factor_Version':['test']*2, 'Capacity_Version':['test']*2}),
        }
        for name, frame in frames.items():
            frame.to_csv(folder/f'{name}.csv', index=False)
        config = {'data_mode':'SYNTHETIC_DEMO', 'assumption_version':'acceptance-v1',
                  'planning_interpretation':'RETROSPECTIVE', 'demand_format':'ORDER_LINES',
                  'source_is_complete':True, 'eligibility_version':'test', 'status_eligibility':{'RELEASED':True},
                  'planning_start_week':'2026-01-04', 'planning_end_week':'2026-01-11',
                  'quantity_step':0., 'allocation_policy':'PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT',
                  'files':{name:{'path':f'{name}.csv'} for name in frames},
                  'scenarios':[{'Scenario':name, 'Demand_Multiplier':1., 'Capacity_Multiplier':multiplier,
                                'Disruption_Plants':['P'], 'Disruption_Weeks':None, 'Backlog_Policy':policy}
                               for name,multiplier in [('Baseline',1.),('REF',.5),('CAND',1.)]]}
        # Header-only receipts are valid published evidence of no scheduled supply.
        pd.DataFrame(columns=['Receipt_ID','Plant_ID','Product_ID','Week','External_Receipts_Qty']).to_csv(folder/'external_receipts.csv',index=False)
        config['files']['external_receipts']={'path':'external_receipts.csv'}
        paths = run_csv_planning(config, inputs_dir=folder, output_root=folder/'runs')
        a = load_comparison_input(paths['run_manifest'].parent, 'REF')
        b = ComparisonInput(a.manifest, a.tables, 'CAND')
        scope = ComparisonScope(('001','NA'),('P',),'2026-01-04','2026-01-11',(3,))
        return compare_published_results(a,b,scope), a, b, scope

    def row(self, result, metric, group='ALL'):
        return result.metrics.loc[result.metrics.Metric_ID.eq(metric)&result.metrics.Cohort_ID.eq(group)].iloc[0]

    def test_constrained_manual_oracle_service_and_backlog_tradeoffs(self):
        r,_,_,_ = self.fixture()
        service = self.row(r,'Horizon_Service_Level')
        self.assertAlmostEqual(service.Reference_Value,10/16)
        self.assertAlmostEqual(service.Candidate_Value,1.)
        self.assertAlmostEqual(service.Delta,37.5)
        self.assertEqual(service.Reference_Numerator,10)
        self.assertEqual(service.Reference_Denominator,16)
        self.assertEqual(self.row(r,'Terminal_Backlog').Reference_Value,6)
        self.assertEqual(self.row(r,'Terminal_Backlog').Delta,-6)
        self.assertEqual(self.row(r,'Current_Unfulfilled_Quantity').Reference_Value,7)
        self.assertEqual(self.row(r,'Allocated_Workload').Delta,6)
        self.assertEqual(self.row(r,'Unmet_Workload').Reference_Value,9)
        self.assertEqual(self.row(r,'Horizon_Service_Level','SELECTED').Reference_Value,1.)
        self.assertEqual(self.row(r,'Horizon_Service_Level','COMPLEMENT').Reference_Value,.25)
        weekly=r.metrics.loc[r.metrics.Cohort_ID.eq('ALL')&r.metrics.Metric_ID.eq('Weekly_Service_Level')].sort_values('Order_Date')
        self.assertEqual(weekly.Reference_Value.tolist(),[5/8,4/8])
        self.assertEqual(sum(x['Available_Workload_Capacity'] for x in r.context['Plant_Capacity_Pool_Context'] if x['Side']=='REFERENCE'),10)
        self.assertEqual(set(r.cohort_membership['Product Card Id']),{'001','NA'})

    def test_zero_capacity_is_zero_service_with_full_terminal_backlog(self):
        r,_,_,_=self.fixture(capacity=0.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Reference_Value,0.)
        self.assertEqual(self.row(r,'Terminal_Backlog').Reference_Value,16.)
        self.assertEqual(self.row(r,'Allocated_Workload').Reference_Value,0.)

    def test_zero_demand_is_na_not_perfect_service(self):
        r,_,_,_=self.fixture(demand=0.)
        self.assertTrue(pd.isna(self.row(r,'Horizon_Service_Level').Reference_Value))
        self.assertTrue(pd.isna(self.row(r,'Horizon_Service_Level').Delta))
        self.assertEqual(self.row(r,'Terminal_Backlog').Reference_Value,0.)

    def test_inventory_covered_demand_needs_no_production_workload(self):
        r,_,_,_=self.fixture(capacity=0.,inventory=100.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Reference_Value,1.)
        self.assertEqual(self.row(r,'Allocated_Workload').Reference_Value,0.)
        self.assertEqual(self.row(r,'Unmet_Workload').Reference_Value,0.)
        self.assertEqual(self.row(r,'Terminal_Backlog').Reference_Value,0.)

    def test_unconstrained_capacity_no_service_or_backlog_change(self):
        r,_,_,_=self.fixture(capacity=20.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Reference_Value,1.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Delta,0.)
        self.assertEqual(self.row(r,'Terminal_Backlog').Delta,0.)

    def test_opening_origin_fulfillment_is_excluded_from_horizon_service(self):
        r,_,_,_=self.fixture(opening_backlog=2.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Reference_Numerator,8.)
        self.assertEqual(self.row(r,'Horizon_Service_Level').Reference_Value,.5)
        self.assertEqual(self.row(r,'Terminal_Opening_Backlog').Reference_Value,0.)
        self.assertEqual(self.row(r,'Terminal_Horizon_Backlog').Reference_Value,8.)

    def test_export_contains_native_evidence_and_unambiguous_string_ids(self):
        import io
        r,_,_,_=self.fixture()
        exports=comparison_csv_exports(r)
        members=pd.read_csv(io.StringIO(exports['cohort_membership']),dtype=str,keep_default_na=False)
        self.assertEqual(set(members['Product Card Id']),{'001','NA'})
        data=pd.read_csv(io.StringIO(exports['metrics']),keep_default_na=False)
        self.assertEqual(set(data.Reference_Scenario),{'REF'})
        self.assertEqual(set(data.Candidate_Scenario),{'CAND'})
        self.assertEqual(len(json.loads(data.Evidence_References.iloc[0])),24)
