# Backend P0 Remediation Plan

**Date:** 2026-01-15
**Priority:** P0 (Critical — Blocking)
**Source:** Root Cause Analysis (`ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md`)
**Purpose:** Restore architectural invariant "One BMI Engine"

---

## 🎯 Goal

**Restore architectural invariant:**
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**Success Criteria:**
- ✅ Only one calculation path exists
- ✅ All modules use canonical engine
- ✅ Result structure is always consistent
- ✅ Guard tests pass
- ✅ No legacy dependencies

---

## 📋 Remediation Actions

### Action 1: Remove Legacy Dependency (P0-Critical)

**Problem:** `core/bmi/risk.py` imports from legacy `bmi_core.py`

**Current State:**
```python
# core/bmi/risk.py:17
from bmi_core import compute_wht_ratio  # ❌ Legacy

# Used in:
# core/bmi/risk.py:151
wht_ratio = compute_wht_ratio(waist_cm, height_m)
```

**Target State:**
```python
# core/bmi/risk.py
from core.bmi.engine import _compute_wht_ratio  # ✅ Canonical

# Usage:
wht_ratio = _compute_wht_ratio(waist_cm, height_m)
```

**Steps:**

1. **Update import in `core/bmi/risk.py`:**
   - Remove: `from bmi_core import compute_wht_ratio`
   - Add: `from core.bmi.engine import _compute_wht_ratio`

2. **Update function call:**
   - Replace `compute_wht_ratio(waist_cm, height_m)` with `_compute_wht_ratio(waist_cm, height_m)`
   - Verify signature compatibility (both accept `waist_cm: float | None, height_m: float`)

3. **Verify behavior parity:**
   - Both return `float | None`
   - Both handle invalid inputs (return None)
   - Both use same rounding (2 decimals)

4. **Run tests:**
   ```bash
   pytest tests/test_bmi* -v
   pytest tests/test_core_bmi* -v
   ```

5. **Deprecate `bmi_core.py`:**
   - Add deprecation warning if still imported elsewhere
   - Document migration path
   - Plan removal in future PR

**Files to Modify:**
- `core/bmi/risk.py:17, 151`

**Verification:**
- ✅ No imports from `bmi_core` in `core/bmi/`
- ✅ All tests pass
- ✅ WHtR calculation uses canonical engine

**Estimated Time:** 1-2 hours

---

### Action 2: Consolidate BMI Extras Modules (P0-Critical)

**Problem:** Three duplicate modules with identical functions

**Current State:**
- `core/bmi_extras.py`
- `core/bmi_extras_pro.py`
- `core/bmi_extras_simple.py`

All contain:
- `wht_ratio()`
- `whr_ratio()`
- `ffmi()`
- `interpret_wht_ratio()`
- `interpret_whr_ratio()`
- `stage_obesity()`

**Target State:**
- Single canonical module: `core/bmi/extras.py`
- Or: Document purpose of each (if they serve different tiers)

**Steps:**

1. **Analyze usage:**
   ```bash
   # Find all imports
   grep -r "from core.bmi_extras" app/ core/ tests/
   grep -r "import.*bmi_extras" app/ core/ tests/
   ```

2. **Decision: Consolidate or Document?**
   - **If all serve same purpose:** Consolidate into `core/bmi/extras.py`
   - **If they serve different tiers:** Document purpose, keep but make canonical clear

3. **If consolidating:**
   - Create `core/bmi/extras.py` with canonical implementation
   - Update all imports to use canonical module
   - Remove duplicate modules
   - Update tests

4. **If documenting:**
   - Add clear docstrings explaining purpose of each
   - Ensure canonical module is clearly marked
   - Update imports to use canonical where possible

5. **Run tests:**
   ```bash
   pytest tests/test_bmi* -v
   ```

**Files to Modify:**
- `core/bmi_extras.py` (or consolidate)
- `core/bmi_extras_pro.py` (or consolidate)
- `core/bmi_extras_simple.py` (or consolidate)
- All files importing these modules

**Verification:**
- ✅ Only one canonical extras module (or clear purpose for each)
- ✅ All imports updated
- ✅ All tests pass

**Estimated Time:** 2-4 hours

---

### Action 3: Fix Metadata (P0-High)

**Problem:** `core/bmi/engine.py` marked as "stub" but is functionally complete

**Current State:**
```python
# core/bmi/engine.py:1-9
"""
This module will be fully implemented in PR-455.
Currently provides a stub implementation for development/testing.
"""
```

**Target State:**
- Remove "stub" comment if PR-455 is complete
- Or document what's missing if incomplete

**Steps:**

1. **Verify PR-455 status:**
   - Check if PR-455 is merged
   - Review what was planned vs what's implemented
   - Check git history / PR description

2. **If PR-455 complete:**
   - Remove "stub" comment
   - Update docstring to reflect canonical status
   - Add note: "Canonical BMI calculation engine"

3. **If PR-455 incomplete:**
   - Document what's missing
   - Create TODO with PR reference
   - Keep "stub" but clarify what's missing

4. **Update related documentation:**
   - Update `AGENTS.md` if needed
   - Update `core/AGENTS.md` if needed

**Files to Modify:**
- `core/bmi/engine.py:1-9`

**Verification:**
- ✅ Metadata accurately reflects implementation status
- ✅ No confusion about engine completeness

**Estimated Time:** 30 minutes

---

