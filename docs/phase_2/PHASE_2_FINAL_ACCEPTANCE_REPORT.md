# Phase 2 Final Acceptance — Authorized Service Recovery Addendum

2026-11-19 UTC. This is the **current** decision; the complete pre-recovery blocked report is preserved below as historical context and in the new recovery baseline snapshot. Original raw evidence is unchanged.

## Final decision and acceptance evidence

**Final recommendation: Phase 2 COMPLETE — PASS WITH LIMITATIONS, pending owner review.** T33 and P2-G08 now PASS. **T01–T33: 33 PASS; P2-G00–P2-G08: 9 PASS.** No required current gate remains FAIL/BLOCKED/PARTIAL. This is not a claim of complete negative-data Published E2E coverage or operational production certification.

Reused unchanged evidence: T25 **22 PASS**, safe regression **92 PASS / 0 FAIL / 0 SKIPPED**, and **eight actual CSV downloads** already parsed and byte-identical to independently verified original outputs. No full UAT, WP1/WP2 workflow, CSV download, planning or regression suite was rerun in this recovery task. The new source-reuse check matches current dashboard/helper source to recorded T25 incremental diffs; source and evidence are not assumed from HEAD alone. [acceptance_source_reuse.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/acceptance_source_reuse.json).

| Gate | Result | Basis |
| --- | --- | --- |
| P2-G00 | PASS | Baseline, explicit allowlist, owner authorization and non-publishing controls recorded. |
| P2-G01 | PASS | Original inventory/invariants preserved; paired display additions and canonical exceptions explicit. |
| P2-G02 | PASS | Workflow/state/handoff/controlled rejection evidence valid; fresh guarded regressions pass. |
| P2-G03 | PASS | No metric/semantic changes; current formatting tests and byte-identical canonical output. |
| P2-G04 | PASS | T22–T25 pass at declared layers; actual readable en/zh state/browser evidence and approved raw/external exceptions. |
| P2-G05 | PASS | Fresh actual four-format bilingual downloads equal independently verified original files; native evidence unchanged. |
| P2-G06 | PASS | 92 safe regression cases pass; three runner guards zero. Unsafe historical setup excluded, not counted as executed. |
| P2-G07 | PASS | T25 and T32 completed; current reports describe actual behavior and retained limitations. |
| P2-G08 | PASS | Final service blocker resolved under explicit recovery authorization. Source/tests/config/history unchanged; only authorized documentation delta; original accepted limitations retained. Recommend COMPLETE / PASS WITH LIMITATIONS pending owner review. |

T33/P2-G08 use the owner-authorized replacement PID for 8502; they do **not** claim the disappeared original PID was preserved or its disappearance disproved. Current recovery evidence supplements, rather than edits, the original blocked matrix: [final_acceptance.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/final_acceptance.json). Original T25/CSV/regression/final-integrity raw evidence remains unchanged under tmp/phase_2_t25/20261119T160308Z/.


## Recovery and final integrity

Original 8502 command/ownership was confirmed in Phase A, Phase 1 and T25 records before launch. It was restored with the same argv, interpreter, cwd and settings as PID **2562690**. Original 8501 PID **1117256** / start time remained unchanged. Both health endpoints return **200 / ok** and two minimum real-Chromium homepage/WebSocket checks pass. No Planning, Run loading, WP1/WP2 interaction or unnecessary regression execution occurred. The original process exit cause remains unconfirmed; no claim of OOM/container fault or preserved dead-process memory is made.

[Final Service Verification Report](PHASE_2_FINAL_SERVICE_VERIFICATION_REPORT.md) records original startup evidence, recovery steps, exact runtime results, remaining limits and scope. [final_integrity.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/final_integrity.json) records post-document scoped Git/file/Run/evidence checks. HEAD main/4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf and empty index remain unchanged; dirty user work is preserved. All 53 Run paths/manifests and 13 primary files remain unchanged. Only this final report, the execution log and new service report change in this task.

## Limitations and owner review

All previously accepted Phase 1 limitations, provenance caveat, container-local CJK fonts, raw/external translation exceptions and declared test-layer boundaries remain. The now-healthy service is not a production uptime/SLO guarantee. No required Phase 2 gate remains unresolved; root-cause forensic uncertainty is recorded as an operational limitation, not concealed or confused with a functional PASS.

**Recommendation: Phase 2 COMPLETE / PASS WITH LIMITATIONS**, awaiting the owner's final review. No source/config/dependency changes, deployment, commit/push or Phase 3/WP3.

---

# Historical pre-recovery report — BLOCKED at that time, superseded by the current addendum above

The following prior report is preserved verbatim. Its T33/P2-G08 BLOCKED statements refer to the service absence before the separately authorized recovery, not the current result.

# Phase 2 Final Acceptance Report — Consolidated Reassessment

2026-11-19 UTC — Main Agent only.

**Current verdict: BLOCKED — final service integrity prerequisite not met.** **T01–T32 PASS at their declared layers**, **T33 BLOCKED**; **P2-G00–G07 PASS**, **P2-G08 BLOCKED**. Phase 2 COMPLETE is not recommended yet. This is not full negative Published E2E or operational production certification.

## Current decision and history

