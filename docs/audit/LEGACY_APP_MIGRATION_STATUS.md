# Legacy App Migration Status — Progress Report

**Date:** 2026-01-28
**Based on:** Analysis of `legacy_app.py` (6300+ lines) vs current state (5383 lines)
**Purpose:** Track progress on critical issues identified in legacy_app.py analysis

---

## 📊 Executive Summary

**Overall Progress:** ~60% complete (migration from monolithic legacy to modular architecture)

**Status:**
- ✅ **Architecture migration:** Active (many routers connected, thin proxy pattern established)
- ✅ **BMI duplication:** Fixed (uses `core.bmi.engine._compute_bmi`)
- ❌ **Rate limiting:** Not implemented (code commented out, critical security gap)
- ❌ **Tier guards:** Partial (uses `_get_api_key_dynamic`, not tier decorators)
- ✅ **Thin proxy cleanup:** In progress (PR-616 merged, PR-TP2 pending)

---

## 🔍 Critical Issues Status

### 1. 🔴 Монолитная архитектура (6300+ строк в одном файле)

**Original Analysis:**
- 60+ endpoints in one file
- Business logic mixed with routing
- Hard to maintain, test, and reuse

**Current State:**
- ✅ **Many routers connected:** 15+ modular routers registered
  - `bmi_router`, `bmi_pro_router`, `foods_router`, `recipes_router`, `users_router`
  - `pro_router`, `vip_router`, `vip_shoplist_router`, `business_router`, `catalog_router`
  - `export_router`, `plan_router`, `shoplist_router`, `shopping_list_pro_router`, `shoplist_day_router`
- ✅ **Thin proxy pattern:** PR-616 moved helpers out of `legacy_app.py`
- ⚠️ **File still large:** 5383 lines (down from 6300+, but still monolithic)
- ⚠️ **Legacy endpoints remain:** Many endpoints still in `legacy_app.py` for backward compatibility

**Progress:** ~70% (routers connected, but legacy endpoints not fully migrated)

**Remaining Work:**
- PR-TP2: Move DB fallback helpers (P0, next)
- Deprecate legacy endpoints after client migration (P2)
- Eventually delete `legacy_app.py` (long-term)

---

### 2. ✅ Дублирование логики BMI (Fixed)

**Original Analysis:**
- BMI calculation duplicated in 3 places (lines 2097, 2316, 3808)
- Hardcoded formulas instead of using `core.bmi.engine`

**Current State:**
- ✅ **Uses canonical engine:** `from core.bmi.engine import _compute_bmi`
- ✅ **No duplication:** All BMI calculations go through `core.bmi.engine`
- ✅ **Compatibility layer:** `core.bmi.compat_plan` for legacy endpoints

**Progress:** ✅ **100% Fixed**

**Evidence:**
```python
# legacy_app.py:1392-1394
from core.bmi.engine import _compute_bmi
bmi = _compute_bmi(weight_kg=self.weight_kg, height_m=self.height_m)
```

---

### 3. ❌ Rate Limiting для дорогих операций (NOT FIXED)

**Original Analysis:**
- `/api/v1/insight` (LLM) — no rate limiting → $72k/month potential abuse
- PDF exports — no rate limiting → DoS risk
- WebSocket — no rate limiting → message spam

**Current State:**
- ❌ **Rate limiting code commented out:** Lines 1251-1256
  ```python
  if _is_rate_limiting_available():
      pass
      # limiter = Limiter(key_func=get_remote_address)  # type: ignore
      # app.state.limiter = limiter
  ```
- ❌ **No rate limiting on `/api/v1/insight`:** Lines 2256-2301
- ❌ **No rate limiting on `/insight`:** Lines 2305-2348
- ❌ **No rate limiting on PDF exports:** Not checked (likely missing)

**Progress:** ❌ **0% Fixed** (Critical security gap remains)

**Risk:**
- Cost attack: Unlimited LLM API calls → $72k/month potential
- DoS: PDF generation spam → server crash
- Message spam: WebSocket abuse → resource exhaustion

**Required Actions (P0):**
1. Uncomment and configure rate limiting
2. Add `@limiter.limit("10/hour")` to `/api/v1/insight`
3. Add `@limiter.limit("5/hour")` to PDF exports
4. Add rate limiting to WebSocket (if exists)

**References:**
- `docs/audit/AUDIT_GAPS_ANALYSIS.md` — P0 CRITICAL gap
- `core/insight/analysis_insights.md` — $72k/month potential abuse

---

### 4. 🟡 Tier Guards (Partial Fix)

