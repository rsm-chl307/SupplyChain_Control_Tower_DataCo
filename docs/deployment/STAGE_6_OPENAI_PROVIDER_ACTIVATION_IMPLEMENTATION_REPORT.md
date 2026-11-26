# Stage 6 — OpenAI Provider activation implementation

Date: 2026-11-26 UTC. **Offline/Mock implementation only.** No real API, production key, paid usage, Cloud deployment, P5 release remediation, commit or push.

## Baseline and scope

At start, `main` was `be425671b27918788dfcec0d39b2d221158cfef7`, with 35 modified tracked files, 176 untracked and zero staged. Existing work was preserved. Stage 4/5 implementation, tests, four Stage 5 reports, Cloud Secrets instructions, current `requirements.txt`, Responses request builder, P1 validator and Streamlit UI were inspected. The current runtime declares no OpenAI SDK. Stage 6 uses the Python standard-library HTTPS client for one fixed Responses endpoint, adding no dependency or environment-level change. The [official Responses create reference](https://developers.openai.com/api/reference/resources/responses/methods/create) was checked 2026-11-26 for request/response shape; no claim is made that a particular model supports every parameter.

## Completed 6.1–6.6

| Stage | Implementation | Validation |
| --- | --- | --- |
| 6.1 Provider | `CloudAIService` canonicalizes and measures the full Responses arguments, then passes immutable bytes plus SHA-256 in `CloudQuestionRequest`. After reservation it issues a short-lived, one-use process ticket; the provider rejects direct invocation without it and consumes it before key lookup. `CloudOpenAIProvider` verifies provenance and sends the measured bytes. `HTTPSResponsesTransport` fixes host/path, does not follow redirects and makes one attempt. | Exact bytes, digest tampering, direct-call/replay rejection and fixed-endpoint Mock tests. |
| 6.2 Secrets | Existing `StreamlitSecretsCredential` remains the only Cloud key source. Lookup occurs only after Service authentication and budget reservation and provider payload verification. Missing/invalid/inaccessible values produce safe categories. | Synthetic credential/no-key/UI tests; no formal Secret access. |
| 6.3 Activation | UI defaults to Fake. Only backend Boolean `AI_REAL_PROVIDER_ENABLED=true` selects the Cloud adapter. Real selection requires explicit non-fixture `AI_MODEL_ID` and complete matching price configuration. Existing P5 lock remains unchanged. | Disabled, missing-config and pre-provider rejection tests. |
| 6.4 Response | Bounded HTTP body, status/model check, usage extraction and existing P1 response validation. Uncertain transport/parse result is not retried; incomplete or oversize output cannot be displayed as accepted advice. | Complete, malformed, wrong-model, incomplete, HTTP error and timeout tests. |
| 6.5 Cost | Stage 5 price reservation remains before transport. Reported usage and provider request ID are retained only in the authenticated UI session; the UI labels the reservation as an estimate, not a billed charge. Missing usage stays unknown. | Mock usage, missing usage, over-cap usage, price mismatch and budget rejection tests. |
| 6.6 Integration | Existing Decision Copilot UI uses the same backend Service for Fake and selected Cloud adapter. Public Planning remains independent of the key. The fixed synthetic Brief and business excerpts remain the context; Planning Engine calculations are unchanged. | Mock UI E2E, Stage 4/5 AI regression, Planning/WP1/WP2/Scenario regression. |

The transport's API key is supplied only as an HTTP Authorization header. No key is placed in request bytes, `st.session_state`, logs or returned evidence. Tests block socket connections and inject synthetic credentials and Mock transport. `CloudOpenAIProvider.execute_mock()` and existing Fake Provider behavior remain available. No P5 Worker, package contract, allowlist, Ledger, Archive or frozen business rule was modified.

## Files

- Modified within Stage 6 scope: `src/ai_copilot/cloud_question.py`, `src/ai_copilot/cloud_ai_service.py`, `dashboard/copilot_view.py`, `docs/deployment/CLOUD_SECRETS_CONFIGURATION.md`.
- Created: `tests/test_stage6_cloud_provider.py`, `STAGE_6_OPENAI_PROVIDER_ACTIVATION_SPEC.md`, `STAGE_6_IMPLEMENTATION_PLAN.md`, this report, `STAGE_6_OPENAI_PROVIDER_ACTIVATION_TEST_REPORT.md`, `STAGE_6_PAID_AI_ACTIVATION_READINESS.md`.

The three source modules were already part of substantial pre-existing untracked/unstaged Stage 4/5 work. The baseline Git status was recorded before the Stage 6 edits; historical work was not reset, cleaned, committed or replaced.

## Remaining limits

- No real API call, model compatibility, real Usage, provider billing, Cloud Secret or Python 3.12 Cloud runtime was verified.
- Historical `gpt-6-luna` availability and structured-output support are unverified. Select and price a model only in a future Owner-controlled qualification.
- Session/process counters and estimated cost retain the Stage 5 documented limitations; no durable global budget or provider-side hard cap is claimed.
- The Service handoff ticket is process-local and one-use. It closes an accidental direct-provider bypass in this application, but does not protect against malicious deployed application code or guarantee exactly-once execution across an HTTP failure.
- A validated response proves schema/evidence-reference conformance, not that a live model's prose is substantively correct. Human/ground-truth review remains necessary.
- The public AI password is a shared access gate. Enabling real transport for public visitors before a separately approved abuse/cost policy would expose paid usage; leave the flag false.

**Stage 6 implementation assessment: PASS WITH LIMITATIONS** for offline/Mock scope. Paid activation and Cloud release remain NOT READY. See the [test report](STAGE_6_OPENAI_PROVIDER_ACTIVATION_TEST_REPORT.md) and [readiness boundary](STAGE_6_PAID_AI_ACTIVATION_READINESS.md).

Final Git review: all 211 baseline status entries remained present. The only new status entries were the six Stage 6 files listed above. Tracked modified count remained 35; untracked count rose from 176 to 182; staged count remained zero. `git diff --check`, focused AST parsing and targeted Secret-pattern/trailing-whitespace checks passed. No commit, push, reset or cleanup was performed.
