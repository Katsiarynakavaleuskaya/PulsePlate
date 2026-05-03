"""Guard tests for the devcontainer CI smoke workflow.

These tests verify that:
- Workflow and smoke script files exist
- Workflow is path-scoped and supports manual dispatch
- Workflow does not use secrets, package proxy, or dependency bootstrap
- Workflow builds the devcontainer Dockerfile (not production)
- Smoke script checks tooling baseline without installing dependencies
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "devcontainer-smoke.yml"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "devcontainer" / "smoke.sh"


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_devcontainer_smoke_workflow_exists() -> None:
    """Both the workflow and the smoke script must be present."""
    assert WORKFLOW.is_file(), "Missing .github/workflows/devcontainer-smoke.yml"
    assert SMOKE_SCRIPT.is_file(), "Missing scripts/devcontainer/smoke.sh"


# ---------------------------------------------------------------------------
# Workflow triggers: path-scoped + manual
# ---------------------------------------------------------------------------


def test_devcontainer_smoke_workflow_is_path_scoped_and_manual() -> None:
    """Workflow must trigger on PR path changes and support manual dispatch."""
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = data[True] if True in data else data.get("on", {})

    assert "workflow_dispatch" in triggers, "Workflow must support workflow_dispatch"
    assert "pull_request" in triggers, "Workflow must trigger on pull_request"

    paths = triggers["pull_request"].get("paths", [])
    assert ".devcontainer/**" in paths, "Workflow must be scoped to .devcontainer/**"
    assert "scripts/devcontainer/**" in paths, "Workflow must be scoped to scripts/devcontainer/**"
    assert "opencode.json" in paths, "Workflow must be scoped to opencode.json"


# ---------------------------------------------------------------------------
# Security: no secrets, no bootstrap, no error masking
# ---------------------------------------------------------------------------


def test_devcontainer_smoke_workflow_does_not_use_secrets_or_bootstrap() -> None:
    """Workflow must not reference secrets, package proxy, or dependency bootstrap."""
    text = WORKFLOW.read_text(encoding="utf-8")

    forbidden = [
        "secrets.",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "make devcontainer-bootstrap",
        "continue-on-error: true",
        "|| true",
    ]

    for token in forbidden:
        assert token not in text, f"Workflow must not contain '{token}'"


# ---------------------------------------------------------------------------
# Docker: builds devcontainer Dockerfile, not production
# ---------------------------------------------------------------------------


def test_devcontainer_smoke_builds_devcontainer_dockerfile() -> None:
    """Workflow must build the devcontainer Dockerfile image."""
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "docker build" in text, "Workflow must contain docker build command"
    assert (
        "-f .devcontainer/Dockerfile" in text
    ), "Workflow must build from .devcontainer/Dockerfile"
    assert (
        "pulseplate-devcontainer-smoke:ci" in text
    ), "Workflow must tag image as pulseplate-devcontainer-smoke:ci"


def test_devcontainer_smoke_does_not_build_production_dockerfile() -> None:
    """Workflow must not reference the production Dockerfile."""
    text = WORKFLOW.read_text(encoding="utf-8")

    # The only Dockerfile reference should be .devcontainer/Dockerfile
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "Dockerfile" in stripped and ".devcontainer/Dockerfile" not in stripped:
            assert (
                False
            ), f"Workflow references a Dockerfile that is not .devcontainer/Dockerfile: {stripped}"


# ---------------------------------------------------------------------------
# Smoke script: tooling checks without dependency install
# ---------------------------------------------------------------------------


def test_devcontainer_smoke_script_checks_tooling_without_installing_deps() -> None:
    """Smoke script must verify tooling baseline without installing dependencies."""
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    required = [
        "python3 --version",
        "make --version",
        "git --version",
        "jq --version",
        "curl --version",
        "sqlite3 --version",
        "psql --version",
        "bash -n scripts/opencode/run_pulseplate_mcp.sh",
    ]

    for token in required:
        assert token in text, f"Smoke script must contain '{token}'"

    forbidden = [
        "pip install",
        "npm install",
        "npm ci",
        "make devcontainer-bootstrap",
    ]

    for token in forbidden:
        assert token not in text, f"Smoke script must not contain '{token}'"


def test_devcontainer_smoke_script_uses_strict_mode() -> None:
    """Smoke script must use set -euo pipefail for safe execution."""
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "set -euo pipefail" in text, "Smoke script must use 'set -euo pipefail'"


def test_devcontainer_smoke_script_checks_python_313() -> None:
    """Smoke script must validate Python 3.13 baseline."""
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "(3, 13)" in text, "Smoke script must check for Python 3.13"


def test_devcontainer_smoke_script_checks_workdir() -> None:
    """Smoke script must verify the expected working directory."""
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert (
        "/workspaces/PulsePlate" in text
    ), "Smoke script must check /workspaces/PulsePlate workdir"