**Original Analysis:**
- Tier checking duplicated in 20+ endpoints
- Inconsistent application (some endpoints skip tier checks)
- `/api/v1/insight` accessible to FREE users (should be VIP)

**Current State:**
- ✅ **Modular routers use decorators:** `require_vip_tier()`, `require_pro_tier()` in `app/routers/vip.py`, `app/routers/pro.py`
- ⚠️ **Legacy endpoints use `_get_api_key_dynamic`:** Not tier-aware (only checks API key existence)
- ⚠️ **`/api/v1/insight` uses `_get_api_key_dynamic`:** Line 2258 — checks API key, but not tier
- ❌ **`/insight` has no auth:** Line 2305 — no dependencies (accessible to anyone)

**Progress:** ~50% (modular routers fixed, legacy endpoints not)

**Required Actions:**
1. Move `/api/v1/insight` to VIP tier (use `require_vip_tier()`)
2. Add tier check to `/insight` or remove it (deprecated)
3. Audit all legacy endpoints for tier consistency

**References:**
- `docs/audit/AUDIT_GAPS_ANALYSIS.md` — LLM should be VIP tier
- `app/middleware/api_tiers.py` — tier decorators available

---

### 5. ✅ WebSocket Authentication (RESOLVED — No WebSocket Found)

**Original Analysis:**
- `/ws` endpoint accepts connections without token verification
- No rate limiting on WebSocket messages

**Current State:**
- ✅ **WebSocket NOT FOUND in codebase:** Comprehensive search found no WebSocket endpoints
  - No `@app.websocket` or `@router.websocket` decorators
  - No `/ws` path registered in FastAPI app
  - No WebSocket imports in any router or main entry point
  - OpenAPI schema contains no WebSocket paths
- ✅ **False positives identified:**
  - `fix_failing_tests.py` — test fixes only (not actual WebSocket code)
  - `frontend/package-lock.json` — frontend dependency (not backend server)
  - Documentation references — RFC/analysis mentions, not implementation

**Progress:** ✅ **RESOLVED** — WebSocket endpoint does not exist (security gap does not exist)

**Conclusion:**
- WebSocket never existed OR was removed before current snapshot
- No security vulnerability (no endpoint to secure)
- If WebSocket is added in future → require auth + rate limiting

**References:**
- `docs/audit/WEBSOCKET_ANALYSIS.md` — detailed investigation results

---

### 6. 🟡 Хардкод констант (Partial Fix)

**Original Analysis:**
- BMR formula constants hardcoded (10, 6.25, 5)
- Activity multipliers hardcoded
- Export formats hardcoded

**Current State:**
- ✅ **Some constants extracted:** `core.targets`, `core.bmi.engine`
- ⚠️ **BMR still uses `nutrition_core`:** Lines 97, 120 — `from nutrition_core import calculate_all_bmr`
- ⚠️ **Activity factors:** Uses `core.utils.get_activity_factor` (centralized)
- ⚠️ **Export formats:** Still hardcoded in export functions (not enum)

**Progress:** ~60% (some constants extracted, BMR/export formats remain)

**Remaining Work:**
- Extract BMR constants to `core.bmr` module
- Create `ExportFormat` enum
- Replace hardcoded values with constants

---

### 7. ✅ Thin Proxy Cleanup (In Progress)

**Original Analysis:**
- `legacy_app.py` should be thin proxy only
- Business logic should be in `core/` or `app/routers/`

**Current State:**
- ✅ **PR-616 merged:** Steps 1/2/3/4/6/7 complete
  - Scheduler wrappers moved to `app/scheduler_helpers.py`
  - Utility helpers moved to `app/utils/helpers.py`
  - Feature flags moved to `app/utils/feature_flags.py`
  - Nutrition wrappers moved to `app/utils/nutrition_wrappers.py`
  - Fingerprint moved to `core/fingerprint_security.py`
  - Dead BMI helpers removed
- ⏳ **PR-TP2 pending:** Step 5 (DB fallback helpers) deferred
- ✅ **Guard tests pass:** `test_no_legacy_bmi_helpers_request_path.py`

**Progress:** ~85% (most helpers moved, DB fallback pending)

**Remaining Work:**
- PR-TP2: Move DB fallback helpers to canonical module
- Complete thin proxy transformation

**References:**
- `docs/roadmap/BACKLOG_LEDGER.md` — PR-616 merged, PR-TP2 next
- `docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md`

---

## 📋 Migration Status by Domain

