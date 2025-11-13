# Bayesian Test Diagnostics

The Bayesian analyzer learns from test execution history to estimate the likelihood of different failure categories (such as flaky tests, environmental issues, or regressions), providing probabilistic hints that help diagnose test failures more efficiently. It records per-test executions and uses this historical data to categorize and prioritize potential failure causes.

## Enable (env)

- `BAYESIAN_PERSIST=1` to persist history (JSON).
- `BAYESIAN_HISTORY_PATH` (default: `test_execution_history.json`).
- `BAYESIAN_DIAG_VERBOSE=1` to print inline hints in test output.

## Pytest Plugin

- Plugin module: `pytest_bayesian_plugin.py` (autoloaded via pytest.ini addopts).
- Marker: `@pytest.mark.bayesian` (optional, for categorization).

## Nightly Report

- `python scripts/bayesian_quality_report.py` -> `bayesian_quality_report.json` artifact.
