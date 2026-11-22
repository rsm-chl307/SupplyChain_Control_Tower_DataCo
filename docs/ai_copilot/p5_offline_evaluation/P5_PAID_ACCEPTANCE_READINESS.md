# P5 paid acceptance readiness — GPT-6 Luna

Checked 2026-11-22 UTC against the current repository and **official OpenAI documentation only**. Consolidated recommendation: **NOT READY** for paid authorization. The P5-D offline quality framework is reviewable, but several paid execution controls are explicitly prohibited in this task and do not exist. This is a readiness assessment, not a request to perform the calls. GPT-6 Luna (`gpt-6-luna`) remains the sole candidate; no higher-tier search or model switch is proposed.

## 1. Evaluation readiness

| Requirement | Status | Evidence and decision |
|---|---|---|
| Eight independently named synthetic cases | READY WITH OWNER DECISION | `cases.v2.json` retains EV-01–07 from v1 and adds admitted EV-08-LR; live trusted Brief/reference test passes. Owner must approve v2 as the paid corpus; v1 remains unchanged. |
| Expected/forbidden findings and actual evidence refs | READY | `cases.v2.json`, quality matrix and `tests.test_p5_quality_corpus` resolve exact values/refs against trusted Briefs. |
| Six-dimension scoring and Critical Failure rules | READY WITH OWNER DECISION | `AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md` specifies proposed weights/1–5 anchors/thresholds and independent critical override. Owner must approve policy version. |
| Reviewer worksheet and aggregation | READY WITH OWNER DECISION | Eight-row register, two independent review forms and adjudication fields are prepared. `quality_evaluation.py` calculates exact Decimal scores and stable JSON; missing inputs return INCOMPLETE. Human reviewer identity is recorded, not cryptographically authenticated. |
| Actual GPT-6 Luna quality | NOT READY | No model response, latency, usage or charge exists. Offline synthetic tests cannot establish model quality. |

The historical `EVALUATION_RUBRIC.md` uses 0–4 and remains intact. The P5-D six-dimension 1–5 policy is a **new proposal**, not an approved replacement. No automatic PASS arises from a syntactically valid JSON response, incomplete reviewer form or seven of eight cases.

## 2. Model and API compatibility