### Action 4: Add Guard Tests (P0-High)

**Problem:** No guard tests to prevent regression

**Target State:**
- Guard test: No imports from `bmi_core` in `core/bmi/`
- Guard test: Only one extras module (or clear purpose)
- Guard test: Result structure consistency

**Steps:**

1. **Create guard test: `tests/test_bmi_canonical_guard.py`:**
   ```python
   def test_no_legacy_bmi_imports_in_core_bmi():
       """Guard: core/bmi/ must not import from bmi_core."""
       # Check for imports
       pass

   def test_bmi_result_structure_consistency():
       """Guard: BMICalculateResult must always have all fields."""
       # Test result structure
       pass
   ```

2. **Add to CI:**
   - Run guard tests in CI
   - Fail on violation

3. **Document in `AGENTS.md`:**
   - Add guard test requirement
   - Document invariant

**Files to Create:**
- `tests/test_bmi_canonical_guard.py`

**Verification:**
- ✅ Guard tests pass
- ✅ CI enforces guards

**Estimated Time:** 1-2 hours

---

## 📊 Implementation Order

### Phase 1: Critical Path (Must Do First)

1. **Action 1: Remove Legacy Dependency** (1-2 hours)
   - **Blocking:** All other actions depend on this
   - **Risk:** Low (signature compatible)

2. **Action 3: Fix Metadata** (30 minutes)
   - **Blocking:** Prevents confusion
   - **Risk:** None

### Phase 2: Consolidation (After Phase 1)

3. **Action 2: Consolidate BMI Extras** (2-4 hours)
   - **Blocking:** Depends on Action 1
   - **Risk:** Medium (need to analyze usage)

### Phase 3: Prevention (After Phase 1-2)

4. **Action 4: Add Guard Tests** (1-2 hours)
   - **Blocking:** Prevents regression
   - **Risk:** Low

**Total Estimated Time:** 5-9 hours

---

## ✅ Verification Checklist

### After Action 1 (Legacy Dependency)

- [ ] `core/bmi/risk.py` uses `core.bmi.engine._compute_wht_ratio`
- [ ] No imports from `bmi_core` in `core/bmi/`
- [ ] All tests pass
- [ ] WHtR calculation works correctly

### After Action 2 (Extras Consolidation)

- [ ] Only one canonical extras module (or clear purpose)
- [ ] All imports updated
- [ ] All tests pass
- [ ] No duplicate function definitions

### After Action 3 (Metadata)

- [ ] Engine docstring accurately reflects status
- [ ] No "stub" confusion
- [ ] Documentation updated

### After Action 4 (Guard Tests)

- [ ] Guard tests pass
- [ ] CI enforces guards
- [ ] `AGENTS.md` documents invariant

### Final Verification

- [ ] Only one calculation path exists
- [ ] All modules use canonical engine
- [ ] Result structure is always consistent
- [ ] Guard tests pass
- [ ] No legacy dependencies

---

## 🎯 Success Criteria

**Backend is "deterministic single source of truth" when:**

1. ✅ **One calculation path:**
   - All BMI calculations use `core/bmi/engine`
   - No legacy imports in `core/bmi/`

2. ✅ **Consistent result structure:**
   - `BMICalculateResult` always fully populated
   - No conditional field gaps

3. ✅ **Guard tests enforce invariant:**
   - CI prevents regression
   - Tests fail on violation

4. ✅ **Metadata accurate:**
   - No confusion about engine status
   - Clear canonical path

---

## 📝 PR Strategy

### Option 1: Single PR (Recommended)

**PR Title:** `fix(backend): restore One BMI Engine invariant (P0)`

**Scope:**
- All 4 actions in one PR
- Complete remediation
- Guard tests included

**Pros:**
- Atomic fix
- Complete remediation
- Easier to review

**Cons:**
- Larger PR
- More risk if something breaks

---

### Option 2: Sequential PRs

**PR-1:** Remove legacy dependency
**PR-2:** Consolidate extras
**PR-3:** Fix metadata + guards

**Pros:**
- Smaller PRs
- Easier to review
- Lower risk

**Cons:**
- Multiple PRs
- Longer timeline
- Partial fixes between PRs

---

## 🚨 Risk Assessment

### Low Risk

- **Action 1 (Legacy Dependency):**
  - Signature compatible
  - Well-tested function
  - Low chance of breakage

- **Action 3 (Metadata):**
  - Documentation only
  - No code changes

### Medium Risk

- **Action 2 (Extras Consolidation):**
  - Need to analyze all usages
  - May have tier-specific logic
  - Requires careful migration

### Mitigation

- Run comprehensive tests after each action
- Verify behavior parity
- Use guard tests to prevent regression

---

## 📚 Related Documents

- `ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md` — Root cause analysis
- `DECISION_LOG_BMI_UNDEFINED.md` — Decision log
- `BACKEND_DUPLICATION_AUDIT.md` — Duplication details
- `BACKEND_BUSINESS_LOGIC_AUDIT.md` — Business logic verification

---

## 🎯 Next Steps After Remediation

1. **Backend Re-Validation:**
   - Run comprehensive tests
   - Verify result consistency
   - Check for any remaining legacy paths

2. **Frontend Audit (Only After Remediation):**
   - Diagnose with deterministic backend
   - Fix locale/units/errors
   - Verify no "undefined" in UI

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation
**Priority:** P0 (Critical — Blocking)
