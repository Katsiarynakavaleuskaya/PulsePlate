"""Regression tests for Python supply-chain hardening controls."""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from typing import Any, cast

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version
import pytest
import yaml

import scripts.ci.install_locked_python_requirements as locked_installer
from scripts.ci import audit_fastembed_compat as compat_audit
from scripts.ci import dependabot_requirement_carriers as carriers
from scripts.ci import check_python_dependency_surfaces as dependency_surfaces
from scripts.ci.check_docker_provenance_attestation import SBOM_PREDICATE_TYPE
from tests.runtime_toolchain_versions import CANONICAL_PYTHON
from scripts.orchestration.creative_code_patch_workspace import (
    git_env_without_parent_state,
    safe_git_config_args,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCKED_INSTALL_WORKFLOW_PATHS: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    ".github/workflows/frontend-ci.yml",
    ".github/workflows/nightly-tests.yml",
    ".github/workflows/nightly.yml",
    ".github/workflows/rag-release-gates.yml",
    ".github/workflows/security.yml",
)
PROXY_WORKFLOW_ENV_PATHS: tuple[str, ...] = LOCKED_INSTALL_WORKFLOW_PATHS + (
    ".github/workflows/build.yml",
    ".github/workflows/trivy.yml",
    ".github/workflows/cd.yml",
)
APPROVED_PROXY_ENV_EXPRESSION = (
    "${{ secrets.PULSEPLATE_PYTHON_INDEX_URL || vars.PULSEPLATE_PYTHON_INDEX_URL }}"
)
APPROVED_TRUSTED_HOST_EXPRESSION = (
    "${{ secrets.PULSEPLATE_PYTHON_TRUSTED_HOST || vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
)
APPROVED_PR_PROXY_ENV_EXPRESSION = "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
APPROVED_PR_TRUSTED_HOST_EXPRESSION = "${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
APPROVED_DEVPI_CI_USER_EXPRESSION = (
    "${{ github.event_name != 'pull_request' && "
    "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}"
)
APPROVED_DEVPI_CI_PASSWORD_EXPRESSION = (
    "${{ github.event_name != 'pull_request' && "
    "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}"
)
PR_TRIGGERED_PROXY_WORKFLOWS = frozenset(
    {
        ".github/workflows/ci.yml",
        ".github/workflows/frontend-ci.yml",
        ".github/workflows/build.yml",
    }
)
PIP_INSTALL_PATTERN = re.compile(r"\b\S*python\S*\s+-m\s+pip\s+install\b")
PIP_INSTALL_INVOCATION_PATTERN = re.compile(
    r"(?:^|[;&|]\s*)(?:\S*python\S*\s+-m\s+)?(?:\S*/)?pip(?:\d+(?:\.\d+)?)?\s+install\b",
)
PIP_REQUIREMENT_DIRECTIVE_PREFIXES = (
    "-i ",
    "--index-url ",
    "--extra-index-url ",
    "-f ",
    "--find-links ",
    "-r ",
    "--requirement ",
    "-c ",
    "--constraint ",
)
PINNED_CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
OPTIONAL_VECTOR_STACK_PACKAGES = (
    "fastembed",
    "pgvector",
)
OPTIONAL_VECTOR_FORBIDDEN_PACKAGES = (
    "cuda-bindings",
    "cuda-toolkit",
    "sentence-transformers",
    "triton",
    "torch",
    "transformers",
)
DEFAULT_INSTALL_REQUIREMENT_FILES = (
    "requirements.in",
    "requirements.txt",
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
    "requirements-lock.txt",
    "requirements-test.txt",
)
OPTIONAL_VECTOR_REQUIREMENT_FILES = (
    "requirements-rag-vector.in",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.in",
    "requirements-rag-vector-cpu.txt",
)
LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES = (
    "requirements-data.in",
    "requirements-data.txt",
    "requirements-evals.in",
    "requirements-evals.txt",
)
LOCAL_MANUAL_EVAL_DATA_LOCKFILES = (
    "requirements-data.txt",
    "requirements-evals.txt",
)
LOCAL_MANUAL_EVAL_DATA_PACKAGES = (
    "diskcache",
    "datasets",
    "ragas",
    "pandas",
    "pyarrow",
)
DISABLED_RAGAS_EVAL_PACKAGES = (
    "diskcache",
    "datasets",
    "ragas",
)
HTTPX2_TESTCLIENT_BACKEND_SURFACES = (
    "requirements-dev.in",
    "requirements-dev.txt",
    "requirements-test.in",
    "requirements-test.txt",
    "requirements-lock.txt",
)
HTTPX2_TESTCLIENT_RUNTIME_EXCLUDED_SURFACES = (
    "requirements.in",
    "requirements.txt",
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
    "requirements-data.in",
    "requirements-data.txt",
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
    "requirements-evals.in",
    "requirements-evals.txt",
    "requirements-rag-vector.in",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.in",
    "requirements-rag-vector-cpu.txt",
)
DS3_HOOK_LOCK_PARITY = {
    "https://github.com/adrienverge/yamllint": {
        "hook_id": "yamllint",
        "hook_count": 1,
        "package": "yamllint",
        "revision": "v1.38.0",
        "inputs": {"requirements-dev.in": {("~=", "1.38.0")}},
        "locks": ("requirements-dev.txt", "requirements-lock.txt"),
    },
    "https://github.com/psf/black": {
        "hook_id": "black",
        "hook_count": 1,
        "package": "black",
        "inputs": ("requirements-dev.in", "constraints.txt", "requirements-all.txt"),
        "locks": ("requirements-dev.txt", "requirements-lock.txt"),
    },
    "https://github.com/astral-sh/ruff-pre-commit": {
        "hook_id": "ruff",
        "hook_count": 2,
        "package": "ruff",
        "revision": "v0.16.4",
        "inputs": {
            "requirements-dev.in": {("~=", "0.16.4")},
            "constraints.txt": {(">=", "0.16.4")},
            "requirements-all.txt": {(">=", "0.16.4")},
        },
        "locks": ("requirements-dev.txt", "requirements-lock.txt"),
    },
    "https://github.com/pre-commit/mirrors-mypy": {
        "hook_id": "mypy",
        "hook_count": 1,
        "package": "mypy",
        "revision": "v2.3.1",
        "inputs": {
            "requirements-dev.in": {("==", "2.3.1")},
            "constraints.txt": {(">=", "2.3.1"), ("<", "3.0.0")},
            "requirements-all.txt": {(">=", "2.3.1")},
        },
        "locks": ("requirements-dev.txt", "requirements-lock.txt"),
    },
    "https://github.com/PyCQA/bandit": {
        "hook_id": "bandit",
        "hook_count": 1,
        "package": "bandit",
        "revision": "1.9.4",
        "inputs": {
            "requirements-ci-lite.in": {(">=", "1.9.4")},
            "requirements-dev.in": {(">=", "1.9.4")},
            "constraints.txt": {(">=", "1.9.4")},
            "requirements-all.txt": {(">=", "1.9.4")},
        },
        "locks": (
            "requirements-ci-lite.txt",
            "requirements-dev.txt",
            "requirements-lock.txt",
        ),
    },
    "https://github.com/pypa/pip-audit": {
        "hook_id": "pip-audit",
        "hook_count": 1,
        "package": "pip-audit",
        "revision": "v2.10.1",
        "inputs": {
            "requirements-ci-lite.in": {(">=", "2.10.1")},
            "requirements-dev.in": {(">=", "2.10.1")},
            "constraints.txt": {(">=", "2.10.1")},
            "requirements-all.txt": {(">=", "2.10.1")},
        },
        "locks": (
            "requirements-ci-lite.txt",
            "requirements-dev.txt",
            "requirements-lock.txt",
        ),
    },
}
DS3_RUNTIME_AND_OPTIONAL_EXCLUDED_SURFACES = (
    (
        "requirements.in",
        "requirements.txt",
        "requirements-docker-runtime.in",
        "requirements-docker-runtime.txt",
    )
    + OPTIONAL_VECTOR_REQUIREMENT_FILES
    + LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES
)
DS3_MYPY_CHANGED_FILE_REGEX = (
    r"^(app/.*\.py|core/.*\.py|scripts/.*\.py|mcp_.*\.py|setup_.*\.py|update_.*\.py|"
    r"verify_.*\.py|app\.py|main\.py|settings\.py|secure_config\.py|signed_links\.py|"
    r"llm\.py|nutrition_core\.py|nutrition_plate\.py|bmi_core\.py|bodyfat\.py|"
    r"bmi_visualization\.py|providers/.*\.py)$"
)
DEFAULT_AND_TOOLING_REQUIREMENT_FILES = DEFAULT_INSTALL_REQUIREMENT_FILES + (
    "requirements-dev.in",
    "requirements-dev.txt",
    "requirements-all.txt",
    "constraints.txt",
)


def _load_workflow(path: str) -> dict[str, object]:
    """Load a GitHub Actions workflow as structured YAML."""
    return yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))


def _iter_step_env_values(workflow: dict[str, object], env_name: str) -> list[str]:
    """Return all step-level env values for a GitHub Actions variable."""

    values: list[str] = []
    jobs = workflow.get("jobs", {})
    assert isinstance(jobs, dict)
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            env = step.get("env", {})
            if not isinstance(env, dict) or env_name not in env:
                continue
            value = env[env_name]
            assert isinstance(value, str)
            values.append(value)
    return values


def _workflow_events(path: str) -> dict[str, object]:
    """Return the GitHub Actions `on` block, including YAML boolean-key normalization."""

    workflow = _load_workflow(path)
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, dict), f"Missing workflow events block for {path}"
    return events


def test_pip_install_invocation_pattern_catches_path_and_versioned_pip() -> None:
    assert PIP_INSTALL_INVOCATION_PATTERN.search("/opt/venv/bin/pip install safety")
    assert PIP_INSTALL_INVOCATION_PATTERN.search("pip3 install safety")
    assert PIP_INSTALL_INVOCATION_PATTERN.search("python -m pip install safety")


def _workflow_steps(path: str, job_name: str) -> list[dict[str, object]]:
    """Return workflow steps for a specific job."""
    workflow = _load_workflow(path)
    return workflow["jobs"][job_name]["steps"]


def _python_setup_step(path: str, job_name: str) -> dict[str, object]:
    """Return the canonical python-setup step for a workflow job."""
    for step in _workflow_steps(path, job_name):
        if step.get("uses") == "./.github/actions/python-setup":
            return step
    raise AssertionError(f"Missing python-setup step for {path}:{job_name}")


def _workflow_step_by_name(path: str, job_name: str, step_name: str) -> dict[str, object]:
    """Return a workflow step by its display name."""

    for step in _workflow_steps(path, job_name):
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Missing step {step_name!r} for {path}:{job_name}")


def _python_setup_action_script(step_name: str) -> str:
    """Return a shell script block from the local python-setup action."""

    action = _load_workflow(".github/actions/python-setup/action.yml")
    steps = action["runs"]["steps"]
    assert isinstance(steps, list)
    for step in steps:
        if not isinstance(step, dict) or step.get("name") != step_name:
            continue
        script = step["run"]
        assert isinstance(script, str)
        return script
    raise AssertionError(f"Missing python-setup action step: {step_name}")


def _run_bash_script(script: str, *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(
        [bash],
        input=script,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _pushed_docker_steps_with_secret_index_args() -> tuple[dict[str, object], ...]:
    """Return pushed Docker build steps that receive private index inputs."""

    return (
        _workflow_step_by_name(
            ".github/workflows/cd.yml",
            "build",
            "Build & Push backend image (staging)",
        ),
        _workflow_step_by_name(
            ".github/workflows/cd.yml",
            "build-production",
            "Build & Push image (production)",
        ),
    )


def _build_publish_scan_step_with_secret_index_args() -> dict[str, object]:
    """Return the build.yml publish image build that feeds the fail-closed scan."""

    return _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Build Docker image for publish scan",
    )


def _workflow_step_names(path: str, job_name: str) -> list[str]:
    """Return display names for a workflow job's steps."""

    return [str(step["name"]) for step in _workflow_steps(path, job_name)]


def _requirement_package_versions(path: Path, package_name: str) -> set[str]:
    """Return exact or minimum package versions declared in a requirement surface."""

    canonical_package_name = canonicalize_name(package_name)
    versions: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if canonicalize_name(requirement.name) != canonical_package_name:
            continue
        for specifier in requirement.specifier:
            if specifier.operator in {"==", ">="}:
                versions.add(specifier.version)
    return versions


def _requirement_package_specifiers(path: Path, package_name: str) -> set[tuple[str, str]]:
    """Return package specifier tuples declared in a requirement surface."""

    canonical_package_name = canonicalize_name(package_name)
    specifiers: set[tuple[str, str]] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if canonicalize_name(requirement.name) != canonical_package_name:
            continue
        specifiers.update(
            (specifier.operator, specifier.version) for specifier in requirement.specifier
        )
    return specifiers


def _requirement_package_names(path: Path) -> set[str]:
    """Return canonical package names declared in a requirement surface."""

    package_names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        package_names.add(canonicalize_name(requirement.name))
    return package_names


def _requirement_entries(path: Path) -> list[Requirement]:
    """Return parsed package requirement entries, excluding pip directives."""

    requirements: list[Requirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirements.append(Requirement(line))
        except InvalidRequirement as exc:
            raise AssertionError(f"{path.name}: invalid requirement entry: {line}") from exc
    return requirements


def _requirement_pin_pairs(path: Path) -> tuple[tuple[str, str], ...]:
    """Return canonical package/specifier pairs for lockfile parity checks."""

    return tuple(
        (canonicalize_name(requirement.name), str(requirement.specifier))
        for requirement in _requirement_entries(path)
    )


def _requirement_is_exact_pin(requirement: Requirement) -> bool:
    """Return True when a requirement entry uses a concrete package==version pin."""

    return requirement.url is None and any(
        specifier.operator == "==" and not specifier.version.endswith(".*")
        for specifier in requirement.specifier
    )


def test_requirement_parser_canonicalizes_names_and_skips_non_requirements(tmp_path: Path) -> None:
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text(
        "\n".join(
            (
                "--extra-index-url https://download.pytorch.org/whl/cpu",
                "Torch~=2.11",
                "sentence-transformers @ https://example.invalid/sentence.whl",
                "-e git+https://example.invalid/repo.git#egg=ignored",
            )
        ),
        encoding="utf-8",
    )

    package_names = _requirement_package_names(requirements_path)
    assert "torch" in package_names
    assert "sentence-transformers" in package_names
    assert "ignored" not in package_names


def test_dependency_security_schema_blocks_known_bad_litellm_versions() -> None:
    schema = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "dependency_security_schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["blocked_versions"]["litellm"] == ["==1.82.7", "==1.82.8"]


def test_python_setup_action_uses_locked_installer_not_floating_tools() -> None:
    action_text = (REPO_ROOT / ".github" / "actions" / "python-setup" / "action.yml").read_text(
        encoding="utf-8"
    )

    assert "install_locked_python_requirements.py" in action_text
    assert "${{ github.workspace }}/scripts/ci/install_locked_python_requirements.py" in action_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in action_text
    assert '--index-url "$PULSEPLATE_PYTHON_INDEX_URL"' in action_text
    assert "Configure private Python index authentication" in action_text
    assert "DEVPI_CI_USER" in action_text
    assert "DEVPI_CI_PASSWORD" in action_text
    assert "*[[:space:]]*)" in action_text
    assert "must not contain whitespace" in action_text
    assert 'cat > "$HOME/.netrc"' in action_text
    assert action_text.index('touch "$marker"') < action_text.index('cat > "$HOME/.netrc"')
    assert "Root devpi credentials are forbidden" in action_text
    assert "PULSEPLATE_PYTHON_INDEX_URL must not contain credentials" in action_text
    assert "Remove private Python index authentication" in action_text
    assert 'rm -f "$HOME/.netrc"' in action_text
    assert "${{ inputs.requirements-profile }}" in action_text
    assert "${{ inputs.ci-lite-requirements-file }}" in action_text
    assert "${{ inputs.rag-vector-requirements-file }}" in action_text
    assert "${{ inputs.install-dev-deps }}" in action_text
    assert "${{ inputs.install-test-deps }}" in action_text
    assert "${{ inputs.test-requirements-file }}" in action_text
    assert "${{ inputs.install-mode }}" in action_text
    assert "${{ inputs.skip-base-install != 'true' }}" in action_text
    assert "--preflight-only" in action_text
    assert "Preflight dependency floors via approved proxy" in action_text
    assert (
        "::error::requirements-profile cannot be combined with install-dev-deps/install-test-deps"
        in action_text
    )
    assert "::error::Expected requirements.txt when requirements-profile is runtime" in action_text
    assert (
        "::error::Expected requirements-dev.txt when requirements-profile is runtime-dev"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when requirements-profile is runtime-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.ci-lite-requirements-file }} when requirements-profile is ci-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when requirements-profile is ci-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.ci-lite-requirements-file }} when requirements-profile is ci-lite"
        in action_text
    )
    assert (
        "::error::Expected requirements.txt when requirements-profile is rag-vector" in action_text
    )
    assert (
        "::error::Expected ${{ inputs.rag-vector-requirements-file }} when requirements-profile is rag-vector"
        in action_text
    )
    assert "::error::Expected requirements.txt for locked dependency install" in action_text
    assert "::error::Expected requirements-dev.txt when install-dev-deps is true" in action_text
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when install-test-deps is true"
        in action_text
    )
    assert "--requirements-profile" in action_text
    assert "--ci-lite-requirements-file" in action_text
    assert "--rag-vector-requirements-file" in action_text
    assert "skipping base dependency install" not in action_text
    assert "pre-commit>=" not in action_text
    assert "bandit>=" not in action_text
    assert "pytest>=" not in action_text
    assert "pytest-cov>=" not in action_text
    assert "requirements-dev.txt via install_locked_python_requirements.py" in action_text
    assert (
        "${{ inputs.test-requirements-file }} via install_locked_python_requirements.py"
        in action_text
    )


def test_python_setup_pip_upgrade_precedes_sdk_and_preserves_skip_and_cleanup() -> None:
    action = _load_workflow(".github/actions/python-setup/action.yml")
    steps = action["runs"]["steps"]
    names = [step.get("name") for step in steps]
    upgrade = next(step for step in steps if step.get("name") == "Upgrade and observe parent pip")
    assert names.index("Configure private Python index authentication") < names.index(
        upgrade["name"]
    )
    assert names.index(upgrade["name"]) < names.index("Build exact Psycopg C client SDK")
    assert upgrade["if"] == "${{ inputs.skip-base-install != 'true' }}"
    assert upgrade["working-directory"] == "${{ inputs.working-directory }}"
    script = upgrade["run"]
    assert "--upgrade-pip-only --upgrade-pip-spec 'pip==26.2.2'" in script
    assert '--index-url "$PULSEPLATE_PYTHON_INDEX_URL"' in script
    assert '--trusted-host "$PULSEPLATE_PYTHON_TRUSTED_HOST"' in script
    assert (
        '--emergency-wheel-manifest "$GITHUB_WORKSPACE/scripts/ci/emergency_python_wheels.json"'
        in script
    )
    assert script.index("--upgrade-pip-only") < script.index("import pip._vendor.certifi")
    assert "--requirements-profile" not in script and "--prefetch-only" not in script
    cleanup = next(
        step for step in steps if step.get("name") == "Remove private Python index authentication"
    )
    assert cleanup["if"] == "${{ always() }}"
    assert 'rm -f "$HOME/.netrc" "$marker"' in cleanup["run"]


