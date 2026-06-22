# Inventory Risk Module Assumptions

## Objective

This document summarizes the assumptions, business rules, and simulation logic used in the Inventory Risk Monitoring module of the Supply Chain Control Tower project.

---

# 1. Inventory Policy Framework

Products are categorized using ABC inventory classification based on cumulative demand contribution.

Inventory policies are assigned according to product importance.

| ABC Class | Safety Stock Days | Target Coverage Days |
| --------- | ----------------: | -------------------: |
| A         |                21 |                   45 |
| B         |                14 |                   30 |
| C         |                 7 |                   21 |

### Business Rationale

* A products represent high-demand and business-critical items requiring higher service levels.
* B products represent medium-demand items requiring balanced inventory policies.
* C products represent long-tail products with lower inventory coverage requirements.

---

# 2. Initial Inventory Estimation

The source dataset does not contain actual inventory records.

To enable inventory risk analysis, initial inventory positions are estimated using demand-based planning assumptions.

## Formula

Average Daily Demand

= Average Weekly Demand ÷ 7

Initial Inventory

= Average Daily Demand × Target Coverage Days × Buffer Factor

---

# 3. Inventory Buffer Assumptions

Additional inventory buffers are applied to account for demand variability and long-tail demand patterns.

| ABC Class | Buffer Factor |
| --------- | ------------: |
| A         |             2 |
| B         |             3 |
| C         |             5 |

### Business Rationale

Lower-volume products often exhibit unstable demand patterns. Applying inventory buffers reduces the likelihood of unrealistic inventory depletion caused by demand sparsity in the dataset.

---

# 4. Inventory Review Policy

A periodic review inventory policy is used.

## Review Frequency

Inventory positions are reviewed every 4 weeks.

## Replenishment Rule

At the end of each review cycle:

Replenishment Quantity

= Target Inventory − Ending Inventory

Inventory is replenished back to the target inventory level whenever inventory falls below the target position.

---

# 5. Inventory Simulation Logic

The inventory simulation follows the process below:

Beginning Inventory

↓

Weekly Demand Consumption

↓

Ending Inventory

↓

Periodic Inventory Review

↓

Replenishment

↓

Next Week Beginning Inventory

Inventory levels are constrained to remain non-negative.

---

# 6. Days of Inventory (DOI)

Days of Inventory (DOI) measures how many days current inventory can support expected demand.

## Formula

DOI

= Inventory On Hand ÷ Average Daily Demand

---

# 7. Inventory Status Classification

Inventory health is classified according to DOI thresholds.

## Critical

DOI < Safety Stock Days

## Warning

Safety Stock Days ≤ DOI < Target Coverage Days

## Normal

DOI ≥ Target Coverage Days

---

# 8. Inventory Alert Logic

Products are flagged for inventory risk monitoring when inventory falls below safety stock requirements.

## Reorder Risk

Triggered when:

DOI < Safety Stock Days

## Inventory Alert

Triggered when:

Inventory Status = Critical

---

# 9. Known Limitations

The dataset does not contain:

* Actual inventory transactions
* Purchase orders
* Production schedules
* Supplier lead times
* Warehouse receipts
* Replenishment history

Therefore, inventory positions are simulated using policy-based assumptions rather than actual operational inventory data.

Future enhancements may incorporate:

* Dynamic safety stock calculations
* Demand forecast-based replenishment
* Lead time variability
* Service-level optimization
* Multi-echelon inventory planning

---

# Deliverables

The Inventory Risk module produces the following datasets:

* inventory_policy.csv
* product_inventory_baseline.csv
* inventory_snapshot_weekly.csv
* inventory_risk_weekly.csv

These datasets support inventory monitoring, risk alerting, root cause investigation, and executive supply chain dashboards.
