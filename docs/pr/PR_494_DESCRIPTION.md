# PR-494: BMI Targets / Interpretation Layer

> **Reviewer checklist:** `docs/pr/PR_494_REVIEW_CHECKLIST.md`

## Summary

Adds a canonical BMI interpretation layer (`interpretation_v1`) that provides structured recommendations, targets, and disclaimers based on BMI results. The interpretation is group-aware (general, athlete, elderly, child, teen, pregnant) and uses i18n keys only (no translated strings).

**Key feature:** Free BMI becomes more valuable with actionable, context-aware guidance without entering paid logic.

**Important:** `interpretation_v1` is always present for all groups except `too_young`. Pregnancy always returns structured interpretation (goal=`medical_review`, target=`prenatal_guidelines`).

## Scope

### What This PR Does

1. **Interpretation Models** — `BMIInterpretation` dataclass with i18n keys only
2. **Interpretation Rules** — `build_interpretation_v1()` with rules for all groups
   - **Pregnant**: Always returns interpretation (with or without athlete)
   - **Child/Teen**: Qualitative targets with growth monitoring
   - **Elderly**: Stability-first, allow `increase` on low BMI
   - **Athlete**: Maintain in 18.5-30 range, `medical_review` at extremes
   - **General**: `increase`/`maintain`/`reduce`/`medical_review` per BMI (≥30 → `medical_review`)
   - **Too_young**: Only group that returns `None` (no interpretation)
3. **Request Validation** — `male + pregnant` → `422` (hard invariant)
4. **API Integration** — New field `interpretation_v1` in response (fail-soft)

### Non-goals

- ❌ No changes to BMI calculation or category logic
- ❌ No changes to legacy `interpretation: str` field
- ❌ No nutrition/calorie recommendations
- ❌ No paid features

## Tests

- **42+ tests** covering all groups, boundary values, validation, API contract
- **Fail-soft test** ensures builder failures don't break endpoint
- **Guard tests** for i18n keys only, immutability
- **Regression tests** updated for new `male + pregnant → 422` invariant

## Risk Assessment

- ✅ Backward compatibility preserved (legacy field untouched)
- ✅ Interpretation does not affect BMI math
- ✅ Fail-soft only for interpretation builder (domain validation remains fail-loud)
- ✅ Gender+pregnant validation at schema level (hard invariant)
- ✅ Existing tests updated to reflect new validation behavior

## Documentation

- `docs/pr/PR_494_SUMMARY.md` — Complete PR description
- `docs/pr/PR_494_INTERPRETATION_V1_CONTRACT.md` — API contract
- `docs/pr/PR_494_READY_FOR_REVIEW.md` — Review checklist

## Commits

1. `feat(bmi): add interpretation models and request validation`
2. `feat(bmi): add interpretation rules by group`
3. `feat(bmi): wire interpretation_v1 into bmi calculate response`
4. `fix(legacy): handle ValidationError serialization in legacy endpoints`

## Breaking Changes

**None** — This PR is backward compatible. The new `interpretation_v1` field is additive, and legacy `interpretation: str` field is preserved.

**Note:** Some existing tests were updated to reflect the new `male + pregnant → 422` validation invariant (this is expected behavior, not a breaking change).

---

## Audit / Verification (mandatory)

**Why this audit is required:** This PR touches **request invariants** and **legacy shim behavior**, which are high-risk areas for hidden 422/500 regressions. We explicitly guarded against schema ↔ engine divergence and added JSON-serializability protection.

### Schema ↔ Engine Divergence Guarded

**Problem:** Schema validation used exact string matching, while engine used prefix-based matching (e.g., `"муж*"`, `"hombre*"`). This could allow `male + pregnant` to pass schema but be treated as male by engine.

**Solution:**
- ✅ Added prefix-based male detection in schema (`_is_male_gender_token`, `_MALE_PREFIXES`) without importing engine
- ✅ Added tests ensuring male+pregnant returns 422 for prefix variants (`hombre_fullform`, `мужик`)
- ✅ Unknown gender tokens default to non-male (safe, no false positives)

**Verification:**
```bash
pytest -q tests/test_bmi_interpretation_validation.py -k "prefix or hombre or муж"
# Result: 4 passed ✅
```

### Legacy Shim Safety

**Problem:** Legacy endpoints (`/bmi`, `/api/v1/bmi`) could fail if `canonical_result` was a Pydantic model (`.get()` errors), and validation errors could contain non-JSON-serializable objects in `ctx`.

**Solution:**
- ✅ Normalized canonical handler result to dict (`_normalize_canonical_result()`) and removed mixed access patterns
- ✅ Centralized category i18n mapping (`_CATEGORY_I18N_MAP` module-level constant) to avoid drift
- ✅ Hardened `sanitize_validation_errors()` to strip non-JSON values from `ctx` (converts to string or removes)
- ✅ Added JSON-serializability guard test for legacy endpoint validation errors

**Verification:**
```bash
pytest -q tests/test_legacy_bmi_validation_json_serialization.py
# Result: 4 passed ✅
```

### Interpretation V1 Contract

**Verification:**
- ✅ `interpretation_v1` added without breaking legacy `interpretation: str`
- ✅ `too_young` → `interpretation_v1: null`; `pregnant` always returns structured `interpretation_v1`
- ✅ Numeric ranges are strict (no UI tricks); `_numeric` rejects invalid bounds/NaN/inf

**Commands:**
```bash
pytest -q tests/test_bmi_interpretation_rules.py -k "numeric"
# Result: 3 passed ✅
```

### Full CI Gate

**Commands:**
```bash
make lint && make test-fast && pytest -q tests/test_repo_policy_guards.py
# All checks pass ✅
```

**Test Fixes:**
- Updated `test_comprehensive_language_support` to respect `male + pregnant → 422` invariant (tests male with `pregnant="no"` only, female with both values)
- Optimized test to use `monkeypatch` instead of `os.environ` try/finally
- Fixed edge case: `age=80, pregnant=yes` → `age=30, pregnant=yes` (realistic)

### Documentation

- ✅ `docs/REQUEST_NORMALIZATION_SPEC.md` — normalization contract (gender, bool flags)
- ✅ `docs/pr/PR_494_AUDIT_REPORT.md` — complete audit report

See `docs/pr/PR_494_AUDIT_REPORT.md` for detailed audit results.