| Requirement | Status | Verified documentation and repository evidence |
|---|---|---|
| Model ID and snapshot | READY WITH OWNER DECISION | Official [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) lists `gpt-6-luna`; its snapshot section lists that alias, with no dated snapshot verified there on 2026-11-22. Owner must choose explicit moving-alias policy if a dated snapshot remains unavailable. No production model configured. |
| Responses API / strict Structured Outputs | NOT READY | Model page lists `/v1/responses` and Structured Outputs support. The [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) requires all fields and `additionalProperties:false`, which P1 supplies. **Exact P1 wire schema compatibility is NOT VERIFIED:** it uses `minLength`/`maxLength`, absent from the guide's supported string-property list. Strict mode may reject unsupported schema. Do not alter P1 local validation; a separately reviewed wire-schema/adapter compatibility fix and live acceptance are required. |
| Context/output limits | NOT READY | [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna) lists 1,050,000 context and 128,000 max output tokens. Current `build_request` allows only **2,500** output tokens and a 60-second timeout; proposed 25,000 output tokens cannot be sent through it. The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) says reasoning and invisible formatting consume `max_output_tokens`, can produce `incomplete`, and are billable output. Actual Luna token/latency behavior is unverified. |
| Rate limits / entitlement | READY WITH OWNER DECISION | [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna) lists Free unsupported, Build 5,000 RPM/2M TPM, Launch 10,000/10M, Grow 30,000/180M. [Rate-limit guidance](https://developers.openai.com/api/docs/guides/rate-limits) says tier limits do not prove model access. Intended API organization/project entitlement and restrictions need a separately authorized check; ChatGPT subscription access is not API entitlement. |
| SDK and timeout behavior | NOT READY | Official [Python SDK guide](https://developers.openai.com/api/docs/libraries?language=python) shows `client.responses.create`; no exact minimum SDK version for this adapter was established. Local `importlib.util.find_spec('openai')` returned **False**; no SDK installed or client instantiated. The current adapter is deliberately blocked, and actual SDK error/timeout mapping is untested. |
| Refusal/incomplete/unknown | NOT READY | Repository `OpenAIResponsesAdapter.interpret` and P1 `classify_response` distinguish these offline using mock-shaped results. Official [reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning) describes `incomplete`; [error guidance](https://developers.openai.com/api/docs/guides/error-codes) describes timeout, 429 and server failures. Actual provider-side behavior remains NOT VERIFIED. No automatic retry is permitted by campaign policy. |

## 3. Cost and budget proposal — estimates, **not charges**

The official [Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) checked 2026-11-22 lists Standard text rates per million tokens: input **$0.10**, cached input **$0.01**, cache write **$0.125**, output **$0.50**. Regional processing may add 10%. The [pricing page](https://developers.openai.com/api/docs/pricing) has separate processing-mode tabs; use **Standard foreground**, not a discounted Batch/Flex/background figure. Actual cache use, taxes and account terms are not verified.

The local synthetic `build_request`/`call_arguments` inspection produced canonical request byte counts below. **Proxy input tokens are deliberately rounded planning estimates from request bytes**, not tokenizer or API counts. They include schema/instruction overhead approximately. The proposed output allowance is 25,000 **total generated** tokens per call, including reasoning and formatting; this exceeds current P2 policy. Stress estimates add uncached input **and** cache-write rates (`$0.225/M`) as a conservative planning allowance, even though actual billing may treat them differently. Formula: `proxy_input × 0.225/1,000,000 + 25,000 × 0.50/1,000,000`.

| Case | Canonical request bytes observed offline | Proxy input tokens | Proposed output + reasoning cap | Stress estimate | Suggested ceiling |
|---|---:|---:|---:|---:|---:|
| EV-01 | 18,497 | 5,000 | 25,000 | $0.013625 | $0.0200 |
| EV-02 | 18,723 | 5,000 | 25,000 | $0.013625 | $0.0200 |
| EV-03 | 18,817 | 5,000 | 25,000 | $0.013625 | $0.0200 |
| EV-04 | 18,737 | 5,000 | 25,000 | $0.013625 | $0.0200 |
| EV-05 | 31,106 | 8,000 | 25,000 | $0.014300 | $0.0200 |
| EV-06 | 31,106 | 8,000 | 25,000 | $0.014300 | $0.0200 |
| EV-07 | 18,497 | 5,000 | 25,000 | $0.013625 | $0.0200 |
| EV-08-LR | 26,815 | 7,000 | 25,000 | $0.014075 | $0.0200 |
| **Total** | — | **48,000 proxy** | **200,000 cap** | **$0.110800** | **$0.1600** |

Suggested campaign contingency is **$0.0492**, or 44.4% above this rough stress estimate. A 10% regional uplift on the estimate is **$0.12188**, still below the suggested $0.16 cap. These figures are **not approved**, configured or guaranteed. Before any paid call, verify exact token counts using an Owner-authorized method (the official [token-counting guide](https://developers.openai.com/api/docs/guides/token-counting) notes that local character estimates omit structural tokens; its API endpoint itself requires separate authorization), recheck current rates and the exact outgoing payload, and enforce an approved input ceiling (P5-C suggested 16,000), per-slot and aggregate reservations. Block on missing count/price/snapshot, estimate above ceiling, unsupported output cap, changed digest, unknown billing, expired approval, or any entitlement/retention uncertainty. No default budget or automatic top-up.

## 4. Privacy and data governance

`provider_brief` is an explicit allowlist. The provider-facing request contains model identifier, instructions/version, response schema/version, privacy version, output/timeout limits and safe transport flags, plus the **projected synthetic Brief**: `brief_version`, `brief_status`, `schema_version`, `definition_version`, `run_context`, `data_scope`, `data_quality`, `planning_summary`, `capacity_analysis`, `service_analysis`, `inventory_analysis`, `risk_analysis`, `root_cause_evidence`, `scenario_comparison`, `system_limitations` and minimized `source_manifest`. Each outbound source entry retains `source_ref_id`, field names, native grain, the **aliased** `Run_ID` and definition reference. The Brief/Request digests and projected Brief digest remain in the canonical request; synthetic values, scenario/comparison labels, aliases and source references remain visible.

The projection excludes local source paths, artifact hashes, row locators, upstream hashes, full source manifest metadata, raw CSVs, private Run ID and USER_DATA. The full provenance stays local. This is minimization, not anonymity. Because the trusted Run is generated just in time, **the exact serialized payload and Request Digest are not frozen or Owner-approved today**; a future Owner must inspect each exact payload and digest before each distinct slot approval. EV-01 and EV-07 may have identical outbound digests but still require distinct slot approvals.

Official [data controls](https://developers.openai.com/api/docs/guides/your-data) say API content is not used for training by default, while `/v1/responses` may have abuse-monitoring retention and application-state rules; `store=false` does **not** imply zero retention. Default abuse-monitoring retention is listed as 30 days, subject to account controls and exceptions. Owner must review account-specific retention, region, monitoring, caching and consent for the exact **synthetic** payload. No USER_DATA may be sent.

## 5. Eight-call Ledger and execution readiness

| Control | Status | Evidence / gap |
|---|---|---|
| Exactly eight distinct slots and JIT binding | READY for offline testing | `EightCallCampaign`, `CASE_IDS` and synthetic tests bind live V1.1 Brief, projection and request to an immutable case template. |
| Distinct Owner approval, atomic reservation, aggregate cap and local concurrency | READY for offline testing | Separate verifier, per-slot refs, `BEGIN IMMEDIATE`, unique keys and full-ceiling reservation tested across threads/processes. Identical digests cannot share an approval. |
| UNKNOWN, crash and reserved-but-undispatched | READY for offline testing | Reservation retained, no automatic retry or release; manual Owner reconciliation and fail-closed missing/replaced DB checks tested. |
| Sanitized audit/accounting | READY for offline testing | Append-only events and separate estimate/reservation/observed fields; actual charges remain unobserved. |
| **Live paid campaign and provider dispatch** | **NOT READY** | Ledger schema enforces `OFFLINE_TEST`, only `provision_offline` exists, `start_offline_attempt` records a test-double attempt, and `OpenAIResponsesAdapter.execute()` raises `ProviderBlocked`. No paid path or approved budget exists. It would be false to claim Owner can directly execute eight calls today. |

## 6. Owner decisions and concrete blockers

Owner review can approve or reject: (1) `cases.v2.json` as the eight-case corpus; (2) the new six weights, 1–5 anchors, 80/85 thresholds and Critical Failure policy; (3) alias versus dated snapshot policy; (4) exact reasoning/output/timeout/input policy; (5) account-specific data retention and minimized payload consent; (6) current pricing basis and actual per-call/aggregate ceilings, including contingency; (7) independent reviewer/adjudicator identities and local response archive retention. The proposed $0.02/$0.16 figures remain **unapproved**.

**Engineering blockers before paid authorization:** reviewed strict wire-schema compatibility with the existing P1 validator still enforcing its full local contract; a tested output/timeout policy that can accommodate complete JSON and reasoning; an installed and version-tested SDK or equivalent authorized transport; a separately authorized paid campaign provisioning/dispatch gate with the approved budget, exact slot approvals, crash/UNKNOWN handling and provider outcome/accounting tests. Current code intentionally lacks those capabilities. A single paid call to validate them is itself P5 Paid Acceptance and requires separate Owner authorization; no offline test can establish live account entitlement or actual billing. The Owner's preference to proceed without another implementation phase cannot be met safely while paid dispatch is prohibited here.

## 7. Exact future authorization sequence

1. Resolve the engineering blockers above in a separately authorized implementation and offline regression, without changing deterministic business logic or weakening P1 local validation.
2. Owner approves the versioned corpus and quality policy, exact model alias/snapshot and settings, retention/region terms, exact synthetic payload for each slot, current pricing basis and explicit per-call/aggregate dollar ceilings.
3. Verify API project entitlement and input-token counts only under a separately authorized account-access procedure. Freeze the manifest and provision the **paid** campaign explicitly; never repurpose the offline test database or P3 one-call allowance.
4. Owner separately authenticates and explicitly approves each live Brief/Request Digest and slot. Reserve cost/allowance atomically before one submission. No automatic retries; UNKNOWN holds reservation and requires Owner reconciliation.
5. Archive response/provenance and actual usage/charge; run P1 then independent human quality review. No model adoption from JSON validity alone.

**Final status: NOT READY for paid acceptance authorization.** P5-D offline quality preparation may be reviewed now. No API call, key access, SDK installation, paid allowance, charge, deployment or production model activation occurred in this task.
