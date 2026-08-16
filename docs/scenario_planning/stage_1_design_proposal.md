# Stage 1 — Planning Data Design Proposal

## Status and authority

Stage 0 is complete. This document freezes the approved Stage 1 design baseline. It is documentation only: no Planning Snapshot, scenario dataset, Python module, notebook, CSV output, or Power BI change is implemented here.

The existing DataCo Control Tower remains the completed monitoring baseline. This design defines the future extension layer.

## 1. Planning horizon

The canonical Planning Snapshot preserves the complete available baseline data range for traceability. It does not hard-code 26, 52, or any other horizon. Stage 2 applies explicit `planning_start_week` and `planning_end_week` parameters.

```text
Canonical Planning Snapshot
  → Stage 2 planning-horizon filter
  → Scenario Planning Dataset
```

## 2. Grain and business key

The canonical grain is exactly `Plant × Product × Week`. The business key is `Plant_ID + Product Card Id + Week`. The snapshot remains sparse: it contains validated observed Product × Week combinations and does not create a complete dense grid. Missing observations are not automatically interpreted as zero demand.

## 3. Canonical Planning Snapshot contract

The snapshot represents the baseline planning state only. It must not contain Demand Surge or Capacity Disruption modifications. Scenario-specific fields are added downstream.

### Source fields

| Canonical field | Existing source | Definition |
|---|---|---|
| `Plant_ID` | `plant_product_weekly_demand.Plant_ID` | Plant identifier, validated against mapping/master data |
| `Product Card Id` | `plant_product_weekly_demand.Product Card Id` | Existing product identifier retained in the source-facing contract |
| `Product Name` | Demand/inventory data, validated against `dim_product.csv` | Explainable product label |
| `Order_Date` / `Week` | `plant_product_weekly_demand.Order_Date` | Existing week-ending date representation |
| `Weekly_Demand` | `plant_product_weekly_demand.Weekly_Demand` | Baseline product demand |
| `Beginning_Inventory` | `inventory_snapshot_weekly.Beginning_Inventory` | Simulated inventory before additional production allocation |
| `Weekly_Capacity` | `capacity_utilization_weekly.Weekly_Capacity` | Total baseline plant-week capacity |
| `ABC_Class` | `product_abc_classification.ABC_Class` | Existing A/B/C classification |

### Derived planning fields

| Field | Derivation | Role |
|---|---|---|
| `Planning_Priority` | A → 3, B → 2, C → 1 | MVP allocation-sequencing priority, not universal business importance |
| `Planning_Key` | Plant_ID + Product Card Id + Week | Validation and traceability key |

### Context/reconciliation fields

| Field | Source | Role |
|---|---|---|
| `Baseline_Available_Capacity` | `capacity_utilization_weekly.Available_Capacity` | Context/reconciliation only |

`Weekly_Capacity` is the canonical allocation capacity pool and the input to capacity-disruption scenarios. `Baseline_Available_Capacity` is not the allocation pool and must not be reinterpreted as scenario capacity.

### Intentionally excluded

Exclude dashboard alerts, `Utilization`, `Capacity_Status`, service-risk fields, `Ending_Inventory`, `Replenishment_Qty`, `Target_Inventory`, and scenario-specific fields. These are downstream measures, diagnostic outputs, or state changes outside the baseline contract.

## 4. Capacity definition

### Approved decision

Use `Weekly_Capacity` as canonical planning capacity. Retain `Baseline_Available_Capacity` for contextual reconciliation only.

The existing relationship is `Baseline_Available_Capacity = Weekly_Capacity − baseline Weekly_Demand`. Using it as the allocation pool would subtract baseline demand twice and understate the Baseline capacity pool. Total `Weekly_Capacity` supports Baseline, Demand Surge, and Capacity Disruption consistently.

## 5. Planning priority

Planning Priority means allocation sequencing priority for the MVP; it is not a complete measure of business importance. ABC is the only MVP factor:

```text
ABC A → 3
ABC B → 2
ABC C → 1
```

Future versions may add approved factors such as strategic importance, margin, or service risk. Stage 4 will consume this value when capacity is constrained; Stage 1 does not implement allocation.

## 6. Scenario compatibility

| Scenario | Status | Uses | Changed downstream | Unchanged |
|---|---|---|---|---|
| Baseline | MVP | All baseline fields | None | Entire snapshot |
| Demand Surge | MVP | `Weekly_Demand` | `Scenario_Demand` | Inventory, capacity, identity, ABC, baseline demand |
| Capacity Disruption | MVP | `Weekly_Capacity`, plant, week | `Scenario_Capacity` for selected plant-weeks | Demand, inventory, identity, priority |
| Priority Shift | Future | `Planning_Priority` | Scenario priority only | Demand, inventory, capacity, identity |

Priority Shift remains an architectural extension but is excluded from the MVP. No Priority Shift output or logic is created now.

## 7. Data lineage and reuse

```text
Existing Control Tower outputs
  → source-field normalization and joins
  → canonical baseline Planning Snapshot
  → Stage 2 horizon selection
  → Stage 3 MVP scenarios
  → Stage 4 allocation
  → Stage 5 performance evaluation
```

| Existing asset | Decision |
|---|---|
| `plant_product_weekly_demand.csv` | Reuse as baseline demand source; normalize names and week field |
| `inventory_snapshot_weekly.csv` | Reuse `Beginning_Inventory` and keys; exclude unnecessary simulation fields |
| `capacity_utilization_weekly.csv` | Reuse `Weekly_Capacity`; retain `Available_Capacity` as context |
| `product_abc_classification.csv` | Reuse `ABC_Class`; derive `Planning_Priority` |
| Product/plant masters and mapping | Reuse for identity, eligibility, and consistency validation |
| Dashboard summary CSVs | Preserve for the existing dashboard; do not use as primary planning sources |
| Raw DataCo source | Preserve as provenance; do not make it a direct core-engine dependency |
| Existing notebooks | Preserve as the completed Control Tower pipeline |

## 8. Data-quality contract

### Hard failures

