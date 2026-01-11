# PR-510: legacy_app.py Audit

**Date:** 2026-01-11
**Status:** Analysis phase (no code changes)
**Goal:** Transform `legacy_app.py` into a pure compatibility-proxy by identifying orchestration/bootstrap logic that must be extracted.

---

## 1. Side-Effects at Import Time

### Module-Level Execution (on `import legacy_app`)

| Line Range | Code Block | Side-Effect | Impact | Code Evidence |
|------------|------------|-------------|--------|---------------|
| 1-94 | Imports (stdlib, fastapi, app modules) | Module loading, potential circular imports | Medium | `from app.routers.* import router as *` (lines 49-62) |
| 95-101 | `premium_week_router`, `pro_router` declarations | Module-level attributes created | Low | ```python<br>premium_week_router: Optional[APIRouter] = None<br>pro_router: Optional[APIRouter] = None<br>``` (lines 99-100) |
| 107-119 | Scheduler imports (try/except) | Conditional module loading | Low | ```python<br>try:<br>    from core.food_apis.scheduler import (<br>        start_background_updates as _scheduler_start_background_updates,<br>        stop_background_updates as _scheduler_stop_background_updates,<br>    )<br>except ImportError:<br>    async def _scheduler_start_background_updates(...): ...<br>``` (lines 107-118) |
| 128-138 | `Limiter` import (try/except) | Conditional middleware availability | Low | ```python<br>try:<br>    from slowapi import Limiter as _Limiter<br>    Limiter = _Limiter<br>except ImportError:<br>    Limiter = None<br>``` (lines 130-135) |
| 149-160 | VIP router registration setup | `_register_vip_routes` assignment, `VIP_MODULE_ENABLED` set | **High** | ```python<br>_register_vip_routes: Callable[[FastAPI], None] \| None = None<br>try:<br>    from app.routers.vip_registration import register_vip_routes<br>    from app.utils.feature_flags import is_vip_module_enabled<br>    _register_vip_routes = register_vip_routes<br>    VIP_MODULE_ENABLED = is_vip_module_enabled()<br>except ImportError:<br>    VIP_MODULE_ENABLED = False<br>``` (lines 151-160) |
| 162-169 | VIP router backward-compat | `vip_router` attribute set | Low | ```python<br>if VIP_MODULE_ENABLED:<br>    try:<br>        from app.routers import vip as _vip_mod<br>        vip_router = getattr(_vip_mod, "router", None)<br>    except ImportError:<br>        vip_router = None<br>``` (lines 163-169) |
| 57 | `_register_pro_routes` import | Router registration function imported | **High** | ```python<br>from app.routers.pro_registration import register_pro_routes as _register_pro_routes<br>``` (line 57) |
| 302 | Environment variable read (`_app_env`) | `APP_ENV`/`ENVIRONMENT` read at module level | **High** | ```python<br>_app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()<br>``` (line 302) |
| 515-833 | Lifespan handler definition | Database initialization logic defined | **High** | `@asynccontextmanager` function `lifespan()` (lines 515-833) contains `init_db()` call |
| 920 | FastAPI app creation | `app = FastAPI(...)` instantiated | **High** | ```python<br>app = FastAPI(<br>    title="PulsePlate",<br>    version="0.1.0",<br>    description=_api_description,<br>    ...<br>    lifespan=lifespan,<br>)<br>``` (line 920) |
| 1067-1102 | Router registration (at module bottom) | `app.include_router()` calls execute | **High** | Multiple `app.include_router()` calls (lines 1067-1102) |

### Critical Side-Effects

1. **Router Registration Logic** (lines 1067-1102):
   - **Code Evidence:**
     ```python
     # Line 1067-1073: Basic routers (always registered)
     app.include_router(foods_router)
     app.include_router(recipes_router)
     app.include_router(users_router)
     app.include_router(catalog_router)
     app.include_router(export_router, dependencies=[protected_dependency])
     app.include_router(plan_router, dependencies=[protected_dependency])
     app.include_router(shoplist_router, dependencies=[protected_dependency])

     # Line 1076-1077: VIP routes (conditional)
     if _register_vip_routes is not None:
         _register_vip_routes(app)

     # Line 1080: PRO routes (always called, but may return None in schema-only mode)
     pro_router, premium_week_router = _register_pro_routes(app)

     # Line 1083-1096: Optional routers (try/except)
     try:
         from app.routers import bayes_adherence
         app.include_router(bayes_adherence.router)
     except ImportError as e:
         logger.warning("Bayesian adherence router not loaded: %s", e)

     # Line 1099-1102: PRO shopping list routers (always)
     app.include_router(shopping_list_pro_router)
     app.include_router(shoplist_day_router)
     ```
   - **Impact:** OpenAPI schema generation depends on import-time router registration order. Order is: basic → VIP → PRO → optional → PRO shopping lists.

