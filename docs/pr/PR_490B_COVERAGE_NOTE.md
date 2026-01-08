# PR-490B: Coverage Note

## Coverage Tail - Resolved

Initial diff-coverage showed 3 uncovered lines in `core/bmi/engine.py`:
- Lines 257-258: Fallback to `(age_band, "general")` branch in `_get_bmi_breakpoints()`
- Line 261: Final fallback to `("adult", "general")` branch
- Line 361: `ValueError` in `_upper_for()` when category is missing

**Status:** ✅ All lines now covered by defensive fallback tests in `tests/test_bmi_visualization_spec.py`:
- `test_get_bmi_breakpoints_fallback_to_age_band_general()` - covers line 258
- `test_upper_for_raises_when_missing_category()` - covers line 361

Tests use monkeypatch with synthetic age_band combinations to trigger defensive fallback branches.
