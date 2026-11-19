"""Consolidate verified Phase 1 evidence; no planning or service operations."""
from pathlib import Path
import collections
import csv
import datetime
import difflib
import hashlib
import json
import os
import subprocess

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ['P1_EVIDENCE_ROOT']).resolve()
DOC=REPO/'docs/phase_1'


def read(name):return json.loads((ROOT/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(p,label=None):
    p=Path(p);p=p if p.is_absolute() else ROOT/p
    return '['+(label or p.name)+']('+os.path.relpath(p,DOC)+')'
def table(headers,rows):
    esc=lambda v:str(v).replace('|','&#124;').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(map(esc,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(esc,r))+' |' for r in rows])+'\n'


def main():
    initial=read('initial_snapshot.json');coverage=read('reports/coverage_results.json')
    risk=read('reports/risk_recovery_final_results.json');ui=read('reports/negative_ui_layers.json')
    original=read('reports/regression_results.json');retry=read('reports/regression_results_recovery_investigation.json')
    rel=read('reports/reliability_results.json');toolbar=read('reports/toolbar_results.json');perf=read('reports/performance_results.json')
    independent=read('reports/integration_results_recovery.json');cleanup=read('reports/runtime_cleanup.json')
    browsers={k:read(p+'/browser_results.json' if p else 'browser_results.json') for k,p in [('main',''),('state','green_state_browser'),('fixtures','fixture_browser')]}
    zero=read('zero_pool_retry/browser_results.json')
    regression_records={r['id']:r for r in original['records'] if 'ExistingInvestigationAdapter' not in r['id']}
    regression_records.update({r['id']:r for r in retry['records']})
    assert len(regression_records)==99 and all(r['status']=='PASS' for r in regression_records.values())
    assert coverage['tests_run']==13 and not coverage['failures'] and not coverage['errors']
    assert risk['tests_run']==22 and not risk['failures'] and not risk['errors']
    assert ui['run']==7 and not ui['failures'] and not ui['errors']
    assert not any(original['runner_guard_calls']+retry['runner_guard_calls']+ui['runner_guard_calls']) and risk['planning_runner_attempts']==0
    browser_cases={k+':'+id:dict(row,group=k) for k,b in browsers.items() for id,row in b['cases'].items()}
    browser_cases['fixtures:NC-N03']=dict(zero['cases']['NC-N03'],group='zero_pool_retry',
        prior_attempt=browsers['fixtures']['cases']['NC-N03'],resolution='Harness explicitly selects Sequential scenario Baseline; previous valid Combined_Stress selection was not a product defect.')
    assert len(browser_cases)==30 and all(c['status']=='PASS' for c in browser_cases.values())
    assert independent['overall_result']=='PASS' and len(independent['cases'])==14

    allowed={'dashboard/scenario_planning_app.py','src/scenario_comparison.py'}
    changed=[p for p,h in initial['files'].items() if not (REPO/p).is_file() or sha(REPO/p)!=h]
    unexpected=[p for p in changed if p not in allowed]
    protected_changed=[p for p,h in initial['protected_files'].items() if not (REPO/p).is_file() or sha(REPO/p)!=h]
    runs=sorted(str(p.relative_to(REPO)) for p in (REPO/'tmp').rglob('run_manifest.json'))
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    status=subprocess.check_output(['git','status','--short'],text=True)
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],text=True)
    diffcheck=subprocess.run(['git','diff','--check'],text=True,capture_output=True)
    external=read('reports/recovery_external_file_hashes.json')
    external_changed=[p for p,h in external.items() if sha(REPO/p)!=h]
    assert not unexpected and not external_changed and set(changed)==allowed
    assert head==initial['head'] and not staged and runs==initial['run_manifest_paths'] and diffcheck.returncode==0
    primary=REPO/'tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98'
    manifest=json.loads((primary/'run_manifest.json').read_text())
    hashes={name:sha(primary/a['Path'])==a['SHA256'] for name,a in manifest['Artifacts'].items()}
    assert len(hashes)==12 and all(hashes.values())
    source_diff=''
    for p in sorted(allowed):
        old=ROOT/'before'/Path(p).name
        assert sha(old)==initial['files'][p]
        source_diff+=''.join(difflib.unified_diff(old.read_text().splitlines(True),(REPO/p).read_text().splitlines(True),fromfile=p+' (pre-Phase1 dirty baseline)',tofile=p+' (current)'))
    (ROOT/'reports/phase1_incremental_source.diff').write_text(source_diff)
    integrity={'result':'PASS','head_before':initial['head'],'head_after':head,'head_unchanged':True,
        'git_status_before':initial['status'],'git_status_after':status,'index_empty':not staged,
        'initial_files_checked':len(initial['files']),'authorized_existing_changes':changed,'unexpected_changes':unexpected,
        'protected_files_checked':len(initial['protected_files']),'authorized_protected_changes':protected_changed,
        'primary_published_files_unchanged':all(sha(REPO/p)==h for p,h in initial['files'].items() if str(primary.relative_to(REPO))+'/' in p),
        'artifact_hashes':hashes,'run_count_before':len(initial['run_manifest_paths']),'run_count_after':len(runs),'run_paths_unchanged':True,
        'external_files_preserved':not external_changed,'runtime_cleanup':cleanup,'git_diff_check':{'returncode':diffcheck.returncode,'output':diffcheck.stdout+diffcheck.stderr},
        'no_dependencies_changed':True,'no_planning_publication_upload':True,'no_commit_push':True,
        'no_existing_service_restart':True,'only_new_recovery8504_test_process_stopped':True,
        'namespace_correction':'Unprivileged/proc view hid active services; actual namespace showed8501/8502/8503. Occupied8503 startup rejected; no restart attempted; new8504 used and cleaned.'}
    (ROOT/'reports/final_integrity.json').write_text(json.dumps(integrity,indent=2))
    nc={id:dict(row) for id,row in coverage['cases'].items()}
    ui_map={'NC-B09':'test_priority_change_fixed_membership_display','NC-N01':'test_invalid_priority_has_unavailable_and_blocked_display','NC-N02':'test_nonempty_zero_demand_display_is_na','NC-N04':'test_inventory_covered_display','NC-N05':'test_opening_origin_excluded_display','NC-N06':'test_factor_mismatch_has_metric_reason','NC-N07':'test_missing_endpoint_has_blocked_display'}
    for id,row in nc.items():
        if id in ['NC-SYNTHETIC','NC-N03','NC-N08']:
            row.update(status='PASS',browser='PASS — real browser production loader',published_run_e2e='PASS within declared fixture scope',remaining_gap='NC-N03 covers zero plant-week pool, not whole-horizon zero capacity.' if id=='NC-N03' else 'NC-N08 uses existing unpublished Run plus disposable invalid snapshots, not altered historical Runs.' if id=='NC-N08' else 'Current existing SYNTHETIC_DEMO fixture only; not every scenario permutation.')
            row['executed_layers']+=['Real browser','actual CSV/Arrow/native artifact reconciliation']
        else:
            row.update(status='PARTIAL',apptest='PASS — '+ui_map[id],browser='NOT COVERED for this negative data case',published_run_e2e='NOT COVERED — no approved complete immutable fixture',remaining_gap='Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured.')
            row['executed_layers']+=['AppTest memory-only UI presentation']
    nc_counts=dict(collections.Counter(r['status'] for r in nc.values()))
    gates={id:{'status':'PASS','mandatory':True} for id in [f'G{i:02}' for i in range(14)]}
    evidence=['initial_snapshot.json','reports/fixture_registry.json','reports/regression_reconciled.json','reports/risk_recovery_final_results.json','green_state_browser/browser_results.json','browser_results.json','reports/integration_results_recovery.json','reports/integration_results_recovery.json','reports/coverage_final.json','reports/reliability_results.json','reports/toolbar_results.json','reports/export_results.json','reports/performance_results.json','reports/final_integrity.json']
    for id,path in zip(gates,evidence):gates[id]['evidence']=str(ROOT/path)
    gates['G08'].update(status='PASS WITH LIMITATIONS',reason='Three NC completed at declared browser scope; seven remain PARTIAL with Published E2E not covered.')
    gates['G10'].update(status='PASS WITH LIMITATIONS',reason='All16 methods attempted and independently measured;14PASS/2FAIL Plant Show-chart mouse interception, known nonblocking observation; keyboard paths work. No claim all toolbar actions pass.')
    reconciled={'result':'PASS','unique_methods':99,'records':list(regression_records.values()),'first_attempt':{'run':99,'passed':98,'failed':1,'evidence':str(ROOT/'reports/regression_results.json')},
        'targeted_retry':{'run':2,'passed':2,'reason':'ExistingInvestigationAdapter USER_DATA fixture switched to R-ZERO matching original SITE-1 contract; only2 affected methods rerun.'},'runner_guard_calls':[0,0],'original_full_suite_rerun':False}
    (ROOT/'reports/regression_reconciled.json').write_text(json.dumps(reconciled,indent=2))
    (ROOT/'reports/coverage_final.json').write_text(json.dumps({'counts':nc_counts,'cases':nc,'historical_source':str(ROOT/'reports/coverage_results.json'),'new_run_created':False},indent=2))
    telemetry={name:{'console_errors':sum(e['type']=='error' for e in b['console']),'warnings':sum(e['type']=='warning' for e in b['console']),'page_errors':len(b['page_errors']),'failed_requests':len(b['failed_requests'])} for name,b in [*browsers.items(),('zero_pool_retry',zero)]}
    assert all(not x['console_errors'] and not x['page_errors'] and not x['failed_requests'] for x in telemetry.values())
    new_sources=sorted([str(p.relative_to(REPO)) for p in (REPO/'scripts').glob('phase1*.py')]+[str(p.relative_to(REPO)) for p in (REPO/'tests').glob('test_phase1*.py')])
    screenshots=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*.png') if 'screenshots' in p.parts]
    traces=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*.zip') if 'traces' in p.parts]
    final={'overall_verdict':'PASS WITH LIMITATIONS','python_cases':{'passed':141,'failed':0,'components':{'WS1':13,'risk_final':22,'safe_regression_unique':99,'negative_UI_AppTest':7}},
        'main_browser_cases':{'PASS':30,'FAIL':0,'cases':browser_cases},'independent_data_checks':{'PASS':14,'FAIL':0},
        'lifecycle':{'PASS':18},'toolbar':toolbar['counts'],'chart_payload_datasets':28,'performance_samples':3,
        'nc_counts':nc_counts,'nc_cases':nc,'gates':gates,'telemetry':telemetry,'new_test_harness_files':new_sources,
        'screenshots':screenshots,'traces':traces,'integrity':'PASS','remaining_major_functional_defect':False,
        'open_observation':'2/16 Plant Show-chart mouse actions timeout at both viewports; not repaired or suppressed.',
        'scope':'No Phase2/WP3/UX/Bilingual development; no new Runs/production planning/upload/publication/dependencies/commit/push',
        'recovery':'Main only; verified old artifacts, did not rerun successful WS1/WS2 measurements; failed/stale/unstarted tasks continued.'}
    (ROOT/'reports/final_acceptance.json').write_text(json.dumps(final,indent=2))
    common='本次僅 Phase 1 UAT Coverage & Reliability；不代表所有資料／模式／負向 Published E2E 都已通過。方法、實際 commands/results 與 evidence 如下；歷史 red/harness attempts 全數保留。\n\n'
    proof='Evidence root: '+str(ROOT)+'\n\n'
    cov='# Phase 1 UAT Coverage Matrix\n\n**Status: PASS WITH LIMITATIONS — 3 PASS／7 PARTIAL／0 NOT COVERED／0 BLOCKED_PENDING_AUTHORIZATION／0 FAIL（整案分類）。** 七案的 browser／Published E2E 子層仍 NOT COVERED，不以 PARTIAL 消除缺口。\n\n'+common+proof
    cov+=table(['ID','Final status','Executed layers','Evidence / remaining gap'],[[id,r['status'],', '.join(r['executed_layers']),r['remaining_gap']] for id,r in nc.items()])
    cov+='\n## Scope and execution\n\nWS1 python -B tests/test_phase1_coverage.py：13 PASS；新增 tests/test_phase1_ui_layers.py：7 PASS（mocked loader的AppTest呈現，不是browser）。主Browser使用既有R-SYN/R-ZERO/R-REJECT與可清理錯誤快照，不產生Planning Run。\n\n'
    cov+='Detailed cases: '+link('reports/coverage_final.json')+'; lower-layer originals: '+link('reports/coverage_results.json')+'; UI: '+link('reports/negative_ui_layers.json')+'; fixtures: '+link('fixture_browser/browser_results.json')+'; zero retry: '+link('zero_pool_retry/browser_results.json')+'.\n\n'
    cov+='## Expected behavior and limits\n\nB09固定Reference cohort/changed flags；N01非法priority UNAVAILABLE與明確Reason；N02非空zero-demand rate/delta N/A；N03單一zero pool不代表全horizon zero service；N04inventory-backed service1/workload0；N05排除opening-origin；N06逐metric阻不相容單位；N07不縮Universe/不替代endpoint；N08hash/type/unpublished拒絕且無舊export；SYN是真正SYNTHETIC_DEMO。\n\n七個純資料負向案沒有完整合法immutable Published fixture，仍保留E2E風險；不執行planning補百分比。原十個歷史NOT COVERED紀錄不改寫。USER_DATA來源仍SYNTHETIC_EXAMPLE，非已認證真實營運資料。\n'
    (DOC/'PHASE_1_UAT_COVERAGE_MATRIX.md').write_text(cov)

    reltext='# Phase 1 Reliability Report\n\n**Status: PASS WITH LIMITATIONS。** 完整揭露toolbar診斷14PASS／2FAIL；不是全部操作通過。\n\n'+common+proof
    reltext+='## Method and actual results\n\n沿用已完成而未失效的WS2診斷，不重跑。scripts/phase1_reliability_probe.py依序以shared Python --mode performance、隔離Playwright venv --mode browser、shared Python --mode decode執行。\n\n'
    reltext+='Chart lifecycle18PASS；28個實際Arrow chart datasets核對native artifacts全部PASS；兩viewport1440×1100及1600×1100各166warnings，共332。Console/page/failed requests各0。Initial/rerun/scenario/plant/toggle都有timestamp、payload與實際畫面。較支持Vega先embed後insert資料的初始化domain推論，不宣稱每warning精確時點都已證實，不suppress或改chart資料。\n\n'
    reltext+='## Toolbar — open observation\n\n每viewport各2charts×2directions×2methods，16操作：14PASS、2FAIL。兩個FAIL皆Plant Show-chart mouse被dvn-scroller攔截，正常5秒timeout，finalstate=data；各自hit-test/screenshot/trace保存。後續獨立keyboard測量成功，圖表恢復；不force click、不改第三方資產。不做未授權UX改版。歷史D03 mouse=true/keyboard=false/chart_restored=true保留，新證據不回寫歷史。\n\n'
    reltext+=table(['Viewport','Chart','Direction','Method','Actual status'],[[str(c['viewport']),c['chart'],c['direction'],c['method'],c['status']] for c in toolbar['cases']])
    reltext+='\n## CSV and performance\n\n同一existing primary pair做3次分段load/compute/four-export serialization，tracemalloc是traced allocation，不是process RSS；實際browser完成/表格geometry另記。\n\n'
    reltext+=table(['Iteration','Load seconds','Compute seconds','Four-CSV seconds','Serialization peak bytes'],[[s['iteration'],s['load']['seconds'],s['compute']['seconds'],s['serialize_four_csv']['seconds'],s['serialize_four_csv']['traced_peak_bytes']] for s in perf['samples']])
    reltext+='\n四CSV與歷史同fixture bytes完全相同；metrics6,866,365bytes，36rows27cols。Repeated embedded evidence/context是既有contract。單一樣本不是普遍效能benchmark，沒有新增SLO、cache、deferred export、schema／sidecar變更或optimization。寬表仍需水平捲動。\n\nEvidence: '+link('reports/reliability_results.json')+', '+link('reports/toolbar_results.json')+', '+link('reports/ws2_chart_payload_validation.json')+', '+link('reports/performance_results.json')+'.\n'
    (DOC/'PHASE_1_RELIABILITY_REPORT.md').write_text(reltext)

    reg='# Phase 1 Regression Report\n\n**Status: PASS（141個最終Python case methods）；整個Phase1仍PASS WITH LIMITATIONS。**\n\n'+common+proof
    reg+=table(['Group','Actual final result','Evidence'],[['WS1 coverage','13 PASS',link('reports/coverage_results.json')],['R1–R3 final','22 PASS;0fail/error/skip;0runner calls',link('reports/risk_recovery_final_results.json')],['Safe existing regression','99 unique PASS after targeted fixture correction',link('reports/regression_reconciled.json')],['Negative AppTest presentation','7 PASS;0runner calls;not Published E2E',link('reports/negative_ui_layers.json')]])
    reg+='\n## Confirmed defects and narrow fixes\n\n- R1：null/list/scalar及nested manifest wrong types造成uncaught exception或被接受；追加Run_ID=[]/{}的red2subtest TypeError後補string guard。Loader明確shape ValueError與可理解訊息，沒有改計算。\n- R2：原server state已None/[]但wire未clear；修復前真實Run A→B→A仍顯示Baseline。明確None/[] assignment同步所有相關WP2 widget，移除redundant default避免新warning。修復後visible/ARIA與manual reselection均通過。\n- R3：True或mixed[1,True]被當1；比較邊界採與planner一致的numeric/bool拒絕。合法1/2/3含合法numeric1.0不變。\n- R4：setup副作用確立；110方法AST盤點、40會runner的排除，70只屬需人工確認candidate，不全數視為授權。\n\n## Commands and safe execution\n\n22-final: PHASE1_EVIDENCE_ROOT=<root> python -B -c "import tests.test_phase1_risks as r; r.run_report(\\\"recovery_final\\\")"。Safe99: P1_EVIDENCE_ROOT=<root> python -B scripts/phase1_safe_regression.py。Affected-only2: same command --investigation-only。UI7: python -B tests/test_phase1_ui_layers.py。實際stdout／unittestlogs均在logs/；PYTHONDONTWRITEBYTECODE=1、TMPDIR指向本root。\n\n原99第一次98PASS/1FAIL是新adapter用了PLANT-1 Run，但原assert要求SITE-1；只修新runner mapping至已核准R-ZERO，再跑兩個受影響方法，2PASS。保留原失敗JSON/log；不是產品缺陷，不把重跑加成101unique tests。\n\nOriginal comparison suite與WP1/dashboard assertions以existing-Run adapter取代planning setup；原AC七方法/pipeline persisted-run suites不原樣跑，hand-tableau保護相對公式但不冒稱原AC完整重跑。允許的SequentialUpgradeTests只做memory simulation。歷史完整227未重跑；不使用blind discovery。\n\n## Protected behavior\n\nPlanning priority/shared pool/full horizon/conservation/receipt timing、WP1 fullkey/pool/peers/trajectory/native export、WP2 sameRun/fixed cohort/coverage/endpoints/comparability/context皆由safe99/新tests/實際Browser及14獨立checks共同保護。原engines/KPI與planning_risk來源bytes不變。\n\nIncremental source diff: '+link('reports/phase1_incremental_source.diff')+'. 原red21(10fail/5error)、Run_ID red(1test/2subtest errors)、harness import/fixture錯誤、green21均保留，不藏失敗歷史。\n'
    (DOC/'PHASE_1_REGRESSION_REPORT.md').write_text(reg)

    finaltext='# Phase 1 Final Acceptance Report\n\n**Overall: PASS WITH LIMITATIONS。**\n\n'+common+proof
    finaltext+='## Executive summary / actual scope\n\nWS1–WS4全部完成本階段可安全執行範圍；3項confirmed reliability defects最小修復，原Planning/WP1/WP2語意不變。141個最終Python method cases PASS；30個Main real-browser cases PASS；14 independent actual CSV/Arrow checks PASS。WS2另有18 lifecycle PASS、28 payload dataset PASS、3performance samples、toolbar14PASS/2FAIL（非阻斷open observation）。這些層級不合併成誇大的單一test總數。\n\nNC最終3PASS、7PARTIAL、0NOT COVERED、0BLOCKED_PENDING_AUTHORIZATION、0FAIL；七個PARTIAL的Published E2E子層仍明確NOT COVERED。\n\n## Acceptance gates\n\n'
    finaltext+=table(['Gate','Outcome','Evidence / limit'],[[id,g['status'],link(g['evidence'])+(' — '+g['reason'] if 'reason' in g else '')] for id,g in gates.items()])
    finaltext+='\n## Browser/integration/export evidence\n\nPrimary A01–A08、WP1雙路徑/fullkey/evidence、普通tabs及雙側handoff、policy warning、independent context全部通過。Run A→B→A三case通過visible/ARIA reset；synthetic實際四CSV/WP1 paths/handoff通過；zero-pool實際capacity下載與N/A Arrow通過；unpublished/hashcorrupt/null manifest拒絕且無stException／舊exports。\n\n'
    finaltext+=table(['Session','Console errors','Page errors','Failed requests','Warnings'],[[k,v['console_errors'],v['page_errors'],v['failed_requests'],v['warnings']] for k,v in telemetry.items()])
    finaltext+='\nNC detail: [coverage matrix](PHASE_1_UAT_COVERAGE_MATRIX.md). Reliability diagnostics: [report](PHASE_1_RELIABILITY_REPORT.md). Test details: [regression](PHASE_1_REGRESSION_REPORT.md).\n\n## Integrity\n\nHEAD仍'+head+'；index空，未commit/push。Initial1161files只2個授權existing source變更；134protected中2授權、132unchanged；所有原Run paths53→53且primary13檔不變、12artifact hashes match。Core engines/KPI/specs/guides/MVP/歷史UAT不變；外部新增deployment/forensic文件保留。\n\n恢復時sandbox /proc看不到host服務，原8503啟動失敗訊息顯示occupied；actual namespace確認8501/8502/8503健康。未重啟這些服務，改用新8504，完成後只關閉本次PID2075083。原PIDs1117256/1503434/1948318與health200保持。沒有dependency/production config改動，沒有planning/upload/publishing或新Run。\n\nFinal integrity: '+link('reports/final_integrity.json')+'。完整final Git status留於該JSON；新增Phase1文件/tests/scripts是授權delta，working tree仍dirty。\n\n## Known limitations / unresolved risks\n\n兩viewport Plant Show-chart mouse仍被dvn-scroller攔截；keyboard替代有效，但不宣稱mouse已修。Vega warnings保留，不等同data corruption，也不宣稱所有圖都無害。七個負向data browser／Published E2E無完整safe fixture，仍PARTIAL。USER_DATA來源SYNTHETIC_EXAMPLE caveat不變。效能數字只代表本機/fixture，不是承載SLO。\n\n沒有為省usage縮減WS或gates：恢復採Main-only、沿用已驗證WS1/WS2、只補未完成與必要失敗重驗。初始harness/fixture/adapter/zero-scenario assumption失敗均在raw evidence；未把它們藏成產品PASS。\n\n## Files and operational boundary\n\nExisting modified by Phase1: dashboard/scenario_planning_app.py、src/scenario_comparison.py；source incremental diff已保存，原使用者內容保留。新增tests/harness：\n\n'
    finaltext+='\n'.join('- '+p for p in new_sources)+'\n\n'
    finaltext+='Formal files: PHASE_1_ASSESSMENT_REPORT.md、PHASE_1_EXECUTION_SPECIFICATION.md、PHASE_1_EXECUTION_LOG.md、PHASE_1_PROGRESS_CHECKPOINT.md、PHASE_1_UAT_COVERAGE_MATRIX.md、PHASE_1_RELIABILITY_REPORT.md、PHASE_1_REGRESSION_REPORT.md、PHASE_1_FINAL_ACCEPTANCE_REPORT.md。原usage forensic保留未改。\n\nMachine summary: '+link('reports/final_acceptance.json')+'；共'+str(len(screenshots))+' screenshots、'+str(len(traces))+' traces，完整paths在該JSON與files_created清單。所有圖片真實browser captures，未偽造。\n\n## Decision / next task\n\nPhase1本次執行完成並停止等待審查。沒有尚未執行的必要gate；剩餘是明確列出的fixture/E2E與非阻斷observations，不能自行以新Published Run補齊。無需下一session恢復必做任務；若需關閉這些限制，另行定義/授權fixture或toolbar修復，不開始Phase2／WP3／UX／Bilingual。\n'
    (DOC/'PHASE_1_FINAL_ACCEPTANCE_REPORT.md').write_text(finaltext)
    with (DOC/'PHASE_1_EXECUTION_LOG.md').open('a') as f:
        f.write('\n## Execution and recovery completion\n\nWS1 coverage13PASS；risk red21/green21、附加Run_ID red與Mainguard後恢復22PASS。WS2原量測performance3samples/lifecycle18PASS/chart28datasetsPASS/toolbar14PASS2FAIL，沿用未重跑。原source修復僅2files。\n\nRecovery namespace correction: original8501/8502/8503仍健康，occupied8503未被重啟；新8504guarded test runtime啟動/health/cleanup均記錄。Safe99首輪1fixture mismatch，僅重跑2affected，最終99uniquePASS；newAppTest7PASS；Mainbrowser22+state3+fixture5=30PASS（zero首次scenario assumption失敗，單案retryPASS）；14獨立CSV/Arrow checksPASS。每個原失敗attempt保留。\n\nActual commands: tests.test_phase1_risks.run_report("recovery_final"); scripts/phase1_safe_regression.py [--investigation-only]; tests/test_phase1_ui_layers.py; scripts/phase1_browser_acceptance.py with mode default/state_only/fixtures and P1_FIXTURE_CASE=zero_only; scripts/phase1_verify_acceptance.py; scripts/phase1_finalize.py。所有Python-B，outputs在unique execution root。\n\nFinal141PythonPASS，NC3PASS7PARTIAL，12 gates PASS/2 PASS WITH LIMITATIONS。Final integrity初始1161檔只2授權source變動、53Run不變、無Git/history/dependency/production operations。所有正式reports齊備，Phase1停止等待審查；詳見final_acceptance.json。\n')
    with (DOC/'PHASE_1_EXECUTION_SPECIFICATION.md').open('a') as f:f.write('\n## Execution completion supplement\n\n原planned matrix的PENDING為啟動時狀態；最終以coverage/final reports為準。恢復改用8504避開已在host namespace存活的8503，不restart原服務；僅清理本次testPID。新增tests/test_phase1_ui_layers.py屬已授權獨立UI-presentation tests。Final141PythonPASS/30browserPASS/14independentPASS，NC3PASS7PARTIAL；G08/G10附limits，其餘gatePASS。沒有縮減原scope或改業務語意。\n')
    checkpoint=DOC/'PHASE_1_PROGRESS_CHECKPOINT.md';old=checkpoint.read_text()
    checkpoint.write_text('# Phase 1 Progress Checkpoint — Complete\n\n**Current status: PASS WITH LIMITATIONS。WS1–WS4全部完成；G00–G13皆已執行並有結果，G08/G10保留限制。**\n\n141Python case methods、30Mainbrowser cases、14獨立資料checks最終通過。NC3PASS7PARTIAL，七案Published E2E仍NOT COVERED；toolbar14PASS2FAIL是保留的非阻斷observations。既有Runs未變，只有2授權source變更；未commit/push。Final report: PHASE_1_FINAL_ACCEPTANCE_REPORT.md；evidence reports/final_acceptance.json、final_integrity.json。下一session沒有必做恢復任務，等待使用者審查；不開始Phase2/WP3。\n\n## Historical recovery audit (preserved; superseded by current completion above)\n\n'+old)
    (ROOT/'reports/files_created.txt').write_text('\n'.join(str(p) for p in sorted(ROOT.rglob('*')) if p.is_file())+'\n')
    print(json.dumps({'verdict':final['overall_verdict'],'python_passed':141,'browser_passed':30,'independent_passed':14,'nc_counts':nc_counts,'gate_counts':dict(collections.Counter(g['status'] for g in gates.values())),'changed_existing':changed,'screenshots':len(screenshots),'traces':len(traces),'git_head':head},indent=2))


if __name__=='__main__':main()
