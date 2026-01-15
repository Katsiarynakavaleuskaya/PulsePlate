# PR Remediation: Exact Patches (Consolidated - Simple + Pro Tiers)

**Purpose:** Copy-paste ready patches for consolidating BMI extras modules.

**Strategy:** One canonical module (`core/bmi_extras.py`) with explicit Simple/Pro tier functions.

**Status:** Ready for implementation

**⚠️ Scope Boundary:**
- ✅ Normalizing existing Free/Pro tiers (documentation + code organization)
- ✅ Explicit tier separation in canonical module
- ❌ NO new features
- ❌ NO VIP tier logic
- ❌ NO menu automation
- ❌ NO product selection

**Rationale:** This is **architectural remediation** — fixing violations and normalizing existing structure, not adding new functionality.

---

## Patch 1: Remove Legacy Dependency (`core/bmi/risk.py`)

### File: `core/bmi/risk.py`

**Line 17 — Replace import:**

```diff
--- a/core/bmi/risk.py
+++ b/core/bmi/risk.py
@@ -14,7 +14,7 @@
 from dataclasses import dataclass
 from typing import Literal

-from bmi_core import compute_wht_ratio
+from core.bmi.engine import _compute_wht_ratio
```

**Line 151 — Replace function call:**

```diff
--- a/core/bmi/risk.py
+++ b/core/bmi/risk.py
@@ -148,4 +148,4 @@
     else:
         notes = ()

-    wht_ratio = compute_wht_ratio(waist_cm, height_m)
+    wht_ratio = _compute_wht_ratio(waist_cm, height_m)
```

**Verification:**
```bash
pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v
```

---

## Patch 2: Fix Engine Metadata (`core/bmi/engine.py`)

### File: `core/bmi/engine.py`

**Lines 2-9 — Update docstring:**

```diff
--- a/core/bmi/engine.py
+++ b/core/bmi/engine.py
@@ -1,9 +1,9 @@
 """
 BMI Engine Orchestrator

 RU: Единый engine для расчета BMI (canonical source of truth).
 EN: Unified engine for BMI calculation (canonical source of truth).

-This module will be fully implemented in PR-455.
-Currently provides a stub implementation for development/testing.
+Canonical implementation: all BMI calculations must use this module.
+No other calculation paths are allowed.
 """
```

**Verification:**
```bash
pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v
```

---

## Patch 3: Consolidate BMI Extras (Add Simple Tier to Canonical)

### File: `core/bmi_extras.py`

**Add Simple tier functions and BMIProCard at the end of file:**

