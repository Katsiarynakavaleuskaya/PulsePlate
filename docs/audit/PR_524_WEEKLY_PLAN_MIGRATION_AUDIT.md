# PR-524: Frontend Weekly Plan Migration to Canonical PRO Endpoint

**Date:** 2026-01-15
**Status:** 🔴 P0 — Critical (blocks main page)
**Type:** Frontend-only migration
**Priority:** Highest

---

## 📋 Executive Summary

### Problem
Frontend still calls deprecated `/api/v1/premium/plan/week` endpoint, causing:
- Main page not updating (UI calls non-existent/deprecated endpoint)
- Weekly plan generation fails (404 or deprecated endpoint)
- User experience broken

### Root Cause
PR-521A (#522) migrated `targets` and `plate` to canonical PRO endpoints, but `weekly-plan` was deferred and never completed.

### Solution
Migrate `weekly-plan.ts` and `WeeklyPlanViewer.tsx` to canonical `/api/v1/pro/meal/weekly` endpoint using OpenAPI types.

---

## ✅ Completed PRs (Context)

### PR-521A (#522) — Merged 2026-01-13
- ✅ `targets.ts` → `/api/v1/pro/nutrition/targets`
- ✅ `plate.ts` → `/api/v1/pro/nutrition/plate`
- ✅ OpenAPI types used (`PlateResponse`)
- ✅ Tests: 15/15 PASS

### PR-521B (#523) — Merged 2026-01-14
- ✅ OpenAPI vendor extensions added
- ✅ Schema regenerated
- ✅ Migration paths documented

---

## 🔴 Current State (Broken)

### Frontend → Backend Mapping

| Frontend Calls | Backend Exists | Status |
|----------------|----------------|--------|
| `/api/v1/premium/plan/week` | ❌ Deprecated alias | **BROKEN** |
| `/api/v1/pro/meal/weekly` | ✅ Canonical | **NOT USED** |

### Files Using Deprecated Endpoint

1. **`frontend/src/api/premium/weekly-plan.ts:8`**
   ```typescript
   export const getWeeklyPlan = createPremiumEndpoint<TargetsRequest, WeeklyMenuResponse>(
     '/api/v1/premium/plan/week'  // ❌ DEPRECATED
   );
   ```

2. **`frontend/src/features/plan/WeeklyPlanViewer.tsx:162`**
   ```typescript
   const week = await fetchJson<WeekPlanResponse>("/api/v1/premium/plan/week", {
     method: "POST",
     body: JSON.stringify(payload),
   });
   ```

3. **`frontend/src/api/__tests__/weekly-plan-integration.test.ts:97, 354`**
   ```typescript
   '/api/v1/premium/plan/week'  // ❌ Test mocks use deprecated path
   ```

---

## 🎯 Backend Canonical Endpoint (Source of Truth)

### Endpoint: `/api/v1/pro/meal/weekly`
- **File:** `app/routers/pro.py:241-262`
- **Method:** POST
- **Request Model:** `WeekPlanRequest` (from `app/routers/pro.py:60-107`)
- **Response Model:** `WeekPlanResponse` (from `app/routers/pro.py:108-115`)
- **Guard:** `require_pro_tier()` (PRO tier required)

### Request Schema (`WeekPlanRequest`)
```python
class WeekPlanRequest(BaseModel):
    sex: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity: Optional[str] = None
    goal: Optional[str] = None
    diet_flags: List[str] = []
    lang: Language = "en"
    targets: Optional[TargetsIn] = None  # Optional pre-calculated targets
```

### Response Schema (`WeekPlanResponse`)
```python
class WeekPlanResponse(BaseModel):
    daily_menus: List[Dict]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float
```

**Note:** Response structure matches `WeeklyMenuResponse` from OpenAPI schema (same fields).

---

## 📝 OpenAPI Schema Status

### Available Types in `frontend/src/api/schema.ts`

1. **Request Type:**
   ```typescript
   components["schemas"]["WeekPlanRequest"]
   ```

2. **Response Type:**
   ```typescript
   components["schemas"]["WeeklyMenuResponse"]
   ```

**Important:** Endpoint `/api/v1/pro/meal/weekly` is **NOT in OpenAPI schema** (excluded due to schema-only mode in `app/routers/pro.py`), but types are available via `components["schemas"]`.

---

## 🔧 Required Changes

### 1. `frontend/src/api/premium/weekly-plan.ts`

**Current:**
```typescript
import { createPremiumEndpoint } from './types';
import type { TargetsRequest } from './types';
import type { components } from '../schema';

export type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];

export const getWeeklyPlan = createPremiumEndpoint<TargetsRequest, WeeklyMenuResponse>(
  '/api/v1/premium/plan/week'
);
```

**After:**
```typescript
import { createPremiumEndpoint } from './types';
import type { components } from '../schema';

// Use OpenAPI types (canonical)
export type WeekPlanRequest = components['schemas']['WeekPlanRequest'];
export type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];

export const getWeeklyPlan = createPremiumEndpoint<WeekPlanRequest, WeeklyMenuResponse>(
  '/api/v1/pro/meal/weekly'  // ✅ Canonical endpoint
);
```

**Changes:**
- Replace `TargetsRequest` with `WeekPlanRequest` (from OpenAPI)
- Update endpoint path: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
- Export `WeekPlanRequest` type for use in `WeeklyPlanViewer.tsx`

---

### 2. `frontend/src/features/plan/WeeklyPlanViewer.tsx`

**Current (lines 53-55, 162):**
```typescript
type WeekPlanResponse =
  paths["/api/v1/premium/plan/week"]["post"]["responses"]["200"]["content"]["application/json"];
type WeekPlanRequest = components["schemas"]["WeekPlanRequest"];

// ... later (line 162)
const week = await fetchJson<WeekPlanResponse>("/api/v1/premium/plan/week", {
  method: "POST",
  body: JSON.stringify(payload),
});
```

**After:**
```typescript
import type { components } from "../../api/schema";
import { getWeeklyPlan } from "../../api/premium/weekly-plan";

type WeekPlanRequest = components["schemas"]["WeekPlanRequest"];
type WeeklyMenuResponse = components["schemas"]["WeeklyMenuResponse"];

// ... later (replace fetchJson call)
const week = await getWeeklyPlan(payload);
setData(week);
```

**Changes:**
- Remove hardcoded `fetchJson` call
- Use `getWeeklyPlan()` helper (consistent with targets/plate pattern)
- Update type imports to use OpenAPI types directly
- Remove deprecated path reference

---

### 3. `frontend/src/api/__tests__/weekly-plan-integration.test.ts`

**Current (lines 97, 354):**
```typescript
expect(mockApi).toHaveBeenCalledWith(
  '/api/v1/premium/plan/week',  // ❌
  // ...
);
```

**After:**
```typescript
expect(mockApi).toHaveBeenCalledWith(
  '/api/v1/pro/meal/weekly',  // ✅
  // ...
);
```

**Changes:**
- Update all test expectations to use canonical path
- Update mock request type from `TargetsRequest` to `WeekPlanRequest` (if needed)

---

### 4. MSW handlers (if they exist)

**File:** `frontend/src/mocks/handlers.ts` (or similar)

**Change:**
- Update handler path from `/api/v1/premium/plan/week` to `/api/v1/pro/meal/weekly`

---

## ✅ Verification Checklist

### Manual Testing
- [ ] Main page loads without 404s
- [ ] Weekly plan generation works
- [ ] No console errors in browser DevTools
- [ ] Network tab shows `/api/v1/pro/meal/weekly` being called
- [ ] Response structure matches UI expectations

### Automated Testing
- [ ] Frontend unit tests pass
- [ ] Integration tests updated and passing
- [ ] TypeScript compilation passes (`npm run build`)
- [ ] No type errors in IDE

### Code Quality
- [ ] Uses OpenAPI types (no manual type duplicates)
- [ ] Consistent with targets/plate migration pattern
- [ ] No hardcoded endpoint paths (use helper function)

---

## 🚨 Risks & Mitigation

### Risk 1: Request Type Mismatch
**Problem:** `TargetsRequest` vs `WeekPlanRequest` may have different fields
**Mitigation:** Use OpenAPI `WeekPlanRequest` type (matches backend exactly)

### Risk 2: Response Shape Change
**Problem:** `WeekPlanResponse` structure may differ from `WeeklyMenuResponse`
**Mitigation:** Backend confirms same structure (`WeekPlanResponse` = `WeeklyMenuResponse` fields)

### Risk 3: PRO Tier Guard
**Problem:** Endpoint requires PRO tier API key
**Mitigation:** Frontend already handles API key via `createPremiumEndpoint` helper

---

## 📊 Success Criteria

- [ ] All frontend calls use `/api/v1/pro/meal/weekly`
- [ ] Main page updates correctly
- [ ] Weekly plan generation works
- [ ] No 404s in production logs
- [ ] OpenAPI types used (no manual types)
- [ ] Tests pass (unit + integration)

---

## 🔗 Related PRs

- **PR-521A (#522):** Targets + Plate migration (completed)
- **PR-521B (#523):** OpenAPI vendor extensions (completed)
- **PR-528:** Original plan (superseded by this PR)

---

## 📝 Commit Message Template

```text
fix(frontend): migrate weekly plan to canonical PRO endpoint

Migrate /api/v1/premium/plan/week → /api/v1/pro/meal/weekly:
- Update weekly-plan.ts to use canonical endpoint and WeekPlanRequest
- Update WeeklyPlanViewer.tsx to use getWeeklyPlan() helper
- Update integration tests to use canonical path
- Use OpenAPI types (WeekPlanRequest, WeeklyMenuResponse)

Fixes main page not updating issue (P0).
```

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation
