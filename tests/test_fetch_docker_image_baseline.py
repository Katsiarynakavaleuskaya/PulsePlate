from __future__ import annotations

import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from scripts.ci import fetch_docker_image_baseline


def test_gh_path_uses_absolute_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch_docker_image_baseline.shutil, "which", lambda _: "/usr/bin/gh")

    assert fetch_docker_image_baseline._gh_path() == "/usr/bin/gh"


def test_auth_env_accepts_github_token_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")

    env = fetch_docker_image_baseline._auth_env()

    assert env["GH_TOKEN"] == "github-token"
    assert env["GITHUB_TOKEN"] == "github-token"


def test_extract_artifact_payload_requires_single_telemetry_json(tmp_path: Path) -> None:
    archive_path = tmp_path / "artifact.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("first/docker-image-telemetry.json", "{}")
        archive.writestr("second/docker-image-telemetry.json", "{}")

    with pytest.raises(RuntimeError, match="Expected exactly one"):
        fetch_docker_image_baseline._extract_artifact_payload(archive_path)


def test_fetch_main_artifact_baseline_normalizes_remote_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_docker_image_baseline, "_auth_env", lambda: {"GH_TOKEN": "token"})
    monkeypatch.setattr(fetch_docker_image_baseline, "_ensure_gh_auth", lambda env: None)
    monkeypatch.setattr(
        fetch_docker_image_baseline,
        "_find_run_and_artifact",
        lambda **_kwargs: (
            {
                "id": 11,
                "run_attempt": 2,
                "run_number": 345,
                "html_url": "https://github.com/example/repo/actions/runs/11",
            },
            {
                "id": 99,
                "name": "docker-image-telemetry-build",
            },
        ),
    )
    monkeypatch.setattr(
        fetch_docker_image_baseline,
        "_download_artifact_payload",
        lambda **_kwargs: {
            "image_size_bytes": 123456,
            "image_size_human": "123.46 KB",
        },
    )

    payload = fetch_docker_image_baseline.fetch_main_artifact_baseline(
        repo="owner/repo",
        workflow="build.yml",
        branch="main",
        artifact_name="docker-image-telemetry-build",
        per_page=10,
    )

    assert payload["baseline_source"] == "main-artifact"
    assert payload["image_size_bytes"] == 123456
    assert payload["baseline_reference"]["artifact_id"] == 99
    assert payload["baseline_reference"]["run_number"] == 345


def test_main_falls_back_to_repo_seed_when_remote_lookup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fallback_path = tmp_path / "fallback.json"
    output_path = tmp_path / "resolved.json"
    fallback_payload = {
        "baseline_source": "repo-seed-fallback",
        "image_size_bytes": 222,
    }
    fallback_path.write_text(json.dumps(fallback_payload), encoding="utf-8")
    monkeypatch.setattr(
        fetch_docker_image_baseline,
        "fetch_main_artifact_baseline",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("gh auth failed")),
    )

    exit_code = fetch_docker_image_baseline.main(
        [
            "--repo",
            "owner/repo",
            "--fallback-json",
            str(fallback_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == fallback_payload
    assert "using repo-seed-fallback baseline" in capsys.readouterr().err


def test_run_gh_uses_resolved_absolute_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(fetch_docker_image_baseline.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(fetch_docker_image_baseline.subprocess, "run", _fake_run)

    fetch_docker_image_baseline._run_gh(["api", "repos/owner/repo"], env={"GH_TOKEN": "token"})

    assert captured["args"] == (["/usr/bin/gh", "api", "repos/owner/repo"],)
    assert captured["kwargs"]["env"] == {"GH_TOKEN": "token"}
