# PR-510: legacy_app.py Audit

**Date:** 2026-01-11  
**Status:** Analysis phase (no code changes)  
**Goal:** Transform `legacy_app.py` into a pure compatibility-proxy by identifying orchestration/bootstrap logic that must be extracted.

---

## 1. Side-Effects at Import Time

### Module-Level Execution (on `import legacy_app`)

| Line Range | Code Block | Side-Effect | Impact |
|------------|------------|-------------|--------|
| 1-94 | Imports (stdlib, fastapi, app modules) | Module loading, potential circular imports | Medium |
| 95-101 | `premium_week_router`, `pro_router` declarations | Module-level attributes created | Low |
| 107-119 | Scheduler imports (try/except) | Conditional module loading | Low |
| 128-138 | `Limiter` import (try/except) | Conditional middleware availability | Low |
| 149-160 | VIP router registration setup | `_register_vip_routes` assignment, `VIP_MODULE_ENABLED` set | **High** |
| 162-169 | VIP router backward-compat | `vip_router` attribute set | Low |
| 57 | `_register_pro_routes` import | Router registration function imported | **High** |
| 300-400+ | Environment variable reads | `os.getenv()` calls for feature flags | **High** |
| 500-600+ | Database initialization | `init_db()` potentially called | **High** |
| 1000-1100+ | Router registration (at module bottom) | `app.include_router()` calls | **High** |

### Critical Side-Effects

1. **Router Registration Logic** (lines ~1075-1100):
   - VIP routes registered via `_register_vip_routes(app)` if available
   - PRO routes registered via `_register_pro_routes(app)`
   - Multiple conditional `app.include_router()` calls
   - **Impact:** OpenAPI schema generation depends on import-time router registration order

2. **Feature Flag Evaluation** (scattered):
   - `VIP_MODULE_ENABLED` set at import time (line 157)
   - `FEATURE_PREMIUM_WEEK_ENABLED` checked (line ~1161)
   - `FEATURE_BMI_PRO_ENABLED` checked (line ~5672)
   - **Impact:** Router availability determined before app creation

3. **Environment Variable Reads**:
   - `APP_ENV`, `ENVIRONMENT`, `ENABLE_TEST_ROUTES` read at module level
   - **Impact:** Test router inclusion depends on env vars at import time

---

## 2. Block Classification

| Block | Lines | Role | Status | Notes |
|-------|-------|------|--------|-------|
| Imports (stdlib) | 1-30 | Compatibility | ✅ OK | Standard library imports |
| Imports (app modules) | 49-94 | Compatibility | ✅ OK | Module imports |
| Router declarations | 95-101 | Compatibility | ✅ OK | Public surface for tests |
| Scheduler fallback | 107-119 | Orchestration | ❌ DEBT | Should be in app lifecycle |
| Limiter fallback | 128-138 | Orchestration | ❌ DEBT | Should be in middleware setup |
| VIP registration setup | 149-160 | Orchestration | ❌ DEBT | Registration logic, not proxy |
| PRO registration import | 57 | Orchestration | ❌ DEBT | Registration logic, not proxy |
| Helper functions | 172-400 | Feature logic | ❌ DEBT | BMI/planning helpers should be in core |
| FastAPI app creation | ~500 | Orchestration | ❌ DEBT | App creation is orchestration |
| Middleware setup | ~600-800 | Orchestration | ❌ DEBT | Should be in app factory |
| Router registration | 1000-1100 | Orchestration | ❌ DEBT | Should be in registration module |
| Endpoint definitions | 1100-5600 | Feature logic | ❌ DEBT | Endpoints should be in routers |
| Legacy aliases | 1100-1200 | Compatibility | ✅ OK | Backward-compat endpoints |

---

## 3. Router Registration Map

### Current Registration Flow

