# Phase 2 T25 Browser Coverage Completion Report

Date: 2026-11-19 UTC. Main Agent only. **T25: PASS** at the declared application-surface/workflow scope. **T32: PASS** for current live Chromium readable-CJK rendering. Phase 2 final acceptance: **BLOCKED** on the subsequent service-integrity audit; no COMPLETE recommendation.

**後續結論：**上述 BLOCKED 是此報告當時的服務稽核狀態。其後服務已依授權恢復並完成最終驗收；目前結果以[最終服務驗證報告](PHASE_2_FINAL_SERVICE_VERIFICATION_REPORT.md)及[整合驗收報告](PHASE_2_FINAL_ACCEPTANCE_REPORT.md)為準：T33／P2-G08 PASS，Phase 2 建議 COMPLETE — PASS WITH LIMITATIONS，待 owner review。

## Scope, method and sequential authorization

Read the current implementation specification v1.1, inventory/invariants, original final report, CJK diagnostic and remediation reports before testing. Their fingerprints are in [preflight_documents.json](../../tmp/phase_2_t25/20261119T160308Z/reports/preflight_documents.json). Baseline and explicit file allowlist were captured before edits. No subagents, service restart, package/environment changes, planning/publication or new Runs.

Real Chromium interactions use the existing 8502 Streamlit service and existing USER_DATA Run sequential_20261117T133913_e22d0f430e98; existing unpublished sequential_20261117T124401_d4d42e5adb4f is used for safe loader rejection. Existing examples/planning/user_data CSVs are uploaded in browser memory for preview and **Validate inputs only**, not Validate and run planning. The invalid UTF-8 diagnostic uses a disposable three-byte browser input, not a business-data Run fixture.

Acceptance combines actual button/selector/file-preview interactions, observable UI checks, WebSocket dataframe column metadata, actual downloads, real screenshots opened for visual review and CDP platform-font evidence. It does not substitute DOM text presence or frozen HTML for live visual acceptance. [T25 PASS checkpoint](../../tmp/phase_2_t25/20261119T160308Z/reports/t25_checkpoint.json) was written **before** final acceptance regression/export execution.

## Original missing breadth and completed coverage

Original T25 was PARTIAL: static translation inventory and representative workflows existed, but input/mapping/diagnostic families, comprehensive surface navigation and readable live Chinese WP1/WP2 evidence were insufficient. The CJK remediation had only home/form live checks and frozen investigation/comparison views. This execution fills those actual-browser gaps.

| Case | Required behavior / observed scope | Result | Evidence |
| --- | --- | --- | --- |
| I01 | English shell, prepare/analyze guidance and no active Run | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I01_home_en.png) |
| I02 | English owned readiness BLOCKED summary; no planning | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I02_blocked_en.png) |
| I03 | Actual Chinese metadata headings and pending form state | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I03_metadata_zh.png) |
| I04 | Chinese owned readiness summary with canonical raw details | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I04_blocked_zh.png) |
| I05 | Chinese mapping sentinel without changing canonical value/headers | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I05_mapping_zh.png) |
| I06 | Owned assumption/help labels readable; no assumptions silently applied | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I06_assumptions_zh.png) |
| I07 | Owned Chinese diagnostic summary preserves low-level UTF-8 error detail | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I07_csv_diagnostic_zh.png) |
| I08 | Language roundtrip retains numeric setting and original file data/error detail | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/input_final/screenshots/I08_return_en.png) |
| R01 | Live English main surfaces and explicit empty comparison guidance | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R01_Scenario_Overview.png) |
| R02 | Chinese empty priority caption and explicit selector placeholders | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R02_empty_zh.png) |
| R03 | Live Chinese pair/cohort/status/help/evidence surfaces | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R03_pair_zh.png) |
| R04 | Chinese main views, product/plant/scenario risk with readable chart labels | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R04_情境概觀.png) |
| R05 | Both WP1 paths and native evidence expansion in live Chinese UI | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R05_product_path_zh.png) |
| R06 | Locale roundtrip retains full WP1 scope and WP2 pair/cohort; English risk text | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R06_wp1_en.png) |
| R07 | Explicit Candidate handoff keeps raw IDs and requires manual tab navigation | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R07_handoff_zh.png) |
| R08 | Owned policy warning in both languages, raw status and IDs preserved | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R08_policy_zh.png) |
| R09 | Controlled loader rejection, translated summary with original reason and no stale export | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/screenshots/R09_reject_en.png) |
| R10 | WebSocket, no page/request failures and no visible missing-key marker | PASS | [Result JSON](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/reports/browser_results.json) |
| L01 | Legacy main surfaces and Plotly charts in English/Chinese without executing planning | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/legacy_final_units/screenshots/L01_Scenario_Overview.png) |
| L02 | Actual CJK glyph font usage in live Chromium application heading | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/legacy_final_units/screenshots/L02_live_cjk.png) |
| V01 | Existing CSV inputs validate READY with English summaries and source/configuration details, no planning | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/ready_final/screenshots/V01_ready_en.png) |
| V02 | Chinese READY summary and validation details after locale switch retain actual uploads/mapping | PASS | [Actual screenshot](../../tmp/phase_2_t25/20261119T160308Z/ready_final/screenshots/V02_ready_zh.png) |

