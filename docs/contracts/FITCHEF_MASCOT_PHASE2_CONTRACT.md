# FitChef Mascot Phase 2 Contract

**Status:** Contract freeze for Phase 2 mascot coaching rollout
**Date:** 2026-03-09
**Owner:** @katsiaryna_kavaleuskaya

## Summary

FitChef Phase 2 is the first public mascot-coaching wave built on top of the
existing FitChef Phase 1 backend runtime. This wave adds text-only mascot
coaching surfaces under the canonical insight namespace and keeps all broader
automation work explicitly deferred.

## Canonical namespace and policy

- Canonical route family: `/api/v1/insight/fitchef*`
- Canonical tier policy: VIP-only
- Canonical namespace exception: this work extends the existing
  `/api/v1/insight` exception documented in
  `docs/contracts/API_CANONICAL_MAP.md`
- Forbidden in this wave:
  - `/api/v1/vip/insight*`
  - export orchestration
  - realtime progress / streaming fan-out
  - broader multi-tool autonomy
  - image upload / CV food recognition

## Approved Phase 2 rollout order

1. Mascot insight endpoint
2. Weekly reflection endpoint
3. Slip-support endpoint

Each slice must land as a separate PR and keep the existing `/api/v1/insight`
surface stable.

## Current runtime anchors

- `app/services/fitchef_runtime.py`
- `app/routers/cbt_insight.py`
- `app/routers/pro.py`
- `app/routers/shopping_list_pro.py`
- `docs/contracts/API_CANONICAL_MAP.md`
- `docs/design/NUTRITION_COACHING_DESIGN.md`
- `core/insight/creative_scientific_innovations.md`

## Public contract freeze

Approved contract paths for this wave — not yet implemented; runtime delivery is
deferred to follow-up PRs:

- `POST /api/v1/insight/fitchef`
- `POST /api/v1/insight/fitchef/weekly-reflection`
- `POST /api/v1/insight/fitchef/slip-support`

Shared constraints:

- VIP guard required
- Same LLM rate-limit class as canonical insight
- Same monthly quota enforcement order as canonical insight
- Policy/audit checks must execute before provider calls
- Wellness-language and philosophy validation must remain fail-closed

## HTTP contract freeze

All FitChef mascot endpoints inherit the canonical insight HTTP behavior and use
`Content-Type: application/json`.

### 1. `POST /api/v1/insight/fitchef`

- Request body:
  - `query: str`
- `200` response envelope:
  - `message: str`
  - `scenario: "mascot_insight"`
  - `sources: list[object]`
  - `confidence: float`
  - `warnings: list[str]`
  - `action_items: list[str]`
  - `quota_state: str`
  - `transparency_notice_id: str`
  - `wellness_boundary: str`

### 2. `POST /api/v1/insight/fitchef/weekly-reflection`

- Request body:
  - `summary: str`
  - `goal: str | null`
- `200` response envelope:
  - same shared envelope as mascot insight
  - `scenario: "weekly_reflection"`

### 3. `POST /api/v1/insight/fitchef/slip-support`

- Request body:
  - `event_text: str`
  - `goal: str | null`
- `200` response envelope:
  - same shared envelope as mascot insight
  - `scenario: "slip_support"`

### Shared error contract

- Error responses remain JSON and inherit the canonical insight failure shape:
  - stable machine-readable error code
  - safe human-readable message
  - structured `detail` field
- Required baseline failures for each route:
  - `403` tier guard failure
  - `429` rate-limit failure
  - `503` feature-disabled or provider-unavailable failure
- Policy gate, audit signing, quota checks, and validation must execute before
  provider generation on every mascot route.

### Test freeze for follow-up runtime PRs

Each endpoint PR must include:

- contract tests for `200` plus representative failure cases
- one happy-path integration test
- deterministic guarantees for any provider/path selection or response shaping
- assertions for `Content-Type` and standardized error fields

## Explicit non-goals

These remain outside the mascot wave and must not be described as live:

- export generation or export delivery
- realtime progress updates
- websocket or push fan-out
- autonomous multi-tool pipelines
- image/CV ingestion
- shopping/export orchestration follow-ups

## Evidence anchors

- `docs/contracts/API_CANONICAL_MAP.md`
- `docs/design/NUTRITION_COACHING_DESIGN.md`
- `core/insight/creative_scientific_innovations.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
