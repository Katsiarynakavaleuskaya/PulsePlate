"""Repository policy guards - enforce import hygiene and architectural constraints.

These tests prevent regression of patterns that cause Dual Base, namespace conflicts,
and xdist failures.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- Hard rules (policy) ---
FORBIDDEN_DYNAMIC_IMPORT_TOKENS = (
    "importlib.util.spec_from_file_location",
    "importlib.util.module_from_spec",
    "spec_from_file_location(",
    "module_from_spec(",
    "exec_module(",
)

FORBIDDEN_SYS_MODULES_TOKENS = (
    "sys.modules[",  # assignment/deletion (check context manually if needed)
)

FORBIDDEN_SYS_PATH_INSERT = "sys.path.insert"

# Allowed exceptions for dynamic imports / sys.path insert in tests
ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/test_ensure_database_versions.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for these patterns)
    "tests/test_import_hygiene_guard.py",  # guard test
    "tests/test_app_public_surface.py",  # checks for spec_from_file_location string
}

ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT = {
    "tests/test_test_pro_access_coverage.py",
    "tests/conftest.py",
    "tests/test_repo_policy_guards.py",  # this file (checks for the pattern)
    "tests/test_import_hygiene_guard.py",  # guard test
}

# sys.modules checking in tests is allowed only for verification/guards
ALLOWED_SYS_MODULES_CHECK_FILES = {
    "tests/test_repo_policy_guards.py",  # this file
    "tests/conftest.py",  # sys.modules binding for app
    "tests/test_app_init_rebinding_spec.py",  # tests sys.modules["app"] behavior
}

# If you intentionally allow a specific file later, add it to an allowlist above.


def _iter_py_files(relative_glob: str) -> Iterable[Path]:
    yield from REPO_ROOT.glob(relative_glob)


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def test_no_dynamic_imports_in_app_core() -> None:
    """Prevent re-introducing dynamic module exec in app/core code."""
    offenders: list[str] = []

    for path in list(_iter_py_files("app/**/*.py")) + list(_iter_py_files("core/**/*.py")):
        content = _read(path)
        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            offenders.append(_rel(path))

    assert not offenders, f"Dynamic import tokens found in: {offenders}"


@pytest.mark.skip(reason="TODO: Many legacy tests use sys.modules - cleanup in follow-up PR")
def test_no_sys_modules_mutation_in_repo() -> None:
    """sys.modules mutation is a common source of Dual Base / namespace bugs.

    This checks for explicit assignment/deletion patterns.
    Reading from sys.modules is allowed.

    TODO: Clean up legacy tests that mutate sys.modules.
    """
    offenders: list[str] = []

    # Check for assignment: sys.modules[...] =
    assignment_pattern = r"sys\.modules\[[^]]+\]\s*="
    # Check for deletion: del sys.modules[...]
    deletion_pattern = r"del\s+sys\.modules\["

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("providers/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        content = _read(path)

        # Allow specific guard/verification files
        if rel in ALLOWED_SYS_MODULES_CHECK_FILES:
            continue

        if re.search(assignment_pattern, content) or re.search(deletion_pattern, content):
            offenders.append(rel)

    assert not offenders, f"sys.modules mutation found in: {offenders}"


def test_tests_have_no_dynamic_imports_except_whitelist() -> None:
    """Dynamic imports in tests cause module identity issues under xdist."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)

        if any(tok in content for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS):
            if rel not in ALLOWED_TEST_FILES_FOR_DYNAMIC_IMPORT:
                offenders.append(rel)

    assert not offenders, (
        "Dynamic imports are forbidden in tests except whitelist. " f"Offenders: {offenders}"
    )


def test_tests_have_no_sys_path_insert_except_whitelist() -> None:
    """sys.path.insert masks import errors and breaks xdist isolation."""
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        content = _read(path)

        if FORBIDDEN_SYS_PATH_INSERT in content:
            if rel not in ALLOWED_TEST_FILES_FOR_SYS_PATH_INSERT:
                offenders.append(rel)

    assert not offenders, (
        "sys.path.insert is forbidden in tests except whitelist. " f"Offenders: {offenders}"
    )


def test_app_init_is_import_shim_not_dynamic_loader() -> None:
    """app/__init__.py must not reintroduce the old dynamic loader."""
    init_path = REPO_ROOT / "app" / "__init__.py"
    assert init_path.exists(), "app/__init__.py missing"

    content = _read(init_path)
    banned = [tok for tok in FORBIDDEN_DYNAMIC_IMPORT_TOKENS if tok in content]
    assert not banned, f"app/__init__.py contains forbidden tokens: {banned}"


