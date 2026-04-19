<!-- markdownlint-disable MD034 -->
# PR 1337 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
Notes: The original runtime blocker for this PR was private package mirror freshness. As of April 5, 2026, `https://katsiarynakavaleuskaya.github.io/PulsePlate/simple/` publishes `marshmallow 4.3.0`, and local validation on current head passes without code changes beyond the Dependabot bump.
<!-- markdownlint-enable MD034 -->
