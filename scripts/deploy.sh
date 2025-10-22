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

# Wait for app container to be ready with active checks
echo "Waiting for app container to be ready..."
max_wait=60
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  if $COMPOSE ps app | grep -q "Up"; then
    echo "App container is running"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app container... ($wait_count/$max_wait)"
  sleep 1
done

if [ $wait_count -eq $max_wait ]; then
  echo "❌ App container failed to start within $max_wait seconds"
  exit 1
fi

# Get the actual container name dynamically
APP_CONTAINER=$($COMPOSE ps -q app)
if [ -z "$APP_CONTAINER" ]; then
  echo "❌ Failed to find app container"
  exit 1
fi
echo "Using app container: $APP_CONTAINER"

# Create database backup if it exists in the running container
if docker exec "$APP_CONTAINER" test -f /app/cache/app.db 2>/dev/null; then
  timestamp=$(date +"%Y%m%d_%H%M%S")
  backup_dir="/srv/pulseplate-staging/backups"
  mkdir -p "$backup_dir"
  backup_path="$backup_dir/app.db.backup-$timestamp"
  echo "Creating database backup: $backup_path"
  docker cp "$APP_CONTAINER:/app/cache/app.db" "$backup_path"

  # Remove old backups (keep last 5)
  ls -t "$backup_dir"/app.db.backup-* 2>/dev/null | tail -n +6 | xargs -r rm -f
  echo "Database backup completed"
else
  echo "No existing database found, skipping backup"
fi

echo "[4/4] Run migrations"
# Wait for app to be ready to accept connections
echo "Waiting for app to be ready for migrations..."
max_wait=30
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  if docker exec "$APP_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" 2>/dev/null; then
    echo "App is ready for migrations"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app readiness... ($wait_count/$max_wait)"
  sleep 1
done

if [ $wait_count -eq $max_wait ]; then
  echo "❌ App failed to become ready within $max_wait seconds"
  exit 1
fi

# Run migrations in the live app container
docker exec "$APP_CONTAINER" alembic upgrade head

echo "[post] Smoke check with retry"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$max_attempts..."

  # Capture curl output and errors
  curl_output=$(curl -fsS "https://${STAGING_DOMAIN}/health" 2>&1)
  curl_exit_code=$?

  if [ $curl_exit_code -eq 0 ]; then
    echo "✅ Health check successful"
    break
  else
    echo "❌ Health check failed (exit code: $curl_exit_code)" >&2
    echo "Error details: $curl_output" >&2

    if [ $attempt -eq $max_attempts ]; then
      echo "❌ Health check failed after ${max_attempts} attempts" >&2
      echo "Final error: $curl_output" >&2
      exit 1
    fi

    echo "Waiting 2 seconds before retry..."
    sleep 2
  fi
done

echo "✅ Staging deployed: $IMG_REF"
