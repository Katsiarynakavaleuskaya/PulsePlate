# Product Tier Remediation Plan

**Status:** Action plan (derived from `PRODUCT_TIER_MAP.md` audit)
**Last updated:** 2026-01-11
**Purpose:** Sequence remediation PRs to fix tier/namespace confusion

---

## Overview

This document outlines the remediation plan to fix architectural confusion between product tiers (FREE/PRO/VIP) and deprecated `/premium/*` namespace.

**Source:** Findings from `docs/contracts/PRODUCT_TIER_MAP.md` audit.

---

## Priority 1: Documentation (✅ Done in PR-A)

* [x] Зафиксировать в `AGENTS.md`: PRO и VIP — реальные уровни, premium — deprecated namespace
* [ ] Обновить `API_CANONICAL_MAP.md` с этой таблицей
* [ ] Добавить deprecation warnings в OpenAPI schema для `/premium/*`

---

## Priority 2: Code (Gradual, PR-B/PR-C/PR-D)

### PR-B: Schema Hygiene

* [ ] Set `include_in_schema=False` on all `/premium/*` endpoints
* [ ] Verify: `make openapi` → zero `/premium/*` paths in schema
* [ ] Runtime: endpoints still work (backward compatible)

### PR-C: VIP Alignment

* [ ] Fix `/api/v1/premium/plan/week` → delegate to `/api/v1/vip/menu/weekly/plan`
* [ ] Remove VIP business logic from premium endpoint (delegation only)
* [ ] Parity test: responses equivalent

### PR-D: PRO Canon Exposure

* [ ] Ensure `/api/v1/pro/nutrition/targets` exists and is in schema
* [ ] Ensure `/api/v1/pro/nutrition/daily` exists and is in schema
* [ ] Ensure `/api/v1/pro/meal/weekly` exists and is in schema

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

**Fix:** PR-C (delegation to `/api/v1/vip/menu/weekly/plan`).

**Source:** `docs/contracts/PRODUCT_TIER_MAP.md` section "Deprecated aliases with wrong namespace"

---

## Related Documents

* `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping (contract/specification)
* `docs/contracts/OPENAPI_PATHS_AUDIT.md` — factual inventory of paths
* `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — visibility rules
* `docs/audit/API_ALIGNMENT_CHECKLIST.md` — alignment checklist
