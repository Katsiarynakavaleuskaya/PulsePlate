# PR #2033 - Fixed in Commit Mapping SoT

## Scope

Fix the current `main` CI authz contract assertion after PR #2029 moved hidden
test-route registration into canonical bootstrap. This PR classifies only the
two hidden mutating `/api/v1/test` POST routes that the current sensitive-route
selector reports.

Out of scope: PR-3 auth/tier/BOLA expansion, public API/OpenAPI/client/runtime
route changes, `GET /api/v1/test/health`, product behavior, and the separate
operator-confirmed Python 3.13 `main` segfault / FastAPI route-compat stability
blocker.

## Implementation Commits

- `a149ff7e1` - classify `POST /api/v1/test/rate-limit` and
  `POST /api/v1/test/echo` as non-production guarded hidden test-route authz
  contracts; add a static hook-safe regression target; keep pre-commit from
  collecting the authz helper module directly; avoid lazy `app.main` bootstrap
  from `reset_environment` when only the `app` package exists in `sys.modules`.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/fe767c3189a3.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Worktree: `worktrees/main-ci-authz-test-route-contracts`
- Branch: `codex/fix-main-test-route-authz-contracts`

## Role / Premortem Evidence

- Bootstrap dispatch order completed before PR open:
  `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor`.
- Coordinator pass: scope locked to authz contract/test-governance alignment;
  local focused pytest blocker recorded as pre-existing route-family bootstrap
  compatibility issue.
- Backend pass: confirmed the two classified routes match `app/routers/test.py`
  `POST` hidden test routes and router-level `_ensure_non_production`.
- Architecture pass: confirmed no runtime/bootstrap/product-truth boundary
  change and no reason to classify `GET /api/v1/test/health`.
- Security pass: confirmed the classification does not weaken production auth
  because the routes remain hidden and non-production guarded.
- Premortem decision: `proceed with changes`.
  - Most likely failure: this narrow PR is mistaken for the broader
    segfault/FastAPI route-compat stabilization lane.
  - Most dangerous failure: merge readiness is claimed while current-head CI or
    the separate `main` segfault blocker remains unresolved.
  - Revision applied: PR body and this artifact explicitly mark segfault
    diagnostics and PR-3 auth/BOLA as out of scope, and do not claim readiness.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/main-ci-authz-contract-oracle-packet.json`
- Artifact:
  `artifacts/orchestration/experiments/results/main-ci-authz-contract-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- Source diff paths:
  - `conftest.py`
  - `scripts/run-backend-tests-pre-commit.sh`
  - `tests/security/_api_authz_contracts.py`
  - `tests/security/test_api_authz_contract_static.py`
  - `tests/test_pre_commit_hook_python_resolver.py`
- Contribution kind: `oracle_review`; implementation commit `a149ff7e1`
  includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Initial PR open: no human review threads existed before PR creation.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2033`.
- [ ] Post-open role reviews, bot comments, and security findings are fixed or
  dispositioned before merge readiness.
- [ ] Current-head CI is complete and inspected before merge readiness.
- [ ] Strict merge-readiness check runs after the final review/check cycle.

## Fixed in Commit Mapping

- Initial `main` CI failure in run
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28296225948`
  -> `a149ff7e1`

Disposition: FIXED

Commit: `a149ff7e1`

Evidence:

- `tests/security/_api_authz_contracts.py` adds
  `AuthClass.NON_PRODUCTION_TEST_GUARD`.
- `tests/security/_api_authz_contracts.py` classifies
  `POST /api/v1/test/rate-limit` and `POST /api/v1/test/echo` with
  `MinimumTier.NONE`, `PrincipalSource.INTERNAL_OPTIONAL`,
  `OwnershipPolicy.INTERNAL_OPTIONAL`, and `ApiExposure.HIDDEN_RUNTIME`.
- `tests/security/_api_authz_contracts.py` maps
  `AuthClass.NON_PRODUCTION_TEST_GUARD` to
  `app.routers.test._ensure_non_production`.
- `tests/security/test_api_authz_contract_static.py` covers the hidden POST
  contract entries and explicitly keeps `GET /api/v1/test/health` out of the
  contract pack.
- `scripts/run-backend-tests-pre-commit.sh` maps the authz helper module to the
  static contract test instead of collecting the helper directly.
- `conftest.py` avoids `hasattr(app, "app")` so helper/static tests do not
  accidentally trigger canonical app bootstrap through `app.__getattr__`.

## Local Validation Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --path conftest.py --path scripts/run-backend-tests-pre-commit.sh --path tests/security/_api_authz_contracts.py --path tests/security/test_api_authz_contract_static.py --path tests/test_pre_commit_hook_python_resolver.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/security/test_api_authz_contract_static.py tests/test_pre_commit_hook_python_resolver.py::test_backend_hook_maps_authz_contract_helper_to_static_contract_test`
- BLOCKED locally, not counted as fix evidence:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/security/test_api_auth_tier_contract_pack.py`
  fails in app fixture setup with
  `RuntimeError: VIP router does not define the expected route family` at
  `app/bootstrap/route_family.py:98` via
  `app/routers/vip_registration.py:133`. This is the local FastAPI
  `_IncludedRouter`/route-family compatibility blocker, not the authz contract
  assertion fixed here.
- PASS: Experiment Runner oracle-only result
  `artifacts/orchestration/experiments/results/main-ci-authz-contract-oracle-result.json`
  accepted with `mutated_paths=[]` and `shared_tree_untouched=true`.
- PASS: `pre-commit run --all-files`
- PASS:
  `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
  selected 22 tests in `tests/security/test_api_authz_contract_static.py` and
  `tests/test_pre_commit_hook_python_resolver.py`.
- PASS during push: pre-push backend tests, full-repo Bandit, and docker build
  test.
- DEFERRED: full `make verify` under the operator-approved machine-heavy
  exception. Heavy parity is GitHub current-head CI after PR open.

## Merge Readiness

- [x] PR opened non-draft.
- [x] PR-numbered fixed mapping artifact exists.
- [ ] Current-head CI complete and inspected.
- [ ] Required checks pass.
- [ ] CodeRabbit, Sourcery, Cubic, post-open role reviews, and Codex Security
  actionables are fixed or dispositioned.
- [ ] Separate operator-confirmed `main` segfault/stability blocker is not
  conflated with this authz-contract fix.
- [ ] Strict merge-readiness wrapper passes after final review/check cycle.
