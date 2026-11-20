# Planning CSV Inputs

The supported primary data modes are SYNTHETIC_DEMO and USER_DATA. Both produce the same CanonicalPlanningInputs bundle and run the same scenario generator, sequential planner, independent validator and KPI engine. DataCo is an optional USER_DATA reference profile; no DataCo dataset, directory or ABC file is required by the portable modes.

This is the authoritative implemented CSV intake contract. The broader Route B proposals remain planning history. Core sequential output schema remains sequential_v1.

## Quick start

Run the existing synthetic fixture through its portable CSV configuration:

    python -B -m src.run_planning --sequential-config examples/planning/synthetic_demo/config.json --output-dir tmp/planning_source_runs

Validate the runnable user-data example without allocating production or writing planning outputs:

    python -B -m src.run_planning --sequential-config examples/planning/user_data/config.json --validate-inputs

Run user data through the same engine:

    python -B -m src.run_planning --sequential-config examples/planning/user_data/config.json --output-dir tmp/planning_source_runs

Copy the [user example](../examples/planning/user_data/config.json), replace its CSV values, update its column mappings and provenance, and validate before execution. The supplied user example is itself synthetic example data, not a claim about a real company. Nine header-only [CSV templates](../examples/planning/templates) are also supplied.

Every CSV path is resolved relative to its configuration file. Absolute paths are supported. --data-root is only for backward-compatible legacy/reference calls; it is not required by either portable mode.

## Configuration and source semantics

Required configuration fields:

| Field | Contract |
|---|---|
| data_mode | SYNTHETIC_DEMO or USER_DATA |
| assumption_version | Nonempty string identifying the configuration/input assumption bundle |
| planning_interpretation | RETROSPECTIVE or USER_PROVIDED_PLAN; the latter accepts supplied future planning demand, not a generated forecast |
| planning_start_week, planning_end_week | Inclusive normalized Sunday week-ending dates |
| demand_format | WEEKLY or ORDER_LINES |
| files | Named CSV descriptors, described below |
| quantity_step | Explicit 0 for continuous product units, or a positive unit/pack step |
| allocation_policy | PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT |
| scenarios | Explicit Baseline and any additional configured scenarios |
| product_ids | Optional explicit string cohort; otherwise all mapped products |
| assumptions | Optional explicit fallbacks; absent business values are never guessed |

A file descriptor is a path or an object containing path, optional columns, encoding, provenance and version. Column mapping is **canonical name -> actual CSV column**. For example, the user example maps Product_ID to sku and Demand_Qty to units. It is not necessary to rename user files to DataCo headers.

Mappings must be one-to-one and may not create duplicate canonical columns. Identifiers are strings, case sensitive and nonempty, without surrounding whitespace. Values such as SKU-A, 001 and NA remain distinct and are preserved by the published-run loader. Do not convert identifiers to numbers in a spreadsheet. The final Product_ID ascending tie-break uses canonical string order in these portable modes; the separate legacy numeric-ID interface retains its original typing.

CSV numeric fields are converted explicitly to finite numeric values; quantities/capacities must be nonnegative, factors strictly positive, priorities integer-valued 1/2/3. No missing numeric value becomes zero.

Source classification:

- SYNTHETIC_DEMO labels every supplied source synthetic.
- USER_DATA defaults to USER_PROVIDED: this means supplied by the user, not independently verified historical fact.
- A file descriptor can explicitly label a synthetic, derived or reference input. Change SYNTHETIC_EXAMPLE in the working example when replacing it with actual user inputs.
- Generated fallback values are listed separately as SYNTHETIC_ASSUMPTION. Derived reconciliation/coverage values retain their basis.
- Exact input bytes, configuration, source paths and artifact hashes are recorded in each successful run manifest.

## CSV schemas

Optional means a column/file may be omitted, not that blank values in a supplied column are silently filled. Remove unused optional columns or provide valid values. If provided, quantity units must match the referenced product master. Product, plant and product-plant references are validated before simulation.

### products

[Template](../examples/planning/templates/products.csv)

Grain/key: one row per Product_ID.

| Column | Type / unit | Requirement |
|---|---|---|
| Product_ID | String | Required, unique |
| Product_Name | Nonempty string | Required |
| Quantity_Unit | String, e.g. EA | Required unless assumptions.quantity_unit is explicitly supplied |
| Planning_Priority | Integer 1/2/3 | Required unless a priorities file or explicit assumptions.planning_priority supplies it |

The current aggregate quantity KPIs require one quantity unit within a run's selected cohort. Mixed EA/kg/box cohorts are rejected; run separately or supply an explicit upstream conversion. No unit conversion is inferred.

