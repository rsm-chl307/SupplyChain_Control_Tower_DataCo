# Supply Chain Scenario Planning Prototype

## Codex Implementation Specification

## 1. Project Context

This project is an extension of an existing Supply Chain Control Tower portfolio project.

The project uses the DataCo Smart Supply Chain dataset and is designed from a Supply Chain Planning perspective.

The objective is to build a scenario-based planning and decision-support prototype that demonstrates:

* Supply Chain Planning
* Scenario Planning
* Capacity Planning
* Capacity Allocation
* Service-Level Analysis
* Root Cause Analysis
* Rule-Based Decision Support

This is a portfolio prototype, not a production planning system.

Do not overstate the system as a real APS, ERP, or production planning platform.

---

# 2. Development Objective

Build the remaining functionality according to the existing project architecture.

The development priority is:

1. Complete the MVP
2. Ensure the complete pipeline works end-to-end
3. Validate business logic
4. Produce Power BI-ready outputs
5. Refactor only after the prototype is functionally complete
6. Add AI-assisted planning only as a later optional extension

Do NOT optimize prematurely.

---

# 3. Important Development Rule

## Architecture Freeze

The existing architecture has already been discussed and approved.

Do not redesign the architecture unless a serious functional or data-integrity problem is discovered.

Before making any architecture change:

1. Explain the problem.
2. Explain why the current design is insufficient.
3. Propose the alternative at a high level.
4. Wait for approval before implementing the change.

Do not silently redesign existing modules.

---

# 4. Existing Planning Architecture

The current planning flow is:

```text
Planning Data
      ↓
Planning Snapshot
      ↓
Scenario Generator
      ↓
Scenario Snapshot
      ↓
Allocation Engine
      ↓
Allocation Result
      ↓
Performance Evaluation
      ↓
Decision Support
      ↓
Power BI
```

The current architecture separates:

* Scenario generation
* Capacity allocation
* KPI calculation
* Performance evaluation
* Decision support

Do not combine these responsibilities unnecessarily.

---

# 5. Planning Grain

The primary planning grain is:

```text
Week × Plant × Product × Scenario
```

Internally, capacity allocation operates on one planning group:

```text
Scenario × Plant × Week
```

Within each planning group, multiple products compete for a shared plant capacity pool.

---

# 6. Current Data Sources

The existing project contains DataCo-derived datasets.

Relevant datasets include:

### Demand

```text
plant_product_weekly_demand.csv
```

Columns:

```text
Plant_ID
Product Card Id
Product Name
Order_Date
Weekly_Demand
```

### Capacity

```text
capacity_utilization_weekly.csv
```

Columns include:

```text
Plant_ID
Order_Date
Weekly_Demand
Weekly_Capacity
Utilization
Available_Capacity
Capacity_Status
```

### Inventory

```text
inventory_snapshot_weekly.csv
```

Relevant columns include:

```text
Plant_ID
Product Card Id
Product Name
Order_Date
Weekly_Demand
Initial_Inventory
Target_Coverage_Days
Average_Daily_Demand
Review_Cycle
Beginning_Inventory
Ending_Inventory
Replenishment_Qty
Target_Inventory
```

### Product Classification

```text
product_abc_classification.csv
```

Columns:

```text
Product Card Id
Product Name
Total_Demand
Demand_Share
Cumulative_Demand_Share
ABC_Class
```

---

# 7. Priority Logic

The first version uses ABC classification as the product priority proxy.

Priority mapping:

```text
ABC A → Priority 3
ABC B → Priority 2
ABC C → Priority 1
```

This is intentionally transparent and does not simulate unavailable margin data.

Future versions may introduce:

* Revenue proxy
* Margin proxy
* Strategic product flag
* Service-risk priority
* Optimization-based priority
* AI-assisted priority

Do not implement these in the MVP unless explicitly requested.

---

# 8. Scenario Planning

Current required scenarios:

## Baseline

Original demand and available capacity.

## Demand Surge

Increase scenario demand by a configurable percentage.

Examples:

```text
+10%
+20%
+30%
```

## Capacity Disruption

Reduce available capacity at a selected plant by a configurable percentage.

Examples:

```text
-10%
-15%
-20%
```

## Priority Shift

Priority-based allocation is handled by the Allocation Engine rather than by changing the scenario demand/capacity itself.

---

# 9. Allocation Business Rules

The Allocation Engine uses a deterministic rule-based strategy.

Current strategy:

```text
Priority First
```

Products are ranked by:

```text
Priority DESC
Net_Demand DESC
Product_ID ASC
```

This ensures deterministic results.

---

# 10. Net Demand Rule

This is a FROZEN business decision.

