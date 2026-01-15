# PR-524: Exact Code Patches (Copy-Paste Ready)

**Date:** 2026-01-15
**Purpose:** Exact code changes for weekly plan migration

---

## File 1: `frontend/src/api/premium/weekly-plan.ts`

### Complete File (After Changes)

```typescript
import { createPremiumEndpoint } from './types';
import type { components } from '../schema';

// Use OpenAPI types (canonical)
export type WeekPlanRequest = components['schemas']['WeekPlanRequest'];
export type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];

/**
 * Generate weekly meal plan (PRO tier).
 *
 * Migrated from deprecated /api/v1/premium/plan/week to canonical /api/v1/pro/meal/weekly.
 * Uses OpenAPI WeekPlanRequest and WeeklyMenuResponse types.
 */
export const getWeeklyPlan = createPremiumEndpoint<WeekPlanRequest, WeeklyMenuResponse>(
  '/api/v1/pro/meal/weekly'  // ✅ Canonical endpoint
);
```

### Changes Summary
- ❌ Removed: `import type { TargetsRequest } from './types'`
- ✅ Added: `export type WeekPlanRequest = components['schemas']['WeekPlanRequest']`
- ✅ Changed: Endpoint path `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
- ✅ Changed: Request type `TargetsRequest` → `WeekPlanRequest`
- ✅ Added: JSDoc comment explaining migration

---

## File 2: `frontend/src/features/plan/WeeklyPlanViewer.tsx`

### Changes (Lines 1-10: Imports)

**Before:**
```typescript
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { components, paths } from "../../api/schema";
import { fetchJson } from "../../api/client";
```

**After:**
```typescript
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { components } from "../../api/schema";
import { getWeeklyPlan } from "../../api/premium/weekly-plan";
```

### Changes (Lines 53-56: Type Definitions)

**Before:**
```typescript
type WeekPlanResponse =
  paths["/api/v1/premium/plan/week"]["post"]["responses"]["200"]["content"]["application/json"];
