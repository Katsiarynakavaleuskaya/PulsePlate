import base64
import gzip
import io
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
PRODUCTION_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.production.yaml"
PRODUCTION_COMPOSE_TEXT = PRODUCTION_COMPOSE_PATH.read_text(encoding="utf-8")
SELF_HOSTED_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.production.selfhosted.yaml"
STAGING_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.staging.yaml"
PROMETHEUS_CONFIG_PATH = REPO_ROOT / "deploy" / "prometheus" / "prometheus.yml"
PROMETHEUS_MANIFEST_PATH = REPO_ROOT / "deploy" / "prometheus" / "image-manifest.json"
POSTGRES_MANIFEST_PATH = REPO_ROOT / "deploy" / "postgres-pgvector" / "image-manifest.json"
PROMETHEUS_SOURCE_REVISION = "53144df54e01b689bf6c45e811c6230631b132e7"
PROMETHEUS_INDEX_DIGEST = "sha256:62464aea89547566d3e26b33566a40d8a9d2ddef947fde9d37454040c9c636b1"
PROMETHEUS_PLATFORM_MANIFEST_DIGEST = (
    "sha256:76f21be0a8e8c825cccb0e2021699dcbfb02037cc594c1f48d44993f8a415f2d"
)
PROMETHEUS_RUNTIME_REF = f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"
POSTGRES_RUNTIME_REF = (
    "ghcr.io/katsiarynakavaleuskaya/pulseplate:postgres-15.19-pgvector0.8.6-alpine3.23@"
    "sha256:06c914735c70f82424a2a9b1e57790590a21d0fbfe250504ff79a1cca2559380"
)
POSTGRES_PLATFORM_MANIFEST_DIGEST = (
    "sha256:06c914735c70f82424a2a9b1e57790590a21d0fbfe250504ff79a1cca2559380"
)
FAKE_PROMETHEUS_COMPOSE_JSON = json.dumps(
    {
        "services": {
            "prometheus": {
                "image": PROMETHEUS_RUNTIME_REF,
                "platform": "linux/amd64",
            },
            "postgres": {
                "image": POSTGRES_RUNTIME_REF,
                "platform": "linux/amd64",
                "environment": {"PGDATA": "/var/lib/postgresql/data"},
                "volumes": [
                    {
                        "type": "volume",
                        "source": "pulseplate_postgres_data",
                        "target": "/var/lib/postgresql/data",
                    }
                ],
            },
        },
        "volumes": {"postgres_data": {"name": "pulseplate_postgres_data"}},
    },
    separators=(",", ":"),
)
FAKE_PROMETHEUS_IMAGE_INSPECT_JSON = json.dumps(
    [
        {
            "Os": "linux",
            "Architecture": "amd64",
            "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
        }
    ],
    separators=(",", ":"),
)
FAKE_POSTGRES_IMAGE_INSPECT_JSON = json.dumps(
    [
        {
            "Os": "linux",
            "Architecture": "amd64",
            "RepoDigests": [
                f"ghcr.io/katsiarynakavaleuskaya/pulseplate@{POSTGRES_PLATFORM_MANIFEST_DIGEST}"
            ],
            "Config": {
                "User": "70",
                "Entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
                "Env": [
                    "PGDATA=/var/lib/postgresql/15/data",
                    "PG_MAJOR=15",
                    "PG_MINOR=19",
                ],
                "Labels": {
                    "com.pulseplate.pgvector.version": "0.8.6",
                    "com.pulseplate.pgvector.source-commit": (
                        "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c"
                    ),
                    "com.pulseplate.postgres.base-manifest": (
                        "sha256:d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d"
                    ),
                },
            },
        }
    ],
    separators=(",", ":"),
)
FAKE_POSTGRES_CONTAINER_INSPECT_JSON = json.dumps(
    [
        {
            "Id": "a" * 64,
            "Image": "sha256:aad6289ca337b3ce76896f2e7e61480490152886c7828120371fb28e6b779e1d",
            "Config": {
                "Image": "postgres:15-alpine",
                "Env": ["PGDATA=/var/lib/postgresql/data", "PG_MAJOR=15"],
            },
            "State": {"Running": True, "Health": {"Status": "healthy"}},
            "Mounts": [
                {
                    "Type": "volume",
                    "Name": "pulseplate_postgres_data",
                    "Destination": "/var/lib/postgresql/data",
                    "RW": True,
                }
            ],
        }
    ],
    separators=(",", ":"),
)
CANONICAL_MANAGED_COMPOSE = "deploy/docker-compose.production.yaml"
CANONICAL_SELF_HOSTED_COMPOSE = "deploy/docker-compose.production.selfhosted.yaml"
METRICS_SECRET_SENTINEL = "obs1b-test-metrics-token-12345678"  # pragma: allowlist secret
MOUNTPOINT_LAYER_GZIP = base64.b64decode(
    "H4sIAAAAAAAA/+zSQQrCMBCF4TmKN/BNMknPM6KIUFCT6PmlYhaCG2unIMy3mV1p+N9dy5aMAcAA"  # pragma: allowlist secret
    "PC8jv90X4hRiEIksmcCACG2S9Y9NbrVpIeDX7/SH9Psnpv7jaWe6gRn9Mwfvv4be/3Ku7VgO9To"  # pragma: allowlist secret
    "uP4Xv+0dw8v5r+NB/r00XHcGM/kPI3t855yw9AgAA//+DTG3aAAwAAA=="  # pragma: allowlist secret
)


