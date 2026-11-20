# Phase 2 Inventory and Invariant Baseline

Status: P2-A COMPLETE. Main Agent only. Internal checkpoint under integrated owner authorization, not a separate approval gate.

## Scope and source

Current app, approved v1.1 specification and Phase 1 closure. No new engine/schema or Phase 1 negative-data fixture. Original UI inventory contains 203 sites; current widget and paired translation inventories are machine-readable in [evidence reports](../../tmp/phase_2_ui/20261119T134451Z/reports/). Original v1.0 specification and application bytes are preserved in the baseline directory.

## Exact file allowlist

- dashboard/scenario_planning_app.py
- dashboard/display_metadata.py
- dashboard/i18n.py
- dashboard/locales/en.json
- dashboard/locales/zh-TW.json
- tests/test_phase2_display.py
- tests/test_phase2_i18n.py
- tests/test_phase2_workflow.py
- scripts/phase2_browser_acceptance.py
- scripts/phase2_safe_regression.py
- docs/phase_2/PHASE_2_IMPLEMENTATION_SPECIFICATION.md
- docs/phase_2/PHASE_2_INVENTORY_AND_INVARIANTS.md
- docs/phase_2/PHASE_2_EXECUTION_LOG.md
- docs/phase_2/PHASE_2_FINAL_ACCEPTANCE_REPORT.md
- docs/planning_csv_inputs.md
- docs/scenario_planning/developer_notes.md
- docs/scenario_planning/dashboard_design_proposal.md
- docs/scenario_planning/project_journal.md
- ai_agent_implementation_spec.md
- docs/USER_GUIDE_EN.md
- docs/USER_GUIDE_ZH-TW.md
- docs/PRODUCT_CAPABILITY_CATALOG_EN.md
- docs/PRODUCT_CAPABILITY_CATALOG_ZH-TW.md

The unique execution root tmp/phase_2_ui/20261119T134451Z additionally holds disposable diagnostic scripts, baseline snapshots, logs, downloads, screenshots and traces. Existing historical evidence/Run paths are read-only. No dependency, service or Git operation is allowed.

## Data and invariant matrix

| Contract | Unchanged source of truth | Evidence / safeguard |
| --- | --- | --- |
| Planning priority/workload/full horizon/receipts | src allocation/sequential/input/inventory modules | Backend file hashes and safe original pure tests; no runner/publication |
| KPI definitions | src/kpi_engine.py and scenario_comparison mappings | No edits; display helpers do not calculate; pp Delta already scaled |
| Identity | Canonical Run_ID / Scenario / Comparison_ID | Values retained in controls/context/downloads, locale excluded from identity |
| WP1 | Full keys, native evidence, peers/order, calendar adjacency, one pool | Existing helpers unchanged; actual handoff and original in-memory tests |
| WP2 | Explicit pair, fixed Reference cohort, same Run, unchanged reasons/policy | Existing backend untouched; selectors reset only for accepted Run/reference events |
| CSV | Native filenames/headers/column order/types/context/values | Raw frames passed to existing exporters; browser en/zh byte/hash equality |
| Published data | 53 initial Run manifest paths and adjacent files | Snapshot hashes before/after; no planning/upload/publication |
| User work | Ten tracked pyc changes, untracked forensic/spec files | Initial snapshot; no reset/clean/stash or overwrites |

## State matrix

| State | Owner / preservation policy |
| --- | --- |
| ui_locale | UI-only en/zh-TW, English default; no environment/config persistence |
| upload_widget_* / retained bytes | Existing stored upload mechanism; never assign uploader values programmatically |
| upload_*, map_*, provenance_*, eligibility_* | Existing capture/restore prefixes; language inside form submits values only, without validating/running |
| ui_planning_model / ui_planning_input_method / ui_published_run_path / ui_sequential_config_path | Stable explicit keys; canonical option/path values; not based on locale |
| wp2_reference / wp2_candidate / wp2_product / wp2_priorities | Existing explicit reset contracts; valid Candidate retained; Run A→B→A clears visibly |
| investigation_* / sequential_scenario | Existing full-key scope reset/handoff; ordinary locale change keeps valid values |
| Momentary buttons/download controls | Never restored from snapshots; avoids illegal Streamlit state assignment |
| Locale request | In CSV form, explicit Apply language and keep inputs; outside CSV form, sidebar selector. Both request keys synchronized after application |

No new Run Picker, task router or automatic tab activation. Handoff instructions explicitly describe manual navigation. Source/user data and machine statuses remain canonical; display column labels are metadata, not DataFrame renames.

## Diagnostics and untranslated-detail register

