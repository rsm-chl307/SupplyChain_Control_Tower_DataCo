# Stage 6 — paid AI activation boundary

Date: 2026-11-26. **Stage 6 offline/Mock implementation: PASS WITH LIMITATIONS. Paid AI Activation: NOT READY. Cloud Release: NOT READY.** The real route is disabled by default and was never exercised against OpenAI.

## Separate Owner-controlled qualification required

1. Review the exact proposed release source and deployed SHA. Resolve the separately scoped P5 deployment-source allowlist blocker and verify Python 3.12 / Streamlit Community Cloud compatibility. Do not deploy from this Stage 6 task.
2. Choose an actually available model, confirm its Responses structured-output/parameter compatibility and current official price. Historical `gpt-6-luna` compatibility remains unverified. Configure `AI_MODEL_ID` and all matching price fields only in Owner-controlled Cloud Secrets.
3. Decide whether paid AI is Owner-only or offered to visitors. The shared AI password plus process/session counters is not a reliable public global spending ceiling. Review provider billing controls and determine an acceptable exposure limit; local cost estimates are not billed charges or a provider-side hard cap.
4. After a separate live-test authorization, the Owner configures `OPENAI_API_KEY`, AI password verifier and `AI_REAL_PROVIDER_ENABLED` in Cloud Settings on an Owner-reviewed deployment. Never paste keys/passwords into chat, a command, Git or logs. Keep the flag false until that specific authorization.
5. Run **one** bounded, authorized question through the UI; record only sanitized model, provider request ID, returned usage, latency and P1 result. Verify the actual response against the validated Brief and check the provider usage/billing dashboard separately. If timeout or outcome is ambiguous, do not retry the same dispatch automatically. Disable the flag after the controlled test until the Owner authorizes broader use.

This is a future procedure, not authorization to execute it. No actual Cloud Secrets, production credential, provider billing, real API or deployment was accessed in Stage 6. Existing Planning Engine/WP1/WP2 and public non-AI views remain independent of an API key.
