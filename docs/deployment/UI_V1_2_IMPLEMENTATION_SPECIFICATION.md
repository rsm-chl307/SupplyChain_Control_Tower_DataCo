# UI V1.2 實作規格：易用性與使用者指南

## 1. 目的與邊界

建立跟隨既有 `ui_locale` 的英／繁中完整 App 使用手冊，並改善 Planning、Dashboard、WP1、WP2 的使用者文案。只修改呈現、導覽、說明與文件；不更動規劃／分配／KPI／風險／比較計算、canonical 欄位、machine values、輸出契約或歷史資料。

## 2. 開發基線

- Repository：`/workspace/SupplyChain_Control_Tower_DataCo`
- Branch：`main`
- HEAD：`6e451b9660dd3be09e632e10ff8698b39a267b07`
- Index：空白
- 開始時既存工作：修改中的 V1.1 檔案 `dashboard/scenario_planning_app.py`、兩份 dashboard locale、`tests/test_phase2_workflow.py`；10 個修改中的 tracked `.pyc`；未追蹤的 deployment、diagnostics、Phase 1 forensic 與 V1.1 報告。以上皆為使用者既有工作，V1.2 不覆蓋、不清理、不 stage。
- Deployment Repository、GitHub、Cloud：本階段不存取、不修改。

## 3. 功能盤點摘要

| Capability | 現況與入口 | 主要前置條件／輸入 | 結果與限制 | 既有文件涵蓋 |
|---|---|---|---|---|
| Dashboard | `Legacy independent weeks` → Scenario Overview、Scenario Comparison、Capacity Allocation Detail；側欄日期、需求增加、產能減少、工廠設定可執行舊版規劃 | 可讀取的 processed input/output；Plant 選項來自 planning snapshot | KPI 卡片、圖表、表格；Legacy 數量分配語意不等同 Sequential 服務 KPI。已存在的日期輸出資料夾會停用 Run，以保護既有檔案 | 舊指南有 Dashboard 說明，但入口和部分語言說明過時 |
| Planning — Sequential workload | 預設模式；CSV 或 JSON 設定；載入 Published sequential Run | 明確的需求資格、需求資料、產品／工廠關係、工作負荷、期初狀態、產能／到貨或明確允許的假設 | 逐週狀態承接；不自動預測需求；輸出 Published Run 與 KPI／明細 | `docs/USER_GUIDE_*`、`docs/planning_csv_inputs.md` 及 Capability Catalog 有覆蓋，尚未集中為 App 手冊 |
| Planning — Legacy independent weeks | 側欄模型選單；日期、surge、disruption、plant；執行 `run_planning` | Legacy processed source | 各週獨立分配，不承接跨週庫存／欠單；Legacy KPI 不可視為 Sequential service KPI | 指南有敘述但須強化差異及限制 |
| CSV intake / mapping | Planning → Upload CSV data；WEEKLY／ORDER_LINES；10 個 dataset uploader、9 個 CSV 範本；欄位映射；來源資格與假設 | Products、Plants、Product-to-plant mapping、Demand 固定必填；其餘資料須提供或明確選擇可用假設 | READY/BLOCKED、來源／假設摘要；只有獨立 Run 按鈕執行規劃；status-free weekly 與 order-line 完整擷取有額外聲明 | README 與舊指南有步驟，但需補全各資料集欄位與邊界 |
| Published Run loading | Sequential sidebar 貼上 Run folder path，讀取 `run_manifest.json` | 已發布的 sequential Run，必要 artifacts 與 hash／schema 合格 | KPI、每週趨勢、明細、WP1、WP2；不會因載入本身執行規劃 | 舊指南有說明，需補充路徑、manifest 驗證與下載內容 |
| KPI / charts / tables | Dashboard 三個 tab；Sequential 五個結果 tab 與指標卡 | 可載入的完整輸出 | Native grain 不同；期末存量不可跨週加總；某些分母為 0 時顯示 N/A | Capability Catalog 定義完整，使用者指南說明不完整 |
| WP1 Root Cause Investigation | Sequential → Planning Risk Summary；產品／工廠風險訊號可帶入 Investigation tab | 可載入 Run 及其調查所需證據 | 同時觀察的模擬訊號不是因果歸因；證據按原生粒度獨立篩選；來源缺失可能顯示 unavailable | 舊指南覆蓋，但需解釋 evidence grain 和限制 |
| WP2 Scenario Trade-off Analysis | Sequential → Scenario Trade-off Analysis | 使用者明確選 Reference、Candidate 與 Reference priority cohort；候選／參考須可比較 | Candidate − Reference；Delta 單位依指標而異；會顯示 comparability reasons；不推薦最佳行動 | 舊指南內容豐富，需整理成操作手冊並與當前 UI 對齊 |
| Evidence / downloads | Published Run CSV / JSON downloads；WP1 evidence downloads；WP2 comparison exports | 對應 Run／比較範圍有效 | 匯出保留機器欄位與 ID；WP2 有 comparison context、cohort、evidence references 等多項匯出 | 既有指南有涵蓋，需合併避免重複與過時說明 |
| Navigation / language | `ui_planning_model`、Sequential tabs、全域 `ui_language_request`；V1.1 全域語言 selector | `ui_locale` en／zh-TW | 頁面文案隨 locale 切換；內部值與匯出不翻譯 | 舊指南語言操作過時；V1.1 報告有最新設計 |

