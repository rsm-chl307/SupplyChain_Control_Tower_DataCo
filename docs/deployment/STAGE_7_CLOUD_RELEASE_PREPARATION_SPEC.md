# Stage 7 — Cloud release preparation specification

Date: 2026-11-26. Stage 7 prepares, validates and preserves a reproducible Streamlit Community Cloud Release Candidate. It does not deploy, push, access Cloud Secrets, or call OpenAI.

## Baseline and product boundary

The source repository starts on `main` at `be425671b27918788dfcec0d39b2d221158cfef7` with 35 modified tracked, 182 untracked and zero staged entries. The existing Streamlit entrypoint is `dashboard/scenario_planning_app.py`; Planning Engine/WP1/WP2 remain the calculation authority. Stage 4–6 AI is an optional explanation layer, defaults to Fake, and requires backend authorization. The existing P5 `REAL_PROVIDER_DISPATCH_LOCKED=True` remains unchanged.

The former 75-file list is correctly blocked because it includes the P5 campaign, `provider.py` with `execute_authorized()`, and Windows Runner code. The Cloud package must exclude those and all Ledger, Archive and local execution modules. Shared safe provider request/response construction may be factored into a Cloud-safe module, preserving the original P5 interface and behavior. The local Owner gate remains available only in the development source; its implementation module is absent from the Cloud package. No P5 authorization semantics are changed.

## Source, data and security contract

An explicit, pinned allowlist contains the entrypoint, direct Python imports, fixed reviewed business definitions, synthetic fixture/CSV templates, locales/guide, `.streamlit/config.toml`, `.gitignore` and `requirements.txt`. It excludes raw/processed datasets, `tmp`, tests, Windows tools, P5 paid modules, `.env`, `secrets.toml`, caches and symlinks. The builder rejects path traversal, unexpected allowlist changes, missing imports or banned execution content before writing output. It emits a deterministic per-file SHA-256 manifest inside a fresh output directory; source files are copied byte-for-byte. The manifest and output are inspection artifacts, not authorization to deploy.

The Cloud package retains Stage 5 password/rate/budget/Context controls, Stage 6 disabled-by-default Cloud Provider selection and P1 validation. No API key is packaged. The public non-AI app must start without AI Secrets. The approved synthetic data is small and read-only; generated Runs use temporary session storage with no persistence guarantee.

## Work packages and acceptance

1. **7.1 source boundary:** isolate shared safe provider contract, select only Cloud-required paths, validate imports and produce a hash manifest.
2. **7.2 P5 preservation:** keep the original P5 dispatch lock, original P5 tests and local execution semantics; prove paid/local modules absent in the package.
3. **7.3 Python 3.12:** inspect pinned dependency metadata and run actual 3.12 install/start/tests only if an isolated interpreter is available. Python 3.10 tests or syntax checks do not establish 3.12 acceptance.
4. **7.4 runtime:** import and run the packaged Streamlit app with Fake/no-key settings; verify fixture, documents, paths, Planning and AI preview.
5. **7.5 security/data:** scan the package for secret patterns, unexpected paths, symlinks and source-content guards; retain synthetic-only data.
6. **7.6 candidate:** preserve a fresh local package and deterministic manifest, record checks/tests and exact reproducible build command. No push or deployment.

Required tests: targeted builder/package/import/security tests after each change; P5 provider/approval/ledger regressions after provider extraction; Stage 4–6 AI and Planning/WP1/WP2/Scenario regressions; `git diff --check`. Official [Streamlit dependency guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) and [Python selection guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) were checked 2026-11-26. Community Cloud defaults to Python 3.12, but this environment has only Python 3.10; actual 3.12 qualification must be reported separately if unavailable.

Stage 8 deployment, Stage 9 paid AI, Cloud Secrets, Git push/commit, P5 security-policy changes, business-rule changes and external infrastructure are out of scope. Any required change to P5 authorization meaning or frozen planning logic stops the affected work for Owner review.
