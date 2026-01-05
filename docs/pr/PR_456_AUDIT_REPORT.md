# PR-456 Audit Report: BMI Route Ownership & Legacy Migration

**Date:** 2025-01-XX
**Status:** Pre-PR-457 Review
**Scope:** BMI calculation logic migration to `core/bmi/*`

---

## A. Инварианты / Policy

### ✅ A1. Нет BMI математики вне `core/bmi/*`

**Status:** ⚠️ **PARTIAL VIOLATION**

**Findings:**
1. ✅ `/bmi` endpoint (legacy_app.py:2047) — **OK**: Uses shim → `bmi_calculate_handler` → `core/bmi/engine.calculate_bmi_result`
2. ✅ `/api/v1/bmi` endpoint (legacy_app.py:2207) — **OK**: Uses shim → `bmi_calculate_handler` → `core/bmi/engine.calculate_bmi_result`
3. ✅ `/api/v1/bmi/calculate` endpoint (app/routers/bmi.py:207) — **OK**: Uses `bmi_calculate_handler` → `core/bmi/engine.calculate_bmi_result`
4. ❌ `/plan` endpoint (legacy_app.py:2156) — **VIOLATION**: Still uses legacy helpers:
   - `calc_bmi(req.weight_kg, req.height_m)` (line 2160)
   - `normalize_flags(req.gender, req.pregnant, req.athlete)` (line 2159)
   - `bmi_category(bmi, req.lang, req.age, ...)` (line 2164) — imported from `bmi_core.py`

**Legacy helpers still defined:**
- `calc_bmi()` (legacy_app.py:1567) — **Used only in `/plan`**
- `normalize_flags()` (legacy_app.py:1571) — **Used only in `/plan`**
- `waist_risk()` (legacy_app.py:1604) — **Not used in request-path** (dead code)
- `bmi_category()` (bmi_core.py:71) — **Used only in `/plan`**

**Note:** `app/routers/bmi_pro.py:16` has local `calc_bmi()` — this is acceptable (Pro endpoints, not legacy migration scope).

### ✅ A2. Legacy endpoints не вычисляют BMI/group/category/threshold

**Status:** ⚠️ **PARTIAL VIOLATION**

**Findings:**
- ✅ `/bmi` — **OK**: Delegates to canonical handler
- ✅ `/api/v1/bmi` — **OK**: Delegates to canonical handler
- ❌ `/plan` — **VIOLATION**: Directly computes BMI, category, flags

**Evidence:**
```python
# legacy_app.py:2156-2164
async def plan_endpoint(req: BMIRequest) -> Dict[str, Any]:
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)  # ❌ Legacy helper
    bmi = calc_bmi(req.weight_kg, req.height_m)  # ❌ Legacy helper
    category = (
        None
        if flags["is_pregnant"]
        else bmi_category(bmi, req.lang, req.age, "athlete" if flags["is_athlete"] else "general")  # ❌ Legacy helper
    )
```

### ✅ A3. Любая i18n строка — через `core.i18n` и RU/EN/ES присутствуют

**Status:** ✅ **PASS**

**Findings:**
- ✅ All shims use `from core.i18n import normalize_lang, t`
- ✅ Category localization uses `t(lang_norm, "bmi_underweight|normal|overweight|obese_1|obese_2|obese_3")`
- ✅ Notes use `t(lang_norm, "bmi_not_valid_during_pregnancy")` and `t(lang_norm, "advice_athlete_bmi")`
- ✅ All required i18n keys exist in `core/i18n.py` (RU/EN/ES)

**Verified keys:**
- `bmi_underweight`, `bmi_normal`, `bmi_overweight`, `bmi_obese_1`, `bmi_obese_2`, `bmi_obese_3`
- `bmi_not_valid_during_pregnancy`
- `advice_athlete_bmi`
- `bmi_engine_unavailable`

---

## B. Inventory Report (обязательный артефакт)

### Legacy Helpers Inventory

| File | Function | Request-Path Usage? | Plan |
|------|----------|---------------------|------|
| `legacy_app.py:1567` | `calc_bmi(weight_kg, height_m)` | ✅ Yes (`/plan`) | **Replace** in `/plan` → use canonical handler |
| `legacy_app.py:1571` | `normalize_flags(gender, pregnant, athlete)` | ✅ Yes (`/plan`) | **Replace** in `/plan` → use canonical handler normalization |
| `legacy_app.py:1604` | `waist_risk(waist_cm, gender_male, lang)` | ❌ No | **Delete** (dead code) |
| `bmi_core.py:71` | `bmi_category(bmi, lang, age, group)` | ✅ Yes (`/plan`) | **Replace** in `/plan` → use canonical handler |

**Summary:**
- **3 functions** used in request-path (`/plan` only)
- **1 function** dead code (`waist_risk`)
- **Action required:** Migrate `/plan` endpoint to use canonical handler (PR-457 scope)

---

## C. Risk Review

### C1. Hidden Usage (import side-effects, indirect calls)

**Status:** ✅ **LOW RISK**