@pytest.mark.parametrize("trusted_host", [None, "packages.pulseplate.app"])
def test_python_setup_failed_pip_upgrade_stops_and_keeps_owned_auth_cleanup(
    tmp_path: Path, trusted_host: str | None
) -> None:
    env = _private_index_auth_env(tmp_path, user="synthetic", password="synthetic")
    commands = tmp_path / "commands"
    commands.mkdir()
    args_path = tmp_path / "upgrade-args.json"
    stub = commands / "python"
    stub.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        "assert sys.argv[1].endswith('/install_locked_python_requirements.py')\n"
        "Path(os.environ['CONTROL_UPGRADE_ARGS']).write_text(json.dumps(sys.argv[1:]))\n"
        "raise SystemExit(7)\n"
    )
    stub.chmod(0o755)
    env.update(
        PATH=str(commands) + os.pathsep + os.defpath,
        GITHUB_WORKSPACE=str(tmp_path),
        CONTROL_UPGRADE_ARGS=str(args_path),
    )
    if trusted_host is not None:
        env["PULSEPLATE_PYTHON_TRUSTED_HOST"] = trusted_host
    configured = _run_bash_script(
        _python_setup_action_script("Configure private Python index authentication"), env=env
    )
    assert configured.returncode == 0, configured.stderr
    failed = _run_bash_script(
        _python_setup_action_script("Upgrade and observe parent pip"), env=env
    )
    assert failed.returncode == 7, failed.stdout + failed.stderr
    argv = json.loads(args_path.read_text())
    assert argv[argv.index("--upgrade-pip-spec") + 1] == "pip==26.2.2"
    assert "--upgrade-pip-only" in argv
    assert ("--trusted-host" in argv) == (trusted_host is not None)
    cleaned = _run_bash_script(
        _python_setup_action_script("Remove private Python index authentication"), env=env
    )
    assert cleaned.returncode == 0, cleaned.stderr
    assert not (Path(env["HOME"]) / ".netrc").exists()
    assert not (Path(env["RUNNER_TEMP"]) / "pulseplate-python-setup-netrc-created").exists()


@pytest.mark.parametrize(
    "name,size,digest,exit_code",
    [
        (
            "pip-26.2.2-py3-none-any.whl",
            1819850,
            "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70",
            0,
        ),
        (
            "pip-26.2.1-py3-none-any.whl",
            1819850,
            "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70",
            1,
        ),
        (
            "pip-26.2.2-py3-none-any.whl",
            1,
            "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70",
            1,
        ),
        ("pip-26.2.2-py3-none-any.whl", 1819850, "0" * 64, 1),
    ],
)
def test_ci_hook_seed_binds_exact_verified_wheel(
    tmp_path: Path, name: str, size: int, digest: str, exit_code: int
) -> None:
    step = _workflow_step_by_name(
        ".github/workflows/ci.yml", "lint", "Pre-commit (lint/format/security quick checks)"
    )
    script = step["run"]
    assert isinstance(script, str)
    source = script.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.If)
        and "Missing or incorrect reviewed pip seed" in ast.unparse(node)
    ]
    assert len(statements) == 1
    program = (
        "from pathlib import Path\nfrom types import SimpleNamespace\n"
        f"seed=SimpleNamespace(path=Path({name!r}),snapshot=SimpleNamespace(size={size},digest={digest!r}))\n"
        + ast.unparse(statements[0])
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert "acquire_locked_wheelhouse(" in source and "_validate_exact_wheelhouse(" in source
    assert "constraints_file=None" in source and "sdk=None" in source
    assert 'expected=frozenset({("pip", "26.2.2")})' in source
    assert source.index("_validate_exact_wheelhouse(\n") < source.index("seed = artifacts[0]")
    empty = tmp_path / "empty-wheelhouse"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="exactly the selected compiled artifacts"):
        locked_installer._validate_exact_wheelhouse(
            wheelhouse=empty, expected=frozenset({("pip", "26.2.2")})
        )


@pytest.mark.parametrize(
    "version,trust,exit_code",
    [
        ("26.2.2", "50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785", 0),
        ("26.2.1", "50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785", 1),
        ("26.2.2", "0" * 64, 1),
    ],
)
def test_parent_pip_observation_rejects_unfixed_version_or_trust_payload(
    tmp_path: Path, version: str, trust: str, exit_code: int
) -> None:
    source = (
        _python_setup_action_script("Upgrade and observe parent pip")
        .split("<<'PY'\n", 1)[1]
        .split("\nPY", 1)[0]
    )
    guards = [node for node in ast.parse(source).body if isinstance(node, ast.If)]
    assert len(guards) == 1
    program = f"version={version!r}\ntrust={trust!r}\n" + ast.unparse(guards[0])
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr


@pytest.mark.parametrize(
    "mode,pre_commit_exit,hook_exit,expected",
    [
        ("normal", 0, 0, 0),
        ("normal", 7, 0, 7),
        ("normal", 0, 3, 1),
        ("normal", 7, 3, 7),
        ("no-hooks", 0, 0, 1),
        ("seed-failure", 0, 0, 9),
        ("probe-failure", 0, 0, 8),
    ],
)
def test_ci_pre_commit_seed_lifecycle_preserves_failures_and_observes_created_hooks(
    tmp_path: Path, mode: str, pre_commit_exit: int, hook_exit: int, expected: int
) -> None:
    """Exercise shell wiring with synthetic executables; native payload proof is separate."""
    step = _workflow_step_by_name(
        ".github/workflows/ci.yml", "lint", "Pre-commit (lint/format/security quick checks)"
    )
    assert step["timeout-minutes"] == "${{ fromJSON(vars.CI_LINT_CHECKS_TIMEOUT_MINUTES || '40') }}"
    assert step["env"] == {"SKIP": "no-commit-to-branch"}
    assert "if" not in step and "continue-on-error" not in step
    script = step["run"]
    assert isinstance(script, str)
    assert script.count("pre-commit run --all-files --show-diff-on-failure") == 1
    env = _private_index_auth_env(tmp_path)
    commands = tmp_path / "commands"
    commands.mkdir()
    trace = tmp_path / "lifecycle.jsonl"
    python_stub = commands / "python"
    python_stub.write_text(
        f"#!{sys.executable}\n"
        "import json,os,shutil,sys\nfrom pathlib import Path\n"
        "assert 'GH_TOKEN' not in os.environ and 'DEVPI_CI_PASSWORD' not in os.environ\n"
        "event={'argv':sys.argv[1:]}\n"
        "if sys.argv[1] == '-':\n"
        "    assert 'PULSEPLATE_PSYCOPG_C_SDK' not in os.environ\n"
        "    root=Path(sys.argv[2]); (root/'wheels').mkdir()\n"
        "    event['kind']='acquire'; code=9 if os.environ['CONTROL_MODE']=='seed-failure' else 0\n"
        "elif sys.argv[1:3] == ['-m','virtualenv']:\n"
        "    assert os.environ['PULSEPLATE_PSYCOPG_C_SDK']=='synthetic-sdk'\n"
        "    assert os.environ['VIRTUALENV_PIP']=='26.2.2'\n"
        "    assert os.environ['VIRTUALENV_DOWNLOAD']=='false'\n"
        "    assert os.environ['VIRTUALENV_NO_PERIODIC_UPDATE']=='true'\n"
        "    assert Path(os.environ['VIRTUALENV_EXTRA_SEARCH_DIR']).name=='wheels'\n"
        "    assert sys.argv[sys.argv.index('--app-data')+1]==os.environ['VIRTUALENV_APP_DATA']\n"
        "    assert not list(Path(os.environ['PRE_COMMIT_HOME']).iterdir())\n"
        "    target=Path(sys.argv[-1])/'bin/python'; target.parent.mkdir(parents=True)\n"
        "    shutil.copy2(Path(__file__),target)\n"
        "    event['kind']='virtualenv'; code=0\n"
        "else:\n"
        "    assert sys.argv[1:3]==['-I','-c']\n"
        "    assert '26.2.2' in sys.argv[3] and 'sys.prefix != sys.base_prefix' in sys.argv[3]\n"
        "    assert '50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785' in sys.argv[3]\n"
        "    event['kind']='probe' if Path(__file__).parent.parent.name=='probe' else 'hook'\n"
        "    code=(8 if os.environ['CONTROL_MODE']=='probe-failure' else 0) if event['kind']=='probe' else int(os.environ['CONTROL_HOOK_EXIT'])\n"
        "with Path(os.environ['CONTROL_TRACE']).open('a') as stream: stream.write(json.dumps(event)+'\\n')\n"
        "raise SystemExit(code)\n"
    )
    pre_commit = commands / "pre-commit"
    pre_commit.write_text(
        f"#!{sys.executable}\n"
        "import json,os,shutil,sys\nfrom pathlib import Path\n"
        "assert sys.argv[1:]==['run','--all-files','--show-diff-on-failure']\n"
        "assert os.environ['SKIP']=='no-commit-to-branch'\n"
        "assert os.environ['PULSEPLATE_PSYCOPG_C_SDK']=='synthetic-sdk'\n"
        "if os.environ['CONTROL_MODE']!='no-hooks':\n"
        "    target=Path(os.environ['PRE_COMMIT_HOME'])/'repo-synthetic/py_env-python3.13/bin/python'\n"
        "    target.parent.mkdir(parents=True); shutil.copy2(Path(os.environ['CONTROL_PYTHON']),target)\n"
        "with Path(os.environ['CONTROL_TRACE']).open('a') as stream: stream.write(json.dumps({'kind':'pre-commit','argv':sys.argv[1:]})+'\\n')\n"
        "raise SystemExit(int(os.environ['CONTROL_PRE_COMMIT_EXIT']))\n"
    )
    python_stub.chmod(0o755)
    pre_commit.chmod(0o755)
    env.update(
        PATH=str(commands) + os.pathsep + os.defpath,
        CONTROL_TRACE=str(trace),
        CONTROL_MODE=mode,
        CONTROL_PYTHON=str(python_stub),
        CONTROL_PRE_COMMIT_EXIT=str(pre_commit_exit),
        CONTROL_HOOK_EXIT=str(hook_exit),
        PULSEPLATE_PSYCOPG_C_SDK="synthetic-sdk",
        SKIP="no-commit-to-branch",
    )
    result = _run_bash_script(script, env=env)
    assert result.returncode == expected, result.stdout + result.stderr
    observed = [json.loads(line)["kind"] for line in trace.read_text().splitlines()]
    if mode == "seed-failure":
        assert observed == ["acquire"]
    elif mode == "probe-failure":
        assert observed == ["acquire", "virtualenv", "probe"]
    else:
        assert observed == ["acquire", "virtualenv", "probe", "pre-commit"] + (
            [] if mode == "no-hooks" else ["hook"]
        )
    assert not list(Path(env["RUNNER_TEMP"]).glob("pulseplate-hook-seed.*"))


def _private_index_auth_env(
    tmp_path: Path,
    *,
    user: str | None = None,
    password: str | None = None,
    index_url: str = "https://packages.pulseplate.app/root/pulseplate/+simple/",
) -> dict[str, str]:
    home = tmp_path / "home"
    runner_temp = tmp_path / "runner-temp"
    home.mkdir()
    runner_temp.mkdir()

    env = {
        "HOME": str(home),
        "RUNNER_TEMP": str(runner_temp),
        "PULSEPLATE_PYTHON_INDEX_URL": index_url,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if user is not None:
        env["DEVPI_CI_USER"] = user
    if password is not None:
        env["DEVPI_CI_PASSWORD"] = password
    return env


def test_python_setup_rejected_zlib_artifact_is_exact_and_failure_scoped() -> None:
    action = _load_workflow(".github/actions/python-setup/action.yml")
    steps = action["runs"]["steps"]
    sdk = next(step for step in steps if step.get("name") == "Build exact Psycopg C client SDK")
    upload = next(
        step for step in steps if step.get("name") == "Retain untrusted rejected zlib response"
    )
    cleanup = next(
        step for step in steps if step.get("name") == "Remove private Python index authentication"
    )
    assert sdk["id"] == "psycopg_sdk" and "set -euo pipefail" in sdk["run"]
    assert 'mktemp -d "$RUNNER_TEMP/pulseplate-zlib-integrity.XXXXXXXX"' in sdk["run"]
    assert '--integrity-rejection-dir "$rejection_parent/quarantine"' in sdk["run"]
    assert "printf 'rejection_dir=%s/quarantine\\n'" in sdk["run"]
    assert sdk["run"].index("fetch_docker_source_artifacts.py") < sdk["run"].index(
        "docker buildx build"
    )
    assert (
        upload["if"]
        == "${{ failure() && steps.psycopg_sdk.outcome == 'failure' && steps.psycopg_sdk.outputs.rejection_dir != '' }}"
    )
    assert upload["uses"] == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    assert upload["with"] == {
        "name": "untrusted-zlib-rejected-response-${{ github.job }}-${{ inputs.python-version }}-${{ github.run_id }}-${{ github.run_attempt }}",
        "path": "${{ steps.psycopg_sdk.outputs.rejection_dir }}/response.bin\n${{ steps.psycopg_sdk.outputs.rejection_dir }}/metadata.json\n",
        "if-no-files-found": "ignore",
        "retention-days": 3,
    }
    assert "continue-on-error" not in sdk and "continue-on-error" not in upload
    assert steps.index(sdk) < steps.index(upload) < steps.index(cleanup)
    assert cleanup["if"] == "${{ always() }}" and 'rm -f "$HOME/.netrc" "$marker"' in cleanup["run"]


def test_python_setup_source_rejection_stops_sdk_build_and_preserves_auth_cleanup(
    tmp_path: Path,
) -> None:
    env = _private_index_auth_env(tmp_path, user="synthetic", password="synthetic")
    workspace, commands = tmp_path / "repo", tmp_path / "commands"
    workspace.mkdir()
    commands.mkdir()
    fetch_args, docker_called = tmp_path / "fetch-args.json", tmp_path / "docker-called"
    (commands / "python").write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        "if sys.argv[1] == '-c':\n    print('3.13')\n    raise SystemExit(0)\n"
        "if sys.argv[1].endswith('/fetch_docker_source_artifacts.py'):\n"
        "    Path(os.environ['CONTROL_FETCH_ARGS']).write_text(json.dumps(sys.argv[1:]))\n"
        "    sys.stderr.write('synthetic-integrity-rejection\\n')\n    raise SystemExit(9)\n"
        "raise SystemExit(2)\n"
    )
    (commands / "uname").write_text(
        '#!/bin/sh\ncase "$1" in -s) printf "Linux\\n";; -m) printf "x86_64\\n";; *) exit 1;; esac\n'
    )
    (commands / "docker").write_text(
        f"#!{sys.executable}\nimport os\nfrom pathlib import Path\n"
        "Path(os.environ['CONTROL_DOCKER_CALLED']).touch()\n"
    )
    for executable in commands.iterdir():
        executable.chmod(0o755)
    env.update(
        {
            "PATH": str(commands) + os.pathsep + env["PATH"],
            "GITHUB_WORKSPACE": str(workspace),
            "GITHUB_ENV": str(tmp_path / "github-env"),
            "GITHUB_OUTPUT": str(tmp_path / "github-output"),
            "CONTROL_FETCH_ARGS": str(fetch_args),
            "CONTROL_DOCKER_CALLED": str(docker_called),
        }
    )
    configure = _run_bash_script(
        _python_setup_action_script("Configure private Python index authentication"), env=env
    )
    assert configure.returncode == 0, configure.stderr
    failed = _run_bash_script(
        _python_setup_action_script("Build exact Psycopg C client SDK"), env=env
    )
    assert failed.returncode == 9 and failed.stderr == "synthetic-integrity-rejection\n"
    assert not docker_called.exists()
    quarantine = Path(Path(env["GITHUB_OUTPUT"]).read_text().removeprefix("rejection_dir=").strip())
    assert quarantine.parent.parent == Path(env["RUNNER_TEMP"])
    assert quarantine.parent.stat().st_mode & 0o777 == 0o700
    assert not quarantine.exists()
    assert json.loads(fetch_args.read_bytes()) == [
        str(workspace / "scripts/ci/fetch_docker_source_artifacts.py"),
        "--manifest",
        str(workspace / "scripts/ci/docker_source_artifacts.json"),
        "--output-dir",
        str(workspace / "build/docker-sources"),
        "--integrity-rejection-dir",
        str(quarantine),
    ]
    cleanup = _run_bash_script(
        _python_setup_action_script("Remove private Python index authentication"), env=env
    )
    assert cleanup.returncode == 0 and not (Path(env["HOME"]) / ".netrc").exists()
    assert not (Path(env["RUNNER_TEMP"]) / "pulseplate-python-setup-netrc-created").exists()


def test_python_setup_action_netrc_lifecycle_accepts_valid_non_root_creds(
    tmp_path: Path,
) -> None:
    configure_script = _python_setup_action_script("Configure private Python index authentication")
    cleanup_script = _python_setup_action_script("Remove private Python index authentication")
    env = _private_index_auth_env(tmp_path, user="pulse-ci", password="rotated-token")

    configure = _run_bash_script(configure_script, env=env)

    assert configure.returncode == 0, configure.stderr + configure.stdout
    netrc_path = Path(env["HOME"]) / ".netrc"
    marker_path = Path(env["RUNNER_TEMP"]) / "pulseplate-python-setup-netrc-created"
    assert netrc_path.exists()
    assert marker_path.exists()
    netrc_text = netrc_path.read_text(encoding="utf-8")
    assert "machine packages.pulseplate.app" in netrc_text
    assert "login pulse-ci" in netrc_text
    assert "password rotated-token" in netrc_text
    assert netrc_path.stat().st_mode & 0o777 == 0o600

    cleanup = _run_bash_script(cleanup_script, env=env)

    assert cleanup.returncode == 0, cleanup.stderr + cleanup.stdout
    assert not netrc_path.exists()
    assert not marker_path.exists()


def test_python_setup_action_netrc_lifecycle_noops_without_creds(tmp_path: Path) -> None:
    configure_script = _python_setup_action_script("Configure private Python index authentication")
    env = _private_index_auth_env(tmp_path)

    configure = _run_bash_script(configure_script, env=env)

    assert configure.returncode == 0, configure.stderr + configure.stdout
    assert not (Path(env["HOME"]) / ".netrc").exists()
    assert not (Path(env["RUNNER_TEMP"]) / "pulseplate-python-setup-netrc-created").exists()


@pytest.mark.parametrize(
    ("user", "password", "index_url", "preexisting_netrc", "expected_error"),
    (
        (
            "pulse-ci",
            None,
            "https://packages.pulseplate.app/root/pulseplate/+simple/",
            False,
            "Set both DEVPI_CI_USER and DEVPI_CI_PASSWORD",
        ),
        (
            "pulse ci",
            "token",
            "https://packages.pulseplate.app/root/pulseplate/+simple/",
            False,
            "must not contain whitespace",
        ),
        (
            "root",
            "token",
            "https://packages.pulseplate.app/root/pulseplate/+simple/",
            False,
            "Root devpi credentials are forbidden",
        ),
        (
            "pulse-ci",
            "token",
            "https://user" + ":" + "token@packages.pulseplate.app/root/pulseplate/+simple/",
            False,
            "must not contain credentials",
        ),
        (
            "pulse-ci",
            "token",
            "https://packages.pulseplate.app/root/pulseplate/+simple/",
            True,
            "Refusing to overwrite an existing .netrc",
        ),
    ),
)
def test_python_setup_action_netrc_lifecycle_rejects_unsafe_auth_inputs(
    tmp_path: Path,
    user: str | None,
    password: str | None,
    index_url: str,
    preexisting_netrc: bool,
    expected_error: str,
) -> None:
    configure_script = _python_setup_action_script("Configure private Python index authentication")
    env = _private_index_auth_env(
        tmp_path,
        user=user,
        password=password,
        index_url=index_url,
    )
    netrc_path = Path(env["HOME"]) / ".netrc"
    if preexisting_netrc:
        netrc_path.write_text("machine example.invalid\n", encoding="utf-8")

    configure = _run_bash_script(configure_script, env=env)

    assert configure.returncode != 0
    assert expected_error in configure.stdout + configure.stderr
    marker_path = Path(env["RUNNER_TEMP"]) / "pulseplate-python-setup-netrc-created"
    assert not marker_path.exists()
    if preexisting_netrc:
        assert netrc_path.read_text(encoding="utf-8") == "machine example.invalid\n"
    else:
        assert not netrc_path.exists()


