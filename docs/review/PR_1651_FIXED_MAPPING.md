# PR #1651 Fixed in Commit Mapping

## Summary

PR #1651 migrates generic developer Makefile targets to `DEV_PYTHON` while preserving `.venv` fallback.

## Scope

- `Makefile` -- 12 targets migrated from `VENV_PYTHON` to `DEV_PYTHON`; `OPENAPI_PYTHON` removed
- `tests/test_makefile_dev_python_migration.py` -- new guard tests (7 tests)
- `tests/test_check_local_verify_environment.py` -- updated expected strings
- `README.md` / `CONTRIBUTING.md` -- document `DEV_PYTHON` behavior
- `docs/roadmap/BACKLOG_LEDGER.md` -- backlog updates

## Fixed in Commit Mapping

- Makefile `DEV_PYTHON` migration + guard tests -> `2da617ab6`
- README/CONTRIBUTING docs update -> `afc0abd0d`
- Backlog ledger updates -> `f8c9c7166`
- Review mapping artifact -> `8ee0633e2`
- RUNBOOK/DEPENDENCY_MANAGEMENT stale refs fix (bug-hunter finding) -> `ead32d8d5`

## Validation

- `pytest -q tests/test_devcontainer_foundation.py` -- 10 passed
- `pytest -q tests/test_makefile_dev_python_migration.py` -- 7 passed
- `pytest -q tests/test_check_local_verify_environment.py::test_verify_critical_make_targets_use_repo_interpreter_module_mode` -- 1 passed
- `pytest -q tests/test_repo_policy_guards.py` -- 14 passed
- `make validate-min` -- passed
- `make test-fast` -- passed
- `make lint` -- passed
- `pre-commit run --all-files` -- all passed
- `python3 scripts/orchestration/check_preflight.py --mode analyze` -- PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -- OK

## Review Thread Disposition

Populate after CodeRabbit, Sourcery, and Cubic reviews complete.
