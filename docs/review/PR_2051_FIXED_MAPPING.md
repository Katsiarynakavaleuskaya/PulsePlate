# PR #2051 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2051

Branch: `codex/starlette-httpx2-testclient-compat`

## Summary

This PR adds a narrow Starlette/httpx2 TestClient backend gate. It removes the
confirmed Starlette TestClient deprecation warning on the production
`app.main.app` test path while keeping `httpx2` out of runtime, Docker runtime,
and CI-lite dependency profiles.

## Scope

- Add `httpx2>=2.3.0,<2.4.0` to test/dev dependency inputs and regenerate the
  test, dev, and full lock surfaces.
- Add a production app canary for `TestClient(app.main.app)` covering `/health`
  and `/openapi.json` without `/ready`.
- Add an AST guard for deprecated `httpx.Client(app=...)` and
  `httpx.AsyncClient(app=...)`, including alias and imported-name forms.
- Update dependency docs so local refresh guidance points to `make venv-sync`
  and the locked installer, not canonical direct `pip-sync`.
- Route dependency/TestClient surfaces through changed-test and CI risk
  selection so the guard cannot silently fall out of validation.

## Out Of Scope

No legacy route extraction, `legacy_app.py` deletion, runtime dependency
expansion, Docker runtime dependency change, CI-lite dependency expansion,
FastAPI/Pydantic/Starlette broad bump, Ruff bump, SQLite change, Docker change,
frontend CI repair, or private-proxy remediation is included.

## Implementation Commits

- `e32f10824` - add the `httpx2` TestClient backend dependency, canary, AST
  guard, dependency-surface checks, and dependency-doc updates.
- `b0fa7c53` - enforce TestClient/dependency-surface routing in changed-test
  and CI risk selection after post-open QA review.
- `8c5e550c` - fix post-open CodeRabbit and bug-hunter findings by handling
  rebound httpx symbols, literal `**{"app": ...}` calls, CLI output tests, and
  dependency-doc CI risk routing.
- `9d0dc0fb` - satisfy the pre-push mypy hook for the AST visitor default
  argument loops without changing guard behavior.
- `08e5e7d6` - keep the httpx2-backed production canary out of the ci-lite
  pre-commit backend hook while preserving it in `make validate-changed`,
  pre-push, and focused pytest paths.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/e75b90b7f074.json

Starter: scripts/orchestration/start_pr_lane.sh

Pre-implementation role order executed explicitly before edits:
`agent-coordinator -> architecture-specialist -> dev-operator ->
security-auditor -> qa-engineer-agent -> bug-hunter ->
cursor-specialist-agent -> web-research-agent`.

## Premortem Evidence

`pulseplate-premortem-risk-review` found two P1 issues before the first commit:
generated `pip==26.1.2` stanzas in dev/full-lock outputs, and an AST guard that
was not yet enforced against the actual repo. Both were fixed before commit:
`requirements-dev.txt` and `requirements-lock.txt` no longer contain `pip==`
pins, and `tests/test_httpx_testclient_compat_guard.py` now scans repo paths
with explicit legacy/generated/local exclusion coverage.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-cd6dd07b670d.json

Artifact: artifacts/orchestration/experiments/results/exp-33973e465f83.json

Status: accepted for both oracle-only governance runs.

Contribution: `oracle_review`; both implementation commits include
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

Note: local macOS runner used `network_budget=1` because network-disabled
sandbox mode requires Linux `unshare`; oracle commands were local validation
commands and the shared tree stayed untouched.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed and its actionable routing
  findings were fixed in `b0fa7c53`.
- [x] Post-open `bug-hunter` pass completed and its actionable guard/routing
  findings were fixed in `8c5e550c`.
- [x] Post-open `security-auditor` pass completed with no actionable security,
  supply-chain, or governance findings beyond the already-known size gate.
- [x] `pulseplate-pr-review` completed; its only finding was the advisory PR
  size/scope governance risk already represented by `pr_scope_guard`.

## Fixed in Commit Mapping

Disposition: FIXED

Commit: 8c5e550c434ac2fe50362a5fad40c47e54838564

Evidence: `scripts/ci/check_httpx_testclient_compat.py` drops stale httpx bindings on rebinding, scopes shadowing, and detects literal `**{"app": ...}` unpacking; `tests/test_httpx_testclient_compat_guard.py` covers rebinding, scoped rebinding, literal unpacking, and CLI output; `scripts/ci/ci_risk_profile.py` and `tests/test_ci_risk_profile.py` route dependency docs through backend/security CI risk selection.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2051#discussion_r3498464120 -> 8c5e550c434ac2fe50362a5fad40c47e54838564
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2051#pullrequestreview-4600021572 -> 8c5e550c434ac2fe50362a5fad40c47e54838564

## Post-Open Review Evidence

- PASS: `qa-engineer-agent` post-open pass found guard-routing gaps; fixed in
  `b0fa7c53` with changed-test, CI-risk, repo-scan, and optional-surface
  coverage.
