# PR-490C Status

## Current Status: **NOT NEEDED** ✅

PR-490C was originally planned to cover defensive fallback branches in `_get_bmi_breakpoints()` that were showing as uncovered in diff-cover.

## What Happened

**PR-490B already covered these tests:**

The tests that were planned for PR-490C were **temporarily added to `test_bmi_visualization_spec.py`** during PR-490B to ensure diff-cover visibility:

- `test_get_bmi_breakpoints_fallback_to_age_band_general()` (covers line 258)
- `test_get_bmi_breakpoints_final_fallback_to_adult_general()` (covers line 261)
- `test_upper_for_raises_when_missing_category()` (covers line 361)

These tests are now in `tests/test_bmi_visualization_spec.py` (lines 397-469) and will be moved to their canonical location in **PR-491**.

## Conclusion

**PR-490C is not needed** — the coverage gap was closed in PR-490B, and PR-491 will move the tests to their proper location.

---

## Original Plan (for reference)

The original plan was:

- Branch: `test/pr-490c-breakpoints-fallback-coverage`
- Goal: Cover defensive fallback branches in `_get_bmi_breakpoints()`
- Tests: Same 3 tests that are now in PR-490B

Since PR-490B already includes these tests, PR-490C is redundant.

## Next Steps

- ✅ PR-490B: Merged (includes the tests)
- ⏳ PR-491: Move tests to canonical location (`test_bmi_engine_helpers.py`)
- ❌ PR-490C: Not needed
