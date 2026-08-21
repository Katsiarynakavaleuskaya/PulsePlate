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
- `app/bootstrap/application.py` constructs the production singleton and owns
  runtime-env, metadata, logging, and exact lifespan wiring only.
- `app/main.py` imports that singleton directly and applies the existing ordered
  route, middleware, and OpenAPI composition without rebinding it.
- `legacy_app.py` re-exports the singleton and retains only bounded compatibility
  values. `app/main.py` does not import `legacy_app`, and the eight former
  paid/BMI registration mirrors are retired from all three Python surfaces.

## Router registration: always-on vs conditional

### Always-on routers (registered unconditionally)

Anchor (stable): `app/main.py -> ensure_canonical_app_bootstrap(...)`

Evidence: `app/main.py -> _include_restaurants_router_if_needed(app)`

- Public restaurants routes are no longer legacy-owned; see
  [Canonical public restaurants router](#canonical-public-restaurants-router-canonical-bootstrap-owned).
- Users CRUD is no longer legacy-owned; see
  [Canonical users router](#canonical-users-router-canonical-bootstrap-owned).

### Canonical public restaurants router (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_restaurants_router_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py` — shared `RouteMemberContract` /
  `ensure_route_family_registered(...)` guard for exact static route families.
- `app/main.py` — registers public `restaurants_router` as one hidden canonical
  static route family and validates dependency, visibility, duplicate, partial,
  foreign-handler, wrong-method, response-metadata, and route-order drift.
- `app/routers/restaurants.py` — owns public restaurant search/menu/submission
  handlers, `get_restaurant_store`, hidden source-route `RESTAURANT_ROUTE_SPECS`,
  SQLite-authoritative response behavior, and PostgreSQL shadow-read helpers.
- `scripts/ci/check_legacy_growth_guard.py` — rejects reintroducing public
  restaurants router import or registration into `legacy_app.py`.

Runtime effect:
- `GET /api/v1/restaurants/search`
- `GET /api/v1/restaurants/{chain_id}/menu`
- `POST /api/v1/restaurants/submissions`
- `GET /api/v1/restaurants/submissions/{submission_id}`

OpenAPI effect:
- Public restaurants source routes stay hidden from OpenAPI at route metadata
  level.
- Final public `app.openapi()` excludes `/api/v1/restaurants*`.
- Restaurant moderation stays separate; see
  [Restaurant moderation router](#restaurant-moderation-router-canonical-bootstrap-owned).

### Canonical users router (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_users_router_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py` — shared `RouteMemberContract` /
  `ensure_route_family_registered(...)` guard for exact static route families.
- `app/main.py` — registers `users_router` as one hidden canonical static route
  family and validates dependency, visibility, duplicate, partial,
  foreign-handler, wrong-method, and route-order drift.
- `app/routers/users.py` — owns users CRUD handlers, `_require_users_api_key`,
  hidden source-route `USERS_ROUTE_SPECS`, DB retry, conflict, not-found, and
  idempotent delete semantics.
- `scripts/ci/check_legacy_growth_guard.py` — rejects reintroducing users router
  import or registration into `legacy_app.py`.

Runtime effect:
- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

OpenAPI effect:
- Users source routes stay hidden from OpenAPI at route metadata level.
- Final public `app.openapi()` excludes `/api/v1/users*`.

### Canonical recipe/nutrition-reference routers (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_recipe_nutrition_reference_routers_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py` — shared `RouteMemberContract` /
  `ensure_route_family_registered(...)` guard for exact static route families.
- `app/main.py` — registers `recipes_router` and `nutrition_recommendations_router`
  as one canonical static route family and validates visibility, duplicate,
  partial, and foreign-handler drift.
- `app/routers/recipes.py` — owns recipe lookup/search/preview handlers and
  visible source-route `RECIPES_ROUTE_SPECS`.
- `app/routers/nutrition_recommendations.py` — owns the FREE basic nutrition
  recommendation handler and visible source-route `NUTRITION_RECOMMENDATIONS_ROUTE_SPECS`.

Runtime effect:
- `GET /api/v1/recipes`
- `GET /api/v1/recipes/search`
- `GET /api/v1/recipes/{recipe_id}`
- `POST /api/v1/recipes/preview`
- `GET /api/v1/nutrition/recommendations`

OpenAPI effect:
- Source routes remain schema-visible in route metadata.
- Final public `app.openapi()` continues to filter `/api/v1/recipes*` and
  `/api/v1/nutrition/recommendations` through the canonical OpenAPI builder.

### Canonical food/catalog routers (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_food_catalog_routers_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py` — shared `RouteMemberContract` /
  `ensure_route_family_registered(...)` guard for exact static route families.
- `app/main.py` — registers `foods_router` and `catalog_router` as one canonical
  static route family and validates dependency, visibility, duplicate, partial,
  foreign-handler, and response-metadata drift.
- `app/routers/foods.py` — owns food endpoint handlers, `get_food_store`, hidden
  `FOODS_ROUTE_SPECS`, and barcode `404`/`422` response metadata.
- `app/routers/catalog.py` — owns catalog endpoint handlers, `get_catalog_service`,
  and visible source-route `CATALOG_ROUTE_SPECS`.

Runtime effect:
- `GET /api/v1/foods`
- `GET /api/v1/foods/search`
- `GET /api/v1/foods/{food_id}`
- `GET /api/v1/foods/barcode/{barcode}`
- `GET /api/v1/catalog/regions`
- `GET /api/v1/catalog/stores`
- `GET /api/v1/catalog/search`

OpenAPI effect:
- Food source routes stay hidden from OpenAPI at route metadata level.
- Catalog source routes remain schema-visible in route metadata, but final public
  `app.openapi()` continues to filter `/api/v1/catalog/*` through the canonical
  OpenAPI builder.

### Canonical plan export routers (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_plan_export_routers_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py:36` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:138` — shared `ensure_route_family_registered(...)` guard
  validates source routers before registration and validates existing app routes for
  idempotency, partial registration, duplicate/foreign handlers, required dependency drift,
  response metadata drift, and OpenAPI visibility drift.
- `app/main.py:887-898` — applies the shared static guard to `export_router` and
  `plan_router`.
- `app/main.py:51,887-898` — imports the direct canonical dependency owner
  `app.routers.api_key._get_api_key_dynamic` and passes it as
  `dependencies=[Depends(api_key_dependency)]` when registering `export_router`
  and `plan_router` from `app/routers/plan_export.py`.
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
- The former hidden premium day/week CSV test/demo aliases are retired; no
  compatibility router owns them and their paths return the ordinary FastAPI
  404 under every former carrier environment.
- Unexpected source `APIRoute`s in the plan/export source routers fail closed before
  registration; this matches the shoplist export bootstrap policy.

### Canonical shoplist export router (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_shoplist_export_router_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py:36` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:138` — shared `ensure_route_family_registered(...)` guard.
- `app/main.py:901-912` — applies the shared static guard to `shoplist_export_router`.
- `app/main.py:51,901-912` — imports the direct canonical dependency owner
  `app.routers.api_key._get_api_key_dynamic` and passes it as
  `dependencies=[Depends(api_key_dependency)]` when registering
  `shoplist_export_router` from `app/routers/shoplist_export.py`.
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
- `app/bootstrap/route_family.py:36` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:138` — shared `ensure_route_family_registered(...)` guard.
- `app/main.py:51,1068-1079` — imports the direct canonical dependency owner
  `app.routers.api_key._get_api_key_dynamic` and passes it as
  `dependencies=[Depends(api_key_dependency)]` when registering
  `moderation_router` from `app/routers/restaurants.py`.
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
- `app/main.py:1085-1087` — `_register_paid_tier_routes(app)` calls VIP
  registration before PRO registration.
- `app/routers/vip_registration.py:82-165` — central VIP registration function
  applies the `is_vip_module_enabled()` gate and `api_key_header` dependency.

Runtime effect:
- When VIP module is enabled, `vip_registration.register_vip_routes()` includes `app/routers/vip.py` with `api_key_header` dependency.

### PRO routes (canonical-owned registration)

Anchor (stable): `app/main.py -> _register_paid_tier_routes(app)` delegates to centralized `pro_registration.register_pro_routes()`

Evidence:
- `app/main.py -> _register_paid_tier_routes()` — canonical bootstrap calls VIP
  registration before PRO registration and does not retain returned routers as
  compatibility attributes.
- `app/routers/pro_registration.py:55-161` — centralized registration +
  feature-flag gated `premium_week`.

Runtime effect:
- In normal runtime: includes `app/routers/pro.py`.
- `premium_week` is included only when enabled (`FEATURE_PREMIUM_WEEK_ENABLED` or VIP module enabled).

### Bayesian adherence + nutrition log + legacy alias (canonical-owned registration)

Anchor (stable): `app/main.py -> _include_nutrition_state_routers_if_needed(app)`

Evidence:
- `app/main.py` — `_include_nutrition_state_routers_if_needed(app)` registers
  the bounded nutrition/adherence state route family with
  `ensure_route_family_registered(...)`.
- `app/routers/bayes_adherence.py` — source route specs for Bayes adherence.
- `app/routers/nutrition_log.py` — source route specs for nutrition log.
- `app/routers/legacy_nutrition_alias.py` — hidden/deprecated legacy nutrition
  compatibility alias.

Runtime effect:
- Canonical bootstrap owns:
  - `app/routers/bayes_adherence.py`
  - `app/routers/nutrition_log.py`
  - `app/routers/legacy_nutrition_alias.py`
- Import-soft legacy behavior is removed for these routers. Missing modules or
  route-family drift now fail startup/bootstrap instead of creating a partial
  runtime.

### Shopping list generators (canonical bootstrap-owned)

Anchor (stable): `app/main.py -> _include_shopping_list_routers_if_needed(app)`

Evidence:
- `app/bootstrap/route_family.py` — shared `RouteMemberContract` and
  `ensure_route_family_registered(...)` guard for exact static route-family registration.
- `app/main.py` — `_include_shopping_list_routers_if_needed(app)` registers
  `shopping_list_pro_router` and `shoplist_day_router` as one `Shopping list`
  family with `require_pro_tier` as a required route-member dependency.
- `app/routers/shopping_list_pro.py` — owns the `POST /api/v1/pro/meal/shopping-list`
  handler and `SHOPPING_LIST_PRO_ROUTE_SPECS`.
- `app/routers/shoplist_day.py` — owns the iOS MVP `GET /api/v1/pro/shoplist/day`
  handler and `SHOPLIST_DAY_ROUTE_SPECS`.

Runtime effect:
- `POST /api/v1/pro/meal/shopping-list`
- `GET /api/v1/pro/shoplist/day`

OpenAPI effect:
- Source `APIRoute.include_in_schema` remains `True` for both routes.
- Canonical bootstrap validates idempotency, partial registration, duplicate/foreign
  handlers, method drift, OpenAPI visibility drift, and `require_pro_tier` dependency drift.
- `legacy_app.py` no longer imports or registers the shopping-list routers; the
  legacy growth guard rejects direct, aliased, module-qualified, dynamic,
  destructured, or walrus-style reintroduction.

### Insight endpoints (LLM) + providers wiring (legacy_app → llm → providers)

Anchor (stable): `legacy_app.py -> POST /api/v1/insight` and `POST /insight` call `llm.get_provider() -> provider.generate()`

Evidence:
- `legacy_app.py:2168-2187` — HTTP endpoints `/api/v1/insight` and `/insight`
- `legacy_app.py:2066-2076` + `2098-2117` — lazy `llm.get_provider()` + `provider.generate()`
- `llm.py:57-79` + `91-153` — provider selection (`LLM_PROVIDER`) + optional provider imports

### Canonical export rate limiting (route wrappers)

Anchor (stable): `app/routers/plan_export.py` and `app/routers/shoplist_export.py`
own the export handlers and their rate-limit wrappers.

Evidence:
- `app/routers/plan_export.py:383-385`, `481-483`, and `620-622` — canonical
  weekly CSV, weekly PDF, and export-sign routes declare 429 responses and use
  `@limit_if_available(RATE_LIMIT_EXPORTS)`.
- `app/routers/shoplist_export.py:282-314` — canonical shoplist and CSV/PDF
  export routes declare 429 responses and use
  `@limit_if_available(RATE_LIMIT_EXPORTS)`.
- `legacy_app.py` owns no export route; the former hidden premium export aliases
  are retired.

### Conditional routers: BMI Pro

Anchor (stable): `app/main.py -> app/routers/bmi_registration.py` owns BMI route registration; `legacy_app.py` remains a compatibility seam for unrelated direct-call shims only.

Evidence:
- `app/main.py -> ensure_canonical_app_bootstrap()`
- `app/routers/bmi_registration.py -> register_bmi_routes()`

- BMI Free: canonical `/api/v1/bmi/calculate` is registered by `app/main.py` via `app/routers/bmi_registration.py`
- BMI Pro: registered by `app/main.py` via `app/routers/bmi_registration.py`, included only if `FEATURE_BMI_PRO_ENABLED` is truthy
  - canonical: `/api/v1/pro/bmi`
  - legacy alias: `/api/v1/bmi/pro`

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

### Business route family (explicit feature flag, canonical-owned bootstrap)

Anchor (stable): `app/main.py -> _include_business_router_if_enabled(app)` owns
`app/routers/business.py`.

Evidence:
- `app/routers/business.py` defines `BUSINESS_ROUTE_SPECS`, source route
  handlers for `POST /api/v1/business/analyze` and
  `GET /api/v1/business/status`, and request-time feature checks through
  `app.utils.feature_flags.is_business_module_enabled()`.
- `app/utils/feature_flags.py` owns explicit-truthy parsing for
  `BUSINESS_MODULE_ENABLED`; unset, empty, and false-like values are disabled.
- `app/main.py -> _include_business_router_if_enabled(app)` registers the
  business family through `ensure_route_family_registered(...)` and
  `RouteMemberContract` only when the env var is explicitly truthy.
- `legacy_app.py` does not import or include `app.routers.business`; the legacy
  growth guard rejects direct, aliased, module-qualified, dynamic, and walrus
  business router re-registration there.

Runtime effect:
- Unset/default `BUSINESS_MODULE_ENABLED`: `/api/v1/business/*` is absent.
- Explicit truthy `BUSINESS_MODULE_ENABLED` (`1`, `true`, `yes`, `on`):
  `POST /api/v1/business/analyze` and `GET /api/v1/business/status` are
  routable exactly once through canonical bootstrap.
- Auth: `/api/v1/business/analyze` keeps the app API-key dependency;
  `/api/v1/business/status` remains unauthenticated when the route family is
  explicitly enabled.
- OpenAPI: the source routes keep current `include_in_schema=True` visibility,
  but the final public OpenAPI builder still filters `/api/v1/business/*` out
  of published `/openapi.json`; generated client/OpenAPI artifacts are expected
  to remain unchanged.

### Test router (canonical bootstrap-owned, non-production env)

Anchor (stable): `app/main.py -> _include_test_router_if_enabled(app)` owns
`app/routers/test.py`.

Evidence:
- `app/bootstrap/route_family.py:36` — shared `RouteMemberContract` for exact static
  route-family members.
- `app/bootstrap/route_family.py:138` — shared `ensure_route_family_registered(...)` guard.
- `app/routers/test.py` — owns `TEST_ROUTE_SPECS`, source route handlers, hidden
  `include_in_schema=False` metadata, and request-time `_ensure_non_production()`.
- `app/main.py` — registers the test route family only when
  `get_runtime_env_name()` resolves to `unset/local/dev/development/test/testing/ci`,
  or `staging` with exact `ENABLE_TEST_ROUTES=1`.
- `legacy_app.py` does not import or include `app.routers.test`; the legacy growth
  guard rejects direct, aliased, module-qualified, dynamic, and walrus
  re-registration there.

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
