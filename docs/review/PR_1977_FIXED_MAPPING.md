# PR 1977 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open Sourcery review comments were fixed in code/tests before thread resolution.

## Fixed in Commit Mapping
Disposition: FIXED
Commit: `a3528ce8a`
Evidence: `app/routers/favicon.py` exports `FAVICON_ROUTE_PATH`; `app/main.py` imports and reuses it for bootstrap validation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178548 -> a3528ce8a

Disposition: FIXED
Commit: `a3528ce8a`
Evidence: `tests/test_app_endpoints_combined.py` asserts `not route.dependant.dependencies` for `GET /favicon.ico`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178554 -> a3528ce8a

## Premortem Findings
- PM-001 duplicate/legacy ownership false-green. Disposition: FIXED. Commit: `ceb82f8fa`. Evidence: `legacy_app.py` no longer defines `@app.get("/favicon.ico")`; `tests/test_app_endpoints_combined.py` asserts canonical `app.routers.favicon` ownership.
- PM-002 OpenAPI visibility drift. Disposition: FIXED. Commit: `ceb82f8fa`. Evidence: `app/routers/favicon.py` registers `include_in_schema=False`; endpoint and namespace tests assert `/favicon.ico` is absent from live OpenAPI.
- PM-003 guard shrink gap. Disposition: FIXED. Commit: `ceb82f8fa`. Evidence: `scripts/ci/check_legacy_growth_guard.py` removes favicon from `ALLOWED_LEGACY_ROUTE_FACTS`; `tests/test_legacy_growth_guard.py` rejects reintroduced legacy favicon.

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/exp-e67983c65937.json`

Status: accepted. Oracles passed in the isolated checkout:
- `python -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py::TestHealthAndMonitoringEndpoints::test_favicon_endpoint tests/test_openapi_namespace_guards.py`
- `python scripts/ci/check_legacy_growth_guard.py`

Commit attribution is present: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/54df96b0ed2b.json`
Starter: `scripts/orchestration/start_pr_lane.sh`

## Local Validation
- `python3 scripts/orchestration/check_preflight.py --mode analyze --path legacy_app.py --path app/main.py --path app/routers --path scripts/ci/check_legacy_growth_guard.py --path tests` -> pass.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py::TestHealthAndMonitoringEndpoints::test_favicon_endpoint tests/test_openapi_namespace_guards.py` -> pass.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_legacy_growth_guard.py` -> pass.
- `python3 scripts/orchestration/check_agent_consistency.py` -> pass.
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` -> pass.
- `pre-commit run --all-files` -> pass.
- Pre-push hooks on `git push` -> pass, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and docker build test.
- Review-fix validation after Sourcery comments: focused pytest bundle, legacy growth guard, `check_agent_consistency.py`, `make validate-changed`, and `pre-commit run --all-files` -> pass.

## Machine-Heavy Local Verify Deferral
Full local `make verify` was intentionally not run per the operator-approved machine-budget constraint for this narrow PR. Current-head CI plus strict merge wrapper remains the heavy signal before merge.
