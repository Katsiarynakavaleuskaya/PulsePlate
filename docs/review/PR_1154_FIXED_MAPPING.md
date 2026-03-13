# PR 1154 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 0d69605f
Evidence: appstore/fitchef/en-US/iphone-6.9/preview/storyboard.json:15
Reason: The preview storyboard now maps `shot-01` through `shot-07` exactly once and restores the governed seven-shot sequence for the EN App Store preview lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931241438 -> 0d69605f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931246422 -> 0d69605f

Disposition: FIXED
Commit: 0d69605f
Evidence: appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json:155
Reason: Shot 07 now uses bounded copy, `AI Nutrition Guide`, instead of the stronger `AI Nutrition Coach` claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931246430 -> 0d69605f

Disposition: FIXED
Commit: 0d69605f
Evidence: tests/test_fitchef_app_store_pack.py:98
Reason: The preview integrity test now enforces exact ordered storyboard coverage instead of set-membership only, so duplicate shot IDs or missing governed shots fail deterministically.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3944355243 -> 0d69605f

Disposition: FIXED
Commit: 536b4f40
Evidence: docs/review/PR_1154_FIXED_MAPPING.md:33
Reason: The local hard-gate checkbox remains unchecked until a real post-fix `make verify` pass completes; it is only marked complete after that verify run succeeds.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931246446 -> 536b4f40

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
