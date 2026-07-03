# Food/Catalog Canonical Bootstrap Premortem

Mode: `pr-premortem`

Skill: `pulseplate-premortem-risk-review`

Task packet: `artifacts/orchestration/task_packets/f130c83cd0bd.json`

Implementation commit reviewed: `687f77e97b`

## Summary

Plan: move only foods/catalog route registration ownership from `legacy_app.py`
to canonical `app/main.py` bootstrap while preserving runtime behavior,
OpenAPI visibility, dependencies, response metadata, and existing metrics labels.

Failure frame: six months from now this PR failed because route ownership looked
migrated, but runtime/API evidence drifted in a way local smoke tests missed.

## Most Likely Failure

Foods/catalog are reintroduced into `legacy_app.py` later through an alias,
dynamic import, or wrapper router because the legacy guard still allows the old
facts. The product continues to run, but ownership silently splits again and
future route-family migrations inherit contradictory registration truth.

Closure: FIXED in `687f77e97b`.

Evidence:

- `scripts/ci/check_legacy_growth_guard.py` removes foods/catalog router imports
  and registration facts from the allowlist.
- `tests/test_legacy_growth_guard.py` rejects direct, aliased, module-qualified,
  dynamic, destructured, walrus, and nested include reintroduction patterns.

## Most Dangerous Failure

Foods become visible in public OpenAPI, or catalog public OpenAPI exposure
changes, because the old hiding behavior was include-level in `legacy_app.py`
while the canonical registrar validates source route metadata. That would
change public contract visibility without an explicit API-contract PR.

Closure: FIXED in `687f77e97b`.

Evidence:

- `app/routers/foods.py` makes foods source route metadata hidden and publishes
  hidden `FOODS_ROUTE_SPECS`.
- `app/routers/catalog.py` keeps visible source-route `CATALOG_ROUTE_SPECS`.
- `tests/test_food_catalog_registration_bootstrap.py` validates source
  visibility and registered route visibility.
- `tests/test_openapi_namespace_guards.py` rejects `/api/v1/foods*` and
  `/api/v1/catalog*` public OpenAPI leaks.

## Hidden Assumption

The migration assumes route behavior is unchanged if paths and methods still
work. That is not enough for this repo: dependency provider identity, response
metadata, duplicate/partial registration behavior, and metrics labels are part
of the production contract.

Closure: FIXED in `687f77e97b`.

Evidence:

- `app/main.py` registers foods/catalog through `ensure_route_family_registered`
  with `get_food_store`, `get_catalog_service`, and barcode `404`/`422`
  response metadata contracts.
- `tests/test_food_catalog_registration_bootstrap.py` covers idempotency,
  duplicate route rejection, partial registration rejection, foreign handlers,
  wrong methods, dependency drift, visibility drift, and response metadata drift.
- `tests/test_metrics.py` proves existing Prometheus labels use route templates
  for foods/catalog routes, not raw IDs or query strings.

## Revised Plan

1. Keep the diff registration-only: no FoodDB, Meili/provider, recipes, users,
   restaurants, nutrition recommendation, frontend, iOS, or macOS changes.
2. Use the established canonical static-family pattern in `app/main.py` and
   leave business logic in the source routers/services.
3. Treat OpenAPI and observability as proof surfaces only: no new runtime
   metrics, dashboards, or public contract expansion.
4. Keep rollback bounded to the canonical bootstrap helper/imports/call, route
   specs/visibility, legacy include removal, guard shrink, tests, and this
   routing evidence.

## Pre-Merge Checklist

- Focused foods/catalog bootstrap tests pass.
- Legacy-growth guard rejects foods/catalog regrowth.
- Public OpenAPI still excludes `/api/v1/foods*` and `/api/v1/catalog*`.
- Existing metrics labels remain route templates, with no raw path/query labels.
- `make validate-changed` and `pre-commit run --all-files` pass on the committed
  branch diff.
- Post-open review chain runs before readiness claims.

## Decision

`proceed with changes`

All premortem findings identified for this PR scope are closed by code,
deterministic tests, guard narrowing, and routing evidence in `687f77e97b`.
