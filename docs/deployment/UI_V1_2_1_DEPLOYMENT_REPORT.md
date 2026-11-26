# UI V1.2.1 部署同步報告

## 執行結果：GitHub PASS／Cloud 驗證 BLOCKED

已依 Owner Decision 完成 UI 移植、測試、commit 及一般 push。GitHub main 已更新；Cloud 是否實際完成重新部署尚未確認。首頁與健康端點均回應 303 並導向 Streamlit 驗證網址，未登入、未跟隨轉址、未改動分享設定。因此不能宣稱 Cloud redeployment PASS、公開新版已可用或完整 UAT 通過。

## Owner Decision 與部署差異

保留 Deployment Repository 原有安全限制，只移植 UI V1.2.1 的介面與指南。單週獨立分析未納入公開 Demo，因缺少核准的必要資料；沒有複製原始資料、單週 Runs 或新增測試資料補足。原始功能未刪除。

以原部署入口為基底，在原始開發位置 `tmp/ui121-deployment-preparation/source/` 準備精確移植結果，再同步 8 個 UI／資源檔案。沒有以原始入口直接覆蓋部署入口。新增下一步欄、help text、全域語言及 Guide；原有 `_build_upload_config`、完整性聲明條件、驗證、run 呼叫與輸出隔離行為不變。原開發版已修正、但不屬於本次 UI-only 授權的 calibration／完整性聲明邏輯未移植，公開指南明確記錄其限制。

公開指南特別調整：不提供模型切換或單週操作入口；JSON 模式只使用固定核准 synthetic 設定；結果僅限本次瀏覽器使用期間，不提供任意資料夾載入。仍保留八章目錄與穩定 IDs，Dashboard 章節說明本 Demo 的功能範圍，而非宣稱獨立週功能可用。

## Repository 前後狀態

| 項目 | 部署前 | 部署後 |
|---|---|---|
| 原始 branch／HEAD | main／6e451b9660dd3be09e632e10ff8698b39a267b07 | 相同，未 commit 或 push |
| 部署 branch／HEAD | main／a2ad90b9693cec4f24b857a21a830dd39906027c | main／281ac77ba0745c1ebea041fc8f347ade07b8b6b2 |
| Deployment working tree／index | clean／空白 | clean／空白 |
| Deployment local／origin/main | 同步 | ahead 0／behind 0 |
| Git history | 獨立 root a2ad90b | 同一 root，2 commits，沒有原始 main 的 parent |

Remote：`https://github.com/rsm-chl307/SupplyChain-Control-Tower-Demo.git`；唯一 push 目標 `origin/main`。

原始 working tree 既有 V1.1／V1.2／V1.2.1、tracked .pyc、diagnostic、reports、untracked work 均保留，index 空白。本次只新增準備／驗證工作檔及更新本報告，沒有刪除既有檔案。

## 同步檔案與 SHA-256

8 個檔案由原始開發位置的已審查移植來源同步，逐檔 bytes／SHA-256 8/8 一致。入口、兩份 locale 及指南內容依既有部署限制做必要呈現調整，故不宣稱所有檔案都與通用開發版完全相同。

| 檔案 | 部署 SHA-256 |
|---|---|
| `dashboard/scenario_planning_app.py` | `ff8d58002a12464ed2250fb8b215bf5d4ecff1423d123a87a9f28d129ac8fc37` |
| `dashboard/locales/en.json` | `bd60a730d31f4d1913def1f4688ab1185ee9ed1937d2ffd2d4800f6076998c58` |
| `dashboard/locales/zh-TW.json` | `d0810467459f5873b9d2095f805a271c7ae0ef81691ed10486afd0645dddc12d` |
| `dashboard/user_guide/__init__.py` | `0db0d86d71dd04812e443424d5b85a003c7d2306c1f2bb8e782335729a23b764` |
| `dashboard/user_guide/guide_navigation.py` | `e111ceef43b77446f36e54509fd3ad70bec6b2f2eda43a60b7272d522b4512cd` |
| `dashboard/user_guide/guide_content.py` | `6e33016071bb6c3020138b753e14e974f11da906a07069a573c29de63d4dfe9c` |
| `dashboard/user_guide/locales/en.md` | `6a4b7c6c4032fd1d8504ff22b99c914a312a25666a743afc5d455f5be8d6b2d1` |
| `dashboard/user_guide/locales/zh-TW.md` | `d4a5b428af4cec6b51232dc548daf4b250e3f5b8f747bb558b54c7f9474f0345` |

另新增 `DEPLOYMENT_SOURCE_MANIFEST.json`，記錄全部 55 個 payload files 的 allowlist 與 SHA-256；manifest 本身不列入自我雜湊。總 tracked files 由 50 增至 56（原有 50 + 5 個必要 guide files + manifest）。55/55 payload hashes 匹配；新增內容僅 Python guide loader/navigation 與雙語文字資源，無擴大資料範圍。原有 synthetic fixture、templates、dependencies、設定與所有 src 檔案不變。`dashboard/i18n.py`、`display_metadata.py` 未改，因既有版本足以支援。

禁止路徑與 token/private-key pattern 檢查通過；無新增原始資料、Access Logs、個資、Runs、Published Artifacts、evidence、screenshots、trace、pyc、cache 或 diagnostics。未複製 `.git`。

