# PR-586 — Web Thin HTTP Adapter Audit (Policy Enforcement)

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `audit/pr-586-web-thin-http-adapter`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🔴 **Expected RED** (guard tests expose violations)

---

## ⚠️ Expected CI Behavior

**This PR is intentionally expected-red.**

- Guard tests (`thin-client-guards.test.ts`) detect **4 direct fetch() violations**
- This is the "policy enforcement" pattern: guards first → remediation in PR-587
- **Do not fix violations in this PR** — PR-587 handles remediation

**Remediation:** PR-587 (migration of 4 files to `api()`)

---

## 0. Meta / Gatekeeping

### Q0.1 Why is Web Thin Adapter needed now?

**Answer:**

- ✅ iOS Thin HTTP Adapter merged (PR-563)
- ✅ Recorded in BACKLOG_LEDGER as P0
- ✅ Client parity required (iOS + Web must follow same thin-client policy)

**Links:**

- PR-563: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/563>
- PR-585: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/585>
- Ledger item: `docs/roadmap/BACKLOG_LEDGER.md` (P0: Thin HTTP Adapter Web)

### Q0.2 Is this P0 and cannot be split?

**Answer:** ✅ Yes, P0. Single transport layer change, splitting would create inconsistent client states.

### Q0.3 Is this transport-only by fact?

**Answer:** ✅ Yes. Current frontend already follows thin pattern:

- HTTP via `api()` function in `frontend/src/api/client.ts`
- DTOs from OpenAPI schema (`frontend/src/api/schema.ts`)
- No BMI calculations or threshold logic found

---

## 1. Scope — What is ALLOWED

### 1.1 HTTP Layer

#### Q1.1 Where does HTTP happen now?

**Inventory:**

| File | Method | Used by |
|------|--------|---------|
| `frontend/src/api/client.ts` | `api<T>()` | All API calls |
| `frontend/src/api/bmi.ts` | `calculateBMI()` | BMI page |
| `frontend/src/api/premium/bmr.ts` | `getBmr()` | PRO features |
| `frontend/src/api/premium/plate.ts` | `getPlate()` | PRO features |
| `frontend/src/api/premium/targets.ts` | `getTargets()` | PRO features |
| `frontend/src/api/premium/weekly-plan.ts` | `getWeeklyPlan()` | PRO features |

**Status:** ✅ Single HTTP client (`api()` in `client.ts`)

#### Q1.2 Is there a single entry point for HTTP?

**Answer:** ✅ Yes

- Main client: `frontend/src/api/client.ts` exports `api()` and `fetchJson()`
- All endpoints use `api()` internally
- Factory pattern: `createPremiumEndpoint()` for PRO endpoints

#### Q1.3 Clear separation of transport/DTO/consumer?

| Layer | Location | Status |
|-------|----------|--------|
| Transport | `frontend/src/api/client.ts` | ✅ Isolated |
| DTO | `frontend/src/api/schema.ts` | ✅ OpenAPI generated |
| Consumer | `frontend/src/pages/*/`, hooks | ✅ Uses typed APIs |

**Status:** ✅ Clean separation exists

#### Q1.4 Single error envelope (backend-compatible)?

**Answer:** ✅ Yes

```typescript
// client.ts handles:
// - 401/403 → UnauthorizedError + redirect
// - Other errors → Error with HTTP status + body
```

Error mapping:

- 401/403 → `UnauthorizedError` → clear API key + redirect
- 422 → Validation error (passed through)
- 5xx → Server error (passed through)

---

### 1.2 DTO / Contracts

#### Q1.5 All types generated from OpenAPI?

**Answer:** ✅ Yes

```typescript
// bmi.ts
import type { components } from './schema';
type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

// premium/types.ts
export type PlateRequest = components["schemas"]["PlateRequest"];
export type TargetsRequest = components["schemas"]["WHOTargetsRequest"];
```

**Exception:** Some hand-written types in `premium/types.ts`:

- `BmrRequest` (not using OpenAPI schema)
- `BmrApiResponse` (not using OpenAPI schema)

**Action needed:** [ ] Verify if OpenAPI has BMR schemas; migrate if available

#### Q1.6 Schema version binding?

**Answer:**

