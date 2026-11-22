# Future controlled GPT-6 Luna acceptance procedure — NOT AUTHORIZED

This is a review plan, not executable permission or a dispatch implementation. The existing `OpenAIResponsesAdapter.execute()` remains blocked. No SDK, API key, budget, dated snapshot or paid request is selected in this preparation task.

## Preflight gates for any future paid call

1. Obtain separate Owner authorization for the exact paid scope and data transfer. Verify the **documented API model ID and dated snapshot**, account entitlement, Responses/strict Structured Outputs compatibility with the current P1 schema, provider retention terms, current pricing basis and selected SDK behavior. Do not infer these from the display name “GPT-6 Luna” or old documentation.
2. Owner chooses a maximum cost ceiling and approves the pricing basis. Measure/count the exact canonical request's input tokens with the verified snapshot method; estimate a conservative maximum from input and allowed output tokens. Check it fits the Owner ceiling. No implicit budget or production model default.
3. Use a live pinned synthetic Context and `ValidatedBrief`; record fixture version, scenario, max-record bound, explicit comparison selection, canonical Brief bytes/digest, minimized outbound projection/digest, instructions/schema/privacy versions, output cap, timeout, no-tool/no-store/no-retry settings and **exact Request Digest**. Compare byte-for-byte when evaluating the same case; a new harness may change the Brief digest, requiring new review and approval.
4. Owner authenticates separately from Demo and explicitly approves that exact Request Digest and ceiling. Verify expiry, revocation and digest binding immediately before the one allowance reservation. A stale or changed Brief/request invalidates the approval.
5. Provision and protect the local SQLite identity/ledger through the approved local procedure; verify the single stable database and current state. Do not recreate a missing/corrupt ledger. Atomically reserve the allowance and maximum cost with explicit estimate before any future submission.

## One-call observation sequence after separate authorization

1. Set ledger `IN_PROGRESS` only when an approved future dispatcher begins submission. Disable SDK/transport/proxy retries, streaming, background work, fallback and provider tools. No automatic repair call.
2. Capture monotonic start/end times and latency, provider request ID, token usage and observed charge when available; persist sanitized usage/charge and event evidence. Compare observed charge to the approved ceiling and escalate any over-ceiling observation; a request ceiling is not a provider-side billing guarantee.
3. Treat a completed non-refusal response as a candidate only after strict JSON parsing, P1 schema, Brief-digest, evidence-reference, exact numerical value/unit/grain and unsupported-prose checks. Human reviewers score the specific case with `EVALUATION_RUBRIC.md` and record the response's limitations. Never render an invalid response as a successful advisory.
4. Record refusal, incomplete output, definitive provider failure, timeout and ambiguous result distinctly. Timeout/process crash/interrupted submission or uncertain billing becomes `UNKNOWN` (or remains conservatively `IN_PROGRESS` until Owner manual reconciliation). Retain its allowance and cost reservation. **No automatic retry or resubmission.** Owner-authenticated manual reconciliation records evidence and does not reset the allowance.
5. Verify the local UI cannot execute recommendations or turn a Fake/invalid output into an accepted result. Confirm Cloud remains preview-only. Stop after the authorized call and report actual usage, latency, provider outcome, P1 result, human score and charge evidence without claiming a second call.

## Dataset and one-allowance mismatch

The current P3 campaign permits **one** paid allowance. The eight-case dataset is ready for offline contract/evidence checks, but a single future paid call can assess only one case of GPT-6 Luna behavior. It cannot establish the rubric's eight-case mean, low-risk over-escalation performance, latency distribution or robust refusal/timeout behavior. Do **not** run all eight cases under one approval or reset/reprovision the ledger to obtain more calls. A multi-case paid evaluation would need a separate Owner decision on call count, budget, authorization and ledger policy. Until then, a one-call outcome is a smoke test, not complete model adoption evidence.

If the chosen first candidate fails the authorized case or later approved corpus, document case ID, exact digest, validator status, discrepancies, rubric score and limitation. Ask the Owner whether to adjust the design, gather better evidence or authorize further evaluation. Do not automatically select a higher-tier model.
