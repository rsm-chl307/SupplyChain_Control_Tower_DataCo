# Business Rules Registry

Version 1.0 • 2026-11-17 • Direction approved; implementation NOT AUTHORIZED.

## Interpretation

Status Approved means an explicit owner requirement, retained legacy rule, or unavoidable dimensional/conservation consequence. It does not authorize implementation. Status Pending means at least one operational policy/formula is unsettled; the referenced owner decision is required before enabling it.

Source records distinguish approved decisions, retained legacy specifications, derived technical invariants and proposals. Proposed field/API names in the contracts remain technical design for review, not claims of current implementation. A rule may impose an approved formula while its input values or schedules remain pending.

Quantities are product units; workload is EqWU in one declared compatible unit/version; stocks are at period boundaries. The general inventory equation does not by itself decide whether a within-week receipt is available before demand fulfillment.

Test IDs link to the [test catalog](08_testing_and_acceptance.md). No future test is claimed to exist today.

## BR-VAL-001

| Field | Definition |
|---|---|
| Rule ID | BR-VAL-001 |
| Domain | Validation |
| Rule | Expected results are independently verified; validators must not call production/scenario/allocation/state engines to obtain expected results. |
| Formula | Independent arithmetic, ordering, source and conservation checks. |
| Inputs | Source frames, candidate outputs, declared contracts/policies. |
| Outputs | Structured findings and validation status. |
| Constraints | Shared names/types may be imported; shared production calculation helpers may not serve as oracle. |
| Source | D01; approved requirement |
| Status | Approved |
| Test Reference | T-VAL-001 — see test catalog |

## BR-VAL-002

| Field | Definition |
|---|---|
| Rule ID | BR-VAL-002 |
| Domain | Validation |
| Rule | Validate schemas, finite numerics, canonical keys and authoritative foreign keys before calculation. |
| Formula | Business key tuples, not a supplied string alone. |
| Inputs | Frames, master references, schema version. |
| Outputs | Reject invalid/duplicate/unmapped inputs. |
| Constraints | Nonnegative quantities/capacities; strictly positive workload factors; finite values. Quantity step/tolerance is P13. |
| Source | D01; D03; necessary type/unit constraints |
| Status | Approved |
| Test Reference | T-VAL-002 — see test catalog |

## BR-VAL-003

| Field | Definition |
|---|---|
| Rule ID | BR-VAL-003 |
| Domain | Validation |
| Rule | Preserve input identity and immutable source fields and report each check with traceable keys. |
| Formula | Keyed expected source value = preserved value. |
| Inputs | Raw/source provenance, output, allowed transformation list. |
| Outputs | Finding_ID, Rule_ID, Dataset, key, expected, actual, severity, outcome. |
| Constraints | Allowed scenario transformations use distinct fields; do not dump unrelated raw fields. |
| Source | D01; D02 |
| Status | Approved |
| Test Reference | T-VAL-003 — see test catalog |

## BR-DMD-001

| Field | Definition |
|---|---|
| Rule ID | BR-DMD-001 |
| Domain | Demand |
| Rule | Every source quantity is reconciled between gross, qualified and excluded streams. |
| Formula | Gross_Demand = Qualified_Demand + Excluded_Demand. |
| Inputs | Order Item Id, Order Item Quantity, approved eligibility result. |
| Outputs | Gross_Demand, Qualified_Demand, Excluded_Demand. |
| Constraints | Same cohort, product, plant, week and source version; no duplicated line during joins. |
| Source | D02 |
| Status | Approved |
| Test Reference | T-DMD-001 — see test catalog |

## BR-DMD-002

| Field | Definition |
|---|---|
| Rule ID | BR-DMD-002 |
| Domain | Demand |
| Rule | Qualification uses a configurable owner-approved status mapping and traceable exclusion reasons. |
| Formula | Qualified_Demand = sum(quantity for approved eligible lines). |
| Inputs | Order Status, approved mapping/version, source lines. |
| Outputs | Eligibility ledger and weekly dual demand. |
| Constraints | P01 whitelist unresolved; unknown mapping must not silently qualify. Explicit failure disposition remains technical review. |
| Source | D02; P01; exact list pending |
| Status | Pending |
| Test Reference | T-DMD-002 — see test catalog |

