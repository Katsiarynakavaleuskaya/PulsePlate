#!/usr/bin/env python3
"""Read-only public-side domain TLS diagnostic for repo-canonical ownership.

RU: Проверяет публичную DNS/TLS топологию без изменений Cloudflare/DNS.
EN: Checks public DNS/TLS topology without mutating Cloudflare/DNS.
"""

from __future__ import annotations

import argparse
import re
import shutil
import socket
import subprocess  # nosec B404: read-only diagnostics require bounded subprocess calls (remove-by: 2026-06-30, ref: PR-WWW-TLS-OPASSIST)
from dataclasses import dataclass

HTTP_TIMEOUT_SEC = 15
SUCCESS_EXIT_CODE = 0
DRIFT_EXIT_CODE = 1
EXPECTED_APEX_STATUSES = frozenset({200, 301, 302, 303, 307, 308, 405})
EXPECTED_WWW_STATUSES = frozenset({301, 302, 307, 308})
EXPECTED_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
FIGMA_SITES_HOST = "sites.figma.net"


@dataclass(frozen=True)
class CommandResult:
    """Completed external command output."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class HttpProbe:
    """Parsed HEAD response for one hostname."""

    url: str
    status_code: int | None
    headers: dict[str, str]
    error: str | None = None


@dataclass(frozen=True)
class DomainReport:
    """Collected public-side domain evidence."""

    domain: str
    apex_a: tuple[str, ...]
    apex_aaaa: tuple[str, ...]
    www_a: tuple[str, ...]
    www_aaaa: tuple[str, ...]
    www_cname: tuple[str, ...]
    apex_probe: HttpProbe
    www_probe: HttpProbe


def _normalize_domain(raw_domain: str) -> str:
    """Accept a hostname only; reject URLs and obvious invalid input."""

    domain = raw_domain.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("--domain must not be empty")
    if "://" in domain or "/" in domain:
        raise ValueError("--domain must be a hostname without scheme or path")
    if not re.fullmatch(r"[a-z0-9.-]+", domain):
        raise ValueError("--domain contains invalid characters")
    if ".." in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("--domain is malformed")
    return domain


def _resolve_binary(binary_name: str) -> str:
    """Return absolute path for required external tools."""

    binary_path = shutil.which(binary_name)
    if not binary_path:
        raise RuntimeError(
            f"Required binary '{binary_name}' is not available on PATH. "
            f"Install it or run the equivalent manual check for {binary_name}."
        )
    return binary_path


def _run_command(argv: list[str], *, timeout: int) -> CommandResult:
    """Execute a bounded diagnostic command and capture its text output."""

    try:
        completed = subprocess.run(  # nosec B603: argv uses absolute binaries and fixed diagnostic flags (remove-by: 2026-06-30, ref: PR-WWW-TLS-OPASSIST)
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        command_name = argv[0]
        raise RuntimeError(f"{command_name} timed out after {timeout}s") from exc
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _dig_answers(dig_path: str, hostname: str, record_type: str) -> tuple[str, ...]:
    """Read DNS answers via dig +short."""

    result = _run_command(
        [dig_path, "+short", hostname, record_type],
        timeout=HTTP_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown dig error"
        raise RuntimeError(f"dig failed for {hostname} {record_type}: {stderr}")
    return tuple(line.strip().rstrip(".") for line in result.stdout.splitlines() if line.strip())


def _socket_answers(hostname: str, family: socket.AddressFamily) -> tuple[str, ...]:
    """Fallback DNS lookup when dig is unavailable."""

    try:
        infos = socket.getaddrinfo(hostname, None, family=family, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return ()
    addresses = {item[4][0] for item in infos}
    return tuple(sorted(addresses))


def _collect_dns_answers(hostname: str, record_type: str) -> tuple[str, ...]:
    """Collect DNS answers via dig or socket fallback when possible."""

    dig_path = shutil.which("dig")
    if dig_path:
        return _dig_answers(dig_path, hostname, record_type)
    if record_type == "CNAME":
        raise RuntimeError(
            "dig is required to inspect CNAME ownership drift; install dig and rerun "
            "the diagnostic."
        )
    if record_type == "A":
        return _socket_answers(hostname, socket.AF_INET)
    if record_type == "AAAA":
        return _socket_answers(hostname, socket.AF_INET6)
    return ()


def _parse_http_probe(stdout: str, url: str) -> HttpProbe:
    """Extract status line and headers from curl HEAD output."""

    status_code: int | None = None
    headers: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper().startswith("HTTP/"):
            headers = {}
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                status_code = int(parts[1])
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return HttpProbe(url=url, status_code=status_code, headers=headers)


def _probe_https(curl_path: str, hostname: str) -> HttpProbe:
    """Issue a HEAD request without following redirects to inspect edge behavior."""

    url = f"https://{hostname}"
    result = _run_command(
        [
            curl_path,
            "-I",
            "-sS",
            "--max-time",
            str(HTTP_TIMEOUT_SEC),
            url,
        ],
        timeout=HTTP_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown curl error"
        return HttpProbe(url=url, status_code=None, headers={}, error=stderr)
    return _parse_http_probe(result.stdout, url)


def collect_domain_report(domain: str) -> DomainReport:
    """Gather DNS answers and HTTPS probe results for apex and www."""

    normalized_domain = _normalize_domain(domain)
    curl_path = _resolve_binary("curl")
    apex_host = normalized_domain
    www_host = f"www.{normalized_domain}"
    return DomainReport(
        domain=normalized_domain,
        apex_a=_collect_dns_answers(apex_host, "A"),
        apex_aaaa=_collect_dns_answers(apex_host, "AAAA"),
        www_a=_collect_dns_answers(www_host, "A"),
        www_aaaa=_collect_dns_answers(www_host, "AAAA"),
        www_cname=_collect_dns_answers(www_host, "CNAME"),
        apex_probe=_probe_https(curl_path, apex_host),
        www_probe=_probe_https(curl_path, www_host),
    )


def _is_expected_redirect(location: str, domain: str) -> bool:
    """Accept redirect targets that remain on the apex production host."""

    normalized = location.strip().lower().rstrip("/")
    return normalized == f"https://{domain}" or normalized.startswith(f"https://{domain}/")


def evaluate_report(report: DomainReport) -> list[str]:
    """Return topology drift findings. Empty list means healthy."""

    findings: list[str] = []
    if not report.apex_a:
        findings.append(f"Apex A lookup returned no values for {report.domain}.")
    if report.apex_aaaa:
        findings.append(
            "Conflicting apex AAAA records detected for "
            f"{report.domain}: {', '.join(report.apex_aaaa)}"
        )
    if report.apex_probe.error:
        findings.append(f"Apex HTTPS probe failed: {report.apex_probe.error}")
    elif report.apex_probe.status_code not in EXPECTED_APEX_STATUSES:
        findings.append(
            f"Apex HTTPS probe returned unexpected status {report.apex_probe.status_code} "
            f"for https://{report.domain}."
        )
    elif report.apex_probe.status_code in EXPECTED_REDIRECT_STATUSES:
        location = report.apex_probe.headers.get("location", "")
        if not location:
            findings.append("Apex redirect response is missing the Location header.")
        elif not _is_expected_redirect(location, report.domain):
            findings.append(
                f"Apex redirect points to unexpected target {location!r}; "
                "expected the repo-owned apex host."
            )

    if not report.www_a and not report.www_cname:
        findings.append(f"www host does not resolve via A or CNAME for www.{report.domain}.")
    if report.www_probe.error:
        findings.append(f"www HTTPS probe failed: {report.www_probe.error}")
    elif report.www_probe.status_code == 525:
        findings.append(
            f"www host returned 525 for https://www.{report.domain}; verify repo-owned DNS, "
            "Full (strict), and origin cert coverage for apex + www."
        )
    elif report.www_probe.status_code not in EXPECTED_WWW_STATUSES:
        findings.append(
            f"www host returned unexpected status {report.www_probe.status_code} "
            f"for https://www.{report.domain}; expected redirect to apex."
        )
    else:
        location = report.www_probe.headers.get("location", "")
        if not location:
            findings.append("www redirect response is missing the Location header.")
        elif not _is_expected_redirect(location, report.domain):
            findings.append(
                f"www redirect points to unexpected target {location!r}; expected apex repo host."
            )

    if any(answer == FIGMA_SITES_HOST for answer in report.www_cname):
        findings.append(
            f"www CNAME points to {FIGMA_SITES_HOST}; detach production root from Figma Sites."
        )
    return findings


def format_report(report: DomainReport, findings: list[str]) -> str:
    """Render a human-readable diagnostic report."""

    lines = [
        f"Domain TLS diagnostic for {report.domain}",
        f"apex A: {', '.join(report.apex_a) if report.apex_a else '(none)'}",
        f"apex AAAA: {', '.join(report.apex_aaaa) if report.apex_aaaa else '(none)'}",
        f"www A: {', '.join(report.www_a) if report.www_a else '(none)'}",
        f"www AAAA: {', '.join(report.www_aaaa) if report.www_aaaa else '(none)'}",
        f"www CNAME: {', '.join(report.www_cname) if report.www_cname else '(none)'}",
        (
            f"apex HTTPS: {report.apex_probe.status_code}"
            if report.apex_probe.status_code is not None
            else f"apex HTTPS: ERROR ({report.apex_probe.error})"
        ),
        (
            "www HTTPS: "
            f"{report.www_probe.status_code} -> {report.www_probe.headers.get('location', '(no location)')}"
            if report.www_probe.status_code is not None
            else f"www HTTPS: ERROR ({report.www_probe.error})"
        ),
    ]
    if findings:
        lines.append("FAIL: topology drift detected")
        lines.extend(f"- {finding}" for finding in findings)
        lines.append(
            "Next step: keep pulseplate.app and www repo-owned, preserve Full (strict), "
            "and run bash scripts/diagnose_production.sh on the origin after public-side drift is confirmed."
        )
    else:
        lines.append("PASS: apex is healthy and www redirects to the repo-owned apex host")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="check_domain_tls",
        description="Read-only public DNS/TLS diagnostic for repo-canonical production domains.",
    )
    parser.add_argument("--domain", required=True, help="Apex hostname, for example pulseplate.app")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = collect_domain_report(args.domain)
        findings = evaluate_report(report)
    except (RuntimeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return DRIFT_EXIT_CODE
    print(format_report(report, findings))
    return SUCCESS_EXIT_CODE if not findings else DRIFT_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