def _write_production_host_contract(
    project_dir: Path,
    *,
    compose_text: str = "services: {}\n",
    self_hosted: bool = False,
) -> Path:
    deploy_dir = project_dir / "deploy"
    prometheus_dir = deploy_dir / "prometheus"
    postgres_manifest_dir = deploy_dir / "postgres-pgvector"
    secret_dir = deploy_dir / "secrets"
    backup_dir = project_dir / "backups"
    backup_helper_dir = project_dir / "scripts" / "ops"
    prometheus_dir.mkdir(parents=True, exist_ok=True)
    postgres_manifest_dir.mkdir(parents=True, exist_ok=True)
    secret_dir.mkdir(parents=True, exist_ok=True)
    if self_hosted:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_helper_dir.mkdir(parents=True, exist_ok=True)
    secret_dir.chmod(0o700)
    secret_file = secret_dir / "pulseplate_metrics_scrape_key"
    secret_file.write_text(METRICS_SECRET_SENTINEL, encoding="ascii")
    secret_file.chmod(0o444)
    (prometheus_dir / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (prometheus_dir / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (postgres_manifest_dir / "image-manifest.json").write_text(
        POSTGRES_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    compose_name = (
        "docker-compose.production.selfhosted.yaml"
        if self_hosted
        else "docker-compose.production.yaml"
    )
    compose_path = deploy_dir / compose_name
    compose_path.write_text(compose_text, encoding="utf-8")
    if self_hosted:
        backup_helper = backup_helper_dir / "postgres_backup.sh"
        backup_helper.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'receipt="${BACKUP_DIR}/pulseplate_test.dump"\n'
            'if [ -n "${STUB_DEPLOY_LOG_FILE:-}" ]; then printf "backup\\n" >> "$STUB_DEPLOY_LOG_FILE"; fi\n'
            "printf 'synthetic-custom-dump' > \"$receipt\"\n"
            'chmod 0600 "$receipt"\n'
            "printf 'Backup created: %s\\n' \"$receipt\"\n",
            encoding="utf-8",
        )
        backup_helper.chmod(0o755)
    return compose_path


def _write_shell_bundle_contract(
    shell_bundle_dir: Path,
    *,
    compose_text: str = PRODUCTION_COMPOSE_TEXT,
    compose_name: str = "docker-compose.production.yaml",
    include_frontend: bool = True,
    include_redeploy: bool = True,
    include_backup_helper: bool = True,
) -> None:
    deploy_dir = shell_bundle_dir / "deploy"
    prometheus_dir = deploy_dir / "prometheus"
    postgres_manifest_dir = deploy_dir / "postgres-pgvector"
    scripts_dir = shell_bundle_dir / "scripts"
    ops_dir = scripts_dir / "ops"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    prometheus_dir.mkdir(parents=True, exist_ok=True)
    postgres_manifest_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)
    if include_frontend:
        (shell_bundle_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (deploy_dir / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n', encoding="utf-8"
    )
    (deploy_dir / compose_name).write_text(compose_text, encoding="utf-8")
    sibling_compose = (
        SELF_HOSTED_COMPOSE_PATH
        if compose_name == "docker-compose.production.yaml"
        else PRODUCTION_COMPOSE_PATH
    )
    (deploy_dir / sibling_compose.name).write_text(
        sibling_compose.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (prometheus_dir / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (prometheus_dir / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (postgres_manifest_dir / "image-manifest.json").write_text(
        POSTGRES_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (scripts_dir / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    if include_redeploy:
        (scripts_dir / "redeploy_caddy.sh").write_text(
            "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
        )
    if include_backup_helper:
        backup_helper = ops_dir / "postgres_backup.sh"
        backup_helper.write_text(
            (REPO_ROOT / "scripts" / "ops" / "postgres_backup.sh").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        backup_helper.chmod(0o755)


def _canonical_test_archive_path(suffix: int) -> Path:
    return Path("/tmp") / f"pulseplate-shell-bundle-{os.getpid()}-{suffix}.tgz"


def _write_shell_bundle_archive(
    archive_path: Path,
    source_dir: Path,
    *,
    variant: str = "valid",
) -> None:
    required_paths = [
        "frontend",
        "deploy/Caddyfile.production",
        "deploy/docker-compose.production.yaml",
        "deploy/docker-compose.production.selfhosted.yaml",
        "deploy/postgres-pgvector/image-manifest.json",
        "deploy/prometheus/prometheus.yml",
        "deploy/prometheus/image-manifest.json",
        "scripts/diagnose_web.sh",
        "scripts/ops/postgres_backup.sh",
        "scripts/redeploy_caddy.sh",
    ]
    if archive_path.exists():
        archive_path.unlink()
    if variant == "oversized_archive":
        with archive_path.open("wb") as handle:
            handle.truncate(512 * 1024 * 1024 + 1)
        return

    with tarfile.open(archive_path, "w:gz") as archive:
        for relative_path in required_paths:
            if variant == "missing_manifest" and relative_path.endswith("image-manifest.json"):
                continue
            if variant.startswith("backup_helper_") and relative_path == (
                "scripts/ops/postgres_backup.sh"
            ):
                continue
            archive.add(source_dir / relative_path, arcname=relative_path, recursive=True)

        if variant == "duplicate":
            archive.add(
                source_dir / "deploy/Caddyfile.production",
                arcname="deploy/Caddyfile.production",
            )
        elif variant in {"traversal", "absolute", "non_normalized", "unexpected"}:
            names = {
                "traversal": "../escape.txt",
                "absolute": "/escape.txt",
                "non_normalized": "frontend/../escape.txt",
                "unexpected": "unexpected.txt",
            }
            payload = b"invalid\n"
            member = tarfile.TarInfo(names[variant])
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        elif variant in {"symlink", "hardlink", "fifo"}:
            member = tarfile.TarInfo(f"frontend/{variant}")
            if variant == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "target"
            elif variant == "hardlink":
                member.type = tarfile.LNKTYPE
                member.linkname = "frontend/bundle-marker.txt"
            else:
                member.type = tarfile.FIFOTYPE
            archive.addfile(member)
        elif variant in {"backup_helper_symlink", "backup_helper_hardlink"}:
            member = tarfile.TarInfo("scripts/ops/postgres_backup.sh")
            if variant == "backup_helper_symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "../../deploy/Caddyfile.production"
            else:
                member.type = tarfile.LNKTYPE
                member.linkname = "scripts/redeploy_caddy.sh"
            archive.addfile(member)
        elif variant == "backup_helper_wrong_mode":
            payload = b"#!/usr/bin/env bash\nexit 0\n"
            member = tarfile.TarInfo("scripts/ops/postgres_backup.sh")
            member.mode = 0o775
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))


def test_production_compose_source_of_truth_matches_split_contract() -> None:
    compose = yaml.safe_load(PRODUCTION_COMPOSE_TEXT)
    assert isinstance(compose, dict), "production compose must deserialize to a mapping"

    services = compose.get("services")
    assert isinstance(services, dict), "production compose must define a services mapping"

    assert "postgres" not in services
    app_service = services.get("app")
    assert isinstance(app_service, dict), "production compose must define an app service"
    assert app_service["image"] == "${IMAGE_REF:?IMAGE_REF is required}"
    assert "build" not in app_service
    app_env_file = app_service.get("env_file")
    assert app_env_file in (".env", [".env"]), "app service must reference deploy/.env"

    caddy_service = services.get("caddy")
    assert isinstance(caddy_service, dict), "production compose must define a caddy service"
    assert "image" not in caddy_service

    caddy_build = caddy_service.get("build")
    assert isinstance(caddy_build, dict), "caddy service must use a build-based shell contract"
    assert caddy_build["context"] == "../frontend"
    assert caddy_build["dockerfile"] == "Dockerfile.caddy-spa"

    caddy_build_args = caddy_build.get("args")
    assert isinstance(caddy_build_args, dict), "caddy build must define build args"
    assert caddy_build_args["VITE_API_BASE"] == "${VITE_API_BASE:-/api/v1}"


def test_prometheus_image_manifest_is_one_closed_exact_record() -> None:
    manifest_bytes = PROMETHEUS_MANIFEST_PATH.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == (
        "4ed16abd263dabd23f4df04aa60401324efd34dd5d93a9fdbb58c60e2081dc75"  # pragma: allowlist secret
    )
    manifest = json.loads(manifest_bytes)
    assert manifest == {
        "schema": "pulseplate.prometheus_image_manifest.v2",
        "repository": "prom/prometheus",
        "source_revision": PROMETHEUS_SOURCE_REVISION,
        "index_digest": PROMETHEUS_INDEX_DIGEST,
        "platform": "linux/amd64",
        "platform_manifest_digest": PROMETHEUS_PLATFORM_MANIFEST_DIGEST,
        "runtime_ref": PROMETHEUS_RUNTIME_REF,
    }


def test_postgres_pgvector_manifest_binds_reproducible_image_and_scan_contract() -> None:
    """Bind the image recipe and every deployment consumer to the same immutable subject."""
    manifest_bytes = POSTGRES_MANIFEST_PATH.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == (
        "f5695851db7e29f4f3d70f202655ca474eddaabc6aecfb9725a4783ca09e55ce"  # pragma: allowlist secret
    )
    manifest = json.loads(manifest_bytes)
    assert manifest["schema"] == "pulseplate.postgres_pgvector_image_manifest.v1"
    assert manifest["repository"] == "ghcr.io/katsiarynakavaleuskaya/pulseplate"
    assert manifest["tag"] == "postgres-15.19-pgvector0.8.6-alpine3.23"
    assert manifest["platform"] == "linux/amd64"
    assert manifest["platform_manifest_digest"] == POSTGRES_PLATFORM_MANIFEST_DIGEST
    assert manifest["config_digest"] == (
        "sha256:c822c68e22d0358e66cee17e06f7b3ece5d1538cb8b607c1376b59620866ceff"
    )
    assert manifest["runtime_ref"] == POSTGRES_RUNTIME_REF
    assert manifest["source_date_epoch"] == "1785349734"
    assert manifest["postgres_version"] == "15.19"
    assert manifest["pgvector_version"] == "0.8.6"
    assert manifest["runtime_user"] == "70"
    assert manifest["runtime_entrypoint"] == "/usr/local/bin/docker-entrypoint.sh"
    assert manifest["runtime_default_pgdata"] == "/var/lib/postgresql/15/data"
    assert manifest["compose_pgdata"] == "/var/lib/postgresql/data"
    assert manifest["compose_volume_target"] == "/var/lib/postgresql/data"
    assert manifest["runtime_base_platform_manifest_digest"] == (
        "sha256:d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d"
    )
    assert manifest["builder_base_platform_manifest_digest"] == (
        "sha256:276224f2143616286f74af844e9508db1cd50d6393163cf9ec60940b2b90f134"
    )
    assert manifest["legacy_platform_manifest_digest"] == (
        "sha256:a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181"
    )
    assert manifest["builder_packages"] == "build-base=0.5-r3,postgresql15-dev=15.19-r0"
    assert manifest["builder_apk_closure_count"] == "94"
    assert manifest["runtime_artifact_count"] == "64"
    assert manifest["runtime_artifact_inventory_sha256"] == (
        "sha256:a51a19ba4c626d476611205144c79c89ccdfc136acdddb9e9eb2ef5921e8ea57"
    )
    assert manifest["mountpoint_layer_schema"] == "pulseplate.pgvector_mountpoint_layer.v1"
    assert manifest["mountpoint_layer_digest"] == (
        "sha256:f5a1938bd1dfbe02232ddc8fad542445d8369541f3ebcacd5892c4e52abab124"
    )
    assert manifest["mountpoint_layer_size"] == "154"
    assert manifest["mountpoint_layer_diff_id"] == (
        "sha256:830c8272961c65f32876a884f52d80ad05cc4534a37bd0ecd4dafcf155f656fc"
    )
    assert manifest["mountpoint_layer_entry_count"] == "4"
    assert manifest["mountpoint_uid"] == "70"
    assert manifest["mountpoint_gid"] == "70"
    assert manifest["mountpoint_mode"] == "0700"
    assert manifest["mountpoint_path"] == "/var/lib/postgresql/data"
    assert manifest["mountpoint_leaf_empty"] == "true"
    assert manifest["mountpoint_base_parent_metadata_equal"] == "true"
    assert manifest["trivy_version"] == "0.74.0"
    assert manifest["trivy_scan_contract"] == (
        "vuln,secret;os,library;HIGH,CRITICAL;exit=1;suppressions=none"
    )
    assert manifest["buildkit_version"] == "0.32.2"
    assert manifest["buildx_version"] == "0.37.0"
    containerfile = REPO_ROOT / "deploy" / "postgres-pgvector" / "Containerfile"
    assert (
        "sha256:" + hashlib.sha256(containerfile.read_bytes()).hexdigest()
        == manifest["containerfile_sha256"]
    )
    assert POSTGRES_RUNTIME_REF == (
        f"{manifest['repository']}:{manifest['tag']}@{manifest['platform_manifest_digest']}"
    )
    for relative_path in ("scripts/deploy.sh", "scripts/deploy_production.sh"):
        script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert f'if [ "$image_id" != "{manifest["config_digest"]}" ]; then' in script


@pytest.mark.parametrize("compose_path", (STAGING_COMPOSE_PATH, SELF_HOSTED_COMPOSE_PATH))
def test_local_postgres_contours_use_one_immutable_pgvector_volume_contract(
    compose_path: Path,
) -> None:
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    postgres = compose["services"]["postgres"]
    assert postgres["image"] == POSTGRES_RUNTIME_REF
    assert postgres["platform"] == "linux/amd64"
    assert "PGDATA=/var/lib/postgresql/data" in postgres["environment"]
    assert postgres["volumes"][0] == "postgres_data:/var/lib/postgresql/data"
    assert "ports" not in postgres
    assert postgres["networks"] == (
        ["database"] if compose_path == STAGING_COMPOSE_PATH else ["web"]
    )
    if compose_path == STAGING_COMPOSE_PATH:
        assert (
            postgres["volumes"][1]
            == "./postgres-pgvector/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro"
        )
        assert compose["networks"]["database"]["internal"] is True
        assert "POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password" in postgres["environment"]


def test_managed_production_compose_remains_postgres_service_free() -> None:
    compose = yaml.safe_load(PRODUCTION_COMPOSE_TEXT)
    assert "postgres" not in compose["services"]
    assert POSTGRES_RUNTIME_REF not in PRODUCTION_COMPOSE_TEXT


def test_postgres_builder_uses_only_authenticated_offline_apk_inputs() -> None:
    """The production recipe must not resolve transitive inputs from a live index."""
    recipe = (POSTGRES_MANIFEST_PATH.parent / "Containerfile").read_text(encoding="utf-8")
    builder = recipe.split("\nFROM ", 2)[1]
    assert "RUN --network=none " in builder
    assert "apk update" not in builder
    assert "apk verify /tmp/builder-apks/x86_64/APKINDEX.tar.gz" in builder
    assert "--no-network --no-cache --repositories-file /dev/null" in builder
    assert "--repository /tmp/builder-apks" in builder
    assert "--allow-untrusted" not in recipe
    manifest = json.loads(POSTGRES_MANIFEST_PATH.read_bytes())
    record = POSTGRES_MANIFEST_PATH.parent / "builder-apk-inputs.tsv"
    index = POSTGRES_MANIFEST_PATH.parent / "builder-apk-index.tar.gz"
    assert "sha256:" + hashlib.sha256(record.read_bytes()).hexdigest() == (
        manifest["builder_apk_inputs_sha256"]
    )
    assert "sha256:" + hashlib.sha256(index.read_bytes()).hexdigest() == (
        manifest["builder_apk_index_sha256"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "valid",
        "record-digest",
        "index-digest",
        "duplicate",
        "short-row",
        "traversal",
        "foreign-url",
        "wrong-version",
        "wrong-arch",
        "bad-digest",
        "zero-size",
        "symlink-record",
        "hardlink-record",
        "symlink-index",
        "missing-index",
        "download-failure",
        "download-truncated",
        "download-altered",
        "extra-file",
        "wrong-count",
        "no-newline",
    ],
)
def test_postgres_apk_context_executes_exact_acquisition_program(
    tmp_path: Path, fault: str
) -> None:
    """Exercise acquisition checks; native signed-index trust is separate image evidence."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    step = next(
        item
        for item in workflow["jobs"]["postgres-pgvector-publish"]["steps"]
        if item.get("name") == "Prepare exact verified pgvector source context"
    )
    program = step["run"].split("python3 - \"$context_dir\" <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    owner = tmp_path / "deploy" / "postgres-pgvector"
    owner.mkdir(parents=True)
    context = tmp_path / "context"
    context.mkdir()
    payload = b"synthetic package bytes\n"
    row = [
        hashlib.sha256(payload).hexdigest(),
        str(len(payload)),
        "build-base-0.5-r3.apk",
        "build-base",
        "0.5-r3",
        "x86_64",
        "https://dhi.io/apk/alpine/v3.23/main/x86_64/build-base-0.5-r3.apk",
    ]
    if fault == "short-row":
        row.pop()
    elif fault == "traversal":
        row[2] = "../outside.apk"
    elif fault == "foreign-url":
        row[6] = "https://example.invalid/build-base-0.5-r3.apk"
    elif fault == "wrong-version":
        row[4] = "0.6-r0"
    elif fault == "wrong-arch":
        row[5] = "aarch64"
    elif fault == "bad-digest":
        row[0] = "not-a-digest"
    elif fault == "zero-size":
        row[1] = "0"
    record = ("\t".join(row) + "\n").encode()
    count = 1
    if fault == "duplicate":
        record += record
        count = 2
    elif fault == "no-newline":
        record = record.rstrip(b"\n")
    record_path = owner / "builder-apk-inputs.tsv"
    record_path.write_bytes(record)
    index_path = owner / "builder-apk-index.tar.gz"
    index = b"synthetic index, not signature evidence\n"
    index_path.write_bytes(index)
    manifest = {
        "builder_apk_inputs_sha256": "sha256:" + hashlib.sha256(record).hexdigest(),
        "builder_apk_index_sha256": "sha256:" + hashlib.sha256(index).hexdigest(),
        "builder_apk_input_count": str(count + (fault == "wrong-count")),
    }
    (owner / "image-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if fault == "record-digest":
        record_path.write_bytes(record + b"\n")
    elif fault == "index-digest":
        index_path.write_bytes(index + b"altered")
    elif fault in {"symlink-record", "hardlink-record"}:
        external = tmp_path / "external-record"
        record_path.rename(external)
        if fault == "symlink-record":
            record_path.symlink_to(external)
        else:
            os.link(external, record_path)
    elif fault == "symlink-index":
        external = tmp_path / "external-index"
        index_path.rename(external)
        index_path.symlink_to(external)
    elif fault == "missing-index":
        index_path.unlink()
    elif fault == "extra-file":
        # Planted by the curl fixture after acquisition creates the repository.
        pass
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "curl",
        f"#!{sys.executable}\nimport os, sys\n"
        "from pathlib import Path\n"
        "fault = os.environ['APK_TEST_FAULT']\n"
        "if fault == 'download-failure': sys.exit(22)\n"
        f"payload = {payload!r}\n"
        "if fault == 'download-truncated': payload = payload[:-1]\n"
        "if fault == 'download-altered': payload = b'X' + payload[1:]\n"
        "if fault == 'extra-file':\n"
        "    Path('context/builder-apks/x86_64/unowned.apk').write_bytes(b'unowned')\n"
        "sys.stdout.buffer.write(payload)\n",
    )
    result = subprocess.run(
        [sys.executable, "-c", program, str(context)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "APK_TEST_FAULT": fault},
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if fault == "valid":
        assert result.returncode == 0, result.stderr
        repository = context / "builder-apks" / "x86_64"
        assert {path.name for path in repository.iterdir()} == {
            "APKINDEX.tar.gz",
            "build-base-0.5-r3.apk",
        }
        assert (repository / "build-base-0.5-r3.apk").read_bytes() == payload
        assert (repository / "APKINDEX.tar.gz").read_bytes() == index
    elif fault == "extra-file":
        assert result.returncode != 0, result.stdout
        assert "APK repository file set drifted" in result.stderr
        assert "Verified 1 exact APK archives" not in result.stdout
    else:
        assert result.returncode != 0, result.stdout
        assert "Verified 1 exact APK archives" not in result.stdout


def test_postgres_containerfile_is_exact_multistage_source_build() -> None:
    """Keep offline source compilation separate from the minimal non-root runtime image."""
    containerfile = (REPO_ROOT / "deploy" / "postgres-pgvector" / "Containerfile").read_text(
        encoding="utf-8"
    )
    assert containerfile.startswith("ARG SOURCE_DATE_EPOCH=1785349734\n")
    assert containerfile.count("FROM dhi.io/postgres@sha256:") == 2
    assert (
        "FROM dhi.io/postgres@sha256:"
        "276224f2143616286f74af844e9508db1cd50d6393163cf9ec60940b2b90f134 AS builder"  # pragma: allowlist secret
        in containerfile
    )
    assert (
        "FROM dhi.io/postgres@sha256:"
        "d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d"  # pragma: allowlist secret
        in containerfile
    )
    assert "--repository /tmp/builder-apks add" in containerfile
    assert "PG_CONFIG=/usr/libexec/postgresql15/pg_config" in containerfile
    assert "make -j1" in containerfile
    assert 'OPTFLAGS=""' in containerfile
    assert (
        "install -D -o 0 -g 0 -m 0644 LICENSE "
        "/out/usr/share/licenses/pgvector/LICENSE" in containerfile
    )
    assert 'touch -d "@${SOURCE_DATE_EPOCH}" /out/usr/share/licenses/pgvector/LICENSE' in (
        containerfile
    )
    assert (
        'test "$(stat -c %Y /out/usr/share/licenses/pgvector/LICENSE)" = '
        '"$SOURCE_DATE_EPOCH"' in containerfile
    )
    assert "/out/usr/share/licenses/pgvector -type f" in containerfile
    assert (
        "COPY --from=builder --chown=0:0 /out/usr/share/licenses/pgvector/LICENSE "
        "/usr/share/licenses/pgvector/LICENSE" in containerfile
    )
    assert "install -d -o 70 -g 70 -m 0700 /out/var/lib/postgresql/data" in containerfile
    assert (
        "COPY --from=builder --chown=70:70 --chmod=0700 "
        "/out/var/lib/postgresql/data/ /var/lib/postgresql/data/" in containerfile
    )
    final_stage = containerfile.split(
        "FROM dhi.io/postgres@sha256:"
        "d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d",  # pragma: allowlist secret
        maxsplit=1,
    )[1]
    for forbidden in ("\nRUN ", "\nUSER ", "\nENV ", "\nVOLUME ", "\nENTRYPOINT ", "\nCMD "):
        assert forbidden not in final_stage
    assert "COPY --from=builder /out/var" not in containerfile
    assert "COPY --from=builder --chown=70:70 --chmod=0700 /out/var/ /var/" not in containerfile
    assert "curl " not in containerfile
    assert "git clone" not in containerfile
    assert "postgres:15-alpine" not in containerfile


def test_cd_postgres_pgvector_contract_is_pr_secret_free_and_main_publish_only() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "cd.yml").read_text(encoding="utf-8")
    contract = workflow.split("\n  postgres-pgvector-contract:\n", maxsplit=1)[1].split(
        "\n  main-push-admission:\n", maxsplit=1
    )[0]
    publish = workflow.split("\n  postgres-pgvector-publish:\n", maxsplit=1)[1].split(
        "\n  build:\n", maxsplit=1
    )[0]
    assert "${{ secrets." not in contract
    assert "docker" + " login" not in contract
    assert hashlib.sha256(POSTGRES_MANIFEST_PATH.read_bytes()).hexdigest() in contract
    workflow_triggers = workflow.split("\npermissions:\n", maxsplit=1)[0]
    assert "pull_request" + "_target:" not in workflow_triggers
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in publish
    assert "DHI_USERNAME" in publish
    assert "DHI_ACCESS_TOKEN" in publish
    assert publish.count("--no-cache") == 1
    assert "for build_number in 1 2" in publish
    assert "diff -qr" in publish
    assert "--output type=registry,rewrite-timestamp=true" in publish
    assert "--scanners vuln,secret" in publish
    assert "--severity CRITICAL,HIGH" in publish
    assert "--exit-code 1" in publish
    assert "--ignorefile" in publish
    assert "ignore-policy" not in publish
    assert "ignore-unfixed" not in publish
    assert "0.74.0" in workflow
    assert POSTGRES_PLATFORM_MANIFEST_DIGEST in workflow
    assert "sha256:f5a1938bd1dfbe02232ddc8fad542445d8369541f3ebcacd5892c4e52abab124" in workflow
    assert "sha256:830c8272961c65f32876a884f52d80ad05cc4534a37bd0ecd4dafcf155f656fc" in workflow
    assert 'stat -c "%u:%g:%a" /var/lib/postgresql/data' in publish
    assert "test -z" in publish
    assert (
        "postgres:15-alpine@sha256:"
        "a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181" in publish
    )
    assert "82cde02f1b64bf198b19829fcf8169efae35fdb89fcd236bbd5b0e4faa2b8817" not in workflow


def _copy_pgvector_material_helpers(root: Path) -> None:
    """Copy actual stdlib helper and finite CI universe for native Git shell tests."""
    for relative in (
        ".github/workflows/ci.yml",
        "scripts/ci/check_pgvector_attestations.py",
        "scripts/ci/check_docker_provenance_attestation.py",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, target)


def test_cd_postgres_pgvector_main_event_state_machine_is_closed_and_terminal() -> None:
    workflow_text = (REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    jobs = workflow["jobs"]
    classifier = jobs["postgres-pgvector-material-change"]
    classifier_run = classifier["steps"][1]["run"]
    assert "scripts/ci/check_pgvector_attestations.py changes" in classifier_run
    assert '--base "$BEFORE_SHA" --head "$AFTER_SHA"' in classifier_run
    assert 'git merge-base --is-ancestor "$BEFORE_SHA" "$AFTER_SHA"' in classifier_run

    publish = jobs["postgres-pgvector-publish"]
    publish_text = json.dumps(publish, sort_keys=True)
    assert "needs.postgres-pgvector-material-change.outputs.changed == 'true'" in publish["if"]
    assert "needs.postgres-pgvector-ci-admission.result == 'success'" in publish["if"]
    assert publish["needs"] == [
        "main-push-admission",
        "postgres-pgvector-contract",
        "postgres-pgvector-material-change",
        "postgres-pgvector-ci-admission",
    ]
    assert "DHI_USERNAME" in publish_text
    assert "DHI_ACCESS_TOKEN" in publish_text
    assert publish["permissions"]["packages"] == "write"
    assert publish["environment"] == {"name": "pgvector-publish"}
    assert publish["concurrency"] == {
        "group": "postgres-pgvector-canonical-tag-promotion",
        "cancel-in-progress": False,
    }
    assert "python -m pytest" not in publish_text
    assert "DEVPI_CI_USER" not in publish_text
    assert "DEVPI_CI_PASSWORD" not in publish_text

    ci_admission = jobs["postgres-pgvector-ci-admission"]
    assert ci_admission["needs"] == [
        "main-push-admission",
        "postgres-pgvector-material-change",
    ]
    assert ci_admission["permissions"] == {"contents": "read"}
    assert ci_admission["timeout-minutes"] == 30
    assert ci_admission["env"] == {
        "PULSEPLATE_PYTHON_INDEX_URL": "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": ("${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"),
    }
    assert "environment" not in ci_admission
    assert workflow.get("concurrency") is None
    postgres_service = ci_admission["services"]["postgres"]
    assert postgres_service["image"] == (
        "pgvector/pgvector:0.8.6-pg15-trixie@"
        "sha256:43904fc138a63f93611a2995cec2566e8ae883c8678cd65c60315fa44308f81f"
    )
    assert postgres_service["ports"] == ["5432:5432"]
    assert len(ci_admission["steps"]) == 4
    assert ci_admission["steps"][0]["name"] == "Checkout exact main compatibility source"
    proxy_step = ci_admission["steps"][1]
    assert proxy_step["name"] == "Validate credential-free compatibility package proxy"
    proxy_run = proxy_step["run"]
    assert "PULSEPLATE_PYTHON_INDEX_URL:?" in proxy_run
    assert "*://*@*" in proxy_run
    assert "must be credential-free" in proxy_run
    assert "must be single-line values" in proxy_run
    setup_step = ci_admission["steps"][2]
    assert setup_step["uses"] == "./.github/actions/python-setup"
    assert "env" not in setup_step
    assert setup_step["with"] == {
        "python-version": "3.13.14",
        "requirements-profile": "ci-test",
        "install-mode": "direct-proxy",
    }
    ci_admission_step = ci_admission["steps"][3]
    assert ci_admission_step["env"] == {
        "PGVECTOR_COMPAT_DATABASE_URL": (
            "postgresql+psycopg://pgvector_compat:pgvector_compat_test_password@"  # pragma: allowlist secret
            "127.0.0.1:5432/pgvector_compat"
        ),
        "PGVECTOR_COMPAT_REQUIRED": "1",
    }
    ci_admission_run = ci_admission_step["run"]
    for required in (
        'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
        "python -m pytest -q",
    ):
        assert required in ci_admission_run
    ci_admission_text = json.dumps(ci_admission, sort_keys=True)
    assert "${{ secrets." not in ci_admission_text
    assert "DEVPI_CI_USER" not in ci_admission_text
    assert "DEVPI_CI_PASSWORD" not in ci_admission_text
    assert "actions/workflows/ci.yml/runs" not in ci_admission_text
    assert "DHI_ACCESS_TOKEN" not in json.dumps(ci_admission, sort_keys=True)
    assert "GHCR_TOKEN" not in json.dumps(ci_admission, sort_keys=True)

    reuse = jobs["postgres-pgvector-reuse"]
    reuse_text = json.dumps(reuse, sort_keys=True)
    assert "github.event_name == 'schedule'" in reuse["if"]
    assert "startsWith(github.ref, 'refs/tags/v')" in reuse["if"]
    assert "needs.postgres-pgvector-material-change.outputs.changed == 'false'" in reuse["if"]
    assert reuse["permissions"] == {
        "attestations": "read",
        "contents": "read",
        "packages": "read",
    }
    assert "concurrency" not in reuse
    assert reuse["timeout-minutes"] == 90
    assert reuse["env"] == {
        "PGVECTOR_REUSE_ADMISSION_POLL_SECONDS": "30",
        "PGVECTOR_REUSE_ADMISSION_WAIT_SECONDS": "3600",
    }
    for forbidden in ("DHI_USERNAME", "DHI_ACCESS_TOKEN", '"packages": "write"', "id-token"):
        assert forbidden not in reuse_text
    reuse_run = reuse["steps"][1]["run"]
    for forbidden_command in ("docker buildx build", "imagetools create", "actions/attest"):
        assert forbidden_command not in reuse_run
    assert "--scanners vuln,secret" in reuse_run
    assert "--severity CRITICAL,HIGH" in reuse_run
    assert "visibility" in reuse_run and "public" in reuse_run
    assert 'docker manifest inspect "$RUNTIME_REF"' in reuse_run
    assert 'canonical_tag_ref="${RUNTIME_REF%@*}"' in reuse_run
    assert 'docker buildx imagetools inspect --raw "$canonical_tag_ref"' in reuse_run
    assert "Canonical PostgreSQL tag does not select the frozen digest" in reuse_run
    assert '"$tag_ready:$image_ready:$provenance_ready:$spdx_ready:$materials_ready"' in reuse_run
    assert reuse_run.count('gh attestation verify "oci://${RUNTIME_REF}"') == 3
    assert "Exact PostgreSQL reuse admission did not become complete before timeout" in reuse_run
    assert "--format spdx-json" not in reuse_run
    assert "postgres-pgvector-reuse-current.spdx.json" not in reuse_run
    assert "scripts/ci/check_pgvector_attestations.py verify" in reuse_run
    assert "--sbom" not in reuse_run
    owner_package_endpoint = (
        'gh api "/users/${GITHUB_REPOSITORY_OWNER}/packages/container/pulseplate"'
    )
    assert workflow_text.count(owner_package_endpoint) == 4
    assert "gh api /user/packages/container/pulseplate" not in workflow_text

    admission = jobs["postgres-pgvector-admission"]
    admission_run = admission["steps"][0]["run"]
    assert "true:success:skipped | false:skipped:success" in admission_run
    prometheus_gate = jobs["prometheus-image-security"]
    assert prometheus_gate["needs"] == [
        "postgres-pgvector-contract",
        "postgres-pgvector-admission",
        "postgres-pgvector-reuse",
    ]
    assert "needs.postgres-pgvector-contract.result == 'success'" in prometheus_gate["if"]
    assert "needs.postgres-pgvector-admission.result == 'success'" in prometheus_gate["if"]
    assert "needs.postgres-pgvector-reuse.result == 'success'" in prometheus_gate["if"]
    assert jobs["build"]["needs"] == [
        "prometheus-image-security",
        "main-push-admission",
    ]
    assert jobs["production-gates"]["needs"] == "prometheus-image-security"


@pytest.mark.parametrize(
    ("ready_after", "expected_returncode"),
    (("2", 0), ("0", 1)),
)
def test_cd_postgres_reuse_waits_without_evicting_pending_publisher(
    tmp_path: Path,
    ready_after: str,
    expected_returncode: int,
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    reuse_run = workflow["jobs"]["postgres-pgvector-reuse"]["steps"][1]["run"]
    start = reuse_run.index('if [[ ! "$PGVECTOR_REUSE_ADMISSION_WAIT_SECONDS"')
    end = reuse_run.index('\ndocker pull --platform linux/amd64 "$RUNTIME_REF"', start)
    wait_program = reuse_run[start:end]
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    program = (
        "set -euo pipefail\n"
        "ATTEMPT=0\n"
        "docker() {\n"
        '  if [ "$1 $2" = "manifest inspect" ]; then\n'
        "    ATTEMPT=$((ATTEMPT + 1))\n"
        '    [ "$STUB_READY_AFTER" -gt 0 ] && [ "$ATTEMPT" -ge "$STUB_READY_AFTER" ]\n'
        "    return\n"
        "  fi\n"
        '  if [ "$1 $2 $3" = "buildx imagetools inspect" ]; then\n'
        '    expected_digest="${RUNTIME_REF##*@}"\n'
        "    printf "
        '\'{"mediaType":"application/vnd.oci.image.index.v1+json",'
        '"manifests":[{"digest":"%s","platform":{'
        '"architecture":"amd64","os":"linux"}}]}\\n\' '
        '"$expected_digest"\n'
        "    return\n"
        "  fi\n"
        "  return 0\n"
        "}\n"
        "gh() {\n"
        '  [ "$STUB_READY_AFTER" -gt 0 ] && [ "$ATTEMPT" -ge "$STUB_READY_AFTER" ]\n'
        "}\n"
        "sleep() { SECONDS=$((SECONDS + $1)); }\n"
        + wait_program
        + '\nprintf "ATTEMPTS=%s\\n" "$ATTEMPT"\n'
    )
    completed = subprocess.run(
        [bash_bin, "-c", program],
        env={
            **os.environ,
            "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
            "PGVECTOR_REUSE_ADMISSION_POLL_SECONDS": "1",
            "PGVECTOR_REUSE_ADMISSION_WAIT_SECONDS": "2",
            "RUNNER_TEMP": str(tmp_path),
            "RUNTIME_REF": POSTGRES_RUNTIME_REF,
            "STUB_READY_AFTER": ready_after,
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == expected_returncode
    if expected_returncode == 0:
        assert completed.stdout.strip() == "ATTEMPTS=2"
    else:
        assert "did not become complete before timeout" in completed.stderr


def test_cd_postgres_reuse_terminally_rechecks_current_main_and_canonical_tag(
    tmp_path: Path,
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    reuse_steps = workflow["jobs"]["postgres-pgvector-reuse"]["steps"]
    assert reuse_steps[0]["with"] == {"fetch-depth": 0, "persist-credentials": False}
    reuse_run = reuse_steps[1]["run"]
    marker = "# Final read-only transaction boundary."
    terminal_program = reuse_run[reuse_run.index(marker) :]
    assert reuse_run.index(marker) > reuse_run.index(
        'index .Config.Labels "com.pulseplate.pgvector.version"'
    )
    ci_workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    filter_step = next(
        step for step in ci_workflow["jobs"]["changes"]["steps"] if step.get("id") == "filter"
    )
    compatibility_paths = yaml.safe_load(filter_step["with"]["filters"])["pgvector_compat"]
    from scripts.ci import check_pgvector_attestations as material_helper

    assert set(compatibility_paths).issubset(material_helper.material_rules("HEAD"))
    assert "scripts/ci/check_pgvector_attestations.py unchanged" in terminal_program

    git_bin = shutil.which("git", path=os.defpath)
    bash_bin = shutil.which("bash")
    assert git_bin is not None and bash_bin is not None
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    runner = tmp_path / "runner"

    def git(cwd: Path, *arguments: str) -> str:
        completed = subprocess.run(
            [git_bin, *arguments],
            cwd=cwd,
            env=git_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "PulsePlate Test")
    git(source, "config", "user.email", "pulseplate-test@example.invalid")
    git(source, "checkout", "-qb", "main")
    required_files = (
        ".github/workflows/cd.yml",
        ".github/workflows/ci.yml",
        "constraints.txt",
        "requirements-ci-lite.txt",
        "requirements-rag-vector.in",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.in",
        "requirements-rag-vector-cpu.txt",
        "requirements-test.in",
        "requirements-test.txt",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/install_locked_python_requirements.py",
        "scripts/deploy.sh",
        "scripts/deploy_production.sh",
        "deploy/docker-compose.staging.yaml",
        "deploy/docker-compose.production.selfhosted.yaml",
        "deploy/postgres-pgvector/Containerfile",
        "scripts/ci/check_alembic_autogenerate_completeness.py",
        "core/db.py",
        "core/db_alembic_comparison.py",
        "core/rag/vector_rag.py",
        "core/db_rls.py",
        "core/models.py",
        "app/models/nested/probe.py",
        "alembic.ini",
        "alembic/env.py",
        "alembic/versions/base.py",
        "tests/test_deploy_contract_scripts.py",
        "tests/test_alembic_autogenerate_completeness.py",
        "tests/test_pgvector_compat.py",
        "tests/test_pgvector_embedding_migration.py",
        "tests/test_vector_rag.py",
        "tests/test_db_rls.py",
        "docs/note.md",
    )
    for relative_path in required_files:
        path = source / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("base\n", encoding="utf-8")
    _copy_pgvector_material_helpers(source)
    git(source, "add", ".")
    git(source, "commit", "-qm", "base")
    base_sha = git(source, "rev-parse", "HEAD")
    git(source, "remote", "add", "origin", str(remote))
    git(source, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(remote), str(runner))
    git(runner, "checkout", "-q", "--detach", base_sha)

    program = (
        "set -euo pipefail\n"
        "docker() {\n"
        '  if [ "$1 $2" = "manifest inspect" ]; then\n'
        '    [ "$STUB_TAG_READY" = "1" ]\n'
        "    return\n"
        "  fi\n"
        "  return 0\n"
        "}\n"
        'canonical_tag_selects_expected_digest() { [ "$STUB_TAG_READY" = "1" ]; }\n'
        + terminal_program
    )

    def terminal_recheck(tag_ready: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [bash_bin, "-c", program],
            cwd=runner,
            env={
                **git_environment,
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_SHA": base_sha,
                "RUNTIME_REF": POSTGRES_RUNTIME_REF,
                "STUB_TAG_READY": tag_ready,
            },
            text=True,
            capture_output=True,
            check=False,
        )

    (source / "docs" / "note.md").write_text("unrelated\n", encoding="utf-8")
    git(source, "add", ".")
    git(source, "commit", "-qm", "unrelated main advance")
    git(source, "push", "-q", "origin", "main")
    unrelated = terminal_recheck("1")
    assert unrelated.returncode == 0, unrelated.stderr

    tag_drift = terminal_recheck("0")
    assert tag_drift.returncode != 0
    assert "tag or immutable digest drifted" in tag_drift.stderr

    (source / "requirements-test.txt").write_text("superseding\n", encoding="utf-8")
    git(source, "add", ".")
    git(source, "commit", "-qm", "superseding compatibility material")
    git(source, "push", "-q", "origin", "main")
    superseded = terminal_recheck("1")
    assert superseded.returncode != 0
    assert "material superseded run" in superseded.stderr


def test_cd_postgres_material_classifier_and_terminal_admission_execute_exact_programs(
    tmp_path: Path,
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    ci_workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    classifier_program = jobs["postgres-pgvector-material-change"]["steps"][1]["run"]
    admission_program = jobs["postgres-pgvector-admission"]["steps"][0]["run"]
    filter_step = next(
        step for step in ci_workflow["jobs"]["changes"]["steps"] if step.get("id") == "filter"
    )
    pgvector_compat_paths = yaml.safe_load(filter_step["with"]["filters"])["pgvector_compat"]
    from scripts.ci import check_pgvector_attestations as material_helper

    assert set(pgvector_compat_paths).issubset(material_helper.material_rules("HEAD"))
    assert "scripts/ci/check_pgvector_attestations.py changes" in classifier_program
    git_bin = shutil.which("git", path=os.defpath)
    bash_bin = shutil.which("bash")
    assert git_bin is not None and bash_bin is not None
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    fixture_root = tmp_path / "git-fixture"
    (fixture_root / ".github" / "workflows").mkdir(parents=True)
    (fixture_root / "deploy" / "postgres-pgvector").mkdir(parents=True)
    (fixture_root / "docs").mkdir()
    (fixture_root / ".github" / "workflows" / "cd.yml").write_text("v1\n", encoding="utf-8")
    (fixture_root / "deploy" / "postgres-pgvector" / "Containerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (fixture_root / "deploy" / "postgres-pgvector" / "image-manifest.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (fixture_root / "docs" / "note.md").write_text("base\n", encoding="utf-8")

    def git(*arguments: str) -> str:
        completed = subprocess.run(
            [git_bin, *arguments],
            cwd=fixture_root,
            env=git_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    _copy_pgvector_material_helpers(fixture_root)
    git("init", "-q")
    git("config", "user.name", "PulsePlate Test")
    git("config", "user.email", "pulseplate-test@example.invalid")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")

    def classify(before: str, after: str) -> tuple[subprocess.CompletedProcess[str], str]:
        output_path = tmp_path / f"classifier-{len(list(tmp_path.glob('classifier-*')))}.txt"
        environment = {
            **git_environment,
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/main",
            "BEFORE_SHA": before,
            "AFTER_SHA": after,
            "GITHUB_OUTPUT": str(output_path),
        }
        completed = subprocess.run(
            [bash_bin, "-c", classifier_program],
            cwd=fixture_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        classifier_output = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        return completed, classifier_output

    (fixture_root / ".github" / "workflows" / "cd.yml").write_text("v2\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "policy-only")
    policy_head = git("rev-parse", "HEAD")
    policy_result, policy_output = classify(base, policy_head)
    assert policy_result.returncode == 0, policy_result.stderr
    assert policy_output == "changed=true\n"

    containerfile = fixture_root / "deploy" / "postgres-pgvector" / "Containerfile"
    containerfile.write_text("FROM scratch\nLABEL test=1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "image-bytes")
    material_head = git("rev-parse", "HEAD")
    material_result, material_output = classify(policy_head, material_head)
    assert material_result.returncode == 0, material_result.stderr
    assert material_output == "changed=true\n"

    migration_path = fixture_root / "alembic" / "versions" / "compatibility_probe.py"
    migration_path.parent.mkdir(parents=True)
    migration_path.write_text("revision = 'compatibility-probe'\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "pgvector compatibility surface")
    compatibility_head = git("rev-parse", "HEAD")
    compatibility_result, compatibility_output = classify(material_head, compatibility_head)
    assert compatibility_result.returncode == 0, compatibility_result.stderr
    assert compatibility_output == "changed=true\n"

    (fixture_root / "docs" / "note.md").write_text("unrelated\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "unrelated docs")
    unrelated_head = git("rev-parse", "HEAD")
    unrelated_result, unrelated_output = classify(compatibility_head, unrelated_head)
    assert unrelated_result.returncode == 0, unrelated_result.stderr
    assert unrelated_output == "changed=false\n"

    zero_result, zero_output = classify("0" * 40, unrelated_head)
    assert zero_result.returncode == 0
    assert zero_output == "changed=true\n"
    malformed_result, _ = classify("not-a-sha", material_head)
    assert malformed_result.returncode != 0

    previous_head = unrelated_head
    for compatibility_path in pgvector_compat_paths:
        probe_path = compatibility_path.replace("**", "nested/compatibility_probe.py")
        target = fixture_root / probe_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if probe_path == ".github/workflows/ci.yml":
            target.write_text(
                target.read_text() + "\n# compatibility input change\n", encoding="utf-8"
            )
        else:
            target.write_text(f"compatibility input: {probe_path}\n", encoding="utf-8")
        git("add", probe_path)
        git("commit", "-qm", f"compatibility member {probe_path}")
        member_head = git("rev-parse", "HEAD")
        member_result, member_output = classify(previous_head, member_head)
        assert member_result.returncode == 0, (probe_path, member_result.stderr)
        assert member_output == "changed=true\n", probe_path
        previous_head = member_head

    statuses = ("success", "failure", "cancelled", "skipped", "")
    for changed in ("true", "false"):
        for publish in statuses:
            for reuse in statuses:
                completed = subprocess.run(
                    [bash_bin, "-c", admission_program],
                    env={
                        **os.environ,
                        "MATERIAL_CHANGED": changed,
                        "PUBLISH_RESULT": publish,
                        "REUSE_RESULT": reuse,
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                )
                admitted = (changed, publish, reuse) in {
                    ("true", "success", "skipped"),
                    ("false", "skipped", "success"),
                }
                assert (completed.returncode == 0) is admitted


@pytest.mark.parametrize(
    ("event_name", "git_ref", "material_changed", "expected_success"),
    (
        ("push", "refs/heads/main", "false", True),
        ("schedule", "refs/heads/main", "", True),
        ("push", "refs/tags/v1.2.3", "", True),
        ("push", "refs/tags/not-semver", "", False),
        ("push", "refs/heads/feature", "false", False),
        ("pull_request", "refs/pull/1/merge", "", False),
    ),
)
def test_cd_postgres_reuse_event_admission_executes_exact_prefix(
    event_name: str,
    git_ref: str,
    material_changed: str,
    expected_success: bool,
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    run = workflow["jobs"]["postgres-pgvector-reuse"]["steps"][1]["run"]
    admission_prefix = run.split('credential_dir="$(mktemp', maxsplit=1)[0]
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    completed = subprocess.run(
        [bash_bin, "-c", admission_prefix],
        env={
            **os.environ,
            "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
            "GITHUB_EVENT_NAME": event_name,
            "GITHUB_REF": git_ref,
            "MATERIAL_CHANGED": material_changed,
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert (completed.returncode == 0) is expected_success, completed.stderr


def test_cd_postgres_candidate_is_verified_before_canonical_promotion() -> None:
    """Require candidate verification before the provisional canonical tag write."""
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    names = [step.get("name") for step in steps]

    def position(name: str) -> int:
        return names.index(name)

    initial_auth = position("Authenticate DHI read and GHCR publication rails")
    scan = position("Scan exact bases, post-APK builder, and final image without suppressions")
    runtime_oracle = position("Prove PostgreSQL 15 pgvector 0.8.6 and same-volume continuity")
    package_identity = position(
        "Verify existing public GHCR package identity before candidate write"
    )
    candidate = position("Publish reproduced manifest under one unadmitted candidate tag")
    provenance = position("Attest actual PostgreSQL pgvector build provenance")
    spdx = position("Attest PostgreSQL pgvector SPDX SBOM")
    verify = position("Verify candidate pullback, material provenance, SBOM, and runtime identity")
    visibility = position("Recheck public GHCR package identity after candidate admission")
    promote = position("Promote verified candidate digest to canonical tag without rebuild")
    canonical = position("Verify canonical pullback and unchanged public package visibility")
    assert (
        initial_auth
        < scan
        < runtime_oracle
        < package_identity
        < candidate
        < provenance
        < spdx
        < verify
        < visibility
        < promote
        < canonical
    )

    initial_auth_step = steps[initial_auth]
    assert set(initial_auth_step["env"]) == {
        "BUILDX_SHA256",
        "BUILDX_VERSION",
        "BUILDKIT_DIGEST",
        "BUILDKIT_VERSION",
        "DHI_USER",
        "DHI_TOKEN",
        "GHCR_USER",
        "GHCR_TOKEN_VALUE",
    }
    assert "docker login dhi.io" in initial_auth_step["run"]
    assert "docker login ghcr.io" in initial_auth_step["run"]

    candidate_run = steps[candidate]["run"]
    assert "candidate-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" in candidate_run
    assert '--tag "$candidate_tag_ref"' in candidate_run
    assert '--tag "$canonical_tag_ref"' not in candidate_run
    promote_run = steps[promote]["run"]
    promote_env = steps[promote]["env"]
    assert promote_env["EXPECTED_RUNTIME_REF"] == (
        "${{ needs.postgres-pgvector-contract.outputs.runtime_ref }}"
    )
    assert 'test "$canonical_runtime_ref" = "$EXPECTED_RUNTIME_REF"' in promote_run
    assert "${{ needs.postgres-pgvector-contract.outputs.runtime_ref }}" not in promote_run
    material_check = '--base "$GITHUB_SHA" --head "$current_main_sha"'
    assert material_check in promote_run
    assert promote_run.index(material_check) < promote_run.index("docker buildx imagetools create")
    post_promotion_check = '--base "$GITHUB_SHA" --head "$post_promotion_main_sha"'
    assert post_promotion_check in promote_run
    assert promote_run.index("docker buildx imagetools create") < promote_run.index(
        post_promotion_check
    )
    assert promote_run.index(post_promotion_check) < promote_run.index(
        "docker buildx imagetools inspect"
    )
    assert "scripts/ci/check_pgvector_attestations.py unchanged" in promote_run
    assert "docker buildx imagetools create" in promote_run
    assert '"$CANDIDATE_RUNTIME_REF"' in promote_run
    assert "docker buildx build" not in promote_run
    job_text = json.dumps(workflow["jobs"]["postgres-pgvector-publish"], sort_keys=True)
    assert job_text.count("actions/attest@") == 2
    assert job_text.count("actions/attest-build-provenance@") == 1
    assert "python -m pytest" not in job_text
    assert "DEVPI_CI_USER" not in job_text
    assert "DEVPI_CI_PASSWORD" not in job_text
    verify_step = steps[verify]
    assert (
        verify_step["env"]["ATTESTATION_MODE"]
        == "${{ steps.pgvector-attestation-inventory.outputs.mode }}"
    )
    verify_run = verify_step["run"]
    assert '--source-sha "$ORIGINAL_SOURCE_SHA"' in verify_run
    assert '--run-invocation-uri "$ORIGINAL_RUN_INVOCATION_URI"' in verify_run
    assert "--sbom postgres-pgvector-image-sbom.spdx.json" in verify_run
    assert "scripts/ci/check_pgvector_attestations.py verify" in verify_run

    runtime_step = next(
        step
        for step in steps
        if step.get("name") == "Prove PostgreSQL 15 pgvector 0.8.6 and same-volume continuity"
    )["run"]
    assert "pytest" not in runtime_step
    assert "--publish 127.0.0.1:5432:5432" in runtime_step
    for forbidden_host in ("@localhost:5432/pgvector_compat", "0.0.0.0:5432", "::1:5432"):
        assert forbidden_host not in runtime_step
    reproduce_step = next(
        step for step in steps if step.get("name") == "Reproduce the exact platform manifest twice"
    )["run"]
    assert "{{.Id}}" in reproduce_step
    assert '"$EXPECTED_CONFIG_DIGEST"' in reproduce_step
    assert "{{json .RootFS.Layers}}" in reproduce_step
    assert "EXPECTED_MOUNTPOINT_LAYER_DIFF_ID" in reproduce_step
    assert position("Reproduce the exact platform manifest twice") < position(
        "Prove PostgreSQL 15 pgvector 0.8.6 and same-volume continuity"
    )
    assert position("Prove PostgreSQL 15 pgvector 0.8.6 and same-volume continuity") < candidate


def test_cd_postgres_canonical_promotion_executes_current_main_material_freshness(
    tmp_path: Path,
) -> None:
    """Reject superseded build inputs while allowing unrelated main changes."""
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    promote = next(
        step
        for step in steps
        if step.get("name") == "Promote verified candidate digest to canonical tag without rebuild"
    )
    freshness_program = promote["run"].split("docker buildx imagetools create", maxsplit=1)[0]
    git_bin = shutil.which("git", path=os.defpath)
    bash_bin = shutil.which("bash")
    assert git_bin is not None and bash_bin is not None
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    runner = tmp_path / "runner"

    def git(cwd: Path, *arguments: str) -> str:
        completed = subprocess.run(
            [git_bin, *arguments],
            cwd=cwd,
            env=git_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "PulsePlate Test")
    git(source, "config", "user.email", "pulseplate-test@example.invalid")
    git(source, "checkout", "-qb", "main")
    (source / ".github" / "workflows").mkdir(parents=True)
    (source / "deploy" / "postgres-pgvector").mkdir(parents=True)
    (source / "docs").mkdir()
    (source / ".github" / "workflows" / "cd.yml").write_text("name: base\n", encoding="utf-8")
    (source / "deploy" / "postgres-pgvector" / "Containerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (source / "deploy" / "postgres-pgvector" / "image-manifest.json").write_text(
        "{}\n", encoding="utf-8"
    )
    for name in ("builder-apk-inputs.tsv", "builder-apk-index.tar.gz"):
        (source / "deploy" / "postgres-pgvector" / name).write_bytes(b"frozen input")
    (source / "docs" / "note.md").write_text("base\n", encoding="utf-8")
    _copy_pgvector_material_helpers(source)
    git(source, "add", ".")
    git(source, "commit", "-qm", "base")
    base_sha = git(source, "rev-parse", "HEAD")
    git(source, "remote", "add", "origin", str(remote))
    git(source, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(remote), str(runner))
    git(runner, "checkout", "-q", "--detach", base_sha)

    (source / "docs" / "note.md").write_text("unrelated\n", encoding="utf-8")
    git(source, "add", ".")
    git(source, "commit", "-qm", "unrelated")
    git(source, "push", "-q", "origin", "main")
    environment = {**git_environment, "GITHUB_SHA": base_sha}
    same_material = subprocess.run(
        [bash_bin, "-c", freshness_program],
        cwd=runner,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert same_material.returncode == 0, same_material.stderr

    (source / ".github" / "workflows" / "cd.yml").write_text(
        "name: superseding-policy\n", encoding="utf-8"
    )
    git(source, "add", ".")
    git(source, "commit", "-qm", "supersede publication policy")
    git(source, "push", "-q", "origin", "main")
    superseded_policy = subprocess.run(
        [bash_bin, "-c", freshness_program],
        cwd=runner,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert superseded_policy.returncode != 0
    assert "material superseded run" in superseded_policy.stderr

    (source / ".github" / "workflows" / "cd.yml").write_text("name: base\n", encoding="utf-8")
    (source / "deploy" / "postgres-pgvector" / "Containerfile").write_text(
        "FROM scratch\nLABEL newer=1\n", encoding="utf-8"
    )
    git(source, "add", ".")
    git(source, "commit", "-qm", "new image material")
    git(source, "push", "-q", "origin", "main")
    superseded = subprocess.run(
        [bash_bin, "-c", freshness_program],
        cwd=runner,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert superseded.returncode != 0
    assert "material superseded run" in superseded.stderr


def test_pgvector_promotion_fails_when_main_material_advances_after_tag_mutation(
    tmp_path: Path,
) -> None:
    """A superseded provisional tag write must not emit downstream admission."""
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    publish = workflow["jobs"]["postgres-pgvector-publish"]
    assert publish["concurrency"] == {
        "group": "postgres-pgvector-canonical-tag-promotion",
        "cancel-in-progress": False,
    }
    promote_program = next(
        step["run"]
        for step in steps
        if step.get("name") == "Promote verified candidate digest to canonical tag without rebuild"
    )
    git_bin = shutil.which("git", path=os.defpath)
    bash_bin = shutil.which("bash")
    assert git_bin is not None and bash_bin is not None
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    runner = tmp_path / "runner"
    bin_dir = tmp_path / "bin"
    docker_log = tmp_path / "docker.log"
    output_path = tmp_path / "github-output.txt"

    def git(cwd: Path, *arguments: str) -> str:
        completed = subprocess.run(
            [git_bin, *arguments],
            cwd=cwd,
            env=git_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.strip()

    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "PulsePlate Test")
    git(source, "config", "user.email", "pulseplate-test@example.invalid")
    git(source, "checkout", "-qb", "main")
    (source / ".github" / "workflows").mkdir(parents=True)
    (source / "deploy" / "postgres-pgvector").mkdir(parents=True)
    (source / ".github" / "workflows" / "cd.yml").write_text("name: admitted\n", encoding="utf-8")
    (source / "deploy" / "postgres-pgvector" / "Containerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (source / "deploy" / "postgres-pgvector" / "image-manifest.json").write_text(
        "{}\n", encoding="utf-8"
    )
    for name in ("builder-apk-inputs.tsv", "builder-apk-index.tar.gz"):
        (source / "deploy" / "postgres-pgvector" / name).write_bytes(b"frozen input")
    _copy_pgvector_material_helpers(source)
    git(source, "add", ".")
    git(source, "commit", "-qm", "admitted material")
    admitted_sha = git(source, "rev-parse", "HEAD")
    git(source, "remote", "add", "origin", str(remote))
    git(source, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(remote), str(runner))
    git(runner, "checkout", "-q", "--detach", admitted_sha)

    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "docker %s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [[ "$*" == buildx\\ imagetools\\ create\\ * ]]; then\n'
        '  printf "name: superseding-after-promotion\\n" > '
        '"$SOURCE_REPO/.github/workflows/cd.yml"\n'
        '  "$GIT_BIN" -C "$SOURCE_REPO" add .github/workflows/cd.yml\n'
        '  "$GIT_BIN" -C "$SOURCE_REPO" commit -qm "supersede after promotion"\n'
        '  "$GIT_BIN" -C "$SOURCE_REPO" push -q origin main\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$*" == buildx\\ imagetools\\ inspect\\ * ]]; then exit 91; fi\n'
        "exit 92\n",
        encoding="utf-8",
    )
    docker_stub.chmod(0o755)
    platform_digest = "sha256:" + "a" * 64
    canonical_tag = "ghcr.io/katsiarynakavaleuskaya/pulseplate:postgres-pgvector"
    completed = subprocess.run(
        [bash_bin, "-c", promote_program],
        cwd=runner,
        env={
            **git_environment,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "GITHUB_SHA": admitted_sha,
            "GITHUB_OUTPUT": str(output_path),
            "RUNNER_TEMP": str(tmp_path),
            "CANDIDATE_RUNTIME_REF": (
                "ghcr.io/katsiarynakavaleuskaya/pulseplate:" f"candidate@{platform_digest}"
            ),
            "CANONICAL_TAG_REF": canonical_tag,
            "EXPECTED_PLATFORM_DIGEST": platform_digest,
            "EXPECTED_RUNTIME_REF": f"{canonical_tag}@{platform_digest}",
            "DOCKER_LOG": str(docker_log),
            "GIT_BIN": git_bin,
            "SOURCE_REPO": str(source),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "material superseded run" in completed.stderr
    log_lines = docker_log.read_text(encoding="utf-8").splitlines()
    assert sum("buildx imagetools create" in line for line in log_lines) == 1
    assert all("buildx imagetools inspect" not in line for line in log_lines)
    assert not output_path.exists() or "runtime_ref=" not in output_path.read_text(encoding="utf-8")
    assert git(source, "rev-parse", "HEAD") != admitted_sha


def test_cd_postgres_pins_scout_and_binds_exact_dhi_source_subjects() -> None:
    """Preserve pinned Scout execution and independent exact source-subject checks."""
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    install = next(
        step for step in steps if step.get("name") == "Install exact Docker Scout 1.24.0 CLI"
    )
    assert install["env"] == {
        "SCOUT_VERSION": "1.24.0",
        "SCOUT_ARCHIVE_SHA256": (
            "f4e2814bd61040365153d5b964b144cb2dc6ee536a68b5bac4cadf00fc0ec34b"  # pragma: allowlist secret
        ),
        "SCOUT_BUILD_COMMIT": "b1c9331b2166aef7ec690aa16fd655b8798ea4c6",  # pragma: allowlist secret
    }
    install_run = install["run"]
    assert "github.com/docker/scout-cli/releases/download/v${SCOUT_VERSION}" in install_run
    assert "sha256sum --check -" in install_run
    assert "version: v${SCOUT_VERSION} (go1.26.3 - linux/amd64)" in install_run
    assert "git commit: ${SCOUT_BUILD_COMMIT}" in install_run

    verify = next(
        step
        for step in steps
        if step.get("name") == "Verify exact DHI source provenance separately"
    )
    assert verify["env"] == {
        "SCOUT_BIN": "${{ steps.docker-scout.outputs.path }}",
        "DOCKER_SCOUT_HUB_USER": "${{ secrets.DHI_USERNAME }}",
        "DOCKER_SCOUT_HUB_PASSWORD": "${{ secrets.DHI_ACCESS_TOKEN }}",
    }
    verify_run = verify["run"]
    assert "docker scout" not in verify_run
    assert '"$SCOUT_BIN" attestation get' in verify_run
    assert "--verify" in verify_run and "--skip-tlog" in verify_run
    for exact_subject in (
        "pkg:docker/dhi/postgres@15-alpine3.23&platform=linux/amd64",
        "d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d",  # pragma: allowlist secret
        "pkg:docker/dhi/postgres@15-alpine3.23-dev&platform=linux/amd64",
        "276224f2143616286f74af844e9508db1cd50d6393163cf9ec60940b2b90f134",  # pragma: allowlist secret
        "https://slsa.dev/provenance/v1",
    ):
        assert exact_subject in verify_run

    cleanup = next(
        step
        for step in steps
        if step.get("name") == "Remove synthetic resources and temporary registry credentials"
    )
    assert cleanup["env"] == {"PRIMARY_JOB_STATUS": "${{ job.status }}"}
    assert "PGVECTOR_SCOUT_DIR" in cleanup["run"]
    assert "preserving primary ${PRIMARY_JOB_STATUS} result" in cleanup["run"]
    docs = (REPO_ROOT / "docs/deploy/OPERATIONAL_SIGNALS.md").read_text(encoding="utf-8")
    assert "verification without transparency-log proof" in docs
    assert "not a Trivy suppression" in docs


@pytest.mark.parametrize("missing", ["user", "password", "neither"])
def test_postgres_scout_authentication_fails_before_provenance_consumers(
    tmp_path: Path, missing: str
) -> None:
    """Run the real step; a rejected first authentication cannot reach later consumers."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    program = next(
        step["run"]
        for step in workflow["jobs"]["postgres-pgvector-publish"]["steps"]
        if step.get("name") == "Verify exact DHI source provenance separately"
    )
    bash = shutil.which("bash")
    assert bash is not None
    scout = tmp_path / "scout"
    calls = tmp_path / "calls"
    _write_executable(
        scout,
        '#!/bin/sh\nprintf "called\\n" >> "$SCOUT_CALLS"\n'
        'printf "Docker Scout authentication rejected\\n" >&2\nexit 43\n',
    )
    secret = "synthetic-scout-test-credential"  # pragma: allowlist secret
    env = {
        "PATH": os.defpath,
        "SCOUT_BIN": str(scout),
        "SCOUT_CALLS": str(calls),
        "DOCKER_SCOUT_HUB_USER": "" if missing == "user" else "synthetic-user",
        "DOCKER_SCOUT_HUB_PASSWORD": "" if missing == "password" else secret,
    }
    result = subprocess.run(
        [bash, "-c", program],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert secret not in result.stdout + result.stderr
    if missing == "neither":
        assert result.returncode == 43
        assert calls.read_text().splitlines() == ["called"]
        assert "authentication rejected" in result.stderr
    else:
        assert not calls.exists()
        assert "is required" in result.stderr
    assert not list(tmp_path.glob("dhi-postgres-*-provenance.json"))


@pytest.mark.parametrize("source", ["runtime", "builder"])
@pytest.mark.parametrize(
    ("fault", "diagnostic"),
    [
        ("valid", ""),
        ("statement-v1", "not the pinned DHI in-toto v0.1 statement"),
        ("statement-missing", "not the pinned DHI in-toto v0.1 statement"),
        ("statement-scalar", "not the pinned DHI in-toto v0.1 statement"),
        ("predicate-version", "predicate type drifted"),
        ("subject-name", "exact DHI platform subject drifted"),
        ("subject-digest", "exact DHI platform subject drifted"),
        ("subject-extra", "exact DHI platform subject drifted"),
        ("subject-missing", "exact DHI platform subject drifted"),
        ("predicate-empty", "provenance predicate is malformed"),
        ("predicate-list", "provenance predicate is malformed"),
        ("predicate-null", "provenance predicate is malformed"),
        ("root-list", "not the pinned DHI in-toto v0.1 statement"),
        ("root-null", "not the pinned DHI in-toto v0.1 statement"),
        ("malformed-json", "JSONDecodeError"),
        ("missing-file", ""),
        ("empty-file", ""),
        ("symlink-file", ""),
        ("scout-failure", "synthetic Scout verification failure"),
    ],
)
def test_postgres_scout_source_statement_consumer(
    tmp_path: Path, source: str, fault: str, diagnostic: str
) -> None:
    """Exercise the whole step; recorded Scout output is not signature verification.

    The output shape follows native artifact 10124696818 from CD run 34403818948.
    Current digest substitutions are synthetic; that archive verified predecessor subjects.
    Statement/v0.1 and SLSA predicate/v1 are independent schema identifiers.
    """
    identities = {
        "runtime": (
            "pkg:docker/dhi/postgres@15-alpine3.23&platform=linux/amd64",
            "d94fee7e5e98fcb5cd58db6ad96fc6aa844f1af6dd56aba1f87d9f8e57a7a16d",  # pragma: allowlist secret
        ),
        "builder": (
            "pkg:docker/dhi/postgres@15-alpine3.23-dev&platform=linux/amd64",
            "276224f2143616286f74af844e9508db1cd50d6393163cf9ec60940b2b90f134",  # pragma: allowlist secret
        ),
    }
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    for key, (name, digest) in identities.items():
        payload = {
            "_type": "https://in-toto.io/Statement/v0.1",
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": name, "digest": {"sha256": digest}}],
            "predicate": {"buildDefinition": {}, "runDetails": {}},
        }
        if key == source:
            if fault == "statement-v1":
                payload["_type"] = "https://in-toto.io/Statement/v1"
            elif fault == "statement-missing":
                payload.pop("_type")
            elif fault == "statement-scalar":
                payload["_type"] = 1
            elif fault == "predicate-version":
                payload["predicateType"] = "https://slsa.dev/provenance/v0.2"
            elif fault == "subject-name":
                payload["subject"] = [{"name": "other-platform", "digest": {"sha256": digest}}]
            elif fault == "subject-digest":
                payload["subject"] = [{"name": name, "digest": {"sha256": "0" * 64}}]
            elif fault == "subject-extra":
                payload["subject"] *= 2
            elif fault == "subject-missing":
                payload["subject"] = []
            elif fault.startswith("predicate-"):
                payload["predicate"] = {
                    "predicate-empty": {},
                    "predicate-list": [],
                    "predicate-null": None,
                }[fault]
        encoded = json.dumps(payload)
        if key == source:
            encoded = {"root-list": "[]", "root-null": "null", "malformed-json": "{"}.get(
                fault, encoded
            )
        (fixtures / f"{key}.json").write_text(encoded, encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python3").symlink_to(sys.executable)
    scout = bin_dir / "scout"
    calls = tmp_path / "calls"
    _write_executable(
        scout,
        f"#!{sys.executable}\n"
        "import json, os, sys\nfrom pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "assert args[:6] == ['attestation', 'get', '--predicate-type', "
        "'https://slsa.dev/provenance/v1', '--verify', '--skip-tlog']\n"
        "assert len(args) == 9 and args[6] == '--output'\n"
        "key = {'dhi-postgres-runtime-provenance.json': 'runtime', "
        "'dhi-postgres-builder-provenance.json': 'builder'}[args[7]]\n"
        f"identities = {identities!r}\n"
        "assert args[8] == 'registry://dhi.io/postgres@sha256:' + identities[key][1]\n"
        "with open(os.environ['SCOUT_CALLS'], 'a') as stream: stream.write(key + '\\n')\n"
        "fault = os.environ['SCOUT_FAULT'] if key == os.environ['SCOUT_SOURCE'] else 'valid'\n"
        "output = Path(args[7]); fixture = Path(os.environ['SCOUT_FIXTURES']) / (key + '.json')\n"
        "if fault == 'symlink-file': output.symlink_to(fixture)\n"
        "elif fault != 'missing-file': output.write_bytes(b'' if fault == 'empty-file' "
        "else fixture.read_bytes())\n"
        "if fault == 'scout-failure':\n"
        "    print('synthetic Scout verification failure', file=sys.stderr)\n"
        "    sys.exit(43)\n",
    )
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    program = next(
        step["run"]
        for step in workflow["jobs"]["postgres-pgvector-publish"]["steps"]
        if step.get("name") == "Verify exact DHI source provenance separately"
    )
    bash = shutil.which("bash")
    assert bash is not None
    secret = "synthetic-scout-consumer-credential"  # pragma: allowlist secret
    result = subprocess.run(
        [bash, "-c", program],
        cwd=tmp_path,
        env={
            "PATH": str(bin_dir) + os.pathsep + os.defpath,
            "SCOUT_BIN": str(scout),
            "SCOUT_CALLS": str(calls),
            "SCOUT_FIXTURES": str(fixtures),
            "SCOUT_SOURCE": source,
            "SCOUT_FAULT": fault,
            "DOCKER_SCOUT_HUB_USER": "synthetic-user",
            "DOCKER_SCOUT_HUB_PASSWORD": secret,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is (fault == "valid"), result.stderr
    assert secret not in result.stdout + result.stderr
    assert diagnostic in result.stderr
    expected_calls = (
        ["runtime"] if source == "runtime" and fault == "scout-failure" else ["runtime", "builder"]
    )
    assert calls.read_text().splitlines() == expected_calls
    if fault == "scout-failure":
        assert result.returncode == 43


def _postgres_publish_cleanup_program() -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    step = next(
        item
        for item in steps
        if item.get("name") == "Remove synthetic resources and temporary registry credentials"
    )
    return step["run"]


def _postgres_setup_program() -> str:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    return next(
        step["run"]
        for step in workflow["jobs"]["postgres-pgvector-publish"]["steps"]
        if step.get("name") == "Authenticate DHI read and GHCR publication rails"
    )


def _isolated_pgvector_credentials(root: Path, directory: Path | None = None) -> dict[str, str]:
    """Execute the first-party adapter without repository or real HOME access."""
    modules = root / "scripts" / "ci"
    modules.mkdir(parents=True)
    for filename in (
        "ghcr_attestation_credentials.py",
        "check_pgvector_attestations.py",
        "check_docker_provenance_attestation.py",
    ):
        shutil.copyfile(REPO_ROOT / "scripts" / "ci" / filename, modules / filename)
    home = root / "home"
    default = home / ".docker"
    default.mkdir(parents=True, mode=0o700)
    (default / "config.json").write_bytes(b"unchanged default credentials\n")
    (default / "config.json").chmod(0o600)
    environment = {"HOME": str(home), "PYTHONPATH": "", "RUNNER_TEMP": str(root)}
    if directory is not None:
        directory.chmod(0o700)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.ci.ghcr_attestation_credentials",
                "capture",
                "--directory",
                str(directory),
            ],
            cwd=root,
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
    return environment


@pytest.mark.parametrize(
    "fail_command",
    (
        "",
        "buildx-download",
        "buildx-checksum",
        "buildx-version-mismatch",
        "buildx-version-missing",
        "buildx-version-malformed",
        "login:dhi.io",
        "login:ghcr.io",
        "buildx:create",
        "buildx:inspect",
    ),
)
def test_postgres_setup_propagates_owned_context_between_processes(
    tmp_path: Path, fail_command: str
) -> None:
    """GITHUB_ENV reaches the next process but must not mask first-step export."""
    bash = shutil.which("bash")
    assert bash is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    isolated_environment = _isolated_pgvector_credentials(tmp_path)
    default_config = Path(isolated_environment["HOME"]) / ".docker"
    sentinel = default_config / "config.json"
    original_bytes, original_mode = sentinel.read_bytes(), stat.S_IMODE(sentinel.stat().st_mode)
    command_log = tmp_path / "docker.log"
    fixture_client = b"synthetic Buildx client bytes\n"
    _write_executable(
        bin_dir / "curl",
        f"#!{sys.executable}\nimport os, sys\nfrom pathlib import Path\n"
        "if os.environ['FAIL_COMMAND'] == 'buildx-download': sys.exit(22)\n"
        f"data = {fixture_client!r}\n"
        "if os.environ['FAIL_COMMAND'] == 'buildx-checksum': data += b'changed'\n"
        "Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(data)\n",
    )
    docker = bin_dir / "docker"
    _write_executable(
        docker,
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'config="${DOCKER_CONFIG:-$DEFAULT_CONFIG}"\n'
        'printf "%s|%s\\n" "$config" "$*" >> "$COMMAND_LOG"\n'
        'if [ "$1" = login ]; then cat >/dev/null; printf synthetic > "$config/config.json"; fi\n'
        'if [ "$1:${2:-}" = buildx:create ]; then touch "$config/builder"; fi\n'
        'if [ "$FAIL_COMMAND" = "$1:${2:-}" ]; then exit 73; fi\n'
        'if [ "$1:${2:-}" = buildx:version ]; then '
        'echo "github.com/docker/buildx v0.37.0 '
        'ac30b249211430b85fb8f37b6e7154b5c47ba0b6"; fi\n'
        'if [ "$1:${2:-}" = buildx:inspect ]; then echo "BuildKit version:      v0.32.2"; fi\n'
        'if [ "$1:${2:-}" = buildx:ls ] && [ -f "$config/builder" ]; then echo pulseplate-pgvector-builder-1234-2; fi\n'
        'if [ "$1:${2:-}" = buildx:rm ]; then rm "$config/builder"; fi\n',
    )
    env_file = tmp_path / "github-env"
    env_file.touch()
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"DOCKER_CONFIG", "PGVECTOR_DOCKER_CONFIG", "PGVECTOR_BUILDX_BUILDER"}
    }
    environment.update(
        PATH=f"{bin_dir}:{os.environ['PATH']}",
        RUNNER_TEMP=str(tmp_path),
        GITHUB_ENV=str(env_file),
        GITHUB_RUN_ID="1234",
        GITHUB_RUN_ATTEMPT="2",
        DHI_USER="synthetic-dhi-user",
        DHI_TOKEN="synthetic-dhi-token",
        GHCR_USER="synthetic-ghcr-user",
        GHCR_TOKEN_VALUE="synthetic-ghcr-token",
        DEFAULT_CONFIG=str(default_config),
        COMMAND_LOG=str(command_log),
        FAIL_COMMAND=fail_command,
        BUILDX_VERSION={
            "buildx-version-mismatch": "0.38.0",
            "buildx-version-missing": "",
            "buildx-version-malformed": "0.37.0/other",
        }.get(fail_command, "0.37.0"),
        BUILDX_SHA256=hashlib.sha256(fixture_client).hexdigest(),
        BUILDKIT_DIGEST=json.loads(POSTGRES_MANIFEST_PATH.read_bytes())[
            "buildkit_platform_manifest_digest"
        ],
        BUILDKIT_VERSION=json.loads(POSTGRES_MANIFEST_PATH.read_bytes())["buildkit_version"],
    )
    environment.update(isolated_environment)
    first = subprocess.run(
        [bash, "-c", _postgres_setup_program()],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    expected_exit = {
        "": 0,
        "buildx-download": 22,
        "buildx-checksum": 1,
        "buildx-version-mismatch": 1,
        "buildx-version-missing": 1,
        "buildx-version-malformed": 1,
    }.get(fail_command, 73)
    assert first.returncode == expected_exit, first.stderr
    emitted = dict(line.split("=", 1) for line in env_file.read_text().splitlines())
    selected = emitted["DOCKER_CONFIG"]
    assert stat.S_IMODE(Path(selected).stat().st_mode) == 0o700
    second = subprocess.run(
        [bash, "-c", _postgres_publish_cleanup_program()],
        env={
            **environment,
            **emitted,
            "FAIL_COMMAND": "",
            "PRIMARY_JOB_STATUS": "failure" if fail_command else "success",
        },
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert emitted["PGVECTOR_DOCKER_CONFIG"] == selected
    assert Path(selected).parent == tmp_path
    assert Path(selected).name.startswith("pulseplate-pgvector-docker-config.")
    assert all(line.split("|", 1)[0] == selected for line in command_log.read_text().splitlines())
    assert sentinel.read_bytes() == original_bytes
    assert stat.S_IMODE(sentinel.stat().st_mode) == original_mode
    assert not Path(selected).exists()
    for secret in (environment["DHI_TOKEN"], environment["GHCR_TOKEN_VALUE"]):
        assert (
            secret
            not in first.stdout
            + first.stderr
            + second.stdout
            + second.stderr
            + command_log.read_text()
        )
        assert secret not in env_file.read_text()


def test_postgres_scout_directory_is_inside_its_cleanup_slot() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    install = next(
        step
        for step in workflow["jobs"]["postgres-pgvector-publish"]["steps"]
        if step.get("name") == "Install exact Docker Scout 1.24.0 CLI"
    )
    assert "${RUNNER_TEMP}/pulseplate-pgvector-scout.XXXXXX" in install["run"]


@pytest.mark.parametrize(
    ("primary_status", "cleanup_status", "expected_status"),
    (
        ("success", "0", 0),
        ("success", "71", 1),
        ("failure", "0", 0),
        ("failure", "71", 0),
        ("cancelled", "71", 0),
    ),
)
def test_cd_postgres_publish_cleanup_executes_primary_secondary_state_machine(
    tmp_path: Path,
    primary_status: str,
    cleanup_status: str,
    expected_status: int,
) -> None:
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [ "${1:-}" = logout ]; then exit "${STUB_LOGOUT_STATUS:-0}"; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    docker_stub.chmod(0o700)
    credential_dir = tmp_path / "pulseplate-pgvector-docker-config.test"
    credential_dir.mkdir()
    isolated_environment = _isolated_pgvector_credentials(tmp_path, credential_dir)
    completed = subprocess.run(
        [bash_bin, "-c", _postgres_publish_cleanup_program()],
        cwd=tmp_path,
        env={
            **os.environ,
            **isolated_environment,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "PRIMARY_JOB_STATUS": primary_status,
            "STUB_LOGOUT_STATUS": cleanup_status,
            "RUNNER_TEMP": str(tmp_path),
            "PGVECTOR_RESOURCE_PREFIX": "",
            "PGVECTOR_BUILDX_BUILDER": "",
            "PGVECTOR_CONTEXT_DIR": "",
            "PGVECTOR_OCI_OUTPUT_DIR": "",
            "PGVECTOR_TRIVY_DIR": "",
            "PGVECTOR_SCOUT_DIR": "",
            "PGVECTOR_DOCKER_CONFIG": str(credential_dir),
            "DOCKER_CONFIG": str(credential_dir),
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == expected_status
    assert not credential_dir.exists()
    assert (
        Path(isolated_environment["HOME"]) / ".docker/config.json"
    ).read_bytes() == b"unchanged default credentials\n"
    if primary_status != "success" and cleanup_status != "0":
        assert f"preserving primary {primary_status} result" in completed.stderr


@pytest.mark.parametrize(
    ("primary_status", "expected_status"),
    (("success", 1), ("failure", 0), ("cancelled", 0)),
)
def test_cd_postgres_publish_cleanup_accounts_for_bounded_rm_failure(
    tmp_path: Path,
    primary_status: str,
    expected_status: int,
) -> None:
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    docker_stub.chmod(0o700)
    rm_stub = bin_dir / "rm"
    rm_stub.write_text(
        "#!/usr/bin/env bash\necho 'synthetic rm failure' >&2\nexit 72\n",
        encoding="utf-8",
    )
    rm_stub.chmod(0o700)
    credential_dir = tmp_path / "pulseplate-pgvector-docker-config.test"
    credential_dir.mkdir()
    isolated_environment = _isolated_pgvector_credentials(tmp_path, credential_dir)
    context_dir = tmp_path / "pulseplate-pgvector-context.test"
    context_dir.mkdir()
    completed = subprocess.run(
        [bash_bin, "-c", _postgres_publish_cleanup_program()],
        cwd=tmp_path,
        env={
            **os.environ,
            **isolated_environment,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "PRIMARY_JOB_STATUS": primary_status,
            "RUNNER_TEMP": str(tmp_path),
            "PGVECTOR_RESOURCE_PREFIX": "",
            "PGVECTOR_BUILDX_BUILDER": "",
            "PGVECTOR_CONTEXT_DIR": str(context_dir),
            "PGVECTOR_OCI_OUTPUT_DIR": "",
            "PGVECTOR_TRIVY_DIR": "",
            "PGVECTOR_SCOUT_DIR": "",
            "PGVECTOR_DOCKER_CONFIG": str(credential_dir),
            "DOCKER_CONFIG": str(credential_dir),
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == expected_status
    assert context_dir.is_dir()
    assert not credential_dir.exists()
    if primary_status != "success":
        assert f"preserving primary {primary_status} result" in completed.stderr


@pytest.mark.parametrize(
    ("inventory_status", "present", "primary_status", "expected"),
    (
        (0, False, "success", 0),
        (0, True, "success", 0),
        (73, False, "success", 1),
        (73, False, "failure", 0),
    ),
)
def test_postgres_cleanup_distinguishes_inventory_failure_from_absence(
    tmp_path: Path, inventory_status: int, present: bool, primary_status: str, expected: int
) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands"
    config = tmp_path / "pulseplate-pgvector-docker-config.test"
    config.mkdir()
    isolated_environment = _isolated_pgvector_credentials(tmp_path, config)
    scout = tmp_path / "pulseplate-pgvector-scout.test"
    scout.mkdir()
    _write_executable(
        bin_dir / "docker",
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'printf "%s|%s\\n" "$DOCKER_CONFIG" "$*" >> "$COMMAND_LOG"\n'
        'if [ "${2:-}" = ls ]; then\n'
        '  if [ "$INVENTORY_STATUS" != 0 ]; then exit "$INVENTORY_STATUS"; fi\n'
        '  if [ "$PRESENT" = yes ]; then\n'
        '    case "$1" in\n'
        '      container) printf "%s\\n" pulseplate-pgvector-1234-2-postgres;;\n'
        '      volume) printf "%s\\n" pulseplate-pgvector-1234-2-data;;\n'
        '      image) printf "%s\\n" pulseplate-pgvector-1234-2-final:latest;;\n'
        '      buildx) printf "%s\\n" pulseplate-pgvector-builder-1234-2;;\n'
        "    esac\n  fi\nfi\n",
    )
    completed = subprocess.run(
        [bash, "-c", _postgres_publish_cleanup_program()],
        cwd=tmp_path,
        env={
            **os.environ,
            **isolated_environment,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "COMMAND_LOG": str(log),
            "INVENTORY_STATUS": str(inventory_status),
            "PRESENT": "yes" if present else "no",
            "DOCKER_CONFIG": str(config),
            "PGVECTOR_DOCKER_CONFIG": str(config),
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_RUN_ID": "1234",
            "GITHUB_RUN_ATTEMPT": "2",
            "PGVECTOR_RESOURCE_PREFIX": "pulseplate-pgvector-1234-2",
            "PGVECTOR_BUILDX_BUILDER": "pulseplate-pgvector-builder-1234-2",
            "PGVECTOR_CONTEXT_DIR": "",
            "PGVECTOR_OCI_OUTPUT_DIR": "",
            "PGVECTOR_TRIVY_DIR": "",
            "PGVECTOR_SCOUT_DIR": str(scout),
            "PRIMARY_JOB_STATUS": primary_status,
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == expected, completed.stderr
    commands = log.read_text().splitlines()
    assert all(line.split("|", 1)[0] == str(config) for line in commands)
    assert not config.exists() and not scout.exists()
    removed = [line for line in commands if " rm " in line or "|rm " in line]
    assert bool(removed) == present
    if inventory_status:
        assert "inventory query failed" in completed.stderr
        if primary_status == "failure":
            assert "preserving primary failure" in completed.stderr


@pytest.mark.parametrize("unsafe_kind", ("foreign-slot", "nested", "traversal", "symlink"))
def test_postgres_cleanup_refuses_foreign_directory_but_cleans_owned_scout(
    tmp_path: Path, unsafe_kind: str
) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands"
    _write_executable(bin_dir / "docker", f'#!/bin/sh\necho "$*" >> "{log}"\n')
    outside = tmp_path / "keep"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("keep", encoding="utf-8")
    if unsafe_kind == "foreign-slot":
        unsafe = tmp_path / "pulseplate-pgvector-trivy.keep"
        unsafe.mkdir()
    elif unsafe_kind == "nested":
        parent = tmp_path / "pulseplate-pgvector-context.test"
        parent.mkdir()
        unsafe = parent / "child"
        unsafe.mkdir()
    elif unsafe_kind == "traversal":
        parent = tmp_path / "pulseplate-pgvector-context.test"
        parent.mkdir()
        unsafe = parent / ".." / "keep"
    else:
        unsafe = tmp_path / "pulseplate-pgvector-context.test"
        unsafe.symlink_to(outside, target_is_directory=True)
    scout = tmp_path / "pulseplate-pgvector-scout.test"
    scout.mkdir()
    completed = subprocess.run(
        [bash, "-c", _postgres_publish_cleanup_program()],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
            "PRIMARY_JOB_STATUS": "success",
            "PGVECTOR_DOCKER_CONFIG": "",
            "PGVECTOR_RESOURCE_PREFIX": "",
            "PGVECTOR_BUILDX_BUILDER": "",
            "PGVECTOR_CONTEXT_DIR": str(unsafe),
            "PGVECTOR_OCI_OUTPUT_DIR": "",
            "PGVECTOR_TRIVY_DIR": "",
            "PGVECTOR_SCOUT_DIR": str(scout),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 1
    assert "Refusing cleanup" in completed.stderr
    assert unsafe.exists() and sentinel.read_text() == "keep"
    assert not scout.exists()
    assert not log.exists(), "no setup means no Docker/logout calls into default context"


def _workflow_trap_prefix(step_name: str, *, suffix: str) -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    step = next(
        step
        for job in jobs.values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("name") == step_name
    )
    prefix = step["run"].split("trap cleanup EXIT", maxsplit=1)[0]
    return prefix + "trap cleanup EXIT\n" + suffix


def _staging_cleanup_program() -> str:
    script = (REPO_ROOT / "scripts/deploy.sh").read_text(encoding="utf-8")
    start = script.index("cleanup() {\n")
    end = script.index("\n}\ntrap cleanup EXIT", start) + len("\n}\n")
    return script[start:end] + 'trap cleanup EXIT\nexit "$TEST_PRIMARY_STATUS"\n'


@pytest.mark.parametrize(
    ("surface", "primary_status", "rm_status", "expected_status"),
    (
        ("prometheus", "0", "0", 0),
        ("prometheus", "0", "72", 1),
        ("prometheus", "33", "72", 33),
        ("prometheus-oci", "0", "0", 0),
        ("prometheus-oci", "0", "72", 1),
        ("prometheus-oci", "33", "72", 33),
        ("reuse", "0", "0", 0),
        ("reuse", "0", "72", 1),
        ("reuse", "33", "72", 33),
        ("staging", "0", "0", 0),
        ("staging", "0", "72", 1),
        ("staging", "33", "72", 33),
    ),
)
def test_other_bounded_cleanup_traps_preserve_primary_and_account_for_rm(
    tmp_path: Path,
    surface: str,
    primary_status: str,
    rm_status: str,
    expected_status: int,
) -> None:
    bash_bin = shutil.which("bash")
    real_rm = shutil.which("rm")
    assert bash_bin is not None and real_rm is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "${1:-}" = logout ]; then exit 0; fi\n'
        'if [ "${1:-}" = container ] || [ "${1:-}" = volume ]; then exit 1; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    docker_stub.chmod(0o700)
    rm_stub = bin_dir / "rm"
    rm_stub.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "${STUB_RM_STATUS:-0}" -ne 0 ]; then exit "$STUB_RM_STATUS"; fi\n'
        'exec "$REAL_RM" "$@"\n',
        encoding="utf-8",
    )
    rm_stub.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "REAL_RM": real_rm,
        "STUB_RM_STATUS": rm_status,
        "RUNNER_TEMP": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/main",
        "MATERIAL_CHANGED": "false",
        "TEST_PRIMARY_STATUS": primary_status,
    }
    if surface == "prometheus":
        program = _workflow_trap_prefix(
            "Prove synthetic non-root header and named-volume runtime",
            suffix='exit "$TEST_PRIMARY_STATUS"\n',
        )
        expected_dir_prefix = "pulseplate-obs1b-ci-123-1."
    elif surface == "prometheus-oci":
        program = _workflow_trap_prefix(
            "Cross-bind immutable index, linux amd64 manifest, and local image config",
            suffix='exit "$TEST_PRIMARY_STATUS"\n',
        )
        expected_dir_prefix = "pulseplate-obs1b-oci."
    elif surface == "reuse":
        program = _workflow_trap_prefix(
            "Read-only admit the existing exact PostgreSQL digest",
            suffix='exit "$TEST_PRIMARY_STATUS"\n',
        )
        expected_dir_prefix = "pulseplate-pgvector-reuse-docker."
    else:
        credential_dir = tmp_path / "pulseplate-docker-config.test"
        credential_dir.mkdir()
        environment["DOCKER_CONFIG"] = str(credential_dir)
        program = _staging_cleanup_program()
        expected_dir_prefix = credential_dir.name
    completed = subprocess.run(
        [bash_bin, "-c", program],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == expected_status, completed.stderr
    matching_dirs = [
        path for path in tmp_path.iterdir() if path.name.startswith(expected_dir_prefix)
    ]
    if rm_status == "0":
        assert matching_dirs == []
    else:
        assert matching_dirs
        if primary_status != "0":
            assert "preserving primary exit 33" in completed.stderr


@pytest.mark.parametrize("failure_target", ("config", "directory"))
def test_production_credential_cleanup_rejects_rm_failure_without_false_success(
    tmp_path: Path,
    failure_target: str,
) -> None:
    script = (REPO_ROOT / "scripts/deploy_production.sh").read_text(encoding="utf-8")
    start = script.index("cleanup_ghcr_credentials() {\n")
    end = script.index("\n}\n\nvalidate_regular_non_symlink_file", start) + len("\n}\n")
    function_source = script[start:end]
    bash_bin = shutil.which("bash")
    real_rm = shutil.which("rm")
    assert bash_bin is not None and real_rm is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    docker_stub.chmod(0o700)
    rm_stub = bin_dir / "rm"
    rm_stub.write_text(
        "#!/usr/bin/env bash\n"
        'target="${*: -1}"\n'
        'if [ "${STUB_FAIL_TARGET:-}" = config ] && [[ "$target" = */config.json ]]; then exit 72; fi\n'
        'if [ "${STUB_FAIL_TARGET:-}" = directory ] && [[ "$target" = /tmp/pulseplate-production-docker-config.* ]]; then exit 72; fi\n'
        'exec "$REAL_RM" "$@"\n',
        encoding="utf-8",
    )
    rm_stub.chmod(0o700)
    credential_dir = (
        Path("/tmp") / f"pulseplate-production-docker-config.test-{os.getpid()}-{failure_target}"
    )
    credential_dir.mkdir(exist_ok=False)
    (credential_dir / "config.json").write_text("{}\n", encoding="utf-8")
    try:
        program = (
            function_source
            + "\nif cleanup_ghcr_credentials; then echo FALSE_SUCCESS; exit 0; "
            + 'else status=$?; printf "RETAINED=%s\\n" "$GHCR_DOCKER_CONFIG"; exit "$status"; fi\n'
        )
        completed = subprocess.run(
            [bash_bin, "-c", program],
            env={
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "REAL_RM": real_rm,
                "STUB_FAIL_TARGET": failure_target,
                "DOCKER_BIN": str(docker_stub),
                "DOCKER_CONFIG": str(credential_dir),
                "GHCR_DOCKER_CONFIG": str(credential_dir),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode != 0
        assert "FALSE_SUCCESS" not in completed.stdout
        assert f"RETAINED={credential_dir}" in completed.stdout
    finally:
        config_path = credential_dir / "config.json"
        if config_path.exists():
            config_path.unlink()
        if credential_dir.exists():
            credential_dir.rmdir()


@pytest.mark.parametrize(
    ("validation_status", "rm_status", "expected_status"),
    (("0", "0", 0), ("0", "72", 1), ("33", "72", 33)),
)
def test_production_shell_bundle_validation_cleanup_preserves_primary_status(
    tmp_path: Path,
    validation_status: str,
    rm_status: str,
    expected_status: int,
) -> None:
    script = (REPO_ROOT / "scripts/deploy_production.sh").read_text(encoding="utf-8")
    start = script.index("validate_shell_bundle_archive() {\n")
    end = script.index("\n}\n\nextract_shell_bundle_archive", start) + len("\n}\n")
    function_source = script[start:end]
    bash_bin = shutil.which("bash")
    real_rm = shutil.which("rm")
    assert bash_bin is not None and real_rm is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    rm_stub = bin_dir / "rm"
    rm_stub.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "${*: -1}" > "$STUB_RM_LOG"\n'
        'if [ "${STUB_RM_STATUS:-0}" -ne 0 ]; then exit "$STUB_RM_STATUS"; fi\n'
        'exec "$REAL_RM" "$@"\n',
        encoding="utf-8",
    )
    rm_stub.chmod(0o700)
    rm_log = tmp_path / "rm-target.txt"
    program = (
        "set -euo pipefail\n"
        'process_shell_bundle_archive() { return "$STUB_VALIDATION_STATUS"; }\n'
        "validate_shell_bundle_contract() { return 0; }\n"
        + function_source
        + '\nif validate_shell_bundle_archive; then exit 0; else exit "$?"; fi\n'
    )
    completed = subprocess.run(
        [bash_bin, "-c", program],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "REAL_RM": real_rm,
            "STUB_RM_LOG": str(rm_log),
            "STUB_RM_STATUS": rm_status,
            "STUB_VALIDATION_STATUS": validation_status,
            "SHELL_BUNDLE_ARCHIVE": "/tmp/pulseplate-shell-bundle-1-1.tgz",
            "SHELL_BUNDLE_DIR": "",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == expected_status
    validation_root = Path(rm_log.read_text(encoding="utf-8").strip())
    if rm_status == "0":
        assert not validation_root.exists()
    else:
        assert validation_root.is_dir()
        validation_root.rmdir()
    if validation_status != "0" and rm_status != "0":
        assert "preserving primary exit 33" in completed.stderr


@pytest.mark.parametrize(
    ("variant", "expected_returncode"),
    (("exact", 0), ("content-drift", 1), ("hardlink", 1), ("writable", 1)),
)
def test_published_backup_helper_binding_rejects_post_publication_drift(
    tmp_path: Path,
    variant: str,
    expected_returncode: int,
) -> None:
    script = (REPO_ROOT / "scripts/deploy_production.sh").read_text(encoding="utf-8")
    start = script.index("validate_published_backup_helper_binding() {\n")
    end = script.index("\n}\n\nvalidate_production_database_contract", start) + len("\n}\n")
    function_source = script[start:end]
    bash_bin = shutil.which("bash")
    assert bash_bin is not None

    shell_bundle_dir = tmp_path / "shell-bundle"
    source_ops_dir = shell_bundle_dir / "scripts" / "ops"
    destination_ops_dir = tmp_path / "production" / "scripts" / "ops"
    source_ops_dir.mkdir(parents=True)
    destination_ops_dir.mkdir(parents=True)
    source_helper = source_ops_dir / "postgres_backup.sh"
    destination_helper = destination_ops_dir / "postgres_backup.sh"
    reviewed_bytes = b"#!/usr/bin/env bash\nprintf 'reviewed-helper\\n'\n"
    source_helper.write_bytes(reviewed_bytes)
    source_helper.chmod(0o755)
    destination_helper.write_bytes(reviewed_bytes)
    destination_helper.chmod(0o755)

    if variant == "content-drift":
        destination_helper.write_bytes(b"#!/usr/bin/env bash\nprintf 'drifted-helper\\n'\n")
        destination_helper.chmod(0o755)
    elif variant == "hardlink":
        destination_helper.unlink()
        external = tmp_path / "hardlinked-helper"
        external.write_bytes(reviewed_bytes)
        external.chmod(0o755)
        os.link(external, destination_helper)
    elif variant == "writable":
        destination_helper.chmod(0o775)

    program = (
        "set -euo pipefail\n"
        "validate_contract_destinations_safely() { :; }\n"
        + function_source
        + "\nvalidate_published_backup_helper_binding\n"
    )
    completed = subprocess.run(
        [bash_bin, "-c", program],
        env={
            **os.environ,
            "PYTHON_BIN": sys.executable,
            "SHELL_BUNDLE_DIR": str(shell_bundle_dir),
            "BACKUP_HELPER": str(destination_helper),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == expected_returncode, completed.stderr
    if expected_returncode != 0:
        assert "backup-helper" in completed.stderr or "backup helper" in completed.stderr


def test_cd_postgres_material_helper_is_shared_by_producer_and_consumers() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    publish = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    generator = next(
        step
        for step in publish
        if step.get("name") == "Generate exact PostgreSQL material predicate"
    )
    assert "scripts/ci/check_pgvector_attestations.py generate" in generator["run"]
    candidate = next(
        step
        for step in publish
        if step.get("name")
        == "Verify candidate pullback, material provenance, SBOM, and runtime identity"
    )
    assert "scripts/ci/check_pgvector_attestations.py verify" in candidate["run"]
    reuse = workflow["jobs"]["postgres-pgvector-reuse"]["steps"][1]
    assert "scripts/ci/check_pgvector_attestations.py verify" in reuse["run"]
    helper = (REPO_ROOT / "scripts/ci/check_pgvector_attestations.py").read_text()
    assert '"recipe": copy.deepcopy(manifest)' in helper
    assert "material_dependencies(manifest)" in helper


def test_postgres_final_scanner_consumes_the_verified_oci_layout() -> None:
    """Trivy 0.74 accepts an OCI directory; its Docker-tar input is a different format."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    scan = next(
        step["run"]
        for step in steps
        if step.get("name")
        == "Scan exact bases, post-APK builder, and final image without suppressions"
    )
    assert '--input "$PGVECTOR_OCI_OUTPUT_DIR/oci-1"' in scan
    assert '--input "$PGVECTOR_OCI_OUTPUT_DIR/image-1.oci.tar"' not in scan
    assert "--exit-code 1" in scan
    assert "--scanners vuln,secret" in scan


def _postgres_oci_verifier_program() -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    step = next(
        item for item in steps if item.get("name") == "Reproduce the exact platform manifest twice"
    )
    run = step["run"]
    marker = "python3 - \"$output_dir/oci-1\" <<'PY'\n"
    assert run.count(marker) == 1
    program, remainder = run.split(marker, maxsplit=1)[1].split("\nPY\n", maxsplit=1)
    assert "docker buildx build" in remainder
    return program


def _generated_mountpoint_layer(
    *,
    uid: int = 70,
    mode: int = 0o700,
    mtime: int = 1_785_349_734,
    extra_file: bool = False,
) -> tuple[bytes, str]:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for path in ("var", "var/lib", "var/lib/postgresql", "var/lib/postgresql/data"):
            member = tarfile.TarInfo(path)
            member.type = tarfile.DIRTYPE
            member.uid = uid
            member.gid = 70
            member.mode = mode
            member.mtime = mtime
            archive.addfile(member)
        if extra_file:
            member = tarfile.TarInfo("var/lib/postgresql/data/unexpected")
            member.type = tarfile.REGTYPE
            member.uid = 70
            member.gid = 70
            member.mode = 0o600
            member.mtime = mtime
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
    tar_bytes = payload.getvalue()
    return gzip.compress(tar_bytes, compresslevel=9, mtime=mtime), (
        "sha256:" + hashlib.sha256(tar_bytes).hexdigest()
    )


def _write_postgres_oci_verifier_fixture(
    tmp_path: Path, variant: str
) -> tuple[Path, dict[str, str]]:
    fixture_root = tmp_path / variant
    blobs = fixture_root / "blobs" / "sha256"
    blobs.mkdir(parents=True)
    if variant in {"valid", "arm64", "manifest-bytes"}:
        layer_bytes = MOUNTPOINT_LAYER_GZIP
        layer_diff_id = "sha256:830c8272961c65f32876a884f52d80ad05cc4534a37bd0ecd4dafcf155f656fc"
    else:
        layer_bytes, layer_diff_id = _generated_mountpoint_layer(
            uid=0 if variant == "uid" else 70,
            mode=0o755 if variant == "mode" else 0o700,
            mtime=1_785_349_735 if variant == "mtime" else 1_785_349_734,
            extra_file=variant == "extra",
        )
    layer_digest = "sha256:" + hashlib.sha256(layer_bytes).hexdigest()
    (blobs / layer_digest.removeprefix("sha256:")).write_bytes(layer_bytes)
    config = {
        "architecture": "amd64",
        "os": "linux",
        "config": {
            "User": "70",
            "Entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
            "Env": [
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PGDATA=/var/lib/postgresql/15/data",
                "PG_MAJOR=15",
                "PG_MINOR=19",
            ],
        },
        "rootfs": {
            "type": "layers",
            "diff_ids": ["sha256:" + "0" * 64] * 12
            + ["sha256:" + "f" * 64 if variant == "diff-id" else layer_diff_id],
        },
    }
    config_bytes = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    config_digest = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    (blobs / config_digest.removeprefix("sha256:")).write_bytes(config_bytes)
    dummy_layer = {
        "digest": "sha256:" + "0" * 64,
        "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        "size": 0,
    }
    manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {
            "digest": config_digest,
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": len(config_bytes),
        },
        "layers": [dummy_layer] * 12
        + [
            {
                "annotations": {"buildkit/rewritten-timestamp": "1785349734"},
                "digest": layer_digest,
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": len(layer_bytes),
            }
        ],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    (blobs / manifest_digest.removeprefix("sha256:")).write_bytes(
        manifest_bytes + (b" " if variant == "manifest-bytes" else b"")
    )
    index = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": manifest_digest,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "size": len(manifest_bytes),
                "platform": {
                    "architecture": "arm64" if variant == "arm64" else "amd64",
                    "os": "linux",
                },
            }
        ],
    }
    (fixture_root / "index.json").write_text(
        json.dumps(index, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    environment = {
        **os.environ,
        "EXPECTED_PLATFORM_DIGEST": manifest_digest,
        "EXPECTED_CONFIG_DIGEST": config_digest,
        "EXPECTED_MOUNTPOINT_LAYER_DIGEST": layer_digest,
        "EXPECTED_MOUNTPOINT_LAYER_SIZE": str(len(layer_bytes)),
        "EXPECTED_MOUNTPOINT_LAYER_DIFF_ID": layer_diff_id,
        "EXPECTED_MOUNTPOINT_LAYER_ENTRY_COUNT": "4",
        "EXPECTED_MOUNTPOINT_UID": "70",
        "EXPECTED_MOUNTPOINT_GID": "70",
        "EXPECTED_MOUNTPOINT_MODE": "0700",
        "EXPECTED_MOUNTPOINT_PATH": "/var/lib/postgresql/data",
        "SOURCE_DATE_EPOCH": "1785349734",
    }
    return fixture_root, environment


def test_cd_postgres_oci_verifier_executes_the_exact_valid_workflow_program(
    tmp_path: Path,
) -> None:
    fixture_root, environment = _write_postgres_oci_verifier_fixture(tmp_path, "valid")
    completed = subprocess.run(
        [sys.executable, "-c", _postgres_oci_verifier_program(), str(fixture_root)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("variant", "message"),
    (
        ("arm64", "platform descriptor"),
        ("manifest-bytes", "manifest bytes"),
        ("extra", "path inventory"),
        ("uid", "metadata"),
        ("mode", "metadata"),
        ("mtime", "metadata"),
        ("diff-id", "diff ID"),
    ),
)
def test_cd_postgres_oci_verifier_rejects_exact_invalid_fixtures(
    tmp_path: Path,
    variant: str,
    message: str,
) -> None:
    fixture_root, environment = _write_postgres_oci_verifier_fixture(tmp_path, variant)
    completed = subprocess.run(
        [sys.executable, "-c", _postgres_oci_verifier_program(), str(fixture_root)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert message in completed.stderr


def test_prometheus_cd_security_job_cross_binds_v2_digest_and_revision() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["prometheus-image-security"]
    steps = {step["name"]: step for step in job["steps"]}

    validate_run = steps["Validate closed Prometheus image record"]["run"]
    assert '"schema": "pulseplate.prometheus_image_manifest.v2"' in validate_run
    assert f'"source_revision": "{PROMETHEUS_SOURCE_REVISION}"' in validate_run
    assert f'"index_digest": "{PROMETHEUS_INDEX_DIGEST}"' in validate_run
    assert f'"platform_manifest_digest": "{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"' in validate_run
    assert f'"runtime_ref": "{PROMETHEUS_RUNTIME_REF}"' in validate_run
    assert "f\"index_ref={manifest['repository']}@{manifest['index_digest']}\"" in validate_run
    assert "f\"{manifest['repository']}@{manifest['platform_manifest_digest']}\"" in validate_run

    cross_bind = steps["Cross-bind immutable index, linux amd64 manifest, and local image config"]
    assert cross_bind["env"] == {
        "PROMETHEUS_INDEX_REF": "${{ steps.prometheus-image.outputs.index_ref }}",
        "PROMETHEUS_INDEX_DIGEST": "${{ steps.prometheus-image.outputs.index_digest }}",
        "PROMETHEUS_PLATFORM_MANIFEST_DIGEST": (
            "${{ steps.prometheus-image.outputs.platform_manifest_digest }}"
        ),
        "PROMETHEUS_RUNTIME_REF": "${{ steps.prometheus-image.outputs.runtime_ref }}",
        "PROMETHEUS_SOURCE_REVISION": "${{ steps.prometheus-image.outputs.source_revision }}",
    }
    cross_bind_run = cross_bind["run"]
    for required in (
        'docker buildx imagetools inspect --raw "$PROMETHEUS_INDEX_REF"',
        'docker buildx imagetools inspect --raw "$PROMETHEUS_RUNTIME_REF"',
        'docker pull --platform linux/amd64 "$PROMETHEUS_RUNTIME_REF"',
        "--entrypoint /bin/prometheus",
        '--version > "$evidence_dir/version.txt" 2>&1',
        r're.findall(r"\brevision: ([0-9a-f]{40})\b", version_text)',
        "if revisions != [expected_revision]:",
        'image.get("Id") != config_digest',
    ):
        assert required in cross_bind_run
    assert "PROMETHEUS_TAG_REF" not in cross_bind_run
    assert "main-distroless" not in cross_bind_run

    scan_run = steps["Scan exact Prometheus image without suppressions"]["run"]
    for required in (
        "--scanners vuln,secret",
        "--severity CRITICAL,HIGH",
        "--exit-code 1",
        '--ignorefile "$TRIVY_IGNORE_FILE"',
        '"$PROMETHEUS_RUNTIME_REF"',
    ):
        assert required in scan_run
    assert "--ignore-unfixed" not in scan_run
    assert "continue-on-error" not in scan_run


def test_prometheus_config_has_one_private_exact_target() -> None:
    config = yaml.safe_load(PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"))
    assert config == {
        "global": {"scrape_interval": "30s", "scrape_timeout": "10s"},
        "scrape_configs": [
            {
                "job_name": "pulseplate-api",
                "scheme": "http",
                "metrics_path": "/metrics",
                "http_headers": {
                    "X-API-Key": {"files": ["/run/secrets/pulseplate_metrics_scrape_key"]}
                },
                "static_configs": [{"targets": ["app:8000"]}],
            }
        ],
    }
    config_text = PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "remote_write",
        "remote_read",
        "rule_files",
        "alerting",
        "storage.tsdb.retention",
        "web.enable-lifecycle",
        "web.enable-admin-api",
        "otlp",
    ):
        assert forbidden not in config_text


@pytest.mark.parametrize(
    "compose_path",
    (STAGING_COMPOSE_PATH, PRODUCTION_COMPOSE_PATH, SELF_HOSTED_COMPOSE_PATH),
)
def test_three_compose_contours_normalize_to_one_private_prometheus_contract(
    compose_path: Path,
) -> None:
    docker_bin = shutil.which("docker")
    assert docker_bin is not None, "docker compose is required for normalized contract validation"
    completed = subprocess.run(
        [
            docker_bin,
            "compose",
            "-f",
            str(compose_path),
            "config",
            "--no-interpolate",
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    normalized = json.loads(completed.stdout)
    services = normalized["services"]
    prometheus = services["prometheus"]

    assert normalized["networks"]["observability"]["internal"] is True
    assert set(services["app"]["networks"]) == (
        {"web", "observability", "database"}
        if compose_path == STAGING_COMPOSE_PATH
        else {"web", "observability"}
    )
    assert set(prometheus["networks"]) == {"observability"}
    assert prometheus["image"] == PROMETHEUS_RUNTIME_REF
    assert prometheus["platform"] == "linux/amd64"
    assert prometheus["user"] == "65532:65532"
    assert prometheus["restart"] == "unless-stopped"
    assert prometheus["cap_drop"] == ["ALL"]
    assert prometheus["security_opt"] == ["no-new-privileges:true"]
    assert prometheus["command"] == [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--storage.tsdb.retention.time=45d",
    ]
    assert prometheus["depends_on"] == {"app": {"condition": "service_healthy", "required": True}}
    assert prometheus["healthcheck"]["test"] == [
        "CMD",
        "/bin/promtool",
        "check",
        "ready",
        "--url=http://localhost:9090",
    ]
    assert "ports" not in prometheus

    volume_projection = {
        (item["type"], item["target"], item.get("source"), item.get("read_only", False))
        for item in prometheus["volumes"]
    }
    assert ("bind", "/etc/prometheus/prometheus.yml", str(PROMETHEUS_CONFIG_PATH), True) in (
        volume_projection
    )
    assert ("volume", "/prometheus", "prometheus_data", False) in volume_projection
    assert prometheus["secrets"] == [
        {
            "source": "pulseplate_metrics_scrape_key",
            "target": "/run/secrets/pulseplate_metrics_scrape_key",
        }
    ]
    assert prometheus["secrets"][0] in services["app"]["secrets"]
    assert "prometheus" not in services["app"].get("depends_on", {})
    for service_name in ("caddy", "worker", "postgres"):
        service = services.get(service_name)
        if isinstance(service, dict):
            assert "observability" not in service.get("networks", {})
            if compose_path != STAGING_COMPOSE_PATH or service_name == "caddy":
                assert "secrets" not in service
    assert "prometheus_data" in normalized["volumes"]


@pytest.mark.parametrize(
    "relative_path",
    (
        "deploy/PRODUCTION.md",
        "deploy/WORKFLOW.md",
        "scripts/QUICK_DIAGNOSTIC.md",
    ),
)
def test_manual_shell_sync_docs_are_merged_truth_only(relative_path: str) -> None:
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    rsync_command = "rsync -az --delete frontend/"
    rsync_indexes = [
        index for index in range(len(content)) if content.startswith(rsync_command, index)
    ]
    assert rsync_indexes, f"Expected rsync command not found in {relative_path}"

    for rsync_index in rsync_indexes:
        provenance_window = content[max(0, rsync_index - 1000) : rsync_index]
        has_git_release_truth = (
            "git fetch origin main" in provenance_window
            and "git switch --detach origin/main" in provenance_window
        )
        has_bundle_release_truth = (
            "CI-produced release bundle" in provenance_window
            or "unpacked CI-produced release bundle" in provenance_window
        )

        assert "merged" in provenance_window or "release bundle" in provenance_window
        assert has_git_release_truth or has_bundle_release_truth
        assert "dirty" in provenance_window or "unmerged" in provenance_window


def test_deploy_production_rejects_shell_bundle_without_redeploy_helper(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir, include_redeploy=False)

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh" in completed.stderr
    assert not log_file.exists()


def test_deploy_production_rejects_shell_bundle_without_reviewed_backup_helper(
    tmp_path: Path,
) -> None:
    env, _project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    (shell_bundle_dir / "scripts" / "ops" / "postgres_backup.sh").unlink()

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Incoming PostgreSQL backup helper" in completed.stderr
    assert not log_file.exists()


def test_deploy_production_preflight_rejects_shell_bundle_without_frontend(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir, include_frontend=False)

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["DATABASE_URL"] = (
        "postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate"  # pragma: allowlist secret
    )
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "SHELL_BUNDLE_DIR is missing frontend/" in completed.stderr
    assert not log_file.exists()


def _staging_compose_fixture_json(project_dir: Path = Path("/srv/pulseplate-staging")) -> str:
    from scripts.ops.check_staging_security import POSTGRES_COMMAND, STORAGE_ROOT

    payload = json.loads(FAKE_PROMETHEUS_COMPOSE_JSON)
    payload["services"]["postgres"]["environment"].update(
        {
            "POSTGRES_DB": "pulseplate",
            "POSTGRES_USER": "pulseplate",
            "POSTGRES_PASSWORD_FILE": "/run/secrets/postgres_password",
        }
    )
    local_database_url = "postgresql+psycopg://pulseplate@postgres:5432/pulseplate?sslmode=verify-full&sslrootcert=/run/secrets/postgres_ca&passfile=/run/secrets/postgres_pgpass"
    for name in ("app", "worker"):
        payload["services"][name] = {
            "environment": {
                "DATABASE_URL": local_database_url,
                "PGSSLMODE": "verify-full",
                "PGPASSFILE": "/run/secrets/postgres_pgpass",
            }
        }
    payload["services"]["postgres"]["command"] = POSTGRES_COMMAND
    payload["services"]["postgres"]["networks"] = {"database": {}}
    payload["networks"] = {"database": {"internal": True}}
    for name, directory in (("postgres_data", "postgres"), ("prometheus_data", "prometheus")):
        payload["volumes"].setdefault(name, {})
        payload["volumes"][name].update(
            {
                "driver": "local",
                "driver_opts": {
                    "type": "none",
                    "o": "bind",
                    "device": f"{STORAGE_ROOT}/{directory}",
                },
            }
        )
    payload["secrets"] = {
        name: {"file": str(project_dir / "secrets" / name)}
        for name in (
            "postgres_ca",
            "postgres_server_crt",
            "postgres_server_key",
            "postgres_password",
            "postgres_pgpass",
        )
    }
    return json.dumps(payload, separators=(",", ":"))


FAKE_STAGING_COMPOSE_JSON = _staging_compose_fixture_json()


def _write_executable(path: Path, content: str) -> None:
    if path.name == "docker":
        contract_responses = f"""case \"$*\" in
  *pg_restore\\ --list\\ --exclude-schema=public*)
    printf '%s\\n' "${{STUB_ARCHIVE_OUTSIDE_PUBLIC:-}}"
    ;;
  *pg_restore\\ --list*)
    if [ "${{STUB_PG_RESTORE_LIST_STATUS:-0}}" -ne 0 ]; then exit "${{STUB_PG_RESTORE_LIST_STATUS}}"; fi
    printf '%s\\n' "${{STUB_ARCHIVE_LIST:-214; 1259 16387 TABLE public items user}}"
    ;;
  *pg_restore\\ --file=/dev/null*)
    if [ "${{STUB_PG_RESTORE_BODY_STATUS:-0}}" -ne 0 ]; then exit "${{STUB_PG_RESTORE_BODY_STATUS}}"; fi
    cat >/dev/null
    ;;
  *pg_restore\\ --clean\\ --if-exists\\ --file=-*)
    printf '%s\\n' "${{STUB_RESTORE_SQL:-CREATE TABLE public.items(id integer);}}"
    exit "${{STUB_RESTORE_RENDER_STATUS:-0}}"
    ;;
  *psql*pg_largeobject_metadata*) printf '%s\\n' "${{STUB_TARGET_PUBLIC_ONLY:-t}}" ;;
  *psql*--single-transaction*)
    if [ -n "${{STUB_RESTORE_TRANSACTION_CALLS:-}}" ]; then printf '%s\\n' "$*" >> "$STUB_RESTORE_TRANSACTION_CALLS"; fi
    cat > "$STUB_RESTORE_TRANSACTION_SQL"
    exit "${{STUB_RESTORE_TRANSACTION_STATUS:-0}}"
    ;;
  *pg_catalog.pg_tables*) printf '1\\n' ;;
  run\\ --rm\\ --network\\ none\\ --entrypoint\\ python\\ *) printf '%s\\n' "${{STUB_BACKEND_IDS:-1000:1000}}" ;;
  *\"config --format json\"*)
    if [ \"${{STUB_COMPOSE_CONFIG_STATUS:-0}}\" -ne 0 ]; then
      exit \"${{STUB_COMPOSE_CONFIG_STATUS}}\"
    fi
    if [ -n \"${{STUB_PROMETHEUS_COMPOSE_JSON+x}}\" ]; then
      printf '%s\\n' \"$STUB_PROMETHEUS_COMPOSE_JSON\"
    else
      printf '%s\\n' '{FAKE_STAGING_COMPOSE_JSON}'
    fi
    ;;
  run\\ --rm\\ --platform\\ linux/amd64\\ --user\\ 70:70\\ *)
    if [ "${{STUB_POSTGRES_MOUNTPOINT_STATUS:-0}}" -ne 0 ]; then
      exit "${{STUB_POSTGRES_MOUNTPOINT_STATUS}}"
    fi
    ;;
  inspect\\ --format\\ *State.Running*)
    printf '%s\\n' "${{STUB_CONTAINER_RUNNING:-true}}"
    exit 0
    ;;
  inspect\\ aaaaaaaaaaaa*)
    if [ "${{STUB_POSTGRES_CONTAINER_INSPECT_STATUS:-0}}" -ne 0 ]; then
      exit "${{STUB_POSTGRES_CONTAINER_INSPECT_STATUS}}"
    fi
    if [ -n "${{STUB_POSTGRES_INSPECT_DRIFT_FILE:-}}" ] && \
       [ -f "$STUB_POSTGRES_INSPECT_DRIFT_FILE" ]; then
      printf '%s\\n' "$STUB_POSTGRES_CONTAINER_INSPECT_JSON_AFTER_FIRST"
    elif [ -n "${{STUB_POSTGRES_CONTAINER_INSPECT_JSON+x}}" ]; then
      if [ -n "${{STUB_POSTGRES_INSPECT_DRIFT_FILE:-}}" ]; then
        : > "$STUB_POSTGRES_INSPECT_DRIFT_FILE"
      fi
      printf '%s\\n' "$STUB_POSTGRES_CONTAINER_INSPECT_JSON"
    else
      printf '%s\\n' '{FAKE_POSTGRES_CONTAINER_INSPECT_JSON}'
    fi
    ;;
  exec\\ aaaaaaaaaaaa*\\ sh\\ -ec*)
    if [ "${{STUB_POSTGRES_RUNTIME_STATUS:-0}}" -ne 0 ]; then
      exit "${{STUB_POSTGRES_RUNTIME_STATUS}}"
    fi
    printf '70\\t150019\\t/var/lib/postgresql/data\\n'
    exit 0
    ;;
  exec\\ -i\\ aaaaaaaaaaaa*\\ pg_restore\\ --list*)
    cat >/dev/null
    exit "${{STUB_PG_RESTORE_LIST_STATUS:-0}}"
    ;;
  volume\\ ls\\ --quiet)
    volume_list_status="${{STUB_POSTGRES_VOLUME_LIST_STATUS:-0}}"
    volume_list_output="${{STUB_POSTGRES_VOLUME_LIST_OUTPUT:-}}"
    if [ -n "${{STUB_POSTGRES_VOLUME_LIST_COUNTER_FILE:-}}" ]; then
      volume_list_count=0
      if [ -f "$STUB_POSTGRES_VOLUME_LIST_COUNTER_FILE" ]; then
        IFS= read -r volume_list_count < "$STUB_POSTGRES_VOLUME_LIST_COUNTER_FILE"
      fi
      case "$volume_list_count" in
        ''|*[!0-9]*) exit 98 ;;
      esac
      volume_list_count=$((volume_list_count + 1))
      printf '%s\\n' "$volume_list_count" > "$STUB_POSTGRES_VOLUME_LIST_COUNTER_FILE"
      if [ "$volume_list_count" -gt 1 ]; then
        volume_list_status="${{STUB_POSTGRES_VOLUME_LIST_STATUS_AFTER_FIRST:-$volume_list_status}}"
        volume_list_output="${{STUB_POSTGRES_VOLUME_LIST_OUTPUT_AFTER_FIRST:-$volume_list_output}}"
      fi
    fi
    if [ "$volume_list_status" -ne 0 ]; then
      exit "$volume_list_status"
    fi
    printf '%s' "$volume_list_output"
    ;;
  image\\ inspect\\ *postgres-15.19-pgvector0.8.6-alpine3.23*)
    if [ "${{STUB_IMAGE_INSPECT_STATUS:-0}}" -ne 0 ]; then
      exit "${{STUB_IMAGE_INSPECT_STATUS}}"
    fi
    if [ -n "${{STUB_POSTGRES_IMAGE_INSPECT_JSON+x}}" ]; then
      printf '%s\\n' "$STUB_POSTGRES_IMAGE_INSPECT_JSON"
    else
      printf '%s\\n' '{FAKE_POSTGRES_IMAGE_INSPECT_JSON}'
    fi
    ;;
  image\\ inspect\\ *)
    if [ \"${{STUB_IMAGE_INSPECT_STATUS:-0}}\" -ne 0 ]; then
      exit \"${{STUB_IMAGE_INSPECT_STATUS}}\"
    fi
    if [ -n \"${{STUB_PROMETHEUS_IMAGE_INSPECT_JSON+x}}\" ]; then
      printf '%s\\n' \"$STUB_PROMETHEUS_IMAGE_INSPECT_JSON\"
    else
      printf '%s\\n' '{FAKE_PROMETHEUS_IMAGE_INSPECT_JSON}'
    fi
    ;;
esac
"""
        marker = "set -euo pipefail\n"
        if marker in content:
            content = content.replace(marker, marker + contract_responses, 1)
        else:
            content = content.replace("\n", "\n" + contract_responses, 1)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _assert_log_index(
    log_lines: list[str],
    *,
    predicate: Callable[[str], bool],
    message: str,
) -> int:
    index = next((position for position, line in enumerate(log_lines) if predicate(line)), None)
    assert index is not None, message
    return index


def _write_prometheus_manifest_variant(path: Path, variant: str) -> None:
    canonical = json.loads(PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"))
    if variant == "malformed":
        path.write_text("{", encoding="utf-8")
        return
    if variant == "duplicate":
        canonical_text = json.dumps(canonical, separators=(",", ":"))
        path.write_text(
            '{"schema":"pulseplate.prometheus_image_manifest.v2",' + canonical_text[1:],
            encoding="utf-8",
        )
        return
    if variant == "missing":
        canonical.pop("index_digest")
    elif variant == "extra":
        canonical["unexpected"] = "forbidden"
    elif variant == "wrong-platform-digest":
        canonical["platform_manifest_digest"] = "sha256:" + "b" * 64
    elif variant == "wrong-source-revision":
        canonical["source_revision"] = "A" * 40
    elif variant == "wrong-runtime-ref":
        canonical["runtime_ref"] = (
            "prom/prometheus:main-distroless@" + PROMETHEUS_PLATFORM_MANIFEST_DIGEST
        )
    elif variant == "index-digest-runtime-ref":
        canonical["runtime_ref"] = f"prom/prometheus@{PROMETHEUS_INDEX_DIGEST}"
    elif variant == "wrong-type":
        canonical["source_revision"] = 314
    else:
        raise AssertionError(f"unsupported manifest variant: {variant}")
    path.write_text(json.dumps(canonical), encoding="utf-8")


def _write_postgres_manifest_variant(path: Path, variant: str) -> None:
    canonical = json.loads(POSTGRES_MANIFEST_PATH.read_text(encoding="utf-8"))
    if variant == "malformed":
        path.write_text("{", encoding="utf-8")
        return
    if variant == "duplicate":
        canonical_text = json.dumps(canonical, separators=(",", ":"))
        path.write_text(
            '{"schema":"pulseplate.postgres_pgvector_image_manifest.v1",' + canonical_text[1:],
            encoding="utf-8",
        )
        return
    if variant == "missing":
        canonical.pop("runtime_base_platform_manifest_digest")
    elif variant == "extra":
        canonical["unexpected"] = "forbidden"
    elif variant == "wrong-platform-digest":
        canonical["platform_manifest_digest"] = "sha256:" + "b" * 64
    elif variant == "wrong-runtime-ref":
        canonical["runtime_ref"] = canonical["runtime_ref"].replace("ca0968c5", "ba0968c5")
    elif variant == "wrong-type":
        canonical["postgres_major"] = 15
    else:
        raise AssertionError(f"unsupported PostgreSQL manifest variant: {variant}")
    path.write_text(json.dumps(canonical), encoding="utf-8")


def _production_preflight_fixture(
    tmp_path: Path,
    *,
    with_bundle: bool,
) -> tuple[dict[str, str], Path, Path, Path | None]:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle" if with_bundle else None
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir, compose_text=PRODUCTION_COMPOSE_TEXT)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    if shell_bundle_dir is not None:
        shell_bundle_dir.mkdir()
        _write_shell_bundle_contract(shell_bundle_dir)
        (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
            "bounded-frontend\n", encoding="utf-8"
        )
    _write_executable(
        bin_dir / "docker",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\\nworker\\ncaddy\\nprometheus\\n' ;;
esac
""",
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")
    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
        }
    )
    if shell_bundle_dir is not None:
        env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)
    return env, project_dir, log_file, shell_bundle_dir


@pytest.mark.parametrize(
    "variant",
    (
        "malformed",
        "duplicate",
        "missing",
        "extra",
        "wrong-platform-digest",
        "wrong-source-revision",
        "wrong-runtime-ref",
        "index-digest-runtime-ref",
        "wrong-type",
    ),
)
def test_staging_deploy_rejects_noncanonical_prometheus_manifest_before_docker(
    tmp_path: Path,
    variant: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    manifest_path = Path(env["PROJECT_DIR"]) / "prometheus" / "image-manifest.json"
    _write_prometheus_manifest_variant(manifest_path, variant)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Prometheus manifest" in completed.stderr
    assert not log_file.exists()


@pytest.mark.parametrize(
    "variant",
    (
        "malformed",
        "duplicate",
        "missing",
        "extra",
        "wrong-platform-digest",
        "wrong-runtime-ref",
        "wrong-type",
    ),
)
def test_staging_deploy_rejects_noncanonical_postgres_manifest_before_docker(
    tmp_path: Path,
    variant: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    manifest_path = Path(env["PROJECT_DIR"]) / "postgres-pgvector" / "image-manifest.json"
    _write_postgres_manifest_variant(manifest_path, variant)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "PostgreSQL image manifest" in completed.stderr
    assert not log_file.exists()


@pytest.mark.parametrize(
    "variant",
    (
        "malformed",
        "duplicate",
        "missing",
        "extra",
        "wrong-platform-digest",
        "wrong-runtime-ref",
        "wrong-type",
    ),
)
def test_production_deploy_rejects_noncanonical_prometheus_manifest_before_docker(
    tmp_path: Path,
    variant: str,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    _write_prometheus_manifest_variant(
        project_dir / "deploy" / "prometheus" / "image-manifest.json",
        variant,
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Prometheus manifest" in completed.stderr
    assert not log_file.exists()


@pytest.mark.parametrize(
    "rendered_compose",
    (
        "{",
        "{}",
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": "prom/prometheus:latest",
                        "platform": "linux/amd64",
                    }
                }
            }
        ),
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": PROMETHEUS_RUNTIME_REF,
                        "platform": "linux/arm64",
                    }
                }
            }
        ),
    ),
)
def test_staging_deploy_rejects_rendered_prometheus_identity_drift_before_pull(
    tmp_path: Path,
    rendered_compose: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_PROMETHEUS_COMPOSE_JSON"] = rendered_compose
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("config --format json" in line for line in log_lines)
    assert all(
        " login " not in line and " pull " not in line and " up " not in line for line in log_lines
    )


@pytest.mark.parametrize(
    "variant",
    (
        "missing",
        "wrong-image",
        "wrong-platform",
        "wrong-pgdata",
        "wrong-volume",
        "ports",
        "missing-app",
        "missing-worker",
        "app-external-dsn",
        "worker-dsn-drift",
    ),
)
def test_staging_deploy_rejects_rendered_postgres_identity_drift_before_pull(
    tmp_path: Path,
    variant: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    rendered = json.loads(FAKE_STAGING_COMPOSE_JSON)
    postgres = rendered["services"]["postgres"]
    if variant == "missing":
        del rendered["services"]["postgres"]
    elif variant == "wrong-image":
        postgres["image"] = "postgres:15-alpine"
    elif variant == "wrong-platform":
        postgres["platform"] = "linux/arm64"
    elif variant == "wrong-pgdata":
        postgres["environment"]["PGDATA"] = "/var/lib/postgresql/15/data"
    elif variant == "wrong-volume":
        postgres["volumes"][0]["target"] = "/var/lib/postgresql/15/data"
    elif variant == "ports":
        postgres["ports"] = [{"target": 5432, "published": "5432"}]
    elif variant == "missing-app":
        del rendered["services"]["app"]
    elif variant == "missing-worker":
        del rendered["services"]["worker"]
    elif variant == "app-external-dsn":
        rendered["services"]["app"]["environment"][
            "DATABASE_URL"
        ] = "postgresql+psycopg://pulseplate:test-only@db.example.com/pulseplate"  # pragma: allowlist secret
    elif variant == "worker-dsn-drift":
        rendered["services"]["worker"]["environment"][
            "DATABASE_URL"
        ] = "postgresql+psycopg://pulseplate:test-only@postgres/other"  # pragma: allowlist secret
    else:
        raise AssertionError(f"unsupported rendered PostgreSQL variant: {variant}")
    env["STUB_PROMETHEUS_COMPOSE_JSON"] = json.dumps(rendered)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    expected_surface = (
        "app"
        if variant in ("missing-app", "app-external-dsn")
        else ("worker" if variant in ("missing-worker", "worker-dsn-drift") else "PostgreSQL")
    )
    assert expected_surface in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("config --format json" in line for line in log_lines)
    assert all(
        " login " not in line and " pull " not in line and " up " not in line for line in log_lines
    )


@pytest.mark.parametrize(
    "rendered_compose",
    (
        "{",
        "{}",
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": "prom/prometheus:latest",
                        "platform": "linux/amd64",
                    }
                }
            }
        ),
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": PROMETHEUS_RUNTIME_REF,
                        "platform": "linux/arm64",
                    }
                }
            }
        ),
    ),
)
def test_production_deploy_rejects_rendered_prometheus_identity_drift_before_pull(
    tmp_path: Path,
    rendered_compose: str,
) -> None:
    env, _project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    env["STUB_PROMETHEUS_COMPOSE_JSON"] = rendered_compose

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("config --format json" in line for line in log_lines)
    assert all(
        " login " not in line and " pull " not in line and " up " not in line for line in log_lines
    )