| Event | Result | Evidence |
| --- | --- | --- |
| Original integrated implementation | FAIL: T25 PARTIAL, T32 FAIL | Original unmodified report archived at [PHASE_2_FINAL_ACCEPTANCE_REPORT.md](../../tmp/phase_2_t25/20261119T160308Z/baseline/PHASE_2_FINAL_ACCEPTANCE_REPORT.md); original raw evidence unchanged |
| Separately authorized CJK remediation | PASS WITH LIMITATIONS at font-only scope; not Phase 2 closure | [Remediation report](PHASE_2_CJK_RENDERING_REMEDIATION_REPORT.md) |
| Current T25 supplement | 22 unique required live browser cases PASS; actual PNG review | [Complete T25 report](PHASE_2_T25_BROWSER_COVERAGE_REPORT.md), [t25_checkpoint.json](../../tmp/phase_2_t25/20261119T160308Z/reports/t25_checkpoint.json) |
| Conditional final acceptance after T25 checkpoint | BLOCKED: final service audit | Current matrix, [coverage_matrix.json](../../tmp/phase_2_t25/20261119T160308Z/reports/coverage_matrix.json), [final_integrity.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_integrity.json) |

T25 passed before final regression and export checks were started. Historical failed attempts retain their original status, traces and screenshots. The original report reproduced below is **historical and superseded**, not the current verdict.

## Delivered scope and final corrections

P2-A inventory/invariants, P2-B workflow/context clarity, P2-C display metadata/help, P2-D centralized English-default / zh-TW presentation, and P2-E integrated testing/documentation remain the delivered packages under specification v1.1. No Run Picker, automatic tab activation, business formula, engine, schema or export change was introduced.

| Finding | Minimal correction | Verification |
| --- | --- | --- |
| Metadata Label/Definition remained English in a long-lived service | Resolve field keys from the current catalog; apply current display localization in DataFrame column configuration | I03 live WebSocket column configuration plus actual Chinese table PNG; new regression simulates an empty import-time FIELDS snapshot |
| Optional mapping sentinel remained English | Display-only format_func for the sentinel; raw CSV source headers and internal sentinel remain unchanged | I05 actual popup plus guarded mapping test retains uom / canonical sentinel |
| Upload status table cells remained English | Localize only locally constructed Dataset/Requirement/Status display rows; add four paired keys | I05 actual table PNG; required/uploaded/missing terms tested |
| Empty Reference-priority caption remained English | Localize existing empty-caption branch | R02 actual screenshot; canonical SELECTED/N/A preserved |
| Legacy dynamic summary and percentage-point units remained English | Translate recognized owned summary templates and display-table unit suffixes; retain deterministic scenario_insights, comparison_display_table and numeric helpers | L01 actual bilingual legacy screenshots; new pure template/identifier tests; no number recalculation |
| Recognized USER_PROVIDED provenance warning remained English | Localize this known warning at the presentation boundary; preserve raw readiness report/contract | V02 actual READY/provenance-warning screenshot; source warning text and data unchanged |

## Actual results — do not aggregate overlapping layers

| Evidence | PASS | FAIL | SKIPPED | Execution status |
| --- | ---: | ---: | ---: | --- |
| New final explicit safe regression allowlist | 92 | 0 | 0 | Actually executed after the T25 PASS checkpoint; [final_regression.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_regression.json) |
| New required T25 browser cases | 22 | 0 | n/a | Actual Chromium, 56 PNGs/four traces in final T25 sessions; lower-layer checks are not substituted |
| New final export browser case X01 | 1 | 0 | n/a | Eight actual parsed downloads; [browser_results.json](../../tmp/phase_2_t25/20261119T160308Z/final_exports/reports/browser_results.json) |
| Original independent numerical/CSV/native-data checks | 29 | 0 | n/a | Reused, not rerun; current downloads exactly equal their verified original bytes |
| Original en/zh negative presentation cases | 14 | 0 | n/a | Reused, not negative Published E2E |
| Original browser retry/supplement/state sessions | 12 / 7 / 5 | 0 | n/a | Historical overlapping setup/state evidence retained, not newly executed counts |

Earlier focused checks overlap the final 92 and are not added to it. Historical 227-pass full-suite acceptance is not rerun or promoted into this current count. Unsafe runner-producing fixtures remain excluded. All three guarded runner calls are zero.

## T01–T33 final matrix

