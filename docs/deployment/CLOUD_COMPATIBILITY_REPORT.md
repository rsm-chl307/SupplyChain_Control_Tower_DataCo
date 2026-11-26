# Stage 1 — Cloud compatibility report

Date: 2026-11-25 UTC. Target: Streamlit Community Cloud, existing `dashboard/scenario_planning_app.py`.

## Inspected

The app imports the existing planning, risk, scenario, WP1/WP2, brief and synthetic Copilot modules. Root `requirements.txt` pins Streamlit, Pandas, NumPy, Plotly and jsonschema; Plotly is optional in the UI. Python 3.12 is the intended Cloud runtime, but only Python 3.10.20 is available here. `python -m pip check` passed; Plotly is not installed locally. The current app uses no Windows Worker or Docker command on its normal public path.

## Compatibility changes

Generated upload and sequential planning outputs now use a random, per-browser-session directory beneath the OS temporary directory, via `_session_runtime_root()`. This replaces three writes to repository `tmp/planning_upgrade_runs`. The paths remain ephemeral and are not a persistence guarantee. The existing static fixture, templates, locale files and Guide remain repository-relative and unchanged. The legacy independent-week view still expects `data/processed`; that dataset is intentionally not packaged for a synthetic-only Cloud source, so the view shows its existing unavailable-data warning.

The public app is not dependent on an OpenAI key. The current Decision Copilot route remains FakeProvider preview only. The loopback-only local Owner gate does not authorize Cloud AI. The existing credential adapter has an explicit Streamlit Secrets source but is not called at app startup.

## Verification and limits

Targeted Cloud access/credential/runtime-path tests: 9/9 pass. Dashboard and upload tests with the initial Cloud access tests: 19/19 pass. Local Streamlit server started on Python 3.10; `/_stcore/health` returned HTTP 200. This proves local server startup, not browser navigation or Community Cloud execution. Python 3.12 and a clean dependency installation could not be exercised in this Container. The newer 75-file deployment builder remains blocked by its P5 content guard; no guarded release source was generated.

See [blockers](CLOUD_MIGRATION_BLOCKERS.md) and [runtime verification](CLOUD_RUNTIME_VERIFICATION_REPORT.md). No deployment or API call occurred.
