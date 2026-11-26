<!-- section:system_overview -->
## System Overview

Use this supply-chain planning demo to explore how demand, capacity, inventory, and shortages affect your plan. Prepare data, compare scenarios, and investigate results before deciding what to do. The same inputs and assumptions produce the same results. Review assumptions before making operational decisions.

### Purpose, users, and limits

Use the app to prepare and check your data, run planning scenarios, inspect risk signals, investigate published evidence, and compare two scenarios. Typical users are planners, supply-chain analysts, and reviewers familiar with their data sources and measurement units. The app does not infer missing demand, production standards, actual stock, or a preferred action.

### End-to-end workflow

1. Select a planning model. Use **Sequential weekly planning** for a multi-week inventory/workload trajectory. **Independent-week analysis** reproduces the separate independent-week workflow.
2. In Sequential Planning, either upload/map CSV inputs or provide an existing JSON configuration path. Review and validate input readiness.
3. Run planning only after reviewing READY status and explicit assumptions, or load a previously completed sequential planning results folder.
4. Inspect the selected scenario in Overview, Comparison, Allocation Detail, Planning Risk Summary, and Scenario Trade-off Analysis.
5. Download the published result files or selected evidence/comparison exports as needed.

### Navigation and language

Select English or 繁體中文 from the menu in the top-right corner. The interface and guide update together. Open or close the guide without leaving your planning work. Choose the planning model in the sidebar and use the result tabs to explore your results. Changing the display language does not change your data or planning results.

### Important concepts

Key performance indicators (KPIs) summarize results such as service and capacity use. CSV is a table file that spreadsheet software can open. ID means a record’s identifier. READY means required input checks passed; BLOCKED means issues must be corrected before planning. N/A means a measure is unavailable or not applicable. These checks do not constitute business approval.

### Limits to keep in mind

The app does not forecast demand, choose an optimal plan, connect to your business systems, or guarantee permanent file storage. Check your inputs and assumptions before relying on a result.

<!-- section:dashboard -->
## Dashboard

Use the older independent-week model to review available scenario results and product allocations. Use Sequential Planning when inventory and backlog must carry into later weeks.

### Inputs and operation

Choose Independent-week analysis in the sidebar. Start and end dates default to `2017-01-01` and `2017-12-31`. Demand increase defaults to 10% (minimum 0; no stated maximum). Capacity reduction defaults to 20% (0–100%). Select the affected plant from the available data.

Each date range has its own output folder. If it already exists, the Run button is disabled to protect saved files. The prepared 2017 results already exist. Do not change dates simply to bypass this protection.

### Results and interpretation

1. Scenario Overview shows service, capacity utilization, allocation rate, backlog, and status for the selected scenario.
2. Scenario Comparison shows results against Baseline. Differences between rates are shown in percentage points.
3. Capacity Allocation Detail shows product allocations for a selected plant and scenario. Shared plant-week capacity is counted once in summaries.

Some charts may be unavailable when chart support or data is missing. The older Service Level is allocated quantity divided by net demand. It measures allocation coverage, rather than on-time delivery or Sequential Horizon Service Level. Weeks are independent: do not assume inventory or backlog carries forward.

<!-- section:planning -->
## Planning

Use Sequential Planning to explore how demand, available stock, receipts, priorities, and plant capacity affect results across several weeks. It produces scenario results rather than a demand forecast or a recommended plan.

### Choose a model and prepare inputs

Sequential weekly planning is the default. It carries ending inventory and backlog into the next week and uses shared workload capacity for each plant and week. Independent-week analysis allocates quantity separately each week without carrying inventory or backlog forward.

- Upload CSV data: download templates, upload your files, match columns, classify demand, and check the results before running planning.
- Use existing JSON configuration: JSON is a text settings format. Use this option if someone has prepared a settings file. Enter its location on the computer running the app; files on your own computer are not automatically available to a hosted app. There is no JSON upload button.
- Load a Published Run: enter the folder containing completed Sequential Planning results. Include the planning record (`run_manifest.json`) and all result files. Opening saved results does not run planning again.

### CSV files and column matching

CSV files are tables you can open in spreadsheet software. Download templates first. Match each required field to one distinct column with the correct meaning. Check suggested matches rather than accepting them by name alone. Keep the spelling and capitalization of fields shown below.

