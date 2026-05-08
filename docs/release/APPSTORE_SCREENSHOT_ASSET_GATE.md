# App Store Screenshot Asset Gate

**Date:** 2026-05-01

**Epic:** `epic/appstore-release-readiness-full-feature`

**PR lane:** `release/appstore-readiness-pr4-screenshot-asset-gate`

## Purpose

Define the canonical repo-local gate for screenshot and App Store asset
submission eligibility. This document consumes the reviewer submission matrix
(PR-3) and maps each screenshot scenario and asset category to a fail-closed
submission classification.

No screenshot may be exported for public App Store submission unless every
gate rule passes. Assets are preserved in repo; submission eligibility is
gated, not deleted.

## Source of Truth

| Document | Role |
| --- | --- |
| `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md` | Surface-level submission classification and reviewer-note checklist |
| `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md` | Feature-to-asset mapping with release flags and privacy |
| `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | Canonical screenshot scenario enum (`AppStoreScreenshotScenario`) |
| `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json` | AppIcon asset catalog with `ios-marketing` 1024x1024 entry |
| `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md` | Protected upload procedure and evidence requirements |
| `ios/fastlane/Fastfile` | Fastlane snapshot, validation, and upload lanes |
| `ios/fastlane/metadata/review_information/notes.txt` | Reviewer notes (current state on main) |

Root `AGENTS.md` section `App Store release readiness gates` remains the
hard-gate source of truth for release readiness checks. This gate document
is the enforcement mirror for screenshot and asset submission decisions.

## Classification Enum

Same enum as the reviewer submission matrix (PR-3):

| Classification | Meaning |
| --- | --- |
| `SUBMIT_READY` | Asset may appear in public App Store screenshots and metadata. All gate rules pass. |
| `IMPLEMENTATION_REQUIRED` | Asset exists in repo but is blocked from public submission until runtime, privacy, or reviewer-note evidence is complete. |
| `INTERNAL_REVIEW_ONLY` | Asset is allowed for QA, reviewer boards, or debug use only. Not for public App Store metadata. |
| `BLOCKED` | Asset cannot proceed until a specific blocker is resolved. Blocker links to `BACKLOG_LEDGER.md`. |

## Screenshot Scenario Registry

Every scenario from `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift`
(`AppStoreScreenshotScenario` enum, lines 4-11):

| Scenario ID | User-Facing Claim | Runtime Dependency | Data/Privacy Dependency | Reviewer-Note Dependency | Feature Flag / Endpoint | Classification | Submission Allowed? | Required Next PR | Evidence Path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `core_value` | Home / welcome screen, app shell | App launch; no backend call required for static welcome | No additional data beyond app metadata | No (standard app launch) | None | `SUBMIT_READY` | Yes | Metadata sync reconciled for release | `ios/PulsePlate/Views/HomeView.swift` |
| `nutrition_analysis` | PRO daily nutrition plate analysis | PRO tier backend call to `/api/v1/pro/nutrition/daily`; release `BASE_URL` is explicit HTTPS | Profile data (age, sex, height, weight, activity, goal) sent to backend; `HEALTH` category disclosed in App Privacy | Yes: PRO tier scope, backend processing disclosure | PRO entitlement; `BASE_URL` in `Info-Release.plist`; backend smoke still required | `IMPLEMENTATION_REQUIRED` | No | Backend smoke/release-enabled proof | `ios/PulsePlate/Views/PlateView.swift`, `ios/PulsePlate/Services/ProDailyNutritionService.swift` |
| `meal_planner` | Weekly meal plan view | Weekly plan reader requires backend `/api/v1/pro/meal/weekly` | Meal plan data to backend; profile context | Yes: feature flag state, meal planning disclosure | `FeatureFlags.weeklyPlanReaderEnabled` must be release-enabled | `IMPLEMENTATION_REQUIRED` | No | Feature flag and backend smoke proof | `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift` |
| `grocery_list` | Shopping list from meal plan | Depends on weekly plan source; backend `/api/v1/pro/meal/shopping-list` | Meal plan and shopping-list data to backend | Yes: source-of-plan dependency, backend smoke | Weekly plan feature flag; shopping list endpoint smoke | `IMPLEMENTATION_REQUIRED` | No | Source-of-plan and backend smoke proof | `ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift` |
| `health_progress` | HealthKit wellness progress view | HealthKit read-only local data; `HealthKitManager.swift` uses `toShare: nil` | HealthKit data read locally (not sent to backend); `NSHealthShareUsageDescription` in `InfoPlist.strings` | Yes: read-only posture, optional/revocable access | HealthKit capability; user authorization | `IMPLEMENTATION_REQUIRED` | No | Full screenshot promotion proof | `ios/PulsePlate/Models/HealthKitManager.swift`, `ios/PulsePlate/Views/WeeklyProgressView.swift` |
| `personalization` | Profile / personalization setup | Profile data sent to backend via `ProfileProvider` | Profile data (age, sex, height, weight) sent to backend; `HEALTH` category disclosed in App Privacy | Yes: profile data disclosure in reviewer notes | PRO entitlement; backend profile endpoint | `IMPLEMENTATION_REQUIRED` | No | Backend/release-enabled proof | `ios/PulsePlate/Views/ProfileView.swift`, `ios/PulsePlate/Services/ProfileProvider.swift` |
| `ai_assistant` | AI wellness assistant / CBT insight | AI query sent to backend `/api/v1/pro/cbt/insight` and forwarded to LLM provider | User free-form text + profile context to backend and LLM provider; `OTHER_USER_CONTENT` disclosed in App Privacy | Yes: AI/provider disclosure, wellness-only consent, third-party processing | `FeatureFlags.aiInsightEnabled`; AI consent gate | `IMPLEMENTATION_REQUIRED` | No | Release flag and backend smoke proof | `ios/PulsePlate/Views/AIInsightView.swift`, `ios/PulsePlate/Services/CBTInsightService.swift` |

### Screenshot Scenario Summary

| Scenario | Classification | Submission Allowed? |
| --- | --- | --- |
| `core_value` | `SUBMIT_READY` | Yes |
| `nutrition_analysis` | `IMPLEMENTATION_REQUIRED` | No |
| `meal_planner` | `IMPLEMENTATION_REQUIRED` | No |
| `grocery_list` | `IMPLEMENTATION_REQUIRED` | No |
| `health_progress` | `IMPLEMENTATION_REQUIRED` | No |
| `personalization` | `IMPLEMENTATION_REQUIRED` | No |
| `ai_assistant` | `IMPLEMENTATION_REQUIRED` | No |

**Current state:** 1 of 7 scenarios is submission-ready.

## Asset Registry

| Asset | Evidence Path | Required Validator | Current State | Classification | Next Action |
| --- | --- | --- | --- | --- | --- |
| AppIcon `ios-marketing` 1024x1024 | `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json` (line 106-110: `AppIcon-1024.png`, idiom `ios-marketing`) | Repo-local App Store validator + PNG validity check | Marketing asset validated and covered by release validators | `SUBMIT_READY` | Keep covered by `make ios-appstore-verify` |
| Screenshot set (7 scenarios) | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` (lines 4-11) | `ios/fastlane/Fastfile` lane `validate_assets` + dimension/color-gamut validators + `make ios-appstore-verify` | Scenarios defined; only `core_value` is `SUBMIT_READY` | Mixed (`SUBMIT_READY` / `IMPLEMENTATION_REQUIRED`) | Per-scenario runtime/privacy/smoke proof before promotion |
| Localized metadata (en-US, ru-RU, es-ES) | `ios/fastlane/metadata/` | `ios/fastlane/Fastfile` lane `validate_metadata_package` | Metadata package is synchronized, but localized descriptions still require manual claim review before protected submission | `IMPLEMENTATION_REQUIRED` | Narrow public copy or attach release-enabled/smoke/privacy proof before protected upload |
| Reviewer notes | `ios/fastlane/metadata/review_information/notes.txt` | `ios/fastlane/Fastfile` lane `validate_metadata_package` + semantic validators | Covers wellness, AI consent, provider disclosure, HealthKit, StoreKit, test account handling, feature limitations, screenshot policy, and validator posture | `SUBMIT_READY` for current public claims | Operator supplies credentials in App Store Connect before protected submission |
| App Privacy package | `ios/fastlane/app_privacy_details.json` | `ios/fastlane/Fastfile` lane `upload_app_privacy` preflight | Declares `HEALTH`, `PURCHASE_HISTORY`, `OTHER_USER_CONTENT` as `DATA_LINKED_TO_YOU` (post PR-1) | `SUBMIT_READY` | Recheck `DIAGNOSTICS` category before protected submission if telemetry is enabled |

