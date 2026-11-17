# Pending Decision Register

Original Route B version 1.0 • 2026-11-17 • Active revised-scope resolutions are identified below; other entries remain pending or deferred.

> Revised three-day scope: P02 retains Order Date and P05 now explicitly excludes plant-specific factors. P08 older-backlog-before-current is supplied by the latest owner instruction. Broad future KPI/page/age-policy questions are not automatically blockers for the reduced executable slice; real-source whitelist/opening supply and cross-product override choices remain explicit. The synthetic fixture resolves none of those production-data choices.

D01–D11 are approved. A recommendation in this register is not an approved business rule. No elapsed time, lack of reply or implementation authorization alone approves a proposed value. Exact rule IDs are linked through the [registry](02_business_rules.md).

P02 does not reopen the approved Order Date basis by default; it records retained basis and outstanding calendar/as-of detail. P05 future plant factors do not authorize alternate routing. Documentation can complete while these items remain pending.

## P01 Qualified Demand whitelist

- Status: RESOLVED for the optional DATACO_REFERENCE demonstration by the owner's revised data strategy.
- Approved profile: COMPLETE, CLOSED and PROCESSING qualify. CANCELED and SUSPECTED_FRAUD are forced excluded. Other statuses remain excluded unless explicitly configured.
- Scope: USER_DATA defines its own status mapping. Unknown status defaults to error unless the caller explicitly chooses EXCLUDE. DataCo spellings are not universal engine rules.
- Evidence/configuration: examples/planning/dataco_reference/config.json; core CSV contract in docs/planning_csv_inputs.md.
- No temporary blanket non-canceled qualification rule is used.

## P02 Historical demand date basis

- Status: retained Order Date basis APPROVED; any future alternate-date/as-of conventions remain separately pending under P12. The reduced adapter keeps Sunday labels and blocks partial source edge weeks.
- Why it matters: D02 already retains Order Date; timezone, cutoff and partial-week interpretation still need confirmation.
- Available options: Keep order date (current direction); alternative date only through a separately approved change.
- Recommendation for review: Retain order date (DateOrders) and existing Sunday-ending labels; confirm cutoff/timezone and boundary-week reporting with P12.
- Affected modules: WP2 preparation; planning_pipeline; WP5 manifest.
- Can implementation proceed without this decision? Date parsing/contracts may proceed; no new date basis may be substituted.
- Is a temporary assumption safe? Existing date basis is approved; partial-week/as-of conventions are not.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P03 Workload factor values and methodology

- Status: PENDING.
- Why it matters: No manufacturing standard hours exist in current factors or capacity CSVs.
- Available options: Measured times; SME estimates; explicitly synthetic product-family assumptions.
- Recommendation for review: Use owner-reviewed synthetic factors with reference equivalent unit, positive values, evidence and immutable version until actual standards exist.
- Affected modules: WP2 workload model; WP3 engine; validators.
- Can implementation proceed without this decision? Schema and symbolic tests yes; real workload calculations/publication no.
- Is a temporary assumption safe? Unit factors or arbitrary family factors are not safe hidden defaults.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P04 Equivalent workload capacity baseline

- Status: PENDING.
- Why it matters: Old 1165/1083/913 values are quantity units and cannot simply be renamed.
- Available options: Independent plant workload capacity; or explicitly synthetic capacity calibrated from qualified workload over an approved window.
- Recommendation for review: Agree capacity unit, calendar, calibration population/window, target utilization and rounding; record recipe and source hashes.
- Affected modules: WP2 capacity baseline; WP3 allocation; WP4 utilization; WP5 manifest.
- Can implementation proceed without this decision? Calibration framework yes; published baseline/stress evaluation no.
- Is a temporary assumption safe? Do not reuse 0.75 or legacy capacity as an approved new baseline.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P05 Plant-specific workload factors

- Status: RESOLVED for revised scope: product-only factors; plant-specific factors explicitly excluded by owner section 1.4. Broader future options below are retained as history, not active implementation permission.
- Why it matters: D03 supports future Plant x Product factors but does not choose initial scope.
- Available options: Global product factors; explicit plant-product factors.
- Recommendation for review: Start global product factors unless credible plant differences exist; retain nullable plant scope in factor contract; no implicit fallback precedence.
- Affected modules: WP2 factors; snapshot joins; allocation.
- Can implementation proceed without this decision? Schema extension point yes; factor resolution in real runs awaits scope approval.
- Is a temporary assumption safe? No mixed global/plant fallback without explicit resolution rule.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P06 External procurement schedule/source

