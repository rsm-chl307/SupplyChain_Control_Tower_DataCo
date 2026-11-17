# WP5 Unified Pipeline and Run Management

Version 1.0 • Proposed implementation specification • NOT STARTED / NOT AUTHORIZED.

Shared authorities: [rules](../02_business_rules.md), [contracts and KPI catalog](../04_data_contracts.md), [pending decisions](../09_pending_decisions.md), [test catalog](../08_testing_and_acceptance.md), [roadmap](../07_implementation_roadmap.md). These shared files are the sole formula/schema definitions; this WP adds scope and acceptance, not competing business defaults.

## 1 Objective

Make raw-to-dashboard results reproducible, isolated, fully validated and safely published with auditable assumptions.

## 2 Scope

Declared dependencies; unified orchestration entry; source hashes and assumption versions; Run_ID; manifests; stage gates; isolated writes; failure handling; complete-run publication; dashboard loading consistency.

## 3 Out of scope

No distributed platform, database, scheduler, production deployment, dependency installation during this task or silent overwrite of completed legacy artifacts.

## 4 Business rules

BR-PIPE-001, BR-PIPE-002, BR-PIPE-003, BR-VAL-001, BR-VAL-003, BR-SCN-001, BR-KPI-002, BR-UI-001.

## 5 Input data

Immutable raw/master inputs, approved versioned assumptions, scenario configs, environment identity and authorized output root.

## 6 Output data

DC14 run manifest and hashes; stage artifacts; DC13 reports; published DC15 views. Failed runs retained as failed/unpublished evidence, not successful data.

## 7 Data model

Run_ID at every artifact, manifest inventory of schema/grain/count/hash, distinct execution/validation/publication status. Isolated staging and explicit immutable publication selection.

## 8 Module dependencies

Contracts for IDs/statuses early; pure preparation WP2, sequential WP3 and KPI WP4 before complete integration. WP1 gates apply at every stage. Minimal infrastructure may be separately authorized earlier without implementing the entire WP.

## 9 Actual repository files affected

src/run_planning.py; src/planning_pipeline.py; dashboard/scenario_planning_app.py loader integration; tests/test_run_planning.py; tests/test_planning_pipeline.py; tests/test_dashboard_app.py; notebooks as read-only transformation sources; root readme.md instructions after actual completion.

## 10 New files proposed

src/run_management.py; src/upstream_pipeline.py; tests/test_run_management.py; one reviewed dependency declaration (requirements.txt or pyproject.toml, no new framework assumed).

## 11 Testing plan

T-PIPE-001/002/003; T-UI-001; T-REG-001. Fixed-input semantic reproducibility, unique runs for identical/different parameters, source mutation detection, stage failure injection, invalid artifact/hash, interrupted publication, stale pointer and same-run reads.

## 12 Acceptance criteria

One authorized entry regenerates required raw-to-dashboard data without hidden notebook history; dependency setup reproducible; every artifact matches manifest; no partial/failed run visible as published success; earlier runs/history preserved; UI selects one consistent published run.

## 13 Risks

Atomic directory/pointer semantics differ by filesystem; select and test one standard-library local mechanism before claiming safety. Unique IDs/timestamps are nondeterministic metadata, not numerical reproducibility defects.

## 14 Pending decisions

P01–P23 values needed for real integrated runs; technical storage/dependency format and status transition details reviewed at stage authorization. No new business choices inside orchestration.

## 15 Implementation complexity

High

## Early minimum versus full integration

Early prerequisite contracts: Run_ID, Schema_Version, assumption references, stage/report records and publication eligibility. If Stage 2/4 needs persisted artifacts or a live UI, separately authorize the minimal safe run writer/publisher and dependency declaration as WP5-min. Do not write new-format fixed files and defer identity to the end.

Full Stage 5: integrate selected raw field loading, master/reference checks, WP2 preparation, scenario generation, WP3 chronological simulation, independent validation, WP4 metrics and published dashboard artifacts. Existing notebooks remain baseline evidence; port necessary transformations into explicit pure functions rather than requiring users to uncomment cells.

Manifest source hashes include raw/master/assumption inputs. Assumption versions identify eligibility, factor reference, capacity recipe, initial state, receipt schedule, priorities, calendar and KPI definitions. Scenario parameters and shortage mode are immutable for a run.

Publication eligibility is evaluated against a declared stage-approved scope with required stages/artifacts/metrics fixed before execution. An early scope-complete fixture/view run is labeled as such and is not final D10 pipeline acceptance. Optional undecided metrics may be omitted with explicit NOT_EVALUATED status; missing mandatory policy/metric blocks the scope. Final program acceptance includes all mandatory D08 metrics and the complete raw-to-dashboard workflow.

Publication eligibility requires all mandatory stage execution and blocking validation checks complete. Missing policy/input is BLOCKED, not a warning that allows publication. A single final atomic mechanism promotes a complete artifact set or selects an immutable completed directory. On failure, preserve last valid published run; record failure detail and never reuse its identity for different content.

Dependency setup itself requires explicit authorization. Prefer existing Pandas/NumPy/Streamlit/Plotly plus standard library; no new orchestration framework is presumed.
