# Stage 5 — Security and cost control test report

Date: 2026-11-26 UTC. Environment: existing Container, Python 3.10, Streamlit 1.56.0; synthetic fixtures, Fake Provider and in-memory test credentials only. No real provider call or paid operation.

## Commands and results

| Command / scope | Final result | What it verifies |
| --- | --- | --- |
| `python -B -m unittest tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_knowledge tests.test_cloud_question tests.test_cloud_paths` | **34/34 PASS**, 50.482 s | Password and signed grant, missing Secret, backend rejection before provider, rate/duplicate/budget, configurable price, timeout/errors, output size, selected context and JSON paths. |
| `python -B -m unittest tests.test_stage4_cloud_ai_ui tests.test_ai_copilot_ui tests.test_ai_copilot_dashboard_synthetic tests.test_synthetic_context_lifecycle` | **19/19 PASS**, final rerun 117.760 s | Public Planning, password gate, Fake question/follow-up, no network, provider errors and existing Copilot UI. |
| `python -B -m unittest tests.test_planning_risk tests.test_phase1_risks tests.test_scenario_comparison tests.test_ai_brief_workflow tests.test_ai_brief_validation tests.test_ai_copilot_provider` | **114/114 PASS**, 151.901 s | Planning/risk, Brief, scenario and provider-contract regression. |
| `python -B -m unittest tests.test_phase2_workflow tests.test_cloud_paths tests.test_planning_pipeline tests.test_scenario_generator` | **43/43 PASS**, 42.989 s | WP2 and Planning Engine regression, including JSON path restriction. |
| `python -B -m unittest tests.test_stage4_cloud_ai_ui.Stage4CloudAITests.test_missing_config_and_session_expiration` | **1/1 PASS**, 6.480 s | Final expiry cleanup removes synthetic Copilot context. |
| `python -B -m unittest tests.test_cloud_access` | **5/5 PASS**, 0.529 s | Final process-key restart simulation invalidates an old grant. |

These suites overlap and are **not** summed as unique tests. An earlier UI run produced one error because its Stage 4 assertion expected a retained `VALIDATION_FAILED` result; the Stage 5 fail-closed service intentionally removes invalid results. The test was updated to assert the stronger no-result behavior, and the full UI suite then passed. No existing test was removed or weakened to permit an invalid response.

## Security evidence and coverage

- The service tests patch `socket.socket.connect` to fail if a network call is attempted. AppTest likewise denies network. Fake credentials are synthetic; no production Secret was read.
- Rejected access, duplicate, too-fast, invalid context, oversized request, malformed cost policy and exhausted budget tests assert zero provider calls.
- A timeout test asserts exactly one invocation and no repeat of the same request digest. Unknown results do not return advisory success.
- Backend grant tests reject forged expiry, altered HMAC, expiration, missing verifier and verifier rotation.
- Provider error tests cover missing key, authentication failure, provider rate limit, service failure, invalid configuration and network category using safe Fake exceptions. Logged diagnostics contain only categories.
- A response-validator exception is converted to a safe code and does not expose its internal text or crash the application.
- Context tests assert no verifier/key setting appears in outbound arguments. Path tests reject traversal, absolute sensitive paths, symlinked JSON/CSV/manifest and oversized or malformed JSON.
- Existing P1 schema/evidence validation rejects malformed responses. A provider-reported incomplete result and a response above 16 KiB are rejected.

## Not verified

Actual Streamlit Community Cloud runtime, Python 3.12, real Cloud Secrets, OpenAI authentication/usage/billing, exact model token count, global multi-instance quotas, durable spend ceiling, provider-side hard spending limits and live browser behavior were not tested. P5 deployment-source remediation is separately scoped. Existing Streamlit deprecation/widget warnings did not fail tests.

Final static review: `git diff --check` passed; eight relevant Python files passed AST parsing; a targeted Stage 5 source/UI/report scan found **0** API-key/private-key pattern hits; `REAL_PROVIDER_DISPATCH_LOCKED=True` remains set. New untracked Stage 5 files had no trailing whitespace. **Offline Stage 5 tests: PASS; production readiness: limited.**
