# WP2 implementation progress

## Phase 0 — inspection and registration (2026-11-18)

Authoritative baseline: [Implementation Specification v1.0](wp2_scenario_tradeoff_analysis_specification.md). Full supplied 13-section text registered because repository-wide Markdown search found no existing Phase 3 WP2 specification. Historical Route B WP2 is a different scope. The later Master Implementation Prompt authorizes WP2.1–WP2.4 sequential implementation; the specification's original pending-authorization text is retained as history.

Branch `main`, HEAD `4b6c84d99173f2472de7a973c1ca98c3a4b15ec2`. Existing WP1 changes, tests, caches and tmp outputs are protected. Pre-edit source/test hashes, dashboard function AST hashes and Git status are saved in `tmp/wp2_acceptance/pre_wp2_baseline.json`. No reset, commit or push.

Inspected: AGENTS.md, current dashboard loader/navigation/upload/investigation, planning_risk product horizon and evidence helpers, planning_inputs contracts, sequential KPI implementation, runner manifest publication, csv input units/provenance, both example configurations, existing risk/pipeline/dashboard/upload tests, project journal/developer notes/legacy specification and architecture alignment report. Existing schema is sequential_v1: 12 hash-backed CSV artifacts, manifest SUCCEEDED/PASSED/PUBLISHED; product-week states and independent plant-week pools. Product horizon helper validates unrelated risk fields and computes risk classifications; use the existing KPI engine for service/backlog aggregation instead of duplicating formulas. WP1 evidence helpers remain unchanged.

## Implementation plan and stage gates

| Stage | Scope / expected files | Validation gate |
| --- | --- | --- |
| WP2.1 | New `src/scenario_comparison.py` dataclasses and in-memory identity/key checks; new `src/comparison_io.py` loader wrapper reusing existing dashboard loader; `tests/test_scenario_comparison.py` foundation tests | Valid manifests, hashes, schema, artifacts, identity, keys and immutability |
| WP2.2 | Pure cohort / metric comparison using existing `calculate_sequential_kpis`; fixed reference membership, full horizon, weekly grain, shared pool context | Direction, cohorts, rates, stocks, losses, workload, units and grain tests |
| WP2.3 | Per-metric validation, policy contrast, input differences, lineage and CSV serialization in comparison modules | Missing coverage, incompatible units/factors, all statuses, evidence, deterministic export, both modes |
| WP2.4 | Add one trade-off tab to existing dashboard; leave WP1/upload functions intact; new `tests/test_comparison_dashboard.py` | AppTest both modes, explicit selectors, cohorts/status/download, WP1 and upload regressions |
| Acceptance | Full unittest discovery, independent hand-derived business assertions, pre-edit hash/AST checks, diff review | All stage suites and full regression pass; no core/WP1 changes |

Dependencies: stage 2 consumes validated stage 1 inputs; stage 3 enriches stage 2 output; stage 4 consumes the complete pure API. Every stage records actual commands/counts below before proceeding. No new dependencies; no cross-run/replay/scenario generation/actions/AI/PBIX. IO stays outside pure comparison.

Risks: published engine lacks backlog age detail, so only full horizon service is supported; priority/receipt/opening/eligibility/capacity-basis differences must be disclosed; workload definitions can block workload while quantity metrics remain available. Empty cohorts and zero denominators remain N/A. Invalid integrity rejects runs; data coverage failures block affected metrics rather than shrink scope. UI uses explicit unselected scenario controls and no preselected priority.

## Baseline

Full regression running; result recorded before WP2.1 gate.

## WP2.1 — passed

New files: `src/scenario_comparison.py`, `src/comparison_io.py`, `tests/test_scenario_comparison.py`. Dataclasses preserve explicit scenario identity; pure validation checks all required tables, publication/schema/identity and native keys. IO wrapper reuses WP1 loader and adds manifest row-count checks. Core and WP1 files unchanged.

Executed `python -B -m unittest discover -s tests`: baseline 181 passed, 0 failed, 0 skipped (80.147s), log `tmp/wp2_acceptance/baseline_tests.log`. Executed `python -B -m unittest discover -s tests -p test_scenario_comparison.py`: 4 passed, 0 failed/skipped, log `tmp/wp2_acceptance/wp2_1_tests.log`. Initial foundation runs exposed new-validator assumptions about blank non-applicable performance dimensions and capacity baseline grain; fixed validation to respect actual per-level dimensions and optional weekly capacity baseline before passing. No existing helper changed. No unresolved stage blocker; proceed to WP2.2.

