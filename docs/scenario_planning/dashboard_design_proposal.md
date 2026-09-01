# Scenario Planning Dashboard / Decision-Support Design Proposal

## 1. Objective

The completed Control Tower answers **what is happening** and **why it is happening**. The Scenario Planning extension answers:

- What happens if demand or capacity conditions change?
- How is shared plant capacity allocated under the scenario?
- What service, capacity, and backlog impact should a planner expect?

The combined decision-support flow is:

```text
Operational Monitoring
        → Root Cause Analysis
        → Scenario Planning
        → Capacity Allocation
        → Performance Evaluation
        → Decision Support
```

The dashboard should visualize this flow without duplicating backend business logic.

## 2. Existing Control Tower architecture

The existing Power BI file is `dashboard/supply_chain_control_tower.pbix`. The documented Control Tower pages are:

| Existing page | Primary question | Keep unchanged |
|---|---|---|
| Executive Overview | What is the overall operational risk? | Yes |
| Demand Driver Analysis | Which products drive demand and growth? | Yes |
| Inventory Risk Analysis | Which products have insufficient coverage or reorder risk? | Yes |
| Capacity Utilization Analysis | Which plants approach capacity limits? | Yes |
| Service Risk Root Cause Analysis | What operational factors drive service risk? | Yes |

Existing notebooks prepare weekly demand, inventory, capacity, service-risk, root-cause, and executive summary datasets. The existing dashboard remains the operational monitoring baseline. Scenario Planning should be an additional section rather than a redesign of those pages.

One repository limitation is that `notebooks/03_control_tower_dashboard.ipynb` is empty/invalid, although the PBIX and supporting datasets exist. This should not block dashboard integration, but it reduces notebook-level reproducibility.

## 3. Scenario Planning integration architecture

```text
Existing Control Tower
  ├─ Executive Overview
  ├─ Demand Driver Analysis
  ├─ Inventory Risk Analysis
  ├─ Capacity Utilization Analysis
  ├─ Service Risk Root Cause Analysis
  │
  └─ Scenario Planning
       ├─ Scenario Overview
       ├─ Scenario Comparison
       └─ Capacity Allocation Detail
```

The existing pages remain responsible for monitoring and diagnosis. The new pages consume the frozen Stage 1–5 outputs for planning and decision support.

## 4. User workflow

1. Review current operational conditions in the Executive Overview.
2. Identify a demand, inventory, capacity, or service-risk signal.
3. Use existing Root Cause Analysis to identify the relevant Plant, Product, Week, and risk driver.
4. Navigate to Scenario Planning while preserving that context.
5. Select Baseline, Demand Surge, or Capacity Disruption.
6. Configure approved scenario parameters.
7. Compare the selected scenario with Baseline.
8. Review plant/week capacity pressure and allocation results.
9. Drill into affected products and allocation reasons.
10. Use the evaluated trade-offs to support a planning decision.

Plant, Product, Week, and risk-driver filters should be passed through navigation or drill-through. Root-cause calculations should remain in the existing Control Tower datasets.

## 5. Scenario controls

| Control | Input type | Default/example | Validation | Backend handoff |
|---|---|---|---|---|
| Scenario | Selector | Baseline | Baseline, Demand Surge, Capacity Disruption only | Scenario parameter mapping |
| Demand Surge percentage | Numeric input | 10.0% | Finite and >= 0 | `demand_increase_pct` |
| Disruption percentage | Numeric input | 20.0% | Finite and 0–100% | `capacity_reduction_pct` |
| Disruption plant | Single/multi-select | P1 for example | Required and must exist | `plant_ids` |
| Planning start week | Date/week selector | Selected horizon start | Required valid date within source range | `planning_start_week` |
| Planning end week | Date/week selector | Selected horizon end | Required valid date within source range and >= start | `planning_end_week` |

Demand Surge applies to the selected horizon. Capacity Disruption applies to selected plants and optionally selected weeks. Priority Shift remains unavailable because it is a future extension.

The UI should display the active assumptions in a scenario summary card and pass them to the backend runner. It must not reimplement scenario formulas in Power BI. Invalid values should be rejected before execution, with the backend returning explicit validation errors.

Multiple scenarios may be selected for comparison, with Baseline always retained as the reference.

## 6. Dashboard page structure

### Scenario Overview

**Purpose:** Give a planner a concise view of one selected scenario.

**Main question:** What is the expected operational state under this scenario?

**KPIs:** Service Level, Capacity Utilization, Allocation Rate, Total Backlog, Remaining Capacity, Capacity Gap, Performance Status.

**Recommended visuals:**

- KPI cards;
- scenario-assumption panel;
- performance-status card or matrix;
- compact plant comparison;
- selected-horizon weekly trend.

**Filters:** Scenario, planning horizon, Plant, Week.

**Drill-through:** Scenario Comparison or Capacity Allocation Detail, preserving Scenario, Plant, and Week context.

### Scenario Comparison

**Purpose:** Show how alternatives differ from Baseline.

**Main question:** What changes if demand increases or capacity is disrupted?

