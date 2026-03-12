# FitChef Brand Asset Contract

## Summary

This document defines the canonical FitChef mascot asset names promoted in PR4.
The goal is to keep iOS, future web surfaces, design runtime outputs, and Figma
references aligned to the same brand IDs instead of overloading scale slots or
using generic asset names such as `Image`.

## Scope

In scope for this contract:

- iOS asset-catalog naming for the first approved FitChef portrait pack
- the canonical default mascot asset used by `Image("FitChef")`
- one governed marketing app icon source image
- follow-up hooks for web and Figma promotion

Out of scope for this PR:

- web rendering or frontend mascot rollout
- Figma asset import or component sync
- scene packs beyond the first portrait/welcome set
- animation or Lottie/MP4 changes

## Canonical Asset IDs

### Default runtime mascot

- Asset ID: `FitChef`
- Purpose: default neutral portrait for launch, bubble fallback, and static
  mascot rendering
- Backing files:
  - `ios/PulsePlate/Assets.xcassets/FitChef.imageset/fitchef_neutral@1x.png`
  - `ios/PulsePlate/Assets.xcassets/FitChef.imageset/fitchef_neutral@2x.png`
  - `ios/PulsePlate/Assets.xcassets/FitChef.imageset/fitchef_neutral@3x.png`

### Secondary approved portrait variants

- Asset ID: `FitChefWink`
  - Intended use: friendly acknowledgement, success nudge, lightweight CTA
- Asset ID: `FitChefWelcome`
  - Intended use: onboarding welcome and brand-intro surfaces
- Asset ID: `FitChefThinking`
  - Intended use: reflection, pause, or recovery-support screens
- Asset ID: `FitChefSurprised`
  - Intended use: reveal, progress milestone, or insight discovery
- Asset ID: `FitChefSleepy`
  - Intended use: rest, wind-down, or bedtime routine surfaces

## Brand Rules

- `FitChef.imageset` stays the default public mascot surface for current iOS
  code paths.
- Variant assets must use descriptive asset IDs, not generic placeholders such
  as `Image.imageset`.
- Scale slots are resolution slots only.
  They must not be used to encode different semantic poses or emotions.
- Any new mascot scene must first get a canonical asset ID and intended-use note
  before it is referenced in code or design runtime payloads.

## App Icon Rule

- Public app-icon asset filename remains:
  `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/AppIcon.png`
- PR4 updates the underlying art only.
  It does not widen app-icon generation scope or promote a second public icon
  contract.

## Website And Figma Follow-ups

- Web mascot pack rollout:
  [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-web-brand-pack`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-web-brand-pack)
- Figma mascot component and asset sync:
  [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-figma-brand-sync`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-figma-brand-sync)
- Screen-scene source pack governance:
  [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-screen-scene-pack`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-screen-scene-pack)

## Decision Log

- PR4 promotes only the first portrait-based mascot pack because those files are
  already present locally and can be reviewed deterministically.
- The broader screen-scene set provided as source images is intentionally
  deferred to a follow-up PR so brand-foundation scope stays reviewable.
