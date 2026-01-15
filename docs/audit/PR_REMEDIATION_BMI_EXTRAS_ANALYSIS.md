# BMI Extras Consolidation Analysis

**Purpose:** Determine canonical module for consolidation.

**Files to consolidate:**
1. `core/bmi_extras.py`
2. `core/bmi_extras_pro.py`
3. `core/bmi_extras_simple.py`

---

## File Comparison

### `core/bmi_extras.py` (Full version)
**Functions (6):**
- `wht_ratio(waist_cm, height_cm)` → float
- `whr_ratio(waist_cm, hip_cm, sex)` → float (with sex parameter)
- `ffmi(weight_kg, height_cm, bodyfat_percent)` → float
- `interpret_wht_ratio(wht_ratio_value, lang)` → Dict[str, str]
- `interpret_whr_ratio(whr_ratio_value, sex, lang)` → Dict[str, str]
- `stage_obesity(bmi, whtr, whr, sex, lang)` → Dict[str, str]

**Used by:**
- `tests/test_bmi_extras.py`
- `tests/test_bmi_pro.py`
- `tests/test_bmi_pro_spanish.py`

---

### `core/bmi_extras_pro.py` (Identical to bmi_extras.py)
**Functions (6):** Same as `bmi_extras.py` (identical signatures)

**Used by:**
- `tests/test_bmi_extras_pro_coverage.py`
- `tests/edges/test_more_edges.py`

**Status:** **Duplicate** of `bmi_extras.py` (can be deleted)

---

### `core/bmi_extras_simple.py` (Simplified version)
**Functions (5):**
- `BMIProCard` (dataclass) - **unique to simple**
- `wht_ratio(waist_cm, height_cm)` → float
- `whr_ratio(waist_cm, hip_cm)` → float (**NO sex parameter**)
- `ffmi(value_weight_kg, height_cm, bodyfat_percent)` → float
- `stage_obesity(bmi, whtr, whr, sex, lang)` → Dict[str, str]

**Used by:**
- `app/routers/bmi_pro.py` (**PRODUCTION CODE**)
- `tests/test_bmi_extras_simple.py`

**Key differences:**
- `whr_ratio` has **no sex parameter** (simplified)
- Has `BMIProCard` dataclass (not in other files)
- No `interpret_*` functions

---

## Usage Analysis

### Production Code Usage

**`app/routers/bmi_pro.py`:**
```python
from core.bmi_extras_simple import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio
```

**Critical:** Uses `whr_ratio` **without sex parameter** and `BMIProCard`.

---

## Recommendation: Canonical Module

### ✅ **Choose `core/bmi_extras.py` as canonical**

**Rationale:**
1. **Most complete** (has all 6 functions including `interpret_*`)
2. **Used by most tests** (test coverage)
3. **Full-featured** (supports sex-specific WHR)

**Migration plan:**

1. **Add `BMIProCard` to `core/bmi_extras.py`** (from `bmi_extras_simple.py`)
2. **Support both `whr_ratio` signatures:**
   - `whr_ratio(waist_cm, hip_cm, sex)` - full version (default)
   - `whr_ratio(waist_cm, hip_cm)` - simplified (optional sex, defaults to "general")
3. **Update `app/routers/bmi_pro.py`** to import from `core.bmi_extras`
4. **Update all test imports** to use `core.bmi_extras`
5. **Delete `core/bmi_extras_pro.py`** (duplicate)
6. **Delete `core/bmi_extras_simple.py`** (consolidated)

---

## Implementation Steps

### Step 1: Add BMIProCard to canonical

```python
# In core/bmi_extras.py, add after imports:

@dataclass(frozen=True)
class BMIProCard:
    """RU: Расширенная карточка BMI (поясничные метрики и риск).
    EN: Extended BMI card with circumferences and risk staging.
    """
    bmi: float
    whtr: float
    whr: Optional[float]
    ffmi: Optional[float]
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]
```

### Step 2: Make whr_ratio backward-compatible

