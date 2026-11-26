# Stage 4 — AI integration test report

Date: 2026-11-25 UTC. All provider tests use FakeProvider or one-shot OfflineMockTransport with synthetic data. No real OpenAI request was made.

## Required scenarios and evidence

| Scenario | Test evidence / expected result |
| --- | --- |
| Public Planning without AI password | Streamlit AppTest opens Planning and retains its existing functions. |
| Wrong/missing password | No Copilot context or provider action rendered; no provider invocation. Missing verifier configuration produces a controlled message. |
| Correct synthetic password | Backend gate admits only that browser session; password and verifier absent from session-state representation after submit. |
| Five wrong attempts / session expiry | Session locks; correct password cannot bypass lock; expiry removes access. New session starts unauthenticated. |
| Trusted context and question | SyntheticHarness → ValidatedBrief → ProviderRequest → question/context digest → FakeProvider → P1 `VALIDATED`. |
| Follow-up | Bounded prior validated summary included and bound to a new question digest. |
| Missing/invalid context or question | Rejected before provider execution. |
| Malformed/failing/uncertain provider response | P1 validation failure, definitive error or UNKNOWN; no advisory success. |
| JSON path traversal, absolute path, Secret path, symlink escape | Rejected before file content is read. Only packaged synthetic config and adjacent CSVs accepted. |
| Provider isolation | Socket connect blocked during UI tests; real Cloud provider execute remains locked before credential lookup. |

## Commands and results

Executed commands and results:

- `python -B -m unittest tests.test_cloud_access tests.test_cloud_paths tests.test_cloud_knowledge tests.test_cloud_question` → final **17/17 PASS in 11.501 s** after symlinked-root hardening. The path suite also passed separately **7/7**.
- `python -B -m unittest tests.test_stage4_cloud_ai_ui tests.test_ai_copilot_ui tests.test_ai_copilot_dashboard_synthetic tests.test_synthetic_context_lifecycle` → **19/19 PASS in 127.019 s**. AppTest used only synthetic verifier material and blocked socket connections.
- `python -B -m unittest tests.test_phase2_workflow tests.test_cloud_paths` → initial run **FAILED with 7 errors**: the new published-run allowlist excluded an existing fixed WP2 acceptance Run. The allowlist was narrowed to include that exact historical local root; rerun **16/16 PASS in 46.450 s**. After the symlinked-root hardening, a focused WP2 smoke test also passed **1/1**.
- `python -B -m unittest tests.test_cloud_question tests.test_cloud_knowledge` → **6/6 PASS** for exact request binding, business excerpt selection and mock response interpretation.
- `python -B -m unittest tests.test_planning_risk tests.test_phase1_risks tests.test_scenario_comparison tests.test_ai_brief_workflow tests.test_ai_brief_validation tests.test_ai_copilot_provider` → **114/114 PASS in 165.885 s**. The tested business rules and Brief/provider contracts were not changed.

The suites overlap; these counts are reported per command and are not summed as unique tests. Final `git diff --check`, six-module AST parse, local Markdown link check and new-code key-pattern scan all passed. Streamlit's existing `use_container_width` deprecation warnings appeared during AppTest but did not fail assertions.

Python 3.12 and actual Streamlit Community Cloud are unavailable in this environment. Fake tests cannot prove a real OpenAI response, paid billing or production Secret isolation. Stage 5 and release preparation remain separately authorized. **Stage 4 Fake integration: PASS WITH LIMITATIONS; ready for Owner review before Stage 5.**