**Findings:**
- ✅ No dynamic imports (`importlib.util.spec_from_file_location`, `exec_module`)
- ✅ No `sys.path.insert` in request-path code
- ✅ No `sys.modules` mutation
- ✅ Local imports in shims are safe (`from app.routers.bmi import bmi_calculate_handler`)

**Potential risks:**
- ⚠️ `bmi_core.py` is imported in `legacy_app.py` (indirect via `bmi_category`). This is isolated to `/plan` only.

### C2. "plan_endpoint" (или иные неочевидные места)

**Status:** ⚠️ **IDENTIFIED**

**Findings:**
- ❌ `/plan` endpoint (legacy_app.py:2156) **still uses legacy BMI math**
- ✅ No other endpoints found using legacy helpers

**Test coverage:**
- ✅ Tests exist: `test_plan_endpoint*` in multiple test files
- ⚠️ Tests do NOT verify that `/plan` uses canonical engine (they only check response structure)

**Action:** Add guard test to verify `/plan` delegates to canonical handler (PR-457).

### C3. Backward Compatibility: какие endpoints/DTO потенциально затронуты

**Status:** ✅ **SAFE**

**Endpoints:**
- ✅ `/bmi` — **Backward compatible**: Shim adapts response format (category slug → localized display, note priority)
- ✅ `/api/v1/bmi` — **Backward compatible**: Same shim logic
- ✅ `/api/v1/bmi/calculate` — **Backward compatible**: New canonical endpoint, no breaking changes
- ⚠️ `/plan` — **Not migrated yet** (PR-457 scope)

**DTOs:**
- ✅ `BMIRequest` (legacy) — **Compatible**: Shim converts to `BMICalculateRequest`
- ✅ `BMIRequestV1` (legacy) — **Compatible**: Shim converts to `BMICalculateRequest`
- ✅ `BMICalculateRequest` (canonical) — **New**, no breaking changes

**Response formats:**
- ✅ Legacy endpoints return same structure: `{bmi, category, note, athlete, group}`
- ✅ Category is localized (slug → display name) for backward compatibility
- ✅ Note priority preserved (pregnancy > athlete > waist risk > interpretation)

---

## D. Test Strategy

### D1. Regression Tests: ключевые сценарии

**Status:** ✅ **COVERED**

**Test files:**
- ✅ `tests/test_legacy_bmi_shims.py` — Proof tests for shim delegation
- ✅ `tests/test_bmi_calculate_endpoint.py` — Canonical endpoint tests
- ✅ `tests/test_bmi_endpoint_diff_coverage.py` — Language normalization tests
- ✅ `tests/test_app_comprehensive_97_final.py` — Integration tests (child/teen/pregnant/athlete/general; RU/EN/ES)

**Coverage:**
- ✅ Child/teen: `age < 19` → `group="child"` or `"teen"`
- ✅ Pregnant: `pregnant=True` → `group="pregnant"`, `category=None`
- ✅ Athlete: `athlete=True` → `group="athlete"`, note includes athlete advice
- ✅ General: `age >= 19, age < 60, not pregnant, not athlete` → `group="general"`
- ✅ Elderly: `age >= 60` → `group="elderly"`
- ✅ Languages: RU/EN/ES (normalization and localization)

**Missing:**
- ⚠️ `/plan` endpoint tests do NOT verify canonical engine usage

### D2. "No legacy helper in request-path" тест

**Status:** ❌ **MISSING**

**Required test:**
```python
def test_no_legacy_bmi_helpers_in_request_path():
    """
    RU: Проверка, что ни один request-path endpoint не использует legacy BMI helpers.
    EN: Verify no request-path endpoint uses legacy BMI helpers.
    """
    # Scan legacy_app.py for endpoint definitions
    # Verify they don't call calc_bmi, normalize_flags, bmi_category, waist_risk
    # Exception: /plan (to be migrated in PR-457)
```

**Action:** Add this guard test in PR-457 (after `/plan` migration).

### D3. Guard Test остаётся зелёным

**Status:** ✅ **PASS** (expected)

**Guard tests:**
- ✅ `tests/test_import_hygiene_guard.py` — Import hygiene (no dynamic imports, no sys.path hacks)
- ✅ `tests/test_env_guards.py` — Environment gating (TESTING=true before imports)

**Note:** Guard tests should remain green after PR-456 (no import hygiene violations introduced).

---

## E. Diff-Coverage Plan

### E1. Какие строки/ветки должны быть закрыты

**Status:** ✅ **COVERED** (Commit 3 + diff coverage tests)

**Shim paths covered:**
1. ✅ `/bmi` shim:
   - ✅ Request conversion (height_m → height_cm)
   - ✅ ValidationError → 422
   - ✅ Category localization (slug → display)
   - ✅ Unknown category fallback (slug as-is)
   - ✅ Note priority (pregnancy > athlete > waist risk > interpretation)
   - ✅ Athlete note with waist risk concatenation
   - ✅ Visualization preservation

