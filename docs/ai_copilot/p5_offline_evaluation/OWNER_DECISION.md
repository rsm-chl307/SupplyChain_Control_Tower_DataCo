# Owner decisions and authorization gates

Current decision (provided for this task): **GPT-6 Luna is the first candidate.** Adopt it only if evidence shows acceptable quality; do not move to a higher-tier model merely for marginal improvement. If it fails, report specific deficiencies and return for Owner review. This is a candidate-order decision, **not** a verified API model ID, production snapshot, budget, transfer consent or paid-call authorization.

| Item | Current state | Decision needed before paid acceptance |
|---|---|---|
| Documented API model ID | NOT VERIFIED in repository evidence | Verify against current official documentation and account entitlement. Do not guess from display name. |
| Exact dated model snapshot | UNDECIDED | Select and freeze an eligible snapshot; verify Responses and strict schema compatibility. |
| SDK/runtime behavior | NOT VERIFIED; real adapter blocked | Approve a pinned SDK and offline/runtime validation plan, including retries, refusal, incomplete, timeout and usage mapping. |
| Input/output limits | Request body ≤64 KiB; explicit output cap 1–2500; timeout >0–60 s; no encoded input token cap | Verify Luna context/output limits and count exact request tokens; approve the specific limits for the paid request. |
| Pricing basis and estimate | UNSET | Verify current rates and billing units; calculate a conservative estimate for the exact request and selected snapshot. |
| Owner maximum cost ceiling | NOT SET | Set an explicit one-call ceiling that is ≥ approved estimate; no default. |
| Provider data handling | NOT REVIEWED for Luna/account | Approve the exact minimized synthetic projection and current processing/retention terms; `store=false` alone is insufficient. |
| Evaluation breadth | Eight offline cases; current ledger grants one paid allowance | Decide whether one separately authorized smoke call is enough for the next gate or whether a separately designed multi-case paid evaluation is needed for model adoption. Do not reset the ledger to extend the allowance. |
| Low-risk coverage | Only a low-risk lost-sales signal within an At Risk Brief | Decide whether to authorize a new trusted synthetic low-risk fixture or accept an explicit coverage limitation. Do not weaken the Context issuer or change pinned hashes silently. |
| Quality rubric | Proposed 0–4 weighted rubric and critical gates | Review/approve quality gates before observing paid outputs; do not change them after seeing an unfavorable result merely to pass. |
| Exact paid request and Owner Approval | NOT AUTHORIZED | Review canonical Brief, provider-facing projection, both digests, Request Digest, cost policy and ledger state; approve the exact one-call action separately. |
| P6/Cloud | NOT AUTHORIZED | Separate identity, durable multi-instance ledger, secrets and runtime validation decision. |

Candidate order does not imply production activation. If GPT-6 Luna fails a future authorized test, the next action is a documented Owner review, not an automatic model switch or additional paid call.

## P5-R / P5-C decision update — 2026-11-22

**Decided by Owner:** GPT-6 Luna (`gpt-6-luna`) remains first candidate; a complete eight-invocation evaluation is required; local-first; no higher-tier model search or automatic switch. The earlier one-call smoke-test option is no longer the acceptance objective. This update does not change `cases.v1.json`, the P3 one-allowance ledger or the paid-authorization status.

| Decision still required | Current proposal / consequence |
|---|---|
| Genuine Low-risk case admission | `tests/fixtures/p5_low_risk_v1/` is independently pinned and produces `Healthy` deterministic output. Approve a separately reviewed V1.1 trusted Context pathway for this second fixture, and approve a new eight-case corpus version replacing original EV-08 with EV-08-LR. Until then the eighth paid case is on hold. |
| Reviewer procedure | Approve `EIGHT_CASE_REVIEWER_WORKSHEET.md` and keep existing rubric thresholds unchanged before seeing model output. Two independent reviewers and Owner adjudication proposed. |
| Eight-slot ledger | Authorize a new explicit campaign implementation, provisioning and concurrency/crash tests. Do not reset or increase the existing P3 allowance. UNKNOWN and unresolved IN_PROGRESS must hold the campaign; no retries. |
| Model identity | Official API alias is `gpt-6-luna`; no dated snapshot was verified in P5-A/B. Prefer a dated immutable snapshot; otherwise explicitly accept moving-alias risk for the bounded study. No production snapshot selected. |
| Token policy | Current cap is 2,500 output tokens. Proposed evaluation cap is 25,000 including reasoning and measured input gate 16,000; this needs later authorized code/policy work, not a setting change in P5-C. Reasoning effort and timeout remain undecided. |
| Cost | `P5_C_BUDGET_AND_AUTHORIZATION_PROPOSAL.md` gives a conservative $0.0161 stress estimate per call, proposed **$0.02 per-call / $0.16 total** ceilings. Both ceilings are **NOT APPROVED / NOT SET**; recheck official rates and actual input counts before approval. |
| Account and privacy | Verify intended API org/project model entitlement and rate limits; review current retention and approve exact minimized synthetic payload, Brief/Request Digests and local retention. `store=false` is not zero retention. |
| Separate paid permission | Explicit Owner authorization for the **specific eight-call campaign** remains required after every gate; P5-D/P5-E/P6 are not authorized. |

### Task 1 trusted admission result — 2026-11-22

The low-risk fixture now has an explicit trusted Context path and passes synthetic-only admission tests. The earlier admission row is historical. Still required: approve a versioned eight-case corpus replacing original EV-08 with the low-risk case, then separately authorize any eight-slot Ledger implementation, budget and paid evaluation. No allowance or paid permission was created by fixture admission.
