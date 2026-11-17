# Testing and Acceptance Standards

Version 1.0 • Planned tests unless explicitly marked current inspection • No implementation authorized.

## Independent validation requirements

Expected values come from hand-calculated fixtures, independently written algebra and authoritative input comparisons. Do not rerun allocate_capacity, scenario_generator or inventory_engine to manufacture the expected result. Shared type/schema descriptors are allowed; calculation helpers from the code being tested are not independent oracles.

Every major calculation covers normal, constrained, zero capacity, zero demand, inventory-covered demand, deterministic repeatability and input immutability. Multiweek cases additionally exercise receipt timing, opening/terminal states, backlog policy/cohort competition, sparse unknown weeks and scenario isolation.

Fixture factors/status mappings are explicitly synthetic test assumptions, not approved project business defaults. Pending policy tests are contract requirements marked BLOCKED/NOT_EVALUATED until the owner resolves them; no “passed” placeholder test.

Numeric tolerance and quantity rounding are resolved under P13. Tests cannot pick a hidden tolerance that changes discrete production decisions. Verify independent physical balances at the approved precision.

## Traceable test catalog

### T-VAL-001 Independent oracle

- Requirement/result: Mutate net demand, allocation order, greedy quantities and remaining load while preserving candidate arithmetic; validator rejects each and never imports/calls the production engine as oracle.
- Proposed location and ownership: tests/test_independent_validation.py; WP1.
- Status: PLANNED, not implemented or executed by this specification task.

### T-VAL-002 Identity/types/references

- Requirement/result: NaN, positive/negative infinity, numeric-looking strings under declared parsing policy, forged key duplicate, invalid date/master/plant, zero/negative/overlapping factors fail with intended check.
- Proposed location and ownership: tests/test_independent_validation.py; tests/test_demand_capacity.py; WP1/2.
- Status: PLANNED, not implemented or executed by this specification task.

### T-VAL-003 Source/report integrity

- Requirement/result: Swap source fields, drop/add source IDs, edit status/reason, skip a required check; keyed preservation detects it; report order/Rule_ID/NOT_EVALUATED status deterministic and inputs unchanged.
- Proposed location and ownership: tests/test_independent_validation.py; WP1.
- Status: PLANNED, not implemented or executed by this specification task.

### T-DMD-001 Dual-demand reconciliation

- Requirement/result: Known synthetic approved mapping partitions quantities exactly at item/product/plant/week/run grain; original raw quantities unchanged; duplicate join rejected.
- Proposed location and ownership: tests/test_demand_capacity.py; WP2.
- Status: PLANNED, not implemented or executed by this specification task.

### T-DMD-002 Eligibility negative cases

- Requirement/result: Unknown/missing status mapping, duplicate or overlapping map and excluded reason missing do not create silently qualified demand; all-excluded and zero-quantity cases explicit.
- Proposed location and ownership: tests/test_demand_capacity.py; WP2.
- Status: PLANNED, not implemented or executed by this specification task.

### T-DMD-003 Historical dates

- Requirement/result: Order Date retained, Sunday labels verified, invalid date rejected, exact as-of/cutoff/partial-week behavior matches resolved P02/P12 rather than silently clipping.
- Proposed location and ownership: tests/test_demand_capacity.py; WP2.
- Status: PLANNED, not implemented or executed by this specification task.

### T-CAP-001 Factor conversion

- Requirement/result: Two synthetic products with unequal positive factors consume different workload per quantity; effective date/scope resolution unique and provenance kept; old capacity not treated as same unit.
- Proposed location and ownership: tests/test_demand_capacity.py; WP2/3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-CAP-002 Pool uniqueness

- Requirement/result: Many product rows reference one pool counted once; missing/duplicate pool, incompatible unit and over-allocation rejected; zero pool and constrained residual cases correct.
- Proposed location and ownership: tests/test_demand_capacity.py; tests/test_sequential_planning.py; WP2/3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-CAP-003 Calibration reproducibility

