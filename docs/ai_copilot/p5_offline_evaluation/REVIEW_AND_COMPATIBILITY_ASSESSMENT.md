# P5-A / P5-B — Offline package review and GPT-6 Luna compatibility

Checked: **2026-11-22 UTC**. Scope: documentation and source inspection, plus the explicit synthetic-only test group. This assessment does not replace the historical preparation records or approve a paid call. GPT-6 Luna remains the Owner's first candidate; no higher-tier model is proposed.

## Recommendation

**NOT READY for Paid Acceptance under the existing eight-case rubric.** The model catalog supports the basic endpoint and Structured Outputs in principle, but the current one-allowance ledger cannot produce eight separately scored model responses, a genuine low-risk case is absent, the exact schema/SDK behavior has not been exercised with Luna, and the 2,500-token output ceiling may be too small for reasoning plus the complete required JSON. These are readiness gaps, not demonstrated Luna failures. A separately authorized **one-call smoke test** could answer only narrower questions after its own gates are resolved; it cannot establish the eight-case mean or adoption quality.

## P5-A: package and evidence review

Reviewed `README.md`, `MODEL_COMPATIBILITY.md`, `SYNTHETIC_EVALUATION_CASES.md`, `cases.v1.json`, `EVALUATION_RUBRIC.md`, `PAID_ACCEPTANCE_TEST_PLAN.md`, `OWNER_DECISION.md`, the preparation report, `tests/test_p5_offline_evaluation_cases.py`, `tests/synthetic_only_suite.py`, and relevant V1.1/P1/P2/P3 source. Older preparation statements that Luna's API ID/pricing were unverified describe the **earlier offline-only evidence cutoff**; the official-document facts below are new findings, not silent edits to that history.

| Case | Coverage reviewed | Assessment |
|---|---|---|
| EV-01 | Baseline capacity utilization and bottleneck count | Direct synthetic evidence; bounded capacity interpretation expected. |
| EV-02 | Demand surge unmet workload and terminal backlog | Demand pressure covered; causal attribution remains deliberately unproven. |
| EV-03 | Capacity disruption and service fulfillment | Capacity/service relation covered; external cause remains unknown. |
| EV-04 | Combined stress terminal backlog and inventory | Inventory shortage signal covered at its published grain; no invented multi-plant claim. |
| EV-05 | Explicit Baseline→Demand_Surge horizon service comparison | Comparable direction and cohort distinction covered; Legacy denominator conflation forbidden. |
| EV-06 | Planning priorities and selected-cohort service comparison | Trade-off prompts covered; no model authority to alter allocation. |
| EV-07 | At Risk with zero lost sales; unselected root-cause detail | Conflicting signals and missing evidence covered, but not a fully evidence-free Brief. |
| EV-08 | Zero lost-sales signal within an At Risk Brief | Tests restraint on one signal; **does not test a genuinely Low-risk scenario**. |

The case test obtains live, validator-issued V1.1 Briefs from the pinned synthetic harness. It checks repeated canonical Brief bytes/digest within one harness, resolves each listed source ref and exact expected value, verifies one numerical slot per case through the real P1 validator, and rejects an altered value. These are direct **fixture/evidence contract** tests. The tests assert that expected-finding and forbidden-conclusion strings exist; they do **not** score real model interpretations, semantic root-cause quality, recommendation quality, or actual Luna numerical behavior. No hand-authored JSON case is a trusted Brief token. Across new harnesses, temporary Run identity/timestamps may alter the full digest; use the exact live Brief/request pair for any future comparison.

The rubric has explicit 0–4 anchors, weighted dimensions, hard structural gates, per-case minimum 80/100, eight-case mean 85/100, and two human reviewers. Evidence, numerical fidelity and output compliance jointly hold 60/100. This is a reasonable **proposed** evaluation policy, not an approved business threshold. Subjective dimensions such as “reasonable root cause,” “actionable,” and “complete without filler” still need a reviewer worksheet with case-specific examples and adjudication rules before paid scoring. The eight-case mean is impossible to determine from one response: **eight distinct calls** are the minimum for one response per case; repeated samples or latency/timeout characterization would require more. Current P3 one-allowance policy must not be reset or bypassed.

### P5-A findings

