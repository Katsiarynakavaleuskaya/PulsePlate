#!/usr/bin/env python3
"""Collect lightweight CI metrics for the canonical Tier 1 backend/shared lane."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

GITHUB_API_HOST = "api.github.com"
USER_AGENT = "pulseplate-ci-metrics"
CI_XDIST_FALLBACK_MARKER = "PYTEST_XDIST_ARGS=-p no:xdist"
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_MAX_RUNS = 20
DEFAULT_WORKFLOW_FILE = "ci.yml"
DEFAULT_WORKFLOW_NAME = "CI"
DEFAULT_BRANCH = "main"
DEFAULT_PYTHON313_JOB_NAME = "test-main (3.13)"
MAX_REDIRECT_HOPS = 5
GITHUB_API_ONLY_HEADERS = frozenset({"authorization", "accept", "x-github-api-version"})
WARNING_URL_RE = re.compile(r"https://\S+")
ADVISORY_NETWORK_EXCEPTIONS = (RuntimeError, urllib.error.HTTPError, ValueError, OSError)


def _github_token() -> str:
    """Return the preferred GitHub auth token from environment."""

    return os.getenv("GH_TOKEN", "").strip() or os.getenv("GITHUB_TOKEN", "").strip()


def _python313_job_name() -> str:
    """Return the canonical Python 3.13 job name for the Tier 1 CI lane."""

    return os.getenv("CI_METRICS_PYTHON313_JOB_NAME", "").strip() or DEFAULT_PYTHON313_JOB_NAME


def _headers_for_request_host(headers: dict[str, str], *, host: str) -> dict[str, str]:
    """Keep API auth headers only for api.github.com requests.

    RU: Signed log URLs уже авторизованы, поэтому GitHub API bearer нельзя отправлять на другой host.
    EN: Signed log URLs are already authorized, so never forward GitHub API bearer headers cross-host.
    """

    if host == GITHUB_API_HOST:
        return dict(headers)
    return {
        key: value for key, value in headers.items() if key.lower() not in GITHUB_API_ONLY_HEADERS
    }


def _warning_detail(exc: Exception) -> str:
    """Return a warning-safe exception detail without leaking signed URLs."""

    sanitized = WARNING_URL_RE.sub("<redacted-url>", str(exc)).strip()
    if sanitized:
        return sanitized
    return exc.__class__.__name__


def _parse_iso8601(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp into UTC-aware datetime."""

    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _duration_seconds(started_at: str, completed_at: str) -> int | None:
    """Return whole-second duration when both timestamps are available."""

    started = _parse_iso8601(started_at)
    completed = _parse_iso8601(completed_at)
    if started is None or completed is None:
        return None
    return max(0, int((completed - started).total_seconds()))


def _api_json(url: str, *, token: str) -> Any:
    """Perform one GitHub API request and decode JSON response."""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != GITHUB_API_HOST:
        raise ValueError(f"Unsupported API URL: {url}")

    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    try:
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        body = response.read()
    finally:
        conn.close()

    if response.status >= 400:
        raise urllib.error.HTTPError(
            url=url,
            code=response.status,
            msg=response.reason,
            hdrs=response.headers,
            fp=None,
        )
    return json.loads(body.decode("utf-8"))


def _read_text_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_redirect_hops: int = MAX_REDIRECT_HOPS,
) -> str:
    """Fetch plain-text content and follow one redirect when GitHub returns signed URLs.

    RU: Для job logs GitHub API отдаёт 302 на временный URL, поэтому follow делаем явно.
    EN: Job logs come back as 302 redirects to signed URLs, so follow them explicitly.
    """

    current_url = url
    current_headers = _headers_for_request_host(
        dict(headers or {}),
        host=urllib.parse.urlparse(current_url).netloc,
    )
    for redirect_hop in range(max_redirect_hops + 1):
        parsed = urllib.parse.urlparse(current_url)
        if parsed.scheme != "https":
            raise ValueError(f"Unsupported URL scheme: {current_url}")

        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
        try:
            conn.request("GET", path, headers=current_headers)
            response = conn.getresponse()
            body = response.read()
            location = response.headers.get("Location", "")
        finally:
            conn.close()

        if response.status in {301, 302, 303, 307, 308}:
            if not location:
                raise RuntimeError(f"Redirect without location for {current_url}")
            if redirect_hop >= max_redirect_hops:
                raise RuntimeError(
                    "Redirect limit exceeded while fetching " f"{url}; last location was {location}"
                )
            current_url = urllib.parse.urljoin(current_url, location)
            current_headers = _headers_for_request_host(
                current_headers,
                host=urllib.parse.urlparse(current_url).netloc,
            )
            continue

        if response.status >= 400:
            raise urllib.error.HTTPError(
                url=current_url,
                code=response.status,
                msg=response.reason,
                hdrs=response.headers,
                fp=None,
            )
        return body.decode("utf-8", errors="replace")

    raise RuntimeError(f"Redirect limit exceeded while fetching {url}")