def test_ci_python_setup_steps_receive_devpi_secrets_on_main_push_only() -> None:
    workflow = _load_workflow(".github/workflows/ci.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    setup_steps: list[dict[str, object]] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if isinstance(step, dict) and step.get("uses") == "./.github/actions/python-setup":
                setup_steps.append(step)

    assert setup_steps
    for step in setup_steps:
        env = step.get("env")
        assert isinstance(env, dict), f"Missing protected devpi env on {step}"
        assert env["DEVPI_CI_USER"] == APPROVED_DEVPI_CI_USER_EXPRESSION
        assert env["DEVPI_CI_PASSWORD"] == APPROVED_DEVPI_CI_PASSWORD_EXPRESSION


def test_ci_security_job_keeps_devpi_setup_and_uses_pip_audit() -> None:
    steps = _workflow_steps(".github/workflows/ci.yml", "security")
    step_names = [str(step["name"]) for step in steps]

    assert "Configure private Python index authentication for Safety" not in step_names
    assert "Install Safety" not in step_names
    assert "Remove private Python index authentication for Safety" not in step_names
    assert "Dependency audit with Safety" not in step_names

    setup_step = _python_setup_step(".github/workflows/ci.yml", "security")
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"
    setup_env = setup_step["env"]
    assert setup_env["DEVPI_CI_USER"] == APPROVED_DEVPI_CI_USER_EXPRESSION
    assert setup_env["DEVPI_CI_PASSWORD"] == APPROVED_DEVPI_CI_PASSWORD_EXPRESSION

    audit_step = _workflow_step_by_name(
        ".github/workflows/ci.yml",
        "security",
        "Dependency audit with pip-audit",
    )
    assert "bash scripts/ci_pip_audit.sh" in audit_step["run"]
    assert "requirements-security.txt" not in audit_step["run"]


def test_local_bootstrap_surfaces_use_locked_installer_and_virtualenv_guard() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dev_shell_text = (REPO_ROOT / "scripts" / "dev_shell.sh").read_text(encoding="utf-8")
    installer_text = (
        REPO_ROOT / "scripts" / "ci" / "install_locked_python_requirements.py"
    ).read_text(encoding="utf-8")

    assert "install_locked_python_requirements.py" in makefile_text
    assert "--require-virtualenv" in makefile_text
    assert "ensure-python-proxy" in makefile_text
    assert "Export PULSEPLATE_PYTHON_INDEX_URL" in makefile_text
    assert "PIP_REQUIRE_VIRTUALENV=1" in dev_shell_text
    assert "install_locked_python_requirements.py" in dev_shell_text
    for text in (makefile_text, dev_shell_text):
        assert "--consume-only" in text
        assert "--psycopg-sdk" in text and "--wheelhouse-dir" in text
        assert "PULSEPLATE_PSYCOPG_C_SDK" in text
        assert "PULSEPLATE_BOOTSTRAP_WHEELHOUSE" in text
    assert "venv: ensure-native-sdk" in makefile_text
    assert "venv-sync: ensure-native-sdk-inputs ensure-python-proxy" in makefile_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in installer_text


def test_local_bootstrap_docs_bind_source_sdk_and_historical_crypto_proof() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    dependency_docs = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    runbook = (REPO_ROOT / "RUNBOOK_AGENT.md").read_text(encoding="utf-8")
    advisory = (
        REPO_ROOT / "docs" / "security" / "CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md"
    ).read_text(encoding="utf-8")

    approved_proxy_export = 'export PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/"'
    assert approved_proxy_export in contributing
    assert approved_proxy_export in dependency_docs
    assert "make venv-sync" in dependency_docs
    assert "Local Development Bootstrap" in dependency_docs

    for document in (contributing, advisory):
        normalized = " ".join(document.casefold().split())
        assert "2026-08-04" in normalized
        assert "50.0.0" in normalized
        assert "approved proxy" in normalized
        assert "compatible binary wheel" in normalized
        assert "intel macos" in normalized
        assert "devcontainer" in normalized
        assert "ios/xcode" in normalized
        assert "host-native" in normalized
        assert "source-build fallback is not supported" in normalized

    normalized_advisory = " ".join(advisory.casefold().split())
    assert "46 exact artifacts" in normalized_advisory
    assert "macos arm64" in normalized_advisory
    assert "x86_64" in normalized_advisory
    assert "universal2" in normalized_advisory
    assert "133 consumer tests" in normalized_advisory

    normalized_dependency = " ".join(dependency_docs.casefold().split())
    for boundary in (
        "linux amd64 container sdk",
        "verified runtime/dev wheelhouse",
        "offline",
        "native macos",
        "does not supply a darwin sdk",
        "ios/xcode",
        "host-native",
        "make dc-up",
        "make dc-shell",
        "make devcontainer-bootstrap",
    ):
        assert boundary in normalized_dependency

    normalized_runbook = " ".join(runbook.casefold().split())
    for recovery_boundary in (
        "2026-08-04",
        "cryptography==50.0.0",
        "host only with an approved compatible binary wheel",
        "intel macos",
        "x86_64",
        "universal2",
        "use the devcontainer",
        "source-build fallback is not supported",
        "not a permanent availability claim",
    ):
        assert recovery_boundary in normalized_runbook

    wheelhouse = Path("/tmp/pulseplate-wheelhouse")
    requirement_file = Path("requirements.txt")
    constraints_file = Path("constraints.txt")
    index_url = "https://packages.pulseplate.app/root/pulseplate/+simple/"
    download_command = locked_installer.build_pip_download_command(
        python_executable="/usr/bin/python3",
        requirement_file=requirement_file,
        wheelhouse_dir=wheelhouse,
        constraints_file=constraints_file,
        index_url=index_url,
        trusted_host=None,
    )
    proxy_command = locked_installer.build_pip_proxy_install_command(
        python_executable="/usr/bin/python3",
        requirement_file=requirement_file,
        constraints_file=constraints_file,
        index_url=index_url,
        trusted_host=None,
        allow_pip_download_cache=True,
    )
    for command in (download_command, proxy_command):
        assert ["--only-binary", ":all:"] == command[
            command.index("--only-binary") : command.index("--only-binary") + 2
        ]
        assert "--no-binary" not in command

    hermetic_command = locked_installer.build_pip_install_command(
        python_executable="/usr/bin/python3",
        requirement_file=requirement_file,
        wheelhouse_dir=wheelhouse,
        constraints_file=constraints_file,
    )
    assert "--no-index" in hermetic_command
    assert ["--find-links", str(wheelhouse)] == hermetic_command[
        hermetic_command.index("--find-links") : hermetic_command.index("--find-links") + 2
    ]
    assert download_command[download_command.index("--dest") + 1] == str(wheelhouse)
    assert hermetic_command[hermetic_command.index("--find-links") + 1] == str(wheelhouse)
    active_artifacts = locked_installer.load_emergency_wheel_manifest(
        REPO_ROOT / "scripts" / "ci" / "emergency_python_wheels.json"
    )
    assert not any(
        canonicalize_name(artifact["package"]) == "cryptography" for artifact in active_artifacts
    )


def test_canonical_ci_and_docker_use_supply_chain_guardrails() -> None:
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    nightly_text = (REPO_ROOT / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8")
    docker_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose_text = (REPO_ROOT / "docker-compose.yaml").read_text(encoding="utf-8")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dockerignore_text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    installer_text = (
        REPO_ROOT / "scripts" / "ci" / "install_locked_python_requirements.py"
    ).read_text(encoding="utf-8")
    init_test_db_text = (
        REPO_ROOT / ".github" / "actions" / "init-test-db" / "action.yml"
    ).read_text(encoding="utf-8")
    dependency_docs_text = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(
        encoding="utf-8"
    )
    blocked_hosts = set(locked_installer.BLOCKED_INDEX_HOSTS)

    assert "check_python_startup_hooks.py" in installer_text
    assert "check_emergency_wheel_mirror_parity.py" in ci_text
    assert "--only-binary" in installer_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in installer_text
    assert any(host == ".".join(("pypi", "org")) for host in blocked_hosts)
    assert any(host == ".".join(("files", "pythonhosted", "org")) for host in blocked_hosts)
    assert any(host == ".".join(("test", "pypi", "org")) for host in blocked_hosts)
    assert "install_locked_python_requirements.py" in docker_text
    assert "ARG PULSEPLATE_PYTHON_INDEX_URL" in docker_text
    assert "constraints.txt" in docker_text
    assert "requirements-docker-runtime.txt" in docker_text
    assert "requirements-ci-lite.txt" in docker_text
    assert '--index-url "${PULSEPLATE_PYTHON_INDEX_URL}"' in docker_text
    assert 'ARG PULSEPLATE_REQUIREMENTS_FILE="requirements-docker-runtime.txt"' in docker_text
    assert (
        "requirements.txt|requirements-ci-lite.txt|requirements-docker-runtime.txt" in docker_text
    )
    assert '--requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}"' in docker_text
    assert APPROVED_PR_PROXY_ENV_EXPRESSION in ci_text
    assert APPROVED_PR_TRUSTED_HOST_EXPRESSION in ci_text
    assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in ci_text
    assert "secrets.PULSEPLATE_PYTHON_TRUSTED_HOST" not in ci_text
    assert APPROVED_PROXY_ENV_EXPRESSION in security_text
    assert APPROVED_PROXY_ENV_EXPRESSION in nightly_text
    assert "PULSEPLATE_PYTHON_INDEX_URL: ${PULSEPLATE_PYTHON_INDEX_URL:?" in compose_text
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST: ${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" in compose_text
    assert "--build-arg PULSEPLATE_PYTHON_INDEX_URL" in makefile_text
    assert "!requirements-docker-runtime.in" in dockerignore_text
    assert "!requirements-docker-runtime.txt" in dockerignore_text
    assert "!requirements-ci-lite.txt" in dockerignore_text
    assert "!constraints.txt" in dockerignore_text
    assert "!scripts/ci/check_python_startup_hooks.py" in dockerignore_text
    assert "!scripts/ci/emergency_python_wheels.json" in dockerignore_text
    assert "!scripts/ci/install_locked_python_requirements.py" in dockerignore_text
    assert (
        "COPY requirements.txt requirements-ci-lite.txt requirements-docker-runtime.txt constraints.txt ./"
        in docker_text
    )
    assert "COPY requirements.txt requirements-dev.txt constraints.txt ./" in docker_text
    production_root_index = docker_text.index("FROM runtime-base AS production")
    switch_to_root_index = docker_text.index("USER root", production_root_index)
    uninstall_pip_index = docker_text.index("/opt/venv/bin/python -m pip uninstall -y pip")
    return_to_non_root_index = docker_text.index("USER pulseplate", uninstall_pip_index)
    assert (
        production_root_index
        < switch_to_root_index
        < uninstall_pip_index
        < return_to_non_root_index
    )
    assert "install_locked_python_requirements.py" in dependency_docs_text
    assert "check_emergency_wheel_mirror_parity.py" in dependency_docs_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in dependency_docs_text
    assert "Run: make venv-sync" in init_test_db_text
    build_workflow_text = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8"
    )
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )
    for workflow_text in (
        build_workflow_text,
        trivy_workflow_text,
    ):
        assert "Docker image telemetry collection failed; reporting remains advisory-only." not in (
            workflow_text
        )
        assert "scripts/ci/check_docker_image_budget.py" in workflow_text
        assert "docs/telemetry/docker_image_budget.production.json" in workflow_text
        assert "docker-image-budget-check.json" in workflow_text
        assert "docker-image-budget-check.md" in workflow_text
        assert "if-no-files-found: warn" in workflow_text

    assert "if-no-files-found: warn" in trivy_workflow_text
    assert "set -euo pipefail" in trivy_workflow_text.split("- name: Install Trivy via apt", 1)[1]


@pytest.mark.parametrize("workflow_path", LOCKED_INSTALL_WORKFLOW_PATHS)
def test_all_changed_python_install_surfaces_use_locked_installer(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    assert (
        "install_locked_python_requirements.py" in workflow_text
        or ".github/actions/python-setup" in workflow_text
        or 'pip_index_args=(--index-url "$PULSEPLATE_PYTHON_INDEX_URL")' in workflow_text
    )
    assert "PULSEPLATE_PYTHON_INDEX_URL" in workflow_text
    for blocked_host in locked_installer.BLOCKED_INDEX_HOSTS:
        assert blocked_host not in workflow_text


@pytest.mark.parametrize("workflow_path", PROXY_WORKFLOW_ENV_PATHS)
def test_proxy_backed_workflows_support_vars_or_secrets(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    if workflow_path in PR_TRIGGERED_PROXY_WORKFLOWS:
        workflow = _load_workflow(workflow_path)
        pulseplate_envs = list(_iter_step_env_values(workflow, "PULSEPLATE_PYTHON_INDEX_URL"))
        pulseplate_envs.extend(_iter_step_env_values(workflow, "PULSEPLATE_PYTHON_TRUSTED_HOST"))

        workflow_env = workflow.get("env", {})
        if "PULSEPLATE_PYTHON_INDEX_URL" in workflow_env:
            pulseplate_envs.append(workflow_env["PULSEPLATE_PYTHON_INDEX_URL"])
        if "PULSEPLATE_PYTHON_TRUSTED_HOST" in workflow_env:
            pulseplate_envs.append(workflow_env["PULSEPLATE_PYTHON_TRUSTED_HOST"])

        assert pulseplate_envs, f"Expected Python proxy env in {workflow_path}"
        assert all("secrets." not in value for value in pulseplate_envs)
        assert APPROVED_PR_PROXY_ENV_EXPRESSION in pulseplate_envs
        assert APPROVED_PR_TRUSTED_HOST_EXPRESSION in pulseplate_envs
        if workflow_path != ".github/workflows/ci.yml":
            assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in workflow_text
            assert "secrets.PULSEPLATE_PYTHON_TRUSTED_HOST" not in workflow_text
        return

    assert APPROVED_PROXY_ENV_EXPRESSION in workflow_text
    assert APPROVED_TRUSTED_HOST_EXPRESSION in workflow_text


@pytest.mark.parametrize(
    "workflow_path",
    (
        ".github/workflows/ci.yml",
        ".github/workflows/frontend-ci.yml",
        ".github/workflows/build.yml",
    ),
)
def test_devpi_ci_secrets_are_not_exposed_to_feature_branch_pushes(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
    vulnerable_user_expression = "github.event_name != 'pull_request' && secrets.DEVPI_CI_USER"
    vulnerable_password_expression = (
        "github.event_name != 'pull_request' && secrets.DEVPI_CI_PASSWORD"
    )

    assert vulnerable_user_expression not in workflow_text
    assert vulnerable_password_expression not in workflow_text

    workflow = _load_workflow(workflow_path)
    user_envs = list(_iter_step_env_values(workflow, "DEVPI_CI_USER"))
    password_envs = list(_iter_step_env_values(workflow, "DEVPI_CI_PASSWORD"))

    assert user_envs, f"Expected DEVPI_CI_USER env in {workflow_path}"
    assert password_envs, f"Expected DEVPI_CI_PASSWORD env in {workflow_path}"
    assert set(user_envs) == {APPROVED_DEVPI_CI_USER_EXPRESSION}
    assert set(password_envs) == {APPROVED_DEVPI_CI_PASSWORD_EXPRESSION}


def test_pr_diagnostic_proxy_vars_must_stay_credential_free() -> None:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pr_resolver = workflow_text.split("- name: Resolve PR diagnostic package proxy", 1)[1].split(
        "- name: Resolve branch diagnostic package proxy",
        1,
    )[0]

    assert "secrets." not in pr_resolver
    assert "PULSEPLATE_PR_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}" in pr_resolver
    assert "*://*@*)" in pr_resolver
    assert "must be credential-free" in pr_resolver
    assert "DEVPI_CI_USER/DEVPI_CI_PASSWORD" in pr_resolver


def test_private_proxy_health_protected_credentials_are_main_only_netrc() -> None:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    branch_resolver = workflow_text.split("- name: Resolve branch diagnostic package proxy", 1)[
        1
    ].split("- name: Resolve protected main package proxy", 1,)[0]
    protected_resolver = workflow_text.split(
        "- name: Resolve protected main package proxy",
        1,
    )[
        1
    ].split("- name: Configure protected main package proxy authentication", 1,)[0]
    protected_auth = workflow_text.split(
        "- name: Configure protected main package proxy authentication",
        1,
    )[1].split("- name: Check private Python proxy health", 1,)[0]

    assert (
        "if: github.event_name != 'pull_request' && github.ref != 'refs/heads/main'"
        in branch_resolver
    )
    assert "secrets." not in branch_resolver
    assert "DEVPI_CI_USER:" not in branch_resolver
    assert "DEVPI_CI_PASSWORD:" not in branch_resolver
    assert (
        "if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'"
        in protected_resolver
    )
    assert (
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in protected_resolver
    )
    assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in protected_resolver
    assert "secrets.DEVPI_CI_USER" in protected_auth
    assert "secrets.DEVPI_CI_PASSWORD" in protected_auth
    assert "$HOME/.netrc" in protected_auth
    assert "[Rr][Oo][Oo][Tt]" in protected_auth
    assert "Root devpi credentials are forbidden" in protected_auth


def test_private_proxy_docs_use_devpi_shape_without_real_credentials() -> None:
    dependency_docs = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    runbook_text = (REPO_ROOT / "RUNBOOK_AGENT.md").read_text(encoding="utf-8")
    env_example_text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    devpi_simple_root = "https://packages.pulseplate.app/root/pulseplate/+simple/"
    assert devpi_simple_root in dependency_docs
    assert devpi_simple_root in runbook_text
    assert devpi_simple_root in env_example_text

    assert "DEVPI_CI_USER" in dependency_docs
    assert "DEVPI_CI_PASSWORD" in dependency_docs
    assert ".netrc" in dependency_docs
    assert "<ci-user>:<token>@" not in dependency_docs
    assert "root credentials are forbidden for ci" in dependency_docs.lower()
    assert "Repository variables must stay credential-free" in dependency_docs
    assert "root:" not in env_example_text
    assert "@" not in env_example_text.split("PULSEPLATE_PYTHON_INDEX_URL=", 1)[1].splitlines()[0]


def test_no_canonical_workflow_uses_unscoped_public_pip_install() -> None:
    for workflow_path in LOCKED_INSTALL_WORKFLOW_PATHS:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        lines = workflow_text.splitlines()
        for index, line in enumerate(lines):
            if not PIP_INSTALL_PATTERN.search(line):
                continue
            context = "\n".join(lines[max(0, index - 6) : index + 1])
            assert "PULSEPLATE_PYTHON_INDEX_URL" in context


def test_security_scan_workflow_uses_ci_lite_direct_proxy_setup() -> None:
    setup_step = _python_setup_step(".github/workflows/security.yml", "bandit")

    assert setup_step["with"]["python-version"] == CANONICAL_PYTHON
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    step_names = _workflow_step_names(".github/workflows/security.yml", "bandit")
    assert "Install security tooling" not in step_names
    audit_step = _workflow_step_by_name(
        ".github/workflows/security.yml",
        "bandit",
        "Run pip-audit (dependency audit)",
    )
    audit_script = audit_step["run"]
    assert "bash scripts/ci_pip_audit.sh" in audit_script
    assert "requirements-security.txt" not in audit_script
    assert not PIP_INSTALL_INVOCATION_PATTERN.search(audit_script)


def test_constraints_keep_dependency_security_floors_aligned() -> None:
    constraints_path = REPO_ROOT / "constraints.txt"
    requirements_in = REPO_ROOT / "requirements.in"
    requirements_ci_lite_in = REPO_ROOT / "requirements-ci-lite.in"
    requirements_docker_runtime_in = REPO_ROOT / "requirements-docker-runtime.in"

    constraints_text = constraints_path.read_text(encoding="utf-8")
    assert "flake8 removed in favor of ruff" not in constraints_text
    assert "replaces flake8" not in constraints_text
    assert _requirement_package_versions(constraints_path, "pip-audit") == {"2.10.1"}
    assert not _requirement_package_versions(constraints_path, "safety")
    assert _requirement_package_versions(requirements_ci_lite_in, "pip-audit") == {"2.10.1"}

    assert not _requirement_package_versions(constraints_path, "pyarrow")
    assert not _requirement_package_versions(requirements_in, "pyarrow")
    assert not _requirement_package_versions(requirements_ci_lite_in, "pyarrow")
    assert not _requirement_package_versions(requirements_docker_runtime_in, "pyarrow")
    for lock_surface in (
        REPO_ROOT / "requirements.txt",
        REPO_ROOT / "requirements-ci-lite.txt",
        REPO_ROOT / "requirements-docker-runtime.txt",
        REPO_ROOT / "requirements-lock.txt",
    ):
        assert not _requirement_package_versions(lock_surface, "pyarrow")
    assert _requirement_package_versions(REPO_ROOT / "requirements-data.in", "pyarrow") == {
        "25.0.0"
    }
    assert _requirement_package_specifiers(REPO_ROOT / "requirements-data.in", "pyarrow") == {
        (">=", "25.0.0"),
        ("<", "26.0.0"),
    }
    data_lock_versions = _requirement_package_versions(
        REPO_ROOT / "requirements-data.txt", "pyarrow"
    )
    assert data_lock_versions == {"25.0.0"}


def test_offline_builders_require_explicit_pyarrow_parquet_engine() -> None:
    for builder_path in (
        REPO_ROOT / "scripts" / "build_food_db.py",
        REPO_ROOT / "scripts" / "build_recipe_db.py",
    ):
        tree = ast.parse(builder_path.read_text(encoding="utf-8"), filename=str(builder_path))
        parquet_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "to_parquet"
        ]

        assert len(parquet_calls) == 1, builder_path
        keywords = {keyword.arg: keyword.value for keyword in parquet_calls[0].keywords}
        assert isinstance(keywords.get("engine"), ast.Constant), builder_path
        assert keywords["engine"].value == "pyarrow", builder_path
        assert isinstance(keywords.get("index"), ast.Constant), builder_path
        assert keywords["index"].value is False, builder_path


def test_ci_security_job_runs_pip_audit_from_ci_lite_toolchain() -> None:
    step_names = _workflow_step_names(".github/workflows/ci.yml", "security")
    assert "Install Safety" not in step_names

    audit_step = _workflow_step_by_name(
        ".github/workflows/ci.yml",
        "security",
        "Dependency audit with pip-audit",
    )
    audit_script = audit_step["run"]

    assert "bash scripts/ci_pip_audit.sh" in audit_script
    assert "requirements-security.txt" not in audit_script
    assert not PIP_INSTALL_INVOCATION_PATTERN.search(audit_script)


def test_safety_nltk_security_tooling_surface_is_removed() -> None:
    removed_paths = (
        REPO_ROOT / "requirements-security.txt",
        REPO_ROOT / "scripts" / "ci" / "run_safety_audit.py",
        REPO_ROOT / ".github" / "scripts" / "parse-safety-report.py",
        REPO_ROOT / "safety-policy.yaml",
        REPO_ROOT / "safety-policy.toml",
    )
    for removed_path in removed_paths:
        assert not removed_path.exists(), f"{removed_path} must not be restored"

    for requirement_path in (
        REPO_ROOT / "constraints.txt",
        REPO_ROOT / "requirements-all.txt",
        REPO_ROOT / "requirements-ci-lite.in",
        REPO_ROOT / "requirements-ci-lite.txt",
    ):
        package_names = _requirement_package_names(requirement_path)
        assert "safety" not in package_names
        assert "safety-schemas" not in package_names
        assert "nltk" not in package_names

    workflow_text = "\n".join(
        (
            (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
            (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8"),
            (REPO_ROOT / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8"),
        )
    )
    assert "SAFETY_API_KEY" not in workflow_text
    assert "run_safety_audit.py" not in workflow_text
    assert "requirements-security.txt" not in workflow_text


@pytest.mark.parametrize(
    "job_name", ("test", "performance-test", "integration-test", "coverage-merge")
)
def test_nightly_workflow_jobs_use_runtime_dev_direct_proxy_setup(job_name: str) -> None:
    setup_step = _python_setup_step(".github/workflows/nightly.yml", job_name)

    assert setup_step["with"]["python-version"] == CANONICAL_PYTHON
    assert setup_step["with"]["requirements-profile"] == "runtime-dev"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    assert all(
        "install_locked_python_requirements.py" not in step.get("run", "")
        for step in _workflow_steps(".github/workflows/nightly.yml", job_name)
    )


def test_ci_main_full_suite_checkout_uses_pinned_checkout_action() -> None:
    """Ensure the main CI diagnostic job keeps the immutable checkout action pin."""
    checkout_step = _workflow_step_by_name(".github/workflows/ci.yml", "test-main", "Checkout")

    assert checkout_step["uses"] == PINNED_CHECKOUT_ACTION


def test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job() -> None:
    import yaml

    ci_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    jobs = ci_workflow["jobs"]

    direct_proxy_jobs = (
        "lint",
        "security",
        "openapi-sync",
        "diff-coverage",
        "test-pr",
        "test-feature",
        "test-main",
    )
    for job_name in direct_proxy_jobs:
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["install-mode"] == "direct-proxy"

    for job_name in ("lint", "security", "openapi-sync", "diff-coverage"):
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["requirements-profile"] == "ci-lite"
        assert "install-dev-deps" not in setup_step["with"]

    for job_name in ("test-pr", "test-feature", "test-main"):
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["requirements-profile"] == "ci-test"
        assert "install-test-deps" not in setup_step["with"]
        assert all(step.get("name") != "Install dependencies" for step in jobs[job_name]["steps"])


def test_frontend_ci_workflow_uses_ci_lite_python_setup() -> None:
    setup_step = _python_setup_step(".github/workflows/frontend-ci.yml", "build-and-test")
    workflow_events = _workflow_events(".github/workflows/frontend-ci.yml")
    expected_paths = (
        "requirements.txt",
        "requirements-ci-lite.in",
        "requirements-ci-lite.txt",
        "constraints.txt",
        ".github/actions/python-setup/**",
        "scripts/ci/install_locked_python_requirements.py",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/emergency_python_wheels.json",
        "tests/test_python_supply_chain_controls.py",
    )

    assert setup_step["with"]["python-version"] == "${{ env.PYTHON_VERSION }}"
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"
    for event_name in ("pull_request", "push"):
        event_paths = workflow_events[event_name]["paths"]
        for expected_path in expected_paths:
            assert expected_path in event_paths


@pytest.mark.parametrize("job_name", ("rag-release-gates-smoke", "rag-release-gates-weekly"))
def test_rag_release_gates_use_locked_ci_lite_installer(job_name: str) -> None:
    setup_step = _python_setup_step(".github/workflows/rag-release-gates.yml", job_name)
    settings = setup_step["with"]

    assert APPROVED_PROXY_ENV_EXPRESSION in (
        REPO_ROOT / ".github" / "workflows" / "rag-release-gates.yml"
    ).read_text(encoding="utf-8")
    assert settings["python-version"] == "3.13.14"
    assert settings["requirements-profile"] == "ci-lite"
    assert settings["ci-lite-requirements-file"] == "requirements-ci-lite.txt"
    assert settings["constraints-file"] == "constraints.txt"
    assert settings["install-mode"] == "direct-proxy"
    assert settings["skip-base-install"] == "false"
    run_blocks = "\n".join(
        str(step.get("run", ""))
        for step in _workflow_steps(".github/workflows/rag-release-gates.yml", job_name)
    )
    assert "scripts/ci/install_locked_python_requirements.py" not in run_blocks
    assert "python3 -m pip install" not in run_blocks


def test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build() -> None:
    build_step = _workflow_step_by_name(
        ".github/workflows/frontend-ci.yml",
        "build-and-test",
        "Build frontend",
    )
    build_env = build_step.get("env")
    vite_config = (REPO_ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert isinstance(build_env, dict)
    assert "CODECOV_TOKEN" not in build_env
    assert "secrets.CODECOV_TOKEN" not in str(build_step)
    assert build_env["CODECOV_BUNDLE_ANALYSIS"] == (
        "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && 'true' || 'false' }}"
    )
    assert "@codecov/vite-plugin" not in vite_config
    assert "codecovVitePlugin" not in vite_config
    assert "uploadToken" not in vite_config
    assert "process.env.CODECOV_TOKEN" not in vite_config


def test_test_dependency_profile_is_split_from_dev_tooling() -> None:
    requirements_test = (REPO_ROOT / "requirements-test.txt").read_text(encoding="utf-8")

    assert "httpx2==" in requirements_test
    assert "pytest==9.1.1" in requirements_test
    assert "pytest-cov==7.1.0" in requirements_test
    assert "pytest-xdist==3.8.0" in requirements_test
    assert "hypothesis==6.165.10" in {line.strip() for line in requirements_test.splitlines()}
    assert "faker==40.37.0" in requirements_test
    assert "coverage[toml]==7.15.4" in requirements_test
    assert "pgvector==" in requirements_test
    assert "bandit==" not in requirements_test
    assert "pre-commit==" not in requirements_test
    assert "pip-audit==" not in requirements_test
    assert "mypy==" not in requirements_test
    assert "ruff==" not in requirements_test
    assert "sentence-transformers==" not in requirements_test
    assert "transformers==" not in requirements_test
    assert "torch==" not in requirements_test


def test_coverage_html_context_is_safely_escaped(tmp_path: Path) -> None:
    """Coverage must not render a context label as executable HTML."""
    import coverage

    raw_context = "</script><script>window.pulseplateCoverageProbe=1</script>"
    source = tmp_path / "coverage_probe.py"
    source.write_text("value = 42\n", encoding="utf-8")

    cov = coverage.Coverage(
        config_file=False,
        data_file=str(tmp_path / ".coverage"),
    )
    cov.start()
    cov.switch_context(raw_context)
    runpy.run_path(str(source))
    cov.stop()
    cov.save()

    report_dir = tmp_path / "htmlcov"
    cov.html_report(directory=str(report_dir), show_contexts=True)

    report_files = tuple(report_dir.rglob("*.html"))
    rendered_report = "\n".join(path.read_text(encoding="utf-8") for path in report_files)
    assert report_files
    assert raw_context not in rendered_report
    assert "window.pulseplateCoverageProbe=1" in rendered_report


def test_coverage_canary_runs_in_ci_lite_pre_commit() -> None:
    runner = (REPO_ROOT / "scripts/run-backend-tests-pre-commit.sh").read_text(encoding="utf-8")
    dependency_surface_block = runner.split(
        "declare -a PYTHON_DEPENDENCY_TESTCLIENT_SURFACE_FILES=(", 1
    )[1].split("\n)", 1)[0]
    dependency_test_block = runner.split("add_python_dependency_testclient_tests() {", 1)[1].split(
        "\n}", 1
    )[0]
    deselect = (
        "--deselect=tests/test_python_supply_chain_controls.py::"
        "test_coverage_html_context_is_safely_escaped"
    )
    requirements_ci_lite = (REPO_ROOT / "requirements-ci-lite.txt").read_text(encoding="utf-8")

    assert deselect not in runner
    assert '"requirements-ci-lite.in"' in dependency_surface_block
    assert '"requirements-ci-lite.txt"' in dependency_surface_block
    assert '"scripts/ci/compile_locked_python_requirements.py"' in dependency_surface_block
    assert (
        'EXTRA_TEST_FILES+=("tests/test_python_supply_chain_controls.py")' in dependency_test_block
    )
    assert "coverage==7.15.4" in requirements_ci_lite


def test_ci_lite_dependency_profile_excludes_ml_gpu_stack() -> None:
    requirements_ci_lite = (REPO_ROOT / "requirements-ci-lite.txt").read_text(encoding="utf-8")

    assert "fastapi==" in requirements_ci_lite
    assert "sqlalchemy==" in requirements_ci_lite
    assert "openai==" in requirements_ci_lite
    assert "pre-commit==" in requirements_ci_lite
    assert "bandit==" in requirements_ci_lite
    assert "diff-cover==" in requirements_ci_lite
    assert "pytest==" in requirements_ci_lite
    assert "coverage==7.15.4" in requirements_ci_lite
    assert "sentence-transformers==" not in requirements_ci_lite
    assert "transformers==" not in requirements_ci_lite
    assert "torch==" not in requirements_ci_lite
    assert "pgvector==" not in requirements_ci_lite
    assert "triton==" not in requirements_ci_lite
    assert "cuda-bindings==" not in requirements_ci_lite
    assert "nvidia-cublas-cu12==" not in requirements_ci_lite
    assert "httpx2==" not in requirements_ci_lite


def test_httpx2_testclient_backend_stays_dev_and_test_only() -> None:
    for requirement_file in HTTPX2_TESTCLIENT_BACKEND_SURFACES:
        package_names = _requirement_package_names(REPO_ROOT / requirement_file)
        assert canonicalize_name("httpx2") in package_names

    for requirement_file in HTTPX2_TESTCLIENT_RUNTIME_EXCLUDED_SURFACES:
        package_names = _requirement_package_names(REPO_ROOT / requirement_file)
        assert canonicalize_name("httpx2") not in package_names


def _assert_black_hook_lock_parity(repo_root: Path) -> None:
    """Compare live Black configuration; security floors remain with their canonical guard."""
    url = "https://github.com/psf/black"
    relation = DS3_HOOK_LOCK_PARITY[url]
    config = yaml.safe_load((repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repositories = [item for item in config["repos"] if item.get("repo") == url]
    assert len(repositories) == 1, "Black requires one hook repository"
    repository = repositories[0]
    assert len([hook for hook in repository["hooks"] if hook.get("id") == "black"]) == 1
    revision = repository["rev"]
    assert isinstance(revision, str)
    selected_version = Version(revision.removeprefix("v"))
    for filename in (*relation["inputs"], *relation["locks"]):
        requirements = [
            item
            for item in _requirement_entries(repo_root / filename)
            if canonicalize_name(item.name) == "black"
        ]
        assert len(requirements) == 1, f"{filename}: expected one Black owner"
        requirement = requirements[0]
        assert requirement.marker is None and requirement.url is None and not requirement.extras
        assert requirement.specifier, f"{filename}: missing Black constraint"
        if filename in relation["locks"]:
            specifiers = tuple(requirement.specifier)
            assert len(specifiers) == 1 and specifiers[0].operator == "=="
            assert "*" not in specifiers[0].version
            assert Version(specifiers[0].version) == selected_version, "Black hook/lock mismatch"
        else:
            assert requirement.specifier.contains(selected_version), "Black is outside source range"


def test_ds3_hook_revisions_match_finite_dev_lock_owners() -> None:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repositories = config["repos"]
    assert isinstance(repositories, list)
    for repository_url, relation in DS3_HOOK_LOCK_PARITY.items():
        hook_id = relation["hook_id"]
        hook_count = relation["hook_count"]
        package_name = relation["package"]
        if package_name == "black":
            _assert_black_hook_lock_parity(REPO_ROOT)
            continue
        exact_revision = relation["revision"]
        assert isinstance(hook_id, str)
        assert isinstance(hook_count, int)
        assert isinstance(package_name, str)
        assert isinstance(exact_revision, str)
        matching_repositories = [
            repository
            for repository in repositories
            if isinstance(repository, dict) and repository.get("repo") == repository_url
        ]
        assert len(matching_repositories) == 1, repository_url
        repository = matching_repositories[0]
        assert repository.get("rev") == exact_revision

        hooks = repository.get("hooks")
        assert isinstance(hooks, list)
        matching_hooks = [
            hook for hook in hooks if isinstance(hook, dict) and hook.get("id") == hook_id
        ]
        assert len(matching_hooks) == hook_count

        inputs = relation["inputs"]
        assert isinstance(inputs, dict)
        for input_path, expected_specifiers in inputs.items():
            assert (
                _requirement_package_specifiers(REPO_ROOT / input_path, package_name)
                == expected_specifiers
            )

        locks = relation["locks"]
        assert isinstance(locks, tuple)
        for lock_path in locks:
            assert _requirement_package_versions(REPO_ROOT / lock_path, package_name) == {
                exact_revision.removeprefix("v")
            }

    governed_packages = {
        canonicalize_name(str(relation["package"])) for relation in DS3_HOOK_LOCK_PARITY.values()
    }
    governed_packages.update({"coverage", "faker", "hypothesis", "types-pyyaml"})
    for excluded_surface in DS3_RUNTIME_AND_OPTIONAL_EXCLUDED_SURFACES:
        assert _requirement_package_names(REPO_ROOT / excluded_surface).isdisjoint(
            governed_packages
        )


def test_ds3_mypy_hook_remains_isolated_changed_file_pre_push_guard() -> None:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    matching_repositories = [
        repository
        for repository in config["repos"]
        if repository.get("repo") == "https://github.com/pre-commit/mirrors-mypy"
    ]
    assert len(matching_repositories) == 1
    mypy_repository = matching_repositories[0]
    matching_hooks = [hook for hook in mypy_repository["hooks"] if hook.get("id") == "mypy"]
    assert len(matching_hooks) == 1
    mypy_hook = matching_hooks[0]

    assert mypy_hook["stages"] == ["pre-push"]
    assert "pass_filenames" not in mypy_hook
    assert "always_run" not in mypy_hook
    for forbidden_override in ("entry", "exclude", "exclude_types", "types", "types_or"):
        assert forbidden_override not in mypy_hook
    assert mypy_hook["args"] == ["--pretty", "--show-error-codes", "--follow-imports=skip"]
    assert mypy_hook["files"] == DS3_MYPY_CHANGED_FILE_REGEX

    changed_file_filter = re.compile(mypy_hook["files"])
    assert changed_file_filter.fullmatch("app/main.py")
    assert changed_file_filter.fullmatch("scripts/ci/check_python_dependency_surfaces.py")
    assert changed_file_filter.fullmatch("providers/example.py")
    assert changed_file_filter.fullmatch("main.py")
    assert changed_file_filter.fullmatch("tests/test_main.py") is None

    pydantic_runtime_versions = _requirement_package_versions(
        REPO_ROOT / "requirements.txt", "pydantic"
    )
    types_pyyaml_dev_versions = _requirement_package_versions(
        REPO_ROOT / "requirements-dev.txt", "types-pyyaml"
    )
    assert pydantic_runtime_versions == {"2.13.4"}
    assert types_pyyaml_dev_versions == {"6.0.12.20260815"}
    assert mypy_hook["additional_dependencies"] == [
        "pydantic==2.13.4",
        "types-PyYAML==6.0.12.20260815",
    ]


def test_runtime_dependency_profiles_pin_fastapi_pydantic_refresh() -> None:
    expected_runtime_pins = {
        "fastapi": "0.138.1",
        "pydantic": "2.13.4",
        "pydantic-core": "2.46.4",
        "starlette": "1.3.1",
    }

    for lockfile in (
        "requirements.txt",
        "requirements-ci-lite.txt",
        "requirements-docker-runtime.txt",
        "requirements-lock.txt",
    ):
        lock_path = REPO_ROOT / lockfile
        for package_name, expected_version in expected_runtime_pins.items():
            assert _requirement_package_specifiers(lock_path, package_name) == {
                ("==", expected_version)
            }


@pytest.mark.parametrize(
    ("package_name", "expected_specifiers"),
    [
        ("click", {(">=", "8.3.3"), ("<", "9.0.0")}),
    ],
)
def test_runtime_source_profiles_keep_single_security_floor(
    package_name: str, expected_specifiers: set[tuple[str, str]]
) -> None:
    for source_file in (
        "requirements.in",
        "requirements-ci-lite.in",
        "requirements-docker-runtime.in",
    ):
        source_path = REPO_ROOT / source_file
        package_requirements = [
            requirement
            for requirement in _requirement_entries(source_path)
            if canonicalize_name(requirement.name) == package_name
        ]

        assert len(package_requirements) == 1
        assert {
            (specifier.operator, specifier.version)
            for specifier in package_requirements[0].specifier
        } == expected_specifiers


def test_click_security_pin_covers_existing_lock_surfaces() -> None:
    expected_pins = {"click": "8.3.3"}
    lockfiles = (
        "requirements.txt",
        "requirements-ci-lite.txt",
        "requirements-dev.txt",
        "requirements-docker-runtime.txt",
        "requirements-lock.txt",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.txt",
    )

    for lockfile in lockfiles:
        lock_path = REPO_ROOT / lockfile
        package_names = _requirement_package_names(lock_path)
        for package_name, expected_version in expected_pins.items():
            if canonicalize_name(package_name) not in package_names:
                continue
            assert _requirement_package_specifiers(lock_path, package_name) == {
                ("==", expected_version)
            }


def test_base_runtime_dependency_profile_excludes_vector_ml_stack() -> None:
    requirements_runtime = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "fastapi==" in requirements_runtime
    assert "sqlalchemy==" in requirements_runtime
    assert "sentence-transformers==" not in requirements_runtime
    assert "transformers==" not in requirements_runtime
    assert "torch==" not in requirements_runtime
    assert "pgvector==" not in requirements_runtime
    assert "pyarrow==" not in requirements_runtime


def test_docker_runtime_dependency_profile_excludes_ci_and_vector_stack() -> None:
    requirements_runtime = (REPO_ROOT / "requirements-docker-runtime.txt").read_text(
        encoding="utf-8"
    )

    assert "fastapi==" in requirements_runtime
    assert "sqlalchemy==" in requirements_runtime
    assert "bandit==" not in requirements_runtime
    assert "diff-cover==" not in requirements_runtime
    assert "pyarrow==" not in requirements_runtime
    assert "pre-commit==" not in requirements_runtime
    assert "pytest==" not in requirements_runtime
    assert "sentence-transformers==" not in requirements_runtime
    assert "transformers==" not in requirements_runtime
    assert "torch==" not in requirements_runtime
    assert "pgvector==" not in requirements_runtime
    assert "httpx2==" not in requirements_runtime


def test_rag_vector_dependency_profile_contains_extracted_vector_ml_stack() -> None:
    requirements_rag_vector = (REPO_ROOT / "requirements-rag-vector.txt").read_text(
        encoding="utf-8"
    )

    assert "fastembed==" in requirements_rag_vector
    assert "pgvector==" in requirements_rag_vector
    for package in OPTIONAL_VECTOR_FORBIDDEN_PACKAGES:
        assert f"{package}==" not in requirements_rag_vector
    assert "nvidia-" not in requirements_rag_vector


def test_rag_vector_lock_profiles_keep_matching_package_pins() -> None:
    vector_pairs = _requirement_pin_pairs(REPO_ROOT / "requirements-rag-vector.txt")
    vector_cpu_pairs = _requirement_pin_pairs(REPO_ROOT / "requirements-rag-vector-cpu.txt")

    assert vector_pairs == vector_cpu_pairs


def test_torch_and_vector_stack_stay_optional_to_rag_vector_profiles() -> None:
    for requirement_file in DEFAULT_INSTALL_REQUIREMENT_FILES:
        package_names = _requirement_package_names(REPO_ROOT / requirement_file)
        disallowed_packages = (
            OPTIONAL_VECTOR_STACK_PACKAGES
            if requirement_file != "requirements-test.txt"
            else ("fastembed", "sentence-transformers", "torch", "transformers")
        )
        for package in disallowed_packages:
            assert canonicalize_name(package) not in package_names
        for package in OPTIONAL_VECTOR_FORBIDDEN_PACKAGES:
            assert canonicalize_name(package) not in package_names

    for requirement_file in OPTIONAL_VECTOR_REQUIREMENT_FILES:
        requirement_path = REPO_ROOT / requirement_file
        package_names = _requirement_package_names(requirement_path)
        for package in OPTIONAL_VECTOR_STACK_PACKAGES:
            assert canonicalize_name(package) in package_names
        for package in OPTIONAL_VECTOR_FORBIDDEN_PACKAGES:
            assert canonicalize_name(package) not in package_names
        requirement_text = requirement_path.read_text(encoding="utf-8")
        assert "nvidia-" not in requirement_text


def test_eval_and_data_dependency_profiles_are_compiled_and_pinned() -> None:
    expected_sources = {
        "requirements-data.txt": "requirements-data.in",
        "requirements-evals.txt": "requirements-evals.in",
    }
    assert set(expected_sources) == set(LOCAL_MANUAL_EVAL_DATA_LOCKFILES)

    for requirement_file in LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES:
        assert (REPO_ROOT / requirement_file).is_file()

    data_input = REPO_ROOT / "requirements-data.in"
    eval_input = REPO_ROOT / "requirements-evals.in"
    assert _requirement_package_names(data_input) >= {"pandas", "pyarrow"}
    assert _requirement_package_names(eval_input).isdisjoint(
        {canonicalize_name(package) for package in DISABLED_RAGAS_EVAL_PACKAGES}
    )
    assert "\n-c requirements.txt\n" in f"\n{data_input.read_text(encoding='utf-8')}\n"
    eval_input_text = eval_input.read_text(encoding="utf-8")
    assert "\n-c requirements.txt\n" not in f"\n{eval_input_text}\n"
    assert "GHSA-95ww-475f-pr4f" in eval_input_text
    assert "GHSA-w8v5-vhqr-4h9v" in eval_input_text
    assert "RAGAS native execution is disabled" in eval_input_text

    for lockfile, source_file in expected_sources.items():
        lock_path = REPO_ROOT / lockfile
        lock_text = lock_path.read_text(encoding="utf-8")
        requirements = _requirement_entries(lock_path)

        surface = next(
            item for item in dependency_surfaces.DEPENDENCY_SURFACES if item.lockfile == lockfile
        )
        assert lock_text.startswith(dependency_surfaces.render_governed_lock_header(surface))
        assert source_file in lock_text
        if lockfile == "requirements-evals.txt":
            assert not requirements
        else:
            assert requirements
        assert "--index-url" not in lock_text
        assert "--extra-index-url" not in lock_text
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in lock_text
        assert str(REPO_ROOT) not in lock_text
        assert "/Users/" not in lock_text
        assert "http://" not in lock_text
        assert "https://" not in lock_text
        assert "ssh://" not in lock_text
        assert "file://" not in lock_text
        assert "git+" not in lock_text
        assert " @ " not in lock_text
        assert "--find-links" not in lock_text
        assert "--editable" not in lock_text
        assert "\n-e " not in lock_text
        assert all(_requirement_is_exact_pin(requirement) for requirement in requirements)


def test_eval_and_data_dependencies_stay_out_of_default_install_profiles() -> None:
    blocked_packages = {canonicalize_name(package) for package in LOCAL_MANUAL_EVAL_DATA_PACKAGES}

    for requirement_file in DEFAULT_AND_TOOLING_REQUIREMENT_FILES:
        requirement_path = REPO_ROOT / requirement_file
        if not requirement_path.exists():
            continue
        package_names = _requirement_package_names(requirement_path)
        assert blocked_packages.isdisjoint(package_names)


def test_eval_and_data_profiles_do_not_join_shared_install_routing() -> None:
    action_text = (REPO_ROOT / ".github" / "actions" / "python-setup" / "action.yml").read_text(
        encoding="utf-8"
    )
    docker_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore_text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "data" not in locked_installer.REQUIREMENTS_PROFILES
    assert "evals" not in locked_installer.REQUIREMENTS_PROFILES
    assert "requirements-data" not in action_text
    assert "requirements-evals" not in action_text
    assert "requirements-data" not in docker_text
    assert "requirements-evals" not in docker_text
    assert "!requirements-data" not in dockerignore_text
    assert "!requirements-evals" not in dockerignore_text


def test_dependency_docs_describe_eval_and_data_profiles_as_local_manual() -> None:
    dependency_docs = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    evals_agents = (REPO_ROOT / "evals" / "AGENTS.md").read_text(encoding="utf-8")
    ragas_setup = (REPO_ROOT / "docs" / "evals" / "RAGAS_SETUP.md").read_text(encoding="utf-8")

    for requirement_file in LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES:
        assert requirement_file in dependency_docs

    assert "local/manual offline" in dependency_docs
    assert "not shared GitHub Actions `requirements-profile` values" in dependency_docs
    assert "runtime, Docker, or generic CI lanes" in dependency_docs
    assert "scripts/build_food_db.py" in dependency_docs
    assert "scripts/build_recipe_db.py" in dependency_docs
    assert "pandas" in dependency_docs
    assert "pyarrow" in dependency_docs
    assert "sqlite+aiosqlite" in dependency_docs
    assert "production/staging Postgres policy is unchanged" in dependency_docs
    assert "without unrelated lock churn" in dependency_docs
    normalized_dependency_docs = " ".join(dependency_docs.casefold().split())
    assert "runtime, docker runtime, ci-lite, and `requirements-lock.txt`" in (
        normalized_dependency_docs
    )
    assert "legacy_compat_transitional" in dependency_docs
    assert "RAGAS native execution is disabled" in dependency_docs
    assert "GHSA-95ww-475f-pr4f" in dependency_docs
    assert "GHSA-w8v5-vhqr-4h9v" in dependency_docs
    assert "diskcache" in dependency_docs.casefold()
    assert 'LOCK_PROFILES="data evals" make requirements-locks' in dependency_docs
    assert "requirements-evals.in" in evals_agents
    assert "requirements-evals.txt" in evals_agents
    assert "RAGAS native execution is disabled" in evals_agents
    assert "lazy-imported" in evals_agents
    assert "requirements-evals.in" in ragas_setup
    assert "requirements-evals.txt" in ragas_setup
    assert "RAGAS native execution is disabled" in ragas_setup
    assert "GHSA-95ww-475f-pr4f" in ragas_setup
    assert "GHSA-w8v5-vhqr-4h9v" in ragas_setup
    assert 'LOCK_PROFILES="evals" make requirements-locks' in ragas_setup


def test_dependency_docs_document_httpx2_testclient_backend_boundary() -> None:
    dependency_docs = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    contract_docs = (REPO_ROOT / "docs" / "contracts" / "PYTHON_DEPENDENCY_SURFACES.md").read_text(
        encoding="utf-8"
    )
    requirements_guide = (REPO_ROOT / "REQUIREMENTS.md").read_text(encoding="utf-8")

    for docs_text in (dependency_docs, contract_docs, requirements_guide):
        normalized_docs = " ".join(docs_text.casefold().split())
        assert "httpx2" in docs_text
        assert "starlette testclient backend" in normalized_docs
        assert "runtime, docker runtime, and ci-lite" in normalized_docs


def test_production_target_docker_workflows_use_runtime_requirements_profile() -> None:
    cd_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "cd.yml").read_text(encoding="utf-8")
    )
    build_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    )
    trivy_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(encoding="utf-8")
    )

    def _build_args_for_step(workflow: dict[str, object], job_name: str, step_name: str) -> str:
        steps = workflow["jobs"][job_name]["steps"]
        for step in steps:
            if step.get("name") == step_name:
                return step["with"]["build-args"]
        raise AssertionError(f"Missing workflow step: {job_name}.{step_name}")

    local_build_args = _build_args_for_step(
        build_workflow, "build", "Build Docker image (local, for tests)"
    )
    publish_build_args = _build_args_for_step(
        build_workflow, "publish", "Build Docker image for publish scan"
    )
    cd_staging_build_args = _build_args_for_step(
        cd_workflow, "build", "Build & Push backend image (staging)"
    )
    cd_production_build_args = _build_args_for_step(
        cd_workflow, "build-production", "Build & Push image (production)"
    )
    trivy_build_args = _build_args_for_step(
        trivy_workflow, "build", "Build Docker image (production target)"
    )

    expected_arg = "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt"
    assert expected_arg in local_build_args
    assert expected_arg in publish_build_args
    assert expected_arg in cd_staging_build_args
    assert expected_arg in cd_production_build_args
    assert expected_arg in trivy_build_args


def test_provenance_enabled_docker_builds_keep_private_index_out_of_build_args() -> None:
    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_scan_with = publish_scan_step["with"]
    publish_scan_build_args = publish_scan_with["build-args"]
    publish_scan_secret_envs = publish_scan_with["secret-envs"]
    publish_scan_secret_files = publish_scan_with["secret-files"]

    assert publish_scan_with["push"] is False
    assert publish_scan_with["load"] is True
    assert publish_scan_with["provenance"] is False
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in publish_scan_build_args
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in publish_scan_build_args
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in publish_scan_secret_envs
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in publish_scan_secret_envs
    assert "pp_netrc=${{ runner.temp }}/pulseplate-docker-netrc" in publish_scan_secret_files

    for step in _pushed_docker_steps_with_secret_index_args():
        assert step["with"]["provenance"] == "mode=min"
        build_args = step["with"]["build-args"]
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in build_args
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in build_args
        build_secret_envs = step["with"]["secret-envs"]
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in build_secret_envs
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in build_secret_envs


def test_build_workflow_passes_netrc_secret_file_to_private_index_docker_builds() -> None:
    dockerfile_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "--mount=type=secret,id=pp_netrc,required=false" in dockerfile_text
    assert "cp /run/secrets/pp_netrc /root/.netrc" in dockerfile_text
    assert "trap 'rm -f /root/.netrc' EXIT" in dockerfile_text

    for job_name, build_step_name in (
        ("build", "Build Docker image (local, for tests)"),
        ("publish", "Build Docker image for publish scan"),
    ):
        steps = _workflow_steps(".github/workflows/build.yml", job_name)
        step_names = [str(step["name"]) for step in steps]
        auth_step = _workflow_step_by_name(
            ".github/workflows/build.yml",
            job_name,
            "Prepare private Python index Docker authentication",
        )
        build_step = _workflow_step_by_name(
            ".github/workflows/build.yml",
            job_name,
            build_step_name,
        )
        cleanup_step = _workflow_step_by_name(
            ".github/workflows/build.yml",
            job_name,
            "Remove private Python index Docker authentication",
        )

        assert step_names.index(
            "Prepare private Python index Docker authentication"
        ) < step_names.index(build_step_name)
        assert step_names.index(build_step_name) < step_names.index(
            "Remove private Python index Docker authentication"
        )

        auth_env = auth_step["env"]
        assert auth_env["DEVPI_CI_USER"] == APPROVED_DEVPI_CI_USER_EXPRESSION
        assert auth_env["DEVPI_CI_PASSWORD"] == APPROVED_DEVPI_CI_PASSWORD_EXPRESSION
        assert auth_env["PULSEPLATE_PYTHON_INDEX_URL"] == "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"

        auth_script = auth_step["run"]
        assert 'auth_file="$RUNNER_TEMP/pulseplate-docker-netrc"' in auth_script
        assert ': > "$auth_file"' in auth_script
        assert "Root devpi credentials are forbidden" in auth_script
        assert "PULSEPLATE_PYTHON_INDEX_URL must not contain credentials" in auth_script

        build_with = build_step["with"]
        assert "pp_netrc=${{ runner.temp }}/pulseplate-docker-netrc" in build_with["secret-files"]
        assert cleanup_step["if"] == "${{ always() }}"
        assert cleanup_step["shell"] == "bash"
        assert 'rm -f "$RUNNER_TEMP/pulseplate-docker-netrc"' in cleanup_step["run"]


def test_production_target_docker_workflows_run_runtime_surface_guard() -> None:
    workflow_paths = (
        ".github/workflows/build.yml",
        ".github/workflows/trivy.yml",
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        assert "scripts/ci/check_docker_runtime_dependency_surface.py" in workflow_text
        assert "--blocked-debian-package apt" in workflow_text
        assert "--blocked-debian-package gpgv" in workflow_text
        assert "--blocked-debian-package libgnutls30" in workflow_text
        assert "--output-json docker-runtime-dependency-surface.json" in workflow_text


def test_dependency_submission_workflow_tracks_runtime_and_optional_manifests() -> None:
    workflow_events = _workflow_events(".github/workflows/python-dependency-submission.yml")
    expected_paths = {
        "requirements-data.in",
        "requirements-data.txt",
        "requirements-docker-runtime.in",
        "requirements-docker-runtime.txt",
        "requirements-evals.in",
        "requirements-evals.txt",
        "requirements-rag-vector.in",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.in",
        "requirements-rag-vector-cpu.txt",
    }

    for event_name in ("push", "pull_request"):
        event_paths = set(workflow_events[event_name]["paths"])
        assert expected_paths <= event_paths


def test_python_dependency_submission_uses_profile_scoped_graph_roots() -> None:
    workflow = _load_workflow(".github/workflows/python-dependency-submission.yml")
    jobs = workflow["jobs"]
    action = "advanced-security/component-detection-dependency-submission-action@" + "".join(
        (
            "b876b8cc",
            "341a5397",
            "0394b33e",
            "a0ca4e86",
            "c25542de",
        )
    )

    pr_validation_job = jobs["dependency-submission-pr-validation"]
    assert pr_validation_job["if"] == "github.event_name == 'pull_request'"
    assert pr_validation_job["permissions"] == {"contents": "read"}
    assert "dependency submission API" in pr_validation_job["steps"][0]["run"]

    expected_jobs = {
        "runtime-dependency-submission": {
            "correlator": "python-dependency-submission-runtime",
            "root": "pulseplate-python-runtime-dependency-root",
            "must_copy": ("requirements-ci-lite.txt", "requirements-docker-runtime.txt"),
            "must_not_copy": ("requirements-evals.txt", "requirements-rag-vector.txt"),
        },
        "eval-data-dependency-submission": {
            "correlator": "python-dependency-submission-eval-data",
            "root": "pulseplate-python-eval-data-dependency-root",
            "must_copy": ("requirements-data.txt", "requirements-evals.txt"),
            "must_not_copy": ("requirements-ci-lite.txt", "requirements-rag-vector.txt"),
        },
        "rag-vector-dependency-submission": {
            "correlator": "python-dependency-submission-rag-vector",
            "root": "pulseplate-python-rag-vector-dependency-root",
            "must_copy": ("requirements-rag-vector.txt", "requirements-rag-vector-cpu.txt"),
            "must_not_copy": ("requirements-ci-lite.txt", "requirements-evals.txt"),
        },
    }
    observed_correlators: set[str] = set()

    for job_name, expectation in expected_jobs.items():
        job = jobs[job_name]
        assert job["if"] == "github.event_name != 'pull_request'"
        checkout_step = next(
            step for step in job["steps"] if step.get("uses") == PINNED_CHECKOUT_ACTION
        )
        assert checkout_step["with"] == {"persist-credentials": False}
        prepare_step = next(
            step for step in job["steps"] if step.get("name", "").startswith("Prepare ")
        )
        prepare_script = prepare_step["run"]
        assert expectation["root"] in prepare_script
        for manifest in expectation["must_copy"]:
            assert manifest in prepare_script
        for manifest in expectation["must_not_copy"]:
            assert manifest not in prepare_script

        submit_step = next(step for step in job["steps"] if step.get("uses") == action)
        submit_with = submit_step["with"]
        observed_correlators.add(submit_with["correlator"])
        assert submit_with["correlator"] == expectation["correlator"]
        assert submit_with["filePath"] == f"${{{{ runner.temp }}}}/{expectation['root']}"
        assert submit_with["detectorsCategories"] == "Pip"
        assert submit_with["detectorArgs"] == "Pip=EnableIfDefaultOff,SimplePip=EnableIfDefaultOff"

    assert observed_correlators == {
        "python-dependency-submission-runtime",
        "python-dependency-submission-eval-data",
        "python-dependency-submission-rag-vector",
    }
    assert "python-dependency-submission" not in observed_correlators


def test_security_scan_workflow_audits_runtime_and_optional_manifests() -> None:
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    ci_pip_audit_text = (REPO_ROOT / "scripts" / "ci_pip_audit.sh").read_text(encoding="utf-8")

    assert "bash scripts/ci_pip_audit.sh" in ci_text
    assert "bash scripts/ci_pip_audit.sh" in security_text
    assert "requirements-docker-runtime.txt" in ci_pip_audit_text
    assert "requirements-data.txt" in ci_pip_audit_text
    assert "requirements-evals.txt" in ci_pip_audit_text
    assert "requirements-rag-vector.txt" in ci_pip_audit_text
    assert "requirements-rag-vector-cpu.txt" in ci_pip_audit_text
    assert "|| true" not in ci_pip_audit_text
    assert "--no-deps" in ci_pip_audit_text
    assert "--disable-pip" in ci_pip_audit_text
    assert "--ignore-vuln" not in ci_pip_audit_text
    assert "CVE-2025-3000" not in ci_pip_audit_text


def test_pre_push_pip_audit_does_not_create_or_upgrade_an_installer_environment() -> None:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    pip_audit_hook = next(
        hook
        for repository in config["repos"]
        if repository.get("repo") == "https://github.com/pypa/pip-audit"
        for hook in repository["hooks"]
        if hook.get("id") == "pip-audit"
    )

    assert "--no-deps" in pip_audit_hook["args"]
    assert "--disable-pip" in pip_audit_hook["args"]


def _fake_strict_auditor(
    tmp_path: Path, *, fail_first: bool = False, malformed: bool = False
) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "audit-argv.jsonl"
    script = fake_bin / "pip-audit"
    program = r"""
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['--version']:
    print('pip-audit 2.10.1')
    raise SystemExit(0)
assert 'GH_TOKEN' not in os.environ and 'PULSEPLATE_PYTHON_INDEX_URL' not in os.environ
assert 'DEVPI_CI_PASSWORD' not in os.environ and 'PYTHONPATH' not in os.environ
assert 'synthetic-not-forwarded' not in os.environ.values()
args = sys.argv[1:]
with Path(__LOG__).open('a') as stream:
    stream.write(json.dumps(args) + '\n')
output = Path(args[args.index('-o') + 1])
if __FAIL__ and output.name == 'pip-audit-requirements.json':
    print('synthetic scanner failure', file=sys.stderr)
    raise SystemExit(7)
manifest = Path(args[args.index('-r') + 1])
pins = [line.strip().split('==') for line in manifest.read_text().splitlines() if line.strip() and not line.startswith('#')]
report = {'dependencies': [{'name': name, 'version': version, 'vulns': []} for name, version in pins], 'fixes': []}
output.write_text('{}\n' if __MALFORMED__ else json.dumps(report) + '\n')
print('synthetic scanner stderr', file=sys.stderr)
"""
    script.write_text(
        "#!"
        + sys.executable
        + "\n"
        + program.replace("__LOG__", repr(str(log)))
        .replace("__FAIL__", repr(fail_first))
        .replace("__MALFORMED__", repr(malformed))
    )
    script.chmod(0o755)
    return fake_bin, log


def _run_strict_audit_shell(tmp_path: Path, fake_bin: Path) -> subprocess.CompletedProcess[str]:
    for name in (
        "requirements.txt",
        "requirements-docker-runtime.txt",
        "requirements-data.txt",
        "requirements-evals.txt",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.txt",
    ):
        (tmp_path / name).write_text("example==1.0.0\n")
    env = os.environ.copy()
    env.update(
        CI="1",
        VENV_PYTHON=sys.executable,
        GH_TOKEN="synthetic-not-forwarded",
        GITHUB_TOKEN="synthetic-not-forwarded",
        PYPI_TOKEN="synthetic-not-forwarded",
        TWINE_PASSWORD="synthetic-not-forwarded",
        NETRC="synthetic-not-forwarded",
        DEVPI_CI_PASSWORD="synthetic-not-forwarded",
        PULSEPLATE_PYTHON_INDEX_URL="https://packages.example.invalid/simple/",
        PATH=os.pathsep.join((str(fake_bin), "/usr/bin", "/bin", "/usr/sbin", "/sbin")),
    )
    return subprocess.run(
        ["/bin/bash", str(REPO_ROOT / "scripts/ci_pip_audit.sh")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_pip_audit_helper_invokes_cpu_rag_vector_manifest(tmp_path: Path) -> None:
    fake_bin, log = _fake_strict_auditor(tmp_path)
    result = _run_strict_audit_shell(tmp_path, fake_bin)
    assert result.returncode == 0, result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    outputs = [command[command.index("-o") + 1] for command in commands]
    assert outputs == [
        "pip-audit-requirements.json",
        "pip-audit-requirements-docker-runtime.json",
        "pip-audit-requirements-data.json",
        "pip-audit-requirements-evals.json",
        "pip-audit-requirements-rag-vector.json",
        "pip-audit-requirements-rag-vector-cpu.json",
    ]
    for command, output in zip(commands, outputs, strict=True):
        assert command[2:] == ["--no-deps", "--disable-pip", "--strict", "-f", "json", "-o", output]
        assert "--ignore-vuln" not in command and "--timeout" not in command
        evidence = json.loads((tmp_path / output.replace(".json", ".evidence.json")).read_text())
        assert evidence["passed"] is True and evidence["upstream_comparison"] is False
        assert (
            evidence["original_coordinates"]
            == evidence["query_coordinates"]
            == {"example": "1.0.0"}
        )
        assert (
            tmp_path / output.replace(".json", ".stderr.log")
        ).read_text() == "synthetic scanner stderr\n"


def test_pip_audit_helper_scans_all_manifests_before_returning_failure(tmp_path: Path) -> None:
    fake_bin, log = _fake_strict_auditor(tmp_path, fail_first=True)
    result = _run_strict_audit_shell(tmp_path, fake_bin)
    assert result.returncode == 7
    assert "one or more dependency manifests failed audit" in result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(commands) == 6
    assert (tmp_path / "pip-audit-requirements.json").read_bytes() == b""
    assert (
        tmp_path / "pip-audit-requirements.stderr.log"
    ).read_text() == "synthetic scanner failure\n"
    evidence = json.loads((tmp_path / "pip-audit-requirements.evidence.json").read_text())
    assert evidence["scanner_exit"] == 7 and evidence["passed"] is False
    assert evidence["inventory_validation_error"] == "invalid_scanner_json"
    assert (tmp_path / "pip-audit-requirements-rag-vector-cpu.json").exists()


def test_pip_audit_helper_rejects_empty_object_reports_without_rewriting_raw_bytes(
    tmp_path: Path,
) -> None:
    fake_bin, log = _fake_strict_auditor(tmp_path, malformed=True)
    result = _run_strict_audit_shell(tmp_path, fake_bin)
    assert result.returncode == 1
    assert len(log.read_text().splitlines()) == 6
    assert (tmp_path / "pip-audit-requirements.json").read_bytes() == b"{}\n"
    evidence = json.loads((tmp_path / "pip-audit-requirements.evidence.json").read_text())
    assert evidence["inventory_validation_error"] == "invalid_scanner_report_shape"
    assert evidence["passed"] is False


def test_dependency_audit_uses_strict_pip_audit_helper_without_safety_legacy() -> None:
    workflow_paths = (
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        step_name = (
            "Dependency audit with pip-audit"
            if workflow_path.endswith("ci.yml")
            else "Run pip-audit (dependency audit)"
        )
        job_name = "security" if workflow_path.endswith("ci.yml") else "bandit"
        audit_step = _workflow_step_by_name(workflow_path, job_name, step_name)

        assert "bash scripts/ci_pip_audit.sh" in audit_step["run"]
        assert "SAFETY_API_KEY" not in workflow_text
        assert "run_safety_audit.py" not in workflow_text
        assert "requirements-security.txt" not in workflow_text
        assert "safety-*.json" not in workflow_text
        assert "safety-*.txt" not in workflow_text
        assert "safety-*.log" not in workflow_text
        assert "pip-audit-*.json" in workflow_text
        assert 'manifests=("requirements.txt")' not in workflow_text
        assert 'cp "${report_json}" safety-report.json' not in workflow_text
        assert ".github/scripts/parse-safety-report.py" not in workflow_text

    nightly_text = (REPO_ROOT / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8")
    assert "safety check --json" not in nightly_text
    assert "SAFETY_API_KEY" not in nightly_text
    assert "bash scripts/ci_pip_audit.sh" in nightly_text
    assert "pip-audit-*.json" in nightly_text


def test_bandit_high_gate_uses_shared_summary_helper_without_inline_parsers() -> None:
    workflow_paths = (
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
    )
    summary_helper_text = (REPO_ROOT / "scripts" / "ci" / "summarize_bandit_report.py").read_text(
        encoding="utf-8"
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        step_name = (
            "Enforce Bandit HIGH severity gate"
            if workflow_path.endswith("ci.yml")
            else "Run Bandit (security lint)"
        )
        job_name = "security" if workflow_path.endswith("ci.yml") else "bandit"
        bandit_step = _workflow_step_by_name(workflow_path, job_name, step_name)
        bandit_script = str(bandit_step["run"])

        assert "python3 scripts/ci/summarize_bandit_report.py" in workflow_text
        assert "--report bandit-report.json" in bandit_script
        assert "--fail-on-high" in bandit_script
        assert 'select(.issue_severity == "HIGH")' not in workflow_text
        assert "json.loads(report.read_text())" not in bandit_script

    assert "issue_severity" in summary_helper_text
    assert "fail_on_high" in summary_helper_text


def test_requirements_lock_excludes_optional_rag_vector_stack() -> None:
    requirements_lock = (REPO_ROOT / "requirements-lock.txt").read_text(encoding="utf-8")

    assert "pgvector==" not in requirements_lock
    assert "sentence-transformers==" not in requirements_lock
    assert "transformers==" not in requirements_lock
    assert "torch==" not in requirements_lock


def test_ci_risk_profile_tracks_runtime_and_optional_manifests() -> None:
    risk_profile_text = (REPO_ROOT / "scripts" / "ci" / "ci_risk_profile.py").read_text(
        encoding="utf-8"
    )

    assert '"requirements-docker-runtime.in"' in risk_profile_text
    assert '"requirements-docker-runtime.txt"' in risk_profile_text
    assert '"requirements-data.in"' in risk_profile_text
    assert '"requirements-data.txt"' in risk_profile_text
    assert '"requirements-evals.in"' in risk_profile_text
    assert '"requirements-evals.txt"' in risk_profile_text
    assert '"requirements-rag-vector.in"' in risk_profile_text
    assert '"requirements-rag-vector.txt"' in risk_profile_text
    assert '"requirements-rag-vector-cpu.in"' in risk_profile_text
    assert '"requirements-rag-vector-cpu.txt"' in risk_profile_text


def test_docker_workflows_emit_image_telemetry_artifacts() -> None:
    build_workflow_text = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8"
    )
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )

    for workflow_text in (
        build_workflow_text,
        trivy_workflow_text,
    ):
        assert "docker-runtime-dependency-surface.json" in workflow_text
        assert "scripts/ci/fetch_docker_image_baseline.py" in workflow_text
        assert "scripts/ci/docker_image_telemetry.py" in workflow_text
        assert "scripts/ci/check_docker_image_budget.py" in workflow_text
        assert "docs/telemetry/docker_image_baseline.production.json" in workflow_text
        assert "docs/telemetry/docker_image_budget.production.json" in workflow_text
        assert "--baseline-json docker-image-baseline.json" in workflow_text
        assert "docker-image-telemetry.json" in workflow_text
        assert "docker-image-telemetry.md" in workflow_text
        assert "docker-image-budget-check.json" in workflow_text
        assert "docker-image-budget-check.md" in workflow_text
        assert "GITHUB_STEP_SUMMARY" in workflow_text
        assert "actions/upload-artifact@" in workflow_text
        assert "workflow remains advisory-only" not in workflow_text

    build_workflow = _load_workflow(".github/workflows/build.yml")
    trivy_workflow = _load_workflow(".github/workflows/trivy.yml")

    build_job_permissions = build_workflow["jobs"]["build"]["permissions"]
    trivy_job_permissions = trivy_workflow["jobs"]["build"]["permissions"]
    producer_artifact_name = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Upload Docker telemetry artifact",
    )["with"]["name"]
    producer_artifact_paths = str(
        _workflow_step_by_name(
            ".github/workflows/build.yml",
            "build",
            "Upload Docker telemetry artifact",
        )["with"]["path"]
    )
    build_resolve_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Resolve Docker image telemetry baseline",
    )["run"]
    trivy_resolve_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Resolve Docker image telemetry baseline",
    )["run"]
    build_budget_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Enforce Docker image budget",
    )
    trivy_budget_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Enforce Docker image budget",
    )
    build_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Fail build job when Docker budget check failed",
    )
    trivy_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Fail trivy job when Docker budget check failed",
    )
    build_step_names = _workflow_step_names(".github/workflows/build.yml", "build")
    trivy_step_names = _workflow_step_names(".github/workflows/trivy.yml", "build")

    assert build_job_permissions["actions"] == "read"
    assert build_job_permissions["contents"] == "read"
    assert trivy_job_permissions["actions"] == "read"
    assert trivy_job_permissions["contents"] == "read"
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert producer_artifact_name == "docker-image-telemetry-build"
    assert producer_artifact_paths.splitlines().count("docker-image-telemetry.json") == 1
    assert f"--artifact-name {producer_artifact_name}" in build_resolve_step
    assert f"--artifact-name {producer_artifact_name}" in trivy_resolve_step
    assert "--workflow build.yml" in build_resolve_step
    assert "--workflow build.yml" in trivy_resolve_step
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in build_budget_step["run"]
    )
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in trivy_budget_step["run"]
    )
    assert build_budget_step["continue-on-error"] is True
    assert trivy_budget_step["continue-on-error"] is True
    assert build_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert trivy_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert build_step_names.index("Enforce Docker image budget") < build_step_names.index(
        "Test Docker image"
    )
    assert build_step_names.index("Test Docker image") < build_step_names.index(
        "Fail build job when Docker budget check failed"
    )
    assert trivy_step_names.index("Enforce Docker image budget") < trivy_step_names.index(
        "Run Trivy vulnerability scanner"
    )
    assert trivy_step_names.index("Run Trivy vulnerability scanner") < trivy_step_names.index(
        "Fail trivy job when Docker budget check failed"
    )