Final required T25 supplement: **22 PASS / 0 FAIL / 0 NOT COVERED**, unique case IDs I01–I08, R01–R10, L01–L02, V01–V02. Final sessions contain 56 actual PNGs and four traces. Additional final-acceptance X01 is reported separately, not added to the T25 count. Original negative Published E2E gaps remain outside this count.

All screenshots, expected/actual details, browser warnings, requests and WebSocket records are retained in:

- [input_final result](../../tmp/phase_2_t25/20261119T160308Z/input_final/reports/browser_results.json); [actual trace](../../tmp/phase_2_t25/20261119T160308Z/input_final/traces/browser.zip)
- [results_attempt_3 result](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/reports/browser_results.json); [actual trace](../../tmp/phase_2_t25/20261119T160308Z/results_attempt_3/traces/browser.zip)
- [legacy_final_units result](../../tmp/phase_2_t25/20261119T160308Z/legacy_final_units/reports/browser_results.json); [actual trace](../../tmp/phase_2_t25/20261119T160308Z/legacy_final_units/traces/browser.zip)
- [ready_final result](../../tmp/phase_2_t25/20261119T160308Z/ready_final/reports/browser_results.json); [actual trace](../../tmp/phase_2_t25/20261119T160308Z/ready_final/traces/browser.zip)

## Browser and font environment

Existing Python Playwright venv: tmp/wp2_browser_uat_phase_a/venv. Chromium Headless Shell 159.0.8154.6, existing executable under tmp/wp2_browser_uat_phase_a/browsers/chromium_headless_shell-1255/. Viewport 1600×1100. Prior authorized Debian fonts-noto-cjk 1:20240730+repack1-1 remains installed.

L02 CDP reports **Noto Sans CJK JP**, eight actual glyphs for the live Chinese heading. This establishes font use and non-box rendering; it does not assert that Chromium selected the TC face by default. Prior Fontconfig/FreeType TC-face checks remain in the remediation report. Actual reviewed PNGs show readable Traditional Chinese in technical help, controls, native tables, WP1, WP2, policy/empty/diagnostic states and a rendered Vega chart legend. [Visual review paths](../../tmp/phase_2_t25/20261119T160308Z/reports/t25_checkpoint.json) records representative files; the overview chart screenshot was also opened and inspected. No image was fabricated or substituted.

## Confirmed display fixes

