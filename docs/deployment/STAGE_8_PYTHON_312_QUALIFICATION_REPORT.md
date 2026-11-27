# Stage 8 — Python 3.12 qualification

Date: 2026-11-26. Objective: qualify the local Cloud candidate under Python 3.12 while preserving the default Python 3.10.20 environment. Scope is this Debian 13 Dev Container and local `.venv312`; no Cloud deployment, production Secret or real AI call.

## Preflight and installation choice

| Item | Observed value |
| --- | --- |
| Repository / branch / HEAD | `/workspace/SupplyChain_Control_Tower_DataCo`; `main`; `a11f98469cbec7ef7d6439f4c8888c38d2773588` (fetched `origin/main` matched) |
| OS / architecture / account | Debian GNU/Linux 13 (trixie), x86_64, root inside the existing Dev Container |
| Container context | VS Code Dev Containers IPC variables are present; no container rebuild or Docker Desktop change |
| Default Python | `/usr/local/bin/python`, Python 3.10.20; pip 26.0.1; 202 installed distributions at preflight |
| Available space | `/workspace` and `/tmp` on overlay, about 869 GB free at preflight |
| Existing virtual environments | Neither `.venv` nor `.venv312` existed |
| Python 3.12 discovery | Existing uv-managed CPython 3.12.16 at `/root/.local/share/uv/python/cpython-3.12.16-linux-x86_64-gnu/bin/python3.12`; 3.12 was installed in this Container but absent from the default PATH |

`apt-get update` succeeded against the existing official Debian trixie, updates and security repositories. `apt-cache policy/search` found no `python3.12` or `python3.12-venv` package; Debian's installed `/usr/bin/python3` is 3.13. The discovered uv-managed 3.12.16 interpreter passed `venv`, `ensurepip` and SSL imports. Reusing that existing versioned installation avoided an unsupported Ubuntu PPA, arbitrary install script, source compilation and any default-Python change. Its provenance is an existing managed distribution; no new system interpreter was installed during this task.

## Environment creation and package installation

Commands run:

```bash
/root/.local/share/uv/python/cpython-3.12.16-linux-x86_64-gnu/bin/python3.12 -m venv .venv312
.venv312/bin/python -m pip install -r requirements.txt
.venv312/bin/python -m pip install -r requirements-test.txt
.venv312/bin/python -m pip check
```

The first sandboxed pip attempt failed because DNS to PyPI was blocked. The same approved command outside the sandbox installed all five root pins plus their transitive dependencies into `.venv312`; no system Python package was changed. The previous offline Plotly failure was cache/network availability, not an observed 3.12 incompatibility: `plotly==6.5.2` installed successfully. `markdown-it-py==4.0.0` was added in a separate test-only manifest because the existing UI content test imports `markdown_it`; it is excluded from the Cloud runtime allowlist.

Verified in `.venv312`: Python 3.12.16, pip 26.3, Streamlit 1.56.0, Pandas 2.3.3, NumPy 2.2.6, Plotly 6.5.2, jsonschema 4.26.0; `pip check` PASS. Native/package imports of NumPy, Pandas, Plotly, jsonschema, PyArrow and Streamlit PASS. `.gitignore` now excludes `.venv312/`; `git check-ignore -v .venv312/bin/python` confirms the rule. Default `/usr/local/bin/python` and `/usr/local/bin/python3.10` still report 3.10.20 and the original pip 26.0.1.

The 39-package local test environment snapshot is `/tmp/sct-stage8-312-rc-f7by6htu/python312-test-environment-freeze.txt`, SHA-256 `f49a7860f0dc3cca4f518b0ef00353b21679f937ceca5a8f488ae408f641cf9c`. It is outside the Cloud candidate and contains the test-only parser. Root requirements pin the five direct dependencies, but transitive versions are not locked in the repository; a later clean install can resolve newer transitive releases. The snapshot records this run rather than changing the approved runtime pins.

## Recreation

In this same Container, use the explicit managed 3.12 path above to create `.venv312` only if it does not already exist. Install `requirements.txt`, then `requirements-test.txt` for local tests. Use `.venv312/bin/python` for all 3.12 commands; do not change the shell's default `python`. The managed base path is local to this Container and may not exist in another environment; on another host, install a trusted CPython 3.12 distribution first. Do not copy `.venv312` to Git or Cloud source.

## Qualification result and limits

**Local Python 3.12 qualification: PASS for the inspected candidate and tests.** The Stage 8 test report records package startup, Planning, dashboard, scenario, security and release-candidate checks. This is not an assertion that Streamlit Community Cloud has the same OS, transitive dependency resolution, network or browser behavior. No clean second 3.12 virtual environment was created because the Owner requested one project environment; the package was executed from isolated source directories using `.venv312`.

Stage 7 remains an independent, unaccepted track. This evidence addresses its former Python 3.12 gap technically, but Stage 7 requires its own candidate reconciliation and formal acceptance review. No Stage 7 acceptance status was changed.

Files created/modified for this work: `.venv312/` (ignored local environment), `requirements-test.txt` (test-only), `.gitignore`; supporting Stage 8 tests and reports are listed in the implementation report. No Git commit or push occurred. Next: review candidate and dependency evidence before separate Cloud deployment authorization.