完整內容覆蓋矩陣見 `UI_V1_2_USER_GUIDE_CONTENT_COVERAGE.md`。

## 4. 指南 Center 架構

- `dashboard/user_guide/guide_navigation.py`：固定 section IDs 與雙語標題；ID 不以翻譯標題產生。
- `dashboard/user_guide/guide_content.py`：讀取、剖析、驗證 locale Markdown；缺少內容時回報明確錯誤。
- `dashboard/user_guide/locales/en.md`、`zh-TW.md`：八個穩定 section IDs、章節及可折疊 subsections。
- User Guide Center 使用 Streamlit 原生 `columns`、`button`、`expander`、Markdown anchor；無新依賴與自訂前端框架。
- 全域右上入口沿用 V1.1 `ui_locale`，不新增語言 selector。
- 打開／關閉指南及換章時，既有 App/Form 繼續在同一頁面 render；不以條件分支卸載 Planning Form。Guide 控制器只更改 `ui_user_guide_open`、`ui_guide_section`。

## 5. Work packages

1. **WP1.2-A — Capability audit**：比對 app、i18n、display metadata、雙語 dictionaries、User Guides、Capability Catalog、CSV input contract 與 tests；建立內容覆蓋矩陣。
2. **WP1.2-B — Complete bilingual content**：以實際 UI 與 canonical KPI 定義撰寫八章完整手冊；明確標示已知限制、缺少資料與不可用控制。
3. **WP1.2-C — Guide Center**：新增穩定 TOC IDs、section navigation、active state、expand/collapse、back-to-top、missing content 狀態；同頁保留 App/Form render。
4. **WP1.2-D — UI copy**：更新可讀標籤與 tooltip；只改 locale／presentation strings，保留機器值。
5. **WP1.2-E — Verification**：內容／locale／navigation 單元測試，AppTest 導覽與 Form no-run checks；bounded Dashboard／Planning／WP1／WP2 regressions；可用時進行真實瀏覽器驗收。

## 6. 驗收門檻與不變條件

- 8 個 section IDs 在兩種 locale 完整且唯一；subsections 非空；locale 翻譯齊全；模板格式正確。
- TOC、active section、expander、locale round-trip、back-to-top、missing-content handling 均可測。
- 規劃 Form 仍在 rerun 頁面樹內；Guide UI 事件不觸發 validation、planning、Run creation。
- 不變更 backend functions、KPI formulas、canonical schemas、identities、exports 或歷史 artifacts。
- 若無真實瀏覽器工具，瀏覽器驗收列為 PARTIAL，不以 AppTest 代替宣稱 PASS。
- 不建立 Runs，不修改既有 Runs／Published Artifacts／evidence；不 stage／commit／push。

## 7. 已知內容限制

Capability Catalog 曾指出 CSV UI 的 synthetic capacity calibration 設定位置與 adapter 不一致，且 ORDER_LINES 完整擷取聲明會被 Status 分支隱藏。WP1.2-D 以既有 adapter key 接線，並將完整性聲明移到 Status 分類之外顯示；只修正既有 UI 控制可達性／設定路由，保留原規則及計算。

Legacy Dashboard 的舊版執行輸出採日期範圍決定固定資料夾，預設的 2017 目錄已存在。V1.2 增加輸出目錄存在檢查：目標已存在時顯示雙語警告並停用 Run，未改變輸出格式或規劃計算。
