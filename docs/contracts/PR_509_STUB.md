# PR-509: Restore Full OpenAPI Schema Generation

**Status:** Planned (follow-up to PR-508)
**Priority:** High (required for complete API contract)
**Estimated effort:** Medium (refactoring import-time ORM deps + DTOs)

---

## Goal

Restore full OpenAPI schema generation by eliminating import-time SQLAlchemy dependencies and adding proper Pydantic response models for VIP/PRO endpoints.

---

## Problem (from PR-508)

PR-508 introduced "schema-only mode" to fix OpenAPI determinism, but this mode **excludes** routers that import SQLAlchemy models at module level:
- `premium_week` router
- `pro` router
- Potentially other VIP/Product routers

This means:
- ❌ OpenAPI schema is incomplete (missing premium/pro endpoints)
- ❌ Frontend TypeScript types are incomplete
- ❌ API contract is not fully documented

---

## Solution

### 1) Remove import-time ORM dependencies

**Current problem:**
```python
# app/routers/premium_week.py
from app.models import WeeklyPlan  # ← Import at module level triggers SQLAlchemy table creation

@router.get("/...")
async def get_weekly_plan(...):
    # Uses WeeklyPlan
```

**Target:**
```python
# app/routers/premium_week.py
# NO module-level ORM imports

@router.get("/...")
async def get_weekly_plan(...):
    from app.models import WeeklyPlan  # ← Lazy import inside function
    # OR
    from app.schemas import WeeklyPlanDTO  # ← Use Pydantic DTO instead
```

**Files to refactor:**
- `app/routers/premium_week.py`
- `app/routers/pro.py`
- Any other routers importing `app.models.*` at module level

---

### 2) Add Pydantic response models

**Current problem:**
```python
@router.get("/api/v1/pro/nutrition/daily")
async def get_daily_nutrition(...) -> dict[str, Any]:  # ← Untyped response
    return {...}
```

**Target:**
```python
@router.get("/api/v1/pro/nutrition/daily", response_model=DailyNutritionResponse)
async def get_daily_nutrition(...) -> DailyNutritionResponse:  # ← Typed response
    return DailyNutritionResponse(...)
```

**DTOs to create:**
- `app/schemas/pro.py` - Pro tier response models
- `app/schemas/premium_week.py` - Premium week response models
- `app/schemas/vip.py` - VIP tier response models (if needed)
- `app/schemas/product.py` - Product catalog response models
- `app/schemas/region.py` - Region catalog response models
- `app/schemas/shoplist.py` - Shopping list response models
- `app/schemas/recipe.py` - Recipe response models

**Goal:** Eliminate all `unknown` types in `frontend/src/api/schema.ts`.

---

### 3) Update OpenAPI generator

**Remove schema-only mode:**
```python
# scripts/generate_openapi.py
# Remove:
# os.environ["PULSEPLATE_OPENAPI"] = "1"
# os.environ["FEATURE_PREMIUM_WEEK_ENABLED"] = "false"
# os.environ["FEATURE_BMI_PRO_ENABLED"] = "false"
# os.environ["BUSINESS_MODULE_ENABLED"] = "false"

# Remove guards in legacy_app.py:
# OPENAPI_MODE = os.getenv("PULSEPLATE_OPENAPI") == "1"
# if not OPENAPI_MODE:
#     from app.routers.premium_week import router as premium_week_router
```

**Or keep as fallback:**
```python
# Keep schema-only mode as fallback if DB unavailable
# But make it explicit and logged
if os.getenv("PULSEPLATE_OPENAPI") == "1":
    logger.warning("Schema-only mode: premium/pro routers excluded")
```

---

### 4) Update determinism test

**Current:**
```python
# tests/test_openapi_determinism.py
# Tests that openapi.json + schema.ts are deterministic
```

**Target:**
```python
# tests/test_openapi_determinism.py
# Tests that FULL openapi.json (with all routers) is deterministic
# Tests that schema.ts has no `unknown` types
```

---

## Checklist

### Phase 1: Remove import-time ORM deps
- [ ] Audit all routers for module-level `from app.models import *`
- [ ] Refactor `app/routers/premium_week.py` to lazy imports or DTOs
- [ ] Refactor `app/routers/pro.py` to lazy imports or DTOs
- [ ] Refactor any other VIP/Product routers
- [ ] Verify no "Table already defined" errors in OpenAPI generation

### Phase 2: Add Pydantic response models
- [ ] Create `app/schemas/pro.py` with Pro tier DTOs
- [ ] Create `app/schemas/premium_week.py` with Premium week DTOs
- [ ] Create `app/schemas/product.py` with Product catalog DTOs
- [ ] Create `app/schemas/region.py` with Region catalog DTOs
- [ ] Create `app/schemas/shoplist.py` with Shopping list DTOs
- [ ] Create `app/schemas/recipe.py` with Recipe DTOs
- [ ] Update all VIP/PRO endpoints to use `response_model=...`
- [ ] Verify no `unknown` types in generated `schema.ts`

### Phase 3: Restore full schema generation
- [ ] Remove schema-only mode from `scripts/generate_openapi.py`
- [ ] Remove guards from `legacy_app.py`
- [ ] Update `AGENTS.md` to document full schema generation
- [ ] Regenerate `openapi.json` and `schema.ts` with full schema
- [ ] Update determinism test to verify full schema

### Phase 4: Testing & validation
- [ ] `pytest tests/test_openapi_determinism.py` passes
- [ ] `make openapi-check` passes
- [ ] Frontend TypeScript types compile without errors
- [ ] No `unknown` types in `schema.ts`
- [ ] All VIP/PRO endpoints appear in OpenAPI schema
- [ ] CI `openapi-sync` job passes

---

## Out of scope (future PRs)

- ❌ Frontend endpoint migrations (separate PR)
- ❌ iOS endpoint migrations (separate PR)
- ❌ Legacy endpoint deprecation (separate PR)
- ❌ OpenAPI 3.1.0 → 4.0 migration (future)

---

## Dependencies

- ✅ PR-508 must be merged first (deterministic OpenAPI generation)
- ✅ Requires SQLAlchemy model audit (identify all import-time deps)
- ✅ Requires Pydantic DTO design (response model contracts)

---

## Success criteria

1. ✅ Full OpenAPI schema includes all routers (premium/pro/VIP)
2. ✅ No `unknown` types in `frontend/src/api/schema.ts`
3. ✅ `make openapi` produces deterministic output (full schema)
4. ✅ `pytest tests/test_openapi_determinism.py` passes
5. ✅ CI `openapi-sync` job passes
6. ✅ No import-time ORM dependencies in routers

---

## Notes

- This PR is **architectural refactoring**, not just "adding endpoints back"
- Focus on **clean separation**: ORM models vs Pydantic DTOs
- Keep schema-only mode as **fallback** if needed (but make it explicit)
- Document all DTO contracts in `docs/contracts/API_DTOS.md` (new file)

---

**Created:** 2026-01-11
**Related:** PR-508 (baseline OpenAPI determinism)
