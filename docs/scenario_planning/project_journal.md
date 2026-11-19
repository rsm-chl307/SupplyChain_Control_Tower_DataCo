# Project Journal

> **Route B planning record — 2026-11-17:** [Specification package](../improvement_program/README.md) prepared for owner review; no improvement WP implemented or authorized. Legacy stage completion records below retain their historical meaning. Route B Stage 0 owner freeze and every implementation authorization remain separate gates.

## Stage 0 — Project Definition

### Objective

Define the business problem, planning decision context, scenarios, architecture direction, constraints, success criteria, and future AI boundary for the Scenario Planning extension. Stage 0 is documentation only.

### Decisions and Scope

- The completed Control Tower and Power BI dashboard are the baseline monitoring and diagnostic layer.
- Scenario Planning is a separate future layer at Plant × Product × Week, with Scenario added to scenario outputs.
- Baseline, Demand Surge, and Capacity Disruption are required initial scenarios; Priority Shift is optional.
- ABC A/B/C maps to priorities 3/2/1, and the initial capacity-allocation direction is deterministic and rule-based.
- The future flow is Planning Data Layer → Planning Snapshot → Scenario Generator → Allocation → Performance Evaluation → Decision Support → Power BI.
- Stage 0 does not create planning code, allocation logic, scenario outputs, OR optimization, AI/RAG functionality, or changes to existing Control Tower assets.

### Assumptions and Unresolved Items

Inventory and capacity inputs are derived or simulated Control Tower datasets rather than production execution records. Stage 1 must resolve whether `Scenario_Capacity` uses total `Weekly_Capacity` or derived `Available_Capacity`, and whether missing product-week observations should remain sparse or be represented as zero demand. These are planning-data decisions, not Stage 0 implementation changes.

### Current Status

Stage 0 — Project Definition: COMPLETE.

Stage 1 — Planning Data Design: COMPLETE.

Stage 2 — Planning Data Pipeline: COMPLETE.

Stage 3 — Scenario Generator: COMPLETE.

Stage 4 — Decision / Allocation Engine: COMPLETE.

Stage 5 — Performance Evaluation: COMPLETE.

AI-Assisted Planning: FUTURE.

At the time of the Stage 0 entry, Scenario Planning implementation had not yet begun.

### Next Step

Stages 1–5 are complete. Future work is limited to separately approved decision-support extensions.


## Stage 2 — Planning Data Pipeline

### Objective

Convert the approved Stage 1 snapshot preparation into a reproducible, parameterized pipeline without changing the Stage 1 contract.

### Completion Record

Stage 2 is complete. The pipeline loads approved sources, reuses `src/planning_snapshot.py`, validates the full baseline, applies strict inclusive horizon parameters, validates the filtered result, sorts deterministically, and writes a horizon-specific artifact.

### Files and Output

- `src/planning_pipeline.py`
- `tests/test_planning_pipeline.py`
- `data/processed/planning_snapshot_20170101_20171231.csv`
- Example horizon: `2017-01-01` through `2017-12-31`
- Output rows: 1,977

### Validation and Integrity

Seven unittest methods passed, including grouped parameter cases for missing, invalid, reversed, out-of-range, and empty horizons. Source hashes and the full-range Stage 1 baseline artifact remained unchanged. Sparse observations were preserved.

Out-of-range horizons fail explicitly because silently clipping a requested horizon would make the requested parameters inconsistent with the actual analysis period.

No scenario logic, allocation, performance evaluation, or Stage 3 work was started.

### Next Step

Stage 3 — Scenario Generator.


## Stage 3 — Scenario Generator

### Objective

Create deterministic scenario-specific planning inputs from the approved Stage 2 horizon snapshot without changing the baseline snapshot or implementing allocation.

### Decisions and Implementation

