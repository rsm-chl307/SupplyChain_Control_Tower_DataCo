# UI V1.2 執行報告

## 執行摘要

已在原始 Repository 完成雙語 User Guide Center、Planning 文案改善及目錄保護。規劃與資料契約驗證使用既有 synthetic demo fixture；未建立正式 Run。此工作沒有同步至部署 Repository，沒有 commit、push 或 Cloud 部署。

## 基線與保護

- Repository：`/workspace/SupplyChain_Control_Tower_DataCo`
- Branch／HEAD：`main`／`6e451b9660dd3be09e632e10ff8698b39a267b07`
- 測試前既有 V1.1 修改、使用者文件、deployment／diagnostics 報告、Phase 1 forensic report 及 10 個 tracked `.pyc` 修改均保留。
- Index 維持空白；沒有執行 staging、commit、push 或任何清理／還原 Git 操作。
- 對照開始時保存的 9,272-file fingerprint inventory：629 個 Run／evidence 相關檔案逐一比對，變更／遺失／新增皆為 0；預設 Legacy 2017 輸出目錄 4 個檔案 fingerprint 全部一致。

## Work packages

### WP1.2-A — 能力盤點

檢查 App、i18n、display metadata、雙語 locale、既有手冊、Capability Catalog、資料契約及回歸測試。以實際可用入口建立 coverage matrix，將未實作或受資料限制的能力列為限制。

### WP1.2-B — 雙語手冊

建立八章完整英文及繁體中文手冊：系統介紹、Dashboard、Planning、WP1、WP2、資料與報表、KPI 詞彙、疑難排解。章節包括用途、適用時機、必要輸入、操作、輸出、判讀及常見錯誤。

### WP1.2-C — Guide Center

新增固定 ID 的目錄、章節導覽、active section、可折疊內容、回到頂端與關閉操作，沿用既有 `ui_locale`。Guide 會與 App 同頁 render，AppTest 驗證開啟、切章、切語言與關閉時 Planning pending form values／uploads 保留，且沒有呼叫 planning functions。AppTest 確認 expander 與回頂端 anchor 有 render；未驗證實際瀏覽器的展開／捲動操作。

### WP1.2-D — UI 文案

- 為 Planning 重要欄位補上雙語 help text，說明用途、單位、實際 UI 預設／範圍及對結果的影響。
- 顯示需求解讀、日期、數量步長、surge、capacity reduction 等更明確用語；機器值、欄位與識別碼不變。
- 修正 ORDER_LINES 完整擷取聲明在有 Status 分類時不可見的 UI 分支問題；原 `source_is_complete` contract 不變。
- 將既有合成產能設定 recipe 傳入 adapter 契約要求的頂層 `capacity_calibration`；synthetic adapter readiness 為 READY，標示 `SYNTHETIC_DEMAND_CALIBRATED`。公式與校準邏輯未改。
- Legacy 日期對應的輸出目錄若已存在，顯示警告並停用 Run。此保護避免預設 2017 路徑覆寫既有 Run。

## 修改檔案

V1.2 程式／測試／新增手冊模組：

- `dashboard/scenario_planning_app.py`
- `dashboard/locales/en.json`
- `dashboard/locales/zh-TW.json`
- `dashboard/user_guide/__init__.py`
- `dashboard/user_guide/guide_navigation.py`
- `dashboard/user_guide/guide_content.py`
- `dashboard/user_guide/locales/en.md`
- `dashboard/user_guide/locales/zh-TW.md`
- `tests/test_ui_v12_user_guide.py`

V1.2 文件更新／新增：

- `docs/PRODUCT_CAPABILITY_CATALOG_EN.md`
- `docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md`
- `docs/USER_GUIDE_EN.md`
- `docs/USER_GUIDE_ZH-TW.md`
- `docs/deployment/UI_V1_2_IMPLEMENTATION_SPECIFICATION.md`
- `docs/deployment/UI_V1_2_USER_GUIDE_CONTENT_COVERAGE.md`
- `docs/deployment/UI_V1_2_EXECUTION_REPORT.md`
- `docs/deployment/UI_V1_2_FINAL_ACCEPTANCE_REPORT.md`

開始前已存在的 V1.1 及使用者未提交檔案不屬於本次新成果清單；其狀態仍在工作樹且未 stage。

## 測試

最終定向回歸命令：

```text
python3 -B -m unittest tests.test_ui_v12_user_guide tests.test_phase2_i18n tests.test_phase2_workflow tests.test_dashboard_app tests.test_comparison_dashboard tests.test_dashboard_upload_workflow.DashboardUploadWorkflowTests.test_uploads_mappings_and_scenario_settings_survive_model_switch tests.test_dashboard_upload_workflow.DashboardUploadWorkflowTests.test_duplicate_column_mapping_is_reported_and_blocks_execution
```

結果：**45 tests，130.905 秒，OK**。涵蓋指南內容與雙語、目錄互動、Form 狀態、使用者 CSV 暫存值、ORDER_LINES UI 可達性、synthetic adapter readiness、Legacy 既有目錄保護、既有 i18n／Dashboard／Comparison／Planning upload regressions。測試以 guard 阻止實際規劃執行，沒有建立正式 Run。

其他檢查：`git diff --check` PASS；兩份 dashboard locale 各 484 keys 且 key sets 相同 PASS；Run／evidence fingerprint 比對 PASS。

## 手動／瀏覽器驗收

環境未提供 Chromium、Chrome、Firefox、Playwright 或 Selenium，無法執行實際瀏覽器驗收、不同 viewport／鍵盤操作、expander／回頂端實際互動檢查或截圖。因此 AppTest 項目可列自動化 PASS，但 browser/manual acceptance 為 **PARTIAL**；沒有以 AppTest 假稱瀏覽器通過。

## 未解決事項與結果

- 請在可用瀏覽器環境完成實際視窗寬度、鍵盤導覽及截圖檢查，尤其是 User Guide 兩語、目錄跳轉、language switching 與表單 pending state。
- Streamlit 的既有 `use_container_width` deprecation warning 在測試中出現，未擴大成 dependency/runtime 更新。
- Git branch／HEAD 維持原值、index 無 staged changes；使用者原有 tracked／untracked 修改及 `.pyc` 保留。
- 629 個 Run／evidence 路徑 fingerprint 完全一致。
- 沒有訪問／修改 Deployment Repository，也沒有 commit、push 或 Cloud redeployment。

**結論：程式與自動化驗收 PASS；整體 UI V1.2 為 PASS WITH LIMITATIONS，等待真實瀏覽器驗收後才可達成完整 acceptance gate。**
