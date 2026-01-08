# PR-491: Test Reorganization — Move Core BMI Engine Tests

## Summary

Pure test reorganization following PR-490B. No production code changes.

Move core BMI engine internal tests from `test_bmi_visualization_spec.py` to `test_bmi_engine_helpers.py` for better test discoverability and separation of concerns.

---

## What Changed

### Added to `tests/test_bmi_engine_helpers.py`

- `TestBMIBreakpointsFallback` class:
  - `test_fallback_to_age_band_general()` — covers (age_band, "general") fallback
  - `test_final_fallback_to_adult_general()` — covers final ("adult", "general") fallback
- `TestBMIUpperFor` class:
  - `test_raises_when_missing_category()` — covers ValueError path in `_upper_for()`

### Removed from `tests/test_bmi_visualization_spec.py`

- Lines 397-469: Three core-internal tests that were temporarily colocated for diff-cover visibility in PR-490B

---

## Why This Change

1. **Test discoverability**: Core engine tests belong with other core engine tests
2. **Separation of concerns**: Visualization spec tests should focus on visualization, not core internals
3. **Maintainability**: Easier to find and maintain related tests when grouped logically
4. **Follow-up to PR-490B**: These tests were temporarily placed in `test_bmi_visualization_spec.py` to ensure diff-cover visibility; now moving them to their canonical location

---

## Non-Goals

- ❌ No production code changes
- ❌ No test logic changes
- ❌ No coverage changes (same tests, different location)

---

## Verification

- ✅ All tests pass
- ✅ Coverage maintained (same lines covered)
- ✅ Diff-cover happy (both files modified in PR)
- ✅ No behavior changes

---

## Related

- Follow-up to PR-490B (where these tests were temporarily added)
- Addresses CodeRabbit nitpick about test location

---

## Commit Message

```
chore(tests): move core bmi breakpoint fallback tests into dedicated file

- Move _get_bmi_breakpoints fallback tests from test_bmi_visualization_spec.py
- Move _upper_for ValueError test to core test file
- No behavior change, only test organization
- Improves test discoverability and separation of concerns

Follow-up to PR-490B where these tests were temporarily colocated
for diff-cover visibility.
```
