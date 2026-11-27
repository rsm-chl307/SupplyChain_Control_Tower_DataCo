# P5 Execution Source Publication Review

Date: 2026-11-27. Objective: identify and qualify the smallest complete P5 local execution graph from clean committed source while preserving unrelated historical files.

## Root cause and dependency graph

The baseline commit `501e79a07096aef031f18d1817f258df089d5f75` contains the locked Provider and base Approval/Ledger but not the newer P5 evaluation Archive, exact-count orchestrator, Windows Host, signed Generation authorization and permit modules. `eight_call_campaign.py` is tracked but its paid Ledger implementation is only in the modified working tree. The clean GitHub source therefore cannot reproduce that full path. Publishing the locked Provider alone does not publish P5 execution.

Reviewed direct implementation dependencies include `src/ai_copilot/eight_call_campaign.py`, `evaluation_archive.py`, `evaluation_namespace.py`, `input_token_count_payload.py`, `p5_token_count_orchestrator.py`, `token_count_evidence.py`, `windows_generation_dispatch.py`, `windows_runner_exchange.py`, and `tools/windows_api_runner` count/Generation Python modules. The Windows Host also has credential-store, PowerShell deployment, schema, manifest and `cryptography==46.0.7` dependencies. The tracked `docs/ai_copilot/p5_offline_evaluation/cases.v2.json` is a SHA-256 pinned paid corpus; temporary Runs are never source files.

The clean candidate exposed one additional tracked-code dependency: `quality_evaluation.assess_technical()` must preserve the request's execution profile when rebuilding it. The working tree already contained that fix together with unrelated changes to the quality policy version and PASS threshold. Only the execution-profile hunk was committed for this P5 publication; the policy changes remain untouched and uncommitted. The candidate Archive tests were rerun against precisely that hunk.

After applying only the profile hunk to the isolated candidate, `env -u OPENAI_API_KEY /workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_p5_evaluation_archive tests.test_p5_wp4_6_2_archive_lifecycle tests.test_p5_wp4_6_3_legacy_archive_compat` passed 18/18. The original committed `tests/test_p5_quality_evaluation.py`, copied into that candidate, passed 8/8, confirming the original 85-point PASS rule was retained. The earlier full candidate run loaded the pre-fix module and its Archive errors are superseded only for those rerun modules; its full result is retained as historical diagnostic evidence.

The first expanded candidate run finished 92 passed / 8 errors in 100 tests; all eight errors were in Archive modules loaded before the profile fix. The 18-test Archive rerun passed. The separate candidate qualification run had 77 passed / 1 failure in 78 tests: the rehearsal destination check accepted a path inside the source repository when the *repository itself* was placed under `/tmp`. `wp36_qualification.py` now rejects destinations under its own repository root even if that root is under the system temp directory. Its test uses a unique repository probe name so a prior failed run does not contaminate a retry. The focused isolated test passed. These failures are preserved in the report rather than counted as passing runs.

An exact staged snapshot was built from `git archive HEAD` plus the 69 staged index blobs, with no other worktree changes. Its full P5/Windows suite passed 109/109, extra P5/Windows suite passed 78/78 and Stage 7/8/security suite passed 30/30 under Python 3.12.16 with `OPENAI_API_KEY` unset. A fresh `git archive` of committed source `0c90b0a955d5c0ab1ab22b1ac962c56af3d73e97` independently passed the same three groups: 109/109, 78/78 and 30/30. The exact commands were the staged-snapshot commands below, run from `/tmp/sct-p5-committed-source` with the same Python executable; `pip check` returned `No broken requirements found.`

The same committed archive additionally passed the original Stage 7 safety/acceptance group 49/49 and broader Stage 8 public-functionality group 63/63. Commands, local environment and nonblocking Streamlit deprecation warnings are recorded in `LOCAL_REAL_AI_TRIAL_READINESS_REPORT.md`. No real API, Windows native or Cloud deployment check was substituted for these offline suites.

SHA-256 comparison of all 69 snapshot files against their staged index blobs found 0 mismatches. `git diff --cached --check` passed. Exact staged path set matched the reviewed list (69/69; no extra path). Credential-pattern scan found only the deliberate synthetic `sk-...` rejection fixture in `tests/test_windows_api_runner.py`; no actual credential, private key, virtual environment, `tmp`, SQLite database, or Python cache was staged.