| Dataset | Required fields | Optional fields or instructions |
|---|---|---|
| Products | `Product_ID`, `Product_Name` | `Quantity_Unit`, `Planning_Priority` |
| Plants | `Plant_ID` | `Plant_Name` |
| Product to plant mapping | `Product_ID`, `Plant_ID` | Supported product/plant relationships |
| Demand — WEEKLY | `Product_ID`, `Demand_Qty`, `Week` | Plant, Status, unit, source references; classify statuses or confirm already-qualified demand |
| Demand — ORDER_LINES | `Product_ID`, `Order_Line_ID`, `Date`, `Quantity`, `Status` | Classify every status and confirm complete coverage of the stated period |
| Optional planning priorities | `Product_ID`, `Planning_Priority` | Use only when Products does not already provide priorities |
| Weekly workload capacity | `Plant_ID`, `Week`, `Capacity`, `Workload_Unit` | Capacity and factor versions; compatible units |
| Product workload factors | `Product_ID`, `Workload_Factor`, `Workload_Unit` | Factor version and quantity unit; positive factors |
| Initial inventory | `Plant_ID`, `Product_ID`, `Beginning_Inventory` | `Week`, `Quantity_Unit`, `Beginning_Backlog`; Week must be the first planning week |
| Opening backlog | `Plant_ID`, `Product_ID`, `Beginning_Backlog` | `Quantity_Unit`; avoid duplicating backlog in Initial inventory |
| External receipts | `Receipt_ID`, `Plant_ID`, `Product_ID`, `Week`, `External_Receipts_Qty` | Scenario and quantity unit; Week is when receipts become usable |

Products, Plants, Product to plant mapping, and Demand are always required. Supply other datasets unless you explicitly select their supported assumption. Product/plant identifiers and measurement units must agree across files. Missing rows do not prove zero demand.

Choose WEEKLY for demand summarized by Sunday-ending week; choose ORDER_LINES for dated individual orders. Qualified means included in planning; Excluded means left out. Classify every demand status. Weekly data without Status needs confirmation that all demand is already qualified. Order-line data also needs confirmation that it includes all orders in the stated history. USER_PROVIDED identifies who supplied data; it does not independently verify accuracy.

### Planning settings and assumptions

The following defaults and entry ranges are provided by the current form. Input checks also verify dates, numbers, identifiers, coverage, and units.

| Setting | Unit, default, and range | Effect and example |
|---|---|---|
| First / last planning week | Sundays; suggested from demand, otherwise both next Sunday; start no later than end | Defines planning horizon, such as four consecutive weeks |
| Demand interpretation | USER_PROVIDED_PLAN by default, or RETROSPECTIVE | Use supplied planning demand or replay historical demand; neither creates a forecast |
| Planning settings name | Required text; default `streamlit-user-upload-v1` | Names the settings saved with results, e.g. `FY27-weekly-plan-v1` |
| Product quantity step | Quantity units; default 0, minimum 0, no form maximum | 0 allows continuous quantities; 5 uses 5-unit production increments |
| Demand surge | Percent; default 10%, minimum 0, no form maximum | Increases demand in Demand Surge and Combined Stress; 10% means multiplying by 1.10 |
| Capacity reduction | Percent; default 20%, 0–100% | Reduces selected plants’ capacity in Capacity Disruption and Combined Stress |
| Affected plants | Multiple selections; first available plant selected by default | Limits the capacity reduction to selected plants |
| Shortage policy | CARRY_FORWARD by default, or LOST_SALES | Carry unfulfilled obligations forward, or discard current-week unserved demand; Lost Sales requires zero opening backlog |
| Fallback quantity unit | Text, empty by default | Needed when product units are missing; enter the actual unit, such as case |
| Assumed priority | Off by default; value 2, options 1–3 | Use only when priorities are absent; 1 lower, 3 higher |
| Uniform workload factor | Off; default 1.0, minimum 0.000001, entry step 0.25; unit EqWU | Assumed workload per quantity unit, rather than measured production standard |
| Zero initial inventory | Off | Explicitly assumes zero stock when the inventory file is missing |
| Zero opening backlog | Off | Explicitly assumes zero missing backlog; does not erase supplied balances |
| No external receipts | Off | Explicitly assumes no modeled external receipts when the file is missing |
| Synthetic capacity target utilization | Off; default 0.75, range 0.01–1.00, step 0.05 | Estimates capacity from qualified demand and target utilization; clearly labeled as assumed rather than measured capacity |

