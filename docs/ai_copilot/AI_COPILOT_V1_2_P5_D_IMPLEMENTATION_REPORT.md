# AI Decision Copilot V1.2 — P5-D Offline Quality Evaluation Implementation

Date: 2026-11-22 UTC. **P5-D result: PASS WITH LIMITATIONS. Offline evaluation framework: PASS. P5 Paid Acceptance readiness: NOT READY.** GPT-6 Luna (`gpt-6-luna`) remains the sole Owner-selected candidate. No model outputs or actual provider charges exist. The new weights and thresholds are proposed for Owner review, not approved adoption criteria.

## Inspect, plan and implementation

Preflight: `/workspace/SupplyChain_Control_Tower_DataCo`, branch `main`, HEAD `6e451b9660dd3be09e632e10ff8698b39a267b07`; pre-existing tracked Dashboard/locales/docs/cache edits and untracked V1.1/V1.2/P5 work preserved. Inspected `cases.v1.json`, the historical rubric and worksheet, P1 `response_contract.py`, the request builder/privacy projection, the eight-call Ledger and tests, P5-A/B/P5-R/P5-C documents, and the genuine Low-risk trusted fixture path. The original v1 corpus had old EV-08, which is not genuinely Low-risk. The P3/P1/P2/V1.1 modules and blocked provider adapter were not changed.

The [P5-D plan](p5_offline_evaluation/P5_D_IMPLEMENTATION_PLAN.md) was written before source changes. Created versioned `cases.v2.json`: EV-01–07 preserve their v1 facts and refs, and EV-08-LR is based on trusted `p5_low_risk_v1` Baseline. The new corpus SHA-256 is `08a34585b1cb819c82093adb4828734cb05507ea6b6cd6448efc5cc0d819ff50`, pinned in the evaluator. Corpus tests resolve all eight case expectations against fresh live trusted Briefs; a caller-edited case or changed corpus bytes is rejected. Original v1 and fixture bytes/hashes remain unchanged. The v2 corpus still needs explicit Owner approval for paid use.

`src/ai_copilot/quality_evaluation.py` adds bounded provenance records (campaign/corpus/case, Brief/projection/Request/response digests, model and policy versions, limits), the P1 technical gate, exact source-ref checks, locally retained raw response bytes, independent reviewer records, Critical Failure flags, adjudication and Decimal weighted scoring. It has no model call, provider dispatch, cost approval or business KPI calculation. It produces stable machine-readable JSON summaries without copying the raw response body into that summary. Human semantic review remains mandatory; the module never grades prose by itself. `tests/synthetic_only_suite.py` now explicitly names `p5_quality` and includes it in the integrated selection.

## Proposed scoring and case coverage

The separate [quality specification](p5_offline_evaluation/AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md) proposes Factual Accuracy **25%**, Root Cause Analysis **20%**, Recommendation Quality **20%**, Decision Trade-off **15%**, Context & Risk Awareness **10%**, Communication Quality **10%**. Each human score is an integer 1–5 with a rationale; `Σ(weight × score/5)` gives 20–100. No N/A or default score. Two independent reviewers and a distinct adjudicator are required. A missing score, rationale, P1 result, case record or adjudication is INCOMPLETE, never PASS. The historical 0–4 rubric remains unchanged.

| Case | Verified synthetic evidence | Quality focus |
|---|---|---|
| EV-01 | Baseline `s7`: utilization `1.0`, bottleneck count `3` | Capacity fact versus unproven cause. |
| EV-02 | Demand_Surge `s8/s11`: unmet workload `11.6`, backlog `7.300000000000001` | Scenario pressure without universal causality claim. |
| EV-03 | Capacity_Disruption `s7/s9`: capacity `9.6`, fulfillment `0.4461538461538462` | No invented supplier/recovery cause. |
| EV-04 | Combined_Stress `s11`: backlog `8.5`, inventory `0.0` | Native-grain coverage and no whole-network overclaim. |
| EV-05 | Comparison `s27`: horizon service `0.5384615384615384` → `0.4895104895104895` | Comparable cohort and Legacy distinction. |
| EV-06 | `s22/s24/s28`: priority `1/3`, cohort service `0.875` → `0.7954545454545454` | Conditional product trade-offs; fixed priority. |
| EV-07 | `s13/s9`: At Risk with lost sales `0.0` | Explicit missing root-cause evidence and uncertainty. |
| EV-08-LR | `s22/s24` Healthy, `s14` fulfillment `1.0`, `s18` inventory `27.0`, selected zero backlog/lost sales | No fabricated shortage or urgent escalation. |

