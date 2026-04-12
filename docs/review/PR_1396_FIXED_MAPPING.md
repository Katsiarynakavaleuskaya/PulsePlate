# PR 1396 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
Notes: This PR head is refreshed onto `origin/main` to keep the diff scoped to the intended test-only bumps `faker 40.12.0 -> 40.13.0` and `hypothesis 6.151.10 -> 6.151.12` across `requirements-dev*`, `requirements-test*`, and `requirements-lock.txt`. The previous Dependabot merge head introduced unrelated runtime/CUDA lock churn; the refreshed head preserves the runtime baseline from `main` and adds temporary emergency wheel fallback entries for the new test wheels while the approved proxy catches up.