2. **Feature Flag Evaluation** (scattered):
   - **Code Evidence:**
     ```python
     # Line 157: VIP_MODULE_ENABLED set at import time
     VIP_MODULE_ENABLED = is_vip_module_enabled()  # Keep for backward compatibility

     # Line 5644-5647: FEATURE_BMI_PRO_ENABLED checked at module bottom
     _bmi_pro_flag = os.getenv("FEATURE_BMI_PRO_ENABLED")
     FEATURE_BMI_PRO_ENABLED = _is_truthy(_bmi_pro_flag) if _bmi_pro_flag is not None else False
     if FEATURE_BMI_PRO_ENABLED and bmi_pro_router:
         app.include_router(bmi_pro_router)

     # Line 5654-5657: BUSINESS_MODULE_ENABLED checked at module bottom
     _business_flag = os.getenv("BUSINESS_MODULE_ENABLED")
     BUSINESS_MODULE_ENABLED = _is_truthy(_business_flag) if _business_flag is not None else False
     if BUSINESS_MODULE_ENABLED and business_router:
         app.include_router(business_router)
     ```
   - **Impact:** Router availability determined before app creation. Feature flags evaluated at different times (VIP at top, BMI Pro/Business at bottom).

3. **Environment Variable Reads**:
   - **Code Evidence:**
     ```python
     # Line 302: APP_ENV/ENVIRONMENT read at module level
     _app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()

     # Line 1146-1148: Test router conditional on env
     if _app_env in {"", "local", "dev", "development", "test"} or (
         _app_env == "staging" and os.getenv("ENABLE_TEST_ROUTES") == "1"
     ):
         try:
             from app.routers import test as test_router
             app.include_router(test_router.router)
     ```
   - **Impact:** Test router inclusion depends on env vars at import time. Cannot change `APP_ENV` after import without reloading module.

---

## 2. Block Classification

| Block | Lines | Role | Status | Notes | Code Evidence |
|-------|-------|------|--------|-------|---------------|
| Imports (stdlib) | 1-30 | Compatibility | ✅ OK | Standard library imports | `from typing import ...` (lines 16-30) |
| Imports (app modules) | 49-94 | Compatibility | ✅ OK | Module imports | `from app.routers.* import router as *` (lines 49-62) |
| Router declarations | 95-101 | Compatibility | ✅ OK | Public surface for tests | ```python<br>premium_week_router: Optional[APIRouter] = None<br>pro_router: Optional[APIRouter] = None<br>``` (lines 99-100) |
| Scheduler fallback | 107-119 | Orchestration | ❌ DEBT | Should be in app lifecycle | `try/except ImportError` with fallback functions (lines 107-118) |
| Limiter fallback | 128-138 | Orchestration | ❌ DEBT | Should be in middleware setup | `try/except ImportError` with `Limiter = None` fallback (lines 130-135) |
| VIP registration setup | 149-160 | Orchestration | ❌ DEBT | Registration logic, not proxy | `_register_vip_routes` assignment and `VIP_MODULE_ENABLED` (lines 151-160) |
| PRO registration import | 57 | Orchestration | ❌ DEBT | Registration logic, not proxy | `from app.routers.pro_registration import register_pro_routes as _register_pro_routes` (line 57) |
| Helper functions | 172-400 | Feature logic | ❌ DEBT | BMI/planning helpers should be in core | `_resolve_scheduler_starter`, `_resolve_stop_callable`, `reset_targets_cache()` (lines 172-513) |
| FastAPI app creation | 920 | Orchestration | ❌ DEBT | App creation is orchestration | ```python<br>app = FastAPI(<br>    title="PulsePlate",<br>    version="0.1.0",<br>    ...<br>    lifespan=lifespan,<br>)<br>``` (line 920) |
| Middleware setup | 700-800+ | Orchestration | ❌ DEBT | Should be in app factory | Lifespan handler contains middleware-like logic (lines 515-833) |
| Router registration | 1067-1102 | Orchestration | ❌ DEBT | Should be in registration module | Multiple `app.include_router()` calls (lines 1067-1102) |
| Endpoint definitions | 1020-5657 | Feature logic | ❌ DEBT | Endpoints should be in routers | 32 `@app.get/post()` decorators (see endpoint table below) |
| Legacy aliases | 1107-1137 | Compatibility | ✅ OK | Backward-compat endpoints | `/api/nutrition/{date_str}` delegates to PRO (lines 1107-1137) |

---

## 3. Router Registration Map

### Current Registration Flow

```
import legacy_app
  ↓
Module-level imports execute (lines 1-94)
  ↓
Feature flags evaluated:
  - VIP_MODULE_ENABLED (line 157)
  - _app_env (line 302)
  ↓
Registration functions imported:
  - _register_vip_routes (line 153)
  - _register_pro_routes (line 57)
  ↓
FastAPI app created: app = FastAPI(...) (line 920)
  ↓
Lifespan handler defined (lines 515-833)
  ↓
Routers registered (scattered throughout file):
  - Basic routers (foods, recipes, users, catalog) - lines 1067-1070
  - Export/plan/shoplist routers - lines 1071-1073
  - VIP routes (via _register_vip_routes) - line 1076-1077
  - PRO routes (via _register_pro_routes) - line 1080
  - Optional routers (bayes_adherence, nutrition_log) - lines 1083-1096
  - PRO shopping lists - lines 1099-1102
  - Test router (conditional) - lines 1146-1155
  - Bodyfat router (conditional) - lines 5640-5641
  - BMI Pro router (conditional) - lines 5644-5647
  - BMI router (always) - line 5650
  - Business router (conditional) - lines 5654-5657
```

### Router Registration Details

