# PR-524: Weekly Plan Migration — Complete Summary & Answers

**Date:** 2026-01-15
**PR Number:** #524
**Status:** Ready for implementation
**Priority:** P0 (Critical — blocks main page)

---

## 📋 Answers to All Questions

### Q1: Что уже сделано в предыдущих PR?

**✅ PR-521A (#522) — Merged 2026-01-13**
- Targets migration: `/api/v1/premium/targets` → `/api/v1/pro/nutrition/targets`
- Plate migration: `/api/v1/premium/plate` → `/api/v1/pro/nutrition/plate`
- OpenAPI types used (`PlateResponse`)
- Tests: 15/15 PASS
- Build: PASS

**✅ PR-521B (#523) — Merged 2026-01-14**
- OpenAPI vendor extensions (`x-alias-of`, `x-migration-path`)
- Schema regenerated
- Migration paths documented in OpenAPI

**🔴 PR-528 — NOT DONE**
- Weekly plan migration was planned but never implemented
- This PR (#524) completes that work

---

### Q2: Что осталось сделать?

**Единственная критическая задача (P0):**
- Migrate weekly plan endpoint: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
- Update request type: `TargetsRequest` → `WeekPlanRequest`
- Update 3 files: `weekly-plan.ts`, `WeeklyPlanViewer.tsx`, `weekly-plan-integration.test.ts`

---

### Q3: Какие типы использовать?

**Request Type:**
```typescript
import type { components } from '../schema';
type WeekPlanRequest = components['schemas']['WeekPlanRequest'];
```

**Response Type:**
```typescript
type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];
```

**Source:** OpenAPI schema (`frontend/src/api/schema.ts`) — already available after PR-521B.

---

### Q4: Какой endpoint использовать?

**Canonical Endpoint:**
```
POST /api/v1/pro/meal/weekly
```

**Backend Location:** `app/routers/pro.py:241-262`
- Request: `WeekPlanRequest`
- Response: `WeekPlanResponse` (matches `WeeklyMenuResponse` structure)
- Guard: `require_pro_tier()` (PRO tier required)

---

### Q5: Нужен ли адаптер для response?

**❌ НЕТ — адаптер не нужен**

**Причина:**
- Backend `WeekPlanResponse` имеет те же поля, что и `WeeklyMenuResponse`:
  - `daily_menus: List[Dict]`
  - `weekly_coverage: Dict[str, float]`
  - `shopping_list: Dict[str, float]`
  - `total_cost: float`
  - `adherence_score: float`
- UI уже работает с этой структурой (см. `WeeklyPlanViewer.tsx:187-396`)
- Прямая замена типа без адаптера

---

### Q6: Что делать с тестами?

**Обновить:**
1. Request type: `TargetsRequest` → `WeekPlanRequest`
2. Endpoint path: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
3. Imports: добавить `WeekPlanRequest` из `weekly-plan.ts`

**Файл:** `frontend/src/api/__tests__/weekly-plan-integration.test.ts`
- Lines 29, 111: изменить тип запроса
- Lines 97, 354: изменить endpoint path

---

### Q7: Нужно ли обновлять моки?

**Да, если MSW handlers существуют:**
- Файл: `frontend/src/mocks/handlers.ts` (или аналогичный)
- Изменить: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`

---

### Q8: Как проверить, что всё работает?

**1. Type Check:**
```bash
cd frontend
npm run build  # Должно пройти без ошибок
```

**2. Tests:**
```bash
npm test  # Все тесты должны пройти
```

**3. Manual Test:**
- Запустить dev server: `npm run dev`
- Открыть главную страницу
- Проверить Network tab: должен быть запрос на `/api/v1/pro/meal/weekly`
- Убедиться, что weekly plan загружается

**4. Production Check:**
- Нет 404 в логах
- Главная страница обновляется
- Weekly plan генерируется корректно

---

## 🎯 Implementation Plan

### Step 1: Create Branch
```bash
git checkout main
git pull
git checkout -b fix/frontend-weekly-plan-alignment
```

### Step 2: Apply Patches
1. **`frontend/src/api/premium/weekly-plan.ts`**
   - Заменить endpoint path
   - Заменить `TargetsRequest` на `WeekPlanRequest`
   - Экспортировать `WeekPlanRequest`

2. **`frontend/src/features/plan/WeeklyPlanViewer.tsx`**
   - Убрать `fetchJson` и `paths` import
   - Добавить `getWeeklyPlan` import
   - Заменить `fetchJson` call на `getWeeklyPlan(payload)`
   - Обновить типы

3. **`frontend/src/api/__tests__/weekly-plan-integration.test.ts`**
   - Обновить request types
   - Обновить endpoint paths в expectations

4. **MSW handlers (если есть)**
   - Обновить handler path

### Step 3: Verify
```bash
cd frontend
npm run build
npm test
```

### Step 4: Commit
```bash
git add frontend/src/api/premium/weekly-plan.ts
git add frontend/src/features/plan/WeeklyPlanViewer.tsx
git add frontend/src/api/__tests__/weekly-plan-integration.test.ts
git commit -m "fix(frontend): migrate weekly plan to canonical PRO endpoint

Migrate /api/v1/premium/plan/week → /api/v1/pro/meal/weekly:
- Update weekly-plan.ts to use canonical endpoint and WeekPlanRequest
- Update WeeklyPlanViewer.tsx to use getWeeklyPlan() helper
- Update integration tests to use canonical path
- Use OpenAPI types (WeekPlanRequest, WeeklyMenuResponse)

Fixes main page not updating issue (P0)."
```

### Step 5: Update Documentation (Optional, same PR)
```bash
# Update audit doc
git add docs/audit/FRONTEND_BACKEND_ALIGNMENT_AUDIT.md
git commit -m "docs(audit): update status - PR-524 weekly plan migration"
```

---

## 📊 Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Targets | ✅ Migrated | PR-521A (#522) |
| Plate | ✅ Migrated | PR-521A (#522) |
| Weekly Plan | 🔴 **NOT MIGRATED** | **This PR (#524)** |
| BMR | ⚠️ Legacy stable | No migration needed |
| OpenAPI Schema | ✅ Synced | PR-521B (#523) |

---

## 🚨 Critical Issues Fixed

1. **Main page not updating** — Fixed by migrating to canonical endpoint
2. **404 errors** — Fixed by using existing `/api/v1/pro/meal/weekly`
3. **Type mismatch** — Fixed by using OpenAPI `WeekPlanRequest`

---

## ✅ Success Criteria

- [ ] All frontend calls use `/api/v1/pro/meal/weekly`
- [ ] Main page updates correctly
- [ ] Weekly plan generation works
- [ ] No 404s in production logs
- [ ] OpenAPI types used (no manual types)
- [ ] Tests pass (unit + integration)
- [ ] TypeScript compilation passes

---

## 📝 Files Changed Summary

| File | Lines Changed | Type |
|------|---------------|------|
| `weekly-plan.ts` | ~10 | Core API client |
| `WeeklyPlanViewer.tsx` | ~25 | UI component |
| `weekly-plan-integration.test.ts` | ~10 | Tests |
| **Total** | **~45 lines** | **3 files** |

---

## 🔗 Related Documents

- **`docs/audit/PR_524_WEEKLY_PLAN_MIGRATION_AUDIT.md`** — Full audit
- **`docs/audit/PR_524_EXACT_PATCHES.md`** — Exact code patches
- **`docs/audit/FRONTEND_BACKEND_ALIGNMENT_AUDIT.md`** — Overall alignment status
- **`docs/audit/PR_528_PLAN.md`** — Original plan (superseded)

---

## 💡 Key Insights

1. **No adapter needed** — Response structure matches exactly
2. **OpenAPI types available** — After PR-521B, all types are in schema
3. **Consistent pattern** — Follows targets/plate migration (PR-521A)
4. **Minimal changes** — Only 3 files, ~45 lines total
5. **Low risk** — Backend endpoint exists and is tested

---

**Last updated:** 2026-01-15
**Ready for implementation** ✅
