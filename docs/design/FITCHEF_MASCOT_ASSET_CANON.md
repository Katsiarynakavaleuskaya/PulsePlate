# FitChef Mascot Asset Canon

Status: `Seed Pack v1`
Owner: `@katsiaryna_kavaleuskaya`
Scope: `Repo brand asset canon for FitChef mascot/logo references`

## Summary

This document locks the first canonical FitChef mascot seed pack that can be
reused by iOS, web, and Figma reference workflows without treating Xcode asset
catalogs as the source of truth.

Current source-of-truth pack:

- `frontend/src/assets/brand/fitchef-portrait-neutral-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-wink-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-thinking-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-sleepy-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-surprised-v1.png`
- `frontend/src/assets/brand/fitchef-onboarding-welcome-v1.png`

## Canonical Rules

1. Repo asset files are the current mascot source of truth for PR4.
2. `ios/PulsePlate/Assets.xcassets/` is a derived runtime mirror, not the
   authoring lane.
3. Figma remains a design/reference lane for placement and composition, not the
   master asset lane for these mascot PNGs.
4. Legacy web aliases remain valid for current consumers:
   - `frontend/src/assets/brand/fitchef-static.png`
   - `frontend/src/assets/brand/fitchef-wink.png`

## Default Runtime Mapping

### Web

- Default mascot alias: `frontend/src/assets/brand/fitchef-static.png`
- Existing wink alias: `frontend/src/assets/brand/fitchef-wink.png`
- New PR4 source pack is additive and should be used for future website hero,
  onboarding, and campaign layouts.

### iOS

- Default mascot alias: `ios/PulsePlate/Assets.xcassets/FitChef.imageset`
- Named variants:
  - `FitChefWink.imageset`
  - `FitChefThinking.imageset`
  - `FitChefSleepy.imageset`
  - `FitChefSurprised.imageset`
  - `FitChefOnboardingWelcome.imageset`

## Variant Contract

| Variant | Canonical file | Intended usage |
| --- | --- | --- |
| neutral | `frontend/src/assets/brand/fitchef-portrait-neutral-v1.png` | default UI mascot / baseline portrait |
| wink | `frontend/src/assets/brand/fitchef-portrait-wink-v1.png` | positive feedback / playful UI states |
| thinking | `frontend/src/assets/brand/fitchef-portrait-thinking-v1.png` | reflection / planning / question states |
| sleepy | `frontend/src/assets/brand/fitchef-portrait-sleepy-v1.png` | rest / night / calm guidance states |
| surprised | `frontend/src/assets/brand/fitchef-portrait-surprised-v1.png` | alert / attention / highlight states |
| onboarding-welcome | `frontend/src/assets/brand/fitchef-onboarding-welcome-v1.png` | onboarding hero / welcome card / promo scenes |

## Mutation Policy

Allowed:

- add new named variants with explicit `-vN` suffixes
- derive runtime copies for iOS/web from this pack
- update docs that map usages

Forbidden:

- overwrite a locked variant in place without version bump
- use generic names like `Image.imageset` for mascot variants
- use filenames with Finder collision suffixes like ` 1.png`
- treat Figma export/import as the mascot source of truth

## Figma Policy

Figma consumers must reference this seed pack when composing screens or
marketing layouts. Any future Figma sync remains `reference_only` until a
follow-up PR promotes a governed export/import contract.