- `frontend/src/api/schema.ts` — generated from `frontend/src/api/openapi.json`
- Generation via `make openapi` (documented in AGENTS.md)
- No explicit commit hash binding

**Action needed:** [ ] Consider adding schema generation timestamp/hash

#### Q1.7 Web DTO == iOS DTO == Backend schema?

**Answer:** ✅ Semantically aligned

- Web uses OpenAPI-generated types
- iOS uses aligned DTOs (PR-563)
- Both derive from backend Pydantic schemas

---

## 2. Anti-Scope — What is FORBIDDEN

### 2.1 Business Logic

#### Q2.1 BMI logic in web code?

**Grep results:**

```bash
rg "(18\.5|24\.9|25\.0|30\.0|if.*bmi|bmi\s*[<>=]|category.*=|risk.*=)" frontend/src --type ts --type tsx
```

**Findings:**

- ❌ No BMI threshold literals in code
- ❌ No BMI comparisons
- ❌ No category assignments
- ✅ Only in `schema.ts` (OpenAPI comments, not code)

**Status:** ✅ PASS — No BMI business logic

#### Q2.2 Helper functions that aggregate/interpret?

**Answer:** ✅ None found

The UI only displays `response.interpretation` as-is:

```typescript
// BMICalculatePage.tsx
{response.interpretation && (
  <p className="text-sm text-muted">{response.interpretation}</p>
)}
```

#### Q2.3 Backend data used only for display?

**Answer:** ✅ Yes — no reinterpretation detected

---

### 2.2 Duplicate HTTP Logic

#### Q2.4 Direct fetch outside thin adapter?

**Answer:** ❌ **VIOLATIONS FOUND** by guard tests

```
features/plan/WeeklyPlanViewer.tsx:39      - direct fetch()
features/shoplist/ShoplistPreview.tsx:109  - direct fetch()
lib/shareFile.ts:108                       - direct fetch()
lib/sharedLinks.ts:21                      - direct fetch()
```

**Action needed:**
- [ ] Migrate `WeeklyPlanViewer.tsx` to use `api()` or dedicated endpoint
- [ ] Migrate `ShoplistPreview.tsx` to use `api()`
- [ ] Migrate `shareFile.ts` to use `api()`
- [ ] Migrate `sharedLinks.ts` to use `api()`

#### Q2.5 Can `rg fetch\(` return only one module?

**Answer:** ❌ No — 4 files have direct fetch outside `client.ts`

**Status:** ❌ FAIL — requires migration

---

## 3. Thin-Client Policy (Invariants)

#### Q3.1 Web = renderer of contracts, not interpreter?

**Answer:** ✅ Yes — frontend renders backend-provided values

#### Q3.2 Guard mechanisms exist?

| Guard | Status | Location |
|-------|--------|----------|
| ESLint rule | ❌ Not implemented | — |
| Grep-based test | ❌ Not implemented | — |
| CI job | ❌ Not implemented | — |

**Action needed:**

- [ ] Add guard test similar to iOS `ThinClientGuardsTests`
- [ ] Add to CI pipeline

#### Q3.3 Forbidden patterns documented?

**Answer:** ⚠️ Partially — in `AGENTS.md` but not in `frontend/AGENTS.md`

**Action needed:** [ ] Update `frontend/AGENTS.md` with thin-client policy

---

## 4. Error Handling

#### Q4.1 Single error mapping exists?

**Answer:** ✅ Yes — in `client.ts`:

- 401/403 → UnauthorizedError + redirect
- Other errors → pass through with status/body

#### Q4.2 No error masking or normalization?

**Answer:** ✅ Correct — errors passed through as-is

---

## 5. i18n / UX

#### Q5.1 Web shows only backend-provided texts?

**Answer:** ✅ Yes

- `interpretation` field displayed as-is
- `soft_paywall_hook` uses i18n keys from backend

#### Q5.2 No local fallback texts or interpretations?

**Answer:** ✅ Correct — no local interpretation logic

---

## 6. Tests

#### Q6.1 Unit tests for HTTP adapter?

**Location:** `frontend/src/api/__tests__/`

