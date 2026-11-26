# Stage 3 — Cloud runtime verification

Date: 2026-11-25 UTC. Verification is **local simulation**, not Streamlit Community Cloud acceptance.

| Check | Result | Evidence / limit |
| --- | --- | --- |
| App import and startup | PASS locally | `python -B -m streamlit run dashboard/scenario_planning_app.py --server.headless true --server.port 18501` started; `/_stcore/health` returned HTTP 200 (`ok`). Process was then stopped normally. |
| Python runtime | PASS WITH LIMITATIONS | Local Python 3.10.20. Intended Community Cloud Python 3.12 is unavailable here; no 3.12 clean-environment test. |
| Dependencies | PASS WITH LIMITATIONS | `python -m pip check` passed. Streamlit 1.56.0, Pandas 2.3.3, NumPy 2.2.6, jsonschema 4.26.0 installed. Plotly is listed in `requirements.txt` but absent locally; UI treats it as optional. Clean install not verified. |
| Public operation without OpenAI key | PASS locally for current Fake path | Startup and FakeProvider tests did not require an API key. No real provider route was executed. |
| Generated output location | PASS | New tests confirm temp root, session isolation and no repository output root for new planning runs. Files remain ephemeral. |
| Existing major pages/workflows | PASS WITH LIMITATIONS | Existing AppTest/dashboard/upload tests and selected planning regressions run locally. No actual browser navigation across all pages or Cloud-hosted test in this stage. |
| Deployment package / manifest | BLOCKED | The 75-file builder intentionally rejects P5 execution content. No new Cloud source or release manifest was generated. |
| Secrets isolation | PASS for prepared interface only | Synthetic credential tests cover missing/invalid Streamlit Secrets. No actual Cloud Secrets or real API key was accessed. |
| Windows independence | PASS for normal UI import/startup | Public Streamlit entrypoint started with no Windows Worker, Credential Manager or Docker command. Local P5 modules remain in development repository. |

Actual Cloud App settings, deployment logs, public visibility, deployed SHA, sleep/wake behavior and browser UAT require Owner-controlled deployment verification at a later authorized stage. Local health 200 does not establish those results.

## Incremental sync verification — 2026-11-26

Cloud entrypoint and guide integration: 20/20 focused working-tree tests passed. The staged-only checkout passed 8/8 Cloud path/runtime tests and a no-Secret startup import plus bilingual guide load. The two dashboard locale files were included with the entrypoint because it uses their new keys. Commit `fb1d5793475408e501e05f4003f46757af040bab` was pushed and confirmed by a fresh fetch. No Cloud deployment or Python 3.12 qualification was performed.
