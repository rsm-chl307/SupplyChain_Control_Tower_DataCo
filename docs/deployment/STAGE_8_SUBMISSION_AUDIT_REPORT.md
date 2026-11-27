# Stage 8 submission audit

Date: 2026-11-26. Objective: review and publish only the Owner-authorized WP8.1–WP8.5 changes after reproducible Python 3.12 checks. Scope excludes Cloud deployment, production Secrets, real AI and P5/Windows historical publication. Review baseline was `main` = fetched `origin/main` = `a11f98469cbec7ef7d6439f4c8888c38d2773588`.

## Scope and dependency review

Stage 8 exact paths: `.gitignore`; `requirements-test.txt`; `tests/test_stage8_local_runtime.py`; `tests/test_phase2_workflow.py`; `tests/test_dashboard_app.py`; `tests/test_comparison_dashboard.py`; `docs/deployment/STAGE_7_STAGE_8_BASELINE_AND_BOUNDARY_REPORT.md`; `docs/deployment/STAGE_8_IMPLEMENTATION_PROGRESS.md`; `docs/deployment/STAGE_8_PYTHON_312_QUALIFICATION_REPORT.md`; `docs/deployment/STAGE_8_TEST_AND_RUNTIME_VERIFICATION_REPORT.md`; `docs/deployment/STAGE_8_RELEASE_CANDIDATE_READINESS_REPORT.md`; this audit report. All other modified and untracked user paths are excluded.

The Stage 8 package test requires the Stage 7 `scripts/build_streamlit_demo_source.py` and `docs/deployment/STREAMLIT_CLOUD_ALLOWLIST.txt`. Their standalone 74-file builder smoke test passes from a clean HEAD archive. They are reviewed as a separate Stage 7 preparation commit, with formal Stage 7 acceptance remaining **NOT ACCEPTED — REMEDIATION REQUIRED**. The Stage 7 P5 lock regression depends on preserved uncommitted historical P5 code; it is not part of either Stage 8 commit.

The Stage 8 source changes are limited to `.venv312/` Git exclusion, a pinned test-only Markdown dependency, a Cloud runtime package test, and UI/Planning test fixtures that generate their own synthetic Runs in allowed temporary locations. `tests/test_phase2_workflow.py` also contains previously local UI compatibility assertions needed for the committed app behavior; the complete file is reviewed and tested from clean source. No Planning formula, priority, allocation, KPI, scenario rule or real provider dispatch changed.

## Review gates

| Gate | Evidence | Result |
| --- | --- | --- |
| Dependencies | Runtime pins in `requirements.txt` unchanged; `requirements-test.txt` pins `markdown-it-py==4.0.0`; `.venv312/bin/python -m pip check` | PASS |
| Exclusions | `git check-ignore -v .venv312/bin/python tmp/planning_source_runs/example`; builder list excludes tmp, local P5, Secrets and virtual environment | PASS |
| Sensitive data | Exact staged paths and 74-file candidate reviewed for key/token/private-key values; no credential value found | PASS |
| Source quality | `git diff --cached --check`, complete staged diff, Python 3.12 unit/integration tests and clean-source run | PASS |
| Real AI lock | Working tree `REAL_PROVIDER_DISPATCH_LOCKED = True`; packaged source excludes `provider.py` and paid modules | PASS locally; Stage 7 repository acceptance separate |
| Cloud deployment | No deployment, public browser test or production Secret access | NOT EXECUTED |

## Tests and reproducibility

Commands and full WP8.1–WP8.5 evidence are in `STAGE_8_TEST_AND_RUNTIME_VERIFICATION_REPORT.md`. Push-audit reruns: `.venv312/bin/python -B -m unittest tests.test_stage8_local_runtime tests.test_stage7_cloud_release` — 5 passed, 0 failed, 0 skipped in the local worktree (the Stage 7 test remains uncommitted); `.venv312/bin/python -B -m unittest tests.test_phase2_workflow` — 10 passed, 0 failed, 0 skipped; `.venv312/bin/python -m pip check` — pass. A clean `git archive HEAD` plus only the exact Stage 7 builder/allowlist and Stage 8 test files ran `/workspace/SupplyChain_Control_Tower_DataCo/.venv312/bin/python -B -m unittest tests.test_stage8_local_runtime tests.test_dashboard_app tests.test_comparison_dashboard tests.test_phase2_workflow` — **28 passed, 0 failed, 0 skipped**. Counts overlap. The 28-test command is reproducible from the intended two-commit source without developer-local artifacts.

The local Python 3.12 candidate has 74 allowlisted files plus one deterministic manifest. Two builds match with manifest SHA-256 `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`; candidate-a passed packaged AppTest/Planning and local HTTP health. The manifest includes working-tree `.gitignore`, so a committed-source candidate should be rebuilt and compared before calling it GitHub-synchronized.

## Publication record

Stage 7 preparation dependency committed separately as `97f69bae06901476c5e50a24f78dee52b3a46159`; push to `origin/main` succeeded, then `git fetch origin main` confirmed remote SHA `97f69bae06901476c5e50a24f78dee52b3a46159`. Stage 7 formal acceptance remains NOT ACCEPTED. A clean committed-source copy with the local Stage 7 test module added ran 4 tests: 3 passed, 0 assertion failures, 1 error (`REAL_PROVIDER_DISPATCH_LOCKED` absent from committed `provider.py`). This confirms the formal 7.2 blocker independently of the passing local-worktree suite.

The exact 12-path Stage 8 index snapshot ran 28 tests: 28 passed, 0 failed, 0 skipped. Rebuilding its 74-file package produced manifest SHA-256 `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`, byte-identical to the two earlier candidate builds. `git diff --cached --check` passed; the complete staged diff and a targeted credential/private-key pattern scan showed no unrelated file or sensitive value.

Stage 8 implementation commit `b9f1d89f7789b5ebe20caef3a6e2bfc1f0f807c0` contains the 12 exact Stage 8 paths above. `git push origin main` succeeded (`97f69ba..b9f1d89`), followed by `git fetch origin main`; fetched `origin/main` and local HEAD both resolved to `b9f1d89f7789b5ebe20caef3a6e2bfc1f0f807c0`. Rebuilding from a clean `git archive` of that committed SHA reproduced the same 74-file manifest SHA-256. The source candidate is therefore GitHub-synchronized at this SHA and locally Python 3.12 validated. It is **not deployed** or Cloud runtime accepted.

Stage 7 acceptance evidence was subsequently supplemented in a separate Stage 7-only commit `8b5182230eeba8dd8650ca1b3e046798427c2046` (clean-source 3 passed, 1 error); push and fetch succeeded. This does not alter the Stage 8 candidate source files or the Stage 7 **NOT ACCEPTED — REMEDIATION REQUIRED** conclusion. This audit evidence update is a Stage 8 documentation-only follow-up commit; its final SHA is reported in the terminal summary after push/fetch because a commit cannot contain its own SHA.
