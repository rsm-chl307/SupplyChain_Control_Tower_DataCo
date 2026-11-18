# Supply Chain Copilot — MVP Acceptance Report

**MVP Acceptance: PASS WITH LIMITATIONS**
驗收彙整日期：2026-11-18（UTC）。適用於指定的既有 USER_DATA Published Run、已測試的 WP1／WP2 功能與整合範圍；不代表所有資料模式、負向情境或寫入流程皆已通過 browser acceptance。

本文件記錄驗收判定與邊界；可重現識別、歷史 worktree status 與 SHA256 清單見 [MVP Acceptance Baseline](MVP_ACCEPTANCE_BASELINE.md)。本次只新增這兩份文件，未重跑 UAT、修改產品或改寫原始證據。

## Contents

1. [Executive Summary](#1-executive-summary)
2. [Accepted MVP Scope](#2-accepted-mvp-scope)
3. [WP1 Acceptance Summary](#3-wp1-acceptance-summary)
4. [WP2 Acceptance Summary](#4-wp2-acceptance-summary)
5. [WP1 / WP2 Integration Results](#5-wp1--wp2-integration-results)
6. [UAT Execution Summary](#6-uat-execution-summary)
7. [Data and Export Integrity](#7-data-and-export-integrity)
8. [Known Limitations](#8-known-limitations)
9. [Open Observations](#9-open-observations)
10. [Excluded Scope](#10-excluded-scope)
11. [Final Acceptance Decision](#11-final-acceptance-decision)

## 1. Executive Summary

這是一個 rule-based、deterministic、scenario-based 的供應鏈規劃決策支援 MVP。已驗收的重點是讀取既有規劃結果、調查觀察到的風險、比較情境取捨，以及追溯資料與 evidence；不是 production APS、ERP replacement 或因果推論系統。

最終 Phase 3 共 **47 cases：37 PASS、0 FAIL、0 BLOCKED、10 NOT COVERED**。其中 23 個 browser cases、12 個 independent data checks、2 個 telemetry／integrity checks 為 37 個通過案例；另有 **3 項 focused Python selector regression tests passed**，分開計數。歷史完整 suite **227 passed、0 failed、0 skipped**，沒有在 Phase 3 或本次文件整理時重跑。

主要功能與資料一致性通過；10 個 browser coverage 缺口及非阻斷 observations 保留。因此最後結論為 **PASS WITH LIMITATIONS**，而非所有可能情境皆通過。[Phase 3 results](../tmp/wp2_browser_uat_phase_3/test_results.json)、[integration results](../tmp/wp2_browser_uat_phase_3/integration_results.json)。

## 2. Accepted MVP Scope

| 能力 | 已接受範圍 | 證據邊界 |
| --- | --- | --- |
| 既有 Dashboard／Risk views | Scenario Overview、Scenario Comparison、Capacity Allocation Detail、Planning Risk Summary 與 Product／Plant／Scenario Risk rendering | Phase 1／Batch 1 與 Phase 3 代表性 browser regression；未重新執行 planning |
| WP1 Root Cause Investigation | 兩條調查路徑、篩選、native-grain evidence、provenance 與 CSV | 同一既有 Run 的已測 key；觀察不是已驗證因果責任 |
| WP2 Scenario Trade-off Analysis | 明確 Reference／Candidate、fixed reference cohort、ALL／SELECTED／COMPLEMENT、KPI／Delta、comparability、POLICY_CONTRAST | 同一完整 sequential_v1 Published Run；非跨 Run 比較 |
| WP1／WP2 Integration | 一般分頁狀態保留、明確 side/product handoff、共同 Run／artifact identity | 不假設額外 WP1→WP2 deep link |
| Evidence／Exports | WP1 native evidence 與 WP2 四種 CSV 的實際下載、parse、context 與 hash 核對 | 沒有以按鈕存在取代下載成功 |
| P2-UI-01 修復 | invalid Candidate 的可見值與 ARIA 清空、必須手動重選、後端 gate 保留 | 原失敗保留；修復後 A01–A08 真實 browser 重驗通過 |

規格依據為 [WP2 Implementation Specification v1.0](wp2_scenario_tradeoff_analysis_specification.md)、[WP2 progress](wp2_implementation_progress.md) 與 [project journal 的 WP1 完成紀錄](scenario_planning/project_journal.md)。獨立的 Root Cause Investigation specification 檔案未找到；沒有捏造 WP1 規格版本。歷史文件的命名歧義見 §9。

## 3. WP1 Acceptance Summary

Phase 3 實際驗證：

- Product → Plant → Week：`Baseline / SKU-A / PLANT-1 / 2017-01-15`。
- Plant → Week → Product：`Baseline / PLANT-2 / 2017-01-22 / SKU-C`。
- 額外切至 `SKU-D / PLANT-2 / 2017-01-08`，再還原 SKU-C／2017-01-22。
- 展開 selected-week、shared-capacity、performance、initial-state evidence，以及來源 provenance／assumptions。
- 下載 12 份 WP1 evidence CSV；涵蓋兩條路徑、adjacent weeks、allocation peers、eligibility ledger、source status 與兩側 handoff。

四組 selected-week native fields、原始 artifact、實際 browser Arrow payload 與下載值一致；shared capacity 保持單一 plant-week pool，沒有因產品引用而重複。Investigation_* context 與 Evidence_Artifact 保留，不改變原資料 grain。來源 hash/status 與 manifest 相符。[獨立資料檢查及整合結果](../tmp/wp2_browser_uat_phase_3/integration_results.json)。

WP1 提供的是 published simulation observations，不構成因果歸因、order-level backlog aging 或已驗證的真實現場事件證據。

## 4. WP2 Acceptance Summary

P2-UI-01 最初在 Phase 2 A04 失敗：Reference 改成原 Candidate 後，後端要求重選，但畫面仍保留舊值。另行授權的 UI fix 將 invalid Candidate 從 `pop()` 改為明確 `None` assignment，以傳送 frontend clear；未改比較計算。修復前後測試、截圖與增量 diff 保留於 [Fix report](../tmp/wp2_browser_uat_phase_2_fix/FIX_REPORT.md)。

Fix validation 與 Phase 3 都實際重驗 A01–A08：初始空選擇、正常 pair、排除 Reference、invalid Candidate 清空、相同情境阻擋、反向 Delta、Run identity、Comparison Context。使用者手動重選後可產生比較；不能只以 AppTest 宣稱修復成功。

已測試的主要 pairs：

| Reference | Candidate | 驗證重點 |
| --- | --- | --- |
| Baseline | Combined_Stress | 正常比較、Priority 3 cohort、四種 CSV |
| Combined_Stress | Baseline | 反向數值與 Candidate − Reference Delta |
| Combined_Stress | Combined_Stress_Lost_Sales | POLICY_CONTRAST、DESCRIPTIVE_ONLY、沒有錯誤 Winner／service 改善宣告 |

指定 Run 可見五個 scenarios：`Baseline`、`Demand_Surge`、`Capacity_Disruption`、`Combined_Stress`、`Combined_Stress_Lost_Sales`。前兩個單獨 stress scenarios 出現在既有 Scenario Comparison rendering，**沒有宣稱其所有 pair permutations 都完成 browser functional acceptance**。

Priority 3：SELECTED=`SKU-A`，COMPLEMENT=`SKU-B, SKU-C, SKU-D`；四個產品 priority-change count=0。原 Run 的 priorities 跨 scenarios 相同，非零 Candidate priority-change browser 行為仍 NOT COVERED。空 Selected／Complement 的 BLOCKED／N/A 行為於 Phase 2 驗證；沒有將其誤報為真正 zero-demand fixture。

以下為 Baseline → Combined_Stress 的 ALL checkpoint；完整精度與 independent native CSV／Decimal 檢查見 [Phase 3 integration results](../tmp/wp2_browser_uat_phase_3/integration_results.json)。

| Metric | Reference | Candidate |
| --- | ---: | ---: |
| Horizon Service Level | 0.4102564103 | 0.3449883450 |
| Terminal Backlog | 23.0 | 28.1 |
| Lost Sales | 0.0 | 0.0 |
| Allocated Workload | 24.0 | 21.6 |
| Unmet Workload | 68.0 | 87.0 |

Policy contrast 的 terminal backlog `28.1 → 0`、lost sales `0 → 28.1`，horizon service 約 `0.344988345` 且近似不變。**零 backlog 不代表服務改善。** 保留描述性狀態，不合併 loss/backlog，不宣告勝出方案。

## 5. WP1 / WP2 Integration Results

- 一般 WP1→WP2→WP1 分頁切換保留原 Baseline／product／plant／week；comparison selector 不靜默改變 WP1 source scenario。
- 現有 UI 的 `Investigate Candidate in WP1`／`Investigate Reference in WP1` 經明確點擊後，分別開啟 `Combined_Stress`／`Baseline` 的 `SKU-A / PLANT-1 / 2017-01-08`。
- Handoff 不改 WP2 pair direction／priority cohort。手動改 WP1 week 至 2017-01-15，往返分頁仍保留。
- 後續 WP2 reverse／policy comparison 不經 handoff 時，WP1 仍維持 Baseline source。
- WP1 四組 Product×Plant×Week keys 落於 WP2 scope／evidence filters，兩側 Run identity 與 artifact hashes 一致。沒有新 Run 或 planning 觸發。

具體 browser cases B01–B05、derived B06 與兩側 evidence 見 [integration results](../tmp/wp2_browser_uat_phase_3/integration_results.json)。

## 6. UAT Execution Summary

各階段 scope、重跑與累計範圍不同，**不得跨階段加總成一個不重複測試數**。Phase 1 Core Application Regression 對應現有 Batch 1 報告，沒有另外捏造 Phase 1 報告。

| 階段 | 記錄結果 | 補充／原始證據 |
| --- | --- | --- |
| WP2 implementation automated acceptance／歷史 Phase 2 full suite | 227 passed、0 failed、0 skipped | [WP2 progress](wp2_implementation_progress.md)、[原始 full-suite log](../tmp/wp2_acceptance/final_full_suite.log)；不是 Browser Phase 2 的 56 cases；Phase 3 未重跑 |
| Phase A environment／smoke | PASS，限 browser 啟動、WebSocket、首頁／Run／selector smoke | [Phase A report](../tmp/wp2_browser_uat_phase_a/reports/PHASE_A_SMOKE_REPORT.md)；最初 runtime blocked／retry 記錄保留；曾獲授權安裝 11 個 runtime packages，不代表後續驗收改依賴 |
| Phase 1／Batch 1 | 7 PASS、0 FAIL、0 BLOCKED | [Batch 1 report](../tmp/wp2_browser_uat_phase_a/batch_1/reports/BATCH_1_UAT_REPORT.md)、[final results](../tmp/wp2_browser_uat_phase_a/batch_1/reports/final_results.json) |
| Phase 2 WP2 functional | FAIL；46 PASS、1 FAIL、0 BLOCKED、9 NOT COVERED，共 56 cases | [Phase 2 report](../tmp/wp2_browser_uat_phase_2/reports/PHASE_2_UAT_REPORT.md)、[results](../tmp/wp2_browser_uat_phase_2/reports/test_results.json)；28 supporting Python tests passed，另計；唯一功能失敗 P2-UI-01 |
| Phase 2 Fix | PASS；A01–A08 為 8 PASS，另 3 focused Python tests passed | [Fix report](../tmp/wp2_browser_uat_phase_2_fix/FIX_REPORT.md)、[results](../tmp/wp2_browser_uat_phase_2_fix/test_results.json)；不改寫原 Phase 2 FAIL |
| Phase 3 integration／final | PASS WITH LIMITATIONS；47 cases＝37 PASS＋10 NOT COVERED，0 FAIL／BLOCKED | [Phase 3 report](../tmp/wp2_browser_uat_phase_3/PHASE_3_UAT_REPORT.md)、[results](../tmp/wp2_browser_uat_phase_3/test_results.json)；另 3 focused Python tests passed |

Phase 3 的 37 PASS 由 **23 browser cases＋12 independent data checks＋2 telemetry/integrity checks** 組成。其最終 D03 assessment PASS 不等於每一種輸入方式成功；D03 欄位的正確解讀見 §9。

### Material process history

| Attempt | 原始問題與處理 | 保留證據 |
| --- | --- | --- |
| SETUP-1 | `KeyError: 'result'`，發生於案例開始前；僅修正 test harness 參數後重新執行 | [initial harness error](../tmp/wp2_browser_uat_phase_3/logs/initial_harness_error.json)、[trace](../tmp/wp2_browser_uat_phase_3/traces/initial_harness_trace.zip) |
| D03-FIRST | Data mode 移除 stVegaLiteChart，截圖 locator 因而失效；僅用 stable toggle locator 定向 retry | [原始 browser results](../tmp/wp2_browser_uat_phase_3/browser_results.json)、[失敗截圖](../tmp/wp2_browser_uat_phase_3/screenshots/D03_failure.png)、[retry results](../tmp/wp2_browser_uat_phase_3/toolbar_retry_results.json) |
| DATA-FIRST | Verifier 過度要求 reverse payload 必須標記 A06；數值 assertions 已通過，實際 payload 在 A04 手動重選時送出。校正 stage attribution 後通過 | [initial data validation](../tmp/wp2_browser_uat_phase_3/logs/initial_data_validation.json)、[最終 data checks](../tmp/wp2_browser_uat_phase_3/integration_results.json) |

這三項是 test-harness／verifier 問題，**不是 Phase 3 產品修復**。原失敗 attempts 與後續成功 retries 皆保留，未刪除或改寫。

## 7. Data and Export Integrity

唯一 final acceptance Run：`sequential_20261117T133913_e22d0f430e98`，schema `sequential_v1`，Run classification **USER_DATA**。來源 metadata 仍含 **SYNTHETIC_EXAMPLE**；此差異未解決。**不能描述成已獨立驗證的真實營運／production data。** [原始 manifest](../tmp/user_data_acceptance_2026-11-17/runs/sequential_20261117T133913_e22d0f430e98/run_manifest.json)。

Phase 3 實際下載 16 份 CSV：12 WP1＋4 WP2。WP2 metrics、cohort_membership、evidence_refs、context 各下載一次且可 parse，與 Phase 2 Fix 對應輸出 byte-identical；沒有重複下載大量 reverse／policy CSV，改以實際 browser Arrow payload 核對。

- 36 metric rows 的複合 key 唯一；4 個 cohort product IDs 唯一。
- 24 個 evidence references 的 Side×Artifact keys 唯一；兩側引用相同 artifact 是預期。
- Path、hash、native grain、scope/filter、source provenance、Run／Scenario／Comparison Context 一致，沒有 evidence fanout。
- Weighted service、terminal endpoint backlog、workload quantities 與 delta 定義按原始 artifacts 獨立計算，不用待驗 production function 當唯一 oracle。

Phase 3 原始 [final integrity JSON](../tmp/wp2_browser_uat_phase_3/final_integrity.json) 確認：

| 項目 | 原始驗證結果 |
| --- | --- |
| HEAD before／after | 相同：`4b6c84d99173f2472de7a973c1ca98c3a4b15ec2` |
| Git status before／after | 逐字相同；worktree 原本 dirty，並非 clean |
| Protected existing files | 134 checked，0 changed |
| Published Run files | 13 checked，0 changed |
| Artifact SHA256 | 12／12 matched manifest |
| Run count | 53 → 53，manifest paths 集合相同 |
| Streamlit | PID 1117256／1503434 不變；8501／8502 health HTTP 200 |
| git diff --check | Return code 0 |
| Phase 3 變更／操作 | 無 source／tests／specifications／user guides 修改；無新 Run、planning、upload、publishing、dependency changes、service restart、commit／push |

以上是已保存的 Phase 3 歷史驗證，並非本次重新探測服務。沒有查驗遠端狀態，不宣稱 branch 與 remote 同步。各證據完整性與 acceptance worktree 指紋見 [Baseline](MVP_ACCEPTANCE_BASELINE.md)。

## 8. Known Limitations

以下十項保留 **NOT COVERED**，不因已有 pure-Python/helper assertions 而改為 browser PASS。原因是 approved Phase 3 scope 僅使用指定 Run，或沒有可安全使用且不產生／修改 Run 的 browser fixtures。

| ID | 未覆蓋情境 | 原始限制 |
| --- | --- | --- |
| NC-B09 | Non-zero Candidate Priority changes 與 browser cohort membership | 主 Run priorities 相同；歷史 in-memory test 不等於 browser 驗證 |
| NC-N01 | Missing／invalid priority | 有歷史 pure-test memory variants，沒有 browser fixture |
| NC-N02 | Genuine zero-demand denominator | 原 Run cohorts 有正需求；空 cohort 不等於真正 zero-demand |
| NC-N03 | Zero-capacity pool | 有安全 helper assertions，沒有 WP2 browser／horizon fixture |
| NC-N04 | Fully inventory-covered demand | 有 zero-requirement helper，沒有完整 browser／horizon fixture |
| NC-N05 | Non-zero opening backlog | 有 inventory-origin helper；完整 fixture 會生成 Run，未執行 |
| NC-N06 | Incompatible unit／factor | 歷史 memory-only assertions，不是 browser fixture |
| NC-N07 | Missing product／week／endpoint | 歷史 memory-only assertions，不是 browser fixture |
| NC-N08 | Corrupted／unpublished Run | In-memory manifest checks 不等於 filesystem loader browser 測試；未寫 copied Run |
| NC-SYNTHETIC | Current Phase 3 SYNTHETIC_DEMO browser acceptance | 本階段僅准指定 USER_DATA Run；歷史另一模式測試不算本次驗收 |

來源：[Phase 3 case register](../tmp/wp2_browser_uat_phase_3/test_results.json)。未建立或變造 Run 補測；不擴張至 cross-Run、sub-horizon service 或未支援 scenario comparisons。

## 9. Open Observations

### P3-OBS-01 — Vega Infinite Extent Warnings

**OPEN／non-blocking。** 原始 Phase 3 session counts：main **83**、toolbar_retry **69**、initial_harness_setup **35**；主驗證＋retry＝**152**，含 setup attempt＝**187**。各 session console errors、page errors、failed requests 均為 0。沿用 Batch 1 rendering／finite-data 調查，不代表所有圖表情境皆無害；未 suppress 或改 chart code。[原始 telemetry](../tmp/wp2_browser_uat_phase_3/logs/browser_telemetry.json)。

### P3-OBS-02 — Chart Toolbar Interaction / D03 Correction

原始 [D03 machine-readable result](../tmp/wp2_browser_uat_phase_3/toolbar_retry_results.json) 與 [final test results](../tmp/wp2_browser_uat_phase_3/test_results.json) 記錄：

```json
{"mouse_success": true, "keyboard_success": false, "chart_restored": true}
```

正確解讀：**滑鼠互動在測試的 1600×1100 viewport 成功；依 machine-readable record，鍵盤互動未成功（keyboard_success=false）；chart_restored=true 只確認圖表已恢復，不能由此判定恢復方法。** 不宣稱鍵盤恢復成功，也不宣稱所有 viewport 的既有 toolbar 問題已排除。

歷史 Phase 3 report／先前敘述曾稱 keyboard Show chart restoration 成功，與上述欄位不一致。**本整併文件以 machine-readable evidence 為準，明確保留差異；原 report、script、screenshots、logs、trace 不改寫。** 最終 D03 PASS 是 observation assessment 的結果，不能轉換成 keyboard acceptance PASS。原 mouse obstruction 在本次 viewport 未重現，舊觀察仍保留。

### P3-OBS-03 — Wide Tables and Large CSV

**OPEN／non-blocking usability observation。** 寬表需要水平捲動；代表性 metrics CSV **6,866,365 bytes，約 6.9 MB**。已成功下載，不因檔案大小減少 evidence 或更改 export contract。[Download manifest](../tmp/wp2_browser_uat_phase_3/download_manifest.json)。

### P3-LIMIT-02 — Historical WP1 Naming Ambiguity

本次已接受的 WP1 是 **Root Cause Investigation**。歷史 [WP1_validation.md](improvement_program/work_packages/WP1_validation.md) 是另一個 proposed Independent Validation Layer，不能當成本次已接受功能或規格。獨立 Root Cause Investigation spec 版本未找到；使用 project journal 完成紀錄與 approved WP2 integration requirements，不捏造版本。

## 10. Excluded Scope

本次 acceptance 不包含以下能力或操作：

- WP3／新功能開發、AI／LLM recommendations、optimization、preferred-action／winner ranking、canonical replay、cross-Run comparisons。
- 新 scenario generation／what-if controls、business rule／engine／schema 變更、Power BI 改版或 bilingual UI 實作。
- 在 Phase 3 執行 planning、publishing、upload、建立 Run；這些寫入路徑未重新 browser 驗收。歷史 upload regression 不等於本次執行。
- Production-grade APS／ERP、真實營運來源分類認證、所有 browser／viewport／data mode／scenario permutations。
- Commit／tag／push、remote synchronization 或 deployment。本次「freeze」是驗收文件與指紋基線，不是 Git history 操作。

## 11. Final Acceptance Decision

**MVP Acceptance: PASS WITH LIMITATIONS**，登錄日期 **2026-11-18（UTC）**。已測必要 WP1／WP2／整合能力正常，P2-UI-01 修復後 browser regression 通過，沒有未解決的重大功能／資料一致性失敗；十項 NOT COVERED 與 OPEN observations 不抹除。

可將 [MVP Acceptance Baseline](MVP_ACCEPTANCE_BASELINE.md) 作為後續變更審查的正式文件基準。它結合固定 HEAD、實際 dirty-worktree 指紋、原 Run／artifact hashes 與證據；**單獨 checkout HEAD 不足以重現被驗收的未提交功能**。

目前 `.gitignore` 忽略 `tmp/`，證據仍在本機，不能假設會隨 Git clone／push 保存。若需跨環境或長期可取得的證據封存，應另行授權保存完整 worktree／UAT／Run archive 並核對本基線 hashes；本次未搬移檔案、改 ignore 規則或聲稱已遠端封存。此為後續保存建議，不影響本機證據已找到的事實。

完成本次文件交付後停止，等待使用者審查；不開始下一開發階段。
