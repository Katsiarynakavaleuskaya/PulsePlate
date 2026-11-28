from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any
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


# Exact public original/patched tree listings from the qualified source carrier.
# Other fixture projections are deliberately small, synthetic test evidence,
# never a substitute for execution of the actual producer.
_CADDY_ORIGINAL_LISTING = (
    b"02a6f9e68de0e988d9d1ec025ee88f9762c632363f8cf6923813a1337e3366aa  ./enco"
    b"ding.go\n0a214aff7fa3efb30b5b64f6165d25ee686d081b48c2adffdd0acb06da413e85"
    b"  ./jwt/builder.go\n0a3842b88d6007dee4259f87a64607ea348e651c0ba66f0f28e27"
    b"3fd424f2866  ./json/scanner.go\n0a999edb648b3e8ac082d4bf3a5e51d14d57881a8"
    b"3d85fc9c7803a428336b90b  ./go.sum\n0b64d2ef9370826cd2aaa348a39b59af4f4c3a"
    b"7a7df7997a0935ea330e55a395  ./json/stream.go\n0e400cc0c518ad187ef5bdcaf01"
    b"b8e233f48b09e22ca9f3cbdd345789c9b9ba9  ./jwt/jwt_test.go\n10468f9aabd1604"
    b"255cb71564047fd23e9cb1f9317e2f145c1f6f11a6de81af8  ./cipher/key_wrap.go\n"
    b"143ad295ca0f4325cf6e31dade7dd7b9d12b783729b6d4cdf270cbc6f404c3cf  ./cryp"
    b"tosigner/cryptosigner.go\n14f403591026951c84d3e11a2a328c2785d393e0372a4bb"
    b"f59a4ffff383582b5  ./cipher/ecdh_es.go\n174f0fd50efe52d28eed1cfdee3fe2469"
    b"796cbcd701f1cad8f1302755fbb438e  ./cipher/key_wrap_test.go\n197089ee2ea3e"
    b"bc03132822408e7b7e5e78b8da7105614f8ee66cfea5a4ee406  ./cipher/ecdh_es_te"
    b"st.go\n23e11f7623387ce280eef8fc6d072eed22b7c18ec885a8c0636c7f616fe54bbe  "
    b"./cryptosigner/cryptosigner_test.go\n257ee0dc596476a56a720078bcf1ada5eafe"
    b"cdb1d1442dd927d67aba86f0da88  ./opaque.go\n25fe48ba1962bd1a2fa1308de37fe1"
    b"0c0e921f7e71562a911b2f26e9e56829b4  ./README.md\n26a336cffe4ff245ccaedb39"
    b"70f6df8de397091b15c3df0af5ac0a05271ef803  ./json/testdata/code.json.gz\n2"
    b"882d3fd7bfebb18bfd0de0c76f6786d9b6e6e60d1b0395478c6648ed0be9c4a  ./jwe_t"
    b"est.go\n2b8768b473ecf66b8e2319e912a9370d433ecc01c75c33aeaaf532d6912b1fc4 "
    b" ./json/decode.go\n2e878e0eafe5d382fcf79cbb07224805b95410edc2c3bcf23f8bf3"
    b"ce93f919af  ./json/stream_test.go\n2fa51c15e906895f21a9055bab4571573a6809"
    b"1b795335a814f0d4ba87403658  ./json/tags.go\n31060827a46e11767fa0cd9f9bc8f"
    b"70a712553b177fecc0a521b54884c8733c8  ./jwt/jwt.go\n3572a4f5f4abe2efa08e85"
    b"2c42961d84a7d8b1ef4cdbe344d80b896b1ec884cb  ./.gitignore\n37a0d67f0c94887"
    b"7ecd56a6349272794d3b6ef2d8da0acc7adb5898bf7b7959f  ./json/number_test.go"
    b"\n3802ca5b8f811f72d33eb662cbbdf53d3b7aa4bcbb6b6c6ddd7695a54e3a3d40  ./sha"
    b"red.go\n3a0dcc8891aae5fededb80eeebd1b4aa693c26f70dc826ca44d5a4732586bf7e "
    b" ./json/scanner_test.go\n3c013eb9024bd574fe571cc33bc1a72ba96ed67ecddb3a42"
    b"fad0bf32eaf247ac  ./json/encode.go\n4595e9de6d2f74e3128b142a71dd2cc8675ed"
    b"cf46662cba38a438332a373b969  ./symmetric.go\n4dba0d8e1276339baa02a1e4bd04"
    b"78c37bb59a7f1a5824e487d0243d08cb434a  ./json/encode_test.go\n507fe1006b27"
    b"5a2230b291b907faceb6b26050786d6e37718cb75b903c4a89da  ./cipher/concat_kd"
    b"f_test.go\n56e9bde510f6e1e7b2cb32ce1d1bbd8fee6014d0fccbfa183fd5f3933734e4"
    b"75  ./.golangci.yml\n5a43f58e957d0c9a7f014f202d312a1d24601b0c42d078dc3915"
    b"c1b048198d9c  ./json/tagkey_test.go\n5ada1044bdb8009a237d3b1eb2aa33205748"
    b"1900e623dd07dff427877dee5594  ./symmetric_test.go\n5bdd0358dee976cb1350ea"
    b"e8b29e130019a98924b8d1a2527cbc30200b9aee6a  ./cipher/cbc_hmac.go\n5dee9c2"
    b"0054bb2d26cc0acb25599386180041c76ccda005b5bf8071cae5ba062  ./.travis.yml"
    b"\n5f80eabb79f50a108c53e972e2f89af71b04e31fe9a783343271c808e1332de7  ./jwt"
    b"/validation_test.go\n5ff43da49987e3fd676683b9bcd6b52a525b28a858a04f6dfc70"
    b"bfdb72271dbf  ./SECURITY.md\n6396d58d5ff3f9d0d5c13fd044e02979c1124cdec5e7"
    b"7f5f00321987d0a670f4  ./json/decode_test.go\n660b09b92bc545be28a5c8c9ffeb"
    b"21fef91495c4288ee856316fcb439506f61f  ./encoding_test.go\n6cc24876cea42cf"
    b"11503f87ac68456d9169d5e6fec757efaf9e4fd46bc74fb0b  ./jws.go\n6fac52914eaa"
    b"78b327cade7a9d273d08b9f69d76a5a16ae168769ba71c32d9e7  ./jwt/claims.go\n70"
    b"d2eeb241106fb449aa5ec10b2a8febd0628b27b9ec30165d11cc74a5aadbcc  ./jwt/er"
    b"rors.go\n712a24fce3600ea60af382a29a9485b9da11c4847ff9a37093df45fab6ae6976"
    b"  ./asymmetric.go\n7395f1f05012f0619395dcfc6ae7ac60e349381dc80f99ba23866e"
    b"b5cf1af11d  ./crypter.go\n74099b655f22259349f0423db89229b94fab976a87ce79d"
    b"bfc912305810f5159  ./crypter_test.go\n743f093462330cf7735eba6fa5aee42ecbb"
    b"9cada72cd4597af56489d5604c4dd  ./.github/workflows/go.yml\n795808acfd20ae"
    b"d2fb30909b3502ac75d98552b1a8826080e9ecb5d4911792ed  ./jwt/validation.go\n"
    b"7995b124e19d45cb751265c0f878bbd4c36ec1c5df893cf7091865277e068a06  ./opaq"
    b"ue_test.go\n79f510a4b97fa2e34ec37932cab57e64dfdc9fa6c314654d1ccc2dd93898a"
    b"532  ./jwk.go\n84608a8c5a5f7fde7ec993a5c3fcecc5a0c7e1781b11c651c9aecd83c4"
    b"24b20a  ./cipher/concat_kdf.go\n86a795ba34eafb4e240d34c7455f33ba4d398051b"
    b"03735e706b15e98578e96ab  ./cipher/cbc_hmac_test.go\n88d7ad7d296a07e7c8dab"
    b"39dde6f2c3bc38e126fd5352ae8b2b34a3d6fe06790  ./CHANGELOG.md\n8a138c7825a1"
    b"375edbc6cce6037b38d10bb8db7ebddc7b886e22a9460501aca3  ./go.mod\n8c5072a0d"
    b"dab5e05bf0e9ecb60695f6da78b09508e9cd8559b4db12aa1e6350b  ./json/tags_tes"
    b"t.go\n9019582c69a7c113189a092587bee1c59480880eb7d62aca5c7f7f3a52bf07fe  ."
    b"/CONTRIBUTING.md\n904beb59428b5bd472debed7bc9c799b7cffeb426fc4395ee78973b"
    b"88597f8a8  ./jwe.go\n934f594b8b60c11e0042bb8b0797b60465a51747458ccb0a2ae7"
    b"10523c61359c  ./asymmetric_test.go\n9af8857427e52d3156a15ddfb06e3f716a917"
    b"f69545f577e3c26fd0f06e0fe1b  ./jwt/doc.go\n9ca9a84359e3c263e96ce44d34ecf3"
    b"4a0d875fe37e4f88d98ac7bcd04aaf10b6  ./doc.go\na28903619096f04e818a2f2b68a"
    b"12551eb41b2c055b0560d94283b2314b2a55f  ./jwt/claims_test.go\na28c81d1fc9d"
    b"19662b03bf8beffd10a6a9650b89c20236bf1ae3f1f102278103  ./jwk_test.go\nb6d5"
    b"207cc192ac3d178fd4f02113b2bfb4dbae4bedc42bb9214321fd9ac2f9f9  ./jwt/exam"
    b"ple_test.go\nc506df0ba7f7cd747310d4aa8b2f25e069558b26a3ecc987dc93caa49797"
    b"71ae  ./signing_test.go\nc7997868ae6ced7fa7977ceb3219f19ec2610159d71e120d"
    b"c556e0288f631ffe  ./doc_test.go\nca568aaa205684c00dae8278198ba11837d98a11"
    b"47c7f36207489eb8e74187d6  ./jws_test.go\ncf6dcd3750dce8f3050bd03fc4227748"
    b"87f95b55b4180732fd8edb70c2248eb5  ./signing.go\ncfc7749b96f63bd31c3c42b5c"
    b"471bf756814053e847c10f3eb003417bc523d30  ./LICENSE\nd5d4622a4b5779d533d24"
    b"3e51ac456f10ba7b1c0c2c6f7daa4a2cadf1fc63be3  ./utils_test.go\nd8bc4201d19"
    b"cd6c93e18bd88e277ac2cdfa607f4209c743be3df35348c02b480  ./json/bench_test"
    b".go\ndd26a7abddd02e2d0aba97805b31f248ef7835d9e10da289b22e3b8ab78b324d  ./"
    b"json/LICENSE\ne5c0051f54aec2c7bacdcd3b216bc3f9c8d1a3f9c4583370e74ea9137b0"
    b"849b8  ./json/README.md\nfbd43c0566800186453a90a743bf7895baf14560a2e5ead2"
    b"40b2c70fec696638  ./jwt/builder_test.go\nfe95485e51867d61a5b6096bb8288fc6"
    b"af2ee057f700688354b04dc71d44f5de  ./json/indent.go\n"
)
_CADDY_PATCHED_LISTING = (
    b"02a6f9e68de0e988d9d1ec025ee88f9762c632363f8cf6923813a1337e3366aa  ./enco"
    b"ding.go\n04a64f7c2edfaf04c9b6d85101f86646bf07cf325939e6c1ed8eacdfa8aa5a94"
    b"  ./jwk_test.go\n083013cc521bb95c1d439bff2fd8d65f981a10c49bb789175649d7db"
    b"ec44d4fb  ./shared.go\n0a214aff7fa3efb30b5b64f6165d25ee686d081b48c2adffdd"
    b"0acb06da413e85  ./jwt/builder.go\n0a3842b88d6007dee4259f87a64607ea348e651"
    b"c0ba66f0f28e273fd424f2866  ./json/scanner.go\n0a999edb648b3e8ac082d4bf3a5"
    b"e51d14d57881a83d85fc9c7803a428336b90b  ./go.sum\n0b64d2ef9370826cd2aaa348"
    b"a39b59af4f4c3a7a7df7997a0935ea330e55a395  ./json/stream.go\n0e400cc0c518a"
    b"d187ef5bdcaf01b8e233f48b09e22ca9f3cbdd345789c9b9ba9  ./jwt/jwt_test.go\n1"
    b"0468f9aabd1604255cb71564047fd23e9cb1f9317e2f145c1f6f11a6de81af8  ./ciphe"
    b"r/key_wrap.go\n143ad295ca0f4325cf6e31dade7dd7b9d12b783729b6d4cdf270cbc6f4"
    b"04c3cf  ./cryptosigner/cryptosigner.go\n14f403591026951c84d3e11a2a328c278"
    b"5d393e0372a4bbf59a4ffff383582b5  ./cipher/ecdh_es.go\n174f0fd50efe52d28ee"
    b"d1cfdee3fe2469796cbcd701f1cad8f1302755fbb438e  ./cipher/key_wrap_test.go"
    b"\n197089ee2ea3ebc03132822408e7b7e5e78b8da7105614f8ee66cfea5a4ee406  ./cip"
    b"her/ecdh_es_test.go\n23e11f7623387ce280eef8fc6d072eed22b7c18ec885a8c0636c"
    b"7f616fe54bbe  ./cryptosigner/cryptosigner_test.go\n257ee0dc596476a56a7200"
    b"78bcf1ada5eafecdb1d1442dd927d67aba86f0da88  ./opaque.go\n25fe48ba1962bd1a"
    b"2fa1308de37fe10c0e921f7e71562a911b2f26e9e56829b4  ./README.md\n26a336cffe"
    b"4ff245ccaedb3970f6df8de397091b15c3df0af5ac0a05271ef803  ./json/testdata/"
    b"code.json.gz\n2b5aa10053904d326773992068294ccb96e93cda48fe870610965bd305a"
    b"4d5ae  ./shared_test.go\n2b8768b473ecf66b8e2319e912a9370d433ecc01c75c33ae"
    b"aaf532d6912b1fc4  ./json/decode.go\n2e878e0eafe5d382fcf79cbb07224805b9541"
    b"0edc2c3bcf23f8bf3ce93f919af  ./json/stream_test.go\n2fa51c15e906895f21a90"
    b"55bab4571573a68091b795335a814f0d4ba87403658  ./json/tags.go\n31060827a46e"
    b"11767fa0cd9f9bc8f70a712553b177fecc0a521b54884c8733c8  ./jwt/jwt.go\n3572a"
    b"4f5f4abe2efa08e852c42961d84a7d8b1ef4cdbe344d80b896b1ec884cb  ./.gitignor"
    b"e\n37a0d67f0c948877ecd56a6349272794d3b6ef2d8da0acc7adb5898bf7b7959f  ./js"
    b"on/number_test.go\n3a0dcc8891aae5fededb80eeebd1b4aa693c26f70dc826ca44d5a4"
    b"732586bf7e  ./json/scanner_test.go\n3c013eb9024bd574fe571cc33bc1a72ba96ed"
    b"67ecddb3a42fad0bf32eaf247ac  ./json/encode.go\n4595e9de6d2f74e3128b142a71"
    b"dd2cc8675edcf46662cba38a438332a373b969  ./symmetric.go\n484359608030aa495"
    b"ffbdbf4d2029087b332145820222d6a69df3628445c3445  ./jwe_test.go\n4dba0d8e1"
    b"276339baa02a1e4bd0478c37bb59a7f1a5824e487d0243d08cb434a  ./json/encode_t"
    b"est.go\n507fe1006b275a2230b291b907faceb6b26050786d6e37718cb75b903c4a89da "
    b" ./cipher/concat_kdf_test.go\n56e9bde510f6e1e7b2cb32ce1d1bbd8fee6014d0fcc"
    b"bfa183fd5f3933734e475  ./.golangci.yml\n5a43f58e957d0c9a7f014f202d312a1d2"
    b"4601b0c42d078dc3915c1b048198d9c  ./json/tagkey_test.go\n5ada1044bdb8009a2"
    b"37d3b1eb2aa332057481900e623dd07dff427877dee5594  ./symmetric_test.go\n5bd"
    b"d0358dee976cb1350eae8b29e130019a98924b8d1a2527cbc30200b9aee6a  ./cipher/"
    b"cbc_hmac.go\n5dee9c20054bb2d26cc0acb25599386180041c76ccda005b5bf8071cae5b"
    b"a062  ./.travis.yml\n5f80eabb79f50a108c53e972e2f89af71b04e31fe9a783343271"
    b"c808e1332de7  ./jwt/validation_test.go\n5ff43da49987e3fd676683b9bcd6b52a5"
    b"25b28a858a04f6dfc70bfdb72271dbf  ./SECURITY.md\n6396d58d5ff3f9d0d5c13fd04"
    b"4e02979c1124cdec5e77f5f00321987d0a670f4  ./json/decode_test.go\n63bf71b42"
    b"b40ce2cb01bedbc254a0efc4986a7b6c0908633dd83f419684cabe7  ./jwe.go\n660b09"
    b"b92bc545be28a5c8c9ffeb21fef91495c4288ee856316fcb439506f61f  ./encoding_t"
    b"est.go\n6fac52914eaa78b327cade7a9d273d08b9f69d76a5a16ae168769ba71c32d9e7 "
    b" ./jwt/claims.go\n70d2eeb241106fb449aa5ec10b2a8febd0628b27b9ec30165d11cc7"
    b"4a5aadbcc  ./jwt/errors.go\n712a24fce3600ea60af382a29a9485b9da11c4847ff9a"
    b"37093df45fab6ae6976  ./asymmetric.go\n7395f1f05012f0619395dcfc6ae7ac60e34"
    b"9381dc80f99ba23866eb5cf1af11d  ./crypter.go\n74099b655f22259349f0423db892"
    b"29b94fab976a87ce79dbfc912305810f5159  ./crypter_test.go\n743f093462330cf7"
    b"735eba6fa5aee42ecbb9cada72cd4597af56489d5604c4dd  ./.github/workflows/go"
    b".yml\n795808acfd20aed2fb30909b3502ac75d98552b1a8826080e9ecb5d4911792ed  ."
    b"/jwt/validation.go\n7995b124e19d45cb751265c0f878bbd4c36ec1c5df893cf709186"
    b"5277e068a06  ./opaque_test.go\n84608a8c5a5f7fde7ec993a5c3fcecc5a0c7e1781b"
    b"11c651c9aecd83c424b20a  ./cipher/concat_kdf.go\n86a795ba34eafb4e240d34c74"
    b"55f33ba4d398051b03735e706b15e98578e96ab  ./cipher/cbc_hmac_test.go\n88d7a"
    b"d7d296a07e7c8dab39dde6f2c3bc38e126fd5352ae8b2b34a3d6fe06790  ./CHANGELOG"
    b".md\n8a138c7825a1375edbc6cce6037b38d10bb8db7ebddc7b886e22a9460501aca3  ./"
    b"go.mod\n8c5072a0ddab5e05bf0e9ecb60695f6da78b09508e9cd8559b4db12aa1e6350b "
    b" ./json/tags_test.go\n9019582c69a7c113189a092587bee1c59480880eb7d62aca5c7"
    b"f7f3a52bf07fe  ./CONTRIBUTING.md\n934f594b8b60c11e0042bb8b0797b60465a5174"
    b"7458ccb0a2ae710523c61359c  ./asymmetric_test.go\n9af8857427e52d3156a15ddf"
    b"b06e3f716a917f69545f577e3c26fd0f06e0fe1b  ./jwt/doc.go\n9ca9a84359e3c263e"
    b"96ce44d34ecf34a0d875fe37e4f88d98ac7bcd04aaf10b6  ./doc.go\na28903619096f0"
    b"4e818a2f2b68a12551eb41b2c055b0560d94283b2314b2a55f  ./jwt/claims_test.go"
    b"\naadb058f88a8ca84edc30aeacd5a95db5739c1cdb864d65e2131e8057c65b321  ./jws"
    b"_test.go\nb6d5207cc192ac3d178fd4f02113b2bfb4dbae4bedc42bb9214321fd9ac2f9f"
    b"9  ./jwt/example_test.go\nc21536e7ea64d1be6e66f7413417623a1a38440348fa88a"
    b"444fa3b0117125c32  ./jwk.go\nc506df0ba7f7cd747310d4aa8b2f25e069558b26a3ec"
    b"c987dc93caa4979771ae  ./signing_test.go\nc7997868ae6ced7fa7977ceb3219f19e"
    b"c2610159d71e120dc556e0288f631ffe  ./doc_test.go\ncc5e5ff2616255ff591e2d28"
    b"6ea9789d185a01d297c6949bb10795bf5aee6a58  ./jws.go\ncf6dcd3750dce8f3050bd"
    b"03fc422774887f95b55b4180732fd8edb70c2248eb5  ./signing.go\ncfc7749b96f63b"
    b"d31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  ./LICENSE\nd5d4622a4b"
    b"5779d533d243e51ac456f10ba7b1c0c2c6f7daa4a2cadf1fc63be3  ./utils_test.go\n"
    b"d8bc4201d19cd6c93e18bd88e277ac2cdfa607f4209c743be3df35348c02b480  ./json"
    b"/bench_test.go\ndd26a7abddd02e2d0aba97805b31f248ef7835d9e10da289b22e3b8ab"
    b"78b324d  ./json/LICENSE\ne5c0051f54aec2c7bacdcd3b216bc3f9c8d1a3f9c4583370"
    b"e74ea9137b0849b8  ./json/README.md\nfbd43c0566800186453a90a743bf7895baf14"
    b"560a2e5ead240b2c70fec696638  ./jwt/builder_test.go\nfe95485e51867d61a5b60"
    b"96bb8288fc6af2ee057f700688354b04dc71d44f5de  ./json/indent.go\n"
)
_CADDY_FIXTURE_MODULES = (
    '[{"Path": "pulseplate.local/caddy-build", "Main": true, "Dir": "/tmp/tmp'
    '.hfKfLO", "GoMod": "/tmp/tmp.hfKfLO/go.mod", "GoVersion": "1.26.10"}, {"'
    'Path": "github.com/caddyserver/caddy/v2", "Version": "v2.11.9", "Time": '
    '"2026-06-01T19:35:02Z", "Indirect": true, "Dir": "/go/pkg/mod/github.com'
    '/caddyserver/caddy/v2@v2.11.9", "GoMod": "/go/pkg/mod/cache/download/git'
    'hub.com/caddyserver/caddy/v2/@v/v2.11.9.mod", "GoVersion": "1.25.1", "Su'
    'm": "h1:bhZtcRKQOq0fuLvEgCdPYvUxXyGn9kzjG4lh2332DTE=", "GoModSum": "h1:j'
    'ctG0eTy0tC4ST/Q7GIPKIfxox7mhSCtcwlwF82HLVM="}, {"Path": "github.com/core'
    'os/go-oidc/v3", "Version": "v3.17.0", "Time": "2025-11-21T03:32:42Z", "I'
    'ndirect": true, "Dir": "/go/pkg/mod/github.com/coreos/go-oidc/v3@v3.17.0'
    '", "GoMod": "/go/pkg/mod/cache/download/github.com/coreos/go-oidc/v3/@v/'
    'v3.17.0.mod", "GoVersion": "1.24.0", "Sum": "h1:hWBGaQfbi0iVviX4ibC7bk8O'
    'KT5qNr4klBaCHVNvehc=", "GoModSum": "h1:wqPbKFrVnE90vty060SB40FCJ8fTHTxSw'
    'yXJqZH+sI8="}, {"Path": "github.com/go-jose/go-jose/v3", "Version": "v3.'
    '0.5", "Replace": {"Path": "/opt/go-jose-v3.0.5-patched", "Dir": "/opt/go'
    '-jose-v3.0.5-patched", "GoMod": "/opt/go-jose-v3.0.5-patched/go.mod", "G'
    'oVersion": "1.12"}, "Indirect": true, "Dir": "/opt/go-jose-v3.0.5-patche'
    'd", "GoMod": "/opt/go-jose-v3.0.5-patched/go.mod", "GoVersion": "1.12"},'
    ' {"Path": "github.com/go-jose/go-jose/v4", "Version": "v4.1.6", "Time": '
    '"2026-10-14T22:46:21Z", "Indirect": true, "Dir": "/go/pkg/mod/github.com'
    '/go-jose/go-jose/v4@v4.1.6", "GoMod": "/go/pkg/mod/cache/download/github'
    '.com/go-jose/go-jose/v4/@v/v4.1.6.mod", "GoVersion": "1.24.0", "Sum": "h'
    '1:sNRkftxFJxwsILiQukqp5z83QBSmntVwmgRY7AqBDO4=", "GoModSum": "h1:x4oUasV'
    'rzR7071A4TnHLGSPpNOm2a21K9Kf04k1rs08="}, {"Path": "github.com/smallstep/'
    'certificates", "Version": "v0.30.2", "Time": "2026-03-19T11:55:22Z", "In'
    'direct": true, "Dir": "/go/pkg/mod/github.com/smallstep/certificates@v0.'
    '30.2", "GoMod": "/go/pkg/mod/cache/download/github.com/smallstep/certifi'
    'cates/@v/v0.30.2.mod", "GoVersion": "1.25.0", "Sum": "h1:1G3xBi8sJ740iA1'
    'mMPW2Svv7EIZKJ4Zf/iQtA5QlN0Y=", "GoModSum": "h1:oyaE/aEYUGDr+YiCZLAxxP22'
    'bOQqcSHTeDgp8Vv2rlY="}, {"Path": "go.step.sm/crypto", "Version": "v0.81.'
    '0", "Time": "2026-05-14T17:26:55Z", "Indirect": true, "Dir": "/go/pkg/mo'
    'd/go.step.sm/crypto@v0.81.0", "GoMod": "/go/pkg/mod/cache/download/go.st'
    'ep.sm/crypto/@v/v0.81.0.mod", "GoVersion": "1.25.1", "Sum": "h1:e+ouzpNt'
    '3Xm4dp7HGXhgYB5y4iFik3vh3phHKWmvugU=", "GoModSum": "h1:fsTizqQeASjTXnbv9'
    'O00XtRlIuXRkCdoRiJNyXGQujc="}]'
)
_CADDY_FIXTURE_IMPORTS = (
    "github.com/caddyserver/caddy/v2/cmd/caddy|/go/pkg/mod/github.com/caddyse"
    "rver/caddy/v2@v2.11.9/cmd/caddy|github.com/caddyserver/caddy/v2/modules/"
    "standard\ngithub.com/caddyserver/caddy/v2/modules/caddypki|/go/pkg/mod/gi"
    "thub.com/caddyserver/caddy/v2@v2.11.9/modules/caddypki|github.com/smalls"
    "tep/certificates/authority\ngithub.com/caddyserver/caddy/v2/modules/caddy"
    "pki/acmeserver|/go/pkg/mod/github.com/caddyserver/caddy/v2@v2.11.9/modul"
    "es/caddypki/acmeserver|github.com/caddyserver/caddy/v2/modules/caddypki "
    "github.com/smallstep/certificates/acme github.com/smallstep/certificates"
    "/authority\ngithub.com/caddyserver/caddy/v2/modules/standard|/go/pkg/mod/"
    "github.com/caddyserver/caddy/v2@v2.11.9/modules/standard|github.com/cadd"
    "yserver/caddy/v2/modules/caddypki github.com/caddyserver/caddy/v2/module"
    "s/caddypki/acmeserver\ngithub.com/coreos/go-oidc/v3/oidc|/go/pkg/mod/gith"
    "ub.com/coreos/go-oidc/v3@v3.17.0/oidc|github.com/go-jose/go-jose/v4\ngith"
    "ub.com/go-jose/go-jose/v3|/opt/go-jose-v3.0.5-patched|\ngithub.com/go-jos"
    "e/go-jose/v4|/go/pkg/mod/github.com/go-jose/go-jose/v4@v4.1.6|\ngithub.co"
    "m/smallstep/certificates/acme|/go/pkg/mod/github.com/smallstep/certifica"
    "tes@v0.30.2/acme|github.com/coreos/go-oidc/v3/oidc github.com/smallstep/"
    "certificates/authority go.step.sm/crypto/jose\ngithub.com/smallstep/certi"
    "ficates/authority|/go/pkg/mod/github.com/smallstep/certificates@v0.30.2/"
    "authority|go.step.sm/crypto/jose\ngo.step.sm/crypto/jose|/go/pkg/mod/go.s"
    "tep.sm/crypto@v0.81.0/jose|github.com/go-jose/go-jose/v3\n"
)
_CADDY_FIXTURE_BINARY = (
    b"/go/bin/caddy: go1.26.11\n\tmod\tgithub.com/caddyserver/caddy/v2\tv2.11.9\th1"
    b":bhZtcRKQOq0fuLvEgCdPYvUxXyGn9kzjG4lh2332DTE=\n\tdep\tgithub.com/coreos/go-"
    b"oidc/v3\tv3.17.0\th1:hWBGaQfbi0iVviX4ibC7bk8OKT5qNr4klBaCHVNvehc=\n\tdep\tgit"
    b"hub.com/go-jose/go-jose/v3\tv3.0.5\n\t=>\t/opt/go-jose-v3.0.5-patched\t(devel"
    b")\t\n\tdep\tgithub.com/go-jose/go-jose/v4\tv4.1.6\th1:sNRkftxFJxwsILiQukqp5z83"
    b"QBSmntVwmgRY7AqBDO4=\n\tdep\tgithub.com/smallstep/certificates\tv0.30.2\th1:1"
    b"G3xBi8sJ740iA1mMPW2Svv7EIZKJ4Zf/iQtA5QlN0Y=\n\tdep\tgo.step.sm/crypto\tv0.81"
    b".0\th1:e+ouzpNt3Xm4dp7HGXhgYB5y4iFik3vh3phHKWmvugU=\n\tbuild\t-buildmode=exe"
    b"\n\tbuild\t-compiler=gc\n\tbuild\t-trimpath=true\n\tbuild\tCGO_ENABLED=0\n\tbuild\tG"
    b"OARCH=amd64\n\tbuild\tGOOS=linux\n\tbuild\tGOAMD64=v1\n"
)


