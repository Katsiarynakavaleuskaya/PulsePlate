# App Store Reviewer Submission Matrix

**Date:** 2026-05-01

**Epic:** `epic/appstore-release-readiness-full-feature`

**PR lane:** `release/appstore-readiness-pr3-reviewer-submission-matrix`

**Note:** This document is delivered by a dedicated reviewer-submission-matrix PR.
The original epic PR-3 (`release/appstore-readiness-pr3-base-url`) remains the
Release backend fail-fast lane. Both are part of the same epic train but are
distinct tracks with separate scope.

## Purpose

Define the canonical release-review matrix that maps each App Store-visible
surface to runtime readiness, privacy disclosure state, permission-string state,
reviewer-note requirement, screenshot/asset readiness, and final submission
classification.

This document is the single source of truth for determining which surfaces may
appear in a public App Store submission and which require further implementation,
privacy alignment, or internal review before export.

Root `AGENTS.md` section `App Store release readiness gates` remains the
hard-gate source of truth for release readiness checks. This matrix is the
planning mirror that maps each surface to the gate list.

## Classification Enum

| Classification | Meaning |
| --- | --- |
| `SUBMIT_READY` | Surface may appear in public App Store screenshots, metadata, and reviewer notes. Runtime is release-enabled, privacy is disclosed, consent exists where required, and reviewer notes explain the flow. |
| `IMPLEMENTATION_REQUIRED` | Surface exists as repo/design asset but is blocked from public submission until implementation, smoke proof, privacy disclosure, or reviewer-note coverage is complete. |
| `INTERNAL_REVIEW_ONLY` | Surface is allowed for QA, reviewer boards, or debug use only. Not for public App Store metadata or screenshots. |
| `BLOCKED` | Surface cannot proceed until a specific blocker is resolved. Blocker is linked to `BACKLOG_LEDGER.md`. |

## Submission Surfaces Matrix

### Core Surfaces

| Surface | Repo Evidence | User-Visible Claim | Data Collected/Shared | Permission Required? | Reviewer Note Required? | Screenshot Allowed? | Classification | Required Next Action | Backlog Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| App Launch / Welcome Gate | `ios/PulsePlate/Views/HomeView.swift` | App shell, language selection, welcome flow | No additional data beyond app metadata | No | No (standard app launch) | Yes | `SUBMIT_READY` | PR-8 (planned) metadata sync | -- |
| BMI / Free Calculation | `ios/PulsePlate/Views/BMIFormView.swift`, backend `/api/v1/bmi/calculate` | Free BMI calculation with category | Height, weight (sent to backend) | No | Yes (explain free tier scope) | Yes | `SUBMIT_READY` | PR-8 (planned) reviewer notes must explain free BMI flow | -- |
| Nutrition Setup / Profile | `ios/PulsePlate/Views/ProfileView.swift`, `ios/PulsePlate/Services/ProfileProvider.swift` | Profile-based nutrition targets | Profile data (age, sex, height, weight, activity, goal) sent to backend | No | Yes (profile data disclosure) | No | `IMPLEMENTATION_REQUIRED` | PR-1 (merged) privacy truth; PR-8 (planned) reviewer notes | -- |
| PRO Planning Flow | `ios/PulsePlate/Views/PlateView.swift`, `ios/PulsePlate/Services/ProDailyNutritionService.swift`, backend `/api/v1/pro/nutrition/daily` | PRO daily nutrition analysis | Profile + nutrition context to backend | No | Yes (PRO tier, backend processing) | No | `IMPLEMENTATION_REQUIRED` | PR-3 (planned) explicit HTTPS BASE_URL; PR-8 (planned) reviewer notes | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| VIP Weekly Plan | `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`, backend `/api/v1/pro/meal/weekly` | Weekly meal planning | Profile + meal plan data to backend | No | Yes (VIP tier, meal planning) | No | `IMPLEMENTATION_REQUIRED` | Feature flag `weeklyPlanReaderEnabled` must be release-enabled; PR-8 (planned) reviewer notes | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| FitChef / AI Wellness Assistant | `ios/PulsePlate/Views/AIInsightView.swift`, `ios/PulsePlate/Services/CBTInsightService.swift`, backend `/api/v1/pro/cbt/insight` | AI-powered wellness reflection | User free-form text + profile context to backend and LLM provider | No | Yes (AI disclosure, third-party provider, wellness-only positioning) | No | `IMPLEMENTATION_REQUIRED` | PR-7 (planned) AI consent gate; PR-8 (planned) reviewer notes with AI/provider disclosure | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| CBT / Reflection / Coaching Copy | Same as FitChef / AI surface above | Wellness reflection and habit coaching | Same as AI assistant | No | Yes (must clarify: not therapy, not diagnosis, not treatment) | No | `IMPLEMENTATION_REQUIRED` | PR-7 (planned) consent; PR-8 (planned) wellness-only copy validation | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |

### Billing and Subscription Surfaces

| Surface | Repo Evidence | User-Visible Claim | Data Collected/Shared | Permission Required? | Reviewer Note Required? | Screenshot Allowed? | Classification | Required Next Action | Backlog Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Paywall / StoreKit / Subscription | `ios/PulsePlate/Screens/PaywallScreen.swift`, `ios/PulsePlate/Services/SubscriptionManager.swift`, backend `/api/v1/billing/apple/verify-receipt` | PRO/VIP subscription purchase | Purchase history, receipt data to backend | No | Yes (StoreKit flow, backend activation, pricing from App Store Connect only) | No | `IMPLEMENTATION_REQUIRED` | PR-1 (merged) App Privacy; PR-8 (planned) reviewer notes must reference StoreKit truth for pricing | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |

### Privacy and Compliance Surfaces

| Surface | Repo Evidence | User-Visible Claim | Data Collected/Shared | Permission Required? | Reviewer Note Required? | Screenshot Allowed? | Classification | Required Next Action | Backlog Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| App Privacy Package | `ios/fastlane/app_privacy_details.json` | App Privacy declarations in App Store Connect | Declares HEALTH, PURCHASE_HISTORY, OTHER_USER_CONTENT as DATA_LINKED_TO_YOU | No | Yes (must match actual runtime data flows) | N/A | `SUBMIT_READY` | PR-1 (merged) corrected DATA_NOT_COLLECTED to accurate disclosures | -- |
| PrivacyInfo.xcprivacy | `ios/PulsePlate/PrivacyInfo.xcprivacy` | Required-reason API disclosure | UserDefaults (CA92.1) | No | No (Apple-required manifest, not user-visible) | N/A | `SUBMIT_READY` | PR-1 (merged) added privacy manifest | -- |
| Legal Links: Privacy Policy | App Store metadata, in-app settings | Privacy policy URL | N/A | No | Yes (URL must be live and accurate) | N/A | `IMPLEMENTATION_REQUIRED` | PR-8 (planned) must verify live privacy policy URL in metadata | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Legal Links: Terms of Use | App Store metadata, in-app settings | Terms of use URL | N/A | No | Yes (URL must be live and accurate) | N/A | `IMPLEMENTATION_REQUIRED` | PR-8 (planned) must verify live terms URL in metadata | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |

### Health and Device Surfaces

| Surface | Repo Evidence | User-Visible Claim | Data Collected/Shared | Permission Required? | Reviewer Note Required? | Screenshot Allowed? | Classification | Required Next Action | Backlog Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HealthKit Read-Only | `ios/PulsePlate/Models/HealthKitManager.swift` | Read dietary energy, protein, carbs, fat, fiber, sugar, sodium, body mass | HealthKit data read locally (not sent to backend) | Yes (`NSHealthShareUsageDescription`) | Yes (read-only posture, optional, revocable) | No | `IMPLEMENTATION_REQUIRED` | PR-6 (planned) Swift 6 cleanup; PR-8 (planned) reviewer notes parity | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Diagnostics / Telemetry | Backend observability (`app/bootstrap/metrics.py`) | App performance and error monitoring | Anonymized crash/performance telemetry | No | No (standard diagnostics) | N/A | `IMPLEMENTATION_REQUIRED` | PR-8 (planned) confirm whether App Privacy `DIAGNOSTICS` category is needed; if collected, must be disclosed | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |

### App Store Assets

