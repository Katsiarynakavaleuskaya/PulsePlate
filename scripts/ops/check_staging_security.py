#!/usr/bin/env python3
"""Check the admitted staging mount and PostgreSQL TLS inputs without mutation.

DigitalOcean owns encryption at rest; this adapter binds the actual mounted
device to the root-owned receipt from authenticated Volume provisioning.
"""

from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess  # nosec B404: native mount/TLS/daemon recognizers have no safer bounded replacement (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
import sys
from typing import cast
from urllib.parse import parse_qsl, unquote, urlsplit


class SecurityError(ValueError):
    """One required staging security observation is missing or inconsistent."""


STORAGE_ROOT = "/mnt/pulseplate-staging-data"
DEVICE_PATH = "/dev/disk/by-id/scsi-0DO_Volume_pulseplate-staging-data"
CONTRACT_FIELDS = {
    "schema",
    "droplet_id",
    "volume_id",
    "volume_name",
    "filesystem_uuid",
    "mountpoint",
    "device",
    "size_gib",
    "backend_uid",
    "backend_gid",
}
POSTGRES_COMMAND = [
    "-c",
    "ssl=on",
    "-c",
    "ssl_min_protocol_version=TLSv1.2",
    "-c",
    "ssl_cert_file=/run/secrets/postgres_server_crt",
    "-c",
    "ssl_key_file=/run/secrets/postgres_server_key",
    "-c",
    "hba_file=/etc/postgresql/pg_hba.conf",
    "-c",
    "password_encryption=scram-sha-256",
]


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise SecurityError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SecurityError("Duplicate JSON field")
        result[key] = value
    return result


def _read_json(value: str) -> object:
    def reject_constant(_: str) -> object:
        raise SecurityError("Non-finite JSON value")

    return json.loads(value, object_pairs_hook=_unique_object, parse_constant=reject_constant)


def _regular_file(path: Path, uid: int, gid: int, mode: int, device: int | None = None) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (device is not None and metadata.st_dev != device)
        or metadata.st_nlink != 1
        or (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)) != (uid, gid, mode)
    ):
        raise SecurityError(
            f"Invalid regular-file owner, permissions, links or device: {path.name}"
        )


def _directory(path: Path, uid: int, gid: int, mode: int, device: int) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)) != (uid, gid, mode)
        or metadata.st_dev != device
    ):
        raise SecurityError(f"Invalid directory owner, permissions or device: {path.name}")


