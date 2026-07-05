# PR 2079 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2079

Branch: `codex/move-restaurants-registration-to-canonical-bootstrap`

## Summary

This PR moves the public restaurants route-family registration owner from
`legacy_app.py` into the canonical `app/main.py` bootstrap while preserving
runtime route availability and hidden OpenAPI behavior for
`/api/v1/restaurants*`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 3920fe8ba3974cd0f452dd6818d4c8ae5ea8b62d
Evidence: `app/main.py:244`, `app/main.py:389`, `app/routers/restaurants.py:373`, `tests/test_restaurants_registration_bootstrap.py:37`, `tests/test_restaurants_registration_bootstrap.py:150`, `tests/test_legacy_growth_guard.py:1296`, `tests/test_legacy_growth_guard.py:2151`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2079#pullrequestreview-4631260857 -> 3920fe8ba3974cd0f452dd6818d4c8ae5ea8b62d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2079#discussion_r3524853144 -> 3920fe8ba3974cd0f452dd6818d4c8ae5ea8b62d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2079#pullrequestreview-4631266221 -> 3920fe8ba3974cd0f452dd6818d4c8ae5ea8b62d

## Role-Agent Evidence

- Lane packet: `artifacts/orchestration/task_packets/511957ebc225.json`
- Pre-open role order completed: `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor`.
- Post-open role chain is in progress and must update this artifact if any actionable findings appear.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-f514bdc54ecb.json`

- Experiment id: `exp-f514bdc54ecb`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer: `956042fb4346556d77595c59e3ab52cc4c167726`
- Oracle commands passed: `python3 -m pytest -q tests/test_restaurants_registration_bootstrap.py tests/test_restaurant_moderation_bootstrap.py tests/test_legacy_growth_guard.py`, `python3 scripts/ci/check_legacy_growth_guard.py`, and `python3 -m mypy app/main.py app/routers/restaurants.py legacy_app.py`.

Infra caveat: the first zero-network local attempt recorded `status=rejected`
because this macOS development host did not provide `unshare` for the
network-disabled sandbox. The accepted `network_budget=1` artifact kept the
same local oracle commands and does not grant product runtime, provider,
client, dependency installer, or public API authority.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/511957ebc225.json`
Starter: `scripts/orchestration/start_pr_lane.sh`

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS; local environment still emits the existing `PULSEPLATE_PYTHON_INDEX_URL` shape warning.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `pytest -q tests/test_restaurants_registration_bootstrap.py tests/test_restaurants_router.py tests/test_restaurant_moderation_bootstrap.py tests/test_route_family_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py` - PASS.
- `python3 scripts/ci/check_legacy_growth_guard.py` - PASS.
- `make openapi-check` with the repo virtualenv first on `PATH` - PASS; no generated OpenAPI/client diff.
- `python3 -m mypy app/main.py app/routers/restaurants.py legacy_app.py` - PASS.
- `make validate-changed` - PASS after commit; selected `tests/test_legacy_growth_guard.py` and `tests/test_restaurants_registration_bootstrap.py`.
- `pre-commit run --all-files` - PASS before push.
- Push hook - PASS, including pre-push pytest, full-repo bandit, dependency audit, and docker build test.
- `git diff --check origin/main...HEAD` - PASS.

## Merge Readiness

Not claimed here. Requires current-head CI after the latest governance/body
commit, strict merge-readiness gate, post-open role chain completion, Codex
Security diff scan/finding discovery when available, `pulseplate-pr-review`,
bot review dispositions, and resolved review threads.
