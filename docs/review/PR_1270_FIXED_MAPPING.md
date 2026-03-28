# PR 1270 — Fixed in Commit Mapping

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
- [ ] Mandatory post-open bug-hunter pass completed
Notes: Draft PR `#1270` is the security-first remediation lane requested after merged PR `#1269`. The code change is intentionally narrow: carry the safe npm lockfile remediation already proposed for GitHub alerts `#76`, `#82`, and `#83`, then refresh the Pygments seam documentation/backlog for still-open GitHub alerts `#80` and `#81`, which remain upstream-blocked because `GHSA-5239-wwwm-4pmq` still exposes no patched release. The branch stays isolated from the Postgres foundation slice and from unrelated feature or infra work.
