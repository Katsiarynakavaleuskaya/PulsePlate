"""Unit tests for rate limit client key extraction (CIDR + header precedence).

RU: Тесты для извлечения client key при rate-limiting (поддержка CIDR + приоритет заголовков).
EN: Unit tests for rate limit client key extraction (CIDR support + header precedence).

These tests verify:
- CIDR parsing (172.30.100.0/24, 127.0.0.1, caddy)
- Trusted proxy detection
- Header precedence (CF-Connecting-IP > X-Forwarded-For > request.client.host)
- Malformed header handling
"""

from __future__ import annotations

import ipaddress
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.security.rate_limit import (
    _rate_limit_exceeded_json_handler,
    extract_client_ip,
    is_trusted_proxy,
    parse_trusted_proxies,
    rate_limit_client_key,
)
from core.i18n import normalize_lang, t


class TestParseTrustedProxies:
    """Tests for parse_trusted_proxies() function."""

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty TRUSTED_PROXIES env → empty list."""
        result = parse_trusted_proxies("")
        assert result == []

    def test_single_ip_address(self) -> None:
        """Single IP address → parsed as network."""
        result = parse_trusted_proxies("127.0.0.1")
        assert len(result) == 1
        assert isinstance(result[0], (ipaddress.IPv4Network, ipaddress.IPv6Network))
        assert ipaddress.ip_address("127.0.0.1") in result[0]

    def test_cidr_notation(self) -> None:
        """CIDR notation → parsed as network."""
        result = parse_trusted_proxies("172.30.100.0/24")
        assert len(result) == 1
        assert isinstance(result[0], (ipaddress.IPv4Network, ipaddress.IPv6Network))
        # Check range membership
        assert ipaddress.ip_address("172.30.100.1") in result[0]
        assert ipaddress.ip_address("172.30.100.254") in result[0]
        assert ipaddress.ip_address("172.30.101.1") not in result[0]

    def test_hostname(self) -> None:
        """Hostname → stored as string."""
        result = parse_trusted_proxies("caddy")
        assert result == ["caddy"]

    def test_multiple_mixed(self) -> None:
        """Mixed: IP + CIDR + hostname → all parsed."""
        result = parse_trusted_proxies("172.30.100.0/24, caddy, 127.0.0.1")
        assert len(result) == 3
        # First: CIDR network
        assert isinstance(result[0], (ipaddress.IPv4Network, ipaddress.IPv6Network))
        # Second: hostname
        assert result[1] == "caddy"
        # Third: single IP as network
        assert isinstance(result[2], (ipaddress.IPv4Network, ipaddress.IPv6Network))

    def test_whitespace_handling(self) -> None:
        """Whitespace around entries is stripped."""
        result = parse_trusted_proxies("  172.30.100.0/24  ,  caddy  ")
        assert len(result) == 2


class TestIsTrustedProxy:
    """Tests for is_trusted_proxy() function."""

    def test_exact_ip_match(self) -> None:
        """Exact IP match in trusted list → True."""
        trusted = parse_trusted_proxies("127.0.0.1")
        assert is_trusted_proxy("127.0.0.1", trusted)

    def test_cidr_range_match(self) -> None:
        """IP within CIDR range → True."""
        trusted = parse_trusted_proxies("172.30.100.0/24")
        assert is_trusted_proxy("172.30.100.10", trusted)
        assert is_trusted_proxy("172.30.100.254", trusted)

    def test_cidr_range_no_match(self) -> None:
        """IP outside CIDR range → False."""
        trusted = parse_trusted_proxies("172.30.100.0/24")
        assert not is_trusted_proxy("172.30.101.10", trusted)

    def test_hostname_match(self) -> None:
        """Hostname exact match → True."""
        trusted = parse_trusted_proxies("caddy")
        assert is_trusted_proxy("caddy", trusted)

    def test_hostname_no_match(self) -> None:
        """Hostname mismatch → False."""
        trusted = parse_trusted_proxies("caddy")
        assert not is_trusted_proxy("nginx", trusted)

    def test_untrusted_ip(self) -> None:
        """IP not in any trusted entry → False."""
        trusted = parse_trusted_proxies("172.30.100.0/24, caddy")
        assert not is_trusted_proxy("192.168.1.1", trusted)

    def test_remote_host_not_ip_skips_cidr_entries(self) -> None:
        """Non-IP remote_host should not crash CIDR checks (returns False)."""
        trusted = parse_trusted_proxies("172.30.100.0/24")
        assert not is_trusted_proxy("caddy", trusted)


class TestExtractClientIP:
    """Tests for extract_client_ip() header precedence."""

    def test_untrusted_proxy_returns_remote_host(self) -> None:
        """Untrusted proxy → use request.client.host directly."""
        trusted = parse_trusted_proxies("172.30.100.0/24")
        request = Mock()
        request.client = Mock(host="192.168.1.100")
        request.headers = {"x-forwarded-for": "10.0.0.1", "cf-connecting-ip": "10.0.0.2"}

        result = extract_client_ip(request, trusted)
        # Should ignore headers and use direct remote_host
        assert result == "192.168.1.100"

    def test_trusted_proxy_uses_cf_connecting_ip_first(self) -> None:
        """Trusted proxy + CF-Connecting-IP present → use CF-Connecting-IP."""
        trusted = parse_trusted_proxies("172.30.100.10")
        request = Mock()
        request.client = Mock(host="172.30.100.10")
        request.headers = {"cf-connecting-ip": "203.0.113.1", "x-forwarded-for": "198.51.100.1"}

        result = extract_client_ip(request, trusted)
        assert result == "203.0.113.1"

    def test_trusted_proxy_uses_xff_when_no_cf_header(self) -> None:
        """Trusted proxy + no CF-Connecting-IP → use X-Forwarded-For first IP."""
        trusted = parse_trusted_proxies("172.30.100.10")
        request = Mock()
        request.client = Mock(host="172.30.100.10")
        request.headers = {"x-forwarded-for": "198.51.100.1, 172.30.100.5"}

        result = extract_client_ip(request, trusted)
        assert result == "198.51.100.1"

    def test_trusted_proxy_fallback_to_remote_host(self) -> None:
        """Trusted proxy + no valid headers → fallback to remote_host."""
        trusted = parse_trusted_proxies("172.30.100.10")
        request = Mock()
        request.client = Mock(host="172.30.100.10")
        request.headers = {}

        result = extract_client_ip(request, trusted)
        assert result == "172.30.100.10"

    def test_malformed_cf_connecting_ip_skipped(self) -> None:
        """Malformed CF-Connecting-IP → skip to X-Forwarded-For."""
        trusted = parse_trusted_proxies("172.30.100.10")
        request = Mock()
        request.client = Mock(host="172.30.100.10")
        request.headers = {
            "cf-connecting-ip": "not-an-ip",
            "x-forwarded-for": "198.51.100.1",
        }

        result = extract_client_ip(request, trusted)
        assert result == "198.51.100.1"

    def test_malformed_xff_fallback_to_remote_host(self) -> None:
        """Malformed X-Forwarded-For → fallback to remote_host."""
        trusted = parse_trusted_proxies("172.30.100.10")
        request = Mock()
        request.client = Mock(host="172.30.100.10")
        request.headers = {"x-forwarded-for": "not-an-ip, also-not-an-ip"}

        result = extract_client_ip(request, trusted)
        assert result == "172.30.100.10"

    def test_cidr_trust_with_cf_header(self) -> None:
        """Remote host in CIDR range → trust headers."""
        trusted = parse_trusted_proxies("172.30.100.0/24")
        request = Mock()
        request.client = Mock(host="172.30.100.50")
        request.headers = {"cf-connecting-ip": "203.0.113.5"}

        result = extract_client_ip(request, trusted)
        assert result == "203.0.113.5"


class TestRateLimitClientKey:
    """Tests for rate_limit_client_key() fallback behavior."""

    def test_returns_unknown_when_client_ip_missing(self) -> None:
        """No client host + no trusted proxy headers → "unknown" fingerprint."""
        request = Mock()
        request.client = None
        request.headers = {}
        assert rate_limit_client_key(request) == "unknown"

    def test_hashes_client_ip_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client host present → returns pseudonymous (hashed) fingerprint."""
        monkeypatch.setenv("TRUSTED_PROXIES", "")

        request = Mock()
        request.client = Mock(host="203.0.113.9")
        request.headers = {}

        import core.fingerprint_security as fingerprint_security

        def _fake_compute_fingerprint(value: str) -> str:
            return f"fp:{value}"

        monkeypatch.setattr(fingerprint_security, "compute_fingerprint", _fake_compute_fingerprint)

        assert rate_limit_client_key(request) == "fp:203.0.113.9"


