# UI V1.2.1 內容與 Planning 改善報告

## 實作結果

兩語完整手冊已逐章改寫為操作導向說明，保留八個穩定導覽 ID、既有入口、雙欄、展開、回頂端、關閉及語言同步。Planning 補充範圍在同一次任務整合，不另建專案。

## 代表性前後對照

| 修改前 | 修改後 |
|---|---|
| 沿用 App 的 ui_locale 狀態 | 點擊右上角語言選單，介面與說明同步更新 |
| Validate canonical column mappings | Check each uploaded column is matched to the correct field |
| WP1／WP2 | 根因與營運風險分析／情境比較與決策分析；Operational Risk Investigation／Scenario Comparison |
| 單週獨立分析（舊版）／Independent-week analysis (legacy) | 單週獨立分析／Independent-week analysis |
| 本次規劃設定名稱 | 為這次規劃設定命名／Name this planning setup |
| 短缺政策 | 無法滿足的需求如何處理？／How should unfulfilled demand be handled? |
| 需求增加幅度 | 假設需求增加多少？（%）；提示 100 件增加 10% 為 110 件 |
| manifest、artifact、native grain | 規劃紀錄、結果檔案、原本記錄的產品／工廠／週次 |

模型真實行為仍是連續週次承接庫存與欠單、按工廠週共享工作負荷產能；單週獨立以數量產能分週計算。保留內部 `Sequential workload`／`Legacy independent weeks` 與 routing，僅顯示名稱改變。

CSV 名稱改為產品資料、工廠資料、產品工廠對應、需求資料、供應優先順序、每週產能、每單位生產工作量、期初庫存、未完成訂單與外部到貨。需求仍依 WEEKLY／ORDER_LINES 選項區分，未錯稱所有需求皆是每週格式。固定四個必填資料集與其餘資料／假設條件未改。資料表新增下一步，已上傳則請檢查欄位與單位，缺少必填則請上傳，其餘請檢查可用假設及產品中是否已有優先順序。

## Markdown 根因與修正

實際顯示使用 `st.markdown`，沒有把手冊用 `st.text` 顯示，也沒有額外 escape。發現中文強調標記以冒號結尾且緊貼後續文字，例如 `**Scenario（情境）：**Run`；此類標點邊界可能導致 Markdown 強調解析失敗。改為獨立粗體詞條或粗體標籤加分隔，沒有全面刪除粗體。表格、清單、欄位行內 code 保留。

以現有 `markdown_it` 解析八章內容，驗證 strong、table、清單及 code 標記、沒有殘留不預期的雙星號或標題 escape。Streamlit 使用瀏覽器端解析器，因此此驗證不能取代實際瀏覽器呈現驗收。未新增套件、未使用 raw HTML 呈現手冊。Guide 錯誤訊息改為可理解的重試／求助指引，避免對讀者直接顯示 parser exception。

## 修改檔案

- `dashboard/user_guide/locales/en.md`
- `dashboard/user_guide/locales/zh-TW.md`
- `dashboard/user_guide/guide_navigation.py`（僅顯示標題）
- `dashboard/locales/en.json`
- `dashboard/locales/zh-TW.json`
- `dashboard/scenario_planning_app.py`（提示文字層級、下一步欄位、Guide 錯誤提示）
- `tests/test_ui_v121_content.py`
- `tests/test_phase2_workflow.py`（更新核准的顯示名稱預期）
- 三份本次報告；既有 V1.2 報告保留歷史結論。

## 驗證與限制

內容測試先行通過 5 項；最終相關回歸結果與 Git／資料保護比較見最終驗收報告。沒有瀏覽器工具，故未宣稱瀏覽器驗收。未建立正式 Run 或部署測試。完整實際規劃不重跑，使用既有定向合成 adapter 與 guarded UI 測試確認顯示修改未觸發計算或建立 Run。

所有工作維持原始 Repository；未進入部署 Repository，未 stage、commit、push、merge、rebase 或部署。
