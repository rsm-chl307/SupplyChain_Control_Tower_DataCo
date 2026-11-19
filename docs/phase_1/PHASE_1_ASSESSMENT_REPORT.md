# Phase 1 — UAT Coverage & Reliability Assessment

**評估日期：2026-11-19 UTC**  
**結論：可進入 Phase 1 實作規劃；尚未授權實作或執行新一輪 UAT。**

本報告只做 repository、原始驗收證據、測試與 fixtures 的唯讀評估。沒有重新驗證產品，MVP 的既有結論仍是 **PASS WITH LIMITATIONS**。

原評估時 `docs/phase_1/` 不存在，因此未建立該目錄或報告檔案，先於對話交付完整報告。本檔依使用者後續授權直接保存該報告至 `tmp/`，未重新執行評估、測試或 UAT。原建議的正式文件路徑仍為：

`docs/phase_1/PHASE_1_ASSESSMENT_REPORT.md`

## 1. Executive Summary

主要發現：

1. **十個 NOT COVERED 仍不能改標 PASS。** 不過，現有資料中找到可供未來測試的 SYNTHETIC_DEMO、零產能 pool，以及 FAILED／UNPUBLISHED Run；部分缺口不必靠新增 Run 才能驗證。
2. **現有測試不能整套直接執行。** 多個 class 在 setup 中執行 planning、寫入 inputs 或發布 temporary Runs；測試主體有 no-planning mock，也不代表 setup 安全。
3. **三個可靠性 observations 暫不支持直接修改產品。** Vega 警告較符合 chart initialization lifecycle；toolbar 需要更精確的測量；大型 CSV 主要來自既定 embedded-evidence contract。
4. **有三個值得 tests-first 驗證的靜態風險候選：** malformed manifest 錯誤處理、切換 Run 後的前端狀態同步、非法 priority 型別。它們尚未在本次評估中重現為產品缺陷。
5. **Browser 執行環境需要重新準備。** 評估時未找到 application processes，8501／8502 亦沒有監聽紀錄；歷史 HTTP 200 與 PID 不能當成目前服務可用證據。本次未啟動服務。
6. **四個 Workstreams 可以分工，但有共同前置工作與整合 barrier。** 本環境最多 Main＋3 個同時活動的 Subagents，不能安排四個 worker 同時執行。

## 2. Repository Baseline and Git Status

已先閱讀：

- [MVP Acceptance Report](../docs/MVP_ACCEPTANCE_REPORT.md)
- [MVP Acceptance Baseline](../docs/MVP_ACCEPTANCE_BASELINE.md)

| 項目 | 評估時確認 |
|---|---|
| HEAD | `b29984919342d71c9bc8d3086805058886659cc2` |
| Branch | `main` |
| Upstream | `origin/main` |
| Modified tracked files | 20 |
| Untracked files | 12 |
| Staged files | 0 |
| 與預期差異 | HEAD 與檔案狀態符合最近報告；runtime services 已不在 |
| Report directory | `docs/phase_1/` 不存在，未建立 |

完整 status：

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

評估前後核對：

- HEAD、完整 status、空 index 均未改變。
- 1,160 個納入檢查的既有檔案：**0 修改、0 新增**。
- Run manifests：**53 → 53**，路徑集合相同。
- MVP Baseline 的 161 筆 fingerprint rows 全部吻合。
- `git diff --check` 通過。
- 沒有執行 tests、browser、planning、upload、publishing、安裝、服務啟停或 Git mutations。

以上為原評估結果；後續僅依授權新增本 Markdown，不重新量測上述狀態。

**重要：** acceptance commit 主要保存驗收文件；目前被驗收的 implementation 仍包含 dirty／untracked bytes。不能從 HEAD 建立乾淨 checkout，就假定取得相同 WP1／WP2 實作。

## 3. Subagent Execution

**四個獨立 Subagents 均已實際啟動並完成。**

