# Phase 2 — Local Real-AI Trial Preflight

Date: 2026-11-27 UTC. Scope: local, offline preparation only. Source baseline: `cd32326328b5e492fa08f45b2e52cd841e62934c` on `main`; fetched `origin/main` matched before edits. Python: `.venv312/bin/python` 3.12.16 in Linux Dev Container. No API key, paid request, real transport unlock, Cloud deployment or production Secret was used.

## Decision

**NOT READY FOR OWNER AUTHORIZATION.** The implementation remains fail closed. A US$1 *hard billing limit* cannot currently be proved: the fixed US$0.02 per-request reserve has no validated worst-case price quote for the exact model/tier/input/output settings; Count returns a token count rather than an authoritative charge; Responses usage can be null and is not a final bill; a fresh Windows Host can create a new local database unless the Owner establishes one authoritative store and reconciliation procedure. The first unknown result holds the whole trial and blocks subsequent requests. This is deliberately safer than assuming an unknown cost is zero, but it prevents the planned multi-request campaign. No Owner should unlock either real transport on this evidence.

## WP1 — Shared Count + Generation budget

New `tools/windows_api_runner/trial_budget.py` provides a default-disabled SQLite trial store. Its one ledger holds both operations, US$1 nominal limit, US$0.20 reserve buffer, and exactly US$0.02 reserve per request. `BEGIN IMMEDIATE` serializes reservations and one-use claims among processes using the same database. Request UUID, operation, campaign, model, payload digest and price version are stored. Reserved amounts are never automatically refunded. Duplicate UUIDs, changed payloads, competing claims, claims after restart, missing database, unknown outcomes and absent trusted billing evidence block new traffic. Estimated, reserved and known actual values are separate; latency and optional usage/billing source are stored when available. A claim is required before credential access on both fixed real transports. Existing `REAL_PROVIDER_DISPATCH_LOCKED`, `REAL_TOKEN_COUNT_DISPATCH_LOCKED` and `REAL_GENERATION_DISPATCH_LOCKED` remain `True`.

The Windows Runner's strict `source-manifest.json` now includes the budget module and native preflight script with current SHA-256 hashes; `deploy_generation.ps1` includes the budget module in its exact Generation file list. Its corresponding offline manifest/deployer regression (`tests.test_windows_runner_deployment tests.test_wp3_generation_deployment`) passed 6/6. No Windows deployment was performed.

The local store is a technical pre-dispatch barrier, **not** a validated payment ceiling. The production transports cannot settle a request automatically because neither response supplies final authoritative billing evidence. The controller's settlement method is exercised only by synthetic tests. There is no automated source of validated price version or cross-Host single-writer guarantee, so the current code must remain locked. Existing Generation ledger's US$0.02 request / US$0.16 campaign constraints remain separately enforced.

## WP2 — Exact Token Count

Existing P5 workflow binds Run ID, request UUID, full Count wire digest, count projection digest, Brief digest and Provider request digest. The fixed Host validates the request digest and one-use execution identity; Generation permit binds `count_request_id`, Count evidence SHA, payload SHA, Approval and Ledger claim. New Windows Runner evidence expires after 24 hours, with at most five minutes of future clock skew. Stale or mutated evidence fails before Generation preparation. The Count real transport now also requires a matching shared-budget claim. No real Count request was sent.

Remaining: a Count response does not yield authoritative billed cost. A failed or uncertain Count must be manually reconciled; no automatic Generation follows it. Native Windows clock, exchange and SQLite behavior remain unverified.

## WP3 — Provider compatibility, offline review

The fixed Count endpoint matches the official `POST /v1/responses/input_tokens` path. Its documented response contains `input_tokens`; no final charge field is promised. The Generation Host uses `POST /v1/responses`, fixed timeout, no automatic retry, signed proposal/Owner proof/permit and a one-use Host claim. The official Responses schema permits `usage: null`; usage is token metadata, not a final bill. Existing response packages distinguish HTTP status, usage, raw-response digest, latency and `charge: null`. Network transport and account/model entitlement have **not** been tested. No claim is made about the Owner account's access to `gpt-6-luna`, rate limits, billing tier, actual model ID or current effective price. Before any future trial, the exact model, service tier and price version must be checked by the Owner and a worst-case quote for input/output caps must be proved below each reserve.