### Check inputs and run planning

1. Correct file-reading errors and duplicate column names.
2. Confirm column matches and demand classification.
3. Set the Sunday dates, demand interpretation, scenarios, and assumptions.
4. Select Validate inputs. READY means required checks passed; review warnings and assumptions too. BLOCKED lists issues to correct. Checking inputs does not create results.
5. Select Validate and run planning only after reviewing READY. The app checks again and saves completed results if planning succeeds. A failed attempt is not a completed result.

CSV planning prepares Baseline, Demand Surge, Capacity Disruption, and Combined Stress. Review the Run ID and folder shown after success. Download `performance_result.csv`, `allocation_result.csv`, and `run_manifest.json` to keep your own copy.

### Interpret and save results

Select a scenario and inspect Overview, Scenario Comparison, Capacity Allocation Detail, Planning Risk Summary, and Scenario Trade-off Analysis. Selecting a scenario changes the view without running planning again. Use the glossary to interpret units and indicators.

Do not add ending inventory or backlog across weeks. Under CARRY_FORWARD, shortages remain as backlog; under LOST_SALES, unserved current demand is discarded. Zero backlog under LOST_SALES does not mean all demand was served.

Avoid treating READY as business approval, mixing quantity with workload, counting opening backlog twice, or assuming missing weeks mean zero demand. Saved files are checked for completeness and changes. Original inputs may be unavailable even when saved results can still be viewed. Cloud restarts or app updates may remove generated files; download important results.

<!-- section:wp1 -->
## Operational Risk Investigation

Investigate product, plant, and weekly observations to understand possible operational issues. The observations help focus a review but do not establish causal responsibility.

### Open and select an investigation

Load completed Sequential Planning results, open Planning Risk Summary, and choose Product Risk, Plant Bottlenecks, Scenario Risk, or Root Cause Investigation. These are the current screen labels. Product/plant risk actions and Scenario Trade-off Analysis can preselect a product and scenario for investigation.

Choose a product, plant, and Sunday-ending week as requested. You need saved results and available supporting records for those selections. If a record is unavailable, check its source message rather than treating it as zero.

### Read evidence and download details

Inspect the selected product/week, shared plant-week capacity, related observations, adjacent weeks, and other products using the same capacity. Each table keeps the level of detail recorded in its source: a plant-week total must not be treated as a product-specific quantity. Download the relevant supporting records to inspect detail.

Export fields beginning with `Investigation_` describe your selected filters. They do not change the detail of original records. Weekly row identifiers are not necessarily customer order numbers; extra scenario demand does not represent newly identified source orders.

### Interpret findings carefully

Priority, workload, shared capacity, and another product’s shortage are review signals, not proof that one product caused another’s result. Product quantities and plant workload use different units. Do not add ending inventory or backlog across weeks. If original inputs are missing or changed, the app may still show checked saved evidence and warn about source availability; it does not invent replacement source records.

<!-- section:wp2 -->
## Scenario Comparison

Compare two scenarios within the same completed Sequential Planning results to understand service and workload trade-offs. The app describes differences; you decide which outcomes matter.

### Choose scenarios and products

Open Scenario Trade-off Analysis, the current result-tab label. Choose Reference Scenario (your baseline) and Candidate Scenario (the alternative). No baseline is chosen automatically, and the candidate must differ from the reference.

Choose zero or more priorities from 1–3 to define a product group. ALL includes all products, SELECTED matches your chosen Reference priorities, and COMPLEMENT contains the rest. Membership remains based on Reference even if Candidate priorities differ. No selected members can produce N/A. Comparison covers the full saved planning period, products, and included plants.

### Read measures and comparison warnings

Review Horizon Service Level, Terminal Backlog, Lost Sales, Allocated Workload, and Unmet Workload for each group. Expand reasons and supporting references before relying on a difference. Definitions and units are in the glossary.

