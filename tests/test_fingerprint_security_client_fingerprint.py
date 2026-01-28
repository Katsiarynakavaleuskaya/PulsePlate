"""Tests for _client_fingerprint function in core.fingerprint_security.

Covers all branches:
- no client / no headers
- trusted proxy + X-Forwarded-For
- malformed X-Forwarded-For (fallback to client.host)
- IPv6 addresses
- empty source (returns None)
"""

from __future__ import annotations

import pytest

from core.fingerprint_security import _client_fingerprint


class _MockClient:
    """Mock client object for testing."""

    def __init__(self, host: str | None) -> None:
        self.host = host


class _MockHeaders:
    """Mock headers object for testing."""

    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get header value by key."""
        return self._headers.get(key.lower(), default)


class _MockRequest:
    """Mock request object implementing ClientFingerprintRequest Protocol."""

    def __init__(self, host: str | None, headers: dict[str, str]) -> None:
        self.client = _MockClient(host) if host else None
        self.headers = _MockHeaders(headers)


def test_client_fingerprint_no_client_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that _client_fingerprint returns None when client is None."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    request = _MockRequest(host=None, headers={})
    result = _client_fingerprint(request)
    assert result is None


def test_client_fingerprint_empty_host_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that _client_fingerprint returns None when client.host is empty."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    request = _MockRequest(host="", headers={})
    result = _client_fingerprint(request)
    assert result is None


def test_client_fingerprint_direct_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _client_fingerprint with direct client IP (no proxy)."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    request = _MockRequest(host="192.168.1.1", headers={})
    result = _client_fingerprint(request)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_client_fingerprint_trusted_proxy_with_xff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint with trusted proxy and X-Forwarded-For header."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1,10.0.0.2")
    request = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.1"})
    result = _client_fingerprint(request)
    assert result is not None
    assert isinstance(result, str)
    # Should use X-Forwarded-For IP, not proxy IP
    request2 = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.2"})
    result2 = _client_fingerprint(request2)
    assert result != result2  # Different IPs produce different fingerprints


def test_client_fingerprint_trusted_proxy_xff_multiple_ips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint with X-Forwarded-For containing multiple IPs (uses first)."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(
        host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.1, 198.51.100.1"}
    )
    result = _client_fingerprint(request)
    assert result is not None
    # Should use first IP (203.0.113.1)
    request2 = _MockRequest(
        host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.1, 198.51.100.2"}
    )
    result2 = _client_fingerprint(request2)
    assert result == result2  # Same first IP = same fingerprint


def test_client_fingerprint_trusted_proxy_malformed_xff_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint falls back to client.host when X-Forwarded-For is malformed."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "not-an-ip"})
    result = _client_fingerprint(request)
    assert result is not None
    # Should fallback to proxy IP (10.0.0.1), not malformed XFF
    request2 = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "also-not-ip"})
    result2 = _client_fingerprint(request2)
    assert result == result2  # Same proxy IP = same fingerprint


def test_client_fingerprint_trusted_proxy_empty_xff_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint falls back to client.host when X-Forwarded-For is empty."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": ""})
    result = _client_fingerprint(request)
    assert result is not None
    # Should use proxy IP
    request2 = _MockRequest(host="10.0.0.1", headers={})
    result2 = _client_fingerprint(request2)
    assert result == result2  # Same proxy IP = same fingerprint


def test_client_fingerprint_untrusted_proxy_ignores_xff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint ignores X-Forwarded-For when proxy is not trusted."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(host="192.168.1.1", headers={"x-forwarded-for": "203.0.113.1"})
    result = _client_fingerprint(request)
    assert result is not None
    # Should use client.host (192.168.1.1), not XFF
    request2 = _MockRequest(host="192.168.1.1", headers={})
    result2 = _client_fingerprint(request2)
    assert result == result2  # Same client IP = same fingerprint


def test_client_fingerprint_ipv6(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _client_fingerprint with IPv6 address."""
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    request = _MockRequest(host="2001:db8::1", headers={})
    result = _client_fingerprint(request)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_client_fingerprint_ipv6_xff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _client_fingerprint with IPv6 in X-Forwarded-For header."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "2001:db8::2"})
    result = _client_fingerprint(request)
    assert result is not None
    assert isinstance(result, str)


def test_client_fingerprint_trusted_proxy_xff_with_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint handles whitespace in X-Forwarded-For correctly."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    request = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "  203.0.113.1  "})
    result = _client_fingerprint(request)
    assert result is not None
    # Should strip whitespace and use IP
    request2 = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.1"})
    result2 = _client_fingerprint(request2)
    assert result == result2


def test_client_fingerprint_trusted_proxies_comma_separated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _client_fingerprint handles comma-separated trusted proxies list."""
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1, 10.0.0.2 , 10.0.0.3")
    # First proxy
    request1 = _MockRequest(host="10.0.0.1", headers={"x-forwarded-for": "203.0.113.1"})
    result1 = _client_fingerprint(request1)
    assert result1 is not None
    # Second proxy
    request2 = _MockRequest(host="10.0.0.2", headers={"x-forwarded-for": "203.0.113.1"})
    result2 = _client_fingerprint(request2)
    assert result2 is not None
    # Third proxy
    request3 = _MockRequest(host="10.0.0.3", headers={"x-forwarded-for": "203.0.113.1"})
    result3 = _client_fingerprint(request3)
    assert result3 is not None
    # All should use same XFF IP
    assert result1 == result2 == result3
