#!/usr/bin/env python3
"""Fail-fast health and mirror-parity check for the private Python proxy."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from html.parser import HTMLParser
import json
import netrc
import os
from pathlib import Path
import re
import socket
import ssl
import sys
from typing import Any, Iterable, Iterator, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

INDEX_ENV_VAR = "PULSEPLATE_PYTHON_INDEX_URL"
NETRC_ENV_VAR = "PULSEPLATE_PYTHON_NETRC"
DEFAULT_PACKAGES_HOST = "packages.pulseplate.app"
DEFAULT_SIMPLE_ROOT_PATH = "/root/pulseplate/+simple/"
BLOCKED_PUBLIC_HOSTS = frozenset(
    {
        "pypi.org",
        "files.pythonhosted.org",
        "test.pypi.org",
        "pypi.python.org",
    }
)
PROJECT_NAME_RE = re.compile(r"[-_.]+")
PIN_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*==\s*"
    r"([A-Za-z0-9][A-Za-z0-9._+!~-]*)"
    r"(?:\s+--hash(?:=|\s+)[A-Za-z0-9:]+)*\s*$"
)
PACKAGE_REQUIREMENT_RE = re.compile(r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]+\])?\s*")
ORIGIN_UNHEALTHY_STATUSES = {500, 502, 503, 504, 520, 521, 522, 523, 524}
CLOUDFLARE_ORIGIN_MARKERS = (
    "error 521",
    "error 522",
    "origin is unreachable",
    "web server is down",
)
WHEEL_DISTRIBUTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._]*$")
WHEEL_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.!+]*$")
WHEEL_BUILD_TAG_RE = re.compile(r"^[0-9][A-Za-z0-9]*$")
WHEEL_TAG_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")
PYTHON_VERSION_RE = re.compile(r"^(?:cp)?(?P<major>3)(?:\.?)(?P<minor>\d{1,2})$")
REQUIRES_PYTHON_SPECIFIER_RE = re.compile(
    r"^(?P<operator>~=|==|!=|<=|>=|<|>)\s*" r"(?P<version>\d+(?:\.\d+){0,2})(?P<wildcard>\.\*)?$"
)
SHA256_FRAGMENT_RE = re.compile(r"^sha256=(?P<digest>[0-9a-fA-F]{64})$")


class NoRedirect(HTTPRedirectHandler):
    """Make redirects explicit failures so the probe cannot drift to public hosts."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


@dataclass(frozen=True)
class ProbeResult:
    project: str
    normalized_project: str
    project_url: str
    expected_version: str | None
    ok: bool
    reason: str
    status: int | None = None
    bytes_read: int = 0
    detail: str = ""

    def safe_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "project": self.project,
            "normalized_project": self.normalized_project,
            "project_url": redact_url_credentials(self.project_url),
            "expected_version": self.expected_version,
            "ok": self.ok,
            "reason": self.reason,
            "status": self.status,
            "bytes_read": self.bytes_read,
        }
        if self.detail:
            payload["detail"] = redact_text(self.detail)
        return payload


@dataclass(frozen=True)
class HealthSummary:
    ok: bool
    index_url: str
    host: str
    results: tuple[ProbeResult, ...]

    def safe_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "index_url": redact_url_credentials(self.index_url),
            "host": self.host,
            "results": [result.safe_dict() for result in self.results],
        }


@dataclass(frozen=True)
class _SimplePageAnchor:
    href: str
    requires_python: str | None