```python
# In core/bmi_extras.py, update whr_ratio signature:

def whr_ratio(
    waist_cm: float,
    hip_cm: float,
    sex: Optional[Literal["male", "female"]] = None
) -> float:
    """Calculate Waist-to-Hip Ratio (WHR).

    Args:
        waist_cm: Waist circumference in centimeters
        hip_cm: Hip circumference in centimeters
        sex: Optional biological sex ("male" or "female")
              If None, uses general thresholds

    Returns:
        WHR value (waist/hip ratio)
    """
    if waist_cm <= 0 or hip_cm <= 0:
        raise ValueError("waist_cm and hip_cm must be positive")
    return round(waist_cm / hip_cm, 2)
```

**Note:** If `sex` is None, use general thresholds (or keep existing logic if it handles None).

### Step 3: Update imports

**File: `app/routers/bmi_pro.py`**
```python
# BEFORE
from core.bmi_extras_simple import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio

# AFTER
from core.bmi_extras import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio
```

**Update whr_ratio call (line 51):**
```python
# BEFORE
v_whr = whr_ratio(req.waist_cm, float(req.hip_cm)) if req.hip_cm is not None else None

# AFTER (req.sex is available in BMIProRequest)
v_whr = whr_ratio(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None
```

**Note:** `req.sex` is available in `BMIProRequest`, so we can use the full signature.

**All test files:**
- `tests/test_bmi_extras_pro_coverage.py`: `from core.bmi_extras_pro import` → `from core.bmi_extras import`
- `tests/edges/test_more_edges.py`: `from core import bmi_extras_pro as pro` → `from core import bmi_extras as pro`
- `tests/test_bmi_extras_simple.py`: `from core import bmi_extras_simple as bx` → `from core import bmi_extras as bx`

### Step 4: Delete duplicate files

```bash
rm core/bmi_extras_pro.py
rm core/bmi_extras_simple.py
```

---

## Verification

After consolidation:

```bash
# All imports should use core.bmi_extras
grep -r "from core.bmi_extras" --include="*.py" | grep -v "bmi_extras_pro\|bmi_extras_simple"

# No references to old modules
grep -r "bmi_extras_pro\|bmi_extras_simple" --include="*.py" | grep -v "test\|audit\|\.md"

# Guard test should pass
pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v
```

---

## Alternative: Keep Simple as Alias (Not Recommended)

If backward compatibility is critical, could create thin alias:

```python
# core/bmi_extras_simple.py (thin alias, deprecated)
from core.bmi_extras import BMIProCard, ffmi, stage_obesity, wht_ratio
from core.bmi_extras import whr_ratio as _whr_ratio_full

def whr_ratio(waist_cm: float, hip_cm: float) -> float:
    """Simplified WHR (no sex parameter)"""
    return _whr_ratio_full(waist_cm, hip_cm, None)

__all__ = ["BMIProCard", "ffmi", "stage_obesity", "whr_ratio", "wht_ratio"]
```

**Not recommended:** Creates technical debt. Better to update `bmi_pro.py` to use full signature.

---

## Decision (Updated - Corrected Understanding)

**Canonical module:** `core/bmi_extras.py`

**Strategy:** One canonical module with **explicit Simple/Pro tier functions**:
- Pro tier: `wht_ratio()`, `whr_ratio(waist, hip, sex)`, `ffmi()`, `stage_obesity()`, `interpret_*()`
- Simple tier: `wht_ratio_simple()`, `whr_ratio_simple(waist, hip)`, `ffmi_simple()`, `stage_obesity_simple()`, `BMIProCard`

**Rationale:**
- Simple and Pro are **different product policies** (different rounding, thresholds, return formats)
- Not a 1:1 duplicate — they serve different tiers (Free vs Paid)
- Consolidating into one module with explicit naming prevents confusion
- Guard requires one canonical module — this satisfies the requirement

**Migration:**
- `app/routers/bmi_pro.py`: Use Pro tier functions (has `req.sex` available)
- Free endpoints: Use Simple tier functions
- Tests: Update imports and function names accordingly

---

**Last updated:** 2026-01-15
**Status:** Ready for consolidation
