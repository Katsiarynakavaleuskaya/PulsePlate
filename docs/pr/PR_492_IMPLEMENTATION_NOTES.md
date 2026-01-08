# PR-492 Implementation Notes: Code Analysis & Adaptations

## Summary

Анализ структуры проекта и адаптация шаблонов под реальный код завершены.
Оба файла созданы и адаптированы под структуру проекта.

---

## 🔍 Code Analysis Results

### 1. Request Fields (BMICalculateRequest)

**Real structure from `app/schemas/bmi.py`:**

```python
class BMICalculateRequest(BaseModel):
    weight_kg: float      # ✅ (not "weight")
    height_cm: float      # ✅ (not "height")
    age: int              # ✅ (not "age_years")
    gender: str           # ✅ ("male" or "female")
    pregnant: str | bool  # ✅ ("yes"/"no" or True/False)
    athlete: str | bool   # ✅ ("yes"/"no" or True/False)
    waist_cm: float | None  # Optional
    lang: Language        # ✅ ("en", "ru", "es")
```

**Adaptation in tests:**
- ✅ Used `_valid_payload()` helper (matches existing test pattern)
- ✅ Fields match exactly: `weight_kg`, `height_cm`, `age`, `gender`, `pregnant`, `athlete`, `lang`

### 2. Age Band Mapping

**Real logic from `core/bmi/engine.py` → `_age_band()`:**

```python
def _age_band(age: int) -> AgeBand:
    if age < 12:
        return "too_young"
    if age == 12:
        return "child"      # ✅ age 12 is "child", not "teen"
    if 13 <= age <= 19:
        return "teen"       # ✅ age 13-19 is "teen"
    if 19 < age < 60:
        return "adult"      # ✅ age 20-59 is "adult"
    return "elderly"        # ✅ age >= 60 is "elderly"
```

**Adaptation in tests:**
- ✅ `test_visualization_contract_child_is_null`: uses `age=12` (correctly maps to "child")
- ✅ `test_visualization_contract_teen_is_null`: uses `age=16` (correctly maps to "teen")
- ✅ `test_visualization_ranges_are_group_aware_elderly_vs_adult`: uses `age=75` (correctly maps to "elderly")

### 3. Test Client Pattern

**Real pattern from `tests/conftest.py`:**

```python
@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)
```

**Adaptation in tests:**
- ✅ Used `client: TestClient` fixture (matches existing pattern)
- ✅ Used `_post_bmi()` helper (consistent with existing tests)
- ✅ Used `_valid_payload()` helper (reused from `test_bmi_calculate_endpoint.py`)

### 4. BMIScaleV1Spec Structure

**Real structure from `app/schemas/bmi.py`:**

```python
class BMIScaleV1Spec(BaseModel):
    kind: Literal["bmi_scale_v1"] = "bmi_scale_v1"
    bmi: float
    min: float = 0.0
    max: float = 60.0
    ranges: list[BMIRangeSpec]
    marker: BMIMarkerSpec
```

**Adaptation in documentation:**
- ✅ Documented all fields correctly
- ✅ Explained `from` alias (serialized as `"from"`, not `"from_"`)
- ✅ Explained exactly 4 ranges requirement

### 5. Group-Aware Ranges

**Real thresholds from `core/bmi/engine.py` → `_BMI_BREAKPOINTS`:**

```python
# Adult (general)
("adult", "general"): [
    (18.5, "underweight"),
    (25.0, "normal"),
    (30.0, "overweight"),
    (35.0, "obesity_1"),
    (40.0, "obesity_2"),
    (float("inf"), "obesity_3"),
]

# Athlete
("adult", "athlete"): [
    (18.5, "underweight"),
    (27.0, "normal"),  # ✅ Different: 27.0 vs 25.0
    (30.0, "overweight"),
    ...
]

# Elderly
("elderly", "general"): [
    (17.5, "underweight"),  # ✅ Different: 17.5 vs 18.5
    (26.0, "normal"),        # ✅ Different: 26.0 vs 25.0
    (30.0, "overweight"),
    ...
]
```

**Adaptation in tests:**
- ✅ `test_visualization_ranges_are_group_aware_athlete_vs_adult`: asserts `athlete_normal_to != adult_normal_to` (expected: 27.0 vs 25.0)
- ✅ `test_visualization_ranges_are_group_aware_elderly_vs_adult`: asserts differences in both underweight and normal thresholds

