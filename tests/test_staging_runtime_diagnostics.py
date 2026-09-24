"""OPS-03A: bounded, read-only staging diagnostic contract tests."""

from __future__ import annotations

import json
import io
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time
from typing import Any
from contextlib import redirect_stdout
from types import ModuleType

import pytest

from scripts.ops import staging_runtime_diagnostics as diagnostic


def observation() -> dict[str, Any]:
    return {
        "health": {"status": "response", "code": 200},
        "ready": {"status": "response", "code": 200},
        "database": {
            "status": "response",
            "database_match": True,
            "role_match": True,
            "server_version": "15.19",
            "in_recovery": False,
            "tls": True,
            "tls_version": "TLSv1.3",
            "activity": {"visibility": "complete", "active": 1, "waiting": 0, "sessions": 1},
        },
    }


def payload(value: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "pulseplate.staging-runtime-host.v1",
        "trust": "accepted",
        "fingerprint": "a" * 64,
        "observation": value or observation(),
    }


def host_functions() -> dict[str, Any]:
    namespace: dict[str, Any] = {"__name__": "ops03a_host_test"}
    source = diagnostic.HOST_PROBE.rsplit("\nmain()", 1)[0]
    exec(compile(source, "<fixed-host-probe>", "exec"), namespace)
    return namespace


