"""Fixed native scheduler admission: unit evidence, not native execution proof."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

from core.food_apis.scheduler_runtime import FOOD_UPDATE_ADVISORY_LOCK_KEY
from scripts.ci import check_scheduler_worker_runtime as smoke

REPO_ROOT = Path(__file__).resolve().parents[1]
PG_REF = "pgvector/pgvector:0.8.6-pg15-trixie@sha256:43904fc138a63f93611a2995cec2566e8ae883c8678cd65c60315fa44308f81f"
PG_ID = "sha256:" + "b" * 64


def test_native_capture_bounds_output_during_collection() -> None:
    with pytest.raises(smoke.SmokeError, match="output exceeded"):
        smoke.capture([sys.executable, "-c", "import os; os.write(1,b'x'*4096)"], 5, 32)


@pytest.mark.parametrize("argv", [[], ["python", "-c", "print('untrusted PATH')"]])
def test_native_capture_rejects_unresolved_executable_before_start(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("Relative or missing executable must not reach Popen")

    monkeypatch.setattr(smoke.subprocess, "Popen", unexpected)
    with pytest.raises(smoke.SmokeError, match="absolute executable"):
        smoke.capture(argv, 5)


def test_native_missing_pipe_fails_closed_and_reaps_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingPipe:
        stdout = None
        killed = False
        waited = False

        def __enter__(self) -> MissingPipe:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def kill(self) -> None:
            self.killed = True

        def wait(self) -> int:
            self.waited = True
            return 0

    process = MissingPipe()

    def popen(argv: list[str], **kwargs: object) -> MissingPipe:
        assert kwargs["shell"] is False
        return process

    monkeypatch.setattr(smoke.subprocess, "Popen", popen)
    with pytest.raises(smoke.SmokeError, match="output pipe"):
        smoke.capture([sys.executable, "-c", "pass"], 5)
    assert process.killed and process.waited


def test_native_capture_timeout_invalid_utf8_and_failure() -> None:
    with pytest.raises(smoke.SmokeError, match="timed out"):
        smoke.capture([sys.executable, "-c", "import time; time.sleep(30)"], 0.1)
    with pytest.raises(smoke.SmokeError, match="not UTF-8"):
        smoke.capture([sys.executable, "-c", "import os; os.write(1,b'\\xff')"], 5)
    with pytest.raises(smoke.SmokeError, match=r"failed \(7\).*native-error"):
        smoke.capture([sys.executable, "-c", "print('native-error'); raise SystemExit(7)"], 5)
    with pytest.raises(smoke.SmokeError, match="deadline"):
        smoke.capture([sys.executable], 0)
    assert smoke.capture([sys.executable, "-c", "print('complete')"], 5) == "complete\n"


@pytest.mark.parametrize("key", sorted(smoke.FORBIDDEN_ENV | {"PYTEST_UNKNOWN", "GH_TOKEN"}))
def test_effective_bypasses_rejected_even_if_false(key: str) -> None:
    with pytest.raises(smoke.SmokeError, match="bypass|credential"):
        smoke.check_worker_environment([key + "=false"])


@pytest.mark.parametrize("values", [None, {}, [1], ["missing"], ["=x"], ["A=x", "A=y"]])
def test_malformed_native_environment_fails(values: object) -> None:
    with pytest.raises(smoke.SmokeError):
        smoke.environment(values)


def test_worker_environment_requires_exact_configuration() -> None:
    smoke.check_worker_environment(["APP_ENV=staging", "PYTHONPATH=/app"], {"APP_ENV": "staging"})
    with pytest.raises(smoke.SmokeError, match="differs"):
        smoke.check_worker_environment(["APP_ENV=ci"], {"APP_ENV": "production"})
    with pytest.raises(smoke.SmokeError, match="injected"):
        smoke.check_worker_environment(["PYTHONPATH=/tmp"])


def _worker() -> dict[str, Any]:
    return {
        "Id": "container",
        "Image": "sha256:image",
        "RestartCount": 0,
        "State": {"Running": True, "OOMKilled": False, "Pid": 91, "StartedAt": "start"},
    }


@pytest.mark.parametrize(
    "field,value",
    [("Running", False), ("Pid", 0), ("Pid", True), ("OOMKilled", True), ("StartedAt", "")],
)
def test_invalid_worker_state_fails(field: str, value: object) -> None:
    info = _worker()
    info["State"][field] = value
    with pytest.raises(smoke.SmokeError):
        smoke.worker_identity(info, "sha256:image")


def test_wrong_image_restart_and_missing_identity_fail() -> None:
    info = _worker()
    assert smoke.worker_identity(info, "sha256:image") == ("container", "sha256:image", 91, "start")
    for changed in ({"Image": "other"}, {"RestartCount": 1}, {"Id": None}):
        with pytest.raises(smoke.SmokeError):
            smoke.worker_identity(info | changed, "sha256:image")


def _lease() -> str:
    return "".join(
        f"91|abc.5b|worker|db|LOG:  execute <unnamed>: SELECT {operation}($1)\n"
        f"91|abc.5b|worker|db|DETAIL:  parameters: $1 = '{smoke.LEASE_KEY}'\n"
        for operation in ("pg_try_advisory_lock", "pg_advisory_unlock")
    )


def test_lease_native_projection_is_bound_and_not_an_observer_substitute() -> None:
    assert smoke.LEASE_KEY == FOOD_UPDATE_ADVISORY_LOCK_KEY
    assert smoke.lease_session(_lease(), "worker", "db") == (91, "abc.5b")
    assert smoke.lease_session(_lease(), "observer", "db") is None
    assert smoke.lease_session("", "worker", "db") is None
    assert smoke.lease_session(_lease().split("pg_advisory_unlock")[0], "worker", "db") is None
    assert smoke.lease_session(_lease().split("DETAIL:")[0], "worker", "db") is None


@pytest.mark.parametrize(
    "changed",
    [
        _lease().replace(str(smoke.LEASE_KEY), "1"),
        _lease().replace("91|abc.5b|worker|db|DETAIL", "92|abc.5c|worker|db|DETAIL"),
        _lease() + _lease(),
        _lease().replace("pg_try_advisory_lock", "pg_advisory_unlock"),
        _lease() + "91|abc.5b|worker|db|WARNING:  you don't own a lock\n",
        _lease().replace("DETAIL:  parameters", "DETAIL:  unsupported"),
    ],
)
def test_wrong_lease_key_session_order_or_native_error_fails(changed: str) -> None:
    with pytest.raises(smoke.SmokeError):
        smoke.lease_session(changed, "worker", "db")


def _backend() -> dict[str, object]:
    return {
        "pid": 91,
        "session": "abc.5b",
        "backend_start": "start",
        "state": "idle",
        "xact_start": None,
        "locked": False,
    }


@pytest.mark.parametrize(
    "changed",
    [
        None,
        {},
        {"pid": 92},
        {"session": "def.5b"},
        {"state": "idle in transaction"},
        {"xact_start": "now"},
        {"locked": True},
        {"backend_start": None},
    ],
)
def test_backend_invalidation_cannot_pass_via_later_lock_availability(changed: object) -> None:
    value = _backend() | changed if isinstance(changed, dict) and changed else changed
    with pytest.raises(smoke.SmokeError):
        smoke.check_session(value, (91, "abc.5b"))


def test_same_pid_with_replaced_backend_start_rejected() -> None:
    identity = smoke.check_session(_backend(), (91, "abc.5b"))
    with pytest.raises(smoke.SmokeError, match="identity changed"):
        smoke.check_session(_backend() | {"backend_start": "later"}, (91, "abc.5b"), identity)


@pytest.mark.parametrize(
    "failure",
    [
        " ERROR boundary failed",
        " WARNING release failed",
        "Traceback",
        "Running update for usda",
        "shared lease is held",
        "Error checking USDA updates",
    ],
)
def test_no_update_before_caught_failure_never_passes(failure: str) -> None:
    with pytest.raises(smoke.SmokeError):
        smoke.check_logs(
            "Checking for database updates...\nNo database updates available\n" + failure
        )


def test_no_update_and_clean_term_are_distinct_required_observations() -> None:
    log = "Checking for database updates...\nNo database updates available\n"
    assert smoke.check_logs(log)
    assert not smoke.check_logs("process started")
    with pytest.raises(smoke.SmokeError, match="SIGTERM"):
        smoke.check_logs(log, stopped=True)
    assert smoke.check_logs(
        log + "Received signal 15, initiating graceful shutdown\n"
        "Database update scheduler stopped",
        stopped=True,
    )


def test_cleanup_preserves_primary_failure_and_records_all_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        smoke.Smoke,
        "inspect",
        lambda *args: (_ for _ in ()).throw(smoke.SmokeError("primary native failure")),
    )
    monkeypatch.setattr(smoke.Smoke, "cleanup", lambda self: ["owned cleanup failure"])
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    assert smoke.main(["--image", "candidate", "--postgres-image", PG_REF]) == 1
    output = capsys.readouterr().out
    assert "primary native failure" in output and "owned cleanup failure" in output


def test_cleanup_only_recorded_resources_in_reverse_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    runner.resources = [("network", "n"), ("volume", "v"), ("container", "c")]
    monkeypatch.setattr(
        runner, "inspect", lambda *args: {"Labels": {"pulseplate.scheduler-smoke": runner.prefix}}
    )
    calls: list[tuple[str, ...]] = []

    def run(*args: str) -> str:
        calls.append(args)
        if args[:2] == ("volume", "rm"):
            raise smoke.SmokeError("failure")
        return "unrelated\n"

    monkeypatch.setattr(runner, "run", run)
    assert runner.cleanup() == ["volume v: failure"]
    assert [call[:2] for call in calls] == [
        ("container", "rm"),
        ("container", "ls"),
        ("volume", "rm"),
        ("network", "rm"),
        ("network", "ls"),
    ]
    assert calls[0] == ("container", "rm", "--force", "--volumes", "c")


def test_unknown_mount_or_ingress_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    info = {
        "Mounts": [{"Destination": "/app/cache", "Type": "volume", "Name": "cache"}],
        "HostConfig": {"Tmpfs": {}, "PortBindings": {}, "Privileged": False, "NetworkMode": "n"},
    }
    monkeypatch.setattr(runner, "inspect", lambda *args: info)
    runner.mounts("worker", {"/app/cache": "cache"}, "n")
    for key, value in [
        ("PortBindings", {"8000/tcp": []}),
        ("Privileged", True),
        ("NetworkMode", "host"),
    ]:
        bad = copy.deepcopy(info)
        bad["HostConfig"][key] = value
        monkeypatch.setattr(runner, "inspect", lambda *args: bad)
        with pytest.raises(smoke.SmokeError):
            runner.mounts("worker", {"/app/cache": "cache"}, "n")
    monkeypatch.setattr(runner, "inspect", lambda *args: info)
    with pytest.raises(smoke.SmokeError):
        runner.mounts("worker", {}, "n")
    with pytest.raises(smoke.SmokeError):
        runner.mounts("worker", {"/app/cache": "foreign"}, "n")


@pytest.mark.parametrize("runtime", ["production", "staging"])
def test_fresh_enabled_export_process_still_rejects_missing_secret(
    runtime: str,
    tmp_path: Path,
) -> None:
    # No inherited pytest/CI flags: actual import-time settings path in a new interpreter.
    import subprocess

    env = {
        "PATH": os.defpath,
        "APP_ENV": runtime,
        "ENVIRONMENT": runtime,
        "PYTHONPATH": str(REPO_ROOT),
        "PRIVATE_EXPORTS_ENABLED": "true",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import settings"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "EXPORT_TOKEN_SECRET must be set" in result.stderr


def test_hosted_workflow_executes_actual_candidate_after_build_auth_cleanup() -> None:
    import yaml

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/build.yml").read_text())
    steps = workflow["jobs"]["build"]["steps"]
    names = [step["name"] for step in steps]
    index = names.index("Check native scheduler worker lifecycle")
    assert names.index("Build Docker image (local, for tests)") < index
    assert names.index("Remove private Python index Docker authentication") < index
    assert names.index("Validate production image report and render SARIF") < index
    assert names.index("Preserve production image scan evidence") < index
    assert names.index("Upload Docker telemetry artifact") < index
    assert names.index("Upload Docker budget check artifact") < index
    assert names.index("Test Docker image") < index
    assert index < names.index("Fail build job when Docker budget check failed")
    assert "--image pulseplate:test" in steps[index]["run"]
    assert '--postgres-image "$POSTGRES_IMAGE"' in steps[index]["run"]
    assert steps[index]["env"]["POSTGRES_IMAGE"] == PG_REF
    for filename in ("ci.yml", "cd.yml"):
        owner = yaml.safe_load((REPO_ROOT / ".github/workflows" / filename).read_text())
        pins = [
            job["services"]["postgres"]["image"]
            for job in owner["jobs"].values()
            if job.get("services", {})
            .get("postgres", {})
            .get("image", "")
            .startswith("pgvector/pgvector:")
        ]
        assert pins == [steps[index]["env"]["POSTGRES_IMAGE"]]
    assert "continue-on-error" not in steps[index] and "if" not in steps[index]


class _DockerTranscript(smoke.Smoke):
    """An explicitly synthetic CLI transcript; hosted native evidence is separate."""

    def __init__(self, fault: str = "") -> None:
        super().__init__()
        self.fault = fault
        self.calls: list[tuple[str, ...]] = []
        self.created: dict[str, tuple[str, ...]] = {}
        self.stopped = False
        self.observations = 0
        self.worker_inspections = 0

    def run(self, *args: str) -> str:
        self.calls.append(args)
        if args[0] == "create":
            name = args[args.index("--name") + 1]
            self.created[name] = args
            return "c" * 64
        if args[:2] in [("network", "create"), ("volume", "create")]:
            return args[-1] if args[0] == "volume" else "d" * 64
        if args[0] == "exec":
            # A temporary Unix-only init daemon cannot answer this readiness contract.
            assert args[args.index("-h") + 1] == "127.0.0.1"
            # Synthetic disposable fixture credential, never an operator password.
            credential = "PGPASSWORD=synthetic-fixture-password"  # pragma: allowlist secret
            assert credential in args
            query = args[-1]
            if query == "SELECT 1":
                return "1"
            if query == "SHOW server_version":
                return "14.1" if self.fault == "pg-major" else "15.10"
            if query.startswith("SELECT row_to_json"):
                self.observations += 1
                row = _backend()
                if self.fault == "invalidated-session":
                    return "null"  # A later observer lock success cannot rescue this.
                if self.fault == "backend-replaced" and self.observations > 1:
                    row["backend_start"] = "later"
                return json.dumps(row)
            if query.startswith("SELECT pg_try"):
                return "f\nf" if self.fault == "observer-fails" else "t\nt"
            if query == "CREATE EXTENSION vector" and self.fault == "missing-vector":
                raise smoke.SmokeError("fixture vector extension unavailable")
            assert query.startswith(("CREATE ROLE", "CREATE DATABASE", "CREATE EXTENSION"))
            return "CREATE"
        if args[0] == "logs":
            if args[1].endswith("-pg"):
                return _lease().replace("|worker|db|", "|scheduler_smoke_worker|workerdb|")
            log = "Checking for database updates...\nNo database updates available\n"
            if self.fault == "caught-unlock-error":
                log += " ERROR Database update attempt failed at the shared lease boundary\n"
            if self.stopped:
                log += "Received signal 15, initiating graceful shutdown\nDatabase update scheduler stopped\n"
            return log
        if args[0] == "kill":
            assert args[1:3] == ("--signal", "TERM")
            self.stopped = True
            return "stopped"
        if args[0] == "wait":
            return "137" if self.fault == "forced-kill" else "0"
        if args[0] in {"start", "pull"}:
            if args[0] == "start" and args[-1].endswith("-worker"):
                self.stopped = False
            return ""
        if len(args) > 1 and args[1] in {"rm", "ls"}:
            return ""
        raise AssertionError(args)

    def inspect(self, kind: str, name: str) -> dict[str, Any]:
        if kind == "network":
            return {"Internal": self.fault != "external-network"}
        if kind == "volume":
            return {"Labels": {"pulseplate.scheduler-smoke": self.prefix}}
        if kind == "image":
            if name == "candidate":
                return {
                    "Id": "sha256:image",
                    "Config": {
                        "Env": ["PYTHONPATH=/app"],
                        "User": "root" if self.fault == "root-candidate" else "pulseplate",
                        "Volumes": {},
                        "Entrypoint": None,
                    },
                }
            return {
                "Id": "bad" if self.fault == "wrong-fixture-config" else PG_ID,
                "Architecture": "arm64" if self.fault == "wrong-platform" else "amd64",
                "Os": "linux",
                "RepoDigests": (
                    []
                    if self.fault == "wrong-fixture-digest"
                    else ["pgvector/pgvector@" + PG_REF.split("@")[1]]
                ),
                "Config": {"Volumes": {"/var/lib/postgresql/data": {}}},
            }
        args = self.created[name]
        info = _worker()
        info["State"]["ExitCode"] = 0
        config = {
            "User": "pulseplate",
            "Env": ["PYTHONPATH=/app"],
            "Cmd": ["python", "-m", "core.food_apis.scheduler", "--serve"],
        }
        mount_rows = []
        tmpfs: dict[str, str] = {}
        for i, arg in enumerate(args[:-1]):
            if arg == "-e":
                config["Env"].append(args[i + 1])
            if arg == "--user":
                config["User"] = args[i + 1]
            if arg == "--tmpfs":
                tmpfs[args[i + 1].split(":")[0]] = args[i + 1]
            if arg == "--mount":
                source = args[i + 1].split("source=")[1].split(",")[0]
                mount_rows.append({"Destination": "/app/cache", "Type": "volume", "Name": source})
        info["Config"] = config
        info["Mounts"] = mount_rows
        info["HostConfig"] = {
            "Tmpfs": tmpfs,
            "PortBindings": {},
            "Privileged": False,
            "NetworkMode": args[args.index("--network") + 1],
        }
        info["NetworkSettings"] = {"Networks": {info["HostConfig"]["NetworkMode"]: {}}}
        if name.endswith("-pg"):
            info["Image"] = PG_ID
        if name.endswith("-worker"):
            if self.fault == "wrong-command":
                info["Config"]["Cmd"] = ["python", "-m", "uvicorn", "app.main:app"]
            if self.fault == "extra-network":
                info["NetworkSettings"]["Networks"]["bridge"] = {}
            self.worker_inspections += 1
            if self.fault == "process-replaced" and self.worker_inspections > 4:
                info["State"]["Pid"] = 92
            if self.stopped:
                info["State"]["Running"] = False
                if self.fault == "terminal-oom":
                    info["State"]["OOMKilled"] = True
        return info


@pytest.mark.parametrize(
    "fault,match",
    [
        ("external-network", "internal"),
        ("pg-major", "major"),
        ("missing-vector", "extension unavailable"),
        ("invalidated-session", "absent"),
        ("backend-replaced", "identity changed"),
        ("observer-fails", "observer"),
        ("caught-unlock-error", "failed"),
        ("process-replaced", "identity changed"),
        ("forced-kill", "exit normally"),
        ("terminal-oom", "terminal"),
        ("wrong-command", "canonical CLI"),
        ("extra-network", "network attachment"),
    ],
)
def test_fixed_lifecycle_rejects_native_boundary_failures(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    match: str,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(smoke.time, "sleep", lambda seconds: None)
    runner = _DockerTranscript(fault)
    with pytest.raises(smoke.SmokeError, match=match):
        runner.exercise(
            "sha256:image",
            PG_ID,
            "staging",
            ("70", "70"),
            ("999", "999"),
        )


def test_fixed_lifecycle_runs_canonical_cli_under_least_privilege_and_tcp_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(smoke.time, "sleep", lambda seconds: None)
    runner = _DockerTranscript()
    runner.exercise(
        "sha256:image",
        PG_ID,
        "production",
        ("70", "70"),
        ("999", "999"),
    )
    worker = next(args for name, args in runner.created.items() if name.endswith("-worker"))
    assert worker[-5:] == ("sha256:image", "python", "-m", "core.food_apis.scheduler", "--serve")
    assert "PRIVATE_EXPORTS_ENABLED=false" in worker
    assert not any("EXPORT_TOKEN_SECRET" in arg for arg in worker)
    assert worker[worker.index("--pull") + 1] == "never"
    assert worker[worker.index("--cap-drop") + 1] == "ALL"
    assert worker[worker.index("--security-opt") + 1] == "no-new-privileges"
    assert worker[worker.index("--restart") + 1] == "no"
    postgres = next(args for name, args in runner.created.items() if name.endswith("-pg"))
    assert f"TMPDIR={smoke.PG_SCRATCH}" in postgres
    assert f"{smoke.PG_SCRATCH}:uid=70,gid=70,mode=0700,size=256m" in postgres
    assert "/tmp" not in postgres
    role = next(
        args[-1]
        for args in runner.calls
        if args[0] == "exec" and args[-1].startswith("CREATE ROLE")
    )
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION" in role
    database = next(
        i
        for i, args in enumerate(runner.calls)
        if args[-1] == "CREATE DATABASE workerdb OWNER smoke_worker"
    )
    extension = next(
        i for i, args in enumerate(runner.calls) if args[-1] == "CREATE EXTENSION vector"
    )
    worker_start = next(
        i
        for i, args in enumerate(runner.calls)
        if args[0] == "start" and args[-1].endswith("-worker")
    )
    assert database < extension < worker_start
    extension_args = runner.calls[extension]
    assert extension_args[extension_args.index("-d") + 1] == "workerdb"
    assert extension_args[extension_args.index("-U") + 1] == "postgres"
    assert runner.observations == 2 and runner.stopped
    assert runner.cleanup() == []


def test_cleanup_uses_created_id_even_when_container_name_is_rebound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    calls: list[tuple[str, ...]] = []

    def run(*args: str) -> str:
        calls.append(args)
        if args[0] == "create":
            return "a" * 64
        return "b" * 64 if args[1] == "ls" else ""

    monkeypatch.setattr(runner, "run", run)
    runner.create("container", "rebound-name", "image")
    assert runner.cleanup() == []
    assert calls[1] == ("container", "rm", "--force", "--volumes", "a" * 64)
    assert "rebound-name" not in calls[1]


def test_log_rotation_cannot_erase_an_earlier_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    logs = iter(["old ERROR failure\n", "new success\n"])
    monkeypatch.setattr(runner, "run", lambda *args: next(logs))
    assert runner.logs("worker") == "old ERROR failure\n"
    with pytest.raises(smoke.SmokeError, match="truncated"):
        runner.logs("worker")


@pytest.mark.parametrize(
    "content",
    [
        b"postgres:x:70:70::/:/bin/sh\n",
        b"postgres:x:0:0::/:/bin/sh\n",
        b"postgres:x:70:70::/:/bin/sh\npostgres:x:71:71::/:/bin/sh\n",
        b"",
    ],
)
def test_image_account_is_read_without_starting_root_and_requires_nonroot_identity(
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
) -> None:
    import io
    import tarfile

    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(runner, "run", lambda *args: calls.append(args) or "a" * 64)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        member = tarfile.TarInfo("passwd")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    monkeypatch.setattr(smoke, "capture_bytes", lambda *args: output.getvalue())
    if content == b"postgres:x:70:70::/:/bin/sh\n":
        assert runner.account("image", "postgres") == ("70", "70")
    else:
        with pytest.raises(smoke.SmokeError, match="non-root"):
            runner.account("image", "postgres")
    assert all(args[0] != "start" for args in calls)
    assert "--tmpfs" in calls[0]  # Overrides the fixture's image-declared volume.


def test_native_inspect_rejects_unavailable_or_ambiguous_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    for output in ["null", "[]", "[{},{}]", "[1]"]:
        monkeypatch.setattr(runner, "run", lambda *args: output)
        with pytest.raises(smoke.SmokeError, match="inspection"):
            runner.inspect("image", "candidate")
    monkeypatch.setattr(runner, "run", lambda *args: '[{"Id":"real"}]')
    assert runner.inspect("image", "candidate") == {"Id": "real"}


@pytest.mark.parametrize(
    "fault",
    ["", "root-candidate", "wrong-fixture-config", "wrong-platform", "wrong-fixture-digest"],
)
def test_main_preserves_immutable_fixture_selection_and_two_configurations(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(smoke.time, "sleep", lambda seconds: None)
    runner = _DockerTranscript(fault)
    monkeypatch.setattr(runner, "account", lambda image, account: ("70", "70"))
    monkeypatch.setattr(smoke, "Smoke", lambda: runner)
    assert smoke.main(["--image", "candidate", "--postgres-image", PG_REF]) == (1 if fault else 0)
    if not fault:
        pull = next(call for call in runner.calls if call[0] == "pull")
        assert pull == (
            "pull",
            "--platform",
            "linux/amd64",
            PG_REF,
        )
        workers = [args for name, args in runner.created.items() if name.endswith("-worker")]
        assert len(workers) == 2
        for worker, runtime in zip(workers, ("production", "staging"), strict=True):
            environment = smoke.environment(
                [worker[index + 1] for index, argument in enumerate(worker) if argument == "-e"]
            )
            assert "APP_ENV" not in environment
            assert environment["ENVIRONMENT"] == runtime


@pytest.mark.parametrize("cleanup_errors", [[], ["owned cleanup failure"]])
def test_main_interruption_after_registration_cleans_once_and_preserves_interruption(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cleanup_errors: list[str],
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = _DockerTranscript()
    monkeypatch.setattr(runner, "account", lambda image, account: ("70", "70"))
    interruption = KeyboardInterrupt("synthetic interruption after resource registration")
    cleanup_calls = 0
    original_cleanup = runner.cleanup

    def interrupt(*args: object) -> None:
        runner.create("network", "interrupted-network", "--internal")
        runner.create("volume", "interrupted-cache")
        runner.create("container", "interrupted-worker", "candidate")
        raise interruption

    def cleanup() -> list[str]:
        nonlocal cleanup_calls
        cleanup_calls += 1
        assert len(runner.resources) == 3
        return original_cleanup() + cleanup_errors

    monkeypatch.setattr(runner, "exercise", interrupt)
    monkeypatch.setattr(runner, "cleanup", cleanup)
    monkeypatch.setattr(smoke, "Smoke", lambda: runner)
    with pytest.raises(KeyboardInterrupt) as captured:
        smoke.main(["--image", "candidate", "--postgres-image", PG_REF])
    assert captured.value is interruption
    assert cleanup_calls == 1
    removals = [call for call in runner.calls if call[1] == "rm"]
    assert [call[0] for call in removals] == ["container", "volume", "network"]
    output = capsys.readouterr().out
    if cleanup_errors:
        assert "owned cleanup failure" in output


def test_unknown_environment_key_and_owned_cleanup_ambiguity_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(smoke.SmokeError, match="unadmitted"):
        smoke.check_worker_environment(["UNREVIEWED_CREDENTIAL=x"])
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = smoke.Smoke()
    runner.resources = [("volume", "owned")]
    monkeypatch.setattr(runner, "inspect", lambda *args: {"Labels": {}})
    assert "Volume ownership changed" in runner.cleanup()[0]
    runner.resources = [("container", "a" * 64)]
    monkeypatch.setattr(runner, "run", lambda *args: "a" * 64)
    assert "remains after removal" in runner.cleanup()[0]


def test_native_cycle_timeout_cannot_pass_on_running_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = _DockerTranscript()
    ticks = iter([0.0, 0.0, 0.0, 1000.0])
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(ticks))
    with pytest.raises(smoke.SmokeError, match="never completed"):
        runner.exercise(
            "sha256:image",
            PG_ID,
            "staging",
            ("70", "70"),
            ("999", "999"),
        )


@pytest.mark.parametrize(
    "reference",
    ["postgres:15", "pgvector/pgvector:latest", "registry.invalid/pgvector@sha256:" + "d" * 64],
)
def test_no_mutable_or_non_pgvector_fixture_fallback(
    monkeypatch: pytest.MonkeyPatch,
    reference: str,
) -> None:
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "/usr/bin/docker")
    runner = _DockerTranscript()
    monkeypatch.setattr(smoke, "Smoke", lambda: runner)
    assert smoke.main(["--image", "candidate", "--postgres-image", reference]) == 1
    assert not any(call[0] == "pull" for call in runner.calls)
