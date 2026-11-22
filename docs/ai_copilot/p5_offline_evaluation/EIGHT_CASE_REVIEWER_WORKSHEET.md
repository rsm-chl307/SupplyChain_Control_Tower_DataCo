# Proposed eight-case human reviewer worksheet — P5-R

Version: `p5-review-worksheet-1`; prepared 2026-11-22 UTC. **No model outputs have been scored.** Preserve `cases.v1.json` and the approved P1 validator. The Owner requires a full eight-invocation evaluation. Seven original cases (EV-01–07) remain available through the existing trusted harness. The eighth row below proposes a genuine low-risk replacement for EV-08, but that replacement is **on hold** until the separate fixture is admitted through a reviewed trusted Context pathway. Original EV-08 remains in `cases.v1.json` as a zero-lost-sales signal and is not silently deleted or counted as a genuine low-risk case.

## Review record required for every invocation

Record: case ID and fixture version; selected scenario/comparison scope; local canonical Brief digest; projected Brief digest; exact Request Digest and model identifier/snapshot; schema/instruction/privacy versions; output/timeout policy; Owner approval reference, time and expiry; ledger slot/state; provider status; P1 status; numerical slot checks; input, cached-input, output and reasoning tokens; latency; estimated reservation and observed charge; reviewer identities and timestamps. Store the full response and local provenance under the approved local retention procedure; do not include credentials or USER_DATA.

Before scoring, both reviewers independently confirm: (1) response is completed and P1 `VALIDATED`; (2) every cited source ref resolves in the **same** Brief; (3) each numeric claim is in a validated slot with exact value, unit, grain and cohort; (4) free prose contains no unsupported quantity or action claim. Any refusal, incomplete result, UNKNOWN, unvalidated result or critical failure is **not a scored success**. A human must inspect semantic causality and recommendation usefulness even after P1 passes.

| Slot | Source-backed expected findings | Forbidden or unsupported conclusions | Extra adjudication focus |
|---|---|---|---|
| EV-01 | Baseline `s7`: capacity utilization `1.0` ratio; bottleneck plant-weeks `3`. Recognize published capacity pressure. | Specific plant is sole cause; future unrun weeks remain saturated. | Distinguish deterministic bottleneck fact from AI causal inference. |
| EV-02 | Demand_Surge `s8` unmet workload `11.6` EqWU and `s11` ending backlog `7.300000000000001` EA. Describe scenario pressure. | Demand surge is proven sole cause of every shortage; an unrun action clears backlog. | Check native grain and conditional action wording. |
| EV-03 | Capacity_Disruption `s7` available capacity `9.6` EqWU; `s9` demand fulfillment `0.4461538461538462` ratio. | Invent supplier failure or recovery date. | Separate capacity observation from external-cause hypothesis. |
| EV-04 | Combined_Stress `s11` terminal backlog `8.5` EA and inventory `0.0` EA. | Every product/plant is out of stock; procurement already occurred. | No stock double-counting across weeks or scope overstatement. |
| EV-05 | Explicit Baseline→Demand_Surge comparison `s27`: horizon service `0.5384615384615384` → `0.4895104895104895`, comparable ratio. | Legacy independent-week Service_Level shares the same denominator; future target guaranteed. | Verify reference/candidate order, cohort and metric basis. |
| EV-06 | Same comparison: `s22/s24` priorities `1/3`; `s28` cohort service `0.875` → `0.7954545454545454`. | Model may reorder priority; reallocation guarantees all products improve. | Trade-offs across products and protected deterministic allocation order. |
| EV-07 | Baseline `s13` At Risk while `s9` lost sales `0.0` EA; root-cause evidence unselected. | Zero lost sales proves no risk; exact root cause is established. | Require missing-evidence and investigation language. |
| EV-08-LR **PROPOSED, HOLD** | Separate `p5-low-risk-v1` Baseline: two deterministic `Healthy` products, zero ending backlog/lost sales, fulfillment `1.0`, positive ending inventory. **Source refs/digest pending trusted Brief issuance.** | Reclassify either product At Risk; invent shortage, bottleneck, remedy or unsupported numerical claim. | Test restraint on a genuinely Low-risk scenario. Do not score until trusted Context/Brief and exact refs exist. |

Original EV-08 is retained unchanged in `cases.v1.json` and may serve as an additional offline control, but does not replace EV-08-LR in the Owner's required eight-case adoption set. The case replacement and corpus version must be explicitly approved **before** paid outputs are seen.

## Scoring and adjudication

Apply the existing `EVALUATION_RUBRIC.md` unchanged: 0–4 per applicable dimension; evidence 20, numerical 20, output compliance 20, root cause 10, capacity 5, inventory 5, service 5, recommendations 5, trade-offs 3, uncertainty 5, completeness 2. Hard P1/critical gates first; each applicable evidence/numeric/output dimension ≥3; EV-06 trade-offs and EV-07 uncertainty ≥3; every case ≥80/100 and eight-case mean ≥85/100. Record any N/A with the exact absent Brief section and reweight only as the rubric directs. Mark reviewer disagreements explicitly; Owner adjudicates the evidence and final score. A fluent answer cannot override an invalid source or unsupported conclusion.

