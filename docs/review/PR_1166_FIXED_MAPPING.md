# PR 1166 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 0f5f50e2c69bca4cf2568355fc0040f1a41bfccb
Evidence: `scripts/orchestration/requested_agents.py:10` now centralizes requested-agent normalization for shared reuse, `scripts/orchestration/skill_router.py:481` consumes that helper for deduplicated router echoes, and `tests/test_skill_router.py:48` plus `tests/test_skill_router.py:80` add router-level regression coverage for bundle boosts and normalized requested-agent output.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948494983 -> 0f5f50e2c69bca4cf2568355fc0040f1a41bfccb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934986996 -> 0f5f50e2c69bca4cf2568355fc0040f1a41bfccb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934986999 -> 0f5f50e2c69bca4cf2568355fc0040f1a41bfccb

Disposition: FIXED
Commit: d165935d2bbf4c455efc2d1b8d8dbd1ab3ac976f
Evidence: `scripts/orchestration/context_pack.py:234` now folds `requested_agents` into `compute_task_packet_id(...)`, `scripts/orchestration/task_bootstrap.py:245` passes normalized requested agents into the packet-id calculation, and `tests/test_task_bootstrap.py:127` proves distinct requested-agent inputs no longer collide on the same packet id.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948499021 -> d165935d2bbf4c455efc2d1b8d8dbd1ab3ac976f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934990492 -> d165935d2bbf4c455efc2d1b8d8dbd1ab3ac976f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934992479 -> d165935d2bbf4c455efc2d1b8d8dbd1ab3ac976f

Disposition: FIXED
Commit: c9f2d33787022ded91e8f4ff45ff624b2ab2c5e5
Evidence: `scripts/orchestration/task_bootstrap.py:267` now force-adds `security-auditor` back into the review path for privileged surfaces after requested-agent overrides, and `tests/test_task_bootstrap.py:145` locks that invariant with a regression test for `scripts/orchestration/**` routing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948501266 -> c9f2d33787022ded91e8f4ff45ff624b2ab2c5e5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934992480 -> c9f2d33787022ded91e8f4ff45ff624b2ab2c5e5

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
