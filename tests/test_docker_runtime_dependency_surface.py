from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.ci import check_docker_runtime_dependency_surface as runtime_surface


def _native_image_report() -> dict[str, object]:
    return {
        "SchemaVersion": 2,
        "ArtifactName": "pulseplate:test",
        "ArtifactType": "container_image",
        "Metadata": {"ImageID": "sha256:" + "a" * 64},
        "Results": [
            {"Target": "pulseplate:test (debian 12)", "Class": "os-pkgs", "Type": "debian"}
        ],
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("SchemaVersion", 2.0, "schema version"),
        ("SchemaVersion", 1, "schema version"),
        ("ArtifactName", "another:image", "selected container"),
        ("ArtifactType", "filesystem", "selected container"),
        ("Metadata", None, "metadata"),
        ("Metadata", {"ImageID": "sha256:" + "b" * 64}, "image ID"),
        ("Results", [], "no package"),
        ("Results", {}, "no package"),
        ("Results", [None], "must be an object"),
        ("Results", [{}], "identity is missing"),
        ("Results", [{"Target": "x", "Class": "lang-pkgs", "Type": "python-pkg"}], "OS package"),
        (
            "Results",
            [{"Target": "x", "Class": "os-pkgs", "Type": "debian", "Vulnerabilities": None}],
            "array",
        ),
    ),
)
def test_native_trivy_report_rejects_missing_or_wrong_image_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object, message: str
) -> None:
    report = _native_image_report()
    report[field] = value
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(
            args, 0, stdout="sha256:" + "a" * 64 + "\n", stderr=""
        ),
    )
    with pytest.raises(ValueError, match=message):
        runtime_surface.validate_trivy_image_report("pulseplate:test", path)


@pytest.mark.parametrize("raw", ("", "{", "[]", "null"))
def test_native_trivy_report_rejects_empty_or_invalid_documents(tmp_path: Path, raw: str) -> None:
    path = tmp_path / "report.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        runtime_surface.validate_trivy_image_report("pulseplate:test", path)


def test_native_trivy_report_preserves_valid_findings_and_binds_live_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = _native_image_report()
    report["Results"] = [
        {
            "Target": "image",
            "Type": "debian",
            "Class": "os-pkgs",
            "Vulnerabilities": [{"VulnerabilityID": "CVE-test", "Severity": "HIGH"}],
        }
    ]
    path = tmp_path / "report.json"
    original = json.dumps(report)
    path.write_text(original, encoding="utf-8")
    calls: list[list[str]] = []

    def inspect(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="sha256:" + "a" * 64 + "\n", stderr="")

    monkeypatch.setattr(runtime_surface, "_run_docker", inspect)
    runtime_surface.validate_trivy_image_report("pulseplate:test", path)
    assert calls == [["image", "inspect", "--format", "{{.Id}}", "pulseplate:test"]]
    assert path.read_text() == original, "valid finding evidence must not be rewritten as clean"
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        runtime_surface.validate_trivy_image_report("pulseplate:test", alias)
    with pytest.raises(ValueError, match="regular"):
        runtime_surface.validate_trivy_image_report("pulseplate:test", tmp_path)


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
        "gzip": "1.12-1",
        "libc6": "2.36-9+deb12u13",
        "libgnutls30": "3.7.9-2+deb12u6",
        "libsqlite3-0": "3.40.1-2+deb12u2",
        "openssl": "3.0.17-1~deb12u3",
        "perl-base": "5.36.0-7+deb12u3",
        "perl-modules-5.36": "5.36.0-7+deb12u3",
    }

    assert runtime_surface.find_blocked_debian_packages(
        installed,
        ("gzip", "libgnutls30", "libsqlite3-0", "missing-package", "perl-base"),
        ("perl-modules-",),
    ) == (
        "gzip=1.12-1",
        "libgnutls30=3.7.9-2+deb12u6",
        "libsqlite3-0=3.40.1-2+deb12u2",
        "perl-base=5.36.0-7+deb12u3",
        "perl-modules-5.36=5.36.0-7+deb12u3",
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
            "gzip": "1.12-1",
            "gpgv": "2.2.40-1.1",
            "libgnutls30": "3.7.9-2+deb12u6",
            "libsqlite3-0": "3.40.1-2+deb12u2",
            "openssl": "3.0.17-1~deb12u3",
            "perl-base": "5.36.0-7+deb12u3",
            "perl-modules-5.36": "5.36.0-7+deb12u3",
        },
    )

    result = runtime_surface.build_result(
        "pulseplate:test",
        ("pytest",),
        ("apt", "gzip", "gpgv", "libgnutls30", "libsqlite3-0", "perl-base"),
        ("perl-modules-",),
    )

    assert result.blocked == ()
    assert result.installed_debian_count == 8
    assert result.blocked_debian_packages == (
        "apt=2.6.1",
        "gpgv=2.2.40-1.1",
        "gzip=1.12-1",
        "libgnutls30=3.7.9-2+deb12u6",
        "libsqlite3-0=3.40.1-2+deb12u2",
        "perl-base=5.36.0-7+deb12u3",
        "perl-modules-5.36=5.36.0-7+deb12u3",
    )
    assert result.passed is False