## BR-DMD-003

| Field | Definition |
|---|---|
| Rule ID | BR-DMD-003 |
| Domain | Demand |
| Rule | Retain existing historical Order Date unless separately approved. |
| Formula | Week labels retain existing Sunday-ending basis; as-of details P02/P12. |
| Inputs | order date (DateOrders). |
| Outputs | Order_Date weekly label. |
| Constraints | No silent requested-date/shipping-date substitution. |
| Source | D02; current notebooks; boundary details P02/P12 |
| Status | Approved |
| Test Reference | T-DMD-003 — see test catalog |

## BR-DMD-004

| Field | Definition |
|---|---|
| Rule ID | BR-DMD-004 |
| Domain | Demand |
| Rule | Original order records/quantities remain unchanged and exclusions remain line-traceable. |
| Formula | Every source Order Item Id has exactly one eligibility disposition. |
| Inputs | Raw source, eligibility mapping. |
| Outputs | Source-preserving eligibility ledger. |
| Constraints | No in-place raw edits; aggregate-only exclusions are insufficient. |
| Source | D02; D01 |
| Status | Approved |
| Test Reference | T-DMD-001 — see test catalog |

## BR-CAP-001

| Field | Definition |
|---|---|
| Rule ID | BR-CAP-001 |
| Domain | Capacity |
| Rule | Convert product production quantity using its effective workload factor. |
| Formula | Allocated_Workload = Internal_Production_Qty * Workload_Factor. |
| Inputs | Product, optional plant scope, effective factor/version, production quantity. |
| Outputs | Equivalent workload in declared common unit. |
| Constraints | Factor positive/finite and complete; values/method P03, scope P05, precision P13. |
| Source | D03; formula approved, factor values pending |
| Status | Approved |
| Test Reference | T-CAP-001 — see test catalog |

## BR-CAP-002

| Field | Definition |
|---|---|
| Rule ID | BR-CAP-002 |
| Domain | Capacity |
| Rule | Each Run x Scenario x Plant x Week has one workload capacity pool. |
| Formula | sum(Allocated_Workload) <= Available_Workload_Capacity; Remaining_Workload_Capacity = Available_Workload_Capacity - sum(Allocated_Workload). |
| Inputs | Unique capacity pool and product allocations. |
| Outputs | Pool balance and utilization inputs. |
| Constraints | Never sum capacity repeated on product rows. One workload unit/version per compatible pool. |
| Source | D03; D01; dimensional consequence |
| Status | Approved |
| Test Reference | T-CAP-002 — see test catalog |

## BR-CAP-003

| Field | Definition |
|---|---|
| Rule ID | BR-CAP-003 |
| Domain | Capacity |
| Rule | Re-establish workload capacity with provenance rather than relabeling old quantity capacity. |
| Formula | Baseline method/window/target/rounding P04. |
| Inputs | Approved workload unit, factors, capacity evidence and calibration data. |
| Outputs | Versioned baseline workload capacity. |
| Constraints | P03/P04/P05/P12 must be resolved for real baseline; no automatic legacy 0.75 target. |
| Source | D03; P03–P05/P12 |
| Status | Pending |
| Test Reference | T-CAP-003 — see test catalog |

## BR-INV-001

| Field | Definition |
|---|---|
| Rule ID | BR-INV-001 |
| Domain | Inventory |
| Rule | Carry prior ending inventory into the next modeled week within each scenario trajectory. |
| Formula | Beginning_Inventory[t+1] = Ending_Inventory[t]. |
| Inputs | Initial state, prior ending state, calendar/coverage. |
| Outputs | Beginning/ending inventory ledger. |
| Constraints | No cross-scenario state and no weekly reset from old snapshots. Missing-week policy P16. |
| Source | D04 |
| Status | Approved |
| Test Reference | T-SEQ-001 — see test catalog |

