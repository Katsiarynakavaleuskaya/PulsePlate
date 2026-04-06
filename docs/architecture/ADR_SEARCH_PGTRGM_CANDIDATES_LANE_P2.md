# ADR: PostgreSQL `pg_trgm` preparation for food candidate lane (P2)

## Status

Accepted — Phase 1 (extension + conditional indexes only). Runtime candidate queries and strategy routing are **out of scope** for this slice.

## Context

- Semantic bootstrap search loads a bounded candidate pool from the `foods` table (`canonical_name` and macros); see `app/services/food_store.py` (`_load_semantic_candidates`).
- The canonical packaged food catalog is built into SQLite with FTS5 today; see `scripts/build_food_db.py` (`CREATE TABLE foods`, `foods_fts`).
- Meilisearch remains an optional shadow/index lane; see `app/services/search_meili.py` (`MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE` includes `canonical_name`).
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md` anchor `ledger-p2-search-pgtrgm-candidate-generation` and follow-up `ledger-p2-search-zero-downtime-swap-orchestration`.

## Decision

1. On **PostgreSQL only**, Alembic enables `pg_trgm` (`CREATE EXTENSION IF NOT EXISTS pg_trgm`).
2. If and only if `public.foods` exists, create **GIN** indexes with `gin_trgm_ops` on:
   - `canonical_name` (primary candidate column aligned with `_load_semantic_candidates`)
   - `group_name`, `brand` (secondary text facets present in the SQLite catalog schema)
3. Index names (stable for ops/runbooks):
   - `ix_foods_canonical_name_gin_trgm`
   - `ix_foods_group_name_gin_trgm`
   - `ix_foods_brand_gin_trgm`
4. **No `CREATE INDEX CONCURRENTLY`** in this migration: Alembic runs in a transaction; large-table production rollout belongs to the zero-downtime orchestration ledger item.

## Consequences

- **Positive:** DBA/app owners can validate `pg_trgm` and index definitions before wiring SQL candidate generation.
- **Negative:** Brief locking may occur on `foods` when indexes are created on a populated table; mitigate via follow-up swap/orchestration PR.
- **SQLite / tests:** Migration no-ops (same pattern as `alembic/versions/202602280002_enable_pgvector_extension.py`).

## References

- Migration: `alembic/versions/202604060001_enable_pg_trgm_foods_candidate_indexes.py`
- Task analysis: `docs/orchestration/task_analysis_SEARCH_PGTRGM_CANDIDATES_P2.md`
- Deploy note: `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md` (extension provisioning)