class _SimplePageAnchorParser(HTMLParser):
    """Collect bounded anchor metadata from an already-bounded Simple API body."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[_SimplePageAnchor] = []
        self.has_malformed_anchor = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        href: str | None = None
        href_seen = False
        href_is_ambiguous = False
        requires_python: str | None = None
        requires_python_seen = False
        requires_python_is_ambiguous = False
        for name, value in attrs:
            normalized_name = name.lower()
            if normalized_name == "href":
                if href_seen:
                    href_is_ambiguous = True
                    continue
                href_seen = True
                href = value
            elif normalized_name == "data-requires-python":
                if requires_python_seen:
                    requires_python_is_ambiguous = True
                    continue
                requires_python_seen = True
                requires_python = value or ""
        if href_is_ambiguous or requires_python_is_ambiguous:
            self.has_malformed_anchor = True
            return
        if href:
            self.anchors.append(_SimplePageAnchor(href=href, requires_python=requires_python))


def normalize_project_name(project: str) -> str:
    """Return the normalized Simple API project name."""
    normalized = PROJECT_NAME_RE.sub("-", project).lower().strip("-")
    if not normalized:
        raise ValueError("Project name must not normalize to an empty value.")
    return normalized


def redact_url_credentials(url: str) -> str:
    """Remove URL userinfo before displaying a URL."""
    parsed = urlparse(url)
    if parsed.hostname is None:
        return url
    netloc = parsed.hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def redact_text(value: str) -> str:
    """Remove URL credentials and common secret-bearing fragments from diagnostics."""
    redacted = re.sub(
        r"\b(?P<scheme>https?://)(?P<userinfo>[^/\s?#]+@)(?P<host>[^@\s/?#]+)",
        lambda match: f"{match.group('scheme')}{match.group('host')}",
        value,
    )
    redacted = re.sub(
        r"(?i)\bauthorization\s*[:=]\s*(?:bearer|basic)?\s*\S+",
        "Authorization=<redacted>",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(password|token|secret|devpi_ci_password)\s*[:=]\s*\S+",
        lambda match: f"{match.group(1)}=<redacted>",
        redacted,
    )
    return redacted


def basic_auth_from_netrc(hostname: str, *, netrc_file: Path | None = None) -> str | None:
    """Return a Basic Authorization header from .netrc for hostname, if present."""
    if netrc_file is None:
        env_path = os.environ.get(NETRC_ENV_VAR, "").strip()
        netrc_file = Path(env_path) if env_path else Path.home() / ".netrc"
    if not netrc_file.exists():
        return None

    try:
        parsed_netrc = netrc.netrc(str(netrc_file))
    except (netrc.NetrcParseError, OSError) as exc:
        raise ValueError(
            f"netrc_error: unable to read credentials for {hostname}: {type(exc).__name__}"
        ) from exc
    credentials = parsed_netrc.hosts.get(hostname)
    if credentials is None:
        return None

    login, _, password = credentials
    if not login or not password:
        raise ValueError(f"netrc_error: incomplete credentials for {hostname}")
    if login.strip().lower() == "root":
        raise ValueError("root_devpi_credentials: root devpi credentials are forbidden")
    token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def validate_index_url(
    index_url: str,
    *,
    expected_host: str = DEFAULT_PACKAGES_HOST,
    allow_dev_host: bool = False,
) -> str:
    """Validate and normalize the private proxy simple-index root URL."""
    normalized = index_url.strip()
    if not normalized:
        raise ValueError("missing_index_url: set PULSEPLATE_PYTHON_INDEX_URL")
    if "\n" in normalized or "\r" in normalized:
        raise ValueError("invalid_index_url: index URL must be a single line")

    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    path = parsed.path.rstrip("/") + "/"
    if parsed.scheme != "https":
        raise ValueError("non_https_index_url: private proxy index URL must use https")
    if not hostname:
        raise ValueError("invalid_index_url: index URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(
            "credentialed_index_url: inline credentials are forbidden; use .netrc secrets"
        )
    if hostname in BLOCKED_PUBLIC_HOSTS:
        raise ValueError(f"public_index_url: public package host is forbidden: {hostname}")
    if "pulseplate.app" == hostname:
        raise ValueError("unexpected_packages_host: marketing apex is not the package proxy")
    if hostname != expected_host and not allow_dev_host:
        raise ValueError(f"unexpected_packages_host: expected {expected_host}, got {hostname}")
    if path != DEFAULT_SIMPLE_ROOT_PATH:
        raise ValueError(
            "unexpected_index_path: expected canonical devpi simple root "
            f"{DEFAULT_SIMPLE_ROOT_PATH}"
        )
    if parsed.query or parsed.fragment:
        raise ValueError("invalid_index_url: query and fragment are not allowed")
    return normalized.rstrip("/") + "/"


def project_page_url(index_url: str, project: str) -> str:
    """Build the canonical Simple API project page URL for a project."""
    normalized_project = normalize_project_name(project)
    return index_url.rstrip("/") + "/" + quote(normalized_project, safe="") + "/"


def _iter_exact_pins(requirements_files: Iterable[Path]) -> Iterator[tuple[str, str]]:
    """Yield normalized exact package pins from requirements files."""
    for path in requirements_files:
        if not path.exists():
            raise FileNotFoundError(f"requirements file not found: {path}")
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
            if not line or line.startswith(("-", "--")):
                continue
            match = PIN_RE.match(line)
            if not match:
                if PACKAGE_REQUIREMENT_RE.match(line):
                    raise ValueError(f"non_exact_pin: {path}:{raw_line}")
                continue
            package, version = match.groups()
            yield normalize_project_name(package), version


def parse_exact_pins(requirements_files: Iterable[Path]) -> dict[str, str]:
    """Return canonical package name to exact pinned version from requirements files."""
    pins: dict[str, str] = {}
    for normalized_package, version in _iter_exact_pins(requirements_files):
        previous_version = pins.get(normalized_package)
        if previous_version is not None and previous_version != version:
            raise ValueError(
                "conflicting_exact_pins: "
                f"{normalized_package} has both {previous_version} and {version}"
            )
        pins[normalized_package] = version
    return pins


def parse_exact_pins_for_projects(
    requirements_files: Iterable[Path],
    projects: Iterable[str],
) -> dict[str, str]:
    """Return exact pins for selected probe projects across requirements files."""
    selected_projects = {normalize_project_name(project) for project in projects}
    pins: dict[str, str] = {}
    for normalized_package, version in _iter_exact_pins(requirements_files):
        if normalized_package not in selected_projects:
            continue
        previous_version = pins.get(normalized_package)
        if previous_version is not None and previous_version != version:
            raise ValueError(
                "conflicting_exact_pins: "
                f"{normalized_package} has both {previous_version} and {version}"
            )
        pins[normalized_package] = version
    return pins


def normalize_target_python_version(version: str) -> str:
    """Normalize a Python version such as 3.11 or cp311 into a wheel cp tag."""
    normalized = version.strip().lower()
    match = PYTHON_VERSION_RE.match(normalized)
    if not match:
        raise ValueError(f"invalid_python_version: expected 3.x or cp3x, got {version!r}")
    return f"cp{match.group('major')}{match.group('minor')}"


def default_target_python_versions() -> tuple[str, ...]:
    """Return the current interpreter as the default wheel compatibility target."""
    return (f"cp{sys.version_info.major}{sys.version_info.minor}",)


def normalize_target_python_versions(versions: Sequence[str] | None) -> tuple[str, ...]:
    """Return unique normalized target Python cp tags."""
    raw_versions = versions or default_target_python_versions()
    tags: list[str] = []
    for version in raw_versions:
        tag = normalize_target_python_version(version)
        if tag not in tags:
            tags.append(tag)
    return tuple(tags)


def simple_page_has_project_link(*, body: bytes, normalized_project: str) -> bool:
    """Return True when a response body looks like a Simple API project page."""
    text = body.decode("utf-8", errors="ignore").lower()
    package_markers = (
        f"{normalized_project}-",
        f"{normalized_project.replace('-', '_')}-",
    )
    return "href=" in text and any(marker in text for marker in package_markers)


def _parse_simple_page_anchors(
    body: bytes,
) -> tuple[tuple[_SimplePageAnchor, ...], bool]:
    """Parse anchors from the caller's max-byte-bounded response body."""
    parser = _SimplePageAnchorParser()
    parser.feed(body.decode("utf-8", errors="ignore"))
    parser.close()
    return tuple(parser.anchors), parser.has_malformed_anchor


