"""Tests for the Python dependency surface contract validator."""

from __future__ import annotations

import hashlib
import json
import netrc
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from scripts.ci import check_python_dependency_surfaces as surfaces
from scripts.ci import compile_locked_python_requirements as compiler
from scripts.ci import dependabot_requirement_carriers as carriers

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_INDEX = "https://packages.pulseplate.app/root/pulseplate/+simple/"
OBSERVABILITY_UPGRADES = {
    "opentelemetry-api": "1.44.0",
    "opentelemetry-sdk": "1.44.0",
    "opentelemetry-exporter-otlp-proto-http": "1.44.0",
    "opentelemetry-exporter-otlp-proto-common": "1.44.0",
    "opentelemetry-proto": "1.44.0",
    "opentelemetry-semantic-conventions": "0.65b0",
    "prometheus-client": "0.25.0",
}
OBSERVABILITY_REMOVALS = frozenset({"importlib-metadata", "zipp"})


def _run_fixture_git(repo: Path, *args: str) -> None:
    git_binary = shutil.which("git")
    assert git_binary is not None
    fixture_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    subprocess.run(  # nosec B603: resolved Git binary with test-owned argv (remove-by: 2026-10-31, ref: PR-2181)
        [git_binary, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=fixture_env,
        timeout=10,
    )


def _stage_fixture_paths(repo: Path, *paths: str) -> None:
    _run_fixture_git(repo, "add", "--", *paths)


def _write_lockfile(root: Path, surface: surfaces.DependencySurface) -> None:
    lock_path = root / surface.lockfile
    if surface.lockfile == "requirements-all.txt":
        lock_path.write_text("-r requirements.txt\npytest>=9.1.1\n", encoding="utf-8")
        return

    body = "" if surface.allow_empty_lock else "example==1.0.0\n"
    directive = "".join(f"{item}\n\n" for item in surface.allow_lock_directives)
    lock_path.write_text(
        surfaces.render_governed_lock_header(surface) + directive + body,
        encoding="utf-8",
    )


def _write_valid_contract_repo(root: Path) -> None:
    for directory in (
        root / ".github" / "actions" / "python-setup",
        root / ".github" / "workflows",
        root / "docs" / "contracts",
        root / "docs" / "evals",
        root / "docs" / "security",
        root / "docs",
        root / "scripts",
        root / "scripts" / "ci",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    all_surface_files = sorted(surfaces._known_requirement_surfaces())
    for surface in surfaces.DEPENDENCY_SURFACES:
        if surface.source_file is not None:
            source_body = "" if surface.allow_empty_lock else "example>=1.0.0\n"
            (root / surface.source_file).write_text(source_body, encoding="utf-8")
        _write_lockfile(root, surface)

    contract_body = "\n".join(
        [
            "# Python Dependency Surfaces",
            "Noncanonical Aggregate Install Surfaces",
            "Dependency Ownership Audit",
            "legacy_compat_transitional",
            "Legacy usage is evidence of transitional compatibility pressure",
            "scripts/ci/check_python_dependency_surfaces.py",
            *all_surface_files,
        ]
    )
    (root / surfaces.CONTRACT_DOC).write_text(contract_body, encoding="utf-8")
    for doc_path in surfaces.ACTIVE_LOCK_WORKFLOW_DOCS:
        if doc_path == surfaces.CONTRACT_DOC:
            continue
        (root / doc_path).parent.mkdir(parents=True, exist_ok=True)
        (root / doc_path).write_text(
            "\n".join(
                (
                    str(surfaces.CONTRACT_DOC),
                    "scripts/ci/check_python_dependency_surfaces.py",
                    "verify_requirements.py",
                )
            ),
            encoding="utf-8",
        )

    _write_python_setup_action(root)
    _write_installer_profiles(root)
    _write_pip_audit_helper(root)
    _write_dependency_submission_workflow(root)
    _run_fixture_git(root, "init", "--quiet")
    _stage_fixture_paths(root, ".")


def test_registry_rejects_novel_dependabot_carrier_class(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_valid_contract_repo(repo)
    (repo / "nested").mkdir()
    (repo / "nested" / "extra.txt").write_text(
        "novel-unowned-carrier>=1\n",
        encoding="utf-8",
    )
    _stage_fixture_paths(repo, "nested/extra.txt")

    errors = surfaces.validate_repo(repo)

    assert (
        "Dependabot-discoverable requirement carriers are not in the registry: "
        "['nested/extra.txt']."
    ) in errors


def test_registry_fails_closed_when_candidate_directory_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_valid_contract_repo(tmp_path)
    blocked_directory = tmp_path / "blocked"
    blocked_directory.mkdir()
    (blocked_directory / "extra.txt").write_text(
        "novel-unowned-carrier>=1\n",
        encoding="utf-8",
    )
    _stage_fixture_paths(tmp_path, "blocked/extra.txt")
    real_open = carriers.os.open

    def deny_blocked_directory(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == "blocked" and dir_fd is not None:
            raise PermissionError("deterministic unreadable-directory fixture")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(carriers.os, "open", deny_blocked_directory)

    errors = surfaces.validate_repo(tmp_path)

    assert (
        "Dependabot-discoverable requirement carrier scan could not inspect " "the repository tree."
    ) in errors


def _append_requirement(root: Path, relative_path: str, requirement_line: str) -> None:
    path = root / relative_path
    path.write_text(
        f"{path.read_text(encoding='utf-8').rstrip()}\n{requirement_line}\n",
        encoding="utf-8",
    )


def _append_runtime_requirement(
    root: Path,
    *,
    source_requirement: str,
    exact_requirement: str,
) -> None:
    _append_requirement(root, "requirements.in", source_requirement)
    _append_requirement(root, "requirements.txt", exact_requirement)
    _append_requirement(root, "requirements-lock.txt", exact_requirement)


def _remove_requirement(root: Path, relative_path: str, requirement_line: str) -> None:
    path = root / relative_path
    original = path.read_text(encoding="utf-8")
    updated = original.replace(f"{requirement_line}\n", "", 1)
    assert updated != original
    path.write_text(updated, encoding="utf-8")


def _write_registry_direct_owner_fixture(
    root: Path,
    surface: surfaces.DependencySurface,
) -> tuple[tuple[str, ...], list[str]]:
    exact_requirements: list[str] = []
    normalized_packages: list[str] = []
    compiled_surfaces = surfaces.compiled_dependency_surfaces()
    for source_index, source_file in enumerate(surface.compile_sources):
        for prefix in ("Zulu", "alpha"):
            package = f"{prefix}_{surface.name}_{source_index}"
            exact_requirement = f"{package}==1.0.0"
            _append_requirement(root, source_file, f"{package}>=1.0.0")
            for compiled_surface in compiled_surfaces:
                if source_file in compiled_surface.compile_sources:
                    _append_requirement(root, compiled_surface.lockfile, exact_requirement)
            exact_requirements.append(exact_requirement)
            normalized_packages.append(package.lower().replace("_", "-"))
    return tuple(exact_requirements), sorted(normalized_packages)


def _write_python_setup_action(root: Path, extra_case_labels: tuple[str, ...] = ()) -> None:
    profile_labels = (
        "runtime",
        "runtime-dev",
        "runtime-test",
        "ci-test",
        "ci-lite",
        "rag-vector",
        *extra_case_labels,
    )
    case_lines = "\n".join(f"            {profile}) ;;" for profile in profile_labels)
    (root / surfaces.PYTHON_SETUP_ACTION).write_text(
        (
            "# Mention requirements-data, requirements-evals, and rag-vector-cpu in a comment.\n"
            'case "$selected_profile" in\n'
            f"{case_lines}\n"
            "            *) ;;\n"
            "          esac\n"
        ),
        encoding="utf-8",
    )


def _write_installer_profiles(
    root: Path,
    *,
    profiles: tuple[str, ...] = (
        "runtime",
        "runtime-dev",
        "runtime-test",
        "ci-test",
        "ci-lite",
        "rag-vector",
    ),
) -> None:
    quoted_profiles = ", ".join(f'"{profile}"' for profile in profiles)
    (root / surfaces.INSTALLER_PATH).write_text(
        f"REQUIREMENTS_PROFILES: tuple[str, ...] = ({quoted_profiles},)\n",
        encoding="utf-8",
    )


def _write_pip_audit_helper(
    root: Path,
    *,
    omitted: tuple[str, ...] = (),
    comments: tuple[str, ...] = (),
) -> None:
    audited_lockfiles = [
        surface.lockfile
        for surface in surfaces.DEPENDENCY_SURFACES
        if surface.pip_audit_required and surface.lockfile not in omitted
    ]
    lines = [
        "#!/usr/bin/env bash",
        "# Comments are not audit coverage.",
        *(f"# {comment}" for comment in comments),
    ]
    if "requirements.txt" in audited_lockfiles:
        lines.append('manifests=("requirements.txt")')
    else:
        lines.append("manifests=()")
    lines.extend(
        f'manifests+=("{lockfile}")'
        for lockfile in audited_lockfiles
        if lockfile != "requirements.txt"
    )
    (root / surfaces.PIP_AUDIT_HELPER).write_text("\n".join(lines), encoding="utf-8")


def _write_dependency_submission_workflow(
    root: Path,
    *,
    omitted: tuple[str, ...] = (),
    trigger_omitted: tuple[str, ...] = (),
    trigger_paths: tuple[str, ...] = (),
) -> None:
    submitted_surfaces = [
        surface
        for surface in surfaces.DEPENDENCY_SURFACES
        if surface.dependency_submission_required
    ]
    submitted_lockfiles = [
        surface.lockfile for surface in submitted_surfaces if surface.lockfile not in omitted
    ]
    canonical_path_filters = [
        path
        for surface in submitted_surfaces
        for path in (surface.source_file, surface.lockfile)
        if path is not None and path not in trigger_omitted
    ]
    path_filters = [*trigger_paths, *canonical_path_filters]
    path_filter_lines = "\n".join(f'      - "{path}"' for path in sorted(set(path_filters)))
    copied_lockfiles = "\n".join(f"            {lockfile} \\" for lockfile in submitted_lockfiles)
    (root / surfaces.DEPENDENCY_SUBMISSION_WORKFLOW).write_text(
        "\n".join(
            (
                "name: Python Dependency Submission",
                "on:",
                "  push:",
                "    paths:",
                path_filter_lines,
                "  pull_request:",
                "    paths:",
                path_filter_lines,
                "jobs:",
                "  dependency-submission:",
                "    steps:",
                "      - name: Prepare dependency graph root",
                "        run: |",
                '          graph_root="${RUNNER_TEMP}/dependency-root"',
                "          cp \\",
                copied_lockfiles,
                '            "${graph_root}/"',
            )
        ),
        encoding="utf-8",
    )


def test_dependency_surface_contract_accepts_repo_contract() -> None:
    assert surfaces.validate_repo(REPO_ROOT) == []


def test_dependency_surface_contract_requires_all_managed_surfaces(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    (tmp_path / "requirements-docker-runtime.txt").unlink()

    errors = surfaces.validate_repo(tmp_path)

    assert errors == ["Missing required dependency policy file: requirements-docker-runtime.txt."]


def test_dependency_surface_contract_rejects_unknown_surface(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    (tmp_path / "requirements-surprise.txt").write_text("example==1.0.0\n", encoding="utf-8")
    _stage_fixture_paths(tmp_path, "requirements-surprise.txt")

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "Dependabot-discoverable requirement carriers are not in the registry: "
        "['requirements-surprise.txt']."
    ]


def test_dependency_surface_contract_rejects_local_manual_shared_profile(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_python_setup_action(tmp_path, extra_case_labels=("data", "evals", "rag-vector-cpu"))

    errors = surfaces.validate_repo(tmp_path)

    assert any("'data'" in error for error in errors)
    assert any("'evals'" in error for error in errors)
    assert any("'rag-vector-cpu'" in error for error in errors)


def test_dependency_surface_contract_loads_installer_profiles_from_repo_root(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_installer_profiles(
        tmp_path,
        profiles=("runtime", "runtime-dev", "runtime-test", "ci-test", "rag-vector"),
    )

    errors = surfaces.validate_repo(tmp_path)

    assert "Registry names unsupported installer profiles: ['ci-lite']." in errors


def test_dependency_surface_contract_ignores_local_manual_names_outside_profile_cases(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)

    errors = surfaces.validate_repo(tmp_path)

    assert errors == []


def test_dependency_surface_contract_rejects_missing_doc_mirror(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    contract_path = tmp_path / surfaces.CONTRACT_DOC
    contract_path.write_text(
        contract_path.read_text(encoding="utf-8").replace("requirements-evals.txt\n", ""),
        encoding="utf-8",
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.CONTRACT_DOC}: missing dependency surface requirements-evals.txt."
    ]


def test_dependency_surface_contract_rejects_missing_pip_audit_coverage(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_pip_audit_helper(tmp_path, omitted=("requirements-data.txt",))

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.PIP_AUDIT_HELPER}: missing pip-audit coverage for requirements-data.txt."
    ]


def test_dependency_surface_contract_rejects_missing_runtime_pip_audit_coverage(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_pip_audit_helper(tmp_path, omitted=("requirements.txt",))

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.PIP_AUDIT_HELPER}: missing pip-audit coverage for requirements.txt."
    ]


def test_dependency_surface_contract_rejects_missing_dependency_submission_coverage(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_dependency_submission_workflow(tmp_path, omitted=("requirements-dev.txt",))

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: missing dependency submission coverage "
        "for requirements-dev.txt."
    ]


def test_dependency_surface_contract_ignores_pip_audit_comment_mentions(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_pip_audit_helper(
        tmp_path,
        omitted=("requirements-data.txt",),
        comments=("requirements-data.txt is mentioned here but not audited.",),
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.PIP_AUDIT_HELPER}: missing pip-audit coverage for requirements-data.txt."
    ]


def test_dependency_surface_contract_ignores_dependency_submission_trigger_only_mentions(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_dependency_submission_workflow(
        tmp_path,
        omitted=("requirements-dev.txt",),
        trigger_paths=("requirements-dev.txt",),
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: missing dependency submission coverage "
        "for requirements-dev.txt."
    ]


def test_dependency_surface_contract_rejects_missing_dependency_submission_trigger_paths(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_dependency_submission_workflow(
        tmp_path,
        trigger_omitted=("requirements-test.in", "requirements-test.txt"),
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: push.paths missing dependency "
        "submission trigger for requirements-test.in.",
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: push.paths missing dependency "
        "submission trigger for requirements-test.txt.",
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: pull_request.paths missing dependency "
        "submission trigger for requirements-test.in.",
        f"{surfaces.DEPENDENCY_SUBMISSION_WORKFLOW}: pull_request.paths missing dependency "
        "submission trigger for requirements-test.txt.",
    ]


def test_dependency_surface_contract_rejects_non_exact_compiled_entry(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    runtime_surface = next(
        surface for surface in surfaces.DEPENDENCY_SURFACES if surface.name == "runtime"
    )
    (tmp_path / "requirements.txt").write_text(
        surfaces.render_governed_lock_header(runtime_surface)
        + "example==1.0.0\n"
        + "fastapi>=0.122.0\n",
        encoding="utf-8",
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == ["requirements.txt: compiled entry must be exact-pinned: 'fastapi>=0.122.0'."]


def test_dependency_surface_contract_rejects_obsolete_active_lock_instruction(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(
        tmp_path,
        str(surfaces.REQUIREMENTS_GUIDE),
        "Run pip-compile directly.",
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "REQUIREMENTS.md: active lock workflow must use make requirements-locks; "
        "forbidden token 'pip-compile'."
    ]


def test_dependency_surface_contract_rejects_wrong_profile_header(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    lock_path = tmp_path / "requirements-test.txt"
    lock_path.write_text(
        lock_path.read_text(encoding="utf-8").replace("# Profile: test", "# Profile: dev"),
        encoding="utf-8",
    )

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "requirements-test.txt: header must match governed profile 'test' and sources "
        "['requirements-test.in']."
    ]


@pytest.mark.parametrize(
    "surface",
    surfaces.compiled_dependency_surfaces(),
    ids=[surface.name for surface in surfaces.compiled_dependency_surfaces()],
)
def test_dependency_surface_contract_accepts_direct_owners_for_every_compiled_surface(
    tmp_path: Path,
    surface: surfaces.DependencySurface,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _write_registry_direct_owner_fixture(tmp_path, surface)

    errors = surfaces.validate_repo(tmp_path)

    assert errors == []


@pytest.mark.parametrize(
    "surface",
    surfaces.compiled_dependency_surfaces(),
    ids=[surface.name for surface in surfaces.compiled_dependency_surfaces()],
)
def test_dependency_surface_contract_rejects_missing_direct_owners_for_every_compiled_surface(
    tmp_path: Path,
    surface: surfaces.DependencySurface,
) -> None:
    _write_valid_contract_repo(tmp_path)
    exact_requirements, normalized_packages = _write_registry_direct_owner_fixture(
        tmp_path,
        surface,
    )
    for exact_requirement in exact_requirements:
        _remove_requirement(tmp_path, surface.lockfile, exact_requirement)

    errors = surfaces.validate_repo(tmp_path)

    source_label = " + ".join(surface.compile_sources)
    assert errors == [
        f"{surface.lockfile}: missing direct packages from "
        f"{source_label}: {normalized_packages}."
    ]


def test_dependency_ownership_audit_rejects_pyarrow_runtime_surfaces(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    for source_file in (
        "requirements.in",
        "requirements-ci-lite.in",
        "requirements-docker-runtime.in",
    ):
        _append_requirement(tmp_path, source_file, "pyarrow>=20.0.0,<25.0.0")
    for lockfile in (
        "requirements.txt",
        "requirements-ci-lite.txt",
        "requirements-docker-runtime.txt",
        "requirements-lock.txt",
    ):
        _append_requirement(tmp_path, lockfile, "pyarrow==23.0.1")

    errors = surfaces.validate_repo(tmp_path)

    assert any("pyarrow: error:runtime_direct_no_canonical_owner" in error for error in errors)


def test_dependency_ownership_audit_rejects_pyarrow_docker_runtime_surface(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(
        tmp_path,
        "requirements-docker-runtime.in",
        "pyarrow>=20.0.0,<25.0.0",
    )
    _append_requirement(tmp_path, "requirements-docker-runtime.txt", "pyarrow==23.0.1")

    findings = surfaces.collect_dependency_ownership_findings(tmp_path)
    errors = surfaces.validate_repo(tmp_path)

    assert any("pyarrow: error:runtime_direct_no_canonical_owner" in error for error in errors)
    assert any(
        finding.package == "pyarrow"
        and finding.reason_code == "runtime_direct_no_canonical_owner"
        and finding.surfaces
        == ("requirements-docker-runtime.in", "requirements-docker-runtime.txt")
        for finding in findings
    )


def test_dependency_ownership_audit_rejects_pandas_runtime_surfaces(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(tmp_path, "requirements.in", "pandas")
    _append_requirement(tmp_path, "requirements.txt", "pandas==3.0.3")

    errors = surfaces.validate_repo(tmp_path)

    assert any("pandas: error:data_eval_dependency_in_runtime" in error for error in errors)


def test_dependency_ownership_audit_rejects_httpx2_runtime_surfaces(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(tmp_path, "requirements-ci-lite.in", "httpx2>=2.3.0,<2.4.0")
    _append_requirement(tmp_path, "requirements-ci-lite.txt", "httpx2==2.3.0")

    errors = surfaces.validate_repo(tmp_path)

    assert any("httpx2: error:test_dev_dependency_in_runtime" in error for error in errors)


def test_import_evidence_uses_explicit_distribution_aliases(tmp_path: Path) -> None:
    source_file = tmp_path / "imports.py"

    source_file.write_text("import pydantic_core\n", encoding="utf-8")
    assert surfaces._imports_package(tmp_path, Path("imports.py"), "pydantic-core")


def test_import_evidence_does_not_blindly_normalize_underscores(tmp_path: Path) -> None:
    source_file = tmp_path / "imports.py"

    source_file.write_text("import httpx_2\n", encoding="utf-8")
    assert not surfaces._imports_package(tmp_path, Path("imports.py"), "httpx2")


def test_dependency_ownership_audit_accepts_reportlab_export_owner(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="reportlab>=4.4.4,<5.0.0",
        exact_requirement="reportlab==4.4.10",
    )
    owner_path = tmp_path / "app" / "routers"
    owner_path.mkdir(parents=True, exist_ok=True)
    (owner_path / "plan_export.py").write_text(
        "from reportlab.lib import colors\n", encoding="utf-8"
    )

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "reportlab"
        and finding.severity == surfaces.OWNERSHIP_INFO
        and finding.reason_code == "canonical_runtime_owner_documented"
        for finding in findings
    )


def test_dependency_ownership_audit_rejects_legacy_only_runtime_authority(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="reportlab>=4.4.4,<5.0.0",
        exact_requirement="reportlab==4.4.10",
    )
    (tmp_path / "legacy_app.py").write_text(
        "from reportlab.lib import colors\n",
        encoding="utf-8",
    )

    errors = surfaces.validate_repo(tmp_path)

    assert any(
        "reportlab: error:legacy_only_runtime_authority_forbidden" in error for error in errors
    )


def test_dependency_ownership_audit_reports_matplotlib_as_transitional(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="matplotlib>=3.10.7,<4.0.0",
        exact_requirement="matplotlib==3.10.8",
    )
    (tmp_path / "bmi_visualization.py").write_text("import matplotlib\n", encoding="utf-8")

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "matplotlib"
        and finding.severity == surfaces.OWNERSHIP_WARNING
        and finding.reason_code == "legacy_compat_transitional"
        for finding in findings
    )


def test_dependency_ownership_audit_reports_numpy_as_transitive_candidate(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="numpy>=2.4.1,<3.0.0",
        exact_requirement="numpy==2.4.6",
    )

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "numpy"
        and finding.severity == surfaces.OWNERSHIP_WARNING
        and finding.reason_code == "transitive_only_direct_runtime_candidate"
        for finding in findings
    )


def test_dependency_ownership_audit_documents_aiosqlite_sqlite_async_fallback_owner(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    for surface_file, requirement in (
        ("requirements.in", "aiosqlite>=0.22.1,<1.0.0"),
        ("requirements.txt", "aiosqlite==0.22.1"),
        ("requirements-lock.txt", "aiosqlite==0.22.1"),
        ("requirements-ci-lite.in", "aiosqlite>=0.22.1,<1.0.0"),
        ("requirements-ci-lite.txt", "aiosqlite==0.22.1"),
        ("requirements-docker-runtime.in", "aiosqlite>=0.22.1,<1.0.0"),
        ("requirements-docker-runtime.txt", "aiosqlite==0.22.1"),
    ):
        _append_requirement(tmp_path, surface_file, requirement)
    core_dir = tmp_path / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "db.py").write_text(
        "\n".join(
            (
                "def _sqlite_connect_args(url):",
                "    return {}",
                "",
                "def _derive_async_url(sync_url):",
                "    return sync_url.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)",
            )
        ),
        encoding="utf-8",
    )

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "aiosqlite"
        and finding.severity == surfaces.OWNERSHIP_INFO
        and finding.reason_code == "sqlite_async_fallback_owner_documented"
        and finding.surfaces == ("core/db.py",)
        for finding in findings
    )


def test_dependency_ownership_audit_keeps_aiosqlite_warning_without_owner_evidence(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="aiosqlite>=0.22.1,<1.0.0",
        exact_requirement="aiosqlite==0.22.1",
    )

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "aiosqlite"
        and finding.severity == surfaces.OWNERSHIP_WARNING
        and finding.reason_code == "db_fallback_test_split_pending"
        for finding in findings
    )


@pytest.mark.parametrize(
    "owner_text",
    (
        "def _derive_async_url(sync_url):\n    return 'sqlite+aiosqlite:///tmp.db'\n",
        "def _sqlite_connect_args(url):\n    return {}\n# sqlite+aiosqlite\n",
        "def _derive_async_url(sync_url):\n    return sync_url\n\ndef _sqlite_connect_args(url):\n    return {}\n",
    ),
)
def test_dependency_ownership_audit_requires_complete_aiosqlite_owner_evidence(
    tmp_path: Path,
    owner_text: str,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_runtime_requirement(
        tmp_path,
        source_requirement="aiosqlite>=0.22.1,<1.0.0",
        exact_requirement="aiosqlite==0.22.1",
    )
    core_dir = tmp_path / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "db.py").write_text(owner_text, encoding="utf-8")

    errors = surfaces.validate_repo(tmp_path)
    findings = surfaces.collect_dependency_ownership_findings(tmp_path)

    assert errors == []
    assert any(
        finding.package == "aiosqlite"
        and finding.severity == surfaces.OWNERSHIP_WARNING
        and finding.reason_code == "db_fallback_test_split_pending"
        for finding in findings
    )
    assert not any(
        finding.package == "aiosqlite"
        and finding.reason_code == "sqlite_async_fallback_owner_documented"
        for finding in findings
    )


def test_verify_requirements_wrapper_runs_surface_validator(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import verify_requirements

    result = verify_requirements.main(["--repo-root", str(REPO_ROOT)])

    assert result == 0
    assert (
        "PASS: Python dependency surfaces match the canonical contract." in capsys.readouterr().out
    )


def _surface(profile: str) -> surfaces.DependencySurface:
    return next(
        surface
        for surface in surfaces.compiled_dependency_surfaces()
        if surface.compile_profile == profile
    )


def _write_test_profile(root: Path) -> surfaces.DependencySurface:
    surface = _surface("test")
    (root / "requirements.txt").write_text("fastapi==0.138.1\n", encoding="utf-8")
    (root / "requirements-test.in").write_text(
        "-c requirements.txt\ncoverage~=7.15.1\nfaker~=40.31.0\npytest==9.1.3\n",
        encoding="utf-8",
    )
    (root / "requirements-test.txt").write_text(
        surfaces.render_governed_lock_header(surface)
        + "coverage[toml]==7.15.0\nfaker==40.28.1\npytest==9.1.3\n",
        encoding="utf-8",
    )
    return surface


def _candidate_output_path(command: list[str]) -> Path:
    output_arg = next(item for item in command if item.startswith("--output-file="))
    return Path(output_arg.split("=", 1)[1])


def _successful_resolver(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    _candidate_output_path(command).write_text(
        "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.1.3\n",
        encoding="utf-8",
    )
    return subprocess.CompletedProcess(command, 0, "", "")


def _write_test_wheel(
    wheelhouse: Path,
    *,
    name: str,
    version: str,
    metadata_name: str | None = None,
    metadata_version: str | None = None,
    requires_dist: tuple[str, ...] = (),
    dependency_links: tuple[str, ...] = (),
    tag: str = "py3-none-any",
) -> Path:
    filename_name = name.replace("-", "_")
    wheel_path = wheelhouse / f"{filename_name}-{version}-{tag}.whl"
    dist_info = f"{filename_name}-{version}.dist-info"
    metadata_lines = [
        "Metadata-Version: 2.3",
        f"Name: {metadata_name or name}",
        f"Version: {metadata_version or version}",
        *(f"Requires-Dist: {requirement}" for requirement in requires_dist),
        *(f"Dependency-Link: {link}" for link in dependency_links),
        "",
        "",
    ]
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        wheel.writestr(f"{dist_info}/METADATA", "\n".join(metadata_lines))
    return wheel_path


def _admit_test_wheel(admissions: dict[str, str], wheel_path: Path) -> None:
    admissions[wheel_path.name.lower()] = hashlib.sha256(wheel_path.read_bytes()).hexdigest()


def test_compile_registry_is_single_authority_for_every_compiled_surface() -> None:
    registry = compiler._profile_registry()

    assert set(registry) == {
        "runtime",
        "docker-runtime",
        "ci-lite",
        "test",
        "dev",
        "rag-vector",
        "rag-vector-cpu",
        "data",
        "evals",
        "aggregate",
    }
    assert set(registry.values()) == set(surfaces.compiled_dependency_surfaces())
    surfaces.validate_compile_registry()
    for surface in surfaces.compiled_dependency_surfaces():
        if surface.compile_profile != "aggregate":
            assert surface.compile_sources == (surface.source_file,)

    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "requirements-locks: ensure-python-proxy" in makefile
    assert "PULSEPLATE_LOCK_COMPILE_VIA_MAKE=1" in makefile
    assert "$(value LOCK_PROFILES)" in makefile
    assert "$(value UPGRADE_PACKAGES)" in makefile
    assert "$(value GRAPH_CHANGE_PACKAGES)" in makefile
    assert "$(value GRAPH_CHANGE_ADMISSION)" in makefile
    assert "$(LOCK_PROFILES)" not in makefile
    assert "$(UPGRADE_PACKAGES)" not in makefile
    assert "$(GRAPH_CHANGE_PACKAGES)" not in makefile
    assert "$(GRAPH_CHANGE_ADMISSION)" not in makefile

    ci_workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "--project coverage" in ci_workflow
    assert "--project faker" in ci_workflow


def test_governed_header_is_stable_make_only_provenance() -> None:
    surface = _surface("aggregate")

    header = surfaces.render_governed_lock_header(surface)

    assert "# Profile: aggregate" in header
    assert "# Sources: requirements-dev.in, requirements.in" in header
    assert 'LOCK_PROFILES="aggregate" make requirements-locks' in header
    assert "piptools" not in header
    assert "pip-compile" not in header
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in header


def test_make_preserves_lock_request_values_without_evaluating_them(tmp_path: Path) -> None:
    make = shutil.which("make")
    assert make is not None
    marker = tmp_path / "make-expanded-untrusted-input"
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "override RAW := $(value LOCK_PROFILES)\n"
        "export RAW\n"
        "unexport LOCK_PROFILES\n"
        "show:\n"
        '\t@printf "RAW=<%s>\\n" "$$RAW"\n',
        encoding="utf-8",
    )
    raw_value = f"$(shell touch {marker})"

    result = subprocess.run(  # nosec B603: resolved Make binary and inert temporary fixture (remove-by: 2027-01-31, ref: PR-2142)
        [make, "-s", "-f", str(makefile), "show", f"LOCK_PROFILES={raw_value}"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"RAW=<{raw_value}>\n"
    assert not marker.exists()


def test_profile_and_upgrade_selection_rejects_untrusted_values() -> None:
    assert compiler._parse_profiles("test dev aggregate") == ("test", "dev", "aggregate")
    assert compiler._parse_upgrades("coverage==7.15.1 faker==40.31.0") == {
        "coverage": "7.15.1",
        "faker": "40.31.0",
    }
    assert compiler._parse_graph_changes("Example_Pkg transitive.pkg") == frozenset(
        {"example-pkg", "transitive-pkg"}
    )

    for raw_profiles in (None, "", "test test", "test;touch-pwned"):
        with pytest.raises(RuntimeError):
            compiler._parse_profiles(raw_profiles)
    for raw_upgrade in (
        "pip==26.1.2",
        "coverage[toml]==7.15.1",
        "coverage>=7.15.1",
        "coverage==7.15.1;python_version>'3.11'",
        "coverage@https://example.invalid/coverage.whl",
        "coverage==7.15.1;touch-pwned",
    ):
        with pytest.raises(RuntimeError):
            compiler._parse_upgrades(raw_upgrade)
    for raw_graph_change in ("pip", "name;touch-pwned", "name name"):
        with pytest.raises(RuntimeError):
            compiler._parse_graph_changes(raw_graph_change)


def test_private_proxy_environment_is_canonical_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in compiler.AMBIENT_RESOLVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("PULSEPLATE_PYTHON_TRUSTED_HOST", raising=False)
    inspected_netrc_paths: list[Path | None] = []

    def inspect_netrc(_host: str, *, netrc_file: Path | None = None) -> None:
        inspected_netrc_paths.append(netrc_file)

    monkeypatch.setattr(
        compiler,
        "basic_auth_from_netrc",
        inspect_netrc,
    )

    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()
    child_env = compiler._private_proxy_child_env(
        {"HOME": "/tmp/home", compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
        resolver_home=resolver_home,
    )

    assert child_env["PIP_INDEX_URL"] == APPROVED_INDEX
    assert child_env["PIP_CONFIG_FILE"] == os.devnull
    assert child_env["PIP_NO_INPUT"] == "1"
    assert child_env["PIP_ONLY_BINARY"] == ":all:"
    assert "PIP_EXTRA_INDEX_URL" not in child_env
    assert inspected_netrc_paths == [resolver_home / ".netrc"]

    with pytest.raises((RuntimeError, ValueError)):
        compiler._private_proxy_child_env(
            {compiler.APPROVED_INDEX_ENV_VAR: "https://pypi.org/simple/"},
            resolver_home=resolver_home,
        )
    with pytest.raises((RuntimeError, ValueError)):
        credentialed_index = (
            "https://"
            + ":".join(("user", "placeholder"))
            + "@packages.pulseplate.app/root/pulseplate/+simple/"
        )
        compiler._private_proxy_child_env(
            {compiler.APPROVED_INDEX_ENV_VAR: credentialed_index},
            resolver_home=resolver_home,
        )
    with pytest.raises(RuntimeError, match="PIP_FIND_LINKS"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PIP_FIND_LINKS": "/tmp/wheels",
            },
            resolver_home=resolver_home,
        )
    with pytest.raises(RuntimeError, match="does not consume it"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PULSEPLATE_PYTHON_NETRC": "/tmp/custom.netrc",
            },
            resolver_home=resolver_home,
        )


@pytest.mark.parametrize(
    "variable",
    (
        "PIP_CONSTRAINT",
        "PIP_REQUIREMENT",
        "PIP_BUILD_CONSTRAINT",
        "PIP_ONLY_BINARY",
        "PIP_NO_BINARY",
        "PIP_PREFER_BINARY",
        "PIP_NO_CACHE_DIR",
        "PIP_KEYRING_PROVIDER",
        "NETRC",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ),
)
def test_private_proxy_environment_rejects_ambient_constraint_ca_and_proxy_controls(
    variable: str,
    tmp_path: Path,
) -> None:
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    with pytest.raises(RuntimeError, match=variable):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                variable: "/tmp/untracked-control",
            },
            resolver_home=resolver_home,
        )


def test_private_proxy_environment_rejects_root_netrc_authority(
    tmp_path: Path,
) -> None:
    source_home = tmp_path / "source-home"
    source_home.mkdir()
    source_netrc = source_home / ".netrc"
    source_netrc.write_text(
        "machine packages.pulseplate.app\n" "  login root\n" "  password test-only-placeholder\n",
        encoding="utf-8",
    )
    source_netrc.chmod(0o600)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    with pytest.raises(ValueError, match="root_devpi_credentials"):
        compiler._private_proxy_child_env(
            {"HOME": str(source_home), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
            resolver_home=resolver_home,
        )


def _write_private_proxy_netrc(home: Path, *, mode: int = 0o600) -> Path:
    netrc_path = home / ".netrc"
    netrc_path.write_text(
        "machine packages.pulseplate.app\n"
        "  login ci-reader\n"
        "  password test-only-placeholder\n",
        encoding="utf-8",
    )
    netrc_path.chmod(mode)
    return netrc_path


def test_private_proxy_environment_accepts_private_user_owned_netrc(tmp_path: Path) -> None:
    _write_private_proxy_netrc(tmp_path)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    child_env = compiler._private_proxy_child_env(
        {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
        resolver_home=resolver_home,
    )

    assert child_env["PIP_INDEX_URL"] == APPROVED_INDEX
    assert Path(child_env["HOME"]) == resolver_home
    assert (resolver_home / ".netrc").stat().st_mode & 0o077 == 0


def test_private_proxy_environment_materializes_only_canonical_machine(
    tmp_path: Path,
) -> None:
    source_netrc = _write_private_proxy_netrc(tmp_path)
    source_netrc.write_text(
        source_netrc.read_text(encoding="utf-8")
        + "machine unrelated.example\n"
        + "  login unrelated-user\n"
        + "  password unrelated-secret\n",
        encoding="utf-8",
    )
    source_netrc.chmod(0o600)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    child_env = compiler._private_proxy_child_env(
        {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
        resolver_home=resolver_home,
    )

    resolver_credentials = (Path(child_env["HOME"]) / ".netrc").read_text(encoding="utf-8")
    assert "packages.pulseplate.app" in resolver_credentials
    assert "ci-reader" in resolver_credentials
    assert "unrelated.example" not in resolver_credentials
    assert "unrelated-secret" not in resolver_credentials
    assert not (resolver_home / ".netrc.source").exists()


def test_private_proxy_environment_materializes_stable_netrc_authority(tmp_path: Path) -> None:
    source_netrc = _write_private_proxy_netrc(tmp_path)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    child_env = compiler._private_proxy_child_env(
        {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
        resolver_home=resolver_home,
    )
    replacement = tmp_path / "replacement.netrc"
    replacement.write_text(
        "machine packages.pulseplate.app\n"
        "  login root\n"
        "  password replaced-after-validation\n",
        encoding="utf-8",
    )
    replacement.chmod(0o600)
    replacement.replace(source_netrc)

    resolver_netrc = Path(child_env["HOME"]) / ".netrc"
    resolver_credentials = netrc.netrc(str(resolver_netrc)).hosts["packages.pulseplate.app"]
    assert resolver_credentials[0] == "ci-reader"
    assert resolver_credentials[2] == "test-only-placeholder"


def test_private_proxy_environment_fails_closed_without_effective_uid_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_private_proxy_netrc(tmp_path)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()
    monkeypatch.delattr(compiler.os, "geteuid", raising=False)

    with pytest.raises(RuntimeError, match="requires POSIX effective-UID"):
        compiler._private_proxy_child_env(
            {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
            resolver_home=resolver_home,
        )


def test_private_proxy_environment_rejects_broad_netrc_permissions(tmp_path: Path) -> None:
    _write_private_proxy_netrc(tmp_path, mode=0o644)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    with pytest.raises(RuntimeError, match="no broader than 0600"):
        compiler._private_proxy_child_env(
            {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
            resolver_home=resolver_home,
        )


def test_private_proxy_environment_rejects_symlinked_netrc(tmp_path: Path) -> None:
    real_netrc = tmp_path / "credentials"
    real_netrc.write_text("machine packages.pulseplate.app\n", encoding="utf-8")
    real_netrc.chmod(0o600)
    (tmp_path / ".netrc").symlink_to(real_netrc)
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    with pytest.raises(RuntimeError, match="regular non-symlink"):
        compiler._private_proxy_child_env(
            {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
            resolver_home=resolver_home,
        )


def test_private_proxy_environment_rejects_foreign_owned_netrc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    netrc_path = _write_private_proxy_netrc(tmp_path)
    monkeypatch.setattr(
        compiler.os,
        "geteuid",
        lambda: netrc_path.stat().st_uid + 1,
        raising=False,
    )
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir()

    with pytest.raises(RuntimeError, match="owned by the effective user"):
        compiler._private_proxy_child_env(
            {"HOME": str(tmp_path), compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX},
            resolver_home=resolver_home,
        )


def test_download_phase_batches_exact_profile_pins_without_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    plan = compiler._capture_lock_input_plan(
        repo_root=tmp_path,
        surface=surface,
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    child_env = {
        "HOME": str(tmp_path / "credentialed-home"),
        "PIP_INDEX_URL": APPROVED_INDEX,
        "PIP_KEYRING_PROVIDER": "disabled",
        "PIP_NO_CACHE_DIR": "1",
    }
    commands: list[list[str]] = []

    def download(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert kwargs["env"] == child_env
        destination = Path(command[command.index("--dest") + 1])
        for requirement in command[command.index("--find-links") + 2 :]:
            name, version = requirement.split("==", 1)
            _write_test_wheel(destination, name=name, version=version)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(compiler.subprocess, "run", download)

    compiler._download_profile_wheels(
        wheelhouse=wheelhouse,
        plans=(plan,),
        child_env=child_env,
        bootstrap_artifacts=frozenset({("pip", "26.1.2")}),
    )

    assert len(commands) == 1
    command = commands[0]
    assert command[:4] == [sys.executable, "-m", "pip", "download"]
    assert "--no-deps" in command
    assert "--only-binary=:all:" in command
    assert command[command.index("--find-links") + 1] == str(wheelhouse)
    assert {token for token in command if "==" in token} == {
        "coverage==7.15.1",
        "faker==40.31.0",
        "pip==26.1.2",
        "pytest==9.1.3",
    }


def test_artifact_admission_collects_only_proxy_hash_bound_wheels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver_home = tmp_path / "resolver-home"
    resolver_home.mkdir(mode=0o700)
    child_env = {
        "HOME": str(resolver_home),
        "PIP_INDEX_URL": APPROVED_INDEX,
    }

    monkeypatch.setattr(
        compiler,
        "basic_auth_from_netrc",
        lambda *_args, **_kwargs: "Basic opaque",
    )

    def fetch(
        url: str,
        **kwargs: object,
    ) -> tuple[int, bytes]:
        assert kwargs["authorization_header"] == "Basic opaque"
        package = url.rstrip("/").rsplit("/", 1)[-1]
        version = {"coverage": "7.15.1", "faker": "40.31.0"}[package]
        filename = f"{package}-{version}-py3-none-any.whl"
        digest = ("a" if package == "coverage" else "b") * 64
        return (
            200,
            f'<a href="../../+f/abc/{filename}#sha256={digest}">wheel</a>'.encode(),
        )

    monkeypatch.setattr(compiler, "fetch_project_page", fetch)

    assert compiler._collect_private_proxy_artifact_hashes(
        expected_artifacts=frozenset({("coverage", "7.15.1"), ("faker", "40.31.0")}),
        child_env=child_env,
    ) == {
        "coverage-7.15.1-py3-none-any.whl": "a" * 64,
        "faker-40.31.0-py3-none-any.whl": "b" * 64,
    }


def test_resolver_bootstrap_uses_exact_approved_interpreter_pip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_version(distribution_name: str) -> str:
        assert distribution_name == "pip"
        return "26.1.2"

    monkeypatch.setattr(compiler.importlib_metadata, "version", fake_version)

    assert compiler._resolver_bootstrap_artifacts() == frozenset({("pip", "26.1.2")})


def test_offline_compile_environment_has_no_credentials_or_index(
    tmp_path: Path,
) -> None:
    offline_home = tmp_path / "offline-home"
    wheelhouse = tmp_path / "wheelhouse"
    offline_home.mkdir(mode=0o700)
    wheelhouse.mkdir(mode=0o700)

    child_env = compiler._offline_compile_env(
        {
            "PATH": "/usr/bin",
            compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
        },
        resolver_home=offline_home,
        wheelhouse=wheelhouse,
    )

    assert child_env["HOME"] == str(offline_home)
    assert child_env["PIP_NO_INDEX"] == "1"
    assert child_env["PIP_FIND_LINKS"] == str(wheelhouse)
    assert child_env["PIP_ONLY_BINARY"] == ":all:"
    assert child_env["PIP_NO_CACHE_DIR"] == "1"
    assert child_env["PIP_KEYRING_PROVIDER"] == "disabled"
    assert child_env["PIP_CONFIG_FILE"] == os.devnull
    assert "PIP_INDEX_URL" not in child_env
    assert compiler.APPROVED_INDEX_ENV_VAR not in child_env
    assert not (offline_home / ".netrc").exists()


@pytest.mark.parametrize("variable", ("NETRC", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL"))
def test_offline_compile_environment_rejects_credential_and_index_overrides(
    variable: str,
    tmp_path: Path,
) -> None:
    offline_home = tmp_path / "offline-home"
    wheelhouse = tmp_path / "wheelhouse"
    offline_home.mkdir(mode=0o700)
    wheelhouse.mkdir(mode=0o700)

    with pytest.raises(RuntimeError, match=variable):
        compiler._offline_compile_env(
            {
                "PATH": "/usr/bin",
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                variable: "unexpected",
            },
            resolver_home=offline_home,
            wheelhouse=wheelhouse,
        )


@pytest.mark.parametrize(
    "metadata_kwargs,match",
    (
        (
            {"requires_dist": ("dep @ https://example.invalid/dep.whl",)},
            "direct-reference Requires-Dist",
        ),
        (
            {"requires_dist": ("not a valid requirement @",)},
            "malformed Requires-Dist",
        ),
        (
            {"dependency_links": ("https://example.invalid/simple",)},
            "Dependency-Link metadata is forbidden",
        ),
        (
            {"metadata_name": "other-package"},
            "filename and METADATA Name/Version do not match",
        ),
    ),
)
def test_wheel_metadata_validation_rejects_untrusted_metadata(
    tmp_path: Path,
    metadata_kwargs: dict[str, object],
    match: str,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    _write_test_wheel(
        wheelhouse,
        name="example-package",
        version="1.0.0",
        **metadata_kwargs,
    )

    with pytest.raises(RuntimeError, match=match):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("example-package", "1.0.0")}),
        )


def test_wheel_metadata_validation_accepts_normal_dependency_metadata(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    _write_test_wheel(
        wheelhouse,
        name="example-package",
        version="1.0.0",
        requires_dist=(
            'required-dependency>=2; python_version >= "3.11"',
            'optional-dependency; extra == "speed"',
        ),
    )
    _write_test_wheel(
        wheelhouse,
        name="required-dependency",
        version="2.0.0",
    )
    _write_test_wheel(
        wheelhouse,
        name="optional-dependency",
        version="3.0.0",
    )
    expected = frozenset(
        {
            ("example-package", "1.0.0"),
            ("required-dependency", "2.0.0"),
            ("optional-dependency", "3.0.0"),
        }
    )

    assert set(
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=expected,
        )
    ) == set(expected)


def test_wheelhouse_requires_matching_private_proxy_admission_hash(
    tmp_path: Path,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    wheel_path = _write_test_wheel(
        wheelhouse,
        name="example-package",
        version="1.0.0",
    )
    expected = frozenset({("example-package", "1.0.0")})
    digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()

    assert compiler._validate_wheelhouse(
        wheelhouse=wheelhouse,
        expected_artifacts=expected,
        admitted_hashes={wheel_path.name.lower(): digest},
    )

    with pytest.raises(RuntimeError, match="does not match"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=expected,
            admitted_hashes={wheel_path.name.lower(): "0" * 64},
        )

    with pytest.raises(RuntimeError, match="absent from"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=expected,
            admitted_hashes={},
        )


def test_wheelhouse_rejects_missing_extra_duplicate_and_malformed_artifacts(
    tmp_path: Path,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    _write_test_wheel(wheelhouse, name="one", version="1.0.0")
    expected = frozenset({("one", "1.0.0"), ("two", "2.0.0")})
    with pytest.raises(RuntimeError, match="missing=.*two"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=expected,
        )

    _write_test_wheel(wheelhouse, name="unexpected", version="3.0.0")
    with pytest.raises(RuntimeError, match="unexpected wheel artifact"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=expected,
        )

    (wheelhouse / "unexpected-3.0.0-py3-none-any.whl").unlink()
    _write_test_wheel(wheelhouse, name="one", version="1.0.0", tag="py2-none-any")
    with pytest.raises(RuntimeError, match="duplicate artifacts"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("one", "1.0.0")}),
        )

    for artifact in wheelhouse.iterdir():
        artifact.unlink()
    (wheelhouse / "one-1.0.0-py3-none-any.whl").write_bytes(b"not-a-wheel")
    with pytest.raises(RuntimeError, match="malformed wheel archive"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("one", "1.0.0")}),
        )


def test_wheelhouse_rejects_duplicate_members_and_member_count_overflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    wheel_path = _write_test_wheel(wheelhouse, name="one", version="1.0.0")
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(wheel_path, "a") as wheel:
            wheel.writestr("one/__init__.py", "")
            wheel.writestr("one/__init__.py", "")
    with pytest.raises(RuntimeError, match="duplicate archive members"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("one", "1.0.0")}),
        )

    wheel_path.unlink()
    _write_test_wheel(wheelhouse, name="one", version="1.0.0")
    monkeypatch.setattr(compiler, "MAX_WHEEL_MEMBERS", 0)

    class UnexpectedZipFile:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("ZipFile must not run before the member bound is enforced")

    monkeypatch.setattr(compiler.zipfile, "ZipFile", UnexpectedZipFile)
    with pytest.raises(RuntimeError, match="too many archive members"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("one", "1.0.0")}),
        )


def test_wheel_central_directory_size_is_bounded_before_zipfile_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    _write_test_wheel(wheelhouse, name="one", version="1.0.0")
    monkeypatch.setattr(compiler, "MAX_WHEEL_CENTRAL_DIRECTORY_BYTES", 1)

    class UnexpectedZipFile:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("ZipFile must not run before the size bound is enforced")

    monkeypatch.setattr(compiler.zipfile, "ZipFile", UnexpectedZipFile)
    with pytest.raises(RuntimeError, match="central directory exceeds the size limit"):
        compiler._validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=frozenset({("one", "1.0.0")}),
        )


def test_empty_profile_download_does_not_start_pip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "requirements-evals.txt"
    output_path.write_text("", encoding="utf-8")
    plan = compiler.LockInputPlan(
        surface=_surface("evals"),
        output_path=output_path,
        output_capture=compiler._capture_file(output_path),
        source_captures=(),
        expected_artifacts=frozenset(),
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)

    def unexpected_subprocess(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("empty profiles must not start pip download")

    monkeypatch.setattr(compiler.subprocess, "run", unexpected_subprocess)

    compiler._download_profile_wheels(
        wheelhouse=wheelhouse,
        plans=(plan,),
        child_env={},
    )

    assert tuple(wheelhouse.iterdir()) == ()


def test_empty_profile_downloads_resolver_bootstrap_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "requirements-evals.txt"
    output_path.write_text("", encoding="utf-8")
    plan = compiler.LockInputPlan(
        surface=_surface("evals"),
        output_path=output_path,
        output_capture=compiler._capture_file(output_path),
        source_captures=(),
        expected_artifacts=frozenset(),
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    commands: list[list[str]] = []

    def download(
        command: list[str],
        **_: object,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(compiler.subprocess, "run", download)

    compiler._download_profile_wheels(
        wheelhouse=wheelhouse,
        plans=(plan,),
        child_env={},
        bootstrap_artifacts=frozenset({("pip", "26.1.2")}),
    )

    assert len(commands) == 1
    assert [token for token in commands[0] if "==" in token] == ["pip==26.1.2"]


def test_profile_wheelhouse_views_isolate_conflicting_versions(tmp_path: Path) -> None:
    central = tmp_path / "central"
    views_root = tmp_path / "views"
    central.mkdir(mode=0o700)
    views_root.mkdir(mode=0o700)
    _write_test_wheel(central, name="shared-package", version="1.0.0")
    _write_test_wheel(central, name="shared-package", version="2.0.0")
    expected = frozenset(
        {
            ("shared-package", "1.0.0"),
            ("shared-package", "2.0.0"),
        }
    )
    artifacts = compiler._validate_wheelhouse(
        wheelhouse=central,
        expected_artifacts=expected,
    )
    output_a = tmp_path / "a.txt"
    output_b = tmp_path / "b.txt"
    output_a.write_text("shared-package==1.0.0\n", encoding="utf-8")
    output_b.write_text("shared-package==2.0.0\n", encoding="utf-8")
    plans = (
        compiler.LockInputPlan(
            surface=_surface("test"),
            output_path=output_a,
            output_capture=compiler._capture_file(output_a),
            source_captures=(),
            expected_artifacts=frozenset({("shared-package", "1.0.0")}),
        ),
        compiler.LockInputPlan(
            surface=_surface("dev"),
            output_path=output_b,
            output_capture=compiler._capture_file(output_b),
            source_captures=(),
            expected_artifacts=frozenset({("shared-package", "2.0.0")}),
        ),
    )

    views = compiler._create_profile_wheelhouse_views(
        plans=plans,
        artifacts=artifacts,
        views_root=views_root,
    )

    assert {path.name for path in views["test"].path.iterdir()} == {
        "shared_package-1.0.0-py3-none-any.whl"
    }
    assert {path.name for path in views["dev"].path.iterdir()} == {
        "shared_package-2.0.0-py3-none-any.whl"
    }


def test_untrusted_wheel_metadata_stops_before_compiler_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    original = (tmp_path / surface.lockfile).read_bytes()
    monkeypatch.setattr(compiler, "_profile_registry", lambda: {"test": surface})
    credentialed_homes: list[Path] = []

    def credentialed_env(
        _environment: dict[str, str],
        *,
        resolver_home: Path,
    ) -> dict[str, str]:
        credentialed_homes.append(resolver_home)
        (resolver_home / ".netrc").write_text("temporary credentials\n", encoding="utf-8")
        return {"HOME": str(resolver_home)}

    monkeypatch.setattr(compiler, "_private_proxy_child_env", credentialed_env)
    admissions: dict[str, str] = {}
    monkeypatch.setattr(
        compiler,
        "_collect_private_proxy_artifact_hashes",
        lambda **_kwargs: admissions,
    )

    def malicious_download(
        *,
        wheelhouse: Path,
        plans: tuple[compiler.LockInputPlan, ...],
        child_env: dict[str, str],
        bootstrap_artifacts: frozenset[tuple[str, str]],
    ) -> None:
        assert child_env["HOME"]
        for package, version in plans[0].expected_artifacts | bootstrap_artifacts:
            requires_dist = (
                ("dep @ https://example.invalid/dep.whl",) if package == "coverage" else ()
            )
            wheel_path = _write_test_wheel(
                wheelhouse,
                name=package,
                version=version,
                requires_dist=requires_dist,
            )
            _admit_test_wheel(admissions, wheel_path)

    monkeypatch.setattr(compiler, "_download_profile_wheels", malicious_download)
    real_validate_wheelhouse = compiler._validate_wheelhouse

    def validate_after_credential_teardown(**kwargs: object) -> object:
        assert len(credentialed_homes) == 1
        assert not credentialed_homes[0].exists()
        return real_validate_wheelhouse(**kwargs)

    monkeypatch.setattr(compiler, "_validate_wheelhouse", validate_after_credential_teardown)

    def compiler_must_not_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("offline compiler ran before wheel validation")

    monkeypatch.setattr(compiler.subprocess, "run", compiler_must_not_run)

    with pytest.raises(RuntimeError, match="direct-reference Requires-Dist"):
        compiler._compile_selected_profiles_locked(
            repo_root=tmp_path,
            profiles=("test",),
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            environment={},
        )
    assert (tmp_path / surface.lockfile).read_bytes() == original


def test_two_phase_pipeline_passes_only_offline_profile_artifacts_to_compiler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    original = output_path.read_bytes()
    monkeypatch.setattr(compiler, "_profile_registry", lambda: {"test": surface})
    monkeypatch.setattr(
        compiler,
        "_resolver_bootstrap_artifacts",
        lambda: frozenset({("pip", "26.1.2")}),
    )
    credentialed_homes: list[Path] = []

    def credentialed_env(
        _environment: dict[str, str],
        *,
        resolver_home: Path,
    ) -> dict[str, str]:
        credentialed_homes.append(resolver_home)
        (resolver_home / ".netrc").write_text("temporary credentials\n", encoding="utf-8")
        return {
            "HOME": str(resolver_home),
            "PIP_INDEX_URL": APPROVED_INDEX,
        }

    monkeypatch.setattr(compiler, "_private_proxy_child_env", credentialed_env)
    admissions: dict[str, str] = {}
    monkeypatch.setattr(
        compiler,
        "_collect_private_proxy_artifact_hashes",
        lambda **_kwargs: admissions,
    )

    def admitted_download(
        *,
        wheelhouse: Path,
        plans: tuple[compiler.LockInputPlan, ...],
        bootstrap_artifacts: frozenset[tuple[str, str]],
        **_: object,
    ) -> None:
        for package, version in plans[0].expected_artifacts | bootstrap_artifacts:
            wheel_path = _write_test_wheel(
                wheelhouse,
                name=package,
                version=version,
            )
            _admit_test_wheel(admissions, wheel_path)

    monkeypatch.setattr(compiler, "_download_profile_wheels", admitted_download)

    class PipelineCaptured(RuntimeError):
        pass

    def capture_prepare(**kwargs: object) -> compiler.PreparedLock:
        child_env_value = kwargs["child_env"]
        wheel_artifacts_value = kwargs["wheel_artifacts"]
        assert isinstance(child_env_value, dict)
        assert isinstance(wheel_artifacts_value, tuple)
        child_env = child_env_value
        wheel_artifacts = wheel_artifacts_value
        assert child_env["PIP_NO_INDEX"] == "1"
        assert "PIP_INDEX_URL" not in child_env
        assert compiler.APPROVED_INDEX_ENV_VAR not in child_env
        offline_home = Path(child_env["HOME"])
        assert offline_home.exists()
        assert not (offline_home / ".netrc").exists()
        assert credentialed_homes and offline_home != credentialed_homes[0]
        profile_wheelhouse = Path(child_env["PIP_FIND_LINKS"])
        assert profile_wheelhouse.name == "test"
        assert profile_wheelhouse.parent.name == "profile-wheelhouses"
        assert {artifact.artifact_key for artifact in wheel_artifacts} == (
            compiler._capture_lock_input_plan(
                repo_root=tmp_path,
                surface=surface,
                upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            ).expected_artifacts
            | {("pip", "26.1.2")}
        )
        raise PipelineCaptured

    monkeypatch.setattr(compiler, "_prepare_lock", capture_prepare)

    with pytest.raises(PipelineCaptured):
        compiler._compile_selected_profiles_locked(
            repo_root=tmp_path,
            profiles=("test",),
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            environment={
                "PATH": "/usr/bin",
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
            },
        )

    assert len(credentialed_homes) == 1
    assert not credentialed_homes[0].exists()
    assert output_path.read_bytes() == original


def test_network_phase_source_mutation_stops_before_offline_compile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    source_path = tmp_path / "requirements-test.in"
    monkeypatch.setattr(compiler, "_profile_registry", lambda: {"test": surface})
    monkeypatch.setattr(
        compiler,
        "_private_proxy_child_env",
        lambda _environment, *, resolver_home: {"HOME": str(resolver_home)},
    )
    admissions: dict[str, str] = {}
    monkeypatch.setattr(
        compiler,
        "_collect_private_proxy_artifact_hashes",
        lambda **_kwargs: admissions,
    )

    def mutate_during_download(
        *,
        wheelhouse: Path,
        plans: tuple[compiler.LockInputPlan, ...],
        **_: object,
    ) -> None:
        for package, version in plans[0].expected_artifacts:
            wheel_path = _write_test_wheel(
                wheelhouse,
                name=package,
                version=version,
            )
            _admit_test_wheel(admissions, wheel_path)
        source_path.write_text(
            source_path.read_text(encoding="utf-8") + "# changed during network phase\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(compiler, "_download_profile_wheels", mutate_during_download)

    def compiler_must_not_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("offline compiler ran after captured source mutation")

    monkeypatch.setattr(compiler.subprocess, "run", compiler_must_not_run)

    with pytest.raises(RuntimeError, match="changed during lock compilation"):
        compiler._compile_selected_profiles_locked(
            repo_root=tmp_path,
            profiles=("test",),
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            environment={},
        )


def test_validated_wheel_mutation_is_rejected_after_offline_compile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir(mode=0o700)
    wheel_path = _write_test_wheel(
        wheelhouse,
        name="coverage",
        version="7.15.1",
    )
    artifact = compiler._validate_wheelhouse(
        wheelhouse=wheelhouse,
        expected_artifacts=frozenset({("coverage", "7.15.1")}),
    )[("coverage", "7.15.1")]

    def mutate_after_compile(
        command: list[str],
        **_: object,
    ) -> subprocess.CompletedProcess[str]:
        result = _successful_resolver(command)
        wheel_path.write_bytes(wheel_path.read_bytes() + b"changed")
        return result

    monkeypatch.setattr(compiler.subprocess, "run", mutate_after_compile)

    with pytest.raises(RuntimeError, match="Validated wheel changed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
            wheel_artifacts=(artifact,),
        )


def test_compile_command_uses_module_argv_and_excludes_pip() -> None:
    command = compiler._build_compile_command(
        surface=_surface("test"),
        output_path=Path("requirements-test.txt.candidate"),
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
    )

    assert command[:4] == [sys.executable, "-m", "piptools", "compile"]
    assert "--no-allow-unsafe" in command
    assert "--allow-unsafe" not in command
    assert command[command.index("--unsafe-package") + 1] == "pip"
    assert "--no-config" in command
    assert "--no-emit-index-url" in command
    assert "--no-strip-extras" in command
    assert command[-1] == "requirements-test.in"


def test_prepare_lock_is_seeded_validated_and_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    original = (tmp_path / surface.lockfile).read_bytes()
    monkeypatch.setattr(compiler.subprocess, "run", _successful_resolver)

    prepared = compiler._prepare_lock(
        repo_root=tmp_path,
        surface=surface,
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
        graph_changes=frozenset(),
        child_env={},
    )

    assert (tmp_path / surface.lockfile).read_bytes() == original
    candidate = prepared.candidate_path.read_text(encoding="utf-8")
    assert candidate.startswith(surfaces.render_governed_lock_header(surface))
    assert "coverage[toml]==7.15.1" in candidate
    assert "faker==40.31.0" in candidate
    prepared.candidate_path.unlink()


def test_prepare_lock_cleans_candidate_on_keyboard_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    original = output_path.read_bytes()
    monkeypatch.setattr(compiler.subprocess, "run", _successful_resolver)
    real_snapshot = compiler._snapshot

    def interrupt_candidate_snapshot(path: Path) -> compiler.FileSnapshot:
        if path.name.endswith(".candidate"):
            raise KeyboardInterrupt
        return real_snapshot(path)

    monkeypatch.setattr(compiler, "_snapshot", interrupt_candidate_snapshot)

    with pytest.raises(KeyboardInterrupt):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )

    assert output_path.read_bytes() == original
    assert not tuple(tmp_path.glob(f".{surface.lockfile}.*.candidate"))
    assert not tuple(tmp_path.glob(f".{surface.lockfile}.*.resolver"))


def test_resolver_candidate_symlink_swap_cannot_overwrite_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    victim = tmp_path / "victim.txt"
    victim.write_text("must-stay-unchanged\n", encoding="utf-8")
    monkeypatch.setattr(compiler.subprocess, "run", _successful_resolver)
    real_validate = compiler._validate_candidate_delta

    def validate_then_swap(
        *,
        surface: surfaces.DependencySurface,
        baseline_text: str,
        candidate_text: str,
        upgrades: dict[str, str],
        graph_changes: frozenset[str],
        repo_root: Path,
    ) -> None:
        real_validate(
            surface=surface,
            baseline_text=baseline_text,
            candidate_text=candidate_text,
            upgrades=upgrades,
            graph_changes=graph_changes,
            repo_root=repo_root,
        )
        resolver_candidate = next(tmp_path.glob(f".{surface.lockfile}.*.resolver"))
        resolver_candidate.unlink()
        resolver_candidate.symlink_to(victim)

    monkeypatch.setattr(compiler, "_validate_candidate_delta", validate_then_swap)

    prepared = compiler._prepare_lock(
        repo_root=tmp_path,
        surface=surface,
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
        graph_changes=frozenset(),
        child_env={},
    )

    assert victim.read_text(encoding="utf-8") == "must-stay-unchanged\n"
    assert not tuple(tmp_path.glob(f".{surface.lockfile}.*.resolver"))
    assert not prepared.candidate_path.is_symlink()
    prepared.candidate_path.unlink()


def test_candidate_delta_allows_only_exact_reviewed_graph_changes(tmp_path: Path) -> None:
    surface = _write_test_profile(tmp_path)
    candidate = (tmp_path / surface.lockfile).read_text(encoding="utf-8")
    baseline = candidate + "transitive-package==1.0\n"

    compiler._validate_candidate_delta(
        surface=surface,
        baseline_text=baseline,
        candidate_text=candidate,
        upgrades={},
        graph_changes=frozenset({"transitive-package"}),
        repo_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="unused=.*other-package"):
        compiler._validate_candidate_delta(
            surface=surface,
            baseline_text=baseline,
            candidate_text=candidate,
            upgrades={},
            graph_changes=frozenset({"transitive-package", "other-package"}),
            repo_root=tmp_path,
        )
    with pytest.raises(RuntimeError, match="removal-only"):
        compiler._validate_candidate_delta(
            surface=surface,
            baseline_text=baseline,
            candidate_text=baseline + "new-package==1.0\n",
            upgrades={},
            graph_changes=frozenset({"new-package"}),
            repo_root=tmp_path,
        )


@pytest.mark.parametrize(
    "candidate_body,match",
    (
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.2.0\n",
            "unrelated package versions changed",
        ),
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.1.3\npip==26.1.2\n",
            "must not pin pip",
        ),
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\n",
            "dependency graph change is not exactly authorized",
        ),
        (
            "--index-url https://pypi.org/simple\n"
            "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.1.3\n",
            "unexpected resolver directive in candidate",
        ),
    ),
)
def test_prepare_lock_rejects_unsafe_candidate_without_mutating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_body: str,
    match: str,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    original = output_path.read_bytes()

    def write_candidate(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        _candidate_output_path(command).write_text(candidate_body, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(compiler.subprocess, "run", write_candidate)

    with pytest.raises(RuntimeError, match=match):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original
    assert not tuple(tmp_path.glob(f".{surface.lockfile}.*.candidate"))


def test_failed_resolver_and_source_mutation_leave_output_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    source_path = tmp_path / surface.compile_sources[0]
    original = output_path.read_bytes()

    def fail(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "resolver failed")

    monkeypatch.setattr(compiler.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="resolver failed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original

    def mutate_source(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        source_path.write_text(source_path.read_text(encoding="utf-8") + "# changed\n")
        return _successful_resolver(command)

    monkeypatch.setattr(compiler.subprocess, "run", mutate_source)
    with pytest.raises(RuntimeError, match="file changed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original


def test_atomic_source_replacement_never_reaches_resolver_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    source_path = tmp_path / surface.compile_sources[0]

    def replace_source(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        replacement = tmp_path / "replacement.in"
        replacement.write_text(
            "--extra-index-url https://pypi.org/simple\n"
            "coverage~=7.15.1\n"
            "faker~=40.31.0\n"
            "pytest~=9.1.3\n",
            encoding="utf-8",
        )
        replacement.replace(source_path)
        resolver_cwd = Path(str(kwargs["cwd"]))
        resolver_source = (resolver_cwd / surface.compile_sources[0]).read_text(encoding="utf-8")
        assert "pypi.org" not in resolver_source
        return _successful_resolver(command)

    monkeypatch.setattr(compiler.subprocess, "run", replace_source)

    with pytest.raises(RuntimeError, match="file changed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )


def test_constraint_identity_change_is_detected_even_when_content_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    constraint_path = tmp_path / "requirements.txt"
    original_constraint = constraint_path.read_bytes()

    def replace_constraint(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        replacement = tmp_path / "replacement.txt"
        replacement.write_bytes(original_constraint)
        replacement.replace(constraint_path)
        return _successful_resolver(command)

    monkeypatch.setattr(compiler.subprocess, "run", replace_constraint)

    with pytest.raises(RuntimeError, match="requirements.txt"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )


def test_runtime_and_dependent_profiles_require_separate_transactions() -> None:
    with pytest.raises(RuntimeError, match="compiled and committed before"):
        compiler._validate_profile_transaction(
            repo_root=REPO_ROOT,
            profiles=("runtime", "dev", "test"),
            graph_changes=frozenset(),
        )

    compiler._validate_profile_transaction(
        repo_root=REPO_ROOT,
        profiles=("runtime",),
        graph_changes=frozenset(),
    )
    with pytest.raises(RuntimeError, match="exact selected closed v1 admission"):
        compiler._validate_profile_transaction(
            repo_root=REPO_ROOT,
            profiles=("dev", "test"),
            graph_changes=frozenset({"example"}),
        )


def test_runtime_transaction_normalizes_constraint_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.138.1\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements-test.in").write_text(
        "-c ./requirements.txt\npytest==9.1.3\n",
        encoding="utf-8",
    )
    runtime_surface = _surface("runtime")
    test_surface = _surface("test")
    monkeypatch.setattr(
        compiler,
        "_profile_registry",
        lambda: {
            "runtime": runtime_surface,
            "test": test_surface,
        },
    )

    with pytest.raises(RuntimeError, match="compiled and committed before"):
        compiler._validate_profile_transaction(
            repo_root=tmp_path,
            profiles=("runtime", "test"),
            graph_changes=frozenset(),
        )


def _copy_graph_change_admission_repo(destination: Path) -> None:
    admission_path = destination / compiler.GRAPH_CHANGE_ADMISSION_PATH
    admission_path.parent.mkdir(parents=True)
    admission_path.write_bytes((REPO_ROOT / compiler.GRAPH_CHANGE_ADMISSION_PATH).read_bytes())
    seeded_lock = (
        "importlib-metadata==8.7.0\n"
        "opentelemetry-api==1.40.0\n"
        "opentelemetry-exporter-otlp-proto-common==1.40.0\n"
        "opentelemetry-exporter-otlp-proto-http==1.40.0\n"
        "opentelemetry-proto==1.40.0\n"
        "opentelemetry-sdk==1.40.0\n"
        "opentelemetry-semantic-conventions==0.61b0\n"
        "prometheus-client==0.24.1\n"
        "zipp==3.23.0\n"
    ).encode("utf-8")
    payload = json.loads(admission_path.read_text(encoding="utf-8"))
    for lockfile in (
        "requirements.txt",
        "requirements-docker-runtime.txt",
        "requirements-ci-lite.txt",
        "requirements-lock.txt",
    ):
        (destination / lockfile).write_bytes(seeded_lock)
    for baseline in payload["record"]["baselines"].values():
        baseline["sha256_bytes"] = list(hashlib.sha256(seeded_lock).digest())
    payload["record"]["runtime_target_observation"]["sha256_bytes"] = list(
        hashlib.sha256(_synthetic_runtime_target(destination)).digest()
    )
    admission_path.write_text(json.dumps(payload), encoding="utf-8")


def _synthetic_runtime_surface() -> surfaces.DependencySurface:
    return surfaces.DependencySurface(
        name="runtime",
        source_file="requirements.in",
        lockfile="requirements.txt",
        owner="Synthetic graph-admission test",
        use_case="Closed transition fixture",
        install_authority="Test only",
        compile_profile="runtime",
        compile_sources=("requirements.in",),
    )


def _render_semantic_runtime_target(repo_root: Path) -> bytes:
    runtime_path = repo_root / "requirements.txt"
    pins = compiler._exact_pin_map(
        runtime_path.read_text(encoding="utf-8"),
        label="test runtime baseline",
    )
    rows: list[str] = []
    for name, pin in sorted(pins.items()):
        if name in OBSERVABILITY_REMOVALS:
            continue
        extras = f"[{','.join(pin.extras)}]" if pin.extras else ""
        version = OBSERVABILITY_UPGRADES.get(name, pin.version)
        marker = f"; {pin.marker}" if pin.marker is not None else ""
        rows.append(f"{name}{extras}=={version}{marker}\n")
    return "".join(rows).encode("utf-8")


def _synthetic_runtime_target(repo_root: Path) -> bytes:
    return surfaces.render_governed_lock_header(_synthetic_runtime_surface()).encode(
        "utf-8"
    ) + _render_semantic_runtime_target(repo_root)


def _write_admitted_runtime_target(repo_root: Path) -> None:
    runtime_path = repo_root / "requirements.txt"
    runtime_path.write_bytes(_synthetic_runtime_target(repo_root))


def test_closed_graph_change_admission_authorizes_only_two_ordered_states(
    tmp_path: Path,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)

    runtime_admission = compiler._authorize_graph_changes(
        repo_root=tmp_path,
        profiles=("runtime",),
        upgrades=OBSERVABILITY_UPGRADES,
        graph_changes=OBSERVABILITY_REMOVALS,
        admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
    )
    assert runtime_admission is not None
    assert runtime_admission.profiles == ("runtime",)
    assert runtime_admission.removals == OBSERVABILITY_REMOVALS

    _write_admitted_runtime_target(tmp_path)
    dependent_admission = compiler._authorize_graph_changes(
        repo_root=tmp_path,
        profiles=("docker-runtime", "ci-lite", "aggregate"),
        upgrades=OBSERVABILITY_UPGRADES,
        graph_changes=OBSERVABILITY_REMOVALS,
        admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
    )
    assert dependent_admission is not None
    assert dependent_admission.profiles == ("docker-runtime", "ci-lite", "aggregate")

    with pytest.raises(RuntimeError, match="runtime baseline is stale"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )

    docker_lock = tmp_path / "requirements-docker-runtime.txt"
    docker_lock.write_bytes(docker_lock.read_bytes() + b"# consumed\n")
    with pytest.raises(RuntimeError, match="docker-runtime baseline is stale"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("docker-runtime", "ci-lite", "aggregate"),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


def test_closed_graph_change_admission_rechecks_captured_plan_identity(
    tmp_path: Path,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    runtime_path = tmp_path / "requirements.txt"
    stale_runtime_capture = compiler._capture_file(runtime_path)
    _write_admitted_runtime_target(tmp_path)
    admission = compiler._authorize_graph_changes(
        repo_root=tmp_path,
        profiles=("docker-runtime", "ci-lite", "aggregate"),
        upgrades=OBSERVABILITY_UPGRADES,
        graph_changes=OBSERVABILITY_REMOVALS,
        admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
    )
    assert admission is not None
    surface = _surface("docker-runtime")
    output_path = tmp_path / surface.lockfile
    plan = compiler.LockInputPlan(
        surface=surface,
        output_path=output_path,
        output_capture=compiler._capture_file(output_path),
        source_captures=((runtime_path, compiler._capture_file(runtime_path)),),
        expected_artifacts=frozenset(),
    )
    compiler._assert_plans_match_graph_change_admission((plan,), admission)

    stale_source_plan = compiler.LockInputPlan(
        surface=surface,
        output_path=output_path,
        output_capture=plan.output_capture,
        source_captures=((runtime_path, stale_runtime_capture),),
        expected_artifacts=frozenset(),
    )
    with pytest.raises(RuntimeError, match="runtime constraint does not match"):
        compiler._assert_plans_match_graph_change_admission((stale_source_plan,), admission)

    wrong_baseline_plan = compiler.LockInputPlan(
        surface=surface,
        output_path=output_path,
        output_capture=compiler._capture_file(runtime_path),
        source_captures=plan.source_captures,
        expected_artifacts=frozenset(),
    )
    with pytest.raises(RuntimeError, match="does not match.*admission baseline"):
        compiler._assert_plans_match_graph_change_admission((wrong_baseline_plan,), admission)


def test_tx1_rejects_semantically_equal_candidate_with_wrong_byte_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    (tmp_path / "requirements.in").write_text(
        "\n".join(
            f"{package}>={version}" for package, version in sorted(OBSERVABILITY_UPGRADES.items())
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_path = tmp_path / "requirements.txt"
    baseline = runtime_path.read_bytes()
    semantic_target_with_byte_drift = (
        _render_semantic_runtime_target(tmp_path) + b"# semantically inert candidate drift\n"
    )
    admitted_target = _synthetic_runtime_target(tmp_path)
    assert compiler._exact_pin_map(
        semantic_target_with_byte_drift.decode("utf-8"), label="drifted runtime candidate"
    ) == compiler._exact_pin_map(admitted_target.decode("utf-8"), label="admitted runtime target")
    admission = compiler._authorize_graph_changes(
        repo_root=tmp_path,
        profiles=("runtime",),
        upgrades=OBSERVABILITY_UPGRADES,
        graph_changes=OBSERVABILITY_REMOVALS,
        admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
    )
    assert admission is not None

    def write_semantically_equal_candidate(
        command: list[str], **_: object
    ) -> subprocess.CompletedProcess[str]:
        _candidate_output_path(command).write_bytes(semantic_target_with_byte_drift)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(compiler.subprocess, "run", write_semantically_equal_candidate)
    with pytest.raises(RuntimeError, match="exact admitted TX1 target"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=_synthetic_runtime_surface(),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            graph_admission=admission,
            child_env={},
        )

    assert runtime_path.read_bytes() == baseline
    assert not tuple(tmp_path.glob(".requirements.txt.*.candidate"))
    assert not tuple(tmp_path.glob(".requirements.txt.*.resolver"))


@pytest.mark.parametrize(
    "profiles",
    (
        ("aggregate", "ci-lite", "docker-runtime"),
        ("docker-runtime", "ci-lite"),
        ("runtime", "docker-runtime", "ci-lite", "aggregate"),
        ("runtime", "runtime"),
    ),
)
def test_closed_graph_change_admission_rejects_permutation_subset_and_combination(
    tmp_path: Path,
    profiles: tuple[str, ...],
) -> None:
    _copy_graph_change_admission_repo(tmp_path)

    with pytest.raises(RuntimeError, match="exact ordered transaction"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=profiles,
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


def test_closed_graph_change_admission_rejects_wrong_selector_upgrades_and_delta(
    tmp_path: Path,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    with pytest.raises(RuntimeError, match="repository-owned closed v1 admission"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id="other-admission",
        )
    wrong_upgrades = dict(OBSERVABILITY_UPGRADES)
    wrong_upgrades["prometheus-client"] = "0.26.0"
    with pytest.raises(RuntimeError, match="exact admitted seven targets"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=wrong_upgrades,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )
    with pytest.raises(RuntimeError, match="does not match the exact admitted removals"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=frozenset({"zipp"}),
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )
    with pytest.raises(RuntimeError, match="forbidden when no graph change"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=frozenset(),
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


def test_closed_graph_change_admission_rejects_semantically_equal_runtime_byte_drift(
    tmp_path: Path,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    _write_admitted_runtime_target(tmp_path)
    runtime_path = tmp_path / "requirements.txt"
    exact_pins = compiler._exact_pin_map(
        runtime_path.read_text(encoding="utf-8"), label="exact admitted runtime"
    )
    runtime_path.write_bytes(runtime_path.read_bytes() + b"# semantically inert byte drift\n")
    assert (
        compiler._exact_pin_map(
            runtime_path.read_text(encoding="utf-8"), label="drifted admitted runtime"
        )
        == exact_pins
    )

    with pytest.raises(RuntimeError, match="exact admitted runtime target"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("docker-runtime", "ci-lite", "aggregate"),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


@pytest.mark.parametrize("malformation", ("duplicate", "unknown", "wrong-type"))
def test_closed_graph_change_admission_rejects_malformed_schema(
    tmp_path: Path,
    malformation: str,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    path = tmp_path / compiler.GRAPH_CHANGE_ADMISSION_PATH
    if malformation == "duplicate":
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace(
                '"schema":',
                '"schema":"duplicate","schema":',
                1,
            ),
            encoding="utf-8",
        )
        expected = "Duplicate graph-change admission field"
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if malformation == "unknown":
            payload["unknown"] = True
            expected = "unknown=.*unknown"
        else:
            payload["record"]["profile_universe"] = "runtime"
            expected = "array of strings"
        path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match=expected):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


@pytest.mark.parametrize("path_kind", ("symlink", "hardlink", "directory"))
def test_closed_graph_change_admission_rejects_unsafe_path_identity(
    tmp_path: Path,
    path_kind: str,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    path = tmp_path / compiler.GRAPH_CHANGE_ADMISSION_PATH
    saved = tmp_path / "saved-admission.json"
    path.replace(saved)
    if path_kind == "symlink":
        path.symlink_to(saved)
        expected = "regular non-symlink"
    elif path_kind == "hardlink":
        os.link(saved, path)
        expected = "must not be hardlinked"
    else:
        path.mkdir()
        expected = "regular non-symlink"

    with pytest.raises(RuntimeError, match=expected):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


def test_closed_graph_change_admission_detects_replacement_after_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_graph_change_admission_repo(tmp_path)
    path = tmp_path / compiler.GRAPH_CHANGE_ADMISSION_PATH
    original_capture = compiler._capture_file
    replaced = False

    def capture_then_replace(candidate: Path) -> compiler.FileCapture:
        nonlocal replaced
        capture = original_capture(candidate)
        if candidate == path and not replaced:
            replaced = True
            replacement = path.with_suffix(".replacement")
            replacement.write_bytes(capture.content)
            replacement.replace(path)
        return capture

    monkeypatch.setattr(compiler, "_capture_file", capture_then_replace)
    with pytest.raises(RuntimeError, match="changed during lock compilation"):
        compiler._authorize_graph_changes(
            repo_root=tmp_path,
            profiles=("runtime",),
            upgrades=OBSERVABILITY_UPGRADES,
            graph_changes=OBSERVABILITY_REMOVALS,
            admission_id=compiler.GRAPH_CHANGE_ADMISSION_ID,
        )


def test_graph_change_rejection_happens_before_network_or_input_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_: object, **__: object) -> object:
        raise AssertionError("graph-change rejection must precede capture and network")

    monkeypatch.setattr(compiler, "_capture_lock_input_plan", unexpected_call)
    monkeypatch.setattr(compiler, "_private_proxy_child_env", unexpected_call)

    with pytest.raises(RuntimeError, match="repository-owned closed v1 admission"):
        compiler._compile_selected_profiles_locked(
            repo_root=REPO_ROOT,
            profiles=("test",),
            upgrades={},
            graph_changes=frozenset({"new-package"}),
            environment={},
        )


def _stub_two_phase_pipeline(
    *,
    monkeypatch: pytest.MonkeyPatch,
    prepared_by_profile: dict[str, compiler.PreparedLock],
) -> None:
    plans = {
        profile: compiler.LockInputPlan(
            surface=prepared.surface,
            output_path=prepared.output_path,
            output_capture=compiler._capture_file(prepared.output_path),
            source_captures=(),
            expected_artifacts=frozenset(),
        )
        for profile, prepared in prepared_by_profile.items()
    }
    monkeypatch.setattr(
        compiler,
        "_capture_lock_input_plan",
        lambda *, surface, **_kwargs: plans[str(surface.compile_profile)],
    )
    monkeypatch.setattr(
        compiler,
        "_private_proxy_child_env",
        lambda _environment, *, resolver_home: {"HOME": str(resolver_home)},
    )
    monkeypatch.setattr(
        compiler,
        "_collect_private_proxy_artifact_hashes",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(compiler, "_download_profile_wheels", lambda **_kwargs: None)
    monkeypatch.setattr(compiler, "_validate_wheelhouse", lambda **_kwargs: {})
    monkeypatch.setattr(
        compiler,
        "_create_profile_wheelhouse_views",
        lambda *, plans, views_root, **_kwargs: {
            str(plan.surface.compile_profile): compiler.ProfileWheelhouse(
                path=views_root,
                artifacts=(),
            )
            for plan in plans
        },
    )
    monkeypatch.setattr(compiler, "_offline_compile_env", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        compiler,
        "_prepare_lock",
        lambda **kwargs: prepared_by_profile[str(kwargs["surface"].compile_profile)],
    )


def test_multi_lock_replacement_rolls_back_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_surfaces = (_surface("test"), _surface("dev"))
    prepared_by_profile: dict[str, compiler.PreparedLock] = {}
    for index, surface in enumerate(selected_surfaces):
        output_path = tmp_path / surface.lockfile
        output_path.write_text(f"baseline-{index}\n", encoding="utf-8")
        candidate_path = tmp_path / f".{surface.lockfile}.candidate"
        candidate_path.write_text(f"candidate-{index}\n", encoding="utf-8")
        prepared_by_profile[str(surface.compile_profile)] = compiler.PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=candidate_path,
            source_snapshots=(),
            output_snapshot=compiler._snapshot(output_path),
            candidate_snapshot=compiler._snapshot(candidate_path),
            baseline_bytes=output_path.read_bytes(),
        )

    monkeypatch.setattr(
        compiler,
        "_profile_registry",
        lambda: {str(surface.compile_profile): surface for surface in selected_surfaces},
    )
    _stub_two_phase_pipeline(
        monkeypatch=monkeypatch,
        prepared_by_profile=prepared_by_profile,
    )
    monkeypatch.setattr(compiler, "_fsync_directory", lambda _path: None)
    real_replace = os.replace
    replacement_count = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacement_count
        replacement_count += 1
        if replacement_count == 2:
            raise OSError("simulated second replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(compiler.os, "replace", fail_second_replace)

    with pytest.raises(RuntimeError, match="rolled back"):
        compiler.compile_selected_profiles(
            repo_root=tmp_path,
            profiles=("test", "dev"),
            upgrades={},
            graph_changes=frozenset(),
            environment={},
        )

    assert (tmp_path / "requirements-test.txt").read_text(encoding="utf-8") == "baseline-0\n"
    assert (tmp_path / "requirements-dev.txt").read_text(encoding="utf-8") == "baseline-1\n"


@pytest.mark.parametrize("interrupt_after", (1, 2))
def test_multi_lock_replacement_rolls_back_on_keyboard_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt_after: int,
) -> None:
    selected_surfaces = (_surface("test"), _surface("dev"))
    prepared_by_profile: dict[str, compiler.PreparedLock] = {}
    for index, surface in enumerate(selected_surfaces):
        output_path = tmp_path / surface.lockfile
        output_path.write_text(f"baseline-{index}\n", encoding="utf-8")
        candidate_path = tmp_path / f".{surface.lockfile}.candidate"
        candidate_path.write_text(f"candidate-{index}\n", encoding="utf-8")
        prepared_by_profile[str(surface.compile_profile)] = compiler.PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=candidate_path,
            source_snapshots=(),
            output_snapshot=compiler._snapshot(output_path),
            candidate_snapshot=compiler._snapshot(candidate_path),
            baseline_bytes=output_path.read_bytes(),
        )

    monkeypatch.setattr(
        compiler,
        "_profile_registry",
        lambda: {str(surface.compile_profile): surface for surface in selected_surfaces},
    )
    _stub_two_phase_pipeline(
        monkeypatch=monkeypatch,
        prepared_by_profile=prepared_by_profile,
    )
    monkeypatch.setattr(compiler, "_fsync_directory", lambda _path: None)
    real_replace = os.replace
    replacement_count = 0

    def interrupt_after_replace(source: Path, destination: Path) -> None:
        nonlocal replacement_count
        real_replace(source, destination)
        if source.name.endswith(".candidate"):
            replacement_count += 1
            if replacement_count == interrupt_after:
                raise KeyboardInterrupt

    monkeypatch.setattr(compiler.os, "replace", interrupt_after_replace)

    with pytest.raises(KeyboardInterrupt):
        compiler.compile_selected_profiles(
            repo_root=tmp_path,
            profiles=("test", "dev"),
            upgrades={},
            graph_changes=frozenset(),
            environment={},
        )

    for index, surface in enumerate(selected_surfaces):
        assert (tmp_path / surface.lockfile).read_text(encoding="utf-8") == f"baseline-{index}\n"
        assert not (tmp_path / f".{surface.lockfile}.candidate").exists()


def test_candidate_symlink_swap_before_replace_fails_and_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface("test")
    output_path = tmp_path / surface.lockfile
    output_path.write_text("baseline\n", encoding="utf-8")
    candidate_path = tmp_path / f".{surface.lockfile}.candidate"
    candidate_path.write_text("candidate\n", encoding="utf-8")
    victim = tmp_path / "victim.txt"
    victim.write_text("must-stay-unchanged\n", encoding="utf-8")
    prepared = compiler.PreparedLock(
        surface=surface,
        output_path=output_path,
        candidate_path=candidate_path,
        source_snapshots=(),
        output_snapshot=compiler._snapshot(output_path),
        candidate_snapshot=compiler._snapshot(candidate_path),
        baseline_bytes=output_path.read_bytes(),
    )
    monkeypatch.setattr(compiler, "_profile_registry", lambda: {"test": surface})
    _stub_two_phase_pipeline(
        monkeypatch=monkeypatch,
        prepared_by_profile={"test": prepared},
    )
    monkeypatch.setattr(compiler, "_fsync_directory", lambda _path: None)
    real_replace = os.replace

    def swap_candidate(source: Path, destination: Path) -> None:
        if source == candidate_path:
            source.unlink()
            source.symlink_to(victim)
        real_replace(source, destination)

    monkeypatch.setattr(compiler.os, "replace", swap_candidate)

    with pytest.raises(RuntimeError, match="rolled back"):
        compiler.compile_selected_profiles(
            repo_root=tmp_path,
            profiles=("test",),
            upgrades={},
            graph_changes=frozenset(),
            environment={},
        )

    assert output_path.read_text(encoding="utf-8") == "baseline\n"
    assert not output_path.is_symlink()
    assert victim.read_text(encoding="utf-8") == "must-stay-unchanged\n"


def test_compiler_transaction_lock_rejects_concurrent_governed_writer_across_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_tmpdir = tmp_path / "ambient-a"
    second_tmpdir = tmp_path / "ambient-b"
    first_tmpdir.mkdir()
    second_tmpdir.mkdir()
    monkeypatch.setenv("TMPDIR", str(first_tmpdir))
    monkeypatch.setattr(compiler.tempfile, "gettempdir", lambda: str(first_tmpdir))
    with compiler._compiler_transaction_lock(tmp_path):
        monkeypatch.setenv("TMPDIR", str(second_tmpdir))
        monkeypatch.setattr(compiler.tempfile, "gettempdir", lambda: str(second_tmpdir))
        with pytest.raises(RuntimeError, match="already running"):
            with compiler._compiler_transaction_lock(tmp_path):
                pytest.fail("a second governed compiler acquired the transaction lock")


def test_compiler_transaction_lock_has_one_cross_process_tmpdir_namespace(
    tmp_path: Path,
) -> None:
    first_tmpdir = tmp_path / "ambient-a"
    second_tmpdir = tmp_path / "ambient-b"
    first_tmpdir.mkdir()
    second_tmpdir.mkdir()
    first_probe = (
        "import sys; from pathlib import Path; "
        "from scripts.ci.compile_locked_python_requirements import "
        "_compiler_transaction_lock; "
        "lock=_compiler_transaction_lock(Path(sys.argv[1])); "
        "lock.__enter__(); print('ACQUIRED', flush=True); "
        "sys.stdin.read(1); lock.__exit__(None, None, None)"
    )
    second_probe = (
        "import sys; from pathlib import Path; "
        "from scripts.ci.compile_locked_python_requirements import "
        "_compiler_transaction_lock; "
        "lock=_compiler_transaction_lock(Path(sys.argv[1])); lock.__enter__()"
    )
    first_env = {**os.environ, "TMPDIR": str(first_tmpdir)}
    second_env = {**os.environ, "TMPDIR": str(second_tmpdir)}
    first = subprocess.Popen(  # nosec B603: current interpreter and fixed local lock probe (remove-by: 2027-01-31, ref: PR-2142)
        [sys.executable, "-c", first_probe, str(tmp_path)],
        cwd=REPO_ROOT,
        env=first_env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert first.stdout is not None
    assert first.stdin is not None
    try:
        assert first.stdout.readline().strip() == "ACQUIRED"
        second = subprocess.run(  # nosec B603: current interpreter and fixed local lock probe (remove-by: 2027-01-31, ref: PR-2142)
            [sys.executable, "-c", second_probe, str(tmp_path)],
            cwd=REPO_ROOT,
            env=second_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert second.returncode != 0
        assert "already running" in second.stderr
    finally:
        first.stdin.write("\n")
        first.stdin.flush()
        first.communicate(timeout=10)


def test_prepared_lock_rejects_rollback_bytes_from_another_snapshot(tmp_path: Path) -> None:
    surface = _surface("test")
    output_path = tmp_path / surface.lockfile
    output_path.write_text("captured-baseline\n", encoding="utf-8")
    candidate_path = tmp_path / f".{surface.lockfile}.candidate"
    candidate_path.write_text("candidate\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Rollback baseline bytes"):
        compiler.PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=candidate_path,
            source_snapshots=(),
            output_snapshot=compiler._snapshot(output_path),
            candidate_snapshot=compiler._snapshot(candidate_path),
            baseline_bytes=b"stale-pre-race-baseline\n",
        )


def test_registry_paths_must_be_regular_non_symlink_files(tmp_path: Path) -> None:
    real_file = tmp_path / "real.in"
    real_file.write_text("example==1.0\n", encoding="utf-8")
    symlink = tmp_path / "requirements-test.in"
    symlink.symlink_to(real_file)

    with pytest.raises(RuntimeError, match="non-symlink"):
        compiler._validated_repo_file(tmp_path, "requirements-test.in")
    with pytest.raises(RuntimeError, match="repo-relative"):
        compiler._validated_repo_file(tmp_path, "../requirements-test.in")


def test_dependency_capture_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    fifo_path = tmp_path / "requirements-test.in"
    os.mkfifo(fifo_path, 0o600)
    probe = (
        "import sys; from pathlib import Path; "
        "from scripts.ci.compile_locked_python_requirements import _capture_file; "
        "_capture_file(Path(sys.argv[1]))"
    )

    result = subprocess.run(  # nosec B603: current interpreter and fixed local FIFO probe (remove-by: 2027-01-31, ref: PR-2142)
        [sys.executable, "-c", probe, str(fifo_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=2,
    )

    assert result.returncode != 0
    assert "regular file" in result.stderr


def test_source_manifest_rejects_direct_urls_and_unowned_directives(tmp_path: Path) -> None:
    source = tmp_path / "requirements-test.in"
    source.write_text(
        "example @ https://example.invalid/example.whl\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Direct URL requirements are forbidden"):
        compiler._validate_source_manifest(tmp_path, source)

    source.write_text("--find-links /tmp/wheels\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Unsupported resolver directive"):
        compiler._validate_source_manifest(tmp_path, source)

    source.write_text(
        "--extra-index-url https://download.pytorch.org/whl/cpu\n",
        encoding="utf-8",
    )
    assert not _surface("rag-vector-cpu").allow_lock_directives
    with pytest.raises(RuntimeError, match="Unsupported resolver directive"):
        compiler._validate_source_manifest(tmp_path, source)


def test_direct_helper_invocation_requires_make_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(compiler.MAKE_AUTHORITY_ENV, raising=False)

    with pytest.raises(RuntimeError, match="make requirements-locks"):
        compiler.main()
