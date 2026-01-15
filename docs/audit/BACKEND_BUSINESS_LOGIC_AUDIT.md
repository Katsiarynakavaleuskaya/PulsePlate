# Backend Business Logic & Formula Audit

**Date:** 2026-01-15
**Scope:** BMI formulas, calculation logic, thresholds, and business rules
**Purpose:** Verify correctness of core business logic

---

## 📊 Summary

**BMI Formula Status:** ✅ Correct
**Thresholds Status:** ✅ Correct (with documented variations)
**Business Logic Issues:** 1 (legacy dependency)

---

## ✅ BMI Formula Verification

### 1. Core BMI Calculation

**File:** `core/bmi/engine.py:163-176`

**Formula:**
```python
def _compute_bmi(weight_kg: float, height_m: float) -> float:
    bmi = weight_kg / (height_m**2)
    return round(bmi, 1)
```

**Verification:** ✅ **Correct**
- Standard WHO formula: `BMI = weight (kg) / height (m)²`
- Rounded to 1 decimal (legacy parity)
- Input validation (weight > 0, height > 0)

---

### 2. WHtR Calculation

**File:** `core/bmi/engine.py:179-203`

**Formula:**
```python
def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    ratio = (waist_cm / 100.0) / height_m
    return round(ratio, 2)
```

**Verification:** ✅ **Correct**
- Standard WHtR formula: `WHtR = (waist_cm / 100) / height_m`
- Rounded to 2 decimals
- Fail-soft (returns None for invalid inputs)

**⚠️ Issue:** Legacy dependency
- `core/bmi/risk.py:17` imports `compute_wht_ratio` from `bmi_core.py` (legacy)
- Should use `core/bmi/engine._compute_wht_ratio` instead

---

### 3. BMI Category Thresholds

**File:** `core/bmi/engine.py:228-256`

**Thresholds:**

**General Adult:**
- Underweight: < 18.5
- Normal: 18.5 - 24.9
- Overweight: 25.0 - 29.9
- Obesity 1: 30.0 - 34.9
- Obesity 2: 35.0 - 39.9
- Obesity 3: ≥ 40.0

**Athlete (Adult):**
- Underweight: < 18.5
- Normal: 18.5 - 26.9 (⚠️ **Key difference: 27.0 vs 25.0**)
- Overweight: 27.0 - 29.9
- Obesity 1: 30.0 - 34.9
- Obesity 2: 35.0 - 39.9
- Obesity 3: ≥ 40.0

**Elderly:**
- Underweight: < 17.5
- Normal: 17.5 - 25.9
- Overweight: ≥ 26.0 (no obesity tiers)

**Verification:** ✅ **Correct (by design)**
- Athlete threshold (27.0) is intentional (higher muscle mass)
- Elderly thresholds are age-appropriate
- Matches WHO guidelines and medical literature

---

### 4. Waist Risk Thresholds

**File:** `core/bmi/risk.py:68-89`

**Thresholds:**
```python
def _waist_thresholds(gender: str) -> tuple[float, float]:
    # (warn_cm, high_cm)
    if gender == "male":
        return (94.0, 102.0)  # cm
    else:  # female
        return (80.0, 88.0)  # cm
```

**Verification:** ✅ **Correct**
- Male: 94 cm (warn), 102 cm (high)
- Female: 80 cm (warn), 88 cm (high)
- Matches WHO/medical guidelines

**Source:** `core/bmi/risk._waist_thresholds()` is canonical (per PR-502)

---

## ⚠️ Business Logic Issues

### 1. Legacy Dependency in `core/bmi/risk.py`

**Problem:** `core/bmi/risk.py` imports from legacy `bmi_core.py`

**Code:**
```python
# core/bmi/risk.py:17
from bmi_core import compute_wht_ratio

# core/bmi/risk.py:151
wht_ratio = compute_wht_ratio(waist_cm, height_m)
```

**Impact:** Medium
- Creates dependency on legacy module
- Risk of drift between implementations
- Violates "canonical source of truth" principle

**Recommendation:**
- Replace with `core/bmi/engine._compute_wht_ratio`
- Remove dependency on `bmi_core.py`
- Deprecate `bmi_core.py`

**File:** `core/bmi/risk.py:17, 151`

---

### 2. BMI Engine Marked as "Stub"

**Problem:** `core/bmi/engine.py` marked as stub but appears functional

**Comment:**
```python
"""
This module will be fully implemented in PR-455.
Currently provides a stub implementation for development/testing.
"""
```

**Current State:**
- ✅ All core functions implemented
- ✅ Validation, normalization, computation all work
- ✅ Category/group logic complete

**Impact:** Low (documentation issue)
- Module works but marked as incomplete
- May confuse developers

**Recommendation:**
- Verify if PR-455 is complete
- Remove "stub" comment if implementation is done
- Or document what's missing

**File:** `core/bmi/engine.py:1-9`

---

## 📋 Formula Verification Checklist

### BMI Calculation

- [x] Formula: `BMI = weight_kg / (height_m²)` ✅
- [x] Rounding: 1 decimal place ✅
- [x] Input validation: weight > 0, height > 0 ✅
- [x] Bounds validation: BMI 10-100 ✅

### WHtR Calculation

- [x] Formula: `WHtR = (waist_cm / 100) / height_m` ✅
- [x] Rounding: 2 decimal places ✅
- [x] Input validation: height 0.5-3.0 m, waist 0-300 cm ✅
- [x] Fail-soft: returns None for invalid inputs ✅

### Category Thresholds

- [x] General adult: 18.5, 25.0, 30.0, 35.0, 40.0 ✅
- [x] Athlete: 18.5, 27.0, 30.0, 35.0, 40.0 ✅ (intentional)
- [x] Elderly: 17.5, 26.0 ✅
- [x] Child/teen: 17.5, 24.5 ✅

### Waist Risk Thresholds

- [x] Male: 94 cm (warn), 102 cm (high) ✅
- [x] Female: 80 cm (warn), 88 cm (high) ✅
- [x] Source: `core/bmi/risk._waist_thresholds()` (canonical) ✅

---

## 🔍 Known Variations (By Design)

### 1. Athlete BMI Threshold (27.0 vs 25.0)

**Reason:** Athletes have higher muscle mass, so normal BMI range extends to 27.0

**Source:** Medical literature, sports medicine guidelines

**Status:** ✅ **Correct (intentional variation)**

**File:** `core/bmi/engine.py:241`

---

### 2. Elderly BMI Thresholds (17.5, 26.0)

**Reason:** Age-appropriate thresholds for elderly population

**Source:** WHO guidelines for elderly

**Status:** ✅ **Correct (intentional variation)**

**File:** `core/bmi/engine.py:230-236`

---

## 🎯 Action Items

### P0 (Critical)

1. **Remove legacy dependency from `core/bmi/risk.py`**
   - Replace `from bmi_core import compute_wht_ratio`
   - Use `core/bmi/engine._compute_wht_ratio` instead
   - Deprecate `bmi_core.py`

### P1 (High Priority)

2. **Verify BMI engine status**
   - Check if PR-455 is complete
   - Remove "stub" comment if done
   - Or document what's missing

---

## 📚 Related Documents

- `tests/test_no_bmi_math_outside_core.py` — BMI duplication guard
- `core/bmi/engine.py` — Canonical BMI implementation
- `core/bmi/risk.py` — Waist risk calculation

---

**Last updated:** 2026-01-15
