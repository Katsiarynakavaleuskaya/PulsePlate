#!/usr/bin/env bash
# Backup Postgres database for PulsePlate production/staging.
# Usage: POSTGRES_USER=... POSTGRES_DB=... [PROJECT_DIR=...] [BACKUP_DIR=...] [COMPOSE_FILE=...] scripts/ops/postgres_backup.sh
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
BACKUP_DIR="${BACKUP_DIR:-/srv/pulseplate-production/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

mkdir -p "${BACKUP_DIR}"

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

OUTPUT="${BACKUP_DIR}/pulseplate_${TIMESTAMP}.dump"
compose_exec \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${OUTPUT}" || { rm -f "${OUTPUT}"; exit 1; }

find "${BACKUP_DIR}" -type f -name 'pulseplate_*.dump' -mtime +7 -delete

echo "Backup created: ${OUTPUT}"
