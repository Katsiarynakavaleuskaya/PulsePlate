"""Tests for the host-only Codex/Ollama operator doctor."""

from __future__ import annotations

from pathlib import Path
from subprocess import TimeoutExpired
from typing import Any

import pytest

from scripts.orchestration import check_codex_ollama_operator as doctor


def test_parse_version_accepts_major_minor_patch() -> None:
    assert doctor._parse_version("ollama version is 0.15.1") == (0, 15, 1)
    assert doctor._parse_version("client version is 0.12.0") == (0, 12, 0)
    assert doctor._parse_version("version 1.2") == (1, 2, 0)


def test_run_version_reports_cli_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*args: Any, **kwargs: Any) -> Any:
        raise TimeoutExpired(cmd=["/usr/bin/ollama", "--version"], timeout=10)

    monkeypatch.setattr(doctor.subprocess, "run", _timeout)

    returncode, output = doctor._run_version("/usr/bin/ollama", ["--version"])

    assert returncode == 124
    assert "timed out" in output
    assert "/usr/bin/ollama --version" in output


def test_stale_ollama_version_reports_launch_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        doctor,
        "_run_version",
        lambda binary, args: (0, "Warning: client version is 0.12.0"),
    )

    result = doctor._check_ollama_version("/usr/bin/ollama")

    assert result.ok is False
    assert "requires 0.15.0+" in result.detail
    assert "ollama launch codex" in result.fix
    assert "codex-app" in result.fix


def test_missing_binaries_are_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

    ollama_check, binary, _ = doctor._check_ollama_binary()
    codex_check = doctor._check_codex_binary()

    assert binary is None
    assert ollama_check.ok is False
    assert "not found" in ollama_check.detail
    assert "Install" in ollama_check.fix
    assert codex_check.ok is False
    assert "Codex CLI" in codex_check.fix


def test_rejects_non_local_ollama_url() -> None:
    result = doctor._check_ollama_server("https://example.com", timeout_s=0.01)

    assert result.ok is False
    assert "localhost" in result.detail
    assert "local" in result.fix


def test_unavailable_local_ollama_server_reports_serve_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: Any, **kwargs: Any) -> Any:
        raise OSError("connection refused")

    monkeypatch.setattr(doctor, "urlopen", _raise)

    result = doctor._check_ollama_server("http://localhost:11434", timeout_s=0.01)

    assert result.ok is False
    assert "could not reach" in result.detail
    assert "ollama serve" in result.fix


def test_successful_server_check_uses_local_version_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    class _Response:
        status = 200

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _fake_urlopen(url: str, *, timeout: float) -> _Response:
        observed["url"] = url
        observed["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(doctor, "urlopen", _fake_urlopen)

    result = doctor._check_ollama_server("http://127.0.0.1:11434", timeout_s=0.5)

    assert result.ok is True
    assert observed == {"url": "http://127.0.0.1:11434/api/version", "timeout": 0.5}


def test_timeout_must_be_positive() -> None:
    assert doctor._positive_timeout("0.5") == 0.5

    with pytest.raises(SystemExit):
        doctor.main(["--timeout", "0"])


def test_main_json_reports_host_write_guard(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    monkeypatch.setattr(
        doctor,
        "run_checks",
        lambda ollama_url, timeout_s: [
            doctor.CheckResult(
                name="host-config-write-guard",
                ok=True,
                detail="read-only diagnostic; no host config files are inspected or written.",
                fix="",
            )
        ],
    )

    exit_code = doctor.main(["--json"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "host-config-write-guard" in out
    assert "read-only diagnostic" in out


def test_template_does_not_contain_secrets_or_personal_paths() -> None:
    template = Path("docs/templates/codex.config.example.toml").read_text(encoding="utf-8")

    assert "sk-" not in template
    assert "/Users/" not in template
    assert "api_key" not in template.lower()