| ID | Severity | Evidence and impact | Required action |
|---|---|---|---|
| AB-01 | MEDIUM | EV-08 is a zero lost-sales signal in an otherwise At Risk Brief; false escalation on a fully Low-risk scenario remains untested. | Owner decides whether to authorize a new trusted pinned synthetic fixture or accept this explicit coverage limit. Do not alter existing hashes/cases silently. |
| AB-02 | HIGH | `EVALUATION_RUBRIC.md` requires eight-case mean; `PAID_ACCEPTANCE_TEST_PLAN.md` and `src/ai_copilot/ledger.py` allow one paid reservation. One call cannot meet the stated adoption gate. | Owner chooses a separately authorized multi-case campaign and ledger policy, or formally narrows a one-call objective to a smoke test without claiming adoption. |
| AB-03 | MEDIUM | Only one slot per case is mutation-tested; expected interpretation strings and unsupported conclusions are not executable model-quality assertions. | Prepare a human scoring sheet and adversarial response probes before paid evaluation; retain current tests and criteria. |
| AB-04 | LOW | Case values include exact binary-float renderings such as `7.300000000000001`; equality is intentional for the canonical Brief but can be awkward to read. | Keep exact contract values; show human-readable displays separately only after an approved presentation rule. |

## P5-B: official OpenAI documentation facts

All external evidence below was checked **2026-11-22 UTC** on official OpenAI documentation. A documented model capability is not proof of this account's entitlement or of the exact request succeeding.

