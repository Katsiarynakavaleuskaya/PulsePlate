# Backend Audit Summary

**Date:** 2026-01-15
**Scope:** Complete backend audit (tech debt, tests, modules, duplication, business logic, APIs)
**Purpose:** Executive summary of all backend audits

---

## 📊 Overall Status

**Backend Health:** 75% (Good foundation, some tech debt)

**Breakdown:**
- **Business Logic:** 95% (formulas correct, minor legacy dependency)
- **External APIs:** 90% (well implemented, catalog stubs by design)
- **Code Quality:** 70% (some duplication, legacy dependencies)
- **Test Coverage:** 97% (2 xfailed tests, target met)
- **Technical Debt:** 60% (28 TODOs, some stub modules)

---

## 🔴 Critical Issues (P0)

### 1. Legacy BMI Dependency

**Problem:** `core/bmi/risk.py` imports from legacy `bmi_core.py`

**Impact:** High (violates canonical source principle)

**Fix:** Replace with `core/bmi/engine._compute_wht_ratio`

**File:** `core/bmi/risk.py:17`

---

### 2. BMI Extras Duplication

**Problem:** Three modules with identical functions (`bmi_extras.py`, `bmi_extras_pro.py`, `bmi_extras_simple.py`)

**Impact:** High (maintenance burden, risk of drift)

**Fix:** Consolidate into single module

**Files:** `core/bmi_extras*.py`

---

## ⚠️ High-priority Issues (P1)

### 3. xfailed Tests (2)

1. `test_no_calculate_all_bmr` — Module reload issue
2. `test_bmi_visualization_endpoint_with_api_key` — Test isolation issue

**Impact:** Medium (tests pass individually, fail in suite)

**Fix:** Use dependency override instead of `sys.modules` manipulation

---

### 4. Log Cleanup Not Implemented

**Problem:** `core/log_retention.py:cleanup_expired_logs()` returns 0 (stub)

**Impact:** Medium (log files may accumulate)

**Fix:** Implement file deletion logic

---

### 5. Database Lookup for API Tiers

**Problem:** Placeholder TODOs in `app/middleware/api_tiers.py`

**Impact:** Medium (needed for production)

**Fix:** Implement database lookup when `SUBSCRIPTION_DB_ENABLED=true`

---

### 6. Function Duplication

**Problem:** `estimate_targets_minimal` duplicated in routers

**Impact:** Medium (code quality)

**Fix:** Move to `app/services/nutrition_targets.py`

---

## 📝 Medium-priority Issues (P2)

### 7. i18n Error Messages (Multiple files)

**Problem:** Error messages not localized (13 TODOs)

**Impact:** Low (UX enhancement)

**Fix:** Create i18n error message system

---

### 8. BMI Engine Status

**Problem:** Marked as "stub" but appears functional

**Impact:** Low (documentation issue)

**Fix:** Verify PR-455 status, update comment

---

### 9. Telemetry Integration (2 TODOs)

**Problem:** Placeholder metrics in business analyzer

**Impact:** Low (observability)

**Fix:** Integrate telemetry service

---

## ✅ What's Working Well

### 1. BMI Formulas

- ✅ Core BMI calculation correct
- ✅ WHtR calculation correct
- ✅ Category thresholds correct (with documented variations)
- ✅ Waist risk thresholds correct

### 2. External APIs

- ✅ USDA client fully implemented
- ✅ OpenFoodFacts client fully implemented
- ✅ Unified database interface works
- ✅ LLM providers (Ollama, Grok, Pico) fully implemented
- ✅ Error handling and retry logic in place

### 3. Test Infrastructure

- ✅ 97% coverage requirement met
- ✅ Guard tests enforce architecture rules
- ✅ Test isolation (mostly) working

---

## 📋 Complete Audit Documents

1. **`BACKEND_XFAILED_TESTS_AUDIT.md`** — xfailed and skipped tests
2. **`BACKEND_TODO_FIXME_AUDIT.md`** — All TODOs and incomplete features
3. **`BACKEND_STUB_MODULES_AUDIT.md`** — Stub and incomplete modules
4. **`BACKEND_DUPLICATION_AUDIT.md`** — Code duplication issues
5. **`BACKEND_BUSINESS_LOGIC_AUDIT.md`** — BMI formulas and business logic
6. **`BACKEND_EXTERNAL_APIS_AUDIT.md`** — External API integrations

---

## 🎯 Priority Action Plan

### P0 (Critical — Fix First)

1. Remove legacy BMI dependency (`core/bmi/risk.py`)
2. Consolidate BMI extras modules

### P1 (High-priority)

3. Fix xfailed tests (dependency override)
4. Implement log cleanup
5. Implement database lookup for API tiers
6. Deduplicate `estimate_targets_minimal`

### P2 (Medium-priority)

7. i18n error messages (systematic update)
8. Verify BMI engine status
9. Integrate telemetry

---

## 📊 Metrics

| Category | Count | Status |
|----------|-------|--------|
| **xfailed tests** | 2 | ⚠️ Need fix |
| **TODOs** | 28 | ⚠️ Tracked |
| **Stub modules** | 5 | ⚠️ Documented |
| **Duplications** | 2 critical | 🔴 Need fix |
| **Business logic errors** | 0 | ✅ Correct |
| **External API issues** | 0 | ✅ Working |

---

**Last updated:** 2026-01-15