def test_pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args() -> None:
    """Max-mode BuildKit provenance can expose secret-derived build arguments."""

    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_scan_with = publish_scan_step["with"]
    publish_scan_build_args = publish_scan_with["build-args"]
    publish_scan_secret_envs = publish_scan_with["secret-envs"]

    assert publish_scan_with["push"] is False
    assert publish_scan_with["load"] is True
    assert publish_scan_with["provenance"] is False
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in publish_scan_build_args
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in publish_scan_build_args
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in publish_scan_secret_envs
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in publish_scan_secret_envs

    for step in _pushed_docker_steps_with_secret_index_args():
        step_with = step["with"]
        build_args = step_with["build-args"]
        secret_envs = step_with["secret-envs"]

        assert step_with["push"] is True
        assert step_with["provenance"] == "mode=min"
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in build_args
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in build_args
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in secret_envs
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in secret_envs


def test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes() -> None:
    build_workflow = _load_workflow(".github/workflows/build.yml")
    cd_workflow = _load_workflow(".github/workflows/cd.yml")

    local_build_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Build Docker image (local, for tests)",
    )
    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_push_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Push scanned Docker image",
    )
    pushed_steps = _pushed_docker_steps_with_secret_index_args()
    publish_sbom_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Attest Docker image SBOM",
    )
    staging_verify_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Verify staged backend image attestations",
    )
    staging_provenance_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged backend image provenance",
    )
    staging_sbom_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged backend image SBOM",
    )
    staging_caddy_verify_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Verify staged Caddy image attestations",
    )
    staging_caddy_provenance_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged Caddy image provenance",
    )
    staging_caddy_sbom_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged Caddy image SBOM",
    )
    production_verify_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Verify production image attestations",
    )
    production_provenance_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Attest production image provenance",
    )
    production_sbom_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Attest production image SBOM",
    )
    staging_upload_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Upload staging attestation verification artifact",
    )
    production_upload_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Upload production attestation verification artifact",
    )
    staging_step_names = _workflow_step_names(".github/workflows/cd.yml", "build")
    production_step_names = _workflow_step_names(".github/workflows/cd.yml", "build-production")

    assert local_build_step["with"]["load"] is True
    assert local_build_step["with"]["provenance"] is False
    assert publish_scan_step["with"]["load"] is True
    assert publish_scan_step["with"]["push"] is False
    assert publish_scan_step["with"]["provenance"] is False
    assert publish_push_step["id"] == "docker-build-push"
    assert "docker image push" in publish_push_step["run"]
    assert "digest=${digest}" in publish_push_step["run"]
    assert cd_workflow["jobs"]["build"]["permissions"]["attestations"] == "write"
    assert cd_workflow["jobs"]["build-production"]["permissions"]["attestations"] == "write"

    for step in pushed_steps:
        assert step["with"]["push"] is True
        assert step["with"]["provenance"] == "mode=min"
        assert step["with"]["sbom"] is True
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in step["with"]["build-args"]
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in step["with"]["build-args"]
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in step["with"]["secret-envs"]
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in step["with"]["secret-envs"]

    for provenance_step in (
        staging_provenance_step,
        staging_caddy_provenance_step,
        production_provenance_step,
    ):
        assert provenance_step["uses"].startswith(
            "actions/attest-build-provenance@b3e506e8c389afc651c5bacf2b8f2a1ea0557215"
        )
        assert provenance_step["with"]["push-to-registry"] is True

    assert staging_provenance_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"
    assert (
        production_provenance_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"
    )
    assert staging_caddy_provenance_step["with"]["subject-digest"] == (
        "${{ steps.build-caddy.outputs.digest }}"
    )

    for sbom_step in (staging_sbom_step, production_sbom_step, staging_caddy_sbom_step):
        assert sbom_step["uses"].startswith(
            "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26"
        )
        assert sbom_step["with"]["push-to-registry"] is True
        assert sbom_step["with"]["predicate-type"] == SBOM_PREDICATE_TYPE
        assert "sbom-path" not in sbom_step["with"]

    assert staging_sbom_step["with"]["predicate-path"] == "backend-image-sbom.spdx.json"
    assert staging_sbom_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"
    assert production_sbom_step["with"]["predicate-path"] == "docker-image-sbom.spdx.json"
    assert production_sbom_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"
    assert staging_caddy_sbom_step["with"]["predicate-path"] == "caddy-image-sbom.spdx.json"
    assert staging_caddy_sbom_step["with"]["subject-digest"] == (
        "${{ steps.build-caddy.outputs.digest }}"
    )

    assert publish_sbom_step["uses"].startswith(
        "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26"
    )
    assert publish_sbom_step["with"]["push-to-registry"] is True
    assert publish_sbom_step["with"]["predicate-type"] == SBOM_PREDICATE_TYPE
    assert publish_sbom_step["with"]["predicate-path"] == "sbom.spdx.json"
    assert "sbom-path" not in publish_sbom_step["with"]
    assert (
        publish_sbom_step["with"]["subject-digest"]
        == "${{ steps.docker-build-push.outputs.digest }}"
    )

    for verify_step in (staging_verify_step, staging_caddy_verify_step):
        verify_script = verify_step["run"]
        verify_if = verify_step["if"]
        verify_env = verify_step["env"]
        assert "always()" in verify_if
        assert "scripts/ci/check_docker_provenance_attestation.py" in verify_script
        assert verify_env["REPO_SLUG"] == "${{ github.repository }}"
        assert verify_env["SOURCE_REF"] == "${{ github.ref }}"
        assert '--repo "$REPO_SLUG"' in verify_script
        assert '--signer-workflow "$REPO_SLUG/.github/workflows/cd.yml"' in verify_script
        assert '--source-ref "$SOURCE_REF"' in verify_script

    production_verify_script = production_verify_step["run"]
    assert "always()" in production_verify_step["if"]
    assert "scripts/ci/check_docker_provenance_attestation.py" in production_verify_script
    assert '--repo "${{ github.repository }}"' in production_verify_script
    assert '--signer-workflow "${{ github.repository }}/.github/workflows/cd.yml"' in (
        production_verify_script
    )
    assert '--source-ref "${{ github.ref }}"' in production_verify_script

    assert "steps.build.outcome == 'success'" in staging_verify_step["if"]
    assert "backend-provenance-attestation-check.json" in staging_verify_step["run"]
    assert "backend-provenance-attestation-check.md" in staging_verify_step["run"]
    assert "steps.build.outcome == 'success'" in production_verify_step["if"]
    assert "docker-provenance-attestation-check.json" in production_verify_step["run"]
    assert "docker-provenance-attestation-check.md" in production_verify_step["run"]
    assert "steps.build-caddy.outcome == 'success'" in staging_caddy_verify_step["if"]
    assert (
        "steps.attest-staged-caddy-provenance.outcome == 'success'"
        in staging_caddy_verify_step["if"]
    )
    assert (
        "steps.generate-staged-caddy-sbom.outcome == 'success'" in staging_caddy_verify_step["if"]
    )
    assert "steps.attest-staged-caddy-sbom.outcome == 'success'" in staging_caddy_verify_step["if"]
    assert "caddy-provenance-attestation-check.json" in staging_caddy_verify_step["run"]
    assert "caddy-provenance-attestation-check.md" in staging_caddy_verify_step["run"]

    # Staging verify must depend on all staging attestation steps
    staging_verify_if = staging_verify_step["if"]
    assert "steps.attest-staged-provenance.outcome == 'success'" in staging_verify_if
    assert "steps.generate-staged-sbom.outcome == 'success'" in staging_verify_if
    assert "steps.attest-staged-sbom.outcome == 'success'" in staging_verify_if

    # Production verify must depend on all production attestation steps
    production_verify_if = production_verify_step["if"]
    assert "steps.attest-production-provenance.outcome == 'success'" in production_verify_if
    assert "steps.generate-production-sbom.outcome == 'success'" in production_verify_if
    assert "steps.attest-production-sbom.outcome == 'success'" in production_verify_if

    assert staging_upload_step["with"]["name"] == "docker-provenance-attestation-check-cd-staging"
    assert (
        production_upload_step["with"]["name"]
        == "docker-provenance-attestation-check-cd-production"
    )
    assert staging_upload_step["with"]["if-no-files-found"] == "error"
    assert production_upload_step["with"]["if-no-files-found"] == "warn"
    assert staging_step_names.index(
        "Build & Push backend image (staging)"
    ) < staging_step_names.index("Attest staged backend image provenance")
    assert staging_step_names.index("Attest staged backend image SBOM") < staging_step_names.index(
        "Verify staged backend image attestations"
    )
    assert staging_step_names.index(
        "Verify staged Caddy image attestations"
    ) < staging_step_names.index("Check staging deploy readiness")
    assert production_step_names.index(
        "Build & Push image (production)"
    ) < production_step_names.index("Attest production image provenance")
    assert production_step_names.index(
        "Attest production image SBOM"
    ) < production_step_names.index("Verify production image attestations")
    assert production_step_names.index("Verify production image attestations") < (
        production_step_names.index("Upload production attestation verification artifact")
    )
    assert cd_workflow["jobs"]["production-deploy-config"]["needs"] == [
        "production-gates",
        "build-production",
    ]
    expected_deploy_needs = [
        "production-gates",
        "build-production",
        "production-deploy-config",
        "release-control-plane-production-evidence",
    ]
    assert cd_workflow["jobs"]["deploy-production"]["needs"] == expected_deploy_needs
    assert cd_workflow["jobs"]["deploy-production-self-hosted"]["needs"] == expected_deploy_needs


