"""Deterministic tests for local verify environment parity checks."""

from __future__ import annotations

import os
import hashlib
import subprocess
import venv
import re
import sys
from pathlib import Path

import pytest

import scripts.ci.check_local_verify_environment as env_gate
from scripts.ci import check_python_startup_hooks as guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_collect_missing_modules_returns_only_failed_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import(module_name: str) -> str | None:
        if module_name == "coverage":
            return "No module named 'coverage'"
        return None

    monkeypatch.setattr(env_gate, "_import_module", fake_import)

    missing = env_gate.collect_missing_modules(
        (
            ("pytest", "test-fast"),
            ("coverage", "diff-cov"),
        ),
    )

    assert missing == [("coverage", "diff-cov", "No module named 'coverage'")]


def test_build_failure_output_includes_recovery_commands() -> None:
    lines = env_gate.build_failure_output(
        python_executable=Path("/tmp/.venv/bin/python"),
        broken_console_wrappers=[],
        missing_modules=[
            (
                "diff_cover.diff_cover_tool",
                "diff-cov",
                "No module named 'diff_cover'",
            )
        ],
        unexpected_startup_hooks=[],
    )

    assert "ERROR: local verify environment is incomplete." in lines
    assert any("PULSEPLATE_PYTHON_INDEX_URL" in line for line in lines)
    assert any("make venv" in line for line in lines)
    assert any("make venv-sync" in line for line in lines)
    assert "Missing verify-critical Python modules:" in lines


def test_build_failure_output_includes_broken_console_wrappers() -> None:
    bin_dir = Path("/tmp/.venv/bin")
    lines = env_gate.build_failure_output(
        python_executable=Path("/tmp/.venv/bin/python"),
        broken_console_wrappers=[
            ("flake8", "stale shebang interpreter missing: /tmp/deleted-python")
        ],
        missing_modules=[],
        unexpected_startup_hooks=[],
        venv_bin_dir=bin_dir,
    )

    label = env_gate._format_venv_bin_display(bin_dir)
    assert f"Stale or broken venv console scripts ({label}):" in lines
    assert "- flake8 :: stale shebang interpreter missing: /tmp/deleted-python" in lines
    assert any("make venv-sync" in line for line in lines)


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "clean",
        "missing-clean",
        "extra-clean",
        "missing-header",
        "empty",
        "mixed",
        "duplicate",
        "allowed",
        "long-statement",
        "extra-root",
        "footer",
        "zero",
        "not-import",
        "timeout",
        "oserror",
        "decode",
        "other-exit",
    ],
)
def test_collect_unexpected_startup_hooks_uses_guard_subprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str
) -> None:
    token = "synthetic-verifier-secret"
    home, userbase = tmp_path / "actual-home", tmp_path / "custom-userbase"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PYTHONUSERBASE", str(userbase))
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")
    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "PIP_INDEX_URL",
        "PYTHONPATH",
        "LD_PRELOAD",
        "BASH_ENV",
    ):
        monkeypatch.setenv(key, token)
    python = tmp_path / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    monkeypatch.setattr(env_gate, "VENV_PYTHON", python)
    monkeypatch.setattr(env_gate, "REPO_ROOT", tmp_path)
    path = tmp_path / (token + ".pth")
    lines = guard.format_failure_lines(
        [
            guard.ExecutablePthFinding(path=path, line_number=2, line="import " + token),
        ]
    )
    if case == "missing-header":
        del lines[1]
    elif case == "empty":
        del lines[2:-1]
    elif case == "mixed":
        lines.insert(-1, token)
    elif case == "duplicate":
        lines.insert(-1, lines[2])
    elif case == "allowed":
        lines[2] = "- /fixture/distutils-precedence.pth:1 :: import os"
    elif case == "long-statement":
        lines[2] += token * 1024
    elif case == "extra-root":
        lines.insert(-1, "- relative.pth:1 :: import os")
    elif case == "footer":
        lines[-1] = token
    elif case == "zero":
        lines[2] = lines[2].replace(":2 ::", ":0 ::")
    elif case == "not-import":
        lines[2] = lines[2].replace(" :: import ", " :: ")
    raw = "\n".join(lines) + "\n"
    status = 1
    clean = "startup-hook-guard: no unexpected executable .pth files detected.\n"
    if case in {"clean", "missing-clean", "extra-clean"}:
        status = 0
        raw = {"clean": clean, "missing-clean": "", "extra-clean": clean + token}[case]
    if case == "other-exit":
        status = 2

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert argv == [str(python), "-P", "-S", guard.__file__, "--python-executable", str(python)]
        assert kwargs["cwd"] == tmp_path and kwargs["timeout"] == 60
        assert kwargs["stdin"] == kwargs["stderr"] == subprocess.DEVNULL
        env = kwargs["env"]
        assert isinstance(env, dict) and token not in env.values()
        assert env["HOME"] == str(home) and env["PYTHONUSERBASE"] == str(userbase)
        assert env["PYTHONNOUSERSITE"] == "1"
        if case == "timeout":
            raise subprocess.TimeoutExpired([token], 60, output=token, stderr=token)
        if case == "oserror":
            raise OSError(token)
        if case == "decode":
            raise UnicodeDecodeError("utf8", token.encode(), 0, 1, token)
        return subprocess.CompletedProcess(argv, status, stdout=raw, stderr=token)

    monkeypatch.setattr(env_gate.subprocess, "run", run)
    if case in {"valid", "long-statement"}:
        assert env_gate.collect_unexpected_startup_hooks() == [
            env_gate.StartupHookFinding(hashlib.sha256(str(path).encode()).hexdigest()[:16], 2)
        ]
    elif case == "clean":
        assert env_gate.collect_unexpected_startup_hooks() == []
    else:
        with pytest.raises(RuntimeError) as failure:
            env_gate.collect_unexpected_startup_hooks()
        assert token not in str(failure.value)
        assert failure.value.__cause__ is None and failure.value.__context__ is None