Official OpenAI references: [Count input tokens](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count), [Responses create and usage](https://developers.openai.com/api/reference/resources/responses/methods/create), [pricing](https://platform.openai.com/pricing/).

## WP4 — Windows native Host preparation

`tools/windows_api_runner/preflight_trial.ps1` is a read-only PowerShell preflight. From repository root on native Windows: `powershell -NoProfile -File tools/windows_api_runner/preflight_trial.ps1`. It writes a timestamped result under `%TEMP%`, with Python 3.12 executable/version, commit, path-only Git status, lock booleans, SQLite version/thread-safety, presence and read-only integrity check of the local budget DB. It does not read or print credential values. Review private path names before sharing the output. This Linux Dev Container cannot establish Windows Credential Manager, ACL, native SQLite file-lock, backup or path behavior; the script was prepared but **not executed on Windows**. The current local budget DB is separate from the Container's P5 workflow and ledger DBs; moving between Hosts must preserve one authoritative trial DB and its backup, and the current implementation does not enforce that globally.

Owner's Windows-only offline regression command, still without a credential or network call: `py -3.12 -m unittest -q tests.test_trial_budget tests.test_windows_api_runner tests.test_windows_generation_host tests.test_windows_generation_authorization tests.test_windows_generation_permit tests.test_windows_generation_ledger`. Capture it with PowerShell `2>&1 | Tee-Object -FilePath "$env:TEMP\supplychain-trial-tests.txt"`; review the file before sharing. Do not run any real-dispatch CLI.

## WP5 — Validation and evidence

Commands run with `OPENAI_API_KEY` unset and no real network transport. `.venv312/bin/python -B -m unittest -q tests.test_trial_budget`: 8 passed, 0 failed, 0 skipped. `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest -q tests.test_stage7_cloud_release tests.test_p5_paid_readiness_adapter tests.test_ai_copilot_provider tests.test_ai_copilot_approval tests.test_ai_copilot_ledger tests.test_ai_copilot_execution_gate tests.test_ai_copilot_eight_call_campaign tests.test_stage8_local_runtime tests.test_dashboard_app tests.test_comparison_dashboard tests.test_phase2_workflow tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_question tests.test_stage6_cloud_provider`: 112 passed, 0 failed, 0 skipped in the worktree. `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest -q tests.test_windows_generation_authorization tests.test_windows_generation_permit tests.test_windows_generation_ledger tests.test_p5_windows_runner_orchestrator_e2e tests.test_p5_windows_runner_exchange tests.test_p5_token_count_reconciliation tests.test_p5_windows_token_count_orchestrator tests.test_trial_budget`: 62 passed, 0 failed, 0 skipped. Earlier focused Count/Host/budget regression: `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest -q tests.test_trial_budget tests.test_windows_api_runner tests.test_windows_generation_host`: 33 passed before the final two budget tests were added. Focused Count evidence/workflow suite: `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest -q tests.test_trial_budget tests.test_windows_api_runner tests.test_p5_windows_token_count_orchestrator tests.test_p5_token_counting_gate`: 38 passed, 0 failed, 0 skipped. `.venv312/bin/python -m pip check`: no broken requirements. The focused budget test covers disabled default, Owner verifier, exact/insufficient budget, mixed Count/Generation total, parallel final-slot reservation, duplicate UUID, changed payload, one-use claim, crash/restart, unknown usage, actual above estimate and above reserve. Existing security tests cover locked real transports and Fake Provider isolation. Actual Windows and API acceptance: **NOT EXECUTED**.

## Blockers by responsibility

### A. Codex completed and verified

- Added one default-disabled local Count/Generation reservation ledger and pre-credential checks to both fixed real transports; missing or uncertain accounting fails closed.
- Added 24-hour freshness check for newly collected Windows Count evidence, offline tests and native Windows read-only preflight script.
- Preserved all three real dispatch locks, existing Planning Engine and unrelated worktree changes.

### B. Cannot verify in this environment; Owner must operate

- Run the native Windows script and retain its output; verify native Python, packages, Credential Manager presence, ACLs, SQLite locking, backup/recovery and exchange paths without sharing secrets.
- Establish whether one authoritative local budget DB can be preserved across every permitted Host and restart. Current process-local/container ledgers do not do this.
- Confirm current account/model access and effective billing configuration in OpenAI Platform; do not infer access from source code.

### C. Requires a separately authorized real API trial to confirm

- Actual Count response and charge treatment, Responses schema/model compatibility, timeout/rate-limit behavior, actual usage, provider request ID and response quality.
- Real account billing and whether a worst-case pre-reservation bound matches the final invoice. Offline mocks cannot prove a provider-side hard US$1 cap.

### D. Requires explicit Owner authorization before execution

- Any paid Count or Generation request, reading/using an OpenAI API credential, unlocking real Provider/Runner/Host dispatch, provisioning or enabling a real trial, and any Cloud deployment or production Secrets change.

## Next technical decisions

1. Determine a documented, versioned worst-case quote for each permitted request. It must cover model, input cap, output cap, tier, regional/cache modifiers, Count fee if any and safety margin. If the worst case exceeds US$0.02, revise the pre-existing cap only after Owner approval and revalidate the campaign budget.
2. Define authoritative reconciliation for Count and Generation after each claim. An UNKNOWN request remains held until the Owner resolves whether it was billed; never retry automatically.
3. Establish one durable, access-controlled budget authority for every local Host. A Host-local SQLite file is safe for concurrency in one Host but does not stop a second Host from starting a different trial file.
4. After these are solved, request separate Owner authorization for one real call at a time. US$1 is an approved planning ceiling, **not** authorization to spend it.

Provisional first round, after the blockers are resolved: one fresh synthetic Planning Run, one exact Count, one separately approved Generation, then stop and reconcile before any second case. This is **two possible network requests**, with US$0.04 in nominal reservations (US$0.02 each), leaving US$0.76 of the locally spendable US$0.80 after the safety buffer. These are reservation amounts, not reliable estimated or actual provider charges. A numeric price estimate is intentionally withheld until the Owner verifies the model/tier price version and the maximum billable token calculation.

## Files in this Phase 2 change

Created: `tools/windows_api_runner/trial_budget.py`, `tools/windows_api_runner/preflight_trial.ps1`, `tests/test_trial_budget.py`, this report. Modified: `tools/windows_api_runner/api_runner.py`, `tools/windows_api_runner/generation_host.py`, `tools/windows_api_runner/deploy_generation.ps1`, `tools/windows_api_runner/source-manifest.json`, `src/ai_copilot/token_count_evidence.py`, `tests/test_p5_windows_token_count_orchestrator.py`. No unrelated historical file, virtual environment, temporary output or credential is included.

## Git publication and clean-source verification

To be filled after exact staging, committed-source validation, push/fetch and remote SHA comparison. This report does not claim GitHub synchronization until then.
