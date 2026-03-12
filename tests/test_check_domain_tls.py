"""Deterministic tests for the public-side domain TLS diagnostic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import check_domain_tls


def _completed(stdout: str, returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


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

    def fake_run(argv: list[str], **kwargs) -> SimpleNamespace:  # noqa: ARG001
        if argv[0] == "/usr/bin/dig":
            return _completed(dig_outputs[(argv[2], argv[3])])
        if argv[0] == "/usr/bin/curl":
            return _completed(curl_outputs[argv[-1]])
        raise AssertionError(f"Unexpected argv: {argv}")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_domain_tls.subprocess, "run", fake_run)

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

    def fake_run(argv: list[str], **kwargs) -> SimpleNamespace:  # noqa: ARG001
        if argv[0] == "/usr/bin/dig":
            return _completed(dig_outputs[(argv[2], argv[3])])
        if argv[0] == "/usr/bin/curl":
            return _completed(curl_outputs[argv[-1]])
        raise AssertionError(f"Unexpected argv: {argv}")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_domain_tls.subprocess, "run", fake_run)

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

    def fake_run(argv: list[str], **kwargs) -> SimpleNamespace:  # noqa: ARG001
        if argv[0] == "/usr/bin/dig":
            return _completed(dig_outputs[(argv[2], argv[3])])
        if argv[0] == "/usr/bin/curl":
            return _completed(curl_outputs[argv[-1]])
        raise AssertionError(f"Unexpected argv: {argv}")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_domain_tls.subprocess, "run", fake_run)

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Conflicting apex AAAA records detected" in captured.out


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

    def fake_run(argv: list[str], **kwargs) -> SimpleNamespace:  # noqa: ARG001
        if argv[0] == "/usr/bin/dig":
            return _completed(dig_outputs[(argv[2], argv[3])])
        if argv[0] == "/usr/bin/curl":
            return _completed(curl_outputs[argv[-1]])
        raise AssertionError(f"Unexpected argv: {argv}")

    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(check_domain_tls.subprocess, "run", fake_run)

    exit_code = check_domain_tls.main(["--domain", "pulseplate.app"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "points to sites.figma.net" in captured.out
    assert "unexpected target" in captured.out


def test_collect_dns_answers_falls_back_to_socket_without_dig(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_domain_tls.shutil, "which", lambda name: None if name == "dig" else "")
    monkeypatch.setattr(
        check_domain_tls,
        "_socket_answers",
        lambda hostname, family: ("203.0.113.10",) if family == check_domain_tls.socket.AF_INET else (),
    )

    assert check_domain_tls._collect_dns_answers("pulseplate.app", "A") == ("203.0.113.10",)
    assert check_domain_tls._collect_dns_answers("pulseplate.app", "AAAA") == ()
    assert check_domain_tls._collect_dns_answers("www.pulseplate.app", "CNAME") == ()


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
