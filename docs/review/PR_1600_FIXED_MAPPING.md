# PR 1600 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1600

Branch: `release/appstore-readiness-pr2-permission-purpose-strings`

Title: `fix(ios): remove unused sensitive permission strings from release metadata`

## Scope

This PR is App Store readiness PR-2. It removes sensitive permission purpose
strings that are not backed by current release runtime capability evidence and
keeps the read-only HealthKit consent copy.

## Coordinator Evidence

Task packet:

- `artifacts/orchestration/task_packets/20ece0834a86.json` (local, gitignored)

Declared role order:

1. `agent-coordinator`
2. `ios-engineer-agent`
3. `appstore-release-agent`
4. `privacy-compliance-agent`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Actionable review threads were triaged after the PR moved to ready-for-review.

Future actionable review threads must be listed here with disposition-specific
proof before they are resolved:

- `FIXED`: thread URL -> commit SHA made after the comment timestamp
- `NOT-A-BUG`: thread URL plus evidence
- `DEFERRED`: thread URL plus backlog link

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 13e3d855e
Evidence: `tests/ios/test_info_plist_permission_strings.py` now scans Xcode
Evidence: `INFOPLIST_KEY_*UsageDescription` build settings are covered.
Evidence: localized `InfoPlist.strings` files are discovered dynamically.
Evidence: ATT checks stay fail-closed.
Evidence: `docs/orchestration/APPSTORE_RELEASE_READINESS_PR2_PERMISSION_PACKET_2026-04-30.md`
Evidence: current-head CI wording now says iOS unit tests rather than iOS unit/UI.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1600#discussion_r3168663349 -> 13e3d855e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1600#discussion_r3168686984 -> 13e3d855e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1600#pullrequestreview-4206008955 -> 13e3d855e

## Local Validation

Full local `make verify` was intentionally not run per operator CPU-budget
instruction. Current-head GitHub CI is the heavy validation signal for this
lane.

Narrow local gates run:

```text
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/ios/test_info_plist_permission_strings.py tests/test_ios_appstore_asset_validators.py
plutil -lint ios/PulsePlate/en.lproj/InfoPlist.strings ios/PulsePlate/es.lproj/InfoPlist.strings ios/PulsePlate/ru.lproj/InfoPlist.strings
cd ios && bundle exec fastlane validate_metadata_package
git diff --check
pre-commit run --all-files
```

Pre-push hooks also passed.

## Merge Readiness

- [ ] current-head PR CI is complete
- [ ] CodeRabbit/Sourcery/Cubic have no actionable items
- [ ] all review threads are dispositioned
- [ ] strict merge readiness passes
