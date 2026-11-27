# Stage 8 — implementation progress

Date: 2026-11-26. Objective: implement WP8.1–WP8.5 locally for a reproducible Python 3.12 Cloud candidate. This records the original implementation snapshot, when Git push was outside scope and HEAD/fetched `origin/main` were `a11f98469cbec7ef7d6439f4c8888c38d2773588`. Later authorized publication is recorded in `STAGE_8_SUBMISSION_AUDIT_REPORT.md`. Actual deployment, production Secrets and real AI remain excluded.

## Work package status

| Package | Status and implemented work | Acceptance evidence | Remaining boundary |
| --- | --- | --- | --- |
| WP8.1 Python 3.12 runtime | **Completed locally.** Reused existing uv-managed CPython 3.12.16 in this Debian 13 Container; created `.venv312`; added `.venv312/` ignore; preserved Python 3.10.20. | Root dependencies and test-only Markdown parser installed into venv; five pins, native imports, `pip check`, Stage 8/Stage 7 package tests (5/5) passed. | Cloud OS and installer behavior require actual deployment evidence. |
| WP8.2 dependency/configuration security | **Completed locally.** Root pins unchanged. Test-only `requirements-test.txt` declares `markdown-it-py==4.0.0`. Reviewed backend Secret selection, no-key startup, package exclusions and log redaction. | 35 Cloud access/credential/service/provider tests passed in 3.12; no real provider call. | Production Secrets and Cloud isolation were not accessed or tested. |
| WP8.3 public non-AI runtime | **Completed for local 3.12 scope with product limitation.** Packaged Planning and locked Copilot UI run without API key; synthetic Planning produces 13 outputs. Repaired three UI test files to generate allowed published Runs from tracked fixtures. | Planning/risk/scenario 119/119; UI/workflow/Fake 28/28; Dashboard/WP2 17/17. Isolated source: workflow 10/10 and Dashboard/WP2 17/17. | Legacy Executive Dashboard needs excluded `data/processed` reference data; public Cloud browser UAT remains pending. |
| WP8.4 local Release Candidate | **Completed locally.** Built two independent 74-file candidates using the existing pinned builder; both manifests match byte-for-byte. Tested candidate-a with Python 3.12, no AI key, and local Streamlit HTTP health. | Manifest SHA-256 `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`; 74 hash matches, zero unlisted files/symlinks/targeted secret patterns; health HTTP 200. | Candidate includes modified `.gitignore` and uses untracked builder/allowlist, so it is a local working-tree candidate, not a GitHub-synchronized release. |
| WP8.5 deployment readiness | **Prepared locally.** Runtime acceptance procedure and security checklist are in the Stage 8 test report. | All locally executable checks above passed. | Actual Community Cloud deployment, installation logs, deployed SHA, public browser/UAT and Owner acceptance were **not executed** and need separate authorization. |

## Files and decisions

Created: `.venv312/` (ignored local environment), `requirements-test.txt`, `tests/test_stage8_local_runtime.py`, and `docs/deployment/STAGE_8_PYTHON_312_QUALIFICATION_REPORT.md` plus the four Stage 8/boundary reports listed below. Modified: `.gitignore`, `tests/test_phase2_workflow.py`, `tests/test_dashboard_app.py`, `tests/test_comparison_dashboard.py`, and the Stage 8/boundary reports. Existing P5/Windows, Planning Engine calculations, business rules, root `requirements.txt`, Streamlit configuration and production settings were not modified.

The UI test fixes preserve the server-side path allowlist: test Runs are generated from tracked `examples/planning/` inputs under Git-ignored `tmp/planning_source_runs` or `tmp/user_data_acceptance_2026-11-17/runs`. The tests no longer require pre-existing developer-local Run IDs. The earlier two Dashboard suites generated Runs in generic `/tmp`, which the Cloud-safe UI correctly rejected; they now create their own Runs under the allowed root. No generated Run is staged or committed.

`REAL_PROVIDER_DISPATCH_LOCKED = True` remains unchanged. The 74-file Cloud package excludes the local paid provider, Windows tooling, secrets, `.venv312`, tests, raw/processed data and runtime `tmp` outputs. Existing source builder and allowlist remain local untracked Stage 7 work; no Git commit or push occurred.

## Dependencies and next steps

The local 3.12 installation and previously missing Plotly wheel issue are resolved in `.venv312`. Stage 7 formal acceptance remains separate: its old 3.12 evidence gap has new technical evidence, but its own candidate review and Owner acceptance were not performed. Cloud runtime acceptance needs separately authorized deployment and actual Cloud logs, SHA, sharing and browser checks. Legacy Executive Dashboard reference data remains unavailable in the synthetic-only Cloud package by design; adding reviewed sample data would require a separate product/data decision. Stage 9 paid AI remains out of scope.

Related records: `STAGE_7_STAGE_8_BASELINE_AND_BOUNDARY_REPORT.md`, `STAGE_8_PYTHON_312_QUALIFICATION_REPORT.md`, `STAGE_8_TEST_AND_RUNTIME_VERIFICATION_REPORT.md`, `STAGE_8_RELEASE_CANDIDATE_READINESS_REPORT.md`.
