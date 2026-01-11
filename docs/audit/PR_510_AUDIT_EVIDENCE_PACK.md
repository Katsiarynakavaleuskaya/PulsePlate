# PR-510: Audit Evidence Pack

**Date:** 2026-01-11
**Branch:** `fix/openapi-determinism`
**Commit:** `48cd4429 docs(audit): add PR-510 legacy_app.py analysis`

> **Note:** Line numbers are best-effort at time of audit; prefer searching by symbols/strings like `app.include_router(`, `_register_*`, `normalize_openapi_schema`, etc.

---

## 0. Facts & Identifiers

### 0.1 Git Status
- **Branch:** `fix/openapi-determinism`
- **Commit SHA:** `48cd4429`
- **File:** `legacy_app.py` (5658 lines)

### 0.2 CI OpenAPI Determinism Check
- **Job:** `openapi-sync` (`.github/workflows/ci.yml:94-120`)
- **Makefile target:** `openapi-check` (line 307) → depends on `openapi` (line 293)
- **Script:** `scripts/generate_openapi.py` (called via `make openapi`)
- **Check:** `git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts` (`.github/workflows/frontend-ci.yml:80`)

### 0.3 Schema-Only Mode Usage
- **When:**
  - ✅ CI: `openapi-sync` job sets `PULSEPLATE_OPENAPI=1`, `APP_ENV=test`, `ENVIRONMENT=test` (`.github/workflows/ci.yml:99-100`)
  - ✅ Local: `scripts/generate_openapi.py:98-106` sets same env vars
- **Purpose:**
  1. Prevent SQLAlchemy "Table already defined" errors during schema generation (ORM import flake prevention)
  2. Act as **public schema hygiene boundary** (exclude sensitive routes like admin/test endpoints from public `/openapi.json`)
- **Evidence:** `scripts/generate_openapi.py:97-112` explicitly disables feature flags that import ORM models

### 0.4 Runtime Environment Variables (Production)
- **APP_ENV:** Unknown (not set in CI config for production)
- **ENVIRONMENT:** Unknown (not set in CI config for production)
- **Note:** Production values not visible in codebase; CI uses `test` for schema generation

### 0.5 Known Flakes/Errors
- **"Table already defined" errors:**
  - ✅ Documented in `scripts/generate_openapi.py:97` (prevented by schema-only mode)
  - ✅ Documented in `app/routers/pro_registration.py:79` (comment explains why PRO routes skip in schema-only)
  - ✅ Referenced in `docs/audit/PR_510_legacy_app_audit.md:275` (problem statement)
- **When:** During OpenAPI schema generation if routers import SQLAlchemy models at module level
- **Where:** CI `openapi-sync` job, local `make openapi`

---

## 1. Code Fragments

### A) `legacy_app.py` — Import-Time Feature Flags (Lines 149-169, 347-350)

```python
# VIP router registration (explicit, no import-side-effects)
# Use centralized registration function instead of importing router directly
_register_vip_routes: Callable[[FastAPI], None] | None = None
try:
    from app.routers.vip_registration import register_vip_routes
    from app.utils.feature_flags import is_vip_module_enabled

    _register_vip_routes = register_vip_routes
    VIP_MODULE_ENABLED = is_vip_module_enabled()  # Keep for backward compatibility
except ImportError:
    # VIP registration not available - VIP module disabled
    VIP_MODULE_ENABLED = False

# Backward-compat: expose vip_router for tests/introspection.
if VIP_MODULE_ENABLED:
    try:
        from app.routers import vip as _vip_mod

        vip_router = getattr(_vip_mod, "router", None)
    except ImportError:
        vip_router = None
```

```python
# Only load the local .env automatically for explicit local/dev environments.
_env_was_sanitized = "PATH" not in os.environ
_app_env = (os.getenv("APP_ENV", "") or "").strip().lower()
_should_load_local_env = _app_env in {"", "local", "dev", "development"}
if not _env_was_sanitized and _should_load_local_env and os.getenv("PYTEST_CURRENT_TEST") is None:
    dotenv.load_dotenv()
```

**Analysis:**
- `VIP_MODULE_ENABLED` evaluated at import time (line 157) via `is_vip_module_enabled()`
  - **Default value:** `True` (see `app/utils/feature_flags.py:14`: `os.getenv("VIP_MODULE_ENABLED", "true")`)
  - **Impact:** VIP routes included by default unless explicitly disabled
- `_app_env` read at import time (line 347) — used later for test router conditional (line 1146)
- **Impact:** Feature flags locked at import; cannot change without module reload

---

### B) `legacy_app.py` — FastAPI App Creation (Lines 836-933)

```python
# OpenAPI/Swagger metadata for API documentation
tags_metadata: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Health check and system status endpoints",
    },
    {
        "name": "bmi",
        "description": "BMI calculation endpoints (FREE tier)",
    },
    {
        "name": "foods",
        "description": "Food database search and retrieval (FREE tier)",
    },
    {
        "name": "recipes",
        "description": "Recipe database search and preview (FREE tier)",
    },
    {
        "name": "users",
        "description": "User management endpoints (FREE tier)",
    },
    {
        "name": "pro",
        "description": "PRO tier features - weekly meal planning, nutrition targets. **Requires PRO API key**.",
    },
    {
        "name": "premium",
        "description": "[DEPRECATED] PRO tier features - use /api/v1/pro/* instead. **Requires PRO API key**.",
    },
    {
        "name": "vip",
        "description": "VIP tier features - micronutrients, auto-repair, recipe synthesis, shopping lists. **Requires VIP API key**.",
    },
    {
        "name": "business",
        "description": "Businesss analytics and Bayesian analysis (Internal use)",
    },
    {
        "name": "export",
        "description": "Export endpoints for meal plans and shopping lists",
    },
]

# Build API description with environment-specific content
# Reuse _app_env defined earlier (line 302) to avoid duplication
_is_dev_env = _app_env in {"", "local", "dev", "development", "test", "testing"}

_api_description = """
## PulsePlate - Nutrition & Meal Planning API

**Mobile-first API** for iOS and web applications with tiered subscription access.

### Subscription Tiers

- **FREE**: BMI calculations, food/recipe search, user management
- **PRO**: Advanced meal planning, WHO-based nutrition targets, macro tracking
- **VIP**: Micronutrient goals, AI recipe synthesis, auto-repair, shopping lists

### Authentication

Premium endpoints require API key in `X-API-Key` header:
- PRO tier: Use API key with PRO access level
- VIP tier: Use API key with VIP access level
"""

if _is_dev_env:
    _api_description += """
### Test API Keys (Development Only)

- PRO: `YOUR_PRO_TEST_KEY`
- VIP: `YOUR_VIP_TEST_KEY`

**Note**: Replace with actual test keys from your environment variables or Config.plist.
**Production**: Test keys are disabled in production environments.
"""

_api_description += """
### Documentation

- Mobile API Migration Guide: `docs/MOBILE_API_MIGRATION_GUIDE.md`
- iOS Integration: `docs/IOS_API_INTEGRATION.md`
"""

app = FastAPI(
    title="PulsePlate",
    version="0.1.0",
    description=_api_description,
    contact={
        "name": "PulsePlate API Support",
        "url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
```

