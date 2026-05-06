# PR 1684 - Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1684#discussion_r3195834923 -> 3e6217da2
Disposition: FIXED
Commit: 3e6217da2
Evidence: `.github/workflows/frontend-ci.yml` removes workflow-level OIDC permission; `frontend/vite.config.ts` removes `oidc.useGitHubOIDC` and keeps token-based Codecov upload.

## Merge Readiness

- [ ] Current-head CI is complete
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Final merge-readiness wait-window has elapsed
