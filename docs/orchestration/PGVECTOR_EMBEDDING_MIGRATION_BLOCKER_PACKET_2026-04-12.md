# PGVector Embedding Migration Blocker Packet

Date: `2026-04-12`
Lane: `coordinator-owned PostgreSQL migration blocker fix`
Branch: `fix/pgvector-embedding-migration-blocker`

## Summary

Fix pre-existing PostgreSQL migration blocker in `202602280003_convert_embedding_to_vector768.py`.

Current clean-room PostgreSQL `alembic upgrade head` fails before downstream revisions because
the migration uses a subquery inside `ALTER TABLE ... ALTER COLUMN ... USING (...)`, which
PostgreSQL rejects with `cannot use subquery in transform expression`.

## Source Of Truth

- Repo migration chain in `alembic/versions/`
- Runtime / schema contracts already checked into repo
- Local PostgreSQL execution proof

## In Scope

- Minimal fix inside `202602280003_convert_embedding_to_vector768.py`
- Regression test for the migration DDL contract
- Local validation proving PostgreSQL clean-room upgrade succeeds through current main head

## Out Of Scope

- No changes to downstream revisions unrelated to the blocker
- No runtime RAG/schema redesign
- No PR-A foods catalog edits in this lane
- No deploy / OpenAPI / importer changes

## Touched Files

- `alembic/versions/202602280003_convert_embedding_to_vector768.py`
- `tests/test_pgvector_embedding_migration.py`
- `docs/orchestration/PGVECTOR_EMBEDDING_MIGRATION_BLOCKER_PACKET_2026-04-12.md`

## Execution Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pytest -q tests/test_pgvector_embedding_migration.py`
- local PostgreSQL clean-room `alembic upgrade head` on `pgvector/pgvector:pg16`
- `pre-commit run --all-files`
- `make verify`

## Success Criteria

- PostgreSQL no longer errors at revision `202602280003`
- Clean-room PostgreSQL migration chain reaches current branch head
- Regression test locks the migration away from subquery-based transform logic