def _synthetic_stdlib_events(phase: str) -> bytes:
    """Small procedural fixture; never native execution/source proof."""
    custom = (
        {"TestPPHTTPConnectionBaseline"}
        if phase == "baseline-red"
        else (
            runtime_surface.CADDY_STDLIB_BASELINE_CUSTOM
            if phase == "baseline-controls"
            else set(runtime_surface.CADDY_STDLIB_CUSTOM_TOPS)
        )
    )
    packages = {"net/http": set(custom)}
    if phase != "baseline-red":
        packages["net/http"].update(runtime_surface.CADDY_STDLIB_UPSTREAM_TOPS)
        packages["net/http/httputil"] = {"TestReverseProxyStripHeadersPresentInConnection"}
    records = []
    for package, tops in packages.items():
        records.append({"Action": "start", "Package": package})
        for top in sorted(tops):
            records.append({"Action": "run", "Package": package, "Test": top})
            for suffix in runtime_surface.CADDY_STDLIB_CUSTOM_SUBTESTS.get(top, ()):
                name = top + "/" + suffix
                records.append({"Action": "run", "Package": package, "Test": name})
                outputs = []
                if top == "TestPPHTTPMalformedReaderControls":
                    outputs = [f"PP_READER_REJECT name={suffix} error=synthetic\n"]
                elif top == "TestPPHTTPMalformedAcceptedParity":
                    legacy = suffix == "legacy_space_field_name"
                    state = (
                        'close=false length=0 body="" error=<nil> field=["x"]'
                        if legacy
                        else 'close=true length=1 body="x" error=<nil>'
                    )
                    values = (
                        "[]"
                        if phase == "baseline-controls" or legacy
                        else (
                            '["cloſe" "\\"close\\"" "close;parameter"]'
                            if suffix == "opaque_obs_text"
                            else '["X-A"]'
                        )
                    )
                    outputs = [
                        f"PP_ACCEPTED_PARITY name={suffix} {state}\n",
                        f"PP_ACCEPTED_HEADER name={suffix} values={values}\n",
                    ]
                for output in outputs:
                    records.append(
                        {"Action": "output", "Package": package, "Test": name, "Output": output}
                    )
                records.append({"Action": "pass", "Package": package, "Test": name})
            if phase == "baseline-red":
                for output in (
                    "PP_BASELINE_SETUP_BODY_CLOSE_OK\n",
                    'PP_EXPECTED_NOMINATION_MISMATCH: got=[] want=["X-A" "X-B"]\n',
                ):
                    records.append(
                        {"Action": "output", "Package": package, "Test": top, "Output": output}
                    )
            records.append(
                {
                    "Action": "fail" if phase == "baseline-red" else "pass",
                    "Package": package,
                    "Test": top,
                }
            )
        records.append(
            {"Action": "fail" if phase == "baseline-red" else "pass", "Package": package}
        )
    return b"".join(json.dumps(row).encode() + b"\n" for row in records)


def _synthetic_stdlib_evidence(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """Exercise the real recognizer with an explicitly synthetic, tiny tree."""
    original = {
        "bin/go": runtime_surface.CADDY_GO_BINARY_SHA256,
        "src/net/http/transfer.go": runtime_surface.CADDY_STDLIB_BEFORE_SHA256,
        **runtime_surface.CADDY_STDLIB_HELPERS,
        "test/Þsample.go": "d" * 64,
    }
    baseline = {
        **original,
        "src/net/http/go_http_connection_nominations_test.go": runtime_surface.CADDY_STDLIB_FIXTURE_SHA256,
    }
    patched = {**baseline, "src/net/http/transfer.go": runtime_surface.CADDY_STDLIB_AFTER_SHA256}
    manifests = {}
    for label, entries in (("original", original), ("baseline", baseline), ("patched", patched)):
        raw = "".join(
            sorted(digest + "  ./" + path + "\n" for path, digest in entries.items())
        ).encode()
        manifests[label] = raw
        monkeypatch.setattr(
            runtime_surface,
            "CADDY_STDLIB_" + label.upper() + "_TREE",
            hashlib.sha256(raw).hexdigest(),
        )
    monkeypatch.setattr(runtime_surface, "CADDY_STDLIB_ORIGINAL_COUNT", len(original))
    data = {
        "stdlib-inputs.sha256": runtime_surface.caddy_stdlib_inputs(),
        "stdlib-test-commands.txt": runtime_surface.caddy_stdlib_commands(),
        "stdlib-original-tree.sha256": manifests["original"],
        "stdlib-original-post-build-tree.sha256": manifests["original"],
        "stdlib-baseline-tree.sha256": manifests["baseline"],
        "stdlib-patched-tree.sha256": manifests["patched"],
        "stdlib-post-tests-tree.sha256": manifests["patched"],
        "stdlib-post-build-tree.sha256": manifests["patched"],
    }
    for phase in ("baseline-red", "baseline-controls", "patched-tests"):
        data["stdlib-" + phase + ".jsonl"] = _synthetic_stdlib_events(phase)
    listing = (
        "\n".join(
            [
                *runtime_surface.CADDY_STDLIB_UPSTREAM_TOPS,
                *runtime_surface.CADDY_STDLIB_CUSTOM_TOPS,
                "TestReverseProxyStripHeadersPresentInConnection",
                "ok\tnet/http\t0.001s",
                "ok\tnet/http/httputil\t0.001s",
            ]
        )
        + "\n"
    ).encode()
    data["stdlib-test-inventory.txt"] = (
        b"BASELINE_NATIVE_LIST\n" + listing + b"PATCHED_NATIVE_LIST\n" + listing
    )
    return data


def _caddy_source_fixture(
    directory: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[bytes, str, bytes]:
    directory.mkdir()
    data = {
        "patch-tool.txt": b"git version 2.52.0\n" + b"a" * 64 + b"  /usr/bin/git\n",
        "inputs.sha256": (
            runtime_surface.CADDY_PATCH_SHA256
            + "  /opt/go-jose-v3.patch\n"
            + runtime_surface.CADDY_COMPAT_SHA256
            + "  /opt/caddy_v3_compat_test.go\n"
        ).encode(),
        "modules.json": b"\n".join(
            json.dumps(row).encode() for row in json.loads(_CADDY_FIXTURE_MODULES)
        ),
        "module-graph.txt": b"pulseplate.local/caddy-build github.com/go-jose/go-jose/v3@v3.0.5\n",
        "import-graph.txt": _CADDY_FIXTURE_IMPORTS.encode(),
        "build-module.sha256": b"a" * 64 + b"  go.mod\n" + b"b" * 64 + b"  go.sum\n",
        "build-info.txt": _CADDY_FIXTURE_BINARY,
        "binary.sha256": b"c" * 64 + b"  /go/bin/caddy\n",
    }
    for name in ("original-tree.sha256", "copied-tree.sha256", "original-post-build-tree.sha256"):
        data[name] = _CADDY_ORIGINAL_LISTING
    for name in ("patched-tree.sha256", "post-unit-tree.sha256", "post-build-tree.sha256"):
        data[name] = _CADDY_PATCHED_LISTING
    for name, count, packages in (
        (
            "jose-tests.jsonl",
            301,
            [
                "github.com/go-jose/go-jose/v3" + tail
                for tail in ("", "/cipher", "/cryptosigner", "/json", "/jwt")
            ],
        ),
        ("compat-tests.jsonl", 19, ["pulseplate.local/caddy-build/compat"]),
    ):
        records = [{"Action": "start", "Package": package} for package in packages]
        for number in range(count):
            for action in ("run", "pass"):
                records.append(
                    {
                        "Action": action,
                        "Package": packages[number % len(packages)],
                        "Test": "TestSynthetic" + str(number),
                    }
                )
        records.extend({"Action": "pass", "Package": package} for package in packages)
        data[name] = b"\n".join(json.dumps(row).encode() for row in records) + b"\n"
    data.update(_synthetic_stdlib_evidence(monkeypatch))
    graph = data["import-graph.txt"].decode().splitlines()
    graph[0] += " fmt"
    graph.append("fmt|" + runtime_surface.CADDY_STDLIB_ROOT + "/src/fmt|")
    data["import-graph.txt"] = ("\n".join(graph) + "\n").encode()
    assert set(data) == runtime_surface.CADDY_BUILD_MEMBERS
    for name, raw in data.items():
        (directory / name).write_bytes(raw)
    recipe = (Path(__file__).resolve().parents[1] / "frontend/Dockerfile.caddy-spa").read_bytes()
    return _CADDY_FIXTURE_BINARY, "c" * 64, recipe


def _caddy_source_report() -> dict:
    original = runtime_surface.CADDY_PATCHED_ROOT
    v4 = "github.com/go-jose/go-jose/v4"
    ordinary = [
        {"Name": row["Path"], "Version": row["Version"], "ID": row["Path"] + "@" + row["Version"]}
        for row in json.loads(_CADDY_FIXTURE_MODULES)
        if row["Path"] not in ("pulseplate.local/caddy-build", "github.com/go-jose/go-jose/v3", v4)
    ]
    ordinary.append({"Name": "stdlib", "Version": "v1.26.11", "ID": "stdlib@v1.26.11"})
    return {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": "sha256:" + "a" * 64,
        "Metadata": {
            "ImageID": "sha256:" + "a" * 64,
            "ImageConfig": {"architecture": "amd64", "os": "linux"},
        },
        "Results": [
            {
                "Target": "sha256:" + "a" * 64 + " (alpine 3.23.5)",
                "Class": "os-pkgs",
                "Type": "alpine",
                "Packages": [{"Name": "busybox", "ID": "busybox@1", "Version": "1"}],
            },
            {
                "Target": "usr/bin/caddy",
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [
                    {
                        "Name": original,
                        "ID": original,
                        "Identifier": {"PURL": "pkg:golang/opt/go-jose-v3.0.5-patched"},
                    },
                    *ordinary,
                    {"Name": v4, "ID": v4 + "@v4.1.6", "Version": "v4.1.6"},
                ],
            },
        ],
    }


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing",
        "extra",
        "symlink",
        "oversized",
        "tree",
        "patch",
        "test-fail",
        "test-partial",
        "test-duplicate",
        "sum",
        "replace-version",
        "replace-extra",
        "replace-path",
        "replace-mod",
        "graph-disconnected",
        "graph-duplicate",
        "graph-root",
        "binary",
        "binary-extra-replace",
        "binary-sum",
        "recipe",
    ],
)
def test_caddy_source_carrier_exact_replacement_and_independent_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    directory = tmp_path / "source"
    binary, digest, recipe = _caddy_source_fixture(directory, monkeypatch)
    if fault == "missing":
        (directory / "inputs.sha256").unlink()
    elif fault == "extra":
        (directory / "packages.json").write_text("{}")
    elif fault == "symlink":
        (directory / "inputs.sha256").unlink()
        (directory / "inputs.sha256").symlink_to(directory / "binary.sha256")
    elif fault == "oversized":
        (directory / "patch-tool.txt").write_bytes(b"x" * (2097152 + 1))
    elif fault == "tree":
        (directory / "post-build-tree.sha256").write_bytes(
            _CADDY_PATCHED_LISTING.replace(b"a", b"b", 1)
        )
    elif fault == "patch":
        (directory / "inputs.sha256").write_bytes(b"changed")
    elif fault in ("test-fail", "test-partial", "test-duplicate"):
        path = directory / "jose-tests.jsonl"
        records = [json.loads(line) for line in path.read_bytes().splitlines()]
        if fault == "test-fail":
            records[-1]["Action"] = "fail"
        elif fault == "test-partial":
            records.pop()
        else:
            records.append(records[-1])
        path.write_text("\n".join(json.dumps(row) for row in records))
    elif fault in ("sum", "replace-version", "replace-extra", "replace-path", "replace-mod"):
        rows = json.loads(_CADDY_FIXTURE_MODULES)
        row = next(row for row in rows if "Replace" in row)
        if fault == "sum":
            row["Sum"] = runtime_surface.CADDY_SOURCE_MODULES[row["Path"]][1]
        elif fault == "replace-version":
            row["Replace"]["Version"] = "v3.0.5"
        elif fault == "replace-extra":
            rows[0]["Replace"] = dict(row["Replace"])
        elif fault == "replace-path":
            row["Replace"]["Path"] += "-alias"
        else:
            row["Replace"]["GoMod"] += ".other"
        (directory / "modules.json").write_text("\n".join(json.dumps(row) for row in rows))
    elif fault in ("graph-disconnected", "graph-duplicate", "graph-root"):
        path = directory / "import-graph.txt"
        value = path.read_text()
        if fault == "graph-disconnected":
            value += "unused|/usr/local/go/src/unused|\n"
        elif fault == "graph-duplicate":
            value += value.splitlines()[0] + "\n"
        else:
            value = value.replace("/opt/go-jose-v3.0.5-patched", "/opt/other")
        path.write_text(value)
    elif fault == "binary":
        digest = "d" * 64
    elif fault == "binary-extra-replace":
        binary += b"=> /other (devel)\n"
    elif fault == "binary-sum":
        binary = binary.replace(b"v3.0.5\n", b"v3.0.5 h1:invented\n")
    elif fault == "recipe":
        recipe = recipe.replace(b"go mod verify", b"go mod tidy")
    if fault is None:
        result = runtime_surface.validate_caddy_source_evidence(
            directory, binary_metadata=binary, binary_sha256=digest, recipe=recipe
        )
        assert result["v3_scanner_comparability"] == "UNKNOWN"
        assert set(result["members"]) == runtime_surface.CADDY_BUILD_MEMBERS
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_source_evidence(
                directory, binary_metadata=binary, binary_sha256=digest, recipe=recipe
            )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "high",
        "critical",
        "secret",
        "missing-v3",
        "versioned-v3",
        "purl",
        "missing-v4",
        "malformed-version",
        "report-hash",
        "native-error",
        "platform",
        "image",
    ],
)
def test_caddy_source_report_preserves_unknown_and_rejects_unqualified_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    directory = tmp_path / "source"
    binary, digest, recipe = _caddy_source_fixture(directory, monkeypatch)
    report = _caddy_source_report()
    packages = report["Results"][1]["Packages"]
    if fault in ("high", "critical"):
        report["Results"][0]["Vulnerabilities"] = [
            {
                "VulnerabilityID": "CVE-synthetic",
                "PkgID": "busybox@1",
                "PkgName": "busybox",
                "InstalledVersion": "1",
                "Severity": fault.upper(),
                "Status": "affected",
            }
        ]
    elif fault == "secret":
        report["Results"][0]["Secrets"] = [{"RuleID": "synthetic"}]
    elif fault == "missing-v3":
        packages.pop(0)
    elif fault == "versioned-v3":
        packages[0]["Version"] = "(devel)"
    elif fault == "purl":
        packages[0]["Identifier"]["PURL"] = "wrong"
    elif fault == "missing-v4":
        packages.pop()
    elif fault == "malformed-version":
        del packages[1]["Version"]
    elif fault == "platform":
        report["Metadata"]["ImageConfig"]["architecture"] = "arm64"
    elif fault == "image":
        report["Metadata"]["ImageID"] = "sha256:" + "b" * 64
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(args, 0, "sha256:" + "a" * 64 + "\n", ""),
    )
    kwargs = {
        "binary_metadata": binary,
        "source_evidence": directory,
        "binary_sha256": digest,
        "recipe": recipe,
        "native_exit": 2 if fault == "native-error" else 0,
        "expected_report_sha256": (
            "0" * 64 if fault == "report-hash" else hashlib.sha256(path.read_bytes()).hexdigest()
        ),
    }
    original = path.read_bytes()
    if fault is None:
        decision = runtime_surface.validate_caddy_ci_report(report["ArtifactName"], path, **kwargs)
        assert decision["v3_scanner_comparability"] == "UNKNOWN"
        assert "accepted" not in decision and "review_by" not in decision
        assert decision["CD_release_accepted"] is False
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_ci_report("sha256:" + "a" * 64, path, **kwargs)
    assert path.read_bytes() == original


@pytest.mark.parametrize("fault", [None, "removed", "added", "metadata"])
def test_caddy_strict_conversion_preserves_every_native_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from copy import deepcopy

    report = _caddy_source_report()
    converted = deepcopy(report)
    if fault == "removed":
        converted["Results"][1]["Packages"].pop()
    elif fault == "added":
        converted["Results"][0]["new"] = "unexplained"
    elif fault == "metadata":
        converted["Metadata"]["ImageConfig"]["os"] = "other"
    raw, output = tmp_path / "raw.json", tmp_path / "converted.json"
    raw.write_text(json.dumps(report))
    output.write_text(json.dumps(converted))
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(args, 0, "sha256:" + "a" * 64 + "\n", ""),
    )
    if fault is None:
        runtime_surface.validate_caddy_policy_projection(report["ArtifactName"], raw, output)
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_policy_projection(report["ArtifactName"], raw, output)


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
        "order-prepared",
        "order-runtime",
        "order-cleanup",
        "order-each",
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
        "pre-label",
        "typed-pre-duplicate",
        "typed-pre-nonstring",
        "typed-pre-unhashable",
        "typed-runtime-duplicate",
        "typed-runtime-nonstring",
        "typed-runtime-unhashable",
        "typed-cleanup-duplicate",
        "typed-cleanup-nonstring",
        "typed-cleanup-unhashable",
        "typed-pre-and-cleanup",
        "typed-runtime-and-cleanup",
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
        "changed-binary",
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
    binary = b"synthetic candidate executable bytes"
    binary_hash = hashlib.sha256(binary).hexdigest()
    decision = {
        "decision": "source_CVE116587_correction_with_unsuppressed_scan",
        "image": image,
        "source": {
            "binary_sha256": binary_hash,
            "compiled_module_versions": {runtime_surface.CADDY_MODULE: "v2.11.9"},
        },
        "controls": {
            "native_controls": "observed_exact_current_epoch",
            "subjects": {
                "candidate": {"image": image, "version": "v2.11.9", "binary_sha256": binary_hash},
                "official": {"image": "sha256:" + "9" * 64, "version": "v2.11.4"},
            },
        },
    }
    sentinel = "synthetic-private-observation-sentinel"
    synthetic_environment = [
        "HOME=/run/pulseplate-caddy-tmp",
        "TMPDIR=/run/pulseplate-caddy-tmp",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CADDY_VERSION=v2.11.9",
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
        elif args[0] == "cp":
            assert args[1] == container_id + ":/usr/bin/caddy"
            Path(args[2]).write_bytes(b"changed" if fault == "changed-binary" else binary)
        elif args[0] == "start":
            assert args[1] == container_id
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
            orders = {
                "prepared": [1, 0, 2, 3, 4, 5],
                "main": [5, 4, 3, 2, 1, 0],
                "cleanup": [2, 3, 4, 5, 0, 1],
            }
            order_phase = {
                "order-prepared": "prepared",
                "order-runtime": "main",
                "order-cleanup": "cleanup",
            }.get(fault)
            if fault == "order-each" or phase == order_phase:
                observed["Config"]["Env"] = [synthetic_environment[k] for k in orders[phase]]
            typed_phase = {"pre": "prepared", "runtime": "main", "cleanup": "cleanup"}
            if fault is not None and fault.startswith("typed-"):
                _, target, kind = fault.split("-", 2)
                if phase == typed_phase[target] or kind == "and-cleanup" and phase == "cleanup":
                    values = observed["Config"]["Env"]
                    values[-1] = {"duplicate": values[0], "nonstring": False}.get(
                        kind, {"private": sentinel}
                    )
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
                    "pre-label": ("Labels", {"pulseplate.caddy-D": "foreign"}),
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
                        if field in ("Tty", "Hostname", "WorkingDir", "Labels")
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
    baseline = runtime_surface._observe_validated_caddy_runtime(decision, current_directory)
    assert all(call[1] == container_id for call in calls if call[0] in ("start", "exec", "logs"))
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
    if fault in (None, "order-prepared", "order-runtime", "order-cleanup", "order-each"):
        result = runtime_surface._observe_validated_caddy_runtime(decision, current_directory)
        assert result["response"] == expected_response
    else:
        error_type: type[Exception] = ValueError
        if fault.startswith("typed-pre-"):
            message = "Caddy pre-start synthetic environment binding differs"
        elif fault.startswith("typed-runtime-"):
            message = "Caddy synthetic environment changed after startup"
        elif fault.startswith("typed-cleanup-"):
            message = "Caddy synthetic inspection not retained"
        elif fault.startswith("native-"):
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
                "changed-binary": "Caddy pre-start binary differs",
                "mount": "Caddy immutable configuration mount differs",
                "bind-type": "Caddy immutable configuration mount differs",
                "bind-source": "Caddy immutable configuration mount differs",
                "extra-mount": "Caddy immutable configuration mount differs",
            }[fault]
        with pytest.raises(error_type, match=message) as caught:
            runtime_surface._observe_validated_caddy_runtime(decision, current_directory)
        if fault == "changed-binary":
            assert all(call[0] != "start" for call in calls)
        rendered = "".join(traceback.format_exception(caught.value))
        assert sentinel not in rendered
        notes = getattr(caught.value, "__notes__", [])
        expected_phase = {
            "native-create": "create",
            "native-preinspect": "pre-start-inspect",
            "changed-binary": "pre-start-binary",
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
    if fault is not None and fault.startswith("typed-"):
        if fault.startswith("typed-pre-"):
            assert "Caddy runtime phase: pre-start-inspect" in caught.value.__notes__
        elif fault.startswith("typed-runtime-"):
            assert "Caddy runtime phase: runtime-inspect" in caught.value.__notes__
            assert any(args[0] == "start" for args in calls)
            assert not any(args[0] == "logs" for args in calls)
        else:
            assert any(args[0] == "start" for args in calls)
            assert any(args[0] == "logs" for args in calls)
        if fault.endswith("and-cleanup") or fault.startswith("typed-cleanup-"):
            assert (
                "Caddy diagnostic write failed (cleanup-inspect): ValueError"
                in caught.value.__notes__
            )
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
        values = json.loads(output)[0]["Config"]["Env"]
        safe = (
            type(values) is list
            and len(values) == 6
            and all(type(value) is str for value in values)
            and sorted(values) == sorted(synthetic_environment)
        )
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
    if fault is not None and fault.startswith(("env-", "pre-", "typed-pre-")):
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
        "trivy/ignore-policy.rego",
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("material\n")
    if fault == "missing-owner":
        paths.remove("trivy/ignore-policy.rego")
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


@pytest.mark.parametrize(
    ("fault", "result", "diagnostic"),
    [
        (None, True, None),
        ("nonmember", False, None),
        ("nonancestor", False, None),
        ("unavailable", None, "synthetic API unavailable"),
        ("short", None, "GitHub_complete_distinct_pages"),
        ("missing-final", None, "Caddy authenticated PR commit inventory differs"),
        ("duplicate-sha", None, "Caddy authenticated PR commit inventory differs"),
        ("invalid-parent", None, "Caddy authenticated PR parent inventory differs"),
        ("wrong-base", None, "candidate_same_repository_PR"),
    ],
)
def test_caddy_skip_only_confirmed_nonmatching_producer(
    fault: str | None, result: bool | None, diagnostic: str | None
) -> None:
    from typing import Any

    from scripts.ci.prometheus_source_image import QualificationError

    final, source, other = "1" * 40, "2" * 40, "3" * 40
    branch = "codex/alertmanager-controller-transition"

    def read(endpoint: str) -> Any:
        if endpoint == "/pulls/2501":
            return {
                "number": 2501,
                "head": {"sha": final, "ref": branch, "repo": {"id": 1043311030}},
                "base": {
                    "ref": "retargeted" if fault == "wrong-base" else "main",
                    "repo": {"id": 1043311030},
                },
                "commits": 2,
            }
        assert endpoint == "/pulls/2501/commits?per_page=100&page=1"
        if fault == "unavailable":
            raise ValueError("synthetic API unavailable")
        prior = other if fault == "nonmember" else source
        if fault == "short":
            return [{"sha": final, "parents": []}]
        linked_parent = {"sha": prior}
        if fault == "invalid-parent":
            linked_parent["sha"] = "wrong"
        return [
            {"sha": prior, "parents": [], "id": 7},
            {
                "sha": (
                    {"missing-final": other, "duplicate-sha": prior}.get(fault, final)
                    if fault
                    else final
                ),
                "parents": [] if fault == "nonancestor" else [linked_parent],
                "id": 8,
            },
        ]

    if fault == "nonmember":
        assert not runtime_surface.caddy_producer_in_pr(read, 2501, source, final, branch)
        assert runtime_surface.caddy_producer_in_pr(read, 2501, other, final, branch)
    elif diagnostic is not None:
        with pytest.raises((ValueError, QualificationError), match="^" + diagnostic + "$"):
            runtime_surface.caddy_producer_in_pr(read, 2501, source, final, branch)
    else:
        assert runtime_surface.caddy_producer_in_pr(read, 2501, source, final, branch) is result


@pytest.mark.parametrize("fault", [None, "matching-retarget", "ambiguous", "invalid-merge"])
def test_caddy_push_selects_only_one_exact_merged_main_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from typing import Any

    selected, other, final = "1" * 40, "2" * 40, "3" * 40
    event = tmp_path / "event.json"
    ref = "refs/heads/main"
    event.write_text(json.dumps({"ref": ref, "after": selected}))
    for name, value in {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_REF": ref,
        "GITHUB_SHA": selected,
    }.items():
        monkeypatch.setenv(name, value)

    repo = {"id": 1043311030, "full_name": "Katsiarynakavaleuskaya/PulsePlate"}
    branches = {
        2484: "codex/cab07c-eslint-pages-features",
        2494: "codex/dependency-alertmanager-remediation",
        2495: "codex/npm-braces-build-prerequisite",
        2501: "codex/alertmanager-controller-transition",
    }

    def read(endpoint: str) -> Any:
        if endpoint.startswith("/pulls?"):
            return []
        number = int(endpoint.removeprefix("/pulls/"))
        participating = number == 2501 or (
            (fault == "matching-retarget" and number == 2484)
            or (fault == "ambiguous" and number == 2495)
        )
        return {
            "number": number,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": (
                selected if participating else "bad" if fault == "invalid-merge" else other
            ),
            "base": {"ref": "retargeted" if number == 2484 else "main", "repo": repo},
            "head": {"ref": branches[number], "sha": final, "repo": repo},
        }

    if fault is None:
        result = runtime_surface.caddy_bound_pr(read, selected)
        assert result["number"] == 2501 and result["head"]["sha"] == final
    else:
        diagnostic = {
            "matching-retarget": "^Caddy original PR identity differs$",
            "ambiguous": "^Caddy observation requires one exact accepted PR or main merge$",
            "invalid-merge": "^Caddy main merge evidence is invalid$",
        }
        with pytest.raises(ValueError, match=diagnostic[fault]):
            runtime_surface.caddy_bound_pr(read, selected)


