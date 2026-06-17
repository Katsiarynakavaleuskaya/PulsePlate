"""Tests for deterministic Bandit report summarization."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "scripts" / "ci" / "summarize_bandit_report.py"


def _finding(
    *,
    severity: str,
    confidence: str = "HIGH",
    test_id: str = "B602",
    filename: str = "scripts/example.py",
    line_number: int = 10,
    issue_text: str = "example finding",
) -> dict[str, object]:
    return {
        "filename": filename,
        "issue_confidence": confidence,
        "issue_severity": severity,
        "issue_text": issue_text,
        "line_number": line_number,
        "test_id": test_id,
    }


def _write_report(path: Path, results: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"results": results}), encoding="utf-8")


def _run_helper(report: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(HELPER),
            "--report",
            str(report),
            "--github-annotations",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_missing_report_fails_closed(tmp_path: Path) -> None:
    result = _run_helper(tmp_path / "missing.json", "--fail-on-high")

    assert result.returncode == 2
    assert "::error::Bandit report not found" in result.stdout
    assert "::warning::" not in result.stdout


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    report.write_text("{not valid", encoding="utf-8")

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 2
    assert "::error::Bandit report is not valid JSON" in result.stdout
    assert "Traceback" not in result.stderr


def test_malformed_schema_fails_closed(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    report.write_text(json.dumps({"results": {"bad": "shape"}}), encoding="utf-8")

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 2
    assert ".results` must be a list" in result.stdout


def test_high_severity_findings_fail_even_with_lower_findings(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [
            _finding(severity="MEDIUM", filename="scripts/medium.py", line_number=5),
            _finding(
                severity="HIGH",
                confidence="MEDIUM",
                test_id="B999",
                filename="app/security/high.py",
                line_number=12,
                issue_text="high risk",
            ),
            _finding(severity="LOW", filename="legacy_app.py", line_number=20),
        ],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 1
    assert "::error::Bandit found 1 HIGH severity issue" in result.stdout
    assert "B999 | MEDIUM confidence | app/security/high.py:12 | high risk" in result.stdout
    assert "::warning::Bandit reported 2 findings below HIGH severity" in result.stdout


def test_low_and_medium_findings_warn_but_do_not_fail(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [
            _finding(severity="LOW", confidence="LOW", test_id="B101", filename="app/main.py"),
            _finding(severity="MEDIUM", test_id="B602", filename="scripts/ci/tool.py"),
            _finding(severity="MEDIUM", test_id="B602", filename="scripts/ci/other.py"),
        ],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 0
    assert "::error::" not in result.stdout
    assert "::warning::Bandit reported 3 findings below HIGH severity" in result.stdout
    assert "MEDIUM | HIGH confidence | B602 | scripts/ci: 2" in result.stdout
    assert "LOW | LOW confidence | B101 | app: 1" in result.stdout


def test_clean_report_exits_zero_without_warning(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(report, [])

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 0
    assert "No HIGH severity issues found in Bandit report" in result.stdout
    assert "::warning::" not in result.stdout
    assert "::error::" not in result.stdout


def test_summary_output_is_deterministically_sorted(tmp_path: Path) -> None:
    findings = [
        _finding(severity="MEDIUM", test_id="B602", filename="scripts/z.py", line_number=2),
        _finding(severity="LOW", test_id="B101", filename="app/a.py", line_number=7),
        _finding(severity="MEDIUM", test_id="B602", filename="scripts/a.py", line_number=1),
    ]
    first_report = tmp_path / "first.json"
    second_report = tmp_path / "second.json"
    _write_report(first_report, findings)
    _write_report(second_report, list(reversed(findings)))

    first = _run_helper(first_report, "--fail-on-high")
    second = _run_helper(second_report, "--fail-on-high")

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout.replace(str(first_report), "<report>") == second.stdout.replace(
        str(second_report),
        "<report>",
    )
    assert first.stdout.index("scripts/a.py:1") < first.stdout.index("scripts/z.py:2")


def test_github_annotation_escapes_bandit_control_characters(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [
            _finding(
                severity="LOW",
                test_id="B%1\n::warning:: injected\rline",
                issue_text="percent marker",
            )
        ],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 0
    annotation = next(line for line in result.stdout.splitlines() if line.startswith("::warning::"))
    assert "%25" in annotation
    assert "%0D" in annotation
    assert "%0A" in annotation
    assert "\n::warning:: injected" not in annotation
    assert "\rline" not in annotation
