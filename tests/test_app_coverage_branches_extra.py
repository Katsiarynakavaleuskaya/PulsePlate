import importlib
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from app.services import pro_nutrition_plate as plate_service


def test_background_updates_wrappers_normal_mode_calls_resolvers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover start/stop wrappers in normal (non-pytest-sync) mode."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    legacy_app = importlib.import_module("legacy_app")

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


def test_plate_dependencies_are_resolved_per_call() -> None:
    """Production dependency sets are fresh and bound to canonical modules."""
    first = plate_service._default_dependencies()
    second = plate_service._default_dependencies()

    assert first is not second
    assert first.make_plate is plate_service.nutrition_plate.make_plate
    assert first.calculate_all_bmr is plate_service.nutrition_bmr.calculate_all_bmr
    assert first.calculate_all_tdee is plate_service.nutrition_bmr.calculate_all_tdee


def test_plate_dependencies_are_immutable_without_facade_registry() -> None:
    """Dependency overrides cannot mutate process-global Plate behavior."""
    dependencies = plate_service._default_dependencies()

    with pytest.raises(FrozenInstanceError):
        setattr(dependencies, "make_plate", None)

    assert not hasattr(plate_service, "_plate_deps")
    assert not hasattr(plate_service, "_targets_disabled_cache")
