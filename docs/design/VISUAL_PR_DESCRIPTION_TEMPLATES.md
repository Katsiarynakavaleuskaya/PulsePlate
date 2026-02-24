<!-- markdownlint-disable MD013 -->
# Visual PR Description Templates

**Date:** February 24, 2026 (America/New_York)
**Scope:** Copy/paste PR body snippets for each visual element

Use together with:

- `.github/PULL_REQUEST_TEMPLATE/visuals.md`
- `docs/design/VISUAL_IMPLEMENTATION_MAP.md`
- `docs/design/VISUAL_ELEMENT_PROMPT_CATALOG.md`

## Template 01: Home Hero Ambient Layer (P0)

```md
## Summary
Implement Home Hero Ambient Layer to improve first-screen visibility and premium perception.

## Visual Scope
- Visual element: Home Hero Ambient Layer
- Prompt pack: `docs/sora/prompts/hpp/p0_visibility/home_hero_ambient__home__v1.0.md`
- Frontend path: `frontend/src/pages/Home.tsx`

## Acceptance
- Reduced-motion fallback included
- Hero text/CTA readability preserved on mobile and desktop
- Sora + Figma outputs aligned with token SoT
```

## Template 02: Progress Momentum Ring + Weekly Streak Badge (P0)

```md
## Summary
Implement Progress Momentum Ring and Weekly Streak Badge to improve progress clarity and modernity.

## Visual Scope
- Visual element: Progress Momentum Ring + Weekly Streak Badge
- Prompt pack: `docs/sora/prompts/hpp/p0_visibility/progress_momentum_ring__progress__v1.0.md`
- Frontend paths:
  - `frontend/src/pages/Progress.tsx`
  - `frontend/src/features/progress/LiveProgressIndicator.tsx`

## Acceptance
- Ring readable at 24/32 px
- State differences visible without color-only encoding
- No clinical visual cues
```

## Template 03: Premium Gate Value Frame (P0)

```md
## Summary
Implement Premium Gate Value Frame to increase conversion visibility with trust-first tone.

## Visual Scope
- Visual element: Premium Gate Value Frame
- Prompt pack: `docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md`
- Frontend paths:
  - `frontend/src/components/PremiumGate.tsx`
  - `frontend/src/components/Paywall/BeforeAfter.tsx`

## Acceptance
- Primary CTA remains dominant and readable
- Tone remains non-manipulative and non-clinical
- Modal/frame variants pass style QA checklist
```

## Template 04: Onboarding Trust Canvas (P0)

```md
## Summary
Implement Onboarding Trust Canvas to strengthen trust and modern first-run quality in key-entry flow.

## Visual Scope
- Visual element: Onboarding Trust Canvas
- Prompt pack: `docs/sora/prompts/hpp/p0_visibility/onboarding_trust_canvas__enter_key__v1.0.md`
- Frontend path: `frontend/src/pages/Onboarding/EnterKey.tsx`

## Acceptance
- Form remains first focal element
- State variants (`initial/loading/success/invalid`) are visually clear
- No fear-based security aesthetics
```

## Template 05: Setup Completion Step Rail (P1)

```md
## Summary
Implement Setup Completion Step Rail to reduce cognitive load in Nutrition Setup flow.

## Visual Scope
- Visual element: Setup Completion Step Rail
- Prompt pack: `docs/sora/prompts/hpp/p1_polish/setup_completion_step_rail__setup__v1.0.md`
- Frontend paths:
  - `frontend/src/pages/NutritionSetup/SetupForm.tsx`
  - `frontend/src/pages/NutritionSetup/ResultView.tsx`

## Acceptance
- Current step clearly visible without color-only indicators
- Mobile compact layout verified
- Step rail consistent across form/result screens
```

## Template 06: BMI Result Confidence Card (P1)

```md
## Summary
Implement BMI Result Confidence Card to improve trust and readability of BMI results.

## Visual Scope
- Visual element: BMI Result Confidence Card
- Prompt pack: `docs/sora/prompts/hpp/p1_polish/bmi_result_confidence_card__bmi__v1.0.md`
- Frontend path: `frontend/src/pages/BMI/BMICalculatePage.tsx`

## Acceptance
- No diagnosis-like visual implication
- Long localized strings remain readable
- Next-action CTA visibility is preserved
```

## Template 07: Smart Empty States Pack (P1)

```md
## Summary
Implement Smart Empty States Pack to unify no-data/locked/retry states for Plate and Progress.

## Visual Scope
- Visual element: Smart Empty States Pack
- Prompt pack: `docs/sora/prompts/hpp/p1_polish/smart_empty_states_pack__plate_progress__v1.0.md`
- Frontend paths:
  - `frontend/src/pages/Plate.tsx`
  - `frontend/src/pages/Progress.tsx`
  - `frontend/src/components/ui/EmptyState.tsx`

## Acceptance
- State meaning is obvious at first glance
- Visual style continuity across all state variants
- No fear/shame patterns
```

## Template 08: Tab Bar Active Trail Micro-Motion (P2)

```md
## Summary
Implement Tab Bar Active Trail Micro-Motion for subtle modern navigation polish.

## Visual Scope
- Visual element: Tab Bar Active Trail Micro-Motion
- Prompt pack: `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md`
- Frontend path: `frontend/src/components/TabBar.tsx`

## Acceptance
- Transition remains subtle and non-distracting
- Reduced-motion fallback is implemented
- No jitter/strobe/overshoot motion
```

## Template 09: Export Success Celebration Chip (P2)

```md
## Summary
Implement Export Success Celebration Chip to reinforce successful export actions.

## Visual Scope
- Visual element: Export Success Celebration Chip
- Prompt pack: `docs/sora/prompts/hpp/p2_expressive/export_success_celebration_chip__progress__v1.0.md`
- Frontend path: `frontend/src/features/progress/ProgressCharts.tsx`

## Acceptance
- Success feedback is readable and unobtrusive
- No full-screen celebration or motion overload
- Mobile viewport behavior validated
```

## Template 10: Seasonal Theme Accent Pack (P2)

```md
## Summary
Implement Seasonal Theme Accent Pack under campaign toggle without changing core brand identity.

## Visual Scope
- Visual element: Seasonal Theme Accent Pack
- Prompt pack: `docs/sora/prompts/hpp/p2_expressive/seasonal_theme_accent_pack__home_progress__v1.0.md`
- Frontend paths:
  - `frontend/src/pages/Home.tsx`
  - `frontend/src/pages/Progress.tsx`

## Acceptance
- Core token identity preserved
- Accent layer can be turned off with zero layout impact
- No palette override or brand drift
```
