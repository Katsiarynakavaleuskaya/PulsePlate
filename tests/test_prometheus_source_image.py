"""Offline security contracts for the hosted metadata-only source qualifier."""

from __future__ import annotations

from dataclasses import replace
from email.message import Message
import gzip
import io
import json
from pathlib import Path
import signal
import tarfile
from typing import Any
from urllib.request import HTTPSHandler, ProxyHandler, build_opener
from urllib.response import addinfourl

import pytest

from scripts.ci import prometheus_source_image as source


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_CONFIG_DIR",
        "GH_HOST",
        "GH_DEBUG",
        "GIT_TRACE",
        "GIT_CURL_VERBOSE",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)


def package_stream(command: str, *, http2: bool = False) -> bytes:
    root = {"ImportPath": source.ROOT_MODULE + "/cmd/" + command, "Name": "main", "Imports": []}
    objects: list[dict[str, Any]] = []
    if command == "prometheus":
        ui = {
            "ImportPath": source.ROOT_MODULE + "/web/ui",
            "Name": "ui",
            "Imports": [],
            "EmbedFiles": [p + ".gz" for p in source.UI_FILES],
        }
        root["Imports"].append(ui["ImportPath"])
        objects.append(ui)
    if http2:
        root["Imports"].append("golang.org/x/net/http2")
        objects.append(
            {
                "ImportPath": "golang.org/x/net/http2",
                "Name": "http2",
                "Imports": [],
                "Module": {"Path": "golang.org/x/net", "Version": "v0.58.0"},
            }
        )
    objects.append(root)
    return b"\n".join(json.dumps(obj).encode() for obj in objects)


@pytest.mark.parametrize("command", ["prometheus", "promtool"])
def test_complete_graph_preserves_observation_without_disposition(command: str) -> None:
    result = source.decode_packages(package_stream(command, http2=True), command)
    assert result["affected_package_path_observations"]["golang.org/x/net/http2"] is True
    assert len(result["affected_package_path_observations"]) == 8
    assert "pending" in result["advisory_disposition"]
    assert set(source.ADVISORIES) == {
        "GO-2026-6603",
        "GO-2026-6610",
        "GO-2026-6611",
        "GO-2026-6612",
        "GO-2026-6617",
        "GO-2026-5932",
    }
    assert not any("openpgp" in p for p in result["package_paths"])


@pytest.mark.parametrize(
    "change",
    [
        "Error",
        "DepsErrors",
        "Incomplete",
        "missing_dependency",
        "missing_root",
        "duplicate",
        "missing_UI",
        "bad_Incomplete_type",
    ],
)
def test_graph_rejects_incomplete_or_conflicting_native_output(change: str) -> None:
    objects = [json.loads(line) for line in package_stream("prometheus").splitlines()]
    if change == "Error":
        objects[-1]["Error"] = {"Err": "synthetic native error"}
    elif change == "DepsErrors":
        objects[-1]["DepsErrors"] = [{"Err": "synthetic missing module"}]
    elif change == "Incomplete":
        objects[-1]["Incomplete"] = True
    elif change == "bad_Incomplete_type":
        objects[-1]["Incomplete"] = 0
    elif change == "missing_dependency":
        objects[-1]["Imports"].append("golang.org/x/net/http2")
    elif change == "missing_root":
        objects.pop()
    elif change == "duplicate":
        objects.append(dict(objects[-1], Name="different"))
    elif change == "missing_UI":
        objects[0]["EmbedFiles"].pop()
    with pytest.raises(source.QualificationError):
        source.decode_packages(
            b"\n".join(json.dumps(obj).encode() for obj in objects), "prometheus"
        )


@pytest.mark.parametrize(
    "tail",
    [b"{", b"trailing", b'{"ImportPath":"x","ImportPath":"y"}', b'{"ImportPath":"x","Value":NaN}'],
)
def test_json_stream_rejects_truncation_duplicates_and_nonfinite(tail: bytes) -> None:
    with pytest.raises((source.QualificationError, json.JSONDecodeError)):
        source.decode_packages(package_stream("prometheus") + b"\n" + tail, "prometheus")


class SyntheticHTTPS(HTTPSHandler):
    def __init__(self, replies: list[tuple[int, bytes, str | None]]) -> None:
        super().__init__()
        self.replies = list(replies)
        self.requests: list[Any] = []

    def https_open(self, request: Any) -> Any:
        self.requests.append(request)
        code, body, location = self.replies.pop(0)
        headers = Message()
        if location is not None:
            headers["Location"] = location
        if code == 200:
            headers["Content-Length"] = str(len(body))
        response = addinfourl(io.BytesIO(body), headers, request.full_url, code)
        response.msg = "synthetic response"
        return response


def install_transport(
    monkeypatch: pytest.MonkeyPatch, replies: list[tuple[int, bytes, str | None]]
) -> SyntheticHTTPS:
    handler = SyntheticHTTPS(replies)
    transport = build_opener(ProxyHandler({}), source.NoRedirect(), handler)
    monkeypatch.setattr(source, "opener", lambda: transport)
    return handler


FINAL = "https://release-assets.githubusercontent.com/github-production-release-asset/6838921/45b9efd2-fa57-4f55-951b-67f2ea9abb5d?sig=synthetic-query-do-not-log"


def test_direct_acquisition_uses_verified_bytes_and_rejects_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.GO, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(200, b"abc", None)])
    result = source.acquire(artifact, tmp_path / "go")
    assert result["sha256"] == source.sha(b"abc")
    assert handler.requests[0].get_header("Authorization") is None
    install_transport(monkeypatch, [(302, b"", FINAL)])
    with pytest.raises(source.QualificationError, match="source_transport_failed"):
        source.acquire(artifact, tmp_path / "redirect")


def test_release_accepts_one_finite_handoff_then_no_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.UI, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(302, b"", FINAL), (200, b"abc", None)])
    result = source.acquire(artifact, tmp_path / "ui")
    assert result["explicit_release_handoff"] is True and len(handler.requests) == 2
    assert "sig=" not in json.dumps(result)
    install_transport(monkeypatch, [(302, b"", FINAL), (302, b"", FINAL)])
    with pytest.raises(source.QualificationError, match="source_transport_failed"):
        source.acquire(artifact, tmp_path / "second-hop")


@pytest.mark.parametrize(
    "url",
    [
        "http://release-assets.githubusercontent.com/github-production-release-asset/6838921/45b9efd2-fa57-4f55-951b-67f2ea9abb5d?x=1",
        FINAL.replace("6838921", "9999999"),
        FINAL.replace("release-assets.githubusercontent.com", "evil.example"),
        FINAL.replace("https://", "https://user:password@"),
        FINAL + "#fragment",
    ],
)
def test_release_handoff_rejects_wrong_authority_path_or_credentials(url: str) -> None:
    with pytest.raises(source.QualificationError):
        source.validate_release_handoff(url, "ui")


def test_digest_failure_does_not_become_cache_or_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.GO, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(200, b"bad", None)])
    with pytest.raises(source.QualificationError, match="download_integrity"):
        source.acquire(artifact, tmp_path / "go")
    assert len(handler.requests) == 1
    with pytest.raises(source.QualificationError, match="download_cache_collision"):
        source.acquire(artifact, tmp_path / "go")


