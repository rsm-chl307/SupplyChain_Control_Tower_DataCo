# Controlled Implementation Roadmap

Version 1.0 • Planning only • No development stage authorized.

## Critical path and gates

Owner review/Stage 0 freeze -> WP1 foundation -> approved WP2 demand/workload -> approved WP3 sequential state -> WP4 metrics/views -> WP5 complete raw-to-dashboard publication -> WP6 demonstration.

Run_ID/schema/manifest contracts are designed before implementation. WP5-min dependency declarations and minimal safe run infrastructure may be explicitly authorized earlier where a stage needs persisted artifacts or live loading. That does not authorize full pipeline integration or new business rules early.

Foundation work is not blocked by every pending business choice. Each stage has local gates. A missing approved whitelist blocks qualified demand outputs, for example, but not legacy finite-value validation.

## Stage 0 Specification and Business Rules Freeze

- Prerequisites: current repository inspection and owner D01–D11 direction.
- Work packages: all six at documentation level only.
- Files affected: docs/improvement_program and temporary completion report; small scope notices in readme.md, ai_agent_implementation_spec.md, developer_notes.md and project_journal.md.
- Tasks: review exact approved/pending rule separation, contracts, file map, conflicts and P01–P23; record owner resolutions where available.
- Deliverables: permanent v1.0 specification package and owner review record.
- Testing requirements: internal links, BR/test/WP cross references, canonical dataset names, formula consistency and protected-file hashes.
- Acceptance criteria: owner agrees scope/technical direction and identifies which pending decisions gate each stage. Unresolved sections remain explicitly Pending.
- Exit conditions: explicit owner specification review/freeze; subsequent implementation authorization remains separate.
- Complexity: Medium.
- Current status: documentation prepared for review; owner freeze not yet granted.

## Stage 1 WP1 Validation Foundation

- Prerequisites: separate Stage 1 authorization; legacy frozen rules and structured report/schema agreement.
- Work packages: WP1; optionally separately scoped WP5-min contracts, not full WP5.
- Files affected: allocation_validator.py; snapshot validation boundaries; proposed data_contracts.py, validation_report.py, test_independent_validation.py; existing allocation tests. Exact list is in WP1.
- Tasks: finite/type/key/reference/source validation, independently recomputed net demand/greedy order/running capacity, structured outcomes and negative tests.
- Deliverables: independent legacy validation foundation and Route B check contracts, with continuity checks explicitly deferred until WP3 inputs exist.
- Testing requirements: T-VAL-001–003, T-REG-001; all reviewed corruption probes; normal/constrained/zero/inventory-covered/deterministic cases.
- Acceptance criteria: reject corruption for intended independent reasons without calling engine for expected results.
- Exit conditions: foundation passes independent acceptance; no claim that the entire sequential D01 layer is complete.
- Complexity: Medium.
- Local pending gates: P13 for real Route B numeric tolerance; P07/P08/P14/P16 not prerequisites for validating unchanged legacy arithmetic.

## Stage 2 WP2 Demand and Capacity Model

- Prerequisites: WP1 foundation; approved P01/P03/P04/P05/P12 and relevant P02/P13/P16/P17 input conventions; separate implementation authorization.
- Work packages: WP2, WP1 validation extensions; WP5-min metadata/output support when needed.
- Files affected: planning_snapshot.py/planning_pipeline.py Route B input paths; proposed demand_preparation.py, workload_model.py, test_demand_capacity.py; shared contracts. Historical notebooks remain references.
- Tasks: status eligibility ledger, dual demand reconciliation, workload factor resolution/provenance, workload capacity calibration, source/coverage lineage and approved priority-input version.
- Deliverables: validated versioned inputs DC01–DC06 and the DC07 schema contract only, no changed legacy artifacts. Populated DC07 initial state additionally requires P09/P12/P23 approval and belongs to the WP3 input gate; it is not implicitly delivered with invented stock.
- Testing requirements: T-DMD-001–003; T-CAP-001–003; coverage and many-to-one join checks; source preservation.
- Acceptance criteria: no unknown statuses/factors silently accepted; compatible approved workload reference; reproducible capacity recipe; sparse demand facts retained.
- Exit conditions: owner accepts demand/factor/capacity assumptions and test evidence. WP3 may not consume placeholder business values.
- Complexity: High.

## Stage 3 WP3 Sequential Planning Engine

