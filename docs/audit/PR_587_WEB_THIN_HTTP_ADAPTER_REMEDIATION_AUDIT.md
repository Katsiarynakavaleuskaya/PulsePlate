# PR-587 — Web Thin HTTP Adapter Remediation Audit

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `fix/pr-587-web-thin-remediation`
**Author:** @katsiaryna_kavaleuskaya
**Status:** ✅ **Code complete** (ready for review)

---

## A. Scope (факты)

### Q1. Какие **точно 4 файла** сейчас нарушают policy (path + line)?

| File | Line | Violation (до фикса) |
|------|------|----------------------|
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

| File | До фикса | После фикса |
|------|----------|-------------|
| `sharedLinks.ts` | ❌ direct fetch | ✅ `api<SignedLinkResponse>()` |
| `shareFile.ts` | ❌ direct fetch | ✅ `fetchBlob()` (NEW) |
| `ShoplistPreview.tsx` | ❌ direct fetch | ✅ `fetchBlob()` (NEW) |
| `WeeklyPlanViewer.tsx` | ❌ direct fetch | ✅ `fetchBlob()` (NEW) |

---

## B. Anti-scope (жёсткие запреты)

### Q5. Мы **не** создаём "локальные http helpers" в `features/*` или `lib/*`?

**Answer:** ✅ Верно. Все http функции только в `src/api/client.ts`:
- `api()` — существующая, для JSON
- `fetchBlob()` — добавлена для бинарных данных

### Q6. Мы **не** добавляем новые hand-written DTO / не правим OpenAPI в этом PR?

**Answer:** ✅ Верно. Используем:
- Существующие типы из `schema.ts`
- Inline type `SignedLinkResponse` (локальный для sharedLinks.ts)
- Никаких изменений OpenAPI

### Q7. Мы **не** меняем UI-поведение/тексты/flow, кроме транспорта?

**Answer:** ✅ Верно. Только замена транспортного слоя:
- `fetch()` → `api()` для JSON
- `fetch()` → `fetchBlob()` для binary
- UI/UX остаётся неизменным

---

## C. Transport design (как будет после)

### Q8. Для каждого из 4 кейсов: какая **целевая API-функция**?

| File | Target Function | URL Type | Notes |
|------|-----------------|----------|-------|
| `sharedLinks.ts` | `api<SignedLinkResponse>()` | API path | Existing, POST JSON |
| `shareFile.ts` | `fetchBlob()` | External | NEW, no auth headers |
| `ShoplistPreview.tsx` | `fetchBlob()` | API path | NEW, with auth headers |
| `WeeklyPlanViewer.tsx` | `fetchBlob()` | External | NEW, no auth headers |

### Q9. Будут ли какие-то вызовы требовать **blob/arrayBuffer**?

**Answer:** Да, 3 из 4:
- `shareFile.ts`: `fetchBlob()` → `.arrayBuffer()` (для base64 encoding)
- `ShoplistPreview.tsx`: `fetchBlob()` returns Blob directly
- `WeeklyPlanViewer.tsx`: `fetchBlob()` returns Blob directly

**Solution:** `fetchBlob()` returns `Blob`, caller calls `.arrayBuffer()` if needed.

### Q10. Как будет обрабатываться **401/403**?

**URL Classification Rule (Critical):**

| URL Pattern | Classification | Behavior |
|-------------|----------------|----------|
| `/api/...` | **API path** | Auth headers, base URL, 401/403 → clear key + redirect |
| `http(s)://...` | **External** | NO auth headers, NO key clearing, pass-through |
| Other | **Error** | `throw new Error("Invalid URL for fetchBlob")` |

**Security:**
- ✅ API key NEVER sent to external URLs (credential leak prevention)
- ✅ External 401/403 does NOT trigger local auth state changes
- ✅ Signed URLs already contain token in query string

**Implementation:**

```typescript
function classifyUrl(url: string): 'api' | 'absolute' {
  if (url.startsWith('/api/')) return 'api';
  if (url.startsWith('http://') || url.startsWith('https://')) return 'absolute';
  throw new Error(`Invalid URL for fetchBlob: ${url}`);
}
```