| Router | Registration Method | Condition | Line | OpenAPI Impact | Code Evidence |
|--------|---------------------|-----------|------|----------------|---------------|
| `foods_router` | Direct `app.include_router()` | Always | 1067 | ✅ Always in schema | ```python<br>app.include_router(foods_router)<br>``` |
| `recipes_router` | Direct `app.include_router()` | Always | 1068 | ✅ Always in schema | ```python<br>app.include_router(recipes_router)<br>``` |
| `users_router` | Direct `app.include_router()` | Always | 1069 | ✅ Always in schema | ```python<br>app.include_router(users_router)<br>``` |
| `catalog_router` | Direct `app.include_router()` | Always | 1070 | ✅ Always in schema | ```python<br>app.include_router(catalog_router)<br>``` |
| `export_router` | Direct `app.include_router()` with deps | Always | 1071 | ✅ Always in schema | ```python<br>app.include_router(export_router, dependencies=[protected_dependency])<br>``` |
| `plan_router` | Direct `app.include_router()` with deps | Always | 1072 | ✅ Always in schema | ```python<br>app.include_router(plan_router, dependencies=[protected_dependency])<br>``` |
| `shoplist_router` | Direct `app.include_router()` with deps | Always | 1073 | ✅ Always in schema | ```python<br>app.include_router(shoplist_router, dependencies=[protected_dependency])<br>``` |
| VIP routes | `_register_vip_routes(app)` | `VIP_MODULE_ENABLED` | 1076-1077 | ⚠️ Conditional | ```python<br>if _register_vip_routes is not None:<br>    _register_vip_routes(app)<br>```<br>**Note:** `register_vip_routes()` checks `is_vip_module_enabled()` internally (see `app/routers/vip_registration.py:44`) |
| PRO routes | `_register_pro_routes(app)` | Always (imported) | 1080 | ⚠️ Conditional (schema-only mode) | ```python<br>pro_router, premium_week_router = _register_pro_routes(app)<br>```<br>**Note:** Returns `(None, None)` in schema-only mode (`PULSEPLATE_OPENAPI=1 AND APP_ENV=test AND ENVIRONMENT=test`) |
| `bayes_adherence.router` | Direct `app.include_router()` | Try/except ImportError | 1083-1088 | ⚠️ Conditional (module availability) | ```python<br>try:<br>    from app.routers import bayes_adherence<br>    app.include_router(bayes_adherence.router)<br>except ImportError as e:<br>    logger.warning("Bayesian adherence router not loaded: %s", e)<br>``` |
| `nutrition_log.router` | Direct `app.include_router()` | Try/except ImportError | 1091-1096 | ⚠️ Conditional (module availability) | ```python<br>try:<br>    from app.routers import nutrition_log<br>    app.include_router(nutrition_log.router)<br>except ImportError as e:<br>    logger.warning("Nutrition log router not loaded: %s", e)<br>``` |
| `shopping_list_pro_router` | Direct `app.include_router()` | Always | 1099 | ✅ Always in schema | ```python<br>app.include_router(shopping_list_pro_router)<br>``` |
| `shoplist_day_router` | Direct `app.include_router()` | Always | 1102 | ✅ Always in schema | ```python<br>app.include_router(shoplist_day_router)<br>``` |
| Premium week | Via `_register_pro_routes()` | `FEATURE_PREMIUM_WEEK_ENABLED` OR `VIP_MODULE_ENABLED` | 1080 (inside pro_registration) | ⚠️ Conditional | **Note:** Premium week router is registered inside `register_pro_routes()` if feature flag enabled (see `app/routers/pro_registration.py:90-104`) |
| Test router | Direct `app.include_router()` | Env-based (`_app_env` check) | 1146-1155 | ⚠️ Conditional | ```python<br>if _app_env in {"", "local", "dev", "development", "test"} or (<br>    _app_env == "staging" and os.getenv("ENABLE_TEST_ROUTES") == "1"<br>):<br>    try:<br>        from app.routers import test as test_router<br>        app.include_router(test_router.router)<br>``` |
| Bodyfat router | Direct `app.include_router()` | `get_bodyfat_router is not None` | 5640-5641 | ⚠️ Conditional | ```python<br>if get_bodyfat_router is not None:<br>    app.include_router(get_bodyfat_router(), prefix="/api/v1")<br>``` |
| BMI Pro | Direct `app.include_router()` | `FEATURE_BMI_PRO_ENABLED` AND `bmi_pro_router` | 5644-5647 | ⚠️ Conditional | ```python<br>_bmi_pro_flag = os.getenv("FEATURE_BMI_PRO_ENABLED")<br>FEATURE_BMI_PRO_ENABLED = _is_truthy(_bmi_pro_flag) if _bmi_pro_flag is not None else False<br>if FEATURE_BMI_PRO_ENABLED and bmi_pro_router:<br>    app.include_router(bmi_pro_router)<br>``` |
| `bmi_router` | Direct `app.include_router()` | Always | 5650 | ✅ Always in schema | ```python<br>app.include_router(bmi_router)<br>``` |
| Business router | Direct `app.include_router()` | `BUSINESS_MODULE_ENABLED` AND `business_router` | 5654-5657 | ⚠️ Conditional | ```python<br>_business_flag = os.getenv("BUSINESS_MODULE_ENABLED")<br>BUSINESS_MODULE_ENABLED = _is_truthy(_business_flag) if _business_flag is not None else False<br>if BUSINESS_MODULE_ENABLED and business_router:<br>    app.include_router(business_router)<br>``` |