Optional files.priorities contains Product_ID and Planning_Priority. It may use config.priority_value_mapping to map source classes to explicit 1/2/3. Do not supply priority in both places. ABC is not a universal requirement.

### plants

[Template](../examples/planning/templates/plants.csv)

Key: Plant_ID, nonempty unique string. Plant_Name is optional.

### product_plant_mapping

[Template](../examples/planning/templates/product_plant_mapping.csv)

Columns: Product_ID and Plant_ID, both master foreign keys. The current engine retains one production plant per product. Duplicate eligibility and alternate routing are rejected; plant-specific workload factors are outside this upgrade.

### demand — WEEKLY

[Template](../examples/planning/templates/demand.csv)

| Column | Type / meaning | Requirement |
|---|---|---|
| Product_ID | String product reference | Required |
| Plant_ID | String plant reference | Optional; derived from mapping when absent; validated against mapping when present |
| Week | Sunday-ending date | Required |
| Demand_Qty | Finite nonnegative product quantity | Required |
| Status | User-defined status | Optional subject to qualification rule below |
| Quantity_Unit | Product quantity unit | Optional, inherits master when absent |
| Coverage_Status | Defined coverage enum | Optional; derived from supplied qualified quantity when absent |

With Status, the source key is Plant x Product x Week x Status: different status totals can coexist and reconcile to one canonical product-week. Duplicate same-status totals are rejected. Without Status, the source key is Plant x Product x Week.

Status-bearing demand requires config.status_eligibility, an explicit status -> boolean map. Unmapped statuses fail by default. Only an explicitly configured unknown_status_policy=EXCLUDE may exclude unrecognized states; this is recorded. There is no universal spelling or interpretation of CANCELED, OPEN or RELEASED.

Without Status, the caller must declare qualification_basis=ALREADY_QUALIFIED_INPUT. Gross then refers to this supplied qualified population; exclusions outside that population are unavailable, not fabricated. This limitation is recorded. To analyze exclusions, supply status-separated weekly totals or order lines.

Canonical totals always reconcile:

    Gross_Demand = Qualified_Demand + Excluded_Demand

Coverage enums are OBSERVED_DEMAND, OBSERVED_ZERO, UNKNOWN and OUT_OF_SCOPE. The first two refer to data available in the declared input population; USER_PROVIDED_PLAN does not turn future plans into observed historical facts.

Missing weekly rows remain UNKNOWN. Provide an explicit zero row only when the period is known to have zero demand. UNKNOWN or in-horizon unavailable coverage blocks simulation. Extra rows outside the selected horizon are labeled OUT_OF_SCOPE.

### demand — ORDER_LINES

Use Product_ID, Order_Line_ID, Date, Quantity and Status. Order_Line_ID must be unique. Plant_ID and Quantity_Unit are optional as above. Date is the caller-mapped historical order/requirement date; it is aggregated into Sunday-ending weeks.

source_is_complete=true is an explicit source-coverage assertion. It permits derived no-order zeros only inside each product's first/last observed lifespan. The source's partial first/last weeks and periods outside the lifespan remain UNKNOWN. Without that assertion, missing order weeks do not become zero.

The optional DataCo profile uses this format with configurable raw field mappings. Its source/date spellings do not appear in the user CSV contract.

### weekly_capacity

[Template](../examples/planning/templates/weekly_capacity.csv)

Key: Plant_ID x Week. Required columns: Plant_ID, Week, Capacity and Workload_Unit. Capacity is finite nonnegative equivalent workload available before allocation, not remaining capacity or pooled raw item quantities.

Every selected plant-week must be explicitly supplied, including zero capacity. Repeated product-level capacities are rejected rather than summed. Workload_Unit must match the factors. Optional Factor_Version must match when supplied; otherwise the current factor association is recorded by the converted input. Capacity_Version is optional; bundle version identifies the supplied snapshot when absent.

An explicit capacity_calibration recipe can replace the file: start_week, end_week, target_utilization in (0,1], capacity_version. The baseline is qualified workload mean divided by the declared target, labeled synthetic demand-calibrated capacity. Old quantity capacities and utilization targets are never reused automatically.

### initial_inventory

[Template](../examples/planning/templates/initial_inventory.csv)

Key: Plant_ID x Product_ID. Required quantity: Beginning_Inventory, finite nonnegative in the product unit. It must cover every initialized item exactly once. Optional Week identifies the first planning bucket and must match planning_start_week.