Staged-snapshot full command, run from `/tmp/sct-p5-staged-snapshot`: `env -u OPENAI_API_KEY /workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_p5_paid_readiness_adapter tests.test_p5_paid_readiness_ledger tests.test_p5_token_counting_gate tests.test_input_token_count_payload tests.test_p5_wp4_1_offline_dispatch tests.test_p5_evaluation_archive tests.test_p5_wp4_6_2_archive_lifecycle tests.test_p5_wp4_6_3_legacy_archive_compat tests.test_windows_generation_authorization tests.test_windows_generation_permit tests.test_windows_generation_host tests.test_p5_windows_token_count_orchestrator tests.test_windows_api_runner tests.test_windows_api_runner_policy tests.test_windows_runner_deployment tests.test_p5_quality_evaluation` — 109 passed, 0 failed, 0 skipped. Extra command: `env -u OPENAI_API_KEY /workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_p5_evaluation_namespace tests.test_p5_token_count_reconciliation tests.test_p5_windows_runner_exchange tests.test_p5_windows_runner_orchestrator_e2e tests.test_windows_api_runner_worker tests.test_windows_external_issuer tests.test_windows_fake_bootstrap_compat tests.test_windows_generation_ledger tests.test_windows_generation_owner tests.test_wp35b_windows_acceptance_script tests.test_wp36_host_preflight_script tests.test_wp36_qualification tests.test_wp3_generation_deployment tests.test_local_token_count_e2e` — 78 passed, 0 failed, 0 skipped. The Stage 7/8/security command is listed in `LOCAL_REAL_AI_TRIAL_READINESS_REPORT.md` — 30 passed, 0 failed, 0 skipped in the same snapshot.

## Safety findings

The signed Generation Proposal, Host proof and one-use Permit carry the same request ID, Run, case, model, payload, count evidence, Approval reference, Ledger attempt and ceiling. The Container claim precedes the Host dispatch. The Host's own real transport previously did not read `provider.py`'s lock; `generation_host.py` now checks `REAL_GENERATION_DISPATCH_LOCKED = True` before package parsing or credential read. The separate Count Runner's real `UrllibTransport` is now also blocked by `REAL_TOKEN_COUNT_DISPATCH_LOCKED = True` before credential access. Fake transports remain available for offline testing. Native Windows credential and task behavior cannot be established by Linux tests.

No historical `tmp Run`, `.venv312`, credential, private key or unrelated Windows artifact was approved for publication by this review. The publication used exact reviewed paths, a full staged-diff check and staged-snapshot tests; the post-commit clean-source run is recorded separately below.

Historical P5 documentation drafts, review worksheets, the existing `quality_evaluation.py` policy-version and 85→80 threshold changes, and unrelated synthetic-context/test edits were not staged. The 69-path selection contains only runtime source, required schema/manifest/deployment source, and matching tests. The remaining local history is preserved for a separate Owner review; publication of this source graph does not retroactively approve those product or evaluation-policy changes.

## Verification record

The initial Python 3.12 worktree tests exercised P5 paid readiness, token-count gates, Archive and Windows Host authorization/permit paths with `OPENAI_API_KEY` unset. Core command: `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest tests.test_p5_paid_readiness_adapter tests.test_p5_paid_readiness_ledger tests.test_p5_token_counting_gate tests.test_input_token_count_payload tests.test_p5_wp4_1_offline_dispatch tests.test_p5_evaluation_archive tests.test_p5_wp4_6_2_archive_lifecycle tests.test_p5_wp4_6_3_legacy_archive_compat` — 43 passed. Windows command: `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest tests.test_windows_generation_authorization tests.test_windows_generation_permit tests.test_windows_generation_host tests.test_p5_windows_token_count_orchestrator tests.test_windows_api_runner tests.test_windows_api_runner_policy` — 50 passed. A clean HEAD archive was constructed in `/tmp/sct-p5-clean-candidate` and overlaid only as a *candidate* for dependency testing; it is not a committed-source acceptance result. The 22-test candidate smoke suite passed after the missing Archive schema was identified and added. `pip check` passed in `.venv312`. Broader candidate and extra suite results, source commit, push and fetched remote SHA are recorded below.

Dependency command: `.venv312/bin/python -m pip install -r tools/windows_api_runner/requirements-generation.txt`; installed `cryptography==46.0.7` in the project virtual environment. `.venv312/bin/python -m pip check` returned `No broken requirements found.` Python 3.10 and system packages were not changed. The Stage 8 Cloud requirements are not expanded by this Windows-only manifest.

| Item | Status |
| --- | --- |
| Full reviewed P5 source in GitHub main | Yes: 69-path source/test commit `0c90b0a955d5c0ab1ab22b1ac962c56af3d73e97` |
| Linux offline staged-snapshot tests | 109 + 78 + 30 passed |
| Native Windows Host qualification | Pending separate environment |
| Real token count / Generation API compatibility | Pending separate paid authorization |
| P5 publication commit and verified remote | `git push origin main` succeeded (`501e79a..0c90b0a`); `git fetch origin main` verified `origin/main = HEAD = 0c90b0a955d5c0ab1ab22b1ac962c56af3d73e97` |

