#!/usr/bin/env bash
set -euo pipefail

MODE="deploy"
if [ "$#" -gt 1 ]; then
  echo "❌ Usage: $0 [--preflight-only]" >&2
  exit 1
fi
if [ "$#" -eq 1 ]; then
  case "$1" in
    --preflight-only)
      MODE="preflight-only"
      ;;
    *)
      echo "❌ Unsupported argument: $1" >&2
      echo "Usage: $0 [--preflight-only]" >&2
      exit 1
      ;;
  esac
fi
readonly MODE

DEPLOY_IMAGE_REF="${IMAGE_REF:-}"
DEPLOY_TAG="${TAG:-}"
if [ "$MODE" != "preflight-only" ]; then
  : "${IMAGE_REF:?IMAGE_REF is required (ghcr.io/<image>@sha256:...)}"
  : "${TAG:?TAG is required (prod-vX.Y.Z)}"
fi

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-12}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

COMPOSE_FILE="${COMPOSE_FILE:-}"
COMPOSE_FILE_WAS_EXPLICIT=0
if [ -n "$COMPOSE_FILE" ]; then
  COMPOSE_FILE_WAS_EXPLICIT=1
fi
RESOLVED_COMPOSE_FILE="${COMPOSE_FILE:-}"
DEPLOY_DIR="${DEPLOY_DIR:-}"
ENV_FILE="${ENV_FILE:-}"
SHELL_BUNDLE_DIR="${SHELL_BUNDLE_DIR:-}"
SHELL_BUNDLE_ARCHIVE="${SHELL_BUNDLE_ARCHIVE:-}"
DOCKER_BIN_OVERRIDE="${DOCKER_BIN:-}"
PYTHON_BIN_OVERRIDE="${PYTHON_BIN:-}"
STAT_BIN_OVERRIDE="${STAT_BIN:-}"
CURL_BIN_OVERRIDE="${CURL_BIN:-}"
TRUSTED_DOCKER_CANDIDATES=(
  "/usr/bin/docker"
  "/usr/local/bin/docker"
  "/snap/bin/docker"
)
TRUSTED_DOCKER_CANDIDATES_TEXT="/usr/bin/docker, /usr/local/bin/docker, /snap/bin/docker"
TRUSTED_PYTHON_CANDIDATES=("/usr/bin/python3" "/usr/local/bin/python3")
TRUSTED_STAT_CANDIDATES=("/usr/bin/stat" "/bin/stat")
TRUSTED_CURL_CANDIDATES=("/usr/bin/curl" "/usr/local/bin/curl")
ARCHIVE_EXTRACT_DIR=""
GHCR_DOCKER_CONFIG=""

# RU: Сохраняем credentials из workflow/окружения до загрузки .env,
# чтобы локальный deploy/.env не подменял registry contract из CI.
# EN: Snapshot caller-provided credentials before sourcing .env so a host-local
# deploy/.env cannot override the CI-provided registry contract.
ORIGINAL_GHCR_USER="${GHCR_USER:-}"
ORIGINAL_GHCR_TOKEN="${GHCR_TOKEN:-}"