def _caddy_control_fixture(directory: Path, *, local_layer: bool = False) -> tuple[dict, dict]:
    from copy import deepcopy

    directory.mkdir()
    candidate = _caddy_source_report()
    images = {
        name: "sha256:" + digit * 64
        for name, digit in (("candidate", "a"), ("official", "b"), ("secret", "c"))
    }
    lower = {
        "VulnerabilityID": "CVE-test-low",
        "PkgID": "busybox@1",
        "PkgName": "busybox",
        "InstalledVersion": "1",
        "Severity": "LOW",
        "Status": "affected",
    }
    candidate["Results"][0]["Vulnerabilities"] = [lower]
    official = deepcopy(candidate)
    official["ArtifactName"] = images["official"]
    official["Metadata"]["ImageID"] = images["official"]
    official["Results"][0]["Target"] = images["official"] + " (alpine 3.23.5)"
    official["Results"][1]["Packages"][0] = {
        "Name": "github.com/go-jose/go-jose/v3",
        "Version": "v3.0.5",
        "ID": "github.com/go-jose/go-jose/v3@v3.0.5",
    }
    module = runtime_surface.CADDY_MODULE
    package = next(pkg for pkg in official["Results"][1]["Packages"] if pkg["Name"] == module)
    package.update(Version="v2.11.4", ID=module + "@v2.11.4")
    official["Results"][1]["Vulnerabilities"] = [
        {
            "VulnerabilityID": "CVE-2026-116587",
            "PkgName": "github.com/go-jose/go-jose/v3",
            "PkgID": "github.com/go-jose/go-jose/v3@v3.0.5",
            "InstalledVersion": "v3.0.5",
            "Severity": "HIGH",
            "Status": "affected",
            "PkgIdentifier": {"PURL": "pkg:golang/github.com/go-jose/go-jose/v3@v3.0.5"},
        }
    ]
    child = deepcopy(candidate)
    child["ArtifactName"] = images["secret"]
    child["Metadata"]["ImageID"] = images["secret"]
    child["Results"][0]["Target"] = images["secret"] + " (alpine 3.23.5)"
    masked = "GITHUB_PAT=" + "*" * 40
    child["Results"].append(
        {
            "Target": "/credentials.txt",
            "Class": "secret",
            "Secrets": [
                {
                    "RuleID": "github-pat",
                    "Category": "GitHub",
                    "Severity": "CRITICAL",
                    "Title": "GitHub Personal Access Token",
                    "StartLine": 1,
                    "EndLine": 1,
                    "Code": {
                        "Lines": [
                            {
                                "Number": 1,
                                "Content": masked,
                                "IsCause": True,
                                "Annotation": "",
                                "Truncated": False,
                                "Highlighted": masked,
                                "FirstCause": True,
                                "LastCause": True,
                            },
                            {
                                "Number": 2,
                                "Content": "",
                                "IsCause": False,
                                "Annotation": "",
                                "Truncated": False,
                                "FirstCause": False,
                                "LastCause": False,
                            },
                        ]
                    },
                    "Match": masked,
                    "Offset": 11,
                    "Layer": {
                        "Digest": "sha256:" + "e" * 64,
                        "DiffID": "sha256:" + "d" * 64,
                        "CreatedBy": "caddy run --config /etc/caddy/Caddyfile --adapter caddyfile",
                    },
                }
            ],
        }
    )
    for subject, report, repository in (
        ("candidate", candidate, "pulseplate-caddy"),
        ("secret", child, "pulseplate-caddy-control"),
    ):
        report["ArtifactID"] = (
            "sha256:"
            + hashlib.sha256(
                (images[subject] + ":index.docker.io/library/" + repository).encode()
            ).hexdigest()
        )
        for row in report["Results"]:
            for finding in row.get("Vulnerabilities", []):
                finding["Fingerprint"] = (
                    "sha256:"
                    + hashlib.sha256(
                        ":".join(
                            (
                                report["ArtifactID"],
                                row["Target"],
                                finding["PkgID"],
                                finding["VulnerabilityID"],
                            )
                        ).encode()
                    ).hexdigest()
                )
    controls = {
        "subjects": images,
        "scans": {},
        "parent_layers": ["sha256:" + "f" * 64],
        "child_layers": ["sha256:" + "f" * 64, "sha256:" + "d" * 64],
        "filesystem_delta": ["A /credentials.txt"],
        "child_was_started": False,
        "fixture_sha256": hashlib.sha256(
            ("GITHUB_PAT=" + "ghp_" + "012345678901234567890123456789abcdef" + "\n").encode()
        ).hexdigest(),
    }
    official_binary = b"static test binary"
    metadata = (
        "go version go1.26.11 linux/amd64\n"
        "/tmp/caddy-static: go1.26.10\n"
        "mod github.com/caddyserver/caddy/v2 v2.11.4\n"
        "dep github.com/go-jose/go-jose/v3 v3.0.5 h1:BLLJWbC4nMZOfuPVxoZIxeYsn6Nl2r1fITaJ78UQlVQ=\n"
    ).encode()
    (directory / "official-caddy.binary").write_bytes(official_binary)
    (directory / "official-go-version-m.txt").write_bytes(metadata)
    controls["official_static"] = {
        "image": images["official"],
        "binary_sha256": hashlib.sha256(official_binary).hexdigest(),
        "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
    }
    if local_layer:
        controls.update(owner="synthetic", child_tag="pulseplate-caddy-control:synthetic")
        for report, tag, layers in (
            (candidate, "pulseplate-caddy:contract", controls["parent_layers"]),
            (child, controls["child_tag"], controls["child_layers"]),
        ):
            descriptors = [{"Size": 512, "DiffID": diff_id} for diff_id in layers]
            report["Metadata"].update(
                Reference=tag, RepoTags=[tag], DiffIDs=layers, Layers=descriptors
            )
            report["Metadata"]["ImageConfig"]["rootfs"] = {"type": "layers", "diff_ids": layers}
        del child["Results"][-1]["Secrets"][0]["Layer"]["Digest"]
    for subject, full in (("candidate", candidate), ("official", official), ("secret", child)):
        high = deepcopy(full)
        for row in high["Results"]:
            if "Vulnerabilities" in row:
                values = [
                    v for v in row["Vulnerabilities"] if v["Severity"] in ("HIGH", "CRITICAL")
                ]
                if values:
                    row["Vulnerabilities"] = values
                else:
                    row.pop("Vulnerabilities")
        for stage, report in (("full", full), ("HC", high)):
            name = subject + "-" + stage
            path = directory / (name + ".raw.json")
            path.write_text(json.dumps(report))
            controls["scans"][name] = {
                "exit": int(stage == "HC" and subject != "candidate"),
                "timeout": False,
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    return candidate, controls


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "scanner-error",
        "timeout",
        "boolean-exit",
        "missing-scan",
        "missing-report",
        "report-alias",
        "image",
        "official-witness",
        "fingerprint",
        "unknown-field",
        "local",
        "same-subject",
        "local-registry",
        "local-tag",
        "local-reference",
        "local-chain",
        "local-rootfs",
        "local-layer-order",
        "local-layer-size",
        "local-descriptor-null",
        "local-descriptor-extra",
        "local-metadata-HC",
        "local-HC-size-float",
        "local-HC-size-bool",
        "local-hides-digest",
        "descriptor-digest-mismatch",
        "descriptor-digest-match",
        "legacy-registry",
        "local-digest-null",
        "local-created-by",
        "local-layer-extra",
        "local-masked-match",
        "secret-layer",
        "secret-extra-field",
        "secret-missing",
        "fixture",
        "parent-layer",
        "child-ran",
        "filesystem-delta",
        "HC-disagrees",
    ],
)
def test_caddy_native_controls_require_decoded_findings_and_complete_subject_relation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    directory = tmp_path / "controls"
    candidate, controls = _caddy_control_fixture(
        directory, local_layer=(fault == "local" or bool(fault and fault.startswith("local-")))
    )
    if fault in ("scanner-error", "timeout", "boolean-exit"):
        target = controls["scans"]["secret-HC"]
        if fault == "timeout":
            target["timeout"] = True
        else:
            target["exit"] = 2 if fault == "scanner-error" else True
    elif fault == "missing-scan":
        controls["scans"].pop("official-HC")
    elif fault == "missing-report":
        (directory / "secret-HC.raw.json").unlink()
    elif fault == "report-alias":
        controls["scans"]["secret-HC"]["file"] = "./secret-HC.raw.json"
    elif fault == "fixture":
        controls["fixture_sha256"] = "0" * 64
    elif fault == "parent-layer":
        controls["parent_layers"] = []
    elif fault == "child-ran":
        controls["child_was_started"] = True
    elif fault == "filesystem-delta":
        controls["filesystem_delta"].append("C /etc/hosts")
    elif fault == "same-subject":
        controls["subjects"]["official"] = controls["subjects"]["secret"]
    elif fault not in (None, "local"):
        names = (
            ["official-full", "official-HC"]
            if fault == "official-witness"
            else ["secret-full", "secret-HC"]
        )
        for name in names:
            path = directory / (name + ".raw.json")
            report = json.loads(path.read_text())
            if fault == "image":
                report["Metadata"]["ImageID"] = "sha256:" + "9" * 64
            elif fault == "official-witness":
                report["Results"][1]["Vulnerabilities"][0]["VulnerabilityID"] = "CVE-other"
            elif fault == "fingerprint" and name.endswith("full"):
                report["Results"][0]["Vulnerabilities"][0]["Fingerprint"] = "sha256:" + "0" * 64
            elif fault == "unknown-field":
                report["Results"][0]["unexplained"] = "must not be dropped"
            elif fault == "secret-layer":
                report["Results"][-1]["Secrets"][0]["Layer"]["DiffID"] = "sha256:" + "9" * 64
            elif fault == "local-registry":
                report["Metadata"]["RepoDigests"] = [
                    "registry.invalid/caddy@" + "sha256:" + "8" * 64
                ]
            elif fault == "local-tag":
                report["Metadata"]["RepoTags"] = ["foreign:tag"]
            elif fault == "local-reference":
                report["Metadata"].pop("Reference")
            elif fault == "local-chain":
                report["Metadata"]["DiffIDs"][0] = "sha256:" + "8" * 64
            elif fault == "local-rootfs":
                report["Metadata"]["ImageConfig"]["rootfs"]["diff_ids"].reverse()
            elif fault == "local-layer-order":
                report["Metadata"]["Layers"].reverse()
            elif fault == "local-layer-size":
                report["Metadata"]["Layers"][-1]["Size"] = True
            elif fault == "local-descriptor-null":
                report["Metadata"]["Layers"][-1]["Digest"] = None
            elif fault == "local-descriptor-extra":
                report["Metadata"]["Layers"][-1]["unknown"] = True
            elif fault == "local-HC-size-float" and name.endswith("HC"):
                report["Metadata"]["Layers"][-1]["Size"] = 512.0
            elif fault == "local-HC-size-bool":
                report["Metadata"]["Layers"][-1]["Size"] = True if name.endswith("HC") else 1
            elif fault == "local-metadata-HC" and name.endswith("HC"):
                report["Metadata"]["Layers"][-1]["Size"] += 1
            elif fault == "local-hides-digest":
                report["Metadata"]["Layers"][-1]["Digest"] = "sha256:" + "8" * 64
            elif fault in ("descriptor-digest-match", "descriptor-digest-mismatch"):
                final_layer = report["Results"][-1]["Secrets"][0]["Layer"]
                digest = (
                    final_layer["Digest"]
                    if fault == "descriptor-digest-match"
                    else "sha256:" + "8" * 64
                )
                report["Metadata"]["Layers"] = [
                    {"Size": 512, "DiffID": controls["parent_layers"][0]},
                    {"Size": 512, "DiffID": final_layer["DiffID"], "Digest": digest},
                ]
            elif fault == "legacy-registry":
                report["Metadata"]["RepoDigests"] = [
                    "registry.invalid/caddy@" + "sha256:" + "7" * 64
                ]
            elif fault == "local-digest-null":
                report["Results"][-1]["Secrets"][0]["Layer"]["Digest"] = None
            elif fault == "local-created-by":
                report["Results"][-1]["Secrets"][0]["Layer"]["CreatedBy"] = "other"
            elif fault == "local-layer-extra":
                report["Results"][-1]["Secrets"][0]["Layer"]["unknown"] = True
            elif fault == "local-masked-match":
                report["Results"][-1]["Secrets"][0]["Match"] = "wrong"
            elif fault == "secret-extra-field":
                report["Results"][-1]["Secrets"][0]["unknown"] = "must not be dropped"
            elif fault == "secret-missing":
                report["Results"].pop()
            elif fault == "HC-disagrees" and name.endswith("HC"):
                report["Results"][0]["Packages"][0]["Version"] = "2"
            path.write_text(json.dumps(report))
            controls["scans"][name]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(args, 0, args[-1] + "\n", ""),
    )
    original = {path.name: path.read_bytes() for path in directory.iterdir()}
    if fault in (None, "local", "descriptor-digest-match", "legacy-registry"):
        result = runtime_surface.validate_caddy_control_reports(
            candidate, controls, directory, candidate_binary_sha256="c" * 64
        )
        assert result["native_controls"] == "observed_exact_current_epoch"
        assert result["v3_scanner_comparability"] == "UNKNOWN"
        assert len(result["reports"]) == 6
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_control_reports(
                candidate, controls, directory, candidate_binary_sha256="c" * 64
            )
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "official-observed",
        "wrong-owner",
        "binary-tampered",
        "metadata-symlink",
        "reader-version",
        "module-version",
        "replacement",
        "wrong-package",
        "candidate-observed",
        "candidate-version",
    ],
)
def test_caddy_static_subjects_bind_original_metadata_and_both_native_inventories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    directory = tmp_path / "controls"
    candidate, controls = _caddy_control_fixture(directory)
    static = controls["official_static"]
    metadata = directory / "official-go-version-m.txt"
    if fault == "wrong-owner":
        static["image"] = controls["subjects"]["candidate"]
    elif fault == "binary-tampered":
        (directory / "official-caddy.binary").write_bytes(b"changed")
    elif fault == "metadata-symlink":
        backup = metadata.rename(directory / "fixture.txt")
        metadata.symlink_to(backup)
    elif fault in ("reader-version", "module-version", "replacement"):
        text = metadata.read_text()
        if fault == "reader-version":
            text = text.replace("go1.26.11", "go1.26.10")
        elif fault == "module-version":
            text = text.replace("v2.11.4", "v2.11.9")
        else:
            text = text.replace("dep github.com/go-jose", "=> other v0.0.0\ndep github.com/go-jose")
        metadata.write_text(text)
        static["metadata_sha256"] = hashlib.sha256(metadata.read_bytes()).hexdigest()
    elif fault in ("official-observed", "wrong-package", "candidate-observed", "candidate-version"):
        subject = "candidate" if fault.startswith("candidate-") else "official"
        scan = controls["scans"][subject + "-full"]
        path = directory / scan["file"]
        report = json.loads(path.read_bytes())
        row = report["Results"][1]
        pkg = next(p for p in row["Packages"] if p["Name"] == runtime_surface.CADDY_MODULE)
        if fault == "candidate-version":
            pkg["Version"] = "v2.11.4"
            hc = controls["scans"]["candidate-HC"]
            hc_path = directory / hc["file"]
            high = json.loads(hc_path.read_bytes())
            next(p for p in high["Results"][1]["Packages"] if p["Name"] == pkg["Name"]).update(pkg)
            hc_path.write_text(json.dumps(high))
            hc["sha256"] = hashlib.sha256(hc_path.read_bytes()).hexdigest()
        else:
            row.setdefault("Vulnerabilities", []).append(
                {
                    "VulnerabilityID": runtime_surface.CADDY_UPGRADE_CVE,
                    "PkgID": pkg["ID"],
                    "PkgName": "other" if fault == "wrong-package" else pkg["Name"],
                    "InstalledVersion": pkg["Version"],
                    "Severity": "LOW",
                    "Status": "affected",
                }
            )
        path.write_text(json.dumps(report))
        scan["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if subject == "candidate":
            candidate = report
    monkeypatch.setattr(
        runtime_surface,
        "_run_docker",
        lambda args: subprocess.CompletedProcess(args, 0, args[-1] + "\n", ""),
    )
    if fault in (None, "official-observed"):
        result = runtime_surface.validate_caddy_control_reports(
            candidate, controls, directory, candidate_binary_sha256="c" * 64
        )
        assert result["subjects"]["candidate"]["scanner_visibility"] == "not_reported"
        observed = result["subjects"]["official"]
        assert observed["scanner_visibility"] == ("observed" if fault else "not_reported")
        assert observed["reported_severities"] == (["LOW"] if fault else [])
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_control_reports(
                candidate, controls, directory, candidate_binary_sha256="c" * 64
            )


def test_caddy_synthetic_environment_accepts_exactly_all_720_orders() -> None:
    from itertools import permutations

    expected = [
        "HOME=/run/pulseplate-caddy-tmp",
        "TMPDIR=/run/pulseplate-caddy-tmp",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CADDY_VERSION=v2.11.9",
        "XDG_CONFIG_HOME=/config",
        "XDG_DATA_HOME=/data",
    ]
    assert len({entry.split("=", 1)[0] for entry in expected}) == 6
    count = 0
    for order in permutations(expected):
        actual = list(order)
        assert runtime_surface._is_caddy_synthetic_environment(actual)
        assert actual == list(order)
        count += 1
    assert count == 720
    invalid: list[object] = [None, tuple(expected), {}, "invalid", 1, True]
    for position in range(6):
        invalid.extend(
            [expected[:position] + expected[position + 1 :], expected + [expected[position]]]
        )
        for replacement in (
            False,
            1,
            None,
            [],
            {},
            "invalid",
            "HOME=/changed",
            expected[(position + 1) % 6],
        ):
            invalid.append([*expected[:position], replacement, *expected[position + 1 :]])
        for suffix in (" ", "\nprivate", "\rprivate", "\0private", "\u2028private"):
            invalid.append(
                [*expected[:position], expected[position] + suffix, *expected[position + 1 :]]
            )
    invalid.extend(
        expected + [key + "=synthetic"]
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "UNKNOWN")
    )
    for value in invalid:
        assert runtime_surface._is_caddy_synthetic_environment(value) is False


def _upgrade_native_fixture(case: str = "upgrade", *, response: bytes | None = None) -> bytes:
    """Independent native-shape fixture; not evidence of a real Caddy process."""
    duplex = case == "upgrade"
    client_frame = bytes.fromhex("818d13579bdf4307a9eb2a63b6bc7f3efeb167")
    server_frame = bytes.fromhex("810d5050323439342d736572766572")
    request = b"GET /ws HTTP/1.1\r\nHost: localhost\r\n"
    if duplex:
        request += b"Connection: Upgrade\r\nUpgrade: websocket\r\n"
    request += b"\r\n" + (client_frame if duplex else b"")
    if response is None:
        if duplex:
            response = (
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                b"Connection: Upgrade\r\n"
                b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
                b"X-End-To-End: first\r\nx-end-to-end: second\r\n"
            )
            response += b"\r\n" + server_frame
        elif case == "ordinary-200":
            response = (
                b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\n"
                b"X-End-To-End: first\r\nx-end-to-end: second\r\n\r\nordinary-body\r\n"
            )
        else:
            response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
    if duplex:
        upstream = (
            b"HTTP/1.1 101 Switching Protocols\r\nConnection: upgrade\r\nUpgrade: websocket\r\n"
            b"X-End-To-End: first\r\nx-end-to-end: second\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n"
        ) + server_frame
    else:
        upstream = (
            b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\n"
            b"Connection: keep-alive\r\nKeep-Alive: timeout=5\r\n"
            b"X-End-To-End: first\r\nx-end-to-end: second\r\n\r\nordinary-body\r\n"
        )
    files = {
        "server-received": request,
        "client-received": response,
        "server-stderr": b"",
        "client-stderr": b"",
        "stop-server.stderr": b"",
        "stop-client.stderr": b"",
        "kill-server.stderr": b"",
        "kill-client.stderr": b"",
        "wait-server.stderr": b"Killed\n",
        "wait-client.stderr": b"Killed\n",
        "server-sent": upstream,
    }
    rows = [
        "TERMINAL role=server stop=0 kill=0 wait=137",
        "TERMINAL role=client stop=0 kill=0 wait=137",
    ]
    rows += [f"FILE name={name} bytes={len(raw)} hex={raw.hex()}" for name, raw in files.items()]
    return ("\n".join(rows) + "\nRESULT primary=0 capture=0\n").encode()


@pytest.mark.parametrize("case", ["upgrade", "ordinary-200"])
def test_caddy_upgrade_native_channels_keep_http_and_duplex_contract(case: str) -> None:
    result = runtime_surface._validate_caddy_upgrade_exchange(case, _upgrade_native_fixture(case))
    assert result["case"] == case
    assert result["duplex"] is (case == "upgrade")


@pytest.mark.parametrize("case", ["ordinary-200", "upgrade"])
@pytest.mark.parametrize("defect", ["missing", "empty", "truncated", "substituted", "forwarded"])
def test_caddy_observer_requires_emitted_input_and_normalized_output(
    case: str, defect: str
) -> None:
    rows = _upgrade_native_fixture(case).decode().splitlines()
    index = next(i for i, row in enumerate(rows) if row.startswith("FILE name=server-sent "))
    emitted = bytes.fromhex(rows[index].split(" hex=")[1])
    if defect == "forwarded":
        # Replacing the observed client response with the unchanged input must reject both cases.
        index = next(
            i for i, row in enumerate(rows) if row.startswith("FILE name=client-received ")
        )
        rows[index] = f"FILE name=client-received bytes={len(emitted)} hex={emitted.hex()}"
        error = "canonical upgrade Connection" if case == "upgrade" else "ordinary response"
    elif defect == "missing":
        del rows[index]
        error = "incomplete native terminal result"
    else:
        changed = {"empty": b"", "truncated": emitted[:-1], "substituted": emitted.swapcase()}[
            defect
        ]
        rows[index] = f"FILE name=server-sent bytes={len(changed)} hex={changed.hex()}"
        error = "captured upstream response"
    with pytest.raises(ValueError, match=error):
        runtime_surface._validate_caddy_upgrade_exchange(case, ("\n".join(rows) + "\n").encode())


@pytest.mark.parametrize(
    "defect",
    [
        "status",
        "missing-upgrade",
        "extra-connection",
        "lost-duplicate",
        "wrong-frame",
        "unmasked-client",
        "timeout",
        "native-failure",
        "missing-role",
        "duplicate-role",
        "missing-channel",
        "truncated-channel",
        "socket-diagnostic",
        "cleanup",
        "extra-output",
    ],
)
def test_caddy_upgrade_rejects_protocol_capture_and_cleanup_failures(defect: str) -> None:
    raw = _upgrade_native_fixture()
    rows = raw.decode().splitlines()
    if defect in {
        "status",
        "missing-upgrade",
        "extra-connection",
        "lost-duplicate",
        "wrong-frame",
        "unmasked-client",
    }:
        index = next(
            i
            for i, row in enumerate(rows)
            if row.startswith(
                "FILE name="
                + ("server-received" if defect == "unmasked-client" else "client-received")
            )
        )
        prefix, wire_hex = rows[index].split(" hex=")
        wire = bytes.fromhex(wire_hex)
        if defect == "status":
            wire = wire.replace(b"101 Switching Protocols", b"200 OK")
        elif defect == "missing-upgrade":
            wire = wire.replace(b"Upgrade: websocket\r\n", b"")
        elif defect == "extra-connection":
            wire = wire.replace(
                b"Connection: Upgrade\r\n", b"Connection: Upgrade\r\nConnection: other\r\n"
            )
        elif defect == "lost-duplicate":
            wire = wire.replace(b"x-end-to-end: second\r\n", b"")
        elif defect == "unmasked-client":
            wire = wire[: wire.index(b"\r\n\r\n") + 4] + bytes.fromhex(
                "810d5050323439342d636c69656e74"
            )
        else:
            wire = wire[:-1] + b"x"
        rows[index] = prefix.split(" bytes=")[0] + f" bytes={len(wire)} hex={wire.hex()}"
    elif defect == "timeout":
        rows[-1] = "RESULT primary=143 capture=0"
    elif defect == "native-failure":
        rows[-1] = "RESULT primary=1 capture=0"
    elif defect == "missing-role":
        rows.pop(0)
    elif defect == "duplicate-role":
        rows[1] = rows[0]
    elif defect == "missing-channel":
        rows.pop(4)
    elif defect == "truncated-channel":
        rows[2] = rows[2].replace("bytes=", "bytes=9")
    elif defect == "socket-diagnostic":
        rows[4] = "FILE name=server-stderr bytes=1 hex=78"
    elif defect == "cleanup":
        rows[0] = "TERMINAL role=server stop=0 kill=1 wait=0"
    else:
        rows.insert(-1, "UNRECOGNIZED")
    with pytest.raises(ValueError):
        runtime_surface._validate_caddy_upgrade_exchange(
            "upgrade", ("\n".join(rows) + "\n").encode()
        )


def test_caddy_normal_entry_configuration_keeps_static_d_separate() -> None:
    static = json.loads(runtime_surface.CADDY_D_CONFIG)
    upgraded = json.loads(runtime_surface.CADDY_UPGRADE_CONFIG)
    assert upgraded["admin"] == static["admin"]
    server = upgraded["apps"]["http"]["servers"]["ci"]
    assert server["listen"] == ["127.0.0.1:18080"]
    assert server["routes"][1:] == static["apps"]["http"]["servers"]["ci"]["routes"]
    assert server["routes"][0]["match"] == [{"path": ["/ws"]}]
    handler = server["routes"][0]["handle"][0]
    assert handler["handler"] == "reverse_proxy"
    assert handler["upstreams"] == [{"dial": "127.0.0.1:18081"}]
    cases = runtime_surface._caddy_upgrade_cases()
    assert set(cases) == {"upgrade", "ordinary-200"}
    assert runtime_surface._caddy_websocket_frame(b"PP2494-client", masked=True) == bytes.fromhex(
        "818d13579bdf4307a9eb2a63b6bc7f3efeb167"
    )
    assert runtime_surface._caddy_websocket_frame(b"PP2494-server", masked=False) == bytes.fromhex(
        "810d5050323439342d736572766572"
    )


@pytest.mark.parametrize(
    "fault",
    [None, "native", "stderr", "capture", "cleanup", "native-and-capture", "native-and-cleanup"],
)
def test_caddy_upgrade_execution_reuses_native_owner_and_retains_failure_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from scripts.ci import prometheus_source_image as source

    seen: list[str] = []
    monkeypatch.setattr(runtime_surface, "DOCKER_BINARY", "/usr/bin/docker")
    monkeypatch.setattr(runtime_surface, "_CADDY_REMAINING", lambda cap: min(cap, 120.0))

    class Native:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            self.evidence = evidence
            self.records: list[dict[str, object]] = []
            assert cleanup == 0

        def run(
            self,
            argv: list[str],
            name: str,
            env: dict[str, str],
            *,
            cwd: Path,
            maximum_seconds: int,
            output_bound: int,
        ) -> bytes:
            seen.append(name)
            assert argv[:2] == ["/usr/bin/docker", "--config"]
            assert argv[3:8] == ["exec", "owned-caddy", "/bin/busybox", "sh", "-c"]
            assert maximum_seconds == 35 and output_bound == 65536
            assert set(env) == {"PATH", "HOME", "DOCKER_CONFIG", "LANG"}
            assert cwd == tmp_path
            assert Path(env["DOCKER_CONFIG"]).is_dir()
            self.records.append({"name": name, "exit": 1 if fault == "native" else 0})
            (self.evidence / (name + ".stderr")).write_bytes(
                b"diagnostic" if fault == "stderr" else b""
            )
            if fault in ("capture", "native-and-capture"):
                (self.evidence / "native-records.json").write_text("existing retained evidence")
            if fault in ("cleanup", "native-and-cleanup"):
                (Path(env["DOCKER_CONFIG"]) / "unexpected").write_text("retain")
            if fault in ("native", "native-and-capture", "native-and-cleanup"):
                raise RuntimeError("native failure retained")
            return _upgrade_native_fixture(name)

    monkeypatch.setattr(source, "Native", Native)
    if fault is None:
        result = runtime_surface._observe_caddy_upgrade_exchanges("owned-caddy", tmp_path)
        assert len(result) == 2 and len(seen) == 2
    else:
        with pytest.raises((RuntimeError, ValueError, OSError)) as failure:
            runtime_surface._observe_caddy_upgrade_exchanges("owned-caddy", tmp_path)
        assert seen == (
            ["upgrade"]
            if fault in ("native", "stderr", "native-and-capture", "native-and-cleanup")
            else list(runtime_surface._caddy_upgrade_cases())
        )
        if fault.startswith("native-and-"):
            assert str(failure.value) == "native failure retained"
            assert len(failure.value.__notes__) == 1
    record = (tmp_path / "upgrade-native/native-records.json").read_text()
    if fault in ("capture", "native-and-capture"):
        assert record == "existing retained evidence"
    else:
        assert len(json.loads(record)) == len(seen)
    assert (tmp_path / "upgrade-native/docker-config").exists() is (
        fault in ("cleanup", "native-and-cleanup")
    )


@pytest.mark.parametrize("stop,kill", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_caddy_nonupgrade_natural_exit_retains_actual_signal_race(stop: int, kill: int) -> None:
    raw = (
        _upgrade_native_fixture("ordinary-200")
        .replace(
            b"TERMINAL role=client stop=0 kill=0 wait=137",
            f"TERMINAL role=client stop={stop} kill={kill} wait=0".encode(),
        )
        .replace(
            b"FILE name=wait-client.stderr bytes=7 hex=4b696c6c65640a",
            b"FILE name=wait-client.stderr bytes=0 hex=",
        )
    )
    assert runtime_surface._validate_caddy_upgrade_exchange("ordinary-200", raw)["roles"][
        "client"
    ] == (stop, kill, 0)


@pytest.mark.parametrize(
    "response",
    [
        b"HTTP/1.1 200 OK\r\nContent-Length: 14\r\nX-End-To-End: first\r\nX-End-To-End: second\r\n\r\nordinary-body\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\nX-End-To-End: first\r\nX-End-To-End: second\r\n\r\n",
        b'HTTP/1.1 200 OK\r\nContent-Length: 15\r\nAlt-Svc: h3=":443"\r\nX-End-To-End: first\r\nX-End-To-End: second\r\n\r\nordinary-body\r\n',
    ],
)
def test_caddy_ordinary_response_requires_complete_body_length_and_no_alt_svc(
    response: bytes,
) -> None:
    with pytest.raises(ValueError):
        runtime_surface._validate_caddy_upgrade_exchange(
            "ordinary-200",
            _upgrade_native_fixture("ordinary-200", response=response),
        )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-stdlib",
        "extra-member",
        "original-goroot",
        "goroot-alias",
        "stdlib-location",
        "changed-postbuild",
        "input-drift",
        "command-root",
        "shared-cache",
        "red-setup",
        "missing-custom",
        "substituted-custom",
        "duplicate-terminal",
        "terminal-before-run",
        "skip",
        "malformed-parity",
        "v3-aggregate",
        "stdlib-aggregate",
        "union-aggregate",
    ],
)
def test_caddy_stdlib_proof_and_private_import_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    directory = tmp_path / "source"
    binary, digest, recipe = _caddy_source_fixture(directory, monkeypatch)
    if fault in {"v3-aggregate", "stdlib-aggregate", "union-aggregate"}:
        names, constant = {
            "v3-aggregate": (runtime_surface.CADDY_V3_BUILD_MEMBERS, "CADDY_V3_TOTAL_BYTES"),
            "stdlib-aggregate": (runtime_surface.CADDY_STDLIB_MEMBERS, "CADDY_STDLIB_TOTAL_BYTES"),
            "union-aggregate": (runtime_surface.CADDY_BUILD_MEMBERS, "CADDY_SOURCE_TOTAL_BYTES"),
        }[fault]
        monkeypatch.setattr(
            runtime_surface, constant, sum((directory / name).stat().st_size for name in names) - 1
        )
    elif fault == "missing-stdlib":
        (directory / "stdlib-post-build-tree.sha256").unlink()
    elif fault == "extra-member":
        (directory / "stdlib-unknown.txt").write_text("not admitted")
    elif fault in {"original-goroot", "goroot-alias", "stdlib-location"}:
        path = directory / "import-graph.txt"
        original = runtime_surface.CADDY_STDLIB_ROOT + "/src/fmt"
        changed = {
            "original-goroot": "/usr/local/go/src/fmt",
            "goroot-alias": runtime_surface.CADDY_STDLIB_ROOT + "/src/./fmt",
            "stdlib-location": runtime_surface.CADDY_STDLIB_ROOT + "/src/other",
        }[fault]
        path.write_text(path.read_text().replace(original, changed))
    elif fault == "changed-postbuild":
        path = directory / "stdlib-post-build-tree.sha256"
        path.write_bytes(path.read_bytes().replace(b"a", b"b", 1))
    elif fault == "input-drift":
        path = directory / "stdlib-inputs.sha256"
        path.write_bytes(path.read_bytes().replace(b"2dc6", b"3dc6", 1))
    elif fault in {"command-root", "shared-cache"}:
        path = directory / "stdlib-test-commands.txt"
        old, new = (
            (runtime_surface.CADDY_STDLIB_ROOT, "/usr/local/go")
            if fault == "command-root"
            else ("/opt/caddy-stdlib-patched-cache", "/opt/caddy-stdlib-baseline-cache")
        )
        command_text = path.read_text()
        assert old in command_text
        path.write_text(command_text.replace(old, new))
    elif fault == "red-setup":
        path = directory / "stdlib-baseline-red.jsonl"
        path.write_bytes(
            path.read_bytes().replace(
                b"PP_BASELINE_SETUP_BODY_CLOSE_OK", b"PP_BASELINE_SETUP_OR_BODY_CLOSE_FAILURE"
            )
        )
    elif fault in {
        "missing-custom",
        "substituted-custom",
        "duplicate-terminal",
        "terminal-before-run",
        "skip",
        "malformed-parity",
    }:
        path = directory / "stdlib-patched-tests.jsonl"
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        selected = "TestPPHTTPPersistenceOptions/duplicate_nominees"
        if fault == "missing-custom":
            rows = [row for row in rows if row.get("Test") != selected]
        elif fault == "substituted-custom":
            for row in rows:
                if row.get("Test") == selected:
                    row["Test"] = "TestPPHTTPPersistenceOptions/unreviewed_substitute"
        elif fault == "duplicate-terminal":
            rows.append(
                next(
                    dict(row)
                    for row in rows
                    if row.get("Test") == selected and row["Action"] == "pass"
                )
            )
        elif fault == "terminal-before-run":
            run = next(
                i
                for i, row in enumerate(rows)
                if row.get("Test") == selected and row["Action"] == "run"
            )
            end = next(
                i
                for i, row in enumerate(rows)
                if row.get("Test") == selected and row["Action"] == "pass"
            )
            rows[run], rows[end] = rows[end], rows[run]
        elif fault == "skip":
            next(row for row in rows if row.get("Test") == selected and row["Action"] == "pass")[
                "Action"
            ] = "skip"
        else:
            row = next(row for row in rows if "PP_ACCEPTED_PARITY" in row.get("Output", ""))
            row["Output"] = row["Output"].replace("error=<nil>", "error=changed")
        path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))
    if fault is not None:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_source_evidence(
                directory, binary_metadata=binary, binary_sha256=digest, recipe=recipe
            )
    else:
        result = runtime_surface.validate_caddy_source_evidence(
            directory, binary_metadata=binary, binary_sha256=digest, recipe=recipe
        )
        assert result["stdlib_source"]["patched_goroot"] == runtime_surface.CADDY_STDLIB_ROOT
        assert len(result["stdlib_source"]["patched_tests"]["runs"]) >= 61
        assert result["v3_scanner_comparability"] == "UNKNOWN"