## BR-INV-002

| Field | Definition |
|---|---|
| Rule ID | BR-INV-002 |
| Domain | Inventory |
| Rule | Inventory and fulfilled quantities obey conservation; production and receipts cannot be counted twice. |
| Formula | Beginning_Inventory + External_Receipts_Qty + Internal_Production_Qty = Fulfilled_Current_Qty + Fulfilled_Backlog_Qty + Ending_Inventory. |
| Inputs | Declared opening state, receipts, production and fulfillment. |
| Outputs | Nonnegative balanced closing stock. |
| Constraints | Cohort bounds: 0 <= Fulfilled_Current_Qty <= Scenario_Qualified_Demand; 0 <= Fulfilled_Backlog_Qty <= Beginning_Backlog. Period-total balance assumes receipts booked in their declared period; availability for fulfillment P22; no shrink/scrap/transfers in this scope. |
| Source | D04/D06/D07; derived conservation identity |
| Status | Approved |
| Test Reference | T-SEQ-002 — see test catalog |

## BR-INV-003

| Field | Definition |
|---|---|
| Rule ID | BR-INV-003 |
| Domain | Inventory |
| Rule | Use one declared opening inventory/backlog state; initial policy and evidence require approval. |
| Formula | Initial state = approved as-of input, not later-week baseline inventory. |
| Inputs | Opening stock/backlog input and source/version. |
| Outputs | Scenario initial state. |
| Constraints | P09/P12/P23; scenario comparison initialization policy explicit. |
| Source | D04; P09/P12/P23 |
| Status | Pending |
| Test Reference | T-SEQ-003 — see test catalog |

## BR-INV-004

| Field | Definition |
|---|---|
| Rule ID | BR-INV-004 |
| Domain | Inventory |
| Rule | External supply is explicit and cannot enter inventory before its declared receipt period. |
| Formula | Receipt is booked in its declared period, never earlier; within-week fulfillment availability P22. Any schedule change requires a versioned event revision. |
| Inputs | Receipt_ID, quantity, declared period/source/version. |
| Outputs | External_Receipts_Qty. |
| Constraints | Do not infer actual procurement from synthetic Replenishment_Qty; schedule P06; no internal capacity debit. |
| Source | D06; timing minimum approved |
| Status | Approved |
| Test Reference | T-RCP-001 — see test catalog |

## BR-PROD-001

| Field | Definition |
|---|---|
| Rule ID | BR-PROD-001 |
| Domain | Production |
| Rule | Internal production is capacity allocated, consumes equivalent workload and is usable in its production week. |
| Formula | Production receipt[t] = allocated production[t]; workload debit = production * factor. |
| Inputs | Allocated quantity and factor. |
| Outputs | Internal_Production_Qty and same-week supply. |
| Constraints | No configurable multiweek lead-time parameter. Target-stock building remains P18. |
| Source | D03/D06/D07 |
| Status | Approved |
| Test Reference | T-SEQ-004 — see test catalog |

## BR-ALLOC-001

| Field | Definition |
|---|---|
| Rule ID | BR-ALLOC-001 |
| Domain | Allocation |
| Rule | Preserve frozen quantity allocation in legacy mode and historical artifacts. |
| Formula | Net_Demand=max(Scenario_Demand-Beginning_Inventory,0); Allocated_Qty=min(Net_Demand,remaining old quantity capacity). |
| Inputs | Legacy exact-schema snapshot. |
| Outputs | Legacy allocation result. |
| Constraints | Legacy Backlog=Net_Demand-Allocated_Qty; no silent workload substitution. |
| Source | Existing Stage 4 freeze; D08 preservation |
| Status | Approved |
| Test Reference | T-REG-001 — see test catalog |

## BR-ALLOC-002

