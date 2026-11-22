import copy,json,unittest
from src.ai_brief.contract import *

def minimal():
    run={k: 'x' for k in RUN_FIELDS}
    run.update(Run_ID='R-1',Schema_Version='sequential_v1',Execution_Status='SUCCEEDED',Validation_Status='PASSED',Publication_Status='PUBLISHED',Scenario='Baseline',Started_At='2026-01-01T00:00:00Z',Finished_At='2026-01-01T00:00:01Z',Comparison_ID=None,source_ref='s1')
    scope={'Planning_Horizon':['2017-01-08','2017-01-22'],'Product_IDs':['P-1'],'Plant_IDs':['P-2'],'Selected_Products':1,'Quantity_Unit':'units','Demand_Basis':'RETROSPECTIVE','Data_Mode':'SYNTHETIC_DEMO','source_ref':'s2'}
    return {'brief_version':VERSION,'brief_status':'DRAFT','schema_version':'ai_brief_1.0','definition_version':DEFINITIONS,'privacy_policy_version':PRIVACY,'run_context':run,'data_scope':scope,'source_manifest':[],**{s:{'availability':'CONDITIONAL','reason':'No optional selection','selection':{'Run_ID':'R-1','Scenario':'Baseline','total_rows':0,'returned_rows':0,'truncated':False},'records':[],'source_refs':[]} for s in SECTIONS}}

class ContractTests(unittest.TestCase):
    def test_closed_schema_valid(self):validate_structure(minimal());Draft202012Validator.check_schema(SCHEMA)
    def test_unknown_top_and_nested(self):
        for target in ['top','run','scope']:
            b=minimal();d=b if target=='top' else b['run_context' if target=='run' else 'data_scope'];d['unknown']=1
            with self.assertRaises(BriefRejected):validate_structure(b)
    def test_wrong_types_and_enums(self):
        for key,value in [('brief_version',1),('brief_status','READY'),('definition_version','future')]:
            b=minimal();b[key]=value
            with self.assertRaises(BriefRejected):validate_structure(b)
    def test_invalid_dates(self):
        b=minimal();b['data_scope']['Planning_Horizon'][0]='2017-99-01'
        with self.assertRaises(BriefRejected):validate_structure(b)
    def test_nonfinite_and_python_objects(self):
        for value in [float('nan'),float('inf'),float('-inf'),object(),(1,2)]:
            with self.assertRaises(BriefRejected):canonical_bytes({'x':value})
    def test_deterministic_digest(self):
        b=minimal();self.assertEqual(digest(b),digest(json.loads(canonical_bytes(b))));b['brief_status']='BLOCKED';self.assertNotEqual(digest(b),digest(minimal()))
    def test_null_reason_and_unknown_record(self):
        b=minimal();r={'kind':'service','values':{k:None for k in KINDS['service']},'source_ref':'s3','value_states':{}}
        b['service_analysis']['records']=[r];b['service_analysis']['selection'].update(total_rows=1,returned_rows=1)
        with self.assertRaises(BriefRejected):validate_structure(b)
    def test_wrong_truncation(self):
        b=minimal();b['planning_summary']['selection']['truncated']=True
        with self.assertRaises(BriefRejected):validate_structure(b)

    def test_valid_null_ratio_with_reasons(self):
        b=minimal();values={k:0 for k in KINDS['service']}
        values.update(Aggregation_Level='Scenario',Scenario='Baseline',Order_Date=None,
          Fulfillment_Basis='HORIZON_ORIGIN_COHORT',Ratio_Zero_Policy='UNDEFINED_WHEN_DENOMINATOR_ZERO',
          Demand_Fulfillment_Rate=None,Production_Coverage_Rate=None)
        r={'kind':'service','values':values,'source_ref':'s3','value_states':{'Order_Date':'NOT_APPLICABLE',
          'Demand_Fulfillment_Rate':'UNDEFINED_DENOMINATOR','Production_Coverage_Rate':'UNDEFINED_DENOMINATOR'}}
        b['service_analysis']['records']=[r];b['service_analysis']['source_refs']=['s3'];b['service_analysis']['selection'].update(total_rows=1,returned_rows=1)
        validate_structure(b)
