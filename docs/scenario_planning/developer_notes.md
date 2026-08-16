# Developer Notes — Scenario Planning Extension

## Purpose and Boundary

The existing DataCo-based Control Tower is the completed monitoring baseline. Its notebooks, processed CSV datasets, risk calculations, and Power BI dashboard remain unchanged. It answers what happened in demand, inventory, capacity, and service risk. Scenario Planning is a separate future planning layer that will reuse those outputs to evaluate what-if decisions.

## Target Architecture and Data Flow

```text
Existing Control Tower data
  → Planning Data Layer
  → Planning Snapshot (Plant × Product × Week)
  → Scenario Generator (adds Scenario)
  → Decision / Allocation Engine
  → Performance Evaluation
  → Decision Support
  → Power BI-ready outputs
```

The Planning Data Layer will map existing demand, inventory, capacity, ABC classification, and master data into a canonical representation. The Planning Snapshot is the stable baseline before scenario changes. Scenario outputs use the same weekly Plant × Product × Week grain with a Scenario dimension.

## Module Boundaries

- Scenario Generator applies approved demand and capacity assumptions; it does not allocate capacity.
- Decision / Allocation Engine operates on one shared `Scenario × Plant × Week` capacity pool and returns explainable allocation results.
- Performance Evaluation calculates service, utilization, backlog, and risk measures from allocation results.
- Decision Support converts evaluated results into transparent recommendations and root-cause views.
- Power BI consumes published outputs; it is not part of core business logic.

The initial allocation direction is deterministic and rule-based: calculate `Net Demand = max(Scenario Demand - Beginning Inventory, 0)`, rank by Priority descending, Net Demand descending, and Product ID ascending, then allocate `min(Net Demand, Remaining Capacity)`. This direction is documented only at Stage 0 and is not implemented here.

## Technical Assumptions and Constraints

Core modules should use Python, Pandas, and NumPy with type hints, clear interfaces, and no unnecessary frameworks. Engines must remain independent of CSV I/O; a pipeline or notebook may orchestrate reads and writes. Existing field names and source provenance should be preserved or explicitly mapped. Stage 1 must resolve whether planning capacity means total `Weekly_Capacity` or derived `Available_Capacity`, and whether absent product-week observations remain absent or become explicit zero-demand rows.

The two-week MVP excludes OR solvers, advanced forecasting, real-time or ERP integration, production deployment, and AI/RAG functionality. The modular boundary leaves room for future optimization or AI explanation layers to consume validated deterministic outputs without replacing the core planning rules.
