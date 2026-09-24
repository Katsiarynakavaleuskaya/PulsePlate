#!/usr/bin/env python3
"""One-shot, read-only observation of the selected private staging stack.

The only remote program is the fixed HOST_PROBE below. Neither this CLI nor
the probe copies a helper to the host or exposes native diagnostic text.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import subprocess  # nosec B404: bounded fixed SSH observer has no stdlib transport replacement (remove-by: 2026-12-31, ref: OPS-03A)
import sys
import time
from typing import BinaryIO, cast

SCHEMA = "pulseplate.staging-runtime-diagnostics.v1"
PROJECT = "/srv/pulseplate-staging"
SSH_BINARY = Path("/usr/bin/ssh")
MAX_OUTPUT = 65536
# Worst-case remote budget: Compose (15) + checker (25) + eight container
# census/inspect calls (8*15) + app probe (15) = 175 seconds. Allow a bounded
# 35-second SSH/scheduling margin without truncating valid slow observations.
SSH_TIMEOUT = 210
REMOTE_ERRORS = frozenset(
    {
        "NATIVE_UNAVAILABLE",
        "NATIVE_TIMEOUT",
        "NATIVE_OUTPUT_OVERSIZE",
        "NATIVE_FAILED",
        "CONTAINER_CENSUS_FAILED",
        "CONTAINER_SELECTION_FAILED",
        "CONTAINER_INSPECT_FAILED",
        "CONTAINER_INSPECT_UNTRUSTED",
        "CONTAINER_IDENTITY_UNTRUSTED",
        "CONTAINER_GENERATION_CHANGED",
        "COMPOSE_RENDER_FAILED",
        "COMPOSE_IDENTITY_UNTRUSTED",
        "STAGING_RECEIPT_FAILED",
        "APP_PROBE_FAILED",
        "REMOTE_PROBE_UNTRUSTED",
    }
)

# This text is sent to the already authenticated host's Python stdin. All
# native argv, SQL, paths and output fields are fixed or selected from the
# trusted staging Compose/checker contract. It never prints subprocess stderr.
HOST_PROBE = r'''
import hashlib
import json
import os
import re
import selectors
import shutil
import subprocess
import sys
import time

PROJECT = "/srv/pulseplate-staging"
COMPOSE = PROJECT + "/docker-compose.staging.yaml"
CHECKER = PROJECT + "/scripts/ops/check_staging_security.py"
MAX_NATIVE = 2_000_000

APP_PROBE = r"""
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlsplit
from urllib.request import urlopen

def http(path):
    try:
        with urlopen("http://127.0.0.1:8000" + path, timeout=3) as response:
            response.read(4096)
            return {"status": "response", "code": response.status}
    except HTTPError as error:
        error.close()
        return {"status": "response", "code": error.code}
    except (TimeoutError, URLError, OSError):
        return {"status": "unreachable", "code": None}

