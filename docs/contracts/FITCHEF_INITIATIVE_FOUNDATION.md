# FitChef Initiative Foundation

**Status:** Umbrella initiative foundation contract
**Date:** 2026-03-12
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This foundation contract opens the next FitChef initiative as a governed
umbrella without breaking the current live mascot canon.

The immediate goal is to separate work into clean PR families:

1. foundation and backlog governance
2. visual and App Store system work
3. structured coach contracts and runtime

The initiative is additive. It does not migrate or rename the existing public
FitChef mascot routes during the foundation or visual waves.

## Current live canon

The live public FitChef routes remain:

- `POST /api/v1/insight/fitchef`
- `POST /api/v1/insight/fitchef/weekly-reflection`
- `POST /api/v1/insight/fitchef/slip-support`

These routes are already registered under the canonical insight namespace by
`app.routers.fitchef_insight.router`, with the stable handler anchors
`app.routers.fitchef_insight.fitchef_mascot_insight`,
`app.routers.fitchef_insight.fitchef_weekly_reflection`, and
`app.routers.fitchef_insight.fitchef_slip_support`.

The current runtime anchors are stable service symbols:
`app.services.fitchef_runtime.run_mascot_insight_task`,
`app.services.fitchef_runtime.run_weekly_reflection_task`,
`app.services.fitchef_runtime.run_slip_support_task`,
`app.services.fitchef_runtime.run_distortion_simulator_task`, and
`app.services.fitchef_runtime.run_weekly_plan_task`.

## Foundation invariants

- FitChef must not implement nutrition math outside canonical backend engines.
- LLM output is not product truth for tiers, targets, planner state, or action
  availability.
- FREE tier must not expose open-ended FitChef coaching runtime.
- UI clients must render structured DTOs or approved response envelopes instead
  of parsing raw prose into product state.
- Every FitChef action exposed to UI must map to an existing routed product
  flow.
- Template and fallback responses are mandatory whenever LLM execution is
  unavailable, disallowed, or disabled.

## Rollout order

### PR-0 foundation

- backlog umbrella entry
- root and scoped AGENTS updates
- preserved live-canon documentation

### PR-1 visual system and App Store contract

- canonical screenshot blueprint
- safe-area and export rules
- App Store-safe copy rules
- `EN` first-wave localization only
- contract artifact: `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md`

### PR-2 mascot asset taxonomy

- canonical mascot asset naming
- portrait and emotion variants
- App Icon relation rules
- screenshot-safe asset usage rules
- selective promotion only from cleanly normalizable local source assets
- contract artifact: `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md`

### PR-3 App Store production pack

- metadata starter pack
- screenshot package contract
- preview storyboard
- upload checklist
- contract artifact: `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md`

### PR-4 structured coach contract

Contract artifact:

- `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`

Contract-frozen additive routes:

- `POST /api/v1/pro/fitchef/explain`
- `POST /api/v1/pro/fitchef/recommend`
- `POST /api/v1/vip/fitchef/insight`
- `POST /api/v1/vip/fitchef/chat`
- `POST /api/v1/vip/fitchef/week-repair`

This phase is contract-only and must not migrate the live mascot routes.

### PR-5 through PR-7 runtime follow-up

- domain shell
- PRO structured coach runtime
- VIP runtime expansion

Status reconciliation:

- `POST /api/v1/pro/fitchef/explain` is now the landed, feature-gated PRO
  Distortion Simulator runtime from PR #1215 / `70bdbd9e51d977d440b605eed3064c71212cff97`.
- `POST /api/v1/pro/fitchef/recommend` remains a contract-frozen PRO follow-up.
- `POST /api/v1/vip/fitchef/insight` is the feature-gated VIP Identity Loop
  Mapper runtime once this implementation lane registers the route and updates
  OpenAPI.
- `POST /api/v1/vip/fitchef/chat` and `POST /api/v1/vip/fitchef/week-repair`
  remain future-only VIP structured coach follow-ups until later reviewed
  runtime PRs register routes and update OpenAPI.

## Artifact and asset governance

- Foundation and contract PRs must remain docs-only.
- Mascot or App Icon binary promotion must land only in dedicated asset-focused
  PRs.
- Local or dirty asset diffs must not be bundled into governance or contract
  branches.
- PR-2 may selectively promote mascot or icon binaries only after filename and
  catalog normalization inside the dedicated asset worktree.
- Non-canonical icon source files with spaces or duplicate filename families
  remain deferred to the App Store production lane.

## Localization policy

- First App Store wave: `EN`
- Follow-up localization waves: `RU` (`PR-TBD-FITCHEF-LOCALIZATION-RU`), `ES` (`PR-TBD-FITCHEF-LOCALIZATION-ES`)

`RU` and `ES` stay in backlog until the `EN` visual contract and production pack
are governed.

## Explicit non-goals for this foundation wave

- migrating `/api/v1/insight/fitchef*` to a new namespace
- shipping production screenshot binaries
- shipping mascot or App Icon binaries
- adding new runtime behavior outside the already-landed, feature-gated PRO
  `POST /api/v1/pro/fitchef/explain` route and the bounded VIP Identity Loop
  Mapper lane at `POST /api/v1/vip/fitchef/insight`
- adding any remaining structured coach routes before their dedicated reviewed
  runtime PRs

## Evidence anchors

- `app.routers.fitchef_insight.router`
- `app.routers.fitchef_insight.fitchef_mascot_insight`
- `app.routers.fitchef_insight.fitchef_weekly_reflection`
- `app.routers.fitchef_insight.fitchef_slip_support`
- `app.routers.fitchef_structured.fitchef_distortion_simulator`
- `app.main.ensure_canonical_app_bootstrap`
- `app.services.fitchef_runtime.run_mascot_insight_task`
- `app.services.fitchef_runtime.run_weekly_reflection_task`
- `app.services.fitchef_runtime.run_slip_support_task`
- `app.services.fitchef_runtime.run_distortion_simulator_task`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
- `docs/contracts/API_CANONICAL_MAP.md`
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md`
- `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md`
- `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md`
- `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