| Finding | Minimal correction | Verification |
| --- | --- | --- |
| Metadata Label/Definition remained English in a long-lived service | Resolve field keys from the current catalog; apply current display localization in DataFrame column configuration | I03 live WebSocket column configuration plus actual Chinese table PNG; new regression simulates an empty import-time FIELDS snapshot |
| Optional mapping sentinel remained English | Display-only format_func for the sentinel; raw CSV source headers and internal sentinel remain unchanged | I05 actual popup plus guarded mapping test retains uom / canonical sentinel |
| Upload status table cells remained English | Localize only locally constructed Dataset/Requirement/Status display rows; add four paired keys | I05 actual table PNG; required/uploaded/missing terms tested |
| Empty Reference-priority caption remained English | Localize existing empty-caption branch | R02 actual screenshot; canonical SELECTED/N/A preserved |
| Legacy dynamic summary and percentage-point units remained English | Translate recognized owned summary templates and display-table unit suffixes; retain deterministic scenario_insights, comparison_display_table and numeric helpers | L01 actual bilingual legacy screenshots; new pure template/identifier tests; no number recalculation |
| Recognized USER_PROVIDED provenance warning remained English | Localize this known warning at the presentation boundary; preserve raw readiness report/contract | V02 actual READY/provenance-warning screenshot; source warning text and data unchanged |

Implementation changes are limited to dashboard/scenario_planning_app.py, dashboard/display_metadata.py, the two locale dictionaries and two existing Phase 2 tests. dashboard/i18n.py is byte-identical to the pre-task snapshot. Eleven keys were appended in each locale (449→460); every prior translation remains unchanged. The three new test methods plus the extended mapping-state test preserve all pre-existing test bytes when their additions are removed: [preservation_review.json](../../tmp/phase_2_t25/20261119T160308Z/reports/preservation_review.json).

## Original failures and retries

All attempts remain in separate directories; no original JSON/PNG/trace was overwritten.

- input_attempt_1: I03 failed on actual English metadata headings (2 PASS / 1 FAIL). input_attempt_2/3 preserved the same unresolved observation in port 8501; fresh source hashes matched. input_attempt_4 on existing port 8502 passed I03 and exposed the actual English mapping sentinel (4 PASS / 1 FAIL).
- input_attempt_5 passed the mapping fix but I06 used an incorrect exact get_by_label selector for a custom selectbox (5 PASS / 1 FAIL). The test locator alone was corrected; input_attempt_6 and the post-status-cell-fix input_final each passed all eight cases.
- results_attempt_1 exposed the actual empty-priority caption leak (1 PASS / 1 FAIL). results_attempt_2 passed five cases then failed because the harness searched for Investigate product instead of the visible Investigation product in the other WP1 path. Only the locator/expected text was corrected; results_attempt_3 passed all ten cases.
- legacy_attempt_1 passed navigation but the CDP probe failed because CSS agent was not enabled (1 PASS / 1 FAIL). Enabling read-only DOM/CSS agents corrected the diagnostic harness; legacy_attempt_2 passed. Visual review then found actual untranslated owned summary/unit text; legacy_final and legacy_final_units document successive minimal fixes and successful rechecks. The last session is the final L01/L02 evidence.
- ready_attempt_1 assumed DOM file-input order matched the dictionary despite two-column layout, then could not find the status selector. ready_attempt_2 used the correct upload field but the wrong English Map columns wait label. These are preserved harness setup failures, before READY acceptance. ready_attempt_3 passed two cases; visual review exposed the recognized English provenance-warning detail. After its display-only correction, ready_final passed both cases.
- A failed raw attempt is not relabeled PASS. Final counts refer to the 22 unique required case IDs using the last applicable valid evidence, not a sum of retries.

## Translation boundary and honest coverage

| Content | Policy / observed examples |
| --- | --- |
| App-owned UI text | Translate navigation, labels/help, summaries, known diagnostic/provenance families, upload status cells and display units |
| Canonical identifiers / technical field names | Retain Run_ID, Scenario values, Comparison_ID, filenames, artifact/source/evidence identifiers, JSON keys and unmapped canonical column IDs such as Bottleneck_Weeks / Source_SHA256; they remain technical identifiers, not hidden translated business values |
| Machine values / original data | Retain ALL/SELECTED/COMPLEMENT, COMPARABLE/DESCRIPTIVE_ONLY/BLOCKED/POLICY_CONTRAST/READY, source classifications, reasons, user names/CSV headers and IDs; surrounding help explains them in the selected language |
| Raw diagnostics | I07 UTF-8 details and R09 original loader reason remain original below a localized owned summary; no machine reason/CSV is translated |
| External UI | Streamlit Upload/Deploy, grid empty/search controls, Vega date ticks, browser/framework text remain external; not counted as application translation failures |

