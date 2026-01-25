# PR-587 — Web Thin HTTP Adapter Remediation Audit

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `fix/pr-587-web-thin-remediation` (TBD)
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🟡 **Audit-first** (code not started)
**Policy anchor:** PR-586 (guards, expected-red)

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
| `sharedLinks.ts` | Запрос подписанной ссылки для безопасного экспорта файла |
| `shareFile.ts` | Скачивание blob с подписанного URL для native share |
| `ShoplistPreview.tsx` | Скачивание списка покупок как CSV/PDF |
| `WeeklyPlanViewer.tsx` | Скачивание PDF недельного плана с подписанного URL |

### Q3. Какие **backend endpoints** и методы реально вызываются?

| File | URL | URL Type | Method | Response |
|------|-----|----------|--------|----------|
| `sharedLinks.ts` | `/api/v1/export/sign` | **API path** | POST | JSON `{url, ttl, exp}` |
| `shareFile.ts` | `https://...` (signed URL) | **External** | GET | blob → arrayBuffer |
| `ShoplistPreview.tsx` | `/api/v1/shoplist/export.{csv\|pdf}` | **API path** | GET | blob |
| `WeeklyPlanViewer.tsx` | `https://...` (signed URL) | **External** | GET | blob |

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

| File | Target Function | URL Type | Notes |
|------|-----------------|----------|-------|
| `sharedLinks.ts` | `api<SignedLinkResponse>()` | API path | Existing, POST JSON |
| `shareFile.ts` | `fetchBlob()` | External | **NEW**, no auth headers |
| `ShoplistPreview.tsx` | `fetchBlob()` | API path | **NEW**, with auth headers |
| `WeeklyPlanViewer.tsx` | `fetchBlob()` | External | **NEW**, no auth headers |

### Q9. Будут ли какие-то вызовы требовать **blob/arrayBuffer**?

**Answer:** Да, 3 из 4 кейсов требуют blob:
- `shareFile.ts`: uses `arrayBuffer()` → need blob → arrayBuffer conversion
- `ShoplistPreview.tsx`: uses `blob()` → direct return
- `WeeklyPlanViewer.tsx`: uses `blob()` → direct return

**Solution:** `fetchBlob()` returns `Blob`, caller can call `.arrayBuffer()` if needed.

### Q10. Как будет обрабатываться **401/403**?

**URL Classification Rule (Critical):**

| URL Pattern | Classification | Behavior |
|-------------|----------------|----------|
| `/api/...` | **API path** | Prepend `VITE_API_BASE`, attach auth headers, apply `onAuthError` (401/403 → clear key + redirect) |
| `http://...` or `https://...` | **External signed URL** | **NO** auth headers, **NO** api-base prepend, **NO** key clearing / redirect |
| Other | **Error** | Throw immediately (prevent silent wrong requests) |

**Security rationale:**
- Signed URLs already contain auth token in query string
- Sending API key to external domain = credential leak risk
- External 401/403 should not trigger local auth state changes

**New function signature:**

```typescript
// In src/api/client.ts
export async function fetchBlob(
  url: string,
  init?: RequestInit
): Promise<Blob>
```

**Internal logic:**
- `classifyUrl(url)` → `'api' | 'absolute'`
- API path: prepend base, add auth headers, handle 401/403
- External: pass-through fetch, no auth modification

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

- Guards PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/586>

### Q16. Ссылка на ledger item (P0)

- `docs/roadmap/BACKLOG_LEDGER.md` — "PR-587 Web Thin HTTP Adapter — Remediation"

### Q17. Ссылка на конкретные строки нарушений

- Guards PR audit: `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md` (Section 2)

---

## F. Implementation Plan

1. **Add `fetchBlob()` to `client.ts`**
   - Add `classifyUrl()` helper
   - Implement auth handling for API paths only
   - Return `Blob` instead of JSON

2. **Migrate `sharedLinks.ts`**
   - Replace `fetch()` with `api()`
   - Import `api, getApiBase` from `../api/client`

3. **Migrate `shareFile.ts`**
   - Replace `fetch()` with `fetchBlob()`
   - Keep `.arrayBuffer()` call on result

4. **Migrate `ShoplistPreview.tsx`**
   - Replace `fetch()` with `fetchBlob()`

5. **Migrate `WeeklyPlanViewer.tsx`**
   - Replace `fetch()` with `fetchBlob()`

6. **Update tests**
   - Update `shareFile.test.ts` mocks

7. **Verify**
   - `npm test` — all pass
   - Guard tests PASS
   - Manual verification of exports

---

## G. DoD Checklist

### Transport layer
- [ ] `fetchBlob()` added to `client.ts`
- [ ] `fetchBlob()` must **NOT** send API key to external URLs (security)
- [ ] `fetchBlob()` must **NOT** clear stored key / redirect on 401/403 for external URLs
- [ ] URL classification: `/api/...` vs `http(s)://...` handled correctly

### Migrations
- [ ] `sharedLinks.ts` migrated to `api()` (JSON, internal)
- [ ] `shareFile.ts` migrated to `fetchBlob()` (blob, external signed URL)
- [ ] `ShoplistPreview.tsx` migrated to `fetchBlob()` (blob, API path)
- [ ] `WeeklyPlanViewer.tsx` migrated to `fetchBlob()` (blob, external signed URL)

### Tests & Verification
- [ ] `shareFile.test.ts` mocks updated
- [ ] `thin-client-guards.test.ts` PASS
- [ ] `rg -n "\\bfetch\\s*\\(" frontend/src` → only `src/api/client.ts`
- [ ] CI green

---

**Last updated:** 2026-01-25
**Maintainer:** @katsiaryna_kavaleuskaya