def make_archive(path: Path, entries: list[tuple[str, bytes | None, bytes]]) -> source.Artifact:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.mode = 0o644
            if payload is not None:
                member.size = len(payload)
            if kind == tarfile.SYMTYPE:
                member.linkname = "../outside"
            archive.addfile(member, io.BytesIO(payload) if payload is not None else None)
    return source.Artifact(
        "fixture",
        source.GO.url,
        path.stat().st_size,
        source.file_hash(path),
        "",
        len(entries),
        sum(kind == tarfile.REGTYPE for _, _, kind in entries),
        1024,
    )


def test_safe_archive_checks_every_member_before_extraction(tmp_path: Path) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, [("a/b", b"content", tarfile.REGTYPE)])
    rows = source.extract(artifact, path, tmp_path / "result")
    assert rows[0]["sha256"] == source.sha(b"content")
    assert (tmp_path / "result/a/b").read_bytes() == b"content"


@pytest.mark.parametrize(
    "entries",
    [
        [("../escape", b"x", tarfile.REGTYPE)],
        [("a//b", b"x", tarfile.REGTYPE)],
        [("/absolute", b"x", tarfile.REGTYPE)],
        [("a", None, tarfile.SYMTYPE)],
        [("fifo", None, tarfile.FIFOTYPE)],
        [("a", b"1", tarfile.REGTYPE), ("a", b"2", tarfile.REGTYPE)],
        [("a", b"1", tarfile.REGTYPE), ("a/b", b"2", tarfile.REGTYPE)],
    ],
)
def test_archive_rejects_escapes_links_specials_and_collisions(
    tmp_path: Path, entries: list[tuple[str, bytes | None, bytes]]
) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, entries)
    with pytest.raises(source.QualificationError):
        source.extract(artifact, path, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_fresh_owned_directories_reject_symlink_and_existing_cache(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(source.QualificationError, match="output_not_fresh"):
        source.fresh_directory(existing)
    alias = tmp_path / "alias"
    alias.symlink_to(existing, target_is_directory=True)
    with pytest.raises(source.QualificationError):
        source.fresh_directory(alias / "child")
    assert not (existing / "child").exists()


def test_ui_staging_discloses_transform_and_keeps_licenses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, ui = tmp_path / "source", tmp_path / "ui"
    (root / "web/ui").mkdir(parents=True)
    (ui / "static").mkdir(parents=True)
    template = b'package ui\nimport "embed"\n'
    (root / "web/ui/embed.go.tmpl").write_bytes(template)
    monkeypatch.setattr(source, "EMBED_TEMPLATE", source.sha(template))
    files = {}
    for name in ["static/index.html", "static/third-party-licenses.txt"]:
        data = name.encode()
        (ui / name).write_bytes(data)
        files[name] = {"size": len(data), "sha256": source.sha(data)}
    monkeypatch.setattr(source, "UI_FILES", files)
    result = source.stage_ui(root, ui)
    assert len(result["generated_paths"]) == 2
    assert "not GNU" in result["algorithm"]
    for name in files:
        payload = (root / "web/ui" / (name + ".gz")).read_bytes()
        assert payload[9] == 255 and gzip.decompress(payload) == (ui / name).read_bytes()
    assert "third-party-licenses.txt.gz" in (root / "web/ui/embed.go").read_text()


def test_sandbox_is_fixed_rootless_readonly_and_credential_free(tmp_path: Path) -> None:
    roots = [tmp_path / name for name in ["source", "go", "modules"]]
    for path in roots:
        path.mkdir()
    argv = source.sandbox_arguments(
        "/usr/bin/docker", tmp_path, "sha256:" + "1" * 64, "owned", "owner", *roots
    )
    assert argv[argv.index("--user") + 1] == "65532:65532"
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--memory") + 1] == "4g"
    assert argv.count("--mount") == 3 and "--read-only" in argv
    assert argv[argv.index("--tmpfs") + 1] == (
        "/qualification:rw,nosuid,nodev,noexec,size=1g,mode=1777"
    )
    assert "HOME=/qualification" in argv and "TMPDIR=/qualification" in argv
    assert "GOCACHE=/qualification/gocache" in argv
    assert all(argv[i + 1].endswith(",readonly") for i, v in enumerate(argv) if v == "--mount")
    env = source.clean_environment(tmp_path, tmp_path, tmp_path, tmp_path, offline=True)
    assert env["GOPROXY"] == env["GOSUMDB"] == "off"
    assert env["GOTOOLCHAIN"] == "local" and env["CGO_ENABLED"] == "0"
    assert not {"GITHUB_TOKEN", "GH_TOKEN", "NETRC", "PIP_INDEX_URL"}.intersection(env)


def test_local_Mac_is_rejected_before_network_or_native_operations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(source.platform, "system", lambda: "Darwin")
    with pytest.raises(source.QualificationError, match="hosted_linux_only"):
        source.qualify(tmp_path / "not-created", 900, 120)
    assert not (tmp_path / "not-created").exists()


def test_valid_wrong_release_asset_is_rejected_before_final_fetch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wrong = FINAL.replace(
        "45b9efd2-fa57-4f55-951b-67f2ea9abb5d", "01234567-89ab-cdef-0123-456789abcdef"
    )
    handler = install_transport(monkeypatch, [(302, b"", wrong)])
    with pytest.raises(source.QualificationError, match="release_handoff_path"):
        source.acquire(replace(source.UI, size=3, digest=source.sha(b"abc")), tmp_path / "ui")
    assert len(handler.requests) == 1


def test_producer_binding_is_absolute_and_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = source.producer_paths()
    assert all(path.is_absolute() and path.is_file() for path in paths)
    assert paths[1].name == "build.yml"
    assert all(len(source.file_hash(path)) == 64 for path in paths)


def test_hash_rejects_single_leaf_aliases_and_special_nodes(tmp_path: Path) -> None:
    path = tmp_path / "regular"
    path.write_bytes(b"safe")
    link = tmp_path / "hardlink"
    link.hardlink_to(path)
    with pytest.raises(source.QualificationError, match="multilink"):
        source.file_hash(path)
    fifo = tmp_path / "fifo"
    import os

    os.mkfifo(fifo)
    with pytest.raises(source.QualificationError, match="nonregular"):
        source.file_hash(fifo)


def test_create_timeout_retains_ownership_and_raw_status_for_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    owned: dict[str, dict[str, Any]] = {}
    expected = {"owner": "synthetic"}
    calls: list[list[str]] = []
    state = {"exists": False}

    class FakeNative:
        def __init__(self) -> None:
            self.records: list[dict[str, Any]] = []

        def run(self, argv: list[str], label: str, env: dict[str, str], **kwargs: Any) -> bytes:
            calls.append(argv)
            if "create" in argv:
                assert owned["owned"] == expected
                state["exists"] = True
                self.records.append(
                    {
                        "exit": None,
                        "failure": "TimeoutExpired",
                        "stderr": "retained-raw-create.stderr",
                    }
                )
                raise TimeoutError("synthetic create timeout")
            if "ps" in argv:
                return b"owned\n" if state["exists"] else b""
            if "inspect" in argv:
                return b"[{}]"
            if "rm" in argv:
                state["exists"] = False
                return b"owned\n"
            raise AssertionError(argv)

    fake = FakeNative()
    with pytest.raises(TimeoutError):
        source.create_owned(
            fake, ["/usr/bin/docker", "create"], "owned", expected, owned, "probe", {}, tmp_path
        )
    monkeypatch.setattr(source, "validate_container", lambda actual, name, record: None)
    result = source.cleanup_owned(fake, "/usr/bin/docker", tmp_path, owned, {}, tmp_path)
    assert result == [{"name": "owned", "native_absent": True}]
    assert fake.records[0]["failure"] == "TimeoutExpired"
    assert any("rm" in argv for argv in calls)


def test_never_created_resource_needs_positive_inventory_without_delete(tmp_path: Path) -> None:
    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            assert "ps" in argv
            return b""

    result = source.cleanup_owned(
        FakeNative(), "/usr/bin/docker", tmp_path, {"owned": {}}, {}, tmp_path
    )
    assert result[0]["native_absent"] is True


def test_diagnostics_retain_constant_code_without_remote_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        source.diagnostic_code(source.QualificationError("source_lock_changed"))
        == "source_lock_changed"
    )
    assert source.diagnostic_code(RuntimeError(FINAL)) is None
    assert source.diagnostic_code(source.QualificationError(FINAL)) is None

    def fail(*args: Any) -> None:
        raise source.QualificationError("source_lock_changed")

    monkeypatch.setattr(source, "qualify", fail)
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--work-dir",
            str(tmp_path),
            "--timeout-seconds",
            "900",
            "--cleanup-seconds",
            "120",
        ],
    )
    previous_handlers = {
        signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        assert source.main() == 1
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    assert all(signal.getsignal(signum) == handler for signum, handler in previous_handlers.items())
    stderr = capsys.readouterr().err
    assert "source_lock_changed" in stderr and "sig=" not in stderr


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b'{"Path":"x","Version":"v1.0.0","Error":"failed"}',
        b'{"Path":"x"}',
        b'{"Path":"x","Version":"v1.0.0"}\n{"Path":"x","Version":"v1.0.0"}',
    ],
)
def test_native_module_stream_errors_cannot_be_success(payload: bytes) -> None:
    with pytest.raises(source.QualificationError):
        source.decode_modules(payload)


