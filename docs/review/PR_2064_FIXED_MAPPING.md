# PR #2064 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2064

Branch: `codex/move-nutrition-state-registration-to-canonical-bootstrap`

## Summary

This PR moves the bounded nutrition/adherence state route-family registration
from `legacy_app.py` into canonical `app/main.py` bootstrap.

## Scope

- `bayes_adherence.router`
- `nutrition_log.router`
- `legacy_nutrition_alias.router`
- Canonical `ensure_route_family_registered(...)` registration
- Legacy growth guard shrinkage and reintroduction tests
- Backend routing map and pre-open premortem documentation

## Out Of Scope

No shopping, FoodDB/catalog, AI/RAG, middleware/lifespan, frontend/iOS/macOS,
DB/model/migration, adherence math, nutrition response-schema, or broad
auth/tier/BOLA refactor work is included.

## Implementation Commits

- `402c105a6` - refactor nutrition state route registration into canonical
  bootstrap and add route-family/legacy-guard/premortem coverage.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/move-nutrition-state-registration-to-canonical-bootstrap`
- Packet: `artifacts/orchestration/task_packets/194bff367860.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Operator explicitly allowed implementation to begin while current-head
  `main` CI run `28586396946` still had two `test-main` jobs in progress.
  Merge-readiness still requires current-head PR CI evidence.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2064`.
- [x] Initial PR open: no GitHub review threads were resolved before mapping.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED

Commit: `402c105a6`

Evidence:
- `app/main.py` registers the five nutrition/adherence state route members via
  `ensure_route_family_registered(...)`.
- `legacy_app.py` removes the three target soft-import include blocks.
- `scripts/ci/check_legacy_growth_guard.py` removes the target allowlist facts.
- `tests/test_nutrition_state_registration_bootstrap.py` adds exact
  route-family registration, dependency, visibility, and fail-closed coverage.
- `tests/test_legacy_growth_guard.py` rejects direct, aliased,
  module-qualified, dynamic, destructured, and walrus reintroductions.
- `tests/test_nutrition_daily.py` proves legacy alias metric recording and
  delegation to `get_daily_nutrition(...)`.

## Premortem Closure

Artifact: `docs/review/PR_NUTRITION_STATE_BOOTSTRAP_PREMORTEM.md`

Disposition: FIXED

Commit: `402c105a6`

Evidence:
- Split ownership risk closed by removing legacy includes/imports and shrinking
  the legacy-growth allowlist.
- Partial/duplicate runtime risk closed by atomic route-family registration and
  isolated FastAPI tests.
- Auth/BOLA/API5 risk closed by required dependency contracts, source
  router-level dependency tests, and existing auth/BOLA packs.
- Alias observability/delegation risk closed by explicit metric + delegation
  tests.
- OpenAPI drift risk closed by OpenAPI zero-diff evidence.
- Import-soft partial-runtime risk closed by canonical fail-closed bootstrap.

## Experiment Runner Evidence

Packet: `artifacts/orchestration/experiments/exp-70808f0c6402.json`

Artifact: `artifacts/orchestration/experiments/results/exp-70808f0c6402.json`

Status: accepted oracle-only reviewer result.

Co-author trailer: required and present in commit `402c105a6`.

Note: Earlier packet `exp-07196d53ec39` rejected as local infra before oracle
execution because the network-disabled sandbox required `unshare` on PATH. The
accepted packet used `network_budget=1` and ran the same immutable oracles.

## Validation Evidence

Passed:
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_nutrition_state_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_route_family_bootstrap.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_bayes_adherence_api.py tests/test_nutrition_log_api.py tests/test_nutrition_log_idempotency.py tests/test_nutrition_daily.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_paid_route_guards.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" scripts/ci/check_legacy_growth_guard.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" scripts/orchestration/check_preflight.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" scripts/orchestration/check_agent_consistency.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; PATH="$(dirname "$VENV_PYTHON"):$PATH" make openapi-check`
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- `make validate-changed`
- `pre-commit run --all-files`
- Pre-push hooks during `git push`: mypy, pip-audit, backend tests,
  full-repo bandit, and docker build test.

Notes:
- Planned `tests/test_nutrition_log_api_diff_coverage.py` does not exist on
  current `main`; `tests/test_nutrition_log_idempotency.py` was used as the
  repo-actual behavior/idempotency suite.
- Plain `make openapi-check` first failed because Make resolved host `python3`
  without `dotenv`; rerunning with the repo venv first on `PATH` passed.
- `make validate-changed` passed but selected no branch-scoped tests, so the
  focused pytest bundles above are the primary Python evidence.

## Post-Open Review Evidence

Role: `qa-engineer-agent`

Disposition: FIXED

Commit: `f3f187fa7`

Evidence: Post-open QA found the Phase 2/fixed-mapping gate failed because the
mapping artifact omitted parser-required checkbox labels and used prose instead
of the canonical `- No actionable review comments` line. This artifact now
uses the exact required checklist labels and canonical no-actionable line.

Disposition: NOT-A-BUG

Evidence: Post-open QA found no actionable code-level QA defects in the route
migration. The focused route-family/bootstrap tests, nutrition/adherence
behavior tests, auth/tier+BOLA packs, and legacy growth guard passed.

Role: `bug-hunter`

Disposition: FIXED

Commit: `89f85c1a3`

Evidence: Post-open bug-hunter found local absolute user paths in this mapping
artifact's validation evidence. Commit `89f85c1a3` rewrites those commands to
repo-relative `VENV_PYTHON` / Make / pre-commit forms. Validation:
`pytest -q tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`
and `scripts/ci/check_pr_body_phase2_gates.py` both pass after the fix.

Disposition: NOT-A-BUG

Evidence: Post-open bug-hunter found no additional actionable bugs in the
current HEAD diff for duplicate/partial registration, startup/import behavior,
auth/subject ownership, idempotency, legacy alias metric/delegation, or OpenAPI
visibility.
