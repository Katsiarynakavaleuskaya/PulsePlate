#!/usr/bin/env bash
# Fail-closed staging deploy. Requires Docker Compose and two attested GHCR digests.
set -euo pipefail

STAGING_DEPLOY_CONTRACT_VERSION="4"
STAGING_DEPLOY_MARKER_CONTENT="pulseplate-staging-attested-digest-v1"
CANONICAL_IMAGE_PATTERN='^ghcr\.io/katsiarynakavaleuskaya/pulseplate@sha256:[0-9a-f]{64}$'

usage() {
  cat >&2 <<'EOF'
Usage:
  deploy.sh [--preflight-only] BACKEND_DIGEST_REF CADDY_DIGEST_REF

Both image references must use the canonical PulsePlate GHCR repository and a
lowercase sha256 digest. Floating tags are not accepted.
EOF
}

PREFLIGHT_ONLY=0
if [ "${1:-}" = "--preflight-only" ]; then
  PREFLIGHT_ONLY=1
  shift
fi

if [ "$#" -ne 2 ]; then
  usage
  exit 2
fi

BACKEND_IMAGE_REF="$1"
CADDY_IMAGE_REF="$2"

for image_ref in "$BACKEND_IMAGE_REF" "$CADDY_IMAGE_REF"; do
  if [[ ! "$image_ref" =~ $CANONICAL_IMAGE_PATTERN ]]; then
    echo "❌ Immutable canonical GHCR digest reference required: $image_ref" >&2
    exit 2
  fi
done

if [ "$BACKEND_IMAGE_REF" = "$CADDY_IMAGE_REF" ]; then
  echo "❌ Backend and Caddy image digests must be distinct" >&2
  exit 2
fi

PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-staging}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_DIR}/docker-compose.staging.yaml}"
CADDYFILE="${CADDYFILE:-${PROJECT_DIR}/Caddyfile}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
BACKUP_HELPER="${BACKUP_HELPER:-${PROJECT_DIR}/scripts/ops/postgres_backup.sh}"
STAGING_DEPLOY_MARKER="${STAGING_DEPLOY_MARKER:-${PROJECT_DIR}/.attested-digest-deploy-v1}"
PROMETHEUS_CONFIG="${PROMETHEUS_CONFIG:-${PROJECT_DIR}/prometheus/prometheus.yml}"
PROMETHEUS_IMAGE_MANIFEST="${PROMETHEUS_IMAGE_MANIFEST:-${PROJECT_DIR}/prometheus/image-manifest.json}"
POSTGRES_IMAGE_MANIFEST="${POSTGRES_IMAGE_MANIFEST:-${PROJECT_DIR}/postgres-pgvector/image-manifest.json}"
METRICS_SECRET_DIR="${METRICS_SECRET_DIR:-${PROJECT_DIR}/secrets}"
METRICS_SECRET_FILE="${METRICS_SECRET_FILE:-${METRICS_SECRET_DIR}/pulseplate_metrics_scrape_key}"

if [ -L "$STAGING_DEPLOY_MARKER" ] || [ ! -f "$STAGING_DEPLOY_MARKER" ]; then
  echo "❌ Missing regular non-symlink staging deploy marker: $STAGING_DEPLOY_MARKER" >&2
  exit 1
fi

STAT_BIN="${STAT_BIN:-}"
if [ -z "$STAT_BIN" ]; then
  STAT_BIN="$(command -v stat || :)"
fi
if [ -z "$STAT_BIN" ] || [ ! -x "$STAT_BIN" ]; then
  echo "❌ stat executable is required for staging marker validation" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for candidate in /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$candidate" ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [[ "$PYTHON_BIN" != /* ]] || [ ! -x "$PYTHON_BIN" ]; then
  echo "❌ PYTHON_BIN must resolve to an absolute executable" >&2
  exit 1
fi

marker_metadata="$($STAT_BIN -c '%u:%g:%a' "$STAGING_DEPLOY_MARKER")"
if [ "$marker_metadata" != "0:0:644" ]; then
  echo "❌ Staging deploy marker must be root-owned with mode 0644; got $marker_metadata" >&2
  exit 1
fi

marker_size="$(wc -c < "$STAGING_DEPLOY_MARKER" | tr -d '[:space:]')"
marker_content=""
IFS= read -r marker_content < "$STAGING_DEPLOY_MARKER" || [ -n "$marker_content" ]
if [ "$marker_content" != "$STAGING_DEPLOY_MARKER_CONTENT" ] || \
   [ "$marker_size" -ne "${#STAGING_DEPLOY_MARKER_CONTENT}" ]; then
  echo "❌ Staging deploy marker content mismatch" >&2
  exit 1
fi

for required_path in \
  "$ENV_FILE" \
  "$COMPOSE_FILE" \
  "$CADDYFILE" \
  "$PROMETHEUS_CONFIG" \
  "$PROMETHEUS_IMAGE_MANIFEST" \
  "$POSTGRES_IMAGE_MANIFEST"; do
  if [ -L "$required_path" ] || [ ! -f "$required_path" ]; then
    echo "❌ Staging file must be a regular non-symlink file: $required_path" >&2
    exit 1
  fi
done
env_file_mode="$($STAT_BIN -c '%a' "$ENV_FILE")"
if [ "$env_file_mode" != "600" ]; then
  echo "❌ Staging env file must use mode 0600; got $env_file_mode" >&2
  exit 1
fi
if [ -L "$BACKUP_HELPER" ] || [ ! -f "$BACKUP_HELPER" ] || [ ! -x "$BACKUP_HELPER" ]; then
  echo "❌ Postgres backup helper must be a regular executable non-symlink file: $BACKUP_HELPER" >&2
  exit 1