| ID | Current result | Current/reused evidence and scope |
| --- | --- | --- |
| T01 | PASS | Original surface/widget/invariant inventory; new file allowlist and 11 paired translation keys recorded. |
| T02 | PASS | New 1034-file snapshot, 53 manifest paths and unchanged original evidence/downloads. |
| T03 | PASS | New guarded 92-case safe suite, runner calls [0,0,0]; actual browser never clicks planning/publishing. |
| T04 | PASS | I01/I03 guidance and workflow separation in actual en/zh-TW browser. |
| T05 | PASS | R01 visible primary Run identity; existing synthetic loader/browser evidence reused, not rerun. |
| T06 | PASS | R09 controlled unpublished-Run rejection in both locales; original nonexistent-path AppTest and current safe recheck. |
| T07 | PASS | R01/R04 five sequential surfaces; L01 three legacy surfaces in both locales, optional Plotly-unavailable fallback observed. |
| T08 | PASS | Original B15 global-scenario independence retained; relevant control/backend functions unchanged and current state tests pass. |
| T09 | PASS | R05/R07 full-key WP1 evidence and explicit Candidate handoff; actual unchanged-context exports X01. |
| T10 | PASS | R05/R06/R07 both WP1 paths and manual return to comparison. |
| T11 | PASS | R01/R02 explicit initial empty pair; existing selector regressions included in current 92-case suite. |
| T12 | PASS | Current invalid-Candidate-clearing regression and prior actual browser reset evidence reused; selector reset code unchanged. |
| T13 | PASS | Current valid-Candidate retention regression; original reverse CSV/Delta independent evidence remains valid. |
| T14 | PASS | Current A→B→A guarded regression; original actual browser Run roundtrip reused, synchronization code unchanged. |
| T15 | PASS | I03/I08 pending numeric setting; V01/V02 actual nine-file upload/mapping retained through locale change; extended guarded sentinel-state test. |
| T16 | PASS | Current display tests, original scalar-formatting arithmetic, and unchanged canonical helpers; visible legacy percentage-point unit translated only after formatting. |
| T17 | PASS | Current display definitions plus I03 technical-help screenshot; original independent horizon/current-week arithmetic retained. |
| T18 | PASS | Original 14 en/zh in-memory negative-presentation cases reused; live empty/help/policy/diagnostic surfaces I03/R02/R08. No negative Published E2E claim. |
| T19 | PASS | R02 empty priority and R03 Priority 3 fixed cohort; original CSV set/additive reconciliation, byte-identical actual X01 exports. |
| T20 | PASS | R08 bilingual policy warning; original independent 28.1→0 backlog / 0→28.1 loss and unchanged-service checks retained. |
| T21 | PASS | Original raw leading-zero/NA-like identifier tests, current canonical-field tests, live raw IDs and source/evidence fields remain accessible. |
| T22 | PASS | Current 460 paired keys, nonempty values/placeholder parity; all original 449 key/value pairs unchanged. |
| T23 | PASS | Current fallback/missing-key/missing-parameter tests; no visible missing marker in required final browser cases. |
| T24 | PASS | Current known diagnostic helper test plus I07 UTF-8 and R09 controlled-loader summaries/raw details; V02 recognized provenance warning translated. |
| T25 | PASS | 22 new required live Chromium cases, real PNG visual review, every declared surface family covered; raw/external exceptions and non-executable runner branches explicit. |
| T26 | PASS | R05 both WP1 paths; original native-key/peer/pool/trajectory safe regressions included, engine/WP1 helpers unchanged. |
| T27 | PASS | R06 actual full-key scope before/after locale and tab roundtrip; pair/cohort retained. |
| T28 | PASS | R07 Candidate-side browser handoff; original Reference-side callback/state evidence retained. No automatic tab activation. |
| T29 | PASS | Current canonical frame equality tests and eight real X01 downloads byte-identical to original verified files; backend/IO hashes unchanged. |
| T30 | PASS | X01: four actual download events per locale, parse/header/filename/context/byte checks; original 29 independent export checks reused. |
| T31 | PASS | Original actual WP1 native-grain CSV and Published KPI artifact download evidence retained; export functions and artifacts unchanged. |
| T32 | PASS | L02 live Chromium CDP: Noto Sans CJK JP supplies 8 glyphs in app heading; actual live WP1/WP2/chart/table/diagnostic PNGs readable after prior authorized fonts-noto-cjk remediation. |
| T33 | BLOCKED | Files/Run/artifact/Git/document checks PASS; final service preservation prerequisite not met. Final service audit: original port 8502 process PID 1503434 is absent and health connection is refused; cause unconfirmed. Port 8501 PID 1117256 remains present and health 200. No service restart/stop was issued by this task. Restore/restart is outside current authorization. |

## P2-G00–P2-G08 final matrix

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

## CSV, KPI, WP1/WP2 and provenance

Four formats (metrics/cohort/evidence/context), two locales, eight fresh browser downloads parse successfully. They are **byte-identical** to original independent-check inputs. Normal/reversed/policy historical arithmetic remains valid because the original input/download evidence and all backend/IO source hashes remain unchanged; current canonical frame/state tests pass. No formulas, numerator/denominator/grain, origin policy, fixed Reference cohort, same-Run rule, reason, native evidence, Comparison_ID, filename or schema changed.

The accepted Run remains sequential_20261117T133913_e22d0f430e98, USER_DATA with SYNTHETIC_EXAMPLE source metadata. This does not establish independently verified real operational data. The two optional status-description display rows and legacy summaries do not feed planning or exporters.

## CJK, UI and telemetry

T32 is now **PASS for the current runtime**: prior authorized Noto CJK installation plus live Chromium platform-font evidence and actual readable chart/table/WP1/WP2/diagnostic PNGs. The browser selected Noto Sans CJK JP for the tested heading; it is not claimed to default to the TC face. Containers rebuilt without fonts may regress; persistence/deployment remains outside scope.

Final sessions have 0 console errors/page errors/failed requests/WebSocket errors, and 252 recorded warnings (244 Vega Infinite extent, 8 external Popper). These are retained observations, not suppressed or universally declared harmless. [T25 report](PHASE_2_T25_BROWSER_COVERAGE_REPORT.md) lists counts, screenshots, all failed attempts, minimal fixes, raw/external exceptions and exact evidence paths.

## Integrity and final file scope

