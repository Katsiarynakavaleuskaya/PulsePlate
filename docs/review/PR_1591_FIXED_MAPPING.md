# PR 1591 - Fixed in Commit Mapping

## PR

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591>
- Branch: `release/appstore-readiness-pr1-privacy-manifest`
- Base: `main`
- Implementation commit: `6e601deca`

## Local Validation

Disposition: FIXED
Commit: `6e601deca`
Evidence:

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `pytest -q tests/ios/test_privacy_manifest_contract.py tests/ios/test_app_privacy_details_contract.py tests/test_ios_appstore_asset_validators.py` PASS, 43 tests
- `pytest -q tests/ios/test_privacy_manifest_contract.py tests/ios/test_app_privacy_details_contract.py tests/test_ios_appstore_asset_validators.py` PASS, 44 tests after post-ready review fixes
- `pytest -q tests/test_repo_policy_guards.py` PASS, 14 tests
- `cd ios && bundle exec fastlane validate_metadata_package` PASS
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python` PASS
- `pre-commit run --all-files` PASS
- `plutil -lint ios/PulsePlate/PrivacyInfo.xcprivacy` PASS
- `git diff --check` PASS
- push hooks PASS, including `pip-audit`, backend changed tests, and full-repo Bandit

## Operator CPU Override

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-app-store-release-readiness-closure`
Reason: The operator explicitly paused additional local `make` gates for CPU
load during draft opening. `make verify` was not run to completion locally and
`make ios-test` was not run locally for this opening. GitHub current-head CI is
the heavy validation signal before ready-for-review and merge readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable human, CodeRabbit, Sourcery, or Cubic comments have been reviewed
yet. New actionables must be added below with one of: `FIXED`, `NOT-A-BUG`, or
`DEFERRED`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#pullrequestreview-4203449341 -> 2f9bdf4fc
Disposition: FIXED
Commit: 2f9bdf4fc
Evidence: `tests/ios/test_app_privacy_details_contract.py` centralizes runtime-flow privacy probes in `AppPrivacyRuntimeFlow`; `tests/ios/test_privacy_manifest_contract.py` asserts the UserDefaults required-reason entry is present without requiring it to be the only accessed API type.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#pullrequestreview-4203457899 -> 2f9bdf4fc
Disposition: FIXED
Commit: 2f9bdf4fc
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now lists PR #1582 and PR #1591 / `release/appstore-readiness-pr1-privacy-manifest` in `Target PR`; `tests/ios/test_privacy_manifest_contract.py` now asserts `membership_exception_blocks` is non-empty before checking exclusions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#discussion_r3166473693 -> 2f9bdf4fc
Disposition: FIXED
Commit: 2f9bdf4fc
Evidence: `tests/ios/test_privacy_manifest_contract.py` asserts `membership_exception_blocks` is non-empty before `PrivacyInfo.xcprivacy` exclusion checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#discussion_r3166747911 -> 4941c3c38
Disposition: FIXED
Commit: 4941c3c38
Evidence: `ios/fastlane/app_privacy_details.json` now uses Fastlane/App Store Connect category identifiers `HEALTH`, `OTHER_USER_CONTENT`, and `PURCHASE_HISTORY`; `tests/ios/test_app_privacy_details_contract.py` locks the allowed Fastlane category ID set.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#pullrequestreview-4203813159 -> 4941c3c38
Disposition: FIXED
Commit: 4941c3c38
Evidence: `tests/ios/test_app_privacy_details_contract.py` now asserts `data_protections` exists and is a list before checking `DATA_NOT_COLLECTED`, runtime-flow protections, and tracking protections.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1591#discussion_r3166780304 -> 4941c3c38
Disposition: FIXED
Commit: 4941c3c38
Evidence: `tests/ios/test_app_privacy_details_contract.py` uses `_data_protections(...)` to fail closed when `data_protections` is missing or malformed.

## Merge Readiness

- [ ] PR is draft until current-head CI and post-open review settle.
- [ ] Required current-head checks PASS on the latest commit.
- [ ] CodeRabbit, Sourcery, and Cubic have no unresolved actionables.
- [ ] No unresolved review threads.
- [ ] Required wait window observed after latest bot/review activity.
