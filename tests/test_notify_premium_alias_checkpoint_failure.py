"""Deterministic notifier checks and explicitly selected native Linux controls."""

from __future__ import annotations

import argparse
import asyncio
import base64
import errno
import gzip
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import signal
import socket
import ssl
import stat
import subprocess
import sys
import tarfile
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
from urllib.request import ProxyHandler, Request, build_opener
from collections.abc import Callable

import pytest
import yaml

from scripts.ci import prometheus_source_image as prometheus_image
from scripts.ops import notify_premium_alias_checkpoint_failure as notifier

ROOT = Path(__file__).resolve().parents[1]
ALERTMANAGER_IMAGE = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:bc6c847d25e48a8bcddfd8fef0aec25b6ac890346b4bfe6dea3d2d82cd0dc3b9"
# Frozen native UI oracle from accepted C10; ordinary checks do not depend on artifact expiry.
_ACCEPTED_AM_UI = {
    ".build_stamp": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "assets/fontawesome-webfont-B-jkhYfk.woff2": "2adefcbc041e7d18fcf2d417879dc5a09997aa64d675b7a3c4b6ce33da13f3fe",
    "assets/fontawesome-webfont-CDK5bt4p.woff": "ba0c59deb5450f5cb41b3f93609ee2d0d995415877ddfa223e8a8a7533474f07",
    "assets/fontawesome-webfont-CQDK8MU3.ttf.br": "8048e9ede4a9dd536e8cca75e8b2340f2a055722aef030caa417c36f32cd9b5a",
    "assets/fontawesome-webfont-CQDK8MU3.ttf.gz": "7c613ddd2cde1e1298d41aae563fd71bcb886773df60bca980a13d89988f4d4b",
    "assets/fontawesome-webfont-D13rzr4g.svg.br": "c2df316d94b864d726fbf995ab04b5096e33669f8d48ebc345db50023f4e5b75",
    "assets/fontawesome-webfont-D13rzr4g.svg.gz": "64ad34590af0fb6b10b587e156e0935c0c6ab6fbd8b13ceba233ec9432dcf2e4",
    "assets/fontawesome-webfont-G5YE5S7X.eot.br": "dd9a61283fd3a0f543f95c9778e31775e10160ba567c4f0abcbe4b5d233a049c",
    "assets/fontawesome-webfont-G5YE5S7X.eot.gz": "5e6b26dbf1f3c59d60ac9731778d1dc0826b9001b8fd262cb477dc08b61832f2",
    "assets/index-OLfEAnkS.css.br": "61866ae189af1a140fe04ad24de882e010ac28fce4458a5c45072371d862ce9f",
    "assets/index-OLfEAnkS.css.gz": "c2df3900c65ec13f4a6d62bff90200da87aa2c4b0cf3856835478197e3004b22",
    "assets/index-aNRKuvMz.js.br": "71fbfb3fbf1810902e546e6dd1436eea9149e7b330b70dc99cebde94a5ff0501",
    "assets/index-aNRKuvMz.js.gz": "be05a4f9d5eaf190f27bf5b268c311103281b8cb32a54caa918807ab00a43a8f",
    "favicon.ico.br": "b3761d089558180bb068354cb7f2f72aa055d4a442b0362820021ae6b7c93cd5",
    "favicon.ico.gz": "0449fc08a09431cb4d78805a820a0a121803e08a33389ba83a12206664799bfb",
    "index.html.br": "d5c8902b247bb34a39cadc6538e5bf04416b52a1a26f44cdad36e58e8c080757",
    "index.html.gz": "cda9f8f59ab3194a9e16416887800e7f6d99bb69e167e5db9f3963fd91b1257d",
}
_ACCEPTED_AM_BINARIES = {
    "alertmanager": "08778bcb751b4ccdf1727701cb5af5cdfaae3f0cc122d697a49792a987c56f6b",
    "amtool": "5cfcb4a40897f2095339284989b563e144bc8ed2e827493e47cb9083202c89b4",
}

SYSTEMD_UNIT_DIRECTORY = Path("/run/systemd/system")
_AM_NATIVE_DOCKER_CONFIG: Path | None = None
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


def _clock(monkeypatch: pytest.MonkeyPatch, *, stub_manifest: bool = True) -> Clock:
    if stub_manifest:
        monkeypatch.setattr(notifier, "_compose_environment", lambda path: {})
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

    def send(argv: list[str], env: dict[str, str]) -> bool:
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
        str(Path("compose.yaml").absolute()),
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

    def send(argv: list[str], env: dict[str, str]) -> bool:
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

    def send(argv: list[str], env: dict[str, str]) -> bool:
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
    monkeypatch.setattr(notifier, "_send", lambda argv, env: next(results))
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


@pytest.mark.parametrize("child_env", [None, {"PROMETHEUS_RUNTIME_REF": "synthetic-reference"}])
@pytest.mark.parametrize("failure", ["success", "spawn", "exit", "timeout", "interrupt"])
def test_native_command_channels_discard_raw_sentinel(
    monkeypatch: pytest.MonkeyPatch, failure: str, child_env: dict[str, str] | None
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
            "env": child_env,
        }
        if failure == "spawn":
            raise OSError("secret-sentinel")
        return Process()

    monkeypatch.setattr(notifier.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(notifier.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    if failure == "interrupt":
        with pytest.raises(asyncio.CancelledError):
            notifier._send(["/absolute/docker"], child_env)
    else:
        assert notifier._send(["/absolute/docker"], child_env) is (failure == "success")
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
    argv: list[str],
    *,
    timeout: float = 30,
    check: bool = True,
    cwd: Path | None = None,
    binary: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded secret-free fixture child and retain its actual exit and diagnostics."""
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
    if _AM_NATIVE_DOCKER_CONFIG is not None:
        environment["DOCKER_CONFIG"] = str(_AM_NATIVE_DOCKER_CONFIG)
    try:
        result = subprocess.run(
            [resolved, *argv[1:]],
            env=environment,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=not binary,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        if _AM_NATIVE_DOCKER_CONFIG is not None:
            print(
                json.dumps(
                    {
                        "AM_native_argv": [resolved, *argv[1:]],
                        "exit": None,
                        "failure": "TimeoutExpired",
                        "stdout_partial_base64": base64.b64encode(
                            (error.stdout or b"")[: 1024 * 1024]
                        ).decode("ascii"),
                        "stderr_partial_base64": base64.b64encode(
                            (error.stderr or b"")[: 1024 * 1024]
                        ).decode("ascii"),
                    }
                ),
                flush=True,
            )
        raise
    assert len(result.stdout) + len(result.stderr) <= 1024 * 1024
    if binary:
        result = subprocess.CompletedProcess(
            result.args,
            result.returncode,
            base64.b64encode(result.stdout).decode("ascii"),
            result.stderr.decode("utf-8", errors="replace"),
        )
    if _AM_NATIVE_DOCKER_CONFIG is not None:
        print(
            json.dumps(
                {
                    "AM_native_argv": result.args,
                    "environment": environment,
                    "exit": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            ),
            flush=True,
        )
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


def _native_query_lifetime(directory: Path, prometheus_image_id: str) -> None:
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
                "--pull",
                "never",
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
                prometheus_image_id,
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


def _amtool_fixture_context(compose: Path, config: Path, expected: str | None = None) -> str:
    """Bind the generated sender's regular Compose file and same empty private config."""
    directory = compose.parent
    assert compose.name == "amtool-compose.yaml" and config == directory / "empty-docker-config"
    assert re.fullmatch(r"pulseplate-am-only-native-[a-z0-9_]{8}", directory.name)
    assert all(
        path.is_absolute()
        and path == path.resolve()
        and not path.is_symlink()
        and re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path)) is not None
        and ".." not in path.parts
        for path in (directory, compose, config)
    ), "AM sender paths must be canonical owned data"
    parent_info, compose_info, config_info = (path.lstat() for path in (directory, compose, config))
    assert (
        stat.S_ISDIR(parent_info.st_mode)
        and stat.S_IMODE(parent_info.st_mode) == 0o700
        and stat.S_ISREG(compose_info.st_mode)
        and stat.S_IMODE(compose_info.st_mode) == 0o600
        and compose_info.st_nlink == 1
        and stat.S_ISDIR(config_info.st_mode)
        and stat.S_IMODE(config_info.st_mode) == 0o700
        and parent_info.st_uid == compose_info.st_uid == config_info.st_uid
        and not list(config.iterdir())
    ), "AM sender requires the original owner's empty private context"
    identity = ":".join(
        str(value)
        for value in (
            parent_info.st_uid,
            parent_info.st_dev,
            parent_info.st_ino,
            compose_info.st_dev,
            compose_info.st_ino,
            config_info.st_dev,
            config_info.st_ino,
        )
    )
    if expected is None:
        assert parent_info.st_uid == os.getuid(), "AM parent must own the sender context"
    else:
        assert (
            re.fullmatch(r"[0-9]+(?::[0-9]+){6}", expected) and identity == expected
        ), "AM sender context identity changed"
    return identity


