"""Guards for local runtime and CI toolchain version alignment."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.check_jwt_fastlane_unblock import _version_at_least
from tests.runtime_toolchain_versions import (
    CANONICAL_PYTHON,
    CANONICAL_RUBY,
    EXCON_MINIMUM_VERSION,
    FASTLANE_VERSION,
    RUBY_SETUP_ACTION,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_PYTHON_SETUP_USE = "actions/setup-python@"
LOCAL_PYTHON_SETUP_USE = "./.github/actions/python-setup"
PYTHON_VERSION_FROM_ENV = "${{ env.PYTHON_VERSION }}"
PYTHON_VERSION_FROM_MATRIX = (
    "${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || matrix.python-version }}"
)
EXPECTED_CANONICAL_CI_PYTHON_SETUP_OWNERS = (
    ("pygments_exception_guard", PYTHON_VERSION_FROM_ENV),
    ("docs_phase1_gates", PYTHON_VERSION_FROM_ENV),
    ("pr_body_phase2_gates", PYTHON_VERSION_FROM_ENV),
    ("merge_readiness_gate", PYTHON_VERSION_FROM_ENV),
    ("private_python_proxy_health", PYTHON_VERSION_FROM_ENV),
    ("lint", PYTHON_VERSION_FROM_ENV),
    ("security", PYTHON_VERSION_FROM_ENV),
    ("openapi-sync", PYTHON_VERSION_FROM_ENV),
    ("test-pr", PYTHON_VERSION_FROM_ENV),
    ("pgvector_compat", CANONICAL_PYTHON),
    ("test-feature", PYTHON_VERSION_FROM_ENV),
    ("test-main", PYTHON_VERSION_FROM_MATRIX),
    ("diff-coverage", PYTHON_VERSION_FROM_ENV),
)
EXPECTED_FRONTEND_CI_PYTHON_SETUP_OWNERS = (("build-and-test", PYTHON_VERSION_FROM_ENV),)
SEPARATELY_GOVERNED_PYTHON_SETUP_WORKFLOWS = frozenset(
    {
        ".github/workflows/ci.yml",
        ".github/workflows/codecov-upload.yml",
        ".github/workflows/frontend-ci.yml",
    }
)
EXPECTED_AUXILIARY_PYTHON_SETUP_OWNERS = (
    (".github/workflows/build-equivalence-evidence.yml", "publish-build-equivalence-evidence"),
    (".github/workflows/ci-metrics.yml", "collect-ci-metrics"),
    (".github/workflows/experiment-runner-dispatch.yml", "experiment-runner-dispatch-contract"),
    (".github/workflows/experiment-runner-slack-socket-smoke.yml", "slack-socket-bridge-smoke"),
    # nightly-tests has two setup steps in one job; keep both owners for strict multiplicity.
    (".github/workflows/nightly-tests.yml", "tests"),
    (".github/workflows/nightly-tests.yml", "tests"),
    (".github/workflows/nightly.yml", "coverage-merge"),
    (".github/workflows/nightly.yml", "integration-test"),
    (".github/workflows/nightly.yml", "performance-test"),
    (".github/workflows/nightly.yml", "test"),
    (".github/workflows/rag-release-gates.yml", "rag-release-gates-smoke"),
    (".github/workflows/rag-release-gates.yml", "rag-release-gates-weekly"),
    (
        ".github/workflows/release-control-plane-evidence.yml",
        "publish-release-control-plane-evidence",
    ),
    (".github/workflows/release-manifest-evidence.yml", "publish-release-manifest-evidence"),
    (".github/workflows/security.yml", "bandit"),
)
EXPECTED_RUBY_SETUP_OWNERS = (
    (".github/workflows/ci.yml", "jwt_fastlane_unblock_guard"),
    (".github/workflows/ios-appstore-assets.yml", "upload-app-privacy"),
    (".github/workflows/ios-appstore-assets.yml", "upload-assets"),
    (".github/workflows/ios-appstore-assets.yml", "validate-assets"),
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
            if uses.casefold().startswith(EXTERNAL_PYTHON_SETUP_USE) or (
                uses == LOCAL_PYTHON_SETUP_USE
            ):
                setup_steps.append((job_name, step))
    return setup_steps


def _discover_auxiliary_python_setup_steps() -> list[tuple[tuple[str, str], dict[str, Any]]]:
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_paths = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in workflow_dir.glob(pattern)
    )
    discovered: list[tuple[tuple[str, str], dict[str, Any]]] = []
    for path in workflow_paths:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        if rel_path in SEPARATELY_GOVERNED_PYTHON_SETUP_WORKFLOWS:
            continue
        for job_name, step in _iter_python_setup_steps(rel_path):
            discovered.append(((rel_path, job_name), step))
    return discovered


def _iter_ruby_setup_steps(path: str) -> list[tuple[str, dict[str, Any]]]:
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
            if str(step.get("uses", "")).casefold().startswith("ruby/setup-ruby@"):
                setup_steps.append((job_name, step))
    return setup_steps


def _python_version_input(step: dict[str, Any]) -> str:
    with_block = step.get("with", {})
    assert isinstance(with_block, dict)
    version = with_block.get("python-version")
    assert isinstance(version, str)
    return version


def _ruby_version_input(step: dict[str, Any]) -> str:
    with_block = step.get("with", {})
    assert isinstance(with_block, dict)
    version = with_block.get("ruby-version")
    assert isinstance(version, str)
    return version


def _assert_expected_ruby_setup_steps(
    discovered: list[tuple[tuple[str, str], dict[str, Any]]],
) -> None:
    owners = Counter(owner for owner, _step in discovered)
    assert owners == Counter(EXPECTED_RUBY_SETUP_OWNERS)
    for owner, step in discovered:
        assert step.get("uses") == RUBY_SETUP_ACTION, owner
        assert _ruby_version_input(step) == CANONICAL_RUBY, owner


def _assert_expected_auxiliary_python_setup_steps(
    discovered: list[tuple[tuple[str, str], dict[str, Any]]],
) -> None:
    """Require the finite owner multiset and canonical Python pin."""
    owners = Counter(owner for owner, _step in discovered)
    assert owners == Counter(EXPECTED_AUXILIARY_PYTHON_SETUP_OWNERS)
    for owner, step in discovered:
        assert _python_version_input(step) == CANONICAL_PYTHON, owner


def _assert_expected_python_setup_steps(
    discovered: list[tuple[str, dict[str, Any]]],
    expected: tuple[tuple[str, str], ...],
) -> None:
    """Require the finite owner/input multiset for one known workflow."""
    actual = Counter((owner, _python_version_input(step)) for owner, step in discovered)
    assert actual == Counter(expected)


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

    discovered = _iter_python_setup_steps(".github/workflows/ci.yml")
    _assert_expected_python_setup_steps(
        discovered,
        EXPECTED_CANONICAL_CI_PYTHON_SETUP_OWNERS,
    )
    setup_steps = dict(discovered)
    assert _python_version_input(setup_steps["test-pr"]) == "${{ env.PYTHON_VERSION }}"
    assert _python_version_input(setup_steps["test-feature"]) == "${{ env.PYTHON_VERSION }}"
    assert _python_version_input(setup_steps["test-main"]) == (
        "${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || matrix.python-version }}"
    )
    assert _python_version_input(setup_steps["pgvector_compat"]) == CANONICAL_PYTHON


def test_frontend_ci_keeps_shared_python_patch_source() -> None:
    workflow = _load_workflow(".github/workflows/frontend-ci.yml")
    assert workflow["env"]["PYTHON_VERSION"] == CANONICAL_PYTHON

    discovered = _iter_python_setup_steps(".github/workflows/frontend-ci.yml")
    _assert_expected_python_setup_steps(
        discovered,
        EXPECTED_FRONTEND_CI_PYTHON_SETUP_OWNERS,
    )
    setup_steps = dict(discovered)
    assert _python_version_input(setup_steps["build-and-test"]) == "${{ env.PYTHON_VERSION }}"


def test_canonical_ci_python_setup_owner_contract_rejects_stale_patch() -> None:
    owner = "pygments_exception_guard"
    discovered = [
        (
            owner,
            {
                "uses": "actions/setup-python@full-sha",
                "with": {"python-version": "3.13.13"},
            },
        )
    ]

    with pytest.raises(AssertionError):
        _assert_expected_python_setup_steps(
            discovered,
            ((owner, PYTHON_VERSION_FROM_ENV),),
        )


def test_frontend_ci_python_setup_owner_contract_rejects_duplicate_step() -> None:
    owner = "build-and-test"
    step = {
        "uses": "./.github/actions/python-setup",
        "with": {"python-version": PYTHON_VERSION_FROM_ENV},
    }
    discovered = [(owner, step), (owner, step)]

    with pytest.raises(AssertionError):
        _assert_expected_python_setup_steps(
            discovered,
            EXPECTED_FRONTEND_CI_PYTHON_SETUP_OWNERS,
        )


def test_auxiliary_workflow_python_setup_pins_use_exact_patch_version() -> None:
    discovered = _discover_auxiliary_python_setup_steps()
    _assert_expected_auxiliary_python_setup_steps(discovered)


def test_auxiliary_python_setup_discovery_rejects_unlisted_mixed_case_stale_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = _discover_auxiliary_python_setup_steps()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "unlisted.yaml").write_text(
        """
