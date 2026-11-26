# UI V1.1 語言選擇器與規劃模型名稱改善紀錄

## 執行摘要

- 本機程式修改：**PASS**。全域語言選擇器及模型顯示名稱已實作；模型內部值與規劃呼叫維持不變。
- 自動化回歸測試：**PASS**。20 項相關測試通過。
- 本機瀏覽器驗收：**PARTIAL**。AppTest 與本機 HTTP 健康檢查通過，但目前無可用瀏覽器工具實際驗證畫面及瀏覽器端未送出的 Form buffer。
- Deployment Repository 同步：**未開始**。依流程，必須先完成本機驗收才能同步。
- Cloud redeployment：**未開始**。

## 修改前問題

語言切換原本位於 CSV Planning Form 內，需按 Apply 才能切換；其他模式則使用 Sidebar 選擇器。使用者無法在所有功能共用同一個立即切換入口。模型名稱也未清楚說明連續週次規劃與舊版逐週獨立分析的差異。

## 新 UI 與模型標籤

- 語言選擇器已移至主內容區上方右側，選擇 English 或繁體中文後立即切換全 App 顯示語言。
- CSV Planning Form 內的語言選擇器、Apply 按鈕及其提示文字已移除。
- 保留原有 `st.form`、提交按鈕、widget keys、i18n dictionary/fallback 與 `ui_locale` 狀態設計。語言 callback 不提交表單、不呼叫驗證或規劃函式。
- 模型顯示名稱：

| 內部值（不變） | English 顯示 | 繁體中文顯示 |
|---|---|---|
| `Sequential workload` | Sequential weekly planning | 連續週次規劃 |
| `Legacy independent weeks` | Independent-week analysis (legacy) | 單週獨立分析（舊版） |

- 選擇器下方提供各模型的週次連續性、庫存／欠單承接及工作負荷產能差異說明。沒有更動 model routing 或計算。

## 表單狀態保留設計與限制

全域選擇器觸發一般 Streamlit rerun；Planning Form 的欄位 keys 與 Form 本身維持不變。程式保留目前伺服器 session 中已知的上傳內容及表單值，locale callback 只更新語言狀態。AppTest 已覆蓋日期、數值、selectbox、選填假設、CSV upload mapping 與 JSON 設定路徑在模擬 rerun 後的狀態。

AppTest 不等同真實瀏覽器，無法證明尚未送出 Form 的前端 buffer 在實際瀏覽器 rerun 後仍完整保留。因此這項要求目前標為 **PARTIAL**，尚未宣稱瀏覽器端已通過。正式同步前應以瀏覽器逐項驗收日期、數值、選擇器、CSV 檔案、設定路徑及選填假設，並確認切換語言後可繼續編輯及提交。

## 修改檔案

- `dashboard/scenario_planning_app.py`：主畫面全域語言選擇器、模型顯示標籤與說明。
- `dashboard/locales/en.json`：英文模型標籤／說明，移除舊表單語言提示。
- `dashboard/locales/zh-TW.json`：繁體中文模型標籤／說明，移除舊表單語言提示。
- `tests/test_phase2_workflow.py`：全域語言往返、表單值保留及未執行規劃檢查。

未修改 dependencies、Python runtime、CSV schema、Run／Scenario identity 或核心規劃邏輯。

## 測試與本機檢查

- `tests.test_phase2_i18n`、`tests.test_phase2_workflow` 與兩項不建立 Run 的 Dashboard upload workflow 測試：**20 項通過**。
- 測試驗證語言來回切換、主要頁面文案、模型顯示文字與內部值、現有 Run 分析配對保留、上傳對應、規劃日期及表單假設狀態。保護測試確認規劃函式未被呼叫。
- 英文與繁體中文 JSON 均可解析；舊 `locale.apply`、`locale.form_help`、`locale.sidebar_help` 字典項目已移除；`git diff --check` 通過。
- 嘗試在 8503 啟動新 Streamlit instance 時發現該 port 已被占用；既有 8503 的首頁與 `/_stcore/health` 均回應 HTTP 200，8502 健康檢查亦回應 200。沒有停止或重啟 8501／8502，也未終止既有 8503 服務。
- 自動測試首次執行時誤納入一項會實際建立 Run 的既有整合測試；該測試產生的唯一臨時 Run 目錄已移除。基準 fingerprint 清單的 9,272 個檔案全部一致，既有 Runs、Published Artifacts 與 evidence 未變。
- **尚未完成**真實瀏覽器的右上角位置／窄視窗排版、Dashboard／Planning／WP1／WP2 手動切換及未送出 Form buffer 驗收。
- 兩項關鍵狀態保留測試在完整 20 項通過後另行重跑，均通過。

## Deployment 與 Cloud

- 原始 Repository：`main` HEAD 維持 `6e451b9660dd3be09e632e10ff8698b39a267b07`；本次未 commit 或 push 原始 Repository。
- Deployment Repository：未同步、未修改 manifest、未建立 commit、未 push；本機先前基準 HEAD 為 `a2ad90b9693cec4f24b857a21a830dd39906027c`。
- Cloud 唯讀 GET（2026-11-20 06:27 UTC）：首頁 `/` 與 `/_stcore/health` 均回應 HTTP 303，導向 Streamlit 登入流程；未跟隨重新導向。這是部署前基線檢查，無法驗證公開 App 或 redeployment。
- 原有公開網址：<https://supplychain-control-tower-demo-ue5zgscfhjn7ujvlnxwqbs.streamlit.app>
- 本次沒有更動 App 分享設定、Repository 權限、網址或 GitHub 內容。

## 後續必要步驟

1. 使用真實瀏覽器在本機 8503 驗收語言切換及所有未送出的 Planning 欄位；若表單狀態任一項未保留，先修正並重測。
2. 本機驗收通過後，才將 allowlist 內核准檔案同步至隔離 Deployment Repository、更新 manifest、執行 pre-push 檢查並推送 `origin/main`。
3. Cloud GET 目前導向登入流程；部署後需重新確認公開存取狀態及新版功能。不得在本任務中自行變更分享設定。