| Surface | Repo Evidence | User-Visible Claim | Data Collected/Shared | Permission Required? | Reviewer Note Required? | Screenshot Allowed? | Classification | Required Next Action | Backlog Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Screenshot: `core_value` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | Home / welcome screen | N/A | No | No | Yes | `SUBMIT_READY` | PR-8 (planned) metadata sync | -- |
| Screenshot: `nutrition_analysis` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | PRO nutrition plate | N/A | No | Yes (PRO tier) | No | `IMPLEMENTATION_REQUIRED` | PR-3 (planned) BASE_URL; PR-4 (planned) asset gating; PR-8 (planned) reviewer notes | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Screenshot: `meal_planner` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | Weekly meal plan | N/A | No | Yes (feature flag gated) | No | `IMPLEMENTATION_REQUIRED` | Feature flag must be release-enabled; PR-4 (planned); PR-8 (planned) | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Screenshot: `grocery_list` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | Shopping list from meal plan | N/A | No | Yes (depends on weekly plan) | No | `IMPLEMENTATION_REQUIRED` | Source-of-plan and backend smoke; PR-4 (planned); PR-8 (planned) | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Screenshot: `health_progress` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | HealthKit progress view | N/A | No | Yes (HealthKit read-only) | No | `IMPLEMENTATION_REQUIRED` | PR-6 (planned) HealthKit cleanup; PR-4 (planned); PR-8 (planned) | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Screenshot: `personalization` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | Profile / personalization | N/A | No | Yes (profile data) | No | `IMPLEMENTATION_REQUIRED` | PR-1 (merged) privacy; PR-4 (planned); PR-8 (planned) | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| Screenshot: `ai_assistant` | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | AI wellness assistant | N/A | No | Yes (AI disclosure, consent) | No | `IMPLEMENTATION_REQUIRED` | PR-7 (planned) consent; PR-4 (planned); PR-8 (planned) | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| AppIcon Marketing Asset | `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json` | 1024x1024 `ios-marketing` icon | N/A | No | No | N/A | `IMPLEMENTATION_REQUIRED` | PR-5 (planned) actool validation and PNG validity | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |
| External AI/Provider Disclosure | Backend LLM provider calls (`core/ai/`, `providers/`) | AI features use third-party providers | User queries forwarded to LLM provider | No | Yes (must disclose third-party AI processing in reviewer notes) | N/A | `IMPLEMENTATION_REQUIRED` | PR-7 (planned) consent; PR-8 (planned) reviewer notes with provider disclosure | [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature) |

## Reviewer Notes Checklist

The following items must be addressed in `ios/fastlane/metadata/review_information/notes.txt`
before public submission. Current state is evaluated against
`ios/fastlane/metadata/review_information/notes.txt` on main.

### Wellness-Only Positioning

- [x] Notes state the app does not diagnose, treat, cure, or provide medical advice
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:9`
- [ ] Notes confirm wellness-only AI positioning (not therapy, not clinical)
  - Required in: PR-8

### AI Feature Disclosure

- [ ] Notes disclose that AI features use third-party LLM providers
  - Required in: PR-7 (consent) + PR-8 (reviewer notes)
- [ ] Notes disclose what user data is sent to the provider
  - Required in: PR-8
- [ ] Notes confirm user consent is required before first AI query
  - Required in: PR-7

### Third-Party/Provider Disclosure

- [ ] Notes disclose if user data leaves the device/server to third-party services
  - Required in: PR-8 (LLM provider disclosure)

### Billing/Subscription Path

- [ ] Notes explain StoreKit purchase flow and backend activation
  - Partially present: `ios/fastlane/metadata/review_information/notes.txt:10-11`
  - Required in: PR-8 (must reference App Store Connect as pricing truth)

### HealthKit Read-Only Status

- [x] Notes explain read-only HealthKit access
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:4-6`
- [x] Notes confirm Health access is optional and revocable
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:6`

### Test Account / Demo Flow

- [x] Notes confirm screenshots use seeded test data only
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:10`
- [ ] Notes provide test account credentials if reviewer needs to test PRO/VIP flows
  - Required in: PR-8

### What Is Intentionally Not Enabled

- [ ] Notes list features that are in the app but not release-enabled (feature-flagged off)
  - Required in: PR-8 (weekly plan, grocery list, AI assistant if feature-flagged)

## App Privacy Cross-Check

Map App Privacy declarations to repo evidence. App Privacy must not declare
`DATA_NOT_COLLECTED` while profile, AI, billing, receipt, activation, or
diagnostics data leaves the device.

### Current App Privacy State (post PR-1)

| App Privacy Category | Purpose | Protection | Repo Evidence |
| --- | --- | --- | --- |
| `HEALTH` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `ios/PulsePlate/Services/ProfileProvider.swift` sends profile data (age, sex, height, weight) to backend |
| `PURCHASE_HISTORY` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `ios/PulsePlate/Services/SubscriptionManager.swift` sends receipt to `/api/v1/billing/apple/verify-receipt` |
| `OTHER_USER_CONTENT` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `ios/PulsePlate/Services/CBTInsightService.swift` sends free-form AI query to backend |

