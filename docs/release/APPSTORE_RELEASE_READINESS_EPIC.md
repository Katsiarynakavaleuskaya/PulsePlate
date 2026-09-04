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

- `ios/PulsePlate/PrivacyInfo.xcprivacy` exists and declares the UserDefaults
  required-reason API with tracking disabled.
- `ios/fastlane/app_privacy_details.json` no longer declares
  `DATA_NOT_COLLECTED`; it declares HEALTH, PURCHASE_HISTORY, and
  OTHER_USER_CONTENT as linked data.
- Release builds require an explicit HTTPS `BASE_URL` from
  `ios/PulsePlate/Info-Release.plist` and fail before submission if it is
  missing or invalid.
- Release permission strings are narrowed to the current read-only HealthKit
  posture.
- App Store screenshot scenarios remain wider than the public submission set:
  only `core_value` is `SUBMIT_READY`; unreleased feature assets are preserved
  but remain `IMPLEMENTATION_REQUIRED`.
- HealthKit remains read-only and Swift 6 readiness cleanup has landed.
- The approved `AppIcon-1024.png` is a valid, byte-locked 1024x1024 PNG. For the
  current Xcode/actool contract, its `ios-marketing` entry is exactly the four
  keys `filename`, `idiom`, `scale`, and `size`; `platform` is absent from this
  entry. CAB-03 adds that exact assignment contract and a separate unsigned
  Release simulator compilation after the complete unit run.
- The `platform` absence rule applies only to this `ios-marketing` entry. It
  changes no other asset entry and implies no iOS/visionOS support, Xcode
  project-setting, target-membership, or PNG-content change.
- The validator-owned SHA-256 pin applies to the current CAB-03 admitted baseline, not
  to every future visual revision. A dedicated asset-focused visual/provenance
  PR may atomically replace the PNG and rotate that single approved hash pin.
- The unified repo-local `make ios-appstore-verify` gate remains the canonical
  local release validator; CAB-03 strengthens its existing AppIcon check rather
  than creating another validator family.
- Protected App Store Connect upload and final submission evidence remain
  operator-owned release-ops tasks outside repo branches.

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
   - Execution branch: `release/appstore-readiness-pr8-appicon-marketing-asset`
   - Repair asset catalog assignment, PNG validity, and actool warning.
   - Do not mix broader App Store asset changes.
   - **Historical status (PR-8):** `AppIcon-1024.png` was confirmed as a valid
     1024x1024 PNG and no pixel change was needed, but the current-Xcode/actool
     assignment remained incomplete: `scale=1x` was absent while `platform`
     was present on the `ios-marketing` entry.
   - **CAB-03 correction:** bind the exact four-field marketing slot with
     `platform` absent and retain the approved PNG bytes in the existing
     validators, then run one blocking unsigned Release simulator build after
     the complete unit test target.
     This performs no archive, distribution signing, upload, submission, or
     App Store Connect mutation.

7. **PR-6: HealthKit Swift 6 readiness**
   - Branch: `release/appstore-readiness-pr9-healthkit-swift6`
   - Remove Swift 6 sendability warning.
   - Lock read-only HealthKit posture in tests and reviewer notes.
   - **Status (PR-9):** Local function extracted to private instance method
     (`fetchSum`) in `HealthKitManager.swift` to eliminate Swift 6 sendability
     warning. Read-only posture preserved (`toShare: nil`). Deterministic guard
     added in `tests/ios/test_healthkit_readonly_guard.py` (5 checks: read-only
     auth, no write permission string, read permission present, no write
     operations, no nested local functions).

8. **PR-7: AI wellness consent**
   - Branch: `release/appstore-readiness-pr7-ai-consent`
   - Gate first CBT insight request behind explicit wellness-only AI disclosure
     and consent.
   - Keep no-medical/no-therapy/no-crisis positioning.
   - **Status (PR-10):** Consent gate added at `AIInsightViewModel.submit()` as
     the first guard before any network request. `AIWellnessConsentStore` persists
     boolean consent in UserDefaults (key `ai_wellness_consent_accepted_v1`).
     `AIWellnessDisclosureSheet` presents wellness-only disclosure with 5 semantic
     points. Declining returns to idle without sending data. Accepting persists
     consent and proceeds with submit. Localized in en/ru/es. Deterministic guard
     added in `tests/ios/test_ai_wellness_consent_guard.py` (7 checks). Swift
     tests added in `AIWellnessConsentTests` (5 tests). CI test targets updated.