| Subagent | 明確範圍 | 主要產出 |
|---|---|---|
| WS1 | 十個 NC cases、現有 tests／fixtures／Runs、安全測試分層 | Coverage matrix、三個可重用既有 Run、fixture／授權需求 |
| WS2 | Vega、toolbar、wide tables／large CSV | 原始證據、成因分析、測量缺口與定向測試建議 |
| WS3 | MVP reliability 範圍內的 source／regression review | 三個靜態風險候選、測試 setup 的副作用風險 |
| WS4 | 整合流程、共同 fixtures、最終 acceptance gates | 分層驗收矩陣、所有權、執行順序與權限需求 |

執行方式為：

- 第一波：WS1、WS2、WS3 並行。
- WS2 完成釋出名額後，啟動第四個獨立 WS4。
- Main 核對來源、fixture hashes、環境與互相重疊的結論，再統整本報告。

沒有 Subagent 執行失敗或未完成工作。所有 Subagents 均採唯讀操作，沒有產生 report files。

## 4. WS1 — Ten UAT Cases

以下狀態是**覆蓋評估**，不是新的測試 verdict。

縮寫：

- **SC**：[test_scenario_comparison.py](../tests/test_scenario_comparison.py)
- **AC**：[test_comparison_acceptance.py](../tests/test_comparison_acceptance.py)
- **P**：Python／independent oracle
- **B**：真實 Browser
- **L**：production loader／artifact validation

「可安全設計」不代表本次已獲准執行；新增 tests、fixtures、harness 或 evidence outputs 仍需後續授權。

| Case | 現有覆蓋 | Fixture availability | 安全測試方式／必要層級 | 依賴與建議 acceptance |
|---|---|---|---|---|
| **NC-B09** 非零 Candidate priority changes | Partial；SC `test_fixed_reference_cohort_candidate_priority_changes`，126–136 | 有 copied-memory variant；未找到對應 Published Run | P 可用記憶體資料；B 需核准 test-only fixture 或完整合法 fixture | WS3 priority contract；驗升／降 priority 後 membership 不變、Changed flags 正確、Selected／Complement 互斥且 union=ALL |
| **NC-N01** Missing／invalid priority | Partial；SC `test_missing_priority_is_explicit_not_classified`，138–144，主要測 NaN | 無現成 invalid-priority Run | P 型別／缺值矩陣；B 驗 controlled error／UNAVAILABLE／Reason | 與 WS3-R3 合併。分開測缺欄位、NaN、bool、0／4、字串、fractional、跨週不一致；不得靜默分類 |
| **NC-N02** 真正 zero-demand denominator | Partial；SC 146–157、AC `test_zero_demand_is_na_not_perfect_service` | 有測試程式定義；AC setup 會產生 Run；未找到非空零需求 cohort 的可用 Run | P＋B；需完整 coverage 的非空 cohort fixture | 分母確為 0，rate／Delta=N/A 且 Reason 正確；不能以 empty cohort 代替 |
| **NC-N03** Zero-capacity pool | Partial；AC zero-capacity test、planning helper | **已有 R-ZERO** | 未來核准後可 L＋P＋B，不改 Run | 驗 SITE-1／2017-01-22 的 pool allocated=0、合法 N/A utilization；不能推論整 horizon service=0 |
| **NC-N04** Inventory 完全覆蓋需求 | Partial；AC inventory-covered test、zero-requirement helper | 未找到完整 product-horizon fixture；AC 會 planning | P conservation＋B metric display；需核准 fixture | 正需求、足額 inventory 下 production／workload／backlog=0、service=1；不能只把 requirement 欄改 0 |
| **NC-N05** Non-zero opening backlog | Partial；AC opening-origin test、inventory-origin helpers | 未找到 positive opening-origin backlog 的既有 native Run | P origin arithmetic＋B numerator／denominator／terminal breakdown | Opening-origin fulfillment 不得混入 horizon-origin service；完整 fixture 需另准 |
| **NC-N06** Incompatible unit／factor | Partial；SC `test_units_block_quantity_but_not_workload`、`test_workload_definition_blocks_only_workload_deltas` | 有 memory variants，無現成 incompatible Published pair | P 逐 metric comparability＋B Reason／CSV | 不可把一個不相容條件一律套用所有 metrics；workload／quantity 各依規格阻擋 |
| **NC-N07** Missing product／week／endpoint | Partial；SC coverage／subhorizon tests | 有 memory filters；既有缺欄位樣本不是完整 coverage fixture | P completeness＋B BLOCKED／Reason | 不縮小 Universe、不填 0、不以 last available week 取代 endpoint |
| **NC-N08** Corrupted／unpublished Run | Partial；SC invalid manifest／hash／path／rowcount tests | **已有 R-REJECT**；未找到 hash-corrupted Run | R-REJECT 可未來 L＋B；其他 corruption 要核准 disposable fixture／mock filesystem | 明確拒絕且無舊 comparison／export 殘留；unpublished 測試不等於 hash corruption coverage |
| **NC-SYNTHETIC** SYNTHETIC_DEMO browser | 有歷史 Python／AppTest coverage；本次 browser 未驗 | **已有 R-SYN** | 核准後可 L＋P＋B，無須重跑 planning | 驗真正 Data_Mode、string IDs、WP1 雙路徑、WP2 selectors／cohort／handoff／actual exports |

