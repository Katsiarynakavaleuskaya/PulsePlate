"""Guard tests for Makefile DEV_PYTHON migration.

Ensures that:
- DEV_PYTHON is defined with correct fallback semantics
- Generic developer targets use DEV_PYTHON (not VENV_PYTHON)
- No activate-then-pytest patterns remain in generic targets
- make venv and VENV_PYTHON remain available as fallback
- OPENAPI_PYTHON is removed (subsumed by DEV_PYTHON)
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"


def _makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# DEV_PYTHON definition and fallback semantics
# ---------------------------------------------------------------------------


def test_makefile_defines_dev_python_fallback() -> None:
    """DEV_PYTHON must be defined with venv-preferred, python3-fallback semantics."""
    text = _makefile_text()

    assert "VENV_PYTHON ?= .venv/bin/python" in text, "VENV_PYTHON definition must be preserved"
    assert "DEV_PYTHON ?=" in text, "DEV_PYTHON must be defined"
    assert (
        "$(wildcard $(VENV_PYTHON))" in text
    ), "DEV_PYTHON must use wildcard to detect .venv presence"
    assert "python3" in text, "DEV_PYTHON must fall back to python3"


# ---------------------------------------------------------------------------
# Generic targets must use DEV_PYTHON
# ---------------------------------------------------------------------------

# Targets that have been migrated to DEV_PYTHON
_GENERIC_DEV_PYTHON_TOKENS = [
    "$(DEV_PYTHON) -m pytest",
    "$(DEV_PYTHON) -m coverage",
    "$(DEV_PYTHON) -m mypy",
    "$(DEV_PYTHON) -m flake8",
    "$(DEV_PYTHON) -m diff_cover",
]


def test_generic_python_targets_use_dev_python() -> None:
    """Generic test/coverage/typecheck/lint targets must use DEV_PYTHON."""
    text = _makefile_text()

    for token in _GENERIC_DEV_PYTHON_TOKENS:
        assert token in text, f"Makefile must contain '{token}'"


# ---------------------------------------------------------------------------
# No activate-then-pytest in generic targets
# ---------------------------------------------------------------------------

_FORBIDDEN_ACTIVATE_PATTERNS = [
    r"source \.venv/bin/activate && pytest",
    r"\. \.venv/bin/activate && pytest",
    r"source \.venv/bin/activate && coverage",
    r"\. \.venv/bin/activate && coverage",
    r"source \.venv/bin/activate && mypy",
    r"\. \.venv/bin/activate && mypy",
    r"source \.venv/bin/activate && flake8",
    r"\. \.venv/bin/activate && flake8",
]


def test_generic_targets_do_not_source_venv_activation() -> None:
    """Generic targets must not use 'source .venv/bin/activate && ...' patterns."""
    text = _makefile_text()

    for pattern in _FORBIDDEN_ACTIVATE_PATTERNS:
        match = re.search(pattern, text)
        assert match is None, (
            f"Forbidden pattern found in Makefile: {pattern!r} "
            f"at position {match.start() if match else '?'}"
        )


# ---------------------------------------------------------------------------
# Venv fallback preserved
# ---------------------------------------------------------------------------


def test_make_venv_fallback_remains_available() -> None:
    """make venv target must remain as host-native fallback."""
    text = _makefile_text()

    assert (
        re.search(r"^venv:", text, re.MULTILINE) is not None
    ), "Makefile must preserve 'venv:' target"
    assert "VENV_PYTHON ?=" in text, "VENV_PYTHON definition must remain"
    assert ".venv" in text, "References to .venv must remain for fallback"


# ---------------------------------------------------------------------------
# OPENAPI_PYTHON removed
# ---------------------------------------------------------------------------


def test_openapi_python_variable_removed() -> None:
    """OPENAPI_PYTHON variable is subsumed by DEV_PYTHON and must not be defined."""
    text = _makefile_text()

    assert "OPENAPI_PYTHON ?=" not in text, (
        "OPENAPI_PYTHON variable definition must be removed "
        "(DEV_PYTHON subsumes its functionality)"
    )


# ---------------------------------------------------------------------------
# verify-env stays on VENV_PYTHON (venv-specific target)
# ---------------------------------------------------------------------------


def test_verify_env_uses_venv_python() -> None:
    """verify-env is a venv health check and must stay on VENV_PYTHON."""
    text = _makefile_text()

    # Find the verify-env recipe
    pattern = re.compile(r"(?m)^verify-env:.*\n(?P<body>(?:\t[^\n]*\n)+)")
    match = pattern.search(text)
    assert match, "verify-env target must exist"

    body = match.group("body")
    assert "$(VENV_PYTHON)" in body, "verify-env must use VENV_PYTHON (it validates venv health)"


# ---------------------------------------------------------------------------
# openapi target uses DEV_PYTHON
# ---------------------------------------------------------------------------


def test_openapi_target_uses_dev_python() -> None:
    """openapi target must use DEV_PYTHON after OPENAPI_PYTHON removal."""
    text = _makefile_text()

    # Find the openapi recipe
    pattern = re.compile(r"(?m)^openapi:.*\n(?P<body>(?:\t[^\n]*\n)+)")
    match = pattern.search(text)
    assert match, "openapi target must exist"

    body = match.group("body")
    assert "$(DEV_PYTHON)" in body, "openapi target must use DEV_PYTHON"
