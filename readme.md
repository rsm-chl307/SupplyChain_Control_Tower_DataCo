# Supply Chain Control Tower Dashboard

An end-to-end supply chain analytics project that integrates demand, inventory, capacity utilization, and service-risk signals into an interactive Power BI control tower.

The dashboard is designed to help supply chain managers identify operational risks, trace their potential drivers, and prioritize products and plants that require attention.

---

## Project Overview

Supply chain teams often monitor demand, inventory, production capacity, and service performance in separate reports. This project combines these operational signals into a single decision-support dashboard.

The dashboard follows a business-oriented analytical flow:

Executive Overview  
↓  
Demand Driver Analysis  
↓  
Inventory Risk Analysis  
↓  
Capacity Utilization Analysis  
↓  
Service Risk Root Cause Analysis  

The final page connects service-risk events with their underlying inventory and capacity conditions, helping users move from identifying a problem to understanding its likely driver.

---

## Business Questions

This dashboard is designed to answer the following questions:

- What is the current overall operational risk level?
- Which products are driving weekly demand?
- Which products have the fastest demand growth?
- Which products have insufficient inventory coverage?
- Which plants are approaching critical capacity utilization?
- Which products and plants have the highest service risk?
- Are service risks primarily driven by inventory shortages, capacity constraints, or both?

---

## Dashboard Pages

### 1. Executive Overview

Provides a high-level view of supply chain performance and operational risk.

Key metrics include:

- Capacity Utilization
- Capacity Alerts
- Inventory Alerts
- Service Risk Events
- Executive Risk Score
- Weekly Executive Risk Trend

![alt text](excutive_summary-1.png)

---

### 2. Demand Driver Analysis

Identifies products that contribute the most to demand and products with the fastest demand growth.

Key visuals include:

- Latest Week Top Demand Drivers
- Fastest Growing Products
- Weekly Demand Trend
- Product Detail Table

![alt text](image.png)

---

### 3. Inventory Risk Analysis

Monitors inventory coverage and identifies products that may fall below safety-stock levels.

Key metrics include:

- Days of Inventory (DOI)
- Safety Stock Days
- Coverage Ratio
- Inventory Status
- Reorder Risk

Key visuals include:

- Historical Inventory Risk Trend
- Inventory Status Distribution
- Inventory Coverage Ratio by Product
- Inventory Risk Detail Table

![alt text](image.png)

---

### 4. Capacity Utilization Analysis

Evaluates whether plant capacity can support current demand levels.

Key metrics include:

- Weekly Demand
- Weekly Capacity
- Available Capacity
- Capacity Utilization
- Capacity Status

Capacity status is categorized as:

- Critical
- Warning
- Normal

Key visuals include:

- Historical Capacity Utilization Trend
- Plant Status Distribution
- Plant Utilization Comparison
- Plant Capacity Detail Table

![alt text](image.png)

---

### 5. Service Risk Root Cause Analysis

Highlights service-risk events and connects them to potential operational drivers.

Key metrics include:

- Service Alert
- Service Risk Score
- Risk Driver
- Inventory Status
- Capacity Status

Key visuals include:

- Weekly Service Risk Alerts
- Service Risk Driver Distribution
- High Service Risk Detail Table
- Highest-Impact Service Risk Products

![alt text](image.png)

---

## Key KPI Definitions

| KPI | Definition |
|---|---|
| Weekly Demand | Total product demand within a plant-week |
| Capacity Utilization | Weekly Demand / Weekly Capacity |
| DOI | Inventory available expressed as days of demand coverage |
| Coverage Ratio | DOI / Safety Stock Days |
| Inventory Alert | Indicates whether inventory is below the defined safety-stock threshold |
| Capacity Alert | Indicates whether capacity utilization exceeds a defined threshold |
| Service Alert | Indicates a high-risk service event |
| Service Risk Score | Composite score used to prioritize service-risk events |
| Risk Driver | Primary operational driver associated with service risk, such as Inventory, Capacity, or Inventory + Capacity |

---

## Data Structure

The project uses weekly simulated supply-chain data at the product, plant, and date level.

The primary analytical grain is:

`Product × Plant × Week`

Main datasets include:

- `capacity_utilization_weekly.csv`
- `dashboard_root_cause_summary.csv`
- `executive_dashboard_summary.csv`
- `inventory_risk_weekly.csv`
- `service_risk_weekly.csv`
- `top_product_driver_weekly.csv`

---

## Tools Used

- **Python**
  - Pandas
  - NumPy

- **Power BI**
  - Data modeling
  - DAX calculated columns and measures
  - Interactive slicers and visual interactions
  - Conditional formatting

- **Data Pipeline**
  - CSV-based data preparation and dashboard integration

---

## Analytical Design Decisions

Several design choices were made to ensure that metrics are interpreted correctly:

- Alert fields are aggregated using `SUM` because they represent event counts or binary indicators.
- Ratio-based metrics such as Capacity Utilization, DOI, Coverage Ratio, and Demand Growth are displayed using `AVERAGE` in charts and are not summed.
- Trend charts are intentionally disconnected from the date slicer so users can view historical patterns while analyzing a selected week.
- Current-week visuals, including ranking charts, distribution charts, and detail tables, are connected to the date slicer.
- Service Risk Root Cause Analysis filters detail views to high-risk service events only.
- Products and plants are ranked by risk severity to prioritize operational attention.

---

## Repository Structure

```text
├── data/
│   ├── capacity_utilization_weekly.csv
│   ├── dashboard_root_cause_summary.csv
│   ├── executive_dashboard_summary.csv
│   ├── inventory_risk_weekly.csv
│   ├── service_risk_weekly.csv
│   └── top_product_driver_weekly.csv
│
├── notebooks/
│   └── supply_chain_data_preparation.ipynb
│
├── dashboard/
│   └── supply_chain_control_tower.pbix
│
├── images/
│   ├── executive_overview.png
│   ├── demand_driver_analysis.png
│   ├── inventory_risk_analysis.png
│   ├── capacity_utilization_analysis.png
│   └── service_risk.png
│
└── README.md

## How to Run

1. Clone this repository.

2. Open the Power BI file located in the `dashboard/` folder.

3. If prompted, update the data source paths to point to the CSV files in the `data/` folder.

4. Refresh the data model.

5. Use the date slicer to explore weekly operational conditions.

---

## Example Insights Enabled by the Dashboard

The dashboard can help users identify scenarios such as:

- A plant operating at critical utilization while supporting high-demand products.
- A product with low inventory coverage and elevated service risk.
- Service-risk events primarily driven by combined inventory and capacity constraints.
- High-demand products that should be prioritized for replenishment or capacity reallocation.
- Plants that may require workload balancing or capacity expansion.

---

## Limitations and Future Improvements

This project uses simulated data and simplified business rules. Future improvements could include:

- Incorporating actual production schedules and lead times.
- Adding supplier reliability and transportation disruption indicators.
- Adding forecast accuracy metrics.
- Introducing scenario analysis for demand surges or capacity disruptions.
- Creating automated alerts through Power BI Service.
- Adding drill-through pages for product- or plant-level investigation.
- Adding cost and revenue impact estimates for service-risk events.

---

## Author

Chen-Fan Lee

---

## Disclaimer

All data used in this project is simulated and created for portfolio and analytical demonstration purposes only.