# Stage 0 – Project Definition

## 1. Purpose

Stage 0 establishes the business objective, scope, decision context, architecture direction, and implementation boundaries for the Scenario Planning extension of the existing Supply Chain Control Tower.

This stage converts the previously defined project direction into a formal repository-level specification before implementation begins.

Stage 0 is documentation and project-definition work only.

No Scenario Planning engine, allocation logic, or AI functionality should be implemented during this stage.

---

## 2. Project Context

The project extends an existing Supply Chain Control Tower built using the DataCo Smart Supply Chain dataset.

The existing Control Tower already provides:

- Demand analysis
- Inventory analysis
- Capacity analysis
- Service-risk analysis
- Root-cause analysis
- Supply chain KPIs
- Power BI-based operational monitoring

The current system is primarily a monitoring and diagnostic system.

The new Scenario Planning module extends the Control Tower from:

Monitoring / Diagnosis

to:

Planning / Simulation / Decision Support

---

## 3. Business Perspective

The project should be designed primarily from a Supply Chain Planning perspective.

The planning problem is:

> When demand or capacity conditions change, how should constrained capacity be allocated across products, and what service-level and operational trade-offs result from that allocation?

The planning engine should support planners in evaluating alternative operating conditions before making operational decisions.

---

## 4. Primary Business Objectives

The Scenario Planning module should:

1. Simulate alternative demand and capacity conditions.
2. Identify potential capacity constraints and bottlenecks.
3. Allocate constrained capacity across products based on defined business priorities.
4. Quantify unmet demand and service-level impact.
5. Evaluate trade-offs between priority and non-priority products.
6. Support root-cause analysis of service degradation.
7. Provide decision-support outputs that can be consumed by Power BI.
8. Demonstrate practical Supply Chain Planning capabilities rather than focusing on machine-learning model accuracy.

---

## 5. Planning Decision Context

The core planning grain is:

> Plant × Product × Week

The planning horizon is weekly.

The planning engine should operate at Level 3 planning granularity:

- Plant
- Product
- Week

This level provides sufficient operational detail for demonstrating:

- Capacity allocation
- Product prioritization
- Bottleneck identification
- Service-level trade-offs
- Scenario comparison

while remaining feasible within the project timeline.

---

## 6. Scenario Planning Scope

The initial Scenario Planning module should support the following scenarios.

### 6.1 Baseline Scenario

Represents the original planning assumptions.

Demand and capacity remain unchanged from the planning snapshot.

Purpose:

- Establish baseline service level
- Establish baseline utilization
- Provide comparison point for other scenarios

---

### 6.2 Demand Surge Scenario

Increases demand according to a predefined scenario assumption.

Purpose:

- Test system resilience under demand pressure
- Identify capacity bottlenecks
- Quantify unmet demand
- Evaluate service-level degradation

---

### 6.3 Capacity Disruption Scenario

Reduces available capacity for selected plants/weeks.

Purpose:

- Simulate operational disruption
- Identify affected products
- Evaluate allocation trade-offs
- Quantify service impact

---

### 6.4 Priority Shift Scenario

Optional scenario.

Changes product priority assumptions to evaluate how allocation decisions affect service across product groups.

This scenario should only be implemented if it can be completed without compromising the core project timeline.

---

## 7. Planning Inputs

The Scenario Planning module should primarily reuse existing Control Tower datasets.

Primary planning inputs:

- `plant_product_weekly_demand.csv`
- `inventory_snapshot_weekly.csv`
- `capacity_utilization_weekly.csv`
- `product_abc_classification.csv`

Existing master/reference data may also be reused where required.

The source Control Tower datasets should not be unnecessarily modified.

The planning layer should transform them into a canonical planning representation.

---

## 8. Planning Snapshot

Before scenario generation or allocation, the system should create a Planning Snapshot.

The Planning Snapshot should establish a canonical planning dataset at:

> Plant × Product × Week

The snapshot should contain the information required for scenario generation and allocation, including at minimum:

- Plant_ID
- Product Card Id
- Product Name
- Week / Order_Date
- Baseline Demand
- Beginning Inventory
- Capacity context
- Product Priority

The exact definition of capacity available for planning must be formally resolved during Stage 1.

---

## 9. Product Priority

The initial product priority mechanism should use the existing ABC classification.

Mapping:

| ABC Class | Planning Priority |
|-----------|-------------------|
| A | 3 |
| B | 2 |
| C | 1 |

Higher priority products should receive capacity before lower-priority products under constrained-capacity scenarios.

The priority mechanism should remain rule-based in the initial implementation.

---

## 10. Capacity Allocation Concept

The initial planning engine should use a rule-based allocation approach rather than a mathematical optimization / Operations Research model.

The allocation engine should:

1. Determine scenario demand.
2. Determine scenario capacity.
3. Rank products by planning priority.
4. Allocate available capacity sequentially.
5. Calculate allocated demand.
6. Calculate unmet demand / backlog.
7. Calculate service level.
8. Calculate utilization.
9. Identify allocation risks and bottlenecks.

The purpose is to create an interpretable planning engine suitable for business discussion and interview explanation.

