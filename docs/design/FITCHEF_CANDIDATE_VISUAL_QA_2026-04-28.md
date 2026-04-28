# FitChef Candidate Visual QA Matrix (2026-04-28)

Status: `Reference-only intake review`
Scope: `Figma board 1473:2 candidate audit`
Figma source: `2JDwOByQIbcPgp93FDzHii` node `1473:2`

## Canonical boundaries

- Canonical seed pack remains locked in `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`.
- This matrix does not promote assets into runtime.
- No candidate from this matrix may be added to:
  - `frontend/src/assets/brand/*`
  - `ios/PulsePlate/Assets.xcassets/*`
  without a separate promotion PR.

## Disposition vocabulary

- `keep candidate`
- `reference-only`
- `needs-rework`
- `reject`
- `promotion proposal`

## Visual QA matrix

| asset_id | current_status | asset_type | visual_fitchef_identity | embedded_text_risk | localization_risk | wellness_safety_risk | marketing_use | runtime_use | disposition | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fitchef-candidate-001 | APPROVED-SEED | portrait | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-portrait-neutral-v1.png`. |
| fitchef-candidate-002 | APPROVED-SEED | portrait | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-portrait-wink-v1.png`. |
| fitchef-candidate-003 | APPROVED-SEED | portrait | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-portrait-thinking-v1.png`. |
| fitchef-candidate-004 | APPROVED-SEED | portrait | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-portrait-sleepy-v1.png`. |
| fitchef-candidate-005 | APPROVED-SEED | portrait | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-portrait-surprised-v1.png`. |
| fitchef-candidate-006 | APPROVED-SEED | onboarding | pass | none | low | low | approved_seed | canon_aligned | keep candidate | Canonical seed: `fitchef-onboarding-welcome-v1.png`. |
| fitchef-candidate-007 | CANDIDATE | action | partial | minor_ui | medium | low | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_ACTION_SHOPPING_LIST_V1`; social-first usage. |
| fitchef-candidate-008 | CANDIDATE | action | partial | minor_ui | medium | medium | blocked_gtm | blocked_runtime | needs-rework | Maps to `FITCHEF_ACTION_WORKOUT_COACH_V1`; requires claim-safe rework. |
| fitchef-candidate-009 | CANDIDATE | marketing | partial | dominant_text | high | medium | blocked_gtm | no_runtime_promotion | reject | Maps to `FITCHEF_MARKETING_BREAKFAST_PROMO_V1`; promo-heavy text risk. |
| fitchef-candidate-010 | CANDIDATE | marketing | partial | minor_ui | medium | medium | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_MARKETING_FITNESS_MOTIVATION_V1`; campaign-only lane. |
| fitchef-candidate-011 | CANDIDATE | marketing | pass | minor_ui | medium | low | aso_supporting_hold | no_runtime_promotion | keep candidate | Maps to `FITCHEF_MARKETING_HEALTHY_LIFESTYLE_V1`; hold for localization pass. |
| fitchef-candidate-012 | CANDIDATE | marketing | pass | minor_ui | medium | low | aso_supporting_hold | no_runtime_promotion | keep candidate | Maps to `FITCHEF_MARKETING_NUTRITION_EDUCATION_V1`; wording review required. |
| fitchef-candidate-013 | CANDIDATE | onboarding | pass | minor_ui | medium | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_ONBOARDING_BUILD_MEAL_PLAN_V1`; archive until promotion lane. |
| fitchef-candidate-014 | CANDIDATE | onboarding | partial | minor_ui | medium | medium | aso_supporting_hold | no_runtime_promotion | needs-rework | Maps to `FITCHEF_ONBOARDING_CALCULATE_NUTRITION_V1`; avoid diagnostic tone. |
| fitchef-candidate-015 | CANDIDATE | onboarding | pass | none | low | low | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_ONBOARDING_PROFILE_SETUP_V1`; candidate only. |
| fitchef-candidate-016 | CANDIDATE | onboarding | partial | minor_ui | medium | medium | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_ONBOARDING_START_COOKING_V1`; non-runtime usage only. |
| fitchef-candidate-017 | CANDIDATE | onboarding | pass | none | low | low | aso_supporting_hold | no_runtime_promotion | promotion proposal | Maps to `FITCHEF_ONBOARDING_TRACK_PROGRESS_V1`; proposal requires separate PR. |
| fitchef-candidate-018 | CANDIDATE | onboarding | pass | none | low | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_ONBOARDING_WELCOME_V1`; reference lane here despite seed relation. |
| fitchef-candidate-019 | CANDIDATE | portrait | fail | none | low | medium | blocked_gtm | blocked_runtime | reject | Maps to `FITCHEF_PORTRAIT_CONCERNED_V1`; clinical-affect drift risk. |
| fitchef-candidate-020 | CANDIDATE | portrait | pass | none | low | low | aso_supporting_hold | no_runtime_promotion | keep candidate | Maps to `FITCHEF_PORTRAIT_CURIOUS_V1`; hold for App Store readability QA. |
| fitchef-candidate-021 | CANDIDATE | portrait | pass | none | low | low | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_PORTRAIT_ENCOURAGING_V1`; acceptable when paired with a compliant caption. |
| fitchef-candidate-022 | CANDIDATE | portrait | pass | none | low | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_PORTRAIT_FOCUSED_V1`; keep as concept/archive lane. |
| fitchef-candidate-023 | CANDIDATE | portrait | pass | none | low | low | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_PORTRAIT_HAPPY_V1`; social rotation candidate. |
| fitchef-candidate-024 | CANDIDATE | portrait | partial | none | low | low | blocked_gtm | blocked_runtime | needs-rework | Maps to `FITCHEF_PORTRAIT_LAUGHING_V1`; over-playful tone for storefront. |
| fitchef-candidate-025 | CANDIDATE | portrait | pass | none | low | low | aso_supporting_hold | no_runtime_promotion | keep candidate | Maps to `FITCHEF_PORTRAIT_NEUTRAL_V1`; hold in candidate lane for this intake pass. |
| fitchef-candidate-026 | CANDIDATE | portrait | partial | none | low | low | social_ready | no_runtime_promotion | keep candidate | Maps to `FITCHEF_PORTRAIT_PROUD_V1`; style consistency pass still needed. |
| fitchef-candidate-027 | REFERENCE-ONLY | portrait | pass | none | low | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_PORTRAIT_SLEEPY_V1`; explicitly reference-only batch slot. |
| fitchef-candidate-028 | REFERENCE-ONLY | portrait | pass | none | low | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_PORTRAIT_SURPRISED_V1`; archive-only lane. |
| fitchef-candidate-029 | REFERENCE-ONLY | portrait | pass | none | low | low | reference_archive | no_runtime_promotion | reference-only | Maps to `FITCHEF_PORTRAIT_THINKING_V1`; archive-only lane. |
| fitchef-candidate-030 | NEEDS-REWORK | portrait | pass | none | low | low | blocked_gtm | blocked_runtime | needs-rework | Maps to `FITCHEF_PORTRAIT_WINK_V1`; intake marks this slot as mandatory rework. |

## Review outcome

- All 30 intake assets now have disposition coverage.
- Embedded-text and localization risk are explicitly captured per row.
- Marketing-use vs runtime-use separation is explicit per row.
- Runtime promotion remains blocked in this docs-only lane.