These are existing fixture/Brief facts, not recalculated KPIs. Full expected interpretations, conditional recommendations, forbidden conclusions and case-specific gates appear in `cases.v2.json` and the quality specification. [The worksheet](p5_offline_evaluation/EIGHT_CASE_REVIEWER_WORKSHEET.md) now has a complete eight-row register and per-reviewer/adjudicator forms.

Proposed case PASS requires P1 VALIDATED, every expected material ref cited, no confirmed Critical Failure, explicit case requirements met, factual score ≥4, all dimensions ≥3 and weighted score ≥80. Proposed campaign PASS requires eight complete case PASS results, no Critical Failure and mean ≥85. Complete borderline records may be PASS WITH LIMITATIONS under the documented 75/80 floors; one FAIL or Critical Failure makes the campaign FAIL. Incomplete/unknown outcomes never become PASS. All numerical thresholds require Owner approval and are not business risk thresholds.

Critical Failure categories cover fabricated numbers/refs, deterministic contradictions, unsupported facts or confirmed causes, prohibited action, material limitation omission, wrong Run/Scenario and Low-risk false escalation. P1 rejects structural/evidence errors automatically; human reviewers decide semantic failures. A confirmed Critical Failure overrides any score. The adjudicator records a reason for dismissing a reviewer flag; the machine-readable export retains the final dimension scores and rationales.