---

## D. Tests & Verification (DoD PR-587)

### Q11. `thin-client-guards.test.ts` должен стать **PASS**?

**Answer:** ✅ Да — после PR-587 guards будут зелёными.
- Guards из PR-586 ловили 4 нарушения
- PR-587 исправляет все 4
- Guards станут PASS

### Q12. `rg fetch\(` возвращает **только** `src/api/client.ts`?

**Answer:** ✅ Проверено:

```bash
rg -n "\bfetch\s*\(" frontend/src --type ts | grep -v client.ts | grep -v .test.
# Result: empty (only client.ts has fetch)
```

### Q13. Добавим ли мы regression test?

**Answer:**
- ✅ `shareFile.test.ts` — моки обновлены для `blob()` response
- ✅ `client.fetchBlob.test.ts` — **security contract tests** (4 tests):
  - Test 1: External URL strips auth headers + `credentials: 'omit'`
  - Test 2: API path uses `credentials: 'include'` by default
  - Test 3: 401/403 on API path clears key + redirects
  - Test 4: 401/403 on external URL does NOT affect app state
- **Testing approach:** `vi.stubGlobal` + `setApiClientDependencies()` (no MSW conflicts)

### Q14. Как мы проверим, что export/download работает?

**Local verification:**
1. `npm test` — all tests pass ✅
2. `npm run dev` — start dev server
3. Test shopping list export (CSV/PDF download)
4. Test weekly plan PDF download
5. Test native share on mobile (if possible)

---

## E. Links

### Q15. Ссылка на policy anchor

- **PR-586:** [Guards PR](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/586) (expected-red)

### Q16. Ссылка на ledger item (P0)

- `docs/roadmap/BACKLOG_LEDGER.md` — "Thin HTTP Adapter (Web)"

### Q17. Ссылка на конкретные строки нарушений

- Detected by guards in PR-586
- Fixed in this PR (PR-587)

---

## F. Implementation Summary

### Files changed

| File | Change |
|------|--------|
| `frontend/src/api/client.ts` | +`classifyUrl()`, +`fetchBlob()` |
| `frontend/src/lib/sharedLinks.ts` | `fetch()` → `api()` |
| `frontend/src/lib/shareFile.ts` | `fetch()` → `fetchBlob()` |
| `frontend/src/features/shoplist/ShoplistPreview.tsx` | `fetch()` → `fetchBlob()` |
| `frontend/src/features/plan/WeeklyPlanViewer.tsx` | `fetch()` → `fetchBlob()` |
| `frontend/src/lib/shareFile.test.ts` | Mocks updated for `blob()` |

### `fetchBlob()` signature

```typescript
export async function fetchBlob(
  url: string,
  init?: RequestInit
): Promise<Blob>
```

---

## G. DoD Checklist

### Transport layer
- [x] `fetchBlob()` added to `client.ts`
- [x] `fetchBlob()` does **NOT** send API key to external URLs
- [x] `fetchBlob()` does **NOT** clear key on external 401/403
- [x] URL classification: `/api/...` vs `http(s)://...` handled correctly

### Migrations
- [x] `sharedLinks.ts` migrated to `api()` (JSON, internal)
- [x] `shareFile.ts` migrated to `fetchBlob()` (blob, external signed URL)
- [x] `ShoplistPreview.tsx` migrated to `fetchBlob()` (blob, API path)
- [x] `WeeklyPlanViewer.tsx` migrated to `fetchBlob()` (blob, external signed URL)

### Tests & Verification
- [x] `shareFile.test.ts` mocks updated
- [x] `client.fetchBlob.test.ts` — security contract tests (4 tests)
- [x] `npm test` passes (515 tests green)
- [x] `rg fetch\(` → only `client.ts`
- [ ] CI green (awaiting)

---

**Last updated:** 2026-01-25
**Maintainer:** @katsiaryna_kavaleuskaya
