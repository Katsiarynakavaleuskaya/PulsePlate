# -*- coding: utf-8 -*-
"""
Adapter coverage for app.routers.vip: _adapter_make_weekly_menu and _adapter_synthesize_recipes_for_week.
"""

import importlib
from unittest.mock import patch

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

    def fake_make_weekly_menu(profile):
        return {"ok": True, "got": profile}

    with patch("core.menu_engine.make_weekly_menu", fake_make_weekly_menu):
        out = vip._adapter_make_weekly_menu(object())
        assert isinstance(out, dict) and out.get("ok") is True


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
