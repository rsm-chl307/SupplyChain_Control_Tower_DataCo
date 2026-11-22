# P5 eight-invocation Ledger implementation specification

Version: `p5-eight-call-ledger-spec-1`; prepared **2026-11-22 UTC** from the current repository. **Design only. No allowance, database, provider call or production setting was created.** GPT-6 Luna (`gpt-6-luna`) is the first candidate; the campaign is local-first and contains exactly eight intended invocations. Paid execution, P5-D/P5-E and P6 remain **NOT AUTHORIZED**.

## 1. Existing implementation and compatibility constraints

The current P3 `src/ai_copilot/ledger.py` has fixed `CAMPAIGN_ID = "v1.2-first-paid-acceptance"`, one `execution_ledger` row keyed by campaign, `allowance CHECK(allowance=1)`, `BEGIN IMMEDIATE` reservation, one-use approval consumption, accounting events and an Owner-attested `reconcile` that keeps `UNKNOWN`. `src/ai_copilot/approval.py` stores a separate scrypt Owner verifier and digest-bound approvals with expiry/revocation; the SQLite file and identity marker fail closed on absence/replacement/corruption. `src/ai_copilot/execution_gate.py::LocalExecutionGate.bind` rebuilds the live `ProviderRequest` from a validator-issued `ValidatedBrief` and has no `execute` method. None of these APIs supports an eight-slot campaign or per-case approvals today. Do not change their behavior or reinterpret an existing one-call approval as campaign authority.

Task 1 added `SyntheticHarness(fixture_id='p5_low_risk_v1')`, code-pinned manifest validation and live V1.1 Brief admission. It did **not** revise `cases.v1.json`, enable a paid caller, or extend P3. The [Task 1 report](../AI_COPILOT_V1_2_P5_LOW_RISK_TRUSTED_ADMISSION_REPORT.md) records the tested trust boundary. The [P5-C proposal](P5_C_BUDGET_AND_AUTHORIZATION_PROPOSAL.md) supplies a planning envelope of $0.02 per call and $0.16 total, still **unapproved**.

### Important design corrections to the earlier proposal

1. **Do not require Request Digest uniqueness across all eight slots.** `cases.v1.json` uses the same Baseline/`max_records=2` selection for EV-01 and EV-07 (and old EV-08), so identical live Brief inputs can yield the same Request Digest. A unique digest would incorrectly reject a separately approved case. Uniqueness is `(campaign_id, case_id)` plus one-use approval reference and dispatch attempt; each slot binds its exact digest even if another slot has the same bytes.
2. A V1.1 `ValidatedBrief` is bound to a **live, 300-second harness Context** and is not portable across process restart. Freeze the campaign's eight-slot roster and policy up front, then bind each slot's exact live Brief/Request Digest **once at its reservation**. Never use a stored digest to recreate a Brief or infer renewed authorization. An unreserved slot can obtain a fresh Brief and new explicit approval; a reserved slot cannot be rebound after expiry or restart.
3. The original P3 approval rows contain no campaign or case ID. A separate, versioned campaign approval table/service is required. Passing caller-supplied verifier material or reusing a Demo credential is prohibited.

## 2. Campaign and slot model

Create a **new, separately provisioned local SQLite store**, leaving the existing P3 DB, identity marker, campaign row and event history untouched. The campaign has an immutable `campaign_id` and `campaign_version`, a hash of a canonical Owner-reviewed roster/policy manifest, and exactly these slot keys:

`EV-01`, `EV-02`, `EV-03`, `EV-04`, `EV-05`, `EV-06`, `EV-07`, `EV-08-LR`.

