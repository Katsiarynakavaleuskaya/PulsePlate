"""Tests for the host-only Codex/Ollama operator doctor."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Any
from urllib.error import HTTPError

import pytest

from scripts.orchestration import check_codex_ollama_operator as doctor


def test_parse_version_accepts_major_minor_patch() -> None:
    assert doctor._parse_version("ollama version is 0.15.1") == (0, 15, 1)
    assert doctor._parse_version("client version is 0.12.0") == (0, 12, 0)
    assert doctor._parse_version("version 1.2") == (1, 2, 0)


def test_ollama_version_prefers_client_version_from_mixed_output() -> None:
    output = "\n".join(
        [
            "ollama version is 0.24.0",
            "Warning: client version is 0.12.0",
        ]
    )

    assert doctor._parse_ollama_binary_version(output) == (0, 12, 0)


def test_run_version_reports_cli_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*args: Any, **kwargs: Any) -> Any:
        raise TimeoutExpired(cmd=["/usr/bin/ollama", "--version"], timeout=10)

    monkeypatch.setattr(doctor.subprocess, "run", _timeout)

    returncode, output = doctor._run_version("/usr/bin/ollama", ["--version"])

    assert returncode == 124
    assert "timed out" in output
    assert "/usr/bin/ollama --version" in output


def test_run_version_passes_expected_subprocess_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def _record_run(*args: Any, **kwargs: Any) -> CompletedProcess[str]:
        observed["args"] = args
        observed["kwargs"] = kwargs
        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="ollama version is 0.24.0",
            stderr="version probe warning",
        )

    monkeypatch.setattr(doctor.subprocess, "run", _record_run)

    result = doctor._run_version("/usr/bin/ollama", ["--version"])

    assert result == (0, "ollama version is 0.24.0\nversion probe warning")
    assert observed == {
        "args": (["/usr/bin/ollama", "--version"],),
        "kwargs": {
            "text": True,
            "capture_output": True,
            "check": False,
            "timeout": 10,
            "shell": False,
        },
    }


def test_stale_ollama_version_reports_launch_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        doctor,
        "_run_version",
        lambda binary, args: (0, "Warning: client version is 0.12.0"),
    )

    cli_result, app_result = doctor._check_ollama_version("/usr/bin/ollama")

    assert cli_result.ok is False
    assert "requires 0.15.0+" in cli_result.detail
    assert "ollama launch codex" in cli_result.fix
    assert app_result.ok is False
    assert "requires 0.24.0+" in app_result.detail
    assert "ollama launch codex-app" in app_result.fix


def test_cli_ready_version_can_still_require_codex_app_upgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        doctor,
        "_run_version",
        lambda binary, args: (0, "ollama version is 0.15.0"),
    )

    cli_result, app_result = doctor._check_ollama_version("/usr/bin/ollama")

    assert cli_result.ok is True
    assert app_result.ok is False
    assert "0.24.0+" in app_result.detail


def test_nonzero_ollama_version_fails_even_with_parseable_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctor,
        "_run_version",
        lambda binary, args: (1, "ollama version is 0.24.0"),
    )

    cli_result, app_result = doctor._check_ollama_version("/usr/bin/ollama")

    assert cli_result.ok is False
    assert app_result.ok is False
    assert "`ollama --version` failed" in cli_result.detail
    assert "Parsed version: 0.24.0" in cli_result.detail


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


def test_binary_checks_normalize_relative_which_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, list[str]]] = []

    def _relative_which(name: str) -> str:
        return f"bin/{name}"

    def _record_version(binary: str, args: Sequence[str]) -> tuple[int, str]:
        observed.append((binary, list(args)))
        return 0, "codex 1.0.0"

    monkeypatch.setattr(doctor.shutil, "which", _relative_which)
    monkeypatch.setattr(doctor, "_run_version", _record_version)

    ollama_check, ollama_binary, _ = doctor._check_ollama_binary()
    codex_check = doctor._check_codex_binary()

    assert ollama_check.ok is True
    assert ollama_binary is not None
    assert Path(ollama_binary).is_absolute()
    assert ollama_binary.endswith("/bin/ollama")
    assert codex_check.ok is True
    assert len(observed) == 1
    assert Path(observed[0][0]).is_absolute()
    assert observed[0][0].endswith("/bin/codex")
    assert observed[0][1] == ["--version"]


def test_rejects_non_local_ollama_url() -> None:
    result = doctor._check_ollama_server("https://example.com", timeout_s=0.01)

    assert result.ok is False
    assert "localhost" in result.detail
    assert "local" in result.fix


def test_rejects_credentialed_ollama_url_without_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened_urls: list[str] = []
    credential_sentinel = "credential-sentinel"

    def _record_open(url: str, timeout_s: float) -> Any:
        opened_urls.append(url)
        raise AssertionError("credentialed URL must be rejected before opening")

    monkeypatch.setattr(doctor, "_open_no_redirect", _record_open)

    result = doctor._check_ollama_server(
        f"http://user:{credential_sentinel}@localhost:11434",
        timeout_s=0.01,
    )

    assert result.ok is False
    assert result.detail == "Ollama URL must not include credentials."
    assert credential_sentinel not in result.detail
    assert credential_sentinel not in result.fix
    assert opened_urls == []


@pytest.mark.parametrize(
    "sensitive_url",
    [
        "http://user:credential-sentinel\uff20localhost:11434",
        "http://localhost:credential-sentinel",
    ],
)
def test_rejects_malformed_sensitive_ollama_url_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    sensitive_url: str,
) -> None:
    opened_urls: list[str] = []

    def _record_open(url: str, timeout_s: float) -> None:
        opened_urls.append(url)

    monkeypatch.setattr(doctor, "_open_no_redirect", _record_open)

    result = doctor._check_ollama_server(sensitive_url, timeout_s=0.01)

    assert result.ok is False
    assert result.detail == "Malformed Ollama URL."
    assert "credential-sentinel" not in result.detail
    assert "credential-sentinel" not in result.fix
    assert opened_urls == []


def test_rejects_unexpected_ollama_url_path() -> None:
    result = doctor._check_ollama_server("http://localhost:11434/admin", timeout_s=0.01)

    assert result.ok is False
    assert "server root" in result.detail


def test_malformed_ollama_url_returns_check_failure() -> None:
    result = doctor._check_ollama_server("http://[::1", timeout_s=0.01)

    assert result.ok is False
    assert "Malformed Ollama URL" in result.detail


def test_unavailable_local_ollama_server_reports_serve_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: Any, **kwargs: Any) -> Any:
        raise OSError("connection refused")

    monkeypatch.setattr(doctor, "_open_no_redirect", _raise)

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

        def read(self) -> bytes:
            return b'{"version":"0.13.3"}'

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _fake_open(url: str, timeout_s: float) -> _Response:
        observed["url"] = url
        observed["timeout"] = timeout_s
        return _Response()

    monkeypatch.setattr(doctor, "_open_no_redirect", _fake_open)

    result = doctor._check_ollama_server("http://127.0.0.1:11434/v1", timeout_s=0.5)

    assert result.ok is True
    assert observed == {"url": "http://127.0.0.1:11434/api/version", "timeout": 0.5}
    assert "0.13.3" in result.detail


def test_local_server_opener_disables_environment_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}
    response = object()

    class _Opener:
        def open(self, url: str, *, timeout: float) -> object:
            observed["url"] = url
            observed["timeout"] = timeout
            return response

    def _build_opener(*handlers: object) -> _Opener:
        observed["handlers"] = handlers
        return _Opener()

    monkeypatch.setattr(doctor, "build_opener", _build_opener)

    result = doctor._open_no_redirect("http://localhost:11434/api/version", 0.5)

    assert result is response
    handlers = observed["handlers"]
    assert len(handlers) == 2
    assert isinstance(handlers[0], doctor.ProxyHandler)
    assert handlers[0].proxies == {}
    assert handlers[1] is doctor._NoRedirectHandler
    assert observed["url"] == "http://localhost:11434/api/version"
    assert observed["timeout"] == 0.5


def test_stale_running_ollama_server_fails_profile_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"version":"0.12.0"}'

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(doctor, "_open_no_redirect", lambda url, timeout_s: _Response())

    result = doctor._check_ollama_server("http://localhost:11434", timeout_s=0.5)

    assert result.ok is False
    assert "0.12.0" in result.detail
    assert "0.13.3+" in result.detail


def test_unparseable_ollama_server_version_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b"not json"

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(doctor, "_open_no_redirect", lambda url, timeout_s: _Response())

    result = doctor._check_ollama_server("http://localhost:11434", timeout_s=0.5)

    assert result.ok is False
    assert "no parseable server version" in result.detail


@pytest.mark.parametrize("raw_body", [b"[]", b"null", b'"0.24.0"', b"42", b"true"])
def test_server_version_rejects_non_object_json(raw_body: bytes) -> None:
    class _Response:
        def read(self) -> bytes:
            return raw_body

    assert doctor._read_ollama_server_version(_Response()) is None


def test_http_error_reports_status_instead_of_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_http_error(*args: Any, **kwargs: Any) -> Any:
        raise HTTPError(
            url="http://localhost:11434/api/version",
            code=500,
            msg="Server Error",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(doctor, "_open_no_redirect", _raise_http_error)

    result = doctor._check_ollama_server("http://localhost:11434", timeout_s=0.5)

    assert result.ok is False
    assert "HTTP 500" in result.detail
    assert "could not reach" not in result.detail


def test_redirects_are_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_redirect(*args: Any, **kwargs: Any) -> Any:
        raise HTTPError(
            url="http://localhost:11434/api/version",
            code=302,
            msg="Found",
            hdrs={"Location": "https://example.com"},
            fp=None,
        )

    monkeypatch.setattr(doctor, "_open_no_redirect", _raise_redirect)

    result = doctor._check_ollama_server("http://localhost:11434", timeout_s=0.5)

    assert result.ok is False
    assert "redirect" in result.detail
    assert "blocked" in result.detail


def test_timeout_must_be_positive(capsys: pytest.CaptureFixture[str]) -> None:
    assert doctor._positive_timeout("0.5") == 0.5

    with pytest.raises(SystemExit):
        doctor.main(["--timeout", "0"])
    assert "timeout must be greater than 0 seconds" in capsys.readouterr().err


@pytest.mark.parametrize("raw_timeout", ["nan", "inf", "-inf"])
def test_timeout_must_be_finite(
    raw_timeout: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        doctor.main([f"--timeout={raw_timeout}"])
    assert "timeout must be finite" in capsys.readouterr().err


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


def test_main_text_output_exercises_real_aggregate_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        doctor,
        "_check_ollama_binary",
        lambda: (
            doctor.CheckResult("ollama-binary", True, "found /usr/bin/ollama", ""),
            "/usr/bin/ollama",
            "",
        ),
    )
    monkeypatch.setattr(
        doctor,
        "_check_ollama_version",
        lambda binary: (
            doctor.CheckResult("ollama-codex-cli-version", True, "CLI ready", ""),
            doctor.CheckResult("ollama-codex-app-version", True, "App ready", ""),
        ),
    )
    monkeypatch.setattr(
        doctor,
        "_check_ollama_server",
        lambda ollama_url, timeout_s: doctor.CheckResult(
            "ollama-local-server", True, "server ready", ""
        ),
    )
    monkeypatch.setattr(
        doctor,
        "_check_codex_binary",
        lambda: doctor.CheckResult("codex-binary", True, "Codex ready", ""),
    )

    exit_code = doctor.main([])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "ollama launch codex-app" in out
    assert "ollama launch codex" in out
    assert "host-config-write-guard" in out


def test_template_contains_expected_ollama_profile_contract() -> None:
    template = Path("docs/templates/codex.config.example.toml").read_text(encoding="utf-8")

    assert "sk-" not in template
    assert "/Users/" not in template
    assert "api_key" not in template.lower()
    assert "[model_providers.ollama-launch]" in template
    assert 'base_url = "http://localhost:11434/v1"' in template
    assert "[profiles.ollama-launch]" in template
    assert 'model = "gpt-oss:120b"' in template
    assert "[profiles.ollama-cloud]" in template
    assert 'model = "gpt-oss:120b-cloud"' in template
