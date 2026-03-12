# FitChef Visual and App Store Contract

**Status:** PR-1 visual/App Store contract
**Date:** 2026-03-12
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract defines the first governed visual/App Store lane for the FitChef
initiative. It translates the umbrella foundation into one docs-only visual
baseline that can later drive mascot taxonomy work and the production App Store
pack without mixing in runtime changes or binary asset promotion.

This wave is additive. It does not migrate the live
`/api/v1/insight/fitchef*` routes, rename current iOS assets in-place, or ship
final screenshot binaries.

## Scope

This PR-1 contract defines:

- the first-wave App Store device/export baseline
- safe-area and composition rules for FitChef launch screenshots
- the canonical seven-shot sequence for the `EN` launch wave
- copy guardrails for App Store-safe wellness messaging
- source-of-truth ordering for tokens, iOS assets, and future export folders

This PR-1 contract explicitly does not define:

- mascot asset renames or binary promotion
- App Icon promotion
- preview video production assets
- Fastlane or screenshot automation
- structured coach runtime routes or DTOs

## Source precedence

The visual/App Store lane inherits the canonical design-tooling precedence from
`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:15` through
`docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:24`.

Project-specific order for this lane:

1. repo docs/contracts remain the governing source
2. `/tokens` remains the token authoring SoT
3. runtime token mirrors remain implementation evidence for web and iOS
4. existing iOS asset catalogs remain the current mascot/icon source lane
5. Figma may inform layouts, but promoted repo contracts win until a reviewed
   PR changes them

## Device and export baseline

### Primary launch surface

- First-wave device class: `iPhone 6.9"`
- Canonical canvas: `1320 x 2868 px`
- Allowed capture compatibility size: `1290 x 2796 px`
- Fallback only if required by tooling/export limitations: `1242 x 2688 px`

### Export contract

- Preferred format: `PNG`
- Allowed alternate format: `JPG/JPEG`
- Color space: `RGB`
- Preferred profile: `sRGB`
- `Display P3` is acceptable only if the export path preserves it correctly
- Final uploads must not contain transparency

### Safe area

- top safe zone: `260 px`
- bottom safe zone: `260 px`
- left/right margin: `120 px`
- Headline and supporting copy must stay inside the safe zone
- FitChef must not overlap headline, supporting copy, or critical UI affordances

## Composition contract

Canonical vertical stack for each screenshot:

1. headline block
2. main product UI frame
3. short benefit/supporting copy
4. FitChef supporting placement in a non-blocking corner

Layout rules:

- headline uses a two-line maximum
- supporting copy uses a two-line maximum
- the real product UI remains the dominant visual mass
- FitChef acts as a trust/personality amplifier, not as a fake-UI substitute
- backgrounds may be styled, but the central UI must remain recognizably real

## Seven-shot sequence

### Shot 1. Core value

- Headline: `Smart Nutrition` / `Powered by AI`
- Supporting copy: `Track nutrients` / `plan meals` / `improve health`
- Product surface: dashboard with calories, macros, micronutrients, and daily
  score
- FitChef emotion: calm / welcoming

### Shot 2. Nutrition analysis

- Headline: `Understand Your` / `Nutrition`
- Supporting copy: `Macros` / `Micronutrients` / `Daily balance`
- Product surface: nutrient analysis with chart + vitamin/micronutrient detail
- FitChef emotion: explaining

### Shot 3. Meal planner

- Headline: `AI Meal Planning` / `For Your Goals`
- Supporting copy: `Weight loss` / `Muscle gain` / `Healthy balance`
- Product surface: weekly planner
- FitChef emotion: cooking

### Shot 4. Grocery list

- Headline: `Smart Grocery` / `Lists`
- Supporting copy: `Auto-generated` / `from your meals`
- Product surface: grocery list generated from planning flow
- FitChef emotion: helpful

### Shot 5. Health progress

