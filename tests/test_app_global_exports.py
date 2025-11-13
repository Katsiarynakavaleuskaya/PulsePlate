"""Ensure module-level fallbacks in app.py execute for coverage."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def test_app_module_initializes_menu_engine_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load a fresh copy of app.py to exercise globals() fallback assignments."""
    app_path = Path(__file__).parent.parent / "app.py"
    module_name = "app_globals_reload"
    spec = importlib.util.spec_from_file_location(module_name, app_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # Minimize side effects during import
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "app_globals_reload::test")

    import core.db as core_db

    monkeypatch.setattr(core_db, "init_db", lambda: None, raising=False)

    spec.loader.exec_module(module)  # type: ignore[union-attr]

    try:
        assert hasattr(module, "analyze_nutrient_gaps")
        assert hasattr(module, "make_weekly_menu")
        assert hasattr(module, "repair_week_plan")
    finally:
        sys.modules.pop(module_name, None)
