# Data Contracts and KPI Catalog

> **Current CSV source contract:** [Planning CSV Inputs](../planning_csv_inputs.md) defines SYNTHETIC_DEMO and USER_DATA, neutral external fields, templates and diagnostics. Both convert to the same sequential_v1 engine bundle. The source-specific adapter requirements in the earlier upgrade record below remain compatibility history, not mandatory user-data schemas.

Original Route B v1.0 proposals remain unimplemented as a whole. The active reduced sequential_v1 implementation is documented first below.

## Active reduced upgrade contract sequential_v1

The owner subsequently authorized a reduced sequential implementation, not the complete proposed Route B contract set below. This section is the active implemented contract; DC01–DC15 below remain the broader original proposals unless explicitly mapped here.

- Historical inputs and legacy exact schemas remain untouched. New functions are additive and require explicit configuration.
- Input adapters: src/demand_preparation.py (prepare_demand, build_demand_coverage), src/workload_model.py (validate_workload_factors, calibrate_workload_capacity, expand_capacity_calendar).
- Planning: allocation_engine.allocate_workload, scenario_generator.generate_sequential_scenarios, inventory_engine.transition_inventory, sequential_planner.simulate_sequential.
- Independent validation: sequential_validator.validate_sequential_results imports no calculation engine; it reconstructs requirements, ranking, greedy workload allocation, receipts, cohort fulfillment and balances from original inputs.
- Execution: run_planning.run_sequential_planning; CLI --sequential-config. The legacy run_planning function and CLI remain separate.
- Output schema marker: Schema_Version=sequential_v1 and unique Run_ID on every artifact. Manifest records configuration, exact hashed source bytes, environment, scope, artifact hashes and independent validation/publication state.

### Required explicit inputs

JSON configuration requires assumption_version, planning_interpretation=RETROSPECTIVE, planning_start_week/end_week (Sunday labels), product_ids (explicit cohort), status_eligibility (bool per observed status), eligibility_version, source_is_complete (bool), orders_file (relative to data root), workload_factors_file, initial_state_file, external_receipts_file (relative to configuration directory), quantity_step, allocation_policy and scenarios. Supply exactly one capacity_file or capacity_calibration with start_week/end_week/target_utilization/capacity_version.

quantity_step=0 explicitly declares continuous product units; a positive value declares a pack/unit step. No operational default is inferred. The supported allocation_policy is PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT: retained product priority descending, uncovered obligation quantity descending, product ID ascending; within each product old backlog is fulfilled before current demand. A global backlog-before-any-current-demand cross-product override is not implemented or silently selected.

- Factors: Product Card Id, Workload_Factor (>0), Factor_Version, Workload_Unit, Provenance_Type. One compatible product-level factor/version/unit; plant-specific factors rejected.
- Initial state: Plant_ID, Product Card Id, Beginning_Inventory, Beginning_Backlog, Provenance_Type, Initial_State_Version. Required exactly once per initialized item; copied independently per scenario. No weekly stock replay. Nonzero opening backlog is incompatible with LOST_SALES.
- External receipts: Receipt_ID, Plant_ID, Product Card Id, Order_Date, External_Receipts_Qty, Provenance_Type, Receipt_Schedule_Version. Optional Scenario scopes events; otherwise the explicitly supplied schedule applies independently to each scenario. Order_Date means the week the input declares supply usable, not a purported actual procurement date. An explicitly empty schedule is valid; a missing schedule is not zero. Out-of-horizon/item events are rejected rather than consumed early.
- Explicit capacity file: Plant_ID, Baseline_Workload_Capacity, Capacity_Version, Provenance_Type, Factor_Version, Workload_Unit. Values are workload, never automatically converted from legacy pooled quantities. Calibration is explicitly synthetic qualified-workload mean / caller-provided target; window/cohort/version recorded.
- Scenario definitions: Scenario, Demand_Multiplier, Capacity_Multiplier, Disruption_Plants, Disruption_Weeks (explicit list or null for full horizon), Backlog_Policy. Baseline multipliers must equal 1; shortage mode is explicit. No +10%/-20% default in calculation logic.

### Coverage and transitions

Status values are OBSERVED_DEMAND, OBSERVED_ZERO, UNKNOWN, OUT_OF_SCOPE. Sparse demand remains sparse; a separate requested-horizon state view exposes missing coverage. Derived no-order zeros are permitted only under an explicit complete-extract assertion inside each observed product lifespan. Partial source edge weeks and missing outside-lifespan weeks remain UNKNOWN; no launch/discontinuation or zero-demand facts are inferred.