def _native_am_send(argv: list[str]) -> bool:
    """Give AM parent sends the same private Docker identity as its native owner."""
    config = _AM_NATIVE_DOCKER_CONFIG
    if config is None:
        return notifier._send(argv)
    info = config.lstat()
    assert (
        config.is_absolute()
        and config == config.resolve()
        and not config.is_symlink()
        and config.name == "empty-docker-config"
        and stat.S_ISDIR(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o700
        and info.st_uid == config.parent.stat().st_uid
        and not list(config.iterdir())
    ), "AM send private config changed"
    assert argv and os.path.isabs(argv[0]) and argv[1:2] == ["compose"]
    return notifier._send(
        [argv[0], "--config", str(config), *argv[1:]],
        {
            "PATH": os.defpath,
            "LANG": "C",
            "HOME": str(config.parent),
            "COMPOSE_PROFILES": "",
            "DOCKER_CONFIG": str(config),
        },
    )


def _amtool_fixture_send(compose: Path, config: Path, identity: str) -> int:
    """Recheck the parent-owned identity in the fresh root sender before Docker."""
    _amtool_fixture_context(compose, config, identity)
    docker = shutil.which("docker")
    assert docker is not None and os.path.isabs(docker)
    start = datetime.now(timezone.utc)
    argv = notifier._argv(
        docker,
        compose,
        "staging",
        notifier._timestamp(start),
        notifier._timestamp(start + timedelta(seconds=900)),
    )
    with pytest.MonkeyPatch.context() as runtime:
        runtime.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", config)
        return 0 if _native_am_send(argv) else 1


def _amtool_owned_unit_file(path: Path, expected: bytes) -> None:
    """An attempted install alone never authorizes deleting foreign or partial bytes."""
    info = path.lstat()
    assert (
        not path.is_symlink()
        and stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == 0
        and stat.S_IMODE(info.st_mode) == 0o644
        and path.read_bytes() == expected
    ), "AM installed unit ownership or bytes unknown"


def _amtool_owned_unit(
    unit: str,
    path: Path,
    expected: bytes,
    command: list[str],
    *,
    before_start: bool = False,
) -> None:
    """Bind the exact loaded scratch unit through the incumbent typed systemd owner."""
    _amtool_owned_unit_file(path, expected)
    systemctl = shutil.which("systemctl")
    assert systemctl is not None and os.path.isabs(systemctl)
    loaded = _native([systemctl, "show", unit, "--property=LoadState", "--value"])
    assert loaded.stdout == "loaded\n", "AM unit load state unknown"
    assert _property(unit, "Unit", "FragmentPath", "s") == str(path)
    assert _property(unit, "Unit", "DropInPaths", "as") == []
    assert _property(unit, "Unit", "NeedDaemonReload", "b") is False
    actual = _property(unit, "Service", "ExecStart", "a(sasbttttuii)")
    assert isinstance(actual, list) and len(actual) == 1
    assert actual[0][0] == command[0] and actual[0][1] == command and actual[0][2] is False
    for name, signature, value in (
        ("WorkingDirectory", "s", str(ROOT)),
        ("User", "s", "root"),
        ("Environment", "as", []),
        ("EnvironmentFiles", "a(sb)", []),
        ("Type", "s", "oneshot"),
        ("TimeoutStartUSec", "t", 960_000_000),
        ("TimeoutStopUSec", "t", 10_000_000),
        ("KillMode", "s", "control-group"),
        ("Restart", "s", "no"),
    ):
        assert _property(unit, "Service", name, signature) == value
    if before_start:
        assert _property(unit, "Unit", "ActiveState", "s") == "inactive"
        assert _property(unit, "Unit", "SubState", "s") == "dead"
        for name in ("MainPID", "ControlPID"):
            value = _property(unit, "Service", name, "u")
            assert type(value) is int and value == 0, "AM unit already has a process"


def _native_am_failure(label: str, error: BaseException) -> None:
    """Project finite primary metadata; exception prose and custom names stay private."""
    try:
        assert label in {"amtool_lifetime", "alertmanager", "owned_fixture", "timer_cleanup"}
        known = (
            AssertionError,
            OSError,
            PermissionError,
            FileNotFoundError,
            RuntimeError,
            TimeoutError,
            ValueError,
            TypeError,
            subprocess.TimeoutExpired,
        )
        record: dict[str, object] = {
            "native_AM_fixture_failure": label,
            "type": type(error).__name__ if type(error) in known else "unknown_exception",
            "message": "withheld",
        }
        if (
            isinstance(error, OSError)
            and type(error.errno) is int
            and error.errno in errno.errorcode
        ):
            record.update(
                errno=error.errno,
                errno_name=errno.errorcode[error.errno],
                errno_description=os.strerror(error.errno),
            )
        frames = []
        current = error.__traceback__
        visited = 0
        while current is not None and visited < 32 and len(frames) < 16:
            visited += 1
            code = current.tb_frame.f_code
            if code.co_filename == __file__ and code.co_name in {
                "_native",
                "_native_amtool_lifetime",
                "_amtool_owned_unit_file",
                "_amtool_owned_unit",
                "_native_alertmanager",
                "_native_am_send",
                "_amtool_fixture_context",
                "_amtool_fixture_send",
                "native_alertmanager_main",
            }:
                frames.append(
                    {
                        "file": "tests/test_notify_premium_alias_checkpoint_failure.py",
                        "line": current.tb_lineno,
                        "function": code.co_name,
                    }
                )
            current = current.tb_next
        record["frames"] = frames
        print(json.dumps(record), flush=True)
    except Exception:
        # Failure was recorded by the owner before this optional projection.
        try:
            print("native_AM_failure_metadata_unavailable", flush=True)
        except Exception:
            return


def _native_amtool_lifetime(
    directory: Path, image: str = ALERTMANAGER_IMAGE, *, independent: bool = False
) -> None:
    """Observe bounded amtool cleanup, with one narrowly installed owned unit."""
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
    staged_unit = directory / unit
    unit_attempted = False
    unit_start_attempted = False
    unit_bytes = b""
    primary_failure: BaseException | None = None
    try:
        assert not unit_file.exists() and not unit_file.is_symlink(), "AM unit already exists"
        server = ThreadingHTTPServer(("127.0.0.1", 9093), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = directory / "amtool-lifetime.yml"
        config.write_text("route:\n  receiver: synthetic\nreceivers:\n  - name: synthetic\n")
        config.chmod(0o444)
        compose = directory / "amtool-compose.yaml"
        compose.write_text(
            f"services:\n  alertmanager:\n    profiles: [alerting]\n    image: {image}\n    pull_policy: never\n    platform: linux/amd64\n    user: '65534:65534'\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    read_only: true\n    network_mode: host\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:19093']\n    volumes: ['{config}:/etc/alertmanager/alertmanager.yml:ro']\n"
        )
        compose.chmod(0o600)
        if not independent:
            selected_manifest = directory / "prometheus/image-manifest.json"
            selected_manifest.parent.mkdir(exist_ok=True)
            selected_manifest.write_bytes(
                (ROOT / "deploy/prometheus/image-manifest.json").read_bytes()
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
        assert _native_am_send(argv)
        release.clear()
        entered.clear()
        assert _native_am_send(argv) is False
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
        sender = [
            sys.executable,
            "-s",
            "-B",
            "-m",
            "scripts.ops.notify_premium_alias_checkpoint_failure",
            "--compose-file",
            str(compose),
            "--environment",
            "staging",
        ]
        if independent:
            assert _AM_NATIVE_DOCKER_CONFIG is not None
            identity = _amtool_fixture_context(compose, _AM_NATIVE_DOCKER_CONFIG)
            sender = [
                sys.executable,
                "-s",
                "-B",
                "-m",
                "tests.test_notify_premium_alias_checkpoint_failure",
                "--amtool-fixture-send",
                str(compose),
                "--amtool-fixture-config",
                str(_AM_NATIVE_DOCKER_CONFIG),
                "--amtool-fixture-context",
                identity,
            ]
        assert Path(sys.executable).is_absolute() and Path(sys.executable).is_file()
        environment = shutil.which("env")
        sudo, install, remove, systemctl = (
            shutil.which(name) for name in ("sudo", "install", "rm", "systemctl")
        )
        assert all(
            value is not None and os.path.isabs(value)
            for value in (environment, sudo, install, remove, systemctl)
        )
        command = [str(environment), "-i", "PATH=" + os.defpath, "LANG=C", *sender]
        assert all(re.fullmatch(r"[A-Za-z0-9_./:=,-]+", token) for token in [str(ROOT), *command])
        unit_bytes = (
            f"[Service]\nType=oneshot\nUser=root\nWorkingDirectory={ROOT}\nExecStart={' '.join(command)}\nTimeoutStartSec=16min\nTimeoutStopSec=10s\nKillMode=control-group\nRestart=no\n"
        ).encode()
        with staged_unit.open("xb") as stream:
            stream.write(unit_bytes)
        staged_unit.chmod(0o600)
        unit_attempted = True
        _native(
            [str(sudo), "-n", str(install), "-m", "0644", "--", str(staged_unit), str(unit_file)]
        )
        _native([str(sudo), "-n", str(systemctl), "daemon-reload"])
        _amtool_owned_unit(unit, unit_file, unit_bytes, command, before_start=True)
        unit_start_attempted = True
        _native([str(sudo), "-n", str(systemctl), "start", "--no-block", unit])
        assert entered.wait(10)
        stopped_at = time.monotonic()
        _native([str(sudo), "-n", str(systemctl), "stop", unit])
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
        if unit_attempted:
            unit_stopped = False
            try:
                _amtool_owned_unit_file(unit_file, unit_bytes)
                if unit_start_attempted:
                    _amtool_owned_unit(unit, unit_file, unit_bytes, command)
                    _native([str(sudo), "-n", str(systemctl), "stop", unit])
                unit_stopped = True
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
            if unit_stopped:
                try:
                    _amtool_owned_unit_file(unit_file, unit_bytes)
                    _native([str(sudo), "-n", str(remove), "--", str(unit_file)])
                    assert not unit_file.exists() and not unit_file.is_symlink()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            try:
                _native([str(sudo), "-n", str(systemctl), "daemon-reload"])
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
            _native_am_failure("owned_fixture", cleanup_error)
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


def _native_alertmanager(
    directory: Path, image: str = ALERTMANAGER_IMAGE, *, tls_failure: str | None = None
) -> None:
    """Actual pinned AM, exact route timings, private synthetic TLS SMTP receiver."""
    from socketserver import StreamRequestHandler, ThreadingTCPServer

    with pytest.MonkeyPatch.context() as profile_environment:
        profile_environment.setenv("COMPOSE_PROFILES", "")
        received: list[bytes] = []
        smtp_commands: list[bytes] = []
        assert tls_failure in (None, "untrusted", "hostname", "plaintext")
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
                "subjectAltName=DNS:"
                + ("wrong.invalid" if tls_failure == "hostname" else "smtp.resend.com"),
            ],
            timeout=30,
        )
        cert.chmod(0o444)
        key.chmod(0o600)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, key)
        trusted_ca = cert
        if tls_failure == "untrusted":
            trusted_ca = directory / "unrelated-ca.crt"
            _native(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(directory / "unrelated-ca.key"),
                    "-out",
                    str(trusted_ca),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=unrelated-fixture-CA",
                ],
                timeout=30,
            )
            trusted_ca.chmod(0o444)

        class Handler(StreamRequestHandler):
            def handle(self) -> None:
                """Receive bounded synthetic SMTP, retaining AUTH/DATA absence for TLS negatives."""
                self.wfile.write(b"220 synthetic fixture\r\n")
                while True:
                    line = self.rfile.readline(4097)
                    if not line or len(line) > 4096:
                        return
                    command = line.split(b" ", 1)[0].strip().upper()
                    smtp_commands.append(command)
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
                """Wrap implicit TLS except the deliberately plaintext rejection control."""
                sock, address = super().get_request()
                sock.settimeout(10)
                return (
                    sock
                    if tls_failure == "plaintext"
                    else context.wrap_socket(sock, server_side=True)
                ), address

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
                f"services:\n  alertmanager:\n    profiles: [alerting]\n    image: {image}\n    pull_policy: never\n    platform: linux/amd64\n    user: '65534:65534'\n    read_only: true\n    cap_drop: [ALL]\n    security_opt: ['no-new-privileges:true']\n    network_mode: host\n    extra_hosts: ['smtp.resend.com:127.0.0.1']\n    command: ['--config.file=/etc/alertmanager/alertmanager.yml', '--storage.path=/alertmanager', '--cluster.listen-address=', '--web.listen-address=127.0.0.1:9093']\n    tmpfs: ['/alertmanager:uid=65534,gid=65534,mode=0700,size=16m']\n    volumes:\n      - {configuration}:/etc/alertmanager/alertmanager.yml:ro\n      - {secret}:/run/secrets/alertmanager_smtp_key:ro\n      - {trusted_ca}:/etc/ssl/certs/ca-certificates.crt:ro\n"
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
            assert _native_am_send(argv)
            first = json.loads(_native(query).stdout)
            assert len(first) == 1 and first[0]["labels"] == {
                "alertname": "PulsePlateAliasCheckpointFailed",
                "environment": "staging",
                "alias": "all",
                "severity": "warning",
            }
            if tls_failure is not None:
                patterns = {
                    "untrusted": r"x509:.*(?:unknown authority|untrusted)",
                    "hostname": r"x509:.*(?:not smtp\.resend\.com|not valid for|cannot validate)",
                    "plaintext": r"tls:.*(?:first record|handshake)|server gave HTTP response to HTTPS client",
                }
                rejection_deadline = time.monotonic() + 60
                while time.monotonic() < rejection_deadline:
                    logs = _native(["docker", "logs", cid], timeout=10)
                    if re.search(
                        patterns[tls_failure], logs.stdout + logs.stderr, flags=re.IGNORECASE
                    ):
                        assert (
                            not received
                            and b"AUTH" not in smtp_commands
                            and b"DATA" not in smtp_commands
                        )
                        print(
                            "native_AM_SMTP_TLS_rejection=" + tls_failure + "; AUTH=0; DATA=0",
                            flush=True,
                        )
                        return
                    time.sleep(0.1)
                raise AssertionError(
                    "native SMTP negative lacked its actual TLS/x509 cause: " + tls_failure
                )
            fingerprint = first[0]["fingerprint"]
            epoch = time.monotonic()
            for slot in range(1, 15):
                time.sleep(max(0, epoch + slot * 60 - time.monotonic()))
                assert _native_am_send(argv)
                assert json.loads(_native(query).stdout)[0]["fingerprint"] == fingerprint
            assert (
                len(received) == 1
            ), "actual 30s/5m/24h route did not deliver one deduplicated event"
            _assert_alertmanager_email(received[0], "PulsePlateAliasCheckpointFailed", "staging")
            print("native_alertmanager_mime_runbook=pass", flush=True)
            time.sleep(max(0, epoch + 905 - time.monotonic()))
            assert json.loads(_native(query).stdout) == [], "bounded event did not expire"
            later = datetime.now(timezone.utc)
            assert _native_am_send(
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
            assert _native_am_send(failed_argv) is False
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
            assert _native_am_send(failed_argv) is False
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
                _native_am_failure("owned_fixture", cleanup_error)
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
    prometheus = "ghcr.io/pulseplate/prometheus-fixture@sha256:" + "3" * 64
    inputs = {
        "POSTGRES_USER": "synthetic_user",
        "POSTGRES_DB": "synthetic_db",
        "STAGING_DOMAIN": "checkpoint.invalid",
        "STAGING_ENV_FILE": str(application_env),
        "STAGING_IMAGE_REF": backend,
        "STAGING_CADDY_IMAGE_REF": caddy,
        "PROMETHEUS_RUNTIME_REF": prometheus,
    }
    docker = shutil.which("docker")
    assert docker is not None and os.path.isabs(docker), "native Compose binary unavailable"
    client = verifier.DockerPromtoolClient(docker=docker, compose_file=compose)
    argv = [*client._compose_prefix, "--profile", "*", "config", "--format", "json"]
    (fixture / ".env").write_text("".join(f"{key}={value}\n" for key, value in inputs.items()))
    default = _native(
        [*client._compose_prefix, "config", "--format", "json"], cwd=fixture, check=False
    )
    assert default.returncode == 0, (
        "native default-profile configuration failed: " + default.stderr[:2048]
    )
    assert "worker" not in json.loads(default.stdout)["services"]
    for missing in (None, "STAGING_IMAGE_REF", "STAGING_CADDY_IMAGE_REF", "PROMETHEUS_RUNTIME_REF"):
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
        assert (
            services["prometheus"]["image"] == prometheus
        ), "native Prometheus image binding differs"
        print("native_compose_configuration_positive=pass", flush=True)


def _native_amtool_candidate(
    image: str,
    argv: list[str],
    *,
    mounts: list[str] | None = None,
    check: bool = True,
    network: str = "host",
) -> subprocess.CompletedProcess[str]:
    """Observe actual amtool terminal state and remove only its bound owned container."""
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", image) and network in ("host", "none")
    token = uuid.uuid4().hex
    name = "pulseplate-amtool-native-" + token
    cid = ""
    primary: BaseException | None = None
    try:
        create = [
            "docker",
            "create",
            "--name",
            name,
            "--label",
            "pulseplate.amtool-native=" + token,
            "--pull=never",
            "--network=" + network,
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--entrypoint=/usr/bin/amtool",
        ]
        for mount in mounts or []:
            create += ["--mount", mount]
        cid = _native([*create, image, *argv]).stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{64}", cid)
        attached = _native(["docker", "start", "--attach", cid], timeout=30, check=False)
        waited = _native(["docker", "wait", cid], timeout=10)
        observed = json.loads(_native(["docker", "inspect", "--format", "{{json .}}", cid]).stdout)
        state = observed["State"]
        assert (
            observed["Id"] == cid and observed["Name"] == "/" + name and observed["Image"] == image
        )
        assert observed["Config"]["Labels"]["pulseplate.amtool-native"] == token
        assert (
            state["Status"] == "exited"
            and all(state[k] is False for k in ("Running", "Restarting", "Dead", "OOMKilled"))
            and state["Error"] == ""
        )
        assert type(state["ExitCode"]) is int and waited.stdout == str(state["ExitCode"]) + "\n"
        assert attached.returncode in (0, state["ExitCode"])
        if check:
            assert state["ExitCode"] == 0, attached.stdout + attached.stderr
        return subprocess.CompletedProcess(
            attached.args, state["ExitCode"], attached.stdout, attached.stderr
        )
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            ids = _native(
                [
                    "docker",
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=pulseplate.amtool-native=" + token,
                ]
            ).stdout.splitlines()
            assert len(ids) <= 1
            for identifier in ids:
                observed = json.loads(
                    _native(["docker", "inspect", "--format", "{{json .}}", identifier]).stdout
                )
                assert (
                    observed["Id"] == identifier
                    and (not cid or identifier == cid)
                    and observed["Name"] == "/" + name
                    and observed["Image"] == image
                )
                assert observed["Config"]["Labels"]["pulseplate.amtool-native"] == token
                _native(["docker", "rm", "--force", "--volumes", identifier])
            assert not _native(
                [
                    "docker",
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=pulseplate.amtool-native=" + token,
                ]
            ).stdout.strip()

        except BaseException as cleanup_error:
            if primary is not None:
                primary.add_note("Owned amtool cleanup failed: " + type(cleanup_error).__name__)
                raise primary from None
            raise


def _native_alertmanager_candidate(
    directory: Path, image: str, evidence: dict[str, object]
) -> None:
    """Actual local candidate UI/probes/UID/anonymous-volume restart and CA controls."""
    graph = evidence["graph"]
    assert isinstance(graph, dict) and graph["config"]["digest"] == image
    files = graph["files"]
    assert isinstance(files, dict)
    expected = {
        "usr/bin/alertmanager",
        "usr/bin/amtool",
        "usr/bin/wget",
        "usr/bin/httpd",
        "etc/alertmanager/alertmanager.yml",
        "LICENSE",
        "NOTICE",
    }
    assert set(files) == expected
    cid = volume = ""
    token = uuid.uuid4().hex
    name = "pulseplate-am-native-" + token
    attempted = False
    primary: BaseException | None = None
    config = directory / "state.yml"
    config.write_text("route:\n  receiver: synthetic\nreceivers:\n  - name: synthetic\n")
    config.chmod(0o444)
    document = directory / "probe-document"
    document.mkdir()
    document.chmod(0o755)
    (document / "index.html").write_text("pulseplate-owned-httpd-probe\n")
    (document / "index.html").chmod(0o444)

    def request(path: str) -> tuple[bytes, dict[str, str]]:
        """Require a complete bounded local HTTP200 response without ambient proxies."""
        with build_opener(ProxyHandler({})).open(
            Request("http://127.0.0.1:19095" + path, headers={"Accept-Encoding": "gzip"}),
            timeout=10,
        ) as response:
            assert response.status == 200
            raw = response.read(1024 * 1024 + 1)
            assert len(raw) <= 1024 * 1024
            return raw, dict(response.headers)

    def ready() -> None:
        """Prove the actual same-container wget readiness within one nonrenewed deadline."""
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = _native(
                [
                    "docker",
                    "exec",
                    cid,
                    "/usr/bin/wget",
                    "-q",
                    "-O",
                    "-",
                    "http://127.0.0.1:19095/-/ready",
                ],
                timeout=min(10, max(0.1, deadline - time.monotonic())),
                check=False,
            )
            if result.returncode == 0:
                assert "OK" in result.stdout
                return
            time.sleep(0.1)
        raise AssertionError("owned candidate readiness did not complete within30s")

    def archive(path: str) -> list[tuple[tarfile.TarInfo, bytes]]:
        """Decode actual Docker-copy tar data, preserving every regular/directory member."""
        raw = base64.b64decode(
            _native(["docker", "cp", cid + ":" + path, "-"], binary=True).stdout, validate=True
        )
        rows = []
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as copied:
            for member in copied:
                assert member.isfile() or member.isdir()
                stream = copied.extractfile(member) if member.isfile() else None
                value = stream.read(member.size + 1) if stream is not None else b""
                assert len(value) == member.size
                rows.append((member, value))
        return rows

    try:
        attempted = True
        cid = _native(
            [
                "docker",
                "create",
                "--name",
                name,
                "--label",
                "pulseplate.am-native=" + token,
                "--pull=never",
                "--network=host",
                "--read-only",
                "--user=65534:65534",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--mount",
                "type=volume,target=/alertmanager",
                "--mount",
                "type=bind,source=" + str(config) + ",target=/fixture.yml,readonly",
                "--mount",
                "type=bind,source=" + str(document) + ",target=/probe-document,readonly",
                image,
                "--config.file=/fixture.yml",
                "--storage.path=/alertmanager",
                "--cluster.listen-address=",
                "--web.listen-address=127.0.0.1:19095",
            ]
        ).stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{64}", cid)
        observed = json.loads(_native(["docker", "inspect", "--format", "{{json .}}", cid]).stdout)
        assert observed["Id"] == cid and observed["Name"] == "/" + name
        assert (
            observed["Image"] == image
            and observed["Config"]["Labels"]["pulseplate.am-native"] == token
        )
        mounts = [m for m in observed["Mounts"] if m["Destination"] == "/alertmanager"]
        assert len(mounts) == 1 and mounts[0]["Type"] == "volume" and mounts[0]["RW"] is True
        volume = mounts[0]["Name"]
        assert re.fullmatch(r"[0-9a-f]{64}", volume), "explicit anonymous volume identity required"
        before = json.loads(_native(["docker", "volume", "inspect", volume]).stdout)
        assert len(before) == 1 and before[0]["Name"] == volume
        _native(["docker", "start", cid])
        ready()
        top = _native(["docker", "top", cid, "-eo", "uid,pid,args"]).stdout.splitlines()[1:]
        assert any(row.split()[0] == "65534" and "alertmanager" in row for row in top)
        for binary in ("alertmanager", "amtool"):
            copied = directory / ("actual-" + binary)
            assert not copied.exists() and not copied.is_symlink()
            _native(["docker", "cp", cid + ":/usr/bin/" + binary, str(copied)])
            info = copied.lstat()
            assert (
                copied.is_file()
                and not copied.is_symlink()
                and info.st_nlink == 1
                and 0 < info.st_size <= 256 * 1024**2
            )
            with copied.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            assert actual == files["usr/bin/" + binary]
            again = copied.lstat()
            assert (
                again.st_dev,
                again.st_ino,
                again.st_mode,
                again.st_nlink,
                again.st_size,
                again.st_mtime_ns,
            ) == (
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_nlink,
                info.st_size,
                info.st_mtime_ns,
            )
        ca = archive("/etc/ssl/certs/ca-certificates.crt")
        assert len(ca) == 1 and hashlib.sha256(ca[0][1]).hexdigest() == graph["default_CA_sha256"]
        root, headers = request("/")
        ui = evidence.get("UI_file_hashes")
        if ui is None:
            # Original acceptance and present binary hashes bind this durable fixture oracle.
            assert (
                image == "sha256:46928bb4d3eac8b7bd9d8516a9427c3ec684244fc5f74260324e0acb6bcea9d4"
            )
            assert graph["manifest"]["digest"] == ALERTMANAGER_IMAGE.split("@", 1)[1]
            assert all(
                files["usr/bin/" + name] == digest for name, digest in _ACCEPTED_AM_BINARIES.items()
            )
            ui = _ACCEPTED_AM_UI
        assert isinstance(ui, dict)
        assert (
            headers.get("Content-Encoding") == "gzip"
            and hashlib.sha256(root).hexdigest() == ui["index.html.gz"]
        )
        html = gzip.decompress(root).decode("utf-8")
        assets = re.findall(r'(?:src|href)="([^"?#]+\.(?:js|css))"', html)
        assert assets, "actual rendered UI asset required"
        asset = assets[0].removeprefix("./")
        relative = asset.lstrip("/") + ".gz"
        assert relative in ui
        payload, asset_headers = request("/" + asset.lstrip("/"))
        assert (
            asset_headers.get("Content-Encoding") == "gzip"
            and hashlib.sha256(payload).hexdigest() == ui[relative]
        )
        _native(
            [
                "docker",
                "exec",
                "--detach",
                cid,
                "/usr/bin/httpd",
                "-f",
                "-p",
                "127.0.0.1:19096",
                "-h",
                "/probe-document",
            ]
        )
        probe_deadline = time.monotonic() + 30
        while time.monotonic() < probe_deadline:
            probe = _native(
                [
                    "docker",
                    "exec",
                    cid,
                    "/usr/bin/wget",
                    "-q",
                    "-O",
                    "-",
                    "http://127.0.0.1:19096/",
                ],
                timeout=10,
                check=False,
            )
            if probe.returncode == 0:
                assert probe.stdout == "pulseplate-owned-httpd-probe\n"
                break
            time.sleep(0.1)
        else:
            raise AssertionError("actual httpd/wget request did not complete")
        amtool = [
            "docker",
            "exec",
            cid,
            "/usr/bin/amtool",
            "--no-version-check",
            "--timeout=10s",
            "--alertmanager.url=http://127.0.0.1:19095",
        ]
        silence = _native(
            [
                *amtool,
                "silence",
                "add",
                "alertname=PulsePlateSyntheticStorage",
                "--author=synthetic-fixture",
                "--comment=owned-persistence-control",
                "--duration=1h",
            ]
        ).stdout.strip()
        assert re.fullmatch(r"[0-9a-f-]{36}", silence)
        _native(["docker", "stop", "--time=30", cid], timeout=35)
        stopped = json.loads(
            _native(["docker", "inspect", "--format", "{{json .State}}", cid]).stdout
        )
        assert (
            stopped["Running"] is False
            and stopped["Status"] == "exited"
            and stopped["ExitCode"] == 0
        )
        state = archive("/alertmanager")
        roots = [
            member
            for member, _raw in state
            if member.isdir() and member.name.rstrip("/") == "alertmanager"
        ]
        assert len(roots) == 1 and roots[0].uid == roots[0].gid == 65534 and roots[0].mode == 0o700
        assert any(
            member.isfile() and member.size > 0 and "silences" in member.name
            for member, _raw in state
        )
        _native(["docker", "start", cid])
        ready()
        restored, _ = request("/api/v2/silence/" + silence)
        assert json.loads(restored)["id"] == silence
        again = json.loads(_native(["docker", "inspect", "--format", "{{json .}}", cid]).stdout)
        assert (
            again["Id"] == cid
            and next(m["Name"] for m in again["Mounts"] if m["Destination"] == "/alertmanager")
            == volume
        )
        print("native_AM_UI_probes_UID_storage_restart=pass", flush=True)
    except BaseException as error:
        primary = error
        try:
            metadata = {}
            for label, path in (("document", document), ("index", document / "index.html")):
                try:
                    info = path.lstat()
                    metadata[label] = {
                        "mode": oct(info.st_mode & 0o7777),
                        "type": oct(info.st_mode & 0o170000),
                        "uid": info.st_uid,
                        "gid": info.st_gid,
                    }
                except OSError as observation_error:
                    metadata[label] = {"unavailable": type(observation_error).__name__}
            error.add_note(
                "Owned HTTP probe fixture metadata: "
                + json.dumps(metadata, ensure_ascii=True, sort_keys=True)
            )
        except BaseException:
            # Optional owned metadata must not replace the primary failure or its cleanup.
            pass
        raise
    finally:
        try:
            if attempted:
                ids = _native(
                    [
                        "docker",
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.am-native=" + token,
                    ]
                ).stdout.splitlines()
                assert len(ids) <= 1
                for identifier in ids:
                    row = json.loads(
                        _native(["docker", "inspect", "--format", "{{json .}}", identifier]).stdout
                    )
                    assert (
                        row["Id"] == identifier
                        and row["Name"] == "/" + name
                        and row["Config"]["Labels"]["pulseplate.am-native"] == token
                    )
                    assert not cid or identifier == cid
                    _native(["docker", "rm", "--force", "--volumes", identifier])
                assert not _native(
                    [
                        "docker",
                        "ps",
                        "--all",
                        "--quiet",
                        "--no-trunc",
                        "--filter",
                        "label=pulseplate.am-native=" + token,
                    ]
                ).stdout.strip()
                if volume:
                    absent = _native(["docker", "volume", "inspect", volume], check=False)
                    assert absent.returncode != 0 and re.search(
                        r"no such volume|not found", absent.stderr, flags=re.IGNORECASE
                    ), "exact anonymous volume absence not observed"
            if primary is not None:
                print("native_AM_candidate_failed=" + type(primary).__name__, flush=True)

        except BaseException as cleanup_error:
            if primary is not None:
                primary.add_note("Owned candidate cleanup failed: " + type(cleanup_error).__name__)
                raise primary from None
            raise

    bad = "pulseplate-am-unwritable-" + uuid.uuid4().hex
    bad_id = ""
    bad_primary: BaseException | None = None
    try:
        bad_id = _native(
            [
                "docker",
                "create",
                "--name",
                bad,
                "--label",
                "pulseplate.am-unwritable=" + bad,
                "--pull=never",
                "--network=none",
                "--read-only",
                "--user=65534:65534",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--tmpfs",
                "/alertmanager:uid=0,gid=0,mode=0500,size=16m",
                "--mount",
                "type=bind,source=" + str(config) + ",target=/fixture.yml,readonly",
                image,
                "--config.file=/fixture.yml",
                "--storage.path=/alertmanager",
                "--cluster.listen-address=",
                "--web.listen-address=127.0.0.1:19095",
            ]
        ).stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{64}", bad_id)
        _native(["docker", "start", bad_id])
        waited = _native(["docker", "wait", bad_id], timeout=30)
        assert waited.stdout.strip().isdigit() and int(waited.stdout.strip()) != 0
        logs = _native(["docker", "logs", bad_id])
        assert (
            re.search(
                r"(?:permission denied|read-only file system)",
                logs.stdout + logs.stderr,
                flags=re.IGNORECASE,
            )
            and "/alertmanager" in logs.stdout + logs.stderr
        )
    except BaseException as error:
        bad_primary = error
        raise
    finally:
        try:
            ids = _native(
                [
                    "docker",
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=pulseplate.am-unwritable=" + bad,
                ]
            ).stdout.splitlines()
            assert len(ids) <= 1
            for identifier in ids:
                row = json.loads(
                    _native(["docker", "inspect", "--format", "{{json .}}", identifier]).stdout
                )
                assert (
                    row["Id"] == identifier
                    and (not bad_id or identifier == bad_id)
                    and row["Name"] == "/" + bad
                    and row["Image"] == image
                    and row["Config"]["Labels"]["pulseplate.am-unwritable"] == bad
                )
                _native(["docker", "rm", "--force", "--volumes", identifier])
            assert not _native(
                [
                    "docker",
                    "ps",
                    "--all",
                    "--quiet",
                    "--no-trunc",
                    "--filter",
                    "label=pulseplate.am-unwritable=" + bad,
                ]
            ).stdout.strip()
        except BaseException as cleanup_error:
            if bad_primary is not None:
                bad_primary.add_note(
                    "Owned permission-control cleanup failed: " + type(cleanup_error).__name__
                )
                raise bad_primary from None
            raise
    default_ca = _native_amtool_candidate(
        image,
        [
            "--no-version-check",
            "--timeout=10s",
            "--alertmanager.url=https://github.com",
            "alert",
            "query",
        ],
        check=False,
    )
    assert (
        default_ca.returncode == 1
        and default_ca.stdout == ""
        and default_ca.stderr
        in (
            "amtool: error: [GET /alerts] getAlerts (status 404): {}\n\n",
            "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
        )
    ), "default-root TLS requires an exact amtool HTTP404/410 response"
    print("native_AM_default_CA_verified_HTTP404_or_410=pass", flush=True)


def _native_alertmanager_local_tls(directory: Path, image: str) -> None:
    """The actual amtool client validates SAN/trust/protocol; no insecure-skip flag."""
    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """Count only a successful TLS HTTP request reaching the synthetic endpoint."""
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")

        def log_message(self, format: str, *args: object) -> None:
            """Keep the fixed synthetic HTTP response from generating unrelated server logs."""
            del format, args

    for case in ("matching", "untrusted", "hostname", "plaintext"):
        case_dir = directory / case
        case_dir.mkdir()
        cert, key = case_dir / "cert.pem", case_dir / "key.pem"
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
                "/CN=owned-fixture",
                "-addext",
                "subjectAltName=" + ("DNS:wrong.invalid" if case == "hostname" else "IP:127.0.0.1"),
            ],
            timeout=30,
        )
        cert.chmod(0o444)
        config = case_dir / "client.yml"
        config.write_text("tls_config:\n  ca_file: /fixture-ca.pem\n")
        config.chmod(0o444)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread: threading.Thread | None = None
        count = len(hits)
        primary_failure: BaseException | None = None
        try:
            if case != "plaintext":
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.load_cert_chain(cert, key)
                server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            mounts = []
            if case != "untrusted":
                mounts += [
                    "type=bind,source=" + str(cert) + ",target=/fixture-ca.pem,readonly",
                    "type=bind,source=" + str(config) + ",target=/fixture-client.yml,readonly",
                ]
            argv = [
                "--no-version-check",
                "--timeout=10s",
                "--alertmanager.url=https://127.0.0.1:" + str(server.server_port),
            ]
            if case != "untrusted":
                argv.append("--http.config.file=/fixture-client.yml")
            actual = _native_amtool_candidate(
                image, [*argv, "-o", "json", "alert", "query"], mounts=mounts, check=False
            )
            if case == "matching":
                assert (
                    actual.returncode == 0
                    and json.loads(actual.stdout) == []
                    and len(hits) == count + 1
                )
            else:
                assert actual.returncode != 0 and len(hits) == count
                assert re.search(
                    r"x509:.*(?:unknown authority|valid for|not valid|cannot validate)|HTTP response to HTTPS client|first record does not look like a TLS handshake",
                    actual.stderr + actual.stdout,
                    flags=re.IGNORECASE,
                )
        except BaseException as error:
            primary_failure = error
            raise
        finally:
            cleanup_errors: list[Exception] = []
            if thread is not None and thread.is_alive():
                try:
                    server.shutdown()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            try:
                server.server_close()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
            if thread is not None and thread.ident is not None:
                try:
                    thread.join(5)
                    assert not thread.is_alive()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            for cleanup_error in cleanup_errors:
                _native_am_failure("owned_fixture", cleanup_error)
            if cleanup_errors and primary_failure is None:
                raise cleanup_errors[0]
    print("native_AM_local_TLS_SAN_and_protocol=pass", flush=True)