| Question | Verified fact or unresolved state | Official source |
|---|---|---|
| API model ID | **VERIFIED:** `gpt-6-luna` is the OpenAI API model ID. This is an alias, not a chosen production snapshot. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| Dated snapshots | **NOT VERIFIED:** the model page's “Snapshots” section lists `gpt-6-luna` only; no dated Luna ID was established in the reviewed official pages. Do not invent one or treat the alias as dated/pinned. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| Responses API | **VERIFIED as documented:** the model page lists `v1/responses`. Actual account/project access is **NOT VERIFIED**. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| Structured Outputs | **VERIFIED as documented:** Luna's feature list says Supported. Strict mode requires all object fields `required`, `additionalProperties:false`, and the supported JSON Schema subset; unsupported strict schemas fail the API request. Exact acceptance of the project's schema is **NOT VERIFIED** without a live request. | [Model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) |
| Schema limits | The guide describes up to 5,000 object properties, 10 nesting levels, 120,000 characters in names/enum/const strings, 1,000 enum values, and excludes certain composition keywords. String/array restrictions have model-specific caveats. | [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) |
| Context and output | **VERIFIED as documented for the listed alias:** 1,050,000-token context and 128,000 max output tokens. Snapshot-specific limits remain **NOT VERIFIED**. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| Reasoning/output budget | `max_output_tokens` includes hidden reasoning and formatting tokens. Reaching it yields `incomplete`, potentially before visible JSON. The generic reasoning guide recommends initially reserving at least 25,000 tokens for reasoning plus output; that is guidance, **not a Luna-specific minimum**. | [Reasoning models guide](https://developers.openai.com/api/docs/guides/reasoning) |
| Standard text price | **VERIFIED published rates per 1M tokens:** input **$0.10**, cached input **$0.01**, output **$0.50**; cache write **$0.125** is also listed. >272K input tokens trigger a higher rate for the whole request; regional/Fast/Batch/Flex terms differ. These are published rates, not an observed charge or approved budget. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [pricing](https://developers.openai.com/api/docs/pricing) |
| Entitlement | **NOT VERIFIED for this Owner's organization/project/key.** Model listing and usage tier do not guarantee access. ChatGPT subscriptions do not by themselves establish API access; eligible subscription credits require a linked API organization and separate activation. No credentials were queried. | [Rate limits and model availability](https://developers.openai.com/api/docs/guides/rate-limits), [ChatGPT subscriber API credits](https://developers.openai.com/api/docs/guides/chatgpt-api-credits) |
| Retention/storage | API content is not used for training by default absent opt-in. Default abuse monitoring logs may contain content and are retained up to 30 days, with stated exceptions. `store=false` avoids ordinary saved Responses objects but **does not guarantee zero retention**; account-level data controls, temporary processing/caching and exceptions require separate review. | [Data controls](https://developers.openai.com/api/docs/guides/your-data), [conversation state](https://developers.openai.com/api/docs/guides/conversation-state) |
| Rate limits | Model page lists Free unsupported; Build **5,000 RPM / 2M TPM**, Launch **10,000 / 10M**, Grow **30,000 / 180M** (plus batch queue limits). Actual org/project limits and model availability are **NOT VERIFIED**. | [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [rate limits](https://developers.openai.com/api/docs/guides/rate-limits) |

## Compatibility matrix against current implementation

“COMPATIBLE” here means source structure aligns with documented capability; it does not mean a real Luna response was obtained.

| Requirement | Classification | Evidence and limit |
|---|---|---|
| Provider interface/DTO | **COMPATIBLE WITH LIMITATIONS** | `DecisionProvider.execute(ProviderRequest)` and `ProviderResult` can represent results, refusals and usage in `src/ai_copilot/provider.py`; actual SDK object/error mapping remains untested. |
| API model identifier and snapshot | **NOT VERIFIED** | Official alias is `gpt-6-luna`, but no dated snapshot is established. The current builder requires an explicit string and the preparation policy requires a reviewed snapshot. No production value is chosen. |
| Responses endpoint | **COMPATIBLE WITH LIMITATIONS** | Official Luna endpoint includes `v1/responses`; `call_arguments()` constructs Responses-style arguments. Adapter `execute()` intentionally raises `ProviderBlocked`; account and SDK runtime behavior untested. |
| Request Digest/privacy projection | **COMPATIBLE** for local construction | `build_request()` binds the full local Brief digest, allowlisted provider projection digest, instructions, schema/privacy versions, model string and limits. `call_arguments()` rechecks provenance. No live transport validation. |
| Strict response schema | **NOT VERIFIED** for Luna | Local schema has 16 closed objects, 64 total properties, depth 5, 14 enum values and 950 name/enum characters; these fit documented size/depth ceilings. It uses `pattern`, `minLength`, `maxLength`, `maxItems`. Only an exact live strict-schema request can confirm provider acceptance of every keyword/version combination. No schema weakening is authorized here. |
| P1 response validator | **COMPATIBLE** as local postcondition | Closed local JSON validation, Brief digest/ref/value/unit/grain checks and unsupported quantitative prose review remain independent of model. They do not establish semantic truth or live Luna quality. |
| Input/output and timeout bounds | **COMPATIBLE WITH LIMITATIONS** | Model's listed 128K output ceiling exceeds local 2,500 cap, but the local cap includes reasoning tokens and may cause `incomplete`; 64 KiB bytes is not a token count. Local >0–60s timeout also lacks Luna latency evidence. Set nothing now. |
| P3 Owner Approval/ledger | **COMPATIBLE WITH LIMITATIONS** | Exact digest approval, explicit model/cost policy, one allowance and UNKNOWN retention exist. Published rate is not an Owner-approved ceiling; one allowance cannot execute the eight-case rubric. |
| Account access/retention/cost realization | **NOT VERIFIED** | No org/project entitlement check, SDK, actual tokenization, provider result, retention configuration or charge observation was performed. |

No demonstrated model incompatibility is claimed. The current production execution path is deliberately blocked.

## Required actions before any Paid Acceptance

1. Owner decides whether the next authorized objective is a **single-call smoke test** or a separately designed **eight-or-more-call quality evaluation**. Preserve the existing rubric until a deliberate reviewed decision; do not silently count one response as eight.
2. Resolve genuine Low-risk coverage through a separately reviewed trusted synthetic fixture, or explicitly accept that the model adoption conclusion cannot cover that condition.
3. Review and approve the rubric before model outputs are seen. Record case-level scoring examples, reviewer disagreements, and the treatment of `N/A`; do not change thresholds after seeing unfavorable responses.
4. Establish a supported immutable Luna snapshot if one becomes officially available; otherwise explicitly decide whether the documented moving alias is acceptable for a narrowly bounded test. No production snapshot is selected here.
5. Independently verify the exact P1 schema/SDK/Responses argument mapping and select an output-token/reasoning/timeout policy that can produce the required JSON within an approved cost ceiling. Any adapter or P3 security-contract change needs its own authorization.
6. Owner verifies API organization/project entitlement, rate limits, current pricing and data controls; approves only the exact minimized synthetic transfer, canonical Request Digest, estimated maximum and separate paid-call authorization. Never infer zero retention from `store=false`.
7. Keep P5 paid execution and P6 deployment disabled until their separate authorization gates. If Luna fails, record case-specific deficiencies and return to Owner review; do not auto-switch models.

## Verification and boundaries

The explicit command `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_offline` is the only P5 test selection used here; it includes the versioned case test plus P1/P2/V1.1 modules and rejects USER_DATA-like paths and network sockets. Exact result is recorded in the accompanying P5-AB report. `git diff --check` was run. No source, existing case, fixture, hash, rubric threshold or adapter was modified. Official documentation browsing was read-only; no OpenAI API request, credential lookup, model execution, charge, USER_DATA access, commit, push or deployment occurred.
