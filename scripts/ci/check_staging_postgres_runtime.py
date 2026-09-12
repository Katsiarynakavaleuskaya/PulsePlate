"""Native Linux PostgreSQL TLS, pgvector, restart and isolated-restore experiment.

This uses disposable Docker storage, not the DigitalOcean encrypted mount.
The image, PostgreSQL command and HBA come from actual staging Compose rendering.
Ephemeral private keys remain local and are never included in evidence artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess  # nosec B404: native Docker/OpenSSL/psql protocol has no safer bounded replacement (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
import sys
import tempfile
import time
from typing import Any
import uuid

from scripts.ops import check_staging_security as source
from scripts.ci import check_docker_provenance_attestation as redactor

LABEL = "io.pulseplate.staging-native-probe"
USER = "pulseplate_probe"
DATABASE = "pulseplate_probe_db"


class ProbeError(ValueError):
    """A bounded native experiment failed."""


def diagnostic_detail(value: bytes, secrets: tuple[str, ...] = (), limit: int = 500) -> str:
    text = value.decode(errors="replace")
    for secret in secrets:
        text = text.replace(secret, "[redacted-probe-secret]")
    text = re.sub(
        r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----[\s\S]*?(?:-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----|$)",
        "[redacted-private-key]",
        text,
    )
    redacted: str = redactor._redact_sensitive_text(text)
    return redacted[:limit].replace("\r", "\\r").replace("\n", "\\n")


def native(
    arguments: list[str],
    data: bytes | None = None,
    timeout: int = 60,
    required: bool = True,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    binary = shutil.which(arguments[0])
    if binary is None:
        raise ProbeError(f"Required native executable unavailable: {arguments[0]}")
    result = subprocess.run(  # nosec B603: resolved argv, binary input, no shell, bounded timeout and redacted errors (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
        [binary, *arguments[1:]],
        input=data,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=environment,
    )
    if required and result.returncode:
        # Native stderr only; never binary stdout, the complete argv or environment.
        detail = diagnostic_detail(result.stderr)
        operation = " ".join(arguments[:2])
        raise ProbeError(f"Native {operation} rejected (exit {result.returncode}): {detail}")
    return result


def selected_contract(rendered: object, manifest: dict[str, Any]) -> dict[str, Any]:
    document = source._object(rendered, "Rendered staging Compose")
    postgres = source._object(
        source._object(document.get("services"), "Services").get("postgres"), "PostgreSQL"
    )
    if (
        postgres.get("image") != manifest["runtime_ref"]
        or postgres.get("platform") != manifest["platform"]
    ):
        raise ProbeError("Rendered PostgreSQL image differs from the selected immutable manifest")
    command = postgres.get("command")
    if command != source.POSTGRES_COMMAND:
        raise ProbeError("Rendered PostgreSQL command differs from the admitted TLS arguments")
    mounts = postgres.get("volumes")
    if not isinstance(mounts, list):
        raise ProbeError("Rendered PostgreSQL mounts missing")
    hba = [
        mount
        for mount in mounts
        if isinstance(mount, dict)
        and mount.get("target") == "/etc/postgresql/pg_hba.conf"
        and mount.get("type") == "bind"
        and mount.get("read_only") is True
    ]
    if len(hba) != 1 or not isinstance(hba[0].get("source"), str):
        raise ProbeError("Exactly one real readonly staging HBA mount is required")
    data = [
        mount
        for mount in mounts
        if isinstance(mount, dict)
        and mount.get("target") == manifest["compose_volume_target"]
        and mount.get("type") == "volume"
    ]
    if len(data) != 1:
        raise ProbeError("Exactly one staging PostgreSQL data mount is required")
    environment = source._object(postgres.get("environment"), "PostgreSQL environment")
    if environment.get("PGDATA") != manifest["compose_pgdata"]:
        raise ProbeError("Rendered PostgreSQL PGDATA differs from the selected manifest")
    return {
        "image": manifest["repository"] + "@" + manifest["platform_manifest_digest"],
        "compose_runtime_ref": postgres["image"],
        "platform": postgres["platform"],
        "command": command,
        "hba": hba[0]["source"],
        "pgdata": environment["PGDATA"],
        "data_target": manifest["compose_volume_target"],
    }


def render_contract(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    environment = {
        **os.environ,
        "POSTGRES_USER": USER,
        "POSTGRES_DB": DATABASE,
        "STAGING_IMAGE_REF": manifest["runtime_ref"],
        "STAGING_CADDY_IMAGE_REF": manifest["runtime_ref"],
        "STAGING_DOMAIN": "localhost",
        "STAGING_ENV_FILE": "/dev/null",
    }
    result = native(
        [
            "docker",
            "compose",
            "-f",
            str(root / "deploy/docker-compose.staging.yaml"),
            "config",
            "--no-env-resolution",
            "--format",
            "json",
        ],
        environment=environment,
    )
    contract = selected_contract(source._read_json(result.stdout.decode()), manifest)
    hba = Path(contract["hba"])
    if (
        hba.is_symlink()
        or not hba.is_file()
        or hba != root / "deploy/postgres-pgvector/pg_hba.conf"
    ):
        raise ProbeError("Rendered HBA is not the real regular staging source asset")
    return contract


def create_pki(root: Path) -> Path:
    private = root / "private"
    secrets = root / "secrets"
    private.mkdir(mode=0o700)
    secrets.mkdir(mode=0o700)
    native(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(private / "ca.key"),
            "-out",
            str(secrets / "postgres_ca"),
            "-subj",
            "/CN=PulsePlate disposable native probe",
            "-days",
            "2",
        ]
    )
    native(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(secrets / "postgres_server_key"),
            "-out",
            str(private / "server.csr"),
            "-subj",
            "/CN=postgres",
        ]
    )
    extension = private / "leaf.ext"
    extension.write_text(
        "subjectAltName=DNS:postgres\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n"
    )
    native(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(private / "server.csr"),
            "-CA",
            str(secrets / "postgres_ca"),
            "-CAkey",
            str(private / "ca.key"),
            "-CAcreateserial",
            "-out",
            str(secrets / "postgres_server_crt"),
            "-days",
            "1",
            "-extfile",
            str(extension),
        ]
    )
    native(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(private / "wrong.key"),
            "-out",
            str(secrets / "wrong_ca"),
            "-subj",
            "/CN=Wrong disposable CA",
            "-days",
            "2",
        ]
    )
    (private / "index").write_text("")
    (private / "serial").write_text("01\n")
    (private / "certs").mkdir(mode=0o700)
    config = private / "ca.cnf"
    config.write_text(f"""[ca]
