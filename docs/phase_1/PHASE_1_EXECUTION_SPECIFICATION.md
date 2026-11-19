# Phase 1 — UAT Coverage & Reliability Execution Specification

Version 1.0 • 2026-11-19 UTC • Execution authorized only within this Phase 1.

## 1. Executive Summary

Reliability First：改善既有SC MVP驗證分層與診斷，僅對已重現且不改語意的缺陷作最小修復。MVP既有結果仍是PASS WITH LIMITATIONS。不授權下一Phase2、WP3、UX/Bilingual UI、新功能、架構重設或業務公式變更。

完成定義：G00–G13有實際結果、十個NC逐層記錄、safe regression及真實browser證據、完整性與正式報告齊備。缺少完整Published E2E fixture不得用helper PASS代替，保留PARTIAL/NOT COVERED/BLOCKED_PENDING_AUTHORIZATION並繼續獨立工作。

## 2. Baseline and Repository Protection

已讀完整405行 tmp/PHASE_1_ASSESSMENT_REPORT.md、MVP_ACCEPTANCE_REPORT及BASELINE、WP2 specification。Assessment逐位元組封存至本目錄，保留原相對連結語境與歷史判斷。
Actual HEAD: b29984919342d71c9bc8d3086805058886659cc2; branch main; upstream origin/main.

Initial complete Git status (20 modified/12 untracked; empty index):

     M ai_agent_implementation_spec.md
     M dashboard/scenario_planning_app.py
     M docs/scenario_planning/dashboard_design_proposal.md
     M docs/scenario_planning/developer_notes.md
     M docs/scenario_planning/project_journal.md
     M src/__pycache__/allocation_engine.cpython-310.pyc
     M src/__pycache__/allocation_manager.cpython-310.pyc
     M src/__pycache__/allocation_validator.cpython-310.pyc
     M src/__pycache__/kpi_engine.cpython-310.pyc
     M src/__pycache__/performance_evaluator.cpython-310.pyc
     M src/__pycache__/performance_manager.cpython-310.pyc
     M src/__pycache__/planning_pipeline.cpython-310.pyc
     M src/__pycache__/planning_snapshot.cpython-310.pyc
     M src/__pycache__/run_planning.cpython-310.pyc
     M src/__pycache__/scenario_generator.cpython-310.pyc
     M src/planning_risk.py
     M tests/test_dashboard_app.py
     M tests/test_dashboard_upload_workflow.py
     M tests/test_planning_risk.py
     M tests/test_sequential_pipeline_upgrade.py
    ?? .gitignore
    ?? docs/PRODUCT_CAPABILITY_CATALOG_EN.md
    ?? docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md
    ?? docs/USER_GUIDE_EN.md
    ?? docs/USER_GUIDE_ZH-TW.md
    ?? docs/wp2_implementation_progress.md
    ?? docs/wp2_scenario_tradeoff_analysis_specification.md
    ?? src/comparison_io.py
    ?? src/scenario_comparison.py
    ?? tests/test_comparison_acceptance.py
    ?? tests/test_comparison_dashboard.py
    ?? tests/test_scenario_comparison.py

Evidence root: /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_1_reliability/20261119T034337Z_f91753

Initial snapshot保存1161檔案SHA256、134 protected files、53Run manifest paths。8501/8502/8503 passive preflight皆無監聽。Dirty implementation是working baseline，不能只checkout HEAD重建。

保護所有既有使用者變更、Runs及歷史UAT。Main可在red test確認後作dashboard/scenario_planning_app.py或src/scenario_comparison.py最小reliability修復；src/comparison_io.py只量測，不預設優化。Planning/Allocation/Inventory/KPI公式、risk business logic、既有specs/guides/catalogs、MVP文件與Runs不變。USER_DATA Run來源仍SYNTHETIC_EXAMPLE，不能稱真實production data。

## 3. Four Workstreams and Ownership

