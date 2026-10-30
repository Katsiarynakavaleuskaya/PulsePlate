from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import traceback

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


@pytest.mark.parametrize("argv_kind", ["logs", "readiness"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "invalid-stdout",
        "invalid-stderr",
        "nonzero",
        "timeout",
        "nonzero-no-output",
        "timeout-no-output",
    ],
)
def test_run_docker_preserves_native_log_framing_and_hides_private_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str | None, argv_kind: str
) -> None:
    sentinel = b"synthetic-private-transport-sentinel"
    requested_fault, fault = fault, None
    kwargs_seen: list[dict[str, object]] = []
    command = (
        ["logs", "synthetic-owned-container"]
        if argv_kind == "logs"
        else [
            "exec",
            "synthetic-owned-container",
            "/bin/busybox",
            "sh",
            "-c",
            "synthetic readiness",
        ]
    )

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        kwargs_seen.append(kwargs)
        assert args == ["/usr/bin/docker", *command]
        if fault == "nonzero-no-output":
            raise subprocess.CalledProcessError(1, args)
        if fault == "timeout-no-output":
            raise subprocess.TimeoutExpired(args, 60)
        if fault == "nonzero":
            raise subprocess.CalledProcessError(1, args, output=sentinel, stderr=sentinel)
        if fault == "timeout":
            raise subprocess.TimeoutExpired(args, 60, output=sentinel, stderr=sentinel)
        stdout, stderr = b"first\r\nsecond\rlast\n", b"diagnostic\r\n"
        if fault == "invalid-stdout":
            stdout = sentinel + b"\xff"
        if fault == "invalid-stderr":
            stderr = sentinel + b"\xff"
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", "/usr/bin/docker")
    monkeypatch.setattr(runtime_surface.subprocess, "run", fake_run)
    baseline = runtime_surface._run_docker(command, preserve_newlines=True)
    assert baseline.stdout == "first\r\nsecond\rlast\n"
    assert baseline.stderr == "diagnostic\r\n"
    assert kwargs_seen[-1] == {
        "check": True,
        "capture_output": True,
        "text": False,
        "timeout": runtime_surface.DOCKER_TIMEOUT_SECONDS,
    }
    fault = requested_fault
    if fault is not None:
        message = (
            "UTF-8"
            if fault.startswith("invalid-")
            else "returncode=1" if fault.startswith("nonzero") else "timed out"
        )
        with pytest.raises(RuntimeError, match=message) as caught:
            runtime_surface._run_docker(command, preserve_newlines=True)
        rendered = "".join(traceback.format_exception(caught.value))
        assert sentinel.decode() not in rendered
        assert "CalledProcessError" not in rendered
        assert "TimeoutExpired" not in rendered
        assert "UnicodeDecodeError" not in rendered
        assert caught.value.__cause__ is None
        assert caught.value.__suppress_context__ is True
        # Suppression is a rendering boundary; exception memory is not erased.
        assert caught.value.__context__ is not None
        if fault.endswith("-no-output"):
            assert "Docker stdout capture unavailable" in caught.value.__notes__
            assert "Docker stderr capture unavailable" in caught.value.__notes__
        else:
            outputs = (
                (sentinel + b"\xff", b"diagnostic\r\n")
                if fault == "invalid-stdout"
                else (
                    (b"first\r\nsecond\rlast\n", sentinel + b"\xff")
                    if fault == "invalid-stderr"
                    else (sentinel, sentinel)
                )
            )
            for channel, output in zip(("stdout", "stderr"), outputs):
                assert (
                    "Docker "
                    + channel
                    + " bytes="
                    + str(len(output))
                    + " sha256="
                    + hashlib.sha256(output).hexdigest()
                    in caught.value.__notes__
                )
        path = tmp_path / "rendered-failure.txt"
        path.write_text(rendered)
        assert sentinel not in path.read_bytes()


def test_run_docker_default_timeout_keeps_existing_diagnostic_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["text"] is True
        raise subprocess.TimeoutExpired(
            args, 60, output="existing output", stderr="existing stderr"
        )

    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", "/usr/bin/docker")
    monkeypatch.setattr(runtime_surface.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out after 60s") as caught:
        runtime_surface._run_docker(["inspect", "synthetic-owned-container"])
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)


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


def _caddy_D_report() -> dict:
    image = "sha256:" + "a" * 64
    packages = []
    for name, (version, _checksum) in runtime_surface.CADDY_D_MODULES.items():
        packages.append(
            {
                "Name": name,
                "Version": version,
                "ID": name + "@" + version,
                "Identifier": {"PURL": "pkg:golang/" + name + "@" + version},
            }
        )
    finding = {
        **runtime_surface.CADDY_D_FINDING,
        "PkgIdentifier": {"PURL": packages[0]["Identifier"]["PURL"]},
    }
    return {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": image,
        "Metadata": {"ImageID": image, "ImageConfig": {"architecture": "amd64", "os": "linux"}},
        "Results": [
            {
                "Target": "image (alpine 3.23)",
                "Type": "alpine",
                "Class": "os-pkgs",
                "Packages": [{"Name": "busybox", "Version": "1", "ID": "busybox@1"}],
            },
            {
                "Target": "usr/bin/caddy",
                "Type": "gobinary",
                "Class": "lang-pkgs",
                "Packages": packages,
                "Vulnerabilities": [finding],
            },
        ],
    }


