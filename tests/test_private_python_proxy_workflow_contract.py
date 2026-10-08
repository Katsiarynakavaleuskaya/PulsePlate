from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
import os
import shutil
import shlex
import subprocess
import sys

import pytest
import yaml

from scripts.ci import install_locked_python_requirements as locked_installer

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
HEALTH_JOB = "private_python_proxy_health"


def load_ci_workflow() -> dict[str, Any]:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def as_needs_set(job: dict[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    assert isinstance(needs, list), "job needs must be a string or list"
    return {str(need) for need in needs}


def job_uses_python_setup(job: dict[str, Any]) -> bool:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return any(
        isinstance(step, dict) and step.get("uses") == "./.github/actions/python-setup"
        for step in steps
    )


def test_shared_setup_builds_only_the_exact_isolated_client_sdk() -> None:
    action = yaml.safe_load((REPO_ROOT / ".github/actions/python-setup/action.yml").read_text())
    steps = action["runs"]["steps"]
    sdk = next(step for step in steps if step.get("name") == "Build exact Psycopg C client SDK")
    assert sdk["if"] == "${{ inputs.skip-base-install != 'true' }}"
    script = sdk["run"]
    assert "--platform linux/amd64 --target psycopg-sdk" in script
    assert "PSYCOPG_SDK_PYTHON_IMAGE=$sdk_image" in script
    for digest in (
        "9fd63080" "3ec34469" "20ed6b64" "d20150bd" "724c1751" "e7181729" "3a423052" "2c1a384a",
        "a594f7e9" "df8a4c43" "1265125b" "5f5d90cd" "1b81c8a8" "797fefee" "69d5b354" "4be11111",
        "7a6b87c0" "2e1f4d6b" "b572e379" "235cbbdd" "7892add0" "572442c9" "b0b860a3" "f5aa9857",
    ):
        assert "python@sha256:" + digest in script
    assert "uname -s" in script and "uname -m" in script
    assert 'test ! -e "$sdk_root"' in script
    assert "--secret id=pp_py_index,env=PULSEPLATE_PYTHON_INDEX_URL" in script
    assert "id=pp_netrc,src=$HOME/.netrc" in script
    assert "PULSEPLATE_PSYCOPG_C_SDK=$sdk_root/psycopg-sdk" in script
    assert '>> "$GITHUB_ENV"' in script
    names = [step.get("name") for step in steps]
    assert names.index("Configure private Python index authentication") < names.index(sdk["name"])
    assert names.index(sdk["name"]) < names.index("Install base dependencies")
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    builder = dockerfile.split("FROM native-builder AS psycopg-wheel-builder", 1)[1].split(
        "FROM scratch AS psycopg-sdk", 1
    )[0]
    assert "RUN --network=none /usr/bin/env -i" in builder
    assert "--build-psycopg-c" in builder
    assert "--mount=type=secret" not in builder
    assert "DEVPI_CI_PASSWORD" not in builder and "GH_TOKEN" not in builder


def test_shared_setup_observes_real_consumers_after_locked_install() -> None:
    """Every selected ABI observes loaded components after the actual SDK/install."""
    action = yaml.safe_load((REPO_ROOT / ".github/actions/python-setup/action.yml").read_text())
    steps = action["runs"]["steps"]
    names = [step.get("name") for step in steps]
    observe = next(
        step for step in steps if step.get("name") == "Observe installed native Python consumers"
    )
    assert observe["if"] == "${{ inputs.skip-base-install != 'true' }}"
    assert names.index("Install base dependencies") < names.index(observe["name"])
    script = observe["run"]
    assert "ssl.OPENSSL_VERSION_INFO" in script
    assert "psycopg.pq.__impl__" in script and "pq.version()" in script
    assert "backend.openssl_version_number()" in script
    assert "backend.openssl_version_text()" in script
    assert 'if importlib.util.find_spec("psycopg") is not None:' in script
    assert 'if importlib.util.find_spec("cryptography") is not None:' in script
    assert "load_manifest" in script and 'selected["openssl"]' in script
    assert 'selected["postgresql"]' in script
    assert 'sdk_root / "usr/local/lib" / name' in script
    assert "ssl.create_default_context().get_ca_certs()" in script
    assert 'Path("/proc/self/maps").read_text()' in script
    assert "hashlib.sha256(path.read_bytes()).hexdigest()" in script
    assert "len(paths) != 1" in script
    assert "raise SystemExit" in script
    assert "--mount" not in script and "subprocess" not in script


@pytest.mark.parametrize(
    "version_info,expected_exit",
    (
        ((3, 5, 0, 9, 0), 0),
        ((3, 5, 0, 8, 0), 1),
        ((3, 6, 0, 9, 0), 1),
        ((4, 0, 0, 9, 0), 1),
        ((3, 5, 9, 0, 0), 1),
        ((3, 5, 0, 9, 15), 1),
    ),
)
def test_shared_setup_openssl_guard_binds_source_patch_and_release_status(
    tmp_path: Path, version_info: tuple[int, ...], expected_exit: int
) -> None:
    """The real observer admits a release-shaped patch tuple and rejects mismatches."""
    action = yaml.safe_load((REPO_ROOT / ".github/actions/python-setup/action.yml").read_text())
    observe = next(
        step
        for step in action["runs"]["steps"]
        if step.get("name") == "Observe installed native Python consumers"
    )
    source = observe["run"].split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(name, ast.Name) and name.id == "expected_ssl"
                for target in node.targets
                for name in ast.walk(target)
            )
        )
        or (
            isinstance(node, ast.Assign)
            and any(
                isinstance(name, ast.Name) and name.id == "ssl_patch"
                for target in node.targets
                for name in ast.walk(target)
            )
        )
        or (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and node.value.args[0].value == "Loaded shared OpenSSL"
        )
        or (
            isinstance(node, ast.If)
            and "Python did not load the source-selected shared OpenSSL" in ast.unparse(node)
        )
    ]
    assert len(statements) == 4
    assert isinstance(statements[-2], ast.Expr) and isinstance(statements[-1], ast.If)
    program = (
        "import types\nselected = {'openssl': '3.5.9'}\n"
        f"ssl = types.SimpleNamespace(OPENSSL_VERSION_INFO={version_info!r}, "
        "OPENSSL_VERSION='synthetic OpenSSL observation', OPENSSL_VERSION_NUMBER=0x30500090)\n"
        + "\n".join(ast.unparse(node) for node in statements)
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert repr(version_info) in result.stdout
    assert "synthetic OpenSSL observation" in result.stdout and "0x30500090" in result.stdout
    if expected_exit:
        assert "Python did not load the source-selected shared OpenSSL" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize("include_sdk_cli", (True, False))
def test_native_checkpoint_selects_the_matching_sdk_cli_before_child_env_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, include_sdk_cli: bool
) -> None:
    """Exercise the actual resolver with SDK/distro sentinels and a negative path control."""
    from tests.test_notify_premium_alias_checkpoint_failure import _native

    workflow = load_ci_workflow()
    steps = workflow["jobs"]["lint"]["steps"]
    setup_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("uses") == "./.github/actions/python-setup"
    )
    native_index = next(
        index for index, step in enumerate(steps) if step.get("id") == "checkpoint-native"
    )
    assert setup_index < native_index
    script = steps[native_index]["run"]
    invocation = next(
        line.strip().removesuffix("\\").strip()
        for line in script.splitlines()
        if line.strip().startswith("sudo /usr/bin/env -i ")
    )
    tokens = shlex.split(invocation)
    assert tokens == [
        "sudo",
        "/usr/bin/env",
        "-i",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "LANG=C",
        "HOME=/tmp",
        "PYTHONDONTWRITEBYTECODE=1",
    ]
    assert (
        '"$native_python" -m tests.test_notify_premium_alias_checkpoint_failure --native' in script
    )
    action = yaml.safe_load((REPO_ROOT / ".github/actions/python-setup/action.yml").read_text())
    sdk = next(
        step
        for step in action["runs"]["steps"]
        if step.get("name") == "Build exact Psycopg C client SDK"
    )
    assert 'sudo cp -a "$sdk_root/usr/local/lib/." /usr/local/lib/' in sdk["run"]
    assert 'sudo cp -a "$sdk_root/usr/local/bin/." /usr/local/bin/' in sdk["run"]

    directories = {
        "/usr/local/bin": tmp_path / "sdk-bin",
        "/usr/bin": tmp_path / "distro-bin",
        "/bin": tmp_path / "base-bin",
    }
    for directory in directories.values():
        directory.mkdir()
    for identity, result in (
        ("/usr/local/bin", "synthetic-sdk-openssl"),
        ("/usr/bin", "synthetic-distro-openssl"),
    ):
        executable = directories[identity] / "openssl"
        executable.write_text("#!/bin/sh\nprintf '%s\\n' '" + result + "'\n")
        executable.chmod(0o755)
    invocation_path = tokens[3].removeprefix("PATH=")
    fixture_path = os.pathsep.join(
        str(directories[identity])
        for identity in invocation_path.split(":")
        if include_sdk_cli or identity != "/usr/local/bin"
    )
    monkeypatch.setenv("PATH", fixture_path)
    result = _native(["openssl", "version"], cwd=tmp_path)
    expected = "synthetic-sdk-openssl" if include_sdk_cli else "synthetic-distro-openssl"
    assert result.returncode == 0 and result.stdout == expected + "\n"
    assert result.stderr == ""


