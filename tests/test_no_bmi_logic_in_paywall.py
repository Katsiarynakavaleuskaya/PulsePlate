# -*- coding: utf-8 -*-
"""
Guard test: Soft paywall hook builder must not import core/bmi/*.

RU: Тест-страж: builder soft paywall hook не должен импортировать core/bmi/*.
EN: Guard test: soft paywall hook builder must not import core/bmi/*.
"""

from __future__ import annotations

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HELPERS = ROOT / "app" / "routers" / "_helpers.py"
BMI_ROUTER = ROOT / "app" / "routers" / "bmi.py"
BMI_PRO_ROUTER = ROOT / "app" / "routers" / "bmi_pro.py"


def _read(p: Path) -> str:
    """Read file content."""
    return p.read_text(encoding="utf-8")


def test_soft_paywall_hook_has_no_core_bmi_imports() -> None:
    """
    Guard: soft-paywall hook must remain text-only router helper.

    - No imports from core.bmi / core/bmi/*
    """
    # Read the file and extract only the _build_soft_paywall_hook function
    # (inspect.getsource may include surrounding context)
    full_src = _read(HELPERS)

    # Find the function definition and extract its body
    start_idx = full_src.find("def _build_soft_paywall_hook")
    assert start_idx != -1, "_build_soft_paywall_hook function not found in _helpers.py"

    # Extract from function start to next function or end of file
    remaining = full_src[start_idx:]
    # Find the next function definition (if any)
    next_def = remaining.find("\ndef ", 1)  # Skip the current def
    if next_def != -1:
        func_src = remaining[:next_def]
    else:
        func_src = remaining

    # Check that _build_soft_paywall_hook doesn't import core/bmi
    assert "from core.bmi" not in func_src, "Soft paywall hook must not import from core.bmi"
    assert "import core.bmi" not in func_src, "Soft paywall hook must not import core.bmi"


def test_routers_do_not_define_local_soft_paywall_hook() -> None:
    """
    Guard: routers must not carry local copies of _build_soft_paywall_hook.

    They must import it from app.routers._helpers so guard covers runtime path.
    """
    for router_path in (BMI_ROUTER, BMI_PRO_ROUTER):
        src = _read(router_path)

        assert "def _build_soft_paywall_hook" not in src, (
            f"{router_path} defines local _build_soft_paywall_hook — "
            "must be removed and replaced with shared helper import"
        )
        assert (
            "from app.routers._helpers import _build_soft_paywall_hook" in src
        ), f"{router_path} must import _build_soft_paywall_hook from app.routers._helpers"


def test_soft_paywall_builder_does_not_import_core_bmi() -> None:
    """
    Guard: soft paywall builder must not import core/bmi/*.

    This ensures hook builder stays in router/adapter layer only,
    with no BMI logic dependencies.

    Note: This test validates the shared helper function directly.
    """
    from app.routers._helpers import _build_soft_paywall_hook

    # Get source of the shared helper function
    src = inspect.getsource(_build_soft_paywall_hook)
    # Check that _build_soft_paywall_hook doesn't import core/bmi
    assert "from core.bmi" not in src
    assert "import core.bmi" not in src
