# V1.2 P4 Git change-boundary assessment

Date: 2026-11-22 UTC. This is the pre-implementation assessment. No P4 commit is authorized to include unrelated User Guide or Planning edits.

## Git baseline

- Repository: `/workspace/SupplyChain_Control_Tower_DataCo`; branch `main`; `HEAD` and local `origin/main`: `4942e3042e7b1009dc88e8be6b6d6662aafef0be`. A read-only `git ls-remote origin refs/heads/main` returned the same SHA. The two P5 commits remain ancestors.
- Seven staged P4 files: `dashboard/copilot_view.py`; `docs/ai_copilot/AI_COPILOT_V1_2_DESIGN_SPECIFICATION.md`, `AI_COPILOT_V1_2_IMPLEMENTATION_REPORT.md`, `AI_COPILOT_V1_2_OVERALL_TECHNICAL_SECURITY_REVIEW.md`; `tests/copilot_browser_uat.py`, `test_ai_copilot_dashboard_synthetic.py`, `test_ai_copilot_ui.py`. Their staged diff is 1,196 added lines.
- Unstaged mixed tracked files: `dashboard/scenario_planning_app.py`, `dashboard/locales/{en,zh-TW}.json`, four user-facing catalog/guide documents, `tests/test_phase2_workflow.py`, and pre-existing Python caches. Untracked `dashboard/user_guide/`, older P5 reports, deployment documentation and other unrelated work remain untouched. No USER_DATA file is staged.

## Exact change boundary

`dashboard/copilot_view.py` is a self-contained P4 view with its own English/Traditional Chinese labels, trusted synthetic Context workflow, Fake Provider preview and local Owner gate. P4 requires an entrypoint import, a `ui_workspace` selector and a branch to `render_copilot()`. The current working-tree entrypoint also imports `dashboard.user_guide`, changes the global locale selector, modifies Planning upload/configuration behavior and adds guide rendering. Both locale JSON files contain the P4 Legacy-versus-horizon Service Level wording alongside unrelated guide labels, Planning help and presentation text. The catalog/guide docs and `test_phase2_workflow.py` are unrelated to P4 publication.

Dependency graph for the isolated publication:

```text
scenario_planning_app.main → ui_workspace radio → Copilot-only locale selector
                                                    → copilot_view.render
                                                    → V1.1 Brief + P1/P2/P3 services
Planning branch → existing _language_sidebar / _language_form (unchanged)
```

The earlier partial index patch inserted only the workspace branch. It fails the intent of `test_locale_navigation_keeps_machine_workspace_and_no_run_selection`: the `ui_language_request` selector is rendered by `_language_sidebar(model)` only in the Planning branch, so the Copilot branch has no selector. The current working tree passes because its global selector was added together with unrelated User Guide code. Staging that whole file would pull unrelated Planning and guide changes into P4.

## Minimal extraction plan

Add a small P4-only selector helper using the existing `ui_language_request` and `_apply_locale` callback, displayed **only** in the Copilot branch. Keep the Planning branch and its existing locale form/sidebar behavior from `HEAD` unchanged. Stage a narrow entrypoint patch based on `HEAD` that imports the helper and `copilot_view`, then inserts the workspace branch. Stage only the Service Level wording needed by the P4 regression from both locale JSON files. Preserve the full current working-tree versions and their unrelated changes. A focused test must exercise the exact index candidate, not merely the mixed working-tree file.

## Risks and validation

- Streamlit may treat a locale key rendered in different branches differently across reruns; verify switching Planning → Copilot → Traditional Chinese → Planning, including pending Planning values and machine `ui_workspace` value.
- The index candidate differs from the mixed working tree by design. Materialize only the staged entrypoint as a temporary local test file, run the focused P4 tests against it, and remove that generated file after validation. Never read USER_DATA or run mixed-data discovery.
- Run explicit synthetic-only P4 focused, Dashboard, contract and integrated groups; run Chromium UAT only against localhost, with network blocked. Verify the staged diff, AST/JSON and secrets before commit. If the isolated candidate cannot pass, do not publish P4.
