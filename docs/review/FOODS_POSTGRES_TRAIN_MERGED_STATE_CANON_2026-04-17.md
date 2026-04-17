# Foods PostgreSQL Train Merged-State Canon

**Effective date:** 2026-04-17 (`America/New_York`)
**Status:** Canonical merged-state reference for post-B3 governance closeout

## Canonical PR-to-lane mapping
- `PR-A` -> PR `#1409` (`feat(db): add repo-aligned foods catalog foundation and restaurant schema`) merged at `2026-04-13T09:39:31Z`, which is April 13, 2026 in `America/New_York`; merge commit `6096c1a35`; source: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409>
- `PR-B1` -> PR `#1413` (`feat(data): promote offline foods snapshot into PostgreSQL foods`) merged at `2026-04-13T17:43:58Z`, which is April 13, 2026 in `America/New_York`; merge commit `46e5a1e64`; source: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413>
- `PR-B2` -> PR `#1419` (`feat(data): bridge restaurant importer into PostgreSQL restaurant catalog`) merged at `2026-04-13T22:39:45Z`, which is April 13, 2026 in `America/New_York`; merge commit `fea79048a`; source: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419>
- `PR-B3` -> PR `#1435` (`feat(data): restaurant PostgreSQL shadow reads + parity (B3)`) merged at `2026-04-16T22:23:24Z`, which is April 16, 2026 in `America/New_York`; merge commit `91a0e5723`; source: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435>

## Canonical follow-through state
- Post-B3 docs/governance closeout is the active lane in PR `#1462` and packet `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md`.
- The next bounded implementation lane after PR `#1462` is `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership`.
- SQLite remains canonical runtime authority for foods/restaurant runtime surfaces until the cutover seam documented in `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md` is explicitly retired.

## Supporting repo artifacts
- `docs/review/PR_1409_FIXED_MAPPING.md`
- `docs/review/PR_1413_FIXED_MAPPING.md`
- `docs/review/PR_1419_FIXED_MAPPING.md`
- `docs/review/PR_1435_FIXED_MAPPING.md`
- `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md`
- `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md`
