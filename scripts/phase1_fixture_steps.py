"""Browser coverage using existing synthetic, zero-pool and rejected Runs."""
from pathlib import Path
import json
import re
import os

REPO=Path(__file__).resolve().parents[1]
PATHS={
    'synthetic':REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324',
    'zero':REPO/'tmp/planning_source_runs/sequential_20261117T123838_5a317a36b54d',
    'reject':REPO/'tmp/planning_source_runs/sequential_20261117T124401_d4d42e5adb4f',
}


def run_steps(g):
    page=g['page'];act=g['act'];case=g['case'];select=g['select'];wrap=g['wrap'];shot=g['shot'];download=g['download'];ui=g['ui']
    if os.environ.get('P1_FIXTURE_CASE')=='zero_only':
        execute=case
        case=lambda id,expected,fn:execute(id,expected,fn) if id=='NC-N03' else None
    def tab(name):
        t=page.get_by_role('tab',name=name,exact=True);t.click()
        p=page.locator('[id='+json.dumps(t.get_attribute('aria-controls'))+']');p.wait_for(state='visible');return p
    def wp1():tab('Planning Risk Summary');return tab('Root Cause Investigation')
    def load(path):
        def fn():
            f=page.get_by_label('Published sequential run folder',exact=True);f.fill(str(path));f.press('Enter')
        act(fn)
    def wselect(label,value):
        wp1();text=wrap(label).inner_text().split('\n')[-1]
        if (text==value if isinstance(value,str) else value.search(text)):return
        select(label,value);wp1()
    def synthetic():
        load(PATHS['synthetic'])
        assert 'SYNTHETIC_DEMO' in page.get_by_text('Active results:',exact=False).first.inner_text()
        assert 'Select Reference explicitly' in wrap('Reference Scenario').inner_text()
        select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
        target=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)',exact=True))
        act(lambda:(target.get_by_role('combobox').click(),page.get_by_role('option',name='Priority 3',exact=True).click()));page.keyboard.press('Escape')
        for kind in ['metrics','cohort_membership','evidence_refs','context']:download('synthetic_p3',kind)
        select('Comparison product to investigate','1')
        act(lambda:page.get_by_role('button',name='Investigate Candidate in WP1',exact=True).click())
        wp1();assert 'Combined_Stress' in wrap('Sequential scenario').inner_text()
        assert wrap('Investigation product').inner_text().split('\n')[-1]=='1'
        a=shot('NC_SYN_product_path',wrap('Investigation path'))
        wselect('Investigation path','Plant → Week → Product')
        wselect('Investigation week (Sunday ending)',re.compile('2017-01-22'))
        b=shot('NC_SYN_plant_path',wrap('Investigation path'))
        tab('Scenario Trade-off Analysis')
        assert 'Baseline' in wrap('Reference Scenario').inner_text() and 'Combined_Stress' in wrap('Candidate Scenario').inner_text()
        return {'mode':'SYNTHETIC_DEMO','Run_ID':PATHS['synthetic'].name,'actual_four_downloads':True,'WP1_two_paths_and_candidate_handoff':True,'screenshots':[a,b]}
    case('NC-SYNTHETIC','Existing SYNTHETIC_DEMO Run supports actual WP1/WP2/exports without new planning.',synthetic)
    def zero():
        load(PATHS['zero']);select('Sequential scenario','Baseline')
        select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
        exp=page.get_by_text('Shared plant capacity pool context — counted once',exact=True);exp.click()
        a=shot('NC_N03_shared_zero_pool',exp)
        # Both scopes use the same existing Run. WP1 selects the native zero pool.
        wp1();wselect('Investigation path','Plant → Week → Product');wselect('Investigation plant','SITE-1')
        wselect('Investigation week (Sunday ending)',re.compile('2017-01-22'))
        key=f"{PATHS['zero'].name} · Baseline · SITE-1"
        assert page.get_by_text(key,exact=False).first.is_visible()
        b=shot('NC_N03_WP1_zero_pool',wrap('Investigation path'))
        label=page.get_by_text('Evidence: shared_capacity',exact=True);label.click()
        label.scroll_into_view_if_needed()
        with page.expect_download(timeout=60000) as event:page.get_by_role('button',name='Download shared_capacity investigation evidence',exact=True).click()
        file=event.value;assert file.failure() is None
        target=Path(g['ROOT'])/'downloads/zero_shared_capacity.csv';file.save_as(str(target))
        import csv
        rows=list(csv.DictReader(target.open()));assert len(rows)==1
        assert float(rows[0]['Available_Workload_Capacity'])==float(rows[0]['Allocated_Workload'])==0
        assert float(rows[0]['Unmet_Workload'])==7
        tab('Planning Risk Summary');panel=tab('Plant Bottlenecks')
        select('Plant drill-down','SITE-1');tab('Planning Risk Summary');tab('Plant Bottlenecks')
        c=shot('NC_N03_zero_capacity_chart',page.get_by_role('tab',name='Plant Bottlenecks',exact=True))
        return {'Run_ID':PATHS['zero'].name,'pool':rows[0],'download':str(target),'scope':'single zero plant-week pool, not all-horizon capacity','screenshots':[a,b,c]}
    case('NC-N03','Existing zero-capacity plant-week reconciles native pool and displayed evidence; no false all-horizon service claim.',zero)
    def rejected():
        load(PATHS['reject']);warning=page.get_by_text('sequential run is incomplete, failed or unpublished',exact=False)
        assert warning.is_visible()
        assert page.get_by_role('tab',name='Scenario Trade-off Analysis',exact=True).count()==0
        assert page.get_by_role('button',name='Download Comparison CSV',exact=True).count()==0
        return {'warning':warning.inner_text(),'no_stale_comparison':True,'screenshot':shot('NC_N08_rejected_run',warning)}
    case('NC-N08-UNPUBLISHED','Existing failed/unpublished Run is rejected with no stale comparison/export.',rejected)
    def invalid_snapshot(kind):
        import tempfile
        import shutil
        root=Path(g['ROOT'])
        # Disposable invalid test fixtures, never a new planning/publication.
        with tempfile.TemporaryDirectory(prefix='browser_invalid_',dir=root/'fixtures') as name:
            folder=Path(name)
            if kind=='hash':
                primary=REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'
                manifest=json.loads((primary/'run_manifest.json').read_text())
                shutil.copyfile(primary/'run_manifest.json',folder/'run_manifest.json')
                for record in manifest['Artifacts'].values():shutil.copyfile(primary/record['Path'],folder/record['Path'])
                (folder/'allocation_result.csv').write_text('deliberately invalid disposable test fixture')
                expected='artifact missing or hash mismatch'
            else:
                (folder/'run_manifest.json').write_text('null')
                expected='sequential manifest must be a JSON object'
            load(folder);warning=page.get_by_text(expected,exact=False)
            assert warning.is_visible()
            assert page.get_by_role('button',name='Download Comparison CSV',exact=True).count()==0
            assert page.get_by_role('tab',name='Scenario Trade-off Analysis',exact=True).count()==0
            return {'fixture_kind':kind,'controlled_warning':warning.inner_text(),'cleanup':'TemporaryDirectory removes fixture after case','no_new_run_or_publication':True,
                'screenshot':shot('NC_N08_'+kind+'_rejection',warning)}
    case('NC-N08-CORRUPTED','Isolated hash-corrupt snapshot is rejected by actual browser production loader.',lambda:invalid_snapshot('hash'))
    case('R1-BROWSER-NULL','Malformed null manifest shows controlled warning, no uncontrolled browser exception/export.',lambda:invalid_snapshot('null'))
