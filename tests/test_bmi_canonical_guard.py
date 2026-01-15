# -*- coding: utf-8 -*-
"""
BMI Canonical Guard Tests

RU: Тесты-охранники для инварианта "One BMI Engine".
EN: Guard tests for "One BMI Engine" invariant.

These tests enforce the architectural invariant:
    "One BMI Engine must be the sole calculation path for all BMI-related computations."

See: docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md
See: docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Get repo root (same pattern as test_no_bmi_math_outside_core.py)
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_legacy_bmi_imports_in_core_bmi() -> None:
    """Guard: core/bmi/ must not import from bmi_core (legacy).

    RU: Проверяет, что модули в core/bmi/ не импортируют из bmi_core.py (legacy).
    EN: Ensures modules in core/bmi/ do not import from bmi_core.py (legacy).

    This guard prevents regression of the architectural invariant.
    """
    core_bmi_dir = REPO_ROOT / "core" / "bmi"
    if not core_bmi_dir.exists():
        pytest.skip("core/bmi/ directory not found")

    violations: list[tuple[str, int, str]] = []

    for py_file in core_bmi_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))

            for node in ast.walk(tree):
                # Check ImportFrom: from bmi_core import ...
                if isinstance(node, ast.ImportFrom):
                    if node.module == "bmi_core":
                        violations.append(
                            (
                                str(py_file.relative_to(REPO_ROOT)),
                                node.lineno or 0,
                                "from bmi_core import ...",
                            )
                        )
                # Check Import: import bmi_core
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "bmi_core":
                            violations.append(
                                (
                                    str(py_file.relative_to(REPO_ROOT)),
                                    node.lineno or 0,
                                    "import bmi_core",
                                )
                            )
        except (SyntaxError, UnicodeDecodeError) as e:
            pytest.fail(f"Failed to parse {py_file}: {e}")

    assert not violations, (
        f"Legacy bmi_core imports found in core/bmi/: {violations}\n"
        f"All BMI calculations must use core/bmi/engine (canonical).\n"
        f"See: docs/audit/BACKEND_P0_REMEDIATION_PLAN.md"
    )


def test_bmi_result_structure_consistency() -> None:
    """Guard: BMICalculateResult must always have all required fields.

    RU: Проверяет, что BMICalculateResult всегда содержит все обязательные поля.
    EN: Ensures BMICalculateResult always contains all required fields.

    This guard prevents partial result assembly (root cause of "undefined").
    """
    import inspect

    try:
        from core.bmi.engine import BMICalculateResult, calculate_bmi_result
    except ImportError:
        pytest.skip("core.bmi.engine not available")

    # Get function signature to filter valid kwargs
    sig = inspect.signature(calculate_bmi_result)
    valid_params = set(sig.parameters.keys())

    # Test cases covering various scenarios
    test_cases = [
        {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "waist_cm": None,
            "lang": "en",
        },
        {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 25,
            "gender": "female",
            "pregnant": True,
            "athlete": False,
            "waist_cm": 80.0,
            "lang": "ru",
        },
        {
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "age": 45,
            "gender": "male",
            "pregnant": False,
            "athlete": True,
            "waist_cm": 95.0,
            "lang": "en",
        },
    ]

    required_fields = {
        "bmi",
        "category",
        "group",
        "group_display",
        "interpretation",
        "wht_ratio",
        "waist_risk",
    }

    for case in test_cases:
        # Filter kwargs to only include valid parameters
        filtered_case = {k: v for k, v in case.items() if k in valid_params}

        result = calculate_bmi_result(**filtered_case)

        # Verify all required fields are present
        missing_fields = required_fields - set(dir(result))
        assert not missing_fields, (
            f"BMICalculateResult missing required fields: {missing_fields}\n"
            f"Test case: {case}\n"
            f"Result: {result}"
        )

        # Verify critical fields are not None (when applicable)
        assert result.bmi is not None, f"BMI is None for case: {case}"
        assert result.group is not None, f"Group is None for case: {case}"
        assert result.group_display is not None, f"Group display is None for case: {case}"

        # Category may be None for certain groups (too_young, child, teen, pregnant)
        # This is expected behavior, so we don't assert it here

        # Verify result is instance of BMICalculateResult
        assert isinstance(
            result, BMICalculateResult
        ), f"Result is not BMICalculateResult instance: {type(result)}"


def test_single_canonical_extras_module() -> None:
    """Guard: Only one canonical extras module exists (or clear purpose for each).

    RU: Проверяет, что существует только один канонический модуль extras, или у каждого есть явное назначение.
    EN: Ensures only one canonical extras module exists, or each has clear documented purpose.

    This guard prevents duplicate BMI extras modules.
    """
    core_dir = REPO_ROOT / "core"
    if not core_dir.exists():
        pytest.skip("core/ directory not found")

    extras_modules = list(core_dir.glob("bmi_extras*.py"))

    if len(extras_modules) == 0:
        pytest.skip("No bmi_extras modules found (may be consolidated)")

    if len(extras_modules) == 1:
        # Single module is fine
        return

    # Multiple modules: check if purpose is documented
    undocumented_modules: list[str] = []

    for module in extras_modules:
        content = module.read_text(encoding="utf-8")
        content_lower = content.lower()

        # Check for canonical marker or purpose documentation
        has_canonical = "canonical" in content_lower
        has_purpose = "purpose" in content_lower or "назначение" in content_lower
        has_docstring = (
            '"""' in content[:500] or "'''" in content[:500]
        )  # Check for docstring in first 500 chars

        if not (has_canonical or (has_purpose and has_docstring)):
            undocumented_modules.append(str(module.relative_to(REPO_ROOT)))

    if undocumented_modules:
        pytest.fail(
            f"Multiple bmi_extras modules found without clear purpose: {undocumented_modules}\n"
            f"Either consolidate into one canonical module, or document purpose of each.\n"
            f"See: docs/audit/BACKEND_P0_REMEDIATION_PLAN.md"
        )


