# Phase 2 — CJK Font Remediation & T32 Verification

日期：2026-11-19 UTC

**本次結果：PASS WITH LIMITATIONS。** 字型缺口已修復；新的 Chromium session 可正常顯示繁中，限定範圍的 T32 字形檢查通過。限制是本次禁止重新執行 WP1／WP2，所以原代表性畫面採既有 DOM 離線重繪；canvas／完整 live 業務流程未重新驗收。容器重建持久性亦未建置。

**後續結論：**本報告撰寫後，T25 瀏覽器補強與最終服務驗證完成；[最終服務驗證報告](PHASE_2_FINAL_SERVICE_VERIFICATION_REPORT.md) 記錄 T32 PASS，並建議 Phase 2 COMPLETE — PASS WITH LIMITATIONS，待 owner review。以下「尚未結案」文字保留當時的歷史狀態。

**這不是 Phase 2 正式結案。** 不改寫先前 FAIL 報告或原始證據；T25 瀏覽器補強與 Phase 2 最終驗收仍等待 owner 決定。

## 1. 授權與執行環境核對

依據 [唯讀診斷報告](PHASE_2_CJK_RENDERING_DIAGNOSTIC.md)，只修復 Chromium 執行環境的 CJK 字型供應。Main Agent 單獨執行，沒有 Subagent。

| 項目 | 本次實際結果 |
| --- | --- |
| Container | Debian GNU/Linux 13 (trixie)，/etc/os-release 版本 13.4；與原診斷一致 |
| Namespace／容器標記 | 實際 Chromium 執行 namespace 的 PID 1 為 sleep，/.dockerenv 存在，REMOTE_CONTAINERS 標記存在 |
| Root filesystem | overlay；未發現 /usr/share/fonts 的獨立持久 mount |
| Chromium | 既有 Headless Shell 159.0.8154.6，使用相同執行檔及 venv |
| Chromium SHA256 前後 | 24eb0a14de64ab0c9c2e283a5512ca817db64af8fd853cdb4d818f19a8e23b9b；相同 |
| Python browser environment | tmp/wp2_browser_uat_phase_a/venv；沒有 pip／依賴升級 |
| Git HEAD／branch | 4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf／main；index 空，工作樹既有 dirty 狀態保留 |

本機 APT repository metadata 的版本標籤不代表本次升級了 OS。實際安裝前後套件清單比對只有下節的一個新字型套件。

## 2. 安裝前模擬與實際安裝

先完成唯讀模擬，再進行安裝；命令及原始 logs 均保存在新的證據目錄。

```sh
apt-get -s install --no-install-recommends --no-upgrade fonts-noto-cjk
apt-get install --no-install-recommends --no-upgrade -y fonts-noto-cjk
```

| 項目 | 模擬／實際結果 |
| --- | --- |
| 新增 | fonts-noto-cjk 1:20240730+repack1-1，狀態 ii |
| 升級 | 0 |
| 移除 | 0 |
| 其他既有套件版本／狀態變更 | 0；完整 dpkg-query 清單前後比對 |
| 額外相依套件 | 無 |
| fonts-noto-cjk-extra | 只有 Suggests，未安裝 |
| fontconfig CLI | 未安裝；不為 fc-list 額外加入套件 |
| 下載／安裝空間 | apt log 記錄下載約 56.7 MB，新增約 93.4 MB 空間 |

沒有執行 apt upgrade、dist-upgrade 或 apt update；沒有變更 Chromium／Playwright／Streamlit。apt 自動選擇可用的 debconf frontend，未另外設定 DEBIAN_FRONTEND 或其他環境變數。安裝會正常更新 dpkg／APT 記錄與字型資料；沒有改 Fontconfig 設定或專案環境建置檔。

證據：[安裝前原始模擬 log](../../tmp/phase_2_cjk_remediation/20261119T154559Z/logs/apt_simulation.log)、[實際安裝 log](../../tmp/phase_2_cjk_remediation/20261119T154559Z/logs/apt_install.log)、[安裝前套件清單](../../tmp/phase_2_cjk_remediation/20261119T154559Z/baseline/packages.tsv)、[安裝後套件清單](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/packages_after.tsv)、[精確套件差異](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/package_diff.json)。

## 3. Fontconfig 與有效字形

不使用 fc-list／fc-match CLI，改用既有 libfontconfig.so.1 與 libfreetype.so.6 查核。Fontconfig 載入新字型後，以 sans-serif、lang=zh-tw 及漢字需求查詢，選到：

- family：**Noto Sans CJK TC**
- file：/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
- face index：**3**

18 個代表性字元的 Fontconfig charset 均包含該字元，FreeType glyph index 均非零：

| 字元 | Glyph index |
| --- | --- |
| 繁 | 31477 |
| 體 | 45257 |
| 中 | 9544 |
| 文 | 20036 |
| 臺 | 33319 |
| 灣 | 24819 |
| 參 | 11849 |
| 考 | 32275 |
| 情 | 17904 |
| 境 | 13791 |
| 候 | 10288 |
| 選 | 40545 |
| 規 | 37352 |
| 劃 | 11329 |
| 服 | 20700 |
| 務 | 11465 |
| 水 | 23010 |
| 準 | 23959 |

修復前的 DejaVu／Source Sans 對原六個繁中樣本均為 glyph index 0；修復後上述 TC 字族提供有效字形。這是字形可用性驗證，不以 DevTools glyphCount 取代實際 glyph index。

[Fontconfig／FreeType 原始結果](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/fontconfig_glyph_check.json)。

## 4. 新 Chromium session 的前後比較

每一輪均使用新的 Chromium process／session；沒有重啟 Streamlit。證據寫到新的專用目錄，不覆蓋原 Phase 2 截圖或 trace。

| 檢查 | 安裝前 | 安裝後 | 結果 |
| --- | --- | --- | --- |
| 同一 Source Sans 靜態字形頁 | 主要字型無 CJK 字形，方框 | 系統 fallback 到 Noto，文字可讀 | PASS |
| 明確 html lang=zh-TW 靜態頁 | 原診斷無可用 CJK fallback | DevTools 回報 Noto Sans CJK TC | PASS |
| 原 WP2 DOM 字型重繪 | 標題／選擇器／說明為方框 | 相同既有 DOM 的中文標籤可讀 | PASS（字形範圍） |
| 原 WP1 DOM 字型重繪 | 同上 | 調查路徑／產品／工廠／週標籤可讀 | PASS（字形範圍） |
| 實際首頁 metadata 表格與說明 | 原 Phase 2 截圖有字形問題 | 真實 Streamlit 元件中的中文清楚可讀 | PASS |
| 英文→繁中→英文與待送出數值 | 依既有狀態設計 | 輸入 17，往返後仍為 17.00 | PASS（本次實測範圍） |

新的修復前結果：[before browser JSON](../../tmp/phase_2_cjk_remediation/20261119T154559Z/before_verified/reports/before_browser.json)；修復後：[after browser JSON](../../tmp/phase_2_cjk_remediation/20261119T154559Z/after_verified/reports/after_browser.json)；聚焦與明確 zh-TW 結果：[focused rendering JSON](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/focused_rendering.json)。

### 字族區域差異

沒有明確 document language 提示的一般靜態頁，Chromium 選到 **Noto Sans CJK JP**，其字形已可顯示原繁中碼位，不再是方框。另以 zh-TW 語言提示的獨立靜態頁，確認 Chromium 實際使用 **Noto Sans CJK TC**（14 個漢字 glyph，另有 2 個 Source Sans 空白／非漢字 glyph）。Fontconfig 的 TC face 查詢亦成功。

因此本次已證明 TC 字族可用且解決缺字，沒有宣稱所有 App 元件都已強制使用 TC 區域字形。區域字形／字體樣式政策不在本次 App 修改範圍；未修改 App 的 HTML lang、CSS、Theme 或字型 stack。

## 5. T32 代表性畫面的驗證方式與限制

