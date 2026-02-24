<!-- markdownlint-disable MD013 -->
# PulsePlate Visual Element Prompt Catalog

Date created: February 24, 2026 (America/New_York)
Status: Working catalog
Scope: Index of visual elements and links to canonical prompt packs

## 1) Purpose

This document is a navigation catalog only.
It does not define new visual rules or policy.

Authoritative policy/rules remain only in:

- `docs/sora/prompts/brand_core/FITCHEF_IDENTITY_PROFILE_v1.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/TOKENS_SOT.md`

## 2) Runtime Evidence Anchors

Route/source anchors:

- Routes list: `frontend/src/config/routes.ts:24`
- Home route: `frontend/src/config/routes.ts:24`
- Plate route: `frontend/src/config/routes.ts:28`
- Progress route: `frontend/src/config/routes.ts:29`
- Setup route: `frontend/src/config/routes.ts:26`
- BMI route: `frontend/src/config/routes.ts:30`
- Pro route: `frontend/src/config/routes.ts:31`
- EnterKey route: `frontend/src/config/routes.ts:25`

Component anchors:

- Home screen: `frontend/src/pages/Home.tsx:7`
- Plate screen: `frontend/src/pages/Plate.tsx:8`
- Progress screen: `frontend/src/pages/Progress.tsx:9`
- Setup flow: `frontend/src/pages/NutritionSetup/index.tsx:1`
- BMI screen: `frontend/src/pages/BMI/BMICalculatePage.tsx:21`
- Pro paywall screen: `frontend/src/pages/Pro/ProPaywallPage.tsx:7`
- EnterKey screen: `frontend/src/pages/Onboarding/EnterKey.tsx:64`

Exit criteria for this section:

- Update anchors whenever route/component ownership changes in the files above.

## 3) Visual Element Index

| ID | Element | Priority | Surface | Prompt Pack |
| --- | --- | --- | --- | --- |
| 01 | Home Hero Ambient Layer | P0 | Home | `docs/sora/prompts/hpp/p0_visibility/home_hero_ambient__home__v1.0.md` |
| 02 | Progress Momentum Ring + Weekly Streak Badge | P0 | Progress | `docs/sora/prompts/hpp/p0_visibility/progress_momentum_ring__progress__v1.0.md` |
| 03 | Premium Gate Value Frame | P0 | Plate/Pro | `docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md` |
| 04 | Onboarding Trust Canvas | P0 | EnterKey | `docs/sora/prompts/hpp/p0_visibility/onboarding_trust_canvas__enter_key__v1.0.md` |
| 05 | Setup Completion Step Rail | P1 | Setup | `docs/sora/prompts/hpp/p1_polish/setup_completion_step_rail__setup__v1.0.md` |
| 06 | BMI Result Confidence Card | P1 | BMI | `docs/sora/prompts/hpp/p1_polish/bmi_result_confidence_card__bmi__v1.0.md` |
| 07 | Smart Empty States Pack | P1 | Plate/Progress | `docs/sora/prompts/hpp/p1_polish/smart_empty_states_pack__plate_progress__v1.0.md` |
| 08 | Tab Bar Active Trail Micro-Motion | P2 | TabBar | `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md` |
| 09 | Export Success Celebration Chip | P2 | Progress export | `docs/sora/prompts/hpp/p2_expressive/export_success_celebration_chip__progress__v1.0.md` |
| 10 | Seasonal Theme Accent Pack | P2 | Home/Progress | `docs/sora/prompts/hpp/p2_expressive/seasonal_theme_accent_pack__home_progress__v1.0.md` |

Execution dependency note:

- P1 starts only after P0 consistency pass.
- P2 remains toggle/campaign-scoped.

## 4) Security Notes

Security requirements are canonical in:

- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`

## 5) Marketing and GTM Notes

GTM planning references:

- `docs/sora/BRAND_THROUGHPUT_METRICS_GTM_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`

## 6) Next Actions

- Use `docs/design/VISUAL_IMPLEMENTATION_MAP.md` for component-level planning.
- Use `docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md` for PR body drafts.
