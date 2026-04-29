# App Store Feature Asset Matrix

**Date:** 2026-04-29

This matrix is the canonical release-readiness map for App Store screenshots,
metadata claims, privacy disclosure, and reviewer-note coverage. Assets may
remain in repo even when they are not submission-ready.

Submission status values:

- `SUBMIT_READY`: may be used in App Store screenshots or metadata.
- `IMPLEMENTATION_REQUIRED`: kept in repo/Figma/Fastlane, blocked from public
  submission until implementation and smoke proof exist.
- `INTERNAL_REVIEW_ONLY`: allowed for QA, reviewer, or debug boards only.

| Feature | Runtime file | Backend endpoint | Release flag | Privacy disclosure | Consent needed | Asset scenario | Submission status | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core value / Home | `ios/PulsePlate/Views/HomeView.swift` | Existing app shell and auth-dependent API calls | None | No additional disclosure beyond app metadata | No | `core_value` | `SUBMIT_READY` after PR-8 metadata sync | `ios/PulsePlateUITests/AppStoreScreenshotTests.swift` |
| Nutrition analysis / Plate | `ios/PulsePlate/Views/PlateView.swift`, `ios/PulsePlate/Services/ProDailyNutritionService.swift` | `/api/v1/pro/nutrition/daily` | PRO access and backend entitlement truth | Profile and wellness/nutrition context must be disclosed | Profile notice required | `nutrition_analysis` | `IMPLEMENTATION_REQUIRED` until PR-1, PR-3, and reviewer notes align | `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift` |
| Meal planner / weekly plan | `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`, `ios/PulsePlate/Utilities/FeatureFlags.swift` | `/api/v1/pro/meal/weekly` | `FeatureFlags.weeklyPlanReaderEnabled` | Profile, meal planning, and backend processing disclosure | Feature notice required | `meal_planner` | `IMPLEMENTATION_REQUIRED` while Release flag is disabled | `ios/PulsePlateTests/WeeklyPlanReaderViewModelTests.swift` |
| Grocery list | `ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift`, `ios/PulsePlate/Utilities/FeatureFlags.swift` | `/api/v1/pro/meal/shopping-list` | Weekly-plan dependent release flag | Meal plan and shopping-list processing disclosure | Feature notice required | `grocery_list` | `IMPLEMENTATION_REQUIRED` until source-of-plan and backend smoke are release-ready | `ios/PulsePlateTests/ShoppingListReaderViewModelTests.swift` |
| Health progress | `ios/PulsePlate/Models/HealthKitManager.swift`, `ios/PulsePlate/Views/WeeklyProgressView.swift` | Local HealthKit read path plus app progress surfaces | HealthKit capability and user authorization | Health data read-only disclosure in App Privacy and reviewer notes | Apple Health authorization required | `health_progress` | `IMPLEMENTATION_REQUIRED` until PR-6 reviewer notes and Swift 6 cleanup land | `ios/PulsePlateTests/HealthKitManagerTests.swift` |
| Personalization profile | `ios/PulsePlate/Views/ProfileView.swift`, `ios/PulsePlate/Services/ProfileProvider.swift` | `/api/v1/pro/nutrition/daily` query parameters | PRO access and backend entitlement truth | Profile data disclosure required | Profile notice required | `personalization` | `IMPLEMENTATION_REQUIRED` until PR-1 privacy truth and PR-8 metadata sync land | `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift` |
| AI assistant / CBT insight | `ios/PulsePlate/Views/AIInsightView.swift`, `ios/PulsePlate/Services/CBTInsightService.swift` | `/api/v1/pro/cbt/insight` | `FeatureFlags.aiInsightEnabled` | User content / free-form AI query plus backend processing disclosure | Explicit AI wellness consent required | `ai_assistant` | `IMPLEMENTATION_REQUIRED` until PR-7 consent and PR-8 metadata sync land | `ios/PulsePlateTests/AIInsightViewModelTests.swift` |
| Paywall / StoreKit | `ios/PulsePlate/Screens/PaywallScreen.swift`, `ios/PulsePlate/Services/SubscriptionManager.swift` | `/api/v1/billing/apple/verify-receipt`, `/api/v1/pro/payments/activations` | StoreKit availability plus backend activation truth | Purchase/subscription and receipt processing disclosure required | StoreKit purchase consent; no separate AI consent | Existing paywall screenshot surfaces | `IMPLEMENTATION_REQUIRED` until App Privacy and reviewer notes align | `ios/PulsePlateTests/Services/SubscriptionManagerTests.swift` |
| AppIcon marketing asset | `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset` | N/A | N/A | N/A | No | App icon / marketing asset | `IMPLEMENTATION_REQUIRED` until PR-5 actool validation passes | `tests/test_ios_appstore_asset_validators.py` plus PR-5 asset test |

## Submission Rule

An asset scenario may be exported for App Store submission only when all are
true:

```text
status == SUBMIT_READY
AND Release runtime flag is enabled when applicable
AND backend endpoint smoke passed when applicable
AND App Privacy disclosure covers the data flow
AND consent/notice exists when required
AND reviewer note explains the exact flow
```

Assets that fail this rule stay in repo and design source, but the submission
pipeline must block them from public metadata/screenshots.
