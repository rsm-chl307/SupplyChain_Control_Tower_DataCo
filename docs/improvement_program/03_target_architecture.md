# Target Architecture

Version 1.0 • 2026-11-17 • Proposed technical design implementing approved direction • NOT IMPLEMENTED.

## Retained boundaries and versioning

Keep pure Pandas engines, one shared plant-week allocation pool, separate scenario generation/allocation/KPI/status, and orchestration-owned I/O. Preserve legacy interfaces and output artifacts under their legacy schema. Route B uses an explicit Schema_Version, separate inputs/state/pool facts and isolated outputs. Do not append new columns to an exact legacy contract and hope old validators accept it.

The proposed version labels legacy_v1 and route_b_v1 are contract identifiers for review, not implemented configuration. Field names and new file names are design proposals; any stage-specific refinement updates the shared contract first.

## Flow

    Immutable raw orders + authoritative product/plant mapping
        -> demand_preparation: eligibility ledger and sparse dual demand
    Versioned workload factors + approved capacity recipe
        -> workload_model: positive factors and unique plant-week workload pools
    Opening state + explicit receipt events + completeness/calendar
        -> planning_snapshot: Route B input bundle (no weekly stock resets)
    Scenario definitions
        -> scenario_generator: transformed current demand and capacity views
        -> sequential_planner: scenario -> week -> plant
             -> construct approved uncovered production requirements
             -> allocation_engine: workload-aware group allocation
             -> inventory_engine: same-week production and quantity balance
             -> retain scenario inventory/backlog state and cohort attribution
    Independent allocation_validator + inventory_validator
        -> structured validation_report
    kpi_engine -> performance_evaluator -> performance_manager
        -> grain-specific dashboard outputs
    run_planning + pipeline/run_management
        -> stage gates + isolated artifacts + manifest + publication
    PBIX / Streamlit
        -> consume one fully published Run_ID

Existing allocation_manager.run_allocation remains the legacy independent-week wrapper. The new sequential_planner calls the versioned group allocation interface; it must not simulate a year by independently applying the legacy manager to stock copied from each historical week.

## Module contract proposals

| Module/function boundary | Input | Output | Owner |
|---|---|---|---|
| data_contracts | Versioned schema/key/unit descriptors only | Shared definitions | WP1, extended WP2–4 |
| validation_report | Findings with rule/key/expected/actual | Structured report; no repair | WP1 |
| demand_preparation.prepare_demand | Selected raw columns, mapping, eligibility config | Eligibility ledger + sparse dual demand + reconciliation | WP2 |
| workload_model.prepare_workload | Factors, eligible products, approved capacity recipe/calendar | Resolved factors + workload capacity pools | WP2 |
| planning_snapshot Route B builder | Demand/coverage, pool, initial state, receipt and policy references | Validated input bundle, not a wide repeated-capacity fact | WP2/3 |
| scenario_generator Route B generator | Bundle, explicit scenario definitions | Versioned demand and pool views; immutable historical streams | WP3, combined support WP6 |
| allocation_engine Route B group function | Approved Required_Production_Qty and priority per product; factor; one scalar workload pool | Product production/workload allocations and sequence audit | WP3 |
| inventory_engine transition | Beginning state, current demand, cohort policy, receipts, production | Fulfillment by cohort, ending stock/backlog/losses | WP3 |
| sequential_planner | Initial states, coverage/calendar, scenario views, receipt events, explicit policy | Sequential state/fulfillment/allocation/pool facts | WP3 |
| allocation_validator | Authoritative state/demand/receipts/policies plus candidate requirements/pool/factors/allocations | Independent expected arithmetic/order findings | WP1 + WP3 extensions |
| inventory_validator | Initial state, raw receipts/demand, policies, candidate state/fulfillment | Independent continuity and conservation findings | WP1 contract, WP3 implementation |
| kpi_engine/evaluator/manager Route B | Validated state, allocation and unique capacity facts | Separate product-week, plant-week, scenario and terminal views | WP4 |
| upstream_pipeline | Explicit source paths and configs | Validated preparation artifacts; boundary I/O only | WP5, pure transformations reused WP2 |
| run_management | Run metadata, hashes, statuses, stage outputs | Manifest and safe immutable publication selection | WP5 minimum early, integration later |
| run_planning | Source/config references and authorized mode/version | Run result including Run_ID and manifest path | WP5 |
| dashboard loaders | Published Run_ID and complete manifest | Consistent prepared backend views | WP4/5 |

Proposed new modules are not existing files. Exact argument types are DataFrames plus explicit immutable configuration records. No core engine reads CSVs, installs dependencies, or chooses missing business defaults.

## Sparse demand versus sequential state

Retain sparse demand facts. A state ledger is a separate necessary artifact: stock/backlog for an initialized eligible product can persist when no demand fact exists. That is not evidence of zero demand. The coverage/calendar contract must identify KNOWN_OBSERVED, KNOWN_ZERO or UNKNOWN. These label names are technical proposals; P16 approves their meaning and coverage method.

UNKNOWN input blocks the dependent scenario week rather than silently generating zero demand. Known-zero weeks may produce state-only rows, explicitly labeled, while capacity remains in a separate complete plant-week pool. Do not build a dense product-demand grid or delete sparse identities.

A product not yet initialized cannot receive a guessed zero stock/backlog state. Late product starts, horizon boundaries and opening cohorts are P09/P23.

## Sequential execution and conservation

For each scenario, create isolated initial state, process weeks chronologically and allocate independently within each plant's shared workload pool for that week. Same-week allocated production is available immediately in that week's fulfillment balance. External receipts cannot be recognized early; their within-week fulfillment availability remains P22.

Do not implement cohort ordering before P07/P08. Preserve current demand separately from beginning backlog; do not hide backlog in Scenario_Demand or replay weekly initial inventory. Maintain explicit fulfilled-current and fulfilled-backlog quantities, even if only aggregate backlog cohorts are approved.

General approved identities:

- Beginning inventory + external receipts + production = current fulfillment + backlog fulfillment + ending inventory.
- Carry mode: beginning backlog + current qualified demand = total fulfillment + ending backlog; lost sales = 0.
- Lost-sales mode: beginning/ending backlog = 0; current qualified demand = current fulfillment + lost sales.
- Allocated workload = production quantity x factor; pool remaining = capacity - summed allocated workload.

The independent validator must recompute Required_Production_Qty and its secondary ranking measure from authoritative opening state, current demand, receipt events and approved P14/P18 policies. Validating only allocation against the engine-supplied requirement is insufficient. This check stays BLOCKED until the policies are approved.

Production target, uncovered-requirement construction, cohort priority, factor application/rounding and missing-week coverage remain pending. These equations do not settle those choices.

## Extensibility limits

Reserve factor plant scope/effective dates and a state-event boundary for future lead times. Do not introduce configurable production lead-time offsets, a scheduler, procurement optimizer, multi-plant routing, database or external agent framework in this program.