def test_native_module_semantics_are_retained_not_reimplemented() -> None:
    payload = {
        "Path": "example.org/module",
        "Version": "v1.0.0",
        "Sum": "h1:synthetic",
        "GoModSum": "h1:synthetic",
    }
    assert source.decode_modules(json.dumps(payload).encode()) == [payload]


def test_deadline_and_signal_preserve_failure_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(source.QualificationError, match="qualification_deadline"):
        source.check_deadline(0)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    monkeypatch.setattr(source, "CLEANING", False)
    with pytest.raises(KeyboardInterrupt):
        source.interrupt(15, None)
    assert source.INTERRUPTIONS == [15]
    monkeypatch.setattr(source, "CLEANING", True)
    source.interrupt(15, None)
    assert source.INTERRUPTIONS == [15, 15]


@pytest.mark.parametrize(
    "state",
    [
        {"Running": False, "ExitCode": 1, "OOMKilled": False},
        {"Running": False, "ExitCode": 0, "OOMKilled": True},
        {"Running": True, "ExitCode": 0, "OOMKilled": False},
        {"Running": False, "ExitCode": False, "OOMKilled": False},
    ],
)
def test_attached_CLI_success_requires_native_container_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: dict[str, Any]
) -> None:
    checked = []

    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            if "start" in argv:
                return b"native metadata"
            assert "inspect" in argv
            return json.dumps([{"State": state}]).encode()

    monkeypatch.setattr(
        source, "validate_container", lambda actual, name, expected: checked.append(name)
    )
    with pytest.raises(source.QualificationError, match="container_native_completion"):
        source.start_owned(
            FakeNative(), "/usr/bin/docker", tmp_path, "owned", {}, "case", {}, tmp_path
        )
    assert checked == ["owned"]


def test_completed_container_inspection_retains_actual_native_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = {"Running": False, "ExitCode": 0, "OOMKilled": False, "FinishedAt": "native-time"}
    operations = []

    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            operations.append(argv)
            if "start" in argv:
                return b"native metadata"
            return json.dumps([{"State": state}]).encode()

    monkeypatch.setattr(source, "validate_container", lambda actual, name, expected: None)
    raw, observed = source.start_owned(
        FakeNative(), "/usr/bin/docker", tmp_path, "owned", {}, "case", {}, tmp_path
    )
    assert raw == b"native metadata" and observed == state
    assert "start" in operations[0] and "inspect" in operations[1]


def test_early_cleanup_has_one_shared_window_without_later_native_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = {"now": 10.0}
    launched: list[list[str]] = []
    monkeypatch.setattr(source.time, "monotonic", lambda: clock["now"])

    class CompletedProcess:
        returncode = 0

        def poll(self) -> int:
            return self.returncode

    def completed(argv: list[str], **kwargs: Any) -> CompletedProcess:
        launched.append(argv)
        return CompletedProcess()

    monkeypatch.setattr(source.subprocess, "Popen", completed)
    native = source.Native(tmp_path, deadline=900.0, cleanup=120)
    native.begin_cleanup()
    assert native.cleanup_deadline == 130.0
    native.run(["/usr/bin/docker", "ps"], "first-cleanup", {}, cwd=tmp_path, cleaning=True)
    clock["now"] = 131.0
    with pytest.raises(source.QualificationError, match="qualification_deadline"):
        native.run(
            ["/usr/bin/docker", "inspect", "owned"],
            "second-cleanup",
            {},
            cwd=tmp_path,
            cleaning=True,
        )
    assert launched == [["/usr/bin/docker", "ps"]]
    with pytest.raises(source.QualificationError, match="cleanup_deadline_already_started"):
        native.begin_cleanup()


@pytest.mark.parametrize("missing_read", (1, 2))
def test_missing_archive_stream_preserves_failure_before_output_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing_read: int
) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, [("a/b", b"content", tarfile.REGTYPE)])
    original = tarfile.TarFile.extractfile
    calls = 0

    def missing_stream(archive: tarfile.TarFile, member: tarfile.TarInfo) -> Any:
        nonlocal calls
        calls += 1
        return None if calls == missing_read else original(archive, member)

    monkeypatch.setattr(source.tarfile.TarFile, "extractfile", missing_stream)
    code = "archive_member_missing" if missing_read == 1 else "extract_member_missing"
    destination = tmp_path / "result"
    with pytest.raises(source.QualificationError, match=code):
        source.extract(artifact, path, destination)
    assert calls == missing_read
    assert not (destination / "a/b").exists()
    if missing_read == 1:
        assert not destination.exists()


@pytest.mark.parametrize("path", (None, 0, False, "", []))
def test_native_package_identity_rejects_nonstring_or_empty_path(path: Any) -> None:
    objects = [json.loads(line) for line in package_stream("prometheus").splitlines()]
    objects[-1]["ImportPath"] = path
    with pytest.raises(source.QualificationError, match="package_identity"):
        source.decode_packages(
            b"\n".join(json.dumps(obj).encode() for obj in objects), "prometheus"
        )


def test_missing_native_docker_stops_before_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setattr(source.shutil, "which", lambda name: None)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Missing native Docker must stop before any source acquisition")

    monkeypatch.setattr(source, "acquire", forbidden)
    work = tmp_path / "qualification"
    with pytest.raises(source.QualificationError, match="native_Docker_missing"):
        source.qualify(work, 900, 120)
    assert not (work / "docker-config").exists()


