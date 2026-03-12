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

These routes are already registered under the canonical insight namespace in
`app/routers/fitchef_insight.py:45`, `app/routers/fitchef_insight.py:58`,
`app/routers/fitchef_insight.py:133`, and `app/routers/fitchef_insight.py:214`.

The current runtime anchor remains `app/services/fitchef_runtime.py:17` through
`app/services/fitchef_runtime.py:66` and the weekly-plan adapter seam remains
live in `app/services/fitchef_runtime.py:127` through
`app/services/fitchef_runtime.py:208`.

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

### PR-2 mascot asset taxonomy

- canonical mascot asset naming
- portrait and emotion variants
- App Icon relation rules
- screenshot-safe asset usage rules

### PR-3 App Store production pack

- metadata starter pack
- screenshot package contract
- preview storyboard
- upload checklist

### PR-4 structured coach contract

Planned-only additive routes:

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

## Artifact and asset governance

- Foundation and contract PRs must remain docs-only.
- Mascot or App Icon binary promotion must land only in dedicated asset-focused
  PRs.
- Local or dirty asset diffs must not be bundled into governance or contract
  branches.

## Localization policy

- First App Store wave: `EN`
- Follow-up localization waves: `RU` (`PR-TBD-FITCHEF-LOCALIZATION-RU`), `ES` (`PR-TBD-FITCHEF-LOCALIZATION-ES`)

`RU` and `ES` stay in backlog until the `EN` visual contract and production pack
are governed.

## Explicit non-goals for this foundation wave

- migrating `/api/v1/insight/fitchef*` to a new namespace
- shipping production screenshot binaries
- shipping mascot or App Icon binaries
- adding new runtime behavior
- adding structured coach routes before the contract phase

## Evidence anchors

- `app/routers/fitchef_insight.py:45`
- `app/routers/fitchef_insight.py:58`
- `app/routers/fitchef_insight.py:133`
- `app/routers/fitchef_insight.py:214`
- `app/services/fitchef_runtime.py:17`
- `app/services/fitchef_runtime.py:127`
- `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md:16`
- `docs/contracts/API_CANONICAL_MAP.md:46`