class TestRateLimitExceededJsonHandler:
    """Unit tests for the 429 JSON handler (i18n + header/state precedence)."""

    def test_uses_request_state_lang_over_header(self) -> None:
        request = Mock()
        request.headers = {"accept-language": "en"}
        request.state = SimpleNamespace(lang="ru")

        response = _rate_limit_exceeded_json_handler(request, Exception("boom"))

        assert response.status_code == 429
        assert response.headers.get("content-type", "").startswith("application/json")

        payload = json.loads(response.body.decode("utf-8"))
        expected_detail = t(normalize_lang("ru"), "rate_limit.exceeded")
        assert payload["detail"] == expected_detail

    def test_uses_accept_language_when_no_state_lang(self) -> None:
        request = Mock()
        request.headers = {"accept-language": "es"}
        request.state = SimpleNamespace()

        response = _rate_limit_exceeded_json_handler(request, Exception("boom"))

        assert response.status_code == 429
        payload = json.loads(response.body.decode("utf-8"))
        expected_detail = t(normalize_lang("es"), "rate_limit.exceeded")
        assert payload["detail"] == expected_detail

    def test_fallback_message_when_translation_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        request = Mock()
        request.headers = {"accept-language": "en"}
        request.state = SimpleNamespace()

        import core.i18n as i18n

        def _raise_key_error(*_args: object, **_kwargs: object) -> str:
            raise KeyError("missing")

        monkeypatch.setattr(i18n, "t", _raise_key_error)

        response = _rate_limit_exceeded_json_handler(request, Exception("boom"))

        assert response.status_code == 429
        payload = json.loads(response.body.decode("utf-8"))
        assert payload["detail"] == "Rate limit exceeded"