def _artifact_filename_from_href(href: str, *, allowed_netloc: str | None) -> str:
    """Return a normalized URL-path basename without query or fragment metadata."""
    try:
        parsed = urlparse(href)
    except ValueError:
        return ""
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return ""
    if parsed.username is not None or parsed.password is not None:
        return ""
    if parsed.netloc and (
        allowed_netloc is None or parsed.netloc.lower() != allowed_netloc.lower()
    ):
        return ""
    path = parsed.path
    return unquote(path.rsplit("/", 1)[-1]).lower()


def _wheel_matches_exact_pin(
    filename: str,
    *,
    normalized_project: str,
    expected_version: str,
) -> bool:
    """Validate wheel structure and match its distribution/version components."""
    if not filename.endswith(".whl"):
        return False
    parts = filename[:-4].split("-")
    if len(parts) == 5:
        distribution, version, python_tag, abi_tag, platform_tag = parts
    elif len(parts) == 6:
        distribution, version, build_tag, python_tag, abi_tag, platform_tag = parts
        if WHEEL_BUILD_TAG_RE.fullmatch(build_tag) is None:
            return False
    else:
        return False
    if WHEEL_DISTRIBUTION_RE.fullmatch(distribution) is None:
        return False
    if WHEEL_VERSION_RE.fullmatch(version) is None:
        return False
    if any(WHEEL_TAG_RE.fullmatch(tag) is None for tag in (python_tag, abi_tag, platform_tag)):
        return False
    return (
        normalize_project_name(distribution) == normalized_project
        and version.lower() == expected_version.lower()
    )


