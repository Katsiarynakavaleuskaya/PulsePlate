# App Store Fastlane Metadata Audit

**Date:** 2026-05-02

**Epic:** `epic/appstore-release-readiness-full-feature`

**PR lane:** `release/appstore-readiness-pr5-fastlane-metadata-audit`

## Purpose

Audit all Fastlane metadata, reviewer notes, App Privacy declarations, legal
URLs, StoreKit/pricing copy boundaries, and screenshot metadata alignment
before any App Store submission.

This document does not change metadata files. It documents what the metadata
currently says, identifies gaps and risks, and maps required remediation to
the epic PR train.

## Source of Truth

| Document | Role |
| --- | --- |
| `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md` | Surface-level submission classification and reviewer-note checklist (PR-3) |
| `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` | Screenshot and asset submission gate with fail-closed rules (PR-4) |
| `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md` | Feature-to-asset mapping with release flags and privacy |
| `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md` | Canonical StoreKit product IDs, pricing copy rules, offer governance |
| `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md` | Payment sources, activation contract, billing surfaces |
| `ios/PulsePlate/PrivacyInfo.xcprivacy` | Apple required-reason API privacy manifest |
| `ios/fastlane/app_privacy_details.json` | App Privacy questionnaire answers for App Store Connect |
| `docs/legal/Privacy.md` | User-facing privacy policy (RU/EN/ES) |
| `ios/fastlane/metadata/` | Fastlane metadata directories (en-US, ru-RU, es-ES, review_information) |

Root `AGENTS.md` section `App Store release readiness gates` remains the
hard-gate source of truth for release readiness checks.

## Metadata Inventory

### Localized Metadata (per locale: en-US, ru-RU, es-ES)

Each locale directory contains the same 9 files. Total: 27 localized files.

| File | Purpose | App Store-Facing? | Claim Type | Current State | Risk | Required Next Action |
| --- | --- | --- | --- | --- | --- | --- |
| `name.txt` | App name on App Store | Yes | Brand identity | "PulsePlate" in all locales | Low | None |
| `subtitle.txt` | App Store subtitle | Yes | Product positioning | EN: "Wellness nutrition planner"; RU: "Планировщик питания и wellness"; ES: "Plan de nutrición wellness" | Low -- wellness-only positioning | None |
| `description.txt` | App Store long description | Yes | Feature claims, wellness disclaimer | Still mentions daily nutrition balance, lightweight profile, and Health data access while related screenshot scenarios remain `IMPLEMENTATION_REQUIRED` | P1 -- public metadata can imply broader release-ready surfaces than screenshot gate allows | Narrow copy or produce release-enabled/smoke proof before protected submission |
| `keywords.txt` | App Store search keywords | Yes | Discovery keywords | EN: "nutrition,wellness,meal planner,progress,healthkit,healthy habits"; localized equivalents | Low | None |
| `promotional_text.txt` | App Store promotional banner | Yes | Marketing claim | Wellness-only copy in all locales | Low | None |
| `release_notes.txt` | What's New text | Yes | Version changelog | Updated for the release train | Low | Keep aligned with actual release content |
| `marketing_url.txt` | Marketing URL in App Store listing | Yes | External link | `https://pulseplate.app` in all locales | P1 -- URL liveness not verified from repo | Verify live URL before protected submission |
| `privacy_url.txt` | Privacy Policy URL in App Store listing | Yes | Legal compliance link | `https://pulseplate.app/privacy` in all locales | P1 -- URL liveness not verified from repo; must match `docs/legal/Privacy.md` content | Verify live URL and policy match before protected submission |
| `support_url.txt` | Support URL in App Store listing | Yes | User support link | `https://pulseplate.app/support` in all locales | P1 -- URL liveness not verified from repo | Verify live URL before protected submission |

### Reviewer Notes

