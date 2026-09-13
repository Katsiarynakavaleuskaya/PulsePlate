#!/usr/bin/env bash
# Private, validated PostgreSQL backup through the selected Compose project.
set -euo pipefail
umask 077
PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
PROJECT_DIR="$(cd -- "$PROJECT_DIR" && pwd -P)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
ENV_FILE="${ENV_FILE:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DOCKER_BIN="${DOCKER_BIN:-$(command -v docker)}"
if [[ "$DOCKER_BIN" != /* ]] || [ ! -x "$DOCKER_BIN" ]; then
  echo "An absolute docker executable is required" >&2
  exit 1
fi
# These project/Compose names are reserved staging deployment identities.
if [ -n "$COMPOSE_FILE" ] && [ "${COMPOSE_FILE#/}" = "$COMPOSE_FILE" ]; then
  COMPOSE_FILE="$PROJECT_DIR/$COMPOSE_FILE"
fi
if [ -n "$ENV_FILE" ] && [ "${ENV_FILE#/}" = "$ENV_FILE" ]; then
  ENV_FILE="$PROJECT_DIR/$ENV_FILE"
fi
if [ "$PROJECT_DIR" = "/srv/pulseplate-staging" ] || \
   [ "${COMPOSE_FILE##*/}" = "docker-compose.staging.yaml" ]; then
  PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
  admitted_backup_dir="$("$PYTHON_BIN" "$PROJECT_DIR/scripts/ops/check_staging_security.py" --project-dir "$PROJECT_DIR" --storage-only --print-backup-dir)"
  if [ "$BACKUP_DIR" != "$admitted_backup_dir" ]; then
    echo "Staging backup destination must be the admitted encrypted directory" >&2
    exit 1
  fi
fi
if [ -L "$BACKUP_DIR" ]; then
  echo "Backup destination must not be a symlink" >&2
  exit 1
fi
mkdir -p "$BACKUP_DIR"
compose_exec() {
  local compose_cmd=("$DOCKER_BIN" compose)
  if [ -n "$ENV_FILE" ]; then compose_cmd+=(--env-file "$ENV_FILE"); fi
  compose_cmd+=(--project-directory "$PROJECT_DIR")
  if [ -n "$COMPOSE_FILE" ]; then compose_cmd+=(-f "$COMPOSE_FILE"); fi
  "${compose_cmd[@]}" exec -T postgres "$@"
}
TEMP_DIR="$(mktemp -d "$BACKUP_DIR/.pulseplate-backup.XXXXXXXX")"
cleanup() {
  local original_status=$?
  trap - EXIT
  if ! rm -r -- "$TEMP_DIR"; then
    if [ "$original_status" -eq 0 ]; then original_status=1; fi
  fi
  exit "$original_status"
}
trap cleanup EXIT
PARTIAL="$TEMP_DIR/backup.dump"
if [ -n "${POSTGRES_USER:-}" ] || [ -n "${POSTGRES_DB:-}" ]; then
  : "${POSTGRES_USER:?POSTGRES_USER is required when POSTGRES_DB is supplied}"
  : "${POSTGRES_DB:?POSTGRES_DB is required when POSTGRES_USER is supplied}"
  compose_exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$PARTIAL"
else
  compose_exec sh -euc 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$PARTIAL"
fi
if [ ! -s "$PARTIAL" ] || [ -L "$PARTIAL" ]; then
  echo "Backup must be a nonempty regular custom dump" >&2
  exit 1
fi
compose_exec pg_restore --list < "$PARTIAL" > "$TEMP_DIR/contents.list"
if ! awk '$4 == "TABLE" && $5 == "public" { found = 1 } END { exit !found }' "$TEMP_DIR/contents.list"; then
  echo "Backup has no substantive public table inventory" >&2
  exit 1
fi
# Consume the complete archive, not only its table of contents, before pruning older backups.
compose_exec pg_restore --file=/dev/null < "$PARTIAL"
OUTPUT="$BACKUP_DIR/pulseplate_${TIMESTAMP}_${TEMP_DIR##*.}.dump"
# Atomic no-clobber publication on the same filesystem; cleanup removes the temporary link.
ln "$PARTIAL" "$OUTPUT"
find "$BACKUP_DIR" -type f -name 'pulseplate_*.dump' -mtime +7 -delete
echo "Backup created: $OUTPUT"
