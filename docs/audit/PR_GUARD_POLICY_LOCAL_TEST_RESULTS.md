# Guard Tests Local Run Results

**Date:** 2026-01-15
**Command:** `pytest tests/test_bmi_canonical_guard.py -v`

---

## ✅ Expected Failures (3)

### 1. `test_no_legacy_bmi_imports_in_core_bmi` — FAILED ✅

**Violation Found:**
```
core/bmi/risk.py:17 — from bmi_core import compute_wht_ratio
```

**Status:** ✅ **Expected** — Documents legacy dependency violation

**Fix:** Use `core.bmi.engine._compute_wht_ratio` instead

---

### 2. `test_single_canonical_extras_module` — FAILED ✅

**Violation Found:**
```
Multiple bmi_extras modules found without clear purpose:
- core/bmi_extras.py
- core/bmi_extras_simple.py
- core/bmi_extras_pro.py
```

**Status:** ✅ **Expected** — Documents duplicate modules violation

**Fix:** Consolidate into single canonical module

---

### 3. `test_engine_metadata_accuracy` — FAILED ✅

**Violation Found:**
```
Engine marked as 'stub' but appears functionally complete.
```

**Status:** ✅ **Expected** — Documents metadata confusion

**Fix:** Update docstring to reflect canonical status

---

## ✅ Expected Passes (2)

### 4. `test_bmi_result_structure_consistency` — PASSED ✅

**Status:** ✅ **Pass** — Result structure is consistent (good sign)

---

### 5. `test_no_bmi_calculation_outside_engine` — FAILED ⚠️

**Violations Found:**
```
app/routers/bmi_pro.py:16 — def calc_bmi(...)
core/nutrition_bayesian_analyzer.py:377 — bmi = weight / (height_m**2)
```

**Status:** ⚠️ **Expected violations** — Both should use engine

**Notes:**
- `bmi_pro.py` has local `calc_bmi` helper — should use `core/bmi/engine`
- `nutrition_bayesian_analyzer.py` has direct BMI calculation — should use `core/bmi/engine` for consistency

**Fix:** Replace both with `core.bmi.engine._compute_bmi` or `core.bmi.engine.calculate_bmi_result`

---

## 📊 Summary

**Total Tests:** 5
**Expected Failures:** 4 (3 architectural violations + 1-2 calculation violations)
**Actual Failures:** 4
**Status:** ✅ **Guards work correctly** — they document violations as expected

**Breakdown:**
- Architectural violations: 3 (legacy import, duplicates, metadata)
- Calculation violations: 1-2 (`bmi_pro.py`, possibly `nutrition_bayesian_analyzer.py`)

---

## 🎯 Next Steps

1. ✅ Guards are working correctly
2. ✅ Failures are expected (document violations)
3. ✅ Ready to open Draft PR
4. ⏭️ Remediation PR will make guards pass

---

**Last updated:** 2026-01-15
