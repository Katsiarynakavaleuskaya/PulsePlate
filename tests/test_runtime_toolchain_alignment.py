"""Guards for local runtime and CI toolchain version alignment."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
import yaml

from scripts.ci.check_jwt_fastlane_unblock import _version_at_least
from tests.runtime_toolchain_versions import (
    CANONICAL_PYTHON,
    CANONICAL_RUBY,
    EXCON_MINIMUM_VERSION,
    FASTLANE_VERSION,
    JSON_MINIMUM_VERSION,
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
RUBY_DEPENDENCY_SURFACE_NAMES = frozenset({"Gemfile", "Gemfile.lock"})
EXPECTED_RUBY_DEPENDENCY_SURFACES = frozenset({"ios/Gemfile", "ios/Gemfile.lock"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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


def _locked_top_level_json_version(lockfile: str) -> str:
    """Return the sole stable top-level json version from Bundler's GEM specs."""
    lines = lockfile.splitlines()
    gem_boundaries = [index for index, line in enumerate(lines) if line == "GEM"]
    platform_boundaries = [index for index, line in enumerate(lines) if line == "PLATFORMS"]
    dependency_boundaries = [index for index, line in enumerate(lines) if line == "DEPENDENCIES"]
    bundled_boundaries = [index for index, line in enumerate(lines) if line == "BUNDLED WITH"]

    _require(len(gem_boundaries) == 1, "lock must contain exactly one GEM section")
    _require(len(platform_boundaries) == 1, "lock must contain exactly one PLATFORMS section")
    _require(
        len(dependency_boundaries) == 1,
        "lock must contain exactly one DEPENDENCIES section",
    )
    _require(len(bundled_boundaries) == 1, "lock must contain exactly one BUNDLED WITH section")
    gem_index = gem_boundaries[0]
    platforms_index = platform_boundaries[0]
    dependencies_index = dependency_boundaries[0]
    bundled_index = bundled_boundaries[0]
    _require(
        gem_index < platforms_index < dependencies_index < bundled_index,
        "lock sections must be ordered GEM < PLATFORMS < DEPENDENCIES < BUNDLED WITH",
    )
    specs_boundaries = [
        index for index in range(gem_index + 1, platforms_index) if lines[index] == "  specs:"
    ]
    _require(len(specs_boundaries) == 1, "GEM section must contain exactly one specs boundary")
    specs_index = specs_boundaries[0]
    remote_rows = [
        (index, lines[index])
        for index in range(gem_index + 1, platforms_index)
        if lines[index].startswith("  remote:")
    ]
    _require(len(remote_rows) == 1, "GEM section must contain exactly one remote")
    remote_index, remote_row = remote_rows[0]
    _require(
        remote_row == "  remote: https://rubygems.org/",
        "GEM remote must be the canonical RubyGems HTTPS endpoint",
    )
    _require(remote_index < specs_index, "GEM remote must precede specs")

    json_rows = [
        line
        for line in lines[specs_index + 1 : platforms_index]
        if re.match(r"^ {4}json(?:\s|\()", line)
    ]
    _require(len(json_rows) == 1, "GEM specs must contain exactly one top-level json row")
    match = re.fullmatch(r" {4}json \((\d+(?:\.\d+)*)\)", json_rows[0])
    _require(match is not None, "top-level json row must contain one stable numeric version")

    direct_json_rows = [
        line
        for line in lines[dependencies_index + 1 : bundled_index]
        if re.fullmatch(r" {2}json!?(?: \([^)]*\))?", line)
    ]
    _require(not direct_json_rows, "DEPENDENCIES must not declare json directly")
    return match.group(1)


def _assert_json_lock_postcondition(lockfile: str) -> None:
    locked_json = _locked_top_level_json_version(lockfile)
    _require(
        _version_at_least(locked_json, JSON_MINIMUM_VERSION),
        "top-level json version is below the repository security floor",
    )


def _discover_ruby_dependency_surfaces(repo_root: Path) -> dict[str, Path]:
    """Discover tracked exact Gemfile names through a strict NUL-delimited Git census."""
    git = shutil.which("git") or ""
    _require(bool(git), "git executable is unavailable for dependency surface census")
    _require(Path(git).is_absolute(), "git executable must resolve to an absolute path")
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    command = [git, "-C", str(repo_root), "ls-files", "--cached", "-z"]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=30,
            env=git_environment,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError("git index census timed out") from None
    except OSError:
        raise AssertionError("git index census could not start") from None
    _require(result.returncode == 0, "git index census failed")
    try:
        output = result.stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise AssertionError("git index census returned non-UTF-8 paths") from None
    _require(not output or output.endswith("\0"), "git index census returned malformed NUL framing")
    records = output.split("\0")[:-1] if output else []
    _require(all(records), "git index census returned an empty path record")
    _require(len(records) == len(set(records)), "git index census returned duplicate paths")

    discovered: dict[str, Path] = {}
    for record in records:
        relative = PurePosixPath(record)
        _require(
            not relative.is_absolute() and ".." not in relative.parts,
            "git index census returned an invalid relative path",
        )
        if relative.name not in RUBY_DEPENDENCY_SURFACE_NAMES:
            continue
        discovered[record] = repo_root.joinpath(*relative.parts)
    return discovered