Use:

```text
Net_Demand =
max(
    Scenario_Demand - Beginning_Inventory,
    0
)
```

Inventory is assumed to satisfy demand before additional production capacity is allocated.

Do not change this rule without approval.

---

# 11. Capacity Model

Capacity is a shared pool at:

```text
Scenario × Plant × Week
```

All products within the same planning group compete for the same capacity.

Example:

```text
Plant A
Week 10
Capacity = 100

Product A
Product B
Product C
```

The 100 units are shared across all products.

Do NOT treat Scenario_Capacity as independent capacity for each product.

---

# 12. Allocation Formula

For each product:

```text
Allocated_Qty =
min(
    Net_Demand,
    Remaining_Capacity
)
```

Then:

```text
Remaining_Capacity =
Remaining_Capacity - Allocated_Qty
```

And:

```text
Backlog =
Net_Demand - Allocated_Qty
```

---

# 13. Allocation Reason

Each allocation result should include an explainable reason.

Current allowed values:

```text
No Production Required
Demand Fully Satisfied
Remaining Capacity
Capacity Exhausted
```

Interpretation:

### No Production Required

```text
Net_Demand = 0
```

### Demand Fully Satisfied

The entire Net Demand was allocated.

### Remaining Capacity

Only part of the Net Demand was allocated because the remaining capacity was insufficient.

### Capacity Exhausted

No capacity remained before the product was processed.

---

# 14. Allocation Result

The main allocation output should contain at least:

```text
Scenario
Plant
Week
Product
Scenario_Demand
Beginning_Inventory
Scenario_Capacity
Priority
Net_Demand
Allocated_Qty
Backlog
Remaining_Capacity
Allocation_Order
Allocation_Strategy
Allocation_Reason
```

Preserve the original planning/scenario fields wherever possible.

---

# 15. Allocation Engine Responsibilities

`allocation_engine.py` is responsible for:

* Validating the capacity pool
* Calculating Net Demand
* Sorting products
* Initializing remaining capacity
* Allocating capacity
* Calculating backlog
* Generating allocation reasons
* Returning allocation results

It must NOT:

* Read CSV files
* Write CSV files
* Calculate KPIs
* Generate recommendations
* Loop through all scenarios/plants/weeks

The core engine should operate on one:

```text
Scenario × Plant × Week
```

planning group.

---

# 16. Allocation Manager Responsibilities

`allocation_manager.py` is responsible for:

* Grouping the complete scenario dataset
* Grouping by:

```text
Scenario
Plant
Week
```

* Calling `allocate_capacity()`
* Combining all allocation results
* Returning the complete allocation dataset

It must NOT implement allocation business logic.

---

# 17. Allocation Validator

`allocation_validator.py` is a quality gate.

It should validate:

### Check 1

```text
Allocated_Qty >= 0
```

### Check 2

```text
Allocated_Qty <= Net_Demand
```

### Check 3

```text
Backlog >= 0
```

### Check 4

```text
Allocated_Qty + Backlog = Net_Demand
```

### Check 5

For each:

```text
Scenario × Plant × Week
```

```text
Total Allocated_Qty <= Scenario_Capacity
```

### Check 6

```text
Final Remaining Capacity =
Scenario Capacity - Total Allocation
```

The validator should fail fast when a business rule is violated.

It should not silently modify invalid data.

---

# 18. Stage 4 Milestone

Stage 4 is considered complete when:

```text
scenario_snapshot.csv
        ↓
allocation_manager
        ↓
allocation_result.csv
        ↓
allocation_validator
        ↓
validation passed
```

The output must be reproducible and deterministic.

---

# 19. Stage 5 — Performance Evaluation

Stage 5 asks:

> How well does the generated supply plan perform?

Input:

```text
allocation_result.csv
```

Output:

```text
performance_result.csv
```

Stage 5 is divided into four steps.

---

## Stage 5 Step 1 — KPI Engine

File:

```text
src/kpi_engine.py
```

Responsibilities:

Calculate:

### Service Level

```text
Service_Level =
Allocated_Qty / Net_Demand
```

If:

```text
Net_Demand = 0
```

use:

```text
Service_Level = 1.0
```

because there is no unmet production requirement.

---

### Capacity Utilization

```text
Capacity_Utilization =
Allocated_Qty / Scenario_Capacity
```

If capacity is zero:

```text
Capacity_Utilization = 0
```

---

### Capacity Gap

```text
Capacity_Gap =
Scenario_Capacity - Allocated_Qty
```

---

### Allocation Rate

```text
Allocation_Rate =
Allocated_Qty / Scenario_Demand
```

If Scenario Demand is zero:

