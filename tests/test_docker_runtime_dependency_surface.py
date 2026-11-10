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
    'Path": "github.com/caddyserver/caddy/v2", "Version": "v2.11.4", "Time": '
    '"2026-06-01T19:35:02Z", "Indirect": true, "Dir": "/go/pkg/mod/github.com'
    '/caddyserver/caddy/v2@v2.11.4", "GoMod": "/go/pkg/mod/cache/download/git'
    'hub.com/caddyserver/caddy/v2/@v/v2.11.4.mod", "GoVersion": "1.25.1", "Su'
    'm": "h1:XKxkMTgNSizEvKG6QHue6cAsFOteU2qA61w2tKkCWi0=", "GoModSum": "h1:z'
    'XCl032uTaF5/TpgU38axqFD41jqzxomTDNqK7BzMeI="}, {"Path": "github.com/core'
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
    "rver/caddy/v2@v2.11.4/cmd/caddy|github.com/caddyserver/caddy/v2/modules/"
    "standard\ngithub.com/caddyserver/caddy/v2/modules/caddypki|/go/pkg/mod/gi"
    "thub.com/caddyserver/caddy/v2@v2.11.4/modules/caddypki|github.com/smalls"
    "tep/certificates/authority\ngithub.com/caddyserver/caddy/v2/modules/caddy"
    "pki/acmeserver|/go/pkg/mod/github.com/caddyserver/caddy/v2@v2.11.4/modul"
    "es/caddypki/acmeserver|github.com/caddyserver/caddy/v2/modules/caddypki "
    "github.com/smallstep/certificates/acme github.com/smallstep/certificates"
    "/authority\ngithub.com/caddyserver/caddy/v2/modules/standard|/go/pkg/mod/"
    "github.com/caddyserver/caddy/v2@v2.11.4/modules/standard|github.com/cadd"
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
    b"/go/bin/caddy: go1.26.10\n\tmod\tgithub.com/caddyserver/caddy/v2\tv2.11.4\th1"
    b":XKxkMTgNSizEvKG6QHue6cAsFOteU2qA61w2tKkCWi0=\n\tdep\tgithub.com/coreos/go-"
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
    ordinary.append({"Name": "stdlib", "Version": "v1.26.10", "ID": "stdlib@v1.26.10"})
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
    if fault in (None, "order-prepared", "order-runtime", "order-cleanup", "order-each"):
        result = runtime_surface.observe_caddy_ci_runtime(image, current_directory)
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
        result = runtime_surface.validate_caddy_control_reports(candidate, controls, directory)
        assert result["native_controls"] == "observed_exact_current_epoch"
        assert result["v3_scanner_comparability"] == "UNKNOWN"
        assert len(result["reports"]) == 6
    else:
        with pytest.raises(ValueError):
            runtime_surface.validate_caddy_control_reports(candidate, controls, directory)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original


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


def _upgrade_native_fixture(
    case: str = "upgrade", *, vulnerable: bool = False, response: bytes | None = None
) -> bytes:
    """Independent native-shape fixture; not evidence of a real Caddy process."""
    duplex = case in ("upgrade", "duplicate-connection")
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
            if vulnerable:
                response += b"X-Strip-One: first-secret\r\nX-Strip-Two: second-secret\r\n"
            response += b"\r\n" + server_frame
        elif case == "ordinary-200":
            response = (
                b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\n"
                b"X-End-To-End: first\r\nx-end-to-end: second\r\n\r\nordinary-body\r\n"
            )
        else:
            response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
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
    }
    rows = [
        "TERMINAL role=server stop=0 kill=0 wait=137",
        "TERMINAL role=client stop=0 kill=0 wait=137",
    ]
    rows += [f"FILE name={name} bytes={len(raw)} hex={raw.hex()}" for name, raw in files.items()]
    return ("\n".join(rows) + "\nRESULT primary=0 capture=0\n").encode()


@pytest.mark.parametrize(
    "case",
    [
        "upgrade",
        "duplicate-connection",
        "ordinary-200",
        "missing-upgrade",
        "mismatched-upgrade",
        "invalid-upgrade",
        "no-request-upgrade",
    ],
)
def test_caddy_upgrade_native_channels_keep_http_and_duplex_contract(case: str) -> None:
    result = runtime_surface._validate_caddy_upgrade_exchange(
        case, _upgrade_native_fixture(case), vulnerable_control=False
    )
    assert result["case"] == case
    assert result["duplex"] is (case in ("upgrade", "duplicate-connection"))
    assert result["vulnerable_leak_reproduced"] is False


