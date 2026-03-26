"""Guard the temporary Pygments exception seam against upstream drift.

This CI-oriented check keeps the documented `pip-audit --ignore-vuln` seam for
`GHSA-5239-wwwm-4pmq` honest. As soon as GitHub Dependabot reports that a fixed
version exists, or the tracked open alerts disappear, the guard fails until the
repo removes the temporary exception and refreshes the pinned dependency state.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

ADVISORY_ID = "GHSA-5239-wwwm-4pmq"
PACKAGE_NAME = "pygments"
TRACKED_REQUIREMENTS = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
)
PRE_COMMIT_PATH = ".pre-commit-config.yaml"
TARGET_VERSION = "2.19.2"

_PIN_RE = re.compile(r"^\s*pygments==(?P<version>[^\s#]+)", re.IGNORECASE)


def _api_request(url: str, token: str) -> Any:
    """Perform a GitHub REST API request and return parsed JSON."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise ValueError(f"Unsupported API URL: {url}")

    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
    conn.request(
        "GET",
        path,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pulseplate-pygments-exception-guard",
        },
    )
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
    return json.loads(body)


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


def _has_exception_seam(repo_root: Path) -> bool:
    """Return True when the temporary pip-audit ignore is still present."""
    pre_commit = repo_root / PRE_COMMIT_PATH
    content = pre_commit.read_text(encoding="utf-8")
    return f"--ignore-vuln\n          - {ADVISORY_ID}" in content


def evaluate_guard_state(
    *,
    alerts: list[dict[str, Any]],
    pins: dict[str, str | None],
    exception_present: bool,
) -> list[str]:
    """Evaluate whether the temporary exception seam must now be removed."""
    errors: list[str] = []
    relevant_alerts = _extract_relevant_alerts(alerts)
    patched_versions = _first_patched_versions(relevant_alerts)

    if not relevant_alerts:
        if exception_present:
            errors.append(
                "No open Dependabot alerts remain for GHSA-5239-wwwm-4pmq, but the "
                "temporary pip-audit exception seam is still present."
            )
        return errors

    if not patched_versions:
        return errors

    patched_list = ", ".join(sorted(patched_versions))
    if exception_present:
        errors.append(
            "Dependabot reports a patched release for GHSA-5239-wwwm-4pmq "
            f"({patched_list}), but .pre-commit-config.yaml still ignores the advisory."
        )

    stale_pins = {
        path: version
        for path, version in pins.items()
        if version is None or version == TARGET_VERSION
    }
    if stale_pins:
        stale_render = ", ".join(
            f"{path}={version or 'missing'}" for path, version in sorted(stale_pins.items())
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
    url = f"https://api.github.com/repos/{repo}/dependabot/alerts?state=open&per_page=100"
    payload = _api_request(url, token)
    if not isinstance(payload, list):
        raise ValueError("Dependabot alerts API returned a non-list payload")
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

    try:
        alerts = _fetch_dependabot_alerts(repo=repo, token=token)
    except (urllib.error.HTTPError, OSError, ValueError) as exc:
        print(f"ERROR: failed to query Dependabot alerts: {exc}")
        return 1 if in_ci else 0

    pins = _read_requirement_pins(REPO_ROOT)
    exception_present = _has_exception_seam(REPO_ROOT)
    errors = evaluate_guard_state(
        alerts=alerts,
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
