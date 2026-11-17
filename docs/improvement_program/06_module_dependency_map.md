# Module Dependency Map and File Ownership

Version 1.0 • Proposed target; no modules added in this documentation task.

## Dependency direction

    data_contracts
        <- validation_report and all frame boundaries
    validation_report + data_contracts
        <- allocation_validator, inventory_validator
    data_contracts
        <- demand_preparation, workload_model, planning_snapshot
        <- scenario_generator
        <- allocation_engine, inventory_engine
    allocation_engine + inventory_engine + validators + scenario views
        <- sequential_planner
    validated results + data_contracts
        <- kpi_engine -> performance_evaluator -> performance_manager
    pure preparation functions + run_management + validators + above pipeline
        <- planning_pipeline/upstream_pipeline/run_planning
    published manifest + prepared tables
        <- Streamlit/PBIX adapters

Arrows mean dependency consumer points back to providers. Providers never import orchestrators or dashboards. Validators cannot import the calculation engines they verify; independent equations are intentionally separate. Shared schema constants are allowed. Replace the current validator -> scenario_generator constants coupling only in an authorized compatibility-preserving change.

## Existing files and stage ownership

| Existing repository file | WPs/stage owner | Planned responsibility change |
|---|---|---|
| src/planning_snapshot.py | WP1 checks; WP2/3 Route B builder | Preserve legacy; join new explicit input bundle without repeated capacity totals or weekly stock resets |
| src/allocation_validator.py | WP1 foundation; WP3 complete policies | Independent frozen checks now; Route B checks only as approved contracts mature |
| src/allocation_engine.py | WP3 | Preserve legacy group API; workload-aware group interface consumes prepared requirement |
| src/allocation_manager.py | WP3 compatibility | Keep legacy wrapper; delegate only explicitly versioned paths, no hidden sequential behavior |
| src/scenario_generator.py | WP3 scenario contract; WP6 combined | Add versioned policy/scope metadata and composed shock support |
| src/kpi_engine.py | WP4 | Numerators/denominators/stock snapshots and workload measures |
| src/performance_evaluator.py | WP4 | Approved thresholds and exposure terminology only |
| src/performance_manager.py | WP4 | Grain-specific outputs and like-for-like scenario comparison |
| src/planning_pipeline.py | WP2 source assembly; WP5 integration | Explicit paths/mode, no inferred qualification or replenishment |
| src/run_planning.py | WP5 minimum contracts early; full Stage 5 | Unified entry, run metadata, gates, safe publication |
| tests/test_allocation_engine.py | WP1/3 | Preserve regressions; add independent negative cases, then workload cases |
| tests/test_scenario_generator.py | WP2/3/6 | Keep baseline contract; test versioned transformations/isolation |
| tests/test_performance_evaluation.py | WP4 | Keep frozen KPI tests; add approved new metrics |
| tests/test_planning_pipeline.py; tests/test_run_planning.py | WP5 | Isolated runs, failure injection, reproducibility and historical protection |
| tests/test_dashboard_app.py | WP4/5/6 | Same-run reconciliation, labels and page navigation |
| dashboard/scenario_planning_app.py | WP4, WP5 loader integration, WP6 demo | Published run selection and backend-only metrics |
| dashboard/supply_chain_control_tower.pbix | WP4 after P20 | Explicit five-page migration and aggregation correction |
| notebooks/01_data_modeling.ipynb; 02_risk_metrics.ipynb; 03_inventory_risk.ipynb; 04_service_risk.ipynb; 05_dashboard_dataset.ipynb | WP2/4/5 source references | Read/port transformations; no notebook rewriting required by default |
| data/raw; data/master; data/processed legacy artifacts | All WPs protected baseline | Read only; new assumptions/artifacts isolated and explicitly authorized |
| readme.md; ai_agent_implementation_spec.md; docs/scenario_planning/developer_notes.md; project_journal.md | Stage documentation | Scope pointers now; stage completion records only after actual implementation |

## Genuinely proposed additions

| Proposed file | Reason / owner | Dependency |
|---|---|---|
| src/data_contracts.py | Shared versioned schemas/units/keys, WP1 | No engine imports |
| src/validation_report.py | Structured findings/report model, WP1 | data_contracts |
| src/demand_preparation.py | Pure dual-demand/status lineage, WP2 | data_contracts and validators |
| src/workload_model.py | Pure factor resolution and approved capacity preparation, WP2 | data_contracts |
| src/inventory_engine.py | Pure quantity/state transition, WP3 | approved policy contracts |
| src/sequential_planner.py | Scenario chronological orchestration, WP3 | group allocation, state transition, independent validators |
| src/inventory_validator.py | Independent continuity/conservation, WP1 contract/WP3 behavior | schemas/reports only |
| src/run_management.py | IDs/manifests/status/publication, WP5 minimum early | standard-library I/O at boundary |
| src/upstream_pipeline.py | Unified reproducible raw preparation orchestration, WP5 | WP2 preparation functions |
| tests/test_independent_validation.py | Independent corruption/finiteness/grain tests, WP1 | validation APIs |
| tests/test_demand_capacity.py | Reconciliation/factor/calendar tests, WP2 | preparation APIs |
| tests/test_sequential_planning.py | Multiweek stock/backlog/receipt/isolation cases, WP3 | sequential APIs |
| tests/test_run_management.py | Manifest/publication failure tests, WP5 | isolated temporary outputs only when authorized |
| tests/test_scenario_demonstration.py | Four-scenario hand-checkable acceptance, WP6 | full published contract |
| requirements.txt or pyproject.toml | Tested dependency declaration, WP5 minimum early | Exact format/versions reviewed before authorized creation |

Names are proposals. Reuse an existing module if its responsibility remains clear; avoid separate competing pipelines or duplicate production formulas. No proposed source/test/config file is created now.

## Critical path

Stage 0 owner review -> WP1 independent foundation -> WP2 approved demand/factors/capacity -> WP3 sequential state -> WP4 metric/dashboard reconciliation -> WP5 complete publication workflow -> WP6 demonstration.

WP5 Run_ID, Schema_Version and manifest contracts must be stable before new artifacts. Minimal code infrastructure may be separately authorized early; full integration remains Stage 5. WP1 final sequential validation depends on WP3 facts/policies, so Stage 1 cannot claim the whole D01 layer complete.