HEAD before/after: **4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf**, branch main; index empty. Worktree remains dirty. Initial 1034 existing fingerprints protect user work, Runs and original evidence. Six existing code/test files changed within the explicit allowlist; two requested reports updated and one T25 report added. No unrelated source/test/specification/manual/Phase 1/history modification in this task. [preservation_review.json](../../tmp/phase_2_t25/20261119T160308Z/reports/preservation_review.json) verifies original translation values and pre-existing test bytes are preserved around the additions.

Exact task delta:

- dashboard/scenario_planning_app.py
- dashboard/display_metadata.py
- dashboard/locales/en.json
- dashboard/locales/zh-TW.json
- tests/test_phase2_i18n.py
- tests/test_phase2_workflow.py
- docs/phase_2/PHASE_2_EXECUTION_LOG.md
- docs/phase_2/PHASE_2_FINAL_ACCEPTANCE_REPORT.md
- New docs/phase_2/PHASE_2_T25_BROWSER_COVERAGE_REPORT.md
- New isolated harness/logs/downloads/screenshots/traces/JSONs under tmp/phase_2_t25/20261119T160308Z; no old evidence overwritten.

All 53 Run paths preserved, 13 primary files unchanged, 12 manifest artifact hashes match. Earlier during-execution services were healthy; final audit finds port 8502 original PID absent and health connection refused. Port 8501 remains at original PID with health 200. git diff --check passes. Final evidence: [final_integrity.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_integrity.json) and [final_document_checks.json](../../tmp/phase_2_t25/20261119T160308Z/reports/final_document_checks.json). No planning, publication, dependency changes, service-control operations, commit, push or deployment were performed by this task; the final observed service absence is explicitly unresolved below.

## Accepted limitations and stop

- Seven Phase 1 NC cases remain PARTIAL at their accepted layers; their negative-data Published E2E/browser sublayers remain NOT COVERED. This work creates no negative Published Run and does not promote those cases to full PASS.
- Two Plant Show-chart mouse interactions and recorded Vega warnings remain inherited observations. No toolbar or warning suppression fix was attempted.
- The accepted Run is USER_DATA while source metadata contains SYNTHETIC_EXAMPLE. It is not independently verified operational production data.
- CJK fonts were installed in the preceding separately authorized remediation. This task installs nothing. They remain container-local and may disappear on container recreation; no Docker/deployment persistence work is implied.
- Completed browser acceptance used the existing service on port 8502 before its subsequently observed exit. Initial port 8501 attempts served old cached display metadata despite identical on-disk hashes; this was preserved as evidence. Port 8501 was neither restarted nor certified as serving this updated UI. Runtime rollout/reload is outside this task; health is checked on both ports.
- Plotly is unavailable in the current app runtime; the existing localized fallback was tested. There is no claim of newly executed Plotly-renderer visual acceptance.
- Browser checks are bounded representative workflows in Chromium at 1600×1100, combined with valid original 1440/1600 evidence. They are not every browser/viewport, every source-data permutation or every possible backend failure.
- Success/failure branches that require executing planning/publication were not triggered; their dictionary/static coverage is distinct from live browser acceptance. No lower-layer result is called Published E2E coverage.

T33 and P2-G08 remain BLOCKED on final service integrity. Completed functional evidence is retained: T01–T32 PASS, including T25 and T32. The seven Phase 1 PARTIAL NC cases remain PARTIAL; these are not reclassified. Do not declare Phase 2 COMPLETE; await a separate owner decision on service restoration and a final integrity recheck. No Phase 3, WP3 or additional work is begun.

---

## Final unresolved blocker — service availability

At 2026-11-19T16:44:26Z the final read-only audit found **PID 1503434 absent**, and port **8502 health connection refused**. Port 8501 retains PID 1117256 and health 200. Earlier during-execution evidence had both original processes and health 200. The 22 T25 cases, 92 safe regressions and eight download events completed before this final observation; their actual records remain valid, but they do not establish final service preservation.

Exact evidence: [services_during.json](../../tmp/phase_2_t25/20261119T160308Z/reports/services_during.json) and [services_final_observation.json](../../tmp/phase_2_t25/20261119T160308Z/reports/services_final_observation.json). The available cgroup memory.events records zero OOM/oom_kill, which does **not** establish the exit cause or rule out every external/system cause. No cause is inferred and no silent repair is made. No stop/restart/kill/service-configuration command was issued by this task.

**Impact:** final service invariants cannot pass. T33/P2-G08 are BLOCKED; final verdict BLOCKED, rather than accepting this as a non-blocking limitation. File/Git/Run/artifact/evidence integrity checks still pass. No completion standard has been lowered.

**Required owner decision:** authorize restoration of the existing 8502 service and the resulting targeted final service/current-code verification, or provide an explicit service-scope decision. Do not rerun completed suites merely to reproduce already valid results. This task does not restart the service.


# Historical original report — superseded, preserved verbatim

The following text records the original pre-remediation execution. Its FAIL/PARTIAL and font-authorization statements are historical only. Consult the consolidated current decision above and the unmodified original raw evidence for the distinction.

# Phase 2 Integrated Implementation and Final Review

**Overall verdict: FAIL — not accepted for closure.**

