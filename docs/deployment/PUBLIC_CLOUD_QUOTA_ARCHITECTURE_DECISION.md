# Public Cloud Quota Architecture Decision

Date: 2026-11-27. Scope: design analysis only; no Cloud deployment or persistent public quota implementation is authorized.

## Current limitation

Process-local counters and in-memory locks reset when Streamlit restarts, do not coordinate concurrent replicas or users, and cannot settle a charge after a timeout. A public user can receive a new local allowance on another process. These controls are unsuitable as the sole public paid-AI quota boundary.

## Lowest-cost durable option

Use one small transactional SQL store with unique request IDs, atomic reserve/claim transitions and an append-only usage/charge ledger. Keep per-user and global ceilings in the same transaction, reserve the full worst-case amount before dispatch, hold ambiguous attempts until billing reconciliation, and reject when store connectivity is unavailable. A hosted managed database with a free or low-cost tier may be practical, but the actual provider, cost, durability, backup and concurrency terms must be chosen after reviewing deployment requirements. SQLite on ephemeral Streamlit Community Cloud storage is not sufficient across restarts or replicas. Provider-side project spending controls add protection, but [OpenAI documents](https://developers.openai.com/api/docs/guides/spend-limits) that hard-limit enforcement is not instantaneous, so they do not guarantee an exact external bill ceiling.

## Owner decisions before public service

Confirm whether public AI is in product scope; identity and per-user access policy; global and per-user budgets; persistence provider and expected traffic; data retention and privacy; billing alert and hard-stop semantics; abuse handling; incident response; and paid AI activation. These decisions are independent of local single-Owner offline preparation. No Stage 9 or public paid service is enabled by this document.

## Review record

Environment: repository `main`, Python 3.12.16; no Cloud access or production Secret was used. This document is the only file created for this architecture decision. Its input was the published P5 Ledger/Host implementation and the [official spend-limit behavior](https://developers.openai.com/api/docs/guides/spend-limits). No executable Cloud quota change was made, so Cloud acceptance tests are NOT EXECUTED. Status: proposal awaiting Owner product and infrastructure decisions. Next step, if public AI is approved, is to select a durable store and test atomic concurrent reservations and failure recovery in an isolated environment before any deployment.
