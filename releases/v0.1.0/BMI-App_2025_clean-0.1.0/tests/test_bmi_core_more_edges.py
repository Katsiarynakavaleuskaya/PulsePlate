# -*- coding: utf-8 -*-
"""Дополнительные edge-тесты: _validate_age error и ветка 'general' в auto_group."""

import pytest

from bmi_core import auto_group, bmi_value, build_premium_plan


def test_validate_age_raises_in_build_plan():
    # age=0 → _validate_age должен выбросить ValueError (строка 103)
    with pytest.raises(ValueError):
        # вес/рост валидные, чтобы дошло именно до проверки возраста
        build_premium_plan(0, 70.0, 1.75, bmi_value(70.0, 1.75), "en", "general", False)


def test_auto_group_returns_general_branch():
    # Взрослый, не беременна, не спортсмен → 'general' (строка 166)
    grp = auto_group(30, "male", "no", "no", "en")
    assert grp == "general"
