# Backend Routing Map (evidence-driven)

**Goal:** map which routers/endpoints are registered, where, and under which guards/feature flags.
This is a **runtime truth** view (not a product wishlist).

## Anchors (stable)

- [Canonical entrypoint chain](#canonical-entrypoint-chain)
- [Router registration](#router-registration-always-on-vs-conditional)
- [OpenAPI generation behavior](#openapi-generation-behavior-important)

## Evidence format (recommended)

- **Anchor (stable):** a human-readable identifier that remains true when line numbers move
  (route path, function name, section title).
- **Evidence (file:line):** supporting pointer to the current implementation.

## Canonical entrypoint chain

- Runtime entrypoint: `uvicorn app.main:app` (`Dockerfile:102-105`)
- `app/main.py` uses `legacy_app.app` as the FastAPI instance and applies bootstrap (`app/main.py:11-22`).
- Most legacy route registration still happens in `legacy_app.py`; canonical bootstrap-owned
  route families are registered from `app/main.py`.

## Router registration: always-on vs conditional

### Always-on routers (registered unconditionally)

Anchor (stable): `legacy_app.py -> include_router(...) for core API routers`

Evidence: `legacy_app.py:922-932`

- `foods_router` (`app/routers/foods.py`)
- `recipes_router` (`app/routers/recipes.py`)
- `users_router` (`app/routers/users.py`)
- `catalog_router` (`app/routers/catalog.py`)

### Canonical plan export routers (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_plan_export_routers_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py:26` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:87` — shared `ensure_route_family_registered(...)` guard
  validates source routers before registration and validates existing app routes for
  idempotency, partial registration, duplicate/foreign handlers, required dependency drift,
  response metadata drift, and OpenAPI visibility drift.
- `app/main.py:686-700` — applies the shared static guard to `export_router` and
  `plan_router`.
- `app/main.py` — registers `export_router` and `plan_router` from `app/routers/plan_export.py`
  with `dependencies=[Depends(_legacy_module._get_api_key_dynamic)]`
- `app/routers/plan_export.py` — owns implementation, rate-limit decorators, signed export token
  guard for weekly CSV/PDF, response schemas, and `PLAN_EXPORT_ROUTE_SPECS`

Runtime effect:
- `POST /api/v1/export/sign`
- `GET /api/v1/plan/week/export.csv`
- `GET /api/v1/plan/week/export.pdf`

OpenAPI effect:
- Source `APIRoute.include_in_schema` remains `True`.
- Final public `app.openapi()` continues to hide these export/plan paths through the canonical
  OpenAPI builder.
- Hidden legacy export aliases remain a separate compatibility router owned by
  `app/routers/legacy_export_aliases.py`.
- Unexpected source `APIRoute`s in the plan/export source routers fail closed before
  registration; this matches the shoplist export bootstrap policy.

### Canonical shoplist export router (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_shoplist_export_router_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py:26` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:87` — shared `ensure_route_family_registered(...)` guard.
- `app/main.py:703-717` — applies the shared static guard to `shoplist_export_router`.
- `app/main.py` — registers `shoplist_export_router` from `app/routers/shoplist_export.py`
  with `dependencies=[Depends(_legacy_module._get_api_key_dynamic)]`
- `app/routers/shoplist_export.py` — owns implementation, export rate-limit decorators, CSV/PDF
  response behavior, and the shared route constants from `app/routers/shoplist_export_routes.py`

Runtime effect:
- `GET /api/v1/shoplist`
- `GET /api/v1/shoplist/export.csv`
- `GET /api/v1/shoplist/export.pdf`

OpenAPI effect:
- Source `APIRoute.include_in_schema` remains `True`.
- Final public `app.openapi()` continues to hide these shoplist export paths through the
  canonical OpenAPI builder.
- `legacy_app.py` no longer imports or registers `app/routers/shoplist_export.py`; the
  legacy growth guard rejects reintroduced legacy registration.

### Restaurant moderation router (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_restaurant_moderation_router_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py:26` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:87` — shared `ensure_route_family_registered(...)` guard.
- `app/main.py` — registers `moderation_router` from `app/routers/restaurants.py` with
  `dependencies=[Depends(_legacy_module._get_api_key_dynamic)]`.
- `app/routers/restaurants.py` — owns moderation implementation, `RestaurantSubmission`
  response model, hidden route metadata, `404/422` response metadata, and
  `RESTAURANT_MODERATION_ROUTE_SPECS`.

Runtime effect:
- `PATCH /api/v1/restaurants/submissions/{submission_id}/status`

OpenAPI effect:
- Source `APIRoute.include_in_schema` is `False`.
- Final public `app.openapi()` continues to hide the restaurant moderation path.
- `legacy_app.py` no longer imports or registers `restaurant_moderation_router`; the
  legacy growth guard rejects reintroduced legacy registration.

### VIP routes (feature-flag gated, canonical-owned registration)

Anchor (stable): `app/main.py -> _register_paid_tier_routes(app)` delegates to `vip_registration.register_vip_routes()`

Evidence:
- `app/main.py:829-832` — `_register_paid_tier_routes(app)` calls VIP
  registration before PRO registration.
- `app/routers/vip_registration.py:61-137` — central VIP registration function
  applies the `is_vip_module_enabled()` gate and `api_key_header` dependency.

Runtime effect:
- When VIP module is enabled, `vip_registration.register_vip_routes()` includes `app/routers/vip.py` with `api_key_header` dependency.

### PRO routes (canonical-owned registration)

Anchor (stable): `app/main.py -> _register_paid_tier_routes(app)` delegates to centralized `pro_registration.register_pro_routes()`

Evidence:
- `app/main.py:808-832` — canonical bootstrap mirrors returned PRO routers to
  `legacy_app.pro_router` / `legacy_app.premium_week_router` only after VIP and
  PRO registration values are resolved.
- `app/routers/pro_registration.py:26-104` — centralized registration +
  feature-flag gated `premium_week`.

Runtime effect:
- In normal runtime: includes `app/routers/pro.py`.
- `premium_week` is included only when enabled (`FEATURE_PREMIUM_WEEK_ENABLED` or VIP module enabled).

### Bayesian adherence + nutrition log (import-soft)

Anchor (stable): `legacy_app.py -> try/except ImportError then include_router(...)`

Evidence: `legacy_app.py:829-843`

- Included if import succeeds:
  - `app/routers/bayes_adherence.py`
  - `app/routers/nutrition_log.py`

### Shopping list generators (always included; tier handled inside)

Anchor (stable): `legacy_app.py -> include_router(shopping_list_pro_router, shoplist_day_router)`

Evidence: `legacy_app.py:845-849`

- `app/routers/shopping_list_pro.py`
- `app/routers/shoplist_day.py` (iOS MVP path)

### Insight endpoints (LLM) + providers wiring (legacy_app → llm → providers)

Anchor (stable): `legacy_app.py -> POST /api/v1/insight` and `POST /insight` call `llm.get_provider() -> provider.generate()`

Evidence:
- `legacy_app.py:2168-2187` — HTTP endpoints `/api/v1/insight` and `/insight`
- `legacy_app.py:2066-2076` + `2098-2117` — lazy `llm.get_provider()` + `provider.generate()`
- `llm.py:57-79` + `91-153` — provider selection (`LLM_PROVIDER`) + optional provider imports

### Exports rate limiting (route wrappers)

Anchor (stable): `legacy_app.py -> export routes wrapped with limit_if_available(RATE_LIMIT_EXPORTS)`

Evidence:
- `legacy_app.py:5180-5223` — export endpoints decorated with:
  - `responses=RATE_LIMIT_429_RESPONSES`
  - `@limit_if_available(RATE_LIMIT_EXPORTS)`

### Conditional routers: BMI Pro / Business

Anchor (stable): `app/main.py -> app/routers/bmi_registration.py` owns BMI route registration; `legacy_app.py` remains a compatibility seam for direct-call shims and mirrored attrs.

Evidence:
- `app/main.py -> ensure_canonical_app_bootstrap()`
- `app/routers/bmi_registration.py -> register_bmi_routes()`

- BMI Free: canonical `/api/v1/bmi/calculate` is registered by `app/main.py` via `app/routers/bmi_registration.py`
- BMI Pro: registered by `app/main.py` via `app/routers/bmi_registration.py`, included only if `FEATURE_BMI_PRO_ENABLED` is truthy
  - canonical: `/api/v1/pro/bmi`
  - legacy alias: `/api/v1/bmi/pro`
- Business: included only if `BUSINESS_MODULE_ENABLED` is truthy

### Bodyfat route family (canonical-owned bootstrap)

Anchor (stable): `app/main.py -> _include_bodyfat_router_if_needed(app)` owns
`app/routers/bodyfat.py`.

Evidence:
- `app/routers/bodyfat.py` defines `BODYFAT_ROUTE_SPECS`, a module-level
  canonical router for `POST /api/v1/bodyfat`, and a stable direct-inclusion
  `get_router()` adapter for old `/bodyfat` compatibility tests/utilities.
- `app/main.py -> _include_bodyfat_router_if_needed(app)` registers the
  canonical bodyfat family through `ensure_route_family_registered(...)` and
  `RouteMemberContract`.
- `legacy_app.py` does not import or include `app.routers.bodyfat`; legacy
  growth guard tests reject direct, aliased, module-qualified, and factory-based
  bodyfat re-registration in `legacy_app.py`.

Runtime effect:
- In normal runtime: `POST /api/v1/bodyfat` is routable exactly once through
  canonical bootstrap.
- Direct compatibility: including `app.routers.bodyfat.get_router()` still
  provides unprefixed `POST /bodyfat` for old direct-router inclusion callers.
- OpenAPI: the source route keeps `include_in_schema=True`, but the final
  canonical OpenAPI builder still filters `/api/v1/bodyfat` out of published
  `/openapi.json`; generated client/OpenAPI artifacts are unchanged.

### Test router (canonical bootstrap-owned, non-production env)

Anchor (stable): `app/main.py -> _include_test_router_if_enabled(app)` owns
`app/routers/test.py`.

Evidence:
- `app/bootstrap/route_family.py:26` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:87` — shared `ensure_route_family_registered(...)` guard.
- `app/routers/test.py` — owns `TEST_ROUTE_SPECS`, source route handlers, hidden
  `include_in_schema=False` metadata, and request-time `_ensure_non_production()`.
- `app/main.py` — registers the test route family only when
  `get_runtime_env_name()` resolves to `local/dev/development/test/testing/ci`, or
  `staging` with exact `ENABLE_TEST_ROUTES=1`.
- `legacy_app.py` does not import or include `app.routers.test`; the legacy growth
  guard rejects direct, aliased, module-qualified, and dynamic re-registration there.

Runtime effect:
- `POST /api/v1/test/rate-limit`
- `GET /api/v1/test/health`
- `POST /api/v1/test/echo`

OpenAPI effect:
- Source `APIRoute.include_in_schema` is `False`.
- Final public `app.openapi()` does not expose `/api/v1/test/*`; generated
  client/OpenAPI artifacts are unchanged.

## OpenAPI generation behavior (important)

OpenAPI generation runs in **full-schema mode** (schema-only mode removed in PR-631).

**Evidence (implementation):**

- Generator pins env and enables feature-flagged routers, then imports canonical entrypoint:
  - Anchor (stable): `scripts/generate_openapi.py -> main()`
  - Evidence: `scripts/generate_openapi.py:94`
- Determinism gate asserts key routes exist in schema:
  - Anchor (stable): `tests/test_openapi_determinism.py -> test_openapi_and_schema_ts_are_deterministic()`
  - Evidence: `tests/test_openapi_determinism.py:17`

## Maintenance rule

Checklist (lightweight):
- [ ] If you add/remove a router or change a feature flag / tier gate: update this doc **or** state “no routing-doc update needed” in the PR description.
- [ ] If you change OpenAPI output: regenerate and commit `frontend/src/api/openapi.json` + `schema.ts` (in the runtime PR that changes behavior).
