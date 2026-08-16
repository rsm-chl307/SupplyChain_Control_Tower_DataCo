# Business Notes — Scenario Planning Extension

## Why Add Scenario Planning?

The existing Control Tower provides monitoring and diagnosis: it shows historical demand, inventory, capacity utilization, service risk, and likely drivers. Supply Chain planners also need to test decisions before conditions change. Scenario Planning adds a forward-looking view of how demand or capacity changes affect constrained production and customer service.

## Planning Decision Context

The decision is made at Plant × Product × Week. A plant has a shared weekly capacity pool, products compete for that pool, and inventory can satisfy part of demand before new capacity is allocated. The initial product priority is transparent ABC classification: A = 3, B = 2, and C = 1. This makes the business trade-off explicit when protecting higher-priority products leaves backlog for lower-priority products.

## Scenarios

- **Baseline:** preserves the Planning Snapshot and provides the comparison point.
- **Demand Surge:** increases scenario demand by a defined percentage to test resilience and expose bottlenecks.
- **Capacity Disruption:** reduces capacity for selected plants or weeks to simulate an operational constraint.
- **Priority Shift (optional):** changes priority assumptions to show how service outcomes change when business priorities change.

## KPIs and Trade-offs

The planning view should report scenario demand, allocated quantity, unmet demand/backlog, remaining capacity, utilization, product service level, plant service level, overall scenario service level, bottleneck status, and priority-product risk. These KPIs show which plant is constrained, which products are affected, how much demand cannot be served, and what service-level trade-off results from the allocation rule.

## Decision-Support Value

The objective is to compare scenarios consistently and answer: where is the bottleneck, which products are most exposed, why did service deteriorate, and what operational response should be evaluated? Root-cause analysis should connect scenario change to constraint, allocation outcome, and service impact. The initial system remains rule-based and explainable; OR optimization, real-time integration, machine learning, and autonomous AI are outside the MVP.
