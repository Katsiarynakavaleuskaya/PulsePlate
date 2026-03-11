# OpenAPI Paths Audit — Historical Endpoint Snapshot (2026-01-11)

**Source:** `frontend/src/api/openapi.json`
**Generated:** `make openapi`
**Purpose:** Historical audit snapshot of `/premium/*`, `/pro/*`, `/vip/*` endpoint exposure on 2026-01-11

> Current operator-facing route mapping now lives in `docs/contracts/API_CANONICAL_MAP.md`.
> The canonical generated OpenAPI SoT for CI and thin clients is `frontend/src/api/openapi.json`,
> produced by `scripts/generate_openapi.py`.
> Treat this file as audit evidence and migration analysis, not as the current canonical route map.

---

## Summary

| Namespace | Count | Status |
|-----------|-------|--------|
| `/api/v1/premium/*` | 9 | ⚠️ Deprecated (should be hidden from schema) |
| `/api/v1/pro/*` | 4 | ✅ Canonical PRO namespace |
| `/api/v1/vip/*` | 21 | ✅ Canonical VIP namespace |

**Total:** 34 endpoints

---

## `/api/v1/premium/*` (Deprecated namespace — 9 endpoints)

### Canonical mapping table: "что есть" → "что должно быть"

| Фактический путь            | Фактический tier | Статус            | Канонический target (куда делегировать)                                                       | Action (PR)                                                   |
| --------------------------- | ---------------: | ----------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `/api/v1/premium/plate`     |              PRO | deprecated alias  | **нужен** `/api/v1/pro/nutrition/daily` (или существующий эквивалент)                         | PR-D: сделать pro canon + alias delegation                    |
| `/api/v1/premium/targets`   |              PRO | deprecated alias  | **нужен** `/api/v1/pro/nutrition/targets`                                                     | PR-D: сделать pro canon + alias delegation                    |
| `/api/v1/premium/bmr`       |              PRO | deprecated alias  | (опционально) `/api/v1/pro/bmr`                                                               | Решить: либо заводим pro/bmr, либо оставляем legacy-only      |
| `/api/v1/premium/plan/week` |              VIP | 🔴 **broken naming** | `/api/v1/vip/menu/weekly/plan`                                                                | PR-C: alias → vip canon, скрыть из schema                     |
| `/api/v1/premium/gaps`      |              VIP | deprecated alias  | (скорее) `/api/v1/vip/menu/weekly/plan` (как отдельный режим/флаг) или отдельный vip endpoint | Решить где живёт gaps                                         |
| `/api/v1/premium/exports/day/{plan_id}.csv` | VIP | deprecated alias  | `/api/v1/vip/shoplist/export` (CSV format)                                                    | Унифицировать экспорт                                         |
| `/api/v1/premium/exports/day/{plan_id}.pdf` | VIP | deprecated alias  | `/api/v1/vip/shoplist/export` (PDF format)                                                    | Унифицировать экспорт                                         |
| `/api/v1/premium/exports/week/{plan_id}.csv` | VIP | deprecated alias  | `/api/v1/vip/shoplist/export` (CSV format)                                                     | Унифицировать экспорт                                         |
| `/api/v1/premium/exports/week/{plan_id}.pdf` | VIP | deprecated alias  | `/api/v1/vip/shoplist/export` (PDF format)                                                     | Унифицировать экспорт                                         |

**Critical issue:** `/api/v1/premium/plan/week` requires VIP tier (via `VIP_MODULE_ENABLED`) but lives under `/premium/*` namespace → **architectural confusion** (fixed in PR-C).

---

## `/api/v1/pro/*` (Canonical PRO namespace — 4 endpoints)

| Endpoint | Tier | Status | Notes |
|----------|------|--------|-------|
| `/api/v1/pro/meal/shopping-list` | PRO | ✅ canonical | PRO shopping list |
| `/api/v1/pro/nutrition/day-close` | PRO | ✅ canonical | Daily nutrition log close |
| `/api/v1/pro/nutrition/meal-log` | PRO | ✅ canonical | Meal logging |
| `/api/v1/pro/shoplist/day` | PRO | ✅ canonical | Daily shoplist |

**Current note:** This snapshot predates the current full-schema generator. In the current canonical
generated OpenAPI (`frontend/src/api/openapi.json`), `/api/v1/pro/meal/weekly`,
`/api/v1/pro/nutrition/targets`, and `/api/v1/pro/nutrition/daily` are all present.

---

## `/api/v1/vip/*` (Canonical VIP namespace — 21 endpoints)

### Auto-repair (3 endpoints)

| Endpoint | Tier | Status |
|----------|------|--------|
| `/api/v1/vip/auto-repair/strategies` | VIP | ✅ canonical |
| `/api/v1/vip/auto-repair/suggestions` | VIP | ✅ canonical |
| `/api/v1/vip/auto-repair/weekly` | VIP | ✅ canonical |