Delta equals **Candidate − Reference**. Service differences use percentage points: 60% to 75% is +15 percentage points. Quantity and workload differences keep their own units. A positive value is not always better; additional backlog can be undesirable.

COMPARABLE means comparable; DESCRIPTIVE_ONLY means describe with limitations; BLOCKED means comparison is prevented; POLICY_CONTRAST indicates different shortage policies; N/A means unavailable or not applicable. Read the reason next to each measure. Zero backlog under LOST_SALES does not itself show better service.

### Continue investigation and download results

Select a product and choose Reference or Candidate for further investigation. This preselects the product and scenario in the investigation view without running planning. Download comparison measures, product-group membership, supporting references, and comparison settings. File identifiers keep each comparison separate; changing language does not change exported data.

### Common mistakes

Do not assume Baseline is selected automatically, redefine membership using Candidate priorities, confuse percentage points with percent changes, or read a blocked measure without its reason. Check the unit, product group, and meaning of each measure before interpreting the sign of Delta.

<!-- section:data_reports -->
## Data Management and Reports

Prepare files, reopen completed results, and download reports. Keep your own copy of important data; the demo does not guarantee permanent storage.

### Prepare and protect inputs

Download CSV templates and check each column match, unit, identifier, data coverage, and assumption. Uploads are held for preview and input checks, then temporarily saved while planning executes. Do not upload confidential or personal data to a public demo.

### Open completed results

Each completed execution has a unique Run ID, saved settings, checks, and results. Enter the folder containing all results, including the planning record `run_manifest.json`. Failed or incomplete executions are not completed results. Do not rename or edit files to bypass warnings; ask the person who prepared them for a complete copy.

### Download and save reports

Sequential Planning offers `performance_result.csv` (performance summary), `allocation_result.csv` (allocation details), and `run_manifest.json` (planning record). Investigation downloads contain selected supporting records. Comparison downloads cover measures, product groups, references, and settings. The independent-week Dashboard displays its own tables and charts.

Language changes do not change CSV headings, identifiers, scenario values, statuses, or data. Keep original exported values when processing files further. Temporary files on your computer or Community Cloud can disappear after restart or update. This demo does not provide permanent storage, sign-in, or separate private storage for each user; do not use it as a production record system.

<!-- section:kpi_glossary -->
## KPI and Terminology Glossary

Key performance indicators (KPIs) summarize planning performance. Read the week and scope shown with each value. N/A means a measure cannot be calculated or is not applicable. The independent-week model uses separate definitions.

### Service and demand measures

| Term | Definition and unit | Interpretation and limit |
|---|---|---|
| Horizon Service Level (`Horizon_Service_Level`) | Demand originating in the planning period served by its end, divided by total qualified demand originating in that period; ratio | Includes later service within the period, excludes opening backlog; not an on-time rate |
| Weekly Service Level (`Weekly_Service_Level`) | Current-week demand served that week divided by current-week demand; ratio | Does not credit later recovery; zero demand gives N/A |
| Production Coverage Rate | Internal production divided by calculated production requirements; ratio | Inventory and receipts may satisfy demand without production; not a demand-service measure |
| Current Unfulfilled Quantity | Current-week demand not served that week; quantity | May be served later; differs from terminal backlog |

For demand of 8 with 5 served that week, Weekly Service Level is 62.5%. If all remaining 3 are served later within the planning period, Horizon Service Level can reach 100%; the weekly result stays 62.5%.

### Capacity, stock, and shortages

| Term | Definition and unit | Interpretation and limit |
|---|---|---|
| Capacity Utilization | Allocated workload divided by available workload capacity; ratio | Shows capacity use; count each shared plant-week capacity once; zero capacity gives N/A |
| Allocated Workload | Internal production quantity multiplied by product workload factor; workload units | Receipts do not consume this workload; units and factor versions must agree |
| Unmet Workload | Uncompleted production requirement converted to workload units | Can be totaled over weeks; differs from terminal backlog |
| Backlog | Unfulfilled obligations carried under CARRY_FORWARD; quantity | Check the week; never add ending balances across weeks |
| Ending Inventory | Usable stock left after receipts, production, and fulfillment; quantity | Never add across weeks; no automatic replenishment or safety-stock target |
| Lost Sales (`Lost_Sales_Qty`) | Current demand unserved and discarded under LOST_SALES; quantity | Not lost revenue; zero under CARRY_FORWARD does not prove no shortage |

