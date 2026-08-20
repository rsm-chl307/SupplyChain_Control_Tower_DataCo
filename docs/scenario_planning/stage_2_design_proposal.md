# Stage 2 — Planning Data Pipeline Design and Completion Record

## Original design proposal

Stage 2 converts the Stage 1 in-memory Planning Snapshot preparation into a reproducible pipeline. The approved flow is:

```text
Approved source datasets
  → source loading
  → src/planning_snapshot.py
  → full baseline validation
  → inclusive horizon filter
  → filtered snapshot validation
  → deterministic sort and output
```

The Stage 1 contract remains unchanged: Plant × Product × Week grain, sparse observations, `Weekly_Capacity` as the capacity pool, `Baseline_Available_Capacity` as context only, and no scenario fields.

## Approved horizon policy

The pipeline accepts `planning_start_week` and `planning_end_week`. Validation is strict:

- Missing start or end: hard failure.
- Invalid date: hard failure.
- Start after end: hard failure.
- Start before the available source range: hard failure.
- End after the available source range: hard failure.
- Selected range with no observations: hard failure.
- Sparse observations inside a valid range: warning only.

The available source range is reported in out-of-range errors. The pipeline does not clip, substitute, or adjust user parameters.

## Final approved implementation

The design was implemented with:

- `src/planning_pipeline.py` — source loading, Stage 1 composition, horizon validation/filtering, validation, deterministic sorting, and output writing.
- `tests/test_planning_pipeline.py` — focused unittest coverage.

The entry point is:

```python
run_planning_pipeline(
    data_root,
    planning_start_week,
    planning_end_week,
    output_path,
)
```

The full-range baseline remains protected at `data/processed/planning_snapshot.csv`. Horizon-specific outputs use:

```text
data/processed/planning_snapshot_{start}_{end}.csv
```

## Validation result

Example execution:

```text
Horizon: 2017-01-01 through 2017-12-31
Artifact: data/processed/planning_snapshot_20170101_20171231.csv
Rows: 1,977
```

Seven unittest methods passed. The suite covers valid and full-range horizons, missing/invalid/reversed/out-of-range/empty ranges, sparse preservation, exact schema, Stage 1 builder reuse, deterministic execution, output naming, and baseline protection. Python syntax checks passed. Source CSV hashes and the Stage 1 baseline artifact hash remained unchanged.

Stage 2 implementation is complete. No scenario generation, allocation, performance evaluation, or Stage 3 work was introduced.

## Next stage

Stage 3 — Scenario Generator.
