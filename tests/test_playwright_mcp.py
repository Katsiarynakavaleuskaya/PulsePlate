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
