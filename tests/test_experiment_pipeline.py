"""Tests for the governed experiment completion pipeline."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest

import scripts.orchestration.context_pack as context_pack
import scripts.orchestration.experiment_contract as experiment_contract
import scripts.orchestration.experiment_notify as experiment_notify
import scripts.orchestration.experiment_pipeline as experiment_pipeline
import scripts.orchestration.experiment_promote as experiment_promote
import scripts.orchestration.experiment_runner as experiment_runner

ORACLE_COMMAND = 'python3 -c "import sys; sys.exit(0)"'


class FakeSMTP:
    sent_messages: list[Any] = []
    started_tls = False
    login_args: tuple[str, str] | None = None

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def starttls(self, context: object | None = None) -> None:
        assert context is not None
        FakeSMTP.started_tls = True

    def login(self, username: str, password: str) -> None:
        FakeSMTP.login_args = (username, password)

    def send_message(self, message: object) -> None:
        FakeSMTP.sent_messages.append(message)

    def quit(self) -> None:
        return None


def _reset_fake_smtp() -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.started_tls = False
    FakeSMTP.login_args = None


def _configure_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_contract, "REPO_ROOT", repo)
    monkeypatch.setattr(experiment_notify, "REPO_ROOT", repo)
    monkeypatch.setattr(
        experiment_runner,
        "RESULT_ARTIFACT_DIR",
        repo / "artifacts/orchestration/experiments/results",
    )
    monkeypatch.setattr(
        experiment_promote,
        "PROMOTION_ARTIFACT_DIR",
        repo / "artifacts/orchestration/experiments/promotions",
    )
    monkeypatch.setattr(
        experiment_notify,
        "NOTIFICATION_ARTIFACT_DIR",
        repo / "artifacts/orchestration/experiments/notifications",
    )
    (repo / "core/rag").mkdir(parents=True)
    (repo / "core/rag/allowed.py").write_text("value = 1\n", encoding="utf-8")


def _configure_smtp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_EMAIL_ALLOWLIST", "pulseplate@pm.me")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_PORT", "587")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_PASSWORD", "smtp-secret")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_EMAIL_FROM", "runner@example.test")


def _packet() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "exp-pipeline",
        "decision_question": "Run governed completion pipeline",
        "task_class": "Experimentation",
        "domain": "ml",
        "mutable_candidate_surface": ["core/rag/allowed.py"],
        "immutable_oracles": [
            {
                "command": ORACLE_COMMAND,
                "expected_signal": "must pass",
            }
        ],
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 1,
            "stop_condition": "stop",
        },
        "metrics": {
            "primary": "reliability_score",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no hidden memory"],
        "promotion_target": "audit_artifact",
    }


def _result() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "exp-pipeline",
        "candidate_patch": "candidate.patch",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": ["core/rag/allowed.py"],
        "oracle_results": [
            {
                "command": ORACLE_COMMAND,
                "returncode": 0,
                "timed_out": False,
                "truncated": False,
                "stdout": "secret stdout should not be emailed",
                "stderr": "secret stderr should not be emailed",
                "cwd": "/Users/example/local/repo",
            }
        ],
        "budget_observations": {"attempts": 1},
        "shared_tree_untouched": True,
        "promotion_ready": True,
    }


def _promotion() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "exp-pipeline",
        "result_status": "accepted",
        "failure_class": None,
        "promotion_target": "audit_artifact",
        "disposition": "promoted",
        "durable_artifact_path": "docs/audit/EXPERIMENT_EXP_PIPELINE.md",
        "shared_tree_untouched": True,
        "domain": "ml",
        "evidence": {
            "oracle_commands": [ORACLE_COMMAND],
            "mutated_paths": ["core/rag/allowed.py"],
            "oracle_count": 1,
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _install_fake_runner_and_promote(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    def fake_runner_main(argv: list[str]) -> int:
        output_path = Path(argv[argv.index("--output") + 1])
        _write_json(output_path, _result())
        print(
            json.dumps(
                {
                    "experiment_id": "exp-pipeline",
                    "failure_class": None,
                    "output": str(output_path),
                    "status": "accepted",
                }
            )
        )
        return 0

    def fake_promote_main(argv: list[str]) -> int:
        output_path = Path(argv[argv.index("--output") + 1])
        audit_path = repo / "docs/audit/EXPERIMENT_EXP_PIPELINE.md"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text("# Experiment Audit Artifact: exp-pipeline\n", encoding="utf-8")
        _write_json(output_path, _promotion())
        print(
            json.dumps(
                {
                    "disposition": "promoted",
                    "experiment_id": "exp-pipeline",
                    "output": str(output_path),
                    "promotion_target": "audit_artifact",
                }
            )
        )
        return 0

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", fake_runner_main)
    monkeypatch.setattr(experiment_pipeline.experiment_promote, "main", fake_promote_main)


def test_pipeline_preserves_relative_promotion_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    _reset_fake_smtp()
    captured_promote_args: list[str] = []

    def fake_runner_main(argv: list[str]) -> int:
        output_path = Path(argv[argv.index("--output") + 1])
        _write_json(output_path, _result())
        print(json.dumps({"output": str(output_path), "status": "accepted"}))
        return 0

    def fake_promote_main(argv: list[str]) -> int:
        captured_promote_args.extend(argv)
        raw_output = argv[argv.index("--output") + 1]
        assert raw_output == "nested/decision.json"
        output_path = experiment_promote.PROMOTION_ARTIFACT_DIR / raw_output
        audit_path = repo / "docs/audit/EXPERIMENT_EXP_PIPELINE.md"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text("# Experiment Audit Artifact: exp-pipeline\n", encoding="utf-8")
        _write_json(output_path, _promotion())
        print(json.dumps({"output": str(output_path), "disposition": "promoted"}))
        return 0

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", fake_runner_main)
    monkeypatch.setattr(experiment_pipeline.experiment_promote, "main", fake_promote_main)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--promotion-output",
            "nested/decision.json",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured_promote_args
    payload = json.loads(stdout)
    assert payload["promotion"] == (
        "artifacts/orchestration/experiments/promotions/nested/decision.json"
    )


def test_pipeline_promotes_valid_rejected_result_to_backlog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    packet = _packet()
    packet["promotion_target"] = "backlog_entry"
    packet_path = _write_json(tmp_path / "packet.json", packet)
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("rejected patch\n", encoding="utf-8")
    promotion_called = False

    def fake_runner_main(argv: list[str]) -> int:
        result = _result()
        result.update(
            {
                "status": "rejected",
                "failure_class": "metric_regression",
                "promotion_ready": False,
            }
        )
        oracle_results = result["oracle_results"]
        assert isinstance(oracle_results, list)
        terminal_oracle = oracle_results[0]
        assert isinstance(terminal_oracle, dict)
        terminal_oracle["returncode"] = 1
        output_path = Path(argv[argv.index("--output") + 1])
        _write_json(output_path, result)
        print(json.dumps({"output": str(output_path), "status": "rejected"}))
        return experiment_runner.RUNNER_REJECTED_EXIT_CODE

    def fake_promote_main(argv: list[str]) -> int:
        nonlocal promotion_called
        promotion_called = True
        result_path = Path(argv[argv.index("--result") + 1])
        assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "rejected"
        output_path = Path(argv[argv.index("--output") + 1])
        _write_json(
            output_path,
            {
                "disposition": "deferred",
                "experiment_id": "exp-pipeline",
                "promotion_target": "backlog_entry",
            },
        )
        print(json.dumps({"output": str(output_path), "disposition": "deferred"}))
        return 0

    def fake_notify_main(_argv: list[str]) -> int:
        print(json.dumps({"output": "notification.md"}))
        return 0

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", fake_runner_main)
    monkeypatch.setattr(experiment_pipeline.experiment_promote, "main", fake_promote_main)
    monkeypatch.setattr(experiment_pipeline.experiment_notify, "main", fake_notify_main)

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )

    assert exit_code == 0
    assert promotion_called is True
    assert json.loads(capsys.readouterr().out)["promotion"].endswith("exp-pipeline.json")


def test_pipeline_stops_policy_violation_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    packet = _packet()
    packet["promotion_target"] = "backlog_entry"
    packet_path = _write_json(tmp_path / "packet.json", packet)
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("rejected patch\n", encoding="utf-8")
    promotion_called = False

    def fake_runner_main(argv: list[str]) -> int:
        result = _result()
        result.update(
            {
                "status": "rejected",
                "failure_class": "policy_violation",
                "mutated_paths": [],
                "oracle_results": [],
                "promotion_ready": False,
                "budget_observations": {
                    "attempts": 0,
                    "retries_consumed": 0,
                    "runner_error": "terminal policy violation",
                },
            }
        )
        output_path = Path(argv[argv.index("--output") + 1])
        _write_json(output_path, result)
        print(json.dumps({"output": str(output_path), "status": "rejected"}))
        return experiment_runner.RUNNER_REJECTED_EXIT_CODE

    def fake_promote_main(argv: list[str]) -> int:
        nonlocal promotion_called
        promotion_called = True
        return experiment_promote.main(argv)

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", fake_runner_main)
    monkeypatch.setattr(experiment_pipeline.experiment_promote, "main", fake_promote_main)

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )

    assert exit_code == 1
    assert promotion_called is True
    assert "promotion stage failed" in capsys.readouterr().out
    assert not (repo / "docs" / "roadmap" / "BACKLOG_LEDGER.md").exists()


@pytest.mark.parametrize(
    "raw_output",
    [
        "../outside.json",
        "../../outside.json",
    ],
)
def test_pipeline_rejects_parent_promotion_output_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    raw_output: str,
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)

    def forbidden_runner_main(argv: list[str]) -> int:
        raise AssertionError(f"runner should not run for invalid output: {argv}")

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", forbidden_runner_main)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--promotion-output",
            raw_output,
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "promotion output must stay within governed artifact directory" in captured.out
    assert raw_output not in captured.out
    assert str(tmp_path) not in captured.out


def test_pipeline_rejects_absolute_promotion_output_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)

    def forbidden_runner_main(argv: list[str]) -> int:
        raise AssertionError(f"runner should not run for invalid output: {argv}")

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", forbidden_runner_main)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")
    absolute_output = tmp_path / "outside.json"

    exit_code = experiment_pipeline.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--promotion-output",
            str(absolute_output),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "promotion output must stay within governed artifact directory" in captured.out
    assert str(absolute_output) not in captured.out
    assert str(tmp_path) not in captured.out


def test_pipeline_rejects_oracle_only_packet_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)

    def oracle_only_packet(payload: dict[str, object]) -> dict[str, object]:
        del payload
        packet = _packet()
        packet["runner_mode"] = experiment_contract.ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        return packet

    def forbidden_runner_main(argv: list[str]) -> int:
        raise AssertionError(f"oracle-only packet must not enter runner pipeline: {argv}")

    monkeypatch.setattr(experiment_pipeline, "validate_experiment_packet", oracle_only_packet)
    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", forbidden_runner_main)
    packet_path = _write_json(tmp_path / "packet.json", {"stub": True})
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "runner-only review evidence" in captured.out
    assert str(tmp_path) not in captured.out


def test_pipeline_stage_failure_captures_stderr_without_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)

    def leaking_runner_main(argv: list[str]) -> int:
        del argv
        print("secret stdout")
        print("secret stderr", file=sys.stderr)
        return 1

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", leaking_runner_main)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "runner stage failed" in captured.out
    assert "secret stdout" not in captured.out
    assert "secret stderr" not in captured.out
    assert "secret stderr" not in captured.err


def test_pipeline_stage_exception_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)

    def exploding_runner_main(argv: list[str]) -> int:
        del argv
        raise RuntimeError("secret exception detail")

    monkeypatch.setattr(experiment_pipeline.experiment_runner, "main", exploding_runner_main)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "runner stage failed" in captured.out
    assert "secret exception detail" not in captured.out
    assert "secret exception detail" not in captured.err


def test_pipeline_does_not_email_without_explicit_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    _configure_smtp_env(monkeypatch)
    _reset_fake_smtp()
    monkeypatch.setattr(experiment_notify.smtplib, "SMTP", FakeSMTP)
    _install_fake_runner_and_promote(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text must not render\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        ["--packet", str(packet_path), "--candidate-patch", str(patch_path)]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(stdout)
    assert payload["email_reports"] is False
    assert payload["email_recipient"] is None
    assert FakeSMTP.sent_messages == []
    assert (repo / "artifacts/orchestration/experiments/notifications/exp-pipeline.md").is_file()


def test_pipeline_email_reports_use_governed_recipient_and_redacted_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    _configure_smtp_env(monkeypatch)
    _reset_fake_smtp()
    monkeypatch.setattr(experiment_notify.smtplib, "SMTP", FakeSMTP)
    _install_fake_runner_and_promote(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("raw patch secret should not render\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--email-reports",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(stdout)
    assert payload["email_reports"] is True
    assert payload["email_recipient"] == "governed-v1-recipient"
    assert len(FakeSMTP.sent_messages) == 1
    message = FakeSMTP.sent_messages[0]
    assert message["To"] == "pulseplate@pm.me"
    body = message.get_content()
    assert "secret stdout" not in body
    assert "secret stderr" not in body
    assert "raw patch secret" not in body
    assert "/Users/example" not in body

    audit_path = (
        repo / "artifacts/orchestration/experiments/notifications/exp-pipeline.email-audit.json"
    )
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "pulseplate@pm.me" not in audit_text
    assert "smtp-secret" not in audit_text
    assert payload["email_audit"] == (
        "artifacts/orchestration/experiments/notifications/exp-pipeline.email-audit.json"
    )


def test_pipeline_missing_smtp_config_fails_closed_without_secret_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _configure_repo(monkeypatch, repo)
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_EMAIL_ALLOWLIST", "pulseplate@pm.me")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_HOST", "/Users/alice/.ssh/id_rsa")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_SMTP_PASSWORD", "smtp-secret")
    monkeypatch.setenv("EXPERIMENT_NOTIFICATION_EMAIL_FROM", "runner@example.test")
    _reset_fake_smtp()
    monkeypatch.setattr(experiment_notify.smtplib, "SMTP", FakeSMTP)
    _install_fake_runner_and_promote(monkeypatch, repo)
    packet_path = _write_json(tmp_path / "packet.json", _packet())
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text("patch text\n", encoding="utf-8")

    exit_code = experiment_pipeline.main(
        [
            "--packet",
            str(packet_path),
            "--candidate-patch",
            str(patch_path),
            "--email-reports",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 1
    assert "notification stage failed" in stdout
    assert "/Users/alice" not in stdout
    assert "id_rsa" not in stdout
    assert "smtp-secret" not in stdout
    assert FakeSMTP.sent_messages == []


def test_pipeline_help_documents_explicit_email_reports(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        experiment_pipeline.main(["--help"])
    stdout = capsys.readouterr().out

    assert exc_info.value.code == 0
    assert "--email-reports" in stdout
    assert "--email-to" not in stdout
    assert "fixed to the governed v1 recipient" in stdout
