# App Store Release Readiness Epic

**Epic title:** `epic(ios-release): close App Store readiness for full-feature PulsePlate launch`

**Epic slug:** `epic/appstore-release-readiness-full-feature`

**Branch namespace:** `release/appstore-readiness-*`

**Date:** 2026-04-29

## Summary

This epic closes App Store readiness drift across iOS runtime behavior,
Fastlane metadata, App Privacy declarations, backend reachability, screenshot
governance, reviewer notes, and release validation gates.

The goal is not to reduce the product scope. The release train must make each
public claim follow this chain:

```text
implemented feature
-> enabled release flag
-> backend reachable
-> privacy disclosed
-> consent or notice present
-> App Store asset allowed
-> reviewer notes explain exact flow
-> tests and validators enforce no drift
```

## Principles

- Preserve App Store assets in repo, Figma, and Fastlane. Do not delete assets
  to hide drift.
- Classify assets by submission readiness:
  - `SUBMIT_READY`: allowed for public App Store screenshots and metadata.
  - `IMPLEMENTATION_REQUIRED`: kept as repo/design asset, not exported for
    submission until implementation and smoke proof exist.
  - `INTERNAL_REVIEW_ONLY`: allowed for QA, reviewer, or debug boards only.
- Do not claim social, medical, diagnosis, therapy, treatment, or crisis-support
  functionality.
- Keep HealthKit read-only unless a separate reviewed PR changes entitlement
  posture.
- Keep billing and entitlement truth backend-owned.
- Keep protected App Store uploads operator-owned and evidence-based.

## Canonical Gate Source

Root `AGENTS.md` section `App Store release readiness gates` is the hard-gate
source of truth for release readiness checks. This epic, the feature matrix, and
the orchestration packet are planning mirrors that explain how the train will
close each gate. When a readiness gate changes, update root `AGENTS.md` first,
then update this epic, the matrix, and the lane packet in the same PR.

## Current Repo Truth

- `ios/PulsePlate/PrivacyInfo.xcprivacy` is absent on `main`; the iOS app uses
  `UserDefaults`, so PR-1 must add the required-reason privacy manifest.
- `ios/fastlane/app_privacy_details.json` currently declares
  `DATA_NOT_COLLECTED`, while runtime flows send profile, AI query, receipt, and
  activation data to backend endpoints.
- `ios/PulsePlate/Services/AppConfig.swift` silently falls back to
  `https://api.pulseplate.com` in Release when `BASE_URL` is missing or invalid.
- `ios/PulsePlate/Info-Release.plist` only contains a commented `BASE_URL`
  example; PR-3 must make the Release backend explicit HTTPS.
- `ios/PulsePlate/en.lproj/InfoPlist.strings` contains sensitive permission
  strings beyond the current release posture, including tracking copy.
- `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` contains screenshot
  scenarios wider than release-enabled feature flags.
- `ios/PulsePlate/Models/HealthKitManager.swift` uses read-only authorization
  (`toShare: nil`) but has a Swift 6 local-function sendability cleanup.
- `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json` references
  `AppIcon-1024.png` as `ios-marketing`; PR-5 must verify actool assignment and
  image validity before release.

## PR Train

1. **PR-0: release readiness ledger and epic bootstrap**
   - Branch: `release/appstore-readiness-pr0-bootstrap`
   - Add this epic, the feature asset matrix, the canonical task packet, and
     the backlog ledger anchor.
   - No runtime, metadata, asset, or privacy payload changes.

2. **PR-1: privacy manifest and App Privacy truth**
   - Branch: `release/appstore-readiness-pr1-privacy-manifest`
   - Add `ios/PulsePlate/PrivacyInfo.xcprivacy`.
   - Replace `DATA_NOT_COLLECTED` with App Privacy answers matching profile,
     AI, billing, and diagnostics/telemetry truth.
   - Add deterministic contract tests.

3. **PR-2: permission strings cleanup and capability truth**
   - Branch: `release/appstore-readiness-pr2-permission-purpose-strings`
   - Keep only release-used sensitive permission purpose strings.
   - Keep `NSHealthShareUsageDescription`; remove tracking and unused permission
     copy unless runtime evidence exists.

4. **PR-3: Release backend fail-fast**
   - Branch: `release/appstore-readiness-pr3-base-url`
   - Remove silent production fallback from `AppConfig.baseURL()`.
   - Require explicit HTTPS `BASE_URL` in `Info-Release.plist`.
   - Resolve the production backend host in the backend-host decision register
     below before changing runtime configuration.

5. **PR-4: App Store assets governance**
   - Branch: `release/appstore-readiness-pr4-asset-gating`
   - Add screenshot scenario policy with submission status, release flag,
     required smoke tests, privacy disclosure, and reviewer-note requirements.
   - Preserve all assets; gate export/submission only.

6. **PR-5: AppIcon marketing asset fix**
   - Branch: `release/appstore-readiness-pr5-appicon`
   - Repair asset catalog assignment, PNG validity, and actool warning.
   - Do not mix broader App Store asset changes.