- Requirement/result: Approved recipe/window/availability calendar reproduces workload baseline; changed factor or window changes declared version/hash; no unapproved 0.75 assumption.
- Proposed location and ownership: tests/test_demand_capacity.py; WP2.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SEQ-001 Inventory continuity

- Requirement/result: At least three weeks: prior ending stock equals next opening stock, including approved known-zero state-only week; changed later legacy snapshot cannot reset state.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SEQ-002 Conservation

- Requirement/result: Independent hand balances beginning stock + receipt + production = current/backlog fulfillment + ending stock for every period; no negative/excess fulfillment or double receipt.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SEQ-003 Opening/terminal state

- Requirement/result: Missing initialization rejected; valid zero explicitly declared; nonzero opening backlog in loss mode not discarded; terminal stock/backlog visible; late product start follows P09/P23.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SEQ-004 Same-week production

- Requirement/result: Insufficient opening stock can be fulfilled by current-week allocated production; workload debited once and production counted once; no configurable multiweek offset.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SEQ-005 Sparse calendar

- Requirement/result: Observed sparse demand preserved; known-zero state ledger permitted only with evidence; UNKNOWN gap blocks trajectory; capacity pools available under approved calendar even with no demand fact.
- Proposed location and ownership: tests/test_demand_capacity.py; tests/test_sequential_planning.py; WP2/3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-BKL-001 Explicit mode

- Requirement/result: Missing/unsupported/changing shortage mode rejected; scenario manifest records mode; zero demand and zero stock cases explicit.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-BKL-002 Lost sales

- Requirement/result: Shortage becomes Lost_Sales_Qty and never next-week backlog; ending inventory still carries; opening/ending backlog zero.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-BKL-003 Carry forward

- Requirement/result: Week-one shortfall becomes next opening backlog and can later be fulfilled; Lost_Sales_Qty zero; aggregate obligations conserved; repeated backlog not counted as new demand.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-BKL-004 Cohort sequence

- Requirement/result: Opening/current demand competition and product priority/age conflicts follow resolved P07/P08/P14/P23; fulfillment attribution and terminal cohort totals match hand calculation; reject current fulfillment above current demand and backlog fulfillment above opening backlog, and require zero backlog fulfillment in LOST_SALES.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-RCP-001 External receipt timing

- Requirement/result: A later declared receipt is unavailable in earlier periods; no internal capacity debit; explicit empty schedule differs from missing schedule; within-week availability matches P22.
- Proposed location and ownership: tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-ALLOC-001 Workload-constrained allocation

- Requirement/result: Normal, constrained, zero capacity/demand, inventory-covered and two-factor cases satisfy approved requirement/quantity-step formula; unused residual justified; input unchanged.
- Proposed location and ownership: tests/test_allocation_engine.py; tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-ALLOC-002 Priority trade-off

- Requirement/result: Competing unequal factors/demands with ties follow explicit priority/secondary/product-ID ordering; lower priority cannot take load ahead of eligible higher rank; reason and sequence auditable.
- Proposed location and ownership: tests/test_allocation_engine.py; tests/test_sequential_planning.py; WP3.
- Status: PLANNED, not implemented or executed by this specification task.

### T-KPI-001 Grain/dimension

- Requirement/result: Sum workload pools once, ratio of sums, selected closing inventory/backlog rather than sum over time; incompatible units/runs rejected; flow totals reconcile.
- Proposed location and ownership: tests/test_performance_evaluation.py; WP4.
- Status: PLANNED, not implemented or executed by this specification task.

### T-KPI-002 Service/DOI boundaries

- Requirement/result: Current demand 100, opening stock 90, production 5 illustrates distinct production requirement coverage and current fulfillment; cohort/zero denominator/DOI policies exactly match P15. This is a test example, not an approved policy default.
- Proposed location and ownership: tests/test_performance_evaluation.py; WP4.
- Status: PLANNED, not implemented or executed by this specification task.

### T-KPI-003 Risk/burden

