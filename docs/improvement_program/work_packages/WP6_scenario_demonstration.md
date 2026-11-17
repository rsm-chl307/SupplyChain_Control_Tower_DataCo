# WP6 Combined Stress Demonstration

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Demonstrate explainable effects of demand and capacity shocks with four independent sequential scenarios using the approved workload baseline.

## 2 Scope

Baseline, Demand Surge, Capacity Disruption and Combined Stress; parameter provenance; same starting conditions except declared treatments; sequential state; bottleneck/shortage/priority/inventory/backlog/fulfillment comparison and presentation.

## 3 Out of scope

No arbitrary baseline manipulation, unapproved factor or demand policy, optimized mitigation, AI narrative or new business allocation heuristic.

## 4 Business rules

BR-SCN-001, BR-SCN-002, BR-CAP-001, BR-CAP-002, BR-INV-001, BR-INV-002, BR-BKL-001, BR-BKL-002, BR-BKL-003, BR-KPI-002, BR-KPI-003, BR-UI-001, BR-PIPE-003.

## 5 Input data

Validated published WP2–5 inputs/output contracts, owner-approved stress parameters/scope, explicit policy and identical declared initialization within each comparison family.

## 6 Output data

Versioned four-scenario definitions; complete published run; plant-week and priority/cohort comparisons; concise demonstration narrative and limitations with exact run references.

## 7 Data model

DC09 four scenarios, DC10 treated demand, DC05 independent capacity treatment and DC11/12 trajectories. Policy comparisons use matched Baselines; do not compare mixed policies as one treatment.

## 8 Module dependencies

All earlier stage acceptance; P11 after workload/capacity calibration; P19 shock composition; P20 presentation; same-run WP5 publication.

## 9 Actual repository files affected

src/scenario_generator.py combined parameter contract; tests/test_scenario_generator.py; dashboard/scenario_planning_app.py and PBIX only within approved WP4 mapping. Existing canonical data/scenario outputs remain unchanged.

## 10 New files proposed

tests/test_scenario_demonstration.py; future isolated scenario configuration and demonstration note under approved permanent docs, not canonical baseline rewrites.

## 11 Testing plan

T-SCN-001/002; T-PIPE-003; T-UI-001; all numerical invariants. Include a hand-computable synthetic case distinctly labeled as a test fixture and a provenance-backed project demonstration.

## 12 Acceptance criteria

Four scenarios execute independently and reconcile; combined case composes precisely approved demand/capacity treatments; explain affected plant-weeks/products/priority classes and state evolution; no claim of bottlenecks when outputs show none; canonical baseline unchanged.

## 13 Risks

Candidate +10%/-20% may not create meaningful constraints after recalibration. Backlog sequencing can redistribute current service; compare identical policies and attribute effects cautiously.

## 14 Pending decisions

P11/P19 plus all required upstream policies; if no shortages occur, report that honestly and seek approval for a revised shock or separately labeled constrained fixture.

## 15 Implementation complexity

Medium

## Demonstration method

Begin with candidate +10% demand and -20% selected capacity only as candidates. Establish the new workload baseline first, then evaluate owner-reviewed ranges against plausible scenario scope. Freeze chosen parameters and factors in the manifest; never lower canonical stock/capacity or alter status eligibility just to create a chart.

Explain separately: where workload exceeds available pools, which products lose production under the approved order, how opening stock/receipts protect fulfillment, whether current demand or old backlog gets service, when shortage persists/recoveries occur, and terminal stock/backlog versus cumulative losses.

Support both shortage modes in acceptance fixtures. A real presentation can use an owner-selected mode with policy stated. If comparing both modes, use four scenarios per policy family with its own matched Baseline; do not silently turn four specified scenario kinds into a misleading mixed-policy ranking.

Do not require a mathematically unsupported monotonicity claim: allocation mix and cohort service can shift under priority rules. Validate exact conservation and explain actual trade-offs. A demonstration without shortage is valid evidence of that parameter set, but it does not satisfy an unqualified claim that priority trade-offs were observed.
