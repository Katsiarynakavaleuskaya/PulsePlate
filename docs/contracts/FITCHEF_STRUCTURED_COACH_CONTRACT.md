# FitChef Structured Coach Contract

**Status:** Contract freeze plus landed PRO Distortion Simulator reconciliation
**Date:** 2026-03-21
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

The current public mascot routes under `/api/v1/insight/fitchef*` remain live,
canonical, and unmigrated. The structured coach family stays additive.

As of PR #1215, the first bounded PRO structured coach runtime is implemented
and OpenAPI-exposed:

- `POST /api/v1/pro/fitchef/explain`

The first bounded VIP structured coach surface remains a contract-frozen future
rollout target:

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
- `POST /api/v1/pro/fitchef/recommend`

### VIP structured coach surfaces

- `POST /api/v1/vip/fitchef/insight`
- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`

These paths are contract-frozen for future implementation PRs and must stay
additive to the live mascot family.

## Wave-aligned capability mapping

The current contract-freeze lane now aligns to the docs-first **CBT Coaching Wave**
without changing route naming or public mascot canon.

### PRO mapping

- `POST /api/v1/pro/fitchef/explain`
  - landed first bounded capability: `Distortion Simulator`
  - shape direction: structured thought-record style reframing tool
- `POST /api/v1/pro/fitchef/recommend`
  - intended first bounded capability: action-oriented follow-up after reframing
  - shape direction: structured next-step recommendation, not open-ended chat

### VIP mapping

- `POST /api/v1/vip/fitchef/insight`
  - intended first bounded capability: `Identity Loop Mapper`
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

Additional freeze points:

- live mascot routes remain on `RATE_LIMIT_INSIGHT`
- expensive structured coach surfaces must stay fail-closed on rate limit,
  quota, provider unavailability, and unsafe input
- future runtime paths must preserve explicit `429`, `503`, and `504`
  documentation and deterministic tests

## Structured response direction

Future public FitChef structured-coach responses must be schema-driven and
renderable by thin clients without parsing prose into product state.

### CBT Coaching Wave framework

Future bounded coaching surfaces should align to the default framework:

`Trigger -> Thought -> Distortion -> Reframe -> Action -> Reflection`

This framework is additive guidance for future implementation PRs. It does not change the
status of current routes or current public envelopes in this contract lane.

### Required top-level direction

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

### Remaining PRO follow-up

- `POST /api/v1/pro/fitchef/recommend`
- deterministic route tests
- analytics and action-routing contracts

### Next active VIP runtime lane

- `POST /api/v1/vip/fitchef/insight`

This is the bounded Identity Loop Mapper target for the next substantive VIP
runtime PR.

### Later VIP structured follow-ups

- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`
- entitlement, quota, and degraded-mode guarantees

## Explicit non-goals

- renaming or migrating `/api/v1/insight/fitchef*`
- adding any new runtime surface in this docs reconciliation beyond the already-landed
  `POST /api/v1/pro/fitchef/explain`
- adding frontend or iOS FitChef runtime consumers
- mixing website brand rollout or App Store assets into this contract lane

## Evidence anchors

Use stable symbols rather than line-number evidence for long-lived contract
truth:

- `app.main.ensure_canonical_app_bootstrap`
- `app.routers.fitchef_structured.fitchef_distortion_simulator`
- `app.routers.fitchef_insight.router`
- `app.routers.fitchef_insight.fitchef_mascot_insight`
- `app.routers.fitchef_insight.fitchef_weekly_reflection`
- `app.routers.fitchef_insight.fitchef_slip_support`
- `app.routers.cbt_insight.CBTInsightResponse`
- `app.services.fitchef_runtime.run_distortion_simulator_task`
- `app.services.fitchef_runtime.run_mascot_insight_task`
- `app.services.fitchef_runtime.run_weekly_reflection_task`
- `app.services.fitchef_runtime.run_slip_support_task`
- `app.schemas.fitchef.FitChefDistortionSimulatorInput`
- `app.schemas.fitchef.FitChefSlipSupportTaskEnvelope`
- `app.schemas.fitchef_coaching.FitChefIdentityLoopMapperRequest`
- `app.schemas.fitchef_coaching.FitChefDistortionSimulatorResponse`
- `tests.test_fitchef_structured_api.TestFitChefDistortionSimulatorRoute.test_openapi_documents_distortion_simulator_contract`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
