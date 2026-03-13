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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931264427 -> 0d69605f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931264436 -> 0d69605f

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
Commit: b42fb823
Evidence: tests/test_fitchef_app_store_pack.py:28
Reason: `_repo_path()` now rejects absolute paths and `..` escapes by resolving against `REPO_ROOT` and requiring the normalized path to stay inside the repository.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931264433 -> b42fb823

Disposition: FIXED
Commit: 536b4f40
Evidence: docs/review/PR_1154_FIXED_MAPPING.md:33
Reason: The local hard-gate checkbox remains unchecked until a real post-fix `make verify` pass completes; it is only marked complete after that verify run succeeds.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#discussion_r2931246446 -> 536b4f40

Disposition: NOT-A-BUG
Evidence: appstore/fitchef/en-US/iphone-6.9/preview/storyboard.json:15, appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json:155, appstore/fitchef/en-US/metadata/upload_checklist.md:3, tests/test_fitchef_app_store_pack.py:114
Reason: This aggregate CodeRabbit review only summarizes underlying inline findings that are already dispositioned above; it does not add a standalone unresolved defect once the mapped thread URLs are closed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3944090112

Disposition: NOT-A-BUG
Evidence: appstore/fitchef/en-US/iphone-6.9/preview/storyboard.json:15, tests/test_fitchef_app_store_pack.py:31, tests/test_fitchef_app_store_pack.py:114
Reason: This cubic summary review aggregates underlying findings already mapped in the canonical artifact, so the review-level URL itself does not require an additional standalone code change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3944109244

Disposition: FIXED
Commit: e508e2fc
Evidence: tests/test_fitchef_app_store_pack.py:26
Reason: `_load_json()` now uses the stricter `dict[str, Any]` return type expected by the review nitpick.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3946665221 -> e508e2fc

Disposition: FIXED
Commit: e508e2fc
Evidence: tests/test_fitchef_app_store_pack.py:14, tests/test_fitchef_app_store_pack.py:37
Reason: The guard test now documents the mascot taxonomy source of truth and makes the `relative_to()` containment check explicit with `_ = ...`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3946770483 -> e508e2fc

Disposition: FIXED
Commit: f65db89b
Evidence: tests/test_fitchef_app_store_pack.py:74
Reason: The metadata blocked-term guard now reports the offending terms explicitly, which closes the latest CodeRabbit debugging nitpick.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1154#pullrequestreview-3946855116 -> f65db89b

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [x] Required checks PASS with no pending required jobs
- [x] No unresolved review threads
- [x] No actionable bot comments
- [x] Final post-bot wait cycle completed