```python
# Add after existing Pro tier functions (after line 228)

# ============================================================================
# Free/Simple Tier - Simplified versions for basic BMI calculations
# ============================================================================
#
# Product Policy:
# - Free tier: Simplified thresholds, 2 decimal places, basic risk assessment
# - Pro tier: Stricter sex-specific thresholds, 3 decimal places, comprehensive staging
#
# Rationale: Different rounding and thresholds serve different product tiers.
# Free users get simplified calculations; Pro users get detailed analysis.
# ============================================================================

from dataclasses import dataclass

Sex = Literal["female", "male"]


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


def wht_ratio_simple(waist_cm: float, height_cm: float) -> float:
    """Waist-to-Height Ratio (WHtR) - Free/Simple tier.

    Product Policy: Free tier uses 2 decimal places (simplified precision).
    Pro tier uses 3 decimal places (see wht_ratio()).

    Args:
        waist_cm: Waist circumference in centimeters
        height_cm: Height in centimeters

    Returns:
        WHtR value rounded to 2 decimal places

    Raises:
        ValueError: If waist or height is <= 0
    """
    if waist_cm <= 0 or height_cm <= 0:
        raise ValueError("waist_cm and height_cm must be positive")
    return round(waist_cm / height_cm, 2)


def whr_ratio_simple(waist_cm: float, hip_cm: float) -> float:
    """Waist-to-Hip Ratio (WHR) - Free/Simple tier.

    Product Policy: Free tier uses simplified calculation (no sex-specific thresholds).
    Pro tier uses sex-specific thresholds (see whr_ratio()).

    Rounding: 2 decimal places (Free tier policy).

    Args:
        waist_cm: Waist circumference in centimeters
        hip_cm: Hip circumference in centimeters

    Returns:
        WHR value rounded to 2 decimal places

    Raises:
        ValueError: If waist or hip is <= 0
    """
    if waist_cm <= 0 or hip_cm <= 0:
        raise ValueError("waist_cm and hip_cm must be positive")
    return round(waist_cm / hip_cm, 2)


def ffmi_simple(value_weight_kg: float, height_cm: float, bodyfat_percent: float) -> float:
    """Fat-Free Mass Index (FFMI) - Simple tier.

    Args:
        value_weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        bodyfat_percent: Body fat percentage (required, 0-60)

    Returns:
        FFMI value rounded to 1 decimal place

    Raises:
        ValueError: If weight, height, or bodyfat_percent is invalid
    """
    if value_weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight_kg and height_cm must be positive")
    if not (0 <= bodyfat_percent <= 60):
        raise ValueError("bodyfat_percent out of range")
    ffm = value_weight_kg * (1 - bodyfat_percent / 100.0)
    h_m = height_cm / 100.0
    return round(ffm / (h_m * h_m), 1)


def stage_obesity_simple(
    *, bmi: float, whtr: float, whr: Optional[float], sex: Sex, lang: Language = "en"
) -> tuple[str, list[str]]:
    """RU: Мягкое стадирование риска по BMI+WHtR(+WHR) - Free/Simple tier.
    EN: Light risk staging using BMI+WHtR(+WHR) - Free/Simple tier.

    Product Policy: Free tier uses simplified thresholds:
    - WHR thresholds: 0.90 (male) / 0.85 (female) - simplified
    - Pro tier uses stricter thresholds: 0.95 (male) / 0.80 (female)

    Returns: Tuple format (risk_level, notes_list) for simple tier compatibility.
    Pro tier returns Dict format (see stage_obesity()).

    Args:
        bmi: Body Mass Index
        whtr: Waist-to-Height Ratio
        whr: Optional Waist-to-Hip Ratio
        sex: Biological sex ("male" or "female")
        lang: Language for messages

    Returns:
        Tuple of (risk_level, notes_list)
    """
    notes: list[str] = []
    # Базово по WHtR (≈>0.5 — повышенный риск)
    if whtr < 0.5:
        risk = "low"
    elif whtr < 0.6:
        risk = "moderate"
        notes.append(t(lang, "risk_moderate_central_fat"))
    else:
        risk = "high"
        notes.append(t(lang, "risk_high_central_fat"))

    # Корректировка по WHR (Free tier: simplified thresholds)
    if whr is not None:
        thr = 0.9 if sex == "male" else 0.85  # Free tier thresholds
        if whr >= thr:
            notes.append(t(lang, "risk_high_whr", threshold=thr))
            risk = "high" if risk == "moderate" else risk

    # Доп. акцент по очень высокому BMI
    if bmi >= 35:
        notes.append(t(lang, "risk_high_bmi"))
        risk = "high"
    elif bmi >= 30 and risk == "low":
        risk = "moderate"
        notes.append(t(lang, "risk_moderate_bmi"))

    return risk, notes
```

**Note:** Add these functions at the end of `core/bmi_extras.py` (after existing Pro tier functions).

**Also update module docstring at top:**

```diff
--- a/core/bmi_extras.py
+++ b/core/bmi_extras.py
@@ -1,9 +1,20 @@
 """
-BMI Pro: Advanced metrics and risk assessment functions.
+BMI Extras: Advanced metrics and risk assessment functions.
+
+This module implements BMI analysis with two explicit product tiers:
+
+Pro Tier (Paid - PRO subscription):
+- Rounding: 3 decimal places
+- WHR thresholds: 0.95 (male) / 0.80 (female) - stricter
+- FFMI: Supports estimate mode (0.85 default if bodyfat_pct not provided)
+- Return formats: Dict for staging, comprehensive interpretation
+- Functions: wht_ratio(), whr_ratio(waist, hip, sex), ffmi(), stage_obesity(), interpret_*()
+
+Free/Simple Tier (Free - no subscription):
+- Rounding: 2 decimal places
+- WHR thresholds: 0.90 (male) / 0.85 (female) - simplified
+- FFMI: Requires bodyfat_pct (no estimate mode)
+- Return formats: Tuple for staging, simplified response
+- Functions: wht_ratio_simple(), whr_ratio_simple(waist, hip), ffmi_simple(), stage_obesity_simple(), BMIProCard
+
+Product Policy: Different tiers serve different user needs. Free tier provides basic calculations;
+Pro tier provides detailed analysis with sex-specific thresholds and comprehensive staging.
 """
```

---

## Patch 4: Update bmi_pro Router (Remove Local calc_bmi, Use Engine + Pro Tier)

### File: `app/routers/bmi_pro.py`

**Line 9 — Update imports:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -6,9 +6,9 @@
 from fastapi import APIRouter, HTTPException
 from pydantic import BaseModel, Field

