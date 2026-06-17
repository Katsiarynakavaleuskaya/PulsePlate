"""Tests for deterministic Bandit report summarization."""

from __future__ import annotations

import json
import os
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


def test_equal_count_summary_groups_follow_severity_order(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [
            _finding(severity="LOW", test_id="B101", filename="app/low.py"),
            _finding(severity="MEDIUM", test_id="B602", filename="app/medium.py"),
        ],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 0
    assert result.stdout.index("MEDIUM | HIGH confidence | B602") < result.stdout.index(
        "LOW | HIGH confidence | B101"
    )


def test_github_workflow_path_bucket_is_reachable(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [_finding(severity="LOW", test_id="B101", filename="./.github/workflows/ci.yml")],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 0
    assert "LOW | HIGH confidence | B101 | github/workflows: 1" in result.stdout


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


def test_bandit_derived_raw_output_cannot_emit_workflow_commands(tmp_path: Path) -> None:
    report = tmp_path / "bandit-report.json"
    _write_report(
        report,
        [
            _finding(
                severity="HIGH",
                test_id="B999\n::error:: injected",
                filename="app/security/high.py\n::add-mask::secret",
                issue_text="high\n::warning:: injected",
            ),
            _finding(
                severity="LOW",
                test_id="B101\n::warning:: injected",
                filename="tests/low.py",
            ),
        ],
    )

    result = _run_helper(report, "--fail-on-high")

    assert result.returncode == 1
    command_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(("::warning:: injected", "::error:: injected", "::add-mask::"))
    ]
    assert command_lines == []


def _write_fake_bandit(fake_bin: Path, *, severity: str) -> None:
    fake_bin.mkdir()
    fake_bandit = fake_bin / "bandit"
    fake_bandit.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      output="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -z "$output" ]]; then
  exit 2
fi
cat > "$output" <<'JSON'
{{"results":[{{"filename":"app/security/example.py","issue_confidence":"HIGH","issue_severity":"{severity}","issue_text":"fake finding","line_number":1,"test_id":"B999"}}]}}
JSON
exit 1
""",
        encoding="utf-8",
    )
    fake_bandit.chmod(0o755)


def _run_ci_bandit_with_fake_bandit(
    tmp_path: Path, *, severity: str
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "fake-bin"
    _write_fake_bandit(fake_bin, severity=severity)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(
        [
            "bash",
            "scripts/ci_bandit.sh",
            "--exclude",
            "tests",
            "--output",
            str(tmp_path / "bandit-report.json"),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_ci_bandit_wrapper_fails_high_findings_in_non_strict_mode(tmp_path: Path) -> None:
    result = _run_ci_bandit_with_fake_bandit(tmp_path, severity="HIGH")

    assert result.returncode == 1
    assert "::error::Bandit found 1 HIGH severity issue" in result.stdout


def test_ci_bandit_wrapper_keeps_lower_findings_warning_only(tmp_path: Path) -> None:
    result = _run_ci_bandit_with_fake_bandit(tmp_path, severity="LOW")

    assert result.returncode == 0
    assert "::warning::Bandit reported 1 findings below HIGH severity" in result.stdout
    assert "continuing (non-strict)" in result.stderr