## WP2.2 — passed

Extended `src/scenario_comparison.py` and `tests/test_scenario_comparison.py`. Explicit same-run scenarios, deterministic context, fixed reference membership and complements, priority flags, weighted horizon/weekly service (percentage-point deltas), fulfilled quantity, same-week unfulfilled flows, three terminal backlog measures, lost sales and workload flows. Existing `calculate_sequential_kpis` supplies service/backlog metrics without formula changes. Shared pools remain independent context rows, counted once, with no cohort utilization label. Complete horizon and declared opening-item coverage are checked before aggregation.

Executed `python -B -m unittest discover -s tests -p test_scenario_comparison.py`: cumulative 14 passed, 0 failed/skipped (8.799s), including 10 core tests plus 4 foundation tests; `tmp/wp2_acceptance/wp2_2_tests.log`. Manual component sums verify numerator/denominator, terminal endpoint, lost sales and capacity totals. No test failures in this stage. No core or WP1 modifications. Proceed to WP2.3.

## WP2.3 — passed

Extended both comparison modules and comparison tests. Added COMPARABLE/DESCRIPTIVE_ONLY/BLOCKED per metric, explicit POLICY_CONTRAST and missing policy handling, input difference checks (opening, receipts, priority, eligibility, allocation policy, quantity step, workload definitions and capacity basis), workload incompatibility gates, native evidence references with hashes/provenance, and four context-bearing CSV exports. Every rate retains its actual numerator/denominator; incompatible or unavailable deltas remain N/A. No winner/recommendation layer.

Executed cumulative comparison suite: 33 passed, 0 failed/skipped (35.089s); `tmp/wp2_acceptance/wp2_3_tests.log`. Includes previous core checks and both modes, missing product/week/endpoint, factor incompatibility, evidence/no-fanout, scope rejection and deterministic export. Initial stage run failed two tests: row permutations exposed float-summation-order tails in CSV; fixed by sorting native keys before aggregation. The policy test incorrectly expected descriptive status for a zero-denominator weekly cohort; corrected to require BLOCKED/N/A there and DESCRIPTIVE_ONLY for defined values. Rerun passed. Evidence rows remain separate from measures; no original WP1 export changes. Proceed to WP2.4.

## WP2.4 — passed

Modified only `dashboard/scenario_planning_app.py` among existing source/test files: new trade-off tab and presentation helpers, explicit unselected Reference/Candidate controls, empty-by-default priority selection, fixed membership/priority flags, three-group summary/detail, metric reasons, independent pool context, evidence and four CSV downloads. New `tests/test_comparison_dashboard.py` covers both modes and read-only WP1 handoff. Original WP1 functions, upload functions and risk logic remain byte/AST unchanged; `_sequential_views` alone has the new tab and a stable key for existing scenario selection.

UI suite: 5 passed, 0 failed/skipped (42.591s), log `tmp/wp2_acceptance/wp2_4_ui_tests.log`. Existing dashboard/upload suite: 12 passed, 0 failed/skipped (18.159s), log `tmp/wp2_acceptance/wp2_4_regression_tests.log`. Initial UI run had two assertions inspect truncated DataFrame text rather than cells; corrected the assertions. Also fixed presentation-only mixed date/numeric/N/A columns to use consistent strings where missing, avoiding Arrow fallback serialization errors. No business result changes.

Read-only audit identified legitimate historical OUT_OF_SCOPE coverage rows retained by the source adapter; comparison coverage now checks declared horizon rows while preserving historical evidence, with a dedicated regression test. This is a scope-validation correction, not silent intersection or missing-week filling. Additional final acceptance file `tests/test_comparison_acceptance.py` supplies an independent hand-calculated two-product/two-week oracle, including zero capacity/demand, inventory coverage and opening-origin backlog. Initial acceptance fixture setup attempts were rejected by existing adapter constraints (capacity multiplier >1, missing required Baseline scenario, wrong receipt quantity header); corrected the fixture to the inspected existing contracts without changing engine/adapter rules. Final acceptance results follow.

## Final acceptance report

### A. Specification verification

Registered complete supplied Implementation Specification v1.0 at `docs/wp2_scenario_tradeoff_analysis_specification.md` (561 lines, all 13 numbered sections). Repository-wide search including hidden Markdown files found no earlier Phase 3 WP2 v1.0 document; no historical Route B document was substituted. SHA256: `202e38c96a946031a229d6fd4ceeccba0a92cc78b1d78951a6a39fe35f7a6956`. Original pending-authorization language remains historical; the later Master Prompt authorizes this implementation.