| Field | Definition |
|---|---|
| Rule ID | BR-ALLOC-002 |
| Domain | Allocation |
| Rule | Route B allocation converts remaining workload to feasible product quantity; exact requirement/rounding policy is pending. |
| Formula | Proposed q=min(Required_Production_Qty, remaining workload / factor), subject to approved quantity step. |
| Inputs | State, uncovered obligations, factor and pool. |
| Outputs | Internal_Production_Qty, Allocated_Workload, allocation audit. |
| Constraints | P13/P14/P18; do not treat proposed equation as permission to select policies. |
| Source | D03; derived unit constraint; detailed choice pending |
| Status | Pending |
| Test Reference | T-ALLOC-001 — see test catalog |

## BR-ALLOC-003

| Field | Definition |
|---|---|
| Rule ID | BR-ALLOC-003 |
| Domain | Allocation |
| Rule | Retain priority descending and Product Card Id ascending tie-break; confirm Route B secondary net-requirement key and cohort sequence. |
| Formula | Legacy key: Planning_Priority DESC, Net_Demand DESC, Product Card Id ASC. |
| Inputs | ABC/priority, explicit requirement and cohort policy. |
| Outputs | Allocation_Order and reason. |
| Constraints | A/B/C maps 3/2/1; P07/P08/P14/P17 govern extensions, not hidden age/workload ranking. |
| Source | Existing priority freeze; P07/P08/P14/P17 |
| Status | Pending |
| Test Reference | T-ALLOC-002 — see test catalog |

## BR-ALLOC-004

| Field | Definition |
|---|---|
| Rule ID | BR-ALLOC-004 |
| Domain | Allocation |
| Rule | Production stays within approved product-plant eligibility; no cross-plant transfers/routing extension. |
| Formula | Allocated item must reference an eligible Plant_ID/Product pair. |
| Inputs | Product master, plant master, mapping. |
| Outputs | Eligible allocations only. |
| Constraints | Plant-specific factor capability does not expand eligibility. |
| Source | Existing Stage 4 freeze retained; D03 future factor scope |
| Status | Approved |
| Test Reference | T-VAL-002 — see test catalog |

## BR-BKL-001

| Field | Definition |
|---|---|
| Rule ID | BR-BKL-001 |
| Domain | Backlog |
| Rule | Every scenario explicitly declares LOST_SALES or CARRY_FORWARD. |
| Formula | No policy default; policy recorded in Scenario_Definition. |
| Inputs | Scenario and Backlog_Policy. |
| Outputs | Policy-specific shortage fields. |
| Constraints | No mixing loss and backlog or silent switching over time. |
| Source | D05 |
| Status | Approved |
| Test Reference | T-BKL-001 — see test catalog |

## BR-BKL-002

| Field | Definition |
|---|---|
| Rule ID | BR-BKL-002 |
| Domain | Backlog |
| Rule | LOST_SALES does not propagate unmet current demand as backlog. |
| Formula | Beginning_Backlog=0; Ending_Backlog=0; Fulfilled_Backlog_Qty=0; Lost_Sales_Qty=Scenario_Qualified_Demand-Fulfilled_Current_Qty. |
| Inputs | Qualified demand and fulfillment. |
| Outputs | Lost_Sales_Qty; zero backlog trajectory. |
| Constraints | Nonzero opening backlog is incompatible unless owner explicitly defines a migration; no implicit discard. |
| Source | D05; necessary mode distinction |
| Status | Approved |
| Test Reference | T-BKL-002 — see test catalog |

## BR-BKL-003

| Field | Definition |
|---|---|
| Rule ID | BR-BKL-003 |
| Domain | Backlog |
| Rule | CARRY_FORWARD preserves unfulfilled obligations and does not label them lost sales. |
| Formula | Ending_Backlog=Beginning_Backlog+Scenario_Qualified_Demand-Fulfilled_Current_Qty-Fulfilled_Backlog_Qty; Beginning_Backlog[t+1]=Ending_Backlog[t]; Lost_Sales_Qty=0. |
| Inputs | Backlog, current demand, cohort fulfillment. |
| Outputs | Ending backlog and next opening backlog. |
| Constraints | Nonnegative; no hidden expiry/cancellation; terminal backlog explicitly reported. |
| Source | D04/D05; derived obligation balance |
| Status | Approved |
| Test Reference | T-BKL-003 — see test catalog |

