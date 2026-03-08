# PR 1022 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#pullrequestreview-3910015244 -> 9c0ab939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900737940 -> 9c0ab939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900737941 -> 9c0ab939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#pullrequestreview-3910017035 -> 9c0ab939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900739559 -> 9c0ab939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900740518 -> dd2b2c9e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900740522 -> dd2b2c9e
Disposition: FIXED
Commit: 9c0ab939, dd2b2c9e
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md:36`, `.cursor/agents/agent-coordinator.md:120`, `docs/roadmap/BACKLOG_LEDGER.md:286`, `scripts/orchestration/skill_router.py:289`, `scripts/orchestration/task_bootstrap.py:152`, `tests/test_skill_router.py:50`, `tests/test_task_bootstrap.py:160`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#pullrequestreview-3910070206 -> 497b87da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900784877 -> 497b87da
Disposition: FIXED
Commit: 497b87da
Evidence: `scripts/orchestration/skill_router.py:303`, `tests/test_skill_router.py:113`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#pullrequestreview-3910070427
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/skill_router.py:28`, `scripts/orchestration/skill_router.py:388`, `tests/test_skill_router.py:139`
Reason: The remaining CodeRabbit notes are advisory only. `SCRAPING_BLOCK_PATTERNS` uses explicit repo-specific phrases rather than short ambiguous tokens, and the frozen module-level `SkillRule` config is treated as read-only policy data; changing blocked-pattern semantics or wrapping `domain_weights` would add churn without affecting the current routing contract.
