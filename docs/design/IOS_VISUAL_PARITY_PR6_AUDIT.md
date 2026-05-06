<!-- markdownlint-disable MD013 -->
# iOS Visual Parity PR-6 Audit

## Decision

iOS visual/design-system parity is accepted with one bounded sync fix.

The PR-6 audit found a concrete token-backed parity gap in `ios/PulsePlate/Extensions/ShapeStyle+Theme.swift`: `ShapeStyle` surface aliases manually encoded white-opacity values instead of routing through `PPDesignTokens.ColorToken`. The bounded sync updates those aliases to the generated-token facade and adds a focused contract test.

This audit is review evidence only. It is not live iOS screenshot proof, App Store approval, runtime product truth, or a second source of truth. Repo code, tests, `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI contracts, and implemented runtime behavior remain canonical.

## Evidence Considered

- PR #1689 web launch shell acceptance brief: `/` and `/marketing` accepted with deferred minor follow-up.
- `docs/design/screen_evidence/examples/ios_home.sample.json`: PR-3 iOS sample screen evidence metadata.
- `docs/design/design_scorecard/examples/ios_home.scorecard.sample.json`: PR-4 deterministic iOS sample scorecard metadata.
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`: generated iOS token mirror, not edited by hand.
- `ios/PulsePlate/DesignSystem/DesignTokens.swift`: stable public facade over generated tokens.
- `ios/PulsePlate/DesignSystem/PPButton.swift`, `PPCard.swift`, `PPInput.swift`, `PPTypography.swift`, and `PPAccessibility.swift`: governed iOS design-system primitives.
- `ios/PulsePlate/Extensions/Color+Assets.swift` and `ShapeStyle+Theme.swift`: SwiftUI theme aliases over design tokens.
- `ios/PulsePlateTests/DesignSystemAccessibilityContractTests.swift`: existing accessibility/motion/touch-target contract coverage.

The PR-3/PR-4 iOS evidence commands validate metadata quality only. They do not prove live simulator visuals, pixel parity, App Store screenshots, or current runtime capture.

## iOS Token Parity

Generated token mirrors remain untouched by hand. The iOS token stack follows the repo-owned chain:

1. `/tokens`
2. `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
3. `ios/PulsePlate/DesignSystem/DesignTokens.swift`
4. iOS DesignSystem primitives and theme aliases

`PPDesignTokens` correctly exposes generated brand, semantic color, spacing, typography, radius, elevation, and motion values. `Color+Assets.swift` already routes semantic aliases through `PPDesignTokens`.

The bounded sync fixes `ShapeStyle+Theme.swift` so `surface`, `surfaceElevated`, and `liquidGlass` no longer encode separate white-opacity values outside the token facade.

This creates one expected token-parity visual delta: `Color.surface` moves from the former local `Color.white.opacity(0.08)` alias to the generated token value currently exposed as `PPDesignTokens.ColorToken.surface` (`Color.white.opacity(0.10)`). That is accepted as repo-token parity, not redesign.

## iOS Component Parity

`PPButton`, `PPCard`, `PPInput`, and `PPTypography` use `PPDesignTokens` for colors, spacing, radius, typography, and motion. The observed variants are token-backed iOS-native wrappers over the shared component vocabulary and do not invent a separate visual grammar.

No broad iOS redesign is needed in PR-6. No screen layout, navigation, feature behavior, billing, StoreKit, nutrition, BMI, coaching, backend, or OpenAPI logic is changed.

## Accessibility And Motion

Existing design-system coverage verifies:

- compact buttons keep the generated 44-point minimum target,
- `PPAccessibility.minimumTouchTarget(for:)` never drops below the generated token,
- press scale respects reduced motion,
- animations are disabled when reduced motion is enabled.

This PR adds a focused contract check that `ShapeStyle+Theme.swift` stays routed through the design-token facade instead of hardcoded surface opacity values.

Dynamic Type and live VoiceOver review remain future capture-lane evidence, not claims made by this audit.

## Thin-Client Safety

This PR does not add or modify:

- BMI math or BMI category inference,
- nutrition or coaching logic,
- entitlement truth,
- StoreKit/payment behavior,
- backend/OpenAPI contracts,
- HealthKit behavior,
- AI consent or free-text runtime.

iOS remains a thin presentation client over backend and repo token truth.

## Web PR-5 Relationship

PR #1689 accepted the current web launch shell with deferred minor follow-up. PR-6 does not compare iOS against subjective web screenshots. It audits iOS against shared repo tokens, generated mirrors, UI vocabulary, implemented iOS primitives, and deterministic Design Intelligence metadata.

## Bounded Sync Outcome

- Current iOS design-system parity: accepted with one bounded token-facade sync.
- Code sync required now: yes, only for `ShapeStyle+Theme.swift` token facade alignment.
- Tests required now: focused `DesignSystemAccessibilityContractTests` coverage for the alias contract.
- Deferred minor follow-up: future live iOS simulator capture, Dynamic Type evidence, and VoiceOver review can be added in a separate capture/review lane.
- Next Design Intelligence lane: PR-7 design-agent workflow and PR template. Live iOS capture remains a separate future evidence lane unless separately scoped.

## Out Of Scope

- No broad iOS redesign.
- No web runtime changes.
- No backend, OpenAPI, billing, auth, StoreKit, HealthKit, App Store, or deploy changes.
- No `/tokens` changes.
- No manual generated token mirror edits.
- No Figma or Canva writes.
- No screenshots, videos, traces, DerivedData, Storybook output, or binary artifacts.
- No visual/pixel comparison.
- No GEPA or prompt/rubric evolution.
