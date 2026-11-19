"""Phase 1 safe coverage: immutable existing Runs and memory-only hand tableaux.

No planning runner/publication is allowed. Memory fixtures deliberately exercise
the pure comparison contract; they are NOT hash-validated Published Run E2E.
"""
from __future__ import annotations

import copy
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(os.environ.get('PHASE1_EVIDENCE_ROOT', ROOT / 'tmp/phase_1_reliability/20261119T034337Z_f91753'))
RUNS = {
    'user_data': ROOT / 'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98',
    'synthetic_demo': ROOT / 'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324',
    'zero': ROOT / 'tmp/planning_source_runs/sequential_20261117T123838_5a317a36b54d',
    'reject': ROOT / 'tmp/planning_source_runs/sequential_20261117T124401_d4d42e5adb4f',
}


def no_planning(*args, **kwargs):
    raise AssertionError('Phase 1 forbids persisted planning runners')


def memory_tableau(demand=4.0, inventory=0.0, opening_backlog=0.0, capacity=5.0):
    """Two products/two weeks; explicit simple conservation, never a Run writer.

    This independent test-data construction uses basic arithmetic. Expected
    assertions below are hand-calculated constants, not comparison outputs.
    Manifest artifacts are labelled memory-only and never read/written as files.
    """
    from src.scenario_comparison import ARTIFACT_TABLES, ComparisonInput, ComparisonScope

    run_id = 'MEMORY_ONLY_HAND_TABLEAU_NOT_PUBLISHED_RUN'
    identity = {'Run_ID': run_id, 'Schema_Version': 'sequential_v1'}
    weeks = pd.to_datetime(['2026-01-04', '2026-01-11'])
    records, pools = [], []
    for scenario, available in [('REF', capacity), ('CAND', capacity * 2)]:
        stocks = {'001': inventory, 'NA': inventory}
        backlogs = {'001': 0.0, 'NA': opening_backlog}
        opening = dict(backlogs)
        for week in weeks:
            remaining = available
            weekly_records = []
            for order, (product, priority) in enumerate([('001', 3), ('NA', 1)], 1):
                beginning_inventory, beginning_backlog = stocks[product], backlogs[product]
                opening_before = opening[product]
                required = max(demand + beginning_backlog - beginning_inventory, 0.0)
                production = min(required, remaining)
                remaining -= production
                supply = beginning_inventory + production
                served_backlog = min(beginning_backlog, supply)
                served_opening = min(opening_before, served_backlog)
                served_current = min(demand, supply - served_backlog)
                stocks[product] = supply - served_backlog - served_current
                backlogs[product] = beginning_backlog - served_backlog + demand - served_current
                opening[product] = opening_before - served_opening
                row = {**identity, 'Scenario': scenario, 'Plant_ID': 'P', 'Product Card Id': product,
                    'Product Name': product, 'Order_Date': week, 'Planning_Priority': priority,
                    'Backlog_Policy': 'CARRY_FORWARD', 'Quantity_Unit': 'EA', 'Workload_Unit': 'WU',
                    'Workload_Factor': 1.0, 'Factor_Version': 'HAND_TEST', 'Allocation_Order': order,
                    'Allocation_Policy': 'PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT', 'Quantity_Step': 0.0,
                    'Gross_Demand': demand, 'Qualified_Demand': demand, 'Excluded_Demand': 0.0,
                    'Scenario_Qualified_Demand': demand, 'Incremental_Demand': 0.0,
                    'Coverage_Status': 'OBSERVED_ZERO' if demand == 0 else 'OBSERVED_DEMAND',
                    'Coverage_Basis': 'HAND_TEST_COMPLETE', 'Eligibility_Version': 'HAND_TEST',
                    'Beginning_Inventory': beginning_inventory, 'Beginning_Backlog': beginning_backlog,
                    'Beginning_Opening_Backlog': opening_before, 'External_Receipts_Qty': 0.0,
                    'Required_Production_Qty': required, 'Internal_Production_Qty': production,
                    'Allocated_Workload': production, 'Remaining_Workload_After_Row': remaining,
                    'Unmet_Production_Qty': required - production, 'Unmet_Workload': required - production,
                    'Fulfilled_Current_Qty': served_current, 'Fulfilled_Backlog_Qty': served_backlog,
                    'Fulfilled_Opening_Backlog_Qty': served_opening,
                    'Fulfilled_Horizon_Backlog_Qty': served_backlog - served_opening,
                    'Current_Unfulfilled_Qty': demand - served_current, 'Ending_Inventory': stocks[product],
                    'Ending_Backlog': backlogs[product], 'Ending_Opening_Backlog': opening[product],
                    'Ending_Horizon_Backlog': backlogs[product] - opening[product], 'Lost_Sales_Qty': 0.0}
                records.append(row); weekly_records.append(row)
            pools.append({**identity, 'Scenario': scenario, 'Plant_ID': 'P', 'Order_Date': week,
                'Baseline_Workload_Capacity': capacity * 2, 'Capacity_Version': 'HAND_TEST',
                'Factor_Version': 'HAND_TEST', 'Workload_Unit': 'WU',
                'Available_Workload_Capacity': available, 'Allocated_Workload': available - remaining,
                'Remaining_Workload_Capacity': remaining,
                'Unmet_Workload': sum(row['Unmet_Workload'] for row in weekly_records),
                'Workload_Shortage': any(row['Unmet_Workload'] > 1e-8 for row in weekly_records)})
    allocation = pd.DataFrame(records)
    native = allocation.loc[allocation.Scenario.eq('REF')].drop(columns=['Scenario']).copy()
    tables = {
        'allocation': allocation, 'scenario': allocation.copy(deep=True), 'pools': pd.DataFrame(pools),
        'performance': pd.DataFrame([{**identity, 'Scenario': s, 'Aggregation_Level': 'Scenario',
            'Plant_ID': None, 'Order_Date': pd.NaT} for s in ['REF', 'CAND']]),
        'initial_state': pd.DataFrame([{**identity, 'Plant_ID': 'P', 'Product Card Id': p,
            'Beginning_Inventory': inventory, 'Beginning_Backlog': opening_backlog if p == 'NA' else 0.0}
            for p in ['001', 'NA']]),
        'weekly_demand': native.copy(deep=True), 'demand_coverage': native.copy(deep=True),
        'workload_factors': pd.DataFrame([{**identity, 'Product Card Id': p, 'Workload_Factor': 1.0,
            'Workload_Unit': 'WU', 'Factor_Version': 'HAND_TEST'} for p in ['001', 'NA']]),
        'capacity_baseline': pd.DataFrame([{**identity, 'Plant_ID': 'P', 'Order_Date': week,
            'Baseline_Workload_Capacity': capacity * 2} for week in weeks]),
        'eligibility_ledger': pd.DataFrame(columns=list(identity)),
        'external_receipts': pd.DataFrame(columns=[*identity, 'Receipt_ID']),
        'validation_result': pd.DataFrame([{**identity, 'Check_ID': 'MEMORY_FIXTURE', 'Passed': True}]),
    }
    manifest = {**identity, 'Execution_Status': 'SUCCEEDED', 'Validation_Status': 'PASSED',
        'Publication_Status': 'PUBLISHED', 'Data_Mode': 'SYNTHETIC_DEMO',
        'Fixture_Kind': 'MEMORY_ONLY_NOT_LOADER_E2E', 'Source_Hashes': {},
        'Input_Validation': {'Sources': [], 'Assumptions': ['Hand tableau, no persisted Run']},
        'Configuration': {'scenarios': [{'Scenario': s, 'Backlog_Policy': 'CARRY_FORWARD'} for s in ['REF', 'CAND']]},
        'Scope': {'Planning_Horizon': ['2026-01-04', '2026-01-11'], 'Product_IDs': ['001', 'NA'], 'Quantity_Unit': 'EA'},
        'Artifacts': {artifact: {'Path': 'memory-only/' + artifact, 'SHA256': 'NOT_A_FILE', 'Rows': len(tables[name])}
            for artifact, name in ARTIFACT_TABLES.items()}}
    scope = ComparisonScope(('001', 'NA'), ('P',), '2026-01-04', '2026-01-11', (3,))
    return ComparisonInput(manifest, tables, 'REF'), ComparisonInput(manifest, tables, 'CAND'), scope


