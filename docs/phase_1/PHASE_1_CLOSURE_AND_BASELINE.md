# Phase 1 Closure and Acceptance Baseline

**Decision: PASS WITH LIMITATIONS**
**Closure date: 2026-11-19 UTC**
**Scope: Phase 1 — UAT Coverage & Reliability**

## 1. Executive Decision

Phase 1 is formally accepted as **PASS WITH LIMITATIONS** and its execution is complete within the safely executable scope. The remaining limitations below are explicitly accepted as deferred, non-blocking items for this closure. This decision does not assert that every negative Published Run end-to-end (E2E) scenario passed.

Closure is a documentation and governance decision. It does not commit the implementation, discard the dirty working tree, establish remote synchronization, or authorize Phase 2, WP3, or any subsequent implementation.

Authority: [Final Acceptance Report](PHASE_1_FINAL_ACCEPTANCE_REPORT.md), [Execution Specification](PHASE_1_EXECUTION_SPECIFICATION.md), [Execution Log](PHASE_1_EXECUTION_LOG.md), [Progress Checkpoint](PHASE_1_PROGRESS_CHECKPOINT.md), [Coverage Matrix](PHASE_1_UAT_COVERAGE_MATRIX.md), [Reliability Report](PHASE_1_RELIABILITY_REPORT.md), and [Regression Report](PHASE_1_REGRESSION_REPORT.md).

## 2. Scope and Acceptance Results

These are recorded Phase 1 results, reconciled against the available machine-readable summaries during closure. No tests, browser sessions, performance measurements, or planning workflows were rerun for closure. Different validation layers are deliberately not combined into an inflated aggregate.

| Validation layer | Recorded final result | Interpretation |
|---|---|---|
| Python method cases | 141 PASS, 0 FAIL | 13 coverage + 22 final risk + 99 reconciled safe-regression methods + 7 negative UI-presentation methods |
| Main real-browser cases | 30 PASS, 0 FAIL | Final outcomes after the documented targeted harness corrections; failed attempts remain preserved |
| Independent actual CSV/Arrow checks | 14 PASS | Actual-download and browser-payload reconciliation with native evidence |
| Chart lifecycle checks | 18 PASS | Initial load, rerun, selections, and chart/data transitions |
| Chart payload dataset checks | 28 PASS | Recorded independent validation of actual Arrow datasets |
| Performance samples | 3 | Local measurements, not three universal performance guarantees |
| Toolbar actions | 14 PASS / 2 FAIL | Known non-blocking Plant Show-chart mouse failures; not an all-pass result |

The historical complete 227-test suite was not rerun during Phase 1 final acceptance or this closure. The 99-method regression used explicit safe fixtures/adapters; it is not a claim that all original Run-producing test suites were executed unchanged.

| Gates | Accepted outcome |
|---|---|
| G00–G07 | PASS |
| G08 | PASS WITH LIMITATIONS |
| G09 | PASS |
| G10 | PASS WITH LIMITATIONS |
| G11–G13 | PASS |

G08 retains the seven negative-data E2E gaps. G10 retains the two measured mouse failures. A passing observation/measurement gate does not turn an underlying failed interaction into PASS.

Machine-readable authority: [final_acceptance.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_acceptance.json).

## 3. Negative Case Coverage Baseline

| Case | Final case status | Accepted coverage and retained boundary |
|---|---|---|
| NC-SYNTHETIC | PASS | Existing SYNTHETIC_DEMO fixture through the declared loader/browser/export workflow; not every scenario permutation |
| NC-N03 | PASS | A zero plant-week pool; not whole-horizon zero capacity or necessarily zero service |
| NC-N08 | PASS | Existing unpublished Run and disposable invalid snapshots; historical Runs were not altered |
| NC-B09 | PARTIAL | Nonzero Candidate priority changes |
| NC-N01 | PARTIAL | Missing or invalid priority |
| NC-N02 | PARTIAL | Genuine zero-demand denominator |
| NC-N04 | PARTIAL | Inventory fully covers positive demand |
| NC-N05 | PARTIAL | Nonzero opening backlog |
| NC-N06 | PARTIAL | Incompatible unit/factor |
| NC-N07 | PARTIAL | Missing product/week/endpoint |

Final case-level counts: **3 PASS, 7 PARTIAL, 0 NOT COVERED, 0 BLOCKED_PENDING_AUTHORIZATION, 0 FAIL**.

