# PR-524: GitHub PR Description (Copy-Paste Ready)

## Title

```
fix(frontend): migrate weekly plan to canonical PRO endpoint
```

## Description

```markdown
## What
Migrate weekly plan API usage from deprecated premium path to canonical PRO path.

## Changes
- Frontend weekly plan endpoint: `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
- Request type: `TargetsRequest` → `WeekPlanRequest` (OpenAPI `components.schemas`)
- WeeklyPlanViewer: replace `fetchJson()` call with `getWeeklyPlan(payload)` helper
- Update integration tests to assert canonical path + request type

## Why
Main page weekly plan was broken because frontend still called deprecated/non-working endpoint.

## Verification
- ✅ `pre-commit run --all-files` — PASS
- ✅ `cd frontend && npm test` — 10/10 tests PASS
- ✅ `cd frontend && npm run build` — PASS

## Related
- PR-521A (#522): Targets + Plate migration (completed)
- PR-521B (#523): OpenAPI vendor extensions (completed)
- PR-528: Original plan (superseded by this PR)

## Testing Notes
After merge, verify in browser DevTools → Network:
- ✅ Request goes to `POST /api/v1/pro/meal/weekly`
- ❌ No requests to `/api/v1/premium/plan/week`
- ✅ Main page updates correctly
```

---

**Last updated:** 2026-01-15
**Ready for copy-paste to GitHub PR**
