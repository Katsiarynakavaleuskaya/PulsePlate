# PR-494: Audit Report

## ✅ Audit Status: PASSED

**Date:** 2026-01-XX  
**Scope:** interpretation_v1 layer + hard invariant male+pregnant 422 + legacy shim hardening

---

## 1. Schema ↔ Engine Divergence Audit

### 1.1 Gender Normalization Contract ✅

**Status:** PASSED

- ✅ Prefix-based male detection implemented (`_is_male_gender_token()`)
- ✅ Tests cover `"hombre_fullform"` + pregnant → 422
- ✅ Tests cover `"мужик"` + pregnant → 422
- ✅ Unknown gender tokens default to False (safe, no false positives)

**Test Results:**
```bash
pytest -q tests/test_bmi_interpretation_validation.py -k "prefix or hombre or муж"
# Result: 4 passed ✅
```

**Implementation:**
- `_is_male_gender_token()` uses exact match + prefix-based (`startswith`)
- Matches engine's `_normalize_gender()` logic without importing engine
- Unknown tokens treated as non-male (safe default for invariant checks)

### 1.2 Bool Flags Normalization ✅

**Status:** PASSED

- ✅ `_normalize_bool_flag_local()` handles truthy/falsy strings
- ✅ Unknown strings default to False (safe for invariants)
- ✅ Tests cover pregnant="sí" for male → 422

**Test Results:**
```bash
pytest -q tests/test_bmi_interpretation_v1_api.py -k "pregnant"
# Result: 3 passed ✅
```

---

## 2. Legacy Shim Correctness Audit

### 2.1 `bmi_calculate_handler` Returns Dict ✅

**Status:** PASSED

- ✅ `_normalize_canonical_result()` implemented and used consistently
- ✅ All access patterns use `.get()` (no `[]` direct access)
- ✅ `_CATEGORY_I18N_MAP` centralized (module-level constant, 3 usages)

**Verification:**
```bash
grep -n "canonical_result\[" legacy_app.py
# Result: No direct access found ✅

grep -n "_CATEGORY_I18N_MAP" legacy_app.py
# Result: 3 usages (1 definition + 2 usages) ✅
```

### 2.2 Error Serialization Guard ✅

**Status:** PASSED

- ✅ JSON-serializability guard tests implemented
- ✅ Tests cover all legacy endpoints (`/bmi`, `/api/v1/bmi`, `/api/v1/bmi/calculate`)
- ✅ `sanitize_validation_errors()` hardened to strip non-JSON values from `ctx`

**Test Results:**
```bash
pytest -q tests/test_legacy_bmi_validation_json_serialization.py
# Result: 4 passed ✅
```

**Files:**
- `tests/test_legacy_bmi_validation_json_serialization.py` — comprehensive guard tests
- `legacy_app.py` — `sanitize_validation_errors()` hardened

---

## 3. Interpretation V1 Contract Audit

### 3.1 Backward Compatibility ✅

**Status:** PASSED

- ✅ `interpretation: str` field preserved (unchanged)
- ✅ `interpretation_v1` field is optional (additive)
- ✅ `too_young` → `interpretation_v1: null` (only group returning null)
- ✅ `pregnant` → always returns structured `interpretation_v1` (not null)

**Test Results:**
```bash
pytest -q tests/test_bmi_interpretation_v1_api.py
# Result: All tests pass ✅

pytest -q tests/test_bmi_interpretation_rules.py
# Result: All tests pass ✅
```

### 3.2 i18n Keys Only ✅

**Status:** PASSED

- ✅ Guard tests verify all text fields are i18n keys (contain dots or known patterns)
- ✅ Tests check `risk_flags`, `priority_notes`, `disclaimers` format
- ✅ No human-readable text in interpretation fields

**Test Coverage:**
- `test_all_interpretations_have_i18n_keys_only()` in `test_bmi_interpretation_rules.py`
- `test_all_interpretation_v1_fields_are_i18n_keys()` in `test_bmi_interpretation_v1_api.py`

---

## 4. NumericRange Hygiene Audit

### 4.1 `_numeric` Function Validation ✅