IMAGE_INSPECT_REJECTIONS = (
    "{",
    "[]",
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            },
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            },
        ]
    ),
    json.dumps(
        [
            {
                "Os": "windows",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            }
        ]
    ),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "arm64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            }
        ]
    ),
    json.dumps([{"Os": "linux", "Architecture": "amd64", "RepoDigests": []}]),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_INDEX_DIGEST}"],
            }
        ]
    ),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [
                    f"example.invalid/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"
                ],
            }
        ]
    ),
)


def _postgres_image_inspect_variant(variant: str) -> str:
    payload = json.loads(FAKE_POSTGRES_IMAGE_INSPECT_JSON)
    record = payload[0]
    config = record["Config"]
    if variant == "wrong-platform":
        record["Architecture"] = "arm64"
    elif variant == "wrong-user":
        config["User"] = "0"
    elif variant == "wrong-entrypoint":
        config["Entrypoint"] = ["/bin/sh"]
    elif variant == "wrong-environment":
        config["Env"] = ["PGDATA=/var/lib/postgresql/data", "PG_MAJOR=15", "PG_MINOR=19"]
    elif variant == "wrong-label":
        config["Labels"]["com.pulseplate.pgvector.version"] = "0.8.5"
    elif variant == "wrong-repository-digest":
        record["RepoDigests"] = [f"example.invalid/pulseplate@{POSTGRES_PLATFORM_MANIFEST_DIGEST}"]
    else:
        raise AssertionError(f"unsupported pulled PostgreSQL variant: {variant}")
    return json.dumps(payload)