| Domain | Legacy Endpoints | Modular Routers | Status |
|--------|-----------------|-----------------|--------|
| **BMI** | `/bmi`, `/api/v1/bmi` | `app.routers.bmi`, `app.routers.bmi_pro` | 🟡 Partial (legacy still active) |
| **Foods** | `/api/v1/foods/*` | `app.routers.foods` | ✅ Migrated |
| **Recipes** | `/api/v1/recipes/*` | `app.routers.recipes` | ✅ Migrated |
| **PRO nutrition** | `/premium/plate`, `/premium/targets` | `app.routers.pro` | 🟡 Partial (legacy aliases) |
| **VIP weekly plan** | `/premium/plan/week` | `app.routers.vip` | 🟡 Partial (namespace confusion) |
| **VIP shoplist** | `/premium/exports/*` | `app.routers.vip_shoplist` | 🟡 Partial (legacy aliases) |
| **LLM insight** | `/api/v1/insight`, `/insight` | None (still in legacy) | ❌ Not migrated (security gap) |
| **Users** | `/api/v1/users/*` | `app.routers.users` | ✅ Migrated |
| **Export** | Various | `app.routers.plan_export`, `app.routers.shoplist_export` | ✅ Migrated |

**Legend:**
- ✅ Migrated: Fully moved to modular routers
- 🟡 Partial: Routers exist, but legacy endpoints remain for backward compatibility
- ❌ Not migrated: Still in `legacy_app.py` with issues

---

## 🎯 Critical Actions Required (Prioritized)

### P0 — Critical Security (Week 1)

1. **Rate Limiting (CRITICAL)**
   - Uncomment rate limiting code (lines 1251-1256)
   - Add `@limiter.limit("10/hour")` to `/api/v1/insight`
   - Add `@limiter.limit("5/hour")` to PDF exports
   - Add rate limiting to WebSocket (if exists)
   - **Risk:** $72k/month cost attack, DoS vulnerability
   - **Time:** 1-2 days

2. **Move LLM to VIP Tier (CRITICAL)**
   - Change `/api/v1/insight` to use `require_vip_tier()` instead of `_get_api_key_dynamic`
   - Remove `/insight` endpoint (deprecated, no auth)
   - **Risk:** FREE users accessing expensive LLM API
   - **Time:** 1 day

3. ~~**WebSocket Authentication (if exists)**~~ ✅ **RESOLVED**
   - ✅ Searched codebase — no WebSocket endpoints found
   - ✅ Security gap does not exist (no endpoint to secure)
   - **Status:** Resolved (see `docs/audit/WEBSOCKET_ANALYSIS.md`)

### P1 — API Cleanup (Week 2-3)

4. **PR-B: Hide `/premium/*` from OpenAPI**
   - Set `include_in_schema=False` on legacy endpoints
   - **Time:** 2-3 days

5. **PR-C: Fix `/premium/plan/week` delegation**
   - Remove VIP logic from premium endpoint
   - Delegate to `/api/v1/vip/menu/weekly/plan`
   - **Time:** 2-3 days

6. **PR-D: Expose PRO canonical endpoints**
   - Ensure `/api/v1/pro/nutrition/targets` in schema
   - **Time:** 1-2 days

### P2 — Code Consolidation (Week 4-6)

7. **Extract Constants**
   - BMR constants to `core.bmr`
   - Export formats to enum
   - **Time:** 1 week

8. **PR-TP2: DB Fallback Cleanup**
   - Move DB fallback helpers to canonical module
   - **Time:** 1 week

---

## 📈 Progress Metrics

**Overall Completion:** ~60%

**By Category:**
- Architecture migration: 70% (routers connected, legacy endpoints remain)
- Code deduplication: 85% (BMI fixed, constants partial)
- Security hardening: 30% (rate limiting missing, tier guards partial)
- Thin proxy cleanup: 85% (helpers moved, DB fallback pending)

**Critical Gaps:**
- ❌ Rate limiting: 0% (code commented out)
- ❌ LLM tier guard: 0% (still accessible to FREE)
- ✅ WebSocket auth: Resolved (no WebSocket endpoints found)

---

## 🔗 References

- Original analysis: User-provided `legacy_app.py` analysis (6300+ lines)
- Current state: `legacy_app.py` (5383 lines, 2026-01-28)
- Thin proxy cleanup: `docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md`
- Security gaps: `docs/audit/AUDIT_GAPS_ANALYSIS.md`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md`

---

**Last updated:** 2026-01-28 (WebSocket analysis complete — no endpoints found)
**Next review:** After P0 security fixes (rate limiting, tier guards)
