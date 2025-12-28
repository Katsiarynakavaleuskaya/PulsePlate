from __future__ import annotations

from typing import cast
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


def _is_external_url(url: str | object) -> bool:
    """Return True if the URL points to an external host (not localhost/testserver)."""
    s = str(url)
    if not s.startswith(("http://", "https://")):
        return False
    parsed = urlparse(s)
    host = parsed.hostname
    if not host:
        return True
    return host not in {"127.0.0.1", "localhost", "::1", "testserver"}


def test_catalog_endpoints_do_not_require_external_network(
    test_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify catalog API endpoints work without external network dependencies."""
    import httpx

    real_client_request = httpx.Client.request
    real_async_request = httpx.AsyncClient.request

    def client_request(self: httpx.Client, method: str, url: str | httpx.URL, *args, **kwargs):
        if _is_external_url(url):
            raise AssertionError(f"External HTTP blocked in this test: {method} {url}")
        return real_client_request(self, method, url, *args, **kwargs)

    async def async_request(
        self: httpx.AsyncClient, method: str, url: str | httpx.URL, *args, **kwargs
    ):
        if _is_external_url(url):
            raise AssertionError(f"External HTTP blocked in this test: {method} {url}")
        return await real_async_request(self, method, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "request", client_request, raising=True)
    monkeypatch.setattr(httpx.AsyncClient, "request", async_request, raising=True)

    try:
        import requests as _requests
    except ImportError:  # pragma: no cover
        _requests = None

    if _requests is not None:
        real_requests_request = _requests.sessions.Session.request

        def session_request(self, method: str, url: str, *args, **kwargs):
            if _is_external_url(url):
                raise AssertionError(f"External HTTP blocked in this test: {method} {url}")
            return real_requests_request(self, method, url, *args, **kwargs)

        monkeypatch.setattr(_requests.sessions.Session, "request", session_request, raising=True)

    import app

    client = TestClient(cast(ASGIApp, app.app))
    try:
        assert client.get("/api/v1/catalog/regions").status_code == 200
        assert client.get("/api/v1/catalog/stores", params={"region_id": "ES"}).status_code == 200
        assert (
            client.get("/api/v1/catalog/search", params={"q": "ban", "region_id": "ES"}).status_code
            == 200
        )
    finally:
        client.close()
