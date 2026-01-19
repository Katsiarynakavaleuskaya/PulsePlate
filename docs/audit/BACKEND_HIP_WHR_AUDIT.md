# Backend Audit — Hip Circumference and WHR (Waist-to-Hip Ratio) Implementation

**Date:** 2026-01-18
**Purpose:** Audit of PRO-tier `hip_cm` + WHR (and FREE-tier exclusion) for BMI calculation
**Status:** Implemented (PRO tier contract + engine support)

---

## Executive Summary

**Current State:**
- ✅ **FREE endpoint:** `POST /api/v1/bmi/calculate` (`app/routers/bmi.py`)
  - Request: `BMICalculateRequest` (rejects `hip_cm`)
  - Response: `BMICalculateResponse` (omits `whr`)
- ✅ **PRO endpoint (canonical namespace):** `POST /api/v1/pro/bmi/calculate` (per `/api/v1/pro/*` policy)
  - Current implementation is served from `POST /api/v1/bmi/pro/calculate` (`app/routers/bmi.py`) pending route move.
  - Request: `BMICalculateProRequest` (optional `hip_cm`)
  - Response: `BMICalculateProResponse` (optional `whr`)
- ✅ **Engine behavior:** `core/bmi/engine.py` computes `whr` and returns it only when both `waist_cm` and `hip_cm` are provided and > 0.

---

## A) Audit Questions — Answers

### A1. What is the canonical outcome of this PR?

**Answer:**
- **PRO tier:** adds `hip_cm` in `BMICalculateProRequest` and `whr` in `BMICalculateProResponse`.
- **FREE tier:** explicitly rejects `hip_cm` and omits `whr` from the response.

**DoD:**
- `BMICalculateProRequest` / `BMICalculateProResponse` appear in OpenAPI schema for the PRO endpoint.
- `BMICalculateRequest` rejects `hip_cm` (extra fields forbidden) and `BMICalculateResponse` omits `whr`.
- `core/bmi/engine.py` computes `whr` and returns it only when both `waist_cm` and `hip_cm` are provided and > 0.
- All tests pass, coverage ≥97%.

---

### A2. Where is the canonical BMI contract?

**Answer:**
- ✅ **FREE endpoint:** `/api/v1/bmi/calculate` (`app/routers/bmi.py`) → `BMICalculateRequest` / `BMICalculateResponse`
- ✅ **PRO endpoint (canonical namespace):** `/api/v1/pro/bmi/calculate` (policy)
  - Current implementation is served from `/api/v1/bmi/pro/calculate` (`app/routers/bmi.py`)
  - Uses `BMICalculateProRequest` / `BMICalculateProResponse`

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
- FREE: keep `BMICalculateRequest` strict (`extra="forbid"`) so `hip_cm` is rejected.
- PRO: expose `hip_cm` via `BMICalculateProRequest`.
- FREE: keep `BMICalculateResponse` strict (`extra="forbid"`) so `whr` is omitted.
- PRO: expose `whr` via `BMICalculateProResponse`.

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
- ✅ **Top-level field (PRO only):** `whr?: float | None` in `BMICalculateProResponse` (not in nested `ratios` block)
- ✅ **Parity with `wht_ratio`:** Same structure (optional float)
- ✅ **No i18n keys:** Just number (like `wht_ratio`)

**DoD:**
- `BMICalculateProResponse.whr` exists and is nullable; `BMICalculateResponse` (FREE) omits `whr`.

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
- ✅ Web is thin client (no BMI logic on frontend)
- ✅ No local thresholds (no WHR risk calculation on frontend)
- ✅ Render only:
  - FREE flow: no WHR (response omits `whr`)
  - PRO flow: display `response.whr` only if present and non-null

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

### C1. Frontend validation for hip input (PRO tier only)

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

**Decision:** Hip input is PRO-tier only; validate `>0`, normalize commas, send only if valid.

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
- Hip input should only be shown in a PRO-tier UI/flow (not in the FREE `/api/v1/bmi/calculate` form)

**Decision:** i18n keys ready, no backend changes needed.

---

## D) Tests (DoD)

### D1. Backend tests required

**Answer:**
- ✅ **FREE contract:** rejects `hip_cm` and omits `whr`
- ✅ **PRO contract:** accepts `hip_cm` (optional) and returns `whr` only when both `waist_cm` and `hip_cm` are provided
- ✅ **Negative:** `hip_cm <= 0` is rejected with 422 on the PRO endpoint
- ✅ **Engine:** `core/bmi/engine.py` computes WHR and returns `None` when inputs are missing/invalid

**DoD (canonical references):**
- See `tests/test_bmi_calculate_endpoint.py` for:
  - FREE: `test_bmi_calculate_free_tier_does_not_accept_hip_cm`, `test_bmi_calculate_free_tier_does_not_return_whr`
  - PRO: `test_bmi_calculate_pro_with_hip_returns_whr`, `test_bmi_calculate_pro_without_hip_returns_null_whr`,
    `test_bmi_calculate_rejects_non_positive_hip`, `test_bmi_calculate_rejects_negative_hip`

---

### D2. Web tests (follow-up PR)