Application-owned labels, captions, summaries, help and known empty-cohort/zero-denominator message families use central dictionaries. Original backend reasons, Risk_Signals/Risk_Reason details, uploaded content/statuses, IDs, paths, serialized JSON, evidence fields and machine statuses remain raw and accessible. A localized diagnostic summary accompanies raw free-form messages. Streamlit/grid/Vega/Plotly/OS chrome and default chart date formatting are external text; no third-party patching or warning suppression. Unknown canonical table columns remain visible unchanged as technical identifiers, not silently dropped. This boundary is explicit; there is no universal “every English character translated” claim.

## Translation and metric glossary

Metric labels/help and field/status/cohort terminology live in en.json / zh-TW.json; display_metadata.py stores canonical key associations and precision/kind only. Source keys are stable function-scoped dictionary IDs; dynamic templates retain named placeholders. Complete paired values are in translation_inventory.json.

| Canonical metric key | English | Traditional Chinese | Basis |
| --- | --- | --- | --- |
| metric.Production_Coverage_Rate.label | Production Coverage Rate | 生產涵蓋率 | Internal production / required production. Zero requirement is N/A. |
| metric.Demand_Fulfillment_Rate.label | Demand Fulfillment Rate | 需求滿足率 | Use Fulfillment_Basis: current-week cohort or horizon-origin cohort; opening-origin service is excluded from horizon service. |
| metric.Horizon_Service_Level.label | Horizon Service Level | 規劃期間服務水準 | (Current fulfillment + fulfilled horizon-origin backlog) / qualified demand; excludes opening-origin service. |
| metric.Weekly_Service_Level.label | Weekly Service Level | 每週服務水準 | Current-week fulfilled demand / current-week qualified demand; later backlog service is not current-week service. |
| metric.Terminal_Backlog.label | Terminal Backlog | 期末累積欠單 | Terminal item endpoint stock, never a sum of weekly backlog stocks. |
| metric.Ending_Backlog.label | Ending Backlog | 期末累積欠單 | Ending backlog stock at the displayed grain. Zero LOST_SALES backlog is not improved service. |
| metric.Ending_Inventory.label | Ending Inventory | 期末庫存 | Terminal inventory stock in product units; never sum weekly stocks. |
| metric.Lost_Sales.label | Lost Sales | 流失銷售 | Policy-defined unfulfilled quantity flow; separate from terminal backlog. |
| metric.Lost_Sales_Qty.label | Lost Sales Quantity | 流失銷售數量 | Policy-defined loss flow, not terminal backlog. |
| metric.Allocated_Workload.label | Allocated Workload | 已分配工作負荷 | Allocated equivalent workload; not product quantity. |
| metric.Unmet_Workload.label | Unmet Workload | 未滿足工作負荷 | Unmet workload at the native product or shared pool grain; not cohort capacity. |
| metric.Capacity_Utilization.label | Capacity Utilization | 產能利用率 | Allocated / available workload in unique plant-week pools; zero capacity is N/A in sequential mode. |
| metric.Delta.label | Delta (Candidate − Reference) | 差異（候選－參考） | Use Delta_Unit. Service deltas are already percentage points; do not multiply by 100 again. |
| metric.Required_Production_Qty.label | Required Production Quantity | 所需生產數量 | Existing net production requirement; not raw demand or workload. |
| metric.Scenario_Qualified_Demand.label | Scenario Qualified Demand | 情境合格需求 | Scenario demand after explicit qualification and coverage. |
| metric.Fulfilled_Quantity.label | Fulfilled Quantity | 已滿足數量 | Existing horizon fulfillment numerator; excludes opening-origin service. |
| metric.Current_Unfulfilled_Quantity.label | Current Unfulfilled Quantity | 當期未滿足數量 | Current-demand unfulfilled flow; not terminal backlog. |
| metric.Terminal_Opening_Backlog.label | Terminal Opening-origin Backlog | 期末期初來源欠單 | Terminal remaining opening-origin obligations. |
| metric.Terminal_Horizon_Backlog.label | Terminal Horizon-origin Backlog | 期末期間來源欠單 | Terminal remaining horizon-origin obligations. |
| metric.Service_Level.label | Service Level | 服務水準（歷史獨立週模式） | Legacy allocated quantity / net demand; keep the legacy zero-denominator policy. |
| metric.Allocation_Rate.label | Allocation Rate | 分配率（歷史模式） | Legacy allocated quantity / scenario demand, not sequential horizon service. |

## Widget identity inventory

