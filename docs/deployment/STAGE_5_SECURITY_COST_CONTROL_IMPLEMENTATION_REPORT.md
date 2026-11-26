# Stage 5 — Security and cost control implementation

Date: 2026-11-26 UTC. Scope: existing Streamlit Cloud AI Fake path only. No real provider dispatch or production Secret access.

## Implementation plan (recorded before source changes)

1. ST5.1–5.2: issue a short-lived, process-signed access grant after the existing scrypt password check; require grant verification inside the backend AI service. Keep the actual password out of session state. Preserve the Streamlit Secrets-only credential abstraction and fail-closed configuration behavior.
2. ST5.3–5.4: add per-session request frequency, duplicate-submission, conservative input-size/output-size and usage controls. A missing model price blocks cost estimates but cannot be represented as a verified spending ceiling. Do not add a database or external service.
3. ST5.5–5.6: use a single safe service result/error contract for Fake/Mock providers, bound Brief context, validated P1 responses and sanitized failures. Preserve the Stage 4 JSON path allowlist.
4. Run focused tests after each implementation unit, then AI/UI, WP1/WP2/planning and path security regression. Inspect the full Stage 5 diff and `git diff --check`.

Excluded: Planning Engine, WP1/WP2 calculations, P5 dispatch contracts, deployment allowlist, real API activation, Docker and existing production data. Main risks: Streamlit session counters are not durable or global; byte bounds are not an exact model token count; no verified provider-side spend cap exists.

## Implementation

| Work package | Stage 5 change | Evidence |
| --- | --- | --- |
| ST5.1 access/session | `cloud_access.py` now mints a process-signed 30-minute grant only after the existing scrypt check and five-failure lockout. The backend service verifies the signature, expiry, current verifier and lockout. Mutating an expiry flag alone cannot authorize a request. A restart invalidates grants. | `tests/test_cloud_access.py`, `tests/test_cloud_ai_service.py`, UI AppTest |
| ST5.2 API key | `StreamlitSecretsCredential` remains the only prepared Cloud key source and returns sanitized missing/invalid errors. The Stage 5 Fake path neither requests nor stores a key. `CloudOpenAIProvider.execute()` and P5 real dispatch stay locked. | `tests/test_cloud_credential_provider.py`, socket-blocked UI tests |
| ST5.3 rate | `CloudAIService` reserves each accepted request under a lock: one-second spacing, three per minute, eight per grant/session and 30 per process UTC day. Exact request digest cannot be submitted twice under one grant. | `tests/test_cloud_ai_service.py` |
| ST5.4 usage/cost | The full serialized request is capped at 30,000 UTF-8 bytes, output at 500 configured tokens and 16,000 response bytes. Per-grant reservations cap input at 240,000 bytes and output at 4,000 configured tokens. Optional model-specific prices and a session estimated USD limit are read from settings; partial/invalid price configuration fails closed. A missing price is reported as unpriced, never as zero cost. | Service size, budget, price and response tests |
| ST5.5 errors | One safe `CloudAIRejected` code contract covers access, configuration, rate, budget, context, provider and response failures. Provider exceptions are not shown to users. A timeout/unknown result consumes its reservation and is not retried. Logs contain only sanitized categories. | Fake failure-injection tests |
| ST5.6 data | The service reuses the Stage 4 validated Brief, explicit provider projection and two reviewed business-document excerpts. P1 response validation remains mandatory. Reviewed documents reject symlinks; the packaged JSON/CSV and run-path allowlists remain in force. | Context, path, response and UI tests |

The existing Copilot Fake preview and question buttons both call the backend service. A failure removes any previous response from the current display. Validated follow-up summaries remain bounded. Public Planning never calls the AI service or credential provider. No Planning Engine, WP1/WP2 formula, P5 package schema, Worker, Ledger or Archive was changed. No dependency or infrastructure was added.

### Files changed and created

- Modified: `src/ai_copilot/cloud_access.py`, `src/ai_copilot/cloud_knowledge.py`, `dashboard/copilot_view.py`, `tests/test_cloud_access.py`, `tests/test_cloud_knowledge.py`, `tests/test_stage4_cloud_ai_ui.py`.
- Created: `src/ai_copilot/cloud_ai_service.py`, `tests/test_cloud_ai_service.py`, and the four Stage 5 reports. The existing Stage 4 and Cloud security documents receive only status clarifications.

## Limitations and decision

Process-local limits reset on restart, differ across replicas and can be bypassed by creating a fresh authenticated session. They are not a reliable global rate limit, durable daily budget or provider spending cap. Input bytes are a conservative local proxy, **not an exact provider token count**; output token cap is a request setting, and a truncated/oversized response is rejected. Prices are Owner-configured estimates, not provider charge evidence. The actual model price and provider-side hard spending limit are unverified. Live transport and durable paid accounting remain locked/out of scope. Streamlit Community Cloud Python 3.12, release source and browser deployment remain unverified.

**Stage 5 outcome: PASS WITH LIMITATIONS for the Fake/Mock scope.** This is suitable for subsequent authorized integration review, not real API or Cloud release approval. Test detail is in [the test report](STAGE_5_SECURITY_COST_CONTROL_TEST_REPORT.md).

Final worktree inspection: 35 modified tracked entries and 145 untracked entries, including substantial work that predates Stage 5; no staged changes. Existing work was preserved. `git diff --check` passed, and no commit or push was made.
