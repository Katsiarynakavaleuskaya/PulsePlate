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
- Most route registration currently happens in `legacy_app.py`.

## Router registration: always-on vs conditional

### Always-on routers (registered unconditionally)

Anchor (stable): `legacy_app.py -> include_router(...) for core API routers`

Evidence: `legacy_app.py:811-820`

- `foods_router` (`app/routers/foods.py`)
- `recipes_router` (`app/routers/recipes.py`)
- `users_router` (`app/routers/users.py`)
- `catalog_router` (`app/routers/catalog.py`)
- `export_router` (`app/routers/shoplist_export.py`) — included with `dependencies=[Depends(_get_api_key_dynamic)]`
- `plan_router` (`app/routers/plan_export.py`) — included with `dependencies=[Depends(_get_api_key_dynamic)]`
- `shoplist_router` (`app/routers/shoplist_export.py`) — included with `dependencies=[Depends(_get_api_key_dynamic)]`

### VIP routes (feature-flag gated, centralized)

Anchor (stable): `legacy_app.py -> register_vip_routes(app)` and `vip_registration.register_vip_routes()`

Evidence:
- `legacy_app.py:822-825` — calls VIP registration if available
- `app/routers/vip_registration.py:23-58` — central function + `is_vip_module_enabled()` gate

Runtime effect:
- When VIP module is enabled, `vip_registration.register_vip_routes()` includes `app/routers/vip.py` with `api_key_header` dependency.

### PRO routes (centralized; schema-only OpenAPI can short-circuit)

Anchor (stable): `legacy_app.py -> register_pro_routes(app)` and schema-only short-circuit in `pro_registration`

Evidence:
- `legacy_app.py:826-828` — `pro_router, premium_week_router = _register_pro_routes(app)`
- `app/routers/pro_registration.py:26-36` — schema-only guard conditions
- `app/routers/pro_registration.py:76-105` — avoids importing PRO/premium routers in schema-only mode

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

### Conditional routers: Bodyfat / BMI Pro / Business

Anchor (stable): `legacy_app.py -> feature-flag gated routers (BMI Pro, Business) + optional bodyfat`

Evidence: `legacy_app.py:5226-5248`

- Bodyfat: included if router factory is available (`get_bodyfat_router`)
- BMI Pro: included only if `FEATURE_BMI_PRO_ENABLED` is truthy
  - canonical: `/api/v1/pro/bmi`
  - legacy alias: `/api/v1/bmi/pro`
- Business: included only if `BUSINESS_MODULE_ENABLED` is truthy

### Test router (non-production env)

Anchor (stable): `legacy_app.py -> include test router only in non-prod env`

Evidence: `legacy_app.py:890-902`

- Included only in local/dev/test (or staging with explicit `ENABLE_TEST_ROUTES=1`)

## OpenAPI generation behavior (important)

**Schema-only OpenAPI contract (single source of truth):**
See: `docs/architecture/ADR-002-openapi-schema-only-mode.md#schema-only-openapi-contract`

**Evidence (implementation):**

- Generator sets schema-only mode and pins env/feature flags:
  - `scripts/generate_openapi.py:94-135`
- PRO router registration honors schema-only mode to prevent ORM import hazards:
  - `app/routers/pro_registration.py:26-36` and `76-105`

## Maintenance rule

Checklist (lightweight):
- [ ] If you add/remove a router or change a feature flag / tier gate: update this doc **or** state “no routing-doc update needed” in the PR description.
- [ ] If you change OpenAPI output: regenerate and commit `frontend/src/api/openapi.json` + `schema.ts` (in the runtime PR that changes behavior).
