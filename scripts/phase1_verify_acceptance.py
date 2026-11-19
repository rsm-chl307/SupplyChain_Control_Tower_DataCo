"""Independent actual CSV/Arrow acceptance; preserve all historical evidence."""
from pathlib import Path
import base64
import csv
from decimal import Decimal
import importlib.util
import json
import math
import os
import sys
import traceback

ROOT=Path(os.environ['P1_EVIDENCE_ROOT']).resolve()
REPO=Path(__file__).resolve().parents[1]
csv.field_size_limit(64*1024*1024)


def main():
    # Reuse the independent stdlib/Arrow oracle implementation, not product
    # comparison/KPI functions. Import reads old artifacts; output ROOT is reset
    # before executing anything. Never rewrite original UAT evidence.
    spec=importlib.util.spec_from_file_location('phase1_independent_oracle',REPO/'tmp/wp2_browser_uat_phase_3/verify_data.py')
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    oracle.ROOT=ROOT
    if not (ROOT/'integration_results.json').exists():
        oracle.main()
    result=json.loads((ROOT/'integration_results.json').read_text())
    cases=result['cases']
    if '--primary-only' in sys.argv:
        print(json.dumps({'primary_cases':{k:v['status'] for k,v in cases.items()}}));return
    def check(id,expected,fn):
        try:cases[id]={'section':'E','status':'PASS','expected':expected,'actual':fn()}
        except Exception as e:cases[id]={'section':'E','status':'FAIL','expected':expected,'error':str(e),'traceback':traceback.format_exc()}
    def synthetic():
        browser=json.loads((ROOT/'fixture_browser/browser_results.json').read_text())
        folder=REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324'
        manifest=json.loads((folder/'run_manifest.json').read_text())
        data={kind:oracle.rows(Path(r['path'])) for kind,r in browser['downloads']['synthetic_p3'].items()}
        assert len(data)==4
        contexts={r['Comparison_Context'] for records in data.values() for r in records};assert len(contexts)==1
        context=json.loads(next(iter(contexts)));assert context['Data_Mode']=='SYNTHETIC_DEMO'
        assert context['Reference_Run_ID']==context['Candidate_Run_ID']==manifest['Run_ID']
        oracle.ALLOCATION=oracle.rows(folder/'allocation_result.csv');oracle.END=manifest['Scope']['Planning_Horizon'][1]
        all_products=set(manifest['Scope']['Product_IDs'])
        selected={r['Product Card Id'] for r in data['cohort_membership'] if r['Cohort Membership']=='SELECTED'}
        assert {r['Product Card Id'] for r in data['cohort_membership']}==all_products=={'1','2'}
        groups={'ALL':all_products,'SELECTED':selected,'COMPLEMENT':all_products-selected}
        checked=0
        for row in data['metrics']:
            expected_values=[]
            for prefix,scenario in [('Reference','Baseline'),('Candidate','Combined_Stress')]:
                expected=oracle_value(oracle,scenario,groups[row['Cohort_ID']],row['Metric_ID'],row['Order_Date'])
                expected_values.append(expected);oracle.close(row[prefix+'_Value'],expected)
            if any(v is None for v in expected_values):
                assert row['Delta']=='N/A' and row['Comparability_Status']=='BLOCKED' and row['Reason']
            else:
                oracle.close(row['Delta'],(expected_values[1]-expected_values[0])*(100 if row['Metric_ID'].endswith('Service_Level') else 1))
                assert row['Comparability_Status']=='COMPARABLE'
            checked+=1
        assert len({(r['Side'],r['Artifact_Name']) for r in data['evidence_refs']})==24
        import hashlib
        for row in data['evidence_refs']:
            record=manifest['Artifacts'][row['Artifact_Name']]
            assert row['Artifact_SHA256']==record['SHA256']==hashlib.sha256((folder/record['Path']).read_bytes()).hexdigest()
        return {'metric_rows':checked,'four_actual_exports':True,'mode':'SYNTHETIC_DEMO','same_context_and_native_hashes':True}
    def zero_payload():
        import pyarrow as pa
        import pandas as pd
        from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
        cache={};checks=[]
        frame_path=ROOT/'zero_pool_retry/logs/browser_frames.jsonl'
        if not frame_path.exists():frame_path=ROOT/'fixture_browser/logs/browser_frames.jsonl'
        for line in frame_path.open():
            event=json.loads(line);blob=base64.b64decode(event['payload']);msg=ForwardMsg();msg.ParseFromString(blob)
            if msg.hash:cache[msg.hash]=blob
            if msg.HasField('ref_hash'):
                if msg.ref_hash not in cache:continue
                msg.ParseFromString(cache[msg.ref_hash])
            if event['stage']!='NC-N03' or not msg.HasField('delta') or not msg.delta.HasField('new_element'):continue
            e=msg.delta.new_element
            if not e.HasField('dataframe') or not e.dataframe.arrow_data.data:continue
            df=pa.ipc.open_stream(e.dataframe.arrow_data.data).read_all().to_pandas()
            if not {'Order_Date','Available_Workload_Capacity','Capacity_Utilization'}<=set(df):continue
            part=df.loc[pd.to_datetime(df.Order_Date).eq('2017-01-22') & df.Available_Workload_Capacity.eq(0)]
            for row in part.to_dict('records'):
                assert pd.isna(row['Capacity_Utilization']) and row['Allocated_Workload']==0
                checks.append({'date':str(row['Order_Date']),'available':0,'allocated':0,'utilization':'N/A'})
        assert checks,'No actual browser zero-capacity N/A table payload'
        return {'actual_zero_pool_payloads':len(checks),'rows':checks}
    check('E-SYNTHETIC','Synthetic four actual CSVs match native artifact oracle and context.',synthetic)
    check('E-ZERO-UI','Actual zero-capacity browser table has N/A utilization, no false0%/100%.',zero_payload)
    result['overall_result']='PASS' if all(v['status']=='PASS' for v in cases.values()) else 'FAIL'
    result['counts']={s:sum(v['status']==s for v in cases.values()) for s in ['PASS','FAIL']}
    (ROOT/'reports/integration_results_recovery.json').write_text(json.dumps(result,indent=2,default=str))
    (ROOT/'reports/export_results.json').write_text(json.dumps({'result':result['overall_result'],'cases':{k:v for k,v in cases.items() if k.startswith('E')},'method':'Actual downloads plus native independent oracle and browser Arrow'},indent=2,default=str))
    print(json.dumps({'result':result['overall_result'],'counts':result['counts'],'failed':{k:v.get('error') for k,v in cases.items() if v['status']!='PASS'}}))


