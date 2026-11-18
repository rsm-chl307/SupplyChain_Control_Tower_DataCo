# Supply Chain Copilot — MVP Acceptance Baseline

**Baseline version：1.0**
**MVP Acceptance: PASS WITH LIMITATIONS**
驗收結果／文件基線登錄日期：**2026-11-18（UTC）**。

這是已完成驗收的文件與內容指紋基準，不是新 Git commit、tag、deployment 或 remote synchronization。本文件與 [MVP Acceptance Report](MVP_ACCEPTANCE_REPORT.md) 配套：報告解釋結果，本基線固定識別、scope、worktree、hashes 與限制。未聲稱 working tree clean，也沒有把未提交功能當作已存在於 HEAD 的內容。

## Contents

1. [Identity and Freeze Boundary](#1-identity-and-freeze-boundary)
2. [Specifications and Accepted Scope](#2-specifications-and-accepted-scope)
3. [Published Run and Data Classification](#3-published-run-and-data-classification)
4. [Phase Results and Environment](#4-phase-results-and-environment)
5. [Integrity at Acceptance](#5-integrity-at-acceptance)
6. [NOT COVERED Register](#6-not-covered-register)
7. [Open Observations and D03 Decision](#7-open-observations-and-d03-decision)
8. [Process History and Evidence Index](#8-process-history-and-evidence-index)
9. [Excluded Scope and Reproduction](#9-excluded-scope-and-reproduction)
10. [Frozen Fingerprints](#10-frozen-fingerprints)

## 1. Identity and Freeze Boundary

| 項目 | 固定值／意義 |
| --- | --- |
| Repository | SupplyChain_Control_Tower_DataCo |
| Acceptance HEAD | `4b6c84d99173f2472de7a973c1ca98c3a4b15ec2` |
| Branch recorded in WP2 progress | main；不是 remote 同步證明 |
| Source identity | HEAD **加上** Phase 3 驗收的 dirty-worktree content hashes；不能只靠 HEAD |
| 最終結果 | MVP Acceptance: PASS WITH LIMITATIONS |
| Date | 2026-11-18 UTC；登錄既有 Phase 3 結果，不代表重新執行測試 |
| Change control | 後續開發須另行授權；本次未 commit／tag／push，也未開始 WP3 |
| Remote state | 未獨立查驗，不宣稱 ahead／behind、已 push 或 remote 同步 |

### Acceptance-time Git worktree status

以下逐字取自原 Phase 3 `final_integrity.json:git_status_after`；原 before／after 相同。它包含已修改與未追蹤的 WP1／WP2／文件／cache，**不是 clean checkout**。

```text
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
?? docs/PRODUCT_CAPABILITY_CATALOG_EN.md
?? docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md
?? docs/USER_GUIDE_EN.md
?? docs/USER_GUIDE_ZH-TW.md
?? docs/wp2_implementation_progress.md
?? docs/wp2_scenario_tradeoff_analysis_specification.md
?? src/__pycache__/csv_planning_inputs.cpython-310.pyc
?? src/__pycache__/demand_preparation.cpython-310.pyc
?? src/__pycache__/inventory_engine.cpython-310.pyc
?? src/__pycache__/planning_inputs.cpython-310.pyc
?? src/__pycache__/sequential_planner.cpython-310.pyc
?? src/__pycache__/sequential_validator.cpython-310.pyc
?? src/__pycache__/workload_model.cpython-310.pyc
?? src/comparison_io.py
?? src/scenario_comparison.py
?? tests/test_comparison_acceptance.py
?? tests/test_comparison_dashboard.py
?? tests/test_scenario_comparison.py
?? tmp/

```

### Documentation-consolidation pre-work status

本次文件整理前的 HEAD 仍符合上述值，但 status 顯示方式與歷史 Phase 3 有差異：已存在未追蹤的 `.gitignore`，其規則忽略 `/tmp/` 與部分 cache；因此不能將兩個不同時點的 status 說成相同。本次不修改該檔。134 個 acceptance-protected file hashes 在本次整理前仍全部符合 Phase 3 記錄。

以下是本次新增兩份文件**之前**的獨立 snapshot，不取代 acceptance-time status：

```text
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

```

本次任務預期只增加 `docs/MVP_ACCEPTANCE_REPORT.md`、`docs/MVP_ACCEPTANCE_BASELINE.md` 的未追蹤項目；其他既有 status／bytes 應保留。這兩份新文件不是原 Phase 3 的 source snapshot。

## 2. Specifications and Accepted Scope

| Authority | Version／status | 使用方式 |
| --- | --- | --- |
| [WP2 specification](wp2_scenario_tradeoff_analysis_specification.md) | Implementation Specification v1.0 | WP2 同 Run 比較、fixed cohort、metric definitions、comparability／policy／evidence／WP1 integration 的 approved baseline |
| [WP2 progress](wp2_implementation_progress.md) | 未另標版本；階段與 final acceptance 紀錄 | WP2.1–WP2.4 及歷史 227 suite；其早期「尚無 browser acceptance」描述是當時狀態，後續 UAT 由本基線補充，不改寫歷史 |
| [Project journal](scenario_planning/project_journal.md) | 無獨立 RCI spec version；「Phase 3 — WP1 Root Cause Investigation」完成紀錄 | WP1 兩條導航、native evidence、provenance、觀察語意；未捏造 standalone WP1 specification |
| [Historical WP1_validation](improvement_program/work_packages/WP1_validation.md) | Proposed Independent Validation Layer v1.0 | **不是**本 MVP 接受的 Root Cause Investigation；保留命名歧義 |

WP2 specification 的原始 pending-status 文字由其歷史 implementation progress 解釋，未在本次變更規格。P2-UI-01 UI fix 已納入驗收 worktree 指紋，依 [Fix report](../tmp/wp2_browser_uat_phase_2_fix/FIX_REPORT.md) 記錄，沒有改 scenario comparison 或 engine 邏輯。

Accepted feature scope：

- Dashboard／Scenario Overview／Scenario Comparison／Capacity Allocation Detail／Planning Risk Summary 的代表性唯讀 regression。
- WP1 Product → Plant → Week、Plant → Week → Product，篩選、native-grain evidence、source provenance 與下載。
- WP2 explicit selectors／reset、防同情境、fixed Reference Priority cohort、ALL／SELECTED／COMPLEMENT、KPI／Candidate−Reference Delta、metric-level statuses/reasons、POLICY_CONTRAST、four CSVs。
- 一般 WP1／WP2 tab switching 保留獨立情境狀態；明確 Reference／Candidate product handoff 正確導入 WP1；共同 Run、Product×Plant×Week 與 artifact evidence 一致。
- 本次 final browser scope 是指定 USER_DATA Run；不是所有 scenarios pair／modes／negative fixtures 的全面認證。

## 3. Published Run and Data Classification

| 項目 | 固定值 |
| --- | --- |
| Run ID | `sequential_20261117T133913_e22d0f430e98` |
| Relative path | `tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98` |
| Data_Mode | USER_DATA |
| Schema_Version | sequential_v1 |
| Execution／Validation／Publication | SUCCEEDED／PASSED／PUBLISHED |
| Planning horizon | 2017-01-08 至 2017-01-22，完整三週 |
| Universe | SKU-A、SKU-B、SKU-C、SKU-D；PLANT-1、PLANT-2 |
| Source metadata caveat | 仍含 SYNTHETIC_EXAMPLE；來源分類未解決，不能稱為已獨立驗證的真實營運 production data |

[Manifest](../tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98/run_manifest.json) 為原始 source of truth。Run 的 USER_DATA classification 與來源 metadata 不相互覆蓋。

Available scenarios：Baseline、Demand_Surge、Capacity_Disruption、Combined_Stress、Combined_Stress_Lost_Sales。實際 functional pairs：Baseline→Combined_Stress、其反向、Combined_Stress→Combined_Stress_Lost_Sales；沒有宣稱全部 permutations 都測過。

Priority 3 fixed Reference cohort：SELECTED=SKU-A；COMPLEMENT=SKU-B／SKU-C／SKU-D；此 Run 的非零 priority changes 不存在，仍為 NOT COVERED。

## 4. Phase Results and Environment

| Stage | Result／counts | Separate supporting tests |
| --- | --- | --- |
| WP2 implementation／歷史 Phase 2 full suite | 227 passed／0 failed／0 skipped | 歷史自動化結果，非 Browser Phase 2；Phase 3 與本次文件整理均未重跑 |
| Phase A preparation／smoke | PASS，僅啟動與唯讀 smoke scope | 初始 missing-libraries BLOCKED／retry 保留，不冒充完整 UAT |
| Phase 1 Core Application／Batch 1 | 7 PASS／0 FAIL／0 BLOCKED | 沒有單獨捏造 Phase 1 report |
| Phase 2 functional | 46 PASS／1 FAIL／0 BLOCKED／9 NOT COVERED＝56；overall FAIL | 28 Python tests passed，另計；P2-UI-01 是唯一產品失敗 |
| Phase 2 Fix | A01–A08：8 PASS／0 FAIL；overall PASS | 3 focused selector tests passed；不改寫原 Phase 2 FAIL |
| Phase 3 final | 47 cases：37 PASS／0 FAIL／0 BLOCKED／10 NOT COVERED；PASS WITH LIMITATIONS | 3 focused Python selector tests passed，另計 |

Phase 3 的 37 PASS＝**23 browser cases＋12 independent data checks＋2 telemetry／integrity checks**；10 NOT COVERED 不包含在 PASS。不同階段累計／重跑範圍重疊，不能直接加總。各 phase 原始報告見 §8。

| Environment | Recorded acceptance configuration |
| --- | --- |
| Application entry | `dashboard/scenario_planning_app.py` |
| Browser venv | `tmp/wp2_browser_uat_phase_a/venv` |
| Python／Streamlit | Python 3.10.20／Streamlit 1.56.0，依既有環境／UAT 記錄 |
| Playwright／Chromium | Playwright 1.65.2／Chromium Headless Shell 159.0.8154.6 |
| Browser binaries | `tmp/wp2_browser_uat_phase_a/browsers` |
| Endpoint actually used | `http://127.0.0.1:8502`，WebSocket `ws://127.0.0.1:8502/_stcore/stream` |
| Existing services | 8501 PID 1117256；8502 PID 1503434，驗收前後不變 |
| Phase 3 viewport | 1600×1100，fresh browser profiles |
| Earlier viewports | Phase A 1440×1000；Batch 1 1440×1100；不外推所有 viewport |
| Synchronization | Streamlit script-finished WebSocket 訊息與 UI notRunning state |
| Downloads | Phase 3：12 WP1＋4 WP2＝16 actual downloads；four WP2 exports byte-identical to Phase 2 Fix |

Phase A 曾依另行授權安裝 11 個最低 runtime packages（0 existing upgrades／removals）；細節見 [Phase A report](../tmp/wp2_browser_uat_phase_a/reports/PHASE_A_SMOKE_REPORT.md)。後續 Phase 3 與本次文件任務未改依賴；不將原環境準備誤述為完全沒有安裝。

## 5. Integrity at Acceptance

此節取自原 [Phase 3 final_integrity.json](../tmp/wp2_browser_uat_phase_3/final_integrity.json)，是驗收時記錄，不是本次重新執行 service probes：

| Check | Verified historical result |
| --- | --- |
| HEAD | Before／after identical：4b6c84d99173f2472de7a973c1ca98c3a4b15ec2 |
| Git status | Before／after identical，dirty worktree |
| Protected files | 134 unchanged，0 changes |
| Published Run files | 13 unchanged，0 changes |
| Manifest artifact hashes | 12／12 matched |
| Run count | 53→53，manifest paths 集合不變 |
| Streamlit processes | 1117256／1503434 unchanged |
| Health | 8501／8502 均 HTTP 200、body ok |
| git diff --check | Return code 0 |
| Phase 3 operations | 無 source／tests／specifications／user guides 修改；無新 Run、planning、upload、publishing |
| Phase 3 environment／Git | 無 dependency change、restart／termination、commit／push |

Git remote 未獨立查驗；這裡的「no commit／push」是原 phase operation record，不是遠端同步聲明。本次 documentation task 同樣未執行 Git history／network mutations。

36 metric rows、4 membership product IDs、24 Side×Artifact evidence refs 的關鍵識別唯一。所有 native grain／scope／source hashes 與 context 一致。metrics CSV 為 6,866,365 bytes（約 6.9 MB），不是減少 evidence 後的縮減 export。詳細數值 oracle 與原始記錄見 [integration results](../tmp/wp2_browser_uat_phase_3/integration_results.json)。

## 6. NOT COVERED Register

十項維持 NOT COVERED；完整理由與原始 supporting-evidence 限制見 [report](MVP_ACCEPTANCE_REPORT.md#8-known-limitations) 與 [Phase 3 results](../tmp/wp2_browser_uat_phase_3/test_results.json)。

| ID | Status | Scenario／reason |
| --- | --- | --- |
| NC-B09 | NOT COVERED | Non-zero Candidate Priority changes／browser cohort membership；原 Run priority 相同 |
| NC-N01 | NOT COVERED | Missing／invalid priority；無 safe browser fixture |
| NC-N02 | NOT COVERED | Genuine zero-demand denominator；原 cohorts 有正需求，空 cohort 不等於零需求 |
| NC-N03 | NOT COVERED | Zero-capacity pool；helper coverage 不等於 WP2 browser／horizon |
| NC-N04 | NOT COVERED | Fully inventory-covered demand；helper coverage 不等於完整 browser |
| NC-N05 | NOT COVERED | Non-zero opening backlog；完整 fixture 會生成 Run，未執行 |
| NC-N06 | NOT COVERED | Incompatible unit／factor；僅歷史 memory-only assertions |
| NC-N07 | NOT COVERED | Missing product／week／endpoint；僅歷史 memory-only assertions |
| NC-N08 | NOT COVERED | Corrupted／unpublished Run；in-memory checks 不等於 filesystem browser loader |
| NC-SYNTHETIC | NOT COVERED | Current Phase 3 SYNTHETIC_DEMO browser acceptance；本次只准 USER_DATA Run |

未使用新建／修改／copied Run 填補 coverage，未把歷史內部測試改標為本次 browser PASS。

## 7. Open Observations and D03 Decision

| ID | Frozen observation／status |
| --- | --- |
| P3-OBS-01 | OPEN／non-blocking：Vega Infinite extent warnings。main 83、toolbar_retry 69、initial_harness_setup 35；accepted sessions 152，含 setup 187。各 session console errors／page errors／failed requests 均 0 |
| P3-OBS-02 | Mouse obstruction 在 1600×1100 未重現，舊觀察保留；不宣告所有 viewport 已修復 |
| P3-OBS-03 | OPEN／non-blocking：wide tables 需要水平捲動，metrics CSV 約 6.9 MB |
| P3-LIMIT-02 | Historical WP1 naming ambiguity：此 MVP 的 WP1 是 Root Cause Investigation，不是 proposed Independent Validation Layer |
| Coverage boundary | 10 NOT COVERED 保留；無新發現的未解決重大產品／資料一致性失敗 |

**D03 authoritative fields：`mouse_success=true`、`keyboard_success=false`、`chart_restored=true`。**

正確判讀：滑鼠在測試 viewport 成功；依 machine-readable record，**鍵盤互動未成功**。chart_restored=true 只確認圖表恢復，無法單憑該欄位判定恢復方法。**不宣稱 keyboard restoration succeeded。** 原 Phase 3 prose 的鍵盤恢復成功敘述與 JSON 有差異，本基線以 JSON 為準；raw reports／scripts／screenshots／trace 全數保留，不回寫歷史。

[D03 raw retry result](../tmp/wp2_browser_uat_phase_3/toolbar_retry_results.json)、[最終 results](../tmp/wp2_browser_uat_phase_3/test_results.json)、[warnings telemetry](../tmp/wp2_browser_uat_phase_3/logs/browser_telemetry.json)、[原 observations](../tmp/wp2_browser_uat_phase_3/issues_and_observations.md)。

## 8. Process History and Evidence Index

- SETUP-1：`KeyError: 'result'`，案例尚未開始；只修 harness 參數。
- D03-FIRST：data mode 中 stVegaLiteChart locator 消失造成 screenshot timeout；stable toggle targeted retry 通過 assessment。
- DATA-FIRST：overstrict stage attribution，數值 assertions 已通過；payload 實際於 A04 generation 送出，再於 A06 inspected。Verifier 修正 association 後通過，沒有放寬數值期待。
- 以上不是產品修復。真正 P2-UI-01 UI fix 發生在獨立授權的 Phase 2 Fix，而非 Phase 3；原 Phase 2 FAIL 不刪除。

| Evidence | Path／role |
| --- | --- |
| WP1 completion record | [project journal](scenario_planning/project_journal.md)；沒有獨立 Root Cause Investigation spec 檔案 |
| WP2 design／implementation | [v1.0 specification](wp2_scenario_tradeoff_analysis_specification.md)、[progress](wp2_implementation_progress.md) |
| Historical 227 suite | [原 log](../tmp/wp2_acceptance/final_full_suite.log)，不重跑 |
| Phase A | [report](../tmp/wp2_browser_uat_phase_a/reports/PHASE_A_SMOKE_REPORT.md)、[smoke JSON](../tmp/wp2_browser_uat_phase_a/reports/smoke_result.json) |
| Phase 1／Batch 1 | [report](../tmp/wp2_browser_uat_phase_a/batch_1/reports/BATCH_1_UAT_REPORT.md)、[final JSON](../tmp/wp2_browser_uat_phase_a/batch_1/reports/final_results.json) |
| Phase 2 | [report](../tmp/wp2_browser_uat_phase_2/reports/PHASE_2_UAT_REPORT.md)、[results](../tmp/wp2_browser_uat_phase_2/reports/test_results.json) |
| Phase 2 Fix | [report](../tmp/wp2_browser_uat_phase_2_fix/FIX_REPORT.md)、[results](../tmp/wp2_browser_uat_phase_2_fix/test_results.json)、[integrity](../tmp/wp2_browser_uat_phase_2_fix/final_integrity.json) |
| Phase 3 final | [report](../tmp/wp2_browser_uat_phase_3/PHASE_3_UAT_REPORT.md)、[test results](../tmp/wp2_browser_uat_phase_3/test_results.json)、[integration results](../tmp/wp2_browser_uat_phase_3/integration_results.json)、[integrity](../tmp/wp2_browser_uat_phase_3/final_integrity.json)、[observations](../tmp/wp2_browser_uat_phase_3/issues_and_observations.md) |
| Initial failures | [setup](../tmp/wp2_browser_uat_phase_3/logs/initial_harness_error.json)、[D03 original browser](../tmp/wp2_browser_uat_phase_3/browser_results.json)、[initial verifier](../tmp/wp2_browser_uat_phase_3/logs/initial_data_validation.json) |
| Screenshot／download inventory | [screenshots manifest](../tmp/wp2_browser_uat_phase_3/screenshot_manifest.json)、[downloads manifest](../tmp/wp2_browser_uat_phase_3/download_manifest.json) |
| Actual captures | [Candidate handoff](../tmp/wp2_browser_uat_phase_3/screenshots/B_handoff_candidate.png)、[Candidate cleared](../tmp/wp2_browser_uat_phase_3/screenshots/C_A04_candidate_cleared.png)、[D03 failure](../tmp/wp2_browser_uat_phase_3/screenshots/D03_failure.png) |
| Traces | [setup](../tmp/wp2_browser_uat_phase_3/traces/initial_harness_trace.zip)、[main](../tmp/wp2_browser_uat_phase_3/traces/phase3_integration.zip)、[toolbar retry](../tmp/wp2_browser_uat_phase_3/traces/toolbar_retry.zip) |

UAT directories：`tmp/wp2_browser_uat_phase_a/`（含 batch_1）、`tmp/wp2_browser_uat_phase_2/`、`tmp/wp2_browser_uat_phase_2_fix/`、`tmp/wp2_browser_uat_phase_3/`；歷史 automated acceptance 為 `tmp/wp2_acceptance/`。以上要求的 reports／JSON／對應證據均找到；缺少的是獨立 WP1 Root Cause Investigation spec，而非所列執行報告。

## 9. Excluded Scope and Reproduction

不包含 WP3／新功能、AI／LLM／optimizer／preferred-action recommendation、cross-Run comparison／canonical replay／新 scenario controls、bilingual UI 實作、business rules／engines／schema 變更、Power BI 改版、production APS／ERP 能力。Phase 3 沒有重跑 upload／planning／publishing；不將歷史寫入流程測試當作本次 browser 驗收。

重現此 acceptance 的前提：

1. 保留本基線的 HEAD **以及** §10 的未提交檔案內容。只 checkout HEAD 不能重現 WP1／WP2 acceptance worktree。
2. 取回同一 Published Run 的 13 個檔案並核對原 manifest／12 artifact hashes；不能重新 planning 後以新 Run 取代。
3. 使用記錄的 browser／Streamlit environment 與相同 Run scope。原 PID／health 是歷史驗證識別，無法保證其他機器的 PID 或 localhost URL 一樣。
4. 查閱原始 screenshots／trace／downloads／attempt logs，並維持本文件 D03 修正解讀與 NOT COVERED register。
5. 任何重新執行、環境建立、證據搬移／封存或後續修改都按當時獨立授權；本次沒有安裝、啟動服務或重跑 UAT。

目前 pre-work 已存在的 `.gitignore` 將 `tmp/` 忽略。**證據在本機存在，不代表已被 Git 追蹤、push 或可從 remote clone 還原。** 本文件保留 source／Run／關鍵證據 hashes，但 hashes 不能替代檔案內容。正式的跨環境長期 archive／完整 dirty-worktree snapshot 可另行授權；本次未移動 raw evidence、改 ignore、commit 或 push。

基線可作為正式文件 freeze／變更審查依據；不把它稱為 clean commit baseline。後續新階段須另行授權。

## 10. Frozen Fingerprints

SHA256 以原 Phase 3 machine-readable evidence 為準，本次讀取確認對應 protected bytes 仍一致。表格只固定內容指紋，未寫入／修改所列檔案。

### Specification and evidence fingerprints

| File | SHA256 |
| --- | --- |
| `docs/wp2_scenario_tradeoff_analysis_specification.md` | `202e38c96a946031a229d6fd4ceeccba0a92cc78b1d78951a6a39fe35f7a6956` |
| `docs/wp2_implementation_progress.md` | `153d13030afb40960c752ce0c9d3a0c069c2fe8e8eea810983cf17b387603b4e` |
| `docs/scenario_planning/project_journal.md` | `a24b673aaafb08a7b21832f8d9ade912293b5874193bfc23e8dc0f2e0f04669a` |
| `tmp/wp2_acceptance/final_full_suite.log` | `9122cfa3e6b03edf2a5f99afcaa3bdc57d664b5555ca2a11cabce10ad16fd2dc` |
| `tmp/wp2_browser_uat_phase_a/reports/PHASE_A_SMOKE_REPORT.md` | `6f7192f23b9d131551f069bb1bec11e4c52c17e9ea729abeac35d6d9a053fac3` |
| `tmp/wp2_browser_uat_phase_a/batch_1/reports/BATCH_1_UAT_REPORT.md` | `d8e7ead4dbe0ac8468f097524ff1d0008b72be7ffb72b0e1bdf3d17c8f33bfff` |
| `tmp/wp2_browser_uat_phase_2/reports/PHASE_2_UAT_REPORT.md` | `c6ab0d57839b5e6c04615f17dbafd3a2f1a28bef3fd82e74d9a4171b978d97a9` |
| `tmp/wp2_browser_uat_phase_2_fix/FIX_REPORT.md` | `792b57063f50ca0467566f9b477c1b32e06061d6d94b9914c0823ae6f333d1d3` |
| `tmp/wp2_browser_uat_phase_3/PHASE_3_UAT_REPORT.md` | `5d2a24dd5ab40e28203b5723389f4cdf60bf641ccab04f3fa1f8ac68708ec3b0` |
| `tmp/wp2_browser_uat_phase_3/test_results.json` | `faa026685e3c375f0054c04c75ed7cd5068537423694b6aba6b7b411d2668c41` |
| `tmp/wp2_browser_uat_phase_3/integration_results.json` | `253dffd50ef585d4f043b28d3da6e093841dbc6c6df4a84daaa613e4fe2b597e` |
| `tmp/wp2_browser_uat_phase_3/final_integrity.json` | `6cdd837588776d1d355ddcad3d2c77f1293790131e7945d93db850daad259437` |
| `tmp/wp2_browser_uat_phase_3/issues_and_observations.md` | `b189c21e39034122fd92ff3c166dd0592b11e1ea8a436150b9407eafa0a3478a` |
| `tmp/wp2_browser_uat_phase_3/toolbar_retry_results.json` | `61caa99d42fe302382a6703b6c1c15e75bed36e160dc36aedaf5ab2233297579` |

### Published Run: 13 files

包含 manifest 與 12 artifacts；取自原 Phase 3 published_hashes_after。

| Run-relative file | SHA256 |
| --- | --- |
| `allocation_result.csv` | `ce193e20639952c54eb878a9679c8bdf0ef6577ab6ca77c22bebc91562e60ae8` |
| `capacity_baseline.csv` | `f91c25afce1fab60965911d684a6d686b433d887fd72b7117ea3d228e8457994` |
| `capacity_pools.csv` | `b44ecd4f98f81f2189f86e1d13d81d2dcf1795f93637b9d854aaf52c401d14d3` |
| `demand_coverage.csv` | `1a53203a0039e2e12695bfbc617d84a7d8bbc8d411dfaea40a58a133bb40e8a2` |
| `eligibility_ledger.csv` | `55ebfaa64646516ab7d7334bc37b2f27acecdbf1b279a995e9bbb863c7453008` |
| `external_receipts.csv` | `16673a57e387a0b0f0f221c3d24d7d5327b2e612e920c8fd860f7d2bc75441a3` |
| `initial_state.csv` | `0272c29c5bf32a676c0eaa1c0b7ed4f36bf1712a7d7e680cd70c28b844a6da17` |
| `performance_result.csv` | `e0040cab53fcc7082aee7a20048f748bc542d230a1913fe8d9d8ed7837b5e511` |
| `run_manifest.json` | `9a58fe7e5e47054dbd1ce8a7512d0248da901ef0badc394d7dd2fd2c87891ab3` |
| `scenario_snapshot.csv` | `f77d084f97ce6d4e5bcea17bd88a0c0554a4ef020f493f4086eae2d943d432f8` |
| `validation_result.csv` | `f3e9cc7a7fb4d6de100c1bcfdbbe31430ed90510779ff2e02f7dd2294745f183` |
| `weekly_demand.csv` | `1a53203a0039e2e12695bfbc617d84a7d8bbc8d411dfaea40a58a133bb40e8a2` |
| `workload_factors.csv` | `b88158e817e74bb65b66ea150312cf595547e063f3fafe3f87d8124692544f76` |

### Acceptance worktree: 134 protected existing files

這是實際驗收 bytes 的完整 protected register，不是以 HEAD 假定 working tree 內容；也不宣稱是整個作業系統／所有 ignored files 的完整快照。

| Repository-relative file | SHA256 |
| --- | --- |
| `AGENTS.md` | `32675612baed10f56ef7a77a364603e7ecea4c8b3b7ae65ff2b39eb57c4776ea` |
| `ai_agent_implementation_spec.md` | `39783e792e0a027a02718460ad539611c0be7bd2cdd4e41af4c743c48c6f69d4` |
| `dashboard/scenario_planning_app.py` | `a076f6136a08f7591549604fcefe06bd7af9efa571d944fd2aa384658fc3bc5c` |
| `dashboard/supply_chain_control_tower.pbix` | `2db7098d5e3fbaf1350aca681e0752853d908610f591d448b8ee7c73f6c40add` |
| `docs/02_Risk_Dictionary.md` | `6265c65be43acc7dd696111eb59e7bcc61719ae9cbfc1de278f69638eeba50c1` |
| `docs/03_Data_Model.md` | `526a414975f5b2ec85ba710b4c0693d8793de18549ce4fefc8880f1ffdbba85c` |
| `docs/04_KPI_Definition.md` | `813404adbe6b0908dfa9b40a45d4f461d3c7ade36350fc172d929747a298dde3` |
| `docs/05_Inventory_Assumptions.md` | `bec504cff392a461302de1111bb806d6e69ae3d6976f5f70cc2e7ad32924a553` |
| `docs/06_Service_Risk_Definition.md` | `59074c52a8ba91c16654cd5d4a7db6bbe2847f1a3d436e865184b247454f7173` |
| `docs/07_Dashboard_Design.md` | `8775f9ec9dc804d16dc82f7ea13dd9843b438917fa5387d8388b79a7b58573dd` |
| `docs/PRODUCT_CAPABILITY_CATALOG_EN.md` | `4d4cd56ebe75219befe5c0e998f2080881eb6822783e81366a5ae3e17a15ec21` |
| `docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md` | `221b96d27ad3502ff316830a61e18990d990963f81befc6b6e082de86a7504d9` |
| `docs/USER_GUIDE_EN.md` | `86664668d2dbbc5b10688c3c9514a60e4a8c2df9a6288c680c28fc176c001071` |
| `docs/USER_GUIDE_ZH-TW.md` | `0d03c3f4fad14d6167e815146d577bd042800ed1b1656ab53e282933276ffdcf` |
| `docs/improvement_program/00_program_charter.md` | `c6b21f6ecb472a013096a1f1ccaf2e044a8204c3b26791f4671e8c15c9a2a3ba` |
| `docs/improvement_program/01_approved_decisions.md` | `32758573b39b90052885942246aee35050a89f2065127459c9bb47172f69bbce` |
| `docs/improvement_program/02_business_rules.md` | `dc8d1386917847d40b5fa5f61e4a911e415abea2ca9ef5edaad40714739ca69b` |
| `docs/improvement_program/03_target_architecture.md` | `6a67d5c0df847db61bcd70e8a8801d7d6101186cdbbfaf927c84290f299157a0` |
| `docs/improvement_program/04_data_contracts.md` | `f516c02fb9f540b3c43a7592dcbd167c405c576984ddb67bfdddfe722d32ca3c` |
| `docs/improvement_program/05_work_package_specifications.md` | `5c691ec3b64404c0e269019652d35171bbf382ac8a9e1b2105a8afa94b41111d` |
| `docs/improvement_program/06_module_dependency_map.md` | `09563ceab632afc275ec10ba1b7586044438f90b91b1bb26b82e46b2846e5bb7` |
| `docs/improvement_program/07_implementation_roadmap.md` | `56e5826c02f8d38b47329ab87dfd8bedfd9c7dcf8aa0cc829bf8167fb89b1f38` |
| `docs/improvement_program/08_testing_and_acceptance.md` | `91b55fe2b5dceebf32fde6cd944b035c13a151266738c2305d750e29754ec439` |
| `docs/improvement_program/09_pending_decisions.md` | `dff4303230daf5e73dc00f5dd83f1472c1aede9c1f6c3b89a66fb39908652a7b` |
| `docs/improvement_program/10_change_management.md` | `dcf522e76f2e18c336f50dd5e23e7af6ff0033f98c261866f3e5d0e49bb478cb` |
| `docs/improvement_program/README.md` | `c643b83b765381b82b5854f8639dad08326c0d066b266aa578bd9896a0fd5510` |
| `docs/improvement_program/work_packages/WP1_validation.md` | `3f8b81901972d8d98040d0873dd134c4dec051b45b4ecee47605a5b764a1cc81` |
| `docs/improvement_program/work_packages/WP2_demand_capacity.md` | `d2db6c949a768287914e79dc73a12b24bb5852cb7078d7c3aa54696492281e3e` |
| `docs/improvement_program/work_packages/WP3_sequential_planning.md` | `dcca2fb5d05e1c65d29b3b9863288b5ce1a18cf716852c725e710c691c9b61f4` |
| `docs/improvement_program/work_packages/WP4_kpi_dashboard.md` | `717370b4cc593b811631c4005c60c9e5f91022c711c3803f8de21d19c98c10ed` |
| `docs/improvement_program/work_packages/WP5_data_pipeline.md` | `cdf86146a05ef0019c3a294196115cc5d0b1fb722ec31065c68314dae7196533` |
| `docs/improvement_program/work_packages/WP6_scenario_demonstration.md` | `fc271ea4d63b4d8dc9b5bdb1d057788a2e745a63494c522d74a86dd4c5e96186` |
| `docs/planning_csv_inputs.md` | `9ca169de793294dbd0eaa00174a0f407495d409bd4ea38d899e256a70d68b28c` |
| `docs/scenario_planning/business_notes.md` | `537ce7ef5a745cb8dc7b84b16cc8faea6fda8af176b8823e32367d565d757b00` |
| `docs/scenario_planning/dashboard_design_proposal.md` | `93fa7b547aa354e03412307f235224d178d95dba821d644e43ea6447ba1148f5` |
| `docs/scenario_planning/developer_notes.md` | `299f5c1d7a76de60eccf77b57311277098be9704b534ab1f7a4b4f876aca3712` |
| `docs/scenario_planning/interview_notes_zh_tw.md` | `e49a622a0fae4dd4560ec405014cef37c3dfa3b192bf3e312a9dec966ff7fdbb` |
| `docs/scenario_planning/project_journal.md` | `a24b673aaafb08a7b21832f8d9ade912293b5874193bfc23e8dc0f2e0f04669a` |
| `docs/scenario_planning/stage_0_specification.md` | `dc3609c5edc9a7a14ef1dcaa7e8a2dad0988ff6bb6a6d5690f537ef99d93f431` |
| `docs/scenario_planning/stage_1_design_proposal.md` | `b85fe7beb442f741316dc848a921d4d3721193cc3097cd1135d1adaec9622b57` |
| `docs/scenario_planning/stage_2_design_proposal.md` | `b44aaf26fd0a44c7867b3e11d0ff10f5f35c25b48e69d249abb543cd71aa5d37` |
| `docs/scenario_planning/stage_3_design_proposal.md` | `c7bf8a1a7a4a6cb8bb50786e63d17b73ac9b236d226e4522b8c063fae4e51ec2` |
| `docs/scenario_planning/stage_4_design_proposal.md` | `415c28655ba23079eb8b1edd7964e885e409d7a1262b4e656105ec2af8340f0f` |
| `docs/scenario_planning/stage_5_design_proposal.md` | `d557ab7c10c77e91cbd44f1fd6fbac545654601bcf29f5d1be6d3c708ec9d4c6` |
| `docs/wp2_implementation_progress.md` | `153d13030afb40960c752ce0c9d3a0c069c2fe8e8eea810983cf17b387603b4e` |
| `docs/wp2_scenario_tradeoff_analysis_specification.md` | `202e38c96a946031a229d6fd4ceeccba0a92cc78b1d78951a6a39fe35f7a6956` |
| `examples/planning/README.md` | `853812a9f3e8c70714ef64fb1ebcf4943eb5a1e7e97584611c2726039c62d4f4` |
| `examples/planning/dataco_reference/README.md` | `7415915a8a8cd888a102244fe9da38b94a5d653ea8332f82869f458064ffc0b4` |
| `examples/planning/dataco_reference/config.json` | `fc730e667148df7514663e49077c1474e5230e6c0fc84679ade343072fde42b7` |
| `examples/planning/dataco_reference/synthetic_initial_inventory.csv` | `276bd92ab10cd9d03cbf33fd8e4459c3f89d6eb7a4ac771523101423cf33c2f3` |
| `examples/planning/dataco_reference/synthetic_workload_factors.csv` | `2e8ae83edd096926cf105a9af3be62d8ac76387a822091a275c92f881f3da526` |
| `examples/planning/synthetic_demo/config.json` | `6611a61d72433729241c584438d641d2ef4290716fcdc5177b4baf244e521904` |
| `examples/planning/synthetic_demo/demand.csv` | `fb2f44256bc4ea28e22ed9900818ec7f44e35683da8c694bd1228d2540cfcc68` |
| `examples/planning/synthetic_demo/external_receipts.csv` | `f5ad33a2dc7fef667c4a33ba6812b9fe7519723629a3aad2f7ea634bec1c106c` |
| `examples/planning/synthetic_demo/initial_inventory.csv` | `11baf5c688fb1287624fa7cecaaccf489f39bd7bfe32c17191d5187d1d19fc1c` |
| `examples/planning/synthetic_demo/plants.csv` | `457033301960c8441008d608ba7d057a03e485f47f92d0ebb430bd95237e6f12` |
| `examples/planning/synthetic_demo/product_plant_mapping.csv` | `a485d4fc94ca1d0e4aad9a5d91fe4858fe4f35d8560872c39141d7d15c604d53` |
| `examples/planning/synthetic_demo/products.csv` | `612c3b8a87efec1d21981acb401d685fa949dc62fac482f487b3049639e09393` |
| `examples/planning/synthetic_demo/weekly_capacity.csv` | `ee782c07e0f1062d7d7e83c46d33b1e68cfcdfd75f129572974a1e4102e82569` |
| `examples/planning/synthetic_demo/workload_factors.csv` | `1d801e1491eb3ccae4623c4ba9790abade79a10b149eee174271fdbdbe177dbb` |
| `examples/planning/templates/demand.csv` | `501ed390fe5afb2bb9b972171d1a5a0f732d732026ff7cadcbc799793215f496` |
| `examples/planning/templates/external_receipts.csv` | `cfccfb8401ef3481bee5ee2fe48b6f1026fdafb79c36c16b47b4a13655f8272b` |
| `examples/planning/templates/initial_inventory.csv` | `8f5f9a8b5117d4fe304466a0e9044183a58690edc25a88332bb55bb08534c582` |
| `examples/planning/templates/opening_backlog.csv` | `70d27306eb2ccdd1d53b95c04139ba6f0e8bc4ffb0a49dba7c905a0fe9b1dac0` |
| `examples/planning/templates/plants.csv` | `5edc001444b60809a94d0c5a5c9261bca86b23aa920621309519fdcd9d7cca55` |
| `examples/planning/templates/product_plant_mapping.csv` | `e5a9128d5fd173cf17090fc62f3957d9d671841f19c38de9bbfcf78521ddd2c4` |
| `examples/planning/templates/products.csv` | `e290f758fc2b38d4f172efce2241df5ab85b66794f3566dddda341b63c426046` |
| `examples/planning/templates/weekly_capacity.csv` | `dcfd53a326e05ec610d65276b5aed6381b5c258ec54a6b4dff409e58b0d4dda4` |
| `examples/planning/templates/workload_factors.csv` | `55e0419adb7f4d6b6694da4104e4f86b5a8f0d1d8d166b57475f4a07b97f4399` |
| `examples/planning/user_data/capacity.csv` | `77deb6b3f5a9da965eef6f746af75423fdd1c2bf167dc243e6e70b90bea1826b` |
| `examples/planning/user_data/config.json` | `0fe1b78ae5d45405859b74d077803c167f0c74b360b3444b0ffd12ad10c55a88` |
| `examples/planning/user_data/demand.csv` | `aca5340d6f96b6c7828ec0385a50a1b6d411c55f81f1b8b675e6ed7826872455` |
| `examples/planning/user_data/factors.csv` | `d556cc774ec71d5af4019f97f32d151078ba6981b8396aed620b01b8ac793ff2` |
| `examples/planning/user_data/initial_inventory.csv` | `b1dc8f9a7b239828887b3544c0354ac37b0d0b26ede3107f460236b547241e64` |
| `examples/planning/user_data/mapping.csv` | `5e37667cf25e0728de24dd65eee0021e41592ee89edce54f4b35d7159f17af93` |
| `examples/planning/user_data/opening_backlog.csv` | `a8661ee702a8383f73d463cb7b140ed31e6bfa50b9cc125546b84802aa7cf5ef` |
| `examples/planning/user_data/plants.csv` | `afd8795fa9dfdf92ab8d496df037aab20fddf5f984dc8c646a062150a1f2856b` |
| `examples/planning/user_data/products.csv` | `d4dac2308408e944fed034ce3fb5a82096107abf3fdb7cdc217bf63d087304ba` |
| `examples/planning/user_data/receipts.csv` | `8cb83d51da6bd2e79e68989a27bcdba0414feeb0ee250a3473f76f00b48ce10a` |
| `src/__pycache__/allocation_engine.cpython-310.pyc` | `8afaa0a9e39cd619870d7c5b6e0873d7046bb2b4d81733ec46f8bb38b73a0f16` |
| `src/__pycache__/allocation_manager.cpython-310.pyc` | `9b20f9e7ef860032533ed441088d72ccd64ee576878a9efe3ef6a8af695e24b9` |
| `src/__pycache__/allocation_validator.cpython-310.pyc` | `2072c36dc319537d0904bed72b797b0e111034fbc487f7abcb9ee30387fbea34` |
| `src/__pycache__/csv_planning_inputs.cpython-310.pyc` | `bacb91c4a1b3ca0690ae338e9e56452a1105d8f194eba5735f20aa021bf80b58` |
| `src/__pycache__/demand_preparation.cpython-310.pyc` | `4f15b29ad2111692e674b341ba76cc9f40d0f7c910995cc14a9a37887357477d` |
| `src/__pycache__/inventory_engine.cpython-310.pyc` | `0bea6347ca5e339f056885c3ec0e7392c16f17ad61db4851a37be33778633d24` |
| `src/__pycache__/kpi_engine.cpython-310.pyc` | `c665be8bd1ea5f71982c413afaea7ed81fe03db7ab35bb7790ce0838e7ddfb7f` |
| `src/__pycache__/performance_evaluator.cpython-310.pyc` | `9b58b98b9822e3e9e5e762e74aa75ea410db931eb3c8b519ddd6d142847553a2` |
| `src/__pycache__/performance_manager.cpython-310.pyc` | `7470d29b3e71a725638815d8aa9102bf39f07670747d68fc5c65a4d40f90c5af` |
| `src/__pycache__/planning_inputs.cpython-310.pyc` | `3b9d256e4bd7d354ca7fc9e08ab5399d0a4817cd5e4dfeaff8ab201930d4a51e` |
| `src/__pycache__/planning_pipeline.cpython-310.pyc` | `d3a28dc5cc1b6a0b40caff09b836893ab73d720c887f8894799de8af4dbe6bd5` |
| `src/__pycache__/planning_snapshot.cpython-310.pyc` | `1fc86c5f6ab95a60ef4ecb3990cd83a9f307f634dd96c82d77cd575f7ad3e431` |
| `src/__pycache__/run_planning.cpython-310.pyc` | `2d7638172dcc26ea6f81f71d0ef9656bc001ae934a84c1a2665868d3d5d9e6ba` |
| `src/__pycache__/scenario_generator.cpython-310.pyc` | `49a9c642402a61d7427637791f43587a53416ea5f7ddd62542f257df4572afad` |
| `src/__pycache__/sequential_planner.cpython-310.pyc` | `5f87a07a0f53e1c82bed36ef49add2fc33ab441f6b0c86a4f5100c01648b1252` |
| `src/__pycache__/sequential_validator.cpython-310.pyc` | `006d0e51709d7fdded7e39b293c3d944a1c4a2761123c5c2b1a3fa7a31d90454` |
| `src/__pycache__/workload_model.cpython-310.pyc` | `eb49414e3685f32e68a79afa9f0fde2b3581d672f91ce8a64dbdbda17ce202b2` |
| `src/allocation_engine.py` | `181351c7e1392a301f15ed7c2b729fc3e03d417258b543de910d9c17b491b95c` |
| `src/allocation_manager.py` | `d1593ddaecdb2a1222f9325e510b4017123c7863ab64d84256f18a5077b698b3` |
| `src/allocation_validator.py` | `5a8d58cd6843772f271a9a7e4a8dc739b178cf2ba7230231acd360c987b6638c` |
| `src/comparison_io.py` | `2036eb189a3a27a36ae94ce07bbf1409a574881e9791add460adc756bc578a5e` |
| `src/csv_planning_inputs.py` | `d64d462d0b575d950d4d0d9b89a4bc4f495e30def0c48654b05c3df2b8cf6c35` |
| `src/demand_preparation.py` | `4cb987202079f59e2dc0496726a6123ac9184ce2248bac6019ab3064d83aebec` |
| `src/inventory_engine.py` | `18fdd39e95e9e4c397437251dfa9d80b1cea4b1536cb07d942d2a3d7826bb340` |
| `src/kpi_engine.py` | `5ac906af48069edc74d2079efe54007b2b1f6cc31ae90ccd83a90cc510f39395` |
| `src/performance_evaluator.py` | `fa644698496ac46a76cc2c9d96c30a88a9704383f0d92f79854efc87cd8f0b7f` |
| `src/performance_manager.py` | `56f50ce0e7f5b9b643bd11738bae2b4de1ccdc453bba4abd09182de9fae07e72` |
| `src/planning_inputs.py` | `81d4e8a8627bc3c152bfdb03e085a3864c2bc0ea480f20f177f38d4236ff7115` |
| `src/planning_pipeline.py` | `db6b55992bbb54f8fc0e3fe185519656d050508d408df7df701b34d87f778609` |
| `src/planning_risk.py` | `fd2256b6883d74f69e8acae940258aa7e96660cd856317b315414ec02acb5987` |
| `src/planning_snapshot.py` | `47ec6263c994f3330408f545cde2356728e042b4dde2b9cfc787bb503e0eafba` |
| `src/run_planning.py` | `828ba6c048032f851385dec32c676bf22a1f1b5532432631ffe7f461f54cbf18` |
| `src/scenario_comparison.py` | `0a34008c59b652e5647086e15da40626ca94ea747ea7c429dd2e3cce606f6ab5` |
| `src/scenario_generator.py` | `5b01ac73d829fc45b1b7445daa25238ab32771c5a89c4b6a63244dd074836b06` |
| `src/sequential_planner.py` | `ced2642affdedeb783713c5cc11844c248ef58704947edfe2ffe59823a434f1d` |
| `src/sequential_validator.py` | `6818088c8dfa0c946ef685e643edc57158a2923fd19755592b21d1219ae98e1c` |
| `src/workload_model.py` | `6354bddfd0ca1b4146d84070aed2c9e828a2ccc5a4798fc465846648597ffdb2` |
| `tests/__pycache__/test_planning_pipeline.cpython-310.pyc` | `883c2bb27576f775a5e31118c737841e6b52472c92b32cd9acf8c52094068a76` |
| `tests/test_allocation_engine.py` | `56fd9dc634cf1fdc3d28550c6b83411c3956cd2bde8595aebf7c037feb63255c` |
| `tests/test_comparison_acceptance.py` | `039153618cf72d26f51598b1421a5ce290f922510496701acb33fbe5a5ce415d` |
| `tests/test_comparison_dashboard.py` | `32c5a941d1a99aed34e82a6353aeca0826b1320829832dfb3b531ff2c5876354` |
| `tests/test_csv_planning_inputs.py` | `687defd0801e6b4896b1846235da29ca72af865cb70f766e2d05391b33b424db` |
| `tests/test_dashboard_app.py` | `3d7c8c9275bc8b511f1cd3a77b5445f6d42fa17a918edb056f83d500f03fee6e` |
| `tests/test_dashboard_upload_workflow.py` | `fb844cf0d4c9311a6ad97ae555d5b5d05fa656bc22e32a61f8b52ad5b28282d4` |
| `tests/test_independent_validation_upgrade.py` | `01554d76f7cd2435e942a621ea06002f009487cf55e0d66be7f0c22063f14ba4` |
| `tests/test_inventory_transition.py` | `e3d10c9428a5cd48e3a67ac0a4c19a480823a4870045da8a3a51495f0c2cab5a` |
| `tests/test_performance_evaluation.py` | `b71d59111c1095a6798f0aad4b1dd84579418c42892f040b1b7e3be48c0b1bcd` |
| `tests/test_planning_inputs_upgrade.py` | `2b781b880a672a1900ac1d9e114a7cd9b76e5f995cf2f1ab439b6b04efc09893` |
| `tests/test_planning_pipeline.py` | `d36c9e37e55f944dc354b2e151020ecfeb5a9b5f13a5e2bccf8bf7af7cc03b8a` |
| `tests/test_planning_risk.py` | `113c2d2e91dd379fb5c331c823ab63ee2620996f2b389b4fbbaf2a8e79f17116` |
| `tests/test_run_planning.py` | `1bfeefb37a83e665d4f8e561828f2ef67f26fa099abe08f15d3685656933b94e` |
| `tests/test_scenario_comparison.py` | `97bd0e88d6c9650587c74381bd0cabd554c142618b452fcceefb28e70f1aebcb` |
| `tests/test_scenario_generator.py` | `4a997a42b1cd332ef3aab1e60e86602d1954e63d6ada65425486af431ddbaa91` |
| `tests/test_sequential_pipeline_upgrade.py` | `0d0deb622ea381a96c00418d70b2fa675c7aa90b5cffec31d0fa6107f48fe149` |
| `tests/test_sequential_upgrade.py` | `e2d1d414678cc8f0dc9cc32579d9c305186c34e1bf8f13fc834ccb375e6b232b` |