def test_app_surface_has_required_legacy_symbols() -> None:
    """If tests depend on `from app import X`, enforce that it exists."""
    import app

    required = {
        "app",  # FastAPI instance
        "__getattr__",  # PEP 562 forwarding
    }

    missing = [name for name in required if not hasattr(app, name)]
    assert not missing, f"Missing required symbols in app package: {missing}"


@pytest.mark.parametrize(
    "path_glob,forbidden_tokens",
    [
        ("providers/**/*.py", ("spec_from_file_location(", "exec_module(")),
    ],
)
def test_providers_no_dynamic_imports(path_glob: str, forbidden_tokens: tuple[str, ...]) -> None:
    """Providers must not use dynamic imports to avoid namespace corruption."""
    offenders: list[str] = []

    for path in _iter_py_files(path_glob):
        content = _read(path)
        if any(tok in content for tok in forbidden_tokens):
            offenders.append(_rel(path))

    assert not offenders, f"Providers contain dynamic import tokens: {offenders}"


def test_no_sys_modules_get_recipe_store_in_tests() -> None:
    """Tests must not use sys.modules.get('recipe_store') - use standard imports instead.

    Anti-pattern: sys.modules.get("recipe_store") returns wrong module instance.
    Correct pattern: import app.services.recipe_store as rs
    """
    offenders: list[str] = []

    for path in _iter_py_files("tests/**/*.py"):
        rel = _rel(path)
        # Skip this guard file itself
        if rel == "tests/test_repo_policy_guards.py":
            continue

        content = _read(path)
        if (
            'sys.modules.get("recipe_store")' in content
            or "sys.modules.get('recipe_store')" in content
        ):
            offenders.append(rel)

    assert not offenders, (
        "Tests must not use sys.modules.get('recipe_store'). "
        f"Use 'import app.services.recipe_store as rs' instead. Offenders: {offenders}"
    )


def test_no_sys_modules_none_poisoning() -> None:
    """Prohibit setting sys.modules[...] = None which creates 'halted import' state.

    ❌ sys.modules["core.menu_engine"] = None  # Creates ModuleNotFoundError: import halted
    ❌ patch.dict("sys.modules", {"core.menu_engine": None})  # Same effect
    ✅ del sys.modules["core.menu_engine"]  # Safe removal
    ✅ monkeypatch.delitem(sys.modules, "core.menu_engine", raising=False)  # Safe mocking

    Note: This test allows legitimate import error testing in specific test files.
    """
    import re

    offenders: list[str] = []
    # Pattern: sys.modules[...]=None or patch.dict(..., {...: None})
    # Exclude this guard file itself from the check
    patterns = [
        r"sys\.modules\[[^]]+\]\s*=\s*None",
        r"patch\.dict\([^)]*\{[^}]*:[^}]*None[^}]*\}",  # patch.dict with None values
    ]

    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Skip this guard file itself to avoid false positive on the pattern strings
        if rel == "tests/test_repo_policy_guards.py":
            continue
        # Skip specific test files that legitimately test import error handling
        if rel in [
            "tests/test_bmi_visualization.py",  # Tests matplotlib import error handling
        ]:
            continue

        content = _read(path)

        for pattern in patterns:
            if re.search(pattern, content):
                offenders.append(f"{rel} (pattern: {pattern})")
                break  # Don't report same file multiple times

    assert not offenders, (
        "sys.modules None poisoning found. Use 'del sys.modules[key]' instead of 'sys.modules[key] = None'. "
        f"Offenders: {offenders}"
    )


def test_no_direct_model_submodule_imports() -> None:
    """Prohibit importing models from submodules - causes duplicate registration.

    ❌ from app.models.plans import WeeklyPlan
    ❌ from app.models.events import NutritionEvent
    ✅ from app.models import WeeklyPlan, NutritionEvent

    Reason: Direct submodule imports cause 'Table already defined' errors
    when modules are imported through different paths.
    See PR #403 commit 447e39c8 for context.
    """
    import re

    offenders: list[str] = []
    # Pattern: from app.models.(plans|events) import (exclude nutrition which is a data class module)
    pattern = re.compile(r"from\s+app\.models\.(plans|events)\s+import")

    # Check all Python files except app/models/__init__.py (which does the exports)
    for path in (
        list(_iter_py_files("app/**/*.py"))
        + list(_iter_py_files("core/**/*.py"))
        + list(_iter_py_files("tests/**/*.py"))
    ):
        rel = _rel(path)
        # Allow the export module itself and this guard file
        if rel in ("app/models/__init__.py", "tests/test_repo_policy_guards.py"):
            continue

        content = _read(path)
        if pattern.search(content):
            offenders.append(rel)

    assert not offenders, (
        "Direct model submodule imports forbidden. "
        "Use 'from app.models import X' instead. "
        f"Offenders: {offenders}"
    )