def test_checked_in_docker_image_baseline_seed_has_expected_schema() -> None:
    baseline_payload = json.loads(
        (REPO_ROOT / "docs" / "telemetry" / "docker_image_baseline.production.json").read_text(
            encoding="utf-8"
        )
    )

    assert baseline_payload["baseline_source"] == "repo-seed-fallback"
    assert baseline_payload["image_size_bytes"] > 0
    assert baseline_payload["image_size_human"].endswith("MB")
    assert baseline_payload["baseline_reference"]["artifact_name"] == "docker-image-telemetry-build"
    assert baseline_payload["baseline_reference"]["workflow"] == "build.yml"
    assert baseline_payload["baseline_reference"]["seeded_from_run_id"] == 24771474567


def test_checked_in_docker_image_budget_policy_has_expected_schema() -> None:
    budget_payload = json.loads(
        (REPO_ROOT / "docs" / "telemetry" / "docker_image_budget.production.json").read_text(
            encoding="utf-8"
        )
    )

    assert budget_payload["budget_name"] == "production-backend-image"
    assert budget_payload["budget_version"] == 1
    assert budget_payload["budget_scope"] == "production-backend-image"
    assert budget_payload["max_image_size_bytes"] == 470000000
    assert budget_payload["max_positive_delta_bytes"] == 20000000
    assert (
        budget_payload["baseline_reference"]["baseline_file"]
        == "docs/telemetry/docker_image_baseline.production.json"
    )
    assert budget_payload["baseline_reference"]["workflow"] == "build.yml"


