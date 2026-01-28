import sys
from unittest.mock import patch

import pytest

import app
from app.utils import nutrition_wrappers as nw


def test_background_updates_wrappers_force_sync_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover start/stop background update wrappers in pytest force-sync mode."""

    called: list[str | int] = []

    async def fake_start(update_interval_hours: int = 24) -> None:
        called.append(update_interval_hours)

    async def fake_stop() -> None:
        called.append("stop")

    # Instead of patching global asyncio.get_running_loop, we'll simulate the condition
    # by temporarily setting an environment variable that forces sync mode
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
        # Use monkeypatch to safely set and automatically restore the functions
        monkeypatch.setitem(app.__dict__, "_scheduler_start_background_updates", fake_start)
        monkeypatch.setitem(app.__dict__, "_scheduler_stop_background_updates", fake_stop)

        app.start_background_updates(update_interval_hours=12)
        app.stop_background_updates()

    assert 12 in called
    assert "stop" in called


def test_calculate_wrappers_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure wrappers raise ImportError when their dependencies are missing."""

    # Create a mock module that raises ImportError when trying to import calculate_all_bmr
    class MockModule:
        def __getattr__(self, name: str) -> None:
            raise ImportError(f"cannot import name '{name}' from 'nutrition_core'")

    # Null out all visible locations so wrappers raise ImportError deterministically
    for module in (
        app,
        getattr(app, "app_module", None),
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_bmr", None, raising=False)
    monkeypatch.setitem(nw._calculate_all_bmr_wrapper.__globals__, "calculate_all_bmr", None)
    # Block nutrition_core import (wrapper's fallback) by replacing it with mock that raises ImportError
    original_nutrition_core = sys.modules.get("nutrition_core")
    monkeypatch.setitem(sys.modules, "nutrition_core", MockModule())
    try:
        with pytest.raises(ImportError):
            nw._calculate_all_bmr_wrapper(70, 175, 30, "male")
    finally:
        if original_nutrition_core is not None:
            monkeypatch.setitem(sys.modules, "nutrition_core", original_nutrition_core)
        else:
            monkeypatch.delitem(sys.modules, "nutrition_core", raising=False)

    for module in (
        app,
        getattr(app, "app_module", None),
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_tdee", None, raising=False)
    monkeypatch.setitem(nw._calculate_all_tdee_wrapper.__globals__, "calculate_all_tdee", None)
    # Block nutrition_core import (wrapper's fallback) by replacing it with mock that raises ImportError
    original_nutrition_core = sys.modules.get("nutrition_core")
    monkeypatch.setitem(sys.modules, "nutrition_core", MockModule())
    try:
        with pytest.raises(ImportError):
            nw._calculate_all_tdee_wrapper({"mifflin": 1500}, "moderate")
    finally:
        if original_nutrition_core is not None:
            monkeypatch.setitem(sys.modules, "nutrition_core", original_nutrition_core)
        else:
            monkeypatch.delitem(sys.modules, "nutrition_core", raising=False)


def test_targets_disabled_container_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """targets_disabled returns True when build_nutrition_targets_fn is unset."""
    # Use monkeypatch to safely set and automatically restore the function
    monkeypatch.setattr(app._plate_deps, "build_nutrition_targets_fn", None, raising=False)
    app.reset_targets_cache()
    assert app.targets_disabled() is True


def test_targets_disabled_module_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """targets_disabled detects None on primary app module attribute.

    The container remains configured (function not None), but an explicit
    None on the primary `app` module signals that targets are disabled.
    """
    # Keep container configured but null out the primary module attribute
    original_fn = app._plate_deps.build_nutrition_targets_fn
    monkeypatch.setattr(app._plate_deps, "build_nutrition_targets_fn", original_fn)
    monkeypatch.setattr(app, "build_nutrition_targets", None, raising=False)
    app.reset_targets_cache()
    assert app.targets_disabled() is True
