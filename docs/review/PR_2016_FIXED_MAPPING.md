# PR #2016 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016

Branch: `codex/move-bmi-registration-to-canonical-bootstrap`

## Summary

This PR moves BMI route registration ownership from `legacy_app.py` into the
canonical `app/main.py` bootstrap path without changing public BMI behavior.
Free BMI remains always registered. BMI Pro and the deprecated legacy BMI Pro
alias remain registered only when `FEATURE_BMI_PRO_ENABLED` is truthy.

## Scope

- Add `app/routers/bmi_registration.py` as the canonical BMI route-family
  registrar.
- Register BMI routes from `app/main.py` through
  `ensure_route_family_registered(...)` and
  `route_member_contracts_from_router(...)`.
- Remove BMI router imports and BMI `include_router(...)` calls from
  `legacy_app.py`.
- Preserve compatibility exports for `FEATURE_BMI_PRO_ENABLED`, `bmi_router`,
  `bmi_pro_router`, and `bmi_pro_legacy_alias_router`.
- Tighten `check_legacy_growth_guard.py` and tests so BMI ownership cannot move
  back into `legacy_app.py`.
- Add focused tests for canonical ownership, route inventory, duplicate guards,
  Pro tier dependency, deprecated alias metadata, and OpenAPI stability.

## Out Of Scope

No BMI math/schema changes, bodyfat work, FoodDB work, AI/runtime work,
frontend/iOS change, dependency update, deprecated-endpoint removal, or root
`AGENTS.md` process-rule edit.

## Lane Start Provenance