### Registration Inconsistencies

1. **VIP vs PRO Pattern Mismatch**:
   - **VIP:** Uses centralized `_register_vip_routes()` function (line 1076-1077)
   - **PRO:** Uses centralized `_register_pro_routes()` function (line 1080)
   - **Premium week:** Registered inside `register_pro_routes()` (centralized, but nested)
   - **BMI Pro:** Direct `app.include_router()` (line 5647) - **INCONSISTENT**
   - **Business:** Direct `app.include_router()` (line 5657) - **INCONSISTENT**
   - **Test:** Direct `app.include_router()` (line 1152) - **INCONSISTENT**
   - **Bodyfat:** Direct `app.include_router()` (line 5641) - **INCONSISTENT**

2. **Conditional Logic Scattered**:
   - Feature flags checked in multiple places:
     - `VIP_MODULE_ENABLED` at top (line 157)
     - `FEATURE_BMI_PRO_ENABLED` at bottom (line 5644)
     - `BUSINESS_MODULE_ENABLED` at bottom (line 5654)
     - `FEATURE_PREMIUM_WEEK_ENABLED` inside `pro_registration.py` (not in legacy_app)
     - `_app_env` for test router (line 1146)
   - **No single source of truth** for router availability

3. **OpenAPI Schema-Only Mode**:
   - **PRO routes** respect `PULSEPLATE_OPENAPI=1` guard (in `pro_registration.py:26-35`)
   - **Other routers** do not have schema-only guards
   - **Code Evidence:**
     ```python
     # app/routers/pro_registration.py:26-35
     def _is_openapi_schema_only_mode() -> bool:
         _openapi_flag = (os.getenv("PULSEPLATE_OPENAPI") or "").strip()
         _app_env = (os.getenv("APP_ENV") or "").strip().lower()
         _env = (os.getenv("ENVIRONMENT") or "").strip().lower()
         return (_openapi_flag == "1") and (_app_env == "test") and (_env == "test")
     ```
   - **Impact:** Schema generation may include routers that shouldn't be in schema-only mode (e.g., BMI Pro, Business, Test router)

---

## 4. OpenAPI Generation Impact

### Does `legacy_app.py` Participate in Schema Generation?

**Yes**, in multiple ways:

1. **Router Registration Order**:
   - **Code Evidence:** Routers registered at module level (lines 1067-1102, 1146-1155, 5640-5657)
   - **Order affects OpenAPI `paths` ordering:**
     ```
     1. Basic routers (foods, recipes, users, catalog) - lines 1067-1070
     2. Protected routers (export, plan, shoplist) - lines 1071-1073
     3. VIP routes - line 1076-1077
     4. PRO routes - line 1080
     5. Optional routers (bayes, nutrition_log) - lines 1083-1096
     6. PRO shopping lists - lines 1099-1102
     7. Test router - lines 1146-1155
     8. Bodyfat router - lines 5640-5641
     9. BMI Pro - lines 5644-5647
     10. BMI router - line 5650
     11. Business router - lines 5654-5657
     ```
   - **Evidence:** `scripts/generate_openapi.py:119` imports `app.main.app`, which imports `legacy_app.app` (line 11 of `app/main.py`)

2. **Conditional Router Inclusion**:
   - Feature flags determine which routers are registered
   - Schema-only mode (`PULSEPLATE_OPENAPI=1`) affects PRO routes only
   - **Code Evidence:**
     ```python
     # PRO routes respect schema-only mode
     # app/routers/pro_registration.py:62-75
     openapi_mode = _is_openapi_schema_only_mode()
     if not openapi_mode:
         # Import and register routers
     else:
         # Return (None, None) - routers not registered

     # Other routers do NOT respect schema-only mode
     # legacy_app.py:5644-5647
     if FEATURE_BMI_PRO_ENABLED and bmi_pro_router:
         app.include_router(bmi_pro_router)  # Always registered if flag enabled
     ```

3. **Endpoint Definitions**:
   - Many endpoints defined directly in `legacy_app.py` (32 endpoints, see table below)
   - These appear in OpenAPI schema
   - **Code Evidence:** FastAPI auto-generates schema from `@app.get/post()` decorators
   - **All endpoints are included in schema**, regardless of schema-only mode

### Runtime vs Schema-Only Differences

| Aspect | Runtime | Schema-Only Mode | Code Evidence |
|--------|---------|-------------------|--------------|
| PRO routes | Registered via `_register_pro_routes()` | Skipped (returns `None, None`) | `app/routers/pro_registration.py:62-75` - checks `openapi_mode` |
| Premium week routes | Registered if feature flag enabled | Registered if feature flag enabled | **No schema-only guard** - registered inside `register_pro_routes()` if not in schema-only mode |
| VIP routes | Registered if `VIP_MODULE_ENABLED` | Registered if `VIP_MODULE_ENABLED` | **No schema-only guard** - `register_vip_routes()` doesn't check schema-only mode |
| BMI Pro routes | Registered if `FEATURE_BMI_PRO_ENABLED` | Registered if `FEATURE_BMI_PRO_ENABLED` | **No schema-only guard** - `legacy_app.py:5644-5647` |
| Business routes | Registered if `BUSINESS_MODULE_ENABLED` | Registered if `BUSINESS_MODULE_ENABLED` | **No schema-only guard** - `legacy_app.py:5654-5657` |
| Test router | Registered if env allows | Registered if env allows | **No schema-only guard** - `legacy_app.py:1146-1155` |
| Endpoint definitions | All included | All included (no guard) | **No schema-only guard** - all `@app.get/post()` decorators execute at import time |

