# PR 1241 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: The upstream action README still documents `permissions: id-token: write` together with `contents: write` in the canonical example workflow for `advanced-security/component-detection-dependency-submission-action`: https://github.com/advanced-security/component-detection-dependency-submission-action#example-workflows
Reason: This PR intentionally mirrors the upstream permission contract for the dependency-submission action. Dropping `id-token: write` without upstream documentation or a proven reduced-permission run would add avoidable risk to the new repo-managed submission lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1241#pullrequestreview-4012983822
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1241#discussion_r2993656146
