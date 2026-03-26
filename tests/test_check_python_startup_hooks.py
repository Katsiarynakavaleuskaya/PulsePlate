"""Deterministic tests for executable Python startup-hook guards."""

from __future__ import annotations

from pathlib import Path

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
    (site_packages / "distutils-precedence.pth").write_text("import os\n", encoding="utf-8")

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


def test_collect_site_packages_from_site_module_skips_disabled_user_site() -> None:
    expected_site_packages = Path("/tmp/repo-venv/lib/python3.13/site-packages").resolve()

    class FakeSiteModule:
        ENABLE_USER_SITE = False

        @staticmethod
        def getsitepackages() -> list[str]:
            return ["/tmp/repo-venv/lib/python3.13/site-packages"]

        @staticmethod
        def getusersitepackages() -> str:
            return "/tmp/user-site/lib/python3.13/site-packages"

    site_packages = hook_guard.collect_site_packages_from_site_module(FakeSiteModule)

    assert site_packages == [expected_site_packages]


def test_external_interpreter_site_packages_infers_virtualenv_layout_without_execution(
    tmp_path: Path,
) -> None:
    venv_root = tmp_path / "venv"
    python_executable = venv_root / "bin" / "python"
    site_packages = venv_root / "lib" / "python3.13" / "site-packages"
    python_executable.parent.mkdir(parents=True)
    python_executable.write_text("", encoding="utf-8")
    site_packages.mkdir(parents=True)

    discovered_paths = hook_guard.external_interpreter_site_packages(str(python_executable))

    assert discovered_paths == [site_packages.resolve()]


def test_site_packages_for_interpreter_resolves_command_name_via_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    venv_root = tmp_path / "venv"
    python_executable = venv_root / "bin" / "python"
    site_packages = venv_root / "lib" / "python3.13" / "site-packages"
    python_executable.parent.mkdir(parents=True)
    python_executable.write_text("", encoding="utf-8")
    site_packages.mkdir(parents=True)

    monkeypatch.setattr(hook_guard.shutil, "which", lambda command: str(python_executable))
    monkeypatch.setattr(hook_guard.sys, "executable", str(tmp_path / "system-python"))

    discovered_paths = hook_guard.site_packages_for_interpreter("python")

    assert discovered_paths == [site_packages.resolve()]


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
