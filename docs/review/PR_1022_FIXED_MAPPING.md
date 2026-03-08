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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900863932 -> b4c806fc
Disposition: FIXED
Commit: b4c806fc
Evidence: `scripts/orchestration/skill_router.py:141`, `scripts/orchestration/skill_router.py:149`, `scripts/orchestration/skill_router.py:271`, `tests/test_skill_router.py:117`, `tests/test_skill_router.py:129`, `tests/test_skill_router.py:141`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2900863933 -> b4c806fc
Disposition: FIXED
Commit: b4c806fc
Evidence: `scripts/orchestration/skill_router.py:299`, `tests/test_skill_router.py:153`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#pullrequestreview-3910198436
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/skill_router.py:141`, `scripts/orchestration/skill_router.py:149`, `scripts/orchestration/skill_router.py:299`, `tests/test_skill_router.py:117`, `tests/test_skill_router.py:153`
Reason: This aggregate CodeRabbit review only summarizes the two inline findings already fixed and mapped above (`discussion_r2900863932`, `discussion_r2900863933`), so it does not add a separate unresolved defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2901378994 -> 028be2eb
Disposition: FIXED
Commit: 028be2eb
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md:36`, `scripts/orchestration/skill_router.py:19`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2901378995 -> 028be2eb
Disposition: FIXED
Commit: 028be2eb
Evidence: `scripts/orchestration/skill_router.py:29`, `scripts/orchestration/skill_router.py:363`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1022#discussion_r2901378998 -> 028be2eb
Disposition: FIXED
Commit: 028be2eb
Evidence: `scripts/orchestration/skill_router.py:381`, `tests/test_skill_router.py:209`
