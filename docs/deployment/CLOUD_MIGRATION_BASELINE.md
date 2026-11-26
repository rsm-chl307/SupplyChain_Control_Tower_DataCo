# Stage 0 — Cloud migration baseline

Date: 2026-11-25 UTC. This audit preceded Stage 1–3 source changes; no application code was changed during Stage 0.

## Repository and deployment

- Development repository: `rsm-chl307/SupplyChain_Control_Tower_DataCo`, branch `main`, local HEAD and read-only remote `main` both `be425671b27918788dfcec0d39b2d221158cfef7`. The historical `b299849` finding is superseded. The index/worktree was already heavily modified (142 entries before this task, including tracked and untracked files); those changes are preserved. No reset, checkout, clean, commit or push was performed.
- Historical records identify separate private Demo repository `rsm-chl307/SupplyChain-Control-Tower-Demo`, with last recorded `main=281ac77ba0745c1ebea041fc8f347ade07b8b6b2`. Its current SHA and deployed Cloud SHA are unverified without Owner access. A fresh unauthenticated HTTP HEAD check on 2026-11-25 returned **303** to `share.streamlit.io`; public access is therefore not verified. See [deployment status](STREAMLIT_DEPLOYMENT_STATUS_REPORT.md) and [UI deployment record](UI_V1_2_1_DEPLOYMENT_REPORT.md).
- Actual entrypoint: `dashboard/scenario_planning_app.py`. Root `requirements.txt` and `.streamlit/config.toml` exist in this worktree but are untracked. The 75-file synthetic deployment allowlist is blocked by the builder's P5 execution-content guard; it includes `eight_call_campaign.py`, Windows Runner files and `provider.py` with `execute_authorized`.

## Product capability inventory

| Capability | Actual status / evidence | Cloud migration disposition |
| --- | --- | --- |
| Planning, allocation, backlog, KPIs, sequential scenarios and CSV input | Implemented in `src/` and used by the Streamlit entrypoint; dedicated planning/allocation/UI tests exist. | Reuse; preserve approved deterministic formulas. |
| WP1 root cause, WP2 scenario comparison/trade-offs | Application imports `src.planning_risk`, `src.scenario_comparison`; UI and test modules exist. | Reuse; validate in Cloud runtime. |
| Demand, inventory, service, capacity and related risks | Planning/risk modules and dashboard views exist; exact coverage varies by view and fixture. | Reuse, with fixture-specific limitations visible. |
| Decision Copilot synthetic preview | `dashboard/copilot_view.py` calls `FakeProvider` and validates response; tests exist. | Keep as clearly labeled offline preview. |
| Real OpenAI Generation and Token Count | P5/Windows local implementation and tests exist, but `REAL_PROVIDER_DISPATCH_LOCKED=True`; Cloud UI is not wired for real calls. | Stage 4+, outside current authorization. |
| Owner authorization / Ledger / Archive | Implemented for local P5 with SQLite and Windows-specific flows; not proven durable on Community Cloud. | Preserve source/history; do not migrate blindly. |
| Secrets adapter | `src/ai_copilot/credential_provider.py` can read `st.secrets` on demand; no Cloud account configuration verified. | Reuse in future backend-only AI path; missing key must not block public app. |

## Local-only dependencies and risks

The Cloud entrypoint currently writes planning runs under repository `tmp/`, and legacy dashboard defaults to `data/processed` (absent from the minimal synthetic deployment). `st.session_state` and local SQLite do not establish durable Cloud state. `dashboard/copilot_view.py` has a loopback-only local Owner gate and local SQLite path; it is not Cloud AI authorization. P5 campaign code imports Windows Runner and uses Host/Container exchange and signing concepts. None should be treated as public Demo prerequisites.

The deployment source contains small synthetic fixtures and templates, while `data/raw`, `data/processed`, and existing `tmp` artifacts are unsuitable for wholesale publication. GitHub/Cloud account settings, actual installed Python version, private Demo SHA, deployed SHA, current public visibility and production Secrets remain unverified. Owner review is required for release and any paid operation.
