#!/usr/bin/env bash
# RU: Атомарный деплой на staging. Требует: docker, docker-compose, доступ к GHCR.
set -euo pipefail

# Validate required environment variables
STAGING_DOMAIN=${STAGING_DOMAIN:?"STAGING_DOMAIN not set"}
GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}

IMG_REF="${1:-latest}"         # тег/диджест образа
COMPOSE="docker compose -f /srv/pulseplate-staging/docker-compose.staging.yaml"

echo "[1/4] Login GHCR"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/4] Pull image $IMG_REF"
export TAG="$IMG_REF"
$COMPOSE pull app

echo "[3/4] Start stack and DB backup"
# Start the stack first to ensure network exists
$COMPOSE up -d app caddy

# Wait for network to be ready
sleep 5

# Create database backup if it exists
DB_PATH="/srv/pulseplate-staging/data/app.db"
if [ -f "$DB_PATH" ]; then
  timestamp=$(date +"%Y%m%d_%H%M%S")
  backup_path="/srv/pulseplate-staging/data/app.db.backup-$timestamp"
  echo "Creating database backup: $backup_path"
  cp "$DB_PATH" "$backup_path"

  # Remove old backups (keep last 5)
  ls -t /srv/pulseplate-staging/data/app.db.backup-* 2>/dev/null | tail -n +6 | xargs -r rm -f
  echo "Database backup completed"
else
  echo "No existing database found, skipping backup"
fi

echo "[4/4] Run migrations"
# Run migrations with network now available
docker run --rm --network=pulseplate-staging_web --env-file /srv/pulseplate-staging/.env ghcr.io/katsiarynakavaleuskaya/pulseplate:$TAG alembic upgrade head

echo "[post] Smoke check with retry"
max_attempts=30
attempt=0
until curl -fsS "https://${STAGING_DOMAIN}/health" >/dev/null || [ $attempt -eq $max_attempts ]; do
  attempt=$((attempt + 1))
  echo "Attempt $attempt/$max_attempts - waiting for health endpoint..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "❌ Health check failed after ${max_attempts} attempts"
  exit 1
fi

echo "✅ Staging deployed: $IMG_REF"
