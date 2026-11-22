import unittest,json
from unittest.mock import patch
from src.synthetic_context import SyntheticHarness
from src.ai_brief.adapter import load_context,InvestigationSelection
from src.ai_brief.builder import build_draft,scalar
from src.ai_brief.contract import validate_structure,BriefRejected

class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=SyntheticHarness();cls.c=cls.h.issue('Baseline');cls.bundle=load_context(cls.h,cls.c)
    @classmethod
    def tearDownClass(cls):cls.h.close()
    def setUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Offline only'));self.net.start();self.addCleanup(self.net.stop)
    def test_draft_schema(self):
        b=build_draft(self.bundle).as_dict();validate_structure(b);self.assertEqual(b['brief_status'],'DRAFT')
    def test_kpis_exact(self):
        b=build_draft(self.bundle).as_dict();row=self.bundle.tables()['performance'].query("Scenario=='Baseline' and Aggregation_Level=='Scenario'").iloc[0]
        for section,key in [('capacity_analysis','Capacity_Utilization'),('service_analysis','Demand_Fulfillment_Rate'),('inventory_analysis','Ending_Inventory')]:
            self.assertEqual(b[section]['records'][0]['values'][key],row[key])
    def test_references_resolve_and_duplicate_checks_have_distinct_locators(self):
        b=build_draft(self.bundle,max_records=4).as_dict();refs={s['source_ref_id']:s for s in b['source_manifest']}
        for section in ['data_quality','risk_analysis','inventory_analysis']:
            for r in b[section]['records']:self.assertEqual(set(r['values']),set(refs[r['source_ref']]['field_names']))
        locs=[s['record_locator']['index'] for s in refs.values() if s['artifact_name']=='validation_result'];self.assertEqual(len(locs),len(set(locs)))
    def test_no_raw_privacy_data(self):
        raw=build_draft(self.bundle)._json.decode()
        for text in ['Product Name','Source_Hashes','Column_Mapping',str(self.h._run_path),self.c.run_id]:self.assertNotIn(text,raw)
    def test_optional_sections_unavailable(self):
        b=build_draft(self.bundle).as_dict()
        for s in ['root_cause_evidence','scenario_comparison']:
            self.assertEqual(b[s]['records'],[]);self.assertEqual(b[s]['availability'],'CONDITIONAL')
    def test_explicit_investigation(self):
        r=self.bundle.tables()['allocation'].iloc[0]
        b=build_draft(load_context(self.h,self.c,investigation=InvestigationSelection(r.Plant_ID,r['Product Card Id'],str(r.Order_Date.date())))).as_dict()
        self.assertTrue(b['root_cause_evidence']['records']);validate_structure(b)
    def test_truncation_disclosed(self):
        b=build_draft(self.bundle).as_dict();self.assertTrue(b['inventory_analysis']['selection']['truncated'])
    def test_no_planning(self):
        with patch('src.run_planning.run_csv_planning',side_effect=AssertionError('No planning')):build_draft(self.bundle)
    def test_nan_is_not_zero(self):
        self.assertIsNone(scalar(float('nan')))
        with self.assertRaises(BriefRejected):scalar(float('inf'))
    def test_bound_rejects(self):
        with self.assertRaises(BriefRejected):build_draft(self.bundle,max_records=0)

    def test_explicit_comparison_only(self):
        from src.scenario_comparison import ComparisonInput,ComparisonScope,compare_published_results
        m=self.bundle.manifest();t=self.bundle.tables()
        scope=ComparisonScope(tuple(m['Scope']['Product_IDs']),tuple(t['initial_state'].Plant_ID.unique()),*m['Scope']['Planning_Horizon'],(3,))
        result=compare_published_results(ComparisonInput(m,t,'Baseline'),ComparisonInput(m,t,'Demand_Surge'),scope)
        b=build_draft(load_context(self.h,self.c,comparison=result)).as_dict();validate_structure(b)
        self.assertEqual(b['run_context']['Comparison_ID'],'C-1');self.assertTrue(b['scenario_comparison']['records'])

    def test_empty_comparison_cohort_has_explicit_value_state(self):
        from src.scenario_comparison import ComparisonInput,ComparisonScope,compare_published_results
        m=self.bundle.manifest();t=self.bundle.tables()
        scope=ComparisonScope(tuple(m['Scope']['Product_IDs']),tuple(t['initial_state'].Plant_ID.unique()),*m['Scope']['Planning_Horizon'])
        result=compare_published_results(ComparisonInput(m,t,'Baseline'),ComparisonInput(m,t,'Demand_Surge'),scope)
        b=build_draft(load_context(self.h,self.c,comparison=result),max_records=3).as_dict()
        selected=next(r for r in b['scenario_comparison']['records'] if r['kind']=='comparison_metric' and r['values']['Cohort_ID']=='SELECTED')
        self.assertIsNone(selected['values']['Reference_Value'])
        self.assertEqual(selected['value_states']['Reference_Value'],'EMPTY_SELECTION')
