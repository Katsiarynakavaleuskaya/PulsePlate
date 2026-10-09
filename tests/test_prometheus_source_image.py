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