def app_functions(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    source = host_functions()["APP_PROBE"].rsplit("\nprint(json.dumps", 1)[0]
    namespace: dict[str, Any] = {"__name__": "ops03a_app_test"}
    monkeypatch.setattr(sys, "argv", ["probe", "pulseplate", "pulseplate"])
    for key in tuple(os.environ):
        if key.startswith("PG"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PGSSLMODE", "verify-full")
    monkeypatch.setenv("PGPASSFILE", "/run/secrets/postgres_pgpass")
    exec(compile(source, "<fixed-app-probe>", "exec"), namespace)
    return namespace


def selected_container(
    service: str, *, oneoff: str = "False", started: str = "2026-09-24T00:00:00Z"
) -> dict[str, Any]:
    image = "sha256:" + "b" * 64
    return {
        "Id": "a" * 64,
        "Image": image,
        "Config": {
            "Image": "example.invalid/" + service + ":test",
            "Labels": {
                "com.docker.compose.project": "pulseplate-staging",
                "com.docker.compose.service": service,
                "com.docker.compose.oneoff": oneoff,
                "com.docker.compose.config-hash": "c" * 64,
            },
        },
        "State": {"Running": True, "Status": "running", "StartedAt": started},
    }


def compose_fixture() -> dict[str, Any]:
    return {
        "name": "pulseplate-staging",
        "services": {
            "app": {"image": "example.invalid/app:test"},
            "postgres": {
                "image": "example.invalid/postgres:test",
                "environment": {"POSTGRES_DB": "pulseplate", "POSTGRES_USER": "pulseplate"},
            },
        },
    }


@pytest.fixture
def local_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SSH_HOST_STAGING", "192.0.2.12")
    monkeypatch.setattr(diagnostic, "_ssh_argv", lambda host, home: ["/usr/bin/ssh", host])
    monkeypatch.setattr(
        diagnostic,
        "_ssh_observe",
        lambda argv: json.dumps(payload()).encode(),
    )


@pytest.fixture
def pinned_ssh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake = tmp_path / "fixed-ssh"
    fake.write_text("fixture")
    fake.chmod(0o700)
    monkeypatch.setattr(diagnostic, "SSH_BINARY", fake)
    return fake


def test_t01_staging_json_success(local_run: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == diagnostic.SCHEMA
    assert result["status"] == "complete"
    assert result["environment"] == "staging"
    assert result["fingerprint"] == "a" * 64
    assert result["observed_at"] == result["observation_window"]["completed_at"]
    assert (
        result["observation_window"]["started_at"] <= result["observation_window"]["completed_at"]
    )


def test_observation_window_brackets_ssh_response(
    local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[str] = []

    def now() -> str:
        events.append("clock")
        return "2026-09-24T00:00:00Z" if len(events) == 1 else "2026-09-24T00:00:01Z"

    def observe(argv: list[str]) -> bytes:
        events.append("ssh")
        return json.dumps(payload()).encode()

    monkeypatch.setattr(diagnostic, "_utc_now", now)
    monkeypatch.setattr(diagnostic, "_ssh_observe", observe)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert events == ["clock", "ssh", "clock"]
    assert result["observation_window"] == {
        "started_at": "2026-09-24T00:00:00Z",
        "completed_at": "2026-09-24T00:00:01Z",
    }


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--environment", "production", "--format", "json"],
        ["--environment", "staging", "--format", "text"],
    ],
)
def test_t02_invalid_selector_returns_two(
    argv: list[str], local_run: None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert diagnostic.main(argv) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "host", ["", "user@server", "-oProxyCommand=bad", "host; echo secret", "host/path"]
)
def test_t03_invalid_host_returns_two(
    host: str, local_run: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SSH_HOST_STAGING", host)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 2


def test_t04_ssh_pins_identity_and_host_key(tmp_path: Path, pinned_ssh: Path) -> None:
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    ssh_dir.chmod(0o700)
    (ssh_dir / "pulseplate_staging_obs1_20260824").write_text("fake")
    (ssh_dir / "known_hosts_pulseplate_staging_obs1_20260824").write_text("fake")
    (ssh_dir / "pulseplate_staging_obs1_20260824").chmod(0o600)
    (ssh_dir / "known_hosts_pulseplate_staging_obs1_20260824").chmod(0o600)
    argv = diagnostic._ssh_argv("192.0.2.12", tmp_path)
    assert argv[:3] == [str(pinned_ssh), "-F", "/dev/null"]
    assert "StrictHostKeyChecking=yes" in argv
    assert "BatchMode=yes" in argv
    assert "IdentitiesOnly=yes" in argv
    assert "pulseplate-ops" in argv
    assert argv[-1] == "sudo -n /usr/bin/python3 -"
    assert "ProxyCommand=none" in argv and "ProxyJump=none" in argv


def test_t05_missing_ssh_files_fail_closed(tmp_path: Path, pinned_ssh: Path) -> None:
    with pytest.raises(RuntimeError, match="SSH_IDENTITY_UNAVAILABLE"):
        diagnostic._ssh_argv("192.0.2.12", tmp_path)


@pytest.mark.parametrize("fault", ["symlink", "mode", "directory"])
def test_ssh_identity_files_reject_symlink_or_weak_permissions(
    tmp_path: Path, pinned_ssh: Path, fault: str
) -> None:
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(mode=0o700)
    key = ssh_dir / "pulseplate_staging_obs1_20260824"
    known = ssh_dir / "known_hosts_pulseplate_staging_obs1_20260824"
    key.write_text("fake")
    known.write_text("fake")
    key.chmod(0o600)
    known.chmod(0o600)
    if fault == "symlink":
        known.unlink()
        known.symlink_to(key)
    elif fault == "mode":
        key.chmod(0o644)
    else:
        ssh_dir.chmod(0o755)
    with pytest.raises(RuntimeError, match="SSH_IDENTITY_UNAVAILABLE"):
        diagnostic._ssh_argv("192.0.2.12", tmp_path)


@pytest.mark.parametrize(
    "code",
    [
        "STAGING_RECEIPT_FAILED",
        "CONTAINER_SELECTION_FAILED",
        "CONTAINER_IDENTITY_UNTRUSTED",
        "CONTAINER_GENERATION_CHANGED",
    ],
)
def test_t06_t08_t19_remote_trust_failures_return_three(
    code: str, local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        diagnostic,
        "_ssh_observe",
        lambda argv: json.dumps(
            {"schema": "pulseplate.staging-runtime-host.v1", "trust": "rejected", "error": code}
        ).encode(),
    )
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.strip() == code


def test_t07_exact_non_oneoff_census_and_prepost_identity() -> None:
    source = diagnostic.HOST_PROBE
    assert "label=com.docker.compose.project=pulseplate-staging" in source
    assert "label=com.docker.compose.oneoff=False" in source
    assert "len(ids) != 1" in source
    assert "app_before != app_after or db_before != db_after" in source
    assert "started_at" in source and "config_hash" in source
    assert 'config["Image"] != compose["services"][service]["image"]' in source


@pytest.mark.parametrize(
    "ids,oneoff", [(["a" * 64, "b" * 64], "False"), (["a" * 64], "True"), ([], "False")]
)
def test_t07_host_selection_rejects_duplicate_oneoff_or_absent(ids: list[str], oneoff: str) -> None:
    namespace = host_functions()

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        if argv[1] == "ps":
            assert "label=com.docker.compose.oneoff=False" in argv
            return 0, ("\n".join(ids) + "\n").encode()
        return 0, json.dumps([selected_container("app", oneoff=oneoff)]).encode()

    namespace["run"] = run
    with pytest.raises(
        RuntimeError, match="CONTAINER_SELECTION_FAILED|CONTAINER_IDENTITY_UNTRUSTED"
    ):
        namespace["selected"]("app", compose_fixture(), "c" * 64)


def test_t19_host_rejects_generation_drift_after_app_probe() -> None:
    namespace = host_functions()
    selected_count = 0
    compose = compose_fixture()

    def selected(service: str, source: dict[str, Any], expected_hash: str) -> dict[str, str]:
        nonlocal selected_count
        selected_count += 1
        return {
            "id": "a" * 64,
            "image": "sha256:" + "b" * 64,
            "config_hash": "c" * 64,
            "started_at": "changed" if selected_count == 3 else "initial",
        }

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        if "--hash" in argv:
            return 0, (argv[-1] + " " + "c" * 64 + "\n").encode()
        if "compose" in argv:
            return 0, json.dumps(compose).encode()
        if "check_staging_security.py" in " ".join(argv):
            return 0, b"ok"
        return 0, json.dumps(observation()).encode()

    namespace["selected"] = selected
    namespace["run"] = run
    output = io.StringIO()
    with redirect_stdout(output):
        namespace["main"]()
    result = json.loads(output.getvalue())
    assert result == {
        "schema": "pulseplate.staging-runtime-host.v1",
        "trust": "rejected",
        "error": "CONTAINER_GENERATION_CHANGED",
    }


def test_t06_host_checker_failure_stops_before_container_census() -> None:
    namespace = host_functions()
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        calls.append(argv)
        if "compose" in argv:
            return 0, json.dumps(compose_fixture()).encode()
        return 1, b"sensitive native text"

    namespace["run"] = run
    output = io.StringIO()
    with redirect_stdout(output):
        namespace["main"]()
    assert json.loads(output.getvalue())["error"] == "STAGING_RECEIPT_FAILED"
    assert "sensitive" not in output.getvalue()
    assert len(calls) == 2


def test_t20_host_native_output_cap_kills_only_own_process() -> None:
    namespace = host_functions()
    namespace["MAX_NATIVE"] = 10
    with pytest.raises(RuntimeError, match="NATIVE_OUTPUT_OVERSIZE"):
        namespace["run"]([sys.executable, "-c", "print('x' * 100)"])


def test_host_native_run_passes_bounded_input_and_output() -> None:
    namespace = host_functions()
    code, output = namespace["run"](
        [sys.executable, "-c", "import sys; print(sys.stdin.read())"],
        input_data=b"bounded",
    )
    assert code == 0 and output.strip() == b"bounded"


def test_local_ssh_stream_returns_only_bounded_stdout() -> None:
    output = diagnostic._ssh_observe([sys.executable, "-c", "print('accepted')"])
    assert output.strip() == b"accepted"


def test_local_ssh_stream_rejects_oversized_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diagnostic, "MAX_OUTPUT", 32)
    with pytest.raises(RuntimeError, match="SSH_TRANSPORT_FAILED"):
        diagnostic._ssh_observe([sys.executable, "-c", "print('X' * 1000)"])


def test_local_ssh_stream_rejects_nonzero_native_result() -> None:
    with pytest.raises(RuntimeError, match="SSH_TRANSPORT_FAILED"):
        diagnostic._ssh_observe([sys.executable, "-c", "import sys; print('x'); sys.exit(7)"])


def test_local_ssh_read_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise OSError("native secret in read error")

    monkeypatch.setattr(diagnostic.os, "read", denied)
    with pytest.raises(RuntimeError, match="SSH_TRANSPORT_FAILED"):
        diagnostic._ssh_observe([sys.executable, "-c", "print('x')"])


def test_local_ssh_spawn_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise OSError("native secret in failure")

    monkeypatch.setattr(diagnostic.subprocess, "Popen", denied)
    with pytest.raises(RuntimeError, match="SSH_TRANSPORT_FAILED"):
        diagnostic._ssh_observe(["/invalid/ssh"])


def test_recursive_json_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    def recursive(*args: Any, **kwargs: Any) -> None:
        raise RecursionError("deep")

    monkeypatch.setattr(diagnostic.json, "loads", recursive)
    with pytest.raises(ValueError, match="recursive JSON"):
        diagnostic._parse_json(b"{}")


def test_missing_os_ssh_is_sanitized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(diagnostic, "SSH_BINARY", tmp_path / "absent-fixed-ssh")
    with pytest.raises(RuntimeError, match="SSH_UNAVAILABLE"):
        diagnostic._ssh_argv("192.0.2.12", tmp_path)


def test_default_ssh_binary_is_fixed_os_path() -> None:
    assert diagnostic.SSH_BINARY == Path("/usr/bin/ssh")


def test_host_selector_accepts_one_exact_container() -> None:
    namespace = host_functions()

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        if argv[1] == "ps":
            return 0, ("a" * 64 + "\n").encode()
        return 0, json.dumps([selected_container("app")]).encode()

    namespace["run"] = run
    selected = namespace["selected"]("app", compose_fixture(), "c" * 64)
    assert selected["id"] == "a" * 64
    assert selected["started_at"] == "2026-09-24T00:00:00Z"


def test_compose_hash_uses_same_selected_config_and_binds_container_label() -> None:
    namespace = host_functions()
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        calls.append(argv)
        if "--hash" in argv:
            return 0, ("app " + "c" * 64 + "\n").encode()
        if argv[1] == "ps":
            return 0, ("a" * 64 + "\n").encode()
        return 0, json.dumps([selected_container("app")]).encode()

    namespace["run"] = run
    digest = namespace["compose_hash"]("app")
    assert digest == "c" * 64
    assert calls[0] == [*namespace["compose_command"](), "--hash", "app"]
    assert namespace["selected"]("app", compose_fixture(), digest)["config_hash"] == digest
    with pytest.raises(RuntimeError, match="CONTAINER_IDENTITY_UNTRUSTED"):
        namespace["selected"]("app", compose_fixture(), "d" * 64)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"app invalid\n",
        ("app " + "c" * 64 + "\napp " + "c" * 64 + "\n").encode(),
        ("postgres " + "c" * 64 + "\n").encode(),
    ],
)
def test_compose_hash_rejects_missing_malformed_or_ambiguous_native_output(raw: bytes) -> None:
    namespace = host_functions()
    namespace["run"] = lambda argv, **kwargs: (0, raw)
    with pytest.raises(RuntimeError, match="COMPOSE_HASH_UNTRUSTED"):
        namespace["compose_hash"]("app")


