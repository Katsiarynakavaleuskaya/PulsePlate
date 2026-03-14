# PR 1169 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 7b6ef2da5e5149bb63793f203a0a6512c952a356
Evidence: `scripts/orchestration/check_merge_ready.py:56` defines a stable `BLOCKING_MERGE_READY_GATES` order, while `scripts/orchestration/check_merge_ready.py:253` now derives `blocking=yes/no` from `policy.blocking` instead of hardcoding the label; `tests/test_orchestration_merge_ready.py:225` locks the contract with a regression test that proves a non-blocking policy prints `blocking=no`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#pullrequestreview-3948850887 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#discussion_r2935290995 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
