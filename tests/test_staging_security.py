"""Fail-closed staging mount, TLS and credential boundary tests."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import io
import stat
from typing import Any

import pytest

from scripts.ops import check_staging_security as security


def contract() -> dict[str, Any]:
    return {
        "schema": "pulseplate.staging-storage.v1",
        "droplet_id": 594869239,
        "volume_id": "12345678-1234-1234-1234-123456789abc",
        "volume_name": "pulseplate-staging-data",
        "filesystem_uuid": "abcdef12-1234-1234-1234-123456789abc",
        "mountpoint": security.STORAGE_ROOT,
        "device": security.DEVICE_PATH,
        "size_gib": 50,
        "backend_uid": 999,
        "backend_gid": 999,
    }


def test_closed_storage_receipt_accepts_the_authorized_target() -> None:
    assert security.validate_contract(contract()) == contract()


@pytest.mark.parametrize(
    "key,value",
    [
        ("droplet_id", 527755209),
        ("droplet_id", True),
        ("size_gib", 100),
        ("mountpoint", "/"),
        ("device", "/dev/vda1"),
        ("volume_id", "unknown"),
        ("filesystem_uuid", 5),
        ("backend_uid", 0),
        ("backend_gid", True),
        ("backend_gid", 65536),
        ("schema", "later"),
        ("volume_name", "other"),
    ],
)
def test_unapproved_storage_receipts_fail(key: str, value: object) -> None:
    record = contract()
    record[key] = value
    with pytest.raises(security.SecurityError):
        security.validate_contract(record)


@pytest.mark.parametrize("value", [None, [], {1: "bad"}, {}, {"extra": True}])
def test_incomplete_or_untyped_storage_receipt_fails(value: object) -> None:
    with pytest.raises(security.SecurityError):
        security.validate_contract(value)


@pytest.mark.parametrize("text", ['{"id":1,"id":2}', '{"id":NaN}', '{"id":Infinity}', "{"])
def test_json_does_not_accept_ambiguous_or_nonfinite_values(text: str) -> None:
    with pytest.raises(ValueError):
        security._read_json(text)


def mounted() -> dict[str, Any]:
    return {
        "filesystems": [
            {
                "source": "/dev/sda",
                "target": security.STORAGE_ROOT,
                "fstype": "ext4",
                "uuid": contract()["filesystem_uuid"],
                "options": "rw,relatime",
            }
        ]
    }


def test_actual_mount_accepts_matching_device_separate_from_root() -> None:
    security.validate_mount(contract(), mounted(), "/dev/sda", 42, 1)


@pytest.mark.parametrize(
    "key,value",
    [
        ("source", "/dev/vda1"),
        ("target", "/"),
        ("uuid", "other"),
        ("fstype", "tmpfs"),
        ("options", "ro,relatime"),
        ("options", None),
    ],
)
def test_real_mount_drift_is_rejected(key: str, value: object) -> None:
    observed = mounted()
    observed["filesystems"][0][key] = value
    with pytest.raises(security.SecurityError):
        security.validate_mount(contract(), observed, "/dev/sda", 42, 1)


@pytest.mark.parametrize("rows", [None, [], [{}, {}], [False]])
def test_ambiguous_mount_observation_fails(rows: object) -> None:
    with pytest.raises(security.SecurityError):
        security.validate_mount(contract(), {"filesystems": rows}, "/dev/sda", 42, 1)


def test_matching_pathname_on_root_disk_is_not_encrypted_mount_proof() -> None:
    with pytest.raises(security.SecurityError):
        security.validate_mount(contract(), mounted(), "/dev/sda", 1, 1)


def test_secret_file_metadata_rejects_links_and_insecure_permissions(tmp_path: Path) -> None:
    secret = tmp_path / "key"
    secret.write_text("synthetic")
    secret.chmod(0o600)
    security._regular_file(secret, os.getuid(), os.getgid(), 0o600)
    linked = tmp_path / "linked"
    linked.symlink_to(secret)
    with pytest.raises(security.SecurityError):
        security._regular_file(linked, os.getuid(), os.getgid(), 0o600)
    hard = tmp_path / "hard"
    os.link(secret, hard)
    with pytest.raises(security.SecurityError):
        security._regular_file(secret, os.getuid(), os.getgid(), 0o600)
    hard.unlink()
    secret.chmod(0o644)
    with pytest.raises(security.SecurityError):
        security._regular_file(secret, os.getuid(), os.getgid(), 0o600)


def test_data_directory_requires_real_directory_owner_mode_and_device(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    device = data.stat().st_dev
    security._directory(data, os.getuid(), os.getgid(), 0o700, device)
    for uid, mode, expected_device in (
        (os.getuid() + 1, 0o700, device),
        (os.getuid(), 0o755, device),
        (os.getuid(), 0o700, device + 1),
    ):
        with pytest.raises(security.SecurityError):
            security._directory(data, uid, os.getgid(), mode, expected_device)
    link = tmp_path / "alias"
    link.symlink_to(data)
    with pytest.raises(security.SecurityError):
        security._directory(link, os.getuid(), os.getgid(), 0o700, device)


def test_native_failure_is_not_absence_or_secret_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.shutil, "which", lambda _: "/usr/bin/findmnt")

    def failed(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert args[0][0] == "/usr/bin/findmnt"
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(args[0], 1, "private-data", "private-key")

    monkeypatch.setattr(security.subprocess, "run", failed)
    with pytest.raises(security.SecurityError, match="exit 1") as error:
        security._native(["findmnt", "--json"])
    assert "private" not in str(error.value)
    monkeypatch.setattr(security.shutil, "which", lambda _: None)
    with pytest.raises(security.SecurityError, match="unavailable"):
        security._native(["findmnt"])


def compose(project: Path) -> dict[str, Any]:
    client = {
        "DATABASE_URL": "postgresql+psycopg://pulseplate@postgres:5432/pulseplate?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca&passfile=/run/secrets/postgres_pgpass",
        "PGSSLMODE": "verify-full",
        "PGPASSFILE": "/run/secrets/postgres_pgpass",
    }
    return {
        "name": "pulseplate-staging",
        "services": {
            "postgres": {
                "command": security.POSTGRES_COMMAND.copy(),
                "networks": {"database": None},
                "environment": {
                    "POSTGRES_DB": "pulseplate",
                    "POSTGRES_USER": "pulseplate",
                    "POSTGRES_PASSWORD_FILE": "/run/secrets/postgres_password",
                },
            },
            "app": {"environment": copy.deepcopy(client)},
            "worker": {"environment": copy.deepcopy(client)},
            "prometheus": {"image": "prom/prometheus@sha256:" + "a" * 64},
        },
        "networks": {"database": {"internal": True}},
        "volumes": {
            name: {
                "name": "pulseplate-staging_" + name + "_v5",
                "driver": "local",
                "driver_opts": {
                    "type": "none",
                    "o": "bind",
                    "device": f"{security.STORAGE_ROOT}/{folder}",
                },
            }
            for name, folder in (("postgres_data", "postgres"), ("prometheus_data", "prometheus"))
        },
        "secrets": {
            name: {"file": str(project / "secrets" / name)}
            for name in (
                "postgres_ca",
                "postgres_server_crt",
                "postgres_server_key",
                "postgres_password",
                "postgres_pgpass",
            )
        },
    }


def test_rendered_compose_uses_private_tls_and_file_backed_credentials(tmp_path: Path) -> None:
    security.validate_compose(compose(tmp_path), tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "tls-off",
        "duplicate-executable",
        "public-port",
        "public-network",
        "wrong-network",
        "password-env",
        "missing-dsn",
        "downgrade",
        "duplicate-option",
        "password-url",
        "wrong-host",
        "wrong-user",
        "pgpassword",
        "bad-passfile",
        "root-volume",
        "secret-source",
    ],
)
def test_rendered_compose_cannot_downgrade_security(tmp_path: Path, mutation: str) -> None:
    value = compose(tmp_path)
    postgres = value["services"]["postgres"]
    client = value["services"]["worker"]["environment"]
    if mutation == "tls-off":
        postgres["command"] += ["-c", "ssl=off"]
    elif mutation == "duplicate-executable":
        postgres["command"].insert(0, "postgres")
    elif mutation == "public-port":
        postgres["ports"] = [{"published": "5432"}]
    elif mutation == "public-network":
        value["networks"]["database"]["internal"] = False
    elif mutation == "wrong-network":
        postgres["networks"]["web"] = None
    elif mutation == "password-env":
        postgres["environment"]["POSTGRES_PASSWORD"] = "synthetic"
    elif mutation == "missing-dsn":
        client.pop("DATABASE_URL")
    elif mutation == "downgrade":
        client["DATABASE_URL"] = client["DATABASE_URL"].replace("verify-full", "prefer")
    elif mutation == "duplicate-option":
        client["DATABASE_URL"] += "&sslmode=disable"
    elif mutation == "password-url":
        client["DATABASE_URL"] = client["DATABASE_URL"].replace(
            "pulseplate@", "pulseplate:synthetic@"
        )
    elif mutation == "wrong-host":
        client["DATABASE_URL"] = client["DATABASE_URL"].replace("@postgres:", "@other:")
    elif mutation == "wrong-user":
        client["DATABASE_URL"] = client["DATABASE_URL"].replace("://pulseplate@", "://other@")
    elif mutation == "pgpassword":
        client["PGPASSWORD"] = "synthetic"
    elif mutation == "bad-passfile":
        client["PGPASSFILE"] = "/tmp/public"
    elif mutation == "root-volume":
        value["volumes"]["postgres_data"]["driver_opts"]["device"] = "/var/lib/docker"
    elif mutation == "secret-source":
        value["secrets"]["postgres_ca"]["file"] = "/tmp/other"
    with pytest.raises(security.SecurityError):
        security.validate_compose(value, tmp_path)


@pytest.mark.parametrize(
    "existing_options", [None, {}, {"type": "none", "o": "bind", "device": "/old/data"}]
)
def test_existing_volume_is_preserved_when_storage_backing_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing_options: object
) -> None:
    calls: list[list[str]] = []

    def native(args: list[str]) -> str:
        calls.append(args)
        if args[2] == "ls":
            return "pulseplate-staging_postgres_data_v5\n"
        return json.dumps([{"Driver": "local", "Options": existing_options}])

    monkeypatch.setattr(security, "_native", native)
    with pytest.raises(security.SecurityError, match="preserve"):
        security.check_existing_volumes(compose(tmp_path))
    assert all("rm" not in command and "create" not in command for command in calls)


def test_existing_matching_and_absent_volumes_are_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_backing: Path
) -> None:
    value = compose(tmp_path)

    def native(args: list[str]) -> str:
        if args[2] == "ls":
            return "pulseplate-staging_postgres_data_v5\npulseplate-staging_postgres_data\n"
        if args[1] == "ps":
            return ""
        return json.dumps(
            [
                {
                    "Name": value["volumes"]["postgres_data"]["name"],
                    "Driver": "local",
                    "Options": value["volumes"]["postgres_data"]["driver_opts"],
                }
            ]
        )

    monkeypatch.setattr(security, "_native", native)
    security.check_existing_volumes(value)


def test_source_database_restore_is_rejected_before_docker(tmp_path: Path) -> None:
    import shutil

    bash = shutil.which("bash")
    assert bash
    result = subprocess.run(
        [
            bash,
            "scripts/ops/postgres_restore.sh",
            "--verify-into",
            "pulseplate",
            str(tmp_path / "missing.dump"),
        ],
        env={
            **os.environ,
            "POSTGRES_DB": "pulseplate",
            "POSTGRES_USER": "pulseplate",
            "DOCKER_BIN": "/bin/echo",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "distinct" in result.stderr
    assert result.stdout == ""


@pytest.fixture
def tls_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (tmp_path / "postgres-pgvector").mkdir()
    for name in ("postgres_ca", "postgres_server_crt", "postgres_server_key"):
        (secrets / name).write_text("synthetic crypto-provider input")
    (secrets / "postgres_password").write_text("x" * 40)
    (secrets / "postgres_pgpass").write_text(
        "postgres:5432:pulseplate:pulseplate:" + "x" * 40 + "\n"
    )
    (tmp_path / "postgres-pgvector" / "pg_hba.conf").write_text(
        "local all all trust\nhostnossl all all all reject\nhostssl all all all scram-sha-256\n"
    )
    # Metadata and native cryptography have independent tests/host proof. This
    # fixture exercises their consumer and does not claim a real TLS handshake.
    monkeypatch.setattr(security, "_regular_file", lambda *args: None)
    monkeypatch.setattr(security, "_directory", lambda *args: None)
    monkeypatch.setattr(
        security,
        "_native",
        lambda args: "PUBLIC\n" if "-pubkey" in args or "-pubout" in args else "",
    )
    return tmp_path


def test_tls_identity_comes_from_selected_compose_not_host_env(
    tls_inputs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "wrong_ambient_user")
    monkeypatch.setenv("POSTGRES_DB", "wrong_ambient_database")
    security.check_tls(
        tls_inputs, contract(), {"POSTGRES_USER": "pulseplate", "POSTGRES_DB": "pulseplate"}
    )


@pytest.mark.parametrize(
    "failure", ["ca", "expiry", "keypair", "database", "password-shape", "passfile", "hba"]
)
def test_tls_or_credential_defects_fail_before_admission(
    tls_inputs: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    identity: dict[str, object] = {"POSTGRES_USER": "pulseplate", "POSTGRES_DB": "pulseplate"}
    if failure in ("ca", "expiry", "keypair"):

        def native(args: list[str]) -> str:
            if (failure == "ca" and "verify" in args) or (
                failure == "expiry" and "-checkend" in args
            ):
                raise security.SecurityError("Native certificate verification rejected input")
            return "OTHER" if "-pubout" in args else "PUBLIC"

        monkeypatch.setattr(security, "_native", native)
    elif failure == "database":
        identity["POSTGRES_DB"] = False
    elif failure == "password-shape":
        (tls_inputs / "secrets" / "postgres_password").write_text("unsafe:format")
    elif failure == "passfile":
        (tls_inputs / "secrets" / "postgres_pgpass").write_text("wrong endpoint")
    elif failure == "hba":
        (tls_inputs / "postgres-pgvector" / "pg_hba.conf").write_text("host all all all trust\n")
    with pytest.raises(security.SecurityError):
        security.check_tls(tls_inputs, contract(), identity)


def test_main_uses_selected_rendered_identity_without_host_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[dict[str, object]] = []
    monkeypatch.setattr(security, "check_storage", lambda path: contract())
    monkeypatch.setattr(
        security, "check_tls", lambda path, receipt, environment: seen.append(environment)
    )
    monkeypatch.setattr(security, "check_daemon_guard", lambda path: None)
    monkeypatch.setattr(security, "check_backup_units", lambda path: None)
    monkeypatch.setattr(security, "check_existing_volumes", lambda value: None)
    monkeypatch.setattr(
        security.sys, "argv", ["checker", "--project-dir", str(tmp_path), "--compose-stdin"]
    )
    monkeypatch.setattr(security.sys, "stdin", io.StringIO(json.dumps(compose(tmp_path))))
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    assert security.main() == 0
    assert seen[0]["POSTGRES_USER"] == "pulseplate"
    assert "verified" in capsys.readouterr().out


def test_storage_only_path_receipt_requires_successful_mount_check(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(security.sys, "argv", ["checker", "--storage-only", "--print-backup-dir"])
    monkeypatch.setattr(security, "check_storage", lambda path: contract())
    assert security.main() == 0
    assert capsys.readouterr().out.strip() == security.STORAGE_ROOT + "/backups"

    def fail(path: Path) -> dict[str, object]:
        raise security.SecurityError("Wrong mounted device")

    monkeypatch.setattr(security, "check_storage", fail)
    assert security.main() == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert "HOLD" in result.err


def test_full_check_cannot_omit_selected_compose(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(security.sys, "argv", ["checker"])
    monkeypatch.setattr(security, "check_storage", lambda path: contract())
    assert security.main() == 1
    assert "selected rendered Compose" in capsys.readouterr().err


@pytest.fixture
def storage_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, object]]:
    root, project, device = tmp_path / "volume", tmp_path / "project", tmp_path / "device"
    root.mkdir()
    project.mkdir()
    device.touch()
    monkeypatch.setattr(security, "STORAGE_ROOT", str(root))
    monkeypatch.setattr(security, "DEVICE_PATH", str(device))
    record = contract()
    receipt = project / ".staging-storage.json"
    receipt.write_text(json.dumps(record))
    receipt.chmod(0o600)
    metadata: dict[Path, os.stat_result] = {}

    def observation(path: Path, uid: int, gid: int, mode: int, dev: int = 42) -> os.stat_result:
        values = list(path.lstat())
        values[0], values[2], values[4], values[5] = mode, dev, uid, gid
        return os.stat_result(values)

    for name, uid in (("postgres", 70), ("prometheus", 65532), ("backups", 0), ("secrets", 0)):
        path = root / name
        path.mkdir(mode=0o700)
        metadata[path] = observation(path, uid, uid, stat.S_IFDIR | 0o700)
    (project / "secrets").mkdir()
    metadata[project / "secrets"] = metadata[root / "secrets"]
    metadata[root] = observation(root, 0, 0, stat.S_IFDIR | 0o755)
    metadata[receipt] = observation(receipt, 0, 0, stat.S_IFREG | 0o600)
    metadata[device] = observation(device, 0, 0, stat.S_IFBLK | 0o600)
    native_stat, native_lstat = Path.stat, Path.lstat

    def observed_stat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        return metadata[path] if path in metadata else native_stat(path, *args, **kwargs)

    def observed_lstat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        return metadata[path] if path in metadata else native_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", observed_stat)
    monkeypatch.setattr(Path, "lstat", observed_lstat)
    outputs: dict[str, object] = {
        "size": str(50 * 1024**3),
        "mount": {
            "filesystems": [
                {
                    "source": str(device),
                    "target": str(root),
                    "uuid": record["filesystem_uuid"],
                    "fstype": "ext4",
                    "options": "rw,relatime",
                }
            ]
        },
    }

    def native(args: list[str]) -> str:
        if args[0] == "blockdev":
            return str(outputs["size"])
        assert args[0] == "findmnt" and "--mountpoint" in args
        return json.dumps(outputs["mount"])

    monkeypatch.setattr(security, "_native", native)
    return project, outputs


def test_native_storage_observations_bind_each_declared_directory(
    storage_observations: tuple[Path, dict[str, object]],
) -> None:
    project, _ = storage_observations
    result = security.check_storage(project)
    assert result["droplet_id"] == 594869239


@pytest.mark.parametrize("kind", ["capacity", "missing-mount", "bad-uuid"])
def test_native_storage_observation_failures_hold(
    storage_observations: tuple[Path, dict[str, object]], kind: str
) -> None:
    project, outputs = storage_observations
    if kind == "capacity":
        outputs["size"] = "4096"
    elif kind == "missing-mount":
        outputs["mount"] = {"filesystems": []}
    else:
        outputs["mount"] = {"filesystems": [{"uuid": "unrelated"}]}
    with pytest.raises(security.SecurityError):
        security.check_storage(project)


@pytest.mark.parametrize(
    "fault", [None, "file-drift", "missing-mount-unit", "live-restore", "unknown-live-restore"]
)
def test_docker_lifecycle_guard_requires_loaded_mount_binding_and_stop_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    monkeypatch.setattr(security, "_regular_file", lambda *args: None)

    def read_bytes(path: Path) -> bytes:
        return (
            b"drifted"
            if fault == "file-drift" and str(path).startswith("/etc/")
            else b"same-reviewed-unit"
        )

    monkeypatch.setattr(Path, "read_bytes", read_bytes)

    def native(args: list[str]) -> str:
        if args[0] == "systemctl":
            if fault == "missing-mount-unit":
                return "docker.socket"
            return (
                r"mnt-pulseplate\x2dstaging\x2ddata.mount srv-pulseplate\x2dstaging-secrets.mount"
            )
        return (
            "true"
            if fault == "live-restore"
            else "unknown" if fault == "unknown-live-restore" else "false"
        )

    monkeypatch.setattr(security, "_native", native)
    if fault is None:
        security.check_daemon_guard(tmp_path)
    else:
        with pytest.raises(security.SecurityError):
            security.check_daemon_guard(tmp_path)


@pytest.mark.parametrize("fault", ["malformed-census", "missing-name", "ambiguous-inspect"])
def test_unknown_volume_state_is_never_inferred_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    value = compose(tmp_path)
    if fault == "missing-name":
        value["volumes"]["postgres_data"].pop("name")

    def native(args: list[str]) -> str:
        if args[2] == "ls":
            return (
                "bad/name" if fault == "malformed-census" else "pulseplate-staging_postgres_data_v5"
            )
        return "[]"

    monkeypatch.setattr(security, "_native", native)
    with pytest.raises(security.SecurityError):
        security.check_existing_volumes(value)


def test_native_success_returns_only_native_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.shutil, "which", lambda _: "/usr/bin/findmnt")
    monkeypatch.setattr(
        security.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "observed", ""),
    )
    assert security._native(["findmnt", "--json"]) == "observed"


def test_secret_bind_mount_mismatch_is_rejected(
    storage_observations: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = storage_observations
    monkeypatch.setattr(Path, "samefile", lambda *args: False)
    with pytest.raises(security.SecurityError, match="bind-mounted"):
        security.check_storage(project)


def test_plain_file_cannot_impersonate_a_block_device(
    storage_observations: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = storage_observations
    monkeypatch.setattr(security.stat, "S_ISBLK", lambda _: False)
    with pytest.raises(security.SecurityError, match="block device"):
        security.check_storage(project)


@pytest.mark.parametrize(
    "file_name",
    [
        "postgres_ca",
        "postgres_server_crt",
        "postgres_server_key",
        "postgres_password",
        "postgres_pgpass",
    ],
)
def test_each_tls_credential_rejects_a_nested_other_device_mount(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_name: str
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    owners = {
        "postgres_ca": (0, 0, 0o444),
        "postgres_server_crt": (0, 0, 0o444),
        "postgres_server_key": (0, 70, 0o640),
        "postgres_password": (70, 70, 0o400),
        "postgres_pgpass": (contract()["backend_uid"], contract()["backend_gid"], 0o600),
    }
    for name in owners:
        (secrets / name).write_text("synthetic metadata-only input")
    native_lstat = Path.lstat

    def lstat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        metadata = list(native_lstat(path, *args, **kwargs))
        if path == secrets:
            metadata[0], metadata[2], metadata[4], metadata[5] = stat.S_IFDIR | 0o700, 42, 0, 0
        elif path.parent == secrets:
            uid, gid, mode = owners[path.name]
            metadata[0], metadata[2] = stat.S_IFREG | mode, 13 if path.name == file_name else 42
            metadata[4], metadata[5] = uid, gid
        return os.stat_result(metadata)

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(security.SecurityError, match="device"):
        security.check_tls(
            tmp_path, contract(), {"POSTGRES_USER": "pulseplate", "POSTGRES_DB": "pulseplate"}
        )


def test_v5_missing_service_preserves_legacy_history_and_requires_manual_cutover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_backing: Path
) -> None:
    value = compose(tmp_path)
    for key in ("postgres_data", "prometheus_data"):
        value["volumes"][key]["name"] = "pulseplate-staging_" + key + "_v5"
    calls: list[list[str]] = []

    def native(args: list[str]) -> str:
        calls.append(args)
        if args == ["docker", "volume", "ls", "--format", "{{.Name}}"]:
            return "pulseplate-staging_prometheus_data\n"
        assert args[:2] == ["docker", "ps"]
        return ""

    monkeypatch.setattr(security, "_native", native)
    security.validate_compose(value, tmp_path)
    with pytest.raises(security.SecurityError, match="trustworthy"):
        security.check_existing_volumes(value)
    assert all("rm" not in args and "create" not in args for args in calls)


@pytest.mark.parametrize("key", ["postgres_data", "prometheus_data"])
def test_v5_existing_volume_with_wrong_backing_holds_without_mutating_old_volumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, empty_backing: Path
) -> None:
    value = compose(tmp_path)
    for name in ("postgres_data", "prometheus_data"):
        value["volumes"][name]["name"] = "pulseplate-staging_" + name + "_v5"
    selected_name = value["volumes"][key]["name"]
    calls: list[list[str]] = []

    def native(args: list[str]) -> str:
        calls.append(args)
        if args[2] == "ls":
            return "pulseplate-staging_prometheus_data\n" + selected_name + "\n"
        assert args == ["docker", "volume", "inspect", selected_name]
        return json.dumps([{"Driver": "local", "Options": {}}])

    monkeypatch.setattr(security, "_native", native)
    with pytest.raises(security.SecurityError, match="preserve it and migrate explicitly"):
        security.check_existing_volumes(value)
    assert calls[-1][-1] == selected_name
    assert all("create" not in args and "rm" not in args for args in calls)


@pytest.fixture
def empty_backing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    root.mkdir()
    for name in ("postgres", "prometheus"):
        (root / name).mkdir(mode=0o700)
    monkeypatch.setattr(security, "STORAGE_ROOT", str(root))
    return root


def test_fresh_backing_census_detects_data_appearing_before_start(empty_backing: Path) -> None:
    security.check_empty_data_directory("postgres")
    (empty_backing / "postgres" / "PG_VERSION").write_text("15\n")
    with pytest.raises(security.SecurityError, match="populated"):
        security.check_empty_data_directory("postgres")


@pytest.mark.parametrize("entry", ["PG_VERSION", ".hidden", "directory", "link", "fifo"])
def test_fresh_backing_rejects_every_kind_of_existing_entry(
    empty_backing: Path, entry: str
) -> None:
    path = empty_backing / "postgres" / entry
    if entry == "directory":
        path.mkdir()
    elif entry == "link":
        path.symlink_to("missing")
    elif entry == "fifo":
        os.mkfifo(path)
    else:
        path.touch()
    with pytest.raises(security.SecurityError, match="populated"):
        security.check_empty_data_directory("postgres")
    assert path.lstat()


@pytest.mark.parametrize(
    "fault",
    [
        "symlink",
        "file",
        "fifo",
        "unreadable",
        "missing",
        "list-error",
        "replace-before-open",
        "replace-after-list",
    ],
)
def test_fresh_backing_rejects_unreadable_or_replaced_directory(
    empty_backing: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    path = empty_backing / "postgres"
    if fault in {"symlink", "file", "fifo", "missing"}:
        path.rmdir()
        if fault == "symlink":
            path.symlink_to(empty_backing / "prometheus", target_is_directory=True)
        elif fault == "file":
            path.touch()
        elif fault == "fifo":
            os.mkfifo(path)
    elif fault == "unreadable":
        path.chmod(0o300)
    elif fault == "list-error":

        def denied(descriptor: int) -> Any:
            raise PermissionError("Synthetic census denial")

        monkeypatch.setattr(security.os, "scandir", denied)
    else:
        native = security.os.open if fault == "replace-before-open" else security.os.scandir

        def replaced(*args: Any, **kwargs: Any) -> Any:
            path.rename(empty_backing / "preserved")
            path.mkdir(mode=0o700)
            return native(*args, **kwargs)

        monkeypatch.setattr(
            security.os, "open" if fault == "replace-before-open" else "scandir", replaced
        )
    try:
        with pytest.raises((security.SecurityError, OSError)):
            security.check_empty_data_directory("postgres")
    finally:
        if fault == "unreadable":
            path.chmod(0o700)


def test_fresh_postgres_cli_requires_empty_backing_after_mount_admission(
    empty_backing: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(security, "check_storage", lambda path: contract())
    monkeypatch.setattr(security.sys, "argv", ["checker", "--storage-only", "--fresh-postgres"])
    assert security.main() == 0
    (empty_backing / "postgres" / ".retained").touch()
    assert security.main() == 1
    assert "populated" in capsys.readouterr().err


@pytest.fixture
def prometheus_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_backing: Path
) -> dict[str, Any]:
    value = compose(tmp_path)
    name = value["volumes"]["prometheus_data"]["name"]
    volume = {
        "Name": name,
        "Driver": "local",
        "Options": value["volumes"]["prometheus_data"]["driver_opts"],
        "Mountpoint": "/var/lib/docker/volumes/" + name + "/_data",
    }
    container = {
        "Id": "b" * 64,
        "Config": {
            "Image": value["services"]["prometheus"]["image"],
            "Labels": {
                "com.docker.compose.project": "pulseplate-staging",
                "com.docker.compose.service": "prometheus",
                "com.docker.compose.oneoff": "False",
            },
        },
        "State": {"Running": True, "Status": "running", "Health": {"Status": "healthy"}},
        "Mounts": [
            {
                "Destination": "/prometheus",
                "Type": "volume",
                "Name": name,
                "RW": True,
                "Source": volume["Mountpoint"],
            }
        ],
    }
    outputs: dict[str, Any] = {
        "compose": value,
        "existing": [name, "pulseplate-staging_prometheus_data"],
        "ids": "b" * 64,
        "container": [container],
        "volume": [volume],
        "calls": [],
    }

    def native(args: list[str]) -> str:
        outputs["calls"].append(args)
        if args[:2] == ["docker", "ps"]:
            assert "--all" in args and "--no-trunc" in args
            assert "label=com.docker.compose.project=pulseplate-staging" in args
            assert "label=com.docker.compose.service=prometheus" in args
            return str(outputs["ids"])
        if args[:2] == ["docker", "inspect"]:
            return json.dumps(outputs["container"])
        assert args == ["docker", "volume", "inspect", name]
        return json.dumps(outputs["volume"])

    monkeypatch.setattr(security, "_native", native)
    return outputs


def test_prometheus_retains_legacy_volume_after_verified_v5_cutover(
    prometheus_observations: dict[str, Any],
) -> None:
    o = prometheus_observations
    security.check_prometheus_state(o["compose"], o["existing"])
    assert all("rm" not in command and "create" not in command for command in o["calls"])


def test_prometheus_genuinely_fresh_state_requires_empty_backing(
    prometheus_observations: dict[str, Any], empty_backing: Path
) -> None:
    o = prometheus_observations
    o["ids"] = ""
    security.check_prometheus_state(o["compose"], [])
    (empty_backing / "prometheus" / "wal").mkdir()
    with pytest.raises(security.SecurityError, match="populated"):
        security.check_prometheus_state(o["compose"], [])


@pytest.mark.parametrize(
    "fault",
    [
        "legacy-only",
        "v5-without-service",
        "multiple",
        "malformed-id",
        "ambiguous-container",
        "missing-config",
        "missing-labels",
        "wrong-project",
        "wrong-service",
        "oneoff",
        "wrong-id",
        "old-image",
        "stopped",
        "unhealthy",
        "missing-health",
        "missing-v5",
        "legacy-mount",
        "duplicate-mount",
        "absent-mount",
        "bad-mounts",
        "nonobject-mount",
        "bind-mount",
        "readonly",
        "wrong-source",
        "ambiguous-volume",
        "renamed-volume",
        "wrong-driver",
        "old-options",
        "missing-mountpoint",
        "relative-mountpoint",
        "project-drift",
        "volume-name-drift",
    ],
)
def test_prometheus_history_ambiguity_holds_without_mutation(
    prometheus_observations: dict[str, Any], fault: str
) -> None:
    o = prometheus_observations
    c, v = o["container"][0], o["volume"][0]
    mount = c["Mounts"][0]
    if fault in {"legacy-only", "v5-without-service"}:
        o["ids"] = ""
        o["existing"] = o["existing"][1:] if fault == "legacy-only" else o["existing"][:1]
    elif fault == "multiple":
        o["ids"] += "\n" + "c" * 64
    elif fault == "malformed-id":
        o["ids"] = "not-an-id"
    elif fault == "ambiguous-container":
        o["container"] *= 2
    elif fault == "missing-config":
        c.pop("Config")
    elif fault == "missing-labels":
        c["Config"].pop("Labels")
    elif fault in {"wrong-project", "wrong-service", "oneoff"}:
        key = {"wrong-project": "project", "wrong-service": "service", "oneoff": "oneoff"}[fault]
        c["Config"]["Labels"]["com.docker.compose." + key] = "other"
    elif fault == "wrong-id":
        c["Id"] = "c" * 64
    elif fault == "old-image":
        c["Config"]["Image"] = "prom/prometheus:old"
    elif fault == "stopped":
        c["State"]["Running"] = False
    elif fault == "unhealthy":
        c["State"]["Health"]["Status"] = "unhealthy"
    elif fault == "missing-health":
        c["State"].pop("Health")
    elif fault == "missing-v5":
        o["existing"] = o["existing"][1:]
    elif fault == "legacy-mount":
        mount["Name"] = "pulseplate-staging_prometheus_data"
    elif fault == "duplicate-mount":
        c["Mounts"] *= 2
    elif fault == "absent-mount":
        c["Mounts"] = []
    elif fault == "bad-mounts":
        c["Mounts"] = None
    elif fault == "nonobject-mount":
        c["Mounts"] = [False]
    elif fault == "bind-mount":
        mount["Type"] = "bind"
    elif fault == "readonly":
        mount["RW"] = False
    elif fault == "wrong-source":
        mount["Source"] = "/old/history"
    elif fault == "ambiguous-volume":
        o["volume"] = []
    elif fault == "renamed-volume":
        v["Name"] = "other"
    elif fault == "wrong-driver":
        v["Driver"] = "remote"
    elif fault == "old-options":
        v["Options"] = {}
    elif fault == "missing-mountpoint":
        v.pop("Mountpoint")
    elif fault == "relative-mountpoint":
        v["Mountpoint"] = "relative"
    elif fault == "project-drift":
        o["compose"]["name"] = "new-project"
    elif fault == "volume-name-drift":
        o["compose"]["volumes"]["prometheus_data"]["name"] = "other"
    with pytest.raises(security.SecurityError):
        security.check_prometheus_state(o["compose"], o["existing"])
    assert all("rm" not in command and "create" not in command for command in o["calls"])


@pytest.fixture
def backup_observations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    project = Path("/srv/pulseplate-staging")
    paths: dict[Path, Path] = {}
    for suffix in ("service", "timer"):
        name = "pulseplate-postgres-backup." + suffix
        source = Path("deploy/systemd") / (
            "pulseplate-staging-postgres-backup.service.example"
            if suffix == "service"
            else name + ".example"
        )
        for location in (
            Path("/etc/systemd/system") / name,
            project / "systemd" / (name + ".example"),
        ):
            target = tmp_path / str(len(paths))
            target.write_bytes(source.read_bytes())
            target.chmod(0o644)
            paths[location] = target
    native_lstat, native_read = Path.lstat, Path.read_bytes

    def lstat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        if path not in paths:
            return native_lstat(path, *args, **kwargs)
        values = list(native_lstat(paths[path], *args, **kwargs))
        values[4] = values[5] = 0
        return os.stat_result(values)

    def read(path: Path) -> bytes:
        return native_read(paths.get(path, path))

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "read_bytes", read)
    mounts = [
        r"mnt-pulseplate\x2dstaging\x2ddata.mount",
        r"srv-pulseplate\x2dstaging-secrets.mount",
    ]
    properties: dict[str, tuple[str, object]] = {
        "User": ("s", "root"),
        "Type": ("s", "oneshot"),
        "WorkingDirectory": ("s", str(project)),
        "EnvironmentFiles": ("a(sb)", [[str(project / ".env"), False]]),
        "Environment": (
            "as",
            [
                f"PROJECT_DIR={project}",
                "ENV_FILE=/srv/pulseplate-staging/.env",
                "COMPOSE_FILE=docker-compose.staging.yaml",
                f"BACKUP_DIR={security.STORAGE_ROOT}/backups",
            ],
        ),
        # Observed systemd 255 D-Bus tuple shapes; timestamps/PID/status are runtime data.
        "ExecStartPre": (
            "a(sasbttttuii)",
            [
                [
                    "/usr/bin/python3",
                    [
                        "/usr/bin/python3",
                        "/srv/pulseplate-staging/scripts/ops/check_staging_security.py",
                        "--project-dir",
                        "/srv/pulseplate-staging",
                        "--storage-only",
                    ],
                    False,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]
            ],
        ),
        "ExecStart": (
            "a(sasbttttuii)",
            [
                [
                    "/usr/bin/bash",
                    ["/usr/bin/bash", "/srv/pulseplate-staging/scripts/ops/postgres_backup.sh"],
                    False,
                    1789200000,
                    100,
                    1789200010,
                    110,
                    500,
                    1,
                    0,
                ]
            ],
        ),
        "BindsTo": ("as", mounts),
        "After": ("as", mounts + ["docker.service", "network-online.target", "sysinit.target"]),
        "RequiresMountsFor": (
            "as",
            ["/mnt/pulseplate-staging-data", "/srv/pulseplate-staging/secrets"],
        ),
        "Unit": ("s", "pulseplate-postgres-backup.service"),
        "Persistent": ("b", True),
        "TimersCalendar": ("a(sst)", [["OnCalendar", "*-*-* 02:15:00", 1789279200000000]]),
        "UnitFileState": ("s", "enabled"),
        "ActiveState": ("s", "active"),
    }
    output: dict[str, Any] = {
        "project": project,
        "paths": paths,
        "properties": properties,
        "show_override": {},
        "calls": [],
    }

    def native(args: list[str]) -> str:
        output["calls"].append(args)
        if args[0] == "systemctl":
            suffix, name = args[2].rsplit(".", 1)[1], args[3].removeprefix("--property=")
            expected = {
                "LoadState": "loaded",
                "FragmentPath": "/etc/systemd/system/pulseplate-postgres-backup." + suffix,
                "DropInPaths": "",
                "NeedDaemonReload": "no",
            }
            return str(output["show_override"].get((suffix, name), expected[name])) + "\n"
        assert args[:4] == ["busctl", "--json=short", "get-property", "org.freedesktop.systemd1"]
        name = args[-1]
        signature, value = properties[name]
        return json.dumps({"type": signature, "data": value})

    monkeypatch.setattr(security, "_native", native)
    return output


def test_backup_units_bind_installed_bytes_and_loaded_native_properties(
    backup_observations: dict[str, Any],
) -> None:
    o = backup_observations
    security.check_backup_units(o["project"])
    assert all("daemon-reload" not in args and "start" not in args for args in o["calls"])


@pytest.mark.parametrize("suffix", ["service", "timer"])
@pytest.mark.parametrize("fault", ["missing", "symlink", "hardlink", "stale", "generic", "mode"])
def test_backup_installed_unit_mismatch_holds(
    backup_observations: dict[str, Any], tmp_path: Path, suffix: str, fault: str
) -> None:
    o = backup_observations
    target = o["paths"][Path("/etc/systemd/system/pulseplate-postgres-backup." + suffix)]
    if fault in {"missing", "symlink"}:
        target.unlink()
        if fault == "symlink":
            target.symlink_to(tmp_path / "missing")
    elif fault == "hardlink":
        os.link(target, tmp_path / "extra-link")
    elif fault == "mode":
        target.chmod(0o666)
    elif fault == "generic":
        target.write_bytes(
            Path("deploy/systemd/pulseplate-postgres-backup.service.example").read_bytes()
        )
    else:
        target.write_text("[Service]\nExecStart=/usr/bin/false\n")
    with pytest.raises((security.SecurityError, OSError)):
        security.check_backup_units(o["project"])
    assert not o["calls"] if suffix == "service" else len(o["calls"]) == 4


@pytest.mark.parametrize("suffix", ["service", "timer"])
@pytest.mark.parametrize(
    "name,value",
    [
        ("LoadState", "not-found"),
        ("LoadState", "loaded\nloaded"),
        ("FragmentPath", "/usr/lib/systemd/system/other.service"),
        ("DropInPaths", "/run/systemd/system/override.conf"),
        ("NeedDaemonReload", "yes"),
    ],
)
def test_backup_loaded_fragment_or_reload_drift_holds(
    backup_observations: dict[str, Any], suffix: str, name: str, value: str
) -> None:
    o = backup_observations
    o["show_override"][(suffix, name)] = value
    with pytest.raises(security.SecurityError, match=name):
        security.check_backup_units(o["project"])


@pytest.mark.parametrize(
    "name,value",
    [
        ("User", "pulseplate-ops"),
        ("Type", "simple"),
        ("WorkingDirectory", "/srv/pulseplate-production"),
        ("EnvironmentFiles", [["/srv/pulseplate-staging/.env", True]]),
        ("EnvironmentFiles", [["/srv/pulseplate-staging/.env", 0]]),
        ("EnvironmentFiles", [["/srv/pulseplate-staging/.env", False], ["/tmp/other", False]]),
        ("Environment", ["BACKUP_DIR=/tmp/backups"]),
        ("Environment", [False]),
        ("BindsTo", []),
        ("BindsTo", "malformed"),
        ("BindsTo", [False]),
        ("After", ["docker.service"]),
        ("RequiresMountsFor", ["/mnt/pulseplate-staging-data"]),
        ("Unit", "other.service"),
        ("Persistent", False),
        ("Persistent", 1),
        ("UnitFileState", "disabled"),
        ("ActiveState", "inactive"),
        ("TimersCalendar", []),
        ("TimersCalendar", [["OnCalendar", "*-*-* 02:15:00", True]]),
        ("TimersCalendar", [["OnCalendar", "*-*-* 02:15:00", -1]]),
        ("TimersCalendar", [["OnCalendar", "*-*-* 12:00:00", 42]]),
        ("TimersCalendar", [["OnCalendar", "*-*-* 02:15:00", 42], ["OnCalendar", "hourly", 42]]),
    ],
)
def test_backup_loaded_contract_drift_holds(
    backup_observations: dict[str, Any], name: str, value: object
) -> None:
    o = backup_observations
    signature, _ = o["properties"][name]
    o["properties"][name] = (signature, value)
    with pytest.raises(security.SecurityError):
        security.check_backup_units(o["project"])


@pytest.mark.parametrize("name", ["ExecStart", "ExecStartPre"])
@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "truncated",
        "binary",
        "argv",
        "ignore",
        "status-type",
        "negative-runtime",
        "signature",
    ],
)
def test_backup_exact_loaded_commands_reject_overrides_and_malformed_runtime(
    backup_observations: dict[str, Any], name: str, fault: str
) -> None:
    o = backup_observations
    signature, commands = o["properties"][name]
    if fault == "missing":
        commands = []
    elif fault == "extra":
        commands *= 2
    elif fault == "truncated":
        commands[0].pop()
    elif fault == "binary":
        commands[0][0] = "/bin/sh"
    elif fault == "argv":
        commands[0][1].append("--other")
    elif fault == "ignore":
        commands[0][2] = True
    elif fault == "status-type":
        commands[0][3] = False
    elif fault == "negative-runtime":
        commands[0][3] = -1
    elif fault == "signature":
        signature = "as"
    o["properties"][name] = (signature, commands)
    with pytest.raises(security.SecurityError):
        security.check_backup_units(o["project"])


@pytest.mark.parametrize(
    "value",
    [
        '{"type":"s","data":"root","data":"root"}',
        '{"type":"s","data":"root","extra":1}',
        '{"type":"s"}',
        "null",
    ],
)
def test_systemd_native_property_envelope_rejects_ambiguity(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setattr(security, "_native", lambda args: value)
    with pytest.raises(security.SecurityError):
        security._systemd_property("service", "Service", "User", "s")


def test_backup_units_require_selected_canonical_project(tmp_path: Path) -> None:
    with pytest.raises(security.SecurityError, match="canonical"):
        security.check_backup_units(tmp_path)


def test_orphan_legacy_postgres_is_never_a_fresh_database(
    tmp_path: Path, empty_backing: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def native(args: list[str]) -> str:
        calls.append(args)
        assert args == ["docker", "volume", "ls", "--format", "{{.Name}}"]
        return "pulseplate-staging_postgres_data\n"

    monkeypatch.setattr(security, "_native", native)
    with pytest.raises(security.SecurityError, match="Legacy PostgreSQL"):
        security.check_existing_volumes(compose(tmp_path))
    assert len(calls) == 1
    assert list((empty_backing / "postgres").iterdir()) == []