fi
backup_helper_mode="$($STAT_BIN -c '%a' "$BACKUP_HELPER")"
if (( (8#$backup_helper_mode & 8#22) != 0 )); then
  echo "❌ Postgres backup helper must not be group- or world-writable; got mode $backup_helper_mode" >&2
  exit 1
fi

if [ -L "$METRICS_SECRET_DIR" ] || [ ! -d "$METRICS_SECRET_DIR" ]; then
  echo "❌ Metrics scrape secret directory must be a regular non-symlink directory" >&2
  exit 1
fi
if [ -L "$METRICS_SECRET_FILE" ] || [ ! -f "$METRICS_SECRET_FILE" ]; then
  echo "❌ Metrics scrape secret must be a regular non-symlink file" >&2
  exit 1
fi
secret_dir_metadata="$($STAT_BIN -c '%u:%a' "$METRICS_SECRET_DIR")"
if [ "$secret_dir_metadata" != "${EUID}:700" ]; then
  echo "❌ Metrics scrape secret directory must be owned by the Compose account with mode 0700" >&2
  exit 1
fi
secret_file_metadata="$($STAT_BIN -c '%u:%a' "$METRICS_SECRET_FILE")"
if [ "$secret_file_metadata" != "${EUID}:444" ]; then
  echo "❌ Metrics scrape secret file must be owned by the Compose account with mode 0444" >&2
  exit 1
fi

validate_prometheus_image_manifest() {
  local manifest_path="$1"
  "$PYTHON_BIN" - "$manifest_path" <<'PY'
from __future__ import annotations

import json
import os
import re
import stat
import sys

manifest_path = sys.argv[1]
expected = {
    "schema": "pulseplate.prometheus_image_manifest.v1",
    "repository": "prom/prometheus",
    "tag": "v3.14.0-distroless",
    "index_digest": "sha256:50c707e96da5ade383cb1707790576480485e93de06aa60ad8802cb5f744bd0a",
    "platform": "linux/amd64",
    "platform_manifest_digest": "sha256:934c331c7aa29ffdb23b4befec6f34321c518453e63713d741d8ac1737c8e049",
    "runtime_ref": (
        "prom/prometheus:v3.14.0-distroless@"
        "sha256:934c331c7aa29ffdb23b4befec6f34321c518453e63713d741d8ac1737c8e049"
    ),
}


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate Prometheus manifest key")
        result[key] = value
    return result


no_follow = getattr(os, "O_NOFOLLOW", 0)
if no_follow <= 0 or not os.path.isabs(manifest_path):
    raise SystemExit("Prometheus manifest path is not a safe absolute path")
descriptor = os.open(
    manifest_path,
    os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
)
try:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > 64 * 1024
    ):
        raise SystemExit("Prometheus manifest must be one bounded regular file")
    payload = os.read(descriptor, metadata.st_size + 1)
    if len(payload) != metadata.st_size:
        raise SystemExit("Prometheus manifest changed while being read")
finally:
    os.close(descriptor)

try:
    manifest = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"invalid JSON constant: {value}")
        ),
    )
except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Prometheus manifest is malformed") from exc
if type(manifest) is not dict or set(manifest) != set(expected):
    raise SystemExit("Prometheus manifest fields do not match the closed contract")
if any(type(manifest[key]) is not str for key in expected):
    raise SystemExit("Prometheus manifest values must be strings")
if not re.fullmatch(r"sha256:[0-9a-f]{64}", manifest["index_digest"]):
    raise SystemExit("Prometheus index digest is malformed")
if not re.fullmatch(r"sha256:[0-9a-f]{64}", manifest["platform_manifest_digest"]):
    raise SystemExit("Prometheus platform digest is malformed")
derived_ref = (
    f'{manifest["repository"]}:{manifest["tag"]}@{manifest["platform_manifest_digest"]}'
)
if manifest["runtime_ref"] != derived_ref or manifest != expected:
    raise SystemExit("Prometheus manifest identity does not match the canonical record")
print(manifest["runtime_ref"])
PY
}

validate_prometheus_compose_identity() {
  local runtime_ref="$1"
  "${COMPOSE[@]}" config --format json | "$PYTHON_BIN" -c '
import json
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate rendered Compose key")
        result[key] = value
    return result

try:
    payload = json.load(sys.stdin, object_pairs_hook=reject_duplicates)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Rendered Compose JSON is malformed") from exc
services = payload.get("services") if type(payload) is dict else None
prometheus = services.get("prometheus") if type(services) is dict else None
if type(prometheus) is not dict:
    raise SystemExit("Rendered Compose must define exactly one Prometheus service")
if prometheus.get("image") != sys.argv[1] or prometheus.get("platform") != "linux/amd64":
    raise SystemExit("Rendered Compose Prometheus identity does not match the manifest")
' "$runtime_ref"
}

