# Stage 8 — local Release Candidate readiness

Date: 2026-11-26. Objective: identify a reproducible, Python 3.12-tested Cloud source candidate without deploying it. The table below records the original local preparation state; subsequent authorized Git publication and its fetched remote SHA are recorded in `STAGE_8_SUBMISSION_AUDIT_REPORT.md`. Production Secrets and real AI activation remain excluded.

| State | Result | Evidence and boundary |
| --- | --- | --- |
| Local development state | **In progress** | `main` HEAD/fetched `origin/main` = `a11f98469cbec7ef7d6439f4c8888c38d2773588`; unrelated local changes remain. `.gitignore` is modified for `.venv312/`; the Stage 7 builder/allowlist and Stage 8 tests/reports remain untracked. |
| Local Python 3.12 Release Candidate | **Prepared and locally validated** | `/tmp/sct-stage8-312-rc-f7by6htu/candidate-a`; Python 3.12.16 in `.venv312`; 74 allowlisted files plus manifest; root runtime pins installed and `pip check` passed. |
| Independent build comparison | **PASS** | `/tmp/sct-stage8-312-rc-f7by6htu/candidate-b` has identical paths, file count, file hashes and byte-identical manifest. Manifest SHA-256 `32532c482792680d7df01bac24a36c8d10a76406dabb978a0c8f9797f7596252`. Source files are copied byte-for-byte; no timestamp-dependent metadata is in the manifest. |
| Isolated execution | **PASS locally** | Packaged 3.12 AppTest and synthetic Planning produced 13 output paths without AI key; local Streamlit health returned HTTP 200. Planning, UI, Dashboard/WP2 and security regressions passed as recorded in the test report. |
| Source/data/security inventory | **PASS for inspected candidate** | Exact pinned list, 74 hash matches, no unlisted files or symlinks, no `.venv312`, `tmp`, raw/processed data, local paid provider/Windows tools, Secret file or targeted credential pattern. |
| GitHub-synchronized Release Candidate | **No** | This is a working-tree candidate: `.gitignore` differs from HEAD and the builder/allowlist are not committed. No Stage 8 commit or push was authorized. |
| Actually deployed / Cloud runtime verified | **No** | No Streamlit Community Cloud deployment, deployment logs, deployed SHA, sharing check or public browser UAT. |
| Owner accepted / Stage 7 accepted | **No / No** | Stage 7 and Stage 8 acceptance require their own reviews. |

The local source manifest is deterministic. The 39-package `.venv312` test environment is recorded in `/tmp/sct-stage8-312-rc-f7by6htu/python312-test-environment-freeze.txt` (SHA-256 `f49a7860f0dc3cca4f518b0ef00353b21679f937ceca5a8f488ae408f641cf9c`). The five direct runtime dependencies are pinned; transitive dependencies are not locked in the repository, so future fresh installs may resolve different transitive versions. This is an environment reproducibility limitation, not a failing local test.

Rebuild from the repository root with `.venv312/bin/python -B scripts/build_streamlit_demo_source.py /tmp/NEW-UNUSED-DIRECTORY` and verify every manifest hash, the current source SHA and working-tree differences. The output path must not already exist. This local `/tmp` candidate is an inspection artifact and may not survive a Container restart.

**Local RC readiness: PASS WITH LIMITATIONS. Cloud deployment readiness: PENDING AUTHORIZATION AND LIVE EVIDENCE.** No product/business rule or P5 dispatch lock changed. The historical Executive Dashboard needs excluded reference data; the synthetic Planning, scenario, risk and WP1/WP2 paths were locally tested. Actual Cloud platform behavior and public accessibility remain unknown until authorized deployment.

Files created/modified for this assessment are listed in `STAGE_8_IMPLEMENTATION_PROGRESS.md`; tests and exact commands are in `STAGE_8_TEST_AND_RUNTIME_VERIFICATION_REPORT.md`. Next: review the local diff and package, then request separate authorization for any Git publication or Cloud deployment.