The seven PARTIAL cases passed their Python pure-comparison, memory-only fixture, and AppTest UI-presentation layers, but their Published E2E/browser negative-data sublayers remain **NOT COVERED**. The zero case-level NOT COVERED count must not obscure those sublayer gaps. The seven cases are not fully passed, and no new Published Run was manufactured to close coverage.

Evidence: [coverage_final.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_final.json), [coverage_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_results.json), [negative_ui_layers.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/negative_ui_layers.json).

## 4. Toolbar Baseline

Both remaining failures are **Plant Show-chart mouse interactions**, one at 1440×1100 and one at 1600×1100. The recorded hit tests show interception by the data grid's dvn-scroller; ordinary clicks timed out with the data view still visible. Keyboard alternatives passed in the new method-specific Phase 1 measurements. No force-click workaround or third-party asset change was introduced.

This is a known non-blocking observation, **not a resolved defect**. Historical Phase 3 D03 fields remain mouse_success=true, keyboard_success=false, chart_restored=true. The new Phase 1 keyboard evidence does not retroactively rewrite that older record or infer its restoration method.

Evidence: [toolbar_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/toolbar_results.json) and [Reliability Report](PHASE_1_RELIABILITY_REPORT.md).

## 5. Confirmed Reliability Fixes

| Risk | Confirmed behavior and narrow accepted fix |
|---|---|
| R1 | Malformed manifest roots/nested structures and container-valued Run_ID could cause uncontrolled errors or be accepted without sufficient structural validation. The loader now rejects invalid structures and Run_ID types with controlled ValueError feedback. |
| R2 | WP2 Run A→B→A transitions could clear server state without clearing the displayed Reference/priorities. Explicit state assignments synchronize reset values; the redundant multiselect default was removed. |
| R3 | Boolean values could be accepted as numeric priority 1. Comparison-boundary numeric/bool validation now rejects those inputs consistently with the planner's existing validation contract. |

The reported fixes preserved existing Planning, WP1, and WP2 business semantics. No KPI definition, fixed Reference cohort policy, allocation policy, inventory/backlog formula, or Planning Engine implementation was changed.

R4 was a confirmed test-execution hazard: fixture/setup methods could execute persisted planning. Safe allowlists/adapters were used instead of blind test discovery. That does not constitute a fourth business-logic fix.

The closure check reproduced the recorded incremental source diff from the saved pre-Phase 1 dirty copies and current files. It matched exactly. No post-acceptance source delta was found. This is a source-content verification, not a rerun of red/green tests.

Evidence: [phase1_incremental_source.diff](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/phase1_incremental_source.diff), [risk_recovery_final_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/risk_recovery_final_results.json), [regression_reconciled.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/regression_reconciled.json).

## 6. Data Provenance and Performance Limits

The primary accepted Run is sequential_20261117T133913_e22d0f430e98, classified **USER_DATA**. Its source metadata still includes **SYNTHETIC_EXAMPLE**. That distinction remains unresolved and does not constitute independently verified real operational production data.

The three performance samples are local and fixture-specific. Tracemalloc allocations are not process RSS, operational capacity certification, or SLO guarantees. The historical representative metrics CSV is 6,866,365 bytes (approximately 6.9 MB); it is not a universal file-size or performance benchmark. Existing embedded evidence/context and sidecar contracts remain intact.

Vega Infinite Extent warnings remain recorded. Phase 1 diagnostics recorded 166 warnings per viewport, 332 total, with finite-data/rendering checks and no recorded console/page errors or failed requests in those diagnostic sessions. Initialization lifecycle is a supported explanation, not proof that every warning in every dataset is harmless. Warnings were not suppressed.

Evidence: [performance_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/performance_results.json), [reliability_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/reliability_results.json), [ws2_chart_payload_validation.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/ws2_chart_payload_validation.json).

## 7. Repository and Git Baseline

Closure inspection found:

| Item | Actual closure finding |
|---|---|
| Repository root | /workspace/SupplyChain_Control_Tower_DataCo |
| Branch / configured upstream | main / origin/main |
| HEAD | b29984919342d71c9bc8d3086805058886659cc2 |
| Index | Empty; no staged paths |
| Working tree | Dirty: 20 modified tracked paths and 18 default-short untracked entries, including collapsed directories |
| Expanded untracked files before closure | 34 files |
| Comparison with Phase 1 addendum | Complete default-short Git status is identical before adding these closure documents |
| Historical initial-file preservation | Of 1,161 initial files, only the two authorized source files differ; no additional original-file changes |
| Protected register | 134 files: 2 authorized Phase 1 changes and 132 unchanged |
| New source delta after acceptance | None found |

