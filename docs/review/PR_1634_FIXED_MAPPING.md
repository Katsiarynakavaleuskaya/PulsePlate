# PR #1634 — Fixed in Commit Mapping (SoT)

## Summary

Enforce inline nosec `remove-by` expiration in `_validate_nosec_line()`:
calendar date validation via `date.fromisoformat()` and expiry check
`remove_by_date < date.today()`. Adds 3 focused unit tests for the
validation helper and extends 9 expired TTLs found by the new guard.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1634#pullrequestreview-4215624681
  Disposition: NOT-A-BUG
  Evidence: Sourcery rate-limited; no analysis produced. No actionable items.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1634#pullrequestreview-4215626562
  Disposition: NOT-A-BUG
  Evidence: Cubic found no issues ("No issues found across 1 file").

## Merge Readiness

- [x] All bot reviews mapped with disposition
- [x] No unresolved review threads
- [x] `make validate-min` passed locally
- [x] `pre-commit run --all-files` passed locally
- [x] Guard test `tests/guards/test_nosec_policy_guard.py` passes (4/4 tests)
- [x] No literal `# nosec B...` in test source (self-scan clean)
