# Developer Notes — Scenario Planning Extension

## Purpose and Boundary

The existing DataCo-based Control Tower is the completed monitoring baseline. Its notebooks, processed CSV datasets, risk calculations, and Power BI dashboard remain unchanged. It answers what happened in demand, inventory, capacity, and service risk. Scenario Planning is a separate future planning layer that will reuse those outputs to evaluate what-if decisions.

## Target Architecture and Data Flow

```text
Existing Control Tower data
  → Planning Data Layer
  → Planning Snapshot (Plant × Product × Week)
  → Scenario Generator (adds Scenario)
  → Decision / Allocation Engine
  → Performance Evaluation
  → Decision Support
  → Power BI-ready outputs
```

The Planning Data Layer will map existing demand, inventory, capacity, ABC classification, and master data into a canonical representation. The Planning Snapshot is the stable baseline before scenario changes. Scenario outputs use the same weekly Plant × Product × Week grain with a Scenario dimension.

## Module Boundaries

- Scenario Generator applies approved demand and capacity assumptions; it does not allocate capacity.
- Decision / Allocation Engine operates on one shared `Scenario × Plant × Week` capacity pool and returns explainable allocation results.
- Performance Evaluation calculates service, utilization, backlog, and risk measures from allocation results.
- Decision Support converts evaluated results into transparent recommendations and root-cause views.
- Power BI consumes published outputs; it is not part of core business logic.

The initial allocation direction is deterministic and rule-based: calculate `Net Demand = max(Scenario Demand - Beginning Inventory, 0)`, rank by Priority descending, Net Demand descending, and Product ID ascending, then allocate `min(Net Demand, Remaining Capacity)`. This direction is documented only at Stage 0 and is not implemented here.

## Technical Assumptions and Constraints

Core modules should use Python, Pandas, and NumPy with type hints, clear interfaces, and no unnecessary frameworks. Engines must remain independent of CSV I/O; a pipeline or notebook may orchestrate reads and writes. Existing field names and source provenance should be preserved or explicitly mapped. Stage 1 must resolve whether planning capacity means total `Weekly_Capacity` or derived `Available_Capacity`, and whether absent product-week observations remain absent or become explicit zero-demand rows.

The two-week MVP excludes OR solvers, advanced forecasting, real-time or ERP integration, production deployment, and AI/RAG functionality. The modular boundary leaves room for future optimization or AI explanation layers to consume validated deterministic outputs without replacing the core planning rules.


## Stage 2 Implementation Record

Stage 2 separates repeatable source loading and horizon selection from the Stage 1 in-memory snapshot contract. `src/planning_pipeline.py` loads the five approved source datasets, composes `build_planning_snapshot(...)` from `src/planning_snapshot.py`, validates the full baseline, applies inclusive `planning_start_week` and `planning_end_week` parameters, validates again, sorts deterministically, and writes a horizon-specific artifact.

Strict horizon validation fails for missing or invalid parameters, reversed dates, dates outside the available source range, and empty selected ranges. Sparse observations remain warnings only. Outputs use `planning_snapshot_{start}_{end}.csv`, preserving the full-range `planning_snapshot.csv` baseline. Seven unittest methods cover valid, invalid, boundary, reuse, determinism, schema, sparse-data, and baseline-protection behavior. Scenario logic, allocation, performance evaluation, and Stage 3 functionality were intentionally excluded.


## Stage 3 Implementation Record

Stage 3 adds a separate, in-memory Scenario Generator on top of the completed Stage 2 horizon-specific Planning Snapshot. `src/scenario_generator.py` validates the exact Stage 2 baseline schema, requires explicit scenario parameters, and reuses the baseline fields without reloading source datasets.

The MVP supports Baseline, parameterized Demand Surge, and parameterized Capacity Disruption. It preserves the sparse Plant × Product × Week row set and adds only `Scenario`, `Scenario_Demand`, and `Scenario_Capacity`. Scenario IDs encode the major parameters, output ordering is deterministic, and the input DataFrame is never mutated. The generator has no CSV I/O; the example artifact is written by an external run step.

Validation fails loudly for invalid schemas, dates, values, duplicate keys, unsupported Priority Shift, missing parameters, invalid percentages, unknown plants, and out-of-range disruption weeks. Nineteen focused tests cover calculations, boundaries, schema, sparsity, immutability, uniqueness, and reproducibility. Stage 3 intentionally excludes allocation, backlog/KPI/performance logic, optimization, forecasting, AI, and dashboard changes.


## Stage 4 Implementation Record

Stage 4 adds a lean in-memory allocation layer over the Stage 3 Scenario Snapshot. `allocation_engine.py` processes one Scenario × Plant × Week group, `allocation_manager.py` orchestrates all groups, and `allocation_validator.py` enforces input and output business rules. No module reads or writes CSV files.

The frozen rules are weekly independent allocation, product/plant eligibility from the existing Scenario Snapshot, no cross-plant transfers, product-specific same-week inventory coverage, shared `Scenario_Capacity`, and deterministic ordering by Planning Priority descending, Net Demand descending, and Product Card Id ascending. The result adds Net_Demand, Allocated_Qty, Backlog, Remaining_Capacity, Allocation_Order, Allocation_Strategy, and Allocation_Reason.

Eighteen focused tests passed. The real Stage 3 artifact produced `data/processed/allocation_result.csv` with 5,931 rows. Stage 4 does not calculate KPIs, service level, utilization, risk, recommendations, forecasting, optimization, AI, or dashboard changes.


## Stage 5 Implementation Record

Stage 5 evaluates the immutable Stage 4 allocation result through three separated in-memory modules: `kpi_engine.py` calculates numerical KPIs, `performance_evaluator.py` applies the approved status rules, and `performance_manager.py` orchestrates aggregation and Baseline comparison. Capacity is deduplicated at Scenario × Plant × Week before ratio-of-sums utilization is calculated.

The consolidated `data/processed/performance_result.csv` contains Scenario, Scenario × Plant, and observed Scenario × Week KPI rows plus status and scenario-comparison fields. Backlog is read from Stage 4, never recalculated or carried across weeks. Sixteen synthetic-focused tests and the full repository suite passed. Stage 5 does not modify allocation, add product KPI artifacts, create composite scores, or implement UI, dashboards, AI, or recommendations.


## End-to-End Runner Implementation Record

`src/run_planning.py` provides the single `run_planning(...)` orchestration entry point for the completed Stage 2–5 backend. It calls `run_planning_pipeline`, `generate_scenarios`, `run_allocation`, and `evaluate_allocation` in sequence; all business logic remains in those existing modules.

The runner requires a planning start/end week and disruption plant, with approved example defaults of 10% demand surge and 20% capacity reduction. It writes horizon-specific outputs beneath `data/processed/scenario_runs/{start}_{end}/` by default, protecting historical artifacts. It validates arguments, preserves deterministic schemas/order, and supports reproducible reruns.
