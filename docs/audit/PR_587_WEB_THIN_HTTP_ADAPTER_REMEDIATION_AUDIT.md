# PR-587 — Web Thin HTTP Adapter Remediation Audit

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `fix/pr-587-web-thin-client-remediation`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🟡 **Audit-first** (code not started)

---

## A. Scope (факты)

### Q1. Какие **точно 4 файла** сейчас нарушают policy (path + line)?

| File | Line | Violation |
|------|------|-----------|
| `frontend/src/lib/sharedLinks.ts` | 21 | `await fetch("/api/v1/export/sign", {...})` |
| `frontend/src/lib/shareFile.ts` | 108 | `await fetch(url)` |
| `frontend/src/features/shoplist/ShoplistPreview.tsx` | 109 | `await fetch(\`/api/v1/shoplist/export.${kind}\`)` |
| `frontend/src/features/plan/WeeklyPlanViewer.tsx` | 39 | `await fetch(url)` |

### Q2. Какие **HTTP сценарии** покрывает каждый файл?

| File | User Action |
|------|-------------|
| `sharedLinks.ts` | Request signed URL for secure file export |
| `shareFile.ts` | Download blob from signed URL for native share |
| `ShoplistPreview.tsx` | Download shopping list as CSV/PDF |
| `WeeklyPlanViewer.tsx` | Download weekly plan PDF from signed URL |

### Q3. Какие **backend endpoints** и методы реально вызываются?

| File | URL | Method | Content-Type |
|------|-----|--------|--------------|
| `sharedLinks.ts` | `/api/v1/export/sign` | POST | `application/json` → JSON response |
| `shareFile.ts` | signed URL (external) | GET | binary → `arrayBuffer()` |
| `ShoplistPreview.tsx` | `/api/v1/shoplist/export.{csv\|pdf}` | GET | binary → `blob()` |
| `WeeklyPlanViewer.tsx` | signed URL (external) | GET | binary → `blob()` |

### Q4. Есть ли уже **готовая обёртка** в `src/api/*` для каждого вызова?

| File | Existing Wrapper | Notes |
|------|-----------------|-------|
| `sharedLinks.ts` | ✅ `api()` | Can use `api<{url: string, ttl?: number, exp?: number}>()` |
| `shareFile.ts` | ❌ None | Needs new `fetchBlob()` for binary |
| `ShoplistPreview.tsx` | ❌ None | Needs new `fetchBlob()` for binary |
| `WeeklyPlanViewer.tsx` | ❌ None | Needs new `fetchBlob()` for binary |

---

## B. Anti-scope (жёсткие запреты)

### Q5. Мы **не** создаём "локальные http helpers" в `features/*` или `lib/*`?

**Answer:** ✅ Верно. Все новые http функции только в `src/api/client.ts`.

### Q6. Мы **не** добавляем новые hand-written DTO / не правим OpenAPI в этом PR?

**Answer:** ✅ Верно. Используем существующие типы из `schema.ts` + inline types где нужно.

### Q7. Мы **не** меняем UI поведение/тексты/flow, кроме транспорта?

**Answer:** ✅ Верно. Только замена `fetch()` → `api()` / `fetchBlob()`.

---

## C. Transport design (как будет после)

### Q8. Для каждого из 4 кейсов: какая **целевая API-функция** будет использована?

| File | Target Function | Notes |
|------|-----------------|-------|
| `sharedLinks.ts` | `api<SignedLinkResponse>()` | Existing function, POST JSON |
| `shareFile.ts` | `fetchBlob()` | **NEW** in `client.ts` |
| `ShoplistPreview.tsx` | `fetchBlob()` | **NEW** in `client.ts` |
| `WeeklyPlanViewer.tsx` | `fetchBlob()` | **NEW** in `client.ts` |

**New function signature:**

```typescript
// In src/api/client.ts
export async function fetchBlob(
  url: string,
  init?: RequestInit,
  options?: ApiOptions
): Promise<Blob>
```

