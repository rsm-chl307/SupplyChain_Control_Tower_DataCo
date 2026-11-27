# Stage 7 / Stage 8 baseline and boundary

Date: 2026-11-26. Objective: separate the existing Stage 7 acceptance track from Owner-authorized Stage 8 local Python 3.12 implementation. Repository `/workspace/SupplyChain_Control_Tower_DataCo`, branch `main`, HEAD and freshly fetched `origin/main` at preflight `a11f98469cbec7ef7d6439f4c8888c38d2773588`. Existing unrelated local and P5/Windows changes were preserved. The later formal Stage 7 conclusion and Git publication are in `STAGE_7_FORMAL_ACCEPTANCE_REPORT.md` and `STAGE_8_SUBMISSION_AUDIT_REPORT.md`; this document retains the original baseline snapshot.

## Source of truth and recovered baseline

Stage 7 sources: `STAGE_7_CLOUD_RELEASE_PREPARATION_SPEC.md`, `STAGE_7_IMPLEMENTATION_PLAN.md`, the Stage 7 implementation/test/readiness reports, the pinned Cloud builder and its 74-file allowlist. The original Stage 7 report recorded local implementation **PASS WITH LIMITATIONS** but no Python 3.12 execution. Stage 7 **formal acceptance remains incomplete**. No Stage 7 acceptance status was changed in this task.

A repository search found no separate Stage 8 specification or pre-existing Stage 8 implementation plan/acceptance record. The Owner's current WP8.1–WP8.5 instruction is the authorized local scope. Prior Stage 8 reports were local working documents from Python 3.10 checks and have now been updated with actual 3.12 results. Before this task there was no 3.12 virtual environment, no 3.12 dependency install or 3.12 candidate execution, and no Cloud deployment.

## Exact Stage 7 acceptance boundary

The existing Stage 7 specification defines: 7.1 Cloud source boundary and manifest; 7.2 P5 preservation/exclusion; 7.3 actual Python 3.12 dependency installation, startup and tests; 7.4 packaged Fake/no-key runtime and Planning; 7.5 security/data inventory; 7.6 fresh reproducible local candidate and regression evidence. Earlier Stage 7 reports record local evidence for 7.1, 7.2 and 7.4–7.6. Stage 8 now provides separate 3.12 technical evidence for the formerly open 7.3 condition, plus fresh package and regression checks, but this does **not** constitute Stage 7 formal acceptance: the Stage 7 candidate, its changed source and its own evidence must be reconciled and reviewed under Stage 7's approval process. Its readiness report also requires reviewed source/deployment SHA and separate approval before publication; no such publication occurred. Stage 8 Cloud tests cannot substitute for that review.

## Stage 8 status and dependency classification

| WP | Local result | What remains independent of Stage 7 acceptance |
| --- | --- | --- |
| WP8.1 Python 3.12 runtime | Existing uv-managed 3.12.16 found in the same Debian 13 Container; `.venv312` created, root pins installed, native imports and `pip check` passed; Python 3.10.20 preserved. | Community Cloud runtime/install evidence. |
| WP8.2 configuration/Secrets | Backend-only credential path, no-key public startup, safe missing-config behavior, package exclusions and offline tests passed. | Production Secrets isolation is untested and unauthorized. |
| WP8.3 public non-AI | Packaged Planning, scenario/risk/WP1/WP2 and Dashboard regressions passed on 3.12. Previously local-only test fixtures were repaired and pass in clean source. | Public browser UAT; legacy reference-data Dashboard is limited in the synthetic-only package. |
| WP8.4 local RC | Two 74-file builds match byte-for-byte and candidate-a runs in `.venv312` with local HTTP health 200. | GitHub-synchronized RC and deployed version are separate states. |
| WP8.5 acceptance preparation | Runtime/security procedure and evidence recorded. | Actual Cloud deployment logs, deployed SHA, public browser tests and Owner acceptance. |

Compatibility class A (Stage 8 runtime): local 3.12 and pinned install are verified; actual Cloud environment is not. Class B (Stage 7 acceptance): its independent formal review is still open despite new 3.12 evidence. Class C (shared): any change to the 74-file source or runtime pins requires fresh package/compatibility evidence for both tracks. No Planning Engine formula, priority, allocation, scenario or KPI definition changed.

## Material Git and product boundaries

The builder `scripts/build_streamlit_demo_source.py`, `docs/deployment/STREAMLIT_CLOUD_ALLOWLIST.txt`, Stage 7 tests/reports, Stage 8 tests/reports and `requirements-test.txt` remain untracked local work. `.gitignore` now differs from HEAD only for `.venv312/`. Modified historical P5/Windows files remain outside the Cloud source; `REAL_PROVIDER_DISPATCH_LOCKED = True`. The local RC is therefore **not** a GitHub-synchronized RC. No commit, push, deployment, production Secret access or paid API call occurred.

The old Planning test isolation issue is resolved in the Stage 8 working tree: `tests/test_phase2_workflow.py` now generates published Runs from tracked fixtures; it passed 10/10 in a clean `git archive HEAD` source plus that single test change. Two Dashboard/WP2 tests also now generate Runs within the existing UI-allowed, Git-ignored root and passed 17/17 in clean source. Generated runtime outputs were not staged or committed.

## Remaining blockers and decisions

| Affected work | Exact evidence and impact | Resolution / Owner decision |
| --- | --- | --- |
| Stage 7 formal acceptance | New 3.12 evidence has not been reviewed against the Stage 7 candidate and all 7.1–7.6 acceptance records. | Separate Stage 7 review and Owner acceptance; Stage 8 local work may proceed independently. |
| WP8.3 legacy Executive Dashboard in Cloud package | `data/processed` reference artifacts are excluded by the approved synthetic-only source boundary. The historical view can report unavailable data; full reference display cannot be claimed for the package. | Preserve limitation or separately approve a reviewed non-sensitive sample; do not ship raw/processed data wholesale. |
| WP8.4 GitHub-synchronized RC | Local builder/allowlist and Stage 8 changes are uncommitted; `.gitignore` is dirty. | Review exact paths and obtain separate authorization before commit/push. Local RC remains usable for offline work. |
| WP8.5 Cloud acceptance | No deployment, Cloud install/startup log, deployed SHA, public accessibility or browser UAT. | Separate deployment authorization and actual Cloud evidence. Production Secrets/real AI remain separate decisions. |

No additional infrastructure, database or agent framework was introduced. Stage 9 real AI remains outside this task.