def _caddy_D_binary() -> bytes:
    return "".join(
        "dep\t" + name + "\t" + version + "\t" + checksum + "\n"
        for name, (version, checksum) in runtime_surface.CADDY_D_MODULES.items()
    ).encode()


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "CVE",
        "package",
        "version",
        "pkgid",
        "purl",
        "purl-null",
        "package-purl",
        "fixed",
        "status",
        "critical",
        "unknown-severity",
        "missing-severity",
        "extra-high",
        "duplicate",
        "missing-finding",
        "missing-packages",
        "missing-v4",
        "duplicate-v4",
        "v4-stale",
        "target",
        "class",
        "type",
        "architecture",
        "wrong-image",
        "binary-v4-stale",
        "binary-v3-stale",
        "binary-sum",
        "binary-replace",
        "binary-duplicate",
        "secrets",
        "secrets-null",
        "secrets-object",
        "secret-row",
        "scanner-error",
        "scanner-bool",
        "report-hash",
        "before-acceptance",
        "stale-review",
        "expired",
    ],
)
def test_caddy_D_exact_native_projection_and_negative_predicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from datetime import date
    import hashlib

    report = _caddy_D_report()
    row = report["Results"][1]
    finding = row["Vulnerabilities"][0]
    binary = _caddy_D_binary()
    today = date(2026, 10, 30)
    native_exit = 0
    fields = {
        "CVE": "VulnerabilityID",
        "package": "PkgName",
        "version": "InstalledVersion",
        "pkgid": "PkgID",
        "status": "Status",
    }
    if case in fields:
        finding[fields[case]] = "other"
    elif case in ("purl", "purl-null"):
        finding["PkgIdentifier"] = None if case == "purl-null" else {"PURL": "other"}
    elif case == "package-purl":
        row["Packages"][0]["Identifier"]["PURL"] = "other"
    elif case == "fixed":
        finding["FixedVersion"] = "3.0.6"
    elif case in ("critical", "unknown-severity"):
        finding["Severity"] = "CRITICAL" if case == "critical" else "unrecognized"
    elif case == "missing-severity":
        del finding["Severity"]
    elif case in ("extra-high", "duplicate"):
        row["Vulnerabilities"].append(
            {**finding, "VulnerabilityID": "CVE-extra"} if case == "extra-high" else dict(finding)
        )
    elif case == "missing-finding":
        row["Vulnerabilities"] = []
    elif case == "missing-packages":
        del row["Packages"]
    elif case == "missing-v4":
        row["Packages"].pop()
    elif case == "duplicate-v4":
        row["Packages"].append(dict(row["Packages"][1]))
    elif case == "v4-stale":
        row["Packages"][1]["Version"] = "v4.1.4"
    elif case in ("target", "class", "type"):
        row[case.title()] = "wrong"
    elif case == "architecture":
        report["Metadata"]["ImageConfig"]["architecture"] = "arm64"
    elif case == "wrong-image":
        report["Metadata"]["ImageID"] = "sha256:" + "b" * 64
    elif case.startswith("binary-"):
        if case == "binary-v4-stale":
            binary = binary.replace(b"v4.1.6", b"v4.1.4")
        elif case == "binary-v3-stale":
            binary = binary.replace(b"v3.0.5", b"v3.0.4")
        elif case == "binary-sum":
            binary = binary.replace(b"h1:", b"h2:")
        elif case == "binary-replace":
            binary += b"=>\tlocal/fork\tv0.0.0\n"
        else:
            binary += binary
    elif case.startswith("secrets"):
        row["Secrets"] = {"secrets": [{}], "secrets-null": None, "secrets-object": {}}[case]
    elif case == "secret-row":
        report["Results"].append(
            {"Target": "config", "Class": "secret", "Type": "text", "Secrets": [{}]}
        )
    elif case == "scanner-error":
        native_exit = 2
    elif case == "scanner-bool":
        native_exit = False
    elif case in ("before-acceptance", "stale-review", "expired"):
        today = {
            "before-acceptance": date(2026, 10, 27),
            "stale-review": date(2026, 10, 31),
            "expired": date(2026, 11, 5),
        }[case]
    path = tmp_path / "full.raw.json"
    path.write_text(json.dumps(report))
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if case != "report-hash" else "0" * 64
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(
            args, 0, stdout="sha256:" + "a" * 64 + "\n", stderr=""
        ),
    )
    original = path.read_bytes()
    arguments = {
        "binary_metadata": binary,
        "today": today,
        "native_exit": native_exit,
        "expected_report_sha256": digest,
    }
    if case == "valid":
        decision = runtime_surface.validate_caddy_ci_report(
            report["ArtifactName"], path, **arguments
        )
        assert decision["decision"] == "accepted_temporary_CI_residual_risk"
        assert len(decision["accepted"]) == 1
        assert decision["v3_fixed"] is False and decision["CD_release_accepted"] is False
        assert runtime_surface.validate_trivy_image_report(report["ArtifactName"], path) is None
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_ci_report("sha256:" + "a" * 64, path, **arguments)
    assert path.read_bytes() == original