name: Unlisted Python owner
on: workflow_dispatch
jobs:
  stale-owner:
    runs-on: ubuntu-latest
    steps:
      - uses: Actions/setup-python@0123456789abcdef0123456789abcdef01234567
        with:
          python-version: "3.13.13"
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr("tests.test_runtime_toolchain_alignment.REPO_ROOT", tmp_path)

    unlisted = _discover_auxiliary_python_setup_steps()

    assert [owner for owner, _step in unlisted] == [
        (".github/workflows/unlisted.yaml", "stale-owner")
    ]
    with pytest.raises(AssertionError):
        _assert_expected_auxiliary_python_setup_steps([*baseline, *unlisted])


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


def test_repository_ruby_setup_steps_use_canonical_action_and_runtime() -> None:
    discovered: list[tuple[tuple[str, str], dict[str, Any]]] = []
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_paths = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in workflow_dir.glob(pattern)
    )
    for path in workflow_paths:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for job_name, step in _iter_ruby_setup_steps(rel_path):
            discovered.append(((rel_path, job_name), step))

    _assert_expected_ruby_setup_steps(discovered)


def test_ruby_setup_owner_contract_rejects_duplicate_step_in_one_job() -> None:
    owner = (".github/workflows/ci.yml", "jwt_fastlane_unblock_guard")
    step = {
        "uses": RUBY_SETUP_ACTION,
        "with": {"ruby-version": CANONICAL_RUBY},
    }
    discovered = [(owner, step), (owner, step)]

    with pytest.raises(AssertionError):
        _assert_expected_ruby_setup_steps(discovered)


