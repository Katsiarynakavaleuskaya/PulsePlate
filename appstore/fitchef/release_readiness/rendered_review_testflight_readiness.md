# FitChef App Store Rendered Review and TestFlight Readiness

Classification: INTERNAL_REVIEW_ONLY

This bundle moves the EN/RU/ES FitChef App Store packs into a repo-local rendered-review and TestFlight-smoke preparation lane. It does not mutate protected Fastlane metadata, App Store Connect state, screenshot or preview binaries, iOS runtime code, backend routes, telemetry, billing, semantic cache, GraphRAG, or Slack behavior.

## Source Of Truth

- Scenario matrix: `appstore/fitchef/release_readiness/shot_scenario_matrix.json`
- Locale packs: `appstore/fitchef/en-US`, `appstore/fitchef/ru-RU`, `appstore/fitchef/es-ES`
- Screenshot gate: `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md`
- Reviewer matrix: `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md`
- iOS screenshot context: `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift`
- iOS UI tests: `ios/PulsePlateUITests/AppStoreScreenshotTests.swift`
- Local gate: `make ios-appstore-verify`

## Review Contract

The human pass must render all seven shots for each locale before any protected upload follow-up. Each rendered shot must be checked for:

- copy wrapping and line-fit risk;
- safe-area clipping on the 6.9-inch baseline;
- FitChef mascot, logo, and UI overlap;
- mismatch between locale copy and the actual product surface;
- wellness-only language with no diagnosis, treatment, therapy, crisis-support, guaranteed outcome, clinical nutrition, pricing, or trial claim.

## TestFlight Smoke Prep

The TestFlight smoke pass is preparation only. It should confirm that the screenshot scenarios can be exercised from the governed iOS screenshot context, that accessibility identifiers still match the matrix, and that the rendered output aligns with reviewer notes. Evidence from this pass must stay separate from protected App Store upload follow-ups.

## Scenario Summary

| Shot | Scenario | UI-test screenshot | Accessibility identifier | Current public-use gate | Rendered review |
|---|---|---|---|---|---|
| shot-01 | core_value | `01_core-value` | `appstore.core_value.screen` | Core screenshot only | Required for EN/RU/ES |
| shot-02 | nutrition_analysis | `02_nutrition-analysis` | `appstore.nutrition_analysis.screen` | Implementation follow-up required | Required for EN/RU/ES |
| shot-03 | meal_planner | `03_meal-planner` | `appstore.meal_planner.screen` | Implementation follow-up required | Required for EN/RU/ES |
| shot-04 | grocery_list | `04_grocery-list` | `appstore.grocery_list.screen` | Implementation follow-up required | Required for EN/RU/ES |
| shot-05 | health_progress | `05_health-progress` | `appstore.health_progress.screen` | Implementation follow-up required | Required for EN/RU/ES |
| shot-06 | personalization | `06_personalization` | `appstore.personalization.screen` | Implementation follow-up required | Required for EN/RU/ES |
| shot-07 | ai_assistant | `07_ai-assistant` | `appstore.ai_assistant.screen` | Implementation follow-up required | Required for EN/RU/ES |

## Manual Checklist

- [ ] Run `make ios-appstore-verify` before capturing rendered-review evidence.
- [ ] Render `shot-01` through `shot-07` for `en-US`, `ru-RU`, and `es-ES`.
- [ ] Compare rendered screenshots against `shot_scenario_matrix.json`.
- [ ] Confirm copy remains wellness-only and bounded to habit, planning, nutrition-literacy, and preference-support language.
- [ ] Confirm AI assistant copy includes wellness-only framing and does not imply therapy, diagnosis, crisis support, medical care, or clinical nutrition advice.
- [ ] Confirm no screenshot or preview binary is committed by this preparation pass.
- [ ] Keep Fastlane upload, App Store Connect mutation, binary export, and protected environment activation as separate operator-owned follow-ups.