**Metrics:** Service Level Change, Capacity Utilization Change, Backlog Change, Allocation Rate Change.

**Recommended visuals:**

- Baseline-versus-scenario clustered columns;
- KPI variance cards;
- backlog-change bar chart;
- conditional-format comparison table.

**Filters:** Scenario, horizon, Plant where detailed context is needed.

**Drill-through:** Capacity Allocation Detail for the selected scenario and affected plant/week.

### Capacity Allocation Detail

**Purpose:** Explain the operational allocation decision at product level.

**Main question:** Which products received capacity, and what remained unmet?

**Fields:** Scenario, Plant, Product, Week, Planning Priority, Net Demand, Allocated Qty, Backlog, Remaining Capacity, Allocation Reason.

**Recommended visuals:**

- Plant × Week capacity heatmap;
- allocation/backlog detail table;
- priority and allocation-order table;
- remaining-capacity trend.

**Filters:** Scenario, Plant, Week, Product, Planning Priority, Allocation Reason.

This page uses `allocation_result.csv` for detail and does not recalculate allocation.

## 7. KPI design

Use the frozen Stage 5 definitions exactly:

- Service Level = `Allocated_Qty / Net_Demand`, with 1.0 when Net Demand is zero;
- Allocation Rate = `Allocated_Qty / Scenario_Demand`, with 1.0 when Scenario Demand is zero;
- Capacity Utilization = ratio of total allocation to deduplicated total scenario capacity;
- Capacity Gap = Scenario Capacity minus Allocated Quantity;
- Total Backlog = sum of Stage 4 Backlog;
- Remaining Capacity = Stage 5 capacity remainder;
- Performance Status = Healthy, Watch, or At Risk.

Power BI should consume the prepared values. It should not redefine or recompute these KPIs with different denominators.

The legacy Control Tower `Capacity Utilization` is based on weekly demand versus weekly capacity. It must be labeled separately from Scenario Planning utilization, which is based on allocated production versus scenario capacity.

## 8. Scenario comparison design

Baseline is the fixed reference. Display:

- `Service_Level_Change`;
- `Capacity_Utilization_Change`;
- `Backlog_Change`;
- `Allocation_Rate_Change`.

Use positive/negative conditional formatting with explanatory labels. Do not create a composite scenario score or rank scenarios automatically.

Capacity utilization should be interpreted together with backlog and remaining capacity. Higher utilization is not necessarily negative when service remains fully satisfied.

## 9. Capacity planning design

The capacity view should make these relationships visible:

```text
Scenario Capacity
  → Allocated Production
  → Remaining Capacity / Capacity Gap
  → Backlog and Service Impact
```

Recommended views:

- Plant comparison of capacity utilization;
- Plant × Week heatmap;
- remaining-capacity trend;
- scenario variance for the disrupted plant;
- product allocation detail for constrained weeks.

No optimization or automated recommendation should be introduced. The system remains rule-based, deterministic, and explainable.

## 10. Root Cause → Scenario Planning connection

The existing Root Cause page remains the source of the diagnostic context:

```text
What is wrong?
  → Why is it happening?
  → What if conditions change?
  → How is capacity allocated?
  → What is the expected impact?
```

The transition should carry:

- `Plant_ID`;
- `Product Card Id`;
- `Order_Date`;
- existing risk-driver context where available.

Navigation or drill-through should preserve these filters. Scenario Planning should not duplicate existing service-risk or root-cause calculations.

## 11. Power BI data model

| Table | Role | Grain |
|---|---|---|
| `performance_result.csv` | Primary scenario KPI/status/comparison table | Mixed, identified by `Aggregation_Level` |
| `allocation_result.csv` | Product-level drill-through | Scenario × Plant × Product × Week |
| `scenario_snapshot.csv` | Scenario demand/capacity context | Scenario × Plant × Product × Week |
| Existing Control Tower tables | Monitoring and root-cause pages | Existing operational grains |

`performance_result.csv` must not be treated as one ordinary fact table without filtering `Aggregation_Level`. Its rows are:

- Scenario;
- Scenario × Plant;
- Scenario × Week.

Use `Aggregation_Level` explicitly in visuals and measures. Plant and Order Date are nullable for higher-level rows.

Use conformed dimensions for Plant, Product, Week, and Scenario where relationships are needed. Avoid direct many-to-many relationships between mixed-grain KPI rows and product-level allocation rows. Use separate page-level tables or carefully constrained relationships.

`allocation_result.csv` supports drill-through because it retains the complete Scenario × Plant × Product × Week identity and allocation fields.

## 12. Data lineage

```text
DataCo raw/processed sources
  → Stage 1 Planning Snapshot
  → Stage 2 horizon-filtered snapshot
  → Stage 3 scenario snapshot
  → Stage 4 allocation result
  → Stage 5 performance result
  → Power BI Scenario Planning pages
```

The existing Control Tower outputs remain separate monitoring sources. Scenario Planning outputs should be loaded as additional tables rather than replacing the existing model.

## 13. End-to-End runner recommendation

