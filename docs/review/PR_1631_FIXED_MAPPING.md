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

## Fixed in Commit Mapping

- App Store verification script -> `2ce505fee`
- Makefile target -> `312a1c355`
- Validator tests -> `395131dea`
- Release docs/backlog -> `bb4d1a498`

## Validation

- `python3 scripts/release/check_ios_appstore_verify.py`
- `make ios-appstore-verify`
- `pytest -q tests/ios/`
- `pytest -q tests/guards/test_wellness_language_blockers_guard.py`
- `pytest -q tests/test_release_reviewer_packet_hashes.py`
- `pre-commit run --all-files`
- `git diff --check`

## Review Thread Disposition

### CodeRabbit

1. **P2: Enforce complete screenshot scenario coverage**
   - Disposition: DEFERRED
   - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature`
   - Reason: Enhancement for future iteration. Current check validates no overclaim (SUBMIT_READY + IMPLEMENTATION_REQUIRED contradiction). Adding canonical scenario enumeration is a follow-up.

2. **P2: Detect currency-symbol price claims**
   - Disposition: DEFERRED
   - Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature`
   - Reason: Enhancement. Current patterns cover $, USD, EUR, RUB. Broader unicode currency symbols can be added in follow-up.

3. **Add VENV_PYTHON precheck**
   - Disposition: FIXED
   - Commit: `c134706e4`
   - Evidence: `Makefile:547`

4. **Remove unused _length variable (F841)**
   - Disposition: FIXED
   - Commit: `c134706e4`
   - Evidence: `scripts/release/check_ios_appstore_verify.py:79`

### Cubic

- No actionable findings.

### Sourcery

- Skipped (not applicable for this PR scope).