**Answer:**
- ✅ **PRO-only form test:** Hip field renders only in a PRO-tier UI/flow (not on FREE BMI form)
- ✅ **Payload test:** `hip_cm` is included in the PRO request only when valid (`>0`)
- ✅ **Result test:** WHR renders only if `response.whr != null` (PRO response)
- ✅ **Regression test:** FREE BMI UI does not show hip input and does not expect `whr` in FREE response
- ✅ **i18n test:** Locale keys pass quality checks

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
1. **PR-backend:** `feat(bmi): add PRO-tier hip_cm and compute WHR in PRO response`
2. **PR-web:** `feat(web): add PRO-gated hip input and render WHR from PRO response`

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
   - FREE: `BMICalculateRequest` rejects extra fields (including `hip_cm`)
   - PRO: `BMICalculateProRequest` adds optional `hip_cm`
   - FREE: `BMICalculateResponse` omits `whr`
   - PRO: `BMICalculateProResponse` adds optional `whr`

2. `core/bmi/engine.py`
   - Add `_compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None`
   - Integrate into `calculate_bmi_result()` (Step 9.5)

3. `app/routers/bmi.py`
   - FREE: call engine with `hip_cm=None` and omit `whr` in response
   - PRO: accept `BMICalculateProRequest`, pass `hip_cm=req.hip_cm`, include `whr` in response

4. `tests/test_bmi_calculate_endpoint.py`
   - FREE: rejects `hip_cm` and omits `whr`
   - PRO: `hip_cm` enables `whr`; non-positive hip is rejected with 422

5. `make openapi` (regenerate OpenAPI artifacts)
   - `frontend/src/api/openapi.json`
   - `frontend/src/api/schema.ts` (if TypeScript generation exists)

---

### G2. Code Changes (Skeleton)

**File: `app/schemas/bmi.py`**

```python
class BMICalculateRequest(BaseModel):
    model_config = {"extra": "forbid"}  # FREE: rejects hip_cm
    # ... existing fields ...

class BMICalculateResponse(BaseModel):
    model_config = {"extra": "forbid"}  # FREE: omits whr
    # ... existing fields ...

class BMICalculateProRequest(BMICalculateRequest):
    hip_cm: float | None = Field(default=None, gt=0)

class BMICalculateProResponse(BMICalculateResponse):
    whr: float | None = Field(default=None)
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
        hip_cm=None,  # FREE tier: do not accept hip_cm / do not compute WHR
        lang=request.lang,
    )

    return BMICalculateResponse(
        # ... existing fields ...
    )

# PRO tier endpoint (canonical namespace should be /api/v1/pro/bmi/calculate; current implementation lives here)
@router.post("/pro/calculate", response_model=BMICalculateProResponse)
async def calculate_bmi_pro(request: BMICalculateProRequest) -> BMICalculateProResponse:
    # ... existing code ...
    result = calculate_bmi_result(
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        age=request.age,
        gender=request.gender or "",
        pregnant=request.pregnant,
        athlete=request.athlete,
        waist_cm=request.waist_cm,
        hip_cm=request.hip_cm,
        lang=request.lang,
    )
    return BMICalculateProResponse(
        # ... existing fields ...
        whr=result.whr,
    )
```

---

### G3. Definition of Done (DoD)

**Backend PR DoD:**
- [ ] `BMICalculateRequest` rejects `hip_cm` (FREE tier)
- [ ] `BMICalculateResponse` omits `whr` (FREE tier)
- [ ] `hip_cm` field added to `BMICalculateProRequest` schema (PRO tier)
- [ ] `whr` field added to `BMICalculateProResponse` schema (PRO tier)
- [ ] `_compute_whr()` function implemented in `core/bmi/engine.py`
- [ ] `calculate_bmi_result()` accepts `hip_cm` parameter
- [ ] `calculate_bmi_result()` returns `whr` in result
- [ ] Router passes `hip_cm=None` for FREE and includes `whr` only in PRO response
- [ ] OpenAPI schema regenerated (`make openapi`)
- [ ] Contract test: `hip_cm` in PRO OpenAPI request schema
- [ ] Contract test: `whr` in PRO OpenAPI response schema
- [ ] Unit test: `_compute_whr(80, 100) == 0.8`
- [ ] Unit test: `_compute_whr(None, 100) is None`
- [ ] Unit test: `_compute_whr(80, None) is None`
- [ ] Negative test: `hip_cm=0` → 422 validation error
- [ ] Integration test: FREE endpoint rejects `hip_cm`
- [ ] Integration test: FREE endpoint omits `whr`
- [ ] Integration test: PRO endpoint with `hip_cm` → returns `whr`
- [ ] Integration test: PRO endpoint without `hip_cm` → returns `whr=null`
- [ ] Coverage ≥97% for changed files
- [ ] `make verify` passes (lint, typecheck, test-fast, diff-cov)
- [ ] `make openapi-check` passes (determinism)

**Web Follow-up PR DoD (separate PR):**
- [ ] Hip input field added to a PRO-tier UI/flow (do not add to FREE `/api/v1/bmi/calculate` form)
- [ ] `hip_cm` sent in PRO request payload when provided
- [ ] WHR displayed in result when `response.whr != null` (PRO flow)
- [ ] WHR hidden when `response.whr == null` (PRO flow)
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
6. **Web follow-up PR:** Separate PR to add PRO-gated hip input + render WHR
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
5. **Open PR:** Title: `feat(bmi): add PRO-tier hip_cm and compute WHR in PRO response`
6. **After merge:** Create web follow-up PR to add PRO-gated hip input + render WHR

---

## End of Audit