## Publication gate performed

The 69 exact source/test paths were reviewed for secrets and generated data. `git diff --cached --check` passed; the complete staged diff was saved for inspection, and its path set and safety-sensitive sections were reviewed. The P5 source was committed separately, pushed after staged-snapshot qualification, and verified by a fresh `git fetch origin main`. The default dispatch locks remain true. Native Windows and live API acceptance remain separate gates.

## Exact reviewed source and test paths

- `docs/ai_copilot/p5_offline_evaluation/GENERATION_EVALUATION_RECORD_SCHEMA.json`
- `src/ai_copilot/eight_call_campaign.py`
- `src/ai_copilot/evaluation_archive.py`
- `src/ai_copilot/evaluation_namespace.py`
- `src/ai_copilot/generation_issuer_setup.py`
- `src/ai_copilot/input_token_count_payload.py`
- `src/ai_copilot/local_token_count_e2e.py`
- `src/ai_copilot/p5_token_count_orchestrator.py`
- `src/ai_copilot/quality_evaluation.py`
- `src/ai_copilot/token_count_evidence.py`
- `src/ai_copilot/windows_generation_dispatch.py`
- `src/ai_copilot/windows_runner_exchange.py`
- `src/ai_copilot/wp36_qualification.py`
- `tests/test_input_token_count_payload.py`
- `tests/test_local_token_count_e2e.py`
- `tests/test_p5_evaluation_archive.py`
- `tests/test_p5_evaluation_namespace.py`
- `tests/test_p5_paid_readiness_ledger.py`
- `tests/test_p5_token_count_reconciliation.py`
- `tests/test_p5_token_counting_gate.py`
- `tests/test_p5_windows_runner_exchange.py`
- `tests/test_p5_windows_runner_orchestrator_e2e.py`
- `tests/test_p5_windows_token_count_orchestrator.py`
- `tests/test_p5_wp4_1_offline_dispatch.py`
- `tests/test_p5_wp4_6_2_archive_lifecycle.py`
- `tests/test_p5_wp4_6_3_legacy_archive_compat.py`
- `tests/test_windows_api_runner.py`
- `tests/test_windows_api_runner_policy.py`
- `tests/test_windows_api_runner_worker.py`
- `tests/test_windows_external_issuer.py`
- `tests/test_windows_fake_bootstrap_compat.py`
- `tests/test_windows_generation_authorization.py`
- `tests/test_windows_generation_host.py`
- `tests/test_windows_generation_ledger.py`
- `tests/test_windows_generation_owner.py`
- `tests/test_windows_generation_permit.py`
- `tests/test_windows_runner_deployment.py`
- `tests/test_wp35b_windows_acceptance_script.py`
- `tests/test_wp36_host_preflight_script.py`
- `tests/test_wp36_qualification.py`
- `tests/test_wp3_generation_deployment.py`
- `tools/windows_api_runner/README.md`
- `tools/windows_api_runner/__init__.py`
- `tools/windows_api_runner/api_runner.py`
- `tools/windows_api_runner/auto_run_policy.py`
- `tools/windows_api_runner/auto_run_policy.template.json`
- `tools/windows_api_runner/backup_runner_state.py`
- `tools/windows_api_runner/bootstrap_worker.ps1`
- `tools/windows_api_runner/deploy_generation.ps1`
- `tools/windows_api_runner/deploy_runner.ps1`
- `tools/windows_api_runner/disable_auto_run.ps1`
- `tools/windows_api_runner/enable_auto_run.ps1`
- `tools/windows_api_runner/external_issuer.py`
- `tools/windows_api_runner/generation_authorization.py`
- `tools/windows_api_runner/generation_host.py`
- `tools/windows_api_runner/generation_key_setup.py`
- `tools/windows_api_runner/generation_owner.py`
- `tools/windows_api_runner/generation_permit.py`
- `tools/windows_api_runner/request-package.schema.json`
- `tools/windows_api_runner/requirements-generation.txt`
- `tools/windows_api_runner/response-package.schema.json`
- `tools/windows_api_runner/source-manifest.json`
- `tools/windows_api_runner/start_worker.ps1`
- `tools/windows_api_runner/status_worker.ps1`
- `tools/windows_api_runner/stop_worker.ps1`
- `tools/windows_api_runner/store_credential.py`
- `tools/windows_api_runner/verify_credential.py`
- `tools/windows_api_runner/worker.py`
- `tools/windows_api_runner/worker_task.ps1`
