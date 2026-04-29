# Design Runtime System Web+iOS PR-5 iOS Design-System Adoption Packet

**Version:** 2026-04-28 (`America/New_York`)
**Epic Slug:** `epic/design-runtime-system-web-ios-v1`
**Slice:** `PR-5`
**PR:** `draft pending`
**Worktree:** `worktrees/design-runtime-system-pr5`
**Branch:** `codex/ios-design-system-adoption-v1`
**PR Phase:** `pre_open`
**Design Lane Mode:** `execution`
**Title:** `feat(ios): adopt governed design-system primitives`

## Summary

This packet is the branch-scoped field contract for `PR-5` of the design
runtime system web+iOS epic line.

`PR-0`, `PR-1`, `PR-2`, `PR-3`, and `PR-4` are treated as merged baseline
per the design epic ledger (`docs/roadmap/BACKLOG_LEDGER.md:1003`).
This slice adopts existing generated iOS design tokens and existing
`PPDesignTokens` (`ios/PulsePlate/DesignSystem/DesignTokens.swift:5`),
`PPButton` (`ios/PulsePlate/DesignSystem/PPButton.swift:51`), and
`PPTypography` (`ios/PulsePlate/DesignSystem/PPTypography.swift:7`) primitives on bounded,
non-conflicting iOS surfaces without product-screen migration, token
regeneration, backend changes, or ownership drift.

Execution started only after fresh live `main` confirmation:

- `origin/main` head: `3c83082a49812fe08eaafc153dde957036abb689`
- `main...origin/main`: `0 0`
- current-head `main` workflows for that head completed with `success`, including
  canonical `CI` run `25065564665`

Evidence:

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR4_WEB_SHELL_CONVERGENCE_PACKET_2026-04-25.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `ios/AGENTS.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN

- create this `PR-5` packet as the first tracked PR artifact
- update the design epic backlog anchor so `PR-4` / `#1527` is recorded as
  merged and `PR-5` is active
- adopt existing iOS token and primitive consumers on bounded surfaces:
  - `WelcomeFlowView`
  - `LaunchScreenView`
  - `BMICalculatorScreen` validation styling and CTA presentation only
  - `RootTabs` shell-level tint only

### OUT

- product screen migration or ownership claims for `Home`, `Plate`, `Progress`,
  Weekly Plan, Profile, Paywall, billing, or App Store assets
- backend, OpenAPI, entitlement, provider, deploy, or token-generation changes
- `/tokens` authoring changes or generated token mirror regeneration
- Figma writes, manifest ownership, Canva, Cloudflare, Remotion, Life Science,
  macOS, OpenAPI, GraphMap, or Playwright work

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR5_IOS_DESIGN_SYSTEM_ADOPTION_PACKET_2026-04-28.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
- `ios/PulsePlate/Views/LaunchScreenView.swift`
- `ios/PulsePlate/Screens/BMICalculatorScreen.swift`
- `ios/PulsePlate/Views/RootTabs.swift`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR creation

Read-only dependency surfaces:

- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- `ios/PulsePlate/DesignSystem/DesignTokens.swift`
- `ios/PulsePlate/DesignSystem/PPButton.swift`
- `ios/PulsePlate/DesignSystem/PPTypography.swift`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.

## Plugin And Skill Policy

- `pulseplate-workflow`: coordinator-first workflow and repo policy
- `pulseplate-design-launch-system`: source precedence and token governance
- `pulseplate-frontend-ui`: web/iOS token parity context only
- `pulseplate-gates`: local validation bundle
- `pulseplate-guards`: guard triage, especially iOS thin-client BMI rules
- `pulseplate-pr-review`: post-open review governance
- `GitHub`: draft PR, current-head checks, review disposition, merge readiness
- `CodeRabbit`: post-open review input
- `Build iOS Apps`: targeted xcodebuild / simulator validation evidence
- `Figma`: read-only design-intent reference only

Out of scope unless a later coordinator handoff records it explicitly:
`Canva`, `Cloudflare`, `Remotion`, `LaTeX`, `Build macOS Apps`, `Life Science
Research`, `OpenAPI`, `GraphMap`, and `Playwright`.

## Implementation Contract

- consume existing generated iOS runtime mirrors through `PPDesignTokens`
  (`ios/PulsePlate/DesignSystem/DesignTokens.swift:5`)
- consume existing `PPButton` (`ios/PulsePlate/DesignSystem/PPButton.swift:51`)
  and `PPTypography` (`ios/PulsePlate/DesignSystem/PPTypography.swift:7`)
  primitives without changing their public APIs
- preserve `WelcomeFlowView` localization keys and accessibility identifiers
  (`ios/PulsePlate/Welcome/WelcomeFlowView.swift:81`)
- preserve `BMICalculatorScreen` request/response DTOs, parsing behavior,
  backend-owned BMI logic, and paywall routing
  (`ios/PulsePlate/Screens/BMICalculatorScreen.swift:108`)
- preserve `RootTabs` tab structure, destinations, labels, and debug gating
  (`ios/PulsePlate/Views/RootTabs.swift:10`)
- do not add local BMI thresholds, category inference, waist/height math, or
  product entitlement logic

## Validation Bundle

Start gates already passed before edits:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`

Required local gates before push:

- `pytest -q tests/test_repo_policy_guards.py`
- targeted iOS xcodebuild / simulator validation aligned with `ios/AGENTS.md`
  and `scripts/ios_test_targets.sh`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `pre-commit run --all-files`
- `make verify`

If `make verify` is machine-blocked, stop and ask for an explicit operator
exception before substituting GitHub CI.

## Review Path

- open the PR as draft first
- create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md` after PR
  number assignment
- sync the PR body mirror after review dispositions
- use GitHub current-head truth plus CodeRabbit/Sourcery/Cubic review input;
  do not rely on stale historical runs
- run the mandatory `qa-engineer-agent -> bug-hunter` lane post-open

## Merge Path

- move the lane to `post_open_review` after draft PR creation
- move the lane to `merge_ready` only on current head after local validation,
  review artifact sync, review-thread disposition, and required current-head
  checks are coherent
- run:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Cleanup Path

After merge:

1. checkout root `main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. confirm PR state is `MERGED`
5. confirm `HEAD...origin/main` is `0 0`
6. remove only `worktrees/design-runtime-system-pr5`, the local branch
   `codex/ios-design-system-adoption-v1`, and PR-5 temp artifacts
7. `git worktree prune`

## DoD

- bounded iOS surfaces consume existing governed tokens/primitives
- localization keys and accessibility identifiers remain intact
- BMI screen remains a thin client with no local BMI business logic
- backlog anchor records `PR-4` merged and `PR-5` active
- targeted iOS validation, design guard, pre-commit, and `make verify` pass or
  an explicit operator exception is recorded before substitution
- no backend, OpenAPI, `/tokens`, generated mirrors, Figma writes, App Store
  assets, or product-screen ownership drift is introduced
