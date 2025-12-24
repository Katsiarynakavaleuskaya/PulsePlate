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

## Import hygiene (hard rules)

- Do NOT use `importlib.util.spec_from_file_location`,
  `module_from_spec`, or `exec_module` in tests
  (exceptions are explicitly whitelisted in guard tests).
- Do NOT mutate `sys.modules` in tests.
- `sys.path.insert` is only allowed in `conftest.py`
  and `test_test_pro_access_coverage.py`.
- `TESTING=true` must be set before importing `app`
  (handled centrally in `pytest_configure`).
- If a test imports symbols from `app`,
  a guard-test must assert their presence.

### Import hygiene exceptions (intentional)
Dynamic imports allowed only for script-style tests:
- `tests/test_test_pro_access_coverage.py`
- `tests/test_ensure_database_versions.py`
- `tests/conftest.py` (xdist/db + env bootstrap)

sys.path.insert allowed only in:
- `tests/conftest.py`
- `tests/test_test_pro_access_coverage.py`

### Pre-commit verification
```bash
# 1. No dynamic imports (except whitelisted)
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py"

# 2. No sys.path.insert (except allowed)
git grep -n "sys\.path\.insert" tests \
  | grep -vE "test_test_pro_access_coverage\.py|conftest\.py"

# 3. No sys.modules mutations
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" tests

# All should return empty or only whitelisted files
```
