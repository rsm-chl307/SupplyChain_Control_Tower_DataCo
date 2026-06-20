# KPI Definition

## Project

Supply Chain Control Tower

---

# Capacity Risk KPI

## Objective

The Capacity Risk module monitors manufacturing workload, identifies potential bottlenecks, and supports proactive capacity planning decisions.

The objective is to provide early visibility into capacity constraints before they impact service levels, inventory availability, or business performance.

---

## KPI 1: Weekly Demand

### Business Definition

Total customer demand assigned to a manufacturing plant during a specific week.

### Formula

Weekly Demand =

Sum of Order Item Quantity

### Granularity

* Weekly
* Plant Level

### Business Purpose

* Measure plant workload
* Support capacity planning
* Monitor demand fluctuations

### Stakeholders

* Supply Chain Planning Manager
* Manufacturing Operations Manager

---

## KPI 2: Weekly Capacity

### Business Definition

Estimated weekly production capacity available at a manufacturing plant.

### Capacity Planning Assumption

The original DataCo dataset does not contain manufacturing capacity information.

To support bottleneck monitoring and capacity planning, plant capacity was estimated using historical demand patterns.

### Formula

Weekly Capacity =

Average Weekly Demand / 0.75

### Design Rationale

A target utilization rate of 75% was selected after sensitivity analysis.

The initial 85% utilization assumption generated an unrealistically high proportion of Warning and Critical alerts.

The 75% assumption produced a more realistic operational risk distribution and provided sufficient capacity buffer to absorb demand variability.

### Granularity

* Weekly
* Plant Level

### Stakeholders

* Supply Chain Planning Manager
* Manufacturing Operations Manager

---

## KPI 3: Capacity Utilization

### Business Definition

Percentage of plant capacity consumed by weekly demand.

### Formula

Capacity Utilization =

Weekly Demand / Weekly Capacity

### Interpretation

Higher utilization indicates increasing workload and reduced operational flexibility.

### Business Purpose

* Identify bottlenecks
* Monitor plant workload
* Trigger capacity planning actions

### Granularity

* Weekly
* Plant Level

### Stakeholders

* Supply Chain Planning Manager
* Manufacturing Operations Manager
* Business Process Analyst

---

## KPI 4: Available Capacity

### Business Definition

Remaining production capacity available after fulfilling weekly demand.

### Formula

Available Capacity =

Weekly Capacity − Weekly Demand

### Interpretation

Lower available capacity indicates higher risk of future capacity constraints.

### Business Purpose

* Monitor remaining capacity buffer
* Evaluate ability to absorb additional demand
* Support production planning decisions

### Granularity

* Weekly
* Plant Level

### Stakeholders

* Supply Chain Planning Manager
* Manufacturing Operations Manager

---

## KPI 5: Capacity Status

### Business Definition

Capacity risk level assigned to a plant based on utilization thresholds.

### Alert Logic

Normal

Capacity Utilization < 85%

---

Warning

85% ≤ Capacity Utilization < 95%

---

Critical

Capacity Utilization ≥ 95%

### Business Purpose

Provide an easily interpretable operational risk signal for management monitoring.

### Stakeholders

* Supply Chain Planning Manager
* Manufacturing Operations Manager
* Executive Leadership

---

# Capacity Risk Monitoring Workflow

Weekly Demand
↓
Weekly Capacity
↓
Capacity Utilization
↓
Available Capacity
↓
Capacity Status
↓
Management Action

---

# Management Actions

## Normal

Action:

* Continue monitoring
* No intervention required

---

## Warning

Action:

* Review demand trends
* Evaluate short-term capacity adjustments
* Investigate high-growth products

---

## Critical

Action:

* Escalate to planning team
* Review production schedule
* Reallocate capacity if possible
* Initiate root cause analysis

# Root Cause Analysis KPIs

## Demand Rank

Business Definition:

Product demand ranking within a plant-week.

Business Purpose:

Identify products consuming the largest share of plant capacity.

---

## Demand Change

Business Definition:

Absolute increase in demand compared with the previous week.

Formula:

Weekly Demand - Previous Week Demand

Business Purpose:

Identify products driving capacity utilization increases.

---

## Demand Contribution

Business Definition:

Percentage contribution to total plant demand.

Formula:

Product Demand / Plant Demand

Business Purpose:

Measure product concentration risk and identify dominant products.