from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts.ci import docker_image_telemetry


def _write_context_files(tmp_path: Path) -> tuple[Path, Path]:
    dockerfile = tmp_path / "Dockerfile"
    dockerignore = tmp_path / ".dockerignore"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM python:3.13-slim AS builder",
                "COPY requirements.txt requirements-ci-lite.txt constraints.txt ./",
                "COPY --chown=pulseplate:pulseplate app/ ./app/",
                "COPY --from=builder /opt/venv /opt/venv",
            ]
        ),
        encoding="utf-8",
    )
    dockerignore.write_text(
        "\n".join(
            [
                "**",
                "!Dockerfile",
                "!requirements.txt",
                "!requirements-ci-lite.txt",
                "!constraints.txt",
                "!scripts/",
                "!scripts/ci/",
                "!scripts/ci/emergency_python_wheels.json",
            ]
        ),
        encoding="utf-8",
    )
    return dockerfile, dockerignore


def test_run_docker_uses_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="[]", stderr="")

    import subprocess

    monkeypatch.setattr(docker_image_telemetry, "DOCKER_BINARY", "/usr/bin/docker")
    monkeypatch.setattr(docker_image_telemetry.subprocess, "run", _fake_run)

    docker_image_telemetry._run_docker(["image", "inspect", "pulseplate:test"])

    assert captured["args"] == (["/usr/bin/docker", "image", "inspect", "pulseplate:test"],)
    assert captured["kwargs"]["timeout"] == docker_image_telemetry.DOCKER_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    ("size_text", "expected_bytes"),
    (
        ("65.4kB", 65_400),
        ("65.4k", 65_400),
        ("12MB", 12_000_000),
        ("512B", 512),
    ),
)
def test_human_size_to_bytes_accepts_docker_style_units(
    size_text: str, expected_bytes: int
) -> None:
    assert docker_image_telemetry._human_size_to_bytes(size_text) == expected_bytes


def test_parse_copy_inputs_supports_shell_and_json_forms(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM python:3.13-slim AS builder",
                'COPY ["requirements.txt", "constraints.txt", "/tmp/deps/"]',
                "COPY --chown=pulseplate:pulseplate app/ ./app/",
                "COPY --from=builder /opt/venv /opt/venv",
            ]
        ),
        encoding="utf-8",
    )

    assert docker_image_telemetry._parse_copy_inputs(dockerfile) == (
        "requirements.txt",
        "constraints.txt",
        "app/",
    )


def test_load_baseline_size_bytes_rejects_non_object_payload(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(["unexpected", "payload"]), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Unsupported baseline payload shape"):
        docker_image_telemetry._load_baseline_size_bytes(baseline_path)


@pytest.mark.parametrize("raw_value", ("0", "-1"))
def test_positive_int_rejects_non_positive_values(raw_value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="greater than 0"):
        docker_image_telemetry._positive_int(raw_value)


def test_read_history_rows_redacts_created_by(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    stdout = '\n'.join(
        [
            '{"CreatedBy":"RUN pip install --index-url https://user:pass@example.com/simple","Size":"10MB"}',
            '{"CreatedBy":"RUN echo SAFE","Size":"5MB"}',
        ]
    )

    monkeypatch.setattr(
        docker_image_telemetry,
        "_run_docker",
        lambda _args: subprocess.CompletedProcess(
            args=["docker", "history"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    )

    rows = docker_image_telemetry._read_history_rows("pulseplate:test")

    assert len(rows) == 2
    assert all(
        row.created_by == docker_image_telemetry.REDACTED_CREATED_BY for row in rows
    )
    assert rows[0].size_bytes == 10_000_000
    assert rows[1].size_bytes == 5_000_000


def test_collect_telemetry_without_baseline_is_warning_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dockerfile, dockerignore = _write_context_files(tmp_path)
    history_rows = [
        docker_image_telemetry.LayerTelemetry(
            created_by="RUN apt-get update",
            size_bytes=30_000_000,
            size_human="30MB",
        ),
        docker_image_telemetry.LayerTelemetry(
            created_by="COPY app/ ./app/",
            size_bytes=5_000_000,
            size_human="5MB",
        ),
    ]

    monkeypatch.setattr(docker_image_telemetry, "_read_image_size_bytes", lambda _: 95_000_000)
    monkeypatch.setattr(docker_image_telemetry, "_read_history_rows", lambda _: history_rows)

    report = docker_image_telemetry.collect_telemetry(
        image_ref="pulseplate:test",
        dockerfile_path=dockerfile,
        dockerignore_path=dockerignore,
        top_layers=2,
        baseline_path=None,
    )

    assert report.advisory_only is True
    assert report.image_size_bytes == 95_000_000
    assert report.largest_layers == tuple(history_rows)
    assert report.build_context.copy_inputs == (
        "requirements.txt",
        "requirements-ci-lite.txt",
        "constraints.txt",
        "app/",
    )
    assert "!scripts/ci/emergency_python_wheels.json" in report.build_context.dockerignore_allowlist
    assert report.baseline.baseline_size_bytes is None
    assert report.baseline.regression_warning is False
    assert "telemetry remains advisory-only" in report.warnings[0]


def test_main_writes_warning_only_growth_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dockerfile, dockerignore = _write_context_files(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"image_size_bytes": 80_000_000}), encoding="utf-8")

    monkeypatch.setattr(docker_image_telemetry, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docker_image_telemetry, "_read_image_size_bytes", lambda _: 95_000_000)
    monkeypatch.setattr(
        docker_image_telemetry,
        "_read_history_rows",
        lambda _: [
            docker_image_telemetry.LayerTelemetry(
                created_by="RUN python -m pip install -r requirements.txt",
                size_bytes=12_500_000,
                size_human="12.5MB",
            )
        ],
    )

    json_out = tmp_path / "telemetry.json"
    markdown_out = tmp_path / "telemetry.md"
    exit_code = docker_image_telemetry.main(
        [
            "--image-ref",
            "pulseplate:test",
            "--dockerfile",
            dockerfile.name,
            "--dockerignore",
            dockerignore.name,
            "--baseline-json",
            baseline_path.name,
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["advisory_only"] is True
    assert payload["image_size_bytes"] == 95_000_000
    assert payload["baseline"]["baseline_size_bytes"] == 80_000_000
    assert payload["baseline"]["size_delta_bytes"] == 15_000_000
    assert payload["baseline"]["regression_warning"] is True
    assert "warning-only mode keeps the lane non-blocking" in payload["warnings"][0]
    assert "Docker Image Telemetry" in markdown
    assert "Delta vs baseline" in markdown
    assert "Build Context Evidence" in markdown
