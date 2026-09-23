#!/usr/bin/env python3
"""Bounded native smoke of the actual candidate scheduler; no host deployment."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import os
import re
import selectors
import shutil
import subprocess  # nosec B404: # bounded native Docker protocol has no safer replacement (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
import tarfile
import time
from typing import Any
import uuid

OUTPUT_LIMIT = 1024 * 1024
COMMAND_SECONDS = 30
TOTAL_SECONDS = 240
CYCLE_SECONDS = 60
SURVIVAL_SECONDS = 5
PG_SCRATCH = "/run/pulseplate-scheduler-smoke"
LEASE_KEY = 5788616816583527508
FORBIDDEN_ENV = {
    "CI",
    "GITHUB_ACTIONS",
    "PYTEST_CURRENT_TEST",
    "PYTEST_XDIST_WORKER",
    "TESTING",
    "DEBUG",
    "ALLOW_DEV_API_KEY",
    "ALLOW_ANONYMOUS_API_KEYS",
    "EXPORT_TOKEN_SECRET",
    "PYTHONSTARTUP",
    "PYTHONHOME",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "USDA_API_KEY",
}

IMAGE_ENV_KEYS = {
    "PATH",
    "LANG",
    "GPG_KEY",
    "PYTHON_VERSION",
    "PYTHON_SHA256",
    "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONPATH",
    "MPLCONFIGDIR",
}


class SmokeError(RuntimeError):
    """A missing native observation is a failure, not an inferred success."""


def capture_bytes(argv: list[str], timeout: float, limit: int = OUTPUT_LIMIT) -> bytes:
    """Bound the combined stream while reading, including failed commands."""
    if not argv or not os.path.isabs(argv[0]):
        raise SmokeError("Native command requires an absolute executable")
    if timeout <= 0:
        raise SmokeError("Native execution deadline exceeded")
    data = bytearray()
    end = time.monotonic() + timeout
    with subprocess.Popen(  # nosec B603: # absolute argv, shell=False and bounded streams; native CLI required (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False
    ) as process:
        try:
            if process.stdout is None:
                raise SmokeError("Native command output pipe is unavailable")
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = end - time.monotonic()
                    if remaining <= 0:
                        raise SmokeError("Native command timed out")
                    for key, _ in selector.select(min(remaining, 0.2)):
                        chunk = os.read(key.fd, min(65536, limit + 1 - len(data)))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        data.extend(chunk)
                        if len(data) > limit:
                            raise SmokeError("Native output exceeded its complete-output bound")
            status = process.wait(timeout=max(0.01, end - time.monotonic()))
        except BaseException:
            process.kill()
            process.wait()
            raise
    if status:
        raise SmokeError(
            f"Native command failed ({status}): {data[-3000:].decode(errors='replace')}"
        )
    return bytes(data)


def capture(argv: list[str], timeout: float, limit: int = OUTPUT_LIMIT) -> str:
    """Require lossless text for native evidence; binary is only the passwd archive."""
    try:
        return capture_bytes(argv, timeout, limit).decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SmokeError("Native output is not UTF-8") from exc


def environment(values: object) -> dict[str, str]:
    """Read the finite Docker Env projection without accepting duplicate keys."""
    if not isinstance(values, list):
        raise SmokeError("Missing native environment")
    result: dict[str, str] = {}
    for entry in values:
        if not isinstance(entry, str) or "=" not in entry:
            raise SmokeError("Malformed native environment")
        key, value = entry.split("=", 1)
        if not key or key in result:
            raise SmokeError("Ambiguous native environment")
        result[key] = value
    return result


def check_worker_environment(values: object, expected: dict[str, str] | None = None) -> None:
    """Presence-based runtime bypasses are forbidden even when set to false."""
    env = environment(values)
    if FORBIDDEN_ENV.intersection(env) or any(
        key.startswith(("PYTEST_", "AWS_", "GITHUB_", "GH_", "DEVPI_")) for key in env
    ):
        raise SmokeError("Worker environment contains a bypass or ambient credential")
    if set(env) - IMAGE_ENV_KEYS - set(expected or {}):
        raise SmokeError("Worker environment contains an unadmitted key")
    if env.get("PYTHONPATH", "/app") != "/app":
        raise SmokeError("Worker Python path was injected")
    if expected and any(env.get(key) != value for key, value in expected.items()):
        raise SmokeError("Worker effective environment differs from the synthetic contract")


def worker_identity(info: dict[str, Any], image: str) -> tuple[object, ...]:
    """Observe one live process, never a restart loop or API health status."""
    state = info.get("State", {})
    pid = state.get("Pid")
    if (
        info.get("Image") != image
        or state.get("Running") is not True
        or state.get("OOMKilled") is not False
        or type(info.get("RestartCount")) is not int
        or info.get("RestartCount") != 0
        or type(pid) is not int
        or pid <= 0
        or not state.get("StartedAt")
        or not isinstance(info.get("Id"), str)
    ):
        raise SmokeError("Worker exited, restarted, changed image, or has invalid native state")
    return info["Id"], image, pid, state["StartedAt"]


def lease_session(log: str, application: str, database: str) -> tuple[int, str] | None:
    """Recognize only the fixed PG15 stderr prefix and bound parameterized calls."""
    events: list[tuple[int, str, str]] = []
    pending: tuple[int, str, str] | None = None
    prefix = re.compile(r"^(\d+)\|([0-9a-f]+\.[0-9a-f]+)\|([^|]*)\|([^|]*)\|")
    for line in log.splitlines():
        match = prefix.match(line)
        if not match or match[3] != application or match[4] != database:
            continue
        message = line[match.end() :].strip()
        if re.match(r"(?:ERROR|FATAL|PANIC|WARNING):", message):
            raise SmokeError("PostgreSQL reported a worker-session error")
        for operation in ("pg_try_advisory_lock", "pg_advisory_unlock"):
            if re.fullmatch(
                rf"LOG:\s+(?:statement:|execute <unnamed>:) SELECT {operation}\(\$1\)",
                message,
            ):
                if pending is not None:
                    raise SmokeError("Missing PostgreSQL lease parameters")
                pending = int(match[1]), match[2], operation
        if message.startswith("DETAIL:") and pending:
            if (int(match[1]), match[2]) != pending[:2] or message != (
                f"DETAIL:  parameters: $1 = '{LEASE_KEY}'"
            ):
                raise SmokeError("PostgreSQL lease key/session mismatch")
            events.append(pending)
            pending = None
    if not events or len(events) == 1 or pending:
        return None
    if (
        len(events) != 2
        or events[0][2] != "pg_try_advisory_lock"
        or (events[1][:2] != events[0][:2] or events[1][2] != "pg_advisory_unlock")
    ):
        raise SmokeError("Ambiguous native worker lease sequence")
    return events[0][:2]


def check_logs(log: str, *, stopped: bool = False) -> bool:
    """Complete worker logs must show useful work and no caught failure."""
    if any(
        value in log
        for value in (
            " ERROR ",
            " WARNING ",
            "Traceback",
            "Running update for ",
            "shared lease is held",
            "Error checking ",
        )
    ):
        raise SmokeError("Worker output contains a failed or supplier-update attempt")
    if stopped and not all(
        value in log
        for value in (
            "Received signal 15, initiating graceful shutdown",
            "Database update scheduler stopped",
        )
    ):
        raise SmokeError("Worker did not report graceful SIGTERM completion")
    return "Checking for database updates..." in log and "No database updates available" in log


def check_session(row: object, session: tuple[int, str], previous: object = None) -> object:
    """Disconnection/invalidation cannot masquerade as normal unlock."""
    if not isinstance(row, dict) or (
        row.get("pid") != session[0]
        or row.get("session") != session[1]
        or row.get("state") != "idle"
        or row.get("xact_start") is not None
        or row.get("locked") is not False
        or not isinstance(row.get("backend_start"), str)
    ):
        raise SmokeError("Worker PostgreSQL backend is absent, replaced, busy or still locked")
    identity = row["pid"], row["backend_start"], row["session"]
    if previous is not None and identity != previous:
        raise SmokeError("Worker PostgreSQL backend identity changed")
    return identity


class Smoke:
    """Own only the fixed smoke's disposable Docker objects."""

    def __init__(self) -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise SmokeError("Docker executable is unavailable")
        self.docker = docker
        self.end = time.monotonic() + TOTAL_SECONDS
        self.prefix = "scheduler-smoke-" + uuid.uuid4().hex
        self.resources: list[tuple[str, str]] = []
        self.log_snapshots: dict[str, str] = {}

    def run(self, *args: str) -> str:
        return capture([self.docker, *args], min(COMMAND_SECONDS, self.end - time.monotonic()))

    def logs(self, name: str) -> str:
        """Require complete, append-only Docker logs (no tail/since/rotation)."""
        value = self.run("logs", name)
        previous = self.log_snapshots.get(name, "")
        if not value.startswith(previous):
            raise SmokeError("Native log history was truncated or replaced")
        self.log_snapshots[name] = value
        return value

    def inspect(self, kind: str, name: str) -> dict[str, Any]:
        result = json.loads(self.run(kind, "inspect", name))
        if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
            raise SmokeError("Invalid Docker inspection")
        return result[0]

    def create(self, kind: str, name: str, *args: str) -> str:
        label = f"pulseplate.scheduler-smoke={self.prefix}"
        result = (
            self.run(kind, "create", "--label", label, *args, name)
            if kind != "container"
            else self.run("create", "--name", name, "--label", label, *args)
        ).strip()
        if kind == "volume":
            if result != name:
                raise SmokeError("Unexpected created volume identity")
        elif re.fullmatch(r"[0-9a-f]{64}", result) is None:
            raise SmokeError("Missing immutable created resource identity")
        self.resources.append((kind, result))
        return result

    def cleanup(self) -> list[str]:
        self.end = time.monotonic() + COMMAND_SECONDS
        failures: list[str] = []
        for kind, identity in reversed(self.resources):
            try:
                if kind == "volume":
                    labels = self.inspect("volume", identity).get("Labels") or {}
                    if labels.get("pulseplate.scheduler-smoke") != self.prefix:
                        raise SmokeError("Volume ownership changed")
                args = ("--force", "--volumes") if kind == "container" else ()
                self.run(kind, "rm", *args, identity)
                listing = (
                    ["--all", "--no-trunc"]
                    if kind == "container"
                    else (["--no-trunc"] if kind == "network" else [])
                )
                identities = self.run(
                    kind, "ls", *listing, "--format", "{{.Name}}" if kind == "volume" else "{{.ID}}"
                )
                if identity in identities.splitlines():
                    raise SmokeError("Owned resource remains after removal")
            except Exception as exc:
                failures.append(f"{kind} {identity}: {exc}")
        return failures

    def account(self, image: str, account: str) -> tuple[str, str]:
        """Inspect passwd bytes without running the image's default root entrypoint."""
        name = self.prefix + "-account-" + account
        mounts = ["--tmpfs", "/var/lib/postgresql/data"] if account == "postgres" else []
        self.create(
            "container", name, "--network", "none", *mounts, "--entrypoint", "/bin/false", image
        )
        archive_bytes = capture_bytes(
            [self.docker, "cp", name + ":/etc/passwd", "-"],
            min(COMMAND_SECONDS, self.end - time.monotonic()),
        )
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1 or not members[0].isfile() or members[0].size > 65536:
                raise SmokeError("Invalid image passwd inventory")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise SmokeError("Native image account stream is unavailable")
            rows = [line.split(":") for line in stream.read().decode().splitlines()]
        selected = [row for row in rows if row[0] == account and len(row) == 7]
        if len(selected) != 1 or not all(re.fullmatch(r"[1-9][0-9]*", x) for x in selected[0][2:4]):
            raise SmokeError("Image has no unambiguous non-root account")
        return selected[0][2], selected[0][3]

    def mounts(self, name: str, expected: dict[str, str], network: str) -> None:
        info = self.inspect("container", name)
        actual = {row["Destination"]: row for row in info["Mounts"]}
        # Docker reports explicit tmpfs through HostConfig before start, Mounts after start.
        tmpfs = info["HostConfig"].get("Tmpfs") or {}
        destinations = set(actual) | set(tmpfs)
        if destinations != set(expected):
            raise SmokeError("Unreconciled writable or implicit container mount")
        for destination, source in expected.items():
            if source != "tmpfs" and (
                actual.get(destination, {}).get("Type") != "volume"
                or actual[destination].get("Name") != source
            ):
                raise SmokeError("Container storage is not its owned scratch volume")
            if (
                source == "tmpfs"
                and destination in actual
                and actual[destination]["Type"] != "tmpfs"
            ):
                raise SmokeError("Container tmpfs was replaced")
        if info["HostConfig"].get("PortBindings") or info["HostConfig"].get("Privileged"):
            raise SmokeError("Container gained ingress or privilege")
        if info["HostConfig"]["NetworkMode"] != network:
            raise SmokeError("Container network differs from isolated fixture")
        if (
            info.get("State", {}).get("Running") is True
            and network != "none"
            and set(info.get("NetworkSettings", {}).get("Networks", {})) != {network}
        ):
            raise SmokeError("Running container has an unexpected network attachment")

    def exercise(
        self,
        image: str,
        pg_image: str,
        runtime: str,
        pg_user: tuple[str, str],
        worker_user: tuple[str, str],
    ) -> None:
        prefix = self.prefix + "-" + runtime
        network, cache, pg, seed, worker = [
            prefix + suffix
            for suffix in (
                "-network",
                "-cache",
                "-pg",
                "-seed",
                "-worker",
            )
        ]
        database = "workerdb"
        application = "scheduler_smoke_worker"
        self.create("network", network, "--internal")
        if self.inspect("network", network).get("Internal") is not True:
            raise SmokeError("Fixture network is not internal")
        self.create("volume", cache)
        safe = [
            "--pull",
            "never",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "256",
            "--restart",
            "no",
            "--no-healthcheck",
        ]
        pg_tmp = []
        for path in ("/var/lib/postgresql/data", "/var/run/postgresql", PG_SCRATCH):
            pg_tmp.extend(
                ["--tmpfs", f"{path}:uid={pg_user[0]},gid={pg_user[1]},mode=0700,size=256m"]
            )
        self.create(
            "container",
            pg,
            *safe,
            "--user",
            ":".join(pg_user),
            "--network",
            network,
            *pg_tmp,
            "-e",
            "POSTGRES_PASSWORD=synthetic-fixture-password",  # pragma: allowlist secret -- Disposable fixture only.
            "-e",
            f"TMPDIR={PG_SCRATCH}",
            "-e",
            "PGDATA=/var/lib/postgresql/data/pgdata",
            pg_image,
            "postgres",
            "-c",
            "log_statement=all",
            "-c",
            "logging_collector=off",
            "-c",
            "log_line_prefix=%p|%c|%a|%d|",
            "-c",
            "log_parameter_max_length=-1",
        )
        self.mounts(
            pg,
            {p: "tmpfs" for p in ("/var/lib/postgresql/data", "/var/run/postgresql", PG_SCRATCH)},
            network,
        )
        self.run("start", pg)

        def sql(statement: str, db: str = "postgres") -> str:
            return self.run(
                "exec",
                "-e",
                "PGAPPNAME=scheduler_smoke_observer",
                "-e",
                "PGPASSWORD=synthetic-fixture-password",  # pragma: allowlist secret -- Disposable fixture only.
                pg,
                "psql",
                "-h",
                "127.0.0.1",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-At",
                "-U",
                "postgres",
                "-d",
                db,
                "-c",
                statement,
            ).strip()

        pg_info = self.inspect("container", pg)
        if pg_info["Image"] != pg_image or pg_info["Config"]["User"] != ":".join(pg_user):
            raise SmokeError("PostgreSQL process identity/user mismatch")
        self.mounts(
            pg,
            {p: "tmpfs" for p in ("/var/lib/postgresql/data", "/var/run/postgresql", PG_SCRATCH)},
            network,
        )
        ready_end = min(self.end, time.monotonic() + CYCLE_SECONDS)
        last_error = "PostgreSQL TCP server did not become ready"
        while time.monotonic() < ready_end:
            try:
                ready = sql("SELECT 1")
            except SmokeError as exc:
                last_error = str(exc)
                time.sleep(0.5)
                continue
            if ready != "1":
                raise SmokeError("Invalid native PostgreSQL readiness output")
            break
        else:
            raise SmokeError(last_error)
        if not sql("SHOW server_version").startswith("15."):
            raise SmokeError("Fixture is not the admitted PostgreSQL major")
        sql(
            "CREATE ROLE smoke_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOREPLICATION PASSWORD 'synthetic-worker-password'"
        )
        sql("CREATE DATABASE workerdb OWNER smoke_worker")
        sql("CREATE EXTENSION vector", database)
        env = {
            "APP_ENV": runtime,
            "ENVIRONMENT": runtime,
            "FOOD_UPDATE_SCHEDULER_MODE": "external",
            "PRIVATE_EXPORTS_ENABLED": "false",
            "DATABASE_URL": f"postgresql+psycopg://smoke_worker:synthetic-worker-password@{pg}:5432/{database}"  # pragma: allowlist secret -- Disposable non-superuser fixture only.
            f"?application_name={application}&connect_timeout=5",
        }
        env_args = [item for key, value in env.items() for item in ("-e", key + "=" + value)]
        versions = {
            source: {
                "source": source,
                "version": "synthetic-current",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "record_count": 0,
                "checksum": "synthetic",
                "metadata": {},
            }
            for source in ("usda", "openfoodfacts")
        }
        seed_code = (
            "from pathlib import Path; p=Path('/app/cache/food_db'); p.mkdir(exist_ok=True); "
            + ("(p/'database_versions.json').write_text(" + repr(json.dumps(versions)) + ")")
        )
        self.create(
            "container",
            seed,
            *safe,
            "--network",
            "none",
            "--mount",
            f"type=volume,source={cache},target=/app/cache",
            image,
            "python",
            "-c",
            seed_code,
        )
        self.mounts(seed, {"/app/cache": cache}, "none")
        self.run("start", "--attach", seed)
        self.create(
            "container",
            worker,
            *safe,
            "--network",
            network,
            "--mount",
            f"type=volume,source={cache},target=/app/cache",
            *env_args,
            image,
            "python",
            "-m",
            "core.food_apis.scheduler",
            "--serve",
        )
        info = self.inspect("container", worker)
        check_worker_environment(info["Config"]["Env"], env)
        if info["Image"] != image or info["Config"].get("Cmd") != [
            "python",
            "-m",
            "core.food_apis.scheduler",
            "--serve",
        ]:
            raise SmokeError("Worker effective image/command differs from the canonical CLI")
        if info["Config"]["User"] not in ("pulseplate", ":".join(worker_user), worker_user[0]):
            raise SmokeError("Worker lost its inspected default non-root user")
        self.mounts(worker, {"/app/cache": cache}, network)
        self.run("start", worker)
        self.mounts(worker, {"/app/cache": cache}, network)
        identity = worker_identity(self.inspect("container", worker), image)
        end = min(self.end, time.monotonic() + CYCLE_SECONDS)
        session = None
        complete = False
        while time.monotonic() < end:
            if worker_identity(self.inspect("container", worker), image) != identity:
                raise SmokeError("Worker process identity changed")
            complete = check_logs(self.logs(worker))
            session = lease_session(self.logs(pg), application, database)
            if complete and session:
                break
            time.sleep(0.5)
        if not session or not complete:
            raise SmokeError("Worker never completed the native leased no-update cycle")

        def observe() -> object:
            query = (
                "SELECT row_to_json(s) FROM (SELECT pid, backend_start::text, state, xact_start, "
            )
            query += "to_hex(floor(extract(epoch from backend_start))::bigint)||'.'||to_hex(pid) AS session, "
            query += "EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=a.pid AND locktype='advisory') AS locked "
            query += "FROM pg_stat_activity a WHERE application_name='scheduler_smoke_worker' "
            query += "AND datname='workerdb' AND usename='smoke_worker') s"
            return json.loads(sql(query, database))

        backend = check_session(observe(), session)
        if (
            sql(
                f"SELECT pg_try_advisory_lock({LEASE_KEY}); SELECT pg_advisory_unlock({LEASE_KEY})",
                database,
            )
            != "t\nt"
        ):
            raise SmokeError("Native observer could not acquire/release the canonical lock")
        time.sleep(SURVIVAL_SECONDS)
        check_session(observe(), session, backend)
        if worker_identity(self.inspect("container", worker), image) != identity:
            raise SmokeError("Worker process changed during survival interval")
        check_logs(self.logs(worker))
        if lease_session(self.logs(pg), application, database) != session:
            raise SmokeError("Native lease evidence changed")
        self.run("kill", "--signal", "TERM", worker)
        if self.run("wait", worker).strip() != "0":
            raise SmokeError("Worker did not exit normally")
        stopped = self.inspect("container", worker)
        if (
            (stopped["Id"], stopped["Image"], stopped["State"]["StartedAt"])
            != (identity[0], identity[1], identity[3])
            or stopped["State"]["Running"] is not False
            or stopped["State"]["OOMKilled"] is not False
            or (stopped["RestartCount"] != 0 or stopped["State"]["ExitCode"] != 0)
        ):
            raise SmokeError("Invalid terminal worker state")
        check_logs(self.logs(worker), stopped=True)
        print(
            json.dumps(
                {
                    "runtime": runtime,
                    "image": image,
                    "container": identity[0],
                    "postgres_session": backend,
                    "postgres_image": pg_image,
                    "restart_count": 0,
                    "exit_code": 0,
                }
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--postgres-image", required=True)
    args = parser.parse_args(argv)
    smoke = Smoke()
    failure: Exception | None = None
    try:
        candidate = smoke.inspect("image", args.image)
        check_worker_environment(candidate["Config"]["Env"])
        if candidate["Config"].get("User") != "pulseplate" or candidate["Config"].get("Entrypoint"):
            raise SmokeError("Unexpected candidate process user/entrypoint")
        if candidate["Config"].get("Volumes"):
            raise SmokeError("Candidate introduced implicit image volumes")
        image = candidate["Id"]
        pg_ref = args.postgres_image
        if re.fullmatch(r"pgvector/pgvector:[A-Za-z0-9_.-]+@sha256:[0-9a-f]{64}", pg_ref) is None:
            raise SmokeError("Expected an explicitly pinned public CI pgvector fixture")
        smoke.run("pull", "--platform", "linux/amd64", pg_ref)
        fixture = smoke.inspect("image", pg_ref)
        repository_digest = "pgvector/pgvector@" + pg_ref.split("@", 1)[1]
        if (
            re.fullmatch(r"sha256:[0-9a-f]{64}", fixture["Id"]) is None
            or fixture.get("Architecture") != "amd64"
            or fixture.get("Os") != "linux"
            or repository_digest not in fixture.get("RepoDigests", [])
        ):
            raise SmokeError("Synthetic PostgreSQL fixture identity mismatch")
        if set(fixture["Config"].get("Volumes") or {}) != {"/var/lib/postgresql/data"}:
            raise SmokeError("Unexpected PostgreSQL implicit volume inventory")
        pg_user = smoke.account(fixture["Id"], "postgres")
        worker_user = smoke.account(image, "pulseplate")
        for runtime in ("production", "staging"):
            smoke.exercise(image, fixture["Id"], runtime, pg_user, worker_user)
    except Exception as exc:
        failure = exc
    cleanup = smoke.cleanup()
    if failure or cleanup:
        print(f"Scheduler smoke failed: {failure or 'owned cleanup failed'}; cleanup={cleanup}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