**Problem:** Schema-only mode only affects PRO routes, not other conditional routers or endpoint definitions. This means schema generation may include routers/endpoints that import SQLAlchemy models at module level, potentially causing "Table already defined" errors.

---

## 5. Endpoint Status Map

### Endpoints Defined in `legacy_app.py`

| Endpoint | Method | Path | Status | Condition | Line | Code Evidence |
|----------|--------|------|--------|-----------|------|---------------|
| Admin status | GET | `/api/v1/admin/status` | ✅ Active | API key required | 1020 | ```python<br>@app.get("/api/v1/admin/status", dependencies=[Depends(_get_api_key_dynamic)])<br>async def admin_status() -> Dict[str, str]:<br>``` |
| Legacy nutrition | GET | `/api/nutrition/{date_str}` | ✅ Active (shim) | API key required | 1107 | ```python<br>@app.get("/api/nutrition/{date_str}", tags=["pro", "legacy"])<br>async def get_daily_nutrition_legacy(...):<br>    # Delegates to app.routers.pro.get_daily_nutrition<br>``` |
| Database health | GET | `/health/db` | ✅ Active | Always | 1302 | ```python<br>@app.get("/health/db")<br>async def database_health(session: Session = Depends(get_session)):<br>``` |
| Readiness probe | GET | `/ready` | ✅ Active | Always (excluded from schema) | 1325 | ```python<br>@app.get("/ready", include_in_schema=False)<br>async def ready(session: Session = Depends(get_session)):<br>``` |
| Root | GET | `/` | ✅ Active | Always | 1677 | ```python<br>@app.get("/")<br>async def root(request: Request) -> HTMLResponse:<br>``` |
| Favicon | GET | `/favicon.ico` | ✅ Active | Always | 1906 | ```python<br>@app.get("/favicon.ico")<br>async def favicon() -> Response:<br>    return Response(status_code=204)<br>``` |
| Health check | GET | `/health` | ✅ Active | Always | 1951 | ```python<br>@app.get("/health")<br>async def health() -> Dict[str, Any]:<br>``` |
| Health check v1 | GET | `/api/v1/health` | ✅ Active | Always | 1980 | ```python<br>@app.get("/api/v1/health")<br>async def health_v1() -> Dict[str, Any]:<br>    return await health()<br>``` |
| Privacy policy | GET | `/privacy` | ✅ Active | Always | 1989 | ```python<br>@app.get("/privacy")<br>async def privacy() -> Dict[str, Any]:<br>``` |
| Admin logs cleanup | POST | `/admin/logs/cleanup` | ✅ Active | API key required | 2048 | ```python<br>@app.post("/admin/logs/cleanup", dependencies=[Depends(_get_api_key_dynamic)])<br>async def cleanup_expired_logs(...):<br>``` |
| BMI legacy | POST | `/bmi` | ✅ Active (shim) | Always | 2097 | ```python<br>@app.post("/bmi")<br>async def bmi_endpoint(req: BMIRequest) -> Dict[str, Any]:<br>    # Delegates to app.routers.bmi.bmi_calculate_handler<br>``` |
| Plan legacy | POST | `/plan` | ✅ Active (shim) | Always | 2209 | ```python<br>@app.post("/plan")<br>async def plan_endpoint(req: BMIRequest) -> Dict[str, Any]:<br>    # Delegates to app.routers.bmi.bmi_calculate_handler<br>``` |
| BMI v1 | POST | `/api/v1/bmi` | ✅ Active (shim) | Always | 2316 | ```python<br>@app.post("/api/v1/bmi")<br>async def bmi_endpoint_v1(req: BMIRequestV1) -> Dict[str, Any]:<br>    # Delegates to app.routers.bmi.bmi_calculate_handler<br>``` |
| Insight v1 | POST | `/api/v1/insight` | ⚠️ Conditional | `FEATURE_INSIGHT` flag | 2443 | ```python<br>@app.post("/api/v1/insight", dependencies=[Depends(_get_api_key_dynamic)])<br>async def insight_v1(req: InsightRequest):<br>    flag_value = os.getenv("FEATURE_INSIGHT", "false")<br>    if not _is_truthy(flag_value):<br>        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")<br>``` |
| Insight legacy | POST | `/insight` | ⚠️ Conditional | `FEATURE_INSIGHT` flag | 2486 | ```python<br>@app.post("/insight")<br>async def insight(req: InsightRequest):<br>    # Same logic as insight_v1<br>``` |
| Premium plate | POST | `/api/v1/premium/plate` | ⚠️ Conditional | `FEATURE_PREMIUM_NUTRITION` flag | 3979 | ```python<br>@app.post("/api/v1/premium/plate", ...)<br>async def api_premium_plate(req: PlateRequest):<br>    if str(os.getenv("FEATURE_PREMIUM_NUTRITION", "")).strip().lower() not in {"1", "true", "on", "yes"}:<br>        raise HTTPException(status_code=503, detail="Enhanced plate feature not available")<br>``` |
| Premium plate flexible | POST | `/api/v1/premium/plate-flexible` | ⚠️ Conditional | `FEATURE_PREMIUM_NUTRITION` flag | 4147 | Similar runtime check as above |
| Premium BMR | POST | `/premium_bmr` | ✅ Active | Always | 4330 | ```python<br>@app.post("/premium_bmr")<br>async def premium_bmr(...):<br>``` |
| Premium targets legacy | POST | `/premium_targets` | ✅ Active | API key required | 4653 | ```python<br>@app.post("/premium_targets", dependencies=[Depends(_get_api_key_dynamic)])<br>async def premium_targets_legacy(req: WHOTargetsRequest):<br>``` |
| WHO targets | POST | `/api/v1/premium/targets` | ✅ Active | API key required | 4684 | ```python<br>@app.post("/api/v1/premium/targets", ...)<br>async def api_who_targets(payload: Dict[str, Any] = Body(...)):<br>``` |
| Weekly menu | POST | `/api/v1/premium/plan/week` | ⚠️ Conditional | `VIP_MODULE_ENABLED` flag | 4705 | ```python<br>@app.post("/api/v1/premium/plan/week", ...)<br>async def api_weekly_menu(req: WeekPlanRequest):<br>    _vip_env = os.getenv("VIP_MODULE_ENABLED")<br>    if _vip_env is not None and _vip_env.strip().lower() not in {"1", "true", "on", "yes"}:<br>        raise HTTPException(status_code=503, detail="VIP module is disabled")<br>    if _vip_env is None and not VIP_MODULE_ENABLED:<br>        raise HTTPException(status_code=503, detail="VIP module is disabled")<br>``` |
| Weekly menu flexible | POST | `/api/v1/premium/plan/week-flexible` | ⚠️ Conditional | `VIP_MODULE_ENABLED` flag | 4840 | Similar runtime check as above |
| Debug env | GET | `/debug_env` | ⚠️ Conditional | Env-based (non-production) | 4930 | ```python<br>@app.get("/debug_env")<br>async def debug_env() -> JSONResponse:<br>    allowed_envs = {"", "local", "dev", "development", "test"}<br>    debug_flag = _is_truthy(os.getenv("ENABLE_DEBUG_ENDPOINT"))<br>    if os.getenv("APP_ENV", "").strip().lower() not in allowed_envs and not debug_flag:<br>        raise HTTPException(status_code=404, detail="Not found")<br>``` |
| DB status | GET | `/api/v1/admin/db-status` | ✅ Active | API key required | 4953 | ```python<br>@app.get("/api/v1/admin/db-status", dependencies=[Depends(_get_api_key_dynamic)])<br>async def get_database_status() -> JSONResponse:<br>``` |
| Force update | POST | `/api/v1/admin/force-update` | ✅ Active | API key required | 4980 | ```python<br>@app.post("/api/v1/admin/force-update", dependencies=[Depends(_get_api_key_dynamic)])<br>async def force_database_update(source: Optional[str] = None):<br>``` |
| Check updates | GET | `/api/v1/admin/check-updates` | ✅ Active | API key required | 5025 | ```python<br>@app.get("/api/v1/admin/check-updates", dependencies=[Depends(_get_api_key_dynamic)])<br>async def check_database_updates():<br>``` |
| Rollback | POST | `/api/v1/admin/rollback` | ✅ Active | API key required | 5078 | ```python<br>@app.post("/api/v1/admin/rollback", dependencies=[Depends(_get_api_key_dynamic)])<br>async def rollback_database_update():<br>``` |
| Export day CSV | GET | `/api/v1/premium/exports/day/{plan_id}.csv` | ⚠️ Conditional | `EXPORTS_ENABLED` flag | 5193 | ```python<br>if EXPORTS_ENABLED:<br>    @app.get("/api/v1/premium/exports/day/{plan_id}.csv", ...)<br>    async def export_daily_plan_csv(plan_id: str):<br>``` |
| Export PDF generic | POST | `/api/v1/export/pdf` | ⚠️ Conditional | `EXPORTS_ENABLED` flag | 5276 | ```python<br>if EXPORTS_ENABLED:<br>    @app.post("/api/v1/export/pdf", ...)<br>    async def export_pdf_generic(payload: Dict[str, Any]):<br>``` |
| Export day PDF | GET | `/api/v1/premium/exports/day/{plan_id}.pdf` | ⚠️ Conditional | `EXPORTS_ENABLED` flag | 5439 | ```python<br>if EXPORTS_ENABLED:<br>    @app.get("/api/v1/premium/exports/day/{plan_id}.pdf", ...)<br>    async def export_daily_plan_pdf(plan_id: str):<br>``` |
| Export week PDF | GET | `/api/v1/premium/exports/week/{plan_id}.pdf` | ⚠️ Conditional | `EXPORTS_ENABLED` flag | 5524 | ```python<br>if EXPORTS_ENABLED:<br>    @app.get("/api/v1/premium/exports/week/{plan_id}.pdf", ...)<br>    async def export_weekly_plan_pdf(plan_id: str):<br>``` |

