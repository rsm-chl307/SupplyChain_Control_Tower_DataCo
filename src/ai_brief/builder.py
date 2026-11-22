"""Projection/provenance only. No Planning execution or new KPI formulas."""
from dataclasses import dataclass,field
import hashlib,json,math
import pandas as pd

from src.ai_brief.adapter import SourceBundle, SourceBlocked
from src.ai_brief.contract import (KINDS, RUN_FIELDS,SCOPE_FIELDS,SECTIONS,VERSION,DEFINITIONS,PRIVACY,
                                   BriefRejected,canonical_bytes)
from src.planning_risk import product_risk_ranking,risk_driver_details,investigation_views

LIMITATIONS=(
 'Demand basis is declared by the source configuration; no forecast model is generated.',
 'Synthetic workload standards and capacity recipes must be labeled in input assumptions.',
 'Cross-product ranking retains product priority; backlog is served first within each product.',
 'Receipt Order_Date is explicitly the week supply is usable.',
 'No production lead-time configuration or procurement optimization.')

@dataclass(frozen=True,slots=True)
class DraftBrief:
    _json: bytes=field(repr=False)
    _bundle: SourceBundle=field(repr=False)
    max_records: int=2
    def as_dict(self):return json.loads(self._json)


def scalar(value):
    """Serialization only; does not replace missing source values with zero."""
    if value is None or value is pd.NA or pd.isna(value):return None
    if isinstance(value,pd.Timestamp):return value.date().isoformat()
    if hasattr(value,'item'):value=value.item()
    if isinstance(value,float) and not math.isfinite(value):raise BriefRejected('Non-finite source value')
    if type(value) not in (str,int,float,bool):raise BriefRejected('Unsupported source scalar')
    return value


