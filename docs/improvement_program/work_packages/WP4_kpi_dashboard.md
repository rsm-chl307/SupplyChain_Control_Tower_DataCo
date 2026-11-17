# WP4 KPI and Decision Support

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Provide interpretable, reconcilable demand, supply, workload, stock and shortage metrics through the approved five-page structure.

## 2 Scope

DC15 expanded KPI catalog; separate grains/ratios/stocks; current-versus-backlog service; plant-week bottlenecks; priority trade-offs; rule-based exposure and alert burden; Power BI/Streamlit integration with backend output reconciliation.

## 3 Out of scope

No silent replacement of frozen formulas, probability/causal claims, AI recommendations, economic optimization or wholesale dashboard redesign.

## 4 Business rules

BR-KPI-001, BR-KPI-002, BR-KPI-003, BR-KPI-004, BR-UI-001, BR-CAP-002, BR-BKL-002, BR-BKL-003, BR-PIPE-003.

## 5 Input data

Independently validated Route B state, allocation, current-demand and unique capacity facts; approved metric/threshold/policy versions; manifest for one published run.

## 6 Output data

DC15 grain-specific KPI tables, numerator/denominator fields, terminal-state views, approved event/exposure outputs and five-page presentation mapping.

## 7 Data model

Separate kpi_product_week, kpi_plant_week, kpi_scenario and kpi_terminal_state. Inventory/backlog close stocks are not additive over time. Old Service_Level remains legacy production coverage, not renamed as demand fulfillment.

## 8 Module dependencies

WP3 validated state and cohort attribution; WP2 compatible units; WP1 metric validation; minimal WP5 same-run/publication contract before live loaders. Full raw-to-dashboard integration is accepted at Stage 5.

## 9 Actual repository files affected

src/kpi_engine.py; src/performance_evaluator.py; src/performance_manager.py; dashboard/scenario_planning_app.py; dashboard/supply_chain_control_tower.pbix only after explicit P20 mapping approval; tests/test_performance_evaluation.py; tests/test_dashboard_app.py.

## 10 New files proposed

No new engine module required by default; proposed grain-specific backend outputs at future run paths; add focused KPI/dashboard tests within existing modules unless separate tests improve scope clarity.

## 11 Testing plan

T-KPI-001/002/003; T-UI-001; T-REG-001. Ratio-of-sums, zero/undefined denominator policies, terminal stock versus flow, backlog cohort accounting, stale/mixed run rejection and selected-week/multiweek dashboard reconciliation.

## 12 Acceptance criteria

Every D08 KPI is tracked with its approval/evaluation status. Any unresolved mandatory metric blocks the declared publication scope; optional metric omissions are explicit NOT_EVALUATED, not silently successful. Final program acceptance requires all mandatory expanded KPIs approved and evaluated; backend and dashboard agree at documented grains; five approved page names are preserved; no SUM of ratios/stocks misrepresented as valid; allocation sequence visible; active run/assumptions distinguish results from edited controls.

## 13 Risks

Existing PBIX pages do not match target five pages. Existing legacy risk scores double count exposure and UI can show stale outputs. Plant-week averages can mask local pressure; new views must expose direct pools.

## 14 Pending decisions

P08/P10/P12/P15/P17/P20/P21/P23. A wire/field contract may proceed, but unapproved formulas, page remapping and thresholds cannot be enabled.

## 15 Implementation complexity

High

## KPI catalog and five-page mapping

The single formula catalog is DC15 in ../04_data_contracts.md. Do not duplicate alternate formulas in this WP. Required measures cover all D08 names, including production coverage, customer-demand fulfillment, cohort-aware backlog, workload shortage, inventory/DOI/safety stock, receipts/production, bottlenecks, priority trade-offs and burden.

Approved logical pages are Executive Overview, Demand Analysis, Capacity Monitoring, Inventory & Service Risk and Scenario Planning. Current PBIX has Executive Summary, Demand Driver, Inventory Risk, Capacity Utilization Analysis and Service Risk Analysis. Current Streamlit has three scenario tabs. P20 decides how investigation capabilities are consolidated and where scenario views run; no eight-page expansion is assumed.

UI and Power BI may aggregate approved additive numerators/denominators and render prepared KPIs. They must not independently classify order eligibility, allocate capacity, simulate inventory or reproduce a competing KPI calculation.

Expose current-demand fulfillment and backlog fulfillment separately. A smaller production/net ratio is not inherently a worse customer-demand fill result. Changing shortage mode requires a separate comparison family with an explicitly corresponding Baseline.

New statuses remain unclassified until P10/P15/P21 are approved; a missing threshold cannot produce Healthy by fall-through.