def test_caddy_stdlib_exact_identity_inventory() -> None:
    patched = runtime_surface._caddy_stdlib_custom_identities(
        set(runtime_surface.CADDY_STDLIB_CUSTOM_TOPS)
    )
    baseline = runtime_surface._caddy_stdlib_custom_identities(
        runtime_surface.CADDY_STDLIB_BASELINE_CUSTOM
    )
    assert len(patched) == 61
    assert len(baseline) == 26
    assert "TestPPHTTPPersistenceBoundaryControls/eof_close_without_close_token" in baseline
    assert "TestPPHTTPMalformedAcceptedParity/legacy_space_field_name" in baseline
    assert len(runtime_surface.CADDY_V3_BUILD_MEMBERS) == 16
    assert len(runtime_surface.CADDY_STDLIB_MEMBERS) == 12
    assert len(runtime_surface.CADDY_BUILD_MEMBERS) == 28


@pytest.fixture
def caddy062_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Small synthetic metadata only; real retained source hashes are native evidence."""
    output = tmp_path / "metadata"
    output.mkdir()
    for phase in ("baseline", "incumbent", "final"):
        modules = [
            {"Path": "pulseplate.local/caddy-build", "Main": True},
            {
                "Path": "github.com/caddyserver/caddy/v2",
                "Version": "v2.11.4" if phase == "baseline" else "v2.11.9",
                "Sum": "h1:synthetic",
            },
            {"Path": "golang.org/x/net", "Version": "v0.62.0" if phase == "final" else "v0.60.0"},
            {
                "Path": "example.test/added" if phase == "final" else "example.test/removed",
                "Version": "v1.0.0",
            },
        ]
        packages = [
            {
                "ImportPath": "github.com/caddyserver/caddy/v2/cmd/caddy",
                "Name": "main",
                "Imports": ["golang.org/x/net/html"],
            },
            {"ImportPath": "golang.org/x/net/html", "Name": "html", "Imports": []},
        ]
        files = {
            "go.mod": (phase + " mod\n").encode(),
            "go.sum": (phase + " sums\n").encode(),
            "modules.json": ("\n".join(json.dumps(row) for row in modules) + "\n").encode(),
            "packages.json": ("\n".join(json.dumps(row) for row in packages) + "\n").encode(),
            "module-graph.txt": b"pulseplate.local/caddy-build golang.org/x/net@v0.60.0\n",
            "verify.txt": b"all modules verified\n",
        }
        for suffix, raw in files.items():
            (output / (phase + "-" + suffix)).write_bytes(raw)
            if phase != "baseline":
                (output / (phase + "-offline-" + suffix)).write_bytes(raw)
    monkeypatch.setattr(
        runtime_surface,
        "CADDY_XNET062_INCUMBENT_FILES",
        {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in runtime_surface.CADDY_XNET062_INCUMBENT_FILES
        },
    )
    return output


def test_caddy062_metadata_separates_historical_root_and_new_module_intent(
    caddy062_metadata: Path,
) -> None:
    result = runtime_surface.validate_caddy_xnet062_metadata(caddy062_metadata)
    assert result["epoch"] == "caddy2.11.9-xnet062-metadata"
    assert result["build_profile_admission"].startswith("HOLD")
    delta = {row["path"]: row for row in result["complete_delta"]}
    assert set(delta) == {"golang.org/x/net", "example.test/added", "example.test/removed"}
    assert delta["golang.org/x/net"]["class"] == "I_R"
    assert delta["golang.org/x/net"]["before"]["Version"] == "v0.60.0"
    assert delta["golang.org/x/net"]["after"]["Version"] == "v0.62.0"
    assert delta["example.test/added"]["before"] is None
    assert delta["example.test/removed"]["after"] is None
    assert [row["path"] for row in result["historical_caddy_delta"]] == [
        "github.com/caddyserver/caddy/v2"
    ]


@pytest.mark.parametrize("fault", ["incumbent", "missing", "symlink", "offline", "empty"])
def test_caddy062_metadata_rejects_unbound_or_incomplete_bytes(
    caddy062_metadata: Path, fault: str
) -> None:
    target = caddy062_metadata / "final-go.sum"
    if fault == "incumbent":
        (caddy062_metadata / "incumbent-go.sum").write_bytes(b"different incumbent")
    elif fault == "missing":
        target.unlink()
    elif fault == "symlink":
        target.unlink()
        target.symlink_to(caddy062_metadata / "final-offline-go.sum")
    elif fault == "empty":
        target.write_bytes(b"")
    else:
        (caddy062_metadata / "final-offline-go.sum").write_bytes(b"different offline")
    with pytest.raises((ValueError, OSError)):
        runtime_surface.validate_caddy_xnet062_metadata(caddy062_metadata)


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-net",
        "wrong-root",
        "replacement",
        "duplicate",
        "package-error",
        "missing-import",
        "malformed-graph",
        "missing-command",
    ],
)
def test_caddy062_metadata_rejects_semantically_invalid_final_observations(
    caddy062_metadata: Path, fault: str
) -> None:
    suffix = "modules.json"
    if fault in ("package-error", "missing-import", "missing-command"):
        suffix = "packages.json"
    if fault == "malformed-graph":
        suffix = "module-graph.txt"
        data = b"malformed-edge\n"
    else:
        rows = [
            json.loads(line)
            for line in (caddy062_metadata / ("final-" + suffix)).read_text().splitlines()
        ]
        if fault == "wrong-net":
            rows[2]["Version"] = "v0.60.0"
        elif fault == "wrong-root":
            rows[1]["Version"] = "v2.11.4"
        elif fault == "replacement":
            rows[2]["Replace"] = {"Path": "/unqualified"}
        elif fault == "duplicate":
            rows.append(dict(rows[2]))
        elif fault == "package-error":
            rows[0]["Error"] = {"Err": "synthetic error"}
        elif fault == "missing-command":
            rows.pop(0)
        else:
            rows.pop(1)
        data = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    for phase in ("final", "final-offline"):
        (caddy062_metadata / (phase + "-" + suffix)).write_bytes(data)
    with pytest.raises((ValueError, RuntimeError)):
        runtime_surface.validate_caddy_xnet062_metadata(caddy062_metadata)


def test_caddy062_recipe_and_workflow_preserve_seed_then_one_new_action() -> None:
    import re

    root = Path(__file__).resolve().parents[1]
    recipe = (root / "frontend/Dockerfile.caddy-spa").read_text()
    gets = re.findall(r"^    go get ([^;]+);", recipe, re.MULTILINE)
    assert gets == [
        "github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4",
        "google.golang.org/grpc@v1.83.2",
        "golang.org/x/crypto@v0.55.0",
        "golang.org/x/net@v0.60.0",
        "github.com/klauspost/compress@v1.18.7",
        "github.com/go-jose/go-jose/v4@v4.1.6",
        "github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.9",
        "golang.org/x/net@v0.62.0",
    ]
    workflow = (root / ".github/workflows/frontend-ci.yml").read_text()
    assert "options: [contract, xnet062-metadata, candidate-D]" in workflow
    assert 'for phase, online_script in (("incumbent", seed), ("final", advance))' in workflow
    assert "for offline in (False, True)" in workflow
    assert '"caddy_retained_incumbent_before_new_get"' in workflow
    assert '"caddy_metadata_offline_input_changed"' in workflow
    assert '"caddy_independent_raw_output_equality"' in workflow
    assert 'caddy_ci_charge_action("BUILD")' in workflow
    assert '"historical-caddy-delta.json"' in workflow
    seed = workflow.split("seed = '''", 1)[1].split("'''", 1)[0]
    advance = workflow.split("advance = '''", 1)[1].split("'''", 1)[0]
    assert "cp go.sum /output/incumbent-postget-go.sum" in seed
    assert "cmp go.sum /output/incumbent-postget-go.sum" not in seed
    assert seed.index("go mod download all", seed.index("@v2.11.9")) < seed.index(
        "capture incumbent"
    )
    assert "cmp go.mod /output/post-get-go.mod" in advance
    assert "cmp go.sum /output/post-get-go.sum" not in advance
    assert (
        "f5d9289fa0e27604a936ed5e35368db876398dac62154b9a6af9d0d2a891f7d9  /output/post-get-go.sum"
        in advance
    )
    assert "be8f44f7e591bcaa54412fe5f3061235596be2faf9bd3f5fdece0106fea45338  go.sum" in advance


def test_caddy062_current_generated_metadata_bindings_match_exact_observed_DATA() -> None:
    assert runtime_surface.CADDY_XNET062_INCUMBENT_FILES == {
        "baseline-go.mod": "e85dc5d385d444fc90eb5a35ba42eb3fe404515c9a66fcdcea5aa3e61472a603",
        "baseline-go.sum": "912171681209ea4fcc6c3f2571307a16dfccb77ac88eb4ec6e1246329a1e23df",
        "baseline-modules.json": "940262f6c6411705a735cdd2a4fe07910a90d7963807152164a316a77c77fe32",
        "baseline-module-graph.txt": "3cbdbceb9b1e4b9d81b22583172692ff9090d386f6f67836e01324a3a6675cc8",
        "baseline-packages.json": "1a973a0b318f58e0a30c7c9aea831a7cd6794ee61fae489734cf5f42b6e69bab",
        "baseline-verify.txt": "b4537ed75f533f993f371954de47e42a793b8e5b0587577de7e27fb3e50696bd",
        "incumbent-go.mod": "4a11def21d6670163e30e911b160c48f1ad5af8eb946a4388b86d60c473f7bda",
        "incumbent-go.sum": "bc1def232f1f0a8d205b39c38fa9b0159d481c05f90933bc975659ec0c0317c8",
        "incumbent-modules.json": "350ebc67daf202a4f184a940a1459e7c02ef07a677048498d1d8905bb95f090d",
        "incumbent-module-graph.txt": "a1631c64f483398286ca2eda8d9d36dc1889163e63df4572a8f153d1b68b0cd2",
        "incumbent-packages.json": "cc45b9153ba630ef3cb65da4419358bc0bcba666779714e57b6b49f4306a77db",
        "incumbent-verify.txt": "b4537ed75f533f993f371954de47e42a793b8e5b0587577de7e27fb3e50696bd",
    }
    assert runtime_surface.CADDY_XNET062_PROFILE_SHA256 == (
        "3c20d7520c469a5f5d02fee4c12205a434e9e22088320791c45e95a4f5f50b74"
    )
    recipe = Path(__file__).resolve().parents[1] / "frontend/Dockerfile.caddy-spa"
    assert hashlib.sha256(recipe.read_bytes()).hexdigest() == (
        "5c3425b7d668dd4a768ddca65f4b483b97c3dfdf8735bfb2a0520b711e68540c"
    )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "metadata",
        "dirty",
        "omitted-input",
        "head",
        "attempt",
        "recipe",
        "old-recipe",
        "old-platform",
        "old-Go-version",
        "status-only",
        "cleanup",
        "same-start",
        "stale-binding",
        "missing-lane",
        "aliased-lane",
        "partial-lock",
        "extra-member",
        "one-wrong",
        "equal-wrong",
        "equal-package-replacement",
        "finish",
        "recovery-build",
        "train-build",
        "transition-build",
        "recovery-stale",
        "transition-substitute",
        "transition-replacement",
        "recovery-input",
        "allow-ignored-outputs",
        "stage-drift",
        "charge",
    ],
)
def test_caddy062_charge_step_requires_independently_reviewed_same_run_outputs(
    caddy062_metadata: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from contextlib import contextmanager
    import os
    import shutil
    from collections.abc import Callable, Iterator
    from typing import Any

    import yaml

    from scripts.ci.prometheus_source_image import (
        canonical_data,
        tree_inventory,
        QualificationError,
    )
    from scripts.orchestration.creative_code_patch_workspace import (
        git_env_without_parent_state,
        safe_git_config_args,
    )

    root = Path(__file__).resolve().parents[1]
    steps = yaml.safe_load((root / ".github/workflows/frontend-ci.yml").read_text())["jobs"][
        "caddy-contract"
    ]["steps"]
    charge_step = next(
        s for s in steps if s["name"] == "Charge Build source-patched Caddy candidate budget"
    )
    build = next(s for s in steps if s["name"] == "Build source-patched Caddy candidate")
    assert steps.index(charge_step) + 1 == steps.index(build)
    assert (
        build["if"]
        == charge_step["if"]
        == "${{ steps.caddy-admission.outputs.mode == 'build' && steps.caddy-metadata.outcome == 'success' }}"
    )
    admission = next(step for step in steps if step.get("id") == "caddy-admission")
    assert charge_step["env"]["GH_TOKEN"] == (
        "${{ steps.caddy-admission.outputs.owner_prebuild == 'true' && github.token || '' }}"
    )
    emission = 'output.write("owner_prebuild=true\\n")'
    assert admission["run"].count(emission) == 1
    assert 'if state["mode"] == "build" and owner_build:\n        ' + emission in admission["run"]
    assert not charge_step.get("continue-on-error")
    workflow = yaml.safe_load((root / ".github/workflows/frontend-ci.yml").read_text())
    concurrency = workflow["concurrency"]
    assert "inputs.caddy_action == 'candidate-D' && '-caddy-D-producer'" in concurrency["group"]
    assert concurrency["cancel-in-progress"] == "${{ inputs.caddy_action != 'candidate-D' }}"
    assert build["with"]["context"] == "${{ steps.caddy-build-budget.outputs.context }}"
    assert (
        build["with"]["file"]
        == "${{ steps.caddy-build-budget.outputs.context }}/Dockerfile.caddy-spa"
    )
    cleanup = next(s for s in steps if s["name"] == "Clean staged Caddy build context")
    assert cleanup["if"] == "${{ always() && steps.caddy-build-budget.outputs.context != '' }}"
    assert (
        charge_step["env"]["CADDY_METADATA_BINDING"]
        == "${{ steps.caddy-metadata.outputs.prebuild_binding }}"
    )

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    selected = [
        *sorted(runtime_surface.CADDY_CI_FIXED_SOURCES),
        "frontend/Dockerfile.caddy-spa",
        "frontend/.dockerignore",
        "frontend/package-lock.json",
        "frontend/another",
        "frontend/space and\r\nnewline",
    ]
    for name in selected:
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            (root / name).read_bytes() if name == "frontend/Dockerfile.caddy-spa" else b"fixture"
        )
    (checkout / "frontend/another").chmod(0o755)
    (checkout / ".gitignore").write_text(
        "/frontend/dist/\n/frontend/node_modules/\n/frontend/fixtures/\n"
        "/frontend/Dockerfile.caddy-spa.dockerignore\n"
    )
    git = shutil.which("git")
    assert git
    env = git_env_without_parent_state()
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
    ):
        subprocess.run([git, *safe_git_config_args(), *args], cwd=checkout, env=env, check=True)
    head = subprocess.check_output(
        [git, "rev-parse", "HEAD"], cwd=checkout, env=env, text=True
    ).strip()
    inputs = runtime_surface.caddy_ci_source_inventory(checkout, selected)
    if fault == "allow-ignored-outputs":
        for path in ("dist/output.js", "node_modules/module.js", "fixtures/untracked.js"):
            ignored = checkout / "frontend" / path
            ignored.parent.mkdir()
            ignored.write_bytes(b"ignored")
        (checkout / "frontend/Dockerfile.caddy-spa.dockerignore").write_bytes(b"!fixtures\n")
    state = {
        "mode": "build",
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "repository_id": 1043311030,
        "current_head": head,
        "current_run_id": 73,
        "current_run_attempt": 1,
        "inputs": inputs,
    }
    branch_by_lane = {
        "train": "codex/cab07c-eslint-pages-features",
        "recovery": "codex/npm-braces-build-prerequisite",
        "transition": "codex/alertmanager-oras-copy-fix",
    }
    pr_lane = str(fault).partition("-")[0]
    owner_build = pr_lane in branch_by_lane
    branch = branch_by_lane.get(pr_lane, "codex/dependency-alertmanager-remediation")
    number_by_lane = {"transition": 9999, "recovery": 2495, "train": 2484}
    if owner_build:
        state.update(source_branch=branch, source_pr=number_by_lane[pr_lane], pr_head=head)
        sender = {"type": "User", "login": "Katsiarynakavaleuskaya", "id": 73}
        event = tmp_path / "dispatch.json"
        event.write_text(
            json.dumps(
                {
                    "sender": sender,
                    "ref": branch,
                    "inputs": {
                        "caddy_action": "candidate-D",
                        "caddy_source_sha": "0" * 40 if fault == "recovery-input" else head,
                    },
                }
            )
        )
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
        monkeypatch.setenv("GITHUB_ACTOR", sender["login"])
        monkeypatch.setenv("GITHUB_ACTOR_ID", str(sender["id"]))
        monkeypatch.setenv("GH_TOKEN", "synthetic-prebuild-reader")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    if fault == "omitted-input":
        del inputs["frontend/another"]
    if fault == "dirty":
        (checkout / "frontend/another").write_text("different")
    if fault == "metadata":
        state["mode"] = "metadata"
    (tmp_path / "caddy-admission").mkdir()
    (tmp_path / "caddy-admission/admission.json").write_bytes(canonical_data(state))
    metadata = tmp_path / "caddy-xnet062-metadata"
    for extra in (
        "alpine-release.txt",
        "compiler-version.txt",
        "complete-delta.json",
        "historical-caddy-delta.json",
        "incumbent-postget-go.mod",
        "incumbent-postget-go.sum",
        "module-derivation.patch",
        "post-get-go.mod",
        "post-get-go.sum",
    ):
        (caddy062_metadata / extra).write_text(extra + "\n")
    # Independently projected miniature policy for this synthetic scheduling fixture.
    monkeypatch.setattr(
        runtime_surface,
        "CADDY_XNET062_PROFILE_SHA256",
        "29a6fa2670dc8157f7cad1bd65c3de4465468387316f3e146ca454e49285b4c8",
    )
    for lane in ("a", "b"):
        output = metadata / lane / "output"
        shutil.copytree(caddy062_metadata, output)
        if fault == "equal-wrong" or (fault == "one-wrong" and lane == "b"):
            for phase in ("final", "final-offline"):
                path = output / (phase + "-modules.json")
                path.write_bytes(path.read_bytes().replace(b"v1.0.0", b"v1.0.1"))
        if fault == "equal-package-replacement":
            for phase in ("final", "final-offline"):
                path = output / (phase + "-packages.json")
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                rows[0]["Module"] = {"Replace": {"Path": "example.test/unchecked"}}
                path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = {
        "status": runtime_surface.CADDY_XNET062_METADATA_SUCCESS,
        "failure": None,
        "go_build_invocations": 0,
        "authored_action": "golang.org/x/net@v0.62.0",
        "source_head": head,
        "run_id": 73,
        "run_attempt": 1,
        "recipe_sha256": inputs["frontend/Dockerfile.caddy-spa"]["sha256"],
        "compiler_platform": {
            "digest": "sha256:6fa4e6dc2fc42920e53eb6b6a7e928155dc68282060f0901ec3cdd134c3a0eb5"
        },
        "compiler_go_version_sha256": "3008ffc50874cac169bf0446997798346d244c5c1ff94af771a02191f465a4b1",
        "compiler_scan": {"Secrets_fields_absent": 1},
        "derivations": {
            lane: runtime_surface.validate_caddy_xnet062_metadata(metadata / lane / "output")
            for lane in ("a", "b")
        },
    }
    records = [
        {
            "stdout": f"{lane}-{phase}-{network}-native.stdout",
            "argv": ["docker", "--config", "config", "start", "--attach", f"{idx:064x}"],
            "exit": 0,
            "failure": None,
        }
        for idx, (lane, phase, network) in enumerate(
            (
                (lane, phase, network)
                for lane in ("a", "b")
                for phase in ("incumbent", "final")
                for network in ("online", "offline")
            ),
            1,
        )
    ]
    if fault == "same-start":
        records[4]["argv"] = records[0]["argv"]
    report["native_commands"] = [
        {
            "stdout": "compiler-native-version.stdout",
            "argv": ["docker", "--config", "config", "start", "--attach", "f" * 64],
            "exit": 0,
            "failure": None,
        },
        *records,
        {
            "stdout": "cleanup-absence.stdout",
            "argv": ["docker", "--config", "config", "ps"],
            "exit": 0,
            "failure": None,
        },
    ]
    if fault == "status-only":
        report = {"status": runtime_surface.CADDY_XNET062_METADATA_SUCCESS}
    if fault == "head":
        report["source_head"] = "1" * 40
    if fault == "attempt":
        report["run_attempt"] = True
    if fault == "recipe":
        report["recipe_sha256"] = "0" * 64
    if fault == "old-recipe":
        report["recipe_sha256"] = "0c78748dba55fceea2afbb62f4bd6693f3d784f613089c7a8fbc54b518344f92"
    if fault == "old-platform":
        report["compiler_platform"][
            "digest"
        ] = "sha256:9d1e2c4fda593efb2c405e1c855c75ec17fe42dc02f6b7142a5ea7af7f386bf4"
    if fault == "old-Go-version":
        report["compiler_go_version_sha256"] = (
            "4e0b213cba780f63b02f3ab9001ee61e4101d254e0af1a8205574c19dad0f93b"
        )
    if fault == "cleanup":
        report["cleanup_failure"] = "fixture failure"
    (metadata / "evidence").mkdir()
    (metadata / "evidence/qualification.json").write_bytes(canonical_data(report))
    producer = next(s for s in steps if s.get("id") == "caddy-metadata")
    marker = "# Only a completed producer"
    emit = producer["run"][producer["run"].index(marker) :].rsplit("\nPY", 1)[0]
    out = tmp_path / "step-output"
    assert producer["env"]["CADDY_CAPTURE_MODE"] == "${{ steps.caddy-admission.outputs.mode }}"
    monkeypatch.setenv("CADDY_CAPTURE_MODE", "build")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    exec(
        compile(emit, "<caddy-metadata-output>", "exec"),
        {
            "hashlib": hashlib,
            "canonical_data": canonical_data,
            "report": report,
            "output_inventory": tree_inventory(metadata / "a/output"),
            "os": os,
        },
    )
    key, binding = out.read_text().strip().split("=", 1)
    assert key == "prebuild_binding"
    for key, value in {
        "GITHUB_SHA": head,
        "GITHUB_REF": "refs/heads/" + branch,
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_RUN_ID": "73",
        "GITHUB_RUN_ATTEMPT": "1",
        "RUNNER_TEMP": str(tmp_path),
        "CADDY_ACTION": "candidate-D",
        "CADDY_METADATA_BINDING": binding if fault != "stale-binding" else "0" * 64,
    }.items():
        monkeypatch.setenv(key, value)
    right = metadata / "b/output"
    if fault in ("missing-lane", "aliased-lane"):
        shutil.rmtree(right)
        if fault == "aliased-lane":
            right.symlink_to(metadata / "a/output", target_is_directory=True)
    if fault == "partial-lock":
        (right / "final-go.sum").unlink()
    if fault == "extra-member":
        (right / "extra").touch()
    order = []

    @contextmanager
    def processing(phase: str):
        if phase == "ADMISSION":
            assert owner_build
            yield float
            return
        assert phase == "PROCESSING"
        yield float
        if fault == "finish":
            raise ValueError("processing exit")
        order.append("finished")

    def charge(phase: str) -> None:
        order.append(phase)
        if fault == "charge":
            raise ValueError("charge failed")

    @contextmanager
    def reader(
        root: Path, directory: Path, remaining: Callable, expected: str
    ) -> Iterator[Callable]:
        assert owner_build and directory == tmp_path / "caddy-admission/prebuild-api"
        assert expected == inputs["scripts/ci/prometheus_source_image.py"]["sha256"]

        def get(endpoint: str) -> Any:
            number = 9998 if fault == "transition-replacement" else number_by_lane[pr_lane]
            repo = {"id": 1043311030, "full_name": "Katsiarynakavaleuskaya/PulsePlate"}
            pr = {
                "number": number,
                "state": "open",
                "base": {"ref": "main", "repo": repo, "sha": runtime_surface.CADDY_COPY_BASE},
                "head": {
                    "repo": repo,
                    "ref": "wrong" if fault == "transition-substitute" else branch,
                    "sha": "f" * 40 if fault == "recovery-stale" else head,
                },
            }

            if endpoint.startswith("/pulls?"):
                assert pr_lane == "transition"
                return [pr]
            if endpoint == "/git/ref/heads/main":
                return {
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": runtime_surface.CADDY_COPY_BASE},
                }
            assert endpoint == f"/pulls/{number}"
            return pr

        yield get

    validate_original = runtime_surface.validate_caddy_prebuild

    def validate(
        work: Path, inventory: dict[str, dict[str, object]], checked_head: str, deadline: float
    ) -> dict[str, Any]:
        admission = validate_original(work, inventory, checked_head, deadline)
        if fault == "stage-drift":
            (checkout / "frontend/another").write_bytes(b"changed")
        return admission

    monkeypatch.setattr(runtime_surface, "validate_caddy_prebuild", validate)
    monkeypatch.setattr(runtime_surface, "caddy_ci_reader", reader)
    monkeypatch.setattr(runtime_surface, "caddy_ci_phase", processing)
    monkeypatch.setattr(runtime_surface, "caddy_ci_charge_action", charge)
    monkeypatch.chdir(checkout)
    program = compile(
        charge_step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0], "<caddy-prebuild>", "exec"
    )
    other_context = tmp_path / "caddy-build-context-unowned"
    other_context.mkdir()
    if fault in (
        None,
        "recovery-build",
        "transition-build",
        "train-build",
        "allow-ignored-outputs",
    ):
        exec(program, {})
        assert order == ["finished", "BUILD"]
        outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
        context = Path(outputs["context"])
        created = context.stat()
        assert outputs["context_device"] == str(created.st_dev)
        assert outputs["context_inode"] == str(created.st_ino)
        assert context.parent == tmp_path and context.name.startswith("caddy-build-context-")
        assert context != other_context
        expected_paths = sorted(
            name.removeprefix("frontend/") for name in selected if name.startswith("frontend/")
        )
        assert (
            sorted(path.relative_to(context).as_posix() for path in context.rglob("*"))
            == expected_paths
        )
        for name in expected_paths:
            assert (context / name).read_bytes() == (checkout / "frontend" / name).read_bytes()
        assert (context / "another").stat().st_mode & 0o777 == 0o755
        if fault == "allow-ignored-outputs":
            assert (checkout / "frontend/dist/output.js").is_file()
            assert (checkout / "frontend/fixtures/untracked.js").is_file()
        monkeypatch.setenv("CADDY_BUILD_CONTEXT", str(context))
        monkeypatch.setenv("CADDY_CONTEXT_DEVICE", outputs["context_device"])
        monkeypatch.setenv("CADDY_CONTEXT_INODE", outputs["context_inode"])
        program = cleanup["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        exec(compile(program, "<caddy-build-cleanup>", "exec"), {})
        assert not context.exists()
    else:
        message = {
            "equal-wrong": "reviewed selected-source profile differs",
            "equal-package-replacement": "reviewed selected-source profile differs",
            "old-recipe": "^declared_data_value$",
            "old-platform": "^Caddy qualification identity or cleanup differs$",
            "old-Go-version": "^Caddy qualification identity or cleanup differs$",
            "recovery-input": "^Caddy requires the owner's exact frozen source dispatch$",
            "recovery-stale": "^Caddy current authenticated PR source changed$",
            "transition-replacement": "^Caddy current authenticated PR source changed$",
            "transition-substitute": "^Caddy original PR identity differs$",
            "stage-drift": "^Caddy build context source changed before staging$",
        }.get(fault)
        with pytest.raises((OSError, KeyError, ValueError, QualificationError), match=message):
            exec(program, {})
        assert order == (
            ["finished", "BUILD"]
            if fault == "charge"
            else (
                ["finished"]
                if fault in ("recovery-stale", "transition-substitute", "transition-replacement")
                else []
            )
        )
    assert other_context.is_dir()
    assert list(tmp_path.glob("caddy-build-context-*")) == [other_context]


@pytest.mark.parametrize("fault", ["wrong-parent", "wrong-prefix", "wrong-device", "replacement"])
def test_caddy_staged_context_cleanup_rejects_unowned_directory(tmp_path: Path, fault: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    owned = workspace / "caddy-build-context-owned"
    owned.mkdir()
    original = owned.stat()
    identity = (original.st_dev, original.st_ino)
    if fault == "wrong-parent":
        target = tmp_path / owned.name
        owned.rename(target)
    elif fault == "wrong-prefix":
        target = workspace / "unowned"
        owned.rename(target)
    elif fault == "wrong-device":
        identity = (original.st_dev + 1, original.st_ino)
        target = owned
    else:
        retained = workspace / "retained"
        owned.rename(retained)
        owned.mkdir()
        assert owned.stat().st_ino != original.st_ino
        target = owned

    sentinel = target / "keep"
    sentinel.write_text("leave untouched")
    diagnostic = "ownership" if fault in {"wrong-parent", "wrong-prefix"} else "identity"
    with pytest.raises(ValueError, match=f"^Caddy staged build context {diagnostic} differs$"):
        runtime_surface.clean_staged_caddy_build_context(workspace, target, identity)
    assert sentinel.read_text() == "leave untouched"


def test_caddy_metadata_native_identity_delegates_without_config_ID_alias() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/frontend-ci.yml"
    ).read_text()
    assert (
        "image_relation = native_go_identity(observed, raw, platform_raw, expected_source=compiler)"
        in workflow
    )
    assert (
        "native_container_image_identity(inspected, image_relation, expected_source=compiler)"
        in workflow
    )
    assert (
        "native_container_image_identity(terminal, image_relation, expected_source=compiler)"
        in workflow
    )
    assert (
        "native_container_image_identity(actual, image_relation, expected_source=compiler)"
        in workflow
    )
    assert 'inspected["Id"] == container_id' in workflow
    assert (
        "validate_caddy_metadata_custody(version_before, version_after, started_id=version_id)"
        in workflow
    )
    assert (
        "validate_caddy_metadata_custody(inspected, terminal, started_id=container_id)" in workflow
    )
    assert (
        "validate_caddy_metadata_custody(owned_profiles[name], actual, started_id=started_id)"
        in workflow
    )
    assert 'version_before["Config"]["Cmd"] == ["version"]' in workflow
    assert 'inspected["Config"]["Cmd"] == ["-c", script]' in workflow
    assert 'json.loads(platform_raw)["config"]["digest"] == observed["Id"]' not in workflow
    assert (
        "CADDY_METADATA_BINDING: ${{ steps.caddy-metadata.outputs.prebuild_binding }}" in workflow
    )


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        (None, None),
        ("missing-start", "actual start"),
        ("zero-start", "actual start"),
        ("invalid-date", "actual start"),
        ("unknown-state", "current state"),
        ("never-started-null", "declared_data_type"),
        ("foreign-id", "declared_data_value"),
        ("wrong-attempt", "another container"),
        ("renamed", "declared_data_value"),
        ("integer", "declared_data_type"),
        ("nested-float", "declared_data_type"),
        ("missing-key", "declared_data_keys"),
        ("reverse-transition", "declared_data_type"),
        ("short-id", "full container ID"),
        ("mount-rotation", None),
        ("mount-carrier", "Mounts must be a list"),
        ("mount-row-before", "mount must be an object"),
        ("mount-missing-key", "canonical absolute path"),
        ("mount-key-type", "canonical absolute path"),
        ("mount-relative", "canonical absolute path"),
        ("mount-root", "canonical absolute path"),
        ("mount-nul", "canonical absolute path"),
        ("mount-double-leading", "canonical absolute path"),
        ("mount-empty-component", "canonical absolute path"),
        ("mount-trailing", "canonical absolute path"),
        ("mount-dot", "canonical absolute path"),
        ("mount-dot-dot", "canonical absolute path"),
        ("mount-duplicate-before-self", "destination is duplicated"),
        ("mount-duplicate-after", "destination is duplicated"),
        ("mount-membership", "declared_data_keys"),
        ("mount-source", "declared_data_value"),
        ("mount-rw-type", "declared_data_type"),
        ("mount-extra-field", "declared_data_keys"),
    ],
)
def test_caddy_metadata_custody_accepts_only_the_observed_typed_transition(
    fault: str | None, message: str | None
) -> None:
    from copy import deepcopy
    from typing import Any

    before: dict[str, Any] = {
        "Id": "a" * 64,
        "Name": "/caddy-fixture",
        "Image": "sha256:" + "b" * 64,
        "Config": {"Cmd": ["version"], "Labels": {"pulseplate.caddy-metadata": "9"}},
        "Mounts": [],
        "State": {"Status": "created", "Running": False, "StartedAt": "0001-01-01T00:00:00Z"},
        "HostConfig": {"OomKillDisable": False, "Resources": {"PidsLimit": 128}},
    }
    actual = deepcopy(before)
    actual["State"] = {
        "Status": "exited",
        "Running": False,
        "StartedAt": "2026-11-07T18:00:00.123456789Z",
    }
    actual["HostConfig"]["OomKillDisable"] = None
    attempted = before["Id"]
    if fault == "missing-start":
        attempted = None
    elif fault == "zero-start":
        actual["State"]["StartedAt"] = before["State"]["StartedAt"]
    elif fault == "invalid-date":
        actual["State"]["StartedAt"] = "2026-02-31T18:00:00Z"
    elif fault == "unknown-state":
        actual["State"]["Status"] = "dead"
    elif fault == "never-started-null":
        actual["State"] = deepcopy(before["State"])
    elif fault == "foreign-id":
        actual["Id"] = "f" * 64
    elif fault == "wrong-attempt":
        attempted = "f" * 64
    elif fault == "renamed":
        actual["Name"] = "/foreign"
    elif fault == "integer":
        actual["HostConfig"]["OomKillDisable"] = 0
    elif fault == "nested-float":
        actual["HostConfig"]["Resources"]["PidsLimit"] = 128.0
    elif fault == "missing-key":
        del actual["HostConfig"]["OomKillDisable"]
    elif fault == "reverse-transition":
        before["HostConfig"]["OomKillDisable"] = None
        actual["HostConfig"]["OomKillDisable"] = False
    elif fault == "short-id":
        before["Id"] = actual["Id"] = attempted = "a" * 12
    elif fault is not None and fault.startswith("mount-"):
        # The hosted resolver's last mount was reported first at terminal inspection.
        mounts = [
            {
                "Type": "bind",
                "Source": "/owned" + destination,
                "Destination": destination,
                "Mode": "",
                "RW": True,
                "Propagation": "rprivate",
            }
            for destination in ("/modules", "/home", "/cache", "/tmp", "/output", "/work")
        ]
        before["Mounts"] = mounts
        actual["Mounts"] = deepcopy(mounts[-1:] + mounts[:-1])
        row = actual["Mounts"][0]
        match fault:
            case "mount-carrier":
                actual["Mounts"] = {}
            case "mount-row-before":
                before["Mounts"][0] = None
            case "mount-missing-key":
                del row["Destination"]
            case "mount-key-type":
                row["Destination"] = 1
            case "mount-relative":
                row["Destination"] = "work"
            case "mount-root":
                row["Destination"] = "/"
            case "mount-nul":
                row["Destination"] = "/work\0"
            case "mount-double-leading":
                row["Destination"] = "//work"
            case "mount-empty-component":
                row["Destination"] = "/work//cache"
            case "mount-trailing":
                row["Destination"] = "/work/"
            case "mount-dot":
                row["Destination"] = "/work/."
            case "mount-dot-dot":
                row["Destination"] = "/work/cache/.."
            case "mount-duplicate-before-self":
                before["Mounts"].append(deepcopy(mounts[0]))
                actual = before
                attempted = None
            case "mount-duplicate-after":
                actual["Mounts"].append(deepcopy(row))
            case "mount-membership":
                row["Destination"] = "/different"
            case "mount-source":
                row["Source"] = "/foreign/work"
            case "mount-rw-type":
                row["RW"] = 1
            case "mount-extra-field":
                row["Extra"] = True
    snapshot = json.dumps([before, actual], sort_keys=True)
    if message is None:
        runtime_surface.validate_caddy_metadata_custody(before, actual, started_id=attempted)
        runtime_surface.validate_caddy_metadata_custody(before, before, started_id=None)
    else:
        with pytest.raises((ValueError, RuntimeError), match=message):
            runtime_surface.validate_caddy_metadata_custody(before, actual, started_id=attempted)
    assert json.dumps([before, actual], sort_keys=True) == snapshot


def _repair_subject_fixture() -> tuple[dict[str, str], dict[str, Any]]:
    from scripts.ci.fetch_docker_source_artifacts import _alertmanager_accepted_producer

    selected = _alertmanager_accepted_producer()
    return {
        "source": selected["source"],
        "q": "43808505545/14199242996",
        "s": "43810186398/14200227448",
        "c": f'{selected["run"]}/{selected["artifact"]}',
        "zip": "sha256:" + selected["zip_sha256"],
        "manifest": selected["graph"]["manifest"]["digest"],
    }, selected


class _DispatchNativeFixture:
    """Native response and ZIP fixtures. No network, actual credentials or registered GitHub runs."""

    def __init__(
        self, pr: dict[str, Any], material: dict[str, str], fault: str | None = None
    ) -> None:
        self.pr, self.material, self.fault = pr, material, fault
        self.repo = {"id": 1043311030, "full_name": runtime_surface.CADDY_REPOSITORY}
        self.actor = {"id": 169792616, "login": "Katsiarynakavaleuskaya", "type": "User"}
        self.records: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], bytes]] = {}
        self.lists = 0
        self.live_id = 73
        self.subject, self.original = _repair_subject_fixture()

    def projection(
        self,
        run: int = 73,
        action: str = "candidate-D",
        started: str = "2026-01-01T00:00:00Z",
        producer: int = 73,
    ) -> dict[str, str]:
        material = self.material
        return {
            **material,
            "action": action,
            "input": runtime_surface.publisher_repair_input(material, action),
            "run": str(run),
            "job": str(run + 1000),
            "started": started,
            "source_horizon": "2099-01-01T00:00:00Z",
            "expires": runtime_surface._publisher_utc(
                runtime_surface._publisher_time(started) + runtime_surface._REPAIR_WINDOW
            ),
            "producer_run": str(producer),
        }

    def add(self, projection: dict[str, str], *, active: bool = False) -> None:
        import io
        import zipfile
        from datetime import datetime, timedelta

        r = int(projection["run"])
        w = projection["callers"]
        created = projection["started"]
        action = projection["action"]

        def later(minutes: int) -> str:
            return (
                datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ") + timedelta(minutes=minutes)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        steps = []

        def step(name: str, muted: bool = False) -> None:
            i = len(steps) + 1
            steps.append(
                {
                    "name": name,
                    "number": i,
                    "status": "completed",
                    "conclusion": "skipped" if muted else "success",
                    "started_at": None if muted else later(i),
                    "completed_at": None if muted else later(i),
                }
            )

        step("Admit existing Caddy producer or exact retained subject")
        step("Verify delegated publisher repair input", self.fault == "skipped-input")
        step("Download original retained Caddy candidate", action != "contract")
        step("Import and bind exact retained Caddy candidate", action != "contract")
        step("Charge Build source-patched Caddy candidate budget", action != "candidate-D")
        step("Build source-patched Caddy candidate", action != "candidate-D")
        step(
            "Decide source-qualified Caddy inventory and current native controls",
            self.fault == "skipped-decision",
        )
        step("Upload Caddy contract evidence", self.fault == "skipped-upload")
        step("Verify published repair evidence transport")
        run = {
            "id": r,
            "run_attempt": 1,
            "head_branch": self.pr["head"]["ref"],
            "head_sha": w,
            "workflow_id": 196310935,
            "path": ".github/workflows/frontend-ci.yml",
            "event": "workflow_dispatch",
            "repository": self.repo,
            "head_repository": self.repo,
            "actor": self.actor,
            "triggering_actor": self.actor,
            "created_at": created,
            "run_started_at": created,
            "status": "in_progress" if active else "completed",
            "conclusion": None if active else "success",
        }
        job = {
            "id": r + 1000,
            "run_id": r,
            "run_attempt": 1,
            "head_sha": w,
            "head_branch": run["head_branch"],
            "name": "caddy-contract",
            "started_at": created,
            "completed_at": None if active else later(9),
            "status": run["status"],
            "conclusion": run["conclusion"],
            "steps": steps,
        }
        bound = dict(projection)
        if action == "candidate-D":
            bound.update(producer_run=str(r), producer_head=w)
        elif not active:
            old = self.records[int(projection["producer_run"])]
            bound.update(
                producer_head=old[0]["head_sha"],
                producer_artifact=str(old[2]["id"]),
                producer_digest=old[2]["digest"],
            )
        runtime_raw = b'{"fixture":"successful checked runtime"}'
        strict = b'{"native":"strict report"}'
        decision = {
            "current_head": w,
            "publisher_dispatch": bound,
            "decision": "source_CVE116587_correction_with_unsuppressed_scan",
            "CD_release_accepted": False,
            "runtime_observation_sha256": hashlib.sha256(runtime_raw).hexdigest(),
            "image": "sha256:" + "1" * 64,
            "strict_conversion": {"native_exit": 0, "sha256": hashlib.sha256(strict).hexdigest()},
        }
        if self.fault == "missing-projection":
            del decision["publisher_dispatch"]
        inputs = {"fixture": "exact"}
        admission = {
            "mode": "build" if action == "candidate-D" else "reuse",
            "current_head": w,
            "current_run_id": r,
            "current_run_attempt": 1,
            "source_pr": self.pr["number"],
            "publisher_repair": {
                key: v
                for key, v in bound.items()
                if key
                not in ("producer_run", "producer_head", "producer_artifact", "producer_digest")
            },
            "inputs": inputs,
        }
        if action == "candidate-D":
            admission["publisher_repair"]["producer_run"] = str(r)
        if self.fault == "changed-admission":
            admission["publisher_repair"]["input"] = "replaced technical operand"
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as z:
            decision_raw = json.dumps(decision).encode()
            z.writestr("source-decision.json", decision_raw)
            z.writestr("strict-control.raw.json", strict)
            z.writestr("loaded-runtime/observation.json", runtime_raw)
            z.writestr(
                "controls/native-controls.json",
                json.dumps({"cleanup": self.fault != "cleanup-failed"}),
            )
            if action == "candidate-D":
                tar = b"synthetic test image bytes"
                manifest = {
                    "producer_run_id": r,
                    "producer_run_attempt": 1,
                    "producer_head": w,
                    "inputs": inputs,
                    "image_config_id": decision["image"],
                    "archive_bytes": len(tar),
                    "archive_sha256": hashlib.sha256(tar).hexdigest(),
                    "source_decision_sha256": hashlib.sha256(decision_raw).hexdigest(),
                }
                z.writestr("candidate.json", json.dumps(manifest))
                z.writestr(
                    "candidate.docker.tar",
                    tar if self.fault != "wrong-image-bytes" else b"?" * len(tar),
                )
            elif not active:
                prior = {
                    "run_id": int(bound["producer_run"]),
                    "head": bound["producer_head"],
                    "artifact": {
                        "id": int(bound["producer_artifact"]),
                        "digest": bound["producer_digest"],
                    },
                    "git_inputs": inputs,
                }
                admission["producer"] = prior
                z.writestr("original-producer.json", json.dumps(prior))
            z.writestr("admission.json", json.dumps(admission))
        archive = raw.getvalue()
        artifact = {
            "id": r + 10000,
            "name": "caddy-contract-evidence.zip",
            "created_at": later(8),
            "expires_at": "2099-01-02T00:00:00Z",
            "expired": False,
            "size_in_bytes": len(archive),
            "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
            "workflow_run": {
                "id": r,
                "head_sha": w,
                "repository_id": 1043311030,
                "head_repository_id": 1043311030,
            },
        }
        self.records[r] = (run, job, artifact, archive)

    def read(self, path: str) -> Any:
        from copy import deepcopy
        import re

        if path == f"/pulls/{self.pr['number']}":
            return deepcopy(self.pr)
        if path == "/git/ref/heads/" + self.pr["head"]["ref"]:
            return {
                "ref": "refs/heads/" + self.pr["head"]["ref"],
                "object": {"type": "commit", "sha": self.pr["head"]["sha"]},
            }
        if path == "/actions/workflows/frontend-ci.yml":
            return {"id": 196310935, "path": ".github/workflows/frontend-ci.yml"}
        if path == "/actions/workflows/cd.yml":
            return {"id": 123, "path": ".github/workflows/cd.yml"}
        for label, name, job_name in (
            ("q", "alertmanager-module-qualification", "alertmanager-module-qualification"),
            ("s", "alertmanager-input-inspection", "alertmanager-input-inspection"),
            ("c", "alertmanager-candidate", "alertmanager-candidate-build"),
        ):
            run, artifact = map(int, self.subject[label].split("/"))
            rev = self.subject["source"]
            branch = "codex/dependency-alertmanager-remediation"
            if path == f"/actions/artifacts/{artifact}":
                return {
                    "id": artifact,
                    "name": f"{name}-{run}-1",
                    "expired": False,
                    "expires_at": "2099-01-01T00:00:00Z",
                    "digest": (
                        self.subject["zip"]
                        if label == "c" and self.fault != "wrong-original-C"
                        else "sha256:" + "f" * 64
                    ),
                    "workflow_run": {
                        "id": run,
                        "head_sha": (
                            "f" * 40
                            if (label, self.fault)
                            in (("q", "wrong-original-Q"), ("s", "wrong-original-S"))
                            else rev
                        ),
                        "head_branch": branch,
                        "repository_id": 1043311030,
                        "head_repository_id": 1043311030,
                    },
                }
            attempt = f"/actions/runs/{run}/attempts/1"
            if path == attempt:
                return {
                    "id": run,
                    "event": "workflow_dispatch",
                    "run_attempt": 1,
                    "head_sha": rev,
                    "head_branch": branch,
                    "workflow_id": 123,
                    "path": ".github/workflows/cd.yml",
                    "repository": self.repo,
                    "head_repository": self.repo,
                    "status": "completed",
                    "conclusion": "success",
                }
            if path == attempt + "/jobs?per_page=100&page=1":
                return {
                    "total_count": 1,
                    "jobs": [
                        {
                            "id": self.original["job"] if label == "c" else run,
                            "run_id": run,
                            "run_attempt": 1,
                            "head_sha": rev,
                            "name": job_name,
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ],
                }
        if path.startswith("/actions/workflows/frontend-ci.yml/runs?"):
            self.lists += 1
            head = re.search(r"head_sha=([0-9a-f]{40})", path).group(1)
            runs = [v[0] for v in self.records.values() if v[0]["head_sha"] == head]
            if self.fault == "list-drift" and self.lists % 2 == 0:
                runs = []
            listed = deepcopy(runs)
            if self.fault in (
                "first-wins-rerun",
                "first-wins-in-progress",
                "failed-first",
                "replacement-zip",
            ):
                for row in listed:
                    row.update(
                        run_attempt=2,
                        status=(
                            "in_progress" if self.fault == "first-wins-in-progress" else "completed"
                        ),
                        conclusion=(
                            None
                            if self.fault == "first-wins-in-progress"
                            else "success" if self.fault == "failed-first" else "failure"
                        ),
                        triggering_actor={"id": 19, "login": "subsequent", "type": "User"},
                    )
            return {"total_count": len(listed), "workflow_runs": listed}
        for r, (run, job, artifact, raw) in self.records.items():
            if path == f"/actions/runs/{r}":
                return deepcopy(run)
            if path == f"/actions/runs/{r}/attempts/1":
                if self.fault == "failed-first":
                    return {**run, "status": "completed", "conclusion": "failure"}
                return None if self.fault == "missing-attempt" else deepcopy(run)
            if path == f"/actions/runs/{r}/attempts/1/jobs?per_page=100&page=1":
                native_job = deepcopy(job)
                if self.fault == "missing-job-attempt":
                    del native_job["run_attempt"]
                return {"total_count": 1, "jobs": [native_job]}
            if path == f"/actions/runs/{r}/artifacts?per_page=100&page=1":
                artifacts = [] if self.fault == "missing-artifact" else [deepcopy(artifact)]
                if self.fault == "replacement-zip":
                    artifacts[0].update(id=27, created_at="2026-02-01T00:00:00Z")
                if self.fault == "short-retention":
                    artifacts[0]["expires_at"] = "2098-12-31T23:59:59.999999Z"
                return {"total_count": len(artifacts), "artifacts": artifacts}
            if path == f"/actions/artifacts/{artifact['id']}":
                return deepcopy(artifact)
            if path == f"/actions/artifacts/{artifact['id']}/zip":
                return raw + b"stale" if self.fault == "wrong-archive" else raw
        raise KeyError(path)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        (None, None),
        ("main-advanced", "publisher_repair_live_base"),
        ("reused-branch", None),
        ("two-open-PRs", "Caddy transition PR lookup is ambiguous"),
        ("closed-only", "Caddy observation requires one exact accepted PR or main merge"),
        ("closed-open-response", "Caddy corrective PR listing changed"),
        ("stale-listed-PR", "Caddy corrective PR listing changed"),
        ("wrong-sender", "publisher_repair_actual_dispatch_input"),
        ("wrong-input", "publisher_repair_actual_dispatch_input"),
        ("wrong-trigger", "publisher_repair_live_native_dispatch"),
        ("wrong-archive", "publisher_repair_native_artifact_bytes"),
        ("missing-artifact", "publisher_repair_missing_native_artifact"),
        ("missing-projection", "publisher_repair_missing_checked_input_record"),
        ("wrong-image-bytes", "publisher_repair_retained_build_bytes"),
        ("cleanup-failed", "publisher_repair_retained_native_decision"),
        ("changed-admission", "publisher_repair_archived_admission_differs"),
        ("skipped-decision", "publisher_repair_positive_native_step"),
        ("skipped-upload", "publisher_repair_positive_native_step"),
        ("skipped-input", None),
        ("missing-attempt", "publisher_repair_missing_native_attempt"),
        ("missing-job-attempt", "publisher_repair_attempt_job_identity"),
        ("list-drift", "declared_data_"),
        ("competing", "publisher_repair_competing_dispatches"),
        ("wrong-subject", "publisher_repair_terminal_subject_or_input"),
        ("stale-only", None),
        ("legitimate-renewal", None),
        ("prior-W-exact-inputs", None),
        ("expired", None),
        ("late-original-import", None),
        ("first-wins-rerun", None),
        ("first-wins-in-progress", None),
        ("failed-first", None),
        ("replacement-zip", "publisher_repair_missing_native_artifact"),
        ("short-retention", "publisher_repair_evidence_lifetime"),
        ("second-build", "publisher_repair_duplicate_spent_build"),
    ],
)
def test_delegated_caddy_dispatch_live_and_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None, diagnostic: str | None
) -> None:
    from datetime import datetime, timezone
    from scripts.ci.prometheus_source_image import QualificationError

    subject, _ = _repair_subject_fixture()
    b, k, w = "1" * 40, "2" * 40, "3" * 40
    material = {"pr": "81", "base": b, "controller": k, "callers": w, **subject}
    repo = {"id": 1043311030, "full_name": runtime_surface.CADDY_REPOSITORY}
    pr = {
        "number": 81,
        "created_at": "2025-12-31T00:00:00Z",
        "state": "open",
        "merged": False,
        "head": {"sha": w, "ref": "repair/selected", "repo": repo},
        "base": {"sha": b, "ref": "main", "repo": repo},
    }
    api = _DispatchNativeFixture(pr, material)
    projection = api.projection()
    api.add(projection, active=True)
    for key, val in {
        "GITHUB_RUN_ID": "73",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_SHA": w,
        "GITHUB_SHA": w,
        "GITHUB_JOB": "caddy-contract",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_ACTOR_ID": "169792616",
        "GITHUB_ACTOR": "Katsiarynakavaleuskaya",
        "GITHUB_REF": "refs/heads/repair/selected",
        "GITHUB_WORKFLOW_REF": runtime_surface.CADDY_REPOSITORY
        + "/.github/workflows/frontend-ci.yml@refs/heads/repair/selected",
    }.items():
        monkeypatch.setenv(key, val)
    event_path = tmp_path / "event.json"

    def event(proj: dict[str, str]) -> None:
        event_path.write_text(
            json.dumps(
                {
                    "repository": api.repo,
                    "ref": "repair/selected",
                    "inputs": {
                        "caddy_action": proj["action"],
                        "caddy_source_sha": proj["input"] if fault != "wrong-input" else w,
                    },
                    "sender": {**api.actor, "id": 1} if fault == "wrong-sender" else api.actor,
                }
            )
        )

    event(projection)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    main_reads = 0
    looked_up = False

    def read(path: str) -> Any:
        nonlocal main_reads, looked_up
        if path == f"/commits/{w}?per_page=100&page=1":
            return {
                "sha": w,
                "parents": [{"sha": k}],
                "files": [
                    {"filename": f".github/workflows/{name}.yml", "status": "modified"}
                    for name in ("ci", "cd")
                ],
            }
        if path == "/git/ref/heads/main":
            main_reads += 1
            sha = "f" * 40 if main_reads > 1 and fault == "main-advanced" else b
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": sha}}
        query = "&head=Katsiarynakavaleuskaya%3Arepair%2Fselected&base=main&per_page=2"
        if path in ("/pulls?state=open" + query, "/pulls?state=all" + query):
            looked_up = True
            rows = [pr]
            if fault == "stale-listed-PR":
                return [{**pr, "head": {**pr["head"], "sha": "e" * 40}}]
            if fault == "closed-open-response":
                return [{**pr, "state": "closed"}]
            closed = {**pr, "number": 79, "state": "closed"}
            if fault == "reused-branch":
                rows.insert(0, closed)
            elif fault == "two-open-PRs":
                rows.append({**pr, "number": 80})
            elif fault == "closed-only":
                rows = [closed]
            return [
                row for row in rows if row["state"] == "open" or path.startswith("/pulls?state=all")
            ]
        return api.read(path)

    monkeypatch.setattr(runtime_surface, "_publisher_repair_material", lambda *a: None)

    def accepted_source(
        _read: Any, _b: str, _k: str, _w: str, horizons: list[datetime]
    ) -> dict[str, str]:
        horizons.extend([runtime_surface._publisher_time("2099-01-01T00:00:00Z")] * 3)
        return subject

    monkeypatch.setattr(runtime_surface, "_publisher_input_source", accepted_source)
    clock_day = 1

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return datetime(
                2026,
                1,
                clock_day,
                3,
                tzinfo=timezone.utc,
            )

    monkeypatch.setattr(runtime_surface, "datetime", Clock)

    def exercise() -> None:
        nonlocal clock_day
        if fault == "wrong-trigger":
            api.records[73][0]["triggering_actor"] = {**api.actor, "id": 3}
        live = runtime_surface.publisher_repair_dispatch(read, pr, current_event=True)
        if fault == "main-advanced":
            return  # Only the first live admission may satisfy this rejection check.
        assert live == projection
        if fault in (
            None,
            "stale-listed-PR",
            "reused-branch",
            "two-open-PRs",
            "closed-only",
            "closed-open-response",
        ):
            actual = runtime_surface.caddy_bound_pr(read, w)
            assert looked_up and actual == {**pr, "publisher_repair": live}
        state = {"source_pr": 81, "current_head": w, "publisher_repair": live, "mode": "build"}
        assert runtime_surface.verify_caddy_dispatch_projection(state) == {
            **projection,
            "producer_head": w,
        }
        if fault in (
            "legitimate-renewal",
            "prior-W-exact-inputs",
            "expired",
            "second-build",
            "late-original-import",
        ):
            clock_day = 3
        api.fault = fault
        if fault == "wrong-subject":
            projection["manifest"] = "sha256:" + "f" * 64
        if fault in ("stale-only", "prior-W-exact-inputs"):
            projection["callers"] = "4" * 40
        api.add(projection)
        if fault == "late-original-import":
            api.records[73][1]["completed_at"] = "2026-01-02T01:00:00Z"
        if fault == "competing":
            other = api.projection(
                74, action="contract", started="2026-01-01T01:00:00Z", producer=73
            )
            other["manifest"] = "sha256:" + "f" * 64
            api.add(other)
        if fault in (
            "legitimate-renewal",
            "prior-W-exact-inputs",
            "second-build",
            "late-original-import",
        ):
            action = "candidate-D" if fault == "second-build" else "contract"
            renewal = api.projection(74, action=action, started="2026-01-03T00:00:00Z")
            api.add(renewal, active=True)
            event(renewal)
            monkeypatch.setenv("GITHUB_RUN_ID", "74")
            result = runtime_surface.publisher_repair_dispatch(read, pr, current_event=True)
            assert result == {key: value for key, value in renewal.items() if key != "producer_run"}
            original_run, _, artifact, _ = api.records[73]
            bound = runtime_surface.verify_caddy_dispatch_projection(
                {
                    **state,
                    "publisher_repair": result,
                    "mode": "reuse",
                    "inputs": {"fixture": "exact"},
                    "producer": {
                        "run_id": 73,
                        "run_attempt": 1,
                        "head": original_run["head_sha"],
                        "artifact": artifact,
                        "git_inputs": {"fixture": "exact"},
                    },
                }
            )
            assert (
                bound["producer_run"] == "73" and bound["producer_head"] == original_run["head_sha"]
            )
            api.add(bound)
        terminal = runtime_surface.publisher_repair_dispatch(read, pr)
        if fault in ("skipped-input", "stale-only", "expired", "failed-first"):
            assert terminal is None
        else:
            assert terminal is not None and terminal["producer_run"] == "73"
            assert terminal["run"] == (
                "74"
                if fault in ("legitimate-renewal", "prior-W-exact-inputs", "late-original-import")
                else "73"
            )

    if diagnostic:
        with pytest.raises((QualificationError, ValueError), match=diagnostic):
            exercise()
        if fault == "main-advanced":
            assert main_reads == 2 and pr["base"]["sha"] == b and api.lists == 2
        if fault in ("stale-listed-PR", "two-open-PRs", "closed-only", "closed-open-response"):
            assert looked_up
    else:
        exercise()


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "unrelated-removal",
        "single-wrapper",
        "changed-verification",
        "extra-wrapper-edit",
        "wrong-old-pin",
    ],
)
def test_native_baseline_prunes_only_two_authenticated_public_pins(fault: str | None) -> None:
    import base64
    from copy import deepcopy
    from typing import Any
    from scripts.ci.prometheus_source_image import QualificationError

    objects: dict[str, bytes] = {}

    def blob(raw: bytes) -> str:
        oid = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        objects[oid] = raw
        return oid

    def read(path: str) -> dict[str, Any]:
        oid = path.rsplit("/", 1)[1]
        raw = objects[oid]
        return {
            "sha": oid,
            "size": len(raw),
            "encoding": "base64",
            "content": base64.b64encode(raw).decode(),
        }

    helper = "scripts/ci/fetch_docker_source_artifacts.py"
    old, new = b"original test helper", b"reviewed test helper"
    changed = {helper: (blob(old), blob(new))}
    old_digest, new_digest = hashlib.sha256(old).hexdigest(), hashlib.sha256(new).hexdigest()
    fingerprint = hashlib.sha1(old_digest.encode(), usedforsecurity=False).hexdigest()
    baseline: dict[str, Any] = {
        "version": "synthetic",
        "generated_at": "2026-01-01T00:00:00Z",
        "results": {},
    }
    target = deepcopy(baseline)
    for path in ("scripts/deploy.sh", "scripts/deploy_production.sh"):
        before = f'ALERTMANAGER_CONTRACT_HELPER_SHA256="{old_digest}"\n'.encode()
        after = f'ALERTMANAGER_CONTRACT_HELPER_SHA256="{new_digest}"  # pragma: allowlist secret - public AM helper SHA-256\n'.encode()
        if fault == "extra-wrapper-edit":
            after += b"echo unrelated\n"
        if fault == "wrong-old-pin":
            before = before.replace(old_digest.encode(), new_digest.encode())
        changed[path] = (blob(before), blob(after))
        retired = {
            "filename": path,
            "type": "Hex High Entropy String",
            "hashed_secret": fingerprint,
            "is_verified": False,
            "line_number": 1,
        }
        unrelated = {
            **retired,
            "hashed_secret": hashlib.sha256(b"unrelated synthetic finding").hexdigest(),
            "line_number": 2,
        }
        baseline["results"][path] = [retired, unrelated]
        target["results"][path] = [deepcopy(unrelated)]
        if fault == "single-wrapper" and path == "scripts/deploy.sh":
            target["results"][path].append(deepcopy(retired))
        if fault == "changed-verification":
            target["results"][path][0]["is_verified"] = True
        if fault == "unrelated-removal":
            target["results"][path].clear()
    changed[".secrets.baseline"] = (
        blob(json.dumps(baseline).encode()),
        blob(json.dumps(target).encode()),
    )
    if fault is None:
        runtime_surface._publisher_baseline_change(read, changed)
    else:
        with pytest.raises(
            QualificationError, match="publisher_repair_baseline_finding_or_policy_changed"
        ):
            runtime_surface._publisher_baseline_change(read, changed)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        (None, None),
        ("old-event", "publisher_repair_original_event_after_dispatch"),
        ("wrong-source", "publisher_repair_original_event_after_dispatch"),
        ("queued", None),
        ("attempt-queued", None),
        ("original-queued", None),
        ("queued-CD", None),
        ("queued-Caddy-final", None),
        *(
            (case, "publisher_repair_actual_job_after_dispatch")
            for case in (
                "terminal-parent",
                "unknown-parent",
                "concluded-original",
                "missing-conclusion",
                "superseded-attempt",
                "missing-job",
                "queued-job",
                "failed-job",
                "unknown-job",
                "closed-job",
                "job-conclusion",
                "job-no-start",
                "job-other-branch",
                "no-steps",
                "wrong-active-step",
                "two-active",
                "duplicated-step",
                "queued-step",
                "step-before-job",
                "step-at-expiry",
                "skipped-step",
                "step-finished",
                "step-no-start",
                "bool-step-number",
                "untrusted-status",
            )
        ),
        ("expired-job", "publisher_repair_actual_job_after_dispatch"),
        ("missing-job-attempt", "publisher_repair_attempt_job_identity"),
    ],
)
def test_am_pr_read_starts_after_terminal_delegated_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: str | None,
    diagnostic: str | None,
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    w = "9" * 40
    repo = {"id": 1043311030}
    receipt = {
        "created": "2026-01-01T00:09:00Z",
        "expires": "2026-01-02T00:00:00Z",
        "base": "1" * 40,
    }
    workflow, job_name = {
        "queued-CD": ("cd.yml", "prometheus-image-security-pr"),
        "queued-Caddy-final": ("frontend-ci.yml", "caddy-contract"),
    }.get(fault or "", ("ci.yml", "lint"))
    step_name = (
        "Decide source-qualified Caddy inventory and current native controls"
        if job_name == "caddy-contract"
        else "Prepare exact AM subject before material execution"
    )
    run = {
        "id": 22,
        "run_attempt": 2,
        "workflow_id": 12,
        "path": ".github/workflows/" + workflow,
        "event": "pull_request",
        "head_sha": w,
        "head_branch": "fixture/authorized-repair",
        "repository": repo,
        "head_repository": repo,
        "status": (
            "in_progress"
            if fault
            in (
                None,
                "original-queued",
                "old-event",
                "wrong-source",
                "expired-job",
                "missing-job-attempt",
            )
            else "queued"
        ),
        "conclusion": None,
        "run_started_at": "2026-01-01T01:00:00Z",
    }
    event = {
        **run,
        "created_at": "2026-01-01T00:08:59Z" if fault == "old-event" else "2026-01-01T00:30:00Z",
    }
    if fault == "wrong-source":
        event["head_sha"] = "0" * 40
    job = {
        "id": 32,
        "name": job_name,
        "head_branch": run["head_branch"],
        "conclusion": None,
        "completed_at": None,
        "steps": [
            {
                "number": 8,
                "name": step_name,
                "status": "in_progress",
                "conclusion": None,
                "started_at": "2026-01-01T01:00:07Z",
                "completed_at": None,
            }
        ],
        "head_sha": w,
        "run_id": 22,
        "run_attempt": 2,
        "status": "in_progress",
        "started_at": "2026-01-02T00:00:00Z" if fault == "expired-job" else "2026-01-01T01:00:05Z",
    }
    if fault == "missing-job-attempt":
        del job["run_attempt"]
    if fault == "original-queued":
        event["status"] = "queued"
    if fault == "attempt-queued":
        event["status"] = "in_progress"
    if fault == "terminal-parent":
        run["status"], run["conclusion"] = "completed", "cancelled"
    if fault == "unknown-parent":
        event["status"] = "requested"
    if fault == "concluded-original":
        event["conclusion"] = "failure"
    if fault == "missing-conclusion":
        del run["conclusion"]
    if fault == "superseded-attempt":
        event["run_attempt"] = 3
    job.update(
        {
            "queued-job": {"status": "queued"},
            "failed-job": {"status": "completed", "conclusion": "failure"},
            "unknown-job": {"status": "requested"},
            "closed-job": {"completed_at": run["run_started_at"]},
            "job-conclusion": {"conclusion": "cancelled"},
            "job-no-start": {"started_at": None},
            "job-other-branch": {"head_branch": "unrelated/topic"},
            "untrusted-status": {"status": "PRIVATE-UNTRUSTED"},
        }.get(fault or "", {})
    )
    step = job["steps"][0]
    step.update(
        {
            "wrong-active-step": {"name": "unrelated step"},
            "queued-step": {"status": "queued"},
            "step-before-job": {"started_at": "2026-01-01T00:59:59Z"},
            "step-at-expiry": {"started_at": receipt["expires"]},
            "skipped-step": {"conclusion": "skipped"},
            "step-finished": {"completed_at": step["started_at"]},
            "step-no-start": {"started_at": None},
            "bool-step-number": {"number": True},
        }.get(fault or "", {})
    )
    if fault == "two-active":
        job["steps"].append({**step, "number": 9, "name": "different active step"})
    if fault == "duplicated-step":
        job["steps"].append({**step, "number": 9, "status": "queued"})
    if fault == "no-steps":
        del job["steps"]
    for key, value in {
        "GITHUB_RUN_ID": "22",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_JOB": job_name,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_WORKFLOW_SHA": w,
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF": "refs/pull/81/merge",
        "GITHUB_WORKFLOW_REF": runtime_surface.CADDY_REPOSITORY
        + "/.github/workflows/"
        + workflow
        + "@refs/pull/81/merge",
    }.items():
        monkeypatch.setenv(key, value)

    def read(path: str) -> Any:
        return {
            "/actions/runs/22/attempts/2": run,
            "/actions/runs/22": event,
            "/actions/workflows/" + workflow: {"id": 12, "path": ".github/workflows/" + workflow},
            "/actions/runs/22/attempts/2/jobs?per_page=100&page=1": {
                "total_count": 0 if fault == "missing-job" else 1,
                "jobs": [] if fault == "missing-job" else [job],
            },
        }[path]

    def verify() -> None:
        if job_name == "caddy-contract":
            runtime_surface.publisher_repair_run(
                read, receipt, w, workflow, job_name, current_step=step_name
            )
        else:
            runtime_surface.publisher_repair_run(read, receipt, w, workflow, job_name)

    if diagnostic:
        with pytest.raises(QualificationError, match="^" + diagnostic + "$"):
            verify()
        if diagnostic == "publisher_repair_actual_job_after_dispatch":
            log = capsys.readouterr().err
            assert "PRIVATE-UNTRUSTED" not in log
            flags = json.loads(log.removeprefix("Publisher repair current job rejected "))
            assert (flags["run"], flags["attempt"], flags["job_id"]) == (
                22,
                2,
                None if fault == "missing-job" else 32,
            )
            assert all(
                type(value) is bool
                for key, value in flags.items()
                if key not in {"run", "attempt", "job_id"}
            )
    else:
        verify()


def test_repair_native_wire_precision_and_fixed_dispatch_vector() -> None:
    from datetime import datetime, timezone
    from scripts.ci.prometheus_source_image import QualificationError

    timestamp = runtime_surface._publisher_time
    assert timestamp("2020-01-20T09:42:40.000-08:00") == datetime(
        2020, 1, 20, 17, 42, 40, tzinfo=timezone.utc
    )
    assert timestamp("2026-01-01T03:00:00.000001+03:00") > timestamp("2026-01-01T00:00:00Z")
    assert timestamp("2026-01-01T00:00:00.999999Z") < timestamp("2026-01-01T01:00:01+01:00")
    for invalid in (
        "2026-01-01T00:00:00",
        "2026-01-01T00:00:00-00:00",
        "2026-02-30T00:00:00Z",
        "2026-01-01T00:00:00.0000009Z",
        "2026-01-01T00:00:00+02:60",
    ):
        with pytest.raises(
            (ValueError, QualificationError), match="publisher_repair_native_timestamp"
        ):
            timestamp(invalid)
    # Independently recorded public coordinates and exact operand of GitHub dispatch 44938910620.
    material = {
        "pr": "2503",
        "base": "b96c7f66767d314e2952ea8180a7a3b499c16fce",  # pragma: allowlist secret - public Git commit
        "controller": "47dcc127c37e825fce3df5d188d684c560062324",  # pragma: allowlist secret - public Git commit
        "callers": "3146f3ef72ba8cd9f2a8a7974665a6cc21ed0f4e",  # pragma: allowlist secret - public Git commit
        "source": "e91033b4528a83782de3e7dc1e73e6def398348a",  # pragma: allowlist secret - public Git commit
        "q": "43808505545/14199242996",
        "s": "43810186398/14200227448",
        "c": "43811981051/14202207192",
        "zip": "sha256:4d0a39d1d1a94d5ef16ee57036366e36f1a5782e5e430222055eb57b2ce56dbf",
        "manifest": "sha256:873bc6cfae14edcf9f2acf2d81f9863f98ee8f78623125a7e02642a66e3bbe27",
    }
    fixed = (
        "repair-v1:3146f3ef72ba8cd9f2a8a7974665a6cc21ed0f4e:"
        "d26b25e741692d042271af53f3300ecd458bfd98282b5931871bf0b46b9bb260"  # pragma: allowlist secret - public dispatch SHA-256
    )
    assert runtime_surface.publisher_repair_input(material, "candidate-D") == fixed
    assert (
        runtime_surface.publisher_repair_input(
            {**material, "zip": "sha256:" + "0" * 64}, "candidate-D"
        )
        != fixed
    )


@pytest.mark.parametrize(
    "fault,queries",
    [
        (None, 4),
        ("forward", 6),
        ("time-only", 6),
        ("repeated", 6),
        ("backward", 4),
        ("new-terminal", 4),
        ("changed-field", 4),
        ("reordered", 4),
        ("missing-time", 4),
        ("jobs", 4),
    ],
)
def test_caddy_complete_two_page_workflow_lifecycle_evidence(
    fault: str | None, queries: int
) -> None:
    from copy import deepcopy

    path = (
        runtime_surface.CADDY_RUN_HISTORY_PATH
        if fault != "jobs"
        else "/actions/runs/1/jobs?filter=all"
    )
    key = "jobs" if fault == "jobs" else "workflow_runs"
    initial = [
        {
            "id": i + 1,
            "head_sha": "1" * 40,
            "run_attempt": 1,
            "updated_at": "2026-01-01T00:00:00Z",
            "conclusion": None,
            "status": "queued",
        }
        for i in range(145)
    ]
    second = deepcopy(initial)
    if fault:
        second[115].update(status="in_progress", updated_at="2026-01-01T01:00:00.001+01:00")
    if fault == "time-only":
        second[115]["status"] = "queued"
    elif fault == "backward":
        initial[115]["status"] = "completed"
        initial[115]["conclusion"] = "success"
    elif fault == "new-terminal":
        initial[115].update(status="completed", conclusion="success")
        second[115].update(status="completed", conclusion="failure")
    elif fault == "changed-field":
        second[115]["head_sha"] = "2" * 40
    elif fault == "reordered":
        second[115], second[116] = second[116], second[115]
    elif fault == "missing-time":
        del second[115]["updated_at"]
    third = deepcopy(second)
    if fault == "repeated":
        third[115].update(status="completed", conclusion="success")
    reads = []

    def read(endpoint: str) -> dict[str, Any]:
        observation = len(reads) // 2
        page = len(reads) % 2 + 1
        assert endpoint == f"{path}&per_page=100&page={page}"
        reads.append(endpoint)
        return {
            "total_count": 145,
            key: deepcopy((initial, second, third)[observation][(page - 1) * 100 : page * 100]),
        }

    if fault in (None, "forward", "time-only"):
        assert runtime_surface.caddy_stable_pages(read, path, key, lambda _: 1) == second
    else:
        with pytest.raises(ValueError, match="Caddy API same-count inventory replacement"):
            runtime_surface.caddy_stable_pages(read, path, key, lambda _: 1)
    assert len(reads) == queries


@pytest.mark.parametrize(
    ("window_slack", "job_slack", "source_slack", "eligible"),
    [
        (1, 0, 60, True),
        (0, 0, 60, False),
        (-1, 0, 60, False),
        (1, -1, 60, False),
        (-479, -479, 60, False),
        (60, 0, 1, True),
        (60, 0, 0, False),
        (60, 0, -1, False),
        (60, 0, -11040, False),
    ],
)
def test_prebuild_covers_usable_output_before_absolute_expiry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    window_slack: int,
    job_slack: int,
    source_slack: int,
    eligible: bool,
) -> None:
    from datetime import datetime, timedelta, timezone

    import yaml
    from tests.test_caddy_deploy_provenance import _caddy_budget_fixture
    from scripts.ci.prometheus_source_image import QualificationError

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return datetime(2026, 1, 2, tzinfo=timezone.utc)

    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/frontend-ci.yml"
    job = yaml.safe_load(workflow_path.read_bytes())["jobs"]["caddy-contract"]
    caps = {
        key.removeprefix("CADDY_PHASE_"): int(value)
        for key, value in job["env"].items()
        if key.startswith("CADDY_PHASE_")
    }
    build_idx = next(
        i
        for i, step in enumerate(job["steps"])
        if step["name"] == "Build source-patched Caddy candidate"
    )
    after_build = "\n".join(step.get("run", "") for step in job["steps"][build_idx + 1 :])
    for phase in ("SOURCE16", "FINAL_SUBJECT"):
        assert f'caddy_ci_phase("{phase}")' in after_build

    finished = {
        "SETUP",
        "COMPILER_BOOTSTRAP",
        "COMPILER_WORK",
        "COMPILER_CLEANUP",
        "METADATA_UPLOAD",
    }
    assert finished <= caps.keys()
    required = sum(value for phase, value in caps.items() if phase not in finished)
    clock_now = 20000.0
    monkeypatch.setattr(runtime_surface, "datetime", Clock)
    monkeypatch.setattr(runtime_surface.time, "monotonic", lambda: clock_now)
    for phase, cap in caps.items():
        monkeypatch.setenv("CADDY_PHASE_" + phase, str(cap))
    monkeypatch.setenv("GITHUB_RETENTION_DAYS", "90")
    expiry = Clock.now() + timedelta(seconds=required + window_slack)
    source_horizon = Clock.now() + timedelta(seconds=required + source_slack)
    state = _caddy_budget_fixture(tmp_path, monkeypatch)
    state["mode"] = "build"
    state["publisher_repair"] = {
        "started": runtime_surface._publisher_utc(expiry - timedelta(days=1)),
        "expires": runtime_surface._publisher_utc(expiry),
        "source_horizon": runtime_surface._publisher_utc(source_horizon),
    }
    state["budget"].update(
        started=clock_now - (sum(caps.values()) - required - job_slack),
        charged={phase: caps[phase] if phase in finished else 0 for phase in caps},
    )
    ledger = tmp_path / "caddy-admission/admission.json"
    ledger.write_text(json.dumps(state))
    if eligible:
        assert runtime_surface.caddy_ci_charge_action("BUILD") == caps["BUILD"]
    else:
        with pytest.raises(QualificationError, match="^publisher_repair_build_usable_window$"):
            runtime_surface.caddy_ci_charge_action("BUILD")
    budget = json.loads(ledger.read_bytes())["budget"]
    assert budget["charged"]["BUILD"] == (caps["BUILD"] if eligible else 0)
    assert ("BUILD" in budget["action_deadlines"]) is eligible


@pytest.mark.parametrize(
    ("requested", "native", "horizon", "diagnostic"),
    [
        ("90", "7", (20, 0), "publisher_repair_retention_horizon"),
        ("7", "90", (20, 0), "publisher_repair_retention_horizon"),
        ("90", "7", (7, 0), None),
        ("90", "7", (7, 1), "publisher_repair_retention_horizon"),
        ("90", "90", (20, 0), None),
        ("90", None, (20, 0), "publisher_repair_retention_days"),
        ("90", "0", (20, 0), "publisher_repair_retention_days"),
    ],
)
def test_caddy_repair_build_checks_run_native_retention_before_debit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    native: str | None,
    horizon: tuple[int, int],
    diagnostic: str | None,
) -> None:
    from datetime import datetime, timedelta, timezone
    from scripts.ci.prometheus_source_image import QualificationError
    from tests.test_caddy_deploy_provenance import _caddy_budget_fixture

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return datetime(2026, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(runtime_surface, "datetime", Clock)
    monkeypatch.setattr(runtime_surface.time, "monotonic", lambda: 20000.0)
    state = _caddy_budget_fixture(tmp_path, monkeypatch)
    state.update(
        mode="build",
        publisher_repair={
            "started": runtime_surface._publisher_utc(Clock.now()),
            "expires": runtime_surface._publisher_utc(Clock.now() + timedelta(days=1)),
            "source_horizon": runtime_surface._publisher_utc(
                Clock.now() + timedelta(days=horizon[0], microseconds=horizon[1])
            ),
        },
    )
    ledger = tmp_path / "caddy-admission/admission.json"
    ledger.write_text(json.dumps(state))
    monkeypatch.setenv("CADDY_REPAIR_RETENTION_DAYS", requested)
    if native is None:
        monkeypatch.delenv("GITHUB_RETENTION_DAYS", raising=False)
    else:
        monkeypatch.setenv("GITHUB_RETENTION_DAYS", native)
    if diagnostic is None:
        assert runtime_surface.caddy_ci_charge_action("BUILD") == 1800
    else:
        with pytest.raises(QualificationError, match=f"^{diagnostic}$"):
            runtime_surface.caddy_ci_charge_action("BUILD")
    budget = json.loads(ledger.read_bytes())["budget"]
    assert budget["charged"]["BUILD"] == (1800 if diagnostic is None else 0)
    assert ("BUILD" in budget["action_deadlines"]) is (diagnostic is None)


@pytest.mark.parametrize(
    "remaining,eligible", [(555, False), (600, False), (659, False), (660, True), (870, True)]
)
def test_caddy_upload_retains_actual_verification_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remaining: float, eligible: bool
) -> None:
    import os
    from tests.test_caddy_deploy_provenance import _caddy_budget_fixture

    now = 20000.0
    monkeypatch.setattr(runtime_surface.time, "monotonic", lambda: now)
    state = _caddy_budget_fixture(tmp_path, monkeypatch)
    caps = {
        key.removeprefix("CADDY_PHASE_"): int(value)
        for key, value in os.environ.items()
        if key.startswith("CADDY_PHASE_")
    }
    state["budget"].update(
        started=now + remaining - sum(caps.values()),
        charged={k: (0 if k in ("UPLOAD", "SAFETY") else v) for k, v in caps.items()},
    )
    ledger = tmp_path / "caddy-admission/admission.json"
    ledger.write_text(json.dumps(state))
    if eligible:
        assert runtime_surface.caddy_ci_charge_action("UPLOAD", 540, reserve=60) == 540
    else:
        with pytest.raises(
            ValueError, match="^Caddy complete action ceiling is unavailable: UPLOAD$"
        ):
            runtime_surface.caddy_ci_charge_action("UPLOAD", 540, reserve=60)
    budget = json.loads(ledger.read_bytes())["budget"]
    assert budget["charged"]["UPLOAD"] == (540 if eligible else 0)
    assert ("UPLOAD" in budget["action_deadlines"]) is eligible
    if eligible:
        now += 540 + 60  # Full uploader ceiling and the bounded scheduler handoff.
        with runtime_surface.caddy_ci_phase("UPLOAD") as verify:
            assert verify(float("inf")) == 60


@pytest.mark.parametrize(
    "name,mib",
    [
        ("source-decision.json", 2),
        ("admission.json", 2),
        ("controls/native-controls.json", 2),
        ("loaded-runtime/observation.json", 2),
        ("strict-control.raw.json", 32),
        ("candidate.json", 2),
        ("candidate.docker.tar", 512),
        ("original-producer.json", 2),
    ],
)
def test_caddy_repair_member_size_before_any_zip(tmp_path: Path, name: str, mib: int) -> None:
    import time
    from scripts.ci.prometheus_source_image import QualificationError

    source = tmp_path / "evidence"
    member = source / name
    member.parent.mkdir(parents=True)
    limit = mib * 1024**2
    runtime_surface._require_caddy_repair_member_size(name, limit)
    with pytest.raises(QualificationError, match="^publisher_repair_bounded_native_member$"):
        runtime_surface._require_caddy_repair_member_size(name, 0)
    with member.open("wb") as handle:
        handle.truncate(limit + 1)
    target = tmp_path / "caddy-contract-evidence.zip"
    # An exclusive target collision would otherwise fail first, before packaging.
    target.write_bytes(b"original")
    with pytest.raises(QualificationError, match="^publisher_repair_bounded_native_member$"):
        runtime_surface.pack_caddy_repair_evidence(source, target, time.monotonic() + 10)
    assert target.read_bytes() == b"original"


@pytest.mark.parametrize(
    ("action", "fault", "diagnostic"),
    [
        ("candidate-D", None, None),
        ("contract", None, None),
        ("ordinary", None, None),
        ("candidate-D", "directory", "publisher_repair_zip_directory_bound"),
        ("candidate-D", "wrong-image-bytes", "publisher_repair_retained_build_bytes"),
        ("candidate-D", "missing-strict", "publisher_repair_missing_checked_input_record"),
        ("contract", "cleanup-failed", "publisher_repair_retained_native_decision"),
        ("contract", "missing-original", "publisher_repair_missing_checked_input_record"),
    ],
)
def test_caddy_qualifying_upload_step_checks_same_zip_as_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    fault: str | None,
    diagnostic: str | None,
) -> None:
    import io
    import zipfile
    from scripts.ci.prometheus_source_image import QualificationError
    from tests.test_caddy_deploy_provenance import _caddy_budget_fixture, _caddy_inline

    head = "3" * 40
    material = {
        "pr": "81",
        "base": "1" * 40,
        "controller": "2" * 40,
        "callers": head,
        **_repair_subject_fixture()[0],
    }
    pr = {"number": 81, "head": {"ref": "fixture/repair"}}
    api = _DispatchNativeFixture(pr, material)
    api.add(api.projection())
    api.fault = fault
    run_id = 73 if action == "candidate-D" else 75
    projection = api.projection(run_id, "contract" if action == "ordinary" else action)
    api.add(projection)
    run, _, artifact, original_zip = api.records[run_id]
    state = _caddy_budget_fixture(tmp_path, monkeypatch)
    state["publisher_repair"] = projection
    ledger = tmp_path / "caddy-admission/admission.json"
    ledger.write_text(json.dumps(state))
    output = tmp_path / "step-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_RUN_ID", str(run_id))
    monkeypatch.setenv("GITHUB_SHA", head)
    monkeypatch.setenv("CADDY_REPAIR_TRANSPORT", "false" if action == "ordinary" else "true")
    path = tmp_path / "caddy-contract-evidence.zip"
    if fault == "directory":
        monkeypatch.setattr(runtime_surface, "_CADDY_REPAIR_DIRECTORY_MAX", 100)
    missing = {
        "missing-original": "original-producer.json",
        "missing-strict": "strict-control.raw.json",
    }.get(fault or "")
    with zipfile.ZipFile(io.BytesIO(original_zip)) as z:
        for name in z.namelist():
            if name != missing:
                dest = tmp_path / "caddy-contract" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))

    code = compile(
        _caddy_inline("Charge Upload Caddy contract evidence budget"),
        "<actual-repair-upload-budget>",
        "exec",
    )
    if diagnostic:
        with pytest.raises(QualificationError, match=f"^{diagnostic}$"):
            exec(code, {})
        assert not path.exists() and not output.exists()
        assert json.loads(ledger.read_bytes())["budget"]["charged"]["UPLOAD"] == 0
        return
    exec(code, {})
    if action == "ordinary":
        assert not path.exists() and not output.exists()
        return
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert output.read_text().splitlines() == [
        "repair_zip=true",
        f"bytes={len(raw)}",
        f"digest={digest}",
        "horizon=" + projection["source_horizon"],
    ]
    artifact.update(size_in_bytes=len(raw), digest="sha256:" + digest)
    record = runtime_surface._publisher_artifact_record(lambda _: raw, artifact, run, {})
    assert record["input"] == projection["input"] and record["action"] == action


def test_caddy_repair_exact_zip_cap_and_mutating_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import random
    import time
    import zipfile
    from scripts.ci import prometheus_source_image as native

    root = tmp_path / "source"
    root.mkdir()
    target = tmp_path / "caddy-contract-evidence.zip"
    (root / ".private").mkdir()
    (root / ".private/unpublished.txt").write_text("fixture excluded by the native default")
    compressed = root / "large.txt"
    compressed.write_bytes(b"a" * 330000)
    other = root / "nested"
    other.mkdir()
    binary = other / "data"
    binary.write_bytes(random.Random(71).randbytes(40000))
    binary.chmod(0o750)
    size, digest = runtime_surface.pack_caddy_repair_evidence(root, target, time.monotonic() + 10)
    assert (
        target.stat().st_size == size
        and hashlib.sha256(target.read_bytes()).hexdigest() == digest
        and size < compressed.stat().st_size
    )
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == {"large.txt", "nested/data"}
        assert (
            z.read("nested/data") == binary.read_bytes()
            and z.getinfo("nested/data").external_attr >> 16 == binary.stat().st_mode
        )
    target.unlink()
    monkeypatch.setattr(runtime_surface, "_REPAIR_ARCHIVE_MAX", size)
    assert runtime_surface.pack_caddy_repair_evidence(root, target, time.monotonic() + 10) == (
        size,
        digest,
    )
    target.unlink()
    monkeypatch.setattr(runtime_surface, "_REPAIR_ARCHIVE_MAX", size - 1)
    with pytest.raises(native.QualificationError, match="publisher_repair_zip_transport_bound"):
        runtime_surface.pack_caddy_repair_evidence(root, target, time.monotonic() + 10)
    assert not target.exists()
    monkeypatch.setattr(runtime_surface, "_REPAIR_ARCHIVE_MAX", size * 2)
    original = native.check_deadline

    def mutate(deadline: float) -> None:
        original(deadline)
        if target.exists() and not (root / "late").exists():
            (root / "late").write_bytes(b"changed during packing")

    monkeypatch.setattr(native, "check_deadline", mutate)
    with pytest.raises(native.QualificationError, match="publisher_repair_transport_source_drift"):
        runtime_surface.pack_caddy_repair_evidence(root, target, time.monotonic() + 10)
    assert not target.exists()


@pytest.mark.parametrize(
    "fault", [None, "digest", "size", "missing-size", "expiry", "different-run"]
)
def test_caddy_upload_observation_binds_actual_server_transport(fault: str | None) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    digest = hashlib.sha256(b"native prepacked bytes").hexdigest()
    env = {
        "CADDY_REPAIR_ZIP_BYTES": "184",
        "CADDY_UPLOADED_ID": "61",
        "CADDY_REPAIR_ZIP_SHA256": digest,
        "CADDY_UPLOADED_DIGEST": digest,
        "CADDY_SOURCE_HORIZON": "2027-02-14T05:10:32Z",
        "GITHUB_RUN_ID": "77",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
    }
    record = {
        "name": "caddy-contract-evidence.zip",
        "id": 61,
        "size_in_bytes": 185 if fault == "size" else 184,
        "expired": False,
        "expires_at": (
            "2027-02-14T05:10:31.999999Z" if fault == "expiry" else "2027-02-14T06:10:32+01:00"
        ),
        "digest": "sha256:" + ("0" * 64 if fault == "digest" else digest),
        "workflow_run": {
            "id": 72 if fault == "different-run" else 77,
            "head_sha": "a" * 40,
            "repository_id": 1043311030,
            "head_repository_id": 1043311030,
        },
    }
    if fault == "missing-size":
        del record["size_in_bytes"]
    if fault is None:
        runtime_surface.verify_repair_evidence_upload(record, env)
    else:
        with pytest.raises(QualificationError, match="publisher_repair_uploaded_transport"):
            runtime_surface.verify_repair_evidence_upload(record, env)


def _fixture_git(directory: Path, *args: str, data: bytes | None = None) -> bytes:
    import shutil
    from scripts.orchestration.creative_code_patch_workspace import (
        git_env_without_parent_state,
        safe_git_config_args,
    )

    git = shutil.which("git")
    assert git
    return subprocess.run(
        [git, *safe_git_config_args(), "-C", str(directory), *args],
        input=data,
        env=git_env_without_parent_state(),
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout


@lru_cache(maxsize=1024)
def _fixture_git_object_id(kind: str, contents: bytes) -> str:
    """Use Git's object framing outside any checkout, sharing immutable IDs across test cases."""
    root = Path(Path.cwd().anchor)
    return _fixture_git(root, "hash-object", "-t", kind, "--stdin", data=contents).decode().strip()