def test_host_rejects_native_compose_hash_change_during_observation() -> None:
    namespace = host_functions()
    app_hash_reads = 0

    def run(argv: list[str], **kwargs: Any) -> tuple[int, bytes]:
        nonlocal app_hash_reads
        if "--hash" in argv:
            service = argv[-1]
            if service == "app":
                app_hash_reads += 1
            digest = "d" * 64 if service == "app" and app_hash_reads == 2 else "c" * 64
            return 0, (service + " " + digest + "\n").encode()
        if "compose" in argv:
            return 0, json.dumps(compose_fixture()).encode()
        if "check_staging_security.py" in " ".join(argv):
            return 0, b"ok"
        return 0, json.dumps(observation()).encode()

    namespace["run"] = run
    namespace["selected"] = lambda service, compose, expected_hash: {"id": "a" * 64}
    output = io.StringIO()
    with redirect_stdout(output):
        namespace["main"]()
    assert json.loads(output.getvalue())["error"] == "COMPOSE_HASH_CHANGED"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("ready"),
        lambda value: value.update(ready={"status": "response", "code": "200"}),
        lambda value: value.update(database=None),
        lambda value: value["database"].update(extra="secret"),
        lambda value: value["database"].update(tls=1),
        lambda value: value["database"].update(server_version="secret"),
        lambda value: value["database"].update(tls_version="TLSv1.0"),
        lambda value: value["database"].update(activity={}),
        lambda value: value["database"]["activity"].update(active=-1),
        lambda value: value.update(database={"status": "unreachable", "error": "PASSWORD=secret"}),
    ],
)
def test_untrusted_observation_shapes_are_rejected(mutation: Any) -> None:
    value = observation()
    mutation(value)
    with pytest.raises(ValueError):
        diagnostic._report(payload(value))


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"schema": "wrong"},
        {
            "schema": "pulseplate.staging-runtime-host.v1",
            "trust": "rejected",
            "error": "secret=value",
        },
        {
            "schema": "pulseplate.staging-runtime-host.v1",
            "trust": "rejected",
            "error": "SECRET_PASSWORD_ABC",
        },
        {
            "schema": "pulseplate.staging-runtime-host.v1",
            "trust": "accepted",
            "fingerprint": "wrong",
            "observation": {},
        },
    ],
)
def test_untrusted_host_envelopes_are_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        diagnostic._report(bad)


