# PR-494: BMI Targets / Interpretation Layer

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
