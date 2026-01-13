# PR-521B: Backend OpenAPI Vendor Extensions (Final Plan)

**Date:** 2026-01-13  
**Status:** 📋 Ready for implementation  
**Scope:** Backend-only, OpenAPI metadata only (no runtime changes)

---

## 🎯 Goal

Add vendor extensions (`x-alias-of`, `x-migration-path`) to deprecated alias endpoints `/api/v1/premium/*` to document canonical replacements in OpenAPI schema.

**Hard constraint:** No runtime behavior changes, only OpenAPI metadata.

---

## 📋 Endpoint Mapping (Canonical)

| Deprecated Alias | Canonical Endpoint | File | Line |
|------------------|-------------------|------|------|
| `/api/v1/premium/plan/week-flexible` | `/api/v1/pro/meal/weekly` | `app/routers/premium_week.py` | 175 |
| `/api/v1/premium/plate` | `/api/v1/pro/nutrition/plate` | `legacy_app.py` | 4024 |
| `/api/v1/premium/targets` | `/api/v1/pro/nutrition/targets` | `legacy_app.py` | 4576 |

---

## ✅ Files to Change (5-7 files)

### 1. `app/routers/premium_week.py`

**Location:** Line 175-179

**Current:**
```python
@router.post(
    "/plan/week-flexible",
    response_model=WeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
    summary="[DEPRECATED] Generate weekly meal plan",
```

**Change to:**
```python
@router.post(
    "/plan/week-flexible",
    response_model=WeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/meal/weekly",
        "x-migration-path": "Migrate to /api/v1/pro/meal/weekly (same contract)",
    },
    summary="[DEPRECATED] Generate weekly meal plan",
```

---

### 2. `legacy_app.py` — `/api/v1/premium/plate`

**Location:** Line 4024-4029

**Current:**
```python
@app.post(
    "/api/v1/premium/plate",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=PlateResponse,
    deprecated=True,
)
```

**Change to:**
```python
@app.post(
    "/api/v1/premium/plate",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=PlateResponse,
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/nutrition/plate",
        "x-migration-path": "Migrate to /api/v1/pro/nutrition/plate (same contract)",
    },
)
```

---

### 3. `legacy_app.py` — `/api/v1/premium/targets`

**Location:** Line 4576-4581

**Current:**
```python
@app.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WHOTargetsResponse,
    deprecated=True,
)
```

**Change to:**
```python
@app.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WHOTargetsResponse,
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/nutrition/targets",
        "x-migration-path": "Migrate to /api/v1/pro/nutrition/targets (same contract)",
    },
)
```

---

### 4. `frontend/src/api/openapi.json` (generated)

**Action:** Regenerate via `make openapi` (will include vendor extensions in schema)

---

### 5. `frontend/src/api/schema.ts` (generated)

**Action:** Regenerate via `make openapi` (will include vendor extensions in TypeScript types)

---

### 6. `tests/test_openapi_determinism.py` (verify)

**Action:** Run `pytest tests/test_openapi_determinism.py` to ensure determinism is preserved

**Expected:** Test should pass (vendor extensions are deterministic metadata)

---

## 🔧 Implementation Steps

### Step 1: Add vendor extensions to endpoints

1. Edit `app/routers/premium_week.py` (line 175)
2. Edit `legacy_app.py` (lines 4024, 4576)

**Pattern:**
```python
openapi_extra={
    "x-alias-of": "/api/v1/pro/...",
    "x-migration-path": "Migrate to /api/v1/pro/... (same contract)",
}
```

### Step 2: Regenerate OpenAPI artifacts

```bash
make openapi
make openapi-check
```

**Expected changes:**
- `frontend/src/api/openapi.json` — vendor extensions appear in schema
- `frontend/src/api/schema.ts` — TypeScript types updated (if openapi-typescript supports vendor extensions)

### Step 3: Verify determinism

```bash
pytest tests/test_openapi_determinism.py -v
```

**Expected:** Test passes (no drift)

### Step 4: Run backend gates

```bash
make verify
```

**Expected:** All checks pass (lint, typecheck, test-fast, diff-cov)

---

## ✅ Review Checklist

- [ ] Vendor extensions added **only** to `/api/v1/premium/*` endpoints
- [ ] `deprecated=True` preserved on all alias endpoints
- [ ] `include_in_schema` not changed (remains default `True`)
- [ ] `response_model` not changed
- [ ] Guards/dependencies not changed
- [ ] Handler bodies not changed (only `openapi_extra` added)
- [ ] `frontend/src/api/openapi.json` regenerated via `make openapi`
- [ ] `frontend/src/api/schema.ts` regenerated via `make openapi`
- [ ] `make openapi-check` passes (artifacts committed)
- [ ] `pytest tests/test_openapi_determinism.py` passes
- [ ] `make verify` passes

---

## 🚫 Out of Scope (Explicitly)

- ❌ Changing `include_in_schema` (keep default `True`)
- ❌ Modifying guards/dependencies
- ❌ Changing response models
- ❌ Modifying handler logic
- ❌ Adding vendor extensions to canonical endpoints
- ❌ Frontend code changes (only generated artifacts)

---

## 📝 Commit Message Template

```
feat(openapi): add vendor extensions to deprecated premium aliases

Add x-alias-of and x-migration-path vendor extensions to:
- /api/v1/premium/plan/week-flexible → /api/v1/pro/meal/weekly
- /api/v1/premium/plate → /api/v1/pro/nutrition/plate
- /api/v1/premium/targets → /api/v1/pro/nutrition/targets

OpenAPI metadata only; no runtime behavior changes.
Regenerated frontend artifacts via make openapi.
```

---

**Last updated:** 2026-01-13