為遵守「不執行 WP1 或 WP2」，使用原 Phase 2 的：

`tmp/phase_2_ui/20261119T134451Z/browser_retry/traces/browser.zip`

唯讀解碼其中已捕獲的 HTML／CSS／資源與 snapshot delta references；移除 App scripts 及 event handlers，攔截所有 HTTP 資源要求，只由原 zip 內資源提供內容。**沒有把代表性畫面的要求送到 App，沒有載入 Run、重新調查或重新計算比較。**

| 代表性內容 | 原始 trace call ID | 檢查 |
| --- | --- | --- |
| WP2 參考／候選與優先群組控制項 | jzvx@163 | 1440×1100、1600×1100 的靜態 DOM 字形重繪 |
| WP1 調查路徑、產品、工廠、週控制項 | jzvx@233 | 同上 |

這些畫面是**實際 Chromium 對原 DOM 的離線重繪截圖**，不是捏造的畫面，也不是新的 live WP1／WP2 測試結果。快照中的 canvas 像素未重建；個別 icon／layout 的 snapshot 表現亦不等同 live 元件。因此不把這次重繪當作 canvas 全表、圖表工具列、WP1／WP2 功能或數值重新驗收。

另以真正 App 首頁驗證共用 Streamlit 字體與 dataframe 元件，使用全新空白工作階段：Published Run path 保持空白，WP2 tab 不存在，僅打開 metadata 說明及操作語言表單。沒有點擊 Validate inputs、Validate and run planning 或任何執行按鈕。語言套用只傳送 UI 值；沒有驗證、上傳、Planning、Run 或 Publication。

### 已實際檢視的修復後截圖

- [新 Chromium 靜態繁中字形](../../tmp/phase_2_cjk_remediation/20261119T154559Z/after_verified/screenshots/after_static.png)
- [明確 zh-TW 靜態頁](../../tmp/phase_2_cjk_remediation/20261119T154559Z/screenshots/after_explicit_zh_TW.png)
- [真實首頁與 metadata dataframe](../../tmp/phase_2_cjk_remediation/20261119T154559Z/after_verified/screenshots/after_live_zh.png)
- [真實繁中表單與 17.00 待送出值](../../tmp/phase_2_cjk_remediation/20261119T154559Z/after_verified/screenshots/after_live_form_zh.png)
- [切回英文](../../tmp/phase_2_cjk_remediation/20261119T154559Z/after_verified/screenshots/after_live_en.png)
- [原 WP2 DOM 聚焦重繪](../../tmp/phase_2_cjk_remediation/20261119T154559Z/screenshots/after_frozen_wp2_focused_1600.png)
- [原 WP1 DOM 聚焦重繪](../../tmp/phase_2_cjk_remediation/20261119T154559Z/screenshots/after_frozen_wp1_focused_1600.png)

修復前畫面仍保留：[靜態頁方框](../../tmp/phase_2_cjk_remediation/20261119T154559Z/before_verified/screenshots/before_static.png)、[原 WP2 DOM 修復前字形](../../tmp/phase_2_cjk_remediation/20261119T154559Z/before_verified/screenshots/before_frozen_wp2.png)、[原 WP1 DOM 修復前字形](../../tmp/phase_2_cjk_remediation/20261119T154559Z/before_verified/screenshots/before_frozen_wp1.png)。原 Phase 2 失敗截圖與報告同樣未改動。

第一版離線解碼 harness 遇到只有 tag、沒有 attrs 的壓縮節點，拋出 IndexError；只修正新測試目錄中的解碼器，成功重試結果放在 before_verified，最初 log／靜態截圖保留。這不是 App 修復或產品缺陷；沒有因此改任何原始 Evidence。

## 6. Container 持久性

目前字型位於 container root overlay，沒有獨立 /usr/share/fonts 掛載；本次沒有把字型安裝寫入 image build／Dockerfile／Devcontainer 或部署設定。

