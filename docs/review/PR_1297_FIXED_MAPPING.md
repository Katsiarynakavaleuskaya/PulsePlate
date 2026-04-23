# PR 1297 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: `deploy/WORKFLOW.md`; current head `fc0da359` does not contain the `bridge-job` wording referenced by the Sourcery review, so there is no remaining code/doc change to apply in this lane.
Reason: The Sourcery review wrapper and inline thread point to wording that is not present on the current head. The comment is fully dispositioned as a non-actionable review artifact on the latest revision.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1297#pullrequestreview-4048197945
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1297#discussion_r3025741998

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- Scope: CD hotfix only. This lane restores production deploy config resolution for release tags by retrying GitHub environment variable reads with a dedicated token only after the default workflow token gets a 403.