- Prerequisites: accepted WP2 inputs; resolved P06–P09/P13/P14/P16/P18/P19/P22/P23 as relevant; Stage 3 authorization.
- Work packages: WP3 and final WP1 sequential/allocation checks.
- Files affected: existing allocation/scenario/snapshot interfaces plus proposed inventory_engine.py, sequential_planner.py, inventory_validator.py, test_sequential_planning.py.
- Tasks: explicit opening state, chronological scenario/week/plant processing, workload group allocation, same-week production, external events, fulfillment attribution, loss/carry policies and complete independent conservation.
- Deliverables: DC11/12 facts, scenario isolation evidence and structured independent validation reports.
- Testing requirements: hand-calculated multiweek cases; T-SEQ-001–005; T-BKL-001–004; T-RCP-001; T-ALLOC-001/002; scenario-order independence.
- Acceptance criteria: exact approved stock/obligation/workload balances; no early receipts, shared state, weekly resets or demand invented in unknown gaps.
- Exit conditions: both shortage modes pass; all applicable D01 sequential checks pass; legacy regression results preserved.
- Complexity: High.

## Stage 4 WP4 KPI and Dashboard Enhancement

- Prerequisites: accepted sequential facts, approved P10/P15/P20/P21 and cohort/priority conventions; Stage 4 authorization. Published-run support WP5-min must exist before a live loader is accepted.
- Work packages: WP4 plus independent metric validation; WP5-min only if explicitly included.
- Files affected: KPI/evaluator/performance manager, Streamlit, approved PBIX pages, KPI/dashboard tests and contract outputs.
- Tasks: approve DC15 formulas; expose distinct flow/stock/cohort/workload metrics; fix aggregations; implement exact approved five-page mapping; show published Run_ID and active assumptions.
- Deliverables: grain-specific KPI outputs and reconciled five-page experience.
- Testing requirements: T-KPI-001–003, T-UI-001, T-REG-001; selected-week/multiweek/grain, zero denominator, stale run and allocation order tests. Live PBIX checks require its authoring environment.
- Acceptance criteria: metrics match independently calculated values and preserve legacy meanings; no fake probability/causal labels; all new categorical thresholds approved.
- Exit conditions: view-level reconciliation accepted. Full raw-to-dashboard integrated acceptance is Stage 5, not silently claimed here.
- Complexity: High.

## Stage 5 WP5 Full Pipeline Integration

- Prerequisites: WP1–4 accepted; declared dependencies/environment changes separately approved; all business parameters for the integrated run resolved; Stage 5 authorization.
- Work packages: WP5 full integration, reusing earlier WP5-min without competing runner.
- Files affected: run_planning.py, planning_pipeline.py, proposed upstream_pipeline.py/run_management.py, dependency declaration, pipeline/runner/publication tests and published-run loaders.
- Tasks: unify raw preparation -> scenario -> sequential simulation -> independent validation -> KPI -> reconciliation -> safe publication; hash source/assumptions; isolate runs; record statuses/failures.
- Deliverables: one supported execution workflow, manifests, reproducible setup and complete published artifacts.
- Testing requirements: T-PIPE-001–003; failure injection at each write/stage; identical-input semantic reproduction and changed-source/parameter runs; publication visibility under failure.
- Acceptance criteria: incomplete runs never replace valid published results; no notebook-history dependency; historical files protected; UI reads one immutable successful run.
- Exit conditions: isolated authorized clean setup/run and failure recovery demonstrated with evidence.
- Complexity: High.

## Stage 6 WP6 Combined Stress Demonstration

- Prerequisites: accepted integrated pipeline; P11/P19 final treatments; calibrated workload baseline; Stage 6 authorization.
- Work packages: WP6 only, no new core allocation heuristic.
- Files affected: explicit scenario configuration, generator support as authorized, scenario demonstration tests and approved existing dashboard views.
- Tasks: four scenario kinds per selected policy, independent initialization, chronological execution, shortage/priority/stock/backlog/fulfillment interpretation and limits.
- Deliverables: published demonstration run plus traceable narrative and parameter references.
- Testing requirements: T-SCN-001/002 and all prior gates; unchanged canonical baseline and hand-computable constrained fixture.
- Acceptance criteria: correctly composed combined treatment; observed results explained without guaranteed or fabricated scarcity; policy and baseline comparability explicit.
- Exit conditions: owner accepts business narrative and constraint evidence; any unobserved trade-off claim removed.
- Complexity: Medium.

## Essential versus optional

Essential: independent correctness, approved input semantics, conservation, workload units, named KPI definitions, consistent five-page mapping, reproducible publication and a truthful demonstration.

Outside Route B: configurable production lead times, procurement optimization, OR solvers, alternate routing, ERP integration, AI, real-time monitoring, enterprise orchestration and statistical safety-stock optimization. These need separate business justification and authorization.

No precise person-day estimates are asserted; dependency/data decisions dominate effort uncertainty.
