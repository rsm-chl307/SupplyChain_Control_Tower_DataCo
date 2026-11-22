# AI Decision Copilot V1.2 — Provider and Experience Design Specification

Status: **DESIGN ONLY — owner review required before implementation**. Prepared 2026-11-20 UTC. No provider call, network request, key, dependency installation, UI change, deployment, or paid execution occurred for this design.

## 1. Purpose and verified baseline

Option E keeps the existing deterministic Planning, KPI, risk and comparison code as the only authority for business facts. V1.2 would interpret a **validated, immutable V1.1 Brief** and return advisory, evidence-linked text. It cannot run Planning, modify a Run, invent a scenario, calculate a new KPI or execute a recommendation.

The original repository is on `main` at `6e451b9660dd3be09e632e10ff8698b39a267b07`, with pre-existing UI, report and Python cache changes and an empty index. V1.1 closure is `PASS WITH LIMITATIONS`: final selected suite 134 passed, 0 failed/errors/skipped. `src/ai_brief/workflow.py::prepare_brief` returns `BriefOutcome(status, message, review, markdown)`; `review` is a local `ValidatedBrief` containing canonical JSON bytes and SHA-256 `content_digest`. `ValidatedBrief.verify()` checks issuer registry, digest and live Context evidence. `contract.py` uses strict JSON Schema, `brief_version=1.0`, definition/privacy versions, a 32 KiB JSON ceiling and source references. `preview.py` displays the exact validated JSON and disclosure of bounded records. There is no provider interface, response schema, paid authorization, Cloud session trust, authentication or UI entry point in V1.1. The local synthetic harness is a fixed-fixture trusted-process mechanism, not a Cloud authorization service.

Actual development UI in `dashboard/scenario_planning_app.py` has a global locale selector and Guide button near the top-right, a Planning form with preserved pending widget state, selected sequential Run paths in session state, risk/investigation and comparison views, and public Planning execution. The development UI's path selection is not an authorization credential. The deployment entrypoint has additional upload limits, session output containment and path checks (feasibility report §§10–11); no deployment file is changed here. A future hosted design must be reviewed against that deployment implementation rather than copying the development entrypoint.

## 2. Proposed trust and data flow

```text
Approved synthetic session Run → current-session authorization → V1.1 verified Context/Brief
→ owner review of exact outbound request and digest → durable authorization/cost gate
→ provider-neutral request DTO → OpenAI Responses adapter (one synchronous request)
→ strict response and evidence validator → safe, evidence-linked renderer
```

The full outbound request includes fixed instructions, model/snapshot, schema version, canonical Brief bytes, token/output limits and privacy version. Approval binds a digest over **all** of those bytes and settings, not only `brief_digest`. Immediately before submission, reverify the Brief and current-session source; any change invalidates approval. The provider receives only that minimized Brief, not a path, raw CSV, full manifest, source filenames, credentials, tools, previous conversation or mutable Python object. The Brief's `VALIDATED` status is a prerequisite, not authorization to spend.

**Gap:** the current V1.1 issuer is limited to a local trusted interpreter and pinned fixtures. It cannot by itself authorize a Streamlit Cloud user/session or survive restart. Hosted Brief construction, including preview, must remain locked until a separately approved Cloud gate and session-bound Run authorization exist. V1.2 can develop provider/response logic offline against local fixtures without claiming hosted readiness.

## 3. Provider architecture and decision record

| Choice | Security | Complexity / cost | Maintenance | Recommendation |
|---|---|---|---|---|
| Call OpenAI directly from the page | Streamlit rerun and widget state can duplicate calls; hard to audit | Initially small, paid-call risk high | Provider details spread through UI | Reject |
| Small `DecisionProvider` interface plus one OpenAI adapter | Separates side effects and permits a single gated call site | Modest extra types; mockable without charge | Provider replacement localized | **Use** |
| Generic agent/tool framework | Broadens filesystem/network/action surface | High tokens, dependency and test cost | More moving parts | Exclude from V1.2 |