def oracle_value(module,scenario,products,metric,week):
    # The preserved Phase 3 oracle is local to its main(). Independent rules
    # below use only native CSV Decimal arithmetic, never production functions.
    data=[r for r in module.ALLOCATION if r['Scenario']==scenario and r['Product Card Id'] in products and (week=='N/A' or r['Order_Date'][:10]==week[:10])]
    total=lambda col:sum((Decimal(r[col]) for r in data),Decimal(0))
    if metric in ['Horizon_Service_Level','Weekly_Service_Level','Fulfilled_Quantity']:
        n=total('Fulfilled_Current_Qty')
        if metric!='Weekly_Service_Level':n+=total('Fulfilled_Backlog_Qty')-total('Fulfilled_Opening_Backlog_Qty')
        denominator=total('Scenario_Qualified_Demand')
        return n if metric=='Fulfilled_Quantity' else n/denominator if denominator else None
    if metric.startswith('Terminal_'):
        col={'Terminal_Backlog':'Ending_Backlog','Terminal_Opening_Backlog':'Ending_Opening_Backlog','Terminal_Horizon_Backlog':'Ending_Horizon_Backlog'}[metric]
        return sum((Decimal(r[col]) for r in data if r['Order_Date'][:10]==module.END),Decimal(0))
    if metric=='Lost_Sales':return total('Lost_Sales_Qty')
    if metric=='Allocated_Workload':return sum((Decimal(r['Internal_Production_Qty'])*Decimal(r['Workload_Factor']) for r in data),Decimal(0))
    if metric=='Unmet_Workload':return sum(((Decimal(r['Required_Production_Qty'])-Decimal(r['Internal_Production_Qty']))*Decimal(r['Workload_Factor']) for r in data),Decimal(0))
    if metric=='Current_Unfulfilled_Quantity':return total('Scenario_Qualified_Demand')-total('Fulfilled_Current_Qty')
    raise AssertionError(metric)


if __name__=='__main__':main()
