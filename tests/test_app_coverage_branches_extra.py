import sys
from unittest.mock import patch

import pytest

import app


def test_background_updates_wrappers_no_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover start/stop background update wrappers when no event loop is running."""

    called: list[str | int] = []

    async def fake_start(update_interval_hours: int = 24) -> None:
        called.append(update_interval_hours)

    async def fake_stop() -> None:
        called.append("stop")

    # Instead of patching global asyncio.get_running_loop, we'll simulate the condition
    # by temporarily setting an environment variable that forces sync mode
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
        # Patch the global functions directly in the app module's dict
        # This is safer than patching asyncio globals which affects other tests
        original_start = app.__dict__.get("_scheduler_start_background_updates")
        original_stop = app.__dict__.get("_scheduler_stop_background_updates")

        try:
            app.__dict__["_scheduler_start_background_updates"] = fake_start
            app.__dict__["_scheduler_stop_background_updates"] = fake_stop

            app.start_background_updates(update_interval_hours=12)
            app.stop_background_updates()
        finally:
            # Restore original functions
            if original_start is not None:
                app.__dict__["_scheduler_start_background_updates"] = original_start
            else:
                app.__dict__.pop("_scheduler_start_background_updates", None)

            if original_stop is not None:
                app.__dict__["_scheduler_stop_background_updates"] = original_stop
            else:
                app.__dict__.pop("_scheduler_stop_background_updates", None)

    assert 12 in called
    assert "stop" in called


def test_calculate_wrappers_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure wrappers raise ImportError when their dependencies are missing."""
    # Null out all visible locations so wrappers raise ImportError deterministically
    for module in (
        app,
        app.app_module,
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_bmr", None, raising=False)
    monkeypatch.setitem(app._calculate_all_bmr_wrapper.__globals__, "calculate_all_bmr", None)
    with pytest.raises(ImportError):
        app._calculate_all_bmr_wrapper(70, 175, 30, "male")

    for module in (
        app,
        app.app_module,
        sys.modules.get("app_module"),
    ):
        if module is not None:
            monkeypatch.setattr(module, "calculate_all_tdee", None, raising=False)
    monkeypatch.setitem(app._calculate_all_tdee_wrapper.__globals__, "calculate_all_tdee", None)
    with pytest.raises(ImportError):
        app._calculate_all_tdee_wrapper({"mifflin": 1500}, "moderate")


def test_targets_disabled_container_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """targets_disabled returns True when build_nutrition_targets_fn is unset."""
    original_fn = app._plate_deps.build_nutrition_targets_fn
    try:
        app._plate_deps.build_nutrition_targets_fn = None
        app.reset_targets_cache()
        assert app.targets_disabled() is True
    finally:
        app._plate_deps.build_nutrition_targets_fn = original_fn
        app.reset_targets_cache()


def test_targets_disabled_module_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """targets_disabled detects None on primary app module attribute.

    The container remains configured (function not None), but an explicit
    None on the primary `app` module signals that targets are disabled.
    """
    original_fn = app._plate_deps.build_nutrition_targets_fn
    _had_attr = hasattr(app, "build_nutrition_targets")
    original_app_attr = getattr(app, "build_nutrition_targets", None) if _had_attr else None

    try:
        # Keep container configured but null out the primary module attribute
        app._plate_deps.build_nutrition_targets_fn = original_fn
        app.build_nutrition_targets = None
        app.reset_targets_cache()
        assert app.targets_disabled() is True
    finally:
        app._plate_deps.build_nutrition_targets_fn = original_fn
        if not _had_attr:
            if hasattr(app, "build_nutrition_targets"):
                delattr(app, "build_nutrition_targets")
        else:
            app.build_nutrition_targets = original_app_attr
        app.reset_targets_cache()


def test_who_targets_request_goal_normalization() -> None:
    """WHOTargetsRequest normalizes goal synonyms via validator."""
    req = app.WHOTargetsRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="lose",
    )
    assert req.goal == "loss"
