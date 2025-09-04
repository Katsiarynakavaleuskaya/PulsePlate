"""
Compatibility package shim to expose the FastAPI `app` from the
top-level `app.py` module while preserving attribute access for tests
that patch functions like `app.make_weekly_menu`.
"""

from __future__ import annotations

import importlib.util
import sys as _sys
from pathlib import Path
from types import ModuleType

_ROOT_APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

_spec = importlib.util.spec_from_file_location("_app_top_module", _ROOT_APP_PATH)
_mod: ModuleType
if _spec and _spec.loader:  # pragma: no cover - defensive
    _mod = importlib.util.module_from_spec(_spec)
    # Ensure module is visible in sys.modules under its name before exec
    _sys.modules["_app_top_module"] = _mod
    _spec.loader.exec_module(_mod)
else:  # pragma: no cover
    raise ImportError("Failed to load top-level app.py module")

# Public FastAPI instance
app = getattr(_mod, "app", None)
if app is None:  # pragma: no cover
    raise AttributeError("Top-level app.py has no 'app' instance")


def __getattr__(name: str):  # pragma: no cover - passthrough
    return getattr(_mod, name)


__all__ = ["app"]

# Pre-expose commonly patched symbols so unittest.mock.patch finds them
for _name in (
    "make_weekly_menu",
    "make_daily_menu",
    "build_nutrition_targets",
    "analyze_nutrient_gaps",
    "make_plate",
    "get_api_key",
    "WHOTargetsRequest",
):
    try:  # pragma: no cover
        globals()[_name] = getattr(_mod, _name)
    except Exception:
        pass
