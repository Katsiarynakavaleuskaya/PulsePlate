"""Tests for the canonical multi-manifest Safety audit helper."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.ci import run_safety_audit as safety_audit


def _write_report(path: Path, severities: list[str]) -> None:
    payload = {
        "vulnerabilities": [
            {
                "package_name": f"pkg-{index}",
                "analyzed_version": "1.0.0",
                "vuln_id": f"VULN-{index}",
                "severity": {"cvssv3": {"base_severity": severity}},
            }
            for index, severity in enumerate(severities, start=1)
        ],
        "ignored_vulnerabilities": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_scan_report(path: Path, severities: list[str], *, ignored: bool = False) -> None:
    payload = {
        "meta": {"scan_type": "scan"},
        "scan_results": {
            "projects": [
                {
                    "files": [
                        {
                            "location": "requirements.txt",
                            "results": {
                                "dependencies": [
                                    {
                                        "name": "example",
                                        "specifications": [
                                            {
                                                "raw": "example==1.0.0",
                                                "vulnerabilities": {
                                                    "known_vulnerabilities": [
                                                        {
                                                            "id": f"VULN-{index}",
                                                            "vulnerable_spec": "example==1.0.0",
                                                            "CVE": {
                                                                "cvssv3": {
                                                                    "base_severity": severity,
                                                                },
                                                            },
                                                            **(
                                                                {
                                                                    "ignored": {
                                                                        "code": "manual",
                                                                        "reason": "test policy",
                                                                        "expires": "2026-07-08",
                                                                    }
                                                                }
                                                                if ignored
                                                                else {}
                                                            ),
                                                        }
                                                        for index, severity in enumerate(
                                                            severities, start=1
                                                        )
                                                    ],
                                                },
                                            }
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                }
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_manifest(root: Path, name: str, content: str = "example==1.0.0\n") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _report_path_from_scan_command(command: list[str]) -> Path:
    assert "scan" in command
    assert "check" not in command
    assert command[command.index("--save-as") + 1] == "json"
    return Path(command[command.index("--save-as") + 2])


def test_discovers_required_and_optional_manifests(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "requirements.txt")
    _write_manifest(tmp_path, "requirements-docker-runtime.txt")
    _write_manifest(tmp_path, "requirements-rag-vector.txt")
    _write_manifest(tmp_path, "requirements-rag-vector-cpu.txt")

    manifests = safety_audit.discover_manifests(tmp_path)

    assert [manifest.name for manifest in manifests] == [
        "requirements.txt",
        "requirements-docker-runtime.txt",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.txt",
    ]


def test_discovery_fails_when_required_manifest_is_missing(tmp_path: Path) -> None:
    with pytest.raises(safety_audit.SafetyAuditError, match="requirements.txt not found"):
        safety_audit.discover_manifests(tmp_path)


def test_policy_file_precedence_prefers_yaml_over_toml(tmp_path: Path) -> None:
    (tmp_path / "safety-policy.toml").write_text("[policy]\n", encoding="utf-8")
    (tmp_path / "safety-policy.yaml").write_text("policy: {}\n", encoding="utf-8")

    assert safety_audit.policy_args(tmp_path) == (
        "--policy-file",
        str(tmp_path / "safety-policy.yaml"),
    )


def test_run_audit_emits_per_manifest_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, "requirements.txt")
    _write_manifest(tmp_path, "requirements-docker-runtime.txt")
    _write_manifest(tmp_path, "requirements-rag-vector-cpu.txt")
    output_dir = tmp_path / "reports"
    commands: list[list[str]] = []
    scan_target_files: list[set[str]] = []

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        commands.append(command)
        target_path = Path(command[command.index("--target") + 1])
        scan_target_files.append({path.name for path in target_path.rglob("*") if path.is_file()})
        report_path = _report_path_from_scan_command(command)
        _write_report(report_path, [])
        return SimpleNamespace(returncode=0, stdout="safety output\n", stderr="")

    monkeypatch.setenv("SAFETY_API_KEY", "test-key")
    monkeypatch.setattr(safety_audit.shutil, "which", lambda _: "/usr/bin/safety")
    monkeypatch.setattr(safety_audit.subprocess, "run", fake_run)

    config = safety_audit.build_config(root=tmp_path, output_dir=output_dir)
    results = safety_audit.run_audit(config)

    assert safety_audit.exit_code_for_results(results) == 0
    assert sorted(path.name for path in output_dir.glob("safety-*")) == [
        "safety-requirements-docker-runtime.json",
        "safety-requirements-docker-runtime.log",
        "safety-requirements-docker-runtime.txt",
        "safety-requirements-rag-vector-cpu.json",
        "safety-requirements-rag-vector-cpu.log",
        "safety-requirements-rag-vector-cpu.txt",
        "safety-requirements.json",
        "safety-requirements.log",
        "safety-requirements.txt",
    ]
    assert any("requirements-rag-vector-cpu.txt" in files for files in scan_target_files)
    assert all("--target" in command for command in commands)
    assert all(
        command[:4] == ["/usr/bin/safety", "--stage", "cicd", "--disable-optional-telemetry"]
        for command in commands
    )


def test_scan_target_copies_nested_requirement_references(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        "requirements.txt",
        "-r requirements/base.txt\n-c constraints/global.txt\n",
    )
    _write_manifest(
        tmp_path, "requirements/base.txt", "--constraint nested/pins.txt\nexample==1.0.0\n"
    )
    _write_manifest(tmp_path, "requirements/nested/pins.txt", "example==1.0.0\n")
    _write_manifest(tmp_path, "constraints/global.txt", "example<2\n")
    target_dir = tmp_path / "scan-target"

    safety_audit._prepare_scan_target(tmp_path, tmp_path / "requirements.txt", target_dir)

    assert (target_dir / "requirements.txt").is_file()
    assert (target_dir / "requirements/base.txt").is_file()
    assert (target_dir / "requirements/nested/pins.txt").is_file()
    assert (target_dir / "constraints/global.txt").is_file()


def test_scan_target_handles_cyclic_requirement_references(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "requirements.txt", "-r requirements/base.txt\n")
    _write_manifest(tmp_path, "requirements/base.txt", "-r ../requirements.txt\n")
    target_dir = tmp_path / "scan-target"

    safety_audit._prepare_scan_target(tmp_path, tmp_path / "requirements.txt", target_dir)

    assert (target_dir / "requirements.txt").is_file()
    assert (target_dir / "requirements/base.txt").is_file()


def test_scan_v3_report_high_risk_finding_fails_aggregate(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    _write_scan_report(report_path, ["HIGH"])

    analysis = safety_audit.analyze_report(report_path, summary_path)

    assert analysis.status == safety_audit.PARSE_BLOCKING
    assert analysis.high_risk_count == 1
    assert "VULN-1" in summary_path.read_text(encoding="utf-8")


def test_scan_v3_ignored_findings_do_not_fail_aggregate(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    _write_scan_report(report_path, ["HIGH"], ignored=True)

    analysis = safety_audit.analyze_report(report_path, summary_path)

    assert analysis.status == safety_audit.PARSE_OK
    assert analysis.high_risk_count == 0
    assert "Ignored vulnerabilities: 1" in summary_path.read_text(encoding="utf-8")


def test_cpu_rag_vector_manifest_high_risk_finding_fails_aggregate(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements-rag-vector-cpu.json"
    summary_path = tmp_path / "safety-requirements-rag-vector-cpu.txt"
    _write_report(report_path, ["HIGH"])

    analysis = safety_audit.analyze_report(report_path, summary_path)
    result = safety_audit.ManifestAuditResult(
        manifest=tmp_path / "requirements-rag-vector-cpu.txt",
        report_json=report_path,
        report_txt=summary_path,
        console_log=tmp_path / "safety-requirements-rag-vector-cpu.log",
        safety_exit_code=64,
        analysis=analysis,
    )

    assert analysis.status == safety_audit.PARSE_BLOCKING
    assert safety_audit.exit_code_for_results([result]) == 1


def test_run_audit_removes_stale_report_before_safety_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, "requirements.txt")
    stale_report = tmp_path / "safety-requirements.json"
    _write_report(stale_report, [])

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        assert _report_path_from_scan_command(command) == stale_report
        assert not stale_report.exists()
        return SimpleNamespace(returncode=64, stdout="", stderr="failed before report\n")

    monkeypatch.setenv("SAFETY_API_KEY", "test-key")
    monkeypatch.setattr(safety_audit.shutil, "which", lambda _: "/usr/bin/safety")
    monkeypatch.setattr(safety_audit.subprocess, "run", fake_run)

    config = safety_audit.build_config(root=tmp_path, output_dir=tmp_path)

    with pytest.raises(safety_audit.SafetyAuditError, match="failed to produce"):
        safety_audit.run_audit(config)
    assert not stale_report.exists()


@pytest.mark.parametrize("severity", ["HIGH", "CRITICAL", "UNKNOWN"])
def test_high_risk_findings_fail_aggregate(tmp_path: Path, severity: str) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    _write_report(report_path, [severity])

    analysis = safety_audit.analyze_report(report_path, summary_path)

    assert analysis.status == safety_audit.PARSE_BLOCKING
    assert analysis.high_risk_count == 1


@pytest.mark.parametrize("severity", ["LOW", "MEDIUM"])
def test_low_and_medium_findings_warn_without_failing_when_safety_exits_zero(
    tmp_path: Path, severity: str
) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    _write_report(report_path, [severity])

    analysis = safety_audit.analyze_report(report_path, summary_path)

    assert analysis.status == safety_audit.PARSE_WARNING
    assert analysis.high_risk_count == 0
    result = safety_audit.ManifestAuditResult(
        manifest=tmp_path / "requirements.txt",
        report_json=report_path,
        report_txt=summary_path,
        console_log=tmp_path / "safety-requirements.log",
        safety_exit_code=0,
        analysis=analysis,
    )
    assert safety_audit.exit_code_for_results([result]) == 0


@pytest.mark.parametrize("severity", ["LOW", "MEDIUM"])
def test_low_and_medium_findings_fail_when_safety_exits_nonzero(
    tmp_path: Path, severity: str
) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    _write_report(report_path, [severity])

    analysis = safety_audit.analyze_report(report_path, summary_path)
    result = safety_audit.ManifestAuditResult(
        manifest=tmp_path / "requirements.txt",
        report_json=report_path,
        report_txt=summary_path,
        console_log=tmp_path / "safety-requirements.log",
        safety_exit_code=64,
        analysis=analysis,
    )

    assert analysis.status == safety_audit.PARSE_WARNING
    assert safety_audit.exit_code_for_results([result]) == 1


def test_missing_or_empty_report_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text("", encoding="utf-8")

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "not generated" in summary_path.read_text(encoding="utf-8")


def test_non_object_report_json_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text("[]", encoding="utf-8")

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "must be an object" in summary_path.read_text(encoding="utf-8")


def test_non_list_vulnerabilities_field_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text('{"vulnerabilities": {}}', encoding="utf-8")

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "vulnerabilities field must be a list" in summary_path.read_text(encoding="utf-8")


def test_non_object_vulnerability_entry_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text('{"vulnerabilities": [1]}', encoding="utf-8")

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "vulnerability entries must be objects" in summary_path.read_text(encoding="utf-8")


def test_non_list_ignored_vulnerabilities_field_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text(
        '{"vulnerabilities": [], "ignored_vulnerabilities": {}}',
        encoding="utf-8",
    )

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "ignored_vulnerabilities field must be a list" in summary_path.read_text(
        encoding="utf-8"
    )


def test_invalid_report_json_fails_closed(tmp_path: Path) -> None:
    report_path = tmp_path / "safety-requirements.json"
    summary_path = tmp_path / "safety-requirements.txt"
    report_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.analyze_report(report_path, summary_path)

    assert exc_info.value.exit_code == safety_audit.PARSE_ERROR
    assert "Failed to parse Safety report JSON" in summary_path.read_text(encoding="utf-8")


def test_run_audit_writes_summary_when_report_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, "requirements.txt")

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        report_path = _report_path_from_scan_command(command)
        assert report_path.name == "safety-requirements.json"
        return SimpleNamespace(returncode=3, stdout="", stderr="no json\n")

    monkeypatch.setenv("SAFETY_API_KEY", "test-key")
    monkeypatch.setattr(safety_audit.shutil, "which", lambda _: "/usr/bin/safety")
    monkeypatch.setattr(safety_audit.subprocess, "run", fake_run)
    config = safety_audit.build_config(root=tmp_path, output_dir=tmp_path)

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.run_audit(config)

    assert exc_info.value.exit_code == 3
    assert "failed to produce safety-requirements.json" in (
        tmp_path / "safety-requirements.txt"
    ).read_text(encoding="utf-8")


def test_nonzero_safety_exit_with_empty_report_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, "requirements.txt")

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        report_path = _report_path_from_scan_command(command)
        _write_report(report_path, [])
        return SimpleNamespace(returncode=3, stdout="", stderr="tool error\n")

    monkeypatch.setenv("SAFETY_API_KEY", "test-key")
    monkeypatch.setattr(safety_audit.shutil, "which", lambda _: "/usr/bin/safety")
    monkeypatch.setattr(safety_audit.subprocess, "run", fake_run)
    config = safety_audit.build_config(root=tmp_path, output_dir=tmp_path)

    with pytest.raises(safety_audit.SafetyAuditError) as exc_info:
        safety_audit.run_audit(config)

    assert exc_info.value.exit_code == 3
    assert "report contained no parsed vulnerabilities" in (
        tmp_path / "safety-requirements.txt"
    ).read_text(encoding="utf-8")


def test_scan_requires_api_key_for_cicd_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, "requirements.txt")
    monkeypatch.delenv("SAFETY_API_KEY", raising=False)
    monkeypatch.setattr(safety_audit.shutil, "which", lambda _: "/usr/bin/safety")

    config = safety_audit.build_config(root=tmp_path, output_dir=tmp_path)

    with pytest.raises(safety_audit.SafetyAuditError, match="SAFETY_API_KEY is required"):
        safety_audit.run_audit(config)
