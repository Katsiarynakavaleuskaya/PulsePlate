"""Nutrition calculation wrappers extracted from legacy_app.py.

These wrappers provide dynamic resolution of BMR/TDEE calculation functions
to support mocking in tests. They do not contain business logic, only
resolution and delegation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Union, cast


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
        # Fallback: try to import from nutrition_core directly
        # This preserves original behavior where functions were available in legacy_app globals
        try:
            if name == "calculate_all_bmr":
                from nutrition_core import calculate_all_bmr as calc_fn  # type: ignore[assignment]
            elif name == "calculate_all_tdee":
                from nutrition_core import calculate_all_tdee as calc_fn  # type: ignore[assignment]
            else:
                raise ImportError(f"unknown nutrition callable '{name}'")
        except ImportError as e:
            raise ImportError(f"cannot import '{name}' (nutrition_core missing)") from e

    if calc_fn is None:
        raise ImportError(f"nutrition callable '{name}' not available")
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