The canonical manifest fixes each slot's case/fixture version and scenario/comparison selection; the shared model ID and either a **specific Owner-approved snapshot** or an explicit moving-alias policy; P1 schema, instruction and privacy versions; permitted request limits and transport flags; pricing-basis version; proposed per-call and aggregate ceilings; and local-only location/retention policy. Reject unknown/missing/duplicate slots and unapproved corpus versions. A slot becomes executable only after a live `ValidatedBrief` and canonical `ProviderRequest` are rebuilt and bound to that slot, together with a distinct authenticated Owner Approval. Bindings are immutable after reservation.

The slot reservation record must contain: `campaign_id`, `case_id`, `case_version`, fixture ID and source-manifest hash; actual private Run ID (local only), Brief digest, projected Brief digest and Request Digest; model ID and exact approved snapshot/alias policy; schema/instruction/privacy versions; input/output caps, measured input-token count, timeout and safe transport settings; pricing basis, estimated cost and per-call ceiling; approval reference; one-use allowance; timestamps; state; sanitized usage/charge evidence. Never store full Brief or outbound body in the Ledger. Store full source provenance separately under an approved local evidence policy and reference it by digest.

For the present P2 builder, `model_snapshot` is one explicit string and `max_output_tokens <= 2500`; a proposed 25,000-token evaluation cap is **not executable under current code**. A future separately authorized request-policy change must be tested and approved before that cap can be bound. Until then the campaign is configuration-unset and fail closed.

## 3. Owner Approval lifecycle

Use a trusted local composition root to open the provisioned store and compare its persisted Owner verifier against approved local configuration. No API may accept an arbitrary verifier, credential hash or “is_owner” flag as evidence. Owner authentication uses the separate local scrypt verifier, never Demo login. Campaign creation requires an explicit authenticated Owner decision and canonical manifest digest. Each of the eight requests requires another explicit authenticated Owner approval for `(campaign_id, case_id, campaign_manifest_digest, request_digest, brief_digest, projection_digest, model/policy versions, exact limits, estimated_cost, slot_ceiling, aggregate_ceiling)`. Store approval reference, policy version, creation/expiry, revocation and one-time consumption in the durable database.

Approval is valid only if the current live Brief and rebuilt Request match **every** bound field; the approval is unexpired, unrevoked, unconsumed; and the campaign/slot policy remains unchanged. A request change, Context expiry, owner revocation, schema/prompt/privacy/version change, snapshot change or cost change blocks reservation. Streamlit/session state has no authority. Never recreate approval during rerun or after restart.

The immutable campaign roster may be provisioned before live Briefs exist. Per-slot approval is just in time; a slot's exact digest is frozen in the same transaction that consumes that approval and reserves the slot. An expired approval for an **unreserved** slot may be replaced only by a new explicit Owner action; this is not a reused slot or automatic retry. Once reserved, that slot cannot be rebound, even if the Context later expires.

## 4. Suggested SQLite schema

Use integer **micro-USD** for ceilings/estimates/observed charges (no SQLite REAL for money), with strict decimal conversion and explicit rounding policy at the trusted service boundary. The DDL below is conceptual and must be tested with the chosen SQLite version before implementation:

```sql
CREATE TABLE store_identity (
  store_id TEXT PRIMARY KEY, owner_salt TEXT NOT NULL, owner_digest TEXT NOT NULL,
  schema_version INTEGER NOT NULL CHECK(schema_version = 1)
);
CREATE TABLE campaign_owner_approvals (
  reference TEXT PRIMARY KEY, manifest_digest TEXT NOT NULL,
  approved_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
  revoked_at INTEGER, policy_version TEXT NOT NULL,
  CHECK(expires_at > approved_at)
);
CREATE TABLE campaigns (
  campaign_id TEXT PRIMARY KEY, campaign_version TEXT NOT NULL,
  manifest_digest TEXT NOT NULL UNIQUE, model_id TEXT NOT NULL,
  model_policy TEXT NOT NULL, pricing_basis TEXT NOT NULL,
  per_slot_ceiling_micro INTEGER NOT NULL CHECK(per_slot_ceiling_micro > 0),
  total_ceiling_micro INTEGER NOT NULL CHECK(total_ceiling_micro > 0),
  reserved_micro INTEGER NOT NULL DEFAULT 0 CHECK(reserved_micro >= 0),
  status TEXT NOT NULL CHECK(status IN ('DRAFT','OPEN','HELD','CLOSED')),
  owner_campaign_approval_ref TEXT NOT NULL UNIQUE
    REFERENCES campaign_owner_approvals(reference), created_at INTEGER NOT NULL,
  CHECK(reserved_micro <= total_ceiling_micro)
);
CREATE TABLE campaign_slots (
  campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
  case_id TEXT NOT NULL, case_version TEXT NOT NULL,
  fixture_id TEXT NOT NULL, selection_digest TEXT NOT NULL,
  PRIMARY KEY (campaign_id, case_id)
);
CREATE TABLE campaign_approvals (
  reference TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
  manifest_digest TEXT NOT NULL, request_digest TEXT NOT NULL,
  brief_digest TEXT NOT NULL, projection_digest TEXT NOT NULL,
  policy_digest TEXT NOT NULL, estimated_micro INTEGER NOT NULL,
  ceiling_micro INTEGER NOT NULL, approved_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL, revoked_at INTEGER, consumed_at INTEGER,
  approval_policy_version TEXT NOT NULL,
  CHECK(expires_at > approved_at), CHECK(estimated_micro >= 0),
  CHECK(ceiling_micro >= estimated_micro)
);
CREATE TABLE slot_reservations (
  campaign_id TEXT NOT NULL, case_id TEXT NOT NULL,
  request_digest TEXT NOT NULL, brief_digest TEXT NOT NULL,
  projection_digest TEXT NOT NULL, approval_reference TEXT NOT NULL UNIQUE,
  bound_metadata_json TEXT NOT NULL, estimated_micro INTEGER NOT NULL,
  ceiling_micro INTEGER NOT NULL, reserved_at INTEGER NOT NULL,
  state TEXT NOT NULL CHECK(state IN
    ('NOT_STARTED','IN_PROGRESS','SUCCEEDED','FAILED','UNKNOWN')),
  dispatch_started_at INTEGER, updated_at INTEGER NOT NULL,
  provider_request_id TEXT, usage_json TEXT, charge_micro INTEGER,
  charge_status TEXT NOT NULL CHECK(charge_status IN
    ('UNOBSERVED','OBSERVED','RECONCILED')),
  PRIMARY KEY(campaign_id, case_id),
  FOREIGN KEY(campaign_id,case_id) REFERENCES campaign_slots(campaign_id,case_id),
  FOREIGN KEY(approval_reference) REFERENCES campaign_approvals(reference),
  CHECK(ceiling_micro >= estimated_micro), CHECK(charge_micro IS NULL OR charge_micro >= 0)
);
CREATE TABLE campaign_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id TEXT NOT NULL,
  case_id TEXT, event_type TEXT NOT NULL, event_time INTEGER NOT NULL,
  actor_kind TEXT NOT NULL, state_before TEXT, state_after TEXT,
  request_digest TEXT, approval_reference TEXT, usage_json TEXT,
  charge_micro INTEGER, note TEXT NOT NULL
);
```

Provision exactly eight `campaign_slots` in one transaction and check the canonical roster both at open and before every reservation. Use a separate `owner_decisions` table or signed `OWNER_DECISION` events for manifest approval, hold/release and close decisions; each event must bind campaign/manifest digest. Add triggers or trusted write APIs that reject UPDATE/DELETE of event rows, but do not claim SQLite alone is tamper-proof against a local administrator. All event notes and provider IDs must be sanitized; **never log keys, credentials, full Briefs, request bodies, response bodies or raw provider errors**.

