"""Nutrition calculation wrappers extracted from legacy_app.py.

These wrappers provide dynamic resolution of BMR/TDEE calculation functions
to support mocking in tests. They do not contain business logic, only
resolution and delegation.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any, cast


def _import_nutrition_core_bmr() -> Callable[..., Any] | None:
    """Import seam for tests. Patch this function; do not touch sys.modules.

    Returns calculate_all_bmr callable or None if unavailable.
    """
    try:
        mod = importlib.import_module("nutrition_core")
    except ImportError:
        return None

    calc = getattr(mod, "calculate_all_bmr", None)
    return cast(Callable[..., Any], calc) if callable(calc) else None


def _import_nutrition_core_tdee() -> Callable[..., Any] | None:
    """Import seam for tests. Patch this function; do not touch sys.modules.

    Returns calculate_all_tdee callable or None if unavailable.
    """
    try:
        mod = importlib.import_module("nutrition_core")
    except ImportError:
        return None

    calc = getattr(mod, "calculate_all_tdee", None)
    return cast(Callable[..., Any], calc) if callable(calc) else None


def _resolve_nutrition_callable(name: str) -> Callable[..., Any]:
    """Resolve nutrition calculation callable from module hierarchy.

    Resolution order (legacy parity):
    1. app.<name>
    2. app.app_module.<name> (if present)
    3. sys.modules["app_module"].<name> (if present)
    4. nutrition_core.<name> via import seams (fallback)

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

    # Resolution order: app -> app.app_module -> app_module -> nutrition_core
    calc_fn = None
    if pkg is not None:
        calc_fn = getattr(pkg, name, None)

    if calc_fn is None and pkg_appmod is not None:
        calc_fn = getattr(pkg_appmod, name, None)

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
    return cast(dict[str, float], result)


def _calculate_all_tdee_wrapper(
    bmr_results: dict[str, float], activity: str
) -> dict[str, int | float]:
    """Wrapper for calculate_all_tdee to support mocking in tests"""
    calc_tdee = _resolve_nutrition_callable("calculate_all_tdee")
    result = calc_tdee(bmr_results, activity)
    return cast(dict[str, int | float], result)