- Base branch: `main`
- Start head: `827eee384a4fd7fa9e80b993d503b3183a6312db`
- Packet: `artifacts/orchestration/task_packets/68028055c67e.json`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/68028055c67e.json --mode runtime --implementation-owner bug-hunter --implementation-owner qa-engineer-agent --implementation-owner security-auditor --pretty`
- Pre-implementation role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed at PR open
- [x] Fixed in commit mapping initialized
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No review threads existed at PR open. Any later CodeRabbit, Sourcery, Cubic,
Codex Security, human, or role-agent actionable must be fixed or dispositioned
below before merge readiness.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016#pullrequestreview-4560935403 -> 3301be7d65a171c9cc029930ff9f73cec58a3b16
Disposition: FIXED
Commit: 3301be7d65a171c9cc029930ff9f73cec58a3b16
Evidence: `app/routers/bmi_registration.py` now reports concrete route-family mismatches, duplicate keys, unsupported route types, method-shape problems, and `include_in_schema` drift; its docstring also documents per-app first-call feature-flag caching. `tests/test_bmi_registration_router_coverage.py` verifies unexpected source-route diagnostics. Focused pytest, `make openapi-check`, `make validate-changed`, `pre-commit run --all-files`, and Phase2 gates passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016#pullrequestreview-4565385286 -> 42978e28e086aee0c007f71da44276b801ba87b6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016#discussion_r3469821502 -> 42978e28e086aee0c007f71da44276b801ba87b6
Disposition: FIXED
Commit: 42978e28e086aee0c007f71da44276b801ba87b6
Evidence: `docs/review/PR_2016_FIXED_MAPPING.md` keeps merge-readiness gate checklist items unchecked until final merge readiness while preserving completed-work evidence in prose above. `git diff --check`, `check_preflight.py`, and commit hooks passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016#issuecomment-4793153666 -> 68c1d4d6ecee59a1d01af7d00def0197df9ff4e0
Disposition: FIXED
Commit: 68c1d4d6ecee59a1d01af7d00def0197df9ff4e0
Evidence: `tests/test_bmi_registration_router_coverage.py` now covers the BMI registration guard branches Codecov reported for `app/routers/bmi_registration.py`: non-`APIRoute` members, multi-method source routes, duplicate source routes, and `include_in_schema` drift. Focused coverage proof reports `100.00%` line and branch coverage for the file; `make validate-changed`, `pre-commit run --all-files`, `git diff --check`, and commit hooks passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2016#issuecomment-4787837121 -> 5e2e125a5cd733c96b1f3715d98f2a85c853d20b
Disposition: FIXED
Commit: 5e2e125a5cd733c96b1f3715d98f2a85c853d20b
Evidence: `app/routers/bmi_registration.py` now documents the BMI registration helper functions used by the production route-family registrar. The PR body mirror also adds related-PR context and a split-justification section for the description-shape advisory. Focused pytest and selected-suite coverage proof passed after the docstring change.
Reason: The remaining CodeRabbit docstring-coverage framing is advisory for test/helper surfaces, not a repo gate. PulsePlate tests do not require per-test docstrings; adding broad test docstrings would reduce signal without improving the runtime BMI contract.

## Implementation Commits

- `ba1eabf3d` - moves BMI route registration to canonical bootstrap, preserves
  compatibility exports, removes legacy BMI ownership, tightens the legacy
  growth guard, and adds focused route/bootstrap/security tests.
- `761e2637a` - adds PR #2016 fixed-mapping governance artifact.
- `614c37f0c` - aligns PR #2016 mapping artifact with Phase2 parser contract.
- `3301be7d6` - fixes Sourcery review feedback by making BMI registration guard
  failures diagnostic and documenting first-call feature flag caching.
- `42978e28e` - keeps PR #2016 merge-readiness gate checkboxes unchecked until
  the final merge-readiness pass.
- `68c1d4d6e` - covers BMI registration guard drift branches reported by
  Codecov and proves 100% focused coverage for the canonical registrar.
- `855738ce7` - moves BMI registration coverage proof into the CI-selected
  `tests/test_main_paywall_bootstrap.py` suite so current-head `diff-coverage`
  uses the branch coverage evidence.
- `5e2e125a5` - documents BMI registration production helpers in response to
  CodeRabbit's advisory docstring-coverage warning.

## Premortem Findings

Disposition: FIXED

Finding: `PM-BMI-001` - validation could be too narrow for a route ownership
move.

Commit: `ba1eabf3d`

Evidence: focused BMI/bootstrap/security pytest bundle, route inventory proof,
`make openapi-check`, `make validate-changed`, `pre-commit run --all-files`,
and pre-push hooks passed.

Disposition: FIXED

Finding: `PM-BMI-002` - duplicate or lost BMI route guard could alter runtime
behavior.

Commit: `ba1eabf3d`

Evidence: `tests/test_bmi_registration_router_coverage.py` covers exact
enabled/disabled route inventory, duplicate/foreign route rejection, partial Pro
family rejection, and unguarded Pro route rejection.

Disposition: NOT-A-BUG

Finding: canonical app ownership assumption.

Evidence: `app/main.py` calls the canonical BMI registrar during
`ensure_canonical_app_bootstrap(...)`; direct `legacy_app.py` construction is
compatibility surface only and no longer owns BMI router registration.

Reason: This PR intentionally proves route ownership through canonical
`app.main:app`, which is the backend runtime route owner.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-fb358458ae4e.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-fb358458ae4e.json`
- Status: accepted
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer included in implementation commit `ba1eabf3d`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Oracles passed:
  - `python3 -m pytest -q tests/test_bmi_registration_router_coverage.py tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_bmi_calculate_endpoint.py tests/test_bmi_pro_api.py tests/test_bmi_pro_endpoint_errors.py tests/test_bmi_pro_missing_hip.py tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_paid_route_guards.py`
  - `make openapi-check`
  - `python3 scripts/ci/check_legacy_growth_guard.py`

Rejected Runner context:

- `artifacts/orchestration/experiments/results/exp-98bd49dad8d8.json` was
  rejected because the temporary sandbox checkout could not resolve the shared
  repo `.venv` for `make validate-changed`.
- This rejection is not used as readiness evidence.
- `make validate-changed` was rerun and passed in the real worktree, where the
  shared repo `.venv` is intentionally available.

## Post-Open Review Evidence

- PASS: post-open packet
  `artifacts/orchestration/task_packets/b9100128481b.json`.