| Function | Surface | Key | Label expression |
| --- | --- | --- | --- |
| _run_controls | date_input | 'ui_run_controls_date_input_2' | t('ui.run_controls.41a591c1a92a') |
| _run_controls | date_input | 'ui_run_controls_date_input_3' | t('ui.run_controls.f2f154d87898') |
| _run_controls | number_input | 'ui_run_controls_number_input_4' | t('ui.run_controls.3f4ea5cf5e11') |
| _run_controls | number_input | 'ui_run_controls_number_input_5' | t('ui.run_controls.135bc0b63887') |
| _run_controls | selectbox | 'ui_run_controls_selectbox_6' | t('ui.run_controls.39b3fb4803d5') |
| _run_controls | button | 'ui_run_controls_button_7' | t('ui.run_controls.b18bba05ab1d') |
| _overview | selectbox | 'ui_overview_selectbox_2' | t('ui.overview.2fcb5d374697') |
| _allocation_detail | selectbox | 'detail_scenario' | t('ui.allocation_detail.96f7a6b3a027') |
| _allocation_detail | selectbox | 'detail_plant' | t('ui.allocation_detail.0bd287f6ce17') |
| _render_column_mapping | selectbox | f'provenance_{dataset}' | t('ui.render_column_mapping.168dc92a7edb') |
| _render_column_mapping | selectbox | f'map_{dataset}_{canonical}_{uploaded.name}' | t('ui.render_column_mapping.380e3dbd6730', p0=canonical, p1=' *' if canonical in required else '') |
| _user_csv_upload_workflow | radio | 'upload_demand_format' | t('ui.user_csv_upload_workflow.b95a1f51b901') |
| _user_csv_upload_workflow | selectbox | 'upload_interpretation' | t('ui.user_csv_upload_workflow.f1b413244e48') |
| _user_csv_upload_workflow | text_input | 'upload_assumption_version' | t('ui.user_csv_upload_workflow.838b1873c8ea') |
| _user_csv_upload_workflow | number_input | 'upload_quantity_step' | t('ui.user_csv_upload_workflow.b0fa4241919e') |
| _user_csv_upload_workflow | number_input | 'upload_surge_pct' | t('ui.user_csv_upload_workflow.363490b8991e') |
| _user_csv_upload_workflow | number_input | 'upload_disruption_pct' | t('ui.user_csv_upload_workflow.8571395c8005') |
| _user_csv_upload_workflow | multiselect | f'upload_disrupted_plants_{plants_key}' | t('ui.user_csv_upload_workflow.955fc3a56a5a') |
| _user_csv_upload_workflow | selectbox | 'upload_backlog_policy' | t('ui.user_csv_upload_workflow.3d234b7e424e') |
| _user_csv_upload_workflow | form_submit_button | form-managed | t('ui.user_csv_upload_workflow.9e85075f0c01') |
| _user_csv_upload_workflow | form_submit_button | form-managed | t('ui.user_csv_upload_workflow.6e3fe7846156') |
| _user_csv_upload_workflow | download_button | f'download_template_{name}' | t('ui.user_csv_upload_workflow.6fa9e12bf7fc', p0=localize(CSV_INPUT_SCHEMAS[name][0])) |
| _user_csv_upload_workflow | file_uploader | f'upload_widget_{dataset}' | t('ui.user_csv_upload_workflow.8cbaa55a52ef', p0=localize(label), p1=t('upload.required') if dataset in required_uploads else t('upload.optional')) |
| _user_csv_upload_workflow | date_input | f'upload_start_week_{horizon_widget_key}' | t('ui.user_csv_upload_workflow.3e0fd01065a6') |
| _user_csv_upload_workflow | date_input | f'upload_end_week_{horizon_widget_key}' | t('ui.user_csv_upload_workflow.c2e1866609b6') |
| _user_csv_upload_workflow | text_input | 'upload_quantity_unit' | t('ui.user_csv_upload_workflow.52a08ee9a085') |
| _user_csv_upload_workflow | checkbox | 'upload_use_priority' | t('ui.user_csv_upload_workflow.350885b217bf') |
| _user_csv_upload_workflow | selectbox | 'upload_assumed_priority' | t('ui.user_csv_upload_workflow.c7bb626a504f') |
| _user_csv_upload_workflow | checkbox | 'upload_use_factor' | t('ui.user_csv_upload_workflow.0d92b4c13ed0') |
| _user_csv_upload_workflow | number_input | 'upload_uniform_factor' | t('ui.user_csv_upload_workflow.540c922746b5') |
| _user_csv_upload_workflow | text_input | 'upload_workload_unit' | t('ui.user_csv_upload_workflow.2cfdc8a6fe8f') |
| _user_csv_upload_workflow | checkbox | 'upload_zero_inventory' | t('ui.user_csv_upload_workflow.92ca2fc427c4') |
| _user_csv_upload_workflow | checkbox | 'upload_zero_backlog' | t('ui.user_csv_upload_workflow.99caf326c4ba') |
| _user_csv_upload_workflow | checkbox | 'upload_no_receipts' | t('ui.user_csv_upload_workflow.c67ea6e1d864') |
| _user_csv_upload_workflow | checkbox | 'upload_calibrate_capacity' | t('ui.user_csv_upload_workflow.e10917b8fa24') |
| _user_csv_upload_workflow | number_input | 'upload_target_utilization' | t('ui.user_csv_upload_workflow.a73f263428d9') |
| _user_csv_upload_workflow | download_button | 'upload_run_manifest_download' | t('ui.user_csv_upload_workflow.9632aff0f596') |
| _user_csv_upload_workflow | selectbox | f'eligibility_{index}_{status}' | t('ui.user_csv_upload_workflow.7f61c6cb867b', p0=status) |
| _user_csv_upload_workflow | checkbox | 'upload_ui_user_csv_upload_workflow_checkbox_43' | t('ui.user_csv_upload_workflow.49d6ae885be6') |
| _user_csv_upload_workflow | checkbox | 'upload_ui_user_csv_upload_workflow_checkbox_45' | t('ui.user_csv_upload_workflow.2982f08bede9') |
| _investigation_select | selectbox | key | localize(label) |
| _root_cause_investigation | download_button | f'evidence_download_{name}' | t('ui.root_cause_investigation.4dea83904a8a', p0=name) |
| _planning_risk_summary | selectbox | f'risk_product_{selected_scenario}' | t('ui.planning_risk_summary.fc629b4f441b') |
| _planning_risk_summary | button | 'investigate_product' | t('ui.planning_risk_summary.cd5bf6fd2ea6') |
| _planning_risk_summary | selectbox | f'risk_plant_{selected_scenario}' | t('ui.planning_risk_summary.5b95e6edfd45') |
| _planning_risk_summary | button | 'investigate_plant' | t('ui.planning_risk_summary.f3de97961801') |
| _scenario_tradeoff_analysis | selectbox | 'wp2_reference' | t('ui.scenario_tradeoff_analysis.d085d703e7f0') |
| _scenario_tradeoff_analysis | selectbox | 'wp2_candidate' | t('ui.scenario_tradeoff_analysis.be83d15cbcbd') |
| _scenario_tradeoff_analysis | multiselect | 'wp2_priorities' | t('ui.scenario_tradeoff_analysis.ce18aa647d9e') |
| _scenario_tradeoff_analysis | selectbox | 'wp2_product' | t('ui.scenario_tradeoff_analysis.438a10baeecb') |
| _scenario_tradeoff_analysis | download_button | f'wp2_download_{name}' | localize(label) |
| _scenario_tradeoff_analysis | button | f'wp2_investigate_{side.lower()}' | t('ui.scenario_tradeoff_analysis.825974e2ff04', p0=t('side.' + side.lower())) |
| _sequential_views | radio | 'ui_planning_input_method' | t('ui.sequential_views.523611cca3e9') |
| _sequential_views | text_input | 'ui_published_run_path' | t('ui.sequential_views.e1694cb96dd8') |
| _sequential_views | selectbox | 'sequential_scenario' | t('ui.sequential_views.0f624371985d') |
| _sequential_views | text_input | 'ui_sequential_config_path' | t('ui.sequential_views.8ac82fd8e33c') |
| _sequential_views | button | 'ui_sequential_views_button_10' | t('ui.sequential_views.674b67e4a20b') |
| _sequential_views | download_button | f'ui_published_download_{filename}' | localize(label) |
| _language_form | selectbox | 'upload_language_request' | t('locale.label') |
| _language_form | form_submit_button | form-managed | t('locale.apply') |
| _language_sidebar | selectbox | 'ui_language_request' | t('locale.label') |
| main | selectbox | 'ui_planning_model' | t('ui.main.914d526ec39a') |

## Acceptance mapping

T01 inventory, T02 snapshots, T03 runner guards; T04–T15 workflow/state/form; T16–T25 display/translation; T26–T28 WP1; T29–T31 byte/context checks; T32 browser readability; T33 final integrity. Actual outcomes are in the final acceptance report, not presumed by this inventory. Seven Phase 1 NC cases remain PARTIAL at case level with their Published E2E sublayers NOT COVERED; toolbar, provenance and Vega observations remain deferred.
