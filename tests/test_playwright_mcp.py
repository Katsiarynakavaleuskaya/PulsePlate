"""Tests for the repo-owned Playwright MCP/toolchain helper."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import playwright_mcp


def _configure_fake_repo_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frontend_dir = tmp_path / "frontend"
    node_modules_dir = frontend_dir / "node_modules"
    playwright_pkg_dir = node_modules_dir / "playwright"
    wrapper_path = tmp_path / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"
    browser_cache_dir = tmp_path / "Library" / "Caches" / "ms-playwright" / "chromium-1234"

    playwright_pkg_dir.mkdir(parents=True)
    wrapper_path.parent.mkdir(parents=True)
    wrapper_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    browser_cache_dir.mkdir(parents=True)
    nvmrc_path = tmp_path / ".nvmrc"
    nvmrc_path.write_text("24.16.0\n", encoding="utf-8")

    monkeypatch.setattr(playwright_mcp, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(playwright_mcp, "FRONTEND_DIR", frontend_dir)
    monkeypatch.setattr(playwright_mcp, "NODE_MODULES_PATH", node_modules_dir)
    monkeypatch.setattr(playwright_mcp, "PLAYWRIGHT_PACKAGE_PATH", playwright_pkg_dir)
    monkeypatch.setattr(playwright_mcp, "PLAYWRIGHT_WRAPPER_PATH", wrapper_path)
    monkeypatch.setattr(playwright_mcp, "PLAYWRIGHT_CACHE_DIR", browser_cache_dir.parent)
    monkeypatch.setattr(playwright_mcp, "NVMRC_PATH", nvmrc_path)


@pytest.mark.parametrize(
    ("platform_name", "env_name", "env_value", "expected"),
    [
        ("darwin", None, None, Path.home() / "Library" / "Caches" / "ms-playwright"),
        ("linux", "XDG_CACHE_HOME", "/tmp/xdg-cache", Path("/tmp/xdg-cache") / "ms-playwright"),
        (
            "win32",
            "LOCALAPPDATA",
            "C:/Users/test/AppData/Local",
            Path("C:/Users/test/AppData/Local") / "ms-playwright",
        ),
    ],
)
def test_playwright_cache_dir_is_platform_aware(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
    env_name: str | None,
    env_value: str | None,
    expected: Path,
) -> None:
    monkeypatch.setattr(playwright_mcp.sys, "platform", platform_name)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    if env_name is not None and env_value is not None:
        monkeypatch.setenv(env_name, env_value)

    assert playwright_mcp._playwright_cache_dir() == expected


def test_playwright_cache_dir_prefers_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "~/custom-cache")

    assert playwright_mcp._playwright_cache_dir() == Path("~/custom-cache").expanduser()


def test_playwright_cache_dir_uses_repo_local_browsers_when_env_is_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frontend_dir = tmp_path / "frontend"
    monkeypatch.setattr(playwright_mcp, "FRONTEND_DIR", frontend_dir)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "0")

    assert (
        playwright_mcp._playwright_cache_dir()
        == frontend_dir / "node_modules" / "playwright-core" / ".local-browsers"
    )


def test_doctor_fails_on_exact_node_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(playwright_mcp, "_current_node_version", lambda node_bin: "25.6.1")

    results = playwright_mcp._build_doctor_report()

    node_result = next(result for result in results if result.name == "node-version")
    assert node_result.ok is False
    assert "24.16.0" in node_result.detail
    assert "25.6.1" in node_result.detail


def test_doctor_passes_when_repo_prerequisites_are_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(playwright_mcp, "_current_node_version", lambda node_bin: "24.16.0")

    results = playwright_mcp._build_doctor_report()

    assert all(result.ok for result in results)
    assert playwright_mcp._doctor_exit_code(results) == 0


def test_doctor_accepts_nvmrc_version_with_v_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    playwright_mcp.NVMRC_PATH.write_text("v24.16.0\n", encoding="utf-8")
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(playwright_mcp, "_current_node_version", lambda node_bin: "24.16.0")

    results = playwright_mcp._build_doctor_report()

    node_result = next(result for result in results if result.name == "node-version")
    assert node_result.ok is True
    assert "24.16.0" in node_result.detail


def test_doctor_reports_missing_nvmrc_without_hiding_other_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(playwright_mcp, "NVMRC_PATH", tmp_path / ".nvmrc-missing")
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: None)

    results = playwright_mcp._build_doctor_report()

    details_by_name = {result.name: result.detail for result in results}
    assert "node-version" in details_by_name
    assert "npm" in details_by_name
    assert "npx" in details_by_name
    assert "codex-playwright-wrapper" in details_by_name


def test_main_doctor_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        playwright_mcp,
        "_build_doctor_report",
        lambda: [playwright_mcp.CheckResult(name="node-version", ok=True, detail="ok")],
    )

    exit_code = playwright_mcp.main(["doctor", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload == [{"name": "node-version", "ok": True, "detail": "ok", "remediation": None}]


@pytest.mark.parametrize("cache", [None, "0", "relative cache", "/explicit/cache"])
@pytest.mark.parametrize("status", [0, 7])
def test_install_browser_runs_repo_local_playwright_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cache: str | None, status: int
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    node = tmp_path / "node"
    node.write_bytes(b"synthetic executable")
    node.chmod(0o700)
    package = playwright_mcp.PLAYWRIGHT_PACKAGE_PATH
    metadata = {"name": "playwright", "version": "1.2.3", "bin": {"playwright": "cli.js"}}
    (package / "package.json").write_text(json.dumps(metadata))
    (package / "cli.js").write_text("// fixture only")
    (playwright_mcp.FRONTEND_DIR / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {"node_modules/playwright": metadata}})
    )
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda _name: str(node))
    monkeypatch.setattr(
        playwright_mcp,
        "_current_node_version",
        lambda path: "24.16.0" if path == str(node) else None,
    )
    if cache is None:
        monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    else:
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", cache)
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST", "https://fixture.invalid")
    monkeypatch.setenv("HTTPS_PROXY", "http://local-proxy.invalid")
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "NODE_OPTIONS", "NODE_PATH", "LD_PRELOAD"):
        monkeypatch.setenv(name, "synthetic-private")
    calls = []

    def fake_run(
        argv: list[str], *, cwd: Path, check: bool, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert cwd == playwright_mcp.FRONTEND_DIR and not check
        assert env.get("PLAYWRIGHT_BROWSERS_PATH") == cache
        assert env["PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST"] == "https://fixture.invalid"
        assert env["HTTPS_PROXY"] == "http://local-proxy.invalid"
        assert "synthetic-private" not in env.values()
        return subprocess.CompletedProcess(argv, status)

    monkeypatch.setattr(playwright_mcp.subprocess, "run", fake_run)
    assert playwright_mcp.main(["install-browser"]) == status
    assert calls == [[str(node), str(package / "cli.js"), "install", "chromium"]]


@pytest.mark.parametrize(
    "fault",
    [
        "missing-lock",
        "missing-package",
        "name",
        "version",
        "wrong-bin",
        "absolute",
        "escape",
        "missing-cli",
        "cli-symlink",
        "hardlink",
        "package-symlink",
        "node-modules-symlink",
        "changed-node",
        "relative-node",
    ],
)
def test_install_rebind_rejects_without_install_or_npx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    # Successful initial doctor observations precede the damaged/replaced at-use state.
    monkeypatch.setattr(playwright_mcp, "_build_doctor_report", lambda: [])
    package = playwright_mcp.PLAYWRIGHT_PACKAGE_PATH
    lock = playwright_mcp.FRONTEND_DIR / "package-lock.json"
    node = tmp_path / "node"
    node.write_text("fixture")
    node.chmod(0o700)
    monkeypatch.setattr(
        playwright_mcp,
        "_resolve_binary",
        lambda name: (
            ("bin/node" if fault == "relative-node" else str(node))
            if name == "node"
            else pytest.fail("unexpected npx")
        ),
    )
    monkeypatch.setattr(
        playwright_mcp,
        "_current_node_version",
        lambda _: "25.0.0" if fault == "changed-node" else "24.16.0",
    )
    entry = {"absolute": str(tmp_path / "outside.js"), "escape": "../outside.js"}.get(
        fault, "cli.js"
    )
    expected = {"version": "1.2.3", "bin": {"playwright": entry}}
    actual = {
        "name": "wrong" if fault == "name" else "playwright",
        "version": "1.2.4" if fault == "version" else "1.2.3",
        "bin": {"playwright": "other.js" if fault == "wrong-bin" else entry},
    }
    if fault != "missing-lock":
        lock.write_text(
            json.dumps({"lockfileVersion": 3, "packages": {"node_modules/playwright": expected}})
        )
    if fault != "missing-package":
        (package / "package.json").write_text(json.dumps(actual))
    foreign = tmp_path / "outside.js"
    foreign.write_text("foreign sentinel")
    cli = package / "cli.js"
    if fault == "cli-symlink":
        cli.symlink_to(foreign)
    elif fault == "hardlink":
        os.link(foreign, cli)
    elif fault != "missing-cli":
        cli.write_text("fixture")
    if fault in ("package-symlink", "node-modules-symlink"):
        path = package if fault == "package-symlink" else package.parent
        moved = tmp_path / "foreign-tree"
        path.rename(moved)
        path.symlink_to(moved, target_is_directory=True)
    monkeypatch.setattr(
        playwright_mcp.subprocess, "run", lambda *a, **kw: pytest.fail("install escaped")
    )
    assert playwright_mcp.main(["install-browser"]) == 1
    assert foreign.read_text() == "foreign sentinel"


def test_install_browser_refuses_when_local_playwright_package_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        playwright_mcp,
        "_build_doctor_report",
        lambda: [
            playwright_mcp.CheckResult(name="node-version", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="npm", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="npx", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="frontend-node-modules", ok=True, detail="ok"),
            playwright_mcp.CheckResult(
                name="frontend-playwright-package",
                ok=False,
                detail="Local Playwright package is missing.",
                remediation="Run npm ci.",
            ),
        ],
    )

    exit_code = playwright_mcp.main(["install-browser"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Refusing to install Playwright browsers" in captured.err


def test_install_browser_refuses_when_toolchain_is_not_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        playwright_mcp,
        "_build_doctor_report",
        lambda: [
            playwright_mcp.CheckResult(
                name="node-version",
                ok=False,
                detail="Repo baseline is Node 24.16.0, current runtime is 25.6.1.",
                remediation="Switch to Node 24.16.0.",
            )
        ],
    )

    exit_code = playwright_mcp.main(["install-browser"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Refusing to install Playwright browsers" in captured.err


def test_playwright_browser_cache_present_handles_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(playwright_mcp, "PLAYWRIGHT_CACHE_DIR", cache_dir)

    def raise_permission_error(self: Path) -> object:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "iterdir", raise_permission_error)

    assert playwright_mcp._playwright_browser_cache_present() is False


def test_playwright_browser_cache_requires_chromium_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "firefox-9999").mkdir()
    monkeypatch.setattr(playwright_mcp, "PLAYWRIGHT_CACHE_DIR", cache_dir)

    assert playwright_mcp._playwright_browser_cache_present() is False

    (cache_dir / "chromium-1234").mkdir()

    assert playwright_mcp._playwright_browser_cache_present() is True


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "prerelease",
        "relative",
        "missing",
        "directory",
        "non-executable",
        "timeout",
        "launch",
        "nonzero",
        "encoding",
        "malformed",
        "multiline",
    ],
)
def test_doctor_node_probe_is_bounded_and_unavailable_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    node = tmp_path / "node"
    node.write_bytes(b"synthetic executable fixture")
    node.chmod(0o600 if case == "non-executable" else 0o700)
    selected = {
        "relative": Path("bin/node"),
        "missing": tmp_path / "absent",
        "directory": tmp_path,
    }.get(case, node)
    secret = "synthetic-node-credential"
    for name in (
        "NODE_OPTIONS",
        "NODE_PATH",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "HTTPS_PROXY",
        "LD_PRELOAD",
    ):
        monkeypatch.setenv(name, secret)
    calls = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert argv == [str(node.resolve()), "-p", "process.versions.node"]
        assert kwargs["cwd"] == playwright_mcp.REPO_ROOT and kwargs["timeout"] == 10
        assert kwargs.get("shell", False) is False
        assert kwargs["stdin"] == kwargs["stderr"] == subprocess.DEVNULL
        assert secret not in repr(kwargs["env"])
        if case == "timeout":
            raise subprocess.TimeoutExpired([secret], 10, output="24.22.1", stderr=secret)
        if case == "launch":
            raise OSError(secret)
        if case == "encoding":
            raise UnicodeDecodeError("utf8", b"\xff", 0, 1, secret)
        output = {
            "prerelease": "24.0.0-rc.1\n",
            "malformed": secret,
            "multiline": "24.22.1\n" + secret,
        }.get(case, "24.22.1\n")
        return subprocess.CompletedProcess(
            argv, 1 if case == "nonzero" else 0, stdout=output, stderr=secret
        )

    monkeypatch.setattr(playwright_mcp.subprocess, "run", run)
    assert playwright_mcp._current_node_version(str(selected)) == {
        "valid": "24.22.1",
        "prerelease": "24.0.0-rc.1",
    }.get(case)
    assert len(calls) == (
        0 if case in {"relative", "missing", "directory", "non-executable"} else 1
    )


def test_doctor_real_node_excludes_inherited_preload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = shutil.which("node")
    assert (
        selected is not None and Path(selected).is_absolute()
    ), "qualified Node required for preload control"
    marker = tmp_path / "preload-marker"
    preload = tmp_path / "probe.cjs"
    preload.write_text(
        "require('node:fs').writeFileSync(" + json.dumps(str(marker)) + ", process.env.GH_TOKEN);\n"
    )
    options = "--require " + json.dumps(str(preload))
    token = "synthetic-node-preload"
    monkeypatch.setenv("NODE_OPTIONS", options)
    monkeypatch.setenv("NODE_PATH", str(tmp_path))
    monkeypatch.setenv("GH_TOKEN", token)
    monkeypatch.setenv("GITHUB_TOKEN", token)
    monkeypatch.setattr(playwright_mcp, "REPO_ROOT", tmp_path)
    control = subprocess.run(
        [selected, "-p", "process.versions.node"],
        cwd=tmp_path,
        env={"PATH": os.defpath, "LC_ALL": "C", "NODE_OPTIONS": options, "GH_TOKEN": token},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert marker.read_text() == token
    marker.unlink()
    expected = control.stdout.strip()
    assert expected and playwright_mcp._current_node_version(selected) == expected
    assert not marker.exists()