### Endpoint Classification Summary

- **✅ Always Active (18 endpoints):** Health checks, admin endpoints, legacy BMI/plan shims, premium BMR/targets
- **⚠️ Conditionally Active (14 endpoints):** Feature-flagged endpoints (insight, premium nutrition, weekly menu, exports), env-gated (debug_env)
- **Total:** 32 endpoints defined directly in `legacy_app.py`

---

## 6. Responsibility Boundaries

### ✅ MUST REMAIN in `legacy_app.py` (Compatibility-Proxy)

1. **Public Surface Attributes**:
   - **Code Evidence:**
     ```python
     # Lines 99-100
     premium_week_router: Optional[APIRouter] = None
     pro_router: Optional[APIRouter] = None

     # Lines 139, 163-169
     vip_router: Optional[APIRouter] = None
     if VIP_MODULE_ENABLED:
         try:
             from app.routers import vip as _vip_mod
             vip_router = getattr(_vip_mod, "router", None)
         except ImportError:
             vip_router = None
     ```
   - **Reason:** Tests and `app/__init__.py` expect these via `hasattr()` and `patch()`
   - **Evidence:** `tests/test_coverage_boost_simple_97.py:135` uses `patch("legacy_app.premium_week_router", None)`

2. **Legacy Endpoint Aliases**:
   - **Code Evidence:**
     ```python
     # Line 1107-1137: Legacy nutrition endpoint
     @app.get("/api/nutrition/{date_str}", tags=["pro", "legacy"])
     async def get_daily_nutrition_legacy(...):
         """Legacy alias for iOS nutrition endpoint - redirects to PRO endpoint."""
         from app.routers.pro import get_daily_nutrition
         response = await get_daily_nutrition(...)
         return response.model_dump()

     # Line 2097-2143: Legacy BMI endpoint
     @app.post("/bmi")
     async def bmi_endpoint(req: BMIRequest):
         """Shim endpoint. Delegates to canonical handler."""
         from app.routers.bmi import bmi_calculate_handler
         canonical_result = await bmi_calculate_handler(canonical_req)
         # ... legacy response mapping ...

     # Line 2209-2306: Legacy plan endpoint
     @app.post("/plan")
     async def plan_endpoint(req: BMIRequest):
         """Legacy endpoint /plan. Delegates to canonical BMI engine."""
         from app.routers.bmi import bmi_calculate_handler
         canonical = await bmi_calculate_handler(bmi_payload)
         # ... legacy response mapping ...
     ```
   - **Reason:** iOS/legacy clients depend on these paths (`/api/nutrition/{date}`, `/bmi`, `/plan`)