Database open must require a previously provisioned regular file and identity marker with stable store ID, inode/device and restrictive permissions, as P3 does. Use `mode=rw`, `PRAGMA foreign_keys=ON`, an integrity check, a defined busy timeout, and a schema-version check. Missing/replaced/corrupt files fail closed; no automatic recreation or replay of approvals. Keep the P3 store untouched and give the eight-call store a distinct identity and path.

## 5. Transaction and budget algorithm

**Provision:** Owner authenticates; validate exact roster, corpus version, model policy and explicit positive monetary caps. Create the identity/store and all tables with exclusive new-file semantics; insert campaign, eight slots and `PROVISIONED`/Owner decision events atomically. Do not create an OPEN campaign until approval and policy preconditions are complete. No implicit $0.02/$0.16 default: those are proposal values until approved.

**Approve one slot:** Rebuild request from live validator-issued Brief using trusted `LocalExecutionGate.bind` equivalent; verify `verify_request`; compare case selection to immutable slot template; require Owner password; insert one approval and `APPROVED` event with TTL, digest and cost policy. Approval creation does not reserve or dispatch.

**Reserve one slot:** The service takes a live Brief, exact request, case ID and approval reference. Before transaction, revalidate Brief and request. Inside `BEGIN IMMEDIATE`: recheck database identity, campaign OPEN, roster/version, slot unreserved, exact unexpired approval, model/policy/limits, measured input gate, estimate ≤ slot ceiling, and no unresolved campaign hold. Compute or compare `reserved_micro + slot_ceiling_micro <= total_ceiling_micro`; update the aggregate with a conditional SQL predicate; insert immutable slot reservation, mark approval consumed and append `RESERVED` event **in the same transaction**. Commit before any future dispatch. On any failure roll back all changes. Unique `(campaign,case)` and `approval_reference` constraints plus the SQLite writer lock block concurrent local processes. Duplicate clicks or requests return a blocked status, never a second allowance.

Reserve the **full ceiling**, not just the estimate. Keep the reserved total as the sum of every slot ceiling, including successful, failed and UNKNOWN slots; never recycle a completed or uncertain allowance. At eight proposed $0.02 ceilings, the aggregate commitment is $0.16. The estimate, reservation and actual provider charge are separate fields and events. If an actual charge exceeds estimate but remains within ceiling, record it and require review of remaining assumptions; if it exceeds per-call or aggregate ceiling, commit the observed evidence, hold campaign and block all further dispatch. A local ceiling cannot guarantee provider billing.

For implementation tests only, the P5-C planning arithmetic uses at most 16,000 measured input tokens and 25,000 output tokens per call: uncached input `16,000 × $0.10/1M = $0.0016`; an intentionally additive cache-write stress allowance `16,000 × $0.125/1M = $0.0020`; output including reasoning `25,000 × $0.50/1M = $0.0125`; stress estimate **$0.0161 per call / $0.1288 for eight**. The proposed ceiling is **$0.02 per call / $0.16 total**. These are neither approved prices nor observed usage/charges. Recheck official rates, exact model token counts, cache treatment and regional/tax terms before any Owner budget authorization. If estimated cost exceeds an approved ceiling, reject before reservation; do not silently truncate or discount.

**Dispatch boundary (future authorization only):** Revalidate live Brief/request and reservation; transactionally change reserved `NOT_STARTED` to `IN_PROGRESS` with a unique dispatch-attempt marker and `DISPATCH_STARTED` event immediately before submission. No second attempt marker or automatic retry. If the process stops after this commit, treat the outcome as ambiguous even if no network call is visible. This specification does not implement that dispatcher.

## 6. State machine and reconciliation

Unreserved slot is displayed as `NOT_STARTED` but has no allowance. Reserved slot starts `NOT_STARTED` and is already consumed. Valid paths:

```text
unreserved NOT_STARTED --atomic reserve--> reserved NOT_STARTED
reserved NOT_STARTED --one dispatch-start commit--> IN_PROGRESS
IN_PROGRESS --complete validated result + accounting--> SUCCEEDED
IN_PROGRESS --definitive no-advisory result + accounting--> FAILED
IN_PROGRESS --timeout/crash/ambiguous result or charge--> UNKNOWN
IN_PROGRESS or UNKNOWN --Owner evidence review--> UNKNOWN + reconciliation event
```

No transition from `UNKNOWN`, `FAILED` or `SUCCEEDED` to an executable state. A refusal or incomplete response is never a successful advisory; if its outcome and billing are definitive, record `FAILED` with sanitized status/usage/charge. If provider acceptance, usage or charge remains uncertain, hold `UNKNOWN`. `FAILED` still consumes the one slot. After restart, any `IN_PROGRESS` is held pending Owner review and may be explicitly marked `UNKNOWN`; it is never reset or auto-resubmitted. A reserved `NOT_STARTED` whose live Context is gone is also **non-executable**: it remains reserved, requires Owner review, and cannot be rebound to a new request. No background recovery worker.

No automatic retry or fallback is permitted in any state, including rate limits, refusals, incomplete output and ambiguous billing.

Owner-attested reconciliation authenticates against the provisioned verifier, records evidence source, provider request ID if known, observed usage/charge and a sanitized conclusion. It may correct accounting metadata and set/keep `UNKNOWN`; it may **not** free a slot or create another allowance. If a full eight-response campaign becomes impossible, use a separately authorized **new campaign version**, never hidden retry or database reset.

## 7. Failure and recovery matrix

| Event | Durable action | Automatic continuation |
|---|---|---|
| Crash before approval/reservation | Unreserved slot; no allowance consumed. On restart, require a fresh live Brief and explicit Owner action. | None. |
| Crash after approval, before reservation | Approval may expire; slot remains unreserved. Rebuild/reapprove explicitly if digest or Context changes. | None. |
| Crash after reservation, before dispatch | Reserved `NOT_STARTED` retained; if original live Context cannot be verified, hold for Owner review. No rebinding or slot reuse. | None. |
| Crash/timeout during or after submission | `IN_PROGRESS` or `UNKNOWN`; retain full reservation and campaign hold. Provider ID is not proof of exactly-once billing. | None. |
| Definitive provider refusal | `FAILED` only with definitive status and accounting; otherwise `UNKNOWN`. No advisory. | None. |
| Incomplete structured response | `FAILED` with definitive billing evidence, else `UNKNOWN`; preserve raw response only in separately approved local evidence store. | None. |
| Missing usage or charge | Do not call it a fully reconciled success. Hold `UNKNOWN` or explicit accounting-pending state outside the five execution states; Owner obtains evidence. | None. |
| Actual charge > estimate | Record charge; review budget assumptions. Full ceiling remains reserved. | No new call until approved review if assumptions changed. |
| Actual charge > slot/aggregate ceiling | Record overrun, set campaign HELD, require Owner decision; cannot undo provider charge. | None. |
| Missing, replaced, corrupt DB/marker | Fail closed before approval/reservation/dispatch; preserve external evidence; manual forensic recovery only. | No automatic re-provision. |
| Duplicate click or concurrent process | Unique slot/approval constraints and `BEGIN IMMEDIATE` permit at most one reservation/dispatch marker. | No retry. |
| Context expiry or changed Brief/request | Reject approval/reservation or pre-dispatch eligibility; stale digest cannot authorize new content. | Fresh explicit approval only for unreserved slot. |
| Local process compromise or Cloud replica | Outside trusted local-process threat model; SQLite file controls alone are insufficient. | No Cloud execution. |

## 8. Auditability and threat model

