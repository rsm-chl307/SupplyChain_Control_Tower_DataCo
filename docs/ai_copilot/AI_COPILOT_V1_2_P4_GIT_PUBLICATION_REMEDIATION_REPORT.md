# V1.2 P4 Git publication remediation report

Date: 2026-11-22 UTC. **P4 Git publication verdict: PASS.** This verdict covers the isolated, tested P4 commit and remote verification. It does not change the earlier product-level P4 **PASS WITH LIMITATIONS** assessment or authorize paid/provider/Cloud execution.

## Initial state and root cause

At preflight, `main`, local `origin/main` and the live remote `refs/heads/main` all pointed to `4942e3042e7b1009dc88e8be6b6d6662aafef0be`. Seven P4 files were already staged: `dashboard/copilot_view.py`; the V1.2 design, implementation and technical/security review documents; `tests/copilot_browser_uat.py`, `tests/test_ai_copilot_dashboard_synthetic.py` and `tests/test_ai_copilot_ui.py`. The Dashboard entrypoint and English/Traditional Chinese locale JSON were unstaged, mixed with unrelated User Guide, Planning and presentation changes. Other user docs, tests, caches, deployment docs and historical P5 reports were also dirty or untracked and were preserved.

The earlier narrow P4 index candidate exposed a Copilot workspace but returned before the existing Planning-only `_language_sidebar(model)` ran. Therefore the Copilot page had no `ui_language_request` selector, contrary to the existing bilingual navigation test. The working-tree page had a global selector, but that implementation was intertwined with a User Guide and Planning UI revision. Staging the entire entrypoint would have published unrelated work. The [initial boundary assessment](AI_COPILOT_V1_2_P4_GIT_BOUNDARY_ASSESSMENT.md) records the source and test evidence.

## Isolation and exact published change

Created `dashboard/copilot_locale.py::render_copilot_locale_selector`. It reuses the existing `ui_language_request` key and the entrypoint's `_apply_locale` callback only while the Copilot branch is active. Planning keeps its published locale form/sidebar behavior; locale changes remain presentation-only. The published `dashboard/scenario_planning_app.py` adds only two imports and a six-line `ui_workspace` branch. English and Traditional Chinese locale JSON include only the P4 Legacy-versus-horizon Service Level wording. No deterministic KPI, Planning formula, Run, artifact, P1, P2 or P3 logic was changed.

The mixed working-tree entrypoint was **not overwritten**. A narrow patch was applied only to the Git index from the published `HEAD`; its exact staged bytes were materialized temporarily as `dashboard/_p4_staged_preview.py` to test the commit candidate. The generated file was removed after verifying it matched the staged blob. The original User Guide, Planning, localization and other pre-existing changes remain in the working tree.

Added `tests/test_ai_copilot_locale.py` for the shared-key bilingual selector. Existing P4 AppTest modules and Chromium UAT gained an allowlisted `COPILOT_P4_ENTRYPOINT` choice between the normal entrypoint and the local staged preview. Their assertions were not weakened; arbitrary paths and symlinks are rejected. The committed default still tests `scenario_planning_app.py`.

## Validation of the exact staged candidate

All commands used synthetic data only. `COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py` selected the exact staged entrypoint for AppTest and browser runs; the existing `tests.synthetic_only_suite` selected fixed modules, rejected USER_DATA/production paths and socket connections, and allowed only `SYNTHETIC_DEMO` Planning preparation.

| Test command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ai_copilot_locale -v` | **1 passed**, 0 failed/errors/skipped |
| `PYTHONDONTWRITEBYTECODE=1 COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py python3 -B -m tests.synthetic_only_suite focused` | **15 passed**, 0 failed/errors/skipped, 88.398 s |
| `PYTHONDONTWRITEBYTECODE=1 COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py python3 -B -m tests.synthetic_only_suite dashboard` | **15 passed**, 0 failed/errors/skipped, 1.312 s |
| `PYTHONDONTWRITEBYTECODE=1 COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py python3 -B -m tests.synthetic_only_suite contracts` | **49 passed**, 0 failed/errors/skipped, 92.323 s |
| `PYTHONDONTWRITEBYTECODE=1 COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py python3 -B -m tests.synthetic_only_suite integrated` | **192 passed**, 0 failed/errors/skipped, 535.396 s |
| `PYTHONDONTWRITEBYTECODE=1 COPILOT_P4_ENTRYPOINT=_p4_staged_preview.py tmp/wp2_browser_uat_phase_a/venv/bin/python -B tests/copilot_browser_uat.py` | **PASS**, Chromium local UAT, `external_requests=0` |

The first browser command with system Python stopped before browser execution because `playwright` was absent there. The already existing local test virtual environment supplied it without installation. A second attempt could not bind `127.0.0.1` inside the sandbox; the same local-only UAT passed outside that socket restriction. Browser routing blocked all off-origin requests. No real provider request or charge occurred. Streamlit emitted existing bare-mode/deprecation warnings during AppTest; they were not test failures.

## Staged boundary and push verification

The reviewed P4 implementation commit contained exactly 13 paths: `dashboard/copilot_locale.py`, `dashboard/copilot_view.py`, `dashboard/scenario_planning_app.py`, two locale JSON files, four V1.2 documents (including the initial assessment), and four P4 test/UAT files. `git diff --cached --check` and `git diff --check` passed. Staged Python/JSON parsed; a staged-blob scan found no excluded path, credential pattern, trailing whitespace, USER_DATA, environment file, cache or runtime database. The staged entrypoint diff was only eight additions; locale diffs were only three changed Service Level lines. User Guide, unrelated Planning, product catalogs/guides, `test_phase2_workflow.py`, caches and deployment files were excluded.

Commit **`a9332b305db94e578d62ffb08e73f7401b2d4dc8`** (`feat(ai-copilot): publish isolated P4 Dashboard integration`) was pushed without force to `origin/main` at `https://github.com/rsm-chl307/SupplyChain_Control_Tower_DataCo.git`. A separate `git ls-remote origin refs/heads/main` returned that exact SHA. The preceding V1.1/P1–P3 commit `4942e3042e7b1009dc88e8be6b6d6662aafef0be` and both P5 commits remain in its history. This report is a documentation follow-up to the verified P4 implementation push.

## Security, remaining work and limits

No USER_DATA fixture was opened or processed; no production Run or Published Artifact was used as test input or modified. No OpenAI/API key was accessed, no real provider call or charge occurred, and no deployment was performed. Only authorized Git push and localhost UAT used network capability; the Chromium test observed zero external browser requests. The OpenAI adapter remains blocked. The original dirty User Guide/Planning/localization files and other untracked user work remain untouched.

Cloud runtime, real SDK/provider behavior and a full 305-second elapsed-time cleanup test remain outside this publication verification. The report's P4 **PASS** states that the isolated Git change set is complete and tested; it is not a claim of paid or Cloud readiness. P5 paid acceptance and P6 deployment remain not authorized.