The MVP implements `Baseline`, `Demand_Surge_10pct`, and `Capacity_Disruption_P1_20pct`. Demand Surge requires an explicit percentage; Capacity Disruption requires explicit percentage and plant IDs, with optional inclusive week bounds. Scenario IDs encode parameters. Priority Shift remains a future extension. The generator preserves sparse observations, uses `Weekly_Capacity` as scenario capacity, retains `Baseline_Available_Capacity` as context, and adds only the three approved scenario fields.

### Files and Artifact

- `src/scenario_generator.py`
- `tests/test_scenario_generator.py`
- `data/processed/scenario_snapshot.csv`
- Example input: `data/processed/planning_snapshot_20170101_20171231.csv`
- Output: 5,931 rows, 1,977 per scenario

### Validation and Integrity

Nineteen focused tests passed, including parameter failures, scenario calculations, schema, sparsity, scenario-key uniqueness, input immutability, and deterministic repeated execution. The generated artifact has the exact approved 14-column schema. Stage 1 and Stage 2 source code and artifacts remained unchanged. No allocation or performance logic was started.

### Next Step

Stage 4 — Decision / Allocation Engine.


## Stage 4 — Decision / Allocation Engine

### Objective

Allocate scenario production capacity deterministically across eligible products and calculate same-week backlog for the Stage 3 Scenario Snapshot.

### Frozen decisions

Allocation is independent by week at Scenario × Plant × Week. Beginning Inventory covers only its product’s same-week demand. The existing Plant × Product rows are the complete eligibility set; cross-plant transfers and backlog carryover are excluded. Products are ordered by Planning_Priority descending, Net_Demand descending, and Product Card Id ascending. Scenario_Capacity is the shared capacity pool.

### Implementation and artifact

- `src/allocation_engine.py`
- `src/allocation_manager.py`
- `src/allocation_validator.py`
- `tests/test_allocation_engine.py`
- `data/processed/allocation_result.csv`

The real Stage 3 input contained 5,931 rows and produced 5,931 allocation rows. The output retained the sparse input row set and the approved allocation fields.

### Validation and integrity

Eighteen focused tests passed. Full result validation passed, including capacity reconciliation, arithmetic rules, priority ordering, eligibility, deterministic repeatability, and input immutability. Stage 1, Stage 2, and Stage 3 code and artifacts remained unchanged.

No KPI, service-level, utilization, risk, recommendation, optimization, forecasting, AI, dashboard, or Stage 5 functionality was implemented.

### Next step

Stage 5 — Performance Evaluation.


## Stage 5 — Performance Evaluation

### Objective

Evaluate the operational impact of Stage 4 allocation results without changing allocation decisions.

### Frozen decisions

Service Level uses Allocated_Qty divided by Net_Demand, Allocation Rate uses Allocated_Qty divided by Scenario_Demand, and Capacity Utilization uses ratio-of-sums allocation divided by deduplicated Scenario_Capacity pools. Zero denominators use the approved deterministic policies. Backlog is read from Stage 4 and is not carried across weeks.

KPI rows are produced at Scenario, Scenario × Plant, and Scenario × Week levels. Baseline is the comparison reference. Healthy, Watch, and At Risk statuses use only backlog and 100% utilization; no additional thresholds or composite score are used.

### Implementation and artifact

- `src/kpi_engine.py`
- `src/performance_evaluator.py`
- `src/performance_manager.py`
- `tests/test_performance_evaluation.py`
- `data/processed/performance_result.csv`

The real Stage 4 input produced 171 performance rows. All current rows are Healthy because the approved horizon has zero backlog and utilization below 100%.

### Validation and integrity

Sixteen focused tests and the full 60-test repository suite passed. Synthetic cases covered partial allocation, backlog, zero demand, zero capacity, and inventory coverage. The Stage 4 allocation artifact and all earlier artifacts remained unchanged.

No UI, dashboard, AI, recommendation, optimization, or later-stage functionality was implemented.


## Dashboard Integration — End-to-End Runner

### Objective

Provide one reproducible command-level entry point for Stages 2–5 before Power BI integration.

### Implementation