@pytest.mark.parametrize("changed_lock", (None, "go.mod", "go.sum"))
def test_main_prefetch_uses_no_explicit_module_args_and_rejects_lock_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    changed_lock: str | None,
) -> None:
    """Exercise the real main/qualify flow through prefetch with synthetic native I/O.

    This proves argv and the real post-download lock guard, not native Go closure.
    No Docker or Go process is launched; the unchanged case stops at mod verify.
    """
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setattr(source.shutil, "which", lambda name: "/usr/bin/docker")
    locks = {"go.mod": b"synthetic module lock\n", "go.sum": b"synthetic sums\n"}
    monkeypatch.setattr(source, "LOCKS", {name: source.sha(data) for name, data in locks.items()})
    monkeypatch.setattr(source, "GO_LICENSE", source.sha(b"synthetic license"))
    monkeypatch.setattr(source, "SOURCE_LICENSES", {"LICENSE": source.sha(b"synthetic license")})

    def acquire_fixture(artifact: source.Artifact, target: Path, deadline: float) -> dict[str, Any]:
        target.write_text(
            source.UI.digest + "  prometheus-web-ui-3.15.0.tar.gz\n"
            if artifact.name == "checksums"
            else "synthetic archive"
        )
        return {"synthetic": True}

    def extract_fixture(
        artifact: source.Artifact, archive: Path, target: Path, deadline: float
    ) -> list[dict[str, Any]]:
        target.mkdir()
        if artifact.name in ("source", "go"):
            (target / "LICENSE").write_bytes(b"synthetic license")
            (target / "VERSION").write_bytes(
                b"3.15.0\n"
                if artifact.name == "source"
                else b"go1.27.2\ntime 2026-10-02T20:28:03Z\n"
            )
        if artifact.name == "source":
            for name, data in locks.items():
                (target / name).write_bytes(data)
        return []

    calls: list[tuple[list[str], str]] = []

    def native_fixture(
        native: source.Native,
        argv: list[str],
        name: str,
        env: dict[str, str],
        *,
        cwd: Path,
        cleaning: bool = False,
    ) -> bytes:
        calls.append((argv, name))
        assert not cleaning
        assert env["GOTOOLCHAIN"] == "local" and env["GOFLAGS"] == "-mod=readonly"
        if name == "online-go-version":
            return source.GO_VERSION.encode()
        if name == "public-module-download":
            if changed_lock is not None:
                (cwd / changed_lock).write_bytes(b"unexpected native lock mutation\n")
            return b'{"Path":"example.org/synthetic-module","Version":"v1.0.0"}'
        assert name == "online-module-verify"
        raise source.QualificationError("synthetic_stop_before_Docker")

    monkeypatch.setattr(source, "acquire", acquire_fixture)
    monkeypatch.setattr(source, "extract", extract_fixture)
    monkeypatch.setattr(source, "stage_ui", lambda *args: {"synthetic": True})
    monkeypatch.setattr(source.Native, "run", native_fixture)
    work = tmp_path / "qualification"
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--work-dir",
            str(work),
            "--timeout-seconds",
            "900",
            "--cleanup-seconds",
            "120",
        ],
    )
    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        assert source.main() == 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    assert calls[1] == (
        [str(work / "go/bin/go"), "mod", "download", "-json"],
        "public-module-download",
    )
    report = json.loads((work / "evidence/qualification.json").read_text())
    expected = "source_lock_changed" if changed_lock else "synthetic_stop_before_Docker"
    assert report["failure"] == {
        "class": "QualificationError",
        "code": expected,
        "stage": "public_native_Go_prefetch",
    }
    assert expected in capsys.readouterr().err
    assert report["status"] == "failed_or_unknown" and report["cleanup"] == []
    assert [name for _, name in calls] == (
        ["online-go-version", "public-module-download"]
        if changed_lock
        else ["online-go-version", "public-module-download", "online-module-verify"]
    )
    if changed_lock:
        assert (work / "source" / changed_lock).read_bytes() == b"unexpected native lock mutation\n"


def ghcr_synthetic_responses() -> tuple[dict[str, Any], dict[str, Any]]:
    """Synthetic fields; delimiter shape matches host observation f1459cf, not hosted parity."""
    repository = {
        "id": 123,
        "full_name": source.GHCR_REPOSITORY,
        "owner": {"id": 456, "login": source.GHCR_OWNER},
    }
    package = {
        "id": 789,
        "name": "pulseplate",
        "package_type": "container",
        "visibility": "public",
        "owner": {"id": 456, "login": source.GHCR_OWNER},
        "repository": {"id": 123, "full_name": source.GHCR_REPOSITORY},
    }
    return repository, package


def ghcr_synthetic_HTTP(value: Any) -> bytes:
    return b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\r\n" + json.dumps(value).encode()


def test_ghcr_typed_projection_does_not_copy_unused_fields() -> None:
    repository, package = ghcr_synthetic_responses()
    repository["description"] = "synthetic private unused field"
    package["url"] = "https://synthetic.invalid/unused"
    projection = source.ghcr_identity(repository, package)
    assert projection == {
        "repository": {"id": 123, "full_name": source.GHCR_REPOSITORY},
        "owner": {"id": 456, "login": source.GHCR_OWNER},
        "package": {
            "id": 789,
            "name": "pulseplate",
            "package_type": "container",
            "visibility": "public",
            "source_repository_id": 123,
        },
    }
    assert source.ghcr_response(ghcr_synthetic_HTTP(repository)) == (200, repository)
    assert "synthetic" not in json.dumps(projection)


@pytest.mark.parametrize("value", [True, False, 0, -1, "123", None, 1.25])
@pytest.mark.parametrize(
    "location", ["repository", "owner", "package", "package_owner", "linked_repository"]
)
def test_ghcr_IDs_are_positive_JSON_integers(value: Any, location: str) -> None:
    repository, package = ghcr_synthetic_responses()
    targets = {
        "repository": repository,
        "owner": repository["owner"],
        "package": package,
        "package_owner": package["owner"],
        "linked_repository": package["repository"],
    }
    targets[location]["id"] = value
    with pytest.raises(source.QualificationError, match="GHCR_positive_ID"):
        source.ghcr_identity(repository, package)


@pytest.mark.parametrize(
    "location,field,value",
    [
        ("package", "visibility", "private"),
        ("package", "package_type", "npm"),
        ("package", "name", "pulseplate-other"),
        ("package_owner", "id", 457),
        ("linked_repository", "id", 124),
        ("repository", "full_name", "other/PulsePlate"),
        ("owner", "login", "Katsiarynakavaleuskayа"),
    ],
)
def test_ghcr_cross_identity_and_public_conditions_fail_closed(
    location: str, field: str, value: Any
) -> None:
    repository, package = ghcr_synthetic_responses()
    targets = {
        "repository": repository,
        "owner": repository["owner"],
        "package": package,
        "package_owner": package["owner"],
        "linked_repository": package["repository"],
    }
    targets[location][field] = value
    with pytest.raises(source.QualificationError):
        source.ghcr_identity(repository, package)


