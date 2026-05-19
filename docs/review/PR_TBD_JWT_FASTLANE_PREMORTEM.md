# PR TBD Premortem - JWT / Fastlane Suppression Unblock Monitor

## Summary

Plan: open a narrow security/governance PR that revalidates Dependabot alert
`#142` for Ruby `jwt` in `ios/Gemfile.lock`, remediates only if Bundler can
reach `jwt >= 3.2.0`, and otherwise adds monitoring so the temporary Trivy
suppression cannot be forgotten.

Failure frame: it is 48 hours from now; the PR landed, but the alert remained
open or the suppression hid a newly fixable vulnerability.

## Most Likely Failure

The most likely failure is a false-green suppression monitor: the repository
continues to check only the file-level `Suppression expires` marker while
individual `Review-by` dates go stale. This would let `jwt` remain suppressed
even after the next review date passes.

Disposition: FIXED.

Evidence: `scripts/ci/check_trivy_ignore_policy_expiry.py` now evaluates every
`Review-by: YYYY-MM-DD` marker in addition to the single file-level expiry, and
`tests/test_trivy_ignore_policy_expiry.py` covers stale review dates.

## Most Dangerous Failure

The most dangerous failure is forcing `jwt 3.2.0` into `ios/Gemfile.lock` while
Fastlane still declares `jwt < 3`. That could break protected App Store Connect
release tooling while giving a misleading impression that the Dependabot alert
was safely closed.

Disposition: NOT-A-BUG for the current diff.

Evidence: no lockfile update was made. Fresh resolver evidence on 2026-05-19
still resolves `fastlane 2.234.0` with `jwt (>= 2.1.0, < 3)` and `jwt 2.10.2`.
The PR adds `scripts/ci/check_jwt_fastlane_unblock.py` to fail when Bundler
reaches `jwt >= 3.2.0` or Fastlane stops constraining `jwt < 3`.

## Hidden Assumption

The hidden assumption was that a date-based review reminder is enough. It is
not enough by itself because the alert is blocked by dependency-graph
compatibility, not by the absence of a patched `jwt` release.

Disposition: FIXED.

Evidence: the new JWT/Fastlane guard parses Bundler output directly and tests
both blocked and unblocked resolver graphs in
`tests/test_jwt_fastlane_unblock_guard.py`.

## Revised Plan

- Keep Dependabot alert `#142` open and documented as blocked until Fastlane
  permits `jwt >= 3.2.0` or the release tooling no longer depends on Fastlane's
  `jwt 2.x` graph.
- Add per-suppression `Review-by` enforcement to the existing Trivy expiry
  guard.
- Add a focused JWT/Fastlane unblock checker that fails on a compatible
  resolver graph instead of relying on stale docs.
- Record fresh 2026-05-19 RubyGems and Bundler evidence in the security note
  and backlog ledger.

## Pre-Merge Checklist

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- `python3 scripts/ci/check_jwt_fastlane_unblock.py`
- Focused pytest for the two new guard surfaces.
- `make validate-changed`
- `pre-commit run --all-files`

## Decision

Proceed with changes.