`src/run_planning.py` now composes the existing planning pipeline, scenario generator, allocation manager, and performance manager. It accepts planning horizon bounds, demand surge percentage, capacity disruption percentage, disruption plant, and an optional run output directory. Invalid inputs fail before execution.

The default output convention is `data/processed/scenario_runs/{start}_{end}/`, containing the horizon snapshot plus `scenario_snapshot.csv`, `allocation_result.csv`, and `performance_result.csv`. This protects the approved root artifacts.

Focused runner tests cover valid execution, invalid/reversed horizons, parameter validation, missing/unknown plants, propagation, expected outputs, deterministic reruns, and completed-artifact protection. The full repository suite remains passing.

No Power BI, UI, backend business-rule, or dashboard-page implementation was started. The next step is validating the documented Power BI mapping and then implementing the approved dashboard pages.

## Dashboard Integration MVP

Implemented a separate Streamlit Scenario Planning experience at `dashboard/scenario_planning_app.py` while preserving the completed PBIX Control Tower. The app delegates execution to `src/run_planning.py`, loads prepared Stage 5/4/3 outputs, and provides scenario overview, baseline comparison, and allocation drill-down views. Focused dashboard integration tests pass; no backend business rules, historical artifacts, PBIX pages, or existing Control Tower notebooks were changed.


## Revised three-day planning upgrade — implementation record

The owner replaced the broad six-WP delivery plan with a focused sequential planning target. The implemented vertical slice now runs raw-order eligibility through workload allocation, continuous inventory/backlog, four scenarios, independent validation, KPI output and prepared Streamlit views. Legacy functions and historical artifacts remain separate.

Data inspection traced 588 resampled zero weeks, 11,508 outside-lifespan unknown combinations and 344,529 synthetic replenishment units already embedded in later opening stock. No actual procurement or production standards were found. The new input path therefore requires explicit coverage, factor, capacity, opening-state and receipt assumptions rather than replaying historical simulation stock.

A fully synthetic repeatable fixture and successful CLI run are saved under tmp; they do not approve DataCo's production whitelist. Current evidence, actual test counts and generated run path are recorded in tmp/planning_data_inspection_2026-11-17.md. No completion claim is made for all original WPs or unverified Power BI runtime behavior.


## Revised data strategy — synthetic and user CSV sources

Implemented two portable data modes feeding one canonical bundle and the same planning/validation/scenario/KPI functions. Added working examples, nine header templates, configurable column/status mappings and capability diagnostics. DataCo is an optional reference profile, with owner-approved qualification and separate synthetic planning inputs.

Verified both examples through the CLI and successfully published the optional DataCo reference run after correcting a machine-roundoff-only capacity residual. Original datasets and PBIX remain protected. Reference-free test execution is checked in an isolated copy with no data directory. Final counts and source hashes are recorded in tmp/data_source_extensibility_2026-11-17.md.


## Phase 2 — Planning Risk Summary

Added a presentation-only risk summary to the existing sequential Streamlit results view. `src/planning_risk.py` derives product risk indicators, unique plant-week bottleneck summaries, traceable same-week risk signals, and scenario deltas from the published allocation, capacity-pool, and performance artifacts. Product ending inventory/backlog use each plant-product's final week; capacity aggregation uses the unique Scenario × Plant × Week pools. Risk categories use visible service and inventory signals and do not use a composite score. Risk-driver descriptions are explicitly observational, not causal findings.

The planning engine, allocation policy, inventory simulation, and KPI formulas were not changed. Acceptance testing found and corrected four presentation/data-handling defects: null numeric inputs had been silently skipped during risk aggregation; one plant comparison table requested a column name not returned by its calculation; published empty/incomplete artifacts did not always produce a specific user-facing message; and an optional bottleneck-week KPI was assumed to be present by one comparison view. Numeric risk inputs are now checked for finite values, unmatched capacity pools remain explicitly unavailable, and absent optional bottleneck-week metrics no longer prevent other scenario comparisons. Focused tests cover synthetic edge cases and both SYNTHETIC_DEMO and USER_DATA. Full-suite result after acceptance fixes: 169 tests passed. Streamlit AppTest covered both modes and Combined Stress; browser visual testing was not performed. No Phase 3 recommendation capability was added.

