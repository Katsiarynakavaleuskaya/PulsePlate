<!-- markdownlint-disable MD034 -->
# PR 1287 — Fixed in Commit Mapping

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments yet.

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [ ] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: Draft recovery PR for the four ncurses image-alert findings on `main`.
The initial two-CVE draft scope was narrowed after the mandatory QA and
bug-hunter post-open passes flagged the repo rule that suppression PRs must be
CVE-scoped. The latest
`main` CI cancellations on merge commit `6b16dadc23dc99ddc4f1761afbeeff2b2a68f1f9`
did not reproduce as a deterministic repo-side failure in local validation, so
this PR intentionally limits code changes to the live security-tab remediation.
<!-- markdownlint-enable MD034 -->