- Status: PENDING.
- Why it matters: Legacy periodic replenishment is modeled, not an actual dated procurement feed.
- Available options: Explicit imported receipts; approved synthetic schedule; explicitly empty external-supply scenario.
- Recommendation for review: Use an owner-approved versioned event schedule; label synthetic and do not auto-copy legacy replenishment.
- Affected modules: WP3 receipts/state; WP5 input loading; validators.
- Can implementation proceed without this decision? Event schema and receipt timing tests yes; real runs need a declared schedule, including explicitly empty if chosen.
- Is a temporary assumption safe? An absent file is not zero receipts.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P07 Backlog priority across products

- Status: PENDING.
- Why it matters: Age or service class could override the existing product ranking.
- Available options: Existing priority first with age within product; global oldest-first; explicit weighted policy.
- Recommendation for review: Preserve product priority unless the owner approves an age override; keep any cohort ordering explicit.
- Affected modules: WP3 group requirement builder/allocator; validator; WP4 trade-offs.
- Can implementation proceed without this decision? Legacy rank validation yes; CARRY_FORWARD business execution no.
- Is a temporary assumption safe? No implicit age override or invented weight.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P08 Older backlog versus current demand

- Status: RESOLVED for the revised implementation scope.
- Approved rule: in CARRY_FORWARD, fulfill older backlog before current-week demand. LOST_SALES does not carry unmet current demand.
- Source: owner's “Planning Logic Upgrade — Revised Scope & Data Inspection Requirements,” Target Business Capabilities 4.
- Implemented consequence: separate Fulfilled_Backlog_Qty and Fulfilled_Current_Qty; prior obligations consume each product's available supply first. Opening-origin versus horizon-origin backlog is tracked for honest horizon fulfillment.
- Cross-product allocation is a different question under P07/P14: current supported explicit caller policy retains existing product priority and net-unit ordering; a global age override was not silently added.
- Temporary assumptions: no oldest-current inversion is permitted. Detailed age-based cross-product ranking and cancellation/expiry remain outside the reduced slice.

## P09 Opening inventory and backlog

- Status: RESOLVED method for the DataCo demo: a separate explicitly synthetic planning initialization; historical synthetic replenishment is not replayed.
- Current versioned example uses declared zero opening inventory, zero opening backlog and no external receipts. These are synthetic demonstration inputs, not reconstructed historical facts or defaults for other users.
- USER_DATA must supply initial inventory, or explicitly configure a ZERO assumption. Opening backlog is supplied separately/in initial state, or explicitly declared ZERO. Optional Week must match the first planning bucket.
- Source/as-of choices for a user's actual operational stock remain that user's explicit input responsibility; no missing balance becomes zero.
- Contract and provenance: docs/planning_csv_inputs.md and examples/planning/dataco_reference/README.md.

## P10 Capacity risk thresholds

- Status: PENDING.
- Why it matters: Old 85/95% workload proxies and 100% production rules are different semantics.
- Available options: Retain separately labeled legacy thresholds; approve new workload thresholds; only objective shortage/full-pool flags.
- Recommendation for review: Publish measured load/shortage and retain legacy statuses separately until workload thresholds are approved.
- Affected modules: WP4 evaluator and bottleneck view; WP6 demo.
- Can implementation proceed without this decision? Numerical utilization and remaining-load metrics yes; new categorical thresholds no.
- Is a temporary assumption safe? Do not transfer 85/95 or legacy Healthy rules silently.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P11 Final stress parameters

- Status: PENDING.
- Why it matters: New units, receipts and initial stock determine whether 10%/20% reveals scarcity.
- Available options: Candidate +10%/-20%; another justified shock; sensitivity range.
- Recommendation for review: Validate candidates after approved workload calibration; record unchanged baseline and explain any scenario adjustment.
- Affected modules: WP6 scenario definitions and presentation.
- Can implementation proceed without this decision? Generic combined scenario support yes; final demonstration sign-off no.
- Is a temporary assumption safe? Candidate values can be identified as candidates, never as frozen approved parameters.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P12 Retrospective versus future planning

