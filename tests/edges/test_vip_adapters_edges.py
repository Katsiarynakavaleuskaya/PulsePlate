# -*- coding: utf-8 -*-
"""
Adapter coverage for app.routers.vip: _adapter_make_weekly_menu and _adapter_synthesize_recipes_for_week.
"""

import importlib
from collections import UserDict
from unittest.mock import Mock, patch

import pytest


def _vip():
    return importlib.import_module("app.routers.vip")


def test_adapter_make_weekly_menu_from_single_dict_profile():
    vip = _vip()

    def fake_make_weekly_menu(profile):  # minimal stub
        return {"profile_sex": getattr(profile, "sex", None)}

    with patch("core.menu_engine.make_weekly_menu", fake_make_weekly_menu):
        out = vip._adapter_make_weekly_menu(
            {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            }
        )
        assert isinstance(out, dict) and out.get("profile_sex") == "male"


def test_adapter_make_weekly_menu_from_kwargs_profile_dict():
    try:
        vip = _vip()
    except Exception:
        pytest.skip("Skipping due to import environment constraints for app.routers.vip")

    def fake_make_weekly_menu(profile):
        return {"age": getattr(profile, "age", None)}

    with patch("core.menu_engine.make_weekly_menu", fake_make_weekly_menu):
        out = vip._adapter_make_weekly_menu(
            data={
                "sex": "female",
                "age": 25,
                "height_cm": 160.0,
                "weight_kg": 55.0,
                "activity": "light",
                "goal": "maintain",
            }
        )
        assert isinstance(out, dict) and out.get("age") == 25


def test_adapter_make_weekly_menu_direct_args_passthrough():
    try:
        vip = _vip()
    except Exception:
        pytest.skip("Skipping due to import environment constraints for app.routers.vip")

    direct_profile = object()
    food_db = {"food": "db"}
    recipe_db = {"recipe": "db"}
    core_builder = Mock(return_value={"ok": True})
    with patch("core.menu_engine.make_weekly_menu", core_builder):
        out = vip._adapter_make_weekly_menu(direct_profile, food_db, recipe_db=recipe_db)

    assert out == {"ok": True}
    core_builder.assert_called_once_with(direct_profile, food_db, recipe_db=recipe_db)


def test_adapter_make_weekly_menu_rejects_incomplete_dict_before_core_builder() -> None:
    vip = _vip()
    core_builder = Mock()

    with patch("core.menu_engine.make_weekly_menu", core_builder):
        with pytest.raises(vip.fitchef_runtime.WeeklyProfileInputError) as exc_info:
            vip._adapter_make_weekly_menu(
                {
                    "sex": "female",
                    "age": 25,
                    "height_cm": 160.0,
                    "weight_kg": 55.0,
                    "activity": "light",
                }
            )

    assert exc_info.value.missing_fields == ("goal",)
    core_builder.assert_not_called()


def test_adapter_make_weekly_menu_rejects_incomplete_dict_with_trailing_args() -> None:
    vip = _vip()
    core_builder = Mock()

    with patch("core.menu_engine.make_weekly_menu", core_builder):
        with pytest.raises(vip.fitchef_runtime.WeeklyProfileInputError) as exc_info:
            vip._adapter_make_weekly_menu({"sex": "female"}, {"food": "db"})

    assert exc_info.value.missing_fields == (
        "age",
        "height_cm",
        "weight_kg",
        "activity",
        "goal",
    )
    core_builder.assert_not_called()


def test_adapter_make_weekly_menu_rejects_incomplete_non_dict_mapping() -> None:
    vip = _vip()
    core_builder = Mock()

    with patch("core.menu_engine.make_weekly_menu", core_builder):
        with pytest.raises(vip.fitchef_runtime.WeeklyProfileInputError) as exc_info:
            vip._adapter_make_weekly_menu(UserDict({"sex": "female"}))

    assert exc_info.value.missing_fields == (
        "age",
        "height_cm",
        "weight_kg",
        "activity",
        "goal",
    )
    core_builder.assert_not_called()


def test_adapter_make_weekly_menu_forwards_validated_mapping_and_builder_arguments() -> None:
    vip = _vip()
    raw_profile = UserDict(
        {
            "sex": "female",
            "age": 25,
            "height_cm": 160.0,
            "weight_kg": 55.0,
            "activity": "light",
            "goal": "maintain",
        }
    )
    food_db = {"food": "db"}
    recipe_db = {"recipe": "db"}
    expected_result = {"menu": "weekly"}
    core_builder = Mock(return_value=expected_result)

    with patch("core.menu_engine.make_weekly_menu", core_builder):
        result = vip._adapter_make_weekly_menu(raw_profile, food_db, recipe_db=recipe_db)

    assert result is expected_result
    core_builder.assert_called_once()
    profile, forwarded_food_db = core_builder.call_args.args
    assert profile is not raw_profile
    assert getattr(profile, "sex") == "female"
    assert getattr(profile, "age") == 25
    assert forwarded_food_db is food_db
    assert core_builder.call_args.kwargs == {"recipe_db": recipe_db}


def test_adapter_make_weekly_menu_preserves_no_profile_none_behavior() -> None:
    vip = _vip()
    core_builder = Mock()

    with patch("core.menu_engine.make_weekly_menu", core_builder):
        result = vip._adapter_make_weekly_menu(metadata={"request_id": "local"})

    assert result is None
    core_builder.assert_not_called()


def test_adapter_synthesize_recipes_for_week_passthrough():
    try:
        vip = _vip()
    except Exception:
        pytest.skip("Skipping due to import environment constraints for app.routers.vip")

    def fake_synth(week_plan, recipes_per_day):
        return {"count": recipes_per_day}

    with patch("core.recipe_synth.synthesize_recipes_for_week", fake_synth):
        out = vip._adapter_synthesize_recipes_for_week({"days": []}, 3)
        assert out == {"count": 3}
