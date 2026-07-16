#!/usr/bin/env bash
# Backup Postgres database for PulsePlate production/staging.
# Usage: [DOCKER_BIN=/absolute/path/to/docker] [POSTGRES_USER=... POSTGRES_DB=...]
#        [PROJECT_DIR=...] [BACKUP_DIR=...] [COMPOSE_FILE=...] scripts/ops/postgres_backup.sh
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
BACKUP_DIR="${BACKUP_DIR:-/srv/pulseplate-production/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

DOCKER_BIN="${DOCKER_BIN:-}"
if [ -z "$DOCKER_BIN" ]; then
  DOCKER_BIN="$(command -v docker || :)"
fi
if [ -z "$DOCKER_BIN" ] || [ ! -x "$DOCKER_BIN" ]; then
  echo "docker executable is required" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

if [ -n "${COMPOSE_FILE}" ] && [ "${COMPOSE_FILE#/}" = "${COMPOSE_FILE}" ]; then
  COMPOSE_FILE="${PROJECT_DIR}/${COMPOSE_FILE}"
fi

compose_exec() {
  local compose_cmd=("$DOCKER_BIN" compose --project-directory "${PROJECT_DIR}")
  if [ -n "${COMPOSE_FILE}" ]; then
    compose_cmd+=(-f "${COMPOSE_FILE}")
  fi
  "${compose_cmd[@]}" exec -T postgres "$@"
}

OUTPUT="${BACKUP_DIR}/pulseplate_${TIMESTAMP}.dump"
if [ -n "${POSTGRES_USER:-}" ] || [ -n "${POSTGRES_DB:-}" ]; then
  : "${POSTGRES_USER:?POSTGRES_USER is required when POSTGRES_DB is supplied}"
  : "${POSTGRES_DB:?POSTGRES_DB is required when POSTGRES_USER is supplied}"
  compose_exec \
    pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
    > "${OUTPUT}" || { rm -f "${OUTPUT}"; exit 1; }
else
  compose_exec sh -euc \
    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "${OUTPUT}" || { rm -f "${OUTPUT}"; exit 1; }
fi

find "${BACKUP_DIR}" -type f -name 'pulseplate_*.dump' -mtime +7 -delete

echo "Backup created: ${OUTPUT}"
