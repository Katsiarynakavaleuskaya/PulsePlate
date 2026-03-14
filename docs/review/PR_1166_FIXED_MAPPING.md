# PR 1166 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 0f5f50e26c9802c72bae8bd186e6404cbf271659
Evidence: `scripts/orchestration/requested_agents.py:10` now centralizes requested-agent normalization for shared reuse, `scripts/orchestration/skill_router.py:481` consumes that helper for deduplicated router echoes, and `tests/test_skill_router.py:48` plus `tests/test_skill_router.py:80` add router-level regression coverage for bundle boosts and normalized requested-agent output.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948494983 -> 0f5f50e26c9802c72bae8bd186e6404cbf271659
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934986996 -> 0f5f50e26c9802c72bae8bd186e6404cbf271659
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934986999 -> 0f5f50e26c9802c72bae8bd186e6404cbf271659

Disposition: FIXED
Commit: 6c2d15b5df25b78298575e8bb74b061d4085af07
Evidence: `tests/test_skill_router.py:100` now directly proves duplicate requested-agent slugs collapse to one normalized request and do not stack an extra `pulseplate-gates` bundle boost, which is the exact regression described in `discussion_r2934996808`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934996808 -> 6c2d15b5df25b78298575e8bb74b061d4085af07

Disposition: FIXED
Commit: d165935dcbabb704abc52728a0ec0dbcb212ae20
Evidence: `scripts/orchestration/context_pack.py:234` now folds `requested_agents` into `compute_task_packet_id(...)`, `scripts/orchestration/task_bootstrap.py:245` passes normalized requested agents into the packet-id calculation, and `tests/test_task_bootstrap.py:127` proves distinct requested-agent inputs no longer collide on the same packet id.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948499021 -> d165935dcbabb704abc52728a0ec0dbcb212ae20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934990492 -> d165935dcbabb704abc52728a0ec0dbcb212ae20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934992479 -> d165935dcbabb704abc52728a0ec0dbcb212ae20

Disposition: FIXED
Commit: c9f2d337bc2bacab37d54145a776e579436779e7
Evidence: `scripts/orchestration/task_bootstrap.py:267` now force-adds `security-auditor` back into the review path for privileged surfaces after requested-agent overrides, and `tests/test_task_bootstrap.py:145` locks that invariant with a regression test for `scripts/orchestration/**` routing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948501266 -> c9f2d337bc2bacab37d54145a776e579436779e7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934992480 -> c9f2d337bc2bacab37d54145a776e579436779e7

Disposition: FIXED
Commit: 8532f9dad7d18618719b82cad87d5aa04b801236
Evidence: `scripts/orchestration/skill_router.py:341` now treats `docs/review/` plus merge-readiness/review-mapping keywords as privileged security-trigger surfaces, `scripts/orchestration/task_bootstrap.py:167` rewrites stale `honored_primary` dispositions to `honored_secondary` after later promotions, and `tests/test_skill_router.py:289` plus `tests/test_task_bootstrap.py:159` add regression coverage for both behaviors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948506013 -> 8532f9dad7d18618719b82cad87d5aa04b801236
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#pullrequestreview-3948515087 -> 8532f9dad7d18618719b82cad87d5aa04b801236
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934996806 -> 8532f9dad7d18618719b82cad87d5aa04b801236
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1166#discussion_r2934996810 -> 8532f9dad7d18618719b82cad87d5aa04b801236

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
