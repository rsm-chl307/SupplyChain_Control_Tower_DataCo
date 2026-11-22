# Independent P5 low-risk synthetic fixture

Version: `p5-low-risk-v1`. This directory is separate from `examples/planning/synthetic_demo`; none of the V1.1 pinned fixture files or hashes are changed. `MANIFEST.json` pins every input byte in this directory. The source data is synthetic and uses `SYNTHETIC_DEMO` mode.

The copied synthetic demand/product mapping is preserved; beginning inventory is raised to 20 EA per product and weekly workload capacity to 100 EqWU. This is a deliberately low-pressure test condition, **not** a change to any business calculation. The deterministic runner and `product_risk_ranking` produce two `Healthy` Baseline products with zero terminal backlog/lost sales and full demand fulfillment. The selected test runs only in a fresh temporary directory and checks cleanup.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_low_risk
```

**Trust boundary:** this fixture is pinned for the independent P5 test only. The existing V1.1 `SyntheticHarness` hard-codes the original pinned fixture and cannot issue a trusted Context for this directory. Consequently no valid V1.1 `ValidatedBrief`, P2 Request Digest or paid evaluation approval may be built from these files today. Integrating a second trusted fixture requires a separately reviewed issuer/harness design and tests. Do not monkeypatch the issuer, substitute paths or hand-author a trusted Brief.

## Trusted admission update — 2026-11-22

`SyntheticHarness(fixture_id='p5_low_risk_v1')` now verifies this manifest against a digest pinned in trusted source, checks every listed input hash, and rechecks source bytes before issuing or validating Contexts. The paragraph above records the earlier P5-R state. `SyntheticHarness()` still uses the original V1.1 fixture. This admission does not authorize paid execution or change the eight-case corpus.