### Planning and comparison terms

**Planning scenario (Scenario)**

A named set of demand, capacity, and shortage-policy assumptions within one planning execution. Compare scenarios to see how different conditions affect results.

**Planning execution (Run)**

One execution saves its settings and results under a unique Run ID. Loading results does not run planning again.

**Reference / Candidate**

Reference is your chosen comparison baseline. Candidate is the alternative. Delta equals Candidate minus Reference.

**Product group (Cohort)**

ALL includes all products. SELECTED matches chosen Reference priorities; COMPLEMENT contains the rest.

**Percentage point**

A change from 60% to 75% is an increase of 15 percentage points.

**Independent-week Service Level**

Allocated quantity divided by net demand in the independent-week model. It measures allocation coverage rather than Sequential Horizon Service Level.

<!-- section:troubleshooting -->
## Troubleshooting and FAQ

Use the readiness errors and source-status details as the first diagnostic. A missing or unavailable input must not be silently replaced with zero unless the exact explicit assumption is offered and selected.

### Missing inputs or BLOCKED readiness

Confirm the four always-required CSV datasets are present. For each other missing dataset, either provide its CSV or select the specific supported assumption. Read the full error list and the assumptions/source section. A declared zero inventory/backlog or no receipts is a modeling assumption, not discovered historical truth.

### Invalid CSV or mapping errors

Check that the file has a header and rows, unique column names, readable encoding, correct WEEKLY/ORDER_LINES shape, one-to-one source mappings, finite nonnegative quantities, valid dates, compatible units, and unique product, plant, and week combinations. Re-map columns whose names look similar but mean something different. Do not use an identifier column as a quantity field.

### Demand status or horizon problems

Every source status must be classified. Status-free WEEKLY input requires the explicit already-qualified declaration. Dates must be Sundays and start must not exceed end. ORDER_LINES needs the explicit complete-history assertion even when status values are also classified; do not claim partial order lines are complete.

### Capacity or factor assumptions

Provide compatible Weekly workload capacity and Product workload factors, or select the supported explicit factor and/or synthetic capacity assumptions. Synthetic capacity is calculated from qualified demand and the target utilization, then labeled as an assumption; it is not measured production capacity.

### Planning did not run or failed

Validation and execution are separate actions. BLOCKED readiness prevents a run. If execution fails, read the localized summary and technical detail, verify paths and input files, and correct configuration before trying again. Check that the destination is writable and that the run is not using a Independent-week path. A failed attempt is not a published result.

### Published Run not found or evidence unavailable

Enter the folder containing completed planning results, rather than a single CSV or its parent folder. Include the planning record (`run_manifest.json`) and all required results. Ask the person who prepared them for the folder location on the computer running the app. Missing original inputs may limit investigation even when saved results can still be viewed.

### Operational Risk Investigation has empty results

Confirm the selected Run/scenario/product/plant/week has evidence at the level of detail recorded in the selected file. Empty rows do not prove zero demand or zero risk. Check source availability/hash messages and whether the selected item belongs to the Run scope.

### Scenario Comparison is blocked or hard to compare

Select distinct Reference and Candidate scenarios from the same loaded Run. Review the metric comparability reasons, policy contrast, input differences, and fixed Reference cohort. N/A means unavailable at that calculation or level of detail; BLOCKED or DESCRIPTIVE_ONLY requires reading its reason. No automatic scenario preference is produced.

### Language, guide navigation, and pending form values

Choose a language from the top-right menu. Your selected guide section stays open, and you can return to your unfinished planning form after reading the guide. If a value disappears, do not run planning. Record the field name and steps taken, then ask for help before continuing.

### Common mistakes checklist

- Assuming a missing row means zero demand.
- Treating data sources or synthetic labels as independent truth validation.
- Comparing Independent-week and Sequential KPIs as if they shared one formula.
- Summing inventory/backlog stocks across weeks.
- Treating a risk observation as a causal attribution.
- Reading Scenario Comparison Delta without its sign, unit, cohort, and comparability reason.
- Assuming an upload, validation result, generated Run, or Cloud file is permanently stored.
