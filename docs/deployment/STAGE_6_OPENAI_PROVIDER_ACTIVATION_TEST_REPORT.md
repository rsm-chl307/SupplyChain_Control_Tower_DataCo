# Stage 6 — offline test evidence

Date: 2026-11-26 UTC. Existing Container Python 3.10 / Streamlit 1.56.0, synthetic Brief, Fake Credentials and Mock Transport. Socket connections were patched to fail in Stage 6 and AI UI tests. No real API or Cloud Secret was used.

| Command | Result | Scope |
| --- | --- | --- |
| `python -B -m unittest tests.test_cloud_question tests.test_cloud_ai_service` | 15/15 PASS | First immutable request change against existing Cloud tests. |
| `python -B -m unittest tests.test_stage6_cloud_provider` | 10/10 PASS before the final handoff-ticket addition | Exact request bytes, fixed host/path, one attempt, synthetic Secret, budget denial, HTTP categories, missing/over-cap usage, malformed/incomplete/unknown response, UI Mock flow and missing-key public Planning. |
| `python -B -m unittest tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_knowledge tests.test_cloud_question tests.test_cloud_paths tests.test_stage4_cloud_ai_ui tests.test_stage6_cloud_provider` | 48/48 PASS | Stage 4/5/6 AI integration and path security; suites do not call the real provider. |
| `python -B -m unittest tests.test_planning_risk tests.test_phase1_risks tests.test_scenario_comparison tests.test_ai_brief_workflow tests.test_ai_brief_validation tests.test_ai_copilot_provider` | 114/114 PASS | Planning, risk, Brief, scenario and provider contracts. |
| `python -B -m unittest tests.test_phase2_workflow tests.test_cloud_paths tests.test_planning_pipeline tests.test_scenario_generator` | 43/43 PASS | WP2 and Planning Engine, including public UI/JSON path regression. |
| `python -B -m unittest tests.test_stage6_cloud_provider tests.test_stage4_cloud_ai_ui` | 14/14 PASS | Final changed-UI/usage-recording rerun. |
| `python -B -m unittest tests.test_stage6_cloud_provider tests.test_cloud_ai_service tests.test_cloud_question` | 26/26 PASS | Final one-use Service ticket, direct-provider rejection and Cloud contract rerun. |
| `python -B -m unittest tests.test_cloud_access tests.test_cloud_credential_provider tests.test_cloud_ai_service tests.test_cloud_knowledge tests.test_cloud_question tests.test_cloud_paths tests.test_stage4_cloud_ai_ui tests.test_stage6_cloud_provider` | **49/49 PASS** final run | Final Stage 4/5/6 AI regression after the Service ticket was added. |
| `python -B -m unittest tests.test_stage6_cloud_provider` | **11/11 PASS** last targeted run | Rechecked the final bounded-response change, including oversized HTTP body as unknown outcome with one call. |

The suites overlap; these totals must not be summed as unique test cases. WP2/UI tests printed Streamlit deprecation and widget warnings, but exited 0 and reported `OK`. No test was deleted or weakened. Focused AST parsing of four affected Python files passed. `git diff --check` was clean at interim review; final review is recorded below.

## What the tests establish

- Authorization, price, size, duplicate and rate rejection happen before the transport and key lookup. Tests inspect provider/transport call counts.
- The Service-counted payload bytes equal the Mock transport's payload bytes. Changed bytes, including changed bytes with a recomputed hash, fail provenance validation.
- Fake HTTP errors, missing key, malformed body, wrong model, timeout and incomplete response fail safely. An uncertain request is not automatically retried.
- Reported usage is separate from the estimated reservation; missing usage remains absent. P1 validation is required before UI display.
- The Streamlit UI reaches the same Mock transport after password verification; public Planning starts without a key. Test-only sentinel values are absent from Session State and wire payload.

## Not verified

No actual OpenAI call, official model compatibility, Cloud Secrets, billed charge, provider hard spending limit, multi-worker quota, deployed Streamlit runtime or public browser UAT was tested. Mock transport success is not live provider acceptance.

Final static checks: `git diff --check` exited 0; four affected Python files parsed successfully; targeted Stage 6 source/docs scan found zero API-key/private-key pattern hits and zero trailing-whitespace files. Git status retained all 211 baseline entries, added only the six intended Stage 6 files, and showed 35 modified tracked / 182 untracked / zero staged entries. The three Stage 4/5 source modules edited in Stage 6 were already untracked at baseline, so Git status counts alone do not display their content changes.
