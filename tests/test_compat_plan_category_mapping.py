# -*- coding: utf-8 -*-
"""
RU: Таргетные тесты для покрытия compat слоя /plan category mapping.
EN: Targeted coverage tests for compat /plan category mapping.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.bmi.compat_plan import legacy_plan_category
from core.i18n import t


@pytest.mark.parametrize(
    "group,bmi,expected_i18n_key",
    [
        # athlete: full adult buckets must be reachable
        ("athlete", Decimal("18.4"), "bmi_underweight"),
        ("athlete", Decimal("24.9"), "bmi_normal"),
        ("athlete", Decimal("29.9"), "bmi_overweight"),
        ("athlete", Decimal("34.9"), "bmi_obese_1"),
        ("athlete", Decimal("39.9"), "bmi_obese_2"),
        ("athlete", Decimal("40.0"), "bmi_obese_3"),
        # elderly
        ("elderly", Decimal("17.4"), "bmi_underweight"),
        ("elderly", Decimal("25.9"), "bmi_normal"),
        ("elderly", Decimal("26.0"), "bmi_overweight"),
        # teen/child thresholds
        ("teen", Decimal("17.4"), "bmi_underweight"),
        ("teen", Decimal("24.4"), "bmi_normal"),
        ("teen", Decimal("24.5"), "bmi_overweight"),
        # general thresholds full buckets
        ("general", Decimal("18.4"), "bmi_underweight"),
        ("general", Decimal("24.9"), "bmi_normal"),
        ("general", Decimal("29.9"), "bmi_overweight"),
        ("general", Decimal("34.9"), "bmi_obese_1"),
        ("general", Decimal("39.9"), "bmi_obese_2"),
        ("general", Decimal("40.0"), "bmi_obese_3"),
    ],
)
def test_legacy_plan_category_minors_bucket_mapping(
    group: str, bmi: Decimal, expected_i18n_key: str
) -> None:
    """
    RU: Для minors (age<18) engine_category=None → compat вычисляет slug по bmi+group
    и возвращает локализованную строку.
    EN: For minors, compat computes slug by bmi+group and returns a localized string.
    """
    res = legacy_plan_category(
        engine_category=None,  # force mapping path for minors
        bmi=bmi,
        age=15,
        lang="en",
        group=group,
    )
    assert res.category == t("en", expected_i18n_key)


def test_legacy_plan_category_too_young_returns_none() -> None:
    """
    RU: group=too_young (age<12) не должен классифицироваться (category=None).
    EN: too_young group should not be classified (category=None).
    """
    res = legacy_plan_category(
        engine_category=None,
        bmi=Decimal("19.0"),
        age=11,
        lang="en",
        group="too_young",
    )
    assert res.category is None


def test_legacy_plan_category_keeps_engine_category_when_present() -> None:
    """
    RU: Если engine_category задан, compat не должен пересчитывать по BMI.
    EN: If engine_category is present, compat must not recompute it.
    """
    res = legacy_plan_category(
        engine_category="normal",
        bmi=Decimal("100.0"),
        age=15,  # even for minors: do not recompute when engine_category is present
        lang="en",
        group="teen",
    )
    assert res.category == t("en", "bmi_normal")


def test_legacy_plan_category_unknown_slug_falls_back_to_string() -> None:
    """
    RU: Если slug не известен _CATEGORY_I18N_KEY → вернуть как строку.
    EN: If slug is not known to _CATEGORY_I18N_KEY, return it as string.
    """
    res = legacy_plan_category(
        engine_category="custom_slug",
        bmi=Decimal("22.0"),
        age=30,
        lang="en",
        group="general",
    )
    assert res.category == "custom_slug"


def test_legacy_plan_category_adult_with_none_engine_category_returns_none() -> None:
    """
    RU: engine_category=None + age>=18 → вернуть None (для взрослых этот слой не маппит по BMI).
    EN: engine_category=None + age>=18 should return None (no BMI mapping for adults here).
    """
    res = legacy_plan_category(
        engine_category=None,
        bmi=Decimal("22.0"),
        age=30,
        lang="en",
        group="general",
    )
    assert res.category is None