def _fetch_workflow_runs(
    *,
    repo: str,
    workflow_file: str,
    branch: str,
    lookback_days: int,
    max_runs: int,
    token: str,
) -> list[dict[str, Any]]:
    """Fetch completed runs until the lookback boundary is reached."""

    owner, name = repo.split("/", maxsplit=1)
    recent_runs: list[dict[str, Any]] = []
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    page = 1

    while True:
        url = (
            f"https://{GITHUB_API_HOST}/repos/{owner}/{name}/actions/workflows/"
            f"{urllib.parse.quote(workflow_file, safe='')}/runs"
            f"?branch={urllib.parse.quote(branch, safe='')}"
            f"&status=completed&per_page={max_runs}&page={page}"
        )
        payload = _api_json(url, token=token)
        page_runs = list(payload.get("workflow_runs") or [])
        if not page_runs:
            break

        recent_runs.extend(page_runs)
        oldest_created_at = _parse_iso8601(str(page_runs[-1].get("created_at") or ""))
        if len(page_runs) < max_runs or (
            oldest_created_at is not None and oldest_created_at < cutoff
        ):
            break
        page += 1

    return recent_runs


def _fetch_run_jobs(*, jobs_url: str, token: str) -> list[dict[str, Any]]:
    """Fetch jobs for one workflow run."""

    payload = _api_json(jobs_url, token=token)
    return list(payload.get("jobs") or [])


def _fetch_job_log_text(*, repo: str, job_id: int, token: str) -> str:
    """Fetch raw log text for one job by following the API redirect."""

    owner, name = repo.split("/", maxsplit=1)
    url = f"https://{GITHUB_API_HOST}/repos/{owner}/{name}/actions/jobs/{job_id}/logs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    return _read_text_url(url, headers=headers)


def _filter_recent_runs(runs: list[dict[str, Any]], *, lookback_days: int) -> list[dict[str, Any]]:
    """Keep only runs whose creation timestamp falls within the lookback window."""

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    filtered: list[dict[str, Any]] = []
    for run in runs:
        created_at = _parse_iso8601(str(run.get("created_at") or ""))
        if created_at is not None and created_at >= cutoff:
            filtered.append(run)
    return filtered


def _rerun_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute rerun count/rate from repeated workflow runs on the same SHA."""

    if not runs:
        return {
            "state": "unavailable",
            "reason": "No completed CI runs found inside the lookback window.",
        }

    counts_by_sha: dict[str, int] = {}
    for run in runs:
        head_sha = str(run.get("head_sha") or "").strip()
        if not head_sha:
            continue
        counts_by_sha[head_sha] = counts_by_sha.get(head_sha, 0) + 1

    rerun_count = sum(max(0, count - 1) for count in counts_by_sha.values())
    scanned_runs = len(runs)
    rerun_rate = round(rerun_count / scanned_runs, 4)
    return {
        "state": "available",
        "rerun_count": rerun_count,
        "rerun_rate": rerun_rate,
        "unique_head_shas": len(counts_by_sha),
    }


def _red_build_rate_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute failed/cancelled rate across the scanned CI runs."""

    scanned_runs = len(runs)
    if scanned_runs == 0:
        return {
            "state": "unavailable",
            "reason": "No completed CI runs found inside the lookback window.",
        }

    red_conclusions = {"failure", "cancelled", "timed_out", "startup_failure", "stale"}
    red_runs = 0
    success_runs = 0
    neutral_runs = 0
    for run in runs:
        conclusion = str(run.get("conclusion") or "").strip().lower()
        if conclusion == "success":
            success_runs += 1
        elif conclusion in red_conclusions:
            red_runs += 1
        else:
            neutral_runs += 1

    return {
        "state": "available",
        "red_runs": red_runs,
        "successful_runs": success_runs,
        "neutral_runs": neutral_runs,
        "red_build_rate": round(red_runs / scanned_runs, 4),
    }