| 情境 | 結論 |
| --- | --- |
| 同一容器中的全新 Chromium session | 已實測有效 |
| 同一容器生命週期持續使用 | 已安裝的字型可持續使用 |
| 同一 container object 的一般 stop/start | 通常保留 writable layer；本次沒有執行此操作驗證 |
| 從原始 image 重建／替換容器，沒有其他外部持久化 | **預期字型安裝會消失**，因本次安裝僅在目前 writable layer |
| 未知的外部 image 管理／平台備份政策 | 未查證，不能宣稱平台會替本次安裝自動持久化 |

結論：本次修復對目前 container 有效，但不是可重建的環境定義。若日後要保證重建後仍存在，必須由 owner 另行核定真正管理 image／devcontainer 的位置與變更；本次未擴大範圍建立任何設定檔，也未實際重建容器。

## 7. 對既有功能與資料契約的影響

- 沒有修改 App Code、CSS、Theme、i18n、翻譯字典或 Python 測試。
- 沒有執行 WP1／WP2／KPI／CSV 計算或重新下載業務匯出；原有資料契約以 source 與既有檔案 hash 不變為依據，不冒充新的數值回歸結果。
- 活頁面只測量首頁顯示、語言往返及待送出數值保留，沒有聲稱所有 WP1／WP2 selection 行為重新通過。
- 唯一套件差異是 fonts-noto-cjk，沒有其他套件新增／升級／移除；Chromium binary hash 與版本不變。
- 新字型只提供繪製字形，不改 Run_ID、Scenario_ID、Comparison_ID、KPI、CSV schema／values 或 Evidence references。
- T25 PARTIAL、原 Phase 1 七項負面 Published E2E 子層及其他已接受限制不在本次重開／補測範圍。

## 8. Git／Run／原有 Evidence 完整性

在建立本報告之前已比對：

- **997 個既有檔案** hash 全數不變，包含既有 Git 內容、Run-adjacent 檔案與整個原 Phase 2 evidence root。
- **53 個 Run manifest 路徑**清單相同；沒有新增／修改／發布 Run。
- 原有 dirty／untracked 檔案保留；HEAD 前後均為 4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf，main，index 空。
- 沒有 stage、commit、push、reset、clean、restore、stash、branch 或部署操作；沒有啟停既有 Streamlit 服務。

完整開始狀態與 fingerprint 在 [初始保護快照](../../tmp/phase_2_cjk_remediation/20261119T154559Z/baseline/repository.json)；報告前核對在 [完整性結果](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/integrity_before_report.json)。本報告完成後另作最終核對，只允許新增此 Markdown 與本次專用測試輸出。

## 9. 證據根目錄與最終處置

新證據根目錄：`tmp/phase_2_cjk_remediation/20261119T154559Z/`。

它包含套件模擬／安裝 logs、完整套件清單前後差異、Fontconfig／glyph 結果、修復前後 JSON／實際截圖及只針對本次任務的 probe scripts。這些是新的本地證據，不修改任何既有 Run／Published Artifact／Evidence。

**字型修復已完成；本次授權範圍的字形／語言往返檢查通過。** 因 WP1／WP2 只做原 DOM 字形重繪、且安裝未宣告為可重建環境，整體交付標為 PASS WITH LIMITATIONS，不把它擴大為完整 Phase 2 acceptance。

本次停止。等待 owner 決定是否授權 T25 瀏覽器測試補強與 Phase 2 最終驗收；不自動更新歷史驗收決策、不建立持久化環境定義、不 commit／push／部署。

### 最終完整性核對

已確認 997 個原有檔案全部未變、53 個 Run 路徑相同；Git 唯一新增的專案檔案是本報告，原有 status 逐項保留，HEAD／main／空 index 不變。套件前後比對僅新增 fonts-noto-cjk。未修改 App／CSS／翻譯／Docker／設定，未重啟服務，未 stage／commit／push。

完整機器可讀結果：[final_integrity.json](../../tmp/phase_2_cjk_remediation/20261119T154559Z/reports/final_integrity.json)。本報告相對連結、code fences、行尾空白與 git diff --check 通過。