POSTGRES_IMAGE_INSPECT_REJECTIONS = (
    "{",
    "[]",
    *(
        _postgres_image_inspect_variant(variant)
        for variant in (
            "wrong-platform",
            "wrong-user",
            "wrong-entrypoint",
            "wrong-environment",
            "wrong-label",
            "wrong-repository-digest",
        )
    ),
)


@pytest.mark.parametrize("inspect_payload", IMAGE_INSPECT_REJECTIONS)
def test_staging_deploy_rejects_pulled_prometheus_identity_before_product_mutation(
    tmp_path: Path,
    inspect_payload: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_PROMETHEUS_IMAGE_INSPECT_JSON"] = inspect_payload
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" pull app caddy postgres prometheus" in line for line in log_lines)
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


@pytest.mark.parametrize("inspect_payload", POSTGRES_IMAGE_INSPECT_REJECTIONS)
def test_staging_deploy_rejects_pulled_postgres_identity_before_product_mutation(
    tmp_path: Path,
    inspect_payload: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_POSTGRES_IMAGE_INSPECT_JSON"] = inspect_payload
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "PostgreSQL image" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" pull app caddy postgres prometheus" in line for line in log_lines)
    assert sum("image inspect" in line for line in log_lines) >= 2
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


def test_staging_deploy_rejects_postgres_mountpoint_drift_before_product_mutation(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_POSTGRES_MOUNTPOINT_STATUS"] = "17"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 17
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert sum("image inspect" in line for line in log_lines) >= 2
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


@pytest.mark.parametrize("inspect_payload", IMAGE_INSPECT_REJECTIONS)
def test_production_deploy_rejects_pulled_prometheus_identity_before_product_mutation(
    tmp_path: Path,
    inspect_payload: str,
) -> None:
    env, _project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "STUB_PROMETHEUS_IMAGE_INSPECT_JSON": inspect_payload,
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" pull prometheus" in line for line in log_lines)
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


