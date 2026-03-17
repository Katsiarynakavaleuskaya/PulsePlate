#!/usr/bin/env bash
# Restore Postgres database from backup.
# Usage: POSTGRES_USER=... POSTGRES_DB=... scripts/ops/postgres_restore.sh /absolute/path/to/backup.dump
set -euo pipefail

if [ "${#}" -ne 1 ]; then
  echo "Usage: $0 /absolute/path/to/backup.dump"
  exit 1
fi

BACKUP_FILE="$1"
PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

cd "${PROJECT_DIR}"

docker compose exec -T postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

docker compose exec -T postgres \
  pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists \
  < "${BACKUP_FILE}"

echo "Restore completed from: ${BACKUP_FILE}"
