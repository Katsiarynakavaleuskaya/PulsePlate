import os
import sys
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import app


def _namespaced_attrs(overrides: dict[str, Any] | None = None) -> SimpleNamespace:
    """Create a namespace that contains all patched attrs used by app helpers."""

    base = {attr: object() for attr in app._PATCHED_ATTRS}
    if overrides:
        base.update(overrides)
    return SimpleNamespace(**base)


def test_propagate_app_patches_copies_all_known_attrs() -> None:
    """Ensure helper copies patched attributes without raising."""

    source = _namespaced_attrs()
    target = SimpleNamespace()

    app._propagate_app_patches(source, target)

    for attr in app._PATCHED_ATTRS:
        assert getattr(target, attr) is getattr(source, attr)


def primary_callable(*_: Any, **__: Any) -> str:
    """Primary callable for testing patch isolation."""
    return "primary"


def secondary_callable(*_: Any, **__: Any) -> str:
    """Secondary callable for testing patch isolation."""
    return "secondary"


def test_sync_app_attr_sources_skips_current_value_before_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Alias that already references primary helper should be switched to the next candidate."""

    alias_module = _namespaced_attrs({"make_plate": primary_callable})
    primary = _namespaced_attrs({"make_plate": primary_callable})
    secondary = _namespaced_attrs({"make_plate": secondary_callable})

    state = {name: None for name in app._PATCHED_ATTRS}
    monkeypatch.setattr(app, "_PATCH_SOURCE_IDS", state, raising=False)

    app._sync_app_attr_sources(alias_module, (primary, secondary))

    assert alias_module.make_plate is secondary_callable


def test_targets_disabled_detects_alias_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    """If alias module nulls build_nutrition_targets we propagate disable."""

    class AliasStub(SimpleNamespace):
        """Stub class for testing alias module behavior.

        RU: Заглушка для тестирования поведения модуля-алиаса.
        EN: Stub class for testing alias module behavior.

        This class overrides __setattr__ to ignore subsequent assignments to
        'build_nutrition_targets' after it has been set once. This simulates the
        behavior where an alias module may null out or disable certain functions
        at runtime, and we want to detect and propagate this disable state.

        Callers should expect that:
        - First assignment to 'build_nutrition_targets' succeeds
        - Subsequent assignments are silently ignored
        - Other attributes can be set normally

        Edge cases:
        - If 'build_nutrition_targets' is never set initially, it can be set normally
        - The check uses hasattr() so even None values are considered "set"
        """

        def __setattr__(self, name: str, value: Any) -> None:
            if name == "build_nutrition_targets" and hasattr(self, "build_nutrition_targets"):
                return
            super().__setattr__(name, value)

    alias_module = AliasStub(build_nutrition_targets=None, make_plate="alias-value")
    original_alias = sys.modules.get("app_module")
    monkeypatch.setitem(sys.modules, "app_module", alias_module)
    monkeypatch.setattr(app, "_APP_PACKAGE_REF", app, raising=False)
    monkeypatch.setattr(app, "_targets_runtime_disabled", False, raising=False)
    sentinel_builder = object()
    monkeypatch.setattr(app, "build_nutrition_targets", sentinel_builder, raising=False)

    try:
        assert app._targets_disabled() is True
    finally:
        if original_alias is not None:
            sys.modules["app_module"] = original_alias


def test_plate_env_snapshot_restores_env_and_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Context manager restores aliased module attributes and env state."""

    alias_original = sys.modules.get("app_module")
    dummy_alias = SimpleNamespace(
        **{attr: f"original-{attr}" for attr in app._PATCHED_ATTRS},
    )
    monkeypatch.setitem(sys.modules, "app_module", dummy_alias)
    os.environ["FEATURE_PREMIUM_NUTRITION"] = "test-flag"

    with app._plate_env_snapshot():
        for attr in app._PATCHED_ATTRS:
            setattr(dummy_alias, attr, f"mutated-{attr}")
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "mutated"

    for attr in app._PATCHED_ATTRS:
        assert getattr(dummy_alias, attr) == f"original-{attr}"
    assert os.environ["FEATURE_PREMIUM_NUTRITION"] == "test-flag"

    os.environ.pop("FEATURE_PREMIUM_NUTRITION", None)
    with app._plate_env_snapshot():
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "inside-snapshot"
    assert "FEATURE_PREMIUM_NUTRITION" not in os.environ

    if alias_original is not None:
        sys.modules["app_module"] = alias_original


@pytest.mark.asyncio
async def test_premium_plate_alignment_uses_heuristic_when_targets_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When targets backend disabled we fall back to heuristic carbs alignment."""

    alias_module = sys.modules.get("app_module")
    top_module = sys.modules.get("_app_top_module")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    async def fake_aggregate(_meals: Any) -> dict[str, Any]:
        return {}

    monkeypatch.setattr(app, "_aggregate_day_micronutrients", fake_aggregate, raising=False)

    def fake_make_plate(**_: Any) -> dict[str, Any]:
        return {
            "macros": {"protein_g": 90, "fat_g": 40, "carbs_g": 60, "fiber_g": 10},
            "portions": {"protein_palm": 1.0},
            "layout": [
                {"kind": "plate_sector", "fraction": 0.5, "label": "Demo", "tooltip": "Demo"}
            ],
            "meals": [
                {
                    "title": "Demo meal",
                    "kcal": 1200,
                    "macros": {"protein_g": 30, "fat_g": 15, "carbs_g": 20},
                }
            ],
            "kcal": 2400,
            "meals_per_day": 3,
        }

    for target in filter(None, (app, alias_module, top_module)):
        monkeypatch.setattr(target, "make_plate", fake_make_plate, raising=False)
        monkeypatch.setattr(target, "build_nutrition_targets", None, raising=False)

    monkeypatch.setattr(app, "_targets_runtime_disabled", False, raising=False)
    monkeypatch.setattr(app, "calculate_all_bmr", lambda *_: {"mifflin": 1600}, raising=False)
    monkeypatch.setattr(
        app, "calculate_all_tdee", lambda *_1, **_2: {"mifflin": 1800}, raising=False
    )

    request = app.PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
    )

    response = await app.api_premium_plate(request)

    prot_ref = int(round(1.6 * request.weight_kg))
    fat_ref = int(round(0.9 * request.weight_kg))
    expected_carbs = int(round((response.kcal - prot_ref * 4 - fat_ref * 9) / 4))
    assert response.macros["carbs_g"] == expected_carbs