The two authorized source files have different Git states:

| File | Current Git state | Attribution |
|---|---|---|
| dashboard/scenario_planning_app.py | Modified tracked file | Its full HEAD diff includes earlier user/MVP work. Only the exact saved pre-Phase 1-to-current incremental diff is attributed to Phase 1. |
| src/scenario_comparison.py | Untracked file, already untracked in the initial working baseline | No normal tracked HEAD diff exists. Saved pre-Phase 1 bytes/hash plus the recorded incremental diff establish the Phase 1 change and current consistency. |

The documentation HEAD alone is not a reproducible source release. The accepted implementation also depends on the dirty/untracked files. This freeze neither stages them nor claims that they are committed or remotely synchronized.

The accepted Run registry currently still contains **53 paths**, with exact equality to the original registry. The primary **13 files** match the initial snapshot hashes. All **12 artifact hashes** were independently recalculated during this closure and match the current manifest as well as the recorded integrity result. No Run was regenerated to achieve that match.

The complete pre-closure Git status and expanded untracked register are retained in Appendix A. Current source fingerprints and primary Run fingerprints are retained in Appendix B. Existing tracked modifications and untracked content remain protected.

## 8. Evidence and Runtime Cleanup

Evidence root: tmp/phase_1_reliability/20261119T034337Z_f91753/

| Evidence | Available exact reference |
|---|---|
| Final acceptance and gate summary | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_acceptance.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_acceptance.json) |
| Recorded final integrity | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity.json) |
| Final integrity addendum | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity_addendum.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity_addendum.json) |
| Interrupted-execution runtime ownership cleanup | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/runtime_original_cleanup.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/runtime_original_cleanup.json) |
| Recovery-owned 8504 cleanup | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/runtime_cleanup.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/runtime_cleanup.json) |
| Initial snapshot / Run registry | [tmp/phase_1_reliability/20261119T034337Z_f91753/initial_snapshot.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/initial_snapshot.json) |
| Fixture registry | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/fixture_registry.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/fixture_registry.json) |
| Final coverage | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_final.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_final.json) |
| Final risk tests | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/risk_recovery_final_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/risk_recovery_final_results.json) |
| Reconciled safe regression | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/regression_reconciled.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/regression_reconciled.json) |
| Negative UI layers | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/negative_ui_layers.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/negative_ui_layers.json) |
| Independent integration checks | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/integration_results_recovery.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/integration_results_recovery.json) |
| Actual export checks | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/export_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/export_results.json) |
| Reliability / lifecycle | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/reliability_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/reliability_results.json) |
| Toolbar outcomes | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/toolbar_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/toolbar_results.json) |
| Chart payload checks | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/ws2_chart_payload_validation.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/ws2_chart_payload_validation.json) |
| Performance samples | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/performance_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/performance_results.json) |
| Screenshot / trace paths and final file inventory | [tmp/phase_1_reliability/20261119T034337Z_f91753/reports/recovery_final_file_inventory.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/recovery_final_file_inventory.json) |
| Main browser results | [tmp/phase_1_reliability/20261119T034337Z_f91753/browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/browser_results.json) |
| Run-switch results | [tmp/phase_1_reliability/20261119T034337Z_f91753/green_state_browser/browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/green_state_browser/browser_results.json) |
| Fixture browser results, including retained initial zero-case failure | [tmp/phase_1_reliability/20261119T034337Z_f91753/fixture_browser/browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/fixture_browser/browser_results.json) |
| Targeted successful zero-pool retry | [tmp/phase_1_reliability/20261119T034337Z_f91753/zero_pool_retry/browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/zero_pool_retry/browser_results.json) |

Closure verified that all gate evidence references, **83 screenshot files**, and **7 trace files** listed in final_acceptance.json exist. The final file-inventory fingerprints for existing Phase 1 documents/tests/harnesses also match. The final-integrity file's SHA256 matches the digest recorded in its addendum.

These statements distinguish three levels:

1. **Exists now:** referenced files and captures are present.
2. **Previously validated:** test, browser, lifecycle, timing, and cleanup outcomes were recorded during Phase 1.
3. **Independently checked for this closure:** summary consistency, source diff/hash reconciliation, original-file preservation, Run registry, primary-file/artifact hashes, reference existence, and available inventory fingerprints.

