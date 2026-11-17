# WP2 Demand and Equivalent Workload Capacity

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Create traceable gross/qualified/excluded demand and a dimensionally compatible product-workload/capacity model.

## 2 Scope

Pure source preparation; configurable owner-approved status mapping; line and aggregate reconciliation; product-factor provenance and effective scope; approved workload capacity recalibration; sparse coverage/input contracts.

## 3 Out of scope

No arbitrary whitelist/factors/target utilization, no automatic ABC reclassification, no sequential engine, no procurement optimization or alternate plant routing.

## 4 Business rules

BR-DMD-001, BR-DMD-002, BR-DMD-003, BR-DMD-004, BR-CAP-001, BR-CAP-002, BR-CAP-003, BR-VAL-002, BR-VAL-003; BR-SCN-003 coverage design.

## 5 Input data

Selected DataCo fields including Order Item Id, Order Status, order date (DateOrders), Product Card Id and Order Item Quantity; existing dimensions/mapping; owner-approved eligibility/factors/calibration/coverage/as-of assumptions.

## 6 Output data

DC01–DC06 and resolved factor references; Route B input assembly. New outputs use isolated future run directories; no overwriting master capacity_table.csv or old demand snapshots.

## 7 Data model

Eligibility ledger at source item grain; sparse weekly_demand at plant-product-week; factors with scope/effective version; capacity_pools at plant-week independently of product facts. See DC01–DC06.

## 8 Module dependencies

WP1 contracts/independent gates first; WP5 minimal Run_ID/assumption metadata contracts early. P01/P03/P04/P05/P12 determine real business outputs. Preparation remains pure, I/O belongs to pipeline.

## 9 Actual repository files affected

src/planning_snapshot.py; src/planning_pipeline.py source assembly; tests/test_scenario_generator.py compatibility references. notebooks/01_data_modeling.ipynb and notebooks/02_risk_metrics.ipynb are transformation evidence, not mandatory edit targets. data/master files remain read-only inputs.

## 10 New files proposed

src/demand_preparation.py; src/workload_model.py; tests/test_demand_capacity.py; future approved versioned eligibility/factor/capacity assumption inputs (paths decided at stage review, not current data/master overwrites).

## 11 Testing plan

T-DMD-001/002/003; T-CAP-001/002/003; T-SEQ-005 coverage contract; T-REG-001. Unknown status, all excluded, source duplicates, positive reconciliation, factor gap/overlap/zero/infinity, plant scope mismatch and unit mismatch cases.

## 12 Acceptance criteria

Source item quantities unchanged; gross=qualified+excluded at every declared aggregation; exclusions explainable; all eligible items resolve one positive factor; new pools use declared workload unit and independently reproducible approved recipe; no hidden old-capacity reuse.

## 13 Risks

Full-history calibration can leak future information in an as-of backtest. Factor joins can multiply facts. Assuming all non-canceled orders eligible or defaulting missing factors to 1 changes business meaning.

## 14 Pending decisions

P01–P05, P12/P13/P16/P17/P19. Numeric business baselines cannot be signed off until relevant values/methods are approved.

## 15 Implementation complexity

High

## Preparation details

Keep the original raw file immutable. Source-line identity precedes joins; enforce many-to-one product mapping, exactly one status disposition and non-overlapping factor resolution. Produce exclusion totals by reason and status, including explicitly reported mapping failures.

Historical Gross/Qualified/Excluded remain distinct from synthetic scenario demand. Scenario treatment is not a rewrite of the eligibility ledger.

Capacity recalibration records qualified/gross workload population, time window, plant calendar including declared zero-demand available weeks, target utilization if chosen, rounding and the common workload reference. No default 0.75 target or 1165/1083/913 compatibility is approved.

Factor design permits future Plant x Product scope but does not assume different plant factors initially or authorize cross-plant production. P05 resolves initial scope and resolution precedence.

A/B/C-to-priority mapping is retained. Any classification recomputation basis/window is separately approved under P17.
