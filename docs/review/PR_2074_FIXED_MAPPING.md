# PR 2074 - Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

- Commit: `24aaf8f71b2d01939a9e1b2b2057e38e878045df`
- Evidence: `app/main.py` owns users CRUD registration through
  `_include_users_router_if_needed(...)` and
  `ensure_route_family_registered(...)`.
- Evidence: `legacy_app.py` no longer imports or includes `users_router`.
- Evidence: `app/routers/users.py` defines hidden source `USERS_ROUTE_SPECS`
  and keeps `_require_users_api_key`.
- Evidence: `scripts/ci/check_legacy_growth_guard.py` rejects users
  registration/import reintroduction.
- Tests: `tests/test_users_registration_bootstrap.py`,
  `tests/test_legacy_growth_guard.py`, `tests/test_openapi_namespace_guards.py`,
  `tests/test_users_api.py`, `tests/test_users_router.py`,
  `tests/test_users_router_retry_logic.py`,
  `tests/security/test_api_auth_tier_contract_pack.py`, and
  `tests/security/test_api_authz_contract_static.py`.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-d18b2b538b82.json`

Summary: accepted oracle-only governance review. The runner applied the source
diff in an isolated checkout, kept `shared_tree_untouched=true`, and passed:
- `python3 -m pytest -q tests/test_users_registration_bootstrap.py tests/test_openapi_namespace_guards.py tests/test_users_api.py tests/test_users_router.py tests/test_users_router_retry_logic.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py tests/test_legacy_growth_guard.py tests/test_route_family_bootstrap.py`
- `python3 scripts/ci/check_legacy_growth_guard.py --repo-root .`

The implementation commit includes:
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

Starter: `scripts/orchestration/start_pr_lane.sh`

Packet: `artifacts/orchestration/task_packets/50f8dc5bd549.json`

Branch: `codex/move-users-registration-to-canonical-bootstrap`

## Validation Evidence

- PASS: `.venv/bin/python -m pytest -q tests/test_users_registration_bootstrap.py tests/test_legacy_growth_guard.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_route_family_bootstrap.py tests/test_openapi_namespace_guards.py tests/test_users_api.py tests/test_users_router.py tests/test_users_router_retry_logic.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`
- PASS: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py --repo-root .`
- PASS: explicit route probe confirmed four users routes exactly once,
  `include_in_schema=False`, and no `/api/v1/users*` in public OpenAPI.
- PASS: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/orchestration/check_preflight.py`
  with warning only for noncanonical local `PULSEPLATE_PYTHON_INDEX_URL`.
- PASS: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/orchestration/check_agent_consistency.py`
- PASS: `DEV_PYTHON=.venv/bin/python make openapi-check`
- PASS: `.venv/bin/pre-commit run --all-files`
- PASS: `make validate-changed`
- PASS during push: pre-push hooks including changed-file mypy, pip-audit,
  backend tests, full Bandit, and Docker build test.

## Merge Readiness

Not merge-ready yet. Current-head GitHub CI, post-open
`qa-engineer-agent -> bug-hunter -> security-auditor`, Codex Security diff scan
/ finding discovery, `pulseplate-pr-review`, bot review actionables, review
threads, and strict merge-readiness checks remain pending.
