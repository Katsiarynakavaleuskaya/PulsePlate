# Backend Audit — Hip Circumference and WHR (Waist-to-Hip Ratio) Implementation

**Date:** 2026-01-18
**Purpose:** Pre-implementation audit for adding `hip_cm` and WHR calculation to BMI endpoint
**Status:** Pre-implementation (backend contract extension, web follow-up PR planned)

---

## Executive Summary

**Current State:**
- ✅ BMI endpoint exists: `POST /api/v1/bmi/calculate` (`app/routers/bmi.py`)
- ✅ Current request includes: `weight_kg, height_cm, gender, age, waist_cm?, athlete, pregnant, lang`
- ✅ Current response includes: `wht_ratio` (waist-to-height), `waist_risk` (risk assessment)
- ❌ **`hip_cm` field: NOT in request schema**
- ❌ **WHR (waist-to-hip ratio): NOT calculated or returned**

**Proposed Change:**
- Add `hip_cm?: float | None` to `BMICalculateRequest`
- Add `whr?: float | None` to `BMICalculateResponse`
- Calculate WHR in `core/bmi/engine.py` (following "One BMI Engine" policy)
- Return WHR only when both `waist_cm` and `hip_cm` are provided

**Critical Finding:** This is a **backend-first PR** (contract extension). Web follow-up PR will restore hip input field and render WHR from response.

---

## A) Audit Questions — Answers

### A1. What is the canonical outcome of this PR?

**Answer:**
- **(а) Backend: `hip_cm` + WHR in BMI response** ✅
- PR is **backend-first** (canon: WHR = backend-first, web follows)

**DoD:**
- `hip_cm` appears in OpenAPI request schema
- `whr` appears in OpenAPI response schema
- WHR calculated in `core/bmi/engine.py` (canonical location)
- All tests pass, coverage ≥97%

**Decision:** Backend PR only. Web follow-up PR will restore hip input + render WHR.

---

### A2. Where is the canonical BMI contract?

**Answer:**
- ✅ **Endpoint:** `/api/v1/bmi/calculate` (`app/routers/bmi.py:57`)
- ✅ **Request schema:** `app/schemas/bmi.py:178` (`BMICalculateRequest`)
- ✅ **Response schema:** `app/schemas/bmi.py:404` (`BMICalculateResponse`)

**Current Request Fields:**
```python
weight_kg: float (required, gt=0)
height_cm: float (required, gt=0)
age: int (required, ge=1, le=120)
gender: str | None (optional, normalized)
pregnant: str | bool (default=False, normalized)
athlete: str | bool (default=False, normalized)
waist_cm: float | None (optional, gt=0)
lang: Language (default="en")
```

**Current Response Fields:**
```python
bmi: float
category: str | None
group: str
group_display: str
interpretation: str
wht_ratio: float | None  # Waist-to-Height Ratio
waist_risk: WaistRiskResultSchema | None
notes: list[str]
age_band: Literal["too_young", "child", "teen", "adult", "elderly"]
visualization: BMIScaleV1Spec | None
interpretation_v1: BMIInterpretationV1Schema | None
soft_paywall: SoftPaywallHook | None
```

**DoD:**
- Add `hip_cm?: float | None = Field(default=None, gt=0)` to `BMICalculateRequest`
- Add `whr?: float | None = Field(default=None, description="Waist-to-Hip Ratio. Calculated only if both waist_cm and hip_cm are provided.")` to `BMICalculateResponse`

**Decision:** Extend existing schemas, maintain backward compatibility (optional fields).

---

### A3. How should WHR be calculated?

**Answer:**
- ✅ **Formula:** `WHR = waist_cm / hip_cm`
- ✅ **WHtR already exists:** `wht_ratio` in response (waist-to-height)
- ✅ **WHR is different:** waist-to-hip (not waist-to-height)

**DoD:**
```python
# core/bmi/engine.py
def _compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None:
    """
    RU: WHR = waist_cm / hip_cm, округление до 2 знаков.
    EN: WHR = waist_cm / hip_cm, rounded to 2 decimals.

    Returns None if either waist_cm or hip_cm is None or <= 0.
    """
    if waist_cm is None or hip_cm is None:
        return None
    if waist_cm <= 0 or hip_cm <= 0:
        return None
    try:
        ratio = waist_cm / hip_cm
        return round(ratio, 2)  # Same precision as wht_ratio
    except (ZeroDivisionError, OverflowError):
        return None
```

**Decision:** WHR = `waist_cm / hip_cm`, rounded to 2 decimals (parity with `wht_ratio`).

