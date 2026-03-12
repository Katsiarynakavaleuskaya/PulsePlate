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

Disposition: FIXED
Commit: 5ad198f4
Evidence: `5ad198f4` removes the false-negative path identified by cubic by using `mergeStateStatus` only when required-check metadata is unavailable in `scripts/ci/check_current_head_pr_checks.py:157-371`, hardens `_api_request()` with guaranteed connection cleanup in `scripts/ci/check_current_head_pr_checks.py:32-65`, updates the active backlog item to point at PR `#1129` in `docs/roadmap/BACKLOG_LEDGER.md:6032-6039`, and adds deterministic draft / missing-token / HTTP-error / metadata-unavailable regression coverage in `tests/test_current_head_pr_checks.py:157-292`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#pullrequestreview-3934252786 -> 5ad198f4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922564734 -> 5ad198f4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#pullrequestreview-3934263739 -> 5ad198f4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922575286 -> 5ad198f4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922575288 -> 5ad198f4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922575292 -> 5ad198f4

Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_current_head_pr_checks.py:337-362`
Reason: The concern is valid in the abstract, but the current implementation already distinguishes “required check metadata unavailable” from “no required checks configured”, falls back to `mergeStateStatus` only in the unavailable case, and prints advisory checks without blocking on non-required runs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922616508

Disposition: FIXED
Commit: 53a0f896
Evidence: `53a0f896` lets local wrapper auth fall back to `gh auth status` before `gh pr view` in `scripts/orchestration/check_merge_ready.py:97-136`, converts pre-gate PR-body fetch failures into deterministic gate failures via `PreGateFailure` in `scripts/orchestration/check_merge_ready.py:25-194`, and adds focused regression coverage for both behaviors in `tests/test_orchestration_merge_ready.py:58-137`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#pullrequestreview-3934298012 -> 53a0f896
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922602995 -> 53a0f896
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#pullrequestreview-3934316276 -> 53a0f896
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1129#discussion_r2922616515 -> 53a0f896

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
