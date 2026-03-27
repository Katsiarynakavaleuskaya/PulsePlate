from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import collect_ci_metrics


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    runs: list[dict[str, object]],
    jobs_by_run_id: dict[int, list[dict[str, object]]],
    logs_by_job_id: dict[int, str] | None = None,
    log_exc: Exception | None = None,
) -> tuple[int, dict[str, object], str]:
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

    def fake_fetch_job_log_text(**kwargs: object) -> str:
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

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")
    return exit_code, payload, markdown


def test_main_writes_metrics_for_successful_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs = [
        {
            "id": 301,
            "run_number": 9,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": "2026-03-27T08:00:00Z",
            "run_started_at": "2026-03-27T08:01:00Z",
            "updated_at": "2026-03-27T08:06:00Z",
            "jobs_url": "https://example.invalid/jobs/301",
        },
        {
            "id": 300,
            "run_number": 8,
            "head_sha": "sha-0",
            "conclusion": "success",
            "created_at": "2026-03-26T08:00:00Z",
            "run_started_at": "2026-03-26T08:01:00Z",
            "updated_at": "2026-03-26T08:04:00Z",
            "jobs_url": "https://example.invalid/jobs/300",
        },
    ]
    jobs_by_run_id = {
        301: [
            {
                "id": 901,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": "2026-03-27T08:01:00Z",
                "completed_at": "2026-03-27T08:05:00Z",
            },
            {
                "id": 902,
                "name": "diff-coverage",
                "conclusion": "success",
                "started_at": "2026-03-27T08:05:00Z",
                "completed_at": "2026-03-27T08:06:00Z",
            },
        ],
        300: [
            {
                "id": 903,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": "2026-03-26T08:01:00Z",
                "completed_at": "2026-03-26T08:05:00Z",
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
    runs = [
        {
            "id": 401,
            "run_number": 12,
            "head_sha": "sha-rerun",
            "conclusion": "success",
            "created_at": "2026-03-27T09:00:00Z",
            "run_started_at": "2026-03-27T09:01:00Z",
            "updated_at": "2026-03-27T09:06:00Z",
            "jobs_url": "https://example.invalid/jobs/401",
        },
        {
            "id": 400,
            "run_number": 11,
            "head_sha": "sha-rerun",
            "conclusion": "failure",
            "created_at": "2026-03-27T08:00:00Z",
            "run_started_at": "2026-03-27T08:01:00Z",
            "updated_at": "2026-03-27T08:04:00Z",
            "jobs_url": "https://example.invalid/jobs/400",
        },
        {
            "id": 399,
            "run_number": 10,
            "head_sha": "sha-cancelled",
            "conclusion": "cancelled",
            "created_at": "2026-03-26T08:00:00Z",
            "run_started_at": "2026-03-26T08:01:00Z",
            "updated_at": "2026-03-26T08:02:00Z",
            "jobs_url": "https://example.invalid/jobs/399",
        },
    ]
    jobs_by_run_id = {
        401: [
            {
                "id": 911,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": "2026-03-27T09:01:00Z",
                "completed_at": "2026-03-27T09:05:00Z",
            }
        ],
        400: [
            {
                "id": 912,
                "name": "test-main (3.13)",
                "conclusion": "failure",
                "started_at": "2026-03-27T08:01:00Z",
                "completed_at": "2026-03-27T08:03:00Z",
            }
        ],
        399: [
            {
                "id": 913,
                "name": "test-main (3.13)",
                "conclusion": "cancelled",
                "started_at": "2026-03-26T08:01:00Z",
                "completed_at": "2026-03-26T08:02:00Z",
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
    runs = [
        {
            "id": 501,
            "run_number": 4,
            "head_sha": "sha-1",
            "conclusion": "success",
            "created_at": "2026-03-27T08:00:00Z",
            "run_started_at": "2026-03-27T08:01:00Z",
            "updated_at": "2026-03-27T08:06:00Z",
            "jobs_url": "https://example.invalid/jobs/501",
        }
    ]
    jobs_by_run_id = {
        501: [
            {
                "id": 921,
                "name": "test-main (3.13)",
                "conclusion": "success",
                "started_at": "2026-03-27T08:01:00Z",
                "completed_at": "2026-03-27T08:05:00Z",
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
    assert payload["red_build_rate"]["state"] == "unavailable"
    assert payload["xdist_fallback_frequency"]["state"] == "unavailable"
    assert "No completed CI runs found inside the lookback window." in markdown


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
