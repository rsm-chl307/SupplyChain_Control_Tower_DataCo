# Product Master Design

## Objective

Create a product master table to support demand monitoring, inventory planning, capacity allocation, and risk analysis.

## Source

DataCo Supply Chain Dataset

## Design Logic

The original dataset contains transaction-level order records.

To support control tower reporting, a dedicated product master table was created by extracting unique product attributes.

## Result

- 118 Unique Products
- 50 Product Categories
- 11 Departments

## Key Attributes

- Product Card Id
- Product Name
- Category Name
- Department Name

# Plant Master Design

## Objective

The original DataCo dataset does not contain manufacturing plant information.

To support capacity planning and bottleneck monitoring, a virtual manufacturing network was introduced.

## Plant Structure

### P1 - Consumer_Fab

Departments:
- Apparel
- Footwear

Business Characteristics:
- Consumer-oriented products
- Stable demand patterns
- High order volume

### P2 - Sports_Fab

Departments:
- Golf
- Outdoors
- Fitness

Business Characteristics:
- Equipment-oriented products
- Capacity-intensive operations
- Seasonal demand fluctuations

### P3 - Specialty_Fab

Departments:
- Fan Shop
- Technology
- Discs Shop
- Pet Shop
- Book Shop
- Health and Beauty

Business Characteristics:
- Specialty products
- Higher demand variability
- Diverse product portfolio

## Design Rationale

Departments were grouped based on product family similarity and demand profile.

The objective is to create a realistic manufacturing network capable of supporting capacity planning, bottleneck identification, and supply chain risk monitoring.

# Capacity Planning Design

## Objective

The original DataCo dataset does not contain manufacturing capacity information.

To support bottleneck monitoring and capacity planning, plant capacity was estimated using historical weekly demand.

## Methodology

Target Utilization = 85%

Weekly Capacity =

Average Weekly Demand / 0.85

## Business Assumption

Manufacturing plants are expected to operate at approximately 85% utilization under normal conditions.

The remaining capacity acts as a buffer against demand variability and operational disruptions.

## Result

| Plant | Capacity |
|---------|---------|
| P1 | 1028 |
| P2 | 956 |
| P3 | 805 |

