# FitChef Structured Coach Contract

**Status:** Contract freeze for additive structured coach surfaces
**Date:** 2026-03-14
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract freezes the next additive FitChef route family without changing
the live mascot canon.

Identifier note:

- umbrella rollout lane: `PR-4`
- GitHub review artifact for this lane: `PR #1159`

The current public mascot routes under `/api/v1/insight/fitchef*` remain live,
canonical, and unmigrated in this phase. PR-4 defines future structured coach
surfaces under `/api/v1/pro/fitchef/*` and `/api/v1/vip/fitchef/*` so later
runtime PRs can implement them without reopening route naming, tier semantics,
or client-envelope rules.

This is a docs-only contract phase. It does not add runtime behavior, OpenAPI
paths, or client integrations yet.

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

### PR-5 domain shell

- context builder
- policy layer
- template and fallback layer
- safety layer
- service orchestration shell

### PR-6 PRO runtime

- `POST /api/v1/pro/fitchef/explain`
- `POST /api/v1/pro/fitchef/recommend`
- deterministic route tests
- analytics and action-routing contracts

### PR-7 VIP runtime

- `POST /api/v1/vip/fitchef/insight`
- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`
- entitlement, quota, and degraded-mode guarantees

## Explicit non-goals

- renaming or migrating `/api/v1/insight/fitchef*`
- shipping runtime code in this PR
- adding OpenAPI paths in this PR
- adding frontend or iOS FitChef runtime consumers
- mixing website brand rollout or App Store assets into this contract lane

## Evidence anchors

- `app/routers/fitchef_insight.py:45`
- `app/routers/fitchef_insight.py:58`
- `app/routers/fitchef_insight.py:133`
- `app/routers/fitchef_insight.py:214`
- `app/routers/cbt_insight.py:87`
- `app/services/fitchef_runtime.py:264`
- `app/services/fitchef_runtime.py:435`
- `app/schemas/fitchef.py:33`
- `app/schemas/fitchef.py:121`
- `app/schemas/fitchef_coaching.py:60`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:21`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md:11`