default_ca=local
[local]
database={private / 'index'}
serial={private / 'serial'}
new_certs_dir={private / 'certs'}
certificate={secrets / 'postgres_ca'}
private_key={private / 'ca.key'}
default_md=sha256
default_days=1
policy=policy
x509_extensions=leaf
[policy]
commonName=supplied
[leaf]
subjectAltName=DNS:postgres
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
""")
    native(
        [
            "openssl",
            "ca",
            "-config",
            str(config),
            "-batch",
            "-notext",
            "-in",
            str(private / "server.csr"),
            "-out",
            str(secrets / "expired_server_crt"),
            "-startdate",
            "20200101000000Z",
            "-enddate",
            "20200102000000Z",
        ]
    )
    password = uuid.uuid4().hex
    (secrets / "postgres_password").write_text(password)
    (secrets / "postgres_pgpass").write_text(f"*:5432:*:{USER}:{password}\n")
    return secrets


def connection(
    database: str = DATABASE,
    host: str = "postgres",
    ca: str = "postgres_ca",
    sslmode: str = "verify-full",
) -> str:
    return (
        f"host={host} hostaddr=127.0.0.1 port=5432 dbname={database} user={USER} sslmode={sslmode} "
        f"sslrootcert=/run/secrets/{ca} passfile=/run/secrets/postgres_pgpass connect_timeout=3"
    )


def query(
    container: str,
    sql: str,
    conn: str | None = None,
    required: bool = True,
    variables: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return native(
        [
            "docker",
            "exec",
            "-i",
            container,
            "psql",
            "--no-password",
            "-X",
            "-qAt",
            "-v",
            "ON_ERROR_STOP=1",
            "--dbname",
            conn or connection(),
            *[
                argument
                for name, value in (variables or {}).items()
                for argument in ("--set", name + "=" + value)
            ],
        ],
        data=sql.encode(),
        required=required,
    )


def wait_database(container: str, verified: bool = True) -> None:
    deadline = time.monotonic() + 60
    last_query = "No readiness query completed"
    while time.monotonic() < deadline:
        result = (
            query(container, "SELECT 1", required=False)
            if verified
            else native(
                [
                    "docker",
                    "exec",
                    container,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    USER,
                    "-d",
                    DATABASE,
                ],
                required=False,
            )
        )
        if result.returncode == 0:
            return
        last_query = f"exit={result.returncode} stderr={diagnostic_detail(result.stderr)}"
        time.sleep(1)
    raise ProbeError(
        "Native PostgreSQL startup did not reach the bounded readiness condition; " + last_query
    )


def diagnose_container(container: str, owner: str, secrets: tuple[str, ...]) -> None:
    """Read only this invocation's container, without full inspect/env/argv output."""
    inspected = native(
        [
            "docker",
            "container",
            "inspect",
            "--format",
            '{{json (index .Config.Labels "' + LABEL + '")}}',
            container,
        ],
        required=False,
        timeout=10,
    )
    if inspected.returncode or source._read_json(inspected.stdout.decode()) != owner:
        print(
            "native-staging diagnostics unavailable: container ownership unconfirmed",
            file=sys.stderr,
        )
        return
    state = native(
        [
            "docker",
            "container",
            "inspect",
            "--format",
            '{"status":{{json .State.Status}},"running":{{json .State.Running}},'
            '"oom_killed":{{json .State.OOMKilled}},"exit_code":{{json .State.ExitCode}},'
            '"error":{{json .State.Error}}}',
            container,
        ],
        required=False,
        timeout=10,
    )
    logs = native(["docker", "logs", "--tail", "64", container], required=False, timeout=10)
    for name, result, limit in (("state", state, 1500), ("logs", logs, 8000)):
        print(
            "native-staging diagnostic="
            + name
            + " "
            + json.dumps(
                {
                    "exit_code": result.returncode,
                    "output": diagnostic_detail(result.stdout + result.stderr, secrets, limit),
                }
            ),
            file=sys.stderr,
            flush=True,
        )