3. **Re-exports** (if any):
   - Currently no explicit re-exports, but `app/__init__.py` uses PEP 562 forwarding to `legacy_app`
   - **Reason:** External code may import from `legacy_app` directly

### ❌ MUST BE EXTRACTED (Orchestration/Bootstrap)

1. **App Creation**:
   - **Code Evidence:**
     ```python
     # Line 920-933
     app = FastAPI(
         title="PulsePlate",
         version="0.1.0",
         description=_api_description,
         contact={...},
         license_info={...},
         openapi_tags=tags_metadata,
         lifespan=lifespan,
     )
     ```
   - **Target:** `app/main.py` or `app/factory.py`
   - **Note:** `app/main.py` already exists but just re-exports `legacy_app.app` (line 11)

2. **Router Registration**:
   - **Code Evidence:** All `app.include_router()` calls (lines 1067-1102, 1146-1155, 5640-5657)
   - **Target:** `app/routers/registration.py` (unified registration module)

3. **Middleware Setup**:
   - **Code Evidence:** Lifespan handler contains middleware-like logic (lines 515-833)
   - **Target:** `app/middleware/setup.py` or app factory

4. **Feature Flag Evaluation**:
   - **Code Evidence:**
     ```python
     # Line 157: VIP_MODULE_ENABLED
     VIP_MODULE_ENABLED = is_vip_module_enabled()

     # Line 302: _app_env
     _app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()

     # Line 5644-5645: FEATURE_BMI_PRO_ENABLED
     _bmi_pro_flag = os.getenv("FEATURE_BMI_PRO_ENABLED")
     FEATURE_BMI_PRO_ENABLED = _is_truthy(_bmi_pro_flag) if _bmi_pro_flag is not None else False

     # Line 5654-5655: BUSINESS_MODULE_ENABLED
     _business_flag = os.getenv("BUSINESS_MODULE_ENABLED")
     BUSINESS_MODULE_ENABLED = _is_truthy(_business_flag) if _business_flag is not None else False

     # Line 5185-5189: EXPORTS_ENABLED
     _export_feature_flag = os.getenv("FEATURE_EXPORTS_ENABLED")
     EXPORTS_ENABLED = _is_truthy(_export_feature_flag) if _export_feature_flag is not None else False
     ```
   - **Target:** `app/utils/feature_flags.py` (already exists, but needs cleanup)

5. **Conditional Imports**:
   - **Code Evidence:** Multiple `try/except ImportError` blocks (scheduler, limiter, bayes_adherence, nutrition_log, test router, bodyfat)
   - **Target:** Lazy imports in registration functions

6. **Helper Functions**:
   - **Code Evidence:** `_resolve_scheduler_starter`, `_resolve_stop_callable`, `reset_targets_cache()`, `_validate_fallback_url()`, `_configure_session_bindings()`, etc. (lines 172-513)
   - **Target:** `core/bmi/` or `core/planning/` or `app/bootstrap/`

