# AI Decision Copilot V1.2 — P5 Eight-Call Ledger Design Report

Date: **2026-11-22 UTC**. **Decision: READY FOR OWNER IMPLEMENTATION AUTHORIZATION** for a separate **offline-only Ledger implementation stage**, subject to the explicit design decisions below. This document does **not** approve provisioning, eight actual allowances, a budget, API execution or production activation. The implementation-ready specification is [EIGHT_CALL_LEDGER_IMPLEMENTATION_SPEC.md](p5_offline_evaluation/EIGHT_CALL_LEDGER_IMPLEMENTATION_SPEC.md).

## Sequencing and evidence baseline

Task 1 Trusted Context Admission was completed **before** this read-only Task 2 review. Its [completion report](AI_COPILOT_V1_2_P5_LOW_RISK_TRUSTED_ADMISSION_REPORT.md) records **PASS**: new admission 5/5, V1.1 Context/lifecycle 34/34, P5/P1/P2/V1.1 offline regression 26/26, independent fixture 1/1, original fixture hashes unchanged and no real provider dispatch. Task 1's remaining corpus-version and paid-policy decisions do not impair TrustedBrief integrity, Request Digest binding, Owner Approval or the existing Ledger. They are prerequisites for future campaign provisioning.

Task 2 inspected actual `src/ai_copilot/ledger.py`, `approval.py`, `execution_gate.py`, `provider.py`, the Task 1 `src/synthetic_context.py` changes, relevant P3 tests, the P5-C budget proposal and eight-case reviewer worksheet. The original P3 store has fixed `CAMPAIGN_ID`, one row keyed by campaign and `allowance=1`; its `reserve` transaction consumes a digest-bound approval under `BEGIN IMMEDIATE`. Owner verification is separate from Demo; the local file identity marker and SQLite checks fail closed. `UNKNOWN` and manual reconciliation preserve the one allowance. `LocalExecutionGate` binds a live `ValidatedBrief` to the canonical request and has no provider execute method.

## Architecture decision

The specification proposes a **new, explicitly provisioned local SQLite store** and versioned campaign, leaving the existing P3 database/schema/campaign untouched. The campaign freezes exactly eight case templates: EV-01–EV-07 and EV-08-LR. Each actual slot binding is created only at atomic reservation from a live trusted Brief and explicit one-use Owner approval. Unique `(campaign_id, case_id)` and approval references prevent slot reuse. The campaign and approval digest bind case identity, request/Brief/projection digests, model/policy versions, exact limits and cost ceilings. Session state never grants authority.

The earlier P5-C proposal suggested unique Request Digests across slots; this cannot safely be required as a database constraint. EV-01 and EV-07 can use identical Baseline Brief inputs and therefore share an outbound digest. The new design permits identical request bytes for separately named slots **only with separate explicit Owner approvals and allowances**. This does not permit duplicate execution of one slot. It is a documented design refinement, not an alteration of existing cases.

V1.1 Contexts are live and expire after 300 seconds. Therefore an immutable campaign roster can exist before requests, but exact per-slot digests must be bound just in time. An unreserved slot may be prepared afresh and explicitly approved. Once reserved, its digest and allowance cannot be rebound or recycled after expiry, process restart, timeout, refusal or UNKNOWN. A reserved-but-undispatched slot whose Context is gone is held for Owner review; a replacement invocation requires separate campaign authorization.

## State, cost and audit controls

The five execution states are `NOT_STARTED`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED` and `UNKNOWN`. Unreserved and reserved `NOT_STARTED` are distinguished by the presence of a durable reservation. The only dispatch transition is reserved `NOT_STARTED` → `IN_PROGRESS` with one durable attempt marker immediately before submission. A crash at that boundary is ambiguous and never auto-retried. `UNKNOWN` retains the full slot allowance and ceiling; unresolved `IN_PROGRESS` on restart holds the campaign. Owner-attested reconciliation appends evidence and never restores a slot.

The P5-C planning numbers are **$0.02 per slot and $0.16 aggregate**, still proposals. The stress estimate is $0.0161 per call / $0.1288 for eight using the earlier documented 16,000-input/25,000-output token envelope and intentionally additive cache-write allowance. The Ledger design stores exact integer micro-USD ceiling/reservation, distinct estimate and observed charge fields, and checks the aggregate under `BEGIN IMMEDIATE`. Successful, failed and uncertain slots retain their full ceiling commitment. Observed over-ceiling charges are recorded and hold the campaign; local policy cannot cap the provider's actual bill. Missing usage/charge prevents a fully reconciled success.

Append-only event types cover provisioning, campaign and slot approvals, revocation, reservation, dispatch start, provider outcome, usage/charge, UNKNOWN, reconciliation and Owner decisions. Event records exclude API keys, passwords, full Briefs, request/response bodies and raw errors. A local administrator or compromised Python process remains outside the trusted local-process guarantee; SQLite event constraints are not a tamper-proof external audit system. Cloud/multi-instance operation is deferred to P6.

## Failure and recovery

The specification includes a matrix for pre-reservation crash, post-reservation/pre-dispatch crash, crash during dispatch, timeout after provider acceptance, refusal, incomplete result, missing usage/charge, over-ceiling observation, missing/replaced/corrupt DB, duplicate click, concurrent processes, Context expiry and local-process compromise. All uncertain billing or submission states hold their reservation; there is no automatic retry, fallback, database reprovisioning or allowance restoration. The existing P3 one-call state/history is preserved and never migrated destructively.

## Implementation authorization boundary

Suggested later modules are `eight_call_campaign.py`, `eight_call_store.py` and `eight_call_gate.py`, with temporary-DB, synthetic-only security/concurrency tests. This task created **none** of them. Before authorizing that implementation, the Owner should accept three explicit design points: (1) exact digest binding at just-in-time reservation, (2) identical outbound digests allowed across **different** case slots with distinct approvals, and (3) fail-closed handling of a reserved but never dispatched slot. The future implementation must keep the P3 API/schema and one-call allowance untouched.

Before **paid acceptance**, separate decisions remain: a versioned eight-case corpus with EV-08-LR, documented model snapshot or explicit alias policy, exact input/output/reasoning/timeout settings, current account entitlement and data controls, exact minimized synthetic payload and Request Digests, actual Owner-approved per-call/aggregate ceilings, and eight specific call approvals. The current P2 2,500 output-token limit cannot implement the P5-C proposed 25,000 cap; any change needs its own authorization and tests. No production model setting was selected.

## Deliverables and validation

Created only:

- `docs/ai_copilot/p5_offline_evaluation/EIGHT_CALL_LEDGER_IMPLEMENTATION_SPEC.md`
- This design report.

Task 2 performed read-only source inspection. No Ledger, Approval, Provider Adapter, fixture, test, production setting or deployment code was modified for Task 2. A local documentation consistency check confirmed that the specification names all eight slots, all five states, the SQLite transaction/budget design, approval and recovery rules, and the proposed ceilings; the report summarizes those controls. Both documents have a final newline and no trailing whitespace. `git diff --check` passed (exit 0). New untracked documents were also checked directly because Git does not include them in `git diff --check`. No mixed-data or paid tests were run for Task 2.

**P5 paid execution: NOT AUTHORIZED. P5-D/P5-E: NOT STARTED. P6: NOT AUTHORIZED.** No USER_DATA access, API key access, OpenAI API call, SDK installation, external network request, charge, commit, push or deployment occurred.