def _exact_pin_wheel_links(
    *,
    body: bytes,
    normalized_project: str,
    expected_version: str,
    allowed_netloc: str | None = None,
) -> tuple[tuple[str, str | None], ...]:
    """Return exact-version wheel filenames with metadata from their own anchors."""
    links_by_filename: dict[str, str | None] = {}
    ambiguous_filenames: set[str] = set()
    anchors, has_malformed_anchor = _parse_simple_page_anchors(body)
    if has_malformed_anchor:
        return ()
    for anchor in anchors:
        filename = _artifact_filename_from_href(
            anchor.href,
            allowed_netloc=allowed_netloc,
        )
        if not _wheel_matches_exact_pin(
            filename,
            normalized_project=normalized_project,
            expected_version=expected_version,
        ):
            continue
        if filename in links_by_filename:
            ambiguous_filenames.add(filename)
            continue
        links_by_filename[filename] = anchor.requires_python
    return tuple(
        (filename, requires_python)
        for filename, requires_python in links_by_filename.items()
        if filename not in ambiguous_filenames
    )


def exact_pin_wheel_filenames(
    *,
    body: bytes,
    normalized_project: str,
    expected_version: str,
    allowed_netloc: str | None = None,
) -> tuple[str, ...]:
    """Return exact-version wheel filenames advertised on a Simple API project page."""
    filenames: list[str] = []
    seen: set[str] = set()
    for filename, _requires_python in _exact_pin_wheel_links(
        body=body,
        normalized_project=normalized_project,
        expected_version=expected_version,
        allowed_netloc=allowed_netloc,
    ):
        if filename in seen:
            continue
        seen.add(filename)
        filenames.append(filename)
    return tuple(filenames)


def trusted_exact_pin_wheel_hashes(
    *,
    body: bytes,
    project_url: str,
    normalized_project: str,
    expected_version: str,
) -> dict[str, str]:
    """Return exact wheel hashes only when every matching link is proxy-hosted.

    This is the artifact-admission parser used by governed lock compilation.
    Unlike the health probe's compatibility helpers, it fails closed when an
    exact-version wheel link leaves the canonical project origin, omits its
    SHA-256 fragment, or advertises one filename ambiguously.
    """

    project = urlparse(project_url)
    if (
        project.scheme.lower() != "https"
        or not project.netloc
        or project.username is not None
        or project.password is not None
        or project.query
        or project.fragment
    ):
        raise ValueError("artifact_admission_invalid_project_url")

    anchors, has_malformed_anchor = _parse_simple_page_anchors(body)
    if has_malformed_anchor:
        raise ValueError("artifact_admission_malformed_anchor")

    admitted: dict[str, str] = {}
    for anchor in anchors:
        try:
            raw_path = urlparse(anchor.href).path
        except ValueError as exc:
            raise ValueError("artifact_admission_malformed_href") from exc
        filename = unquote(raw_path.rsplit("/", 1)[-1]).lower()
        if not _wheel_matches_exact_pin(
            filename,
            normalized_project=normalized_project,
            expected_version=expected_version,
        ):
            continue

        resolved = urlparse(urljoin(project_url, anchor.href))
        if (
            resolved.scheme.lower() != "https"
            or resolved.netloc.lower() != project.netloc.lower()
            or resolved.username is not None
            or resolved.password is not None
            or resolved.query
        ):
            raise ValueError(f"artifact_admission_untrusted_url: {filename}")
        fragment_match = SHA256_FRAGMENT_RE.fullmatch(resolved.fragment)
        if fragment_match is None:
            raise ValueError(f"artifact_admission_missing_sha256: {filename}")
        digest = fragment_match.group("digest").lower()
        if filename in admitted:
            raise ValueError(f"artifact_admission_ambiguous_filename: {filename}")
        admitted[filename] = digest

    if not admitted:
        raise ValueError(
            f"artifact_admission_exact_pin_missing: " f"{normalized_project}=={expected_version}"
        )
    return admitted