Proposed immutable DTOs: `ProviderRequest(request_digest, brief_digest, model_snapshot, response_schema_version, instructions_version, canonical_brief, max_output_tokens, timeout_seconds, client_request_id)` and `ProviderResult(outcome, raw_response_bytes_or_none, provider_request_id, usage, refusal_reason, incomplete_reason, sanitized_error)`. The provider interface has one `execute(request)` method and **no** runner, file, cache, search or tool hooks. It does not decide permission or retry. The orchestration gate is the only caller of `execute`; a test fake implements the same interface. Provider-neutral errors distinguish `REFUSED`, `INCOMPLETE`, `DEFINITIVE_ERROR`, `UNKNOWN_OUTCOME` and `SUCCEEDED`. Unknown transport outcomes consume the initial allowance.

The initial adapter is planned for OpenAI Responses API with Structured Outputs strict JSON. The exact SDK method, supported schema subset, refusal/incomplete response fields, timeout and model snapshot must be verified against current **official OpenAI documentation** immediately before implementation; this design makes no live API claim. The prior feasibility report §8 cites official [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [SDK reference](https://developers.openai.com/api/reference/python), [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini), [spend limits](https://developers.openai.com/api/docs/guides/spend-limits), and [data controls](https://developers.openai.com/api/docs/guides/your-data). These links are inherited planning evidence; no current page or pricing was rechecked because network access is prohibited in this task. Configure one approved snapshot in a server-side allowlist, version the prompt/schema/adapter, disable SDK/transport/proxy retries, streaming, background mode and fallback. Never silently switch models. Refusal or incomplete content is not schema-valid advice, and never triggers repair calls.

Provider replacement is allowed only behind the same request/response DTOs, strict validator, authorization and privacy tests. A second provider is not implemented in initial V1.2. Owner decisions: exact model snapshot/account entitlement, response schema compatibility, processing terms and cost envelope.

## 4. Versioned AI response contract

Use strict closed JSON Schema (`additionalProperties:false` at every level), `response_version="1.0"`, bounded strings/arrays, no NaN/Infinity, no HTML/URLs/code/tools. Top-level keys, all required: `response_version`, `brief_digest`, `executive_assessment`, `key_findings`, `root_cause_interpretation`, `recommendations`, `decision_trade_offs`, `further_investigation`, `limitations_and_confidence`. Schema validity is necessary but **not** evidence validity. A refusal/incomplete provider event is represented outside this business-response object.

| Section | Closed content and limit |
|---|---|
| `executive_assessment` | `summary`, `principal_concern`, `evidence_refs`; concise, no unsupported quantitative claim |
| `key_findings` | 0–5: `finding_id`, `description`, `evidence_refs`, `numerical_evidence`, `potential_operational_impact`, `severity` High/Medium/Low, `severity_rationale` |
| `root_cause_interpretation` | Separate `observed_facts`, `system_identified_drivers`, `ai_interpretations`, `unverified_hypotheses`, `missing_evidence`; each item has text, evidence refs and support class; hypotheses explicitly unverified |
| `recommendations` | 0–3: `recommendation_id`, `priority`, `proposed_action`, `rationale`, qualitative `expected_impact`, `trade_offs`, `required_validation`, `evidence_refs`; advisory only |
| `decision_trade_offs` | 0–5 bounded statements, affected measures/groups, evidence refs and existing comparability status; empty/unsupported without valid comparison |
| `further_investigation` | Bounded unanswered questions, reason and needed evidence; no invented organizational owner |
| `limitations_and_confidence` | `data_completeness`, `evidence_quality`, `directly_supported_conclusions`, `inferences`, `unsupported_questions`, qualitative `confidence` Limited/Moderate/Strong and `confidence_rationale`; no numeric confidence score |

Each structured numerical evidence slot is `{source_ref_id, field_name, value, unit, scope_or_grain}`. Its reference must resolve through the approved Brief `source_manifest` and `resolve_source`, match the exact displayed numeric value and source unit, and belong to the selected Run/scenario/comparison. Do not let the model supply arbitrary record keys or path selectors. The validator rejects invented refs, unavailable/empty source sections, wrong units/grain/cohort basis, altered KPI values, >3 recommendations, causal certainty without evidence and quantified future outcomes from unrun scenarios. Render numbers from validated slots, not free text. Prose containing an unreferenced quantitative claim or unsupported promised improvement is rejected or marked for human review; schema alone cannot prove truth. Severity is AI advisory priority and must be visually distinct from deterministic `Risk_Category`; it cannot overwrite that category. Missing evidence yields fewer or zero findings/recommendations, never fabricated filler.

`Demand_Fulfillment_Rate` keeps its existing denominator/cohort meaning and is not `Production_Coverage_Rate`; `Capacity_Utilization` is copied, shared capacity remains Plant × Week, terminal stocks are not summed flows, and `null` with `UNDEFINED_DENOMINATOR` remains undefined. Response validators must enforce these semantics using source-backed Brief fields and approved definition version. The renderer must show direct facts, deterministic findings, inference and hypothesis in different labeled groups. Validate bilingual display labels separately from machine values.

## 5. Authorization, privacy and cost design

**Offline preparation:** authenticate before any hosted Brief construction; authorize only the current session's published synthetic Run; validate lifecycle/artifact hashes; build the V1.1 Brief; show exact JSON/Markdown, field disclosure, source references, truncation, unavailable sections, model and expected maximum cost. No API key is needed for offline tests. Owner approval uses a short-lived server-side nonce bound to request digest, Brief digest, Run/scenario/comparison, schema/prompt/model/privacy versions and caps. Change or logout voids it. A shared Demo password is an access gate, not proof of owner identity or permission to spend. The owner must choose a separate owner-controlled approval mechanism.

**Initial paid acceptance:** globally authorize exactly **one** planned invocation only after offline and browser gates pass. Transactionally reserve the sole acceptance allowance and worst-case cost **before** sending. Ledger states: `NOT_STARTED`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, `UNKNOWN`; record distinct provider/refusal/incomplete and response-validation outcomes, timestamps, digests, model/version, reservation, usage/estimated charge, provider IDs and sanitized errors. Concurrency needs a unique campaign key and transactional compare-and-swap or insert. A rerun or duplicate click reads the ledger; it never sends. `UNKNOWN` after timeout/crash retains reservation and blocks resubmission pending owner reconciliation. A response rejected locally may still cost money. No automatic retries, prompt experiments, connectivity calls or provider test calls. A second paid call requires a new owner decision. Local IDs or client request IDs do not guarantee provider-side exactly-once billing.

**Durability decision:** Streamlit Cloud session state, local JSON/SQLite and process locks are not durable global enforcement across restarts or instances. Options: (A) owner-operated local one-call acceptance with a persistent local ledger and Cloud preview-only, lowest new infrastructure but no hosted paid feature; (B) owner-approved durable coordinator/store with atomic transactions for hosted paid calls, additional infrastructure/operations/cost. Recommend **A for first acceptance** until the owner explicitly approves B. Missing/corrupt ledger or budget configuration must fail closed. Do not create a store in this design phase.

**Proposed ceilings, not authorization:** retain V1.1 Brief ≤32 KiB, full request ≤64 KiB, conservative local input-token cap ≤8,000, `max_output_tokens` ≤2,500, 60-second total deadline, concurrency one and no retry/fallback. If the actual prompt/schema/model token count cannot be bounded offline, block. Recheck model availability, current pricing, possible reasoning-token charging and account budget before requesting approval. The feasibility report's provisional $0.03 reservation is only a planning placeholder; owner must set a hard per-request and campaign envelope. Provider spend alerts alone are not atomic hard caps. Do not assume ChatGPT subscription credits fund API usage.

**Privacy:** synthetic-only first; pinned fixture origin must be verified, not inferred from `SYNTHETIC_DEMO` text. Send alias IDs and bounded approved fields, no raw CSV/source rows, product names, personal/customer data, filenames/paths, full manifest, source-hash keys, mappings, credentials, access logs or unrelated session data. Keep no multi-turn history. Treat Brief text as untrusted instruction-bearing data. Do not log full outbound/inbound bodies; log only digests, versions, state, usage and sanitized error/request IDs. `store=false` is proposed but does **not** mean zero retention; owner must review provider data controls and approve transfer terms. Synthetic-to-USER_DATA expansion requires separate privacy/business approval.

## 6. Copilot user experience (design only)

**Placement:** a dedicated “Decision Copilot / 決策輔助” view adjacent to existing Planning results, available only after the future Copilot access gate. Public Dashboard and Planning remain accessible. The global `ui_locale` controls both languages; no second language selector. The gate wraps Brief build, preview, download and submission, not just the button. No Copilot construction on page load, normal Planning submit or Streamlit rerun.

**Journey:** (1) unlock Copilot; (2) select an eligible current-session synthetic published Run/scenario and optionally an already-valid investigation/comparison; (3) press “Prepare Brief”; (4) view validation status, digest, explicit missing/truncated evidence, exact payload and cost envelope; (5) owner review/approve separately; (6) press one guarded “Request analysis” action; (7) see loading state or terminal success/refusal/incomplete/error/unknown; (8) inspect evidence-linked findings and limitations; (9) lock/logout. A new selection or modified Brief clears approval and requires review again. No valid Run shows an unavailable message with next step; invalid evidence shows blocked, with no provider button.

```text
Desktop:  [Public navigation] [Global language] [Copilot lock/logout]
          ┌─ Current Run + status ─────────────────────────────────────┐
          │ Scenario | optional evidence | Prepare Brief              │
          ├─ Brief review ────────────────────┬─ Source/detail panel ──┤
          │ VALIDATED / BLOCKED / UNAVAILABLE  │ source ref + grain     │
          │ digest, limits, exact payload      │ matched field/value    │
          ├─ Cost/approval ────────────────────┴───────────────────────┤
          │ model, caps, disclosure, explicit owner approval           │
          ├─ AI result (only validated response) ──────────────────────┤
          │ assessment | facts | system drivers | interpretations      │
          │ findings + evidence | ≤3 actions | trade-offs | limits      │
          └─────────────────────────────────────────────────────────────┘
Mobile: stacked panels in the same order; no hover-only evidence access.
```

Terminology: “AI Analysis Brief / AI 分析摘要”, “Prepare Brief / 準備摘要”, “Evidence / 依據資料”, “Observed fact / 已觀察事實”, “System finding / 系統判定”, “AI interpretation / AI 解讀”, “Unverified hypothesis / 待驗證假設”, “Recommendation / 建議措施”, “Trade-off / 取捨”, “Confidence / 判斷信心”, “Request analysis / 送出分析請求”, “Unknown outcome / 執行結果待確認”. Technical statuses remain machine values in stored records; localized labels explain them. Never label AI severity as deterministic risk status.

Use semantic headings, labeled buttons, keyboard focus order, visible status text and an `aria-live`-compatible status area if Streamlit supports it, sufficient contrast and readable tables. Buttons have descriptive disabled reasons; confirmation is not color-only. Preserve existing Planning form buffer when opening/closing the Copilot view. Responsive acceptance requires actual browser tests at desktop and narrow widths, keyboard navigation, both locales and screen-reader spot checks; AppTest alone is insufficient. Malformed responses remain hidden behind a clear validation error and sanitized diagnostic ID; never render raw provider HTML/Markdown or silently repair with another paid request.

## 7. Implementation roadmap and acceptance gates

| Package | Objective / expected files | Dependencies and security gate | Offline acceptance | Paid authorization? |
|---|---|---|---|---|
| D0 owner decisions | Freeze model, processing/privacy scope, qualitative severity rubric, password-widget interpretation, paid approval identity, ledger option and budget; update this design | No code until unresolved security decisions close | Reviewed decision record | No |
| P1 response contract | Add `src/ai_copilot/response_contract.py`, `response_validation.py`, local fixtures/tests | V1.1 exact Brief references and definitions; closed strict JSON; no provider | Valid response accepted; invented numbers/refs, >3 actions, causality, null/cohort errors rejected | No |
| P2 prompt/provider seam | Add provider-neutral DTO, fixed prompt builder, fake provider, OpenAI adapter module isolated from UI | Official docs recheck, pinned supported model/SDK, no tools/history, retry disabled, fail closed | Network denied; fake call count zero except explicit gated mock; refusal/incomplete/timeout tests | No real call |
| P3 authorization and ledger | Add owner-approved `execution_gate.py`, `ledger.py`, transactional store tests | Durable choice approved; digest binding, one global campaign allowance, atomic reservation, default-off | Concurrent process/duplicate/rerun/crash/UNKNOWN/budget and missing-ledger tests | No real call |
| P4 protected local experience | Add reviewed Copilot view components and bilingual strings; reuse global locale | Agreed auth boundary before Brief access; preserve Planning form and local fixture trust | UI/AppTest plus real browser, accessibility and form-state acceptance, mocked provider only | No real call |
| P5 one-call acceptance | Execute single synthetic approved request after all gates | Explicit owner authorization of exact body, model, cap and data transfer; ledger ready | Prior offline gates already passed; record actual response/usage/outcome | **Yes: exactly one separately authorized invocation** |
| P6 deployment port (separate authorization) | Review deployment entrypoint/security tests, minimal allowlist/manifest update | Cloud session Run auth, durable gate or preview-only decision, secrets and existing security baseline | Six deployment safety tests plus current-session containment, bilingual/browser, privacy and protected artifact hashes | No automatic paid call |

Packages can be split smaller, but P3 security must precede any hosted paid path. P1/P2 can proceed offline using mocks once owner approves implementation. No package may treat V1.1's local Context as a Cloud login token. Provider/API and hosted UI work are not authorized by this design task.

## 8. Unresolved owner decisions and release criteria

1. Choose the first model snapshot, account/project billing controls, maximum total spend, request reservation and acceptable provider retention; verify current official docs at implementation time.
2. Approve a qualitative severity/priority rubric and exact evidence threshold for any causal wording or expected impact.
3. Decide whether paid acceptance is strictly local with Cloud preview-only, or fund/approve a durable Cloud coordinator; do not claim global one-call enforcement from session state.
4. Decide how owner approval is authenticated separately from a shared Demo password; clarify whether transient native password-widget state is acceptable. A literal ban on transient framework state rules out the native widget.
5. Approve synthetic payload disclosure and any later expansion to actual operational data/identifiers.
6. Confirm the exact response JSON Schema against the selected model's current Structured Outputs subset and choose the failure policy for semantically ambiguous prose (recommended: block and human review, no retry).

Release gates: source/session authorization, authentication, durable execution control or preview-only mode, offline zero-egress security tests, protected deployment regression, browser accessibility, owner approval of exact outbound request, and separate one-call authorization. No paid request or Cloud exposure occurs merely because this specification exists.

## 9. Inspection and change record

Inspected: both AI Copilot reports; `src/ai_brief/{workflow,validation,preview,contract,adapter,builder}.py`; `src/synthetic_context.py`; `dashboard/scenario_planning_app.py` and existing i18n/navigation references; previous 134-test result record. The feasibility report provides the detailed artifact inventory and field mapping. No source file was edited. This document is new; the V1.1 report received an append-only formal closure section. Existing UI, Planning/KPI code, Runs, Published Artifacts, evidence, datasets and deployment files were not changed. No API call, network request, spending, commit, push or deployment occurred.

## 10. D0 owner decisions — authoritative addendum (2026-11-20)

This append-only addendum supersedes only the corresponding undecided recommendations above; historical design reasoning remains intact. **P1–P4 are authorized for offline implementation in sequence. P5 paid acceptance and P6 deployment port are NOT AUTHORIZED.**

| ID | Final owner decision | Implementation consequence |
|---|---|---|
| D0-01 | Model selection **UNDECIDED** | No production model default or implicit selection. Explicit Model Snapshot and its settings belong to request provenance. Official model/SDK/schema/pricing/retention verification is required before future provider acceptance. |
| D0-02 | **LOCAL OWNER-OPERATED ACCEPTANCE** | Future one-call acceptance is local only. Cloud remains preview-only and may never initiate paid execution. Local durable transactional reservation must precede any future send; UNKNOWN consumes allowance. No retry, fallback or background call. |
| D0-03 | **QUALITATIVE** severity | High/Medium/Low describe advisory AI severity without numeric thresholds; never conflate it with deterministic `Risk_Category`. Separate facts, system findings, interpretations and hypotheses. |
| D0-04 | **SEPARATE OWNER APPROVAL** | Demo password is not owner identity. Local approval binds the exact canonical outbound request digest; changes to Brief, instructions, model snapshot, schema, privacy version or limits void approval. Offline implementation does not authorize execution. |

Revised roadmap status: D0 finalized; P1 response contract, P2 provider seam, P3 local approval/ledger and P4 protected local experience authorized **offline only**, subject to each preceding stage passing. P5 and P6 remain outside scope. No production model, cost ceiling or provider transfer consent has been supplied. A missing configuration must fail closed. The local owner identity method and official current API details require verification before any real execution; this addendum grants no payment or Cloud access authority.

## 11. Offline implementation status after D0

D0 was recorded before implementation. P1 response contract is implemented and passed its focused and selected V1.1 regression tests; details are in `AI_COPILOT_V1_2_IMPLEMENTATION_REPORT.md`. P2 is **BLOCKED before adapter implementation** because its mandatory gate requires checking current official OpenAI Responses API and SDK documentation, while this task explicitly prohibits network requests and no current official local reference was found. Historical links in the feasibility report are not proof of current SDK methods or Structured Outputs capabilities. Under the required sequential stop rule, P3 and P4 have not started. This is not a request for credentials or permission to make a paid API call. P5 and P6 remain NOT AUTHORIZED.

## 12. P2 documentation-gate resolution

The owner authorized read-only official OpenAI documentation access on 2026-11-20. The official Python SDK Responses, Structured Outputs, retry/timeout and API parameter references were verified and are recorded with links and implications in `AI_COPILOT_V1_2_IMPLEMENTATION_REPORT.md`. The P2 offline provider seam passed its focused and selected regression tests. The prior blocked status in Section 11 is historical. **Current status: D0 finalized; P1 PASS; P2 PASS WITH LIMITATIONS; P3/P4 not started; P5/P6 not authorized.** No production model or SDK version was selected, installed or exercised. The adapter remains unable to send a real request.

## 13. P3 local approval and ledger implementation addendum

P3 uses a separate local Owner password verifier supplied through `COPILOT_OWNER_SALT_HEX` and `COPILOT_OWNER_SCRYPT_HEX`. The password itself is never stored by the application. The Demo password is neither consulted nor accepted as Owner identity. The owner must provision a private local environment and protect the verifier, SQLite database, and host account. Scrypt provides password verification, not remote identity proof or defense against a compromised local process. There is no network authentication, rate limiting, hardware key, or multi-user authorization service.

An explicit `LocalExecutionGate.approve()` call first revalidates the live V1.1 Brief and reconstructs the canonical request. The persisted approval stores a random reference, exact request digest, policy version, issue/expiry/revocation/consumption times, and the explicitly approved cost ceiling and pricing basis when supplied. Session state is not authority. An approval without cost configuration may support offline review but cannot reserve paid allowance. Changing the Brief, instruction, schema, privacy version, model snapshot or limits changes the digest and invalidates the old approval.

The local SQLite ledger has a fixed one-allowance campaign key. `BEGIN IMMEDIATE` serializes competing processes; one transaction inserts a `NOT_STARTED` reservation and consumes the matching, live approval. A reservation retains its allowance and maximum cost after all terminal outcomes. `IN_PROGRESS` represents a future dispatch starting; `UNKNOWN` retains the reservation and has no automatic reset or retry. A crash after committed reservation but before dispatch leaves a reserved `NOT_STARTED` entry; recovery must not silently submit. This is a local single-database guarantee only. The DB path and its backup/host integrity remain owner responsibilities; Cloud multi-instance durability is not claimed. P3 creates no provider dispatch method, and `OpenAIResponsesAdapter.execute()` continues to raise `ProviderBlocked`.

## 14. P4 implementation checkpoint and stopped gate

P4 development began after the P3 offline gate passed. A local Decision Copilot workspace now offers explicit pinned synthetic Context creation, V1.1 Brief preparation and exact content review, request digest preview with a clearly unset production cost policy, separate Owner approval under default-off local configuration, and a Fake Provider response preview checked by P1. The existing development app's Planning workspace remains the default. The Cloud deployment repository was not edited; this is not a Cloud security or paid execution claim. The view's synthetic harness creates a disposable test Run only when the user explicitly requests a Context; this behavior requires owner review against the no-Run-creation product boundary before P4 acceptance.

P4 acceptance is **not complete**. A selected Dashboard regression module unexpectedly processes the repository's `examples/planning/user_data` fixture and creates temporary USER_DATA Runs, contrary to this batch's explicit no-USER_DATA condition. The run stayed in a temporary test directory, but the prohibited data was processed. Work stopped at P4 gate; no final integrated acceptance was run. The historical P3 PASS remains scoped to its synthetic-only tests. P4 cannot be called PASS on this evidence. Further work requires a safe synthetic-only regression selection and review of the local fixture initialization boundary.