- Requirement/result: Threshold boundary, no missing-input fall-through to Healthy, explicit event grain/overlap and component totals; labels contain no probability/causal assertion.
- Proposed location and ownership: tests/test_performance_evaluation.py; WP4.
- Status: PLANNED, not implemented or executed by this specification task.

### T-UI-001 Backend/dashboard reconciliation

- Requirement/result: Same published Run_ID/schema/unit/hash set; ratio/stock and selected-week totals match backend; five approved pages/P20 mapping; active assumptions and allocation order visible; stale edited controls distinguish prior result.
- Proposed location and ownership: tests/test_dashboard_app.py plus authorized manual PBIX inspection; WP4/5.
- Status: PLANNED, not implemented or executed by this specification task.

### T-PIPE-001 Unified workflow

- Requirement/result: Authorized clean environment with declared dependencies and explicit raw inputs regenerates required artifacts without notebook manual state; stages validate before downstream use.
- Proposed location and ownership: tests/test_planning_pipeline.py; tests/test_run_planning.py; WP5.
- Status: PLANNED, not implemented or executed by this specification task.

### T-PIPE-002 Run reproducibility

- Requirement/result: Unique IDs for distinct executions; identical inputs/config produce equivalent semantic facts excluding IDs/timestamps; source/factor/parameter changes captured by hashes and assumptions.
- Proposed location and ownership: tests/test_run_management.py; tests/test_run_planning.py; WP5.
- Status: PLANNED, not implemented or executed by this specification task.

### T-PIPE-003 Failure/publication

- Requirement/result: Inject missing output, invalid hash, blocked check, stage crash and interrupted promotion; previous published run remains valid, failure manifest retained, partial run invisible as success.
- Proposed location and ownership: tests/test_run_management.py; WP5.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SCN-001 Scenario isolation

- Requirement/result: Run alone/together/reordered scenarios yield same per-scenario facts after removing run metadata; no shared state/receipt mutation; explicit initial-state references.
- Proposed location and ownership: tests/test_scenario_generator.py; tests/test_sequential_planning.py; WP3/6.
- Status: PLANNED, not implemented or executed by this specification task.

### T-SCN-002 Combined stress

- Requirement/result: Baseline/individual/combined treatments match P11/P19 exactly with one demand and one capacity application; four scenarios compare within matched mode; unchanged baseline hashes and independent fixture balances.
- Proposed location and ownership: tests/test_scenario_demonstration.py; WP6.
- Status: PLANNED, not implemented or executed by this specification task.

### T-REG-001 Legacy regression/protection

- Requirement/result: Retain legacy formulas/schema/order and approved artifact bytes. Before/after hashes, existing normal/constrained/zero/inventory-covered/deterministic cases and source-input immutability.
- Proposed location and ownership: Existing six test modules as appropriate; all stages.
- Status: PLANNED, not implemented or executed by this specification task.

## Stage acceptance and execution safety

A stage cannot pass if a mandatory check is not evaluated or a required business choice is missing. Reports include tested schema/rule/assumption versions, actual test command, pass/fail counts, protected-file checks and known limits. Never repeat a historical test claim as a fresh result.

Source/dataset/dependency/dashboard changes require stage-specific authorization. File-producing integration tests must write only into explicitly authorized isolated test directories; preserve baseline artifacts. During this task only non-mutating inspection and documentation checks are allowed. Python bytecode writing is disabled for read-only Python checks.

WP4 acceptance separates backend/helper tests from manual Power BI model/refresh checks. PBIX archive layout cannot prove live measures, relationships or refresh correctness. Missing authoring environment is recorded as unverified, not a fabricated pass.

## Documentation quality checks for this task

Check all local Markdown links; each WP's BR IDs and all registry test IDs; required 15 WP sections; P01–P12 plus added pending items; exact D01–D11 coverage; canonical dataset/column/unit definitions; formula and source/target version consistency; all stages unimplemented; all original source/tests/data/runtime/dashboard bytes unchanged.

The temporary completion report records actual results. This file specifies standards and future tests; it is not a log claiming future acceptance has occurred.