def _platform_tag_is_linux_x86_64(platform_tag: str) -> bool:
    if platform_tag == "any":
        return True
    return platform_tag.endswith("_x86_64") and platform_tag.startswith(("manylinux", "linux"))


def _wheel_cp_number(cp_tag: str) -> int | None:
    if not cp_tag.startswith("cp") or not cp_tag[2:].isdigit():
        return None
    return int(cp_tag[2:])


def _python_tag_matches_target(
    *,
    python_tag: str,
    abi_tags: Sequence[str],
    target_python_tag: str,
) -> bool:
    if "none" in abi_tags and python_tag == "py3":
        return True
    if "none" in abi_tags and python_tag.startswith("py3") and python_tag[2:].isdigit():
        return python_tag[2:] == target_python_tag[2:]
    if not python_tag.startswith("cp"):
        return False
    target_number = _wheel_cp_number(target_python_tag)
    wheel_number = _wheel_cp_number(python_tag)
    if target_number is None or wheel_number is None:
        return False
    if "abi3" in abi_tags:
        return target_number >= wheel_number
    return python_tag == target_python_tag and target_python_tag in abi_tags


def wheel_is_compatible_with_targets(
    filename: str,
    *,
    target_python_versions: Sequence[str] | None = None,
) -> bool:
    """Return True when a wheel filename is installable on GitHub Ubuntu targets."""
    target_python_tags = normalize_target_python_versions(target_python_versions)
    wheel_name = filename.rsplit("/", 1)[-1].lower()
    if not wheel_name.endswith(".whl"):
        return False
    parts = wheel_name[:-4].split("-")
    if len(parts) < 5:
        return False

    python_tags = parts[-3].split(".")
    abi_tags = parts[-2].split(".")
    platform_tags = parts[-1].split(".")
    if not any(_platform_tag_is_linux_x86_64(tag) for tag in platform_tags):
        return False

    return any(
        _python_tag_matches_target(
            python_tag=python_tag,
            abi_tags=abi_tags,
            target_python_tag=target_python_tag,
        )
        for python_tag in python_tags
        for target_python_tag in target_python_tags
    )


