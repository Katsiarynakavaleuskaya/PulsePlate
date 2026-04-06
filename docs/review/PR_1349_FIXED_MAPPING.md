<!-- markdownlint-disable MD034 -->
# PR 1349 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: **FIXED** — Alembic downgrade no longer drops `pg_trgm`; ADR updated with `path:line` evidence anchors (bot feedback on extension lifecycle + docs Phase 1).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#pullrequestreview-4060739449 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#pullrequestreview-4060741341 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#pullrequestreview-4060753710 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#pullrequestreview-4060759442 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#discussion_r3038306530 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#discussion_r3038308428 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#discussion_r3038320617 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#discussion_r3038320632 -> e8282c5e1b229f1650319235c497a5b472555252
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349#discussion_r3038326566 -> e8282c5e1b229f1650319235c497a5b472555252

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green (re-run after mapping commit)
- [ ] `make verify` green (re-run after mapping commit)

Notes: P2 Phase 1 — `pg_trgm` + conditional GIN(trgm) on `foods` (Postgres), ADR + runbook + ledger; no runtime search-path change.

<!-- markdownlint-enable MD034 -->
