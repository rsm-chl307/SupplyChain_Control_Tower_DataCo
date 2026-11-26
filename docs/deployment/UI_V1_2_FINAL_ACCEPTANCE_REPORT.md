# UI V1.2 最終驗收報告

## 驗收結論

**PASS WITH LIMITATIONS**。雙語使用手冊、App 內 Guide Center、Planning 用語改善及 Legacy 輸出目錄保護已實作並通過定向自動化測試。完整 acceptance gate 尚差真實瀏覽器驗收與截圖。

| 驗收項目 | 結果 | 證據／限制 |
|---|---|---|
| 能力盤點與雙語完整手冊 | PASS | 八個固定章節 ID 在英／繁中內容存在且非空；內容測試通過 |
| 全域 User Guide 入口及 TOC | PASS（AppTest）／互動 PARTIAL | 入口、章節導覽、active section、close 與 locale switching 已測；expander 與回頂端 anchor 確認 render，但瀏覽器中的展開／捲動尚未驗收 |
| locale 切換保留目前章節 | PASS（AppTest） | 章節切換至 `wp2` 後切 `zh-TW`，目前章節及開啟狀態保留 |
| Planning pending state／uploads | PASS（AppTest） | 指南開關／切章／切語言後，測試中的數字、日期與 synthetic CSV upload bytes 保留；planning functions 呼叫數為 0 |
| ORDER_LINES 完整擷取控制 | PASS（AppTest） | Status 欄值存在時仍顯示完整擷取 checkbox；資料 contract 未變 |
| 合成產能 recipe adapter wiring | PASS（定向測試） | 頂層 `capacity_calibration` 被 adapter 接受，synthetic fixture 為 READY 並標示既有 synthetic provenance |
| Legacy Run 輸出保護 | PASS（AppTest／fingerprint） | 已存在的預設 2017 目錄停用 Run 並顯示警告；目錄 4 個檔案 fingerprint 未變 |
| Regression suite | PASS | 45 tests，130.905 秒，OK；命令詳見執行報告 |
| locale／diff integrity | PASS | 484 個 locale keys 完全一致；`git diff --check` 通過 |
| 真實瀏覽器、responsive、鍵盤與截圖 | PARTIAL | 沒有可用 browser binary 或 Playwright／Selenium；尚未完成實際展開／回頂端操作與不同 viewport 驗收；沒有生成或偽造截圖 |
| Git／資料保護 | PASS | branch `main`、HEAD `6e451b9660dd3be09e632e10ff8698b39a267b07`；index 空白；629 個 Run／evidence 檔案與基線 fingerprints 一致 |

## 不變條件確認

- Planning／allocation／KPI 計算、canonical CSV 欄位、機器值、Run／Scenario／Comparison identity 與 Published Run schema 未更改。
- 沒有執行正式 planning；沒有建立、刪除或修改 Runs、Published Artifacts 或歷史 evidence。
- V1.1 既有修改、其餘使用者工作、untracked files 與 tracked `.pyc` 修改均保留。
- 本次只在原始 Repository 工作；沒有進入 Deployment Repository。
- 沒有 staging、commit、push、Cloud 檢查或 redeployment。

## 尚需完成的驗收

在有瀏覽器的本機環境檢查英文與繁體中文 Guide、TOC 導覽／展開、視窗窄寬版面、鍵盤操作、切換語言保留章節及 Planning pending inputs。完成後補上真實截圖與手動驗收結果；在此之前不宣稱 V1.2 完整 PASS。

## 報告索引

- 規格與 baseline：`docs/deployment/UI_V1_2_IMPLEMENTATION_SPECIFICATION.md`
- 執行記錄：`docs/deployment/UI_V1_2_EXECUTION_REPORT.md`
- 功能盤點與手冊覆蓋：`docs/deployment/UI_V1_2_USER_GUIDE_CONTENT_COVERAGE.md`
- 本文件：`docs/deployment/UI_V1_2_FINAL_ACCEPTANCE_REPORT.md`
