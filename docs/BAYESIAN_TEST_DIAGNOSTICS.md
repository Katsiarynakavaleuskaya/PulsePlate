# Bayesian Test Diagnostics

The Bayesian analyzer records per-test executions and provides quick, probabilistic hints about failure categories.

## Enable (env)
- `BAYESIAN_PERSIST=1` to persist history (JSON).
- `BAYESIAN_HISTORY_PATH` (default: `test_execution_history.json`).
- `BAYESIAN_DIAG_VERBOSE=1` to print inline hints in test output.

## Pytest Plugin
- Plugin module: `pytest_bayesian_plugin.py` (autoloaded via pytest.ini addopts).
- Marker: `@pytest.mark.bayesian` (optional, for categorization).

## Nightly Report
- `python scripts/bayesian_quality_report.py` -> `bayesian_quality_report.json` artifact.
