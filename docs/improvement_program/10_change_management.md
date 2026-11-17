# Change Management and Authorization

Version 1.0 • 2026-11-17 • Specification only.

## Authority hierarchy and states

Owner D01–D11 are approved direction. The [Business Rules Registry](02_business_rules.md) identifies exact rules and Pending formulas. Existing legacy freezes remain authoritative for legacy artifacts. Approved Route B direction does not authorize code, tests, dependencies, data or dashboard implementation.

Separate records are required for:
1. Direction approval (already D01–D11).
2. Resolution of a pending business choice, with exact values and version.
3. Authorization to implement a named stage/WP and explicit file/output scope.
4. Acceptance after tests and artifact review.

Do not equate specification completion with owner freeze or implementation acceptance. Current state: planning package assembled for owner review; all Route B implementation stages NOT STARTED and NOT AUTHORIZED. Stage 0 owner sign-off remains open.

## Change request contents

Record change ID, reason, impacted BR/P/contract IDs, old/new semantics and units, migration compatibility, targeted files, tests, expected outputs, dependency/environment needs, rollback strategy and owner approval. Resolve a pending entry in place, update rule status only with that record, and bump specification/assumption/schema version when meaning changes.

No changes to frozen artifacts. New Route B outputs belong to isolated versioned runs, not legacy data/processed fixed filenames. A compatibility adapter must not place workload values in legacy quantity-capacity columns.

## Historical documentation

Existing documents are preserved. Small scope notices in the root README, implementation specification, developer notes and journal point here. They do not rewrite the former designs. [Charter conflicts C01–C10](00_program_charter.md) remain review records; P20 page mapping and all other unresolved business choices remain unresolved.

AGENTS.md and runtime configuration are untouched. A future authorization must explicitly identify how a Route B stage extends frozen legacy behavior; no agent should infer permission from this directory alone.

## Stage gates and rollback

Before coding: approve stage-specific scope, contract version and required pending decisions; fingerprint protected inputs. During implementation: keep new engines pure, publish only validated complete runs, preserve original tests and historical artifacts. After implementation: independent invariants, regression results, source hashes, changed-file list and known limits must be recorded.

Rollback means selecting a prior validated published run/version or reverting a separately authorized change; it never means silently rewriting baseline data. Git history operations require explicit approval.

## Change history

| Entry | Date | Change | Authority / status |
|---|---|---|---|
| CHG-001 | 2026-11-17 | Retain D01–D11, registry/contracts, six WP specifications, roadmap and pending decisions | Owner authorized documentation only; review package v1.0; no implementation approval |


## CHG-002 Revised implementation scope, 2026-11-17

A subsequent owner instruction authorized the reduced three-day vertical slice, superseding the original full-roadmap execution boundary for that scope only. Implemented behavior and schema are recorded in [active contracts](04_data_contracts.md) and [developer notes](../scenario_planning/developer_notes.md). The complete six-WP program is not represented as delivered. Synthetic fixture parameters are not approvals of unresolved real-source business rules.


## CHG-003 Source-independent data strategy, 2026-11-17

The owner authorized SYNTHETIC_DEMO and USER_DATA through one canonical planning bundle. Added the source adapter, portable examples/templates and validated CSV interface; no database/upload platform or separate engine. DataCo whitelist and synthetic opening method are now resolved only for its reference profile. Current external schemas are in docs/planning_csv_inputs.md. Original reference artifacts and historical reports are preserved.