| File | Purpose | App Store-Facing? | Claim Type | Current State | Risk | Required Next Action |
| --- | --- | --- | --- | --- | --- | --- |
| `review_information/notes.txt` | Reviewer-only guidance for App Review | Yes (reviewer) | Compliance, feature disclosure | Reconciled for the current release train; covers wellness posture, AI disclosure, test account handling, feature limitations, StoreKit, HealthKit, and validator posture | Low -- protected submission still needs operator-provided review credentials | Keep synchronized with release validators and App Store Connect review information |

### Non-Localized Assets

| File | Purpose | App Store-Facing? | Current State | Risk | Required Next Action |
| --- | --- | --- | --- | --- | --- |
| `app_privacy_details.json` | App Privacy questionnaire for App Store Connect | Yes (compliance) | 3 categories: HEALTH, PURCHASE_HISTORY, OTHER_USER_CONTENT; all DATA_LINKED_TO_YOU | P1 -- DIAGNOSTICS category may be needed if telemetry is added or enabled | Recheck before protected submission |
| `PrivacyInfo.xcprivacy` | Apple required-reason API manifest | Yes (compliance) | UserDefaults CA92.1; NSPrivacyTracking false | Low | None |

**Totals:** 29 metadata files audited (27 localized + 1 reviewer notes + 1
App Privacy JSON). Plus 1 privacy manifest in Xcode project.

## Reviewer Notes Audit

Current file: `ios/fastlane/metadata/review_information/notes.txt`
(reconciled for the current release train).

### Wellness-Only Positioning

- [x] **PASS**: Notes state the app does not diagnose, treat, cure, or provide medical advice
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:1`
- [x] **PASS**: Notes confirm wellness-only AI positioning (not therapy, not clinical)
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:4-5`

### AI Feature Disclosure

- [x] **PASS**: Notes disclose that AI features use third-party LLM providers
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:7`
- [x] **PASS**: Notes disclose what user data is sent to the AI provider
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:7`
- [x] **PASS**: Notes confirm user consent is required before first AI query
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:5`

### Third-Party Provider Disclosure

- [x] **PASS**: Notes disclose if user data leaves the device or server to third-party services
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:7`

### Billing and Subscription Path

- [x] **PASS**: Notes explain that paywall screenshots are static preview states
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:19`
- [x] **PASS**: Notes reference App Store Connect as the sole pricing truth source
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:17`

### HealthKit Read-Only Status

- [x] **PASS**: Notes explain read-only HealthKit access
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:11-12`
- [x] **PASS**: Notes confirm Health access is optional and revocable
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:13-14`

### Test Account and Demo Flow

- [x] **PASS**: Notes confirm screenshots use seeded test data only
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:23`
- [x] **PASS**: Notes provide test account placeholder for reviewer
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:22`

### Feature Flag and Intentionally Disabled Flows

- [x] **PASS**: Notes list features that are in the app but not release-enabled
  - Evidence: `ios/fastlane/metadata/review_information/notes.txt:26-28`

### Summary

| Status | Count |
| --- | --- |
| PASS | 12 |
| GAP | 0 |
| BLOCKED | 0 |
| NOT_APPLICABLE | 0 |

All 12 checklist items are reconciled against current reviewer notes and release-train governance. Protected submission still requires operator-owned credential and upload evidence.

## Metadata Claim Boundary

### Forbidden Claims in App Store Metadata

The following claims are forbidden in any App Store-facing text (descriptions,
subtitles, promotional text, reviewer notes, screenshot captions):

1. **Diagnosis**: claiming the app diagnoses health conditions
2. **Treatment**: claiming the app treats any medical condition
3. **Therapy**: claiming the app provides therapy or CBT treatment
4. **Cure**: claiming the app cures any condition
5. **Guaranteed weight loss**: asserting definite weight-loss outcomes
6. **Guaranteed health outcome**: asserting definite health improvements
7. **Doctor or medical-device framing**: positioning the app as medical advice or a medical device
8. **Hardcoded pricing**: stating specific prices, trial durations, or discount percentages not sourced from StoreKit or App Store Connect
9. **Live AI capability without consent or disclosure**: claiming AI features without disclosing third-party processing, data sent, and consent requirement
10. **Live screenshots of unreleased features**: showing HealthKit progress, weekly plan, AI assistant, or grocery list screenshots as public App Store assets without release-enabled proof

