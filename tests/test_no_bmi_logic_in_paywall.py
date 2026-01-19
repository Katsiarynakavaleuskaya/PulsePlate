# -*- coding: utf-8 -*-
"""
Guard test: Soft paywall hook builder must not import core/bmi/*.

RU: Тест-страж: builder soft paywall hook не должен импортировать core/bmi/*.
EN: Guard test: soft paywall hook builder must not import core/bmi/*.
"""

from __future__ import annotations

import inspect


def test_soft_paywall_builder_does_not_import_core_bmi() -> None:
    """
    Guard: soft paywall builder must not import core/bmi/*.

    This ensures hook builder stays in router/adapter layer only,
    with no BMI logic dependencies.
    """
    from app.routers._helpers import _build_soft_paywall_hook

    # Get source of the shared helper function
    src = inspect.getsource(_build_soft_paywall_hook)
    # Check that _build_soft_paywall_hook doesn't import core/bmi
    assert "from core.bmi" not in src
    assert "import core.bmi" not in src