def test_ruby_setup_discovery_catches_mixed_case_action_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_path = tmp_path / "mixed-case-ruby-action.yml"
    workflow_path.write_text(
        """
name: Mixed-case Ruby action
on: workflow_dispatch
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: Ruby/setup-ruby@v1
        with:
          ruby-version: "3.4"
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr("tests.test_runtime_toolchain_alignment.REPO_ROOT", tmp_path)

    discovered = _iter_ruby_setup_steps(workflow_path.name)

    assert discovered == [
        (
            "release",
            {
                "uses": "Ruby/setup-ruby@v1",
                "with": {"ruby-version": "3.4"},
            },
        )
    ]


def test_codecov_python_input_is_metadata_only_and_canonical() -> None:
    workflow = _load_workflow(".github/workflows/codecov-upload.yml")
    workflow_call = workflow[True]["workflow_call"]
    inputs = workflow_call["inputs"]

    assert inputs["python-version"] == {
        "description": (
            "Python metadata label for Codecov context; this workflow does not install Python"
        ),
        "required": False,
        "type": "string",
        "default": CANONICAL_PYTHON,
    }
    assert set(inputs) == {
        "coverage-file",
        "flags",
        "python-version",
        "name",
        "skip-upload",
        "fail_on_codecov_error",
        "coverage-artifact",
    }
    assert _iter_python_setup_steps(".github/workflows/codecov-upload.yml") == []


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
    assert _version_at_least(locked_excon, EXCON_MINIMUM_VERSION)
    assert _version_at_least("1.5", EXCON_MINIMUM_VERSION)
    assert not _version_at_least("1.5.0.rc1", EXCON_MINIMUM_VERSION)
    assert "      excon (>= 0.71.0, < 2.0.0)" in lockfile