def _git_tree_fixture(repository: Path | None = None) -> tuple[dict[str, Any], Any, Any]:
    """Build content-addressed Git blobs, trees and commits for the native reader fixtures."""
    import base64

    if repository is not None:
        repository.mkdir()
        _fixture_git(repository, "init", "-q", "--object-format=sha1")
    stored = set()

    def git_object(kind: str, contents: bytes) -> str:
        oid = _fixture_git_object_id(kind, contents)
        if repository is not None and oid not in stored:
            written = _fixture_git(
                repository, "hash-object", "-t", kind, "-w", "--stdin", data=contents
            )
            assert written.decode().strip() == oid
            stored.add(oid)
        return oid

    endpoints: dict[str, Any] = {}

    def blob(raw: bytes) -> str:
        oid = git_object("blob", raw)
        endpoints["/git/blobs/" + oid] = {
            "sha": oid,
            "size": len(raw),
            "encoding": "base64",
            "content": base64.b64encode(raw).decode(),
        }
        return oid

    def tree(files: dict[str, tuple[str, bytes]]) -> str:
        children: dict[str, dict[str, tuple[str, bytes]]] = {}
        rows = []
        for path, (mode, content) in files.items():
            first, slash, rest = path.partition("/")
            if slash:
                children.setdefault(first, {})[rest] = (mode, content)
            else:
                rows.append({"path": first, "mode": mode, "type": "blob", "sha": blob(content)})
        for name, members in children.items():
            rows.append({"path": name, "mode": "040000", "type": "tree", "sha": tree(members)})
        rows.sort(key=lambda row: (row["path"] + ("/" if row["type"] == "tree" else "")).encode())
        oid = git_object(
            "tree",
            b"".join(
                row["mode"].lstrip("0").encode()
                + b" "
                + row["path"].encode()
                + b"\0"
                + bytes.fromhex(row["sha"])
                for row in rows
            ),
        )
        endpoints["/git/trees/" + oid] = {"sha": oid, "tree": rows, "truncated": False}
        return oid

    def node(
        parent: str | None,
        files: dict[str, tuple[str, bytes]],
        label: str,
        second_parent: str | None = None,
    ) -> str:
        tree_oid = tree(files)
        parents = [revision for revision in (parent, second_parent) if revision is not None]
        parent_header = "".join("parent " + revision + "\n" for revision in parents)
        identity = "Native Fixture <fixture@example.invalid> 1770000000 +0000"
        oid = git_object(
            "commit",
            (
                f"tree {tree_oid}\n{parent_header}author {identity}\ncommitter {identity}\n\n{label}\n"
            ).encode(),
        )
        endpoints["/git/commits/" + oid] = {
            "sha": oid,
            "parents": [{"sha": revision} for revision in parents],
            "tree": {"sha": tree_oid},
        }
        return oid

    return endpoints, blob, node


