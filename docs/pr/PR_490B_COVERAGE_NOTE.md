# PR-490B: Coverage Note

## Coverage Tail - Resolved

Initial diff-coverage showed 3 uncovered lines in `core/bmi/engine.py`:
- Lines 257-258: Fallback to `(age_band, "general")` branch in `_get_bmi_breakpoints()`
- Line 261: Final fallback to `("adult", "general")` branch
- Line 361: `ValueError` in `_upper_for()` when category is missing

**Status:** ✅ All lines now covered by `tests/test_bmi_engine_breakpoints_coverage_tail.py` using monkeypatch with synthetic age_band combinations to trigger defensive fallback branches.
