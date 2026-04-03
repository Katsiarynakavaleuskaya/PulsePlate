"""Tests for the repo-owned Playwright MCP/toolchain helper."""

from __future__ import annotations

import json
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
    nvmrc_path.write_text("22.22.1\n", encoding="utf-8")

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
    assert "22.22.1" in node_result.detail
    assert "25.6.1" in node_result.detail


def test_doctor_passes_when_repo_prerequisites_are_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_fake_repo_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(playwright_mcp, "_current_node_version", lambda node_bin: "22.22.1")

    results = playwright_mcp._build_doctor_report()

    assert all(result.ok for result in results)
    assert playwright_mcp._doctor_exit_code(results) == 0


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


def test_install_browser_runs_repo_local_playwright_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        playwright_mcp,
        "_build_doctor_report",
        lambda: [
            playwright_mcp.CheckResult(name="node-version", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="npm", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="npx", ok=True, detail="ok"),
            playwright_mcp.CheckResult(name="frontend-node-modules", ok=True, detail="ok"),
        ],
    )
    monkeypatch.setattr(playwright_mcp, "_resolve_binary", lambda name: f"/usr/local/bin/{name}")

    recorded: dict[str, object] = {}

    def fake_run(argv: list[str], cwd: Path, check: bool) -> object:
        recorded["argv"] = argv
        recorded["cwd"] = cwd
        recorded["check"] = check
        return type("Process", (), {"returncode": 0})()

    monkeypatch.setattr(playwright_mcp.subprocess, "run", fake_run)

    exit_code = playwright_mcp.main(["install-browser"])

    assert exit_code == 0
    assert recorded["argv"] == [
        "/usr/local/bin/npx",
        "playwright",
        "install",
        "chromium",
    ]
    assert recorded["cwd"] == playwright_mcp.FRONTEND_DIR
    assert recorded["check"] is False


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
                detail="Repo baseline is Node 22.22.1, current runtime is 25.6.1.",
                remediation="Switch to Node 22.22.1.",
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
