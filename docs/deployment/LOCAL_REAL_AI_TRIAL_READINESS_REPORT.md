# Local Real-AI Trial Readiness

Date: 2026-11-27. Scope: local, single-Owner, small-scale trial preparation only. No paid request, API credential, Provider unlock, Cloud deployment, or production Secret was used.

## Baseline and boundary

At the start of this review `main`, local HEAD and `origin/main` were `501e79a07096aef031f18d1817f258df089d5f75`. The working tree already contained 122 entries (23 modified, 99 untracked); none were discarded. Stage 7's original 7.1–7.6 local release-preparation acceptance remains recorded as accepted in `STAGE_7_REMEDIATION_REPORT.md`; that acceptance does not authorize paid AI. Stage 8 local Python 3.12 candidate and regressions are separate from live Cloud acceptance.

| Stage 7 original item | Existing formal evidence | This review |
| --- | --- | --- |
| 7.1 Cloud source boundary | 74-file Cloud manifest, package tests | Stage 7/8 regression passed |
| 7.2 P5 preservation | Provider lock and clean-source safety tests | Provider and separate Host/Count locks reviewed; new P5 publication remains independent |
| 7.3 Python 3.12 | Pinned install and clean-source tests | `.venv312` 3.12.16 and `pip check` passed |
| 7.4 Fake/no-key runtime | Packaged Streamlit, synthetic Planning and AI preview | No-key regression passed |
| 7.5 Security/data | Secret/path/package boundary tests | New P5 source scanned; Cloud package remains separate |
| 7.6 Reproducible candidate | Two prior Stage 8 package builds | No Cloud package or Stage 7 acceptance status changed |

## Technical review

The P5 implementation has a request-bound exact-count evidence type, a separate signed Host Owner authorization, a signed one-use Generation Permit, a paid Ledger reservation, an append-only Archive, and a Host response record. The count evidence for historical EV-01 belongs to a closed Run and is not reusable for a new request. The Source Publication report identifies the newly published dependencies. The Provider's real path retains `REAL_PROVIDER_DISPATCH_LOCKED = True` and its trusted real count dispatch is intentionally incomplete. The separate Host Generation and Count Runner routes now have independent default-closed locks before credential access.

The published source has all three lock assignments set to `True`: `REAL_PROVIDER_DISPATCH_LOCKED`, `REAL_TOKEN_COUNT_DISPATCH_LOCKED`, and `REAL_GENERATION_DISPATCH_LOCKED`. Source search found no alternate assignment. Offline tests use injected Fake transports and cannot create a paid request in the sandboxed environment.

The approved P5 policy remains US$0.02 per call and US$0.16 across eight reserved slots, below the Owner's first-round US$1 target. Reservations use a SQLite immediate transaction, are sequential, and keep ambiguous results held. These limits govern local authorization, not final provider billing. No software-only check in the current design can guarantee a provider-side US$1 charge ceiling; see the Budget Control report.

## First offline trial plan

Use one fresh synthetic EV-01 Run; verify current model entitlement, exact count payload, count response identity and projection digest; review the same Generation payload and estimate; obtain independent Owner Approval and Generation Authorization; verify Ledger and Archive intent; exercise success, refusal, timeout, HTTP error, missing usage and uncertain outcome with Fake transport; verify no retry. Only after separate future paid authorization may a real request be considered. The approved P5 campaign permits at most eight sequential cases and requires reconciliation and review between cases.

| Suggested first-round case | Requests | Input tokens | Output cap | Example Standard-text estimate* |
| --- | ---: | ---: | ---: | ---: |
| Fresh EV-01 | 1 exact count + 1 Generation | unknown until fresh exact count; planning example 4,000 | 25,000 | US$0.0129 Generation only |
| EV-02 only after EV-01 reconciliation | 1 exact count + 1 Generation | planning example 4,000 | 25,000 | US$0.0129 Generation only |