## Submission Gate Rules

These rules are **fail-closed**: a screenshot or asset is blocked unless every
applicable rule passes.

### Rule 1: Runtime surface must be release-enabled

A screenshot is **blocked** if the runtime surface it depicts is not
release-enabled. Feature-flagged flows (weekly plan, grocery list, AI
assistant) must have their release flags confirmed enabled before the
screenshot scenario can be classified `SUBMIT_READY`.

Evidence required: feature flag configuration in release build or
`FeatureFlags` source showing default-on for release.

### Rule 2: App Privacy must cover the data flow

A screenshot is **blocked** if App Privacy does not declare the data
categories that the depicted flow collects or shares. For example, a
screenshot showing AI assistant interaction requires `OTHER_USER_CONTENT`
in `app_privacy_details.json`.

Evidence required: `ios/fastlane/app_privacy_details.json` entry matching
the data flow.

### Rule 3: Reviewer notes must explain applicable flows

A screenshot is **blocked** if applicable reviewer-note items are not
addressed in `ios/fastlane/metadata/review_information/notes.txt`:

- AI/HealthKit/StoreKit flows require explicit disclosure
- Third-party LLM provider usage requires disclosure
- Wellness-only positioning must be stated when AI features are shown

Evidence required: specific line references in `notes.txt`.