| WS | Owner / files | Deliverables / boundaries |
|---|---|---|
| WS1 Coverage | Agent A: tests/test_phase1_coverage.py | Existing-Run adapters及手算memory fixtures、coverage_results；不改shared source |
| WS2 Reliability | Agent B: scripts/phase1_reliability_probe.py | Chart/toolbar browser diagnostics、CSV timing；不改產品、不啟動服務 |
| WS3 Risks | Agent C: tests/test_phase1_risks.py | R1-R3 red/green tests、R4 side-effect allowlist；不改shared source |
| WS4 Integration | Main | Specification/log/reports、shared utilities/source、runtime、browser/integration/verifiers/final integrity |

最多三個active Subagents＋Main，不宣稱四workers同時。Main唯一擁有dashboard、scenario_comparison、comparison_io、共用fixture/test utility、runtime與正式文件。Subagents只寫獨立分配檔案與evidence子目錄，不可同檔並改。

## 4. Execution Dependencies and Stage 0

Snapshot/spec完成→fixtures與test side effects核准→Python red tests→Main確認/修復→green/source freeze→runtime/browser/exports/diagnostics→safe regression→final integrity/reports。WS1/2/3獨立設計並行；WS2 browser等Main服務ready，performance不與重型browser競爭。Shared UI修改時暫停browser；最終驗收須source freeze。

Approved read-only fixture allowlist:
- R-PRIMARY tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98
- R-SYN tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324
- R-ZERO tmp/planning_source_runs/sequential_20261117T123838_5a317a36b54d
- R-REJECT tmp/planning_source_runs/sequential_20261117T124401_d4d42e5adb4f

前三個先核對12artifact hashes/schema/rowcounts/identity；R-REJECT只測controlled rejection。不得planning補資料。Runtime由Main用localhost空閒8503啟動test-only app，PYTHONDONTWRITEBYTECODE=1、usageStats=false、fileWatcherType=none，profile/cache/temp/log在unique root。不重啟現有服務，不安裝依賴。測後只關閉本次自建PID，記錄health/服務生命週期。

## 5. UAT Coverage Matrix

SC=tests/test_scenario_comparison.py，AC=tests/test_comparison_acceptance.py。AC fixture會runner，不能原樣跑。下表是啟動時測試設計，當時status皆PENDING；最終status已載PHASE_1_UAT_COVERAGE_MATRIX.md及completion supplement，不以計畫宣告PASS。所有方法不需新persisted Planning Run；memory/invalid-file fixtures可isolated建立，Published E2E缺口必須保留。

| ID | Existing evidence / missing layer | Method/fixture | Expected / acceptance evidence |
|---|---|---|---|
| NC-SYNTHETIC | SC及dashboard both modes；missing current browser | Existing R-SYN L/P/B/E2E | Mode/string IDs/WP1/WP2/handoff/actual CSV |
| NC-N03 | AC zero-capacity/helper；missing browser | R-ZERO SITE-1/2017-01-22 L/P/B | Pool allocated0/utilization N/A；不能假設horizon service0 |
| NC-N08 | SC Foundation statuses/hash/path/rows | R-REJECT L/B；isolated disposable invalid manifests/files | Controlled reject，無stException/舊export；unpublished不等於hash corruption |
| NC-B09 | SC fixed_reference_cohort_candidate_priority_changes | Copied memory priority升降 P | Ref membership固定、flags/union/disjoint；Published E2E仍缺 |
| NC-N01 | SC missing_priority_is_explicit_not_classified | NaN/bool/string/fractional/inconsistent P/AppTest | UNAVAILABLE/BLOCKED/具體Reason；缺欄位依loader拒絕 |
| NC-N06 | SC units/workload_definition tests | Copied unit/factor P | 只阻受影響metric，理由正確；E2E仍缺 |
| NC-N07 | SC missing_product_week_or_endpoint | Copied memory drop rows P | No shrink/fill0/endpoint substitution；E2E仍缺 |
| NC-N02 | AC zero_demand、SC denominator | 完整一致hand-built memory fixture P | Nonempty cohort sumD0，rate/delta N/A；非empty cohort |
| NC-N04 | AC inventory_covered/helper | 完整hand-built conservation fixture P | Positive demand、inventory-backed service1/workload/backlog0 |
| NC-N05 | AC opening_origin/helper | 完整hand-built origin fixture P | Exclude opening fulfillment；明確numerator/terminal origins |

