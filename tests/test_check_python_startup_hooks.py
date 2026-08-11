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


def _run_startup_probe_with_site_setup(
    setup: str,
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    probe = "import site\n" + setup + "\n" + hook_guard.STARTUP_SAFE_SITE_PACKAGES_PROBE
    return subprocess.run(
        [sys.executable, "-P", "-S", "-c", probe],
        check=False,
        capture_output=True,
        cwd=cwd,
        env=hook_guard._startup_probe_environment(),
        text=True,
        timeout=30,
    )


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
    monkeypatch.setenv("PYTHONHOME", "/tmp/runtime-home")
    monkeypatch.setenv("PYTHONUSERBASE", "relative-userbase")
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")
    monkeypatch.setenv("PYTHONPLATLIBDIR", "runtime-lib")
    monkeypatch.setenv("PYTHONPATH", "/tmp/untrusted-imports")
    monkeypatch.setenv("PYTHONINSPECT", "1")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_command[:] = command
        observed_kwargs.clear()
        observed_kwargs.update(kwargs)
        return completed

    monkeypatch.setattr(hook_guard.subprocess, "run", fake_run)

    result = hook_guard.external_interpreter_site_packages(sys.executable)

    assert observed_command[:4] == [
        str(resolved.invocation_path),
        "-P",
        "-S",
        "-c",
    ]
    assert "site.addpackage = _skip_addpackage" in observed_command[4]
    assert "site.execsitecustomize = lambda: None" in observed_command[4]
    assert observed_kwargs.get("check") is True
    assert observed_kwargs.get("capture_output") is True
    observed_env = observed_kwargs.get("env")
    assert isinstance(observed_env, dict)
    assert observed_env["PYTHONUSERBASE"] == "relative-userbase"
    assert observed_env["PYTHONNOUSERSITE"] == "1"
    assert "PYTHONHOME" not in observed_env
    assert "PYTHONPLATLIBDIR" not in observed_env
    assert "PYTHONPATH" not in observed_env
    assert "PYTHONINSPECT" not in observed_env
    assert observed_kwargs.get("text") is True
    assert observed_kwargs.get("timeout") == 30
    assert result == [Path("/tmp/site-packages")]


def test_startup_safe_probe_skips_missing_and_none_site_getters() -> None:
    result = _run_startup_probe_with_site_setup(
        "site.ENABLE_USER_SITE = True\n"
        "site.getsitepackages = None\n"
        "site.getusersitepackages = lambda: None\n"
        "site.main = lambda: None"
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["site_packages"] == []


def test_startup_safe_probe_preserves_unexpected_getter_failure() -> None:
    result = _run_startup_probe_with_site_setup(
        "def raise_unexpected_failure():\n"
        "    raise RuntimeError('site getter failed')\n"
        "site.ENABLE_USER_SITE = False\n"
        "site.getsitepackages = raise_unexpected_failure\n"
        "site.main = lambda: None"
    )

    assert result.returncode != 0
    assert "site getter failed" in result.stderr


def test_startup_safe_probe_disables_readline_customization() -> None:
    result = _run_startup_probe_with_site_setup(
        "def forbidden_readline_customization():\n"
        "    raise RuntimeError('readline customization executed')\n"
        "site.ENABLE_USER_SITE = False\n"
        "site.getsitepackages = lambda: ['/tmp/site-packages']\n"
        "site.enablerlcompleter = forbidden_readline_customization\n"
        "site.main = lambda: site.enablerlcompleter()"
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["site_packages"] == ["/tmp/site-packages"]


def test_startup_safe_probe_normalizes_relative_site_paths(
    tmp_path: Path,
) -> None:
    relative_site_packages = Path("relative-userbase") / "site-packages"
    result = _run_startup_probe_with_site_setup(
        "site.ENABLE_USER_SITE = True\n"
        "site.getsitepackages = lambda: []\n"
        f"site.getusersitepackages = lambda: {str(relative_site_packages)!r}\n"
        "site.main = lambda: None",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["site_packages"] == [str(tmp_path / relative_site_packages)]


def test_external_interpreter_ignores_pythonhome_code_loading_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_python_executable = getattr(sys, "_base_executable", sys.executable)
    empty_python_home = tmp_path / "empty-python-home"
    empty_python_home.mkdir()
    userbase = tmp_path / "controlled-userbase"
    monkeypatch.setenv("PYTHONUSERBASE", str(userbase))
    monkeypatch.delenv("PYTHONNOUSERSITE", raising=False)
    monkeypatch.delenv("PYTHONHOME", raising=False)

    baseline = hook_guard.external_interpreter_site_packages(base_python_executable)
    monkeypatch.setenv("PYTHONHOME", str(empty_python_home))

    discovered = hook_guard.external_interpreter_site_packages(base_python_executable)

    assert discovered == baseline
    assert any(userbase in path.parents for path in discovered)


def test_external_interpreter_normalizes_relative_pythonuserbase_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_python_executable = getattr(sys, "_base_executable", sys.executable)
    relative_userbase = Path("relative-userbase")
    shadow_marker = tmp_path / "shadow-json-imported"
    (tmp_path / "json.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(shadow_marker)!r}).write_text('executed')\n"
        "raise RuntimeError('cwd shadow import executed')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONUSERBASE", str(relative_userbase))
    monkeypatch.delenv("PYTHONNOUSERSITE", raising=False)

    discovered = hook_guard.external_interpreter_site_packages(base_python_executable)

    expected_userbase = tmp_path / relative_userbase
    assert any(expected_userbase in path.parents for path in discovered)
    assert all(path.is_absolute() for path in discovered)
    assert not shadow_marker.exists()


def test_external_interpreter_honors_pythonno_usersite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_python_executable = getattr(sys, "_base_executable", sys.executable)
    userbase = tmp_path / "disabled-userbase"
    monkeypatch.setenv("PYTHONUSERBASE", str(userbase))
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")

    discovered = hook_guard.external_interpreter_site_packages(base_python_executable)

    assert all(userbase not in path.parents for path in discovered)


def test_external_interpreter_accepts_verified_resolved_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation = tmp_path / "python"
    try:
        invocation.symlink_to(Path(sys.executable).resolve(strict=True))
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    resolved = hook_guard.resolve_python_executable(str(invocation))
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "executable": str(resolved.resolved_target),
                "prefix": "/tmp/venv",
                "base_prefix": "/tmp/base",
                "site_packages": ["/tmp/site-packages"],
            }
        ),
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    result = hook_guard.external_interpreter_site_packages(str(invocation))

    assert result == [Path("/tmp/site-packages")]


def test_external_interpreter_rejects_unrelated_executable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unrelated = tmp_path / "unrelated-python"
    unrelated.write_text("#!/bin/sh\n", encoding="utf-8")
    unrelated.chmod(unrelated.stat().st_mode | stat.S_IXUSR)
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "executable": str(unrelated),
                "prefix": "/tmp/venv",
                "base_prefix": "/tmp/base",
                "site_packages": ["/tmp/site-packages"],
            }
        ),
        stderr="",
    )
    monkeypatch.setattr(hook_guard.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match="executable mismatch"):
        hook_guard.external_interpreter_site_packages(sys.executable)


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