### Cross-Check Against Privacy Manifest

| Privacy Manifest Entry | App Privacy Coverage | Status |
| --- | --- | --- |
| `NSPrivacyAccessedAPICategoryUserDefaults` (CA92.1) | Not a data-collection category; required-reason API disclosure only | OK |

### Cross-Check Against Release Docs

| Document | Alignment | Status |
| --- | --- | --- |
| `ios/fastlane/app_privacy_details.json` | Matches HEALTH + PURCHASE_HISTORY + OTHER_USER_CONTENT | OK (post PR-1) |
| `ios/PulsePlate/PrivacyInfo.xcprivacy` | UserDefaults CA92.1 disclosed | OK (post PR-1) |
| `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md` | App Privacy column matches current disclosures | OK |

### Gaps

- HealthKit read-only data does not leave the device to the backend, so no
  additional App Privacy category is required for HealthKit. If HealthKit data
  begins leaving the device in a future PR, App Privacy must be updated.
- Diagnostics/telemetry: if anonymized crash or performance data is collected,
  confirm whether `DIAGNOSTICS` category is needed in App Privacy. Currently not
  declared. Deferred to PR-8 metadata sync.

## Permission Strings

Record each sensitive permission string present in release localization files.

### Current State (post PR-2)

| Permission String Key | EN Value | Purpose | Used in Release Build? | Should Remain? | Reviewer Notes Must Mention? |
| --- | --- | --- | --- | --- | --- |
| `NSHealthShareUsageDescription` | "PulsePlate reads Health nutrition and body weight data to show wellness progress and planning with your consent." | HealthKit read-only access | Yes (defined in `en.lproj/InfoPlist.strings` and `ru.lproj/InfoPlist.strings`; `HealthKitManager.swift` uses `toShare: nil`) | Yes | Yes (already covered in reviewer notes) |

### Removed in PR-2

PR-2 removed unused sensitive permission strings that were not backed by release
runtime evidence:

- Camera (`NSCameraUsageDescription`)
- Location (`NSLocationWhenInUseUsageDescription`)
- Photo Library (`NSPhotoLibraryUsageDescription`)
- Microphone (`NSMicrophoneUsageDescription`)
- Contacts (`NSContactsUsageDescription`)
- Face ID (`NSFaceIDUsageDescription`)
- App Tracking Transparency (`NSUserTrackingUsageDescription`)

These may be re-added in future PRs only when runtime evidence exists and
reviewer notes are updated to explain their use.

## Asset / Screenshot Gate

### Submission Rules

An asset scenario may be exported for App Store submission only when all are true:

1. `status == SUBMIT_READY`
2. Release runtime flag is enabled (when applicable)
3. Backend endpoint smoke passed (when applicable)
4. App Privacy disclosure covers the data flow
5. Consent/notice exists (when required)
6. Reviewer note explains the exact flow

### Screenshot Eligibility

| Scenario | Classification | Reason |
| --- | --- | --- |
| `core_value` | `SUBMIT_READY` | Standard app launch; no special data flow or permission |
| `nutrition_analysis` | `IMPLEMENTATION_REQUIRED` | PRO tier; requires explicit HTTPS BASE_URL (PR-3, planned) and reviewer notes (PR-8, planned) |
| `meal_planner` | `IMPLEMENTATION_REQUIRED` | Feature flag `weeklyPlanReaderEnabled` is not confirmed release-enabled |
| `grocery_list` | `IMPLEMENTATION_REQUIRED` | Depends on weekly plan; source-of-plan and backend smoke not confirmed |
| `health_progress` | `IMPLEMENTATION_REQUIRED` | HealthKit Swift 6 cleanup (PR-6, planned) and reviewer notes (PR-8, planned) pending |
| `personalization` | `IMPLEMENTATION_REQUIRED` | Profile data disclosure in reviewer notes (PR-8, planned) pending |
| `ai_assistant` | `IMPLEMENTATION_REQUIRED` | AI consent gate (PR-7, planned) and provider disclosure in reviewer notes (PR-8, planned) pending |

### Screenshot Content Rules

- No fake UI claims: screenshots must reflect actual release runtime behavior
- No unsupported medical claims: wellness-only positioning in all copy
- No pricing/entitlement drift: paywall screenshots must not hardcode pricing;
  pricing comes from StoreKit / App Store Connect truth only
  (see `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`)
