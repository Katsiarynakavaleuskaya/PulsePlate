# PR 2005 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2005

Branch: `codex/shrink-legacy-restaurant-moderation-registration-seam`

## Summary

This PR moves protected restaurant moderation status route registration from
`legacy_app.py` into canonical `app/main.py` bootstrap. It preserves the existing
route path, handler, response model, hidden OpenAPI posture, protected
`_get_api_key_dynamic` dependency, and `403/404/422` behavior.

## Scope

- Add moderation route constants in `app/routers/restaurants.py`.
- Register `moderation_router` from `app/main.py` via
  `ensure_route_family_registered(...)`.
- Remove the legacy moderation router import/include from `legacy_app.py`.
- Shrink the legacy growth guard allowlist and reduce the measured `api_key`
  app-surface baseline to `6`.
- Add focused tests for route registration, auth behavior, OpenAPI hiding,
  duplicate/partial-state rejection, and legacy guard regression coverage.
- Update `docs/architecture/backend_routing_map.md`.

## Out Of Scope

FoodDB, restaurant store, PostgreSQL shadow reads, provenance, importer,
promotion, RBAC, moderator identity, BOLA remediation, rate limiting, route
path/status changes, OpenAPI/client artifacts, frontend, iOS, DB migrations,
and `RouteMemberContract` changes.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/8180df059038.json`
- Base SHA: `6b84f6bbd24b5c7205d47935194a4ff4febf7f03`.
- Branch: `codex/shrink-legacy-restaurant-moderation-registration-seam`.
- Starter: direct repo startup with `check_preflight.py` and `task_bootstrap.py`;
  packet creation was treated as provenance only, not role execution.

## Role Dispatch Evidence

- Required role order from packet:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- `agent-coordinator`: scope locked to registration ownership of only
  `PATCH /api/v1/restaurants/submissions/{submission_id}/status`; no product,
  store, auth model, OpenAPI client, frontend, iOS, or DB scope.
- `architecture-specialist`: confirmed reuse of the PR-7 route-family contract;
  `app/bootstrap/route_family.py` must remain unchanged.
- `backend-engineer`: confirmed canonical registration shape, legacy include
  removal, and expected post-change `api_key` app-surface baseline of `6`.
- `security-auditor`: confirmed `_get_api_key_dynamic`, hidden OpenAPI, and
  `403` behavior must be preserved without RBAC/BOLA/rate-limit expansion.
- `qa-engineer-agent`: required focused pytest, legacy guard CLI,
  `make validate-changed`, pre-commit, and exact route-table checks.
- `bug-hunter`: highlighted false-green risks around route ownership,
  duplicate/partial registration, auth drift, copied 429 metadata, and
  TestClient override leakage.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/pr-8-restaurant-moderation-registration-premortem.md`.