def _native_alertmanager_compose_context(directory: Path) -> None:
    """Render actual templates with synthetic installed context and no daemon or images."""
    from scripts.ci import fetch_docker_source_artifacts as source

    fixture = directory / "am-compose-context"
    fixture.mkdir(mode=0o700)
    installed = fixture / "installed/deploy"
    incoming = fixture / "payload/deploy"
    installed.mkdir(parents=True, mode=0o700)
    incoming.mkdir(parents=True, mode=0o700)
    (incoming / "alertmanager").mkdir(mode=0o700)
    for name in ("alertmanager.yml", "trivy-ignore.yaml"):
        (incoming / "alertmanager" / name).write_bytes(
            (ROOT / "deploy/alertmanager" / name).read_bytes()
        )
    private_config = fixture / "empty-docker-config"
    private_config.mkdir(mode=0o700)
    configuration: dict[str, object] = {"auths": {}}
    if sys.platform == "darwin":
        # Use only the already-installed Docker Desktop plugin; no user config is read.
        configuration["cliPluginsExtraDirs"] = [
            "/Applications/Docker.app/Contents/Resources/cli-plugins"
        ]
    (private_config / "config.json").write_text(json.dumps(configuration))
    socket_path = fixture / "absent-docker.sock"
    assert not socket_path.exists()
    env_file = fixture / "synthetic-server.env"
    synthetic = "ghcr.io/pulseplate/configuration-only@sha256:" + "1" * 64
    inputs = {
        "IMAGE_REF": synthetic,
        "STAGING_IMAGE_REF": synthetic,
        "STAGING_CADDY_IMAGE_REF": synthetic,
        "PROMETHEUS_RUNTIME_REF": synthetic,
        "STAGING_ENV_FILE": str(installed / ".env"),
        "POSTGRES_USER": "synthetic",
        "POSTGRES_DB": "synthetic",
        "POSTGRES_PASSWORD": "synthetic",
        "DATABASE_URL": "postgresql://synthetic:synthetic@database.invalid/synthetic",
        "STAGING_DOMAIN": "staging.invalid",
        "PRODUCTION_DOMAIN": "production.invalid",
        "STAGING_FALLBACK_DOMAIN": "staging.invalid",
    }
    env_file.write_text("".join(f"{key}={value}\n" for key, value in inputs.items()))
    prefix = [
        "docker",
        "--config",
        str(private_config),
        "--host",
        "unix://" + str(socket_path),
        "compose",
        "--env-file",
        str(env_file),
    ]
    with pytest.MonkeyPatch.context() as runtime:
        runtime.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", private_config)
        for name in (
            "docker-compose.staging.yaml",
            "docker-compose.production.yaml",
            "docker-compose.production.selfhosted.yaml",
        ):
            original = (ROOT / "deploy" / name).read_bytes()
            compose = incoming / name
            compose.write_bytes(original)
            installed_compose = installed / name
            installed_compose.write_bytes(original)
            contour = "staging" if "staging" in name else "production"
            # First prove the incumbent CI-owned empty-env context for every real template.
            (incoming / ".env").write_bytes(b"")
            (installed / ".env").write_bytes(b"")
            contexts = (incoming,) if contour == "staging" else (incoming, installed)
            for project in contexts:
                inputs["STAGING_ENV_FILE"] = str(project / ".env")
                env_file.write_text("".join(f"{key}={value}\n" for key, value in inputs.items()))
                if project == installed:
                    (incoming / ".env").unlink()
                argv = [
                    *prefix,
                    "--project-directory",
                    str(project),
                    "-f",
                    str(compose),
                    "--profile",
                    "*",
                    "config",
                    "--format",
                    "json",
                ]
                result = _native(argv, cwd=fixture, check=False, timeout=8)
                assert result.returncode == 0, result.stderr
                actual = source._alertmanager_contract_json(result.stdout.encode())
                assert (
                    source._alertmanager_contract_candidate(
                        actual,
                        compose,
                        incoming / "alertmanager/alertmanager.yml",
                        incoming / "alertmanager/trivy-ignore.yaml",
                        contour,
                        installed_compose=project / name,
                    )
                    == "accepted"
                )
                assert compose.read_bytes() == original
                assert not (installed / "alertmanager").exists()
                if project == installed:
                    assert not (incoming / ".env").exists()
                    # --env-file cannot substitute for the service's installed relative .env.
                    (installed / ".env").unlink()
                    missing_service_env = _native(argv, cwd=fixture, check=False, timeout=8)
                    assert missing_service_env.returncode != 0
                    assert str(installed / ".env") in missing_service_env.stderr
                    (installed / ".env").write_bytes(b"")
                    env_file.rename(fixture / "held-synthetic-server.env")
                    try:
                        missing_explicit_env = _native(argv, cwd=fixture, check=False, timeout=8)
                        assert missing_explicit_env.returncode != 0
                        assert str(env_file) in missing_explicit_env.stderr
                    finally:
                        (fixture / "held-synthetic-server.env").rename(env_file)
                    assert not (incoming / ".env").exists()
                print(
                    "native_AM_compose_context=" + name + ":" + project.parent.name + "=pass",
                    flush=True,
                )
    assert not socket_path.exists()


def native_alertmanager_main(
    image_id: str,
    config_sha256: str,
    observation: Path | None = None,
    *,
    producer_image: bool = False,
) -> None:
    """Explicit local-image AM fixtures, independent of Prometheus publication state."""
    assert type(producer_image) is bool, "one explicit native AM scope required"
    assert (
        not producer_image or observation is not None
    ), "producer-image scope requires observation"
    assert sys.platform == "linux", "native mode requires the existing Linux CI runner"
    assert re.fullmatch(
        r"sha256:[0-9a-f]{64}", image_id
    ), "one immutable local AM image ID required"
    config = ROOT / "deploy/alertmanager/alertmanager.yml"
    assert config_sha256 == "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549"
    assert (
        not config.is_symlink() and hashlib.sha256(config.read_bytes()).hexdigest() == config_sha256
    )
    with (
        tempfile.TemporaryDirectory(prefix="pulseplate-am-only-native-") as raw,
        pytest.MonkeyPatch.context() as runtime,
    ):
        directory = Path(raw)
        native_config = directory / "empty-docker-config"
        native_config.mkdir(mode=0o700)
        runtime.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", native_config)
        observed = prometheus_image.one_object(
            _native(
                ["docker", "image", "inspect", "--format", "{{json .}}", image_id]
            ).stdout.encode()
        )
        assert (
            observed.get("Id") == image_id
            and observed.get("Os") == "linux"
            and observed.get("Architecture") == "amd64"
        )
        assert observed.get("Config", {}).get("User") == "65534:65534"
        for name in ("alertmanager", "amtool"):
            version = _native(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--pull=never",
                    "--network=none",
                    "--read-only",
                    "--user=65534:65534",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges:true",
                    "--entrypoint=/bin/" + name,
                    image_id,
                    "--version",
                ]
            )
            assert "version 0.34.1" in version.stdout + version.stderr
            if observation is not None:
                lines = [
                    line.strip()
                    for line in (version.stdout + version.stderr).splitlines()
                    if line.strip()
                ]
                assert (
                    len(lines) == 6
                    and lines[0]
                    == name
                    + ", version 0.34.1 (branch: HEAD, revision: 73c6bfe7393929211294c1954f30d8ed78e4d0ad)"
                )
                stamped = {}
                for line in lines[1:]:
                    field, separator, value = line.partition(":")
                    assert separator and field.strip() not in stamped
                    stamped[field.strip()] = value.strip()
                assert stamped == {
                    "build user": "pulseplate@builder",
                    "build date": "19700101-00:00:00",
                    "go version": "go1.27.3",
                    "platform": "linux/amd64",
                    "tags": "netgo",
                }, "actual stamped native metadata differs from frozen compiler command"
        _native(
            [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "--network=none",
                "--read-only",
                "--user=65534:65534",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--mount",
                "type=bind,source="
                + str(config)
                + ",target=/etc/alertmanager/alertmanager.yml,readonly",
                "--entrypoint=/bin/amtool",
                image_id,
                "check-config",
                "/etc/alertmanager/alertmanager.yml",
            ]
        )
        # Producer image proof precedes independent output selection. The selected
        # consumer remains responsible for the complete canonical Compose check.
        if not producer_image:
            _native_alertmanager_compose_context(directory)
        failures = []
        if observation is not None:
            assert (
                observation.is_file()
                and not observation.is_symlink()
                and observation.stat().st_size <= 64 * 1024**2
            )
            evidence = prometheus_image.one_object(observation.read_bytes())
            _native_alertmanager_candidate(directory, image_id, evidence)
            _native_alertmanager_local_tls(directory, image_id)
        for name, check in (
            (
                "amtool_lifetime",
                lambda: _native_amtool_lifetime(directory, image_id, independent=True),
            ),
            ("alertmanager", lambda: _native_alertmanager(directory, image_id)),
        ):
            try:
                check()
            except Exception as error:
                failures.append(name)
                _native_am_failure(name, error)
        assert not failures, "AM-only native fixtures failed: " + ",".join(failures)
        if observation is not None:
            for case in ("untrusted", "hostname", "plaintext"):
                negative = directory / ("smtp-" + case)
                negative.mkdir()
                _native_alertmanager(negative, image_id, tls_failure=case)
    print(
        (
            (
                "native_AM_producer_image_controls=pass"
                if producer_image
                else "native_AM_full_candidate_controls=pass"
            )
            if observation is not None
            else "native_AM_existing_fixture_subset=pass; default_CA_and_full_candidate_acceptance=HOLD_SEPARATE_CONTROLS"
        ),
        flush=True,
    )


