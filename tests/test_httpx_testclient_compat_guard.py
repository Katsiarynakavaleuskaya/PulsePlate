"""Tests for the deprecated httpx TestClient backend guard."""

from __future__ import annotations

from pathlib import Path

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
                "test_client = TestClient(object())",
            )
        ),
    )

    assert guard.find_violations([path], repo_root=tmp_path) == []


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
