# Agent instructions (scope: alembic/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `alembic/` and below.
- Key files: `alembic.ini`, `alembic/versions/`.

## Commands (run from repo root)
- Create migration: `alembic revision -m "<message>"` (add `--autogenerate` if configured).
- Upgrade: `alembic upgrade head`
- Downgrade: `alembic downgrade -1`

## Conventions
- Keep migrations deterministic and reversible.
- Align schema changes with SQLAlchemy models and tests.
- Confirm target DB (SQLite/Postgres) before running destructive migrations.