def _compare_releases(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    padded_left = left + (0,) * (width - len(left))
    padded_right = right + (0,) * (width - len(right))
    return (padded_left > padded_right) - (padded_left < padded_right)


def _requires_python_clause_allows_target(
    clause: str,
    *,
    target_release: tuple[int, ...],
) -> bool:
    """Evaluate one bounded numeric clause; unsupported PEP 440 syntax fails closed."""
    match = REQUIRES_PYTHON_SPECIFIER_RE.fullmatch(clause.strip())
    if match is None:
        return False

    operator = match.group("operator")
    required_release = tuple(int(part) for part in match.group("version").split("."))
    target_floor = target_release + (0,)
    target_upper = (target_release[0], target_release[1] + 1, 0)
    wildcard = match.group("wildcard") is not None
    if wildcard:
        if operator not in {"==", "!="}:
            return False
        shared_prefix = target_release[: len(required_release)] == required_release
        if len(required_release) <= len(target_release):
            return shared_prefix if operator == "==" else not shared_prefix
        intersects_target_minor = required_release[: len(target_release)] == target_release
        return False if operator == "==" else not intersects_target_minor

    if operator == "==":
        return False
    if operator == "!=":
        return not (
            _compare_releases(required_release, target_floor) >= 0
            and _compare_releases(required_release, target_upper) < 0
        )
    if operator == "<=":
        # The target patch is intentionally unknown.  PEP 440 interprets
        # ``<=3.11`` as ``<=3.11.0``, so an inclusive bound covers the entire
        # target minor only when it reaches at least the next minor boundary.
        return _compare_releases(target_upper, required_release) <= 0
    if operator == ">=":
        return _compare_releases(target_floor, required_release) >= 0
    if operator == "<":
        return _compare_releases(target_upper, required_release) <= 0
    if operator == ">":
        return _compare_releases(target_floor, required_release) > 0
    if operator == "~=":
        if len(required_release) < 2:
            return False
        compatible_prefix = list(required_release[:-1])
        compatible_prefix[-1] += 1
        compatible_upper = tuple(compatible_prefix)
        return (
            _compare_releases(target_floor, required_release) >= 0
            and _compare_releases(target_upper, compatible_upper) <= 0
        )
    return False


def _requires_python_allows_target(
    requires_python: str | None,
    *,
    target_python_tag: str,
) -> bool:
    if requires_python is None:
        return True
    clauses = [clause.strip() for clause in requires_python.split(",")]
    if not clauses or any(not clause for clause in clauses):
        return False

    target_release = (int(target_python_tag[2]), int(target_python_tag[3:]))
    return all(
        _requires_python_clause_allows_target(
            clause,
            target_release=target_release,
        )
        for clause in clauses
    )


def simple_page_has_exact_pin(
    *,
    body: bytes,
    normalized_project: str,
    expected_version: str,
    target_python_versions: Sequence[str] | None = None,
    allowed_netloc: str | None = None,
) -> bool:
    """Return True when exact-version wheels cover every requested Python target."""
    wheel_links = _exact_pin_wheel_links(
        body=body,
        normalized_project=normalized_project,
        expected_version=expected_version,
        allowed_netloc=allowed_netloc,
    )
    target_python_tags = normalize_target_python_versions(target_python_versions)
    return all(
        any(
            wheel_is_compatible_with_targets(
                filename,
                target_python_versions=(target_python_tag,),
            )
            and _requires_python_allows_target(
                requires_python,
                target_python_tag=target_python_tag,
            )
            for filename, requires_python in wheel_links
        )
        for target_python_tag in target_python_tags
    )


def body_has_cloudflare_origin_error(body: bytes) -> bool:
    """Return True when a response body contains Cloudflare origin-error markers."""
    text = body[:20_000].decode("utf-8", errors="ignore").lower()
    return "cloudflare" in text and any(marker in text for marker in CLOUDFLARE_ORIGIN_MARKERS)


def classify_http_error(exc: HTTPError) -> str:
    """Map an HTTP error to a stable reason code."""
    if exc.code in ORIGIN_UNHEALTHY_STATUSES:
        return "origin_unhealthy"
    if exc.code in {301, 302, 303, 307, 308}:
        return "redirect_not_allowed"
    if exc.code in {401, 403}:
        return "auth_or_access_denied"
    if exc.code == 404:
        return "project_page_not_found"
    return "http_error"


def fetch_project_page(
    url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
    authorization_header: str | None = None,
) -> tuple[int, bytes]:
    """Fetch a project page with redirects disabled and bounded reads."""
    opener = build_opener(NoRedirect)
    headers = {"User-Agent": "PulsePlate-private-proxy-health/1"}
    if authorization_header:
        headers["Authorization"] = authorization_header
    request = Request(url, headers=headers)
    with opener.open(request, timeout=timeout_seconds) as response:
        status = int(getattr(response, "status", response.getcode()))
        body = response.read(max_bytes + 1)
    return status, body


def probe_project(
    *,
    index_url: str,
    project: str,
    expected_version: str | None,
    timeout_seconds: float,
    max_bytes: int,
    retries: int,
    authorization_header: str | None = None,
    target_python_versions: Sequence[str] | None = None,
) -> ProbeResult:
    """Probe one canonical Simple API project page."""
    normalized_project = normalize_project_name(project)
    url = project_page_url(index_url, normalized_project)
    last_detail = ""
    attempts = max(retries, 0) + 1
    for attempt in range(1, attempts + 1):
        try:
            status, body = fetch_project_page(
                url,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
                authorization_header=authorization_header,
            )
        except HTTPError as exc:
            reason = classify_http_error(exc)
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason=reason,
                status=exc.code,
                detail=f"HTTP {exc.code}",
            )
        except (TimeoutError, socket.timeout) as exc:
            last_detail = f"attempt {attempt}/{attempts}: {exc}"
            if attempt == attempts:
                return ProbeResult(
                    project=project,
                    normalized_project=normalized_project,
                    project_url=url,
                    expected_version=expected_version,
                    ok=False,
                    reason="tls_or_connect_timeout",
                    detail=last_detail,
                )
            continue
        except (URLError, ssl.SSLError, OSError) as exc:
            reason = "tls_or_connect_timeout" if _looks_like_timeout(exc) else "origin_unhealthy"
            last_detail = f"attempt {attempt}/{attempts}: {exc}"
            if attempt == attempts:
                return ProbeResult(
                    project=project,
                    normalized_project=normalized_project,
                    project_url=url,
                    expected_version=expected_version,
                    ok=False,
                    reason=reason,
                    detail=last_detail,
                )
            continue

        if status in ORIGIN_UNHEALTHY_STATUSES:
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="origin_unhealthy",
                status=status,
                bytes_read=len(body),
            )
        if status < 200 or status >= 300:
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="http_error",
                status=status,
                bytes_read=len(body),
            )
        if body_has_cloudflare_origin_error(body):
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="origin_unhealthy",
                status=status,
                bytes_read=len(body),
                detail="Cloudflare origin-error marker found in body",
            )
        if not body.strip():
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="empty_project_page",
                status=status,
                bytes_read=len(body),
            )
        if not simple_page_has_project_link(body=body, normalized_project=normalized_project):
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="simple_page_malformed",
                status=status,
                bytes_read=len(body),
            )
        if expected_version is None:
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="missing_exact_pin_in_requirements",
                status=status,
                bytes_read=len(body),
            )
        exact_wheels = exact_pin_wheel_filenames(
            body=body,
            normalized_project=normalized_project,
            expected_version=expected_version,
            allowed_netloc=urlparse(url).netloc,
        )
        if not exact_wheels:
            if len(body) > max_bytes:
                return ProbeResult(
                    project=project,
                    normalized_project=normalized_project,
                    project_url=url,
                    expected_version=expected_version,
                    ok=False,
                    reason="simple_page_truncated",
                    status=status,
                    bytes_read=len(body),
                )
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="mirror_lag_exact_pin_missing",
                status=status,
                bytes_read=len(body),
            )
        if not simple_page_has_exact_pin(
            body=body,
            normalized_project=normalized_project,
            expected_version=expected_version,
            target_python_versions=target_python_versions,
            allowed_netloc=urlparse(url).netloc,
        ):
            targets = ",".join(normalize_target_python_versions(target_python_versions))
            return ProbeResult(
                project=project,
                normalized_project=normalized_project,
                project_url=url,
                expected_version=expected_version,
                ok=False,
                reason="mirror_lag_compatible_wheel_missing",
                status=status,
                bytes_read=len(body),
                detail=f"no compatible Linux x86_64 wheel for {targets}",
            )
        return ProbeResult(
            project=project,
            normalized_project=normalized_project,
            project_url=url,
            expected_version=expected_version,
            ok=True,
            reason="ok",
            status=status,
            bytes_read=len(body),
        )

    return ProbeResult(
        project=project,
        normalized_project=normalized_project,
        project_url=url,
        expected_version=expected_version,
        ok=False,
        reason="origin_unhealthy",
        detail=last_detail,
    )


