"""Tests for nutrition wrappers resolver paths to improve coverage.

Covers all resolution branches:
- app path (preferred)
- app.app_module path
- app_module path
- nutrition_core fallback via import seams
- unknown name error
- seam returns None error
"""

from __future__ import annotations

import types
from unittest.mock import Mock

import pytest

from app.utils import nutrition_wrappers as nw


def test_resolve_prefers_app_over_app_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that app.<name> is preferred over app.app_module.<name>."""

    def f_app(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 1.0}

    def f_appmod(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 2.0}

    fake_appmod = types.SimpleNamespace(calculate_all_bmr=f_appmod)
    fake_app = types.SimpleNamespace(calculate_all_bmr=f_app, app_module=fake_appmod)
    fake_alias = types.SimpleNamespace(calculate_all_bmr=lambda *a, **k: {"mifflin": 3.0})

    # Patch the seam function instead of sys.modules directly
    monkeypatch.setattr(
        nw, "_get_candidate_modules", lambda: (fake_app, fake_alias, fake_appmod), raising=True
    )

    fn = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert fn is f_app


def test_resolve_falls_back_to_app_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that app.app_module.<name> is used when app.<name> is not available."""

    def f_appmod(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 2.0}

    fake_appmod = types.SimpleNamespace(calculate_all_bmr=f_appmod)
    fake_app = types.SimpleNamespace(app_module=fake_appmod)  # No calculate_all_bmr on app

    # Patch the seam function instead of sys.modules directly
    monkeypatch.setattr(
        nw, "_get_candidate_modules", lambda: (fake_app, None, fake_appmod), raising=True
    )

    fn = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert fn is f_appmod


def test_resolve_falls_back_to_sys_modules_app_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that sys.modules['app_module'].<name> is used when app/app.app_module are not available."""

    def f_alias(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 3.0}

    fake_app = types.SimpleNamespace()  # No calculate_all_bmr, no app_module
    fake_appmod = types.SimpleNamespace(calculate_all_bmr=f_alias)

    # Patch the seam function instead of sys.modules directly
    monkeypatch.setattr(
        nw, "_get_candidate_modules", lambda: (fake_app, fake_appmod, None), raising=True
    )

    fn = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert fn is f_alias


def test_resolve_unknown_name_raises() -> None:
    """Test that unknown callable name raises ImportError."""
    with pytest.raises(ImportError, match="unknown nutrition callable"):
        nw._resolve_nutrition_callable("nope")


def test_resolve_falls_back_to_import_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that nutrition_core import seam is used when all other paths fail."""

    def seam_fn(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 123.0}

    # Patch the seam function to return None modules (all paths fail)
    monkeypatch.setattr(nw, "_get_candidate_modules", lambda: (None, None, None), raising=True)
    monkeypatch.setattr(nw, "_import_nutrition_core_bmr", lambda: seam_fn, raising=True)

    fn = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert fn is seam_fn
    assert fn() == {"mifflin": 123.0}


def test_resolve_import_seam_none_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ImportError is raised when import seam returns None."""
    # Patch the seam function to return None modules (all paths fail)
    monkeypatch.setattr(nw, "_get_candidate_modules", lambda: (None, None, None), raising=True)
    monkeypatch.setattr(nw, "_import_nutrition_core_bmr", lambda: None, raising=True)

    with pytest.raises(ImportError, match="not available"):
        nw._resolve_nutrition_callable("calculate_all_bmr")


def test_resolve_tdee_uses_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that TDEE resolution also uses import seams."""

    def seam_fn(*a: object, **k: object) -> dict[str, int | float]:
        return {"mifflin": 456.0}

    # Patch the seam function to return None modules (all paths fail)
    monkeypatch.setattr(nw, "_get_candidate_modules", lambda: (None, None, None), raising=True)
    monkeypatch.setattr(nw, "_import_nutrition_core_tdee", lambda: seam_fn, raising=True)

    fn = nw._resolve_nutrition_callable("calculate_all_tdee")
    assert fn is seam_fn
    assert fn({"mifflin": 1500.0}, "moderate") == {"mifflin": 456.0}


def test_resolve_skips_non_callable_attr_and_falls_back_to_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that non-callable attributes are skipped and fallback to seam is used."""
    # pkg exposes the "right" name but it's NOT callable
    fake_pkg = types.SimpleNamespace(calculate_all_bmr="not-a-function")
    fake_alias = None
    fake_pkg_appmod = None

    def seam_fn(*a: object, **k: object) -> dict[str, float]:
        return {"mifflin": 123.0}

    monkeypatch.setattr(
        nw,
        "_get_candidate_modules",
        lambda: (fake_pkg, fake_alias, fake_pkg_appmod),
        raising=True,
    )
    monkeypatch.setattr(nw, "_import_nutrition_core_bmr", lambda: seam_fn, raising=True)

    fn = nw._resolve_nutrition_callable("calculate_all_bmr")
    assert fn is seam_fn
    assert fn() == {"mifflin": 123.0}