### B. Implementation summary

WP2.1 foundation/model, WP2.2 comparison logic, WP2.3 comparability/evidence/export and WP2.4 Streamlit integration: all implemented and stage-tested in order. No stage approval pauses, no WP3/WP4 implementation.

### C. Code/document changes and inspected dependencies

New files:

- `src/scenario_comparison.py`: pure data contracts, native-key/identity validation, explicit comparison, fixed cohorts, metric results, conditioning-input/policy checks and evidence references.
- `src/comparison_io.py`: published loader wrapper and four deterministic CSV exports.
- `tests/test_scenario_comparison.py`: staged foundation/core/comparability tests.
- `tests/test_comparison_dashboard.py`: Streamlit integration, both modes, exports and WP1 handoff.
- `tests/test_comparison_acceptance.py`: independent hand-derived business acceptance cases.
- `docs/wp2_scenario_tradeoff_analysis_specification.md`: full authoritative baseline.
- `docs/wp2_implementation_progress.md`: plan, stage audit and this final report.

Modified by WP2: `dashboard/scenario_planning_app.py`, `docs/scenario_planning/project_journal.md`, `docs/scenario_planning/developer_notes.md`, `docs/scenario_planning/dashboard_design_proposal.md`, `ai_agent_implementation_spec.md`. Existing WP1 changes in other files were retained, not attributed to WP2.

Reused: `load_sequential_outputs(include_evidence=True)`, shared `require_frame`/`weekly_dates`/`horizon`/`numeric`, existing `calculate_sequential_kpis`, existing published manifest/CSV schemas, and original WP1 navigation/evidence workflow. Product horizon aggregation was inspected, but its unrelated risk-field requirements make the existing KPI engine the narrower reusable calculation interface. No core module/schema/dependency redesign; no formula changes. Source IO is confined to the loader boundary.

Files inspected include AGENTS.md; planning_risk, planning_inputs, demand_preparation, workload_model, csv_planning_inputs, sequential_planner, inventory_engine, kpi_engine, performance_manager, run_planning; dashboard; existing risk/pipeline/dashboard/upload tests; both portable example profiles and published runs; architecture alignment report, stage/dashboard proposals, developer notes, journal and legacy specification. Historical Route B references were inspected for scope separation.

### D. Tests and results

All counts below are executed unittest test cases, with subtests covering additional modes/defects. Stage suites are cumulative where noted, not additive.

| Gate / command | Passed | Failed | Skipped | Evidence |
| --- | ---: | ---: | ---: | --- |
| Pre-edit `python -B -m unittest discover -s tests` | 181 | 0 | 0 | `tmp/wp2_acceptance/baseline_tests.log` |
| WP2.1 comparison suite | 4 | 0 | 0 | `tmp/wp2_acceptance/wp2_1_tests.log` |
| WP2.2 cumulative comparison suite | 14 | 0 | 0 | `tmp/wp2_acceptance/wp2_2_tests.log` |
| WP2.3 cumulative comparison suite | 33 | 0 | 0 | `tmp/wp2_acceptance/wp2_3_tests.log` |
| Final comparison suite, including historical coverage regression | 34 | 0 | 0 | `tmp/wp2_acceptance/wp2_3_final_gate_tests.log` |
| WP2.4 `python -B -m unittest discover -s tests -p test_comparison_dashboard.py` | 5 | 0 | 0 | `tmp/wp2_acceptance/wp2_4_ui_tests.log` |
| Existing `python -B -m unittest discover -s tests -p 'test_dashboard*.py'` | 12 | 0 | 0 | `tmp/wp2_acceptance/wp2_4_regression_tests.log` |
| Independent `python -B -m unittest discover -s tests -p test_comparison_acceptance.py` | 7 | 0 | 0 | `tmp/wp2_acceptance/independent_acceptance_tests.log` |
| Final `python -B -m unittest discover -s tests` | **227** | **0** | **0** | `tmp/wp2_acceptance/final_full_suite.log` (169.334s) |

Comparison-suite command at each corresponding gate: `python -B -m unittest discover -s tests -p test_scenario_comparison.py`. Initial failures and fixes are documented in the stage entries above; final counts do not hide those development failures.

