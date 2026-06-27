# PR #2029 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2029

Branch: `codex/move-test-route-registration-to-canonical-bootstrap`

## Summary

This PR moves `/api/v1/test/*` route registration ownership from
`legacy_app.py` to canonical `app.main` bootstrap without changing handler
payloads, headers, auth behavior, request-time production/staging fail-closed
guards, generated OpenAPI, or generated client artifacts.

## Scope

- Add `TEST_ROUTE_SPECS` in `app/routers/test.py`.
- Hide test routes at source with `include_in_schema=False`.
- Register the test route family from `app/main.py` through
  `RouteMemberContract` and `ensure_route_family_registered(...)`.
- Preserve the golden registration matrix: unset/local/dev/development/test/
  testing/ci register; production/prod do not; staging requires exact
  `ENABLE_TEST_ROUTES=1`; unknown env does not register.
- Preserve request-time `_ensure_non_production()` 404 behavior.
- Remove only the legacy `app.routers.test` import/include block.
- Shrink the legacy growth guard allowlist and add test-router reintroduction
  tests for direct, aliased, module-qualified, dynamic, and walrus imports.
- Update backend routing documentation.

## Out Of Scope

No business router, nutrition, shopping, FoodDB, dependency updates, middleware,
lifespan, frontend, iOS, macOS, or feature-flag redesign.

## Implementation Commits

- `929fda5791333fae2c0eff31f911408e5a38bc55` - moves test route
  registration to canonical bootstrap, removes legacy ownership, adds guards
  and focused tests, and records routing-map evidence.

## Lane Start Provenance

- Base branch: fresh `origin/main` containing merged PR `#2021`.
- Branch: `codex/move-test-route-registration-to-canonical-bootstrap`
- Packet: `artifacts/orchestration/task_packets/f4b4a3415bdb.json`
- Role order executed pre-open:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed mapping artifact created after GitHub assigned PR number `#2029`.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Post-open Role Review Evidence

Disposition: NOT-A-BUG

Finding: No actionable defects reported by the mandatory post-open role passes.

Evidence:

- `qa-engineer-agent`: PASS; no blocking QA findings. It verified the env
  matrix, canonical `app.main` owner, request-time production/staging-disabled
  404 behavior, source/final OpenAPI hiding, legacy reintroduction coverage,
  focused pytest evidence, `make validate-changed`, and generated artifact
  zero diff.
- `bug-hunter`: PASS; no blocking runtime/edge-case findings. It verified
  canonical owner wiring, env precedence, request-time fail-closed behavior,
  source/final OpenAPI hiding, dynamic legacy reintroduction tests, and
  `git diff --check origin/main...HEAD`.
- `security-auditor`: PASS; no blocking security findings. It verified
  production/prod/unknown env non-registration, exact staging flag semantics,
  request-time env-flip 404 behavior, no auth/payload/header rewrite, no
  OpenAPI/client exposure, no legacy reintroduction gap, and no auth/business/
  FoodDB/middleware/lifespan/frontend/iOS/macOS scope creep.

## Codex Security Evidence

Disposition: NOT-A-BUG

Finding: Codex Security diff scan found no reportable security findings.

Evidence:

- Scan ID: `bd691441-a818-410d-a585-dec1477f6770`
- Mode: branch-diff-backed Codex Security diff scan
- Reportable findings: `0`
- Coverage: `6/6` workbench rows closed
- Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-zSiTqs/move-test-route-registration-to-canonical-bootstrap/929fda5791333fae2c0eff31f911408e5a38bc55_20260627T095720Z_3nu5mkap/report.md`

## pulseplate-pr-review Disposition

Disposition: NOT-A-BUG

Finding: The advisory dry-run report flagged a `note` for large diff risk
because the diff has 468 changed lines, above the 300-line review-risk
threshold.

Evidence: This PR is the approved narrow test-router canonical-bootstrap
slice. The larger line count is primarily deterministic tests and guard
coverage for the required env matrix, request-time fail-closed behavior,
OpenAPI hiding, and legacy reintroduction cases. The approved focused pytest
bundle, `make validate-changed`, pre-commit, post-open role passes, and Codex
Security diff scan all ran; no actionable code/security/test defect was
reported. No split is required for this already-scoped route-registration PR.

## Premortem Finding Closure

Disposition: FIXED

Finding: Registration could widen by moving to canonical bootstrap but losing
the env gate.

Evidence: `app/main.py` gates registration in
`_test_routes_enabled_for_registration()`. `tests/test_test_route_registration_bootstrap.py`
covers unset/local/dev/development/test/testing/ci, staging exact flag,
production/prod, unknown env, and env-precedence cases.

Disposition: FIXED

Finding: Test routes could leak into public OpenAPI or generated clients.

Evidence: `app/routers/test.py` sets source `include_in_schema=False`, and
`tests/test_openapi_namespace_guards.py` plus `make openapi-check` prove
`/api/v1/test/*` stays out of public schema with zero generated artifact diff.

Disposition: FIXED

Finding: Legacy reintroduction could return through direct or dynamic imports.

Evidence: `scripts/ci/check_legacy_growth_guard.py` no longer allowlists
`test_router.router` or `from app.routers import test as test_router`, and
`tests/test_legacy_growth_guard.py` covers direct, aliased, module-qualified,
dynamic, and walrus reintroduction.

Disposition: FIXED

Finding: Existing tests could keep proving the old raw `legacy_app.app` owner
instead of canonical bootstrap behavior.

Evidence: `tests/test_test_router.py` and
`tests/test_legacy_runtime_env_canonicalization.py` reload through
`app.main` canonical bootstrap after env changes.

Disposition: NOT-A-BUG

Finding: Full local `make verify` is not run.

Evidence: Operator explicitly approved deferring full local `make verify` for
this PR. Focused local gates, pre-commit, current-head CI, and strict
merge-readiness remain mandatory before readiness claims.

## Experiment Runner Evidence

- Runner mode: `oracle_only_governance_reviewer`
- Experiment ID: `exp-ca7cfd17a97b`
- Artifact: `artifacts/orchestration/experiments/results/test-route-canonical-bootstrap-oracle-result-v2.json`
- Status: accepted
- Shared tree untouched: true
- Mutated paths: []
- Oracle commands:
  - `python3 scripts/ci/check_legacy_growth_guard.py` -> exit 0
  - `pytest -q tests/test_test_router.py tests/test_legacy_runtime_env_canonicalization.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/test_route_family_bootstrap.py tests/test_test_route_registration_bootstrap.py` -> exit 0
- Co-author trailer required and included in implementation commit:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation Evidence

- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `pytest -q tests/test_test_router.py tests/test_legacy_runtime_env_canonicalization.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/test_route_family_bootstrap.py tests/test_test_route_registration_bootstrap.py`
- PASS: `make openapi-check`
- PASS: `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS: `make validate-changed` after commit; selected changed backend tests passed.
- PASS: `pre-commit run --all-files`
- PASS: `git diff --check`
- PASS: pre-push hooks, including changed-file mypy, full-repo Bandit
  pre-push, backend pre-push tests, and Docker build test.
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 2029`
- PASS: post-open `qa-engineer-agent`, `bug-hunter`, and `security-auditor`
  role passes.
- PASS: Codex Security diff scan / finding discovery; `0` reportable findings.
- PASS: `pulseplate-pr-review`; advisory large-diff note dispositioned
  `NOT-A-BUG` above.

Full local `make verify` deferred by operator approval for this PR. No readiness
claim until current-head CI and strict merge-readiness pass.

## Mapping Notes

Initial PR open: no actionable review comments existed at artifact creation.
Any post-open actionable bot, human, role-agent, Codex Security, or
`pulseplate-pr-review` finding must be fixed or formally dispositioned here
before readiness claims.
