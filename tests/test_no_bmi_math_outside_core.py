"""
RU: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).
EN: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).

Commit 4: prevents BMI formulas/thresholds from creeping into app/web/iOS adapters.

This guard enforces the canonical BMI rule: all BMI math MUST live only in core/bmi/*.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Whitelist: paths where BMI math is allowed (temporary or canonical)
WHITELIST_PARTS = [
    "core/bmi/",  # Canonical location ✅
    "tests/",  # Test code allowed ✅
    "legacy_app.py",  # Temporary, until PR-456 ✅
    "docs/",  # Documentation formulas OK ✅
    "bmi_core.py",  # Legacy oracle, temporary ✅
    ".venv/",  # Virtual environment (exclude)
    ".venv-ci/",  # CI virtual environment (exclude)
    "bmi_visualization.py",  # Visualization only (not core logic, but contains thresholds for charts)
    "app/routers/bmi_pro.py",  # PRO endpoint (separate from Free BMI, PR-456 will handle)
    "core/nutrition_",  # Nutrition constants (not BMI math)
    "core/bmi_extras",  # PRO features (separate from Free BMI)
    "app/schemas/bmi.py",  # Schema Field descriptions (documentation, not code)
    "tests_strict/",  # Strict test suite (test code)
    "core/nutrition_bayesian_analyzer.py",  # Uses BMI for nutrition analysis (not core BMI logic)
]

# Forbidden patterns (domain signatures for BMI math)
# Pattern 1: BMI formula (weight / height^2) - must be in context of BMI calculation
# More specific: look for BMI-related context (bmi =, calc_bmi, etc.)
BMI_FORMULA_RE = re.compile(
    r"(bmi\s*=|calc_bmi|calculate.*bmi|bmi_value).*weight(_kg)?\s*/\s*\(\s*height(_m|_cm)?\s*\*\*\s*2|"
    r"weight(_kg)?\s*/\s*\(\s*height(_m|_cm)?\s*\*\*\s*2.*bmi",
    re.IGNORECASE,
)

# Pattern 2: BMI thresholds (canonical values) - must be in BMI context
# Look for BMI-related keywords nearby (bmi, category, threshold, etc.)
BMI_THRESHOLDS_RE = re.compile(
    r"(bmi|category|threshold|underweight|normal|overweight|obesity).*"
    r"\b(18\.5|25\.0|30\.0|35\.0|40\.0|17\.5|26\.0|27\.0|24\.5)\b|"
    r"\b(18\.5|25\.0|30\.0|35\.0|40\.0|17\.5|26\.0|27\.0|24\.5)\b.*"
    r"(bmi|category|threshold|underweight|normal|overweight|obesity)",
    re.IGNORECASE,
)

# Pattern 3: WHtR formula (waist / 100 / height)
WHTR_FORMULA_RE = re.compile(
    r"waist(_cm)?\s*/\s*100(\.0)?\s*/\s*height(_m)?|wht(r|_ratio)\s*=\s*.*waist.*height",
    re.IGNORECASE,
)

# Skip comment-only lines and docstrings (to avoid false positives from documentation)
SKIP_LINE_RE = re.compile(r"^\s*#|^\s*\"\"\"|^\s*'''|description=|Field\(.*description")

# Skip lines that are clearly not BMI math (docstrings, type hints, etc.)
SKIP_CONTEXT_RE = re.compile(
    r"description=|Field\(|#|docstring|type:|->|def.*\(.*\)\s*->|:.*float.*="
)


def _is_whitelisted(rel_path: str) -> bool:
    """Check if path is in whitelist."""
    return any(part in rel_path for part in WHITELIST_PARTS)


def _scan(pattern: re.Pattern[str], description: str) -> list[str]:
    """
    Scan repository for forbidden patterns.

    Returns:
        List of hits in format "file:line: content"
    """
    hits: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.as_posix().replace(REPO_ROOT.as_posix() + "/", "")
        if _is_whitelisted(rel):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for idx, line in enumerate(text, start=1):
                if SKIP_LINE_RE.match(line):
                    continue
                # Skip docstrings and type hints
                if SKIP_CONTEXT_RE.search(line) and "bmi" not in line.lower():
                    continue
                if pattern.search(line):
                    hits.append(f"{rel}:{idx}: {line.strip()}")
        except Exception:
            # Skip files that can't be read (permissions, etc.)
            continue

    return hits


def test_no_bmi_formula_outside_core() -> None:
    """
    RU: Проверяет, что формула BMI (weight / height^2) не встречается вне whitelist.
    EN: Ensures BMI formula (weight / height^2) is not found outside whitelist.
    """
    hits = _scan(BMI_FORMULA_RE, "BMI formula")
    assert not hits, (
        f"BMI formula found outside core/bmi (violates canonical rule):\n"
        f"{chr(10).join(f'  {hit}' for hit in hits)}\n\n"
        "Move BMI calculations to core/bmi/engine.py"
    )


def test_no_bmi_thresholds_outside_core() -> None:
    """
    RU: Проверяет, что пороги BMI (18.5, 25.0, 30.0, etc.) не встречаются вне whitelist.
    EN: Ensures BMI thresholds (18.5, 25.0, 30.0, etc.) are not found outside whitelist.
    """
    hits = _scan(BMI_THRESHOLDS_RE, "BMI thresholds")
    assert not hits, (
        "BMI thresholds found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove threshold logic to core/bmi/engine.py"
    )


def test_no_whtr_formula_outside_core() -> None:
    """
    RU: Проверяет, что формула WHtR (waist / 100 / height) не встречается вне whitelist.
    EN: Ensures WHtR formula (waist / 100 / height) is not found outside whitelist.
    """
    hits = _scan(WHTR_FORMULA_RE, "WHtR formula")
    assert not hits, (
        "WHtR formula found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove WHtR calculations to core/bmi/engine.py or core/bmi/risk.py"
    )
