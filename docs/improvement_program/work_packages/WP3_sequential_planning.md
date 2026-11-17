# WP3 Sequential Multiweek Planning

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Run an isolated state-conserving trajectory per scenario, with explicit shortage mode and workload-constrained same-week production.

## 2 Scope

Chronological inventory/backlog transitions; external event recognition; internal production allocation; current/backlog fulfillment attribution; LOST_SALES and CARRY_FORWARD; initial-state and sparse-calendar handling; independent transition checks.

## 3 Out of scope

No configurable multiweek production lead time, procurement optimization, cross-plant routing/transfer, unapproved backlog age override, unknown-demand zero filling or inferred external receipts.

## 4 Business rules

BR-INV-001, BR-INV-002, BR-INV-003, BR-INV-004, BR-PROD-001, BR-ALLOC-002, BR-ALLOC-003, BR-ALLOC-004, BR-BKL-001, BR-BKL-002, BR-BKL-003, BR-BKL-004, BR-SCN-001, BR-SCN-003, BR-CAP-001, BR-CAP-002.

## 5 Input data

Validated DC03–DC10; explicit backlog/fulfillment/quantity/production-target policies; declared initial stock/backlog and complete approved demand coverage for the simulated calendar.

## 6 Output data

DC11 allocation_result_route_b; DC12 inventory_state_weekly and conditional backlog cohorts; unique pool balances; structured independent validation results.

## 7 Data model

Separate current-demand flow, opening/closing stock, opening/closing backlog, fulfilled-current/fulfilled-backlog, lost sales, external receipts and internal production. Workload capacity stays at pool grain.

## 8 Module dependencies

WP2 approved workload/demand inputs; WP1 independent gate/report; minimal WP5 run identity contracts. State functions do not import managers; sequential orchestrator composes group engine and state transition and validates independently.

## 9 Actual repository files affected

src/allocation_engine.py versioned interface; src/allocation_manager.py legacy compatibility; src/scenario_generator.py versioned definitions; src/planning_snapshot.py Route B bundle; src/allocation_validator.py Route B extension; tests/test_allocation_engine.py; tests/test_scenario_generator.py.

## 10 New files proposed

src/inventory_engine.py; src/sequential_planner.py; src/inventory_validator.py; tests/test_sequential_planning.py. Conditional cohort table only when approved age semantics require it.

## 11 Testing plan

T-SEQ-001/002/003/004/005; T-BKL-001/002/003/004; T-RCP-001; T-ALLOC-001/002; T-SCN-001; T-REG-001. Hand-calculated multiweek shortages, later receipts, recovery, zero capacity, surplus stock, no-demand known weeks, missing/unknown coverage and isolated scenario runs.

## 12 Acceptance criteria

Every week balances quantity and workload; carry mode ending backlog becomes next beginning backlog; lost mode losses never carry as backlog; production usable same week and debits workload once; external receipts cannot appear early; scenarios do not share state; no later-week historical inventory resets.

## 13 Risks

Overwriting Scenario_Demand with backlog-inclusive obligations destroys provenance. Replaying legacy replenishment and opening stock double counts supply. Missing sparse observations cannot safely be treated as zeros.

## 14 Pending decisions

P06–P09/P13/P14/P16/P18/P19/P22/P23, plus approved WP2 inputs. No real sequential trajectory sign-off without the relevant policy choices.

## 15 Implementation complexity

High

## Period execution contract

1. Establish scenario initial state from DC07 once; validate policy and coverage.
2. Select the declared week, plant pool, effective factors and receipt events. Receipt availability follows P22; never before its period.
3. Keep Beginning_Backlog and current Scenario_Qualified_Demand separate. Apply approved P07/P08 cohort order and P14 uncovered-requirement definition.
4. Allocate Required_Production_Qty under common workload capacity and approved quantity step; retain authoritative Allocation_Order.
5. Recognize Internal_Production_Qty as same-week supply. Attribute actual fulfillment to current demand and opening backlog.
6. Compute ending stock and policy-specific ending backlog/losses; independently validate conservation.
7. Carry state to the next declared week. Report terminal inventory and terminal backlog separately from cumulative flows.

The general conservation formulas are approved in the registry. The exact use of inventory/receipts to prioritize old versus current demand, any stock-build target and secondary ranking key remain Pending. Do not implement the ordered list by choosing those rules implicitly.

Legacy allocation APIs remain explicitly independent-week. Route B group allocation receives a separate requirement quantity and factor; remaining workload divided by factor bounds feasible quantity. Never subtract raw units directly from workload.

For sparse histories, state-only rows require an explicit known-zero/coverage record. Unknown demand blocks the affected trajectory. Preserve the original sparse demand facts; separate state ledger coverage is the concrete need for additional state rows, not approval of a dense demand grid.