- Status: PENDING.
- Why it matters: Current ABC/capacity/inventory use full-history information.
- Available options: Explicit retrospective replay; as-of historical backtest; future planning with approved forecasts.
- Recommendation for review: Use clearly labeled retrospective replay initially unless owner requires an as-of backtest; never call historical quantities a future forecast.
- Affected modules: WP2 calibrations; WP3 opening state; WP5 manifest; WP6 claims.
- Can implementation proceed without this decision? Architecture/schema work yes; real calibration window and claims await scope.
- Is a temporary assumption safe? No future-information leakage hidden under an as-of label.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P13 Quantity divisibility and precision

- Status: PENDING for operational values. The implemented interface requires explicit quantity_step (0=continuous; positive=unit/pack step); the synthetic fixture explicitly uses continuous units, not an approved manufacturing default.
- Why it matters: Workload division and percentage shocks yield fractional finished goods.
- Available options: Continuous quantities; integer units; approved pack sizes.
- Recommendation for review: Confirm per-product quantity unit/step and workload precision; define rounding sequence/residual handling and numeric tolerance.
- Affected modules: WP2 factors/demand transforms; WP3 allocator; WP1 tolerance policy.
- Can implementation proceed without this decision? Symbolic equations and generic precision hooks yes; real rounding default no.
- Is a temporary assumption safe? No rounding to integer or treating all goods as divisible without approval.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P14 Route B net requirement and secondary rank

- Status: PENDING.
- Why it matters: Legacy Net_Demand excludes receipts/backlog; workload weighting changes feasible allocation.
- Available options: Rank by backlog-inclusive uncovered units; current-demand uncovered units; uncovered workload.
- Recommendation for review: Preserve priority and product-ID tie-break; propose uncovered obligation units as secondary key; require approval of exact construction.
- Affected modules: WP3 requirement builder and allocator; independent validator.
- Can implementation proceed without this decision? Legacy validator may proceed; Route B allocation policy remains gated.
- Is a temporary assumption safe? Do not reuse Scenario_Demand for backlog-inclusive demand or rank by workload silently.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P15 KPI definitions and denominators

- Status: PENDING.
- Why it matters: D08 names KPIs but does not settle cohort fulfillment, repeated backlog counting, zero ratios, DOI basis or safety stock units.
- Available options: Current-cohort fill plus terminal backlog separately; total-obligation fulfillment; explicit alternative KPI names.
- Recommendation for review: Approve the proposed catalog in 04, including separate current fulfillment and terminal stock measures; no sum of repeated backlog balances.
- Affected modules: WP4 KPI/evaluator; WP3 cohort outputs; WP1 metric checks.
- Can implementation proceed without this decision? Column contracts and proposed formulas yes; publishing undecided rates/statuses no.
- Is a temporary assumption safe? Legacy zero-denominator rules apply only to legacy fields.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P16 Sparse demand and simulation calendar

- Status: PENDING.
- Why it matters: No observed row does not mean zero; state must survive weeks without demand rows.
- Available options: Explicit completeness coverage with known-zero calendar; explicit unknown demand blocking; owner-defined restricted active horizon.
- Recommendation for review: Keep sparse demand facts; add a separate coverage/calendar contract and state ledger for initialized items, not a fabricated dense demand grid.
- Affected modules: WP2 coverage; WP3 calendar/state; WP4 capacity calendar; WP5 validation.
- Can implementation proceed without this decision? Schema and gap rejection yes; unknown weeks cannot be simulated as zeros.
- Is a temporary assumption safe? Carrying stock is safe only with explicit demand completeness; missing input is not zero.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P17 ABC priority basis

- Status: PENDING.
- Why it matters: Recomputing ABC on qualified demand/workload could change approved product priorities.
- Available options: Preserve versioned legacy ABC; recompute from qualified quantity; separate strategic priority input.
- Recommendation for review: Retain existing A/B/C-to-3/2/1 mapping and freeze input ABC version initially; owner decides recalibration population/window.
- Affected modules: WP2 classification; WP3 ranking; WP6 trade-offs.
- Can implementation proceed without this decision? Mapping validation yes; reclassification no.
- Is a temporary assumption safe? No automatic switch to workload or qualified-demand ranking.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P18 Production target and inventory build

