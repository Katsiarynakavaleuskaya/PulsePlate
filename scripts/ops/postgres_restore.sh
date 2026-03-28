#!/usr/bin/env bash
# Restore Postgres database from backup.
# Usage: POSTGRES_USER=... POSTGRES_DB=... [PROJECT_DIR=...] [COMPOSE_FILE=...] scripts/ops/postgres_restore.sh path/to/backup.dump
set -euo pipefail

if [ "${#}" -ne 1 ]; then
  echo "Usage: $0 path/to/backup.dump"
  exit 1
fi

BACKUP_FILE="$1"
PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
COMPOSE_FILE="${COMPOSE_FILE:-}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

# Resolve to absolute path so relative paths work from cwd (Cubic r2946901107)
if [ "${BACKUP_FILE#/}" = "${BACKUP_FILE}" ]; then
  BACKUP_FILE="$(cd "$(dirname "${BACKUP_FILE}")" && pwd)/$(basename "${BACKUP_FILE}")"
fi

if [ -n "${COMPOSE_FILE}" ] && [ "${COMPOSE_FILE#/}" = "${COMPOSE_FILE}" ]; then
  COMPOSE_FILE="${PROJECT_DIR}/${COMPOSE_FILE}"
fi

compose_exec() {
  local compose_cmd=(docker compose --project-directory "${PROJECT_DIR}")
  if [ -n "${COMPOSE_FILE}" ]; then
    compose_cmd+=(-f "${COMPOSE_FILE}")
  fi
  "${compose_cmd[@]}" exec -T postgres "$@"
}

compose_exec \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

compose_exec \
  pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists \
  < "${BACKUP_FILE}"

echo "Restore completed from: ${BACKUP_FILE}"