```text
Allocation_Rate = 1.0
```

because there is no demand to allocate.

---

# 20. Stage 5 Step 2 — Performance Evaluator

File:

```text
src/performance_evaluator.py
```

Responsibilities:

Use KPI results to assign performance/risk statuses.

Potential outputs:

```text
Service_Risk
Capacity_Risk
Performance_Status
```

The thresholds should be transparent and documented.

Do not introduce arbitrary complex scoring models.

Use simple business rules first.

---

# 21. Stage 5 Step 3 — Performance Manager

File:

```text
src/performance_manager.py
```

Responsibilities:

```text
allocation_result
        ↓
KPI Engine
        ↓
Performance Evaluator
        ↓
performance_result
```

It should orchestrate modules rather than duplicate business logic.

---

# 22. Stage 5 Step 4 — Notebook

Create:

```text
03_run_performance_engine.ipynb
```

Purpose:

Run the complete Performance Evaluation pipeline.

Expected flow:

```text
allocation_result.csv
        ↓
KPI Engine
        ↓
Performance Evaluator
        ↓
performance_result.csv
```

---

# 23. Important Scope Boundary

Do NOT implement the following yet:

* OR-Tools
* Linear Programming
* Mixed Integer Programming
* Multi-plant optimization
* Machine Learning
* LLM
* AI Agent
* Dynamic optimization
* Advanced forecasting

These are future extensions.

The MVP should remain:

```text
Rule-Based
Explainable
Deterministic
Scenario-Based
```

---

# 24. Future Decision Support

After Stage 5, Stage 6 will convert performance results into recommendations.

Example rules:

### Rule 1

If:

```text
Capacity Utilization > 95%
AND
Backlog > 0
```

recommend:

```text
Evaluate overtime, alternate plant, or capacity expansion
```

### Rule 2

If:

```text
Priority Product
AND
Service Level < 90%
```

recommend:

```text
Prioritize allocation or expedite capacity recovery
```

### Rule 3

If:

```text
Demand increase > 15%
```

recommend:

```text
Validate forecast and secure material or production capacity
```

### Rule 4

If:

```text
Low-priority product
AND
Capacity constrained
```

recommend:

```text
Consider reallocating capacity
```

Do not implement these until Stage 6.

---

# 25. Development Philosophy

The project should demonstrate business thinking rather than excessive software engineering.

Prioritize:

1. Correct business logic
2. Explainability
3. Reproducibility
4. End-to-end functionality
5. Clear outputs
6. Portfolio presentation

Do not spend excessive time on minor refactoring during MVP development.

Refactoring can happen after the full prototype works.

---

# 26. Required Working Style

Before modifying an existing module:

1. Inspect the current implementation.
2. Inspect its inputs and outputs.
3. Check whether the requested functionality already exists.
4. Reuse existing functions where appropriate.
5. Avoid duplicate logic.
6. Do not rewrite unrelated files.

When a change affects architecture:

STOP and report:

```text
Architecture Issue
Current Design
Problem
Proposed Change
Impact
```

Do not implement the architecture change automatically.

---

# 27. Coding Style

Use:

* Python
* Pandas
* NumPy where appropriate
* Type hints
* Clear function names
* Docstrings
* Simple modular functions

Do not add unnecessary frameworks.

Do not introduce paid tools.

---

# 28. Validation Philosophy

For every major module:

1. Test normal case
2. Test constrained case
3. Test zero-capacity case
4. Test zero-demand case
5. Test inventory-covered demand
6. Test deterministic output

The purpose is to confirm business behavior rather than maximize automated test coverage.

---

# 29. Current Development Status

```text
Stage 0  Project Definition                 COMPLETE
Stage 1  Planning Data Design               COMPLETE
Stage 2  Planning Data Pipeline             COMPLETE
Stage 3  Scenario Generator                 COMPLETE
Stage 4  Decision / Allocation Engine       NOT STARTED
Stage 5  Performance Evaluation             NOT STARTED

Future   AI-Assisted Planning               FUTURE
```

---

# 30. Immediate Task

Stage 3 Scenario Generator is complete.

The next implementation stage is Stage 4 – Decision / Allocation Engine.

Do not proceed to Stage 5 unless explicitly instructed.

---

# 31. Final Principle

This project should be treated as:

> **A scenario-based supply chain planning decision-support prototype.**

It is not a production APS.

The purpose is to demonstrate that the developer understands:

```text
Supply Chain Data
        ↓
Planning Context
        ↓
Scenario Analysis
        ↓
Capacity Allocation
        ↓
Performance Evaluation
        ↓
Decision Support
```

The implementation should remain simple, explainable, and business-oriented.