7. **Endpoint Definitions**:
   - **Code Evidence:** 32 `@app.get/post()` decorators (see endpoint table above)
   - **Target:** Move to appropriate routers (`app/routers/*.py`)

---

## 7. Problem Statement

### Why `legacy_app.py` ≠ Compatibility-Proxy Currently

1. **Orchestration Logic Mixed with Proxy**:
   - App creation, router registration, and middleware setup all happen in the same file
   - **Code Evidence:**
     - App creation: line 920
     - Router registration: lines 1067-1102, 1146-1155, 5640-5657
     - Middleware/lifespan: lines 515-833
   - No separation between "what legacy needs" and "how app is built"

2. **Feature Logic Embedded**:
   - Endpoint implementations directly in `legacy_app.py` (32 endpoints)
   - Business logic mixed with compatibility layer
   - **Code Evidence:** All endpoint definitions (lines 1020-5657) contain business logic, not just delegation

3. **Import-Time Side-Effects**:
   - Feature flags evaluated at import time
   - Routers registered at module level
   - **Code Evidence:**
   - `VIP_MODULE_ENABLED` set at line 157 (during import)
   - `_app_env` read at line 302 (during import)
   - Routers registered at lines 1067-1102 (during import, after app creation)
   - **Impact:** Cannot import `legacy_app` without triggering full app initialization

4. **Inconsistent Registration Patterns**:
   - Some routers use centralized registration (VIP, PRO)
   - Others use direct `app.include_router()` calls
   - **Code Evidence:**
     - VIP: `_register_vip_routes(app)` (line 1076-1077)
     - PRO: `_register_pro_routes(app)` (line 1080)
     - BMI Pro: `app.include_router(bmi_pro_router)` (line 5647) - **INCONSISTENT**
     - Business: `app.include_router(business_router)` (line 5657) - **INCONSISTENT**
   - **Impact:** Hard to reason about router availability and OpenAPI schema

5. **OpenAPI Generation Coupling**:
   - Schema generation depends on import-time router registration
   - Schema-only mode only partially implemented
   - **Code Evidence:**
     - `scripts/generate_openapi.py:119` imports `app.main.app`
     - `app/main.py:11` imports `legacy_app.app`
     - Only PRO routes respect schema-only mode (`pro_registration.py:26-35`)
     - Other routers/endpoints have no schema-only guard
   - **Impact:** Non-deterministic schema generation (partially fixed in PR-508, but only for PRO routes)

---

## 8. Scope for Next Code-PR (PR-511)

### Phase 1: Extract Orchestration (Minimal Diff)

1. **Create `app/main.py`** (already exists, but needs refactoring):
   - Move `app = FastAPI(...)` creation from `legacy_app.py:920`
   - Move middleware setup from lifespan handler
   - Keep `legacy_app.py` as re-export: `from app.main import app`

2. **Create `app/routers/registration.py`**:
   - Unified router registration function
   - Single source of truth for router availability
   - Respects feature flags and schema-only mode
   - Consolidates all `app.include_router()` calls

3. **Update `legacy_app.py`**:
   - Remove orchestration logic
   - Keep only compatibility-proxy code (public attributes, legacy endpoint aliases)
   - Re-export `app` from `app.main`

### Phase 2: Extract Feature Logic (Follow-up)

1. Move endpoint definitions to routers
2. Move helper functions to `core/`
3. Clean up feature flag evaluation

### Out of Scope for PR-510/511

- Refactoring for "cleanliness"
- Moving logic "while we're at it"
- BMI/VIP/Weekly logic changes
- Gradio/AI-lab changes
- OpenAPI improvements (only document consequences)

---

## 9. Dependencies and Risks

### Dependencies

- PR-508 (OpenAPI determinism) - **DONE**
- PR-509 (Full schema generation) - **PENDING**

### Risks

1. **Breaking Changes**:
   - Tests that import `legacy_app` directly may break
   - External code importing from `legacy_app` may break
   - **Mitigation:** Keep public surface stable, use re-exports

2. **Import Order Issues**:
   - Circular imports if orchestration moved incorrectly
   - **Mitigation:** Use lazy imports, PEP 562 forwarding

3. **OpenAPI Schema Changes**:
   - Router registration order may change
   - **Mitigation:** Explicit ordering in registration module

---

## 10. Success Criteria

### PR-510 (Analysis) ✅

- [x] Side-effects documented with code evidence
- [x] Block classification complete with line numbers
- [x] Router registration map created with conditions
- [x] OpenAPI impact analyzed with evidence
- [x] Endpoint status map created (32 endpoints)
- [x] Responsibility boundaries defined with code references
- [x] Problem statement clear with evidence
- [x] Scope for next PR defined

### PR-511 (Code) - Future

- [ ] `legacy_app.py` contains only compatibility-proxy code
- [ ] Orchestration moved to `app/main.py` and `app/routers/registration.py`
- [ ] All tests pass
- [ ] OpenAPI schema generation unchanged (deterministic)
- [ ] No breaking changes to public surface

---

## 11. Notes

- This audit is **analysis-only**. No code changes in PR-510.
- Focus is on **identifying what must move**, not **how to move it**.
- Next PR (PR-511) will implement the extraction with minimal diff.
- PR-512+ will handle feature logic extraction (endpoints, helpers).