- PASS: dispatch manifest from
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/b9100128481b.json --mode runtime --pretty`.
- PASS: mandatory post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- PASS: `qa-engineer-agent` found no current-PR QA actionables and reran
  focused route inventory, `make validate-changed`, `make openapi-check`, and
  Phase2 gates.
- PASS: `bug-hunter` found no current-PR regressions; it confirmed idempotent
  per-app BMI registration, no BMI compatibility route conflicts, and parser
  contract validity.
- PASS: `security-auditor` found no current-head security actionables on
  `b045a55a3deeaedd880d713c646cc41f83ba068e`; the Sourcery delta only adds
  diagnostic messages, a docstring, a focused test, and mapping evidence.

## Codex Security Diff Scan / Finding Discovery

- Artifact:
  `artifacts/security_lab/pr_2016_bmi_bootstrap/diff_security_scan.md`
- Scope: `origin/main...HEAD`.
- Result: no reportable findings.
- Evidence: static pattern scan found no added subprocess, `# nosec`, hardcoded
  secret assignment, `eval`, or `exec` in changed files; route exposure and tier
  guard behavior are covered by focused tests, route inventory proof, and
  pre-push Bandit.

## PulsePlate PR Review Disposition

Finding: `large-diff-risk` advisory from `pulseplate-pr-review`.

Disposition: NOT-A-BUG

Evidence: the diff is intentionally concentrated in one narrow BMI route
ownership lane, with production changes limited to canonical registration,
compatibility exports, and the legacy-growth guard. `make validate-changed`
selected the relevant new/changed Python tests and passed; focused BMI,
security/auth tier, OpenAPI, pre-commit, pre-push, Experiment Runner, and
post-open role passes also passed.

Reason: The line-count threshold is crossed by focused tests and the canonical
review artifact, not by broad unrelated production scope. No bodyfat, FoodDB,
AI, frontend/iOS, dependency, deprecated-endpoint removal, or root-process-rule
change is included.

## Local Validation

Full local `make verify` was not run under the operator-approved machine-heavy
exception. Current-head GitHub CI remains the full-suite signal.

Passed locally before the dependency-stack rebase:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_legacy_growth_guard.py`
- `git diff --check origin/main...HEAD`
- `FEATURE_BMI_PRO_ENABLED=0` route inventory proof: exactly
  `POST /api/v1/bmi/calculate` for the BMI route-family set.
- `FEATURE_BMI_PRO_ENABLED=1` route inventory proof: exactly
  `POST /api/v1/bmi/calculate`, `POST /api/v1/pro/bmi`,
  `POST /api/v1/pro/bmi/calculate`, and `POST /api/v1/bmi/pro`; Pro routes are
  guarded by `require_pro_tier`; the legacy alias remains deprecated and keeps
  migration metadata.
- `PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_bmi_registration_router_coverage.py tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_bmi_calculate_endpoint.py tests/test_bmi_pro_api.py tests/test_bmi_pro_endpoint_errors.py tests/test_bmi_pro_missing_hip.py tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_paid_route_guards.py`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" make openapi-check`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" PREPUSH_DEBUG=1 make validate-changed`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" pre-commit run --all-files`
- Pre-push hooks during `git push -u origin codex/move-bmi-registration-to-canonical-bootstrap`:
  changed-files mypy, pip-audit, backend tests, full-repo Bandit, and Docker
  build test.

After Sourcery review remediation `3301be7d6`:

- `PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_bmi_registration_router_coverage.py`
- `PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_bmi_registration_router_coverage.py tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_bmi_calculate_endpoint.py tests/test_bmi_pro_api.py tests/test_bmi_pro_endpoint_errors.py tests/test_bmi_pro_missing_hip.py tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_paid_route_guards.py`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" make openapi-check`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" PREPUSH_DEBUG=1 make validate-changed`
- `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" pre-commit run --all-files`

