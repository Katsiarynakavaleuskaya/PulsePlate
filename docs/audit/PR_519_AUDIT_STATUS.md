# PR-519 — Backend PRO/Premium Alias Audit Status

**Date:** 2026-01-12
**Status:** 🔄 In Progress (Implementation Phase)
**Goal:** Map canonical PRO endpoints and deprecated premium aliases for thin proxy implementation

---

## 📋 Context from Previous PRs

### PR-510 (legacy_app audit) — PR #515
**Status:** ✅ Docs-only PR (merged)
- **Realized:** Documentation and analysis only
- **Not realized:** Code extraction (deferred to PR-511+)
- **Date completed:** 2026-01-11

### PR-517 (VIP Guard Consistency) — PR #517
**Status:** ✅ Merged
- **Realized:**
  - VIP endpoints covered by guard suite use `require_vip_tier()` consistently (legacy deprecated `/api/v1/vip/weekly-plan` is a known exception)
  - OpenAPI artifacts updated (Security scheme)
  - Tests updated (vip_headers fixture)
  - AGENTS.md updated (Security() pattern rule)
- **Date completed:** 2026-01-11

### PR-518 (VIP Guard Matrix + Test Hygiene) — PR #518
**Status:** ✅ Merged
- **Realized:**
  - VIP guard matrix created (`tests/test_vip_tier_guard_matrix.py`) — 51 tests
  - Env cleanup fixed (`VIP_MODULE_ENABLED` cleaned in teardown)
  - sys.modules mutations replaced with `monkeypatch.setattr()` (no importlib.reload)
  - AGENTS.md updated (dependency override, sys.modules, env cleanup rules)
  - Separate "no API key" test added (`test_vip_no_api_key_403.py`)
- **Date completed:** 2026-01-12

### FRONTEND_BACKEND_ALIGNMENT_AUDIT
**Status:** ❌ Not started
- **Realized:** None (all tasks marked `[ ]`)
- **Note:** This is a separate frontend-backend alignment PR (not included in recent PRs)

---

## 🎯 PR-519 Goals

### Canonical PRO Endpoints (must be stable and documented)
- `/api/v1/pro/nutrition/targets`
- `/api/v1/pro/nutrition/plate`
- `/api/v1/pro/nutrition/daily`
- `/api/v1/pro/meal/weekly`

### Deprecated Premium Aliases (thin proxy only, do not remove)
- `/api/v1/premium/targets` → delegates to `/api/v1/pro/nutrition/targets`
- `/api/v1/premium/plate` → delegates to `/api/v1/pro/nutrition/plate` (PlateRequest → PlateResponse)
- `/api/v1/premium/plan/week` → deprecated legacy tail (sanctioned bridge: `week-flexible`)

### OpenAPI
- PRO paths — canonical
- premium paths — **deprecated: true**, but remain in schema

---

## 🔍 Audit Checklist (In Progress)

### A. Inventory (Facts Only)

#### 1. Where are PRO endpoints defined?
- [x] Check `app/routers/pro.py` (runtime canonical: `/meal/weekly`, `/nutrition/daily`)
- [x] Check registration: `app/routers/pro_registration.py` / `legacy_app.py` include_router
- [x] Confirm OpenAPI schema-only mode skips `app.routers.pro` (PRO weekly/daily absent from `frontend/src/api/openapi.json`)

#### 2. Where are premium endpoints?
- [x] Check `legacy_app.py` for:
  - `/api/v1/premium/targets`
  - `/api/v1/premium/plate` (POST, feature flag `FEATURE_PREMIUM_NUTRITION`)
  - `/api/v1/premium/plan/week` (VIP module flag)
- [x] Identify which are already "shim/delegate" vs. which calculate internally
- [x] Note additional deprecated premium weekly endpoint: `POST /api/v1/premium/plan/week-flexible` in `app/routers/premium_week.py`

#### 3. Method and request format for canonical daily
- [x] Canonical PRO daily is `GET /api/v1/pro/nutrition/daily` (query params)

#### 4. Response shape for canonical endpoints
- [x] `daily` (PRO): `DailyNutritionResponse` (segments/total_progress/daily_goals)
- [x] `weekly` (PRO): `WeekPlanResponse` (daily_menus/weekly_coverage/shopping_list/total_cost/adherence_score)
- [x] `targets` (PRO): canonical endpoint exists (`POST /api/v1/pro/nutrition/targets`)
- [x] `plate` (PRO): canonical endpoint exists (`POST /api/v1/pro/nutrition/plate`)

### B. Risks/Invariants
- [x] Anti-duplication: aliases must NOT recalculate nutrition/plans themselves (targets+plate are thin proxies)
- [ ] OpenAPI determinism: do not break order and schema-only mode
- [ ] Feature flags: canonical PRO always available; aliases may be gated but better: canonical gated by PRO tier, aliases only deprecated wrapper
- [ ] Frontend compatibility: minimal diff, no "improvements"
  - [x] Plate resolved: canonical `pro/nutrition/plate` introduced (no proxy to `pro/nutrition/daily`)
  - [!] Weekly mismatch remains: `/api/v1/premium/plan/week` is VIP-gated and returns `WeeklyMenuResponse` (includes `week_summary`)
  - [x] Guards divergence documented: premium aliases are legacy-guarded by design (not auth-equivalent to PRO tier)

### C. Audit Artifacts (Expected Output)
- [x] Table: canonical path → handler/function → request model → response model
- [x] Table: premium alias path → current behavior → should do (delegate)
- [x] Decision on `plate`: canonical plate = `pro/nutrition/plate` (POST)
- [x] Parity tests implemented for targets+plate (no parity for `plan/week`)

---

## ✅ Current snapshot (facts)

- Runtime canonical PRO endpoints exist:
  - `app/routers/pro.py`: `/api/v1/pro/nutrition/daily`, `/api/v1/pro/meal/weekly` (excluded from schema-only OpenAPI)
  - `app/routers/pro_nutrition_contracts.py`: `/api/v1/pro/nutrition/targets`, `/api/v1/pro/nutrition/plate` (included in schema-only OpenAPI via `app/main.py` bootstrap)
- OpenAPI currently exposes `/api/v1/premium/*` endpoints (deprecated) and now also includes canonical PRO targets+plate.
- Guard divergence is intentional in PR-519:
  - PRO canonical: `require_pro_tier`
  - Premium aliases: `_get_api_key_dynamic`

---

## 📝 Next Steps

1. Stage+commit OpenAPI artifacts (`frontend/src/api/openapi.json`, `frontend/src/api/schema.ts`)
2. Add minimal AGENTS.md bullets for PR-519 invariants (no contract-mismatch proxies)
3. Run `make verify` and paste output for gates

---

**Last updated:** 2026-01-12
