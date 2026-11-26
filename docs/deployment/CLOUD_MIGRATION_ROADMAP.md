# Cloud-only migration roadmap

> **Owner decision update, 2026-11-25:** The earlier separate-private-AI-app option below is superseded. The confirmed direction is one existing Streamlit app with backend AI Access Password protection. Stage 0–3 implementation is recorded in [final acceptance](CLOUD_STAGE_0_3_FINAL_ACCEPTANCE_REPORT.md); Stage 4 and deployment remain separately authorized.

Research date: 2026-11-25 UTC. **Planning only.** The target is a low-cost, publicly accessible Streamlit Community Cloud portfolio Demo. Local development remains a test tool, not a separate production deployment.

| Phase | Work and evidence | Exit criterion / Owner decision |
| --- | --- | --- |
| 0. Recover baseline | Reconcile 2026-11-19 audit, later private Demo deployment records, current original `main=be425671b27918788dfcec0d39b2d221158cfef7`, dirty worktree and existing Cloud preparation blockers. | Baseline in [architecture assessment](CLOUD_ONLY_ARCHITECTURE_ASSESSMENT.md) accepted; Owner confirms actual Streamlit App settings, deployed SHA and current private Demo repo HEAD. |
| 1. Architecture decision | Select Streamlit-only public synthetic Demo, separate private Owner AI app later, or explicitly choose a different scope. Decide whether first public release includes Fake AI preview and whether Owner AI is in the first release. | Owner approves public/paid boundary, persistence policy and deployment repo/branch. No implementation inferred from this research. |
| 2. Cloud compatibility | Make a reviewed, minimal source allowlist; resolve `STREAMLIT_CLOUD_PREPARATION.md` P5 execution-content blocker. Adapt configuration/temporary-file paths; preserve planning rules, validators and UI. Keep Windows code out of Cloud runtime. If paid Owner AI is approved, separately adapt credential adapter and durable execution state; test UNKNOWN/duplicate/charge handling. | Unit/integration tests, source manifest, secrets scan, Linux/Streamlit smoke and restart tests pass. Existing deployment source is not overwritten blindly. |
| 3. Release candidate | Pin compatible dependencies and Python version; verify `dashboard/scenario_planning_app.py`, packaged synthetic fixtures, data sizes, upload/download, bilingual UI and Demo labeling. Review all diffs and generated manifests. | Owner reviews release candidate and approves deployment source; public package contains no API key and no unauthenticated paid path. |
| 4. Deployment and browser UAT | Owner-controlled push to the separate deployment repo/branch; select repo, branch and entrypoint in Streamlit; verify build logs/deployed SHA, public sharing, unauthenticated browser, sleep/wake, CSV workflows and downloadable outputs. Paid AI validation, if separately authorized, runs only in private app with durable state. | Public URL works without authentication and tested flows pass; explicit Owner approval required before any Cloud deployment, Secrets configuration or real API call. |
| 5. Demo acceptance | Record functionality and coverage limits, measured hosting/API cost, data retention limits, security gates, deployed SHA, final public URL and rollback procedure. | Owner accepts the portfolio Demo; paid AI remains disabled until independently qualified and authorized. |

## Dependencies and practical order

Phase 2's first slice can ship the deterministic Demo without waiting for database selection. Paid AI is a separate dependent slice: Owner access model → durable request/quota/UNKNOWN records → server-side Secrets → fake integration and restart recovery → security review → separately authorized live test. Do not migrate all CSVs to PostgreSQL. Keep static datasets packaged, temporary user work in session state or downloads, and only persist records with a defined cross-session need.

Use the existing deployment repository as a review boundary, subject to Owner verification of its current SHA and access controls. The original development worktree has many unrelated staged/unstaged/untracked changes; do not push it wholesale. The existing Streamlit URL currently redirects unauthenticated visitors to a login flow, so publication and browser acceptance remain open.

## Decisions needed from the Owner before implementation

1. Approve **Option A** as first public release and confirm whether Fake AI preview is included; confirm no public paid AI.
2. Approve separate private Owner AI app as the preferred future paid path, or choose a single public app with a stronger server-side Owner gate and corresponding risk acceptance.
3. Confirm whether any user-generated or AI records must survive sleep/redeploy. If yes, approve a minimal durable store and retention policy (Neon is the DB-only fallback).
4. Confirm who controls the separate deployment repo, protected/reviewed branch, Streamlit sharing and Secrets. Provide **status only**, never credentials.
5. Authorize source changes, deployment, Cloud Secrets setup and real API evaluation separately at their respective stages.

## Deferred local-production work

Do not proceed with WP3.6 External Issuer, Windows Native deployment, Credential Manager qualification or Count Worker remediation as Cloud Demo prerequisites. Retain their code and evidence without deleting them during research. Reuse business and P5 evidence tests where they help qualify Cloud paid operations. No Cloud migration code, infrastructure or configuration was changed in this task.