Each initialized item needs known full-horizon coverage. A limited cohort is explicitly configured and its omitted source demand quantified in the manifest.

Required_Production_Qty = max(Beginning_Backlog + Scenario_Qualified_Demand - Beginning_Inventory - External_Receipts_Qty, 0).
Internal production is bounded by remaining workload / factor and explicit quantity step. It serves unmet obligations only; no safety-stock replenishment target is invented.
Beginning inventory + usable external receipts + same-week production = fulfilled old backlog + fulfilled current demand + ending inventory.
CARRY_FORWARD carries unmet obligations; LOST_SALES records current unfilled demand as losses and never carries it.
Opening-origin backlog is tracked separately from horizon-origin backlog so later service of horizon demand is attributed correctly. No backlog age-based cross-product priority is added.

### Artifacts and KPIs

Each complete unique run contains eligibility_ledger, weekly_demand, demand_coverage, initial_state, external_receipts, workload_factors, capacity_baseline, scenario_snapshot, capacity_pools, allocation_result, performance_result, validation_result (CSV), plus run_manifest.json. allocation_result is the full sequential product-week state/allocation ledger, explicitly not the legacy 21-column schema. capacity_pools is one row per Scenario x Plant x Week.

Publication occurs only after all 12 artifacts and independent checks complete. Failed/partial runs remain UNPUBLISHED. The dashboard verifies manifest status, all artifact hashes and selected-table run/schema identity before loading.

Production_Coverage_Rate = sum Internal_Production_Qty / sum Required_Production_Qty. The denominator describes production requirements evaluated during the chosen periods and can include requirements carried from previous weeks; it is not unique customer demand.
Demand_Fulfillment_Rate at Scenario/Scenario x Plant = (fulfilled current demand + later fulfillment of horizon-origin backlog) / horizon scenario qualified demand. Fulfillment of pre-horizon backlog is excluded. Weekly views use current-week cohort fulfillment / current-week demand, with an explicit Fulfillment_Basis.
Capacity_Utilization = summed allocated workload / unique available plant-week workload pools.
Zero denominators produce NaN/N/A with Ratio_Zero_Policy=UNDEFINED_WHEN_DENOMINATOR_ZERO; no fabricated 100% service or Healthy classification.
Ending inventory/backlog use the terminal selected week per item, never a sum of weekly stocks. Lost sales, production and external receipts are period flows. Baseline deltas match grain and shortage policy; unmatched policies have no comparison value.
Unmet workload and bottleneck flags are plant-week quantities/flags, not calibrated probabilities.

Deferred from the broader program: DOI/safety-stock redesign, Alert Burden Index, five-page PBIX consolidation, age-sensitive routing, full procurement systems and configurable production lead times. The existing Streamlit scenario tabs receive the new prepared outputs; PBIX is unchanged.

## Original broader Route B contract conventions

Authoritative rules: [Business Rules Registry](02_business_rules.md). Unsettled semantics: [P01–P23](09_pending_decisions.md). All dataset and new column names below are target design proposals, not claims of existing files.

Each output carries Run_ID and Schema_Version. Scenario facts also carry Scenario. Identifier strings are nonempty; Product Card Id retains the source integer identifier. Order_Date remains a normalized Sunday week-ending date, not an arbitrary transaction timestamp. Date/as-of boundaries remain P02/P12. A supplied Planning_Key is a traceability string, never the only uniqueness constraint.

Type notation: str, int64, float64, bool, date, timestamp, JSON-object. Numerical quantities/capacities are finite and nonnegative; factors strictly positive. Quantity step/rounding/tolerance P13. All columns are non-null unless explicitly marked nullable. CSV schema comes from the contract, not inferred mixed types. Decimal versus float implementation may be reviewed for approved precision; no new dependency is required by this design.

Quantity unit: product units. Workload unit: EqWU with a declared reference and compatible unit/assumption version. EqWU is a relative workload unit, not a measured hour unless the approved methodology establishes that equivalence. Never sum EqWU from incompatible references. Stocks are quantities at a boundary; flows are quantities during a period.

Dimension FKs: Product Card Id -> preserved dim_product; Plant_ID -> preserved dim_plant; Plant_ID/Product Card Id -> approved product_plant_mapping. Existing single-plant eligibility remains. Run_ID -> run_manifest; Scenario -> scenario_definition within the same run. All tables reject unintended many-to-many merges.

