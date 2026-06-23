# PR #2013 - Fixed in Commit Mapping SoT

## Scope

Fix post-merge `main` CI after PR #2009 by cleaning stale VIP coverage tests
that still expected deleted legacy shoplist/export symbols on
`app.routers.vip`. This PR does not restore production aliases and does not
change runtime routes, auth, OpenAPI, generated clients, DB, billing,
entitlements, frontend, or iOS surfaces.

## Implementation Commits

- `e26069f83dc1090ff6454e7081c5ff4eba8e6039` - sync
  `.secrets.baseline` line numbers after test-line cleanup.
- `8184b8b84a5867d327361c21f4a598a707f8f185` - remove stale VIP coverage
  tests and patches for deleted `app.routers.vip` shoplist/export aliases,
  replace duplicate fallback coverage with a negative alias-absence guard, and
  assert the real `/api/v1/vip/shoplist/formats` contract.
- `5b490696cc4ead4d408359b90d4471d7b47602ad` - address Sourcery review by
  using set intersection for the legacy-alias absence guard and centralizing
  the VIP shoplist formats response assertion in a shared test helper.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no human review threads existed at artifact creation.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2013`.
- [x] Initial Sourcery review comments fixed and mapped.
- [ ] Later post-open bot/human review comments are fixed or dispositioned
  before merge readiness.
- [ ] Current-head CI is complete before merge readiness.
- [ ] Strict merge-readiness check runs after the final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2013#pullrequestreview-4556631754 -> 5b490696cc4ead4d408359b90d4471d7b47602ad
Disposition: FIXED
Commit: 5b490696cc4ead4d408359b90d4471d7b47602ad
Evidence: `tests/test_vip_coverage_clean.py` now checks legacy VIP shoplist alias absence with `legacy_shoplist_aliases & set(dir(vip))`; `tests/_helpers/vip_contracts.py` centralizes the static VIP shoplist formats contract; `tests/test_vip_coverage_simple.py` and `tests/test_vip_coverage_additional.py` call the helper instead of duplicating the `formats` / `locales` literals. Focused validation passed: `pytest -q tests/test_vip_coverage_clean.py tests/test_vip_coverage_simple.py tests/test_vip_coverage_additional.py`; the full stale-VIP cleanup bundle passed.

## Additional Fixed Findings

Post-merge `main` CI run
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28032859273`
failed in `test-main` shards because stale VIP coverage tests referenced
deleted `app.routers.vip.ShoplistGenerator` and `app.routers.vip.format_export`
symbols.

Disposition: FIXED

Commit: `8184b8b84a5867d327361c21f4a598a707f8f185`

Evidence:

- `tests/test_vip_coverage_clean.py` now asserts that
  `ShoplistGenerator`, `aggregate_ingredients`, `round_to_packages`, and
  `format_export` are absent from `app.routers.vip`.
- `tests/test_vip_coverage_fixed.py`,
  `tests/test_vip_coverage_comprehensive.py`, and
  `tests/test_vip_coverage_precise.py` no longer mutate `sys.modules` to
  re-import `app.routers.vip` and assert stale shoplist aliases.
- `tests/test_vip_coverage_simple.py` and
  `tests/test_vip_coverage_additional.py` now assert the live static
  `/api/v1/vip/shoplist/formats` contract.
- `tests/test_vip_coverage_boost.py`,
  `tests/test_vip_coverage_boost_fixed.py`, and
  `tests/test_vip_simple_working.py` no longer patch the removed
  `app.routers.vip.ShoplistGenerator` alias.
- `rg -n "app\\.routers\\.vip\\.(ShoplistGenerator|aggregate_ingredients|round_to_packages|format_export)|vip\\.(ShoplistGenerator|aggregate_ingredients|round_to_packages|format_export)" tests/test_vip_* tests/test_coverage_*`
  returned no matches after cleanup.

## Governance Evidence

- Worktree isolation: branch
  `codex/fix-main-vip-coverage-after-paid-tier-merge` in
  `worktrees/fix-main-vip-coverage-after-paid-tier-merge`.
- Lane start packet:
  `artifacts/orchestration/task_packets/fee0b9e24cfa.json` (local artifact).
- Role pass order completed before edits:
  `agent-coordinator -> qa-engineer-agent -> backend-engineer -> security-auditor -> bug-hunter`.
- Backend role pass confirmed route ownership:
  `app.routers.vip` owns only static `GET /api/v1/vip/shoplist/formats`;
  `app.routers.vip_shoplist` owns `/generate`, `/daily`, `/weekly`, and
  `/export`; duplicate VIP shoplist route keys were not present.
- Security role pass confirmed no auth/tier drift and no reason to restore
  deleted production aliases.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/exp-9c2ff5026aa1.json`
  (local artifact), status `accepted`, runner mode
  `oracle_only_governance_reviewer`, shared tree untouched, failure class
  `null`, mutated paths `[]`.
- Experiment Runner attribution:
  commit `8184b8b84a5867d327361c21f4a598a707f8f185` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the accepted oracle-only result shaped validation evidence.

## Local Validation Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path ...`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_vip_coverage_clean.py tests/test_vip_coverage_fixed.py tests/test_vip_coverage_comprehensive.py tests/test_vip_coverage_precise.py tests/test_vip_coverage_simple.py tests/test_vip_coverage_boost_fixed.py tests/test_vip_simple_working.py tests/test_vip_coverage_additional.py tests/test_vip_coverage_boost.py tests/test_coverage_final_push.py`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_pro_vip_route_dependency_guard.py tests/test_vip_shoplist_daily.py tests/test_vip_shoplist_weekly.py tests/test_vip_shoplist_generate_api.py tests/test_vip_shoplist_invalid_enum_422.py tests/test_vip_shoplist_router_hardening.py tests/test_vip_guard_consistency.py tests/test_pro_registration_router_coverage.py tests/edges/test_vip_auth_edges.py tests/test_repo_policy_sys_modules.py tests/test_repo_policy_guards.py`
- PASS:
  `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" make openapi-check`
- PASS:
  `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS:
  `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" make validate-changed`
  after commit; selected all changed VIP test files.
- PASS:
  `PATH="/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH" pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including pip-audit, backend
  pre-push pytest, and full-repo Bandit.
- PASS: `git diff --check && git diff --check origin/main...HEAD`
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py`

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. The operator explicitly requested narrow
validation for this hotfix because the full suite is machine-heavy without
shards. Merge readiness requires the focused local gates above, current-head CI
parity for the PR surface, post-open role review, bot/human comment
disposition, Codex Security diff scan / finding discovery when available,
`pulseplate-pr-review`, strict merge-readiness checks with auth, and the final
wait-window.
