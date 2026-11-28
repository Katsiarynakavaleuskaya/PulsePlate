"""Deterministic tests for the public-side domain TLS diagnostic."""

from __future__ import annotations

from typing import Any
from types import SimpleNamespace

import pytest

from scripts import check_domain_tls


def _completed(stdout: str, returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _install_subprocess_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dig_outputs: dict[tuple[str, str], str],
    curl_outputs: dict[str, str],
) -> None:
    """Install deterministic subprocess mocks for dig and curl helpers."""

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:  # noqa: ARG001
        if argv[0] == "/usr/bin/dig":
            assert len(argv) == 6
            assert argv[1:3] == ["+short", "-q"]
            assert argv[4] == "-t"
            return _completed(dig_outputs[(argv[3], argv[5])])
        if argv[0] == "/usr/bin/curl":
            return _completed(curl_outputs[argv[-1]])
        raise AssertionError(f"Unexpected argv: {argv}")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_domain_tls.subprocess, "run", fake_run)


def test_main_passes_for_healthy_topology(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n104.26.9.193\n",
        ("pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "A"): "104.26.8.193\n104.26.9.193\n",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "",
    }
    curl_outputs = {
        "https://pulseplate.app": "HTTP/2 405 \r\nallow: GET\r\n\r\n",
        "https://www.pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://pulseplate.app\r\nserver: cloudflare\r\n\r\n"
        ),
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS: apex is healthy and www redirects to the repo-owned apex host" in captured.out


def test_main_fails_when_www_returns_525(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n",
        ("pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "A"): "104.26.8.193\n",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "",
    }
    curl_outputs = {
        "https://pulseplate.app": "HTTP/2 405 \r\nallow: GET\r\n\r\n",
        "https://www.pulseplate.app": "HTTP/2 525 \r\nserver: cloudflare\r\n\r\n",
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "returned 525" in captured.out
    assert "Full (strict)" in captured.out


def test_main_fails_when_apex_aaaa_exists(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n",
        ("pulseplate.app", "AAAA"): "2606:4700:20::681a:8c1\n",
        ("www.pulseplate.app", "A"): "104.26.8.193\n",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "",
    }
    curl_outputs = {
        "https://pulseplate.app": "HTTP/2 405 \r\nallow: GET\r\n\r\n",
        "https://www.pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://pulseplate.app\r\nserver: cloudflare\r\n\r\n"
        ),
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Conflicting apex AAAA records detected" in captured.out


def test_main_passes_when_apex_redirects_to_repo_owned_host(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n",
        ("pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "A"): "104.26.8.193\n",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "",
    }
    curl_outputs = {
        "https://pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://pulseplate.app/landing\r\n\r\n"
        ),
        "https://www.pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://pulseplate.app\r\nserver: cloudflare\r\n\r\n"
        ),
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS: apex is healthy and www redirects to the repo-owned apex host" in captured.out


def test_main_fails_when_www_points_to_figma_sites(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n",
        ("pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "A"): "",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "sites.figma.net.\n",
    }
    curl_outputs = {
        "https://pulseplate.app": "HTTP/2 405 \r\nallow: GET\r\n\r\n",
        "https://www.pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://curve-shown-53684781.figma.site\r\n\r\n"
        ),
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "points to sites.figma.net" in captured.out
    assert "unexpected target" in captured.out


def test_main_fails_when_apex_redirects_to_non_repo_host(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dig_outputs = {
        ("pulseplate.app", "A"): "104.26.8.193\n",
        ("pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "A"): "104.26.8.193\n",
        ("www.pulseplate.app", "AAAA"): "",
        ("www.pulseplate.app", "CNAME"): "",
    }
    curl_outputs = {
        "https://pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://curve-shown-53684781.figma.site\r\n\r\n"
        ),
        "https://www.pulseplate.app": (
            "HTTP/2 308 \r\nlocation: https://pulseplate.app\r\nserver: cloudflare\r\n\r\n"
        ),
    }
    _install_subprocess_mocks(
        monkeypatch,
        dig_outputs=dig_outputs,
        curl_outputs=curl_outputs,
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Apex redirect points to unexpected target" in captured.out


def test_collect_dns_answers_falls_back_to_socket_without_dig(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_domain_tls.shutil, "which", lambda name: None if name == "dig" else ""
    )
    monkeypatch.setattr(
        check_domain_tls,
        "_socket_answers",
        lambda hostname, family: (
            ("203.0.113.10",) if family == check_domain_tls.socket.AF_INET else ()
        ),
    )

    assert check_domain_tls._collect_dns_answers("pulseplate.app", "A") == ("203.0.113.10",)
    assert check_domain_tls._collect_dns_answers("pulseplate.app", "AAAA") == ()
    with pytest.raises(RuntimeError, match="dig is required to inspect CNAME ownership drift"):
        check_domain_tls._collect_dns_answers("www.pulseplate.app", "CNAME")


def test_parse_http_probe_keeps_only_last_response_headers() -> None:
    probe = check_domain_tls._parse_http_probe(
        (
            "HTTP/2 301 \r\n"
            "location: https://old.example\r\n"
            "server: cloudflare\r\n\r\n"
            "HTTP/2 308 \r\n"
            "location: https://pulseplate.app\r\n\r\n"
        ),
        "https://www.pulseplate.app",
    )

    assert probe.status_code == 308
    assert probe.headers == {"location": "https://pulseplate.app"}


def test_main_fails_closed_when_curl_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        check_domain_tls.shutil,
        "which",
        lambda name: None if name == "curl" else f"/usr/bin/{name}",
    )

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Required binary 'curl'" in captured.out


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  PuLsEpLaTe.App  ", "pulseplate.app"),
        ("Example.COM...", "example.com"),
        ("localhost", "localhost"),
        ("A", "a"),
        ("MX", "mx"),
        ("IN", "in"),
        ("CH", "ch"),
        ("a-b.example", "a-b.example"),
        ("xn--opaque.example", "xn--opaque.example"),
        ("123", "123"),
        ("a", "a"),
        ("a" * 63, "a" * 63),
        (".".join(["a" * 63] * 3 + ["b" * 61]), ".".join(["a" * 63] * 3 + ["b" * 61])),
    ],
)
def test_hostname_normalization_preserves_bounded_ascii_compatibility(
    raw: str, expected: str
) -> None:
    assert check_domain_tls._normalize_domain(raw) == expected


_INVALID_DOMAINS = (
    "",
    "...",
    "-",
    "-f",
    "-k",
    "-h",
    "--help",
    "a.-b",
    "a.b-",
    ".example",
    "a..example",
    "a_b.example",
    "+trace",
    "@server",
    "https://example.com",
    "example.com/path",
    "example.com:443",
    "user@example.com",
    "example.com?x",
    "example.com#x",
    "a\\b",
    "a b",
    "a\tb",
    "a\nb",
    "a\x00b",
    "é.example",
    "K.example",
    "a" * 64,
    ".".join(["a" * 63] * 3 + ["b" * 62]),
)


@pytest.mark.parametrize("domain", _INVALID_DOMAINS)
def test_invalid_hostname_is_rejected(domain: str) -> None:
    with pytest.raises(ValueError):
        check_domain_tls._normalize_domain(domain)


@pytest.mark.parametrize("domain", (*_INVALID_DOMAINS, ".".join(["a" * 63] * 3 + ["b" * 61])))
@pytest.mark.parametrize("entrypoint", ["report", "cli"])
def test_invalid_apex_or_www_overflow_has_no_diagnostic_effects(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    domain: str,
    entrypoint: str,
) -> None:
    def unexpected(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Invalid hostname reached diagnostic effects")

    monkeypatch.setattr(check_domain_tls.shutil, "which", unexpected)
    monkeypatch.setattr(check_domain_tls.subprocess, "run", unexpected)
    monkeypatch.setattr(check_domain_tls.socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(check_domain_tls, "_collect_dns_answers", unexpected)
    monkeypatch.setattr(check_domain_tls, "_probe_https", unexpected)
    if entrypoint == "report":
        with pytest.raises(ValueError):
            check_domain_tls.collect_domain_report(domain)
    else:
        assert check_domain_tls.main(["--domain=" + domain]) == 1
        captured = capsys.readouterr()
        assert captured.out.startswith("FAIL: ")
        assert "PASS:" not in captured.out


@pytest.mark.parametrize("domain", ["A", "MX", "IN", "CH", "a-b.example", "xn--opaque"])
def test_legal_query_names_bind_explicitly_through_public_report(
    monkeypatch: pytest.MonkeyPatch, domain: str
) -> None:
    calls: list[list[str]] = []
    normalized = domain.lower()

    def run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append(argv)
        assert kwargs["timeout"] == check_domain_tls.HTTP_TIMEOUT_SEC
        assert kwargs.get("shell", False) is False
        if argv[0] == "/usr/bin/dig":
            assert len(argv) == 6
            assert argv[1:3] == ["+short", "-q"] and argv[4] == "-t"
            return _completed("")
        assert argv == ["/usr/bin/curl", "-I", "-sS", "--max-time", "15", argv[-1]]
        assert argv[-1] in ("https://" + normalized, "https://www." + normalized)
        return _completed("HTTP/2 200\r\n\r\n")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(check_domain_tls.subprocess, "run", run)
    report = check_domain_tls.collect_domain_report(domain)
    assert report.domain == normalized
    assert [argv for argv in calls if argv[0] == "/usr/bin/dig"] == [
        ["/usr/bin/dig", "+short", "-q", host, "-t", kind]
        for host, kind in [
            (normalized, "A"),
            (normalized, "AAAA"),
            ("www." + normalized, "A"),
            ("www." + normalized, "AAAA"),
            ("www." + normalized, "CNAME"),
        ]
    ]
    assert report.apex_a == report.apex_aaaa == report.www_cname == ()


def test_maximum_two_target_apex_admits_www_without_partial_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    apex = ".".join(["a" * 63] * 3 + ["b" * 57])
    assert len(apex) == 249 and len("www." + apex) == 253
    names: list[str] = []

    def dns(hostname: str, record_type: str) -> tuple[str, ...]:
        names.append(hostname)
        return ()

    monkeypatch.setattr(check_domain_tls, "_resolve_binary", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(check_domain_tls, "_collect_dns_answers", dns)
    monkeypatch.setattr(
        check_domain_tls,
        "_probe_https",
        lambda binary, hostname: check_domain_tls.HttpProbe("https://" + hostname, 200, {}),
    )
    report = check_domain_tls.collect_domain_report(apex)
    assert report.domain == apex
    assert names == [apex, apex, "www." + apex, "www." + apex, "www." + apex]