def test_engine_metadata_accuracy() -> None:
    """Guard: Engine docstring must accurately reflect implementation status.

    RU: Проверяет, что docstring engine не говорит 'stub', если реализация полная.
    EN: Ensures engine docstring does not say 'stub' if implementation is complete.

    This guard prevents metadata confusion that encourages bypassing canonical path.
    """
    try:
        from core.bmi.engine import calculate_bmi_result
        import core.bmi.engine as engine_module
    except ImportError:
        pytest.skip("core.bmi.engine not available")

    # Get module docstring
    module_doc = engine_module.__doc__ or ""

    # Check if marked as stub
    if "stub" in module_doc.lower():
        # Verify if it's actually a stub (heuristic: check if core functions exist)
        has_core_functions = all(
            hasattr(engine_module, func)
            for func in ["calculate_bmi_result", "_compute_bmi", "_compute_wht_ratio"]
        )

        if has_core_functions:
            pytest.fail(
                "Engine marked as 'stub' but appears functionally complete.\n"
                "Update docstring to reflect canonical status.\n"
                "See: docs/audit/BACKEND_P0_REMEDIATION_PLAN.md"
            )


def test_no_bmi_calculation_outside_engine() -> None:
    """Guard: No BMI calculation logic outside core/bmi/engine.

    RU: Проверяет, что расчёт BMI не происходит вне core/bmi/engine.
    EN: Ensures BMI calculation does not occur outside core/bmi/engine.

    This guard extends test_no_bmi_math_outside_core.py to be more specific.
    Focuses on function definitions and actual calculations, not docstrings.
    """
    import re

    # Patterns for actual BMI calculation code (not docstrings/comments)
    forbidden_patterns = [
        r"def\s+.*bmi.*\(.*weight.*height",  # Function definitions
        r"^\s*bmi\s*=\s*weight.*height",  # Variable assignments (not in strings)
        r"^\s*.*=\s*weight.*/\s*\(.*height.*\*\*?\s*2",  # Direct calculations
    ]

    # Whitelist: files where BMI formula mention is OK (docstrings, schemas, etc.)
    # Note: We whitelist paths/patterns, not specific files, to avoid hiding violations
    whitelist_patterns = [
        r"schemas/",  # Schema descriptions (documentation only)
        r"docs/",  # Documentation
        r"test.*\.py$",  # Test files
        r"bmi_visualization\.py$",  # Visualization (temporary, tracked in PR-456)
        # Note: bmi_pro.py is NOT whitelisted - it should use engine (violation to be fixed)
        # Note: nutrition_bayesian_analyzer.py is NOT whitelisted - if it has BMI calculation,
        #       it should use engine. Docstring-only mentions are filtered by line-level checks.
    ]

    violations: list[tuple[str, int, str]] = []

    # Check app/ and core/ (excluding core/bmi/)
    for directory in [REPO_ROOT / "app", REPO_ROOT / "core"]:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            # Skip core/bmi/ (allowed)
            if "core/bmi" in str(py_file):
                continue

            # Skip tests
            if "test" in str(py_file):
                continue

            # Check whitelist
            py_file_str = str(py_file.relative_to(REPO_ROOT))
            if any(
                re.search(pattern, py_file_str, re.IGNORECASE) for pattern in whitelist_patterns
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Skip docstrings and comments
                    stripped = line.strip()
                    if (
                        stripped.startswith('"""')
                        or stripped.startswith("'''")
                        or stripped.startswith("#")
                    ):
                        continue

                    # Skip lines that are clearly docstrings (contained in triple quotes)
                    # Simple heuristic: if line contains formula but is in quotes context, skip
                    if '"""' in line or "'''" in line:
                        # Check if this is a docstring line (contains description text)
                        if "description" in line.lower() or "doc" in line.lower():
                            continue

                    # Skip string literals (formula in string, not actual calculation)
                    # Check if line is assignment to string or in string context
                    if re.search(r'["\'].*bmi.*["\']', line, re.IGNORECASE):
                        # Formula is in string literal, not actual code
                        continue

                    for pattern in forbidden_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append((py_file_str, line_num, line.strip()))
            except (UnicodeDecodeError, Exception):
                # Skip files we can't read
                continue

    # Filter out known acceptable cases
    # app/routers/bmi_pro.py has calc_bmi helper - this is a violation we want to catch
    # But we should be more specific about what we're checking

    assert not violations, (
        f"BMI calculation logic found outside core/bmi/engine: {violations}\n"
        f"All BMI calculations must use core/bmi/engine (canonical).\n"
        f"See: docs/audit/BACKEND_P0_REMEDIATION_PLAN.md\n"
        f"Note: This guard may flag some false positives (docstrings, etc.). Review violations carefully."
    )