**Status:** PASSED

- ✅ Rejects NaN/inf values (`math.isfinite()` check)
- ✅ Rejects `min_v >= max_v` (not just `>`)
- ✅ Comprehensive unit tests cover all edge cases

**Test Results:**
```bash
pytest -q tests/test_bmi_interpretation_rules.py -k "numeric"
# Result: 3 passed ✅
```

**Test Coverage:**
- `test_numeric_rejects_inverted_bounds()` — min_v > max_v
- `test_numeric_rejects_equal_bounds()` — min_v == max_v
- `test_numeric_rejects_nan_inf()` — NaN and inf values

---

## 5. Full CI Gate Rehearsal

### 5.1 Lint Check ✅

**Status:** PASSED

```bash
make lint
# Result: All checks passed ✅
```

### 5.2 Fast Tests ✅

**Status:** PASSED

```bash
make test-fast
# Result: All tests pass ✅
```

### 5.3 Policy Guards ✅

**Status:** PASSED

```bash
pytest -q tests/test_repo_policy_guards.py
# Result: All guards pass ✅
```

---

## 6. Security/Ethics Audit

### 6.1 Male+Pregnant Invariant ✅

**Status:** PASSED

- ✅ Blocked at schema level (422 validation error)
- ✅ Prefix-based gender detection prevents bypass
- ✅ Unknown gender tokens default to non-male (safe)

### 6.2 Athlete+Pregnant Handling ✅

**Status:** PASSED

- ✅ Group remains `pregnant` (age-based priority)
- ✅ Interpretation accounts for athlete status (additional disclaimers)

### 6.3 BMI ≥ 30 Medical Review ✅

**Status:** PASSED

- ✅ `goal_direction="medical_review"` for BMI ≥ 30 (general group)
- ✅ No "do it yourself" recommendations for high BMI

---

## 7. Documentation Audit

### 7.1 Request Normalization Spec ✅

**Status:** PASSED

- ✅ `docs/REQUEST_NORMALIZATION_SPEC.md` created
- ✅ Documents gender normalization contract
- ✅ Documents bool flag normalization contract
- ✅ Lists required guard tests

### 7.2 PR Documentation ✅

**Status:** PASSED

- ✅ `docs/pr/PR_494_DESCRIPTION.md` — complete PR description
- ✅ `docs/pr/PR_494_INTERPRETATION_V1_CONTRACT.md` — API contract
- ✅ `docs/pr/PR_494_SUMMARY.md` — high-level summary

---

## Summary

### ✅ All Audit Checks Passed

1. **Schema ↔ Engine Divergence:** Guarded with prefix-based detection and comprehensive tests
2. **Legacy Shim Correctness:** Normalized result handling, centralized i18n mapping, JSON-serializability guards
3. **Interpretation V1 Contract:** Backward compatible, i18n keys only, proper null handling
4. **NumericRange Hygiene:** Strict validation (NaN/inf, min >= max), comprehensive tests
5. **CI Gate:** All checks pass (lint, test-fast, policy guards)
6. **Security/Ethics:** Hard invariants enforced, medical review for high BMI

### Files Changed

**Production Code:**
- `app/schemas/bmi.py` — normalization helpers + updated validator
- `app/routers/bmi.py` — interpretation_v1 integration
- `core/bmi/interpretation_models.py` — data models
- `core/bmi/interpretation_rules.py` — interpretation logic
- `legacy_app.py` — shim hardening (normalization, error serialization)

**Tests:**
- `tests/test_bmi_interpretation_validation.py` — validation tests (prefix-based gender)
- `tests/test_bmi_interpretation_rules.py` — rules tests (numeric hygiene)
- `tests/test_bmi_interpretation_v1_api.py` — API contract tests
- `tests/test_legacy_bmi_validation_json_serialization.py` — JSON-serializability guards

**Documentation:**
- `docs/REQUEST_NORMALIZATION_SPEC.md` — normalization contract
- `docs/pr/PR_494_*.md` — PR documentation

---

## Ready for Merge ✅

All audit checks passed. PR is ready for review and merge.

