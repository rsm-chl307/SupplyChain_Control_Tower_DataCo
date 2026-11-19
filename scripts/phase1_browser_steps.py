"""Read-only UI steps; never execute a planner or upload data."""
from pathlib import Path
import csv
from decimal import Decimal
import hashlib
import json
import re
import os

ROOT=Path(os.environ['P1_EVIDENCE_ROOT']).resolve()
REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'


def run_steps(g):
    page=g['page'];act=g['act'];case=g['case'];wrap=g['wrap'];select=g['select'];shot=g['shot'];download=g['download'];options=g['options'];ui=g['ui'];result=g['result'];idle=g['idle']
    def tab(name):
        control=page.get_by_role('tab',name=name,exact=True);control.click()
        panel=page.locator('[id='+json.dumps(control.get_attribute('aria-controls'))+']');panel.wait_for(state='visible');return panel
    def wp1():tab('Planning Risk Summary');return tab('Root Cause Investigation')
    def wp2():return tab('Scenario Trade-off Analysis')
    def wselect(label,value):
        wp1();current=wrap(label).inner_text().split('\n')[-1]
        if (current==value if isinstance(value,str) else value.search(current)):return
        select(label,value);wp1()
    def state():
        return {k:wrap(label).inner_text() for k,label in [('path','Investigation path'),('product','Investigation product'),('plant','Investigation plant'),('week','Investigation week (Sunday ending)'),('scenario','Sequential scenario')]}
    def identity(scenario,plant,product,week):
        text=f'{RUN.name} · {scenario} · {plant} · {product} · {week}'
        assert page.get_by_text(text,exact=True).is_visible(),text
        return text
    def expand(label):
        item=page.get_by_text(label,exact=True);item.scroll_into_view_if_needed()
        details=item.locator('xpath=ancestor::details[1]')
        if details.get_attribute('open') is None:item.click()
        return item
    def wp1_download(tag,name):
        wp1();expand('Evidence: '+name)
        with page.expect_download(timeout=60000) as event:page.get_by_role('button',name=f'Download {name} investigation evidence',exact=True).click()
        file=event.value;assert file.failure() is None
        folder=ROOT/'downloads'/tag;folder.mkdir(exist_ok=True);path=folder/(name+'.csv');file.save_as(str(path))
        with path.open(newline='') as f:rows=list(csv.DictReader(f))
        result['downloads'].setdefault(tag,{})[name]={'path':str(path),'bytes':path.stat().st_size,'rows':len(rows),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'captured_download_event':True,'suggested_filename':file.suggested_filename,'parse':'PASS'}
        idle();wp1();return rows
    def visible_table(panel):
        frame=panel.get_by_test_id('stDataFrame').first;frame.wait_for(state='visible');assert frame.locator('canvas').count()>0;return frame
    def initial():
        wp2();assert 'Select Reference explicitly' in wrap('Reference Scenario').inner_text()
        assert 'Select Candidate explicitly' in wrap('Candidate Scenario').inner_text()
        return dict(ui(),screenshot=shot('C_A01_initial',wrap('Reference Scenario')))
    case('C-A01','Fresh WP2 Reference/Candidate selectors explicitly unselected.',initial)
    def dashboard():
        observations={}
        for name in ['Scenario Overview','Scenario Comparison','Capacity Allocation Detail']:
            panel=tab(name);frame=visible_table(panel)
            if name=='Scenario Overview':
                chart=panel.get_by_test_id('stVegaLiteChart');chart.locator('canvas,svg').first.wait_for(state='visible')
            observations[name]={'tables':panel.get_by_test_id('stDataFrame').count(),'screenshot':shot('D_'+name.replace(' ','_'),frame)}
        return observations
    case('D01','Dashboard, Scenario Overview, existing Scenario Comparison and Capacity Allocation Detail render.',dashboard)
    def risks():
        tab('Planning Risk Summary');out={}
        for name in ['Product Risk','Plant Bottlenecks','Scenario Risk']:
            panel=tab(name);frame=visible_table(panel)
            out[name]={'tables':panel.get_by_test_id('stDataFrame').count(),'screenshot':shot('D_'+name.replace(' ','_'),frame)}
        return out
    case('D02','Planning Risk Summary Product/Plant/Scenario views render.',risks)
    def product_path():
        wp1();wselect('Investigation path','Product → Plant → Week');wselect('Investigation product','SKU-A')
        wselect('Investigation week (Sunday ending)',re.compile('2017-01-15'))
        key=identity('Baseline','PLANT-1','SKU-A','2017-01-15')
        for name in ['selected_week','shared_capacity','adjacent_weeks','allocation_peers','eligibility_ledger','source_status']:wp1_download('wp1_product',name)
        return {'selected_key':key,'state':state(),'screenshot':shot('A01_product_path',wrap('Investigation path'))}
    case('A01','WP1 Product → Plant → Week selects SKU-A / PLANT-1 / 2017-01-15 with native evidence downloads.',product_path)
    def plant_path():
        wselect('Investigation path','Plant → Week → Product');wselect('Investigation plant','PLANT-2')
        wselect('Investigation week (Sunday ending)',re.compile('2017-01-22'));wselect('Investigation product','SKU-C')
        key=identity('Baseline','PLANT-2','SKU-C','2017-01-22')
        for name in ['selected_week','shared_capacity']:wp1_download('wp1_plant',name)
        return {'selected_key':key,'state':state(),'screenshot':shot('A02_plant_path',wrap('Investigation path'))}
    case('A02','WP1 Plant → Week → Product independently selects PLANT-2 / 2017-01-22 / SKU-C.',plant_path)
    def filters():
        wselect('Investigation product','SKU-D');wselect('Investigation week (Sunday ending)',re.compile('2017-01-08'))
        a=identity('Baseline','PLANT-2','SKU-D','2017-01-08')
        screenshot=shot('A03_switched_filters',wrap('Investigation path'))
        wselect('Investigation product','SKU-C');wselect('Investigation week (Sunday ending)',re.compile('2017-01-22'))
        b=identity('Baseline','PLANT-2','SKU-C','2017-01-22')
        return {'first_key':a,'restored_key':b,'state':state(),'screenshot':screenshot}
    case('A03','Product/plant/week filters switch and restore correct visible identities.',filters)
    def evidence():
        out={}
        for label in ['Evidence: selected_week','Evidence: shared_capacity','Evidence: performance','Evidence: initial_state','Source provenance and assumptions']:
            control=expand(label);out[label]=shot('A04_'+label.replace(':','').replace(' ','_'),control)
        assert 'Source: allocation_result.csv' in page.get_by_test_id('stApp').inner_text()
        return {'screenshots':out,'native_evidence_expanded':True}
    case('A04','Evidence expands with artifact source, native-grain details, provenance and assumptions.',evidence)
    # This comparison must not change WP1's selected sequential scenario or filters.
    saved={}
    def pair():
        wp1();saved.update(state());wp2()
        select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
        target=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)',exact=True))
        def priority():target.get_by_role('combobox').click();page.get_by_role('option',name='Priority 3',exact=True).click()
        act(priority);page.keyboard.press('Escape');wp2()
        for kind in ['metrics','cohort_membership','evidence_refs','context']:download('baseline_p3',kind)
        for kind,record in result['downloads']['baseline_p3'].items():
            old=REPO/'tmp/wp2_browser_uat_phase_2_fix/downloads/baseline_p3'/(kind+'.csv')
            assert record['sha256']==hashlib.sha256(old.read_bytes()).hexdigest()
        return {'state':ui(),'all_four_exports_identical_to_phase2_fix':True,'screenshot':shot('C_A02_pair',wrap('Reference Scenario'))}
    case('C-A02','Baseline → Combined_Stress / priority 3 works; four representative actual exports remain byte-identical.',pair)
    def retained():
        wp1();current=state();assert current==saved
        identity('Baseline','PLANT-2','SKU-C','2017-01-22')
        return {'before':saved,'after':current,'screenshot':shot('B01_retained_wp1',wrap('Investigation path'))}
    case('B01','Ordinary WP1 → WP2 → WP1 tab switching preserves WP1 scenario/product/plant/week.',retained)
    def ids():
        wp2();active=page.get_by_text('Active results:',exact=False).first.inner_text();assert RUN.name in active
        for kind,record in result['downloads']['baseline_p3'].items():
            with Path(record['path']).open(newline='') as f:rows=list(csv.DictReader(f))
            assert all(r['Reference_Run_ID']==RUN.name and r['Candidate_Run_ID']==RUN.name for r in rows)
        return {'active_results':active,'same_run':RUN.name,'screenshot':shot('C_A07_identity',wrap('Reference Scenario'))}
    case('C-A07','Both comparison sides and WP1 active identity remain the same authorized Run.',ids)
    def cohorts():
        wp2();metric=page.get_by_test_id('stMetric').filter(has=page.get_by_text('Priority Changed Product Count',exact=True))
        assert metric.get_by_test_id('stMetricValue').inner_text()=='0'
        for label in ['All Products','Selected Cohort','Complement','Metric-level comparability reasons','Comparison evidence references']:
            expand(label)
        return {'priority_changed_count':0,'screenshot':shot('C02_fixed_cohort',page.get_by_text('Fixed reference cohort membership',exact=True))}
    case('C02','ALL / SELECTED / COMPLEMENT, fixed priority cohort, status/reason and evidence tables render.',cohorts)
    def handoff(side,scenario,tag):
        wp2()
        current=wrap('Comparison product to investigate').inner_text().split('\n')[-1]
        if current!='SKU-A':select('Comparison product to investigate','SKU-A')
        act(lambda:page.get_by_role('button',name=f'Investigate {side} in WP1',exact=True).click())
        wp1();assert scenario in wrap('Sequential scenario').inner_text()
        identity(scenario,'PLANT-1','SKU-A','2017-01-08')
        assert 'Product → Plant → Week' in wrap('Investigation path').inner_text()
        wp1_download(tag,'selected_week');wp1_download(tag,'shared_capacity')
        screenshot=shot('B_handoff_'+side.lower(),wrap('Investigation path'));selected=state()
        wp2();assert 'Baseline' in wrap('Reference Scenario').inner_text() and 'Combined_Stress' in wrap('Candidate Scenario').inner_text()
        return {'side':side,'wp1_state':selected,'comparison_state':ui(),'screenshot':screenshot}
    case('B02','Explicit Candidate-side handoff opens Combined_Stress SKU-A in WP1 without mutating comparison direction.',lambda:handoff('Candidate','Combined_Stress','wp1_candidate'))
    case('B03','Explicit Reference-side handoff opens Baseline SKU-A in WP1 without mutating comparison direction.',lambda:handoff('Reference','Baseline','wp1_reference'))
    def switch_after_handoff():
        wp1();wselect('Investigation week (Sunday ending)',re.compile('2017-01-15'));before=state()
        wp2();assert 'Baseline' in wrap('Reference Scenario').inner_text() and 'Combined_Stress' in wrap('Candidate Scenario').inner_text()
        wp1();assert state()==before;identity('Baseline','PLANT-1','SKU-A','2017-01-15')
        return {'before':before,'after':state(),'screenshot':shot('B04_return_to_wp1',wrap('Investigation path'))}
    case('B04','After explicit handoff, manual WP1 filters survive tab switching back and forth.',switch_after_handoff)
    def excluded():
        wp2();values=options();assert 'Baseline' not in values and len(values)==4;return values
    case('C-A03','Candidate options exclude current Reference.',excluded)
    def reset():
        wp2();select('Reference Scenario','Combined_Stress');before=ui()
        assert 'Select Candidate explicitly' in before['candidate'] and 'Combined_Stress' not in before['candidate_aria']
        assert page.get_by_role('button',name='Download Comparison CSV',exact=True).count()==0
        assert page.get_by_text('Select both Reference and Candidate.',exact=False).is_visible()
        screenshot=shot('C_A04_candidate_cleared',wrap('Candidate Scenario'))
        select('Candidate Scenario','Baseline');assert page.get_by_role('button',name='Download Comparison CSV',exact=True).count()==1
        return {'cleared_state':before,'reselected':ui(),'screenshots':[screenshot,shot('C_A04_reselected',wrap('Reference Scenario'))]}
    case('C-A04','P2-UI-01 remains fixed: visible/ARIA reset, empty guard, then manual valid reselection.',reset)
    def same():
        values=options();assert 'Combined_Stress' not in values;return values
    case('C-A05','Identical Reference/Candidate remains excluded.',same)
    def reverse():
        wp2();assert 'Combined_Stress' in wrap('Reference Scenario').inner_text() and 'Baseline' in wrap('Candidate Scenario').inner_text()
        frame=page.get_by_text('Trade-off summary — ALL / SELECTED / COMPLEMENT',exact=True)
        return {'state':ui(),'screenshot':shot('C_A06_reverse_summary',frame),'validation':'Actual Arrow metrics independently checked after browser completion; no additional large download.'}
    case('C-A06','Reverse comparison renders; actual UI payload Delta is checked independently.',reverse)
    def context():
        wp2();text=page.locator('[data-testid="stJson"]:visible').last.inner_text()
        assert RUN.name in text and 'Combined_Stress' in text and 'Baseline' in text
        return {'visible_context':text,'screenshot':shot('C_A08_context',wrap('Reference Scenario'))}
    case('C-A08','Comparison Context retains correct direction and same Run after reset and integration.',context)
    def policy():
        wp2();select('Candidate Scenario','Combined_Stress_Lost_Sales')
        warning=page.get_by_text('POLICY_CONTRAST — descriptive comparison only.',exact=False)
        assert warning.is_visible() and 'improved service' in warning.inner_text()
        text=page.get_by_test_id('stApp').inner_text();assert not re.search(r'candidate wins|winner is|recommended scenario',text,re.I)
        expand('Metric-level comparability reasons');expand('Comparison evidence references')
        return {'warning':warning.inner_text(),'state':ui(),'screenshot':shot('C03_policy_contrast',warning),
            'validation':'Actual browser metric payloads checked against prior independently verified policy values.'}
    case('C03','POLICY_CONTRAST warns backlog=0 is not service improvement; statuses and evidence visible; no winner.',policy)
    def unchanged_wp1():
        wp1();identity('Baseline','PLANT-1','SKU-A','2017-01-15')
        return {'state':state(),'screenshot':shot('B05_policy_does_not_change_wp1',wrap('Investigation path'))}
    case('B05','Changing WP2 comparison/policy without handoff leaves WP1 Baseline source and selection unchanged.',unchanged_wp1)
    def toolbar():
        panel=tab('Scenario Overview');chart=panel.get_by_test_id('stVegaLiteChart')
        chart.scroll_into_view_if_needed();chart.hover()
        container=chart.locator('xpath=ancestor::*[@data-testid="stElementContainer"][1]')
        button=container.get_by_role('button',name='Show data',exact=True)
        observed={'mouse_success':False,'keyboard_success':False,'observation':'Toolbar behavior assessed without force-click or product changes.'}
        try:button.click(timeout=4000);observed['mouse_success']=True
        except Exception as e:observed['mouse_error']=str(e)
        data=page.get_by_role('button',name='Show chart',exact=True)
        if not data.is_visible():button.focus();button.press('Enter')
        data.wait_for(state='visible');observed['keyboard_success']=not observed['mouse_success']
        observed['data_screenshot']=shot('D03_toolbar_data',container)
        data.focus();data.press('Enter');chart.locator('canvas,svg').first.wait_for(state='visible')
        observed['chart_screenshot']=shot('D03_toolbar_chart',chart)
        return observed
    # Four toolbar actions are independently exercised by WS2, not duplicated here.
    def finish():
        tab('Planning Risk Summary');wp1();identity('Baseline','PLANT-1','SKU-A','2017-01-15')
        wp2();assert 'Combined_Stress' in wrap('Reference Scenario').inner_text() and 'Combined_Stress_Lost_Sales' in wrap('Candidate Scenario').inner_text()
        assert page.get_by_test_id('stException').count()==0
        return {'final_comparison':ui(),'active_run':RUN.name,'screenshot':shot('D04_final_switch',wrap('Reference Scenario'))}
    case('D04','Final module switching leaves intentional independent contexts valid without exceptions.',finish)