Beginning_Backlog can be supplied here or in the separate backlog file, never both. Quantity_Unit is optional and validated when present. No subsequent historical inventory or replenishment rows reset carried state.

If the file is absent, only explicit assumptions.initial_inventory=ZERO creates a clearly labeled synthetic initialization.

### workload_factors — optional

[Template](../examples/planning/templates/workload_factors.csv)

Key: Product_ID. Columns: Product_ID, Workload_Factor (>0), Workload_Unit; optional Factor_Version and Quantity_Unit.

    Allocated_Workload = Internal_Production_Qty x Workload_Factor

Factor unit is workload per product quantity unit. Every selected product needs exactly one positive factor; one compatible workload unit/version is required. Missing file is allowed only with explicit assumptions.uniform_workload_factor and assumptions.workload_unit. This creates labeled synthetic factors, not actual manufacturing standards. No silent factor=1.

### external_receipts — optional

[Template](../examples/planning/templates/external_receipts.csv)

Key: Receipt_ID, or Scenario x Receipt_ID when Scenario is supplied. Columns: Receipt_ID, Plant_ID, Product_ID, Week and External_Receipts_Qty. Quantity_Unit is optional.

Week explicitly means the week supply is usable. Events cannot appear earlier and consume no internal production workload. Scenario, when present, must reference a configured scenario. An unscoped schedule applies independently to all scenarios. Out-of-horizon/cohort events are reported and excluded from that run.

An explicit empty schedule is valid. If the file is omitted, assumptions.external_receipts=NONE is required. This says no external supply is modeled; it is not a historical claim that procurement never occurred.

### opening_backlog — optional

[Template](../examples/planning/templates/opening_backlog.csv)

Key: Plant_ID x Product_ID. Quantity: Beginning_Backlog, finite nonnegative; Quantity_Unit optional. Provided balances must cover initialized items. Missing records are not zero.

If omitted and not supplied in initial_inventory, assumptions.opening_backlog=ZERO is required. LOST_SALES rejects nonzero opening backlog; CARRY_FORWARD serves old backlog before current demand within each product while retaining the configured product-priority allocation.

## Shared canonical interface

    from src.csv_planning_inputs import load_csv_planning_inputs
    from src.run_planning import run_csv_planning

    bundle = load_csv_planning_inputs(config, inputs_dir)
    outputs = run_csv_planning(config, inputs_dir=inputs_dir, output_root=output_root)

CanonicalPlanningInputs holds ledger, weekly demand, coverage, planning demand, initial state, receipts, factors, baseline/calendar capacity, scope and validation report. Both modes construct this exact type.

The existing internal Product Card Id label is retained as a compatibility alias for generic Product_ID. It accepts string SKUs; users never need to supply DataCo columns or integer DataCo IDs. The same downstream functions are used for every source.

The validation report includes sources/provenance, assumptions, derived-value bases, canonical keys/types, errors and unavailable capabilities. InputValidationError carries report. A blocked intake never publishes successful outputs. Input validation complements, rather than replaces, independent simulation-result validation.

Output loading verifies publication state, artifact hashes, run identity and schema. Failed/partial runs remain unpublished. Quantity stocks are terminal snapshots; workload pools are unique plant-week facts. No engine, scenario or KPI calculation is duplicated in the CSV or UI layer.

## Optional DataCo reference

[Configuration and limitations](../examples/planning/dataco_reference/README.md)

Only this profile defines COMPLETE/CLOSED/PROCESSING as qualified, forces CANCELED/SUSPECTED_FRAUD excluded, and excludes other statuses unless explicitly configured. The profile uses separate synthetic initial inventory and synthetic workload/capacity assumptions. Historical simulated replenishment is never read or replayed.

DataCo is not a third required engine mode: it is a USER_DATA reference configuration. Other user datasets can use entirely different status meanings and columns.

## UI scope and limitations

The existing Streamlit app starts in sequential mode with the portable synthetic config path. A configuration path can select USER_DATA; active mode, scope and input diagnostics are displayed. No DataCo data is loaded automatically.

The Streamlit interface implements multi-file CSV upload, templates, interactive canonical-to-source column mapping, explicit assumptions, readiness validation and the existing runner. CSV + JSON configuration, validation CLI and Python interfaces remain available. Phase 2 adds presentation-only English/Traditional Chinese labels and workflow guidance; canonical files and input rules are unchanged. No database, ERP integration, authentication, new dependency or ingestion platform was added.

The current calendar uses Sunday-ending weekly buckets, one plant per product and one quantity unit per aggregate cohort. The system does not infer missing demand, production standards, procurement history, forecasts or actual stock.
