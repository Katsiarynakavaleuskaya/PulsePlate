from __future__ import annotations

import importlib
import socket
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

    def _to_str(value: object) -> str:
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode()
            except Exception:  # pragma: no cover
                return str(value)
        return str(value)

    def _is_external_url(url: str | object) -> bool:
        scheme = getattr(url, "scheme", None)
        host = getattr(url, "host", None)
        if scheme is not None and host is not None:
            scheme_str = _to_str(scheme).lower()
            host_str = _to_str(host)
            if scheme_str in {"http", "https"}:
                return host_str not in allowed_hosts
            return False

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

    real_getaddrinfo = socket.getaddrinfo

    def guarded_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001
        host_str = _to_str(host) if host else ""
        if host_str and host_str not in allowed_hosts:
            raise AssertionError(f"DNS/network blocked in tests: host={host_str!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", _blocked_socket)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo, raising=True)

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

    try:
        httpcore = importlib.import_module("httpcore")
    except Exception:  # pragma: no cover
        httpcore = None
    if httpcore is not None:
        for cls_name, handler_name in (
            ("HTTPConnection", "handle_request"),
            ("ConnectionPool", "handle_request"),
        ):
            cls = getattr(httpcore, cls_name, None)
            handler = getattr(cls, handler_name, None) if cls is not None else None
            if callable(handler):

                def handle_request(
                    self, method, url, *args, _real=handler, **kwargs
                ):  # noqa: ANN001
                    if _is_external_url(url):
                        raise AssertionError(
                            f"External HTTP blocked in tests (httpcore): {_to_str(method)} {url}"
                        )
                    return _real(self, method, url, *args, **kwargs)

                monkeypatch.setattr(cls, handler_name, handle_request, raising=True)

        for cls_name, handler_name in (
            ("AsyncHTTPConnection", "handle_async_request"),
            ("AsyncConnectionPool", "handle_async_request"),
            ("AsyncHTTPProxy", "handle_async_request"),
        ):
            cls = getattr(httpcore, cls_name, None)
            handler = getattr(cls, handler_name, None) if cls is not None else None
            if callable(handler):

                async def handle_async_request(  # noqa: ANN001
                    self,
                    method,
                    url,
                    *args,
                    _real=handler,
                    **kwargs,
                ):
                    if _is_external_url(url):
                        raise AssertionError(
                            f"External HTTP blocked in tests (httpcore): {_to_str(method)} {url}"
                        )
                    return await _real(self, method, url, *args, **kwargs)

                monkeypatch.setattr(cls, handler_name, handle_async_request, raising=True)

    client = _make_client()
    r = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})
    assert r.status_code == 200

    payload = r.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) > 0