### Menu/Planning (3 endpoints)

| Endpoint | Tier | Status | Notes |
|----------|------|--------|-------|
| `/api/v1/vip/menu/weekly/plan` | VIP | ✅ canonical | Main weekly plan endpoint |
| `/api/v1/vip/menu/weekly/repair` | VIP | ✅ canonical | Weekly plan repair |
| `/api/v1/vip/weekly-plan` | VIP | ⚠️ deprecated | Legacy alias (should delegate to `/api/v1/vip/menu/weekly/plan`) |

### Recipes (3 endpoints)

| Endpoint | Tier | Status |
|----------|------|--------|
| `/api/v1/vip/recipes/synthesize` | VIP | ✅ canonical |
| `/api/v1/vip/recipes/templates` | VIP | ✅ canonical |
| `/api/v1/vip/recipes/weekly` | VIP | ✅ canonical |

### Regions (5 endpoints)

| Endpoint | Tier | Status |
|----------|------|--------|
| `/api/v1/vip/regions` | VIP | ✅ canonical |
| `/api/v1/vip/regions/compare/{product_name}` | VIP | ✅ canonical |
| `/api/v1/vip/regions/{region}/categories` | VIP | ✅ canonical |
| `/api/v1/vip/regions/{region}/search` | VIP | ✅ canonical |
| `/api/v1/vip/regions/{region}/stores` | VIP | ✅ canonical |

### Shoplist (6 endpoints)

| Endpoint | Tier | Status |
|----------|------|--------|
| `/api/v1/vip/shoplist/daily` | VIP | ✅ canonical |
| `/api/v1/vip/shoplist/export` | VIP | ✅ canonical |
| `/api/v1/vip/shoplist/formats` | VIP | ✅ canonical |
| `/api/v1/vip/shoplist/generate` | VIP | ✅ canonical |
| `/api/v1/vip/shoplist/preview` | VIP | ✅ canonical |
| `/api/v1/vip/shoplist/weekly` | VIP | ✅ canonical |

### Health (1 endpoint)

| Endpoint | Tier | Status |
|----------|------|--------|
| `/api/v1/vip/health` | VIP | ✅ canonical |

---

## Recommendations (PR execution plan)

### PR-B (schema hygiene): Hide deprecated aliases from OpenAPI

**Goal:** Frontend stops generating types for `/premium/*`.

**Changes:**
- Set `include_in_schema=False` on all `/premium/*` endpoints
- Verify: `make openapi` → zero `/premium/*` paths in `openapi.json`

**DoD:**
- `make openapi` → no `/premium/*` in schema
- Runtime: endpoints still work (backward compatible)
- `pytest tests/test_openapi_determinism.py` passes

**Note:** PR-B description will be created in PR-B branch.

---

### PR-C (VIP alignment): Fix broken naming `/premium/plan/week`

**Status:** ✅ Completed in [PR #1061](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061)

**Goal:** `/api/v1/premium/plan/week` becomes a clean compatibility alias to the VIP canonical route.

**Canonical behavior reference:** `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` is the single narrative source for delegation, runtime compatibility, and schema-hiding behavior for completed PR-C work.

**Shipped outcomes:**
- `/premium/plan/week` delegates to `/vip/menu/weekly/plan`
- VIP business logic no longer lives in the legacy premium shim
- `/premium/plan/week` stays runtime-compatible for callers that still use it
- `/premium/plan/week` is hidden from the public OpenAPI surface

**DoD:**
- ✅ Parity test passes
- ✅ No VIP logic in premium endpoint
- ✅ `/api/v1/premium/plan/week` absent from generated public schema
- ✅ Regression checks cover parity and public-schema absence for the legacy alias

---

### PR-D (PRO canon exposure): Expose canonical PRO endpoints

**Status:** ✅ Completed as part of the current full-schema OpenAPI generation contract.

**Goal:** PRO clients have canonical paths, not legacy `/premium/*`.

**Shipped outcomes:**
- `/api/v1/pro/nutrition/targets` is present in the canonical generated OpenAPI
- `/api/v1/pro/nutrition/daily` is present in the canonical generated OpenAPI
- `/api/v1/pro/meal/weekly` is present in the canonical generated OpenAPI

**DoD:**
- ✅ PRO canonical endpoints appear in `frontend/src/api/openapi.json`
- ✅ Frontend can target `/api/v1/pro/*` contracts from generated schema/types

---

### Long-term (cleanup)

1. **Remove `/premium/*` endpoints** after frontend/iOS migration to canonical namespaces.
2. **Remove `/api/v1/vip/weekly-plan`** after migration to `/api/v1/vip/menu/weekly/plan`.

---

**See also:**
- `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping
- `docs/audit/API_ALIGNMENT_CHECKLIST.md` — alignment checklist
- `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — visibility rules for public/deprecated endpoints
- `AGENTS.md` § "Product tiers and API namespaces (canonical)" — canonical tier policy and namespace governance
