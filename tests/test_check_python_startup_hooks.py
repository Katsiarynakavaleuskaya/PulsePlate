"""Deterministic tests for executable Python startup-hook guards."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import venv
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


def test_resolve_python_executable_uses_which_for_bare_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interpreter = Path(sys.executable)
    monkeypatch.setattr(
        hook_guard.shutil,
        "which",
        lambda command: str(interpreter) if command == "repo-python" else None,
    )

    resolved = hook_guard.resolve_python_executable("repo-python")

    assert resolved.invocation_path == (interpreter.parent.resolve(strict=True) / interpreter.name)
    assert resolved.resolved_target == interpreter.resolve(strict=True)


def test_resolve_python_executable_preserves_final_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation = tmp_path / "python"
    try:
        invocation.symlink_to(Path(sys.executable).resolve(strict=True))
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    monkeypatch.chdir(tmp_path)

    resolved = hook_guard.resolve_python_executable("./python")

    assert resolved.invocation_path == invocation
    assert resolved.invocation_path.is_symlink()
    assert resolved.resolved_target == Path(sys.executable).resolve(strict=True)


@pytest.mark.parametrize("value", ["", "   ", "missing-python"])
def test_resolve_python_executable_rejects_unresolved_input(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hook_guard.shutil, "which", lambda command: None)

    with pytest.raises(RuntimeError, match="Python executable|Unable to resolve"):
        hook_guard.resolve_python_executable(value)


def test_resolve_python_executable_rejects_invalid_targets(tmp_path: Path) -> None:
    directory = tmp_path / "python-dir"
    directory.mkdir()
    non_executable = tmp_path / "python-file"
    non_executable.write_text("not executable\n", encoding="utf-8")
    non_executable.chmod(stat.S_IRUSR | stat.S_IWUSR)

    candidates = [directory, tmp_path / "missing"]
    if os.name != "nt":
        candidates.append(non_executable)

    for candidate in candidates:
        with pytest.raises(RuntimeError, match="Python executable|Unable to resolve"):
            hook_guard.resolve_python_executable(str(candidate))


def test_resolve_python_executable_rejects_dangling_symlink(tmp_path: Path) -> None:
    invocation = tmp_path / "python"
    try:
        invocation.symlink_to(tmp_path / "missing-target")
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")

    with pytest.raises(RuntimeError, match="Unable to resolve"):
        hook_guard.resolve_python_executable(str(invocation))


def test_revalidate_python_executable_rejects_target_swap(tmp_path: Path) -> None:
    first_target = tmp_path / "python-first"
    first_target.write_text("#!/bin/sh\n", encoding="utf-8")
    first_target.chmod(first_target.stat().st_mode | stat.S_IXUSR)
    second_target = tmp_path / "python-second"
    second_target.write_text("#!/bin/sh\n", encoding="utf-8")
    second_target.chmod(second_target.stat().st_mode | stat.S_IXUSR)
    invocation = tmp_path / "python"
    try:
        invocation.symlink_to(first_target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    resolved = hook_guard.resolve_python_executable(str(invocation))
    invocation.unlink()
    invocation.symlink_to(second_target)

    with pytest.raises(RuntimeError, match="changed before launch"):
        hook_guard._revalidate_python_executable(resolved)


def test_resolve_python_executable_rejects_non_regular_target(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable on this platform")
    fifo = tmp_path / "python-fifo"
    os.mkfifo(fifo)

    with pytest.raises(RuntimeError, match="executable regular file"):
        hook_guard.resolve_python_executable(str(fifo))


def test_external_interpreter_rejects_invalid_target_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        hook_guard.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("subprocess must not run"),
    )

    with pytest.raises(RuntimeError, match="Unable to resolve"):
        hook_guard.external_interpreter_site_packages(str(tmp_path / "missing"))


def test_external_interpreter_site_packages_uses_startup_safe_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = hook_guard.resolve_python_executable(sys.executable)
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "executable": str(resolved.invocation_path),
                "prefix": "/tmp/venv",
                "base_prefix": "/tmp/base",
                "site_packages": ["/tmp/site-packages"],
            }
        ),
        stderr="",
    )
    observed_command: list[str] = []
    observed_kwargs: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_command[:] = command
        observed_kwargs.clear()
        observed_kwargs.update(kwargs)
        return completed

    monkeypatch.setattr(hook_guard.subprocess, "run", fake_run)

    result = hook_guard.external_interpreter_site_packages(sys.executable)

    assert observed_command[:4] == [
        str(resolved.invocation_path),
        "-I",
        "-S",
        "-c",
    ]
    assert "site.addpackage = _skip_addpackage" in observed_command[4]
    assert "site.execsitecustomize = lambda: None" in observed_command[4]
    assert observed_kwargs.get("check") is True
    assert observed_kwargs.get("capture_output") is True
    assert observed_kwargs.get("text") is True
    assert observed_kwargs.get("timeout") == 30
    assert result == [Path("/tmp/site-packages")]


def test_external_interpreter_site_packages_rejects_empty_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = hook_guard.resolve_python_executable(sys.executable)
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "executable": str(resolved.invocation_path),
                "prefix": "/tmp/venv",
                "base_prefix": "/tmp/base",
                "site_packages": [],
            }
        ),
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match="empty path inventory"):
        hook_guard.external_interpreter_site_packages(sys.executable)


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
        hook_guard.external_interpreter_site_packages(sys.executable)


def test_external_interpreter_site_packages_wraps_timeout_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(
            cmd=["python3", "-S", "-c", "probe"],
            timeout=30,
        )

    monkeypatch.setattr(hook_guard.subprocess, "run", raise_timeout)

    with pytest.raises(RuntimeError, match="Timed out probing site-packages"):
        hook_guard.external_interpreter_site_packages(sys.executable)


def test_external_interpreter_site_packages_wraps_json_decode_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="not valid json",
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match="Unable to parse site-packages"):
        hook_guard.external_interpreter_site_packages(sys.executable)


def test_external_interpreter_site_packages_rejects_non_object_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='["/tmp/site-packages"]',
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match="expected JSON object"):
        hook_guard.external_interpreter_site_packages(sys.executable)


def test_external_interpreter_discovers_venv_without_running_startup_hooks(
    tmp_path: Path,
) -> None:
    venv_dir = tmp_path / "target-venv"
    venv.EnvBuilder(with_pip=False).create(venv_dir)
    if os.name == "nt":
        python_executable = venv_dir / "Scripts" / "python.exe"
        site_packages = venv_dir / "Lib" / "site-packages"
    else:
        python_executable = venv_dir / "bin" / "python"
        site_packages = (
            venv_dir
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
    site_packages.mkdir(parents=True, exist_ok=True)
    pth_marker = tmp_path / "pth-executed"
    sitecustomize_marker = tmp_path / "sitecustomize-executed"
    usercustomize_marker = tmp_path / "usercustomize-executed"
    (site_packages / "malicious.pth").write_text(
        f"import pathlib; pathlib.Path({str(pth_marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    (site_packages / "sitecustomize.py").write_text(
        f"import pathlib; pathlib.Path({str(sitecustomize_marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    (site_packages / "usercustomize.py").write_text(
        f"import pathlib; pathlib.Path({str(usercustomize_marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    discovered = hook_guard.external_interpreter_site_packages(str(python_executable))

    assert site_packages in discovered
    assert not pth_marker.exists()
    assert not sitecustomize_marker.exists()
    assert not usercustomize_marker.exists()
