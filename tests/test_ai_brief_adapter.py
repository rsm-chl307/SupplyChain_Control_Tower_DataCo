import json
from dataclasses import replace
import unittest
from unittest.mock import patch
from src.synthetic_context import SyntheticHarness
from src.ai_brief.adapter import load_context, SourceBlocked, InvestigationSelection

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Network forbidden'));self.net.start();self.addCleanup(self.net.stop)
        self.h=SyntheticHarness();self.addCleanup(self.h.close);self.c=self.h.issue('Baseline')

    def test_valid_bundle_and_copied_frames(self):
        b=load_context(self.h,self.c);self.assertEqual(len(b.tables()),12)
        t=b.tables();t['allocation'].loc[0,'Run_ID']='fake'
        self.assertEqual(b.tables()['allocation'].Run_ID.iloc[0],self.c.run_id)
        self.assertIsNone(b.comparison_json)

    def test_no_selection_before_io(self):
        with patch.object(self.h,'snapshot',side_effect=AssertionError('No IO')):
            with self.assertRaises(SourceBlocked):load_context(self.h,None)

    def test_path_rejected_before_inspection(self):
        with patch.object(self.h,'_inspect',side_effect=AssertionError('No IO')):
            with self.assertRaises(SourceBlocked):load_context(self.h,'/tmp/other')

    def test_forged(self):
        with self.assertRaises(SourceBlocked):load_context(self.h,replace(self.c))

    def test_cross_harness(self):
        with SyntheticHarness() as other:
            with self.assertRaises(SourceBlocked):load_context(other,self.c)

    def test_modified_evidence(self):
        b=load_context(self.h,self.c)
        with (self.h._run_path/'allocation_result.csv').open('ab') as f:f.write(b'\n')
        with self.assertRaises(SourceBlocked):b.revalidate()

    def test_lifecycle_mode_missing_rows_and_hash(self):
        p=self.h._run_path/'run_manifest.json';original=p.read_bytes()
        for kind in ['unpublished','failed','user','missing','rows','hash']:
            m=json.loads(original)
            if kind=='unpublished':m['Publication_Status']='UNPUBLISHED'
            if kind=='failed':m['Execution_Status']='FAILED'
            if kind=='user':m['Data_Mode']='USER_DATA'
            if kind=='missing':del m['Artifacts']['weekly_demand']
            if kind=='rows':m['Artifacts']['allocation_result']['Rows']+=1
            if kind=='hash':m['Artifacts']['allocation_result']['SHA256']='0'*64
            p.write_text(json.dumps(m))
            with self.subTest(kind=kind),self.assertRaises(SourceBlocked):load_context(self.h,self.c)
            p.write_bytes(original)

    def test_symlink(self):
        p=self.h._run_path/'weekly_demand.csv';outside=self.h._run_path.parent/'outside.csv'
        outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside)
        with self.assertRaises(SourceBlocked):load_context(self.h,self.c)

    def test_no_runner_after_fixture_preparation(self):
        with patch('src.run_planning.run_csv_planning',side_effect=AssertionError('No planning')):
            load_context(self.h,self.c).revalidate()

    def test_invalid_investigation(self):
        with self.assertRaises(SourceBlocked):load_context(self.h,self.c,investigation=InvestigationSelection('bad','bad','2017-01-08'))

    def test_legitimate_empty_receipts_schema(self):
        from src.scenario_comparison import ComparisonInput,validate_comparison_input
        b=load_context(self.h,self.c);tables=b.tables();tables['external_receipts']=tables['external_receipts'].iloc[:0].copy()
        validate_comparison_input(ComparisonInput(b.manifest(),tables,b.scenario))
        self.assertEqual(len(tables['external_receipts']),0)

    def test_explicit_comparison_and_mismatch(self):
        from src.scenario_comparison import ComparisonInput,ComparisonScope,compare_published_results
        b=load_context(self.h,self.c);m=b.manifest();t=b.tables()
        scope=ComparisonScope(tuple(m['Scope']['Product_IDs']),tuple(t['initial_state'].Plant_ID.unique()),*m['Scope']['Planning_Horizon'])
        result=compare_published_results(ComparisonInput(m,t,'Baseline'),ComparisonInput(m,t,'Demand_Surge'),scope)
        self.assertIsNotNone(load_context(self.h,self.c,comparison=result).comparison_json)
        result.context['Candidate_Run_ID']='other'
        with self.assertRaises(SourceBlocked):load_context(self.h,self.c,comparison=result)

    def test_explicit_investigation(self):
        b=load_context(self.h,self.c);row=b.tables()['allocation'].iloc[0]
        selected=InvestigationSelection(row.Plant_ID,row['Product Card Id'],str(row.Order_Date.date()))
        self.assertEqual(load_context(self.h,self.c,investigation=selected).investigation,selected)

    def test_forged_bundle_rejected(self):
        from dataclasses import replace
        b=load_context(self.h,self.c)
        with self.assertRaises(SourceBlocked):replace(b).revalidate()

    def test_comparison_numbers_round_trip_without_pandas_rounding(self):
        import math
        from src.scenario_comparison import ComparisonInput,ComparisonScope,compare_published_results
        b=load_context(self.h,self.c);m=b.manifest();t=b.tables()
        scope=ComparisonScope(tuple(m['Scope']['Product_IDs']),tuple(t['initial_state'].Plant_ID.unique()),*m['Scope']['Planning_Horizon'])
        result=compare_published_results(ComparisonInput(m,t,'Baseline'),ComparisonInput(m,t,'Demand_Surge'),scope)
        rows=json.loads(load_context(self.h,self.c,comparison=result).comparison_json)['metrics']
        for idx,row in result.metrics.iterrows():
            for field in ['Reference_Value','Candidate_Value','Delta']:
                original=float(row[field]);copied=rows[idx][field]
                if math.isnan(original):self.assertIsNone(copied)
                else:self.assertEqual(original,copied)
