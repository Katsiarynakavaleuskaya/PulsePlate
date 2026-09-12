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
        },
        "networks": {"database": {"internal": True}},
        "volumes": {
            name: {
                "name": "staging_" + name,
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
            return "staging_postgres_data\n"
        return json.dumps([{"Driver": "local", "Options": existing_options}])

    monkeypatch.setattr(security, "_native", native)
    with pytest.raises(security.SecurityError, match="preserve"):
        security.check_existing_volumes(compose(tmp_path))
    assert all("rm" not in command and "create" not in command for command in calls)


def test_existing_matching_and_absent_volumes_are_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = compose(tmp_path)

    def native(args: list[str]) -> str:
        if args[2] == "ls":
            return "staging_postgres_data\n"
        return json.dumps(
            [{"Driver": "local", "Options": value["volumes"]["postgres_data"]["driver_opts"]}]
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
            return "bad/name" if fault == "malformed-census" else "staging_postgres_data"
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