This is complete coverage of the declared available application-owned surface families, combining the original inventory/AppTest evidence with the new browser cases. It is not a claim that each of 460 keys was independently clicked on screen or that every unsafe planning/error branch was executed. Data-dependent negative Published E2E remains explicitly untested. No requirement was weakened to turn such cases into PASS.

## Telemetry and final acceptance

Across final input/results/legacy/ready/export sessions: **0 console errors, 0 page errors, 0 failed requests, 0 WebSocket errors**. There are **252 warning messages**: 244 Vega Infinite extent and 8 external Popper preventOverflow/hide warnings; session counts are 0 / 211 / 2 / 0 / 39. These are observed counts for these sessions, not a performance benchmark. Chart PNGs visibly render; warning provenance is retained and no assertion that all warnings are universally harmless is made. [telemetry_summary.json](../../tmp/phase_2_t25/20261119T160308Z/reports/telemetry_summary.json).

After T25 passed, the final safe suite ran: **92 PASS / 0 FAIL / 0 SKIPPED**, three runner guard counts zero. [final_regression.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_regression.json). Focused 6/7/8/13-case checks overlap this suite and are not inflated into an aggregate.

X01 captured eight actual download events (four formats × two locales). Each parsed and equaled the original independently checked file byte-for-byte, including context, identifiers, headers/order and values. [browser_results.json](../../tmp/phase_2_t25/20261119T160308Z/final_exports/reports/browser_results.json). Original 29 independent numerical/export checks and 14 negative-presentation cases are reused as historical evidence, not described as rerun.

| Gate | Final result | Basis |
| --- | --- | --- |
| P2-G00 | PASS | Baseline, explicit allowlist, owner authorization and non-publishing controls recorded. |
| P2-G01 | PASS | Original inventory/invariants preserved; paired display additions and canonical exceptions explicit. |
| P2-G02 | PASS | Workflow/state/handoff/controlled rejection evidence valid; fresh guarded regressions pass. |
| P2-G03 | PASS | No metric/semantic changes; current formatting tests and byte-identical canonical output. |
| P2-G04 | PASS | T22–T25 pass at declared layers; actual readable en/zh state/browser evidence and approved raw/external exceptions. |
| P2-G05 | PASS | Fresh actual four-format bilingual downloads equal independently verified original files; native evidence unchanged. |
| P2-G06 | PASS | 92 safe regression cases pass; three runner guards zero. Unsafe historical setup excluded, not counted as executed. |
| P2-G07 | PASS | T25 and T32 completed; current reports describe actual behavior and retained limitations. |
| P2-G08 | BLOCKED | Final service audit: original port 8502 process PID 1503434 is absent and health connection is refused; cause unconfirmed. Port 8501 PID 1117256 remains present and health 200. No service restart/stop was issued by this task. Restore/restart is outside current authorization. No COMPLETE recommendation. |

## Integrity, limits and remaining risks

[final_integrity.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_integrity.json) records HEAD/index/status, exact allowed changes, backend/Run/artifact/evidence hashes and documentation checks. HEAD remains 4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf on main, index empty and dirty worktree preserved. Existing Run manifest paths remain **53→53**; all **13 primary files unchanged**, **12/12 manifest artifact hashes match**; original Phase 2/CJK evidence remains unchanged. At the earlier during-execution audit, both original service PIDs were present and both health endpoints returned 200. The final audit supersedes that observation: PID 1503434 / port 8502 is absent and connection is refused; PID 1117256 / port 8501 remains healthy (200). Final post-document checks are part of P2-G08, not a test-suite rerun.