After dependency-stack rebase onto `220139000`:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_legacy_growth_guard.py`
- `FEATURE_BMI_PRO_ENABLED=0` canonical BMI family proof: exactly
  `POST /api/v1/bmi/calculate`; pre-existing legacy compatibility endpoints
  `/bmi`, `/api/v1/bmi`, and `/legacy/bmi-calculator` remain preserved and out
  of this PR's removal scope.
- `FEATURE_BMI_PRO_ENABLED=1` canonical BMI/BMI Pro family proof: exactly
  `POST /api/v1/bmi/calculate`, `POST /api/v1/pro/bmi`,
  `POST /api/v1/pro/bmi/calculate`, and `POST /api/v1/bmi/pro`; Pro routes are
  guarded by `require_pro_tier`; the legacy alias remains deprecated and keeps
  migration metadata.
- `PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_bmi_registration_router_coverage.py tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_bmi_calculate_endpoint.py tests/test_bmi_pro_api.py tests/test_bmi_pro_endpoint_errors.py tests/test_bmi_pro_missing_hip.py tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_paid_route_guards.py`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make openapi-check`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`

After Codecov patch-coverage remediation `68c1d4d6e`:

- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_current PYTHONPATH=. VIP_MODULE_ENABLED=true APP_ENV=test ENVIRONMENT=test FEATURE_PREMIUM_NUTRITION=true API_KEY=test_key /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage run --source=app.routers.bmi_registration -m pytest -q tests/test_bmi_registration_router_coverage.py`
- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_current /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage report -m app/routers/bmi_registration.py`
  - Result: `app/routers/bmi_registration.py` `100.00%` line and branch
    coverage.
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pre-commit run --all-files`
- `git diff --check`

After CI-selected diff-coverage remediation `855738ce7`:

- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_bmi_registration_router_coverage.py`
- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_ci_selected /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage run --source=app.routers.bmi_registration -m pytest -q tests/test_main_paywall_bootstrap.py`
- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_ci_selected /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage report -m app/routers/bmi_registration.py`
  - Result: `app/routers/bmi_registration.py` `100.00%` line and branch
    coverage from the CI-selected `tests/test_main_paywall_bootstrap.py` suite.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_preflight.py`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_agent_consistency.py`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_legacy_growth_guard.py`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make openapi-check`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run --all-files`
- `git diff --check`
- Commit hooks passed for `855738ce7`.

After CodeRabbit advisory docstring remediation `5e2e125a5`:

- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python PYTHONPATH=. /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_bmi_registration_router_coverage.py`
- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_ci_selected_after_docstrings /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage run --source=app.routers.bmi_registration -m pytest -q tests/test_main_paywall_bootstrap.py`
- `COVERAGE_FILE=/tmp/pr2016_coverage_bmi_ci_selected_after_docstrings /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m coverage report -m app/routers/bmi_registration.py`
  - Result: `app/routers/bmi_registration.py` `100.00%` line and branch
    coverage from the CI-selected `tests/test_main_paywall_bootstrap.py` suite.
- `git diff --check`
- Commit hooks passed for `5e2e125a5`.

Current-head CI passed at `ff7c6d335` before the CodeRabbit advisory docstring
commit. New current-head CI is pending at mapping update.

## Security Notes

- Free BMI calculation remains unguarded/free.
- BMI Pro canonical routes and the deprecated legacy BMI Pro alias remain behind
  `require_pro_tier` when enabled.
- Duplicate FastAPI method/path registration is guarded by the canonical route
  family helper and focused tests.
- This PR does not touch secrets, token handling, billing, deploy, migrations,
  or LLM endpoints.

## Merge Readiness

Not merge-ready yet.

Required before merge:

- [ ] Current-head GitHub CI passes for the pushed head.
- [ ] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan/finding discovery run.
- [ ] `pulseplate-pr-review` run; advisory large-diff-risk dispositioned.
- [ ] CodeRabbit, Sourcery, Cubic, and human review comments inspected and all
  actionables fixed or dispositioned.
- [ ] PR body mirrors this fixed-mapping artifact.
- [ ] Strict merge-readiness checks pass with the documented machine-heavy
  exception.