### 6. Null Cases (category=None Groups)

**Real logic from `core/bmi/engine.py`:**

```python
# Groups with category=None
if group in {"too_young", "child", "teen", "pregnant"}:
    return None  # visualization is None
```

**Adaptation in tests:**
- ✅ `test_visualization_contract_child_is_null`: age=12 → child → visualization: null
- ✅ `test_visualization_contract_teen_is_null`: age=16 → teen → visualization: null
- ✅ `test_visualization_contract_pregnant_is_null`: pregnant="yes" → visualization: null

### 7. Graceful Fallback

**Real implementation from `app/routers/bmi.py`:**

```python
try:
    resp.visualization = build_bmi_scale_v1(result)
except Exception:
    logger.exception("Failed to build BMI visualization spec (BMI=%.1f)", result.bmi)
    resp.visualization = None  # ✅ Graceful fallback
```

**Adaptation in tests:**
- ✅ `test_visualization_contract_graceful_fallback_on_builder_failure`: monkeypatches builder to fail, asserts endpoint returns 200 with visualization: null

---

## 📝 Key Adaptations Made

### Documentation (`docs/bmi/visualization.md`)

1. **Age band mapping:**
   - ✅ Documented exact age boundaries from `_age_band()`
   - ✅ Clarified: age 12 = "child", age 13-19 = "teen"

2. **Group-aware ranges:**
   - ✅ Added table showing differences (adult vs athlete vs elderly)
   - ✅ Documented exact thresholds (18.5/25.0 vs 18.5/27.0 vs 17.5/26.0)

3. **Null cases:**
   - ✅ Listed all groups that return `visualization: null`
   - ✅ Explained why (category=None groups)

4. **Implementation references:**
   - ✅ Added links to actual code locations
   - ✅ Documented `_BMI_BREAKPOINTS` registry

### Tests (`tests/test_bmi_contract_visualization.py`)

1. **Request payload:**
   - ✅ Used `_valid_payload()` helper (matches existing pattern)
   - ✅ Fields match exactly: `weight_kg`, `height_cm`, `age`, `gender`, `pregnant`, `athlete`, `lang`

2. **Age boundaries:**
   - ✅ `age=12` for child test (correctly maps to "child")
   - ✅ `age=16` for teen test (correctly maps to "teen")
   - ✅ `age=75` for elderly test (correctly maps to "elderly")

3. **Test client:**
   - ✅ Used `client: TestClient` fixture (matches conftest pattern)
   - ✅ Used `_post_bmi()` helper for consistency

4. **Contract assertions:**
   - ✅ Structure validation (kind, bmi, min, max, ranges, marker)
   - ✅ Range invariants (4 ranges, sorted, contiguous, covers [min, max])
   - ✅ Group awareness (athlete vs adult, elderly vs adult)
   - ✅ Null cases (child, teen, pregnant)
   - ✅ Graceful fallback (builder failure → 200 + visualization: null)

---

## ✅ Verification

### Files Created

1. **`docs/bmi/visualization.md`** (✅ Created)
   - Contract documentation
   - JSON examples for all groups
   - Age band mapping
   - Group-aware ranges explanation
   - Client guidance

2. **`tests/test_bmi_contract_visualization.py`** (✅ Created)
   - 7 contract tests
   - All adapted to real project structure
   - Uses existing test patterns

### Code Compatibility

- ✅ Request fields match `BMICalculateRequest`
- ✅ Age boundaries match `_age_band()` logic
- ✅ Test client matches `conftest.py` fixture
- ✅ Group-aware ranges match `_BMI_BREAKPOINTS` registry
- ✅ Null cases match `category=None` groups
- ✅ Graceful fallback matches router implementation

---

## 🚀 Ready to Commit

Both files are ready and adapted to the project structure:

```bash
# Commit 1
git add docs/bmi/visualization.md
git commit -m "docs(bmi): add BMI visualization contract documentation"

# Commit 2
git add tests/test_bmi_contract_visualization.py
git commit -m "test(bmi): add contract tests for visualization field"
```

---

## 📊 Test Coverage

**Contract tests cover:**
1. ✅ Structure validation (adult group)
2. ✅ Null cases (child, teen, pregnant)
3. ✅ Group awareness (athlete vs adult, elderly vs adult)
4. ✅ Graceful fallback (builder failure)

**Total:** 7 contract tests, all adapted to real project structure.

