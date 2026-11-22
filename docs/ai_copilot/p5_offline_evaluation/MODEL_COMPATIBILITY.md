# GPT-6 Luna compatibility assessment (offline only)

Evidence date: 2026-11-21 UTC. Sources: current repository implementation and existing V1.2 reports only. No current model documentation, account access or live API was consulted.

| Requirement | Verified repository behavior | GPT-6 Luna status |
|---|---|---|
| API model ID and dated snapshot | `build_request` requires an explicit ASCII `model_snapshot` and never chooses a default (`src/ai_copilot/provider.py`). | **NOT VERIFIED.** The Owner supplied the display name “GPT-6 Luna,” not a documented API ID or snapshot. No ID is asserted here. |
| Responses API | `OpenAIResponsesAdapter.call_arguments` prepares Responses-shaped `model`, `instructions`, `input`, `text.format`, `max_output_tokens`, `store=false`, no tools/stream/background; `required_client_options` requests zero retries and a timeout. | **NOT VERIFIED for Luna.** The adapter is an offline argument mapper; `execute()` raises `ProviderBlocked`. |
| Structured Outputs | P1 supplies a versioned closed JSON Schema as strict `text.format`; local `validate_response` independently parses and checks it. | **NOT VERIFIED for Luna.** Support for this schema and snapshot must be checked before a paid call. |
| Strict JSON Schema subset | `SCHEMA` requires nested objects, `additionalProperties:false`, enums, arrays, patterns, numeric values and bounded strings. Existing tests validate it locally with `jsonschema`. | **NOT VERIFIED.** Local schema validity does not prove provider-side strict-schema acceptance. |
| Output limit | `build_request` accepts explicit `max_output_tokens` from 1 to 2500; request body has a 64 KiB byte ceiling. | Luna's actual context window, output cap and tokenization are **NOT VERIFIED**. No input token ceiling is encoded; input usage must be measured against a verified snapshot. |
| Refusal, incomplete and unknown outcomes | P2 mock interpreter distinguishes `REFUSED`, `INCOMPLETE`, `DEFINITIVE_ERROR`, `UNKNOWN_OUTCOME`; P1 validates only successful structured content. | Real Luna/SDK response shapes, timeout exceptions and usage fields **REQUIRE FUTURE LIVE ACCEPTANCE**. |
| Privacy and cost | `provider_brief()` sends a documented allowlist projection; request digest binds full local Brief digest, projected digest, instruction/schema/privacy versions, limits and no-tool/no-store/no-retry settings. P3 cost policy defaults unset. | Provider processing/retention, price, measured usage and actual charge **NOT VERIFIED**. `store=false` is not a zero-retention guarantee. |

The historical feasibility plan discusses a different provisional model; that is **not** a Luna compatibility claim and is superseded by the Owner's first-candidate decision for this preparation task. The installed environment previously had no OpenAI SDK; this task does not install or use one. No adapter change or model-specific workaround is made from an unverified assumption.

## Non-production configuration proposal

| Setting | Proposed preparation state |
|---|---|
| Candidate display name | GPT-6 Luna (Owner-selected first candidate). |
| Documented API model ID | **NOT VERIFIED** in existing repository evidence; no guessed ID. |
| Production snapshot | **UNDECIDED**; no hard-coded production default. |
| Input limit | Exact canonical request is capped at 64 KiB by current builder; token count/context fit require snapshot verification. |
| Output token cap | Choose an explicit value within the existing `1..2500` request bound after compatibility review; no production value selected here. |
| Timeout | Choose an explicit value within the existing `>0..60` second bound; no automatic retry. |
| Pricing basis and maximum cost | **NOT SET**; Owner must approve both before reservation. |
| API execution authorization | **NOT GRANTED**; real adapter remains blocked. |

When verified rates exist, calculate a conservative estimate as `(measured_input_tokens × verified_input_rate + approved_max_output_tokens × verified_output_rate) / 1,000,000 + other verified billable components`, with units and rounding stated in the pricing basis. Use the exact projected request and selected snapshot for token measurement; do not infer prices, reasoning-token treatment or cached-input discounts. Round the reservation estimate upward at the approved billing precision and require it to fit the Owner's explicit ceiling. Actual provider usage and charge must later be recorded separately; the estimate is not a billing observation.

## Future compatibility gate

Before any P5 paid authorization, obtain current official evidence for the exact API ID/snapshot, Responses and strict Structured Outputs support, output/input limits, billing units, data handling and the selected SDK version. Validate the exact current P1 schema against that snapshot without weakening evidence checks. Record any incompatibility and ask the Owner; do not switch to a higher-tier model automatically.
