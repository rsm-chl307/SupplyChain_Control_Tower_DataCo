# Cloud cost and free-tier comparison

Research date: **2026-11-25 UTC**. Prices and quotas can change; confirm in the Owner's account before activation. Figures below are vendor list prices, not a guarantee of zero charges. AI API charges are separate from hosting.

| Architecture | Minimum recurring infrastructure cost | Free-tier limits / triggers | Light personal Demo estimate |
| --- | --- | --- | --- |
| A. Streamlit Community Cloud only | $0 hosting; packaged data and Streamlit Secrets add no separate service bill | Free apps can hibernate after inactivity; shared CPU/memory/storage quotas and no durable local filesystem guarantee. [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud), [resource limits](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app). | **$0 infrastructure** while within free limits; no background-worker bill. Paid AI additional. |
| B. Streamlit + Supabase | $0 on Free; Pro starts at **$25/month** | Free: 500 MB database/project, 1 GB file storage, 5 GB egress, up to 2 active projects, pause after 7 days inactivity; no free automatic database backup. Pro and overages create charges. [Supabase pricing](https://supabase.com/pricing), [pause behavior](https://supabase.com/docs/guides/platform/free-project-pausing). | $0 if low traffic and pauses acceptable; $25+/month for Pro. |
| C. Streamlit + Neon PostgreSQL | $0 on Free; Launch usage billing if upgraded | Free: 100 CU-hours/project/month, 1 GB/project storage, 5 GB public transfer, compute scales to zero after 5 minutes idle. Launch: $0.106/CU-hour plus $0.35/GB-month, with no monthly minimum per current plan. [Neon pricing](https://neon.com/pricing), [plan limits](https://neon.com/docs/introduction/plans). | $0 if within quota; small paid usage varies by compute hours/storage/transfer. |
| D. Streamlit + external secret manager or object store | Can be $0 within service-specific free limits; may require cloud billing account | Google Secret Manager lists 6 active versions and 10,000 access operations/month free; additional use billed. AWS Secrets Manager starts around $0.40 per secret/month plus API requests. Storage and egress are separate. [Google pricing](https://cloud.google.com/secret-manager/pricing), [AWS pricing](https://aws.amazon.com/secrets-manager/pricing/). | Adds complexity and possibly a small nonzero bill, with no proven first-release benefit. |
| E. Streamlit + Cloud Run / full cloud backend | Cloud Run has a requests-based free tier but requires billing and other service choices | Free tier includes 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds/month; network egress, database, storage, secrets and regional choices may cost extra. [Cloud Run pricing](https://cloud.google.com/run/pricing). | Could be $0 at tiny use, but less predictable and more operational work than A. |

Community Cloud has no separate continuously running background worker in the proposed first release. Streamlit app runtime storage is temporary; publishing a SQLite file there does not establish cross-restart durability. The private Owner app is a future option; [Streamlit sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app) describes private-repo sharing and current account limits. Confirm the Owner account's actual available app slots and visibility before committing to two apps.

## OpenAI API cost, separate from infrastructure

The selected `gpt-6-luna` [official model page](https://developers.openai.com/api/docs/models/gpt-6-luna) lists standard short-context pricing of **$0.10 per million input tokens** and **$0.50 per million output tokens**; cached input is $0.01 per million. Usage beyond the relevant context tier, tools or other provider charges can change the bill. The real response's token usage is the source for final accounting. No API call was made for this estimate.

Formula, ignoring cached-input discounts and other fees:

`estimated USD = input_tokens × 0.10 / 1,000,000 + output_tokens × 0.50 / 1,000,000`

| Illustrative monthly use | Input / output per call | Estimate |
| --- | --- | ---: |
| 50 Owner calls | 8,000 / 2,000 | $0.09 |
| 50 larger calls | 25,000 / 25,000 | $0.75 |
| 2,500 larger calls if public abuse is possible | 25,000 / 25,000 | $37.50 |

These are **examples**, not a budget approval or forecast for the eight-case evaluation. Count requests, retries, failed dispatches that consume tokens, and provider-side charges need separate accounting. Public anonymous paid AI can dominate the hosting cost even when infrastructure is free.

The Owner should configure provider project spend controls separately from application quotas. [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits) distinguish limits from alerts; [OpenAI help](https://help.openai.com/en/articles/6614457-troubleshooting-api-usage-and-spend-limits) notes enforcement may lag or slightly exceed a configured limit. An application's local cost ceiling is **not** a provider-side hard cap, and neither control should be described as instantaneous or absolute.

## Cost recommendation

Release the public, no-paid-API Demo on Option A first. Add Neon only when the Owner explicitly requires durable paid execution records or cross-session user state. Do not add Supabase, a secret manager, or a cloud backend without a measured need. Require Owner review of actual usage and free-tier consumption after launch, especially if paid AI is later activated.
