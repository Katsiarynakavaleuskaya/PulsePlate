"""Contracts for canonical lazy weekly-menu builder access."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.services import legacy_premium_weekly_plan as weekly_plan_service


def _service_source() -> str:
    service_path = Path(weekly_plan_service.__file__).resolve()
    return service_path.read_text(encoding="utf-8")


def test_weekly_menu_builder_access_returns_exact_core_callable() -> None:
    from core.menu_engine import make_weekly_menu

    assert weekly_plan_service.get_weekly_menu_builder() is make_weekly_menu


@pytest.mark.parametrize("missing_name", ("core", "core.menu_engine"))
def test_weekly_menu_builder_access_maps_only_canonical_module_absence_to_none(
    monkeypatch: pytest.MonkeyPatch,
    missing_name: str,
) -> None:
    def _raise_missing_module() -> weekly_plan_service.WeeklyMenuBuilder:
        raise ModuleNotFoundError("canonical module absent", name=missing_name)

    monkeypatch.setattr(weekly_plan_service, "_load_weekly_menu_builder", _raise_missing_module)

    assert weekly_plan_service.get_weekly_menu_builder() is None


@pytest.mark.parametrize(
    "failure",
    (
        ModuleNotFoundError("transitive module absent", name="optional_provider"),
        ModuleNotFoundError("module name unavailable", name=None),
        ImportError("make_weekly_menu export missing"),
        ImportError("plain import failure"),
    ),
    ids=("transitive-module", "missing-name", "missing-symbol", "plain-import"),
)
def test_weekly_menu_builder_access_propagates_broken_runtime_imports(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    def _raise_broken_import() -> weekly_plan_service.WeeklyMenuBuilder:
        raise failure

    monkeypatch.setattr(weekly_plan_service, "_load_weekly_menu_builder", _raise_broken_import)

    with pytest.raises(type(failure), match=str(failure)):
        weekly_plan_service.get_weekly_menu_builder()


def test_weekly_menu_builder_loader_rejects_non_callable_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.menu_engine as menu_engine

    monkeypatch.setattr(menu_engine, "make_weekly_menu", None)

    with pytest.raises(TypeError, match="make_weekly_menu must be callable"):
        weekly_plan_service._load_weekly_menu_builder()


def test_weekly_menu_builder_access_is_lazy_stateless_and_facade_independent() -> None:
    source = _service_source()
    tree = ast.parse(source)

    top_level_core_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            (alias.name if isinstance(node, ast.Import) else node.module or "").startswith(
                "core.menu_engine"
            )
            for alias in node.names
        )
    ]
    assigned_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Name)
    }

    assert top_level_core_imports == []
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
        and node.attr == "modules"
        for node in ast.walk(tree)
    )
    assert "legacy_app" not in source
    assert not any(
        marker in name.lower()
        for name in assigned_names
        for marker in ("cache", "registry", "override")
    )


@pytest.mark.parametrize(
    "imports",
    (
        ("app.services.legacy_premium_weekly_plan", "core.menu_engine"),
        ("core.menu_engine", "app.services.legacy_premium_weekly_plan"),
        ("legacy_app", "app.services.legacy_premium_weekly_plan", "core.menu_engine"),
    ),
    ids=("service-first", "core-first", "legacy-first"),
)
def test_weekly_menu_builder_access_is_import_order_independent(
    imports: tuple[str, ...],
) -> None:
    import_lines = "\n".join(f'importlib.import_module("{module_name}")' for module_name in imports)
    script = f"""
import importlib
{import_lines}
from app.services.legacy_premium_weekly_plan import get_weekly_menu_builder
from core.menu_engine import make_weekly_menu
assert get_weekly_menu_builder() is make_weekly_menu
"""
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "TESTING": "true",
        }
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