Additional independent LOST_SALES oracle: capacity-constrained reference service 0.625, candidate 1.0, loss 6 → 0, terminal backlog 0 → 0; assertions passed (`tmp/wp2_acceptance/lost_sales_manual_oracle.json`). This independently demonstrates why zero backlog cannot stand in for service. The two-week CARRY_FORWARD hand oracle verifies horizon service 10/16, weekly service 5/8 and 4/8, terminal backlog 6 versus same-week-unfulfilled flow 7, allocated workload delta +6 and unmet workload 9 → 0. Separate cases cover unconstrained/zero capacity, zero demand, inventory-covered demand, opening-origin fulfillment exclusion, string IDs `001`/`NA`, and export lineage.

`git diff --check` passed. Final source/AST and 24 archived artifact checks passed; machine-readable evidence: `tmp/wp2_acceptance/final_verification.json` and `protected_baseline_verification.json`. Outputs generated include the full registered specification, comparison implementation/UI, automated tests, this audit record, test logs, pre/post verification records and runtime metrics/cohort/evidence/context CSV exports. Test fixture runs use temporary directories; existing upload regressions also create isolated published runs under tmp.

### E. Business rules and acceptance mapping

| v1.0 acceptance criterion | Verified result / evidence |
| --- | --- |
| 1. Explicit Reference/Candidate | Empty-by-default controls; same-run and distinct-side gates; non-Baseline REF/CAND hand oracle; direction reverses correctly |
| 2–3. Fixed cohort / priority changes | Membership is based solely on reference priority; candidate change flags do not move members; missing priority is explicit |
| 4. ALL / SELECTED / COMPLEMENT | One declared universe and scope; additive quantities reconcile; membership is unique and complementary; empty groups N/A |
| 5. Service/backlog/loss/workload definitions | Existing KPI engine and independent hand sums; weighted rates; weekly/horizon bases distinct; opening-origin service excluded; terminal opening/horizon backlog separate |
| 6. Shared capacity | Unique plant-week context table; no join to evidence details and no cohort utilization claim |
| 7. Metric-level comparability | Status and reason on every metric; POLICY_CONTRAST is descriptive for defined metrics; incompatible workload deltas blocked; no winner/actions |
| 8. Missing data | No zero filling or silent intersection; missing products/weeks/endpoints block deltas; zero denominator N/A; legitimate historical OUT_OF_SCOPE rows stay evidence |
| 9. Context/evidence CSV | Four deterministic CSVs; primary metrics file embeds identities/scope/cohort/evidence; artifact hashes/native grain/provenance retained |
| 10. Both modes | Real published USER_DATA and SYNTHETIC_DEMO tested through loader, comparison, export and AppTest |
| 11. WP1 / earlier regression | Both WP1 navigation paths, evidence downloads, upload workflow and Phase 2 summary pass full regression |
| 12. Core formula protection | All pre-existing src/test file hashes unchanged; only existing dashboard `_sequential_views` AST changed |

### F. Regression assessment

PASS. Relative to the pre-WP2 worktree, all existing `src/*.py` and existing tests are byte-identical. Every pre-existing dashboard function except `_sequential_views` is AST-identical, including upload, loader, risk and WP1 investigation/export functions. The altered function adds the new tab and a stable scenario widget key for explicit WP1 handoff. Source/AST baseline checks passed after the full suite. Existing USER_DATA and SYNTHETIC_DEMO archived runs each retained all 12 original artifact hashes/row counts. Full 227-test regression passed; no planning/allocation/inventory/KPI/WP1 result changes were detected.

### G. Git status

Branch remains `main`; HEAD remains `4b6c84d99173f2472de7a973c1ca98c3a4b15ec2`. WP2 files and documentation are uncommitted. Original WP1 modifications, existing tracked/untracked caches and tmp files remain. Exact pre-existing status is in `tmp/wp2_acceptance/pre_wp2_baseline.json`; final status is in `tmp/wp2_acceptance/final_git_status.txt`. No commit, push, reset, clean, branch switch or history-changing operation occurred.

### H. Outstanding issues / limits

No unresolved WP2 acceptance failures. MVP intentionally supports only one complete published sequential_v1 run, with no cross-run comparison/replay, scenario generation, recommendation, optimizer, AI or PBIX changes. No browser visual acceptance was performed; interactive behavior was exercised with Streamlit AppTest. Existing Streamlit width deprecation and legacy sparse-data warnings remain; no new dependency/environment change was made. Original WP2–WP4 Subagent research full texts remain unavailable, but the complete owner-supplied v1.0 implementation baseline is registered and authoritative. Publication/commit/push still require separate explicit authorization.

### I. Final recommendation

**IMPLEMENTATION COMPLETE — ACCEPTANCE PASSED**
