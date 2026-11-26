# UI V1.2.1 最終驗收報告

## 結論

**PASS WITH LIMITATIONS**。雙語手冊與 Planning 顯示改善已完成；實際瀏覽器的文字呈現、對比與操作驗收未執行，不宣稱 Browser Acceptance PASS。

## 驗收項目

| 項目 | 結果／證據 |
|---|---|
| 雙語完整性 | 每語八章，固定 section IDs、內容與導覽標題吻合；內容測試通過 |
| 一般商業使用者可讀性 | 移除可見 WP1／WP2／ui_locale／canonical 等內部敘述，改為功能名稱、操作與下一步；供應鏈詞彙保留定義 |
| Markdown | 現有 MarkdownIt 解析器驗證 strong、table、ol、ul、code；沒有不預期雙星號或 escaped strong；瀏覽器端仍待人工確認 |
| 模型 | 顯示單週獨立分析／Independent-week analysis，兩模型原內部值保留；定向測試驗證顯示名稱 |
| Planning 文案與視覺層級 | 重要指引改一般文字，詳細假設仍放可展開區；百分比與數量提示有範例 |
| CSV 狀態 | 名稱改善與下一步欄位；固定必填集及原驗證判斷保持原樣 |
| 原始使用者工作 | 與本次開始時雜湊比較，只有四個核准既有檔案改變；沒有遺失既有檔案 |
| 核心程式／資料 | 9,339 個 src、data、tmp 保護路徑檔案，變更及遺失均為 0；Runs、Published Artifacts、歷史 evidence 與既有 .pyc 保留 |
| Git | main／6e451b9660dd3be09e632e10ff8698b39a267b07；index 空白 |
| 部署 | 沒有存取部署 Repository，沒有 commit、push、merge、rebase 或部署 |

## 測試紀錄

內容階段：

```text
python3 -B -m unittest tests.test_ui_v121_content tests.test_ui_v12_user_guide.UserGuideContentTests
```

結果：5 tests，OK。手冊最後修訂後再驗證仍通過。

整合相關回歸命令：

```text
python3 -B -m unittest tests.test_ui_v121_content tests.test_ui_v12_user_guide tests.test_phase2_i18n tests.test_phase2_workflow tests.test_dashboard_app tests.test_comparison_dashboard tests.test_dashboard_upload_workflow.DashboardUploadWorkflowTests.test_uploads_mappings_and_scenario_settings_survive_model_switch tests.test_dashboard_upload_workflow.DashboardUploadWorkflowTests.test_duplicate_column_mapping_is_reported_and_blocks_execution
```

整合套件執行 48 項，46 項通過、2 項因舊文案／元件預期失敗（194.571 秒）。已更新 `test_default_empty_and_guidance` 的一般文字預期，以及 `test_global_language_round_trip_and_model_labels_keep_machine_values` 的核准模型說明文字預期；沒有削弱模型值、語言切換或狀態保留斷言。

修正後定向重測上述兩項加 `tests.test_ui_v121_content`：5 tests，2.637 秒，OK。未重跑已通過的 46 項，故結果為初次 46 項通過，加 2 項修正後重測通過；不是宣稱第二次完整套件重新跑過。

最後 locale 檢查：英／繁中各 488 個 keys 與 placeholders 完全一致。

測試涵蓋 Guide 開關、八章目錄、語言切換與章節保留、Planning 未提交欄位／CSV 暫存保留、mapping 阻擋、readiness adapter、模型標籤、Dashboard 與比較流程。Guard 阻止操作指南時執行 planning；沒有為驗收建立正式 Run。

完整 planning 執行未重跑；本次修改不涉及計算，只檢查既有 UI／adapter 與回歸契約，不能宣稱重新驗證所有業務結果。`git diff --check` 通過。既有 Streamlit use_container_width 棄用警告仍存在，未擴大成環境更新。

## 未完成與限制

- 環境沒有可用的瀏覽器工具、browser binary、Playwright 或 Selenium；沒有生成實際瀏覽器截圖。
- Markdown 解析器檢查不能保證不同 Streamlit 瀏覽器端版本的視覺結果，仍需人工閱讀兩語粗體、表格、清單、字色及 tooltip。
- 需在瀏覽器確認 Planning 未提交值、上傳與語言切換；AppTest 通過不等同 Browser Acceptance PASS。
- 僅改寫可見說明及必要顯示層，未將其他歷史文件重寫成新的功能規格。

## 文件索引

- `docs/deployment/UI_V1_2_1_CONTENT_AUDIT.md`
- `docs/deployment/UI_V1_2_1_CONTENT_IMPROVEMENT_REPORT.md`
- `docs/deployment/UI_V1_2_1_FINAL_ACCEPTANCE_REPORT.md`
