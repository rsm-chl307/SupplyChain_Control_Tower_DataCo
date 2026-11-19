# Streamlit Community Cloud Deployment Status Audit

- 查核時間：2026-11-19 03:49 UTC（GitHub API 查詢及本機檢查於本次工作階段執行）。
- 專案：Supply Chain Copilot／SupplyChain_Control_Tower_DataCo。
- 任務：READ-ONLY DEPLOYMENT STATUS AUDIT。
- 唯一允許的寫入：本報告與其必要目錄。未變更產品、部署設定、Secrets、依賴、Git index、branch 或既有檔案；未建立 App、部署、push、fetch、commit 或操作服務。

## 1. 結論

**部署狀態：NOT CONFIGURED（以本次可取得的 repository／公開 GitHub 證據為判定範圍）。**

目前**無法確認 MVP 已部署並發布到 Streamlit Community Cloud**。沒有找到 Cloud App URL、Cloud 中的 repository／branch／entrypoint 設定紀錄、部署成功紀錄或 deployed commit。公開 GitHub deployments 回傳空陣列，Actions runs 與 HEAD checks 均為 0。

這不是「已證明任何帳號內都不存在 App」：本環境沒有已授權的 Streamlit Community Cloud 控制台工具或其帳號內 app 清單。Cloud 設定可能只存在控制台；GitHub Deployments／Actions 沒有紀錄也不保證 Cloud 沒有獨立部署。因此 NOT CONFIGURED 表示**查核範圍內未發現可驗證的 Cloud 設定**，不將證據缺漏當成已證明從未部署。

**已接受 MVP 的發布另有明確缺口：** 公開遠端 main 目前為 `b29984919342d71c9bc8d3086805058886659cc2`。此 commit 只新增兩份 acceptance 文件，未收錄目前已接受的完整 WP1／WP2 實作。即使另有 App 部署此 commit，也不能據此聲稱完整已驗收 MVP 已上線。

## 2. 八項檢查結果

| 項目 | 結果與證據 |
| --- | --- |
| 1. Repository 部署設定／紀錄 | 未找到 Streamlit Cloud 部署設定、工作流程或 Cloud 部署紀錄。找到的是本機 Streamlit 開發／UAT 紀錄。 |
| 2. Repository／branch／entrypoint | Git origin 明確為下述 GitHub repository，本機與遠端預設 branch 均為 main。entrypoint 確實是 dashboard/scenario_planning_app.py；但沒有證據顯示這三項已在 Cloud App 中設定。 |
| 3. 部署相關檔案 | 根目錄及專案子目錄（排除已安裝環境）沒有 .streamlit/config.toml、requirements.txt、packages.txt，也沒有其他列於 §4 的依賴／runtime 宣告。 |
| 4. App URL／metadata | 未找到 *.streamlit.app、share.streamlit.io 的專案 URL，亦未找到 app_url、deployment_url、deployment_id 等 metadata。GitHub repository homepage=null。 |
| 5. 成功啟動目前 MVP | 無 Cloud runtime logs、Cloud UI 證據、Cloud health 結果或 Cloud 執行版本識別。歷史 localhost UAT 不能證明 Cloud 成功啟動。 |
| 6. 遠端核實 | 已透過唯讀 GitHub 公開 REST API 成功取得 HTTP 200 結果，詳見 §5。gh CLI 未安裝，未安裝新工具。 |
| 7. 狀態分類 | NOT CONFIGURED（查核範圍限定）；其他分類之證據門檻與排除原因詳見 §7。 |
| 8. 部署 commit 含已接受實作？ | deployed commit 未知；但遠端 main 已確認不含完整 acceptance worktree。b299849 僅新增驗收文件，WP1 修改與 WP2 新模組仍未提交，詳見 §6。 |

## 3. Repository、branch 與 entrypoint