```
import legacy_app
  ↓
Module-level imports execute
  ↓
Feature flags evaluated (VIP_MODULE_ENABLED, etc.)
  ↓
Registration functions imported (_register_vip_routes, _register_pro_routes)
  ↓
FastAPI app created: app = FastAPI(...)
  ↓
Routers registered (scattered throughout file):
  - Basic routers (foods, recipes, users, catalog) - lines ~1078-1087
  - VIP routes (via _register_vip_routes) - line ~1076
  - PRO routes (via _register_pro_routes) - line ~1080
  - Premium week router (conditional) - line ~1161
  - Test router (conditional) - line ~1158
  - BMI Pro router (conditional) - line ~5672
```

### Router Registration Details

| Router | Registration Method | Condition | Line | OpenAPI Impact |
|--------|---------------------|-----------|------|----------------|
| `foods_router` | Direct `app.include_router()` | Always | ~1078 | ✅ Always in schema |
| `recipes_router` | Direct `app.include_router()` | Always | ~1079 | ✅ Always in schema |
| `users_router` | Direct `app.include_router()` | Always | ~1081 | ✅ Always in schema |
| `catalog_router` | Direct `app.include_router()` | Always | ~1082 | ✅ Always in schema |
| VIP routes | `_register_vip_routes(app)` | `VIP_MODULE_ENABLED` | ~1076 | ⚠️ Conditional |
| PRO routes | `_register_pro_routes(app)` | Always (imported) | ~1080 | ⚠️ Conditional (schema-only mode) |
| Premium week | Direct `app.include_router()` | `FEATURE_PREMIUM_WEEK_ENABLED` | ~1161 | ⚠️ Conditional |
| Test router | Direct `app.include_router()` | Env-based | ~1158 | ⚠️ Conditional |
| BMI Pro | Direct `app.include_router()` | `FEATURE_BMI_PRO_ENABLED` | ~5672 | ⚠️ Conditional |

### Registration Inconsistencies

1. **VIP vs PRO Pattern Mismatch**:
   - VIP: Uses centralized `_register_vip_routes()` function
   - PRO: Uses centralized `_register_pro_routes()` function
   - Premium week: Direct `app.include_router()` (inconsistent)
   - BMI Pro: Direct `app.include_router()` (inconsistent)

2. **Conditional Logic Scattered**:
   - Feature flags checked in multiple places
   - No single source of truth for router availability

3. **OpenAPI Schema-Only Mode**:
   - PRO routes respect `PULSEPLATE_OPENAPI=1` guard (in `pro_registration.py`)
   - Other routers do not have schema-only guards
   - **Impact:** Schema generation may include routers that shouldn't be in schema-only mode

---

## 4. OpenAPI Generation Impact

### Does `legacy_app.py` Participate in Schema Generation?

**Yes**, in multiple ways:

1. **Router Registration Order**:
   - Routers registered at module level (lines ~1075-1100)
   - Order affects OpenAPI `paths` ordering
   - **Evidence:** `scripts/generate_openapi.py` imports `app.main.app`, which imports `legacy_app.app`

2. **Conditional Router Inclusion**:
   - Feature flags determine which routers are registered
   - Schema-only mode (`PULSEPLATE_OPENAPI=1`) affects PRO routes
   - **Evidence:** `pro_registration.py` checks `_is_openapi_schema_only_mode()`

3. **Endpoint Definitions**:
   - Many endpoints defined directly in `legacy_app.py` (lines 1100-5600)
   - These appear in OpenAPI schema
   - **Evidence:** FastAPI auto-generates schema from `@app.get/post()` decorators

### Runtime vs Schema-Only Differences

| Aspect | Runtime | Schema-Only Mode |
|--------|---------|------------------|
| PRO routes | Registered via `_register_pro_routes()` | Skipped (returns `None, None`) |
| Premium week routes | Registered if feature flag enabled | Registered if feature flag enabled |
| Endpoint definitions | All included | All included (no guard) |

**Problem:** Schema-only mode only affects PRO routes, not other conditional routers.

---

## 5. Responsibility Boundaries

### ✅ MUST REMAIN in `legacy_app.py` (Compatibility-Proxy)

1. **Public Surface Attributes**:
   - `premium_week_router: Optional[APIRouter] = None`
   - `pro_router: Optional[APIRouter] = None`
   - `vip_router: Optional[APIRouter] = None`
   - **Reason:** Tests and `app/__init__.py` expect these via `hasattr()` and `patch()`