def test_dependabot_git_discovery_isolated_from_executable_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git = shutil.which("git")
    assert git is not None
    repo = tmp_path / "repo"
    repo.mkdir()
    fixture_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}

    def fixture_git(*argv: str) -> None:
        subprocess.run(  # nosec B603: resolved Git binary with fixed test-owned argv (remove-by: 2026-10-31, ref: PR-consol-ci-1)
            [git, "-C", str(repo), *argv],
            check=True,
            capture_output=True,
            env=fixture_env,
        )

    fixture_git("init", "--quiet")
    (repo / "requirements.txt").write_text("requests==2.32.5\n", encoding="utf-8")
    fixture_git("add", "requirements.txt")
    fixture_git("config", "core.fsmonitor", str(tmp_path / "untrusted-helper"))

    real_run = subprocess.run
    observed: list[tuple[list[str], dict[str, str]]] = []

    def record_git_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        environment = kwargs.get("env")
        assert isinstance(environment, dict)
        observed.append((argv, environment))
        return cast(subprocess.CompletedProcess[bytes], real_run(argv, **kwargs))

    monkeypatch.setattr(carriers.subprocess, "run", record_git_run)
    assert carriers.discover_dependabot_requirement_carriers(repo) == {"requirements.txt"}
    assert len(observed) == 2
    for argv, environment in observed:
        assert argv[0] == carriers.GIT_BINARY
        assert argv[1 : 1 + len(carriers.SAFE_GIT_CONFIG_ARGS)] == list(
            carriers.SAFE_GIT_CONFIG_ARGS
        )
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
        assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
        assert environment["GIT_TERMINAL_PROMPT"] == "0"


