# Stage 5 — Performance Evaluation Design and Implementation Record

## Approved business-rule freeze

Stage 5 consumes `data/processed/allocation_result.csv` and evaluates allocation results without changing them. The primary consolidated artifact is `data/processed/performance_result.csv`.

Frozen KPI formulas:

```text
Service_Level = Allocated_Qty / Net_Demand
Allocation_Rate = Allocated_Qty / Scenario_Demand
Capacity_Utilization = sum(Allocated_Qty) / sum(Scenario_Capacity)
Capacity_Gap = Scenario_Capacity - Allocated_Qty
Total_Backlog = sum(Backlog)
```

Zero-denominator rules:

- Service Level is 1.0 when Net Demand is zero.
- Allocation Rate is 1.0 when Scenario Demand is zero.
- Capacity Utilization is 0 when total Scenario Capacity is zero.
- Backlog Rate is not persisted.

KPI aggregation levels are Scenario, Scenario × Plant, and Scenario × Week. Capacity utilization uses ratio-of-sums aggregation. Baseline is the reference scenario; scenario-level comparisons include Service Level, Capacity Utilization, Backlog, and Allocation Rate changes. No composite score or product-level KPI artifact is created.

Performance status rules are:

- Healthy: no backlog and utilization below 100%.
- Watch: no backlog and utilization equals 100%.
- At Risk: backlog is greater than zero.

## Architecture

- `src/kpi_engine.py` — numerical KPI aggregation only.
- `src/performance_evaluator.py` — status rules only.
- `src/performance_manager.py` — in-memory orchestration and scenario comparison.
- `tests/test_performance_evaluation.py` — focused KPI, status, comparison, edge-case, and immutability tests.

No module modifies Stage 4 results or implements allocation, scenario generation, inventory simulation, forecasting, optimization, AI, UI, or dashboard logic.

## Output contract

`performance_result.csv` is one consolidated table containing KPI rows at the three approved aggregation levels, status fields, and scenario-level comparison fields.

Implementation and validation results are recorded below after completion.


## Implementation and validation

Implemented files:

- `src/kpi_engine.py`
- `src/performance_evaluator.py`
- `src/performance_manager.py`
- `tests/test_performance_evaluation.py`

The real Stage 4 artifact was evaluated without modification and produced `data/processed/performance_result.csv`. The consolidated output contains 171 rows: 3 Scenario rows, 9 Scenario × Plant rows, and 159 observed Scenario × Week rows.

The KPI engine deduplicates repeated product-row capacity values at Scenario × Plant × Week before ratio-of-sums aggregation. The evaluator applies only the approved Healthy/Watch/At Risk rules. The manager adds scenario-level Baseline comparisons without creating a composite score or product KPI artifact.

Sixteen focused tests passed, including synthetic partial allocation, backlog, zero demand, zero capacity, inventory-covered demand, status assignment, zero-denominator behavior, comparison, determinism, invalid input, and Stage 4 immutability. The full repository suite passed with 60 tests.

For the approved 2017 artifact, all 171 rows are `Healthy`; total backlog is zero in every scenario. Scenario-level KPI results are:

- Baseline: Service Level 1.0, Capacity Utilization 0.010067, Allocation Rate 0.015056, Backlog 0.
- Capacity Disruption: Service Level 1.0, Capacity Utilization 0.010897, Allocation Rate 0.015056, Backlog 0.
- Demand Surge: Service Level 1.0, Capacity Utilization 0.012390, Allocation Rate 0.016846, Backlog 0.

Stage 4 artifacts remained byte-identical. No UI, dashboard, AI, or later-stage functionality was implemented.