**Contract (OpenAPI metadata):**
- `title`: "PulsePlate" — **MUST NOT CHANGE**
- `version`: "0.1.0" — **MUST NOT CHANGE** (unless versioning policy)
- `description`: Dynamic based on `_is_dev_env` — **CONTRACT:** dev vs prod descriptions
- `tags_metadata`: 10 tags — **CONTRACT:** tag names/descriptions are API contract
- `lifespan`: Handler function — **CONTRACT:** startup/shutdown behavior

---

### C) `legacy_app.py` — Main Router Registration (Lines 1064-1102)

```python
# Include API routers
protected_dependency = Depends(_get_api_key_dynamic)

app.include_router(foods_router)
app.include_router(recipes_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(export_router, dependencies=[protected_dependency])
app.include_router(plan_router, dependencies=[protected_dependency])
app.include_router(shoplist_router, dependencies=[protected_dependency])

# Register VIP routes (centralized, explicit registration)
if _register_vip_routes is not None:
    _register_vip_routes(app)

# Register PRO routes (centralized, explicit registration)
pro_router, premium_week_router = _register_pro_routes(app)

# Include Bayesian adherence router (PRO/VIP tier)
try:
    from app.routers import bayes_adherence

    app.include_router(bayes_adherence.router)
except ImportError as e:
    logger.warning("Bayesian adherence router not loaded: %s", e)

# Include nutrition logging router (PRO tier)
try:
    from app.routers import nutrition_log

    app.include_router(nutrition_log.router)
except ImportError as e:
    logger.warning("Nutrition log router not loaded: %s", e)

# Include PRO Shopping List Generator router
app.include_router(shopping_list_pro_router)

# Include Day Shopping List router (iOS MVP)
app.include_router(shoplist_day_router)
```

**Registration Order (CONTRACT):**
1. `foods_router` (always)
2. `recipes_router` (always)
3. `users_router` (always)
4. `catalog_router` (always)
5. `export_router` (always, with API key)
6. `plan_router` (always, with API key)
7. `shoplist_router` (always, with API key)
8. VIP routes (conditional: `_register_vip_routes is not None`)
9. PRO routes (conditional: `_register_pro_routes(app)` — may return `None, None` in schema-only mode)
10. `bayes_adherence.router` (conditional: try/except ImportError)
11. `nutrition_log.router` (conditional: try/except ImportError)
12. `shopping_list_pro_router` (always)
13. `shoplist_day_router` (always)

**⚠️ CRITICAL:** `normalize_openapi_schema()` **SORTS paths alphabetically** (line 76: `dict(sorted(paths.items()))`), so **registration order is NOT preserved** in final schema. The contract is **sorted path order**, not registration order.

---

### D) `legacy_app.py` — Conditional Routers at End of File (Lines 1143-1155, 5175-5190, 5639-5657)

```python
# Conditionally include test router for non-production environments
# Reuse _app_env defined earlier (line 302) to avoid duplication
# Exclude staging from test endpoints for security (staging may be externally accessible)
if _app_env in {"", "local", "dev", "development", "test"} or (
    _app_env == "staging" and os.getenv("ENABLE_TEST_ROUTES") == "1"
):
    try:
        from app.routers import test as test_router

        app.include_router(test_router.router)
        logger.info("Test endpoints enabled for environment: %s", _app_env or "local")
    except ImportError:
        logger.debug("Test router not available")
```

```python
_export_feature_flag = os.getenv("FEATURE_EXPORTS_ENABLED")
_export_testing_flag = (
    _is_truthy(os.getenv("TESTING")) if os.getenv("TESTING") is not None else False
)
if not _export_testing_flag:
    _export_app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    if _export_app_env in {"test", "testing", "ci"}:
        _export_testing_flag = True
    elif "pytest" in sys.modules:
        _export_testing_flag = True
_export_debug_flag = _is_truthy(os.getenv("DEBUG")) if os.getenv("DEBUG") is not None else False
EXPORTS_ENABLED = _is_truthy(_export_feature_flag) if _export_feature_flag is not None else False
if not EXPORTS_ENABLED:
    EXPORTS_ENABLED = _export_testing_flag or _export_debug_flag
if EXPORTS_ENABLED and not _export_testing_flag:
    logging.warning("Export endpoints enabled outside tests; intended for test/demo only.")

if EXPORTS_ENABLED:

    @app.get(
        "/api/v1/premium/exports/day/{plan_id}.csv", dependencies=[Depends(_get_api_key_dynamic)]
    )
    async def export_daily_plan_csv(plan_id: str) -> Response:
        # ... endpoint implementation ...
```

```python
# Include bodyfat router if available
if get_bodyfat_router is not None:
    app.include_router(get_bodyfat_router(), prefix="/api/v1")

# Include BMI Pro router (with feature flag). Defaults to disabled for safety.
_bmi_pro_flag = os.getenv("FEATURE_BMI_PRO_ENABLED")
FEATURE_BMI_PRO_ENABLED = _is_truthy(_bmi_pro_flag) if _bmi_pro_flag is not None else False
if FEATURE_BMI_PRO_ENABLED and bmi_pro_router:
    app.include_router(bmi_pro_router)

# Include BMI router (FREE tier, no API key required)
app.include_router(bmi_router)

# Include Businesss router (with feature flag). Defaults to disabled for safety.

_business_flag = os.getenv("BUSINESS_MODULE_ENABLED")
BUSINESS_MODULE_ENABLED = _is_truthy(_business_flag) if _business_flag is not None else False
if BUSINESS_MODULE_ENABLED and business_router:
    app.include_router(business_router)
```

