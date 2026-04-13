# Foods Catalog Foundation PR-A Task Packet

**Effective date:** 2026-04-12 (`America/New_York`)
**Status:** Active execution packet
**Mode:** coordinator-owned backend/data migration lane

## Goal

Land one additive Alembic foundation revision that creates repo-aligned PostgreSQL-ready
catalog tables without changing the current runtime, importer, or deploy behavior.

## Source of Truth

- Repo code is the final source of truth for schema shape and compatibility boundaries.
- External operator brief and design note are supportive only and must not override repo truth.
- Schema vocabulary must be grounded in:
  - `app/services/food_store.py`
  - `scripts/build_food_db.py`
  - `app/services/restaurant_store.py`
  - `scripts/import_restaurant_menu.py`
  - `alembic/versions/202604060001_enable_pg_trgm_foods_candidate_indexes.py`

## In Scope

- Add exactly one Alembic revision after `202604060001`
- Create additive `foods` table aligned to the current runtime/local catalog vocabulary
- Create additive `restaurant_chains` and `restaurant_menu_items` tables as future relational targets
- Close the existing PostgreSQL trigram seam by replaying `pg_trgm` + `foods` GIN(trgm) index creation after `foods` exists
- Add narrow migration-focused tests for SQLite upgrade/downgrade safety and static DDL contract checks
- Record deferred follow-up work for ETL/importer/runtime cutover in `docs/roadmap/BACKLOG_LEDGER.md`

## Out of Scope

- No ETL or data backfill
- No runtime cutover from current SQLite/local-first catalog behavior
- No importer rewiring or claim that `scripts/import_restaurant_menu.py` works unchanged with the new tables
- No changes to `core/models.py`, runtime ORM, OpenAPI, deploy files, Meilisearch, vector search, or feature flags
- No `CREATE INDEX CONCURRENTLY`
- No mutation or rename of `food_items`

## Touched Files

- `docs/orchestration/FOODS_CATALOG_FOUNDATION_PR_A_TASK_PACKET_2026-04-12.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `alembic/versions/202604120001_add_foods_catalog_foundation.py`
- `tests/test_foods_catalog_foundation_migration.py`

## Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## Validation Plan

- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Targeted validation:
  - `pytest -q tests/test_foods_catalog_foundation_migration.py`
- Full local gates before undraft:
  - `pre-commit run --all-files`
  - `make verify`
- Manual PostgreSQL proof before undraft:
  - run `alembic stamp 202604060001`
  - then run `alembic upgrade head` against an available PostgreSQL path
  - confirm `foods` exists
  - confirm `ix_foods_canonical_name_gin_trgm`, `ix_foods_group_name_gin_trgm`, and `ix_foods_brand_gin_trgm` exist on `foods`

## Acceptance Criteria

- Exactly one new additive Alembic revision is introduced
- `foods` mirrors the current repo catalog vocabulary instead of inventing a new runtime contract
- `food_items` remains untouched
- `restaurant_chains` and `restaurant_menu_items` land as foundation-only schema targets
- PostgreSQL trigram seam is closed in the clean-upgrade path
- Deferred ETL/importer/runtime cutover work is tracked explicitly in the backlog ledger