Append-only event types: `PROVISIONED`, `CAMPAIGN_APPROVED`, `SLOT_APPROVED`, `APPROVAL_REVOKED`, `RESERVED`, `DISPATCH_STARTED`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `USAGE_OBSERVED`, `CHARGE_OBSERVED`, `MANUAL_RECONCILIATION`, `CAMPAIGN_HELD`, `OWNER_DECISION`, `CAMPAIGN_CLOSED`. Write state and event in the same transaction. Check monotonic event sequence and `reserved_micro == SUM(slot ceilings)` on open and before eligibility. An optional event hash chain can detect accidental edits but is **not** a substitute for an external trusted anchor against a local DB administrator.

Assets: synthetic Brief provenance, Owner authorization, eight allowances and aggregate budget. Threats: Demo-user impersonation, stale approval/replay, changed request/case swap, concurrent duplicate submit, crash ambiguity, forged usage/charge, DB replacement, path/symlink substitution, local-process compromise and future Cloud exposure. Controls: separate persisted Owner verifier, exact request/campaign/case binding, live V1.1 Brief validation, one-use approvals, transactional unique reservations, source hash/Run identity checks, durable UNKNOWN hold, file identity marker and sanitized audit events. Residual risk: a privileged local process can alter code/DB or access credentials; provider-side billing and true exactly-once behavior are not guaranteed. Never treat a UI button or session flag as authorization.

## 9. Implementation plan, tests and compatibility

**Suggested future files** (not created by this task): `src/ai_copilot/eight_call_campaign.py` for immutable manifest/slot DTOs and validation; `src/ai_copilot/eight_call_store.py` for explicit provisioning, schema, transactions, events and recovery; `src/ai_copilot/eight_call_gate.py` for trusted Brief/request/Owner checks; `tests/test_ai_copilot_eight_call_campaign.py` and `tests/test_ai_copilot_eight_call_store.py` using temporary local DBs and synthetic-only Briefs. Do not add provider execution in this stage. Keep P3 `ledger.py`, `approval.py`, `execution_gate.py` APIs and original DB schema unchanged; share carefully reviewed pure helpers only if this does not alter P3 behavior.

Minimum tests: exact eight-slot roster and corpus version; genuine EV-08-LR trusted Brief; identical digest in separate slots with distinct approvals; mismatch of every digest-bound field; expired/revoked/reused/Demo-only approval; caller-controlled verifier rejection; concurrent threads and processes; failure injection at each transaction write; aggregate boundary 7th/8th/9th reservation; full-ceiling commitment; restart before reservation, after reservation and after `IN_PROGRESS`; UNKNOWN hold and no resubmission; missing/replaced/corrupt DB; over-ceiling and missing accounting; refusal/incomplete/timeout interpretation; event sanitization and immutability; no provider/SDK/network dispatch; original P3/V1.1/P1/P2 regressions. Use explicit synthetic-only test selection, not unrestricted discovery.

Migration is **additive**: a distinct DB/campaign version and policy, no in-place P3 schema change and no copy/reset of its one-call allowance. If provisioning or migration validation fails, leave both stores fail closed and preserve evidence. Rollback means disabling the new gate and retaining its DB/events for forensic review; it does **not** delete rows, refund observed charges, restore approvals or recreate an allowance. Any backup/restore must retain identity and approval history with an Owner-attested, tested procedure; a copied SQLite file cannot silently become a fresh campaign. Cloud/multi-instance ledger consistency is deferred to P6.

## 10. Prerequisites and decision

**READY FOR OWNER IMPLEMENTATION AUTHORIZATION** for a separately scoped, offline-only eight-call Ledger implementation **if** the Owner accepts this design's just-in-time slot binding, duplicate Request Digest handling and fail-closed treatment of a reserved-but-undispatched slot. This is **not** authorization to provision or use eight allowances. Before any paid acceptance, the Owner must approve a versioned eight-case corpus including EV-08-LR, the exact snapshot or explicit alias policy, request/output/input/timeout settings, current pricing/retention/entitlement, the actual per-call and aggregate ceilings, exact synthetic payload and eight distinct call approvals. The current $0.02/$0.16 figures remain proposals. No production model or paid API execution is enabled.
