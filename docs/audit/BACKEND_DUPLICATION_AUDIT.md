# Backend Code Duplication Audit

**Date:** 2026-01-15
**Scope:** Duplicate modules, function names, and business logic
**Purpose:** Identify and track code duplication issues

---

## 📊 Summary

**Critical duplications:** 2
**Medium priority duplications:** 3
**Low priority duplications:** Multiple (by design for compatibility)

---

## 🔴 Critical Duplications (P0)

### 1. BMI Calculation Functions — Legacy vs Canonical

**Problem:** Multiple BMI calculation implementations

**Files:**
- `bmi_core.py` (root) — Legacy implementation
- `core/bmi/engine.py` — Canonical implementation (PR-455)
- `core/bmi/risk.py` — Imports from `bmi_core` (legacy dependency)

**Evidence:**
```python
# core/bmi/risk.py:17
from bmi_core import compute_wht_ratio

# core/bmi/engine.py:179
def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
```

**Impact:** High
- Two implementations of WHtR calculation
- `core/bmi/risk.py` depends on legacy `bmi_core.py`
- Risk of drift between implementations

**Recommendation:**
- Remove dependency on `bmi_core.py` from `core/bmi/risk.py`
- Use `core/bmi/engine._compute_wht_ratio` instead
- Deprecate `bmi_core.py` (move to legacy or remove)

**Files:**
- `bmi_core.py` (root)
- `core/bmi/risk.py:17`
- `core/bmi/engine.py:179`

---

### 2. BMI Extras Modules — Duplicate Functions

**Problem:** Three modules with identical function signatures

**Files:**
- `core/bmi_extras.py`
- `core/bmi_extras_pro.py`
- `core/bmi_extras_simple.py`

**Duplicate Functions:**
- `wht_ratio(waist_cm, height_cm)`
- `whr_ratio(waist_cm, hip_cm, sex)`
- `ffmi(...)`
- `interpret_wht_ratio(...)`
- `interpret_whr_ratio(...)`
- `stage_obesity(...)`

**Evidence:**
```python
# core/bmi_extras.py:17
def wht_ratio(waist_cm: float, height_cm: float) -> float:

# core/bmi_extras_pro.py:17
def wht_ratio(waist_cm: float, height_cm: float) -> float:

# core/bmi_extras_simple.py:36
def wht_ratio(waist_cm: float, height_cm: float) -> float:
```

**Impact:** High
- Three implementations of same functions
- Risk of drift and maintenance burden
- Unclear which one is canonical

**Recommendation:**
- Consolidate into single module (`core/bmi/extras.py`)
- Or document purpose of each (if they serve different tiers)
- Remove duplicates

**Files:**
- `core/bmi_extras.py`
- `core/bmi_extras_pro.py`
- `core/bmi_extras_simple.py`

---

## ⚠️ Medium Priority Duplications (P1)

### 3. `estimate_targets_minimal` — Duplicated in Routers

**Problem:** Function duplicated in multiple routers

**Files:**
- `app/routers/premium_week.py:127`
- `app/routers/pro.py:182`

**Code:**
```python
# TODO(#286): Deduplicate estimate_targets_minimal by moving it into app/services/nutrition_targets.py
```

**Impact:** Medium
- Code duplication
- Maintenance burden
- Risk of drift

**Recommendation:**
- Move to `app/services/nutrition_targets.py`
- Update all call sites
- Close TODO #286

---

### 4. Legacy vs Canonical BMI Logic

**Problem:** Legacy BMI logic may still exist alongside canonical

**Files:**
- `bmi_core.py` (root) — Legacy
- `core/bmi/engine.py` — Canonical
- `legacy_app.py` — May have legacy BMI helpers

**Impact:** Medium
- Guard test exists: `tests/test_no_bmi_math_outside_core.py`
- But legacy files still exist

**Recommendation:**
- Verify all BMI logic uses `core/bmi/engine.py`
- Deprecate `bmi_core.py`
- Remove legacy BMI helpers from `legacy_app.py` if any

---

### 5. Catalog Loaders — Similar Structure

**Problem:** Multiple catalog loaders with similar structure

**Files:**
- `core/catalog/loaders/carrefour_es.py`
- `core/catalog/loaders/walmart_us.py`
- `core/catalog/loaders/base.py`

**Impact:** Low
- Similar structure is expected (different sources)
- Not true duplication (different implementations)

**Status:** ✅ Acceptable (different sources, similar interface)

---

## 📝 Low Priority Duplications (P2)

### 6. i18n Error Messages — Pattern Duplication

**Problem:** Same TODO comment in multiple files

**Files:**
- `core/data_sanitizer.py:371`
- `app/routers/users.py:134`
- `app/routers/premium_week.py:97`
- `app/routers/pro.py:152`

**Code:**
```python
# TODO: Localize error messages using t(lang, "translation_key") for i18n support
```

**Impact:** Low
- Not code duplication, just TODO pattern
- Should be addressed systematically

**Recommendation:**
- Create i18n error message system
- Update all error messages at once

---

## 🔍 Verification Commands

### Find Duplicate Function Names

```bash
# Find functions with same name in different files
grep -r "^def " core/ app/ | cut -d: -f2 | sed 's/def //' | sed 's/(.*//' | sort | uniq -d
```

### Find Duplicate Imports

```bash
# Find modules imported in multiple places
grep -r "^from\|^import" core/ app/ | grep -v "^#" | sort | uniq -d
```

### Find BMI Calculation Functions

```bash
# Find all BMI calculation functions
grep -r "def.*bmi\|def.*calculate.*bmi" core/ app/ bmi_core.py
```

---

## 📋 Complete Duplication List

### Critical (P0)

1. **BMI calculation** — `bmi_core.py` vs `core/bmi/engine.py`
2. **BMI extras** — `bmi_extras.py`, `bmi_extras_pro.py`, `bmi_extras_simple.py`

### Medium (P1)

3. **estimate_targets_minimal** — Duplicated in routers
4. **Legacy BMI logic** — May exist in `legacy_app.py`

### Low (P2)

5. **i18n TODOs** — Pattern duplication (not code)

---

## 🎯 Action Items

### P0 (Critical)

1. **Remove `bmi_core.py` dependency from `core/bmi/risk.py`**
   - Use `core/bmi/engine._compute_wht_ratio` instead
   - Deprecate `bmi_core.py`

2. **Consolidate BMI extras modules**
   - Merge into single module or document purpose
   - Remove duplicates

### P1 (High Priority)

3. **Deduplicate `estimate_targets_minimal`**
   - Move to `app/services/nutrition_targets.py`
   - Update call sites

4. **Verify no legacy BMI logic in `legacy_app.py`**
   - Run guard test: `tests/test_no_bmi_math_outside_core.py`
   - Remove any legacy BMI helpers

### P2 (Low Priority)

5. **Systematic i18n error messages**
   - Create error message system
   - Update all error messages

---

## 📚 Related Documents

- `AGENTS.md` — Duplication policy
- `app/AGENTS.md` — No duplicated business logic rule
- `tests/test_no_bmi_math_outside_core.py` — BMI duplication guard

---

**Last updated:** 2026-01-15
