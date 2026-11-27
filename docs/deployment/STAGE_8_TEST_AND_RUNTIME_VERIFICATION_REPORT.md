# Stage 8 — test and runtime verification

Date: 2026-11-26. Objective: verify WP8.1–WP8.5 locally under Python 3.12.16. No Cloud deployment, production Secret or paid AI call. All `python` tests below used `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python` unless stated otherwise. Counts overlap and are not added into a unique total.

## Executed tests

| Exact command / procedure | Environment | Passed | Failed | Skipped | Result and limit |
| --- | --- | ---: | ---: | ---: | --- |
| `.venv312/bin/python -B -m unittest tests.test_stage8_local_runtime tests.test_stage7_cloud_release` | Local worktree; Stage 7 test module is uncommitted and depends on uncommitted P5 lock; packaged subprocess uses 3.12 with no API key | 5 | 0 | 0 | PASS locally; not a clean-source Stage 7 acceptance test |
| `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_stage8_local_runtime tests.test_dashboard_app tests.test_comparison_dashboard tests.test_phase2_workflow` | Fresh HEAD archive plus exact Stage 7 builder/allowlist and Stage 8 test files | 28 | 0 | 0 | PASS; reproduces proposed published source without developer-local Runs |
| `.venv312/bin/python -B -m unittest tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_question tests.test_stage6_cloud_provider` | Local 3.12, Fake/offline | 35 | 0 | 0 | PASS; no real provider call |
| `.venv312/bin/python -B -m unittest tests.test_run_planning tests.test_planning_pipeline tests.test_planning_risk tests.test_scenario_generator tests.test_scenario_comparison tests.test_inventory_transition tests.test_phase1_risks` | Local 3.12 Planning Engine | 119 | 0 | 0 | PASS; source business rules unchanged |
| `.venv312/bin/python -B -m unittest tests.test_phase2_workflow tests.test_synthetic_context_lifecycle tests.test_ui_v12_user_guide tests.test_ui_v121_content tests.test_stage4_cloud_ai_ui` | Local 3.12 with root and test-only pins | 28 | 0 | 0 | PASS after test dependency and fixture repair; no Cloud browser |
| `.venv312/bin/python -B -m unittest tests.test_phase2_workflow` | Local 3.12 after self-generated fixture repair | 10 | 0 | 0 | PASS |
| `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_phase2_workflow` | Fresh `git archive HEAD` source plus only the repaired test file | 10 | 0 | 0 | PASS; no developer-local `tmp` Run needed |
| `.venv312/bin/python -B -m unittest tests.test_dashboard_app tests.test_comparison_dashboard` | Local 3.12 after allowed-root fixture repair | 17 | 0 | 0 | PASS; legacy dashboard uses reference data where present |
| `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_dashboard_app tests.test_comparison_dashboard` | Fresh `git archive HEAD` source plus only repaired test files | 17 | 0 | 0 | PASS; generated Runs use the UI allowlisted, Git-ignored test root |
| `.venv312/bin/python -m pip check` | Project Python 3.12 environment | — | — | — | PASS: no broken requirements |

Initial diagnostic runs are retained as history: the first combined 3.12 UI command had one import error because the existing content test imported undeclared `markdown_it`; adding `requirements-test.txt` and installing `markdown-it-py==4.0.0` resolved it. The first Dashboard/WP2 run had missing widgets because its tests generated Runs outside the UI path allowlist; fixing test fixture locations resolved all affected tests. These diagnostics are not counted as final passes.

## Package, native dependency and runtime checks

- `.venv312/bin/python -m pip install -r requirements.txt`: PASS from the configured package index; Streamlit 1.56.0, Pandas 2.3.3, NumPy 2.2.6, Plotly 6.5.2 and jsonschema 4.26.0 match root pins. The first sandbox attempt failed DNS; the authorized outside-sandbox run succeeded. `.venv312/bin/python -m pip install -r requirements-test.txt` installed the separate Markdown test parser. Native imports of NumPy, Pandas, PyArrow, Plotly, Streamlit and jsonschema passed.
- Two independent `build()` calls using Python 3.12: 74 identical paths and byte-identical `CLOUD_RELEASE_MANIFEST.json`; all 74 SHA-256 hashes matched; zero extra files, symlinks, `.venv312`, Secret files or targeted credential/private-key patterns. Candidate-a is `/tmp/sct-stage8-312-rc-f7by6htu/candidate-a`; candidate-b is its sibling. Manifest SHA-256 is `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`.
- Candidate-a subprocess with Python 3.12 and `OPENAI_API_KEY`, `AI_REAL_PROVIDER_ENABLED`, `PYTHONPATH` removed: `STAGE8_PACKAGE_PROBE_PASS 13`. AppTest started Planning, verified Planning did not read AI Secrets, showed locked Copilot and a missing-configuration warning, then ran the packaged synthetic JSON through the UI. The resulting risk/WP1 scenario selector and WP2 reference/candidate controls appeared; selecting Baseline versus Combined_Stress produced the comparison table. A separate direct `run_csv_planning` check generated 13 Planning output paths. The submitted synthetic password was absent from captured stdout/stderr. No provider dispatch occurred.
- Candidate-a `streamlit run dashboard/scenario_planning_app.py --server.headless=true --server.address=127.0.0.1 --server.port=8766` using `.venv312/bin/python`: localhost `/_stcore/health` returned HTTP 200 with `ok`; local server log passed targeted secret scan. The server was stopped after the check. Sandbox socket binding is denied, so this check ran outside the sandbox. HTTP health does not establish browser or Community Cloud behavior.
- `git diff --check`, AST/whitespace and targeted secret-pattern checks are final review gates. Existing Streamlit `use_container_width` deprecation and bare-mode warnings did not fail assertions.