## Phase 3 — WP1 Root Cause Investigation

Extended the Phase 2 Risk Drivers tab into Root Cause Investigation, with product → plant → week and plant → week → product selection, explicit investigation weeks, and entry actions from existing product/plant summaries. The view presents published selected-week demand, production, inventory, receipts, backlog and fulfillment alongside one shared plant-week capacity pool, adjacent calendar-week product states, and all allocation peers in existing Allocation_Order. Observations reuse Phase 2 risk signals and do not establish causal responsibility.

Supporting evidence remains in separate tables at native artifact grain, preventing demand-line/receipt joins from inflating planning quantities. Per-table CSV downloads retain native fields and add the complete investigation context separately. Additional artifact loading reuses manifest path/SHA256 checks, preserves string identifiers, checks run/schema identity and evidence fields, and accepts valid empty external receipts. Original source availability/hash status and source provenance are explicit; missing or changed raw files do not replace intact published evidence. Weekly source-record IDs are not described as business order IDs, and scenario demand increments have no fabricated source orders.

No planning engine, allocation, inventory or KPI formula was changed. Investigation selections only read existing outputs. WP2–WP4 received independent read-only research, with no implementation or automatic expansion of WP1. Future decisions include comparison cohort/policy handling, source-backed simulation versus canonical replay, supported simulation controls and explicit action-rule approval.

Validation: `python -B -m unittest discover -s tests` passed all 181 tests, including USER_DATA and SYNTHETIC_DEMO, both navigation paths, Baseline/Combined Stress, key isolation, allocation-peer/pool reconciliation, adjacent inventory/backlog, empty receipts, missing/tampered source evidence, CSV context/identifier preservation, deterministic selections and no planning/file mutation during investigation. `git diff --check` passed. Streamlit AppTest was used; browser visual testing was not performed. Remaining limits are the existing model's lack of causal attribution, order-level backlog aging and real-world operational event evidence. No commit or push was performed.

## Phase 3 — WP2 specification registration and implementation authorization

The owner authorized sequential WP2.1–WP2.4 implementation. The complete supplied v1.0 design is registered at [WP2 Scenario Trade-off Analysis](../wp2_scenario_tradeoff_analysis_specification.md); stage scope, inspection, verification and audit records are maintained in [WP2 implementation progress](../wp2_implementation_progress.md). Existing WP1 worktree changes are protected. No WP3/WP4 implementation, engine formula changes, cross-run comparison, commit or push is authorized by this work.

## Phase 3 — WP2 Scenario Trade-off Analysis completed

Implemented WP2.1–WP2.4 against the [registered complete v1.0 baseline](../wp2_scenario_tradeoff_analysis_specification.md). The comparison API uses two explicit scenarios in one published sequential_v1 run, fixed reference-priority cohorts and complements, existing KPI calculations, terminal backlog origin distinctions, loss/workload flows, unique shared capacity context, metric-level comparability/POLICY_CONTRAST and native evidence references. Streamlit adds an independent trade-off tab, four context-bearing CSV exports and an explicit side/product handoff into existing WP1 navigation. No new simulation, formula change, cross-run/replay or recommendation functionality was added.

Stage gates passed in order. Final full suite: `python -B -m unittest discover -s tests` — 227 passed, 0 failed, 0 skipped (169.334s). Independent seven-case hand-derived acceptance and a nonzero LOST_SALES oracle passed. Pre-WP2 source/test hashes and existing dashboard function ASTs confirm all core/WP1 logic unchanged; only existing `_sequential_views` gained tab/widget integration. Both pre-existing archived data-mode runs retain their 12 artifact hashes/row counts. Development failures, fixes, commands, file lists and acceptance matrix are recorded in [WP2 implementation progress](../wp2_implementation_progress.md). AppTest was performed; browser visual testing was not. No commit or push.