### Rule 4: No pricing claims outside StoreKit / App Store Connect

A screenshot is **blocked** if it implies pricing, trial eligibility,
or subscription terms not sourced from StoreKit or App Store Connect.
Paywall screenshots must use seeded preview states and must not hardcode
pricing or billing claims.

Evidence required: `notes.txt` line 11 (current) states paywall screenshots
are static preview states; canonical SoT is
`docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`.

### Rule 5: No medical/diagnosis/treatment claims

A screenshot is **blocked** if it contains medical, diagnosis, treatment,
cure, therapy, or clinical claims. All screenshots must reflect
wellness-only positioning.

Evidence required: `notes.txt` line 9 (current) states the app does not
diagnose, treat, cure, or provide medical advice.

### Rule 6: No feature-flagged or unimplemented flow depicted as live

A screenshot is **blocked** if it depicts a feature-flagged-off or
unimplemented flow as if it were a live, available feature. Screenshots
must reflect actual release runtime behavior.

Evidence required: feature flag state in release build confirming the
depicted flow is enabled.

### Rule 7: Backend smoke evidence must exist when required

A screenshot is **blocked** if the depicted flow requires backend
interaction and no backend smoke evidence exists for the release
configuration. This applies to PRO/VIP flows, AI queries, billing
verification, and any endpoint the screenshot flow depends on.

Evidence required: backend smoke test or endpoint reachability proof
in release configuration.

## Validator Design (Repo-Local Contract)

### Future validator command

```bash
python3 scripts/release/check_appstore_screenshot_asset_gate.py
```

### Validator contract (implemented repo-local)

The validator should eventually:

1. Parse `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` (or a later JSON
   mirror) to extract scenario classifications.
2. Verify every scenario in `AppStoreScreenshotScenario` (from
   `AppStoreScreenshotContext.swift`) has a classification entry.
3. Verify `SUBMIT_READY` scenarios have reviewer-note evidence (line
   references in `notes.txt`).
4. Verify `AppIcon-1024.png` exists in `Contents.json` with idiom
   `ios-marketing`.
5. Fail on unknown scenario IDs not present in the gate document.
6. Fail if `IMPLEMENTATION_REQUIRED` scenarios appear in any public
   submission manifest.

### Implementation status

The validator contract is implemented. `make ios-appstore-verify` is the
unified repo-local gate for App Store readiness checks and does not perform App
Store Connect uploads.

Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

## Non-Goals

This document does not:

- Generate or capture screenshots
- Upload to App Store Connect
- Delete App Store assets or reduce product scope
- Implement runtime features or change iOS/backend/frontend code
- Change OpenAPI contracts
- Access MCP, Figma, or App Store Connect API
- Introduce network or provider calls
- Add secrets or environment variable requirements
- Change the validator script or release validation implementation
- Change billing, subscription, or entitlement logic
- Change AI provider configuration

## Blockers

Explicit blockers that must be resolved before screenshot scenarios can be
reclassified to `SUBMIT_READY`. Each links to backlog or the epic PR train.

