#!/usr/bin/env bash
# Backup Postgres database for PulsePlate production.
# Usage: POSTGRES_USER=... POSTGRES_DB=... [PROJECT_DIR=...] [BACKUP_DIR=...] scripts/ops/postgres_backup.sh
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-production}"
BACKUP_DIR="${BACKUP_DIR:-/srv/pulseplate-production/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

cd "${PROJECT_DIR}"

docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${BACKUP_DIR}/pulseplate_${TIMESTAMP}.dump"

find "${BACKUP_DIR}" -type f -name 'pulseplate_*.dump' -mtime +7 -delete

echo "Backup created: ${BACKUP_DIR}/pulseplate_${TIMESTAMP}.dump"