All five authorized packages were executed as one Main-Agent task, without interim owner approvals. Code, documentation and safe functional/data validation are delivered. Required Chinese visual readability failed in the existing Chromium runtime; this is not masked by a PASS WITH LIMITATIONS result. Final owner review is required. No Phase 3/WP3, commit/push or deployment follows automatically.

## 1. Authority, baseline and package disposition

The [v1.1 specification](PHASE_2_IMPLEMENTATION_SPECIFICATION.md) records OWNER-AUTHORIZED FOR INTEGRATED IMPLEMENTATION — P2-A THROUGH P2-E and approved OD01–OD09. Original v1.0 bytes remain in the version-history archive under the evidence root. [Inventory and invariants](PHASE_2_INVENTORY_AND_INVARIANTS.md) and [execution log](PHASE_2_EXECUTION_LOG.md) contain the exact allowlist, state/glossary/contract design and chronological failures/fixes.

Actual starting HEAD: 4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf on main, empty index. Ten pre-existing tracked cache changes, the untracked forensic report and untracked v1.0 specification were preserved; the specification is intentionally updated within authorization, with the original archived. The repository was never assumed clean.

| Package | Delivered | Result |
| --- | --- | --- |
| P2-A | Original 203-site UI inventory, current widget/key inventory, canonical glossary, data/state invariants and exact allowlist | COMPLETE internal checkpoint |
| P2-C | Central canonical metadata, metric bases/units/precision/status/cohort help and display-only table/chart adapters | Functional checks PASS |
| P2-B | Prepare/Analyze guidance, manual Run loading help, view-purpose/global-versus-pair context and manual WP1 handoff guidance | Functional checks PASS |
| P2-D | English default, zh-TW catalogs/helper, stable controls/locale restore and form-local language application | IMPLEMENTED; visual acceptance FAIL |
| P2-E | Paired/current-scope docs, staged tests/browser/CSV/integrity and this consolidated report | Reporting complete; acceptance NOT GRANTED |

## 2. Actual implementation

- 449 paired central dictionary keys for application-owned labels/help, known field headings, metric definitions, statuses/cohorts and recognized diagnostic summaries. Metadata references canonical translation keys; no duplicate engine or KPI calculation.
- English default; CSV-mode Language selector is inside the existing planning form. Apply language and keep form inputs transmits pending state only, never validation/planning. Other modes use the sidebar. Existing pending numeric edits and retained-file bytes/mappings/model return were validated at their declared layers.
- Stable explicit keys for previously unkeyed controls; locale formatters bind the selected locale at widget creation. Transient button/download states are excluded from restoration. Existing invalid Candidate reset, valid Candidate retention and Run A→B→A clearing remain.
- DataFrames passed to computational/export code remain canonical; Streamlit column_config labels and chart copies provide presentation only. IDs, raw statuses, original reasons, source content, serialized JSON and filenames remain accessible/unchanged.
- No new Run Picker, automatic tab activation, task router or scenario creation. WP2 side/product handoff retains existing global scenario/WP1 semantics and explicitly instructs manual destination navigation.

## 3. Tests actually executed

Counts are separate; repeated checkpoints are not added into an inflated total.

| Execution | PASS | FAIL / ERROR | SKIPPED | Evidence |
| --- | --- | --- | --- | --- |
| Final explicit safe regression allowlist | 88 | 0 | 0 | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/final_regression.json](../../tmp/phase_2_ui/20261119T134451Z/reports/final_regression.json) |
| Affected display/i18n/workflow recheck after catalog enrichment | 18 | 0 | 0 | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/logs/final_affected_recheck.log](../../tmp/phase_2_ui/20261119T134451Z/logs/final_affected_recheck.log) |
| Additional retained-existing-upload/mapping/model/locale test | 1 | 0 | 0 | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/logs/upload_state_targeted.log](../../tmp/phase_2_ui/20261119T134451Z/logs/upload_state_targeted.log) |
| Existing negative presentation cases reused in en/zh-TW | 14 | 0 | 0 | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/negative_presentation_recheck.json](../../tmp/phase_2_ui/20261119T134451Z/reports/negative_presentation_recheck.json) |
| Stable real-browser retry session | 12 | 0 | n/a | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/browser_retry/reports/browser_results.json](../../tmp/phase_2_ui/20261119T134451Z/browser_retry/reports/browser_results.json) |
| Browser reverse/policy/export/legacy/viewport supplement | 7 | 0 | n/a | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/browser_supplement/reports/browser_results.json](../../tmp/phase_2_ui/20261119T134451Z/browser_supplement/reports/browser_results.json) |
| Browser global-scenario independence / rejected-existing-Run session | 5 | 0 | n/a | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/browser_state/reports/browser_results.json](../../tmp/phase_2_ui/20261119T134451Z/browser_state/reports/browser_results.json) |
| Independent actual CSV/native-data checks | 29 | 0 | n/a | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/export_validation.json](../../tmp/phase_2_ui/20261119T134451Z/reports/export_validation.json) |
| Actual screenshot Chinese glyph readability | 0 | 1 | n/a | [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/visual_readability.json](../../tmp/phase_2_ui/20261119T134451Z/reports/visual_readability.json) |

The 18-case recheck overlaps the 88-case suite. Browser session counts include repeated homepage/pair/locale setup, not 24 unique coverage cases. The 14 negative checks are memory/AppTest presentation only; they do not close any Phase 1 Published E2E gap. No historical 227/full discovery suite was rerun.

