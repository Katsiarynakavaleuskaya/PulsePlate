"""Tests for the Python dependency surface contract validator."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.ci import check_python_dependency_surfaces as surfaces
from scripts.ci import compile_locked_python_requirements as compiler

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_INDEX = "https://packages.pulseplate.app/root/pulseplate/+simple/"


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
            (root / surface.source_file).write_text("example>=1.0.0\n", encoding="utf-8")
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

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "Unknown root requirements surfaces are not in the registry: ['requirements-surprise.txt']."
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
        surfaces.render_governed_lock_header(runtime_surface) + "fastapi>=0.122.0\n",
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


def test_dependency_surface_contract_rejects_missing_test_direct_owner(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(tmp_path, "requirements-test.in", "pytest>=9.1.1")
    _append_requirement(tmp_path, "requirements-test.txt", "pytest==9.1.1")
    _remove_requirement(tmp_path, "requirements-test.txt", "pytest==9.1.1")

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "requirements-test.txt: missing direct packages from requirements-test.in: ['pytest']."
    ]


def test_dependency_surface_contract_rejects_missing_dev_direct_owner(tmp_path: Path) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(tmp_path, "requirements-dev.in", "mypy>=2.2.0")
    _append_requirement(tmp_path, "requirements-dev.txt", "mypy==2.2.0")
    _append_requirement(tmp_path, "requirements-lock.txt", "mypy==2.2.0")
    _remove_requirement(tmp_path, "requirements-dev.txt", "mypy==2.2.0")

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "requirements-dev.txt: missing direct packages from requirements-dev.in: ['mypy']."
    ]


def test_dependency_surface_contract_rejects_missing_aggregate_direct_owner(
    tmp_path: Path,
) -> None:
    _write_valid_contract_repo(tmp_path)
    _append_requirement(tmp_path, "requirements-dev.in", "bandit>=1.9.4")
    _append_requirement(tmp_path, "requirements-dev.txt", "bandit==1.9.4")
    _append_requirement(tmp_path, "requirements-lock.txt", "bandit==1.9.4")
    _remove_requirement(tmp_path, "requirements-lock.txt", "bandit==1.9.4")

    errors = surfaces.validate_repo(tmp_path)

    assert errors == [
        "requirements-lock.txt: missing direct packages from requirements.in + "
        "requirements-dev.in: ['bandit']."
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
    assert "$(LOCK_PROFILES)" not in makefile
    assert "$(UPGRADE_PACKAGES)" not in makefile
    assert "$(GRAPH_CHANGE_PACKAGES)" not in makefile

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

    child_env = compiler._private_proxy_child_env(
        {"HOME": "/tmp/home", compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX}
    )

    assert child_env["PIP_INDEX_URL"] == APPROVED_INDEX
    assert child_env["PIP_CONFIG_FILE"] == os.devnull
    assert child_env["PIP_NO_INPUT"] == "1"
    assert "PIP_EXTRA_INDEX_URL" not in child_env
    assert inspected_netrc_paths == [Path("/tmp/home/.netrc")]

    with pytest.raises((RuntimeError, ValueError)):
        compiler._private_proxy_child_env(
            {compiler.APPROVED_INDEX_ENV_VAR: "https://pypi.org/simple/"}
        )
    with pytest.raises((RuntimeError, ValueError)):
        credentialed_index = (
            "https://"
            + ":".join(("user", "placeholder"))
            + "@packages.pulseplate.app/root/pulseplate/+simple/"
        )
        compiler._private_proxy_child_env({compiler.APPROVED_INDEX_ENV_VAR: credentialed_index})
    with pytest.raises(RuntimeError, match="PIP_FIND_LINKS"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PIP_FIND_LINKS": "/tmp/wheels",
            }
        )
    with pytest.raises(RuntimeError, match="does not consume it"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PULSEPLATE_PYTHON_NETRC": "/tmp/custom.netrc",
            }
        )


def test_private_proxy_environment_rejects_root_netrc_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in compiler.AMBIENT_RESOLVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("PULSEPLATE_PYTHON_TRUSTED_HOST", raising=False)

    def reject_root(_host: str, *, netrc_file: Path | None = None) -> None:
        raise ValueError("root_devpi_credentials: root devpi credentials are forbidden")

    monkeypatch.setattr(compiler, "basic_auth_from_netrc", reject_root)

    with pytest.raises(ValueError, match="root_devpi_credentials"):
        compiler._private_proxy_child_env({compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX})


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


def test_candidate_delta_allows_only_exact_reviewed_graph_changes(tmp_path: Path) -> None:
    surface = _write_test_profile(tmp_path)
    baseline = (tmp_path / surface.lockfile).read_text(encoding="utf-8")
    candidate = baseline + "new-direct-package==1.0\n"

    compiler._validate_candidate_delta(
        surface=surface,
        baseline_text=baseline,
        candidate_text=candidate,
        upgrades={},
        graph_changes=frozenset({"new-direct-package"}),
        repo_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="unused=.*other-package"):
        compiler._validate_candidate_delta(
            surface=surface,
            baseline_text=baseline,
            candidate_text=candidate,
            upgrades={},
            graph_changes=frozenset({"new-direct-package", "other-package"}),
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
    with pytest.raises(RuntimeError, match="exactly one"):
        compiler._validate_profile_transaction(
            repo_root=REPO_ROOT,
            profiles=("dev", "test"),
            graph_changes=frozenset({"example"}),
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
    monkeypatch.setattr(compiler, "_private_proxy_child_env", lambda _environment: {})
    monkeypatch.setattr(
        compiler,
        "_prepare_lock",
        lambda **kwargs: prepared_by_profile[str(kwargs["surface"].compile_profile)],
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


def test_registry_paths_must_be_regular_non_symlink_files(tmp_path: Path) -> None:
    real_file = tmp_path / "real.in"
    real_file.write_text("example==1.0\n", encoding="utf-8")
    symlink = tmp_path / "requirements-test.in"
    symlink.symlink_to(real_file)

    with pytest.raises(RuntimeError, match="non-symlink"):
        compiler._validated_repo_file(tmp_path, "requirements-test.in")
    with pytest.raises(RuntimeError, match="repo-relative"):
        compiler._validated_repo_file(tmp_path, "../requirements-test.in")


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

    cpu_index = "--extra-index-url https://download.pytorch.org/whl/cpu"
    source.write_text(f"{cpu_index}\n", encoding="utf-8")
    assert (
        compiler._validate_source_manifest(
            tmp_path,
            source,
            allow_directives=(cpu_index,),
        )
        == ()
    )


def test_direct_helper_invocation_requires_make_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(compiler.MAKE_AUTHORITY_ENV, raising=False)

    with pytest.raises(RuntimeError, match="make requirements-locks"):
        compiler.main()
