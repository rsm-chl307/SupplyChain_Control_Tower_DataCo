# Portable planning CSV examples

- synthetic_demo/config.json: the existing synthetic fixture converted to portable CSVs. No DataCo files or ABC dependency. All inputs are synthetic.
- user_data/config.json: runnable example with arbitrary column names, SKU-A and leading-zero ID 001. Its sample values are synthetic; replace CSVs and mappings with your own data.
- templates/: nine header-only CSV templates. They are schemas, not fabricated zero-valued facts.
- dataco_reference/: optional DataCo adapter configuration with its owner-approved whitelist and separate synthetic planning assumptions. No historical replenishment is replayed.

Run either portable example from repository root:

    python -B -m src.run_planning --sequential-config examples/planning/synthetic_demo/config.json --output-dir tmp/planning_source_runs
    python -B -m src.run_planning --sequential-config examples/planning/user_data/config.json --output-dir tmp/planning_source_runs

Validate without running or writing planning outputs:

    python -B -m src.run_planning --sequential-config examples/planning/user_data/config.json --validate-inputs

Detailed fields, optional-input assumptions and limitations: [Planning CSV Inputs](../../docs/planning_csv_inputs.md).
