"""Phase 1 read-only reliability diagnostics on an isolated existing-run UI.

Run shared Python --mode performance/decode; existing Playwright venv --mode browser.
Never calls a planning runner, changes a published artifact, or starts a service.
"""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
PRIMARY = REPO / 'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def protobuf_fields(data):
    offset = 0

    def integer():
        nonlocal offset
        value = shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                return value
            shift += 7
        raise ValueError('Incomplete protobuf integer')

    while offset < len(data):
        tag = integer()
        yield tag >> 3
        wire = tag & 7
        if wire == 0:
            integer()
        elif wire == 1:
            offset += 8
        elif wire == 2:
            length = integer()
            offset += length
        elif wire == 5:
            offset += 4
        else:
            return


def performance(root):
    """Read existing artifacts; time distinct calls, preserving export contract."""
    import tracemalloc
    from unittest.mock import patch

    sys.path.insert(0, str(REPO))
    samples = []
    exported = None
    with patch('src.run_planning.run_csv_planning', side_effect=AssertionError('Planning prohibited')), \
         patch('src.run_planning.run_sequential_planning', side_effect=AssertionError('Planning prohibited')):
        from src.comparison_io import load_comparison_input, comparison_csv_exports
        from src.scenario_comparison import ComparisonInput, ComparisonScope, compare_published_results

        def measured(name, fn, sample):
            tracemalloc.start()
            started = time.perf_counter()
            value = fn()
            duration = time.perf_counter() - started
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            sample[name] = {'seconds': duration, 'traced_current_bytes': current,
                            'traced_peak_bytes': peak, 'tracemalloc_not_process_rss': True}
            return value

        for iteration in range(3):
            sample = {'iteration': iteration + 1, 'timestamp': now()}
            a = measured('load', lambda: load_comparison_input(PRIMARY, 'Baseline'), sample)
            b = ComparisonInput(a.manifest, a.tables, 'Combined_Stress')
            scope = ComparisonScope(tuple(a.manifest['Scope']['Product_IDs']),
                                    tuple(sorted(a.tables['initial_state'].Plant_ID.unique())),
                                    *a.manifest['Scope']['Planning_Horizon'], (3,))
            compared = measured('compute', lambda: compare_published_results(a, b, scope), sample)
            exported = measured('serialize_four_csv', lambda: comparison_csv_exports(compared), sample)
            sample['metric_rows'] = len(compared.metrics)
            sample['comparison_id'] = compared.context['Comparison_ID']
            sample['csv_bytes'] = {kind: len(text.encode('utf-8')) for kind, text in exported.items()}
            samples.append(sample)
    contracts = {}
    for kind, data in exported.items():
        original = REPO / 'tmp/wp2_browser_uat_phase_3/downloads/baseline_p3' / (kind + '.csv')
        actual = data.encode('utf-8')
        contracts[kind] = {'bytes': len(actual), 'sha256': hashlib.sha256(actual).hexdigest(),
                           'historical_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                           'byte_identical_to_historical': actual == original.read_bytes()}
    result = {'status': 'PASS' if all(r['byte_identical_to_historical'] for r in contracts.values()) else 'FAIL',
              'run': str(PRIMARY), 'method': 'Three separate load/compute/serialization measurements; no publishing',
              'samples': samples, 'csv_contracts': contracts,
              'limits': ['Single representative fixture, not load/concurrency benchmark or SLO',
                         'tracemalloc excludes native allocations and is not RSS',
                         'Stage timings include tracemalloc instrumentation overhead',
                         'First iteration may include lazy-import/cold-cache cost',
                         'No export optimization or schema changes performed'],
              'planning_executed': False, 'dependency_changes': False}
    save(root / 'reports/performance_results.json', result)
    print(json.dumps({'performance_status': result['status'], 'samples': len(samples),
                      'csv_bytes': samples[-1]['csv_bytes']}, indent=2), flush=True)


def browser(root, url):
    from playwright.sync_api import sync_playwright

    output = {'run': str(PRIMARY), 'url': url, 'sessions': {}, 'lifecycle': [], 'toolbar': [],
              'started_at': now(), 'historical_d03': {'mouse_success': True,
              'keyboard_success': False, 'chart_restored': True, 'preserved_not_reinterpreted': True}}
    with sync_playwright() as pw:
        for width, height in [(1440, 1100), (1600, 1100)]:
            name = f'ws2_{width}x{height}'
            session = {'viewport': {'width': width, 'height': height}, 'console': [], 'page_errors': [],
                       'failed_requests': [], 'websockets': [], 'actions': [], 'browser_timings': []}
            output['sessions'][name] = session
            state = {'stage': 'setup', 'finished': 0}
            raw = (root / f'logs/{name}_frames.jsonl').open('w')
            context = None
            try:
                context = pw.chromium.launch_persistent_context(str(root / f'profiles/{name}'),
                    headless=True, viewport={'width': width, 'height': height}, accept_downloads=False,
                    downloads_path=str(root / 'downloads'), args=['--disable-dev-shm-usage'])
                context.tracing.start(screenshots=True, snapshots=True, sources=False)
                page = context.pages[0]
                page.set_default_timeout(30000)
                page.on('console', lambda msg: session['console'].append({'time': now(),
                    'monotonic': time.perf_counter(), 'stage': state['stage'], 'type': msg.type,
                    'text': msg.text}) if msg.type in ['warning', 'error'] else None)
                page.on('pageerror', lambda e: session['page_errors'].append({'time': now(), 'stage': state['stage'], 'error': str(e)}))
                page.on('requestfailed', lambda req: session['failed_requests'].append({'time': now(), 'stage': state['stage'], 'url': req.url, 'failure': req.failure}))

                def socket(ws):
                    item = {'url': ws.url, 'received': 0, 'errors': []}
                    session['websockets'].append(item)

                    def received(payload):
                        if isinstance(payload, bytes):
                            item['received'] += 1
                            raw.write(json.dumps({'time': now(), 'stage': state['stage'],
                                'payload': base64.b64encode(payload).decode()}) + '\n')
                            raw.flush()
                            if 6 in set(protobuf_fields(payload)):
                                state['finished'] += 1
                    ws.on('framereceived', received)
                    ws.on('socketerror', lambda e: item['errors'].append(str(e)))
                page.on('websocket', socket)

                def idle():
                    page.wait_for_function("() => document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
                    page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

                def tab(label):
                    widget = page.get_by_role('tab', name=label, exact=True)
                    widget.click()
                    panel = page.locator('[id=' + json.dumps(widget.get_attribute('aria-controls')) + ']')
                    panel.wait_for(state='visible')
                    return panel

                def chart_panel(kind):
                    if kind == 'overview':
                        return tab('Scenario Overview')
                    tab('Planning Risk Summary')
                    return tab('Plant Bottlenecks')

                def act(stage, fn):
                    state['stage'] = stage
                    before = state['finished']
                    started = time.perf_counter()
                    session['actions'].append({'stage': stage, 'time': now(), 'type': 'rerun'})
                    fn()
                    deadline = time.monotonic() + 90
                    while state['finished'] <= before:
                        if time.monotonic() >= deadline:
                            raise TimeoutError('No Streamlit script-finished: ' + stage)
                        page.wait_for_timeout(100)
                    idle()
                    session['browser_timings'].append({'stage': stage,
                        'action_to_script_finished_and_two_animation_frames_seconds': time.perf_counter() - started,
                        'includes_server_compute_network_and_frontend_not_pure_render': True})

                def select(label, value, stage):
                    wrapper = page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label, exact=True))
                    if wrapper.inner_text().split('\n')[-1] == value:
                        session['actions'].append({'stage': stage, 'time': now(), 'type': 'already_selected', 'value': value})
                        return

                    def choose():
                        wrapper.get_by_role('combobox').click()
                        page.get_by_role('option', name=value, exact=True).click()
                    act(stage, choose)

                def screenshot(label, target=None):
                    if target is not None:
                        target.scroll_into_view_if_needed()
                    path = root / f'screenshots/{name}_{label}.png'
                    page.screenshot(path=str(path))
                    return str(path)

                def chart_observation(kind, action):
                    state['stage'] = f'{kind}:{action}'
                    before = len(session['console'])
                    record = {'session': name, 'chart': kind, 'action': action, 'time': now(), 'status': 'BLOCKED'}
                    output['lifecycle'].append(record)
                    try:
                        panel = chart_panel(kind)
                        chart = panel.get_by_test_id('stVegaLiteChart')
                        started = time.perf_counter()
                        chart.locator('canvas,svg').first.wait_for(state='visible')
                        record['visible_wait_seconds'] = time.perf_counter() - started
                        box = chart.bounding_box()
                        assert box and box['width'] > 0 and box['height'] > 0
                        record['bounds'] = box
                        record['screenshot'] = screenshot(kind + '_' + action, chart)
                        assert page.get_by_test_id('stException').count() == 0
                        record['status'] = 'PASS'
                    except Exception as e:
                        record.update(status='FAIL', error=str(e), traceback=traceback.format_exc())
                        record['screenshot'] = screenshot(kind + '_' + action + '_failure')
                    record['warnings_during_observation'] = session['console'][before:]

                def toolbar(kind, direction, method):
                    panel = chart_panel(kind)
                    stage = f'toolbar:{kind}:{direction}:{method}'
                    state['stage'] = stage
                    item = {'session': name, 'chart': kind, 'direction': direction, 'method': method,
                            'viewport': session['viewport'], 'attempted': False, 'status': 'BLOCKED',
                            'time': now(), 'force_click': False, 'preparation': []}
                    output['toolbar'].append(item)
                    chart = panel.get_by_test_id('stVegaLiteChart')

                    def mode():
                        return 'data' if panel.get_by_role('button', name='Show chart', exact=True).is_visible() else 'chart'

                    def hover_chart():
                        if chart.is_visible():
                            chart.scroll_into_view_if_needed()
                            chart.hover()

                    def keyboard_toggle(label):
                        button = panel.get_by_role('button', name=label, exact=True)
                        button.focus()
                        button.press('Enter')
                    try:
                        required = 'chart' if direction == 'show_data' else 'data'
                        if mode() != required:
                            label = 'Show data' if required == 'data' else 'Show chart'
                            hover_chart()
                            keyboard_toggle(label)
                            want = 'Show chart' if required == 'data' else 'Show data'
                            if required == 'data':
                                panel.get_by_role('button', name=want, exact=True).wait_for(state='visible')
                            else:
                                chart.locator('canvas,svg').first.wait_for(state='visible')
                            item['preparation'].append({'action': label, 'method': 'keyboard', 'not_test_verdict': True})
                        hover_chart()
                        label = 'Show data' if direction == 'show_data' else 'Show chart'
                        button = panel.get_by_role('button', name=label, exact=True)
                        button.wait_for(state='visible')
                        item['locator'] = f'active {kind} panel button[name={label!r}]'
                        item['initial_state'] = mode()
                        box = button.bounding_box()
                        if box:
                            item['hit_test'] = page.evaluate("b => {const e=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e?{tag:e.tagName,html:e.outerHTML.slice(0,1000)}:null}", box)
                        item['attempted'] = True
                        started = time.perf_counter()
                        if method == 'mouse':
                            button.click(timeout=5000)
                        else:
                            button.focus()
                            item['focus_before'] = page.evaluate('() => ({tag:document.activeElement?.tagName,text:document.activeElement?.getAttribute("aria-label")||document.activeElement?.textContent})')
                            button.press('Enter')
                        expected = 'data' if direction == 'show_data' else 'chart'
                        if expected == 'data':
                            panel.get_by_role('button', name='Show chart', exact=True).wait_for(state='visible', timeout=10000)
                        else:
                            chart.locator('canvas,svg').first.wait_for(state='visible', timeout=10000)
                        item['elapsed_seconds'] = time.perf_counter() - started
                        item['final_state'] = mode()
                        assert item['final_state'] == expected
                        item['focus_after'] = page.evaluate('() => ({tag:document.activeElement?.tagName,text:document.activeElement?.getAttribute("aria-label")||document.activeElement?.textContent})')
                        item['status'] = 'PASS'
                        target = panel.get_by_role('button', name='Show chart', exact=True) if expected == 'data' else chart
                        item['screenshot'] = screenshot(kind + '_' + direction + '_' + method, target)
                    except Exception as e:
                        item.update(status='FAIL' if item['attempted'] else 'BLOCKED', error=str(e), traceback=traceback.format_exc())
                        item['final_state'] = mode()
                        item['screenshot'] = screenshot(kind + '_' + direction + '_' + method + '_failure')
                    save(root / 'reports/toolbar_results.json', {'cases': output['toolbar'], 'historical_d03': output['historical_d03']})

                started = time.perf_counter()
                page.goto(url, wait_until='domcontentloaded')
                page.get_by_role('heading', name='Scenario Planning Decision Support', exact=True).wait_for()
                idle()
                session['browser_timings'].append({'stage': 'homepage', 'seconds': time.perf_counter() - started})

                def load():
                    field = page.get_by_label('Published sequential run folder', exact=True)
                    field.fill(str(PRIMARY))
                    field.press('Enter')
                act('load_primary', load)
                assert PRIMARY.name in page.get_by_text('Active results:', exact=False).first.inner_text()
                # Measure actual comparison UI separately from pure Python stages.
                tab('Scenario Trade-off Analysis')
                select('Reference Scenario', 'Baseline', 'comparison_reference')
                tab('Scenario Trade-off Analysis')
                select('Candidate Scenario', 'Combined_Stress', 'comparison_candidate')
                tab('Scenario Trade-off Analysis')
                multi = page.get_by_test_id('stMultiSelect').filter(has=page.get_by_text('Reference priorities (fixed cohort)', exact=True))

                def priority():
                    multi.get_by_role('combobox').click()
                    page.get_by_role('option', name='Priority 3', exact=True).click()
                act('comparison_priority3', priority)
                page.keyboard.press('Escape')
                tab('Scenario Trade-off Analysis')
                title = page.get_by_text('Trade-off summary — ALL / SELECTED / COMPLEMENT', exact=True)
                frame = title.locator('xpath=following::*[@data-testid="stDataFrame"][1]')
                started = time.perf_counter()
                frame.locator('canvas').first.wait_for(state='visible')
                geometry = frame.evaluate("""el => [...el.querySelectorAll('*')]
                    .filter(x => x.scrollWidth > x.clientWidth + 10 && /auto|scroll/.test(getComputedStyle(x).overflowX))
                    .map(x => ({className:x.className,clientWidth:x.clientWidth,scrollWidth:x.scrollWidth,left:x.scrollLeft}))""")
                session['comparison_table'] = {'post_script_finished_canvas_visible_wait_seconds': time.perf_counter() - started,
                    'scroll_geometry': geometry, 'horizontal_scroll_required': bool(geometry),
                    'screenshot': screenshot('comparison_summary_identifiers', frame),
                    'timing_limit': 'This DOM visibility wait is not end-to-end pure render timing; rerun totals above include server work.'}
                frame.evaluate("""el => [...el.querySelectorAll('*')]
                    .filter(x => x.scrollWidth > x.clientWidth + 10 && /auto|scroll/.test(getComputedStyle(x).overflowX))
                    .forEach(x => x.scrollLeft=(x.scrollWidth-x.clientWidth)*.42)""")
                page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
                session['comparison_table']['scrolled_screenshot'] = screenshot('comparison_summary_values', frame)
                for kind in ['overview', 'plant']:
                    chart_observation(kind, 'initial')
                select('Sequential scenario', 'Combined_Stress', 'scenario_combined')
                for kind in ['overview', 'plant']:
                    chart_observation(kind, 'scenario_change')
                chart_panel('plant')
                plant_control = page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Plant drill-down', exact=True))
                next_plant = 'PLANT-1' if plant_control.inner_text().split('\n')[-1] == 'PLANT-2' else 'PLANT-2'
                select('Plant drill-down', next_plant, 'plant_change')
                chart_observation('plant', 'plant_change')
                select('Sequential scenario', 'Baseline', 'scenario_baseline_rerun')
                for kind in ['overview', 'plant']:
                    chart_observation(kind, 'rerun')
                    for direction, method in [('show_data', 'mouse'), ('show_chart', 'mouse'),
                                              ('show_data', 'keyboard'), ('show_chart', 'keyboard')]:
                        toolbar(kind, direction, method)
                    chart_observation(kind, 'after_toggles')
            except Exception as e:
                session['driver_error'] = {'error': str(e), 'traceback': traceback.format_exc()}
                if context:
                    try:
                        page.screenshot(path=str(root / f'screenshots/{name}_driver_failure.png'))
                    except Exception:
                        pass
            finally:
                raw.close()
                if context:
                    context.tracing.stop(path=str(root / f'traces/{name}.zip'))
                    context.close()
                save(root / 'reports/reliability_results.json', output)
                print('WS2_SESSION', name, 'toolbar', dict(collections.Counter(x['status'] for x in output['toolbar'] if x['session'] == name)), flush=True)
    output['finished_at'] = now()
    output['limits'] = ['No instrumentation inside third-party Vega embed; warning/data ordering is observational, not exact causal attribution',
                       'Browser completion time includes server compute/network/rerender; pure chart visible-wait is already-warm DOM timing',
                       'Viewport-specific observations do not generalize to all devices',
                       'Historical D03 true/false/true remains unchanged']
    save(root / 'reports/reliability_results.json', output)
    save(root / 'reports/toolbar_results.json', {'cases': output['toolbar'],
        'counts': dict(collections.Counter(x['status'] for x in output['toolbar'])),
        'historical_d03': output['historical_d03']})