- Screenshots use seeded test data only (confirmed in reviewer notes:
  `ios/fastlane/metadata/review_information/notes.txt:10`)

## Blockers

Explicit blockers that must be resolved before full App Store submission.
Each links to `BACKLOG_LEDGER.md` or the epic PR train.

- [ ] **Release BASE_URL**: `Info-Release.plist` contains only a commented
  example; no explicit HTTPS production host is set. Silent fallback in
  `AppConfig.swift` is a release-truth risk.
  - Owner: PR-3 (`release/appstore-readiness-pr3-base-url`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **AppIcon marketing asset**: `Contents.json` references
  `AppIcon-1024.png` as `ios-marketing`; actool validation and PNG validity
  not confirmed.
  - Owner: PR-5 (`release/appstore-readiness-pr5-appicon`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **AI/CBT consent gate**: No explicit wellness-only consent before first
  AI query. Required before AI features can be submission-ready.
  - Owner: PR-7 (`release/appstore-readiness-pr7-ai-consent`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Reviewer notes incomplete**: Current reviewer notes do not cover AI
  disclosure, third-party provider, test account, or feature-flag state.
  - Owner: PR-8 (`release/appstore-readiness-pr8-reviewer-pack`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **HealthKit Swift 6 cleanup**: `HealthKitManager.swift` has a Swift 6
  local-function sendability warning.
  - Owner: PR-6 (`release/appstore-readiness-pr6-healthkit-swift6`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Screenshot submission policy enforcement**: This matrix defines
  classification rules; PR-4 must add Swift and Python enforcement tests
  that gate export/submission based on these classifications.
  - Owner: PR-4 (`release/appstore-readiness-pr4-asset-gating`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **CI release validators**: `make ios-appstore-verify` does not exist yet.
  - Owner: PR-9 (`release/appstore-readiness-pr9-validation-gates`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Legal links**: Privacy Policy and Terms of Use URLs must be live and
  accurate in App Store metadata.
  - Owner: PR-8 (`release/appstore-readiness-pr8-reviewer-pack`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Protected upload evidence**: Implementation PRs do not close rollout.
  Protected `upload_to_asc=true` and `upload_app_privacy=true` dispatches
  require operator evidence per
  `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`.
  - Owner: Release-ops (post-merge)
  - Backlog: [ledger-p1-ios-appstore-assets-rollout](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-appstore-assets-rollout)

## Decision Log

1. **Keep assets; do not delete assets to reduce review risk.** App Store
   assets are preserved in repo, Figma, and Fastlane. Submission is gated by
   classification, not by deletion.

2. **Classify public submission surfaces instead.** Each surface is classified
   as `SUBMIT_READY`, `IMPLEMENTATION_REQUIRED`, `INTERNAL_REVIEW_ONLY`, or
   `BLOCKED`. Only `SUBMIT_READY` surfaces may appear in public App Store
   screenshots and metadata.

3. **Reviewer packet must be evidence-backed.** Reviewer notes must reference
   actual runtime behavior, not aspirational features. Each claim in reviewer
   notes must have a repo evidence path.

4. **App Store metadata cannot imply unimplemented runtime.** No screenshot
   scenario may be marked `SUBMIT_READY` without release flag, smoke proof,
   privacy disclosure, and reviewer-note coverage.

5. **Pricing and trial claims come from StoreKit / App Store Connect only.**
   Reviewer notes and paywall screenshots must not hardcode pricing or trial
   eligibility. Canonical SoT:
   `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`.

6. **HealthKit remains read-only.** No write access unless a separate reviewed
   PR changes entitlement posture.

7. **AI/CBT features require explicit consent.** No AI query may leave the
   device without wellness-only disclosure and user consent.

8. **Production API host is an unresolved operator decision.** PR-3 must
   resolve the canonical HTTPS production host before runtime fail-fast changes
   land. See `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md#backend-host-decision-register`.

## Non-Goals

This document does not:

- Implement runtime features
- Generate or capture screenshots
- Upload to App Store Connect
- Migrate billing or subscription logic
- Integrate AI providers
- Change OpenAPI contracts
- Change backend, frontend, or iOS runtime code

## Validation Commands

Commands that should pass for this docs/release PR:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
git diff --name-only origin/main...HEAD | rg -v '\.md$'  # must be empty (docs-only)
```