| 欄位 | 查核值 | 證據與限制 |
| --- | --- | --- |
| Git origin（fetch／push） | https://github.com/rsm-chl307/SupplyChain_Control_Tower_DataCo.git | git remote -v；未執行 fetch／push |
| Repository | [rsm-chl307/SupplyChain_Control_Tower_DataCo](https://github.com/rsm-chl307/SupplyChain_Control_Tower_DataCo) | GitHub API：public，private=false |
| 本機 branch | main | git branch --show-current |
| 本機 HEAD | b29984919342d71c9bc8d3086805058886659cc2 | git log／show |
| 本機 origin/main | b29984919342d71c9bc8d3086805058886659cc2 | 僅是本機 remote-tracking ref；另以 API 核實即時遠端 |
| GitHub default_branch | main | 即時 GitHub repository API |
| GitHub main SHA | b29984919342d71c9bc8d3086805058886659cc2 | 即時 branches/main API |
| GitHub pushed_at | 2026-11-18T17:01:38Z | repository metadata；不是 Cloud 部署時間 |
| 本機程式 entrypoint | dashboard/scenario_planning_app.py | 檔案存在、歷史設計／開發紀錄與 acceptance baseline 一致 |
| 本機啟動命令 | python -B -m streamlit run dashboard/scenario_planning_app.py | USER_GUIDE_EN／ZH-TW；本次未執行 |
| Cloud App 設定的 repo／branch／entrypoint | UNKNOWN／無可驗證紀錄 | 不把本機對應值當成 Cloud 控制台已設定 |

## 4. 本機部署檔案與紀錄

以檔案列舉、git ls-files、git log --all 的相關路徑歷史及文字搜尋交叉檢查。專案遞迴檔名檢查排除 .git、venv／.venv、site-packages、node_modules、browsers、__pycache__，避免把已安裝套件的檔案誤當專案部署宣告。

| 檔案／目錄 | 查核結果 |
| --- | --- |
| .streamlit/、.streamlit/config.toml | 不存在 |
| requirements.txt、packages.txt | 專案內未找到 |
| pyproject.toml、Pipfile、Pipfile.lock | 未找到 |
| environment.yml、environment.yaml、runtime.txt | 未找到 |
| uv.lock、poetry.lock | 未找到 |
| .github/ 與 Actions workflow | 目錄不存在 |
| git log --all -- .streamlit requirements.txt packages.txt .github | 無相關 commit 輸出 |
| deployment／streamlit 命名的 md／json／toml／yaml／txt／log 紀錄 | 排除已安裝環境後未找到 |
| Cloud URL／deployment metadata 搜尋 | 工作樹及 tmp 的指定文字格式搜尋無命中 |

Cloud URL／metadata 搜尋涵蓋 hidden 檔案與 ignored tmp（另明確指定 tmp），格式為 md、json、toml、yml、yaml、txt；排除 .git 與已安裝環境。沒有讀取 Secrets 或列印認證內容。此搜尋不是對所有二進位檔、圖片或帳號控制台的窮盡檢查。

**檔案缺漏的解讀：** .streamlit/config.toml、packages.txt、GitHub Actions／Deployments 紀錄的缺席，個別都不足以證明 Cloud App 不存在。本專案直接 import streamlit、pandas，plotly 為 optional import；缺少可重現的依賴宣告是部署準備缺口，不能直接判定已發生部署失敗。

### 找到的啟動／驗收證據屬於本機

[MVP Acceptance Baseline](../MVP_ACCEPTANCE_BASELINE.md) §4 記錄：

- Python 3.10.20／Streamlit 1.56.0，這是歷史 UAT 環境版本，本次未重新驗證。
- 實際 endpoint：`http://127.0.0.1:8502`。
- WebSocket：`ws://127.0.0.1:8502/_stcore/stream`。
- Browser venv 與 binaries 在 tmp 下；歷史服務使用 8501／8502。

[MVP Acceptance Report](../MVP_ACCEPTANCE_REPORT.md) §7 明載這些 PID／health 200 是既有 Phase 3 歷史驗證，並非遠端狀態查核。本次未探測 localhost 或任何可能喚醒休眠 App 的 Cloud URL，也未啟動、重啟、停止服務。規劃資料的「Published Run」與 Streamlit Cloud 網站發布是不同事件。

## 5. GitHub 遠端核實

gh 指令不存在（`gh: command not found`）。可用工具清單未包含 GitHub／Streamlit Cloud 帳號控制台連線工具；因此使用公開 HTTPS GET，不使用或變更帳號認證。

初始公開網頁讀取工具對 GitHub 頁面回傳 Cache miss／Internal Error；沙箱內 HTTPS 因 DNS 解析失敗。其後依環境要求請求網路升權，唯讀 API 查詢成功。這些初始工具錯誤不被當成 repository 不存在或部署失敗的證據。

| 公開 GET endpoint | HTTP | 實際結果 |
| --- | --- | --- |
| [Repository metadata](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo) | 200 | private=false；default_branch=main；homepage=null；pushed_at=2026-11-18T17:01:38Z |
| [main branch](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo/branches/main) | 200 | commit.sha=b29984919342d71c9bc8d3086805058886659cc2 |
| [Deployments](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo/deployments?per_page=100) | 200 | []，第一頁即為空；無 deployment id、environment、SHA、URL 可追查 |
| [Actions runs](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo/actions/runs?per_page=10) | 200 | total_count=0；workflow_runs=[] |
| [HEAD combined status](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo/commits/b29984919342d71c9bc8d3086805058886659cc2/status) | 200 | state=pending；total_count=0；statuses=[] |
| [HEAD check runs](https://api.github.com/repos/rsm-chl307/SupplyChain_Control_Tower_DataCo/commits/b29984919342d71c9bc8d3086805058886659cc2/check-runs) | 200 | total_count=0；check_runs=[] |

**pending 的正確解讀：** 此處同時為 total_count=0、statuses=[]，不能解讀成已有 Cloud deployment 正在建置。未取得成功或失敗的 Cloud status，也沒有 target_url。

**限制：** Streamlit Cloud 不一定透過 GitHub Actions 或 GitHub Deployments 公開部署資訊；本結果只證明上述 API 沒有對應紀錄。未取得 Cloud account app listing、build logs 或 deployed SHA，不能由 API 空值斷言其他帳號內沒有 App。

## 6. 已接受 MVP 與 commit 的差異

### 6.1 HEAD 是 acceptance documentation commit

`git show --stat HEAD` 核實：

- commit：`b29984919342d71c9bc8d3086805058886659cc2`
- subject：`docs: consolidate MVP acceptance and freeze baseline`
- 只新增 `docs/MVP_ACCEPTANCE_BASELINE.md`、`docs/MVP_ACCEPTANCE_REPORT.md`，共 684 行。
- 前一個實作 commit：`4b6c84d99173f2472de7a973c1ca98c3a4b15ec2`（Add planning risk summary and scenario analysis）。

b299849 的 tree 仍含較早的 app／planning 實作，並非空專案；問題是它未包含 acceptance 所依賴的完整後續 WP1／WP2 bytes。

### 6.2 目前已接受實作仍有未提交內容

| 檔案 | 本機狀態 | HEAD／遠端 main 的對應狀態 |
| --- | --- | --- |
| dashboard/scenario_planning_app.py | tracked modified | HEAD 有較舊版本，與 acceptance worktree 不同 |
| src/planning_risk.py | tracked modified | HEAD 有較舊版本，與 acceptance worktree 不同 |
| src/scenario_comparison.py | untracked | HEAD 不存在 |
| src/comparison_io.py | untracked | HEAD 不存在 |
| tests/test_scenario_comparison.py、test_comparison_dashboard.py、test_comparison_acceptance.py | untracked | 未提交的 WP2 測試 |

`git cat-file -e` 核實 HEAD 與 4b6c84d 均無兩個 WP2 新模組。`git show HEAD:<path>` 與本機 bytes 比對確認 app 及 planning_risk 的內容不同。

### 6.3 驗收基準與目前內容的交叉驗證

解析 [MVP Acceptance Baseline](../MVP_ACCEPTANCE_BASELINE.md) §10「Acceptance worktree: 134 protected existing files」SHA256 表格，實際唯讀重新計算：

- 134 筆全部匹配。
- 0 缺檔、0 差異。
- 此結果核對 acceptance source/content baseline，並未重跑業務測試或 Cloud UAT。

關鍵工作樹 SHA256：

| 檔案 | 本機／accepted bytes SHA256 | HEAD SHA256 |
| --- | --- | --- |
| dashboard/scenario_planning_app.py | a076f6136a08f7591549604fcefe06bd7af9efa571d944fd2aa384658fc3bc5c | 0da8d51bb71d63798557b2468660d2f34fdf15865d3a391b52aeb60c57b1df92 |
| src/planning_risk.py | fd2256b6883d74f69e8acae940258aa7e96660cd856317b315414ec02acb5987 | 143cf01d9991e87c8fdc0887d95a555cc9cbb94cc3630f074c12c7b70377c622 |
| src/scenario_comparison.py | 0a34008c59b652e5647086e15da40626ca94ea747ea7c429dd2e3cce606f6ab5 | 不存在 |
| src/comparison_io.py | 2036eb189a3a27a36ae94ce07bbf1409a574881e9791add460adc756bc578a5e | 不存在 |

**commit 查核結論：** deployed SHA 未取得，故無法證明任何 Cloud deployment 包含已接受 MVP。更明確的是，若 App 使用目前已核實的 main commit b299849，就不包含上述完整已驗收實作。只看到 acceptance documentation commit 不能當作 implementation 已發布的證據。

## 7. 五種部署狀態的判定

| 狀態 | 本報告使用的證據門檻 | 本次判定 |
| --- | --- | --- |
| NOT CONFIGURED | 查核範圍內沒有可驗證的 Cloud App 設定／註冊紀錄 | **目前採用；限可見 repository／公開 GitHub 證據** |
| CONFIGURED BUT NOT DEPLOYED | 有 Cloud App 設定或註冊證據，且可確認尚未部署 | 未取得設定或尚未部署的直接證據，不能採用 |
| DEPLOYMENT FAILED | 有已識別部署的 failed build／runtime logs 或失敗狀態 | 沒有；初始 DNS／網頁工具失敗不是部署失敗 |
| DEPLOYED | 有成功部署與可運作證據，且可識別 deployed SHA／內容包含宣稱的 MVP | 沒有；Cloud runtime、URL、SHA 都未取得 |
| DEPLOYED BUT NOT VERIFIED | 有可信的部署存在／完成紀錄，但 runtime 或 MVP 版本尚未核實 | 沒有可信的部署存在紀錄；不能僅因查核受限就稱為 DEPLOYED |

若後續取得 Cloud 控制台 app 詳情、正式 URL、build/runtime logs 與 deployed SHA，可重新分類。本次不建立 App、不補部署檔、不部署、不推送；後續發布需另行授權。

## 8. 執行與完整性紀錄

### Files inspected

- AGENTS.md；Git status、remote、branch、log、commit tree／stat 與相關檔案 diff 摘要。
- readme.md；dashboard/scenario_planning_app.py 的入口／import；src/planning_risk.py、src/scenario_comparison.py、src/comparison_io.py 的 Git 存在性與內容雜湊。
- docs/MVP_ACCEPTANCE_REPORT.md、docs/MVP_ACCEPTANCE_BASELINE.md（含 134 筆內容指紋）。
- docs/scenario_planning/dashboard_design_proposal.md、developer_notes.md、project_journal.md 與 ai_agent_implementation_spec.md 的部署／Streamlit 相關段落。
- docs/USER_GUIDE_EN.md、docs/USER_GUIDE_ZH-TW.md、docs/wp2_implementation_progress.md、docs/phase_1/PHASE_1_ASSESSMENT_REPORT.md 等搜尋命中段落；不是重新驗收這些文件中的所有歷史結論。
- 專案檔案清單、部署檔案歷史、tmp 文字紀錄的 Cloud URL／metadata 搜尋。

### Files changed／created

- 既有檔案變更：無。
- 新增：docs/deployment/STREAMLIT_DEPLOYMENT_STATUS_REPORT.md。
- 新增目錄：docs/deployment（必要時）。
- 不更新其他設計、開發或 journal 文件：本次為唯讀 audit，未完成或修改任何實作 stage。

### Tests performed／test results

| 查核 | 結果 |
| --- | --- |
| GitHub 公開 GET 共 6 項 | 全部 HTTP 200；實際值見 §5 |
| Cloud 部署相關檔案／URL 搜尋 | 無可驗證的 Cloud 設定、URL 或部署 metadata |
| Acceptance 134 檔 SHA256 | 134 matched、0 changed、0 missing |
| HEAD 與 acceptance implementation 比對 | 兩個關鍵檔不同、兩個 WP2 模組缺少 |
| 業務單元測試／AppTest／browser UAT／planning pipeline | 本次未執行，避免產生 Run、輸出或其他狀態變更 |
| Cloud runtime／health／WebSocket | 未執行：未取得正式 URL，且任務禁止服務生命週期操作 |

### Outputs generated

僅本報告。無 planning output、測試輸出、部署 artifact 或服務操作。

### Known issues／查核限制

1. 無 Streamlit Cloud 帳號控制台 app 清單、部署日誌、app URL 或 deployed SHA。
2. 公開 GitHub 無 deployment／Actions／checks 不足以排除控制台內的獨立部署。
3. 已接受 MVP 的完整實作尚未收錄於目前遠端 main；部署該 SHA 無法重現完整 acceptance worktree。
4. 現有 dirty／untracked 檔案屬於任務開始前的狀態，全部保留；不將其視為本次變更。
5. 本報告為時間點查核，GitHub 或 Cloud 後續變更不在本結論範圍。

### 本次開始時的 Git status（原有狀態）

```text
 M ai_agent_implementation_spec.md
 M dashboard/scenario_planning_app.py
 M docs/scenario_planning/dashboard_design_proposal.md
 M docs/scenario_planning/developer_notes.md
 M docs/scenario_planning/project_journal.md
 M src/__pycache__/allocation_engine.cpython-310.pyc
 M src/__pycache__/allocation_manager.cpython-310.pyc
 M src/__pycache__/allocation_validator.cpython-310.pyc
 M src/__pycache__/kpi_engine.cpython-310.pyc
 M src/__pycache__/performance_evaluator.cpython-310.pyc
 M src/__pycache__/performance_manager.cpython-310.pyc
 M src/__pycache__/planning_pipeline.cpython-310.pyc
 M src/__pycache__/planning_snapshot.cpython-310.pyc
 M src/__pycache__/run_planning.cpython-310.pyc
 M src/__pycache__/scenario_generator.cpython-310.pyc
 M src/planning_risk.py
 M tests/test_dashboard_app.py
 M tests/test_dashboard_upload_workflow.py
 M tests/test_planning_risk.py
 M tests/test_sequential_pipeline_upgrade.py
?? .gitignore
?? docs/PRODUCT_CAPABILITY_CATALOG_EN.md
?? docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md
?? docs/USER_GUIDE_EN.md
?? docs/USER_GUIDE_ZH-TW.md
?? docs/phase_1/PHASE_1_ASSESSMENT_REPORT.md
?? docs/phase_1/PHASE_1_EXECUTION_LOG.md
?? docs/phase_1/PHASE_1_EXECUTION_SPECIFICATION.md
?? docs/wp2_implementation_progress.md
?? docs/wp2_scenario_tradeoff_analysis_specification.md
?? src/comparison_io.py
?? src/scenario_comparison.py
?? tests/test_comparison_acceptance.py
?? tests/test_comparison_dashboard.py
?? tests/test_scenario_comparison.py
```

### Audit 寫入後完整性檢查

報告建立後已實際核對：任務起始記錄的 178 個既有 tracked／untracked 檔案 SHA256 全部不變；Git index SHA256 不變；HEAD 仍為 b29984919342d71c9bc8d3086805058886659cc2。本 audit 的寫入工具只建立及更新本報告。

**工作區並行變化：** 核對時另外觀察到以下 8 個新增未追蹤檔案，均非本次 audit 的工具操作建立。其建立來源未核實，未讀取、修改或刪除，因此不能宣稱整個 git status 除報告外完全不變。原有檔案的 bytes 與 index 保持不變，但無法保證其他工作階段稍後不再變更工作區。

- scripts/phase1_browser_acceptance.py
- scripts/phase1_browser_steps.py
- scripts/phase1_reliability_probe.py
- scripts/phase1_safe_regression.py
- scripts/phase1_state_steps.py
- scripts/phase1_test_app.py
- tests/test_phase1_coverage.py
- tests/test_phase1_risks.py

