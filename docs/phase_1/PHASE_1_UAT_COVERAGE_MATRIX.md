# Phase 1 UAT Coverage Matrix

**Status: PASS WITH LIMITATIONS — 3 PASS／7 PARTIAL／0 NOT COVERED／0 BLOCKED_PENDING_AUTHORIZATION／0 FAIL（整案分類）。** 七案的 browser／Published E2E 子層仍 NOT COVERED，不以 PARTIAL 消除缺口。

本次僅 Phase 1 UAT Coverage & Reliability；不代表所有資料／模式／負向 Published E2E 都已通過。方法、實際 commands/results 與 evidence 如下；歷史 red/harness attempts 全數保留。

Evidence root: /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_1_reliability/20261119T034337Z_f91753

| ID | Final status | Executed layers | Evidence / remaining gap |
| --- | --- | --- | --- |
| NC-SYNTHETIC | PASS | Python, production loader of immutable existing Run, Real browser, actual CSV/Arrow/native artifact reconciliation | Current existing SYNTHETIC_DEMO fixture only; not every scenario permutation. |
| NC-N03 | PASS | Python, production loader of immutable existing Run, Real browser, actual CSV/Arrow/native artifact reconciliation | NC-N03 covers zero plant-week pool, not whole-horizon zero capacity. |
| NC-N08 | PASS | Python, production loader of immutable existing Run, Real browser, actual CSV/Arrow/native artifact reconciliation | NC-N08 uses existing unpublished Run plus disposable invalid snapshots, not altered historical Runs. |
| NC-B09 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N01 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N06 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N07 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N02 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N04 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |
| NC-N05 | PARTIAL | Python pure comparison, memory-only fixture, AppTest memory-only UI presentation | Pure and AppTest UI-presentation coverage passed; no new Published Run manufactured. |

## Scope and execution

WS1 python -B tests/test_phase1_coverage.py：13 PASS；新增 tests/test_phase1_ui_layers.py：7 PASS（mocked loader的AppTest呈現，不是browser）。主Browser使用既有R-SYN/R-ZERO/R-REJECT與可清理錯誤快照，不產生Planning Run。

Detailed cases: [coverage_final.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_final.json); lower-layer originals: [coverage_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_results.json); UI: [negative_ui_layers.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/negative_ui_layers.json); fixtures: [browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/fixture_browser/browser_results.json); zero retry: [browser_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/zero_pool_retry/browser_results.json).

## Expected behavior and limits

B09固定Reference cohort/changed flags；N01非法priority UNAVAILABLE與明確Reason；N02非空zero-demand rate/delta N/A；N03單一zero pool不代表全horizon zero service；N04inventory-backed service1/workload0；N05排除opening-origin；N06逐metric阻不相容單位；N07不縮Universe/不替代endpoint；N08hash/type/unpublished拒絕且無舊export；SYN是真正SYNTHETIC_DEMO。

七個純資料負向案沒有完整合法immutable Published fixture，仍保留E2E風險；不執行planning補百分比。原十個歷史NOT COVERED紀錄不改寫。USER_DATA來源仍SYNTHETIC_EXAMPLE，非已認證真實營運資料。
