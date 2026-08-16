# AGENTS.md

## Project

This repository contains a Supply Chain Scenario Planning and Decision-Support prototype built on top of an existing Supply Chain Control Tower project.

The project is portfolio-oriented and should demonstrate practical Supply Chain Planning capabilities.

---

## Core Rule

Do not redesign the project unless explicitly requested or a serious architectural problem is discovered.

The architecture has already been designed and approved.

Prefer implementing the existing specification over inventing new functionality.

---

## Development Priority

Always prioritize:

1. Business correctness
2. Functional MVP
3. End-to-end integration
4. Explainability
5. Validation
6. Refactoring

Do not optimize prematurely.

Do not spend significant effort on minor code-quality improvements while core functionality is incomplete.

---

## Before Coding

Before modifying code:

1. Inspect the repository.
2. Inspect relevant files.
3. Inspect existing functions and interfaces.
4. Determine whether the functionality already exists.
5. Identify dependencies between modules.

Do not assume file names, column names, or interfaces without checking the repository.

---

## Scope Control

Only implement the requested stage or step.

Do not automatically continue into later stages.

For example:

If asked to implement:

```text
Stage 5 Step 1
```

do not implement:

```text
Stage 5 Step 2
Stage 6
AI Agent
Power BI
```

unless explicitly requested.

---

## Architecture Changes

If you discover that the existing architecture is insufficient:

STOP before implementing the architectural change.

Report:

* Current architecture
* Problem
* Why the current design is insufficient
* Proposed alternative
* Expected impact

Wait for approval.

---

## Business Logic

Business rules are more important than code elegance.

Do not silently change:

* Net Demand definition
* Priority logic
* Capacity allocation logic
* Scenario definitions
* KPI definitions

These are approved business decisions.

---

## Current Frozen Allocation Logic

```text
Net Demand =
max(Scenario Demand - Beginning Inventory, 0)
```

Priority:

```text
Priority DESC
Net Demand DESC
Product_ID ASC
```

Allocation:

```text
Allocated =
min(Net Demand, Remaining Capacity)
```

Backlog:

```text
Backlog =
Net Demand - Allocated
```

Capacity is shared at:

```text
Scenario × Plant × Week
```

---

## Coding Style

Use:

* Python
* Pandas
* NumPy when appropriate
* Type hints
* Clear function names
* Docstrings
* Simple modular functions

Avoid unnecessary dependencies.

---

## Module Responsibilities

### Scenario Generator

Creates alternative planning scenarios.

### Allocation Engine

Allocates capacity for one:

```text
Scenario × Plant × Week
```

### Allocation Manager

Runs the allocation engine across the complete dataset.

### Allocation Validator

Validates allocation business rules.

### KPI Engine

Calculates performance KPIs.

### Performance Evaluator

Converts KPI results into risk/performance statuses.

### Performance Manager

Orchestrates KPI calculation and performance evaluation.

Do not duplicate business logic between modules.

---

## File I/O

Core engines should not directly read or write CSV files unless explicitly designed as a pipeline/orchestration module.

Keep business logic separate from file I/O.

---

## Validation

When implementing a major function, test:

* Normal case
* Constrained capacity
* Zero capacity
* Zero demand
* Inventory-covered demand
* Deterministic output

Report test results clearly.

---

## Output Reporting

After implementation, always report:

```text
Files inspected
Files changed
Files created
Tests performed
Test results
Outputs generated
Known issues
```

Do not claim success without actually running the relevant code.

---

## Refactoring

Do not refactor unrelated code during MVP development.

If a refactor is useful but not required for the current task:

Mention it under:

```text
Potential Future Refactor
```

but do not implement it.

---

## Documentation

When a stage is completed, update project documentation only if requested.

Do not create unnecessary documentation files during coding.

---

## Product Scope

This is a:

> Scenario-based supply chain planning decision-support prototype.

Do not describe it as:

* Production APS
* ERP replacement
* Real-time production planning system
* Enterprise optimization platform

unless the project is actually expanded to support those capabilities.

---

## Future AI Extension

AI/LLM/Agent functionality is intentionally deferred.

Do not introduce AI into the core planning engine.

The current system should remain:

```text
Rule-Based
Deterministic
Explainable
Scenario-Based
```

AI can be added later as an optional decision-support layer.
