# PR 1111 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#pullrequestreview-3929157106 -> 95f618c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2917980302 -> 64387d53
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2917980308 -> 64387d53
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#pullrequestreview-3929179703 -> 64387d53
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2918085352 -> b8b3d337
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2918085358 -> b8b3d337
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#pullrequestreview-3929291677 -> b8b3d337
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2918157010 -> d98e4aa9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#pullrequestreview-3929369091 -> d98e4aa9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2918212346
Disposition: FIXED
Commit: 95f618c0
Evidence: `docs/design/COLOR_PROFILE_GOVERNANCE.md`, section `Repo-grounded evidence`; `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`, section `Repo-grounded evidence`; `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`, section `Workflow definitions`
Reason: Replaced brittle line-number evidence with section/symbol references and added explicit snapshot-vs-runtime workflow definitions mapped to concrete repo paths, matching the Sourcery review request.

Disposition: FIXED
Commit: 64387d53
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:2154`; `docs/roadmap/BACKLOG_LEDGER.md:2182`; `docs/roadmap/BACKLOG_LEDGER.md:2209`
Reason: Moved both unchecked P1 follow-up trackers out of `## Completed Items` and into the open backlog, so the ledger once again keeps active work under the open-item lane instead of mixing it with merged entries.

Disposition: FIXED
Commit: b8b3d337
Evidence: `docs/design/COLOR_PROFILE_GOVERNANCE.md`, section `Repo-grounded evidence`; `docs/review/PR_1111_FIXED_MAPPING.md`, section `## Fixed in Commit Mapping`
Reason: Tightened the color-governance wording so `Color.init(hex:)` is described as an `sRGB` helper instead of an asset bridge, and aligned the Sourcery mapping proof with the actual section/symbol-based evidence rather than stale line-number references.

Disposition: FIXED
Commit: d98e4aa9
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:193`; `docs/roadmap/BACKLOG_LEDGER.md:1069`; `docs/roadmap/BACKLOG_LEDGER.md:1072`
Reason: Reordered the two new open P1 follow-up items so they live inside the open `### P1` lane and above the existing `### P2` bucket, restoring the ledger's declared priority sort order.

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1111#discussion_r2918212346`
Reason: This CodeRabbit follow-up is a confirmation that the earlier backlog-placement issue is resolved; it does not request an additional code or docs change beyond commit `64387d53`.

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