### 可重用的既有 Runs

本次只讀 manifest／CSV 並驗 hashes，**未執行 production loader 或 browser**。

| Alias | 路徑 | 已確認 | 邊界 |
|---|---|---|---|
| R-PRIMARY | `tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98` | 既有 acceptance Run；USER_DATA，source metadata 含 SYNTHETIC_EXAMPLE | 不能稱為已驗證真實營運 production data |
| R-SYN | `tmp/planning_source_runs/sequential_20261117T123837_b3a65ad9b324` | SYNTHETIC_DEMO；SUCCEEDED／PASSED／PUBLISHED；12 artifact hashes 匹配；24 allocation rows | 尚待未來 loader preflight 與 browser acceptance |
| R-ZERO | `tmp/planning_source_runs/sequential_20261117T123838_5a317a36b54d` | USER_DATA；12 artifact hashes 匹配；四個 scenario 的 SITE-1／2017-01-22 pool capacity=0 | 是單一 plant-week 零 pool，不是完整 horizon 零產能 |
| R-REJECT | `tmp/planning_source_runs/sequential_20261117T124401_d4d42e5adb4f` | FAILED／FAILED／UNPUBLISHED；Artifacts={} | 適用 rejection；不是正常 comparison 或 corruption fixture |

**覆蓋關閉規則：** mocked loader 的 browser fixture 可驗 UI presentation，但不能當成通過 production loader 的 Published Run E2E。若不授權額外 fixtures，相關 E2E 缺口應繼續保留 NOT COVERED。

## 5. WS2 — Reliability Observations

### P3-OBS-01 — Vega Infinite Extent Warnings

**歷史可重現；本次未重新啟動 browser。**

證據與來源：

- Overview：`dashboard/scenario_planning_app.py:1330`，`_sequential_views` 的 `st.line_chart`。
- Plant Bottlenecks：`dashboard/scenario_planning_app.py:1108`，`_planning_risk_summary` 的 `st.bar_chart`。
- 歷史 chart payload：Overview 9 melted rows、3 dates；PLANT-2 utilization 3 rows，均有 finite values 且與 artifacts 一致。
- 已安裝 Streamlit frontend 的流程為先 embed，再 insert Arrow data，再 run／resize；較支持暫時空 domain 的 lifecycle 推論。
- 但沒有將每一筆 warning 與 data insertion 的精確時點完整對齊，不能宣稱所有 warnings 永遠無害。

Phase 3 原始計數：

| Session | Warnings |
|---|---:|
| main | 83 |
| toolbar_retry | 69 |
| initial_harness_setup | 35 |
| 主驗證＋retry | 152 |
| 含 setup | 187 |

**Severity：Low／目前非阻斷。** 沒有證據指出 accepted Run 的 KPI 或 artifacts 被破壞。

**建議：** 未來分別量測兩張圖的 initial load、rerun、scenario／plant change、data/chart toggle；同時保存 warning timestamps、payload、completion state 與 final screenshot。合法 zero-capacity utilization N/A 不應自動當作資料損壞。

**現在不支持：** suppress warnings、修改 chart data、升級 dependencies 或立即改 application chart code。

