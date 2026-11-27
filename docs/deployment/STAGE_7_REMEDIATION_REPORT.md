# Stage 7 remediation and formal recheck

Date: 2026-11-27. Objective: close the Stage 7 7.2 clean-source publication defect without changing the original 7.1–7.6 criteria. Source of truth: `STAGE_7_CLOUD_RELEASE_PREPARATION_SPEC.md`. Environment: Debian 13 Dev Container, Python 3.12.16 from `.venv312/bin/python`; Python 3.10.20 remains available. No deployment, Cloud Secret, paid API or real dispatch was used.

## Changes and scope

The local P5 `src/ai_copilot/provider.py` was reviewed against the committed P2 version and the existing `provider_base.py`. The Provider boundary retains `REAL_PROVIDER_DISPATCH_LOCKED = True`; `execute()` rejects all real calls; `execute_authorized()` rejects a real transport before campaign import, credential use or network I/O. A missing local paid-campaign runtime now produces a fail-closed `ProviderBlocked`. `tests/test_stage7_cloud_release.py` adds a behavioral network sentinel for a locked paid request. `tests/test_p5_paid_readiness_adapter.py` exercises the offline mock contract and no-retry/error mapping without a real key. The Stage 7 Cloud package still excludes `provider.py` and all paid/local P5 modules.

The worktree also contains many historical P5/Windows changes. They were preserved; the Provider and two focused test files form one functional remediation commit. A separate Planning test-only fix in `tests/test_phase1_risks.py` removes a fixed Git-ignored Run dependency discovered during clean-source regression. The current local WP4.1 mock integration may use unpublished archive/token/Windows dependencies; it is not claimed as clean-source paid readiness.

Exact changed paths for this task: `src/ai_copilot/provider.py`, `tests/test_stage7_cloud_release.py`, `tests/test_p5_paid_readiness_adapter.py`, `tests/test_phase1_risks.py`, `docs/deployment/STAGE_7_FORMAL_ACCEPTANCE_AUDIT.md`, `docs/deployment/STAGE_7_FORMAL_ACCEPTANCE_REPORT.md`, `docs/deployment/AI_ENABLEMENT_BLOCKER_AUDIT.md`, this report, and `docs/deployment/AI_ENABLEMENT_SECURITY_ACCEPTANCE_REPORT.md`. The last five paths are documentation only. No P5/Windows historical batch was bulk-published.

## Original acceptance matrix

| Criterion | Required evidence | Recheck | Status |
| --- | --- | --- | --- |
| 7.1 Cloud source boundary | 74 reviewed files, import closure and deterministic hash manifest | Stage 7 builder/package tests and Stage 8 packaged AppTest | PASS locally |
| 7.2 P5 preservation | Locked real dispatch, original Provider/Approval/Ledger behavior, paid modules excluded from package | Clean-source Provider/security suite plus locked network sentinel; P5 mock test | PASS for Stage 7 local release boundary; historical advanced P5 publication remains separate |
| 7.3 Python 3.12 | Pinned install, startup and relevant tests using actual 3.12 | `.venv312`, `pip check`, clean-source suites | PASS locally |
| 7.4 Fake/no-key runtime | Packaged Streamlit startup, synthetic fixture/Planning and AI preview | Stage 8 packaged runtime test and Cloud/Stage 6 tests | PASS locally |
| 7.5 Security/data | No Secret, unsafe path, symlink or paid execution module in package | Builder tests, manifest/security scan, no-network test | PASS for inspected package |
| 7.6 reproducible candidate | Fresh 74-file package, matching manifest and regressions | Two Stage 8 builds and post-remediation clean-source rebuild | PASS locally |

This is acceptance of the original **local Stage 7 release preparation** only. It does not accept Stage 8 Cloud runtime, public browser behavior, production Secrets, paid P5 execution or Stage 9. The historical `STAGE_7_FORMAL_ACCEPTANCE_REPORT.md` recorded the earlier failure and is retained as an audit record; this report records the later remediation decision and evidence.

## Verification and publication

The test sources were isolated `git archive` copies of the named commits; all commands used `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python` (3.12.16) from those archive directories. Counts overlap and are not summed.

| Exact command suffix after `.venv312/bin/python` | Source | Passed | Failed/errors | Skipped |
| --- | --- | ---: | ---: | ---: |
| `-B -m unittest tests.test_stage7_cloud_release tests.test_p5_paid_readiness_adapter tests.test_ai_copilot_provider tests.test_ai_copilot_approval tests.test_ai_copilot_ledger tests.test_ai_copilot_execution_gate tests.test_ai_copilot_eight_call_campaign` | Clean `fda19bb` archive | 49 | 0 | 0 |
| `-B -m unittest tests.test_stage8_local_runtime tests.test_dashboard_app tests.test_comparison_dashboard tests.test_phase2_workflow tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_question tests.test_stage6_cloud_provider` | Clean `fda19bb` archive | 63 | 0 | 0 |
| `-B -m unittest tests.test_run_planning tests.test_planning_pipeline tests.test_planning_risk tests.test_scenario_generator tests.test_scenario_comparison tests.test_inventory_transition tests.test_phase1_risks` | Clean `71fab3e` archive | 119 | 0 | 0 |
| `-B -m unittest tests.test_stage7_cloud_release tests.test_p5_paid_readiness_adapter` | Staged snapshot and local worktree | 10 each | 0 | 0 |
| `-B -m unittest tests.test_p5_wp4_1_offline_dispatch` | Local worktree, unpublished historical P5 dependencies | 1 | 0 | 0 |
| `-m pip check` | Project Python 3.12 venv | pass | 0 | — |

The first clean Planning run had 13 errors in 119 tests because `tests/test_phase1_risks.py` read a fixed Git-ignored `tmp` Run. The test-only fix generates a disposable Run from tracked inputs; focused clean-source tests then passed 22/22, and the full 119-test command passed from committed source. No Planning Engine source or business rule changed. The committed 74-file Cloud package rebuilt with manifest SHA-256 `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`, matching the Stage 8 candidate. Targeted key/private-key scan found no value; no symlink, `.venv312` or `tmp` path is included in the package. `git diff --cached --check` passed for both code/test commits.

Functional commit `fda19bbfa7bb054b8590f347338e0eab043d1487` contains exactly `src/ai_copilot/provider.py`, `tests/test_stage7_cloud_release.py`, `tests/test_p5_paid_readiness_adapter.py`. Test-isolation commit `71fab3e707850e3e5067f8aa0f83185253423eaf` contains exactly `tests/test_phase1_risks.py`. `git push origin main` succeeded (`7ba4cac..71fab3e`); a subsequent `git fetch origin main` verified both commits are ancestors of remote SHA `71fab3e707850e3e5067f8aa0f83185253423eaf`, equal to local HEAD at that check. No unrelated P5/Windows, virtual environment, tmp output or Secret was committed.

**Formal Stage 7 recheck: ACCEPTED for the original local Cloud release-preparation scope (7.1–7.6).** This supersedes the 2026-11-26 failure recorded in `STAGE_7_FORMAL_ACCEPTANCE_REPORT.md`; the historical failure remains documented. Paid AI enablement and Cloud deployment remain unaccepted. Remaining activation blockers and Owner decisions are in `AI_ENABLEMENT_SECURITY_ACCEPTANCE_REPORT.md`. No product business rule or safety lock was relaxed.
