"""Guard the temporary Pygments exception seam against upstream drift.

This CI-oriented check keeps the documented `pip-audit --ignore-vuln` seam for
`GHSA-5239-wwwm-4pmq` honest. As soon as the public GHSA advisory reports that
a fixed version exists, or the tracked open alerts disappear when repository
alerts are readable, the guard fails until the repo removes the temporary
exception and refreshes the pinned dependency state.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

ADVISORY_ID = "GHSA-5239-wwwm-4pmq"
PACKAGE_NAME = "pygments"
TRACKED_REQUIREMENTS = (
    "requirements.txt",
    "requirements-ci-lite.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
    "requirements-test.txt",
)
PRE_COMMIT_PATH = ".pre-commit-config.yaml"
DEPENDABOT_ALERTS_PER_PAGE = 100

_PIN_RE = re.compile(r"^\s*pygments==(?P<version>[^\s#]+)", re.IGNORECASE)
_IGNORE_SEAM_RE = re.compile(
    rf'(?im)^\s*-\s*["\']?--ignore-vuln["\']?\s*$'
    rf"(?:\n^\s*#.*$|\n^\s*$)*"
    rf'\n^\s*-\s*["\']?{re.escape(ADVISORY_ID)}["\']?\s*$'
)
_RELEASE_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")


def _api_request_with_headers(
    url: str,
    token: str | None = None,
) -> tuple[Any, http.client.HTTPMessage]:
    """Perform a GitHub REST API request and return parsed JSON plus headers."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise ValueError(f"Unsupported API URL: {url}")

    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pulseplate-pygments-exception-guard",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    conn.request("GET", path, headers=headers)
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    conn.close()

    if response.status >= 400:
        raise urllib.error.HTTPError(
            url=url,
            code=response.status,
            msg=response.reason,
            hdrs=response.headers,
            fp=None,
        )
    return json.loads(body), response.headers


def _api_request(url: str, token: str | None = None) -> Any:
    """Perform a GitHub REST API request and return parsed JSON."""
    payload, _headers = _api_request_with_headers(url, token)
    return payload


def _public_api_request(url: str, token: str | None = None) -> Any:
    """Perform a GitHub REST API request that can fall back to public access."""
    try:
        return _api_request(url, token)
    except urllib.error.HTTPError as exc:
        if token and exc.code in {401, 403}:
            return _api_request(url, None)
        raise


