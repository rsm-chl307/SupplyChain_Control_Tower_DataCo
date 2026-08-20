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

## Approval / Permission Policy

Operate autonomously within the currently approved stage.

Do not repeatedly ask for approval for routine, non-destructive actions that
are clearly required by the current task, including:

* Reading repository files
* Inspecting Git status or diffs
* Running tests and validation
* Running Python scripts or syntax checks
* Creating or modifying files within the approved stage
* Generating approved outputs
* Removing generated Python cache files such as `__pycache__` and `.pyc`
* Updating documentation required to record completed work

Ask for explicit approval only when the action:

* Changes a frozen business rule
* Changes the approved architecture
* Expands beyond the current stage
* Modifies or deletes important completed-stage artifacts
* Requires a new dependency or environment-level change
* Performs destructive filesystem operations
* Performs Git commit, push, reset, clean, or history-changing operations
* Requires a new business decision

When approval is required, briefly explain what decision is needed and why.

Otherwise, proceed with the implementation without interrupting the user
for routine permission requests.

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

If a business rule is ambiguous or not yet defined, identify the issue and
ask for approval before changing it.

---

## Current Frozen Allocation Logic

```text
Net Demand =
max(Scenario Demand - Beginning Inventory, 0)
```

Priority:

```text
Planning_Priority DESC
Net Demand DESC
Product Card Id ASC
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

When a stage is completed, update the relevant project documentation to
keep development records synchronized.

At minimum, review:

* Stage design proposal
* developer notes
* project journal
* ai_agent_implementation_spec.md

Update documentation only for the work completed in the current stage.

Do not create unnecessary documentation files.

Preserve historical development decisions where appropriate.

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

## Future UI

The final project may expose scenario parameters through a user-facing UI.

Users should eventually be able to adjust scenario parameters without
modifying Python source code.

However:

* Do not implement UI functionality unless explicitly requested.
* Keep scenario business logic in the backend.
* The UI should pass parameters to the Scenario Generator rather than
  duplicate scenario calculations.

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