## DC01 Status eligibility assumption

- Dataset name: status_eligibility (proposed future versioned assumption input; no file created now).
- Purpose: configurable qualification with reasons.
- Grain/PK: Eligibility_Version x Order_Status.
- FKs: referenced by eligibility_ledger and manifest assumption versions.
- Source: owner-approved mapping covering every observed raw status; P01.
- Transformation: exact status lookup, no automatic “non-canceled qualifies.”
- Validation: unique mapping; observed statuses covered; no overlapping eligibility definitions; unknown status does not silently qualify.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Eligibility_Version | str | No | Immutable assumption version |
| Order_Status | str | No | Original raw Order Status value |
| Is_Qualified | bool | No | Approved status disposition |
| Exclusion_Reason | str | Yes, only when qualified | Required explanation when excluded |
| Approval_Reference | str | No | Owner decision/effective record |
| Effective_From | date | No | Version validity |
| Effective_To | date | Yes, open-ended | No overlapping active version under selected mapping |

## DC02 Order eligibility ledger

- Dataset: eligibility_ledger.
- Purpose: preserve source quantities and make exclusions traceable.
- Grain/PK: Run_ID x Order Item Id (source item IDs freshly inspected as existing raw identifiers).
- FKs: product, plant mapping, selected status_eligibility.
- Source: selected raw DataCo columns, read-only.
- Transformation: map plant without row multiplication; map status; retain raw date/quantity/status.
- Validation: exact source item set, no duplicated item, keyed source preservation and line reconciliation.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version | str each | No | Run and contract identity |
| Order Item Id, Order Id, Product Card Id | int64 each | No | Original source identifiers |
| Plant_ID | str | No | Validated eligibility mapping |
| Source_Order_Status | str | No | Original Order Status |
| Source_Order_Date | timestamp | No | Original order date (DateOrders) |
| Order_Date | date | No | Derived week label |
| Source_Order_Qty | float64 | No | Product units, raw quantity preserved numerically |
| Is_Qualified | bool | No | Mapping result |
| Exclusion_Reason | str | Conditional | Required for excluded lines |
| Eligibility_Version, Source_Hash | str each | No | Exact mapping/input provenance |

No unrelated personal columns are needed in this derived ledger. Gross line quantity = Source_Order_Qty; qualified/excluded line contribution is determined by the approved mapping. Original raw records remain untouched.

## DC03 Sparse weekly demand

- Dataset: weekly_demand.
- Purpose: baseline historical gross/qualified/excluded demand.
- Grain/PK: Run_ID x Plant_ID x Product Card Id x Order_Date.
- FKs: dimensions, run; lineage to eligibility_ledger.
- Source: DC02.
- Transformation: sum disjoint line contributions to Sunday-ending product-week facts; preserve sparse observations.
- Validation: Gross_Demand = Qualified_Demand + Excluded_Demand at line-to-week, plant-week and run totals; no unknown mapping; no factor joins multiplying demand.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Plant_ID | str each | No | Context |
| Product Card Id | int64 | No | Product |
| Product Name | str | No | Master-validated label |
| Order_Date | date | No | Week-ending label |
| Gross_Demand, Qualified_Demand, Excluded_Demand | float64 each | No | Historical product quantity flows |
| Eligibility_Version, Demand_Date_Basis, Source_Hash | str each | No | Provenance; date basis remains historical Order Date |

Do not overwrite legacy plant_product_weekly_demand.csv or reinterpret Weekly_Demand as newly qualified demand without a version boundary.

## DC04 Workload factors

- Dataset: workload_factors; resolved per run as workload_factors_resolved.
- Purpose: convert product units into one compatible workload reference.
- Grain/PK: Factor_ID x Factor_Version. Natural uniqueness: product, factor scope, applicable plant and non-overlapping effective interval.
- FKs: product; plant when scope is plant-specific.
- Source: measured, SME or explicitly synthetic evidence approved under P03/P05.
- Transformation: effective-date and scope resolution; no undeclared fallback between global and plant factors.
- Validation: exactly one resolved factor for every allocated product/plant/week; positive finite factor; no overlapping matches; compatible workload unit.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Factor_ID, Factor_Version | str each | No | Assumption identity |
| Product Card Id | int64 | No | Product |
| Factor_Scope | str | No | PRODUCT or PLANT_PRODUCT; values proposed |
| Plant_ID | str | Yes, only PRODUCT scope | Future plant-factor extension |
| Workload_Factor | float64 | No | EqWU / product unit |
| Workload_Unit, Reference_Definition | str each | No | Compatible workload basis |
| Effective_From | date | No | Effective boundary |
| Effective_To | date | Yes | Open-ended allowed |
| Provenance_Type, Provenance_Reference, Approval_Reference | str each | No | Synthetic label and evidence required |

