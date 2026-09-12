#!/usr/bin/env bash
# Restore only into an explicitly named isolated target, or an explicitly replaced database.
set -euo pipefail
umask 077
if [ "$#" -ne 3 ]; then
  echo "Usage: postgres_restore.sh --verify-into TARGET_DB BACKUP.dump" >&2
  echo "       postgres_restore.sh --replace-existing TARGET_DB BACKUP.dump" >&2
  exit 2
fi
MODE="$1"
TARGET_DB="$2"
BACKUP_FILE="$3"
PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
ENV_FILE="${ENV_FILE:-}"
DOCKER_BIN="${DOCKER_BIN:-$(command -v docker)}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB identifies the source database}"
if [[ "$DOCKER_BIN" != /* ]] || [ ! -x "$DOCKER_BIN" ]; then
  echo "An absolute docker executable is required" >&2
  exit 1
fi
if [[ ! "$TARGET_DB" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
  echo "Invalid PostgreSQL restore target" >&2
  exit 2
fi
case "$MODE" in
  --verify-into)
    if [ "$TARGET_DB" = "$POSTGRES_DB" ] || \
       [[ ! "$TARGET_DB" =~ ^pulseplate_restore_check_[a-z0-9_]+$ ]]; then
      echo "Verification restore requires a distinct pulseplate_restore_check_ target" >&2
      exit 2
    fi
    ;;
  --replace-existing) ;;
  *) echo "An explicit restore mode is required" >&2; exit 2 ;;
esac
if [ -L "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
  echo "Backup must be a nonempty regular non-symlink file" >&2
  exit 1
fi
if [ "$PROJECT_DIR" = "/srv/pulseplate-staging" ] || \
   [ "${COMPOSE_FILE##*/}" = "docker-compose.staging.yaml" ]; then
  PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
  "$PYTHON_BIN" "$PROJECT_DIR/scripts/ops/check_staging_security.py" --project-dir "$PROJECT_DIR" --storage-only
fi
if [ -n "$COMPOSE_FILE" ] && [ "${COMPOSE_FILE#/}" = "$COMPOSE_FILE" ]; then COMPOSE_FILE="$PROJECT_DIR/$COMPOSE_FILE"; fi
if [ -n "$ENV_FILE" ] && [ "${ENV_FILE#/}" = "$ENV_FILE" ]; then ENV_FILE="$PROJECT_DIR/$ENV_FILE"; fi
compose_exec() {
  local compose_cmd=("$DOCKER_BIN" compose)
  if [ -n "$ENV_FILE" ]; then compose_cmd+=(--env-file "$ENV_FILE"); fi
  compose_cmd+=(--project-directory "$PROJECT_DIR")
  if [ -n "$COMPOSE_FILE" ]; then compose_cmd+=(-f "$COMPOSE_FILE"); fi
  "${compose_cmd[@]}" exec -T postgres "$@"
}
# Validate the complete archive before any database mutation.
archive_list="$(compose_exec pg_restore --list < "$BACKUP_FILE")"
expected_tables="$(printf '%s\n' "$archive_list" | awk '$4 == "TABLE" && $5 == "public" { n++ } END { print n+0 }')"
if [ "$expected_tables" -eq 0 ]; then
  echo "Restore archive contains no substantive public tables" >&2
  exit 1
fi
compose_exec pg_restore --file=/dev/null < "$BACKUP_FILE" > /dev/null
if [ "$MODE" = "--verify-into" ]; then
  # createdb fails if the target already exists; it never replaces an existing database.
  compose_exec createdb -U "$POSTGRES_USER" --owner "$POSTGRES_USER" "$TARGET_DB"
fi
compose_exec pg_restore -U "$POSTGRES_USER" -d "$TARGET_DB" \
  --exit-on-error --single-transaction --clean --if-exists < "$BACKUP_FILE"
restored_tables="$(compose_exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$TARGET_DB" \
  -c "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public';")"
if [ "$restored_tables" != "$expected_tables" ]; then
  echo "Restored table inventory differs from the validated archive" >&2
  exit 1
fi
echo "Restore completed into: $TARGET_DB"