@pytest.mark.parametrize("accept_v3", [True, False])
@pytest.mark.parametrize("fault", [None, "other-member", "missing-finding", "extra-finding"])
def test_caddy_native_policy_projection_preserves_every_other_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, accept_v3: bool, fault: str | None
) -> None:
    import copy

    native = _caddy_D_report()
    projected = copy.deepcopy(native)
    if accept_v3:
        del projected["Results"][1]["Vulnerabilities"]
    if fault == "other-member":
        projected["Results"][0]["Packages"][0]["Version"] = "wrong"
    elif fault == "missing-finding":
        projected["Results"][1]["Vulnerabilities"] = []
        if accept_v3:
            projected["Results"][0]["Vulnerabilities"] = []
    elif fault == "extra-finding":
        projected["Results"][0]["Vulnerabilities"] = [{"VulnerabilityID": "unexpected"}]
    original, output = tmp_path / "raw.json", tmp_path / "converted.json"
    original.write_text(json.dumps(native))
    output.write_text(json.dumps(projected))
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(
            args, 0, stdout="sha256:" + "a" * 64 + "\n", stderr=""
        ),
    )
    if fault is None:
        runtime_surface.validate_caddy_policy_projection(
            native["ArtifactName"], original, output, accept_v3=accept_v3
        )
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_policy_projection(
                native["ArtifactName"], original, output, accept_v3=accept_v3
            )


