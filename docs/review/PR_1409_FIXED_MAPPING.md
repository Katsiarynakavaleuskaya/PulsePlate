<!-- markdownlint-disable MD034 -->
# PR 1409 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 9238ac69c275412547bbb1aa521f7e41833607d1
Evidence: `alembic/versions/202604120001_add_foods_catalog_foundation.py:72`; `alembic/versions/202604120001_add_foods_catalog_foundation.py:80`; `alembic/versions/202604120001_add_foods_catalog_foundation.py:134`; `alembic/versions/202604120001_add_foods_catalog_foundation.py:157`; `tests/test_foods_catalog_foundation_migration.py:37`; `tests/test_foods_catalog_foundation_migration.py:89`; `tests/test_foods_catalog_foundation_migration.py:157`; `docs/orchestration/FOODS_CATALOG_FOUNDATION_PR_A_TASK_PACKET_2026-04-12.md:69`; `docs/roadmap/BACKLOG_LEDGER.md:4666`
Reason: The foundation migration now guards pre-existing `foods`, uses repo-aligned `restaurant_chains` / `chain_id`, keeps `Numeric` defaults self-documenting, pins the migration tests to `FOUNDATION_REVISION`, validates non-trigram indexes plus FK fidelity, updates the PostgreSQL proof instructions to the stamped sequence, and moves the deferred follow-through item back under Open Items. The `foods` guard and stamped-proof corrections were also identified by cubic.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#pullrequestreview-4095728810 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#pullrequestreview-4095731022 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#pullrequestreview-4095734627 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#pullrequestreview-4095830398 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070193194 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070193195 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070195414 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070196042 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070196043 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070196044 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070200762 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070200763 -> 9238ac69c275412547bbb1aa521f7e41833607d1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070309108 -> 9238ac69c275412547bbb1aa521f7e41833607d1

Disposition: NOT-A-BUG
Evidence: `alembic/versions/202604120001_add_foods_catalog_foundation.py:191`; `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md:81`; `docs/architecture/ADR_SEARCH_PGTRGM_CANDIDATES_LANE_P2.md:16`
Reason: The `pg_trgm` extension call is intentional and matches the accepted Phase 1 PostgreSQL candidate-index lane. Managed-provider privilege limits are handled operationally by pre-enabling `pg_trgm`; this foundation revision only replays the already-approved extension/index seam after `foods` exists.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070193191

Disposition: NOT-A-BUG
Evidence: `tests/test_foods_catalog_foundation_migration.py:37`; `tests/test_foods_catalog_foundation_migration.py:97`; `tests/test_foods_catalog_foundation_migration.py:178`; `alembic/env.py:33`
Reason: The migration tests run every Alembic step in a fresh subprocess and inspect the SQLite database through direct `create_engine(...)` calls in the parent process. No cached `core.db` engine or `SessionLocal` state is reused across upgrade/downgrade steps, so resetting module globals in this test would be redundant.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#pullrequestreview-4095832513
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#discussion_r3070311540

Disposition: NOT-A-BUG
Evidence: `AGENTS.md:5`; `AGENTS.md:8`; `tests/test_foods_catalog_foundation_migration.py:37`
Reason: CodeRabbit's walkthrough "Docstring Coverage" warning is advisory and not part of the repository's hard merge gates. The touched helper introduced in this PR already has a bilingual docstring; the remaining warning does not indicate a merge-blocking regression in this lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1409#issuecomment-4232685869

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