def _prometheus_repair_git_fixture(
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
    *,
    historical: bool = False,
    repository: Path | None = None,
    dispatched: bool = False,
    renewal: bool = False,
) -> tuple[Any, dict[str, Any], dict[str, str]]:
    """Closed immutable Git-response fixture, using real blob content addressing and original Q/S/C."""
    from scripts.ci import prometheus_source_image as prom

    endpoints, blob, node = _git_tree_fixture(repository)
    incumbent = "a" * 40
    subject, accepted = _repair_subject_fixture()
    repo = {"id": 1043311030, "full_name": runtime_surface.CADDY_REPOSITORY}
    ci = ".github/workflows/ci.yml"
    old_prom = "b" * 40
    old_finding = {
        "type": "Hex High Entropy String",
        "filename": ci,
        "hashed_secret": hashlib.sha1(old_prom.encode(), usedforsecurity=False).hexdigest(),
        "is_verified": fault == "baseline-verified-old",
        "line_number": 1264,
    }
    other_finding = {**old_finding, "hashed_secret": "f" * 40, "line_number": 99}
    alias = b"          CONTROLLER_SHA: *prometheus_test_revision"
    public_marker = b"# pragma: allowlist secret - public trusted control commit"
    anchor = b"          ref: &prometheus_test_revision "

    def baseline(day: str, *, retired: bool = False) -> bytes:
        rows = [dict(other_finding)] if retired else [dict(other_finding), dict(old_finding)]
        return prom.canonical_data(
            {"generated_at": "2026-01-" + day + "T00:00:00Z", "results": {ci: rows}}
        )

    original = {path: ("100644", path.encode()) for path in runtime_surface._PROM_REPAIR_PATHS}
    am = "scripts/ci/fetch_docker_source_artifacts.py"
    original[am] = (
        "100644",
        ("_ALERT_ACCEPTED_CANDIDATE: dict = " + repr(accepted) + "\n").encode(),
    )
    ps = runtime_surface._PROM_SOURCE
    pt = runtime_surface._PROM_TEST
    nightly = runtime_surface._PROM_NIGHTLY
    original[nightly] = (
        "100644",
        b"header\n          CONTROLLER_SHA: "
        + old_prom.encode()
        + b" "
        + public_marker
        + b"\nread-only command\n",
    )
    original[".secrets.baseline"] = ("100644", baseline("01"))

    def digest(raw: bytes) -> bytes:
        return hashlib.sha256(raw).hexdigest().encode()

    for wrapper in runtime_surface._PROM_REPAIR_WRAPPERS:
        raw = b'PROMETHEUS_CONTRACT_HELPER_SHA256="' + digest(original[ps][1]) + b'"\n'
        if "QUICK_FIX" not in wrapper:
            raw += b'ALERTMANAGER_CONTRACT_HELPER_SHA256="' + digest(original[am][1]) + b'"\n'
        original[wrapper] = ("100755", raw)
    caller_names = (".github/workflows/ci.yml", ".github/workflows/cd.yml")
    for name in caller_names:
        raw = f"  ALERTMANAGER_CONTROLLER_SOURCE: '{incumbent}'\n"
        for key, label in (("qualification", "q"), ("support", "s"), ("candidate", "c")):
            run, artifact = subject[label].split("/")
            raw += (
                f"--alertmanager-{key}-run {run} --alertmanager-{key}-artifact {artifact} "
                + chr(92)
                + f"\n  --alertmanager-{key}-source {subject['source']}\n"
            )
        caller = raw.encode()
        if name == ci:
            caller += anchor + old_prom.encode() + b" " + public_marker + b"\n" + alias + b"\n"
        original[name] = ("100644", caller)
    for name in ("staging", "production", "production.selfhosted"):
        original["deploy/docker-compose." + name + ".yaml"] = (
            "100644",
            (
                "  alertmanager:\n    image: ghcr.io/katsiarynakavaleuskaya/pulseplate@"
                + subject["manifest"]
                + "\n"
            ).encode(),
        )
    for stable in ("scripts/ops/notify_premium_alias_checkpoint_failure.py", "tests/__init__.py"):
        original[stable] = ("100644", b"stable fixture input")
    b = node(None, original, "B")
    hook = {**original, ".secrets.baseline": ("100644", baseline("02"))}
    if fault == "hook-extra":
        hook["transient.py"] = ("100644", b"extra")
    h = node("0" * 40 if fault == "wrong-base" else b, hook, "H")
    pair = {**hook, ps: ("100644", b"designated P"), pt: ("100644", b"P tests")}
    monkeypatch.setattr(
        runtime_surface, "_PROM_REPAIR_SOURCE_BLOBS", {ps: blob(pair[ps][1]), pt: blob(pair[pt][1])}
    )
    if fault == "wrong-P":
        pair[pt] = ("100644", b"foreign tests")
    p = node(b if fault == "wrong-H" else h, pair, "P")
    for constant, value in (
        ("_PROM_REPAIR_BASE", b),
        ("_PROM_REPAIR_HOOK", h),
        ("_PROM_REPAIR_SOURCE", p),
    ):
        monkeypatch.setattr(runtime_surface, constant, value)
    final = pair.copy()
    for name in runtime_surface._PROM_REPAIR_PATHS - {
        ps,
        pt,
        ".secrets.baseline",
        *runtime_surface._PROM_REPAIR_WRAPPERS,
    }:
        final[name] = ("100644", final[name][1] + b"\n# reviewed repair\n")
    for name in runtime_surface._PROM_REPAIR_WRAPPERS:
        before = original[name][1]
        after = before.replace(digest(original[ps][1]), digest(final[ps][1])).replace(
            digest(original[am][1]), digest(final[am][1])
        )
        final[name] = ("100755", after)
    final[nightly] = ("100644", original[nightly][1].replace(old_prom.encode(), p.encode()))
    if fault == "nightly-extra-byte":
        final[nightly] = ("100644", final[nightly][1] + b"# extra\n")
    if fault == "nightly-mode":
        final[nightly] = ("100755", final[nightly][1])
    if fault == "nightly-wrong-target":
        final[nightly] = ("100644", original[nightly][1].replace(old_prom.encode(), b"e" * 40))
    new_alias = alias if fault == "baseline-unannotated" else alias + b"  " + public_marker
    final[ci] = (
        "100644",
        final[ci][1]
        .replace(anchor + old_prom.encode(), anchor + p.encode())
        .replace(alias + b"\n", new_alias + b"\n"),
    )
    final[".secrets.baseline"] = ("100644", baseline("03", retired=True))
    if fault in (
        "baseline-extra-remove",
        "baseline-extra-add",
        "baseline-other-change",
        "baseline-p-ref",
    ):
        damaged = json.loads(final[".secrets.baseline"][1])
        rows = damaged["results"][ci]
        if fault == "baseline-extra-remove":
            rows.clear()
        elif fault == "baseline-extra-add":
            rows.append({**other_finding, "hashed_secret": "e" * 40})
        elif fault == "baseline-p-ref":
            rows.append(
                {
                    **old_finding,
                    "hashed_secret": hashlib.sha1(p.encode(), usedforsecurity=False).hexdigest(),
                }
            )
        else:
            rows[0]["is_verified"] = True
        final[".secrets.baseline"] = ("100644", prom.canonical_data(damaged))
    harness = runtime_surface._PROM_HARNESS
    first_harness = final[harness]
    corrected_harness = ("100644", first_harness[1] + b"# exact capture diagnostic tests\n")
    monkeypatch.setattr(runtime_surface, "_PROM_FIRST_HARNESS", blob(first_harness[1]))
    caller_blobs = {
        name: blob(final[name][1]) for name in runtime_surface._PROM_REPAIR_CALLER_BLOBS
    }
    caller_blobs[harness] = blob(corrected_harness[1])
    monkeypatch.setattr(runtime_surface, "_PROM_REPAIR_CALLER_BLOBS", caller_blobs)
    if fault == "stale-prom-caller":
        final[caller_names[0]] = ("100644", original[caller_names[0]][1] + b"# stale P\n")
    if fault == "substituted-P":
        final[ps] = ("100644", b"different helper")
    if fault == "substituted-harness":
        final["tests/test_notify_premium_alias_checkpoint_failure.py"] = (
            "100644",
            b"other harness",
        )
    if fault in ("wrong-wrapper", "extra-wrapper-byte", "wrapper-mode"):
        name = runtime_surface._PROM_REPAIR_WRAPPERS[-1]
        final[name] = (
            "100644" if fault == "wrapper-mode" else "100755",
            original[name][1] + b"# stale\n" if fault == "wrong-wrapper" else final[name][1] + b" ",
        )
    if fault == "unapproved-path":
        final[".github/workflows/frontend-ci.yml"] = ("100644", b"previously allowed generic path")
    if fault == "baseline-policy":
        final[".secrets.baseline"] = (
            "100644",
            prom.canonical_data(
                {"generated_at": "2026-01-03T00:00:00Z", "results": {}, "new_policy": True}
            ),
        )
    parent = p
    if fault == "nightly-transient":
        parent = node(
            p,
            {**pair, nightly: ("100644", final[nightly][1] + b"# temporary mutation")},
            "unapproved nightly change",
        )
    if fault in ("hook-before-U", "restored-retired-alias"):
        intermediate = {**pair, ".secrets.baseline": ("100644", baseline("03", retired=True))}
        parent = node(p, intermediate, "native baseline-only hook")
        if fault == "restored-retired-alias":
            parent = node(
                parent,
                {**intermediate, ".secrets.baseline": ("100644", baseline("04"))},
                "restore retired finding",
            )
    correction_path = "tests/test_docker_runtime_dependency_surface.py"
    if fault == "edit-revert":
        temporary = {**pair, "scripts/AGENTS.md": ("100644", b"transient text")}
        parent = node(p, temporary, "temporary edit")
        parent = node(parent, pair, "revert to base bytes")
    if fault == "corrected-pre-W":
        interim = {**pair, correction_path: ("100644", b"first regression coverage")}
        parent = node(p, interim, "first scoped test implementation")
    first_publication = None
    if fault in (
        "corrected-post-W",
        "prior-W-only",
        "partial-restore",
        "prior-no-fix",
        "docs-before-restore",
        "docs-with-restore",
        "premature-harness",
        "regressed-harness",
        "stale-final-harness",
        "wrong-first-publication",
        "corrected-AM-helper",
        "wrong-prior-W",
        "prior-outside",
        "prior-P",
        "prior-harness",
        "prior-wrapper",
    ):
        first = {**final, correction_path: ("100644", b"first regression coverage")}
        if fault in ("prior-no-fix", "corrected-AM-helper"):
            first = final.copy()
        if fault in ("docs-before-restore", "docs-with-restore"):
            first = {**final, "scripts/AGENTS.md": ("100644", b"earlier instructions")}
        if fault == "corrected-AM-helper":
            first[am] = ("100644", final[am][1] + b"# earlier checked implementation\n")
            for wrapper in runtime_surface._PROM_REPAIR_WRAPPERS[:2]:
                first[wrapper] = (
                    "100755",
                    final[wrapper][1].replace(digest(final[am][1]), digest(first[am][1])),
                )
        if fault == "prior-outside":
            first["outside.txt"] = ("100644", b"foreign path")
        if fault == "prior-P":
            first[ps] = ("100644", b"substituted protected source")
        final[harness] = corrected_harness
        if fault == "premature-harness":
            first[harness] = corrected_harness
        if fault == "stale-final-harness":
            final[harness] = first_harness
        if fault == "prior-harness":
            first[harness] = (
                "100644",
                b"unreviewed protected harness",
            )
        if fault == "prior-wrapper":
            first["scripts/deploy.sh"] = ("100755", b"other wrapper")
        k1 = node(p, first, "K1")
        pinned = {
            **first,
            **{
                name: ("100644", first[name][1].replace(incumbent.encode(), k1.encode()))
                for name in caller_names
            },
        }
        if fault == "wrong-prior-W":
            pinned[caller_names[1]] = (
                "100644",
                pinned[caller_names[1]][1] + b"other caller change",
            )
        w1 = node(k1, pinned, "W1")
        parent = w1
        first_publication = (k1, w1 if fault != "wrong-first-publication" else "f" * 40)
        if fault == "regressed-harness":
            advanced = {**pinned, harness: corrected_harness}
            parent = node(w1, advanced, "advance to corrected harness")
            parent = node(parent, pinned, "restore old harness")
        if fault == "docs-before-restore":
            docs_only = {**pinned, "scripts/AGENTS.md": final["scripts/AGENTS.md"]}
            parent = node(w1, docs_only, "update instructions before restoring callers")
        if fault == "partial-restore":
            partial = {**pinned, caller_names[0]: final[caller_names[0]]}
            parent = node(w1, partial, "restore only one pin")
    if fault == "rewound-controller":
        parent = h
    k = node(parent, final, "K", b if fault == "ambiguous-controller" else None)
    successor = {
        **final,
        **{
            name: ("100644", final[name][1].replace(incumbent.encode(), k.encode()))
            for name in caller_names
        },
    }
    if fault == "second-W-edit":
        successor["scripts/AGENTS.md"] = ("100644", b"extra W byte")
    if fault == "stale-W-slot":
        name = caller_names[1]
        successor[name] = ("100644", successor[name][1] + b"# extra W caller byte\n")
    w = node(k, successor, "W")
    original_k, original_w = first_publication or (k, w)
    monkeypatch.setattr(runtime_surface, "_PROM_FIRST_CONTROLLER", original_k)
    monkeypatch.setattr(runtime_surface, "_PROM_FIRST_CALLERS", original_w)
    endpoints[f"/commits/{w}?per_page=100&page=1"] = {
        "sha": w,
        "parents": [{"sha": k}],
        "files": [{"filename": name, "status": "modified"} for name in caller_names],
    }
    mapping = "docs/review/PR_81_FIXED_MAPPING.md"
    mapped = {**successor, mapping: ("100644", b"mapping")}
    close = node(w, mapped, "Mapping")
    endpoints[f"/commits/{close}?per_page=100&page=1"] = {
        **endpoints["/git/commits/" + close],
        "files": [{"filename": mapping, "status": "added", "sha": blob(b"mapping")}],
        "commit": {"tree": endpoints["/git/commits/" + close]["tree"]},
    }
    landed = (
        mapped if fault != "altered-squash" else {**mapped, "unrelated": ("100644", b"changed")}
    )
    squash = node(b, landed, "squash")
    pr = {
        "number": 81,
        "base": {"ref": "main", "sha": b, "repo": repo},
        "head": {
            "ref": runtime_surface._PROM_REPAIR_BRANCH,
            "sha": close if historical else w,
            "repo": repo,
        },
        "state": "closed" if historical else "open",
        "merged": historical,
        "merge_commit_sha": squash,
        "created_at": "2025-12-01T00:00:00Z",
        "merged_at": "2026-01-03T00:00:00Z" if renewal else "2026-01-02T00:00:00Z",
    }

    endpoints["/git/ref/heads/main"] = {
        "ref": "refs/heads/main",
        "object": {"type": "commit", "sha": b},
    }
    material = {"pr": "81", "base": b, "controller": k, "callers": w, **subject}
    chain = []
    at = k
    while at != b and "/git/commits/" + at in endpoints:
        n = endpoints["/git/commits/" + at]
        chain.append(n)
        at = n["parents"][0]["sha"]
    endpoints[f"/compare/{b}...{k}"] = {
        "status": "ahead" if at == b else "diverged",
        "base_commit": {"sha": b},
        "merge_base_commit": {"sha": at},
        "behind_by": 0,
        "ahead_by": len(chain),
        "total_commits": len(chain),
        "commits": list(reversed(chain)),
    }
    native = _DispatchNativeFixture(pr, material, fault)

    for path in caller_names:
        oid = blob(final[path][1])
        endpoints[f"/contents/{path}?ref={k}"] = {
            **endpoints["/git/blobs/" + oid],
            "type": "file",
            "path": path,
        }
    root_tree = endpoints["/git/commits/" + k]["tree"]["sha"]
    endpoints["/git/trees/" + root_tree + "?recursive=1"] = {
        "sha": root_tree,
        "truncated": False,
        "tree": [
            {"path": path, "mode": mode, "type": "blob", "sha": blob(raw)}
            for path, (mode, raw) in final.items()
        ],
    }
    endpoints[f"/commits/{squash}/pulls?per_page=2"] = [{"number": 81}]
    if repository is not None:
        _fixture_git(repository, "checkout", "--detach", "-q", squash if historical else w)
    if fault == "prior-W-only":
        old = _DispatchNativeFixture(pr, {**material, "controller": k1, "callers": w1})
        old.add(old.projection(run=74, producer=74))
        native.records.update(old.records)
        assert (
            native.read(
                f"/actions/workflows/frontend-ci.yml/runs?event=workflow_dispatch&head_sha={w1}&per_page=100&page=1"
            )["total_count"]
            == 1
        )
    if dispatched:
        from datetime import datetime, timezone

        class FixtureClock(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:
                return cls(2026, 1, 7 if historical else 1, 1, tzinfo=timezone.utc)

        monkeypatch.setattr(runtime_surface, "datetime", FixtureClock)
    if dispatched and fault != "prior-W-only":
        if renewal and fault == "corrected-post-W":
            original = _DispatchNativeFixture(
                pr, {**material, "controller": original_k, "callers": original_w}
            )
            original.add(original.projection())
            native.records.update(original.records)
        else:
            native.add(native.projection(started="2026-01-01T00:00:00Z"))
        if renewal:
            native.add(native.projection(run=74, action="contract", started="2026-01-02T00:00:00Z"))
        if historical:
            review_date = "2026-01-02" if renewal else "2026-01-01"
            for run_number, ((workflow, jobname), steps) in enumerate(
                runtime_surface._REPAIR_NATIVE_STEPS.items(), 22
            ):
                flow_id = 123 if workflow == "cd.yml" else 124
                workflow_path = ".github/workflows/" + workflow
                endpoints["/actions/workflows/" + workflow] = {"id": flow_id, "path": workflow_path}
                row = {
                    "id": run_number,
                    "run_attempt": 1,
                    "event": "pull_request",
                    "head_sha": w,
                    "workflow_id": flow_id,
                    "repository": repo,
                    "head_repository": repo,
                    "path": workflow_path,
                    "head_branch": pr["head"]["ref"],
                    "pull_requests": [{**pr, "head": {**pr["head"], "sha": w}}],
                    "created_at": f"{review_date}T01:00:00Z",
                    "run_started_at": f"{review_date}T01:00:05Z",
                    "status": "completed",
                    "conclusion": "success",
                }
                for at, rows in ((w, [row]), (close, [])):
                    endpoints[
                        f"/actions/workflows/{workflow}/runs?event=pull_request&head_sha={at}&per_page=100&page=1"
                    ] = {"total_count": len(rows), "workflow_runs": rows}
                endpoints[f"/actions/runs/{run_number}/attempts/1"] = row
                endpoints[f"/actions/runs/{run_number}/attempts/1/jobs?per_page=100&page=1"] = {
                    "total_count": 1,
                    "jobs": [
                        {
                            "id": run_number + 100,
                            "name": jobname,
                            "run_id": run_number,
                            "run_attempt": 1,
                            "head_sha": w,
                            "started_at": f"{review_date}T01:01:00Z",
                            "completed_at": f"{review_date}T01:30:00Z",
                            "status": "completed",
                            "conclusion": "success",
                            "steps": [
                                {
                                    "name": step,
                                    "started_at": f"{review_date}T01:02:00Z",
                                    "completed_at": f"{review_date}T01:15:00Z",
                                    "status": "completed",
                                    "conclusion": (
                                        "skipped"
                                        if fault == "missing-CI" and workflow == "ci.yml"
                                        else "success"
                                    ),
                                }
                                for step in steps
                            ],
                        }
                    ],
                }

    def read(path: str) -> Any:
        if fault == "prior-W-only" and "/runs?" in path and f"head_sha={w1}&" in path:
            raise AssertionError("An earlier W cannot supply this dispatch")
        return endpoints[path] if path in endpoints else native.read(path)

    return read, pr, material


@pytest.mark.parametrize("historical", [False, True])
def test_prometheus_designated_tree_and_original_artifacts_still_need_dispatch(
    monkeypatch: pytest.MonkeyPatch, historical: bool
) -> None:
    read, pr, material = _prometheus_repair_git_fixture(monkeypatch, None, historical=historical)
    b, k, w = runtime_surface.publisher_repair_head(read, pr, historical=historical)
    runtime_surface._publisher_repair_material(read, b, k, w, pr)
    assert runtime_surface._publisher_input_source(read, b, k, w) == _repair_subject_fixture()[0]
    assert runtime_surface.publisher_repair_dispatch(read, pr, historical=historical) is None


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("wrong-base", "native_ancestor_relation"),
        ("wrong-H", "publisher_prometheus_designated_topology"),
        ("wrong-P", "publisher_prometheus_designated_source"),
        ("hook-extra", "publisher_repair_complete_maintenance_delta"),
        ("substituted-P", "publisher_prometheus_exact_source_or_caller"),
        ("substituted-harness", "publisher_prometheus_exact_source_or_caller"),
        ("stale-prom-caller", "publisher_prometheus_exact_source_or_caller"),
        ("wrong-wrapper", "publisher_prometheus_wrapper_pin"),
        ("extra-wrapper-byte", "publisher_prometheus_wrapper_pin"),
        ("wrapper-mode", "publisher_repair_complete_maintenance_delta"),
        ("unapproved-path", "publisher_repair_complete_maintenance_delta"),
        ("edit-revert", "publisher_prometheus_transient_material"),
        ("baseline-extra-remove", "publisher_prometheus_baseline_findings"),
        ("baseline-extra-add", "publisher_prometheus_baseline_findings"),
        ("baseline-p-ref", "publisher_prometheus_baseline_findings"),
        ("baseline-other-change", "publisher_prometheus_baseline_findings"),
        ("restored-retired-alias", "publisher_prometheus_baseline_findings"),
        ("baseline-unannotated", "publisher_prometheus_baseline_alias"),
        ("baseline-verified-old", "publisher_prometheus_baseline_alias"),
        ("nightly-extra-byte", "publisher_prometheus_nightly_operand"),
        ("nightly-wrong-target", "publisher_prometheus_nightly_operand"),
        ("nightly-transient", "publisher_prometheus_nightly_operand"),
        ("nightly-mode", "publisher_repair_complete_maintenance_delta"),
        ("baseline-policy", "publisher_prometheus_baseline_findings"),
        ("second-W-edit", "publisher_repair_complete_maintenance_delta"),
        ("stale-W-slot", "publisher_repair_exact_caller_pin_bytes"),
        ("wrong-prior-W", "publisher_repair_exact_caller_pin_bytes"),
        ("partial-restore", "publisher_prometheus_coordinated_restore"),
        ("prior-no-fix", "publisher_prometheus_distinct_correction"),
        ("prior-outside", "publisher_repair_complete_maintenance_delta"),
        ("prior-P", "publisher_repair_complete_maintenance_delta"),
        ("prior-harness", "publisher_prometheus_exact_source_or_caller"),
        ("premature-harness", "publisher_prometheus_exact_source_or_caller"),
        ("regressed-harness", "publisher_prometheus_transient_material"),
        ("stale-final-harness", "publisher_prometheus_exact_source_or_caller"),
        ("wrong-first-publication", "publisher_prometheus_exact_source_or_caller"),
        ("prior-wrapper", "publisher_prometheus_wrapper_pin"),
        ("rewound-controller", "publisher_prometheus_source_ancestry"),
        ("ambiguous-controller", "publisher_prometheus_direct_parent"),
        ("altered-squash", "publisher_repair_exact_squash"),
        ("wrong-original-Q", "publisher_repair_original_artifact"),
        ("wrong-original-S", "publisher_repair_original_artifact"),
        ("wrong-original-C", "publisher_repair_original_candidate_zip"),
    ],
)
def test_prometheus_repair_rejects_substituted_graph_or_original_subject(
    monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    historical = fault == "altered-squash"
    read, pr, _ = _prometheus_repair_git_fixture(monkeypatch, fault, historical=historical)
    with pytest.raises((QualificationError, ValueError), match="^" + diagnostic + "$"):
        runtime_surface.publisher_repair_dispatch(read, pr, historical=historical)


@pytest.mark.parametrize(
    "fault", ["wrong-controller", "wrong-callers", "wrong-number", "incomplete", "extra"]
)
def test_dispatched_prometheus_paths_crossbind_same_authenticated_coordinates(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    read, pr, _ = _prometheus_repair_git_fixture(monkeypatch, None, dispatched=True)
    grant = runtime_surface.publisher_repair_dispatch(read, pr)
    assert grant
    paths = set(runtime_surface._PROM_REPAIR_PATHS)
    runtime_surface.require_dispatched_publisher_repair_paths(
        read, pr["number"], grant, paths, historical=False
    )
    if fault == "wrong-controller":
        grant["controller"] = "d" * 40
    elif fault == "wrong-callers":
        grant["callers"] = "c" * 40
    elif fault == "wrong-number":
        grant["pr"] = "82"
    elif fault == "incomplete":
        paths.remove("scripts/QUICK_FIX_PRODUCTION.sh")
    else:
        paths.add(".github/workflows/frontend-ci.yml")
    with pytest.raises(QualificationError, match="^publisher_prometheus_exact_material$"):
        runtime_surface.require_dispatched_publisher_repair_paths(
            read, pr["number"], grant, paths, historical=False
        )


def test_prometheus_repair_paths_remain_outside_generic_maintenance_class() -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    additions = runtime_surface._PROM_REPAIR_PATHS - runtime_surface._PUBLISHER_REPAIR_FILES
    assert len(runtime_surface._PROM_REPAIR_PATHS) == 18
    assert additions == {
        "scripts/ci/prometheus_source_image.py",
        "tests/test_prometheus_source_image.py",
        "tests/test_notify_premium_alias_checkpoint_failure.py",
        ".github/workflows/nightly-tests.yml",
        "scripts/QUICK_FIX_PRODUCTION.sh",
    }
    for path in additions:
        with pytest.raises(
            QualificationError, match="^publisher_repair_complete_maintenance_delta$"
        ):
            runtime_surface.require_publisher_repair_paths({".github/workflows/ci.yml", path})


def test_special_baseline_can_record_native_hook_as_separate_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    read, pr, material = _prometheus_repair_git_fixture(
        monkeypatch, "hook-before-U", repository=tmp_path / "git", dispatched=True
    )
    grant = runtime_surface.publisher_repair_dispatch(read, pr)
    assert grant is not None and grant["controller"] == material["controller"]


@pytest.mark.parametrize(
    "history",
    ["docs-before-restore", "docs-with-restore", "corrected-post-W", "corrected-AM-helper"],
)
def test_corrected_controller_requires_implementation_or_regression_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, history: str
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    read, pr, material = _prometheus_repair_git_fixture(
        monkeypatch, history, repository=tmp_path / "git", dispatched=True
    )
    if history in ("docs-before-restore", "docs-with-restore"):
        with pytest.raises(QualificationError, match="^publisher_prometheus_distinct_correction$"):
            runtime_surface.publisher_repair_dispatch(read, pr)
        return
    grant = runtime_surface.publisher_repair_dispatch(read, pr)
    assert grant is not None
    assert (grant["controller"], grant["callers"]) == (material["controller"], material["callers"])


@pytest.mark.parametrize(
    ("kind", "fault", "diagnostic"),
    [
        ("pull_request", None, None),
        ("push", None, None),
        ("push", "mapping", None),
        ("pull_request", "mapping", None),
        ("pull_request", "unchanged", None),
        ("pull_request", "extra-path", "complete_maintenance_delta"),
        ("pull_request", "mapping-mixed", "complete_maintenance_delta"),
        ("pull_request", "one-wrapper", "verifier_and_both_wrappers"),
        ("pull_request", "wrong-pin", "exact_verifier_pin"),
        ("pull_request", "extra-byte", "exact_verifier_pin"),
        ("pull_request", "stale-base", "live_base"),
        ("pull_request", "changed-during-proof", "declared_data_value"),
        ("pull_request", "expires-final", "ordinary_evidence_expired"),
        ("push", "expires-final", "ordinary_evidence_expired"),
        ("pull_request", "mode", "complete_maintenance_delta"),
        ("pull_request", "deleted-doc", "regular_delta"),
        ("pull_request", "fork", "receiver_repository"),
        ("pull_request", "different-event", "receiver_pr_event"),
        ("pull_request", "different-controller", "issuer_controller"),
        ("pull_request", "ambiguous-issuer", "issuer_merged_pr"),
        ("pull_request", "self-issuer", "issuer_merged_pr"),
        ("pull_request", "open-issuer", "issuer_merged_pr"),
        ("pull_request", "no-grant", "issuer_historical_grant"),
        ("pull_request", "foreign-grant", "issuer_historical_grant"),
        ("pull_request", "issuer-off-main", "native_ancestor_relation"),
        ("push", "wrong-parent", "receiver_squash"),
        ("push", "different-tree", "declared_data_value"),
    ],
)
def test_caddy_ordinary_receiver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault: str | None,
    diagnostic: str | None,
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    endpoints, _, node = _git_tree_fixture()
    k = "1" * 40
    upstream = "2" * 40
    number = 83
    verifier = runtime_surface._CHECKPOINT_VERIFIER
    wrappers = runtime_surface._CHECKPOINT_WRAPPERS
    callers = (".github/workflows/ci.yml", ".github/workflows/cd.yml")
    ledger = "docs/roadmap/BACKLOG_LEDGER.md"
    mapping = f"docs/review/PR_{number}_FIXED_MAPPING.md"

    def wrapper(raw: bytes) -> bytes:
        return (
            b"body\n    '"
            + verifier.encode()
            + b"': 'sha256:"
            + hashlib.sha256(raw).hexdigest().encode()
            + b"',\nend\n"
        )

    old, new = b"old verifier", b"new verifier"
    pin = f"  ALERTMANAGER_CONTROLLER_SOURCE: '{k}'\n".encode()
    source = {verifier: ("100644", old), ledger: ("100644", b"pending")}
    source.update({name: ("100755", wrapper(old)) for name in wrappers})
    source.update({name: ("100644", pin) for name in callers})
    if fault == "different-controller":
        source[callers[1]] = ("100644", pin.replace(k.encode(), upstream.encode()))
    base = node(upstream, source, "base")
    updated = {**source, ledger: ("100644", b"target PR"), verifier: ("100644", new)}
    updated.update({name: ("100755", wrapper(new)) for name in wrappers})
    if fault == "extra-path":
        updated["unrelated"] = ("100644", b"x")
    elif fault == "one-wrapper":
        updated[wrappers[1]] = source[wrappers[1]]
    elif fault in ("extra-byte", "wrong-pin", "mode"):
        updated[wrappers[0]] = {
            "extra-byte": ("100755", wrapper(new) + b"extra"),
            "wrong-pin": ("100755", wrapper(b"wrong")),
            "mode": ("100644", wrapper(new)),
        }[fault]
    elif fault == "deleted-doc":
        del updated[ledger]
    elif fault == "unchanged":
        updated = source.copy()
    head = node(base, updated, "material")
    if fault in ("mapping", "mapping-mixed"):
        updated[mapping] = ("100644", b"seal")
        if fault == "mapping-mixed":
            updated[ledger] = ("100644", b"other")
        head = node(head, updated, "mapping")
    squash = node(
        upstream if fault == "wrong-parent" else base,
        source if fault == "different-tree" else updated,
        "squash",
    )
    repository = {"full_name": runtime_surface.CADDY_REPOSITORY, "id": 1043311030}
    pr = {
        "number": number,
        "state": "closed" if kind == "push" else "open",
        "merged": kind == "push",
        "base": {"ref": "main", "sha": base, "repo": repository},
        "head": {
            "ref": "receiver",
            "sha": head,
            "repo": repository if fault != "fork" else {**repository, "id": 42},
        },
        "merge_commit_sha": squash,
    }
    synthetic = node(base, updated, "synthetic", second_parent=head)
    monkeypatch.setenv("GITHUB_WORKFLOW_SHA", squash if kind == "push" else synthetic)
    monkeypatch.setenv("GITHUB_JOB", "caddy-contract")
    monkeypatch.setenv(
        "GITHUB_REF", "refs/heads/main" if kind == "push" else f"refs/pull/{number}/merge"
    )
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        (
            f"{runtime_surface.CADDY_REPOSITORY}/.github/workflows/frontend-ci.yml@refs/pull/{number}/merge"
            if kind == "pull_request"
            else f"{runtime_surface.CADDY_REPOSITORY}/.github/workflows/frontend-ci.yml@refs/heads/main"
        ),
    )
    event = {"before": base, "number": number + int(fault == "different-event"), "pull_request": pr}
    producer = number if fault == "self-issuer" else 18
    issuer = {
        "number": producer,
        "head": {"sha": "4" * 40, "ref": "issuer"},
        "merge_commit_sha": upstream,
        "state": "closed",
        "merged": fault != "open-issuer",
    }
    endpoints[f"/pulls/{number}"] = {
        **pr,
        "head": {**pr["head"], "sha": k if fault == "changed-during-proof" else head},
    }
    endpoints["/git/ref/heads/main"] = {
        "ref": "refs/heads/main",
        "object": {"type": "commit", "sha": head if fault == "stale-base" else base},
    }
    endpoints[f"/commits/{k}/pulls?per_page=2"] = [issuer] * (
        2 if fault == "ambiguous-issuer" else 1
    )
    endpoints[f"/pulls/{producer}"] = issuer
    for prior, later in ((base, head), (upstream, base)):
        endpoints[f"/compare/{prior}...{later}"] = {
            "base_commit": {"sha": prior},
            "merge_base_commit": {"sha": prior},
            "status": "behind" if prior == upstream and fault == "issuer-off-main" else "ahead",
            "behind_by": 0,
            "ahead_by": 1,
            "total_commits": 1,
            "commits": [{"sha": later, "parents": [{"sha": prior}]}],
        }

    from datetime import datetime, timedelta

    deadline = runtime_surface._publisher_time("2099-01-01T00:00:00Z")
    now = deadline - timedelta(seconds=1)

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now.astimezone(tz)

    monkeypatch.setattr(runtime_surface, "datetime", Clock)

    def grant(
        read: Any, observed: dict, *, historical: bool, historical_retention: list
    ) -> dict | None:
        historical_retention.append(deadline)
        assert observed == issuer and historical is True
        assert read("/git/commits/" + base)["sha"] == base
        assert read(f"/pulls/{producer}") == issuer
        return (
            None
            if fault == "no-grant"
            else {
                "controller": upstream if fault == "foreign-grant" else k,
                "producer_run": "21",
                "producer_head": "a" * 40,
            }
        )

    monkeypatch.setattr(runtime_surface, "publisher_repair_dispatch", grant)
    bound = runtime_surface._publisher_utc(deadline)
    main_validated = False

    def main_import(*args: Any, source_expiry: datetime) -> dict[str, str]:
        nonlocal main_validated
        assert source_expiry == deadline
        main_validated = True
        return {"producer_artifact": "31", "evidence_expires_at": bound}

    def native_read(endpoint: str) -> Any:
        nonlocal now
        if (
            fault == "expires-final"
            and main_validated
            and endpoint
            == ("/git/ref/heads/main" if kind == "pull_request" else f"/pulls/{number}")
        ):
            now = deadline
        return endpoints[endpoint]

    monkeypatch.setattr(runtime_surface, "_caddy_main_import", main_import)
    args = (native_read, pr, squash if kind == "push" else head, kind, event)
    if diagnostic:
        with pytest.raises((ValueError, QualificationError), match=diagnostic):
            runtime_surface._caddy_ordinary_pr(*args)
    else:
        if fault == "unchanged":
            assert runtime_surface._caddy_ordinary_pr(*args) is None
        else:
            selected = squash if kind == "push" else head
            path = tmp_path / "native-event.json"
            path.write_text(json.dumps({**event, "ref": "refs/heads/main", "after": selected}))
            monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
            monkeypatch.setenv("GITHUB_EVENT_NAME", kind)
            monkeypatch.setenv("GITHUB_SHA", selected)
            for historical_number in (2484, 2494, 2495, 2501):
                endpoints[f"/pulls/{historical_number}"] = {
                    "state": "closed",
                    "merged": True,
                    "merge_commit_sha": upstream,
                }
            endpoints[f"/commits/{squash}/pulls?per_page=2"] = [pr]

            def read(endpoint: str) -> Any:
                if endpoint.startswith("/pulls?"):
                    return [pr] if kind == "pull_request" else []
                return endpoints[endpoint]

            record = runtime_surface.caddy_bound_pr(read, selected)
            assert record["number"] == number and "publisher_repair" not in record
            assert record["ordinary_reader"] == {
                "base": base,
                "evidence_expires_at": bound,
                "controller": k,
                "issuer_pr": producer,
                "issuer_head": issuer["head"]["sha"],
                "issuer_branch": "issuer",
                "issuer_merge": upstream,
                "producer_head": "a" * 40,
                "producer_run": "21",
                "producer_artifact": "31",
            }


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        (None, None),
        ("renewal", None),
        ("archived-grant-drift", "declared_data_value"),
        ("sibling-failure", None),
        ("sibling-timeout", "main_import_ineligible"),
        ("sibling-neutral", "main_import_ineligible"),
        ("sibling-skipped", "main_import_ineligible"),
        ("sibling-failure-with-failed-upload", None),
        ("failed-precursor", "main_import_ineligible"),
        ("unknown-sibling", "main_independent_failure"),
        ("unfinished-sibling", "main_independent_failure"),
        ("foreign-sibling-attempt", "main_independent_failure"),
        ("original-aggregate-incomplete", "main_run"),
        ("original-aggregate-unknown", "main_artifact_conclusion"),
        ("original-job-incomplete", "main_run"),
        ("original-job-unknown", "main_artifact_conclusion"),
        ("failed-first", None),
        ("failed-latest", None),
        ("failed-attempt-witness", None),
        ("failed-latest-witness", None),
        ("unbound-second-witness", "main_artifact_owner"),
        ("upload-time-mismatch", "main_import_artifact"),
        ("zero-main-attempt", "retained_native_decision"),
        ("claims-future-attempt", "main_attempt"),
        ("wrong-native-attempt", "actual_run_attempt"),
        ("two-witnesses", "main_artifact_inventory"),
        ("no-witness", "main_artifact_inventory"),
        ("expired-witness", "main_import_artifact"),
        ("main-expires-during-transfer", "main_import_artifact"),
        ("shortened-Q-expires-during-job", "main_import_artifact"),
        ("prior-D-expires-during-job", "main_import_artifact"),
        ("expired-extra-still-live", None),
        ("unowned-expired-extra", "main_artifact_owner"),
        ("unparseable-extra-expiry", "native_timestamp"),
        ("typed-extra-expiry", "main_import_artifact"),
        ("supplemental-steps", None),
        ("supplemental-step-unknown", "main_import_steps"),
        ("supplemental-step-missing", "main_import_steps"),
        ("supplemental-step-duplicate", "main_import_steps"),
        ("two-negative", "main_artifact_inventory"),
        ("all-succeeded-failed-aggregate", "main_independent_failure"),
        ("artifact-id", "retained_import"),
        ("copied-witness", "native_artifact_identity"),
        ("bad-digest", "native_artifact_bytes"),
        ("failed-job", "main_import_ineligible"),
        ("ambiguous-run", "main_run"),
        ("no-job", "main_run"),
        ("no-import", "main_import_ineligible"),
        ("did-build", "main_import_ineligible"),
        ("wrong-action", "not_a_dispatch"),
        ("wrong-attempt", "original_job"),
        ("protected-parser", "missing_checked_input_record"),
    ],
)
def test_caddy_main_import_requires_actual_original_artifact(
    monkeypatch: pytest.MonkeyPatch, fault: str | None, diagnostic: str | None
) -> None:
    _assert_caddy_main_import(monkeypatch, fault, diagnostic)