@pytest.mark.parametrize("body", [b'{"id":1,"id":2}', b'{"id":NaN}', b"{}{}", b"[]", b"{", b""])
def test_ghcr_requires_one_complete_unique_finite_JSON_object(body: bytes) -> None:
    with pytest.raises((source.QualificationError, ValueError)):
        source.ghcr_response(b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\r\n" + body)


@pytest.mark.parametrize(
    "raw,diagnostic",
    [
        (b"{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 403 Forbidden\nContent-Type: application/json\r\n\r\n{}",
            "GHCR_HTTP_status_403",
        ),
        (b"HTTP/2.0 302 Found\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_status_302"),
        (b"HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_status"),
        (b"HTTP/2.0 200 OK\n\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 200 OK\nContent-Type: application/json\nX-Test: value\r\n\r\n{}",
            "GHCR_HTTP_header",
        ),
        (
            b"HTTP/2.0 200 OK\nContent-Type: application/json\rX-Test: value\r\n\r\n{}",
            "GHCR_HTTP_header",
        ),
        (b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\n{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 200 OK trailing\x00\nContent-Type: application/json\r\n\r\n{}",
            "GHCR_HTTP_status",
        ),
    ],
)
def test_ghcr_requires_observed_native_delimiters_and_success(raw: bytes, diagnostic: str) -> None:
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.ghcr_response(raw)


def test_ghcr_host_observed_status_LF_and_strict_header_CRLF_shape() -> None:
    repository, _ = ghcr_synthetic_responses()
    status = bytes.fromhex("485454502f322e3020323030204f4b0a")
    raw = (
        status
        + b"Content-Type: application/json\r\nX-Synthetic: unused\r\n\r\n"
        + json.dumps(repository).encode()
    )
    assert source.ghcr_response(raw) == (200, repository)
    # Only status/delimiter shape is native-observed; body/headers are synthetic.
    with pytest.raises(source.QualificationError, match="GHCR_HTTP_header"):
        source.ghcr_response(status + b"X-Synthetic: " + b"x" * 32768 + b"\r\n\r\n{}")


def test_ghcr_mode_cannot_fall_through_to_source_qualify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called: list[str] = []
    monkeypatch.setattr(source, "qualify", lambda *args: called.append("source"))
    monkeypatch.setattr(
        source, "qualify_existing_ghcr_package", lambda *args: called.append("GHCR")
    )
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--qualify-existing-ghcr-package",
            "--public-output",
            str(tmp_path / "public.json"),
            "--work-dir",
            str(tmp_path / "private"),
            "--timeout-seconds",
            "90",
            "--cleanup-seconds",
            "30",
        ],
    )
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        assert source.main() == 0
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    assert called == ["GHCR"]


@pytest.mark.parametrize("selector", [[], ["--qualify-existing-ghcr-package"]])
def test_ghcr_mixed_flags_reject_before_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, selector: list[str]
) -> None:
    monkeypatch.setattr(source, "qualify", lambda *args: pytest.fail("source operation"))
    monkeypatch.setattr(
        source,
        "qualify_existing_ghcr_package",
        lambda *args: pytest.fail("authenticated operation"),
    )
    args = [
        "qualifier",
        "--work-dir",
        str(tmp_path / "private"),
        "--timeout-seconds",
        "90",
        "--cleanup-seconds",
        "30",
        *selector,
    ]
    if not selector:
        args += ["--public-output", str(tmp_path / "public.json")]
    monkeypatch.setattr(source.sys, "argv", args)
    with pytest.raises(SystemExit) as error:
        source.main()
    assert error.value.code == 2