validate_postgres_image_manifest() {
  local manifest_path="$1"
  "$PYTHON_BIN" - "$manifest_path" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys

manifest_path = sys.argv[1]
expected_file_sha256 = "97cfcc5896bf687ced40c56a983dfaacda81ce891e4b656736dc8cf3cac4d9bd"  # pragma: allowlist secret
expected_keys = set(
    """
    schema repository tag platform platform_manifest_digest config_digest runtime_ref
    source_date_epoch containerfile_sha256 runtime_base_repository runtime_base_tag
    runtime_base_index_digest runtime_base_platform_manifest_digest runtime_base_config_digest
    builder_base_repository builder_base_tag builder_base_index_digest
    builder_base_platform_manifest_digest builder_base_config_digest legacy_repository
    legacy_tag legacy_index_digest legacy_platform_manifest_digest legacy_config_digest
    postgres_major postgres_version runtime_user runtime_entrypoint runtime_default_pgdata
    compose_pgdata compose_volume_target pgvector_version pgvector_source_commit
    pgvector_source_url pgvector_source_sha256 builder_packages builder_apk_closure_count
    builder_apk_closure_sha256 pg_config_path pg_config_version make_jobs optflags
    runtime_artifact_count runtime_artifact_inventory_sha256 trivy_version
    mountpoint_layer_schema mountpoint_layer_digest mountpoint_layer_size
    mountpoint_layer_diff_id mountpoint_layer_entry_count mountpoint_uid mountpoint_gid
    mountpoint_mode mountpoint_path mountpoint_leaf_empty
    mountpoint_base_parent_metadata_equal trivy_linux_archive_sha256 trivy_scan_contract
    """.split()
)
expected_values = {
    "schema": "pulseplate.postgres_pgvector_image_manifest.v1",
    "repository": "ghcr.io/katsiarynakavaleuskaya/pulseplate",
    "tag": "postgres-15.19-pgvector0.8.6-alpine3.23",
    "platform": "linux/amd64",
    "platform_manifest_digest": "sha256:ca0968c51a9af5d873c1053af0fdbf6e96f20fa4995bb0b98bfc3df47371d0ec",
    "config_digest": "sha256:bf19b760177b04d255691b4d793493b158240836e78afbb17904a8b385db7738",
    "runtime_user": "70",
    "runtime_entrypoint": "/usr/local/bin/docker-entrypoint.sh",
    "runtime_default_pgdata": "/var/lib/postgresql/15/data",
    "compose_pgdata": "/var/lib/postgresql/data",
    "compose_volume_target": "/var/lib/postgresql/data",
    "postgres_major": "15",
    "postgres_version": "15.19",
    "pgvector_version": "0.8.6",
    "mountpoint_layer_schema": "pulseplate.pgvector_mountpoint_layer.v1",
    "mountpoint_layer_digest": "sha256:f5a1938bd1dfbe02232ddc8fad542445d8369541f3ebcacd5892c4e52abab124",
    "mountpoint_layer_size": "154",
    "mountpoint_layer_diff_id": "sha256:830c8272961c65f32876a884f52d80ad05cc4534a37bd0ecd4dafcf155f656fc",
    "mountpoint_layer_entry_count": "4",
    "mountpoint_uid": "70",
    "mountpoint_gid": "70",
    "mountpoint_mode": "0700",
    "mountpoint_path": "/var/lib/postgresql/data",
    "mountpoint_leaf_empty": "true",
    "mountpoint_base_parent_metadata_equal": "true",
    "trivy_version": "0.74.0",
    "trivy_scan_contract": "vuln,secret;os,library;HIGH,CRITICAL;exit=1;suppressions=none",
}


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate PostgreSQL image manifest key")
        result[key] = value
    return result


no_follow = getattr(os, "O_NOFOLLOW", 0)
if no_follow <= 0 or not os.path.isabs(manifest_path):
    raise SystemExit("PostgreSQL image manifest path is not one safe absolute path")
descriptor = os.open(
    manifest_path,
    os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
)
try:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > 64 * 1024
    ):
        raise SystemExit("PostgreSQL image manifest must be one bounded regular file")
    payload = os.read(descriptor, metadata.st_size + 1)
    if len(payload) != metadata.st_size:
        raise SystemExit("PostgreSQL image manifest changed while being read")
finally:
    os.close(descriptor)

if hashlib.sha256(payload).hexdigest() != expected_file_sha256:
    raise SystemExit("PostgreSQL image manifest bytes do not match the frozen contract")
try:
    manifest = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"invalid JSON constant: {value}")
        ),
    )
except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("PostgreSQL image manifest is malformed") from exc
if type(manifest) is not dict or set(manifest) != expected_keys:
    raise SystemExit("PostgreSQL image manifest fields do not match the closed contract")
if any(type(value) is not str for value in manifest.values()):
    raise SystemExit("PostgreSQL image manifest values must be strings")
if any(manifest[key] != value for key, value in expected_values.items()):
    raise SystemExit("PostgreSQL image manifest identity does not match the canonical record")
for key in (
    "platform_manifest_digest",
    "config_digest",
    "containerfile_sha256",
    "runtime_base_index_digest",
    "runtime_base_platform_manifest_digest",
    "runtime_base_config_digest",
    "builder_base_index_digest",
    "builder_base_platform_manifest_digest",
    "builder_base_config_digest",
    "legacy_index_digest",
    "legacy_platform_manifest_digest",
    "legacy_config_digest",
    "pgvector_source_sha256",
    "builder_apk_closure_sha256",
    "runtime_artifact_inventory_sha256",
    "mountpoint_layer_digest",
    "mountpoint_layer_diff_id",
    "trivy_linux_archive_sha256",
):
    if re.fullmatch(r"sha256:[0-9a-f]{64}", manifest[key]) is None:
        raise SystemExit(f"PostgreSQL image manifest digest is malformed: {key}")
derived_ref = (
    f'{manifest["repository"]}:{manifest["tag"]}@'
    f'{manifest["platform_manifest_digest"]}'
)
if manifest["runtime_ref"] != derived_ref:
    raise SystemExit("PostgreSQL runtime reference is not manifest-digest bound")
print(manifest["runtime_ref"])
PY
}

validate_postgres_compose_identity() {
  local runtime_ref="$1"
  "${COMPOSE[@]}" config --format json | "$PYTHON_BIN" -c '
import json
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate rendered Compose key")
        result[key] = value
    return result

try:
    payload = json.load(sys.stdin, object_pairs_hook=reject_duplicates)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Rendered Compose JSON is malformed") from exc
services = payload.get("services") if type(payload) is dict else None
postgres = services.get("postgres") if type(services) is dict else None
if type(postgres) is not dict:
    raise SystemExit("Rendered staging Compose must define exactly one PostgreSQL service")
if postgres.get("image") != sys.argv[1] or postgres.get("platform") != "linux/amd64":
    raise SystemExit("Rendered staging PostgreSQL identity does not match the manifest")
environment = postgres.get("environment")
if type(environment) is not dict or environment.get("PGDATA") != "/var/lib/postgresql/data":
    raise SystemExit("Rendered staging PostgreSQL PGDATA does not preserve the legacy volume root")
volumes = postgres.get("volumes")
if type(volumes) is not list:
    raise SystemExit("Rendered staging PostgreSQL volumes are malformed")
data_mounts = [
    item
    for item in volumes
    if type(item) is dict and item.get("target") == "/var/lib/postgresql/data"
]
if len(data_mounts) != 1 or data_mounts[0].get("type") != "volume":
    raise SystemExit("Rendered staging PostgreSQL must use one named data volume")
if postgres.get("ports") not in (None, []):
    raise SystemExit("Rendered staging PostgreSQL must not publish a host port")
' "$runtime_ref"
}

