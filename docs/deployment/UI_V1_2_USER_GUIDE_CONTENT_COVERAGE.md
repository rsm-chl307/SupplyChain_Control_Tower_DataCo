# UI V1.2 使用手冊功能盤點與內容覆蓋矩陣

## 1. 盤點基準

- App：`dashboard/scenario_planning_app.py`
- 顯示翻譯：`dashboard/i18n.py`、`dashboard/display_metadata.py`、`dashboard/locales/en.json`、`dashboard/locales/zh-TW.json`
- 行為與資料契約：`docs/planning_csv_inputs.md`、`docs/PRODUCT_CAPABILITY_CATALOG_EN.md`、`docs/wp2_scenario_tradeoff_analysis_specification.md`
- 使用者文件：`docs/USER_GUIDE_EN.md`、`docs/USER_GUIDE_ZH-TW.md`
- 既有測試：`tests/test_dashboard_app.py`、`tests/test_phase2_workflow.py`、`tests/test_dashboard_upload_workflow.py`、`tests/test_comparison_dashboard.py`、`tests/test_phase2_i18n.py`

盤點只記錄 App 目前入口及已實作行為。已延期、未接通或受資料限制的能力均列為限制，不當作可用功能。

## 2. Capability inventory

| 功能 | 使用目的／入口 | 必要輸入與前置條件 | 操作及預期輸出 | 限制／已知問題 | 現有文件涵蓋 |
|---|---|---|---|---|---|
| Dashboard | `Planning model → Legacy independent weeks`；Scenario Overview、Scenario Comparison、Capacity Allocation Detail | Legacy processed input／輸出存在；日期期間及 disruption plant 可用 | 選情境讀 KPI 卡、圖表及摘要；切換 Scenario；在 allocation 明細選 Plant | 舊版依週獨立計算；Service_Level 是 allocation coverage，不是 Sequential service level；輸出目錄已存在時 Run 會停用以保護資料 | V1.2 App 手冊及 Legacy 輸出保護 AppTest |
| Sequential Planning | 預設 `Sequential workload` → `Upload CSV data` 或 `Use existing JSON configuration` | CSV 固定必填 Products、Plants、Product-to-plant mapping、Demand；其他資料集須提供或明確選擇合法假設。JSON 必須符合既有契約 | Validate inputs → READY/BLOCKED；獨立按 Validate and run planning 建立 Published Run；選擇情境檢視週趨勢、KPI、明細 | 不產生預測；明確輸入需求／資格／庫存／欠單／係數／產能；CSV calibration recipe 已接上 adapter 頂層契約並經 synthetic adapter READY 測試；runtime 儲存限制仍適用 | V1.2 App 手冊涵蓋操作步驟及限制 |
| Legacy independent weeks | 模型選單；Sidebar 的期間、surge、capacity disruption、plant 和執行按鈕 | Legacy processed data；範圍內 Snapshot／Scenario inputs | 執行 Baseline、Demand Surge、Capacity Disruption、Combined Stress 舊版比較 | 不承接跨週 inventory/backlog；數量產能，不是 workload capacity；輸出和 sequential Run 不可混用 | 有模型描述；UI 操作及 KPI 對照待補 |
| CSV upload／templates | Sequential Planning → Upload CSV data；Download CSV templates | 10 個 dataset uploader、9 個 CSV 範本；Products、Plants、mapping、Demand 固定必填 | 選 WEEKLY／ORDER_LINES；上傳 CSV；檢視 preview／status；下載範本 | 檔案留在記憶體，執行時短暫落盤；缺少 optional input 需合法 explicit assumption；ORDER_LINES completeness assertion 現在不受 status 分類分支影響 | V1.2 App 手冊涵蓋資料欄位、映射與限制 |
| Column mapping／readiness | CSV form → Column mapping、source classification、Validate inputs | Header/data rows 可讀；canonical required fields；所有 demand status 有分類，或明確聲明 WEEKLY 已 qualified | 對應來源欄位；看 READY/BLOCKED、錯誤、來源、假設、derived values | 欄位對應不能重複；來源資格是使用者聲明／設定，不代表歷史事實；沒有驗證前不建 Run | 舊指南已有流程但缺詳細故障排除 |
| Published Run loading | Sequential sidebar → Published sequential run folder | 已發布 Run folder；manifest、Run identity、artifact hash／schema 合格 | 貼路徑載入；選 Scenario；顯示 KPI、pool、allocation、Risk、Trade-off tabs；下載三個輸出 | 載入不執行規劃；絕對／相對路徑依 repository root；來源原檔可能 unavailable，但 published evidence 仍可用 | 有基本步驟；驗證及資料持久性限制待補 |
| KPI、charts、tables | Dashboard 與 Sequential 結果 tabs | 有符合契約的輸出 | KPI cards、Scenario summary、plant-week pool、allocation detail、time-series chart | 需按各自 grain 解讀；期末存量不是跨週流量；Plotly 缺少時部分圖表轉為文字摘要 | 定義主要在 catalog；用戶向 glossary 待補 |
| WP1 Root Cause Investigation | Sequential → Planning Risk Summary → Root Cause Investigation；可由 Product Risk／Plant Bottlenecks 導入 | 可載入 Run、調查索引及所需 evidence | 選 product／plant／week／scenario；檢視相鄰週、共享 plant-week pool、來源、佐證；按 artifact 下載 | 同時出現不表示因果；每 artifact 按 native grain；不完整來源／hash mismatch 不可當作新 evidence | 有章節；需更易讀說明 grain、shared capacity 與 missing source |
| WP2 Scenario Trade-off Analysis | Sequential → Scenario Trade-off Analysis | 必須明確選 Reference、Candidate；同一 loaded Run 有 scenario scope；Reference priority cohort 可選 | 比較 ALL／SELECTED／COMPLEMENT，查看 KPI、Delta、優先序差異、comparability reasons、context；可 handoff WP1 | Candidate − Reference；服務指標用百分點；BLOCKED／DESCRIPTIVE_ONLY 需讀原因；不推薦最佳行動 | 已有規格及舊指南章節，需對齊現有操作順序 |
| Evidence／downloads／exports | Run downloads；WP1 evidence；WP2 四類 comparison exports；CSV templates | 對應 Run／comparison context 可用 | 下載 `performance_result.csv`、`allocation_result.csv`、`run_manifest.json`、WP1 evidence、WP2 CSV exports | machine values、headers、IDs 不隨語言改變；使用者上傳資料和 Cloud runtime 不保證永久保存 | 有零散說明；命名與用途待合併 |
| Navigation／language | 頂端全域語言選擇器；model selector；Sequential tabs | `ui_locale` = `en`／`zh-TW` | 切換 UI 文案；以既有控件切換模型／結果頁 | 不翻譯身份、欄名、狀態值、數據和匯出；locale 不是另一個獨立狀態 | V1.1 說明已更新，但既有兩份指南仍有舊操作 |

