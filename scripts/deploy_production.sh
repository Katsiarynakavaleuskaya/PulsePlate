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
readonly PROMETHEUS_CONFIG PROMETHEUS_IMAGE_MANIFEST
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

  echo "Logging in to ghcr.io with deploy credentials..."
  printf '%s\n' "$GHCR_TOKEN" | "$DOCKER_BIN" login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
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

contract_destination_transaction() {
  local operation="$1"
  local source_compose="${2:-}"
  local source_prometheus_config="${3:-}"
  local source_prometheus_manifest="${4:-}"

  "$PYTHON_BIN" - \
    "$operation" \
    "$REQUESTED_DEPLOY_DIR" \
    "$source_compose" \
    "$COMPOSE_RELATIVE_IDENTITY" \
    "$source_prometheus_config" \
    "deploy/prometheus/prometheus.yml" \
    "$source_prometheus_manifest" \
    "deploy/prometheus/image-manifest.json" <<'PY'
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

if operation not in {"validate", "publish"}:
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

no_follow = getattr(os, "O_NOFOLLOW", 0)
directory_flag = getattr(os, "O_DIRECTORY", 0)
if no_follow <= 0 or directory_flag <= 0:
    raise SystemExit("descriptor no-follow directory validation is unavailable")
directory_open_flags = os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0)


def open_existing_directory(parent_fd: int, component: str) -> int:
    try:
        metadata = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise SystemExit("contract destination parent is missing") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise SystemExit("contract destination parent must be a real directory")
    try:
        descriptor = os.open(component, directory_open_flags, dir_fd=parent_fd)
    except OSError as exc:
        raise SystemExit("contract destination parent cannot be opened safely") from exc
    opened_metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(opened_metadata.st_mode):
        os.close(descriptor)
        raise SystemExit("contract destination parent identity changed")
    return descriptor


def ensure_directory(parent_fd: int, component: str, *, create: bool) -> int | None:
    try:
        return open_existing_directory(parent_fd, component)
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
                raise SystemExit("contract destination directory cannot be created safely") from exc
            return open_existing_directory(parent_fd, component)
        if not stat.S_ISDIR(metadata.st_mode):
            raise SystemExit("contract destination parent must be a real directory")
        raise


def validate_leaf(parent_fd: int, leaf: str) -> None:
    try:
        metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(metadata.st_mode):
        raise SystemExit("contract destination leaf must be absent or a regular file")


def split_target(raw_target: str) -> tuple[str, ...]:
    pure_path = PurePosixPath(raw_target)
    if pure_path.is_absolute() or str(pure_path) != raw_target:
        raise SystemExit("contract destination path is not canonical")
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise SystemExit("contract destination path is not bounded")
    return pure_path.parts


root_fd = os.open("/", directory_open_flags)
walk_fd = root_fd
deploy_fd: int | None = None
directory_fds: list[int] = []
try:
    for component in Path(requested_deploy_dir).parts[1:]:
        next_fd = open_existing_directory(walk_fd, component)
        if walk_fd != root_fd:
            os.close(walk_fd)
        walk_fd = next_fd
    deploy_fd = walk_fd
    directory_fds.append(deploy_fd)

    targets = [compose_target, config_target, manifest_target]
    target_parts = {target: split_target(target) for target in targets}
    deploy_contract_fd = ensure_directory(deploy_fd, "deploy", create=False)
    if deploy_contract_fd is None:
        raise SystemExit("canonical deploy contract directory is missing")
    directory_fds.append(deploy_contract_fd)

    prometheus_fd = ensure_directory(
        deploy_contract_fd,
        "prometheus",
        create=operation == "publish",
    )
    if prometheus_fd is not None:
        directory_fds.append(prometheus_fd)

    parent_by_target: dict[str, int | None] = {
        compose_target: deploy_contract_fd,
        config_target: prometheus_fd,
        manifest_target: prometheus_fd,
    }
    for target in targets:
        parent_fd = parent_by_target[target]
        if parent_fd is not None:
            validate_leaf(parent_fd, target_parts[target][-1])

    if operation == "validate":
        raise SystemExit(0)
    if prometheus_fd is None:
        raise SystemExit("Prometheus contract directory was not created")

    sources = {
        compose_target: source_compose,
        config_target: source_config,
        manifest_target: source_manifest,
    }
    prepared: list[tuple[int, str, str]] = []
    max_contract_bytes = 4 * 1024 * 1024
    try:
        for target in (config_target, manifest_target, compose_target):
            source_path = sources[target]
            if not os.path.isabs(source_path):
                raise SystemExit("contract source path must be absolute")
            source_fd = os.open(
                source_path,
                os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
            )
            try:
                source_metadata = os.fstat(source_fd)
                if (
                    not stat.S_ISREG(source_metadata.st_mode)
                    or source_metadata.st_nlink != 1
                    or source_metadata.st_size <= 0
                    or source_metadata.st_size > max_contract_bytes
                ):
                    raise SystemExit("contract source must be one bounded regular file")

                parent_fd = parent_by_target[target]
                if parent_fd is None:
                    raise SystemExit("contract destination parent is unavailable")
                leaf = target_parts[target][-1]
                temp_name = f".pulseplate-{leaf}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
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
                    remaining = source_metadata.st_size
                    while remaining:
                        chunk = os.read(source_fd, min(1024 * 1024, remaining))
                        if not chunk:
                            raise SystemExit("contract source changed during publication")
                        view = memoryview(chunk)
                        while view:
                            written = os.write(temp_fd, view)
                            if written <= 0:
                                raise SystemExit("contract destination write failed")
                            view = view[written:]
                        remaining -= len(chunk)
                    if os.read(source_fd, 1):
                        raise SystemExit("contract source grew during publication")
                    os.fchmod(temp_fd, 0o644)
                    os.fsync(temp_fd)
                finally:
                    os.close(temp_fd)
                prepared.append((parent_fd, temp_name, leaf))
            finally:
                os.close(source_fd)

        for parent_fd, temp_name, leaf in prepared:
            os.replace(
                temp_name,
                leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
    finally:
        for parent_fd, temp_name, _leaf in prepared:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
finally:
    for descriptor in reversed(directory_fds):
        if descriptor != root_fd:
            try:
                os.close(descriptor)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise
    os.close(root_fd)
PY
}

