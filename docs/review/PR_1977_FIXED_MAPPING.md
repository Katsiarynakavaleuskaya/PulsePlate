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
Commit: 7e8ff38f3
Evidence: Current-head tree proof includes `app/routers/favicon.py` exporting `FAVICON_ROUTE_PATH` and `app/main.py` importing and reusing it for bootstrap validation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178548 -> 7e8ff38f3

Disposition: FIXED
Commit: 7e8ff38f3
Evidence: Current-head tree proof includes `tests/test_app_endpoints_combined.py` asserting `not route.dependant.dependencies` for `GET /favicon.ico`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410178554 -> 7e8ff38f3

Disposition: FIXED
Commit: 7e8ff38f3
Evidence: The Sourcery review-level summary duplicated the two inline favicon findings; current-head tree proof includes the fixes in `app/routers/favicon.py`, `app/main.py`, and `tests/test_app_endpoints_combined.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493518770 -> 7e8ff38f3

Disposition: NOT-A-BUG
Evidence: The Sourcery reviewer guide is a generated overview, not a separate requested code change after the inline Sourcery findings were fixed.
Reason: Generated summary content does not introduce an additional actionable requirement beyond the mapped Sourcery review findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#issuecomment-4702933611

Disposition: NOT-A-BUG
Evidence: The CodeRabbit walkthrough/docstring warning is advisory; the new favicon handler has a docstring and repo validation passed formatting, lint, pydocstyle/pre-commit, and focused tests.
Reason: The repo does not enforce CodeRabbit's standalone docstring coverage warning as a PR-specific blocker for this narrow route extraction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#issuecomment-4702933387

Disposition: FIXED
Commit: 7e8ff38f3
Evidence: Current-head tree proof includes an unchecked `## Merge-readiness Checklist` before the fixed mapping section in `docs/review/PR_1977_FIXED_MAPPING.md`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493537527 -> 7e8ff38f3

Disposition: NOT-A-BUG
Evidence: The Codex review body contains no concrete file/line finding or requested change; it is an automated review notification only.
Reason: There is no actionable item to fix or defer in that review body.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493539087

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor a3528ce8a HEAD` exits 0 locally, and GitHub PR commit history includes `a3528ce8a`.
Reason: The review comment used stale reviewed-head evidence. The mapped Sourcery fix commit is reachable from current PR head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410201789

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor a3528ce8a HEAD` and `git merge-base --is-ancestor 20e1a3142 HEAD` both exit 0 locally, and GitHub PR commit history includes both commits.
Reason: The review comment used stale reviewed-head evidence. The mapped Sourcery and CodeRabbit governance commits are reachable from current PR head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410225930

Disposition: NOT-A-BUG
Evidence: The later Codex review body is an automated summary wrapper for the same inline reachability comment already dispositioned above; live GraphQL reports `unresolved_count 0`.
Reason: No separate file/line change is requested beyond the resolved reachability thread.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#pullrequestreview-4493565187

Disposition: FIXED
Commit: 8d5062696
Evidence: `docs/review/PR_1977_FIXED_MAPPING.md` remaps prior FIXED proof entries to reachable current-head tree proof commit `7e8ff38f3`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1977#discussion_r3410276917 -> 8d5062696

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` dry-run report `/tmp/pulseplate_pr_1977_review_report.md` reported only an advisory diff-size planning note; this PR is intentionally narrow and test-heavy, with focused pytest, legacy guard, agent consistency, `make validate-changed`, `pre-commit run --all-files`, pre-push hooks, post-open QA/bug/security passes, and Codex Security no-findings scan all completed.
Reason: The changed-line count is not a functional/security defect and does not require splitting this narrow extraction.

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

## Post-open Review Evidence
- `qa-engineer-agent`: no blocking findings; non-blocking `app/static/openapi.json` note classified out-of-scope because live `app.main.app.openapi()` and generated frontend OpenAPI are contract truth for this PR.
- `bug-hunter`: runtime findings none; governance thread blocker fixed by NOT-A-BUG dispositions and thread resolution.
- `security-auditor`: no actionable findings on current head.
- Codex Security diff scan: no findings. Report: `/tmp/codex-security-scans/extract-favicon-route-from-legacy/5f0eda7bc_20260614T204840Z/report.md`.
- `pulseplate-pr-review`: advisory large-diff planning note only; dispositioned NOT-A-BUG above.

## Local Validation
- `python3 scripts/orchestration/check_preflight.py --mode analyze --path legacy_app.py --path app/main.py --path app/routers --path scripts/ci/check_legacy_growth_guard.py --path tests` -> pass.
- `$VENV_PYTHON -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py::TestHealthAndMonitoringEndpoints::test_favicon_endpoint tests/test_openapi_namespace_guards.py` -> pass.
- `$VENV_PYTHON scripts/ci/check_legacy_growth_guard.py` -> pass.
- `python3 scripts/orchestration/check_agent_consistency.py` -> pass.
- `VENV_PYTHON=$REPO_ROOT/.venv/bin/python DEV_PYTHON=$REPO_ROOT/.venv/bin/python make validate-changed` -> pass.
- `pre-commit run --all-files` -> pass.
- Pre-push hooks on `git push` -> pass, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and docker build test.
- Review-fix validation after Sourcery comments: focused pytest bundle, legacy growth guard, `check_agent_consistency.py`, `make validate-changed`, and `pre-commit run --all-files` -> pass.
- Final governance validation after reachability dispositions: `check_legacy_growth_guard.py`, `check_agent_consistency.py`, Phase 2 body parser, strict disposition guard, `make validate-changed`, `pre-commit run --all-files`, and pre-push hooks -> pass.

## Machine-Heavy Local Verify Deferral
Full local `make verify` was intentionally not run per the operator-approved machine-budget constraint for this narrow PR. Current-head CI plus strict merge wrapper remains the heavy signal before merge.