## BR-BKL-004

| Field | Definition |
|---|---|
| Rule ID | BR-BKL-004 |
| Domain | Backlog |
| Rule | Backlog age, cross-product priority and current-versus-old fulfillment sequence require explicit policy. |
| Formula | Cohort sequence P07/P08/P23. |
| Inputs | Opening cohorts and approved policy. |
| Outputs | Fulfillment attribution and cohort balances. |
| Constraints | Do not choose oldest-first merely because it is common. |
| Source | D05; P07/P08/P23 |
| Status | Pending |
| Test Reference | T-BKL-004 — see test catalog |

## BR-SCN-001

| Field | Definition |
|---|---|
| Rule ID | BR-SCN-001 |
| Domain | Scenario |
| Rule | Each scenario has its own inventory/backlog trajectory, parameters and receipts references. |
| Formula | State key includes Run_ID and Scenario. |
| Inputs | Scenario definitions and initial-state references. |
| Outputs | Isolated state ledger. |
| Constraints | No shared mutable state; initial comparability policy P09; immutable historical demand. |
| Source | D04/D10 |
| Status | Approved |
| Test Reference | T-SCN-001 — see test catalog |

## BR-SCN-002

| Field | Definition |
|---|---|
| Rule ID | BR-SCN-002 |
| Domain | Scenario |
| Rule | Provide Baseline, Demand Surge, Capacity Disruption and Combined Stress definitions. |
| Formula | Shock composition/scope P19; final magnitudes P11. |
| Inputs | Approved parameters, factors and baseline capacity. |
| Outputs | Four named scenario definitions and comparable outputs. |
| Constraints | +10%/-20% candidates only; no baseline manipulation. |
| Source | D11; parameter decisions pending |
| Status | Pending |
| Test Reference | T-SCN-002 — see test catalog |

## BR-SCN-003

| Field | Definition |
|---|---|
| Rule ID | BR-SCN-003 |
| Domain | Scenario |
| Rule | Preserve sparse demand facts; sequential calendar/coverage cannot infer zero from an absent row. |
| Formula | Known demand coverage + state calendar policy P16. |
| Inputs | Sparse demand, coverage calendar, opening state. |
| Outputs | Complete validated state trajectory without fabricated demand. |
| Constraints | Separate state-only records require known coverage and provenance; no dense demand grid by default. |
| Source | Existing sparse freeze; D04; P16 |
| Status | Pending |
| Test Reference | T-SEQ-005 — see test catalog |

## BR-KPI-001

| Field | Definition |
|---|---|
| Rule ID | BR-KPI-001 |
| Domain | KPI |
| Rule | Legacy KPI formulas/names remain version-bound and distinct from new business measures. |
| Formula | Service_Level=allocated/net (zero=>1); Allocation_Rate=allocated/demand (zero=>1); Capacity_Gap=capacity-allocated; utilization allocated/capacity (zero=>0). |
| Inputs | Legacy allocation results. |
| Outputs | Legacy performance results. |
| Constraints | Do not reuse Service_Level as customer fill or Capacity_Gap as unmet workload. |
| Source | D08; existing Stage 5 |
| Status | Approved |
| Test Reference | T-REG-001 — see test catalog |

## BR-KPI-002

| Field | Definition |
|---|---|
| Rule ID | BR-KPI-002 |
| Domain | KPI |
| Rule | Keep quantity flows, workload flows and end-of-period stocks distinct during aggregation. |
| Formula | Workload sums only in compatible units; rates from summed numerators/denominators; inventory/backlog are closing stocks across time. |
| Inputs | Versioned state and pool facts. |
| Outputs | Separate plant-week/scenario views and stock snapshots. |
| Constraints | Never sum repeated capacity or backlog stocks across weeks as unique demand; P15 defines rate cohorts. |
| Source | D03/D08; dimensional/stock-flow consequence |
| Status | Approved |
| Test Reference | T-KPI-001 — see test catalog |

