# PR 1254 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999531470
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/task_bootstrap.py:70`; `scripts/orchestration/task_bootstrap.py:75`
Reason: PR2 deliberately scopes `needs_docs_sync` to the explicit implementation roots `app/`, `core/`, `scripts/`, `frontend/`, and `ios/`; widening that policy to additional top-level paths is a separate follow-up, not a correctness bug in this slice.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999531473
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/task_bootstrap.py:173`; `scripts/orchestration/task_bootstrap.py:181`
Reason: The approved PR2 `needs_agents_sync` rule is intentionally limited to `AGENTS.md`, nested `AGENTS.md`, `.cursor/agents/`, and `SKILL.md`; orchestration protocol docs are not part of this trigger contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999531886 -> e3a4be58d5a56a991ef1442288b2c2a9f1aa562f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999531893 -> e3a4be58d5a56a991ef1442288b2c2a9f1aa562f
Disposition: FIXED
Commit: e3a4be58d5a56a991ef1442288b2c2a9f1aa562f
Evidence: `scripts/orchestration/task_bootstrap.py:176`; `scripts/orchestration/task_bootstrap.py:181`; `tests/test_task_bootstrap.py:569`; `tests/test_task_bootstrap.py:596`
Reason: Root-level `SKILL.md` is now treated consistently with `AGENTS.md`, and coverage now exercises root/nested contract paths plus a non-triggering docs case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#pullrequestreview-4019477054
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md:2083`
Reason: The broad review suggestion to centralize bootstrap sync-policy constants is valid but intentionally outside the bounded PR2 bootstrap slice; it is tracked as a dedicated follow-up item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#pullrequestreview-4019488003 -> e3a4be58d5a56a991ef1442288b2c2a9f1aa562f
Disposition: FIXED
Commit: e3a4be58d5a56a991ef1442288b2c2a9f1aa562f
Evidence: `scripts/orchestration/task_bootstrap.py:180`; `tests/test_task_bootstrap.py:575`; `tests/test_task_bootstrap.py:579`
Reason: The root-level `SKILL.md` gap raised by the review shell is closed in the follow-up fix commit and covered by deterministic tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999566123
Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/task_bootstrap.py:176`; `scripts/orchestration/task_bootstrap.py:181`; `tests/test_task_bootstrap.py:569`; `tests/test_task_bootstrap.py:596`
Reason: This later CodeRabbit inline note repeats a gap that is already closed on the current head; the review itself acknowledges the issue was addressed in commits `e3a4be5` through `b9172ea`, so no additional post-comment code change is required.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#pullrequestreview-4019521610
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999566123`; `scripts/orchestration/task_bootstrap.py:176`; `scripts/orchestration/task_bootstrap.py:181`
Reason: This review shell only summarizes the single inline CodeRabbit note above; because the current head already contains the root-level `SKILL.md` fix, the shell carries no additional unresolved action.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#discussion_r2999587498 -> f69629ebfa4100398ee9b3a26b55acfc3277907b
Disposition: FIXED
Commit: f69629ebfa4100398ee9b3a26b55acfc3277907b
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:2110`
Reason: The downstream PR3 dependency now points at the concrete PR2 identifier `PR-1254`, eliminating the stale placeholder that triggered the inline review comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1254#pullrequestreview-4019546133 -> f69629ebfa4100398ee9b3a26b55acfc3277907b
Disposition: FIXED
Commit: f69629ebfa4100398ee9b3a26b55acfc3277907b
Evidence: `scripts/orchestration/task_bootstrap.py:130`; `scripts/orchestration/task_bootstrap.py:133`; `scripts/orchestration/task_bootstrap.py:162`; `tests/test_task_bootstrap.py:616`; `tests/test_task_bootstrap.py:623`; `docs/roadmap/BACKLOG_LEDGER.md:2110`
Reason: The new review shell is fully addressed by the latest fix commit: the stale backlog dependency was corrected, prefix matching now uses a shared helper, and deterministic packet-stability coverage now locks the additive top-level metadata fields.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
