# Task Analysis

**Task:** Land PostgreSQL `pg_trgm` extension and conditional GIN(trgm) indexes on `foods` text columns (candidate lane prep). No runtime query-path switch in this PR.

**Domain(s):** Architecture | Multiple (migrations, docs, search)

**Complexity:** Moderate

**Priority:** P2

- **Priority track (P0-A / P0-B / P1):** P2 (search modernization follow-up)

**Expected Outcome:** On PostgreSQL, `CREATE EXTENSION IF NOT EXISTS pg_trgm` runs via Alembic; when `public.foods` exists, `ix_foods_*_gin_trgm` indexes are created. SQLite/tests unchanged. ADR + deploy note document extension privileges, index names, and boundary to zero-downtime follow-up.

**Invariants Affected:**

- One BMI Engine
- Thin HTTP Adapter Policy
- Layer Separation (DDL in Alembic; no router/runtime change)
- Contract-First (`/api/v1/foods`* unchanged)
- Other: Search strategy remains SQLite FTS + optional Meili; pg_trgm is additive DB prep only.

**Domain hints (pick if relevant; links-only):**

- `alembic/versions/`*: Postgres-only branches; reversible downgrade; no `CREATE INDEX CONCURRENTLY` in this slice (documented trade-off vs `ledger-p2-search-zero-downtime-swap-orchestration`).
- `app/services/food_store.py`: semantic candidates load `canonical_name` from `foods` (evidence for index choice).

**Risks:**

1. **Extension privileges:** `CREATE EXTENSION` may require superuser on managed Postgres; mitigation: document pre-provisioned `pg_trgm` in provider console (`docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md`, ADR).
2. **Missing `foods` on app DB:** Today `foods` is SQLite-built; indexes are conditional on `to_regclass('public.foods')` so migration is safe no-op until catalog is colocated on Postgres.

**Proposed Approach:**

1. Add Alembic revision after `202603110001` enabling `pg_trgm` and conditional indexes.
2. ADR with evidence anchors to `food_store.py`, `build_food_db.py`, migration path.
3. Ledger progress line under `ledger-p2-search-pgtrgm-candidate-generation`; full DoD remains for a later PR (runtime routing + tests).

**Agent Assignment:**

- **Primary:** migrations + docs (single implementation pass in this session)
- **Secondary:** security review if extension policy questions arise
- **Dependencies:** preflight PASS

**Constraints:**

- No OpenAPI / `frontend/src/api/`* changes.
- No runtime food search behavior change.
- English-first ledger text.

**Analysis by:** agent-coordinator (executed)
**Date:** 2026-04-06