7. **PR-6: HealthKit Swift 6 readiness**
   - Branch: `release/appstore-readiness-pr6-healthkit-swift6`
   - Remove Swift 6 sendability warning.
   - Lock read-only HealthKit posture in tests and reviewer notes.

8. **PR-7: AI wellness consent**
   - Branch: `release/appstore-readiness-pr7-ai-consent`
   - Gate first CBT insight request behind explicit wellness-only AI disclosure
     and consent.
   - Keep no-medical/no-therapy/no-crisis positioning.

9. **PR-8: reviewer notes and metadata sync**
   - Branch: `release/appstore-readiness-pr8-reviewer-pack`
   - Sync reviewer notes, metadata, privacy map, screenshots, feature access,
     backend URL, StoreKit flow, HealthKit, and AI consent.

10. **PR-9: release validators in CI**
    - Branch: `release/appstore-readiness-pr9-validation-gates`
    - Add `make ios-appstore-verify` and Fastlane validators for privacy
      manifest, App Privacy, screenshot policy, Release base URL, permission
      strings, and AppIcon marketing asset.

## Out Of Scope

- Deleting App Store assets.
- Removing AI, weekly plan, grocery, HealthKit, personalization, or billing
  backlog features.
- Social sharing or social-network features.
- Medical, diagnosis, therapy, treatment, or crisis-support claims.
- Apple Server API migration.
- Figma or brand-system redesign.
- Billing rewrite.

## Backend Host Decision Register

`canonical_release_base_url` was resolved in execution-order PR-7 (epic
scope PR-3) on branch `release/appstore-readiness-pr7-base-url-fail-fast`.

**Decision:** `https://pulseplate.app`

Resolved signals:

- `ios/PulsePlate/Services/AppConfig.swift` no longer falls back to
  `https://api.pulseplate.com` in Release. The Release path requires an explicit
  HTTPS `BASE_URL` from `Info-Release.plist` and calls `fatalError` if the value
  is missing, empty, non-HTTPS, or lacks a host component.
- `ios/PulsePlate/Info-Release.plist` contains an active `BASE_URL` key set to
  `https://pulseplate.app`.
- Python guard `tests/ios/test_release_base_url_guard.py` enforces the plist
  contract and blocks regression to the silent fallback.
- Swift unit tests in `ios/PulsePlateTests/Services/AppConfigTests.swift` cover
  the `validateReleaseBaseURL` helper that gates the `fatalError` path.

If a future operator decision moves the backend to a dedicated subdomain
(e.g. `api.pulseplate.app`), that change requires a separate PR updating
`Info-Release.plist`, this decision register, and the Python plist guard in
`tests/ios/test_release_base_url_guard.py`.

## Required Gates

Every PR in this train starts with:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "<slice goal>" --task-class Orchestration --pr-phase pre_open
```

Before push, run the normal local bundle unless the operator explicitly approves
a machine-heavy exception:

```bash
pre-commit run --all-files
make verify
```

iOS/App Store slices add the relevant focused checks:

```bash
make ios-test
make ios-appstore-verify
bundle exec fastlane verify_appstore_metadata
```

Protected upload completion remains outside implementation PRs and requires
operator-owned App Store Connect evidence per
`docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`.

## Security Notes

- App Privacy must not declare `DATA_NOT_COLLECTED` while profile, AI, billing,
  receipt, activation, or diagnostics data leaves the device.
- Release backend URL must be explicit HTTPS and fail before submission if
  missing or invalid.
- AI/CBT free text must not leave device without consent and wellness-only
  disclosure.
- HealthKit remains read-only and must not be used for advertising, data mining,
  diagnosis, treatment, or clinical claims.
- UserDefaults use is allowed for non-sensitive local state, but the privacy
  manifest must disclose required-reason API use.
- Secrets remain in Keychain or protected environments; do not put API keys,
  App Store credentials, or live reviewer secrets in plist files.

## Marketing And GTM

Allowed positioning:

```text
AI-powered wellness and nutrition planning.
Personalized meal planning, nutrition targets, shopping support, and habit reflection.
Not medical advice. Not diagnosis. Not therapy.
```

Blocked positioning:

```text
treats eating disorders
diagnoses health conditions
clinical nutrition prescription
therapy / CBT treatment
medical-grade coach
```

Public App Store screenshots and metadata may mention only features that are
`SUBMIT_READY`, release-enabled, privacy-disclosed, smoke-tested, and explained
in reviewer notes.

## Decision Log

1. App Store assets are preserved and governed, not deleted.
2. Public submission claims must match release runtime and backend truth.
3. Social features remain explicitly out of scope.
4. The first technical blocker is privacy manifest plus App Privacy truth.
5. The second technical blocker is Release backend fail-fast.
6. The third technical blocker is AppIcon marketing asset validation.
7. AI/CBT release requires consent, disclosure, and wellness-only posture.
8. Production API host selection is deferred to PR-3 and must be resolved before
   changing `Info-Release.plist`.