Actual commands (all logs below the evidence root):

- python3 -B -m unittest tests.test_phase2_display -v; then display + i18n, then guarded test_phase2_workflow checkpoints.
- python3 -B scripts/phase2_safe_regression.py --root /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z
- python3 -B -m unittest tests.test_phase2_display tests.test_phase2_i18n tests.test_phase2_workflow -v (18 cases at that execution).
- python3 -B -m unittest tests.test_phase2_workflow.WorkflowTests.test_retained_existing_upload_mapping_survives_language_and_model_round_trip -v
- python3 -B /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/recheck_negative.py (adapts only reporter ROOT in memory; does not set environment variables or change existing test files).
- tmp/wp2_browser_uat_phase_a/venv/bin/python -B scripts/phase2_browser_acceptance.py --root <new-session-root>, with --supplement / --state-only for bounded follow-ups.
- python3 -B /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/verify_exports.py

The allowlist includes original inventory/conservation/input/sequential engine, risk/native evidence, legacy dashboard and Candidate synchronization tests, plus Phase 2 helpers/workflow cases. Three persisted planning runner guards report [0, 0, 0]. Run-producing test setups/pipeline/publication tests were excluded after inspection. The upload retention test seeds bytes from an existing example in memory, not a new browser dataset upload or Run. No new negative fixture, planning/publication or dependency was used to force coverage.

## 4. Failed attempts and narrow fixes

| Attempt | Actual failure | Resolution / current status |
| --- | --- | --- |
| Initial workflow | 1 PASS / 7 FAIL: constant explicit key reused in Published download loop | Canonical filename-based stable keys; fixed |
| Next workflow | 6 PASS / 2 FAIL: Series chart adapter assumed DataFrame; button state restored illegally | Series/name-aware display copy; exclude transient keys; fixed |
| Next workflow | 7 PASS / 1 ERROR: AppTest invoked a locale formatter outside script context | Bind locale in display formatter; targeted and final affected tests pass |
| First browser | 9 PASS / 3 FAIL: hidden evidence download / manual-tab locator context | Harness explicitly opens evidence/navigates tabs; retry passes; no comparison/data code fix |
| State-only launch | Log directory missing before process execution | Created only the dedicated output folders; retry passes |
| Chinese screenshot review | Actual Chinese labels are boxed glyphs | OPEN / FAIL; no font/package/environment fix authorized |

Original failed logs/screenshots/trace remain; successful retries do not erase them. [Checkpoint register](../../tmp/phase_2_ui/20261119T134451Z/reports/checkpoints.json) records commands/counts. Initial browser evidence is [preserved here](../../tmp/phase_2_ui/20261119T134451Z/reports/browser_results.json).

## 5. Data, CSV and evidence verification

Independent native CSV arithmetic validated normal, reverse and policy comparisons: each file has 36 Delta rows and 72 side-value checks, totaling 216 scalar values and 108 Delta checks. Oracle calculations sum native demand/fulfillment/workload flows or terminal item endpoints; they do not call the KPI/comparison function under test. All 29 grouped checks passed.

The stable successful browser sessions captured **12 actual downloads**: four WP2 files in each locale (eight), one native WP1 selection, reverse metrics, policy metrics and original Published KPI CSV. en/zh-TW filenames and bytes matched for all four WP2 exports. Parsing checked schemas, Run/scenario context, disjoint/comprehensive fixed Reference membership, evidence artifacts/full-record duplicates and source hashes. The Published KPI download equals the original artifact bytes. All 12 primary manifest artifact hashes match.

Policy evidence independently confirms ALL terminal backlog 28.1→0, lost sales 0→28.1 and approximately unchanged horizon service. No preferred winner/service-improvement inference was introduced. Shared capacity remains separate; no cohort utilization claim.

Twenty original calculation/input/loader/source-status/upload-preservation dashboard function ASTs are unchanged. Every existing backend src file is unchanged. These checks supplement executed regressions; they are not a new claim that all planning/publication workflows or negative Published E2E combinations were exercised.

## 6. Browser, visual failure and telemetry

Confirmed new acceptance issue **P2-ENV-01**: actual Chromium screenshots show boxed Traditional Chinese glyphs, despite correct Unicode DOM strings, translated controls and successful language/state interaction. This makes zh-TW text unreadable in this runtime. Runtime font/glyph capability is the likely cause; exact OS-level cause was not independently proven. The inspected shell lacks fc-list and visible standard font files are DejaVu. No font/dependency/OS/configuration change was attempted.

Evidence: [actual WP2 Chinese screenshot](../../tmp/phase_2_ui/20261119T134451Z/browser_retry/screenshots/pair_zh.png) and [actual legacy Chinese screenshot](../../tmp/phase_2_ui/20261119T134451Z/browser_supplement/screenshots/legacy_zh.png). Screenshots were genuinely captured and visually inspected; no rendering substitutions or fabricated screenshots.

| Successful session | Console warnings | Infinite extent messages | Page errors | Failed requests |
| --- | --- | --- | --- | --- |
| retry | 198 | 197 | 0 | 0 |
| supplement | 41 | 38 | 0 | 0 |
| state | 47 | 46 | 0 | 0 |

