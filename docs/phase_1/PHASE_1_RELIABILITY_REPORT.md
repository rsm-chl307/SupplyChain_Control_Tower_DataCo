# Phase 1 Reliability Report

**Status: PASS WITH LIMITATIONS。** 完整揭露toolbar診斷14PASS／2FAIL；不是全部操作通過。

本次僅 Phase 1 UAT Coverage & Reliability；不代表所有資料／模式／負向 Published E2E 都已通過。方法、實際 commands/results 與 evidence 如下；歷史 red/harness attempts 全數保留。

Evidence root: /workspace/SupplyChain_Control_Tower_DataCo/tmp/phase_1_reliability/20261119T034337Z_f91753

## Method and actual results

沿用已完成而未失效的WS2診斷，不重跑。scripts/phase1_reliability_probe.py依序以shared Python --mode performance、隔離Playwright venv --mode browser、shared Python --mode decode執行。

Chart lifecycle18PASS；28個實際Arrow chart datasets核對native artifacts全部PASS；兩viewport1440×1100及1600×1100各166warnings，共332。Console/page/failed requests各0。Initial/rerun/scenario/plant/toggle都有timestamp、payload與實際畫面。較支持Vega先embed後insert資料的初始化domain推論，不宣稱每warning精確時點都已證實，不suppress或改chart資料。

## Toolbar — open observation

每viewport各2charts×2directions×2methods，16操作：14PASS、2FAIL。兩個FAIL皆Plant Show-chart mouse被dvn-scroller攔截，正常5秒timeout，finalstate=data；各自hit-test/screenshot/trace保存。後續獨立keyboard測量成功，圖表恢復；不force click、不改第三方資產。不做未授權UX改版。歷史D03 mouse=true/keyboard=false/chart_restored=true保留，新證據不回寫歷史。

| Viewport | Chart | Direction | Method | Actual status |
| --- | --- | --- | --- | --- |
| {'width': 1440, 'height': 1100} | overview | show_data | mouse | PASS |
| {'width': 1440, 'height': 1100} | overview | show_chart | mouse | PASS |
| {'width': 1440, 'height': 1100} | overview | show_data | keyboard | PASS |
| {'width': 1440, 'height': 1100} | overview | show_chart | keyboard | PASS |
| {'width': 1440, 'height': 1100} | plant | show_data | mouse | PASS |
| {'width': 1440, 'height': 1100} | plant | show_chart | mouse | FAIL |
| {'width': 1440, 'height': 1100} | plant | show_data | keyboard | PASS |
| {'width': 1440, 'height': 1100} | plant | show_chart | keyboard | PASS |
| {'width': 1600, 'height': 1100} | overview | show_data | mouse | PASS |
| {'width': 1600, 'height': 1100} | overview | show_chart | mouse | PASS |
| {'width': 1600, 'height': 1100} | overview | show_data | keyboard | PASS |
| {'width': 1600, 'height': 1100} | overview | show_chart | keyboard | PASS |
| {'width': 1600, 'height': 1100} | plant | show_data | mouse | PASS |
| {'width': 1600, 'height': 1100} | plant | show_chart | mouse | FAIL |
| {'width': 1600, 'height': 1100} | plant | show_data | keyboard | PASS |
| {'width': 1600, 'height': 1100} | plant | show_chart | keyboard | PASS |

## CSV and performance

同一existing primary pair做3次分段load/compute/four-export serialization，tracemalloc是traced allocation，不是process RSS；實際browser完成/表格geometry另記。

| Iteration | Load seconds | Compute seconds | Four-CSV seconds | Serialization peak bytes |
| --- | --- | --- | --- | --- |
| 1 | 0.6700095570122357 | 1.6438556220091414 | 0.10335675699752755 | 14787330 |
| 2 | 0.14587411901447922 | 1.7715250040055253 | 0.10012679101782851 | 14724400 |
| 3 | 0.1560965969983954 | 1.4678433320077602 | 0.10654167502070777 | 14724349 |

四CSV與歷史同fixture bytes完全相同；metrics6,866,365bytes，36rows27cols。Repeated embedded evidence/context是既有contract。單一樣本不是普遍效能benchmark，沒有新增SLO、cache、deferred export、schema／sidecar變更或optimization。寬表仍需水平捲動。

Evidence: [reliability_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/reliability_results.json), [toolbar_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/toolbar_results.json), [ws2_chart_payload_validation.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/ws2_chart_payload_validation.json), [performance_results.json](../../tmp/phase_1_reliability/20261119T034337Z_f91753/reports/performance_results.json).
