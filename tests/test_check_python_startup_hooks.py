"""Deterministic tests for executable Python startup-hook guards."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import scripts.ci.check_python_startup_hooks as hook_guard


def test_extract_executable_lines_returns_only_import_lines() -> None:
    contents = "\n".join(
        (
            "relative/path",
            "import os",
            "  import sys",
            "# import ignored",
        )
    )

    assert hook_guard.extract_executable_lines(contents) == [
        (2, "import os"),
        (3, "  import sys"),
    ]


def test_collect_unexpected_executable_pth_files_ignores_allowlisted_names(
    tmp_path: Path,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "distutils-precedence.pth").write_text(
        "import os\n",
        encoding="utf-8",
    )

    findings = hook_guard.collect_unexpected_executable_pth_files([site_packages])

    assert findings == []


def test_collect_unexpected_executable_pth_files_ignores_cuda_vendor_redirector(
    tmp_path: Path,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "_cuda_bindings_redirector.pth").write_text(
        "import _cuda_bindings_redirector\n",
        encoding="utf-8",
    )

    findings = hook_guard.collect_unexpected_executable_pth_files([site_packages])

    assert findings == []


def test_collect_unexpected_executable_pth_files_flags_unknown_import_hook(
    tmp_path: Path,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    malicious = site_packages / "litellm_init.pth"
    malicious.write_text("import os\nrelative/path\n", encoding="utf-8")

    findings = hook_guard.collect_unexpected_executable_pth_files([site_packages])

    assert findings == [
        hook_guard.ExecutablePthFinding(
            path=malicious,
            line_number=1,
            line="import os",
        )
    ]


def test_format_failure_lines_is_deterministic() -> None:
    finding = hook_guard.ExecutablePthFinding(
        path=Path("/tmp/litellm_init.pth"),
        line_number=1,
        line="import os",
    )

    lines = hook_guard.format_failure_lines([finding])

    assert lines[0] == "ERROR: unexpected executable Python startup hook (.pth) detected."
    assert "- /tmp/litellm_init.pth:1 :: import os" in lines


def test_main_passes_when_no_findings(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(hook_guard, "current_interpreter_site_packages", lambda: [])

    result = hook_guard.main([])

    assert result == 0
    assert (
        "startup-hook-guard: no unexpected executable .pth files detected."
        in capsys.readouterr().out
    )


def test_external_interpreter_site_packages_uses_startup_safe_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='["/tmp/site-packages"]',
        stderr="",
    )
    observed_command: list[str] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_command[:] = command
        return completed

    monkeypatch.setattr(hook_guard.subprocess, "run", fake_run)

    result = hook_guard.external_interpreter_site_packages("/usr/bin/python3")

    assert observed_command[:3] == ["/usr/bin/python3", "-S", "-c"]
    assert "import json, site" in observed_command[3]
    assert result == [Path("/tmp/site-packages")]


def test_external_interpreter_site_packages_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="[]",
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    assert hook_guard.external_interpreter_site_packages("/usr/bin/python3") == []


def test_external_interpreter_site_packages_wraps_subprocess_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_called_process_error(*args: object, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["python3", "-S", "-c", "probe"],
            stderr="boom",
        )

    monkeypatch.setattr(hook_guard.subprocess, "run", raise_called_process_error)

    with pytest.raises(RuntimeError, match="Unable to probe site-packages"):
        hook_guard.external_interpreter_site_packages("/usr/bin/python3")