## BR-KPI-003

| Field | Definition |
|---|---|
| Rule ID | BR-KPI-003 |
| Domain | KPI |
| Rule | New coverage, fulfillment, backlog, DOI, safety-stock/exposure and trade-off metrics use separately approved formulas. |
| Formula | Proposed catalog in 04_data_contracts.md; P15/P21. |
| Inputs | Qualified cohorts, net production need, supply and terminal state. |
| Outputs | Expanded KPI catalog. |
| Constraints | New zero-denominator/average-demand windows are not inherited silently. |
| Source | D08; P15/P21 |
| Status | Pending |
| Test Reference | T-KPI-002 — see test catalog |

## BR-KPI-004

| Field | Definition |
|---|---|
| Rule ID | BR-KPI-004 |
| Domain | KPI |
| Rule | Risk flags are rule-based exposure, not validated probabilities or proven causes. |
| Formula | Numeric measurements separate from threshold classification. |
| Inputs | Workload utilization, stock, obligations and approved thresholds. |
| Outputs | Exposure flags and Alert Burden Index. |
| Constraints | P10 capacity thresholds; P21 counting/weights; no default recalibration. |
| Source | D08 |
| Status | Approved |
| Test Reference | T-KPI-003 — see test catalog |

## BR-UI-001

| Field | Definition |
|---|---|
| Rule ID | BR-UI-001 |
| Domain | Dashboard |
| Rule | Target exactly the approved five-page structure; views consume backend metrics and published runs. |
| Formula | Executive Overview; Demand Analysis; Capacity Monitoring; Inventory & Service Risk; Scenario Planning. |
| Inputs | Published run views. |
| Outputs | Five-page logical navigation. |
| Constraints | Placement/consolidation P20; no numerical rule duplication in DAX/UI. |
| Source | D09; mapping details pending |
| Status | Approved |
| Test Reference | T-UI-001 — see test catalog |

## BR-PIPE-001

| Field | Definition |
|---|---|
| Rule ID | BR-PIPE-001 |
| Domain | Pipeline |
| Rule | Use a unified raw-to-dashboard workflow with stage-level quality gates and reproducible dependencies. |
| Formula | Prepare -> validate -> simulate -> independently validate -> KPI -> reconcile -> publish. |
| Inputs | Raw sources, assumptions, run/scenario config. |
| Outputs | Stage statuses and versioned artifacts. |
| Constraints | No ingestion download or installation hidden inside a numerical engine. |
| Source | D10 |
| Status | Approved |
| Test Reference | T-PIPE-001 — see test catalog |

## BR-PIPE-002

| Field | Definition |
|---|---|
| Rule ID | BR-PIPE-002 |
| Domain | Pipeline |
| Rule | Every run is uniquely identified and records source hashes, assumption versions and scenario parameters. |
| Formula | Run_ID + Schema_Version + manifest referenced by each artifact. |
| Inputs | Inputs, environment identity and parameters. |
| Outputs | Run_Manifest with execution/validation/publication status. |
| Constraints | Unique run identity does not mean deterministic ID; equivalent inputs must reproduce semantic results. |
| Source | D10 |
| Status | Approved |
| Test Reference | T-PIPE-002 — see test catalog |

## BR-PIPE-003

| Field | Definition |
|---|---|
| Rule ID | BR-PIPE-003 |
| Domain | Pipeline |
| Rule | An incomplete or failed run cannot be published as successful or replace a valid published run. |
| Formula | Publish only if all required stages complete and all blocking checks pass. |
| Inputs | Manifest, artifact hashes and validation results. |
| Outputs | Immutable published run selection. |
| Constraints | Isolated staging directories; atomic promotion/pointer mechanism is a proposed technical design. |
| Source | D10 |
| Status | Approved |
| Test Reference | T-PIPE-003 — see test catalog |