def _assert_caddy_main_import(
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
    diagnostic: str | None,
    supplemental_conclusions: tuple[object, object] = ("failure", "failure"),
    malformed_id: object = None,
) -> None:
    from io import BytesIO
    from zipfile import ZipFile
    from scripts.ci.prometheus_source_image import QualificationError

    from datetime import datetime, timedelta, timezone

    renewal = fault in {"renewal", "prior-D-expires-during-job"}
    history, issuer, material = _prometheus_repair_git_fixture(
        monkeypatch,
        "corrected-post-W" if fault == "prior-D-expires-during-job" else None,
        historical=True,
        dispatched=True,
        renewal=renewal,
    )
    now = datetime(2026, 1, 7, 1, tzinfo=timezone.utc)
    expiry = now + timedelta(seconds=1)

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now.astimezone(tz)

    monkeypatch.setattr(runtime_surface, "datetime", Clock)

    def selected_history(endpoint: str) -> Any:
        result = history(endpoint)
        if (
            fault == "shortened-Q-expires-during-job"
            and endpoint == "/actions/artifacts/14199242996"
            or fault == "prior-D-expires-during-job"
            and endpoint == "/actions/artifacts/10073"
        ):
            return {**result, "expires_at": runtime_surface._publisher_utc(expiry)}
        return result

    retention: list[datetime] = []
    grant = runtime_surface.publisher_repair_dispatch(
        selected_history, issuer, historical=True, historical_retention=retention
    )
    assert grant is not None and grant["action"] == ("contract" if renewal else "candidate-D")
    assert len(retention) == 1
    if fault in {"shortened-Q-expires-during-job", "prior-D-expires-during-job"}:
        assert (
            retention[0] == expiry
            and runtime_surface._publisher_time(grant["source_horizon"]) > expiry
        )
    squash = issuer["merge_commit_sha"]
    # The archived import contains what the issuer actually selected prior to its push.
    # Independently project that observation from the original dispatch ZIP plus native upload.
    source_run = 74 if renewal else 73
    source_job = history(f"/actions/runs/{source_run}/attempts/1/jobs?per_page=100&page=1")["jobs"][
        0
    ]
    source_artifact = history(f"/actions/artifacts/{10000 + source_run}")
    with ZipFile(BytesIO(history(f"/actions/artifacts/{source_artifact['id']}/zip"))) as archive:
        observed = json.loads(archive.read("source-decision.json"))["publisher_dispatch"]
    archived_grant = {
        **observed,
        "created": source_job["completed_at"],
        "artifact": str(source_artifact["id"]),
        "artifact_digest": source_artifact["digest"],
    }
    assert archived_grant == grant
    assert grant["created"] < issuer["merged_at"]
    original = history("/actions/artifacts/10073")
    original_job = history("/actions/runs/73/attempts/1/jobs?per_page=100&page=1")["jobs"][0]
    api = _DispatchNativeFixture(issuer, material)
    api.records[73] = (
        history("/actions/runs/73/attempts/1"),
        original_job,
        original,
        history("/actions/artifacts/10073/zip"),
    )
    api.add(api.projection(75, "contract", "2026-01-05T00:00:00Z"))
    main_run, main_job, main_artifact, reference = api.records[75]
    archived_attempt = (
        2
        if fault
        in {
            "failed-first",
            "bad-extra-id",
            "supplemental-steps",
            "supplemental-step-unknown",
            "supplemental-step-missing",
            "supplemental-step-duplicate",
            "two-negative",
            "failed-attempt-witness",
            "sibling-failure-with-failed-upload",
            "claims-future-attempt",
            "wrong-native-attempt",
        }
        else 1
    )
    main_run.update(
        event="push", head_sha=squash, head_branch="main", created_at="2026-01-03T00:01:00Z"
    )
    main_job.update(head_sha=squash, head_branch="main")
    sibling_failure = fault in {
        "sibling-failure",
        "all-succeeded-failed-aggregate",
        "sibling-timeout",
        "sibling-neutral",
        "sibling-skipped",
        "sibling-failure-with-failed-upload",
        "failed-precursor",
        "unknown-sibling",
        "unfinished-sibling",
        "foreign-sibling-attempt",
    }
    if fault == "singleton-terminal":
        main_job["conclusion"], main_run["conclusion"] = supplemental_conclusions
    elif sibling_failure:
        main_run["conclusion"] = "failure"
    elif fault == "original-aggregate-incomplete":
        main_run.update(status="in_progress", conclusion=None)
    elif fault == "original-aggregate-unknown":
        main_run["conclusion"] = "future"
    elif fault == "original-job-incomplete":
        main_job.update(status="in_progress", conclusion=None)
    elif fault == "original-job-unknown":
        main_job["conclusion"] = "future"
    main_artifact.update(name="caddy-contract-evidence")
    main_artifact["workflow_run"].update(head_sha=squash, head_branch="main")
    if fault == "bad-single-id":
        main_artifact["id"] = malformed_id
    if fault == "expired-witness":
        main_artifact["expires_at"] = "2026-01-03T01:00:00Z"
    elif fault == "main-expires-during-transfer":
        main_artifact["expires_at"] = runtime_surface._publisher_utc(expiry)
    elif fault == "upload-time-mismatch":
        main_artifact["created_at"] = "2026-01-05T00:06:00Z"
    elif fault == "copied-witness":
        main_artifact["workflow_run"]["id"] = 999
    elif fault == "failed-job":
        main_job["conclusion"] = "failure"
    elif fault == "no-import":
        next(
            step
            for step in main_job["steps"]
            if step["name"] == runtime_surface._REPAIR_IMPORT_STEP
        )["conclusion"] = "skipped"
    elif fault == "did-build":
        next(
            step for step in main_job["steps"] if step["name"] == runtime_surface._REPAIR_BUILD_STEP
        )["conclusion"] = "success"
    buf = BytesIO()
    with ZipFile(BytesIO(reference)) as source, ZipFile(buf, "w") as target:
        original_ref = json.loads(source.read("original-producer.json"))
        original_ref.update(
            run_attempt=2 if fault == "wrong-attempt" else 1, job_id=original_job["id"]
        )
        if fault == "artifact-id":
            original_ref["artifact"]["id"] += 1
        for name in source.namelist():
            raw = source.read(name)
            if name == "source-decision.json":
                decision = json.loads(raw)
                if fault != "wrong-action":
                    del decision["publisher_dispatch"]
                decision["current_head"] = squash
                raw = json.dumps(decision).encode()
            elif name == "original-producer.json":
                raw = json.dumps(original_ref).encode()
            elif name == "admission.json":
                record = json.loads(raw)
                record.update(
                    current_head=squash,
                    current_run_attempt=0 if fault == "zero-main-attempt" else archived_attempt,
                    current_run_id=75,
                    publisher_repair=(
                        dict(archived_grant, created=issuer["merged_at"])
                        if fault == "archived-grant-drift"
                        else archived_grant
                    ),
                    producer=original_ref,
                )
                raw = json.dumps(record).encode()
            target.writestr(name, raw)
    raw = buf.getvalue()
    main_artifact.update(size_in_bytes=len(raw), digest="sha256:" + hashlib.sha256(raw).hexdigest())
    if fault == "bad-digest":
        main_artifact["digest"] = "sha256:" + "f" * 64
    api.records[75] = main_run, main_job, main_artifact, raw

    attempt_reads: list[int] = []
    step_faults = {
        "supplemental-steps",
        "supplemental-step-unknown",
        "supplemental-step-missing",
        "supplemental-step-duplicate",
        "two-negative",
    }
    second_run = fault in step_faults or fault in {
        "failed-first",
        "failed-latest",
        "wrong-native-attempt",
        "failed-attempt-witness",
        "bad-extra-id",
        "sibling-failure-with-failed-upload",
        "failed-latest-witness",
    }
    duplicate = fault in step_faults or fault in {
        "supplemental-steps",
        "two-negative",
        "expired-extra-still-live",
        "unowned-expired-extra",
        "unparseable-extra-expiry",
        "typed-extra-expiry",
        "supplemental-step-unknown",
        "two-witnesses",
        "unbound-second-witness",
        "failed-attempt-witness",
        "bad-extra-id",
        "sibling-failure-with-failed-upload",
        "failed-latest-witness",
    }

    def native_job(attempt: int) -> dict:
        actual = 1 if fault == "wrong-native-attempt" else attempt
        job = {**main_job, "id": 1074 + actual, "run_attempt": actual}
        if attempt != archived_attempt:
            day = "06" if fault == "failed-latest-witness" else "04"
            stamp = f"2026-01-{day}T00:08:00Z"
            job.update(conclusion=supplemental_conclusions[0], started_at=stamp, completed_at=stamp)
            job["steps"] = [
                (
                    {
                        **step,
                        "started_at": stamp,
                        "completed_at": stamp,
                    }
                    if step["name"] == runtime_surface._REPAIR_UPLOAD_STEP
                    else step
                )
                for step in job["steps"]
            ]
        if fault in step_faults and (attempt != archived_attempt or fault == "two-negative"):
            job["conclusion"] = "success"
            target = runtime_surface._REPAIR_IMPORT_STEP
            steps = [dict(step) for step in job["steps"]]
            selected = next(step for step in steps if step["name"] == target)
            if fault == "supplemental-step-missing":
                steps.remove(selected)
            elif fault == "supplemental-step-duplicate":
                steps.append(dict(selected))
            else:
                selected["conclusion"] = (
                    "future" if fault == "supplemental-step-unknown" else "skipped"
                )
            job["steps"] = steps
        return job

    def attempt_jobs(job: dict[str, Any], aggregate: object) -> dict[str, Any]:
        if aggregate != "failure" or job["conclusion"] != "success":
            return {"total_count": 1, "jobs": [job]}
        siblings = [
            {
                **job,
                "id": job["id"] + 10,
                "name": "changes",
                "conclusion": "failure" if fault == "failed-precursor" else "success",
            },
            {
                **job,
                "id": job["id"] + 20,
                "name": "unknown" if fault == "unknown-sibling" else "build-and-test",
                "run_attempt": 19 if fault == "foreign-sibling-attempt" else job["run_attempt"],
                "status": "in_progress" if fault == "unfinished-sibling" else "completed",
                "conclusion": {
                    "sibling-timeout": "timed_out",
                    "sibling-neutral": "neutral",
                    "all-succeeded-failed-aggregate": "success",
                    "sibling-skipped": "skipped",
                }.get(fault or "", "failure"),
            },
        ]
        return {"total_count": 3, "jobs": [*siblings, job]}

    reads_at_expiry: list[str] = []

    def read(endpoint: str) -> Any:
        nonlocal now
        if fault == "main-expires-during-transfer" and reads_at_expiry:
            pytest.fail("Expired ZIP must stop the read before native job lookup")
        if (
            fault == "main-expires-during-transfer" and endpoint == "/actions/artifacts/10075/zip"
        ) or (
            fault in {"shortened-Q-expires-during-job", "prior-D-expires-during-job"}
            and endpoint == "/actions/runs/75/attempts/1/jobs?per_page=100&page=1"
        ):
            reads_at_expiry.append(endpoint)
            now = expiry
        if second_run:
            if endpoint.startswith("/actions/workflows/frontend-ci.yml/runs?"):
                latest = {
                    **main_run,
                    "run_attempt": 2,
                    "conclusion": (
                        "failure"
                        if fault in {"failed-latest", "failed-latest-witness"}
                        else "success"
                    ),
                }
                return {"total_count": 1, "workflow_runs": [latest]}
            if endpoint.startswith("/actions/runs/75/attempts/"):
                attempt = int(endpoint.split("/")[5])
                job = native_job(attempt)
                aggregate = (
                    main_run["conclusion"]
                    if attempt == archived_attempt
                    else supplemental_conclusions[1]
                )
                if fault in step_faults:
                    aggregate = "success"
                if "/jobs?" in endpoint:
                    return attempt_jobs(job, aggregate)
                attempt_reads.append(attempt)
                return {
                    **main_run,
                    "run_attempt": job["run_attempt"],
                    "conclusion": aggregate,
                }
        elif (sibling_failure or fault == "singleton-terminal") and "/attempts/1/jobs?" in endpoint:

            return attempt_jobs(main_job, main_run["conclusion"])
        if duplicate:
            if "/artifacts?" in endpoint:
                extra = {**main_artifact, "id": malformed_id if fault == "bad-extra-id" else 19000}
                if fault.startswith(("expired-extra", "unowned-expired")):
                    extra["expires_at"] = runtime_surface._publisher_utc(now)
                elif fault == "unparseable-extra-expiry":
                    extra["expires_at"] = "unknown"
                elif fault == "typed-extra-expiry":
                    extra["expired"] = 0
                if fault not in {"two-witnesses", "expired-extra-still-live"}:
                    extra["created_at"] = (
                        "2026-01-06T00:08:00Z"
                        if fault == "failed-latest-witness"
                        else "2026-01-04T00:08:00Z"
                    )
                return {"total_count": 2, "artifacts": [main_artifact, extra]}
            if "/jobs?filter=all" in endpoint:
                jobs = [native_job(i) for i in ((1, 2) if second_run else (1,))]
                return {"total_count": len(jobs), "jobs": jobs}
        if fault == "ambiguous-run" and endpoint.startswith(
            "/actions/workflows/frontend-ci.yml/runs?"
        ):
            return {"total_count": 2, "workflow_runs": [main_run, main_run]}
        if fault == "no-job" and "/attempts/1/jobs?" in endpoint:
            return {"total_count": 0, "jobs": []}
        if fault == "no-witness" and "/artifacts?" in endpoint:
            return {"total_count": 0, "artifacts": []}
        return api.read(endpoint)

    if fault == "protected-parser":
        with pytest.raises(QualificationError, match=diagnostic):
            runtime_surface._publisher_zip_record(BytesIO(raw), len(raw), 75, squash)
    elif diagnostic is not None:
        with pytest.raises((QualificationError, ValueError), match=diagnostic):
            runtime_surface._caddy_main_import(read, issuer, grant, source_expiry=retention[0])
    else:
        assert runtime_surface._caddy_main_import(
            read, issuer, grant, source_expiry=retention[0]
        ) == {
            "main_run": "75",
            "evidence_expires_at": runtime_surface._publisher_utc(
                min(retention[0], runtime_surface._publisher_time(main_artifact["expires_at"]))
            ),
            "main_attempt": str(archived_attempt),
            "main_job": str(1074 + archived_attempt),
            "main_artifact": "10075",
            "main_digest": main_artifact["digest"],
            "producer_job": "1073",
            "producer_artifact": "10073",
            "producer_digest": original["digest"],
        }
        if fault in ("failed-first", "failed-latest"):
            assert attempt_reads == [archived_attempt]
    if fault in {
        "main-expires-during-transfer",
        "shortened-Q-expires-during-job",
        "prior-D-expires-during-job",
    }:
        assert len(reads_at_expiry) == 1
        assert now == expiry
    if fault == "failed-attempt-witness":
        # At most one read per owner in duplicate attribution; rebind the winner before use.
        assert attempt_reads == ([2, 1] if diagnostic is not None else [2, 1, 2])


