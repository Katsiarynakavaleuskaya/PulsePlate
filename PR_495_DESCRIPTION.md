# PR-495: BMI Gender/Pregnancy Invariant Validation (Runtime)

## Summary

Enforces the `male + pregnant` invariant at the schema level with soft normalization (no 422 errors), closes schema↔engine gender token parity gap, and ensures JSON-safe validation error serialization.

## Changes

### 1. BMI Input Normalization
- **Gender tokens**: Normalized to canonical `"male" | "female" | None` via `@field_validator`
- **Pregnancy flag**: Normalized to `bool` via `@field_validator`
- **Tests updated**: Assertions now check canonical normalized values (e.g., `req.gender == "female"` instead of raw localized strings)

### 2. Pregnancy Invariant (Soft Normalization)
- **Schema-level enforcement**: `@model_validator` `_apply_pregnancy_invariant` handles:
  - `gender=None + pregnant=True` → auto-sets `gender="female"` (pregnant implies female)
  - `gender="male" + pregnant=True` → coerces `pregnant=False` (pipeline robustness)
- **Router remains thin**: Removed duplicate soft normalization logic from handler
- **No 422 errors**: Invalid combinations are normalized, not rejected (keeps `/plan` and `/bmi` endpoints stable)

### 3. Schema↔Engine Contract Parity
- **Exact token sets synchronized**: `_MALE_EXACT` and `_FEMALE_EXACT` in schema match engine's exact token recognition
- **Added `"w"` token**: Included in `_FEMALE_EXACT` to match engine contract
- **Guard tests**: Bidirectional parity tests ensure schema and engine agree on all exact tokens

### 4. JSON-Safe Validation Errors
- **Fixed serialization**: `ValidationError` objects sanitized via `jsonable_encoder(e.errors())` before passing to `HTTPException.detail`
- **Applied in**: `app/routers/bmi.py`, `legacy_app.py` (all `bmi_endpoint` variants and `api_who_targets`)

### 5. Typing Consistency
- **Guideline added**: `app/AGENTS.md` documents `model_validate()` + mypy `Any` workaround pattern
- **Pattern applied**: All direct `return Model.model_validate(...)` replaced with typed local assignment
- **Helper extracted**: `_to_response()` in `nutrition_log.py` centralizes the pattern and reduces duplication

### 6. Schema Validation
- **`NumericRangeSchema`**: Added `min ≤ max` validation (consistent with `BMIRangeSpec`)

## Testing

### Guard Tests Added
- `test_gender_none_pregnant_true_auto_sets_female`: Schema-level auto-set behavior
- `test_gender_none_pregnant_true_api_returns_200`: API-level soft normalization
- `test_schema_engine_exact_tokens_parity`: Bidirectional contract parity check
- `test_all_male_exact_tokens_block_pregnant`: Parameterized 422 tests for all `_MALE_EXACT` tokens

### Tests Updated
- `test_bmi_schemas.py`: Updated defaults and normalization assertions
- `test_bmi_calculate_endpoint.py`: Explicit `gender="female"` to avoid soft normalization in test assertions

## Verification Commands

```bash
# Quick status check
git status
git log -1 --oneline

# Guard policies
pytest -q tests/test_repo_policy_guards.py

# Fast tests
make test-fast

# Type checking (with cache cleared if needed)
mypy --no-incremental --cache-dir=/dev/null app core

# Lint/format
make lint
make fmt-check

# Specific guard tests
pytest -q tests/test_bmi_interpretation_validation.py::TestGenderPregnantValidation -k "gender_none and pregnant_true"
pytest -q tests/test_bmi_interpretation_validation.py::TestSchemaEngineContractParity::test_schema_engine_exact_tokens_parity
```

## Files Changed

- `app/schemas/bmi.py`: Gender/pregnancy normalization, invariant enforcement, `NumericRangeSchema` validation
- `core/bmi/engine.py`: Exact token sets synchronized with schema
- `app/routers/bmi.py`: Removed duplicate normalization, JSON-safe errors, typing fix
- `app/routers/nutrition_log.py`: Extracted `_to_response()` helper
- `app/routers/users.py`: Typing fix for `model_validate()`
- `app/services/bmi_visualization.py`: Typing fix for `model_validate()`
- `legacy_app.py`: JSON-safe error serialization
- `app/AGENTS.md`: Typing guideline for `model_validate()` + mypy
- `tests/test_bmi_interpretation_validation.py`: Guard tests for invariant and contract parity
- `tests/test_bmi_schemas.py`: Updated normalization assertions
- `tests/test_bmi_calculate_endpoint.py`: Fixed test assertions

## Related

- Closes schema↔engine contract mismatch identified in PR-494 analysis
- Establishes canonical pattern for Pydantic v2 `model_validate()` + mypy typing
- Maintains backward compatibility (no breaking API changes)
