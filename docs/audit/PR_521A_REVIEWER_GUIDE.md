# PR-521A — Reviewer Guide

**Purpose:** Quick reference for reviewers to understand scope, risks, and rationale.

---

## What This PR Does

**Frontend-only migration:** Migrates `/api/v1/premium/{targets,plate}` → `/api/v1/pro/nutrition/{targets,plate}` in the web client.

**Files changed:** 6 frontend files (all in `frontend/src/api/` and `frontend/src/pages/`)

---

## Key Changes

### 1. Endpoint Paths
- `targets.ts`: `/api/v1/premium/targets` → `/api/v1/pro/nutrition/targets`
- `plate.ts`: `/api/v1/premium/plate` → `/api/v1/pro/nutrition/plate`
- `client.ts`: `mockUrl()` updated to match new paths

### 2. Type Safety (Critical Fix)
- **Before:** Manual `PlateApiResponse` type (duplicate of OpenAPI schema)
- **After:** OpenAPI-generated `components["schemas"]["PlateResponse"]`
- **Rationale:** Aligns with frontend AGENTS rule: use OpenAPI types from `schema.ts`

### 3. Test Coverage
- Added `Plate API Integration` tests in `targets-integration.test.ts`
- Tests: `getPlate` endpoint + request options passthrough

### 4. Code Clarity
- Added comments clarifying migration intent (premium/* → pro/* routes)
- Exported path constants in `client.ts` (for future use)

---

## What to Review

### ✅ Must Check
1. **Type consistency:** Verify `PlateResponse` is OpenAPI type (not manual duplicate)
2. **Endpoint paths:** Confirm all premium paths migrated to pro/nutrition
3. **Test coverage:** Plate tests should mirror targets test structure
4. **Scope:** Only frontend files changed (no backend/OpenAPI artifacts)

### ⚠️ Known Design Decisions

#### Path Constants vs Literal Strings
**Question:** "Why export constants but use literals in plate.ts/targets.ts?"

**Answer:** Test harness mocks `client.ts`, and importing constants from a mocked module caused `undefined` path regressions. Constants are exported for future use once mock boundaries are cleaned up. This is a pragmatic workaround, not a design flaw.

#### Type Exports
**Question:** "Why export `PlateResponse` from `premium/index.ts`?"

**Answer:** This is the canonical OpenAPI-generated type replacing the manual `PlateApiResponse` duplicate. Export ensures consumers get the correct type.

---

## Common Reviewer Questions

### Q: "Why not rename `createPremiumEndpoint` to `createProEndpoint`?"
**A:** Out of scope for this PR. Module rename (`premium/* → pro/*`) is a separate refactor PR to avoid scope creep.

### Q: "Why not add OpenAPI vendor extensions now?"
**A:** Deferred to PR-521B. This PR is frontend-only; OpenAPI changes require backend coordination.

### Q: "What about weekly endpoints?"
**A:** Deferred to PR-522/523. Weekly endpoints have contract mismatches that require separate analysis.

### Q: "Type checking — where's `npm run typecheck`?"
**A:** Not defined in `package.json`. Type safety is verified via `npm run build` (Vite TypeScript compilation) and `npm test`. This is standard for Vite projects.

---

## Risk Assessment

### ✅ Low Risk
- Frontend-only changes
- No breaking API changes (internal client migration)
- All tests pass
- Build successful

### ⚠️ Potential Concerns (Mitigated)
- **Type consistency:** ✅ Fixed (OpenAPI type used)
- **Test coverage:** ✅ Added (plate integration tests)
- **Scope creep:** ✅ Explicitly bounded (see "Out of Scope" section)

---

## Merge Criteria

✅ **Ready to merge if:**
- All CI checks pass
- Tests: 15/15 pass
- Build: successful
- No backend files in diff
- Reviewer approval

❌ **Block merge if:**
- Any test failures
- Backend files changed
- OpenAPI artifacts modified
- Type errors in build

---

## Related PRs

- **PR-520:** Backend PRO contract routes (merged)
- **PR-521B:** OpenAPI vendor extensions (planned)
- **PR-522:** Weekly endpoint truth table (planned)

---

**Last updated:** 2026-01-12
**For questions:** See `docs/audit/PR_521A_SOURCERY_RESPONSES.md` and `docs/audit/PR_521A_CODERABBIT_RESPONSES.md`
