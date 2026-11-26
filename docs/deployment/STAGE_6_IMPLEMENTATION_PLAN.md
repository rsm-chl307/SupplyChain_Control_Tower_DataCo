# Stage 6 — implementation plan

Date: 2026-11-26. Baseline at start: `main` / `be425671b27918788dfcec0d39b2d221158cfef7`; 35 modified tracked, 176 untracked, zero staged files. Existing work is preserved.

| Order | Minimal change | Targeted validation |
| --- | --- | --- |
| 6.1 | Extend `cloud_question.py` with immutable canonical wire bytes, a short-lived one-use Service handoff ticket, and a fixed, injectable Responses transport. Preserve existing Fake interfaces. | Exact payload/hash, direct-call rejection, ticket replay, one call, endpoint and timeout tests. |
| 6.2 | Use existing `credential_provider.py` only after backend preflight; sanitize credential failures. | Synthetic key, missing/invalid key and no-leak tests. |
| 6.3 | Connect an explicit disabled-by-default provider selection to existing `CloudAIService.ask`; require model and price settings for real selection. | Disabled selection, rejected-before-provider and no-network tests. |
| 6.4 | Parse bounded HTTP response, classify status/model/usage and continue through P1 gate. | Complete/incomplete/malformed/oversized/unknown tests. |
| 6.5 | Preserve Stage 5 estimated reservation and expose reported usage as separate evidence. | Price mismatch, missing usage, over-cap usage tests. |
| 6.6 | Exercise UI with Mock Transport and run Stage 4/5 and planning regression. | AppTest, focused tests, relevant business suites. |

Files explicitly excluded: Planning Engine, WP1/WP2, P5 Worker/package/allowlist, Count Worker, Ledger/Archive and production configuration. No new runtime dependency is planned; the standard-library HTTPS client is adequate for the fixed Responses endpoint and avoids an unapproved environment change. No real request is run. Review the full diff and stop after the Stage 6 reports.