A lightweight runner should be used before dashboard refreshes so the repository has one clear command to regenerate all Stage 1–5 artifacts.

Conceptual interface:

```text
planning_start_week
planning_end_week
demand_surge_pct
capacity_disruption_pct
disruption_plant
```

Flow:

```text
Planning Pipeline
  → Scenario Generator
  → Allocation Manager
  → Performance Manager
  → approved output artifacts
```

The runner should compose existing modules, preserve the baseline artifacts, validate parameters, and write deterministic outputs. No orchestration framework is required.

## 14. Current zero-backlog limitation

The approved 2017 horizon currently produces:

- Service Level = 100%;
- Backlog = 0;
- Healthy status for all real output rows.

The dashboard should state this plainly rather than implying that no risk is possible. A callout such as “No backlog observed in selected horizon” is appropriate.

A future, explicitly named stress-test configuration could use an approved constrained capacity parameter or alternate horizon to demonstrate backlog behavior. It must not alter the canonical baseline, current artifacts, or frozen business rules.

## 15. MVP scope

### Must have

- Existing five Control Tower pages preserved;
- Scenario Overview page;
- Scenario Comparison page;
- Capacity Allocation Detail page;
- Baseline comparison;
- Service Level, Capacity Utilization, Allocation Rate, Backlog, Remaining Capacity, Capacity Gap, and Performance Status;
- Plant/week filtering;
- allocation drill-through;
- visible scenario assumptions;
- clear distinction between monitoring and planning metrics.

### Should have

- Root Cause → Scenario Planning navigation;
- Plant × Week capacity heatmap;
- allocation-reason detail;
- parameter provenance display;
- explicit zero-backlog messaging;
- documented refresh sequence.

### Future

- Interactive parameter execution through the runner;
- approved stress-test presets;
- product-level KPI drilldown;
- automated recommendations;
- optimization;
- forecasting;
- AI/RAG decision-support explanations.

## 16. Portfolio / interview value

The combined story is:

```text
Control Tower
  → Root Cause Analysis
  → Scenario Planning
  → Capacity Planning
  → Rule-Based Allocation
  → Performance Evaluation
  → Decision Support
```

The project demonstrates how a monitoring dashboard can evolve into a planning decision-support tool without pretending to be a production APS. It connects operational evidence to explicit what-if assumptions, shared-capacity allocation, and measurable service/capacity trade-offs.

## 17. Implementation sequence

1. Freeze this dashboard design.
2. Define and implement the lightweight end-to-end runner.
3. Validate reproducibility and artifact refresh behavior.
4. Map Scenario Planning outputs into the Power BI model without changing existing Control Tower logic.
5. Build Scenario Overview.
6. Build Scenario Comparison.
7. Build Capacity Allocation Detail.
8. Connect Root Cause → Scenario Planning navigation.
9. Validate filters, aggregation-level handling, and KPI consistency.
10. Perform final end-to-end dashboard validation.

## 18. Risks and assumptions

- The existing PBIX model is treated as the operational baseline; its internal relationships require validation when opened in Power BI.
- Mixed-grain `performance_result.csv` requires strict `Aggregation_Level` filtering.
- Legacy Control Tower and Scenario Planning KPI definitions must remain visibly distinct.
- The runner now regenerates Stages 2–5; Stage 1 remains the approved baseline contract.
- The current horizon has no real backlog, limiting stress visualization.
- The empty dashboard notebook reduces reproducibility but does not invalidate the PBIX.
- No dependency manifest is currently present.
- No UI, Power BI change, backend refactor, or new data artifact is part of this design phase.



## End-to-End Runner Implementation Record

The lightweight runner is implemented at `src/run_planning.py`. Its `run_planning(...)` entry point composes the existing Stage 2 planning pipeline, Stage 3 scenario generator, Stage 4 allocation manager, and Stage 5 performance manager without duplicating business rules.

Required inputs are `data_root`, `planning_start_week`, `planning_end_week`, and `disruption_plant`. The approved example defaults are 10% demand surge and 20% capacity disruption. An optional `output_dir` controls the run destination; by default outputs are written under `data/processed/scenario_runs/{start}_{end}/` so historical root artifacts are protected.

Each run writes a horizon snapshot, `scenario_snapshot.csv`, `allocation_result.csv`, and `performance_result.csv` in that run-specific directory. Invalid horizons, percentages, or plant arguments fail loudly. Repeated execution with identical inputs produces identical files.

The runner does not implement UI or Power BI behavior. Future dashboard controls should pass validated parameters to this runner rather than reproduce scenario, allocation, or KPI calculations.

## Dashboard Integration MVP Implementation Record

The approved MVP presentation layer is implemented as `dashboard/scenario_planning_app.py` using Streamlit and Plotly. It adds Scenario Overview, Scenario Comparison, and Capacity Allocation Detail views without modifying the existing `dashboard/supply_chain_control_tower.pbix`. User controls pass planning horizon and approved scenario parameters to `src/run_planning.py`; prepared performance, allocation, and scenario outputs are loaded for display.
