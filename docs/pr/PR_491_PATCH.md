# PR-491: Test Reorganization Patch

## Summary

Pure test reorganization following PR-490B. No production code changes.

Move core BMI engine internal tests from `test_bmi_visualization_spec.py` to `test_bmi_engine_helpers.py` for better test discoverability and separation of concerns.

---

## Patch: Add to `tests/test_bmi_engine_helpers.py`

Add at the end of the file (after line 278):

```python
class TestBMIBreakpointsFallback:
    """
    RU: Тесты для fallback-логики _get_bmi_breakpoints (defensive branches).
    EN: Tests for _get_bmi_breakpoints fallback logic (defensive branches).

    These tests cover defensive fallback branches that ensure robustness
    when registry lookups fail (missing age_band/group combinations).
    """

    def test_fallback_to_age_band_general(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        RU: Покрывает ветку fallback (age_band, "general") в _get_bmi_breakpoints().
        EN: Covers (age_band, "general") fallback branch in _get_bmi_breakpoints().

        Test strategy:
        - Inject synthetic age_band "adult2" with only ("adult2", "general") in registry
        - Request ("adult2", "athlete") which doesn't exist
        - Should fallback to ("adult2", "general") → covers line 258
        """
        from typing import Any

        import core.bmi.engine as eng

        # Copy current registry and inject a synthetic age_band
        patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]

        # Provide only (adult2, general), but request (adult2, athlete)
        patched[("adult2", "general")] = patched[("adult", "general")]
        monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
        assert bp == patched[("adult", "general")]
        assert len(bp) == 6

    def test_final_fallback_to_adult_general(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        RU: Покрывает финальный fallback ("adult","general") в _get_bmi_breakpoints().
        EN: Covers final ("adult","general") fallback branch in _get_bmi_breakpoints().

        Test strategy:
        - Use synthetic age_band "adult2" with NO entries in registry
        - Request ("adult2", "athlete") which doesn't exist
        - Should fallback to ("adult2", "general") which also doesn't exist
        - Should use final fallback ("adult", "general") → covers line 261
        """
        from typing import Any

        import core.bmi.engine as eng

        # Copy registry, but DO NOT define (adult2, general)
        patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]
        monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
        assert bp == patched[("adult", "general")]
        assert len(bp) == 6
        # Verify it's actually adult/general thresholds (25.0 normal_max)
        assert bp[1][0] == 25.0  # adult normal_max


class TestBMIUpperFor:
    """
    RU: Тесты для _upper_for() (извлечение верхних границ из breakpoints).
    EN: Tests for _upper_for() (extracting upper bounds from breakpoints).
    """

    def test_raises_when_missing_category(self) -> None:
        """
        RU: Покрывает raise ValueError в _upper_for() когда категория отсутствует.
        EN: Covers raise ValueError in _upper_for() when category is missing.

        Test strategy:
        - Provide breakpoints without "normal" category
        - Request "normal" → should raise ValueError → covers line 361
        """
        from core.bmi.engine import _upper_for

        breakpoints = [
            (18.5, "underweight"),
            (25.0, "overweight"),  # intentionally missing "normal"
            (float("inf"), "obesity_3"),
        ]
        with pytest.raises(ValueError, match="Missing breakpoint"):
            _upper_for(breakpoints, "normal")  # type: ignore[arg-type]  # Intentionally missing category for test
```

---

## Patch: Remove from `tests/test_bmi_visualization_spec.py`

Delete lines 397-469 (entire section):

```python
# DELETE THESE LINES (397-469):
def test_get_bmi_breakpoints_fallback_to_age_band_general(monkeypatch: pytest.MonkeyPatch) -> None:
    ...

def test_get_bmi_breakpoints_final_fallback_to_adult_general(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ...

def test_upper_for_raises_when_missing_category() -> None:
    ...
```

---

## Verification Steps

1. Run tests:
   ```bash
   pytest tests/test_bmi_engine_helpers.py::TestBMIBreakpointsFallback -v
   pytest tests/test_bmi_engine_helpers.py::TestBMIUpperFor -v
   ```

2. Verify deletion:
   ```bash
   git diff tests/test_bmi_visualization_spec.py | grep -E "^\-.*def test.*breakpoint|^\-.*def test.*upper_for"
   ```

3. Full test suite:
   ```bash
   pytest -q
   ```

4. Coverage check:
   ```bash
   pytest --cov=core/bmi/engine --cov-report=term-missing tests/test_bmi_engine_helpers.py
   ```

---

## Expected Diff Stats

- `tests/test_bmi_engine_helpers.py`: +73 lines (2 new test classes)
- `tests/test_bmi_visualization_spec.py`: -73 lines (removed core-internal tests)
- Net change: 0 lines (pure reorganization)

