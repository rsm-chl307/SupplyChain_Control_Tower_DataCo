# UI V1.2.1 內容與 Planning 易用性稽核

## 基線與範圍

Repository：`/workspace/SupplyChain_Control_Tower_DataCo`。Branch：`main`；HEAD：`6e451b9660dd3be09e632e10ff8698b39a267b07`。開始時 index 空白，工作樹已有 V1.1、V1.2 程式／測試／文件、10 個 tracked `.pyc` 修改及未追蹤報告。未清理、還原或 stage 任何工作。

逐段閱讀兩語八章，共 16 個章節版本，包含標題、段落、清單、表格、例子與 FAQ；追蹤 `guide_navigation.py` → locale Markdown → `guide_content.py` → `_render_user_guide` 的顯示路徑。另檢查 locale 中 guide、Planning、workflow、model、dataset 名稱及上傳／驗證相關文案。

## 問題清單與處理

| 範圍 | 問題 | 處理 |
|---|---|---|
| 系統介紹 | 程式狀態、內部代號、未解釋縮寫 | 改為操作流程，定義 CSV、KPI、ID、READY、BLOCKED、N/A |
| 營運總覽 | 新舊定位與本機內部儲存路徑 | 改為單週獨立用途，保留既有目錄會阻擋執行的限制 |
| Planning | canonical、manifest、repository、widget 等術語 | 改為欄位配對、規劃紀錄與檔案位置；必要檔名保留 |
| 風險調查 | WP1、native grain、artifact | 改為根因與營運風險分析、來源原有明細層級與佐證資料；不宣稱因果能力 |
| 情境比較 | WP2、交接機制、未解釋比較狀態 | 改為情境比較與決策分析；解釋參考／候選、群組、Delta 與狀態 |
| 資料報表 | 系統架構／儲存細節擠壓操作指引 | 改為如何開啟與下載，提醒保存完整結果與資料安全 |
| 詞彙 | 粗體冒號貼鄰正文、Run 的工程定義 | 改為獨立粗體詞條與自然段；保留既有 KPI 定義 |
| 常見問題 | 技術錯誤解說缺少下一步 | 先列使用者檢查項目及向資料提供者尋求協助 |
| Planning 模型 | Legacy／舊版造成新舊版本印象 | 顯示單週獨立分析／Independent-week analysis，內部值不變 |
| 上傳資料 | 資料名稱抽象、缺少行動指引 | 改善雙語資料名稱；狀態表增加下一步，不更動必填判斷 |
| 操作提示 | 重要資訊集中在低對比小字 | 主要模型／準備／分類／假設提示改一般 Markdown 文字；補充資訊仍可收合 |

## 術語分類原則

- 應改寫：canonical、artifacts、native grain、repository、state、rendering、implementation 等工程敘述。
- 應移除：面向讀者的 WP1／WP2、ui_locale、Legacy／舊版定位。
- 必要檔名／欄位／狀態：`run_manifest.json`、CSV 欄名、Run ID、WEEKLY／ORDER_LINES、CARRY_FORWARD／LOST_SALES 等保持拼字，附操作說明。
- 合理專業詞彙：Service Level、Capacity Utilization、Backlog 等保留定義與限制。章節 ID `wp1`／`wp2` 僅作非顯示導覽鍵，不改名以免破壞選擇狀態。

## 最終命中逐筆分類

下表逐筆列出完整手冊掃描結果；沒有列出的指定工程詞彙在可見手冊中沒有命中。

| 檔案／行 | 命中 | 分類與判斷 |
|---|---|---|
| en.md:60 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| en.md:114 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| en.md:124 | wp1 | 非顯示穩定導覽鍵，保留 |
| en.md:145 | wp2 | 非顯示穩定導覽鍵，保留 |
| en.md:183 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| en.md:187 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| en.md:271 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| zh-TW.md:80 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| zh-TW.md:138 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| zh-TW.md:150 | wp1 | 非顯示穩定導覽鍵，保留 |
| zh-TW.md:173 | wp2 | 非顯示穩定導覽鍵，保留 |
| zh-TW.md:215 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| zh-TW.md:219 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
| zh-TW.md:307 | run_manifest.json | 必要規劃紀錄檔名，保留並附解釋 |
