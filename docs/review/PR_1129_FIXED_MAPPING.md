# PR 1129 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 56a49c9f
Evidence: `56a49c9f` treats `StatusContext.state=EXPECTED` as pending in `scripts/ci/check_current_head_pr_checks.py:232-244`, so waiting status contexts no longer read as false failures, and it makes the local wrapper fetch the live PR body before invoking the Phase2 gate in `scripts/orchestration/check_merge_ready.py:89-140`, which removes the empty-body regression revealed by the current-head wrapper path. Regression coverage was added in `tests/test_current_head_pr_checks.py:202-214` and `tests/test_orchestration_merge_ready.py:58-87,173-238`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#pullrequestreview-3934249599 -> 56a49c9f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922561675 -> 56a49c9f

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