## Tests and self-review

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_quality`: **11 passed, 0 failed, 0 errors, 0 skipped** in **81.667 seconds** on the final files. Covers six dimensions, score bounds, missing/invalid scores, exact arithmetic, case/campaign thresholds, critical override, low-risk restraint, missing expected evidence, P1 unsupported prose quantity, reviewer disagreement, provenance mismatch, corpus tampering, all eight live Brief evidence references and deterministic JSON aggregation.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite p5_offline`: **26 passed, 0 failed/errors/skipped** in **122.945 seconds**; existing P5/P1/P2/V1.1 synthetic offline regression.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tests.synthetic_only_suite integrated`: **192 passed, 0 failed, 0 errors, 0 skipped** in **506.481 seconds**. Selection contains P5 quality, P5 eight-call Ledger, P5 trusted admission, P1/P2/P3, P4 synthetic UI/Dashboard and relevant V1.1 tests. Streamlit emitted existing bare-mode/deprecation warnings; they did not fail tests. No unrestricted suite was used.
- Final AST/JSON, whitespace and `git diff --check`: **PASS**, with direct checks on untracked files; see final validation below.

Self-review identified and corrected four quality-record risks before final regression: missing adjudicated dimension rationale in export, possible aggregate PASS from incomplete reviewer records, caller-modified case expectations, and a caller-edited case verdict that could contradict its scored dimensions. The evaluator now preserves final scores/rationales, validates aggregate records, and pins exact v2 corpus bytes. The raw response remains local; no LLM self-score is accepted as independent review.

## Paid readiness, official documentation and limits

The [P5 Paid Acceptance Readiness Package](p5_offline_evaluation/P5_PAID_ACCEPTANCE_READINESS.md) checked official OpenAI documentation on 2026-11-22. The model page confirms ID `gpt-6-luna`, Responses and Structured Outputs support, 1,050,000 context and 128,000 max output tokens. The current P1 wire schema's `minLength`/`maxLength` are absent from the official supported strict-schema property list; exact live compatibility is not verified. Current request builder caps output at 2,500 tokens, while reasoning can consume output tokens before visible JSON. The SDK is not installed, account entitlement and actual errors/latency are unverified, and the eight-call Ledger is strictly `OFFLINE_TEST`; the adapter remains blocked. These are concrete blockers to paid calls, not optional polish. No paid path was implemented under this authorization.

Current official Standard rates used for a **proposal** are $0.10/M input, $0.01/M cached input, $0.125/M cache write and $0.50/M output. The eight-case stress estimate is **$0.1108** based on rough byte-derived input proxies and a proposed 25,000 generated-token cap per call; suggested ceilings remain **$0.02 per call / $0.16 aggregate**, with $0.0492 contingency. These are not actual token counts, approved budget settings or observed charges. Official documentation read-only access occurred; no provider/API endpoint was contacted.

The outbound projection retains synthetic business evidence, aliases, source refs and metadata while excluding raw CSVs, private Run path/ID and local provenance hashes. Exact live Brief/Request Digests vary with the trusted Run and need separate Owner inspection. `store=false` does not establish zero retention; default API abuse-monitoring and application-state rules need account-specific review. No USER_DATA was used.

## Final validation

The v2 corpus SHA-256 matched the pinned value; all eight cases were present in the expected order. Three new/modified Python files parsed successfully in the offline AST check. The new documents, JSON, Python sources and tests were checked directly for final newlines and trailing whitespace because this V1.2 work was initially untracked. `git diff --check` exited 0. At test completion, pre-existing dirty and untracked user work remained preserved; no destructive Git operation occurred.

## Files and next decision

Created `docs/ai_copilot/p5_offline_evaluation/{P5_D_IMPLEMENTATION_PLAN.md,AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md,cases.v2.json,P5_PAID_ACCEPTANCE_READINESS.md}`, `src/ai_copilot/quality_evaluation.py`, `tests/{test_p5_quality_evaluation.py,test_p5_quality_corpus.py}`, and this report. Modified only package `README.md`, `EIGHT_CASE_REVIEWER_WORKSHEET.md` and `tests/synthetic_only_suite.py`. Existing user changes, deterministic business logic, P1/P2/P3/P4 code, offline Ledger, deployment repository and production settings were preserved.

Owner must review/approve the v2 corpus, new six-dimension policy, reviewer/adjudicator process, model alias/snapshot, output/input/reasoning/timeout policy, retention consent, exact payload and pricing/budget. Paid execution additionally needs separately authorized resolution of strict wire-schema compatibility, output cap, SDK/runtime, account access and a paid Ledger/dispatch gate. Therefore **P5 Paid Acceptance is NOT READY and NOT AUTHORIZED** despite a tested offline scoring framework. No real GPT-6 Luna calls, API key access, SDK installation, paid allowance, charge or deployment occurred. Stop for Owner review.

## Subsequent Owner-authorized Git record

The Owner subsequently authorized a scope-limited Git commit and push. Before staging, the branch was `main`, its upstream was `origin/main`, and local ahead/behind counts were `0/0`. All modified and untracked paths were inventoried. Dashboard, localization, unrelated docs/tests, Python caches and deployment-only files remained excluded. The staged review covered 39 P5-specific files: the offline evaluation package, Eight-Call Ledger and Low-risk admission work, synthetic fixture, explicit test runner and related tests. `git diff --cached --check` passed; a staged-file scan found no excluded path, credential pattern, USER_DATA or runtime database. No force push was used.

Implementation commit **`301a46ba7a94720b8394da7b02bd76f8221567f9`** was pushed to **`origin/main`** at `https://github.com/rsm-chl307/SupplyChain_Control_Tower_DataCo.git`. `git ls-remote origin refs/heads/main` independently returned that exact SHA, and local `HEAD` matched `origin/main` immediately afterward. This report is the documentation follow-up to that verified push. Earlier V1.1/P1–P4 source and Dashboard changes remain pre-existing, untracked or dirty, and were intentionally excluded. Consequently, the scope-limited P5 commit is **not a self-contained runnable checkout**; it records P5 progress without claiming remote release readiness. Unrelated user work remained untouched.
