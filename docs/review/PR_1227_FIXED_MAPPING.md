# PR 1227 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: `.github/workflows/nightly-tests.yml:55`, `.github/workflows/nightly-tests.yml:58`, `package.json:13`, `package.json:14`, `package.json:28`, `package.json:31`
Reason: The root Node package is required by repo-level business collateral scripts, so the root cache entry and root `npm-ci` step are intentionally unconditional. The frontend step keeps an explicit `working-directory` because it is the non-default path, while the root install intentionally uses the action's default repository root.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1227#pullrequestreview-3988288594

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