def _native(arguments: list[str]) -> str:
    binary = shutil.which(arguments[0])
    if binary is None:
        raise SecurityError(f"Required executable unavailable: {arguments[0]}")
    result = subprocess.run(  # nosec B603: resolved OS/crypto argv, no shell, 30s timeout and fail-closed status (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
        [binary, *arguments[1:]], capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode:
        # Native output may contain credential material. Never copy it into logs.
        raise SecurityError(f"{arguments[0]} check failed (exit {result.returncode})")
    return result.stdout


def validate_contract(value: object) -> dict[str, object]:
    contract = _object(value, "Storage receipt")
    if set(contract) != CONTRACT_FIELDS:
        raise SecurityError("Storage receipt fields differ from the admitted contract")
    expected = {
        "schema": "pulseplate.staging-storage.v1",
        "droplet_id": 594869239,
        "volume_name": "pulseplate-staging-data",
        "mountpoint": STORAGE_ROOT,
        "device": DEVICE_PATH,
        "size_gib": 50,
    }
    for key, expected_value in expected.items():
        if type(contract[key]) is not type(expected_value) or contract[key] != expected_value:
            raise SecurityError(f"Storage receipt has an unapproved {key}")
    for key in ("volume_id", "filesystem_uuid"):
        if (
            not isinstance(contract[key], str)
            or re.fullmatch(
                r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", cast(str, contract[key])
            )
            is None
        ):
            raise SecurityError(f"Storage receipt has an invalid {key}")
    for key in ("backend_uid", "backend_gid"):
        if type(contract[key]) is not int or not 1 <= cast(int, contract[key]) <= 65535:
            raise SecurityError(f"Storage receipt has an invalid {key}")
    return contract


def validate_mount(
    contract: dict[str, object],
    observed: object,
    resolved_device: str,
    mount_device: int,
    root_device: int,
) -> None:
    envelope = _object(observed, "findmnt output")
    rows = envelope.get("filesystems")
    if not isinstance(rows, list) or len(rows) != 1:
        raise SecurityError("Expected exactly one actual staging mount")
    row = _object(rows[0], "findmnt row")
    options = row.get("options")
    if (
        row.get("target") != contract["mountpoint"]
        or row.get("source") != resolved_device
        or row.get("uuid") != contract["filesystem_uuid"]
        or row.get("fstype") != "ext4"
        or not isinstance(options, str)
        or "rw" not in options.split(",")
        or mount_device == root_device
    ):
        raise SecurityError(
            "Staging mount does not bind the admitted device, UUID and writable ext4"
        )


def check_storage(project_dir: Path) -> dict[str, object]:
    receipt = project_dir / ".staging-storage.json"
    _regular_file(receipt, 0, 0, 0o600)
    contract = validate_contract(_read_json(receipt.read_text(encoding="utf-8")))
    device = Path(DEVICE_PATH)
    if not stat.S_ISBLK(device.stat().st_mode):
        raise SecurityError("The admitted DigitalOcean device is not a block device")
    if _native(["blockdev", "--getsize64", DEVICE_PATH]).strip() != str(50 * 1024**3):
        raise SecurityError("The actual staging device must have the admitted 50 GiB capacity")
    root = Path(STORAGE_ROOT)
    mount_device = root.lstat().st_dev
    observed = _read_json(
        _native(
            [
                "findmnt",
                "--json",
                "--mountpoint",
                STORAGE_ROOT,
                "--output",
                "SOURCE,TARGET,FSTYPE,UUID,OPTIONS",
            ]
        )
    )
    validate_mount(
        contract, observed, str(device.resolve(strict=True)), mount_device, Path("/").stat().st_dev
    )
    _directory(root, 0, 0, 0o755, mount_device)
    for name, uid, gid in (
        ("postgres", 70, 70),
        ("prometheus", 65532, 65532),
        ("backups", 0, 0),
        ("secrets", 0, 0),
    ):
        _directory(root / name, uid, gid, 0o700, mount_device)
    _directory(project_dir / "secrets", 0, 0, 0o700, mount_device)
    if not (project_dir / "secrets").samefile(root / "secrets"):
        raise SecurityError(
            "Staging secrets must be bind-mounted from the admitted encrypted volume"
        )
    return contract


def check_tls(
    project_dir: Path, contract: dict[str, object], database_environment: dict[str, object]
) -> None:
    secrets = project_dir / "secrets"
    metadata = secrets.lstat()
    _directory(secrets, 0, 0, 0o700, metadata.st_dev)
    owners = {
        "postgres_ca": (0, 0, 0o444),
        "postgres_server_crt": (0, 0, 0o444),
        "postgres_server_key": (0, 70, 0o640),
        "postgres_password": (70, 70, 0o400),
        "postgres_pgpass": (
            cast(int, contract["backend_uid"]),
            cast(int, contract["backend_gid"]),
            0o600,
        ),
    }
    for name, owner in owners.items():
        _regular_file(secrets / name, *owner, metadata.st_dev)
    ca, certificate, key = (
        secrets / name for name in ("postgres_ca", "postgres_server_crt", "postgres_server_key")
    )
    _native(
        [
            "openssl",
            "verify",
            "-CAfile",
            str(ca),
            "-purpose",
            "sslserver",
            "-verify_hostname",
            "postgres",
            str(certificate),
        ]
    )
    _native(["openssl", "x509", "-in", str(certificate), "-noout", "-checkend", "86400"])
    public_certificate = _native(["openssl", "x509", "-in", str(certificate), "-pubkey", "-noout"])
    public_key = _native(["openssl", "pkey", "-in", str(key), "-pubout"])
    if not hmac.compare_digest(public_certificate, public_key):
        raise SecurityError("PostgreSQL certificate and server key differ")
    database = database_environment.get("POSTGRES_DB")
    user = database_environment.get("POSTGRES_USER")
    if any(
        not isinstance(value, str) or re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value) is None
        for value in (database, user)
    ):
        raise SecurityError("Staging database and role must use admitted lowercase identifiers")
    password = (secrets / "postgres_password").read_text(encoding="ascii").removesuffix("\n")
    if re.fullmatch(r"[A-Za-z0-9_-]{32,128}", password) is None:
        raise SecurityError("Staging password file is not one admitted generated secret")
    expected_passfile = f"postgres:5432:{database}:{user}:{password}\n"
    if not hmac.compare_digest(
        (secrets / "postgres_pgpass").read_text(encoding="ascii"), expected_passfile
    ):
        raise SecurityError(
            "Staging libpq password file does not match the selected database identity"
        )
    hba = project_dir / "postgres-pgvector" / "pg_hba.conf"
    _regular_file(hba, 0, 0, 0o444)
    rules = [
        line.strip()
        for line in hba.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if rules != [
        "local all all trust",
        "hostnossl all all all reject",
        "hostssl all all all scram-sha-256",
    ]:
        raise SecurityError("Staging PostgreSQL HBA rules differ from the TLS-only contract")


def validate_compose(value: object, project_dir: Path) -> None:
    document = _object(value, "Compose")
    services = _object(document.get("services"), "Compose services")
    postgres = _object(services.get("postgres"), "PostgreSQL service")
    if postgres.get("command") != POSTGRES_COMMAND or postgres.get("ports"):
        raise SecurityError("PostgreSQL must retain the exact TLS-only command and no public ports")
    environment = _object(postgres.get("environment"), "PostgreSQL environment")
    if environment.get(
        "POSTGRES_PASSWORD_FILE"
    ) != "/run/secrets/postgres_password" or environment.get("POSTGRES_PASSWORD"):
        raise SecurityError("PostgreSQL server password must use its admitted secret file")
    db_networks = _object(document.get("networks"), "Compose networks")
    if _object(db_networks.get("database"), "Database network").get("internal") is not True:
        raise SecurityError("PostgreSQL network must be internal")
    if set(_object(postgres.get("networks"), "PostgreSQL networks")) != {"database"}:
        raise SecurityError("PostgreSQL must join only the private database network")
    for service_name in ("app", "worker"):
        service = _object(services.get(service_name), service_name)
        client = _object(service.get("environment"), f"{service_name} environment")
        dsn = client.get("DATABASE_URL")
        if not isinstance(dsn, str):
            raise SecurityError("Missing canonical PostgreSQL client URL")
        parsed = urlsplit(dsn)
        options = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        expected_options = {
            "sslmode": "verify-full",
            "sslrootcert": "/run/secrets/postgres_ca",
            "passfile": "/run/secrets/postgres_pgpass",
        }
        if (
            parsed.scheme != "postgresql+psycopg"
            or parsed.hostname != "postgres"
            or parsed.port != 5432
            or parsed.password is not None
            or parsed.fragment
            or unquote(parsed.username or "") != environment.get("POSTGRES_USER")
            or unquote(parsed.path.removeprefix("/")) != environment.get("POSTGRES_DB")
            or len(options) != len(expected_options)
            or dict(options) != expected_options
            or client.get("PGSSLMODE") != "verify-full"
            or client.get("PGPASSFILE") != "/run/secrets/postgres_pgpass"
            or client.get("PGPASSWORD")
            or client.get("POSTGRES_PASSWORD")
        ):
            raise SecurityError(
                f"{service_name} must use the matching file-backed verify-full database identity"
            )
    volumes = _object(document.get("volumes"), "Compose volumes")
    for name, directory in (("postgres_data", "postgres"), ("prometheus_data", "prometheus")):
        volume = _object(volumes.get(name), name)
        if volume.get("driver") != "local" or volume.get("driver_opts") != {
            "type": "none",
            "o": "bind",
            "device": f"{STORAGE_ROOT}/{directory}",
        }:
            raise SecurityError(f"{name} must bind the admitted encrypted storage directory")
    secrets = _object(document.get("secrets"), "Compose secrets")
    for name in (
        "postgres_ca",
        "postgres_server_crt",
        "postgres_server_key",
        "postgres_password",
        "postgres_pgpass",
    ):
        source = _object(secrets.get(name), name).get("file")
        if not isinstance(source, str) or Path(source) != project_dir / "secrets" / name:
            raise SecurityError(f"{name} must use the admitted host file")


def check_daemon_guard(project_dir: Path) -> None:
    installed = Path("/etc/systemd/system/docker.service.d/pulseplate-storage.conf")
    _regular_file(installed, 0, 0, 0o644)
    expected = project_dir / "systemd" / "pulseplate-staging-storage.conf"
    _regular_file(expected, 0, 0, 0o644)
    if installed.read_bytes() != expected.read_bytes():
        raise SecurityError("Docker storage lifecycle guard differs from the deployed contract")
    mount_units = {
        r"mnt-pulseplate\x2dstaging\x2ddata.mount",
        r"srv-pulseplate\x2dstaging-secrets.mount",
    }
    bound_units = _native(
        ["systemctl", "show", "docker.service", "--property=BindsTo", "--value"]
    ).split()
    if not mount_units.issubset(bound_units):
        raise SecurityError("Docker has not loaded its staging mount dependency")
    if _native(["docker", "info", "--format", "{{.LiveRestoreEnabled}}"]).strip() != "false":
        raise SecurityError("Docker live restore would bypass the storage lifecycle boundary")


def check_existing_volumes(value: object) -> None:
    volumes = _object(_object(value, "Compose").get("volumes"), "Compose volumes")
    existing = _native(["docker", "volume", "ls", "--format", "{{.Name}}"]).splitlines()
    if any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name) is None for name in existing):
        raise SecurityError("Docker volume census is malformed")
    for key in ("postgres_data", "prometheus_data"):
        requested = _object(volumes.get(key), key)
        name = requested.get("name")
        if (
            not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name) is None
        ):
            raise SecurityError("Rendered named-volume identity is missing or invalid")
        if name not in existing:
            continue
        inspected = _read_json(_native(["docker", "volume", "inspect", name]))
        if not isinstance(inspected, list) or len(inspected) != 1:
            raise SecurityError("Docker named-volume inspection is ambiguous")
        actual = _object(inspected[0], "Docker volume")
        if actual.get("Driver") != "local" or actual.get("Options") != requested.get("driver_opts"):
            raise SecurityError(
                "Existing named volume has different storage backing; preserve it and migrate explicitly"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("/srv/pulseplate-staging"))
    parser.add_argument("--storage-only", action="store_true")
    parser.add_argument("--compose-stdin", action="store_true")
    parser.add_argument("--print-backup-dir", action="store_true")
    arguments = parser.parse_args()
    try:
        contract = check_storage(arguments.project_dir)
        composed = _read_json(sys.stdin.read()) if arguments.compose_stdin else None
        if composed is not None:
            validate_compose(composed, arguments.project_dir)
        if not arguments.storage_only:
            if composed is None:
                raise SecurityError("Full TLS verification requires the selected rendered Compose")
            services = _object(_object(composed, "Compose").get("services"), "Compose services")
            database_environment = _object(
                _object(services.get("postgres"), "PostgreSQL").get("environment"),
                "PostgreSQL environment",
            )
            check_tls(arguments.project_dir, contract, database_environment)
            check_daemon_guard(arguments.project_dir)
        if composed is not None:
            check_existing_volumes(composed)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Staging security HOLD: {error}", file=sys.stderr)
        return 1
    if arguments.print_backup_dir:
        print(STORAGE_ROOT + "/backups")
        return 0
    print(
        "Staging storage binding verified"
        if arguments.storage_only
        else "Staging storage and TLS inputs verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
