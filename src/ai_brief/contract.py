"""Versioned closed JSON Schema and deterministic transport; no business math."""
import hashlib
import json
import math
from datetime import date, datetime

from jsonschema import Draft202012Validator, FormatChecker

VERSION='1.0'
DEFINITIONS='sequential_v1.kpi1.risk1.comparison1'
PRIVACY='synthetic-minimized-1'
MAX_BYTES=32768
SECTIONS=('data_quality','planning_summary','capacity_analysis','service_analysis',
          'inventory_analysis','risk_analysis','root_cause_evidence','scenario_comparison','system_limitations')
AVAILABILITY=('AVAILABLE','DERIVABLE','CONDITIONAL','NOT_AVAILABLE','REQUIRES_OWNER_DECISION')
STATES=('UNDEFINED_DENOMINATOR','SOURCE_MISSING','NOT_APPLICABLE','EMPTY_SELECTION','UNSUPPORTED')
GRAINS=('Run','Source','Check occurrence','Scenario','Scenario × Plant','Scenario × Week',
        'Scenario × Plant × Week','Scenario × Plant × Product × Week','Scenario × Product','Comparison')


def obj(properties,required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}

def enum(*values):return {'enum':list(values)}
TEXT={'type':'string','minLength':1,'maxLength':256}
NUMBER={'type':['number','null']}
INTEGER={'type':'integer','minimum':0,'maximum':1000000}
DATE={'type':'string','format':'date'}
DATETIME={'type':'string','format':'date-time'}
ALIAS={'type':'string','pattern':r'^[RPC]-[1-9][0-9]*$'}
SCENARIO=enum('Baseline','Demand_Surge','Capacity_Disruption','Combined_Stress')
POLICY=enum('CARRY_FORWARD','LOST_SALES')
LEVEL=enum(*GRAINS)