### Current Metadata Compliance

| Locale | Forbidden Claim Found? | Details |
| --- | --- | --- |
| en-US | No | Description uses wellness-only language; no medical claims; no pricing |
| ru-RU | No | Description uses wellness-only language; no medical claims; no pricing |
| es-ES | No | Description uses wellness-only language; no medical claims; no pricing |
| Reviewer notes | No | Wellness disclaimer at line 9; no medical claims |

**Verdict:** Current metadata text does not contain forbidden claims. However,
descriptions mention features (weekly wellness progress, Health data access)
that are mapped to `IMPLEMENTATION_REQUIRED` screenshot scenarios. This is a
P0 submission blocker (descriptions imply availability of features not yet
submission-ready), though it is not a forbidden-claim violation per se.

## StoreKit and Pricing Copy Audit

Cross-checked against `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`.

### Pricing Claims in Metadata

| Surface | Hardcoded Price? | Trial Claim? | Eligibility Claim? | Verdict |
| --- | --- | --- | --- | --- |
| `description.txt` (all locales) | No | No | No | PASS |
| `subtitle.txt` (all locales) | No | No | No | PASS |
| `promotional_text.txt` (all locales) | No | No | No | PASS |
| `release_notes.txt` (all locales) | No | No | No | PASS |
| `review_information/notes.txt` | No | No | No (line 11 references ASC) | PASS |

### Copy Fallback Compliance

Per `IOS_STOREKIT_PRODUCTS_CONTRACT.md` section "Copy fallback rules":

- No metadata file contains numeric price claims. **PASS.**
- No metadata file contains exact trial-length claims. **PASS.**
- No metadata file contains definite eligibility claims. **PASS.**
- Reviewer notes line 11 correctly references "in-app purchase configuration in
  App Store Connect" as pricing authority. **PASS.**

### StoreKit Product ID Exposure

- No metadata file references `com.pulseplate.premium.monthly` or
  `com.pulseplate.premium.yearly` product IDs. **PASS** (product IDs should not
  appear in public metadata).

**Verdict:** All metadata files comply with StoreKit pricing copy rules. No
remediation needed for pricing claims.

## Privacy Metadata Audit

### App Privacy Details Cross-Check

Source: `ios/fastlane/app_privacy_details.json` (29 lines, 3 categories).

| App Privacy Category | Purpose | Protection | Runtime Evidence | Privacy Policy Coverage | Status |
| --- | --- | --- | --- | --- | --- |
| `HEALTH` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `ProfileProvider.swift` sends age, sex, height, weight to backend | `docs/legal/Privacy.md` section "Account Data" covers profile data | PASS |
| `PURCHASE_HISTORY` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `SubscriptionManager.swift` sends receipt to `/api/v1/billing/apple/verify-receipt` | `docs/legal/Privacy.md` covers purchase/subscription processing | PASS |
| `OTHER_USER_CONTENT` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` | `CBTInsightService.swift` sends free-form AI query to backend and LLM provider | `docs/legal/Privacy.md` section "AI/Automated Analysis" covers AI processing | PASS |

### Privacy Manifest Cross-Check

Source: `ios/PulsePlate/PrivacyInfo.xcprivacy` (19 lines).

| Manifest Entry | Coverage | Status |
| --- | --- | --- |
| `NSPrivacyAccessedAPICategoryUserDefaults` (CA92.1) | Required-reason API disclosure for UserDefaults access | PASS |
| `NSPrivacyTracking` = `false` | No App Tracking Transparency usage | PASS |

### Reviewer Notes Privacy Cross-Check

| Privacy Topic | Reviewer Notes Coverage | Status |
| --- | --- | --- |
| HealthKit read-only posture | Lines 3-6: explicit read-only, optional, revocable | PASS |
| Profile data sent to backend | Covered through AI/profile context and feature limitations | PASS |
| AI query sent to third-party LLM | Covered through explicit AI consent and provider disclosure | PASS |
| Purchase receipt sent to backend | Covered through StoreKit/billing truth and backend activation wording | PASS |

### Privacy Policy Alignment

`docs/legal/Privacy.md` (234 lines) covers:

- Account and profile data (RU/EN/ES)
- AI/automated analysis disclosure
- External and self-hosted processor disclosure
- Retention and deletion policy
- GDPR user rights

The privacy policy content appears aligned with `app_privacy_details.json`
declarations. URL liveness (`https://pulseplate.app/privacy`) cannot be
verified from repo.

