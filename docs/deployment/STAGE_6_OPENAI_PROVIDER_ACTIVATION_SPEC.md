# Stage 6 — OpenAI Provider activation specification

Date: 2026-11-26. This stage implements an offline-qualified Cloud provider path. It does not authorize a live API call, Cloud Secrets access, deployment, or paid use.

## Goal and boundaries

Keep the existing Streamlit Decision Copilot, deterministic Planning Engine, Stage 4 validated Brief/P1 response contract, and Stage 5 backend authorization, rate, duplicate, size, and estimated-budget checks. The public Planning pages must work without AI configuration. No P5 Worker, deployment allowlist, Ledger, Archive, WP1/WP2 business rule, database, or new service is changed.

## Request path and contract

`Streamlit form → CloudAIService.ask → authorized grant → prepare_cloud_question → cloud_response_arguments → canonical UTF-8 JSON bytes → Stage 5 size/price/rate/budget reservation → selected provider → P1 classify_response → UI`.

The service passes the exact immutable, digest-bound bytes it measured to the provider. After reservation, it also issues a short-lived, process-local, one-use dispatch ticket bound to the request and wire digests; direct provider invocation without this ticket is rejected before credential lookup. The provider consumes the ticket, verifies provenance and fixed safety fields, and sends the measured bytes unchanged. This ticket is an application-internal handoff, not a durable/global paid authorization or a guarantee of exactly-once API execution. The request contains one selected model, reviewed Brief/context/question, structured JSON schema, no tools, `store=false`, non-streaming output, a 500-token output setting and bounded timeout. No API key or password is part of the request body. The REST transport has a fixed HTTPS host/path (`api.openai.com/v1/responses`), one attempt and a bounded response read. It does not follow redirects or accept a caller-supplied endpoint. Python's standard library is used; no SDK dependency or dependency installation is needed. The official Responses create reference was checked on 2026-11-26: https://developers.openai.com/api/reference/resources/responses/methods/create . Actual model compatibility is unverified.

The response is accepted only after HTTP/status classification, returned-model check, bounded body parsing, usage validation when present, and the existing P1 evidence/schema gate. Missing usage is recorded as unknown; estimated cost is never represented as billed cost. Timeout or uncertain transport outcome consumes the Stage 5 reservation and is never automatically retried.

## Secrets and activation

Only the backend `StreamlitSecretsCredential` reads `OPENAI_API_KEY`, immediately before a permitted transport call. No key enters Streamlit Session State, UI responses, logs, exchange files or tests. Mock tests use synthetic credentials and an injected transport with the same byte contract. Real transport is selected only by explicit backend `AI_REAL_PROVIDER_ENABLED=true` configuration; the default remains Fake. The P5 `REAL_PROVIDER_DISPATCH_LOCKED=True` is unchanged. A future Owner-controlled Cloud Secrets configuration and deployment is a separate authorization boundary; simply implementing this switch does not authorize using it.

The configured model `AI_MODEL_ID` and the four Stage 5 price fields must be complete for the real route. The exact model must be checked for API availability, compatible output schema and current price by the Owner before any separately authorized live test. `gpt-6-luna` from historical P5 work is not claimed to be available in the Cloud API.

## Stages and acceptance

1. **6.1 Provider readiness:** one immutable request byte contract and fixed REST transport; Fake/Mock and production adapter share it.
2. **6.2 Secrets:** backend-only credential lookup with sanitized missing/invalid handling; public Planning remains independent.
3. **6.3 Controlled test preparation:** disabled-by-default real selection, one attempt, explicit model/timeout/size/output settings and a documented Owner-only future procedure.
4. **6.4 Response:** bounded parse, status/model/usage/error handling and P1 validation before UI.
5. **6.5 Cost:** preserve Stage 5 reservations, record reported usage separately, require matching price configuration for an enabled real route.
6. **6.6 Integration:** Fake/Mock UI and service tests plus WP1/WP2/planning/public-page regression.

Each stage requires targeted no-network tests before the next. Final evidence includes test commands/results, `git diff --check`, status comparison, and a source-only secret-pattern scan. Mock success never certifies a live model, Cloud deployment, exact billing or a durable/global quota.

## Owner gates and stop conditions

Live API execution, actual Cloud Secrets, production deployment, provider billing verification, P5 release remediation, commit/push and Stage 7 require separate Owner authorization. Any need to change a frozen business rule or approved architecture stops that affected work. Stage 6 ends after offline implementation and regression evidence.
