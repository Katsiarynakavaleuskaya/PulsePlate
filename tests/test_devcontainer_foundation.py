"""Guard tests for the Docker devcontainer foundation.

These tests verify that:
- Required devcontainer files exist
- No package-proxy secrets are baked into the devcontainer image
- Configuration values match project conventions
- Makefile exposes the required container-aware targets
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVCONTAINER_DIR = REPO_ROOT / ".devcontainer"


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_devcontainer_files_exist() -> None:
    """All three devcontainer foundation files must be present."""
    assert (DEVCONTAINER_DIR / "Dockerfile").is_file(), "Missing .devcontainer/Dockerfile"
    assert (
        DEVCONTAINER_DIR / "devcontainer.json"
    ).is_file(), "Missing .devcontainer/devcontainer.json"
    assert (
        DEVCONTAINER_DIR / "docker-compose.devcontainer.yml"
    ).is_file(), "Missing .devcontainer/docker-compose.devcontainer.yml"


# ---------------------------------------------------------------------------
# Security: no baked secrets in devcontainer Dockerfile
# ---------------------------------------------------------------------------


def test_devcontainer_dockerfile_does_not_bake_package_proxy_secrets() -> None:
    """Devcontainer Dockerfile must NOT contain proxy secrets or install deps
    in executable lines (ARG, ENV, RUN, COPY).  Comments are allowed."""
    text = (DEVCONTAINER_DIR / "Dockerfile").read_text(encoding="utf-8")

    forbidden_tokens = [
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PULSEPLATE_PYTHON_TRUSTED_HOST",
        "pip install -r requirements",
        "pip-sync",
    ]

    executable_lines = [
        line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    executable_text = "\n".join(executable_lines)

    for token in forbidden_tokens:
        assert token not in executable_text, (
            f"Devcontainer Dockerfile executable lines must not contain '{token}' — "
            "deps are installed at runtime via make devcontainer-bootstrap"
        )


def test_devcontainer_dockerfile_has_no_build_args() -> None:
    """Devcontainer Dockerfile must not use ARG for secret-like values."""
    text = (DEVCONTAINER_DIR / "Dockerfile").read_text(encoding="utf-8")

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ARG ") and not stripped.startswith("ARG VARIANT"):
            # Allow ARG VARIANT for base image selection; block everything else
            assert (
                "INDEX_URL" not in stripped.upper()
            ), f"Devcontainer Dockerfile must not pass index URL as build arg: {stripped}"
            assert (
                "TRUSTED_HOST" not in stripped.upper()
            ), f"Devcontainer Dockerfile must not pass trusted host as build arg: {stripped}"


# ---------------------------------------------------------------------------
# devcontainer.json configuration
# ---------------------------------------------------------------------------


def test_devcontainer_json_configuration() -> None:
    """devcontainer.json must have correct workspace and user."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    assert data["workspaceFolder"] == "/workspaces/PulsePlate"
    assert data["remoteUser"] == "vscode"


def test_devcontainer_json_does_not_auto_execute_workspace_bootstrap() -> None:
    """Opening the devcontainer must not auto-run repository-controlled code."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    assert "postCreateCommand" not in data
    assert "onCreateCommand" not in data
    assert "updateContentCommand" not in data


def test_devcontainer_json_does_not_enable_host_docker_socket() -> None:
    """Default devcontainer must not expose the host Docker daemon."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    features = data.get("features", {})
    assert "ghcr.io/devcontainers/features/docker-outside-of-docker:1" not in features
    assert "ghcr.io/devcontainers/features/docker-in-docker:2" not in features


def test_devcontainer_json_node_24_feature() -> None:
    """devcontainer.json must include Node 24 feature to match .nvmrc."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    node_feature = data.get("features", {}).get("ghcr.io/devcontainers/features/node:1", {})
    assert (
        node_feature.get("version") == "24"
    ), "devcontainer.json must pin Node feature version to 24 (matching .nvmrc)"


def test_devcontainer_json_container_env_marker() -> None:
    """devcontainer.json must set PULSEPLATE_IN_CONTAINER=1."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    env = data.get("containerEnv", {})
    assert (
        env.get("PULSEPLATE_IN_CONTAINER") == "1"
    ), "devcontainer.json must set PULSEPLATE_IN_CONTAINER=1 in containerEnv"


# ---------------------------------------------------------------------------
# Compose configuration
# ---------------------------------------------------------------------------


def test_devcontainer_compose_does_not_import_full_env_file() -> None:
    """Compose must not load the full application .env into the devcontainer."""
    data = yaml.safe_load(
        (DEVCONTAINER_DIR / "docker-compose.devcontainer.yml").read_text(encoding="utf-8")
    )
    service = data["services"]["devcontainer"]

    assert "env_file" not in service, "Devcontainer must not import ../.env wholesale"
    build_cfg = service.get("build", {})
    assert (
        "args" not in build_cfg
    ), "Compose build must NOT pass args (secrets leak into image layers)"


def test_devcontainer_compose_forwards_only_bootstrap_proxy_env() -> None:
    """Only package-proxy env vars may be forwarded for manual bootstrap."""
    data = yaml.safe_load(
        (DEVCONTAINER_DIR / "docker-compose.devcontainer.yml").read_text(encoding="utf-8")
    )
    service = data["services"]["devcontainer"]

    env = service["environment"]
    forbidden = {
        "SERVER_SALT",
        "APPLE_SHARED_SECRET",
        "EXPORT_TOKEN_SECRET",
        "PERPLEXITY_API_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
    }
    assert forbidden.isdisjoint(env), "Devcontainer must not forward app secrets from .env"
    assert env["PULSEPLATE_PYTHON_INDEX_URL"] == "${PULSEPLATE_PYTHON_INDEX_URL:-}"
    assert env["PULSEPLATE_PYTHON_TRUSTED_HOST"] == "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}"


def test_devcontainer_compose_container_marker() -> None:
    """Compose must set PULSEPLATE_IN_CONTAINER=1 in environment."""
    data = yaml.safe_load(
        (DEVCONTAINER_DIR / "docker-compose.devcontainer.yml").read_text(encoding="utf-8")
    )
    service = data["services"]["devcontainer"]

    assert service["environment"]["PULSEPLATE_IN_CONTAINER"] == "1"


# ---------------------------------------------------------------------------
# Makefile targets
# ---------------------------------------------------------------------------


def test_makefile_exposes_devcontainer_targets_and_dev_python() -> None:
    """Makefile must define DEV_PYTHON and all devcontainer targets."""
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    required = [
        "DEV_PYTHON ?=",
        "devcontainer-bootstrap:",
        "dc-up:",
        "dc-shell:",
        "dc-down:",
        "dc-smoke:",
    ]

    for token in required:
        assert token in text, f"Makefile must contain '{token}'"


def test_makefile_preserves_venv_target() -> None:
    """make venv must remain as fallback — never removed."""
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "venv:" in text, "Makefile must preserve 'venv:' target as fallback"
    assert "VENV_PYTHON ?=" in text, "Makefile must preserve VENV_PYTHON definition"