- Decision: `proceed with changes`.
- Findings closed:
  - Auth/OpenAPI parity preserved by exact route-table and runtime API-key tests.
  - Legacy guard baseline reduced from measured code and backed by regression tests.
  - Initial staged-state `make validate-changed` no-selection risk closed by
    post-commit rerun that selected the changed tests.
  - Scope containment preserved by keeping product/security policy work out of
    this diff.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr8-restaurant-moderation-oracle.json`.
Artifact: `artifacts/orchestration/experiments/results/exp-7c1ad9f17afb-pr8-restaurant-moderation.json`
- Mode: `oracle_only_governance_reviewer`.
- Status: `accepted`.
- Mutated paths: `[]`.
- Shared tree untouched: `true`.
- Source diff applied in isolated checkout:
  `app/main.py`, `app/routers/restaurants.py`,
  `docs/architecture/backend_routing_map.md`, `legacy_app.py`,
  `scripts/ci/check_legacy_growth_guard.py`, `tests/test_legacy_growth_guard.py`,
  `tests/test_restaurant_moderation_bootstrap.py`.
- Oracle commands passed:
  - `python3 scripts/ci/check_legacy_growth_guard.py`.
  - `python3 -m py_compile app/main.py app/routers/restaurants.py legacy_app.py scripts/ci/check_legacy_growth_guard.py tests/test_restaurant_moderation_bootstrap.py tests/test_legacy_growth_guard.py`.
- Co-author required: `true`.
- Co-author reason: Experiment Runner oracle evidence shaped the PR-8 commit
  decision and governance evidence.
- Commit `7e34103c5` includes the canonical trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 7e34103c5
Evidence: `app/main.py` registers restaurant moderation through canonical bootstrap; `app/routers/restaurants.py` owns route constants and hidden source OpenAPI metadata; `legacy_app.py` no longer imports/includes `restaurant_moderation_router`; `scripts/ci/check_legacy_growth_guard.py` sets `api_key` baseline to `6`; `tests/test_restaurant_moderation_bootstrap.py` and `tests/test_legacy_growth_guard.py` cover registration, runtime behavior, and legacy reintroduction rejection.
Reason: Moves only the protected restaurant moderation registration ownership seam from legacy to canonical bootstrap while preserving route behavior and guard coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2005 -> 7e34103c5

Disposition: FIXED
Commit: 8f2529440
Evidence: `tests/test_restaurant_moderation_bootstrap.py` parameterizes the valid API-key success path over both `approved` and `rejected`; focused pytest and `make validate-changed` passed with `72 passed`.
Reason: Closed the post-open QA coverage note that the success-path behavior test only exercised `approved` despite the PR-8 acceptance wording naming approve and reject success.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2005 -> 8f2529440

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: role dispatch bridge manifest for packet
  `artifacts/orchestration/task_packets/8180df059038.json`.
- PASS: focused pytest for
  `tests/test_restaurant_moderation_bootstrap.py`,
  `tests/test_restaurants_router.py`, `tests/test_legacy_growth_guard.py`,
  `tests/test_route_family_bootstrap.py`,
  `tests/security/test_api_auth_tier_contract_pack.py`,
  `tests/security/test_api_bola_contract_pack.py`, and
  `tests/test_openapi_namespace_guards.py`.
- PASS: runtime route-table probe found exactly one `PATCH`, endpoint
  `app.routers.restaurants.review_restaurant_submission`, hidden OpenAPI,
  `404/422`, recursive `_get_api_key_dynamic`, and no public OpenAPI path.
- PASS: measured legacy guard counter `Counter({'api_key': 6})`.
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`.
- PASS: `. .venv/bin/activate && python -m mypy app/main.py app/routers/restaurants.py`.
- PASS: `pre-commit run --all-files`.
- PASS: `git diff --check --cached`.
- PASS: post-commit `make validate-changed`, selecting
  `tests/test_legacy_growth_guard.py` and
  `tests/test_restaurant_moderation_bootstrap.py`.
- PASS: post-QA focused pytest for `tests/test_restaurant_moderation_bootstrap.py`
  and `tests/test_legacy_growth_guard.py` with `72 passed`.
- PASS: post-QA `make validate-changed` with `72 passed`.
- PASS: pre-push hooks, including changed-file backend tests, full-repo Bandit,
  and docker build test.
- DEFERRED by operator instruction: full local `make verify` because the project
  has a large test suite; this PR uses the machine-heavy narrow-gate path with
  focused pytest, `make validate-changed`, pre-commit, pre-push hooks, and
  current-head CI as the heavy signal before merge.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Initial PR open: no review threads were present at artifact creation.
- [x] Post-open `qa-engineer-agent` pass completed; QA coverage note fixed in
  commit `8f2529440`.

No review thread has been resolved without disposition evidence.

## Merge Readiness

- [x] Narrow local gates passed.
- [x] Full local `make verify` deferral documented.
- [x] Canonical fixed-mapping artifact exists with the assigned PR number.
- [ ] Mandatory post-open role passes complete:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan / finding discovery complete when callable.
- [ ] `pulseplate-pr-review` complete.
- [ ] Current-head CI required checks pass with no pending required jobs.
- [ ] CodeRabbit/Sourcery/Cubic actionables are dispositioned.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict `check_merge_ready.py --require-auth` passes.
- [ ] Mandatory wait-window after latest bot/review activity completes.