@pytest.mark.parametrize("multiple", [False, True], ids=("single", "supplemental"))
@pytest.mark.parametrize("job", sorted(runtime_surface._CADDY_TERMINAL_CONCLUSIONS))
@pytest.mark.parametrize("aggregate", sorted(runtime_surface._CADDY_TERMINAL_CONCLUSIONS))
def test_caddy_witness_terminal_outcome_matrix(
    monkeypatch: pytest.MonkeyPatch, multiple: bool, job: str, aggregate: str
) -> None:
    # The fixture proves the independent sibling when the aggregate failed and Caddy succeeded.
    eligible = job == "success" and aggregate in {"success", "failure"}
    if multiple:
        diagnostic = "main_artifact_inventory" if eligible else None
        fault = "failed-attempt-witness"
    else:
        diagnostic = None if eligible else "main_import_ineligible"
        fault = "singleton-terminal"
    _assert_caddy_main_import(monkeypatch, fault, diagnostic, (job, aggregate))


@pytest.mark.parametrize(
    ("job_conclusion", "run_conclusion", "diagnostic"),
    [
        ("future_outcome", "failure", "main_artifact_conclusion"),
        ("cancelled", "future_outcome", "main_artifact_conclusion"),
        (None, "failure", "main_artifact_conclusion"),
        ("failure", [], "main_artifact_conclusion"),
    ],
)
def test_caddy_supplemental_witness_requires_known_native_conclusions(
    monkeypatch: pytest.MonkeyPatch,
    job_conclusion: object,
    run_conclusion: object,
    diagnostic: str | None,
) -> None:
    _assert_caddy_main_import(
        monkeypatch, "failed-attempt-witness", diagnostic, (job_conclusion, run_conclusion)
    )


@pytest.mark.parametrize("fault", ["bad-single-id", "bad-extra-id"])
@pytest.mark.parametrize("identity", [None, True, 1.0, "19000", 0, -1])
def test_caddy_named_main_archive_requires_native_positive_id(
    monkeypatch: pytest.MonkeyPatch, fault: str, identity: object
) -> None:
    _assert_caddy_main_import(
        monkeypatch, fault, "caddy_issuer_main_artifact_id", malformed_id=identity
    )