def _extract_relevant_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return open Dependabot alerts for the tracked Pygments advisory."""
    relevant: list[dict[str, Any]] = []
    for alert in alerts:
        dependency = alert.get("dependency", {})
        package = dependency.get("package", {})
        advisory = alert.get("security_advisory", {})
        if package.get("name", "").lower() != PACKAGE_NAME:
            continue
        if advisory.get("ghsa_id") != ADVISORY_ID:
            continue
        relevant.append(alert)
    return relevant


def _first_patched_versions(alerts: list[dict[str, Any]]) -> set[str]:
    """Collect first patched versions from all relevant alert surfaces."""
    patched_versions: set[str] = set()
    for alert in alerts:
        security_vulnerability = alert.get("security_vulnerability", {})
        patched = security_vulnerability.get("first_patched_version")
        if isinstance(patched, dict):
            identifier = patched.get("identifier")
            if identifier:
                patched_versions.add(identifier)
    return patched_versions


def _advisory_first_patched_versions(advisory_payload: dict[str, Any]) -> set[str]:
    """Collect first patched versions from the public GHSA advisory payload."""
    patched_versions: set[str] = set()
    for vulnerability in advisory_payload.get("vulnerabilities", []):
        if not isinstance(vulnerability, dict):
            continue
        package = vulnerability.get("package", {})
        if str(package.get("name", "")).lower() != PACKAGE_NAME:
            continue
        identifier = vulnerability.get("first_patched_version")
        if identifier:
            patched_versions.add(str(identifier))
    return patched_versions


def _read_requirement_pins(repo_root: Path) -> dict[str, str | None]:
    """Read the currently pinned Pygments versions from tracked requirement files."""
    pins: dict[str, str | None] = {}
    for relative_path in TRACKED_REQUIREMENTS:
        path = repo_root / relative_path
        version: str | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _PIN_RE.match(line)
            if match:
                version = match.group("version")
                break
        pins[relative_path] = version
    return pins


def _parse_release_version(identifier: str) -> tuple[int, ...] | None:
    """Parse dotted numeric release versions without external packaging deps."""
    normalized = identifier.strip()
    if not _RELEASE_VERSION_RE.fullmatch(normalized):
        return None
    parts = [int(part) for part in normalized.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _has_exception_seam(repo_root: Path) -> bool:
    """Return True when the temporary pip-audit ignore is still present."""
    pre_commit = repo_root / PRE_COMMIT_PATH
    content = pre_commit.read_text(encoding="utf-8")
    return _IGNORE_SEAM_RE.search(content) is not None


def evaluate_guard_state(
    *,
    alerts: list[dict[str, Any]] | None,
    advisory_patched_versions: set[str],
    pins: Mapping[str, str | None],
    exception_present: bool,
) -> list[str]:
    """Evaluate whether the temporary exception seam must now be removed."""
    errors: list[str] = []
    relevant_alerts = _extract_relevant_alerts(alerts or [])
    patched_versions = _first_patched_versions(relevant_alerts) | advisory_patched_versions

    if alerts is not None and not relevant_alerts:
        if exception_present:
            errors.append(
                "No open Dependabot alerts remain for GHSA-5239-wwwm-4pmq, but the "
                "temporary pip-audit exception seam is still present."
            )
        if not patched_versions:
            return errors

    if not patched_versions:
        return errors

    parsed_patched_versions: dict[str, tuple[int, ...]] = {}
    invalid_patched = sorted(
        identifier for identifier in patched_versions if _parse_release_version(identifier) is None
    )
    if invalid_patched:
        errors.append("Patched version metadata is invalid: " + ", ".join(invalid_patched))
        return errors
    for identifier in patched_versions:
        parsed = _parse_release_version(identifier)
        if parsed is not None:
            parsed_patched_versions[identifier] = parsed

    patched_floor = max(parsed_patched_versions.values())

    patched_list = ", ".join(sorted(patched_versions))
    if exception_present:
        errors.append(
            "Dependabot reports a patched release for GHSA-5239-wwwm-4pmq "
            f"({patched_list}), but .pre-commit-config.yaml still ignores the advisory."
        )

    stale_pins: dict[str, str] = {}
    for path, version in pins.items():
        if version is None:
            stale_pins[path] = "missing"
            continue
        parsed_version = _parse_release_version(version)
        if parsed_version is None:
            stale_pins[path] = f"invalid:{version}"
            continue
        if parsed_version < patched_floor:
            stale_pins[path] = version

    if stale_pins:
        stale_render = ", ".join(
            f"{path}={version}" for path, version in sorted(stale_pins.items())
        )
        errors.append(
            "Dependabot reports a patched release for GHSA-5239-wwwm-4pmq "
            f"({patched_list}), but tracked requirement pins are still unresolved: {stale_render}."
        )
    return errors


def _resolve_repo() -> str | None:
    """Resolve the GitHub repository slug from the environment."""
    return os.environ.get("GITHUB_REPOSITORY", "").strip() or None


def _resolve_token() -> str | None:
    """Resolve a GitHub token from standard CI env vars."""
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _fetch_dependabot_alerts(*, repo: str, token: str) -> list[dict[str, Any]]:
    """Fetch open Dependabot alerts for the repository."""
    alerts: list[dict[str, Any]] = []
    url: str | None = (
        f"https://api.github.com/repos/{repo}/dependabot/alerts?state=open&per_page=100"
    )
    while url:
        payload, headers = _api_request_with_headers(url, token)
        if not isinstance(payload, list):
            raise ValueError("Dependabot alerts API returned a non-list payload")
        alerts.extend(payload)
        url = _extract_next_link(headers.get("Link"))
    return alerts


def _extract_next_link(link_header: str | None) -> str | None:
    """Extract the next-page URL from a GitHub Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        match = re.match(r"<(?P<url>[^>]+)>", section)
        if match:
            return match.group("url")
    return None


def _fetch_public_global_advisory(*, token: str | None) -> dict[str, Any]:
    """Fetch the public GHSA advisory payload for the tracked advisory."""
    url = f"https://api.github.com/advisories/{ADVISORY_ID}"
    payload = _public_api_request(url, token=token)
    if not isinstance(payload, dict):
        raise ValueError("Global advisory API returned a non-dict payload")
    return payload


def main() -> int:
    """Run the CI guard and return a process status code."""
    parser = argparse.ArgumentParser(
        description="Fail when the temporary Pygments exception seam should be removed."
    )
    parser.parse_args()

    token = _resolve_token()
    repo = _resolve_repo()
    in_ci = os.environ.get("CI", "").lower() == "true"

    if not token or not repo:
        if in_ci:
            print("ERROR: GH_TOKEN/GITHUB_TOKEN and GITHUB_REPOSITORY are required in CI.")
            return 1
        print("SKIP: missing GitHub auth or repository context outside CI.")
        return 0

    alerts: list[dict[str, Any]] | None = None
    try:
        alerts = _fetch_dependabot_alerts(repo=repo, token=token)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            print(
                "WARN: Dependabot alerts endpoint is not accessible with the current token; "
                "falling back to the public GHSA advisory."
            )
        else:
            print(f"ERROR: failed to query Dependabot alerts: {exc}")
            return 1 if in_ci else 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: failed to query Dependabot alerts: {exc}")
        return 1 if in_ci else 0

    try:
        advisory_payload = _fetch_public_global_advisory(token=token)
    except (urllib.error.HTTPError, OSError, ValueError) as exc:
        print(f"ERROR: failed to query public GHSA advisory: {exc}")
        return 1 if in_ci else 0

    pins = _read_requirement_pins(REPO_ROOT)
    exception_present = _has_exception_seam(REPO_ROOT)
    errors = evaluate_guard_state(
        alerts=alerts,
        advisory_patched_versions=_advisory_first_patched_versions(advisory_payload),
        pins=pins,
        exception_present=exception_present,
    )
    if errors:
        print("ERROR: Pygments exception guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: Pygments exception seam remains upstream-blocked; no removal required yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
