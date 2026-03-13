# FitChef Mascot Asset Taxonomy

**Status:** PR-2 mascot asset taxonomy and selective promotion contract
**Date:** 2026-03-13
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract freezes the iOS-side mascot and icon taxonomy for the FitChef
visual lane. It normalizes asset bucket names, variant rules, and icon
catalog hygiene so future App Store production work can reuse one governed
asset shape without inheriting local or experimental drift.

This PR is asset-focused. It does not change live FitChef backend routes or
add runtime behavior.

## Scope

This contract defines:

- the canonical default mascot asset key for current Swift surfaces
- the approved variant asset buckets for emotion/onboarding states
- App Icon filename and catalog hygiene rules
- selective promotion rules for local source PNGs
- deterministic readiness checks for xcassets integrity

This contract does not define:

- App Store screenshot exports
- preview video assets
- Fastlane or screenshot automation
- structured coach DTOs or runtime routes

## Canonical mascot buckets

### Stable default runtime asset

- Asset key: `FitChef`
- Catalog bucket: `ios/PulsePlate/Assets.xcassets/FitChef.imageset`
- Role: neutral default mascot for current Swift surfaces such as launch,
  fallback mascot bubbles, and non-variant previews

### Approved variant buckets

- `FitChefPortraitWink`
- `FitChefPortraitThinking`
- `FitChefPortraitSurprised`
- `FitChefPortraitSleepy`
- `FitChefOnboardingWelcome`

Each variant must live in its own `.imageset` bucket. Semantic variants must
not be encoded by abusing `1x/2x/3x` slots inside one shared bucket.

## Naming rules

- Filenames must be ASCII-safe and contain no spaces.
- Generic bucket names such as `Image.imageset` are forbidden for FitChef
  assets.
- Filenames must be FitChef-prefixed and clearly identify the represented
  variant.
- A single bucket must represent a single semantic variant only.
- The stable public key `FitChef` must remain available for current Swift
  callers until a future explicit migration PR changes it.

## App Icon relation rules

- Public icon bucket remains `AppIcon.appiconset`.
- Canonical referenced filename family for this lane is `AppIcon-*`.
- Duplicate filename families such as mixed `icon_*` and `AppIcon-*` are not
  allowed to coexist in the reviewed catalog without an explicit contract.
- Unreferenced PNG files must not remain in `AppIcon.appiconset` after
  normalization.
- FitChef mascot portraits may inform icon source design, but portrait assets
  and icon slots must remain in separate asset buckets.

## Selective promotion policy

- Root local iOS asset diffs are source candidates only.
- PR-2 may promote only files that fit the canonical taxonomy without adding
  filename drift, mixed semantics, or duplicate catalog families.
- Files that still require renaming, re-export, or icon-source review remain
  deferred to the App Store production lane and must be tracked in the backlog.

## Deterministic readiness checks

PR-2 must enforce repository checks that prove:

- every `Contents.json` references only existing local files
- canonical FitChef filenames contain no spaces
- `FitChef.imageset` remains a neutral-only default bucket
- no generic `Image.imageset` remains as a FitChef bucket
- `AppIcon.appiconset` contains only referenced canonical files after
  normalization

## Evidence anchors

- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:67`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:108`
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md:211`
- `ios/PulsePlate/Assets.xcassets/FitChef.imageset/Contents.json:1`
- `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json:1`
