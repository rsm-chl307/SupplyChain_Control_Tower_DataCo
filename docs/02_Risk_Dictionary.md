# Risk Dictionary

## Demand Risk

### Business Definition

Demand Risk refers to unexpected fluctuations in customer demand that may disrupt supply chain planning and execution.

### Business Impact

- Capacity Bottleneck
- Inventory Shortage
- Service Level Degradation

### Stakeholders

- Supply Chain Planner
- Manufacturing Planning
- Operations Manager

### KPI

#### Weekly Demand

Definition:
Total weekly order quantity.

#### Demand Growth Rate

Definition:
Week-over-week demand growth.

#### Demand Volatility

Definition:
Rolling 8-week coefficient of variation.

### Alert Logic

#### Demand Surge

Current Week Demand >
8 Week Average + 2 Std

Severity:
Medium

Recommended Action:
Review Capacity Allocation

#### Demand Spike

Current Week Demand >
8 Week Average + 3 Std

Severity:
High

Recommended Action:
Escalate to Planning Team

#### High Demand Volatility

CV > 0.30

Severity:
Medium

Recommended Action:
Review Safety Stock Strategy

## Capacity Risk

### Business Definition

Capacity Risk refers to the risk that production or operational capacity is insufficient to meet customer demand, resulting in bottlenecks, delayed fulfillment, and reduced service performance.

### Business Impact

- Production Bottlenecks
- Reduced Throughput
- Inventory Shortages
- Late Deliveries
- Customer Service Degradation

### Stakeholders

Primary Owner:

- Supply Chain Planner
- Manufacturing Planner

Secondary Owner:

- Operations Manager
- Plant Manager

### Key Business Questions

1. Is current demand approaching available capacity?

2. Which plants are at risk of becoming bottlenecks?

3. How much additional demand can be supported before capacity constraints occur?

4. Which products contribute most to capacity utilization?

### KPI

#### Capacity Utilization

Definition:
Percentage of available capacity currently consumed by demand.

Formula:

Capacity Utilization =
Demand / Available Capacity

#### Available Capacity

Definition:
Remaining capacity available after current demand allocation.

Formula:

Available Capacity =
Total Capacity - Demand

#### Bottleneck Index

Definition:
Relative workload concentration by plant.

Purpose:
Identify operational bottlenecks before service levels are affected.

### Alert Logic

#### Capacity Warning

Condition:

Capacity Utilization > 85%

Severity:
Medium

Recommended Action:
Review production schedule and capacity allocation.

#### Capacity Critical

Condition:

Capacity Utilization > 95%

Severity:
High

Recommended Action:
Escalate to planning team and evaluate overtime, outsourcing, or capacity expansion.

#### Bottleneck Alert

Condition:

Plant utilization exceeds network average by more than 15%.

Severity:
Medium

Recommended Action:
Rebalance workload across plants.

### Risk Relationships

Capacity Risk is primarily driven by:

* Demand Risk

Capacity Risk may lead to:

* Inventory Risk
* Service Risk

### Dashboard Components

* Capacity Utilization Trend
* Plant Utilization Comparison
* Bottleneck Monitoring
* Capacity Alert Summary

### Recommended Actions

* Reallocate production volume
* Increase production shifts
* Review demand prioritization
* Evaluate alternative production capacity

## Inventory Risk

### Business Definition

Inventory Risk refers to the risk that inventory levels become insufficient or excessive relative to customer demand, resulting in stockouts, excess inventory carrying costs, and reduced supply chain performance.

### Business Impact

* Stockout Events
* Lost Sales Opportunities
* Excess Inventory Carrying Costs
* Reduced Service Levels
* Increased Working Capital Requirements

### Stakeholders

Primary Owner:

* Supply Chain Planner
* Inventory Planner

Secondary Owner:

* Operations Manager
* Supply Chain Manager

### Key Business Questions

1. Are inventory levels sufficient to support future demand?

2. Which products are at risk of stockout?

3. Which products have excessive inventory exposure?

4. How many days of demand can current inventory support?

### KPI

#### Inventory Position

Definition:
Estimated available inventory after accounting for demand and replenishment.

#### Days of Inventory (DOI)

Definition:
Number of days current inventory can support future demand.

Formula:

Days of Inventory =
Current Inventory / Average Daily Demand

#### Stockout Risk

Definition:
Probability that inventory will fall below safety stock levels.

Purpose:
Identify products requiring replenishment actions.

### Alert Logic

#### Inventory Warning

Condition:

Days of Inventory < 14 Days

Severity:
Medium

Recommended Action:
Review replenishment plan.

#### Inventory Critical

Condition:

Days of Inventory < 7 Days

Severity:
High

Recommended Action:
Escalate replenishment priority.

#### Excess Inventory Alert

Condition:

Days of Inventory > 60 Days

Severity:
Medium

Recommended Action:
Review inventory reduction opportunities.

### Risk Relationships

Inventory Risk is primarily driven by:

* Demand Risk
* Capacity Risk

Inventory Risk may lead to:

* Service Risk

### Dashboard Components

* Inventory Position Trend
* Days of Inventory
* Stockout Risk Monitoring
* Excess Inventory Monitoring

### Recommended Actions

* Adjust replenishment plans
* Increase production allocation
* Rebalance inventory across regions
* Review safety stock strategy

## Service Risk

### Business Definition

Service Risk refers to the risk that customer orders are not fulfilled according to promised delivery commitments, resulting in reduced customer satisfaction, lower service levels, and potential revenue impact.

### Business Impact

* Late Deliveries
* Reduced Customer Satisfaction
* Lower Service Levels
* Customer Escalations
* Potential Revenue Loss

### Stakeholders

Primary Owner:

* Operations Manager
* Customer Fulfillment Team

Secondary Owner:

* Supply Chain Planner
* Supply Chain Manager

### Key Business Questions

1. Are customer orders being delivered on time?

2. Which regions experience the highest delivery delays?

3. Which products contribute most to service failures?

4. Are service levels deteriorating over time?

### KPI

#### On-Time Delivery Rate (OTD)

Definition:
Percentage of orders delivered on or before the scheduled delivery date.

Formula:

OTD Rate =
On-Time Orders / Total Orders

#### Late Delivery Rate

Definition:
Percentage of orders delivered later than scheduled.

Formula:

Late Delivery Rate =
Late Orders / Total Orders

#### Average Delivery Delay

Definition:
Average difference between actual delivery time and scheduled delivery time.

Formula:

Average Delivery Delay =
Actual Shipping Days - Scheduled Shipping Days

#### Service Level

Definition:
Overall fulfillment performance measured by successful and timely order delivery.

### Alert Logic

#### Service Warning

Condition:

Late Delivery Rate > 10%

Severity:
Medium

Recommended Action:
Review fulfillment process and logistics performance.

#### Service Critical

Condition:

Late Delivery Rate > 20%

Severity:
High

Recommended Action:
Escalate to operations management and investigate root causes.

#### Delivery Delay Alert

Condition:

Average Delivery Delay > 2 Days

Severity:
Medium

Recommended Action:
Review transportation and fulfillment bottlenecks.

### Risk Relationships

Service Risk is primarily driven by:

* Demand Risk
* Capacity Risk
* Inventory Risk

Service Risk directly impacts:

* Customer Satisfaction
* Revenue Protection

### Dashboard Components

* On-Time Delivery Rate
* Late Delivery Rate
* Delivery Delay Trend
* Regional Service Performance
* Top Service Risk Products

### Recommended Actions

* Prioritize delayed orders
* Reallocate inventory
* Expedite transportation
* Review fulfillment bottlenecks
* Escalate operational issues
