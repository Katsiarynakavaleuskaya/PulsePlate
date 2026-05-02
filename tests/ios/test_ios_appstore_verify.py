"""Tests for the unified App Store submission readiness validator.

Verifies that:
- the validator script exists at the expected path
- the Makefile contains the ``ios-appstore-verify`` target
- the validator script passes on the current repo state
- the validator exposes all required check functions
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "release" / "check_ios_appstore_verify.py"
MAKEFILE = REPO_ROOT / "Makefile"

REQUIRED_CHECKS = [
    "check_release_base_url",
    "check_appicon_marketing",
    "check_privacy_manifest",
    "check_app_privacy_details",
    "check_permission_strings",
    "check_healthkit_readonly",
    "check_ai_wellness_consent",
    "check_reviewer_pack",
    "check_screenshot_policy",
    "check_storekit_pricing_truth",
]


def test_validator_script_exists() -> None:
    """Validator script must exist at the canonical path."""
    assert VALIDATOR_SCRIPT.exists(), f"Missing validator script: {VALIDATOR_SCRIPT}"
    assert VALIDATOR_SCRIPT.stat().st_size > 0, "Validator script is empty"


def test_makefile_target_exists() -> None:
    """Makefile must contain the ios-appstore-verify target."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "ios-appstore-verify:" in content, "Makefile missing ios-appstore-verify target"
    # Target must also be in .PHONY.
    assert (
        "ios-appstore-verify" in content.split(".PHONY:")[-1]
    ), "ios-appstore-verify not declared in .PHONY"


def test_validator_script_passes() -> None:
    """Validator script must exit 0 on the current repo state."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_SCRIPT)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Validator failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_validator_has_required_checks() -> None:
    """Validator script must define all required check functions."""
    content = VALIDATOR_SCRIPT.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_CHECKS if f"def {name}(" not in content]
    assert not missing, f"Validator missing check functions: {missing}"


def test_validator_registers_all_checks() -> None:
    """ALL_CHECKS list must reference every required check function."""
    content = VALIDATOR_SCRIPT.read_text(encoding="utf-8")
    # Find the ALL_CHECKS list block.
    assert "ALL_CHECKS" in content, "Validator missing ALL_CHECKS list"
    for name in REQUIRED_CHECKS:
        assert name in content.split("ALL_CHECKS")[1], f"Check {name} not registered in ALL_CHECKS"