validate_pulled_postgres_image() {
  local runtime_ref="$1"
  local platform_digest="${runtime_ref##*@}"
  "$DOCKER_BIN" image inspect "$runtime_ref" | "$PYTHON_BIN" -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("PostgreSQL image inspect JSON is malformed") from exc
if type(payload) is not list or len(payload) != 1 or type(payload[0]) is not dict:
    raise SystemExit("PostgreSQL image inspect must return exactly one image")
record = payload[0]
config = record.get("Config")
if type(config) is not dict:
    raise SystemExit("PostgreSQL image config is malformed")
if record.get("Os") != "linux" or record.get("Architecture") != "amd64":
    raise SystemExit("Pulled PostgreSQL image platform is not linux/amd64")
if config.get("User") != "70" or config.get("Entrypoint") != ["/usr/local/bin/docker-entrypoint.sh"]:
    raise SystemExit("Pulled PostgreSQL image runtime identity is not canonical")
environment = config.get("Env")
required_environment = {
    "PGDATA=/var/lib/postgresql/15/data",
    "PG_MAJOR=15",
    "PG_MINOR=19",
}

if type(environment) is not list or not required_environment.issubset(environment):
    raise SystemExit("Pulled PostgreSQL image version or default PGDATA drifted")
labels = config.get("Labels")
required_labels = {
    "com.pulseplate.pgvector.version": "0.8.6",
    "com.pulseplate.pgvector.source-commit": "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c",
    "com.pulseplate.postgres.base-manifest": "sha256:eb42371d95afbeda8d559979fcfa11efc1416d2991551f05181522cda64561ee",
}
if type(labels) is not dict or any(labels.get(key) != value for key, value in required_labels.items()):
    raise SystemExit("Pulled PostgreSQL image labels do not match the closed build")
repo_digests = record.get("RepoDigests")
expected = f"ghcr.io/katsiarynakavaleuskaya/pulseplate@{sys.argv[1]}"
if type(repo_digests) is not list or expected not in repo_digests:
    raise SystemExit("Pulled PostgreSQL image is not bound to the canonical GHCR digest")
' "$platform_digest"
}

validate_pulled_postgres_mountpoint() {
  local runtime_ref="$1"
  "$DOCKER_BIN" run --rm \
    --platform linux/amd64 \
    --user 70:70 \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --entrypoint /bin/sh \
    "$runtime_ref" \
    -ec 'test "$(stat -c "%u:%g:%a" /var/lib/postgresql/data)" = "70:70:700"; test -z "$(find /var/lib/postgresql/data -mindepth 1 -print -quit)"'
}

read_rendered_postgres_volume_name() {
  "${COMPOSE[@]}" config --format json | "$PYTHON_BIN" -c '
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Rendered Compose JSON is malformed") from exc
volumes = payload.get("volumes") if type(payload) is dict else None
postgres_data = volumes.get("postgres_data") if type(volumes) is dict else None
name = postgres_data.get("name") if type(postgres_data) is dict else None
if type(name) is not str or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", name) is None:
    raise SystemExit("Rendered PostgreSQL volume identity is missing or malformed")
print(name)
'
}

read_existing_postgres_state() {
  local container_id="$1"
  "$DOCKER_BIN" inspect "$container_id" | "$PYTHON_BIN" -c '
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Existing PostgreSQL container inspect JSON is malformed") from exc
if type(payload) is not list or len(payload) != 1 or type(payload[0]) is not dict:
    raise SystemExit("Existing PostgreSQL inspect must return exactly one container")
record = payload[0]
state = record.get("State")
config = record.get("Config")
mounts = record.get("Mounts")
if type(state) is not dict or state.get("Running") is not True:
    raise SystemExit("Existing PostgreSQL container must be running")
health = state.get("Health")
if type(health) is not dict or health.get("Status") != "healthy":
    raise SystemExit("Existing PostgreSQL container must be healthy")
if type(config) is not dict or type(config.get("Image")) is not str:
    raise SystemExit("Existing PostgreSQL configured image is malformed")
environment = config.get("Env")
if type(environment) is not list or any(type(item) is not str for item in environment):
    raise SystemExit("Existing PostgreSQL environment is malformed")
pgdata_values = [item.removeprefix("PGDATA=") for item in environment if item.startswith("PGDATA=")]
if pgdata_values != ["/var/lib/postgresql/data"]:
    raise SystemExit("Existing PostgreSQL must have one exact PGDATA value")
if type(mounts) is not list:
    raise SystemExit("Existing PostgreSQL mounts are malformed")
data_mounts = [item for item in mounts if type(item) is dict and item.get("Destination") == "/var/lib/postgresql/data"]
if len(data_mounts) != 1:
    raise SystemExit("Existing PostgreSQL must have one exact data mount")
mount = data_mounts[0]
if (
    mount.get("Type") != "volume"
    or type(mount.get("Name")) is not str
    or mount.get("RW") is not True
):
    raise SystemExit("Existing PostgreSQL data mount must be one named volume")
container = record.get("Id")
image_id = record.get("Image")
if type(container) is not str or re.fullmatch(r"[0-9a-f]{12,64}", container) is None:
    raise SystemExit("Existing PostgreSQL container ID is malformed")
if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
    raise SystemExit("Existing PostgreSQL image ID is malformed")
print("\t".join((container, image_id, config["Image"], pgdata_values[0], mount["Name"])))
'
}