def _critical_path_summary(
    latest_run: dict[str, Any] | None, latest_jobs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Summarize duration of the latest completed canonical CI run and its jobs."""

    if latest_run is None:
        return {
            "state": "unavailable",
            "reason": "No completed CI runs found inside the lookback window.",
        }

    latest_run_duration_seconds = _duration_seconds(
        str(latest_run.get("run_started_at") or ""),
        str(latest_run.get("updated_at") or ""),
    )
    jobs: list[dict[str, Any]] = []
    for job in latest_jobs:
        if str(job.get("conclusion") or "").strip().lower() == "skipped":
            continue
        duration_seconds = _duration_seconds(
            str(job.get("started_at") or ""),
            str(job.get("completed_at") or ""),
        )
        jobs.append(
            {
                "name": str(job.get("name") or ""),
                "conclusion": str(job.get("conclusion") or ""),
                "duration_seconds": duration_seconds,
            }
        )

    return {
        "state": "available",
        "latest_run_id": latest_run.get("id"),
        "latest_run_number": latest_run.get("run_number"),
        "latest_run_conclusion": latest_run.get("conclusion"),
        "latest_run_duration_seconds": latest_run_duration_seconds,
        "jobs": jobs,
    }


def _find_python313_job(jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the canonical main-branch Python 3.13 job when present."""

    canonical_name = _python313_job_name().casefold()
    for job in jobs:
        name = str(job.get("name") or "").strip().casefold()
        if name == canonical_name:
            return job
    return None


def _xdist_fallback_summary(
    *,
    repo: str,
    latest_run: dict[str, Any] | None,
    latest_jobs: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    token: str,
) -> tuple[dict[str, Any], list[str]]:
    """Estimate xdist fallback frequency from the Python 3.13 canonical main job logs."""

    warnings: list[str] = []
    python313_job_name = _python313_job_name()
    if latest_run is None:
        return (
            {
                "state": "unavailable",
                "reason": "No completed CI runs found inside the lookback window.",
            },
            warnings,
        )

    observed_runs = 0
    fallback_hits = 0
    for run in runs:
        jobs_url = str(run.get("jobs_url") or "")
        if not jobs_url:
            continue
        try:
            jobs = (
                latest_jobs
                if run.get("id") == latest_run.get("id")
                else _fetch_run_jobs(jobs_url=jobs_url, token=token)
            )
        except ADVISORY_NETWORK_EXCEPTIONS as exc:
            warnings.append(
                "xdist fallback frequency is unknown because jobs for run "
                f"{run.get('id')} could not be loaded: {_warning_detail(exc)}"
            )
            return (
                {
                    "state": "unknown",
                    "reason": "Python 3.13 job metadata could not be loaded.",
                },
                warnings,
            )
        python313_job = _find_python313_job(jobs)
        if python313_job is None:
            continue
        observed_runs += 1
        raw_job_id = python313_job.get("id")
        if raw_job_id is None:
            warnings.append(
                "xdist fallback frequency is unknown because Python 3.13 job metadata "
                f"for run {run.get('id')} did not include a job id"
            )
            return (
                {
                    "state": "unknown",
                    "reason": "Python 3.13 job metadata was incomplete.",
                },
                warnings,
            )
        try:
            job_id = int(str(raw_job_id))
            log_text = _fetch_job_log_text(repo=repo, job_id=job_id, token=token)
        except ADVISORY_NETWORK_EXCEPTIONS as exc:
            warnings.append(
                "xdist fallback frequency is unknown because Python 3.13 job logs "
                f"could not be read for run {run.get('id')}: {_warning_detail(exc)}"
            )
            return (
                {
                    "state": "unknown",
                    "reason": "Python 3.13 job logs were unavailable.",
                },
                warnings,
            )
        if CI_XDIST_FALLBACK_MARKER in log_text:
            fallback_hits += 1

    if observed_runs == 0:
        warnings.append(
            "xdist fallback frequency is unknown because no canonical "
            f"'{python313_job_name}' jobs were found in the scanned CI runs."
        )
        return (
            {
                "state": "unknown",
                "reason": f"No canonical Python 3.13 job '{python313_job_name}' was found.",
            },
            warnings,
        )

    return (
        {
            "state": "available",
            "observed_runs": observed_runs,
            "fallback_hits": fallback_hits,
            "fallback_rate": round(fallback_hits / observed_runs, 4),
            "marker": CI_XDIST_FALLBACK_MARKER,
        },
        warnings,
    )


def _latest_completed_run(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest completed run from the filtered set."""

    if not runs:
        return None
    return max(runs, key=lambda run: str(run.get("created_at") or ""))


def _render_markdown_summary(payload: dict[str, Any]) -> str:
    """Render a compact Markdown report suitable for artifacts and step summary."""

    critical_path = payload["critical_path_duration"]
    reruns = payload["reruns"]
    red_build_rate = payload["red_build_rate"]
    xdist_fallback = payload["xdist_fallback_frequency"]
    warnings = list(payload.get("warnings") or [])
    notes = list(payload.get("notes") or [])

    lines = [
        "# Tier 1 CI Metrics Summary",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Repo: `{payload['repo']}`",
        f"- Workflow: `{payload['ci_workflow']}` on branch `{payload['branch']}`",
        f"- Lookback window: `{payload['lookback_days']}` days",
        f"- Scanned runs: `{payload['scanned_runs']}`",
        "",
        "## Highlights",
    ]

    if critical_path["state"] == "available":
        lines.append(
            f"- Latest CI run `{critical_path['latest_run_id']}` took "
            f"`{critical_path['latest_run_duration_seconds']}` seconds "
            f"with conclusion `{critical_path['latest_run_conclusion']}`."
        )
    else:
        lines.append(f"- Critical-path duration: {critical_path['reason']}")

    if reruns["state"] == "available":
        lines.append(
            f"- Reruns: `{reruns['rerun_count']}` across `{payload['scanned_runs']}` scanned runs "
            f"(rate `{reruns['rerun_rate']}`)."
        )
    else:
        lines.append(f"- Reruns: {reruns['reason']}")

    if red_build_rate["state"] == "available":
        lines.append(
            f"- Red-build rate: `{red_build_rate['red_build_rate']}` "
            f"(`{red_build_rate['red_runs']}` red, `{red_build_rate['successful_runs']}` successful)."
        )
    else:
        lines.append(f"- Red-build rate: {red_build_rate['reason']}")

    if xdist_fallback["state"] == "available":
        lines.append(
            f"- Python 3.13 xdist fallback frequency: `{xdist_fallback['fallback_rate']}` "
            f"(`{xdist_fallback['fallback_hits']}` / `{xdist_fallback['observed_runs']}`)."
        )
    else:
        lines.append(f"- Python 3.13 xdist fallback frequency: {xdist_fallback['reason']}")

    if critical_path["state"] == "available":
        lines.extend(["", "## Latest Run Job Durations"])
        for job in critical_path["jobs"]:
            lines.append(
                f"- `{job['name']}`: `{job['duration_seconds']}` seconds "
                f"({job['conclusion'] or 'unknown'})"
            )

    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    if notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in notes)

    return "\n".join(lines) + "\n"


def _build_summary(
    *,
    repo: str,
    branch: str,
    workflow_name: str,
    workflow_file: str,
    lookback_days: int,
    max_runs: int,
    token: str,
) -> dict[str, Any]:
    """Collect workflow metrics and return the canonical summary payload."""

    warnings: list[str] = []
    notes = [
        f"Headline metrics are calculated from workflow '{workflow_name}' on branch '{branch}'."
    ]
    if workflow_name == DEFAULT_WORKFLOW_NAME and branch == DEFAULT_BRANCH:
        notes.append(
            "Specialized add-on lanes remain contextual and do not influence the headline Tier 1 rates."
        )

    try:
        runs = _fetch_workflow_runs(
            repo=repo,
            workflow_file=workflow_file,
            branch=branch,
            lookback_days=lookback_days,
            max_runs=max_runs,
            token=token,
        )
    except ADVISORY_NETWORK_EXCEPTIONS as exc:
        unavailable_reason = "Workflow run metadata was unavailable."
        warnings.append(
            "CI metrics collection degraded because workflow runs could not be loaded: "
            f"{_warning_detail(exc)}"
        )
        return {
            "repo": repo,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "lookback_days": lookback_days,
            "max_runs": max_runs,
            "scanned_runs": 0,
            "branch": branch,
            "ci_workflow": workflow_name,
            "critical_path_duration": {
                "state": "unavailable",
                "reason": unavailable_reason,
            },
            "reruns": {
                "state": "unavailable",
                "reason": unavailable_reason,
            },
            "red_build_rate": {
                "state": "unavailable",
                "reason": unavailable_reason,
            },
            "xdist_fallback_frequency": {
                "state": "unavailable",
                "reason": unavailable_reason,
            },
            "notes": notes,
            "warnings": warnings,
        }

    recent_runs = _filter_recent_runs(runs, lookback_days=lookback_days)
    latest_run = _latest_completed_run(recent_runs)
    latest_jobs: list[dict[str, Any]] = []
    if latest_run is not None:
        latest_jobs_url = str(latest_run.get("jobs_url") or "")
        if latest_jobs_url:
            try:
                latest_jobs = _fetch_run_jobs(jobs_url=latest_jobs_url, token=token)
            except ADVISORY_NETWORK_EXCEPTIONS as exc:
                warnings.append(
                    "Latest CI run jobs could not be loaded; critical-path job details are incomplete: "
                    f"{_warning_detail(exc)}"
                )

    xdist_fallback_summary, xdist_warnings = _xdist_fallback_summary(
        repo=repo,
        latest_run=latest_run,
        latest_jobs=latest_jobs,
        runs=recent_runs,
        token=token,
    )
    warnings.extend(xdist_warnings)

    return {
        "repo": repo,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "lookback_days": lookback_days,
        "max_runs": max_runs,
        "scanned_runs": len(recent_runs),
        "branch": branch,
        "ci_workflow": workflow_name,
        "critical_path_duration": _critical_path_summary(latest_run, latest_jobs),
        "reruns": _rerun_summary(recent_runs),
        "red_build_rate": _red_build_rate_summary(recent_runs),
        "xdist_fallback_frequency": xdist_fallback_summary,
        "notes": notes,
        "warnings": warnings,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", "").strip(),
        help="Repository in owner/name format (default: GITHUB_REPOSITORY).",
    )
    parser.add_argument(
        "--workflow-file",
        default=DEFAULT_WORKFLOW_FILE,
        help=f"Workflow file to query (default: {DEFAULT_WORKFLOW_FILE}).",
    )
    parser.add_argument(
        "--workflow-name",
        default=DEFAULT_WORKFLOW_NAME,
        help=f"Display name for the workflow summary (default: {DEFAULT_WORKFLOW_NAME}).",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help=f"Branch to scan for workflow runs (default: {DEFAULT_BRANCH}).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Lookback window in days (default: {DEFAULT_LOOKBACK_DAYS}).",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=DEFAULT_MAX_RUNS,
        help=(
            "Page size when scanning completed workflow runs before filtering by lookback "
            f"(default: {DEFAULT_MAX_RUNS})."
        ),
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        required=True,
        help="Path to the JSON summary artifact.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        required=True,
        help="Path to the Markdown summary artifact.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if "/" not in args.repo:
        parser.error("--repo must be provided in owner/name format.")
    if args.lookback_days <= 0:
        parser.error("--lookback-days must be positive.")
    if args.max_runs <= 0:
        parser.error("--max-runs must be positive.")

    token = _github_token()
    if not token:
        print("ERROR: GH_TOKEN or GITHUB_TOKEN is required for CI metrics collection.")
        return 1

    payload = _build_summary(
        repo=args.repo,
        branch=args.branch,
        workflow_name=args.workflow_name,
        workflow_file=args.workflow_file,
        lookback_days=args.lookback_days,
        max_runs=args.max_runs,
        token=token,
    )
    markdown = _render_markdown_summary(payload)

    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(markdown, encoding="utf-8")

    print(
        f"ci-metrics: wrote {args.json_out} and {args.markdown_out} "
        f"for workflow '{args.workflow_name}' on '{args.branch}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