Resolved view adds Run_ID, Order_Date and non-null actual Plant_ID, retaining Factor_ID/Factor_Version. Factor_Scope must not expand product-plant production eligibility.

## DC05 Capacity pools

- Dataset: capacity_pools.
- Purpose: one authoritative workload pool independent of product facts.
- Grain/PK: Run_ID x Scenario x Plant_ID x Order_Date.
- FKs: scenario, plant, calibration/factor assumption versions.
- Source: approved recalibrated workload capacity and scenario disruption treatment.
- Transformation: apply disruption once to selected pools; retain baseline capacity separately.
- Validation: unique pool; finite nonnegative capacity; consistent workload unit; full declared available plant calendar; exact scenario treatment scope.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario, Plant_ID | str each | No | Context |
| Order_Date | date | No | Capacity week |
| Baseline_Workload_Capacity | float64 | No | EqWU before scenario treatment |
| Available_Workload_Capacity | float64 | No | EqWU available before allocations, not post-allocation slack |
| Workload_Unit, Capacity_Version, Factor_Version | str each | No | Calibration compatibility |
| Calibration_Reference, Assumption_Version | str each | No | Approved population/window/method |
| Capacity_Treatment_Reference | str | No | Explicit baseline/disruption definition |

P04 governs the numeric baseline and availability calendar. Capacity is never obtained by summing repeated product-row values. Reporting Remaining Capacity means Remaining_Workload_Capacity in this schema.

## DC06 Demand coverage calendar

- Dataset: demand_coverage.
- Purpose: distinguish absent observations from known zero demand for sequential processing.
- Grain/PK: Run_ID x Plant_ID x Product Card Id x Order_Date for declared coverage, not an automatically fabricated dense demand table.
- FKs: eligible product-plant, run/calendar.
- Source: declared completeness policy/evidence, P16.
- Transformation: attach coverage semantics without creating historical orders.
- Validation: no duplicate/conflicting coverage; UNKNOWN cannot become zero; observed demand must reconcile with coverage.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Plant_ID, Coverage_Status | str each | No | Proposed statuses KNOWN_OBSERVED / KNOWN_ZERO / UNKNOWN |
| Product Card Id | int64 | No | Product |
| Order_Date | date | No | Week |
| Coverage_Version, Coverage_Reference | str each | No | Evidence and approved missingness policy |

A separate declared plant calendar determines capacity availability. Explicitly initialized state may persist without an observed demand row only under approved known-zero/completeness semantics.

## DC07 Initial state

- Dataset: initial_state.
- Purpose: one scenario initialization source per declared eligible item.
- Grain/PK: Run_ID x Initial_State_ID x Plant_ID x Product Card Id.
- FKs: dimensions and scenario_definition.Initial_State_ID.
- Source: owner-approved as-of physical or explicitly synthetic opening state; P09/P12/P23.
- Transformation: no replay of later weekly legacy stock; maintain compatible date and backlog scope.
- Validation: finite nonnegative openings; source and as-of boundary valid; opening state complete for simulated items; lost-sales mode rejects any nonzero opening backlog unless an explicitly owner-approved migration defines its disposition; declaration alone does not authorize loss of old obligations.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Initial_State_ID, Plant_ID | str each | No | Context |
| Product Card Id | int64 | No | Product |
| State_As_Of | date | No | Boundary before first simulated period |
| Beginning_Inventory, Beginning_Backlog | float64 each | No | Product-unit stocks |
| Initial_State_Source, Initial_State_Version | str each | No | Explicit source/version |
| Backlog_Cohort_Reference | str | Conditional | Required for approved age-level claims; aggregate-only limitation otherwise explicit |

## DC08 External receipt events

