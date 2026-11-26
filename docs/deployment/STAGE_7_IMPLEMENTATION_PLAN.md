# Stage 7 — implementation plan

Date: 2026-11-26. Execute 7.1–7.6 sequentially; test each before continuing.

| WP | Exact intended changes | Targeted validation |
| --- | --- | --- |
| 7.1 | Extract P2-safe request/response and Fake/Mock code from `src/ai_copilot/provider.py` to `provider_base.py`; retain original P5 adapter and lock in `provider.py`. Switch Cloud modules to the safe contract. Move local UI Owner gate into an excluded local module. Replace the blocked allowlist with a minimal Cloud list. | Provider contract parity, package import closure, no P5 runtime paths. |
| 7.2 | Strengthen `scripts/build_streamlit_demo_source.py` to pin the reviewed list, reject banned source paths/content/symlinks and emit deterministic SHA-256 manifest. Keep all existing fail-closed guards. | Tampered allowlist, path escape, P5 code and manifest tests; P5 provider/approval/ledger regression. |
| 7.3 | Inspect Python/requirements metadata; use an isolated 3.12 runtime if present. Do not change unrelated pins or install into the shared environment. | Exact interpreter/install/start evidence, or documented NOT VERIFIED. |
| 7.4 | Build to a fresh `/tmp` directory, import/start the packaged app and exercise public Planning and Fake AI with synthetic credentials. | AppTest, fixed documents/fixture, no-key startup, no network. |
| 7.5 | Inspect the candidate file set and hashes; scan only packaged files for credential patterns and forbidden paths. | Zero forbidden paths/content/Secrets, manifest 100% match. |
| 7.6 | Preserve candidate, run relevant AI/P5/Planning regression, review diff/status and write three Stage 7 reports. | Exact test counts, source SHA, package path, `git diff --check`. |

Intended source edits: `provider.py`, Cloud provider imports, `dashboard/copilot_view.py`, `scripts/build_streamlit_demo_source.py`, the Cloud allowlist and the outdated preparation status. New files: safe provider module, excluded local UI gate, focused builder tests, Stage 7 reports. No Windows Runner, P5 Ledger/Archive, Planning Engine/WP1/WP2 business rule or production configuration change is planned. No commit, push or Cloud deployment.