Test-only browser loader injection最多UI presentation，不得聲稱production-loader Published E2E。Disposable invalid files只在root/fixtures的TemporaryDirectory建立清除，不寫歷史Run、不新增valid Published Run。每案記layer/fixture/oracle/expected/status/outputs，是否newfixture與remainingE2E gap。

## 6. Reliability and Regression Strategy

R1：先測null/list/scalar、Artifacts/Configuration/Scope wrong types；red後Main加入shape validation/controlled ValueError與UI feedback，沒有invalid export。
R2：先selector AppTest wire，再existing Runs browser A→B→A驗visible/ARIA/priorities/product/context；證實後才修，不盲套Candidate方案。
R3：bool/invalid priority對照planning_inputs.numeric；red後只拒非法型別，保持1/2/3與cohort政策。
R4：PublishedFixture、ComparisonDashboardTests、InvestigationAppTests的setup與AC fixture會runner/publish，禁止原樣執行；以readonly adapter替換setup，透明記錄非原suite重跑。

Explicit safe execution allowlist（執行前再逐method檢視）：
- tests.test_inventory_transition.InventoryTransitionTests
- tests.test_independent_validation_upgrade.IndependentValidationUpgradeTests
- tests.test_planning_inputs_upgrade.PlanningInputsUpgradeTests
- tests.test_sequential_upgrade.SequentialUpgradeTests，允許memory simulate_sequential，不落Run
- tests.test_planning_risk pure methods；排除test_risk_views_accept_both_published_data_modes與test_both_published_modes_all_keys_and_kpi_grain
- tests.test_comparison_dashboard.CandidateSelectionSyncTests
- Approved existing-Run adapters重用SC/InvestigationAppTests assertions，不執行原planning setup
- New tests.test_phase1_coverage與tests.test_phase1_risks
- AC原fixture七方法不執行；用新手算memory oracle保護其定義，不假稱AC原suite跑完。

所有tests用python -B、TMPDIR=root/temp；runner guard攔截run_csv_planning/run_sequential_planning，test imports在guard內；記實際count與excluded reasons，不blind discover。核心planning/validation/inventory/KPI來源不改。

WS2：viewports1440x1100及1600x1100；獨立Show-data mouse/keyboard、Show-chart mouse/keyboard，記attempt/focus/locator/timeout/visible state，不force-click。Vega記timestamp/action/payload；initial/rerun/scenario/plant/toggle後finite/visible render，不suppress。歷史D03 true/false/true保持；新測量不改舊evidence。
CSV：R-PRIMARY Baseline→Combined_Stress Priority3；分開load/compute/serialize timing與tracemalloc peak及browser completion。保持schema/bytes/context/sidecars；6.9MB只歷史樣本，無自訂硬SLO、新performance framework或預設cache/UX改版。

## 7. Acceptance Gates

全部G00-G13 mandatory有明確結果。G08可保留remainingE2E gaps，G09/10/12非阻斷observations可附limits。每gate失敗保存trace/log/screenshot或Python traceback，繼續獨立cases；correctness/integrity FAIL不得以低層PASS遮蓋。越界fix只停止該項並BLOCKED_PENDING_AUTHORIZATION。