### P3-OBS-02 — Chart Toolbar

保留 authoritative historical record：

```json
{"mouse_success": true, "keyboard_success": false, "chart_restored": true}
```

正確結論：

- Mouse 在測試的 **1600×1100** viewport 成功。
- 依 machine-readable record，keyboard 未成功。
- `chart_restored=true` 本身不能證明恢復方法。
- 不能宣告其他 viewport 的問題已修復。

歷史 Batch 1 在 1440×1100 的 pointer-interception 記錄涉及 `stFullScreenFrame`／Vega transparent background。Application 使用 Streamlit built-in toolbar，沒有自訂 toolbar mouse／keyboard handlers。

另確認一個**測量設計缺口**：`tmp/wp2_browser_uat_phase_3/toolbar_retry_steps.py:17` 的 `keyboard_success` 只在某個 fallback 分支設定，未分開記錄兩個切換方向。這不能用來覆寫 frozen false，也不能推定鍵盤驗收通過。

**Severity：Low product observation；Medium-priority harness improvement。**

未來應分別記錄：

| 操作 | 必須獨立記錄 |
|---|---|
| Show data — mouse | attempted、success／timeout、hit-test、最後狀態 |
| Show chart — mouse | 同上 |
| Show data — keyboard | focus、按鍵、最後狀態 |
| Show chart — keyboard | 同上 |

至少重測歷史兩種 viewport；使用 stable toggle／panel locator，不用 force-click。**先改善測量，再依重現結果判斷是否需要產品修復。**

### P3-OBS-03 — Wide Tables／Large CSV

確定的 generation path：

- `src/comparison_io.py:26`，`comparison_csv_exports` 將完整 context、evidence、membership JSON 加入每列 metrics。
- `dashboard/scenario_planning_app.py:1254` 在有效 comparison rerun 時 eager 建立四份 CSV，即使尚未下載。
- 寬表直接顯示多個 machine-oriented 欄位，水平捲動是已知限制。

歷史代表性檔案為 **6,866,365 bytes、36 rows、27 columns**。其中 decoded repeated evidence JSON 總量約 6.14 MB。這是單一 fixture 的檔案觀察，**不是一般效能 benchmark，也不是 process RSS／memory leak 證據**。

**Severity：Low usability；潛在 Medium scale／rerun cost。**

建議先分別測量 comparison compute、serialization、browser rendering 的時間與 memory。若證實有問題，再評估保持 CSV bytes／schema 的 cache 或 deferred generation。

不應直接移除 embedded evidence、改成 sidecar-only，或以重組顯示欄位開始 UX 工作；前者涉及契約，後者超出本次 Reliability First 範圍。

## 6. WS3 — Bug & Regression Assessment

以下前三項為**靜態風險候選**，不是本次重現的產品失敗。

| ID | 風險、來源 | 既有 coverage／缺口 | 建議 |
|---|---|---|---|
| R1 | `dashboard/scenario_planning_app.py:865` loader 假設 manifest root／nested structures 為有效 dict。`[]` 等有效 JSON shape 可導致 `.get` 的 AttributeError；UI catch 未涵蓋所有類型錯誤 | 有 publication／schema／hash／path／rowcount tests；缺完整 root／nested type matrix | Medium。先測 `null`、list、scalar、錯型別 Artifacts／Configuration／Scope；要求 controlled rejection、無 `stException`／可信匯出殘留 |
| R2 | `dashboard/scenario_planning_app.py:1191` WP2 Run reset 仍對 Reference／priorities／product 使用 `pop()`；與已修 Candidate 的同步風險類型相似 | Run-switch AppTest 驗 server values；缺相應 browser visible／ARIA／wire 證據 | Medium。先做 Run A→B→A 測試，不預先套用 Candidate 修法。切換 Run 不等於新增跨 Run 比較能力 |
| R3 | `src/scenario_comparison.py:190`，`_priority` 使用 `isin([1,2,3])`；沒有 planner `src/planning_inputs.py:27` 的 `numeric` bool rejection | 現有 priority test 主要測 NaN、合法整數 changes | Low–Medium。驗 bool／非法型別矩陣，確認 approved type contract；不改 priority business policy |
| R4 | **已確認的執行風險，不是產品 bug：** suites 的 setup 會 planning／寫 Runs | SC `PublishedFixture`、dashboard `ComparisonDashboardTests`／`InvestigationAppTests`、AC fixture | High coordination priority。方法＋class setup＋fixture 一起審核；禁止 blind discovery |