- Dataset: external_receipts (resolved for each scenario; raw schedule source retained).
- Purpose: explicit external procurement receipts, separate from internal production.
- Grain/PK: Run_ID x Scenario x Receipt_ID.
- FKs: scenario, product-plant and declared calendar.
- Source: P06-approved schedule; synthetic flag when relevant.
- Transformation: assign to declared receipt period using P22 availability convention; aggregate only after checking unique events.
- Validation: no early booking, no duplicate event recognition, nonnegative quantities, no capacity debit, no copying implied legacy replenishment.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario, Receipt_ID, Plant_ID | str each | No | Context/event identity |
| Product Card Id | int64 | No | Product |
| Order_Date | date | No | Declared receipt week in planning calendar |
| External_Receipts_Qty | float64 | No | Product units |
| Receipt_Source, Receipt_Schedule_Version, Provenance_Type | str each | No | Explicit source/version/synthetic label |
| Receipt_Availability_Policy | str | No | P22-approved period availability |

An explicitly empty validated schedule is different from a missing schedule. Internal production never appears as an external receipt event.

## DC09 Scenario definitions

- Dataset: scenario_definition.
- Purpose: immutable explicit treatment and policy per scenario.
- Grain/PK: Run_ID x Scenario.
- FKs: run, opening state, receipt schedule and assumption versions.
- Source: owner-approved parameters/policies; P11/P19.
- Validation: explicit backlog policy; percentages finite; disruption range bounded; selected plants/weeks valid; no hidden policy defaults.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario | str each | No | Identity |
| Scenario_Kind | str | No | BASELINE / DEMAND_SURGE / CAPACITY_DISRUPTION / COMBINED_STRESS (proposed labels) |
| Backlog_Policy | str | No | LOST_SALES or CARRY_FORWARD |
| Initial_State_ID, Receipt_Schedule_Version | str each | No | State/supply sources |
| Demand_Surge_Pct, Capacity_Reduction_Pct | float64 each | No | Percent, explicitly 0 where no shock; capacity reduction <=100 |
| Affected_Plants, Affected_Weeks | JSON-object or list | No | Explicit scope, no inferred first plant |
| Demand_Treatment_Policy, Fulfillment_Policy, Quantity_Policy | str each | No | P19, P07/P08, P13 references |
| Assumption_Version, Planning_Interpretation | str each | No | P12 interpretation and approved bundle |

Scenario names must distinguish materially different parameters or be scoped by unique Run_ID plus immutable parameters. A legacy name does not imply Route B compatibility.

## DC10 Scenario demand

- Dataset: scenario_demand.
- Grain/PK: Run_ID x Scenario x Plant_ID x Product Card Id x Order_Date on sparse observed demand or separately approved known-zero event scope.
- FKs: scenario and weekly_demand or explicit coverage reference.
- Purpose/source: immutable baseline linkage plus declared synthetic treatment.
- Validation: original historical Gross/Qualified/Excluded remain unchanged; transforms agree with P19; no backlog hidden as current demand.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario, Plant_ID | str each | No | Context |
| Product Card Id | int64 | No | Product |
| Order_Date | date | No | Week |
| Scenario_Qualified_Demand | float64 | No | Current-period synthetic/treated qualified quantity |
| Incremental_Demand | float64 | No | Treated qualified demand minus historical qualified demand (nonnegative for current surge scope) |
| Demand_Treatment_Reference, Coverage_Status | str each | No | Transformation/known-data provenance |
| ABC_Class | str | No | A/B/C, input version P17 |
| Planning_Priority | int64 | No | Existing A3/B2/C1 mapping |

Historical reconciliation applies to DC03. If the owner wants a scenario gross/excluded reconciliation as well, P19 must define the synthetic excluded stream. Do not invent it or silently transform observed history.

## DC11 Product allocation fact

- Dataset: allocation_result_route_b.
- Grain/PK: Run_ID x Scenario x Plant_ID x Product Card Id x Order_Date.
- FKs: scenario demand/coverage, eligibility, resolved factor, unique capacity pool.
- Purpose: auditable internal-production decisions; no capacity total summed from product rows.
- Validation: source preservation, independent requirement/ranking/greedy checks, workload debit, order uniqueness and determinism.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario, Plant_ID | str each | No | Context |
| Product Card Id | int64 | No | Product |
| Order_Date | date | No | Production week |
| Planning_Priority, Allocation_Order | int64 each | No | Approved rank and unique contiguous group order |
| Required_Production_Qty | float64 | No | P14/P18-approved uncovered production requirement |
| Internal_Production_Qty | float64 | No | Same-week allocated product units |
| Workload_Factor, Allocated_Workload | float64 each | No | EqWU/unit; EqWU |
| Remaining_Workload_After_Row | float64 | No | Running audit only; never additive across products |
| Unmet_Production_Qty, Unmet_Workload | float64 each | No | Remaining production requirement; qty x factor under approved target |
| Factor_ID, Factor_Version, Allocation_Reason | str each | No | Provenance/explanation |