Screenshots/traces were not replayed, all downloads were not reparsed, tests and timing were not repeated, and historical service actions cannot be re-observed by replaying a report.

The cleanup records support that original services on **8501 and 8502 were preserved**. Execution-owned **8504 (PID 2075083)** and the interrupted execution's **8503 (PID 1948318)** were stopped only after PID/command ownership verification. The first integrity snapshot predates the later 8503 cleanup; the addendum records that subsequent action. This is a chronological supplement, not a contradiction or a claim that 8503 remained running.

No unrelated user service was intentionally restarted or stopped. Closure itself performed no service operation and makes no fresh assertion about current health or PIDs.

The historical inspection initially missed services because of namespace visibility. The recorded recovery correction and later cleanup addenda take precedence over that early passive observation. No historical evidence was edited to conceal it.

The repository's ignore rules exclude tmp/. Local evidence existence is not Git or remote archival. Fingerprints identify content but cannot replace missing files on another machine. No archive/deployment/storage changes are authorized by this closure.

## 9. Accepted Deferred Items and Reopening Triggers

| Deferred item | Accepted boundary | Trigger for a separately authorized review |
|---|---|---|
| Seven NC Published E2E/browser negative-data sublayers | Python and AppTest coverage passed; full negative Published E2E remains NOT COVERED | An approved immutable, complete fixture or explicitly authorized isolated fixture strategy becomes available; or a relevant real-data defect requires investigation |
| Two Plant Show-chart mouse interactions | Non-blocking; keyboard alternatives work; no force-click fix | Mouse-only operation becomes an acceptance requirement, keyboard alternatives cease to work, accessibility requirements change, or reproducible impact becomes material |
| USER_DATA / SYNTHETIC_EXAMPLE provenance | No independent real-operational-data certification | The owner provides authoritative provenance, classification decisions, and a permitted validation scope |
| Vega warning investigation | Recorded warnings with no established material failure in accepted checks | Persistent blank/wrong-domain rendering, non-finite source data, value mismatch, or other reproducible material impact is established |

These triggers are not implementation commitments and do not authorize new Runs, warning suppression, third-party changes, new features, or relaxed acceptance criteria.

## 10. Baseline Freeze Statement

Phase 1 is formally closed with an accepted PASS WITH LIMITATIONS baseline. The scope, acceptance results, known limitations, repository state, Run preservation evidence, and evidence references recorded in this document constitute the Phase 1 closure baseline. Any future change to Phase 1 behavior or acceptance criteria must be separately authorized and documented. This closure does not authorize Phase 2, WP3, or any subsequent implementation.

## Appendix A. Pre-closure Git Working Tree

The following is the actual short-status snapshot before creation of the two closure documents. Directory entries are collapsed by Git; the expanded register follows. The new documents remain uncommitted within the already-untracked docs/phase_1 directory.

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
    ?? docs/deployment/
    ?? docs/phase_1/
    ?? docs/wp2_implementation_progress.md
    ?? docs/wp2_scenario_tradeoff_analysis_specification.md
    ?? scripts/
    ?? src/comparison_io.py
    ?? src/scenario_comparison.py
    ?? tests/test_comparison_acceptance.py
    ?? tests/test_comparison_dashboard.py
    ?? tests/test_phase1_coverage.py
    ?? tests/test_phase1_risks.py
    ?? tests/test_phase1_ui_layers.py
    ?? tests/test_scenario_comparison.py

### Expanded untracked register before closure

- .gitignore
- docs/PRODUCT_CAPABILITY_CATALOG_EN.md
- docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md
- docs/USER_GUIDE_EN.md
- docs/USER_GUIDE_ZH-TW.md
- docs/deployment/STREAMLIT_DEPLOYMENT_STATUS_REPORT.md
- docs/phase_1/PHASE_1_ASSESSMENT_REPORT.md
- docs/phase_1/PHASE_1_EXECUTION_LOG.md
- docs/phase_1/PHASE_1_EXECUTION_SPECIFICATION.md
- docs/phase_1/PHASE_1_FINAL_ACCEPTANCE_REPORT.md
- docs/phase_1/PHASE_1_PROGRESS_CHECKPOINT.md
- docs/phase_1/PHASE_1_REGRESSION_REPORT.md
- docs/phase_1/PHASE_1_RELIABILITY_REPORT.md
- docs/phase_1/PHASE_1_UAT_COVERAGE_MATRIX.md
- docs/phase_1/PHASE_1_USAGE_CONSUMPTION_FORENSIC_REPORT.md
- docs/wp2_implementation_progress.md
- docs/wp2_scenario_tradeoff_analysis_specification.md
- scripts/phase1_browser_acceptance.py
- scripts/phase1_browser_steps.py
- scripts/phase1_finalize.py
- scripts/phase1_fixture_steps.py
- scripts/phase1_reliability_probe.py
- scripts/phase1_safe_regression.py
- scripts/phase1_state_steps.py
- scripts/phase1_test_app.py
- scripts/phase1_verify_acceptance.py
- src/comparison_io.py
- src/scenario_comparison.py
- tests/test_comparison_acceptance.py
- tests/test_comparison_dashboard.py
- tests/test_phase1_coverage.py
- tests/test_phase1_risks.py
- tests/test_phase1_ui_layers.py
- tests/test_scenario_comparison.py

