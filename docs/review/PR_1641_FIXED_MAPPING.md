# PR #1641 Fixed in Commit Mapping

## Summary

PR #1641 fixes the import hygiene guard failure on `main` by removing
`sys.path.insert` from `tests/evals/conftest.py` and removing the stale
allowlist entry from `tests/test_repo_policy_guards.py`.

## Root Cause

`tests/evals/conftest.py` mutated `sys.path` to make `scripts.evals.*`
importable. The import hygiene guard (`tests/test_import_hygiene_guard.py`)
forbids this pattern in test files. The mutation was redundant because
`pyproject.toml` already sets `pythonpath = "."`.

## Scope

- `tests/evals/conftest.py`
- `tests/test_repo_policy_guards.py`

## Fixed in Commit Mapping

Pending bot review comments. Will be populated after CodeRabbit, Sourcery,
and Cubic reviews complete.

## Validation

- `pytest -q tests/test_import_hygiene_guard.py` — PASS
- `pytest -q tests/test_repo_policy_guards.py` — PASS
- `pytest -q tests/evals/` — PASS (53 tests)
- `make validate-min` — PASS
- `pre-commit run --all-files` — PASS

## Review Thread Disposition

Populate after bot reviews complete.