## 3. 現有使用者文件差距

- 兩份既有指南包含 Planning、WP1、WP2 及資料／KPI 的大量內容，可作為來源；但仍含 V1.1 前語言操作與早期 UI 狀態敘述。
- 使用手冊需以目前入口和 UI labels 重組，尤其是兩種 Planning model、必填／選填 dataset、欄位映射、READY/BLOCKED、Published Run path、WP1 native evidence grain、WP2 comparability。
- 完整指標定義以 Capability Catalog 及 KPI implementation 為準；Legacy `Service_Level` 不得等同 Sequential `Horizon_Service_Level`。
- Capacity calibration CSV checkbox 為已知 wiring limitation；手冊要明確指出不能用此 checkbox 取代 capacity CSV。

## 4. V1.2 完整手冊章節覆蓋

| Stable section ID | English / zh-TW | What / when / inputs / steps / outputs / interpretation / mistakes |
|---|---|---|---|
| `system_overview` | System Overview / 系統介紹 | 產品定位、角色、工作流程、模型差異、狀態與限制 |
| `dashboard` | Dashboard / 營運總覽 | 三個 tab、情境／工廠選擇、Legacy KPI、圖表與常見誤讀 |
| `planning` | Planning / 規劃作業 | 模式、資料集及欄位、預設／範圍、假設、READY、Run、輸出和限制 |
| `wp1` | WP1 Root Cause Investigation / 根因調查 | 入口、selection、evidence grain、解讀、下載與因果限制 |
| `wp2` | WP2 Scenario Trade-off / 情境取捨分析 | Reference/Candidate、cohort、Delta、comparability、handoff、exports |
| `data_reports` | Data Management and Reports / 資料與報表 | CSV、Published Run、identity、資料保存、downloads、命名 |
| `kpi_glossary` | KPI and Terminology / KPI 與詞彙 | canonical KPI 定義、grain、單位、例子、legacy 差異 |
| `troubleshooting` | Troubleshooting and FAQ / 常見問題 | 缺檔、CSV／mapping、readiness、執行、Published Run、WP1/WP2、語言 |

## 5. 驗證結果

- 兩份手冊均包含上述八個固定 section ID 及非空 subsections；定向內容測試 PASS。
- AppTest 驗證目錄導覽、active section、locale switching 保留目前 section、open/close 與 pending CSV／Planning form state；PASS。
- AppTest 驗證 guide 操作不呼叫 planning functions；PASS。
- ORDER_LINES status 值存在時完整擷取 assertion 可見；PASS。
- Capacity calibration UI config 送至 adapter 的頂層契約，synthetic fixture readiness 為 READY；PASS。
- Legacy 預設既有輸出目錄顯示警告且停用 Run；PASS。
- 45 項定向及相關既有回歸測試全部通過。
- 真實瀏覽器的響應式版面、鍵盤操作及截圖驗收未執行；PARTIAL，原因是環境沒有 browser automation package 或 browser binary。AppTest 不作為瀏覽器驗收替代證據。