**Schema-Only Gaps:**
- ❌ Test router: No schema-only guard (registered if `_app_env` allows)
- ❌ Bodyfat router: No schema-only guard (registered if `get_bodyfat_router is not None`)
- ❌ BMI Pro router: No schema-only guard (registered if `FEATURE_BMI_PRO_ENABLED` and `bmi_pro_router`)
- ❌ Businesss router: No schema-only guard (registered if `BUSINESS_MODULE_ENABLED` and `business_router`)
- ❌ EXPORTS_ENABLED endpoints: No schema-only guard (registered if `EXPORTS_ENABLED`)

**Risks:**
1. **ORM import errors:** These routers may import SQLAlchemy models at module level, causing "Table already defined" errors in schema-only mode
2. **Public schema exposure:** Export endpoints are "test/demo only" (warning at line 5189), but appear in public schema if enabled → **MUST be excluded from schema unless explicitly productized (VIP/PRO tier)**

**Policy for Export Endpoints:**
- Export endpoints **MUST be excluded from public schema** unless explicitly productized (VIP/PRO tier)
- Current warning (`logging.warning("Export endpoints enabled outside tests; intended for test/demo only.")`) is not enforced in schema generation
- **Mitigation:** Add schema-only guard OR `include_in_schema=False` to export endpoints

---

### E) `app/routers/pro_registration.py` — Full File

```python
# -*- coding: utf-8 -*-
"""
PRO Router Registration

RU: Централизованная регистрация PRO и premium_week роутеров.
EN: Centralized PRO and premium_week router registration.

This module provides a single entry point for registering all PRO routes
with the FastAPI application, eliminating import-side-effects and making
PRO route registration explicit and testable.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi.routing import APIRouter

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["register_pro_routes"]


def _is_openapi_schema_only_mode() -> bool:
    """Check if OpenAPI schema-only generation mode is active.

    Schema-only mode must never activate in production by accident.
    We only honor it in generation/test context (PULSEPLATE_OPENAPI=1 AND APP_ENV=test AND ENVIRONMENT=test).
    """
    _openapi_flag = (os.getenv("PULSEPLATE_OPENAPI") or "").strip()
    _app_env = (os.getenv("APP_ENV") or "").strip().lower()
    _env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    return (_openapi_flag == "1") and (_app_env == "test") and (_env == "test")


def register_pro_routes(app: "FastAPI") -> tuple[APIRouter | None, APIRouter | None]:
    """
    Register PRO and premium_week routes with the FastAPI application.

    RU: Регистрирует PRO и premium_week роуты в FastAPI приложении.
    EN: Registers PRO and premium_week routes with the FastAPI application.

    This function centralizes PRO route registration logic:
    - Checks OpenAPI schema-only mode (skips routers that import SQLAlchemy models)
    - Includes premium_week router
    - Includes pro router
    - Applies route-level dependencies (API key)

    Args:
        app: FastAPI application instance

    Returns:
        Tuple of (pro_router, premium_week_router) for backward compatibility.
        Both may be None if in OpenAPI schema-only mode or feature flags disabled.

    Note:
        This function has no side effects if in OpenAPI schema-only mode.
        It can be called multiple times safely (idempotent).
    """
    openapi_mode = _is_openapi_schema_only_mode()

    # Return cached values if already registered in the same mode (idempotent)
    if (
        getattr(app.state, "_pro_routes_registered", False)
        and getattr(app.state, "_pro_routes_registered_openapi_mode", None) == openapi_mode
    ):
        cached_pro = getattr(app.state, "_cached_pro_router", None)
        cached_premium = getattr(app.state, "_cached_premium_week_router", None)
        return cached_pro, cached_premium

    pro_router_result: APIRouter | None = None
    premium_week_router_result: APIRouter | None = None

    if not openapi_mode:
        # Import routers only in non-schema-only mode to avoid import-time ORM hazards.
        # These routers import app.models at module level, which triggers SQLAlchemy
        # table creation and causes "Table already defined" errors on repeated imports.
        from app.routers.pro import router as pro_router_imported

        if pro_router_imported is not None:
            app.include_router(pro_router_imported)
            pro_router_result = pro_router_imported

        # Include premium_week router for backward compatibility (deprecated)
        # Check FEATURE_PREMIUM_WEEK_ENABLED feature flag
        from app.utils.feature_flags import is_vip_module_enabled

        feature_premium_week_enabled = (
            os.getenv("FEATURE_PREMIUM_WEEK_ENABLED", "").strip().lower()
            in {"1", "true", "yes", "on"}
        ) or is_vip_module_enabled()  # Also enable if VIP module is enabled

        if feature_premium_week_enabled:
            from app.routers.premium_week import router as premium_week_router_imported

            # premium_week endpoints enforce tier access internally via app.middleware.api_tiers
            # (e.g., require_pro_tier). Do not add the global API_KEY guard here, otherwise
            # PRO/VIP test keys (test_pro_key/test_vip_key) are rejected when API_KEY is set.
            # NOTE: This router is deprecated. Use /api/v1/pro/* endpoints instead.
            if premium_week_router_imported is not None:
                app.include_router(premium_week_router_imported)
                premium_week_router_result = premium_week_router_imported

    # Cache routers for idempotent return.
    # Avoid "locking in" schema-only results in case the same app instance is reused.
    if not openapi_mode:
        app.state._pro_routes_registered = True
        app.state._pro_routes_registered_openapi_mode = openapi_mode
        app.state._cached_pro_router = pro_router_result
        app.state._cached_premium_week_router = premium_week_router_result

    return pro_router_result, premium_week_router_result
```

**Key Points:**
- `_is_openapi_schema_only_mode()`: Triple guard (`PULSEPLATE_OPENAPI=1` AND `APP_ENV=test` AND `ENVIRONMENT=test`)
- `register_pro_routes()`: Returns `(None, None)` in schema-only mode (line 114)
- Premium week registration: Inside `register_pro_routes()` (lines 90-104), conditional on feature flag OR VIP module enabled
- **Idempotency:** Caches routers in `app.state` to prevent re-registration

**VIP Module Behavior:**
- `is_vip_module_enabled()` (line 14 of `app/utils/feature_flags.py`): `os.getenv("VIP_MODULE_ENABLED", "true")` — **defaults to `True`**
- **Impact:** In schema generation, `VIP_MODULE_ENABLED` is not explicitly set, so VIP routes are **included by default** (no schema-only guard)
- **Risk:** VIP routes may import SQLAlchemy models at module level, causing "Table already defined" errors

---

### F) `scripts/generate_openapi.py` + `app/main.py`

