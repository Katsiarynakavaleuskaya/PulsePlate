#!/usr/bin/env python3
"""Submit one bounded failure event; expiry does not assert checkpoint recovery."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NoReturn, Sequence

EVENT_SECONDS = 900
INTERVAL_SECONDS = 60
MAX_ATTEMPTS = 15
COMMAND_TIMEOUT_SECONDS = 10
CLEANUP_TIMEOUT_SECONDS = 1
RUNBOOK_URL = (
    "https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/"
    "docs/deploy/OPERATIONAL_SIGNALS.md#daily-checkpoint"
)
SUMMARY = "PulsePlate checkpoint failed; inspect the service journal and canonical evidence."
ERROR = "checkpoint_failure_notification_error"


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _argv(docker: str, compose_file: Path, environment: str, start: str, end: str) -> list[str]:
    return [
        docker,
        "compose",
        "-f",
        os.fspath(compose_file),
        "exec",
        "-T",
        "alertmanager",
        "/bin/amtool",
        "--alertmanager.url=http://127.0.0.1:9093",
        "--timeout=10s",
        "--no-version-check",
        "alert",
        "add",
        f"--start={start}",
        f"--end={end}",
        f"--annotation=summary={SUMMARY}",
        f"--annotation=runbook={RUNBOOK_URL}",
        "alertname=PulsePlateAliasCheckpointFailed",
        f"environment={environment}",
        "alias=all",
        "severity=warning",
    ]


async def _stop(process: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        # A vanished group still requires a bounded native child reap.
        await _reap(process)
        return
    await _reap(process)


async def _reap(process: asyncio.subprocess.Process) -> None:
    try:
        await asyncio.wait_for(process.wait(), timeout=CLEANUP_TIMEOUT_SECONDS)
    except (TimeoutError, asyncio.TimeoutError):
        raise OSError("notification_cleanup_incomplete") from None


async def _send_async(argv: list[str]) -> bool:
    # The native client owns request timeout; this owns only its host group.
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    try:
        return await asyncio.wait_for(process.wait(), timeout=COMMAND_TIMEOUT_SECONDS) == 0
    except (TimeoutError, asyncio.TimeoutError):
        await _stop(process)
        return False
    except asyncio.CancelledError:
        cleanup = asyncio.create_task(_stop(process))
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                if cleanup.done():
                    break
            except OSError:
                # Retrieve and report the completed cleanup task below.
                break
        try:
            cleanup.result()
        except OSError:
            # Report secondary cleanup failure without replacing cancellation.
            print(ERROR, flush=True)
        raise


def _send(argv: list[str]) -> bool:
    return asyncio.run(_send_async(argv))


def notify(*, docker: str, compose_file: Path, environment: str) -> int:
    start_wall = datetime.now(timezone.utc)
    end_wall = start_wall + timedelta(seconds=EVENT_SECONDS)
    epoch = time.monotonic()
    argv = _argv(docker, compose_file, environment, _timestamp(start_wall), _timestamp(end_wall))
    failed = False
    attempts = 0
    for slot in range(MAX_ATTEMPTS):
        target = epoch + slot * INTERVAL_SECONDS
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        now = time.monotonic()
        wall = datetime.now(timezone.utc)
        if wall < start_wall:
            print(ERROR, flush=True)
            failed = True
            break
        if now >= epoch + EVENT_SECONDS or wall >= end_wall:
            break
        # Missed slots are omitted rather than replayed as a burst after suspension.
        if now >= target + INTERVAL_SECONDS:
            continue
        attempts += 1
        if not _send(argv):
            failed = True
            print(ERROR, flush=True)
    if attempts == 0:
        if not failed:
            print(ERROR, flush=True)
        return 1
    return 1 if failed else 0


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, ERROR + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--compose-file", required=True, type=Path)
    parser.add_argument("--environment", required=True, choices=("staging", "production"))
    args = parser.parse_args(argv)
    docker = shutil.which("docker")
    if docker is None or not os.path.isabs(docker) or not os.access(docker, os.X_OK):
        print(ERROR)
        return 1
    try:
        return notify(docker=docker, compose_file=args.compose_file, environment=args.environment)
    except (OSError, KeyboardInterrupt):
        print(ERROR)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