def decode(root):
    import pandas as pd
    import pyarrow as pa
    from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

    charts = []
    for path in sorted((root / 'logs').glob('ws2_*_frames.jsonl')):
        cache = {}
        for line in path.open():
            event = json.loads(line)
            blob = base64.b64decode(event['payload'])
            m = ForwardMsg()
            m.ParseFromString(blob)
            if m.hash:
                cache[m.hash] = blob
            if m.HasField('ref_hash'):
                if m.ref_hash not in cache:
                    continue
                m.ParseFromString(cache[m.ref_hash])
            if not m.HasField('delta') or not m.delta.HasField('new_element'):
                continue
            e = m.delta.new_element
            if not e.HasField('vega_lite_chart'):
                continue
            chart = e.vega_lite_chart
            name = 'plant' if 'Capacity_Utilization' in chart.spec else 'overview'
            entry = {'session': path.stem, 'time': event['time'], 'stage': event['stage'],
                     'name': name, 'spec': json.loads(chart.spec), 'datasets': []}
            blobs = [('direct', chart.data.data)] + [(d.name, d.data.data) for d in chart.datasets]
            for dataset_name, data in blobs:
                if not data:
                    continue
                f = pa.ipc.open_stream(data).read_all().to_pandas()
                numeric = {}
                for c in f:
                    if pd.api.types.is_numeric_dtype(f[c]):
                        values = [float(x) for x in f[c].dropna()]
                        numeric[c] = {'nulls': int(f[c].isna().sum()), 'all_finite_nonnull': all(math.isfinite(x) for x in values),
                                      'values': values}
                entry['datasets'].append({'name': dataset_name, 'rows': len(f), 'columns': list(f.columns),
                                          'records': f.reset_index().to_dict('records'), 'numeric': numeric})
            charts.append(entry)
    native = list(csv.DictReader((PRIMARY / 'performance_result.csv').open()))
    pools = list(csv.DictReader((PRIMARY / 'capacity_pools.csv').open()))
    actual_checked = 0
    errors = []
    for chart in charts:
        for dataset in chart['datasets']:
            try:
                assert dataset['rows'] > 0
                assert all(v['all_finite_nonnull'] and v['nulls'] == 0 for v in dataset['numeric'].values())
                records = dataset['records']
                if chart['name'] == 'overview':
                    # A chart payload does not carry scenario identity, so test
                    # exact whole-series alternatives against both UI-selected scenarios.
                    matched = []
                    for scenario in ['Baseline', 'Combined_Stress']:
                        expected = {(r['Order_Date'][:10], metric): float(r[metric]) for r in native
                            if r['Scenario'] == scenario and r['Aggregation_Level'] == 'Scenario × Week'
                            for metric in ['Ending_Inventory', 'Ending_Backlog', 'Lost_Sales_Qty']}
                        if len(records) == len(expected) and all(abs(float(row['value -- streamlit-generated']) - expected[(str(row['Order_Date'])[:10], row['color -- streamlit-generated'])]) < 1e-8 for row in records):
                            matched.append(scenario)
                    assert matched, 'Overview series mismatches all selected published scenarios'
                    dataset['matching_native_scenarios'] = matched
                else:
                    matched = []
                    for scenario in ['Baseline', 'Combined_Stress']:
                        for plant in ['PLANT-1', 'PLANT-2']:
                            expected = {r['Order_Date'][:10]: float(r['Allocated_Workload']) / float(r['Available_Workload_Capacity'])
                                for r in pools if r['Scenario'] == scenario and r['Plant_ID'] == plant}
                            if len(records) == len(expected) and all(abs(float(row['Capacity_Utilization']) - expected[str(row['Order_Date'])[:10]]) < 1e-8 for row in records):
                                matched.append({'scenario': scenario, 'plant': plant})
                    assert matched, 'Plant series mismatches native capacity utilization'
                    dataset['matching_native_scopes'] = matched
                actual_checked += 1
            except Exception as e:
                errors.append({'stage': chart['stage'], 'session': chart['session'], 'chart': chart['name'],
                               'error': str(e), 'traceback': traceback.format_exc()})
    validation = {'status': 'PASS' if charts and actual_checked and not errors else 'FAIL',
                  'chart_payload_occurrences': len(charts), 'datasets_checked': actual_checked,
                  'errors': errors, 'charts': charts,
                  'method': 'Actual browser-received Arrow chart data compared to native published CSV using independent division/sums; no planning/KPI engine oracle'}
    save(root / 'reports/ws2_chart_payload_validation.json', validation)
    reliability = json.loads((root / 'reports/reliability_results.json').read_text())
    reliability['chart_payload_validation'] = {k: v for k, v in validation.items() if k != 'charts'}
    reliability['warning_counts'] = {name: sum(x['type'] == 'warning' for x in session['console']) for name, session in reliability['sessions'].items()}
    reliability['console_error_count'] = sum(x['type'] == 'error' for s in reliability['sessions'].values() for x in s['console'])
    reliability['page_error_count'] = sum(len(s['page_errors']) for s in reliability['sessions'].values())
    reliability['failed_request_count'] = sum(len(s['failed_requests']) for s in reliability['sessions'].values())
    save(root / 'reports/reliability_results.json', reliability)
    performance_path = root / 'reports/performance_results.json'
    if performance_path.is_file():
        measured = json.loads(performance_path.read_text())
        measured['browser_measurements'] = {name: {'timings': s['browser_timings'],
            'comparison_table': s.get('comparison_table')} for name, s in reliability['sessions'].items()}
        measured['browser_timing_caveat'] = 'Action-to-script-finished includes server/network/frontend; post-finished DOM wait is not an isolated full rendering benchmark.'
        save(performance_path, measured)
    print(json.dumps({k: v for k, v in validation.items() if k != 'charts'}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=['performance', 'browser', 'decode'], required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8503')
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.is_relative_to(REPO / 'tmp/phase_1_reliability') and root.is_dir()
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(root / 'temp'), XDG_CACHE_HOME=str(root / 'cache'),
                      PLAYWRIGHT_BROWSERS_PATH=str(REPO / 'tmp/wp2_browser_uat_phase_a/browsers'))
    csv.field_size_limit(64 * 1024 * 1024)
    {'performance': performance, 'browser': lambda r: browser(r, args.url), 'decode': decode}[args.mode](root)


if __name__ == '__main__':
    main()