def native_main(alertmanager_image_id: str, alertmanager_config_sha256: str) -> None:
    """Run every existing generic control with explicit same-runner AM identity after preparation."""
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", alertmanager_image_id)
    assert (
        alertmanager_config_sha256
        == hashlib.sha256((ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()).hexdigest()
    )
    selection = prometheus_image.read_image_manifest(ROOT / prometheus_image.MANIFEST_PATH)[
        "selection"
    ]
    image_id = selection["config_digest"]
    assert sys.platform == "linux", "native mode requires the existing Linux CI runner"
    image = prometheus_image.one_object(
        _native(["docker", "image", "inspect", "--format", "{{json .}}", image_id]).stdout.encode()
    )
    prometheus_image.native_image_contract(image, selection, local=True)
    with (
        tempfile.TemporaryDirectory(prefix="pulseplate-obs2a-native-") as raw,
        pytest.MonkeyPatch.context() as runtime,
    ):
        directory = Path(raw)
        private_config = directory / "empty-docker-config"
        private_config.mkdir(mode=0o700)
        runtime.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", private_config)
        actual_am = prometheus_image.one_object(
            _native(
                ["docker", "image", "inspect", "--format", "{{json .}}", alertmanager_image_id]
            ).stdout.encode()
        )
        assert (
            actual_am.get("Id") == alertmanager_image_id
            and actual_am.get("Os") == "linux"
            and actual_am.get("Architecture") == "amd64"
            and actual_am.get("Config", {}).get("User") == "65534:65534"
        )
        failures: list[str] = []
        for name, check in (
            ("compose_configuration", _native_compose_configuration),
            ("systemd", _native_systemd),
            ("query_lifetime", lambda directory: _native_query_lifetime(directory, image_id)),
            (
                "amtool_lifetime",
                lambda directory: _native_amtool_lifetime(directory, alertmanager_image_id),
            ),
            (
                "alertmanager",
                lambda directory: _native_alertmanager(directory, alertmanager_image_id),
            ),
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


@pytest.mark.parametrize("fault", [None, "image", "config", "platform", "user"])
def test_alertmanager_only_native_entry_binds_local_identity_before_fixtures_without_prometheus(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    image_id = "sha256:" + "a" * 64
    config_hash = "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549"
    calls: list[object] = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        prometheus_image,
        "read_image_manifest",
        lambda *args: pytest.fail("AM-only must not select Prometheus"),
    )

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(argv)
        if "inspect" in argv:
            value = {
                "Id": image_id,
                "Os": "linux",
                "Architecture": "arm64" if fault == "platform" else "amd64",
                "Config": {"User": "root" if fault == "user" else "65534:65534"},
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
        return subprocess.CompletedProcess(argv, 0, "version 0.34.1", "")

    def lifetime(directory: Path, image: str, *, independent: bool) -> None:
        assert directory.is_dir() and image == image_id and independent is True
        calls.append("amtool-lifetime")

    def compose_context(directory: Path) -> None:
        assert directory.is_dir()
        assert isinstance(calls[-1], list) and "check-config" in calls[-1]
        calls.append("compose-context")

    def smtp(directory: Path, image: str) -> None:
        assert directory.is_dir() and image == image_id
        calls.append("smtp-lifecycle")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(
        sys.modules[__name__], "_native_alertmanager_compose_context", compose_context
    )
    monkeypatch.setattr(sys.modules[__name__], "_native_amtool_lifetime", lifetime)
    monkeypatch.setattr(sys.modules[__name__], "_native_alertmanager", smtp)
    if fault:
        with pytest.raises(AssertionError):
            native_alertmanager_main(
                "latest" if fault == "image" else image_id,
                "f" * 64 if fault == "config" else config_hash,
            )
        assert not any(
            phase in calls for phase in ("compose-context", "amtool-lifetime", "smtp-lifecycle")
        )
    else:
        native_alertmanager_main(image_id, config_hash)
        assert calls[-3:] == ["compose-context", "amtool-lifetime", "smtp-lifecycle"]
        assert any(isinstance(argv, list) and "check-config" in argv for argv in calls)
        assert ALERTMANAGER_IMAGE.startswith("ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:")


@pytest.mark.parametrize(
    "fault", ["none", "positive-rejected", "wrong-worker", "wrong-prometheus", "negative-accepted"]
)
def test_checkpoint_original_compose_fixture_classifies_only_synthetic_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/docker")

    def config(argv: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        prefix = ["/absolute/docker", "compose", "-f", str(cwd / "docker-compose.staging.yaml")]
        text = (cwd / ".env").read_text()
        if not calls:
            expected = {
                "POSTGRES_USER": "synthetic_user",
                "POSTGRES_DB": "synthetic_db",
                "STAGING_DOMAIN": "checkpoint.invalid",
                "STAGING_ENV_FILE": str(cwd / "application.env"),
                "STAGING_IMAGE_REF": "ghcr.io/pulseplate/checkpoint-fixture@sha256:" + "1" * 64,
                "STAGING_CADDY_IMAGE_REF": "ghcr.io/pulseplate/caddy-fixture@sha256:" + "2" * 64,
                "PROMETHEUS_RUNTIME_REF": "ghcr.io/pulseplate/prometheus-fixture@sha256:"
                + "3" * 64,
            }
            assert text == "".join(f"{key}={value}\n" for key, value in expected.items())
        if argv == [*prefix, "config", "--format", "json"]:
            assert not calls
            return subprocess.CompletedProcess(argv, 0, json.dumps({"services": {"app": {}}}), "")
        assert argv == [*prefix, "--profile", "*", "config", "--format", "json"]
        assert (cwd / "docker-compose.staging.yaml").read_bytes() == (
            ROOT / "deploy/docker-compose.staging.yaml"
        ).read_bytes()
        assert (cwd / "application.env").read_bytes() == b""
        assert cwd.stat().st_mode & 0o777 == 0o700
        assert "POSTGRES_USER=synthetic_user\n" in text and "POSTGRES_DB=synthetic_db\n" in text
        assert "STAGING_DOMAIN=checkpoint.invalid\n" in text
        calls.append(argv)
        if len(calls) == 1:
            assert "STAGING_IMAGE_REF=" in text and "STAGING_CADDY_IMAGE_REF=" in text
            backend = "ghcr.io/pulseplate/checkpoint-fixture@sha256:" + "1" * 64
            caddy = "ghcr.io/pulseplate/caddy-fixture@sha256:" + "2" * 64
            prometheus = "ghcr.io/pulseplate/prometheus-fixture@sha256:" + "3" * 64
            model = {
                "services": {
                    "app": {"image": backend},
                    "worker": {"image": backend if fault != "wrong-worker" else caddy},
                    "caddy": {"image": caddy},
                    "prometheus": {"image": prometheus if fault != "wrong-prometheus" else caddy},
                }
            }
            return subprocess.CompletedProcess(
                argv, 1 if fault == "positive-rejected" else 0, json.dumps(model), ""
            )
        bindings = ("STAGING_IMAGE_REF", "STAGING_CADDY_IMAGE_REF", "PROMETHEUS_RUNTIME_REF")
        missing = bindings[len(calls) - 2]
        assert missing + "=" not in text
        assert all(binding + "=" in text for binding in bindings if binding != missing)
        return subprocess.CompletedProcess(
            argv,
            0 if fault == "negative-accepted" else 1,
            "",
            missing + " synthetic interpolation rejection",
        )

    monkeypatch.setattr(sys.modules[__name__], "_native", config)
    if fault == "none":
        _native_compose_configuration(tmp_path)
        assert len(calls) == 4
    else:
        with pytest.raises(AssertionError):
            _native_compose_configuration(tmp_path)
    output = capsys.readouterr().out
    assert "synthetic_db" not in output and "postgresql" not in output


def _checkpoint_prometheus_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, object], dict[str, object]]:
    """Complete parser/native-shape data only; no artifact or native admission."""
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    root = tmp_path / "checkpoint-source"
    path = root / prometheus_image.MANIFEST_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_synthetic_prometheus_manifest()))
    (root / "Dockerfile").write_bytes((ROOT / "Dockerfile").read_bytes())
    (root / "deploy/alertmanager").mkdir(parents=True, exist_ok=True)
    (root / "deploy/alertmanager/alertmanager.yml").write_bytes(
        (ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()
    )
    selection = prometheus_image.read_image_manifest(path)["selection"]
    image = {
        "Id": selection["config_digest"],
        "Os": "linux",
        "Architecture": "amd64",
        "RootFS": {"Layers": selection["diff_ids"]},
        "Config": {
            "User": "65532:65532",
            "Entrypoint": ["/bin/prometheus"],
            "WorkingDir": "/prometheus",
            "Cmd": [
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
            ],
            "Volumes": None,
        },
    }
    prometheus_image.native_image_contract(image, selection, local=True)
    monkeypatch.setattr(sys.modules[__name__], "ROOT", root)
    return selection, image


def test_checkpoint_helper_import_does_not_activate_source_prepared_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "import-source"
    for relative in (
        "tests/__init__.py",
        "tests/test_notify_premium_alias_checkpoint_failure.py",
        "scripts/ci/prometheus_source_image.py",
        "scripts/ops/notify_premium_alias_checkpoint_failure.py",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    path = root / prometheus_image.MANIFEST_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": prometheus_image.IMAGE_SCHEMA,
                "phase": "source_prepared",
                "inputs": prometheus_image.declared_inputs(),
                "selection": None,
                "candidate": None,
            }
        )
    )
    prometheus_image.read_image_manifest(path, preparation=True)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "from tests.test_notify_premium_alias_checkpoint_failure import _native; "
            "assert callable(_native); print('import_without_activation')",
        ],
        cwd=root,
        env={
            "PATH": os.defpath,
            "HOME": str(tmp_path),
            "LANG": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "import_without_activation\n" and not result.stderr


def test_checkpoint_prepared_activation_rejects_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _checkpoint_prometheus_fixture(tmp_path, monkeypatch)
    path = ROOT / prometheus_image.MANIFEST_PATH
    data = json.loads(path.read_text())
    data.update(phase="source_prepared", selection=None, candidate=None)
    data["inputs"]["oras"]["retained"] = None
    path.write_text(json.dumps(data))
    prometheus_image.read_image_manifest(path, preparation=True)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda *args, **kwargs: pytest.fail("prepared native effect"),
    )
    monkeypatch.setattr(
        tempfile,
        "TemporaryDirectory",
        lambda *args, **kwargs: pytest.fail("prepared scratch effect"),
    )
    with pytest.raises(
        prometheus_image.QualificationError, match="^source_prepared_not_consumable$"
    ):
        native_main(
            "sha256:" + "6" * 64,
            hashlib.sha256(
                (ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()
            ).hexdigest(),
        )


@pytest.mark.parametrize("fault", ["config-id", "platform", "diff-ids", "runtime-user"])
def test_checkpoint_loaded_image_contract_rejects_before_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    selection, image = _checkpoint_prometheus_fixture(tmp_path, monkeypatch)
    if fault == "config-id":
        image["Id"] = "sha256:" + "4" * 64
    elif fault == "platform":
        image["Architecture"] = "arm64"
    elif fault == "diff-ids":
        image["RootFS"] = {"Layers": ["sha256:" + "4" * 64]}
    else:
        image["Config"]["User"] = "0"
    observed: list[list[str]] = []

    def inspect(argv: list[str]) -> subprocess.CompletedProcess[str]:
        observed.append(argv)
        assert argv == [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{json .}}",
            selection["config_digest"],
        ]
        return subprocess.CompletedProcess(argv, 0, json.dumps(image), "")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys.modules[__name__], "_native", inspect)
    monkeypatch.setattr(
        tempfile, "TemporaryDirectory", lambda *args, **kwargs: pytest.fail("invalid-image effect")
    )
    diagnostic = (
        "consumer_native_runtime_contract"
        if fault == "runtime-user"
        else "consumer_native_config_layers"
    )
    with pytest.raises(prometheus_image.QualificationError, match="^" + diagnostic + "$"):
        native_main(
            "sha256:" + "6" * 64,
            hashlib.sha256(
                (ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()
            ).hexdigest(),
        )
    assert len(observed) == 1


def test_checkpoint_native_main_selects_original_model_configuration_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, image = _checkpoint_prometheus_fixture(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native",
        lambda argv: subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                image
                if argv[-1] == selection["config_digest"]
                else {
                    "Id": "sha256:" + "6" * 64,
                    "Os": "linux",
                    "Architecture": "amd64",
                    "Config": {"User": "65534:65534"},
                }
            ),
            "",
        ),
    )
    for name in (
        "_native_compose_configuration",
        "_native_systemd",
        "_native_query_lifetime",
        "_native_amtool_lifetime",
        "_native_alertmanager",
    ):
        if name == "_native_query_lifetime":

            def query(directory: Path, image_id: str) -> None:
                assert image_id == selection["config_digest"]
                calls.append("_native_query_lifetime")

            monkeypatch.setattr(sys.modules[__name__], name, query)
        else:
            monkeypatch.setattr(
                sys.modules[__name__],
                name,
                lambda directory, *args, selected=name: calls.append(selected),
            )
    native_main(
        "sha256:" + "6" * 64,
        hashlib.sha256((ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()).hexdigest(),
    )
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
    monkeypatch.setattr(notifier, "_compose_environment", lambda path: {})
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
    monkeypatch.setattr(notifier, "_compose_environment", lambda path: {})
    origin = datetime(2026, 10, 5, tzinfo=timezone.utc)
    times = iter([origin, origin + timedelta(seconds=900)])

    class DateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return next(times)

    monkeypatch.setattr(notifier, "datetime", DateTime)
    monkeypatch.setattr(notifier, "_send", lambda argv, env: pytest.fail("expired alert submitted"))
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
    monkeypatch.setattr(notifier, "_compose_environment", lambda path: {})
    calls = 0

    def send(argv: list[str], env: dict[str, str]) -> bool:
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
    image_id = ""
    if fixture == "query":
        selection, _image = _checkpoint_prometheus_fixture(tmp_path, monkeypatch)
        image_id = selection["config_digest"]
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
            if fixture == "query":
                assert argv[:4] == ["docker", "run", "--pull", "never"]
                assert image_id in argv and selection["runtime_ref"] not in argv
            calls.append("setup-error")
            raise RuntimeError("synthetic primary setup")
        calls.append("owned-release:" + ("rm" if "rm" in argv else "stop"))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    with pytest.raises(RuntimeError, match="synthetic primary setup"):
        if fixture == "query":
            _native_query_lifetime(tmp_path, image_id)
        else:
            _native_amtool_lifetime(tmp_path)
    assert calls[:3] == ["acquire", "start", "setup-error"]
    assert "shutdown" in calls and "close" in calls and "join" in calls
    assert any(call.startswith("owned-release:") for call in calls)
    assert "synthetic secondary shutdown" not in capsys.readouterr().out


@pytest.mark.parametrize("fixture", ["query", "amtool"])
@pytest.mark.parametrize("fault", ["shutdown", "container"])
def test_checkpoint_cleanup_failure_without_primary_is_not_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    fixture: str,
    fault: str,
) -> None:
    if fixture == "amtool":
        state = request.getfixturevalue("amtool_native_lifecycle_io")
        state["fault"] = fault
        with pytest.raises(OSError, match="synthetic cleanup-only failure"):
            _native_amtool_lifetime(state["directory"], independent=True)
        assert all(
            operation in state["released"]
            for operation in ("shutdown", "close", "join", "container")
        )
        assert state["released"].count("container") == 1
        return
    from scripts import verify_premium_alias_telemetry as verifier

    image_id = ""
    if fixture == "query":
        selection, _image = _checkpoint_prometheus_fixture(tmp_path, monkeypatch)
        image_id = selection["config_digest"]
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
        if fixture == "query":
            _native_query_lifetime(tmp_path, image_id)
        else:
            _native_amtool_lifetime(tmp_path)
    assert all(operation in released for operation in ("shutdown", "close", "join", "container"))

    assert released.count("container") == (2 if fixture == "query" else 1)


def _interrupt_am_native(signum: int, frame: object) -> None:
    """Global interruption bypasses ordinary fixture aggregation and later work."""
    del frame
    raise SystemExit(
        "native_AM_phase_interrupted="
        + {
            signal.SIGALRM: "SIGALRM",
            signal.SIGTERM: "SIGTERM",
        }.get(signum, "unknown_signal")
    )


