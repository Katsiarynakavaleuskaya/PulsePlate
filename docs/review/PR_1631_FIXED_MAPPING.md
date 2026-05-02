# PR #1631 Fixed in Commit Mapping

## Summary

PR #1631 adds repo-local App Store validation gates for iOS release readiness
(PR-12 in the App Store release readiness train).

## Scope

- `Makefile` (ios-appstore-verify target)
- `scripts/release/check_ios_appstore_verify.py` (10 deterministic checks)
- `tests/ios/test_ios_appstore_verify.py` (5 tests)
- `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md` (pre-upload step)
- `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md` (PR-12 record)
- `docs/roadmap/BACKLOG_LEDGER.md` (PR-12 reference)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177198133
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177198134
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177200720 -> c134706e4
Disposition: FIXED
Commit: c134706e4
Evidence: scripts/release/check_ios_appstore_verify.py:72

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177200721 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: scripts/release/check_ios_appstore_verify.py:93

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177200722 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: scripts/release/check_ios_appstore_verify.py:279

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177200724 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: tests/ios/test_ios_appstore_verify.py:57

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177201581 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: docs/review/PR_1631_FIXED_MAPPING.md (this artifact, canonical format)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177201582 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: docs/review/PR_1631_FIXED_MAPPING.md (Discussion Thread Pass section)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177201832
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177201833
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177201834
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177207781 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: Makefile:547

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1631#discussion_r3177208824 -> 7328209f9
Disposition: FIXED
Commit: 7328209f9
Evidence: docs/review/PR_1631_FIXED_MAPPING.md (canonical format applied)

## Validation

- `python3 scripts/release/check_ios_appstore_verify.py`
- `make ios-appstore-verify`
- `pytest -q tests/ios/`
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py`
- `pytest -q tests/test_release_reviewer_packet_hashes.py`
- `pre-commit run --all-files`
- `git diff --check`

## Merge Readiness

- [x] All review threads dispositioned (FIXED/DEFERRED)
- [x] CodeRabbit: PASS / no new actionables
- [x] Cubic: PASS
- [x] Sourcery: skipped (not applicable for this PR scope)
- [x] CI current-head checks green (lint, test-pr, build-and-test, diff-coverage, security)
- [x] pre-commit run --all-files green
