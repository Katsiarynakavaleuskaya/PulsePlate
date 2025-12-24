import sys
from unittest.mock import patch

import pytest

import app


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
    monkeypatch.setitem(app._calculate_all_bmr_wrapper.__globals__, "calculate_all_bmr", None)
    with pytest.raises(ImportError):
        app._calculate_all_bmr_wrapper(70, 175, 30, "male")

    for module in (
        app,
        getattr(app, "app_module", None),
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_tdee", None, raising=False)
    monkeypatch.setitem(app._calculate_all_tdee_wrapper.__globals__, "calculate_all_tdee", None)
    with pytest.raises(ImportError):
        app._calculate_all_tdee_wrapper({"mifflin": 1500}, "moderate")


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