def test_production_env_cannot_override_manifest_derived_prometheus_digest(
    tmp_path: Path,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    conflicting_digest = "sha256:" + "b" * 64
    with (project_dir / ".env").open("a", encoding="utf-8") as env_file:
        env_file.write(f"PROMETHEUS_PLATFORM_MANIFEST_DIGEST={conflicting_digest}\n")
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "STUB_PROMETHEUS_IMAGE_INSPECT_JSON": json.dumps(
                [
                    {
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RepoDigests": [f"prom/prometheus@{conflicting_digest}"],
                    }
                ]
            ),
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "canonical platform digest" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)


@pytest.mark.parametrize(
    "destination_variant",
    (
        "frontend-directory-symlink",
        "caddy-leaf-symlink",
        "scripts-directory-symlink",
        "redeploy-leaf-symlink",
        "ops-directory-symlink",
        "backup-helper-leaf-symlink",
        "backup-helper-leaf-hardlink",
    ),
)
def test_production_full_bundle_rejects_hostile_destination_before_docker(
    tmp_path: Path,
    destination_variant: str,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    external = tmp_path / f"external-{destination_variant}"
    if destination_variant == "frontend-directory-symlink":
        external.mkdir()
        (external / "sentinel").write_text("external-frontend\n", encoding="utf-8")
        hostile = project_dir / "frontend"
        hostile.symlink_to(external, target_is_directory=True)
        expected = (external / "sentinel").read_bytes()
    elif destination_variant == "caddy-leaf-symlink":
        external.write_text("external-caddy\n", encoding="utf-8")
        hostile = project_dir / "deploy" / "Caddyfile.production"
        hostile.symlink_to(external)
        expected = external.read_bytes()
    elif destination_variant == "scripts-directory-symlink":
        external.mkdir()
        (external / "sentinel").write_text("external-scripts\n", encoding="utf-8")
        hostile = project_dir / "scripts"
        hostile.symlink_to(external, target_is_directory=True)
        expected = (external / "sentinel").read_bytes()
    elif destination_variant == "redeploy-leaf-symlink":
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir()
        external.write_text("external-helper\n", encoding="utf-8")
        hostile = scripts_dir / "redeploy_caddy.sh"
        hostile.symlink_to(external)
        expected = external.read_bytes()
    elif destination_variant == "ops-directory-symlink":
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir()
        external.mkdir()
        (external / "sentinel").write_text("external-ops\n", encoding="utf-8")
        hostile = scripts_dir / "ops"
        hostile.symlink_to(external, target_is_directory=True)
        expected = (external / "sentinel").read_bytes()
    else:
        ops_dir = project_dir / "scripts" / "ops"
        ops_dir.mkdir(parents=True)
        external.write_text("external-backup-helper\n", encoding="utf-8")
        hostile = ops_dir / "postgres_backup.sh"
        if destination_variant == "backup-helper-leaf-symlink":
            hostile.symlink_to(external)
        else:
            os.link(external, hostile)
        expected = external.read_bytes()

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    if destination_variant == "backup-helper-leaf-hardlink":
        assert not hostile.is_symlink()
        assert hostile.stat().st_nlink == 2
    else:
        assert hostile.is_symlink()
    assert not log_file.exists()
    if external.is_dir():
        assert (external / "sentinel").read_bytes() == expected
    else:
        assert external.read_bytes() == expected
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []


@pytest.mark.parametrize(
    "source_variant",
    (
        "bundle-parent-symlink",
        "frontend-nested-symlink",
        "frontend-nested-hardlink",
        "caddy-source-symlink",
        "redeploy-source-symlink",
        "backup-source-symlink",
        "backup-source-hardlink",
        "backup-source-nonexec",
        "backup-source-writable",
    ),
)
def test_production_full_bundle_rejects_hostile_source_before_runtime_mutation(
    tmp_path: Path,
    source_variant: str,
) -> None:
    env, project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    external = tmp_path / f"external-{source_variant}"
    if source_variant == "bundle-parent-symlink":
        real_bundle = tmp_path / "real-shell-bundle"
        shell_bundle_dir.rename(real_bundle)
        shell_bundle_dir.symlink_to(real_bundle, target_is_directory=True)
        expected_path = real_bundle / "frontend" / "bundle-marker.txt"
    elif source_variant == "frontend-nested-symlink":
        external.write_text("external-frontend\n", encoding="utf-8")
        (shell_bundle_dir / "frontend" / "hostile-link").symlink_to(external)
        expected_path = external
    elif source_variant == "frontend-nested-hardlink":
        external.write_text("external-hardlink\n", encoding="utf-8")
        os.link(external, shell_bundle_dir / "frontend" / "hostile-hardlink")
        expected_path = external
    elif source_variant == "caddy-source-symlink":
        caddy = shell_bundle_dir / "deploy" / "Caddyfile.production"
        caddy.rename(external)
        caddy.symlink_to(external)
        expected_path = external
    elif source_variant == "redeploy-source-symlink":
        redeploy = shell_bundle_dir / "scripts" / "redeploy_caddy.sh"
        redeploy.rename(external)
        redeploy.symlink_to(external)
        expected_path = external
    else:
        backup_helper = shell_bundle_dir / "scripts" / "ops" / "postgres_backup.sh"
        if source_variant == "backup-source-symlink":
            backup_helper.rename(external)
            backup_helper.symlink_to(external)
            expected_path = external
        elif source_variant == "backup-source-hardlink":
            backup_helper.unlink()
            external.write_text("hardlinked-backup-helper\n", encoding="utf-8")
            os.link(external, backup_helper)
            expected_path = external
        else:
            backup_helper.chmod(0o644 if source_variant == "backup-source-nonexec" else 0o775)
            expected_path = backup_helper
    expected = expected_path.read_bytes()

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert expected_path.read_bytes() == expected
    if log_file.exists():
        log_lines = log_file.read_text(encoding="utf-8").splitlines()
        assert all(
            " login " not in line
            and " pull " not in line
            and " stop " not in line
            and " up " not in line
            for line in log_lines
        )
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []


@pytest.mark.parametrize(
    ("variant", "suffix", "expected_returncode"),
    (
        ("valid", 1, 0),
        ("valid-selfhosted", 17, 0),
        ("traversal", 2, 1),
        ("absolute", 3, 1),
        ("non_normalized", 4, 1),
        ("duplicate", 5, 1),
        ("symlink", 6, 1),
        ("hardlink", 7, 1),
        ("fifo", 8, 1),
        ("unexpected", 9, 1),
        ("missing_manifest", 10, 1),
        ("oversized_archive", 11, 1),
        ("backup_helper_missing", 13, 1),
        ("backup_helper_symlink", 14, 1),
        ("backup_helper_hardlink", 15, 1),
        ("backup_helper_wrong_mode", 16, 1),
    ),
)
def test_production_archive_preflight_is_bounded_and_extracts_nothing(
    tmp_path: Path,
    variant: str,
    suffix: int,
    expected_returncode: int,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    self_hosted = variant == "valid-selfhosted"
    selected_compose_text = (
        SELF_HOSTED_COMPOSE_PATH.read_text(encoding="utf-8")
        if self_hosted
        else PRODUCTION_COMPOSE_TEXT
    )
    selected_compose_name = (
        "docker-compose.production.selfhosted.yaml"
        if self_hosted
        else "docker-compose.production.yaml"
    )
    _write_production_host_contract(
        project_dir,
        compose_text=selected_compose_text,
        self_hosted=self_hosted,
    )
    _write_shell_bundle_contract(
        shell_bundle_dir,
        compose_text=selected_compose_text,
        compose_name=selected_compose_name,
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    archive_path = _canonical_test_archive_path(suffix)
    _write_shell_bundle_archive(archive_path, shell_bundle_dir, variant=variant)
    service_list = (
        "app\\ncaddy\\npostgres\\nprometheus\\nworker\\n"
        if self_hosted
        else "app\\ncaddy\\nprometheus\\nworker\\n"
    )
    _write_executable(
        bin_dir / "docker",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf '{service_list}' ;;
esac
""",
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": (
                CANONICAL_SELF_HOSTED_COMPOSE if self_hosted else CANONICAL_MANAGED_COMPOSE
            ),
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_ARCHIVE": str(archive_path),
        }
    )
    if self_hosted:
        env.update(
            {
                "PROD_DEPLOY_MODE": "self-hosted",
                "POSTGRES_DB": "pulseplate",
                "POSTGRES_USER": "pulseplate",
                "POSTGRES_PASSWORD": "test-only",  # pragma: allowlist secret
            }
        )
    try:
        completed = subprocess.run(
            [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == expected_returncode, completed.stderr
        assert not (project_dir / "frontend").exists()
        if expected_returncode == 0:
            assert log_file.is_file()
            assert "Production deploy preflight passed" in completed.stdout
        else:
            assert not log_file.exists()
            assert "archive" in completed.stderr.lower()
    finally:
        if archive_path.exists():
            archive_path.unlink()


@pytest.mark.parametrize(
    "destination_variant",
    (
        "compose-leaf-symlink",
        "prometheus-directory-symlink",
        "config-leaf-symlink",
        "manifest-leaf-symlink",
    ),
)
def test_production_contract_publication_rejects_destination_symlinks_before_docker(
    tmp_path: Path,
    destination_variant: str,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    _write_shell_bundle_contract(shell_bundle_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    deploy_dir = project_dir / "deploy"
    compose_path = deploy_dir / "docker-compose.production.yaml"
    prometheus_dir = deploy_dir / "prometheus"
    config_path = prometheus_dir / "prometheus.yml"
    manifest_path = prometheus_dir / "image-manifest.json"
    external_referent = tmp_path / f"external-{destination_variant}"
    expected_external_files: dict[str, bytes] = {}

    if destination_variant == "compose-leaf-symlink":
        compose_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        compose_path.symlink_to(external_referent)
        symlink_path = compose_path
    elif destination_variant == "prometheus-directory-symlink":
        prometheus_dir.rename(external_referent)
        expected_external_files["prometheus.yml"] = (
            external_referent / "prometheus.yml"
        ).read_bytes()
        expected_external_files["image-manifest.json"] = (
            external_referent / "image-manifest.json"
        ).read_bytes()
        prometheus_dir.symlink_to(external_referent, target_is_directory=True)
        symlink_path = prometheus_dir
    elif destination_variant == "config-leaf-symlink":
        config_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        config_path.symlink_to(external_referent)
        symlink_path = config_path
    else:
        manifest_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        manifest_path.symlink_to(external_referent)
        symlink_path = manifest_path

    _write_executable(
        bin_dir / "docker",
        f'#!/usr/bin/env bash\nprintf \'docker %s\\n\' "$*" >> "{log_file}"\n',
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")
    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_DIR": str(shell_bundle_dir),
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "destination" in completed.stderr or "Prometheus contract directory" in completed.stderr
    assert symlink_path.is_symlink()
    assert not log_file.exists()
    if external_referent.is_dir():
        for name, expected_bytes in expected_external_files.items():
            assert (external_referent / name).read_bytes() == expected_bytes
    else:
        assert external_referent.read_bytes() == expected_external_files[external_referent.name]
    assert list(deploy_dir.rglob(".pulseplate-*.tmp-*")) == []


def test_production_archive_full_deploy_preserves_server_local_state_and_orders_prometheus_last(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "archive-shell\n", encoding="utf-8"
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    evidence_file = project_dir / "evidence" / "receipt.json"
    backup_file = project_dir / "backups" / "backup.dump"
    tsdb_sentinel = project_dir / "prometheus_data" / "sentinel"
    for path, value in (
        (evidence_file, "evidence\n"),
        (backup_file, "backup\n"),
        (tsdb_sentinel, "tsdb\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    secret_file = project_dir / "deploy" / "secrets" / "pulseplate_metrics_scrape_key"
    original_secret = secret_file.read_bytes()

    archive_path = _canonical_test_archive_path(12)
    _write_shell_bundle_archive(archive_path, shell_bundle_dir)
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*) printf 'app-id\n' ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_ARCHIVE": str(archive_path),
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert METRICS_SECRET_SENTINEL not in completed.stdout
    assert METRICS_SECRET_SENTINEL not in completed.stderr
    assert not archive_path.exists()
    assert secret_file.read_bytes() == original_secret
    assert evidence_file.read_text(encoding="utf-8") == "evidence\n"
    assert backup_file.read_text(encoding="utf-8") == "backup\n"
    assert tsdb_sentinel.read_text(encoding="utf-8") == "tsdb\n"
    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "archive-shell\n"
    published_backup_helper = project_dir / "scripts" / "ops" / "postgres_backup.sh"
    assert (
        published_backup_helper.read_bytes()
        == (shell_bundle_dir / "scripts" / "ops" / "postgres_backup.sh").read_bytes()
    )
    assert stat.S_IMODE(published_backup_helper.stat().st_mode) == 0o755

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all(METRICS_SECRET_SENTINEL not in line for line in log_lines)
    prometheus_pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: " pull prometheus" in line,
        message="exact Prometheus pull missing",
    )
    image_inspect_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("docker image inspect "),
        message="pulled Prometheus identity validation missing",
    )
    promtool_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "promtool prometheus" in line,
        message="Prometheus config validation missing",
    )
    guard_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "assert_production_runtime_invariants(app=app)" in line,
        message="canonical app.main production invariant was not invoked",
    )
    migration_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "app alembic upgrade head" in line,
        message="migration command missing",
    )
    caddy_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "up -d --remove-orphans caddy" in line,
        message="Caddy start missing",
    )
    prometheus_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "up -d --pull never prometheus" in line,
        message="Prometheus start missing",
    )
    assert (
        prometheus_pull_index
        < image_inspect_index
        < promtool_index
        < guard_index
        < migration_index
        < caddy_index
        < prometheus_index
    )
    for forbidden in ("down -v", "volume rm", "volume prune", "prometheus_data rm"):
        assert all(forbidden not in line for line in log_lines)


def test_production_prometheus_failure_is_nonzero_after_product_and_preserves_state(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    tsdb_sentinel = project_dir / "prometheus_data" / "sentinel"
    tsdb_sentinel.parent.mkdir()
    tsdb_sentinel.write_text("preserve\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*) printf 'app-id\n' ;;
  *"up -d --pull never prometheus"*) exit 47 ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 47
    assert "Prometheus failed to start; app and Caddy remain running" in completed.stderr
    assert tsdb_sentinel.read_text(encoding="utf-8") == "preserve\n"
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    app_index = next(
        index for index, line in enumerate(log_lines) if "up -d --remove-orphans app" in line
    )
    caddy_index = next(
        index for index, line in enumerate(log_lines) if "up -d --remove-orphans caddy" in line
    )
    prometheus_index = next(
        index for index, line in enumerate(log_lines) if "up -d --pull never prometheus" in line
    )
    assert app_index < caddy_index < prometheus_index
    for forbidden in ("down", "volume rm", "volume prune", "stop app", "stop caddy"):
        assert all(forbidden not in line for line in log_lines[prometheus_index + 1 :])


def test_postgres_backup_helper_passes_project_dir_and_compose_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    backup_dir = project_dir / "backups"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_dir.mkdir()
    env_file = project_dir / "config" / "selected.env"
    env_file.parent.mkdir()
    env_file.write_text("POSTGRES_DB=pulseplate\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{log_file}"
cat <<'EOF'
FAKE_BACKUP
EOF
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_stage_native_oracles(project_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"  # pragma: allowlist secret
    env["PROJECT_DIR"] = str(project_dir)
    env["BACKUP_DIR"] = str(backup_dir)
    env["COMPOSE_FILE"] = "docker-compose.staging.yaml"
    env["ENV_FILE"] = str(env_file)
    env["POSTGRES_USER"] = "pulseplate"
    env["POSTGRES_DB"] = "pulseplate"
    env["PYTHON_BIN"] = sys.executable
    env["PYTHONPATH"] = str(REPO_ROOT)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Backup created:" in completed.stdout
    docker_call = log_file.read_text(encoding="utf-8")
    assert f"compose --env-file {env_file} --project-directory {project_dir}" in docker_call
    assert f"-f {project_dir / 'docker-compose.staging.yaml'}" in docker_call
    assert "exec -T postgres pg_dump -U pulseplate -d pulseplate -Fc" in docker_call
    backup_files = list(backup_dir.glob("pulseplate_*.dump"))
    assert len(backup_files) == 1
    assert backup_files[0].read_text(encoding="utf-8").strip() == "FAKE_BACKUP"
    assert stat.S_IMODE(backup_files[0].stat().st_mode) == 0o600


def test_postgres_backup_helper_uses_container_database_identity_when_host_env_is_absent(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    backup_dir = project_dir / "backups"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "{log_file}"
printf 'FAKE_BACKUP\n'
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_stage_native_oracles(project_dir)

    env = os.environ.copy()
    env.pop("POSTGRES_USER", None)
    env.pop("POSTGRES_DB", None)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["PROJECT_DIR"] = str(project_dir)
    env["BACKUP_DIR"] = str(backup_dir)
    env["COMPOSE_FILE"] = "docker-compose.staging.yaml"
    env["PYTHON_BIN"] = sys.executable
    env["PYTHONPATH"] = str(REPO_ROOT)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Backup created:" in completed.stdout
    docker_call = log_file.read_text(encoding="utf-8")
    assert "exec -T postgres sh -euc" in docker_call
    assert 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' in docker_call
    backup_files = list(backup_dir.glob("pulseplate_*.dump"))
    assert len(backup_files) == 1
    assert backup_files[0].read_text(encoding="utf-8").strip() == "FAKE_BACKUP"


def test_postgres_restore_helper_passes_project_dir_and_compose_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    backup_file = tmp_path / "pulseplate.dump"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_file.write_text("FAKE_RESTORE", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{log_file}"
if printf '%s\\n' "$*" | grep -q 'pg_restore'; then
  cat >/dev/null
fi
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["PROJECT_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["POSTGRES_USER"] = "pulseplate"
    env["POSTGRES_DB"] = "pulseplate"

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/ops/postgres_restore.sh"),
            "--verify-into",
            "pulseplate_restore_check_fixture",
            str(backup_file),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Restore completed into: pulseplate_restore_check_fixture" in completed.stdout
    docker_calls = log_file.read_text(encoding="utf-8").splitlines()
    assert len(docker_calls) == 5
    assert all(f"compose --project-directory {project_dir}" in call for call in docker_calls)
    assert all(
        f"-f {project_dir / 'docker-compose.production.yaml'}" in call for call in docker_calls
    )
    assert "pg_restore --list" in docker_calls[0]
    assert "pg_restore --file=/dev/null" in docker_calls[1]
    assert (
        "createdb -U pulseplate --maintenance-db pulseplate --owner pulseplate" in docker_calls[2]
    )
    assert (
        "pg_restore -U pulseplate -d pulseplate_restore_check_fixture --exit-on-error --single-transaction --clean --if-exists"
        in docker_calls[3]
    )
    assert all("DROP SCHEMA" not in call for call in docker_calls)


def test_deploy_production_runs_migrations_before_caddy_and_external_ready(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    migrate_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "run --rm --no-deps app alembic upgrade head" in line,
        message="Expected one-shot alembic migration step to appear in deploy log",
    )
    app_up_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "up -d --remove-orphans app" in line,
        message="Expected app docker compose up step to appear in deploy log",
    )
    caddy_build_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line and "build caddy" in line,
        message="Expected caddy docker compose build step to appear in deploy log",
    )
    caddy_up_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "up -d --remove-orphans caddy" in line,
        message="Expected caddy docker compose up step to appear in deploy log",
    )
    external_ready_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("curl ") and "https://pulseplate.test/ready" in line,
        message="Expected external readiness check to appear in deploy log",
    )

    assert migrate_index < app_up_index < caddy_build_index < caddy_up_index < external_ready_index
    assert all("up -d --remove-orphans postgres" not in line for line in log_lines)
    assert all("helper " not in line for line in log_lines)


def test_deploy_production_preflight_only_exits_non_zero_when_default_env_file_is_missing(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert f"Missing production env file: {project_dir / 'deploy' / '.env'}" in completed.stderr
    assert "GitHub Actions does not provision it." in completed.stderr
    assert "See deploy/PRODUCTION.md for the canonical bootstrap contract." in completed.stderr
    # RU: Неуспешный --preflight-only запуск не должен создавать deploy log.
    # EN: A failed --preflight-only run must not create a deploy log.
    assert not log_file.exists()


def test_deploy_production_fails_fast_when_resolved_compose_file_is_missing(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "deploy").mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "RESOLVED_COMPOSE_FILE does not exist: deploy/docker-compose.production.yaml" in (
        completed.stderr
    )
    assert not log_file.exists()


def test_deploy_production_logs_in_to_ghcr_with_resolved_docker_binary(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    docker_home = tmp_path / "docker-home"
    docker_dir = docker_home / "bin"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    docker_dir.mkdir(parents=True)
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "GHCR_USER=stale-env-user",
                "GHCR_TOKEN=stale-env-token",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  "login ghcr.io -u deploy-bot --password-stdin")
    cat >/dev/null
    ;;
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(docker_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(docker_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["GHCR_USER"] = "deploy-bot"
    env["GHCR_TOKEN"] = "read-token"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    login_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line == "docker login ghcr.io -u deploy-bot --password-stdin",
        message="Expected deploy script to log in to GHCR via resolved docker binary",
    )
    pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line and "pull app" in line,
        message="Expected deploy script to pull the production app image",
    )

    assert login_index < pull_index
    assert all("stale-env-user" not in line for line in log_lines)
    assert all("stale-env-token" not in line for line in log_lines)


def test_deploy_production_syncs_shell_bundle_and_prunes_stale_shell_files(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "outside-sentinel.txt").write_text(
        "outside-shell\n", encoding="utf-8"
    )
    (project_dir / "frontend").mkdir()
    (project_dir / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")
    destination_ops_dir = project_dir / "scripts" / "ops"
    destination_ops_dir.mkdir()
    stale_backup_helper = destination_ops_dir / "postgres_backup.sh"
    stale_backup_helper.write_text(
        "#!/usr/bin/env bash\nprintf 'stale-backup-helper\\n'\n",
        encoding="utf-8",
    )
    stale_backup_helper.chmod(0o755)
    source_backup_helper = shell_bundle_dir / "scripts" / "ops" / "postgres_backup.sh"
    reviewed_backup_helper = source_backup_helper.read_bytes()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "frontend-sync\n"
    assert (
        (project_dir / "deploy" / "Caddyfile.production")
        .read_text(encoding="utf-8")
        .startswith("pulseplate.test")
    )
    assert not (project_dir / "Caddyfile.production").exists()
    assert (shell_root / "frontend" / "outside-sentinel.txt").read_text(
        encoding="utf-8"
    ) == "outside-shell\n"
    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT
    published_config = project_dir / "deploy" / "prometheus" / "prometheus.yml"
    published_manifest = project_dir / "deploy" / "prometheus" / "image-manifest.json"
    published_postgres_manifest = (
        project_dir / "deploy" / "postgres-pgvector" / "image-manifest.json"
    )
    assert published_config.read_text(encoding="utf-8") == PROMETHEUS_CONFIG_PATH.read_text(
        encoding="utf-8"
    )
    assert published_manifest.read_text(encoding="utf-8") == PROMETHEUS_MANIFEST_PATH.read_text(
        encoding="utf-8"
    )
    assert published_postgres_manifest.read_text(
        encoding="utf-8"
    ) == POSTGRES_MANIFEST_PATH.read_text(encoding="utf-8")
    for published_path in (
        project_dir / "deploy" / "docker-compose.production.yaml",
        published_config,
        published_manifest,
        published_postgres_manifest,
        project_dir / "deploy" / "Caddyfile.production",
        project_dir / "frontend" / "bundle-marker.txt",
    ):
        assert stat.S_IMODE(published_path.stat().st_mode) == 0o644
    for helper_path in (
        project_dir / "scripts" / "diagnose_web.sh",
        project_dir / "scripts" / "redeploy_caddy.sh",
        stale_backup_helper,
    ):
        assert stat.S_IMODE(helper_path.stat().st_mode) == 0o755
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []
    assert not (project_dir / "frontend" / "stale.txt").exists()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"
    assert stale_backup_helper.read_bytes() == reviewed_backup_helper
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all("pg_dump" not in line for line in log_lines)


def test_production_contract_publication_failure_preserves_previous_backup_helper(
    tmp_path: Path,
) -> None:
    env, project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    destination_ops_dir = project_dir / "scripts" / "ops"
    destination_ops_dir.mkdir(parents=True)
    destination_backup_helper = destination_ops_dir / "postgres_backup.sh"
    previous_helper = b"#!/usr/bin/env bash\nprintf 'previous-helper\\n'\n"
    destination_backup_helper.write_bytes(previous_helper)
    destination_backup_helper.chmod(0o755)

    source_config = shell_bundle_dir / "deploy" / "prometheus" / "prometheus.yml"
    oversized_config = tmp_path / "oversized-prometheus.yml"
    oversized_config.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    move_bin = shutil.which("mv")
    assert move_bin is not None
    docker_bin = Path(env["DOCKER_BIN"])
    _write_executable(
        docker_bin,
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"login ghcr.io"*)
    "$STUB_MV_BIN" "$STUB_OVERSIZED_CONFIG" "$STUB_SOURCE_CONFIG"
    ;;
  *"config --services"*) printf 'app\nworker\ncaddy\nprometheus\n' ;;
esac
""",
    )
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "GHCR_USER": "bundle-test",
            "GHCR_TOKEN": "test-only-token",  # pragma: allowlist secret
            "STUB_MV_BIN": move_bin,
            "STUB_OVERSIZED_CONFIG": str(oversized_config),
            "STUB_SOURCE_CONFIG": str(source_config),
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "source must be one bounded regular file" in completed.stderr
    assert destination_backup_helper.read_bytes() == previous_helper
    assert stat.S_IMODE(destination_backup_helper.stat().st_mode) == 0o755
    assert list(project_dir.rglob(".pulseplate-postgres_backup.sh.tmp-*")) == []
    if log_file.exists():
        assert all(
            " stop " not in line and " up " not in line
            for line in log_file.read_text(encoding="utf-8").splitlines()
        )


def test_production_full_sync_cannot_republish_contracts_changed_after_validation(
    tmp_path: Path,
) -> None:
    env, project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    source_manifest = shell_bundle_dir / "deploy" / "prometheus" / "image-manifest.json"
    source_compose = shell_bundle_dir / "deploy" / "docker-compose.production.yaml"
    bin_dir = Path(env["DOCKER_BIN"]).parent
    tampered_manifest = '{"tampered":true}\n'
    tampered_compose = "services:\n  prometheus:\n    image: prom/prometheus:latest\n"
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\\nworker\\ncaddy\\nprometheus\\n' ;;
  *"run --rm --no-deps app alembic upgrade head"*)
    printf '%s' '{tampered_manifest}' > "{source_manifest}"
    printf '%s' '{tampered_compose}' > "{source_compose}"
    ;;
  *"ps -q app"*) printf 'app-id\\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert source_manifest.read_text(encoding="utf-8") == tampered_manifest
    assert source_compose.read_text(encoding="utf-8") == tampered_compose
    assert (project_dir / "deploy" / "prometheus" / "image-manifest.json").read_text(
        encoding="utf-8"
    ) == PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8")
    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT


def test_deploy_production_syncs_shell_bundle_with_autodetected_compose_file(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env.pop("COMPOSE_FILE", None)
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT
    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "frontend-sync\n"
    assert (project_dir / "deploy" / "Caddyfile.production").is_file()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_deploy_production_syncs_shell_bundle_with_relative_compose_subpath(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(
        shell_bundle_dir,
        compose_text="services:\n  app:\n    image: ghcr.io/example/pulseplate:test\n",
    )
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "deploy/docker-compose.production.yaml"
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == "services:\n  app:\n    image: ghcr.io/example/pulseplate:test\n"
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_deploy_production_autodetects_deploy_subdir_compose_and_env_file(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    deploy_dir = project_dir / "deploy"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (deploy_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"/deploy/.env -f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env.pop("COMPOSE_FILE", None)
    env.pop("ENV_FILE", None)
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f deploy/docker-compose.production.yaml pull app" in line
        for line in log_lines
    )
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f deploy/docker-compose.production.yaml up -d --remove-orphans caddy"
        in line
        for line in log_lines
    )


def test_deploy_production_uses_deploy_env_file_for_absolute_deploy_compose_path(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    deploy_dir = project_dir / "deploy"
    compose_file = deploy_dir / "docker-compose.production.yaml"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (deploy_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"/deploy/.env -f {compose_file} ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = str(compose_file)
    env.pop("ENV_FILE", None)
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "compose --env-file" in line and f"{deploy_dir / '.env'} -f {compose_file} pull app" in line
        for line in log_lines
    )
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f {compose_file} up -d --remove-orphans caddy" in line
        for line in log_lines
    )


def test_deploy_production_rejects_compose_file_outside_deploy_dir_during_shell_sync(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    outside_dir = tmp_path / "outside"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    outside_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (outside_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = str(outside_dir / "docker-compose.production.yaml")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "COMPOSE_FILE must select one exact canonical production Compose identity" in (
        completed.stderr
    )


def test_deploy_production_exits_non_zero_when_migrations_fail(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
    printf 'migration failed\\n' >&2
    exit 1
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Database migrations failed (exit code: 1)" in completed.stderr

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("run --rm --no-deps app alembic upgrade head" in line for line in log_lines)
    assert all("up -d --remove-orphans app" not in line for line in log_lines)
    assert all("up -d --remove-orphans caddy" not in line for line in log_lines)
    assert not any(
        line.startswith("curl ") and "https://pulseplate.test/ready" in line for line in log_lines
    )


def test_deploy_production_keeps_shell_bundle_untouched_when_migrations_fail(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (project_dir / "frontend").mkdir()
    (project_dir / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
    printf 'migration failed\\n' >&2
    exit 1
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (project_dir / "frontend" / "stale.txt").read_text(encoding="utf-8") == "old-shell\n"
    assert not (project_dir / "frontend" / "bundle-marker.txt").exists()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "stale-diagnose\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "stale-redeploy\n"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://pulseplate:secret@postgres:5432/pulseplate",  # pragma: allowlist secret
        "postgresql+psycopg://pulseplate:secret@postgres/pulseplate",  # pragma: allowlist secret
        "postgresql+psycopg://pulseplate:secret@postgres:6543/pulseplate",  # pragma: allowlist secret
    ],
)
def test_deploy_production_rejects_compose_local_postgres_dsn(
    tmp_path: Path,
    database_url: str,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        f"DATABASE_URL={database_url}\n",
        encoding="utf-8",
    )

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "external managed PostgreSQL" in completed.stderr


def test_deploy_production_rejects_compose_with_local_postgres_reference(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(
        project_dir,
        compose_text=(
            "services:\n  app:\n    depends_on:\n      postgres:\n"
            "        condition: service_healthy\n  postgres:\n    image: postgres:16\n"
        ),
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *"config --services"*) printf 'app\npostgres\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Managed production Compose must not contain a local postgres service" in (
        completed.stderr
    )


@pytest.mark.parametrize(
    "destination_helper_variant",
    ("absent", "stale-executable", "stale-nonexec"),
)
@pytest.mark.parametrize(
    "env_file_input", ("absolute", ".env", "./.env", "runtime config/selected.env", "missing.env")
)
def test_deploy_production_accepts_only_explicit_exact_self_hosted_database_contour(
    tmp_path: Path,
    destination_helper_variant: str,
    env_file_input: str,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    self_hosted_compose = SELF_HOSTED_COMPOSE_PATH.read_text(encoding="utf-8")
    _write_production_host_contract(
        project_dir,
        compose_text=self_hosted_compose,
        self_hosted=True,
    )
    _write_shell_bundle_contract(
        shell_bundle_dir,
        compose_text=self_hosted_compose,
        compose_name="docker-compose.production.selfhosted.yaml",
    )
    source_backup_helper = shell_bundle_dir / "scripts" / "ops" / "postgres_backup.sh"
    source_backup_helper.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'test "$ENV_FILE" = "$STUB_EXPECTED_ENV_FILE"\n'
        'printf "reviewed-bundle-backup project=%s compose=%s env=%s\\n" "$PROJECT_DIR" "$COMPOSE_FILE" "$ENV_FILE" >> "$STUB_DEPLOY_LOG_FILE"\n'
        'receipt="${BACKUP_DIR}/pulseplate_reviewed.dump"\n'
        "printf 'synthetic-custom-dump' > \"$receipt\"\n"
        "printf 'Backup created: %s\\n' \"$receipt\"\n",
        encoding="utf-8",
    )
    source_backup_helper.chmod(0o755)
    destination_backup_helper = project_dir / "scripts" / "ops" / "postgres_backup.sh"
    stale_helper_bytes = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "stale-host-backup\\n" >> "$STUB_DEPLOY_LOG_FILE"\n'
        'receipt="${BACKUP_DIR}/pulseplate_stale.dump"\n'
        "printf 'synthetic-custom-dump' > \"$receipt\"\n"
        'chmod 0600 "$receipt"\n'
        "printf 'Backup created: %s\\n' \"$receipt\"\n"
    ).encode()
    if destination_helper_variant == "absent":
        destination_backup_helper.unlink()
        destination_backup_helper.parent.rmdir()
        destination_backup_helper.parent.parent.rmdir()
    else:
        destination_backup_helper.write_bytes(stale_helper_bytes)
        destination_backup_helper.chmod(
            0o755 if destination_helper_variant == "stale-executable" else 0o644
        )
    selected_env = project_dir / (
        env_file_input if env_file_input == "runtime config/selected.env" else ".env"
    )
    selected_env.parent.mkdir(parents=True, exist_ok=True)
    selected_env.write_text(
        "\n".join(
            (
                "DATABASE_URL=postgresql+psycopg://stale:managed@db.example.com/db",  # pragma: allowlist secret
                "POSTGRES_DB=pulseplate",
                "POSTGRES_USER=pulseplate",
                "POSTGRES_PASSWORD=test-only",  # pragma: allowlist secret
            )
        )
        + "\n",
        encoding="utf-8",
    )
    if env_file_input == "missing.env":
        (project_dir / "deploy" / ".env").write_text(
            selected_env.read_text(encoding="utf-8"), encoding="utf-8"
        )
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "compose" ]; then
  test "$2" = "--env-file"
  test "$3" = "$STUB_EXPECTED_ENV_FILE"
fi
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\ncaddy\npostgres\nprometheus\nworker\n' ;;
  *"ps -q postgres"*) printf 'aaaaaaaaaaaa\n' ;;
  *"ps -q app"*) printf 'bbbbbbbbbbbb\n' ;;
  *"ps -q caddy"*) printf 'cccccccccccc\n' ;;
  *"ps -q worker"*) printf 'dddddddddddd\n' ;;
  *"inspect --format"*) printf 'healthy\n' ;;
  *"ps --last 20"*) printf 'CONTAINER ID\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.pop("GHCR_TOKEN", None)
    env.pop("GHCR_USER", None)
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(selected_env) if env_file_input == "absolute" else env_file_input,
            "COMPOSE_FILE": CANONICAL_SELF_HOSTED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "STUB_DEPLOY_LOG_FILE": str(log_file),
            "STUB_EXPECTED_ENV_FILE": str(selected_env),
            "SHELL_BUNDLE_DIR": str(shell_bundle_dir),
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if env_file_input == "missing.env":
        assert completed.returncode == 1
        assert "Missing production env file" in completed.stderr
        assert not log_file.exists()
        return
    assert completed.returncode == 0, completed.stderr
    assert "Production deploy preflight passed" in completed.stdout
    if destination_helper_variant == "absent":
        assert not destination_backup_helper.exists()
        assert not destination_backup_helper.parent.exists()
    else:
        assert destination_backup_helper.read_bytes() == stale_helper_bytes
        assert stat.S_IMODE(destination_backup_helper.stat().st_mode) == (
            0o755 if destination_helper_variant == "stale-executable" else 0o644
        )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    quiesce_index = next(
        index for index, line in enumerate(log_lines) if " stop worker caddy app" in line
    )
    backup_index = next(
        index for index, line in enumerate(log_lines) if line.startswith("reviewed-bundle-backup ")
    )
    old_stop_index = log_lines.index(f"docker stop {'a' * 64}")
    candidate_index = next(
        index for index, line in enumerate(log_lines) if " up -d --pull never postgres" in line
    )
    migration_index = next(
        index
        for index, line in enumerate(log_lines)
        if " run --rm --no-deps app alembic upgrade head" in line
    )
    assert quiesce_index < backup_index < old_stop_index < candidate_index < migration_index
    assert "stale-host-backup" not in log_lines
    assert f"project={project_dir / 'deploy'}" in log_lines[backup_index]
    assert f"env={selected_env}" in log_lines[backup_index]
    assert (
        f"compose={project_dir / 'deploy' / 'docker-compose.production.selfhosted.yaml'}"
        in log_lines[backup_index]
    )
    assert destination_backup_helper.read_bytes() == source_backup_helper.read_bytes()
    assert stat.S_IMODE(destination_backup_helper.stat().st_mode) == 0o755
    backup_receipt = project_dir / "backups" / "pulseplate_reviewed.dump"
    assert stat.S_IMODE(backup_receipt.stat().st_mode) == 0o600

    alternate_backup_helper = project_dir / "scripts" / "ops" / "alternate_backup.sh"
    alternate_backup_helper.write_bytes(source_backup_helper.read_bytes())
    alternate_backup_helper.chmod(0o755)
    env["BACKUP_HELPER"] = str(alternate_backup_helper)
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "backup helper must use the canonical deployed path" in completed.stderr
    env.pop("BACKUP_HELPER")

    env.pop("COMPOSE_FILE")
    env["PROD_DEPLOY_MODE"] = "self-hosted"
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "RESOLVED_COMPOSE_FILE does not exist" in completed.stderr