- Status: PENDING.
- Why it matters: D07 permits same-week supply but does not authorize stock-building quantities.
- Available options: Produce only uncovered obligations; replenish to approved target; additional declared production requirements.
- Recommendation for review: Propose only uncovered obligations initially; safety-stock production requires explicit new target policy.
- Affected modules: WP3 production requirement; WP4 coverage and stock.
- Can implementation proceed without this decision? Legacy allocation unchanged; Route B build-to-stock behavior gated.
- Is a temporary assumption safe? Do not add target-stock demand silently.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P19 Scenario demand and receipt transformations

- Status: PENDING.
- Why it matters: Surging demand must preserve gross/qualified/excluded lineage; receipts may or may not change by scenario.
- Available options: Scale qualified demand and derive scenario gross with unchanged excluded; scale all streams consistently; explicit scenario incremental orders.
- Recommendation for review: Propose scale qualified current demand, keep historical measures immutable and expose incremental scenario demand separately; explicitly state receipts unchanged unless configured.
- Affected modules: WP2 provenance; scenario_generator; WP3 receipts; WP6 combined stress.
- Can implementation proceed without this decision? Generic scenario metadata yes; no unstated scaling scope.
- Is a temporary assumption safe? Never overwrite historical Gross/Qualified/Excluded values to present synthetic shocks as actual orders.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P20 Five-page mapping across Power BI and Streamlit

- Status: PENDING.
- Why it matters: Owner target five pages differs from actual five monitoring PBIX pages and three Streamlit scenario tabs.
- Available options: Five PBIX pages with scenario page linking/routing to Streamlit; five unified Streamlit views with frozen PBIX; coordinated five-page navigation.
- Recommendation for review: Owner approve an explicit mapping retaining existing investigation capabilities and reusing scenario subviews; no automatic eight-page expansion.
- Affected modules: WP4 PBIX/Streamlit/navigation acceptance.
- Can implementation proceed without this decision? Backend metrics and page contracts yes; dashboard migration no.
- Is a temporary assumption safe? Target five names are approved; deployment location and page consolidation are not.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P21 Alert Burden Index and exposure counting

- Status: PENDING.
- Why it matters: Legacy score sums plant and product alerts and overlaps service exposure.
- Available options: Explicit event-grain counts by domain; approved weighted composite; display components without a single total.
- Recommendation for review: Propose disaggregated counts with a documented optional additive burden index; define overlap, weights and observation windows.
- Affected modules: WP4 risk preparation/KPI/evaluator.
- Can implementation proceed without this decision? Raw event contracts yes; aggregate index/status decisions pending.
- Is a temporary assumption safe? Do not rename legacy Executive_Risk_Score as a newly validated risk metric.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P22 Receipt availability within declared week

- Status: PENDING.
- Why it matters: D06 states receipt period but not start/end-of-week availability for fulfillment.
- Available options: Beginning-of-week receipts available same week; end-of-week receipts available next week; explicit within-week cutoff.
- Recommendation for review: Propose beginning-of-week availability for an explicitly bucketed receipt feed; owner must approve attribution and reporting.
- Affected modules: WP3 state/fulfillment; WP4 receipt KPIs; WP1 continuity checks.
- Can implementation proceed without this decision? No-early-arrival checks yes; fulfillment availability timing awaits choice.
- Is a temporary assumption safe? Receipt cannot be consumed before its declared period under any option.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.

## P23 Horizon boundaries and cohort persistence

- Status: PENDING.
- Why it matters: Initial backlog age, product starts/exits and terminal carryover affect conservation and service measurement.
- Available options: Explicit opening backlog cohorts; aggregate opening backlog with limited age claims; owner-approved zero-opening case.
- Recommendation for review: Require declared initial cohorts or an explicit aggregate-only limitation; report terminal inventory/backlog without pretending terminal backlog is lost sales.
- Affected modules: WP3 state and optional backlog ledger; WP4 terminal KPIs; WP6 demo.
- Can implementation proceed without this decision? Schema/basic conservation yes; age/cohort comparisons require approved input scope.
- Is a temporary assumption safe? No unrecorded reset at horizon boundaries.
- Resolution: owner, selected option, exact values, effective rule/assumption version and approval reference must be recorded here before dependent business behavior is enabled.