def _looks_like_timeout(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in ("timed out", "timeout", "temporarily unavailable"))


def check_health(
    *,
    index_url: str,
    projects: Sequence[str],
    pins: dict[str, str],
    expected_host: str,
    allow_dev_host: bool,
    timeout_seconds: float,
    max_bytes: int,
    retries: int,
    netrc_file: Path | None = None,
    target_python_versions: Sequence[str] | None = None,
) -> HealthSummary:
    """Run health checks for representative projects."""
    validated_index = validate_index_url(
        index_url,
        expected_host=expected_host,
        allow_dev_host=allow_dev_host,
    )
    parsed = urlparse(validated_index)
    host = (parsed.hostname or "").rstrip(".").lower()
    authorization_header = basic_auth_from_netrc(host, netrc_file=netrc_file)
    results = tuple(
        probe_project(
            index_url=validated_index,
            project=project,
            expected_version=pins.get(normalize_project_name(project)),
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            retries=retries,
            authorization_header=authorization_header,
            target_python_versions=target_python_versions,
        )
        for project in projects
    )
    return HealthSummary(
        ok=all(result.ok for result in results),
        index_url=validated_index,
        host=host,
        results=results,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index-url",
        default=os.environ.get(INDEX_ENV_VAR, ""),
        help=f"Private proxy simple-index root. Defaults to ${INDEX_ENV_VAR}.",
    )
    parser.add_argument(
        "--requirements-file",
        action="append",
        type=Path,
        default=[],
        help="Pinned requirements file used to find exact project versions. Repeatable.",
    )
    parser.add_argument(
        "--netrc-file",
        type=Path,
        default=None,
        help=f"Optional .netrc file for authenticated project-page probes. Defaults to ${NETRC_ENV_VAR} or ~/.netrc.",
    )
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Representative project to probe. Repeatable.",
    )
    parser.add_argument(
        "--python-version",
        action="append",
        default=[],
        help="GitHub Ubuntu Python target version for wheel tag parity, e.g. 3.11. Repeatable.",
    )
    parser.add_argument(
        "--expected-host",
        default=DEFAULT_PACKAGES_HOST,
        help="Expected private packages hostname.",
    )
    parser.add_argument(
        "--allow-dev-host",
        action="store_true",
        help="Allow non-production private hosts for local development only.",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Per-request timeout in seconds."
    )
    parser.add_argument(
        "--retries", type=int, default=1, help="Bounded retry count after the first attempt."
    )
    parser.add_argument(
        "--max-bytes", type=int, default=1_000_000, help="Maximum project page bytes to inspect."
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def emit_text(summary: HealthSummary) -> None:
    print(
        "private_python_proxy_health "
        f"ok={str(summary.ok).lower()} host={summary.host} index={redact_url_credentials(summary.index_url)}"
    )
    for result in summary.results:
        status = result.status if result.status is not None else "-"
        version = result.expected_version or "-"
        detail = f" detail={redact_text(result.detail)}" if result.detail else ""
        print(
            "project "
            f"name={result.normalized_project} status={status} expected={version} "
            f"bytes={result.bytes_read} reason={result.reason}{detail}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    projects = args.project or [
        "aiosqlite",
        "cryptography",
        "requests",
        "pytest-xdist",
        "hypothesis",
        "mypy",
        "ruff",
        "librt",
        "ast-serialize",
        "pgvector",
    ]
    requirements_files = args.requirements_file or [
        Path("requirements.txt"),
        Path("requirements-ci-lite.txt"),
        Path("requirements-test.txt"),
        Path("requirements-dev.txt"),
    ]
    try:
        pins = parse_exact_pins_for_projects(requirements_files, projects=projects)
        summary = check_health(
            index_url=args.index_url,
            projects=projects,
            pins=pins,
            expected_host=args.expected_host,
            allow_dev_host=args.allow_dev_host,
            timeout_seconds=args.timeout,
            max_bytes=args.max_bytes,
            retries=args.retries,
            netrc_file=args.netrc_file,
            target_python_versions=args.python_version,
        )
    except Exception as exc:
        message = redact_text(str(exc))
        if args.format == "json":
            print(json.dumps({"ok": False, "reason": message}, sort_keys=True))
        else:
            print(f"private_python_proxy_health ok=false reason={message}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(summary.safe_dict(), sort_keys=True))
    else:
        emit_text(summary)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
