from __future__ import annotations

import json
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from scripts.ci import collect_ci_metrics


def _anchor_now() -> datetime:
    """Return a stable UTC anchor for relative timestamp generation."""

    return datetime.now(UTC).replace(microsecond=0)


def _iso_utc(value: datetime) -> str:
    """Render a UTC datetime using the GitHub API timestamp shape."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    runs: list[dict[str, Any]],
    jobs_by_run_id: dict[int, list[dict[str, Any]]],
    logs_by_job_id: dict[int, str] | None = None,
    log_exc: Exception | None = None,
) -> tuple[int, dict[str, Any], str]:
    logs_by_job_id = logs_by_job_id or {}
    json_out = tmp_path / "ci-metrics-summary.json"
    markdown_out = tmp_path / "ci-metrics-summary.md"

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(
        collect_ci_metrics,
        "_fetch_workflow_runs",
        lambda **kwargs: runs,
    )
    monkeypatch.setattr(
        collect_ci_metrics,
        "_fetch_run_jobs",
        lambda **kwargs: jobs_by_run_id[int(str(kwargs["jobs_url"]).rsplit("/", 1)[-1])],
    )

    def fake_fetch_job_log_text(**kwargs: Any) -> str:
        job_id = int(kwargs["job_id"])
        if log_exc is not None:
            raise log_exc
        return logs_by_job_id[job_id]

    monkeypatch.setattr(collect_ci_metrics, "_fetch_job_log_text", fake_fetch_job_log_text)

    exit_code = collect_ci_metrics.main(
        [
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--lookback-days",
            "30",
            "--max-runs",
            "20",
        ]
    )

    payload = cast(dict[str, Any], json.loads(json_out.read_text(encoding="utf-8")))
    markdown = markdown_out.read_text(encoding="utf-8")
    return exit_code, payload, markdown


def test_main_writes_metrics_for_successful_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 301,
            "run_number": 9,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=54)),
            "jobs_url": "https://example.invalid/jobs/301",
        },
        {
            "id": 300,
            "run_number": 8,
            "head_sha": "sha-0",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(days=1, hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(days=1, minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(days=1, minutes=56)),
            "jobs_url": "https://example.invalid/jobs/300",
        },
    ]
    jobs_by_run_id = {
        301: [
            {
                "id": 901,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            },
            {
                "id": 902,
                "name": "diff-coverage",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=55)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=54)),
            },
        ],
        300: [
            {
                "id": 903,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(days=1, minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(days=1, minutes=55)),
            }
        ],
    }
    logs_by_job_id = {
        901: f"...\n{collect_ci_metrics.CI_XDIST_FALLBACK_MARKER}\n...",
        903: f"...\n{collect_ci_metrics.CI_XDIST_FALLBACK_MARKER}\n...",
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        logs_by_job_id=logs_by_job_id,
    )

    assert exit_code == 0
    assert payload["scanned_runs"] == 2
    assert payload["critical_path_duration"]["latest_run_id"] == 301
    assert payload["critical_path_duration"]["latest_run_duration_seconds"] == 300
    assert payload["reruns"]["rerun_count"] == 0
    assert payload["red_build_rate"]["red_build_rate"] == 0.0
    assert payload["xdist_fallback_frequency"]["fallback_hits"] == 2
    assert payload["xdist_fallback_frequency"]["fallback_rate"] == 1.0
    assert "Tier 1 CI Metrics Summary" in markdown
    assert "Latest CI run `301` took `300` seconds" in markdown


def test_main_counts_reruns_and_red_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 401,
            "run_number": 12,
            "head_sha": "sha-rerun",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=54)),
            "jobs_url": "https://example.invalid/jobs/401",
        },
        {
            "id": 400,
            "run_number": 11,
            "head_sha": "sha-rerun",
            "conclusion": "failure",
            "created_at": _iso_utc(anchor - timedelta(hours=2)),
            "run_started_at": _iso_utc(anchor - timedelta(hours=2) + timedelta(minutes=1)),
            "updated_at": _iso_utc(anchor - timedelta(hours=2) + timedelta(minutes=4)),
            "jobs_url": "https://example.invalid/jobs/400",
        },
        {
            "id": 399,
            "run_number": 10,
            "head_sha": "sha-cancelled",
            "conclusion": "cancelled",
            "created_at": _iso_utc(anchor - timedelta(days=1, hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(days=1, hours=1) + timedelta(minutes=1)),
            "updated_at": _iso_utc(anchor - timedelta(days=1, hours=1) + timedelta(minutes=2)),
            "jobs_url": "https://example.invalid/jobs/399",
        },
    ]
    jobs_by_run_id = {
        401: [
            {
                "id": 911,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ],
        400: [
            {
                "id": 912,
                "name": "test-main (3.13)",
                "conclusion": "failure",
                "started_at": _iso_utc(anchor - timedelta(hours=2) + timedelta(minutes=1)),
                "completed_at": _iso_utc(anchor - timedelta(hours=2) + timedelta(minutes=3)),
            }
        ],
        399: [
            {
                "id": 913,
                "name": "test-main (3.13)",
                "conclusion": "cancelled",
                "started_at": _iso_utc(anchor - timedelta(days=1, hours=1) + timedelta(minutes=1)),
                "completed_at": _iso_utc(
                    anchor - timedelta(days=1, hours=1) + timedelta(minutes=2)
                ),
            }
        ],
    }
    logs_by_job_id = {
        911: f"...\n{collect_ci_metrics.CI_XDIST_FALLBACK_MARKER}\n...",
        912: "...",
        913: "...",
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        logs_by_job_id=logs_by_job_id,
    )

    assert exit_code == 0
    assert payload["reruns"]["rerun_count"] == 1
    assert payload["reruns"]["rerun_rate"] == pytest.approx(1 / 3, rel=1e-3)
    assert payload["red_build_rate"]["red_runs"] == 2
    assert payload["red_build_rate"]["red_build_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert "Reruns: `1` across `3` scanned runs" in markdown


def test_main_marks_xdist_metric_unknown_when_log_lookup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 501,
            "run_number": 4,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=54)),
            "jobs_url": "https://example.invalid/jobs/501",
        }
    ]
    jobs_by_run_id = {
        501: [
            {
                "id": 921,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        log_exc=RuntimeError("logs unavailable"),
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert payload["warnings"]
    assert (
        "Python 3.13 xdist fallback frequency: Python 3.13 job logs were unavailable." in markdown
    )


def test_main_marks_xdist_metric_unknown_when_log_lookup_raises_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 502,
            "run_number": 5,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=54)),
            "jobs_url": "https://example.invalid/jobs/502",
        }
    ]
    jobs_by_run_id = {
        502: [
            {
                "id": 922,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        log_exc=TimeoutError("timed out while fetching logs"),
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert any("timed out while fetching logs" in warning for warning in payload["warnings"])
    assert (
        "Python 3.13 xdist fallback frequency: Python 3.13 job logs were unavailable." in markdown
    )


def test_main_marks_xdist_metric_unknown_when_no_canonical_python313_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_METRICS_PYTHON313_JOB_NAME", "custom-main-3.13")
    anchor = _anchor_now()
    runs = [
        {
            "id": 601,
            "run_number": 5,
            "head_sha": "sha-2",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=55)),
            "jobs_url": "https://example.invalid/jobs/601",
        }
    ]
    jobs_by_run_id = {
        601: [
            {
                "id": 931,
                "name": "test-main (3.12)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        logs_by_job_id={},
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert "No canonical Python 3.13 job 'custom-main-3.13' was found." in markdown
    assert any("no canonical 'custom-main-3.13' jobs" in warning for warning in payload["warnings"])


def test_main_marks_xdist_metric_unknown_when_python313_job_id_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 701,
            "run_number": 6,
            "head_sha": "sha-3",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=55)),
            "jobs_url": "https://example.invalid/jobs/701",
        }
    ]
    jobs_by_run_id = {
        701: [
            {
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        logs_by_job_id={},
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert "Python 3.13 job metadata was incomplete." in markdown
    assert any("did not include a job id" in warning for warning in payload["warnings"])


def test_main_marks_xdist_metric_unknown_when_python313_job_id_is_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 702,
            "run_number": 7,
            "head_sha": "sha-4",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=55)),
            "jobs_url": "https://example.invalid/jobs/702",
        }
    ]
    jobs_by_run_id = {
        702: [
            {
                "id": "not-an-int",
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        logs_by_job_id={},
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert "Python 3.13 job logs were unavailable." in markdown
    assert any("invalid literal for int()" in warning for warning in payload["warnings"])


def test_main_writes_valid_outputs_when_no_runs_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=[],
        jobs_by_run_id={},
        logs_by_job_id={},
    )

    assert exit_code == 0
    assert payload["scanned_runs"] == 0
    assert payload["critical_path_duration"]["state"] == "unavailable"
    assert payload["reruns"]["state"] == "unavailable"
    assert payload["red_build_rate"]["state"] == "unavailable"
    assert payload["xdist_fallback_frequency"]["state"] == "unavailable"
    assert "No completed CI runs found inside the lookback window." in markdown
    assert "Reruns: No completed CI runs found inside the lookback window." in markdown


def test_main_degrades_to_unavailable_when_workflow_runs_cannot_be_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_out = tmp_path / "ci-metrics-summary.json"
    markdown_out = tmp_path / "ci-metrics-summary.md"

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(
        collect_ci_metrics,
        "_fetch_workflow_runs",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("github api unavailable")),
    )

    exit_code = collect_ci_metrics.main(
        [
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["critical_path_duration"]["state"] == "unavailable"
    assert payload["reruns"]["state"] == "unavailable"
    assert payload["red_build_rate"]["state"] == "unavailable"
    assert payload["xdist_fallback_frequency"]["state"] == "unavailable"
    assert any("workflow runs could not be loaded" in warning for warning in payload["warnings"])
    assert "Workflow run metadata was unavailable." in markdown


def test_main_degrades_to_unavailable_when_workflow_runs_raise_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_out = tmp_path / "ci-metrics-summary.json"
    markdown_out = tmp_path / "ci-metrics-summary.md"

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(
        collect_ci_metrics,
        "_fetch_workflow_runs",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionResetError("github socket reset")),
    )

    exit_code = collect_ci_metrics.main(
        [
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["critical_path_duration"]["state"] == "unavailable"
    assert payload["reruns"]["state"] == "unavailable"
    assert payload["red_build_rate"]["state"] == "unavailable"
    assert payload["xdist_fallback_frequency"]["state"] == "unavailable"
    assert any("github socket reset" in warning for warning in payload["warnings"])
    assert "Workflow run metadata was unavailable." in markdown


def test_main_sanitizes_signed_urls_from_warning_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = _anchor_now()
    runs = [
        {
            "id": 503,
            "run_number": 6,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": _iso_utc(anchor - timedelta(hours=1)),
            "run_started_at": _iso_utc(anchor - timedelta(minutes=59)),
            "updated_at": _iso_utc(anchor - timedelta(minutes=54)),
            "jobs_url": "https://example.invalid/jobs/503",
        }
    ]
    jobs_by_run_id = {
        503: [
            {
                "id": 923,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": _iso_utc(anchor - timedelta(minutes=59)),
                "completed_at": _iso_utc(anchor - timedelta(minutes=55)),
            }
        ]
    }

    exit_code, payload, markdown = _run(
        tmp_path,
        monkeypatch,
        runs=runs,
        jobs_by_run_id=jobs_by_run_id,
        log_exc=RuntimeError(
            "Redirect limit exceeded while fetching https://api.github.com/foo; "
            "last location was https://pipelines.actions.githubusercontent.com/logs/download"
        ),
    )

    assert exit_code == 0
    assert payload["xdist_fallback_frequency"]["state"] == "unknown"
    assert all("https://" not in warning for warning in payload["warnings"])
    assert any("<redacted-url>" in warning for warning in payload["warnings"])
    assert "https://" not in markdown
    assert "<redacted-url>" in markdown


def test_fetch_workflow_runs_paginates_until_the_lookback_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchor = _anchor_now()
    requested_urls: list[str] = []
    page_payloads = {
        1: {
            "workflow_runs": [
                {"id": 801, "created_at": _iso_utc(anchor - timedelta(days=1))},
                {"id": 800, "created_at": _iso_utc(anchor - timedelta(days=2))},
            ]
        },
        2: {
            "workflow_runs": [
                {"id": 799, "created_at": _iso_utc(anchor - timedelta(days=3))},
                {"id": 798, "created_at": _iso_utc(anchor - timedelta(days=10))},
            ]
        },
    }

    def fake_api_json(url: str, *, token: str) -> object:
        requested_urls.append(url)
        page = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["page"][0])
        return page_payloads[page]

    monkeypatch.setattr(collect_ci_metrics, "_api_json", fake_api_json)

    runs = collect_ci_metrics._fetch_workflow_runs(
        repo="Katsiarynakavaleuskaya/PulsePlate",
        workflow_file="ci.yml",
        branch="main",
        lookback_days=7,
        max_runs=2,
        token="token",
    )

    assert [run["id"] for run in runs] == [801, 800, 799, 798]
    assert requested_urls == [
        "https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml/runs?branch=main&status=completed&per_page=2&page=1",
        "https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml/runs?branch=main&status=completed&per_page=2&page=2",
    ]


def test_parse_iso8601_returns_none_for_malformed_values() -> None:
    assert collect_ci_metrics._parse_iso8601("not-a-timestamp") is None


def test_read_text_url_raises_when_redirect_limit_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, *, status: int, location: str = "", body: bytes = b"") -> None:
            self.status = status
            self.reason = "Found" if status < 400 else "Error"
            self.headers = {"Location": location} if location else {}
            self._body = body

        def read(self) -> bytes:
            return self._body

    class FakeConnection:
        def __init__(self, netloc: str, timeout: int) -> None:
            self.netloc = netloc
            self.timeout = timeout

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            self.method = method
            self.path = path
            self.headers = headers

        def getresponse(self) -> FakeResponse:
            return FakeResponse(status=302, location="https://example.invalid/loop")

        def close(self) -> None:
            return None

    monkeypatch.setattr(collect_ci_metrics.http.client, "HTTPSConnection", FakeConnection)

    with pytest.raises(RuntimeError, match="Redirect limit exceeded"):
        collect_ci_metrics._read_text_url("https://example.invalid/start", max_redirect_hops=2)


def test_read_text_url_drops_github_api_headers_after_cross_host_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, *, status: int, location: str = "", body: bytes = b"") -> None:
            self.status = status
            self.reason = "Found" if status < 400 else "Error"
            self.headers = {"Location": location} if location else {}
            self._body = body

        def read(self) -> bytes:
            return self._body

    recorded_requests: list[dict[str, object]] = []

    class FakeConnection:
        def __init__(self, netloc: str, timeout: int) -> None:
            self.netloc = netloc
            self.timeout = timeout

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            recorded_requests.append(
                {"host": self.netloc, "method": method, "path": path, "headers": dict(headers)}
            )

        def getresponse(self) -> FakeResponse:
            if self.netloc == collect_ci_metrics.GITHUB_API_HOST:
                return FakeResponse(
                    status=302,
                    location="https://pipelines.actions.githubusercontent.com/logs/download",
                )
            return FakeResponse(status=200, body=b"log output")

        def close(self) -> None:
            return None

    monkeypatch.setattr(collect_ci_metrics.http.client, "HTTPSConnection", FakeConnection)

    body = collect_ci_metrics._read_text_url(
        "https://api.github.com/repos/octo/test/actions/jobs/1/logs",
        headers={
            "Authorization": "Bearer secret",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": collect_ci_metrics.USER_AGENT,
        },
    )

    assert body == "log output"
    assert len(recorded_requests) == 2
    assert recorded_requests[0]["host"] == collect_ci_metrics.GITHUB_API_HOST
    assert recorded_requests[0]["headers"]["Authorization"] == "Bearer secret"
    redirected_headers = recorded_requests[1]["headers"]
    assert recorded_requests[1]["host"] == "pipelines.actions.githubusercontent.com"
    assert "Authorization" not in redirected_headers
    assert "Accept" not in redirected_headers
    assert "X-GitHub-Api-Version" not in redirected_headers
    assert redirected_headers["User-Agent"] == collect_ci_metrics.USER_AGENT


def test_find_python313_job_uses_configurable_canonical_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI_METRICS_PYTHON313_JOB_NAME", "custom-main-3.13")

    found = collect_ci_metrics._find_python313_job(
        [
            {"id": 1, "name": "test-main (3.13)"},
            {"id": 2, "name": "custom-main-3.13"},
        ]
    )

    assert found == {"id": 2, "name": "custom-main-3.13"}


def test_main_uses_requested_workflow_and_branch_in_summary_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_out = tmp_path / "ci-metrics-summary.json"
    markdown_out = tmp_path / "ci-metrics-summary.md"

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(collect_ci_metrics, "_fetch_workflow_runs", lambda **kwargs: [])

    exit_code = collect_ci_metrics.main(
        [
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--branch",
            "release/hotfix",
            "--workflow-name",
            "CI Metrics Preview",
            "--workflow-file",
            "ci-metrics.yml",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["notes"] == [
        "Headline metrics are calculated from workflow 'CI Metrics Preview' on branch 'release/hotfix'."
    ]
    assert (
        "Headline metrics are calculated from workflow 'CI Metrics Preview' on branch 'release/hotfix'."
        in markdown
    )
    assert "Specialized add-on lanes remain contextual" not in markdown


def test_main_requires_repo_token_and_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = collect_ci_metrics.main(
        [
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--json-out",
            str(tmp_path / "summary.json"),
            "--markdown-out",
            str(tmp_path / "summary.md"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GH_TOKEN or GITHUB_TOKEN is required" in captured.out


def test_ci_metrics_workflow_remains_advisory_only() -> None:
    import yaml

    repo_root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (repo_root / ".github" / "workflows" / "ci-metrics.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    triggers = workflow["on"]

    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert "pull_request" not in triggers
    assert "push" not in triggers
    assert triggers["schedule"] == [{"cron": "0 13 * * 1"}]