*Two conditional Generation requests total about US$0.0258 at these assumptions. The [official GPT-6 Luna page](https://developers.openai.com/api/docs/models/gpt-6-luna) listed US$0.10/M input and US$0.50/M output Standard-text rates on this report date. The [input token count guide](https://developers.openai.com/api/docs/guides/token-counting) says the endpoint counts the exact submitted payload; a new request needs fresh evidence. The estimate excludes both count operations' cost, account terms, taxes and other billing factors. It is not an exact count or hard bill ceiling. The per-case US$0.02 local policy still applies. Do not execute even one real request under this report.

## Decision

**NOT READY for a real API request.** The reviewed P5 execution graph has been published and its clean committed source passed offline tests. Remaining gates: fresh exact evidence for the selected Run, current account pricing/entitlement verification, trial-wide accounting for any count-operation charge, reconciliation of any prior unknown charge, Windows-native Host qualification, and a separately authorized Owner-controlled unlock. The Owner's US$1 planning target is not permission to spend or to remove either dispatch lock.

## Evidence and next steps

Environment: `.venv312/bin/python` 3.12.16; `pip check` passed after installing the pinned `cryptography==46.0.7` into the project virtual environment. See the Source Publication, Provider Integration and Budget Control reports for exact commands, test results, limitations and Git disposition. No key or user data is reproduced here.

P5 source commit `0c90b0a955d5c0ab1ab22b1ac962c56af3d73e97` was pushed to `origin/main`; post-push fetch verified the same remote SHA. Its fresh clean-committed-source archive passed 109 main P5/Windows, 78 supplementary P5/Windows and 30 Stage 7/8/security tests; exact commands are in the Source Publication report. Report publication is a separate documentation batch and does not alter the code qualification.

Files created for this decision record: this report, `P5_EXECUTION_SOURCE_PUBLICATION_REPORT.md`, `AI_PROVIDER_INTEGRATION_READINESS_REPORT.md`, `LOCAL_AI_TRIAL_BUDGET_CONTROL_REPORT.md`, and `PUBLIC_CLOUD_QUOTA_ARCHITECTURE_DECISION.md`. Exact P5 implementation and test paths are enumerated in the Source Publication report. No Planning Engine business rule, Cloud Secret, production deployment configuration, or real Provider lock was changed.

Stage 7/8/security regression command, with `OPENAI_API_KEY` removed: `env -u OPENAI_API_KEY .venv312/bin/python -B -m unittest tests.test_stage7_cloud_release tests.test_stage8_local_runtime tests.test_ai_copilot_provider tests.test_ai_copilot_approval tests.test_ai_copilot_ledger tests.test_ai_copilot_execution_gate` — 30 passed, 0 failed, 0 skipped in the working tree; the same 30 passed in a clean HEAD plus reviewed candidate overlay, in the exact 69-file staged snapshot, and in a fresh archive of committed source `0c90b0a`. This is regression evidence, not a new formal Stage 7 acceptance or Cloud runtime result.

The original Stage 7 safety/acceptance command, run from the fresh committed-source archive, was `env -u OPENAI_API_KEY /workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_stage7_cloud_release tests.test_p5_paid_readiness_adapter tests.test_ai_copilot_provider tests.test_ai_copilot_approval tests.test_ai_copilot_ledger tests.test_ai_copilot_execution_gate tests.test_ai_copilot_eight_call_campaign`: 49 passed, 0 failed, 0 skipped. This independently rechecks the original local Stage 7 boundary; paid AI and Cloud runtime acceptance remain separate.

The broader Stage 8 public-functionality command, run from the same fresh archive, was `env -u OPENAI_API_KEY /workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_stage8_local_runtime tests.test_dashboard_app tests.test_comparison_dashboard tests.test_phase2_workflow tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_question tests.test_stage6_cloud_provider`: 63 passed, 0 failed, 0 skipped. Streamlit emitted `use_container_width` deprecation warnings; they did not fail this local run. No Cloud deployment or browser acceptance was executed.