2. ✅ `/api/v1/bmi` shim:
   - ✅ Request conversion (BMIRequestV1 → BMICalculateRequest)
   - ✅ ValidationError → 422
   - ✅ Category localization
   - ✅ Unknown category fallback
   - ✅ Note priority
   - ✅ Athlete note with waist risk concatenation

3. ✅ Handler unit tests:
   - ✅ Engine unavailable → 501 (handler level)
   - ✅ Language normalization (RU/es-ES/EN → ru/en/es)

**Test files:**
- ✅ `tests/test_legacy_bmi_shims.py` — Edge cases (unknown category, ValidationError, athlete+waist notes)
- ✅ `tests/test_bmi_calculate_endpoint.py` — Handler unit test (501 branch)
- ✅ `tests/test_bmi_endpoint_diff_coverage.py` — Language normalization (HTTP level)

### E2. Какие тесты их закроют (минимум 1 тест на каждую важную ветку)

**Status:** ✅ **COMPLETE**

| Branch/Path | Test | File |
|-------------|------|------|
| `/bmi` shim delegation | `test_bmi_endpoint_uses_canonical_handler_via_shim` | `test_legacy_bmi_shims.py` |
| `/api/v1/bmi` shim delegation | `test_bmi_endpoint_v1_uses_canonical_handler_via_shim` | `test_legacy_bmi_shims.py` |
| Unknown category fallback | `test_bmi_endpoint_unknown_category_falls_back_to_slug` | `test_legacy_bmi_shims.py` |
| ValidationError → 422 | `test_bmi_endpoint_v1_validation_error_maps_to_422` | `test_legacy_bmi_shims.py` |
| Athlete note + waist risk | `test_bmi_endpoint_v1_athlete_note_appends_waist_risk_notes_and_unknown_category_fallback` | `test_legacy_bmi_shims.py` |
| Engine unavailable → 501 (handler) | `test_engine_unavailable_returns_501_from_handler` | `test_bmi_calculate_endpoint.py` |
| Language normalization (HTTP) | `test_http_calculate_normalizes_lang_for_localized_501` | `test_bmi_calculate_endpoint.py` |
| Language normalization (indirect) | `test_router_uses_core_i18n_normalize_lang_indirect` | `test_bmi_endpoint_diff_coverage.py` |

---

## F. Critical Findings & Action Items

### 🔴 Critical: `/plan` Endpoint Still Uses Legacy Helpers

**Issue:** `plan_endpoint` (legacy_app.py:2156) violates invariant A1 and A2.

**Impact:**
- Duplicate BMI calculation logic
- Potential inconsistencies between `/plan` and canonical BMI endpoints
- Maintenance burden (two code paths)

**Action (PR-457):**
1. Migrate `/plan` to use `bmi_calculate_handler` (similar to `/bmi` shim)
2. Remove legacy helpers: `calc_bmi`, `normalize_flags`, `bmi_category` (from `legacy_app.py`)
3. Consider removing `bmi_core.py` if no longer needed
4. Add guard test: `test_no_legacy_bmi_helpers_in_request_path`

### 🟡 Medium: Dead Code (`waist_risk`)

**Issue:** `waist_risk()` (legacy_app.py:1604) is not used in any request-path.

**Action (PR-457):**
- Delete `waist_risk()` function (dead code cleanup)

### 🟢 Low: Guard Test for Legacy Helpers

**Issue:** No automated guard test to prevent reintroduction of legacy BMI helpers in request-path.

**Action (PR-457):**
- Add `test_no_legacy_bmi_helpers_in_request_path` guard test

---

## G. PR-456 Summary

### ✅ Completed (Commits 1-3)

1. ✅ Route ownership audit and documentation
2. ✅ Removed legacy shim for `/api/v1/bmi/calculate` (now canonical only)
3. ✅ Implemented shims for `/bmi` and `/api/v1/bmi` (delegate to canonical handler)
4. ✅ Language normalization via `core.i18n.normalize_lang`
5. ✅ Category localization (slug → display name)
6. ✅ Note priority logic (pregnancy > athlete > waist risk > interpretation)
7. ✅ Comprehensive test coverage (shim delegation, edge cases, language normalization)
8. ✅ Diff coverage for all shim branches

### ⚠️ Deferred to PR-457

1. ❌ `/plan` endpoint migration
2. ❌ Legacy helper removal (`calc_bmi`, `normalize_flags`, `bmi_category`, `waist_risk`)
3. ❌ Guard test for "no legacy helpers in request-path"

---

## H. Recommendations for PR-457

1. **Priority 1:** Migrate `/plan` endpoint to use canonical handler
2. **Priority 2:** Remove legacy helpers (`calc_bmi`, `normalize_flags`, `bmi_category`, `waist_risk`)
3. **Priority 3:** Add guard test `test_no_legacy_bmi_helpers_in_request_path`
4. **Priority 4:** Consider removing `bmi_core.py` if no longer needed (verify no other imports)

---

**Audit completed:** 2025-01-XX
**Next step:** PR-457 planning and implementation
