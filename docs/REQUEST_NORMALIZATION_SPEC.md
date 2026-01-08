# Request Normalization Spec (schema ↔ engine)

This document defines **minimal compatibility rules** for request-field normalization between:
- **schema validation layer** (`app/schemas/*`)
- **engine/domain layer** (`core/*`)

## Goals

- Prevent schema/engine divergence for **hard invariants**.
- Keep schemas free of engine imports (no cycles).
- Provide a single reference for test guards.

---

## GenderNormalizationSpec

### Male detection (for invariants)

A gender token is treated as **male** if, after trim+lower:
- exact match in: `{"male","m","man","м"}`
- OR startswith any prefix in: `("муж", "hombre")`

A gender token is treated as **female** if:
- exact match in: `{"female","f","woman","ж"}`
- OR startswith any prefix in: `("жен", "mujer")`

### Invariant

If male-detected AND pregnant=True → schema must raise validation error (422).

### Implementation

- **Schema layer**: `app/schemas/bmi.py` → `_is_male_gender_token()` / `_is_female_gender_token()`
- **Engine layer**: `core/bmi/engine.py` → `_normalize_gender()`

Both must use the same prefix-based logic to prevent divergence.

---

## BoolFlagNormalizationSpec (pregnant/athlete)

### Accepted truthy tokens (trim+lower)

`yes, y, true, 1, да, д, истина, si, sí`

### Accepted falsy tokens

`no, n, false, 0, нет, н, ложь`

### Unknown strings

Unknown strings must be treated as **False** in schema invariants (safe default).

### Implementation

- **Schema layer**: `app/schemas/bmi.py` → `_normalize_bool_flag_local()`
- **Engine layer**: `core/bmi/engine.py` → `_normalize_bool_flag()`

Schema normalization is intentionally simpler (exact match only) to enforce invariants safely.

---

## Guard Tests (required)

### Gender prefix divergence tests

Must test that schema validation blocks prefix-based male tokens with pregnancy:

- `test_gender_prefix_ru_male_blocks_pregnancy` — "мужик" + pregnant → ValueError
- `test_gender_prefix_es_male_blocks_pregnancy` — "hombre_fullform" + pregnant → ValueError
- `test_gender_prefix_ru_male_api_returns_422` — API contract test
- `test_gender_prefix_es_male_api_returns_422` — API contract test

**Location**: `tests/test_bmi_interpretation_validation.py`

### Test payload hygiene

**Important:** Any test not explicitly validating pregnancy logic must set `pregnant` to a falsy token (e.g., `"no"` / `False`) to avoid invalid states introduced by hard invariant validation.

Example: Language support tests should use `gender="male"` with `pregnant="no"` only, or test both genders separately (male with `pregnant="no"`, female with both `pregnant="yes"` and `"no"`).

### Legacy endpoint JSON-serializability guard

Must ensure legacy endpoints return JSON-serializable error envelopes for validation failures:

- `test_legacy_bmi_male_pregnant_422_is_json_serializable` — `/api/v1/bmi`
- `test_legacy_bmi_prefix_male_pregnant_422_is_json_serialization` — prefix-based gender
- `test_legacy_bmi_v0_male_pregnant_422_is_json_serializable` — `/bmi` (v0)
- `test_canonical_bmi_male_pregnant_422_is_json_serializable` — `/api/v1/bmi/calculate`

**Location**: `tests/test_legacy_bmi_validation_json_serialization.py`

---

## Field-by-Field Audit

### A) Gender

- ✅ **Status**: Synchronized (exact + prefix matching in both layers)
- ✅ **Guard tests**: Present (prefix-based divergence tests)

### B) Pregnant / Athlete (`str | bool`)

- ✅ **Status**: Schema uses safe normalization (exact match, unknown → False)
- ✅ **Guard tests**: Present (JSON-serializability guards)

### C) Lang

- ✅ **Status**: Schema uses `Language` enum (ru/en/es), engine normalizes to same enum
- ⚠️ **Risk**: Low (enum prevents divergence)

### D) Numeric fields (weight_kg, height_cm, waist_cm)

- ✅ **Status**: Schema enforces `gt=0` for all numeric fields
- ⚠️ **Note**: Legacy endpoints (`BMIRequestV1`) should also enforce `gt=0` (audit recommended)

---

## Future Considerations

### Schema ↔ Engine Alignment Strategy

1. **Hard invariants** (e.g., male+pregnant) → schema must enforce with aligned normalization
2. **Soft normalization** (e.g., athlete detection) → engine handles richer logic, schema uses safe defaults
3. **No import cycles** → schema helpers are local, engine remains independent

### When to Update This Spec

- New gender tokens added to engine → update schema helpers
- New bool flag tokens added to engine → update schema helpers
- New normalization logic in engine → audit schema alignment

---

## Related Documentation

- `app/schemas/bmi.py` — Schema implementation with local normalization helpers
- `core/bmi/engine.py` — Engine normalization implementation
- `tests/test_bmi_interpretation_validation.py` — Validation tests
- `tests/test_legacy_bmi_validation_json_serialization.py` — JSON-serializability guards

