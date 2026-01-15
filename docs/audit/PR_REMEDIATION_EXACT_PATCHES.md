# PR Remediation: Exact Code Patches

**Purpose:** Copy-paste ready patches for Backend P0 Remediation PR.

**Status:** Ready for implementation
**Depends on:** Guard Policy PR #534 (must be merged or in Draft)

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

**Verification:** After both changes (import + call), ensure no other references to `compute_wht_ratio` remain:
```bash
grep -n "compute_wht_ratio" core/bmi/risk.py
# Should return nothing (or only comments/docstrings)
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

## Patch 3: Remove Local BMI Calculation (`app/routers/bmi_pro.py`)

### File: `app/routers/bmi_pro.py`

**Line 9 — Update imports:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -6,9 +6,9 @@
 from fastapi import APIRouter, HTTPException
 from pydantic import BaseModel, Field

 # Use the simplified extras module that matches the function signatures used here
 from core.bmi_extras_simple import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio
+from core.bmi.engine import _compute_bmi

 # Import i18n functionality
 from core.i18n import Language
```

**Lines 15-17 — Remove local function:**

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
 router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])
```

**Line 49 — Update function call:**

```diff
--- a/app/routers/bmi_pro.py
+++ b/app/routers/bmi_pro.py
@@ -46,7 +46,7 @@
 def bmi_pro(req: BMIProRequest):
     try:
         # Convert height to meters for calc_bmi(weight, height_m)
-        bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)
+        bmi_val = _compute_bmi(req.weight_kg, req.height_cm / 100.0)
```

**Verification:**
```bash
pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v
```

---

## Patch 4: Remove Direct BMI Calculation (`core/nutrition_bayesian_analyzer.py`)

### File: `core/nutrition_bayesian_analyzer.py`

**Top of file — Add import:**

Find the imports section (around line 1-30) and add:

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

**Verification:**
```bash
pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v
```

---

## Patch 5: Consolidate BMI Extras Modules

### Files: `core/bmi_extras.py`, `core/bmi_extras_pro.py`, `core/bmi_extras_simple.py`

**Decision:** Consolidate into `core/bmi/extras.py` (move to `core/bmi/` subdirectory for consistency).

**Steps:**

1. **Analyze current usage:**
   ```bash
   grep -r "from core.bmi_extras" --include="*.py"
   grep -r "import.*bmi_extras" --include="*.py"
   ```

2. **Create canonical module:**
   - Create `core/bmi/extras.py`
   - Copy/merge all functions from the 3 existing files
   - Ensure function signatures match exactly

3. **Update all imports:**
   ```bash
   # Find all files importing bmi_extras
   grep -r "from core.bmi_extras" --include="*.py" -l
   ```

   For each file, replace:
   ```diff
   -from core.bmi_extras_simple import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio
   +from core.bmi.extras import BMIProCard, ffmi, stage_obesity, whr_ratio, wht_ratio
   ```

4. **Delete duplicate modules:**
   ```bash
   rm core/bmi_extras.py
   rm core/bmi_extras_pro.py
   rm core/bmi_extras_simple.py
   ```

**Verification:**
```bash
pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v
```

---

## Final Verification

After all patches:

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
**Status:** Ready for implementation
