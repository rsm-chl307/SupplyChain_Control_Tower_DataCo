# WP1 Independent Validation Layer

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Independently establish correctness of legacy outputs and future Route B contracts, including structured evidence instead of “engine ran successfully.”

## 2 Scope

Schema/key/reference/finiteness/source checks; independent legacy arithmetic, greedy order and pool checks; version-aware report contracts. Define sequential conservation checks now and complete them with WP3, not before its policy inputs exist.

## 3 Out of scope

No demand whitelist, workload values, sequential engine, dataset repair, new business threshold or production formula shared as the oracle.

## 4 Business rules

BR-VAL-001, BR-VAL-002, BR-VAL-003, BR-ALLOC-001, BR-ALLOC-004; future extensions BR-INV-001, BR-INV-002, BR-BKL-001, BR-BKL-002, BR-BKL-003, BR-CAP-002.

## 5 Input data

Legacy exact-schema source/result DataFrames; authoritative dimensions/mapping; declared schema and rule versions. Later: Route B requirements/factors/pools/opening state/events/policies.

## 6 Output data

DC13 validation_findings/summary; independent pass/fail/error outcome. Existing exception behavior remains supported through an explicit compatibility boundary.

## 7 Data model

DC13; DC02/DC03/DC05/DC11/DC12 key checks; contracts independent of the generator. Rule IDs and canonical row keys in each finding.

## 8 Module dependencies

Shared contracts/report types are leaves. Validators may use standard numeric/date utilities but cannot import allocation/state/scenario engines or production arithmetic helpers as their expected-result source.

## 9 Actual repository files affected

src/allocation_validator.py; src/planning_snapshot.py (validation boundaries only); tests/test_allocation_engine.py. Inspect src/scenario_generator.py contract constants; do not change business scenario behavior.

## 10 New files proposed

src/data_contracts.py; src/validation_report.py; tests/test_independent_validation.py. src/inventory_validator.py may start as a contract proposal but executable continuity behavior belongs to the WP3-authorized extension.

## 11 Testing plan

T-VAL-001/002/003; T-REG-001. Inject false net demand, forged key duplicates, priority inversion, under-allocation with slack, swapped source fields, duplicate order numbers, infinity/NaN, invalid factor/reference and missing-policy states. Test report determinism and input immutability.

## 12 Acceptance criteria

Every existing frozen allocation invariant has an independent check; all corruption probes fail for the intended reason; normal/constrained/zero/inventory-covered cases pass; no engine self-oracle; policy-dependent checks are NOT_EVALUATED/BLOCKED rather than fake PASS.

## 13 Risks

Exact-column legacy schemas can break if new fields are appended indiscriminately. Avoid dependency cycles and validation logic that just reuses the engine.

## 14 Pending decisions

P13 numeric precision/tolerance for Route B; P07/P08/P14/P16 for full sequential order/state checks. These do not block legacy validation foundation.

## 15 Implementation complexity

Medium

## Validation design details

Check order: schema -> type/finiteness -> canonical identity -> authoritative references -> immutable source equality -> independent arithmetic/order -> pool totals -> sequential state (when available) -> structured summary.

Legacy expected quantities are recomputed from original scenario demand/opening stock. Expected order is independently derived from approved priority/net requirement/product ID, with unique contiguous integer order. Expected allocation is checked from prior expected capacity, not the candidate Remaining_Capacity column. Compare all preserved columns by key, not only set equality of supplied strings.

For Route B, independently reconstruct Required_Production_Qty and the secondary ranking measure from authoritative state, current demand, receipt events and approved P14/P18 policies; do not trust a requirement calculated by sequential_planner as an expected input. Until those policies are approved the check is BLOCKED.

For Route B, validate quantity and workload as different dimensions. State verification starts from declared initial state and independently reconciles each chronological week, raw receipt recognition and cohort totals. It must not call inventory_engine transition.

A blocking input failure prevents dependent expected-result checks; the report must identify which checks were not evaluated. Findings cannot silently repair or normalize ambiguous business data. Parsing/normalization rules require declared contract behavior.