### 應保護的既有能力

- Planning：priority order、shared workload pool、full-horizon coverage、inventory／backlog origin conservation、receipt timing。
- WP1：`src/planning_risk.py:347` investigation helpers 的完整 key isolation、單一 pool、peer order、adjacent-week trajectory、native-grain exports。
- WP2：同 Run／不同 scenario、固定 cohort、不縮小 Universe、完整 endpoint、metric-specific comparability。
- Export：四檔 context 一致、string IDs、no fanout、deterministic ordering。

Relevant regression families：

- `tests/test_inventory_transition.py`
- `tests/test_independent_validation_upgrade.py`
- `tests/test_planning_inputs_upgrade.py`
- `tests/test_sequential_upgrade.py`
- `tests/test_planning_risk.py`
- `tests/test_dashboard_app.py`
- `tests/test_scenario_comparison.py`
- `tests/test_comparison_dashboard.py`
- `tests/test_comparison_acceptance.py`

目前沒有理由修改 Planning／Allocation／Inventory／KPI formulas。

## 7. WS4 — Integration & Final Acceptance Matrix

以下是**未來規劃**，本次沒有執行 final regression。

| Gate | 必要驗證 | 完成準則 |
|---|---|---|
| G00 Baseline | HEAD、dirty bytes、Git status、Run set | 基線完整，不以 HEAD 取代工作目錄實作 |
| G01 Fixture eligibility | Run status、hash／schema／identity／用途 | Fixture allowlist 明確；invalid fixture 不被當正常數值來源 |
| G02 Engine protection | 核准的 pure／in-memory regressions、獨立 oracle | Frozen business rules 不變；無 persisted Run |
| G03 Invalid inputs | Manifest／artifact／publication／coverage | Controlled rejection／BLOCKED 與理由正確，無錯誤 export |
| G04 WP2 state | A01–A08＋Run A→B→A | Visible／ARIA／server／context 同步；不得自動猜選 |
| G05 WP1 | 雙路徑與 Product／Plant／Week 切換 | Selected row／pool 唯一、trajectory／peers 正確 |
| G06 Integration | 一般 tab switching＋兩側 handoff | 正確 Scenario／Product／Run，不混用來源 |
| G07 Metrics／policy | Numerator／denominator、endpoint、workload、Delta | Metric-level statuses／reasons 正確；無錯誤 Winner |
| G08 Ten NC cases | 各 case、layer、fixture、verdict | 只有完成相應層級才關閉；其餘保留 NOT COVERED |
| G09 Chart lifecycle | Payload／warning／completion／rendering | 有限非空資料無 persistent blank／wrong domain |
| G10 Toolbar | 四種方法／方向、兩種 viewport | 每操作有 attempted/result，不能共用模糊布林 |
| G11 Exports | 四種 WP2＋代表性 WP1 actual downloads | Parse、schema、IDs、context、hash、native grain、determinism 正確 |
| G12 Performance observation | Compute／serialize／render 分段量測 | 記錄條件與數據；未核准前不捏造硬門檻 |
| G13 Final integrity | Git／protected bytes／Runs／services | 無未授權變更；所有 FAIL／NC／OPEN／attempt history 保留 |

驗收分層必須區分：

**Pure assertions → Loader → AppTest → Real Browser → Cross-module reconciliation → Final integrity。**

任一層通過，都不能自動替代下一層。

## 8. Cross-Workstream Dependencies