def test_private_proxy_health_job_is_stdlib_fail_fast_gate() -> None:
    workflow = load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[HEALTH_JOB]
    assert isinstance(job, dict)

    assert job["name"] == "Private Python proxy health"
    assert job["needs"] == ["changes"]
    assert job["timeout-minutes"] <= 3
    assert job.get("continue-on-error") is None
    assert job.get("permissions") == {"contents": "read"}

    steps = job["steps"]
    assert isinstance(steps, list)
    step_uses = [step.get("uses") for step in steps if isinstance(step, dict)]
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in step_uses
    assert "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405" in step_uses
    assert "./.github/actions/python-setup" not in step_uses
    checkout_step = next(
        step
        for step in steps
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout_step.get("with", {}).get("persist-credentials") is False

    run_blocks = "\n".join(str(step.get("run", "")) for step in steps if isinstance(step, dict))
    assert "scripts/ci/check_private_python_proxy_health.py" in run_blocks
    assert "pip install" not in run_blocks
    assert "continue-on-error" not in run_blocks
    assert "--requirements-file requirements-test.txt" in run_blocks
    assert "--requirements-file requirements-dev.txt" in run_blocks
    assert "--python-version 3.11" in run_blocks
    assert "--python-version 3.12" in run_blocks
    assert "--python-version 3.13" in run_blocks
    assert "--project pytest-xdist" in run_blocks
    assert "--project hypothesis" in run_blocks
    assert "--project mypy" in run_blocks
    assert "--project ruff" in run_blocks
    assert "--project librt" in run_blocks
    assert "--project ast-serialize" in run_blocks
    assert "--project pgvector" in run_blocks
    assert "--project pydantic-core" not in run_blocks

    step_names = [step.get("name") for step in steps if isinstance(step, dict)]
    assert step_names.index("Check private Python proxy health") < step_names.index(
        "Emergency wheel mirror parity"
    )
    assert step_names.index("Emergency wheel mirror parity") < step_names.index(
        "Cleanup protected main package proxy authentication"
    )
    parity_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Emergency wheel mirror parity"
    )
    parity_run = str(parity_step.get("run", ""))
    assert "scripts/ci/check_emergency_wheel_mirror_parity.py" in parity_run
    assert "--manifest scripts/ci/emergency_python_wheels.json" in parity_run
    assert "--python-version 3.11" in parity_run
    assert "--python-version 3.12" in parity_run
    assert "--python-version 3.13" in parity_run
    assert "--format text" in parity_run
    assert parity_step.get("continue-on-error") is None

    cleanup_step = next(
        step
        for step in steps
        if (
            isinstance(step, dict)
            and step.get("name") == "Cleanup protected main package proxy authentication"
        )
    )
    assert (
        cleanup_step.get("if")
        == "always() && github.event_name != 'pull_request' && github.ref == 'refs/heads/main'"
    )
    cleanup_run = str(cleanup_step.get("run", ""))
    assert "pulseplate-private-proxy-health-netrc-created" in cleanup_run
    assert '[[ -n "${RUNNER_TEMP:-}" && -f "$marker" ]]' in cleanup_run
    assert 'rm -f "$HOME/.netrc" "$marker"' in cleanup_run
    assert cleanup_step.get("continue-on-error") is None


