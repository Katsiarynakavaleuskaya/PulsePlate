# -*- coding: utf-8 -*-
"""
RU: Guard-тесты для предотвращения возврата legacy BMI helpers в request-path.
EN: Guard tests to prevent legacy BMI helpers from returning to request-path.

PR-457 Commit 4: Enforce that request-path endpoints do not use legacy BMI helpers.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Request-path files that must not use legacy BMI helpers
REQUEST_PATH_FILES = [
    Path("legacy_app.py"),
    Path("app/routers/bmi.py"),
]

# Forbidden import modules
FORBIDDEN_IMPORT_MODULES = {"bmi_core"}

# Forbidden import-from modules
FORBIDDEN_IMPORT_FROM = {"bmi_core"}

# Forbidden function call names
FORBIDDEN_CALL_NAMES = {"calc_bmi", "normalize_flags", "bmi_category", "waist_risk"}


def _repo_root() -> Path:
    """Return repository root directory."""
    return Path(__file__).resolve().parents[1]


def _parse(path: Path) -> ast.Module:
    """Parse Python source file into AST Module."""
    full_path = _repo_root() / path
    src = full_path.read_text(encoding="utf-8")
    return ast.parse(src, filename=str(full_path))


def test_no_legacy_bmi_imports_in_request_path() -> None:
    """
    RU: Проверка, что request-path файлы не импортируют legacy BMI helpers.
    EN: Verify request-path files do not import legacy BMI helpers.
    """
    violations: list[str] = []

    for path in REQUEST_PATH_FILES:
        tree = _parse(path)

        for node in ast.walk(tree):
            # Check: import bmi_core
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_MODULES:
                        violations.append(
                            f"Forbidden import '{alias.name}' in {path} " f"(line {node.lineno})"
                        )

            # Check: from bmi_core import ...
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in FORBIDDEN_IMPORT_FROM:
                    violations.append(
                        f"Forbidden import-from '{mod}' in {path} " f"(line {node.lineno})"
                    )

    assert not violations, "Legacy BMI helper imports found in request-path files:\n" + "\n".join(
        violations
    )


def test_no_legacy_bmi_calls_in_request_path() -> None:
    """
    RU: Проверка, что request-path файлы не вызывают legacy BMI helpers.
    EN: Verify request-path files do not call legacy BMI helpers.
    """
    violations: list[str] = []

    for path in REQUEST_PATH_FILES:
        tree = _parse(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func

                # Check: calc_bmi(...) - direct call
                if isinstance(fn, ast.Name):
                    if fn.id in FORBIDDEN_CALL_NAMES:
                        violations.append(
                            f"Forbidden call '{fn.id}()' in {path} " f"(line {node.lineno})"
                        )

                # Check: legacy_app.calc_bmi(...) or bmi_core.bmi_category(...)
                if isinstance(fn, ast.Attribute):
                    if fn.attr in FORBIDDEN_CALL_NAMES:
                        violations.append(
                            f"Forbidden call '{fn.attr}()' via attribute in {path} "
                            f"(line {node.lineno})"
                        )

    assert not violations, "Legacy BMI helper calls found in request-path files:\n" + "\n".join(
        violations
    )