def _bandit_gate_test_repo(tmp_path: Path) -> tuple[Path, str, dict[str, str], Path]:
    """Real Make/Git; synthetic scanner bytes are explicit transport fixtures."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "Makefile").write_bytes((REPO_ROOT / "Makefile").read_bytes())
    (root / ".bandit").write_bytes((REPO_ROOT / ".bandit").read_bytes())
    helper = Path("scripts/orchestration/creative_code_patch_workspace.py")
    (root / helper).parent.mkdir(parents=True, exist_ok=True)
    (root / helper).write_bytes((REPO_ROOT / helper).read_bytes())
    git, make = shutil.which("git"), shutil.which("make")
    assert git is not None and make is not None
    fixture_env = git_env_without_parent_state()
    fixture_env["HOME"] = str(tmp_path)
    subprocess.run(
        [git, *safe_git_config_args(), "-c", "init.templateDir=", "init", "--quiet", str(root)],
        env=fixture_env,
        check=True,
    )
    tracked = [
        "src/regular.py",
        "src/with spaces.py",
        "scripts/ci/fetch_docker_source_artifacts.py",
        "-leading.py",
        "src/with\nnewline.py",
    ]
    for relative in tracked + ["untracked.py", "artifacts/private.py", "worktrees/foreign.py"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n")
    subprocess.run(
        [git, *safe_git_config_args(), "add", "--", *tracked],
        cwd=root,
        env=fixture_env,
        check=True,
    )
    control = tmp_path / "control"
    control.mkdir()
    log = tmp_path / "scanner-argv.json"
    # This test-owned startup shim intercepts exactly [approved Python, -m, bandit].
    # Native Git/config/discovery remain real; synthetic reports are not native proof.
    scanner = control / "sitecustomize.py"
    scanner.write_text(
        "import json, os, pathlib, subprocess, sys\n"
        "native_run = subprocess.run\n"
        "\n"
        "def fixture_bandit(argv, *args, **kwargs):\n"
        '    if argv[:3] != [sys.executable, "-m", "bandit"]:\n'
        "        return native_run(argv, *args, **kwargs)\n"
        "    arguments = argv[3:]\n"
        '    pathlib.Path(os.environ["SCANNER_LOG"]).write_text(json.dumps(arguments))\n'
        '    output = pathlib.Path(arguments[arguments.index("-o") + 1])\n'
        '    paths = arguments[arguments.index("--") + 1:]\n'
        "    from bandit.core.config import BanditConfig\n"
        "    from bandit.core.manager import BanditManager\n"
        "    from bandit.core.metrics import Metrics\n"
        '    manager = BanditManager(BanditConfig(".bandit"), "file")\n'
        "    manager.discover_files(paths)\n"
        "    eligible_paths = manager.files_list\n"
        "    metrics = Metrics()\n"
        "    for path in eligible_paths:\n"
        '        metrics.data[path] = dict(metrics.data["_totals"])\n'
        '        metrics.data[path]["loc"] = 1\n'
        "    metrics.aggregate()\n"
        '    report = {"errors": [], "results": [], "generated_at": "2000-01-01T00:00:00Z", "metrics": metrics.data}\n'
        '    mode = os.environ.get("REPORT_MODE", "complete")\n'
        '    if mode == "errors": report["errors"] = [{"filename": eligible_paths[0], "reason": "syntax error"}]\n'
        '    if mode == "findings": report["results"] = [{"issue_severity": "MEDIUM"}]\n'
        '    if mode == "partial": report["metrics"].pop(eligible_paths[0])\n'
        '    if mode == "extra": report["metrics"]["./untracked.py"] = {}\n'
        '    if mode in ("missing-errors", "missing-results", "missing-metrics", "missing-generated_at"): report.pop(mode.removeprefix("missing-"))\n'
        '    if mode == "wrong-metrics-type": report["metrics"] = list(report["metrics"])\n'
        '    if mode == "wrong-row-type": report["metrics"][eligible_paths[0]] = []\n'
        '    if mode == "missing-counter": report["metrics"][eligible_paths[0]].pop("loc")\n'
        '    if mode == "missing-issue-counter": report["metrics"][eligible_paths[0]].pop("SEVERITY.LOW")\n'
        '    if mode == "empty-row": report["metrics"][eligible_paths[0]] = {}\n'
        '    if mode == "float-counter": report["metrics"][eligible_paths[0]]["loc"] = 1.0\n'
        '    if mode == "bool-counter": report["metrics"][eligible_paths[0]]["loc"] = True\n'
        '    if mode == "negative-counter": report["metrics"][eligible_paths[0]]["loc"] = -1\n'
        '    if mode == "inconsistent-total": report["metrics"]["_totals"]["loc"] += 1\n'
        '    if mode == "hidden-medium":\n'
        '        report["metrics"][eligible_paths[0]]["SEVERITY.MEDIUM"] = 1\n'
        '        report["metrics"]["_totals"]["SEVERITY.MEDIUM"] = 1\n'
        '    if mode == "drift-source": pathlib.Path(eligible_paths[0]).write_text("changed = 1\\n")\n'
        '    if mode == "drift-config": pathlib.Path(".bandit").write_text(pathlib.Path(".bandit").read_text() + "\\n")\n'
        '    if mode == "drift-index":\n'
        "        import shutil\n"
        "        from scripts.orchestration.creative_code_patch_workspace import git_env_without_parent_state, safe_git_config_args\n"
        '        native_run([shutil.which("git"), *safe_git_config_args(), "add", "--", "untracked.py"], env=git_env_without_parent_state(), check=True)\n'
        '    if mode == "symlink": output.symlink_to(os.environ["SCANNER_LOG"])\n'
        '    elif mode == "duplicate": output.write_text(\'{"errors":[],"errors":[],"results":[]}\')\n'
        '    elif mode == "invalid": output.write_text("{")\n'
        '    elif mode != "absent": output.write_text(json.dumps(report))\n'
        '    return subprocess.CompletedProcess(argv, int(os.environ.get("SCANNER_EXIT", "0")))\n'
        "\n"
        "subprocess.run = fixture_bandit\n"
    )
    environment = {
        "PATH": str(control) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "SCANNER_LOG": str(log),
        "PYTHONPATH": str(control),
    }
    return root, make, environment, log


@pytest.mark.parametrize("ci", (None, "true", "false"))
@pytest.mark.parametrize("scanner_exit", (0, 1, 2))
def test_full_bandit_make_gate_uses_complete_tracked_paths_and_preserves_failures(
    tmp_path: Path, ci: str | None, scanner_exit: int
) -> None:
    """Synthetic scanner status proves propagation, never a security verdict."""
    root, make, environment, log = _bandit_gate_test_repo(tmp_path)
    environment["SCANNER_EXIT"] = str(scanner_exit)
    if ci is not None:
        environment["CI"] = ci
    result = subprocess.run(
        [make, "bandit-full", "DEV_PYTHON=" + sys.executable],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert (result.returncode == 0) is (scanner_exit == 0), result.stdout + result.stderr
    argv = json.loads(log.read_text())
    report_argument = argv[argv.index("-o") + 1]
    assert Path(report_argument).name == "bandit-report.json"
    assert Path(report_argument).parent.name.startswith(".bandit-full-")
    assert not Path(report_argument).parent.exists()
    assert argv[: argv.index("--")] == [
        "-c",
        ".bandit",
        "--severity-level",
        "medium",
        "-f",
        "json",
        "-o",
        report_argument,
    ]
    assert argv[argv.index("--") + 1 :] == [
        "./-leading.py",
        "./scripts/ci/fetch_docker_source_artifacts.py",
        "./src/regular.py",
        "./src/with\nnewline.py",
        "./src/with spaces.py",
    ]
    if scanner_exit:
        assert "✅ Bandit отчет" not in result.stdout


@pytest.mark.parametrize(
    "mode",
    (
        "absent",
        "invalid",
        "errors",
        "findings",
        "partial",
        "extra",
        "missing-errors",
        "missing-results",
        "missing-metrics",
        "symlink",
        "duplicate",
        "wrong-metrics-type",
        "wrong-row-type",
        "drift-source",
        "drift-config",
        "drift-index",
        "missing-generated_at",
        "missing-counter",
        "missing-issue-counter",
        "empty-row",
        "float-counter",
        "bool-counter",
        "negative-counter",
        "inconsistent-total",
        "hidden-medium",
    ),
)
def test_full_bandit_zero_exit_cannot_accept_missing_partial_or_erroneous_report(
    tmp_path: Path,
    mode: str,
) -> None:
    root, make, environment, log = _bandit_gate_test_repo(tmp_path)
    report = root / "bandit-report.json"
    report.write_text('{"errors": [], "results": [], "metrics": {"stale": {}}}')
    environment["REPORT_MODE"] = mode
    result = subprocess.run(
        [make, "bandit-full", "DEV_PYTHON=" + sys.executable],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert log.is_file(), result.stdout + result.stderr
    assert result.returncode != 0 and "✅ Bandit отчет" not in result.stdout
    expected_diagnostic = {
        "absent": "Bandit report is missing, unsafe",
        "invalid": "JSONDecodeError",
        "errors": "scanner errors/findings",
        "findings": "scanner errors/findings",
        "partial": "exact configured tracked inventory",
        "extra": "exact configured tracked inventory",
        "missing-errors": "scanner errors/findings",
        "missing-results": "scanner errors/findings",
        "missing-metrics": "exact configured tracked inventory",
        "symlink": "Bandit report is missing, unsafe",
        "duplicate": "duplicate JSON keys",
        "wrong-metrics-type": "exact configured tracked inventory",
        "wrong-row-type": "exact configured tracked inventory",
        "drift-source": "changed during the scan",
        "drift-config": "changed during the scan",
        "drift-index": "changed during the scan",
        "missing-generated_at": "missing its native generation metadata",
        "missing-counter": "incomplete or malformed native metrics",
        "missing-issue-counter": "incomplete or malformed native metrics",
        "empty-row": "incomplete or malformed native metrics",
        "float-counter": "incomplete or malformed native metrics",
        "bool-counter": "incomplete or malformed native metrics",
        "negative-counter": "incomplete or malformed native metrics",
        "inconsistent-total": "totals are inconsistent",
        "hidden-medium": "totals are inconsistent",
    }[mode]
    assert expected_diagnostic in result.stderr, result.stdout + result.stderr
    if mode == "absent":
        assert not report.exists()  # Old bytes cannot supply the missing new result.


def test_full_bandit_rejects_missing_tracked_file_before_scanner(tmp_path: Path) -> None:
    root, make, environment, log = _bandit_gate_test_repo(tmp_path)
    (root / "src/regular.py").unlink()
    result = subprocess.run(
        [make, "bandit-full", "DEV_PYTHON=" + sys.executable],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0 and not log.exists()
    assert "src/regular.py" in result.stderr


@pytest.mark.parametrize(
    ("raw", "git_exit"),
    (
        (b"", 0),
        (b"src/regular.py", 0),
        (b"src/regular.py\0\0", 0),
        (b"src/regular.py\0src/regular.py\0", 0),
        (b"src/regular.py\0", 2),
    ),
)
def test_full_bandit_rejects_invalid_native_inventory_before_scanner(
    tmp_path: Path,
    raw: bytes,
    git_exit: int,
) -> None:
    root, make, environment, log = _bandit_gate_test_repo(tmp_path)
    git = tmp_path / "control/git"
    actual_git = shutil.which("git")
    assert actual_git is not None
    git.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "if sys.argv[-4:] == ['ls-files', '-z', '--', '*.py']:\n"
        f"    sys.stdout.buffer.write({raw!r})\n"
        f"    raise SystemExit({git_exit})\n"
        "else:\n"
        f"    os.execv({actual_git!r}, [{actual_git!r}, *sys.argv[1:]])\n"
    )
    git.chmod(0o755)
    result = subprocess.run(
        [make, "bandit-full", "DEV_PYTHON=" + sys.executable],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0 and not log.exists()
    if git_exit:
        assert "CalledProcessError" in result.stderr, result.stdout + result.stderr
    else:
        assert "Tracked Python security inventory" in result.stderr


def test_full_bandit_quotes_developer_interpreter_path(tmp_path: Path) -> None:
    root, make, environment, log = _bandit_gate_test_repo(tmp_path)
    wrapper = tmp_path / "python directory/interpreter"
    wrapper.parent.mkdir()
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    result = subprocess.run(
        [make, "bandit-full", "DEV_PYTHON=" + str(wrapper)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0 and log.is_file(), result.stdout + result.stderr


@pytest.mark.parametrize(
    "bad", ("import pickle\npickle.loads(b'never-executed fixture')\n", "def invalid(:\n")
)
def test_full_bandit_native_report_rejects_findings_and_scanner_errors(
    tmp_path: Path,
    bad: str,
) -> None:
    """Actual Bandit scans fixtures but never executes their Python code."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "Makefile").write_bytes((REPO_ROOT / "Makefile").read_bytes())
    (root / ".bandit").write_bytes((REPO_ROOT / ".bandit").read_bytes())
    helper = Path("scripts/orchestration/creative_code_patch_workspace.py")
    (root / helper).parent.mkdir(parents=True, exist_ok=True)
    (root / helper).write_bytes((REPO_ROOT / helper).read_bytes())
    git, make = shutil.which("git"), shutil.which("make")
    assert git is not None and make is not None
    fixture_env = git_env_without_parent_state()
    fixture_env["HOME"] = str(tmp_path)
    subprocess.run(
        [git, *safe_git_config_args(), "-c", "init.templateDir=", "init", "--quiet", str(root)],
        env=fixture_env,
        check=True,
    )
    source = root / "fetch_docker_source_artifacts.py"
    source.write_text(bad)
    excluded = root / "tests/excluded.py"
    excluded.parent.mkdir()
    excluded.write_text(bad)
    (root / "artifacts").mkdir()
    (root / "artifacts/untracked.py").write_text(bad)
    subprocess.run(
        [git, *safe_git_config_args(), "add", "--", source.name, "tests/excluded.py"],
        cwd=root,
        env=fixture_env,
        check=True,
    )
    environment = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "CI": "true",
    }
    argv = [make, "bandit-full", "DEV_PYTHON=" + sys.executable]
    rejected = subprocess.run(
        argv,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert rejected.returncode != 0, rejected.stdout + rejected.stderr
    report = json.loads((root / "bandit-report.json").read_text())
    if bad.startswith("import"):
        assert report["errors"] == [] and report["results"]
        assert all(Path(row["filename"]).name == source.name for row in report["results"])
        assert any(
            row["test_id"] == "B301" and row["issue_severity"] == "MEDIUM"
            for row in report["results"]
        )
    else:
        assert report["errors"] and report["results"] == []
        assert "scanner errors" in rejected.stderr
    source.write_text("pass\n")
    accepted = subprocess.run(
        argv,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    report = json.loads((root / "bandit-report.json").read_text())
    assert report["errors"] == report["results"] == []
    assert (root / "artifacts/untracked.py").read_text() == bad


def _comparison_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, private: bool = True
) -> tuple[Path, Path, Path, dict[str, str], list[str]]:
    manifest = tmp_path / "requirements.txt"
    content = b"numpy==2.4.6\npillow==13.0.0\n"
    if private:
        content += b"fastembed==0.8.0+pulseplate.1\n"
    manifest.write_bytes(content)
    output = tmp_path / "pip-audit-requirements.json"
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    calls: list[str] = []

    def acquire(_work: Path) -> None:
        calls.append("acquire")

    def prove(_work: Path) -> dict[str, str]:
        calls.append("prove")
        return {
            "source_wheel_sha256": compat_audit.SOURCE_SHA256,
            "private_wheel_sha256": compat_audit.PRIVATE_SHA256,
            "recipe_sha256": compat_audit.RECIPE_SHA256,
        }

    monkeypatch.setattr(compat_audit, "_acquire_pair", acquire)
    monkeypatch.setattr(compat_audit, "_prove_pair", prove)
    compat_audit.prepare(manifest, output, work)
    _, _, query, _ = compat_audit._projection(content)
    return manifest, output, work, query, calls


def _write_audit_report(output: Path, coordinates: dict[str, str]) -> bytes:
    raw = json.dumps(
        {
            "dependencies": [
                {"name": name, "version": version, "vulns": []}
                for name, version in coordinates.items()
            ],
            "fixes": [],
        }
    ).encode()
    output.write_bytes(raw)
    output.with_suffix(".stderr.log").write_bytes(b"raw scanner diagnostic\n")
    return raw


def test_private_comparison_changes_only_fastembed_query_and_rechecks_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, output, work, query, calls = _comparison_fixture(tmp_path, monkeypatch)
    original = manifest.read_bytes()
    raw = _write_audit_report(output, query)
    assert query == {"numpy": "2.4.6", "pillow": "13.0.0", "fastembed": "0.8.0"}
    assert compat_audit.validate(
        manifest,
        output,
        work,
        scanner_exit=0,
        scanner_version="pip-audit 2.10.1",
        auditor="/synthetic/pip-audit",
    )
    evidence = json.loads(output.with_suffix(".evidence.json").read_text())
    assert (
        evidence["upstream_comparison"] is True
        and evidence["private_version_directly_audited"] is False
    )
    assert evidence["original_coordinates"]["fastembed"] == "0.8.0+pulseplate.1"
    assert evidence["query_coordinates"] == query
    assert calls == ["acquire", "prove", "prove"]
    assert manifest.read_bytes() == original and output.read_bytes() == raw
    assert output.with_suffix(".stderr.log").read_bytes() == b"raw scanner diagnostic\n"


@pytest.mark.parametrize(
    "content",
    [
        b"fastembed==0.8.0+pulseplate.2\n",
        b"other==0.8.0+pulseplate.1\n",
        b"fast-embed==0.8.0+pulseplate.1\n",
        b"FastEmbed==0.8.0+pulseplate.1\n",
        b"fastembed == 0.8.0+pulseplate.1\n",
        b"fastembed[extra]==0.8.0+pulseplate.1\n",
        b"fastembed==0.8.0+pulseplate.1\nfastembed==0.8.0+pulseplate.1\n",
        b"fastembed>=0.8.0\n",
        b"-r other.txt\n",
        b'fastembed==0.8.0; python_version>="3.10"\n',
    ],
)
def test_unsupported_comparison_input_fails_before_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_bytes(content)
    work = tmp_path / "work"
    work.mkdir(mode=0o700)

    def forbidden(_: Path) -> None:
        pytest.fail("unsupported carrier reached acquisition")

    monkeypatch.setattr(compat_audit, "_acquire_pair", forbidden)
    with pytest.raises(compat_audit.AuditFailure):
        compat_audit.prepare(manifest, tmp_path / "out.json", work)
    assert manifest.read_bytes() == content


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "duplicate",
        "skip",
        "pillow",
        "private-claim",
        "empty-object",
        "nonfinite",
        "malformed-finding",
    ],
)
def test_strict_comparison_rejects_independent_report_defects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    manifest, output, work, query, _ = _comparison_fixture(tmp_path, monkeypatch)
    raw = _write_audit_report(output, query)
    assert compat_audit._report_inventory(raw, query) == 0
    report = json.loads(raw)
    if mutation == "missing":
        report["dependencies"].pop()
    elif mutation == "extra":
        report["dependencies"].append({"name": "unlisted", "version": "1.0", "vulns": []})
    elif mutation == "duplicate":
        report["dependencies"].append(report["dependencies"][0])
    elif mutation == "skip":
        report["dependencies"][0] = {"name": "numpy", "skip_reason": "unknown"}
    elif mutation == "pillow":
        report["dependencies"][1]["version"] = "12.3.0"
    elif mutation == "private-claim":
        report["dependencies"][-1]["version"] = "0.8.0+pulseplate.1"
    elif mutation == "empty-object":
        report = {}
    elif mutation == "nonfinite":
        report["dependencies"][0]["vulns"] = float("nan")
    else:
        report["dependencies"][0]["vulns"] = [{"id": "GHSA-fixture", "fix_versions": "1.0"}]
    mutated = json.dumps(report).encode()
    output.write_bytes(mutated)
    assert not compat_audit.validate(
        manifest,
        output,
        work,
        scanner_exit=0,
        scanner_version="pip-audit 2.10.1",
        auditor="/synthetic/pip-audit",
    )
    evidence = json.loads(output.with_suffix(".evidence.json").read_text())
    assert evidence["inventory_validation_error"] is not None
    assert output.read_bytes() == mutated


