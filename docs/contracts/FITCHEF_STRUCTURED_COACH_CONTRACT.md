# FitChef Structured Coach Contract

**Status:** Contract freeze plus structured runtime and support-outcome reconciliation
**Date:** 2026-08-27
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract freezes the next additive FitChef route family without changing
the live mascot canon.

Identifier note:

- umbrella rollout lane: `PR-4`
- GitHub review artifact for this lane: `PR #1159`
- structured coach contract freeze: PR #1214 /
  `29a11e62e38307dd4cc7414bffc159b508878744`
- PRO Distortion Simulator runtime: PR #1215 /
  `70bdbd9e51d977d440b605eed3064c71212cff97`
- VIP Identity Loop Mapper runtime: PR #1870 /
  `7802ed25e99e0a4f346d14487270a037bb5ec97a`

The current public mascot routes under `/api/v1/insight/fitchef*` remain live,
canonical, and unmigrated. The structured coach family stays additive.

As of PR #1215, the first bounded PRO structured coach runtime is implemented
and OpenAPI-exposed:

- `POST /api/v1/pro/fitchef/explain`

As of PR #1870, the first bounded VIP structured coach runtime is implemented
and OpenAPI-exposed:

- `POST /api/v1/vip/fitchef/insight`

The remaining structured coach paths stay contract-frozen follow-ups so later
runtime PRs do not need to reopen route naming, tier semantics, or client
envelope rules.

## Relationship to the live mascot canon

- Live mascot routes remain canonical:
  - `POST /api/v1/insight/fitchef`
  - `POST /api/v1/insight/fitchef/weekly-reflection`
  - `POST /api/v1/insight/fitchef/slip-support`
- This contract is additive. It does not rename, deprecate, or proxy-migrate
  the live mascot family.
- The live mascot family remains governed by:
  - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
  - `docs/contracts/API_CANONICAL_MAP.md`
  - `app/routers/fitchef_insight.py`

## Route family freeze

### PRO structured coach surfaces

- `POST /api/v1/pro/fitchef/explain`
- `POST /api/v1/pro/fitchef/recommend` — landed via PR #2320 /
  `f95a329d899d5ac4fa73f198e90cfed44d0fc45c`

### Landed VIP structured coach surface

- `POST /api/v1/vip/fitchef/insight`

### Remaining VIP structured coach follow-ups

- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`

The remaining unimplemented paths are contract-frozen for future implementation
PRs and must stay additive to the live mascot family.

## Current web channel posture

At the named PR #2337 evidence cutoff (`2026-08-26T22:19:41Z`, merge
`d5ef261473bb76fcaa57a6a982013a2424263dfa`), bounded examples of the current
free web channel posture were BMI, wellness and nutrition education, bounded
informational chat, acquisition and iOS referral, and the FitChef
support-choice consumer. The web product is not advertising-only: its complete
FREE product posture includes the BMI calculator questionnaire, FREE results,
and allowed education and information surfaces, alongside bounded chat,
marketing and capability demonstration, and the iOS handoff. These examples
describe the recorded channel posture at that cutoff only. They authorize no
unnamed paid web capability, new route, or future carrier and are not asserted
as an exhaustive repository-wide inventory. This is a channel-posture
statement, not a product-tier grant.

For this phase, `free web channel` means that the web client does not originate
a FitChef sale, checkout, or paid entitlement and has no client-side billing or
entitlement authority. It does **not** grant `FREE` tier access to the protected
`POST /api/v1/pro/fitchef/recommend` route. That route remains a canonical,
server-authorized `PRO` surface; missing or disallowed authorization continues
to fail closed with `401` or `403` under the backend contract.

The current phase neither authorizes nor permanently prohibits a future full or
paid web FitChef surface. A separate, exact human `GO` is necessary but not
sufficient for such a carrier. Server-authoritative billing and entitlement
architecture, a bounded carrier, and the ordinary architecture, security,
contract, test, review, and merge gates remain independently required before
any future activation.

This posture reconciliation preserves the landed PR #2337 implementation. It
adds no runtime, payment, entitlement, persistence, navigation, execution, or
plan-mutation authority.

PR #2337 remains historical `transport=none` evidence for support outcomes.
The web support-choice acknowledgement stays local and no web handler calls
`POST /api/v1/pro/fitchef/recommend/outcome`. The explicit current channel
decision assigns the first persisted-outcome consumer to iOS; it does not
remove or narrow the complete FREE web product posture above.

## Support-outcome ledger contract

The additive backend intake is:

- `POST /api/v1/pro/fitchef/recommend/outcome`
- default-off flag: `FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER=false`
- scoped rate limit: `RATE_LIMIT_FITCHEF_SUPPORT_OUTCOME=30/minute`

The request is one closed four-field object:

```json
{
  "schema_version": "fitchef_support_outcome_v1",
  "support_need": "daily_structure",
  "outcome": "acknowledged",
  "client_event_id": "opaque-client-event-id"
}
```

`support_need` is exactly `daily_structure` or `weekly_structure`; `outcome` is
exactly `acknowledged` or `dismissed`. `client_event_id` is an opaque 16–128
character identifier matching `^[A-Za-z0-9][A-Za-z0-9_-]{15,127}$`. Unknown,
sensitive, targeting, free-text, plan, profile, timestamp, and metadata fields
are rejected rather than ignored.

The response contains only the schema version and `state=recorded|replayed`.
It never returns the credential subject, event identifier, target surface,
timestamp, or an internal integrity field. Stable status semantics are `200`
for a new or exact replay, canonical `401`/`403` for PRO auth, `409` for a
divergent same-subject event-id replay, `422` for media/JSON/schema failure,
`429` for the scoped intake limit, and `503` for the disabled feature or an
unavailable store.

Admission order is canonical PRO auth, scoped rate limit, feature flag, exact
JSON media type, actual streamed body limit (4096 bytes), duplicate-free and
depth-bounded JSON, strict DTO validation, credential-derived bigint subject,
canonical handoff target derivation, RLS context, and race-safe persistence.
The target is derived only by `build_fitchef_support_handoff`; no second mapping
switch exists.

Each row means only an accepted authenticated client-reported outcome assertion
plus a server-derived credential subject and one client event id. It does not
prove a human UI click, a prior successful `/recommend` response, consent,
understanding, navigation, plan execution or mutation, goal change,
effectiveness, retention, conversion, or causality. `acknowledged` is not a
consent or understanding claim.

The SQL ledger is append-only and subject-isolated. It has no `users.id`
foreign key or cascade, public history endpoint, free-form/JSON payload,
update surface, TTL, scheduler, provider, RAG, LLM, planner, Markov, or Bayesian
authority. PostgreSQL uses forced RLS; SQLite/test paths retain exact subject
predicates. Support-led export/delete receives a separate explicit credential
subject namespace, independent from account `user_id`, and no public DSAR
endpoint is introduced.

The low-cardinality metric has exactly the closed dimensions
`2 support_need × 2 outcome × 3 result`. `rejected` is emitted only for a
divergent `409`; the metric has no subject, event-id, credential, path, error,
plan, goal, or timestamp label. The flow directly sends no outcome field or row
to an AI provider or other third-party processor; aggregate metrics remain
subject to configured telemetry policy.

## Internal iOS recommendation/outcome capability

ER-IOS-2 is one thin, testable capability with no production presentation
owner. `FitChefSupportFlowScreen` is constructed only by its own deterministic
DEBUG previews; Home, tabs, routers, deep links, and other production Swift
files do not construct it.

The internal flow contract is:

1. The user locally chooses `daily_structure` or `weekly_structure`; selection,
   rendering, and pre-result dismissal perform no network call.
2. Explicit confirmation sends only that need through the existing
   `APIClient` to `POST /api/v1/pro/fitchef/recommend`.
3. The feature accepts only an exact, fail-closed descriptor whose need echoes
   the request and whose backend-owned target remains an inert localized text
   label in previews.
4. The first explicit result-stage Thanks or Not now action maps internally to
   `acknowledged` or `dismissed`, creates one in-memory opaque event id, and
   sends the exact four-field outcome body.
5. Only an exact `recorded` or `replayed` receipt permits persistence-success
   copy. Retryable failures require a new gesture and reuse the same attempt and
   credential; `409` and `422` are terminal, while `401` and `403` require a new
   lifecycle.

The client reuses the exact credential that successfully obtained the
descriptor for the matching outcome attempt. The credential and event id are
not logged or durably stored. The carrier has no automatic retry, outbox,
analytics, target navigation, target invocation, entitlement or billing
inference, plan lookup, plan execution, or plan mutation.

No feature flag or Home action is introduced because neither has a live caller
in ER-IOS-2. ER-IOS-3 is the separately governed future owner for one unified
FitChef Coach destination. Only after ER-IOS-3 lands may ER-IOS-4 add one Home
FitChef Coach button; ER-IOS-4 explicitly excludes a Home redesign. Neither
future lane is implemented or authorized by this capability PR.

Structural nonreachability does not activate either backend feature flag,
provision a credential, prove entitlement, authorize staging or production
writes, or satisfy the separate activation-readiness work.

## Wave-aligned capability mapping

The current contract-freeze lane now aligns to the docs-first **CBT Coaching Wave**
without changing route naming or public mascot canon.

### PRO mapping

- `POST /api/v1/pro/fitchef/explain`
  - landed first bounded capability: `Distortion Simulator`
  - shape direction: structured thought-record style reframing tool
- `POST /api/v1/pro/fitchef/recommend`
  - landed via PR #2320: deterministic support handoff
  - closed request needs: `daily_structure` and `weekly_structure`
  - shape: one descriptor-only product-surface action, not open-ended chat,
    plan adaptation, navigation, or downstream execution

### VIP mapping

- `POST /api/v1/vip/fitchef/insight`
  - landed first bounded capability: `Identity Loop Mapper`
  - shape direction: belief -> behavior -> payoff -> replacement action
- `POST /api/v1/vip/fitchef/week-repair`
  - intended first bounded capability: identity-aware repair after slips
  - shape direction: recovery and continuity, not punishment
- `POST /api/v1/vip/fitchef/chat`
  - remains a future broader structured coach surface
  - must not become the first implementation target ahead of bounded structured tools

## Tier policy freeze

- `FREE`
  - may receive only bounded static or template guidance outside this route
    family
  - must not receive open-ended FitChef coach runtime
- `PRO`
  - may use `explain` and `recommend`
  - must not receive VIP-only long-form insight, open-ended chat, or week
    repair
- `VIP`
  - may use `insight`, `chat`, and `week-repair`
  - may depend on PRO-calculated domain context, but must not replace canonical
    nutrition or planner engines

### Cross-tier and disallowed-access semantics

Future implementations must keep cross-tier access fail-closed:

- disallowed tier or missing entitlement:
  - `403`
  - JSON error envelope with stable `detail`
- feature-disabled or execution-disabled route:
  - `503`
  - JSON error envelope with stable `detail`
- rate-limit rejection:
  - `429`
  - JSON error envelope with stable `detail`
- provider timeout or unavailable downstream:
  - `504` or `503`
  - JSON error envelope with stable `detail`

The contract direction for those failures is the same safe JSON envelope style
already used by the live mascot family: no raw provider traces, no client-side
inference from prose, and no fail-open downgrade to a broader tier.

## Guard and execution policy

Future implementation PRs must keep the current FitChef guard precedence
aligned with the live mascot routers:

1. tier and feature gate
2. execution-mode gate
3. input guard
4. quota / policy / provider path

The deterministic `POST /api/v1/pro/fitchef/recommend` route is the bounded
non-executing exception to steps 2-4. Its exact order is:

`POST /api/v1/pro/fitchef/recommend` returns one deterministic, non-executing
product-surface handoff selected solely from the request's explicit
`support_need`. It does not inspect a plan, history, adherence, goal, or prior
FitChef response; infer friction or intent; call RAG, an AI provider, or an LLM;
invoke the target surface; or create or change a plan.

1. canonical `require_pro_tier`
2. shared `FEATURE_FITCHEF_STRUCTURED_COACH` flag
3. raw JSON parse and `FitChefSupportHandoffRequest` validation
4. pure two-branch descriptor selection

After auth and the shared feature flag, the route reads `Content-Type` once,
partitions once at the first `;`, and compares the untrimmed base token
case-insensitively to exactly `application/json`. The parameter tail is ignored.
Missing, empty, leading/base-trailing whitespace, `application/json ;...`,
`+json`, and other media types return the existing stable JSON `422` before
`request.json()`, DTO validation, or mapping; no `415` is introduced.

It documents only `200`, `401`, `403`, `422`, and `503`. It does not use an
execution-mode gate, input guard, rate limit, monthly quota, provider, RAG,
planner, persistence, analytics, navigation, or target invocation. This narrow
exception does not weaken any expensive or AI-backed FitChef route.

Additional freeze points:

- live mascot routes remain on `RATE_LIMIT_INSIGHT`
- expensive structured coach surfaces must stay fail-closed on rate limit,
  quota, provider unavailability, and unsafe input
- future expensive or provider-backed runtime paths must preserve explicit
  `429`, `503`, and `504` documentation and deterministic tests

## Structured response direction

Future public FitChef structured-coach responses must be schema-driven and
renderable by thin clients without parsing prose into product state.

The landed PRO Distortion Simulator route is already governed by
`FitChefDistortionSimulatorResponse`, with `scenario`, `distortion_labels`,
`why_it_matches`, `evidence_for`, `evidence_against`, `balanced_reframe`,
`next_small_action`, `sources`, `confidence`, `warnings`, `quota_state`,
`transparency_notice_id`, and `wellness_boundary`.

The landed VIP Identity Loop Mapper runtime is schema-frozen by
`FitChefIdentityLoopMapperResponse`, with `scenario`, `identity_loop`,
`identity_shift_statement`, `replacement_action`, `repair_if_slip`, `sources`,
`confidence`, `warnings`, `quota_state`, `transparency_notice_id`, and
`wellness_boundary`.

The deterministic PRO support handoff landed via PR #2320 / `f95a329d899d5ac4fa73f198e90cfed44d0fc45c` and is schema-frozen by
`FitChefSupportHandoffRequest`, `FitChefSupportHandoffActionV1`, and
`FitChefSupportHandoffResponse`:

- `daily_structure` maps only to `pro_daily_plate`
- `weekly_structure` maps only to `pro_weekly_plan`
- `action.action_type` is always `handoff_to_product_surface`
- `user_confirmation_required=true`
- `execution_authority=false`
- `plan_mutation_authority=false`
- `used_llm=false`
- `wellness_boundary=wellness_planning_only`

These fields have the following frozen meaning:

- `recommend` means only enum-to-surface selection. It does not mean best
  choice, ranking, personalization, or inferred suitability.
- `support_need` is the caller's explicit request-local choice. It is not a
  detected problem, goal authority, inferred friction, or persisted preference.
- `user_confirmation_required=true` requires a separate user gesture before a
  client uses the handoff. It is not plan approval.
- `execution_authority=false` forbids automatic target invocation, screen
  opening, navigation, or generation by the server or client.
- `plan_mutation_authority=false` means no plan lookup, creation, repair,
  replacement, update, persistence, or deletion and makes no claim that a plan
  exists.
- `used_llm=false` is backed by the pure service boundary and negative-call
  tests, not treated as sufficient evidence by itself.
- `target_surface` is a declarative backend slug. It does not guarantee that a
  client screen exists or that a downstream request is available to this user.

The response contains no free text, history, reframe, or plan. Its product
utility remains unmeasured, and the surface slug does not claim that any client
has implemented navigation.

The selector itself performs no database or analytics work after authorization.
Canonical `require_pro_tier` may read persisted subscription state, and existing
middleware may still emit operational metrics; neither is selector-side product
state or plan mutation.

The generic envelope direction below is for later unimplemented structured-coach
follow-ups that do not already have a frozen response schema. It must not
override landed OpenAPI schemas or schema-frozen follow-up lanes.

### Internal Distortion Simulator field-assurance boundary

The E1-04 field-assurance record is internal and negative-only. It binds the
six existing Distortion Simulator fields to one request-local, sanitized and
PII-redacted source snapshot without adding a public response key or changing
the public OpenAPI/client contract. Only `balanced_reframe` may carry opaque
candidate occurrence references.

A candidate reference proves only that the identified occurrence was present in
the frozen, sanitized, PII-redacted prompt snapshot available when provider
generation was attempted.
It does **not** prove that the final field originated from that occurrence:
deterministic normalization or wellness fallback may replace provider text. It
also does not prove semantic support, truth, entailment, contradiction review,
or source quality. Therefore v1 keeps `adjudicated_support_status=null`,
`conflict_adjudicated=false`, and `support_claimed_count=0`. Duplicate source
identities, snapshot drift, missing links, and local fingerprint failure degrade
to explicit negative states with no candidate references.

This assurance has no public-response, provider-retry, cache-admission,
knowledge-promotion, or plan-mutation authority. It does not invoke an NLI or
provider judge, reuse canonical adjudication helpers, write evidence/cache/DB
state, or make the retrieved corpus canonical truth. A future positive semantic
support verifier requires the separate backlog gate and a terminal human
decision before implementation.

E1-04 is in-process contract groundwork observed only by bounded local
prospective evaluation. It supplies no continuous deployed-health signal and
must not be used as evidence of production traffic health or terminal rollout
success. The internal assessment therefore remains absent from public responses,
telemetry, and privileged audit records.

Implementation anchors:

- `app.schemas.fitchef.FitChefDistortionFieldAssuranceAssessmentV1`
- `app.services.fitchef_claim_evidence_assurance`
- `app.services.fitchef_runtime.run_distortion_simulator_task`
- `tests.test_fitchef_claim_evidence_assurance`

### CBT Coaching Wave framework

Future bounded coaching surfaces should align to the default framework:

`Trigger -> Thought -> Distortion -> Reframe -> Action -> Reflection`

This framework is additive guidance for future implementation PRs. It does not change the
status of current routes or current public envelopes in this contract lane.

### Future non-frozen follow-up top-level direction

- `mode: str`
- `title: str`
- `summary: str`
- `bullets: list[str]`
- `actions: list[FitChefStructuredAction]`
- `source_modules: list[str]`
- `used_llm: bool`
- `disclaimers: list[str]`
- `transparency_notice_id: str`
- `wellness_boundary: str`

### Action contract

`actions` must be typed and routable, not free-form text. Each action must map
to an existing product flow.

Minimum direction:

- `type: str`
- `label: str`
- `payload: object`

### Minimal schema sketch

```json
{
  "mode": "pro_structured" ,
  "title": "Protein below target",
  "summary": "Your lunch pattern is the main driver today.",
  "bullets": [
    "Lunch protein remained below the daily target.",
    "Dinner still has room for a corrective swap."
  ],
  "actions": [
    {
      "type": "open_meal",
      "label": "Review dinner",
      "payload": {
        "meal_slot": "dinner"
      }
    }
  ],
  "source_modules": [
    "nutrition.targets",
    "planner.daily"
  ],
  "used_llm": false,
  "disclaimers": [
    "General wellness guidance only"
  ],
  "transparency_notice_id": "fitchef_structured_v1",
  "wellness_boundary": "non_diagnostic_guidance"
}
```

### Client contract rules

- UI must render structured DTOs or frozen response envelopes only.
- UI must not infer entitlement, planner truth, or route navigation by parsing
  raw prose.
- Web and iOS clients must treat future OpenAPI schemas as the source for
  generated request/response types once implementation begins.

## Runtime boundary freeze

Future structured coach implementation must:

- reuse canonical backend outputs for targets, planner state, adherence, and
  shopping context
- avoid any new nutrition math outside canonical engines
- keep LLM output advisory and non-authoritative
- keep fallback or template responses available whenever LLM execution is
  unavailable, disallowed, or disabled

## Implementation follow-up order

### Landed contract/runtime sequence

- PR #1214 froze the structured coach contract and route family.
- PR #1215 landed the feature-gated PRO `Distortion Simulator` runtime at
  `POST /api/v1/pro/fitchef/explain`.
- PR #1870 landed the feature-gated VIP Identity Loop Mapper runtime at
  `POST /api/v1/vip/fitchef/insight` with the frozen
  `FitChefIdentityLoopMapperResponse` envelope.
- PR #2320 landed the feature-gated deterministic PRO support handoff at
  `POST /api/v1/pro/fitchef/recommend` on 2026-08-25 at
  `f95a329d899d5ac4fa73f198e90cfed44d0fc45c`, with frozen DTOs and deterministic
  route tests. Business utility remains unmeasured; the route emits no analytics,
  navigates nowhere, mutates no plan, and executes no action.

### Later VIP structured follow-ups

- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`
- entitlement, quota, and degraded-mode guarantees