@pytest.mark.parametrize("status", ["configuration_rejected", "driver_unavailable"])
def test_db_probe_prerequisite_or_config_failure_is_trust_error(status: str) -> None:
    value = observation()
    value["database"] = {
        "status": status,
        "error": (
            "DB_CONFIG_UNTRUSTED" if status == "configuration_rejected" else "DB_DRIVER_UNAVAILABLE"
        ),
    }
    with pytest.raises(RuntimeError):
        diagnostic._report(payload(value))


def test_missing_driver_exits_three_while_connection_failure_is_measured(
    local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    value = observation()
    value["database"] = {"status": "driver_unavailable", "error": "DB_DRIVER_UNAVAILABLE"}
    monkeypatch.setattr(
        diagnostic, "_ssh_observe", lambda argv: json.dumps(payload(value)).encode()
    )
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3
    rejected = capsys.readouterr()
    assert rejected.out == "" and rejected.err.strip() == "DB_DRIVER_UNAVAILABLE"

    value["database"] = {"status": "unreachable", "error": "DB_CONNECTION_FAILED"}
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 0
    measured = json.loads(capsys.readouterr().out)
    assert measured["status"] == "degraded"
    assert measured["errors"] == ["DB_CONNECTION_FAILED"]


def test_db_tls_false_is_trust_error() -> None:
    value = observation()
    value["database"]["tls"] = False
    value["database"]["tls_version"] = None
    with pytest.raises(RuntimeError, match="DB_TLS_UNVERIFIED"):
        diagnostic._report(payload(value))


def test_main_local_prerequisite_returns_three(
    local_run: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*args: Any) -> list[str]:
        raise RuntimeError("SSH_IDENTITY_UNAVAILABLE")

    monkeypatch.setattr(diagnostic, "_ssh_argv", unavailable)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3


def test_main_never_echoes_unknown_remote_error(
    local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(argv: list[str]) -> bytes:
        raise RuntimeError("secret-with-hyphen")

    monkeypatch.setattr(diagnostic, "_ssh_observe", fail)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3
    captured = capsys.readouterr()
    assert captured.err.strip() == "REMOTE_OUTPUT_UNTRUSTED"


def test_main_transport_failure_emits_only_coded_error(
    local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(argv: list[str]) -> bytes:
        raise RuntimeError("SSH_TRANSPORT_FAILED")

    monkeypatch.setattr(diagnostic, "_ssh_observe", fail)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "SSH_TRANSPORT_FAILED\n"


def test_t09_http_liveness_and_readiness_are_separate() -> None:
    source = diagnostic.HOST_PROBE
    assert 'http("/health")' in source
    assert 'http("/ready")' in source
    assert "HTTP_TIMEOUT = 3" in source


def test_http_probe_uses_local_transport_without_proxy_or_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = app_functions(monkeypatch)
    seen: list[str] = []
    status = {"ready": 503}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            return None

        def do_GET(self) -> None:
            seen.append(self.path)
            if self.path == "/health":
                self.send_response(200)
            elif self.path == "/ready" and status["ready"] == 302:
                self.send_response(302)
                self.send_header("Location", "/second")
            elif self.path == "/ready" and status["ready"] == 0:
                time.sleep(0.2)
                self.send_response(200)
            else:
                self.send_response(status["ready"])
            self.end_headers()
            try:
                self.wfile.write(b"ok")
            except BrokenPipeError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        namespace["HTTP_ORIGIN"] = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("NO_PROXY", "")
        assert namespace["http"]("/health") == {"status": "response", "code": 200}
        assert namespace["http"]("/ready") == {"status": "response", "code": 503}
        status["ready"] = 302
        assert namespace["http"]("/ready") == {"status": "response", "code": 302}
        assert "/second" not in seen
        status["ready"] = 0
        namespace["HTTP_TIMEOUT"] = 0.02
        assert namespace["http"]("/ready") == {"status": "unreachable", "code": None}
        assert seen.count("/health") == 1 and seen.count("/ready") == 3
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("field,code", [("health", "HEALTH_NOT_OK"), ("ready", "READY_NOT_OK")])
def test_t10_t11_http_failure_is_measured_degradation(field: str, code: str) -> None:
    value = observation()
    value[field] = {"status": "response", "code": 503}
    report = diagnostic._report(payload(value))
    assert report["status"] == "degraded"
    assert code in report["errors"]


def test_t12_timeout_is_measured_degradation() -> None:
    value = observation()
    value["health"] = {"status": "unreachable", "code": None}
    report = diagnostic._report(payload(value))
    assert report["status"] == "degraded"


def test_t13_db_uses_file_backed_tls_and_read_only_transaction() -> None:
    source = diagnostic.HOST_PROBE
    assert 'sslmode="verify-full"' in source
    assert 'sslrootcert="/run/secrets/postgres_ca"' in source
    assert 'passfile="/run/secrets/postgres_pgpass"' in source
    assert 'cursor.execute("BEGIN READ ONLY")' in source
    assert 'cursor.execute("ROLLBACK")' in source
    assert "pg_stat_ssl WHERE pid = pg_backend_pid()" in source


def test_t13_app_probe_executes_only_read_only_sql_with_file_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = app_functions(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulseplate@postgres:5432/pulseplate"
        "?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca"
        "&passfile=/run/secrets/postgres_pgpass",
    )
    sql: list[str] = []
    credentials: list[dict[str, Any]] = []

    class Cursor:
        def __enter__(self) -> "Cursor":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, statement: str) -> None:
            sql.append(statement)

        def fetchone(self) -> tuple[Any, ...]:
            statement = sql[-1]
            if "current_database()" in statement and "pg_is_in_recovery()" in statement:
                return ("pulseplate", "pulseplate", "150019", False)
            if "pg_stat_ssl" in statement:
                return (True, "TLSv1.3")
            return (0, 1, 0, 1)

    class Connection:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

        def close(self) -> None:
            sql.append("CLOSED")

    fake = ModuleType("psycopg")
    fake.Error = type("Error", (Exception,), {})

    def connect(**kwargs: Any) -> Connection:
        credentials.append(kwargs)
        return Connection()

    fake.connect = connect
    result = namespace["database"](fake)
    assert result["status"] == "response" and result["tls"] is True
    assert credentials[0]["sslmode"] == "verify-full"
    assert credentials[0]["sslrootcert"] == "/run/secrets/postgres_ca"
    assert credentials[0]["passfile"] == "/run/secrets/postgres_pgpass"
    assert sql[0] == "BEGIN READ ONLY" and sql[-2:] == ["ROLLBACK", "CLOSED"]
    assert all(
        statement.startswith(("BEGIN READ ONLY", "SELECT", "ROLLBACK")) for statement in sql[:-1]
    )


def test_t13_app_probe_rejects_duplicate_dsn_keys_before_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = app_functions(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulseplate@postgres:5432/pulseplate"
        "?sslmode=verify-full&sslmode=disable&sslrootcert=/run/secrets/postgres_ca"
        "&passfile=/run/secrets/postgres_pgpass",
    )
    fake = ModuleType("psycopg")
    fake.Error = type("Error", (Exception,), {})
    fake.connect = lambda **kwargs: pytest.fail("duplicate DSN keys reached DB connection")
    assert namespace["database"](fake) == {
        "status": "configuration_rejected",
        "error": "DB_CONFIG_UNTRUSTED",
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("PGPASSWORD", "ambient-secret"),
        ("PGSERVICE", "other"),
        ("PGHOSTADDR", "192.0.2.10"),
        ("PGSSLMODE", "disable"),
        ("PGPASSFILE", "/tmp/other"),
    ],
)
def test_app_db_rejects_ambient_libpq_override_before_connect(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    namespace = app_functions(monkeypatch)
    monkeypatch.setenv(key, value)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulseplate@postgres:5432/pulseplate"
        "?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca"
        "&passfile=/run/secrets/postgres_pgpass",
    )
    fake = ModuleType("psycopg")
    fake.Error = type("Error", (Exception,), {})
    fake.connect = lambda **kwargs: pytest.fail("untrusted libpq environment reached provider")
    assert namespace["database"](fake) == {
        "status": "configuration_rejected",
        "error": "DB_CONFIG_UNTRUSTED",
    }


@pytest.mark.parametrize("code", ["DB_CONNECTION_FAILED", "DB_AUTH_FAILED"])
def test_t14_t16_db_failures_are_distinct_and_sanitized(code: str) -> None:
    value = observation()
    value["database"] = {"status": "unreachable", "error": code}
    report = diagnostic._report(payload(value))
    assert report["status"] == "degraded"
    assert report["errors"] == [code]


@pytest.mark.parametrize(
    "sqlstate,expected_code",
    [("28P01", "DB_AUTH_FAILED"), (None, "DB_CONNECTION_FAILED")],
)
def test_app_db_connect_failure_classifies_sqlstate_without_provider_prose(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sqlstate: str | None,
    expected_code: str,
) -> None:
    namespace = app_functions(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulseplate@postgres:5432/pulseplate"
        "?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca"
        "&passfile=/run/secrets/postgres_pgpass",
    )
    attempts: list[dict[str, Any]] = []
    created_sessions: list[object] = []
    closed_sessions: list[object] = []

    class ConnectError(Exception):
        def __init__(self) -> None:
            super().__init__("password=provider-secret; certificate=provider-secret")
            self.sqlstate = sqlstate

    class NeverReturnedSession:
        def __init__(self) -> None:
            created_sessions.append(self)

        def close(self) -> None:
            closed_sessions.append(self)

    fake = ModuleType("psycopg")
    fake.Error = ConnectError

    def connect(**kwargs: Any) -> NeverReturnedSession:
        attempts.append(kwargs)
        raise ConnectError()

    fake.connect = connect
    result = namespace["database"](fake)
    assert result == {"status": "unreachable", "error": expected_code}
    assert len(attempts) == 1
    assert created_sessions == closed_sessions == []
    assert "provider-secret" not in json.dumps(result) + capsys.readouterr().out


@pytest.mark.parametrize(
    "status,error",
    [
        ("driver_unavailable", "DB_CONNECTION_FAILED"),
        ("configuration_rejected", "DB_AUTH_FAILED"),
        ("unreachable", "DB_CONFIG_UNTRUSTED"),
        ("unreachable", "DB_TLS_FAILED"),
    ],
)
def test_db_status_error_pairs_fail_closed(status: str, error: str) -> None:
    value = observation()
    value["database"] = {"status": status, "error": error}
    with pytest.raises(ValueError):
        diagnostic._report(payload(value))


def test_tls_true_requires_supported_version() -> None:
    value = observation()
    value["database"]["tls_version"] = None
    with pytest.raises(ValueError, match="tls version"):
        diagnostic._report(payload(value))


def test_t17_db_or_role_mismatch_rejects_trust() -> None:
    value = observation()
    value["database"]["role_match"] = False
    with pytest.raises(RuntimeError, match="DB_IDENTITY_MISMATCH"):
        diagnostic._report(payload(value))


def test_t18_hidden_activity_is_unknown_not_zero() -> None:
    value = observation()
    value["database"]["activity"] = {
        "visibility": "unknown",
        "active": None,
        "waiting": None,
        "sessions": None,
    }
    report = diagnostic._report(payload(value))
    assert report["status"] == "partial"
    assert report["unknowns"] == ["db.activity"]
    value["database"]["activity"]["active"] = 0
    with pytest.raises(ValueError):
        diagnostic._report(payload(value))


@pytest.mark.parametrize(
    "raw", [b'{"schema":1,"schema":2}', b'{"x":NaN}', b"X" * (diagnostic.MAX_OUTPUT + 1)]
)
def test_t20_malformed_native_output_fails_closed(
    raw: bytes, local_run: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(diagnostic, "_ssh_observe", lambda argv: raw)
    assert diagnostic.main(["--environment", "staging", "--format", "json"]) == 3
    assert capsys.readouterr().out == ""


def test_t21_cancellation_or_timeout_never_exposes_native_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    spawned: list[subprocess.Popen[bytes]] = []
    real_popen = diagnostic.subprocess.Popen

    def owned_popen(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        child = real_popen(*args, **kwargs)
        spawned.append(child)
        return child

    monkeypatch.setattr(diagnostic.subprocess, "Popen", owned_popen)
    monkeypatch.setattr(diagnostic, "SSH_TIMEOUT", 0.1)
    with pytest.raises(RuntimeError, match="SSH_TRANSPORT_FAILED"):
        diagnostic._ssh_observe(
            [sys.executable, "-c", "import sys,time;print('secret',file=sys.stderr);time.sleep(2)"]
        )
    captured = capsys.readouterr()
    assert "secret" not in captured.out + captured.err
    assert len(spawned) == 1 and spawned[0].poll() is not None


def test_app_db_forced_error_closes_only_owned_session(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = app_functions(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulseplate@postgres:5432/pulseplate"
        "?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca"
        "&passfile=/run/secrets/postgres_pgpass",
    )
    closed: list[bool] = []
    fake = ModuleType("psycopg")

    class QueryError(Exception):
        sqlstate = "08006"

    class Cursor:
        def __enter__(self) -> "Cursor":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, statement: str) -> None:
            raise QueryError()

    class Connection:
        autocommit = False

        def cursor(self) -> Cursor:
            return Cursor()

        def close(self) -> None:
            closed.append(True)

    fake.Error = QueryError
    fake.connect = lambda **kwargs: Connection()
    assert namespace["database"](fake) == {
        "status": "unreachable",
        "error": "DB_CONNECTION_FAILED",
    }
    assert closed == [True]


def test_t22_remote_output_rejects_extra_fields_and_secrets() -> None:
    value = payload()
    value["Config.Env"] = ["DATABASE_URL=secret"]
    with pytest.raises(ValueError):
        diagnostic._report(value)