def database():
    try:
        import psycopg
    except ImportError:
        return {"status": "driver_unavailable", "error": "DB_DRIVER_UNAVAILABLE"}
    raw = os.environ.get("DATABASE_URL", "")
    expected_name, expected_user = sys.argv[1:3]
    try:
        parsed = urlsplit(raw)
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        values = dict(pairs)
        user = unquote(parsed.username or "")
        name = unquote(parsed.path.lstrip("/"))
        if (parsed.scheme != "postgresql+psycopg" or parsed.hostname != "postgres"
                or parsed.port != 5432 or parsed.password is not None
                or not re.fullmatch(r"[a-z_][a-z0-9_]*", user)
                or not re.fullmatch(r"[a-z_][a-z0-9_]*", name)
                or name != expected_name or user != expected_user
                or len(values) != len(pairs)
                or values != {"sslmode": "verify-full", "sslrootcert": "/run/secrets/postgres_ca",
                              "passfile": "/run/secrets/postgres_pgpass"}):
            return {"status": "configuration_rejected", "error": "DB_CONFIG_UNTRUSTED"}
    except (ValueError, TypeError):
        return {"status": "configuration_rejected", "error": "DB_CONFIG_UNTRUSTED"}
    connection = None
    try:
        connection = psycopg.connect(host="postgres", port=5432, dbname=name, user=user,
            sslmode="verify-full", sslrootcert="/run/secrets/postgres_ca",
            passfile="/run/secrets/postgres_pgpass", connect_timeout=3,
            options="-c statement_timeout=2000 -c idle_in_transaction_session_timeout=4000")
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("BEGIN READ ONLY")
            try:
                cursor.execute("SELECT current_database(), current_user, current_setting('server_version_num'), pg_is_in_recovery()")
                actual_name, actual_user, version, recovery = cursor.fetchone()
                cursor.execute("SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
                tls_row = cursor.fetchone()
                stats = {"visibility": "unknown", "active": None, "waiting": None, "sessions": None}
                try:
                    cursor.execute("SELECT count(*) FILTER (WHERE pid <> pg_backend_pid() AND state IS NULL), count(*) FILTER (WHERE state = 'active'), count(*) FILTER (WHERE wait_event IS NOT NULL), count(*) FROM pg_stat_activity WHERE datname = current_database()")
                    hidden, active, waiting, sessions = cursor.fetchone()
                    if hidden == 0:
                        stats = {"visibility": "complete", "active": active, "waiting": waiting, "sessions": sessions}
                except psycopg.Error:
                    pass
            finally:
                cursor.execute("ROLLBACK")
        return {"status": "response", "database_match": actual_name == name,
            "role_match": actual_user == user, "server_version": version,
            "in_recovery": recovery, "tls": bool(tls_row and tls_row[0]),
            "tls_version": tls_row[1] if tls_row and tls_row[0] else None,
            "activity": stats}
    except psycopg.Error as error:
        state = error.sqlstate or ""
        if state.startswith("28"):
            code = "DB_AUTH_FAILED"
        else:
            code = "DB_CONNECTION_FAILED"
        return {"status": "unreachable", "error": code}
    finally:
        if connection is not None:
            connection.close()

print(json.dumps({"health": http("/health"), "ready": http("/ready"),
                  "database": database()}, separators=(",", ":")))
"""

def run(argv, *, input_data=None, timeout=15):
    binary = shutil.which(argv[0])
    if binary is None or not os.path.isabs(binary):
        raise RuntimeError("NATIVE_UNAVAILABLE")
    process = subprocess.Popen([binary, *argv[1:]],
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        if process.stdout is None:
            raise RuntimeError("NATIVE_FAILED")
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        offset = 0
        if input_data is not None:
            if process.stdin is None:
                raise RuntimeError("NATIVE_FAILED")
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("NATIVE_TIMEOUT")
            for key, _ in selector.select(remaining):
                if key.fileobj is process.stdout:
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        selector.unregister(process.stdout)
                    else:
                        output.extend(chunk)
                        if len(output) > MAX_NATIVE:
                            raise RuntimeError("NATIVE_OUTPUT_OVERSIZE")
                else:
                    if process.stdin is None or input_data is None:
                        raise RuntimeError("NATIVE_FAILED")
                    try:
                        count = os.write(process.stdin.fileno(), input_data[offset:offset + 8192])
                    except BrokenPipeError:
                        count = len(input_data) - offset
                    offset += count
                    if offset >= len(input_data):
                        selector.unregister(process.stdin)
                        process.stdin.close()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("NATIVE_TIMEOUT")
        return process.wait(timeout=remaining), bytes(output)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("NATIVE_FAILED") from None
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait()

def parse_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))

def selected(service, compose):
    code, raw = run(["docker", "ps", "--quiet", "--no-trunc",
        "--filter", "status=running",
        "--filter", "label=com.docker.compose.project=pulseplate-staging",
        "--filter", "label=com.docker.compose.service=" + service,
        "--filter", "label=com.docker.compose.oneoff=False"])
    if code:
        raise RuntimeError("CONTAINER_CENSUS_FAILED")
    ids = raw.decode("ascii").splitlines()
    if len(ids) != 1 or not re.fullmatch(r"[a-f0-9]{64}", ids[0]):
        raise RuntimeError("CONTAINER_SELECTION_FAILED")
    code, raw = run(["docker", "inspect", ids[0]])
    if code:
        raise RuntimeError("CONTAINER_INSPECT_FAILED")
    values = parse_json(raw)
    if not isinstance(values, list) or len(values) != 1:
        raise RuntimeError("CONTAINER_INSPECT_UNTRUSTED")
    value = values[0]
    config = value["Config"]
    labels = config["Labels"]
    state = value["State"]
    if (value["Id"] != ids[0] or labels.get("com.docker.compose.project") != "pulseplate-staging"
        or labels.get("com.docker.compose.service") != service
        or labels.get("com.docker.compose.oneoff") != "False"
        or not state["Running"] or state["Status"] != "running"
        or config["Image"] != compose["services"][service]["image"]):
        raise RuntimeError("CONTAINER_IDENTITY_UNTRUSTED")
    image = value["Image"]
    config_hash = labels.get("com.docker.compose.config-hash")
    started = state["StartedAt"]
    if (not re.fullmatch(r"sha256:[a-f0-9]{64}", image)
        or not re.fullmatch(r"[a-f0-9]{64}", config_hash or "")
        or not isinstance(started, str) or not started or started.startswith("0001-")):
        raise RuntimeError("CONTAINER_IDENTITY_UNTRUSTED")
    return {"id": ids[0], "image": image, "config_hash": config_hash, "started_at": started}

def main():
    try:
        code, raw = run(["docker", "compose", "--project-directory", PROJECT,
            "-f", COMPOSE, "--env-file", PROJECT + "/.env", "--profile", "*",
            "config", "--format", "json"])
        if code:
            raise RuntimeError("COMPOSE_RENDER_FAILED")
        compose = parse_json(raw)
        if compose.get("name") != "pulseplate-staging":
            raise RuntimeError("COMPOSE_IDENTITY_UNTRUSTED")
        db_environment = compose["services"]["postgres"]["environment"]
        expected_name = db_environment["POSTGRES_DB"]
        expected_user = db_environment["POSTGRES_USER"]
        if (not isinstance(expected_name, str) or not isinstance(expected_user, str)
            or not re.fullmatch(r"[a-z_][a-z0-9_]*", expected_name)
            or not re.fullmatch(r"[a-z_][a-z0-9_]*", expected_user)):
            raise RuntimeError("COMPOSE_IDENTITY_UNTRUSTED")
        code, _ = run(["/usr/bin/python3", CHECKER, "--project-dir", PROJECT,
            "--compose-stdin"], input_data=raw, timeout=25)
        if code:
            raise RuntimeError("STAGING_RECEIPT_FAILED")
        app_before = selected("app", compose)
        db_before = selected("postgres", compose)
        code, raw = run(["docker", "exec", "-i", app_before["id"],
            "python", "-c", APP_PROBE, expected_name, expected_user], timeout=15)
        if code or len(raw) > 65536:
            raise RuntimeError("APP_PROBE_FAILED")
        observation = parse_json(raw)
        app_after = selected("app", compose)
        db_after = selected("postgres", compose)
        if app_before != app_after or db_before != db_after:
            raise RuntimeError("CONTAINER_GENERATION_CHANGED")
        identity = json.dumps({"app": app_before, "postgres": db_before},
            sort_keys=True, separators=(",", ":")).encode()
        print(json.dumps({"schema": "pulseplate.staging-runtime-host.v1", "trust": "accepted",
            "fingerprint": hashlib.sha256(identity).hexdigest(), "observation": observation},
            separators=(",", ":")))
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            subprocess.SubprocessError, RuntimeError) as error:
        code = str(error) if isinstance(error, RuntimeError) else "REMOTE_PROBE_UNTRUSTED"
        if code not in {"NATIVE_UNAVAILABLE", "NATIVE_TIMEOUT", "NATIVE_OUTPUT_OVERSIZE",
            "NATIVE_FAILED", "CONTAINER_CENSUS_FAILED", "CONTAINER_SELECTION_FAILED",
            "CONTAINER_INSPECT_FAILED", "CONTAINER_INSPECT_UNTRUSTED",
            "CONTAINER_IDENTITY_UNTRUSTED", "CONTAINER_GENERATION_CHANGED",
            "COMPOSE_RENDER_FAILED", "COMPOSE_IDENTITY_UNTRUSTED",
            "STAGING_RECEIPT_FAILED", "APP_PROBE_FAILED"}:
            code = "REMOTE_PROBE_UNTRUSTED"
        print(json.dumps({"schema": "pulseplate.staging-runtime-host.v1", "trust": "rejected",
            "error": code}, separators=(",", ":")))

main()
'''


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _parse_json(raw: bytes) -> object:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")),
        )
    except RecursionError as error:
        raise ValueError("recursive JSON") from error


def _host_valid(value: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", value):
        return True
    try:
        return isinstance(ipaddress.ip_address(value), ipaddress.IPv6Address)
    except ValueError:
        return False


def _ssh_argv(host: str, home: Path) -> list[str]:
    if not SSH_BINARY.is_file():
        raise RuntimeError("SSH_UNAVAILABLE")
    ssh_dir = home / ".ssh"
    key = ssh_dir / "pulseplate_staging_obs1_20260824"
    known = ssh_dir / "known_hosts_pulseplate_staging_obs1_20260824"
    try:
        directory = ssh_dir.lstat()
        if (
            not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) != 0o700
        ):
            raise RuntimeError("SSH_IDENTITY_UNAVAILABLE")
        for path in (key, known):
            entry = path.lstat()
            if (
                not stat.S_ISREG(entry.st_mode)
                or entry.st_uid != os.getuid()
                or entry.st_nlink != 1
                or stat.S_IMODE(entry.st_mode) != 0o600
            ):
                raise RuntimeError("SSH_IDENTITY_UNAVAILABLE")
    except OSError as error:
        raise RuntimeError("SSH_IDENTITY_UNAVAILABLE") from error
    return [
        str(SSH_BINARY),
        "-F",
        "/dev/null",
        "-i",
        str(key),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile=" + str(known),
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        "ProxyCommand=none",
        "-o",
        "ProxyJump=none",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=2",
        "-l",
        "pulseplate-ops",
        "--",
        host,
        "sudo -n /usr/bin/python3 -",
    ]


def _ssh_observe(argv: list[str]) -> bytes:
    """Stream a bounded result and kill only this owned SSH process on failure."""
    try:
        process = subprocess.Popen(  # nosec B603: fixed strict SSH argv, no shell (remove-by: 2026-12-31, ref: OPS-03A)
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise RuntimeError("SSH_TRANSPORT_FAILED") from error
    selector = selectors.DefaultSelector()
    output = bytearray()
    source = HOST_PROBE.encode("utf-8")
    offset = 0
    deadline = time.monotonic() + SSH_TIMEOUT
    try:
        stdout = cast(BinaryIO, process.stdout)
        stdin = cast(BinaryIO, process.stdin)
        os.set_blocking(stdout.fileno(), False)
        os.set_blocking(stdin.fileno(), False)
        selector.register(stdout, selectors.EVENT_READ)
        selector.register(stdin, selectors.EVENT_WRITE)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("SSH_TRANSPORT_FAILED")
            for key, _ in selector.select(remaining):
                if key.fileobj is process.stdout:
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        selector.unregister(process.stdout)
                    else:
                        output.extend(chunk)
                        if len(output) > MAX_OUTPUT:
                            raise RuntimeError("SSH_TRANSPORT_FAILED")
                else:
                    try:
                        count = os.write(process.stdin.fileno(), source[offset : offset + 8192])
                    except BrokenPipeError:
                        count = len(source) - offset
                    offset += count
                    if offset >= len(source):
                        selector.unregister(process.stdin)
                        process.stdin.close()
        remaining = deadline - time.monotonic()
        if remaining <= 0 or process.wait(timeout=remaining) != 0 or not output:
            raise RuntimeError("SSH_TRANSPORT_FAILED")
        return bytes(output)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("SSH_TRANSPORT_FAILED") from error
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait()


def _valid_http(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"status", "code"}
        and value["status"] in {"response", "unreachable"}
        and (
            (
                value["status"] == "response"
                and type(value["code"]) is int
                and 100 <= value["code"] <= 599
            )
            or (value["status"] == "unreachable" and value["code"] is None)
        )
    )


def _validate_observation(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"health", "ready", "database"}:
        raise ValueError("observation shape")
    if not _valid_http(value["health"]) or not _valid_http(value["ready"]):
        raise ValueError("http shape")
    db = value["database"]
    if not isinstance(db, dict) or db.get("status") not in {
        "response",
        "unreachable",
        "driver_unavailable",
        "configuration_rejected",
    }:
        raise ValueError("database shape")
    if db["status"] == "response":
        if set(db) != {
            "status",
            "database_match",
            "role_match",
            "server_version",
            "in_recovery",
            "tls",
            "tls_version",
            "activity",
        }:
            raise ValueError("database fields")
        if any(
            type(db[key]) is not bool
            for key in ("database_match", "role_match", "in_recovery", "tls")
        ):
            raise ValueError("database booleans")
        if not isinstance(db["server_version"], str) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+){0,3}", db["server_version"]
        ):
            raise ValueError("server version")
        if db["tls_version"] is not None and db["tls_version"] not in {"TLSv1.2", "TLSv1.3"}:
            raise ValueError("tls version")
        stats = db["activity"]
        if (
            not isinstance(stats, dict)
            or set(stats) != {"visibility", "active", "waiting", "sessions"}
            or stats["visibility"] not in {"complete", "unknown"}
        ):
            raise ValueError("activity shape")
        if stats["visibility"] == "unknown":
            if any(stats[key] is not None for key in ("active", "waiting", "sessions")):
                raise ValueError("unknown activity")
        elif any(
            type(stats[key]) is not int or stats[key] < 0
            for key in ("active", "waiting", "sessions")
        ):
            raise ValueError("activity counts")
    else:
        if set(db) != {"status", "error"} or db["error"] not in {
            "DB_DRIVER_UNAVAILABLE",
            "DB_CONFIG_UNTRUSTED",
            "DB_AUTH_FAILED",
            "DB_TLS_FAILED",
            "DB_CONNECTION_FAILED",
        }:
            raise ValueError("database error")
        if db["status"] == "configuration_rejected":
            raise RuntimeError("DB_CONFIG_UNTRUSTED")
        if db["status"] == "driver_unavailable":
            raise RuntimeError("DB_DRIVER_UNAVAILABLE")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _report(
    payload: object, *, started_at: str | None = None, completed_at: str | None = None
) -> dict[str, object]:
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "pulseplate.staging-runtime-host.v1"
    ):
        raise ValueError("host payload")
    if payload.get("trust") == "rejected":
        if (
            set(payload) != {"schema", "trust", "error"}
            or not isinstance(payload["error"], str)
            or payload["error"] not in REMOTE_ERRORS
        ):
            raise ValueError("host rejection")
        raise RuntimeError(payload["error"])
    if (
        set(payload) != {"schema", "trust", "fingerprint", "observation"}
        or payload["trust"] != "accepted"
        or not isinstance(payload["fingerprint"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", payload["fingerprint"])
    ):
        raise ValueError("host identity")
    observation = _validate_observation(payload["observation"])
    db = cast(dict[str, object], observation["database"])
    failures: list[str] = []
    unknowns: list[str] = []
    for path in ("health", "ready"):
        item = cast(dict[str, object], observation[path])
        if item["status"] != "response" or item["code"] != 200:
            failures.append(path.upper() + "_NOT_OK")
    if db["status"] != "response":
        failures.append(str(db["error"]))
    else:
        if not db["database_match"] or not db["role_match"]:
            raise RuntimeError("DB_IDENTITY_MISMATCH")
        if not db["tls"]:
            raise RuntimeError("DB_TLS_UNVERIFIED")
        stats = cast(dict[str, object], db["activity"])
        if stats["visibility"] == "unknown":
            unknowns.append("db.activity")
    status = "degraded" if failures else "partial" if unknowns else "complete"
    completion = completed_at or _utc_now()
    start = started_at or completion
    return {
        "schema": SCHEMA,
        "observed_at": completion,
        "observation_window": {"started_at": start, "completed_at": completion},
        "environment": "staging",
        "scope": "host-app-postgres",
        "fingerprint": payload["fingerprint"],
        "status": status,
        "http": {"health": observation["health"], "ready": observation["ready"]},
        "database": db,
        "unknowns": unknowns,
        "errors": failures,
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("INVALID_ARGUMENT")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--format", required=True)
    try:
        args = parser.parse_args(argv)
        if args.environment != "staging" or args.format != "json":
            raise ValueError("INVALID_ARGUMENT")
        host = os.environ.get("SSH_HOST_STAGING", "")
        if not host or not _host_valid(host):
            raise ValueError("INVALID_STAGING_HOST")
        ssh_argv = _ssh_argv(host, Path.home())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 3
    try:
        started_at = _utc_now()
        raw = _ssh_observe(ssh_argv)
        completed_at = _utc_now()
        report = _report(_parse_json(raw), started_at=started_at, completed_at=completed_at)
    except (ValueError, TypeError, RuntimeError, UnicodeError) as error:
        code = str(error) if isinstance(error, RuntimeError) else "REMOTE_OUTPUT_UNTRUSTED"
        if code not in REMOTE_ERRORS | {
            "SSH_TRANSPORT_FAILED",
            "DB_CONFIG_UNTRUSTED",
            "DB_DRIVER_UNAVAILABLE",
            "DB_IDENTITY_MISMATCH",
            "DB_TLS_UNVERIFIED",
        }:
            code = "REMOTE_OUTPUT_UNTRUSTED"
        print(code, file=sys.stderr)
        return 3
    print(json.dumps(report, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
