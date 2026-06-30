"""Tests for the deprecated httpx TestClient backend guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci import check_httpx_testclient_compat as guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_guard_blocks_httpx_module_alias_app_shortcuts(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/bad_httpx_alias.py",
        "\n".join(
            (
                "import httpx as hx",
                "",
                "client = hx.Client(app=object())",
                "async_client = hx.AsyncClient(app=object())",
            )
        ),
    )

    violations = guard.find_violations([path], repo_root=tmp_path)

    assert [violation.symbol for violation in violations] == ["hx.Client", "hx.AsyncClient"]


def test_guard_blocks_imported_httpx_client_app_shortcuts(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/bad_imported_client.py",
        "\n".join(
            (
                "from httpx import AsyncClient as AC",
                "from httpx import Client",
                "",
                "client = Client(app=object())",
                "async_client = AC(app=object())",
            )
        ),
    )

    violations = guard.find_violations([path], repo_root=tmp_path)

    assert [violation.symbol for violation in violations] == ["Client", "AsyncClient"]


def test_guard_blocks_literal_app_keyword_unpacking(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/bad_literal_unpacking.py",
        "\n".join(
            (
                "import httpx",
                "from httpx import Client",
                "",
                "client = httpx.Client(**{'app': object()})",
                "imported = Client(**{'app': object()})",
            )
        ),
    )

    violations = guard.find_violations([path], repo_root=tmp_path)

    assert [violation.symbol for violation in violations] == ["httpx.Client", "Client"]


def test_guard_allows_transports_testclient_and_normal_httpx_clients(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/allowed_httpx_patterns.py",
        "\n".join(
            (
                "import httpx",
                "from fastapi.testclient import TestClient",
                "",
                "transport = httpx.ASGITransport(app=object())",
                "wsgi_transport = httpx.WSGITransport(app=object())",
                "client = httpx.Client(timeout=10, transport=transport)",
                "client_from_kwargs = httpx.Client(**{'timeout': 10})",
                "test_client = TestClient(object())",
            )
        ),
    )

    assert guard.find_violations([path], repo_root=tmp_path) == []


def test_guard_allows_rebound_httpx_aliases_and_imported_clients(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/rebound_httpx_names.py",
        "\n".join(
            (
                "import httpx as hx",
                "from httpx import AsyncClient as AC",
                "from httpx import Client",
                "",
                "hx = object()",
                "AC = lambda **kwargs: kwargs",
                "Client = lambda **kwargs: kwargs",
                "",
                "module_client = hx.Client(app=object())",
                "async_client = AC(app=object())",
                "client = Client(app=object())",
            )
        ),
    )

    assert guard.find_violations([path], repo_root=tmp_path) == []


def test_guard_scopes_rebound_names_to_function_body(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "tests/scoped_rebound_httpx_client.py",
        "\n".join(
            (
                "from httpx import Client",
                "",
                "def factory():",
                "    Client = lambda **kwargs: kwargs",
                "    return Client(app=object())",
                "",
                "client = Client(app=object())",
            )
        ),
    )

    violations = guard.find_violations([path], repo_root=tmp_path)

    assert [violation.symbol for violation in violations] == ["Client"]
    assert [violation.line for violation in violations] == [7]


def test_default_scan_excludes_legacy_generated_and_local_noise(tmp_path: Path) -> None:
    _write(tmp_path, "legacy_app.py", "import httpx\nhttpx.Client(app=object())\n")
    _write(
        tmp_path, "tests/disabled_hypothesis/bad.py", "import httpx\nhttpx.Client(app=object())\n"
    )
    _write(tmp_path, "app/generated/bad.py", "import httpx\nhttpx.Client(app=object())\n")
    good_path = _write(tmp_path, "app/good.py", "import httpx\nhttpx.Client(timeout=10)\n")

    assert guard.iter_python_files([tmp_path], repo_root=tmp_path) == [good_path.resolve()]
    assert guard.find_violations([tmp_path], repo_root=tmp_path) == []


def test_guard_scans_current_repo_without_deprecated_httpx_app_shortcuts() -> None:
    scan_paths = [REPO_ROOT / path for path in guard.DEFAULT_SCAN_PATHS]

    assert guard.find_violations(scan_paths, repo_root=REPO_ROOT) == []


def test_guard_main_reports_success_for_clean_scan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "tests/clean_cli_scan.py", "import httpx\nhttpx.Client(timeout=10)\n")

    exit_code = guard.main(["--repo-root", str(tmp_path), "--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "PASS: no deprecated httpx Client(app=...) shortcuts found.\n"
    assert captured.err == ""


def test_guard_main_reports_violating_scan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "tests/bad_cli_scan.py", "import httpx\nhttpx.Client(app=object())\n")

    exit_code = guard.main(["--repo-root", str(tmp_path), "--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Deprecated httpx TestClient backend shortcuts found:" in captured.out
    assert "tests/bad_cli_scan.py:2:1: deprecated httpx.Client(app=...)" in captured.out
    assert captured.err == ""


def test_guard_default_scan_paths_include_root_backend_modules() -> None:
    assert {
        "legacy_app.py",
        "llm.py",
        "main.py",
        "mcp_pulseplate_server.py",
        "secure_config.py",
        "settings.py",
        "signed_links.py",
    }.issubset(set(guard.DEFAULT_SCAN_PATHS))