def test_private_proxy_health_uses_vars_for_pull_request_context() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]

    assert (
        "PULSEPLATE_PR_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}" in health_section
    )
    assert (
        "PULSEPLATE_PR_PYTHON_TRUSTED_HOST: ${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
        in health_section
    )
    pr_resolver = health_section.split("- name: Resolve PR diagnostic package proxy", 1)[1].split(
        "- name: Resolve branch diagnostic package proxy",
        1,
    )[0]
    assert "secrets." not in pr_resolver
    assert "pull_request_target" not in workflow_text


def test_private_proxy_health_uses_vars_for_non_main_branch_pushes() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]
    branch_resolver = health_section.split(
        "- name: Resolve branch diagnostic package proxy",
        1,
    )[
        1
    ].split("- name: Resolve protected main package proxy", 1,)[0]

    assert (
        "if: github.event_name != 'pull_request' && github.ref != 'refs/heads/main'"
        in branch_resolver
    )
    assert (
        "PULSEPLATE_BRANCH_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in branch_resolver
    )
    assert "secrets." not in branch_resolver
    assert "DEVPI_CI_USER:" not in branch_resolver
    assert "DEVPI_CI_PASSWORD:" not in branch_resolver


def test_private_proxy_health_main_auth_is_netrc_only() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]
    protected_resolver = health_section.split(
        "- name: Resolve protected main package proxy",
        1,
    )[
        1
    ].split("- name: Configure protected main package proxy authentication", 1,)[0]
    protected_auth = health_section.split(
        "- name: Configure protected main package proxy authentication",
        1,
    )[1].split("- name: Check private Python proxy health", 1,)[0]

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
    assert "://$DEVPI_CI_USER" not in protected_auth
    assert "://$DEVPI_CI_PASSWORD" not in protected_auth
    assert "$HOME/.netrc" in protected_auth
    assert "pulseplate-private-proxy-health-netrc-created" in protected_auth
    assert 'touch "$marker"' in protected_auth
    assert protected_auth.index('touch "$marker"') < protected_auth.index('> "$HOME/.netrc"')
    assert "[Rr][Oo][Oo][Tt]" in protected_auth
    assert "Root devpi credentials are forbidden" in protected_auth