class Phase1CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guards = [patch('src.run_planning.' + name, side_effect=no_planning)
                      for name in ['run_csv_planning', 'run_sequential_planning']]
        for guard in cls.guards:guard.start();cls.addClassCleanup(guard.stop)
        from src.comparison_io import load_comparison_input
        cls.loaded = {mode: load_comparison_input(RUNS[mode], 'Baseline')
                      for mode in ['user_data', 'synthetic_demo', 'zero']}

    def inputs(self, mode='user_data'):
        from src.scenario_comparison import ComparisonInput, ComparisonScope
        a = self.loaded[mode]
        b = ComparisonInput(a.manifest, a.tables, 'Combined_Stress')
        scope = ComparisonScope(tuple(a.manifest['Scope']['Product_IDs']),
            tuple(sorted(a.tables['initial_state'].Plant_ID.unique())),
            *a.manifest['Scope']['Planning_Horizon'], (3,))
        return a, b, scope

    def compare(self, mode='user_data'):
        from src.scenario_comparison import compare_published_results
        return compare_published_results(*self.inputs(mode))

    def row(self, result, metric, group='ALL'):
        return result.metrics.loc[result.metrics.Metric_ID.eq(metric) & result.metrics.Cohort_ID.eq(group)].iloc[0]

    def changed(self, value, table, transform):
        from src.scenario_comparison import ComparisonInput
        tables = {k: v.copy(deep=True) for k, v in value.tables.items()}
        tables[table] = transform(tables[table])
        return ComparisonInput(copy.deepcopy(value.manifest), tables, value.scenario)

    def test_synthetic_existing_run_loader_and_exports(self):
        from src.comparison_io import comparison_csv_exports
        a, _, _ = self.inputs('synthetic_demo');result = self.compare('synthetic_demo')
        self.assertEqual(a.manifest['Data_Mode'], 'SYNTHETIC_DEMO')
        self.assertEqual(set(result.cohort_membership['Product Card Id']), {'1', '2'})
        exports = comparison_csv_exports(result)
        contexts = []
        for kind, content in exports.items():
            frame = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
            self.assertFalse(frame.empty, kind)
            self.assertEqual(set(frame.Reference_Run_ID), {a.run_id})
            self.assertEqual(set(frame.Candidate_Run_ID), {a.run_id})
            contexts.extend(frame.Comparison_Context.unique())
        self.assertEqual(len(set(contexts)), 1)
        self.assertEqual(exports, comparison_csv_exports(result))

    def test_zero_capacity_existing_pool_native_reconciliation(self):
        a, _, _ = self.inputs('zero');pools=a.tables['pools']
        zero=pools.loc[pools.Available_Workload_Capacity.eq(0)]
        self.assertEqual(len(zero), 4)
        self.assertEqual(set(zero.Plant_ID), {'SITE-1'})
        self.assertEqual(set(zero.Order_Date.dt.strftime('%Y-%m-%d')), {'2017-01-22'})
        self.assertTrue(zero.Allocated_Workload.eq(0).all())
        self.assertTrue(zero.Unmet_Workload.gt(0).all())
        result=self.compare('zero')
        context=pd.DataFrame(result.context['Plant_Capacity_Pool_Context'])
        self.assertFalse(context.duplicated(['Side','Plant_ID','Order_Date']).any())
        for row in zero.itertuples():
            detail=a.tables['allocation'].loc[lambda f:f.Scenario.eq(row.Scenario)&f.Plant_ID.eq(row.Plant_ID)&f.Order_Date.eq(row.Order_Date)]
            self.assertAlmostEqual(detail.Allocated_Workload.sum(), 0.0)
            self.assertAlmostEqual(detail.Unmet_Workload.sum(), row.Unmet_Workload)
        kpis=a.tables['performance'].loc[lambda f:f.Aggregation_Level.eq('Scenario × Plant × Week') & f.Plant_ID.eq('SITE-1') & f.Order_Date.eq(pd.Timestamp('2017-01-22'))]
        self.assertEqual(len(kpis), 4)
        self.assertTrue(kpis.Capacity_Utilization.isna().all())

    def test_unpublished_existing_run_is_rejected(self):
        from src.comparison_io import load_comparison_input
        with self.assertRaisesRegex(ValueError, 'unpublished'):
            load_comparison_input(RUNS['reject'], 'Baseline')

    def test_fixed_reference_priority_changes_both_directions(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=self.inputs()
        b=self.changed(b,'allocation',lambda f:f.assign(Planning_Priority=f['Product Card Id'].map({'SKU-A':1,'SKU-B':3,'SKU-C':2,'SKU-D':1})))
        result=compare_published_results(a,b,scope);members=result.cohort_membership.set_index('Product Card Id')
        self.assertEqual(set(members.index[members['Cohort Membership'].eq('SELECTED')]), {'SKU-A'})
        self.assertEqual(set(members.index[members['Cohort Membership'].eq('COMPLEMENT')]), {'SKU-B','SKU-C','SKU-D'})
        self.assertTrue(members.loc['SKU-A','Priority Changed'])
        self.assertTrue(members.loc['SKU-B','Priority Changed'])
        self.assertEqual(result.context['Priority_Changed_Product_Count'], 2)

    def test_missing_and_invalid_priorities_are_not_classified(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=self.inputs()
        for invalid in [float('nan'),0,4,1.5,'1']:
            with self.subTest(priority=str(invalid)):
                modified=self.changed(b,'allocation',lambda f:f.assign(Planning_Priority=invalid))
                result=compare_published_results(a,modified,scope)
                self.assertEqual(set(result.cohort_membership['Cohort Membership']), {'UNAVAILABLE'})
                self.assertTrue(result.metrics.Delta.isna().all())
                self.assertTrue(result.metrics.Reason.str.contains('Priority data issue').all())
        missing=self.changed(b,'allocation',lambda f:f.drop(columns=['Planning_Priority']))
        result=compare_published_results(a,missing,scope)
        self.assertEqual(set(result.cohort_membership['Cohort Membership']), {'UNAVAILABLE'})

    def test_incompatible_quantity_and_workload_definitions_are_metric_specific(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=self.inputs()
        result=compare_published_results(a,self.changed(b,'allocation',lambda f:f.assign(Quantity_Unit='KG')),scope)
        self.assertEqual(self.row(result,'Lost_Sales').Comparability_Status,'BLOCKED')
        self.assertEqual(self.row(result,'Allocated_Workload').Comparability_Status,'COMPARABLE')
        result=compare_published_results(a,self.changed(b,'allocation',lambda f:f.assign(Workload_Factor=f.Workload_Factor*2)),scope)
        for metric in ['Allocated_Workload','Unmet_Workload']:
            row=self.row(result,metric);self.assertEqual(row.Comparability_Status,'BLOCKED');self.assertTrue(pd.isna(row.Delta))
        self.assertEqual(self.row(result,'Horizon_Service_Level').Comparability_Status,'DESCRIPTIVE_ONLY')

    def test_missing_product_week_and_endpoint_do_not_shrink_scope(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=self.inputs()
        removals={'product':lambda f:f.loc[~f['Product Card Id'].eq('SKU-A')],
            'first_week':lambda f:f.loc[~f.Order_Date.eq(f.Order_Date.min())],
            'endpoint':lambda f:f.loc[~f.Order_Date.eq(f.Order_Date.max())]}
        for name,remove in removals.items():
            with self.subTest(defect=name):
                result=compare_published_results(a,self.changed(b,'allocation',remove),scope)
                self.assertTrue(result.metrics.Delta.isna().all())
                self.assertEqual(set(result.context['Scope']['product_ids']),set(scope.product_ids))
                self.assertTrue(result.metrics.Reason.str.contains('coverage').all())

    def test_hand_tableau_constrained_independent_constants(self):
        from src.scenario_comparison import compare_published_results
        result=compare_published_results(*memory_tableau())
        row=self.row(result,'Horizon_Service_Level')
        self.assertAlmostEqual(row.Reference_Value,10/16)
        self.assertEqual(row.Candidate_Value,1.0)
        self.assertEqual(row.Reference_Numerator,10.0)
        self.assertEqual(row.Reference_Denominator,16.0)
        self.assertEqual(self.row(result,'Terminal_Backlog').Reference_Value,6.0)
        self.assertEqual(self.row(result,'Current_Unfulfilled_Quantity').Reference_Value,7.0)
        self.assertEqual(self.row(result,'Allocated_Workload').Delta,6.0)

    def test_true_zero_demand_nonempty_cohort_is_na(self):
        from src.scenario_comparison import compare_published_results
        result=compare_published_results(*memory_tableau(demand=0.0))
        self.assertEqual(len(result.cohort_membership),2)
        for group in ['ALL','SELECTED','COMPLEMENT']:
            row=self.row(result,'Horizon_Service_Level',group)
            self.assertEqual(row.Reference_Denominator,0.0)
            self.assertTrue(pd.isna(row.Reference_Value));self.assertTrue(pd.isna(row.Delta))
            self.assertEqual(row.Comparability_Status,'BLOCKED')
            self.assertIn('Zero denominator',row.Reason)

    def test_inventory_fully_covers_positive_demand(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=memory_tableau(inventory=100.0,capacity=0.0)
        result=compare_published_results(a,b,scope)
        self.assertEqual(self.row(result,'Horizon_Service_Level').Reference_Value,1.0)
        for metric in ['Allocated_Workload','Unmet_Workload','Terminal_Backlog']:
            self.assertEqual(self.row(result,metric).Reference_Value,0.0)
        self.assertEqual(self.row(result,'Horizon_Service_Level').Reference_Denominator,16.0)
        self.assertTrue(a.tables['allocation'].Internal_Production_Qty.eq(0).all())
        self.assertTrue(a.tables['allocation'].Required_Production_Qty.eq(0).all())

    def test_opening_origin_is_excluded_from_horizon_service(self):
        from src.scenario_comparison import compare_published_results
        a,b,scope=memory_tableau(opening_backlog=2.0)
        result=compare_published_results(a,b,scope);row=self.row(result,'Horizon_Service_Level')
        self.assertEqual(row.Reference_Numerator,8.0)
        self.assertEqual(row.Reference_Denominator,16.0)
        self.assertEqual(row.Reference_Value,0.5)
        self.assertEqual(self.row(result,'Terminal_Opening_Backlog').Reference_Value,0.0)
        self.assertEqual(self.row(result,'Terminal_Horizon_Backlog').Reference_Value,8.0)
        source=a.tables['allocation'].loc[lambda f:f.Scenario.eq('REF')]
        self.assertEqual(source.Fulfilled_Opening_Backlog_Qty.sum(),2.0)
        self.assertEqual(source.Fulfilled_Current_Qty.sum()+source.Fulfilled_Backlog_Qty.sum(),10.0)

    def test_tableau_conservation_and_string_id_exports(self):
        from src.scenario_comparison import compare_published_results
        from src.comparison_io import comparison_csv_exports
        for kwargs in [{},{'demand':0.0},{'inventory':100.0,'capacity':0.0},{'opening_backlog':2.0}]:
            with self.subTest(case=kwargs):
                a,b,scope=memory_tableau(**kwargs);f=a.tables['allocation']
                self.assertTrue((f.Beginning_Inventory+f.Internal_Production_Qty-f.Fulfilled_Current_Qty-f.Fulfilled_Backlog_Qty-f.Ending_Inventory).abs().lt(1e-12).all())
                self.assertTrue((f.Beginning_Backlog+f.Scenario_Qualified_Demand-f.Fulfilled_Current_Qty-f.Fulfilled_Backlog_Qty-f.Ending_Backlog).abs().lt(1e-12).all())
                exports=comparison_csv_exports(compare_published_results(a,b,scope))
                members=pd.read_csv(io.StringIO(exports['cohort_membership']),dtype=str,keep_default_na=False)
                self.assertEqual(set(members['Product Card Id']),{'001','NA'})

    def test_primary_all_metrics_native_decimal_oracle(self):
        result=self.compare();a,b,_=self.inputs()
        for scenario,prefix in [('Baseline','Reference'),('Combined_Stress','Candidate')]:
            f=a.tables['allocation'].loc[lambda f:f.Scenario.eq(scenario)]
            s=lambda column:sum((Decimal(str(x)) for x in f[column]),Decimal(0))
            numerator=s('Fulfilled_Current_Qty')+s('Fulfilled_Backlog_Qty')-s('Fulfilled_Opening_Backlog_Qty')
            denominator=s('Scenario_Qualified_Demand')
            self.assertAlmostEqual(float(numerator/denominator),self.row(result,'Horizon_Service_Level')[prefix+'_Value'])
            terminal=f.loc[f.Order_Date.eq(pd.Timestamp(a.manifest['Scope']['Planning_Horizon'][1]))]
            self.assertAlmostEqual(float(sum((Decimal(str(x)) for x in terminal.Ending_Backlog),Decimal(0))),self.row(result,'Terminal_Backlog')[prefix+'_Value'])
            allocated=sum((Decimal(str(r.Internal_Production_Qty))*Decimal(str(r.Workload_Factor)) for r in f.itertuples()),Decimal(0))
            unmet=sum(((Decimal(str(r.Required_Production_Qty))-Decimal(str(r.Internal_Production_Qty)))*Decimal(str(r.Workload_Factor)) for r in f.itertuples()),Decimal(0))
            self.assertAlmostEqual(float(allocated),self.row(result,'Allocated_Workload')[prefix+'_Value'])
            self.assertAlmostEqual(float(unmet),self.row(result,'Unmet_Workload')[prefix+'_Value'])
            self.assertAlmostEqual(float(s('Lost_Sales_Qty')),self.row(result,'Lost_Sales')[prefix+'_Value'])


def main():
    """Dedicated executable writes results only in this execution's evidence root."""
    os.environ['TMPDIR']=str(EVIDENCE/'temp')
    records=[]
    class Recorder(unittest.TextTestResult):
        def addSuccess(self,test):super().addSuccess(test);records.append({'test':test.id(),'status':'PASS'})
        def addFailure(self,test,err):super().addFailure(test,err);records.append({'test':test.id(),'status':'FAIL','details':self._exc_info_to_string(err,test)})
        def addError(self,test,err):super().addError(test,err);records.append({'test':test.id(),'status':'FAIL','details':self._exc_info_to_string(err,test)})
    with (EVIDENCE/'logs/ws1_coverage.log').open('w') as log:
        outcome=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Recorder).run(unittest.defaultTestLoader.loadTestsFromTestCase(Phase1CoverageTests))
    case_tests={
        'NC-SYNTHETIC':['test_synthetic_existing_run_loader_and_exports'],
        'NC-N03':['test_zero_capacity_existing_pool_native_reconciliation'],
        'NC-N08':['test_unpublished_existing_run_is_rejected'],
        'NC-B09':['test_fixed_reference_priority_changes_both_directions'],
        'NC-N01':['test_missing_and_invalid_priorities_are_not_classified'],
        'NC-N06':['test_incompatible_quantity_and_workload_definitions_are_metric_specific'],
        'NC-N07':['test_missing_product_week_and_endpoint_do_not_shrink_scope'],
        'NC-N02':['test_true_zero_demand_nonempty_cohort_is_na'],
        'NC-N04':['test_inventory_fully_covers_positive_demand'],
        'NC-N05':['test_opening_origin_is_excluded_from_horizon_service'],
    }
    cases={}
    for id,names in case_tests.items():
        matching=[r for r in records if any(r['test'].endswith('.'+n) for n in names)]
        passed=len(matching)==len(names) and all(r['status']=='PASS' for r in matching)
        existing=id in ['NC-SYNTHETIC','NC-N03','NC-N08']
        cases[id]={'status':'PARTIAL' if passed else 'FAIL','executed_layer_status':'PASS' if passed else 'FAIL',
            'executed_layers':['Python','production loader of immutable existing Run'] if existing else ['Python pure comparison','memory-only fixture'],
            'tests':names,'browser':'NOT COVERED by WS1; Main records real browser separately',
            'published_run_e2e':'Pending Main browser' if existing else 'NOT COVERED: no compatible immutable published fixture',
            'new_run_created':False}
    report={'tests_run':outcome.testsRun,'passed':sum(r['status']=='PASS' for r in records),'failures':len(outcome.failures),
        'errors':len(outcome.errors),'skipped':len(outcome.skipped),'records':records,'cases':cases,
        'fixture_notes':'memory_tableau is a labelled in-memory pure-contract fixture, never a Published Run or loader E2E; no production planner/runner used',
        'original_suites_rerun':False,'planning_runner_called':False,'evidence_root':str(EVIDENCE)}
    (EVIDENCE/'reports/coverage_results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['tests_run','passed','failures','errors','skipped']},indent=2))
    return 0 if outcome.wasSuccessful() else 1


if __name__=='__main__':
    sys.path.insert(0,str(ROOT))
    raise SystemExit(main())
