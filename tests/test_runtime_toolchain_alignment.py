"""Guards for local runtime and CI toolchain version alignment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.runtime_toolchain_versions import (
    CANONICAL_PYTHON,
    CANONICAL_RUBY,
    EXCON_MINIMUM_VERSION,
    FASTLANE_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SETUP_USES = ("actions/setup-python@", "./.github/actions/python-setup")
AUXILIARY_PY313_WORKFLOWS = (
    ".github/workflows/build-equivalence-evidence.yml",
    ".github/workflows/ci-metrics.yml",
    ".github/workflows/experiment-runner-dispatch.yml",
    ".github/workflows/experiment-runner-slack-socket-smoke.yml",
    ".github/workflows/nightly.yml",
    ".github/workflows/release-control-plane-evidence.yml",
    ".github/workflows/release-manifest-evidence.yml",
)


def _load_workflow(path: str) -> dict[str, Any]:
    workflow = yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _iter_python_setup_steps(path: str) -> list[tuple[str, dict[str, Any]]]:
    workflow = _load_workflow(path)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    setup_steps: list[tuple[str, dict[str, Any]]] = []
    for job_name, job in jobs.items():
        assert isinstance(job_name, str)
        assert isinstance(job, dict)
        steps = job.get("steps", [])
        assert isinstance(steps, list)
        for step in steps:
            assert isinstance(step, dict)
            uses = str(step.get("uses", ""))
            if any(uses.startswith(prefix) for prefix in PYTHON_SETUP_USES):
                setup_steps.append((job_name, step))
    return setup_steps


def _python_version_input(step: dict[str, Any]) -> str:
    with_block = step.get("with", {})
    assert isinstance(with_block, dict)
    version = with_block.get("python-version")
    assert isinstance(version, str)
    return version


def _tool_versions() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (REPO_ROOT / ".tool-versions").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tool, version, *_rest = stripped.split()
        entries[tool] = version
    return entries


def test_local_python_and_ruby_version_sources_are_canonical() -> None:
    assert (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip() == (CANONICAL_PYTHON)
    tool_versions = _tool_versions()
    assert tool_versions["python"] == CANONICAL_PYTHON
    assert tool_versions["ruby"] == CANONICAL_RUBY
    assert (REPO_ROOT / ".ruby-version").read_text(encoding="utf-8").strip() == CANONICAL_RUBY


def test_canonical_ci_uses_patch_pin_without_renaming_visible_labels() -> None:
    workflow = _load_workflow(".github/workflows/ci.yml")
    assert workflow["env"]["PYTHON_VERSION"] == CANONICAL_PYTHON
    jobs = workflow["jobs"]

    test_pr_matrix = jobs["test-pr"]["strategy"]["matrix"]["python-version"]
    test_feature_matrix = jobs["test-feature"]["strategy"]["matrix"]["python-version"]
    assert test_pr_matrix == ["3.13"]
    assert test_feature_matrix == ["3.13"]

    test_main_include = jobs["test-main"]["strategy"]["matrix"]["include"]
    assert [entry["python-version"] for entry in test_main_include] == ["3.11", "3.12", "3.13"]
    assert [entry["timeout-minutes"] for entry in test_main_include] == [60, 90, 90]

    setup_steps = dict(_iter_python_setup_steps(".github/workflows/ci.yml"))
    assert _python_version_input(setup_steps["test-pr"]) == "${{ env.PYTHON_VERSION }}"
    assert _python_version_input(setup_steps["test-feature"]) == "${{ env.PYTHON_VERSION }}"
    assert _python_version_input(setup_steps["test-main"]) == (
        "${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || matrix.python-version }}"
    )


def test_frontend_ci_keeps_shared_python_patch_source() -> None:
    workflow = _load_workflow(".github/workflows/frontend-ci.yml")
    assert workflow["env"]["PYTHON_VERSION"] == CANONICAL_PYTHON

    setup_steps = dict(_iter_python_setup_steps(".github/workflows/frontend-ci.yml"))
    assert _python_version_input(setup_steps["build-and-test"]) == "${{ env.PYTHON_VERSION }}"


def test_auxiliary_workflow_python_setup_pins_use_exact_patch_version() -> None:
    for path in AUXILIARY_PY313_WORKFLOWS:
        setup_steps = _iter_python_setup_steps(path)
        assert setup_steps, f"Missing Python setup step in {path}"
        for job_name, step in setup_steps:
            assert _python_version_input(step) == CANONICAL_PYTHON, f"{path}:{job_name}"


def test_no_python_setup_step_uses_bare_py313_runtime_pin() -> None:
    offenders: list[str] = []
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_paths = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in workflow_dir.glob(pattern)
    )
    for path in workflow_paths:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for job_name, step in _iter_python_setup_steps(rel_path):
            if _python_version_input(step) == "3.13":
                offenders.append(f"{rel_path}:{job_name}")

    assert offenders == []


def test_fastlane_and_ruby_tooling_are_pinned_consistently() -> None:
    gemfile = (REPO_ROOT / "ios" / "Gemfile").read_text(encoding="utf-8")
    lockfile = (REPO_ROOT / "ios" / "Gemfile.lock").read_text(encoding="utf-8")

    assert f'gem "fastlane", "= {FASTLANE_VERSION}"' in gemfile
    assert f"    fastlane ({FASTLANE_VERSION})" in lockfile
    assert f"  fastlane (= {FASTLANE_VERSION})" in lockfile
    assert "fastlane (~>" not in gemfile
    assert "fastlane (~>" not in lockfile

    excon_line = next(
        line.strip() for line in lockfile.splitlines() if line.startswith("    excon (")
    )
    locked_excon = excon_line.removeprefix("excon (").removesuffix(")")
    assert tuple(map(int, locked_excon.split("."))) >= tuple(
        map(int, EXCON_MINIMUM_VERSION.split("."))
    )
    assert "      excon (>= 0.71.0, < 2.0.0)" in lockfile
