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

Stage 4 — Decision / Allocation Engine: NOT STARTED.

Stage 5 — Performance Evaluation: NOT STARTED.

AI-Assisted Planning: FUTURE.

At the time of the Stage 0 entry, Scenario Planning implementation had not yet begun.

### Next Step

Stages 1–3 are complete. The next stage is Stage 4 — Decision / Allocation Engine; do not begin performance evaluation until explicitly authorized.


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
