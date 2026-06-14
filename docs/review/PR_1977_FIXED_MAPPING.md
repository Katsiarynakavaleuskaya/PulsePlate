# PR 1977 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open Sourcery review comments were fixed in code/tests before thread resolution.

## Merge-readiness Checklist
- [ ] Current-head required CI checks pass.
- [ ] Focused local validation remains current after the latest commit.
- [ ] Review-thread disposition guard passes with `--require-auth`.
- [ ] No actionable bot or human comments remain undispositioned.
- [ ] Strict merge wrapper passes after the latest review activity.
- [ ] Mandatory wait window after latest bot/review activity has elapsed.

## Fixed in Commit Mapping
Disposition: FIXED
Commit: a3528ce8a
Evidence: `app/routers/favicon.py` exports `FAVICON_ROUTE_PATH`; `app/main.py` imports and reuses it for bootstrap validation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178548 -> a3528ce8a

Disposition: FIXED
Commit: a3528ce8a
Evidence: `tests/test_app_endpoints_combined.py` asserts `not route.dependant.dependencies` for `GET /favicon.ico`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178554 -> a3528ce8a

Disposition: FIXED
Commit: a3528ce8a
Evidence: The Sourcery review-level summary duplicated the two inline favicon findings; both were fixed in `app/routers/favicon.py`, `app/main.py`, and `tests/test_app_endpoints_combined.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493518770 -> a3528ce8a

Disposition: NOT-A-BUG
Evidence: The Sourcery reviewer guide is a generated overview, not a separate requested code change after the inline Sourcery findings were fixed.
Reason: Generated summary content does not introduce an additional actionable requirement beyond the mapped Sourcery review findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#issuecomment-4702933611

Disposition: NOT-A-BUG
Evidence: The CodeRabbit walkthrough/docstring warning is advisory; the new favicon handler has a docstring and repo validation passed formatting, lint, pydocstyle/pre-commit, and focused tests.
Reason: The repo does not enforce CodeRabbit's standalone docstring coverage warning as a PR-specific blocker for this narrow route extraction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#issuecomment-4702933387

Disposition: FIXED
Commit: 20e1a3142
Evidence: `docs/review/PR_1977_FIXED_MAPPING.md` now includes an unchecked `## Merge-readiness Checklist` before the fixed mapping section.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493537527 -> 20e1a3142

Disposition: NOT-A-BUG
Evidence: The Codex review body contains no concrete file/line finding or requested change; it is an automated review notification only.
Reason: There is no actionable item to fix or defer in that review body.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493539087

## Premortem Findings
- PM-001 duplicate/legacy ownership false-green. Disposition: FIXED. Commit: ceb82f8fa. Evidence: `legacy_app.py` no longer defines `@app.get("/favicon.ico")`; `tests/test_app_endpoints_combined.py` asserts canonical `app.routers.favicon` ownership.
- PM-002 OpenAPI visibility drift. Disposition: FIXED. Commit: ceb82f8fa. Evidence: `app/routers/favicon.py` registers `include_in_schema=False`; endpoint and namespace tests assert `/favicon.ico` is absent from live OpenAPI.
- PM-003 guard shrink gap. Disposition: FIXED. Commit: ceb82f8fa. Evidence: `scripts/ci/check_legacy_growth_guard.py` removes favicon from `ALLOWED_LEGACY_ROUTE_FACTS`; `tests/test_legacy_growth_guard.py` rejects reintroduced legacy favicon.

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
- `$VENV_PYTHON -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py::TestHealthAndMonitoringEndpoints::test_favicon_endpoint tests/test_openapi_namespace_guards.py` -> pass.
- `$VENV_PYTHON scripts/ci/check_legacy_growth_guard.py` -> pass.
- `python3 scripts/orchestration/check_agent_consistency.py` -> pass.
- `VENV_PYTHON=$REPO_ROOT/.venv/bin/python DEV_PYTHON=$REPO_ROOT/.venv/bin/python make validate-changed` -> pass.
- `pre-commit run --all-files` -> pass.
- Pre-push hooks on `git push` -> pass, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and docker build test.
- Review-fix validation after Sourcery comments: focused pytest bundle, legacy growth guard, `check_agent_consistency.py`, `make validate-changed`, and `pre-commit run --all-files` -> pass.

## Machine-Heavy Local Verify Deferral
Full local `make verify` was intentionally not run per the operator-approved machine-budget constraint for this narrow PR. Current-head CI plus strict merge wrapper remains the heavy signal before merge.