- [x] **Release BASE_URL**: Closed by the landed release train. Release builds require an
  explicit HTTPS `BASE_URL`; missing or invalid values fail before submission.
  This no longer blocks screenshot scenario governance.
  - Owner: PR-7 (`release/appstore-readiness-pr7-base-url-fail-fast`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [x] **AI/CBT consent gate**: Closed by the landed release train. AI requests
  require explicit wellness-only consent before off-device processing. This
  no longer blocks screenshot governance, though `ai_assistant` remains
  excluded from public screenshots until all `SUBMIT_READY` criteria are met.
  - Owner: PR-10 / PR-10b (`release/appstore-readiness-pr10-ai-wellness-consent`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [x] **Reviewer notes incomplete**: Closed by the landed release train. Reviewer notes now
  cover AI disclosure, third-party provider, test account handling, feature
  limitations, HealthKit, StoreKit, and screenshot policy.
  - Owner: PR-11 (`release/appstore-readiness-pr11-reviewer-pack`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [x] **HealthKit Swift 6 cleanup**: Closed by the landed release train. HealthKit remains
  read-only and Swift 6 readiness is covered by release guards.
  - Owner: PR-9 (`release/appstore-readiness-pr9-healthkit-swift6`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [x] **AppIcon marketing asset validation**: Closed by the landed release train and covered
  by the unified repo-local validator.
  - Owner: PR-8 (`release/appstore-readiness-pr8-appicon-marketing-asset`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Protected upload evidence**: Implementation PRs do not close rollout.
  Protected `upload_to_asc=true` and `upload_app_privacy=true` dispatches
  require operator evidence per
  `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`.
  - Owner: Release-ops (post-merge)
  - Backlog: [ledger-p1-ios-appstore-assets-rollout](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-appstore-assets-rollout)

- [ ] **Legal links**: Privacy Policy and Terms of Use URLs must be live and
  accurate in App Store metadata.
  - Owner: PR-8 (`release/appstore-readiness-pr8-reviewer-pack`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Feature flag gating**: `weeklyPlanReaderEnabled` and
  `aiInsightEnabled` must be confirmed release-enabled for `meal_planner`,
  `grocery_list`, and `ai_assistant` scenarios.
  - Owner: Feature flag enablement PR (planned)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [x] **CI release validators**: Closed by the landed release train. `make
  ios-appstore-verify` now runs repo-local App Store readiness gates, including
  screenshot policy validation, without App Store Connect credentials.
  - Owner: PR-12 (`release/appstore-readiness-pr12-validation-gates`)
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

- [ ] **Backend smoke evidence**: No release-configuration backend smoke
  proof exists for PRO/VIP/AI endpoints used by screenshot scenarios.
  Release `BASE_URL` is no longer the blocker; live endpoint smoke proof remains
  required before implementation-required scenarios can be reclassified.
  - Owner: Future release smoke evidence PR
  - Backlog: [ledger-p0-appstore-release-readiness-full-feature](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature)

## Decision Log

1. **Keep all assets.** App Store assets are preserved in repo, Figma, and
   Fastlane. Submission is gated by classification, not by deletion.

2. **Gate submission eligibility instead of deleting assets.** The screenshot
   asset gate blocks export of non-ready scenarios without removing them
   from the codebase.

3. **Repo truth wins over Figma/App Store screenshots.** This gate document
   and the reviewer submission matrix are the source of truth for what may
   be submitted. External design tools and App Store Connect draft state
   are downstream consumers.

4. **Screenshots cannot claim aspirational features.** Any screenshot
   depicting a feature must reflect actual release runtime behavior with
   the feature flag enabled and backend reachable.

5. **Pricing truth comes from StoreKit / App Store Connect.** No screenshot
   or metadata may hardcode pricing, trial, or eligibility claims. Canonical
   SoT: `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`.

6. **AI screenshots require consent and disclosure.** The wellness-only consent
   gate and provider disclosure have landed, but the `ai_assistant` scenario
   remains blocked from public screenshots until release flag and backend smoke
   proof are complete.

7. **Fail-closed by default.** Any scenario without complete evidence is
   classified `IMPLEMENTATION_REQUIRED` or `BLOCKED`. A scenario must be
   explicitly promoted to `SUBMIT_READY` with evidence.

8. **Validator is repo-local and upload-free.** The release validator is
   implemented. Protected App Store Connect uploads remain operator-owned and
   require separate protected-run evidence.

## Validation Commands

Commands that should pass for this docs/release PR:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
python3 scripts/release/check_ios_appstore_verify.py
! git diff --name-only origin/main...HEAD | rg -q -v '^docs/.*\.md$|^ios/fastlane/metadata/review_information/notes\.txt$'
```
