# P5 offline evaluation package — GPT-6 Luna first candidate

Version: `p5-offline-evaluation-1` (2026-11-21 UTC). This package prepares a **synthetic, offline** quality evaluation. The Owner selected **GPT-6 Luna** as the first candidate; its API model ID, dated snapshot, account entitlement, strict JSON Schema support, price and actual performance have **not** been verified in this repository. Do not substitute another model automatically. If this candidate fails the rubric, record the exact deficiency and return to the Owner.

## What is executable now

`cases.v1.json` contains eight versioned case definitions. The case test obtains a fresh trusted Context from `src/synthetic_context.py::SyntheticHarness`, builds a live V1.1 `ValidatedBrief` through `prepare_brief`, checks canonical serialization and exact source values with `resolve_source`, and validates an offline response with the actual P1 validator. It uses the pinned `examples/planning/synthetic_demo` fixture only. The JSON file is **not** a substitute for a live validator-issued Brief or an authorization token.

Run from the development repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_offline
git diff --check
```

The runner names only the new case module and relevant P1/P2/V1.1 tests, blocks USER_DATA-like paths and socket connections, and permits only `SYNTHETIC_DEMO` Planning fixture preparation. Do not run broad test discovery. No OpenAI SDK, key, network endpoint, paid dispatch or model execution is involved.

## Reproducibility boundary

Within one live `SyntheticHarness`, identical scenario, record bound and explicit comparison selection produce byte-identical canonical Briefs and digests; the test checks this. A new harness creates a new temporary Run identity and timestamps, so a new session's **full Brief digest may differ** even though the pinned business evidence and source-reference selection are reproducible. A future paired evaluation must capture and use the same live validated Brief and exact Request Digest for each authorized submission. Context expiry and approval expiry must be checked again before any future dispatch.

The eight cases cover capacity, demand surge, disruption, inventory, service, priority/comparison trade-offs, missing root-cause evidence and avoiding a false lost-sales escalation. The pinned fixture has **no complete low-risk scenario** in its validated risk summary; EV-08 is a low-risk *signal* inside an otherwise At Risk scenario. This limits conclusions about over-escalation in genuinely low-risk scenarios. Do not synthesize an untrusted low-risk Brief or change fixture hashes to hide the gap. A new trusted fixture would require separate review.

## Package map

- `MODEL_COMPATIBILITY.md`: code-proven interface and unverified GPT-6 Luna capabilities.
- `SYNTHETIC_EVALUATION_CASES.md` and `cases.v1.json`: case intent, expected evidence and forbidden claims.
- `EVALUATION_RUBRIC.md`: scoring and critical failures.
- `PAID_ACCEPTANCE_TEST_PLAN.md`: future procedure only; not executable authorization.
- `OWNER_DECISION.md`: pending gates and decisions.

P5 paid acceptance and P6 deployment remain **NOT AUTHORIZED**. The real adapter's `execute()` remains blocked.

## P5-R / P5-C extension — 2026-11-22

The Owner now requires a **full eight-invocation evaluation** with GPT-6 Luna first and local-first operation. See `EIGHT_CASE_REVIEWER_WORKSHEET.md` and `P5_C_BUDGET_AND_AUTHORIZATION_PROPOSAL.md`. An independent `tests/fixtures/p5_low_risk_v1/` fixture produces a genuinely `Healthy` Baseline using the deterministic pipeline; `python3 -B -m tests.synthetic_only_suite p5_low_risk` verifies its pinned bytes and output. It is **not yet admitted** to the existing V1.1 trusted Context issuer. The original eight-case `cases.v1.json` and pinned V1.1 fixture remain unchanged. Proposed EV-08-LR cannot enter paid acceptance until the Owner approves a reviewed second-fixture trust pathway and corpus revision.

### Trusted admission status — 2026-11-22

The explicit `SyntheticHarness(fixture_id='p5_low_risk_v1')` pathway now issues a trusted Context, V1.1 `ValidatedBrief` and offline Request Digest. Run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_admission` for its synthetic-only security checks. The paragraph above is retained as historical P5-R state. `cases.v1.json` still contains original EV-08; a versioned eight-case corpus, Ledger allowances and paid execution remain separate pending decisions.

## P5-D offline quality package — 2026-11-22

The historical sections above remain for provenance. `cases.v2.json` is the **proposed**, code-pinned eight-case corpus: EV-01–07 preserve v1 expectations and EV-08-LR uses the admitted genuine Low-risk fixture. `AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md` defines a separate proposed six-dimension 1–5 human rubric; it does not reinterpret the historical 0–4 rubric. `src/ai_copilot/quality_evaluation.py` performs deterministic P1-gated provenance checks, score arithmetic and aggregation. The updated `EIGHT_CASE_REVIEWER_WORKSHEET.md` is ready for two independent humans and adjudication. `P5_PAID_ACCEPTANCE_READINESS.md` records current official documentation, rough costs, privacy projection and concrete paid blockers. Owner approval of corpus and scoring policy is pending.

Run only explicit synthetic-only groups from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_quality
PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_offline
PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite integrated
git diff --check
```

The `p5_quality` group verifies every v2 evidence reference against live trusted Briefs and checks missing/invalid human inputs, Critical Failures and reproducible scores. No model is invoked. The new v2 corpus is not yet a paid authorization token. Current eight-call Ledger mode remains `OFFLINE_TEST`; the OpenAI adapter remains blocked.