validate_existing_postgres_image_identity() {
  local image_id="$1"
  local configured_image="$2"
  case "$configured_image" in
    postgres:15-alpine | docker.io/library/postgres:15-alpine | \
      postgres:15-alpine@sha256:a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181 | \
      docker.io/library/postgres:15-alpine@sha256:a2c20749c564b4eb73a77bfda626f8a3cde1bbfae020fb97c616a00cdc1a2181)
      if [ "$image_id" != "sha256:aad6289ca337b3ce76896f2e7e61480490152886c7828120371fb28e6b779e1d" ]; then
        echo "❌ Existing legacy PostgreSQL image ID does not match the frozen predecessor" >&2
        return 1
      fi
      ;;
    "$POSTGRES_RUNTIME_REF")
      if [ "$image_id" != "sha256:da9e5626437d31f000dfd0460332d7194626439123f6ceb87fb9802cc4d165fa" ]; then
        echo "❌ Existing current PostgreSQL image ID does not match the frozen candidate" >&2
        return 1
      fi
      ;;
    *)
      echo "❌ Existing PostgreSQL configured image is outside the closed transition set" >&2
      return 1
      ;;
  esac
}

read_existing_postgres_runtime_state() {
  local container_id="$1"
  "$DOCKER_BIN" exec "$container_id" sh -ec '
postgres_uid="$(id -u postgres)"
server_version_num="$(psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --quiet --command "SHOW server_version_num")"
data_directory="$(psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --quiet --command "SHOW data_directory")"
test "$postgres_uid" = "70"
test "$server_version_num" = "150019"
test "$data_directory" = "/var/lib/postgresql/data"
printf "%s\t%s\t%s\n" "$postgres_uid" "$server_version_num" "$data_directory"
'
}

assert_existing_postgres_unchanged() {
  local expected_state="$1"
  local expected_runtime="$2"
  local current_container=""
  current_container="$("${COMPOSE[@]}" ps -q postgres | tr -d '\r')"
  if [ -z "$current_container" ] || [[ "$current_container" == *$'\n'* ]]; then
    echo "❌ Existing PostgreSQL container identity changed during transition" >&2
    return 1
  fi
  if [ "$(read_existing_postgres_state "$current_container")" != "$expected_state" ]; then
    echo "❌ Existing PostgreSQL container/image/volume identity drifted" >&2
    return 1
  fi
  if [ "$(read_existing_postgres_runtime_state "$current_container")" != "$expected_runtime" ]; then
    echo "❌ Existing PostgreSQL runtime identity drifted" >&2
    return 1
  fi
}

capture_running_service_container() {
  local service="$1"
  local container_id=""
  container_id="$("${COMPOSE[@]}" ps -q "$service" | tr -d '\r')"
  if [[ "$container_id" == *$'\n'* ]]; then
    echo "❌ Expected at most one ${service} container" >&2
    return 1
  fi
  if [ -z "$container_id" ]; then
    return 0
  fi
  if [ "$($DOCKER_BIN inspect --format '{{.State.Running}}' "$container_id")" = "true" ]; then
    printf '%s\n' "$container_id"
  fi
}

restart_captured_product_containers() {
  local cleanup_failed=0
  local container_id
  for container_id in "$CAPTURED_APP_ID" "$CAPTURED_CADDY_ID" "$CAPTURED_WORKER_ID"; do
    if [ -n "$container_id" ]; then
      if ! "$DOCKER_BIN" start "$container_id" >/dev/null; then
        cleanup_failed=1
      fi
    fi
  done
  return "$cleanup_failed"
}

restart_captured_product_containers_after_failure() {
  if ! restart_captured_product_containers; then
    echo "❌ Restart of one or more captured product containers also failed; preserving primary exit" >&2
  fi
  return 0
}