- Seven Phase 1 NC cases remain PARTIAL at their accepted layers; their negative-data Published E2E/browser sublayers remain NOT COVERED. This work creates no negative Published Run and does not promote those cases to full PASS.
- Two Plant Show-chart mouse interactions and recorded Vega warnings remain inherited observations. No toolbar or warning suppression fix was attempted.
- The accepted Run is USER_DATA while source metadata contains SYNTHETIC_EXAMPLE. It is not independently verified operational production data.
- CJK fonts were installed in the preceding separately authorized remediation. This task installs nothing. They remain container-local and may disappear on container recreation; no Docker/deployment persistence work is implied.
- Completed browser acceptance used the existing service on port 8502 before its subsequently observed exit. Initial port 8501 attempts served old cached display metadata despite identical on-disk hashes; this was preserved as evidence. Port 8501 was neither restarted nor certified as serving this updated UI. Runtime rollout/reload is outside this task; health is checked on both ports.
- Plotly is unavailable in the current app runtime; the existing localized fallback was tested. There is no claim of newly executed Plotly-renderer visual acceptance.
- Browser checks are bounded representative workflows in Chromium at 1600×1100, combined with valid original 1440/1600 evidence. They are not every browser/viewport, every source-data permutation or every possible backend failure.
- Success/failure branches that require executing planning/publication were not triggered; their dictionary/static coverage is distinct from live browser acceptance. No lower-layer result is called Published E2E coverage.

## Commands and retained evidence

- tmp/wp2_browser_uat_phase_a/venv/bin/python -B tmp/phase_2_t25/20261119T160308Z/t25_browser.py --root <new attempt directory> --stage input|results|legacy|ready --url http://127.0.0.1:8502
- python3 -B -m unittest tests.test_phase2_i18n tests.test_phase2_display -v (13 PASS; focused display/helper checkpoint).
- python3 -B -m unittest tests.test_phase2_i18n tests.test_phase2_workflow.WorkflowTests.test_retained_existing_upload_mapping_survives_language_and_model_round_trip -v (8 PASS at that checkpoint).
- python3 -B scripts/phase2_safe_regression.py --root tmp/phase_2_t25/20261119T160308Z (92 PASS; final acceptance only after T25 checkpoint).
- Browser command above with --stage exports (X01 PASS; eight actual downloads).
- python3 -B tmp/phase_2_t25/20261119T160308Z/check_integrity.py; git diff --check; documentation link/syntax checks. Exact per-attempt logs and the harness are retained under tmp/phase_2_t25/20261119T160308Z.

**Stop:** T25 completed, but final acceptance is BLOCKED on service integrity. Do not declare Phase 2 COMPLETE. Owner decision is required for restoring port 8502 and repeating the final service verification only; no commit/push/deployment, Phase 3 or WP3.

## Final unresolved blocker — service availability

At 2026-11-19T16:44:26Z the final read-only audit found **PID 1503434 absent**, and port **8502 health connection refused**. Port 8501 retains PID 1117256 and health 200. Earlier during-execution evidence had both original processes and health 200. The 22 T25 cases, 92 safe regressions and eight download events completed before this final observation; their actual records remain valid, but they do not establish final service preservation.

Exact evidence: [services_during.json](../../tmp/phase_2_t25/20261119T160308Z/reports/services_during.json) and [services_final_observation.json](../../tmp/phase_2_t25/20261119T160308Z/reports/services_final_observation.json). The available cgroup memory.events records zero OOM/oom_kill, which does **not** establish the exit cause or rule out every external/system cause. No cause is inferred and no silent repair is made. No stop/restart/kill/service-configuration command was issued by this task.

**Impact:** final service invariants cannot pass. T33/P2-G08 are BLOCKED; final verdict BLOCKED, rather than accepting this as a non-blocking limitation. File/Git/Run/artifact/evidence integrity checks still pass. No completion standard has been lowered.

**Required owner decision:** authorize restoration of the existing 8502 service and the resulting targeted final service/current-code verification, or provide an explicit service-scope decision. Do not rerun completed suites merely to reproduce already valid results. This task does not restart the service.
