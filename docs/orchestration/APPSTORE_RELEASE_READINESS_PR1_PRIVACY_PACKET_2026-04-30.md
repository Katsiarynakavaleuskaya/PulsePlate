# App Store Release Readiness PR-1 Privacy Packet

**Packet ID:** `appstore-release-readiness-pr1-privacy-2026-04-30`

**Epic:** `epic/appstore-release-readiness-full-feature`

**Branch:** `release/appstore-readiness-pr1-privacy-manifest`

**PR title:** `fix(ios): add privacy manifest and align App Privacy disclosures`

## Scope

Close the first technical App Store readiness blocker:

- add the iOS required-reason privacy manifest for `UserDefaults`
- replace the previous `DATA_NOT_COLLECTED` App Privacy payload with collected-data
  disclosures for current profile, AI query, and billing network flows
- keep HealthKit validator behavior read-only without requiring the global
  `DATA_NOT_COLLECTED` posture
- add deterministic pytest contracts for privacy manifest and App Privacy drift

## Out Of Scope

- Release backend fail-fast and canonical production host selection
- sensitive permission-string cleanup
- screenshot scenario gating
- AppIcon asset repair
- HealthKit Swift 6 runtime cleanup
- AI consent runtime flow
- reviewer notes and metadata copy sync
- protected App Store Connect uploads

## Role Order

1. `agent-coordinator`
2. `ios-engineer-agent`
3. `appstore-release-agent`
4. `privacy-compliance-agent`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Mandatory post-open review lane:

```text
qa-engineer-agent -> bug-hunter
```

## Evidence Plan

Focused gates:

```bash
pytest -q tests/ios/test_privacy_manifest_contract.py tests/ios/test_app_privacy_details_contract.py
pytest -q tests/test_ios_appstore_asset_validators.py
plutil -lint ios/PulsePlate/PrivacyInfo.xcprivacy
cd ios && bundle exec fastlane validate_metadata_package
```

Pre-push local gate:

```bash
pre-commit run --all-files
```

Operator CPU override for this lane: do not run additional local `make` gates
before opening the PR. GitHub current-head CI is the heavy signal after push.

`make ios-appstore-verify` is planned for PR-9 and is not expected to exist in
this slice.

## App Privacy Mapping

| Runtime flow | Source | App Privacy category | Purpose | Protection |
| --- | --- | --- | --- | --- |
| Profile and nutrition context | `ios/PulsePlate/Services/ProDailyNutritionService.swift`, `ios/PulsePlate/Services/ProfileProvider.swift` | `HEALTH` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` |
| Free-form CBT/AI query | `ios/PulsePlate/Services/CBTInsightService.swift` | `OTHER_USER_CONTENT` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` |
| Receipt and activation data | `ios/PulsePlate/Services/SubscriptionBillingService.swift` | `PURCHASE_HISTORY` | `APP_FUNCTIONALITY` | `DATA_LINKED_TO_YOU` |

No `DATA_USED_TO_TRACK_YOU` entry is allowed in this PR.

## Decision Log

1. `PrivacyInfo.xcprivacy` is added under `ios/PulsePlate/`, which is a
   file-system synchronized Xcode root group and is not listed in target
   membership exceptions.
2. The App Privacy payload no longer uses the global `DATA_NOT_COLLECTED`
   answer because current iOS runtime sends profile, AI query, and billing data
   to backend endpoints.
3. On-device HealthKit read-only posture remains guarded by purpose strings and
   reviewer-copy validators, but PR-1 does not keep the old global
   `DATA_NOT_COLLECTED` posture.