---

### A4. Should `hip_cm` be optional or required?

**Answer:**
- ✅ **Optional** (`float | None = Field(default=None, gt=0)`)
- ✅ **Rationale:** Backward compatibility (existing clients don't send hip)
- ✅ **If absent:** `whr=null` in response (no calculation)

**DoD:**
```python
# app/schemas/bmi.py
hip_cm: float | None = Field(
    default=None,
    gt=0,
    description=(
        "Hip circumference in centimeters (optional). "
        "If provided along with waist_cm, enables WHR calculation."
    ),
    examples=[95.0, 100.5, None],
)
```

**Decision:** Optional field. WHR calculated only when both `waist_cm` and `hip_cm` are provided and >0.

---

### A5. Where should WHR live in the response?

**Answer:**
- ✅ **Top-level field:** `whr?: float | None` (not in nested `ratios` block)
- ✅ **Parity with `wht_ratio`:** Same structure (optional float)
- ✅ **No i18n keys:** Just number (like `wht_ratio`)

**DoD:**
```python
# app/schemas/bmi.py
whr: float | None = Field(
    None,
    description=(
        "Waist-to-Hip Ratio (WHR). "
        "Calculated only if both waist_cm and hip_cm were provided and >0."
    ),
    examples=[0.80, 0.95, None],
)
```

**Decision:** Top-level optional field, numeric only (no categories/buckets in first iteration).

---

### A6. Do we need WHR risk categories/buckets?

**Answer:**
- ✅ **First iteration: number only** (no risk buckets)
- ✅ **Rationale:** Keep scope minimal, add buckets later if needed
- ✅ **Parity:** `wht_ratio` is also just a number (risk assessment is in `waist_risk`)

**DoD:**
- `whr` field is `float | None` (no nested structure)
- No `whr_risk` field (can be added in future PR if needed)

**Decision:** WHR = number only. Risk categories can be added in follow-up PR if product requires.

---

## B) Thin Client Policy

### B1. Web should only render what backend provides

**Answer:**
- ✅ **Confirmed:** Web is thin client (no BMI logic on frontend)
- ✅ **No local thresholds:** No WHR risk calculation on frontend
- ✅ **Render only:** Display `response.whr` if present, hide if `null`

**DoD (Web follow-up PR):**
```typescript
// frontend/src/pages/BMI/BMICalculatePage.tsx
{response.whr != null && (
  <div className="flex justify-between">
    <span className="text-muted">{t('bmiCalculate.result.whr')}</span>
    <span className="font-semibold text-text">{response.whr.toFixed(2)}</span>
  </div>
)}
```

**Decision:** Web renders `whr` from response, no client-side calculation.

---

### B2. What should UI do if `whr=null`?

**Answer:**
- ✅ **Hide block entirely** (same as `wht_ratio` handling)
- ✅ **No placeholder:** Don't show "—" or "N/A"

**DoD:**
- Conditional rendering: `{response.whr != null && <WHRDisplay />}`
- No fallback text

**Decision:** Hide WHR block if `null` (graceful skip, no UI noise).

---

## C) Validation and UX

### C1. Frontend validation for hip input

**Answer:**
- ✅ **Comma normalization:** Use `normalizeNumber()` helper (RU locale support)
- ✅ **Range validation:** `>0` (same as `waist_cm`)
- ✅ **Optional field:** Not required in form

**DoD (Web follow-up PR):**
```typescript
// frontend/src/pages/BMI/BMICalculatePage.tsx
const normalizedHip = normalizeNumber(hipCm);
const parsedHipCm = parseFloat(normalizedHip);

// In request payload
hip_cm: Number.isFinite(parsedHipCm) && parsedHipCm > 0 ? parsedHipCm : undefined,
```

**Decision:** Frontend validates `>0`, normalizes commas, sends only if valid.

---

### C2. Backend validation for hip_cm

**Answer:**
- ✅ **422 if `hip_cm<=0`:** Same validation as `waist_cm` (Pydantic `gt=0`)
- ✅ **If hip provided but waist missing:** `whr=null` (WHR requires both)
- ✅ **If waist provided but hip missing:** `whr=null` (WHR requires both)

**DoD:**
```python
# app/schemas/bmi.py
hip_cm: float | None = Field(
    default=None,
    gt=0,  # Validation: must be >0 if provided
    ...
)

# core/bmi/engine.py
def _compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None:
    if waist_cm is None or hip_cm is None:
        return None  # Both required
    if waist_cm <= 0 or hip_cm <= 0:
        return None  # Both must be positive
    ...
```

**Decision:** Backend validates `hip_cm>0` if provided. WHR calculated only when both waist and hip are valid.

---

### C3. i18n keys for hip input

**Answer:**
- ✅ **Keys already exist:** `bmiCalculate.form.hipLabel` in `en.json:274`, `ru.json:274`, `es.json:274`
- ✅ **Current values:**
  - EN: `"Hip (cm, optional)"`
  - RU: `"Бёдра (см, необязательно)"`
  - ES: `"Cadera (cm, opcional)"`

**DoD:**
- Keys exist, no changes needed
- Web follow-up PR will restore hip input field using existing keys

**Decision:** i18n keys ready, no backend changes needed.

---

## D) Tests (DoD)

### D1. Backend tests required

**Answer:**
- ✅ **Contract test:** `hip_cm` appears in OpenAPI schema (generated)
- ✅ **Unit test:** WHR calculation (example: `waist_cm=80, hip_cm=100` → `whr=0.8`)
- ✅ **Negative test:** `hip_cm<=0` → 422 validation error
- ✅ **Serialization determinism:** Float precision (2 decimals, same as `wht_ratio`)

**DoD:**
```python
# tests/test_bmi_schemas.py
def test_bmi_calculate_request_accepts_hip_cm():
    """Test that hip_cm is accepted in request schema."""
    request = BMICalculateRequest(
        weight_kg=70.0,
        height_cm=170.0,
        age=30,
        gender="female",
        hip_cm=95.0,
    )
    assert request.hip_cm == 95.0

def test_bmi_calculate_request_rejects_hip_cm_zero():
    """Test that hip_cm <= 0 is rejected."""
    with pytest.raises(ValidationError):
        BMICalculateRequest(
            weight_kg=70.0,
            height_cm=170.0,
            age=30,
            gender="female",
            hip_cm=0.0,
        )

# tests/test_bmi_engine.py
def test_compute_whr_calculates_correctly():
    """Test WHR calculation."""
    whr = _compute_whr(waist_cm=80.0, hip_cm=100.0)
    assert whr == 0.8

def test_compute_whr_returns_none_if_missing():
    """Test WHR returns None if waist or hip missing."""
    assert _compute_whr(None, 100.0) is None
    assert _compute_whr(80.0, None) is None
    assert _compute_whr(None, None) is None

# tests/test_bmi_calculate_endpoint.py
def test_bmi_calculate_with_hip_returns_whr():
    """Test endpoint returns WHR when both waist and hip provided."""
    response = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["whr"] == 0.8

def test_bmi_calculate_without_hip_returns_null_whr():
    """Test endpoint returns whr=null when hip not provided."""
    response = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            # hip_cm not provided
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["whr"] is None
```

**Decision:** 4 test categories required: contract, unit, negative, integration.

---

### D2. Web tests (follow-up PR)

**Answer:**
- ✅ **Form test:** Hip field renders in BMI form
- ✅ **Payload test:** `hip_cm` sent in request when provided
- ✅ **Result test:** WHR renders only if `response.whr != null`
- ✅ **i18n test:** Locale keys pass quality checks

**DoD (Web follow-up PR):**
```typescript
// frontend/src/pages/BMI/__tests__/BMICalculatePage.test.tsx
it("renders hip input field", () => {
  render(<BMICalculatePage />);
  expect(screen.getByLabelText(/hip/i)).toBeInTheDocument();
});

it("sends hip_cm in request when provided", async () => {
  const mockApi = vi.spyOn(bmiApi, "calculateBMI");
  render(<BMICalculatePage />);

  fireEvent.change(screen.getByLabelText(/hip/i), { target: { value: "100" } });
  fireEvent.click(screen.getByText(/calculate/i));

  await waitFor(() => {
    expect(mockApi).toHaveBeenCalledWith(
      expect.objectContaining({ hip_cm: 100.0 })
    );
  });
});

it("renders WHR only when response.whr is not null", () => {
  const response = { bmi: 24.2, whr: 0.8, ... };
  render(<BMICalculatePage />);
  // ... set response state
  expect(screen.getByText(/0.80/)).toBeInTheDocument();

  const responseNull = { bmi: 24.2, whr: null, ... };
  // ... set response state
  expect(screen.queryByText(/whr/i)).not.toBeInTheDocument();
});
```

**Decision:** Web tests in follow-up PR (not in backend PR).

---

### D3. Coverage gate

**Answer:**
- ✅ **Coverage threshold: 97%** (confirmed: `AGENTS.md`, `codecov.yml`, CI workflows)
- ✅ **Diff-coverage: ≥97%** for changed lines
- ✅ **Total coverage: ≥97%** (must not decrease)

**DoD:**
- `make cov-check` passes (total ≥97%)
- `make diff-cov` passes (diff-coverage ≥97%)
- CI coverage job green

**Decision:** Coverage gate enforced at 97% (hard rule).

---

## E) Risks and Dependencies

### E1. "One BMI Engine" risk

**Answer:**
- ✅ **WHR calculation must live in `core/bmi/engine.py`** (canonical location)
- ✅ **Pattern:** Follow `_compute_wht_ratio()` pattern
- ✅ **Integration:** Add to `calculate_bmi_result()` orchestrator (Step 9.5, after WHtR)

**DoD:**
```python
# core/bmi/engine.py

# Step 9: WHtR calculation (existing)
wht_ratio = _compute_wht_ratio(waist_cm, height_m)

# Step 9.5: WHR calculation (new)
whr = _compute_whr(waist_cm, hip_cm)  # NEW

# Step 10: Waist risk calculation (existing)
waist_risk = ...
```

**Decision:** WHR calculation in `core/bmi/engine.py`, integrated into orchestrator.

---

### E2. AGENTS.md update needed?

**Answer:**
- ✅ **No update needed** (hip/WHR is extension of existing contract, not new policy)
- ✅ **Rationale:** Follows existing patterns (`wht_ratio`, `waist_risk`)

**DoD:**
- No changes to `AGENTS.md` required

**Decision:** No policy changes needed.

---

## F) PR Format

### F1. Single PR or split?

**Answer:**
- ✅ **Backend PR only** (this audit)
- ✅ **Web follow-up PR** (separate, after backend merge)

**Canonical order:**
1. **PR-backend:** `feat(bmi): add optional hip_cm and compute WHR in response`
2. **PR-web:** `feat(web): restore hip input and render WHR from response`

**Decision:** 2 PRs (backend-first, web follows).

---

### F2. Database migrations needed?

**Answer:**
- ✅ **No migrations needed** (no DB schema changes)
- ✅ **Rationale:** BMI calculation is stateless (no storage)

**DoD:**
- No Alembic migrations
- No model changes

**Decision:** No DB changes required.

---

## G) Implementation Plan

### G1. Files to Modify

**Backend Files:**
1. `app/schemas/bmi.py`
   - Add `hip_cm?: float | None` to `BMICalculateRequest`
   - Add `whr?: float | None` to `BMICalculateResponse`

2. `core/bmi/engine.py`
   - Add `_compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None`
   - Integrate into `calculate_bmi_result()` (Step 9.5)

3. `app/routers/bmi.py`
   - Pass `hip_cm` from request to engine
   - Add `whr` to response from engine result

4. `tests/test_bmi_schemas.py`
   - Test `hip_cm` in request schema
   - Test `whr` in response schema

5. `tests/test_bmi_engine.py`
   - Test `_compute_whr()` function
   - Test edge cases (None, <=0, division)

6. `tests/test_bmi_calculate_endpoint.py`
   - Test endpoint with `hip_cm` → returns `whr`
   - Test endpoint without `hip_cm` → returns `whr=null`
   - Test validation (`hip_cm<=0` → 422)

7. `make openapi` (regenerate OpenAPI artifacts)
   - `frontend/src/api/openapi.json`
   - `frontend/src/api/schema.ts` (if TypeScript generation exists)

---

### G2. Code Changes (Skeleton)

**File: `app/schemas/bmi.py`**

```python
class BMICalculateRequest(BaseModel):
    # ... existing fields ...

    hip_cm: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Hip circumference in centimeters (optional). "
            "If provided along with waist_cm, enables WHR calculation."
        ),
        examples=[95.0, 100.5, None],
    )

class BMICalculateResponse(BaseModel):
    # ... existing fields ...

    whr: float | None = Field(
        None,
        description=(
            "Waist-to-Hip Ratio (WHR). "
            "Calculated only if both waist_cm and hip_cm were provided and >0."
        ),
        examples=[0.80, 0.95, None],
    )
```

**File: `core/bmi/engine.py`**

```python
def _compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None:
    """
    RU: WHR = waist_cm / hip_cm, округление до 2 знаков.
    EN: WHR = waist_cm / hip_cm, rounded to 2 decimals.

    Returns None if either waist_cm or hip_cm is None or <= 0.
    """
    if waist_cm is None or hip_cm is None:
        return None
    if waist_cm <= 0 or hip_cm <= 0:
        return None
    try:
        ratio = waist_cm / hip_cm
        return round(ratio, 2)
    except (ZeroDivisionError, OverflowError):
        return None

def calculate_bmi_result(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    pregnant: bool,
    athlete: bool,
    waist_cm: float | None,
    hip_cm: float | None,  # NEW parameter
    lang: str | None,
) -> BMICalculateResult:
    # ... existing steps ...

    # Step 9.5: WHR calculation (new)
    whr = _compute_whr(waist_cm, hip_cm)

    # ... rest of function ...

    return BMICalculateResult(
        # ... existing fields ...
        whr=whr,  # NEW field
    )
```

**File: `app/routers/bmi.py`**

```python
@router.post("/calculate", response_model=BMICalculateResponse)
async def calculate_bmi(request: BMICalculateRequest) -> BMICalculateResponse:
    # ... existing code ...

    result = calculate_bmi_result(
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        age=request.age,
        gender=request.gender or "",
        pregnant=request.pregnant,
        athlete=request.athlete,
        waist_cm=request.waist_cm,
        hip_cm=request.hip_cm,  # NEW
        lang=request.lang,
    )

    return BMICalculateResponse(
        # ... existing fields ...
        whr=result.whr,  # NEW
    )
```

---

### G3. Definition of Done (DoD)

**Backend PR DoD:**
- [ ] `hip_cm` field added to `BMICalculateRequest` schema
- [ ] `whr` field added to `BMICalculateResponse` schema
- [ ] `_compute_whr()` function implemented in `core/bmi/engine.py`
- [ ] `calculate_bmi_result()` accepts `hip_cm` parameter
- [ ] `calculate_bmi_result()` returns `whr` in result
- [ ] Router passes `hip_cm` to engine and includes `whr` in response
- [ ] OpenAPI schema regenerated (`make openapi`)
- [ ] Contract test: `hip_cm` in OpenAPI request schema
- [ ] Contract test: `whr` in OpenAPI response schema
- [ ] Unit test: `_compute_whr(80, 100) == 0.8`
- [ ] Unit test: `_compute_whr(None, 100) is None`
- [ ] Unit test: `_compute_whr(80, None) is None`
- [ ] Negative test: `hip_cm=0` → 422 validation error
- [ ] Integration test: endpoint with `hip_cm` → returns `whr`
- [ ] Integration test: endpoint without `hip_cm` → returns `whr=null`
- [ ] Coverage ≥97% for changed files
- [ ] `make verify` passes (lint, typecheck, test-fast, diff-cov)
- [ ] `make openapi-check` passes (determinism)

**Web Follow-up PR DoD (separate PR):**
- [ ] Hip input field restored in `BMICalculatePage.tsx`
- [ ] `hip_cm` sent in request payload when provided
- [ ] WHR displayed in result when `response.whr != null`
- [ ] WHR hidden when `response.whr == null`
- [ ] i18n keys pass locale quality tests
- [ ] Tests: form renders hip field
- [ ] Tests: payload includes `hip_cm` when provided
- [ ] Tests: WHR renders conditionally
- [ ] `npm test` passes
- [ ] `npm run build` passes

---

## H) Decision Log

**Decisions Made:**
1. **Backend-first PR:** Add `hip_cm` + WHR calculation in backend only
2. **Optional `hip_cm`:** Field is optional for backward compatibility
3. **WHR = number only:** No risk categories in first iteration
4. **Top-level `whr` field:** Not nested in `ratios` block (parity with `wht_ratio`)
5. **Calculation in engine:** `_compute_whr()` in `core/bmi/engine.py` (One BMI Engine policy)
6. **Web follow-up PR:** Separate PR to restore hip input + render WHR
7. **No AGENTS.md update:** Extension of existing contract, not new policy

**Open Questions:**
- None (all questions answered)

**Risks Mitigated:**
- ✅ "One BMI Engine" risk: WHR calculation in canonical location
- ✅ Backward compatibility: Optional fields, no breaking changes
- ✅ Scope creep: Backend-only PR, web follows separately

---

## I) Next Steps

1. **Create backend PR branch:** `feat/bmi-hip-whr`
2. **Implement changes:** Follow G2 skeleton
3. **Write tests:** Follow D1 requirements
4. **Run verification:** `make verify`, `make openapi-check`
5. **Open PR:** Title: `feat(bmi): add optional hip_cm and compute WHR in response`
6. **After merge:** Create web follow-up PR to restore hip input + render WHR

---

**End of Audit**
