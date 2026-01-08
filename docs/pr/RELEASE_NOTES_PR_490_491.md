# Release Notes: PR-490B & PR-491

## PR-490B: BMI Visualization Group-Aware

**Type:** Feature  
**Status:** ✅ Merged

### Summary

Made BMI visualization group-aware by deriving ranges from core BMI thresholds instead of hardcoded WHO adult ranges.

### Changes

- **Core (`core/bmi/engine.py`):**
  - Centralized BMI category thresholds in `_BMI_BREAKPOINTS` registry
  - Added `get_bmi_visual_ranges()` function to derive visualization ranges from thresholds
  - Refactored `_bmi_category()` to use centralized breakpoints
  - Returns `None` for groups with `category=None` (too_young, child, teen, pregnant)

- **Service (`app/services/bmi_visualization.py`):**
  - `build_bmi_scale_v1()` now accepts `BMICalculateResult` and uses core thresholds
  - Returns `None` for groups where visualization shouldn't be shown
  - Removed hardcoded WHO adult ranges

- **API (`app/routers/bmi.py`):**
  - Passes full `BMICalculateResult` to visualization builder
  - Maintains graceful fallback (visualization: null on builder failure)

- **Type Safety:**
  - Fixed `BMICalculateResult.group` type from `str` to `BMIGroup` (core source of truth)
  - Removed unnecessary `cast`/`type: ignore` in visualization adapter

### Impact

- ✅ Visualization ranges now match core BMI category thresholds per group
- ✅ Athlete group: normal range extends to 27.0 (was 25.0)
- ✅ Elderly group: underweight threshold 17.5, normal extends to 26.0 (was 18.5/25.0)
- ✅ Groups with `category=None` correctly return `visualization: null` (not misleading adult ranges)
- ✅ Better type safety and maintainability

### Related

- Addresses CodeRabbit feedback about group-specific ranges
- Follow-up to PR-490A (BMI visualization spec v1)

---

## PR-491: Test Reorganization

**Type:** Chore (Test-only)  
**Status:** ⏳ Pending merge

### Summary

Pure test reorganization: moved core BMI engine internal tests from visualization spec file to engine helpers file.

### Changes

- **Moved from `tests/test_bmi_visualization_spec.py`:**
  - `TestBMIBreakpointsFallback` (2 tests: fallback branches in `_get_bmi_breakpoints()`)
  - `TestBMIUpperFor` (1 test: ValueError path in `_upper_for()`)

- **Added to `tests/test_bmi_engine_helpers.py`:**
  - Same 3 tests, now in canonical location with other core engine tests

### Impact

- ✅ Better test discoverability (core tests with core tests)
- ✅ Improved separation of concerns (visualization tests focus on visualization)
- ✅ Easier maintenance (related tests grouped logically)
- ✅ No behavior changes (same tests, different location)

### Related

- Follow-up to PR-490B (where tests were temporarily colocated for diff-cover visibility)
- Addresses CodeRabbit nitpick about test location

---

## Changelog Entry (Combined)

```markdown
### Changed
- BMI visualization now uses group-specific thresholds (athlete, elderly) instead of fixed WHO adult ranges
- Groups with `category=None` (child, teen, pregnant, too_young) correctly return `visualization: null`

### Fixed
- Type safety: `BMICalculateResult.group` now correctly typed as `BMIGroup` instead of `str`

### Internal
- Test reorganization: core BMI engine internal tests moved to canonical location
- Centralized BMI category thresholds in core engine for single source of truth
```

---

## Handoff Notes

### For Next PRs

1. **BMI visualization ranges** now come from `core.bmi.engine.get_bmi_visual_ranges()`
2. **Core thresholds** live in `core/bmi/engine.py` → `_BMI_BREAKPOINTS` registry
3. **Test organization**: core engine tests → `test_bmi_engine_helpers.py`, visualization tests → `test_bmi_visualization_spec.py`

### Future Improvements

- Consider adding visualization ranges for obesity_1/2/3 categories (currently aggregated as "obesity")
- Potential i18n improvements for group-specific visualization labels