### Q9. Будут ли какие-то вызовы требовать **blob/arrayBuffer**?

**Answer:** Да, 3 из 4 кейсов требуют blob:
- `shareFile.ts`: uses `arrayBuffer()` → need blob → arrayBuffer conversion
- `ShoplistPreview.tsx`: uses `blob()` → direct return
- `WeeklyPlanViewer.tsx`: uses `blob()` → direct return

**Solution:** `fetchBlob()` returns `Blob`, caller can call `.arrayBuffer()` if needed.

### Q10. Как будет обрабатываться **401/403**?

**Answer:** `fetchBlob()` inherits auth handling from `api()`:
- Uses `mergeHeaders()` for API key
- Handles 401/403 via `onAuthError` callback or default redirect
- Consistent with existing `api()` behavior

---

## D. Tests & Verification (DoD PR-587)

### Q11. `thin-client-guards.test.ts` должен стать **PASS**?

**Answer:** ✅ Да, это главный критерий.

### Q12. `rg -n "\\bfetch\\s*\\(" frontend/src` возвращает **только** `src/api/client.ts`?

**Answer:** ✅ Да (и test files, которые excluded).

### Q13. Добавим ли мы regression test на каждый из 4 кейсов?

**Answer:**
- ✅ Unit test for `fetchBlob()` in `client.test.ts`
- 🔄 Existing tests in `shareFile.test.ts` need mock updates (fetch → fetchBlob)
- ⏭️ Component tests optional (transport layer tested)

### Q14. Как мы проверим, что export/download всё ещё работает?

**Local verification steps:**
1. `npm test` — all tests pass
2. `npm run dev` — start dev server
3. Test shopping list export (CSV/PDF download)
4. Test weekly plan PDF download
5. Test native share on mobile (if possible)

---

## E. Links

### Q15. Ссылка на policy anchor

- PR-586: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/586

### Q16. Ссылка на ledger item (P0)

- `docs/roadmap/BACKLOG_LEDGER.md` — "Thin HTTP Adapter (Web)"

### Q17. Ссылка на конкретные строки нарушений

- PR-586 audit: `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md` (Section 2)

---

## Implementation Plan (после утверждения audit)

1. **Add `fetchBlob()` to `client.ts`**
   - Copy auth handling from `api()`
   - Return `Blob` instead of JSON
   - Handle 401/403 consistently

2. **Migrate `sharedLinks.ts`**
   - Replace `fetch()` with `api()`
   - Import `api, getApiBase` from `../api/client`

3. **Migrate `shareFile.ts`**
   - Replace `fetch()` with `fetchBlob()`
   - Keep `.arrayBuffer()` call on result

4. **Migrate `ShoplistPreview.tsx`**
   - Replace `fetch()` with `fetchBlob()`
   - Keep `.blob()` → `fetchBlob()` returns Blob directly

5. **Migrate `WeeklyPlanViewer.tsx`**
   - Replace `fetch()` with `fetchBlob()`
   - Same pattern as ShoplistPreview

6. **Update tests**
   - Update `shareFile.test.ts` mocks

7. **Verify**
   - `npm test` — all pass
   - Guard test PASS
   - Manual verification of exports

---

## DoD PR-587

- [ ] `fetchBlob()` added to `client.ts`
- [ ] `sharedLinks.ts` migrated to `api()`
- [ ] `shareFile.ts` migrated to `fetchBlob()`
- [ ] `ShoplistPreview.tsx` migrated to `fetchBlob()`
- [ ] `WeeklyPlanViewer.tsx` migrated to `fetchBlob()`
- [ ] `shareFile.test.ts` mocks updated
- [ ] `thin-client-guards.test.ts` PASS
- [ ] `rg fetch\(` → only `client.ts`
- [ ] CI green

---

**Last updated:** 2026-01-25
**Maintainer:** @katsiaryna_kavaleuskaya