**`scripts/generate_openapi.py` (Lines 94-121):**

```python
def main() -> int:
    # Make OpenAPI generation deterministic across dev/CI
    # Enable schema-only mode to avoid SQLAlchemy model double-loading
    # This prevents "Table already defined" errors and ensures deterministic schema
    os.environ["PULSEPLATE_OPENAPI"] = "1"

    # Hard pin environment and feature flags for schema-only mode
    # IMPORTANT: This is schema-only mode (temporary). Premium/pro routers are disabled
    # because they import SQLAlchemy models at module level, causing double-load errors.
    # Follow-up PR-509: eliminate import-time ORM dependencies to enable full schema.
    # CI uses APP_ENV=test/ENVIRONMENT=test, so we align here
    os.environ["APP_ENV"] = "test"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["ENABLE_TEST_ROUTES"] = "1"
    # Disable routers that import SQLAlchemy models at module level (temporary)
    # These will be re-enabled in PR-509 after moving models to lazy imports or app/schemas
    os.environ["FEATURE_PREMIUM_WEEK_ENABLED"] = "false"
    os.environ["FEATURE_BMI_PRO_ENABLED"] = "false"
    os.environ["BUSINESS_MODULE_ENABLED"] = "false"

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

    # IMPORTANT: canonical entrypoint (applies register_metrics bootstrap)
    # PULSEPLATE_OPENAPI=1 must be set BEFORE importing app to prevent SQLAlchemy double-loading
    from app.main import (
        app,
    )  # noqa: WPS433, ANN401 (intentional runtime import, dynamic typing needed)

    schema = app.openapi()
    schema = normalize_openapi_schema(schema)
```

**`normalize_openapi_schema()` Behavior (Lines 57-91):**

```python
def normalize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Make FastAPI OpenAPI output deterministic by normalizing all dicts/lists.

    This recursively sorts all dictionary keys and normalizes list order
    to ensure identical output across runs.
    """
    # ... recursive normalization ...

    # Sort paths by path string
    paths = normalized.get("paths")
    if isinstance(paths, dict):
        normalized["paths"] = dict(sorted(paths.items()))  # ← ALPHABETICAL SORT

    # Sort operations within each path
    for path_key, ops in paths.items():
        if isinstance(ops, dict):
            normalized["paths"][path_key] = dict(sorted(ops.items()))  # ← METHOD SORT
```

**Critical Finding:**
- **Registration order is NOT preserved** — paths are sorted alphabetically (line 76)
- **Contract is sorted order**, not registration order
- **PR-511 implication:** Router registration order changes won't affect final schema (paths are sorted anyway)

**`app/main.py` (Full File):**

```python
"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from fastapi import FastAPI

from legacy_app import app as _legacy_app  # re-export FastAPI instance from legacy root module

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app

register_metrics(app)

__all__ = ["app"]
```

**Import Chain:**
1. `scripts/generate_openapi.py:119` → `from app.main import app`
2. `app/main.py:11` → `from legacy_app import app as _legacy_app`
3. `legacy_app.py` → Module-level execution (imports, feature flags, app creation, router registration)

**Critical:** `PULSEPLATE_OPENAPI=1` must be set **BEFORE** `from app.main import app` (line 98), otherwise `legacy_app.py` executes with wrong env vars.

---

## 2. Endpoint Questions & Answers

### A) Legacy MUST KEEP (iOS/FE Clients)

**Question:** Which endpoints are officially used by iOS/FE clients?

**Answer (based on code evidence):**

1. **`/api/nutrition/{date_str}`** (line 1107):
   - ✅ **OFFICIAL iOS endpoint** (comment: "Legacy alias for iOS nutrition endpoint compatibility")
   - Delegates to `/api/v1/pro/nutrition/daily`
   - **Status:** MUST KEEP in `legacy_app.py` (compatibility shim)

2. **`/bmi`** (line 2097):
   - ⚠️ **Legacy shim** (comment: "Shim endpoint. Delegates to canonical handler")
   - Delegates to `app.routers.bmi.bmi_calculate_handler`
   - **Status:** MAY BE DEPRECATED (canonical is `/api/v1/bmi/calculate`)

3. **`/plan`** (line 2209):
   - ⚠️ **Legacy endpoint** (comment: "Legacy endpoint /plan. Contract must remain stable")
   - Delegates to `app.routers.bmi.bmi_calculate_handler`
   - **Status:** MUST KEEP (explicit contract stability requirement)

4. **`/api/v1/bmi`** (line 2316):
   - ⚠️ **Legacy shim** (comment: "Shim endpoint. Delegates to canonical handler")
   - Delegates to `app.routers.bmi.bmi_calculate_handler`
   - **Status:** MAY BE DEPRECATED (canonical is `/api/v1/bmi/calculate`)

**Recommendation:**
- **MUST KEEP (runtime):** `/api/nutrition/{date_str}`, `/plan` — iOS clients depend on these paths
- **Schema visibility:**
  - If iOS uses auto-generated SDK from schema → legacy endpoints **MUST BE in schema**
  - If iOS uses manual models → legacy endpoints can be **hidden from schema** (`include_in_schema=False`) while remaining available at runtime
- **CAN DEPRECATE:** `/bmi`, `/api/v1/bmi` (redirect to `/api/v1/bmi/calculate`)

---

### B) Admin Endpoints

**Question:** Should admin endpoints be in OpenAPI schema?

**Answer:**

| Endpoint | Current Status | Should Be in Schema? | Used By |
|----------|---------------|---------------------|---------|
| `/api/v1/admin/status` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | Internal monitoring |
| `/api/v1/admin/db-status` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | Internal scripts |
| `/api/v1/admin/check-updates` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | CI/CD pipelines |
| `/api/v1/admin/rollback` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | Admin scripts |
| `/api/v1/admin/force-update` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | Admin scripts |
| `/admin/logs/cleanup` | ✅ In schema | ❌ **NO** (`include_in_schema=False`) | Admin scripts |

**OpenAPI Accessibility:**
- `/openapi.json`: **Publicly accessible** (no auth/middleware; tests show `status_code == 200` without API key)
- `/docs`: **Publicly accessible** (Swagger UI)
- `/redoc`: **Publicly accessible** (ReDoc UI)

**Security Risk Assessment:**
- **If `/openapi.json` is public** (confirmed by tests) → Admin endpoints in schema = **real security risk** (exposes attack surface)
- **If `/openapi.json` is protected** (not confirmed in codebase) → Admin endpoints in schema = acceptable (only authenticated users see them)

