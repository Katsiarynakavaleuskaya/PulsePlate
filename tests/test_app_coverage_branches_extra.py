import sys
from typing import Any
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

    # Null out all visible locations so wrappers raise ImportError deterministically
    for module in (
        app,
        getattr(app, "app_module", None),
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_bmr", None, raising=False)
            monkeypatch.setattr(module, "calculate_all_tdee", None, raising=False)

    # Block nutrition_core import seams (wrapper's fallback) by patching import functions
    monkeypatch.setattr(nw, "_import_nutrition_core_bmr", lambda: None, raising=False)
    monkeypatch.setattr(nw, "_import_nutrition_core_tdee", lambda: None, raising=False)

    with pytest.raises(ImportError):
        nw._calculate_all_bmr_wrapper(70, 175, 30, "male")

    with pytest.raises(ImportError):
        nw._calculate_all_tdee_wrapper({"mifflin": 1500}, "moderate")


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


def test_calculate_all_bmr_wrapper_happy_path_nutrition_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test BMR wrapper happy path when nutrition_core is available."""
    calls: dict[str, object] = {}

    def fake_bmr(*args: Any, **kwargs: Any) -> dict[str, float]:
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"mifflin": 1500.0, "harris": 1600.0}

    # Null out app/app_module paths to force nutrition_core fallback
    for module in (app, getattr(app, "app_module", None), sys.modules.get("app_module")):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_bmr", None, raising=False)

    # Patch import seam to return fake function
    monkeypatch.setattr(nw, "_import_nutrition_core_bmr", lambda: fake_bmr, raising=False)

    res = nw._calculate_all_bmr_wrapper(70.0, 175.0, 30, "male", bodyfat=None)
    assert res == {"mifflin": 1500.0, "harris": 1600.0}
    assert calls["args"] == (70.0, 175.0, 30, "male", None)
    assert calls["kwargs"] == {}


def test_calculate_all_tdee_wrapper_happy_path_nutrition_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test TDEE wrapper happy path when nutrition_core is available."""
    calls: dict[str, object] = {}

    def fake_tdee(*args: Any, **kwargs: Any) -> dict[str, int | float]:
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"mifflin": 2000.0, "harris": 2100.0}

    # Null out app/app_module paths to force nutrition_core fallback
    for module in (app, getattr(app, "app_module", None), sys.modules.get("app_module")):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_tdee", None, raising=False)

    # Patch import seam to return fake function
    monkeypatch.setattr(nw, "_import_nutrition_core_tdee", lambda: fake_tdee, raising=False)

    res = nw._calculate_all_tdee_wrapper({"mifflin": 1500.0}, "moderate")
    assert res == {"mifflin": 2000.0, "harris": 2100.0}
    assert calls["args"] == ({"mifflin": 1500.0}, "moderate")
    assert calls["kwargs"] == {}
