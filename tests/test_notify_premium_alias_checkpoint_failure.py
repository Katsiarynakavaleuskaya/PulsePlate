"""Deterministic notifier checks and explicitly selected native Linux controls."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shlex
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
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from html import escape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from scripts.ops import notify_premium_alias_checkpoint_failure as notifier

ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS_IMAGE = json.loads((ROOT / "deploy/prometheus/image-manifest.json").read_text())[
    "runtime_ref"
]
ALERTMANAGER_IMAGE = (
    "prom/alertmanager@sha256:84967b9b7ba45e38a9278d3e594305f43d4993c310df3905b51138b816c365f3"
)
SYSTEMD_UNIT_DIRECTORY = Path("/run/systemd/system")
RUNBOOK_URL = (
    "https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/"
    "docs/deploy/OPERATIONAL_SIGNALS.md#daily-checkpoint"
)
RENDER_LABELS = (
    'PulsePlate <em>checkpoint</em> & "quoted" {{ .ExternalURL }}',
    "staging <strong>inert</strong> & 'quoted'",
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


class _EmailHTML(HTMLParser):
    """Observe every tag and href occurrence in the fixed native email fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[str, str, list[tuple[str, str | None]]]] = []
        self.hrefs: list[str | None] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(("start", tag, attrs))
        self.hrefs.extend(value for name, value in attrs if name == "href")

    def handle_endtag(self, tag: str) -> None:
        self.events.append(("end", tag, []))

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_comment(self, data: str) -> None:
        raise AssertionError("Unexpected comment in the fixed email fragment")

    def handle_decl(self, decl: str) -> None:
        raise AssertionError("Unexpected declaration in the fixed email fragment")


def _assert_alertmanager_html(html: str, alertname: str, environment: str) -> None:
    """Require the authored scaffold, singleton ordered href and visible label meaning."""
    observer = _EmailHTML()
    observer.feed(html.replace("\r\n", "\n"))
    observer.close()
    assert observer.hrefs == [RUNBOOK_URL]
    assert observer.events == [
        ("start", "p", []),
        ("end", "p", []),
        ("start", "p", []),
        ("start", "a", [("href", RUNBOOK_URL)]),
        ("end", "a", []),
        ("end", "p", []),
    ]
    assert "".join(observer.text).strip("\n") == (
        f"PulsePlate alert {alertname} ({environment}).\nOpen PulsePlate monitoring runbook"
    )


def _assert_alertmanager_email(payload: bytes, alertname: str, environment: str) -> None:
    """Inspect actual MIME alternatives with strict UTF-8 decoding and no defect fallback."""
    message = BytesParser(policy=policy.default).parsebytes(payload)
    assert isinstance(message, EmailMessage)
    assert not any(part.defects for part in message.walk())
    assert message.get_all("MIME-Version") == ["1.0"]
    assert len(message.get_all("Content-Type", [])) == 1
    assert message.get_content_type() == "multipart/alternative"
    parts = list(message.iter_parts())
    assert len(parts) == 2
    assert sorted(part.get_content_type() for part in parts) == ["text/html", "text/plain"]
    bodies: dict[str, str] = {}
    for part in parts:
        assert not part.is_multipart()
        assert part.get_all("Content-Disposition", []) == []
        assert len(part.get_all("Content-Type", [])) == 1
        assert part.get_content_charset() == "utf-8"
        assert len(part.get_all("Content-Transfer-Encoding", [])) == 1
        assert str(part["Content-Transfer-Encoding"]).lower() in {
            "7bit",
            "8bit",
            "quoted-printable",
            "base64",
        }
        decoded = part.get_payload(decode=True)
        assert isinstance(decoded, bytes)
        assert not part.defects
        bodies[part.get_content_type()] = decoded.decode("utf-8", errors="strict").replace(
            "\r\n", "\n"
        )
    assert not any(part.defects for part in message.walk())
    assert bodies["text/plain"].rstrip("\n") == (
        f"PulsePlate alert {alertname} ({environment}).\n"
        f"Open PulsePlate monitoring runbook: {RUNBOOK_URL}"
    )
    _assert_alertmanager_html(bodies["text/html"], alertname, environment)


def _email_fixture(*, cte: str = "quoted-printable") -> EmailMessage:
    """Construct synthetic decoder controls, never a substitute for native SMTP capture."""
    message = EmailMessage(policy=policy.SMTP)
    message.set_content(
        "PulsePlate alert PulsePlateAliasCheckpointFailed (staging).\n"
        f"Open PulsePlate monitoring runbook: {RUNBOOK_URL}\n",
        cte=cte,
    )
    message.add_alternative(
        "<p>PulsePlate alert PulsePlateAliasCheckpointFailed (staging).</p>\n"
        f'<p><a href="{RUNBOOK_URL}">Open PulsePlate monitoring runbook</a></p>\n',
        subtype="html",
        cte=cte,
    )
    return message


@pytest.mark.parametrize("cte", ["7bit", "8bit", "quoted-printable", "base64"])
def test_alertmanager_email_mime_accepts_expected_alternatives(cte: str) -> None:
    """The observer decodes supported native body encodings before evaluating content."""
    _assert_alertmanager_email(
        _email_fixture(cte=cte).as_bytes(), "PulsePlateAliasCheckpointFailed", "staging"
    )


def test_alertmanager_html_observer_keeps_escaped_label_text() -> None:
    """Synthetic escaping checks the observer; the native producer has its own render control."""
    alertname, environment = RENDER_LABELS
    html = (
        f"<p>PulsePlate alert {escape(alertname)} ({escape(environment)}).</p>\n"
        f'<p><a href="{RUNBOOK_URL}">Open PulsePlate monitoring runbook</a></p>\n'
    )
    _assert_alertmanager_html(html, alertname, environment)