validate_backup_receipt() {
  local backup_output="$1"
  local postgres_container_id="$2"
  local backup_path="${backup_output##*Backup created: }"
  if [ "$backup_path" = "$backup_output" ] || [[ "$backup_path" != "$BACKUP_DIR"/pulseplate_*.dump ]]; then
    echo "❌ Postgres backup helper did not return one bounded receipt" >&2
    return 1
  fi
  if [ -L "$backup_path" ] || [ ! -f "$backup_path" ] || [ ! -s "$backup_path" ]; then
    echo "❌ Postgres backup receipt must be one nonempty regular non-symlink file" >&2
    return 1
  fi
  local backup_mode
  backup_mode="$($STAT_BIN -c '%a' "$backup_path")"
  if [ "$backup_mode" != "600" ]; then
    echo "❌ Postgres backup receipt must use mode 0600; got $backup_mode" >&2
    return 1
  fi
  if ! "$DOCKER_BIN" exec -i "$postgres_container_id" pg_restore --list \
      < "$backup_path" >/dev/null; then
    echo "❌ Postgres backup receipt is not a listable custom-format dump" >&2
    return 1
  fi
  local receipt_metadata
  receipt_metadata="$("$PYTHON_BIN" - "$backup_path" <<'PY'
import hashlib
import os
import stat
import sys

descriptor = os.open(sys.argv[1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
try:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size <= 0:
        raise SystemExit("backup receipt metadata drifted")
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
finally:
    os.close(descriptor)
print(f"size={metadata.st_size} sha256={digest.hexdigest()}")
PY
)"
  printf 'Verified PostgreSQL backup metadata: %s\n' "$receipt_metadata" >&2
  printf '%s\n' "$backup_path"
}

validate_pulled_prometheus_image() {
  local runtime_ref="$1"
  "$DOCKER_BIN" image inspect "$runtime_ref" | "$PYTHON_BIN" -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except (TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit("Prometheus image inspect JSON is malformed") from exc
if type(payload) is not list or len(payload) != 1 or type(payload[0]) is not dict:
    raise SystemExit("Prometheus image inspect must return exactly one image")
record = payload[0]
repo_digests = record.get("RepoDigests")
allowed = {
    f"prom/prometheus@{sys.argv[1]}",
    f"docker.io/prom/prometheus@{sys.argv[1]}",
}
if record.get("Os") != "linux" or record.get("Architecture") != "amd64":
    raise SystemExit("Pulled Prometheus image platform is not linux/amd64")
if type(repo_digests) is not list or any(type(item) is not str for item in repo_digests):
    raise SystemExit("Pulled Prometheus RepoDigests are malformed")
if not allowed.intersection(repo_digests):
    raise SystemExit("Pulled Prometheus image is not bound to the canonical platform digest")
' "$PROMETHEUS_PLATFORM_MANIFEST_DIGEST"
}

export STAGING_IMAGE_REF="$BACKEND_IMAGE_REF"
export STAGING_CADDY_IMAGE_REF="$CADDY_IMAGE_REF"
export STAGING_ENV_FILE="$ENV_FILE"

scheduler_mode_seen=0
scheduler_mode=""
if [ "${FOOD_UPDATE_SCHEDULER_MODE+x}" = "x" ]; then
  scheduler_mode="$FOOD_UPDATE_SCHEDULER_MODE"
  scheduler_mode_seen=1
else
  env_line=""
  while IFS= read -r env_line || [ -n "$env_line" ]; do
    case "$env_line" in
      FOOD_UPDATE_SCHEDULER_MODE=*)
        if [ "$scheduler_mode_seen" -eq 1 ]; then
          echo "❌ Duplicate FOOD_UPDATE_SCHEDULER_MODE entries in staging env file" >&2
          exit 1
        fi
        raw_scheduler_mode="${env_line#*=}"
        if [[ "$raw_scheduler_mode" =~ ^[[:space:]]*(external|disabled|in_process_dev)[[:space:]]*$ ]] || \
           [[ "$raw_scheduler_mode" =~ ^[[:space:]]*(external|disabled|in_process_dev)[[:space:]]+\#.*$ ]]; then
          scheduler_mode="${BASH_REMATCH[1]}"
        else
          scheduler_mode="$raw_scheduler_mode"
        fi
        scheduler_mode_seen=1
        ;;
    esac
  done < "$ENV_FILE"
fi
if [ "$scheduler_mode_seen" -eq 0 ]; then
  scheduler_mode="external"
fi
case "$scheduler_mode" in
  external|disabled)
    ;;
  in_process_dev)
    echo "❌ Staging deploy forbids FOOD_UPDATE_SCHEDULER_MODE=in_process_dev" >&2
    exit 1
    ;;
  *)
    echo "❌ FOOD_UPDATE_SCHEDULER_MODE must be exactly external or disabled" >&2
    exit 1
    ;;
esac
FOOD_UPDATE_SCHEDULER_MODE="$scheduler_mode"
export FOOD_UPDATE_SCHEDULER_MODE

STAGING_DOMAIN=${STAGING_DOMAIN:?"STAGING_DOMAIN not set"}

DOCKER_BIN="${DOCKER_BIN:-}"
if [ -z "$DOCKER_BIN" ]; then
  DOCKER_BIN="$(command -v docker || :)"
fi
if [ -z "$DOCKER_BIN" ] || [ ! -x "$DOCKER_BIN" ]; then
  echo "❌ docker executable is required" >&2
  exit 1
fi

COMPOSE=("$DOCKER_BIN" compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

PROMETHEUS_RUNTIME_REF="$(validate_prometheus_image_manifest "$PROMETHEUS_IMAGE_MANIFEST")"
readonly PROMETHEUS_RUNTIME_REF
PROMETHEUS_PLATFORM_MANIFEST_DIGEST="${PROMETHEUS_RUNTIME_REF##*@}"
readonly PROMETHEUS_PLATFORM_MANIFEST_DIGEST
POSTGRES_RUNTIME_REF="$(validate_postgres_image_manifest "$POSTGRES_IMAGE_MANIFEST")"
readonly POSTGRES_RUNTIME_REF

docker_architecture="$($DOCKER_BIN info --format '{{.Architecture}}')"
case "$docker_architecture" in
  amd64|x86_64) ;;
  *)
    echo "❌ Staging artifacts are linux/amd64 only; host reports $docker_architecture" >&2
    exit 1
    ;;
esac

"${COMPOSE[@]}" config --quiet
validate_prometheus_compose_identity "$PROMETHEUS_RUNTIME_REF"
validate_postgres_compose_identity "$POSTGRES_RUNTIME_REF"
POSTGRES_VOLUME_NAME="$(read_rendered_postgres_volume_name)"
readonly POSTGRES_VOLUME_NAME

if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  echo "✅ Staging deploy preflight passed (contract v${STAGING_DEPLOY_CONTRACT_VERSION})"
  exit 0
fi

GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}

CURL_BIN="${CURL_BIN:-}"
if [ -z "$CURL_BIN" ]; then
  CURL_BIN="$(command -v curl || :)"
fi
if [ -z "$CURL_BIN" ] || [ ! -x "$CURL_BIN" ]; then
  echo "❌ curl executable is required" >&2
  exit 1
fi