WebSocket receive activity and errors are recorded per session. Warning counts are incidental diagnostics, not a new lifecycle investigation or operational benchmark. No suppression, toolbar fix, force-click or third-party patch was introduced. English/Chinese DOM and state checks do not establish visual readability. Two approved viewport sizes were exercised; Chinese readability fails at the actual runtime irrespective of functional assertions.

## 7. Acceptance gates and coverage

| Gate | Outcome | Basis |
| --- | --- | --- |
| P2-G00 | PASS | Actual baseline, allowlist, safe execution and approved OD01–OD09 |
| P2-G01 | PASS | UI/widget/glossary/state inventory and definition contracts |
| P2-G02 | PASS | Representative actual workflow, handoff, state and controlled rejection checks |
| P2-G03 | PASS | Display/helper definitions and unchanged canonical numeric outputs |
| P2-G04 | FAIL | Functional dictionary/locale checks pass; required readable zh-TW visual experience does not |
| P2-G05 | PASS | Actual downloads, independent arithmetic, identifiers, native evidence and artifact hashes |
| P2-G06 | PASS | Explicit safe regressions, zero persisted runner calls; unsafe suites explicitly excluded |
| P2-G07 | FAIL | Documentation updated but current zh-TW visual sign-off unavailable; T25 browser breadth partial |
| P2-G08 | FAIL for closure | Repository/data integrity passes; required visual criteria prevent formal acceptance |

| Planned case | Outcome | Executed scope / limitation |
| --- | --- | --- |
| T01 | PASS | Static UI/widget/key/glossary inventory and file allowlist (D) |
| T02 | PASS | Initial file/Run snapshot and raw download hashes (D/X) |
| T03 | PASS | Safe suite runner guards all zero; browser only allowlisted actions (A/B) |
| T04 | PASS | WorkflowTests.test_default_empty_and_guidance; browser homepage (A/B) |
| T05 | PASS | Existing primary/synthetic loader and visible identity (A/B) |
| T06 | PASS | AppTest nonexistent path and browser existing unpublished Run controlled rejection (A/B) |
| T07 | PASS | Purpose help and representative sequential/legacy three-tab browser navigation (D/B) |
| T08 | PASS | browser_state B15 global Demand_Surge leaves independent pair unchanged (B) |
| T09 | PASS | Explicit side/product/full-key handoff and actual context-bearing downloads (A/B/X) |
| T10 | PASS | Existing Run, comparison, both WP1 paths and manual return navigation (B) |
| T11 | PASS | Fresh empty selectors then explicit pair; old selector safe regressions (A/B) |
| T12 | PASS | Candidate visibly cleared then manually selected; no auto alternative (A/B) |
| T13 | PASS | Valid Candidate retention AppTest; reverse CSV independent Delta validation (A/B/X) |
| T14 | PASS | A→B→A AppTest and browser empty selector checks; priority [] asserted in AppTest (A/B) |
| T15 | PASS | Browser pending numeric form value; AppTest retains existing bytes/mapping/settings/model/locale. No real browser file upload (A/B) |
| T16 | PASS | Pure formatting/immutability tests; no double scaling (P) |
| T17 | PASS | Legacy/horizon help distinction and independent current/horizon arithmetic (P/X) |
| T18 | PASS | Existing in-memory negative UI cases en/zh plus policy/normal browser states; no new negative E2E (A/B) |
| T19 | PASS | Empty/default and Priority 3 fixed membership, CSV set reconciliation (A/B/X) |
| T20 | PASS | Policy warning, unchanged service, backlog 28.1→0 and loss 0→28.1 verified independently (B/X) |
| T21 | PASS | Canonical raw frames/IDs retained; leading-zero/NA cases in existing in-memory presentation tests (A/X) |
| T22 | PASS | 449-key en/zh parity, nonempty strings and named-placeholder tests (P) |
| T23 | PASS | Unsupported locale, missing key and missing parameter behavior tested (P) |
| T24 | PASS | Recognized zero-denominator summary retains original; existing unpublished-run browser rejection (P/B) |
| T25 | PARTIAL | Static owned-text inventory and representative both-model/locale flows pass; not every generated message exercised in a browser; see explicit raw/external exceptions (D/A/B) |
| T26 | PASS | Both WP1 paths exercised; original native-key/peer/pool/trajectory pure regression retained (P/A/B) |
| T27 | PASS | Existing tab return and locale retain valid investigation/pair state at declared representative scope (A/B) |
| T28 | PASS | Candidate-side real browser handoff; existing side callback contract and original tests. No invented tab activation (A/B) |
| T29 | PASS | Canonical frames equal under locale switch and actual same-context CSV bytes; source backend hashes unchanged (A/X) |
| T30 | PASS | Four actual downloads per locale; parse/header/context/filename/byte equality (B/X) |
| T31 | PASS | Actual representative WP1 CSV and original Published KPI artifact bytes match (B/X) |
| T32 | FAIL | Chinese glyphs render as boxes in actual current Chromium screenshots; English/browser interactions work. No font/runtime change authorized (B/visual) |
| T33 | PASS | Final scoped file/Run integrity and documentation checks; not an overall acceptance claim (D/X) |

No planned test is called a full negative Published E2E pass merely because it has a helper/AppTest result. T25 is explicitly PARTIAL: the owned-text inventory is implemented and representative paths tested, not every possible generated diagnostic in a browser. T32 is a confirmed FAIL.

## 8. Known limitations, deferred work and authorization boundary