**Recommendation:**
- **If public:** Add `include_in_schema=False` to all admin endpoints (security: don't expose admin routes in public schema)
- **If protected:** Document auth policy for `/openapi.json` access

---

### C) Feature Flags in CI Schema Generation

**Question:** Which feature flags are enabled in CI `openapi-sync` job?

**Answer (from `scripts/generate_openapi.py:98-112`):**

```python
os.environ["PULSEPLATE_OPENAPI"] = "1"
os.environ["APP_ENV"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENABLE_TEST_ROUTES"] = "1"  # ✅ ENABLED
os.environ["FEATURE_PREMIUM_WEEK_ENABLED"] = "false"  # ❌ DISABLED
os.environ["FEATURE_BMI_PRO_ENABLED"] = "false"  # ❌ DISABLED
os.environ["BUSINESS_MODULE_ENABLED"] = "false"  # ❌ DISABLED
```

**Not set (defaults):**
- `VIP_MODULE_ENABLED`: Not explicitly set → **defaults to `True`** via `is_vip_module_enabled()` (line 14: `os.getenv("VIP_MODULE_ENABLED", "true")`). **This means VIP routes ARE included in schema generation unless explicitly disabled.**
- `FEATURE_EXPORTS_ENABLED`: Not explicitly set → defaults to `False` (unless `TESTING=true` or `DEBUG=true`)

**Problems:**
1. **`ENABLE_TEST_ROUTES=1`** means test router **IS INCLUDED** in schema generation (line 1146-1155). **Why included?** Likely for test coverage or demo purposes, but this violates "schema-only = minimal safe schema" principle.
2. **VIP routes included by default:** `is_vip_module_enabled()` defaults to `True`, so VIP routes are included in schema unless `VIP_MODULE_ENABLED=false` is explicitly set (which it's not in `generate_openapi.py`).
3. **Security risk:** `/openapi.json` is **publicly accessible** (no auth/middleware guards; tests show `status_code == 200` without API key). Admin and test endpoints visible in public schema = attack surface exposure.

---

## 3. Contract Table (Minimal Set)

| Contract | Status | Evidence |
|----------|--------|----------|
| **Path ordering in OpenAPI** | ✅ **CONTRACT (sorted, not registration)** | `normalize_openapi_schema()` sorts paths alphabetically (line 76: `dict(sorted(paths.items()))`). **Contract is sorted order**, not registration order. |
| **Test router in schema** | ❌ **NOT ALLOWED** | Security risk (public `/openapi.json`); should be `include_in_schema=False` or excluded in schema-only mode. Currently included when `ENABLE_TEST_ROUTES=1` (line 107). |
| **Legacy endpoints runtime availability** | ✅ **CONTRACT** | `/api/nutrition/{date_str}`, `/plan` — **MUST REMAIN** in runtime (iOS clients depend on them). `/bmi`, `/api/v1/bmi` — can be deprecated. |
| **Legacy endpoints in schema** | ⚠️ **CONDITIONAL** | If iOS uses auto-generated SDK from schema → legacy endpoints **MUST BE in schema**. If iOS uses manual models → legacy endpoints can be **hidden from schema** (`include_in_schema=False`) while remaining available at runtime. |
| **PRO routes absent in schema-only** | ✅ **CONTRACT** | `pro_registration.py:62-75` returns `(None, None)` in schema-only mode |
| **VIP routes in schema-only** | ⚠️ **NO GUARD** | Currently no schema-only guard; VIP routes included if `VIP_MODULE_ENABLED=True` (defaults to `True` via `is_vip_module_enabled()`). |

**Recommendations:**
1. ✅ Fix: Add schema-only guard to VIP routes (mirror PRO pattern) — **CRITICAL:** VIP defaults to enabled, may import ORM models
2. ✅ Fix: Exclude test router in schema-only mode (or add `include_in_schema=False`) — **CRITICAL:** Test endpoints should not be in public schema
3. ✅ Fix: Add schema-only guards to BMI Pro, Businesss, Bodyfat routers
4. ✅ Fix: Set `VIP_MODULE_ENABLED=false` in `generate_openapi.py` if VIP routes import ORM models
5. ⚠️ Decision needed: Should `ENABLE_TEST_ROUTES=1` be removed from schema generation? (Currently included for test coverage, but violates "minimal safe schema" principle)

---

## 4. Side-Effect Diagnosis

**Question:** Is `init_db()` called at import time or only in runtime lifespan?

**Answer:**

**`init_db()` is called ONLY in runtime lifespan (NOT at import time):**

**Evidence:**
```python
# legacy_app.py:738-747
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    # Detect environment first (before any DB operations)
    env_name = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    is_production = env_name not in {"", "local", "dev", "development", "staging", "test", "ci"}
    truthy = {"1", "true", "yes", "on"}

    try:
        init_db()  # ← Called here, inside lifespan startup
        logger.info("Database schema initialized")
```

**Conclusion:** `init_db()` is **NOT** an import-time side-effect. It's called when FastAPI app starts (lifespan enter). However, `lifespan` function is **defined** at import time (line 738), which is fine (function definition is not execution).

**Real import-time side-effects:**
- Feature flag evaluation (`VIP_MODULE_ENABLED`, `_app_env`)
- Router registration (`app.include_router()` calls at module level)
- FastAPI app creation (`app = FastAPI(...)`)

---

## 5. Security Notes

**`_get_api_key_dynamic` Implementation (Lines 999-1014):**

```python
# Dependency wrapper that resolves get_api_key dynamically at runtime so tests can patch it
def _get_api_key_dynamic(api_key: str = Depends(api_key_header)) -> str:
    import sys as _sys

    _pkg = _sys.modules.get("app")
    _guard = getattr(_pkg, "get_api_key", get_api_key)
    try:
        return _guard(api_key)
    except Exception as exc:
        # Preserve HTTPException semantics (e.g., 403 for auth), convert other errors to 500
        if isinstance(exc, HTTPException):
            raise
        # Log the actual exception server-side for debugging
        logger.exception("Authentication dependency error: %s", exc)
        # Return generic error to client to avoid exposing internal details
        raise HTTPException(status_code=500, detail="Authentication service error") from exc
```

**Analysis:**
- Resolves `get_api_key` dynamically from `app` package (allows test patching)
- Admin endpoints use `dependencies=[Depends(_get_api_key_dynamic)]` → **API key required at runtime**
- **OpenAPI Schema Impact:** Admin endpoints appear in schema with `security` requirements (API key)
- **Risk:** Admin endpoints visible in **public `/openapi.json`** (no auth on schema endpoint itself). Even if schema shows `security: [APIKeyHeader]`, the **presence of admin paths** in schema exposes attack surface (path enumeration, parameter discovery).

**Mitigation:** Add `include_in_schema=False` to all admin endpoints to exclude them from public schema while keeping them functional at runtime.

**Additional Risk:** Public docs UI (`/docs`, `/redoc`) increases exploitability:
- Interactive exploration of endpoints
- Sample payloads and parameter discovery
- No auth required to access documentation
- **Impact:** Attackers can enumerate API surface without making actual requests to business endpoints

---

## 6. PR-511 Plan (Two-Phase Approach)

### PR-511A: Extract Orchestration (Minimal Diff, Safe)

**Goal:** Move app creation and router registration out of `legacy_app.py` without changing behavior.

**Files to Create:**
1. `app/factory.py` (or extend `app/main.py`):
   - Move `app = FastAPI(...)` creation
   - Move `tags_metadata`, `_api_description` construction
   - Move middleware setup (if any)

2. `app/routers/registration.py`:
   - Unified `register_all_routers(app)` function
   - Single source of truth for router registration order
   - **Note:** Registration order doesn't affect final schema (paths are sorted), but keeping order consistent helps with debugging

**Files to Modify:**
1. `legacy_app.py`:
   - Remove `app = FastAPI(...)` (re-export from `app.main`)
   - Remove router registration calls (move to `registration.py`)
   - Keep: Public attributes (`premium_week_router`, `pro_router`, `vip_router`)
   - Keep: Legacy endpoint aliases (`/api/nutrition/{date_str}`, `/plan`, etc.)

2. `app/main.py`:
   - Import app from factory (or create here)
   - Keep: `register_metrics(app)` bootstrap

**Invariant:** OpenAPI schema (after normalization) must be byte-identical before/after PR-511A.

**⚠️ CRITICAL:** PR-511A does **NOT** add schema-only guards or change router enablement logic. It only **moves** registration code to a unified module. Guards and schema hygiene are PR-511B scope.

### PR-511B: Unified Schema-Only Guards (Follow-up)

**Goal:** Add schema-only guards to all conditional routers to prevent ORM import errors.

**Changes:**
1. Create `app/utils/openapi_mode.py` with unified `is_schema_only_mode()` function
2. Apply schema-only guard to:
   - VIP routes (currently no guard, defaults to enabled)
   - Test router (currently included when `ENABLE_TEST_ROUTES=1`)
   - Bodyfat router
   - BMI Pro router
   - Businesss router
   - Export endpoints
3. Update `scripts/generate_openapi.py`:
   - Remove `ENABLE_TEST_ROUTES=1` (or exclude test router from schema)
   - Set `VIP_MODULE_ENABLED=false` if VIP routes import ORM models

**Invariant:**
- Schema generation must not trigger "Table already defined" errors
- Public schema must exclude sensitive routes (admin, test, dev-only endpoints)

### PR-512+ (Later): Move Endpoints Out of legacy_app

This is feature routing cleanup, not orchestration extraction. Separate PR to avoid scope creep.

---

## 7. PR-511A Detailed Scope (Minimal Diff)

### Files to Create:
1. `app/factory.py` (or extend `app/main.py`):
   - Move `app = FastAPI(...)` creation
   - Move `tags_metadata`, `_api_description` construction
   - Move middleware setup (if any)

2. `app/routers/registration.py`:
   - Unified `register_all_routers(app)` function
   - Single source of truth for router registration order
   - **Preserve current conditional logic as-is** (no behavior changes; guards added in PR-511B)

### Files to Modify:
1. `legacy_app.py`:
   - Remove `app = FastAPI(...)` (re-export from `app.main`)
   - Remove router registration calls (move to `registration.py`)
   - Keep: Public attributes (`premium_week_router`, `pro_router`, `vip_router`)
   - Keep: Legacy endpoint aliases (`/api/nutrition/{date_str}`, `/plan`, etc.)

2. `app/main.py`:
   - Import app from factory (or create here)
   - Keep: `register_metrics(app)` bootstrap

### Lines to Remove from `legacy_app.py`:
- Lines 836-933: `tags_metadata`, `_api_description`, `app = FastAPI(...)`
- Lines 1064-1102: Router registration calls
- Lines 1146-1155: Test router conditional
- Lines 5639-5657: Bodyfat/BMI Pro/BMI/Businesss router registrations
- Lines 5175-5190: `EXPORTS_ENABLED` evaluation (move to registration)

### Lines to Keep in `legacy_app.py`:
- Lines 99-100: `premium_week_router`, `pro_router` declarations (public attributes for tests)
- Lines 139, 163-169: `vip_router` declaration (public attribute for tests)
- Lines 1107-1137: `/api/nutrition/{date_str}` legacy alias (runtime compatibility for iOS)
- Lines 2097-2143: `/bmi` legacy shim (or deprecate)
- Lines 2209-2306: `/plan` legacy endpoint (MUST KEEP — explicit contract stability requirement)
- Lines 2316-2403: `/api/v1/bmi` legacy shim (or deprecate)
- All endpoint definitions (move to routers in PR-512+)

**Note:** Legacy endpoints can be hidden from schema (`include_in_schema=False`) while remaining available at runtime. Decision depends on whether iOS uses auto-generated SDK from schema or manual models.

---

## 7. Critical Clarifications (QA Review Findings)

### A) `normalize_openapi_schema()` Sorting Policy

**Question:** Is path ordering a contract, or does normalization override it?

**Answer:**

**`normalize_openapi_schema()` SORTS paths alphabetically** (line 76: `dict(sorted(paths.items()))`).

**Code Evidence:**
```python
# scripts/generate_openapi.py:73-76
# Sort paths by path string
paths = normalized.get("paths")
if isinstance(paths, dict):
    normalized["paths"] = dict(sorted(paths.items()))  # ← ALPHABETICAL SORT
```

**Implication:**
- **Registration order is NOT preserved** in final OpenAPI schema
- **Contract is sorted path order**, not registration order
- **PR-511 Impact:** Router registration order changes are safe (won't affect schema determinism)
- **Why this matters:** If we claim "registration order is contract" but normalize sorts paths, we're holding onto a false contract

**Decision:** Router registration order is **NOT a contract** for OpenAPI schema. The contract is **alphabetically sorted paths**. Registration order only matters for runtime route matching (FastAPI checks routes in registration order), but schema generation normalizes to sorted order.

---

### B) OpenAPI Endpoint Accessibility

**Question:** Is `/openapi.json` publicly accessible or protected?

**Answer:**

**`/openapi.json` is PUBLICLY ACCESSIBLE** (no auth/middleware guards).

**Evidence:**
- Tests show `status_code == 200` without API key: `tests/test_api_extras.py:42-54`
- No middleware/guards found in codebase for `/openapi.json`, `/docs`, `/redoc`
- FastAPI default behavior: OpenAPI endpoints are public unless explicitly protected

**Security Risk Assessment:**
- **If `/openapi.json` is public** (confirmed) → Admin/test endpoints in schema = **real security risk**
- **Attack surface exposure:** Path enumeration, parameter discovery, endpoint visibility
- **Mitigation:** Admin/test endpoints must use `include_in_schema=False` to exclude from public schema

**Recommendation:**
- Admin endpoints: Add `include_in_schema=False` (security: don't expose admin routes in public schema)
- Test router: Exclude from schema-only mode or add `include_in_schema=False`
- **Alternative:** If schema should be protected, add auth middleware to `/openapi.json` endpoint (not currently implemented)

---

### C) `is_vip_module_enabled()` Default Behavior

**Question:** What does `is_vip_module_enabled()` do, and what are its defaults?

**Answer:**

**`is_vip_module_enabled()` defaults to `True`.**

**Code Evidence:**
```python
# app/utils/feature_flags.py:13-15
def is_vip_module_enabled() -> bool:
    raw = os.getenv("VIP_MODULE_ENABLED", "true").strip().lower()  # ← DEFAULT "true"
    return raw in _TRUTHY
```

**Impact:**
- In schema generation, `VIP_MODULE_ENABLED` is **not explicitly set** in `generate_openapi.py`
- VIP routes are **included by default** (no schema-only guard)
- **Risk:** VIP routes may import SQLAlchemy models at module level, causing "Table already defined" errors

**Concrete Evidence:**
- **VIP router (`app/routers/vip.py`):** No direct `app.models` import found at module level (grep negative)
- **Premium week router (`app/routers/premium_week.py`):** **CONFIRMED** — imports `from app.models.nutrition import TargetsIn` at module level (line 21)
- **VIP registration chain:** `register_vip_routes()` → includes `premium_week` router if VIP enabled → premium_week imports ORM models
- **Conclusion:** VIP module registration **can trigger ORM imports** via premium_week router, even if VIP router itself doesn't import models directly

**Current Behavior:**
- `legacy_app.py:157` calls `is_vip_module_enabled()` at import time
- Returns `True` by default (unless `VIP_MODULE_ENABLED=false` is set)
- VIP routes registered if `VIP_MODULE_ENABLED=True` (default)

**Mitigation Options:**
1. Add schema-only guard to VIP registration (mirror PRO pattern in `vip_registration.py`)
2. Set `VIP_MODULE_ENABLED=false` in `generate_openapi.py` if VIP routes import ORM models
3. Make VIP registration respect `PULSEPLATE_OPENAPI=1` flag (unified schema-only policy)

---

### D) `ENABLE_TEST_ROUTES=1` in Schema Generation

**Question:** Why is `ENABLE_TEST_ROUTES=1` set in `generate_openapi.py`?

**Answer:**

**`ENABLE_TEST_ROUTES=1` is explicitly set in `scripts/generate_openapi.py:107`.**

**Code Evidence:**
```python
# scripts/generate_openapi.py:107
os.environ["ENABLE_TEST_ROUTES"] = "1"
```

**Why included?**
- **Likely reasons:** Test coverage, demo purposes, or ensuring test endpoints appear in schema for development
- **Problem:** Violates "schema-only = minimal safe schema" principle
- **Security risk:** Test endpoints visible in public `/openapi.json`

**Current Behavior:**
- Test router is registered when `_app_env in {"", "local", "dev", "development", "test"}` OR `ENABLE_TEST_ROUTES=1` (line 1146-1155)
- In schema generation, `APP_ENV=test` AND `ENABLE_TEST_ROUTES=1` → test router **IS included**

**Decision Needed:**
- **Option 1:** Remove `ENABLE_TEST_ROUTES=1` from `generate_openapi.py` (exclude test router from schema)
- **Option 2:** Keep `ENABLE_TEST_ROUTES=1` but add `include_in_schema=False` to test router
- **Option 3:** Add schema-only guard to test router registration (exclude in schema-only mode)

**Recommendation:** Option 1 or 3 (test endpoints should not be in public schema).

---

## 8. Additional Critical Findings

### A) `normalize_openapi_schema()` Sorting Policy

**Finding:** `normalize_openapi_schema()` sorts paths alphabetically (line 76: `dict(sorted(paths.items()))`).

**Implication:** Router registration order does NOT affect final OpenAPI schema. The contract is **sorted path order**, not registration order.

**PR-511 Impact:** Router registration order changes are safe (won't affect schema determinism).

### B) OpenAPI Endpoint Accessibility

**Finding:** `/openapi.json`, `/docs`, `/redoc` are **publicly accessible** (no auth/middleware guards).

**Evidence:** Tests show `status_code == 200` without API key (e.g., `tests/test_api_extras.py:42-54`).

**Security Risk:** Admin/test endpoints in schema = attack surface exposure (path enumeration, parameter discovery).

**Mitigation:**
- Admin endpoints: `include_in_schema=False`
- Test router: Exclude from schema-only mode or `include_in_schema=False`

### C) `is_vip_module_enabled()` Default Behavior

**Finding:** `is_vip_module_enabled()` defaults to `True` (`os.getenv("VIP_MODULE_ENABLED", "true")`).

**Impact:** VIP routes are included in schema generation by default (unless explicitly disabled).

**Risk:** VIP routes may import SQLAlchemy models at module level, causing "Table already defined" errors.

**Mitigation:**
- Add schema-only guard to VIP registration (mirror PRO pattern)
- OR set `VIP_MODULE_ENABLED=false` in `generate_openapi.py` if VIP routes import ORM models

### D) `ENABLE_TEST_ROUTES=1` in Schema Generation

**Finding:** `scripts/generate_openapi.py:107` sets `ENABLE_TEST_ROUTES=1`, causing test router to be included in schema.

**Why included?** Likely for test coverage or demo purposes, but violates "schema-only = minimal safe schema" principle.

**Decision needed:** Should test router be excluded from schema generation? (Currently included, but should be excluded for security)

---

## 9. AGENTS.md Rules to Add

After PR-510/511, add to `AGENTS.md`:

```markdown
## Import-Time Side-Effects Policy

- **Forbidden:** Feature flag evaluation at module level in compatibility layers (`legacy_app.py`)
- **Forbidden:** Router registration at module level (must be in registration function)
- **Allowed:** Public attribute declarations (`premium_week_router: Optional[APIRouter] = None`)

## Schema-Only Mode Policy

- **Required:** All conditional routers must respect schema-only mode (`PULSEPLATE_OPENAPI=1` guard)
- **Required:** Test router must be excluded from schema (`include_in_schema=False` or schema-only guard)
- **Required:** Admin endpoints must be excluded from schema (`include_in_schema=False`)
- **Required:** Feature flags that default to enabled (e.g., `VIP_MODULE_ENABLED`) must be explicitly disabled in schema generation if routers import ORM models

## OpenAPI Generation Policy

- **Path ordering:** OpenAPI paths are sorted alphabetically by `normalize_openapi_schema()`, not by registration order
- **Schema accessibility:** `/openapi.json` is publicly accessible (no auth) → admin/test endpoints must be excluded from schema
- **Schema-only principle:** Schema generation should produce minimal safe schema (no test/dev endpoints)

## App Factory Policy

- **Required:** App creation (`FastAPI(...)`) must be in `app/main.py` or `app/factory.py`
- **Required:** Router registration must be in `app/routers/registration.py` (unified function)
- **Required:** `legacy_app.py` must re-export app from factory, not create it
```

---

## Summary

**Critical Findings:**
1. ✅ PRO routes have schema-only guard (good)
2. ❌ VIP/BMI Pro/Businesss/Bodyfat/Test routers lack schema-only guards (risk)
   - **VIP:** Defaults to enabled (`is_vip_module_enabled()` returns `True` by default)
   - **Test router:** Explicitly enabled in schema generation (`ENABLE_TEST_ROUTES=1`)
3. ❌ Admin endpoints visible in schema (security risk)
   - **Root cause:** `/openapi.json` is publicly accessible (no auth/middleware)
   - **Impact:** Attack surface exposure (path enumeration, parameter discovery)
4. ❌ Test router included in schema when `ENABLE_TEST_ROUTES=1` (security risk)
   - **Why included?** Likely for test coverage, but violates "schema-only = minimal safe schema"
5. ✅ `init_db()` is NOT import-time side-effect (only in lifespan)
6. ⚠️ **Contract = canonical normalization, not registration order:** `normalize_openapi_schema()` sorts paths/methods alphabetically and normalizes dict keys, so registration order changes won't affect final schema determinism

**PR-511 Must Fix:**
- Add schema-only guards to all conditional routers
- Exclude admin/test endpoints from schema
- Move app creation to factory
- Move router registration to unified module

**PR-511 Must Preserve:**
- **Canonical OpenAPI normalization** (paths sorted alphabetically, methods sorted, dict keys normalized — contract is normalized output, not registration order)
- Public attributes (`premium_week_router`, `pro_router`, `vip_router`)
- Legacy endpoint aliases (`/api/nutrition/{date_str}`, `/plan`) — **runtime availability** (schema visibility is separate concern)

---

## 10. Decision Log (PR-510 Canon)

### PR-510 Scope
- **Analysis-only:** No code changes, only fact-finding and contract documentation
- **Primary debt identified:** `legacy_app.py` performs orchestration (app creation + router registration) at import time
- **Schema-only policy:** Currently partial (PRO excluded, others not) → root cause of flake risk

### Security Decisions
- **Admin endpoints:** Must be excluded from schema (`include_in_schema=False`) because `/openapi.json` is publicly accessible
- **Test router:** Must be excluded from schema (violates "minimal safe schema" principle)
- **OpenAPI accessibility:** Currently public (no auth) → all sensitive endpoints must be hidden from schema

### Contract Decisions
- **OpenAPI determinism:** Contract is **canonical normalization** (sorted paths/methods, normalized dict keys), not registration order (normalization overrides registration)
- **Legacy endpoints:** Runtime availability ≠ schema visibility
  - **Runtime:** `/api/nutrition/{date_str}`, `/plan` MUST remain available (iOS clients)
  - **Schema:** Visibility depends on iOS SDK strategy (auto-generated vs manual models)

### Schema-Only Policy Decisions
- **Unified guard required:** All conditional routers must respect schema-only mode
- **Dual purpose:** Schema-only mode serves both ORM flake prevention AND public schema hygiene boundary
- **VIP default behavior:** Currently defaults to enabled → must add guard or explicitly disable in schema generation
  - **Evidence:** Premium week router (included via VIP) imports `app.models.nutrition` at module level
- **Test router:** Should not be included in schema generation (remove `ENABLE_TEST_ROUTES=1` or add guard)
- **Export endpoints:** Must be excluded from public schema unless explicitly productized (VIP/PRO tier)

### PR-511 Split Decision
- **PR-511A:** Extract orchestration (safe, minimal diff, preserves behavior)
- **PR-511B:** Add unified schema-only guards (follow-up, prevents ORM errors + public schema hygiene)
- **PR-512+:** Move endpoints out of legacy_app (separate concern, feature routing cleanup)

---

## 11. PR-511 Readiness Checklist (Must-Pass)

### PR-511A (Extraction Only)
- [ ] OpenAPI JSON after normalization is byte-identical (`make openapi && git diff --exit-code`)
- [ ] No behavior changes in router enablement (same env → same routes in runtime)
- [ ] `legacy_app.py` no longer creates FastAPI app, but keeps legacy shim endpoints intact
- [ ] `app/main.py` remains canonical entrypoint and still registers metrics
- [ ] Router registration logic moved to `app/routers/registration.py` but **preserves current conditional logic** (no guards added)

### PR-511B (Guards + Schema Hygiene)
- [ ] Unified `is_schema_only_mode()` used by ALL conditional routers
- [ ] Test router excluded from public schema (guard or `include_in_schema=False`)
- [ ] Admin endpoints excluded from public schema (`include_in_schema=False`)
- [ ] VIP routes gated in schema-only mode (or explicitly disabled in generator)
- [ ] Exports endpoints excluded from schema unless productized (VIP/PRO tier)
- [ ] Schema generation does not trigger "Table already defined" errors
- [ ] Public schema contains only production-safe endpoints (no test/dev/admin routes)
