from __future__ import annotations

import asyncio
import importlib
import socket
from types import ModuleType
from typing import Any
from urllib.parse import urlparse

import pytest
from tests._client import open_test_client


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

    def _blocked_socket(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Network access is forbidden in this test")

    real_getaddrinfo = socket.getaddrinfo

    def guarded_getaddrinfo(host: object, *args: Any, **kwargs: Any) -> Any:
        host_str = _to_str(host) if host else ""
        if host_str and host_str not in allowed_hosts:
            raise AssertionError(f"DNS/network blocked in tests: host={host_str!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", _blocked_socket)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo, raising=True)

    def _guard_httpx(module: ModuleType, name: str) -> None:
        client_cls = getattr(module, "Client")
        async_client_cls = getattr(module, "AsyncClient")
        real_client_request = client_cls.request
        real_async_request = async_client_cls.request

        def client_request(self: Any, method: str, url: object, *args: Any, **kwargs: Any) -> Any:
            if _is_external_url(url):
                raise AssertionError(f"External HTTP blocked in tests ({name}): {method} {url}")
            return real_client_request(self, method, url, *args, **kwargs)

        async def async_request(
            self: Any, method: str, url: object, *args: Any, **kwargs: Any
        ) -> Any:
            if _is_external_url(url):
                raise AssertionError(f"External HTTP blocked in tests ({name}): {method} {url}")
            return await real_async_request(self, method, url, *args, **kwargs)

        monkeypatch.setattr(client_cls, "request", client_request, raising=True)
        monkeypatch.setattr(async_client_cls, "request", async_request, raising=True)

    http_libraries = {name: importlib.import_module(name) for name in ("httpx", "httpx2")}
    for name, module in http_libraries.items():
        _guard_httpx(module, name)

    try:
        requests = importlib.import_module("requests")
    except Exception:  # pragma: no cover
        requests = None
    if requests is not None:
        sessions_mod = getattr(requests, "sessions", None)
        session_cls = getattr(sessions_mod, "Session", None) if sessions_mod is not None else None
        if session_cls is not None:
            real_requests_request = session_cls.request

            def session_request(
                self: Any, method: str, url: object, *args: Any, **kwargs: Any
            ) -> Any:
                if _is_external_url(url):
                    raise AssertionError(f"External HTTP blocked in tests: {method} {url}")
                return real_requests_request(self, method, url, *args, **kwargs)

            monkeypatch.setattr(session_cls, "request", session_request, raising=True)

    def _guard_httpcore(module: ModuleType, name: str) -> None:
        for cls_name, handler_name in (
            ("HTTPConnection", "handle_request"),
            ("ConnectionPool", "handle_request"),
        ):
            cls = getattr(module, cls_name, None)
            handler = getattr(cls, handler_name, None) if cls is not None else None
            if callable(handler):

                def handle_request(self: Any, request: Any, *, _real: Any = handler) -> Any:
                    if _is_external_url(request.url):
                        raise AssertionError(
                            f"External HTTP blocked in tests ({name}): "
                            f"{_to_str(request.method)} {request.url}"
                        )
                    return _real(self, request)

                monkeypatch.setattr(cls, handler_name, handle_request, raising=True)

        for cls_name, handler_name in (
            ("AsyncHTTPConnection", "handle_async_request"),
            ("AsyncConnectionPool", "handle_async_request"),
            ("AsyncHTTPProxy", "handle_async_request"),
        ):
            cls = getattr(module, cls_name, None)
            handler = getattr(cls, handler_name, None) if cls is not None else None
            if callable(handler):

                async def handle_async_request(
                    self: Any, request: Any, *, _real: Any = handler
                ) -> Any:
                    if _is_external_url(request.url):
                        raise AssertionError(
                            f"External HTTP blocked in tests ({name}): "
                            f"{_to_str(request.method)} {request.url}"
                        )
                    return await _real(self, request)

                monkeypatch.setattr(cls, handler_name, handle_async_request, raising=True)

    core_libraries = {name: importlib.import_module(name) for name in ("httpcore", "httpcore2")}
    for name, module in core_libraries.items():
        _guard_httpcore(module, name)

    external_url = "https://example.invalid/shoplist-canary"

    async def _check_async_guards() -> None:
        for name, module in http_libraries.items():
            async with module.AsyncClient() as probe:
                with pytest.raises(
                    AssertionError, match=f"External HTTP blocked in tests \\({name}\\)"
                ):
                    await probe.get(external_url)
        for name, module in core_libraries.items():
            async with module.AsyncConnectionPool() as pool:
                request = module.Request("GET", external_url)
                with pytest.raises(
                    AssertionError, match=f"External HTTP blocked in tests \\({name}\\)"
                ):
                    await pool.handle_async_request(request)

    with open_test_client() as client:
        r = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})
        assert r.status_code == 200

        payload = r.json()
        assert "items" in payload
        assert isinstance(payload["items"], list)
        assert len(payload["items"]) > 0

        for name, module in http_libraries.items():
            with module.Client() as probe:
                with pytest.raises(
                    AssertionError, match=f"External HTTP blocked in tests \\({name}\\)"
                ):
                    probe.get(external_url)
        if requests is not None:
            with requests.Session() as probe:
                with pytest.raises(AssertionError, match="External HTTP blocked in tests: GET"):
                    probe.get(external_url)
        for name, module in core_libraries.items():
            with module.ConnectionPool() as pool:
                request = module.Request("GET", external_url)
                with pytest.raises(
                    AssertionError, match=f"External HTTP blocked in tests \\({name}\\)"
                ):
                    pool.handle_request(request)
        asyncio.run(_check_async_guards())
