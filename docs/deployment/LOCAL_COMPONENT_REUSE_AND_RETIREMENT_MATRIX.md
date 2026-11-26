# Local component reuse and retirement matrix

Date: 2026-11-25 UTC. **Classification only; no components deleted or retired from repository.**

| Component | Classification | Cloud treatment |
| --- | --- | --- |
| Planning Engine, allocation, KPI, risk, WP1/WP2, scenario comparison, dashboard | Required | Reuse unchanged business logic; adapt runtime paths only. |
| Synthetic harness, validated Brief, response validation, FakeProvider | Required / reusable | Keep public offline preview and tests. |
| Static fixtures, templates, locale/Guide | Required | Package minimal reviewed copies. |
| `StreamlitSecretsCredential` | Reusable with modification | Future backend-only OpenAI configuration; public path must start without key. |
| ProviderRequest/digest/evidence contracts | Reusable with modification | Stage 4 may use them; do not conflate Cloud app access password with paid authorization. |
| P5 SQLite Ledger, Archive, campaign state | Further investigation | Cross-restart durability needed only if real paid AI requires it; current local files are not Cloud-authoritative. |
| Windows Credential Manager, Count Worker, Task Scheduler, Docker `cp` exchange, Windows Runner | Not required for Cloud public app | Preserve historical source/test evidence, exclude from Cloud deployment package. |
| External P5 Issuer, Host signing, local permit IPC | Not required for current Cloud architecture | Reassess if a concrete trust boundary later warrants it; do not migrate automatically. |
| Existing private Demo repo/release manifest | Reusable with modification | Owner-reviewed source boundary; current remote/deployed SHA needs verification. |

This matrix does not authorize deletion, production migration, or any change to P1/P2/business contracts.