@pytest.mark.parametrize(
    "mode",
    [
        "immediate_exit",
        "auth_nonzero",
        "API_nonzero",
        "API_403",
        "auth_reflection",
        "header_reflection",
        "unused_body_reflection",
        "stderr_reflection",
        "output_bound",
        "deadline",
        "cleanup_failure",
        "owned_residual",
        "owned_residual_exec_exit",
    ],
)
def test_ghcr_fixed_native_capture_and_hygiene(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    """Real child pipes/processes, synthetic GH program; not an authenticated API proof."""
    runner = tmp_path.resolve()
    repository, package = ghcr_synthetic_responses()
    trace = runner / "synthetic-command-trace.jsonl"
    gh = runner / "synthetic-gh"
    child_code = (
        "import os,signal,time\nfrom pathlib import Path\n"
        + "marker=Path("
        + repr(str(trace.with_suffix(".child-signal")))
        + ")\n"
        + "ready=Path("
        + repr(str(trace.with_suffix(".child-ready")))
        + ")\n"
        + "def terminate(signum, frame):\n marker.write_text('SIGTERM\\n')\n"
        + (
            " os.execv('/bin/sleep', ['/bin/sleep', '0.2'])\n"
            if mode == "owned_residual_exec_exit"
            else " raise SystemExit(128+signum)\n"
        )
        + "signal.signal(signal.SIGTERM, terminate)\nready.write_text('ready')\ntime.sleep(5)\n"
    )
    gh.write_text(
        "#!"
        + source.sys.executable
        + "\n"
        + "import os,sys,json,time,subprocess\nfrom pathlib import Path\n"
        + "mode="
        + repr(mode)
        + "\nrepository="
        + repr(repository)
        + "\npackage="
        + repr(package)
        + "\n"
        + "trace=Path("
        + repr(str(trace))
        + ")\n"
        + "child_code="
        + repr(child_code)
        + "\n"
        + "with trace.open('a') as output: output.write(json.dumps({'argv':sys.argv[1:],'environment_keys':sorted(os.environ)})+'\\n')\n"
        + "token=os.environ['GH_TOKEN']\n"
        + "if sys.argv[1:]==['auth','status','--hostname','github.com']:\n"
        + " if mode in ('owned_residual','owned_residual_exec_exit'):\n"
        + "  child=subprocess.Popen([sys.executable,'-c',child_code],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
        + "  trace.with_suffix('.child-pid').write_text(str(child.pid))\n"
        + "  ready=trace.with_suffix('.child-ready'); ready_deadline=time.monotonic()+1\n"
        + "  while not ready.exists():\n"
        + "   assert time.monotonic()<ready_deadline\n"
        + "   time.sleep(0.01)\n"
        + "  time.sleep(0.5)\n"
        + " if mode=='deadline': time.sleep(3)\n"
        + " if mode=='output_bound': sys.stdout.write('x'*(1024**2+1))\n"
        + " elif mode=='auth_reflection': sys.stdout.write(token)\n"
        + " else: sys.stdout.write('synthetic auth status')\n"
        + " sys.exit(1 if mode=='auth_nonzero' else 0)\n"
        + "assert sys.argv[1:9]==['api','--hostname','github.com','--method','GET','--include','-H','Accept:application/vnd.github+json']\n"
        + "endpoint=sys.argv[9]\nvalue=repository if endpoint=='/repos/Katsiarynakavaleuskaya/PulsePlate' else package\n"
        + "if mode=='unused_body_reflection': value['unused']=token\n"
        + "header='HTTP/2.0 200 OK\\nContent-Type: application/json\\r\\n'\n"
        + "if mode=='header_reflection': header+='X-Synthetic: '+token+'\\r\\n'\n"
        + "if mode=='API_403': header='HTTP/2.0 403 Forbidden\\nContent-Type: application/json\\r\\n'; value={'message':'synthetic forbidden'}\n"
        + "sys.stdout.write(header+'\\r\\n'+json.dumps(value))\n"
        + "if mode=='stderr_reflection': sys.stderr.write(token)\n"
        + "if mode=='cleanup_failure': (Path.cwd()/'home'/'unexpected').write_text('synthetic empty-state violation')\n"
        + "sys.exit(1 if mode in ('API_nonzero','API_403') else 0)\n"
    )
    gh.chmod(0o700)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    credential = "synthetic.opaque.step.credential.without.length.assumptions"
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": "Linux",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_JOB": "prometheus-ghcr-package-qualification",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "RUNNER_TEMP": str(runner),
        "GH_TOKEN": credential,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    monkeypatch.setattr(
        source.Native, "run", lambda *args, **kwargs: pytest.fail("credential-bearing Native.run")
    )
    work, public = (
        runner / "ghcr-private-123-1",
        runner / "ghcr-public-123-1" / "qualification.json",
    )
    real_popen = source.subprocess.Popen
    declared_environment_keys: list[set[str]] = []
    declared_commands: list[list[str]] = []

    def observe_environment(argv: list[str], *args: Any, **kwargs: Any) -> Any:
        if argv and argv[0] == str(gh):
            environment = kwargs["env"]
            declared_environment_keys.append(set(environment))
            declared_commands.append(argv[1:])
            assert environment["GH_TOKEN"] == credential  # Explicit synthetic fixture only.
            assert environment["HOME"] == str(work / "home")
            assert environment["GH_CONFIG_DIR"] == str(work / "config")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(source.subprocess, "Popen", observe_environment)
    if mode == "immediate_exit":
        result = source.qualify_existing_ghcr_package(work, public, 8, 2)
        assert result == json.loads(public.read_bytes()) and result["qualified"] is True
        assert result["package"]["id"] == 789
        assert credential.encode() not in public.read_bytes()
    else:
        errors = (source.QualificationError, TimeoutError)
        if mode == "deadline":
            errors += (source.subprocess.TimeoutExpired,)
        with pytest.raises(errors) as failure:
            source.qualify_existing_ghcr_package(work, public, 1 if mode == "deadline" else 8, 2)
        assert not public.exists() and not public.parent.exists()
        if mode == "deadline":
            if isinstance(failure.value, source.subprocess.TimeoutExpired):
                assert failure.value.cmd == [
                    "/bin/ps",
                    "-axo",
                    "pid,ppid,pgid,uid,lstart,state,comm",
                ]
                assert 0 < failure.value.timeout <= 1
            else:
                assert isinstance(failure.value, source.QualificationError)
                assert str(failure.value) == "qualification_deadline"
        if mode == "API_403":
            assert isinstance(failure.value, source.QualificationError)
            assert str(failure.value) == "GHCR_native_exit_1_GHCR_HTTP_status_403"
        if mode in {"owned_residual", "owned_residual_exec_exit"}:
            assert isinstance(failure.value, source.QualificationError)
            assert str(failure.value) == "GHCR_owned_group_survived"
            assert trace.with_suffix(".child-signal").read_bytes() == b"SIGTERM\n"
    assert trace.exists() or mode == "deadline"
    commands = (
        [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    )
    if mode == "deadline":
        # A real deadline may kill the child before its first Python trace write.
        assert len(commands) in {0, 1}
        assert declared_commands in ([], [["auth", "status", "--hostname", "github.com"]])
    else:
        assert len(commands) == (
            3
            if mode in {"immediate_exit", "cleanup_failure"}
            else (
                2
                if mode
                in {
                    "API_nonzero",
                    "API_403",
                    "header_reflection",
                    "unused_body_reflection",
                    "stderr_reflection",
                }
                else 1
            )
        )
    if commands:
        assert commands[0]["argv"] == ["auth", "status", "--hostname", "github.com"]
    assert [command["argv"] for command in commands] == declared_commands[: len(commands)]
    expected_environment_keys = {
        "PATH",
        "LANG",
        "LC_ALL",
        "GH_HOST",
        "GH_TOKEN",
        "GH_PROMPT_DISABLED",
        "GH_PAGER",
        "PAGER",
        "GH_NO_UPDATE_NOTIFIER",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER",
        "GH_TELEMETRY",
        "DO_NOT_TRACK",
        "HOME",
        "GH_CONFIG_DIR",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "TMPDIR",
    }
    assert len(declared_environment_keys) == len(declared_commands)
    if mode != "deadline":
        assert len(declared_commands) == len(commands)
    assert all(keys == expected_environment_keys for keys in declared_environment_keys)
    # The OS/runtime can inject non-selected metadata (observed macOS CF key).
    # Check credential/config selectors in the real child without authorizing an OS-key allowlist.
    selectors = {
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "DEBUG",
        "GIT_TRACE",
        "GIT_CURL_VERBOSE",
        "PYTHONPATH",
        "PYTHONHOME",
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "BASH_ENV",
        "ENV",
        "SSH_ASKPASS",
        "GIT_ASKPASS",
    }
    for command in commands:
        selected = {
            key
            for key in command["environment_keys"]
            if key.startswith(("GH_", "GITHUB_")) or key in selectors
        }
        assert selected == {key for key in expected_environment_keys if key.startswith("GH_")}
    assert not any("GITHUB_TOKEN" in command["environment_keys"] for command in commands)
    assert not work.exists() if mode != "cleanup_failure" else work.exists()
    assert not list(runner.glob("**/*.stdout")) and not list(runner.glob("**/*.stderr"))
    if mode in {"owned_residual", "owned_residual_exec_exit"}:
        child_pid = int(trace.with_suffix(".child-pid").read_text())
        with pytest.raises(ProcessLookupError):
            source.os.kill(child_pid, 0)


def test_GHCR_observation_job_has_only_read_permission_and_exact_public_artifact() -> None:
    import yaml

    workflow = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".github/workflows/build.yml").read_text()
    )
    job = workflow["jobs"]["prometheus-ghcr-package-qualification"]
    assert (
        job["if"]
        == "github.event_name == 'workflow_dispatch' && inputs.mode == 'prometheus-source-qualify' && github.repository == 'Katsiarynakavaleuskaya/PulsePlate'"
    )
    assert job["permissions"] == {"contents": "read", "packages": "read"}
    assert (
        job["timeout-minutes"]
        == "${{ fromJSON(vars.PROMETHEUS_GHCR_QUALIFICATION_TIMEOUT_MINUTES || '3') }}"
    )
    assert job["env"] == {
        "PROMETHEUS_GHCR_QUALIFICATION_SECONDS": "90",
        "PROMETHEUS_GHCR_CLEANUP_SECONDS": "30",
    }
    steps = job["steps"]
    assert steps[1]["with"] == {"persist-credentials": False, "ref": "${{ github.sha }}"}
    assert "\"$GITHUB_RUN_ATTEMPT\" != '1'" in steps[0]["run"]
    assert [step.get("env") for step in steps if "env" in step] == [
        {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
    ]
    observe, retain = steps[3], steps[4]
    assert observe["id"] == "package" and "--qualify-existing-ghcr-package" in observe["run"]
    assert '--timeout-seconds "$PROMETHEUS_GHCR_QUALIFICATION_SECONDS"' in observe["run"]
    assert '--cleanup-seconds "$PROMETHEUS_GHCR_CLEANUP_SECONDS"' in observe["run"]
    assert retain["if"] == "${{ success() && steps.package.outputs.qualified == 'true' }}"
    assert (
        retain["with"]["path"]
        == "${{ runner.temp }}/ghcr-public-${{ github.run_id }}-${{ github.run_attempt }}/qualification.json"
    )
    assert retain["with"]["if-no-files-found"] == "error"
    assert job["outputs"] == {"qualified": "${{ steps.package.outputs.qualified }}"}
    serialized = json.dumps(job)
    for forbidden in (
        "packages: write",
        "docker login",
        "docker build",
        "go build",
        "GHCR_READ_TOKEN",
        "DHI",
        "GITHUB_ENV",
        "always()",
        "*.stdout",
        "*.stderr",
    ):
        assert forbidden not in serialized
    # Real heavy jobs are absent at this stage; this test makes no heavy dependency claim.


def test_selected_Main_object_is_distinct_from_download_identity() -> None:
    objects = [
        {"Path": source.ROOT_MODULE, "Main": True, "UnknownNativeField": {"retained": 1}},
        {"Path": "golang.org/x/net", "Version": "v0.60.0", "GoModSum": "h1:synthetic"},
    ]
    raw = b"\n".join(json.dumps(value).encode() for value in objects)
    assert source.decode_selected_modules(raw) == {value["Path"]: value for value in objects}
    with pytest.raises(source.QualificationError):
        source.decode_modules(raw)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-root",
        "wrong-root",
        "duplicate-path",
        "Main-int",
        "dependency-no-version",
        "Path-none",
        "Path-int",
        "Replace-error",
    ],
)
def test_selected_modules_reject_incomplete_or_conflicting_native_identity(fault: str) -> None:
    values = [{"Path": source.ROOT_MODULE, "Main": True}, {"Path": "x", "Version": "v1.0.0"}]
    if fault == "missing-root":
        values.pop(0)
    elif fault == "wrong-root":
        values[0]["Path"] = "other/root"
    elif fault == "duplicate-path":
        values.append({"Path": "x", "Version": "v2.0.0"})
    elif fault == "Main-int":
        values[0]["Main"] = 1
    elif fault == "dependency-no-version":
        values[1].pop("Version")
    elif fault == "Path-none":
        values[1]["Path"] = None
    elif fault == "Path-int":
        values[1]["Path"] = 1
    else:
        values[1]["Replace"] = {"Path": "replacement", "Error": {"Err": "synthetic"}}
    with pytest.raises(source.QualificationError):
        source.decode_selected_modules(b"\n".join(json.dumps(value).encode() for value in values))


