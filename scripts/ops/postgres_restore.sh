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
# These project/Compose names are reserved staging deployment identities.
PROJECT_DIR="$(cd -- "$PROJECT_DIR" && pwd -P)"
RESTORE_TEMP_ROOT="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
if [ -n "$COMPOSE_FILE" ] && [ "${COMPOSE_FILE#/}" = "$COMPOSE_FILE" ]; then COMPOSE_FILE="$PROJECT_DIR/$COMPOSE_FILE"; fi
if [ -n "$ENV_FILE" ] && [ "${ENV_FILE#/}" = "$ENV_FILE" ]; then ENV_FILE="$PROJECT_DIR/$ENV_FILE"; fi
if [ "$PROJECT_DIR" = "/srv/pulseplate-staging" ] || \
   [ "${COMPOSE_FILE##*/}" = "docker-compose.staging.yaml" ]; then
  PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
  RESTORE_TEMP_ROOT="$("$PYTHON_BIN" "$PROJECT_DIR/scripts/ops/check_staging_security.py" --project-dir "$PROJECT_DIR" --storage-only --print-backup-dir)"
  if [ -n "${BACKUP_DIR:-}" ] && [ "$BACKUP_DIR" != "$RESTORE_TEMP_ROOT" ]; then
    echo "Staging restore temporary storage must use the admitted encrypted directory" >&2
    exit 1
  fi
fi
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
  compose_exec createdb -U "$POSTGRES_USER" --maintenance-db "$POSTGRES_DB" \
    --owner "$POSTGRES_USER" "$TARGET_DB"
  compose_exec pg_restore -U "$POSTGRES_USER" -d "$TARGET_DB" \
    --exit-on-error --single-transaction --clean --if-exists < "$BACKUP_FILE"
  restored_tables="$(compose_exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$TARGET_DB" \
    -c "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public';")"
  if [ "$restored_tables" != "$expected_tables" ]; then
    echo "Restored table inventory differs from the validated archive" >&2
    exit 1
  fi
else
  # This replacement contract covers public-schema archives only. Native
  # filtering owns namespace selection; unknown global descriptors fail closed.
  outside_public="$(compose_exec pg_restore --list --exclude-schema=public < "$BACKUP_FILE")"
  if ! printf '%s\n' "$outside_public" | awk '
    /^;/ || /^[[:space:]]*$/ { next }
    $4 == "SCHEMA" && $5 == "-" && $6 == "public" { next }
    $4 == "EXTENSION" && $5 == "-" { next }
    $4 == "COMMENT" && $5 == "-" && $6 == "EXTENSION" { next }
    ($4 == "COMMENT" || $4 == "ACL") && $5 == "-" && $6 == "SCHEMA" && $7 == "public" { next }
    $4 == "ENCODING" || $4 == "STDSTRINGS" || $4 == "SEARCHPATH" { next }
    { exit 1 }
  '; then
    echo "Replacement restore HOLD: archive contains unsupported non-public schema or global objects" >&2
    exit 1
  fi
  target_boundary="$(compose_exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$TARGET_DB" \
    -c "SELECT NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname <> 'public' AND nspname <> 'information_schema' AND nspname !~ '^pg_') AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_largeobject_metadata);")"
  if [ "$target_boundary" != "t" ]; then
    echo "Replacement restore HOLD: target contains unsupported non-public schema or large objects" >&2
    exit 1
  fi
  if [ -L "$RESTORE_TEMP_ROOT" ]; then
    echo "Restore temporary storage must not be a symlink" >&2
    exit 1
  fi
  mkdir -p "$RESTORE_TEMP_ROOT"
  RESTORE_TEMP_DIR="$(mktemp -d "$RESTORE_TEMP_ROOT/.pulseplate-restore.XXXXXXXX")"
  cleanup_restore() {
    local original_status=$?
    trap - EXIT
    if ! rm -r -- "$RESTORE_TEMP_DIR"; then
      if [ "$original_status" -eq 0 ]; then original_status=1; fi
    fi
    exit "$original_status"
  }
  trap cleanup_restore EXIT
  # Fully render the archive before opening a database transaction. A failed
  # renderer cannot let a downstream psql commit a partial producer stream.
  compose_exec pg_restore --clean --if-exists --file=- < "$BACKUP_FILE" > "$RESTORE_TEMP_DIR/archive.sql"
  if [ ! -s "$RESTORE_TEMP_DIR/archive.sql" ]; then
    echo "Replacement restore HOLD: native SQL rendering is empty" >&2
    exit 1
  fi
  # Ordinary pg_dump may record public ownership without CREATE SCHEMA.
  # Always provide public first. For explicit schema dumps, native --clean
  # drops that empty schema before recreating it; preserve the complete SQL.
  {
    # Repeat the target boundary inside the same transaction before deletion.
    printf '%s\n' "DO \$\$ BEGIN IF EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname <> 'public' AND nspname <> 'information_schema' AND nspname !~ '^pg_') OR EXISTS (SELECT 1 FROM pg_catalog.pg_largeobject_metadata) THEN RAISE EXCEPTION 'Replacement target exceeds public schema boundary'; END IF; END \$\$;"
    printf '%s\n' 'DROP SCHEMA IF EXISTS public CASCADE;'
    printf '%s\n' 'CREATE SCHEMA public;'
    cat "$RESTORE_TEMP_DIR/archive.sql"
    printf '\n%s\n' "DO \$\$ BEGIN IF (SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public') <> $expected_tables OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname <> 'public' AND nspname <> 'information_schema' AND nspname !~ '^pg_') OR EXISTS (SELECT 1 FROM pg_catalog.pg_largeobject_metadata) THEN RAISE EXCEPTION 'Restored inventory differs from the public archive'; END IF; END \$\$;"
  } > "$RESTORE_TEMP_DIR/replacement.sql"
  # Schema reset, native restore and inventory assertions commit or roll back
  # together. ON_ERROR_STOP prevents any SQL error from reaching COMMIT.
  compose_exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$TARGET_DB" \
    --single-transaction --file=- < "$RESTORE_TEMP_DIR/replacement.sql"
fi
echo "Restore completed into: $TARGET_DB"