| 輸出／共同決策 | 產出方 | 使用方 | 協調要求 |
|---|---|---|---|
| Fixture catalog／negative-case variants | WS1 | WS2、WS3、WS4 | Main 核准唯一版本，避免各自造不同資料 |
| Error／status expectation | WS1＋WS3 | WS4 | 先分清 loader rejection、membership UNAVAILABLE、metric BLOCKED |
| Toolbar／warning measurement semantics | WS2 | WS4 | 先定義 attempted／not attempted／success，再執行 |
| Confirmed repro／最小 fix proposal | WS3 | Main | 必須先重現，修復另行授權 |
| Export contract／independent verifier | WS4 | 全部 | 不能為效能刪減 evidence |
| Source freeze／runtime allocation | Main | 全部 | Browser acceptance 期間禁止 shared source hot reload |
| Final verdict／integrity | Main | 使用者審查 | 所有 WS 完成後統一收斂 |

## 9. Parallel Execution Feasibility

**可並行：**

- Fixture 盤點與 Python oracle 設計。
- Chart／toolbar 歷史證據分析與新 instrumentation 設計。
- 三項靜態風險的 focused tests 設計。
- Integration protocol／CSV verifier／report schema 設計。

**必須排序：**

1. Fixture 批准後，才能 loader preflight。
2. Runtime／output permissions 完成後，才能 browser。
3. Shared source integration 完成並 freeze 後，才能 final browser acceptance。
4. 效能量測不能與重型 browser／downloads 競爭資源。
5. Final integrity 與 acceptance 必須最後執行。

本環境建議採 **三個 worker 輪替四個 Workstreams**。WS4 可先提供 acceptance contract，釋放名額讓 WS1–WS3 並行，最後再獨立收斂。

若要求四個 Subagents **同時**工作且 Main 專職整合，需至少五個同時活動名額；目前不可假設具備。

## 10. Recommended Assignment and Ownership

以下檔案配置是未來提案，**沒有建立任何 implementation／test／harness 檔案**。

| Workstream | Objective／deliverables | Relevant source／tests | Dependencies／permissions | Complexity／completion |
|---|---|---|---|---|
| WS1 | 十案 matrix、fixture registry、獨立 negative tests | `scenario_comparison.py`、SC／AC | 核准 fixtures、test-only 檔案及執行範圍 | Medium–High；每案有 layer、oracle、safe fixture、明確 verdict |
| WS2 | Chart／toolbar harness、performance probes | Dashboard charts、`comparison_io.py`、歷史 UAT scripts | Runtime、browser／outputs；效能 job 獨占時段 | Medium；觀察可重現或明確未重現，方法不含混 |
| WS3 | 三個候選風險的 tests-first repro、engine guard allowlist | Loader／state／priority、相關 regression families | 新獨立 tests；產品 fix 另准 | Medium；風險被證實或排除，不做推測修復 |
| WS4 | Integration protocol、CSV/evidence verifier、acceptance matrix | WP1 helpers、WP2 exports、Phase 3 verifier 設計 | 共同 fixtures 與 measurement contract | Medium；最終報告可追溯、不混用 coverage 層級 |
| Main | Shared changes、整合、資源排程、最終驗收 | Dashboard、comparison modules、既有 shared tests | 明確授權後才修改／執行 | 統一 owner，沒有互相覆寫 |

**Main 應唯一擁有：**

- `dashboard/scenario_planning_app.py`
- `src/scenario_comparison.py`
- `src/comparison_io.py`
- 既有共用 tests／fixture utilities
- Runtime bootstrap、final acceptance reporting

Subagents 未來優先各自新增、各自擁有獨立 test／harness 檔案；不共同編輯上述檔案。

## 11. Phase 1 Implementation Sequence

1. **核准執行契約**：範圍、fixtures、輸出位置、runtime、test side effects。
2. **保存工作目錄基線**：包含未提交 implementation；不能 reset／stash，也不能只用 HEAD。
3. **核准四個既有 Run 的 allowlist**，完成 loader preflight。
4. **並行建置測試**：WS1 fixtures／oracles、WS2 instrumentation、WS3 focused repro；WS4 verifier 可同步設計。
5. **Main review repro**：只將證實問題提出最小修復；沒有證據則保留 observation。
6. **如獲修復授權**，Main 整合 shared changes，再跑 targeted regressions。
7. **Source freeze barrier**：完成後才執行共同 browser acceptance。
8. **依 G00–G13 驗收**，保留 failed attempts 與 NC。
9. **最後完整性檢查與報告**；不自動進入 UX、Bilingual UI 或新能力開發。

