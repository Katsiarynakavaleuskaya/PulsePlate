# PR-494: Review Checklist for Reviewers

## Quick Summary

This PR adds a canonical BMI interpretation layer (`interpretation_v1`) with structured recommendations and implements a hard invariant: `male + pregnant → 422`.

**Type:** Feature (API enhancement)
**Risk:** Medium (touches request validation and legacy shim endpoints)
**Breaking:** None (backward compatible)

---

## Critical Areas to Review

### 1. Schema ↔ Engine Divergence (HIGH PRIORITY)

**What to check:**
- `app/schemas/bmi.py` — `validate_gender_pregnant()` uses prefix-based matching (`_MALE_PREFIXES`, `_FEMALE_PREFIXES`)
- Verify that prefix logic matches engine behavior (without importing engine)
- Check that unknown gender tokens default to non-male (safe)

**Test coverage:**
- `tests/test_bmi_interpretation_validation.py` — prefix-based tests (`hombre_fullform`, `мужик`)

**Why this matters:** If schema and engine diverge, `male + pregnant` could pass schema but be treated as male by engine, violating the hard invariant.

---

### 2. Legacy Shim Safety (HIGH PRIORITY)

**What to check:**
- `legacy_app.py` — `_normalize_canonical_result()` safely converts handler result to dict
- `sanitize_validation_errors()` strips non-JSON values from `ctx` (prevents 500/invalid JSON)
- Category i18n mapping is centralized (`_CATEGORY_I18N_MAP`)

**Test coverage:**
- `tests/test_legacy_bmi_validation_json_serialization.py` — JSON-serializability guards

**Why this matters:** Legacy endpoints could fail if `canonical_result` is a Pydantic model (`.get()` errors), and validation errors could contain non-JSON objects.

---

### 3. Interpretation V1 Contract (MEDIUM PRIORITY)

**What to check:**
- `core/bmi/interpretation_rules.py` — `build_interpretation_v1()` logic for all groups
- `pregnant` always returns structured interpretation (not `None`)
- `too_young` is the only group returning `None`
- Numeric ranges are strict (no UI tricks like `-0.1`)

**Test coverage:**
- `tests/test_bmi_interpretation_rules.py` — all groups, boundary values, `_numeric` validation
- `tests/test_bmi_interpretation_v1_api.py` — API contract, fail-soft behavior

**Why this matters:** Contract must be consistent and predictable for frontend clients.

---

### 4. Request Validation Invariant (MEDIUM PRIORITY)

**What to check:**
- `app/schemas/bmi.py` — `validate_gender_pregnant()` raises `ValueError` for `male + pregnant`
- All tests updated to expect `422` for `male + pregnant` combinations
- Prefix-based gender detection works correctly

**Test coverage:**
- `tests/test_bmi_interpretation_validation.py` — validation tests
- `tests/test_admin_endpoints_97.py` — `test_comprehensive_language_support` respects invariant

**Why this matters:** Hard invariant must be enforced consistently across all endpoints.

---

## Quick Verification Commands

### Schema ↔ Engine Divergence
```bash
pytest -q tests/test_bmi_interpretation_validation.py -k "prefix or hombre or муж"
# Expected: 4 passed
```

### Legacy JSON-Serializability
```bash
pytest -q tests/test_legacy_bmi_validation_json_serialization.py
# Expected: 4 passed
```

### Interpretation Contract
```bash
pytest -q tests/test_bmi_interpretation_rules.py tests/test_bmi_interpretation_v1_api.py
# Expected: All pass
```

### Full Test Suite
```bash
make test-fast
# Expected: All pass
```

---

## Files Changed Summary

**Core changes:**
- `app/schemas/bmi.py` — `BMICalculateRequest` validation, `BMIInterpretationV1Schema`
- `app/routers/bmi.py` — wire `interpretation_v1` into response
- `core/bmi/interpretation_models.py` — `BMIInterpretation` dataclass
- `core/bmi/interpretation_rules.py` — `build_interpretation_v1()` logic
- `legacy_app.py` — shim hardening (result normalization, JSON safety)

**Tests:**
- `tests/test_bmi_interpretation_*.py` — new interpretation tests
- `tests/test_legacy_bmi_validation_json_serialization.py` — JSON-serializability guards
- `tests/test_admin_endpoints_97.py` — updated for invariant
- Various regression tests updated for `male + pregnant → 422`

**Documentation:**
- `docs/REQUEST_NORMALIZATION_SPEC.md` — normalization contract
- `docs/pr/PR_494_AUDIT_REPORT.md` — complete audit report

---

## Common Questions

**Q: Why is `pregnant` always returning `interpretation_v1` now?**
A: Consistency. Previously it returned `None` without athlete, but that was inconsistent with other groups. Now it always returns structured interpretation with `goal_direction="medical_review"` and `target_range="prenatal_guidelines"`.

**Q: Why prefix-based gender detection?**
A: Engine uses prefix matching for some languages (e.g., `"муж*"` for Russian, `"hombre*"` for Spanish). Schema must match this behavior to prevent divergence.

**Q: Why fail-soft for interpretation builder?**
A: Interpretation is additive (doesn't affect BMI math). If builder fails, endpoint still returns `200` with `interpretation_v1: null`. Domain validation remains fail-loud.

**Q: Why JSON-serializability guards?**
A: Pydantic `ValidationError.errors()` can contain non-JSON objects in `ctx` (e.g., `ValueError`). Legacy endpoints must return valid JSON, so we sanitize `ctx` before serialization.

---

## Approval Criteria

- [ ] Schema ↔ engine divergence guarded (prefix tests pass)
- [ ] Legacy shim safety verified (JSON-serializability tests pass)
- [ ] Interpretation contract consistent (all groups tested)
- [ ] Request validation invariant enforced (`male + pregnant → 422`)
- [ ] All tests pass (`make test-fast`)
- [ ] No breaking changes (backward compatible)
- [ ] Documentation complete (`REQUEST_NORMALIZATION_SPEC.md`, audit report)

---

## Risk Assessment

**Low risk:**
- Interpretation is additive (doesn't affect BMI math)
- Backward compatible (legacy field untouched)
- Fail-soft only for interpretation builder

**Medium risk:**
- Request validation changes (`male + pregnant → 422`) — mitigated by comprehensive tests
- Legacy shim changes — mitigated by normalization and JSON-serializability guards

**Mitigation:**
- Comprehensive test coverage (60+ tests)
- Guard tests for critical paths (divergence, JSON-serializability)
- Audit report with verification commands

