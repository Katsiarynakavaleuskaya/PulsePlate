# Follow-up plan: Search zero-downtime index swap (P2)

**Ledger:** `docs/roadmap/BACKLOG_LEDGER.md` — anchor `ledger-p2-search-zero-downtime-swap-orchestration` (`PR-TBD-SEARCH-ZERO-DOWNTIME-SWAP`).

**Purpose:** This note is the **planning handoff** after Phase 1 `pg_trgm` DDL lands (`alembic/versions/202604060001_enable_pg_trgm_foods_candidate_indexes.py`). It does **not** implement swap orchestration.

## Coordinator start (next PR)

1. `python3 scripts/orchestration/check_preflight.py`
2. Task analysis from `docs/orchestration/task_analysis.template.md`
3. Route per `docs/orchestration/AGENT_ROUTING_GRAPH.md` (ops + backend + QA)

## Technical themes (outline)

- Prefer `CREATE INDEX CONCURRENTLY` (or provider-equivalent) **outside** default Alembic transaction patterns; align with RLS/migration conventions already used in repo.
- Meili `*_v2` build / validate / warm / swap as documented in ledger DoD for that item.
- Rollback and grace-period cleanup must be documented with tests (ledger DoD).

## Dependency

- Phase 1 `pg_trgm` + conditional `foods` GIN indexes (ADR: `docs/architecture/ADR_SEARCH_PGTRGM_CANDIDATES_LANE_P2.md`).
