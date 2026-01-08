# PR-494: BMI Targets / Interpretation Layer

## 🎯 Summary

Adds a canonical BMI interpretation layer (`interpretation_v1`) that provides structured recommendations, targets, and disclaimers based on BMI results. The interpretation is group-aware (general, athlete, elderly, child, teen, pregnant) and uses i18n keys only (no translated strings).

**Key feature:** Free BMI becomes more valuable with actionable, context-aware guidance without entering paid logic.

**Important:** `interpretation_v1` is always present for all groups except `too_young`. Pregnancy always returns structured interpretation (goal=`medical_review`, target=`prenatal_guidelines`).

---

## 🧱 Scope

### ✅ What This PR Does

1. **Interpretation Models** (`core/bmi/interpretation_models.py`)
   - `BMIInterpretation` dataclass with `goal_direction`, `target_range`, `risk_flags`, `priority_notes`, `disclaimers`
   - All text fields are i18n keys (semantic `I18nKey` type alias)
   - Numeric ranges are mathematically correct (no UI tricks like `-0.1`)

2. **Interpretation Rules** (`core/bmi/interpretation_rules.py`)
   - `build_interpretation_v1()` with rules for all groups
   - **Pregnant**: Always returns interpretation (with or without athlete)
     - `goal_direction: "medical_review"`, `target_range: "prenatal_guidelines"`
     - With athlete: additional `athlete_body_composition` risk flag and combined disclaimers
   - **Child/Teen**: Qualitative targets with growth monitoring
   - **Elderly**: Stability-first, allow `increase` on low BMI
   - **Athlete**: Maintain in 18.5-30 range, `medical_review` at extremes
   - **General**: `increase`/`maintain`/`reduce`/`medical_review` per BMI (≥30 → `medical_review`)
   - **Too_young**: Only group that returns `None` (no interpretation)

3. **Request Validation** (`app/schemas/bmi.py`)
   - Hard invariant: `male + pregnant` → `422` (fail-loud at schema level)
   - Local gender normalization (no import from `core.bmi.engine`)

4. **API Integration** (`app/routers/bmi.py`, `app/schemas/bmi.py`)
   - New field: `interpretation_v1: BMIInterpretationV1Schema | None` in `BMICalculateResponse`
   - Fail-soft: if builder fails, `interpretation_v1` remains `None` (endpoint still returns 200)
   - Uses request `athlete` flag (not from group) for `pregnant+athlete` logic

### 🚫 Non-goals

- ❌ No changes to BMI calculation or category logic
- ❌ No changes to legacy `interpretation: str` field (backward compatibility preserved)
- ❌ No nutrition/calorie recommendations
- ❌ No paid features
- ❌ No UI/frontend changes

---

## 🧪 Tests

### Coverage

- **34 tests** for interpretation rules (all groups, boundary values)
- **13 tests** for gender+pregnant validation (constructor + API level)
- **8 tests** for API integration (contract, fail-soft, backward compatibility)
- **Guard tests**: i18n keys only, immutability, no BMI mutation

### Test Files

- `tests/test_bmi_interpretation_validation.py` (13 tests)
- `tests/test_bmi_interpretation_rules.py` (34 tests)
- `tests/test_bmi_interpretation_v1_api.py` (8 tests)

---

## ⚠️ Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking backward compatibility | Legacy `interpretation: str` field preserved, `interpretation_v1` is optional |
| Interpretation affects BMI math | Interpretation is separate layer, does not modify BMI/category |
| Localization drift | All fields are i18n keys only, no translated strings in backend |
| Fail-soft masking errors | Fail-soft only for interpretation builder, domain validation remains fail-loud |
| Gender+pregnant validation bypass | Validation at schema level (before engine), hard invariant |

---

## 🔐 Security & Ethics

- **Gender+pregnant validation** prevents incorrect medical interpretations
- **All disclaimers** are informational only (not medical diagnoses)
- **Enhanced disclaimers** for child/teen/elderly/pregnant groups
- **No personal data** in interpretation (only BMI value and group)

---

## 📈 Marketing & GTM

- Free BMI becomes **explainable and actionable** (not just a calculator)
- **Context-aware guidance** (age, athlete status, pregnancy) increases trust
- **Structured interpretation** differentiates from competitors
- Foundation for future premium features (without entering paid logic in this PR)

---

## 📝 Commit History

1. `feat(bmi): add interpretation models and request validation`
   - Models: `BMIInterpretation`, `GoalDirection`, `TargetRange`
   - Validation: `male + pregnant` → `422` (hard invariant)

2. `feat(bmi): add interpretation rules by group`
   - Rules for all groups (general, athlete, elderly, child, teen, pregnant+athlete)
   - All outputs are i18n keys only

3. `feat(bmi): wire interpretation_v1 into bmi calculate response`
   - API integration with fail-soft
   - Comprehensive API tests

---

## ✅ Definition of Done

- [x] Models and validation implemented
- [x] Rules for all groups implemented
- [x] API integration with fail-soft
- [x] Comprehensive test coverage (55+ tests)
- [x] Backward compatibility preserved
- [x] No breaking changes
- [x] All tests pass
- [x] Linter clean

---

## 🔜 Future Work (Out of Scope)

- i18n translations for interpretation keys (separate PR)
- iOS integration (Sprint C.2)
- Frontend visualization of interpretation
- Extended interpretation for premium tiers

