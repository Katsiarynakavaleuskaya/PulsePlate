# PR 1400 — Fixed in Commit Mapping

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
Notes: This PR head is refreshed onto `origin/main` to keep the diff scoped to the intended `transformers 5.5.0 -> 5.5.3` bump in `requirements.txt` and `requirements-lock.txt`. The previous Dependabot merge head introduced unrelated runtime/CUDA lock churn; the refreshed head preserves the CPU-neutral baseline from `main` and adds a temporary emergency wheel fallback for `transformers==5.5.3` while the approved proxy catches up.
