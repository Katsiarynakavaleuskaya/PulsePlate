# App Store Release Readiness PR-2 Permission Packet

**Packet ID:** `appstore-release-readiness-pr2-permission-purpose-strings-2026-04-30`

**Epic:** `epic/appstore-release-readiness-full-feature`

**Branch:** `release/appstore-readiness-pr2-permission-purpose-strings`

**Title:** `fix(ios): remove unused sensitive permission strings from release metadata`

## Coordinator Start

Primary agent:

1. `agent-coordinator`

Declared role order:

1. `agent-coordinator`
2. `ios-engineer-agent`
3. `appstore-release-agent`
4. `privacy-compliance-agent`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Bootstrap packet:

- `artifacts/orchestration/task_packets/20ece0834a86.json`

## Scope

Remove sensitive iOS permission purpose strings that are not backed by current
release runtime capability evidence. Preserve the read-only HealthKit consent
copy.

In scope:

- `ios/PulsePlate/*/InfoPlist.strings`
- `tests/ios/test_info_plist_permission_strings.py`
- App Store readiness packet, epic, and ledger references

Out of scope:

- implementing camera, location, photo library, microphone, contacts, Face ID,
  or ATT runtime features
- changing HealthKit read/write posture
- changing App Privacy payloads or screenshot assets

## Release Truth

Current runtime evidence supports:

- HealthKit read-only access through `HealthKitManager`
- `NSHealthShareUsageDescription`

Current runtime evidence does not support release permission strings for:

- camera
- location
- photo library
- microphone
- contacts
- Face ID
- App Tracking Transparency

## Validation Plan

Do not run full local `make verify` for this PR because the operator explicitly
deferred heavy local validation.

Required narrow local gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/ios/test_info_plist_permission_strings.py tests/test_ios_appstore_asset_validators.py
git diff --check
pre-commit run --all-files
```

Heavy signal:

- GitHub current-head CI for iOS unit tests, lint, security, diff coverage,
  asset validation, and merge readiness

## Stop Conditions

- A removed permission string is required by a release-enabled runtime feature.
- ATT runtime is introduced in this slice.
- HealthKit posture changes from read-only.
- A validator needs full local `make verify` to prove correctness.
