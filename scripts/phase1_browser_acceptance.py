"""Phase 3 real-browser integration validation; no product changes."""
from pathlib import Path
import base64
import csv
from decimal import Decimal
import hashlib
import json
import os
import sys
import time
import traceback

ROOT = Path(os.environ['P1_EVIDENCE_ROOT']).resolve()
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'tmp/wp2_browser_uat_phase_2'))
import browser_phase2 as previous
os.environ.update(TMPDIR=str(ROOT/'temp'), XDG_CACHE_HOME=str(ROOT/'cache'), PYTHONDONTWRITEBYTECODE='1')
csv.field_size_limit(64 * 1024 * 1024)
RUN = previous.RUN
URL = os.environ.get('P1_BROWSER_URL','http://127.0.0.1:8503')
result = {'cases': {}, 'console': [], 'page_errors': [], 'failed_requests': [], 'websockets': [], 'downloads': {}}
stage = 'setup'
finished = 0


def main():
    global stage, finished
    from playwright.sync_api import sync_playwright
    with (ROOT/'logs/browser_frames.jsonl').open('w') as raw, sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(str(ROOT/'profiles/integration_final'), headless=True,
            viewport={'width':1600,'height':1100},accept_downloads=True,
            downloads_path=str(ROOT/'downloads'),args=['--disable-dev-shm-usage'])
        context.tracing.start(screenshots=True,snapshots=True,sources=False)
        page=context.pages[0];page.set_default_timeout(45000)
        page.on('console', lambda m: result['console'].append({'type':m.type,'text':m.text,'stage':stage}) if m.type in ['error','warning'] else None)
        page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
        page.on('requestfailed',lambda r:result['failed_requests'].append({'url':r.url,'failure':r.failure}))
        def socket(ws):
            record={'url':ws.url,'received':0,'errors':[]};result['websockets'].append(record)
            def receive(payload):
                global finished
                if isinstance(payload,bytes):
                    record['received']+=1
                    raw.write(json.dumps({'stage':stage,'payload':base64.b64encode(payload).decode()})+'\n');raw.flush()
                    if 6 in set(previous.fields(payload)):finished+=1
            ws.on('framereceived',receive);ws.on('socketerror',lambda e:record['errors'].append(str(e)))
        page.on('websocket',socket)
        def idle():
            page.wait_for_function("() => document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        def wp2():page.get_by_role('tab',name='Scenario Trade-off Analysis',exact=True).click()
        def act(fn):
            before=finished;fn();deadline=time.monotonic()+90
            while finished<=before:
                if time.monotonic()>deadline:raise TimeoutError('Streamlit completion: '+stage)
                page.wait_for_timeout(100)
            idle()
            if page.get_by_role('tab',name='Scenario Trade-off Analysis',exact=True).count():wp2()
        def wrap(label):return page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True))
        def select(label,value):
            current=wrap(label).inner_text().split('\n')[-1]
            if isinstance(value,str) and current==value:return
            def fn():wrap(label).get_by_role('combobox').click();page.get_by_role('option',name=value,exact=isinstance(value,str)).first.click()
            act(fn)
        def shot(name, target=None):
            if target is not None: target.scroll_into_view_if_needed()
            p=ROOT/'screenshots'/f'{name}.png';page.screenshot(path=str(p));return str(p)
        def options():
            wrap('Candidate Scenario').get_by_role('combobox').click()
            values=page.get_by_role('option').all_inner_texts();page.keyboard.press('Escape');return values
        def ui():return {'reference':wrap('Reference Scenario').inner_text(),'candidate':wrap('Candidate Scenario').inner_text(),
            'candidate_aria':wrap('Candidate Scenario').aria_snapshot(),'script_state':page.get_by_test_id('stApp').get_attribute('data-test-script-state')}
        labels={'metrics':'Download Comparison CSV','cohort_membership':'Download Comparison Cohort',
            'evidence_refs':'Download Comparison Evidence References','context':'Download Comparison Context'}
        def download(tag,kind):
            idle();wp2()
            with page.expect_download(timeout=120000) as event:page.get_by_role('button',name=labels[kind],exact=True).click()
            file=event.value;assert file.failure() is None
            folder=ROOT/'downloads'/tag;folder.mkdir(exist_ok=True)
            path=folder/(kind+'.csv');file.save_as(str(path))
            with path.open(newline='') as f:rows=list(csv.DictReader(f))
            assert rows
            record={'path':str(path),'bytes':path.stat().st_size,'rows':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'suggested_filename':file.suggested_filename,'captured_download_event':True,'parse':'PASS'}
            result['downloads'].setdefault(tag,{})[kind]=record
            idle();wp2();return rows
        def case(id,expected,fn):
            global stage
            stage=id;r={'expected':expected,'status':'BLOCKED'};result['cases'][id]=r
            try:
                r['actual']=fn();assert page.get_by_test_id('stException').count()==0
                r['status']='PASS'
            except Exception as e:
                r.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
                try:r['failure_screenshot']=shot(id+'_failure')
                except Exception:pass
            (ROOT/'browser_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
        try:
            page.goto(URL,wait_until='domcontentloaded')
            page.get_by_role('heading',name='Scenario Planning Decision Support',exact=True).wait_for();idle()
            def load():
                field=page.get_by_label('Published sequential run folder',exact=True);field.fill(str(RUN));field.press('Enter')
            act(load)
            if os.environ.get('P1_BROWSER_MODE')=='fixtures':
                from phase1_fixture_steps import run_steps
            elif os.environ.get('P1_BROWSER_MODE')=='state_only':
                from phase1_state_steps import run_steps
            else:
                from phase1_browser_steps import run_steps
            run_steps(dict(locals(), result=result, ROOT=ROOT))
        except Exception as e:result['driver_error']={'error':str(e),'traceback':traceback.format_exc()}
        finally:
            context.tracing.stop(path=str(ROOT/'traces/phase1_integration.zip'));context.close()
    (ROOT/'browser_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps({'cases':{k:v['status'] for k,v in result['cases'].items()},'driver_error':result.get('driver_error'),
        'console_errors':sum(x['type']=='error' for x in result['console']),'page_errors':result['page_errors'],'failed_requests':result['failed_requests']},indent=2))


if __name__=='__main__':main()