def _native_cli(argv: list[str] | None = None) -> None:
    """Dispatch one explicit fixture mode and retain the global phase interruption."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--native-alertmanager", action="store_true")
    parser.add_argument("--alertmanager-image-id")
    parser.add_argument("--alertmanager-config-sha256")
    parser.add_argument("--alertmanager-observation", type=Path)
    parser.add_argument("--alertmanager-producer-image", action="store_true")
    parser.add_argument("--amtool-fixture-send", type=Path)
    parser.add_argument("--amtool-fixture-config", type=Path)
    parser.add_argument("--amtool-fixture-context")
    parser.add_argument("--query-container", nargs=2, metavar=("PROMETHEUS_CID", "APP_CID"))
    parser.add_argument("--native-fixture")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args(argv)
    if (
        sum(
            bool(value)
            for value in (
                args.native,
                args.native_alertmanager,
                args.amtool_fixture_send,
                args.query_container,
                args.native_fixture,
            )
        )
        != 1
    ):
        parser.error("exactly one explicit native fixture mode required")
    if not args.amtool_fixture_send and (
        args.amtool_fixture_config is not None or args.amtool_fixture_context is not None
    ):
        parser.error("sender context is exclusive to the AM sender mode")
    if args.alertmanager_producer_image and (
        not args.native_alertmanager or args.alertmanager_observation is None
    ):
        parser.error("producer-image scope is exclusive to AM-only mode with observation")
    if args.native_alertmanager:
        if args.native or not args.alertmanager_image_id or not args.alertmanager_config_sha256:
            parser.error("AM-only mode requires exact local image ID and configuration hash")

        if args.alertmanager_observation is not None:
            seconds = os.environ.get("ALERTMANAGER_NATIVE_SECONDS", "")
            if re.fullmatch(r"[1-9][0-9]{0,3}", seconds) is None or not 1230 < int(seconds) <= 2400:
                parser.error("full native phase requires its explicit independent budget")
            signal.signal(signal.SIGTERM, _interrupt_am_native)
            signal.signal(signal.SIGALRM, _interrupt_am_native)
            signal.setitimer(signal.ITIMER_REAL, int(seconds))
        primary: BaseException | None = None
        try:
            if args.alertmanager_producer_image:
                native_alertmanager_main(
                    args.alertmanager_image_id,
                    args.alertmanager_config_sha256,
                    args.alertmanager_observation,
                    producer_image=True,
                )
            else:
                native_alertmanager_main(
                    args.alertmanager_image_id,
                    args.alertmanager_config_sha256,
                    args.alertmanager_observation,
                )
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except Exception as error:
                if primary is None:
                    raise
                _native_am_failure("timer_cleanup", error)
    elif args.amtool_fixture_send:
        if (
            args.amtool_fixture_config is None
            or args.amtool_fixture_context is None
            or args.directory is not None
            or args.alertmanager_image_id is not None
            or args.alertmanager_config_sha256 is not None
            or args.alertmanager_observation is not None
        ):
            parser.error("AM sender requires only its exact private context operands")
        raise SystemExit(
            _amtool_fixture_send(
                args.amtool_fixture_send, args.amtool_fixture_config, args.amtool_fixture_context
            )
        )
    elif args.native:
        if (
            not args.alertmanager_image_id
            or not args.alertmanager_config_sha256
            or args.alertmanager_observation is not None
        ):
            parser.error("generic native requires the exact local AM image/config pair")
        native_main(args.alertmanager_image_id, args.alertmanager_config_sha256)
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


if __name__ == "__main__":
    _native_cli()


@pytest.mark.parametrize("ambient", [None, "hostile.invalid/incorrect:latest"])
def test_notifier_binds_selected_manifest_before_all_compose_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambient: str | None
) -> None:
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    _clock(monkeypatch, stub_manifest=False)
    compose = tmp_path / "selected/compose.yaml"
    manifest = compose.parent / "prometheus/image-manifest.json"
    manifest.parent.mkdir(parents=True)
    data = _synthetic_prometheus_manifest()
    manifest.write_text(json.dumps(data))
    monkeypatch.chdir(tmp_path)
    if ambient is None:
        monkeypatch.delenv("PROMETHEUS_RUNTIME_REF", raising=False)
    else:
        monkeypatch.setenv("PROMETHEUS_RUNTIME_REF", ambient)
    monkeypatch.setenv("COMPOSE_PROFILES", "observability,alerting")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def send(argv: list[str], env: dict[str, str]) -> bool:
        calls.append(
            (argv, {key: env[key] for key in ("PROMETHEUS_RUNTIME_REF", "COMPOSE_PROFILES")})
        )
        return True

    monkeypatch.setattr(notifier, "_send", send)
    assert (
        notifier.notify(
            docker="/absolute/docker",
            compose_file=Path("selected/compose.yaml"),
            environment="staging",
        )
        == 0
    )
    assert len(calls) == 15
    assert all(argv[3] == str(compose) for argv, _ in calls)
    assert all(
        env
        == {
            "PROMETHEUS_RUNTIME_REF": data["selection"]["runtime_ref"],
            "COMPOSE_PROFILES": "observability,alerting",
        }
        for _, env in calls
    )
    assert os.environ.get("PROMETHEUS_RUNTIME_REF") == ambient


@pytest.mark.parametrize("fault", ["missing", "malformed", "unselected", "wrong-contour"])
def test_notifier_manifest_failure_precedes_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    compose = tmp_path / "selected/compose.yaml"
    selected = compose.parent / "prometheus/image-manifest.json"
    data = _synthetic_prometheus_manifest()
    if fault == "unselected":
        data.update(phase="source_prepared", selection=None, candidate=None)
    target = tmp_path / "prometheus/image-manifest.json" if fault == "wrong-contour" else selected
    target.parent.mkdir(parents=True)
    if fault != "missing":
        target.write_text("{" if fault == "malformed" else json.dumps(data))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROMETHEUS_RUNTIME_REF", "ambient-must-not-rescue")
    monkeypatch.setattr(notifier.shutil, "which", lambda name: sys.executable)
    monkeypatch.setattr(
        notifier, "_send", lambda *args: pytest.fail("Compose reached after invalid manifest")
    )
    assert notifier.main(["--compose-file", str(compose), "--environment", "staging"]) == 1
    assert capsys.readouterr().out == notifier.ERROR + "\n"


@pytest.mark.parametrize("fault", ["exit", "timeout", "empty", "extra-line", "oversized"])
def test_notifier_reader_failure_is_stable_and_never_sends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    def reader(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert argv[0] == sys.executable
        assert kwargs["timeout"] == notifier.COMMAND_TIMEOUT_SECONDS
        assert kwargs["env"] == {"PATH": os.defpath, "LANG": "C.UTF-8"}
        assert kwargs["stderr"] == subprocess.DEVNULL
        if fault == "exit":
            raise subprocess.CalledProcessError(1, argv)
        if fault == "timeout":
            raise subprocess.TimeoutExpired(argv, 10)
        return subprocess.CompletedProcess(
            argv, 0, {"empty": b"", "extra-line": b"a\nb\n", "oversized": b"x" * 513 + b"\n"}[fault]
        )

    monkeypatch.setattr(notifier.subprocess, "run", reader)
    monkeypatch.setattr(notifier.shutil, "which", lambda name: sys.executable)
    monkeypatch.setattr(
        notifier, "_send", lambda *args: pytest.fail("Compose reached after reader failure")
    )
    assert (
        notifier.main(
            ["--compose-file", str(tmp_path / "compose.yaml"), "--environment", "staging"]
        )
        == 1
    )
    assert capsys.readouterr().out == notifier.ERROR + "\n"


@pytest.mark.parametrize("fault", [None, "corrupt", "symlink", "hardlink"])
def test_alertmanager_native_candidate_hashes_large_binaries_without_diagnostic_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
) -> None:
    image = "sha256:" + "1" * 64
    cid, volume = "2" * 64, "3" * 64
    bodies = {
        "alertmanager": b"synthetic-large-AM" * 140000,
        "amtool": b"synthetic-large-amtool" * 120000,
    }
    assert all(len(raw) > 1024 * 1024 for raw in bodies.values())
    hashes = {"usr/bin/" + name: hashlib.sha256(raw).hexdigest() for name, raw in bodies.items()}
    hashes.update(
        {
            name: "f" * 64
            for name in (
                "usr/bin/wget",
                "usr/bin/httpd",
                "etc/alertmanager/alertmanager.yml",
                "LICENSE",
                "NOTICE",
            )
        }
    )
    evidence = {
        "graph": {"config": {"digest": image}, "files": hashes, "default_CA_sha256": "f" * 64}
    }
    name = token = ""
    removed = False
    copied: list[str] = []
    ca_calls: list[str] = []

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal name, token, removed
        stdout, stderr, code = "", "", 0
        if "create" in argv:
            name = argv[argv.index("--name") + 1]
            token = argv[argv.index("--label") + 1].split("=", 1)[1]
            stdout = cid
        elif "inspect" in argv and "volume" not in argv:
            stdout = json.dumps(
                {
                    "Id": cid,
                    "Name": "/" + name,
                    "Image": image,
                    "Config": {"Labels": {"pulseplate.am-native": token}},
                    "Mounts": [
                        {
                            "Destination": "/alertmanager",
                            "Name": volume,
                            "Type": "volume",
                            "RW": True,
                        }
                    ],
                }
            )
        elif "volume" in argv:
            if removed:
                code, stderr = 1, "Error: no such volume: " + volume
            else:
                stdout = json.dumps([{"Name": volume}])
        elif "top" in argv:
            stdout = "UID PID ARGS\n65534 123 /bin/alertmanager\n"
        elif "cp" in argv:
            source = argv[-2]
            if source.endswith("/ca-certificates.crt"):
                ca_calls.append(source)
                raise RuntimeError("synthetic boundary after both large binary hashes")
            binary = source.rsplit("/", 1)[1]
            assert source == cid + ":/usr/bin/" + binary
            assert argv[-1] != "-" and not kwargs.get(
                "binary"
            ), "Go binaries must not enter the1MiB diagnostic channel"
            target = Path(argv[-1])
            body = bodies[binary]
            if binary == "amtool" and fault == "corrupt":
                body += b"corrupted"
            if binary == "amtool" and fault in ("symlink", "hardlink"):
                backing = tmp_path / "synthetic-backing"
                backing.write_bytes(body)
                if fault == "symlink":
                    target.symlink_to(backing)
                else:
                    os.link(backing, target)
            else:
                target.write_bytes(body)
            copied.append(binary)
        elif "ps" in argv:
            stdout = "" if removed else cid
        elif "rm" in argv:
            assert argv[-1] == cid and "--volumes" in argv
            removed = True
        elif "exec" in argv:
            stdout = "OK\n"
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    if fault is None:
        with pytest.raises(RuntimeError, match="after both large binary hashes"):
            _native_alertmanager_candidate(tmp_path, image, evidence)
        assert len(ca_calls) == 1
    else:
        with pytest.raises(AssertionError):
            _native_alertmanager_candidate(tmp_path, image, evidence)
        assert ca_calls == []
    assert copied == ["alertmanager", "amtool"] and removed


@pytest.mark.parametrize(
    "case",
    [
        "body",
        "wrong-body",
        "refused",
        "launch",
        "timeout",
        "metadata-unavailable",
        "metadata-render",
        "metadata-note",
        "cleanup",
        "metadata-cleanup",
        "traversal-negative",
    ],
)
def test_alertmanager_native_candidate_probe_permissions_body_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    image, cid, volume = "sha256:" + "1" * 64, "2" * 64, "3" * 64
    document = tmp_path / "probe-document"
    index = document / "index.html"
    marker = "pulseplate-owned-httpd-probe\n"
    bodies = {"alertmanager": b"synthetic-AM", "amtool": b"synthetic-amtool"}
    ca = b"synthetic-owned-CA"
    html = gzip.compress(b'<script src="./assets/owned.js"></script>')
    asset = gzip.compress(b"synthetic-owned-asset")
    hashes = {"usr/bin/" + key: hashlib.sha256(body).hexdigest() for key, body in bodies.items()}
    hashes.update(
        {
            key: "f" * 64
            for key in (
                "usr/bin/wget",
                "usr/bin/httpd",
                "etc/alertmanager/alertmanager.yml",
                "LICENSE",
                "NOTICE",
            )
        }
    )
    evidence = {
        "graph": {
            "config": {"digest": image},
            "files": hashes,
            "default_CA_sha256": hashlib.sha256(ca).hexdigest(),
        },
        "UI_file_hashes": {
            "index.html.gz": hashlib.sha256(html).hexdigest(),
            "assets/owned.js.gz": hashlib.sha256(asset).hexdigest(),
        },
    }
    mkdir, chmod, lstat, dumps = Path.mkdir, Path.chmod, Path.lstat, json.dumps
    created = removed = probe_started = False
    name = token = ""
    clock = 0.0
    calls: list[list[str]] = []

    def restrictive_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        mkdir(path, *args, **kwargs)
        if path == document:
            chmod(path, 0o700)

    def controlled_chmod(path: Path, mode: int, **kwargs: object) -> None:
        chmod(path, 0o700 if case == "traversal-negative" and path == document else mode, **kwargs)

    def observed_lstat(path: Path) -> os.stat_result:
        if (
            probe_started
            and path == document
            and case
            in (
                "metadata-unavailable",
                "metadata-cleanup",
            )
        ):
            raise OSError("synthetic owned metadata unavailable")
        return lstat(path)

    def observed_dumps(value: object, **kwargs: object) -> str:
        if (
            case == "metadata-render"
            and isinstance(value, dict)
            and set(value)
            == {
                "document",
                "index",
            }
        ):
            raise ValueError("synthetic metadata rendering failure")
        return dumps(value, **kwargs)

    class ProbeError(RuntimeError):
        def add_note(self, note: str) -> None:
            if case == "metadata-note" and note.startswith("Owned HTTP probe fixture metadata: "):
                raise RuntimeError("synthetic diagnostic note failure")
            super().add_note(note)

    primary = ProbeError("synthetic boundary after exact probe body")
    launch_error = ProbeError("synthetic httpd launch failure")
    timeout_error = subprocess.TimeoutExpired(["synthetic-owned-wget"], 10)

    class Response:
        status = 200
        headers = {"Content-Encoding": "gzip"}

        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self, size: int) -> bytes:
            return self.body[:size]

    class Opener:
        def open(self, request: Request, *, timeout: int) -> Response:
            assert timeout == 10
            assert request.full_url in (
                "http://127.0.0.1:19095/",
                "http://127.0.0.1:19095/assets/owned.js",
            )
            return Response(html if request.full_url.endswith("19095/") else asset)

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal name, token, created, removed, probe_started, clock
        calls.append(argv)
        stdout, stderr, code = "", "", 0
        if "create" in argv:
            name = argv[argv.index("--name") + 1]
            token = argv[argv.index("--label") + 1].split("=", 1)[1]
            assert document.is_dir() and not document.is_symlink()
            assert (
                document.stat().st_mode & 0o777 == 0o755
            ), "probe document must allow non-owner65534 traversal"
            assert document.stat().st_mode & 0o005 == 0o005
            assert index.stat().st_mode & 0o777 == 0o444 and index.read_text() == marker
            assert "--user=65534:65534" in argv and "--read-only" in argv
            assert "--cap-drop=ALL" in argv and "--security-opt=no-new-privileges:true" in argv
            assert "type=bind,source=" + str(document) + ",target=/probe-document,readonly" in argv
            created, stdout = True, cid
        elif "inspect" in argv and "volume" not in argv:
            stdout = dumps(
                {
                    "Id": cid,
                    "Name": "/" + name,
                    "Image": image,
                    "Config": {"Labels": {"pulseplate.am-native": token}},
                    "Mounts": [
                        {
                            "Destination": "/alertmanager",
                            "Name": volume,
                            "Type": "volume",
                            "RW": True,
                        }
                    ],
                }
            )
        elif "volume" in argv:
            if removed:
                code, stderr = 1, "Error: no such volume: " + volume
            else:
                stdout = dumps([{"Name": volume}])
        elif "top" in argv:
            stdout = "UID PID ARGS\n65534 123 /bin/alertmanager\n"
        elif "cp" in argv:
            if argv[-2].endswith("/ca-certificates.crt"):
                assert kwargs.get("binary") is True and argv[-1] == "-"
                archive = io.BytesIO()
                with tarfile.open(fileobj=archive, mode="w") as output:
                    entry = tarfile.TarInfo("ca-certificates.crt")
                    entry.size = len(ca)
                    output.addfile(entry, io.BytesIO(ca))
                stdout = base64.b64encode(archive.getvalue()).decode("ascii")
            else:
                binary = argv[-2].rsplit("/", 1)[1]
                assert binary in bodies and argv[-1] != "-" and not kwargs.get("binary")
                Path(argv[-1]).write_bytes(bodies[binary])
        elif "ps" in argv:
            stdout = cid if created and not removed else ""
        elif "rm" in argv:
            assert argv[-1] == cid and "--volumes" in argv
            if case in ("cleanup", "metadata-cleanup"):
                raise RuntimeError("synthetic owned cleanup failure")
            removed = True
        elif "/usr/bin/httpd" in argv:
            assert argv == [
                "docker",
                "exec",
                "--detach",
                cid,
                "/usr/bin/httpd",
                "-f",
                "-p",
                "127.0.0.1:19096",
                "-h",
                "/probe-document",
            ]
            probe_started = True
            if case in ("launch", "metadata-render", "metadata-note"):
                raise launch_error
        elif argv[-1] == "http://127.0.0.1:19096/":
            assert probe_started and kwargs == {"timeout": 10, "check": False}
            if case == "timeout":
                raise timeout_error
            if case in ("refused", "metadata-unavailable", "cleanup", "metadata-cleanup"):
                clock = 31
                code, stderr = 1, "wget: connection refused\n"
            else:
                stdout = "wrong-body\n" if case == "wrong-body" else marker
        elif "/usr/bin/amtool" in argv:
            assert probe_started and "silence" in argv and "add" in argv
            raise primary
        elif "exec" in argv:
            assert argv[-1] == "http://127.0.0.1:19095/-/ready"
            stdout = "OK\n"
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    monkeypatch.setattr(Path, "mkdir", restrictive_mkdir)
    monkeypatch.setattr(Path, "chmod", controlled_chmod)
    monkeypatch.setattr(Path, "lstat", observed_lstat)
    monkeypatch.setattr(json, "dumps", observed_dumps)
    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(sys.modules[__name__], "build_opener", lambda *args: Opener())
    monkeypatch.setattr(time, "monotonic", lambda: clock)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    expected = (
        subprocess.TimeoutExpired
        if case == "timeout"
        else (
            ProbeError
            if case in ("body", "launch", "metadata-render", "metadata-note")
            else AssertionError
        )
    )
    with pytest.raises(expected) as caught:
        _native_alertmanager_candidate(tmp_path, image, evidence)
    notes = getattr(caught.value, "__notes__", [])
    if case == "traversal-negative":
        assert str(caught.value).splitlines()[0] == (
            "probe document must allow non-owner65534 traversal"
        )
        assert not created and not probe_started and not removed
        assert document.stat().st_mode & 0o777 == 0o700
    else:
        assert created and probe_started
        assert removed is (case not in ("cleanup", "metadata-cleanup"))
        if case == "body":
            assert caught.value is primary
        elif case in ("launch", "metadata-render", "metadata-note"):
            assert caught.value is launch_error
        elif case == "timeout":
            assert caught.value is timeout_error
        elif case == "wrong-body":
            assert "wrong-body" in str(caught.value) and "pulseplate-owned-httpd-probe" in str(
                caught.value
            )
        else:
            assert str(caught.value) == "actual httpd/wget request did not complete"
        if case in ("metadata-render", "metadata-note"):
            assert notes == []
        else:
            note = next(n for n in notes if n.startswith("Owned HTTP probe fixture metadata: "))
            metadata = json.loads(note.split(": ", 1)[1])
            assert set(metadata) == {"document", "index"}
            assert metadata["index"]["mode"] == "0o444"
            if case in ("metadata-unavailable", "metadata-cleanup"):
                assert metadata["document"] == {"unavailable": "OSError"}
            else:
                observed = lstat(document)
                assert metadata["document"] == {
                    "mode": "0o755",
                    "type": "0o40000",
                    "uid": observed.st_uid,
                    "gid": observed.st_gid,
                }
        if case in ("cleanup", "metadata-cleanup"):
            assert notes[-1] == "Owned candidate cleanup failed: RuntimeError"
        else:
            assert calls[-1] == ["docker", "volume", "inspect", volume]
    assert not any("/usr/bin/amtool" in argv for argv in calls) or case == "body"


@pytest.mark.parametrize("binary", [False, True])
def test_alertmanager_native_transport_keeps_one_MiB_diagnostic_ceiling(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[object]:
        del kwargs
        return subprocess.CompletedProcess(
            argv,
            0,
            b"x" * (1024 * 1024 + 1) if binary else "x" * (1024 * 1024 + 1),
            b"" if binary else "",
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(AssertionError):
        _native(["docker", "synthetic-output"], binary=binary)


@pytest.mark.parametrize("actual_exit", [0, 1])
@pytest.mark.parametrize("fault", [None, "wait", "running", "OOM", "identity"])
def test_alertmanager_native_amtool_uses_terminal_exit_and_exact_owned_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    actual_exit: int,
    fault: str | None,
) -> None:
    cid, image = "4" * 64, "sha256:" + "5" * 64
    token = name = ""
    removed = False
    calls: list[list[str]] = []

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal token, name, removed
        del kwargs
        calls.append(argv)
        stdout, stderr = "", ""
        if "create" in argv:
            token = argv[argv.index("--label") + 1].split("=", 1)[1]
            name = argv[argv.index("--name") + 1]
            stdout = cid
        elif "start" in argv:
            stderr = "synthetic x509 rejection" if actual_exit else ""
        elif "wait" in argv:
            stdout = str(9 if fault == "wait" else actual_exit) + "\n"
        elif "inspect" in argv:
            stdout = json.dumps(
                {
                    "Id": ("6" * 64 if fault == "identity" else cid),
                    "Name": "/" + name,
                    "Image": image,
                    "Config": {"Labels": {"pulseplate.amtool-native": token}},
                    "State": {
                        "Status": "exited",
                        "Running": fault == "running",
                        "Restarting": False,
                        "Dead": False,
                        "OOMKilled": fault == "OOM",
                        "Error": "",
                        "ExitCode": actual_exit,
                    },
                }
            )
        elif "ps" in argv:
            stdout = "" if removed else cid
        elif "rm" in argv:
            assert argv[-1] == cid and "--volumes" in argv
            removed = True
        return subprocess.CompletedProcess(argv, 0, stdout, stderr)

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    if fault:
        with pytest.raises(AssertionError):
            _native_amtool_candidate(image, ["--no-version-check", "alert", "query"], check=False)
        assert removed is (fault != "identity")
    else:
        result = _native_amtool_candidate(
            image, ["--no-version-check", "alert", "query"], check=False
        )
        assert result.returncode == actual_exit and removed
    assert any("--network=host" in argv and "--pull=never" in argv for argv in calls)


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_alertmanager_native_transport_retains_raw_terminal_diagnostics_before_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    private = tmp_path / "owned-empty-config"
    private.mkdir(mode=0o700)
    monkeypatch.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", private)
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-not-forwarded")
    monkeypatch.setenv("HTTPS_PROXY", "synthetic-not-forwarded.invalid")

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert set(kwargs["env"]) == {"PATH", "LANG", "HOME", "COMPOSE_PROFILES", "DOCKER_CONFIG"}
        assert kwargs["env"]["DOCKER_CONFIG"] == str(private)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 30, output=b"synthetic partial stdout", stderr=b"synthetic partial stderr"
            )
        return subprocess.CompletedProcess(
            argv, 7, "synthetic native stdout", "synthetic native stderr"
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.TimeoutExpired if failure == "timeout" else AssertionError):
        _native(["docker", "synthetic-owned-command"])
    raw = capsys.readouterr().out
    assert "synthetic-not-forwarded" not in raw
    report = json.loads(raw)
    assert report["AM_native_argv"] == ["/absolute/docker", "synthetic-owned-command"]
    if failure == "timeout":
        assert report["failure"] == "TimeoutExpired" and report["exit"] is None
        assert base64.b64decode(report["stdout_partial_base64"]) == b"synthetic partial stdout"
    else:
        assert report["exit"] == 7 and report["stdout"] == "synthetic native stdout"
        assert report["stderr"] == "synthetic native stderr"


def test_alertmanager_local_tls_partial_setup_closes_owned_server_without_start_or_amtool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[str] = []

    class Server:
        daemon_threads = False

        def __init__(self, address: tuple[str, int], handler: object) -> None:
            del handler
            assert address == ("127.0.0.1", 0)

        def shutdown(self) -> None:
            pytest.fail("unstarted owned server must not wait on shutdown")

        def server_close(self) -> None:
            closed.append("closed")

    class TLS:
        def load_cert_chain(self, cert: Path, key: Path) -> None:
            assert cert.name == "cert.pem" and key.name == "key.pem"
            raise ValueError("synthetic TLS setup failure")

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        assert argv[:2] == ["openssl", "req"]
        for option in ("-out", "-keyout"):
            Path(argv[argv.index(option) + 1]).write_bytes(b"synthetic certificate or key")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(sys.modules[__name__], "ThreadingHTTPServer", Server)
    monkeypatch.setattr(ssl, "SSLContext", lambda *a: TLS())
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native_amtool_candidate",
        lambda *a, **k: pytest.fail("client reached after failed TLS setup"),
    )
    with pytest.raises(ValueError, match="synthetic TLS setup failure"):
        _native_alertmanager_local_tls(tmp_path, "sha256:" + "5" * 64)
    assert closed == ["closed"]


@pytest.mark.parametrize("producer_image", [False, True])
@pytest.mark.parametrize("binary", ["alertmanager", "amtool"])
@pytest.mark.parametrize(
    "fault",
    [None, "version", "revision", "branch", "user", "date", "Go", "platform", "tags", "duplicate"],
)
def test_alertmanager_full_native_entry_checks_both_real_stamped_version_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binary: str,
    fault: str | None,
    producer_image: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    monkeypatch.setattr(fetcher, "_ALERT_ACCEPTED_CANDIDATE", None)
    image = "sha256:" + "8" * 64
    observation = tmp_path / "candidate-observation.json"
    observation.write_text('{"synthetic_control_only":true}')
    calls: list[str] = []
    monkeypatch.setattr(sys, "platform", "linux")

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        assert _AM_NATIVE_DOCKER_CONFIG is not None and _AM_NATIVE_DOCKER_CONFIG.is_dir()
        if "image" in argv and "inspect" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps(
                    {
                        "Id": image,
                        "Os": "linux",
                        "Architecture": "amd64",
                        "Config": {"User": "65534:65534"},
                    }
                ),
                "",
            )
        if "--version" in argv:
            actual = next(
                value.removeprefix("--entrypoint=/bin/")
                for value in argv
                if value.startswith("--entrypoint=/bin/")
            )
            calls.append(actual)
            raw = (
                actual
                + ", version 0.34.1 (branch: HEAD, revision: 73c6bfe7393929211294c1954f30d8ed78e4d0ad)\n  build user: pulseplate@builder\n  build date: 19700101-00:00:00\n  go version: go1.27.3\n  platform: linux/amd64\n  tags: netgo\n"
            )
            if actual == binary and fault is not None:
                replacements = {
                    "version": ("version 0.34.1", "version 0.34.0"),
                    "revision": ("73c6bfe7393929211294c1954f30d8ed78e4d0ad", "a" * 40),
                    "branch": ("branch: HEAD", "branch: unrelated"),
                    "user": ("pulseplate@builder", "unreviewed@builder"),
                    "date": ("19700101-00:00:00", "20261017-00:00:00"),
                    "Go": ("go1.27.3", "go1.26.8"),
                    "platform": ("linux/amd64", "linux/arm64"),
                    "tags": ("tags: netgo", "tags: unknown"),
                }
                if fault == "duplicate":
                    raw += "  tags: netgo\n"
                else:
                    raw = raw.replace(*replacements[fault])
            return subprocess.CompletedProcess(argv, 0, raw, "")
        assert "check-config" in argv
        return subprocess.CompletedProcess(argv, 0, "configuration valid", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native_alertmanager_compose_context",
        lambda *a: calls.append("compose-context"),
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native_alertmanager_candidate",
        lambda *a: calls.append("candidate"),
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native_alertmanager_local_tls",
        lambda *a: calls.append("local-tls"),
    )
    monkeypatch.setattr(
        sys.modules[__name__], "_native_amtool_lifetime", lambda *a, **k: calls.append("lifetime")
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "_native_alertmanager",
        lambda *a, **k: calls.append("smtp-" + k.get("tls_failure", "matching")),
    )
    if fault:
        with pytest.raises(AssertionError):
            native_alertmanager_main(
                image,
                "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
                observation,
                producer_image=producer_image,
            )
        assert binary in calls
    else:
        native_alertmanager_main(
            image,
            "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549",
            observation,
            producer_image=producer_image,
        )
        assert calls == ["alertmanager", "amtool"] + (
            [] if producer_image else ["compose-context"]
        ) + [
            "candidate",
            "local-tls",
            "lifetime",
            "smtp-matching",
            "smtp-untrusted",
            "smtp-hostname",
            "smtp-plaintext",
        ]
        lines = capsys.readouterr().out.splitlines()
        expected = (
            "native_AM_producer_image_controls=pass"
            if producer_image
            else "native_AM_full_candidate_controls=pass"
        )
        opposite = (
            "native_AM_full_candidate_controls=pass"
            if producer_image
            else "native_AM_producer_image_controls=pass"
        )
        assert lines.count(expected) == 1 and opposite not in lines
    assert fetcher._ALERT_ACCEPTED_CANDIDATE is None
    assert _AM_NATIVE_DOCKER_CONFIG is None


@pytest.fixture
def alertmanager_default_ca_native_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Callable[[], None], dict[str, object], dict[str, object]]:
    """Control native IO while keeping both real candidate/managed-helper owners."""
    image = "sha256:" + "4" * 64
    ids = {"main": "1" * 64, "unwritable": "2" * 64, "default": "3" * 64}
    volume, silence = (
        "5" * 64,
        "6" * 8 + "-" + "6" * 4 + "-" + "6" * 4 + "-" + "6" * 4 + "-" + "6" * 12,
    )
    ca = b"synthetic-default-bundle"
    binaries = {"alertmanager": b"synthetic-alertmanager", "amtool": b"synthetic-amtool"}
    html = gzip.compress(b'<script src="./assets/owned.js"></script>')
    asset = gzip.compress(b"synthetic-native-asset")
    files = {"usr/bin/" + key: hashlib.sha256(body).hexdigest() for key, body in binaries.items()}
    files.update(
        {
            key: "f" * 64
            for key in (
                "usr/bin/wget",
                "usr/bin/httpd",
                "etc/alertmanager/alertmanager.yml",
                "LICENSE",
                "NOTICE",
            )
        }
    )
    evidence = {
        "graph": {
            "config": {"digest": image},
            "files": files,
            "default_CA_sha256": hashlib.sha256(ca).hexdigest(),
        },
        "UI_file_hashes": {
            "index.html.gz": hashlib.sha256(html).hexdigest(),
            "assets/owned.js.gz": hashlib.sha256(asset).hexdigest(),
        },
    }
    control: dict[str, object] = {
        "exit": 1,
        "stdout": "",
        "stderr": "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
        "fault": None,
    }
    calls: list[list[str]] = []
    roles: dict[str, dict[str, object]] = {}
    trace: dict[str, object] = {
        "calls": calls,
        "roles": roles,
        "default_creates": 0,
        "default_inspects": 0,
        "storage_archive": False,
        "restored_silence": False,
        "volume_absence": False,
    }
    timeout_error = subprocess.TimeoutExpired(["synthetic-owned-amtool"], 30)
    cleanup_error = OSError("synthetic owned amtool cleanup failure")
    transport_error = RuntimeError("synthetic owned amtool transport failure")
    trace.update(
        timeout_error=timeout_error, cleanup_error=cleanup_error, transport_error=transport_error
    )

    class Response:
        status = 200

        def __init__(self, body: bytes, headers: dict[str, str]) -> None:
            self.body, self.headers = body, headers

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def read(self, size: int) -> bytes:
            return self.body[:size]

    class Opener:
        def open(self, request: Request, *, timeout: int) -> Response:
            assert timeout == 10
            if request.full_url == "http://127.0.0.1:19095/":
                return Response(html, {"Content-Encoding": "gzip"})
            if request.full_url == "http://127.0.0.1:19095/assets/owned.js":
                return Response(asset, {"Content-Encoding": "gzip"})
            assert request.full_url == "http://127.0.0.1:19095/api/v2/silence/" + silence
            trace["restored_silence"] = True
            return Response(
                json.dumps({"id": silence}).encode(), {"Content-Type": "application/json"}
            )

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert argv[0] == "docker"
        fault = control["fault"]
        stdout, stderr, code = "", "", 0
        if "create" in argv:
            role = (
                "default"
                if "--entrypoint=/usr/bin/amtool" in argv
                else "unwritable" if "--tmpfs" in argv else "main"
            )
            name = argv[argv.index("--name") + 1]
            key, value = argv[argv.index("--label") + 1].split("=", 1)
            roles[role] = {"name": name, "key": key, "value": value, "removed": False}
            assert "--user=65534:65534" in argv and "--read-only" in argv
            assert "--cap-drop=ALL" in argv and "--security-opt=no-new-privileges:true" in argv
            if role == "default":
                trace["default_creates"] = int(trace["default_creates"]) + 1
                assert argv[-6:] == [
                    image,
                    "--no-version-check",
                    "--timeout=10s",
                    "--alertmanager.url=https://github.com",
                    "alert",
                    "query",
                ]
                assert "--network=host" in argv
                assert "--mount" not in argv and "--env" not in argv
                assert not any("insecure" in word or "ca_file" in word for word in argv)
            stdout = ids[role]
        elif "ps" in argv:
            label = argv[-1].removeprefix("label=")
            matches = [
                role
                for role, row in roles.items()
                if row["key"] + "=" + row["value"] == label and not row["removed"]
            ]
            assert len(matches) <= 1
            if matches:
                stdout = ids[matches[0]]
                if matches[0] == "default" and fault == "cleanup-census":
                    stdout += "\n" + "7" * 64
        elif "volume" in argv:
            assert argv[-1] == volume
            if roles["main"]["removed"]:
                code, stderr = 1, "Error: no such volume: " + volume
                trace["volume_absence"] = True
            else:
                stdout = json.dumps([{"Name": volume}])
        elif "inspect" in argv:
            role = next(name for name, identifier in ids.items() if identifier == argv[-1])
            row = roles[role]
            if argv[-2] == "{{json .State}}":
                assert role == "main"
                stdout = json.dumps({"Running": False, "Status": "exited", "ExitCode": 0})
            else:
                observed = {
                    "Id": ids[role],
                    "Name": "/" + row["name"],
                    "Image": image,
                    "Config": {
                        "Labels": {row["key"]: row["value"]},
                        "Env": ["SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt"],
                    },
                    "Mounts": [
                        {
                            "Destination": "/alertmanager",
                            "Name": volume,
                            "Type": "volume",
                            "RW": True,
                        }
                    ],
                }
                if role == "default":
                    trace["default_inspects"] = int(trace["default_inspects"]) + 1
                    terminal = trace["default_inspects"] == 1
                    malformed = {
                        "exit-bool": True,
                        "exit-float": 1.0,
                        "exit-string": "1",
                        "exit-unknown": None,
                    }
                    exit_code = malformed.get(fault, control["exit"])
                    state = {
                        "Status": "exited",
                        "ExitCode": exit_code,
                        "Running": False,
                        "Restarting": False,
                        "Dead": False,
                        "OOMKilled": False,
                        "Error": "",
                    }
                    observed["State"] = state
                    if terminal:
                        if fault in ("cid", "name", "image"):
                            observed[{"cid": "Id", "name": "Name", "image": "Image"}[fault]] = (
                                "7" * 64
                            )
                        elif fault == "label":
                            observed["Config"]["Labels"][row["key"]] = "wrong-owned-token"
                        elif fault == "status":
                            state["Status"] = "unknown"
                        elif fault in ("Running", "Restarting", "Dead", "OOMKilled"):
                            state[fault] = True
                        elif fault == "Error":
                            state["Error"] = "synthetic terminal error"
                    elif fault == "cleanup-identity":
                        observed["Id"] = "7" * 64
                stdout = json.dumps(observed)
        elif "cp" in argv:
            source = argv[-2]
            if source.endswith(":/etc/ssl/certs/ca-certificates.crt") or source.endswith(
                ":/alertmanager"
            ):
                assert kwargs.get("binary") is True and argv[-1] == "-"
                raw = io.BytesIO()
                with tarfile.open(fileobj=raw, mode="w") as archive:
                    if source.endswith(":/alertmanager"):
                        trace["storage_archive"] = True
                        root = tarfile.TarInfo("alertmanager")
                        root.type, root.mode, root.uid, root.gid = (
                            tarfile.DIRTYPE,
                            0o700,
                            65534,
                            65534,
                        )
                        archive.addfile(root)
                        member, body = tarfile.TarInfo("alertmanager/silences.json"), b"owned-state"
                    else:
                        member, body = tarfile.TarInfo("ca-certificates.crt"), ca
                    member.size = len(body)
                    archive.addfile(member, io.BytesIO(body))
                stdout = base64.b64encode(raw.getvalue()).decode("ascii")
            else:
                binary = source.rsplit("/", 1)[1]
                assert source == ids["main"] + ":/usr/bin/" + binary
                assert argv[-1] != "-" and not kwargs.get("binary")
                Path(argv[-1]).write_bytes(binaries[binary])
        elif "top" in argv:
            stdout = "UID PID ARGS\n65534 123 /bin/alertmanager\n"
        elif "exec" in argv:
            if "/usr/bin/httpd" in argv:
                assert "--detach" in argv and argv[-1] == "/probe-document"
            elif argv[-1] == "http://127.0.0.1:19096/":
                stdout = "pulseplate-owned-httpd-probe\n"
            elif "/usr/bin/amtool" in argv:
                assert "silence" in argv and "add" in argv
                stdout = silence
            else:
                assert argv[-1] == "http://127.0.0.1:19095/-/ready"
                stdout = "OK\n"
        elif "start" in argv:
            if "--attach" in argv:
                assert argv[-1] == ids["default"] and kwargs == {"timeout": 30, "check": False}
                if fault in ("timeout", "timeout-cleanup"):
                    raise timeout_error
                if fault == "transport":
                    raise transport_error
                assert type(control["exit"]) is int
                code = control["exit"]
                if fault == "attach-exit":
                    code = 2
                assert isinstance(control["stdout"], str) and isinstance(control["stderr"], str)
                stdout, stderr = control["stdout"], control["stderr"]
        elif "stop" in argv:
            assert argv[-1] == ids["main"] and kwargs == {"timeout": 35}
        elif "wait" in argv:
            if argv[-1] == ids["default"]:
                assert kwargs == {"timeout": 10}
                malformed = {
                    "exit-bool": True,
                    "exit-float": 1.0,
                    "exit-string": "1",
                    "exit-unknown": None,
                }
                stdout = str(malformed.get(fault, control["exit"])) + "\n"
                if fault == "wait":
                    stdout = "2\n"
            else:
                assert argv[-1] == ids["unwritable"] and kwargs == {"timeout": 30}
                stdout = "1\n"
        elif "logs" in argv:
            assert argv[-1] == ids["unwritable"]
            stderr = "open /alertmanager: permission denied\n"
        elif "rm" in argv:
            role = next(name for name, identifier in ids.items() if identifier == argv[-1])
            assert "--force" in argv and "--volumes" in argv
            if role == "default" and fault in ("cleanup", "timeout-cleanup"):
                raise cleanup_error
            roles[role]["removed"] = True
        else:
            pytest.fail("unexpected controlled native command: " + repr(argv))
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(sys.modules[__name__], "build_opener", lambda *args: Opener())

    def execute() -> None:
        try:
            _native_alertmanager_candidate(tmp_path, image, evidence)
        finally:
            print(
                "synthetic_default_CA_reached_trace="
                + json.dumps(
                    {
                        "default_creates": trace["default_creates"],
                        "storage_archive": trace["storage_archive"],
                        "restored_silence": trace["restored_silence"],
                        "volume_absence": trace["volume_absence"],
                        "roles": roles,
                        "last_default_calls": [
                            argv
                            for argv in calls
                            if ids["default"] in argv
                            or "--entrypoint=/usr/bin/amtool" in argv
                            or any("pulseplate.amtool-native=" in word for word in argv)
                        ],
                    },
                    sort_keys=True,
                )
            )

    return execute, control, trace


@pytest.mark.parametrize(
    "exit_code,stdout,stderr,accepted",
    [
        pytest.param(
            1,
            "",
            "amtool: error: [GET /alerts] getAlerts (status 404): {}\n\n",
            True,
            id="exact404",
        ),
        pytest.param(
            1,
            "",
            "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
            True,
            id="exact410",
        ),
        pytest.param(
            1, "", "x509: untrusted certificate; HTTP status 404\n", False, id="tls404-error"
        ),
        *[
            pytest.param(
                code,
                "",
                "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
                False,
                id="exit-" + str(code),
            )
            for code in (0, 2, -1)
        ],
        pytest.param(
            1,
            "unexpected output",
            "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
            False,
            id="stdout",
        ),
        pytest.param(
            1,
            "amtool: error: [GET /alerts] getAlerts (status 404): {}\n\n",
            "",
            False,
            id="wrong-stream",
        ),
        *[
            pytest.param(
                1,
                "",
                "amtool: error: [GET /alerts] getAlerts (status " + str(status) + "): {}\n\n",
                False,
                id="status-" + str(status),
            )
            for status in (200, 400, 401, 403, 429, 500)
        ],
        *[
            pytest.param(1, "", raw, False, id=name)
            for name, raw in (
                ("wrong-method", "amtool: error: [POST /alerts] getAlerts (status 410): {}\n\n"),
                ("wrong-path", "amtool: error: [GET /silences] getAlerts (status 410): {}\n\n"),
                (
                    "wrong-operation",
                    "amtool: error: [GET /alerts] getSilences (status 410): {}\n\n",
                ),
                ("wrong-body", "amtool: error: [GET /alerts] getAlerts (status 410): []\n\n"),
                (
                    "extra-body",
                    'amtool: error: [GET /alerts] getAlerts (status 410): {"error":404}\n\n',
                ),
                ("prefix", "error: [GET /alerts] getAlerts (status 410): {}\n\n"),
                ("case", "AMTOOL: error: [GET /alerts] getAlerts (status 410): {}\n\n"),
                ("unicode-prefix", "amtооl: error: [GET /alerts] getAlerts (status 410): {}\n\n"),
                (
                    "unicode-status",
                    "amtool: error: [GET /alerts] getAlerts (status ４１０): {}\n\n",
                ),
                ("one-LF", "amtool: error: [GET /alerts] getAlerts (status 410): {}\n"),
                ("no-LF", "amtool: error: [GET /alerts] getAlerts (status 410): {}"),
                ("extra-LF", "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n\n"),
                ("CRLF", "amtool: error: [GET /alerts] getAlerts (status 410): {}\r\n\r\n"),
                ("leading-space", " amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n"),
                ("trailing-space", "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\n "),
                ("junk", "junk\namtool: error: [GET /alerts] getAlerts (status 410): {}\n\n"),
                (
                    "duplicate",
                    "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\namtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
                ),
                (
                    "mixed",
                    "amtool: error: [GET /alerts] getAlerts (status 404): {}\n\namtool: error: [GET /alerts] getAlerts (status 410): {}\n\n",
                ),
                (
                    "second-failure",
                    "amtool: error: [GET /alerts] getAlerts (status 410): {}\n\nx509: unknown authority\n",
                ),
                ("tls410", "TLS handshake failed: response 410\n"),
                ("DNS", "lookup status 404: no such host\n"),
                ("timeout", "request timeout [404]\n"),
                ("refused", "connect: connection refused (status 410)\n"),
                ("JSON", '{"status":410,"error":"untrusted"}\n'),
                ("malformed", "JSON parse error in HTTP 404 response\n"),
                ("empty", ""),
            )
        ],
    ],
)
def test_alertmanager_native_default_ca_accepts_only_complete_http_results(
    alertmanager_default_ca_native_io: tuple[
        Callable[[], None], dict[str, object], dict[str, object]
    ],
    capsys: pytest.CaptureFixture[str],
    exit_code: int,
    stdout: str,
    stderr: str,
    accepted: bool,
) -> None:
    execute, control, trace = alertmanager_default_ca_native_io
    control.update(exit=exit_code, stdout=stdout, stderr=stderr)
    if accepted:
        assert execute() is None
    else:
        with pytest.raises(
            AssertionError, match="default-root TLS requires an exact amtool HTTP404/410 response"
        ) as caught:
            execute()
        tb = caught.value.__traceback__
        while tb.tb_next is not None:
            tb = tb.tb_next
        assert tb.tb_frame.f_code is _native_alertmanager_candidate.__code__
    output = capsys.readouterr().out
    assert "native_AM_UI_probes_UID_storage_restart=pass\n" in output
    assert trace["default_creates"] == 1 and trace["storage_archive"] is True
    assert trace["restored_silence"] is True and trace["volume_absence"] is True
    assert all(row["removed"] for row in trace["roles"].values())
    marker = "native_AM_default_CA_verified_HTTP404_or_410=pass\n"
    assert (marker in output) is accepted
    assert "native_AM_default_CA_verified_HTTP404=pass" not in output


@pytest.mark.parametrize(
    "fault",
    [
        "exit-bool",
        "exit-float",
        "exit-string",
        "exit-unknown",
        "wait",
        "attach-exit",
        "cid",
        "name",
        "image",
        "label",
        "status",
        "Running",
        "Restarting",
        "Dead",
        "OOMKilled",
        "Error",
        "timeout",
        "transport",
        "cleanup",
        "timeout-cleanup",
        "cleanup-identity",
        "cleanup-census",
    ],
)
def test_alertmanager_native_default_ca_rejects_real_managed_helper_failure(
    alertmanager_default_ca_native_io: tuple[
        Callable[[], None], dict[str, object], dict[str, object]
    ],
    capsys: pytest.CaptureFixture[str],
    fault: str,
) -> None:
    execute, control, trace = alertmanager_default_ca_native_io
    control["fault"] = fault
    expected = (
        subprocess.TimeoutExpired
        if fault in ("timeout", "timeout-cleanup")
        else (
            OSError
            if fault == "cleanup"
            else RuntimeError if fault == "transport" else AssertionError
        )
    )
    with pytest.raises(expected) as caught:
        execute()
    codes = []
    tb = caught.value.__traceback__
    while tb is not None:
        codes.append(tb.tb_frame.f_code)
        tb = tb.tb_next
    assert _native_amtool_candidate.__code__ in codes
    if expected is AssertionError:
        assert codes[-1] is _native_amtool_candidate.__code__
    elif fault in ("timeout", "timeout-cleanup"):
        assert caught.value is trace["timeout_error"]
    elif fault == "cleanup":
        assert caught.value is trace["cleanup_error"]
    else:
        assert caught.value is trace["transport_error"]
    if fault == "timeout-cleanup":
        assert "Owned amtool cleanup failed: OSError" in caught.value.__notes__
    output = capsys.readouterr().out
    assert "native_AM_UI_probes_UID_storage_restart=pass\n" in output
    assert "native_AM_default_CA_verified_HTTP" not in output
    assert trace["default_creates"] == 1 and trace["storage_archive"] is True
    assert trace["restored_silence"] is True and trace["volume_absence"] is True
    roles = trace["roles"]
    assert roles["main"]["removed"] is True and roles["unwritable"]["removed"] is True
    assert roles["default"]["removed"] is (
        fault not in ("cleanup", "timeout-cleanup", "cleanup-identity", "cleanup-census")
    )


@pytest.fixture
def amtool_native_lifecycle_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    """Exercise the real owned-unit predicates with synthetic native IO only."""
    directory = tmp_path / "pulseplate-am-only-native-abcdefgh"
    directory.mkdir(mode=0o700)
    config = directory / "empty-docker-config"
    config.mkdir(mode=0o700)
    units = tmp_path / "units"
    units.mkdir()
    calls: list[list[str]] = []
    sends: list[tuple[list[str], dict[str, str]]] = []
    released: list[str] = []
    state: dict[str, object] = {
        "directory": directory,
        "config": config,
        "units": units,
        "calls": calls,
        "sends": sends,
        "fault": None,
        "released": released,
    }

    class Event:
        def set(self) -> None:
            return None

        def clear(self) -> None:
            return None

        def is_set(self) -> bool:
            return True

        def wait(self, timeout: float) -> bool:
            assert timeout == 10
            return True

    class Server:
        daemon_threads = False

        def __init__(self, *args: object) -> None:
            del args

        def serve_forever(self) -> None:
            return None

        def shutdown(self) -> None:
            released.append("shutdown")
            if state["fault"] == "shutdown":
                raise OSError("synthetic cleanup-only failure")

        def server_close(self) -> None:
            released.append("close")

    class Thread:
        ident: int | None = None
        running = False

        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def start(self) -> None:
            self.ident, self.running = 1, True

        def is_alive(self) -> bool:
            return self.running

        def join(self, timeout: float) -> None:
            assert timeout == 5
            self.running = False
            released.append("join")

    original_lstat = Path.lstat

    def lstat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        info = original_lstat(path, *args, **kwargs)
        if path.parent == units:
            fields = list(info)
            fields[4] = 0
            return os.stat_result(fields)
        return info

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(argv)
        if "start" in argv and state["fault"] == "interrupt":
            _interrupt_am_native(signal.SIGALRM, None)
        if argv[:3] == ["docker", "rm", "-f"]:
            released.append("container")
            if state["fault"] == "container":
                raise OSError("synthetic cleanup-only failure")
        if len(argv) > 2 and Path(argv[2]).name == "install":
            target, source = Path(argv[-1]), Path(argv[-2])
            target.write_bytes(source.read_bytes())
            target.chmod(0o644)
            state["target"] = target
            if state["fault"] == "partial-mismatch":
                target.write_bytes(b"unknown partial bytes")
            if state["fault"] in {"install", "partial-mismatch"}:
                raise PermissionError(errno.EACCES, "private-primary-sentinel", str(target))
        elif len(argv) > 2 and Path(argv[2]).name == "rm":
            if state.get("secondary") == "remove":
                raise PermissionError(errno.EPERM, "private-secondary-remove")
            assert argv[:4] == ["/absolute/sudo", "-n", "/absolute/rm", "--"]
            if any("start" in call for call in calls):
                assert any("stop" in call for call in calls[:-1])
            Path(argv[-1]).unlink()
        if "stop" in argv and state["fault"] == "stop":
            raise OSError(errno.EIO, "private-cleanup-sentinel")
        stdout = "f" * 64 if "ps" in argv else ""
        if "show" in argv:
            assert argv[0] == "/absolute/systemctl" and argv[-2:] == [
                "--property=LoadState",
                "--value",
            ]
            stdout = "not-found\n" if state["fault"] == "LoadState" else "loaded\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def property_value(unit: str, interface: str, name: str, signature: str) -> object:
        target = units / unit
        text = target.read_text()
        command = shlex.split(
            next(line[10:] for line in text.splitlines() if line.startswith("ExecStart="))
        )
        values: dict[str, tuple[str, str, object]] = {
            "ActiveState": ("Unit", "s", "inactive"),
            "SubState": ("Unit", "s", "dead"),
            "MainPID": ("Service", "u", 0),
            "ControlPID": ("Service", "u", 0),
            "FragmentPath": ("Unit", "s", str(target)),
            "DropInPaths": ("Unit", "as", []),
            "NeedDaemonReload": ("Unit", "b", False),
            "ExecStart": ("Service", "a(sasbttttuii)", [[command[0], command, False]]),
            "WorkingDirectory": ("Service", "s", str(ROOT)),
            "User": ("Service", "s", "root"),
            "Environment": ("Service", "as", []),
            "EnvironmentFiles": ("Service", "a(sb)", []),
            "Type": ("Service", "s", "oneshot"),
            "TimeoutStartUSec": ("Service", "t", 960_000_000),
            "TimeoutStopUSec": ("Service", "t", 10_000_000),
            "KillMode": ("Service", "s", "control-group"),
            "Restart": ("Service", "s", "no"),
        }
        wanted_interface, wanted_signature, value = values[name]
        assert (interface, signature) == (wanted_interface, wanted_signature)
        if name == "ActiveState" and state["fault"] in {"active", "activating"}:
            return state["fault"]
        if name in {"MainPID", "ControlPID"} and state["fault"] == name:
            return 12345
        if state["fault"] == name:
            return ["foreign.conf"] if name == "DropInPaths" else "foreign"
        return value

    def send(argv: list[str], env: dict[str, str]) -> bool:
        sends.append((argv, env))
        return len(sends) == 1

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(threading, "Event", Event)
    monkeypatch.setattr(threading, "Thread", Thread)
    monkeypatch.setattr(sys.modules[__name__], "ThreadingHTTPServer", Server)
    monkeypatch.setattr(sys.modules[__name__], "SYSTEMD_UNIT_DIRECTORY", units)
    monkeypatch.setattr(sys.modules[__name__], "_AM_NATIVE_DOCKER_CONFIG", config)
    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(sys.modules[__name__], "_property", property_value)
    monkeypatch.setattr(sys.modules[__name__], "_owned_task_stopped", lambda *a, **k: True)
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)
    monkeypatch.setattr(notifier, "_send", send)
    return state


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "install",
        "partial-mismatch",
        "stop",
        "DropInPaths",
        "FragmentPath",
        "ExecStart",
        "WorkingDirectory",
        "Environment",
        "EnvironmentFiles",
        "NeedDaemonReload",
        "active",
        "activating",
        "SubState",
        "MainPID",
        "ControlPID",
        "LoadState",
    ],
)
def test_amtool_native_exact_owned_install_and_cleanup(
    amtool_native_lifecycle_io: dict[str, object],
    fault: str | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = amtool_native_lifecycle_io
    state["fault"] = fault
    directory = state["directory"]
    assert isinstance(directory, Path)
    if fault is None:
        _native_amtool_lifetime(directory, independent=True)
    else:
        with pytest.raises((AssertionError, OSError)) as raised:
            _native_amtool_lifetime(directory, independent=True)
        if fault in {"install", "partial-mismatch"}:
            assert type(raised.value) is PermissionError and raised.value.errno == errno.EACCES
    calls = state["calls"]
    assert isinstance(calls, list)
    installed = [call for call in calls if len(call) > 2 and Path(call[2]).name == "install"]
    assert len(installed) == 1 and installed[0][:6] == [
        "/absolute/sudo",
        "-n",
        "/absolute/install",
        "-m",
        "0644",
        "--",
    ]
    target = state["target"]
    assert isinstance(target, Path)
    assert target.exists() is (fault in {"stop", "partial-mismatch"})
    starts = [call for call in calls if "start" in call]
    assert bool(starts) is (fault in {None, "stop"})
    if fault in {"active", "activating", "SubState", "MainPID", "ControlPID", "LoadState"}:
        assert not any("stop" in call for call in calls)
    assert "private-primary-sentinel" not in capsys.readouterr().out


def test_amtool_native_unit_fresh_sender_same_config_and_venv_symlink(
    amtool_native_lifecycle_io: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = amtool_native_lifecycle_io
    directory = state["directory"]
    assert isinstance(directory, Path)
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    monkeypatch.setattr(sys, "executable", str(python))
    _native_amtool_lifetime(directory, independent=True)
    staged = next(directory.glob("obs2aamtool*.service"))
    command = shlex.split(
        next(line[10:] for line in staged.read_text().splitlines() if line.startswith("ExecStart="))
    )
    assert command[:8] == [
        "/absolute/env",
        "-i",
        "PATH=" + os.defpath,
        "LANG=C",
        str(python),
        "-s",
        "-B",
        "-m",
    ]
    assert "-I" not in command and "PYTHONPATH" not in " ".join(command)
    sends: list[tuple[list[str], dict[str, str]]] = []
    monkeypatch.setattr(
        notifier, "_send", lambda argv, env: sends.append((argv, env)) is None or True
    )
    # Root sender accepts the original runner-owned context; it never requires child UID equality.
    monkeypatch.setattr(os, "getuid", lambda: 0 if directory.stat().st_uid != 0 else 12345)
    with pytest.raises(SystemExit) as result:
        _native_cli(command[9:])
    assert result.value.code == 0 and len(sends) == 1
    argv, env = sends[0]
    assert argv[:4] == ["/absolute/docker", "--config", str(state["config"]), "compose"]
    assert env == {
        "PATH": os.defpath,
        "LANG": "C",
        "HOME": str(directory),
        "COMPOSE_PROFILES": "",
        "DOCKER_CONFIG": str(state["config"]),
    }
    for parent_argv, parent_env in state["sends"]:
        assert parent_argv[:4] == argv[:4] and parent_env == env


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "symlink",
        "credentials",
        "plugin",
        "foreign",
        "compose-symlink",
        "compose-hardlink",
        "owner",
        "identity",
        "mixed",
        "percent",
        "whitespace-parent",
        "percent-parent",
        "newline-parent",
    ],
)
def test_amtool_fresh_sender_rejects_changed_context_before_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    directory = tmp_path / "pulseplate-am-only-native-abcdefgh"
    directory.mkdir(mode=0o700)
    compose = directory / "amtool-compose.yaml"
    compose.write_text("services: {}")
    compose.chmod(0o600)
    config = directory / "empty-docker-config"
    config.mkdir(mode=0o700)
    identity = _amtool_fixture_context(compose, config)
    if fault == "missing":
        config.rmdir()
    elif fault == "symlink":
        config.rmdir()
        config.symlink_to(tmp_path, target_is_directory=True)
    elif fault in {"credentials", "plugin"}:
        (config / ("config.json" if fault == "credentials" else "cli-plugins")).write_text(
            "private-sentinel"
        )
    elif fault == "foreign":
        config = tmp_path
    elif fault == "compose-symlink":
        compose.unlink()
        compose.symlink_to(__file__)
    elif fault == "compose-hardlink":
        os.link(compose, directory / "alias")
    elif fault == "owner":
        identity = "999999:" + identity.split(":", 1)[1]
    elif fault == "identity":
        identity += ":1"
    elif fault == "percent":
        config = directory / "empty%20docker-config"
    elif fault in {"whitespace-parent", "percent-parent", "newline-parent"}:
        outer = (
            tmp_path
            / {
                "whitespace-parent": "bad parent",
                "percent-parent": "bad%parent",
                "newline-parent": "bad\nparent",
            }[fault]
        )
        outer.mkdir()
        moved = outer / directory.name
        directory.rename(moved)
        compose, config = moved / compose.name, moved / config.name
    args = [
        "--amtool-fixture-send",
        str(compose),
        "--amtool-fixture-config",
        str(config),
        "--amtool-fixture-context",
        identity,
    ]
    if fault == "mixed":
        args += ["--native"]
    monkeypatch.setattr(shutil, "which", lambda *a: pytest.fail("invalid context resolved Docker"))
    monkeypatch.setattr(
        notifier, "_send", lambda *a, **k: pytest.fail("invalid context sent Docker")
    )
    with pytest.raises((AssertionError, OSError, SystemExit)):
        _native_cli(args)


def test_amtool_preexisting_unit_is_never_stopped_or_deleted(
    amtool_native_lifecycle_io: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    state = amtool_native_lifecycle_io
    units, directory = state["units"], state["directory"]
    assert isinstance(units, Path) and isinstance(directory, Path)
    monkeypatch.setattr(uuid, "uuid4", lambda: SimpleNamespace(hex="a" * 32))
    foreign = units / ("obs2aamtool" + "a" * 32 + ".service")
    foreign.write_text("foreign")
    with pytest.raises(AssertionError, match="AM unit already exists"):
        _native_amtool_lifetime(directory, independent=True)
    assert foreign.read_text() == "foreign" and state["calls"] == []


@pytest.mark.parametrize("failure", ["ordinary", "alarm", "term"])
def test_alertmanager_global_interrupt_bypasses_real_fixture_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    image = "sha256:" + "a" * 64
    seen: list[str] = []
    observation = tmp_path / "observation.json"
    observation.write_text("{}")
    monkeypatch.setattr(sys, "platform", "linux")

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        text = (
            json.dumps(
                {
                    "Id": image,
                    "Os": "linux",
                    "Architecture": "amd64",
                    "Config": {"User": "65534:65534"},
                }
            )
            if "inspect" in argv
            else "version 0.34.1"
        )
        if "--version" in argv:
            binary = (
                argv[argv.index("--entrypoint=/bin/alertmanager")]
                if "--entrypoint=/bin/alertmanager" in argv
                else "--entrypoint=/bin/amtool"
            )
            name = binary.rsplit("/", 1)[1]
            text = (
                name
                + ", version 0.34.1 (branch: HEAD, revision: 73c6bfe7393929211294c1954f30d8ed78e4d0ad)\n"
                "  build user: pulseplate@builder\n  build date: 19700101-00:00:00\n"
                "  go version: go1.27.3\n  platform: linux/amd64\n  tags: netgo\n"
            )
        return subprocess.CompletedProcess(argv, 0, text, "")

    def lifetime(*args: object, **kwargs: object) -> None:
        del args, kwargs
        seen.append("lifetime")
        try:
            if failure == "ordinary":
                raise TimeoutError("private-timeout-sentinel")
            _interrupt_am_native(signal.SIGALRM if failure == "alarm" else signal.SIGTERM, None)
        finally:
            seen.append("cleanup")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(
        sys.modules[__name__], "_native_alertmanager_compose_context", lambda *a: None
    )
    monkeypatch.setattr(sys.modules[__name__], "_native_alertmanager_candidate", lambda *a: None)
    monkeypatch.setattr(sys.modules[__name__], "_native_alertmanager_local_tls", lambda *a: None)
    monkeypatch.setattr(sys.modules[__name__], "_native_amtool_lifetime", lifetime)
    monkeypatch.setattr(
        sys.modules[__name__], "_native_alertmanager", lambda *a: seen.append("smtp")
    )
    with pytest.raises(AssertionError if failure == "ordinary" else SystemExit):
        native_alertmanager_main(
            image, "5dc1025c293763618febeb74c17edcb126ad943f9b20c2296c67847e9f977549", observation
        )
    assert seen == (
        ["lifetime", "cleanup", "smtp"] if failure == "ordinary" else ["lifetime", "cleanup"]
    )
    output = capsys.readouterr().out
    assert (
        "private-timeout-sentinel" not in output
        and "controls=pass" not in output
        and "subset=pass" not in output
    )


def test_alertmanager_cli_uses_process_control_handler_and_preserves_primary_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handlers: dict[int, Callable[..., None]] = {}
    timers: list[float] = []
    monkeypatch.setenv("ALERTMANAGER_NATIVE_SECONDS", "2400")
    monkeypatch.setattr(signal, "signal", lambda key, handler: handlers.update({key: handler}))

    def timer(kind: int, value: float) -> None:
        assert kind == signal.ITIMER_REAL
        timers.append(value)
        if value == 0:
            raise OSError(errno.EIO, "private-timer-cleanup")

    def main(*args: object) -> None:
        del args
        handlers[signal.SIGALRM](signal.SIGALRM, None)

    monkeypatch.setattr(signal, "setitimer", timer)
    monkeypatch.setattr(sys.modules[__name__], "native_alertmanager_main", main)
    with pytest.raises(SystemExit, match="native_AM_phase_interrupted=SIGALRM"):
        _native_cli(
            [
                "--native-alertmanager",
                "--alertmanager-image-id",
                "sha256:" + "a" * 64,
                "--alertmanager-config-sha256",
                "f" * 64,
                "--alertmanager-observation",
                "/synthetic/observation.json",
            ]
        )
    assert handlers[signal.SIGTERM] is handlers[signal.SIGALRM] is _interrupt_am_native
    assert timers == [2400, 0]


def test_alertmanager_safe_primary_metadata_withholds_custom_prose_and_diagnostic_fault(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = PermissionError(errno.EACCES, "private-prose-sentinel", "/private-name-sentinel")
    _native_am_failure("amtool_lifetime", error)
    output = capsys.readouterr().out
    value = json.loads(output)
    assert value["type"] == "PermissionError" and value["errno"] == errno.EACCES
    assert value["errno_name"] == "EACCES" and value["message"] == "withheld"
    assert "private" not in output
    custom = type("private_custom_class_sentinel", (RuntimeError,), {})("private-args")
    _native_am_failure("alertmanager", custom)
    assert json.loads(capsys.readouterr().out)["type"] == "unknown_exception"
    monkeypatch.setattr(
        json, "dumps", lambda *a, **k: (_ for _ in ()).throw(ValueError("private-render"))
    )
    _native_am_failure("alertmanager", custom)
    assert capsys.readouterr().out == "native_AM_failure_metadata_unavailable\n"


@pytest.mark.parametrize("owner", ["smtp", "local"])
def test_alertmanager_actual_TLS_context_floor_precedes_chain_and_preserves_maximum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    owner: str,
) -> None:
    contexts: list[object] = []

    class TLS:
        minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
        maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED

        def load_cert_chain(self, cert: Path, key: Path) -> None:
            assert cert.is_file() and key.is_file()
            assert self.minimum_version == ssl.TLSVersion.TLSv1_2
            assert self.maximum_version == ssl.TLSVersion.MAXIMUM_SUPPORTED
            contexts.append(self)
            raise RuntimeError("synthetic-stop-after-real-TLS-floor")

    class Server:
        daemon_threads = False

        def __init__(self, *args: object) -> None:
            del args

        def server_close(self) -> None:
            return None

    def native(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        assert argv[:2] == ["openssl", "req"]
        for option in ("-keyout", "-out"):
            Path(argv[argv.index(option) + 1]).write_bytes(b"synthetic TLS input")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    monkeypatch.setattr(sys.modules[__name__], "ThreadingHTTPServer", Server)
    monkeypatch.setattr(ssl, "SSLContext", lambda protocol: TLS())
    with pytest.raises(RuntimeError, match="synthetic-stop-after-real-TLS-floor"):
        if owner == "smtp":
            _native_alertmanager(tmp_path)
        else:
            _native_alertmanager_local_tls(tmp_path, "sha256:" + "a" * 64)
    assert len(contexts) == 1


def test_alertmanager_primary_permission_metadata_retains_only_known_repo_frame(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError(errno.EACCES, "private-prose", "/private-path")

    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)
    monkeypatch.setattr(subprocess, "run", denied)
    try:
        _native(["docker", "synthetic"])
    except PermissionError as error:
        _native_am_failure("amtool_lifetime", error)
    else:
        pytest.fail("synthetic transport did not fail")
    value = json.loads(capsys.readouterr().out)
    assert value["errno_name"] == "EACCES" and value["frames"]
    assert all(
        frame["file"] == "tests/test_notify_premium_alias_checkpoint_failure.py"
        and frame["function"] == "_native"
        and type(frame["line"]) is int
        for frame in value["frames"]
    )
    assert "private" not in json.dumps(value)


def test_amtool_primary_global_interruption_survives_real_owned_secondary_cleanup(
    amtool_native_lifecycle_io: dict[str, object],
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = amtool_native_lifecycle_io
    state["fault"], state["secondary"] = "interrupt", "remove"
    directory = state["directory"]
    assert isinstance(directory, Path)
    with pytest.raises(SystemExit, match="native_AM_phase_interrupted=SIGALRM"):
        _native_amtool_lifetime(directory, independent=True)
    calls = state["calls"]
    assert isinstance(calls, list)
    assert any("stop" in call for call in calls)
    assert any(len(call) > 2 and Path(call[2]).name == "rm" for call in calls)
    target = state["target"]
    assert isinstance(target, Path) and target.exists()
    assert all(
        operation in state["released"] for operation in ("shutdown", "close", "join", "container")
    )
    output = capsys.readouterr().out
    assert "private-secondary" not in output and '"errno_name": "EPERM"' in output


def test_alertmanager_failure_metadata_output_error_is_secondary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[str] = []

    class Sink:
        def write(self, value: str) -> None:
            writes.append(value)
            raise OSError(errno.EIO, "private-diagnostic-write")

        def flush(self) -> None:
            return None

    error = PermissionError(errno.EACCES, "private-primary-prose")
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", Sink())
        _native_am_failure("amtool_lifetime", error)
    assert len(writes) == 2
    assert all(
        "private-primary-prose" not in value and "private-diagnostic-write" not in value
        for value in writes
    )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "mount",
        "secret",
        "service-env-accepted",
        "explicit-env-accepted",
        "positive-rejected",
        "unconfigured",
    ],
)
def test_alertmanager_native_compose_context_keeps_real_owner_and_closed_native_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from tests.test_deploy_contract_scripts import (
        FAKE_PROMETHEUS_COMPOSE_JSON,
        _staging_compose_fixture_json,
    )

    from scripts.ci import fetch_docker_source_artifacts as source

    monkeypatch.setattr(
        source,
        "_ALERT_ACCEPTED_CANDIDATE",
        None if fault == "unconfigured" else source._ALERT_HISTORICAL_C10,
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(sys, "platform", "linux")

    def native(
        argv: list[str], *, cwd: Path, check: bool, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        assert not check and timeout == 8
        assert argv[:2] == ["docker", "--config"] and argv[3] == "--host"
        assert argv[5:7] == ["compose", "--env-file"]
        assert argv[8] == "--project-directory" and argv[10] == "-f"
        assert argv[12:] == ["--profile", "*", "config", "--format", "json"]
        assert json.loads((Path(argv[2]) / "config.json").read_text()) == {"auths": {}}
        assert not Path(argv[4].removeprefix("unix://")).exists()
        env_file, project, compose = Path(argv[7]), Path(argv[9]), Path(argv[11])
        assert compose.read_bytes() == (ROOT / "deploy" / compose.name).read_bytes()
        assert project.parent.parent == cwd and compose.parent.parent.name == "payload"
        calls.append(argv)
        if not env_file.exists():
            return subprocess.CompletedProcess(
                argv, 0 if fault == "explicit-env-accepted" else 1, "", str(env_file)
            )
        assert "POSTGRES_PASSWORD=synthetic\n" in env_file.read_text()
        assert "STAGING_ENV_FILE=" + str(project / ".env") + "\n" in env_file.read_text()
        if project.parent.name == "installed":
            assert not (compose.parent / ".env").exists()
        if not (project / ".env").exists():
            return subprocess.CompletedProcess(
                argv, 0 if fault == "service-env-accepted" else 1, "", str(project / ".env")
            )
        model = json.loads(
            _staging_compose_fixture_json(project)
            if "staging" in compose.name
            else FAKE_PROMETHEUS_COMPOSE_JSON
        )
        model["services"]["alertmanager"]["volumes"] = [
            {
                "type": "bind",
                "source": str(
                    (cwd if fault == "mount" else project) / "alertmanager/alertmanager.yml"
                ),
                "target": "/etc/alertmanager/alertmanager.yml",
                "read_only": True,
            }
        ]
        model["secrets"]["alertmanager_smtp_key"]["file"] = str(
            (cwd if fault == "secret" else project) / "secrets/alertmanager_smtp_key"
        )
        return subprocess.CompletedProcess(
            argv,
            1 if fault == "positive-rejected" else 0,
            json.dumps(model),
            "synthetic native output",
        )

    monkeypatch.setattr(sys.modules[__name__], "_native", native)
    if fault == "unconfigured":
        with pytest.raises(ValueError, match="AM_accepted_producer_UNCONFIGURED_HOLD"):
            _native_alertmanager_compose_context(tmp_path)
    elif fault:
        with pytest.raises((AssertionError, SystemExit)):
            _native_alertmanager_compose_context(tmp_path)
    else:
        _native_alertmanager_compose_context(tmp_path)
        assert len(calls) == 9
    assert _AM_NATIVE_DOCKER_CONFIG is None


@pytest.mark.parametrize("producer_image", [False, True])
def test_alertmanager_native_cli_scope_is_explicit_and_never_sets_acceptance(
    monkeypatch: pytest.MonkeyPatch, producer_image: bool
) -> None:
    from scripts.ci import fetch_docker_source_artifacts as source

    monkeypatch.setattr(source, "_ALERT_ACCEPTED_CANDIDATE", None)
    monkeypatch.setenv("ALERTMANAGER_NATIVE_SECONDS", "2400")
    calls: list[dict[str, object]] = []
    timers: list[float] = []

    def main(image: str, config: str, observation: Path | None, **kwargs: object) -> None:
        assert image == "sha256:" + "a" * 64 and config == "b" * 64
        assert observation == Path("/synthetic/observation.json")
        calls.append(kwargs)

    monkeypatch.setattr(sys.modules[__name__], "native_alertmanager_main", main)
    monkeypatch.setattr(signal, "signal", lambda *a: None)
    monkeypatch.setattr(signal, "setitimer", lambda timer, seconds: timers.append(seconds))
    argv = [
        "--native-alertmanager",
        "--alertmanager-image-id",
        "sha256:" + "a" * 64,
        "--alertmanager-config-sha256",
        "b" * 64,
        "--alertmanager-observation",
        "/synthetic/observation.json",
    ]
    if producer_image:
        argv.append("--alertmanager-producer-image")
    _native_cli(argv)
    assert calls == ([{"producer_image": True}] if producer_image else [{}])
    assert timers == [2400, 0]
    assert source._ALERT_ACCEPTED_CANDIDATE is None


@pytest.mark.parametrize(
    "mode_argv,observation",
    [
        (["--native"], True),
        (["--native-alertmanager"], False),
        (["--query-container", "synthetic-prom", "synthetic-app"], True),
        (["--native-fixture", "synthetic"], True),
        (["--amtool-fixture-send", "/synthetic/request"], True),
    ],
)
def test_alertmanager_producer_image_scope_rejects_incomplete_or_other_cli_mode(
    monkeypatch: pytest.MonkeyPatch, mode_argv: list[str], observation: bool
) -> None:
    monkeypatch.setattr(
        sys.modules[__name__],
        "native_alertmanager_main",
        lambda *a, **k: pytest.fail("invalid scope reached native work"),
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "native_main",
        lambda *a, **k: pytest.fail("producer scope escaped to generic consumer"),
    )
    argv = [
        *mode_argv,
        "--alertmanager-producer-image",
        "--alertmanager-image-id",
        "sha256:" + "a" * 64,
        "--alertmanager-config-sha256",
        "b" * 64,
    ]
    if observation:
        argv += ["--alertmanager-observation", "/synthetic/observation.json"]
    with pytest.raises(SystemExit):
        _native_cli(argv)