# Each source-specific values object is closed. No Product Name/order rows/paths.
KINDS={
 'assumption':{'Name':enum('complete_order_extract'),'Value':{'type':'boolean'},'Classification':enum('SYNTHETIC_ASSUMPTION')},
 'assumption_reason':{'Reason':TEXT},
 'warning':{'Warnings':TEXT},
 'limitation':{'Limitations':TEXT},
 'quality':{'Status':enum('READY'),'Data_Mode':enum('SYNTHETIC_DEMO')},
 'check':{'Check_ID':TEXT,'Passed':{'type':'boolean'},'Rows_Checked':INTEGER},
 'source':{'Dataset':enum('products','plants','product_plant_mapping','demand','workload_factors','initial_inventory','external_receipts','weekly_capacity'),
           'Rows':INTEGER,'Classification':enum('SYNTHETIC_DEMO')},
 'config':{'assumption_version':TEXT,'planning_interpretation':enum('RETROSPECTIVE','USER_PROVIDED_PLAN'),
           'planning_start_week':DATE,'planning_end_week':DATE,'quantity_step':NUMBER,'allocation_policy':TEXT},
 'scenario_config':{'Scenario':SCENARIO,'Demand_Multiplier':NUMBER,'Capacity_Multiplier':NUMBER,'Backlog_Policy':POLICY},
 'summary':{'Aggregation_Level':enum('Scenario'),'Scenario':SCENARIO,'Backlog_Policy':POLICY,
            **{k:NUMBER for k in ['Scenario_Qualified_Demand','Required_Production_Qty','Internal_Production_Qty','External_Receipts_Qty']}},
 'pool':{'Scenario':SCENARIO,'Plant_ID':ALIAS,'Order_Date':DATE,'Workload_Unit':TEXT,'Factor_Version':TEXT,
         **{k:NUMBER for k in ['Baseline_Workload_Capacity','Available_Workload_Capacity','Allocated_Workload','Remaining_Workload_Capacity','Unmet_Workload']},
         'Workload_Shortage':{'type':'boolean'}},
 'capacity':{'Aggregation_Level':enum('Scenario'),'Scenario':SCENARIO,**{k:NUMBER for k in ['Capacity_Utilization','Available_Workload_Capacity','Allocated_Workload','Remaining_Workload_Capacity','Bottleneck_Plant_Weeks']}},
 'service':{'Aggregation_Level':enum('Scenario','Scenario × Week'),'Scenario':SCENARIO,
         'Order_Date':{'anyOf':[DATE,{'type':'null'}]},'Fulfillment_Basis':enum('HORIZON_ORIGIN_COHORT','CURRENT_WEEK_COHORT'),
         'Ratio_Zero_Policy':enum('UNDEFINED_WHEN_DENOMINATOR_ZERO'),
         **{k:NUMBER for k in ['Demand_Fulfillment_Rate','Demand_Fulfillment_Numerator','Demand_Fulfillment_Denominator','Production_Coverage_Rate','Fulfilled_Current_Qty','Fulfilled_Horizon_Backlog_Qty','Fulfilled_Opening_Backlog_Qty','Lost_Sales_Qty']}},
 'inventory':{'Scenario':SCENARIO,'Plant_ID':ALIAS,'Product Card Id':ALIAS,'Order_Date':DATE,'Backlog_Policy':POLICY,'Quantity_Unit':TEXT,
         **{k:NUMBER for k in ['Beginning_Inventory','Beginning_Backlog','Beginning_Opening_Backlog','External_Receipts_Qty','Ending_Inventory','Ending_Backlog','Ending_Opening_Backlog','Ending_Horizon_Backlog']}},
 'terminal':{'Aggregation_Level':enum('Scenario'),'Scenario':SCENARIO,**{k:NUMBER for k in ['Ending_Inventory','Ending_Backlog','Ending_Opening_Backlog','Ending_Horizon_Backlog']}},
 'risk':{'Scenario':SCENARIO,'Product Card Id':ALIAS,'Planning_Priority':enum(1,2,3),'Risk_Category':enum('At Risk','Watch','Healthy'),
         **{k:NUMBER for k in ['Demand_Fulfillment_Rate','Production_Coverage_Rate','Ending_Backlog','Lost_Sales_Qty','Unmet_Workload']}},
 'driver':{'Scenario':SCENARIO,'Plant_ID':ALIAS,'Product Card Id':ALIAS,'Order_Date':DATE,
         **{k:NUMBER for k in ['Product_Unmet_Workload','Product_Allocated_Workload','Plant_Week_Allocated_Workload','Plant_Week_Unmet_Workload','Plant_Week_Capacity_Utilization','Capacity_Reduction_From_Baseline']},
         'Capacity_Shortage':{'type':['boolean','null']}},
 'comparison_context':{'Comparison_ID':ALIAS,'Reference_Run_ID':ALIAS,'Candidate_Run_ID':ALIAS,'Reference_Scenario':SCENARIO,'Candidate_Scenario':SCENARIO,
         'Comparison_Schema_Version':enum('comparison_v1'),'Reference_Backlog_Policy':POLICY,'Candidate_Backlog_Policy':POLICY,
         'Policy_Comparison':enum('SAME_POLICY','POLICY_CONTRAST','UNAVAILABLE'),'Priority_Changed_Product_Count':INTEGER},
 'comparison_metric':{'Comparison_ID':ALIAS,'Cohort_ID':enum('ALL','SELECTED','COMPLEMENT'),
         'Metric_ID':enum('Horizon_Service_Level','Weekly_Service_Level','Terminal_Backlog','Lost_Sales','Allocated_Workload','Unmet_Workload','Fulfilled_Quantity','Current_Unfulfilled_Quantity','Terminal_Opening_Backlog','Terminal_Horizon_Backlog'),
         'Aggregation_Level':LEVEL,'Plant_ID':{'anyOf':[ALIAS,{'type':'null'}]},'Order_Date':{'anyOf':[DATE,{'type':'null'}]},
         'Unit':TEXT,'Delta_Unit':TEXT,'Reference_Unit':TEXT,'Candidate_Unit':TEXT,
         'Reason':{'type':'string','maxLength':512},
         'Fulfillment_Basis':{'enum':['HORIZON_ORIGIN_COHORT','CURRENT_WEEK_COHORT',None]},
         'Comparability_Status':enum('COMPARABLE','DESCRIPTIVE_ONLY','BLOCKED'),
         **{k:NUMBER for k in ['Reference_Value','Candidate_Value','Reference_Numerator','Reference_Denominator','Candidate_Numerator','Candidate_Denominator','Delta']}},
 'membership':{'Product Card Id':ALIAS,'Cohort Membership':enum('SELECTED','COMPLEMENT'),'Priority Changed':{'type':'boolean'}},
}
KINDS['comparison_context']['Scope']=obj({
 'product_ids':{'type':'array','items':ALIAS,'maxItems':100},
 'plant_ids':{'type':'array','items':ALIAS,'maxItems':100},
 'start_week':DATE,'end_week':DATE,
 'selected_priorities':{'type':'array','items':enum(1,2,3),'uniqueItems':True,'maxItems':3},
 'cohort_basis':enum('FIXED_REFERENCE_PRIORITY'),
 'metric_ids':{'type':'array','items':TEXT,'maxItems':10},'output_grain':LEVEL})