def test_test_main_uses_same_protected_proxy_source_as_health_gate() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    test_main_section = workflow_text.split("  test-main:", 1)[1].split(
        "\n  diff-coverage:",
        1,
    )[0]
    protected_resolver = test_main_section.split(
        "- name: Resolve protected package proxy",
        1,
    )[
        1
    ].split("- name: Setup Python environment", 1)[0]

    assert (
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in protected_resolver
    )
    assert (
        "PULSEPLATE_PROTECTED_PYTHON_TRUSTED_HOST: ${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
        in protected_resolver
    )
    assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in protected_resolver
    assert "secrets.PULSEPLATE_PYTHON_TRUSTED_HOST" not in protected_resolver
    assert (
        "Set PULSEPLATE_PYTHON_INDEX_URL repository variable for protected test-main runs."
        in protected_resolver
    )


def test_python_setup_jobs_depend_on_private_proxy_health_gate() -> None:
    workflow = load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    python_setup_jobs = {
        job_name
        for job_name, job in jobs.items()
        if isinstance(job, dict) and job_uses_python_setup(job)
    }

    assert python_setup_jobs == {
        "lint",
        "security",
        "openapi-sync",
        "test-pr",
        "pgvector_compat",
        "test-feature",
        "test-main",
        "diff-coverage",
    }
    for job_name in python_setup_jobs:
        job = jobs[job_name]
        assert isinstance(job, dict)
        assert HEALTH_JOB in as_needs_set(job), f"{job_name} must need {HEALTH_JOB}"


