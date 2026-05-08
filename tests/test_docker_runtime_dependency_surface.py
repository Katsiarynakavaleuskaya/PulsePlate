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
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["timeout"] == runtime_surface.DOCKER_TIMEOUT_SECONDS


def test_run_docker_raises_when_docker_binary_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", None)

    with pytest.raises(RuntimeError, match="Docker-enabled environment"):
        runtime_surface._run_docker(["run", "--rm", "pulseplate:test", "python", "-V"])


def test_run_docker_wraps_called_process_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", "/usr/bin/docker")

    def _fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            returncode=125,
            cmd=["/usr/bin/docker", "run", "--rm", "pulseplate:test"],
            stderr="image not found",
        )

    monkeypatch.setattr(runtime_surface.subprocess, "run", _fake_run)

    with pytest.raises(RuntimeError, match="returncode=125"):
        runtime_surface._run_docker(["run", "--rm", "pulseplate:test", "python", "-V"])


def test_parse_installed_packages_normalizes_names() -> None:
    payload = json.dumps(["Sentence_Transformers", "FastAPI", "FastAPI"])

    assert runtime_surface.parse_installed_packages(payload) == (
        "fastapi",
        "sentence-transformers",
    )


def test_parse_installed_packages_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="JSON list of strings"):
        runtime_surface.parse_installed_packages(json.dumps({"fastapi": "0.135.1"}))


def test_parse_installed_debian_packages_normalizes_inventory() -> None:
    payload = (
        "ii \tlibGnuTLS30:amd64\t3.7.9-2+deb12u6\n"
        "rc \tapt\t\n"
        "ii \topenssl\t3.0.17-1~deb12u3\n"
    )

    assert runtime_surface.parse_installed_debian_packages(payload) == {
        "libgnutls30": "3.7.9-2+deb12u6",
        "openssl": "3.0.17-1~deb12u3",
    }


def test_parse_installed_debian_packages_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="'<status>\\\\t<name>\\\\t<version>'"):
        runtime_surface.parse_installed_debian_packages("libgnutls30 3.7.9-2+deb12u6\n")


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


def test_find_blocked_debian_packages_flags_exact_package_names() -> None:
    installed = {
        "libc6": "2.36-9+deb12u13",
        "libgnutls30": "3.7.9-2+deb12u6",
        "openssl": "3.0.17-1~deb12u3",
    }

    assert runtime_surface.find_blocked_debian_packages(
        installed,
        ("libgnutls30", "missing-package"),
    ) == ("libgnutls30=3.7.9-2+deb12u6",)


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


def test_build_result_fails_for_blocked_debian_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "inspect_image_packages",
        lambda _image: ("fastapi", "uvicorn"),
    )
    monkeypatch.setattr(
        runtime_surface,
        "inspect_image_debian_packages",
        lambda _image: {
            "apt": "2.6.1",
            "gpgv": "2.2.40-1.1",
            "libgnutls30": "3.7.9-2+deb12u6",
            "openssl": "3.0.17-1~deb12u3",
        },
    )

    result = runtime_surface.build_result(
        "pulseplate:test",
        ("pytest",),
        ("apt", "gpgv", "libgnutls30"),
    )

    assert result.blocked == ()
    assert result.installed_debian_count == 4
    assert result.blocked_debian_packages == (
        "apt=2.6.1",
        "gpgv=2.2.40-1.1",
        "libgnutls30=3.7.9-2+deb12u6",
    )
    assert result.passed is False


def test_main_writes_json_and_returns_failure_for_blocked_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        lambda _image, _blocked, _blocked_debian: runtime_surface.DependencySurfaceResult(
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
    assert payload["passed"] is False
    captured = capsys.readouterr()
    assert "pytest" in captured.err
    assert captured.out == ""


def test_main_extends_default_blocked_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_build_result(
        image: str,
        blocked_prefixes: tuple[str, ...],
        blocked_debian_packages: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        captured["image"] = image
        captured["blocked_prefixes"] = blocked_prefixes
        captured["blocked_debian_packages"] = blocked_debian_packages
        return runtime_surface.DependencySurfaceResult(
            image=image,
            installed_count=0,
            blocked=(),
            passed=True,
        )

    monkeypatch.setattr(runtime_surface, "build_result", _fake_build_result)

    exit_code = runtime_surface.main(
        ["--image", "pulseplate:test", "--blocked-prefix", "custom-guard"]
    )

    assert exit_code == 0
    assert captured["image"] == "pulseplate:test"
    assert captured["blocked_prefixes"] == runtime_surface.DEFAULT_BLOCKED_PREFIXES + (
        "custom-guard",
    )
    assert captured["blocked_debian_packages"] == ()


def test_main_accepts_blocked_debian_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_build_result(
        image: str,
        blocked_prefixes: tuple[str, ...],
        blocked_debian_packages: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        captured["image"] = image
        captured["blocked_prefixes"] = blocked_prefixes
        captured["blocked_debian_packages"] = blocked_debian_packages
        return runtime_surface.DependencySurfaceResult(
            image=image,
            installed_count=0,
            blocked=(),
            passed=True,
        )

    monkeypatch.setattr(runtime_surface, "build_result", _fake_build_result)

    exit_code = runtime_surface.main(
        [
            "--image",
            "pulseplate:test",
            "--blocked-debian-package",
            "apt",
            "--blocked-debian-package",
            "gpgv",
            "--blocked-debian-package",
            "libgnutls30",
        ]
    )

    assert exit_code == 0
    assert captured["image"] == "pulseplate:test"
    assert captured["blocked_prefixes"] == runtime_surface.DEFAULT_BLOCKED_PREFIXES
    assert captured["blocked_debian_packages"] == ("apt", "gpgv", "libgnutls30")


def test_main_returns_success_for_clean_runtime(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        lambda _image, _blocked, _blocked_debian: runtime_surface.DependencySurfaceResult(
            image="pulseplate:test",
            installed_count=2,
            blocked=(),
            passed=True,
        ),
    )

    exit_code = runtime_surface.main(["--image", "pulseplate:test"])

    assert exit_code == 0
    assert '"passed": true' in capsys.readouterr().out
