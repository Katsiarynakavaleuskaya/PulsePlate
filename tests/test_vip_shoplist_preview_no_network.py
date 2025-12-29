from __future__ import annotations

import socket
import importlib
from urllib.parse import urlparse
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


def _make_client() -> TestClient:
    import app

    return TestClient(cast(ASGIApp, app.app))


def test_vip_shoplist_preview_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test_vip_key")

    allowed_hosts = {"127.0.0.1", "localhost", "::1", "testserver"}

    def _is_external_url(url: str | object) -> bool:
        s = str(url)
        if s.startswith(("http://", "https://")):
            parsed = urlparse(s)
            host = parsed.hostname
            if not host:
                return True
            return host not in allowed_hosts
        return False

    def _blocked_socket(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("Network access is forbidden in this test")

    monkeypatch.setattr(socket, "create_connection", _blocked_socket)

    try:
        httpx = importlib.import_module("httpx")
    except Exception:  # pragma: no cover
        httpx = None
    if httpx is not None:
        httpx_client_cls = getattr(httpx, "Client", None)
        httpx_async_client_cls = getattr(httpx, "AsyncClient", None)
        if httpx_client_cls is not None:
            real_client_request = httpx_client_cls.request

            def client_request(self, method, url, *args, **kwargs):  # noqa: ANN001
                if _is_external_url(url):
                    raise AssertionError(f"External HTTP blocked in tests: {method} {url}")
                return real_client_request(self, method, url, *args, **kwargs)

            monkeypatch.setattr(httpx_client_cls, "request", client_request, raising=True)
        if httpx_async_client_cls is not None:
            real_async_request = httpx_async_client_cls.request

            async def async_request(self, method, url, *args, **kwargs):  # noqa: ANN001
                if _is_external_url(url):
                    raise AssertionError(f"External HTTP blocked in tests: {method} {url}")
                return await real_async_request(self, method, url, *args, **kwargs)

            monkeypatch.setattr(httpx_async_client_cls, "request", async_request, raising=True)

    try:
        requests = importlib.import_module("requests")
    except Exception:  # pragma: no cover
        requests = None
    if requests is not None:
        sessions_mod = getattr(requests, "sessions", None)
        session_cls = getattr(sessions_mod, "Session", None) if sessions_mod is not None else None
        if session_cls is not None:
            real_requests_request = session_cls.request

            def session_request(self, method, url, *args, **kwargs):  # noqa: ANN001
                if _is_external_url(url):
                    raise AssertionError(f"External HTTP blocked in tests: {method} {url}")
                return real_requests_request(self, method, url, *args, **kwargs)

            monkeypatch.setattr(session_cls, "request", session_request, raising=True)

    client = _make_client()
    r = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})
    assert r.status_code == 200
