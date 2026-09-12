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
DATABASE = "pulseplate_probe"


class ProbeError(ValueError):
    """A bounded native experiment failed."""


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
        stderr = result.stderr.decode(errors="replace")
        stderr = re.sub(
            r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----[\s\S]*?(?:-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----|$)",
            "[redacted-private-key]",
            stderr,
        )
        detail = redactor._trim_for_error(stderr)
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
    if (
        not isinstance(command, list)
        or not command
        or command[0] != "postgres"
        or any(not isinstance(item, str) for item in command)
    ):
        raise ProbeError("Rendered PostgreSQL command is malformed")
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
        time.sleep(1)
    raise ProbeError("Native PostgreSQL startup did not reach the bounded readiness condition")


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


def experiment(root: Path, contract: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    owner = uuid.uuid4().hex
    prefix = "pulseplate-staging-native-" + owner[:16]
    container, volume, network = prefix + "-db", prefix + "-data", prefix + "-network"
    tools = [prefix + "-permissions", prefix + "-expiry", prefix + "-ownership-restore"]
    resources = {"container": [container, *tools], "volume": [volume], "network": [network]}
    primary: BaseException | None = None
    key_ownership_attempted = False
    result: dict[str, Any] = {}
    directory = tempfile.mkdtemp(prefix="pulseplate-staging-native-")
    try:
        secrets = create_pki(Path(directory))
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
        native(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                container,
                "--label",
                f"{LABEL}={owner}",
                "--platform",
                contract["platform"],
                "--network",
                network,
                "--network-alias",
                "postgres",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "256",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--env",
                f"POSTGRES_DB={DATABASE}",
                "--env",
                f"POSTGRES_USER={USER}",
                "--env",
                "POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password",
                "--env",
                f"PGDATA={contract['pgdata']}",
                "--mount",
                f"type=volume,source={volume},target={contract['data_target']}",
                "--mount",
                f"type=bind,source={secrets},target=/run/secrets,readonly",
                "--mount",
                f"type=bind,source={contract['hba']},target=/etc/postgresql/pg_hba.conf,readonly",
                contract["image"],
                *contract["command"],
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