def crash_at_transaction_barrier(container: str, owner: str) -> None:
    name = "pulseplate_crash_" + owner[:16]
    transaction = (
        "BEGIN; INSERT INTO staging_probe VALUES(2,'uncommitted'); SELECT pg_sleep(120); COMMIT"
    )
    native(
        [
            "docker",
            "exec",
            "--detach",
            container,
            "psql",
            "--no-password",
            "-X",
            "-qAt",
            "-v",
            "ON_ERROR_STOP=1",
            "--dbname",
            connection() + f" application_name={name}",
            "--command",
            transaction,
        ]
    )
    barrier = "SELECT count(*) FROM pg_stat_activity WHERE application_name=current_setting('application_name') AND state='active' AND wait_event='PgSleep'"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if (
            query(container, barrier, connection() + f" application_name={name}")
            .stdout.decode()
            .strip()
            == "1"
        ):
            native(["docker", "kill", "--signal", "KILL", container])
            native(["docker", "start", container])
            wait_database(container)
            return
        time.sleep(0.25)
    raise ProbeError("Open uncommitted transaction never reached its observed native SQL barrier")


def cleanup(resources: dict[str, list[str]], owner: str) -> None:
    errors = []
    for kind in ("container", "volume", "network"):
        census = native(
            [
                "docker",
                kind,
                "ls",
                *(["--all"] if kind == "container" else []),
                "--filter",
                f"label={LABEL}={owner}",
                "--format",
                "{{.Names}}" if kind == "container" else "{{.Name}}",
            ],
            required=False,
        )
        if census.returncode:
            errors.append(kind + " census")
            continue
        actual = census.stdout.decode().splitlines()
        if any(name not in resources[kind] for name in actual):
            errors.append(kind + " ownership")
            continue
        for name in actual:
            args = ["docker", kind, "rm"] + (["--force"] if kind == "container" else []) + [name]
            if native(args, required=False).returncode:
                errors.append(kind + " cleanup")
    if errors:
        raise ProbeError("Owned native cleanup rejected: " + ", ".join(errors))


def compose_project(
    directory: Path, contract: dict[str, Any], prefix: str, owner: str, secrets: Path
) -> Path:
    """Give the actual ops wrappers a native Compose service on disposable storage."""
    document = {
        "name": prefix,
        "services": {
            "postgres": {
                "container_name": prefix + "-db",
                "image": contract["image"],
                "platform": contract["platform"],
                "command": contract["command"],
                "labels": {LABEL: owner},
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "mem_limit": "512m",
                "cpus": 1,
                "pids_limit": 256,
                "environment": {
                    "POSTGRES_DB": DATABASE,
                    "POSTGRES_USER": USER,
                    "POSTGRES_PASSWORD_FILE": str(Path("/run/secrets") / "postgres_password"),
                    "PGDATA": contract["pgdata"],
                },
                "volumes": [
                    {"type": "volume", "source": "data", "target": contract["data_target"]},
                    {
                        "type": "bind",
                        "source": str(secrets),
                        "target": "/run/secrets",
                        "read_only": True,
                    },
                    {
                        "type": "bind",
                        "source": contract["hba"],
                        "target": "/etc/postgresql/pg_hba.conf",
                        "read_only": True,
                    },
                ],
                "networks": {"database": {"aliases": ["postgres"]}},
            }
        },
        "volumes": {"data": {"external": True, "name": prefix + "-data"}},
        "networks": {"database": {"external": True, "name": prefix + "-network"}},
    }
    compose_file = directory / "compose.native.json"
    compose_file.write_text(json.dumps(document, sort_keys=True))
    return compose_file


