<!-- markdownlint-disable MD013 -->
# PulsePlate Visual Implementation Map

**Date:** February 24, 2026 (America/New_York)
**Status:** Active planning map
**Scope:** Web frontend visual uplift linked to concrete implementation points

## 1) Purpose

This map links proposed visuals to concrete frontend integration points and PR checklists.
Use it to execute visual updates without scope drift.

Primary design source:

- `docs/design/VISUAL_ELEMENT_PROMPT_CATALOG.md`

Prompt source for P0 execution:

- `docs/sora/prompts/hpp/p0_visibility/home_hero_ambient__home__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/progress_momentum_ring__progress__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md`
- `docs/sora/prompts/hpp/p0_visibility/onboarding_trust_canvas__enter_key__v1.0.md`

Prompt source for P1 execution:

- `docs/sora/prompts/hpp/p1_polish/setup_completion_step_rail__setup__v1.0.md`
- `docs/sora/prompts/hpp/p1_polish/bmi_result_confidence_card__bmi__v1.0.md`
- `docs/sora/prompts/hpp/p1_polish/smart_empty_states_pack__plate_progress__v1.0.md`

Prompt source for P2 execution:

- `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md`
- `docs/sora/prompts/hpp/p2_expressive/export_success_celebration_chip__progress__v1.0.md`
- `docs/sora/prompts/hpp/p2_expressive/seasonal_theme_accent_pack__home_progress__v1.0.md`

## 2) Visual -> Component Mapping

| Visual Element | Priority | Frontend Paths | Design Output | Engineering Output |
| --- | --- | --- | --- | --- |
| Home Hero Ambient Layer | P0 | `frontend/src/pages/Home.tsx` | Background asset variants + layout spec | Integrate asset layer with reduced-motion fallback |
| Progress Momentum Ring + Weekly Streak Badge | P0 | `frontend/src/pages/Progress.tsx`, `frontend/src/features/progress/LiveProgressIndicator.tsx` | Ring + badge component visuals, state variants | Render state-driven visuals and preserve contrast |
| Premium Gate Value Frame | P0 | `frontend/src/components/PremiumGate.tsx`, `frontend/src/components/Paywall/BeforeAfter.tsx` | Value frame and modal hero variants | Apply frame in locked states and paywall surface |
| Onboarding Trust Canvas | P0 | `frontend/src/pages/Onboarding/EnterKey.tsx` | Trust canvas backgrounds, state-aware variants | Mount canvas by state (`initial`, `loading`, `success`, `invalid`) |
| Setup Completion Step Rail | P1 | `frontend/src/pages/NutritionSetup/SetupForm.tsx`, `frontend/src/pages/NutritionSetup/ResultView.tsx` | Step rail spec and mobile variant | Add step state UI across form/result |
| BMI Result Confidence Card | P1 | `frontend/src/pages/BMI/BMICalculatePage.tsx` | Confidence card visual system | Update BMI result container layout and states |
| Smart Empty States Pack | P1 | `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Progress.tsx`, `frontend/src/components/ui/EmptyState.tsx` | Empty-state family A/B/C | Replace fragmented empty-state visuals with unified family |
| Tab Bar Active Trail Micro-Motion | P2 | `frontend/src/components/TabBar.tsx` | Micro-motion spec | Implement subtle transition with reduced-motion support |
| Export Success Celebration Chip | P2 | `frontend/src/features/progress/ProgressCharts.tsx` | Compact success chip visuals | Show post-export success feedback |
| Seasonal Theme Accent Pack | P2 | `frontend/src/pages/Home.tsx`, `frontend/src/pages/Progress.tsx` | Optional seasonal accents | Feature-flagged accent overlays |

## 3) PR Checklist Template (Per Visual)

For every implementation PR, copy this checklist and keep all items explicit.
Optional PR body template:

- `.github/PULL_REQUEST_TEMPLATE/visuals.md`
- `docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md`
- `.github/pr_body_visual_p2_tab_bar_active_trail.md` (ready-first example)

### Design and Prompt Checklist

- [ ] Prompt source file is referenced in PR description
- [ ] Output variants are version-tagged (`v1.0`, `v1.1`)
- [ ] Negative prompt constraints are preserved
- [ ] Visual matches `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- [ ] Token policy matches `docs/design/TOKENS_SOT.md`

### Frontend Integration Checklist

- [ ] Component path(s) listed explicitly
- [ ] Reduced-motion fallback is implemented (if motion exists)
- [ ] Contrast/readability validated on mobile and desktop
- [ ] No raw-hex drift outside token SoT allowlist
- [ ] No direct API/client policy regressions in touched components

### QA and Safety Checklist

- [ ] `docs/sora/SORA_STYLE_QA_CHECKLIST.md` pass documented
- [ ] Wellness-safe semantics confirmed (non-clinical)
- [ ] No manipulative urgency/fear visuals
- [ ] Small-size readability check passed (24/32 px where relevant)

## 4) Recommended Execution Order

1. P0 bundle A: Home Hero Ambient Layer + Onboarding Trust Canvas.
2. P0 bundle B: Progress Momentum Ring + Premium Gate Value Frame.
3. P1 bundle: Setup Step Rail + BMI Confidence Card + Smart Empty States.
4. P2 bundle under feature/campaign toggles.

## 5) Security Notes

- Prompts and assets must never include secrets, keys, private URLs, or sensitive metadata.
- Visuals must remain wellness-lifestyle oriented and avoid medical diagnosis implication.
- Any campaign variant still follows the same anti-drift and safety gates.

## 6) Marketing and GTM Notes

- ASO-first: deploy P0 visuals for first-impression screenshots and app-preview frames.
- Product Hunt: showcase before/after from P0 and P1 upgrades.
- Social loops: reuse low-motion assets from Home ambient and Progress ring.

## 7) Decision Log

- Map built from current web route structure and existing component ownership.
- Priority order is optimized for visibility impact first, then polish layers.
- Checklist format is designed to reduce design-dev handoff ambiguity.
