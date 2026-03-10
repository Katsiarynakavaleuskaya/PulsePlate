from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker.js"


def _worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def test_worker_removes_wildcard_cors_and_follow_redirects() -> None:
    source = _worker_source()

    assert 'Access-Control-Allow-Origin", "*"' not in source
    assert 'redirect: "follow"' not in source
    assert 'redirect: "manual"' in source


def test_worker_requires_explicit_target_base_and_trusted_origins() -> None:
    source = _worker_source()

    assert "TARGET_BASE must be explicitly configured" in source
    assert "REPLACE_ME.trycloudflare.com" not in source
    assert "WORKER_ALLOWED_ORIGINS" in source
    assert "cachedAllowedOriginsRaw" in source
    assert "Trusted browser origin is required" in source


def test_worker_bounds_path_method_and_forwarded_headers() -> None:
    source = _worker_source()

    assert 'url.pathname.startsWith("/api/")' in source
    assert 'new Set(["GET", "POST", "OPTIONS"])' in source
    assert 'new Set(["GET", "HEAD"])' in source
    assert "new Headers(request.headers)" not in source

    for header_name in [
        "accept",
        "authorization",
        "cf-connecting-ip",
        "content-type",
        "cookie",
        "x-forwarded-for",
        "x-api-key",
    ]:
        assert f'"{header_name}"' in source