def test_replay_coordinate_correspondence_retains_every_other_native_field(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    left = {
        "Path": "x",
        "Version": "v1",
        "Dir": str(a / "modules/x"),
        "GoMod": str(a / "modules/x/go.mod"),
        "Origin": {"URL": "https://example.invalid/x"},
        "Replace": {"Path": "replacement", "Dir": str(a / "source/local")},
        "Unknown": [1, 2],
    }
    right = json.loads(json.dumps(left).replace(str(a), str(b)))
    observed = source.replay_coordinates(left, a / "source", a / "modules", download=False)
    assert observed == source.replay_coordinates(right, b / "source", b / "modules", download=False)
    assert observed["Origin"] == left["Origin"] and observed["Unknown"] == [1, 2]
    assert left["Dir"] == str(a / "modules/x")
    right["Unknown"] = [2, 1]
    assert observed != source.replay_coordinates(right, b / "source", b / "modules", download=False)
    left["Unknown"] = "arbitrary text containing " + str(a / "source")
    right["Unknown"] = "arbitrary text containing " + str(b / "source")
    assert source.replay_coordinates(
        left, a / "source", a / "modules", download=False
    ) != source.replay_coordinates(right, b / "source", b / "modules", download=False)
    for path in (str(a / "modules") + "/../escape", str(a / "modules") + "-alias/x", "/unbound/x"):
        with pytest.raises(source.QualificationError):
            source.replay_coordinates({"Dir": path}, a / "source", a / "modules", download=False)


@pytest.mark.parametrize(
    "extra",
    [
        ["--qualify-existing-ghcr-package", "--public-output", "public.json"],
        ["--public-output", "public.json"],
        ["--derive-xnet06"],
    ],
)
def test_fixed_derivation_selector_rejects_mixed_or_abbreviated_modes_before_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra: list[str]
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Selector rejected after protected effect")

    monkeypatch.setattr(source, "qualify", forbidden)
    monkeypatch.setattr(source, "qualify_existing_ghcr_package", forbidden)
    monkeypatch.setattr(source.signal, "signal", forbidden)
    args = [
        "qualifier",
        "--work-dir",
        str(tmp_path / "uncreated"),
        "--timeout-seconds",
        "900",
        "--cleanup-seconds",
        "120",
    ]
    if extra != ["--derive-xnet06"]:
        args.append("--derive-xnet060")
    monkeypatch.setattr(source.sys, "argv", args + extra)
    with pytest.raises(SystemExit) as error:
        source.main()
    assert error.value.code == 2
    assert not (tmp_path / "uncreated").exists()


@pytest.mark.parametrize(
    "fault",
    ["none", "base-lock", "get-error", "derived-download-sum", "b-lock-mismatch", "get-nonlock"],
)
def test_derivation_controller_uses_two_clean_original_fixed_get_replays_or_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    """Synthetic native transcript only; it cannot qualify Go, source or closure."""
    work = tmp_path / "work"
    work.mkdir()
    evidence = work / "evidence"
    evidence.mkdir()
    original = {"go.mod": b"original module\n", "go.sum": b"original sums\n"}
    derived = {"go.mod": b"derived module\n", "go.sum": b"derived sums\n"}
    monkeypatch.setattr(source, "LOCKS", {name: source.sha(raw) for name, raw in original.items()})
    go = work / "go"
    (go / "bin").mkdir(parents=True)
    (go / "bin/go").write_bytes(b"inert Go fixture")
    ui = work / "ui"
    ui.mkdir()
    downloads = work / "downloads"
    downloads.mkdir()
    a = work / "source"
    a.mkdir()

    def populate(target: Path) -> None:
        for name, raw in original.items():
            (target / name).write_bytes(raw)
        (target / "retained.go").write_bytes(b"inert source\n")

    populate(a)

    def extracted(
        artifact: source.Artifact, archive: Path, target: Path, deadline: float
    ) -> list[dict[str, Any]]:
        assert not target.exists()
        target.mkdir()
        populate(target)
        return []

    monkeypatch.setattr(source, "extract", extracted)
    monkeypatch.setattr(source, "stage_ui", lambda *args: {"synthetic": True})
    transcript: list[tuple[list[str], dict[str, str], Path]] = []

    class FakeNative:
        deadline = source.time.monotonic() + 900

        def __init__(self) -> None:
            self.evidence = evidence

        def run(
            self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            transcript.append((argv, dict(env), cwd))
            if argv[0] == "/usr/bin/docker":
                if "ps" in argv:
                    return b""
                if "pull" in argv:
                    return b""
                return json.dumps(
                    [
                        {
                            "Id": source.BASE_CONFIG,
                            "Os": "linux",
                            "Architecture": "amd64",
                            "RepoDigests": [source.BASE],
                            "Config": {"Env": []},
                        }
                    ]
                ).encode()
            command = argv[1:]
            changed = (cwd / "go.mod").read_bytes() != original["go.mod"]
            version = "v0.60.0" if changed else "v0.58.0"
            if command == ["get", "golang.org/x/net@v0.60.0"]:
                assert env["GOFLAGS"] == "" and not changed
                if fault == "get-error":
                    raise source.QualificationError("synthetic_get_failure")
                for file, raw in derived.items():
                    (cwd / file).write_bytes(
                        raw
                        + (
                            b"different\n"
                            if fault == "b-lock-mismatch"
                            and cwd.name == "source-b"
                            and file == "go.sum"
                            else b""
                        )
                    )
                if fault == "get-nonlock":
                    (cwd / "retained.go").write_bytes(b"unexpected source")
                return b""
            assert env["GOFLAGS"] == "-mod=readonly"
            if command == ["version"]:
                return source.GO_VERSION.encode()
            if command == ["mod", "edit", "-json"]:
                if fault == "base-lock" and not changed:
                    (cwd / "go.sum").write_bytes(b"unexpected sum")
                return json.dumps(
                    {
                        "Module": {"Path": source.ROOT_MODULE},
                        "Go": "1.26.0",
                        "Unknown": {"retain": True},
                    }
                ).encode()
            if command == ["mod", "download", "-json"]:
                directory = Path(env["GOMODCACHE"]) / ("xnet@" + version)
                directory.mkdir(exist_ok=True)
                (directory / "go.mod").write_bytes(b"inert cache")
                if changed and fault == "derived-download-sum":
                    (cwd / "go.sum").write_bytes(b"late sum write")
                return json.dumps(
                    {
                        "Path": "golang.org/x/net",
                        "Version": version,
                        "Dir": str(directory),
                        "GoMod": str(directory / "go.mod"),
                    }
                ).encode()
            if command == ["mod", "verify"]:
                return b"all modules verified\n"
            if command == ["list", "-m", "-json", "all"]:
                values = [
                    {
                        "Path": source.ROOT_MODULE,
                        "Main": True,
                        "Dir": str(cwd),
                        "GoMod": str(cwd / "go.mod"),
                    },
                    {
                        "Path": "golang.org/x/net",
                        "Version": version,
                        "Dir": str(Path(env["GOMODCACHE"]) / ("xnet@" + version)),
                    },
                ]
                return b"\n".join(json.dumps(value).encode() for value in values)
            if command == ["mod", "graph"]:
                return (source.ROOT_MODULE + " golang.org/x/net@" + version + "\n").encode()
            raise AssertionError(command)

    offline: list[tuple[str, Path]] = []

    def observed(
        native: Any, root: Path, tool: Path, modules: Path, expected: dict[str, bytes], *args: Any
    ) -> dict[str, Any]:
        assert source._derivation_locks(root) == expected
        offline.append((root.name, modules))
        return {
            "full_native_package_objects": {
                "prometheus": {"p": {"ImportPath": "p"}},
                "promtool": {"t": {"ImportPath": "t"}},
            }
        }

    monkeypatch.setattr(source, "_derivation_offline", observed)
    report: dict[str, Any] = {"UI_transform": {"synthetic": True}}
    native = FakeNative()
    if fault == "none":
        source.derive_xnet060_observe(
            native, work, downloads, a, go, ui, {}, "/usr/bin/docker", work, {}, report
        )
        assert len(report["module_derivation"]["replays"]) == 2
        assert len(offline) == 2 and offline[0][1] != offline[1][1]
        assert (evidence / "a-module-derivation.patch").read_bytes() == (
            evidence / "b-module-derivation.patch"
        ).read_bytes()
    else:
        with pytest.raises(source.QualificationError):
            source.derive_xnet060_observe(
                native, work, downloads, a, go, ui, {}, "/usr/bin/docker", work, {}, report
            )
    gets = [(argv, env, cwd) for argv, env, cwd in transcript if argv[1:2] == ["get"]]
    assert len(gets) == (
        2 if fault in ("none", "b-lock-mismatch") else 0 if fault == "base-lock" else 1
    )
    for argv, env, cwd in gets:
        assert argv[1:] == ["get", "golang.org/x/net@v0.60.0"] and env["GOFLAGS"] == ""
    for argv, env, cwd in transcript:
        if argv[0] != "/usr/bin/docker" and argv[1:2] != ["get"]:
            assert env["GOFLAGS"] == "-mod=readonly"
        if argv[1:3] == ["mod", "download"]:
            assert argv[1:] == ["mod", "download", "-json"]


@pytest.mark.parametrize("missing", [False, True])
def test_derivation_offline_keeps_both_production_graphs_and_existing_sandbox_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: bool
) -> None:
    """Synthetic owned-container outcomes; no native executable is started."""
    root, go, modules, evidence = [
        tmp_path / name for name in ("source", "go", "modules", "evidence")
    ]
    for path in (root, go / "bin", modules, evidence):
        path.mkdir(parents=True)
    (root / "go.mod").write_bytes(b"frozen mod")
    (root / "go.sum").write_bytes(b"frozen sum")
    (go / "bin/go").write_bytes(b"inert tool")
    (modules / "cache").write_bytes(b"inert cache")
    frozen = source._derivation_locks(root)
    remainder = source._derivation_nonlocks(root, source.time.monotonic() + 900)
    created: list[list[str]] = []

    class FakeNative:
        deadline = source.time.monotonic() + 900

        def __init__(self) -> None:
            self.evidence = evidence

        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            if "create" in argv:
                created.append(argv)
                return b"owned"
            return b"[{}]"

    monkeypatch.setattr(source, "validate_container", lambda *args: None)

    def completed(
        native: Any,
        docker: str,
        config: Path,
        name: str,
        expected: dict[str, Any],
        label: str,
        *args: Any,
    ) -> tuple[bytes, dict[str, Any]]:
        command = expected["command"]
        if command == ["version"]:
            raw = source.GO_VERSION.encode()
        elif command == ["mod", "verify"]:
            raw = b"all modules verified"
        else:
            selected = command[-1].rsplit("/", 1)[-1]
            raw = package_stream("prometheus" if missing and selected == "promtool" else selected)
        return raw, {"Running": False, "ExitCode": 0, "OOMKilled": False}

    monkeypatch.setattr(source, "start_owned", completed)
    arguments = (
        FakeNative(),
        root,
        go,
        modules,
        frozen,
        remainder,
        source.file_hash(go / "bin/go"),
        "a",
        "/usr/bin/docker",
        tmp_path,
        {"Id": source.BASE_CONFIG, "Config": {"Env": []}},
        "synthetic-owner",
        [],
        {},
        {},
        tmp_path,
    )
    if missing:
        with pytest.raises(source.QualificationError):
            source._derivation_offline(*arguments)
    else:
        result = source._derivation_offline(*arguments)
        assert set(result["command_observations"]) == {"prometheus", "promtool"}
        assert set(result["full_native_package_objects"]) == {"prometheus", "promtool"}
        assert len(result["container_completion"]) == 4
    assert len(created) == 4
    for argv in created:
        assert argv[argv.index("--network") + 1] == "none"
        assert argv[argv.index("--user") + 1] == "65532:65532"
        assert "--read-only" in argv
        assert all(
            value.endswith(",readonly")
            for index, value in enumerate(argv)
            if index and argv[index - 1] == "--mount"
        )
