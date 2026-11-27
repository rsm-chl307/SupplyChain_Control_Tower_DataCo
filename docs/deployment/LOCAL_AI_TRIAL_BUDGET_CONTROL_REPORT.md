# Local AI Trial Budget Control Review

Date: 2026-11-27. Objective: assess first-round US$1 total target without making a paid request or weakening approved P5 limits.

Scope and files: this report is the only budget-policy document created in this task. The reviewed `src/ai_copilot/eight_call_campaign.py`, `tools/windows_api_runner/generation_permit.py` and their tests were published in the P5 source commit. No budget constants, production quota, paid approval, or Cloud Secret was modified.

## Existing controls

The paid P5 policy fixes `OWNER_PER_CALL_MICRO = 20000` (US$0.02) and `OWNER_TOTAL_MICRO = 160000` (US$0.16) across eight sequential cases. The campaign reserves the full case ceiling in SQLite under `BEGIN IMMEDIATE`; a second reservation cannot bypass the aggregate ceiling. Only one in-progress or unknown slot is permitted, later slots require previous charge evidence and human review, and an uncertain dispatch is not retried automatically. Approval, exact count, payload, Generation proof and Ledger claim are identity-bound. The Provider, Count Runner and Generation Host real routes remain locked by default. These are stronger local reservation bounds than US$1 and leave US$0.84 nominal headroom.

The Count Runner is a separate workflow. Its real transport is now locked, and its API operation has no shared cross-campaign monetary reservation in the Generation Ledger. Before any future paid count request, an Owner-approved policy must account for its possible charge and bind the same trial-wide budget. Simply adding US$0.84 nominal headroom does not solve this gap.

The US$0.16 reservation is scoped to one approved eight-case campaign database. It is not a global, durable US$1 aggregate across separately provisioned campaigns or credential uses. A future trial-wide hard local gate would need one canonical durable store shared by Count and Generation, atomic reservations across both, and fail-closed behavior when that store is unavailable. Implementing that cross-boundary authority would change the approved Host/Container workflow and still could not retroactively bound a Provider-side bill; it requires a separate design and Owner decision before paid execution.

## Why US$1 cannot be a billed-charge hard cap yet

The Provider's [Responses schema](https://developers.openai.com/api/reference/resources/responses/methods/create) contains token usage but no authoritative final monetary charge. Input count does not bound output price changes, account-specific rates, taxes, or count-operation charges. A request can time out after being billed. The Container Ledger, Windows Host state and Archive are independent stores, so no distributed exactly-once guarantee exists. Local process or SQLite gates cannot prevent a provider from billing more than an estimate after dispatch. Even OpenAI's [project hard spend limit](https://developers.openai.com/api/docs/guides/spend-limits) is not enforced instantaneously and recorded spend can slightly exceed it. The current system therefore **fails closed for further requests** when charge is unknown, but cannot guarantee the first request's billed amount stays below US$1. Do not call this a hard US$1 cost guarantee.

## Required local trial procedure

Before any separately authorized real trial: confirm a Provider-side account/project spend limit as an additional control, current model price and entitlement, exact request token count, maximum output, count-endpoint billing, and a conservative estimate below the existing US$0.02 per-call reservation. Keep one request in flight, use the current SQLite campaign, record model/usage/latency/response and separately reconcile actual billed charge. Missing usage, charge or uncertain outcome holds the campaign; no automatic retry. The Owner must explicitly accept that US$1 is a local reservation target with safety buffer, not a guaranteed bill cap, before any paid call; a Provider hard limit still does not make an absolute guarantee.

A dedicated project with no other API traffic and a project hard limit materially below US$1 would reduce exposure if the Owner can configure it. The exact threshold requires the Owner's account settings and expected billing factors; this repository cannot set or verify it. The existing US$0.16 Generation reservation and one-at-a-time workflow leave US$0.84 for unmodeled charges, but neither replaces charge reconciliation or a shared quota for count operations.

## Offline tests and acceptance

The present review did not spend funds. Offline tests cover reservations, sequential order, one-use claims, missing usage, unknown outcomes and Host permit handling; both the exact staged snapshot and fresh committed-source archive passed 109 P5/Windows, 78 supplementary P5/Windows and 30 Stage 7/8/security tests with commands in the P5 Source Publication report. The reviewed P5 source was committed as `0c90b0a955d5c0ab1ab22b1ac962c56af3d73e97` and post-push fetched remote SHA matched. **US$1 provider-billed hard cap: NOT VERIFIED / NOT CLAIMED.** First-round real call: NOT AUTHORIZED. No budget policy constant was raised or loosened.