An OR / optimization model is explicitly not required for the initial two-week implementation.

---

## 11. Core Planning KPIs

The planning engine should support calculation of:

### Demand

- Scenario Demand
- Allocated Demand
- Unmet Demand
- Backlog

### Capacity

- Scenario Capacity
- Allocated Capacity
- Remaining Capacity
- Capacity Utilization

### Service

- Product Service Level
- Plant Service Level
- Overall Scenario Service Level

### Risk

- Capacity Bottleneck
- High Utilization
- Unmet Demand Risk
- Priority Product Service Risk

---

## 12. Decision Support Direction

The final system should move beyond simply reporting KPIs.

It should help answer questions such as:

- Which plants become bottlenecks?
- Which products are most affected?
- How much unmet demand occurs?
- How does prioritizing products change service levels?
- What service-level trade-offs occur between product groups?
- Which scenario creates the greatest operational risk?
- Which allocation decision provides the best operational outcome under the defined business rules?

The initial decision-support layer should remain rule-based and interpretable.

---

## 13. Root-Cause Analysis

Root-cause analysis should remain part of the planning solution.

The system should be able to trace service-level deterioration back to factors such as:

- Demand increase
- Capacity reduction
- Plant bottleneck
- Product priority
- Capacity allocation
- Unmet demand

The goal is to connect:

Scenario → Constraint → Allocation → Service Impact

---

## 14. Architecture Direction

The target architecture is:

Existing Control Tower Data
        ↓
Planning Data Layer
        ↓
Planning Snapshot
        ↓
Scenario Generator
        ↓
Scenario Snapshot
        ↓
Decision / Allocation Engine
        ↓
Allocation Results
        ↓
Performance Evaluation
        ↓
Decision Support
        ↓
Power BI

The architecture should be modular so that future AI-assisted functionality can be added without replacing the core planning engine.

---

## 15. Rule-Based Planning vs OR Model

The initial implementation should use a transparent rule-based planning engine.

The project does not initially require:

- Linear Programming
- Mixed Integer Programming
- Solver-based optimization
- Commercial optimization software

An Operations Research optimization layer may be considered as a future enhancement if additional time is available.

The initial priority is to build a reliable and explainable planning engine.

---

## 16. AI-Assisted Planning

AI is intentionally out of scope for the initial planning engine.

The project should first establish a deterministic planning engine.

Future AI functionality may be added as an extension, such as:

- RAG-based supply chain knowledge assistant
- Scenario interpretation
- Natural-language scenario creation
- Planning result explanation
- Root-cause explanation
- Decision recommendation
- Planner conversational interface

AI should consume and interact with the planning engine rather than replace its deterministic business logic.

---

## 17. Technology Constraints

The project should use free/open-source tools only.

Preferred technology stack:

- Python
- Pandas
- NumPy
- Jupyter Notebook where appropriate
- Power BI for visualization
- Git
- Docker

No paid optimization or AI platform is required.

---

## 18. Timeline

Target implementation timeline:

> Approximately two weeks of development time.

Therefore:

- Core functionality has priority.
- Architecture should remain simple.
- Refactoring should be minimized.
- Optional features should not block the core planning engine.
- AI functionality should only be added after the deterministic planning engine is working.

---

## 19. Scope

### In Scope

- Planning Snapshot
- Scenario generation
- Demand surge simulation
- Capacity disruption simulation
- Rule-based capacity allocation
- Product priority
- Unmet demand / backlog
- Service-level calculation
- Utilization calculation
- Bottleneck identification
- Root-cause analysis
- Scenario comparison
- Decision-support outputs
- Power BI integration

### Optional

- Priority shift scenario
- Additional allocation rules
- Advanced visualization
- Additional optimization logic

### Out of Scope for Initial Version

- Machine-learning demand forecasting
- Mathematical optimization / OR solver
- Real-time supply chain integration
- ERP integration
- Paid AI services
- Autonomous AI planning
- Production deployment
- Full conversational AI agent

---

## 20. Success Criteria

The Scenario Planning module is considered successful when it can:

1. Generate a valid planning snapshot.
2. Generate multiple scenarios from the same baseline.
3. Apply demand and capacity changes correctly.
4. Allocate constrained capacity according to product priority.
5. Calculate allocation, unmet demand, service level, and utilization.
6. Identify bottlenecks and service risks.
7. Compare scenarios consistently.
8. Produce outputs suitable for Power BI.
9. Explain the business logic clearly.
10. Provide a foundation for future AI-assisted planning.

---

## 21. Stage Roadmap

Stage 0 – Project Definition

Stage 1 – Planning Data Design

Stage 2 – Planning Data Pipeline

Stage 3 – Scenario Generator

Stage 4 – Decision / Allocation Engine

Stage 5 – Performance Evaluation

Future – AI-Assisted Planning

---

## 22. Stage 0 Deliverables

Stage 0 should produce documentation only.

Required deliverables:

1. Project definition
2. Business objectives
3. Scope and constraints
4. Scenario definitions
5. Planning decision context
6. Architecture direction
7. KPI direction
8. AI extension direction
9. Stage roadmap
10. Project journal entry

No production code should be created during Stage 0.