| Test File | Coverage |
|-----------|----------|
| `client.test.ts` | ✅ HTTP client behavior |
| `api-auth-callback.test.ts` | ✅ Auth error handling |
| `api-serialization.test.ts` | ✅ JSON serialization |

**Status:** ✅ Adequate coverage

#### Q6.2 Tests that forbid BMI logic?

**Answer:** ❌ Not implemented

**Action needed:** [ ] Add guard tests (like iOS ThinClientGuardsTests)

#### Q6.3 Tests don't "know" business meaning?

**Answer:** ✅ Tests use mock responses, don't validate BMI values

---

## 7. CI / Tooling

#### Q7.1 CI step that fails on thin-policy violation?

**Answer:** ❌ Not implemented

**Action needed:** [ ] Add CI grep/lint step for forbidden patterns

#### Q7.2 Documented in frontend/AGENTS.md?

**Answer:** ⚠️ Partial — needs update

---

## 8. Security

#### Q8.1 No hardcoded URLs or tokens?

**Answer:** ✅ Correct

- API base from env: `VITE_API_BASE`
- API key from storage: `getStoredApiKey()`

#### Q8.2 401/403 handled centrally?

**Answer:** ✅ Yes — in `client.ts` with redirect to `/enter-key`

---

## 9. Migration / Compatibility

#### Q9.1 PR-586 breaks existing UI?

**Answer:** ✅ No — current code already follows thin pattern

#### Q9.2 Legacy cleanup plan?

**Items for ledger:**

- [ ] Hand-written DTOs in `premium/types.ts` (BmrRequest, BmrApiResponse)
- [ ] Mock files cleanup (duplicate files: `server 2.ts`, `browser 2.ts`)

---

## 10. DoD — Acceptance Criteria

### Self-Check Checklist

- [x] No BMI logic, thresholds, or interpretations in web code
- [x] Single HTTP path (`api()` in `client.ts`)
- [x] DTOs from OpenAPI (mostly — see exceptions)
- [x] Errors not masked
- [x] Guard tests exist ✅ Created
- [x] `frontend/AGENTS.md` updated ✅ Done
- [ ] **Direct fetch violations fixed** (4 files need migration)

---

## Summary

| Area | Status | Action |
|------|--------|--------|
| HTTP Layer | ❌ **4 Violations** | Migrate files to use `api()` |
| DTOs | ⚠️ Mostly compliant | (P2) Migrate BmrRequest/Response |
| Business Logic | ✅ None found | None |
| Error Handling | ✅ Compliant | None |
| Guards | ✅ Implemented | Guard tests created |
| Documentation | ✅ Updated | frontend/AGENTS.md done |

### Conclusion

**Current state:** Frontend mostly follows thin-client pattern, but has **4 direct fetch() violations**.

**PR-586 scope (expanded after audit):**

1. ✅ Add guard tests for forbidden patterns
2. ✅ Update `frontend/AGENTS.md` with thin-client policy
3. **Migrate 4 files** to use `api()` instead of direct `fetch()`:
   - `features/plan/WeeklyPlanViewer.tsx:39`
   - `features/shoplist/ShoplistPreview.tsx:109`
   - `lib/shareFile.ts:108`
   - `lib/sharedLinks.ts:21`
4. (P2) Migrate hand-written DTOs to OpenAPI

**This is a "hardening + migration" PR** — guard tests exposed real violations.

---

## Files to Change in PR-586

| File | Change |
|------|--------|
| `frontend/src/api/__tests__/thin-client-guards.test.ts` | ✅ NEW — guard tests |
| `frontend/AGENTS.md` | ✅ UPDATE — thin-client policy |
| `frontend/src/features/plan/WeeklyPlanViewer.tsx` | MIGRATE — use `api()` |
| `frontend/src/features/shoplist/ShoplistPreview.tsx` | MIGRATE — use `api()` |
| `frontend/src/lib/shareFile.ts` | MIGRATE — use `api()` |
| `frontend/src/lib/sharedLinks.ts` | MIGRATE — use `api()` |
| `docs/roadmap/BACKLOG_LEDGER.md` | UPDATE — after migration done |

---

**Last updated:** 2026-01-25
**Status:** Audit complete. Guard tests created. **4 fetch migrations required.**
**Next step:** Migrate direct fetch() calls to api()