- Headline: `See Your` / `Progress`
- Supporting copy: `Habits` / `Nutrition balance` / `Weekly insights`
- Product surface: progress graphs and weekly analytics
- FitChef emotion: proud

### Shot 6. Personalization

- Headline: `Nutrition` / `For You`
- Supporting copy: `Goals` / `Preferences` / `Diet types`
- Product surface: setup/profile preference flow
- FitChef emotion: thinking

### Shot 7. AI assistant

- Headline: `Your Personal` / `AI Nutrition Coach`
- Supporting copy: `Guidance` / `Recommendations` / `Insights`
- Product surface: bounded assistant/chat or coach panel UI
- FitChef emotion: guiding

## FitChef placement and emotion map

Default placement rules:

- preferred placement: bottom-right corner
- scale target: `10-15%` of the frame height
- mascot must remain fully inside the safe area
- mascot must never cover charts, meal rows, CTA buttons, or system status
  regions

Emotion map:

| Shot | Product state | FitChef emotion |
| --- | --- | --- |
| 1 | dashboard | calm |
| 2 | analysis | explaining |
| 3 | planner | cooking |
| 4 | grocery | helpful |
| 5 | progress | proud |
| 6 | personalization | thinking |
| 7 | assistant | guiding |

## Copy safety rules

Allowed:

- short feature headlines over real UI
- benefit language grounded in actual product capability
- mascot and decorative visual support
- trust-oriented language about planning, guidance, insights, and habits

Blocked:

- fake UI or fabricated feature states
- prices, discounts, or promotional pricing claims
- unverifiable superlatives such as `#1`, `best app`, or `most accurate`
- medical diagnosis, treatment, or guaranteed-outcome claims
- cross-platform references irrelevant to the App Store surface

Wellness-specific copy rule:

- Use supportive, non-clinical phrasing
- Do not imply diagnosis or treatment
- Prefer `may help support your goal` over guaranteed-result language

## Token and asset anchors

### Token SoT

- `/tokens/00_core/color.json`
- `/tokens/10_semantic/color.json`
- `/tokens/30_platform/web.json`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- `ios/PulsePlate/DesignSystem/DesignTokens.swift`
- `ios/PulsePlate/Extensions/Color+Assets.swift`

### Current iOS asset anchors

- `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json`
- `ios/PulsePlate/Assets.xcassets/FitChef.imageset/Contents.json`
- `ios/PulsePlate/Views/LaunchScreenView.swift`
- `ios/PulsePlate/Views/Components/AppIconTestView.swift`

PR-1 uses these paths as reference anchors only. Asset taxonomy changes belong
to PR-2.

## Folder contract for future PR-3 production assets

The future production pack must follow this folder contract:

```text
/appstore/fitchef/en-US/iphone-6.9/screenshots/
/appstore/fitchef/en-US/iphone-6.9/preview/
/appstore/fitchef/en-US/metadata/
```

Rules:

- PR-1 does not create or populate these folders
- PR-3 may populate them only with reviewed release-ready assets
- `RU` and `ES` folders remain follow-up waves after `EN`

## Localization policy

- First governed App Store wave: `EN` only
- Follow-up waves remain backlog-tracked: `RU`, `ES`
- No bilingual or mixed-language screenshot sets are allowed in the same export
  pack

## Acceptance checklist

- one governed 6.9-inch baseline is defined
- safe areas are explicit
- the seven-shot launch sequence is explicit
- FitChef placement and emotion rules are explicit
- App Store-safe copy rules are explicit
- token and asset source anchors are linked
- future asset folder contract is explicit
- first-wave localization is fixed to `EN`
- no binaries or runtime changes are introduced

## Evidence anchors

- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:59`
- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:108`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:15`
- `docs/design/TOKENS_SOT.md:13`
- `docs/design/TOKENS_SOT.md:28`
- `ios/PulsePlate/Assets.xcassets/FitChef.imageset/Contents.json:1`
- `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json:1`
