# Phase 1 Regression Report

**Status: PASS（141個最終Python case methods）；整個Phase1仍PASS WITH LIMITATIONS。**

本次僅 Phase 1 UAT Coverage & Reliability；不代表所有資料／模式／負向 Published E2E 都已通過。方法、實際 commands/results 與 evidence 如下；歷史 red/harness attempts 全數保留。

Evidence root: /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_1_reliability/20261119T034337Z_f91753

| Group | Actual final result | Evidence |
| --- | --- | --- |
| WS1 coverage | 13 PASS | [coverage_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/coverage_results.json) |
| R1–R3 final | 22 PASS;0fail/error/skip;0runner calls | [risk_recovery_final_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/risk_recovery_final_results.json) |
| Safe existing regression | 99 unique PASS after targeted fixture correction | [regression_reconciled.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/regression_reconciled.json) |
| Negative AppTest presentation | 7 PASS;0runner calls;not Published E2E | [negative_ui_layers.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/negative_ui_layers.json) |

## Confirmed defects and narrow fixes

- R1：null/list/scalar及nested manifest wrong types造成uncaught exception或被接受；追加Run_ID=[]/{}的red2subtest TypeError後補string guard。Loader明確shape ValueError與可理解訊息，沒有改計算。
- R2：原server state已None/[]但wire未clear；修復前真實Run A→B→A仍顯示Baseline。明確None/[] assignment同步所有相關WP2 widget，移除redundant default避免新warning。修復後visible/ARIA與manual reselection均通過。
- R3：True或mixed[1,True]被當1；比較邊界採與planner一致的numeric/bool拒絕。合法1/2/3含合法numeric1.0不變。
- R4：setup副作用確立；110方法AST盤點、40會runner的排除，70只屬需人工確認candidate，不全數視為授權。

## Commands and safe execution

22-final: PHASE1_EVIDENCE_ROOT=<root> python -B -c "import tests.test_phase1_risks as r; r.run_report(\"recovery_final\")"。Safe99: P1_EVIDENCE_ROOT=<root> python -B scripts/phase1_safe_regression.py。Affected-only2: same command --investigation-only。UI7: python -B tests/test_phase1_ui_layers.py。實際stdout／unittestlogs均在logs/；PYTHONDONTWRITEBYTECODE=1、TMPDIR指向本root。

原99第一次98PASS/1FAIL是新adapter用了PLANT-1 Run，但原assert要求SITE-1；只修新runner mapping至已核准R-ZERO，再跑兩個受影響方法，2PASS。保留原失敗JSON/log；不是產品缺陷，不把重跑加成101unique tests。

Original comparison suite與WP1/dashboard assertions以existing-Run adapter取代planning setup；原AC七方法/pipeline persisted-run suites不原樣跑，hand-tableau保護相對公式但不冒稱原AC完整重跑。允許的SequentialUpgradeTests只做memory simulation。歷史完整227未重跑；不使用blind discovery。

## Protected behavior

Planning priority/shared pool/full horizon/conservation/receipt timing、WP1 fullkey/pool/peers/trajectory/native export、WP2 sameRun/fixed cohort/coverage/endpoints/comparability/context皆由safe99/新tests/實際Browser及14獨立checks共同保護。原engines/KPI與planning_risk來源bytes不變。

Incremental source diff: [phase1_incremental_source.diff](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/phase1_incremental_source.diff). 原red21(10fail/5error)、Run_ID red(1test/2subtest errors)、harness import/fixture錯誤、green21均保留，不藏失敗歷史。