2. **Legacy Endpoint Aliases**:
   - `/api/nutrition/{date_str}` → delegates to PRO endpoint
   - Other backward-compat endpoints
   - **Reason:** iOS/legacy clients depend on these paths

3. **Re-exports** (if any):
   - Functions/classes re-exported for backward compatibility
   - **Reason:** External code imports from `legacy_app`

### ❌ MUST BE EXTRACTED (Orchestration/Bootstrap)

1. **App Creation**:
   - `app = FastAPI(...)` instantiation
   - **Target:** `app/main.py` or `app/factory.py`

2. **Router Registration**:
   - All `app.include_router()` calls
   - Registration orchestration logic
   - **Target:** `app/routers/registration.py` (unified registration module)

3. **Middleware Setup**:
   - `app.add_middleware()` calls
   - Middleware configuration
   - **Target:** `app/middleware/setup.py` or app factory

4. **Feature Flag Evaluation**:
   - Module-level `os.getenv()` calls
   - `VIP_MODULE_ENABLED` assignment
   - **Target:** `app/utils/feature_flags.py` (already exists, but needs cleanup)

5. **Conditional Imports**:
   - `try/except ImportError` blocks for optional modules
   - **Target:** Lazy imports in registration functions

6. **Helper Functions**:
   - BMI calculation helpers
   - Planning helpers
   - **Target:** `core/bmi/` or `core/planning/`

7. **Endpoint Definitions**:
   - All `@app.get/post()` endpoint definitions
   - **Target:** Move to appropriate routers (`app/routers/*.py`)

---

## 6. Problem Statement

### Why `legacy_app.py` ≠ Compatibility-Proxy Currently

1. **Orchestration Logic Mixed with Proxy**:
   - App creation, router registration, and middleware setup all happen in the same file
   - No separation between "what legacy needs" and "how app is built"

2. **Feature Logic Embedded**:
   - Endpoint implementations directly in `legacy_app.py`
   - Business logic mixed with compatibility layer

3. **Import-Time Side-Effects**:
   - Feature flags evaluated at import time
   - Routers registered at module level
   - **Impact:** Cannot import `legacy_app` without triggering full app initialization

4. **Inconsistent Registration Patterns**:
   - Some routers use centralized registration (VIP, PRO)
   - Others use direct `app.include_router()` calls
   - **Impact:** Hard to reason about router availability and OpenAPI schema

5. **OpenAPI Generation Coupling**:
   - Schema generation depends on import-time router registration
   - Schema-only mode only partially implemented
   - **Impact:** Non-deterministic schema generation (partially fixed in PR-508)

---

## 7. Scope for Next Code-PR (PR-511)

### Phase 1: Extract Orchestration (Minimal Diff)

1. **Create `app/main.py`**:
   - Move `app = FastAPI(...)` creation
   - Move middleware setup
   - Keep `legacy_app.py` as re-export: `from app.main import app`

2. **Create `app/routers/registration.py`**:
   - Unified router registration function
   - Single source of truth for router availability
   - Respects feature flags and schema-only mode

3. **Update `legacy_app.py`**:
   - Remove orchestration logic
   - Keep only compatibility-proxy code
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

## 8. Dependencies and Risks

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

## 9. Success Criteria

### PR-510 (Analysis) ✅

- [x] Side-effects documented
- [x] Block classification complete
- [x] Router registration map created
- [x] OpenAPI impact analyzed
- [x] Responsibility boundaries defined
- [x] Problem statement clear
- [x] Scope for next PR defined

### PR-511 (Code) - Future

- [ ] `legacy_app.py` contains only compatibility-proxy code
- [ ] Orchestration moved to `app/main.py` and `app/routers/registration.py`
- [ ] All tests pass
- [ ] OpenAPI schema generation unchanged (deterministic)
- [ ] No breaking changes to public surface

---

## 10. Notes

- This audit is **analysis-only**. No code changes in PR-510.
- Focus is on **identifying what must move**, not **how to move it**.
- Next PR (PR-511) will implement the extraction with minimal diff.
- PR-512+ will handle feature logic extraction (endpoints, helpers).