def _assert_ruby_json_repository_postcondition(repo_root: Path) -> None:
    surfaces = _discover_ruby_dependency_surfaces(repo_root)
    _require(
        frozenset(surfaces) == EXPECTED_RUBY_DEPENDENCY_SURFACES,
        "tracked Ruby dependency surfaces differ from the exact two-path contract",
    )
    for path in surfaces.values():
        _require(
            path.is_file() and not path.is_symlink(),
            "tracked Ruby dependency surface must be a regular non-symlink file",
        )
    lockfile = surfaces["ios/Gemfile.lock"].read_text(encoding="utf-8")
    _assert_json_lock_postcondition(lockfile)


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

    _assert_json_lock_postcondition(lockfile)


def test_repository_ruby_json_dependency_surface_is_finite_and_patched() -> None:
    _assert_ruby_json_repository_postcondition(REPO_ROOT)


def _minimal_bundler_lock(
    version: str = "2.19.9",
    *,
    prefix: str = "",
    remote: str = "  remote: https://rubygems.org/\n",
    dependencies: str = "  fastlane (= 2.237.0)\n",
) -> str:
    return f"""\
{prefix}GEM
{remote}  specs:
    json ({version})
PLATFORMS
  ruby
DEPENDENCIES
{dependencies}BUNDLED WITH
   2.4.22
"""


def _write_minimal_ruby_dependency_surfaces(repo_root: Path, lockfile: str) -> None:
    ios_dir = repo_root / "ios"
    ios_dir.mkdir()
    (ios_dir / "Gemfile").write_text('gem "fastlane", "= 2.237.0"\n', encoding="utf-8")
    (ios_dir / "Gemfile.lock").write_text(lockfile, encoding="utf-8")


def _mock_git_index(
    monkeypatch: pytest.MonkeyPatch,
    stdout: bytes,
    *,
    returncode: int = 0,
    stderr: bytes = b"",
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        ),
    )


def test_git_index_census_is_nul_safe_and_clears_git_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=b"ios/Gemfile\0release tools/Gemfile.lock\0",
            stderr=b"",
        )

    monkeypatch.setenv("GIT_SECRET_CONTEXT", "must-not-propagate")
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(subprocess, "run", fake_run)

    surfaces = _discover_ruby_dependency_surfaces(tmp_path)

    assert set(surfaces) == {"ios/Gemfile", "release tools/Gemfile.lock"}
    assert captured["command"] == [
        "/usr/bin/git",
        "-C",
        str(tmp_path),
        "ls-files",
        "--cached",
        "-z",
    ]
    assert captured["check"] is False
    assert captured["capture_output"] is True
    assert captured["timeout"] == 30
    assert captured["shell"] is False
    assert all(not key.startswith("GIT_") for key in captured["env"])


def test_repository_postcondition_ignores_untracked_extra_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_ruby_dependency_surfaces(tmp_path, _minimal_bundler_lock())
    extra_dir = tmp_path / "untracked"
    extra_dir.mkdir()
    (extra_dir / "Gemfile.lock").write_text(_minimal_bundler_lock("2.19.8"), encoding="utf-8")
    _mock_git_index(monkeypatch, b"ios/Gemfile\0ios/Gemfile.lock\0")

    _assert_ruby_json_repository_postcondition(tmp_path)


def test_repository_postcondition_rejects_a_tracked_extra_vulnerable_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_ruby_dependency_surfaces(tmp_path, _minimal_bundler_lock())
    extra_dir = tmp_path / "release-tools"
    extra_dir.mkdir()
    (extra_dir / "Gemfile.lock").write_text(_minimal_bundler_lock("2.19.8"), encoding="utf-8")
    _mock_git_index(
        monkeypatch,
        b"ios/Gemfile\0ios/Gemfile.lock\0release-tools/Gemfile.lock\0",
    )

    with pytest.raises(AssertionError):
        _assert_ruby_json_repository_postcondition(tmp_path)


def test_repository_postcondition_rejects_a_missing_tracked_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ios_dir = tmp_path / "ios"
    ios_dir.mkdir()
    (ios_dir / "Gemfile").write_text('gem "fastlane"\n', encoding="utf-8")
    _mock_git_index(monkeypatch, b"ios/Gemfile\0ios/Gemfile.lock\0")

    with pytest.raises(AssertionError, match="regular non-symlink"):
        _assert_ruby_json_repository_postcondition(tmp_path)