## 12. Required Fixtures and Test Data

優先順序：

1. **既有 R-PRIMARY／R-SYN／R-ZERO／R-REJECT**：唯讀使用，不改 manifest／artifacts。
2. **In-memory ComparisonInput variants**：適合 priority、units、coverage、zero denominator 的 pure contract tests。
3. **Test-only UI fixtures**：僅用於 browser presentation；明確標示未通過 production loader。
4. **Disposable invalid-file fixtures**：若需真實 loader corruption/path/type E2E，必須另行授權建立；不得修改原 Run。
5. **完整 hand-calculated fixtures**：若要關閉 inventory-covered／opening-origin 等 E2E 缺口，需完整一致的資料與 oracle；不能任意改單一 output 欄位。

不建議為了補測而修改 Scenario Generator、優先政策、KPI 定義或新增產品控制項。

## 13. Risk Register

| Risk | 等級 | 控制 |
|---|---|---|
| 只用 acceptance HEAD 重建環境，遺失 dirty implementation | High | 使用已核對 bytes／hashes；不假設 fresh worktree 等價 |
| Test setup 隱藏 planning／Run writes | High | 方法＋class＋fixture side-effect allowlist |
| 評估時沒有原 Streamlit services | Execution blocker | 另准受控啟動；不沿用歷史 health |
| 多人編輯 dashboard／comparison shared files | High | Main 單一 owner，整合 barrier |
| Mock／unit coverage 被誤標 E2E PASS | High | 逐 case 記錄 layer、fixture、loader path |
| UI cache／export optimization 引入 stale context | Medium | 如有量測需求才考慮；完整 hash/scope key 與 cross-Run tests |
| D03／payload stage instrumentation 含混 | Medium | 分方法／方向／generation identity；保留歷史證據 |
| `tmp/` 被忽略，fixtures／evidence 不隨 clone 保存 | Medium–High | 日後另准 evidence archive；hash 不能取代檔案內容 |
| USER_DATA／SYNTHETIC_EXAMPLE 被誤稱真實 production data | Scope risk | 保留原 classification caveat |

## 14. Required Decisions and Authorizations

尚需明確決定：

1. 是否允許建立 `docs/phase_1/` 並保存正式文件版本。後續直接保存本報告至 `tmp/` 的授權不等於此項授權。
2. 未來允許新增哪些 test／harness／fixture 檔案。
3. 是否核准 R-SYN、R-ZERO、R-REJECT 加入測試 allowlist。
4. 是否允許新的獨立 evidence root，例如 `tmp/phase_1_reliability/<execution-id>/`，不得覆寫舊目錄。
5. 現有服務不存在時，允許如何受控啟動，以及指定 port。
6. 是否允許 pure in-memory engine simulation regression；仍不等於允許 persisted planning／publishing。
7. 無現成資料的 cases，接受分層 coverage，或另准完整 static／invalid fixtures。
8. 哪些必要 browser／keyboard gates 必須通過；warning／效能是否需要硬門檻。
9. 產品修復應在 focused repro 成立後，另行明確授權。

## 15. Final Recommendation

**Phase 1 已具備進入實作規劃的證據基礎，但尚未具備直接開跑的授權與 runtime 前置條件。**

建議先批准「fixture allowlist＋test-only 檔案／outputs＋runtime＋驗收分層」，優先處理：

1. 以既有 Runs 補 SYNTHETIC、zero-pool、unpublished rejection coverage。
2. 為 malformed manifest、Run-switch display、非法 priority 建立 focused tests。
3. 改善 toolbar／chart measurement，再決定是否需要產品修復。
4. 維持原 CSV contracts，先量測再考慮效能修改。

**原評估沒有新增 PASS、修改任何檔案、執行 UAT／planning、stage／commit／push，亦未開始 UX、Bilingual UI、WP3 或其他開發。後續僅依使用者要求新增本 Markdown 保存報告，未重跑評估。**
