# PR #2066 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2066

Branch: `codex/move-shopping-list-registration-to-canonical-bootstrap`

## Scope

PR #2066 moves only the paid shopping-list route registration family from
`legacy_app.py` to canonical `app/main.py` bootstrap.

In scope:

- `POST /api/v1/pro/meal/shopping-list`
- `GET /api/v1/pro/shoplist/day`
- Source route specs for the two source routers
- `ensure_route_family_registered(...)` registration through one `Shopping list`
  route family
- Legacy growth guard allowlist shrinkage and reintroduction tests
- Backend routing map ownership update

Out of scope:

- `shoplist_export`, VIP shoplist, FoodDB/catalog, FitChef algorithms/runtime,
  `weekly_plan_id` DB support, OpenAPI/client generated artifacts, frontend,
  iOS, macOS, deploy, and AI runtime.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/e9cd2b93e4e2.json`
- Post-open packet: `artifacts/orchestration/task_packets/6191c7a0e812.json`
- Branch base: `origin/main` at `0e5b8c62e4dc2e8286b393d5d0ce15409a87b2a6`
- Branch: `codex/move-shopping-list-registration-to-canonical-bootstrap`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2066`.
- [x] Initial PR open: no GitHub review threads were resolved before mapping.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit actionable review comments checked and dispositioned.
- [ ] Sourcery actionable review comments checked and dispositioned.
- [ ] Cubic actionable review comments checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED

Commit: `ac0338460`

Evidence:

- `app/main.py` imports the two shopping source routers and route specs, builds
  `_shopping_list_route_members()`, and registers both endpoints through
  `_include_shopping_list_routers_if_needed(...)`.
- `app/routers/shopping_list_pro.py` defines
  `SHOPPING_LIST_PRO_ROUTE_SPECS` for
  `POST /api/v1/pro/meal/shopping-list`.
- `app/routers/shoplist_day.py` defines `SHOPLIST_DAY_ROUTE_SPECS` for
  `GET /api/v1/pro/shoplist/day`.
- `legacy_app.py` no longer imports or includes `shopping_list_pro_router` or
  `shoplist_day_router`.
- `scripts/ci/check_legacy_growth_guard.py` removes the two shopping-list
  registration allowlist facts and their router-import allowlist facts.
- `tests/test_shopping_list_registration_bootstrap.py` covers empty-app and
  live-app registration, idempotency, partial registration, duplicate
  method/path, foreign handler, wrong method, OpenAPI visibility drift, and
  missing `require_pro_tier` dependency failures.
- `tests/test_legacy_growth_guard.py` rejects direct, aliased,
  module-qualified, dynamic import, destructuring, and walrus-style
  shopping-list router reintroduction.

## Premortem Findings

- Duplicate or partial registration - FIXED by removing both legacy
  imports/includes, registering the pair as one atomic `Shopping list` family,
  and adding idempotency, partial, duplicate, wrong-method, foreign-handler, and
  live bootstrapped-app tests.
- Paid-route authorization drift - FIXED by
  `RouteMemberContract.required_dependencies=(require_pro_tier,)` and tests
  that inspect both decorator-level and endpoint-parameter dependency forms with
  `route_has_dependency_call(...)`.
- OpenAPI/iOS drift - FIXED by source route specs and tests asserting exact
  path, method, and `include_in_schema` visibility plus OpenAPI determinism.
- Legacy seam re-growth - FIXED by shrinking the legacy growth guard allowlist
  and adding negative tests for direct, aliased, module-qualified, dynamic,
  destructuring, and walrus reintroduction.
- Scope creep into product behavior - FIXED by keeping the runtime diff to
  registration/constants only; no FitChef, DB, schema, generated client,
  frontend, iOS, deploy, or AI runtime files changed.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-e478f895d5a7.json`
- Artifact:
  `artifacts/orchestration/experiments/results/exp-e478f895d5a7.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff paths:
  - `app/main.py`
  - `app/routers/shoplist_day.py`
  - `app/routers/shopping_list_pro.py`
  - `docs/architecture/backend_routing_map.md`
  - `legacy_app.py`
  - `scripts/ci/check_legacy_growth_guard.py`
  - `tests/test_legacy_growth_guard.py`
  - `tests/test_shopping_list_registration_bootstrap.py`
- Oracle command: focused route-family, legacy-growth, authz, and OpenAPI
  pytest bundle.
- Shared tree untouched: true
- Co-author required: true and present in commit `ac0338460`.
- Note: earlier packet `exp-dd7f551071bc` rejected as local infra before oracle
  execution because the network-disabled sandbox required `unshare` on PATH.
  The accepted packet used `network_budget=1` and ran the same oracle.

## Post-Open Role Findings

### QA Engineer Agent

Disposition: NOT-A-BUG

Evidence: Post-open QA found no blocking QA findings in the route-registration
diff. It verified canonical registration, legacy import/include removal, exact
route specs, executable duplicate/partial/auth/OpenAPI tests, legacy re-growth
tests, and bounded scope.

### Bug Hunter

Disposition: NOT-A-BUG

Evidence: Post-open bug-hunter found no escaped regression in import order, live
route ownership, duplicate route handling, dependency detection, legacy growth
guard coverage, or product logic scope. It also ran a live `app.main` route
probe and extra legacy-growth probes.

### Security Auditor

Disposition: NOT-A-BUG

Evidence: Post-open security-auditor found no blocking security finding in
paid-route authz, handler shadowing, OpenAPI exposure, legacy seam re-growth, or
scope widening. It confirmed that the premortem closures are code/test-backed.

## Codex Security

Pending. A Codex Security diff scan / finding discovery pass is still required
before any merge-readiness claim.

## PulsePlate PR Review

Pending. A `pulseplate-pr-review` pass is still required before any
merge-readiness claim.

## Local Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path app/routers/shopping_list_pro.py --path app/routers/shoplist_day.py --path scripts/ci/check_legacy_growth_guard.py --path tests/test_legacy_growth_guard.py`
  with local-only `PULSEPLATE_PYTHON_INDEX_URL` shape warning.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_shopping_list_registration_bootstrap.py tests/test_shoplist_day_endpoint.py tests/test_shopping_list_pro_router.py tests/test_legacy_growth_guard.py tests/test_route_family_bootstrap.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_determinism.py`
- PASS: Experiment Runner oracle-only reviewer artifact
  `artifacts/orchestration/experiments/results/exp-e478f895d5a7.json`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including backend pre-push tests,
  full-repo Bandit pre-push, and docker build test.

## CI Observation

- Current-head CI run `28623833903` initially failed `PR Body Phase2 gates` and
  `Merge readiness gate` because the PR body/artifact Phase2 mapping surface was
  not present yet.
- This artifact and its PR body mirror are the intended governance fix. A fresh
  current-head CI run is still required before any readiness language.

## Merge Readiness

Not claimed. Current-head CI, Codex Security diff scan, `pulseplate-pr-review`,
bot review disposition, review-thread disposition checks, and strict
merge-readiness governance remain required before any merge-readiness claim.
