# Recipe/Nutrition Reference Canonical Bootstrap Premortem

Mode: `pr-premortem`

Task packet: `artifacts/orchestration/task_packets/3467351ee456.json`

Branch: `codex/move-recipe-nutrition-reference-registration-to-canonical-bootstrap`

## Summary

Plan: move only recipe and FREE nutrition-reference route registration ownership
from `legacy_app.py` to canonical `app/main.py` bootstrap while preserving
runtime behavior, OpenAPI filtering, response schemas, auth/tier posture,
nutrition formulas, recipe store behavior, generated clients, and frontend/iOS
surfaces.

Failure frame: six months from now this PR failed because the route ownership
migration looked mechanical, but a subtle registration, guard, OpenAPI, or
auth/tier drift changed production behavior.

## Most Likely Failure

`recipes_router` or `nutrition_recommendations_router` is reintroduced into
`legacy_app.py` through an alias, module-qualified include, dynamic import,
computed import string, destructuring/walrus assignment, or nested wrapper
router. The product still starts, but canonical bootstrap ownership silently
splits again and future legacy-removal PRs inherit false evidence.

Closure: FIXED in this PR diff.

Evidence:

- `scripts/ci/check_legacy_growth_guard.py` removes recipes and nutrition
  recommendations from the legacy allowlist.
- `tests/test_legacy_growth_guard.py` rejects direct, aliased,
  module-qualified, dynamic/computed import, destructuring/walrus, and nested
  wrapper-router reintroduction patterns.
- `python scripts/ci/check_legacy_growth_guard.py` passes.

## Most Dangerous Failure

Recipes or nutrition recommendations become visible in public `app.openapi()`,
or their source route visibility drifts, because source-router metadata and
final public OpenAPI filtering are different proof surfaces. That would create
a public API/client contract change outside this PR scope.

Closure: FIXED in this PR diff.

Evidence:

- `RECIPES_ROUTE_SPECS` and `NUTRITION_RECOMMENDATIONS_ROUTE_SPECS` preserve
  source route `include_in_schema=True`.
- `tests/test_recipe_nutrition_reference_registration_bootstrap.py` verifies
  source visibility, registered-route visibility, and final public OpenAPI
  filtering for `/api/v1/recipes*` and `/api/v1/nutrition/recommendations`.
- `DEV_PYTHON=.venv/bin/python make openapi-check` passes and generated
  frontend OpenAPI artifacts have no diff.

## Hidden Assumption

This slice assumes route registration can move without changing behavior if the
same paths still respond. In this repo that is not enough: duplicate
method/path ownership, partial registration, wrong method, foreign handlers,
visibility drift, and auth/tier dependency drift are part of the migration
contract.

Closure: FIXED in this PR diff.

Evidence:

- `app/main.py` registers the route family through
  `ensure_route_family_registered(...)` with explicit static route members.
- `tests/test_recipe_nutrition_reference_registration_bootstrap.py` covers empty
  app registration, bootstrapped app registration, idempotency, partial
  registration, duplicate method/path, foreign handlers, wrong method,
  visibility drift, and absence of auth/tier dependencies for this FREE
  reference slice.
- Existing recipes and nutrition recommendation behavior tests pass unchanged.

## Revised Plan

1. Keep the diff registration-only: no BOLA/authz expansion, premium
   nutrition handler move, restaurant/user move, recipe-store changes, formula
   changes, OpenAPI/client generation changes, or frontend/iOS/macOS changes.
2. Use the established static route-family bootstrap pattern in `app/main.py`.
3. Treat OpenAPI, guard, auth/tier, and focused behavior tests as proof
   surfaces only; do not invent new response metadata or new product behavior.
4. Keep rollback bounded to restoring the removed legacy imports/includes and
   removing the new canonical bootstrap helper/spec contracts.

## Pre-Merge Checklist

- Focused recipe/nutrition-reference bootstrap tests pass.
- Existing recipes and nutrition recommendation behavior tests pass.
- Legacy-growth guard rejects recipes/nutrition-reference regrowth.
- Public OpenAPI/client artifacts remain unchanged.
- Auth/tier static contract tests pass for the moved FREE/reference surface.
- `make validate-changed` and `pre-commit run --all-files` pass on the
  committed branch diff.
- Post-open review chain runs before readiness claims.

## Decision

`proceed with changes`

All premortem findings identified for this PR scope are closed by code,
deterministic tests, guard narrowing, and routing evidence in this PR diff.
