from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.ci import check_docker_runtime_dependency_surface as runtime_surface


def test_run_docker_uses_timeout_and_absolute_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", "/usr/bin/docker")
    monkeypatch.setattr(runtime_surface.subprocess, "run", _fake_run)

    runtime_surface._run_docker(["run", "--rm", "pulseplate:test", "python", "-V"])

    assert captured["args"] == (
        ["/usr/bin/docker", "run", "--rm", "pulseplate:test", "python", "-V"],
    )
    assert captured["kwargs"]["timeout"] == runtime_surface.DOCKER_TIMEOUT_SECONDS


def test_parse_installed_packages_normalizes_names() -> None:
    payload = json.dumps(["Sentence_Transformers", "FastAPI", "FastAPI"])

    assert runtime_surface.parse_installed_packages(payload) == (
        "fastapi",
        "sentence-transformers",
    )


def test_parse_installed_packages_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="JSON list of strings"):
        runtime_surface.parse_installed_packages(json.dumps({"fastapi": "0.135.1"}))


def test_find_blocked_packages_flags_ci_and_vector_stack() -> None:
    installed = (
        "bandit",
        "fastapi",
        "huggingface-hub",
        "pytest",
        "sentence-transformers",
        "torch",
        "uvicorn",
    )

    assert runtime_surface.find_blocked_packages(
        installed,
        ("bandit", "pytest", "sentence-transformers", "torch", "huggingface-hub"),
    ) == (
        "bandit",
        "huggingface-hub",
        "pytest",
        "sentence-transformers",
        "torch",
    )


def test_build_result_uses_inspected_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "inspect_image_packages",
        lambda _image: ("fastapi", "pytest", "torch", "uvicorn"),
    )

    result = runtime_surface.build_result("pulseplate:test", ("pytest", "torch"))

    assert result.image == "pulseplate:test"
    assert result.installed_count == 4
    assert result.blocked == ("pytest", "torch")
    assert result.passed is False


def test_main_writes_json_and_returns_failure_for_blocked_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        lambda _image, _blocked: runtime_surface.DependencySurfaceResult(
            image="pulseplate:test",
            installed_count=3,
            blocked=("pytest",),
            passed=False,
        ),
    )

    output_path = tmp_path / "runtime-surface.json"
    exit_code = runtime_surface.main(
        ["--image", "pulseplate:test", "--output-json", str(output_path)]
    )

    assert exit_code == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["blocked"] == ["pytest"]
    assert "pytest" in capsys.readouterr().err


def test_main_returns_success_for_clean_runtime(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        lambda _image, _blocked: runtime_surface.DependencySurfaceResult(
            image="pulseplate:test",
            installed_count=2,
            blocked=(),
            passed=True,
        ),
    )

    exit_code = runtime_surface.main(["--image", "pulseplate:test"])

    assert exit_code == 0
    assert '"passed": true' in capsys.readouterr().out