def build_draft(bundle: SourceBundle, *, max_records: int=2) -> DraftBrief:
    if type(bundle) is not SourceBundle or type(max_records) is not int or not 1<=max_records<=4:
        raise BriefRejected('Verified source bundle and row bound 1..4 required')
    bundle.revalidate()
    m,t=bundle.manifest(),bundle.tables();scenario=bundle.scenario
    if (m.get('Data_Mode')!='SYNTHETIC_DEMO' or
        not t['demand_coverage'].Coverage_Status.isin(['OBSERVED_ZERO','OBSERVED_DEMAND']).all()):
        raise BriefRejected('Only approved fully covered synthetic planning results are supported')
    report=m['Input_Validation']
    approved_assumption={'Name':'complete_order_extract','Value':True,
      'Reason':'No-order internal-lifespan weeks treated as covered zero; edge/outside-lifespan weeks remain UNKNOWN',
      'Classification':'SYNTHETIC_ASSUMPTION'}
    if report.get('Errors') or any(a!=approved_assumption for a in report.get('Assumptions',[])):
        raise BriefRejected('Unreviewed input errors/assumptions; only the pinned complete fixture is supported')
    allowed_warning='USER_PROVIDED means supplied by the user, not independently verified historical fact.'
    if any(w!=allowed_warning for w in report.get('Warnings',[])):
        raise BriefRejected('Unreviewed source warning text')
    quantity=m['Scope']['Quantity_Unit'];workloads=set(t['workload_factors'].Workload_Unit)
    if len(workloads)!=1 or set(t['pools'].Workload_Unit)!=workloads:
        raise BriefRejected('Inconsistent workload units')
    aliases={}
    for prefix,values in [('P', sorted(set(t['initial_state'].Plant_ID)|set(t['initial_state']['Product Card Id']))),
                          ('R',[m['Run_ID']])]:
        for i,value in enumerate(values,1):aliases[(prefix,str(value))]=f'{prefix}-{i}'
    comparison=json.loads(bundle.comparison_json) if bundle.comparison_json else None
    if comparison:aliases[('C',comparison['context']['Comparison_ID'])]='C-1'
    def value(field,v):
        if field=='Scope':
            # Exact existing comparison scope with consistent private aliases.
            v=json.loads(json.dumps(v))
            v['product_ids']=[aliases[('P',str(x))] for x in v['product_ids']]
            v['plant_ids']=[aliases[('P',str(x))] for x in v['plant_ids']]
            return v
        v=scalar(v)
        if field=='Order_Date' and isinstance(v,str):v=pd.Timestamp(v).date().isoformat()
        if v is not None and field in ['Run_ID','Reference_Run_ID','Candidate_Run_ID']:return aliases[('R',v)]
        if v is not None and field in ['Plant_ID','Product Card Id']:return aliases[('P',v)]
        if v is not None and field=='Comparison_ID':return aliases[('C',v)]
        return v
    # Private resolver is reconstructible from immutable bundle; no raw aliases in public JSON.
    sources=[]
    source_rows={k:v['Rows'] for k,v in m['Artifacts'].items()}
    source_rows['run_manifest']=1
    hashes={k:v['SHA256'] for k,v in m['Artifacts'].items()};hashes['run_manifest']=hashlib.sha256(dict(bundle._snapshot)['run_manifest']).hexdigest()
    def provenance(artifact,fields,grain,index=None,pointer=None,definition='published',upstreams=()):
        source='s'+str(len(sources)+1)
        h=hashes[artifact] if artifact in hashes else hashlib.sha256(canonical_bytes([hashes[u] for u in upstreams])).hexdigest()
        sources.append({'source_ref_id':source,'artifact_name':artifact,'artifact_sha256':h,
         'rows':source_rows.get(artifact,1),
         'field_names':list(fields),'native_grain':grain,'Run_ID':'R-1',
         'record_locator':{'kind':'HASH_BOUND_ROW' if index is not None and definition=='published' else 'VIEW_ROW' if definition!='published' else 'MANIFEST_POINTER',
                           'index':index,'pointer':pointer},'definition_ref':definition,'upstream_hashes':[hashes[u] for u in upstreams]})
        return source
    run={k:m.get(k) for k in RUN_FIELDS}
    run.update(Run_ID='R-1',Scenario=scenario,Comparison_ID='C-1' if comparison else None)
    run['source_ref']=provenance('run_manifest',RUN_FIELDS,'Run',pointer='Run+authorized-selection')
    scope={k:m['Scope'].get(k) for k in SCOPE_FIELDS}
    scope.update(Product_IDs=[aliases[('P',str(v))] for v in m['Scope']['Product_IDs']],
                 Plant_IDs=[aliases[('P',str(v))] for v in sorted(t['initial_state'].Plant_ID.unique())],Data_Mode=m['Data_Mode'])
    scope['source_ref']=provenance('run_manifest',SCOPE_FIELDS,'Run',pointer='Scope+initial_state.Plant_ID.unique',upstreams=('initial_state',))
    brief={'brief_version':VERSION,'brief_status':'DRAFT','schema_version':'ai_brief_1.0',
           'definition_version':DEFINITIONS,'privacy_policy_version':PRIVACY,'run_context':run,'data_scope':scope,'source_manifest':sources}
    rows={s:[] for s in SECTIONS}
    def add(section,kind,row,artifact,grain,index=None,pointer=None,definition='published',upstreams=()):
        rows[section].append((kind,row,artifact,grain,index,pointer,definition,upstreams))
    def frame(section,kind,f,artifact,grain,definition='published',upstreams=()):
        if definition!='published':source_rows[artifact]=len(f)
        for idx,row in f.iterrows():add(section,kind,row,artifact,grain,int(idx),None,definition,upstreams)
    selected=t['allocation'].loc[t['allocation'].Scenario.eq(scenario)]
    pools=t['pools'].loc[t['pools'].Scenario.eq(scenario)]
    perf=t['performance'].loc[t['performance'].Scenario.eq(scenario)]
    summary=perf.loc[perf.Aggregation_Level.eq('Scenario')]
    if len(summary)!=1:raise BriefRejected('Scenario summary missing or ambiguous')
    add('data_quality','quality',m['Input_Validation'],'run_manifest','Run',pointer='Input_Validation')
    for idx,row in enumerate(report.get('Assumptions',[])):
        add('data_quality','assumption',row,'run_manifest','Run',pointer=f'Input_Validation.Assumptions.{idx}')
    frame('data_quality','check',t['validation_result'],'validation_result','Check occurrence')
    for idx,row in enumerate(m['Input_Validation']['Sources']):add('data_quality','source',row,'run_manifest','Source',pointer=f'Input_Validation.Sources.{idx}')
    for idx,row in enumerate(m['Configuration']['scenarios']):
        if row['Scenario']==scenario:add('planning_summary','scenario_config',row,'run_manifest','Scenario',pointer=f'Configuration.scenarios.{idx}')
    frame('planning_summary','summary',summary,'performance_result','Scenario')
    add('planning_summary','config',m['Configuration'],'run_manifest','Run',pointer='Configuration')
    frame('capacity_analysis','capacity',summary,'performance_result','Scenario')
    frame('capacity_analysis','pool',pools,'capacity_pools','Scenario × Plant × Week')
    frame('service_analysis','service',summary,'performance_result','Scenario')
    frame('service_analysis','service',perf.loc[perf.Aggregation_Level.eq('Scenario × Week')],'performance_result','Scenario × Week')
    frame('inventory_analysis','terminal',summary,'performance_result','Scenario')
    frame('inventory_analysis','inventory',selected,'allocation_result','Scenario × Plant × Product × Week')
    product=product_risk_ranking(selected).reset_index(drop=True)
    drivers=risk_driver_details(selected,pools).reset_index(drop=True)
    source_rows.update(product_risk=len(product),risk_driver=len(drivers))
    # Interleave a summary and a detailed driver so default preview represents both.
    for idx in range(max(len(product),len(drivers))):
        if idx<len(product):add('risk_analysis','risk',product.iloc[idx],'product_risk','Scenario × Product',idx,None,'planning_risk',('allocation_result',))
        if idx<len(drivers):add('risk_analysis','driver',drivers.iloc[idx],'risk_driver','Scenario × Plant × Product × Week',idx,None,'planning_risk',('allocation_result','capacity_pools'))
    if bundle.investigation:
        s=bundle.investigation
        views=investigation_views(t['allocation'],t['pools'],run_id=m['Run_ID'],scenario=scenario,plant_id=s.plant_id,product_id=s.product_id,week=s.week)
        for name,kind,grain in [('selected_week','inventory','Scenario × Plant × Product × Week'),('shared_capacity','pool','Scenario × Plant × Week'),('observed_signals','driver','Scenario × Plant × Product × Week'),('adjacent_weeks','inventory','Scenario × Plant × Product × Week')]:
            frame('root_cause_evidence',kind,views[name].reset_index(drop=True),'investigation_'+name,grain,'investigation_views',('allocation_result','capacity_pools'))
    if comparison:
        source_rows.update(comparison_metrics=len(comparison['metrics']),comparison_membership=len(comparison['cohort_membership']))
        add('scenario_comparison','comparison_context',comparison['context'],'comparison_context','Comparison',pointer='context',definition='scenario_comparison',upstreams=('allocation_result','capacity_pools','performance_result'))
        metric_rows=list(enumerate(comparison['metrics']))
        metric_rows.sort(key=lambda pair: (pair[1]['Metric_ID']!='Horizon_Service_Level', ['ALL','SELECTED','COMPLEMENT'].index(pair[1]['Cohort_ID']),pair[0]))
        for idx,row in metric_rows:add('scenario_comparison','comparison_metric',row,'comparison_metrics','Comparison',idx,None,'scenario_comparison',('allocation_result','capacity_pools','performance_result'))
        for idx,row in enumerate(comparison['cohort_membership']):add('scenario_comparison','membership',row,'comparison_membership','Comparison',idx,None,'scenario_comparison',('allocation_result',))
    for idx,row in enumerate(report.get('Assumptions',[])):
        add('system_limitations','assumption_reason',row,'run_manifest','Run',pointer=f'Input_Validation.Assumptions.{idx}')
    for idx,text in enumerate(report.get('Warnings',[])):
        add('system_limitations','warning',{'Warnings':text},'run_manifest','Run',pointer=f'Input_Validation.Warnings.{idx}')
    for idx,text in enumerate(m['Limitations']):
        if text not in LIMITATIONS:raise BriefRejected('Unreviewed source limitation text')
        add('system_limitations','limitation',{'Limitations':text},'run_manifest','Run',pointer=f'Limitations.{idx}')
    for section,candidates in rows.items():
        records=[]
        for kind,row,artifact,grain,index,pointer,definition,upstreams in candidates[:max_records]:
            values={k:value(k,row.get(k)) for k in KINDS[kind]}
            states={k:('UNDEFINED_DENOMINATOR' if any(x in k for x in ['Rate','Utilization','Numerator','Denominator','Value','Delta']) else 'NOT_APPLICABLE' if k in ['Order_Date','Plant_ID'] else 'SOURCE_MISSING') for k,v in values.items() if v is None}
            # Optional missing comparison numerators need not be zero denominators.
            if kind=='comparison_metric':
                for k in states:
                    if k in ['Order_Date','Plant_ID','Fulfillment_Basis']:
                        states[k]='NOT_APPLICABLE'
                    elif 'Empty cohort' in values.get('Reason',''):
                        states[k]='EMPTY_SELECTION'
                    elif k.endswith(('Numerator','Denominator')):
                        states[k]='NOT_APPLICABLE'
                    elif 'Zero denominator' in values.get('Reason',''):
                        states[k]='UNDEFINED_DENOMINATOR'
                    elif values.get('Comparability_Status')=='BLOCKED':
                        states[k]='UNSUPPORTED'
                    else:
                        states[k]='SOURCE_MISSING'
            source=provenance(artifact,values,grain,index,pointer,definition,upstreams)
            records.append({'kind':kind,'values':values,'source_ref':source,'value_states':states})
        optional=section in ['root_cause_evidence','scenario_comparison']
        availability='CONDITIONAL' if optional else 'DERIVABLE' if section=='risk_analysis' else 'AVAILABLE'
        reason='Explicit selection not supplied' if optional and not records else 'Bounded existing evidence; no new KPI calculation'
        brief[section]={'availability':availability,'reason':reason,
          'selection':{'Run_ID':'R-1','Scenario':scenario,'total_rows':len(candidates),'returned_rows':len(records),'truncated':len(candidates)>len(records)},
          'records':records,'source_refs':[r['source_ref'] for r in records]}
    bundle.revalidate()
    return DraftBrief(canonical_bytes(brief),bundle,max_records)