@pytest.mark.parametrize("vulnerable", [False, True])
def test_caddy_upgrade_control_requires_positive_leak_not_a_clean_or_failed_run(
    vulnerable: bool,
) -> None:
    raw = _upgrade_native_fixture(vulnerable=vulnerable)
    if vulnerable:
        assert (
            runtime_surface._validate_caddy_upgrade_exchange(
                "upgrade", raw, vulnerable_control=True
            )["vulnerable_leak_reproduced"]
            is True
        )
        with pytest.raises(ValueError, match="leaked"):
            runtime_surface._validate_caddy_upgrade_exchange(
                "upgrade", raw, vulnerable_control=False
            )
    else:
        with pytest.raises(ValueError, match="positively reproduce"):
            runtime_surface._validate_caddy_upgrade_exchange(
                "upgrade", raw, vulnerable_control=True
            )


@pytest.mark.parametrize(
    "defect",
    [
        "status",
        "missing-upgrade",
        "extra-connection",
        "lost-duplicate",
        "wrong-frame",
        "unmasked-client",
        "leak",
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
        "leak",
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
        elif defect == "leak":
            wire = wire.replace(b"\r\n\r\n", b"\r\nx-StRiP-TwO: leak\r\n\r\n")
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
            "upgrade", ("\n".join(rows) + "\n").encode(), vulnerable_control=False
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
    duplicate = cases["duplicate-connection"][1]
    assert b"Connection: Upgrade, X-Strip-One\r\n" in duplicate
    assert b"cOnNeCtIoN: X-Strip-Two, uPgRaDe\r\n" in duplicate
    assert b"X-Strip-One: first-secret\r\nX-Strip-Two: second-secret\r\n" in duplicate
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
        result = runtime_surface._observe_caddy_upgrade_exchanges(
            "owned-caddy", tmp_path, vulnerable_control=False
        )
        assert len(result) == 7 and len(seen) == 7
    else:
        with pytest.raises((RuntimeError, ValueError, OSError)) as failure:
            runtime_surface._observe_caddy_upgrade_exchanges(
                "owned-caddy", tmp_path, vulnerable_control=False
            )
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
    assert runtime_surface._validate_caddy_upgrade_exchange(
        "ordinary-200", raw, vulnerable_control=False
    )["roles"]["client"] == (stop, kill, 0)


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
            vulnerable_control=False,
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
        "charge",
    ],
)
def test_caddy062_charge_step_requires_independently_reviewed_same_run_outputs(
    caddy062_metadata: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from contextlib import contextmanager
    import os
    import shutil

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
    assert not charge_step.get("continue-on-error")
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
    ]
    for name in selected:
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            (root / name).read_bytes() if name == "frontend/Dockerfile.caddy-spa" else b"fixture"
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
    state = {
        "mode": "build",
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "repository_id": 1043311030,
        "current_head": head,
        "current_run_id": 73,
        "current_run_attempt": 1,
        "inputs": inputs,
    }
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
            "digest": "sha256:9d1e2c4fda593efb2c405e1c855c75ec17fe42dc02f6b7142a5ea7af7f386bf4"
        },
        "compiler_go_version_sha256": "4e0b213cba780f63b02f3ab9001ee61e4101d254e0af1a8205574c19dad0f93b",
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
        "GITHUB_REF": "refs/heads/codex/dependency-alertmanager-remediation",
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
        assert phase == "PROCESSING"
        yield float
        if fault == "finish":
            raise ValueError("processing exit")
        order.append("finished")

    def charge(phase: str) -> None:
        order.append(phase)
        if fault == "charge":
            raise ValueError("charge failed")

    monkeypatch.setattr(runtime_surface, "caddy_ci_phase", processing)
    monkeypatch.setattr(runtime_surface, "caddy_ci_charge_action", charge)
    monkeypatch.chdir(checkout)
    program = compile(
        charge_step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0], "<caddy-prebuild>", "exec"
    )
    if fault is None:
        exec(program, {})
        assert order == ["finished", "BUILD"]
    else:
        message = (
            "reviewed selected-source profile differs"
            if fault in {"equal-wrong", "equal-package-replacement"}
            else None
        )
        with pytest.raises((OSError, KeyError, ValueError, QualificationError), match=message):
            exec(program, {})
        assert order == (["finished", "BUILD"] if fault == "charge" else [])


def test_caddy_metadata_native_identity_delegates_without_config_ID_alias() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/frontend-ci.yml"
    ).read_text()
    assert "image_relation = native_go_identity(observed, raw, platform_raw)" in workflow
    assert "native_container_image_identity(inspected, image_relation)" in workflow
    assert "native_container_image_identity(terminal, image_relation)" in workflow
    assert "native_container_image_identity(actual, image_relation)" in workflow
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
