"""Guard tests for the Docker devcontainer foundation.

These tests verify that:
- Required devcontainer files exist
- No package-proxy secrets are baked into the devcontainer image
- Configuration values match project conventions
- Makefile exposes the required container-aware targets
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys

import pytest
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
    assert "postAttachCommand" not in data
    assert "overrideCommand" not in data
    assert data.get("postStartCommand") == (
        "git config --global --add safe.directory /workspaces/PulsePlate"
    )


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


def test_devcontainer_json_container_env_forwards_only_safe_bootstrap_env() -> None:
    """Only safe bootstrap proxy env vars may use localEnv passthrough."""
    data = json.loads((DEVCONTAINER_DIR / "devcontainer.json").read_text(encoding="utf-8"))

    env = data.get("containerEnv", {})
    forbidden = {
        "SERVER_SALT",
        "APPLE_SHARED_SECRET",
        "EXPORT_TOKEN_SECRET",
        "PERPLEXITY_API_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    }
    assert forbidden.isdisjoint(env), "devcontainer.json must not forward app or CI secrets"
    assert env["PULSEPLATE_PYTHON_INDEX_URL"] == "${localEnv:PULSEPLATE_PYTHON_INDEX_URL}"
    assert env["PULSEPLATE_PYTHON_TRUSTED_HOST"] == ("${localEnv:PULSEPLATE_PYTHON_TRUSTED_HOST}")

    local_env_keys = {
        key
        for key, value in env.items()
        if isinstance(value, str) and value.startswith("${localEnv:")
    }
    assert local_env_keys == {
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PULSEPLATE_PYTHON_TRUSTED_HOST",
    }


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
    assert set(env) == {
        "PYTHONPATH",
        "PULSEPLATE_IN_CONTAINER",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PULSEPLATE_PYTHON_TRUSTED_HOST",
        "APP_ENV",
        "VIP_MODULE_ENABLED",
        "WATCHFILES_FORCE_POLLING",
    }
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


def test_devcontainer_sdk_artifacts_keep_source_build_and_auth_in_the_producer() -> None:
    config = yaml.safe_load((DEVCONTAINER_DIR / "docker-compose.devcontainer.yml").read_text())
    producer = config["services"]["native-sdk-artifacts"]
    consumer = config["services"]["devcontainer"]
    assert producer["platform"] == consumer["platform"] == "linux/amd64"
    assert producer["deploy"]["replicas"] == 0
    assert producer["build"]["target"] == "dev-bootstrap-sdk"
    assert producer["build"]["secrets"] == ["pp_py_index", "pp_netrc"]
    assert consumer["build"]["additional_contexts"] == {
        "native_sdk": "service:native-sdk-artifacts"
    }
    assert "secrets" not in consumer and "env_file" not in consumer
    assert "pulseplate-dev-venv:/workspaces/PulsePlate/.venv" in consumer["volumes"]
    assert all("docker.sock" not in mount for mount in consumer["volumes"])
    tooling = (DEVCONTAINER_DIR / "Dockerfile").read_text()
    assert "COPY --from=native_sdk /wheelhouse/ /opt/dev-wheelhouse/" in tooling
    assert "install -d -o vscode -g vscode /workspaces/PulsePlate/.venv" in tooling
    assert "chmod 755 /opt/dev-wheelhouse" in tooling
    assert "chmod 644 /opt/dev-wheelhouse/*.whl" in tooling
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    acquisition = dockerfile.split(" AS dev-bootstrap-inputs\n", 1)[1].split("\nFROM ", 1)[0]
    assert 'index="${PULSEPLATE_PYTHON_INDEX_URL:-}"' in acquisition
    assert "--mount=type=secret,id=pp_py_index,required=false" in acquisition
    assert "--mount=type=secret,id=pp_netrc,required=false" in acquisition
    assert "--prefetch-only" in acquisition and "--psycopg-sdk /opt/psycopg-sdk" in acquisition
    assert "--build-psycopg-c" not in acquisition
    development = dockerfile.split("FROM runtime-base AS development", 1)[1]
    assert "COPY --from=dev-bootstrap-sdk /wheelhouse/ /opt/dev-wheelhouse/" in development
    assert "PULSEPLATE_BOOTSTRAP_WHEELHOUSE=" + "/opt/dev-wheelhouse" in development
    assert "chmod 755 /opt/dev-wheelhouse" in development
    assert "chmod 644 /opt/dev-wheelhouse/*.whl" in development
    makefile = (REPO_ROOT / "Makefile").read_text()
    assert "devcontainer-bootstrap: venv" in makefile
    assert "--consume-only" in makefile and "--require-virtualenv" in makefile
    assert "ln -sf" not in makefile.split("devcontainer-bootstrap:", 1)[1].split("dc-up:", 1)[0]
    for service in ("pulseplate", "pulseplate-dev"):
        root = yaml.safe_load((REPO_ROOT / "docker-compose.yaml").read_text())
        assert root["services"][service]["platform"] == "linux/amd64"


@pytest.mark.parametrize("platform", ("Darwin", "Linux"))
def test_backend_shell_refusal_preserves_caller_and_has_no_venv_side_effect(
    tmp_path: Path, platform: str
) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    uname = tmp_path / "uname"
    uname.write_text(f'#!/bin/sh\nif [ "$1" = -s ]; then echo {platform}; else echo x86_64; fi\n')
    uname.chmod(0o755)
    fixture = tmp_path / "repo"
    script = fixture / "scripts/dev_shell.sh"
    script.parent.mkdir(parents=True)
    script.write_text((REPO_ROOT / "scripts/dev_shell.sh").read_text(encoding="utf-8"))
    python = tmp_path / "python3"
    python.write_text("#!/bin/sh\necho unexpected-python > python-called\nexit 99\n")
    python.chmod(0o755)
    program = (
        "set +e +u; before=$(set +o); "
        f"source '{script}'; code=$?; after=$(set +o); "
        'if test $code -eq 1 && test "$before" = "$after" && '
        'test -z "${VIRTUAL_ENV:-}"; then echo caller-continues; else exit 2; fi'
    )
    result = subprocess.run(
        [bash, "-c", program],
        cwd=tmp_path,
        env={"PATH": str(tmp_path) + os.pathsep + os.defpath, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == "caller-continues"
    assert not (fixture / ".venv").exists()
    assert not (tmp_path / "python-called").exists()


def _standalone_bootstrap_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    """Exercise real shell/Make callers with isolated interpreter transport.

    Synthetic artifacts test caller handoff, not genuine SDK admission; the
    existing installer suite and native image proof own that separate check.
    """
    fixture = tmp_path / "repo"
    scripts = fixture / "scripts"
    (scripts / "ci").mkdir(parents=True)
    (fixture / ".venv").mkdir()  # A new named volume starts as an empty directory.
    (fixture / "Makefile").write_bytes((REPO_ROOT / "Makefile").read_bytes())
    (scripts / "dev_shell.sh").write_bytes((REPO_ROOT / "scripts/dev_shell.sh").read_bytes())
    (scripts / "setup_git_aliases.sh").write_text("#!/bin/sh\nexit 0\n")
    (scripts / "ci/install_locked_python_requirements.py").write_text("# isolated transport\n")
    (fixture / "constraints.txt").write_text("# synthetic caller input\n")
    control = tmp_path / "control"
    control.mkdir()
    uname = control / "uname"
    uname.write_text('#!/bin/sh\nif [ "$1" = -s ]; then echo Linux; else echo x86_64; fi\n')
    uname.chmod(0o755)
    python = control / "python3"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, shlex, sys\n"
        "args = sys.argv[1:]\n"
        "with pathlib.Path(os.environ['CALLER_LOG']).open('a') as stream:\n"
        "    stream.write(json.dumps(args) + '\\n')\n"
        "if args[:2] == ['-m', 'venv']:\n"
        "    directory = pathlib.Path(args[2]); (directory / 'bin').mkdir(parents=True, exist_ok=True)\n"
        "    (directory / 'pyvenv.cfg').write_text('include-system-site-packages = false\\n')\n"
        "    executable = directory / 'bin/python'\n"
        "    executable.write_text(pathlib.Path(sys.argv[0]).read_text()); executable.chmod(0o755)\n"
        "    (directory / 'bin/activate').write_text('export VIRTUAL_ENV=' + shlex.quote(str(directory.resolve())) + '\\n')\n"
        "elif args and args[0].endswith('install_locked_python_requirements.py'):\n"
        "    required = {'--consume-only', '--install-dev', '--require-virtualenv', '--wheelhouse-dir', '--psycopg-sdk'}\n"
        "    if not required.issubset(args) or os.environ.get('PIP_REQUIRE_VIRTUALENV') != '1':\n"
        "        raise SystemExit(3)\n"
        "    for flag, key in (('--psycopg-sdk', 'PULSEPLATE_PSYCOPG_C_SDK'), ('--wheelhouse-dir', 'PULSEPLATE_BOOTSTRAP_WHEELHOUSE')):\n"
        "        if args[args.index(flag) + 1] != os.environ[key]: raise SystemExit(4)\n"
        "elif args[:2] != ['-m', 'pre_commit']:\n"
        "    raise SystemExit(5)\n"
    )
    python.chmod(0o755)
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    (sdk / "psycopg-c-sdk.json").write_text("{}\n")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    log = tmp_path / "caller-log.jsonl"
    environment = {
        "PATH": str(control) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "CALLER_LOG": str(log),
        "PULSEPLATE_PSYCOPG_C_SDK": str(sdk),
        "PULSEPLATE_BOOTSTRAP_WHEELHOUSE": str(wheelhouse),
    }
    return fixture, environment, log


@pytest.mark.parametrize("target", ("venv", "devcontainer-bootstrap"))
def test_make_bootstrap_and_sync_execute_offline_handoff_from_empty_volume(
    tmp_path: Path, target: str
) -> None:
    fixture, environment, log = _standalone_bootstrap_fixture(tmp_path)
    make = shutil.which("make")
    assert make is not None
    for command in (target, "venv-sync"):
        result = subprocess.run(
            [make, command],
            cwd=fixture,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert sum(event[:2] == ["-m", "venv"] for event in events) == 1
    assert sum(event[0].endswith("install_locked_python_requirements.py") for event in events) == 2
    assert (fixture / ".venv/pyvenv.cfg").is_file()


def test_source_backend_shell_initializes_existing_empty_volume_and_then_activates(
    tmp_path: Path,
) -> None:
    fixture, environment, log = _standalone_bootstrap_fixture(tmp_path)
    bash = shutil.which("bash")
    assert bash is not None
    program = (
        f"source {shlex.quote(str(fixture / 'scripts/dev_shell.sh'))}; "
        f"test \"$VIRTUAL_ENV\" = {shlex.quote(str(fixture / '.venv'))}; "
        "echo activated-from-empty-volume"
    )
    result = subprocess.run(
        [bash, "-c", program],
        cwd=fixture,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "activated-from-empty-volume" in result.stdout
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert events[0] == ["-m", "venv", str(fixture / ".venv")]
    assert len(events) == 2 and events[1][0].endswith("install_locked_python_requirements.py")


@pytest.mark.parametrize("missing", ("SDK", "wheelhouse"))
def test_make_bootstrap_rejects_missing_artifacts_before_venv_creation(
    tmp_path: Path, missing: str
) -> None:
    fixture, environment, log = _standalone_bootstrap_fixture(tmp_path)
    key = "PULSEPLATE_PSYCOPG_C_SDK" if missing == "SDK" else "PULSEPLATE_BOOTSTRAP_WHEELHOUSE"
    environment.pop(key)
    make = shutil.which("make")
    assert make is not None
    result = subprocess.run(
        [make, "venv"],
        cwd=fixture,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode != 0
    assert "genuine SDK and verified wheelhouse" in result.stdout + result.stderr
    assert not log.exists() and not (fixture / ".venv/pyvenv.cfg").exists()


@pytest.mark.parametrize("system, machine", (("Darwin", "arm64"), ("Linux", "aarch64")))
@pytest.mark.parametrize("target", ("venv", "venv-sync", "devcontainer-bootstrap"))
def test_make_bootstrap_rejects_unsupported_host_before_interpreter_effects(
    tmp_path: Path, system: str, machine: str, target: str
) -> None:
    fixture, environment, log = _standalone_bootstrap_fixture(tmp_path)
    uname = Path(environment["PATH"].split(os.pathsep)[0]) / "uname"
    uname.write_text(f'#!/bin/sh\nif [ "$1" = -s ]; then echo {system}; else echo {machine}; fi\n')
    make = shutil.which("make")
    assert make is not None
    result = subprocess.run(
        [make, target],
        cwd=fixture,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode != 0
    assert "Backend bootstrap requires Linux amd64" in result.stdout + result.stderr
    assert not log.exists() and not (fixture / ".venv/pyvenv.cfg").exists()
