<!-- markdownlint-disable MD013 -->
# PulsePlate Visual Implementation Map

Date created: February 24, 2026 (America/New_York)
Status: Working map
Scope: Visual element -> frontend ownership mapping

## 1) Purpose

This document is an implementation map only.
It does not define new visual policy.

Canonical governance references:

- `docs/sora/VISUAL_GOVERNANCE_INDEX.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`

## 2) Mapping Table (with Evidence Anchors)

| Visual Element | Priority | Frontend Paths | Evidence (file:line) | Prompt Pack | Exit Criteria |
| --- | --- | --- | --- | --- | --- |
| Home Hero Ambient Layer | P0 | `frontend/src/pages/Home.tsx` | `frontend/src/pages/Home.tsx:7` | `docs/sora/prompts/hpp/p0_visibility/home_hero_ambient__home__v1.0.md` | Update when Home hero layout ownership changes. |
| Progress Momentum Ring + Weekly Streak Badge | P0 | `frontend/src/pages/Progress.tsx`, `frontend/src/features/progress/LiveProgressIndicator.tsx` | `frontend/src/pages/Progress.tsx:9`, `frontend/src/features/progress/LiveProgressIndicator.tsx:18` | `docs/sora/prompts/hpp/p0_visibility/progress_momentum_ring__progress__v1.0.md` | Update when progress indicator implementation moves. |
| Premium Gate Value Frame | P0 | `frontend/src/components/PremiumGate.tsx`, `frontend/src/components/Paywall/BeforeAfter.tsx` | `frontend/src/components/PremiumGate.tsx:24`, `frontend/src/components/Paywall/BeforeAfter.tsx:47` | `docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md` | Update when paywall component ownership changes. |
| Onboarding Trust Canvas | P0 | `frontend/src/pages/Onboarding/EnterKey.tsx` | `frontend/src/pages/Onboarding/EnterKey.tsx:64` | `docs/sora/prompts/hpp/p0_visibility/onboarding_trust_canvas__enter_key__v1.0.md` | Update when key-entry flow is replaced. |
| Setup Completion Step Rail | P1 | `frontend/src/pages/NutritionSetup/SetupForm.tsx`, `frontend/src/pages/NutritionSetup/ResultView.tsx` | `frontend/src/pages/NutritionSetup/SetupForm.tsx:14`, `frontend/src/pages/NutritionSetup/ResultView.tsx:18` | `docs/sora/prompts/hpp/p1_polish/setup_completion_step_rail__setup__v1.0.md` | Apply after P0 consistency pass. |
| BMI Result Confidence Card | P1 | `frontend/src/pages/BMI/BMICalculatePage.tsx` | `frontend/src/pages/BMI/BMICalculatePage.tsx:21` | `docs/sora/prompts/hpp/p1_polish/bmi_result_confidence_card__bmi__v1.0.md` | Apply after P0 consistency pass. |
| Smart Empty States Pack | P1 | `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Progress.tsx`, `frontend/src/components/ui/EmptyState.tsx` | `frontend/src/pages/Plate.tsx:8`, `frontend/src/pages/Progress.tsx:9`, `frontend/src/components/ui/EmptyState.tsx:11` | `docs/sora/prompts/hpp/p1_polish/smart_empty_states_pack__plate_progress__v1.0.md` | Apply after P0 consistency pass. |
| Tab Bar Active Trail Micro-Motion | P2 | `frontend/src/components/TabBar.tsx` | `frontend/src/components/TabBar.tsx:9` | `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md` | Keep behind feature/campaign toggle strategy. |
| Export Success Celebration Chip | P2 | `frontend/src/features/progress/ProgressCharts.tsx` | `frontend/src/features/progress/ProgressCharts.tsx:1` | `docs/sora/prompts/hpp/p2_expressive/export_success_celebration_chip__progress__v1.0.md` | Keep behind feature/campaign toggle strategy. |
| Seasonal Theme Accent Pack | P2 | `frontend/src/pages/Home.tsx`, `frontend/src/pages/Progress.tsx` | `frontend/src/pages/Home.tsx:7`, `frontend/src/pages/Progress.tsx:9` | `docs/sora/prompts/hpp/p2_expressive/seasonal_theme_accent_pack__home_progress__v1.0.md` | Keep behind feature/campaign toggle strategy. |

## 3) PR Authoring References

Use these canonical templates/checklists instead of defining local rule copies here:

- `.github/PULL_REQUEST_TEMPLATE/visuals.md`
- `docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md`
- `.github/pr_body_visual_p2_tab_bar_active_trail.md`

## 4) Execution Order

1. P0 bundle first.
2. P1 bundle only after P0 consistency pass.
3. P2 bundle only as optional toggle/campaign layer.

Before visual planning or prompt-pack execution:

1. Resolve canonical component names through `docs/design/ui_component_vocabulary.json`.
2. Build the screen brief using `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`.
3. Then map the visual element to page ownership and prompt-pack execution.

## 5) Security and GTM References

- Security/QA: `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
- UX quality: `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- GTM: `docs/sora/BRAND_THROUGHPUT_METRICS_GTM_MATRIX.md`
