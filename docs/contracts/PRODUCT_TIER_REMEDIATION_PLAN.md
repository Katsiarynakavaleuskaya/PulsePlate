# Product Tier Remediation Plan

**Status:** Action plan with PR-C completed (derived from `PRODUCT_TIER_MAP.md` audit)
**Last updated:** 2026-03-09
**Purpose:** Sequence remediation PRs to fix tier/namespace confusion

---

## Overview

This document outlines the remediation plan to fix architectural confusion between product tiers (FREE/PRO/VIP) and deprecated `/premium/*` namespace.

**Source:** Findings from `docs/contracts/PRODUCT_TIER_MAP.md` audit.

---

## Priority 1: Documentation (✅ Done in PR-A)

* [x] Зафиксировать в `AGENTS.md`: PRO и VIP — реальные уровни, premium — deprecated namespace
* [x] Обновить `API_CANONICAL_MAP.md` с этой таблицей
* [x] Добавить deprecation warnings в OpenAPI schema для `/premium/*`

---

## Priority 2: Code (Gradual, PR-B/PR-C/PR-D)

### PR-B: Schema Hygiene

* [ ] Keep `/premium/*` public-schema exposure limited to explicitly sanctioned compatibility paths only
* [x] Verify: `make openapi` hides `/api/v1/premium/plan/week` and `/api/v1/premium/plan/week-flexible`
* [x] Runtime: endpoints still work (backward compatible)

### PR-C: VIP Alignment

* [x] Fix `/api/v1/premium/plan/week` → delegate to `/api/v1/vip/menu/weekly/plan`
* [x] Remove VIP business logic from premium endpoint (delegation only)
* [x] Parity test: responses equivalent
* [x] Hide `/api/v1/premium/plan/week` from public OpenAPI (`include_in_schema=False`)

**Status:** ✅ Completed in [PR #1061](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061) on 2026-03-09

**Canonical shipped behavior:** The legacy `/api/v1/premium/plan/week` route remains callable for backward compatibility, but it is now a thin compatibility alias over `/api/v1/vip/menu/weekly/plan`. VIP business logic stays in the canonical VIP route, the legacy shim preserves runtime compatibility for callers that have not migrated yet, and the broken-name compatibility path is hidden from the public OpenAPI surface.

### PR-D: PRO Canon Exposure

* [x] Ensure `/api/v1/pro/nutrition/targets` exists and is in schema
* [x] Ensure `/api/v1/pro/nutrition/daily` exists and is in schema
* [x] Ensure `/api/v1/pro/meal/weekly` exists and is in schema

**Status:** ✅ Canonical PRO weekly/targets/daily routes are present in `frontend/src/api/openapi.json`
and are the current generated-contract basis for thin clients.

### Future: Code Cleanup

* [ ] Переименовать `premium_week.py` → `pro_week_legacy.py` (или удалить после миграции)
* [ ] Унифицировать tier requirements для `/premium/*` endpoints:
  * Либо все требуют PRO tier
  * Либо мигрируют на `/api/v1/vip/*` если требуют VIP
* [ ] Добавить `require_pro_tier()` ко всем `/premium/*` endpoints, которые его не имеют

---

## Priority 3: OpenAPI Schema

* [ ] Явно пометить `/premium/*` как deprecated в schema
* [ ] Добавить `x-deprecated: true` и `x-migration-path: /api/v1/pro/*` (или `/api/v1/vip/*`)

---

## Benefits (Why This Matters)

* 🔒 Убираем путаницу в голове и в PR-ах
* 🔧 PR-511A/511B получают **чёткие границы**
* 📱 Frontend и iOS знают, **что есть что**
* 🧠 Новый разработчик не изобретёт "четвёртый уровень"
* 📊 Единый source of truth для контрактов

---

## Known Issues (Fixed in Remediation PRs)

### `/api/v1/premium/plan/week` — Broken Naming

**Issue:** Requires VIP tier but lives under `/premium/*` namespace (deprecated PRO namespace).

**Fix:** ✅ Completed in [PR #1061](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061). See the canonical shipped-behavior note in the completed PR-C section above.

**Source:** `docs/contracts/PRODUCT_TIER_MAP.md` section "Deprecated aliases with wrong namespace"

---

## Related Documents

* `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping (contract/specification)
* `docs/contracts/OPENAPI_PATHS_AUDIT.md` — factual inventory of paths
* `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — visibility rules
* `docs/audit/API_ALIGNMENT_CHECKLIST.md` — alignment checklist
