"""Nutrition calculation wrappers extracted from legacy_app.py.

These wrappers provide dynamic resolution of BMR/TDEE calculation functions
to support mocking in tests. They do not contain business logic, only
resolution and delegation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Union, cast


def _import_nutrition_core_bmr() -> Callable[..., Any] | None:
    """
    Import seam for tests. Never patch sys.modules; patch this function instead.
    Returns calculate_all_bmr callable or None if unavailable.
    """
    try:
        from nutrition_core import calculate_all_bmr  # type: ignore[import-untyped]

        return cast(Callable[..., Any], calculate_all_bmr)
    except Exception:  # noqa: BLE001
        return None


def _import_nutrition_core_tdee() -> Callable[..., Any] | None:
    """
    Import seam for tests. Never patch sys.modules; patch this function instead.
    Returns calculate_all_tdee callable or None if unavailable.
    """
    try:
        from nutrition_core import calculate_all_tdee  # type: ignore[import-untyped]

        return cast(Callable[..., Any], calculate_all_tdee)
    except Exception:  # noqa: BLE001
        return None


def _resolve_nutrition_callable(name: str) -> Callable[..., Any]:
    """Resolve nutrition calculation callable from module hierarchy.

    Resolution order:
    1. app.app_module.<name> (if present)
    2. app.<name>
    3. app_module.<name>
    4. nutrition_core.<name> (fallback)

    Args:
        name: Name of the callable to resolve ("calculate_all_bmr" or "calculate_all_tdee")

    Returns:
        Resolved callable function

    Raises:
        ImportError: If callable cannot be resolved from any source
    """
    import sys as _sys

    pkg = _sys.modules.get("app")
    alias = _sys.modules.get("app_module")
    pkg_appmod = getattr(pkg, "app_module", None) if pkg else None

    # Try resolution order: app.app_module -> app -> app_module -> nutrition_core
    calc_fn = None
    if pkg_appmod is not None:
        calc_fn = getattr(pkg_appmod, name, None)
    if calc_fn is None and pkg is not None:
        calc_fn = getattr(pkg, name, None)
    if calc_fn is None and alias is not None:
        calc_fn = getattr(alias, name, None)
    if calc_fn is None:
        # Fallback: try to import from nutrition_core using import seams
        # This preserves original behavior where functions were available in legacy_app globals
        if name == "calculate_all_bmr":
            calc_fn = _import_nutrition_core_bmr()
        elif name == "calculate_all_tdee":
            calc_fn = _import_nutrition_core_tdee()
        else:
            raise ImportError(f"unknown nutrition callable '{name}'")

    if calc_fn is None:
        raise ImportError(f"nutrition callable '{name}' not available (nutrition_core missing)")
    return calc_fn


def _calculate_all_bmr_wrapper(
    weight_kg: float, height_cm: float, age: int, sex: str, bodyfat: float | None = None
) -> dict[str, float]:
    """Wrapper for calculate_all_bmr to support mocking in tests"""
    calc_bmr = _resolve_nutrition_callable("calculate_all_bmr")
    result = calc_bmr(weight_kg, height_cm, age, sex, bodyfat)
    return cast(Dict[str, float], result)


def _calculate_all_tdee_wrapper(
    bmr_results: dict[str, float], activity: str
) -> dict[str, int | float]:
    """Wrapper for calculate_all_tdee to support mocking in tests"""
    calc_tdee = _resolve_nutrition_callable("calculate_all_tdee")
    result = calc_tdee(bmr_results, activity)
    return cast(Dict[str, Union[int, float]], result)