validate_contract_destinations_safely() {
  contract_destination_transaction validate "" "" ""
}

publish_contract_files_safely() {
  local source_compose="$1"
  local source_prometheus_config="$2"
  local source_prometheus_manifest="$3"
  contract_destination_transaction publish \
    "$source_compose" \
    "$source_prometheus_config" \
    "$source_prometheus_manifest"
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
    "deploy/prometheus/image-manifest.json",
    "deploy/prometheus/prometheus.yml",
    "scripts/diagnose_web.sh",
    "scripts/redeploy_caddy.sh",
}
allowed_directories = {"frontend", "deploy", "deploy/prometheus", "scripts"}
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
  local validation_status=0
  if process_shell_bundle_archive validate "$validation_root"; then
    validation_status=0
  else
    validation_status=$?
  fi
  rm -rf -- "$validation_root"
  return "$validation_status"
}

extract_shell_bundle_archive() {
  if [ -z "$SHELL_BUNDLE_ARCHIVE" ]; then
    return 0
  fi

  ARCHIVE_EXTRACT_DIR="$(mktemp -d /tmp/pulseplate-shell-bundle-extract.XXXXXX)"
  chmod 700 "$ARCHIVE_EXTRACT_DIR"
  process_shell_bundle_archive extract "$ARCHIVE_EXTRACT_DIR"
  SHELL_BUNDLE_DIR="$ARCHIVE_EXTRACT_DIR/payload"
}

cleanup_shell_bundle_archive() {
  if [ -n "$ARCHIVE_EXTRACT_DIR" ]; then
    case "$ARCHIVE_EXTRACT_DIR" in
      /tmp/pulseplate-shell-bundle-extract.*)
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
  local source_diagnose="$SHELL_BUNDLE_DIR/scripts/diagnose_web.sh"
  local source_redeploy="$SHELL_BUNDLE_DIR/scripts/redeploy_caddy.sh"
  local compose_relative_path="$COMPOSE_RELATIVE_IDENTITY"
  local shell_root
  local target_scripts_dir="$DEPLOY_DIR/scripts"
  shell_root="$(cd "$DEPLOY_DIR/.." && pwd)"

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

  if [ -L "$source_redeploy" ] || [ ! -f "$source_redeploy" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh: $source_redeploy" >&2
    exit 1
  fi

  publish_contract_files_safely \
    "$source_compose" \
    "$source_prometheus_config" \
    "$source_prometheus_manifest"
  if [ "$sync_mode" = "compose-only" ]; then
    echo "Synced production Compose and Prometheus contracts before worker operations"
    return 0
  fi

  echo "Syncing production shell bundle from: $SHELL_BUNDLE_DIR"
  rm -rf "$shell_root/frontend"
  mkdir -p "$shell_root/frontend" "$target_scripts_dir"
  cp -R "$source_frontend/." "$shell_root/frontend/"
  cp "$source_caddyfile" "$DEPLOY_DIR/Caddyfile.production"
  rm -f "$target_scripts_dir/diagnose_web.sh" "$target_scripts_dir/redeploy_caddy.sh"

  if [ -L "$source_diagnose" ]; then
    echo "❌ Optional diagnose helper must not be a symlink" >&2
    exit 1
  fi
  if [ -f "$source_diagnose" ]; then
    cp "$source_diagnose" "$target_scripts_dir/diagnose_web.sh"
    chmod +x "$target_scripts_dir/diagnose_web.sh"
  fi

  cp "$source_redeploy" "$target_scripts_dir/redeploy_caddy.sh"
  chmod +x "$target_scripts_dir/redeploy_caddy.sh"
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
  local compose_relative_path=""
  local required_redeploy=""

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

  required_redeploy="$SHELL_BUNDLE_DIR/scripts/redeploy_caddy.sh"
  if [ -L "$required_redeploy" ] || [ ! -f "$required_redeploy" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh: $required_redeploy" >&2
    exit 1
  fi
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
  fi
  validate_production_database_contract
  validate_scheduler_mode_contract
  echo "✅ Production deploy preflight passed"
}

run_preflight
if [ "$MODE" = "preflight-only" ]; then
  exit 0
fi

if [ -n "$SHELL_BUNDLE_ARCHIVE" ]; then
  trap cleanup_shell_bundle_archive EXIT
  extract_shell_bundle_archive
  validate_shell_bundle_contract
fi

login_to_ghcr_if_configured

sync_shell_bundle compose-only
validate_prometheus_contract_files
dc config --quiet

echo "Pulling production app image..."
dc pull app

echo "Pulling production scheduler worker image..."
dc pull worker

echo "Pulling exact production Prometheus image..."
dc pull prometheus

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
