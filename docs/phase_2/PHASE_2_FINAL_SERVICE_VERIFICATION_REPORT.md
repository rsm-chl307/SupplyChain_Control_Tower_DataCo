# Phase 2 Final Service Verification Report

Date: 2026-11-19 UTC. Main Agent only. Scope: investigate and restore the existing port 8502 service, minimum homepage verification, and final acceptance reevaluation. No feature implementation.

## Final decision and acceptance evidence

**Final recommendation: Phase 2 COMPLETE — PASS WITH LIMITATIONS, pending owner review.** T33 and P2-G08 now PASS. **T01–T33: 33 PASS; P2-G00–P2-G08: 9 PASS.** No required current gate remains FAIL/BLOCKED/PARTIAL. This is not a claim of complete negative-data Published E2E coverage or operational production certification.

Reused unchanged evidence: T25 **22 PASS**, safe regression **92 PASS / 0 FAIL / 0 SKIPPED**, and **eight actual CSV downloads** already parsed and byte-identical to independently verified original outputs. No full UAT, WP1/WP2 workflow, CSV download, planning or regression suite was rerun in this recovery task. The new source-reuse check matches current dashboard/helper source to recorded T25 incremental diffs; source and evidence are not assumed from HEAD alone. [acceptance_source_reuse.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/acceptance_source_reuse.json).

| Gate | Result | Basis |
| --- | --- | --- |
| P2-G00 | PASS | Baseline, explicit allowlist, owner authorization and non-publishing controls recorded. |
| P2-G01 | PASS | Original inventory/invariants preserved; paired display additions and canonical exceptions explicit. |
| P2-G02 | PASS | Workflow/state/handoff/controlled rejection evidence valid; fresh guarded regressions pass. |
| P2-G03 | PASS | No metric/semantic changes; current formatting tests and byte-identical canonical output. |
| P2-G04 | PASS | T22–T25 pass at declared layers; actual readable en/zh state/browser evidence and approved raw/external exceptions. |
| P2-G05 | PASS | Fresh actual four-format bilingual downloads equal independently verified original files; native evidence unchanged. |
| P2-G06 | PASS | 92 safe regression cases pass; three runner guards zero. Unsafe historical setup excluded, not counted as executed. |
| P2-G07 | PASS | T25 and T32 completed; current reports describe actual behavior and retained limitations. |
| P2-G08 | PASS | Final service blocker resolved under explicit recovery authorization. Source/tests/config/history unchanged; only authorized documentation delta; original accepted limitations retained. Recommend COMPLETE / PASS WITH LIMITATIONS pending owner review. |

T33/P2-G08 use the owner-authorized replacement PID for 8502; they do **not** claim the disappeared original PID was preserved or its disappearance disproved. Current recovery evidence supplements, rather than edits, the original blocked matrix: [final_acceptance.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/final_acceptance.json). Original T25/CSV/regression/final-integrity raw evidence remains unchanged under tmp/phase_2_t25/20261119T160308Z/.


## 1. Investigation and confirmed original ownership

Port 8501 original PID **1117256** remained available (health 200). Port 8502 original PID **1503434** was absent and refused connections. Historical Phase A and Phase 1 records identify 8502 as the existing project Streamlit instance, not the disposable 8503/8504 test apps. Two independent argv records agree exactly:

- [services_during.json](../../tmp/phase_2_t25/20261119T160308Z/reports/services_during.json): original argv, repository cwd, PID and start time.
- [recovery_runtime_namespace.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/recovery_runtime_namespace.json): original argument vector and distinct disposable test-service signatures.
- [environment_inspection.json](../../tmp/wp2_browser_uat_phase_a/reports/environment_inspection.json): system Python / no-bytecode 8502 and original application entry.

Original command, now reused verbatim:

```bash
python -B -m streamlit run dashboard/scenario_planning_app.py --server.address 0.0.0.0 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

Working directory: /workspace/SupplyChain_Control_Tower_DataCo. System interpreter /usr/local/bin/python resolves to /usr/local/bin/python3.10, Python 3.10.20; Streamlit 1.56.0. Port 8501 runs /usr/local/bin/python3.10 /usr/local/bin/streamlit run dashboard/scenario_planning_app.py; 8502 is a **separate process** serving the same current entry point, with explicit address 0.0.0.0, port 8502, headless true, usage statistics false and -B. Neither original argv pins a Published Run or separate data source. No repository/home .streamlit/config.toml was present in the inspected environment. No configuration/environment override was supplied during recovery.

## 2. Exit cause — not established

The observed failure is disappearance of the original process and a refused 8502 connection. No original exit status, crash traceback, dedicated 8502 startup/exit log or supervisor restart record was found in the scoped available records. The original 8501 process/start time survived, so there is no positive evidence of a wholesale container restart. Available cgroup memory.events showed zero OOM/oom_kill; this does not establish the cause or exclude every external/system mechanism.

**Root cause remains UNCONFIRMED.** Do not attribute this to OOM, a container rebuild, application code or deliberate termination without evidence. Recovery does not resolve the forensic uncertainty. Current container hostname and boot identity are recorded in [runtime_before.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/runtime_before.json); no new Container was created.

## 3. Authorized recovery

Before launch, captured actual HEAD/index/dirty worktree and scoped file/evidence/Run snapshot. Checked 8502 was not healthy and the original address/port was bindable; no existing listener was killed or replaced. Reused the confirmed original argv, repository cwd and system Python, with **no environment changes**.

Recovered PID: **2562690**. [launch.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/launch.json) records exact arguments/cwd/log target. Launcher uses a detached process session and redirects stdout/stderr to a new recovery log so the service does not depend on the verification terminal lifetime. This changes process IO/session ownership only; no systemd, Docker, dependency or deployment configuration was introduced.

Original 8501 PID **1117256** and process start time **9682561** remain identical. It was not restarted/stopped/reconfigured. Original 8502 PID 1503434 cannot be resurrected; its replacement is explicitly authorized and recorded. No file-backed data/Run/configuration was changed or injected. Lost in-memory sessions from a dead process cannot be recovered or certified as preserved; new browser checks used empty fresh sessions, not restored or fabricated user state.

Recovery log: [streamlit_8502_recovery.log](../../tmp/phase_2_service_recovery/20261119T165128Z/logs/streamlit_8502_recovery.log). No fatal markers (Traceback, Uncaught app execution, Address already in use, Error:) were observed. Existing use_container_width deprecation messages were recorded, not suppressed or fixed.

## 4. Minimum final service verification

| Check | 8501 | 8502 |
| --- | --- | --- |
| Process | Original 1117256 preserved | Authorized replacement 2562690 |
| Health | HTTP 200 / ok | HTTP 200 / ok |
| Chromium homepage | PASS | PASS |
| Streamlit WebSocket | Frames received; no errors | Frames received; no errors |
| Page errors / failed requests / fatal console errors | None observed | None observed |
| Published Run selection | Empty fresh session | Empty fresh session |
| Planning / WP1 / WP2 actions | None | None |

Actual Chromium 159.0.8154.6 used the existing Playwright environment; fresh contexts at 1600×1100, one per port. Only homepage navigation/inspection/screenshot occurred: no clicks, uploads, validation, Run loading or feature execution. Home screenshot was visually inspected for normal rendering. No whole UAT was repeated.

- [browser_homepages.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/browser_homepages.json)
- [Actual 8501 screenshot](../../tmp/phase_2_service_recovery/20261119T165128Z/screenshots/homepage_8501.png)
- [Actual recovered 8502 screenshot](../../tmp/phase_2_service_recovery/20261119T165128Z/screenshots/homepage_8502.png)
- [Process/argv/health/startup verification](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/runtime_verified.json)

Commands: existing venv Python -B tmp/phase_2_service_recovery/20261119T165128Z/verify_homepages.py; system Python -B tmp/phase_2_service_recovery/20261119T165128Z/verify_runtime.py. Both completed PASS. This homepage smoke check does not newly certify WP1/WP2 or all bilingual surfaces; those retain their earlier 22-case evidence.

## 5. Git, data and evidence protection

HEAD remains **4674e8bba3551894de0f9e9ea8d60a7e6ce5e0cf**, branch main. Index empty; working tree remains dirty with pre-existing user modifications/untracked files preserved. No source/test/configuration/manual/Phase 1 baseline changes. This task updates only the two requested Phase 2 reports and adds this service report; new operational evidence is isolated under tmp/phase_2_service_recovery/20261119T165128Z/.

Before documents were updated, all scoped existing fingerprints matched. Final verification permits only those two report updates and this new report. Existing **53 Run paths**, all **53 manifest fingerprints**, and the **13 primary files** remain unchanged. The original 12/12 primary artifact-to-manifest validation remains supported by unchanged primary bytes; no unnecessary full historical hash rerun. Relevant T25 machine-readable evidence is unchanged. [pre_document_integrity.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/pre_document_integrity.json); [final_integrity.json](../../tmp/phase_2_service_recovery/20261119T165128Z/reports/final_integrity.json).

Documentation links/whitespace and git diff --check are checked after writing. No Git staging, commit, push, reset, clean, restore, checkout, stash, branch/deployment action. No Planning, upload/publication, new Run/artifact or modification of historical evidence.

## 6. Remaining accepted limitations

- Seven Phase 1 negative Published E2E/browser sublayers remain NOT COVERED within their parent PARTIAL cases; no coverage promotion by this recovery.
- Two Plant Show-chart mouse interactions and Vega warning observations remain recorded; no fixes/retest here.
- USER_DATA classification still contains SYNTHETIC_EXAMPLE source metadata, not independently verified operational production data.
- CJK fonts remain container-local; no persistence/deployment change. Earlier actual CJK/T32 evidence remains valid, not rerun here.
- Original 8502 exit cause remains unconfirmed; recovery plus current health is not a long-term uptime guarantee. New detached-session lifetime is documented; no supervisor was installed.
- Port 8501 is certified here only for preserved process/health/homepage availability, not a newly executed full UI/translation UAT.

## 7. Stop decision

Recommend **Phase 2 COMPLETE — PASS WITH LIMITATIONS**, submit the consolidated final report for owner review, then stop. No Phase 3/WP3, commit/push, deployment or further feature work is authorized by this recovery.