Required_Production_Qty replaces no legacy field silently. Its formula and sort role await P14/P18. Parent capacity is joined for display only; the authoritative total remains DC05.

## DC12 Sequential state and fulfillment

- Dataset: inventory_state_weekly.
- Grain/PK: Run_ID x Scenario x Plant_ID x Product Card Id x Order_Date for initialized items under approved coverage.
- FKs: initial state, scenario, demand/coverage, receipt/production sources.
- Source: chronological simulation; no core file I/O.
- Validation: BR-INV-001/002, BR-BKL-002/003, same-week production, cohort bounds and scenario isolation.

| Required column | Type | Nullable | Unit / meaning |
|---|---|---|---|
| Run_ID, Schema_Version, Scenario, Plant_ID, Backlog_Policy | str each | No | Context/policy |
| Product Card Id | int64 | No | Product |
| Order_Date | date | No | Week |
| Beginning_Inventory, Ending_Inventory | float64 each | No | Product-unit boundary stocks |
| Beginning_Backlog, Ending_Backlog | float64 each | No | Product-unit obligation boundary stocks |
| Scenario_Qualified_Demand | float64 | No | Current-period demand flow |
| External_Receipts_Qty, Internal_Production_Qty | float64 each | No | Separate product-unit supply flows |
| Fulfilled_Current_Qty, Fulfilled_Backlog_Qty | float64 each | No | Separate fulfillment flows |
| Lost_Sales_Qty, Current_Unfulfilled_Qty | float64 each | No | Loss versus current-period unfilled demand; not interchangeable with ending backlog |
| Coverage_Status, Initial_State_ID | str each | No | Known/observed or state-only provenance |
| Fulfillment_Policy | str | No | P07/P08 version |

Required cohort bounds: 0 <= Fulfilled_Current_Qty <= Scenario_Qualified_Demand and 0 <= Fulfilled_Backlog_Qty <= Beginning_Backlog. LOST_SALES also requires Fulfilled_Backlog_Qty = 0. Aggregate balance alone cannot verify correct cohort attribution.

Current_Unfulfilled_Qty = Scenario_Qualified_Demand - Fulfilled_Current_Qty. It becomes loss in LOST_SALES or contributes to backlog in CARRY_FORWARD, subject to cohort attribution. State-only rows are explicitly identified; they do not become invented historical demand observations.

Conditional dataset backlog_cohorts is required if P07/P08/P23 depend on age: key Run_ID, Scenario, Plant_ID, Product Card Id, Demand_Cohort_ID, Order_Date; fields Origin_Week(date), Beginning_Cohort_Qty, Added_Qty, Fulfilled_Cohort_Qty, Ending_Cohort_Qty (float product units), Cohort_Source(str). Cohort sums must equal aggregate state. It is not automatically necessary for aggregate-only policy; no age claims without it. If an approved KPI attributes terminal backlog to horizon-origin versus opening obligations, retain at least those origin buckets even without age-level cohorts, or block that KPI. Aggregate Ending_Backlog alone cannot supply origin attribution.

## DC13 Structured validation report

- Dataset: validation_findings plus validation_summary.
- Purpose: rule-level gate evidence, independent of successful engine completion.
- PK: Run_ID x Finding_ID; summary Run_ID x Stage_ID x Rule_ID.
- FKs: contract/rule and run; Scenario/key nullable for run-wide checks.
- Required finding columns: Run_ID(str), Finding_ID(str), Stage_ID(str), Rule_ID(str), Dataset(str), Check_Name(str), Canonical_Key(JSON-object nullable for whole-stage), Scenario(str nullable), Expected(JSON value nullable when not applicable), Actual(JSON value nullable when not applicable), Outcome(str), Severity(str), Message(str), Blocking(bool), Validator_Version(str).
- Outcomes proposed: PASS, FAIL, WARNING, NOT_EVALUATED. Missing policy/input is NOT_EVALUATED/BLOCKED at stage summary, never PASS.
- Summary includes checked counts, passed/failed/skipped counts and stage status.
- Validation: unique IDs, valid rule references, deterministic reporting order, no silent repairs. Warning/blocking classification must be approved with stage acceptance. Policy-dependent checks cannot pass simply because not executable.

