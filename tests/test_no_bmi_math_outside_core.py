"""
RU: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).
EN: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).

Commit 4: prevents BMI formulas/thresholds from creeping into app/web/iOS adapters.

This guard enforces the canonical BMI rule: all BMI math MUST live only in core/bmi/*.
"""

from __future__ import annotations

import re
import os
import sys
from pathlib import Path
from typing import Final

import pytest


_DEBUG_GUARD: Final[bool] = bool(os.environ.get("REPO_POLICY_GUARD_DEBUG"))

REPO_ROOT = Path(__file__).resolve().parents[1]

# Whitelist: paths where BMI math is allowed (temporary or canonical)
#
# POLICY: Each whitelist entry MUST have:
#   - Comment explaining WHY it's allowed
#   - Reference to PR/issue tracking cleanup (if temporary)
#   - No silent additions (always document rationale)
#
WHITELIST_PARTS = [
    "core/bmi/",  # Canonical location ✅ (permanent)
    "tests/",  # Test code allowed ✅ (permanent)
    # NOTE: legacy_app.py removed from whitelist (PR-502) — now uses core proxies only
    "docs/",  # Documentation formulas OK ✅ (permanent)
    "bmi_core.py",  # TEMP: legacy oracle for golden parity tests (PR-455 Commit 4)
    ".venv/",  # Virtual environment (exclude from scanning)
    ".venv-ci/",  # CI virtual environment (exclude from scanning)
    # TEMP: Visualization thresholds for charts (not core BMI logic)
    # Tracked in PR-456: migrate to use core/bmi/engine.py thresholds
    "bmi_visualization.py",
    # TEMP: PRO endpoint (separate from Free BMI, uses local calc_bmi helper)
    # Tracked in PR-456: migrate to use core/bmi/engine.py
    "app/routers/bmi_pro.py",
    "core/nutrition_",  # Nutrition constants (not BMI math, different domain)
    # NOTE: core/bmi_extras is whitelisted for BMI calculations, but thresholds must come from core/bmi/risk
    # Guard test will still catch hardcoded thresholds (18.5/25/30/0.95/0.80) even in whitelisted files
    "core/bmi_extras",  # PRO features (separate from Free BMI canonical engine)
    "app/schemas/bmi.py",  # Schema Field descriptions (documentation, not code)
    "tests_strict/",  # Strict test suite (test code)
    # Uses BMI for nutrition analysis context (not core BMI calculation logic)
    "core/nutrition_bayesian_analyzer.py",
    # NOTE: bodyfat.py NOT whitelisted — guard regex excludes 94.42 via negative lookahead
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
# Includes 24.9 (healthy range max) per PR-502 enforcement
# NOTE: Also detects WHR thresholds (0.95/0.80) outside core/bmi/risk.py
BMI_THRESHOLDS_RE = re.compile(
    r"(bmi|category|threshold|underweight|normal|overweight|obesity|healthy|whr|waist.*hip).*"
    r"\b(18\.5|24\.9|25\.0|30\.0|35\.0|40\.0|17\.5|26\.0|27\.0|24\.5|0\.95|0\.80)\b|"
    r"\b(18\.5|24\.9|25\.0|30\.0|35\.0|40\.0|17\.5|26\.0|27\.0|24\.5|0\.95|0\.80)\b.*"
    r"(bmi|category|threshold|underweight|normal|overweight|obesity|healthy|whr|waist.*hip)",
    re.IGNORECASE,
)

# Pattern 3: WHtR formula (waist / 100 / height)
WHTR_FORMULA_RE = re.compile(
    r"waist(_cm)?\s*/\s*100(\.0)?\s*/\s*height(_m)?|wht(r|_ratio)\s*=\s*.*waist.*height",
    re.IGNORECASE,
)

# Pattern 4: Waist circumference thresholds (WHO/clinical values) - PR-502 enforcement
# Detects hardcoded waist risk thresholds (80/88 female, 94/102 male)
# Uses negative lookahead (?!\.) to avoid matching 94.42 (US Navy bodyfat constant)
WAIST_THRESHOLDS_RE = re.compile(
    r"(waist|risk|warn|high|threshold|central|abdominal).*"
    r"\b(80|88|94|102)(?!\.)\b|"
    r"\b(80|88|94|102)(?!\.)\b.*"
    r"(waist|risk|warn|high|threshold|central|abdominal)",
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
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError:
            # Path not relative to REPO_ROOT (shouldn't happen, but defensive)
            continue
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
        except (OSError, UnicodeDecodeError) as e:
            # Skip files that can't be read (permissions, etc.).
            if _DEBUG_GUARD:
                print(
                    f"REPO_POLICY_GUARD_DEBUG: skip unreadable file {rel}: {e!r}", file=sys.stderr
                )
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


def test_no_waist_thresholds_outside_core() -> None:
    """
    RU: Проверяет, что пороги талии (80/88/94/102) не встречаются вне whitelist.
    EN: Ensures waist thresholds (80/88/94/102) are not found outside whitelist.

    PR-502: Prevents hardcoded waist risk constants from creeping back into legacy_app.py.
    """
    hits = _scan(WAIST_THRESHOLDS_RE, "waist thresholds")
    assert not hits, (
        "Waist thresholds found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove waist threshold logic to core/bmi/risk.py"
    )