def test_caddy_private_environment_response_uses_literal_native_placeholders() -> None:
    config = json.loads(runtime_surface.CADDY_D_CONFIG)
    assert config == {
        "admin": {"disabled": True, "config": {"persist": False}},
        "apps": {
            "http": {
                "servers": {
                    "ci": {
                        "listen": ["127.0.0.1:18080"],
                        "automatic_https": {"disable": True},
                        "routes": [
                            {
                                "handle": [
                                    {
                                        "handler": "static_response",
                                        "body": "pulseplate-caddy-D\nHOME={env.HOME}\nTMPDIR={env.TMPDIR}\n",
                                    }
                                ]
                            }
                        ],
                    }
                }
            }
        },
    }


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "response",
        "config",
        "process",
        "admin",
        "udp",
        "mount",
        "image",
        "restart",
        "cap-add-shorthand",
        "cap-add-empty",
        "cap-add-duplicate",
        "cap-add-extra",
        "cap-drop-missing",
        "cap-drop-specific",
        "diagnostic-main-stdout",
        "diagnostic-main-stderr",
        "diagnostic-cleanup-stdout",
        "diagnostic-cleanup-stderr",
        "diagnostic-both-stdout",
        "diagnostic-primary-main-stdout",
        "diagnostic-primary-cleanup-stdout",
        "diagnostic-cleanup-owner-stdout",
        "diagnostic-primary-cleanup-owner-stdout",
        "tmpfs-missing",
        "tmpfs-extra",
        "tmpfs-options",
        "bind-type",
        "bind-source",
        "extra-mount",
        "tmpfs-uid",
        "tmpfs-gid",
        "tmpfs-mode",
        "env-home-wrong",
        "env-home-missing",
        "env-home-duplicate",
        "env-tmpdir-wrong",
        "env-tmpdir-missing",
        "env-tmpdir-duplicate",
        "env-not-list",
        "process-home-wrong",
        "process-home-missing",
        "process-home-duplicate",
        "process-tmpdir-wrong",
        "process-tmpdir-missing",
        "process-tmpdir-duplicate",
        "response-unterminated",
        "directory-uid",
        "directory-gid",
        "directory-mode",
        "directory-type",
        "env-unknown",
        "env-malformed",
        "env-newline",
        "env-cr",
        "env-nul",
        "env-unicode",
        "pre-id",
        "pre-image",
        "pre-path",
        "pre-args",
        "pre-restart",
        "pre-status",
        "pre-running",
        "pre-tty",
        "pre-hostname",
        "pre-workdir",
        "post-env-unknown",
        "main-id",
        "main-tty",
        "main-pid-zero",
        "main-pid-bool",
        "main-start-empty",
        "main-start-zero",
        "response-extra",
        "response-malformed",
        "response-duplicate",
        "response-prefix",
        "response-stderr-only",
        "response-crlf",
        "response-cr",
        "response-nul",
        "response-unicode",
        "log-stdout-size",
        "log-stderr-size",
        "logs-command",
        "stat-command",
        "final-id",
        "final-image",
        "final-path",
        "final-args",
        "final-tty",
        "final-restart",
        "final-pid",
        "final-start",
        "final-running",
        "final-restarting",
        "final-oom",
        "final-missing-pid",
        "final-missing-state",
        "final-env-unknown",
        "diagnostic-stat-main-stdout",
        "diagnostic-final-main-stdout",
        "diagnostic-stat-cleanup-owner-main",
        "cleanup-command",
        "diagnostic-primary-cleanup-command",
        "response-marker-missing",
        "response-invalid-utf8",
        "config-hardcoded",
        "config-admin",
        "config-crlf",
        "argv-cr",
        "stat-crlf",
        "native-create",
        "native-preinspect",
        "native-start",
        "native-readiness",
        "native-config",
        "native-cmdline",
        "native-tcp",
        "native-tcp6",
        "native-udp",
        "native-udp6",
        "native-main-inspect",
        "native-cleanup-inspect",
    ],
)
def test_caddy_actual_loaded_runtime_requires_complete_native_boundary_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    image = "sha256:" + "a" * 64
    container_id = "b" * 64
    sentinel = "synthetic-private-observation-sentinel"
    synthetic_environment = [
        "HOME=/run/pulseplate-caddy-tmp",
        "TMPDIR=/run/pulseplate-caddy-tmp",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CADDY_VERSION=v2.11.4",
        "XDG_CONFIG_HOME=/config",
        "XDG_DATA_HOME=/data",
    ]
    property_lines = synthetic_environment[:2]
    expected_response = "pulseplate-caddy-D\n" + "\n".join(property_lines) + "\n"
    native_stdout = "unrelated native output\nGOTRACEBACK=none\n" + sentinel
    calls: list[list[str]] = []
    selected: dict[str, object] = {}
    inspect_outputs: list[tuple[str, str]] = []

    def docker(
        args: list[str], *, preserve_newlines: bool = False
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        private_capture = args[0] == "logs" or (
            args[0] == "exec"
            and (args[3] in ("sh", "stat") or args[-1] in ("/ci.json", "/proc/1/cmdline"))
        )
        assert preserve_newlines is private_capture
        stdout, stderr = "", "inspection-diagnostic\n"
        if args[0] == "create":
            selected.clear()
            selected.update(name=args[args.index("--name") + 1], count=0, started=False)
            assert args[-3:] == ["run", "--config", "/ci.json"]
            assert "--environ" not in args
            if fault == "native-create":
                raise RuntimeError("synthetic native command failed")
            assert args[args.index("--entrypoint") + 1] == "/usr/bin/caddy"
        elif args[0] == "start":
            if fault == "native-start":
                raise RuntimeError("synthetic native command failed")
            selected["started"] = True
        elif args[0] == "inspect":
            selected["count"] += 1
            phase = (
                "prepared"
                if selected["count"] == 1
                else (
                    "cleanup"
                    if not selected["started"]
                    or selected["count"] > 2
                    or selected.get("early_stop")
                    else "main"
                )
            )
            if (
                (fault == "native-preinspect" and phase == "prepared")
                or (fault == "native-main-inspect" and phase == "main")
                or (fault == "native-cleanup-inspect" and phase == "cleanup")
            ):
                raise RuntimeError("synthetic native command failed")
            observed = {
                "Id": container_id,
                "Image": image,
                "Path": "/usr/bin/caddy",
                "Args": ["run", "--config", "/ci.json"],
                "RestartCount": 0,
                "Config": {
                    "User": "65532:65532",
                    "Env": synthetic_environment.copy(),
                    "Labels": {"pulseplate.caddy-D": selected["name"]},
                    "Tty": False,
                    "Hostname": container_id[:12],
                    "WorkingDir": "/srv",
                },
                "State": {
                    "Status": "running" if selected["started"] else "created",
                    "Running": bool(selected["started"]),
                    "Restarting": False,
                    "OOMKilled": False,
                    "Pid": 4242 if selected["started"] else 0,
                    "StartedAt": (
                        "2026-10-29T12:41:08.605741313Z"
                        if selected["started"]
                        else "0001-01-01T00:00:00Z"
                    ),
                },
                "HostConfig": {
                    "NetworkMode": "none",
                    "ReadonlyRootfs": True,
                    "PortBindings": {},
                    "Privileged": False,
                    "CapAdd": ["CAP_NET_BIND_SERVICE"],
                    "CapDrop": ["ALL"],
                    "Tmpfs": {
                        "/run/pulseplate-caddy-tmp": "size=8m,uid=65532,gid=65532,mode=0700",
                        "/data": "size=8m,uid=65532,gid=65532,mode=0700",
                        "/config": "size=8m,uid=65532,gid=65532,mode=0700",
                    },
                },
                "Mounts": [
                    {
                        "Type": "bind",
                        "Destination": "/ci.json",
                        "Source": str(current_directory / "loaded-ci-config.json"),
                        "RW": False,
                    }
                ],
            }
            if fault is not None and fault.startswith("env-"):
                values = observed["Config"]["Env"]
                if fault == "env-not-list":
                    observed["Config"]["Env"] = None
                elif fault in ("env-unknown", "env-malformed"):
                    values.append(("UNKNOWN=" if fault == "env-unknown" else "") + sentinel)
                elif fault in ("env-newline", "env-cr", "env-nul", "env-unicode"):
                    control = {
                        "env-newline": "\n",
                        "env-cr": "\r",
                        "env-nul": "\0",
                        "env-unicode": "\u2028",
                    }[fault]
                    values[0] += control + sentinel
                else:
                    key = "HOME" if "home" in fault else "TMPDIR"
                    binding = key + "=/run/pulseplate-caddy-tmp"
                    if fault.endswith("-wrong"):
                        values[values.index(binding)] = key + "=/foreign"
                    elif fault.endswith("-missing"):
                        values.remove(binding)
                    else:
                        values.append(binding)
            if phase == "prepared" and fault is not None and fault.startswith("pre-"):
                field, value = {
                    "pre-id": ("Id", "invalid"),
                    "pre-image": ("Image", "sha256:" + "c" * 64),
                    "pre-path": ("Path", "/bin/sh"),
                    "pre-args": ("Args", ["environ"]),
                    "pre-restart": ("RestartCount", 1),
                    "pre-status": ("Status", "running"),
                    "pre-running": ("Running", True),
                    "pre-tty": ("Tty", True),
                    "pre-hostname": ("Hostname", "foreign"),
                    "pre-workdir": ("WorkingDir", "/foreign"),
                }[fault]
                target = (
                    observed["State"]
                    if field in ("Status", "Running")
                    else (
                        observed["Config"]
                        if field in ("Tty", "Hostname", "WorkingDir")
                        else observed
                    )
                )
                target[field] = value
            if phase == "main":
                if fault == "image":
                    observed["Image"] = "wrong"
                if fault == "restart":
                    observed["State"]["Restarting"] = True
                if fault is not None and fault.startswith("cap-add-"):
                    observed["HostConfig"]["CapAdd"] = {
                        "cap-add-shorthand": ["NET_BIND_SERVICE"],
                        "cap-add-empty": [],
                        "cap-add-duplicate": ["CAP_NET_BIND_SERVICE", "CAP_NET_BIND_SERVICE"],
                        "cap-add-extra": ["CAP_NET_BIND_SERVICE", "CAP_SYS_ADMIN"],
                    }[fault]
                if fault in ("cap-drop-missing", "cap-drop-specific"):
                    observed["HostConfig"]["CapDrop"] = (
                        [] if fault == "cap-drop-missing" else ["CAP_CHOWN"]
                    )
                if fault is not None and fault.startswith("diagnostic-primary-"):
                    observed["HostConfig"]["CapAdd"] = ["CAP_SYS_ADMIN"]
                if fault in ("tmpfs-missing", "tmpfs-extra", "tmpfs-options"):
                    observed["HostConfig"]["Tmpfs"] = {
                        "tmpfs-missing": {},
                        "tmpfs-extra": {"/foreign": "size=8m"},
                        "tmpfs-options": {"/run/pulseplate-caddy-tmp": "wrong-options"},
                    }[fault]
                if fault in ("tmpfs-uid", "tmpfs-gid", "tmpfs-mode"):
                    key, value = {
                        "tmpfs-uid": ("uid=65532", "uid=0"),
                        "tmpfs-gid": ("gid=65532", "gid=0"),
                        "tmpfs-mode": ("mode=0700", "mode=1777"),
                    }[fault]
                    original = observed["HostConfig"]["Tmpfs"]["/run/pulseplate-caddy-tmp"]
                    observed["HostConfig"]["Tmpfs"]["/run/pulseplate-caddy-tmp"] = original.replace(
                        key, value
                    )
                if fault == "mount":
                    observed["Mounts"][0]["RW"] = True
                if fault == "bind-type":
                    observed["Mounts"][0]["Type"] = "volume"
                if fault == "bind-source":
                    observed["Mounts"][0]["Source"] = "/foreign"
                if fault == "extra-mount":
                    observed["Mounts"].append({"Destination": "/foreign", "Type": "bind"})
                if fault in (
                    "main-id",
                    "main-tty",
                    "main-pid-zero",
                    "main-pid-bool",
                    "main-start-empty",
                    "main-start-zero",
                ):
                    if fault == "main-id":
                        observed["Id"] = "c" * 64
                    elif fault == "main-tty":
                        observed["Config"]["Tty"] = True
                    elif "pid" in fault:
                        observed["State"]["Pid"] = 0 if fault == "main-pid-zero" else True
                    else:
                        observed["State"]["StartedAt"] = (
                            "" if fault == "main-start-empty" else "0001-01-01T00:00:00Z"
                        )
            if fault == "post-env-unknown" and phase != "prepared":
                observed["Config"]["Env"].append("UNKNOWN=" + sentinel)
            if phase == "cleanup":
                if fault is not None and "cleanup-owner" in fault:
                    observed["Config"]["Labels"]["pulseplate.caddy-D"] = "foreign-container"
                if fault in ("final-id", "diagnostic-final-main-stdout"):
                    observed["Id"] = "c" * 64
                if fault == "final-image":
                    observed["Image"] = "sha256:" + "c" * 64
                if fault == "final-path":
                    observed["Path"] = "/bin/sh"
                if fault == "final-args":
                    observed["Args"] = ["run", "--resume"]
                if fault == "final-tty":
                    observed["Config"]["Tty"] = True
                if fault == "final-restart":
                    observed["RestartCount"] = 1
                if fault in (
                    "final-pid",
                    "final-start",
                    "final-running",
                    "final-restarting",
                    "final-oom",
                ):
                    field, value = {
                        "final-pid": ("Pid", 4243),
                        "final-start": ("StartedAt", "2026-10-29T12:41:09.605741313Z"),
                        "final-running": ("Running", False),
                        "final-restarting": ("Restarting", True),
                        "final-oom": ("OOMKilled", True),
                    }[fault]
                    observed["State"][field] = value
                if fault == "final-missing-pid":
                    observed["State"].pop("Pid")
                if fault == "final-missing-state":
                    observed.pop("State")
                if fault == "final-env-unknown":
                    observed["Config"]["Env"].append("UNKNOWN=" + sentinel)
            stdout = json.dumps([observed])
            inspect_outputs.append((phase, stdout))
        elif args[0] == "exec":
            assert args[-1] != "/proc/1/environ", "the unsupported cross-process read must be gone"
            native_failure_target = {
                "native-readiness": "sh",
                "native-config": "/ci.json",
                "native-cmdline": "/proc/1/cmdline",
                "native-tcp": "/proc/net/tcp",
                "native-tcp6": "/proc/net/tcp6",
                "native-udp": "/proc/net/udp",
                "native-udp6": "/proc/net/udp6",
            }.get(fault)
            if native_failure_target in (args[3], args[-1]):
                selected["early_stop"] = True
                raise RuntimeError("synthetic native command failed")
            if args[3] == "sh":
                if fault == "response-invalid-utf8":
                    selected["early_stop"] = True
                    raise RuntimeError("Docker output is not valid UTF-8")
                values = property_lines.copy()
                if fault is not None and fault.startswith("process-"):
                    key = "HOME" if "home" in fault else "TMPDIR"
                    binding = key + "=/run/pulseplate-caddy-tmp"
                    if fault.endswith("-wrong"):
                        values[values.index(binding)] = key + "=" + sentinel
                    elif fault.endswith("-missing"):
                        values.remove(binding)
                    else:
                        values.append(binding)
                stdout = "pulseplate-caddy-D\n" + "\n".join(values) + "\n"
                if fault == "response":
                    stdout = "wrong"
                if fault == "response-extra":
                    stdout += "UNKNOWN=" + sentinel + "\n"
                if fault == "response-malformed":
                    stdout = stdout.replace("HOME=", "HOME:", 1)
                if fault == "response-marker-missing":
                    stdout = stdout.removeprefix("pulseplate-caddy-D\n")
                if fault == "response-unterminated":
                    stdout = stdout[:-1]
                if fault == "response-duplicate":
                    stdout += stdout
                if fault == "response-prefix":
                    stdout = sentinel + "\n" + stdout
                if fault == "response-stderr-only":
                    stderr, stdout = stdout, ""
                if fault == "response-crlf":
                    stdout = stdout.replace("\n", "\r\n")
                if fault == "response-cr":
                    stdout = stdout.replace("HOME=", "HOME=\r", 1)
                if fault == "response-nul":
                    stdout = stdout.replace("HOME=", "HOME=\0", 1)
                if fault == "response-unicode":
                    stdout = stdout.replace("HOME=", "HOME=\u2028", 1)
                selected["last_response"] = stdout
                selected["early_stop"] = stdout != expected_response
            elif args[3] == "stat":
                if fault == "stat-command":
                    raise RuntimeError("synthetic stat command failed")
                stdout = {
                    "directory-uid": "0:65532:700:directory\n",
                    "directory-gid": "65532:0:700:directory\n",
                    "directory-mode": "65532:65532:777:directory\n",
                    "directory-type": "65532:65532:700:symbolic link\n",
                    "stat-crlf": "65532:65532:700:directory\r\n",
                    "diagnostic-stat-main-stdout": "65532:65532:777:directory\n",
                    "diagnostic-stat-cleanup-owner-main": "65532:65532:777:directory\n",
                }.get(fault, "65532:65532:700:directory\n")
            elif args[-1] == "/ci.json":
                stdout = "{}" if fault == "config" else runtime_surface.CADDY_D_CONFIG.decode()
                if fault == "config-hardcoded":
                    stdout = stdout.replace("{env.HOME}", "/run/pulseplate-caddy-tmp").replace(
                        "{env.TMPDIR}", "/run/pulseplate-caddy-tmp"
                    )
                if fault == "config-admin":
                    stdout = stdout.replace('"disabled":true', '"disabled":false', 1)
                if fault == "config-crlf":
                    stdout = stdout.replace("\n", "\r\n")
                selected["early_stop"] = stdout.encode() != runtime_surface.CADDY_D_CONFIG
            elif args[-1] == "/proc/1/cmdline":
                stdout = (
                    "wrong"
                    if fault == "process"
                    else "/usr/bin/caddy\x00run\x00--config\x00/ci.json\x00"
                )
                if fault == "argv-cr":
                    stdout = stdout.replace("run", "run\r", 1)
                if fault in ("process", "argv-cr"):
                    selected["early_stop"] = True
            else:
                assert args[-1] in ["/proc/net/" + kind for kind in ("tcp", "tcp6", "udp", "udp6")]
                stdout = "header\n"
                if args[-1] == "/proc/net/tcp":
                    stdout += "0: 0100007F:46A0 00000000:0000 0A\n"
                    if fault == "admin":
                        stdout += "1: 0100007F:07E3 00000000:0000 0A\n"
                        selected["early_stop"] = True
                if args[-1] == "/proc/net/udp" and fault == "udp":
                    stdout += "0: 0100007F:1234 00000000:0000 07\n"
                    selected["early_stop"] = True
        elif args[0] == "logs":
            if fault == "logs-command":
                raise RuntimeError("synthetic logs command failed")
            stdout, stderr = native_stdout, sentinel
            if fault == "log-stdout-size":
                stdout = "x" * 65537
            if fault == "log-stderr-size":
                stderr = "x" * 65537
        elif args[0] == "rm":
            if fault in ("cleanup-command", "diagnostic-primary-cleanup-command"):
                raise RuntimeError("synthetic cleanup command failed")
        else:
            raise AssertionError("unexpected Docker command")
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(runtime_surface, "_run_docker", docker)
    requested_fault, fault = fault, None
    current_directory = tmp_path / "valid-baseline"
    current_directory.mkdir()
    baseline = runtime_surface.observe_caddy_ci_runtime(image, current_directory)
    assert baseline["response"] == expected_response
    assert baseline["inspected"]["HostConfig"]["CapAdd"] == ["CAP_NET_BIND_SERVICE"]
    assert baseline["private_temporary_directory"] == "65532:65532:700:directory\n"
    assert baseline["private_temporary_environment"] == synthetic_environment[:2]
    assert baseline["startup_stdout_sha256"] == hashlib.sha256(native_stdout.encode()).hexdigest()
    assert baseline["startup_stderr_sha256"] == hashlib.sha256(sentinel.encode()).hexdigest()
    assert "startup_stderr" not in baseline
    assert "startup_stdout" not in baseline
    assert "process_environment_sha256" not in baseline
    assert sentinel not in json.dumps(baseline)
    assert calls[-1] == ["rm", "--force", selected["name"]]
    fault = requested_fault
    calls.clear()
    inspect_outputs.clear()
    current_directory = tmp_path / "case"
    current_directory.mkdir()
    capture_obstructions = {
        "diagnostic-main-stdout": {"container-inspect.stdout"},
        "diagnostic-main-stderr": {"container-inspect.stderr"},
        "diagnostic-cleanup-stdout": {"cleanup-inspect.stdout"},
        "diagnostic-cleanup-stderr": {"cleanup-inspect.stderr"},
        "diagnostic-both-stdout": {"container-inspect.stdout", "cleanup-inspect.stdout"},
        "diagnostic-primary-main-stdout": {"container-inspect.stdout"},
        "diagnostic-primary-cleanup-stdout": {"cleanup-inspect.stdout"},
        "diagnostic-cleanup-owner-stdout": {"cleanup-inspect.stdout"},
        "diagnostic-primary-cleanup-owner-stdout": {"cleanup-inspect.stdout"},
        "diagnostic-stat-main-stdout": {"container-inspect.stdout"},
        "diagnostic-final-main-stdout": {"container-inspect.stdout"},
        "diagnostic-stat-cleanup-owner-main": {"container-inspect.stdout"},
    }.get(fault, set())
    for filename in capture_obstructions:
        (current_directory / filename).mkdir()
    if fault is None:
        result = runtime_surface.observe_caddy_ci_runtime(image, current_directory)
        assert result["response"] == expected_response
    else:
        error_type: type[Exception] = ValueError
        if fault.startswith("native-"):
            error_type, message = RuntimeError, "synthetic native command failed"
        elif fault == "response-invalid-utf8":
            error_type, message = RuntimeError, "Docker output is not valid UTF-8"
        elif fault.startswith("env-") or fault.startswith("pre-"):
            message = "Caddy pre-start synthetic environment binding differs"
        elif fault == "post-env-unknown":
            message = "Caddy synthetic environment changed after startup"
        elif fault == "final-env-unknown":
            message = "Caddy synthetic inspection not retained"
        elif (
            fault.startswith("diagnostic-primary-")
            or fault.startswith("cap-")
            or fault.startswith("main-")
            or fault in ("image", "restart")
        ):
            message = "Caddy native isolation/state differs"
        elif (
            fault.startswith("diagnostic-stat-")
            or fault.startswith("directory-")
            or fault == "stat-crlf"
        ):
            message = "Caddy private temporary directory owner/mode differs"
        elif fault in ("final-missing-pid", "final-missing-state"):
            error_type = KeyError
            message = "Pid" if fault == "final-missing-pid" else "State"
        elif fault.startswith("final-") or fault == "diagnostic-final-main-stdout":
            message = "Caddy final process identity differs"
        elif "cleanup-owner" in fault:
            message = "Caddy cleanup ownership differs"
        elif capture_obstructions:
            error_type, message = FileExistsError, "File exists"
        elif fault in ("logs-command", "stat-command", "cleanup-command"):
            error_type, message = (
                RuntimeError,
                "synthetic " + fault.split("-")[0] + " command failed",
            )
        elif fault.startswith(("process-", "response-")):
            message = "Caddy loaded configuration/private environment response differs"
        elif fault.startswith("log-"):
            message = "Caddy native log output exceeds retained bound"
        elif fault.startswith("config-") or fault == "argv-cr":
            message = "Caddy actual process/config binding differs"
        elif fault.startswith("tmpfs-"):
            message = "Caddy native tmpfs configuration differs"
        else:
            message = {
                "response": "Caddy loaded configuration/private environment response differs",
                "config": "Caddy actual process/config binding differs",
                "process": "Caddy actual process/config binding differs",
                "admin": "Caddy native listener/admin boundary differs",
                "udp": "Caddy native listener/admin boundary differs",
                "mount": "Caddy immutable configuration mount differs",
                "bind-type": "Caddy immutable configuration mount differs",
                "bind-source": "Caddy immutable configuration mount differs",
                "extra-mount": "Caddy immutable configuration mount differs",
            }[fault]
        with pytest.raises(error_type, match=message) as caught:
            runtime_surface.observe_caddy_ci_runtime(image, current_directory)
        rendered = "".join(traceback.format_exception(caught.value))
        assert sentinel not in rendered
        notes = getattr(caught.value, "__notes__", [])
        expected_phase = {
            "native-create": "create",
            "native-preinspect": "pre-start-inspect",
            "native-start": "start",
            "native-readiness": "readiness-private-environment",
            "native-config": "config-readback",
            "native-cmdline": "process-command",
            "native-tcp": "sockets-tcp",
            "native-tcp6": "sockets-tcp6",
            "native-udp": "sockets-udp",
            "native-udp6": "sockets-udp6",
            "native-main-inspect": "runtime-inspect",
            "native-cleanup-inspect": "cleanup",
            "logs-command": "native-log-bounds",
            "stat-command": "private-directory",
            "cleanup-command": "cleanup",
            "response-invalid-utf8": "readiness-private-environment",
        }.get(fault)
        if expected_phase is not None:
            assert "Caddy runtime phase: " + expected_phase in notes
        if fault == "native-cmdline":
            raw = runtime_surface.CADDY_D_CONFIG
            assert (
                "Caddy config.stdout utf8_bytes="
                + str(len(raw))
                + " sha256="
                + hashlib.sha256(raw).hexdigest()
                in notes
            )
            assert not any(note.startswith("Caddy command.stdout ") for note in notes)
        if fault in (
            "native-readiness",
            "native-config",
            "native-main-inspect",
            "logs-command",
            "stat-command",
        ):
            assert not any(" utf8_bytes=" in note for note in notes)
        if fault in (
            "process-home-wrong",
            "process-tmpdir-wrong",
            "response-prefix",
            "response-extra",
        ):
            raw = selected["last_response"].encode()
            assert "Caddy runtime phase: readiness-private-environment" in notes
            assert (
                "Caddy response.stdout utf8_bytes="
                + str(len(raw))
                + " sha256="
                + hashlib.sha256(raw).hexdigest()
                in notes
            )
        if fault in ("config-hardcoded", "config-admin", "config-crlf"):
            assert "Caddy config_equal=False command_equal=True" in notes
        if fault == "argv-cr":
            assert "Caddy config_equal=True command_equal=False" in notes
        if fault in ("log-stdout-size", "log-stderr-size"):
            channel = "stdout" if fault == "log-stdout-size" else "stderr"
            assert "Caddy runtime phase: native-log-bounds" in notes
            assert (
                "Caddy logs."
                + channel
                + " utf8_bytes=65537 sha256="
                + hashlib.sha256(b"x" * 65537).hexdigest()
                in notes
            )
        for filename in capture_obstructions:
            assert (
                "Caddy diagnostic write failed (" + filename + "): FileExistsError"
                in caught.value.__notes__
            )
        if fault in (
            "diagnostic-primary-cleanup-owner-stdout",
            "diagnostic-stat-cleanup-owner-main",
        ):
            assert "Caddy cleanup also failed: ValueError" in caught.value.__notes__
        if fault == "diagnostic-primary-cleanup-command":
            assert "Caddy cleanup also failed: RuntimeError" in caught.value.__notes__
    if fault == "native-create":
        assert inspect_outputs == []
    else:
        if fault != "native-preinspect":
            assert inspect_outputs[0][0] == "prepared"
        if fault != "native-cleanup-inspect":
            assert inspect_outputs[-1][0] == "cleanup"
    for phase, output in inspect_outputs:
        if phase == "prepared":
            continue
        prefix = "container-inspect" if phase == "main" else "cleanup-inspect"
        safe = json.loads(output)[0]["Config"]["Env"] == synthetic_environment
        for channel, expected in (("stdout", output), ("stderr", "inspection-diagnostic\n")):
            filename = prefix + "." + channel
            path = current_directory / filename
            if filename in capture_obstructions:
                assert path.is_dir()
            elif safe:
                assert path.read_text() == expected
            else:
                assert not path.exists()
    for directory in (tmp_path / "valid-baseline", current_directory):
        assert not (directory / "startup.stdout").exists()
        for path in directory.iterdir():
            if path.is_file():
                assert sentinel not in path.read_text()
    if fault is not None and (fault.startswith("env-") or fault.startswith("pre-")):
        assert not any(args[0] in ("start", "logs") for args in calls)
    if fault == "native-create":
        assert calls[-1][0] == "create"
        assert not any(args[0] == "rm" for args in calls)
    elif fault == "native-cleanup-inspect" or (fault is not None and "cleanup-owner" in fault):
        assert calls[-1] == ["inspect", selected["name"]]
        assert ["rm", "--force", selected["name"]] not in calls
    else:
        assert calls[-1] == ["rm", "--force", selected["name"]]
    assert "--network" in calls[0] and "none" in calls[0]
    assert "/run/pulseplate-caddy-tmp:size=8m,uid=65532,gid=65532,mode=0700" in calls[0]
    assert "HOME=/run/pulseplate-caddy-tmp" in calls[0]
    assert "TMPDIR=/run/pulseplate-caddy-tmp" in calls[0]


@pytest.mark.parametrize(
    "fault",
    [None, "missing-owner", "missing-recipe", "extra-owner", "duplicate", "symlink", "directory"],
)
def test_caddy_reuse_input_inventory_binds_all_caller_enumerated_files(
    tmp_path: Path, fault: str | None
) -> None:
    paths = [
        "frontend/Dockerfile.caddy-spa",
        "frontend/package-lock.json",
        "frontend/.dockerignore",
        "frontend/src/main.tsx",
        ".github/workflows/frontend-ci.yml",
        "deploy/Caddyfile",
        "deploy/Caddyfile.production",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "trivy/ignore-policy-caddy-go-jose-v3.rego",
        "trivy/ignore-policy.rego",
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("material\n")
    if fault == "missing-owner":
        paths.remove("trivy/ignore-policy-caddy-go-jose-v3.rego")
    elif fault == "missing-recipe":
        paths.remove("frontend/Dockerfile.caddy-spa")
    elif fault == "extra-owner":
        paths.append("other/foreign.py")
    elif fault == "duplicate":
        paths.append(paths[0])
    elif fault in ("symlink", "directory"):
        target = tmp_path / paths[0]
        target.unlink()
        if fault == "symlink":
            target.symlink_to(tmp_path / paths[1])
        else:
            target.mkdir()
    if fault is None:
        first = runtime_surface.caddy_ci_source_inventory(tmp_path, paths)
        assert set(first) == set(paths)
        (tmp_path / "frontend/src/main.tsx").write_text("changed\n")
        assert first != runtime_surface.caddy_ci_source_inventory(tmp_path, paths)
    else:
        with pytest.raises(ValueError):
            runtime_surface.caddy_ci_source_inventory(tmp_path, paths)
