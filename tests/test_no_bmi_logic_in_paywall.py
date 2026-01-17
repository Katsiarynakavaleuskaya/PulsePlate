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
    import app.routers.bmi as bmi_router

    # Get source of the specific function, not the whole module
    func = getattr(bmi_router, "_build_soft_paywall_hook", None)
    assert func is not None, "_build_soft_paywall_hook function not found"

    src = inspect.getsource(func)
    # Check that _build_soft_paywall_hook doesn't import core/bmi
    assert "from core.bmi" not in src
    assert "import core.bmi" not in src