RUN_FIELDS={'Run_ID':ALIAS,'Schema_Version':enum('sequential_v1'),'Execution_Status':enum('SUCCEEDED'),
            'Validation_Status':enum('PASSED'),'Publication_Status':enum('PUBLISHED'),'Scenario':SCENARIO,
            'Started_At':DATETIME,'Finished_At':DATETIME,'Comparison_ID':{'anyOf':[ALIAS,{'type':'null'}]}}
SCOPE_FIELDS={'Planning_Horizon':{'type':'array','items':DATE,'minItems':2,'maxItems':2},
    'Product_IDs':{'type':'array','items':ALIAS,'minItems':1,'maxItems':100},'Plant_IDs':{'type':'array','items':ALIAS,'minItems':1,'maxItems':100},
    'Selected_Products':INTEGER,'Quantity_Unit':TEXT,'Demand_Basis':enum('RETROSPECTIVE','USER_PROVIDED_PLAN'),'Data_Mode':enum('SYNTHETIC_DEMO')}


def record_schema(kind,fields):
    return obj({'kind':enum(kind),'values':obj(fields),'source_ref':TEXT,
                'value_states':obj({k:enum(*STATES) for k in fields},required=[])})

RECORD={'oneOf':[record_schema(k,v) for k,v in KINDS.items()]}
SELECTION=obj({'Run_ID':ALIAS,'Scenario':SCENARIO,'total_rows':INTEGER,'returned_rows':INTEGER,'truncated':{'type':'boolean'}})
SECTION=obj({'availability':enum(*AVAILABILITY),'reason':TEXT,'selection':SELECTION,
             'records':{'type':'array','items':RECORD,'maxItems':64},'source_refs':{'type':'array','items':TEXT,'maxItems':64}})
SOURCE=obj({'source_ref_id':TEXT,'artifact_name':TEXT,'artifact_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
     'rows':INTEGER,'field_names':{'type':'array','items':TEXT,'maxItems':40},'native_grain':LEVEL,
     'Run_ID':ALIAS,'record_locator':obj({'kind':enum('MANIFEST_POINTER','HASH_BOUND_ROW','VIEW_ROW'),'index':{'type':['integer','null'],'minimum':0},'pointer':{'type':['string','null'],'maxLength':128}}),
     'definition_ref':enum('published','planning_risk','investigation_views','scenario_comparison'),
     'upstream_hashes':{'type':'array','items':{'type':'string','pattern':'^[a-f0-9]{64}$'},'maxItems':12}})
SCHEMA={'$schema':'https://json-schema.org/draft/2020-12/schema',**obj({
    'brief_version':enum(VERSION),'brief_status':enum('DRAFT','VALIDATED','BLOCKED'),
    'schema_version':enum('ai_brief_1.0'),'definition_version':enum(DEFINITIONS),'privacy_policy_version':enum(PRIVACY),
    'run_context':obj({**RUN_FIELDS,'source_ref':TEXT}), 'data_scope':obj({**SCOPE_FIELDS,'source_ref':TEXT}),
    **{k:SECTION for k in SECTIONS},'source_manifest':{'type':'array','items':SOURCE,'maxItems':100}})}
VALIDATOR=Draft202012Validator(SCHEMA,format_checker=FormatChecker())


class BriefRejected(ValueError):pass


def canonical_bytes(value):
    def check(v):
        if v is None or type(v) in (str,bool,int):return
        if type(v) is float and math.isfinite(v):return
        if type(v) is list:
            for x in v:check(x)
            return
        if type(v) is dict and all(type(k) is str for k in v):
            for x in v.values():check(x)
            return
        raise BriefRejected('Only finite JSON primitives are permitted')
    check(value)
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def digest(value):return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_structure(brief):
    raw=canonical_bytes(brief)
    if len(raw)>MAX_BYTES:raise BriefRejected('Brief exceeds 32 KiB; select fewer bounded records')
    errors=list(VALIDATOR.iter_errors(brief))
    if errors:raise BriefRejected('Brief schema rejected: '+'.'.join(map(str,errors[0].absolute_path)))
    for section in SECTIONS:
        s=brief[section];selected=s['selection']
        if selected['returned_rows']!=len(s['records']) or selected['total_rows']<selected['returned_rows'] or selected['truncated']!=(selected['total_rows']>selected['returned_rows']):
            raise BriefRejected('Selection/truncation counts disagree')
        for r in s['records']:
            nulls={k for k,v in r['values'].items() if v is None}
            if set(r['value_states'])!=nulls:raise BriefRejected('Every null needs exactly one value-state reason')
    if brief['run_context']['Comparison_ID'] is None and brief['scenario_comparison']['records']:
        raise BriefRejected('Comparison identity missing')
