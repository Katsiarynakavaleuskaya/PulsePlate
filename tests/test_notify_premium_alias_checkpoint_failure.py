"""Deterministic notifier checks and explicitly selected native Linux controls."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import shlex
from pathlib import Path
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import pytest

from scripts.ops import notify_premium_alias_checkpoint_failure as notifier

ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS_IMAGE = json.loads((ROOT / "deploy/prometheus/image-manifest.json").read_text())[
    "runtime_ref"
]
ALERTMANAGER_IMAGE = (
    "prom/alertmanager@sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
)
UNITS = tuple(
    ROOT / "deploy/systemd" / ("pulseplate-premium-alias-checkpoint" + suffix + ".example")
    for suffix in (".service", ".timer", "-failure.service")
)


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
        "API_KEY",
        "PRO_API_KEY",
        "VIP_API_KEY",
        "SERVER_SALT",
        "SECRET_KEY",
        "DOCKER_AUTH_CONFIG",
        "DOCKER_CONFIG",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NETRC",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
    ):
        monkeypatch.delenv(key, raising=False)


class Clock:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self.jump = 0.0
        self.origin = datetime(2026, 10, 5, tzinfo=timezone.utc)
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        assert seconds > 0
        self.sleeps.append(seconds)
        self.elapsed += seconds


def _clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()

    class DateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return clock.origin + timedelta(seconds=clock.elapsed + clock.jump)

    monkeypatch.setattr(notifier, "datetime", DateTime)
    monkeypatch.setattr(notifier.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(notifier.time, "sleep", clock.sleep)
    return clock


@pytest.mark.parametrize("contour", ["staging", "production"])
def test_fixed_payload_native_flags_and_frozen_event(
    monkeypatch: pytest.MonkeyPatch, contour: str
) -> None:
    clock = _clock(monkeypatch)
    calls: list[tuple[float, list[str]]] = []

    def send(argv: list[str]) -> bool:
        calls.append((clock.elapsed, argv.copy()))
        clock.elapsed += 10
        return True

    monkeypatch.setattr(notifier, "_send", send)
    assert (
        notifier.notify(
            docker="/absolute/docker", compose_file=Path("compose.yaml"), environment=contour
        )
        == 0
    )
    assert [at for at, _ in calls] == list(range(0, 900, 60))
    assert len(clock.sleeps) == 14
    argv = calls[0][1]
    assert all(sent == argv for _, sent in calls)
    assert argv[:8] == [
        "/absolute/docker",
        "compose",
        "-f",
        "compose.yaml",
        "exec",
        "-T",
        "alertmanager",
        "/bin/amtool",
    ]
    assert "--no-version-check" in argv and "--timeout=10s" in argv
    assert argv[-4:] == [
        "alertname=PulsePlateAliasCheckpointFailed",
        f"environment={contour}",
        "alias=all",
        "severity=warning",
    ]
    start = datetime.fromisoformat(next(arg[8:] for arg in argv if arg.startswith("--start=")))
    end = datetime.fromisoformat(next(arg[6:] for arg in argv if arg.startswith("--end=")))
    assert (end - start).total_seconds() == 900
    assert clock.elapsed == 850


@pytest.mark.parametrize("jump", [1000, -1000])
def test_clock_shift_does_not_extend_event(monkeypatch: pytest.MonkeyPatch, jump: int) -> None:
    clock = _clock(monkeypatch)
    count = 0

    def send(argv: list[str]) -> bool:
        nonlocal count
        del argv
        count += 1
        clock.jump = jump
        return True

    monkeypatch.setattr(notifier, "_send", send)
    notifier.notify(
        docker="/absolute/docker", compose_file=Path("compose.yaml"), environment="staging"
    )
    assert count == 1
    assert clock.elapsed <= 900


def test_suspend_skips_missed_slots_without_burst(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _clock(monkeypatch)
    calls: list[float] = []

    def send(argv: list[str]) -> bool:
        del argv
        calls.append(clock.elapsed)
        if len(calls) == 1:
            clock.elapsed = 305
        return True

    monkeypatch.setattr(notifier, "_send", send)
    notifier.notify(
        docker="/absolute/docker", compose_file=Path("compose.yaml"), environment="staging"
    )
    assert calls[:3] == [0, 305, 360]
    assert len(calls) == 11


def test_failure_stays_visible_without_raw_exception(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clock(monkeypatch)
    results = iter([False] + [True] * 14)
    monkeypatch.setattr(notifier, "_send", lambda argv: next(results))
    assert (
        notifier.notify(
            docker="/absolute/docker", compose_file=Path("private-path"), environment="staging"
        )
        == 1
    )
    assert capsys.readouterr().out == notifier.ERROR + "\n"


@pytest.mark.parametrize("environment", ["dev", "staging\nsecret", "", "PRODUCTION"])
def test_cli_rejects_noncanonical_contour(environment: str) -> None:
    with pytest.raises(SystemExit) as exc:
        notifier.main(["--compose-file", "compose.yaml", "--environment", environment])
    assert exc.value.code == 2


def test_cli_missing_docker_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(notifier.shutil, "which", lambda name: None)
    assert notifier.main(["--compose-file", "secret-path", "--environment", "staging"]) == 1
    assert capsys.readouterr().out == notifier.ERROR + "\n"


@pytest.mark.parametrize("failure", ["success", "spawn", "exit", "timeout", "interrupt"])
def test_native_command_channels_discard_raw_sentinel(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    killed: list[tuple[int, int]] = []

    class Process:
        pid = 123
        waits = 0

        async def wait(self) -> int:
            self.waits += 1
            if self.waits == 1 and failure == "timeout":
                raise TimeoutError("secret-sentinel")
            if self.waits == 1 and failure == "interrupt":
                raise asyncio.CancelledError
            return 0 if failure == "success" else (1 if failure == "exit" else -9)

    async def spawn(*argv: str, **kwargs: object) -> Process:
        assert argv == ("/absolute/docker",)
        assert kwargs == {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "start_new_session": True,
        }
        if failure == "spawn":
            raise OSError("secret-sentinel")
        return Process()

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    if failure == "interrupt":
        with pytest.raises(asyncio.CancelledError):
            notifier._send(["/absolute/docker"])
    else:
        assert notifier._send(["/absolute/docker"]) is (failure == "success")
    assert killed == ([(123, signal.SIGKILL)] if failure in {"timeout", "interrupt"} else [])


def test_units_are_explicit_default_off_and_keep_failure_semantics() -> None:
    service, timer, failure = (path.read_text() for path in UNITS)
    assert "RuntimeDirectoryPreserve=yes" in service and "RuntimeDirectoryMode=0700" in service
    assert "--conflict-exit-code=75" in service and " checkpoint --compose-file " in service
    for text in (service, failure):
        assert (
            "Restart=no" in text
            and "KillMode=control-group" in text
            and "TimeoutStopSec=10s" in text
        )
        assert "ConditionPathExists" not in text and "SuccessExitStatus" not in text
    assert "TimeoutStartSec=10min" in service and "TimeoutStartSec=16min" in failure
    assert "OnCalendar=*-*-* 04:15:00 UTC" in timer
    assert (
        "Persistent=true" in timer
        and "AccuracySec=1min" in timer
        and "RandomizedDelaySec=0" in timer
    )
    assert "[Install]" not in service and "[Install]" not in failure


# Native mode runs explicitly in canonical Linux CI, outside ordinary pytest collection.
# Its fixtures use synthetic environment/config/keys only and own exact unit/container IDs.
def _native(
    argv: list[str], *, timeout: float = 30, check: bool = True, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    resolved = shutil.which(argv[0])
    assert resolved is not None and os.path.isabs(resolved), f"native binary missing: {argv[0]}"
    environment = {"PATH": os.defpath, "LANG": "C", "HOME": str(cwd) if cwd else "/tmp"}
    if cwd is not None:
        environment["COMPOSE_PROFILES"] = ""
    result = subprocess.run(
        [resolved, *argv[1:]],
        env=environment,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert len(result.stdout) + len(result.stderr) <= 1024 * 1024
    if check:
        assert result.returncode == 0, result.stderr[-2048:]
    return result


def _property(unit: str, interface: str, name: str, signature: str) -> object:
    from scripts.ops.check_staging_security import _systemd_property

    return _systemd_property(
        "/org/freedesktop/systemd1/unit/" + unit.replace(".", "_2e"), interface, name, signature
    )


def _native_checkpoint_fixture(case: str, directory: Path) -> int:
    from scripts import verify_premium_alias_telemetry as verifier
    from tests.test_premium_alias_telemetry_verifier import _FakePromtoolClient, _T0, _live_snapshot

    if case == "stall":
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3600)"],
            env={"PATH": os.defpath},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (directory / "child.pid").write_text(str(child.pid))
        time.sleep(3600)
        return 3
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            verifier.DockerPromtoolClient,
            "create",
            lambda **kwargs: _FakePromtoolClient(anchor=_T0),
        )
        if case == "baseline":
            return verifier.main(
                [
                    "baseline",
                    "--compose-file",
                    "fixture.yaml",
                    "--evidence-dir",
                    str(directory),
                    "--output-name",
                    "baseline.json",
                ]
            )
        patch.setattr(
            verifier.DockerPromtoolClient,
            "create",
            lambda **kwargs: _FakePromtoolClient(
                anchor=_T0 + timedelta(days=1),
                healthy=case != "hold",
                snapshot=_live_snapshot(release_id="2" * 40) if case == "drift" else None,
            ),
        )
        return verifier.main(
            [
                "checkpoint",
                "--compose-file",
                "fixture.yaml",
                "--evidence-dir",
                str(directory),
                "--baseline-evidence",
                str(directory / "baseline.json"),
                "--output-name",
                "receipt.json",
            ]
        )


def _native_systemd(directory: Path) -> None:
    token = "obs2a" + uuid.uuid4().hex
    service_name, failure_name, timer_name = (
        token + ".service",
        token + "failure.service",
        token + ".timer",
    )
    unit_dir = Path("/run/systemd/system")
    source_service, source_timer, source_failure = (p.read_text() for p in UNITS)
    files = [unit_dir / name for name in (service_name, timer_name, failure_name)]
    for source, destination in zip((source_service, source_timer, source_failure), files):
        local = directory / destination.name
        local.write_text(source)
        _native(["sudo", "install", "-m", "0644", str(local), str(destination)])
    runtime = Path("/run") / token
    primary_failure: BaseException | None = None
    try:
        _native(["sudo", "systemctl", "daemon-reload"])
        command = _property(service_name, "Service", "ExecStart", "a(sasbttttuii)")
        expected = shlex.split(
            next(line[10:] for line in source_service.splitlines() if line.startswith("ExecStart="))
        )
        assert isinstance(command, list) and len(command) == 1
        assert command[0][0] == expected[0] and command[0][1] == expected and command[0][2] is False
        assert _property(service_name, "Unit", "FragmentPath", "s") == str(files[0])
        assert _property(service_name, "Unit", "DropInPaths", "as") == []
        assert _property(service_name, "Unit", "NeedDaemonReload", "b") is False
        assert _property(service_name, "Service", "User", "s") == "root"
        assert _property(service_name, "Service", "Type", "s") == "oneshot"
        assert _property(service_name, "Service", "TimeoutStartUSec", "t") == 600_000_000
        assert _property(service_name, "Service", "TimeoutStopUSec", "t") == 10_000_000
        assert _property(service_name, "Service", "RuntimeDirectoryPreserve", "s") == "yes"
        assert _property(service_name, "Service", "RuntimeDirectoryMode", "u") == 0o700
        assert _property(service_name, "Service", "KillMode", "s") == "control-group"
        assert _property(service_name, "Service", "Restart", "s") == "no"
        assert _property(service_name, "Unit", "OnFailure", "as") == [
            "pulseplate-premium-alias-checkpoint-failure.service"
        ]
        assert _property(failure_name, "Service", "TimeoutStartUSec", "t") == 960_000_000
        assert _property(timer_name, "Timer", "Persistent", "b") is True
        assert _property(timer_name, "Timer", "AccuracyUSec", "t") == 60_000_000
        assert _property(timer_name, "Timer", "RandomizedDelayUSec", "t") == 0
        calendar = _property(timer_name, "Timer", "TimersCalendar", "a(sst)")
        assert (
            isinstance(calendar, list)
            and len(calendar) == 1
            and calendar[0][1] == "*-*-* 04:15:00 UTC"
        )
        assert _property(timer_name, "Unit", "ActiveState", "s") == "inactive"
        assert (
            _native(["systemctl", "is-enabled", timer_name], check=False).stdout.strip()
            == "disabled"
        )
        # Declared scratch overrides exercise lifecycle; original properties above remain separate.
        failure_marker = directory / "onfailure"
        local = directory / failure_name
        local.write_text(f"[Service]\nType=oneshot\nExecStart=/usr/bin/touch {failure_marker}\n")
        _native(["sudo", "install", "-m", "0644", str(local), str(files[2])])
        assert _native_checkpoint_fixture("baseline", directory) == 0
        baseline_hash = hashlib.sha256((directory / "baseline.json").read_bytes()).hexdigest()
        for case, expected in (
            ("pass", 0),
            ("hold", 1),
            ("drift", 1),
            ("publication", 2),
            ("missing", 1),
            ("malformed", 1),
        ):
            receipt = directory / "receipt.json"
            receipt.unlink(missing_ok=True)
            failure_marker.unlink(missing_ok=True)
            if case == "publication":
                receipt.write_text("invalid existing publication")
            baseline = directory / "baseline.json"
            backup = baseline.read_bytes()
            if case == "missing":
                baseline.unlink()
            elif case == "malformed":
                baseline.write_text("invalid baseline")
            command = f"/usr/bin/flock --nonblock --conflict-exit-code=75 {runtime}/checkpoint.lock {sys.executable} -m tests.test_notify_premium_alias_checkpoint_failure --native-fixture {case} --directory {directory}"
            local = directory / service_name
            local.write_text(
                f"[Unit]\nOnFailure={failure_name}\n[Service]\nType=oneshot\nRuntimeDirectory={token}\nRuntimeDirectoryMode=0700\nRuntimeDirectoryPreserve=yes\nWorkingDirectory={ROOT}\nExecStart={command}\nTimeoutStartSec=10min\nTimeoutStopSec=10s\nKillMode=control-group\nRestart=no\n"
            )
            _native(["sudo", "install", "-m", "0644", str(local), str(files[0])])
            _native(["sudo", "systemctl", "daemon-reload"])
            _native(["sudo", "systemctl", "reset-failed", service_name])
            _native(["sudo", "systemctl", "start", service_name], check=expected == 0)
            assert _property(service_name, "Service", "ExecMainStatus", "i") == expected
            assert _property(service_name, "Unit", "ActiveState", "s") == (
                "inactive" if expected == 0 else "failed"
            )
            deadline = time.monotonic() + 10
            while expected != 0 and not failure_marker.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert failure_marker.exists() is (expected != 0)
            if case in {"pass", "hold"}:
                assert json.loads(receipt.read_text())["decision"] == (
                    "PASS" if case == "pass" else "HOLD"
                )
            if case in {"missing", "malformed"}:
                baseline.write_bytes(backup)
            assert hashlib.sha256(baseline.read_bytes()).hexdigest() == baseline_hash
        # An independent cooperating holder, not a coalesced start, exercises conflict75.
        lock = runtime / "checkpoint.lock"
        import fcntl

        with lock.open("a") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            inode = lock.stat().st_ino
            receipt.unlink(missing_ok=True)
            _native(["sudo", "systemctl", "reset-failed", service_name])
            _native(["sudo", "systemctl", "start", service_name], check=False)
            assert _property(service_name, "Service", "ExecMainStatus", "i") == 75
            _native(["sudo", "systemctl", "stop", service_name])
            assert lock.stat().st_ino == inode and not receipt.exists()
        _native(["sudo", "systemctl", "reset-failed", service_name])
        _native(["sudo", "systemctl", "start", service_name], check=False)
        assert _property(service_name, "Service", "ExecMainStatus", "i") == 0
        # Real host descendant cleanup under a disclosed accelerated timeout,
        # then explicit interruption under the unchanged10min/10s properties.
        scratch_service = local.read_text()
        for action in ("timeout", "interrupt"):
            receipt.unlink(missing_ok=True)
            pid_file = directory / "child.pid"
            pid_file.unlink(missing_ok=True)
            text = scratch_service.replace("--native-fixture malformed", "--native-fixture stall")
            if action == "timeout":
                text = text.replace("TimeoutStartSec=10min", "TimeoutStartSec=1s")
            local.write_text(text)
            _native(["sudo", "install", "-m", "0644", str(local), str(files[0])])
            _native(["sudo", "systemctl", "daemon-reload"])
            _native(["sudo", "systemctl", "reset-failed", service_name])
            _native(["sudo", "systemctl", "start", "--no-block", service_name])
            deadline = time.monotonic() + 10
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert pid_file.exists()
            pid = int(pid_file.read_text())
            if action == "interrupt":
                assert _property(service_name, "Service", "TimeoutStartUSec", "t") == 600_000_000
                assert _property(service_name, "Service", "TimeoutStopUSec", "t") == 10_000_000
                _native(["sudo", "systemctl", "stop", service_name])
            else:
                while (
                    _property(service_name, "Unit", "ActiveState", "s") != "failed"
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.05)
                assert _property(service_name, "Service", "Result", "s") == "timeout"
            deadline = time.monotonic() + 10
            alive = True
            while alive and time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    alive = False
                if alive:
                    time.sleep(0.05)
            assert not alive and not receipt.exists()
        # Restore the real canonical receipt fixture. These accelerated timer
        # calendars prove origin/catch-up only, not staging04:15 acceptance.
        text = (
            local.read_text()
            .replace("--native-fixture stall", "--native-fixture pass")
            .replace("TimeoutStartSec=1s", "TimeoutStartSec=10min")
        )
        local.write_text(text)
        _native(["sudo", "install", "-m", "0644", str(local), str(files[0])])
        for catch_up in (False, True):
            _native(["sudo", "systemctl", "stop", timer_name])
            receipt.unlink(missing_ok=True)
            at = (datetime.now(timezone.utc) + timedelta(seconds=-5 if catch_up else 5)).replace(
                microsecond=0
            )
            calendar = at.strftime("%Y-%m-%d %H:%M:%S UTC")
            timer = directory / timer_name
            timer.write_text(
                f"[Timer]\nUnit={service_name}\nOnCalendar={calendar}\nPersistent=true\nAccuracySec=1us\nRandomizedDelaySec=0\n[Install]\nWantedBy=timers.target\n"
            )
            _native(["sudo", "install", "-m", "0644", str(timer), str(files[1])])
            stamp = Path("/var/lib/systemd/timers") / ("stamp-" + timer_name)
            if catch_up:
                stamp.parent.mkdir(parents=True, exist_ok=True)
                stamp.touch()
                os.utime(stamp, (at.timestamp() - 60, at.timestamp() - 60))
            _native(["sudo", "systemctl", "daemon-reload"])
            _native(["sudo", "systemctl", "reset-failed", service_name])
            _native(["sudo", "systemctl", "start", timer_name])
            deadline = time.monotonic() + 15
            while not receipt.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert receipt.exists() and json.loads(receipt.read_text())["decision"] == "PASS"
            trigger = _property(timer_name, "Timer", "LastTriggerUSec", "t")
            invocation = _property(service_name, "Service", "ExecMainStartTimestamp", "t")
            assert type(trigger) is int and type(invocation) is int
            assert invocation >= trigger > int(at.timestamp() * 1_000_000)
            print(
                "native_timer_origin="
                + ("catch_up" if catch_up else "ordinary")
                + ":"
                + str(trigger),
                flush=True,
            )
            _native(["sudo", "systemctl", "stop", timer_name])
            stamp.unlink(missing_ok=True)
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        try:
            for name in (service_name, failure_name, timer_name):
                _native(["sudo", "systemctl", "stop", name])
            _native(["sudo", "rm", "--", *(str(path) for path in files)])
            _native(["sudo", "systemctl", "daemon-reload"])
            if runtime.exists():
                _native(["sudo", "rm", "-r", "--", str(runtime)])
        except Exception as cleanup_error:
            print(
                "native_cleanup_failure="
                + type(cleanup_error).__name__
                + ":"
                + str(cleanup_error)[:2048],
                flush=True,
            )
            if primary_failure is None:
                raise


def _owned_task_stopped(cid: str, command: str, started: float, probe: str) -> bool:
    """Observe the finite owned fixture census within the original 10s stop bound."""
    main = {"amtool": "alertmanager", "promtool": "prometheus"}[command]
    deadline = started + 10
    immediate: str | None = None
    terminal = ""
    observed = started
    stopped = False
    reason = "no_census_within_deadline"
    while (entered := time.monotonic()) < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        result = _native(["docker", "top", cid, "-eo", "comm"], timeout=min(2, remaining))
        terminal = result.stdout
        observed = time.monotonic()
        if immediate is None:
            immediate = terminal
        rows = terminal.splitlines()
        tasks = [row.strip() for row in rows[1:]]
        valid = (
            result.returncode == 0
            and len(rows) >= 2
            and rows[0].strip() == "COMMAND"
            and tasks.count(main) == 1
            and all(task in {main, command} for task in tasks)
        )
        if not valid:
            reason = "invalid_census"
            break
        if observed > deadline:
            reason = "observation_after_deadline"
            break
        if command not in tasks:
            stopped = True
            reason = "stopped"
            break
        reason = "task_present"
        time.sleep(min(0.1, max(0, deadline - observed)))
    if immediate is None:
        observed = entered
    print(
        json.dumps(
            {
                "probe": probe,
                "immediate": immediate,
                "terminal": terminal,
                "elapsed_seconds": observed - started,
                "stopped": stopped,
                "reason": reason,
            }
        ),
        flush=True,
    )
    return stopped


def _native_query_lifetime(directory: Path) -> None:
    from scripts import verify_premium_alias_telemetry as verifier

    release = threading.Event()
    entered = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            entered.set()
            release.wait(130)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(b'{"status":"success","data":{"resultType":"vector","result":[]}}')
            except BrokenPipeError:
                self.close_connection = True

        do_GET = do_POST

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 9090), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = directory / "prometheus.yml"
    config.write_text("global:\n  scrape_interval: 30s\nscrape_configs: []\n")
    cid = ""
    unit = "obs2aquery" + uuid.uuid4().hex + ".service"
    unit_file = Path("/run/systemd/system") / unit
    failures: list[str] = []
    primary_failure: BaseException | None = None
    try:
        cid = _native(
            [
                "docker",
                "run",
                "-d",
                "--network",
                "host",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--read-only",
                "--tmpfs",
                "/prometheus:uid=65532,gid=65532",
                "--user",
                "65532:65532",
                "-v",
                f"{config}:/etc/prometheus/prometheus.yml:ro",
                PROMETHEUS_IMAGE,
                "--config.file=/etc/prometheus/prometheus.yml",
                "--web.listen-address=127.0.0.1:19090",
                "--storage.tsdb.path=/prometheus",
            ]
        ).stdout.strip()
        assert len(cid) == 64 and all(c in "0123456789abcdef" for c in cid)
        docker = shutil.which("docker")
        assert docker is not None
        client = verifier.DockerPromtoolClient(docker=docker, compose_file=config)
        client._bound_prometheus_container_id = cid
        arguments = ["query", "instant", "-o", "json", "http://localhost:9090", "time()"]
        release.set()
        assert client._run_promtool(arguments).returncode == 0
        release.clear()
        entered.clear()
        with pytest.raises(verifier.VerificationError, match="docker_timeout"):
            client._run_promtool(arguments)
        assert entered.is_set()
        stopped = _owned_task_stopped(cid, "promtool", time.monotonic(), "P02_command_timeout")
        if not stopped:
            failures.append("owned promtool cleanup not proved within timeout plus10s stop bound")
        release.set()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            tasks = _native(["docker", "top", cid, "-eo", "comm"]).stdout.splitlines()[1:]
            if "promtool" not in [row.strip() for row in tasks]:
                break
            time.sleep(0.1)
        assert "promtool" not in [
            row.strip() for row in tasks
        ], "ordinary fixture response failed to finish task"
        release.clear()
        entered.clear()
        unit_file.write_text(
            f"[Service]\nType=oneshot\nWorkingDirectory={ROOT}\nExecStart={sys.executable} -m tests.test_notify_premium_alias_checkpoint_failure --query-container {cid}\nTimeoutStartSec=10min\nTimeoutStopSec=10s\nKillMode=control-group\nRestart=no\n"
        )
        _native(["sudo", "systemctl", "daemon-reload"])
        _native(["sudo", "systemctl", "start", "--no-block", unit])
        assert entered.wait(10), "actual interrupted Docker query never reached endpoint"
        stopped_at = time.monotonic()
        _native(["sudo", "systemctl", "stop", unit])
        if not _owned_task_stopped(cid, "promtool", stopped_at, "P02_systemd_interruption"):
            failures.append(
                "owned promtool cleanup not proved within interruption plus10s stop bound"
            )
        assert not failures, "P02 readiness HOLD: " + "; ".join(failures)
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        try:
            release.set()
            server.shutdown()
            server.server_close()
            thread.join(5)
            if unit_file.exists():
                _native(["sudo", "systemctl", "stop", unit])
                unit_file.unlink()
                _native(["sudo", "systemctl", "daemon-reload"])
            if cid:
                _native(["docker", "rm", "-f", cid])
        except Exception as cleanup_error:
            print(
                "native_cleanup_failure="
                + type(cleanup_error).__name__
                + ":"
                + str(cleanup_error)[:2048],
                flush=True,
            )
            if primary_failure is None:
                raise


def _native_amtool_lifetime(directory: Path) -> None:
    release = threading.Event()
    entered = threading.Event()
    methods: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            methods.append("POST")
            entered.set()
            release.wait(30)
            self.send_response(200)
            self.end_headers()

        def do_GET(self) -> None:
            methods.append("GET")
            release.wait(30)
            self.send_error(500)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 9093), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = directory / "amtool-lifetime.yml"
    config.write_text("route:\n  receiver: synthetic\nreceivers:\n  - name: synthetic\n")
    config.chmod(0o444)
    compose = directory / "amtool-compose.yaml"
    compose.write_text(
        f"services:\n  alertmanager:\n    image: {ALERTMANAGER_IMAGE}\n    platform: linux/amd64\n    user: '65534:65534'\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    read_only: true\n    network_mode: host\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:19093']\n    volumes: ['{config}:/etc/alertmanager/alertmanager.yml:ro']\n"
    )
    prefix = ["docker", "compose", "-f", str(compose)]
    cid = ""
    unit = "obs2aamtool" + uuid.uuid4().hex + ".service"
    unit_file = Path("/run/systemd/system") / unit
    failures: list[str] = []
    primary_failure: BaseException | None = None
    try:
        _native([*prefix, "up", "-d", "--no-deps", "alertmanager"], timeout=120)
        cid = _native([*prefix, "ps", "-q", "alertmanager"]).stdout.strip()
        assert len(cid) == 64 and all(c in "0123456789abcdef" for c in cid)
        docker = shutil.which("docker")
        assert docker is not None
        start = datetime.now(timezone.utc)
        argv = notifier._argv(
            docker,
            compose,
            "staging",
            notifier._timestamp(start),
            notifier._timestamp(start + timedelta(seconds=900)),
        )
        release.set()
        assert notifier._send(argv)
        release.clear()
        entered.clear()
        assert notifier._send(argv) is False
        assert (
            entered.is_set() and "GET" not in methods
        ), "uncontexted status request occurred despite no-version-check"
        stopped = _owned_task_stopped(cid, "amtool", time.monotonic(), "P01_command_timeout")
        if not stopped:
            failures.append("owned amtool cleanup not proved within timeout plus10s stop bound")
        release.set()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            tasks = _native(["docker", "top", cid, "-eo", "comm"]).stdout.splitlines()[1:]
            if "amtool" not in [row.strip() for row in tasks]:
                break
            time.sleep(0.1)
        assert "amtool" not in [
            row.strip() for row in tasks
        ], "ordinary fixture response failed to finish task"
        release.clear()
        entered.clear()
        unit_file.write_text(
            f"[Service]\nType=oneshot\nWorkingDirectory={ROOT}\nExecStart={sys.executable} -m scripts.ops.notify_premium_alias_checkpoint_failure --compose-file {compose} --environment staging\nTimeoutStartSec=16min\nTimeoutStopSec=10s\nKillMode=control-group\nRestart=no\n"
        )
        _native(["sudo", "systemctl", "daemon-reload"])
        _native(["sudo", "systemctl", "start", "--no-block", unit])
        assert entered.wait(10)
        stopped_at = time.monotonic()
        _native(["sudo", "systemctl", "stop", unit])
        if not _owned_task_stopped(cid, "amtool", stopped_at, "P01_systemd_interruption"):
            failures.append(
                "owned amtool cleanup not proved within interruption plus10s stop bound"
            )
        assert not failures, "P01/L03 readiness HOLD: " + "; ".join(failures)
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        try:
            release.set()
            server.shutdown()
            server.server_close()
            thread.join(5)
            if unit_file.exists():
                _native(["sudo", "systemctl", "stop", unit])
                unit_file.unlink()
                _native(["sudo", "systemctl", "daemon-reload"])
            if cid:
                _native(["docker", "rm", "-f", cid])
        except Exception as cleanup_error:
            print(
                "native_cleanup_failure="
                + type(cleanup_error).__name__
                + ":"
                + str(cleanup_error)[:2048],
                flush=True,
            )
            if primary_failure is None:
                raise


def _native_alertmanager(directory: Path) -> None:
    """Actual pinned AM, exact route timings, private synthetic TLS SMTP receiver."""
    from socketserver import ThreadingTCPServer, StreamRequestHandler

    received: list[bytes] = []
    cert, key = directory / "smtp.crt", directory / "smtp.key"
    _native(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=smtp.resend.com",
            "-addext",
            "subjectAltName=DNS:smtp.resend.com",
        ],
        timeout=30,
    )
    cert.chmod(0o444)
    key.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)

    class Handler(StreamRequestHandler):
        def handle(self) -> None:
            self.wfile.write(b"220 synthetic fixture\r\n")
            while True:
                line = self.rfile.readline(4097)
                if not line or len(line) > 4096:
                    return
                command = line.split(b" ", 1)[0].strip().upper()
                if command == b"EHLO":
                    self.wfile.write(b"250-fixture\r\n250 AUTH PLAIN\r\n")
                elif command == b"AUTH":
                    self.wfile.write(b"235 authenticated synthetic account\r\n")
                elif command in {b"MAIL", b"RCPT", b"RSET"}:
                    self.wfile.write(b"250 ok\r\n")
                elif command == b"DATA":
                    self.wfile.write(b"354 data\r\n")
                    payload = bytearray()
                    while True:
                        row = self.rfile.readline(4097)
                        if row == b".\r\n":
                            break
                        if not row or len(row) > 4096 or len(payload) + len(row) > 65536:
                            return
                        payload.extend(row)
                    received.append(bytes(payload))
                    self.wfile.write(b"250 received\r\n")
                elif command == b"QUIT":
                    self.wfile.write(b"221 closing\r\n")
                    return
                else:
                    self.wfile.write(b"500 unsupported fixture command\r\n")

    class Server(ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

        def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
            sock, address = super().get_request()
            sock.settimeout(10)
            return context.wrap_socket(sock, server_side=True), address

    server = Server(("127.0.0.1", 2465), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    configuration = directory / "alertmanager.yml"
    configuration.write_bytes((ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes())
    configuration.chmod(0o444)
    secret = directory / "synthetic-smtp"
    secret.write_text("synthetic-smtp")
    secret.chmod(0o444)
    compose = directory / "compose.yaml"
    compose.write_text(
        f"services:\n  alertmanager:\n    image: {ALERTMANAGER_IMAGE}\n    platform: linux/amd64\n    user: '65534:65534'\n    read_only: true\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    network_mode: host\n    extra_hosts: ['smtp.resend.com:127.0.0.1']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:9093']\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    volumes:\n      - {configuration}:/etc/alertmanager/alertmanager.yml:ro\n      - {secret}:/run/secrets/alertmanager_smtp_key:ro\n      - {cert}:/etc/ssl/certs/ca-certificates.crt:ro\n"
    )
    docker = shutil.which("docker")
    assert docker is not None
    prefix = ["docker", "compose", "-f", str(compose)]
    cid = ""
    primary_failure: BaseException | None = None
    try:
        _native([*prefix, "up", "-d", "--no-deps", "alertmanager"], timeout=120)
        cid = _native([*prefix, "ps", "-q", "alertmanager"]).stdout.strip()
        assert len(cid) == 64 and all(c in "0123456789abcdef" for c in cid)
        query = [
            *prefix,
            "exec",
            "-T",
            "alertmanager",
            "/bin/amtool",
            "--alertmanager.url=http://127.0.0.1:9093",
            "--no-version-check",
            "--timeout=10s",
            "-o",
            "json",
            "alert",
            "query",
            "alertname=PulsePlateAliasCheckpointFailed",
        ]
        setup_started = time.monotonic()
        setup_deadline = setup_started + 30
        while time.monotonic() < setup_deadline:
            result = _native(query, timeout=min(10, setup_deadline - time.monotonic()), check=False)
            if result.returncode == 0:
                assert (
                    time.monotonic() <= setup_deadline
                ), "native Alertmanager API readiness deadline exceeded"
                assert json.loads(result.stdout) == [], "fixture has unexpected pre-event alerts"
                break
            time.sleep(min(0.1, max(0, setup_deadline - time.monotonic())))
        else:
            raise AssertionError("native Alertmanager API readiness deadline exceeded")
        print(
            "native_alertmanager_api_ready_seconds=" + str(time.monotonic() - setup_started),
            flush=True,
        )
        start = datetime.now(timezone.utc)
        end = start + timedelta(seconds=900)
        argv = notifier._argv(
            docker, compose, "staging", notifier._timestamp(start), notifier._timestamp(end)
        )
        # Real native command, then an actual same-event resend and later event.
        assert notifier._send(argv)
        first = json.loads(_native(query).stdout)
        assert len(first) == 1 and first[0]["labels"] == {
            "alertname": "PulsePlateAliasCheckpointFailed",
            "environment": "staging",
            "alias": "all",
            "severity": "warning",
        }
        fingerprint = first[0]["fingerprint"]
        epoch = time.monotonic()
        for slot in range(1, 15):
            time.sleep(max(0, epoch + slot * 60 - time.monotonic()))
            assert notifier._send(argv)
            assert json.loads(_native(query).stdout)[0]["fingerprint"] == fingerprint
        assert len(received) == 1, "actual 30s/5m/24h route did not deliver one deduplicated event"
        time.sleep(max(0, epoch + 905 - time.monotonic()))
        assert json.loads(_native(query).stdout) == [], "bounded event did not expire"
        later = datetime.now(timezone.utc)
        assert notifier._send(
            notifier._argv(
                docker,
                compose,
                "staging",
                notifier._timestamp(later),
                notifier._timestamp(later + timedelta(seconds=900)),
            )
        )
        assert json.loads(_native(query).stdout)[0]["fingerprint"] == fingerprint
        time.sleep(325)
        # Preserve observed repeat suppression; this is not a second mailbox claim.
        print("native_same_fingerprint_repeat_notifications=" + str(len(received)), flush=True)
        assert (
            len(received) == 1
        ), "same-fingerprint repeated event escaped the admitted24h dedup after a full5min group cycle"
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        try:
            if cid:
                _native(["docker", "rm", "-f", cid])
            server.shutdown()
            server.server_close()
            thread.join(5)
        except Exception as cleanup_error:
            print(
                "native_cleanup_failure="
                + type(cleanup_error).__name__
                + ":"
                + str(cleanup_error)[:2048],
                flush=True,
            )
            if primary_failure is None:
                raise


def _native_compose_configuration(directory: Path) -> None:
    """Original-model synthetic configuration only; no host secrets or runtime proof."""
    from scripts import verify_premium_alias_telemetry as verifier

    fixture = directory / "compose-configuration"
    fixture.mkdir(mode=0o700)
    original = (ROOT / "deploy/docker-compose.staging.yaml").read_bytes()
    compose = fixture / "docker-compose.staging.yaml"
    compose.write_bytes(original)
    application_env = fixture / "application.env"
    application_env.write_text("")
    backend = "ghcr.io/pulseplate/checkpoint-fixture@sha256:" + "1" * 64
    caddy = "ghcr.io/pulseplate/caddy-fixture@sha256:" + "2" * 64
    inputs = {
        "POSTGRES_USER": "synthetic_user",
        "POSTGRES_DB": "synthetic_db",
        "STAGING_DOMAIN": "checkpoint.invalid",
        "STAGING_ENV_FILE": str(application_env),
        "STAGING_IMAGE_REF": backend,
        "STAGING_CADDY_IMAGE_REF": caddy,
    }
    docker = shutil.which("docker")
    assert docker is not None and os.path.isabs(docker), "native Compose binary unavailable"
    client = verifier.DockerPromtoolClient(docker=docker, compose_file=compose)
    argv = [*client._compose_prefix, "config", "--format", "json"]
    for missing in (None, "STAGING_IMAGE_REF", "STAGING_CADDY_IMAGE_REF"):
        (fixture / ".env").write_text(
            "".join(f"{key}={value}\n" for key, value in inputs.items() if key != missing)
        )
        result = _native(argv, cwd=fixture, check=False)
        assert compose.read_bytes() == original, "native config changed the copied original model"
        if missing is not None:
            assert result.returncode != 0, "native config accepted a missing required image binding"
            assert (
                missing in result.stderr
            ), "native rejection did not identify the omitted image binding"
            print("native_compose_configuration_missing_" + missing + "=rejected", flush=True)
            continue
        assert result.returncode == 0, "native original-model configuration failed"
        services = json.loads(result.stdout)["services"]
        assert services["app"]["image"] == backend, "native app image binding differs"
        assert services["worker"]["image"] == backend, "native worker image binding differs"
        assert services["caddy"]["image"] == caddy, "native Caddy image binding differs"
        print("native_compose_configuration_positive=pass", flush=True)


def native_main() -> None:
    assert sys.platform == "linux", "native mode requires the existing Linux CI runner"
    with tempfile.TemporaryDirectory(prefix="pulseplate-obs2a-native-") as raw:
        directory = Path(raw)
        failures: list[str] = []
        for name, check in (
            ("compose_configuration", _native_compose_configuration),
            ("systemd", _native_systemd),
            ("query_lifetime", _native_query_lifetime),
            ("amtool_lifetime", _native_amtool_lifetime),
            ("alertmanager", _native_alertmanager),
        ):
            try:
                check(directory)
            except Exception as exc:
                failures.append(name)
                print(
                    "native_failure=" + name + ":" + type(exc).__name__ + ":" + str(exc)[:2048],
                    flush=True,
                )
        assert not failures, "native checks failed: " + ",".join(failures)


@pytest.mark.parametrize(
    "fault", ["none", "positive-rejected", "wrong-worker", "negative-accepted"]
)
def test_checkpoint_original_compose_fixture_classifies_only_synthetic_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/docker")

    def config(argv: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        assert argv == [
            "/absolute/docker",
            "compose",
            "-f",
            str(cwd / "docker-compose.staging.yaml"),
            "config",
            "--format",
            "json",
        ]
        assert (cwd / "docker-compose.staging.yaml").read_bytes() == (
            ROOT / "deploy/docker-compose.staging.yaml"
        ).read_bytes()
        assert (cwd / "application.env").read_bytes() == b""
        assert cwd.stat().st_mode & 0o777 == 0o700
        text = (cwd / ".env").read_text()
        assert "POSTGRES_USER=synthetic_user\n" in text and "POSTGRES_DB=synthetic_db\n" in text
        assert "STAGING_DOMAIN=checkpoint.invalid\n" in text
        calls.append(argv)
        if len(calls) == 1:
            assert "STAGING_IMAGE_REF=" in text and "STAGING_CADDY_IMAGE_REF=" in text
            backend = "ghcr.io/pulseplate/checkpoint-fixture@sha256:" + "1" * 64
            caddy = "ghcr.io/pulseplate/caddy-fixture@sha256:" + "2" * 64
            model = {
                "services": {
                    "app": {"image": backend},
                    "worker": {"image": backend if fault != "wrong-worker" else caddy},
                    "caddy": {"image": caddy},
                }
            }
            return subprocess.CompletedProcess(
                argv, 1 if fault == "positive-rejected" else 0, json.dumps(model), ""
            )
        missing = "STAGING_IMAGE_REF" if len(calls) == 2 else "STAGING_CADDY_IMAGE_REF"
        retained = "STAGING_CADDY_IMAGE_REF" if len(calls) == 2 else "STAGING_IMAGE_REF"
        assert missing + "=" not in text and retained + "=" in text
        return subprocess.CompletedProcess(
            argv,
            0 if fault == "negative-accepted" else 1,
            "",
            missing + " synthetic interpolation rejection",
        )

    monkeypatch.setattr(sys.modules[__name__], "_native", config)
    if fault == "none":
        _native_compose_configuration(tmp_path)
        assert len(calls) == 3
    else:
        with pytest.raises(AssertionError):
            _native_compose_configuration(tmp_path)
    output = capsys.readouterr().out
    assert "synthetic_db" not in output and "postgresql" not in output


def test_checkpoint_native_main_selects_original_model_configuration_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(sys, "platform", "linux")
    for name in (
        "_native_compose_configuration",
        "_native_systemd",
        "_native_query_lifetime",
        "_native_amtool_lifetime",
        "_native_alertmanager",
    ):
        monkeypatch.setattr(
            sys.modules[__name__], name, lambda directory, selected=name: calls.append(selected)
        )
    native_main()
    assert calls == [
        "_native_compose_configuration",
        "_native_systemd",
        "_native_query_lifetime",
        "_native_amtool_lifetime",
        "_native_alertmanager",
    ]


def test_checkpoint_native_config_command_uses_only_fixture_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/docker")

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert argv == ["/absolute/docker", "compose", "config"]
        assert kwargs["cwd"] == tmp_path
        assert kwargs["env"] == {
            "PATH": os.defpath,
            "LANG": "C",
            "HOME": str(tmp_path),
            "COMPOSE_PROFILES": "",
        }
        assert kwargs["timeout"] == 30 and kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["capture_output"] is True and kwargs["check"] is False
        return subprocess.CompletedProcess(argv, 0, "{}", "")

    monkeypatch.setattr(subprocess, "run", run)
    assert _native(["docker", "compose", "config"], cwd=tmp_path).returncode == 0


@pytest.mark.parametrize(
    "output",
    [
        "",
        "COMMAND\n",
        "COMMAND\n\n",
        "PID COMMAND\nalertmanager\n",
        "COMMAND\nother\n",
        "COMMAND\nalertmanager\nother\n",
        "COMMAND\nalertmanager\nalertmanager\n",
        "COMMAND\nalertmanager amtool\n",
    ],
)
def test_owned_task_census_rejects_malformed_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], output: str
) -> None:
    monkeypatch.setattr(time, "monotonic", lambda: 0)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, output, ""),
    )
    assert not _owned_task_stopped("a" * 64, "amtool", 0, "fixture_malformed")
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["immediate"] == evidence["terminal"] == output
    assert evidence["stopped"] is False
    assert evidence["reason"] == "invalid_census"


@pytest.mark.parametrize("command,main", [("amtool", "alertmanager"), ("promtool", "prometheus")])
@pytest.mark.parametrize("observed,expected", [(1, True), (10, True), (11, False)])
def test_owned_task_census_absence_requires_timely_observation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    main: str,
    observed: int,
    expected: bool,
) -> None:
    times = iter([0, 0, observed])
    output = "COMMAND\n" + main + "\n"
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, output, ""),
    )
    assert _owned_task_stopped("a" * 64, command, 0, "fixture_absence") is expected
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["immediate"] == evidence["terminal"] == output
    assert evidence["elapsed_seconds"] == observed
    assert evidence["stopped"] is expected
    assert evidence["reason"] == ("stopped" if expected else "observation_after_deadline")


def test_owned_task_census_rejects_failed_execution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(time, "monotonic", lambda: 0)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "COMMAND\nalertmanager\n", ""),
    )
    assert not _owned_task_stopped("a" * 64, "amtool", 0, "fixture_execution_failed")
    assert json.loads(capsys.readouterr().out)["reason"] == "invalid_census"


def test_owned_task_census_never_probes_after_stop_deadline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(time, "monotonic", lambda: 11)
    monkeypatch.setattr(
        sys.modules[__name__], "_native", lambda *args, **kwargs: pytest.fail("late census started")
    )
    assert not _owned_task_stopped("a" * 64, "amtool", 0, "fixture_already_late")
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["immediate"] is None and evidence["terminal"] == ""
    assert evidence["elapsed_seconds"] == 11
    assert evidence["reason"] == "no_census_within_deadline"


@pytest.mark.parametrize("command,main", [("amtool", "alertmanager"), ("promtool", "prometheus")])
@pytest.mark.parametrize("terminates", [True, False])
def test_owned_task_census_tracks_real_survival_shape(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    main: str,
    terminates: bool,
) -> None:
    times = iter([0, 0, 1, 9, 9, 9.5, 10])
    first = "COMMAND\n" + main + "\n" + command + "\n"
    terminal = "COMMAND\n" + main + "\n" + ("" if terminates else command + "\n")
    outputs = iter([first, terminal])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(time, "sleep", lambda delay: None)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, next(outputs), ""),
    )
    assert _owned_task_stopped("a" * 64, command, 0, "fixture_survival") is terminates
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["immediate"] == first and evidence["terminal"] == terminal
    assert evidence["elapsed_seconds"] == 9.5
    assert evidence["stopped"] is terminates
    assert evidence["reason"] == ("stopped" if terminates else "task_present")


def test_cleanup_failure_stops_notification_loop(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[int] = []

    class Process:
        pid = 123

        async def wait(self) -> int:
            calls.append(1)
            raise TimeoutError("private-sentinel")

    async def spawn(*args: str, **kwargs: object) -> Process:
        del args, kwargs
        return Process()

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", lambda pid, sig: None)
    monkeypatch.setattr(notifier.shutil, "which", lambda name: sys.executable)
    assert notifier.main(["--compose-file", "compose.yaml", "--environment", "staging"]) == 1
    assert calls == [1, 1]
    assert capsys.readouterr().out == notifier.ERROR + "\n"


def test_cancellation_survives_secondary_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    waits: list[int] = []

    class Process:
        pid = 123

        async def wait(self) -> int:
            waits.append(1)
            if len(waits) == 1:
                raise asyncio.CancelledError
            raise TimeoutError("private-sentinel")

    async def spawn(*args: str, **kwargs: object) -> Process:
        del args, kwargs
        return Process()

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", lambda pid, sig: None)
    with pytest.raises(asyncio.CancelledError):
        notifier._send(["/absolute/docker"])
    assert waits == [1, 1]
    assert capsys.readouterr().out == notifier.ERROR + "\n"


def test_vanished_group_still_reaps_with_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[int] = []

    class Process:
        pid = 123

        async def wait(self) -> int:
            waits.append(1)
            if len(waits) == 1:
                raise TimeoutError("private-sentinel")
            return -9

    async def spawn(*args: str, **kwargs: object) -> Process:
        del args, kwargs
        return Process()

    def vanished(pid: int, sig: int) -> None:
        assert pid == 123 and sig == signal.SIGKILL
        raise ProcessLookupError("private-sentinel")

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", vanished)
    assert notifier._send(["/absolute/docker"]) is False
    assert waits == [1, 1]


def test_expired_before_first_attempt_is_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    origin = datetime(2026, 10, 5, tzinfo=timezone.utc)
    times = iter([origin, origin + timedelta(seconds=900)])

    class DateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return next(times)

    monkeypatch.setattr(notifier, "datetime", DateTime)
    monkeypatch.setattr(notifier, "_send", lambda argv: pytest.fail("expired alert submitted"))
    assert (
        notifier.notify(
            docker="/absolute/docker", compose_file=Path("compose.yaml"), environment="staging"
        )
        == 1
    )
    assert capsys.readouterr().out == notifier.ERROR + "\n"


def test_interruption_never_resends(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = 0

    def send(argv: list[str]) -> bool:
        nonlocal calls
        del argv
        calls += 1
        raise KeyboardInterrupt

    monkeypatch.setattr(notifier, "_send", send)
    monkeypatch.setattr(notifier.shutil, "which", lambda name: sys.executable)
    assert notifier.main(["--compose-file", "compose.yaml", "--environment", "staging"]) == 1
    assert calls == 1 and capsys.readouterr().out == notifier.ERROR + "\n"


@pytest.mark.parametrize(
    "case,expected",
    [("pass", 0), ("hold", 1), ("drift", 1), ("publication", 2), ("missing", 1), ("malformed", 1)],
)
def test_native_receipt_fixture_has_real_canonical_stimulus(
    tmp_path: Path, case: str, expected: int
) -> None:
    assert _native_checkpoint_fixture("baseline", tmp_path) == 0
    baseline = tmp_path / "baseline.json"
    raw = baseline.read_bytes()
    if case == "publication":
        (tmp_path / "receipt.json").write_text("invalid existing publication")
    elif case == "missing":
        baseline.unlink()
    elif case == "malformed":
        baseline.write_text("invalid baseline")
    assert _native_checkpoint_fixture(case, tmp_path) == expected
    if case in {"pass", "hold", "drift", "publication"}:
        assert baseline.read_bytes() == raw


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--query-container")
    parser.add_argument("--native-fixture")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if args.native:
        native_main()
    elif args.query_container:
        from scripts import verify_premium_alias_telemetry as verifier

        cid = args.query_container
        assert len(cid) == 64 and all(c in "0123456789abcdef" for c in cid)
        docker = shutil.which("docker")
        assert docker is not None
        client = verifier.DockerPromtoolClient(docker=docker, compose_file=Path("unused.yaml"))
        client._bound_prometheus_container_id = cid
        client._run_promtool(["query", "instant", "-o", "json", "http://localhost:9090", "time()"])
    elif args.native_fixture and args.directory:
        raise SystemExit(_native_checkpoint_fixture(args.native_fixture, args.directory))
    else:
        parser.error("explicit native mode required")
