# Service Risk KPI Definitions

## Service Risk

Service Risk indicates the likelihood that customer demand cannot be fulfilled due to inventory shortages or capacity constraints.

---

## Inventory Risk Impact

Condition:

Inventory_Status = Critical

Impact:

Product may experience stockout risk.

---

## Capacity Risk Impact

Condition:

Capacity_Status = Critical

Impact:

Plant may not be able to support required production volume.

---

## Service Risk Severity

### High

Inventory_Status = Critical
AND
Capacity_Status = Critical

### Medium

Inventory_Status = Critical
OR
Capacity_Status = Critical

### Low

No critical inventory or capacity alerts.

---

## Business Purpose

Service Risk provides an integrated view of operational risk across inventory and production capacity, enabling proactive escalation before customer service levels are impacted.