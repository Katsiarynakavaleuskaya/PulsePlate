# Nutrition State Canonical Bootstrap Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Scope: `bayes_adherence.router`, `nutrition_log.router`, and
`legacy_nutrition_alias.router` registration ownership only.

## Findings

### PM-001 Split route ownership survives the migration

Risk: `app/main.py` could add canonical registration while `legacy_app.py` still
imports/includes the same routers. Route counts would look correct, but
`legacy_app.py` would remain the real owner.

Disposition: FIXED.

Evidence:
- `legacy_app.py` removes the three target import/include blocks.
- `scripts/ci/check_legacy_growth_guard.py` removes their allowlist facts.
- `tests/test_legacy_growth_guard.py` rejects direct, aliased,
  module-qualified, dynamic, destructured, and walrus reintroduction patterns.

### PM-002 Partial or duplicate runtime creates inconsistent state APIs

Risk: one nutrition/adherence route registers while another is missing, or a
duplicate method/path with a foreign handler appears after reload/bootstrap.

Disposition: FIXED.

Evidence:
- `app/main.py` registers the five nutrition state route members atomically via
  `ensure_route_family_registered(...)`.
- `tests/test_nutrition_state_registration_bootstrap.py` covers empty-app
  registration, idempotency, partial family failure, duplicate method/path
  failure, foreign handler failure, wrong method failure, and visibility drift.

### PM-003 Auth tier or subject ownership regresses

Risk: stateful Bayes/nutrition endpoints could lose PRO tier protection or stop
binding state to the credential-derived subject.

Disposition: FIXED.

Evidence:
- `app/main.py` route-member contracts require `require_pro_tier` and
  `get_current_user` for Bayes/nutrition-log routes.
- `tests/test_nutrition_state_registration_bootstrap.py` verifies router-level
  tier dependencies, path-level subject dependencies, and fail-closed missing
  dependency cases.
- `tests/security/test_api_auth_tier_contract_pack.py` and
  `tests/security/test_api_bola_contract_pack.py` pass for this diff.

### PM-004 Legacy alias loses observability or delegation semantics

Risk: `/api/nutrition/{date_str}` could remain callable but stop recording the
alias metric or stop delegating to canonical daily nutrition behavior.

Disposition: FIXED.

Evidence:
- `app/routers/legacy_nutrition_alias.py` keeps the alias metric hit and
  `get_daily_nutrition(...)` delegation in the router module.
- `tests/test_nutrition_daily.py` verifies hidden OpenAPI behavior, auth guard,
  metric increment, canonical route no-op on the alias metric, and explicit
  delegation to `get_daily_nutrition(...)`.

### PM-005 OpenAPI or generated client drift leaks the hidden alias

Risk: moving registration could expose the legacy alias in OpenAPI or remove
visible PRO route contracts from generated clients.

Disposition: FIXED.

Evidence:
- `tests/test_nutrition_state_registration_bootstrap.py` asserts source and
  registered visibility.
- `make openapi-check` passes when run with the repo venv on `PATH`.
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json
  frontend/src/api/schema.ts` passes.

### PM-006 Import-soft legacy behavior masks startup failures

Risk: the old `try/except ImportError` behavior could silently create a runtime
missing nutrition/adherence state routes.

Disposition: FIXED as fail-closed hardening.

Evidence:
- `legacy_app.py` no longer swallows imports for the three target routers.
- `app/main.py` imports/registers them through canonical bootstrap without
  `try/except ImportError`.
- `docs/architecture/backend_routing_map.md` documents that missing modules now
  fail startup/bootstrap instead of creating a partial runtime.

### PM-007 Future auth/BOLA refactor instability bleeds into this slice

Risk: broad auth/tier/BOLA route-introspection work is a separate future lane and
could destabilize this bounded legacy-removal PR.

Disposition: NOT-A-BUG for this PR.

Evidence:
- This diff does not change `tests/security/_api_authz_contracts.py` or widen
  auth/tier classification.
- Existing auth/tier/BOLA packs pass as oracles for the touched surface.
- The future auth/BOLA refactor remains out of scope for this route-family
  ownership migration.

## Validation Evidence

- `pytest -q tests/test_nutrition_state_registration_bootstrap.py
  tests/test_legacy_growth_guard.py tests/test_route_family_bootstrap.py` - PASS.
- `pytest -q tests/test_bayes_adherence_api.py tests/test_nutrition_log_api.py
  tests/test_nutrition_log_idempotency.py tests/test_nutrition_daily.py` - PASS.
- `pytest -q tests/security/test_api_auth_tier_contract_pack.py
  tests/security/test_api_bola_contract_pack.py
  tests/test_pro_vip_route_dependency_guard.py tests/test_paid_route_guards.py`
  - PASS.
- `python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `make openapi-check` - PASS with repo venv first on `PATH`.
- `make validate-changed` - PASS; selected no branch-scoped tests, so focused
  pytest bundles above are primary evidence.
- `pre-commit run --all-files` - PASS.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/exp-70808f0c6402.json` -
  accepted.

No unresolved P0/P1 premortem findings remain.
