from collections.abc import Callable
import sys
import types
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


def test_background_updates_wrappers_normal_mode_calls_resolvers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover start/stop wrappers in normal (non-pytest-sync) mode."""
    import legacy_app

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    executed: list[tuple[Callable[..., Any], int, object]] = []
    safe_stops: list[Callable[..., Any]] = []

    async def fake_starter(update_interval_hours: int = 24) -> None:
        _ = update_interval_hours

    async def fake_stopper() -> None:
        return None

    def resolve_scheduler_starter(*_args: object, **_kwargs: object) -> Callable[..., Any]:
        return fake_starter

    def execute_async_starter(starter: Callable[..., Any], hours: int, _asyncio: object) -> None:
        executed.append((starter, hours, _asyncio))

    def resolve_stop_callable(*_args: object, **_kwargs: object) -> Callable[..., Any]:
        return fake_stopper

    def safe_stop_with_cleanup(stopper: Callable[..., Any]) -> None:
        safe_stops.append(stopper)

    def _no_running_loop() -> None:
        raise RuntimeError("no running loop")

    monkeypatch.setattr(legacy_app, "resolve_scheduler_starter", resolve_scheduler_starter)
    monkeypatch.setattr(legacy_app, "execute_async_starter", execute_async_starter)
    monkeypatch.setattr(legacy_app, "resolve_stop_callable", resolve_stop_callable)
    monkeypatch.setattr(legacy_app, "safe_stop_with_cleanup", safe_stop_with_cleanup)
    monkeypatch.setattr(legacy_app.asyncio, "get_running_loop", _no_running_loop)

    legacy_app.start_background_updates(update_interval_hours=7)
    assert executed[0][0] is fake_starter
    assert executed[0][1] == 7

    legacy_app.stop_background_updates()
    assert safe_stops == [fake_stopper]


def test_resolve_app_callable_returns_default_when_modules_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover _resolve_app_callable when sys.modules lacks app/app_module."""
    from app.utils.helpers import _resolve_app_callable

    def _default() -> str:
        return "ok"

    monkeypatch.delitem(sys.modules, "app", raising=False)
    monkeypatch.delitem(sys.modules, "app_module", raising=False)

    resolved = _resolve_app_callable("nonexistent", default=_default)
    assert resolved is _default


def test_import_nutrition_core_import_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover _import_nutrition_core_* implementations (ImportError + happy paths)."""

    def _boom(_name: str) -> types.ModuleType:
        raise ImportError("boom")

    monkeypatch.setattr(nw.importlib, "import_module", _boom)
    assert nw._import_nutrition_core_bmr() is None
    assert nw._import_nutrition_core_tdee() is None

    mod = types.ModuleType("nutrition_core")

    def calculate_all_bmr(*_args: Any, **_kwargs: Any) -> dict[str, float]:
        return {"mifflin": 1500.0}

    def calculate_all_tdee(*_args: Any, **_kwargs: Any) -> dict[str, int | float]:
        return {"mifflin": 2000.0}

    setattr(mod, "calculate_all_bmr", calculate_all_bmr)
    setattr(mod, "calculate_all_tdee", calculate_all_tdee)

    def _import_module(name: str) -> types.ModuleType:
        assert name == "nutrition_core"
        return mod

    monkeypatch.setattr(nw.importlib, "import_module", _import_module)
    assert nw._import_nutrition_core_bmr() is calculate_all_bmr
    assert nw._import_nutrition_core_tdee() is calculate_all_tdee


def test_resolve_nutrition_callable_prefers_app_app_module_over_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover resolution order: app.app_module wins over sys.modules['app_module']."""
    pkg = types.ModuleType("app")
    pkg_appmod = types.ModuleType("app.app_module")
    alias_pkg = types.ModuleType("app_module")

    def appmod_bmr(*_args: Any, **_kwargs: Any) -> dict[str, float]:
        return {"mifflin": 1500.0}

    def alias_bmr(*_args: Any, **_kwargs: Any) -> dict[str, float]:
        return {"mifflin": 1400.0}

    setattr(pkg_appmod, "calculate_all_bmr", appmod_bmr)
    setattr(alias_pkg, "calculate_all_bmr", alias_bmr)
    setattr(pkg, "app_module", pkg_appmod)

    monkeypatch.setitem(sys.modules, "app", pkg)
    monkeypatch.setitem(sys.modules, "app_module", alias_pkg)

    resolved = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert resolved is appmod_bmr


def test_resolve_nutrition_callable_unknown_name_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover unknown callable name branch."""
    monkeypatch.setitem(sys.modules, "app", types.ModuleType("app"))
    monkeypatch.setitem(sys.modules, "app_module", types.ModuleType("app_module"))

    with pytest.raises(ImportError, match="unknown nutrition callable"):
        nw._resolve_nutrition_callable("unknown")


def test_calculate_wrappers_fallback_to_nutrition_core_real_import_seams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover wrapper fallback to nutrition_core via real import seams."""
    mod = types.ModuleType("nutrition_core")

    def calculate_all_bmr(
        weight_kg: float,
        height_cm: float,
        age: int,
        sex: str,
        bodyfat: float | None,
    ) -> dict[str, float]:
        assert (weight_kg, height_cm, age, sex, bodyfat) == (70.0, 175.0, 30, "male", None)
        return {"mifflin": 1500.0}

    def calculate_all_tdee(bmr_results: dict[str, float], activity: str) -> dict[str, int | float]:
        assert bmr_results == {"mifflin": 1500.0}
        assert activity == "moderate"
        return {"mifflin": 2000.0}

    setattr(mod, "calculate_all_bmr", calculate_all_bmr)
    setattr(mod, "calculate_all_tdee", calculate_all_tdee)

    def _import_module(name: str) -> types.ModuleType:
        assert name == "nutrition_core"
        return mod

    # Ensure wrappers don't resolve from app/app_module so fallback is exercised
    monkeypatch.setitem(sys.modules, "app", types.ModuleType("app"))
    monkeypatch.delitem(sys.modules, "app_module", raising=False)
    monkeypatch.setattr(nw.importlib, "import_module", _import_module)

    bmr = nw._calculate_all_bmr_wrapper(70.0, 175.0, 30, "male", bodyfat=None)
    assert bmr == {"mifflin": 1500.0}

    tdee = nw._calculate_all_tdee_wrapper({"mifflin": 1500.0}, "moderate")
    assert tdee == {"mifflin": 2000.0}


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