9. **PR-8: reviewer notes and metadata sync**
    - Branch: `release/appstore-readiness-pr8-reviewer-pack`
    - Sync reviewer notes, metadata, privacy map, screenshots, feature access,
      backend URL, StoreKit flow, HealthKit, and AI consent.
    - **Status (PR-11):** Reviewer notes rewritten with 7 sections: wellness
      positioning, AI consent and third-party provider disclosure, HealthKit
      read-only posture, StoreKit/billing truth, test account placeholder,
      feature limitations, and screenshot policy. Descriptions narrowed to
      `SUBMIT_READY` surfaces only (removed weekly wellness progress claim).
      Release notes updated to reflect actual release train changes. Deterministic
      reviewer-pack guard added in `tests/ios/test_appstore_reviewer_pack_guard.py`
      (25 checks). Submission matrix and metadata audit updated.

10. **PR-12: release validation gates**
     - Branch: `release/appstore-readiness-pr12-validation-gates`
     - Add `make ios-appstore-verify` as the unified repo-local validation
       entrypoint. The gate checks release BASE_URL, AppIcon, PrivacyInfo,
       App Privacy details, permission strings, HealthKit read-only posture,
       AI consent, reviewer pack, screenshot policy, and StoreKit pricing
       truth boundaries. No App Store Connect upload. No runtime changes.
     - **Status (PR-12):** Validator script at
       `scripts/release/check_ios_appstore_verify.py` (10 deterministic
       checks). Makefile target `ios-appstore-verify` runs the validator
       plus all iOS guard tests, wellness language guard, and reviewer
       packet hash guard. Test coverage in
       `tests/ios/test_ios_appstore_verify.py`. Release runbook updated
       with mandatory pre-upload step. Protected upload remains
       operator-owned.

11. **PR-13: closeout reconciliation**
     - Branch: `release/appstore-readiness-pr13-closeout-reconciliation`
     - Reconcile ledger, release docs, metadata audit, reviewer submission
       matrix, screenshot gate, and reviewer notes with the post-PR #1631
       validation-gates state.
     - No runtime changes, no Fastlane upload changes, no protected App Store
       Connect execution, and no asset changes. Protected upload evidence
       remains operator-owned.

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
# CAB-03 example; other slices use the class selected by their coordinator packet.
python3 scripts/orchestration/task_bootstrap.py --goal "<slice goal>" --task-class Release --pr-phase pre_open
```

The task class must follow the current packet and slice rather than a universal
epic default. CAB-03 uses `--task-class Release`; another slice uses the class
selected by its own coordinator packet.

Before push, run focused tests for the touched surface and the normal narrow
local bundle:

```bash
# CAB-03 example; a different slice uses the focused tests selected by its packet.
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" -m pytest -q \
  tests/ios/test_appicon_marketing_asset.py::test_appicon_marketing_entry_is_declared_once \
  tests/ios/test_appicon_marketing_asset.py::test_appicon_marketing_validator_reports_exact_canonical_success \
  tests/test_ci_workflow_pr_size_governance_contract.py::test_ios_release_simulator_build_stays_blocking_after_complete_unit_run \
  tests/test_ci_workflow_pr_size_governance_contract.py::test_ios_release_build_run_digest_rejects_appended_command
"$VENV_PYTHON" -m pytest -q tests/ios/test_ios_appstore_verify.py -k appicon
make validate-changed
pre-commit run --all-files
```

Full local verification is outside the default machine budget. Run it only
after an explicit human override authorizes one invocation:

```bash
make verify  # explicit one-invocation human override required
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

Public App Store screenshots may show only features that are `SUBMIT_READY`,
release-enabled, privacy-disclosed, smoke-tested, and explained in reviewer
notes. Public metadata must not imply a screenshot-only feature is ready unless
the same proof exists; broader metadata claims require manual pre-submission
review until the metadata validator covers them directly.

## Decision Log

1. App Store assets are preserved and governed, not deleted.
2. Public submission claims must match release runtime and backend truth.
3. Social features remain explicitly out of scope.
4. The first technical blocker is privacy manifest plus App Privacy truth.
5. The second technical blocker is Release backend fail-fast.
6. The AppIcon PNG bytes were valid, but the current-Xcode/actool marketing-slot
   assignment was incomplete. CAB-03 closes the exact four-field entry and
   Release-compilation seam without changing other asset entries, platform
   support, project settings, targets, or PNG content, and without claiming
   archive, signing, upload, submission, or App Store acceptance.
7. AI/CBT release requires consent, disclosure, and wellness-only posture.
8. Production API host selection is deferred to PR-3 and must be resolved before
   changing `Info-Release.plist`.