umask 077
DOCKER_CONFIG="$(mktemp -d "${TMPDIR:-/tmp}/pulseplate-docker-config.XXXXXX")"
export DOCKER_CONFIG
cleanup() {
  local original_status=$?
  local cleanup_failed=0
  trap - EXIT
  case "$DOCKER_CONFIG" in
    "${TMPDIR:-/tmp}"/pulseplate-docker-config.*)
      if [ -d "$DOCKER_CONFIG" ] && [ ! -L "$DOCKER_CONFIG" ]; then
        if ! rm -rf -- "$DOCKER_CONFIG"; then
          cleanup_failed=1
        fi
      else
        echo "❌ Refusing cleanup for an unsafe Docker credential path" >&2
        cleanup_failed=1
      fi
      ;;
    *)
      echo "❌ Refusing cleanup for an unbounded Docker credential path" >&2
      cleanup_failed=1
      ;;
  esac
  if [ "$original_status" -eq 0 ] && [ "$cleanup_failed" -ne 0 ]; then
    original_status=1
  elif [ "$original_status" -ne 0 ] && [ "$cleanup_failed" -ne 0 ]; then
    echo "❌ Docker credential cleanup also failed; preserving primary exit $original_status" >&2
  fi
  exit "$original_status"
}
trap cleanup EXIT

HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-30}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

echo "[1/5] Login to GHCR with temporary credentials"
printf '%s' "$GHCR_TOKEN" | "$DOCKER_BIN" login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/5] Pull exact backend, Caddy, PostgreSQL, and Prometheus digests"
"${COMPOSE[@]}" pull app caddy postgres prometheus
echo "Pull scheduler worker from the exact backend digest"
"${COMPOSE[@]}" pull worker
echo "Validating the pulled Prometheus platform manifest before product mutation"
validate_pulled_prometheus_image "$PROMETHEUS_RUNTIME_REF"
echo "Validating the pulled PostgreSQL platform manifest before product mutation"
validate_pulled_postgres_image "$POSTGRES_RUNTIME_REF"
echo "Validating the pulled PostgreSQL empty UID 70 mountpoint before product mutation"
validate_pulled_postgres_mountpoint "$POSTGRES_RUNTIME_REF"
"$DOCKER_BIN" logout ghcr.io >/dev/null
if [ -L "$DOCKER_CONFIG/config.json" ]; then
  echo "❌ Docker credential file became a symlink" >&2
  exit 1
fi
rm -f -- "$DOCKER_CONFIG/config.json"
unset GHCR_TOKEN GHCR_USER

echo "Validating the exact Prometheus configuration before product mutation"
"${COMPOSE[@]}" run --rm --no-deps --entrypoint /bin/promtool prometheus \
  check config --syntax-only /etc/prometheus/prometheus.yml

echo "Invoking the canonical application production invariant before product mutation"
"${COMPOSE[@]}" run --rm --no-deps app python -c \
  'from app.main import app; from app.security.production_invariants import assert_production_runtime_invariants; assert_production_runtime_invariants(app=app)'

echo "[3/5] Census and quiesce the current product before PostgreSQL transition"
CAPTURED_WORKER_ID="$(capture_running_service_container worker)"
CAPTURED_CADDY_ID="$(capture_running_service_container caddy)"
CAPTURED_APP_ID="$(capture_running_service_container app)"
readonly CAPTURED_WORKER_ID CAPTURED_CADDY_ID CAPTURED_APP_ID

postgres_container_raw="$("${COMPOSE[@]}" ps -q postgres | tr -d '\r')"
if [[ "$postgres_container_raw" == *$'\n'* ]]; then
  echo "❌ Expected at most one existing PostgreSQL container" >&2
  exit 1
fi
postgres_transition="fresh"
postgres_container=""
postgres_image_id=""
postgres_configured_image=""
postgres_pgdata=""
postgres_volume=""
postgres_state_receipt=""
postgres_runtime_receipt=""
if [ -n "$postgres_container_raw" ]; then
  postgres_transition="existing"
  postgres_state_receipt="$(read_existing_postgres_state "$postgres_container_raw")"
  IFS=$'\t' read -r postgres_container postgres_image_id postgres_configured_image \
    postgres_pgdata postgres_volume <<< "$postgres_state_receipt"
  validate_existing_postgres_image_identity "$postgres_image_id" "$postgres_configured_image"
  postgres_runtime_receipt="$(read_existing_postgres_runtime_state "$postgres_container")"
  if [ "$postgres_volume" != "$POSTGRES_VOLUME_NAME" ]; then
    echo "❌ Existing PostgreSQL volume does not match rendered Compose identity" >&2
    exit 1
  fi
else
  if "$DOCKER_BIN" volume inspect "$POSTGRES_VOLUME_NAME" >/dev/null 2>&1; then
    echo "❌ PostgreSQL volume exists without one trustworthy running container; HOLD" >&2
    exit 1
  fi
fi

if "${COMPOSE[@]}" stop worker caddy app; then
  :
else
  transition_status=$?
  restart_captured_product_containers_after_failure
  exit "$transition_status"
fi

if [ "$postgres_transition" = "existing" ]; then
  if assert_existing_postgres_unchanged "$postgres_state_receipt" "$postgres_runtime_receipt"; then
    :
  else
    identity_status=$?
    echo "❌ PostgreSQL identity revalidation failed; captured product writers remain quiesced" >&2
    exit "$identity_status"
  fi
  echo "Creating a verified backup from the still-running old PostgreSQL container"
  backup_output=""
  if backup_output="$(
      export DOCKER_BIN BACKUP_DIR PROJECT_DIR COMPOSE_FILE
      "$BACKUP_HELPER"
    )"; then
    :
  else
    backup_status=$?
    restart_captured_product_containers_after_failure
    exit "$backup_status"
  fi
  if backup_receipt="$(validate_backup_receipt "$backup_output" "$postgres_container")"; then
    :
  else
    receipt_status=$?
    restart_captured_product_containers_after_failure
    exit "$receipt_status"
  fi
  if assert_existing_postgres_unchanged "$postgres_state_receipt" "$postgres_runtime_receipt"; then
    :
  else
    identity_status=$?
    echo "❌ PostgreSQL identity revalidation failed; captured product writers remain quiesced" >&2
    exit "$identity_status"
  fi
  echo "Verified pre-transition backup receipt: $backup_receipt"
  if "$DOCKER_BIN" stop "$postgres_container" >/dev/null; then
    :
  else
    stop_status=$?
    echo "❌ PostgreSQL stop failed ambiguously; captured product writers remain quiesced" >&2
    exit "$stop_status"
  fi