@pytest.mark.parametrize("cte", ["quoted-printable", "base64"])
@pytest.mark.parametrize(
    "fault",
    [
        "missing-plain",
        "missing-html",
        "extra-part",
        "attachment",
        "boundary",
        "charset",
        "unknown-encoding",
        "invalid-base64",
        "invalid-utf8",
        "private-href",
        "extra-private-href",
        "duplicate-href",
        "duplicate-href-attribute",
        "missing-href",
        "missing-plain-link",
        "wrong-plain-link",
        "raw-sentinel",
        "label-markup",
        "comment",
        "declaration",
    ],
)
def test_alertmanager_email_mime_rejects_content_drift(fault: str, cte: str) -> None:
    """Malformed, extra and encoded wrong content cannot pass through a good URL substring."""
    message = _email_fixture(cte=cte)
    plain, html = message.get_payload()
    if fault in {"missing-plain", "missing-html"}:
        message.set_payload([html if fault == "missing-plain" else plain])
    elif fault == "extra-part":
        extra = EmailMessage()
        extra.set_content("extra body")
        message.attach(extra)
    elif fault == "attachment":
        html.add_header("Content-Disposition", "attachment", filename="email.html")
    elif fault == "boundary":
        message.set_boundary("synthetic-email-boundary")
    elif fault == "charset":
        html.replace_header("Content-Type", 'text/html; charset="unknown-charset"')
    elif fault == "unknown-encoding":
        html.replace_header("Content-Transfer-Encoding", "unknown-transfer")
    elif fault == "invalid-base64":
        html.replace_header("Content-Transfer-Encoding", "base64")
        html.set_payload("%%%")
    elif fault == "invalid-utf8":
        plain.replace_header("Content-Transfer-Encoding", "base64")
        plain.set_payload(base64.b64encode(b"\xff").decode("ascii"))
    elif fault in {"missing-plain-link", "wrong-plain-link", "raw-sentinel"}:
        text = plain.get_content()
        replacement = "" if fault == "missing-plain-link" else "http://private-container:9090"
        text = (
            text + "raw-secret-sentinel"
            if fault == "raw-sentinel"
            else text.replace(RUNBOOK_URL, replacement)
        )
        plain.set_content(text, cte=cte)
    else:
        text = html.get_content()
        anchor = f'<a href="{RUNBOOK_URL}">'
        if fault == "private-href":
            text = text.replace(RUNBOOK_URL, "http://private-container:9093")
        elif fault == "extra-private-href":
            text += '<a href="http://private-container:9093">private</a>'
        elif fault == "duplicate-href":
            text += f'<a href="{RUNBOOK_URL}">duplicate</a>'
        elif fault == "duplicate-href-attribute":
            text = text.replace(anchor, f'<a href="{RUNBOOK_URL}" href="{RUNBOOK_URL}">')
        elif fault == "missing-href":
            text = text.replace(anchor, "<a>")
        elif fault == "label-markup":
            text = text.replace("PulsePlateAliasCheckpointFailed", "<em>injected label</em>")
        elif fault == "comment":
            text += "<!-- unexpected -->"
        else:
            assert fault == "declaration"
            text = "<!DOCTYPE html>" + text
        html.set_content(text, subtype="html", cte=cte)
    payload = message.as_bytes()
    if fault == "boundary":
        payload = payload.replace(b"--synthetic-email-boundary--\r\n", b"")
    with pytest.raises((AssertionError, UnicodeDecodeError)):
        _assert_alertmanager_email(payload, "PulsePlateAliasCheckpointFailed", "staging")


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
    assert "--no-version-check" in argv and "--timeout=8s" in argv
    assert notifier.COMMAND_TIMEOUT_SECONDS == 10
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
    environment = {
        "PATH": os.defpath,
        "LANG": "C",
        "HOME": str(cwd) if cwd else "/tmp",
        "COMPOSE_PROFILES": "",
    }
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
    from tests.test_premium_alias_telemetry_verifier import _T0, _FakePromtoolClient, _live_snapshot

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


def _reset_failed_invocation(unit: str, previous_state: str) -> None:
    """Reset only a known failed scratch invocation; start owns loading otherwise."""
    assert previous_state in {"inactive", "failed"}
    if previous_state == "failed":
        assert _property(unit, "Unit", "ActiveState", "s") == "failed"
        result = _property(unit, "Service", "Result", "s")
        assert isinstance(result, str) and result and result != "success"
        _native(["sudo", "systemctl", "reset-failed", unit])