resolve_docker_bin() {
  local candidate

  if [ -n "$DOCKER_BIN_OVERRIDE" ]; then
    # RU: Разрешаем только абсолютный путь, чтобы не запускать docker-wrapper из PATH.
    # EN: Accept only an absolute path to avoid executing a PATH-injected docker wrapper.
    if [[ "$DOCKER_BIN_OVERRIDE" != /* ]]; then
      echo "❌ DOCKER_BIN must be an absolute path: $DOCKER_BIN_OVERRIDE" >&2
      return 1
    fi
    if [ ! -x "$DOCKER_BIN_OVERRIDE" ]; then
      echo "❌ DOCKER_BIN is not executable: $DOCKER_BIN_OVERRIDE" >&2
      return 1
    fi

    printf '%s\n' "$DOCKER_BIN_OVERRIDE"
    return 0
  fi

  for candidate in "${TRUSTED_DOCKER_CANDIDATES[@]}"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

resolve_absolute_executable() {
  local override="$1"
  local label="$2"
  shift 2
  local candidate

  if [ -n "$override" ]; then
    if [[ "$override" != /* ]]; then
      echo "❌ ${label} override must be an absolute path" >&2
      return 1
    fi
    if [ ! -x "$override" ]; then
      echo "❌ ${label} override is not executable" >&2
      return 1
    fi
    printf '%s\n' "$override"
    return 0
  fi

  for candidate in "$@"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  echo "❌ ${label} executable is required" >&2
  return 1
}

if ! DOCKER_BIN="$(resolve_docker_bin)"; then
  if [ -n "$DOCKER_BIN_OVERRIDE" ]; then
    echo "❌ docker binary not found. DOCKER_BIN override: $DOCKER_BIN_OVERRIDE. Trusted paths: $TRUSTED_DOCKER_CANDIDATES_TEXT" >&2
  else
    echo "❌ docker binary not found. Checked trusted paths: $TRUSTED_DOCKER_CANDIDATES_TEXT" >&2
  fi
  exit 1
fi
readonly DOCKER_BIN

if ! PYTHON_BIN="$(resolve_absolute_executable \
  "$PYTHON_BIN_OVERRIDE" "PYTHON_BIN" "${TRUSTED_PYTHON_CANDIDATES[@]}")"; then
  exit 1
fi
readonly PYTHON_BIN

if ! STAT_BIN="$(resolve_absolute_executable \
  "$STAT_BIN_OVERRIDE" "STAT_BIN" "${TRUSTED_STAT_CANDIDATES[@]}")"; then
  exit 1
fi
readonly STAT_BIN

if ! CURL_BIN="$(resolve_absolute_executable \
  "$CURL_BIN_OVERRIDE" "CURL_BIN" "${TRUSTED_CURL_CANDIDATES[@]}")"; then
  exit 1
fi
readonly CURL_BIN

resolve_deploy_dir() {
  if [ -n "$DEPLOY_DIR" ]; then
    if [ -d "$DEPLOY_DIR" ]; then
      echo "$DEPLOY_DIR"
      return 0
    fi
    echo "⚠️  DEPLOY_DIR is set but does not exist: $DEPLOY_DIR" >&2
    echo "    Falling back to auto-detect..." >&2
  fi

  if [ -d "/opt/pulseplate" ]; then
    echo "/opt/pulseplate"
    return 0
  fi

  if [ -d "/srv/pulseplate-production" ]; then
    echo "/srv/pulseplate-production"
    return 0
  fi

  return 1
}

if resolved_deploy_dir="$(resolve_deploy_dir)"; then
  DEPLOY_DIR="$resolved_deploy_dir"
else
  DEPLOY_DIR=""
fi
if [ -z "$DEPLOY_DIR" ]; then
  echo "❌ Could not find deploy directory." >&2
  echo "Set DEPLOY_DIR or create /opt/pulseplate or /srv/pulseplate-production." >&2
  exit 1
fi

REQUESTED_DEPLOY_DIR="$DEPLOY_DIR"
if [[ "$REQUESTED_DEPLOY_DIR" != /* ]]; then
  echo "❌ DEPLOY_DIR must be an absolute path" >&2
  exit 1
fi
readonly REQUESTED_DEPLOY_DIR
DEPLOY_DIR="$(cd "$DEPLOY_DIR" && pwd -P)"
cd "$DEPLOY_DIR"

compose_args=()
if [ "$COMPOSE_FILE_WAS_EXPLICIT" -eq 0 ]; then
  RESOLVED_COMPOSE_FILE="deploy/docker-compose.production.yaml"
else
  case "$RESOLVED_COMPOSE_FILE" in
    deploy/docker-compose.production.yaml | deploy/docker-compose.production.selfhosted.yaml)
      ;;
    "$DEPLOY_DIR/deploy/docker-compose.production.yaml" | \
      "$DEPLOY_DIR/deploy/docker-compose.production.selfhosted.yaml")
      ;;
    *)
      echo "❌ COMPOSE_FILE must select one exact canonical production Compose identity" >&2
      exit 1
      ;;
  esac
fi

if [ ! -f "$RESOLVED_COMPOSE_FILE" ]; then
  echo "❌ RESOLVED_COMPOSE_FILE does not exist: $RESOLVED_COMPOSE_FILE" >&2
  exit 1
fi
compose_args=(-f "$RESOLVED_COMPOSE_FILE")

if [[ "$RESOLVED_COMPOSE_FILE" = /* ]]; then
  COMPOSE_CONTRACT_PATH="$RESOLVED_COMPOSE_FILE"
else
  COMPOSE_CONTRACT_PATH="$DEPLOY_DIR/${RESOLVED_COMPOSE_FILE#./}"
fi
case "$COMPOSE_CONTRACT_PATH" in
  "$DEPLOY_DIR"/*)
    ;;
  *)
    echo "❌ COMPOSE_FILE must stay within DEPLOY_DIR" >&2
    exit 1
    ;;
esac
COMPOSE_CONTRACT_DIR="${COMPOSE_CONTRACT_PATH%/*}"
COMPOSE_RELATIVE_IDENTITY="${COMPOSE_CONTRACT_PATH#"$DEPLOY_DIR"/}"
PROMETHEUS_CONFIG="$COMPOSE_CONTRACT_DIR/prometheus/prometheus.yml"
PROMETHEUS_IMAGE_MANIFEST="$COMPOSE_CONTRACT_DIR/prometheus/image-manifest.json"
POSTGRES_IMAGE_MANIFEST="$COMPOSE_CONTRACT_DIR/postgres-pgvector/image-manifest.json"
METRICS_SECRET_DIR="$COMPOSE_CONTRACT_DIR/secrets"
METRICS_SECRET_FILE="$METRICS_SECRET_DIR/pulseplate_metrics_scrape_key"

PRODUCTION_DB_TOPOLOGY="managed"
if [ "${RESOLVED_COMPOSE_FILE##*/}" = "docker-compose.production.selfhosted.yaml" ]; then
  if [ "$COMPOSE_FILE_WAS_EXPLICIT" -ne 1 ]; then
    echo "❌ Self-hosted PostgreSQL Compose requires an explicit COMPOSE_FILE" >&2
    exit 1
  fi
  PRODUCTION_DB_TOPOLOGY="self-hosted"
fi
readonly COMPOSE_CONTRACT_PATH COMPOSE_CONTRACT_DIR
readonly COMPOSE_RELATIVE_IDENTITY
readonly PROMETHEUS_CONFIG PROMETHEUS_IMAGE_MANIFEST POSTGRES_IMAGE_MANIFEST
readonly METRICS_SECRET_DIR METRICS_SECRET_FILE PRODUCTION_DB_TOPOLOGY

if [ -z "$ENV_FILE" ]; then
  if [[ "$RESOLVED_COMPOSE_FILE" = deploy/* || "$RESOLVED_COMPOSE_FILE" = "$DEPLOY_DIR"/deploy/* ]]; then
    ENV_FILE="$DEPLOY_DIR/deploy/.env"
  else
    ENV_FILE="$DEPLOY_DIR/.env"
  fi
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing production env file: $ENV_FILE" >&2
  echo "Create this server-local runtime file before deploy; GitHub Actions does not provision it." >&2
  echo "See deploy/PRODUCTION.md for the canonical bootstrap contract." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

IMAGE_REF="$DEPLOY_IMAGE_REF"
TAG="$DEPLOY_TAG"

if [ -n "$ORIGINAL_GHCR_USER" ]; then
  GHCR_USER="$ORIGINAL_GHCR_USER"
fi
if [ -n "$ORIGINAL_GHCR_TOKEN" ]; then
  GHCR_TOKEN="$ORIGINAL_GHCR_TOKEN"
fi

export IMAGE_REF TAG

: "${PRODUCTION_DOMAIN:?PRODUCTION_DOMAIN is required}"

export PRODUCTION_DOMAIN

echo "Deploy dir: $DEPLOY_DIR"
if [ ${#compose_args[@]} -gt 0 ]; then
  echo "Compose file: ${compose_args[*]}"
else
  echo "Compose file: <default>"
fi
echo "TAG: $TAG"
echo "IMAGE_REF: $IMAGE_REF"
echo "ENV_FILE: $ENV_FILE"

dc() {
  local base=("$DOCKER_BIN" compose --env-file "$ENV_FILE")
  if [ ${#compose_args[@]} -gt 0 ]; then
    base+=("${compose_args[@]}")
  fi
  "${base[@]}" "$@"
}

login_to_ghcr_if_configured() {
  if [ -z "${GHCR_TOKEN:-}" ]; then
    return 0
  fi

  if [ -z "${GHCR_USER:-}" ]; then
    echo "❌ GHCR_USER is required when GHCR_TOKEN is provided" >&2
    exit 1
  fi

  umask 077
  GHCR_DOCKER_CONFIG="$(mktemp -d /tmp/pulseplate-production-docker-config.XXXXXX)"
  case "$GHCR_DOCKER_CONFIG" in
    /tmp/pulseplate-production-docker-config.*)
      ;;
    *)
      echo "❌ Refusing an unbounded Docker credential directory" >&2
      exit 1
      ;;
  esac
  if [ -L "$GHCR_DOCKER_CONFIG" ] || [ ! -d "$GHCR_DOCKER_CONFIG" ]; then
    echo "❌ Docker credential directory must be a real directory" >&2
    exit 1
  fi
  chmod 700 "$GHCR_DOCKER_CONFIG"
  export DOCKER_CONFIG="$GHCR_DOCKER_CONFIG"

  echo "Logging in to ghcr.io with temporary deploy credentials..."
  printf '%s\n' "$GHCR_TOKEN" | "$DOCKER_BIN" login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
}

cleanup_ghcr_credentials() {
  if [ -z "$GHCR_DOCKER_CONFIG" ]; then
    return 0
  fi
  local cleanup_failed=0
  if [ -d "$GHCR_DOCKER_CONFIG" ] && [ ! -L "$GHCR_DOCKER_CONFIG" ]; then
    if [ -f "$GHCR_DOCKER_CONFIG/config.json" ] && \
       [ ! -L "$GHCR_DOCKER_CONFIG/config.json" ]; then
      "$DOCKER_BIN" logout ghcr.io >/dev/null 2>&1 || cleanup_failed=1
      rm -f -- "$GHCR_DOCKER_CONFIG/config.json"
    elif [ -L "$GHCR_DOCKER_CONFIG/config.json" ]; then
      echo "❌ Docker credential file became a symlink" >&2
      cleanup_failed=1
    fi
    case "$GHCR_DOCKER_CONFIG" in
      /tmp/pulseplate-production-docker-config.*)
        rm -rf -- "$GHCR_DOCKER_CONFIG"
        ;;
      *)
        echo "❌ Refusing cleanup for an unbounded Docker credential directory" >&2
        cleanup_failed=1
        ;;
    esac
  else
    echo "❌ Refusing cleanup for an unsafe Docker credential directory" >&2
    cleanup_failed=1
  fi
  unset DOCKER_CONFIG
  GHCR_DOCKER_CONFIG=""
  return "$cleanup_failed"
}

validate_regular_non_symlink_file() {
  local path="$1"
  local label="$2"
  if [ -L "$path" ] || [ ! -f "$path" ]; then
    echo "❌ ${label} must be a regular non-symlink file" >&2
    return 1
  fi
}

read_owner_mode() {
  local path="$1"
  local metadata=""
  if metadata="$($STAT_BIN -c '%u:%a' "$path" 2>/dev/null)"; then
    printf '%s\n' "$metadata"
    return 0
  fi
  if metadata="$($STAT_BIN -f '%u:%Lp' "$path" 2>/dev/null)"; then
    printf '%s\n' "$metadata"
    return 0
  fi
  echo "❌ Unable to inspect owner and mode metadata" >&2
  return 1
}

validate_metrics_secret_metadata() {
  if [ -L "$METRICS_SECRET_DIR" ] || [ ! -d "$METRICS_SECRET_DIR" ]; then
    echo "❌ Metrics scrape secret directory must be a regular non-symlink directory" >&2
    return 1
  fi
  if [ -L "$METRICS_SECRET_FILE" ] || [ ! -f "$METRICS_SECRET_FILE" ]; then
    echo "❌ Metrics scrape secret must be a regular non-symlink file" >&2
    return 1
  fi

  local directory_metadata
  directory_metadata="$(read_owner_mode "$METRICS_SECRET_DIR")"
  if [ "$directory_metadata" != "${EUID}:700" ]; then
    echo "❌ Metrics scrape secret directory must be owned by the Compose account with mode 0700" >&2
    return 1
  fi

  local file_metadata
  file_metadata="$(read_owner_mode "$METRICS_SECRET_FILE")"
  if [ "$file_metadata" != "${EUID}:444" ]; then
    echo "❌ Metrics scrape secret file must be owned by the Compose account with mode 0444" >&2
    return 1
  fi
}

validate_prometheus_contract_files() {
  validate_regular_non_symlink_file "$PROMETHEUS_CONFIG" "Prometheus configuration"
  validate_regular_non_symlink_file "$PROMETHEUS_IMAGE_MANIFEST" "Prometheus image manifest"
}

validate_postgres_contract_files() {
  validate_regular_non_symlink_file "$POSTGRES_IMAGE_MANIFEST" \
    "PostgreSQL image manifest"
}

read_prometheus_runtime_ref() {
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

read_postgres_runtime_ref() {
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
expected_file_sha256 = "6e9da6d08ace2969ba315f2afcc99a49cec908ffac20f67ef05723246d6170c8"
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
    "platform_manifest_digest": "sha256:63782de6bbcb39760c585dfae46ac961a4dcf89a7d5aca53dd779fec7decdbd4",
    "config_digest": "sha256:da9e5626437d31f000dfd0460332d7194626439123f6ceb87fb9802cc4d165fa",
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

validate_prometheus_compose_identity() {
  local compose_path="$1"
  local runtime_ref="$2"
  "$DOCKER_BIN" compose --env-file "$ENV_FILE" -f "$compose_path" config --format json | \
    "$PYTHON_BIN" -c '
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

validate_prometheus_contract_identity() {
  local manifest_path="$1"
  local compose_path="$2"
  local runtime_ref
  runtime_ref="$(read_prometheus_runtime_ref "$manifest_path")"
  validate_prometheus_compose_identity "$compose_path" "$runtime_ref"
}

validate_postgres_compose_identity() {
  local compose_path="$1"
  local runtime_ref="$2"
  "$DOCKER_BIN" compose --env-file "$ENV_FILE" -f "$compose_path" config --format json | \
    "$PYTHON_BIN" -c '
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
    raise SystemExit("Rendered self-hosted Compose must define exactly one PostgreSQL service")
if postgres.get("image") != sys.argv[1] or postgres.get("platform") != "linux/amd64":
    raise SystemExit("Rendered self-hosted PostgreSQL identity does not match the manifest")
environment = postgres.get("environment")
if type(environment) is not dict or environment.get("PGDATA") != "/var/lib/postgresql/data":
    raise SystemExit("Rendered self-hosted PostgreSQL PGDATA does not preserve the volume root")
volumes = postgres.get("volumes")
if type(volumes) is not list:
    raise SystemExit("Rendered self-hosted PostgreSQL volumes are malformed")
data_mounts = [
    item
    for item in volumes
    if type(item) is dict and item.get("target") == "/var/lib/postgresql/data"
]
if len(data_mounts) != 1 or data_mounts[0].get("type") != "volume":
    raise SystemExit("Rendered self-hosted PostgreSQL must use one named data volume")
if postgres.get("ports") not in (None, []):
    raise SystemExit("Rendered self-hosted PostgreSQL must not publish a host port")
' "$runtime_ref"
}

validate_postgres_contract_identity() {
  local manifest_path="$1"
  local compose_path="$2"
  local runtime_ref
  runtime_ref="$(read_postgres_runtime_ref "$manifest_path")"
  validate_postgres_compose_identity "$compose_path" "$runtime_ref"
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

contract_destination_transaction() {
  local operation="$1"
  local source_compose="${2:-}"
  local source_prometheus_config="${3:-}"
  local source_prometheus_manifest="${4:-}"
  local source_postgres_manifest="${5:-}"
  local source_frontend="${6:-}"
  local source_caddyfile="${7:-}"
  local source_diagnose="${8:-}"
  local source_redeploy="${9:-}"

  "$PYTHON_BIN" - \
    "$operation" \
    "$REQUESTED_DEPLOY_DIR" \
    "$source_compose" \
    "$COMPOSE_RELATIVE_IDENTITY" \
    "$source_prometheus_config" \
    "deploy/prometheus/prometheus.yml" \
    "$source_prometheus_manifest" \
    "deploy/prometheus/image-manifest.json" \
    "$source_postgres_manifest" \
    "deploy/postgres-pgvector/image-manifest.json" \
    "$source_frontend" \
    "frontend" \
    "$source_caddyfile" \
    "deploy/Caddyfile.production" \
    "$source_diagnose" \
    "scripts/diagnose_web.sh" \
    "$source_redeploy" \
    "scripts/redeploy_caddy.sh" <<'PY'
from __future__ import annotations

import errno
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
import sys

operation = sys.argv[1]
requested_deploy_dir = sys.argv[2]
source_compose = sys.argv[3]
compose_target = sys.argv[4]
source_config = sys.argv[5]
config_target = sys.argv[6]
source_manifest = sys.argv[7]
manifest_target = sys.argv[8]
source_postgres_manifest = sys.argv[9]
postgres_manifest_target = sys.argv[10]
source_frontend = sys.argv[11]
frontend_target = sys.argv[12]
source_caddy = sys.argv[13]
caddy_target = sys.argv[14]
source_diagnose = sys.argv[15]
diagnose_target = sys.argv[16]
source_redeploy = sys.argv[17]
redeploy_target = sys.argv[18]

if operation not in {
    "validate-contracts",
    "publish-contracts",
    "validate-full",
    "publish-full",
}:
    raise SystemExit("unsupported contract destination transaction")
if not os.path.isabs(requested_deploy_dir) or os.path.normpath(requested_deploy_dir) != requested_deploy_dir:
    raise SystemExit("DEPLOY_DIR must be one canonical absolute path")

allowed_compose_targets = {
    "deploy/docker-compose.production.yaml",
    "deploy/docker-compose.production.selfhosted.yaml",
}
if compose_target not in allowed_compose_targets:
    raise SystemExit("selected Compose destination is not canonical")
if config_target != "deploy/prometheus/prometheus.yml":
    raise SystemExit("Prometheus configuration destination is not canonical")
if manifest_target != "deploy/prometheus/image-manifest.json":
    raise SystemExit("Prometheus image manifest destination is not canonical")
if postgres_manifest_target != "deploy/postgres-pgvector/image-manifest.json":
    raise SystemExit("PostgreSQL image manifest destination is not canonical")
if frontend_target != "frontend":
    raise SystemExit("frontend destination is not canonical")
if caddy_target != "deploy/Caddyfile.production":
    raise SystemExit("Caddy destination is not canonical")
if diagnose_target != "scripts/diagnose_web.sh":
    raise SystemExit("diagnose helper destination is not canonical")
if redeploy_target != "scripts/redeploy_caddy.sh":
    raise SystemExit("redeploy helper destination is not canonical")

no_follow = getattr(os, "O_NOFOLLOW", 0)
directory_flag = getattr(os, "O_DIRECTORY", 0)
if no_follow <= 0 or directory_flag <= 0:
    raise SystemExit("descriptor no-follow directory validation is unavailable")
directory_open_flags = os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0)
file_read_flags = os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0)
max_contract_bytes = 4 * 1024 * 1024
max_tree_members = 20_000
max_tree_bytes = 512 * 1024 * 1024
max_tree_depth = 32


def open_existing_directory(parent_fd: int, component: str, *, label: str) -> int:
    try:
        metadata = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} directory is missing") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise SystemExit(f"{label} must be a real directory")
    try:
        descriptor = os.open(component, directory_open_flags, dir_fd=parent_fd)
    except OSError as exc:
        raise SystemExit(f"{label} cannot be opened safely") from exc
    opened_metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(opened_metadata.st_mode)
        or opened_metadata.st_dev != metadata.st_dev
        or opened_metadata.st_ino != metadata.st_ino
    ):
        os.close(descriptor)
        raise SystemExit(f"{label} identity changed")
    return descriptor


def ensure_directory(parent_fd: int, component: str, *, create: bool, label: str) -> int | None:
    try:
        return open_existing_directory(parent_fd, component, label=label)
    except SystemExit:
        try:
            metadata = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            if not create:
                return None
            try:
                os.mkdir(component, 0o755, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except OSError as exc:
                raise SystemExit(f"{label} cannot be created safely") from exc
            return open_existing_directory(parent_fd, component, label=label)
        if not stat.S_ISDIR(metadata.st_mode):
            raise SystemExit(f"{label} must be a real directory")
        raise


def validate_regular_leaf(parent_fd: int, leaf: str, *, label: str) -> None:
    try:
        metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise SystemExit(f"{label} must be absent or one regular file")


def open_absolute_directory(raw_path: str, *, label: str) -> int:
    if not os.path.isabs(raw_path) or os.path.normpath(raw_path) != raw_path:
        raise SystemExit(f"{label} path must be canonical and absolute")
    root_fd = os.open("/", directory_open_flags)
    walk_fd = root_fd
    try:
        for component in Path(raw_path).parts[1:]:
            next_fd = open_existing_directory(walk_fd, component, label=label)
            if walk_fd != root_fd:
                os.close(walk_fd)
            walk_fd = next_fd
        if walk_fd == root_fd:
            raise SystemExit(f"{label} cannot be the filesystem root")
        return walk_fd
    finally:
        os.close(root_fd)


def open_absolute_file(raw_path: str, *, label: str, max_bytes: int) -> tuple[int, os.stat_result]:
    if not os.path.isabs(raw_path) or os.path.normpath(raw_path) != raw_path:
        raise SystemExit(f"{label} path must be canonical and absolute")
    parts = Path(raw_path).parts[1:]
    if not parts:
        raise SystemExit(f"{label} path is not a file")
    root_fd = os.open("/", directory_open_flags)
    walk_fd = root_fd
    try:
        for component in parts[:-1]:
            next_fd = open_existing_directory(walk_fd, component, label=f"{label} parent")
            if walk_fd != root_fd:
                os.close(walk_fd)
            walk_fd = next_fd
        leaf = parts[-1]
        try:
            before = os.stat(leaf, dir_fd=walk_fd, follow_symlinks=False)
            descriptor = os.open(leaf, file_read_flags, dir_fd=walk_fd)
        except OSError as exc:
            raise SystemExit(f"{label} cannot be opened safely") from exc
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or opened.st_size <= 0
            or opened.st_size > max_bytes
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            os.close(descriptor)
            raise SystemExit(f"{label} must be one bounded regular file")
        return descriptor, opened
    finally:
        if walk_fd != root_fd:
            os.close(walk_fd)
        os.close(root_fd)


def copy_open_file(
    source_fd: int,
    source_metadata: os.stat_result,
    destination_fd: int,
    *,
    label: str,
) -> None:
    remaining = source_metadata.st_size
    while remaining:
        chunk = os.read(source_fd, min(1024 * 1024, remaining))
        if not chunk:
            raise SystemExit(f"{label} changed during publication")
        view = memoryview(chunk)
        while view:
            written = os.write(destination_fd, view)
            if written <= 0:
                raise SystemExit(f"{label} destination write failed")
            view = view[written:]
        remaining -= len(chunk)
    if os.read(source_fd, 1):
        raise SystemExit(f"{label} grew during publication")
    after = os.fstat(source_fd)
    if (
        after.st_size != source_metadata.st_size
        or after.st_mtime_ns != source_metadata.st_mtime_ns
        or after.st_ctime_ns != source_metadata.st_ctime_ns
    ):
        raise SystemExit(f"{label} identity changed during publication")


def tree_walk(
    source_fd: int,
    *,
    destination_fd: int | None,
    state: dict[str, int],
    depth: int,
    label: str,
) -> None:
    if depth > max_tree_depth:
        raise SystemExit(f"{label} tree depth is out of bounds")
    entries = sorted(os.scandir(source_fd), key=lambda entry: entry.name)
    for entry in entries:
        name = entry.name
        metadata = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        state["members"] += 1
        if state["members"] > max_tree_members:
            raise SystemExit(f"{label} tree member count is out of bounds")
        if stat.S_ISDIR(metadata.st_mode):
            child_source = open_existing_directory(source_fd, name, label=f"{label} directory")
            child_destination: int | None = None
            try:
                if destination_fd is not None:
                    os.mkdir(name, 0o755, dir_fd=destination_fd)
                    child_destination = open_existing_directory(
                        destination_fd,
                        name,
                        label=f"{label} staging directory",
                    )
                tree_walk(
                    child_source,
                    destination_fd=child_destination,
                    state=state,
                    depth=depth + 1,
                    label=label,
                )
                if child_destination is not None:
                    os.fsync(child_destination)
            finally:
                if child_destination is not None:
                    os.close(child_destination)
                os.close(child_source)
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise SystemExit(f"{label} tree contains a link or special file")
        if metadata.st_size < 0 or metadata.st_size > max_tree_bytes:
            raise SystemExit(f"{label} tree file size is out of bounds")
        state["bytes"] += metadata.st_size
        if state["bytes"] > max_tree_bytes:
            raise SystemExit(f"{label} tree expanded size is out of bounds")
        source_file = os.open(name, file_read_flags, dir_fd=source_fd)
        try:
            opened = os.fstat(source_file)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_dev != metadata.st_dev
                or opened.st_ino != metadata.st_ino
                or opened.st_size != metadata.st_size
            ):
                raise SystemExit(f"{label} tree file identity changed")
            if destination_fd is not None:
                destination_file = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=destination_fd,
                )
                try:
                    copy_open_file(
                        source_file,
                        opened,
                        destination_file,
                        label=f"{label} tree file",
                    )
                    os.fchmod(destination_file, 0o644)
                    os.fsync(destination_file)
                finally:
                    os.close(destination_file)
        finally:
            os.close(source_file)


def remove_tree_at(parent_fd: int, name: str, *, label: str) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(metadata.st_mode):
        raise SystemExit(f"{label} cleanup target must be a real directory")
    tree_fd = open_existing_directory(parent_fd, name, label=label)
    try:
        entries = sorted(os.scandir(tree_fd), key=lambda entry: entry.name)
        for entry in entries:
            metadata = os.stat(entry.name, dir_fd=tree_fd, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                remove_tree_at(tree_fd, entry.name, label=label)
            elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                os.unlink(entry.name, dir_fd=tree_fd)
            else:
                raise SystemExit(f"{label} cleanup encountered a link or special file")
        os.fsync(tree_fd)
    finally:
        os.close(tree_fd)
    os.rmdir(name, dir_fd=parent_fd)
    os.fsync(parent_fd)


def split_target(raw_target: str) -> tuple[str, ...]:
    pure_path = PurePosixPath(raw_target)
    if pure_path.is_absolute() or str(pure_path) != raw_target:
        raise SystemExit("contract destination path is not canonical")
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise SystemExit("contract destination path is not bounded")
    return pure_path.parts


deploy_fd = open_absolute_directory(requested_deploy_dir, label="contract destination")
directory_fds: list[int] = [deploy_fd]
try:
    targets = [
        compose_target,
        config_target,
        manifest_target,
        postgres_manifest_target,
        frontend_target,
        caddy_target,
        diagnose_target,
        redeploy_target,
    ]
    target_parts = {target: split_target(target) for target in targets}
    deploy_contract_fd = ensure_directory(
        deploy_fd,
        "deploy",
        create=False,
        label="canonical deploy contract directory",
    )
    if deploy_contract_fd is None:
        raise SystemExit("canonical deploy contract directory is missing")
    directory_fds.append(deploy_contract_fd)

    prometheus_fd = ensure_directory(
        deploy_contract_fd,
        "prometheus",
        create=operation == "publish-contracts",
        label="Prometheus contract directory",
    )
    if prometheus_fd is not None:
        directory_fds.append(prometheus_fd)

    postgres_pgvector_fd = ensure_directory(
        deploy_contract_fd,
        "postgres-pgvector",
        create=operation == "publish-contracts",
        label="PostgreSQL image contract directory",
    )
    if postgres_pgvector_fd is not None:
        directory_fds.append(postgres_pgvector_fd)

    scripts_fd = ensure_directory(
        deploy_fd,
        "scripts",
        create=operation == "publish-full",
        label="production scripts directory",
    )
    if scripts_fd is not None:
        directory_fds.append(scripts_fd)

    parent_by_target: dict[str, int | None] = {
        compose_target: deploy_contract_fd,
        config_target: prometheus_fd,
        manifest_target: prometheus_fd,
        postgres_manifest_target: postgres_pgvector_fd,
        caddy_target: deploy_contract_fd,
        diagnose_target: scripts_fd,
        redeploy_target: scripts_fd,
    }
    for target in (
        compose_target,
        config_target,
        manifest_target,
        postgres_manifest_target,
        caddy_target,
        diagnose_target,
        redeploy_target,
    ):
        parent_fd = parent_by_target[target]
        if parent_fd is not None:
            validate_regular_leaf(
                parent_fd,
                target_parts[target][-1],
                label=f"{target} destination",
            )

    try:
        frontend_metadata = os.stat(frontend_target, dir_fd=deploy_fd, follow_symlinks=False)
    except FileNotFoundError:
        frontend_metadata = None
    if frontend_metadata is not None:
        if not stat.S_ISDIR(frontend_metadata.st_mode):
            raise SystemExit("frontend destination must be absent or a real directory")
        existing_frontend_fd = open_existing_directory(
            deploy_fd,
            frontend_target,
            label="frontend destination",
        )
        try:
            tree_walk(
                existing_frontend_fd,
                destination_fd=None,
                state={"members": 0, "bytes": 0},
                depth=0,
                label="frontend destination",
            )
        finally:
            os.close(existing_frontend_fd)

    if operation == "validate-contracts":
        raise SystemExit(0)

    if operation == "publish-contracts":
        if prometheus_fd is None:
            raise SystemExit("Prometheus contract directory was not created")
        if postgres_pgvector_fd is None:
            raise SystemExit("PostgreSQL image contract directory was not created")
        sources = {
            compose_target: source_compose,
            config_target: source_config,
            manifest_target: source_manifest,
            postgres_manifest_target: source_postgres_manifest,
        }
        prepared_contracts: list[tuple[int, str, str]] = []
        try:
            for target in (
                config_target,
                manifest_target,
                postgres_manifest_target,
                compose_target,
            ):
                source_fd, source_metadata = open_absolute_file(
                    sources[target],
                    label=f"{target} source",
                    max_bytes=max_contract_bytes,
                )
                try:
                    parent_fd = parent_by_target[target]
                    if parent_fd is None:
                        raise SystemExit("contract destination parent is unavailable")
                    leaf = target_parts[target][-1]
                    temp_name = (
                        f".pulseplate-{leaf}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
                    )
                    temp_fd = os.open(
                        temp_name,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | no_follow
                        | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=parent_fd,
                    )
                    try:
                        copy_open_file(
                            source_fd,
                            source_metadata,
                            temp_fd,
                            label=f"{target} source",
                        )
                        os.fchmod(temp_fd, 0o644)
                        os.fsync(temp_fd)
                    finally:
                        os.close(temp_fd)
                    prepared_contracts.append((parent_fd, temp_name, leaf))
                finally:
                    os.close(source_fd)

            for parent_fd, temp_name, leaf in prepared_contracts:
                os.replace(
                    temp_name,
                    leaf,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                os.fsync(parent_fd)
        finally:
            for parent_fd, temp_name, _leaf in prepared_contracts:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
        raise SystemExit(0)

    frontend_source_fd = open_absolute_directory(source_frontend, label="frontend source")
    try:
        if operation == "validate-full":
            tree_walk(
                frontend_source_fd,
                destination_fd=None,
                state={"members": 0, "bytes": 0},
                depth=0,
                label="frontend source",
            )
            for source_path, label in (
                (source_caddy, "Caddy source"),
                (source_redeploy, "redeploy helper source"),
            ):
                source_fd, _metadata = open_absolute_file(
                    source_path,
                    label=label,
                    max_bytes=max_contract_bytes,
                )
                os.close(source_fd)
            if source_diagnose:
                source_fd, _metadata = open_absolute_file(
                    source_diagnose,
                    label="diagnose helper source",
                    max_bytes=max_contract_bytes,
                )
                os.close(source_fd)
            raise SystemExit(0)

        if scripts_fd is None:
            raise SystemExit("production scripts directory was not created")

        temp_frontend = (
            f".pulseplate-frontend.tmp-{os.getpid()}-{secrets.token_hex(8)}"
        )
        os.mkdir(temp_frontend, 0o755, dir_fd=deploy_fd)
        temp_frontend_fd = open_existing_directory(
            deploy_fd,
            temp_frontend,
            label="frontend staging directory",
        )
        try:
            tree_walk(
                frontend_source_fd,
                destination_fd=temp_frontend_fd,
                state={"members": 0, "bytes": 0},
                depth=0,
                label="frontend source",
            )
            os.fsync(temp_frontend_fd)
        finally:
            os.close(temp_frontend_fd)

        prepared_files: list[tuple[int, str, str]] = []
        regular_sources = [
            (source_caddy, deploy_contract_fd, "Caddyfile.production", 0o644, "Caddy source"),
            (source_redeploy, scripts_fd, "redeploy_caddy.sh", 0o755, "redeploy helper source"),
        ]
        if source_diagnose:
            regular_sources.append(
                (source_diagnose, scripts_fd, "diagnose_web.sh", 0o755, "diagnose helper source")
            )
        backup_frontend = ""
        try:
            for source_path, parent_fd, leaf, mode, label in regular_sources:
                source_fd, source_metadata = open_absolute_file(
                    source_path,
                    label=label,
                    max_bytes=max_contract_bytes,
                )
                try:
                    temp_name = (
                        f".pulseplate-{leaf}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
                    )
                    temp_fd = os.open(
                        temp_name,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | no_follow
                        | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=parent_fd,
                    )
                    try:
                        copy_open_file(source_fd, source_metadata, temp_fd, label=label)
                        os.fchmod(temp_fd, mode)
                        os.fsync(temp_fd)
                    finally:
                        os.close(temp_fd)
                    prepared_files.append((parent_fd, temp_name, leaf))
                finally:
                    os.close(source_fd)

            for parent_fd, temp_name, leaf in prepared_files:
                os.replace(
                    temp_name,
                    leaf,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                os.fsync(parent_fd)

            if not source_diagnose:
                try:
                    os.unlink("diagnose_web.sh", dir_fd=scripts_fd)
                except FileNotFoundError:
                    pass
                os.fsync(scripts_fd)

            if frontend_metadata is not None:
                backup_frontend = (
                    f".pulseplate-frontend.old-{os.getpid()}-{secrets.token_hex(8)}"
                )
                os.rename(
                    frontend_target,
                    backup_frontend,
                    src_dir_fd=deploy_fd,
                    dst_dir_fd=deploy_fd,
                )
                os.fsync(deploy_fd)
            try:
                os.rename(
                    temp_frontend,
                    frontend_target,
                    src_dir_fd=deploy_fd,
                    dst_dir_fd=deploy_fd,
                )
                os.fsync(deploy_fd)
            except BaseException:
                if backup_frontend:
                    os.rename(
                        backup_frontend,
                        frontend_target,
                        src_dir_fd=deploy_fd,
                        dst_dir_fd=deploy_fd,
                    )
                    backup_frontend = ""
                    os.fsync(deploy_fd)
                raise

            if backup_frontend:
                remove_tree_at(deploy_fd, backup_frontend, label="previous frontend tree")
                backup_frontend = ""
        finally:
            for parent_fd, temp_name, _leaf in prepared_files:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            remove_tree_at(deploy_fd, temp_frontend, label="frontend staging tree")
            if backup_frontend:
                if frontend_target not in {
                    entry.name for entry in os.scandir(deploy_fd)
                }:
                    os.rename(
                        backup_frontend,
                        frontend_target,
                        src_dir_fd=deploy_fd,
                        dst_dir_fd=deploy_fd,
                    )
                    os.fsync(deploy_fd)
                else:
                    raise SystemExit("previous frontend backup requires operator disposition")
    finally:
        os.close(frontend_source_fd)
finally:
    for descriptor in reversed(directory_fds):
        try:
            os.close(descriptor)
        except OSError as exc:
            if exc.errno != errno.EBADF:
                raise
PY
}

validate_contract_destinations_safely() {
  contract_destination_transaction validate-contracts "" "" "" ""
}

publish_contract_files_safely() {
  local source_compose="$1"
  local source_prometheus_config="$2"
  local source_prometheus_manifest="$3"
  local source_postgres_manifest="$4"
  contract_destination_transaction publish-contracts \
    "$source_compose" \
    "$source_prometheus_config" \
    "$source_prometheus_manifest" \
    "$source_postgres_manifest"
}

validate_full_bundle_safely() {
  local source_frontend="$1"
  local source_caddyfile="$2"
  local source_diagnose="$3"
  local source_redeploy="$4"
  contract_destination_transaction validate-full \
    "" "" "" "" \
    "$source_frontend" \
    "$source_caddyfile" \
    "$source_diagnose" \
    "$source_redeploy"
}

publish_full_bundle_safely() {
  local source_frontend="$1"
  local source_caddyfile="$2"
  local source_diagnose="$3"
  local source_redeploy="$4"
  contract_destination_transaction publish-full \
    "" "" "" "" \
    "$source_frontend" \
    "$source_caddyfile" \
    "$source_diagnose" \
    "$source_redeploy"
}

process_shell_bundle_archive() {
  local operation="$1"
  local private_root="$2"

  "$PYTHON_BIN" - "$SHELL_BUNDLE_ARCHIVE" "$private_root" "$operation" <<'PY'
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile

source_path = Path(sys.argv[1])
private_root = Path(sys.argv[2])
operation = sys.argv[3]
if operation not in {"validate", "extract"}:
    raise SystemExit("unsupported archive operation")
if not re.fullmatch(r"/tmp/pulseplate-shell-bundle-[0-9]+-[0-9]+[.]tgz", str(source_path)):
    raise SystemExit("production shell archive path is not canonical")

no_follow = getattr(os, "O_NOFOLLOW", 0)
source_fd = os.open(source_path, os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0))
try:
    source_metadata = os.fstat(source_fd)
    if not stat.S_ISREG(source_metadata.st_mode) or source_metadata.st_nlink != 1:
        raise SystemExit("production shell archive must be one regular file")
    if source_metadata.st_size <= 0 or source_metadata.st_size > 512 * 1024 * 1024:
        raise SystemExit("production shell archive size is out of bounds")

    copied_archive = private_root / "bundle.tgz"
    copied_fd = os.open(
        copied_archive,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        with os.fdopen(os.dup(source_fd), "rb") as source, os.fdopen(
            copied_fd, "wb", closefd=False
        ) as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
    finally:
        os.close(copied_fd)
finally:
    os.close(source_fd)

required_files = {
    "deploy/Caddyfile.production",
    "deploy/docker-compose.production.yaml",
    "deploy/postgres-pgvector/image-manifest.json",
    "deploy/prometheus/image-manifest.json",
    "deploy/prometheus/prometheus.yml",
    "scripts/diagnose_web.sh",
    "scripts/redeploy_caddy.sh",
}
allowed_directories = {
    "frontend",
    "deploy",
    "deploy/postgres-pgvector",
    "deploy/prometheus",
    "scripts",
}
max_members = 20_000
max_expanded_bytes = 512 * 1024 * 1024

with tarfile.open(copied_archive, mode="r:gz") as archive:
    members = archive.getmembers()
    if not members or len(members) > max_members:
        raise SystemExit("production shell archive member count is out of bounds")

    seen: set[str] = set()
    files_seen: set[str] = set()
    expanded_bytes = 0
    normalized_members: list[tuple[tarfile.TarInfo, str]] = []
    for member in members:
        raw_name = member.name
        if not raw_name or "\\" in raw_name:
            raise SystemExit("production shell archive contains an invalid member name")
        pure_path = PurePosixPath(raw_name)
        normalized_name = str(pure_path)
        if (
            pure_path.is_absolute()
            or normalized_name != raw_name
            or any(part in {"", ".", ".."} for part in pure_path.parts)
        ):
            raise SystemExit("production shell archive contains a non-canonical path")
        if normalized_name in seen:
            raise SystemExit("production shell archive contains a duplicate member")
        seen.add(normalized_name)

        allowed = (
            normalized_name in required_files
            or normalized_name in allowed_directories
            or normalized_name.startswith("frontend/")
        )
        if not allowed:
            raise SystemExit("production shell archive contains an unexpected member")
        if not member.isfile() and not member.isdir():
            raise SystemExit("production shell archive contains a non-data member")
        if member.size < 0 or member.size > max_expanded_bytes:
            raise SystemExit("production shell archive member size is out of bounds")
        expanded_bytes += member.size
        if expanded_bytes > max_expanded_bytes:
            raise SystemExit("production shell archive expanded size is out of bounds")
        if member.isfile():
            files_seen.add(normalized_name)
        normalized_members.append((member, normalized_name))

    if not required_files.issubset(files_seen) or "frontend" not in seen:
        raise SystemExit("production shell archive is missing a canonical member")

    if operation == "extract":
        payload_root = private_root / "payload"
        payload_root.mkdir(mode=0o700)
        for member, normalized_name in sorted(
            normalized_members,
            key=lambda item: (len(PurePosixPath(item[1]).parts), item[1]),
        ):
            target = payload_root.joinpath(*PurePosixPath(normalized_name).parts)
            if member.isdir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise SystemExit("production shell archive member cannot be read")
            target_fd = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow | getattr(os, "O_CLOEXEC", 0),
                member.mode & 0o777,
            )
            try:
                with source, os.fdopen(target_fd, "wb", closefd=False) as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                    destination.flush()
                    os.fsync(destination.fileno())
            finally:
                os.close(target_fd)
PY
}

validate_shell_bundle_archive() {
  if [ -z "$SHELL_BUNDLE_ARCHIVE" ]; then
    return 0
  fi
  if [ -n "$SHELL_BUNDLE_DIR" ]; then
    echo "❌ SHELL_BUNDLE_ARCHIVE and SHELL_BUNDLE_DIR are mutually exclusive" >&2
    return 1
  fi

  local validation_root
  validation_root="$(mktemp -d /tmp/pulseplate-shell-bundle-validation.XXXXXX)"
  chmod 700 "$validation_root"
  validation_root="$(cd "$validation_root" && pwd -P)"
  local validation_status=0
  local original_bundle_dir="$SHELL_BUNDLE_DIR"
  if process_shell_bundle_archive extract "$validation_root"; then
    SHELL_BUNDLE_DIR="$validation_root/payload"
    if validate_shell_bundle_contract; then
      validation_status=0
    else
      validation_status=$?
    fi
  else
    validation_status=$?
  fi
  SHELL_BUNDLE_DIR="$original_bundle_dir"
  rm -rf -- "$validation_root"
  return "$validation_status"
}

extract_shell_bundle_archive() {
  if [ -z "$SHELL_BUNDLE_ARCHIVE" ]; then
    return 0
  fi

  ARCHIVE_EXTRACT_DIR="$(mktemp -d /tmp/pulseplate-shell-bundle-extract.XXXXXX)"
  chmod 700 "$ARCHIVE_EXTRACT_DIR"
  ARCHIVE_EXTRACT_DIR="$(cd "$ARCHIVE_EXTRACT_DIR" && pwd -P)"
  process_shell_bundle_archive extract "$ARCHIVE_EXTRACT_DIR"
  SHELL_BUNDLE_DIR="$ARCHIVE_EXTRACT_DIR/payload"
}

cleanup_shell_bundle_archive() {
  if [ -n "$ARCHIVE_EXTRACT_DIR" ]; then
    local resolved_tmp
    resolved_tmp="$(cd /tmp && pwd -P)"
    case "$ARCHIVE_EXTRACT_DIR" in
      "$resolved_tmp"/pulseplate-shell-bundle-extract.*)
        rm -rf -- "$ARCHIVE_EXTRACT_DIR"
        ;;
      *)
        echo "❌ Refusing to clean an unexpected shell-bundle extraction path" >&2
        ;;
    esac
  fi
  if [ -n "$SHELL_BUNDLE_ARCHIVE" ]; then
    if [[ "$SHELL_BUNDLE_ARCHIVE" =~ ^/tmp/pulseplate-shell-bundle-[0-9]+-[0-9]+\.tgz$ ]] && \
       [ -f "$SHELL_BUNDLE_ARCHIVE" ] && [ ! -L "$SHELL_BUNDLE_ARCHIVE" ]; then
      rm -f -- "$SHELL_BUNDLE_ARCHIVE"
    fi
  fi
}

cleanup_deploy_runtime() {
  local original_status=$?
  trap - EXIT
  if ! cleanup_ghcr_credentials; then
    original_status=1
  fi
  cleanup_shell_bundle_archive
  exit "$original_status"
}

sync_shell_bundle() {
  local sync_mode="${1:-full}"
  case "$sync_mode" in
    compose-only|full)
      ;;
    *)
      echo "❌ Unsupported shell bundle sync mode: $sync_mode" >&2
      exit 1
      ;;
  esac

  if [ -z "$SHELL_BUNDLE_DIR" ]; then
    return 0
  fi

  if [ -z "$DEPLOY_DIR" ]; then
    echo "❌ DEPLOY_DIR is required when SHELL_BUNDLE_DIR is set" >&2
    exit 1
  fi

  local source_frontend="$SHELL_BUNDLE_DIR/frontend"
  local source_caddyfile="$SHELL_BUNDLE_DIR/deploy/Caddyfile.production"
  local source_compose=""
  local source_prometheus_config="$SHELL_BUNDLE_DIR/deploy/prometheus/prometheus.yml"
  local source_prometheus_manifest="$SHELL_BUNDLE_DIR/deploy/prometheus/image-manifest.json"
  local source_postgres_manifest="$SHELL_BUNDLE_DIR/deploy/postgres-pgvector/image-manifest.json"
  local source_diagnose="$SHELL_BUNDLE_DIR/scripts/diagnose_web.sh"
  local source_redeploy="$SHELL_BUNDLE_DIR/scripts/redeploy_caddy.sh"
  local compose_relative_path="$COMPOSE_RELATIVE_IDENTITY"

  if [ -z "$RESOLVED_COMPOSE_FILE" ]; then
    echo "❌ Could not resolve a compose filename for shell bundle sync" >&2
    exit 1
  fi

  source_compose="$SHELL_BUNDLE_DIR/$compose_relative_path"

  if [ -L "$source_frontend" ] || [ ! -d "$source_frontend" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing frontend/: $source_frontend" >&2
    exit 1
  fi

  if [ -L "$source_caddyfile" ] || [ ! -f "$source_caddyfile" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing deploy/Caddyfile.production: $source_caddyfile" >&2
    exit 1
  fi

  if [ -L "$source_compose" ] || [ ! -f "$source_compose" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing $compose_relative_path: $source_compose" >&2
    exit 1
  fi

  validate_regular_non_symlink_file "$source_prometheus_config" \
    "Incoming Prometheus configuration"
  validate_regular_non_symlink_file "$source_prometheus_manifest" \
    "Incoming Prometheus image manifest"
  validate_regular_non_symlink_file "$source_postgres_manifest" \
    "Incoming PostgreSQL image manifest"

  if [ -L "$source_redeploy" ] || [ ! -f "$source_redeploy" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh: $source_redeploy" >&2
    exit 1
  fi

  if [ -L "$source_diagnose" ]; then
    echo "❌ Optional diagnose helper must not be a symlink" >&2
    exit 1
  fi
  if [ ! -f "$source_diagnose" ]; then
    source_diagnose=""
  fi

  if [ "$sync_mode" = "compose-only" ]; then
    publish_contract_files_safely \
      "$source_compose" \
      "$source_prometheus_config" \
      "$source_prometheus_manifest" \
      "$source_postgres_manifest"
    echo "Synced production Compose, Prometheus, and PostgreSQL image contracts before worker operations"
    return 0
  fi

  echo "Syncing production shell bundle from: $SHELL_BUNDLE_DIR"
  publish_full_bundle_safely \
    "$source_frontend" \
    "$source_caddyfile" \
    "$source_diagnose" \
    "$source_redeploy"
}

wait_for_app_ready() {
  local max_wait="${1:-30}"
  local wait_count=0

  while [ "$wait_count" -lt "$max_wait" ]; do
    local app_container
    app_container="$(dc ps -q app | tr -d '\n\r ')"
    if [ -n "${app_container:-}" ] && "$DOCKER_BIN" exec "$app_container" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready').read()" 2>/dev/null; then
      echo "app is ready"
      return 0
    fi
    wait_count=$((wait_count + 1))
    echo "Waiting for app readiness... ($wait_count/$max_wait)"
    sleep 1
  done

  echo "❌ App failed to become ready within $max_wait seconds" >&2
  return 1
}

wait_for_postgres_ready() {
  local max_wait="${1:-60}"
  local wait_count=0

  while [ "$wait_count" -lt "$max_wait" ]; do
    local postgres_container=""
    local postgres_health="unknown"
    postgres_container="$(dc ps -q postgres | tr -d '\n\r ')"
    if [ -n "$postgres_container" ]; then
      if inspected_health="$($DOCKER_BIN inspect \
          --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
          "$postgres_container" 2>/dev/null)"; then
        postgres_health="$inspected_health"
      fi
    fi
    if [ -n "$postgres_container" ] && [ "$postgres_health" = "healthy" ]; then
      echo "PostgreSQL is healthy"
      return 0
    fi
    wait_count=$((wait_count + 1))
    echo "Waiting for PostgreSQL readiness... ($wait_count/$max_wait)"
    sleep 1
  done

  echo "❌ PostgreSQL failed to become healthy within $max_wait seconds" >&2
  return 1
}

validate_managed_postgres_contract() {
  case "${DATABASE_URL:-}" in
    postgresql+psycopg://*)
      ;;
    *)
      echo "❌ DATABASE_URL must use canonical Postgres DSN (postgresql+psycopg://...)" >&2
      exit 1
      ;;
  esac

  case "$DATABASE_URL" in
    *@postgres:*/* | *@postgres/*)
      echo "❌ Production deploy expects external managed PostgreSQL, not compose-local @postgres" >&2
      exit 1
      ;;
  esac

  local service
  while IFS= read -r service; do
    if [ "$service" = "postgres" ]; then
      echo "❌ Managed production Compose must not contain a local postgres service" >&2
      exit 1
    fi
  done < <(dc config --services)
}

validate_self_hosted_postgres_contract() {
  : "${POSTGRES_DB:?POSTGRES_DB is required for self-hosted PostgreSQL}"
  : "${POSTGRES_USER:?POSTGRES_USER is required for self-hosted PostgreSQL}"
  : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required for self-hosted PostgreSQL}"

  local postgres_seen=0
  local service
  while IFS= read -r service; do
    if [ "$service" = "postgres" ]; then
      postgres_seen=$((postgres_seen + 1))
    fi
  done < <(dc config --services)
  if [ "$postgres_seen" -ne 1 ]; then
    echo "❌ Self-hosted production Compose must contain exactly one postgres service" >&2
    exit 1
  fi
}

validate_production_database_contract() {
  case "$PRODUCTION_DB_TOPOLOGY" in
    managed)
      validate_managed_postgres_contract
      ;;
    self-hosted)
      validate_self_hosted_postgres_contract
      ;;
    *)
      echo "❌ Unsupported production database topology" >&2
      exit 1
      ;;
  esac
}

validate_scheduler_mode_contract() {
  FOOD_UPDATE_SCHEDULER_MODE="${FOOD_UPDATE_SCHEDULER_MODE-external}"
  case "$FOOD_UPDATE_SCHEDULER_MODE" in
    external|disabled)
      ;;
    in_process_dev)
      echo "❌ Production deploy forbids FOOD_UPDATE_SCHEDULER_MODE=in_process_dev" >&2
      exit 1
      ;;
    *)
      echo "❌ FOOD_UPDATE_SCHEDULER_MODE must be exactly external or disabled" >&2
      exit 1
      ;;
  esac
  export FOOD_UPDATE_SCHEDULER_MODE
}

validate_shell_bundle_contract() {
  local source_frontend=""
  local source_caddyfile=""
  local source_compose=""
  local source_prometheus_config=""
  local source_prometheus_manifest=""
  local source_postgres_manifest=""
  local compose_relative_path=""
  local required_redeploy=""
  local optional_diagnose=""

  if [ -z "$SHELL_BUNDLE_DIR" ]; then
    return 0
  fi

  if [ -z "$DEPLOY_DIR" ]; then
    echo "❌ DEPLOY_DIR is required when SHELL_BUNDLE_DIR is set" >&2
    exit 1
  fi

  if [ -z "$RESOLVED_COMPOSE_FILE" ]; then
    echo "❌ Could not resolve a compose filename for shell bundle validation" >&2
    exit 1
  fi

  source_frontend="$SHELL_BUNDLE_DIR/frontend"
  source_caddyfile="$SHELL_BUNDLE_DIR/deploy/Caddyfile.production"
  source_prometheus_config="$SHELL_BUNDLE_DIR/deploy/prometheus/prometheus.yml"
  source_prometheus_manifest="$SHELL_BUNDLE_DIR/deploy/prometheus/image-manifest.json"
  source_postgres_manifest="$SHELL_BUNDLE_DIR/deploy/postgres-pgvector/image-manifest.json"

  if [[ "$RESOLVED_COMPOSE_FILE" = /* ]]; then
    case "$RESOLVED_COMPOSE_FILE" in
      "$DEPLOY_DIR"/*)
        compose_relative_path="${RESOLVED_COMPOSE_FILE#"$DEPLOY_DIR"/}"
        ;;
      *)
        echo "❌ COMPOSE_FILE must stay within DEPLOY_DIR: $RESOLVED_COMPOSE_FILE" >&2
        exit 1
        ;;
    esac
  else
    compose_relative_path="${RESOLVED_COMPOSE_FILE#./}"
    case "$compose_relative_path" in
      ""|"."|..|../*|*/../*|*/..)
        echo "❌ COMPOSE_FILE must stay within DEPLOY_DIR: $RESOLVED_COMPOSE_FILE" >&2
        exit 1
        ;;
    esac
  fi

  if [[ "$compose_relative_path" = deploy/* ]]; then
    source_compose="$SHELL_BUNDLE_DIR/$compose_relative_path"
  else
    source_compose="$SHELL_BUNDLE_DIR/deploy/$compose_relative_path"
  fi

  if [ -L "$source_frontend" ] || [ ! -d "$source_frontend" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing frontend/: $source_frontend" >&2
    exit 1
  fi

  if [ -L "$source_caddyfile" ] || [ ! -f "$source_caddyfile" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing deploy/Caddyfile.production: $source_caddyfile" >&2
    exit 1
  fi

  if [ -L "$source_compose" ] || [ ! -f "$source_compose" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing $compose_relative_path: $source_compose" >&2
    exit 1
  fi

  validate_regular_non_symlink_file "$source_prometheus_config" \
    "Incoming Prometheus configuration"
  validate_regular_non_symlink_file "$source_prometheus_manifest" \
    "Incoming Prometheus image manifest"
  validate_regular_non_symlink_file "$source_postgres_manifest" \
    "Incoming PostgreSQL image manifest"

  required_redeploy="$SHELL_BUNDLE_DIR/scripts/redeploy_caddy.sh"
  if [ -L "$required_redeploy" ] || [ ! -f "$required_redeploy" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh: $required_redeploy" >&2
    exit 1
  fi

  optional_diagnose="$SHELL_BUNDLE_DIR/scripts/diagnose_web.sh"
  if [ -L "$optional_diagnose" ]; then
    echo "❌ Optional diagnose helper must not be a symlink" >&2
    exit 1
  fi
  if [ ! -f "$optional_diagnose" ]; then
    optional_diagnose=""
  fi

  validate_prometheus_contract_identity "$source_prometheus_manifest" "$source_compose"
  if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
    validate_postgres_contract_identity "$source_postgres_manifest" "$source_compose"
  fi
  validate_full_bundle_safely \
    "$source_frontend" \
    "$source_caddyfile" \
    "$optional_diagnose" \
    "$required_redeploy"
}

run_preflight() {
  echo "Validating production secret and database contracts..."
  validate_metrics_secret_metadata
  validate_contract_destinations_safely
  validate_shell_bundle_archive
  if [ -n "$SHELL_BUNDLE_DIR" ]; then
    validate_shell_bundle_contract
  elif [ -z "$SHELL_BUNDLE_ARCHIVE" ]; then
    validate_prometheus_contract_files
    validate_prometheus_contract_identity \
      "$PROMETHEUS_IMAGE_MANIFEST" \
      "$COMPOSE_CONTRACT_PATH"
    if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
      validate_postgres_contract_files
      validate_postgres_contract_identity \
        "$POSTGRES_IMAGE_MANIFEST" \
        "$COMPOSE_CONTRACT_PATH"
    fi
  fi
  validate_production_database_contract
  validate_scheduler_mode_contract
  echo "✅ Production deploy preflight passed"
}

run_preflight
if [ "$MODE" = "preflight-only" ]; then
  exit 0
fi

trap cleanup_deploy_runtime EXIT

if [ -n "$SHELL_BUNDLE_ARCHIVE" ]; then
  extract_shell_bundle_archive
  validate_shell_bundle_contract
fi

login_to_ghcr_if_configured

sync_shell_bundle compose-only
validate_prometheus_contract_files
dc config --quiet
PROMETHEUS_RUNTIME_REF="$(read_prometheus_runtime_ref "$PROMETHEUS_IMAGE_MANIFEST")"
readonly PROMETHEUS_RUNTIME_REF
PROMETHEUS_PLATFORM_MANIFEST_DIGEST="${PROMETHEUS_RUNTIME_REF##*@}"
readonly PROMETHEUS_PLATFORM_MANIFEST_DIGEST
validate_prometheus_compose_identity "$COMPOSE_CONTRACT_PATH" "$PROMETHEUS_RUNTIME_REF"
POSTGRES_RUNTIME_REF=""
if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
  validate_postgres_contract_files
  POSTGRES_RUNTIME_REF="$(read_postgres_runtime_ref "$POSTGRES_IMAGE_MANIFEST")"
  readonly POSTGRES_RUNTIME_REF
  validate_postgres_compose_identity "$COMPOSE_CONTRACT_PATH" "$POSTGRES_RUNTIME_REF"
fi

echo "Pulling production app image..."
dc pull app

echo "Pulling production scheduler worker image..."
dc pull worker

echo "Pulling exact production Prometheus image..."
dc pull prometheus

if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
  echo "Pulling exact self-hosted PostgreSQL image..."
  dc pull postgres
fi

echo "Validating the pulled Prometheus platform manifest before product mutation..."
validate_pulled_prometheus_image "$PROMETHEUS_RUNTIME_REF"

if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
  echo "Validating the pulled PostgreSQL platform manifest before product mutation..."
  validate_pulled_postgres_image "$POSTGRES_RUNTIME_REF"
  echo "Validating the pulled PostgreSQL empty UID 70 mountpoint before product mutation..."
  validate_pulled_postgres_mountpoint "$POSTGRES_RUNTIME_REF"
fi

if ! cleanup_ghcr_credentials; then
  echo "❌ Failed to remove temporary GHCR credentials before runtime mutation" >&2
  exit 1
fi
unset GHCR_TOKEN GHCR_USER ORIGINAL_GHCR_TOKEN ORIGINAL_GHCR_USER

echo "Validating the exact Prometheus configuration before product mutation..."
dc run --rm --no-deps --entrypoint /bin/promtool prometheus \
  check config --syntax-only /etc/prometheus/prometheus.yml

echo "Invoking the canonical application production invariant before product mutation..."
dc run --rm --no-deps app python -c \
  'from app.main import app; from app.security.production_invariants import assert_production_runtime_invariants; assert_production_runtime_invariants(app=app)'

echo "Stopping the previous scheduler worker before migrations..."
dc stop worker
if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "disabled" ]; then
  echo "Removing disabled scheduler worker container..."
  dc rm -f worker
fi

echo "Production DB backups are managed outside the deploy script (provider snapshots / PITR)."

if [ "$PRODUCTION_DB_TOPOLOGY" = "self-hosted" ]; then
  echo "Starting exact self-hosted PostgreSQL image without a registry pull..."
  dc up -d --pull never postgres
  wait_for_postgres_ready 60
fi

echo "Running database migrations via one-shot release container..."
if dc run --rm --no-deps app alembic upgrade head; then
  echo "✅ Database migrations completed successfully"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed (exit code: $migration_exit_code)" >&2
  exit "$migration_exit_code"
fi

sync_shell_bundle

echo "Starting app before exposing traffic..."
dc up -d --remove-orphans app
wait_for_app_ready 30

if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then
  echo "Starting scheduler worker after app readiness..."
  dc up -d --pull never --wait --wait-timeout 30 worker
else
  echo "Scheduler mode is disabled; worker container remains absent"
fi

echo "Starting caddy after successful migrations..."
dc build caddy
dc up -d --remove-orphans caddy

# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${PRODUCTION_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=1

# Quick non-blocking HTTP smoke check (diagnostic only; expected 308 -> HTTPS redirect)
echo "Smoke check HTTP..."
if "$CURL_BIN" -sS -o /dev/null -w "HTTP:%{http_code}\n" \
    "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" \
    --max-time "${HEALTH_CURL_MAX_TIME_S}"; then
  :
else
  echo "⚠️  HTTP redirect diagnostic failed; continuing to the required HTTPS check" >&2
fi

# Main healthcheck on HTTPS (does not depend on external DNS)
echo "Healthcheck HTTPS (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS})..."
until "$CURL_BIN" -fsS --max-time "${HEALTH_CURL_MAX_TIME_S}" "$HEALTH_URL" \
    --resolve "${DOMAIN}:443:127.0.0.1" > /dev/null; do
  if [ "$attempt" -ge "$HEALTH_MAX_ATTEMPTS" ]; then
    echo "❌ Healthcheck failed after ${HEALTH_MAX_ATTEMPTS} attempts: $HEALTH_URL" >&2
    echo "Container status:"
    if dc ps; then
      :
    else
      echo "⚠️  Unable to collect container status diagnostics" >&2
    fi
    echo "Container logs (last 200 lines):"
    if dc logs --tail=200; then
      :
    else
      echo "⚠️  Unable to collect container log diagnostics" >&2
    fi
    exit 1
  fi
  echo "Healthcheck not ready (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS}), retrying in ${HEALTH_SLEEP_S}s..."
  attempt=$((attempt + 1))
  sleep "${HEALTH_SLEEP_S}"
done

if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then
  echo "Confirming scheduler worker process is running..."
  dc up -d --pull never --no-recreate --wait --wait-timeout 30 worker
fi

echo "✅ Product healthcheck OK"

echo "Starting Prometheus after complete product health..."
if dc up -d --pull never prometheus; then
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
  if dc exec -T prometheus /bin/promtool check ready \
      --url=http://localhost:9090 >/dev/null 2>&1 && \
     dc exec -T prometheus /bin/promtool check healthy \
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

echo "✅ Product and Prometheus healthchecks OK"

"$DOCKER_BIN" ps --last 20 --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