def test_repository_postcondition_rejects_a_symlinked_tracked_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ios_dir = tmp_path / "ios"
    ios_dir.mkdir()
    (ios_dir / "Gemfile").write_text('gem "fastlane"\n', encoding="utf-8")
    target = tmp_path / "outside.lock"
    target.write_text(_minimal_bundler_lock(), encoding="utf-8")
    (ios_dir / "Gemfile.lock").symlink_to(target)
    _mock_git_index(monkeypatch, b"ios/Gemfile\0ios/Gemfile.lock\0")

    with pytest.raises(AssertionError, match="regular non-symlink"):
        _assert_ruby_json_repository_postcondition(tmp_path)


def test_git_index_census_fails_when_git_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(AssertionError, match="git executable is unavailable"):
        _discover_ruby_dependency_surfaces(tmp_path)


def test_git_index_census_fails_on_nonzero_exit_without_stderr_leakage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_git_index(monkeypatch, b"", returncode=128, stderr=b"secret raw diagnostic")

    with pytest.raises(AssertionError, match="^git index census failed$"):
        _discover_ruby_dependency_surfaces(tmp_path)


def test_git_index_census_fails_on_malformed_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_git_index(monkeypatch, b"ios/Gemfile\0\xff\0")

    with pytest.raises(AssertionError, match="non-UTF-8 paths"):
        _discover_ruby_dependency_surfaces(tmp_path)


@pytest.mark.parametrize("version", ["2.19.9", "2.19.10"])
def test_json_lock_postcondition_accepts_stable_patched_versions(version: str) -> None:
    _assert_json_lock_postcondition(_minimal_bundler_lock(version))


def test_json_lock_postcondition_allows_a_preceding_git_specs_block() -> None:
    prefix = """\
GIT
  remote: https://example.test/release-helper.git
  revision: 0123456789abcdef
  specs:
    release-helper (1.0.0)

"""

    _assert_json_lock_postcondition(_minimal_bundler_lock(prefix=prefix))


@pytest.mark.parametrize(
    "remote",
    [
        "",
        "  remote: https://rubygems.org/\n  remote: https://rubygems.org/\n",
        "  remote: http://rubygems.org/\n",
        "  remote: https://evil.example/\n",
    ],
)
def test_json_lock_postcondition_rejects_missing_duplicate_or_alternate_remote(
    remote: str,
) -> None:
    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(_minimal_bundler_lock(remote=remote))


def test_json_lock_postcondition_rejects_remote_after_specs() -> None:
    lockfile = _minimal_bundler_lock(remote="").replace(
        "  specs:\n",
        "  specs:\n  remote: https://rubygems.org/\n",
        1,
    )

    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(lockfile)


@pytest.mark.parametrize("heading", ["GEM", "PLATFORMS", "DEPENDENCIES", "BUNDLED WITH"])
def test_json_lock_postcondition_rejects_missing_sections(heading: str) -> None:
    lockfile = _minimal_bundler_lock().replace(f"{heading}\n", "", 1)

    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(lockfile)


@pytest.mark.parametrize("heading", ["GEM", "PLATFORMS", "DEPENDENCIES", "BUNDLED WITH"])
def test_json_lock_postcondition_rejects_duplicate_sections(heading: str) -> None:
    lockfile = _minimal_bundler_lock().replace(f"{heading}\n", f"{heading}\n{heading}\n", 1)

    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(lockfile)


def test_json_lock_postcondition_rejects_misordered_sections() -> None:
    lockfile = _minimal_bundler_lock().replace(
        "PLATFORMS\n  ruby\nDEPENDENCIES\n",
        "DEPENDENCIES\nPLATFORMS\n  ruby\n",
        1,
    )

    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(lockfile)


@pytest.mark.parametrize("dependency", ["  json\n", "  json (>= 2.19.9)\n", "  json!\n"])
def test_json_lock_postcondition_rejects_direct_json_dependencies(dependency: str) -> None:
    with pytest.raises(AssertionError, match="must not declare json directly"):
        _assert_json_lock_postcondition(_minimal_bundler_lock(dependencies=dependency))


@pytest.mark.parametrize("version", ["2.19.8", "2.19.9.rc1", "= 2.19.9", "2.19.9-beta"])
def test_json_lock_postcondition_rejects_unsafe_json_versions(version: str) -> None:
    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(_minimal_bundler_lock(version))


def test_json_lock_postcondition_rejects_missing_or_duplicate_json_rows() -> None:
    missing = _minimal_bundler_lock().replace("    json (2.19.9)\n", "")
    duplicate = _minimal_bundler_lock().replace(
        "    json (2.19.9)\n",
        "    json (2.19.9)\n    json (2.19.10)\n",
    )

    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(missing)
    with pytest.raises(AssertionError):
        _assert_json_lock_postcondition(duplicate)


def test_json_lock_postcondition_ignores_nested_and_similarly_named_gems() -> None:
    lockfile = _minimal_bundler_lock(
        dependencies="  json-schema\n  multi_json (= 1.19.1)\n",
    ).replace(
        "    json (2.19.9)\n",
        "    json (2.19.9)\n      json (< 3.0.0)\n    json-schema (5.2.2)\n"
        "    multi_json (1.19.1)\n",
    )

    _assert_json_lock_postcondition(lockfile)