def test_main_writes_json_and_returns_failure_for_blocked_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _fake_build_result(
        _image: str,
        _blocked: tuple[str, ...],
        _blocked_debian: tuple[str, ...],
        _blocked_debian_prefixes: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        return runtime_surface.DependencySurfaceResult(
            image="pulseplate:test",
            installed_count=3,
            blocked=("pytest",),
            passed=False,
        )

    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        _fake_build_result,
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
        blocked_debian_prefixes: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        captured["image"] = image
        captured["blocked_prefixes"] = blocked_prefixes
        captured["blocked_debian_packages"] = blocked_debian_packages
        captured["blocked_debian_prefixes"] = blocked_debian_prefixes
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
    assert captured["blocked_debian_prefixes"] == ()


def test_main_accepts_blocked_debian_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_build_result(
        image: str,
        blocked_prefixes: tuple[str, ...],
        blocked_debian_packages: tuple[str, ...],
        blocked_debian_prefixes: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        captured["image"] = image
        captured["blocked_prefixes"] = blocked_prefixes
        captured["blocked_debian_packages"] = blocked_debian_packages
        captured["blocked_debian_prefixes"] = blocked_debian_prefixes
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
            "gzip",
            "--blocked-debian-package",
            "gpgv",
            "--blocked-debian-package",
            "libgnutls30",
            "--blocked-debian-package",
            "libsqlite3-0",
            "--blocked-debian-package",
            "perl-base",
            "--blocked-debian-prefix",
            "perl-modules-",
        ]
    )

    assert exit_code == 0
    assert captured["image"] == "pulseplate:test"
    assert captured["blocked_prefixes"] == runtime_surface.DEFAULT_BLOCKED_PREFIXES
    assert captured["blocked_debian_packages"] == (
        "apt",
        "gzip",
        "gpgv",
        "libgnutls30",
        "libsqlite3-0",
        "perl-base",
    )
    assert captured["blocked_debian_prefixes"] == ("perl-modules-",)


@pytest.mark.parametrize("with_report", [False, True])
def test_main_returns_success_for_clean_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    with_report: bool,
) -> None:
    def _fake_build_result(
        _image: str,
        _blocked: tuple[str, ...],
        _blocked_debian: tuple[str, ...],
        _blocked_debian_prefixes: tuple[str, ...],
    ) -> runtime_surface.DependencySurfaceResult:
        return runtime_surface.DependencySurfaceResult(
            image="pulseplate:test",
            installed_count=2,
            blocked=(),
            passed=True,
        )

    monkeypatch.setattr(
        runtime_surface,
        "build_result",
        _fake_build_result,
    )

    argv = ["--image", "pulseplate:test"]
    if with_report:
        path = tmp_path / "report.json"
        path.write_text(json.dumps(_native_image_report()))
        monkeypatch.setattr(
            runtime_surface,
            "_run_docker",
            lambda args: subprocess.CompletedProcess(
                args, 0, stdout="sha256:" + "a" * 64 + "\n", stderr=""
            ),
        )
        argv.extend(["--trivy-report", str(path)])
    exit_code = runtime_surface.main(argv)

    assert exit_code == 0
    assert '"passed": true' in capsys.readouterr().out


def test_main_invalid_report_cannot_emit_clean_inventory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "report.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="schema version"):
        runtime_surface.main(["--image", "pulseplate:test", "--trivy-report", str(path)])
    assert capsys.readouterr().out == ""
