# Stage 3 — Scenario Generator Design and Completion Record

## Approved design

Stage 3 consumes the Stage 2 horizon-filtered baseline Planning Snapshot in memory at the existing Plant × Product × Week grain. It preserves sparse observations and the 11 baseline fields, adding only `Scenario`, `Scenario_Demand`, and `Scenario_Capacity`.

The MVP scenarios are:

- `Baseline`
- `Demand_Surge_10pct`
- `Capacity_Disruption_P1_20pct`

The generator remains parameterized. Demand Surge requires an explicit finite non-negative `demand_increase_pct`. Capacity Disruption requires explicit finite `capacity_reduction_pct` in the range 0–100 and a non-empty list of existing `plant_ids`; optional `week_start` and `week_end` are inclusive and must be within the input range. Priority Shift is rejected as a future extension.

Demand Surge changes demand only:

```text
Scenario_Demand = Weekly_Demand * (1 + demand_increase_pct / 100)
Scenario_Capacity = Weekly_Capacity
```

Capacity Disruption changes capacity only for targeted plants and, when supplied, targeted weeks:

```text
Scenario_Capacity = Weekly_Capacity * (1 - capacity_reduction_pct / 100)
Scenario_Demand = Weekly_Demand
```

The baseline preserves both demand and capacity. `Weekly_Capacity` remains the planning capacity pool; `Baseline_Available_Capacity` remains context only. No allocation, backlog, KPI, performance, optimization, or AI fields are introduced.

## Final implementation

Implemented as a lean in-memory module:

- `src/scenario_generator.py` — input/parameter validation, deterministic scenario transformation, and output validation.
- `tests/test_scenario_generator.py` — 19 focused tests covering scenario calculations, parameter failures, sparsity, schema, uniqueness, immutability, and determinism.

The module does not read or write CSV files. The approved example run was orchestrated externally from the Stage 2 artifact:

- Input: `data/processed/planning_snapshot_20170101_20171231.csv`
- Output: `data/processed/scenario_snapshot.csv`
- Output schema: the 11 baseline columns plus the 3 scenario columns above.

## Validation result

- 19 focused tests passed.
- Python syntax compilation passed.
- Input rows: 1,977; output rows: 5,931 (3 × input).
- Each scenario contains 1,977 rows.
- `Scenario + Planning_Key` is unique.
- Scenario output spans 2017-01-01 through 2017-12-31, with 3 plants and 118 products.
- Repeated in-memory generation is deterministic and byte-identical when serialized with the fixed date format.
- Stage 1/2 source code and both planning snapshot artifacts remained byte-identical.

## Boundary and next stage

Stage 3 creates scenario planning inputs only. It does not allocate capacity or calculate net demand, backlog, service level, utilization, recommendations, or performance evaluation. Stage 4 — Decision / Allocation Engine is the next implementation stage; Stage 5 remains not started.