def test_real_fixed_guard_reports_finding_without_running_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_root = tmp_path / ".venv"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(env_root)
    python = env_root / "bin/python"
    monkeypatch.setattr(env_gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(env_gate, "VENV_PYTHON", python)
    hostile = tmp_path / "imports"
    hostile.mkdir()
    marker = tmp_path / "startup-marker"
    (hostile / "json.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\nraise SystemExit(76)\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(hostile))
    monkeypatch.setenv("PYTHONUSERBASE", str(tmp_path / "actual-userbase"))
    control = subprocess.run(
        [str(python), "-P", "-S", "-c", "import json"],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "PYTHONPATH": str(hostile)},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert control.returncode == 76 and marker.read_text() == "executed"
    marker.unlink()
    assert env_gate.collect_unexpected_startup_hooks() == []
    (site_dir,) = (env_root / "lib").glob("python*/site-packages")
    leaf = site_dir / "sensitive-fixture-name.pth"
    leaf.write_text(f"# first line\nimport pathlib; pathlib.Path({str(marker)!r}).touch()\n")
    findings = env_gate.collect_unexpected_startup_hooks()
    assert findings == [
        env_gate.StartupHookFinding(hashlib.sha256(str(leaf).encode()).hexdigest()[:16], 2)
    ]
    assert not marker.exists() and "sensitive-fixture-name" not in repr(findings)


def test_main_fails_when_venv_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(env_gate, "VENV_PYTHON", tmp_path / ".venv" / "bin" / "python")

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Run `make venv` before `make verify`." in captured.out


def test_main_fails_when_running_outside_repo_venv(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    system_python = tmp_path / "system-python"
    system_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(env_gate.sys, "executable", str(system_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(tmp_path / "system-prefix"))

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "verify-env must run inside the repo .venv interpreter." in captured.out
    assert "PULSEPLATE_PYTHON_INDEX_URL" in captured.out


def test_main_fails_when_verify_dependencies_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(
        env_gate,
        "collect_missing_modules",
        lambda: [
            (
                "diff_cover.diff_cover_tool",
                "diff-cov",
                "No module named 'diff_cover'",
            ),
        ],
    )
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])
    monkeypatch.setattr(env_gate, "collect_broken_console_wrappers", lambda: [])

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Missing verify-critical Python modules:" in captured.out
    assert "diff_cover.diff_cover_tool [diff-cov]" in captured.out


def test_main_passes_when_venv_and_dependencies_are_ready(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

    result = env_gate.main()

    assert result == 0
    captured = capsys.readouterr()
    assert "verify-env: local verify environment passed." in captured.out


def test_main_fails_when_console_wrapper_has_stale_absolute_shebang(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    stale_wrapper = tmp_path / ".venv" / "bin" / "flake8"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")
    stale_wrapper.write_text("#!/tmp/deleted-python\nprint('stale')\n", encoding="utf-8")
    os.chmod(stale_wrapper, 0o755)

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    display = env_gate._format_venv_bin_display(env_gate.VENV_BIN_DIR)
    assert f"Stale or broken venv console scripts ({display}):" in captured.out
    assert "flake8" in captured.out
    assert "stale shebang interpreter missing" in captured.out


def test_main_fails_when_console_wrapper_is_not_executable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    flake8_wrapper = tmp_path / ".venv" / "bin" / "flake8"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")
    flake8_wrapper.write_text(f"#!{fake_python}\n", encoding="utf-8")
    os.chmod(flake8_wrapper, 0o644)

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    display = env_gate._format_venv_bin_display(env_gate.VENV_BIN_DIR)
    assert f"Stale or broken venv console scripts ({display}):" in captured.out
    assert "flake8" in captured.out
    assert "not executable" in captured.out


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink and mode semantics")
def test_main_fails_when_console_wrapper_is_dangling_symlink(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    flake8_wrapper = tmp_path / ".venv" / "bin" / "flake8"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")
    flake8_wrapper.symlink_to(tmp_path / "nonexistent-console-target")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    display = env_gate._format_venv_bin_display(env_gate.VENV_BIN_DIR)
    assert f"Stale or broken venv console scripts ({display}):" in captured.out
    assert "flake8" in captured.out
    assert "broken or dangling symlink" in captured.out


def test_collect_broken_console_wrappers_skips_missing_scripts(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)

    assert env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir) == []


def test_collect_broken_console_wrappers_ignores_env_shebang(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    wrapper = bin_dir / "flake8"
    wrapper.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    os.chmod(wrapper, 0o755)

    assert env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir) == []


def test_collect_broken_console_wrappers_reports_resolve_runtimeerror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Broken venvs may trigger RuntimeError from Path.resolve() on interpreter loops."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    interp = tmp_path / "interp"
    interp.touch()
    wrapper = bin_dir / "flake8"
    wrapper.write_text(f"#!{interp}\n", encoding="utf-8")
    os.chmod(wrapper, 0o755)

    def resolve_with_loop(path: Path) -> Path:
        if path == interp:
            raise RuntimeError("symlink loop")
        return path.resolve()

    monkeypatch.setattr(env_gate, "_resolve_interpreter_path", resolve_with_loop)

    out = env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir)
    assert len(out) == 1
    assert out[0][0] == "flake8"
    assert "resolve error" in out[0][1]
    assert "symlink loop" in out[0][1]


def test_collect_broken_console_wrappers_reports_empty_script(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    wrapper = bin_dir / "flake8"
    wrapper.write_text("", encoding="utf-8")
    os.chmod(wrapper, 0o755)

    out = env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir)
    assert out == [("flake8", "empty script")]


def test_collect_broken_console_wrappers_reports_not_regular_file(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    wrapper = bin_dir / "flake8"
    wrapper.mkdir()

    out = env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir)
    assert out == [("flake8", "not a regular file")]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX chmod executable bit")
def test_collect_broken_console_wrappers_reports_non_executable_interpreter(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    interp = tmp_path / "interp"
    interp.write_text("", encoding="utf-8")
    os.chmod(interp, 0o644)
    wrapper = bin_dir / "flake8"
    wrapper.write_text(f"#!{interp}\n", encoding="utf-8")
    os.chmod(wrapper, 0o755)

    out = env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir)
    assert len(out) == 1
    assert out[0][0] == "flake8"
    assert "not executable" in out[0][1]


def test_collect_broken_console_wrappers_strips_utf8_bom_before_shebang_parse(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    wrapper = bin_dir / "flake8"
    wrapper.write_text("\ufeff#!/no_such_interpreter_verify_env_test\n", encoding="utf-8")
    os.chmod(wrapper, 0o755)

    out = env_gate.collect_broken_console_wrappers(venv_bin_dir=bin_dir)
    assert len(out) == 1
    assert out[0][0] == "flake8"
    assert "stale shebang interpreter missing" in out[0][1]


def test_main_fails_when_unexpected_startup_hook_is_present(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_broken_console_wrappers", lambda: [])
    monkeypatch.setattr(
        env_gate,
        "collect_unexpected_startup_hooks",
        lambda: [
            env_gate.StartupHookFinding(
                location_id="1234567890abcdef",
                line_number=1,
            )
        ],
    )

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Unexpected executable startup hooks (.pth):" in captured.out
    assert ".pth location sha256:1234567890abcdef, line 1" in captured.out
    assert "import os" not in captured.out


def _target_recipe(makefile_text: str, target_name: str) -> str:
    """Return the recipe body for a Makefile target."""

    target_pattern = re.compile(rf"(?m)^{re.escape(target_name)}:.*\n(?P<body>(?:\t[^\n]*\n)+)")
    match = target_pattern.search(makefile_text)
    assert match, f"missing Makefile target: {target_name}"
    return match.group("body")


def test_verify_critical_make_targets_use_repo_interpreter_module_mode() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    expected_recipe_parts = {
        "lint": ("$(DEV_PYTHON) -m flake8",),
        "typecheck": (
            "$(DEV_PYTHON) -m mypy",
            "--no-incremental",
            "--cache-dir=/dev/null",
        ),
        "test-fast": ("$(DEV_PYTHON) -m pytest", "tests/edges", "--maxfail=3"),
        "cov": (
            "$(DEV_PYTHON) -m coverage erase",
            "$(DEV_PYTHON) -m coverage run -m pytest -q",
            "$(DEV_PYTHON) -m coverage report -m",
            "$(DEV_PYTHON) -m coverage xml",
        ),
        "diff-cov": (
            "$(DEV_PYTHON) -m coverage erase",
            "$(DEV_PYTHON) -m coverage run -m pytest -q",
            "$(DEV_PYTHON) -m diff_cover.diff_cover_tool",
            "--compare-branch=origin/main",
            "--fail-under=97",
        ),
    }

    for target_name, required_parts in expected_recipe_parts.items():
        recipe_body = _target_recipe(makefile_text, target_name)
        assert "$(DEV_PYTHON) -m" in recipe_body
        for required_part in required_parts:
            assert required_part in recipe_body


@pytest.mark.parametrize("target", ["guard", "venv"])
def test_foreign_startup_verifier_input_is_rejected_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    foreign = tmp_path / "synthetic-private-path"
    foreign.write_text("fixture")
    monkeypatch.setattr(
        env_gate, "STARTUP_HOOK_GUARD" if target == "guard" else "VENV_PYTHON", foreign
    )
    monkeypatch.setattr(
        env_gate.subprocess, "run", lambda *_a, **_k: pytest.fail("foreign input launched")
    )
    with pytest.raises(RuntimeError, match="Local startup guard inputs are unavailable"):
        env_gate.collect_unexpected_startup_hooks()
