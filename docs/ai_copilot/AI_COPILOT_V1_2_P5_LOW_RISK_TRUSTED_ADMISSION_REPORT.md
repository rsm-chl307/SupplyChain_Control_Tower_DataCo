# AI Decision Copilot V1.2 — P5 Low-risk Trusted Admission Report

Date: **2026-11-22 UTC**. **Task 1 verdict: PASS.** Scope: admit only the separately pinned `p5_low_risk_v1` synthetic fixture to the existing local trusted Context → V1.1 Brief → `ValidatedBrief` workflow. No Ledger, Owner Approval, Provider Adapter, production model, paid execution or deployment changes.

## Preflight and traced trust boundary

Repository: `/workspace/SupplyChain_Control_Tower_DataCo`, branch `main`, HEAD `6e451b9660dd3be09e632e10ff8698b39a267b07`. Existing tracked Dashboard/locales/docs/cache edits and untracked V1.1/V1.2/P5 work were identified and preserved. The original development repository is the sole implementation target.

Original lifecycle inspected in `src/synthetic_context.py`, `src/ai_brief/adapter.py`, `workflow.py`, `builder.py`, `validation.py`, `src/ai_copilot/response_contract.py` and `provider.py`:

1. `SyntheticHarness()` reads only its code-fixed `examples/planning/synthetic_demo` files via `_directory` and `_read_at`, compares every input to the unchanged `_APPROVED` SHA-256 map, and runs the existing deterministic pipeline inside a fresh temporary workspace.
2. `_inspect` reopens only that harness's Run, checks manifest identity, configuration, source hashes, artifact names/hashes/row counts and publication state. `issue` signs Run ID, scenario, manifest digest, artifact hashes, expiry and nonce with a harness-local secret; `verify` requires the same registered Context object and live source binding.
3. `snapshot` captures immutable verified bytes. `load_context` issues a `SourceBundle` only from a live `SyntheticHarness`; `build_draft` emits source references; `validate_draft` recomputes the projection from the same bundle and checks all source references before issuing `ValidatedBrief`.
4. P1 `validate_response` checks Brief digest and source-backed numerical slots. P2 `build_request` binds the full local Brief digest, allowlisted provider projection digest, schema/instruction/privacy versions, limits and model string in the canonical Request Digest. The real adapter `execute()` remains blocked.

No arbitrary caller Run path or fixture path is accepted by this route. Brief's visible Run label is a privacy alias; the private snapshot manifest retains the actual temporary Run ID and is bound to the Context. The test was corrected to check these two identities in their proper places.

## Narrow second-fixture admission

`SyntheticHarness(fixture_id='p5_low_risk_v1')` is the only new selector. Unknown IDs, traversal strings and path-like values are rejected **before fixture I/O**. The selector maps to one fixed repository directory. A digest of `MANIFEST.json` is pinned in trusted source, and the manifest must name exactly the nine expected inputs, version `p5-low-risk-v1` and `SYNTHETIC_DEMO`. Every input is read through directory descriptors with `O_NOFOLLOW`, size/regular-file checks and SHA-256 verification. The manifest cannot authorize itself by being edited.

Only the verified bytes are copied into a fresh temporary workspace before the existing Planning runner executes. The resulting Run's configuration and source hashes are checked by the unchanged publication validator. The P5 fixture ID and code-pinned manifest digest are additionally included in the new path's HMAC payload; the original path's signature payload is unchanged. For P5 only, `_inspect` rechecks the registered source manifest and all input bytes before each Context issue, verification and snapshot; post-admission modification fails closed. The Run ID, manifest digest, artifact hashes and scenario remain bound by the original Context and Brief rules.

The original `_FIXTURE` path, `_APPROVED` values, default `SyntheticHarness()` invocation, Context fields, original HMAC payload, Brief schema/validator and deterministic business logic remain unchanged. The new fixture's `MANIFEST.json` digest is `88e3de4a24521c07b4c8cc1bf661fdf72c3310d6ca74719ec066cf45c52cca86`; the original nine-file hash map is checked unchanged in the regression test.

## Security checks and limitations

Focused tests cover valid admission, trusted Context, V1.1 `ValidatedBrief`, two `Healthy` risk records, source-reference resolution, P1 validation of a low-severity response, stable Brief/Request Digests within the same Run, unknown/traversal IDs, modified input/manifest, direct-file and directory symlinks, post-admission source modification, cross-harness and cross-Run rejection, and the original default fixture. A source file is temporarily modified in one negative test and restored in `finally`; its bytes are checked afterward.

The source fixture must remain available and unchanged while a P5 Context is live. Contexts expire after 300 seconds and the harness's explicit `close()` removes its owned temporary workspace; this task did not run a full elapsed-time cleanup test. The same-process trusted-code assumption remains: this mechanism does not defend against a compromised Python process or local administrator. The new fixture path is local-only and does not confer Cloud trust, Owner Approval or a paid allowance.

`cases.v1.json` still contains original EV-08. Admitting the fixture does **not** silently create an approved eight-case corpus or modify the P3 one-allowance Ledger. A versioned corpus and subsequent campaign authorization remain separate Owner decisions.

## Files created and modified

Created `tests/test_p5_low_risk_admission.py` and this report. Modified `src/synthetic_context.py` and `tests/synthetic_only_suite.py` only for explicit admission and test selection. Appended dated status to `tests/fixtures/p5_low_risk_v1/README.md`, package `README.md`, `SYNTHETIC_EVALUATION_CASES.md` and `OWNER_DECISION.md` so historical P5-R limitations remain visible. No other application source, P1/P2/P3 module or fixture bytes/hashes were changed.

## Validation results

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_admission`: **5 passed, 0 failures, 0 errors, 0 skipped** in **18.768 seconds** after correcting a test-only Run-alias expectation. Initial run was 4 passed / 1 failed because the test expected the private Run ID in the public alias field; no production code changed for that correction.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite lifecycle`: **34 passed, 0 failures, 0 errors, 0 skipped** in **29.719 seconds**; existing V1.1 Context/lifecycle regression.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_offline`: **26 passed, 0 failures, 0 errors, 0 skipped** in **126.288 seconds**; includes existing P5 cases and P1/P2/V1.1 workflow contracts.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_low_risk`: **1 passed, 0 failures, 0 errors, 0 skipped** in **0.417 seconds**; independently pinned fixture regression.
- Offline AST and SHA-256 check: **PASS**, three Python files parse and all nine P5 fixture bytes match the unchanged local manifest. The focused test also confirmed every original V1.1 `_APPROVED` hash still matches its file.
- `git diff --check`: **PASS**, exit 0. New untracked source/docs/tests were separately checked for syntax and whitespace.

Only explicit synthetic-only runner groups were used. No USER_DATA fixture was opened, parsed or processed. No external network/API request, OpenAI SDK client, API key, real provider dispatch, API charge, commit, push or deployment occurred.

## Task 2 readiness

Task 1 security boundary is suitable for **read-only Task 2 Ledger specification**: focused and relevant regressions passed, and remaining limitations do not affect TrustedBrief integrity, Request Digest binding, Owner Approval or Ledger security. The remaining corpus-version and paid-policy decisions do not block design-only review; they must be explicit implementation prerequisites. Task 1 validation and this report were completed before Task 2 began.
