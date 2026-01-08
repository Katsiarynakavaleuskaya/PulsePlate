# PR-490B: Final Notes & Follow-ups

## Follow-up: Type Alignment

**Fixed:** Aligned `BMICalculateResult.group` typing with `BMIGroup` (core source of truth); removed cast/ignore in visualization adapter.

This ensures type safety at the source rather than using workarounds in consuming code.

---

## CodeRabbit Responses

### Actionable: `group: BMIGroup` type fix

```text
✅ Fixed: updated `BMICalculateResult.group` type from `str` to `BMIGroup` to match `_auto_group()` return type and `get_bmi_visual_ranges()` signature; removed now-unnecessary cast/ignore at call site.
```

### Nitpicks: Core-internal tests location

```text
👍 Agree. These core-internal tests were temporarily colocated in `test_bmi_visualization_spec.py` for diff-cover visibility. After merge we'll move them into a dedicated core test file (e.g. `tests/test_bmi_engine.py`) in a small cleanup PR.
```

---

## PR-491 Plan: Test Reorganization

**Goal:** Move core BMI engine internal tests from `test_bmi_visualization_spec.py` to dedicated core test file.

**Important:** No behavior change; tests moved only. This improves test discoverability and separation of concerns.

### Scope

1. **Target file:** Add to `tests/test_bmi_engine_helpers.py` (existing file for core engine helpers) or create new section
2. **Move tests (from `test_bmi_visualization_spec.py` lines 397-469):**
   - `test_get_bmi_breakpoints_fallback_to_age_band_general()` (lines 397-421)
   - `test_get_bmi_breakpoints_final_fallback_to_adult_general()` (lines 423-449)
   - `test_upper_for_raises_when_missing_category()` (lines 451-469)
3. **Remove from:** `tests/test_bmi_visualization_spec.py` (delete lines 397-469)
4. **Update imports:** Ensure `core.bmi.engine` imports work correctly
5. **Verify:** Tests still pass, coverage maintained, diff-cover happy
6. **Document:** No changes needed to `tests/AGENTS.md` (diff-cover rule already present)

### Commit Message

```text
chore(tests): move core bmi breakpoint fallback tests into dedicated file

- Move _get_bmi_breakpoints fallback tests from test_bmi_visualization_spec.py
- Move _upper_for ValueError test to core test file
- No behavior change, only test organization
- Improves test discoverability and separation of concerns
```

### Files to Modify

- **Create/Update:** `tests/test_bmi_engine.py` (or appropriate existing file)
- **Remove from:** `tests/test_bmi_visualization_spec.py` (lines 397-469)
- **Update:** `tests/AGENTS.md` (if needed, to document the move)

### Test Structure (Suggested)

Add to `tests/test_bmi_engine_helpers.py` as a new class section:

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

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]
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

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]
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
            _upper_for(breakpoints, "normal")  # type: ignore[arg-type]
```

**Why this structure:**

- Groups related tests into logical classes
- Clear separation: fallback logic vs error handling
- Consistent with existing `test_bmi_engine_helpers.py` style
- Easy to discover and maintain

---

## Pre-Merge Checklist (PR-490B)

### Before Merge

1. **✅ Answer CodeRabbit** (2 copy-paste responses ready above)
   - Actionable: `group: BMIGroup` type fix
   - Nitpicks: Promise PR-491 for test reorganization

2. **✅ PR Description** (optional but recommended)

   Add to PR description or pinned comment:

   ```markdown
   ## Follow-up
   
   Follow-up: aligned `BMICalculateResult.group` typing with `BMIGroup` (core source of truth); removed cast/ignore in visualization adapter.
   ```

3. **✅ Verify All Checks Green**
   - PR checks: tests / lint / mypy / diff-cover / coverage
   - All green on **latest** commit SHA (not stale status)
   - Re-run CI if needed to ensure fresh status

4. **✅ Merge Strategy**
   - **Squash & merge** (if you prefer clean history)
   - **Rebase merge** (if you want to preserve commit history)
   - Avoid "Merge commit" if you keep history clean

### After Merge (PR-491)

- Follow PR-491 plan above
- Ensure `test_bmi_visualization_spec.py` diff shows deletion (lines 397-469)
- Verify diff-cover is happy with both file changes

---

## Status

- ✅ Type alignment complete
- ✅ CodeRabbit responses ready
- ✅ Pre-merge checklist ready
- ⏳ PR-491 planned (post-merge)
