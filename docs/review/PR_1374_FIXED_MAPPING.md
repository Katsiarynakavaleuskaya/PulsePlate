<!-- markdownlint-disable MD034 -->
# PR 1374 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: GitHub GraphQL `reviewThreads(first:100)` returned an empty set for PR `#1374`; there are no actionable human or bot review threads to map.
Reason: This Dependabot PR only needs governance artifact coverage plus a Ruby 3.1 compatibility pin so the existing security bump can pass the `validate-assets` lane.

- No actionable review comments

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [x] No unresolved review threads
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green locally

### Scope Notes

- Keep the security update `addressable 2.8.9 -> 2.9.0` in `ios/Gemfile.lock`.
- Add `public_suffix < 7` in `ios/Gemfile` so the iOS asset lane remains compatible with Ruby `3.1`.
- No product code, backend behavior, or App Store metadata changes are included in this PR.

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `cd ios && bundle install`
- `pre-commit run --all-files`
- `make verify`

Notes: Mirror `### Fixed in Commit Mapping` in the PR body after push so Phase 2 gates see the same disposition summary on GitHub.

<!-- markdownlint-enable MD034 -->
