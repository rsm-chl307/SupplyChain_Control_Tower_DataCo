# Approved Decisions Register

Version 1.0 • Owner decisions dated 2026-11-17 • Direction approved; implementation NOT AUTHORIZED.

This file is the retained transcription of the owner's Route B decisions. [Business rules](02_business_rules.md) provide testable consequences. Missing values/methods remain [pending](09_pending_decisions.md).

| ID | Approved selection | Required direction | Explicit boundary / unresolved detail |
|---|---|---|---|
| D01 | B Complete Independent Validation Layer | Schema, numeric finiteness, canonical keys, referential integrity, source preservation, independent calculations, allocation priority/capacity, sequential inventory/backlog continuity and structured reports | Never use the production engine as its own expected-result oracle |
| D02 | C Dual Demand | Keep original records; Gross Demand = Qualified Demand + Excluded Demand; configurable status eligibility and exclusion reasons | Do not qualify all non-canceled records automatically; P01 whitelist. Retain historical Order Date unless separately approved |
| D03 | B Product Equivalent Workload | Product workload factors; quantity x factor; plant capacity/allocation in one workload unit; re-establish capacity; factor provenance/versions; future Plant x Product factors | Old capacities are not automatically compatible; synthetic assumptions labeled; P03–P05 |
| D04 | B Sequential Multi-week Simulation | Ending inventory becomes next opening inventory; production affects future state; backlog per policy; independent scenarios; receipts only at declared periods; quantity conservation | Independent weekly legacy results are not sequential plans; P07–P09/P16 |
| D05 | C Both shortage modes | Each scenario explicitly selects LOST_SALES or CARRY_FORWARD; do not mix lost sales with backlog | No default policy; sequencing/initial backlog unresolved |
| D06 | C Separate procurement and production | External procurement has explicit quantity/receipt period and uses no internal capacity; internal production is allocated through the engine, consumes workload, enters inventory in production period | No procurement optimization; receipt source/schedule P06 |
| D07 | A Same-week production | Allocated production can fulfill demand in the same week | No configurable multiweek lead times; extension boundary only |
| D08 | B KPI expansion | Gross, Qualified, Excluded Demand; Production Coverage Rate; Demand Fulfillment Rate; Backlog Rate; Available Workload Capacity; Allocated Workload; Capacity Utilization; Remaining Capacity; Unmet Workload; Inventory On Hand; DOI; Safety Stock; Stockout Exposure; External Receipts; Internal Production; Plant-Week Bottleneck; Priority Allocation Trade-offs; Alert Burden Index | Do not change frozen formulas silently. Production coverage differs from customer fulfillment. Rule-based exposure is not a validated probability or causal root cause |
| D09 | B Preserve five-page structure | Target pages: Executive Overview; Demand Analysis; Capacity Monitoring; Inventory & Service Risk; Scenario Planning. Improve definitions, aggregation, drill-down and decision support | No wholesale redesign; actual PBIX differs, exact migration mapping P20 |
| D10 | B Complete Pipeline + Run Manifest | Unified Raw-to-Dashboard workflow, declared reproducible dependencies, stage validation, unique Run ID, source hashes, assumption versions, scenario parameters, execution/validation statuses, isolated directories, safe publication/failure handling | Incomplete runs cannot be published as successful; infrastructure contracts may begin earlier than full WP5 integration |
| D11 | C Combined Stress Demonstration | Baseline; Demand Surge; Capacity Disruption; Combined Demand Surge + Capacity Disruption; explain bottlenecks, shortages, priority trade-offs, stock, backlog and fulfillment differences | +10%/-20% are candidates only; recalibrate after new workload/capacity baseline; never manipulate canonical baseline to force scarcity |

## Retained legacy baseline

Legacy ABC A/B/C maps to 3/2/1. Product ranking is Planning_Priority DESC, Net_Demand DESC, Product Card Id ASC. Single-plant eligibility/no cross-plant transfers remain the baseline: future plant-specific factors do not authorize multi-plant routing.

For legacy contracts only:
- Net_Demand = max(Scenario_Demand - Beginning_Inventory, 0).
- Allocated_Qty = min(Net_Demand, Remaining_Capacity), both in old quantity units.
- Backlog = Net_Demand - Allocated_Qty.
- Service_Level = allocated / net demand (1 if net demand is zero).
- Allocation_Rate = allocated / scenario demand (1 if demand is zero).
- Capacity_Gap = capacity - allocation, identical to remaining capacity.
- Utilization = allocated / deduplicated capacity (0 if capacity is zero).

Route B must add workload and obligation/state contracts rather than silently change the unit of a legacy column. The precise Route B secondary rank requirement is P14; cohort service sequence is P07/P08.
