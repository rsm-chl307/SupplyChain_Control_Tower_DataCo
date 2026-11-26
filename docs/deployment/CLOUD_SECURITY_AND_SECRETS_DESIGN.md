# Cloud security and secrets design

> **Owner decision update, 2026-11-25:** The two-app preference in the original research below is superseded. The confirmed MVP uses the **same Streamlit application** with a backend AI Access Password gate. The API key stays in that App's Streamlit Secrets; public non-AI features must start without it. Password, quotas, code review and provider cost controls remain separate requirements. See [AI access contract](AI_ACCESS_CONTROL_SPEC.md).

Research date: 2026-11-25 UTC. **Design only; no secrets, cloud settings or dispatch were accessed or changed.**

## Four separate controls

| Concern | Proposed control | Boundary |
| --- | --- | --- |
| API key confidentiality | Owner sets `OPENAI_API_KEY` in Streamlit Community Cloud App Settings; server-side code reads `st.secrets`. Never commit `.streamlit/secrets.toml`, log the value, send it to browser, package it in an artifact, or supply it to Codex. [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management). | The app process can read its own secret. `st.secrets` does **not** protect against malicious or accidental code deployed into that same process. |
| Paid-request authorization | Prefer a separate private Owner app with Streamlit account access control and an explicit per-request confirmation/limit. If a single public app is selected, add a server-verified Owner login gate before any paid call; a UI-hidden button is insufficient. | A password is not API-key confidentiality. Never put an Owner password in a public fixture or client-side state. |
| Public abuse | Public app has **no paid API secret or endpoint** in first release. Later Owner app enforces request size, model/operation allowlist, count/day, concurrency and duplicate identity. | App quotas can be lost with ephemeral local state; durable quotas are required for meaningful cross-restart enforcement. |
| Cost monitoring and limits | Provider project budgets/spend controls, alerts, per-request caps and independent usage review. | Alerts do not block traffic; provider hard-limit enforcement may lag. [Spend limits](https://developers.openai.com/api/docs/guides/spend-limits). |

## Deployment and Codex threat model

Codex can read and edit development repository files. It must not receive Streamlit Cloud account permission, App Secrets permission, production API credentials or production deployment credentials. A code change that is automatically deployed could read `st.secrets` and transmit the key; therefore **Owner-reviewed release control is the decisive boundary**. The existing separate private deployment repository is useful because it can contain only reviewed, allowlisted source. Keep production branch write access Owner-controlled; use branch protection/review if supported by the chosen GitHub plan. Do not let development changes auto-publish to the live App. Run secret scanning before release, inspect diffs and dependency changes, then have the Owner publish. [Streamlit deploy behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

Public Demo and private Owner AI app should use separate Cloud App settings and Secrets. The public App should have **no OpenAI key**. A private GitHub source repository does not by itself prove the App is publicly viewable; verify sharing explicitly in Streamlit settings. [Sharing guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

An external secret manager is not justified for the first Demo: Streamlit Secrets already provides server-side configuration without another paid service. Consider an external manager only if a demonstrable rotation, access-audit or multi-service requirement appears. It still cannot protect against malicious code that legitimately fetches a secret.

## Paid AI path, only if separately approved

The Cloud application may call OpenAI server-side under Owner control, but this is a **future migration**, not current readiness. Reuse ProviderRequest, endpoint-specific payload serialization, identity/digest checks, evidence gates and fail-closed handling. Remove the Windows/Docker transport dependency only after tests demonstrate equivalent business/security invariants. Keep exact Request UUIDs, duplicate protection, UNKNOWN/HELD for ambiguous outcomes, and usage/charge reconciliation. Never retry an ambiguous dispatch automatically, and never claim distributed exactly-once. Actual charge evidence must be distinguished from token usage.

Community Cloud session state and local SQLite are not durable enough for authoritative paid-request history. If real Owner AI is added, use a durable transactional record store, such as a small Neon PostgreSQL database, with scoped credentials kept in the private app's Secrets. Define retention and deletion policy before launch. Uploaded business data should be session-scoped by default and excluded from logs.

## Release security checklist for Owner review

1. Review exact deployment diff and dependency lock/pins; verify public source contains no authorized paid dispatch path, secret values, Windows runtime artifacts, raw business data or `tmp` output.
2. Verify production branch and deployed SHA in App settings/build logs; inspect sharing settings and unauthenticated browser behavior.
3. Verify public App has no API secret. Configure private App secret only through Owner-controlled Streamlit settings, if/when paid AI is separately authorized.
4. Verify Owner-only route rejects anonymous users server-side; test request caps, duplicate handling, UNKNOWN, logging redaction and restart behavior before any real provider call.
5. Configure project usage monitoring and realistic spend controls; review actual invoices/usage after launch.

No real key, formal Owner password or production signing key should be pasted into ChatGPT/Codex, source files, scripts, reports or test logs.
