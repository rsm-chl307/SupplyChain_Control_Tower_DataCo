# P5-C — Eight-invocation budget and authorization proposal

Prepared 2026-11-22 UTC for Owner review. **DESIGN ONLY.** No ledger migration, allowance provisioning, model setting, SDK, provider dispatch, API key or paid call was performed. GPT-6 Luna (`gpt-6-luna`) is the only candidate. Local-first evaluation remains mandatory.

## Campaign shape and protected state

Propose a **new**, separately provisioned local campaign version with exactly eight named slots: EV-01–EV-07 and the proposed EV-08-LR after its trusted fixture/Brief gate passes. Do not alter, reset, migrate implicitly, or reuse the existing `v1.2-first-paid-acceptance` one-allowance row. Preserve its approval and event history.

Before provisioning, freeze a canonical campaign manifest: fixture/corpus version, case ID and selected scenario, exact live Brief and projected Brief digests, Request Digest, model identifier/snapshot policy, schema/instruction/privacy versions, input/output/timeout limits, pricing basis, per-slot ceiling and aggregate ceiling. An Owner approval of the campaign **and eight distinct explicit one-use approvals** for the exact eight request digests are required. The existing P3 approval and ledger code does **not** implement this policy. A new service/ledger implementation and security/concurrency tests require separate authorization; these paragraphs do not activate it.

Proposed durable SQLite invariants:

1. Explicit provisioning only, with stable database identity and fail-closed opening. Unique `(campaign_id, case_id)`, unique approval reference and request digest per slot; exactly eight allowlisted case IDs. Owner verifier stays separate from Demo login.
2. `BEGIN IMMEDIATE` transaction for each reservation: revalidate live trusted Brief, canonical request and exact digest, unexpired/unrevoked/unconsumed Owner approval, model and cost policy, unused slot, no campaign hold, and `sum(reserved_slot_ceilings) + new_slot_ceiling <= approved_campaign_ceiling`. Consume that approval, reserve one slot allowance and its full ceiling, and append an audit event in the **same transaction**. Roll back all changes on failure.
3. The aggregate commitment remains the sum of full slot ceilings, including completed, failed and UNKNOWN slots, through campaign closure. Do not recycle a slot after failure, timeout or success. Store estimate, observed usage, provider charge and source of charge separately. If an observed charge exceeds its ceiling or the campaign ceiling, halt new dispatch and require Owner reconciliation; local ceilings are **not** provider-side billing guarantees.
4. Allowed state path per slot: unreserved `NOT_STARTED` → reserved `NOT_STARTED` → `IN_PROGRESS` only when authorized submission begins → `SUCCEEDED` or definitive `FAILED` or `UNKNOWN`. Timeout, crash, interrupted submission and ambiguous status are `UNKNOWN`; after a process restart, unresolved `IN_PROGRESS` is held for Owner reconciliation and never replayed automatically. `UNKNOWN` retains cost and allowance reservations. No transition automatically returns it to `NOT_STARTED`.
5. On an unresolved `UNKNOWN`, `IN_PROGRESS` after restart, identity failure or over-ceiling observation, place the whole campaign on hold. Owner-authenticated manual reconciliation records sanitized evidence, usage, charge, provider request ID, time and conclusion; it never silently grants another invocation. No retries, fallback dispatch or resubmission. Any replacement call would require a new separately authorized campaign decision.
6. On restart, read durable SQLite identity, eight slot rows, consumed approvals, campaign total and event chain before exposing eligibility. Session state is display-only. Concurrent processes must contend on the same local database lock and unique constraints. Test crash points before/after reservation and before/after dispatch with deterministic local doubles.

This is **local single-machine SQLite** design. Multi-host or Cloud operation is outside P5-C and remains prohibited.

## Output-token and request-size decision

