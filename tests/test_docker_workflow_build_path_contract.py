"""Regression guards for the Docker workflow build-path consolidation contract."""

from __future__ import annotations

import ast
from datetime import date
from dataclasses import replace
from email.message import Message
from hashlib import sha256, sha3_256
from io import BytesIO
import json
import os
import shlex
import shutil
from ssl import SSLCertVerificationError
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, HTTPSHandler, Request
from urllib.response import addinfourl

from fastapi.testclient import TestClient
import pytest
import yaml

from scripts.ci import fetch_docker_source_artifacts as docker_sources

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
BACKEND_PYTHON_BASE_IMAGE = (
    "python:3.13.14-slim-bookworm"
    "@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64"
)
EXPECTED_BACKEND_PYTHON_FROM_LINES = (
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS sqlite-builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
)
EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS = {
    ("build.yml", "build", "Build Docker image (local, for tests)"),
    ("build.yml", "publish", "Build Docker image for publish scan"),
    ("trivy.yml", "build", "Build Docker image (production target)"),
    ("cd.yml", "build", "Build & Push backend image (staging)"),
    ("cd.yml", "build-production", "Build & Push image (production)"),
}


def test_finite_backend_exports_follow_credential_cleanup_and_do_not_publish() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    job = workflow["jobs"]["build"]
    assert job["permissions"] == {"actions": "read", "contents": "read"}
    production = _step_by_name(job, "Build Docker image (local, for tests)")
    staging = _step_by_name(job, "Build staging image from the same qualified backend inputs")
    assert production["with"]["target"] == "production"
    assert staging["with"]["target"] == "staging"
    for step in (production, staging):
        assert step["with"]["push"] is False and step["with"]["load"] is True
        assert step["with"]["platforms"] == "linux/amd64"
        assert (
            step["with"]["build-args"]
            == "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt\n"
        )
        assert "pp_netrc=${{ runner.temp }}/pulseplate-docker-netrc" in step["with"]["secret-files"]
    export_name = "Retain exact production and staging native image bytes"
    assert (
        _step_index(job, production["name"])
        < _step_index(job, staging["name"])
        < _step_index(job, "Remove private Python index Docker authentication")
        < _step_index(job, export_name)
    )
    exported = _step_by_name(job, export_name)
    run = exported["run"]
    assert 'test ! -e "$RUNNER_TEMP/pulseplate-docker-netrc"' in run
    assert '[docker, "image", "save", "--output", str(archive), tag]' in run
    assert "again != observed" in run and '"archive_sha256": digest(archive)' in run
    assert "No registry publication or guest execution in this export step" in run
    assert "docker login" not in run and '"push"' not in run
    python_source = run.split("python3 - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    ast.parse(python_source)
    uploaded = _step_by_name(job, "Preserve exact backend native images for pullback qualification")
    assert (
        uploaded["if"]
        == "${{ always() && steps.backend-native-export.outputs.complete == 'true' }}"
    )


def test_finite_arm_sdk_origin_is_manual_canonical_static_and_not_tool_trust() -> None:
    from scripts.ci.install_locked_python_requirements import PSYCOPG_SDK_TARGETS

    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    job = workflow["jobs"]["backend-arm-sdk-qualification"]
    assert job["runs-on"] == "ubuntu-24.04-arm"
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.mode == 'backend-sdk-qualify' && "
        "github.repository == 'Katsiarynakavaleuskaya/PulsePlate' && github.repository_id == '1043311030'"
    )
    targets = [
        target
        for target in PSYCOPG_SDK_TARGETS
        if (target.machine, target.minor) == ("aarch64", 13)
    ]
    assert len(targets) == 1 and job["env"]["SDK_SOURCE_IMAGE"] == targets[0].source_image
    guard = _step_by_name(job, "Require one explicit genuine ARM SDK producer attempt")["run"]
    assert "test \"$GITHUB_RUN_ATTEMPT\" = '1'" in guard
    assert "test \"$GITHUB_REPOSITORY_ID\" = '1043311030'" in guard
    assert 'test "$(uname -m)" = aarch64' in guard
    acquisition = _step_by_name(job, "Prepare existing private acquisition credentials")
    assert acquisition["env"] == {
        "DEVPI_CI_USER": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}",
        "DEVPI_CI_PASSWORD": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}",
    }
    assert (
        'if [[ -z "${DEVPI_CI_USER:-}" && -z "${DEVPI_CI_PASSWORD:-}" ]]; then exit 0; fi'
        in acquisition["run"]
    )
    built = _step_by_name(job, "Build genuine ARM cp313 SDK using its existing target")
    assert built["with"]["target"] == "psycopg-sdk"
    assert built["with"]["platforms"] == "linux/arm64"
    assert built["with"]["push"] is False
    name = "Bind genuine SDK origin, image and exported payload bytes"
    assert (
        _step_index(job, built["name"])
        < _step_index(job, "Remove acquisition credentials before static SDK validation")
        < _step_index(job, name)
    )
    run = _step_by_name(job, name)["run"]
    assert 'read_psycopg_c_sdk(sdk / "psycopg-sdk", native_root=sdk)' in run
    assert "SDK image and local exporter bytes differ" in run
    assert "External clean supporting-tool-root admission" in run
    assert "# Static wheel/receipt/DSO recognition only. No supplied SDK library," in run
    assert '"--entrypoint", "/not-executed", image_id' in run
    python_source = run.split("python3 - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    ast.parse(python_source)


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _step_names(job: dict[str, object]) -> list[str]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    names: list[str] = []
    for step in steps:
        assert isinstance(step, dict)
        name = step.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _step_by_name(job: dict[str, object], step_name: str) -> dict[str, object]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {step_name!r}")


def _step_index(job: dict[str, object], step_name: str) -> int:
    return _step_names(job).index(step_name)


def _root_context_docker_build_steps(
    workflow: dict[str, object],
) -> list[tuple[str, dict[str, object], str]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_steps: list[tuple[str, dict[str, object], str]] = []
    for job_name, job in jobs.items():
        assert isinstance(job_name, str)
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            assert isinstance(step, dict)
            uses = step.get("uses")
            if not (isinstance(uses, str) and uses.startswith("docker/build-push-action@")):
                continue
            step_with = step.get("with")
            assert isinstance(
                step_with,
                dict,
            ), f"{job_name}/{step.get('name')} must define docker build inputs"
            context = step_with.get("context")
            if context != ".":
                # Frontend/Caddy builds do not consume the backend SQLite source bundle.
                continue
            step_name = step.get("name")
            assert isinstance(step_name, str)
            build_steps.append((job_name, job, step_name))
    return build_steps


def _docker_source_manifest(
    *,
    payload: bytes = b"sqlite source",
    review_by: str = "2026-06-28",
    filename: str = "sqlite-autoconf-3530200.tar.gz",
    url: str = "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
) -> dict[str, object]:
    digest = sha3_256(payload).hexdigest()
    return {
        "schema_version": 1,
        "generated_at": "2026-06-14",
        "review_by": review_by,
        "artifacts": [
            {
                "name": "sqlite-autoconf",
                "version": "3530200",
                "filename": filename,
                "url": url,
                "sha3_256_parts": [digest[index : index + 8] for index in range(0, len(digest), 8)],
            }
        ],
    }


def _write_docker_source_manifest(tmp_path: Path, manifest: dict[str, object]) -> Path:
    manifest_path = tmp_path / "docker_source_artifacts.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_removed_duplicate_docker_pr_workflows() -> None:
    """PR-time production image validation stays in the canonical Docker workflow."""
    assert not (WORKFLOWS_DIR / "docker-image.yml").exists()
    assert not (WORKFLOWS_DIR / "docker-openapi-smoke.yml").exists()


def test_build_workflow_owns_docker_validation_contract() -> None:
    """Build workflow keeps runtime, telemetry, budget, and OpenAPI smoke checks together."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    step_names = _step_names(build_job)

    assert "Build Docker image (local, for tests)" in step_names
    assert "Check Docker runtime dependency surface" in step_names
    assert "Collect Docker image telemetry" in step_names
    assert "Enforce Docker image budget" in step_names
    assert "Test Docker image" in step_names

    test_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Test Docker image"
    )
    build_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Build Docker image (local, for tests)"
    )
    build_step_with = build_step["with"]
    assert isinstance(build_step_with, dict)
    assert build_step_with["target"] == "production"
    assert build_step_with["load"] is True
    assert build_step_with["push"] is False
    assert build_step_with["provenance"] is False

    run_script = test_step["run"]
    assert isinstance(run_script, str)
    assert "openapi.json" in run_script
    assert "/api/v1/bmi" in run_script
    assert (
        'assert "/api/v1/bodyfat" not in paths, '
        '"/api/v1/bodyfat must not leak into canonical OpenAPI"'
    ) in run_script


def test_build_workflow_does_not_expose_github_token_to_pr_baseline_script() -> None:
    """PR builds must not pass workflow tokens to checked-out baseline code."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    steps = build_job["steps"]
    assert isinstance(steps, list)

    fallback_step = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("name") == "Use checked-in Docker image telemetry baseline on pull requests"
    )
    assert fallback_step["if"] == "github.event_name == 'pull_request'"
    fallback_run = fallback_step["run"]
    assert isinstance(fallback_run, str)
    assert "fetch_docker_image_baseline.py" not in fallback_run
    assert "GH_TOKEN" not in fallback_step.get("env", {})
    assert "GITHUB_TOKEN" not in fallback_step.get("env", {})

    resolve_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Resolve Docker image telemetry baseline"
    )
    assert resolve_step["if"] == "github.event_name != 'pull_request'"
    resolve_env = resolve_step["env"]
    assert isinstance(resolve_env, dict)
    assert resolve_env["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert resolve_env["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_production_dockerfile_prunes_package_manager_surface() -> None:
    """Production target removes package-manager, gzip, ACL/attr, and Perl runtime packages."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production_section = dockerfile.split("FROM runtime-base AS production", 1)[1]
    production_section = production_section.split("FROM production AS staging", 1)[0]
    pruning_block = production_section.split(
        "# SECURITY: production-package-pruning-start",
        1,
    )[
        1
    ].split("# SECURITY: production-package-pruning-end", 1)[0]

    assert "dpkg --purge --force-depends --force-remove-essential" in pruning_block
    assert "perl_module_packages=" in pruning_block
    assert "'perl-modules-*'" in pruning_block
    assert (
        "for package in apt gzip gpgv libacl1 libattr1 libgnutls30 "
        "libsqlite3-0 libpcre2-8-0 perl-base ${perl_module_packages} bsdutils libblkid1 libmount1 "
        "libsmartcols1 libuuid1 mount util-linux util-linux-extra libsystemd0 libudev1; do"
    ) in pruning_block
    for package in (
        "apt",
        "gzip",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "libpcre2-8-0",
        "perl-base",
    ):
        assert f"        {package} \\" in pruning_block
        assert f" {package} " in pruning_block
    assert "dpkg-query -W -f='${db:Status-Abbrev}'" in pruning_block
    assert "for binary in gzip gunzip zcat" in pruning_block
    assert 'command -v "${binary}"' in pruning_block
    assert "import gzip" in pruning_block
    assert "gzip.compress(payload, mtime=0)" in pruning_block
    assert "import ssl" in pruning_block
    assert "import sqlite3" in pruning_block
    assert "expected >= 3.53.2" in pruning_block


def test_build_workflow_blocks_removed_acl_attr_runtime_packages() -> None:
    """Docker runtime surface guard fails if removed packages return."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)

    surface_step = _step_by_name(build_job, "Check Docker runtime dependency surface")
    run_script = surface_step["run"]
    assert isinstance(run_script, str)

    for package in ("gzip", "libacl1", "libattr1"):
        assert f"--blocked-debian-package {package}" in run_script


def test_dockerfile_pins_all_backend_python_stages_to_one_oci_index() -> None:
    """Runtime bases stay fixed; only the exact isolated SDK family varies."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    trivyignore = (REPO_ROOT / ".trivyignore").read_text(encoding="utf-8")
    python_from_lines = tuple(
        line.strip()
        for line in dockerfile.splitlines()
        if line.lstrip().casefold().startswith("from ") and "python" in line.casefold()
    )

    sdk_from_lines = (
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS native-builder",
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS psycopg-inputs",
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS dev-bootstrap-inputs",
    )
    assert len(python_from_lines) == 6
    assert (
        tuple(line for line in python_from_lines if line not in sdk_from_lines)
        == EXPECTED_BACKEND_PYTHON_FROM_LINES
    )
    assert tuple(line for line in python_from_lines if line in sdk_from_lines) == sdk_from_lines
    assert "3.13.13" not in dockerfile
    assert f"FROM {BACKEND_PYTHON_BASE_IMAGE.partition('@')[0]} AS" not in dockerfile
    assert BACKEND_PYTHON_BASE_IMAGE.partition("@")[0] in trivyignore
    assert "3.13.13" not in trivyignore


@pytest.mark.parametrize(
    ("stage", "helpers"),
    (
        ("native-builder", ("fetch_docker_source_artifacts.py",)),
        (
            "psycopg-inputs",
            ("install_locked_python_requirements.py", "check_private_python_proxy_health.py"),
        ),
        ("psycopg-wheel-builder", ("install_locked_python_requirements.py",)),
        (
            "dev-bootstrap-inputs",
            ("install_locked_python_requirements.py", "check_private_python_proxy_health.py"),
        ),
        (
            "development",
            ("install_locked_python_requirements.py", "check_python_startup_hooks.py"),
        ),
    ),
)
def test_native_helper_stage_layout_executes_real_cli(
    tmp_path: Path, stage: str, helpers: tuple[str, ...]
) -> None:
    """Actual COPY layouts preserve helper roots and parse operations without acquisition."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    section = dockerfile.split(f" AS {stage}\n", 1)[1].split("\nFROM ", 1)[0]
    if stage == "psycopg-wheel-builder":
        assert "FROM native-builder AS psycopg-wheel-builder" in dockerfile
        parent = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
        section = parent + "\n" + section
    stage_root = tmp_path / stage
    staged: dict[str, Path] = {}
    for line in section.splitlines():
        if not line.startswith("COPY scripts/ci/"):
            continue
        tokens = shlex.split(line)
        destination = PurePosixPath(tokens[-1])
        for source in tokens[1:-1]:
            source_path = REPO_ROOT / source
            target = destination / source_path.name if tokens[-1].endswith("/") else destination
            assert target.parents[2] == PurePosixPath(
                "/tooling"
            ), "Native helper COPY lost the repository-root depth required by the real CLI"
            materialized = stage_root / target.relative_to("/")
            materialized.parent.mkdir(parents=True, exist_ok=True)
            materialized.write_bytes(source_path.read_bytes())
            staged[source_path.name] = materialized
    home = tmp_path / "empty-home"
    home.mkdir()
    environment = {"PATH": os.defpath, "HOME": str(home), "LANG": "C.UTF-8"}
    for name in helpers:
        result = subprocess.run(
            [sys.executable, str(staged[name]), "--help"],
            cwd=stage_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout
    installer = staged.get("install_locked_python_requirements.py")
    if installer is not None:
        operations = (
            (["--build-psycopg-c"], "Exact Psycopg build requires all four explicit inputs"),
            (
                ["--prefetch-psycopg-source", str(tmp_path / "source"), "--prefetch-only"],
                "Locked installer operation selectors are mutually exclusive.",
            ),
            (
                ["--prefetch-psycopg-build-wheels", str(tmp_path / "wheels"), "--prefetch-only"],
                "Locked installer operation selectors are mutually exclusive.",
            ),
        )
        for flags, expected_error in operations:
            result = subprocess.run(
                [
                    sys.executable,
                    str(installer),
                    "--index-url",
                    "https://packages.pulseplate.app/root/pulseplate/+simple/",
                    *flags,
                ],
                cwd=stage_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert result.returncode == 1
            assert expected_error in result.stdout, result.stdout + result.stderr
        assert not (tmp_path / "source").exists()
        assert not (tmp_path / "wheels").exists()


def test_ncurses_replacement_preserves_debian_versioned_consumers() -> None:
    """ABI6 keeps its symbol namespaces and checks actual consumers after pruning."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    configuration = dockerfile.split("cd /build/source/ncurses-6.6", 1)[1].split("make -j2", 1)[0]
    for option in ("--with-versioned-syms", "--with-abi-version=6", "--enable-widec"):
        assert option in configuration
    assert "--with-termlib=tinfo" in configuration
    source = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    assert dockerfile.index(
        "USER pulseplate", dockerfile.index("production-package-pruning-end")
    ) < (dockerfile.index("<<'PY_NATIVE_TERMINAL'"))
    assert 'run_checked_consumer(["/bin/bash", "--noprofile", "--norc"' in source
    assert 'for interpreter in ("/usr/local/bin/python", "/opt/venv/bin/python"):' in source
    assert "run_checked_consumer([interpreter" in source
    assert "curses.setupterm" in source and "import curses.panel" in source
    assert 'check_native_empty_panel_stack(ctypes.CDLL("libpanelw.so.6"))' in source
    assert "curses.panel.bottom_panel" not in source
    assert "readline.get_current_history_length" in source
    assert "actual_ncurses = ncurses.curses_version()" in source
    assert "linker.dlvsym(handle._handle, symbol, version)" in source
    for version in (
        "NCURSES6_TINFO_5.0.19991023",
        "NCURSESW6_5.1.20000708",
        "NCURSESW6_5.3.20021019",
    ):
        assert version in source
    assert 'Path("/proc/self/maps")' in source and "hashlib.sha256" in source
    assert "LD_LIBRARY_PATH" not in source and "LD_PRELOAD" not in source


@pytest.mark.parametrize(
    ("producer", "expected_exit", "diagnostic"),
    (
        ("print('ordinary terminal consumer')", 0, ""),
        (
            "import sys; sys.stderr.write('no version information available\\n')",
            1,
            "no version information available",
        ),
        (
            "import sys; sys.stderr.write('version NCURSES6_TINFO not found\\n')",
            1,
            "version NCURSES6_TINFO not found",
        ),
        ("raise SystemExit(2)", 1, "Native terminal consumer returned an error"),
        (
            "import sys; print('ordinary output'); sys.stderr.write('other diagnostic\\n')",
            1,
            "other diagnostic",
        ),
    ),
)
def test_real_terminal_consumer_adapter_rejects_diagnostics(
    tmp_path: Path, producer: str, expected_exit: int, diagnostic: str
) -> None:
    """Execute the shipped adapter with real child exits and stdout/stderr streams."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    parsed = ast.parse(source)
    declarations = ast.Module(
        body=[node for node in parsed.body if isinstance(node, (ast.Import, ast.FunctionDef))],
        type_ignores=[],
    )
    command = [sys.executable, "-c", producer]
    program = ast.unparse(declarations) + f"\nrun_checked_consumer({command!r})\n"
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
    if diagnostic:
        assert diagnostic in result.stderr
    else:
        assert result.stdout == "ordinary terminal consumer\n"
        assert not result.stderr


@pytest.mark.parametrize("above,below,expected_exit", ((None, None, 0), (1, None, 1), (None, 1, 1)))
def test_native_panel_null_boundary_rejects_nonempty_results(
    tmp_path: Path, above: int | None, below: int | None, expected_exit: int
) -> None:
    """The shipped NULL-result checker rejects either unexpected panel pointer."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    wrapper = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    assignment = next(
        node
        for node in ast.parse(wrapper).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "consumer_source"
            for target in node.targets
        )
    )
    assert isinstance(assignment.value, ast.Constant) and isinstance(assignment.value.value, str)
    helper = next(
        node
        for node in ast.parse(assignment.value.value).body
        if isinstance(node, ast.FunctionDef) and node.name == "check_native_empty_panel_stack"
    )
    source = "import ctypes\nimport types\n" + ast.unparse(helper)
    source += f"""
class SyntheticPanelOperation:
    def __init__(self, value):
        self.value = value
    def __call__(self, pointer):
        assert pointer is None
        assert self.argtypes == [ctypes.c_void_p] and self.restype is ctypes.c_void_p
        return self.value
panel = types.SimpleNamespace(panel_above=SyntheticPanelOperation({above!r}),
                              panel_below=SyntheticPanelOperation({below!r}))
check_native_empty_panel_stack(panel)
"""
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    if expected_exit:
        assert "Native panel empty-stack boundary returned a non-NULL panel" in result.stderr
    else:
        assert not result.stdout and not result.stderr


def test_native_shared_export_preserves_source_aliases_and_excludes_static_inputs(
    tmp_path: Path,
) -> None:
    """Real cp -a preserves the source SDK topology before directory-content COPY."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    section = dockerfile.split(" AS native-shared-runtime\n", 1)[1].split("\nFROM ", 1)[0]
    assert "RUN --network=none mkdir -p /native-shared-libraries" in section
    assert "cp -a /native/usr/local/lib/*.so* /native-shared-libraries/" in section
    assert (
        dockerfile.count(
            "COPY --from=native-shared-runtime /native-shared-libraries/ /usr/local/lib/"
        )
        == 2
    )
    assert "COPY --from=native-builder /native/usr/local/lib/*.so*" not in dockerfile
    source = tmp_path / "source"
    export = tmp_path / "export"
    source.mkdir()
    export.mkdir()
    payload = b"synthetic canonical shared DSO bytes"
    (source / "libpq.so.5.18").write_bytes(payload)
    for name in ("libpq.so", "libpq.so.5"):
        (source / name).symlink_to("libpq.so.5.18")
    (source / "libpq.a").write_bytes(b"static archive excluded")
    (source / "pkgconfig").mkdir()
    (source / "pkgconfig/libpq.pc").write_text("excluded package configuration")
    copy_binary = shutil.which("cp")
    assert copy_binary is not None
    result = subprocess.run(
        [copy_binary, "-a", *(str(path) for path in sorted(source.glob("*.so*"))), str(export)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in export.iterdir()} == {"libpq.so", "libpq.so.5", "libpq.so.5.18"}
    assert (export / "libpq.so.5.18").is_file() and not (export / "libpq.so.5.18").is_symlink()
    for name in ("libpq.so", "libpq.so.5"):
        assert (export / name).is_symlink()
        assert (export / name).readlink() == Path("libpq.so.5.18")
        assert (export / name).read_bytes() == payload


@pytest.mark.parametrize(
    "scenario",
    ("canonical", "wrong_path", "extra_path", "flattened_alias", "absolute_alias", "wrong_hash"),
)
def test_libpq_lineage_guard_requires_exact_source_topology_and_bytes(
    tmp_path: Path, scenario: str
) -> None:
    """The shipped guard rejects valid-version libraries with the wrong source identity."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    assert 'psycopg.__version__ != "3.3.4"' in source
    assert 'pq.__impl__ != "c" or pq.version() != 180006' in source
    assert "OpenSSL 4.0.3" in source
    assert "Psycopg actual mapped libpq paths" in source
    assert "Psycopg source DSO hash" in source
    helper = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "check_libpq_lineage"
    )
    root = tmp_path / "native-lib"
    root.mkdir()
    canonical = root / "libpq.so.5.18"
    payload = b"synthetic reviewed canonical DSO"
    canonical.write_bytes(payload)
    for name in ("libpq.so", "libpq.so.5"):
        (root / name).symlink_to("libpq.so.5.18")
    loaded = [canonical]
    if scenario == "wrong_path":
        loaded = [tmp_path / "wrong-lib/libpq.so.5.18"]
    elif scenario == "extra_path":
        loaded.append(tmp_path / "extra-lib/libpq.so.5")
    elif scenario == "flattened_alias":
        (root / "libpq.so.5").unlink()
        (root / "libpq.so.5").write_bytes(payload)
    elif scenario == "absolute_alias":
        (root / "libpq.so.5").unlink()
        (root / "libpq.so.5").symlink_to(canonical)
    receipt = tmp_path / "sdk.json"
    receipt.write_text(
        json.dumps(
            {
                "native_libraries": {
                    "libpq.so.5": sha256(
                        b"different bytes" if scenario == "wrong_hash" else payload
                    ).hexdigest()
                }
            }
        )
    )
    program = "import hashlib, json\nfrom pathlib import Path\n" + ast.unparse(helper)
    program += (
        f"\ncheck_libpq_lineage({{Path(name) for name in {[str(path) for path in loaded]!r}}}, "
        f"Path({str(root)!r}), Path({str(receipt)!r}))\n"
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
    assert result.returncode == (0 if scenario == "canonical" else 1), result.stdout + result.stderr
    assert "Psycopg actual mapped libpq paths" in result.stdout
    if scenario in ("canonical", "wrong_hash"):
        assert "Psycopg source DSO hash" in result.stdout
    if scenario != "canonical":
        assert "Psycopg" in result.stderr


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
def test_runtime_openssl_guard_uses_openssl3_patch_field_and_release_status(
    tmp_path: Path, version_info: tuple[int, ...], expected_exit: int
) -> None:
    """Execute the shipped version guard against the public OpenSSL 3 tuple shape."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and node.value.args[0].value == "Loaded shared OpenSSL"
        )
        or (
            isinstance(node, ast.If)
            and "Psycopg runtime shared OpenSSL mismatch" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    assert isinstance(statements[0], ast.Expr) and isinstance(statements[1], ast.If)
    program = (
        "import types\n"
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
        assert "Psycopg runtime shared OpenSSL mismatch" in result.stderr
    else:
        assert not result.stderr


def test_dockerfile_builds_verified_sqlite_runtime_library() -> None:
    """Dockerfile builds pre-fetched SQLite 3.53.2 before removing Debian SQLite."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    sqlite_builder_section = dockerfile.split("AS sqlite-builder", 1)[1]
    sqlite_builder_section = sqlite_builder_section.split("FROM python", 1)[0]
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert 'ARG SQLITE_AUTOCONF_VERSION="3530200"' in dockerfile
    assert "SQLite source pins are intentionally mirrored" in dockerfile
    assert "Docker COPY source paths are literal" in dockerfile
    checksum_parts = (
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    )
    for index, checksum_part in enumerate(checksum_parts, start=1):
        assert f'ARG SQLITE_AUTOCONF_SHA3_256_PART_{index}="{checksum_part}"' in dockerfile
    assert len("".join(checksum_parts)) == 64
    assert 'os.environ[f"SQLITE_AUTOCONF_SHA3_256_PART_{index}"]' in sqlite_builder_section
    assert "urlopen" not in sqlite_builder_section
    assert "urllib" not in sqlite_builder_section
    assert "https://sqlite.org" not in sqlite_builder_section
    assert "COPY build/docker-sources/sqlite-autoconf-3530200.tar.gz" in sqlite_builder_section
    assert "!build/docker-sources/sqlite-autoconf-*.tar.gz" in dockerignore
    assert "sha3_256(payload).hexdigest()" in sqlite_builder_section
    assert "SQLite source SHA3 mismatch" in sqlite_builder_section
    assert "./configure --prefix=/usr/local --disable-static --enable-shared" in dockerfile
    assert "COPY --from=sqlite-builder /usr/local/lib/libsqlite3.so*" in runtime_base_section
    assert "/etc/ld.so.conf.d/00-pulseplate-local-sqlite.conf" in runtime_base_section
    assert "ldconfig" in runtime_base_section
    assert "import sqlite3" in runtime_base_section
    assert "expected >= 3.53.2" in runtime_base_section


def test_docker_source_artifact_manifest_pins_sqlite_source() -> None:
    """Docker source-artifact manifest pins approved SQLite source with SHA3 parts."""
    manifest = json.loads(
        (REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text(encoding="utf-8")
    )
    artifacts = manifest["artifacts"]
    assert manifest["schema_version"] == 1
    assert manifest["generated_at"] == "2026-10-04"
    assert manifest["review_by"] == "2026-10-21"
    assert len(artifacts) == 15
    assert [row["name"] for row in artifacts[:4]] == [
        "sqlite-autoconf",
        "util-linux",
        "pcre2",
        "sljit",
    ]
    for name in ("SQLite", "util-linux", "PCRE2", "SLJIT"):
        assert name in manifest["reason"]

    artifact = artifacts[0]
    parsed_url = urlparse(artifact["url"])
    assert artifact["name"] == "sqlite-autoconf"
    assert artifact["version"] == "3530200"
    assert artifact["filename"] == "sqlite-autoconf-3530200.tar.gz"
    assert parsed_url.scheme == "https"
    assert parsed_url.hostname == "sqlite.org"
    assert parsed_url.path == "/2026/sqlite-autoconf-3530200.tar.gz"
    assert artifact["sha3_256_parts"] == [
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    ]
    assert len("".join(artifact["sha3_256_parts"])) == 64


def test_docker_source_artifact_manifest_review_window_is_inclusive(tmp_path: Path) -> None:
    """Preserve historical5/6 source rejection and current21/22 admission."""
    manifest_path = REPO_ROOT / "scripts/ci/docker_source_artifacts.json"
    historical = json.loads(manifest_path.read_text())
    historical["generated_at"] = "2026-09-28"
    historical["review_by"] = "2026-10-05"
    old_path = _write_docker_source_manifest(tmp_path, historical)
    assert len(docker_sources.load_manifest(old_path, today=date(2026, 10, 5))) == 15
    with pytest.raises(RuntimeError, match="review_by is stale: 2026-10-05"):
        docker_sources.load_manifest(old_path, today=date(2026, 10, 6))
    for day in (6, 8, 21):
        assert len(docker_sources.load_manifest(manifest_path, today=date(2026, 10, day))) == 15
    with pytest.raises(RuntimeError, match="review_by is stale: 2026-10-21"):
        docker_sources.load_manifest(manifest_path, today=date(2026, 10, 22))


def _forecast_workflow_step() -> tuple[dict[str, object], str]:
    workflow = _load_workflow(WORKFLOWS_DIR / "nightly.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["review-deadline-forecast"]
    assert isinstance(job, dict)
    step = _step_by_name(job, "Forecast source and suppression review deadlines")
    run = step["run"]
    assert isinstance(run, str)
    return job, run


def _run_forecast_workflow(
    tmp_path: Path, *, today: date, review_by: str = "2026-10-05", policy: str | None = None
) -> tuple[subprocess.CompletedProcess[str], str]:
    manifest_dir = tmp_path / "scripts" / "ci"
    policy_dir = tmp_path / "trivy"
    manifest_dir.mkdir(parents=True)
    policy_dir.mkdir()
    (manifest_dir / "docker_source_artifacts.json").write_text(
        json.dumps(_docker_source_manifest(review_by=review_by)), encoding="utf-8"
    )
    (policy_dir / "ignore-policy.rego").write_text(
        (
            policy
            if policy is not None
            else (REPO_ROOT / "trivy" / "ignore-policy.rego").read_text(encoding="utf-8")
        ),
        encoding="utf-8",
    )

    _, run = _forecast_workflow_step()
    marker = "python3 - <<'PY'\n"
    assert run.startswith("set -euo pipefail\n" + marker)
    source = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    assert "datetime.now(UTC).date()" in source
    functions = source.split('if __name__ == "__main__":', 1)[0]
    guard = (
        "import urllib.request\n"
        "def reject_network(*args, **kwargs):\n"
        "    raise AssertionError('forecast must not use network')\n"
        "urllib.request.urlopen = reject_network\n"
    )
    invocation = f"\nraise SystemExit(main(date.fromisoformat({today.isoformat()!r}), Path({str(tmp_path)!r})))\n"
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [sys.executable, "-c", guard + functions + invocation],
        cwd=REPO_ROOT,
        env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary)},
        capture_output=True,
        text=True,
        check=False,
    )
    return result, summary.read_text(encoding="utf-8") if summary.exists() else ""


def test_nightly_forecast_job_is_main_only_private_free_and_independent() -> None:
    job, run = _forecast_workflow_step()
    workflow = _load_workflow(WORKFLOWS_DIR / "nightly.yml")

    assert workflow["jobs"]["test"] != job
    assert job["if"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "(github.event_name == 'schedule' || github.event_name == 'workflow_dispatch') }}"
    )
    assert job["timeout-minutes"] == 2
    assert job["permissions"] == {"contents": "read"}
    assert job["env"] == {
        "PULSEPLATE_PYTHON_INDEX_URL": "",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "",
    }
    checkout = _step_by_name(job, "Checkout code")
    assert checkout["with"] == {"persist-credentials": False}
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" == checkout["uses"]
    assert "load_manifest" in run and "evaluate_policy_file" in run
    assert "urlopen" not in run and "--ignore-policy" not in run
    assert "GITHUB_STEP_SUMMARY" in run


@pytest.mark.parametrize(
    ("today", "expected_exit", "current_finding", "forecast_finding"),
    [
        (date(2026, 9, 30), 0, False, False),
        (date(2026, 10, 2), 1, False, True),
        (date(2026, 10, 4), 1, False, True),
        (date(2026, 10, 6), 1, True, True),
    ],
)
def test_nightly_forecast_executes_utc_date_boundaries_and_labels(
    tmp_path: Path,
    today: date,
    expected_exit: int,
    current_finding: bool,
    forecast_finding: bool,
) -> None:
    historical = (
        "package trivy\n\nimport rego.v1\n"
        "# Suppression expires: 2026-10-07 (manual removal)\n"
        "# Review-by: 2026-10-05 (manual removal)\n"
        "# Review-by: 2026-10-07 (manual removal)\n"
        'default ignore := false\nignore if {\n\tinput.VulnerabilityID == "CVE-0000-0000"\n}\n'
    )
    result, summary = _run_forecast_workflow(tmp_path, today=today, policy=historical)

    assert result.returncode == expected_exit, result.stderr
    assert (
        f"UTC today: {today}; UTC forecast date: {date.fromordinal(today.toordinal() + 4)}"
        in summary
    )
    assert f"### CURRENT: {'attention required' if current_finding else 'no finding'}" in summary
    assert f"### FORECAST: {'attention required' if forecast_finding else 'no finding'}" in summary
    if today == date(2026, 10, 2):
        assert "review-by 2026-10-05" in summary
        assert "review-by 2026-10-07" not in summary
    if today == date(2026, 10, 4):
        assert "review-by 2026-10-07" in summary
        assert "Expired Trivy ignore policy" in summary


@pytest.mark.parametrize(
    ("review_by", "policy"),
    [
        ("bad-date", None),
        ("2026-10-05", "package trivy\nnot a valid policy"),
    ],
)
def test_nightly_forecast_malformed_inputs_fail_closed(
    tmp_path: Path, review_by: str, policy: str | None
) -> None:
    result, summary = _run_forecast_workflow(
        tmp_path, today=date(2026, 9, 28), review_by=review_by, policy=policy
    )

    assert result.returncode == 1, result.stderr
    assert "### CURRENT: attention required" in summary
    assert "### FORECAST: attention required" in summary


def test_libuuid_source_and_production_native_linkage_contract() -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    record = next(row for row in manifest["artifacts"] if row["name"] == "util-linux")
    assert record["version"] == "2.42.3"
    assert "".join(record["sha3_256_parts"]) == (
        "3edc35e7d261478bf9910ec87b70ae0c2be133e8ab523e2683ccfc0704d51652"  # pragma: allowlist secret
    )
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    assert "FROM sqlite-builder AS uuid-builder" in dockerfile
    assert "--disable-all-programs --enable-libuuid --disable-static" in dockerfile
    assert "make -j2 libuuid.la" in dockerfile
    production = dockerfile.split("FROM runtime-base AS production", 1)[1].split(
        "FROM production AS staging", 1
    )[0]
    assert "COPY --from=uuid-builder /opt/libuuid/libuuid.so.1.3.0" in production
    assert "import _uuid" in production and "_uuid.generate_time_safe()" in production
    assert 'Path("/proc/self/maps")' in production and "loaded != {expected}" in production
    assert "sha256sum --check" in production
    assert "/opt/libuuid/COPYING" in production
    assert "for interpreter in /usr/local/bin/python /opt/venv/bin/python" in production
    assert production.index("USER pulseplate") < production.index("import _uuid")


@pytest.mark.parametrize("corrupt_digest", [None, "sha256", "sha3"])
def test_libuuid_build_executes_both_source_digest_checks(
    tmp_path: Path, corrupt_digest: str | None
) -> None:
    """Execute the actual builder verifier with independently corrupted expected hashes."""
    payload = b"bounded util-linux source fixture"
    record = {
        "name": "util-linux",
        "version": "2.42.3",
        "sha256_parts": [sha256(payload).hexdigest()],
        "sha3_256_parts": [sha3_256(payload).hexdigest()],
    }
    if corrupt_digest == "sha256":
        record["sha256_parts"] = ["0" * 64]
    elif corrupt_digest == "sha3":
        record["sha3_256_parts"] = ["0" * 64]
    manifest_path = _write_docker_source_manifest(tmp_path, {"artifacts": [record]})
    archive_path = tmp_path / "util-linux.tar.gz"
    archive_path.write_bytes(payload)
    builder = (
        (REPO_ROOT / "Dockerfile").read_text().split("FROM sqlite-builder AS uuid-builder", 1)[1]
    )
    verifier = builder.split("RUN python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    verifier = verifier.replace(
        '"/opt/libuuid/docker_source_artifacts.json"', repr(str(manifest_path))
    ).replace('"/tmp/util-linux.tar.gz"', repr(str(archive_path)))
    result = subprocess.run(
        [sys.executable, "-c", verifier], capture_output=True, text=True, check=False
    )
    if corrupt_digest is None:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert f"{corrupt_digest.upper()} mismatch" in result.stderr


def test_pr_build_runs_native_suppression_contract_after_pinned_scan() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build = jobs["build"]
    assert isinstance(build, dict)
    names = _step_names(build)
    assert names.count("Validate native Trivy suppression semantics") == 1
    assert names.index("Scan production image before publication eligibility") + 1 == names.index(
        "Validate native Trivy suppression semantics"
    )
    assert names.index("Validate native Trivy suppression semantics") + 1 == names.index(
        "Validate production image report and render SARIF"
    )
    scan = _step_by_name(build, "Scan production image before publication eligibility")
    assert scan["uses"] == ("aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25")
    assert scan["with"]["version"] == "v0.74.0"
    assert scan["with"]["ignore-policy"] == ".trivy-ignore-policy.rego"
    native = _step_by_name(build, "Validate native Trivy suppression semantics")
    assert native == {
        "name": "Validate native Trivy suppression semantics",
        "if": "github.event_name == 'pull_request'",
        "run": "set -euo pipefail\npython3 scripts/ci/check_trivy_ignore_policy_native.py\n",
    }
    assert "continue-on-error" not in native
    assert "Validate native Trivy suppression semantics" not in _step_names(jobs["publish"])


def test_pr_and_publish_share_strict_native_image_scan_predicates() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    build = jobs["build"]
    publish = jobs["publish"]
    first = _step_by_name(build, "Scan production image before publication eligibility")
    second = _step_by_name(publish, "Run Trivy vulnerability scanner (image scan, fail-closed)")
    assert first.get("env", {}).get("TRIVY_DB_REPOSITORY") == second["env"]["TRIVY_DB_REPOSITORY"]
    for key in (
        "version",
        "scan-type",
        "scanners",
        "severity",
        "exit-code",
        "format",
        "trivyignores",
        "ignore-policy",
    ):
        assert first["with"][key] == second["with"][key]
    for step in (first, second):
        assert step["with"]["version"] == "v0.74.0"
        assert step["with"].get("ignore-unfixed", False) is False
        assert "continue-on-error" not in step
    assert first["with"]["image-ref"] == "pulseplate:test"
    assert "if" not in first, "the production scan must not be a main-only step"
    for job, name in (
        (build, "Validate production image report and render SARIF"),
        (publish, "Fail when Trivy image SARIF is missing"),
    ):
        validator = _step_by_name(job, name)
        assert validator["if"] == "${{ always() }}"
        assert "--trivy-report" in validator["run"]
        assert "trivy convert --format sarif" in validator["run"]
    assert "github.event_name != 'pull_request'" in publish["if"]
    blocked = (
        "bsdutils",
        "libblkid1",
        "libmount1",
        "libsmartcols1",
        "libuuid1",
        "mount",
        "util-linux",
        "util-linux-extra",
        "libsystemd0",
        "libudev1",
        "libpcre2-8-0",
    )
    for job, name in (
        (build, "Check Docker runtime dependency surface"),
        (publish, "Check Docker publish runtime dependency surface"),
    ):
        run = _step_by_name(job, name)["run"]
        for package in blocked:
            assert f"--blocked-debian-package {package} \\" in run


def test_docker_source_artifact_loader_rejects_stale_review_dates(tmp_path: Path) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(review_by="2026-06-13"),
    )

    with pytest.raises(RuntimeError, match="review_by is stale"):
        docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))


def test_docker_source_artifact_loader_rejects_unsafe_source_metadata(tmp_path: Path) -> None:
    bad_host_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(url="https://example.com/sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="source URL must use https"):
        docker_sources.load_manifest(bad_host_manifest, today=date(2026, 6, 14))

    bad_filename_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(filename="../sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="safe basename"):
        docker_sources.load_manifest(bad_filename_manifest, today=date(2026, 6, 14))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate", "Duplicate"),
        ("version", "identity/version"),
        ("basename", "URL filename"),
        ("query", "overrides"),
        ("credentials", "overrides"),
        ("port", "overrides"),
        ("wrong-owner", "approved host"),
    ],
)
def test_source_manifest_rejects_ambiguous_identity_and_url_overrides(
    tmp_path: Path, mutation: str, message: str
) -> None:
    manifest = _docker_source_manifest()
    rows = manifest["artifacts"]
    row = rows[0]
    if mutation == "duplicate":
        rows.append(dict(row))
    elif mutation == "version":
        row["version"] = "another"
    elif mutation == "basename":
        row["url"] = "https://sqlite.org/2026/different.tar.gz"
    elif mutation == "query":
        row["url"] += "?override=1"
    elif mutation == "credentials":
        row["url"] = row["url"].replace("https://", "https://user@")
    elif mutation == "port":
        row["url"] = row["url"].replace("sqlite.org/", "sqlite.org:443/")
    else:
        row["url"] = row["url"].replace("sqlite.org", "www.kernel.org")
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError, match=message):
        docker_sources.load_manifest(path, today=date(2026, 6, 14))


def _stub_source_transport(
    monkeypatch: pytest.MonkeyPatch,
    *,
    payload: bytes,
    code: int = 200,
    location: str | None = None,
    response_codes: tuple[int, ...] | None = None,
) -> list[tuple[str, int]]:
    """Keep the actual opener/redirect dispatch and replace only HTTP transport."""
    calls: list[tuple[str, int]] = []

    def respond(_handler: object, request: Request) -> addinfourl:
        calls.append((request.full_url, request.timeout))
        headers = Message()
        if location is not None:
            headers["Location"] = location
        status = code
        if response_codes is not None:
            if len(calls) > len(response_codes):
                pytest.fail("source transport exceeded its finite response inventory")
            status = response_codes[len(calls) - 1]
        response = addinfourl(BytesIO(payload), headers, request.full_url, status)
        response.msg = "synthetic source response"
        return response

    monkeypatch.setattr(HTTPSHandler, "https_open", respond)
    monkeypatch.setattr(HTTPHandler, "http_open", respond)
    return calls


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize(
    "location",
    [
        "/2026/another.tar.gz",
        "https://www.sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://www.kernel.org/another.tar.gz",
        "https://unapproved.example/another.tar.gz",
        "http://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "file:///tmp/another.tar.gz",
    ],
)
def test_source_fetch_rejects_real_opener_redirects_without_second_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, location: str
) -> None:
    payload = b"verified source"
    path = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(path, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=payload, code=code, location=location)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)

    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    "url",
    [
        "http://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://unapproved.example/sqlite-autoconf-3530200.tar.gz",
        "https://www.kernel.org/sqlite-autoconf-3530200.tar.gz",
        "https://@sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://sqlite.org:0/2026/sqlite-autoconf-3530200.tar.gz",
        "https://reader@sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz?override=1",
        "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz#override",
    ],
)
def test_source_fetch_revalidates_direct_artifact_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    path = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = replace(docker_sources.load_manifest(path, today=date(2026, 6, 14))[0], url=url)
    calls = _stub_source_transport(monkeypatch, payload=b"unused")

    with pytest.raises(RuntimeError):
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert calls == []


@pytest.mark.parametrize("status", (502, 503, 504))
def test_source_fetch_retries_gateway_error_then_verifies_same_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: int,
) -> None:
    payload = b"verified sqlite source artifact"
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=payload, response_codes=(status, 200))
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    output = docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert output.read_bytes() == payload
    assert output.stat().st_mode & 0o777 == 0o644
    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert capsys.readouterr().err == f"sqlite-autoconf: source HTTP {status} on attempt 1/3\n"


def test_source_fetch_gateway_exhaustion_preserves_first_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(
        monkeypatch, payload=b"untrusted gateway body", response_codes=(502, 503, 504)
    )
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == 502
    assert raised.value.fp.closed
    assert calls == [(artifact.url, 60)] * 3
    assert waits == [1, 2]
    assert list(output.iterdir()) == []
    assert capsys.readouterr().err.splitlines() == [
        "sqlite-autoconf: source HTTP 502 on attempt 1/3",
        "sqlite-autoconf: source HTTP 503 on attempt 2/3",
        "sqlite-autoconf: source HTTP 504 on attempt 3/3",
    ]


@pytest.mark.parametrize("status", (400, 401, 403, 404, 429, 500, 501, 505))
def test_source_fetch_permanent_http_error_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=b"permanent failure", code=status)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == status
    assert calls == [(artifact.url, 60)]
    assert waits == []
    assert list(output.iterdir()) == []


def test_source_fetch_gateway_then_redirect_still_fails_without_following(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected source", location=artifact.url, response_codes=(504, 302)
    )
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == 302
    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert list(output.iterdir()) == []


def test_source_fetch_gateway_then_bad_digest_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_docker_source_manifest(
        tmp_path, _docker_source_manifest(payload=b"verified source")
    )
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=b"bad source", response_codes=(503, 200))
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, output)

    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("code", (504.0, "504", None, True))
def test_source_fetch_malformed_http_status_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: object
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    failure = HTTPError(artifact.url, 504, "synthetic malformed status", Message(), BytesIO())
    setattr(failure, "code", code)
    calls: list[str] = []

    def reject(_handler: object, request: Request) -> addinfourl:
        calls.append(request.full_url)
        raise failure

    monkeypatch.setattr(HTTPSHandler, "https_open", reject)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert raised.value is failure
    assert calls == [artifact.url]
    assert waits == []


@pytest.mark.parametrize(
    "failure",
    (
        SSLCertVerificationError("synthetic TLS verification failure"),
        URLError("synthetic connection failure"),
        TypeError("synthetic malformed response"),
    ),
)
def test_source_fetch_non_http_failure_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls: list[str] = []

    def reject(_handler: object, request: Request) -> addinfourl:
        calls.append(request.full_url)
        raise failure

    monkeypatch.setattr(HTTPSHandler, "https_open", reject)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    with pytest.raises(type(failure)) as raised:
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert raised.value is failure
    assert calls == [artifact.url]
    assert waits == []


def test_docker_source_artifact_fetcher_verifies_sha3_and_reuses_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"verified sqlite source artifact"
    manifest_path = _write_docker_source_manifest(
        tmp_path, _docker_source_manifest(payload=payload)
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]
    output_dir = tmp_path / "docker-sources"
    calls = _stub_source_transport(monkeypatch, payload=payload)
    output_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert output_path == output_dir / "sqlite-autoconf-3530200.tar.gz"
    assert output_path.read_bytes() == payload
    assert output_path.stat().st_mode & 0o777 == 0o644
    assert calls == [("https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz", 60)]

    reused_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert reused_path == output_path
    assert output_path.read_bytes() == payload
    assert calls == [(artifact.url, 60)]


def test_docker_source_artifact_fetcher_rejects_digest_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(payload=b"expected sqlite source artifact"),
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]

    _stub_source_transport(monkeypatch, payload=b"tampered sqlite source artifact")

    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, tmp_path / "docker-sources")

    assert not (tmp_path / "docker-sources" / "sqlite-autoconf-3530200.tar.gz").exists()


@pytest.mark.parametrize("kind", ("symlink", "dangling", "directory", "fifo", "hardlink"))
def test_source_cache_rejects_nonregular_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    payload = b"reviewed source"
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    output = tmp_path / "sources"
    output.mkdir()
    referent = tmp_path / "outside"
    referent.write_bytes(payload)
    referent.chmod(0o600)
    cached = output / artifact.filename
    if kind == "symlink":
        cached.symlink_to(referent)
    elif kind == "dangling":
        cached.symlink_to(tmp_path / "missing")
    elif kind == "directory":
        cached.mkdir()
    elif kind == "hardlink":
        cached.hardlink_to(referent)
    else:
        os.mkfifo(cached)

    def no_network(*args: object, **kwargs: object) -> None:
        pytest.fail("unsafe cache entry must be rejected before network access")

    monkeypatch.setattr(docker_sources, "build_opener", no_network)
    with pytest.raises(RuntimeError, match="regular|symlink"):
        docker_sources._write_verified_artifact(artifact, output)
    assert referent.read_bytes() == payload
    assert referent.stat().st_mode & 0o777 == 0o600


def test_source_cache_rejects_symlinked_output_parent(tmp_path: Path) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlink"):
        docker_sources._write_verified_artifact(artifact, alias / "sources")
    assert list(actual.iterdir()) == []


def test_source_cache_rejects_parent_traversal(tmp_path: Path) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    with pytest.raises(RuntimeError, match="traverse parent"):
        docker_sources._write_verified_artifact(artifact, tmp_path / "nested" / ".." / "sources")
    assert not (tmp_path / "nested").exists()


def test_docker_build_workflows_prefetch_source_artifacts_before_build() -> None:
    """Docker workflows prepare source artifacts explicitly before image build actions."""
    checked_steps: set[tuple[str, str, str]] = set()

    for workflow_name in ("build.yml", "trivy.yml", "cd.yml"):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        for job_name, job, build_step_name in _root_context_docker_build_steps(workflow):
            prepare_step = _step_by_name(job, "Prepare Docker source artifacts")
            prepare_run = prepare_step["run"]
            assert isinstance(prepare_run, str)
            assert "set -euo pipefail" in prepare_run
            assert "python3 scripts/ci/fetch_docker_source_artifacts.py" in prepare_run
            assert _step_index(job, "Prepare Docker source artifacts") < _step_index(
                job,
                build_step_name,
            )
            checked_steps.add((workflow_name, job_name, build_step_name))

    assert EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS <= checked_steps


def test_makefile_docker_build_targets_prefetch_source_artifacts() -> None:
    """Local Docker Make targets prepare source artifacts before Docker builds."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker-source-artifacts: ## Prepare verified Docker source artifacts" in makefile
    assert "$(DEV_PYTHON) scripts/ci/fetch_docker_source_artifacts.py" in makefile
    assert (
        "docker-build: ensure-python-proxy docker-source-artifacts ## Build production Docker image"
        in makefile
    )
    assert (
        "docker-build-dev: ensure-python-proxy docker-source-artifacts ## Build development Docker image"
        in makefile
    )


def test_runtime_base_requires_fixed_bookworm_glibc_line() -> None:
    """Runtime base fails closed if libc stays below the CVE-2025-8058 fix."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert "libc-bin" in runtime_base_section
    assert "libc6" in runtime_base_section
    assert 'dpkg --compare-versions "${version}" ge "2.36-9+deb12u13"' in runtime_base_section
    assert "below fixed glibc line 2.36-9+deb12u13" in runtime_base_section


def test_runtime_base_requires_fixed_bookworm_pcre2_line() -> None:
    """Refresh inherited PCRE2 and reject packages below both Debian CVE fixes."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = dockerfile.split(f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base", 1)[1]
    runtime = runtime.split("COPY --from=builder", 1)[0]
    assert "        libpcre2-8-0 \\" in runtime
    pcre2_guard = runtime.split("&& pcre2_version=", 1)[1].split(
        "&& rm -rf /var/lib/apt/lists/*", 1
    )[0]
    assert (
        'if ! dpkg --compare-versions "${pcre2_version}" ge "10.42-1+deb12u1"; then' in pcre2_guard
    )
    assert "exit 1;" in pcre2_guard
    assert "below fixed PCRE2 line 10.42-1+deb12u1" in runtime


def test_docker_runtime_surface_guard_blocks_perl_runtime_packages() -> None:
    """Docker workflows fail if production keeps Perl runtime packages."""
    for workflow_name, image_ref in (
        ("build.yml", "pulseplate:test"),
        ("trivy.yml", "pulseplate:trivy-scan-${{ github.sha }}"),
    ):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        build_job = jobs["build"]
        assert isinstance(build_job, dict)
        step = _step_by_name(build_job, "Check Docker runtime dependency surface")
        run_script = step["run"]
        assert isinstance(run_script, str)

        assert f"--image {image_ref}" in run_script
        assert "--blocked-debian-package apt" in run_script
        assert "--blocked-debian-package gzip" in run_script
        assert "--blocked-debian-package gpgv" in run_script
        assert "--blocked-debian-package libacl1" in run_script
        assert "--blocked-debian-package libattr1" in run_script
        assert "--blocked-debian-package libgnutls30" in run_script
        assert "--blocked-debian-package libsqlite3-0" in run_script
        assert "--blocked-debian-package libpcre2-8-0" in run_script
        assert "--blocked-debian-package perl-base" in run_script
        assert "--blocked-debian-prefix perl-modules-" in run_script


def test_docker_entrypoint_keeps_bodyfat_hidden_but_routable() -> None:
    """Docker entrypoint serves app.main while preserving bodyfat compatibility."""
    from app.main import app

    client = TestClient(app)
    openapi_response = client.get("/openapi.json")
    assert openapi_response.headers.get("content-type", "").startswith("application/json")
    openapi_paths = openapi_response.json()["paths"]

    assert "/api/v1/bodyfat" not in openapi_paths
    response = client.post(
        "/api/v1/bodyfat",
        json={
            "gender": "male",
            "age": 30,
            "waist_cm": 80.0,
            "neck_cm": 38.0,
            "height_m": 1.75,
            "weight_kg": 75.0,
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert {"labels", "lang", "median", "methods"} <= response.json().keys()


def test_trivy_workflow_is_main_push_image_security_lane() -> None:
    """Trivy scans production images on main pushes, schedule, and manual dispatch."""
    workflow = _load_workflow(WORKFLOWS_DIR / "trivy.yml")
    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    push = on_section["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]
    assert "pull_request" not in on_section
    assert "pull_request_target" not in on_section
    assert "schedule" in on_section
    assert "workflow_dispatch" in on_section

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    scan_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Run Trivy vulnerability scanner"
    )
    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["limit-severities-for-sarif"] is True
    assert scan_step_with["ignore-unfixed"] is True
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert "Fail when Trivy SARIF is missing" in _step_names(build_job)


def test_publish_image_scan_fails_closed() -> None:
    """Publish path image scan blocks HIGH/CRITICAL findings and missing SARIF."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    publish_job = jobs["publish"]
    assert isinstance(publish_job, dict)
    publish_steps = publish_job["steps"]
    assert isinstance(publish_steps, list)
    build_scan_step = _step_by_name(publish_job, "Build Docker image for publish scan")
    image_ref_step = _step_by_name(publish_job, "Set image ref for SBOM and image scan")
    publish_surface_step = _step_by_name(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    scan_step = _step_by_name(
        publish_job,
        "Run Trivy vulnerability scanner (image scan, fail-closed)",
    )
    fail_sarif_step = _step_by_name(publish_job, "Fail when Trivy image SARIF is missing")
    upload_sarif_step = _step_by_name(publish_job, "Upload Trivy image scan results")
    login_step = _step_by_name(publish_job, "Log in to GHCR")
    push_step = _step_by_name(publish_job, "Push scanned Docker image")
    sbom_step = _step_by_name(publish_job, "Generate SBOM")
    provenance_step = _step_by_name(publish_job, "Attest Docker image provenance")
    attestation_step = _step_by_name(publish_job, "Attest Docker image SBOM")

    assert _step_index(publish_job, "Build Docker image for publish scan") < _step_index(
        publish_job, "Set image ref for SBOM and image scan"
    )
    assert _step_index(publish_job, "Set image ref for SBOM and image scan") < _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    assert _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    ) < _step_index(publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)")
    assert _step_index(
        publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)"
    ) < _step_index(publish_job, "Fail when Trivy image SARIF is missing")
    assert _step_index(publish_job, "Fail when Trivy image SARIF is missing") < _step_index(
        publish_job, "Upload Trivy image scan results"
    )
    assert _step_index(publish_job, "Upload Trivy image scan results") < _step_index(
        publish_job, "Log in to GHCR"
    )
    assert _step_index(publish_job, "Log in to GHCR") < _step_index(
        publish_job, "Push scanned Docker image"
    )
    assert _step_index(publish_job, "Push scanned Docker image") < _step_index(
        publish_job, "Generate SBOM"
    )

    build_scan_with = build_scan_step["with"]
    assert isinstance(build_scan_with, dict)
    assert build_scan_step["id"] == "docker-build-scan"
    assert build_scan_with["target"] == "production"
    assert build_scan_with["platforms"] == "linux/amd64"
    assert build_scan_with["push"] is False
    assert build_scan_with["load"] is True
    assert build_scan_with["provenance"] is False
    assert "sbom" not in build_scan_with
    assert build_scan_with["tags"] == "${{ steps.meta.outputs.tags }}"
    assert build_scan_with["labels"] == "${{ steps.meta.outputs.labels }}"
    assert (
        "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt"
        in build_scan_with["build-args"]
    )
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in build_scan_with["secret-envs"]
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in build_scan_with["secret-envs"]

    for step in publish_steps[: _step_index(publish_job, "Fail when Trivy image SARIF is missing")]:
        assert isinstance(step, dict)
        if step.get("uses") == "docker/build-push-action@d08e5c354a6adb9ed34480a06d141179aa583294":
            step_with = step.get("with")
            assert isinstance(step_with, dict)
            assert step_with["push"] is False

    assert "GITHUB_TOKEN" not in build_scan_step.get("env", {})
    assert "GITHUB_TOKEN" not in publish_surface_step.get("env", {})
    assert "GITHUB_TOKEN" not in scan_step.get("env", {})
    assert login_step["uses"].startswith("docker/login-action@")
    assert _step_index(publish_job, "Log in to GHCR") > _step_index(
        publish_job, "Fail when Trivy image SARIF is missing"
    )

    image_ref_run = image_ref_step["run"]
    assert isinstance(image_ref_run, str)
    assert "sha-${{ github.sha }}" in image_ref_run

    publish_surface_run = publish_surface_step["run"]
    assert isinstance(publish_surface_run, str)
    assert "check_docker_runtime_dependency_surface.py" in publish_surface_run
    assert publish_surface_step["env"] == {"IMAGE_REF": "${{ steps.image-ref.outputs.ref }}"}
    assert '--image "${IMAGE_REF}"' in publish_surface_run
    assert "steps.image-ref.outputs.ref" not in publish_surface_run
    assert "--blocked-debian-package gzip" in publish_surface_run
    for package in (
        "apt",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "perl-base",
    ):
        assert f"--blocked-debian-package {package}" in publish_surface_run
    assert "--blocked-debian-prefix perl-modules-" in publish_surface_run
    assert "docker-publish-runtime-dependency-surface.json" in publish_surface_run

    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["image-ref"] == "${{ steps.image-ref.outputs.ref }}"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["format"] == "json"
    assert scan_step_with["output"] == "trivy-image.json"
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert fail_sarif_step["if"] == "${{ always() }}"

    assert upload_sarif_step["if"] == "${{ always() && hashFiles('trivy-image.sarif') != '' }}"
    assert push_step["id"] == "docker-build-push"
    push_run = push_step["run"]
    assert isinstance(push_run, str)
    assert "docker image push" in push_run
    assert "steps.meta.outputs.tags" in push_run
    assert "steps.image-ref.outputs.ref" in push_run
    assert "grep -F -m1" in push_run
    assert "GITHUB_OUTPUT" in push_run
    assert "digest=${digest}" in push_run

    assert sbom_step["with"]["image"] == "${{ steps.image-ref.outputs.ref }}"
    assert (
        provenance_step["with"]["subject-digest"] == "${{ steps.docker-build-push.outputs.digest }}"
    )
    assert (
        attestation_step["with"]["subject-digest"]
        == "${{ steps.docker-build-push.outputs.digest }}"
    )


@pytest.mark.parametrize(
    "name,version,url,digest",
    [
        (
            "pcre2",
            "10.49",
            "https://codeload.github.com/PCRE2Project/pcre2/legacy.tar.gz/refs/tags/pcre2-10.49",
            "6510970e92ea9410b44f85c606c389c3473ba05d2d6338f0ce763cc4ccaa382c",
        ),
        (
            "sljit",
            "de0259c7aaf36aa40cba8014f3fad3edde9307f9",
            "https://codeload.github.com/zherczeg/sljit/legacy.tar.gz/"
            "de0259c7aaf36aa40cba8014f3fad3edde9307f9",
            "7ad006814d4d9c698832b14541634b9cc12039bae7b3bb547909fda51ee11a80",
        ),
    ],
)
def test_pcre2_source_records_bind_exact_reviewed_closure(
    name: str, version: str, url: str, digest: str
) -> None:
    artifacts = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
    )
    assert len(artifacts) == 15
    matches = [artifact for artifact in artifacts if artifact.name == name]
    assert len(matches) == 1
    artifact = matches[0]
    assert (artifact.version, artifact.filename, artifact.url, artifact.sha3_256) == (
        version,
        f"{name}-{version}.tar.gz",
        url,
        digest,
    )


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize(
    "mutation",
    [
        "repo",
        "ref",
        "path",
        "version",
        "filename",
        "digest",
        "cross_pair",
        "http",
        "credentials",
        "empty_userinfo",
        "port",
        "query",
        "fragment",
        "unknown_name",
        "malformed_version",
        "malformed_digest",
    ],
)
def test_pcre2_source_manifest_rejects_identity_and_metadata_cross_pairs(
    tmp_path: Path, name: str, mutation: str
) -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    row = next(record for record in manifest["artifacts"] if record["name"] == name)
    if mutation == "repo":
        row["url"] = row["url"].replace("/legacy.tar.gz/", "-other/legacy.tar.gz/")
    elif mutation == "ref":
        row["url"] += "-other"
    elif mutation == "path":
        row["url"] = row["url"].replace("/legacy.tar.gz/", "/tar.gz/")
    elif mutation == "version":
        row["version"] += "-other"
        row["filename"] = f"{name}-{row['version']}.tar.gz"
    elif mutation == "filename":
        row["filename"] = "different.tar.gz"
    elif mutation == "digest":
        row["sha3_256_parts"] = ["0" * 64]
    elif mutation == "cross_pair":
        other = next(
            record
            for record in manifest["artifacts"]
            if record["name"] != name and record["name"] in ("pcre2", "sljit")
        )
        row["url"] = other["url"]
        row["sha3_256_parts"] = other["sha3_256_parts"]
    elif mutation == "http":
        row["url"] = row["url"].replace("https:", "http:")
    elif mutation == "credentials":
        row["url"] = row["url"].replace("https://", "https://reader@")
    elif mutation == "empty_userinfo":
        row["url"] = row["url"].replace("https://", "https://@")
    elif mutation == "port":
        row["url"] = row["url"].replace("github.com/", "github.com:443/")
    elif mutation == "query":
        row["url"] += "?override=1"
    elif mutation == "fragment":
        row["url"] += "#override"
    elif mutation == "unknown_name":
        row["name"] = "other"
        row["filename"] = f"other-{row['version']}.tar.gz"
    elif mutation == "malformed_version":
        row["version"] = 10
    else:
        row["sha3_256_parts"] = [None]
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError):
        docker_sources.load_manifest(path, today=date(2026, 10, 2))


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_pcre2_source_redirects_use_real_rejecting_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, code: int
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected source", code=code, location=artifact.url
    )
    output = tmp_path / "sources"
    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize("field", ["url", "version", "filename", "sha3_256"])
def test_pcre2_direct_source_revalidates_identity_before_cache_or_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, field: str
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    corrupted = replace(artifact, **{field: getattr(artifact, field) + "other"})
    calls = _stub_source_transport(monkeypatch, payload=b"unused")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="exact reviewed identity"):
        docker_sources._write_verified_artifact(corrupted, output)
    assert calls == []
    assert not output.exists()


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
def test_pcre2_source_download_rejects_wrong_actual_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    calls = _stub_source_transport(monkeypatch, payload=b"wrong actual source bytes")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="SHA3"):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


def test_pcre2_production_build_preserves_native_features_and_consumers() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    dockerignore = (REPO_ROOT / ".dockerignore").read_text()
    builder = dockerfile.split("FROM sqlite-builder AS pcre2-builder", 1)[1].split(
        "# Stage 2: Runtime base stage", 1
    )[0]
    for filename in ("pcre2-10.49.tar.gz", "sljit-de0259c7aaf36aa40cba8014f3fad3edde9307f9.tar.gz"):
        assert f"COPY build/docker-sources/{filename}" in builder
        assert f"!build/docker-sources/{filename}" in dockerignore
    assert 'sha3_256(payload).hexdigest() != "".join(records[0]["sha3_256_parts"])' in builder
    assert "RUN --network=none" in builder
    assert "--strip-components=1 -C /tmp/pcre2-source/deps/sljit" in builder
    for flag in (
        "--enable-shared",
        "--disable-static",
        "--enable-jit",
        "--enable-unicode",
        "--enable-pcre2-8",
        "--disable-pcre2-16",
        "--disable-pcre2-32",
        "--disable-pcre2grep-libz",
        "--disable-pcre2grep-libbz2",
        "--disable-pcre2test-libreadline",
    ):
        assert flag in builder
    assert "make -j2 libpcre2-8.la" in builder
    for source in ("LICENCE.md", "COPYING", "deps/sljit/LICENSE"):
        assert f"install -m 0644 {source}" in builder
    production = dockerfile.split("FROM runtime-base AS production", 1)[1].split(
        "FROM runtime-base AS development", 1
    )[0]
    replacement = production.index("COPY --from=pcre2-builder")
    pruning = production.index("# SECURITY: production-package-pruning-start")
    nonroot = production.index("USER pulseplate")
    smoke = production.index("# Exercise the actual replacement")
    assert replacement < pruning < nonroot < smoke
    assert "ln -s libpcre2-8.so.0.16.1 /usr/local/lib/libpcre2-8.so.0 && ldconfig" in production
    assert "        libpcre2-8-0 \\" in production
    assert "sha256sum --check /usr/local/share/doc/pulseplate-pcre2/SHA256SUMS" in production
    for native_call in (
        "pcre2_config_8",
        "pcre2_compile_8",
        "pcre2_jit_compile_8",
        "pcre2_jit_match_8",
        "pcre2_jit_stack_assign_8",
        "selabel_open",
        "selabel_lookup_raw",
        "freecon",
        "selabel_close",
    ):
        assert native_call in production[smoke:]
    assert 'version.value.startswith(b"10.49 ")' in production[smoke:]
    assert "if loaded != {expected}:" in production[smoke:]
    assert "finally:" in production[smoke:]
    assert "grep -P" in production[smoke:]
    assert "dpkg --version" in production[smoke:]
    assert 'mkdir "${consumer_directory}/child"' in production[smoke:]


@pytest.mark.parametrize(
    "today,expected_exit,forecast_finding",
    [
        (date(2026, 10, 6), 0, False),
        (date(2026, 10, 8), 0, False),
        (date(2026, 10, 17), 0, False),
        (date(2026, 10, 18), 1, True),
    ],
)
def test_candidate_nightly_forecast_preserves_current_and_plus_four(
    tmp_path: Path, today: date, expected_exit: int, forecast_finding: bool
) -> None:
    result, summary = _run_forecast_workflow(tmp_path, today=today, review_by="2026-10-21")
    assert result.returncode == expected_exit, result.stderr
    assert (
        f"UTC today: {today}; UTC forecast date: {date.fromordinal(today.toordinal() + 4)}"
        in summary
    )
    assert "### CURRENT: no finding" in summary
    assert f"### FORECAST: {'attention required' if forecast_finding else 'no finding'}" in summary
    if forecast_finding:
        assert (
            "Docker sources: Docker source artifact manifest review_by is stale: 2026-10-21"
            in summary
        )
        assert "Expired Trivy ignore policy" not in summary
    assert "Trivy policy:" not in summary


def test_native_client_omits_unused_gss_closure_and_separates_pg_build() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    native = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
    assert "libkrb5-dev" not in dockerfile and "libgssapi-krb5-2 \\\n" not in dockerfile
    assert "--without-gssapi --without-ldap" in native and "--with-gssapi" not in native
    split = "ldconfig\nSH\n\n# PostgreSQL client flags have a separate cache boundary from Z/N/OpenSSL.\nRUN --network=none <<'SH'\nset -eu\ncd /build/source/postgresql-18.6"
    assert split in native
    prefix, client = native.split(split, 1)
    assert "cd /build/source/zlib-1.3.2" in prefix
    assert "--with-versioned-syms" in prefix and "make -j2 build_sw" in prefix
    assert "make -j2 -C src/interfaces/libpq all" in client
    for package in ("libgssapi-krb5-2", "libk5crypto3", "libkrb5-3", "libkrb5support0"):
        assert package in dockerfile.split("retired = ", 1)[1].split("\nfor row", 1)[0]
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    assert "gssencmode=require" in source and "not compiled in" in source
    assert (
        "gss_probe.finish()" in source and "Unused Kerberos native runtime remains loaded" in source
    )


@pytest.mark.parametrize(
    "status,error_message,expected_exit",
    (
        (1, b'gssencmode value "require" invalid when GSSAPI support is not compiled in', 0),
        (1, b"GSSAPI encryption required but no credential cache", 1),
        (0, b"not compiled in", 1),
        (0, b"GSSAPI enabled", 1),
    ),
)
def test_shipped_libpq_gss_feature_probe_rejects_enabled_client_and_always_finishes(
    tmp_path: Path, status: int, error_message: bytes, expected_exit: int
) -> None:
    """Execute the exact shipped public API probe, including cleanup on rejection."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_probe" for target in node.targets
            )
        )
        or (
            isinstance(node, ast.Try)
            and "Unused libpq GSSAPI feature remains enabled" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    program = f"""import atexit, json, types
observed = {{"finish_calls": 0, "connect_arguments": []}}
class SyntheticConnection:
    status = {status!r}
    error_message = {error_message!r}
    def finish(self):
        observed["finish_calls"] += 1
def connect_start(conninfo):
    observed["connect_arguments"].append(conninfo.decode("ascii"))
    return SyntheticConnection()
pq = types.SimpleNamespace(PGconn=types.SimpleNamespace(connect_start=connect_start))
psycopg = types.SimpleNamespace(pq=types.SimpleNamespace(ConnStatus=types.SimpleNamespace(BAD=1)))
atexit.register(lambda: print(json.dumps(observed)))
""" + "\n".join(ast.unparse(node) for node in statements)
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
    assert json.loads(result.stdout) == {
        "finish_calls": 1,
        "connect_arguments": ["host=/tmp gssencmode=require"],
    }
    if expected_exit:
        assert "Unused libpq GSSAPI feature remains enabled" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "library,expected_exit",
    (
        ("libpq.so.5.18", 0),
        ("libkrb5support-helper.so.1", 0),
        ("libgssapi_krb5.so.2.2", 1),
        ("libk5crypto.so.3.1", 1),
        ("libkrb5.so.3.3", 1),
        ("libkrb5support.so.0.1", 1),
    ),
)
def test_shipped_loaded_native_guard_rejects_each_unused_gss_family(
    tmp_path: Path, library: str, expected_exit: int
) -> None:
    """Real fixture map data exercises the shipped family guard without host maps."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_families"
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.If)
            and "Unused Kerberos native runtime remains loaded" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    fixture = tmp_path / "synthetic-maps.txt"
    fixture.write_text(f"1000-2000 r--p 00000000 00:00 0 /usr/local/lib/{library}\n")
    program = "from pathlib import Path\n" + "\n".join(ast.unparse(node) for node in statements)
    program = program.replace("'/proc/self/maps'", repr(str(fixture)))
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
    if expected_exit:
        assert "Unused Kerberos native runtime remains loaded" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "scenario,library,expected_message",
    (
        ("empty", "unrelated.so.1", None),
        ("present", "libgssapi_krb5.so.2.2", "Unused Kerberos library remains"),
        ("present", "libk5crypto.so.3.1", "Unused Kerberos library remains"),
        ("present", "libkrb5.so.3.3", "Unused Kerberos library remains"),
        ("present", "libkrb5support.so.0.1", "Unused Kerberos library remains"),
        ("missing_directory", "unrelated.so.1", "FileNotFoundError"),
        ("non_directory", "unrelated.so.1", "NotADirectoryError"),
    ),
)
def test_shipped_physical_gss_guard_rejects_files_and_required_directory_errors(
    tmp_path: Path, scenario: str, library: str, expected_message: str | None
) -> None:
    """Real scandir input cannot turn an unavailable mandatory directory into absence."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_families"
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.For)
            and "Unused Kerberos library remains in a required native directory"
            in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    native = tmp_path / "native-library-directory"
    system = tmp_path / "system-library-directory"
    native.mkdir()
    if scenario == "non_directory":
        system.write_text("synthetic non-directory")
    elif scenario != "missing_directory":
        system.mkdir()
        (system / library).write_bytes(b"synthetic physical native bytes")
    program = "import os\n" + "\n".join(ast.unparse(node) for node in statements)
    program = program.replace("'/usr/local/lib'", repr(str(native)))
    program = program.replace("'/usr/lib/x86_64-linux-gnu'", repr(str(system)))
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == (1 if expected_message else 0), result.stdout + result.stderr
    if expected_message:
        assert expected_message in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "inventory,expected_message",
    (
        (["ii libgssapi-krb5-2"], "An original native package remains installed"),
        (["ii libk5crypto3"], "An original native package remains installed"),
        (["ii libkrb5-3:amd64"], "An original native package remains installed"),
        (["ii libkrb5support0"], "An original native package remains installed"),
        (["rc libkrb5-3", "ii libkrb5-helper"], None),
        ([""], "Package inventory is malformed after native replacement"),
        (["ii"], "Package inventory is malformed after native replacement"),
        (["ii libkrb5-3 extra"], "Package inventory is malformed after native replacement"),
    ),
)
def test_existing_package_guard_rejects_kerberos_and_preserves_typed_inventory_errors(
    tmp_path: Path, inventory: list[str], expected_message: str | None
) -> None:
    """Execute the existing retirement loop, preserving exact package membership."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split('retired = {"zlib1g"', 1)[1].split("\nssl_root", 1)[0]
    source = 'retired = {"zlib1g"' + source
    program = f"rows = {inventory!r}\n" + source
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == (1 if expected_message else 0), result.stdout + result.stderr
    if expected_message:
        assert expected_message in result.stderr
    else:
        assert not result.stderr


_ZLIB_MAINTENANCE_PATCHES = (
    (
        "zlib-gzwrite-null-fix",
        ("e3dc0a85" "b7032e98" "380dec01" "1bc8f2c2" "ee0d8fca"),
        ("63adc22e" "cebf8bbe" "e7b9aaf4" "f0587657" "68948996" "ca4b26fa" "260d8b80" "6a64e7d3"),
        ("183bc8b9" "dd078a41" "a62de5c2" "d905d9b0" "196b45bc" "46f100d7" "e4147ec2" "28207c74"),
    ),
    (
        "zlib-gzvprintf-return-fix",
        ("bbc2ccf3" "d0de2675" "76b524b8" "75c769a7" "24a513b0"),
        ("55b2edac" "2662134a" "37863f6d" "1e11fb97" "d6e63e03" "5d8d0d3d" "70ec6d8a" "3b669734"),
        ("7d00ee29" "be5e636d" "30da2890" "961e83e3" "5cee0b15" "2333ecd9" "7a46ae2e" "71eb5d47"),
    ),
    (
        "zlib-gzprintf-return-fix",
        ("7235b0a5" "81227c56" "a79a43ff" "828f8ef6" "794194c8"),
        ("274bce56" "61e7c7cc" "9c47e21f" "100c7078" "7cad6d8c" "0c04104a" "ff8d8d84" "baced7a7"),
        ("96040ee8" "4d0d1879" "05283912" "dbd3f7b6" "6ac20339" "76a2ceef" "e9b8cca6" "3143d9c2"),
    ),
    (
        "zlib-blocked-errno-fix",
        ("813dac5d" "cb5902ed" "241e9b0d" "38abd2d8" "47a335a9"),
        ("438d0e57" "75f15081" "a3339eed" "38d4b207" "b100f5cf" "4f68db0e" "619ef9b3" "054e3e4a"),
        ("6475806c" "db638378" "8a03e7af" "5617188e" "f2692803" "889cded1" "fcb01482" "5923d16c"),
    ),
    (
        "zlib-gzprintf-contract-fix",
        ("d81c2d7e" "b705c622" "94ba0329" "92556720" "78e89115"),
        ("adf2578c" "eaa4d9a5" "2ccfa8d7" "4f8b8792" "cce3084f" "9f770944" "39450eec" "2a7a214c"),
        ("a786b2b0" "84126860" "08c7fe12" "47e90701" "cebde564" "037806bd" "9935f849" "07737cc4"),
    ),
    (
        "zlib-errno-order-fix",
        ("a82e0db3" "92178a3e" "05fb27bf" "551a6ce7" "57a47898"),
        ("70b0fb7e" "333c5757" "807407f1" "d88ef2ff" "71f757b5" "59926b73" "22a1a8d7" "84811cbc"),
        ("6d02eb6c" "5403c491" "9076cc89" "ae6609ac" "421aa27d" "e116457a" "ca1554c3" "85296a2b"),
    ),
)


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
def test_zlib_maintenance_manifest_keeps_exact_official_patch_identities(
    name: str, commit: str, sha3: str, sha2: str
) -> None:
    artifacts = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 9)
    )
    matches = [artifact for artifact in artifacts if artifact.name == name]
    assert len(matches) == 1
    artifact = matches[0]
    assert (
        artifact.version,
        artifact.url,
        artifact.filename,
        artifact.sha3_256,
        artifact.sha256,
    ) == (
        commit,
        f"https://github.com/madler/zlib/commit/{commit}.patch",
        f"{name}-{commit}.patch",
        sha3,
        sha2,
    )


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
@pytest.mark.parametrize("field", ["version", "url", "filename", "sha3_256", "sha256"])
def test_zlib_maintenance_identity_drift_rejected_before_cache_or_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    commit: str,
    sha3: str,
    sha2: str,
    field: str,
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch",
        sha3_256=sha3,
        sha256=sha2,
    )
    value = getattr(artifact, field)
    assert isinstance(value, str)
    corrupted = replace(artifact, **{field: value + "other"})
    calls = _stub_source_transport(monkeypatch, payload=b"unused")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="reviewed identity"):
        docker_sources._write_verified_artifact(corrupted, output)
    assert calls == []
    assert not output.exists()


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_zlib_maintenance_redirects_use_real_rejecting_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    commit: str,
    sha3: str,
    sha2: str,
    code: int,
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch",
        sha3_256=sha3,
        sha256=sha2,
    )
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected patch", code=code, location=artifact.url
    )
    output = tmp_path / "sources"
    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
def test_zlib_maintenance_payload_rejects_wrong_actual_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, commit: str, sha3: str, sha2: str
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch",
        sha3_256=sha3,
        sha256=sha2,
    )
    calls = _stub_source_transport(monkeypatch, payload=b"different actual patch bytes")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


def test_zlib_maintenance_docker_recipe_binds_exact_order_and_source_fingerprints() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    native = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
    prefix = native.split("./configure --prefix=/usr/local --libdir=/usr/local/lib --shared", 1)[0]
    commits = [record[1] for record in _ZLIB_MAINTENANCE_PATCHES]
    names = [record[0] for record in _ZLIB_MAINTENANCE_PATCHES]
    names.insert(2, "zlib-gzwrite-fix")
    commits.insert(2, ("df84af25" "dc194249" "0e1d1c89" "9a076191" "52a46148"))
    expected = [
        f"patch --batch --forward --fuzz=0 --no-backup-if-mismatch -p1 --input /input/native/{name}-{commit}.patch"
        for name, commit in zip(names, commits)
    ]
    assert [line for line in prefix.splitlines() if line.startswith("patch ")] == expected
    dockerignore = (REPO_ROOT / ".dockerignore").read_text()
    for name, commit in zip(names, commits):
        filename = f"{name}-{commit}.patch"
        assert f"build/docker-sources/{filename}" in prefix
        assert f"!build/docker-sources/{filename}" in dockerignore
    assert "set(before) != set(after)" in prefix
    assert "len(before) != 254" in prefix
    assert "!= set(expected)" in prefix
    for name, digest in (
        (
            "gzguts.h",
            (
                "6c366344"
                "bc1f1e25"
                "3892a33e"
                "06a01e97"
                "005c9340"
                "f9a44f93"
                "1e6cec8c"
                "b9878ffc"
            ),
        ),
        (
            "gzread.c",
            (
                "22178dd5"
                "092c89bc"
                "46e0a3eb"
                "bcd808f0"
                "3e8aafa3"
                "15c2a452"
                "4a6a0a2f"
                "f7c65038"
            ),
        ),
        (
            "gzwrite.c",
            (
                "548eb543"
                "23313b70"
                "b74a5564"
                "a61ccd4b"
                "968200ef"
                "89cbb70a"
                "6152d50b"
                "373515c5"
            ),
        ),
        (
            "zlib.h",
            (
                "648069fd"
                "ae548705"
                "c3a1c02d"
                "ac97a1dd"
                "7794e9e0"
                "bd32b46f"
                "b2afb357"
                "164b8037"
            ),
        ),
    ):
        assert name in prefix
        assert all(part in prefix for part in [digest[i : i + 8] for i in range(0, 64, 8)])


@pytest.mark.parametrize("bad_name", [[], {}])
def test_zlib_maintenance_manifest_refuses_unhashable_names(
    tmp_path: Path, bad_name: object
) -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    row = next(
        record for record in manifest["artifacts"] if record["name"] == "zlib-gzwrite-null-fix"
    )
    row["name"] = bad_name
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError, match="Only exact reviewed zlib patches"):
        docker_sources.load_manifest(path, today=date(2026, 10, 9))


def test_prometheus_metadata_mode_is_explicit_and_independent() -> None:
    """The qualifier cannot select or publish a Prometheus runtime."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    events = workflow.get("on", workflow.get(True))
    assert events["workflow_dispatch"]["inputs"]["mode"]["options"] == [
        "disabled",
        "normal",
        "prometheus-source-qualify",
        "backend-sdk-qualify",
        "prometheus-oras-qualify",
        "prometheus-source-pair",
    ]
    assert events["workflow_dispatch"]["inputs"]["prometheus_module_action"] == {
        "description": "Explicit Prometheus metadata module action; unchanged retains original locks",
        "type": "choice",
        "required": True,
        "default": "unchanged",
        "options": ["unchanged", "xnet060-replay"],
    }
    jobs = workflow["jobs"]
    qualification = jobs["prometheus-source-qualification"]
    assert "needs" not in qualification
    assert qualification["permissions"] == {"contents": "read"}
    assert qualification["timeout-minutes"] == (
        "${{ fromJSON(vars.PROMETHEUS_SOURCE_QUALIFICATION_TIMEOUT_MINUTES || '20') }}"
    )
    assert qualification["if"] == (
        "github.event_name == 'workflow_dispatch' && "
        "inputs.mode == 'prometheus-source-qualify' && "
        "github.repository == 'Katsiarynakavaleuskaya/PulsePlate'"
    )
    assert jobs["build"]["if"] == (
        "github.event_name != 'workflow_dispatch' || inputs.mode == 'normal'"
    )
    assert jobs["publish"]["needs"] == ["build", "security-scan"]
    command = _step_by_name(qualification, "Qualify Prometheus package metadata only")["run"]
    assert "-m scripts.ci.prometheus_source_image" in command
    assert "$PROMETHEUS_QUALIFICATION_SECONDS" in command
    assert "$PROMETHEUS_CLEANUP_SECONDS" in command
    step = _step_by_name(qualification, "Qualify Prometheus package metadata only")
    assert step["env"] == {"PROMETHEUS_MODULE_ACTION": "${{ inputs.prometheus_module_action }}"}
    assert 'case "$PROMETHEUS_MODULE_ACTION" in' in command
    assert "xnet060-replay) module_args+=(--derive-xnet060)" in command
    assert '"${module_args[@]}"' in command
    assert "${{ inputs.prometheus_module_action }}" not in command
    assert "buildx" not in command and "secrets." not in command
    assert not any("secrets." in str(step) for step in qualification["steps"])
    checkout = _step_by_name(qualification, "Checkout qualification source")
    assert checkout["with"]["persist-credentials"] is False


def test_prometheus_publisher_verifies_retained_original_signed_bundles() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    pair = jobs["prometheus-source-build-pair"]
    attestations = [
        step for step in pair["steps"] if step.get("uses", "").startswith("actions/attest@")
    ]
    assert len(attestations) == 2
    for step in attestations:
        assert step["with"]["push-to-registry"] is False
        assert step["with"]["create-storage-record"] is False
    publisher = jobs["prometheus-publish"]
    assert [step["name"] for step in publisher["steps"]] == [
        "Checkout exact main producer",
        "Promote precise retained bytes and pull them back",
        "Retain main publication and pullback",
    ]
    promote = _step_by_name(publisher, "Promote precise retained bytes and pull them back")
    assert promote["id"] == "published"
    assert promote["env"] == {
        "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
    }
    assert "--operation promote" in promote["run"]
    assert '--cleanup-seconds "$PROMETHEUS_CLEANUP_SECONDS"' in promote["run"]
    assert "DOCKER_CONFIG" not in str(publisher)
    assert not any(
        step.get("uses", "").startswith("docker/login-action@") for step in publisher["steps"]
    )