- Seven inherited NC cases remain PARTIAL; their negative Published E2E/browser sublayers remain NOT COVERED. No new fixture/Run was manufactured.
- Two Plant Show-chart mouse observations remain non-blocking inherited observations, not fixed or remeasured. Keyboard history is preserved without rewriting Phase 3 D03.
- USER_DATA classification still has SYNTHETIC_EXAMPLE metadata; not independently verified real operational data.
- Vega warnings remain recorded; no universal harmlessness claim. Historical large CSV/local timings are not production SLOs.
- Original backend/technical/third-party details, user/source data and machine values remain canonical; unknown field identifiers stay visible. This is not a promise to translate all raw/external text.
- Runtime/clean-checkout dependency preparation, ignored evidence archival and service PID provenance were not newly established. Existing services' health was 200 before/after; no start/stop/restart command was issued. Initial PIDs were not independently sampled.

**Required next decision:** separately authorize a CJK-capable browser/font runtime, or provide an already approved readable CJK-capable browser for targeted visual acceptance. No font installation, network font dependency, deployment or infrastructure workaround is authorized by this implementation. Do not begin another product phase to resolve this silently. Complete the remaining diagnostic/UI browser breadth only within a reviewed safe scope.

## 9. Exact file changes and preservation

Modified existing files (includes the previously untracked authorized v1.0 specification, archived before editing):

- ai_agent_implementation_spec.md
- dashboard/scenario_planning_app.py
- docs/PRODUCT_CAPABILITY_CATALOG_EN.md
- docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md
- docs/USER_GUIDE_EN.md
- docs/USER_GUIDE_ZH-TW.md
- docs/phase_2/PHASE_2_IMPLEMENTATION_SPECIFICATION.md
- docs/planning_csv_inputs.md
- docs/scenario_planning/dashboard_design_proposal.md
- docs/scenario_planning/developer_notes.md
- docs/scenario_planning/project_journal.md

New files:

- dashboard/display_metadata.py
- dashboard/i18n.py
- dashboard/locales/en.json
- dashboard/locales/zh-TW.json
- tests/test_phase2_display.py
- tests/test_phase2_i18n.py
- tests/test_phase2_workflow.py
- scripts/phase2_browser_acceptance.py
- scripts/phase2_safe_regression.py
- docs/phase_2/PHASE_2_INVENTORY_AND_INVARIANTS.md
- docs/phase_2/PHASE_2_EXECUTION_LOG.md
- docs/phase_2/PHASE_2_FINAL_ACCEPTANCE_REPORT.md

Evidence root: /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/. Test/helper scripts and output snapshots beneath it are test-only; original evidence is not overwritten. Principal report references:

- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/test_results.json](../../tmp/phase_2_ui/20261119T134451Z/reports/test_results.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/coverage_matrix.json](../../tmp/phase_2_ui/20261119T134451Z/reports/coverage_matrix.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/final_regression.json](../../tmp/phase_2_ui/20261119T134451Z/reports/final_regression.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/export_validation.json](../../tmp/phase_2_ui/20261119T134451Z/reports/export_validation.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/negative_presentation_recheck.json](../../tmp/phase_2_ui/20261119T134451Z/reports/negative_presentation_recheck.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/visual_readability.json](../../tmp/phase_2_ui/20261119T134451Z/reports/visual_readability.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/final_integrity.json](../../tmp/phase_2_ui/20261119T134451Z/reports/final_integrity.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/widget_inventory.json](../../tmp/phase_2_ui/20261119T134451Z/reports/widget_inventory.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/translation_inventory.json](../../tmp/phase_2_ui/20261119T134451Z/reports/translation_inventory.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/file_allowlist.json](../../tmp/phase_2_ui/20261119T134451Z/reports/file_allowlist.json)
- [/workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_2_ui/20261119T134451Z/reports/historical_evidence_check.json](../../tmp/phase_2_ui/20261119T134451Z/reports/historical_evidence_check.json)

## 10. Final integrity and stop

Final integrity verification is recorded below after the last documentation write. This task stops with FAIL and one consolidated review package; it does not formally close Phase 2 as accepted. No commit, push, deployment, next stage or WP3 was performed. Existing user cache/forensic content remains; the working tree is intentionally dirty.

Final integrity **PASS**: HEAD remains 4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf on main; index empty. 867/878 initial file fingerprints remain identical; the 11 differences are exactly authorized source/documentation edits. 12 new Git-visible files are all allowlisted. Original cache/forensic content is unchanged. All 53 Run manifest paths and original Run-adjacent hashes remain preserved; no backend src changes. Twenty protected dashboard function ASTs match, the original v1.0 archive matches and four principal historical Phase 1 evidence hashes match their closure fingerprints. Health checks returned 200 on 8501/8502 before and after; no PID-comparison claim is made. git diff --check returned 0. Full Git statuses and exact path lists are in final_integrity.json. Overall acceptance remains **FAIL**, separately from integrity.

Retained execution output paths and fingerprints: [evidence_inventory.json](../../tmp/phase_2_ui/20261119T134451Z/reports/evidence_inventory.json). This index excludes its own recursive digest. Latest post-enrichment browser screenshot also confirms the glyph failure: [global/pair context](../../tmp/phase_2_ui/20261119T134451Z/browser_state/screenshots/global_pair_independent.png).
