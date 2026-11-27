# AI enablement blocker audit

Date: 2026-11-27. Objective: reconcile committed and local AI safety behavior before any real AI activation. Scope: local/offline remediation only; no Cloud deployment, production Secrets, paid API call or real-provider unlock. Environment: `/workspace/SupplyChain_Control_Tower_DataCo`, branch `main`, `.venv312/bin/python` 3.12.16. Preflight HEAD and fetched `origin/main`: `7ba4cac1bf6967b57dc39f3d4c69be5c7b63c68c`; zero staged entries; 125 preserved worktree entries (24 modified, 101 untracked).

## Root cause and historical review

The committed `src/ai_copilot/provider.py` remained the earlier P2 offline adapter. Commit `cf313b1` published the Cloud-safe `provider_base.py`, Cloud service and Cloud question path but did not publish the local P5 `provider.py` refactor. The worktree P5 refactor imported that base, retained `REAL_PROVIDER_DISPATCH_LOCKED = True`, and introduced `execute_authorized()` plus offline mock behavior. Its wider historical P5/Windows graph remains partly modified or untracked and was deliberately excluded from the prior GitHub synchronization. Thus Stage 7's local lock test passed while the same test failed on clean GitHub source. The missing lock was a source-publication mismatch, not a Python 3.12 or Cloud package defect.

The reviewed P5 provider checks the real-dispatch lock before loading campaign modules, credentials or network transport. The ordinary `execute()` path remains blocked. Offline `execute_mock()` requires the exact `OfflineMockTransport` type, a digest-bound validated Brief and a fixed P5 mock profile. The paid `execute_authorized()` path also requires campaign, archive, exact token evidence, one-use claim and record-on-uncertainty when those local modules are present. The historical WP4 reports record stale EV-01 exact-token evidence and no separate Generation authorization. No historical P5/Windows set was bulk-staged.

Remediation in this task: publish only the reviewed local Provider boundary and focused Stage 7/P5 tests; make an absent paid campaign runtime fail closed as `ProviderBlocked` instead of exposing an import error. The test asserts a locked paid request cannot call `urllib.request.urlopen`. This preserves the lock and does not activate a provider. Exact file list and committed SHA are in `STAGE_7_REMEDIATION_REPORT.md`.

A separate clean-source Planning regression exposed 13 test errors in `tests/test_phase1_risks.py`: the test read a fixed Git-ignored `tmp` Run that existed only on the developer worktree. The repair generates a disposable published Run from tracked synthetic inputs before the test's planning guards are installed, then compares loaded rows to that generated artifact. No runtime output or business-rule change is committed. This was a test reproducibility blocker, not a Planning Engine calculation failure.

## Independent security boundaries and remaining blockers

| Area | Audit finding | Disposition |
| --- | --- | --- |
| P5 local provider | Clean source lacked the lock and authorized entry; worktree had both | Repair and test from clean committed source |
| Credential management | Cloud key is read from backend Streamlit Secrets only when requested; Windows credential source is separate; missing/invalid key raises a sanitized error | Existing behavior tested offline; no production Secret accessed |
| Cloud access/dispatch | Password verifier and signed process-local grant precede `CloudAIService` reservation; one-use ticket binds exact wire bytes before `CloudOpenAIProvider` transport; missing key and invalid ticket do not send | Existing Stage 6/Cloud tests; default real-provider setting is false |
| P5 Approval/Ledger | Local Owner verifier, digest-bound approval, durable SQLite reservation and one-use claim are separate from Demo login; ordinary Provider call cannot dispatch | Existing committed tests plus P5 offline mock test |
| Planning authority | Provider receives a minimized, validated Brief and response is schema/evidence validated; Planning Engine calculations are unchanged | Planning and Cloud regression tests |
| Paid P5 activation | Matching fresh exact token count, separately authorized Generation, and the larger unpublished P5 campaign/archive/Windows execution set remain absent from clean source; the real branch also has an unconditional fail-closed exact-count gate after the dispatch lock | **BLOCKED**; do not infer paid readiness from the lock repair |
| Public Cloud paid AI | Quotas and access grants are process-local; no durable global spending cap or live Cloud runtime/Secrets evidence exists | **BLOCKED** pending separate architecture/Owner decision and deployment authorization |

The Cloud and P5 paths are distinct. A locked local P5 dispatch does not itself prove that a separately configured Cloud provider is safe for public paid use. The current Cloud path is disabled by default, requires authenticated backend service authorization and a key, and is tested with Fake/recording transport; no real transport was used here. Actual multi-worker quota and billing behavior cannot be established offline.

## Scope, evidence and next step

Files inspected: Stage 7 specification/acceptance and Stage 8 reports; `provider.py`, `provider_base.py`, `cloud_access.py`, `cloud_ai_service.py`, `cloud_question.py`, `credential_provider.py`, `execution_gate.py`, `approval.py`, `ledger.py`, P5 campaign/archive/token modules and their tests; `ai_agent_implementation_spec.md`, developer notes and project journal were reviewed without altering their unrelated user edits. No frozen Planning business rule changed. Exact test commands, counts, clean-source results, commit and push evidence are in the two companion reports. Of the original 125 worktree entries, the relevant Provider and two test files were committed after review; all other pre-existing user work was left intact. The separate Phase 1 test fix and these reports are the only additional paths changed for this task. No credential value or Secret is recorded here. Stage 7 local release-preparation acceptance and paid AI enablement readiness are separate decisions.