| Gate | Preconditions / method | Evidence | Pass criteria |
|---|---|---|---|
| G00 | Initial snapshot | initial_snapshot.json | HEAD/status/hash/Run registry保存、授權delta可追溯 |
| G01 | Four approved fixtures preflight | fixture_registry.json | Valid loaders/hash/schema/rows正確；R-REJECT拒絕 |
| G02 | Safe engine tests/oracle | regression_results.json | Frozen invariants正確，不改core，不產Run |
| G03 | R1/negative loaders | risk_results.json | Controlled rejection，無exception/invalid export |
| G04 | Source freeze, browser A01-A08 + A-B-A | browser_results.json | Visible/ARIA/wire/context同步、explicit selection |
| G05 | Valid Run, WP1 two paths | browser_results.json | Fullkey/pool/peers/trajectory/native evidence正確 |
| G06 | G04/G05, tabs/handoffs | integration_results.json | 正確side/scenario/Run，獨立context保留 |
| G07 | Independent metrics/policy | coverage_results.json | Numerator/denominator/endpoint/workload/Delta/status正確 |
| G08 | Ten NC declared layers | coverage_results.json | 真正executed layer才PASS，E2E gap仍PARTIAL |
| G09 | Runtime charts lifecycle | reliability_results.json | Finite nonempty資料正確render，合法N/A不造值 |
| G10 | Two viewport/four toolbar actions | toolbar_results.json | 方法結果獨立記錄，不force、不誤推keyboard |
| G11 | Actual WP2 four + WP1 downloads | export_results.json | Parse/IDs/context/grain/hash/no fanout/determinism |
| G12 | Isolated representative measurements | performance_results.json | Compute/serialize/browser分開、誠實記錄limits |
| G13 | All integration complete | final_integrity.json | 授權files only，歷史Runs/artifacts/user work完整 |

## 8. Integration Contracts and File Boundaries

Main保存existing touched source的initial copy/hash與incremental diff，保留所有原有changes。不得reset/clean/stash/checkout/commit/push/change branch。原Assessment來源、MVP docs、specs與guides不改。
Four CSV Comparison_ID/Run/scenarios/context一致；metrics保留numerators/denominators/status/reason/N/A/Delta units/embedded evidence。Evidence key=Side×Artifact，兩側同artifact非錯誤duplicate。WP1 native columns與Investigation_* context分開，IDs001/NA以string讀。Actual download+parse才成功。Arrow以Comparison_ID與generation stage聯結，不要求inspection stage重送。

## 9. Deliverables

docs/phase_1完整檔案：PHASE_1_ASSESSMENT_REPORT.md archive、PHASE_1_EXECUTION_SPECIFICATION.md、PHASE_1_EXECUTION_LOG.md、PHASE_1_UAT_COVERAGE_MATRIX.md、PHASE_1_RELIABILITY_REPORT.md、PHASE_1_REGRESSION_REPORT.md、PHASE_1_FINAL_ACCEPTANCE_REPORT.md。不得留placeholder。
New tests/harness見§3。Unique root/reports記fixture registry/allowlist/coverage/risk/regression/browser/reliability/performance/export/integration results、G00-G13、final_integrity/file inventory。Screenshots/traces/logs/downloads/raw frames均保存本次root，原UAT scripts不直接重跑以免覆寫舊evidence。

## 10. Risks, Limitations and Deferred Work

Nonzero priority、invalid priority、完整zero demand/inventory cover/opening backlog、incompatible data、missing coverage/hash corruption等缺部分完整Published E2E fixtures；memory/isolated UI不冒充E2E。需new persisted planning/publication或改歷史Run者BLOCKED_PENDING_AUTHORIZATION，繼續獨立work。
Existing venv/browser目錄在不等於launch已成功；無法用現環境則該browser gate BLOCKED，不安裝修環境。產品fix僅限red test證實且保留語意；business rule/engine/API/architecture changes另需授權。Wide-table UX、Phase2、WP3均排除。
本規格完成後立即Stage0→後續執行，不停止於文件。最終verdict PASS/PASS WITH LIMITATIONS/FAIL/BLOCKED如實記錄，不預設成功。

## Execution completion supplement

原planned matrix的PENDING為啟動時狀態；最終以coverage/final reports為準。恢復改用8504避開已在host namespace存活的8503，不restart原服務；僅清理本次testPID。新增tests/test_phase1_ui_layers.py屬已授權獨立UI-presentation tests。Final141PythonPASS/30browserPASS/14independentPASS，NC3PASS7PARTIAL；G08/G10附limits，其餘gatePASS。沒有縮減原scope或改業務語意。