type WeekPlanRequest = components["schemas"]["WeekPlanRequest"];
type UnknownRecord = Record<string, unknown>;
```

**After:**
```typescript
type WeekPlanRequest = components["schemas"]["WeekPlanRequest"];
type WeeklyMenuResponse = components["schemas"]["WeeklyMenuResponse"];
type UnknownRecord = Record<string, unknown>;
```

### Changes (Line 146: State Type)

**Before:**
```typescript
const [data, setData] = useState<WeekPlanResponse | null>(null);
```

**After:**
```typescript
const [data, setData] = useState<WeeklyMenuResponse | null>(null);
```

### Changes (Lines 150-173: useEffect - Replace fetchJson Call)

**Before:**
```typescript
useEffect(() => {
  (async () => {
    setLoading(true);
    setErr(null);
    try {
      const locale = getClientLocale() as WeekPlanRequest["lang"];
      const supportedLangs: WeekPlanRequest["lang"][] = ["en", "ru", "es"];
      const payload: WeekPlanRequest = {
        ...DEFAULT_REQUEST,
        lang: supportedLangs.includes(locale) ? locale : "en",
      };

      const week = await fetchJson<WeekPlanResponse>("/api/v1/premium/plan/week", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setData(week);
    } catch (e: any) {
      setErr(e?.message || "Fetch error");
    } finally {
      setLoading(false);
    }
  })();
}, []);
```

**After:**
```typescript
useEffect(() => {
  (async () => {
    setLoading(true);
    setErr(null);
    try {
      const locale = getClientLocale() as WeekPlanRequest["lang"];
      const supportedLangs: WeekPlanRequest["lang"][] = ["en", "ru", "es"];
      const payload: WeekPlanRequest = {
        ...DEFAULT_REQUEST,
        lang: supportedLangs.includes(locale) ? locale : "en",
      };

      const week = await getWeeklyPlan(payload);
      setData(week);
    } catch (e: any) {
      setErr(e?.message || "Fetch error");
    } finally {
      setLoading(false);
    }
  })();
}, []);
```

### Changes Summary
- ❌ Removed: `import type { paths } from "../../api/schema"`
- ❌ Removed: `import { fetchJson } from "../../api/client"`
- ✅ Added: `import { getWeeklyPlan } from "../../api/premium/weekly-plan"`
- ✅ Changed: `WeekPlanResponse` type → `WeeklyMenuResponse` (from OpenAPI)
- ✅ Changed: `fetchJson<WeekPlanResponse>("/api/v1/premium/plan/week", {...})` → `getWeeklyPlan(payload)`
- ✅ Removed: Manual `method: "POST"` and `body: JSON.stringify(payload)` (handled by helper)

---

## File 3: `frontend/src/api/__tests__/weekly-plan-integration.test.ts`

### Changes (Lines 1–4: Imports)

**Before:**
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getWeeklyPlan } from '../premium/weekly-plan';
import type { WeeklyMenuResponse } from '../premium/weekly-plan';
import type { TargetsRequest } from '../premium/types';
```

**After:**
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getWeeklyPlan } from '../premium/weekly-plan';
import type { WeeklyMenuResponse, WeekPlanRequest } from '../premium/weekly-plan';
```

### Changes (Line 29: Mock Request Type)

**Before:**
```typescript
const mockRequest: TargetsRequest = {
```

**After:**
```typescript
const mockRequest: WeekPlanRequest = {
```

### Changes (Line 97: Test Expectation - Path)

**Before:**
```typescript
expect(mockApi).toHaveBeenCalledWith(
  '/api/v1/premium/plan/week',
  expect.objectContaining({
    method: 'POST',
    body: mockRequest,
    signal: undefined,
  }),
  undefined,
  true
);
```

**After:**
```typescript
expect(mockApi).toHaveBeenCalledWith(
  '/api/v1/pro/meal/weekly',
  expect.objectContaining({
    method: 'POST',
    body: mockRequest,
    signal: undefined,
  }),
  undefined,
  true
);
```

### Changes (Line 111: Second Test - Request Type)

**Before:**
```typescript
const mockRequest: TargetsRequest = {
```

**After:**
```typescript
const mockRequest: WeekPlanRequest = {
```

### Changes (Line 354: Third Test - Path)

**Find and replace all occurrences:**
- `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`

### Changes Summary
- ❌ Removed: `import type { TargetsRequest } from '../premium/types'`
- ✅ Added: `WeekPlanRequest` to import from `'../premium/weekly-plan'`
- ✅ Changed: All `TargetsRequest` → `WeekPlanRequest`
- ✅ Changed: All `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly` in test expectations

---

## File 4: MSW handlers (if they exist)

### File: `frontend/src/mocks/handlers.ts` (or similar)

**Find:**
```typescript
rest.post('/api/v1/premium/plan/week', ...)
```

**Replace with:**
```typescript
rest.post('/api/v1/pro/meal/weekly', ...)
```

---

## Verification Steps

### 1. Type Check
```bash
cd frontend
npm run build  # Should pass without type errors
```

### 2. Tests
```bash
npm test  # All tests should pass
```

### 3. Manual Test
1. Start dev server: `npm run dev`
2. Navigate to main page
3. Check Network tab: should see `/api/v1/pro/meal/weekly` (not `/api/v1/premium/plan/week`)
4. Verify weekly plan loads correctly

---

## Summary of All Changes

| File | Changes | Lines Affected |
|------|---------|----------------|
| `weekly-plan.ts` | Endpoint path, request type, exports | ~10 lines |
| `WeeklyPlanViewer.tsx` | Imports, type definitions, API call | ~25 lines |
| `weekly-plan-integration.test.ts` | Request types, endpoint paths | ~5-10 lines |
| `mocks/handlers.ts` (if exists) | Handler path | ~1 line |

**Total:** ~40-50 lines changed across 3-4 files

---

**Last updated:** 2026-01-15
**Ready for copy-paste implementation**