## Explicit non-goals

- renaming or migrating `/api/v1/insight/fitchef*`
- adding any new backend runtime surface beyond the landed PRO explain route, the
  landed PR #2320 support-handoff route, and the bounded VIP Identity
  Loop Mapper route
- adding a production iOS presentation owner, FitChef Coach destination, Home
  button or redesign, staging/production activation, target navigation, or any
  entitlement or plan authority
- mixing website brand rollout or App Store assets into this contract lane

## Evidence anchors

Use stable symbols rather than line-number evidence for long-lived contract
truth:

- `app.main.ensure_canonical_app_bootstrap`
- `app.routers.fitchef_structured.fitchef_distortion_simulator`
- `app.routers.fitchef_structured.fitchef_support_handoff`
- `app.services.fitchef_support_handoff.build_fitchef_support_handoff`
- `app.routers.fitchef_insight.router`
- `app.routers.fitchef_insight.fitchef_mascot_insight`
- `app.routers.fitchef_insight.fitchef_weekly_reflection`
- `app.routers.fitchef_insight.fitchef_slip_support`
- `app.routers.cbt_insight.CBTInsightResponse`
- `app.services.fitchef_runtime.run_distortion_simulator_task`
- `app.services.fitchef_runtime.run_identity_loop_mapper_task`
- `app.services.fitchef_runtime.run_mascot_insight_task`
- `app.services.fitchef_runtime.run_weekly_reflection_task`
- `app.services.fitchef_runtime.run_slip_support_task`
- `app.schemas.fitchef.FitChefDistortionSimulatorInput`
- `app.schemas.fitchef.FitChefSlipSupportTaskEnvelope`
- `app.schemas.fitchef_coaching.FitChefIdentityLoopMapperRequest`
- `app.schemas.fitchef_coaching.FitChefIdentityLoopMapperResponse`
- `app.schemas.fitchef_coaching.FitChefDistortionSimulatorResponse`
- `tests.test_fitchef_structured_api.TestFitChefDistortionSimulatorRoute.test_openapi_documents_distortion_simulator_contract`
- `tests.test_fitchef_structured_api.TestFitChefIdentityLoopMapperRoute.test_openapi_documents_identity_loop_mapper_contract`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
