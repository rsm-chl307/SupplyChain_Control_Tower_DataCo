# Cloud migration blockers and open gates

Date: 2026-11-25 UTC. These are release/qualification gates, not reasons to remove existing product logic.

| Gate | Current state | Minimum safe next step |
| --- | --- | --- |
| New 75-file synthetic deployment allowlist | **BLOCKED.** It includes `eight_call_campaign.py`, Windows Runner files and `provider.py` with `execute_authorized`; `build_streamlit_demo_source.py` intentionally rejects it. | Review a Cloud-safe source boundary and prove it preserves the current Copilot preview without shipping local paid execution runtime. Do not disable the guard merely to publish. |
| Cloud Python/dependency qualification | **NOT VERIFIED.** Local Python 3.10.20, Cloud target 3.12; local Plotly absent though declared. | Run fresh Python 3.12 install and full app/browser checks in a suitable environment or reviewed Cloud staging, after Owner authorization. |
| Public Demo deployment | **NOT VERIFIED.** A fresh 2026-11-25 unauthenticated HTTP HEAD check of the Demo URL returned 303 to `share.streamlit.io`; current private repo SHA and deployed SHA unavailable. | Owner checks Streamlit settings, sharing, build logs and current deployment repo SHA; deployment requires separate authorization. |
| Legacy `data/processed` dashboard | **LIMITED** in synthetic-only package; sequential synthetic and upload workflows are independent. | Preserve explicit unavailable-data message or approve a non-sensitive packaged sample for that view. Do not ship raw/processed datasets wholesale. |
| Future paid AI in same app | **NOT IMPLEMENTED in Stage 0–3.** Provider dispatch remains locked; no UI gate is wired to a real API path. | Stage 4 authorization and implementation, with Stage 5 quotas/security testing. |
| Durable paid history and abuse control | **UNRESOLVED.** Session state and temporary files are not durable; no database is approved. | Decide whether initial owner-only AI needs persistent cross-restart execution history. Demonstrate need before adding service. |
| User-supplied JSON configuration path | **SECURITY REVIEW REQUIRED before adding Cloud secrets/paid AI.** Current UI accepts a path, for local data use. | Define a Cloud-safe allowlist or upload mechanism during Stage 4/5; never permit arbitrary server-file reads in a secret-bearing public app. |

No Owner password, API key, Cloud Secret, production Ledger or historical EV-01 record was accessed or modified.
