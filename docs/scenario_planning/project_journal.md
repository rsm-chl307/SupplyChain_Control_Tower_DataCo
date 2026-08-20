# Project Journal

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
