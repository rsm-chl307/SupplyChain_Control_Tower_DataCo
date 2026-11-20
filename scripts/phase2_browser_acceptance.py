"""Read-only existing-service UI acceptance; no planning/upload/publishing actions."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import traceback

REPO = Path(__file__).resolve().parents[1]
PRIMARY = REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'
SYNTHETIC = REPO/'tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--url',default='http://127.0.0.1:8501');parser.add_argument('--supplement',action='store_true');parser.add_argument('--state-only',action='store_true')
    args=parser.parse_args();root=Path(args.root).resolve()
    from playwright.sync_api import sync_playwright, expect
    csv.field_size_limit(64*1024*1024)
    results={'cases':[],'console':[],'page_errors':[],'failed_requests':[],'websockets':[],'downloads':[],'url':args.url}
    def record(id,fn):
        if args.state_only and id not in {'B01-homepage','B02-pair','B04-locale-zh','B15-context-reject','B12-telemetry'}:return
        if args.supplement and id not in {'B01-homepage','B02-pair','B04-locale-zh','B07-candidate-reset','B09-policy','B11-viewports','B12-telemetry'}:return
        try:
            actual=fn();results['cases'].append({'id':id,'status':'PASS','actual':actual})
        except Exception as exc:
            file=root/'screenshots'/f'{id}_FAIL.png'
            try:page.screenshot(path=str(file))
            except Exception:pass
            results['cases'].append({'id':id,'status':'FAIL','error':str(exc),'traceback':traceback.format_exc(),'screenshot':str(file)})
        (root/'reports/browser_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=str(REPO/'tmp/wp2_browser_uat_phase_a/browsers/chromium_headless_shell-1255/chrome-headless-shell-linux64/chrome-headless-shell'),args=['--disable-dev-shm-usage'])
        context=browser.new_context(viewport={'width':1600,'height':1100},accept_downloads=True)
        context.tracing.start(screenshots=True,snapshots=True,sources=False)
        page=context.new_page();page.set_default_timeout(30000)
        page.on('console',lambda m:results['console'].append({'type':m.type,'text':m.text}) if m.type in ('error','warning') else None)
        page.on('pageerror',lambda e:results['page_errors'].append(str(e)))
        page.on('requestfailed',lambda r:results['failed_requests'].append({'url':r.url,'failure':r.failure}))
        def ws(socket):
            entry={'url':socket.url,'received':0,'errors':[]};results['websockets'].append(entry)
            socket.on('framereceived',lambda payload:entry.update(received=entry['received']+1))
            socket.on('socketerror',lambda error:entry['errors'].append(str(error)))
        page.on('websocket',ws)
        def idle():
            page.wait_for_function("() => document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'")
            page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
            expect(page.get_by_test_id('stException')).to_have_count(0)
        def shot(id):
            file=root/'screenshots'/f'{id}.png';page.screenshot(path=str(file));return str(file)
        def select(label,value):
            if label in ['Reference Scenario','Candidate Scenario','參考情境','候選情境','待調查的比較產品']:
                title='情境取捨分析' if page.get_by_role('tab',name='情境取捨分析',exact=True).count() else 'Scenario Trade-off Analysis'
                page.get_by_role('tab',name=title,exact=True).click();idle()
            box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
            box.click();page.get_by_role('option',name=value,exact=True).click();idle()
        def value(label):
            return page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).inner_text()
        def tab(name):page.get_by_role('tab',name=name,exact=True).click();idle()
        def run(path,label='Published sequential run folder'):
            field=page.get_by_label(label,exact=True);field.fill(str(path));field.press('Enter');idle()
            expect(page.get_by_text(path.name,exact=False).first).to_be_visible()
        def download(label,name):
            with page.expect_download(timeout=120000) as event:page.get_by_role('button',name=label,exact=True).click()
            d=event.value;assert d.failure() is None
            file=root/'downloads'/name;d.save_as(str(file));rows=list(csv.DictReader(file.open()))
            result={'file':str(file),'filename':d.suggested_filename,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'rows':len(rows),'columns':list(rows[0]) if rows else []}
            results['downloads'].append(result);return result
        def homepage():
            page.goto(args.url);idle();expect(page.get_by_text('Scenario Planning Decision Support',exact=True)).to_be_visible()
            return {'screenshot':shot('homepage'),'websockets':results['websockets']}
        record('B01-homepage',homepage)
        def load_pair():
            # Choose existing JSON mode so language can be changed in sidebar.
            page.get_by_text('Use existing JSON configuration',exact=True).click();idle()
            run(PRIMARY);tab('Scenario Trade-off Analysis')
            assert 'Select Reference explicitly' in value('Reference Scenario')
            select('Reference Scenario','Baseline');select('Candidate Scenario','Combined_Stress')
            box=page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)',exact=True)).get_by_role('combobox')
            box.click();page.get_by_role('option',name='Priority 3',exact=True).click();page.keyboard.press('Escape');idle()
            return {'screenshot':shot('pair_en'),'Run_ID':PRIMARY.name}
        record('B02-pair',load_pair)
        downloads={}
        def exports_en():
            for kind,label in [('metrics','Download Comparison CSV'),('cohort_membership','Download Comparison Cohort'),('evidence_refs','Download Comparison Evidence References'),('context','Download Comparison Context')]:downloads['en_'+kind]=download(label,'en_'+kind+'.csv')
            return {'four_downloads':True}
        record('B03-exports-en',exports_en)
        def zh():
            select('Language / 語言','繁體中文');tab('情境取捨分析')
            assert 'Baseline' in value('參考情境') and 'Combined_Stress' in value('候選情境')
            expect(page.get_by_text('選定的參考優先順序：3',exact=False)).to_be_visible()
            return {'screenshot':shot('pair_zh'),'state_retained':True}
        record('B04-locale-zh',zh)
        def exports_zh():
            for kind,label in [('metrics','下載比較 CSV'),('cohort_membership','下載比較群組'),('evidence_refs','下載比較佐證參照'),('context','下載比較內容')]:
                other=download(label,'zh_'+kind+'.csv');assert other['sha256']==downloads['en_'+kind]['sha256'];assert other['filename']==downloads['en_'+kind]['filename']
            return {'four_locale_invariant_downloads':True}
        record('B05-exports-zh',exports_zh)
        def handoff():
            select('待調查的比較產品','SKU-A');page.get_by_role('button',name='在 WP1 調查候選情境',exact=True).click();idle()
            tab('規劃風險摘要');tab('根因調查')
            assert 'SKU-A' in value('調查產品');assert 'Combined_Stress' in value('全域序列情境')
            page.get_by_text('佐證資料：selected_week',exact=True).click()
            path=download('下載 selected_week 調查佐證','wp1_zh_selected.csv')
            select('調查路徑','工廠 → 週 → 產品')
            tab('情境取捨分析');assert 'Baseline' in value('參考情境')
            return {'screenshot':shot('wp1_zh'),'download':path}
        record('B06-wp1-handoff',handoff)
        def reset():
            select('參考情境','Combined_Stress')
            assert 'Combined_Stress' not in value('候選情境')
            select('候選情境','Baseline')
            if args.supplement:download('下載比較 CSV','reverse_metrics.csv')
            return {'screenshot':shot('candidate_reset'),'manual_reselection':True}
        record('B07-candidate-reset',reset)
        def run_roundtrip():
            for path in [SYNTHETIC,PRIMARY]:
                run(path,'已發布序列規劃資料夾');tab('情境取捨分析')
                assert '請明確選擇參考情境' in value('參考情境');assert '請明確選擇候選情境' in value('候選情境')
            return {'screenshot':shot('run_roundtrip')}
        record('B08-run-roundtrip',run_roundtrip)
        def policy():
            select('參考情境','Combined_Stress');select('候選情境','Combined_Stress_Lost_Sales')
            expect(page.get_by_text('POLICY_CONTRAST — 僅供描述',exact=False)).to_be_visible()
            if args.supplement:download('下載比較 CSV','policy_metrics.csv')
            return {'screenshot':shot('policy_zh')}
        record('B09-policy',policy)
        def pending():
            page.get_by_text('上傳 CSV 資料',exact=True).click();idle()
            field=page.get_by_label('需求增加情境（%）',exact=True);field.fill('17')
            select('Language / 語言','English')
            page.get_by_role('button',name='套用語言並保留表單輸入',exact=True).click();idle()
            expect(page.get_by_label('Demand surge scenario (%)',exact=True)).to_have_value('17.00')
            assert page.get_by_text('Data readiness:',exact=False).count()==0
            return {'screenshot':shot('pending_form_en'),'pending_value':page.get_by_label('Demand surge scenario (%)',exact=True).input_value(),'no_validation':True}
        record('B10-pending-form',pending)
        def viewports():
            shots=[]
            if args.supplement:
                download('下載 KPI 結果','published_performance.csv')
            for width in [1440,1600]:
                page.set_viewport_size({'width':width,'height':1100});idle();shots.append(shot('viewport_'+str(width)))
            if args.supplement:
                select('規劃模型','歷史獨立週')
                for name in ['情境概觀','情境比較','產能分配明細']:tab(name)
                shots.append(shot('legacy_zh'))
                select('Language / 語言','English')
                for name in ['Scenario Overview','Scenario Comparison','Capacity Allocation Detail']:tab(name)
                shots.append(shot('legacy_en'))
            return {'screenshots':shots}
        record('B11-viewports',viewports)
        def context_reject():
            select('全域序列情境','Demand_Surge');tab('情境取捨分析')
            assert 'Baseline' in value('參考情境') and 'Combined_Stress' in value('候選情境')
            a=shot('global_pair_independent')
            reject=REPO/'tmp/planning_source_runs/sequential_20261117T124401_d4d42e5adb4f'
            field=page.get_by_label('已發布序列規劃資料夾',exact=True);field.fill(str(reject));field.press('Enter');idle()
            expect(page.get_by_text('sequential run is incomplete, failed or unpublished',exact=False)).to_be_visible()
            assert page.get_by_role('tab',name='情境取捨分析',exact=True).count()==0
            assert page.get_by_role('button',name='下載比較 CSV',exact=True).count()==0
            return {'screenshots':[a,shot('rejected_existing_run')],'same_independent_pair':True,'controlled_rejection':True}
        if args.state_only:record('B15-context-reject',context_reject)
        record('B12-telemetry',lambda: {'page_errors':results['page_errors'],'failed_requests':results['failed_requests']} if not results['page_errors'] and not results['failed_requests'] else (_ for _ in ()).throw(AssertionError('Browser telemetry error')))
        context.tracing.stop(path=str(root/'traces/browser.zip'));context.close();browser.close()
    results['counts']={status:sum(c['status']==status for c in results['cases']) for status in ['PASS','FAIL']}
    (root/'reports/browser_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results['counts']));return int(bool(results['counts']['FAIL']))


if __name__=='__main__':raise SystemExit(main())
