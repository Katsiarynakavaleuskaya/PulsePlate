# PR-494: Ready for Review Checklist

## ✅ Pre-Review Checks

### Code Quality
- [x] All tests pass (42+ tests)
- [x] Linter clean (no errors, only Sourcery warnings)
- [x] No `type: ignore` without explanation
- [x] All functions have type hints

### Contract Consistency
- [x] **Pregnancy**: Always returns `interpretation_v1` (not null)
  - `pregnant` (without athlete) → `goal_direction: "medical_review"`, `target_range: "prenatal_guidelines"`
  - `pregnant + athlete` → same + additional athlete disclaimers
- [x] **Only `too_young`** returns `interpretation_v1: null`
- [x] Legacy `interpretation: str` field preserved (backward compatibility)
- [x] `male + pregnant` → `422` (hard invariant, tested)

### Documentation
- [x] `PR_494_SUMMARY.md` — complete PR description
- [x] `PR_494_INTERPRETATION_V1_CONTRACT.md` — API contract documented
- [x] All docstrings updated
- [x] No stale comments about "pregnant → null"

### Test Coverage
- [x] Rules tests: 35 tests (all groups, boundary values)
- [x] Validation tests: 13 tests (constructor + API level)
- [x] API integration tests: 9 tests (contract, fail-soft, backward compatibility)
- [x] Fail-soft test: monkeypatch builder failure → 200 OK

---

## 📋 PR Description (Ready to Copy)

```markdown
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

## Risk Assessment

- ✅ Backward compatibility preserved (legacy field untouched)
- ✅ Interpretation does not affect BMI math
- ✅ Fail-soft only for interpretation builder (domain validation remains fail-loud)
- ✅ Gender+pregnant validation at schema level (hard invariant)

## Documentation

- `docs/pr/PR_494_SUMMARY.md` — Complete PR description
- `docs/pr/PR_494_INTERPRETATION_V1_CONTRACT.md` — API contract

## Commits

1. `feat(bmi): add interpretation models and request validation`
2. `feat(bmi): add interpretation rules by group`
3. `feat(bmi): wire interpretation_v1 into bmi calculate response`
```

---

## 🔍 CodeRabbit Response Template

If asked about pregnancy contract change:

```markdown
We tightened the API contract for pregnancy: returning a structured interpretation is more consistent and avoids a "null guidance" UX.

Pregnancy now always yields `interpretation_v1` with `goal_direction=medical_review` and `target_range=prenatal_guidelines`. Only `too_young` remains `interpretation_v1=null`.

This change improves product consistency: all logically interpretable groups now return structured guidance.
```

---

## ✅ Final Verification

Run before opening PR:

```bash
# 1. All tests pass
pytest -q tests/test_bmi_interpretation_*.py

# 2. Linter clean
# (make lint if available)

# 3. Coverage check
make cov-check

# 4. Smoke test API
python -c "
from fastapi.testclient import TestClient
from app import app
client = TestClient(app)
resp = client.post('/api/v1/bmi/calculate', json={
    'weight_kg': 65.0, 'height_cm': 165.0, 'age': 28,
    'gender': 'female', 'pregnant': True, 'athlete': False, 'lang': 'en'
})
assert resp.status_code == 200
data = resp.json()
assert data['interpretation_v1'] is not None
assert data['interpretation_v1']['goal_direction'] == 'medical_review'
print('✅ Pregnancy interpretation works')
"
```

---

## 🎯 Ready to Open PR

All checks passed. PR-494 is ready for review.
