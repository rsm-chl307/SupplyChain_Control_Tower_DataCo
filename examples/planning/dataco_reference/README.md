# Optional DataCo reference demonstration

This profile is USER_DATA using configurable mappings. Only this profile defines COMPLETE/CLOSED/PROCESSING as qualified; CANCELED/SUSPECTED_FRAUD are forced excluded and other/unknown statuses default excluded. These spellings are not universal planning-engine rules.

Source orders are historical. The plant network, product-family relative workload factors, zero initial inventory, absent opening backlog/external receipts and demand-calibrated capacity are explicitly synthetic planning assumptions. Workload factor values are configurable provisional relative weights, not actual manufacturing standards. Initial inventory is separate; historical inventory/replenishment files are never read.

The selected 54-product cohort has covered source lifespans for the explicit 2017-01-01 through 2017-03-26 horizon. Cohort omissions are quantified in the manifest. Full-history reference ABC is retrospective and not an as-of backtest.

The 0.75 target utilization and +10%/-20% scenarios are explicit demonstration parameters in config.json, not immutable engine defaults. Capacity is recalibrated in the new workload unit; legacy quantity capacities are not reused. Source assumes a complete extract for within-lifespan no-order zeros; the extract alone does not prove operational zero demand.

Run only if the optional repository DataCo files are present:

    python -B -m src.run_planning --sequential-config examples/planning/dataco_reference/config.json --output-dir tmp/planning_source_runs

The synthetic_demo and user_data examples do not read any DataCo/reference files.
