# PR-586 — Web Thin HTTP Adapter Audit (Policy Enforcement)

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `audit/pr-586-web-thin-http-adapter`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🔴 **Expected RED** (guard tests expose violations)

---

## ⚠️ Expected CI Behavior

**This PR is intentionally expected-red.**

**Expected red reason:** Direct fetch guard only (4 violations detected by `thin-client-guards.test.ts`).

- Guard tests (`thin-client-guards.test.ts`) detect **4 direct fetch() violations**
- This is the "policy enforcement" pattern: guards first → remediation follows
- **Do not fix violations in this PR** — remediation is a separate PR

All other checks (linting, markdownlint, BMI logic guard) must be **green**.

**Decision:** This PR = policy+guards (expected-red), remediation PR = fixes violations (green)

---

## 0. Meta / Gatekeeping

### Q0.1 Why is Web Thin Adapter needed now?

**Answer:**
- ✅ iOS Thin HTTP Adapter in review (PR-563)
- ✅ Recorded in BACKLOG_LEDGER as P0
- ✅ Client parity required (iOS + Web must follow same thin-client policy)

**Links:**
- PR-563: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/563>
- Ledger item: `docs/roadmap/BACKLOG_LEDGER.md` (P0: Web Thin HTTP Adapter)

### Q0.2 Split decision

**Answer:** ✅ Intentional split for policy enforcement pattern:
- **This PR:** Guards + policy documentation (expected-red)
- **Remediation PR:** Fixes 4 violations (expected-green)

**Rationale:** Guards must fail before remediation to prove they work.

### Q0.3 Is this transport-only by fact?

**Answer:** ✅ Yes. Current frontend already follows thin pattern for most code:
- HTTP via `api()` function in `frontend/src/api/client.ts`
- DTOs from OpenAPI schema (`frontend/src/api/schema.ts`)
- No BMI calculations or threshold logic found

**Exception:** 4 files use direct `fetch()` — violations detected by guards.

---

## 1. Guard Tests Implementation

### Q1.1 Guard tests exist?

**Answer:** ✅ Implemented

**Location:** `frontend/src/api/__tests__/thin-client-guards.test.ts`

**Features:**
- Block comment handling (`/* ... */` state tracking)
- Shared file scanning helper (`collectSourceFiles()`)
- Exact path check for allowed fetch file (`api/client.ts`)
- Consistent comment skip in both tests

### Q1.2 What do guards check?

| Guard | Status | Description |
|-------|--------|-------------|
| BMI thresholds | ✅ PASS | No 18.5/24.9/25/30 literals |
| BMI comparisons | ✅ PASS | No `if (bmi < ...)` |
| Category/risk assignments | ✅ PASS | No hardcoded categories |
| Local BMI functions | ✅ PASS | No `computeBMI()` etc. |
| Direct fetch | 🔴 FAIL | 4 violations detected |

### Q1.3 frontend/AGENTS.md updated?

**Answer:** ✅ Done — Thin HTTP Adapter Policy documented

---

## 2. Detected Violations (4 direct fetch)

| File | Line | Endpoint | Issue |
|------|------|----------|-------|
| `features/plan/WeeklyPlanViewer.tsx` | 39 | signed URL download | direct `fetch(url)` |
| `features/shoplist/ShoplistPreview.tsx` | 109 | `/api/v1/shoplist/export.{csv\|pdf}` | direct `fetch()` |
| `lib/shareFile.ts` | 108 | file download URL | direct `fetch(url)` |
| `lib/sharedLinks.ts` | 21 | `/api/v1/export/sign` | direct `fetch()` |

**Remediation:** Separate PR (tracked in `docs/roadmap/BACKLOG_LEDGER.md`)

---

## 3. DoD PR-586

- [x] Guard tests created (`thin-client-guards.test.ts`)
- [x] Block comment handling (A)
- [x] Shared file scanning helper (B)
- [x] Stricter client.ts skip (C)
- [x] Consistent comment skip (D)
- [x] `frontend/AGENTS.md` updated with thin-client policy
- [x] `AGENTS.md` updated with guard references
- [x] `BACKLOG_LEDGER.md` updated (guards + remediation split)
- [x] Audit doc created
- [x] CI expected RED (4 violations — this is correct)

---

## 4. Files Changed in PR-586

| File | Change |
|------|--------|
| `frontend/src/api/__tests__/thin-client-guards.test.ts` | NEW — guard tests |
| `frontend/AGENTS.md` | UPDATE — thin-client policy |
| `AGENTS.md` | UPDATE — guard references |
| `docs/roadmap/BACKLOG_LEDGER.md` | UPDATE — PR-586/PR-587 split |
| `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md` | NEW — this doc |

---

## 5. Remediation Audit Questions (for follow-up PR)

### Scope
1. Какие **точно файлы** устраняем? → 4 файла (см. таблицу выше)
2. Какие **endpoint paths** затронуты?
   - Weekly plan viewer: signed URL (blob download)
   - Shoplist export: `/api/v1/shoplist/export.{csv|pdf}` (blob)
   - shareFile: generic URL (blob download)
   - sharedLinks: `/api/v1/export/sign` (JSON)

### Anti-scope
3. Не добавляем "wrapper вокруг fetch" в feature-слое? → Нет, используем `api()` или `fetchBlob()`
4. Не создаём новый `client.ts`-дубликат? → Нет

### Implementation sanity
5. Есть ли готовые API функции? → Нужен `fetchBlob()` для blob downloads
6. Сохраняем ли 401/403 через `api()`? → Да, `fetchBlob()` наследует auth handling

### Verification
7. `npm test` зелёный + guard test зелёный? → DoD remediation PR
8. `rg -n "\bfetch\s*\(" frontend/src` → только `client.ts`
9. Новые hand-written DTO? → Нет

### DoD Remediation PR
10. Guards PASS
11. Нет direct fetch вне client.ts
12. PR body: ссылка на guards PR как policy anchor

---

**Last updated:** 2026-01-25
**Next step:** Merge this PR (expected-red), then remediation PR