@pytest.mark.parametrize(
    "workflow_name,job_name,profile,consumer_name",
    (
        ("rag-release-gates.yml", "rag-release-gates-smoke", "ci-lite", "Run cheap smoke lane"),
        (
            "rag-release-gates.yml",
            "rag-release-gates-weekly",
            "ci-lite",
            "Run strict weekly/manual lane",
        ),
        (
            "ci.yml",
            "pgvector_compat",
            "ci-test",
            "Prove pgvector binding, extension, and RLS compatibility",
        ),
    ),
)
def test_native_profile_callers_use_the_existing_sdk_and_exact_profile(
    workflow_name: str, job_name: str, profile: str, consumer_name: str
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows" / workflow_name).read_text())
    job = workflow["jobs"][job_name]
    steps = job["steps"]
    setup_indexes = [
        index
        for index, step in enumerate(steps)
        if step.get("uses") == "./.github/actions/python-setup"
    ]
    assert len(setup_indexes) == 1
    setup_index = setup_indexes[0]
    setup = steps[setup_index]
    inputs = setup["with"]
    assert inputs["python-version"] == "3.13.14"
    assert inputs["requirements-profile"] == profile
    assert inputs["install-mode"] == "direct-proxy"
    assert inputs.get("skip-base-install", "false") == "false"
    assert (
        inputs.get("ci-lite-requirements-file", "requirements-ci-lite.txt")
        == "requirements-ci-lite.txt"
    )
    assert inputs.get("test-requirements-file", "requirements-test.txt") == "requirements-test.txt"
    assert inputs.get("constraints-file", "constraints.txt") == "constraints.txt"
    assert setup.get("if") is None and setup.get("continue-on-error") is None
    assert job.get("continue-on-error") is None
    checkout_index = next(
        index
        for index, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    consumer_index = next(
        index for index, step in enumerate(steps) if step.get("name") == consumer_name
    )
    assert checkout_index < setup_index < consumer_index
    assert not any(str(step.get("uses", "")).startswith("actions/setup-python@") for step in steps)
    run_blocks = "\n".join(str(step.get("run", "")) for step in steps)
    assert "install_locked_python_requirements.py" not in run_blocks
    assert "PULSEPLATE_PSYCOPG_C_SDK" not in run_blocks
    for env in (workflow.get("env", {}), job.get("env", {}), setup.get("env", {})):
        assert "PULSEPLATE_PSYCOPG_C_SDK" not in env
    selected = locked_installer.resolve_requirement_files(
        requirements_file=REPO_ROOT / "requirements.txt",
        dev_requirements_file=REPO_ROOT / "requirements-dev.txt",
        test_requirements_file=REPO_ROOT / "requirements-test.txt",
        ci_lite_requirements_file=REPO_ROOT
        / inputs.get("ci-lite-requirements-file", "requirements-ci-lite.txt"),
        rag_vector_requirements_file=REPO_ROOT / "requirements-rag-vector.txt",
        install_dev=False,
        install_test=False,
        requirements_profile=profile,
    )
    expected = [REPO_ROOT / "requirements-ci-lite.txt"]
    if profile == "ci-test":
        expected.append(REPO_ROOT / "requirements-test.txt")
    assert selected == expected
    pins = locked_installer._exact_locked_artifacts(selected)
    assert {("psycopg", "3.3.4"), ("psycopg-c", "3.3.4")} <= pins


def test_python_setup_jobs_receive_devpi_credentials_on_main_push_only() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "github.event_name != 'pull_request' && secrets.DEVPI_CI_USER" not in workflow_text
    assert "github.event_name != 'pull_request' && secrets.DEVPI_CI_PASSWORD" not in workflow_text

    workflow = load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    expected_user = (
        "${{ github.event_name != 'pull_request' && "
        "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}"
    )
    expected_password = (
        "${{ github.event_name != 'pull_request' && "
        "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}"
    )

    for job_name, job in jobs.items():
        if not isinstance(job, dict) or not job_uses_python_setup(job):
            continue
        matching_steps = [
            step
            for step in job.get("steps", [])
            if isinstance(step, dict) and step.get("uses") == "./.github/actions/python-setup"
        ]
        assert matching_steps, f"{job_name} must call python-setup"
        for step in matching_steps:
            env = step.get("env")
            assert isinstance(env, dict), f"{job_name} python-setup step must declare env"
            assert env.get("DEVPI_CI_USER") == expected_user
            assert env.get("DEVPI_CI_PASSWORD") == expected_password


@pytest.mark.parametrize(
    "job_name",
    [
        "merge_readiness_gate",
        "lint",
        "security",
        "openapi-sync",
        "test-pr",
        "pgvector_compat",
        "test-feature",
        "test-main",
        "diff-coverage",
    ],
)
def test_proxy_dependent_jobs_fail_before_work_on_invalid_needs(job_name: str) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    job = load_ci_workflow()["jobs"][job_name]
    needs = as_needs_set(job)
    step = job["steps"][0]
    assert step["name"] == "Enforce prerequisite results"
    assert isinstance(step["env"], dict)
    assert isinstance(step["run"], str)
    gate_steps = job["steps"][:2] if job_name == "security" else [step]
    gate_env = {key: value for gate in gate_steps for key, value in gate["env"].items()}
    gate_script = "\n".join(gate["run"] for gate in gate_steps)
    if len(needs) > 1:
        assert "!cancelled()" in str(job["if"])
    if "changes" in needs and job_name not in {"merge_readiness_gate", "test-main"}:
        assert "needs.changes.result != 'success'" in str(job["if"])

    expected_keys = {
        (
            "PGVECTOR_RESULT"
            if need == "pgvector_compat" and job_name == "security"
            else need.upper().replace("-", "_") + "_RESULT"
        )
        for need in needs
    }
    assert expected_keys <= set(gate_env)
    for need in needs:
        key = (
            "PGVECTOR_RESULT"
            if need == "pgvector_compat" and job_name == "security"
            else need.upper().replace("-", "_") + "_RESULT"
        )
        assert gate_env[key] == "${{ needs." + need + ".result }}"

    def execute(overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update({key: "success" for key in expected_keys})
        if job_name == "security":
            env.update(PGVECTOR_RESULT="skipped", PGVECTOR_SELECTION="false")
        if job_name == "merge_readiness_gate":
            env.update(SECURITY_REQUIRED="true", PGVECTOR_REQUIRED="false", IOS_REQUIRED="true")
        env.update(overrides)
        return subprocess.run(  # nosec B603: resolved bash executes fixed workflow gate text (remove-by: 2026-10-31, ref: PR-consol-ci-1)
            [bash, "-e", "-o", "pipefail", "-c", gate_script],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    assert execute({}).returncode == 0
    for need in needs:
        key = (
            "PGVECTOR_RESULT"
            if need == "pgvector_compat" and job_name == "security"
            else need.upper().replace("-", "_") + "_RESULT"
        )
        for invalid in ("failure", "cancelled", "skipped"):
            overrides = {key: invalid}
            if need == "pgvector_compat":
                overrides["PGVECTOR_SELECTION"] = "true"
            assert execute(overrides).returncode != 0, (job_name, need, invalid)
    if job_name == "merge_readiness_gate":
        assert execute({"SECURITY_RESULT": "skipped", "SECURITY_REQUIRED": "false"}).returncode == 0
        assert execute({"SECURITY_RESULT": "failure", "SECURITY_REQUIRED": "false"}).returncode != 0
