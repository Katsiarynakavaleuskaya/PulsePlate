from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import scripts.ci.check_artifact_reader_contracts as artifact_guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_runtime_sources_pass_artifact_reader_guard() -> None:
    findings, errors = artifact_guard.collect_artifact_read_findings(REPO_ROOT)

    assert findings == []
    assert errors == []


def test_artifact_boundary_doc_passes_contract() -> None:
    text = (REPO_ROOT / "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md").read_text(
        encoding="utf-8"
    )

    assert artifact_guard.validate_artifact_boundary_doc(text) == []


def test_artifact_guard_rejects_direct_read_text() -> None:
    source = 'Path("artifacts/orchestration/packet.json").read_text(encoding="utf-8")\n'

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [
        "app/unsafe.py:1: read_text reads local artifacts/orchestration"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            textwrap.dedent("""
                import pathlib

                pathlib.Path("artifacts/orchestration/packet.json").read_text()
                """),
            "app/unsafe.py:4: read_text reads local artifacts/orchestration",
        ),
        (
            textwrap.dedent("""
                from pathlib import Path as P

                P("artifacts/agent_runs/report.json").read_text()
                """),
            "app/unsafe.py:4: read_text reads local artifacts/agent_runs",
        ),
        (
            textwrap.dedent("""
                from pathlib import Path

                Path("artifacts").joinpath("security_lab", "report.json").read_text()
                """),
            "app/unsafe.py:4: read_text reads local artifacts/security_lab",
        ),
    ],
)
def test_artifact_guard_rejects_pathlib_variants(
    source: str,
    expected: str,
) -> None:
    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [expected]


def test_artifact_guard_rejects_builtin_open_default_read() -> None:
    source = 'open("artifacts/agent_runs/summary.json")\n'

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="core/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [
        "core/unsafe.py:1: open reads local artifacts/agent_runs"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'open(file="artifacts/agent_runs/summary.json")\n',
            "core/unsafe.py:1: open reads local artifacts/agent_runs",
        ),
        (
            'os.listdir(path="artifacts/security_lab")\n',
            "core/unsafe.py:1: os.listdir reads local artifacts/security_lab",
        ),
        (
            'os.scandir(path="artifacts/orchestration")\n',
            "core/unsafe.py:1: os.scandir reads local artifacts/orchestration",
        ),
        (
            'glob.glob(pathname="artifacts/orchestration/*.json")\n',
            "core/unsafe.py:1: glob.glob reads local artifacts/orchestration",
        ),
        (
            'glob.iglob(pathname="artifacts/agent_runs/*.json")\n',
            "core/unsafe.py:1: glob.iglob reads local artifacts/agent_runs",
        ),
    ],
)
def test_artifact_guard_rejects_keyword_path_arguments(
    source: str,
    expected: str,
) -> None:
    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="core/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [expected]


def test_artifact_guard_rejects_read_write_open_modes() -> None:
    source = 'Path("artifacts/security_lab/report.json").open("a+")\n'

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="providers/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [
        "providers/unsafe.py:1: open reads local artifacts/security_lab"
    ]


def test_artifact_guard_allows_write_only_artifact_paths() -> None:
    source = textwrap.dedent("""
        from pathlib import Path

        audit_path = Path("artifacts/orchestration/agent_control_audit.jsonl")
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.open("a", encoding="utf-8")
        audit_path.write_text("safe write-only example", encoding="utf-8")
        """)

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/security/audit.py",
    )

    assert findings == []
    assert errors == []


def test_artifact_guard_rejects_existence_and_enumeration() -> None:
    source = textwrap.dedent("""
        from pathlib import Path
        import os

        root = Path("artifacts") / "orchestration"
        root.exists()
        os.listdir("artifacts/security_lab")
        """)

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [
        "app/unsafe.py:6: exists reads local artifacts/orchestration",
        "app/unsafe.py:7: os.listdir reads local artifacts/security_lab",
    ]


def test_artifact_guard_rejects_glob_patterns() -> None:
    source = textwrap.dedent("""
        import glob

        glob.glob("artifacts/orchestration/*.json")
        """)

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="core/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [
        "core/unsafe.py:4: glob.glob reads local artifacts/orchestration"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'os.path.exists("artifacts/orchestration/packet.json")\n',
            "app/unsafe.py:1: os.path.exists reads local artifacts/orchestration",
        ),
        (
            'os.path.isfile(path="artifacts/agent_runs/report.json")\n',
            "app/unsafe.py:1: os.path.isfile reads local artifacts/agent_runs",
        ),
        (
            'os.path.isdir("artifacts/security_lab")\n',
            "app/unsafe.py:1: os.path.isdir reads local artifacts/security_lab",
        ),
    ],
)
def test_artifact_guard_rejects_os_path_existence_checks(
    source: str,
    expected: str,
) -> None:
    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/unsafe.py",
    )

    assert errors == []
    assert [finding.display() for finding in findings] == [expected]


def test_artifact_guard_ignores_comments_and_plain_strings() -> None:
    source = textwrap.dedent("""
        "artifacts/orchestration/not-read.json"
        # Path("artifacts/orchestration/not-read.json").read_text()
        def label():
            return "artifacts/agent_runs/report.json"
        """)

    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        source,
        rel_path="app/safe.py",
    )

    assert findings == []
    assert errors == []


def test_artifact_guard_fails_closed_on_missing_target(tmp_path: Path) -> None:
    (tmp_path / "legacy_app.py").write_text("", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "core").mkdir()

    findings, errors = artifact_guard.collect_artifact_read_findings(tmp_path)

    assert findings == []
    assert errors == ["providers: configured runtime scan target missing"]


def test_artifact_guard_fails_closed_on_syntax_error() -> None:
    findings, errors = artifact_guard.collect_artifact_read_findings_for_source(
        "def broken(:\n",
        rel_path="app/broken.py",
    )

    assert findings == []
    assert errors == ["app/broken.py:1: syntax error: invalid syntax"]


def test_artifact_boundary_doc_rejects_missing_marker() -> None:
    text = (REPO_ROOT / "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md").read_text(
        encoding="utf-8"
    )
    text = text.replace("<!-- ARTIFACT_BOUNDARY_RUNTIME_READS_ALLOWED: false -->\n", "")

    errors = artifact_guard.validate_artifact_boundary_doc(text)

    assert (
        "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md: missing marker "
        "ARTIFACT_BOUNDARY_RUNTIME_READS_ALLOWED"
    ) in errors


def test_artifact_repo_validation_rejects_empty_doc(tmp_path: Path) -> None:
    (tmp_path / "legacy_app.py").write_text("", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "core").mkdir()
    (tmp_path / "providers").mkdir()
    doc_path = tmp_path / "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("", encoding="utf-8")

    errors = artifact_guard.validate_repo(tmp_path)

    assert (
        "docs/architecture/ARTIFACT_VALIDATION_BOUNDARY.md: "
        "missing marker ARTIFACT_BOUNDARY_STATUS"
    ) in errors


def test_artifact_guard_cli_passes(capsys) -> None:
    exit_code = artifact_guard.main(["--repo-root", str(REPO_ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "artifact validation boundary guard passed" in captured.out
