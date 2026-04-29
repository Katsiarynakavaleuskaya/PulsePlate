# Design Runtime System Web+iOS PR-5B Home Plate Progress Adoption Packet

**Version:** 2026-04-29 (`America/New_York`)
**Epic Slug:** `epic/design-runtime-system-web-ios-v1`
**Slice:** `PR-5B`
**PR:** `#1579`
**Worktree:** `worktrees/ios-design-system-adoption-v1-clean`
**Branch:** `codex/ios-design-system-adoption-v1-clean`
**PR Phase:** `post_open_review`
**Design Lane Mode:** `repo_first_reference_sync`
**Title:** `feat(ios): adopt design tokens on Home Plate Progress`

## Summary

This packet records the clean-lane continuation after `PR-5` / `PR #1569`
landed on `main` with bounded iOS adoption for `WelcomeFlowView`,
`LaunchScreenView`, `BMICalculatorScreen`, and `RootTabs`.

This clean slice adopts runtime-approved `PPDesignTokens` and existing shared
design grammar on bounded `HomeView`, `PlateViewPP`, and `ProgressViewPP`
without taking product-flow ownership, changing backend contracts, or treating
Figma as an upstream source of truth.

Figma updates are downstream documentation/reference sync only. Repo code,
generated tokens, and iOS runtime design-system files remain Source of Truth.

## Scope

### IN

- align bounded `HomeView`, `PlateViewPP`, and `ProgressViewPP` spacing,
  radius, typography, status color, card, and button treatment with the shared
  iOS design grammar
- consume only runtime-approved `PPDesignTokens` public surfaces: `Brand`,
  `ColorToken`, `Spacing`, `Radius`, and `Typography`
- update directly required shared iOS primitives only with backwards-compatible
  parameters needed by the bounded screens
- update Figma reference annotations so they mirror final repo state
- update the design epic backlog anchor so PR #1569 is baseline and this clean
  branch is the active Home / Plate / Progress continuation

### OUT

- backend, OpenAPI, web, billing, entitlement, provider, deploy, or `/tokens`
  changes
- generated mirror regeneration or generated-file edits
- SwiftUI navigation, state-machine, API/data-flow, BMI, nutrition, progress,
  or entitlement behavior changes
- product-token runtime consumption; the parity guard remains closed
- Code Connect activation claims
- Figma-driven token creation, component APIs, runtime semantics, or product
  decisions
- edits to `worktrees/design-runtime-system-pr5`

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR5B_HOME_PLATE_PROGRESS_ADOPTION_PACKET_2026-04-29.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `ios/PulsePlate/Views/Components/GlassCard.swift`
- `ios/PulsePlate/Views/HomeView.swift`
- `ios/PulsePlate/Views/PlateView.swift`
- `ios/PulsePlate/Views/ProgressView.swift`
- `docs/review/PR_1579_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

## Implementation Contract

- keep `Home`, `Plate`, and `Progress` behaviorally stable; visual adoption is
  limited to token/style consumption
- preserve navigation, data flow, API contracts, BMI logic, nutrition logic,
  progress logic, and entitlement truth
- keep product-token runtime consumption closed; use semantic/runtime token
  surfaces only
- use Figma writes only for labels, notes, or reference annotations that state
  the repo-first mapping

## Figma Reference Sync

Figma was updated only after SwiftUI/token changes were locally validated.
The update is documentation/reference-only:

- `00_Foundation_Tokens`: `PR-5 iOS Design-System Adoption / Repo-First Sync`
  (`1579:2`)
- `01_Components`: `PR-5 iOS Design-System Adoption / Repo-First Sync`
  (`1579:47`)

Both annotations were corrected after the product-token parity guard caught the
initial overreach, and now state that product-token runtime consumption remains
closed.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `git diff --check` PASS
- `xcodebuild build-for-testing ...` PASS (`** TEST BUILD SUCCEEDED **`)
- `xcodebuild test-without-building ...` PASS (`80 tests, 0 failures`)
- first `make verify` attempt found
  `tests/test_design_token_parity.py::test_product_tokens_are_not_consumed_outside_token_runtime_surfaces`;
  the slice was corrected to avoid product-token runtime consumption
- targeted parity rerun PASS:
  `tests/test_design_token_parity.py::test_product_tokens_are_not_consumed_outside_token_runtime_surfaces`
- `pre-commit run --all-files` PASS after correction
- final `make verify` PASS after correction:
  - `verify-env` PASS
  - `flake8` PASS
  - `mypy --no-incremental --cache-dir=/dev/null app core` PASS
  - smoke tests PASS
  - full coverage pytest PASS
  - `diff-cover` PASS (`No lines with coverage information in this diff.`)
- simulator screenshots captured from deterministic App Store screenshot mode:
  - `/tmp/pulseplate-pr5-ios-evidence/core_value.png`
  - `/tmp/pulseplate-pr5-ios-evidence/nutrition_analysis.png`
  - `/tmp/pulseplate-pr5-ios-evidence/health_progress.png`
- Figma MCP metadata confirmed downstream annotation frames `1579:2` and
  `1579:47`

## DoD

- bounded Home / Plate / Progress surfaces consume governed design tokens and
  stable primitives
- navigation, data flow, backend contracts, and product logic remain unchanged
- Figma reference documentation mirrors final repo code and states repo/code SoT
- targeted iOS build/test evidence and required repo gates pass
- no backend, web, `/tokens`, generated-file, Code Connect, product-token
  runtime, or product-ownership drift is introduced