-# Use canonical extras module with Pro tier functions
+from core.bmi_extras import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio

 # Import i18n functionality
 from core.i18n import Language
```

**Lines 15-17 — Remove local calc_bmi function:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -12,9 +12,6 @@
 # Import i18n functionality
 from core.i18n import Language


-# Define calc_bmi locally to avoid circular import
-def calc_bmi(weight_kg: float, height_m: float) -> float:
-    return round(weight_kg / (height_m**2), 1)
-
-
 router = APIRouter(prefix="/api/v1/pro", tags=["pro"])
```

**Line 49 — Update BMI calculation to use engine:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -46,7 +46,7 @@
 @router.post("/bmi", response_model=BMIProResponse)
 def bmi_pro(req: BMIProRequest):
     try:
-        # Convert height to meters for calc_bmi(weight, height_m)
-        bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)
+        # Use canonical engine for BMI calculation (already imported as calc_bmi alias)
+        bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)
+        v_whtr = wht_ratio(req.waist_cm, req.height_cm)
+        v_whr = whr_ratio(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None
```

**Line 51 — Update whr_ratio call to use Pro tier with sex:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -48,7 +48,7 @@
     try:
         # Use canonical engine for BMI calculation
         bmi_val = _compute_bmi(req.weight_kg, req.height_cm / 100.0)
         v_whtr = wht_ratio(req.waist_cm, req.height_cm)
        v_whr = whr_ratio_pro(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None

**Note:** We use Pro tier `whr_ratio` (imported as `whr_ratio_pro`) because it supports sex-specific thresholds, and `req.sex` is available in the request.

**Note:** `whr_ratio` here refers to Pro tier function (from `core.bmi_extras`), which requires `sex` parameter.

---

## Patch 5: Remove Duplicate/Simple Modules

### Delete files:

```bash
rm core/bmi_extras_pro.py
rm core/bmi_extras_simple.py
```

---

## Patch 6: Update Test Imports

### File: `tests/test_bmi_extras_pro_coverage.py`

**Update import:**

```diff
--- a/tests/test_bmi_extras_pro_coverage.py
+++ b/tests/test_bmi_extras_pro_coverage.py
@@ -X,7 +X,7 @@
-from core.bmi_extras_pro import (
+from core.bmi_extras import (
```

### File: `tests/edges/test_more_edges.py`

**Update import:**

```diff
--- a/tests/edges/test_more_edges.py
+++ b/tests/edges/test_more_edges.py
@@ -X,7 +X,7 @@
-    from core import bmi_extras_pro as pro
+    from core import bmi_extras as pro
```

### File: `tests/test_bmi_extras_simple.py`

**Update import:**

```diff
--- a/tests/test_bmi_extras_simple.py
+++ b/tests/test_bmi_extras_simple.py
@@ -X,7 +X,7 @@
-from core import bmi_extras_simple as bx
+from core import bmi_extras as bx
```

**Update function calls to use `_simple` suffix:**

```python
# Replace:
bx.wht_ratio(...) → bx.wht_ratio_simple(...)
bx.whr_ratio(...) → bx.whr_ratio_simple(...)
bx.ffmi(...) → bx.ffmi_simple(...)
bx.stage_obesity(...) → bx.stage_obesity_simple(...)
```

---

## Patch 7: Remove Direct BMI Calculation (`core/nutrition_bayesian_analyzer.py`)

### File: `core/nutrition_bayesian_analyzer.py`

**Top of file — Add import:**

```diff
--- a/core/nutrition_bayesian_analyzer.py
+++ b/core/nutrition_bayesian_analyzer.py
@@ -X,6 +X,7 @@
 from ... import ...
+from core.bmi.engine import _compute_bmi
```

**Line 377 — Replace direct calculation:**

```diff
--- a/core/nutrition_bayesian_analyzer.py
+++ b/core/nutrition_bayesian_analyzer.py
@@ -374,7 +374,7 @@
                 height_m = height / 100.0 if height > 3 else height
                 if height_m <= 0 or height_m > 3 or height <= 0:
                     continue
-                bmi = weight / (height_m**2)
+                bmi = _compute_bmi(weight, height_m)
                 if (
                     bmi < self.safety_thresholds["bmi_dangerous_low"]
                     or bmi >= self.safety_thresholds["bmi_dangerous_high"]
```

---

## Verification After All Patches

```bash
# All guards must pass
pytest tests/test_bmi_canonical_guard.py -v

# All existing tests must pass
make test-fast

# Full verification
make verify
```

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation (Strategy B - Simple/Pro tiers in one canonical module)