def wrapper_restore_checks(
    root: Path, directory: Path, container: str, owner: str, compose_file: Path
) -> dict[str, bool]:
    """Exercise real wrappers against the invocation-owned generic Compose DB.

    Wrappers use the configured local socket, matching deployed scripts.
    query() independently proves network verify-full; no DigitalOcean or
    wrapper network-session claim is authored by these controls.
    """
    if USER == DATABASE or re.fullmatch(r"[0-9a-f]{32}", owner) is None:
        raise ProbeError("Wrapper fixture requires distinct role/database and a native owner")
    docker = shutil.which("docker")
    if docker is None:
        raise ProbeError("Native wrapper Docker executable unavailable")
    backups = directory / "wrapper-backups"
    backups.mkdir(mode=0o700)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PG")
        and key
        not in ("COMPOSE_PROJECT_NAME", "COMPOSE_PROFILES", "COMPOSE_FILE", "COMPOSE_ENV_FILES")
    }
    environment.update(
        {
            "PROJECT_DIR": str(directory),
            "COMPOSE_FILE": str(compose_file),
            "BACKUP_DIR": str(backups),
            "POSTGRES_USER": USER,
            "POSTGRES_DB": DATABASE,
            "ENV_FILE": "/dev/null",
            "DOCKER_BIN": docker,
        }
    )
    suffix = owner[:16]
    primary: BaseException | None = None
    results: dict[str, bool] = {}
    source_select = "SELECT count(*)::text || ':' || min(payload) FROM public.staging_probe"
    source_expected = query(container, source_select).stdout.decode().strip()
    if not source_expected.startswith("1:"):
        raise ProbeError("Wrapper fixture lacks the observed source sentinel")

    def backup() -> Path:
        before = set(backups.glob("pulseplate_*.dump"))
        completed = native(
            ["bash", str(root / "scripts/ops/postgres_backup.sh")],
            timeout=120,
            environment=environment,
        )
        created = set(backups.glob("pulseplate_*.dump")) - before
        if len(created) != 1:
            raise ProbeError("Actual backup wrapper publication is ambiguous")
        path = created.pop()
        metadata = path.lstat()
        if (
            not path.is_file()
            or path.is_symlink()
            or metadata.st_nlink != 1
            or metadata.st_mode & 0o777 != 0o600
            or not 0 < metadata.st_size <= 64 * 1024**2
            or completed.stdout.decode().strip() != "Backup created: " + str(path)
            or list(backups.glob(".pulseplate-backup.*"))
        ):
            raise ProbeError("Actual backup wrapper did not publish one private complete archive")
        native(
            ["docker", "exec", "-i", container, "pg_restore", "--file=/dev/null"], path.read_bytes()
        )
        return path

    def restore(
        mode: str, target: str, path: Path, required: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        return native(
            ["bash", str(root / "scripts/ops/postgres_restore.sh"), mode, target, str(path)],
            timeout=120,
            required=required,
            environment=environment,
        )

    def target_query(target: str, sql: str, variables: dict[str, str] | None = None) -> str:
        return (
            query(container, sql, connection(target), variables=variables).stdout.decode().strip()
        )

    def create_old_target(target: str) -> None:
        native(
            [
                "docker",
                "exec",
                container,
                "createdb",
                "-U",
                USER,
                "--maintenance-db",
                DATABASE,
                "--owner",
                USER,
                target,
            ]
        )
        target_query(
            target,
            "CREATE TABLE public.wrapper_original(id integer PRIMARY KEY,payload text NOT NULL); "
            "INSERT INTO public.wrapper_original VALUES(1,:'old_payload'); "
            "CREATE TABLE public.wrapper_extra(id integer); "
            "CREATE VIEW public.wrapper_stale_view AS SELECT * FROM public.wrapper_original; "
            "CREATE FUNCTION public.wrapper_stale_fn() RETURNS integer LANGUAGE sql AS 'SELECT 7';",
            variables={"old_payload": "old_" + suffix},
        )

    def old_snapshot(target: str) -> str:
        return target_query(
            target,
            "SELECT count(*)::text || ':' || min(payload) FROM public.wrapper_original; "
            "SELECT to_regclass('public.wrapper_extra') IS NOT NULL, "
            "to_regclass('public.wrapper_stale_view') IS NOT NULL, "
            "to_regprocedure('public.wrapper_stale_fn()') IS NOT NULL, "
            "to_regclass('public.staging_probe') IS NULL;",
        )

    def assert_replaced(target: str) -> None:
        if target_query(target, source_select) != source_expected:
            raise ProbeError("Actual replacement lost the source sentinel")
        if (
            target_query(
                target,
                "SELECT to_regclass('public.wrapper_original') IS NULL, "
                "to_regclass('public.wrapper_extra') IS NULL, "
                "to_regclass('public.wrapper_stale_view') IS NULL, "
                "to_regprocedure('public.wrapper_stale_fn()') IS NULL; "
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename;",
            )
            != "t|t|t|t\nstaging_probe"
        ):
            raise ProbeError("Actual replacement retained stale public objects or wrong tables")
        if list(backups.glob(".pulseplate-restore.*")):
            raise ProbeError("Actual replacement left private temporary SQL residue")

    def schema_shape(path: Path, expected: str) -> None:
        contents = native(
            ["docker", "exec", "-i", container, "pg_restore", "--list"], path.read_bytes()
        ).stdout.decode()
        sql = native(
            ["docker", "exec", "-i", container, "pg_restore", "--clean", "--if-exists", "--file=-"],
            path.read_bytes(),
        ).stdout.decode()
        has_record = (
            re.search(r"^\d+; \d+ \d+ SCHEMA - public ", contents, re.MULTILINE) is not None
        )
        has_create = re.search(r"^CREATE SCHEMA public;$", sql, re.MULTILINE) is not None
        if (has_record, has_create) != {
            "omitted": (False, False),
            "metadata-only": (True, False),
            "definition": (True, True),
        }[expected]:
            raise ProbeError(
                "Native public schema shape differs from its required observed control"
            )

    try:
        query(container, "ALTER SCHEMA public OWNER TO pg_database_owner;")
        default_dump = backup()
        schema_shape(default_dump, "omitted")
        results["wrapper_backup_private_archive_verified"] = True
        if (
            query(
                container,
                "SELECT count(*) FROM pg_database WHERE datname=:'role';",
                variables={"role": USER},
            )
            .stdout.decode()
            .strip()
            != "0"
        ):
            raise ProbeError(
                "Role-name database exists; maintenance negative boundary not exercised"
            )
        verify_target = "pulseplate_restore_check_wrapper_" + suffix
        restore("--verify-into", verify_target, default_dump)
        if target_query(verify_target, source_select) != source_expected:
            raise ProbeError("Actual isolated wrapper restore sentinel mismatch")
        if restore("--verify-into", verify_target, default_dump, required=False).returncode == 0:
            raise ProbeError("Actual verification wrapper replaced its pre-existing target")
        if target_query(verify_target, source_select) != source_expected:
            raise ProbeError("Rejected duplicate verification mutated the target")
        results["wrapper_verify_maintenance_distinct_role"] = True

        query(container, "ALTER SCHEMA public OWNER TO " + USER + ";")
        metadata_dump = backup()
        schema_shape(metadata_dump, "metadata-only")
        explicit_dump = backups / "explicit-public.dump"
        explicit_bytes = native(
            [
                "docker",
                "exec",
                container,
                "pg_dump",
                "-U",
                USER,
                "-d",
                DATABASE,
                "-Fc",
                "--schema=public",
            ]
        ).stdout
        if not 0 < len(explicit_bytes) <= 64 * 1024**2:
            raise ProbeError("Explicit schema fixture exceeds native archive bounds")
        with explicit_dump.open("xb") as handle:
            handle.write(explicit_bytes)
        explicit_dump.chmod(0o600)
        schema_shape(explicit_dump, "definition")
        query(container, "ALTER SCHEMA public OWNER TO pg_database_owner;")
        for shape, archive in (
            ("omitted", default_dump),
            ("metadata-only", metadata_dump),
            ("definition", explicit_dump),
        ):
            target = "pulseplate_wrapper_" + shape.replace("-", "_") + "_" + suffix
            create_old_target(target)
            restore("--replace-existing", target, archive)
            assert_replaced(target)
            results["wrapper_replacement_schema_" + shape.replace("-", "_")] = True
        results["wrapper_replacement_stale_public_objects_removed"] = True

        # Build an index while the immutable function succeeds, then change its
        # body. The complete archive decodes; rebuilding the post-data index
        # invokes the new body and raises after schema/data restoration begins.
        query(
            container,
            "CREATE FUNCTION public.wrapper_restore_key(text) RETURNS integer LANGUAGE plpgsql IMMUTABLE "
            "AS $$ BEGIN RETURN 1; END; $$; "
            "CREATE INDEX wrapper_restore_failure_idx ON public.staging_probe ((public.wrapper_restore_key(payload))); "
            "CREATE OR REPLACE FUNCTION public.wrapper_restore_key(text) RETURNS integer LANGUAGE plpgsql IMMUTABLE "
            "AS $$ BEGIN RAISE EXCEPTION 'synthetic restore index failure'; END; $$;",
        )
        failing_dump = backup()
        query(
            container,
            "DROP INDEX public.wrapper_restore_failure_idx; DROP FUNCTION public.wrapper_restore_key(text);",
        )
        rollback_target = "pulseplate_wrapper_rollback_" + suffix
        create_old_target(rollback_target)
        before = old_snapshot(rollback_target)
        failed = restore("--replace-existing", rollback_target, failing_dump, required=False)
        if (
            failed.returncode == 0
            or b"synthetic restore index failure" not in failed.stderr
            or b"Restore completed" in failed.stdout
            or old_snapshot(rollback_target) != before
            or list(backups.glob(".pulseplate-restore.*"))
        ):
            raise ProbeError("Actual late SQL failure did not roll the replacement back exactly")
        results["wrapper_replacement_late_sql_failure_rolled_back"] = True

        query(
            container,
            "CREATE SCHEMA private_wrapper; CREATE TABLE private_wrapper.hidden(id integer); INSERT INTO private_wrapper.hidden VALUES(9);",
        )
        nonpublic_dump = backup()
        query(container, "DROP SCHEMA private_wrapper CASCADE;")
        hold_target = "pulseplate_wrapper_hold_" + suffix
        create_old_target(hold_target)
        before = old_snapshot(hold_target)
        held = restore("--replace-existing", hold_target, nonpublic_dump, required=False)
        if (
            held.returncode == 0
            or b"archive contains unsupported" not in held.stderr
            or old_snapshot(hold_target) != before
        ):
            raise ProbeError(
                "Actual non-public source archive was not rejected before target mutation"
            )
        results["wrapper_nonpublic_source_hold"] = True
        target_query(
            hold_target,
            "CREATE SCHEMA private_wrapper; CREATE TABLE private_wrapper.hidden(id integer); INSERT INTO private_wrapper.hidden VALUES(9);",
        )
        held = restore("--replace-existing", hold_target, default_dump, required=False)
        if (
            held.returncode == 0
            or b"target contains unsupported" not in held.stderr
            or old_snapshot(hold_target) != before
            or target_query(hold_target, "SELECT id FROM private_wrapper.hidden;") != "9"
            or list(backups.glob(".pulseplate-restore.*"))
        ):
            raise ProbeError(
                "Actual non-public target was not held with all original data retained"
            )
        results["wrapper_nonpublic_target_hold"] = True
    except BaseException as error:
        primary = error
    finally:
        cleanup_error: BaseException | None = None
        try:
            repaired = query(
                container,
                "DROP INDEX IF EXISTS public.wrapper_restore_failure_idx; "
                "DROP FUNCTION IF EXISTS public.wrapper_restore_key(text); "
                "DROP SCHEMA IF EXISTS private_wrapper CASCADE; "
                "ALTER SCHEMA public OWNER TO pg_database_owner;",
                required=False,
            )
            if repaired.returncode:
                cleanup_error = ProbeError("Owned wrapper source cleanup failed")
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            cleanup_error = error
        if cleanup_error is not None:
            if primary is None:
                primary = cleanup_error
            else:
                print(
                    "Owned wrapper source cleanup also failed; primary failure preserved",
                    file=sys.stderr,
                )
    if primary is not None:
        raise primary
    return results


def experiment(root: Path, contract: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    owner = uuid.uuid4().hex
    prefix = "pulseplate-staging-native-" + owner[:16]
    container, volume, network = prefix + "-db", prefix + "-data", prefix + "-network"
    tools = [prefix + "-permissions", prefix + "-expiry", prefix + "-ownership-restore"]
    resources = {"container": [container, *tools], "volume": [volume], "network": [network]}
    primary: BaseException | None = None
    key_ownership_attempted = False
    database_start_attempted = False
    sensitive_values: tuple[str, ...] = ()
    result: dict[str, Any] = {}
    directory = tempfile.mkdtemp(prefix="pulseplate-staging-native-")
    try:
        secrets = create_pki(Path(directory))
        sensitive_values = ((secrets / "postgres_password").read_text(),)
        fingerprint = (
            native(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(secrets / "postgres_ca"),
                    "-noout",
                    "-fingerprint",
                    "-sha256",
                ]
            )
            .stdout.decode()
            .strip()
        )
        native(
            ["docker", "pull", "--platform", contract["platform"], contract["image"]], timeout=180
        )
        inspected = source._read_json(
            native(["docker", "image", "inspect", contract["image"]]).stdout.decode()
        )
        if not isinstance(inspected, list) or len(inspected) != 1:
            raise ProbeError("Native pulled image inspection is ambiguous")
        image = source._object(inspected[0], "Native pulled image")
        if image.get("Id") != manifest["config_digest"]:
            raise ProbeError("Pulled image configuration differs from exact selected manifest")
        native(
            ["docker", "network", "create", "--internal", "--label", f"{LABEL}={owner}", network]
        )
        native(["docker", "volume", "create", "--label", f"{LABEL}={owner}", volume])

        def key_operation(name: str, command: str) -> None:
            native(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    name,
                    "--label",
                    f"{LABEL}={owner}",
                    "--network",
                    "none",
                    "--user",
                    "0:0",
                    "--entrypoint",
                    "/bin/sh",
                    "--mount",
                    f"type=bind,source={secrets},target=/k",
                    contract["image"],
                    "-ec",
                    command,
                ]
            )

        key_ownership_attempted = True
        key_operation(
            tools[0],
            "chown 70:70 /k /k/*; chmod 0700 /k; chmod 0600 /k/postgres_server_key /k/postgres_pgpass /k/postgres_password; chmod 0444 /k/postgres_ca /k/postgres_server_crt /k/wrong_ca /k/expired_server_crt",
        )
        compose_file = compose_project(Path(directory), contract, prefix, owner, secrets)
        database_start_attempted = True
        native(
            [
                "docker",
                "compose",
                "--project-directory",
                directory,
                "-f",
                str(compose_file),
                "up",
                "--detach",
                "--pull",
                "never",
                "postgres",
            ]
        )
        print("native-staging phase=TLS-and-pgvector", flush=True)
        wait_database(container)
        ssl = (
            query(
                container,
                "SELECT ssl::text || ':' || version FROM pg_stat_ssl WHERE pid=pg_backend_pid()",
            )
            .stdout.decode()
            .strip()
        )
        if ssl not in ("true:TLSv1.2", "true:TLSv1.3"):
            raise ProbeError("Actual TCP PostgreSQL session did not use required TLS")
        postgres_version = query(container, "SHOW server_version").stdout.decode().strip()
        if postgres_version != manifest["postgres_version"]:
            raise ProbeError("Actual PostgreSQL binary version differs from the selected manifest")
        if (
            query(
                container, "CREATE EXTENSION IF NOT EXISTS vector; SELECT '[1,2,3]'::vector::text"
            )
            .stdout.decode()
            .strip()
            != "[1,2,3]"
        ):
            raise ProbeError("Native pgvector extension/cast failed")
        vector_version = (
            query(container, "SELECT extversion FROM pg_extension WHERE extname='vector'")
            .stdout.decode()
            .strip()
        )
        if vector_version != manifest["pgvector_version"]:
            raise ProbeError("Actual pgvector extension version differs from the selected manifest")
        sentinel = uuid.uuid4().hex
        query(
            container,
            "CREATE TABLE staging_probe(id integer PRIMARY KEY,payload text NOT NULL); INSERT INTO staging_probe VALUES(1,:'sentinel')",
            variables={"sentinel": sentinel},
        )
        expected = "1:" + sentinel
        select = "SELECT count(*)::text || ':' || min(payload) FROM staging_probe"
        if query(container, select).stdout.decode().strip() != expected:
            raise ProbeError("Synthetic source sentinel mismatch")
        native(["docker", "restart", "--timeout", "10", container])
        wait_database(container)
        if query(container, select).stdout.decode().strip() != expected:
            raise ProbeError("Same-volume restart lost synthetic sentinel")
        print("native-staging phase=process-crash-and-WAL-recovery", flush=True)
        crash_at_transaction_barrier(container, owner)
        if query(container, select).stdout.decode().strip() != expected:
            raise ProbeError(
                "Process crash lost committed sentinel or retained uncommitted insertion"
            )
        print("native-staging phase=custom-archive-and-isolated-restore", flush=True)
        dump = native(
            [
                "docker",
                "exec",
                container,
                "pg_dump",
                "--no-password",
                "--format=custom",
                "--dbname",
                connection(),
            ]
        ).stdout
        if not 0 < len(dump) <= 64 * 1024**2:
            raise ProbeError("Native custom dump size is outside experiment bounds")
        contents = native(
            ["docker", "exec", "-i", container, "pg_restore", "--list"], dump
        ).stdout.decode()
        if "TABLE public staging_probe" not in contents:
            raise ProbeError("Native custom dump does not contain the source sentinel table")
        native(["docker", "exec", "-i", container, "pg_restore", "--file=/dev/null"], dump)
        for label, damaged in (
            ("corrupted", b"BROKEN!!" + dump[8:]),
            ("truncated", dump[: len(dump) // 2]),
        ):
            if (
                native(
                    ["docker", "exec", "-i", container, "pg_restore", "--file=/dev/null"],
                    damaged,
                    required=False,
                ).returncode
                == 0
            ):
                raise ProbeError(f"Native {label} custom archive unexpectedly accepted")
        target = "pulseplate_restore_check_" + owner[:16]
        native(
            [
                "docker",
                "exec",
                container,
                "createdb",
                "--no-password",
                "--maintenance-db",
                connection(),
                "--owner",
                USER,
                target,
            ]
        )
        native(
            [
                "docker",
                "exec",
                "-i",
                container,
                "pg_restore",
                "--no-password",
                "--exit-on-error",
                "--single-transaction",
                "--dbname",
                connection(target),
            ],
            dump,
        )
        if query(container, select, connection(target)).stdout.decode().strip() != expected:
            raise ProbeError("Isolated native restore sentinel/count differs from source")
        print("native-staging phase=actual-backup-replacement-and-rollback", flush=True)
        wrapper_results = wrapper_restore_checks(
            root, Path(directory), container, owner, compose_file
        )
        print("native-staging phase=TLS-negative-controls", flush=True)
        for label, conn in (
            ("plaintext", connection(sslmode="disable")),
            ("wrong_ca", connection(ca="wrong_ca")),
            ("wrong_dns", connection(host="wrong.invalid")),
        ):
            if query(container, "SELECT 1", conn, required=False).returncode == 0:
                raise ProbeError(f"Native {label} rejection unexpectedly succeeded")
            if query(container, "SELECT 1").stdout.decode().strip() != "1":
                raise ProbeError("Native TLS negative control lost its healthy positive baseline")
        key_operation(
            tools[1],
            "cp /k/expired_server_crt /k/postgres_server_crt; chmod 0444 /k/postgres_server_crt",
        )
        native(["docker", "restart", "--timeout", "10", container])
        wait_database(container, verified=False)
        if query(container, "SELECT 1", required=False).returncode == 0:
            raise ProbeError("Expired native server certificate unexpectedly accepted")
        result = {
            "schema": "pulseplate.staging_native_experiment.v1",
            "image": contract["image"],
            "compose_runtime_ref": contract["compose_runtime_ref"],
            "canonical_publication_claim": False,
            "config_digest": manifest["config_digest"],
            "tls_session": ssl,
            "postgres_version": postgres_version,
            "pgvector_version": vector_version,
            "ca_fingerprint": fingerprint,
            "storage_scope": "disposable Docker named volume",
            "same_volume_restart": True,
            "process_crash_committed_survives_uncommitted_rolls_back": True,
            "isolated_restore_sentinel_count_equal": True,
            "actual_ops_wrappers": wrapper_results,
            "pgvector_cast": True,
            "rejected": [
                "plaintext",
                "wrong_ca",
                "wrong_dns",
                "expired_certificate",
                "corrupted_dump",
                "truncated_dump",
            ],
            "live_deployment_sessions_and_do_encryption_claim": False,
        }
        result.update(
            {
                "asset_type": "native_staging_postgres_experiment",
                "upstream_assets": [
                    {
                        "path": str(path.relative_to(root)),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    for path in (
                        root / "deploy/postgres-pgvector/image-manifest.json",
                        root / "deploy/docker-compose.staging.yaml",
                        Path(contract["hba"]),
                        Path(__file__),
                        root / "scripts/ops/postgres_backup.sh",
                        root / "scripts/ops/postgres_restore.sh",
                    )
                ],
                "policy_version": "staging-native-runtime-v1",
                "idempotency_key": owner,
                "replay_admission": "Fresh isolated experiment only; no serving, image promotion or deployment authority",
            }
        )
        result["fingerprint"] = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest()
    except BaseException as error:
        primary = error
    finally:
        if primary is not None and database_start_attempted:
            try:
                diagnose_container(container, owner, sensitive_values)
            except (ValueError, OSError, subprocess.SubprocessError):
                print(
                    "Native diagnostic collection failed; primary failure preserved",
                    file=sys.stderr,
                )
        try:
            cleanup(resources, owner)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            if primary is None:
                primary = error
            else:
                print(
                    "Owned native cleanup also failed; primary experiment failure preserved",
                    file=sys.stderr,
                )
        if key_ownership_attempted and (Path(directory) / "secrets").exists():
            try:
                native(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--name",
                        tools[2],
                        "--label",
                        f"{LABEL}={owner}",
                        "--network",
                        "none",
                        "--user",
                        "0:0",
                        "--entrypoint",
                        "/bin/sh",
                        "--mount",
                        f"type=bind,source={Path(directory) / 'secrets'},target=/k",
                        contract["image"],
                        "-ec",
                        f"chown {os.getuid()}:{os.getgid()} /k /k/*; chmod 0700 /k; chmod 0600 /k/*",
                    ]
                )
                cleanup(resources, owner)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                if primary is None:
                    primary = error
                else:
                    print(
                        "Owned PKI cleanup also failed; primary failure preserved", file=sys.stderr
                    )
        try:
            shutil.rmtree(directory)
        except OSError as error:
            if primary is None:
                primary = error
            else:
                print("Private PKI removal also failed; primary failure preserved", file=sys.stderr)
    if primary is not None:
        raise primary
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--configure-only", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        args.repo_root = args.repo_root.resolve(strict=True)
        manifest = source._object(
            source._read_json(
                (args.repo_root / "deploy/postgres-pgvector/image-manifest.json").read_text()
            ),
            "Selected PostgreSQL manifest",
        )
        contract = render_contract(args.repo_root, manifest)
        if not args.configure_only and sys.platform != "linux":
            raise ProbeError("The actual native experiment requires its Linux CI lane")
        result = (
            {
                "configure_only": True,
                "image": contract["image"],
                "compose_runtime_ref": contract["compose_runtime_ref"],
                "command_source": "native rendered staging Compose",
            }
            if args.configure_only
            else experiment(args.repo_root, contract, manifest)
        )
        if args.json_out:
            args.json_out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Native staging experiment HOLD: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