## DC14 Run manifest and publication

- Dataset: run_manifest, proposed JSON storage at isolated run root.
- Grain/PK: Run_ID.
- FKs: artifacts and findings all reference same run.
- Source: orchestration plus immutable input/config references.
- Required fields: Run_ID(str), Schema_Version(str), Specification_Version(str), Started_At(timestamp), Finished_At(timestamp nullable while running), Execution_Status(str), Validation_Status(str), Publication_Status(str), Source_Hashes(JSON-object), Assumption_Versions(JSON-object), Scenario_Parameters(JSON-object), Environment_Identity(JSON-object), Stage_Results(JSON-object), Artifacts(JSON-object with paths/hashes/schema/grain/rowcounts), Planning_Horizon(JSON-object), Planning_Interpretation(str), Publication_Scope(str), Required_Stages(JSON list), Required_Artifacts(JSON list), Required_Metrics(JSON list), Optional_Metric_Status(JSON-object), Failure_Detail(JSON nullable unless failed).
- Proposed states: Execution CREATED/RUNNING/SUCCEEDED/FAILED; Validation NOT_EVALUATED/PASSED/FAILED/BLOCKED; Publication UNPUBLISHED/PUBLISHED. A manifest can record a failed run but cannot describe it as published success.
- Publication validation: every required artifact present, hashed, schema-valid and same Run_ID; stage success and blocking validation checks all pass; no unresolved business parameters for its declared publication scope; current reader selects one immutable run. Status transition/state names are technical design for review, not current implementation.
- Publication scope is explicit and approved in stage acceptance: a scope-complete validated stage fixture/view set may be published without claiming final raw-to-dashboard success. Required stages/artifacts/metrics are fixed before execution. Pending mandatory metric or policy blocks that scope. Optional unapproved metrics are absent with explicit NOT_EVALUATED status, not numeric zero/Healthy. Final D10/D08 program acceptance requires the complete approved raw-to-dashboard stage set and every mandatory expanded KPI; stage-scoped publication is not a waiver.
- UUID-style IDs proposed for uniqueness; reproducibility compares semantic data/config hashes, not wall-clock timestamp or random identifier equality.
- Paths proposed: data/processed/improvement_runs/<Run_ID>/staging and a complete publication mechanism. Do not create these directories or repoint legacy consumers during specification work.

## DC15 KPI facts and catalog

Target outputs: kpi_product_week, kpi_plant_week, kpi_scenario and kpi_terminal_state. All include Run_ID, Schema_Version, Scenario, KPI_Definition_Version. Plant/week/product keys are present only for their stated grain; use separate tables rather than one ambiguous mixed-grain fact. Numeric values must expose numerator/denominator and Unit where relevant; nullable ratios require an explicit Missing_Reason. Priority trade-offs additionally group by approved priority class.

Sources: validated DC03/DC05/DC11/DC12, optional backlog cohorts and versioned inventory policy. No KPI module recalculates production decisions.

A = sum Internal_Production_Qty; R = sum Required_Production_Qty; Q = sum Scenario_Qualified_Demand; Fcur = sum Fulfilled_Current_Qty; Fback = sum Fulfilled_Backlog_Qty. “Sum” is over compatible units and the declared time/cohort scope. Stocks are not summed across periods. Proposed formulas below remain Pending where identified; names alone in D08 do not approve new zero-denominator rules.