def test_deploy_production_does_not_require_home_when_docker_bin_is_explicit(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env.pop("HOME", None)
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Deploy dir:" in completed.stdout
    assert "compose --env-file" in log_file.read_text(encoding="utf-8")


def test_deploy_production_rejects_relative_docker_bin_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    project_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DOCKER_BIN"] = "docker"
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "DOCKER_BIN must be an absolute path" in completed.stderr


def test_diagnose_web_reports_green_for_spa_and_api_contract(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag.log"
    bin_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
exit 0
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
    url=""
    method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{display:grid}.min-h-screen{min-height:100vh}.rounded-2xl{border-radius:1rem}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{"ok": true}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{"detail": "validation"}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{"detail": "Method Not Allowed"}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist)
    status="404"
    content_type="application/json"
    payload='{"detail": "not found"}'
    ;;
  GET:https://pulseplate.test/api/v1/admin/status)
    status="403"
    content_type="application/json"
    payload='{"detail": "forbidden"}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "PASS: spa-bmi: /bmi serves the SPA shell with HTTP 200." in completed.stdout
    assert (
        "PASS: static-css: /assets/index-test.css is public CSS with HTTP 200." in completed.stdout
    )
    assert "PASS: health-json: /health reaches the JSON backend surface." in completed.stdout
    assert "PASS: sitemap-xml: /sitemap.xml reaches the XML sitemap surface." in completed.stdout
    assert (
        "PASS: legacy-bmi-post: /bmi reached the backend JSON surface (status 422)."
        in completed.stdout
    )
    assert "PASS: legacy-bmi-options: /bmi stayed off SPA/static-405" in completed.stdout
    assert "PASS: legacy-plan-get: /plan stayed off the SPA shell" in completed.stdout
    assert "PASS: legacy-insight-get: /insight stayed off the SPA shell" in completed.stdout
    assert (
        "PASS: legacy-bmi-calculator-get: /legacy/bmi-calculator stayed off the SPA shell"
        in completed.stdout
    )
    assert (
        "PASS: api-prefix: /api/v1/does-not-exist reached the backend JSON surface"
        in completed.stdout
    )
    assert (
        "PASS: admin-canary: /api/v1/admin/status reached the admin/backend canary surface"
        in completed.stdout
    )
    assert "PASS: websocket-upgrade: /ws did not fall through to SPA" in completed.stdout
    assert "Summary: all requested checks passed." in completed.stdout


def test_diagnose_web_uses_cloudflare_access_service_token_headers(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag-access.log"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
headers=""
body=""
url=""
method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{{display:grid}}.min-h-screen{{min-height:100vh}}.rounded-2xl{{border-radius:1rem}}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{{"ok": true}}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{{"detail": "validation"}}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{{"detail": "Method Not Allowed"}}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist)
    status="404"
    content_type="application/json"
    payload='{{"detail": "not found"}}'
    ;;
  GET:https://pulseplate.test/api/v1/admin/status)
    status="403"
    content_type="application/json"
    payload='{{"detail": "forbidden"}}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CF_ACCESS_CLIENT_ID"] = "client-id"
    env["CF_ACCESS_CLIENT_SECRET"] = "client-secret"  # pragma: allowlist secret

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_output = log_file.read_text(encoding="utf-8")
    assert "-H CF-Access-Client-Id: client-id" in log_output
    assert "-H CF-Access-Client-Secret: client-secret" in log_output
    static_css_calls = [
        line
        for line in log_output.splitlines()
        if "https://pulseplate.test/assets/index-test.css" in line
    ]
    assert static_css_calls
    assert all("CF-Access-Client-" not in line for line in static_css_calls)
    assert (
        "PASS: Cloudflare Access service-token headers enabled for private probes."
        in completed.stdout
    )


def test_diagnose_web_fails_when_admin_canary_route_is_missing(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
url=""
method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{display:grid}.min-h-screen{min-height:100vh}.rounded-2xl{border-radius:1rem}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{"ok": true}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{"detail": "validation"}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{"detail": "Method Not Allowed"}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist|GET:https://pulseplate.test/api/v1/admin/status)
    status="404"
    content_type="application/json"
    payload='{"detail": "not found"}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (
        "FAIL: admin-canary: /api/v1/admin/status returned 404, so the admin canary route is missing or misrouted."
        in completed.stdout
    )


def test_diagnose_web_rejects_partial_cloudflare_access_service_token_env(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CF_ACCESS_CLIENT_ID"] = "client-id"
    env.pop("CF_ACCESS_CLIENT_SECRET", None)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--check-caddy-config-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (
        "FAIL: CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be provided together"
        in completed.stdout
    )


def test_diagnose_web_fails_without_base_url_for_http_probes(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env.pop("BASE_URL", None)
    env.pop("PRODUCTION_DOMAIN", None)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--skip-caddy-validate"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "FAIL: BASE_URL or PRODUCTION_DOMAIN is required for HTTP probes." in completed.stdout


def test_diagnose_web_warns_when_docker_daemon_is_unavailable(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "info" ]]; then
  exit 1
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--check-caddy-config-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (
        "WARN: Docker daemon/socket is unavailable; skipping local Caddyfile validation."
        in completed.stdout
    )


def test_diagnose_web_reports_failure_for_spa_or_api_contract(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag-fail.log"
    bin_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
exit 0
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="200"
content_type="text/html; charset=utf-8"
payload='<!doctype html><html><body><h1>maintenance</h1></body></html>'

if [[ "$url" == "https://pulseplate.test/health" ]]; then
  status="500"
  content_type="text/html; charset=utf-8"
  payload='<html><body>error</body></html>'
elif [[ "$url" == "https://pulseplate.test/openapi.json" ]]; then
  status="200"
  content_type="application/json"
  payload='{"ok": true}'
elif [[ "$url" == "https://pulseplate.test/ws" ]]; then
  status="400"
  content_type="text/plain"
  payload='upgrade required'
fi

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "FAIL: spa-root: response does not contain the SPA shell marker." in completed.stdout
    assert "FAIL: health-json: expected HTTP 200, got 500." in completed.stdout


def test_redeploy_caddy_runs_diagnose_web_when_domain_is_available(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    deploy_dir = temp_repo / "deploy"
    scripts_dir = temp_repo / "scripts"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "redeploy.log"
    temp_repo.mkdir()
    deploy_dir.mkdir()
    scripts_dir.mkdir()
    bin_dir.mkdir()

    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text('PRODUCTION_DOMAIN="pulseplate.test"\n', encoding="utf-8")

    diagnose_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'diagnose BASE_URL=%s ARGS=%s\\n' "${{BASE_URL:-}}" "$*" >> "{log_file}"
"""
    _write_executable(scripts_dir / "diagnose_web.sh", diagnose_stub)
    _write_executable(
        scripts_dir / "redeploy_caddy.sh",
        (REPO_ROOT / "scripts" / "redeploy_caddy.sh").read_text(encoding="utf-8"),
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
if [[ "$*" == "compose version" ]]; then
  exit 0
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_DIR"] = str(deploy_dir)
    env["DIAG_MAX_ATTEMPTS"] = "1"
    env["DIAG_RETRY_DELAY_SECONDS"] = "0"

    subprocess.run(
        ["bash", str(scripts_dir / "redeploy_caddy.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "docker compose -f docker-compose.production.yaml build caddy" in line for line in log_lines
    )
    assert any(
        "docker compose -f docker-compose.production.yaml up -d caddy" in line for line in log_lines
    )
    assert any(
        "diagnose BASE_URL=https://pulseplate.test ARGS=--skip-caddy-validate" in line
        for line in log_lines
    )


def test_redeploy_caddy_exits_non_zero_when_diagnosis_fails(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    deploy_dir = temp_repo / "deploy"
    scripts_dir = temp_repo / "scripts"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "redeploy.log"
    temp_repo.mkdir()
    deploy_dir.mkdir()
    scripts_dir.mkdir()
    bin_dir.mkdir()

    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text('PRODUCTION_DOMAIN="pulseplate.test"\n', encoding="utf-8")

    diagnose_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'diagnose-fail BASE_URL=%s ARGS=%s\\n' "${{BASE_URL:-}}" "$*" >> "{log_file}"
exit 1
"""
    _write_executable(scripts_dir / "diagnose_web.sh", diagnose_stub)
    _write_executable(
        scripts_dir / "redeploy_caddy.sh",
        (REPO_ROOT / "scripts" / "redeploy_caddy.sh").read_text(encoding="utf-8"),
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
if [[ "$*" == "compose version" ]]; then
  exit 0
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_DIR"] = str(deploy_dir)
    env["DIAG_MAX_ATTEMPTS"] = "2"
    env["DIAG_RETRY_DELAY_SECONDS"] = "0"

    completed = subprocess.run(
        ["bash", str(scripts_dir / "redeploy_caddy.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "❌ diagnose_web.sh reported a routing mismatch" in completed.stdout


def _write_stage_native_oracles(project_dir: Path) -> None:
    """Keep real JSON validators while replacing native mount/crypto observations."""
    from scripts.ops.check_staging_security import DEVICE_PATH, STORAGE_ROOT

    (project_dir / "scripts" / "ops").mkdir(parents=True, exist_ok=True)
    (project_dir / "scripts" / "ci").mkdir(parents=True, exist_ok=True)
    (project_dir / "secrets").mkdir(exist_ok=True)
    (project_dir / "backups").mkdir(exist_ok=True)
    receipt = {
        "schema": "pulseplate.staging-storage.v1",
        "droplet_id": 594869239,
        "volume_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "volume_name": "pulseplate-staging-data",
        "filesystem_uuid": "11111111-2222-3333-4444-555555555555",
        "mountpoint": STORAGE_ROOT,
        "device": DEVICE_PATH,
        "size_gib": 50,
        "backend_uid": 1000,
        "backend_gid": 1000,
    }
    (project_dir / ".staging-storage.json").write_text(json.dumps(receipt))
    (project_dir / ".staging-storage.json").chmod(0o600)
    for name in (
        "postgres_ca",
        "postgres_server_crt",
        "postgres_server_key",
        "postgres_password",
        "postgres_pgpass",
    ):
        target = project_dir / "secrets" / name
        target.write_text("native-crypto-oracle-fixture")
        target.chmod(0o600)
    _write_executable(
        project_dir / "scripts" / "ops" / "check_staging_security.py",
        """#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from scripts.ops import check_staging_security as security
parser = argparse.ArgumentParser()
parser.add_argument("--project-dir", type=Path, required=True)
parser.add_argument("--storage-only", action="store_true")
parser.add_argument("--compose-stdin", action="store_true")
parser.add_argument("--print-backup-dir", action="store_true")
args = parser.parse_args()
try:
    security.validate_contract(json.loads((args.project_dir / ".staging-storage.json").read_text()))
    if args.compose_stdin:
        security.validate_compose(json.loads(sys.stdin.read()), args.project_dir)
except (ValueError, OSError) as error:
    print("Staging security HOLD: " + str(error), file=sys.stderr)
    raise SystemExit(1)
print(str(args.project_dir / "backups") if args.print_backup_dir else "Native staging probes verified")
""",
    )
    _write_executable(
        project_dir / "scripts" / "ci" / "check_pgvector_attestations.py",
        """#!/usr/bin/env python3
import json, os, subprocess
from scripts.ci import check_pgvector_attestations as verifier
from tests.test_pgvector_attestations import packet
_, payloads = packet()
def verified_crypto(arguments):
    kind = arguments[arguments.index("--predicate-type") + 1]
    if os.getenv("STUB_ATTESTATION_STATUS", "0") != "0":
        raise RuntimeError("Native attestation crypto rejected")
    return subprocess.CompletedProcess(arguments, 0, json.dumps(payloads[kind]), "")
verifier.native._run_gh = verified_crypto
raise SystemExit(verifier.main())
""",
    )


def _staging_deploy_fixture(tmp_path: Path) -> tuple[dict[str, str], Path]:
    project_dir = tmp_path / "staging"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "scripts" / "ops").mkdir(parents=True)
    (project_dir / "prometheus").mkdir()
    (project_dir / "postgres-pgvector").mkdir()
    (project_dir / "secrets").mkdir()
    (project_dir / "secrets").chmod(0o700)
    (project_dir / "backups").mkdir()
    (project_dir / "docker-compose.staging.yaml").write_text(
        "services: {app: {}, caddy: {}}\n", encoding="utf-8"
    )
    (project_dir / "Caddyfile").write_text(":80 { respond ok }\n", encoding="utf-8")
    (project_dir / "prometheus" / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project_dir / "prometheus" / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project_dir / "postgres-pgvector" / "image-manifest.json").write_text(
        POSTGRES_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project_dir / "secrets" / "pulseplate_metrics_scrape_key").write_text(
        METRICS_SECRET_SENTINEL, encoding="ascii"
    )
    (project_dir / "secrets" / "pulseplate_metrics_scrape_key").chmod(0o444)
    (project_dir / ".attested-digest-deploy-v1").write_text(
        "pulseplate-staging-attested-digest-v1", encoding="utf-8"
    )
    (project_dir / ".env").write_text(
        "\n".join(
            (
                "STAGING_DOMAIN=staging.example.com",
                "POSTGRES_USER=pulseplate",
                "POSTGRES_DB=pulseplate",
                "POSTGRES_PASSWORD=test-only",  # pragma: allowlist secret
                "DATABASE_URL=postgresql+psycopg://pulseplate:test-only@postgres/pulseplate",  # pragma: allowlist secret
                "GHCR_USER=pulseplate-ci",
                "GHCR_TOKEN=test-only-token",  # pragma: allowlist secret
                "STAGING_IMAGE_REF=ghcr.io/attacker/override:latest",
                "STAGING_CADDY_IMAGE_REF=ghcr.io/attacker/override:latest",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / ".env").chmod(0o600)
    _write_stage_native_oracles(project_dir)
    _write_executable(
        project_dir / "scripts" / "ops" / "postgres_backup.sh",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'backup docker=%s env_file=%s args=%s\\n' \
  "${{DOCKER_BIN:-}}" "${{ENV_FILE:-}}" "$*" >> "{log_file}"
if [ "${{STUB_BACKUP_FAILURE:-0}}" -ne 0 ]; then
  exit "${{STUB_BACKUP_FAILURE}}"
fi
receipt="${{BACKUP_DIR}}/pulseplate_test.dump"
printf 'synthetic-custom-dump' > "$receipt"
chmod 0600 "$receipt"
printf 'Backup created: %s\\n' "$receipt"
""",
    )
    _write_executable(
        bin_dir / "docker",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
printf 'env backend=%s caddy=%s config=%s\n' "${{STAGING_IMAGE_REF:-}}" "${{STAGING_CADDY_IMAGE_REF:-}}" "${{DOCKER_CONFIG:-}}" >> "{log_file}"
case "$*" in
  start\\ *)
    if [ -n "${{STUB_RESTART_FAILURE_ID:-}}" ] && \
       [ "$*" = "start $STUB_RESTART_FAILURE_ID" ]; then
      exit "${{STUB_RESTART_FAILURE_STATUS:-77}}"
    fi
    ;;
  stop\\ *)
    if [ -n "${{STUB_POSTGRES_STOP_FAILURE_ID:-}}" ] && \
       [ "$*" = "stop $STUB_POSTGRES_STOP_FAILURE_ID" ]; then
      exit "${{STUB_POSTGRES_STOP_FAILURE_STATUS:-47}}"
    fi
    ;;
  *"login ghcr.io"*"--password-stdin"*) cat >/dev/null ;;
  *"info --format"*"Architecture"*) printf 'amd64\n' ;;
  *"inspect --format"*"State.Running"*) printf 'true\n' ;;
  *"ps -q postgres"*)
    if [[ "${{STUB_POSTGRES_CONTAINER_ABSENT:-0}}" != "1" ]] || \
       [[ -f "${{STUB_POSTGRES_STARTED_FILE:-/nonexistent}}" ]]; then
      printf 'aaaaaaaaaaaa\n'
    fi
    ;;
  *"inspect --format"*) printf 'healthy\n' ;;
  *"ps -q app"*) printf 'bbbbbbbbbbbb\n' ;;
  *"ps -q caddy"*) printf 'cccccccccccc\n' ;;
  *"ps -q worker"*) printf 'dddddddddddd\n' ;;
  *"up -d --pull never postgres"*)
    if [[ "${{STUB_POSTGRES_UP_FAILURE:-0}}" != "0" ]]; then
      exit "${{STUB_POSTGRES_UP_FAILURE}}"
    fi
    : > "$STUB_POSTGRES_STARTED_FILE"
    ;;
  *"psycopg.connect"*)
    exit "${{STUB_APPLICATION_TLS_STATUS:-0}}"
    ;;
  *"run --rm --no-deps app alembic upgrade head"*)
    if [[ "${{STUB_MIGRATION_FAILURE:-0}}" == "1" ]]; then
      exit 42
    fi
    ;;
esac
""",
    )
    _write_executable(
        bin_dir / "stat",
        """#!/usr/bin/env bash
set -euo pipefail
case "${*: -1}" in
  *.attested-digest-deploy-v1) printf '0:0:644\\n' ;;
  *.env) printf '%s\\n' "${STUB_ENV_MODE:-600}" ;;
  *postgres_backup.sh) printf '%s\\n' "${STUB_HELPER_MODE:-755}" ;;
  *pulseplate_test.dump) printf '600\\n' ;;
  */secrets) printf '%s\\n' "${STUB_SECRET_DIR_METADATA:-$EUID:700}" ;;
  *pulseplate_metrics_scrape_key) printf '%s\\n' "${STUB_SECRET_FILE_METADATA:-$EUID:444}" ;;
  *) exit 1 ;;
esac
""",
    )
    _write_executable(
        bin_dir / "curl",
        f'#!/usr/bin/env bash\nprintf \'curl %s\\n\' "$*" >> "{log_file}"\n',
    )
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PROJECT_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": str(project_dir / "docker-compose.staging.yaml"),
            "BACKUP_DIR": str(project_dir / "backups"),
            "BACKUP_HELPER": str(project_dir / "scripts" / "ops" / "postgres_backup.sh"),
            "STAGING_DEPLOY_MARKER": str(project_dir / ".attested-digest-deploy-v1"),
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "PYTHONPATH": str(REPO_ROOT),
            "STUB_PROMETHEUS_COMPOSE_JSON": _staging_compose_fixture_json(project_dir),
            "CURL_BIN": str(bin_dir / "curl"),
            "STAT_BIN": str(bin_dir / "stat"),
            "STAGING_DOMAIN": "staging.example.com",
            "GHCR_USER": "pulseplate-ci",
            "GHCR_TOKEN": "test-only-token",  # pragma: allowlist secret
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
            "STUB_POSTGRES_STARTED_FILE": str(tmp_path / "postgres-started"),
        }
    )
    return env, log_file


@pytest.mark.parametrize(
    "arguments",
    (
        (),
        ("latest",),
        ("ghcr.io/katsiarynakavaleuskaya/pulseplate:abc", "caddy:2.11.4"),
        (
            "docker.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "A" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
            "unexpected",
        ),
    ),
)
def test_staging_deploy_rejects_unsafe_image_references_before_side_effects(
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), *arguments],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not log_file.exists()


def test_staging_deploy_preflight_validates_contract_without_mutation(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts" / "deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(line == "docker info --format {{.Architecture}}" for line in log_lines)
    assert any("compose --env-file" in line and "config --quiet" in line for line in log_lines)
    assert not any("login" in line or "pull" in line or "up -d" in line for line in log_lines)
    assert "Staging deploy preflight passed" in completed.stdout


@pytest.mark.parametrize(
    ("scheduler_mode_value", "expected_returncode"),
    (
        ("external # scheduler owner", 0),
        (" disabled\t# maintenance window", 0),
        ("external#not-a-compose-comment", 1),
        ('"external"', 1),
        ("'external'", 1),
        ("${SCHEDULER_MODE}", 1),
    ),
)
def test_staging_deploy_matches_bounded_compose_scheduler_mode_syntax(
    tmp_path: Path,
    scheduler_mode_value: str,
    expected_returncode: int,
) -> None:
    env, _log_file = _staging_deploy_fixture(tmp_path)
    env.pop("FOOD_UPDATE_SCHEDULER_MODE", None)
    env_file = Path(env["ENV_FILE"])
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(f"FOOD_UPDATE_SCHEDULER_MODE={scheduler_mode_value}\n")
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts" / "deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == expected_returncode, completed.stderr
    if expected_returncode == 0:
        assert "Staging deploy preflight passed" in completed.stdout
    else:
        assert "FOOD_UPDATE_SCHEDULER_MODE must be exactly external or disabled" in completed.stderr


def test_staging_deploy_preserves_backup_migration_caddy_order_and_cli_identity(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    project_dir = Path(env["PROJECT_DIR"])
    selected_env_file = project_dir / "config" / "selected.env"
    selected_env_file.parent.mkdir()
    selected_env_file.write_bytes((project_dir / ".env").read_bytes())
    selected_env_file.chmod(0o600)
    env["ENV_FILE"] = str(selected_env_file)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    login_index = _assert_log_index(
        log_lines, predicate=lambda line: "docker login ghcr.io" in line, message="missing login"
    )
    pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " pull app caddy postgres prometheus" in line,
        message="missing exact app, Caddy, PostgreSQL, and Prometheus pull",
    )
    image_inspect_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("docker image inspect "),
        message="missing pulled Prometheus platform manifest validation",
    )
    backup_index = _assert_log_index(
        log_lines, predicate=lambda line: line.startswith("backup "), message="missing backup"
    )
    postgres_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d --pull never postgres" in line,
        message="missing Postgres bootstrap",
    )
    quiesce_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " stop worker caddy app" in line,
        message="missing worker/app/Caddy quiesce",
    )
    migration_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line
        and " run --rm --no-deps app alembic upgrade head" in line,
        message="missing one-shot migration",
    )
    app_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d --pull never app" in line,
        message="missing app start",
    )
    caddy_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d --pull never caddy" in line,
        message="missing Caddy start",
    )
    assert (
        login_index
        < pull_index
        < image_inspect_index
        < quiesce_index
        < backup_index
        < postgres_index
        < migration_index
        < app_index
        < caddy_index
    )
    assert all(" up -d postgres" not in line for line in log_lines)
    assert f"backup docker={env['DOCKER_BIN']}" in log_lines[backup_index]
    assert f"env_file={selected_env_file}" in log_lines[backup_index]

    env_lines = [line for line in log_lines if line.startswith("env backend=")]
    assert env_lines
    assert all(f"backend={backend_ref}" in line for line in env_lines)
    assert all(f"caddy={caddy_ref}" in line for line in env_lines)
    docker_config = env_lines[-1].split(" config=", 1)[1]
    assert docker_config
    assert not Path(docker_config).exists()


def test_staging_backup_failure_preserves_primary_exit_and_never_switches_postgres(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_BACKUP_FAILURE"] = "33"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 33
    assert "backup execution failed ambiguously" in completed.stderr
    assert "captured product writers remain quiesced" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    quiesce = next(
        index for index, line in enumerate(log_lines) if " stop worker caddy app" in line
    )
    backup = next(index for index, line in enumerate(log_lines) if line.startswith("backup "))
    assert quiesce < backup
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(line != f"docker stop {'a' * 64}" for line in log_lines)
    assert all(not line.startswith("docker start ") for line in log_lines)


def test_old_postgres_stop_failure_keeps_product_writers_quiesced(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env.update(
        {
            "STUB_POSTGRES_STOP_FAILURE_ID": "a" * 64,
            "STUB_POSTGRES_STOP_FAILURE_STATUS": "47",
        }
    )
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 47
    assert "captured product writers remain quiesced" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert f"docker stop {'a' * 64}" in log_lines
    assert all(not line.startswith("docker start ") for line in log_lines)
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(" alembic upgrade head" not in line for line in log_lines)

    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    for relative_path in ("scripts/deploy.sh", "scripts/deploy_production.sh"):
        script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        marker = 'if "$DOCKER_BIN" stop "$postgres_container" >/dev/null; then'
        start = script.index(marker)
        line_start = script.rfind("\n", 0, start) + 1
        indentation = script[line_start:start]
        closing = f"\n{indentation}fi"
        end = script.index(closing, start) + len(closing)
        stop_failure_branch = script[start:end]
        assert "captured product writers remain quiesced" in stop_failure_branch
        assert "restart_captured_product_containers_after_failure" not in stop_failure_branch

        branch_log = tmp_path / f"{Path(relative_path).stem}-ambiguous-stop.log"
        docker_stub = tmp_path / f"{Path(relative_path).stem}-docker"
        _write_executable(
            docker_stub,
            f'#!/usr/bin/env bash\nprintf \'docker %s\\n\' "$*" > "{branch_log}"\nexit 47\n',
        )
        branch_program = (
            "set -euo pipefail\n"
            f'DOCKER_BIN="{docker_stub}"\n'
            f'postgres_container="{"a" * 64}"\n'
            f"{stop_failure_branch}\n"
        )
        branch_result = subprocess.run(
            [bash_bin, "-c", branch_program],
            text=True,
            capture_output=True,
            check=False,
        )
        assert branch_result.returncode == 47
        assert "captured product writers remain quiesced" in branch_result.stderr
        assert branch_log.read_text(encoding="utf-8") == f"docker stop {'a' * 64}\n"


def test_postgres_identity_revalidation_failure_keeps_product_writers_quiesced(
    tmp_path: Path,
) -> None:
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    marker = (
        'if assert_existing_postgres_unchanged "$postgres_state_receipt" '
        '"$postgres_runtime_receipt"; then'
    )

    for relative_path in ("scripts/deploy.sh", "scripts/deploy_production.sh"):
        script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert script.count(marker) == 2
        search_from = 0
        for occurrence in range(2):
            start = script.index(marker, search_from)
            line_start = script.rfind("\n", 0, start) + 1
            indentation = script[line_start:start]
            closing = f"\n{indentation}fi"
            end = script.index(closing, start) + len(closing)
            branch = script[start:end]
            search_from = end
            assert "PostgreSQL identity revalidation failed" in branch
            assert "captured product writers remain quiesced" in branch
            assert "restart_captured_product_containers_after_failure" not in branch

            restart_log = tmp_path / f"{Path(relative_path).stem}-{occurrence}-restart.log"
            branch_program = (
                "set -euo pipefail\n"
                'postgres_state_receipt="state"\n'
                'postgres_runtime_receipt="runtime"\n'
                "assert_existing_postgres_unchanged() { return 42; }\n"
                "restart_captured_product_containers_after_failure() {\n"
                f"  printf 'restarted\\n' > \"{restart_log}\"\n"
                "}\n"
                f"{branch}\n"
            )
            completed = subprocess.run(
                [bash_bin, "-c", branch_program],
                text=True,
                capture_output=True,
                check=False,
            )
            assert completed.returncode == 42
            assert "captured product writers remain quiesced" in completed.stderr
            assert not restart_log.exists()


@pytest.mark.parametrize("relative_path", ("scripts/deploy.sh", "scripts/deploy_production.sh"))
@pytest.mark.parametrize(
    ("inspect_status", "inspect_output", "expected_message"),
    (
        (66, "", "Unable to inspect app container running state"),
        (0, "unknown\n", "Invalid app container running state"),
        (0, "true\nfalse\n", "Invalid app container running state"),
    ),
)
def test_product_service_census_fails_closed_on_untrusted_inspect_state(
    tmp_path: Path,
    relative_path: str,
    inspect_status: int,
    inspect_output: str,
    expected_message: str,
) -> None:
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    start = script.index("capture_running_service_container() {\n")
    end = script.index("\n}\n\nrestart_captured_product_containers()", start) + len("\n}\n")
    function = script[start:end]
    docker_stub = tmp_path / f"docker-{Path(relative_path).stem}-{inspect_status}"
    _write_executable(
        docker_stub,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'case "$*" in\n'
        "  *\"ps -q app\"*) printf 'bbbbbbbbbbbb\\n' ;;\n"
        '  *"inspect --format"*)\n'
        '    if [ "$STUB_INSPECT_STATUS" -ne 0 ]; then exit "$STUB_INSPECT_STATUS"; fi\n'
        "    printf '%b' \"$STUB_INSPECT_OUTPUT\"\n"
        "    ;;\n"
        "  *) exit 70 ;;\n"
        "esac\n",
    )
    program = (
        "set -euo pipefail\n"
        f'DOCKER_BIN="{docker_stub}"\n'
        f'COMPOSE=("{docker_stub}" compose)\n'
        'dc() { "$DOCKER_BIN" compose "$@"; }\n'
        f"{function}\n"
        "capture_running_service_container app\n"
    )
    completed = subprocess.run(
        [bash_bin, "-c", program],
        env={
            **os.environ,
            "STUB_INSPECT_STATUS": str(inspect_status),
            "STUB_INSPECT_OUTPUT": inspect_output,
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert expected_message in completed.stderr


def test_deploy_backup_helpers_receive_selected_compose_env_file() -> None:
    staging_script = (REPO_ROOT / "scripts/deploy.sh").read_text(encoding="utf-8")
    production_script = (REPO_ROOT / "scripts/deploy_production.sh").read_text(encoding="utf-8")
    helper_script = (REPO_ROOT / "scripts/ops/postgres_backup.sh").read_text(encoding="utf-8")

    assert "export DOCKER_BIN BACKUP_DIR PROJECT_DIR COMPOSE_FILE ENV_FILE" in staging_script
    assert "export DOCKER_BIN BACKUP_DIR POSTGRES_USER POSTGRES_DB ENV_FILE" in production_script
    assert 'ENV_FILE="${ENV_FILE:-}"' in helper_script
    assert 'compose_cmd+=(--env-file "$ENV_FILE")' in helper_script


def test_postgres_backup_and_receipt_failures_keep_product_writers_quiesced() -> None:
    markers = (
        ('if backup_output="$(', "PostgreSQL backup execution failed ambiguously"),
        (
            'if backup_receipt="$(validate_backup_receipt "$backup_output" '
            '"$postgres_container")"; then',
            "PostgreSQL backup receipt validation failed",
        ),
    )
    for relative_path in ("scripts/deploy.sh", "scripts/deploy_production.sh"):
        script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for marker, expected_message in markers:
            assert script.count(marker) == 1
            start = script.index(marker)
            line_start = script.rfind("\n", 0, start) + 1
            indentation = script[line_start:start]
            closing = f"\n{indentation}fi"
            end = script.index(closing, start) + len(closing)
            failure_branch = script[start:end]
            assert expected_message in failure_branch
            assert "captured product writers remain quiesced" in failure_branch
            assert "restart_captured_product_containers_after_failure" not in failure_branch


@pytest.mark.parametrize(
    "variant",
    ("unknown-image", "wrong-image-id", "wrong-pgdata", "runtime-failure", "identity-drift"),
)
def test_staging_existing_postgres_requires_closed_image_and_pgdata_identity(
    tmp_path: Path,
    variant: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    inspect_payload = json.loads(FAKE_POSTGRES_CONTAINER_INSPECT_JSON)
    if variant == "unknown-image":
        inspect_payload[0]["Config"]["Image"] = "attacker.invalid/not-postgres:latest"
    elif variant == "wrong-image-id":
        inspect_payload[0]["Image"] = "sha256:" + "e" * 64
    elif variant == "wrong-pgdata":
        inspect_payload[0]["Config"]["Env"] = ["PGDATA=/wrong", "PG_MAJOR=15"]
    elif variant == "runtime-failure":
        env["STUB_POSTGRES_RUNTIME_STATUS"] = "65"
    else:
        drift_payload = json.loads(json.dumps(inspect_payload))
        drift_payload[0]["Id"] = "f" * 64
        env["STUB_POSTGRES_INSPECT_DRIFT_FILE"] = str(tmp_path / "inspect-drift")
        env["STUB_POSTGRES_CONTAINER_INSPECT_JSON_AFTER_FIRST"] = json.dumps(drift_payload)
    env["STUB_POSTGRES_CONTAINER_INSPECT_JSON"] = json.dumps(inspect_payload)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    if variant != "identity-drift":
        assert all(" stop worker caddy app" not in line for line in log_lines)
    assert all(not line.startswith("backup ") for line in log_lines)
    assert all(" up -d --pull never postgres" not in line for line in log_lines)


def test_staging_rejects_unlistable_backup_before_postgres_switch(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_PG_RESTORE_LIST_STATUS"] = "67"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "not a listable custom-format dump" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(not line.startswith("docker stop a") for line in log_lines)


@pytest.mark.parametrize("relative_path", ("scripts/deploy.sh", "scripts/deploy_production.sh"))
@pytest.mark.parametrize(
    ("listing_status", "listing", "expected_status", "expected_message"),
    (
        (0, "", 0, None),
        (
            0,
            "unrelated_volume\npulseplate_postgres_data\n",
            1,
            "volume exists without one trustworthy running container",
        ),
        (0, "invalid volume\n", 1, "volume listing is malformed"),
        (47, "", 47, "Unable to establish PostgreSQL volume absence"),
    ),
)
def test_fresh_postgres_volume_probe_requires_definitive_absence(
    tmp_path: Path,
    relative_path: str,
    listing_status: int,
    listing: str,
    expected_status: int,
    expected_message: str | None,
) -> None:
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    marker = "require_absent_postgres_volume() {\n"
    start = script.index(marker)
    end = script.index("\n}\n", start) + len("\n}\n")
    function_definition = script[start:end]
    assert script.count("require_absent_postgres_volume") == 3

    docker_stub = tmp_path / f"{Path(relative_path).stem}-docker"
    response = (
        f"exit {listing_status}" if listing_status != 0 else f"printf '%b' {json.dumps(listing)}"
    )
    _write_executable(
        docker_stub,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [ "$*" != "volume ls --quiet" ]; then exit 99; fi\n'
        f"{response}\n",
    )
    program = (
        "set -euo pipefail\n"
        f'DOCKER_BIN="{docker_stub}"\n'
        'POSTGRES_VOLUME_NAME="pulseplate_postgres_data"\n'
        f"{function_definition}\n"
        "require_absent_postgres_volume\n"
    )
    completed = subprocess.run(
        [bash_bin, "-c", program],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == expected_status
    if expected_message is None:
        assert completed.stderr == ""
    else:
        assert expected_message in completed.stderr


@pytest.mark.parametrize(
    ("relative_path", "fresh_marker", "start_marker"),
    (
        (
            "scripts/deploy.sh",
            "Fresh PostgreSQL path admitted: rendered named volume is absent",
            "Starting the already pulled exact PostgreSQL candidate without registry access",
        ),
        (
            "scripts/deploy_production.sh",
            "Fresh self-hosted PostgreSQL path admitted: rendered named volume is absent",
            "Starting exact self-hosted PostgreSQL image without a registry pull",
        ),
    ),
)
def test_fresh_postgres_volume_recheck_is_the_last_gate_before_candidate_start(
    relative_path: str,
    fresh_marker: str,
    start_marker: str,
) -> None:
    script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    fresh_index = script.index(fresh_marker)
    start_index = script.index(start_marker, fresh_index)
    handoff_block = script[fresh_index:start_index]

    assert handoff_block.count("require_absent_postgres_volume") == 1
    assert "captured product writers remain quiesced" in handoff_block
    assert "restart_captured_product_containers_after_failure" not in handoff_block


def test_staging_orphan_postgres_volume_holds_before_quiesce_or_switch(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_POSTGRES_CONTAINER_ABSENT"] = "1"
    env["STUB_POSTGRES_VOLUME_LIST_OUTPUT"] = "pulseplate_postgres_data\n"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "volume exists without one trustworthy running container" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all(" stop worker caddy app" not in line for line in log_lines)
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(not line.startswith("backup ") for line in log_lines)


def test_staging_absent_volume_uses_fresh_path_without_backup(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_POSTGRES_CONTAINER_ABSENT"] = "1"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" stop worker caddy app" in line for line in log_lines)
    assert any(" up -d --pull never postgres" in line for line in log_lines)
    assert all(not line.startswith("backup ") for line in log_lines)


def test_staging_fresh_volume_appearance_after_quiesce_holds_before_candidate_start(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    volume_counter = tmp_path / "postgres-volume-list-count"
    env.update(
        {
            "STUB_POSTGRES_CONTAINER_ABSENT": "1",
            "STUB_POSTGRES_VOLUME_LIST_COUNTER_FILE": str(volume_counter),
            "STUB_POSTGRES_VOLUME_LIST_OUTPUT_AFTER_FIRST": "pulseplate_postgres_data\n",
        }
    )
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "volume exists without one trustworthy running container" in completed.stderr
    assert "volume revalidation failed; captured product writers remain quiesced" in (
        completed.stderr
    )
    assert volume_counter.read_text(encoding="utf-8") == "2\n"
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" stop worker caddy app" in line for line in log_lines)
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(not line.startswith("backup ") for line in log_lines)


def test_staging_ambiguous_volume_listing_holds_before_quiesce_or_switch(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_POSTGRES_CONTAINER_ABSENT"] = "1"
    env["STUB_POSTGRES_VOLUME_LIST_STATUS"] = "47"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 47
    assert "Unable to establish PostgreSQL volume absence; HOLD" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all(" stop worker caddy app" not in line for line in log_lines)
    assert all(" up -d --pull never postgres" not in line for line in log_lines)
    assert all(not line.startswith("backup ") for line in log_lines)


def test_staging_deploy_migration_failure_keeps_app_and_caddy_stopped(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_MIGRATION_FAILURE"] = "1"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 42
    assert "Caddy and app remain stopped" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" stop worker caddy app" in line for line in log_lines)
    assert any(" run --rm --no-deps app alembic upgrade head" in line for line in log_lines)
    assert not any(" up -d --pull never app" in line for line in log_lines)
    assert not any(" up -d --pull never caddy" in line for line in log_lines)


def test_staging_deploy_treats_env_file_as_data_and_drops_registry_credentials(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    project_dir = Path(env["PROJECT_DIR"])
    command_marker = tmp_path / "env-was-executed"
    with (project_dir / ".env").open("a", encoding="utf-8") as handle:
        handle.write("COMPOSE_FILE=/tmp/attacker-compose.yaml\n")
        handle.write(f'ENV_EXECUTION_PROBE=$(touch "{command_marker}")\n')

    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert not command_marker.exists()
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all("/tmp/attacker-compose.yaml" not in line for line in log_lines)
    logout_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line == "docker logout ghcr.io",
        message="missing registry logout",
    )
    backup_index = _assert_log_index(
        log_lines, predicate=lambda line: line.startswith("backup "), message="missing backup"
    )
    assert logout_index < backup_index


@pytest.mark.parametrize(
    "invalid_boundary",
    (
        "env-symlink",
        "env-mode",
        "compose-symlink",
        "caddy-symlink",
        "prometheus-config-symlink",
        "prometheus-manifest-symlink",
        "secret-dir-symlink",
        "secret-file-symlink",
        "secret-dir-mode",
        "secret-file-mode",
        "secret-dir-owner",
        "secret-file-owner",
        "helper-symlink",
        "helper-mode",
    ),
)
def test_staging_deploy_rejects_invalid_local_control_files_before_docker_side_effects(
    tmp_path: Path,
    invalid_boundary: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    project_dir = Path(env["PROJECT_DIR"])
    env_file = project_dir / ".env"
    compose_file = project_dir / "docker-compose.staging.yaml"
    caddyfile = project_dir / "Caddyfile"
    prometheus_config = project_dir / "prometheus" / "prometheus.yml"
    prometheus_manifest = project_dir / "prometheus" / "image-manifest.json"
    secret_dir = project_dir / "secrets"
    secret_file = secret_dir / "pulseplate_metrics_scrape_key"
    backup_helper = Path(env["BACKUP_HELPER"])

    if invalid_boundary == "env-symlink":
        real_env = project_dir / ".env.real"
        env_file.rename(real_env)
        env_file.symlink_to(real_env)
    elif invalid_boundary == "env-mode":
        env["STUB_ENV_MODE"] = "644"
    elif invalid_boundary == "compose-symlink":
        real_compose = compose_file.with_suffix(".real")
        compose_file.rename(real_compose)
        compose_file.symlink_to(real_compose)
    elif invalid_boundary == "caddy-symlink":
        real_caddyfile = caddyfile.with_suffix(".real")
        caddyfile.rename(real_caddyfile)
        caddyfile.symlink_to(real_caddyfile)
    elif invalid_boundary == "prometheus-config-symlink":
        real_config = prometheus_config.with_suffix(".real")
        prometheus_config.rename(real_config)
        prometheus_config.symlink_to(real_config)
    elif invalid_boundary == "prometheus-manifest-symlink":
        real_manifest = prometheus_manifest.with_suffix(".real")
        prometheus_manifest.rename(real_manifest)
        prometheus_manifest.symlink_to(real_manifest)
    elif invalid_boundary == "secret-dir-symlink":
        real_secret_dir = project_dir / "secrets.real"
        secret_dir.rename(real_secret_dir)
        secret_dir.symlink_to(real_secret_dir, target_is_directory=True)
    elif invalid_boundary == "secret-file-symlink":
        real_secret_file = secret_dir / "pulseplate_metrics_scrape_key.real"
        secret_file.rename(real_secret_file)
        secret_file.symlink_to(real_secret_file)
    elif invalid_boundary == "secret-dir-mode":
        env["STUB_SECRET_DIR_METADATA"] = f"{os.geteuid()}:755"
    elif invalid_boundary == "secret-file-mode":
        env["STUB_SECRET_FILE_METADATA"] = f"{os.geteuid()}:400"
    elif invalid_boundary == "secret-dir-owner":
        env["STUB_SECRET_DIR_METADATA"] = "999:700"
    elif invalid_boundary == "secret-file-owner":
        env["STUB_SECRET_FILE_METADATA"] = "999:444"
    elif invalid_boundary == "helper-symlink":
        real_helper = backup_helper.with_suffix(".real")
        backup_helper.rename(real_helper)
        backup_helper.symlink_to(real_helper)
    else:
        backup_helper.chmod(0o777)
        env["STUB_HELPER_MODE"] = "777"

    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not log_file.exists()


def test_staging_deploy_readiness_probe_has_per_request_timeout() -> None:
    deploy_script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert "urlopen('http://localhost:8000/ready', timeout=5).read()" in deploy_script


def test_obs1b_deploy_scripts_keep_canonical_guard_product_first_and_non_destructive() -> None:
    staging_script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    production_script = (REPO_ROOT / "scripts" / "deploy_production.sh").read_text(encoding="utf-8")
    canonical_guard = (
        "from app.main import app; from app.security.production_invariants import "
        "assert_production_runtime_invariants; assert_production_runtime_invariants(app=app)"
    )
    for script in (staging_script, production_script):
        assert canonical_guard in script
        assert "assert_production_runtime_invariants()" not in script
        assert "|| true" not in script
        assert "down -v" not in script
        assert "volume rm" not in script
        assert "volume prune" not in script
        assert 'cat "$METRICS_SECRET_FILE"' not in script
        assert 'source "$METRICS_SECRET_FILE"' not in script
        assert script.index(canonical_guard) < script.index("alembic upgrade head")
        assert "/bin/promtool check ready" in script
        assert "/bin/promtool check healthy" in script
    assert staging_script.index("up -d --pull never caddy") < staging_script.index(
        "up -d --pull never prometheus"
    )
    assert production_script.index("up -d --remove-orphans caddy") < production_script.index(
        "up -d --pull never prometheus"
    )


@pytest.mark.parametrize("pytest_exit", (0, 23))
def test_cd_pgvector_admission_executes_complete_canonical_suite_and_propagates_failure(
    pytest_exit: int,
) -> None:
    ci = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    cd = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    canonical = next(
        step["run"]
        for step in ci["jobs"]["pgvector_compat"]["steps"]
        if step["name"] == "Prove pgvector binding, extension, and RLS compatibility"
    )
    step = cd["jobs"]["postgres-pgvector-ci-admission"]["steps"][-1]
    actual = step["run"]
    marker = "python -m pytest -q"
    assert canonical.count(marker) == actual.count(marker) == 1
    targets = shlex.split(canonical.split(marker, maxsplit=1)[1].replace("\\\n", " "))
    assert shlex.split(actual.split(marker, maxsplit=1)[1].replace("\\\n", " ")) == targets
    assert all(target.startswith("tests/") and target.endswith(".py") for target in targets)
    bash_bin = shutil.which("bash")
    assert bash_bin is not None
    prefix = (
        "set -euo pipefail\n"
        'git() { test "$*" = "rev-parse HEAD"; printf "%s\\n" "$GITHUB_SHA"; }\n'
        "python() {\n"
        '  test "$CI:$GITHUB_ACTIONS:$APP_ENV:$ENVIRONMENT:$PGVECTOR_COMPAT_REQUIRED" '
        '= "true:true:test:test:1"\n'
        '  printf "%s\\n" "$@"\n'
        '  return "$PYTEST_STUB_EXIT"\n'
        "}\n"
    )
    completed = subprocess.run(
        [bash_bin, "-c", prefix + actual],
        env={
            "PATH": os.defpath,
            **step["env"],
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
            "GITHUB_SHA": "a" * 40,
            "PYTEST_STUB_EXIT": str(pytest_exit),
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.stdout.splitlines() == ["-m", "pytest", "-q", *targets]
    assert completed.returncode == pytest_exit, completed.stderr


def test_signed_apk_index_size_exception_preserves_unrelated_file_limit() -> None:
    """The reviewed signed index must not raise the repository-wide 500KB default."""
    import re

    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text())
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"] == "check-added-large-files"
    ]
    assert len(hooks) == 2
    normal, index = hooks
    assert normal.get("args", []) == []
    assert index["args"] == ["--maxkb=2048", "--enforce-all"]
    index_path = "deploy/postgres-pgvector/builder-apk-index.tar.gz"
    for path in (index_path, index_path + ".extra", "unrelated.bin", "deploy/other/index.tar.gz"):
        selected = [
            hook
            for hook in hooks
            if re.search(hook.get("files", ""), path)
            and not re.search(hook.get("exclude", "^$"), path)
        ]
        assert len(selected) == 1
        assert (selected[0] is index) == (path == index_path)


@pytest.mark.parametrize("scenario", ["ready-after-init", "never-ready", "output-with-error"])
def test_postgres_runtime_waits_for_final_tcp_database_before_sql(
    tmp_path: Path, scenario: str
) -> None:
    """The init-only Unix server can accept connections before the database exists."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text())
    steps = workflow["jobs"]["postgres-pgvector-publish"]["steps"]
    run = next(
        step["run"]
        for step in steps
        if step.get("name") == "Prove PostgreSQL 15 pgvector 0.8.6 and same-volume continuity"
    )
    start = run.split("start_postgres() {", 1)[1].split("\n}\n", 1)[0]
    shell = shutil.which("bash")
    assert shell is not None
    # Calls one and two model the init-only server; the third exposes the final TCP DB.
    program = (
        r"""
set -euo pipefail
database_user=synthetic_user
database_password=synthetic_password
database_name=pgvector_compat
prefix=owned_prefix
sleep() { :; }
docker() {
  printf '%s\n' "$*" >> "$CALLS"
  if [ "$1" = run ]; then return 0; fi
  if [ "$1" = logs ]; then return 0; fi
  if [[ "$*" == *pg_isready* ]]; then return 0; fi
  if [[ "$*" == *'--command SELECT 1'* ]]; then
    [[ "$*" == *'--host 127.0.0.1'* ]] || return 9
    [[ "$*" == *'--dbname pgvector_compat'* ]] || return 9
    local n
    n="$(cat "$STATE")"
    n=$((n + 1))
    printf '%s' "$n" > "$STATE"
    if [ "$SCENARIO" = never-ready ]; then return 2; fi
    if [ "$SCENARIO" = output-with-error ]; then printf '1\n'; return 2; fi
    if [ "$n" -lt 3 ]; then return 2; fi
    printf '1\n'
    return 0
  fi
  return 1
}
start_postgres() {"""
        + start
        + r"""
}
start_postgres owned_container owned_volume owned_image
test "$(cat "$STATE")" = 3
"""
    )
    state = tmp_path / "state"
    state.write_text("0")
    calls = tmp_path / "calls"
    result = subprocess.run(
        [shell, "-c", program],
        env={**os.environ, "STATE": str(state), "CALLS": str(calls), "SCENARIO": scenario},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if scenario == "ready-after-init":
        assert result.returncode == 0, result.stderr
        assert calls.read_text().count("--command SELECT 1") == 3
    else:
        assert result.returncode != 0
        assert "Synthetic PostgreSQL image did not become ready" in result.stderr
        assert calls.read_text().count("--command SELECT 1") == 60
    assert "pg_isready" not in calls.read_text()


@pytest.mark.parametrize(
    "oracle,value,message",
    [
        ("STUB_ATTESTATION_STATUS", "1", "Native attestation crypto rejected"),
        ("STUB_BACKEND_IDS", "0:0", "Backend runtime user differs"),
    ],
)
def test_staging_crypto_and_passfile_owner_rejection_precede_product_mutation(
    tmp_path: Path, oracle: str, value: str, message: str
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env[oracle] = value
    backend = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend, caddy],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert message in completed.stderr
    assert all(
        " stop worker caddy app" not in line
        and " up " not in line
        and not line.startswith("backup ")
        for line in log_file.read_text().splitlines()
    )


def test_staging_backup_full_archive_failure_preserves_old_dump_and_no_publication(
    tmp_path: Path,
) -> None:
    project = tmp_path / "staging"
    project.mkdir()
    _write_stage_native_oracles(project)
    docker = tmp_path / "docker"
    _write_executable(docker, "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'FAKE_BACKUP\\n'\n")
    old = project / "backups" / "pulseplate_old.dump"
    old.write_text("preserve-old-native-dump")
    env = {
        **os.environ,
        "PROJECT_DIR": str(project),
        "BACKUP_DIR": str(old.parent),
        "COMPOSE_FILE": "docker-compose.staging.yaml",
        "DOCKER_BIN": str(docker),
        "PYTHON_BIN": sys.executable,
        "PYTHONPATH": str(REPO_ROOT),
        "POSTGRES_USER": "pulseplate",
        "POSTGRES_DB": "pulseplate",
        "STUB_PG_RESTORE_BODY_STATUS": "51",
    }
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 51
    assert "Backup created:" not in completed.stdout
    assert list(old.parent.glob("pulseplate_*.dump")) == [old]
    assert old.read_text() == "preserve-old-native-dump"
    assert not list(old.parent.glob(".pulseplate-backup.*"))


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("file.dump",),
        ("--verify-into", "pulseplate", "file.dump"),
        ("--verify-into", "arbitrary_target", "file.dump"),
    ],
)
def test_restore_requires_explicit_isolated_target_before_native_mutation(
    tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    docker = tmp_path / "docker"
    log = tmp_path / "docker.log"
    _write_executable(docker, f"#!/usr/bin/env bash\nprintf 'mutation\\n' >> '{log}'\n")
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_restore.sh"), *arguments],
        env={
            **os.environ,
            "POSTGRES_USER": "pulseplate",
            "POSTGRES_DB": "pulseplate",
            "DOCKER_BIN": str(docker),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert not log.exists()


@pytest.mark.parametrize("tls_status", [0, 61])
def test_existing_staging_passfile_authentication_precedes_all_product_stops(
    tmp_path: Path, tls_status: int
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_APPLICATION_TLS_STATUS"] = str(tls_status)
    backend = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    result = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend, caddy],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    calls = log_file.read_text().splitlines()
    tls_calls = [i for i, call in enumerate(calls) if "psycopg.connect" in call]
    assert tls_calls and "connect_timeout=10" in calls[tls_calls[0]]
    if tls_status:
        assert result.returncode == tls_status
        assert (
            "HOLD for an explicit verified credential/TLS migration before quiescence"
            in result.stderr
        )
        assert all(
            " stop " not in call and " up " not in call and not call.startswith("backup ")
            for call in calls
        )
    else:
        assert result.returncode == 0, result.stderr
        stop = next(i for i, call in enumerate(calls) if " stop worker caddy app" in call)
        assert tls_calls[0] < stop < tls_calls[-1]


def test_generic_and_staging_backup_units_keep_their_distinct_storage_contracts() -> None:
    generic = (REPO_ROOT / "deploy/systemd/pulseplate-postgres-backup.service.example").read_text()
    staging = (
        REPO_ROOT / "deploy/systemd/pulseplate-staging-postgres-backup.service.example"
    ).read_text()
    assert "COMPOSE_FILE=docker-compose.production.selfhosted.yaml" in generic
    assert "check_staging_security.py" not in generic
    assert (
        "RequiresMountsFor=/mnt/pulseplate-staging-data /srv/pulseplate-staging/secrets" in staging
    )
    assert (
        "BindsTo=mnt-pulseplate\\x2dstaging\\x2ddata.mount srv-pulseplate\\x2dstaging-secrets.mount"
        in staging
    )
    assert "COMPOSE_FILE=docker-compose.staging.yaml" in staging
    assert "--storage-only" in staging
    assert (
        "systemd/pulseplate-staging-postgres-backup.service.example"
        in (REPO_ROOT / "docs/deploy/STAGING.md").read_text()
    )


def test_verification_restore_selects_source_database_when_role_name_differs(
    tmp_path: Path,
) -> None:
    project = tmp_path / "production"
    project.mkdir()
    dump = tmp_path / "input.dump"
    dump.write_text("synthetic archive")
    docker = tmp_path / "docker"
    calls = tmp_path / "calls"
    _write_executable(
        docker,
        f'#!/usr/bin/env bash\nset -euo pipefail\nprintf "%s\\n" "$*" >> "{calls}"\n',
    )
    result = subprocess.run(
        [
            str(REPO_ROOT / "scripts/ops/postgres_restore.sh"),
            "--verify-into",
            "pulseplate_restore_check_distinct",
            str(dump),
        ],
        env={
            **os.environ,
            "PROJECT_DIR": str(project),
            "DOCKER_BIN": str(docker),
            "POSTGRES_USER": "application_role",
            "POSTGRES_DB": "application_database",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    create = next(call for call in calls.read_text().splitlines() if "createdb" in call)
    assert (
        "createdb -U application_role --maintenance-db application_database --owner application_role"
        in create
    )


@pytest.mark.parametrize("schema_shape", ["omitted", "metadata-only", "definition"])
@pytest.mark.parametrize("transaction_status", [0, 3])
def test_replacement_restore_clears_public_objects_and_asserts_inventory_in_one_transaction(
    tmp_path: Path, schema_shape: str, transaction_status: int
) -> None:
    project = tmp_path / "production"
    project.mkdir()
    dump = tmp_path / "input.dump"
    dump.write_text("synthetic archive")
    docker, calls, sql = tmp_path / "docker", tmp_path / "calls", tmp_path / "transaction.sql"
    _write_executable(
        docker, f'#!/usr/bin/env bash\nset -euo pipefail\nprintf "%s\\n" "$*" >> "{calls}"\n'
    )
    archive_list = "214; 1259 16387 TABLE public items user"
    restore_sql = "CREATE TABLE public.items(id integer);"
    if schema_shape != "omitted":
        archive_list = "5; 2615 2200 SCHEMA - public user\n" + archive_list
    if schema_shape == "definition":
        # Explicit pg_dump --schema=public has native DROP/CREATE statements.
        restore_sql = "DROP SCHEMA IF EXISTS public;\nCREATE SCHEMA public;\n" + restore_sql
    elif schema_shape == "metadata-only":
        # PostgreSQL 15.19 ordinary dumps with a non-default public owner have
        # a SCHEMA entry carrying ownership but no schema creation statement.
        restore_sql = (
            "-- *not* dropping schema, since initdb creates it\n"
            "-- *not* creating schema, since initdb creates it\n"
            "ALTER SCHEMA public OWNER TO user;\n" + restore_sql
        )
    result = subprocess.run(
        [
            str(REPO_ROOT / "scripts/ops/postgres_restore.sh"),
            "--replace-existing",
            "pulseplate",
            str(dump),
        ],
        env={
            **os.environ,
            "PROJECT_DIR": str(project),
            "DOCKER_BIN": str(docker),
            "POSTGRES_USER": "role",
            "POSTGRES_DB": "pulseplate",
            "STUB_ARCHIVE_LIST": archive_list,
            "STUB_RESTORE_SQL": restore_sql,
            "STUB_RESTORE_TRANSACTION_SQL": str(sql),
            "STUB_RESTORE_TRANSACTION_CALLS": str(calls),
            "STUB_RESTORE_TRANSACTION_STATUS": str(transaction_status),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == transaction_status, result.stderr
    rendered = sql.read_text()
    assert "DO $$ BEGIN IF EXISTS" in rendered
    assert rendered.index("DROP SCHEMA IF EXISTS public CASCADE;") < rendered.index(
        "CREATE TABLE public.items"
    )
    assert (
        "DROP SCHEMA IF EXISTS public CASCADE;\nCREATE SCHEMA public;\n" + restore_sql in rendered
    )
    assert rendered.count("CREATE SCHEMA public;") == (2 if schema_shape == "definition" else 1)
    assert rendered.index("CREATE TABLE public.items") < rendered.index(
        "Restored inventory differs"
    )
    assert "<> 1" in rendered
    assert "BEGIN;" not in rendered and "COMMIT;" not in rendered
    assert not list((project / "backups").glob(".pulseplate-restore.*"))
    if transaction_status:
        assert "Restore completed" not in result.stdout
    else:
        assert "Restore completed into: pulseplate" in result.stdout
    transaction_calls = [
        call for call in calls.read_text().splitlines() if "--single-transaction" in call
    ]
    assert len(transaction_calls) == 1 and "psql -X -q -v ON_ERROR_STOP=1" in transaction_calls[0]
    assert "--file=-" in transaction_calls[0]


@pytest.mark.parametrize(
    "failure", ["archive-schema", "archive-table", "archive-global", "target-schema", "render"]
)
def test_replacement_restore_holds_before_target_transaction_for_unsupported_or_failed_input(
    tmp_path: Path, failure: str
) -> None:
    project = tmp_path / "production"
    project.mkdir()
    dump = tmp_path / "input.dump"
    dump.write_text("synthetic archive")
    docker, sql = tmp_path / "docker", tmp_path / "transaction.sql"
    _write_executable(docker, "#!/usr/bin/env bash\nset -euo pipefail\n")
    env = {
        **os.environ,
        "PROJECT_DIR": str(project),
        "DOCKER_BIN": str(docker),
        "POSTGRES_USER": "role",
        "POSTGRES_DB": "pulseplate",
        "STUB_RESTORE_TRANSACTION_SQL": str(sql),
    }
    if failure.startswith("archive"):
        env["STUB_ARCHIVE_OUTSIDE_PUBLIC"] = {
            "archive-schema": "5; 2615 2200 SCHEMA - private role",
            "archive-table": "5; 1259 2200 TABLE private history role",
            "archive-global": "5; 0 2200 BLOB - 1234 role",
        }[failure]
    elif failure == "target-schema":
        env["STUB_TARGET_PUBLIC_ONLY"] = "f"
    else:
        env["STUB_RESTORE_RENDER_STATUS"] = "49"
    result = subprocess.run(
        [
            str(REPO_ROOT / "scripts/ops/postgres_restore.sh"),
            "--replace-existing",
            "pulseplate",
            str(dump),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not sql.exists()
    assert "Restore completed" not in result.stdout
    assert not list((project / "backups").glob(".pulseplate-restore.*"))


@pytest.mark.parametrize(
    "compose_path",
    [
        "docker-compose.staging.yaml",
        "./docker-compose.staging.yaml",
        "config/docker-compose.staging.yaml",
    ],
)
def test_reserved_staging_compose_paths_cannot_bypass_encrypted_backup_destination(
    tmp_path: Path, compose_path: str
) -> None:
    project = tmp_path / "staging"
    project.mkdir()
    _write_stage_native_oracles(project)
    docker = tmp_path / "docker"
    _write_executable(docker, "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'FAKE_BACKUP\\n'\n")
    unencrypted = tmp_path / "other-backups"
    result = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        env={
            **os.environ,
            "PROJECT_DIR": str(project) + "/",
            "COMPOSE_FILE": compose_path,
            "BACKUP_DIR": str(unencrypted),
            "DOCKER_BIN": str(docker),
            "PYTHON_BIN": sys.executable,
            "POSTGRES_USER": "role",
            "POSTGRES_DB": "database",
            "PYTHONPATH": str(REPO_ROOT),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Staging backup destination must be the admitted encrypted directory" in result.stderr
    assert not unencrypted.exists()


def test_production_custom_name_containing_staging_does_not_select_reserved_contract(
    tmp_path: Path,
) -> None:
    project = tmp_path / "production-staging-reference"
    project.mkdir()
    docker = tmp_path / "docker"
    _write_executable(docker, "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'FAKE_BACKUP\\n'\n")
    result = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        env={
            **os.environ,
            "PROJECT_DIR": str(project),
            "COMPOSE_FILE": "docker-compose.production-staging.yaml",
            "DOCKER_BIN": str(docker),
            "POSTGRES_USER": "role",
            "POSTGRES_DB": "database",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Backup created:" in result.stdout