## 保留的安全基線

- 2 MiB 單檔、5 MiB 合計、50,000 列上傳限制及 CSV 類型限制。
- `_session_output_root()` 使用者暫存輸出隔離，所有既有 run 呼叫仍使用相同輸出根目錄。
- `resolve()`／`is_relative_to()` 路徑限制，不允許任意或跨 session 結果讀取。
- 固定 synthetic 設定與部署資料存取限制。
- 原有輸出目錄／Run 保護、input requirements、readiness 與發布行為。
- AST 比較確認 `_session_output_root`、`_csv_preview`、`_validate_uploaded_config`、`_write_upload_inputs`、`_build_upload_config`、`_run_controls`、`load_sequential_outputs` 與基線完全相同。
- 全部 src、requirements、Streamlit config、i18n helper 與 display metadata 雜湊維持基線。

## 本次測試

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_deployment_safety.py`（Deployment Repository）：**6 passed，0.88 秒**。初次誤在原始 cwd 指定同名部署測試得到 file not found，之後以正確部署 cwd 執行通過，未掩蓋此錯誤。
2. 原始位置 `tmp/ui121-deployment-preparation/validate.py` 明確 import 部署來源：安全 AST／雜湊、全 Python compile、488 locale keys／parameters、八章雙語 Markdown、Guide 開關／八章 TOC、語言切換、目前章節及未提交 numeric input 保留全部通過；Guide 操作 guarded run call count 為 0。未使用 AppTest 宣稱 browser acceptance。
3. 部署版 `run_csv_planning` 使用已核准 synthetic fixture，在外部 `TemporaryDirectory` 執行一次跨週規劃，manifest 成功產生，之後僅清除該測試暫存目錄；沒有建立正式 Run 或改動既有 artifacts。
4. Streamlit 本機啟動：sandbox 禁止 socket 後，經核准啟動一次獨立臨時 port，`/_stcore/health` 回應 **200 ok**；只終止該次程序，未停止既有服務。
5. Manifest 55/55、移植來源 8/8、禁止路徑／secret pattern、`git diff --cached --check` 及提交範圍檢查通過。

未重跑原始 48 項歷史套件；沿用原記錄 46 項直接通過、2 項更新文案預期後重測通過。部署環境不包含該完整原始測試資料與正式結果，因此不偽稱此處已完整重跑。未安裝依賴或改變 Python runtime；本機使用既有 interpreter，未重新確認 Cloud Python 版本。測試中既有 Streamlit 棄用警告仍存在。

## Commit／Push

- Commit：`281ac77ba0745c1ebea041fc8f347ade07b8b6b2`
- Message：`feat: deploy UI V1.2.1 usability improvements`
- Commit 僅包含上列 8 個檔案加 manifest，合計 9 paths。
- Git commit 初次因缺少 identity 失敗，之後沿用原部署 root commit 的既有作者 identity，以該次程序環境變數完成；未修改 global 或 local Git config，未臆造另一個作者。
- Push：`git push origin main` 成功；a2ad90b → 281ac77，沒有 force／history rewrite。
- sandbox DNS 失敗後依環境核准機制執行網路操作，沒有繞過 sandbox。
- Push 後 `git ls-remote origin refs/heads/main` 確認遠端 SHA 精確相同；deployment clean，local/origin main 同步。

## Cloud 與公開網址

既有網址：<https://supplychain-control-tower-demo-ue5zgscfhjn7ujvlnxwqbs.streamlit.app>

本次只執行指定網域 `/` 與 `/_stcore/health` 的 GET，timeout 20 秒，最多讀 8192 bytes，不使用 Cookie、Authorization 或 credentials，不跟隨跨網域轉址。

| UTC 時間 | 路徑 | 結果 |
|---|---|---|
| 2026-11-20 09:56:23 | / | HTTP 303，導向 share.streamlit.io 驗證流程 |
| 2026-11-20 09:56:23 | /_stcore/health | HTTP 303，同樣導向驗證流程 |

網站有 HTTP 回應，但不是健康端點 200，亦不能判定這是新版或舊版。未存取 Cloud 管理／部署日誌；無法確認自動建置是否開始、依賴更新是否完成、Cloud runtime 或新 commit 是否已載入。沒有變更 App／分享設定／URL。未建立新服務或 App。

## 保護結果、未完成與下一步

原始 src／data 既有檔案對照先前保存的逐檔 SHA-256 全部一致，既有 Runs／Published Artifacts／evidence 未寫入；原始 HEAD 未變，未 stage／commit／push。部署資料與 backend files 未變。工作準備檔留在原始 `tmp/ui121-deployment-preparation/`，未提交到部署來源。

尚未完成：Cloud redeployment 證據、Cloud logs／Python 版本、實際首頁與 UI、Guide／Planning 互動、兩語排版對比與完整 browser acceptance。Owner 已允許先部署，限制仍保留，不宣稱完整 UAT PASS。

使用者唯一必要操作：以既有帳號登入 Streamlit Community Cloud，打開既有 App 的管理頁，確認 GitHub main 最新 commit `281ac77` 的部署狀態及日誌，並用原公開網址查看 Guide 與 Planning。不要提供密碼／Token；確認後可回報部署結果或非敏感錯誤摘要。此步需要帳號登入，目前工具無法代為取得管理頁證據。