def _finish_failure_handler(unit: str, marker: Path) -> None:
    """The disclosed remain-after-exit scratch handler gives typed completion proof."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if marker.exists() and _property(unit, "Unit", "ActiveState", "s") == "active":
            assert _property(unit, "Service", "Result", "s") == "success"
            assert _property(unit, "Service", "ExecMainStatus", "i") == 0
            _native(["sudo", "systemctl", "stop", unit])
            return
        time.sleep(0.05)
    raise AssertionError("owned failure handler did not complete within its observation bound")


def _native_systemd(directory: Path) -> None:
    token = "obs2a" + uuid.uuid4().hex
    service_name, failure_name, timer_name = (
        token + ".service",
        token + "failure.service",
        token + ".timer",
    )
    unit_dir = SYSTEMD_UNIT_DIRECTORY
    source_service, source_timer, source_failure = (p.read_text() for p in UNITS)
    files = [unit_dir / name for name in (service_name, timer_name, failure_name)]
    runtime = Path("/run") / token
    primary_failure: BaseException | None = None
    installed: list[Path] = []
    previous_state = "inactive"
    try:
        for source, destination in zip((source_service, source_timer, source_failure), files):
            local = directory / destination.name
            local.write_text(source)
            # This exclusive name may exist even if install reports a partial failure.
            installed.append(destination)
            _native(["sudo", "install", "-m", "0644", str(local), str(destination)])
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
        local.write_text(
            f"[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/touch {failure_marker}\n"
        )
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
            _reset_failed_invocation(service_name, previous_state)
            _native(["sudo", "systemctl", "start", service_name], check=expected == 0)
            assert _property(service_name, "Service", "ExecMainStatus", "i") == expected
            assert _property(service_name, "Unit", "ActiveState", "s") == (
                "inactive" if expected == 0 else "failed"
            )
            deadline = time.monotonic() + 10
            while expected != 0 and not failure_marker.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert failure_marker.exists() is (expected != 0)
            previous_state = "inactive" if expected == 0 else "failed"
            if expected != 0:
                _finish_failure_handler(failure_name, failure_marker)
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
            failure_marker.unlink(missing_ok=True)
            _reset_failed_invocation(service_name, previous_state)
            _native(["sudo", "systemctl", "start", service_name], check=False)
            assert _property(service_name, "Service", "ExecMainStatus", "i") == 75
            assert _property(service_name, "Unit", "ActiveState", "s") == "failed"
            _finish_failure_handler(failure_name, failure_marker)
            assert failure_marker.exists() and not receipt.exists()
            _native(["sudo", "systemctl", "stop", service_name])
            previous_state = _property(service_name, "Unit", "ActiveState", "s")
            assert lock.stat().st_ino == inode and not receipt.exists()
        _reset_failed_invocation(service_name, previous_state)
        _native(["sudo", "systemctl", "start", service_name], check=False)
        assert _property(service_name, "Service", "ExecMainStatus", "i") == 0
        previous_state = _property(service_name, "Unit", "ActiveState", "s")
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
            _reset_failed_invocation(service_name, previous_state)
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
            previous_state = _property(service_name, "Unit", "ActiveState", "s")
            if previous_state == "failed":
                _finish_failure_handler(failure_name, failure_marker)
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
            _reset_failed_invocation(service_name, previous_state)
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
            while (
                _property(service_name, "Unit", "ActiveState", "s") == "activating"
                and time.monotonic() < deadline
            ):
                time.sleep(0.05)
            assert _property(service_name, "Unit", "ActiveState", "s") == "inactive"
            assert _property(service_name, "Service", "Result", "s") == "success"
            _native(["sudo", "systemctl", "stop", timer_name])
            previous_state = "inactive"
            stamp.unlink(missing_ok=True)
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        cleanup_errors: list[Exception] = []
        stopped: set[str] = set()
        stop_order = sorted(
            installed, key=lambda path: {timer_name: 0, service_name: 1, failure_name: 2}[path.name]
        )
        for path in stop_order:
            try:
                _native(["sudo", "systemctl", "stop", path.name])
                stopped.add(path.name)
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        all_stopped = all(path.name in stopped for path in installed)
        for path in installed:
            if all_stopped:
                try:
                    _native(["sudo", "rm", "--", str(path)])
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
        try:
            _native(["sudo", "systemctl", "daemon-reload"])
        except Exception as cleanup_error:
            cleanup_errors.append(cleanup_error)
        if runtime.exists() and all_stopped:
            try:
                _native(["sudo", "rm", "-r", "--", str(runtime)])
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for cleanup_error in cleanup_errors:
            print("native_cleanup_failure=systemd:" + type(cleanup_error).__name__, flush=True)
        if cleanup_errors and primary_failure is None:
            raise cleanup_errors[0]


def _owned_census_records(
    result: subprocess.CompletedProcess[str],
) -> list[tuple[str, str]] | None:
    """Decode the single finite PID/COMMAND census used by all owned subjects."""
    rows = result.stdout.splitlines()
    records = [row.split() for row in rows[1:]]
    if (
        result.returncode != 0
        or len(rows) < 2
        or rows[0].split() != ["PID", "COMMAND"]
        or any(len(row) != 2 or re.fullmatch(r"[1-9][0-9]*", row[0]) is None for row in records)
        or len({row[0] for row in records}) != len(records)
    ):
        return None
    return [(row[0], row[1]) for row in records]


def _owned_task_stopped(
    cid: str,
    command: str,
    started: float,
    probe: str,
    *,
    main_identity: tuple[str, str] | None = None,
    task_identity: tuple[str, str] | None = None,
) -> bool:
    """Observe the finite owned fixture census within the original 10s stop bound."""
    main = (
        main_identity[1]
        if main_identity
        else {"amtool": "alertmanager", "promtool": "prometheus"}[command]
    )
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
        try:
            result = _native(["docker", "top", cid, "-eo", "pid,comm"], timeout=min(2, remaining))
        except subprocess.TimeoutExpired:
            observed = time.monotonic()
            reason = "census_timeout"
            break
        terminal = result.stdout
        observed = time.monotonic()
        if immediate is None:
            immediate = terminal
        records = _owned_census_records(result)
        valid = records is not None
        task_present = True
        if records is not None:
            if main_identity is not None:
                valid = (
                    task_identity is not None
                    and main_identity[0] != task_identity[0]
                    and task_identity[1] == command
                    and main_identity in records
                    and all(row in {main_identity, task_identity} for row in records)
                )
                task_present = task_identity in records
            else:
                tasks = [row[1] for row in records]
                valid = tasks.count(main) == 1 and all(task in {main, command} for task in tasks)
                task_present = command in tasks
        if not valid:
            reason = "invalid_census"
            break
        if observed > deadline:
            reason = "observation_after_deadline"
            break
        if not task_present:
            stopped = True
            reason = "stopped"
            break
        reason = "task_present"
        time.sleep(min(0.1, max(0, deadline - observed)))
    if immediate is None and reason == "no_census_within_deadline":
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
    from urllib.parse import parse_qs, urlsplit

    from scripts import verify_premium_alias_telemetry as verifier

    release = threading.Event()
    entered = threading.Event()
    scalar_seen = threading.Event()
    vector_seen = threading.Event()
    fixture_time = "2026-08-22T12:00:00Z"
    fixture_timestamp = datetime.fromisoformat(fixture_time.replace("Z", "+00:00")).timestamp()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlsplit(self.path).query)
            entered.set()
            release.wait(130)
            expression = query.get("query", [""])[0]
            if expression == "sum(up)":
                assert query == {"query": ["sum(up)"], "time": [fixture_time]}
            kind = "scalar" if expression == "time()" else "vector"
            result: object = (
                [fixture_timestamp, str(fixture_timestamp)]
                if kind == "scalar"
                else [{"metric": {}, "value": [fixture_timestamp, "2.5"]}]
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(
                    json.dumps(
                        {"status": "success", "data": {"resultType": kind, "result": result}}
                    ).encode()
                )
                (scalar_seen if kind == "scalar" else vector_seen).set()
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    query_thread: threading.Thread | None = None
    prometheus_cid = ""
    app_cid = ""
    prometheus_name = "obs2aquery" + uuid.uuid4().hex
    app_name = "obs2aqueryapp" + uuid.uuid4().hex
    attempted: list[str] = []
    unit = "obs2aquery" + uuid.uuid4().hex + ".service"
    unit_file = SYSTEMD_UNIT_DIRECTORY / unit
    primary_failure: BaseException | None = None
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 9090), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = directory / "prometheus.yml"
        config.write_text("global:\n  scrape_interval: 30s\nscrape_configs: []\n")
        failures: list[str] = []
        attempted.append(prometheus_name)
        prometheus_cid = _native(
            [
                "docker",
                "run",
                "--name",
                prometheus_name,
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
        runtime_bases = re.findall(
            r"^FROM (\S+) AS runtime-base\s*$", (ROOT / "Dockerfile").read_text(), re.MULTILINE
        )
        assert len(runtime_bases) == 1, "governed Python runtime base is unavailable"
        python_image = runtime_bases[0]
        assert re.fullmatch(r"python:[A-Za-z0-9.-]+@sha256:[0-9a-f]{64}", python_image)
        attempted.append(app_name)
        app_cid = _native(
            [
                "docker",
                "run",
                "--name",
                app_name,
                "-d",
                "--network",
                "host",
                "--add-host",
                "prometheus:127.0.0.1",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--read-only",
                "--user",
                "65532:65532",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                python_image,
                "/usr/local/bin/python",
                "-I",
                "-c",
                "import signal; signal.pause()",
            ]
        ).stdout.strip()
        assert all(re.fullmatch(r"[0-9a-f]{64}", cid) for cid in (prometheus_cid, app_cid))
        assert prometheus_cid != app_cid, "native query requires distinct actual bound subjects"
        main_records = _owned_census_records(_native(["docker", "top", app_cid, "-eo", "pid,comm"]))
        assert main_records is not None and len(main_records) == 1
        main_identity = main_records[0]
        docker = shutil.which("docker")
        assert docker is not None
        client = verifier.DockerPromtoolClient(docker=docker, compose_file=config)
        client._bound_prometheus_container_id = prometheus_cid
        client._bound_app_container_id = app_cid
        release.set()
        assert client.get_evaluation_anchor() == datetime.fromtimestamp(
            fixture_timestamp, timezone.utc
        )
        assert scalar_seen.is_set(), "actual scalar query response was not observed"
        assert client.query_scalar("sum(up)", evaluation_time=fixture_time) == 2.5
        assert vector_seen.is_set(), "actual vector query/explicit UTC response was not observed"
        release.clear()
        entered.clear()
        query_errors: list[Exception] = []

        def blocked_query() -> None:
            try:
                client.get_evaluation_anchor()
            except Exception as error:
                query_errors.append(error)

        query_thread = threading.Thread(target=blocked_query, daemon=True)
        query_thread.start()
        assert entered.wait(10), "actual bounded query never reached the fixture endpoint"
        live_records = _owned_census_records(_native(["docker", "top", app_cid, "-eo", "pid,comm"]))
        assert live_records is not None and len(live_records) == 2 and main_identity in live_records
        task_identity = next(row for row in live_records if row != main_identity)
        query_thread.join(10)
        assert (
            not query_thread.is_alive()
        ), "bounded query did not finish under its admitted deadline"
        assert len(query_errors) == 1 and isinstance(query_errors[0], verifier.VerificationError)
        print(
            "native_query_binding="
            + json.dumps(
                {
                    "prometheus_cid": prometheus_cid,
                    "app_cid": app_cid,
                    "main_identity": main_identity,
                    "relay_identity": task_identity,
                }
            ),
            flush=True,
        )
        if not _owned_task_stopped(
            app_cid,
            task_identity[1],
            time.monotonic(),
            "P02_command_timeout",
            main_identity=main_identity,
            task_identity=task_identity,
        ):
            failures.append(
                "owned query relay cleanup not proved within timeout plus10s stop bound"
            )
        release.set()
        assert _owned_task_stopped(
            app_cid,
            task_identity[1],
            time.monotonic(),
            "P02_released_response",
            main_identity=main_identity,
            task_identity=task_identity,
        ), "ordinary fixture response failed to finish task"
        release.clear()
        entered.clear()
        unit_file.write_text(
            f"[Service]\nType=oneshot\nWorkingDirectory={ROOT}\nExecStart={sys.executable} -m tests.test_notify_premium_alias_checkpoint_failure --query-container {prometheus_cid} {app_cid}\nTimeoutStartSec=10min\nTimeoutStopSec=10s\nKillMode=control-group\nRestart=no\n"
        )
        _native(["sudo", "systemctl", "daemon-reload"])
        _native(["sudo", "systemctl", "start", "--no-block", unit])
        assert entered.wait(10), "actual interrupted query relay never reached endpoint"
        live_records = _owned_census_records(_native(["docker", "top", app_cid, "-eo", "pid,comm"]))
        assert live_records is not None and len(live_records) == 2 and main_identity in live_records
        task_identity = next(row for row in live_records if row != main_identity)
        stopped_at = time.monotonic()
        _native(["sudo", "systemctl", "stop", unit])
        if not _owned_task_stopped(
            app_cid,
            task_identity[1],
            stopped_at,
            "P02_systemd_interruption",
            main_identity=main_identity,
            task_identity=task_identity,
        ):
            failures.append(
                "owned query relay cleanup not proved within interruption plus10s stop bound"
            )
        assert not failures, "P02 readiness HOLD: " + "; ".join(failures)
    except BaseException as exc:
        primary_failure = exc
        raise
    finally:
        cleanup_errors: list[Exception] = []
        release.set()
        if server is not None and thread is not None and thread.is_alive():
            try:
                server.shutdown()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if server is not None:
            try:
                server.server_close()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if thread is not None and thread.ident is not None:
            try:
                thread.join(5)
                assert not thread.is_alive(), "owned server thread did not stop"
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if unit_file.exists():
            unit_stopped = False
            try:
                _native(["sudo", "systemctl", "stop", unit])
                unit_stopped = True
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
            if unit_stopped:
                try:
                    unit_file.unlink()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            try:
                _native(["sudo", "systemctl", "daemon-reload"])
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for container_name in reversed(attempted):
            try:
                _native(["docker", "rm", "-f", container_name])
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if query_thread is not None and query_thread.ident is not None:
            try:
                query_thread.join(5)
                assert not query_thread.is_alive(), "owned query caller did not stop"
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for cleanup_error in cleanup_errors:
            print(
                "native_cleanup_failure=owned_fixture:" + type(cleanup_error).__name__, flush=True
            )
        if cleanup_errors and primary_failure is None:
            raise cleanup_errors[0]


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

    server: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    cid = ""
    compose_attempted = False
    unit = "obs2aamtool" + uuid.uuid4().hex + ".service"
    unit_file = SYSTEMD_UNIT_DIRECTORY / unit
    primary_failure: BaseException | None = None
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 9093), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = directory / "amtool-lifetime.yml"
        config.write_text("route:\n  receiver: synthetic\nreceivers:\n  - name: synthetic\n")
        config.chmod(0o444)
        compose = directory / "amtool-compose.yaml"
        compose.write_text(
            f"services:\n  alertmanager:\n    profiles: [alerting]\n    image: {ALERTMANAGER_IMAGE}\n    platform: linux/amd64\n    user: '65534:65534'\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    read_only: true\n    network_mode: host\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:19093']\n    volumes: ['{config}:/etc/alertmanager/alertmanager.yml:ro']\n"
        )
        prefix = ["docker", "compose", "-f", str(compose)]
        failures: list[str] = []
        compose_attempted = True
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
        assert _owned_task_stopped(
            cid, "amtool", time.monotonic(), "P01_released_response"
        ), "ordinary fixture response failed to finish task"
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
        cleanup_errors: list[Exception] = []
        release.set()
        if server is not None and thread is not None and thread.is_alive():
            try:
                server.shutdown()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if server is not None:
            try:
                server.server_close()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if thread is not None and thread.ident is not None:
            try:
                thread.join(5)
                assert not thread.is_alive(), "owned server thread did not stop"
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if unit_file.exists():
            unit_stopped = False
            try:
                _native(["sudo", "systemctl", "stop", unit])
                unit_stopped = True
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
            if unit_stopped:
                try:
                    unit_file.unlink()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            try:
                _native(["sudo", "systemctl", "daemon-reload"])
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cid:
            try:
                _native(["docker", "rm", "-f", cid])
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        elif compose_attempted:
            for operation in ("stop", "rm"):
                try:
                    argv = [*prefix, operation]
                    if operation == "rm":
                        argv.append("-f")
                    _native([*argv, "alertmanager"])
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
        for cleanup_error in cleanup_errors:
            print(
                "native_cleanup_failure=owned_fixture:" + type(cleanup_error).__name__, flush=True
            )
        if cleanup_errors and primary_failure is None:
            raise cleanup_errors[0]


def _native_alertmanager_render(prefix: list[str]) -> None:
    """Render current repo HTML with inert labels in the already-owned pinned AM fixture."""
    config = yaml.safe_load((ROOT / "deploy/alertmanager/alertmanager.yml").read_text("utf-8"))
    html = config["receivers"][0]["email_configs"][0]["html"]
    assert isinstance(html, str)
    rendered = _native(
        [
            *prefix,
            "exec",
            "-T",
            "alertmanager",
            "/bin/amtool",
            "--no-version-check",
            "template",
            "render",
            "--template.glob=/dev/null",
            "--template.type=html",
            "--template.text=" + html,
            "--template.data=/email-template-data.json",
        ],
        timeout=20,
    )
    _assert_alertmanager_html(rendered.stdout, *RENDER_LABELS)
    print("native_alertmanager_html_escape=pass", flush=True)


def _native_alertmanager(directory: Path) -> None:
    """Actual pinned AM, exact route timings, private synthetic TLS SMTP receiver."""
    from socketserver import StreamRequestHandler, ThreadingTCPServer

    with pytest.MonkeyPatch.context() as profile_environment:
        profile_environment.setenv("COMPOSE_PROFILES", "")
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

        server: ThreadingTCPServer | None = None
        thread: threading.Thread | None = None
        cid = ""
        compose_attempted = False
        primary_failure: BaseException | None = None
        try:
            server = Server(("127.0.0.1", 2465), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            configuration = directory / "alertmanager.yml"
            configuration.write_bytes((ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes())
            configuration.chmod(0o444)
            secret = directory / "synthetic-smtp"
            secret.write_text("synthetic-smtp")
            secret.chmod(0o444)
            template_data = directory / "email-template-data.json"
            template_data.write_text(
                json.dumps(
                    {
                        "receiver": "pulseplate-email",
                        "status": "firing",
                        "alerts": [
                            {
                                "status": "firing",
                                "labels": {},
                                "annotations": {},
                                "generatorURL": "http://synthetic-private-prometheus:9090",
                            }
                        ],
                        "groupLabels": {},
                        "commonLabels": dict(zip(("alertname", "environment"), RENDER_LABELS)),
                        "commonAnnotations": {"description": "raw-secret-sentinel"},
                        "externalURL": "http://synthetic-private-alertmanager:9093",
                    }
                ),
                encoding="utf-8",
            )
            template_data.chmod(0o444)
            compose = directory / "compose.yaml"
            compose.write_text(
                f"services:\n  alertmanager:\n    profiles: [alerting]\n    image: {ALERTMANAGER_IMAGE}\n    platform: linux/amd64\n    user: '65534:65534'\n    read_only: true\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    network_mode: host\n    extra_hosts: ['smtp.resend.com:127.0.0.1']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:9093']\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    volumes:\n      - {configuration}:/etc/alertmanager/alertmanager.yml:ro\n      - {secret}:/run/secrets/alertmanager_smtp_key:ro\n      - {cert}:/etc/ssl/certs/ca-certificates.crt:ro\n"
                f"      - {template_data}:/email-template-data.json:ro\n"
            )
            docker = shutil.which("docker")
            assert docker is not None
            prefix = ["docker", "compose", "-f", str(compose)]
            compose_attempted = True
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
                result = _native(
                    query, timeout=min(10, setup_deadline - time.monotonic()), check=False
                )
                if result.returncode == 0:
                    assert (
                        time.monotonic() <= setup_deadline
                    ), "native Alertmanager API readiness deadline exceeded"
                    assert (
                        json.loads(result.stdout) == []
                    ), "fixture has unexpected pre-event alerts"
                    break
                time.sleep(min(0.1, max(0, setup_deadline - time.monotonic())))
            else:
                raise AssertionError("native Alertmanager API readiness deadline exceeded")
            print(
                "native_alertmanager_api_ready_seconds=" + str(time.monotonic() - setup_started),
                flush=True,
            )
            _native_alertmanager_render(prefix)
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
            assert (
                len(received) == 1
            ), "actual 30s/5m/24h route did not deliver one deduplicated event"
            _assert_alertmanager_email(received[0], "PulsePlateAliasCheckpointFailed", "staging")
            print("native_alertmanager_mime_runbook=pass", flush=True)
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
            _native([*prefix, "stop", "alertmanager"])
            assert (
                json.loads(
                    _native(
                        ["docker", "inspect", "--format", "{{json .State.Running}}", cid]
                    ).stdout
                )
                is False
            )
            failed_argv = notifier._argv(
                docker,
                compose,
                "staging",
                notifier._timestamp(later),
                notifier._timestamp(later + timedelta(seconds=900)),
            )
            assert notifier._send(failed_argv) is False
            assert (
                json.loads(
                    _native(
                        ["docker", "inspect", "--format", "{{json .State.Running}}", cid]
                    ).stdout
                )
                is False
            )
            _native(["docker", "rm", cid])
            cid = ""
            assert notifier._send(failed_argv) is False
            assert _native([*prefix, "ps", "-a", "-q", "alertmanager"]).stdout.strip() == ""
            print("native_profile_off_exec=running_submit_stopped_absent_rejection", flush=True)
        except BaseException as exc:
            primary_failure = exc
            raise
        finally:
            cleanup_errors: list[Exception] = []
            if server is not None and thread is not None and thread.is_alive():
                try:
                    server.shutdown()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            if server is not None:
                try:
                    server.server_close()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            if thread is not None and thread.ident is not None:
                try:
                    thread.join(5)
                    assert not thread.is_alive(), "owned server thread did not stop"
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            if cid:
                try:
                    _native(["docker", "rm", "-f", cid])
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            elif compose_attempted:
                for operation in ("stop", "rm"):
                    try:
                        argv = [*prefix, operation]
                        if operation == "rm":
                            argv.append("-f")
                        _native([*argv, "alertmanager"])
                    except Exception as cleanup_error:
                        cleanup_errors.append(cleanup_error)
            for cleanup_error in cleanup_errors:
                print(
                    "native_cleanup_failure=owned_fixture:" + type(cleanup_error).__name__,
                    flush=True,
                )
            if cleanup_errors and primary_failure is None:
                raise cleanup_errors[0]


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
    argv = [*client._compose_prefix, "--profile", "*", "config", "--format", "json"]
    (fixture / ".env").write_text("".join(f"{key}={value}\n" for key, value in inputs.items()))
    default = _native(
        [*client._compose_prefix, "config", "--format", "json"], cwd=fixture, check=False
    )
    assert default.returncode == 0, "native default-profile configuration failed"
    assert "worker" not in json.loads(default.stdout)["services"]
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
        prefix = ["/absolute/docker", "compose", "-f", str(cwd / "docker-compose.staging.yaml")]
        if argv == [*prefix, "config", "--format", "json"]:
            assert not calls
            return subprocess.CompletedProcess(argv, 0, json.dumps({"services": {"app": {}}}), "")
        assert argv == [*prefix, "--profile", "*", "config", "--format", "json"]
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
        "PID COMMAND\n0 alertmanager\n",
        "PID COMMAND\n01 alertmanager\n",
        "PID COMMAND\n١ alertmanager\n",
        "PID COMMAND\n1 alertmanager\n1 amtool\n",
        "PID COMMAND\n1 alertmanager\n2 alertmanager\n",
        "PID COMMAND\n1 alertmanager\n2 other\n",
        "PID COMMAND\n1 alertmanager extra\n",
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
    output = "PID COMMAND\n1 " + main + "\n"
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
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 1, "PID COMMAND\n1 alertmanager\n", ""
        ),
    )
    assert not _owned_task_stopped("a" * 64, "amtool", 0, "fixture_execution_failed")
    assert json.loads(capsys.readouterr().out)["reason"] == "invalid_census"


@pytest.mark.parametrize(
    "output,observed,expected,reason",
    [
        ("PID COMMAND\n101 python\n", 1, True, "stopped"),
        ("PID COMMAND\n101 python\n202 python\n", 1, False, "task_present"),
        ("PID COMMAND\n202 python\n", 1, False, "invalid_census"),
        ("PID COMMAND\n101 python\n303 python\n", 1, False, "invalid_census"),
        ("PID COMMAND\n101 other\n", 1, False, "invalid_census"),
        ("PID COMMAND\n101 python\n202 other\n", 1, False, "invalid_census"),
        ("PID COMMAND\n101 python\n101 python\n", 1, False, "invalid_census"),
        ("PID COMMAND\n101 python\n", 11, False, "observation_after_deadline"),
    ],
)
def test_bound_python_census_uses_actual_main_and_relay_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    output: str,
    observed: int,
    expected: bool,
    reason: str,
) -> None:
    ticks = iter([0, 0, observed, 10])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, output, ""),
    )
    assert (
        _owned_task_stopped(
            "a" * 64,
            "python",
            0,
            "fixture_bound_python",
            main_identity=("101", "python"),
            task_identity=("202", "python"),
        )
        is expected
    )
    assert json.loads(capsys.readouterr().out)["reason"] == reason


def test_owned_census_timeout_is_unknown_not_absence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ticks = iter([0, 0, 11])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))

    def timed_out(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        raise subprocess.TimeoutExpired(argv, 0.005)

    monkeypatch.setattr(sys.modules[__name__], "_native", timed_out)
    assert not _owned_task_stopped("a" * 64, "amtool", 0, "fixture_census_timeout")
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["reason"] == "census_timeout" and evidence["stopped"] is False
    assert evidence["elapsed_seconds"] == 11


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
    first = "PID COMMAND\n1 " + main + "\n2 " + command + "\n"
    terminal = "PID COMMAND\n1 " + main + "\n" + ("" if terminates else "2 " + command + "\n")
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


@pytest.mark.parametrize("family", ["builtin", "legacy"])
@pytest.mark.parametrize("case", ["send", "reap", "cancel", "vanished"])
def test_checkpoint_timeout_families_preserve_cleanup_and_primary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], family: str, case: str
) -> None:
    class LegacyTimeout(Exception):
        pass

    monkeypatch.setattr(notifier.asyncio, "TimeoutError", LegacyTimeout)
    exception = TimeoutError if family == "builtin" else LegacyTimeout
    waits: list[int] = []
    kills: list[tuple[int, int]] = []

    class Process:
        pid = 123

        async def wait(self) -> int:
            waits.append(1)
            if len(waits) == 1:
                if case == "cancel":
                    raise asyncio.CancelledError
                raise exception("synthetic-secret-sentinel")
            if case in {"reap", "cancel"}:
                raise exception("synthetic-secret-sentinel")
            return -9

    async def spawn(*args: str, **kwargs: object) -> Process:
        del args, kwargs
        return Process()

    def kill(pid: int, sig: int) -> None:
        kills.append((pid, sig))
        if case == "vanished":
            raise ProcessLookupError("synthetic-secret-sentinel")

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", kill)
    if case == "cancel":
        with pytest.raises(asyncio.CancelledError):
            notifier._send(["/absolute/docker"])
    elif case == "reap":
        with pytest.raises(OSError, match="notification_cleanup_incomplete"):
            notifier._send(["/absolute/docker"])
    else:
        assert notifier._send(["/absolute/docker"]) is False
    assert waits == [1, 1] and kills == [(123, signal.SIGKILL)]
    assert capsys.readouterr().out == (notifier.ERROR + "\n" if case == "cancel" else "")


@pytest.mark.parametrize("state", ["inactive", "failed"])
@pytest.mark.parametrize("reset_error", [False, True])
def test_checkpoint_failed_reset_requires_positive_typed_state(
    monkeypatch: pytest.MonkeyPatch, state: str, reset_error: bool
) -> None:
    calls: list[object] = []

    def property_value(unit: str, interface: str, name: str, signature: str) -> object:
        assert (
            state == "failed"
        ), "inactive first/success invocation must not query an unloaded unit"
        calls.append((unit, interface, name, signature))
        return "failed" if name == "ActiveState" else "exit-code"

    def native(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if reset_error:
            raise RuntimeError("synthetic reset failure")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_property", property_value)
    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    if state == "failed" and reset_error:
        with pytest.raises(RuntimeError, match="synthetic reset failure"):
            _reset_failed_invocation("owned.service", state)
    else:
        _reset_failed_invocation("owned.service", state)
    assert len(calls) == (3 if state == "failed" else 0)


def test_checkpoint_failed_reset_rejects_inconsistent_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys.modules[__name__],
        "_property",
        lambda unit, interface, name, signature: "failed" if name == "ActiveState" else "success",
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: pytest.fail("invalid reset reached native command"),
    )
    with pytest.raises(AssertionError):
        _reset_failed_invocation("owned.service", "failed")


@pytest.mark.parametrize("stop_error", [False, True])
def test_checkpoint_partial_unit_setup_preserves_primary_and_safe_owned_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stop_error: bool,
) -> None:
    units = tmp_path / "units"
    units.mkdir()
    monkeypatch.setattr(sys.modules[__name__], "SYSTEMD_UNIT_DIRECTORY", units)
    calls: list[list[str]] = []
    installed: list[Path] = []

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(argv)
        if "install" in argv:
            target = Path(argv[-1])
            target.write_text("owned scratch unit")
            installed.append(target)
            if len(installed) == 2:
                raise RuntimeError("synthetic partial install failure")
        elif "stop" in argv and stop_error:
            raise OSError("synthetic stop failure")
        elif "rm" in argv:
            Path(argv[-1]).unlink()
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    with pytest.raises(RuntimeError, match="synthetic partial install failure"):
        _native_systemd(tmp_path)
    stops = [argv for argv in calls if "stop" in argv]
    assert len(stops) == 2 and "daemon-reload" in calls[-1]
    assert all(path.exists() is stop_error for path in installed)
    assert not any("reset-failed" in argv for argv in calls)
    assert "synthetic stop failure" not in capsys.readouterr().out


@pytest.mark.parametrize("fixture", ["query", "amtool"])
@pytest.mark.parametrize("shutdown_error", [False, True])
def test_checkpoint_partial_server_setup_attempts_independent_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fixture: str,
    shutdown_error: bool,
) -> None:
    calls: list[str] = []

    class Server:
        daemon_threads = False

        def __init__(self, *args: object) -> None:
            del args
            calls.append("acquire")

        def serve_forever(self) -> None:
            return None

        def shutdown(self) -> None:
            calls.append("shutdown")
            if shutdown_error:
                raise OSError("synthetic secondary shutdown")

        def server_close(self) -> None:
            calls.append("close")

    class Thread:
        ident: int | None = None
        running = False

        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def start(self) -> None:
            self.ident = 1
            self.running = True
            calls.append("start")

        def is_alive(self) -> bool:
            return self.running

        def join(self, timeout: float) -> None:
            assert timeout == 5
            calls.append("join")
            self.running = False

    monkeypatch.setattr(sys.modules[__name__], "ThreadingHTTPServer", Server)
    monkeypatch.setattr(threading, "Thread", Thread)
    monkeypatch.setattr(sys.modules[__name__], "SYSTEMD_UNIT_DIRECTORY", tmp_path)

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        if "run" in argv or "up" in argv:
            calls.append("setup-error")
            raise RuntimeError("synthetic primary setup")
        calls.append("owned-release:" + ("rm" if "rm" in argv else "stop"))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    with pytest.raises(RuntimeError, match="synthetic primary setup"):
        (_native_query_lifetime if fixture == "query" else _native_amtool_lifetime)(tmp_path)
    assert calls[:3] == ["acquire", "start", "setup-error"]
    assert "shutdown" in calls and "close" in calls and "join" in calls
    assert any(call.startswith("owned-release:") for call in calls)
    assert "synthetic secondary shutdown" not in capsys.readouterr().out


@pytest.mark.parametrize("fixture", ["query", "amtool"])
@pytest.mark.parametrize("fault", ["shutdown", "container"])
def test_checkpoint_cleanup_failure_without_primary_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture: str, fault: str
) -> None:
    from scripts import verify_premium_alias_telemetry as verifier

    released: list[str] = []

    class Event:
        def set(self) -> None:
            return None

        def clear(self) -> None:
            return None

        def is_set(self) -> bool:
            return True

        def wait(self, timeout: float) -> bool:
            del timeout
            return True

    class Server:
        daemon_threads = True

        def __init__(self, *args: object) -> None:
            del args

        def serve_forever(self) -> None:
            return None

        def shutdown(self) -> None:
            released.append("shutdown")
            if fault == "shutdown":
                raise OSError("synthetic cleanup-only failure")

        def server_close(self) -> None:
            released.append("close")

    class Thread:
        ident: int | None = None
        running = False

        def __init__(self, **kwargs: object) -> None:
            self.target = kwargs["target"]
            assert callable(self.target)

        def start(self) -> None:
            self.ident = 1
            self.running = True
            self.target()

        def is_alive(self) -> bool:
            return self.running

        def join(self, timeout: float) -> None:
            assert timeout in (5, 10)
            released.append("join")
            self.running = False

    monkeypatch.setattr(sys.modules[__name__], "ThreadingHTTPServer", Server)
    monkeypatch.setattr(threading, "Thread", Thread)
    monkeypatch.setattr(threading, "Event", Event)
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)
    monkeypatch.setattr(sys.modules[__name__], "SYSTEMD_UNIT_DIRECTORY", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "_owned_task_stopped", lambda *args, **kwargs: True)
    sends = iter([True, False])
    monkeypatch.setattr(notifier, "_send", lambda argv: next(sends))
    queries = 0

    def query(
        self: object,
        operation: str,
        *,
        expression: str | None = None,
        evaluation_time: str | None = None,
    ) -> verifier._CommandResult:
        nonlocal queries
        del self, operation, evaluation_time
        queries += 1
        if queries == 3:
            raise verifier.VerificationError("docker_timeout")
        timestamp = datetime(2026, 8, 22, 12, tzinfo=timezone.utc).timestamp()
        scalar = expression == "time()"
        payload = {
            "status": "success",
            "data": {
                "resultType": "scalar" if scalar else "vector",
                "result": (
                    [timestamp, str(timestamp)]
                    if scalar
                    else [{"metric": {}, "value": [timestamp, "2.5"]}]
                ),
            },
        }
        return verifier._CommandResult(0, json.dumps(payload).encode(), b"")

    monkeypatch.setattr(verifier.DockerPromtoolClient, "_run_prometheus_http", query)

    runs = 0
    tops = 0

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal runs, tops
        del kwargs
        if "rm" in argv:
            released.append("container")
            if fault == "container":
                raise OSError("synthetic cleanup-only failure")
        stdout = ""
        if "run" in argv:
            runs += 1
            stdout = ("f" if runs == 1 else "e") * 64
        elif "ps" in argv:
            stdout = "f" * 64
        elif "top" in argv:
            tops += 1
            stdout = "PID COMMAND\n101 python\n"
            if tops > 1:
                stdout += "202 python\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    with pytest.raises(OSError, match="synthetic cleanup-only failure"):
        (_native_query_lifetime if fixture == "query" else _native_amtool_lifetime)(tmp_path)
    assert all(operation in released for operation in ("shutdown", "close", "join", "container"))

    assert released.count("container") == (2 if fixture == "query" else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--query-container", nargs=2, metavar=("PROMETHEUS_CID", "APP_CID"))
    parser.add_argument("--native-fixture")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if args.native:
        native_main()
    elif args.query_container:
        from scripts import verify_premium_alias_telemetry as verifier

        prometheus_cid, app_cid = args.query_container
        assert all(re.fullmatch(r"[0-9a-f]{64}", cid) for cid in (prometheus_cid, app_cid))
        assert prometheus_cid != app_cid
        docker = shutil.which("docker")
        assert docker is not None
        client = verifier.DockerPromtoolClient(docker=docker, compose_file=Path("unused.yaml"))
        client._bound_prometheus_container_id = prometheus_cid
        client._bound_app_container_id = app_cid
        client.get_evaluation_anchor()
    elif args.native_fixture and args.directory:
        raise SystemExit(_native_checkpoint_fixture(args.native_fixture, args.directory))
    else:
        parser.error("explicit native mode required")