| KPI / target column | Formula or definition | Grain / aggregation | Unit and status |
|---|---|---|---|
| Gross Demand / Gross_Demand | DC03 historical gross | Sum quantity flows at product/plant/week/horizon | Product units; approved identity, product-mix total descriptive |
| Qualified Demand / Qualified_Demand | DC03 eligible historical quantity | Sum disjoint eligible line contributions | Product units; whitelist P01 |
| Excluded Demand / Excluded_Demand | DC03 excluded quantity | Sum disjoint excluded line contributions | Product units; reasons retained |
| Scenario qualified demand / Scenario_Qualified_Demand | DC10 treated current demand | Sum flows; never add incoming backlog as new demand | Product units; transform P19 |
| Production Coverage Rate / Production_Coverage_Rate | Proposed A / R | Ratio of sums, net production requirements only | Ratio; P14/P15/zero rule pending |
| Demand Fulfillment Rate / Demand_Fulfillment_Rate | Proposed Fcur / Q for current demand, Fback reported separately | Ratio of sums, same current-demand cohort | Ratio; P08/P15/zero rule pending; not OTD |
| Backlog Rate / Backlog_Rate | Proposed terminal backlog from horizon-current cohorts / Q; opening backlog tracked separately | Horizon/cohort denominator; weekly alternatives explicitly named | Ratio; P15/P23 pending; requires opening-versus-horizon origin attribution or remains blocked; never sum repeated ending backlog |
| Available Workload Capacity / Available_Workload_Capacity | Unique DC05 pool before allocation | Sum distinct plant-week pools within compatible unit | EqWU; baseline P04 |
| Allocated Workload / Allocated_Workload | Sum quantity x effective factor | Additive workload flow | EqWU; D03 |
| Capacity Utilization / Capacity_Utilization | Sum Allocated_Workload / sum Available_Workload_Capacity | Plant-week and ratio of sums; explicit complete calendar | Ratio; workload formula derived D03, zero convention P15 |
| Remaining Capacity / Remaining_Workload_Capacity | Capacity - allocated workload | Unique pool balance; sum compatible pools | EqWU; D03 |
| Unmet Workload / Unmet_Workload | Proposed Unmet_Production_Qty x factor | Product-week; repeated carried requirement must not be presented as unique horizon shortage | EqWU; P14/P18/P15 scope pending |
| Inventory On Hand / Inventory_On_Hand | Proposed Ending_Inventory | Product/plant at selected week; terminal snapshot or explicitly labeled average over time | Product units; ending basis P15 |
| DOI / DOI | Proposed Ending_Inventory / approved Average_Daily_Demand | Product-week first; no naive sum or mean over unlike products | Days; mean window, demand basis and zero behavior P15 |
| Safety Stock / Safety_Stock_Qty | Proposed policy Safety_Stock_Days x approved Average_Daily_Demand | Product-week reference; quantity/day definitions separate | Product units/days; P15/P17, not statistical optimum |
| Stockout Exposure / Stockout_Exposure | Proposed explicit stock/shortfall predicate | Event-grain count or share with explicit denominator | Indicator/count; P15/P21, not probability |
| External Receipts / External_Receipts_Qty | Sum unique external receipt events | Product/plant/week/horizon flow | Product units; P06/P22 |
| Internal Production / Internal_Production_Qty | DC11 allocated same-week production | Product/plant/week/horizon flow | Product units; D07 |
| Plant-Week Bottleneck / Plant_Week_Bottleneck | Proposed unmet workload >0 plus separate fully-used pool flag | Run/Scenario/Plant/Week; threshold status separate | Indicator; P10/P15, no automatic legacy thresholds |
| Priority Allocation Trade-offs / Priority_Tradeoff | Production, fulfilled-current, losses and terminal backlog by priority class; comparisons to same-policy Baseline | Class-specific ratio numerators/denominators; cohort and stock rules retained | Quantities/ratios; P07/P15/P17 |
| Alert Burden Index / Alert_Burden_Index | Proposed sum of explicitly defined event counts; disaggregated components retained | Declared plant-week and product-week events; no unrecorded overlap/weights | Burden count/index; P21 pending |

Legacy Service_Level, Allocation_Rate, Capacity_Gap and legacy utilization remain in legacy performance outputs with their old formulas. New Route B workload Capacity_Utilization has a distinct schema/KPI-definition version and cannot be concatenated with old quantity utilization without explicit labels.

## Dashboard reconciliation contract

Exactly five approved logical pages consume the same published Run_ID. P20 controls physical PBIX/Streamlit mapping.

- Executive Overview: reconciled demand, fulfillment and terminal shortage/stock, workload and disaggregated burden.
- Demand Analysis: gross/qualified/excluded and exclusion reasons, current demand growth over the declared full eligible universe.
- Capacity Monitoring: unique plant-week pools, workload/remaining/unmet load, product factor provenance.
- Inventory & Service Risk: sequential stock, explicit receipts/production, current fulfillment, backlog/loss mode and rule-based exposure.
- Scenario Planning: four approved scenario definitions, active assumptions, same-policy Baseline comparisons, allocation order, priority and cohort trade-offs.

No UI/DAX replica of eligibility, production allocation, state simulation or KPI numerator logic. Ratio aggregation must use backend-approved numerators/denominators, and readers reject mixed runs/units/versions or incomplete publication.