## Functional scope and limitations

Planning Engine calculations remain authoritative. The 3.12 regressions cover planning, inventory, scenario comparison, risk, WP1/WP2 and Dashboard behavior. The Cloud package carries the synthetic fixture and upload code, but intentionally excludes `data/processed` reference artifacts; the historical independent-week Executive Dashboard can show its existing unavailable-data message in that package. Full legacy reference-data display was not demonstrated from the Cloud candidate. The Copilot path stayed Fake/locked and no key was read for public Planning.

## Cloud runtime acceptance procedure — prepared, NOT EXECUTED

After separate deployment approval, record the exact source repository, branch, reviewed commit SHA, deployment-source manifest and file list. Select Python 3.12 in Streamlit Community Cloud settings; use `dashboard/scenario_planning_app.py` as entrypoint and root `requirements.txt` for runtime dependencies. Keep test-only `requirements-test.txt`, `.venv312`, local P5/Windows, `tmp` and `secrets.toml` out of the release. Verify installation logs and effective runtime/package versions, then confirm health and inspect startup logs.

The reviewed local runtime configuration is `.streamlit/config.toml` (`maxUploadSize=2`, `maxMessageSize=10`). Synthetic fixture/CSV templates, bilingual locale and guide resources are in the 74-file manifest. Planning uploads and generated Runs use temporary session storage; they are not durable after a Cloud restart. Public Planning requires no AI Secret. The backend credential adapter reads `OPENAI_API_KEY` only for a separately enabled AI request; the public candidate was tested with no key and the Copilot access gate closed. No client response or local log in these checks contained a credential pattern. This inspection cannot prove Cloud account-level Secret isolation.

| Actual Cloud acceptance check | Required evidence | Status |
| --- | --- | --- |
| Repository, branch and deployed version | Reviewed source paths, manifest hash, Git commit SHA and App settings SHA match | **NOT EXECUTED** |
| Runtime install and startup | Python 3.12 version, full dependency install log, entrypoint/config, health and startup logs | **NOT EXECUTED** |
| Public accessibility | Anonymous browser opens the intended URL and sharing state is recorded | **NOT EXECUTED** |
| Planning and scenarios | Upload and packaged JSON flows, deterministic output/KPI comparison, exports and input errors | **NOT EXECUTED** |
| Risk, WP1 and WP2 | Browser navigation, comparison/handoff, evidence and unavailable-data behavior | **NOT EXECUTED** |
| Dashboard and UX | Synthetic-supported views, explicit legacy reference-data limitation, locale and guide | **NOT EXECUTED** |
| Optional AI configuration | Missing key leaves public functions available and Copilot closed; no provider call | **NOT EXECUTED** |
| Security and operations | Browser payloads, downloads and logs contain no credentials; temp files/retention and rollback recorded | **NOT EXECUTED** |

Using an unauthenticated public browser with no AI key, verify Planning upload/JSON paths, synthetic scenario execution, risk/WP1/WP2 views, exports, missing/invalid input errors, locale/guide, the legacy Dashboard unavailable-data message and the locked Copilot configuration message. Compare at least one Planning output and KPI to the deterministic local fixture; verify no client response, downloadable artifact or log contains credentials. Record public URL, sharing state, deployed SHA, Python version, test counts, screenshots or browser trace, startup/error logs, data retention limits and rollback reference. Mark each failed or unavailable capability explicitly. Real AI and production Secrets require separate approval.

**Actual Cloud deployment, runtime verification and Owner acceptance: NOT EXECUTED.** Stage 7 acceptance is independent and unchanged.
