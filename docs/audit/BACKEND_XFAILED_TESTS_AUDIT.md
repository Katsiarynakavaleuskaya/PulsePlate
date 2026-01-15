# Backend xfailed Tests Audit

**Date:** 2026-01-15
**Scope:** All tests marked as `@pytest.mark.xfail` or `skip`
**Purpose:** Identify known test failures and their root causes

---

## 📊 Summary

**Total xfailed tests:** 2
**Total skipped tests:** Multiple (conditional skips for optional modules)

---

## 🔴 xfailed Tests (Known Failures)

### 1. `test_no_calculate_all_bmr` (test_app_branching_and_errors.py:185)

**Status:** `@pytest.mark.xfail(strict=True)`

**Reason:**
```
calculate_all_bmr may not be None after reload; patching not supported in this environment.
TODO: Fix module reload/patching or use dependency override
```

**Root Cause:**
- Test tries to simulate `ImportError` by removing modules from `sys.modules`
- Module reload (`importlib.reload`) doesn't work as expected in test environment
- `calculate_all_bmr` remains defined after reload (should be `None`)

**Impact:** Medium
- Tests import error handling fallback paths
- Not blocking production (handles real ImportError correctly)

**Recommendation:**
- Use dependency override instead of `sys.modules` manipulation
- Or mark as skip if test isolation is not achievable

**File:** `tests/test_app_branching_and_errors.py:185-211`

---

### 2. `test_bmi_visualization_endpoint_with_api_key` (test_bmi_visualization.py:523)

**Status:** `@pytest.mark.xfail(strict=True)`

**Reason:**
```
Test isolation issue in full suite - passes individually.
TODO: Fix test isolation or use dependency override for API key
```

**Root Cause:**
- Test isolation problem when running full test suite
- Passes when run individually
- Likely due to shared state (API key, module-level mocks)

**Impact:** Low
- Visualization endpoint works in production
- Only affects test suite execution

**Recommendation:**
- Use dependency override for API key instead of module-level patching
- Ensure proper test isolation (fixtures, cleanup)

**File:** `tests/test_bmi_visualization.py:523-560`

---

## ⚠️ Skipped Tests (Conditional)

### 1. `test_no_sys_modules_mutation_in_repo` (test_repo_policy_guards.py:85)

**Status:** `@pytest.mark.skip`

**Reason:**
```
TODO: Many legacy tests use sys.modules - cleanup in follow-up PR
```

**Impact:** High (policy enforcement)
- This test enforces "no sys.modules mutation" rule
- Currently skipped because legacy tests violate this rule

**Recommendation:**
- Clean up legacy tests that mutate `sys.modules`
- Re-enable test after cleanup

**File:** `tests/test_repo_policy_guards.py:85-117`

---

### 2. Zero Coverage Modules Tests

**Status:** Conditional skip (`pytest.skip` or `pytest.importorskip`)

**Modules tested:**
- `core.sports_nutrition`
- `core.exports`
- Various optional modules

**Reason:**
- Modules may not be available in all environments
- Some modules are optional dependencies

**Impact:** Low (expected behavior)

**File:** `tests/test_zero_coverage_modules.py`

---

### 3. Optional Module Tests

**Status:** Conditional skip (`pytest.importorskip`)

**Pattern:**
```python
module = pytest.importorskip("core.module_name")
```

**Common skipped modules:**
- `core.exports_simple`
- `core.food_apis.unified_db`
- `core.menu_engine`
- `core.plate`
- `core.recommendations`
- `core.product_finder`
- `core.recipe_synth`
- `core.targets`
- `core.time_utils`
- `core.region_catalog`
- `core.rag.simple_rag`
- `core.recipe_db`
- `core.recipe_db_new`
- `core.food_db`
- `core.food_merge`
- `core.menu_engine_new`
- `core.product_varieties`
- `core.rules_who`

**Impact:** Low (expected for optional modules)

**Files:** Multiple test files use `pytest.importorskip`

---

## 📋 Action Items

### P0 (Fix Known Failures)

1. **Fix `test_no_calculate_all_bmr`**
   - Replace `sys.modules` manipulation with dependency override
   - Or document why test cannot be fixed and mark as skip

2. **Fix `test_bmi_visualization_endpoint_with_api_key`**
   - Improve test isolation
   - Use dependency override for API key

### P1 (Re-enable Policy Tests)

3. **Re-enable `test_no_sys_modules_mutation_in_repo`**
   - Clean up legacy tests that mutate `sys.modules`
   - Create follow-up PR for cleanup

---

## 🔍 Verification

**List all xfailed tests:**
```bash
pytest --collect-only -q | grep -E "xfail|XFAIL"
```

**Run xfailed tests:**
```bash
pytest -v --runxfail tests/test_app_branching_and_errors.py::test_no_calculate_all_bmr
pytest -v --runxfail tests/test_bmi_visualization.py::test_bmi_visualization_endpoint_with_api_key
```

---

**Last updated:** 2026-01-15
