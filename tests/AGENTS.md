# Agent instructions (scope: tests/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `tests/` and below.
- Key directories: `tests/` (pytest suite), `conftest.py` (shared fixtures).

## Commands (run from repo root)
- Test: `make test`, `make test-fast`
- Coverage: `make cov`, `make cov-check`
- Targeted: `pytest tests/<path> -q`, `pytest -k "<pattern>" -q`

## Conventions
- Use pytest fixtures from `conftest.py`; keep tests isolated.
- Maintain >=97% total coverage; add tests for new branches.
- Never mock `builtins.__import__` or `builtins.float`.
- Preserve xdist DB isolation: each worker gets its own SQLite path.
- Prefer `monkeypatch` over global mutations; avoid real sleeps.
