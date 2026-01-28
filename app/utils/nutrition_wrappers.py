"""Nutrition calculation wrappers extracted from legacy_app.py.

These wrappers provide dynamic resolution of BMR/TDEE calculation functions
to support mocking in tests. They do not contain business logic, only
resolution and delegation.
"""

from __future__ import annotations

from typing import Dict, Union, cast


def _calculate_all_bmr_wrapper(
    weight_kg: float, height_cm: float, age: int, sex: str, bodyfat: float | None = None
) -> dict[str, float]:
    """Wrapper for calculate_all_bmr to support mocking in tests"""
    import sys as _sys

    pkg = _sys.modules.get("app")
    alias = _sys.modules.get("app_module")
    pkg_appmod = getattr(pkg, "app_module", None) if pkg else None

    calc_bmr = None
    if pkg is not None:
        calc_bmr = getattr(pkg, "calculate_all_bmr", None)
    if calc_bmr is None and pkg_appmod is not None:
        calc_bmr = getattr(pkg_appmod, "calculate_all_bmr", None)
    if calc_bmr is None and alias is not None:
        calc_bmr = getattr(alias, "calculate_all_bmr", None)
    if calc_bmr is None:
        # Fallback: try to import from nutrition_core directly
        # This preserves original behavior where calculate_all_bmr was available in legacy_app globals
        try:
            from nutrition_core import calculate_all_bmr as calc_bmr
        except ImportError:
            calc_bmr = None
    if calc_bmr is None:
        raise ImportError("nutrition_core module not available")
    result = calc_bmr(weight_kg, height_cm, age, sex, bodyfat)
    return cast(Dict[str, float], result)


def _calculate_all_tdee_wrapper(
    bmr_results: dict[str, float], activity: str
) -> dict[str, int | float]:
    """Wrapper for calculate_all_tdee to support mocking in tests"""
    import sys as _sys

    pkg = _sys.modules.get("app")
    alias = _sys.modules.get("app_module")
    pkg_appmod = getattr(pkg, "app_module", None) if pkg else None

    calc_tdee = None
    if pkg is not None:
        calc_tdee = getattr(pkg, "calculate_all_tdee", None)
    if calc_tdee is None and pkg_appmod is not None:
        calc_tdee = getattr(pkg_appmod, "calculate_all_tdee", None)
    if calc_tdee is None and alias is not None:
        calc_tdee = getattr(alias, "calculate_all_tdee", None)
    if calc_tdee is None:
        # Fallback: try to import from nutrition_core directly
        # This preserves original behavior where calculate_all_tdee was available in legacy_app globals
        try:
            from nutrition_core import calculate_all_tdee as calc_tdee
        except ImportError:
            calc_tdee = None
    if calc_tdee is None:
        raise ImportError("nutrition_core module not available")
    result = calc_tdee(bmr_results, activity)
    return cast(Dict[str, Union[int, float]], result)
