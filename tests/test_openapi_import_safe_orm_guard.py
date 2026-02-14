from __future__ import annotations

import importlib
import sys
from datetime import date
from typing import Any

import pytest
from module_purge import purge_modules


def _purge_nutrition_log_related_modules() -> None:
    # Use approved helper for sys.modules purge in tests.
    purge_modules(prefixes=("app.routers.nutrition_log",))


def test_nutrition_log_import_is_orm_import_safe() -> None:
    """Importing router module must not import ORM models eagerly."""
    _purge_nutrition_log_related_modules()
    had_models_before = "app.models" in sys.modules

    importlib.invalidate_caches()
    importlib.import_module("app.routers.nutrition_log")

    if not had_models_before:
        assert "app.models" not in sys.modules


def test_fetch_existing_event_uses_runtime_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    """The router must resolve NutritionEvent through the helper at runtime."""
    module = importlib.import_module("app.routers.nutrition_log")

    def _boom() -> Any:
        raise RuntimeError("helper-called")

    monkeypatch.setattr(module, "get_nutrition_event_model", _boom)

    session_dummy: Any = None
    with pytest.raises(RuntimeError, match="helper-called"):
        module._fetch_existing_event(session_dummy, 1, date.today(), "meal_log", "evt-1")