For each case, use this record (copy one per reviewer, per response):

| Field | Entry |
|---|---|
| Case / Brief Digest / Request Digest / approval / ledger slot | **NOT RUN** |
| Provider/P1 outcome and critical-failure check | **NOT RUN** |
| Cited refs and exact numerical slots, units, grain | **NOT RUN** |
| Evidence / Numerical / Output compliance (0–4) | **NOT SCORED** |
| Root cause / Capacity / Inventory / Service (0–4 or justified N/A) | **NOT SCORED** |
| Recommendations / Trade-offs / Uncertainty / Completeness (0–4 or justified N/A) | **NOT SCORED** |
| Supported interpretations / forbidden conclusions found / missing evidence | **NOT SCORED** |
| Weighted score, reviewer, independent rationale, disagreement and Owner adjudication | **NOT SCORED** |

Use exact canonical values for validation; any rounded display must remain separate. If Luna fails, record the specific case and failure, then return to Owner review. Do not switch models automatically.

## P5-D worksheet update — version `p5-quality-proposal-1`, 2026-11-22

The text above preserves the historical P5-R worksheet and its earlier EV-08-LR hold. Trusted Low-risk admission now passes; `cases.v2.json` is the proposed eight-slot corpus. **Its replacement of old EV-08 and the new six-dimension policy still require Owner approval before paid use.** Use [AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md](AI_RESPONSE_QUALITY_ACCEPTANCE_SPEC.md) for the proposed 1–5 policy; do not merge these scores with the historical 0–4 rubric.

### Campaign register — complete every row

| Slot | Fixture / scenario | Brief digest | Request digest | Provider/P1 status | Reviewers | Adjudicator | Score / status | Critical Failure |
|---|---|---|---|---|---|---|---|---|
| EV-01 | v1_1 / Baseline | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-02 | v1_1 / Demand_Surge | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-03 | v1_1 / Capacity_Disruption | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-04 | v1_1 / Combined_Stress | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-05 | v1_1 / Baseline comparison | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-06 | v1_1 / Baseline comparison | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-07 | v1_1 / Baseline | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |
| EV-08-LR | p5_low_risk_v1 / Baseline | PENDING | PENDING | NOT RUN | PENDING | PENDING | INCOMPLETE | PENDING |

### Copy this complete case record for **each** row and **each** reviewer

| Identity / technical field | Entry |
|---|---|
| Case ID, case version, `cases.v2.json` digest, campaign ID, fixture ID, scenario/comparison | PENDING |
| Trusted Brief digest, projected Brief digest, Request Digest, response SHA-256 | PENDING |
| Model ID/snapshot or approved alias, schema/instruction/privacy versions, output/timeout settings | PENDING |
| Owner Approval reference and expiry, Ledger slot/reservation/state, estimate/ceiling | PENDING |
| Provider status, P1 status, validated numerical slots with exact value/unit/grain | NOT RUN |
| Raw response local archive reference; source-ref list; missing expected refs | PENDING |
| Input/cached/output/reasoning tokens, latency, observed charge, billing evidence source | NOT OBSERVED |

| Quality dimension | Weight | Reviewer score 1–5 | Response claim and Brief source ref | Reason for score |
|---|---:|---|---|---|
| Factual Accuracy | 25 | PENDING | PENDING | PENDING |
| Root Cause Analysis | 20 | PENDING | PENDING | PENDING |
| Recommendation Quality | 20 | PENDING | PENDING | PENDING |
| Decision Trade-off | 15 | PENDING | PENDING | PENDING |
| Context & Risk Awareness | 10 | PENDING | PENDING | PENDING |
| Communication Quality | 10 | PENDING | PENDING | PENDING |

| Human judgment | Entry |
|---|---|
| Case-specific expected findings and source refs checked | PENDING |
| Unsupported claims, contradictory facts and missing limitations, with exact response location | PENDING |
| Critical Failure categories, evidence and reviewer decision | PENDING |
| Case requirements met? Explanation, including EV-07 uncertainty / EV-08-LR restraint | PENDING |
| Reviewer ID, review time, independent comments | PENDING |
| Second reviewer scores and rationale | PENDING |
| Disagreements and reasons | PENDING |
| Distinct adjudicator ID/time, final six scores, Critical Failure decision and resolution | PENDING |
| `Σ(weight × final_score / 5)`, case status and limiting conditions | INCOMPLETE |

### Final campaign decision record

Require eight distinct complete case records for EV-01–07 and EV-08-LR. Record the arithmetic mean of eight final case scores, count of Critical Failures, each case verdict, missing technical/usage evidence and every policy exception. The deterministic `aggregate_campaign` export is the calculation record; link its JSON digest here: **PENDING**. Record independent reviewers' overall recommendation, Owner adjudication, date, rationale, and explicit **PASS / PASS WITH LIMITATIONS / FAIL / INCOMPLETE**. Incomplete cases never produce automatic PASS. A model-produced self-score is not a reviewer score. The proposed six weights and thresholds remain pending Owner approval.