Current `build_request()` accepts `max_output_tokens <= 2500` and timeout `<=60` seconds. The existing P1 schema requires a complete JSON object with all sections. The [OpenAI reasoning guide](https://developers.openai.com/api/docs/guides/reasoning), verified in the 2026-11-22 P5-A/B report, says the output cap includes hidden reasoning and formatting tokens and can yield `incomplete` before visible JSON. The generic initial guidance of at least **25,000** reasoning-plus-output tokens is not a Luna-specific requirement. No Luna output, token profile or latency was observed.

**Proposal for future evaluation, not a setting change:** budget a maximum of **25,000 output tokens per invocation**, including reasoning, and enforce an **at-most 16,000 input-token gate** after measuring the exact outgoing request using the chosen model's verified method. This output cap exceeds current P2 builder policy and cannot be used without an explicit later adapter/request-policy change and its own tests/approval. If exact input exceeds 16,000, or the complete JSON does not fit the approved output/timeout policy, **stop and recalculate**; do not truncate the Brief, weaken schema or retry automatically. Reasoning effort is **UNDECIDED**; no production setting is chosen. The current 64 KiB canonical request-body cap is bytes, not a verified input-token bound.

## Itemized estimate, **not an observed charge**

Pricing evidence is the [official Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) checked **2026-11-22** in P5-A/B: standard input $0.10, cached input $0.01, output $0.50, cache write $0.125 per million tokens. **No new network check was made for this proposal.** Rates must be rechecked before paid authorization. Account-specific taxes, regional terms, cache behavior, entitlement and actual billing are unknown.

For a conservative **planning envelope**, assume no cached-input discount, 16,000 maximum measured input tokens and 25,000 maximum generated tokens per call. The envelope intentionally adds the uncached input rate and the listed cache-write rate as a stress allowance even if actual billing treats them as alternatives: `16,000 × ($0.10 + $0.125) / 1,000,000 + 25,000 × $0.50 / 1,000,000 = $0.0161`. A 10% regional sensitivity would be `$0.01771`, within the **proposed $0.02 per-call ceiling**. These are budget assumptions, not an assertion that cache writes or regional processing will occur. The ceiling is a suggested Owner decision, **NOT SET** in production.

| Proposed slot | Input cap | Output cap, including reasoning | Stress estimate | Proposed per-call ceiling | Actual charge |
|---|---:|---:|---:|---:|---|
| EV-01 capacity | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-02 demand surge | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-03 disruption | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-04 inventory | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-05 service | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-06 trade-offs | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-07 uncertainty | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| EV-08-LR low risk, pending trust | 16,000 | 25,000 | $0.0161 | $0.0200 | NOT OBSERVED |
| **Eight-call total** | **128,000 cap across calls** | **200,000 cap across calls** | **$0.1288** | **$0.1600** | **NOT OBSERVED** |

The proposed aggregate ceiling is **$0.16**, the sum of eight $0.02 slot ceilings, not a default production budget or API-side spend guarantee. It provides $0.0312 over the stress estimate. Any actual measured input-token count, changed official rate, cache/write treatment, taxes, minimum charge, regional processing, output policy or provider charge outside these assumptions requires recalculation and new Owner approval. A charge can occur for an incomplete or refused response. No automatic retries may consume additional funds.

## Alias, entitlement, retention and exact payload

- Official API ID `gpt-6-luna` is documented; a dated Luna snapshot was **not verified** in P5-A/B. Prefer a documented immutable snapshot for eight-call comparability. If none is available, Owner must explicitly decide whether the moving alias risk is acceptable for this bounded study; record per-response model metadata and dates. No production snapshot is set here.
- Confirm model availability in the **intended API organization and project** only after separate authorization. ChatGPT access or published rate-limit tiers do not prove entitlement. No key or account was accessed now.
- Review current official data handling and account controls before consent. `store=false` avoids ordinary saved response objects but does not promise zero retention; default abuse logs, temporary state and exceptions remain relevant. Use only the minimized synthetic provider projection; USER_DATA is excluded.
- For every call, Owner reviews the **exact serialized outbound arguments** from the current adapter mapping: model, instructions, projected synthetic Brief, strict P1 response schema, output cap and fixed no-tool/no-stream/no-background/no-retry options. Locally retain complete Brief provenance. Display and approve full Brief Digest, projection digest, exact Request Digest and the corresponding cost ceiling. A changed byte or expired Context/approval requires a new explicit review; never auto-reapprove on rerun.

## Owner review gate

Approve or reject the corpus revision with EV-08-LR; approve the separate trusted fixture issuer design; choose eight-call campaign and ledger implementation authorization; approve or revise per-call and total ceilings, pricing basis, output/input/timeout/reasoning policy, alias/snapshot policy, account/retention conditions and exact synthetic payload. **Do not execute P5-D/P5-E or provision allowances from this proposal.** Paid acceptance and P6 remain NOT AUTHORIZED.