### Gaps

- **DIAGNOSTICS category**: Not declared in `app_privacy_details.json`. If
  anonymized crash or performance telemetry is collected, this category may be
  required. Recheck before protected submission and update App Privacy if
  telemetry is enabled.
- **HealthKit data**: Does not leave the device to the backend (confirmed in
  `HealthKitManager.swift` -- read-only, local). No additional App Privacy
  category needed for HealthKit unless data begins leaving the device.

## Screenshot Metadata Alignment

Cross-checked against `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` (PR-4).

### Description Feature Claims vs Screenshot Eligibility

App Store descriptions mention these features across all locales:

| Description Feature Claim | Screenshot Scenario | Gate Classification | Alignment Status |
| --- | --- | --- | --- |
| "review daily nutrition balance" | `nutrition_analysis` | `IMPLEMENTATION_REQUIRED` | Manual P1 -- localized description claim requires pre-submission review outside `make ios-appstore-verify` |
| "follow weekly wellness progress" | `health_progress` | `IMPLEMENTATION_REQUIRED` | Historical P0 -- current localized descriptions no longer include this claim |
| "keep a lightweight profile" | `personalization` | `IMPLEMENTATION_REQUIRED` | Manual P1 -- localized description claim requires pre-submission review outside `make ios-appstore-verify` |
| "understand Health data access" | `health_progress` | `IMPLEMENTATION_REQUIRED` | Manual P1 -- localized description claim requires pre-submission review outside `make ios-appstore-verify` |
| App launch / welcome flow | `core_value` | `SUBMIT_READY` | PASS |

**Verdict:** Public screenshots remain correctly limited to `SUBMIT_READY`
surfaces, but the localized descriptions still mention nutrition balance,
profile, and Health data access while those screenshot scenarios remain
`IMPLEMENTATION_REQUIRED`. This is a manual metadata pre-submission risk outside
the current `make ios-appstore-verify` screenshot-policy check, which only
verifies scenario classifications and public screenshot eligibility. Before
protected submission, release-ops must either narrow those descriptions or
attach release-enabled, privacy, backend-smoke, and reviewer-note proof for the
referenced surfaces.

### Screenshot Directory State

No committed screenshot image files exist under `ios/fastlane/screenshots/`.
Screenshots are generated at snapshot-capture time by Fastlane `snapshot_all`
lane. This means public screenshot content is controlled by the
`AppStoreScreenshotTests.swift` test suite and the `AppStoreScreenshotScenario`
enum, not by pre-committed image files.

The screenshot asset gate (PR-4) governs which scenarios may be exported.
Currently only `core_value` is `SUBMIT_READY`.

## Risk Table

