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
| FITCHEF_ACTION_COOKING_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Seed-aligned action frame, safe for mascot-led composition. |
| FITCHEF_ACTION_HEALTHY_CHOICE_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Keep as approved-seed reference frame only in this PR lane. |
| FITCHEF_ACTION_HYDRATION_REMINDER_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Supportive wellness cue without medical language. |
| FITCHEF_ACTION_MEAL_PLANNING_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Preserves FitChef silhouette and emotional tone. |
| FITCHEF_ACTION_NUTRITION_PLATE_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Nutrition context is visual, not diagnostic. |
| FITCHEF_ACTION_PROGRESS_TRACKING_V1 | APPROVED-SEED | action | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Compatible with progress storytelling in wellness-safe framing. |
| FITCHEF_ACTION_SHOPPING_LIST_V1 | CANDIDATE | action | partial | minor_ui | medium | low | social_only | no_runtime_promotion | keep candidate | Good campaign support, keep out of runtime until promotion PR. |
| FITCHEF_ACTION_WORKOUT_COACH_V1 | CANDIDATE | action | partial | minor_ui | medium | medium | needs_rework | blocked_runtime | needs-rework | "Coach" framing can read as regulated/medical-adjacent promise. |
| FITCHEF_MARKETING_BREAKFAST_PROMO_V1 | CANDIDATE | marketing | partial | dominant_text | high | medium | reject_for_app_store | no_runtime_promotion | reject | Promo-heavy language needs complete copy rework. |
| FITCHEF_MARKETING_FITNESS_MOTIVATION_V1 | CANDIDATE | marketing | partial | minor_ui | medium | medium | social_only | no_runtime_promotion | keep candidate | Keep for social tests with stricter claim-safe captions. |
| FITCHEF_MARKETING_HEALTHY_LIFESTYLE_V1 | CANDIDATE | marketing | pass | minor_ui | medium | low | app_store_supporting_hold | no_runtime_promotion | keep candidate | May be used after localization and wording QA. |
| FITCHEF_MARKETING_NUTRITION_EDUCATION_V1 | CANDIDATE | marketing | pass | minor_ui | medium | low | app_store_supporting_hold | no_runtime_promotion | keep candidate | Educational tone is acceptable if copy avoids guarantees. |
| FITCHEF_ONBOARDING_BUILD_MEAL_PLAN_V1 | CANDIDATE | onboarding | pass | minor_ui | medium | low | onboarding_candidate | no_runtime_promotion | promotion proposal | Candidate for future onboarding lane, requires separate PR. |
| FITCHEF_ONBOARDING_CALCULATE_NUTRITION_V1 | CANDIDATE | onboarding | partial | minor_ui | medium | medium | onboarding_candidate | no_runtime_promotion | needs-rework | Must avoid diagnostic semantics in surrounding copy. |
| FITCHEF_ONBOARDING_PROFILE_SETUP_V1 | CANDIDATE | onboarding | pass | none | low | low | onboarding_candidate | no_runtime_promotion | promotion proposal | Strong onboarding visual, reserve for dedicated promotion lane. |
| FITCHEF_ONBOARDING_START_COOKING_V1 | NEEDS-REWORK | onboarding | partial | minor_ui | medium | medium | needs_rework | blocked_runtime | needs-rework | Intake board marks this lane as needs-rework. |
| FITCHEF_ONBOARDING_TRACK_PROGRESS_V1 | CANDIDATE | onboarding | pass | none | low | low | onboarding_candidate | no_runtime_promotion | promotion proposal | Progress-oriented mood works if claims stay informational. |
| FITCHEF_ONBOARDING_WELCOME_V1 | APPROVED-SEED | onboarding | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Matches canonical onboarding welcome mascot framing. |
| FITCHEF_PORTRAIT_CONCERNED_V1 | CANDIDATE | portrait | fail | none | low | medium | blocked_gtm | blocked_runtime | reject | Concerned affect drifts toward clinical anxiety tone. |
| FITCHEF_PORTRAIT_CURIOUS_V1 | CANDIDATE | portrait | pass | none | low | low | social_only | no_runtime_promotion | keep candidate | Supportive expression, usable in non-runtime campaign comps. |
| FITCHEF_PORTRAIT_ENCOURAGING_V1 | CANDIDATE | portrait | pass | none | low | low | app_store_supporting_hold | no_runtime_promotion | keep candidate | Strong wellness-safe affect, hold until localization pass. |
| FITCHEF_PORTRAIT_FOCUSED_V1 | CANDIDATE | portrait | pass | none | low | low | social_only | no_runtime_promotion | keep candidate | Retains identity markers and compact silhouette. |
| FITCHEF_PORTRAIT_HAPPY_V1 | CANDIDATE | portrait | pass | none | low | low | social_only | no_runtime_promotion | keep candidate | Positive emotion lane suitable for campaign variants. |
| FITCHEF_PORTRAIT_LAUGHING_V1 | CANDIDATE | portrait | partial | none | low | low | social_only | no_runtime_promotion | reference-only | Keep as exploration; expression may be too playful for runtime. |
| FITCHEF_PORTRAIT_NEUTRAL_V1 | APPROVED-SEED | portrait | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Canonical neutral portrait baseline. |
| FITCHEF_PORTRAIT_PROUD_V1 | CANDIDATE | portrait | partial | none | low | low | social_only | no_runtime_promotion | keep candidate | Brand-fit acceptable but needs consistency pass vs seed linework. |
| FITCHEF_PORTRAIT_SLEEPY_V1 | APPROVED-SEED | portrait | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Canonical sleepy portrait retained. |
| FITCHEF_PORTRAIT_SURPRISED_V1 | APPROVED-SEED | portrait | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Canonical surprised portrait retained. |
| FITCHEF_PORTRAIT_THINKING_V1 | APPROVED-SEED | portrait | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Canonical thinking portrait retained. |
| FITCHEF_PORTRAIT_WINK_V1 | APPROVED-SEED | portrait | pass | none | low | low | app_store_candidate | no_runtime_promotion | keep candidate | Canonical wink portrait retained. |

## Review outcome

- All 30 intake assets now have disposition coverage.
- Embedded-text and localization risk are explicitly captured per row.
- Marketing-use vs runtime-use separation is explicit per row.
- Runtime promotion remains blocked in this docs-only lane.