## Appendix B. Content Fingerprints Verified at Closure

### Authorized existing-source files

| File | Saved pre-Phase 1 SHA256 | Closure SHA256 |
| --- | --- | --- |
| dashboard/scenario_planning_app.py | a076f6136a08f7591549604fcefe06bd7af9efa571d944fd2aa384658fc3bc5c | 63b5393fdd1e9d50fc16331fbb6498b300cd4a89b1d2d7cc06b0469a52d1e418 |
| src/scenario_comparison.py | 0a34008c59b652e5647086e15da40626ca94ea747ea7c429dd2e3cce606f6ab5 | 50c74a6b6fdf7a12688d0835f3160495bdef16d4e31a11123f50c47e3a006bd7 |

Incremental source diff SHA256: d249c898291edc97ae994fc6784847fb1745ab1b351d9049faf38cffa3677352

### Primary Run files

| Primary Run-relative file | Closure SHA256 matched to initial snapshot |
| --- | --- |
| allocation_result.csv | ce193e20639952c54eb878a9679c8bdf0ef6577ab6ca77c22bebc91562e60ae8 |
| capacity_baseline.csv | f91c25afce1fab60965911d684a6d686b433d887fd72b7117ea3d228e8457994 |
| capacity_pools.csv | b44ecd4f98f81f2189f86e1d13d81d2dcf1795f93637b9d854aaf52c401d14d3 |
| demand_coverage.csv | 1a53203a0039e2e12695bfbc617d84a7d8bbc8d411dfaea40a58a133bb40e8a2 |
| eligibility_ledger.csv | 55ebfaa64646516ab7d7334bc37b2f27acecdbf1b279a995e9bbb863c7453008 |
| external_receipts.csv | 16673a57e387a0b0f0f221c3d24d7d5327b2e612e920c8fd860f7d2bc75441a3 |
| initial_state.csv | 0272c29c5bf32a676c0eaa1c0b7ed4f36bf1712a7d7e680cd70c28b844a6da17 |
| performance_result.csv | e0040cab53fcc7082aee7a20048f748bc542d230a1913fe8d9d8ed7837b5e511 |
| run_manifest.json | 9a58fe7e5e47054dbd1ce8a7512d0248da901ef0badc394d7dd2fd2c87891ab3 |
| scenario_snapshot.csv | f77d084f97ce6d4e5bcea17bd88a0c0554a4ef020f493f4086eae2d943d432f8 |
| validation_result.csv | f3e9cc7a7fb4d6de100c1bcfdbbe31430ed90510779ff2e02f7dd2294745f183 |
| weekly_demand.csv | 1a53203a0039e2e12695bfbc617d84a7d8bbc8d411dfaea40a58a133bb40e8a2 |
| workload_factors.csv | b88158e817e74bb65b66ea150312cf595547e063f3fafe3f87d8124692544f76 |

### Principal machine-readable evidence

| File | SHA256 at closure |
| --- | --- |
| tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_acceptance.json | 5980821116e22adf0084f65ac06dc00eafd7d2abdf9cf118362bddfdb38a3405 |
| tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity.json | eabfaac3c17275794c9be87ea4ca2eeed28ea93c770757319534b36b6f9f5818 |
| tmp/phase_1_reliability/20261119T034337Z_f91753/reports/final_integrity_addendum.json | 35b0e3d5543ef1b1ce2156bfeb4050c36bc2560a5b7922e3d5bc9c7a43bc098a |
| tmp/phase_1_reliability/20261119T034337Z_f91753/reports/runtime_original_cleanup.json | 44ccb3124ee85aa18436d0dd839024296337cdb8f02e0bb1ec191f960e40bf77 |
