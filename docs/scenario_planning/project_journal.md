# Project Journal

## Stage 0 — Project Definition

### Objective

Define the business problem, planning decision context, scenarios, architecture direction, constraints, success criteria, and future AI boundary for the Scenario Planning extension. Stage 0 is documentation only.

### Decisions and Scope

- The completed Control Tower and Power BI dashboard are the baseline monitoring and diagnostic layer.
- Scenario Planning is a separate future layer at Plant × Product × Week, with Scenario added to scenario outputs.
- Baseline, Demand Surge, and Capacity Disruption are required initial scenarios; Priority Shift is optional.
- ABC A/B/C maps to priorities 3/2/1, and the initial capacity-allocation direction is deterministic and rule-based.
- The future flow is Planning Data Layer → Planning Snapshot → Scenario Generator → Allocation → Performance Evaluation → Decision Support → Power BI.
- Stage 0 does not create planning code, allocation logic, scenario outputs, OR optimization, AI/RAG functionality, or changes to existing Control Tower assets.

### Assumptions and Unresolved Items

Inventory and capacity inputs are derived or simulated Control Tower datasets rather than production execution records. Stage 1 must resolve whether `Scenario_Capacity` uses total `Weekly_Capacity` or derived `Available_Capacity`, and whether missing product-week observations should remain sparse or be represented as zero demand. These are planning-data decisions, not Stage 0 implementation changes.

### Current Status

Stage 0 — Project Definition: COMPLETE.

Stage 1 — Planning Data Design: NOT STARTED.

Stage 2 — Planning Data Pipeline: NOT STARTED.

Stage 3 — Scenario Generator: NOT STARTED.

Stage 4 — Decision / Allocation Engine: NOT STARTED.

Stage 5 — Performance Evaluation: NOT STARTED.

AI-Assisted Planning: FUTURE.

Scenario Planning implementation has not yet begun.

### Next Step

Stage 1 — Planning Data Design: define and validate the canonical Planning Snapshot contract and its source-field mappings. Do not begin scenario generation or allocation until that contract is agreed.