- PASS: `bug-hunter` post-open pass found dependency-doc CI risk routing and
  AST rebinding/unpack edges; fixed in `8c5e550c`.
- PASS: pre-push mypy failure in `scripts/ci/check_httpx_testclient_compat.py`
  was fixed in `9d0dc0fb`.
- PASS: the first Codex Security diff scan for this PR completed on head
  `654c158dfbcdeecff2061cb87cbc82155edf652a` with zero findings:
  scan `d26ee096-a224-4d5d-9d7b-f965ed097fb8`, workspace
  `4188db28-b3cf-4698-b9db-56b90d5b007e`.
- NOTE: no second Codex Security scan is run after the ci-lite pre-commit fix
  commit `08e5e7d6`; the operator explicitly prohibited repeat scans. This
  artifact therefore does not claim a repeated current-head Codex Security
  parity scan for `08e5e7d6`.
- FIXED: current-head CI `lint` on `654c158d` failed because the ci-lite
  pre-commit backend hook selected
  `tests/compat/test_starlette_httpx2_testclient_compat.py`, where the
  expected backend was `httpx2` but ci-lite intentionally installed only
  `httpx`. Commit `08e5e7d6` keeps that canary on dev/test validation paths and
  excludes it only from `PRE_COMMIT=1` ci-lite selection.
- Current-head GitHub CI must rerun after `08e5e7d6`; no merge-readiness claim
  is made here.

## External Review / Thread Status

- CodeRabbit status was `SUCCESS`; its generated summary/walkthrough contained
  no actionable code-change request at the time of this artifact.
- Sourcery status was `SUCCESS`; its generated review content contained no
  actionable code-change request at the time of this artifact.
- Cubic status was advisory/neutral at PR open; no actionable thread was mapped
  at the time of this artifact.

## Scope Governance Evidence

- Operator approval: approved for completing and merging this already validated
  Starlette/httpx2 dependency-guard PR rather than splitting the final
  three-file privileged-lane overage.
- Privileged scope exception: approved because the extra counted files are
  tightly coupled dependency docs, guard tests, and mandatory fixed-mapping
  evidence for one narrow backend TestClient compatibility lane.
- Trusted labels applied to PR #2051:
  `scope/operator-approved`, `scope/privileged-approved`.
- Local reproduction before approval failed with
  `PR scope governance: FAIL (privileged CI/security/workflow PR has 18 files;
  hard cap is 15 without operator-approved exception)`.

## Validation Evidence

- PASS: red proof before dependency install reproduced
  `StarletteDeprecationWarning: Using httpx with starlette.testclient is
  deprecated; install httpx2 instead.`
- PASS: red proof before dependency install showed the new canary using backend
  module `httpx` instead of `httpx2`.
- PASS: `make venv-sync`
- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_httpx_testclient_compat.py`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `python3 scripts/ci/check_private_python_proxy_health.py --requirements-file requirements-dev.txt --requirements-file requirements-test.txt --project httpx2 --python-version 3.11 --python-version 3.12 --python-version 3.13`
- PASS: `.venv/bin/python -m pytest -q tests/compat/test_starlette_httpx2_testclient_compat.py tests/test_httpx_testclient_compat_guard.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py -k "httpx or testclient or dependency_profile"`
- PASS: `.venv/bin/python -m pytest -q tests/test_python_dependency_surfaces.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py -k "pip or unsafe or lock"`
- PASS: `.venv/bin/python -m pip_audit -r requirements-test.txt --no-deps --disable-pip`
- PASS: `.venv/bin/python -m pip_audit -r requirements-dev.txt --no-deps --disable-pip`
- PASS: focused post-open QA tests for TestClient guard routing, dependency
  routing, pre-commit changed-test selection, and supply-chain assertions.
- PASS after `08e5e7d6`: `.venv/bin/python -m pytest -q tests/test_pre_commit_hook_python_resolver.py -k "python_dependency_surface or httpx2_canary"`
- PASS after `08e5e7d6`: `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" PRE_COMMIT=1 PREPUSH_DEBUG=1 bash scripts/run-backend-tests-pre-commit.sh`
- PASS after `08e5e7d6`: `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" BRANCH_DIFF_MODE=1 PREPUSH_DEBUG=1 bash scripts/run-backend-tests-pre-commit.sh`
- PASS after scope approval: `python3 scripts/ci/check_pr_size_governance.py --base-sha "$(git merge-base origin/main HEAD)" --head-sha "$(git rev-parse HEAD)" --event-path <live-pr-event-json>`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `git diff --check`
- PASS: pre-push hooks during branch pushes, including changed-file mypy,
  pip-audit, backend pre-push tests, full-repo Bandit, and Docker build test.

Not run locally:

- Full `make verify`, per repo local machine budget rule.

## Current Review-State Notes

This artifact records current mapping and validation evidence for PR #2051. If
new review threads or actionable bot comments appear, this file must be updated
with FIXED, NOT-A-BUG, or DEFERRED disposition evidence before thread
resolution or merge-readiness claims.
