from __future__ import annotations

import importlib
import sys
from datetime import date
from typing import Any

import pytest


def _purge_nutrition_log_related_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if (
            name == "app.routers.nutrition_log"
            or name == "app.models"
            or name.startswith("app.models.")
        ):
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_nutrition_log_import_is_orm_import_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing router module must not import ORM models eagerly."""
    _purge_nutrition_log_related_modules(monkeypatch)

    importlib.invalidate_caches()
    importlib.import_module("app.routers.nutrition_log")

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
