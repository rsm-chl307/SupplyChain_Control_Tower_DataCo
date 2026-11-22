# P5-D offline quality evaluation implementation plan

Prepared 2026-11-22 UTC. This is the plan completed before P5-D source changes. It authorizes no API request or paid campaign.

## Current state and gaps

P1 `validate_response` checks the closed schema, live `ValidatedBrief`, exact numerical evidence slots, references, and suspicious prose quantities. `classify_response` separates validated, refusal, incomplete, unknown and invalid outcomes. It does not judge causal reasoning, recommendation usefulness, trade-offs or communication. The existing 0–4, eleven-dimension rubric is historical and remains unchanged; this P5-D proposal uses six separate 1–5 quality dimensions and must not silently reinterpret old scores. The eight-call Ledger is separately provisioned and strictly `OFFLINE_TEST`, with no provider dispatch. `cases.v1.json` still contains the old EV-08; the admitted genuine Low-risk fixture is not yet in a versioned eight-case corpus.

## Implementation architecture

1. Create `cases.v2.json` as an explicit, versioned eight-slot corpus: retain EV-01–07 from v1 with their evidence; add EV-08-LR backed by a live Low-risk `ValidatedBrief`. Do not alter v1 or pinned fixture bytes. Add synthetic-only evidence tests.
2. Specify six human quality dimensions: Factual Accuracy 25, Root Cause Analysis 20, Recommendation Quality 20, Decision Trade-off 15, Context & Risk Awareness 10, Communication Quality 10. These are proposed weights, not Owner-approved policy. P1 technical status remains a hard prerequisite, not a quality dimension.
3. Add `src/ai_copilot/quality_evaluation.py` containing frozen provenance/reviewer/result records, exact deterministic Decimal scoring, explicit critical-failure categories, adjudication and eight-case aggregation. It receives verified P1 status and reviewer judgments; it never scores prose automatically or calls a model.
4. Extend the worksheet with independent reviewer and Owner adjudication records. Every score needs evidence/rationale. Missing scores, provenance, technical validity or adjudication yield INCOMPLETE, never PASS. Human disagreement is recorded, not silently averaged.
5. Add a P5 paid-readiness document with current official OpenAI documentation evidence, exact privacy projection categories, cost proposal and remaining blockers. No production adapter, Ledger mode, SDK or budget changes.

## Proposed quality and acceptance policy

Each dimension is an integer 1–5. Weighted case score is `sum(weight × score)/5` out of 100 using exact Decimal arithmetic. No N/A in the initial eight-case policy: a dimension with weak or absent content is scored 1, with a cited case-specific reason. A different N/A policy requires Owner approval and a version change. Proposed case PASS: P1 VALIDATED, all six scores present with rationale, no critical failure, score at least 80, Factual Accuracy at least 4, and Root Cause/Recommendation/Trade-off/Context each at least 3. EV-07 uncertainty and EV-08-LR restraint are checked within Root Cause and Context, with explicit case-specific adjudication. Proposed campaign PASS: eight correct case IDs, eight distinct complete adjudications, zero critical failures, every case PASS and mean at least 85. PASS WITH LIMITATIONS is a human recommendation only for complete technically valid results with no critical failure when a noncritical proposed threshold is missed; it never means automatic adoption. Any critical failure or P1 rejection is FAIL; missing/unknown outcomes are INCOMPLETE, not a quality verdict.

## Critical failures and review

Automatically flag P1 rejection, nonexistent refs, changed numerical slots and wrong Brief digest via P1/identity checks. Human reviewers must identify unsupported causal certainty, invented contextual facts, permission-violating recommendations, material limitation omission, wrong Run/Scenario attribution and low-risk false escalation. A critical failure overrides weighted score. Two independent human reviews are recorded; an authorized adjudicator explicitly resolves disagreements and signs the final case scores/rationales. Model self-scoring is not evidence.

## Files, tests and gates

Create `AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md`, `cases.v2.json`, the quality module/tests, `P5_PAID_ACCEPTANCE_READINESS.md` and the final implementation report; append to the existing worksheet. Add an explicit synthetic-only runner group. Test all dimensions, bounds, missing/invalid scores, exact arithmetic, case/campaign gates, critical override, low-risk restraint, missing evidence, unsupported quantity, disagreement and deterministic aggregation. Run focused tests first, then explicit P1/eight-call/V1.1 regressions and the integrated synthetic-only suite. Inspect final diff and `git diff --check`.

## Risks and Owner decisions

The six weights and numerical thresholds require Owner approval. The v2 corpus needs Owner sign-off before paid use. Current `build_request` caps output at 2,500 tokens; the P5-C 25,000-token idea and exact reasoning/timeout settings remain unresolved. The adapter is deliberately blocked; the Ledger cannot provision paid mode. Exact model snapshot/alias policy, account entitlement, SDK compatibility, current prices, payload/retention consent and per-call/aggregate budget require future Owner decisions. These are concrete paid-readiness blockers; offline P5-D does not remove them.