else
  echo "Fresh PostgreSQL path admitted: rendered named volume is absent"
fi

echo "Starting the already pulled exact PostgreSQL candidate without registry access"
"${COMPOSE[@]}" up -d --pull never postgres

max_wait=60
wait_count=0
while [ "$wait_count" -lt "$max_wait" ]; do
  postgres_container="$("${COMPOSE[@]}" ps -q postgres | tr -d '\n\r ')"
  postgres_health="unknown"
  if [ -n "$postgres_container" ]; then
    if inspected_health="$($DOCKER_BIN inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$postgres_container" 2>/dev/null)"; then
      postgres_health="$inspected_health"
    fi
  fi
  if [ -n "$postgres_container" ] && [ "$postgres_health" = "healthy" ]; then
    echo "Postgres is healthy"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for postgres... ($wait_count/$max_wait)"
  sleep 1
done

if [ "$wait_count" -eq "$max_wait" ]; then
  echo "❌ Postgres failed to become healthy within $max_wait seconds" >&2
  exit 1
fi

echo "[4/5] Run migrations while public traffic and writers remain quiesced"

echo "Running database migrations in a one-shot container"
if "${COMPOSE[@]}" run --rm --no-deps app alembic upgrade head; then
  echo "✅ Database migrations completed successfully"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed (exit code: $migration_exit_code)" >&2
  echo "Caddy and app remain stopped; restore the pre-migration backup before retrying if needed" >&2
  exit "$migration_exit_code"
fi

echo "Starting app after successful migrations"
"${COMPOSE[@]}" up -d --pull never app

max_wait=30
wait_count=0
app_container=""
while [ "$wait_count" -lt "$max_wait" ]; do
  app_container="$("${COMPOSE[@]}" ps -q app | tr -d '\n\r ')"
  if [ -n "$app_container" ] && \
     "$DOCKER_BIN" exec "$app_container" python -c \
       "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=5).read()" \
       2>/dev/null; then
    echo "App is ready"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app readiness... ($wait_count/$max_wait)"
  sleep 1
done

if [ "$wait_count" -eq "$max_wait" ]; then
  echo "❌ App failed to become ready within $max_wait seconds" >&2
  exit 1
fi

if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then
  echo "Starting scheduler worker after app readiness"
  "${COMPOSE[@]}" up -d --pull never --wait --wait-timeout 30 worker
else
  echo "Scheduler mode is disabled; worker container remains absent"
  "${COMPOSE[@]}" rm -f worker
fi

echo "[5/5] Start Caddy after successful migrations"
"${COMPOSE[@]}" up -d --pull never caddy

DOMAIN="$STAGING_DOMAIN"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=0

echo "Diagnostic HTTP smoke check..."
if "$CURL_BIN" -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" \
  --max-time "$HEALTH_CURL_MAX_TIME_S"; then
  :
else
  echo "⚠️  HTTP redirect diagnostic failed; continuing to the required HTTPS check" >&2
fi

while [ "$attempt" -lt "$HEALTH_MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$HEALTH_MAX_ATTEMPTS..."
  if curl_output="$("$CURL_BIN" -fsS --max-time "$HEALTH_CURL_MAX_TIME_S" \
    "$HEALTH_URL" --resolve "${DOMAIN}:443:127.0.0.1" 2>&1)"; then
    echo "✅ Health check successful"
    break
  else
    curl_exit_code=$?
    echo "❌ Health check failed (exit code: $curl_exit_code)" >&2
    echo "Error details: $curl_output" >&2
    if [ "$attempt" -eq "$HEALTH_MAX_ATTEMPTS" ]; then
      echo "❌ Health check failed after ${HEALTH_MAX_ATTEMPTS} attempts" >&2
      exit 1
    fi
    sleep "$HEALTH_SLEEP_S"
  fi
done

if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then
  echo "Confirming scheduler worker process is running"
  "${COMPOSE[@]}" up -d --pull never --no-recreate --wait --wait-timeout 30 worker
fi

echo "Starting Prometheus after complete product health"
if "${COMPOSE[@]}" up -d --pull never prometheus; then
  :
else
  prometheus_start_status=$?
  echo "❌ Prometheus failed to start; app and Caddy remain running" >&2
  exit "$prometheus_start_status"
fi

prometheus_attempt=0
prometheus_ready=0
while [ "$prometheus_attempt" -lt "$HEALTH_MAX_ATTEMPTS" ]; do
  prometheus_attempt=$((prometheus_attempt + 1))
  if "${COMPOSE[@]}" exec -T prometheus /bin/promtool check ready \
      --url=http://localhost:9090 >/dev/null 2>&1 && \
     "${COMPOSE[@]}" exec -T prometheus /bin/promtool check healthy \
      --url=http://localhost:9090 >/dev/null 2>&1; then
    prometheus_ready=1
    break
  fi
  echo "Waiting for Prometheus readiness... ($prometheus_attempt/$HEALTH_MAX_ATTEMPTS)"
  if [ "$prometheus_attempt" -lt "$HEALTH_MAX_ATTEMPTS" ]; then
    sleep "$HEALTH_SLEEP_S"
  fi
done

if [ "$prometheus_ready" -ne 1 ]; then
  echo "❌ Prometheus telemetry readiness failed; app and Caddy remain running and prometheus_data is preserved" >&2
  exit 1
fi

echo "✅ Staging deployed by attested digests"
echo "Backend: $BACKEND_IMAGE_REF"
echo "Caddy:   $CADDY_IMAGE_REF"