| Risk | Severity | Evidence | Owner PR | Blocking? | Required Action |
| --- | --- | --- | --- | --- | --- |
| Reviewer notes AI disclosure | Reconciled | `notes.txt` includes AI consent and provider disclosure | Release-ops | No | Keep synchronized with runtime consent and App Privacy |
| Reviewer notes test account handling | Reconciled | `notes.txt` states credentials are provided in App Store Connect review information | Release-ops | No | Operator supplies credentials before protected submission |
| Reviewer notes feature flag disclosure | Reconciled | `notes.txt` lists implementation-required screenshot scenarios excluded from public submission | Release-ops | No | Keep in sync with screenshot gate |
| Description overclaims blocked scenarios | P1 | `description.txt` still mentions nutrition balance, profile, and Health data access | Release-ops / metadata owner | Yes (submission) | Narrow copy or attach release-enabled/smoke proof before protected submission |
| Marketing URL liveness unverified | P1 | `marketing_url.txt` = `https://pulseplate.app` | Release-ops | No (pre-submission) | Verify URL returns expected content before protected submission |
| Privacy URL liveness unverified | P1 | `privacy_url.txt` = `https://pulseplate.app/privacy` | Release-ops | No (pre-submission) | Verify URL is live and matches Privacy.md before protected submission |
| Support URL liveness unverified | P1 | `support_url.txt` = `https://pulseplate.app/support` | Release-ops | No (pre-submission) | Verify URL is live before protected submission |
| DIAGNOSTICS category may be needed | P1 | `app_privacy_details.json` lacks DIAGNOSTICS | Release-ops / telemetry owner | No (pre-submission) | Recheck whether crash/performance telemetry is collected |
| No terms_url.txt in metadata | P1 | Absent from all locale directories | Release-ops | No (may be set in ASC directly) | Verify if Fastlane deliver requires this or if ASC has it set |
| Reviewer notes StoreKit reference | Reconciled | `notes.txt` states StoreKit/App Store Connect own pricing, trials, and renewal terms | Release-ops | No | Keep aligned with StoreKit product contract |
| Release notes generic | Reconciled | Release notes updated for the release train | Release-ops | No | Keep aligned with actual release content |

## Non-Goals

This document does not:

- Change any metadata files (audit only)
- Upload metadata to App Store Connect
- Generate or capture screenshots
- Implement runtime features or change iOS, backend, or frontend code
- Change OpenAPI contracts
- Migrate billing or subscription logic
- Integrate AI providers
- Access MCP, Figma, or App Store Connect API
- Introduce secrets or environment variable requirements
- Verify URL liveness (requires external HTTP access not available in this mode)
- Delete metadata or assets to reduce review risk

## Decision Log

1. **Audit first, remediate through the train.** This document began as a
   point-in-time audit. The landed release train remediated the repo-local AI
   consent, reviewer notes, metadata sync, and validator gaps; protected upload
   evidence remains operator-owned.

2. **StoreKit / App Store Connect is pricing truth.** No metadata file may
   hardcode prices, trial durations, or eligibility claims. Current metadata
   complies. Per `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`.

3. **Reviewer notes must be evidence-backed.** Each claim in reviewer notes
   must have a repo evidence path. Current notes are covered by reviewer-pack
   guards and the unified App Store readiness validator.

4. **Metadata cannot advertise blocked screenshot scenarios.** Public metadata
   must stay narrowed to current `SUBMIT_READY` claims; screenshots of
   `IMPLEMENTATION_REQUIRED` scenarios must not appear in public submission.
   Per `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md`.

5. **Privacy declarations must match runtime data flows.** Current
   `app_privacy_details.json` correctly declares HEALTH, PURCHASE_HISTORY,
   and OTHER_USER_CONTENT. DIAGNOSTICS category investigation is deferred.

6. **AI and CBT claims require explicit consent and disclosure.** Reviewer
   notes must disclose third-party LLM processing, data sent, and
   wellness-only positioning before AI features can be submission-ready.

7. **URL liveness is a pre-submission requirement.** Marketing, privacy, and
   support URLs must be verified live before any App Store submission. This
   audit cannot verify liveness from repo alone.

8. **Terms of Use URL absence is flagged.** No `terms_url.txt` exists in
   Fastlane metadata directories. This may be set directly in App Store
   Connect or may need to be added to Fastlane metadata.

## Validation Commands

Commands that should pass for this docs/release PR:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
python3 scripts/release/check_ios_appstore_verify.py
! git diff --name-only origin/main...HEAD | rg -q -v '^docs/.*\.md$|^ios/fastlane/metadata/review_information/notes\.txt$'
```
