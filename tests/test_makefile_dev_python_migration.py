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
import subprocess
import os
from shutil import which
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"


def _makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def _make_binary(name: str) -> str:
    binary = which(name)
    assert binary is not None, f"Required executable '{name}' must be on PATH"
    return binary


def _clean_make_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("COMPOSE_PROJECT_NAME", None)
    env.pop("COMPOSE_PROJECT_NAME_SUFFIX", None)
    return env


def _expected_compose_project_name(cwd: Path) -> str:
    """Compute the Makefile's default compose project name formula for a worktree."""
    shell = _make_binary("sh")
    result = subprocess.run(
        ["sh", "-lc", "pwd -P | cksum | cut -d' ' -f1"],
        executable=shell,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        env=_clean_make_env(),
    )
    return f"pulseplate-{result.stdout.strip()}"


def _make_compose_project_name(cwd: Path) -> str:
    """Evaluate COMPOSE_PROJECT_NAME in a temporary make invocation from a worktree."""
    make_binary = _make_binary("make")
    probe_makefile = cwd / "probe.mk"
    worktree_makefile = cwd / "Makefile"
    if not worktree_makefile.exists():
        worktree_makefile.symlink_to(MAKEFILE)
    probe_makefile.write_text(
        "\n".join(
            [
                "include Makefile",
                "",
                ".PHONY: print-compose",
                "print-compose:",
                "\t@printf '%s\\n' \"$(COMPOSE_PROJECT_NAME)\"",
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            make_binary,
            "-s",
            "-f",
            str(probe_makefile),
            "-C",
            str(cwd),
            "print-compose",
        ],
        capture_output=True,
        text=True,
        check=True,
        env=_clean_make_env(),
    )
    return result.stdout.strip()


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


def test_compose_project_name_is_safe_and_deterministic() -> None:
    """Dev-container project names must use safe shell eval + deterministic worktree uniqueness."""
    text = _makefile_text()

    assert (
        "COMPOSE_PROJECT_NAME_SUFFIX" in text
    ), "Makefile should define COMPOSE_PROJECT_NAME_SUFFIX"
    pattern = re.compile(r"^COMPOSE_PROJECT_NAME\s+\?=\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    assert match, "COMPOSE_PROJECT_NAME must be defined"

    assignment = match.group(1)
    assert (
        "COMPOSE_PROJECT_NAME_SUFFIX" in assignment
    ), "COMPOSE_PROJECT_NAME default must use suffix helper variable"
    assert "$(CURDIR)" not in assignment, "COMPOSE_PROJECT_NAME must not interpolate CURDIR"
    assert re.fullmatch(
        r"pulseplate-\$\((?:(?!\)).)*COMPOSE_PROJECT_NAME_SUFFIX(?:(?!\)).)*\)", assignment
    ), "COMPOSE_PROJECT_NAME default must be derived from COMPOSE_PROJECT_NAME_SUFFIX"
    assert assignment != "pulseplate", "COMPOSE_PROJECT_NAME must not be globally static"


def test_compose_project_name_default_override_semantics() -> None:
    """Preserve Make override semantics for COMPOSE_PROJECT_NAME."""
    text = _makefile_text()
    match = re.search(r"^COMPOSE_PROJECT_NAME\s+\?=", text, re.MULTILINE)
    assert match is not None, "COMPOSE_PROJECT_NAME must use conditional assignment"
    assert (
        match.group(0).strip().startswith("COMPOSE_PROJECT_NAME ?=")
    ), "Makefile must use '?=' assignment for environment override support"


def test_devcontainer_dc_targets_are_intact() -> None:
    """Devcontainer targets must still pass compose project name by environment."""
    text = _makefile_text()
    assert "export COMPOSE_PROJECT_NAME" in text

    for target_name, expected_fragment in [
        (
            "dc-up",
            'docker compose -f "$(DEVCONTAINER_COMPOSE)" up -d --build',
        ),
        (
            "dc-shell",
            'docker compose -f "$(DEVCONTAINER_COMPOSE)" exec devcontainer bash',
        ),
        (
            "dc-down",
            'docker compose -f "$(DEVCONTAINER_COMPOSE)" down',
        ),
        (
            "dc-smoke",
            'docker compose -f "$(DEVCONTAINER_COMPOSE)" run --rm devcontainer',
        ),
    ]:
        assert (
            expected_fragment in text
        ), f"{target_name} must remain intact and forward COMPOSE_PROJECT_NAME"


def test_compose_project_name_varies_between_worktrees() -> None:
    """Different worktrees should evaluate to different compose project names."""
    with TemporaryDirectory() as first_dir, TemporaryDirectory() as second_dir:
        first_worktree = Path(first_dir)
        second_worktree = Path(second_dir)

        first = _make_compose_project_name(first_worktree)
        second = _make_compose_project_name(second_worktree)
        expected_first = _expected_compose_project_name(first_worktree)
        expected_second = _expected_compose_project_name(second_worktree)

        assert first == expected_first
        assert second == expected_second
        assert re.fullmatch(r"pulseplate-[0-9]+", first) is not None
        assert re.fullmatch(r"pulseplate-[0-9]+", second) is not None
        assert expected_first != expected_second


def test_compose_project_name_stable_per_worktree() -> None:
    """A single worktree should keep the same deterministic project name across runs."""
    with TemporaryDirectory() as worktree:
        name_one = _make_compose_project_name(Path(worktree))
        name_two = _make_compose_project_name(Path(worktree))
        assert name_one == name_two


def test_compose_project_name_safe_with_special_directory_chars() -> None:
    """Special directory characters must not alter command-evaluation semantics."""
    with TemporaryDirectory() as root:
        worktree = Path(root) / "sp ec;ial $() `chars` dir"
        worktree.mkdir(parents=True, exist_ok=True)
        value = _make_compose_project_name(worktree)
        assert re.fullmatch(r"pulseplate-[0-9]+", value) is not None


def test_compose_project_name_does_not_execute_path_text() -> None:
    """A malicious-looking directory name should not execute shell payloads."""
    with TemporaryDirectory() as root:
        root_path = Path(root)
        injection_marker = root_path / "injection_marker"
        worktree = root_path / f"pwn_$(touch {injection_marker.name})"
        worktree.mkdir(parents=True, exist_ok=True)
        value = _make_compose_project_name(worktree)
        assert re.fullmatch(r"pulseplate-[0-9]+", value) is not None
        assert not injection_marker.exists()


def test_dc_targets_dont_execute_injected_override() -> None:
    """User overrides for COMPOSE_PROJECT_NAME must remain data, never shell code."""
    make_binary = _make_binary("make")
    with TemporaryDirectory() as root:
        root_path = Path(root)
        marker = root_path / "injection_marker"
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = f"pwn_$(touch {marker})"

        result = subprocess.run(
            [
                make_binary,
                "-s",
                "-n",
                "-C",
                str(REPO_ROOT),
                "dc-up",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "touch" not in result.stdout
