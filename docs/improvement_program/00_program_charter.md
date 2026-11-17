# Program Charter and Repository Baseline

Version 1.0 • 2026-11-17 • Owner review package • Implementation NOT AUTHORIZED.

## Objective and authority

Improve the existing deterministic scenario-based supply chain decision-support prototype through independent validation, dual demand, equivalent workload, sequential planning, expanded decision-support metrics and reproducible execution. Preserve useful module boundaries and completed baseline artifacts. Do not build an APS, procurement optimizer, forecast service, AI agent, alternate-routing optimizer or configurable multiweek production lead time.

The owner has approved [D01–D11](01_approved_decisions.md), not implementation. [Registry status](02_business_rules.md) distinguishes approved requirements and logically necessary invariants from proposed policy choices. Technical file/API names are proposals for stage review. No approved frozen rule is silently replaced in legacy mode.

## Current repository reassessment

Fresh inspection confirmed the following interfaces:

| Existing file | Verified responsibility | Route B treatment |
|---|---|---|
| ../../notebooks/01_data_modeling.ipynb | Raw DataCo latin1, virtual masters/mapping, Sunday plant demand; mean quantity / 0.75 capacity | Preserve history; port required transformations to explicit orchestration after authorization |
| ../../notebooks/02_risk_metrics.ipynb | Product demand, growth, ABC, policies, four-observation replenishment simulation | Preserve outputs; do not interpret synthetic replenishment as actual procurement |
| ../../notebooks/03_inventory_risk.ipynb | Ending-stock DOI and policy risk | Retain legacy meaning; version new metrics |
| ../../notebooks/04_service_risk.ipynb | Inventory/capacity co-occurrence rules | Exposure reference, not causal/probability evidence |
| ../../notebooks/05_dashboard_dataset.ipynb | Summary exports, some disabled and one undefined capacity-summary export | Legacy extraction reference; WP5 execution gap |
| ../../src/planning_snapshot.py | build_planning_snapshot(demand, capacity, inventory, abc, product_plant_mapping), pure sparse joins | Preserve legacy adapter; version Route B inputs |
| ../../src/scenario_generator.py | generate_scenarios(snapshot, parameters), exact 11-to-14-column contract | Version target contracts, combined stress and explicit policies |
| ../../src/allocation_engine.py | allocate_capacity(group), one independent plant-week quantity pool | Keep legacy; add workload-aware group contract |
| ../../src/allocation_manager.py | run_allocation(snapshot), independent group orchestration | Preserve legacy wrapper; sequential orchestration in distinct module |
| ../../src/allocation_validator.py | Schema/arithmetic/group capacity checks | Extend independent checks; remove generator constant coupling through shared contracts |
| ../../src/kpi_engine.py | calculate_kpis(allocation_results), three mixed aggregation levels | Preserve legacy; Route B separate flows and stocks/grains |
| ../../src/performance_evaluator.py | Backlog and full-utilization statuses | Do not borrow thresholds for new unit silently |
| ../../src/performance_manager.py | evaluate_allocation(results), Baseline deltas | Version Route B outputs and compatible comparisons |
| ../../src/planning_pipeline.py | Five processed sources, horizon validation and CSV output | Keep source/horizon boundary; add Route B source assembly |
| ../../src/run_planning.py | Stages 2–5 runner, horizon-named output directories | WP5 unified entry; unique runs and publication gates |
| ../../dashboard/scenario_planning_app.py | Three scenario tabs, runner controls, CSV loading | WP4 presentation only; consistent published run |
| ../../dashboard/supply_chain_control_tower.pbix | Five monitoring pages | Frozen until WP4-specific authorization and page mapping |
| ../../tests/ | Six unittest files | Preserve regression tests; propose independent new tests |
| ../../notebooks/03_control_tower_dashboard.ipynb | Empty zero-byte file | Disconnected placeholder; do not delete |
| ../../check_data.ipynb | Exploratory reads | Not a validation pipeline |

Fresh CSV-header and master-row inspection confirmed 118 products, 3 plants, plant/product/date identity names, legacy quantity capacity columns and absence of Route B policies, factor versions, run IDs, external receipt events and sequential stock outputs. File sizes/counts alone are not proof of functionality.

## Confirmed defects versus limitations

Confirmed contract gaps: result validation does not independently recompute net demand, rank/greedy allocation, source preservation or finite-value constraints. Fresh source inspection confirms these gaps; prior adversarial results are supporting historical evidence, not newly executed tests.

Confirmed run risk: fixed same-horizon filenames, sequential writes and no manifest can overwrite or mix runs. No new mixed-run incident is claimed.

Design limitations: independent weekly allocation, synthetic unconstrained replenishment, equal-unit capacity and production-coverage service labels. These are approved legacy behavior, not an assertion that saved arithmetic is wrong.

## Conflict register

| ID | Existing authority or artifact | Approved Route B direction / issue | Disposition |
|---|---|---|---|
| C01 | AGENTS.md; Stage 4 freeze: quantity min allocation, independent weeks, no carryover | D03–D07 require workload and sequential policies | Preserve legacy. Explicit future stage authorization must identify versioned changes; do not edit AGENTS in this task |
| C02 | Stage 1 snapshot: weekly simulated inventory and scalar capacity repeated by product | D03/D04/D06 require workload pools and initial-state/event separation | Version new contracts; never overwrite historical CSVs |
| C03 | Stage 5 frozen Service_Level/Allocation_Rate/Capacity_Gap | D08 expands KPI meaning | Keep legacy names/formulas in legacy schema; new names in Route B |
| C04 | Actual PBIX: Executive Summary, Demand Driver, Inventory Risk, Capacity Utilization Analysis, Service Risk Analysis | D09 target: Executive Overview, Demand Analysis, Capacity Monitoring, Inventory & Service Risk, Scenario Planning | Exactly five target pages approved; placement across PBIX/Streamlit is P20; no dashboard change now |
| C05 | Old dashboard proposal preserves five monitoring pages plus three scenario views | D09 five-page target | Historical proposal remains; owner reviews P20 mapping, no automatic eight-page expansion |
| C06 | README/docs/03 differ on simulated provenance and 75%/85% capacity assumptions | D02/D03 need traceable sources/new baseline | Do not reuse those percentages as new defaults; P04 |
| C07 | Existing ABC uses full-history gross quantity | Qualified-demand/workload changes could alter priorities | Preserve A/B/C mapping; recalculation basis P17 |
| C08 | Existing modules lack versioned run publication and stage gates | D10 complete pipeline and manifest | Minimal WP5 contracts early; full integration later |
| C09 | Existing sparse rows do not automatically mean zero demand | D04 every-week state conservation | P16 missing-observation/calendar policy; no silent densification |
| C10 | Historical notes say legacy stages complete | Route B new stages unimplemented | Add scope pointers only; do not rewrite historical completion claims |

Conflicts involving implementation remain open until the corresponding owner decision/stage authorization. New directional decisions are not a retroactive edit to completed-stage business rules.

## Scope control

Only documentation is created or updated now. Stage authorization must identify files, rule versions, tests and output destinations. No dependencies are installed, dashboards edited, datasets generated, notebooks executed or Git operations changing history performed.

Three read-only agents were used with explicitly selected gpt-6.1-sol and medium reasoning. Their scopes were demand/capacity, sequential validation, and KPI/dashboard/pipeline. The main agent reconciles one specification.