@pytest.mark.parametrize("failure", ["nonzero", "upstream-finding", "empty-output"])
def test_upstream_findings_or_nonterminal_reports_are_never_suppressed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    manifest, output, work, query, _ = _comparison_fixture(tmp_path, monkeypatch)
    raw = _write_audit_report(output, query)
    if failure == "upstream-finding":
        report = json.loads(raw)
        report["dependencies"][-1]["vulns"] = [
            {
                "id": "GHSA-fixture",
                "fix_versions": [],
                "aliases": [],
                "description": "preserved upstream finding",
            }
        ]
        raw = json.dumps(report).encode()
    elif failure == "empty-output":
        raw = b""
    output.write_bytes(raw)
    assert not compat_audit.validate(
        manifest,
        output,
        work,
        scanner_exit=7 if failure == "nonzero" else 0,
        scanner_version="pip-audit 2.10.1",
        auditor="/synthetic/pip-audit",
    )
    assert output.read_bytes() == raw
    evidence = json.loads(output.with_suffix(".evidence.json").read_text())
    if failure == "upstream-finding":
        assert evidence["findings"] == 1


@pytest.mark.parametrize("changed", ["manifest", "comparand", "proof"])
def test_validation_rebinds_preparation_bytes_and_derivation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    manifest, output, work, query, _ = _comparison_fixture(tmp_path, monkeypatch)
    raw = _write_audit_report(output, query)
    if changed == "manifest":
        manifest.write_bytes(manifest.read_bytes() + b"# drift\n")
        expected = "original_manifest_changed"
    elif changed == "comparand":
        (work / "comparand.txt").write_text("pillow==12.3.0\n")
        expected = "comparand_bytes_changed"
    else:

        def rejected(_: Path) -> dict[str, str]:
            raise compat_audit.AuditFailure("compat_wheel_identity_changed")

        monkeypatch.setattr(compat_audit, "_prove_pair", rejected)
        expected = "compat_wheel_identity_changed"
    with pytest.raises(compat_audit.AuditFailure, match=expected):
        compat_audit.validate(
            manifest,
            output,
            work,
            scanner_exit=0,
            scanner_version="pip-audit 2.10.1",
            auditor="/synthetic/pip-audit",
        )
    assert output.read_bytes() == raw and not output.with_suffix(".evidence.json").exists()


def test_empty_registered_lock_needs_complete_empty_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "requirements-evals.txt"
    manifest.write_text("# empty registered lock\n")
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    output = tmp_path / "audit.json"
    compat_audit.prepare(manifest, output, work)
    _write_audit_report(output, {})
    assert compat_audit.validate(
        manifest,
        output,
        work,
        scanner_exit=0,
        scanner_version="pip-audit 2.10.1",
        auditor="/synthetic/pip-audit",
    )


def test_stale_output_or_false_claim_cannot_be_preparation_authority(tmp_path: Path) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("example==1.0.0\n")
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    output = tmp_path / "audit.json"
    stale = b'{"private_version_directly_audited":true,"passed":true}'
    output.with_suffix(".evidence.json").write_bytes(stale)
    with pytest.raises(compat_audit.AuditFailure, match="stale_audit_output_exists"):
        compat_audit.prepare(manifest, output, work)
    assert output.with_suffix(".evidence.json").read_bytes() == stale


@pytest.mark.parametrize(
    "mutation", [None, "foreign-host", "wrong-hash", "wrong-bytes", "http-failure"]
)
def test_comparison_acquisition_uses_only_exact_private_proxy_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str | None
) -> None:
    import hashlib

    source = b"s" * 116572
    private = b"p" * 116726
    monkeypatch.setattr(compat_audit, "SOURCE_SHA256", hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(compat_audit, "PRIVATE_SHA256", hashlib.sha256(private).hexdigest())
    index = "https://packages.pulseplate.app/root/pulseplate/+simple/"
    monkeypatch.setattr(compat_audit, "resolve_private_proxy_settings", lambda **_: (index, None))
    monkeypatch.setattr(
        compat_audit, "_admit_private_proxy_netrc_auth", lambda **_: "Basic synthetic"
    )
    source_url = (
        "https://packages.pulseplate.app/root/pypi/+f/source/"
        + compat_audit.builder.SOURCE_FILENAME
    )
    private_url = (
        "https://packages.pulseplate.app/root/pulseplate/+f/private/"
        + compat_audit.builder.OUTPUT_FILENAME
    )
    html = f'<a href="{source_url}#sha256={compat_audit.SOURCE_SHA256}">source</a><a href="{private_url}#sha256={compat_audit.PRIVATE_SHA256}">private</a>'
    if mutation == "foreign-host":
        html = html.replace(
            "https://packages.pulseplate.app/root/pulseplate/+f/private/",
            "https://foreign.invalid/",
        )
    elif mutation == "wrong-hash":
        html = html.replace(compat_audit.PRIVATE_SHA256, "0" * 64)
    calls: list[str] = []

    def fetch(url: str, **kwargs: object) -> tuple[int, bytes]:
        calls.append(url)
        assert url.startswith("https://packages.pulseplate.app/")
        assert kwargs["authorization_header"] == "Basic synthetic"
        if url.endswith("/fastembed/"):
            return (503 if mutation == "http-failure" else 200), html.encode()
        if url == source_url:
            return 200, source
        assert url == private_url
        return 200, (b"!" + private[1:] if mutation == "wrong-bytes" else private)

    monkeypatch.setattr(compat_audit, "fetch_project_page", fetch)
    if mutation is None:
        compat_audit._acquire_pair(tmp_path)
        assert (tmp_path / compat_audit.builder.SOURCE_FILENAME).read_bytes() == source
        assert (tmp_path / compat_audit.builder.OUTPUT_FILENAME).read_bytes() == private
        assert len(calls) == 3
    else:
        with pytest.raises((compat_audit.AuditFailure, ValueError)):
            compat_audit._acquire_pair(tmp_path)
        assert not (tmp_path / compat_audit.builder.OUTPUT_FILENAME).exists()


def test_missing_scanner_report_is_not_an_empty_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, output, work, _, _ = _comparison_fixture(tmp_path, monkeypatch)
    output.unlink()
    with pytest.raises(FileNotFoundError):
        compat_audit.validate(
            manifest,
            output,
            work,
            scanner_exit=0,
            scanner_version="pip-audit 2.10.1",
            auditor="/synthetic/pip-audit",
        )
    assert not output.with_suffix(".evidence.json").exists()


def test_stale_valid_scanner_report_stays_unchanged(tmp_path: Path) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("example==1.0.0\n")
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    output = tmp_path / "audit.json"
    raw = _write_audit_report(output, {"example": "1.0.0"})
    with pytest.raises(compat_audit.AuditFailure, match="stale_audit_output_exists"):
        compat_audit.prepare(manifest, output, work)
    assert output.read_bytes() == raw


def test_comparison_diagnostic_does_not_echo_untrusted_requirement_credentials(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("example @ https://synthetic-secret@invalid.example/package.whl\n")
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    assert (
        compat_audit.main(
            [
                "prepare",
                "--manifest",
                str(manifest),
                "--output",
                str(tmp_path / "audit.json"),
                "--work-dir",
                str(work),
            ]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert "invalid_exact_requirement_inventory" in stderr
    assert "synthetic-secret" not in stderr


@pytest.fixture
def black_hook_repo(tmp_path: Path) -> Path:
    """A later patch satisfies the unchanged compatible source lower bound."""
    config = {
        "repos": [
            {"repo": "https://github.com/psf/black", "rev": "26.10.2", "hooks": [{"id": "black"}]}
        ]
    }
    (tmp_path / ".pre-commit-config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    for filename in ("requirements-dev.txt", "requirements-lock.txt"):
        (tmp_path / filename).write_text("black==26.10.2\n", encoding="utf-8")
    for filename in ("constraints.txt", "requirements-all.txt"):
        (tmp_path / filename).write_text("black>=26.10.1\n", encoding="utf-8")
    (tmp_path / "requirements-dev.in").write_text("black~=26.10.1\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("revision", ("26.10.2", "v26.10.2"))
def test_black_hook_parity_allows_later_patch_with_unchanged_source_floor(
    black_hook_repo: Path, revision: str
) -> None:
    path = black_hook_repo / ".pre-commit-config.yaml"
    config = yaml.safe_load(path.read_text())
    config["repos"][0]["rev"] = revision
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    _assert_black_hook_lock_parity(black_hook_repo)


@pytest.mark.parametrize(
    "mutation",
    (
        "hook-mismatch",
        "aggregate-mismatch",
        "source-excludes",
        "duplicate-hook",
        "duplicate-repository",
        "missing-source",
        "duplicate-source",
        "missing-lock",
        "duplicate-lock",
        "marked-lock",
        "invalid-revision",
    ),
)
def test_black_hook_parity_rejects_mismatched_or_ambiguous_owners(
    black_hook_repo: Path, mutation: str
) -> None:
    path = black_hook_repo / ".pre-commit-config.yaml"
    config = yaml.safe_load(path.read_text())
    if mutation == "hook-mismatch":
        config["repos"][0]["rev"] = "26.10.3"
    elif mutation == "aggregate-mismatch":
        (black_hook_repo / "requirements-lock.txt").write_text("black==26.10.3\n")
    elif mutation == "source-excludes":
        (black_hook_repo / "requirements-dev.in").write_text("black~=26.11.0\n")
    elif mutation == "duplicate-hook":
        config["repos"][0]["hooks"].append({"id": "black"})
    elif mutation == "duplicate-repository":
        config["repos"].append(config["repos"][0])
    elif mutation == "missing-source":
        (black_hook_repo / "constraints.txt").write_text("# no owner\n")
    elif mutation == "duplicate-source":
        (black_hook_repo / "requirements-all.txt").write_text("black>=26.10.1\nBlack>=26.10.1\n")
    elif mutation == "missing-lock":
        (black_hook_repo / "requirements-dev.txt").write_text("# no owner\n")
    elif mutation == "duplicate-lock":
        (black_hook_repo / "requirements-dev.txt").write_text("black==26.10.2\nBlack==26.10.2\n")
    elif mutation == "marked-lock":
        (black_hook_repo / "requirements-dev.txt").write_text(
            'black==26.10.2; python_version >= "3.13"\n'
        )
    else:
        config["repos"][0]["rev"] = "not-a-version"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises((AssertionError, InvalidVersion)):
        _assert_black_hook_lock_parity(black_hook_repo)
