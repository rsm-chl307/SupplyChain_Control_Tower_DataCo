# Stage 4 — AI integration implementation

Date: 2026-11-25 UTC. Scope: existing Streamlit app, **Fake Provider only**. No real OpenAI call, paid operation, production Secret access, P5 release remediation or deployment.

## Architecture and reused contracts

The existing Decision Copilot workspace now requires a backend-validated AI Access Password before it renders synthetic context creation, Brief review or Fake Provider actions. Planning and other public Dashboard pages remain outside that gate. The masked form's submit callback verifies the password with the Stage 2 scrypt helper and removes the password widget state before rendering. Only access expiry, failed-attempt count and lockout timestamp remain in server-side session state. A successful session lasts 30 minutes; five failures lock the session for 15 minutes. This is not durable cross-session abuse control.

The user can create the existing trusted SyntheticHarness context, prepare a `ValidatedBrief`, ask a bounded question and follow up. `prepare_cloud_question()` reuses `build_request()` and `provider_brief()` and binds the exact Brief/ProviderRequest digest, question, up to three validated prior turns, and at most two selected business-document excerpts into a SHA-256 question digest. The excerpts come from the existing KPI, risk, service and capability documents; each carries its full-source SHA-256. `cloud_response_arguments()` constructs the official Responses-style `model`, `instructions`, `input`, structured `text.format`, no-tools and bounded-output arguments. The Planning Engine remains the source of numerical truth.

The UI explicitly uses existing `FakeProvider`, creates a topic-appropriate but deliberately limited synthetic response, and validates it through the existing P1 `classify_response()` evidence gate before display. Missing evidence is shown as a limitation. Failed, malformed and uncertain responses cannot become validated advice. Follow-up history contains only previously validated summaries. No production provider is selected automatically.

`CloudOpenAIProvider` is a backend-only prepared boundary. It can validate/construct requests and exercise them with the existing one-shot `OfflineMockTransport` in tests. Its real `execute()` remains locked and does not read credentials or open a socket. The existing `StreamlitSecretsCredential` remains the eventual Cloud key source; real dispatch and paid authorization require separate future work. The previous P5 `REAL_PROVIDER_DISPATCH_LOCKED=True` was not changed. Official [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create) and [structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs) were reviewed on 2026-11-25; model availability and actual provider behavior are not established by Fake tests.

## JSON path security

The prior user-controlled JSON path and its nested CSV references could read arbitrary server files. `dashboard/cloud_paths.py` now permits only the exact packaged synthetic JSON configuration and adjacent validated CSV files. The separate CSV upload workflow remains. Published-run loading is limited to current-session generated outputs or historical synthetic runs; symlink escape and symlinked manifest are rejected. See [security review](JSON_CONFIGURATION_SECURITY_REVIEW.md). This gate was addressed in code and tests; Owner-reviewed release source remains necessary.

## Files changed or created

- Changed: `dashboard/copilot_view.py`, `dashboard/scenario_planning_app.py`, `src/ai_copilot/cloud_access.py`; Stage 2 access/context/Secrets documentation updated.
- Created: `dashboard/cloud_paths.py`, `src/ai_copilot/cloud_question.py`, `src/ai_copilot/cloud_knowledge.py`; focused Cloud path/question/knowledge/UI tests; this report, [test report](STAGE_4_AI_INTEGRATION_TEST_REPORT.md) and [JSON security review](JSON_CONFIGURATION_SECURITY_REVIEW.md).

Pre-existing worktree changes were preserved. No business formula, WP1/WP2 algorithm, P5 package schema, Worker, Ledger, Archive, dispatch lock or historical evidence was changed.

## Remaining boundary

Stage 4 is a Fake-validated AI experience, **not a live OpenAI release**. Stage 5 must qualify public abuse controls, durable quotas/accounting, Secret handling, paid authorization, error/retry policy and provider spending controls. The deployment-source P5 content blocker remains for separate release preparation. Actual Streamlit Cloud Python 3.12 and browser behavior are unverified. Do not put an API key or real Owner password in this worktree or tests.

**Stage 4 status: PASS WITH LIMITATIONS.** The Fake workflow and relevant regression checks passed (see test report). The application foundation can proceed to separately authorized Stage 5 security/cost work, but it is not ready for real API execution or Cloud release. Existing worktree changes were preserved; final inspection showed 35 modified and 139 untracked entries, including pre-existing user work. No commit or push was performed.
