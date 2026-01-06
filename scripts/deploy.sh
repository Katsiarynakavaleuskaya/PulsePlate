#!/usr/bin/env bash
# RU: Атомарный деплой на staging. Требует: docker, docker-compose, доступ к GHCR.
set -euo pipefail

# Validate required environment variables
STAGING_DOMAIN=${STAGING_DOMAIN:?"STAGING_DOMAIN not set"}
GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-30}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

IMG_REF="${1:-latest}"         # тег/диджест образа
COMPOSE="docker compose -f /srv/pulseplate-staging/docker-compose.staging.yaml"

# Warn if using latest tag (should be specific commit SHA in production)
if [ "$IMG_REF" = "latest" ]; then
  echo "⚠️  WARNING: Using 'latest' tag. For production deployments, use specific commit SHA tags."
  echo "   CD workflow should pass the exact image tag (e.g., git SHA) to ensure consistency."
fi

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

# Get the actual container name dynamically (trim whitespace)
APP_CONTAINER=$($COMPOSE ps -q app | tr -d '\n\r ')
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
echo "Running database migrations in container: $APP_CONTAINER"
if docker exec "$APP_CONTAINER" alembic upgrade head; then
  echo "✅ Database migrations completed successfully in container: $APP_CONTAINER"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed in container: $APP_CONTAINER (exit code: $migration_exit_code)" >&2
  echo "Check container logs with: docker logs $APP_CONTAINER" >&2
  exit $migration_exit_code
fi

echo "[post] Smoke check with retry"
# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${STAGING_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/health"
attempt=0

# Quick smoke check on HTTP (should return 308 redirect to HTTPS)
echo "Smoke check HTTP..."
curl -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/health" --resolve "${DOMAIN}:80:127.0.0.1" --max-time "${HEALTH_CURL_MAX_TIME_S}" || true

# Main healthcheck on HTTPS (does not depend on external DNS)
while [ $attempt -lt "$HEALTH_MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$HEALTH_MAX_ATTEMPTS..."

  # Use --resolve to avoid DNS dependency
  curl_output=$(curl -fsS --max-time "${HEALTH_CURL_MAX_TIME_S}" "${HEALTH_URL}" \
    --resolve "${DOMAIN}:443:127.0.0.1" 2>&1)
  curl_exit_code=$?

  if [ $curl_exit_code -eq 0 ]; then
    echo "✅ Health check successful"
    break
  else
    echo "❌ Health check failed (exit code: $curl_exit_code)" >&2
    echo "Error details: $curl_output" >&2

    if [ $attempt -eq "$HEALTH_MAX_ATTEMPTS" ]; then
      echo "❌ Health check failed after ${HEALTH_MAX_ATTEMPTS} attempts" >&2
      echo "Final error: $curl_output" >&2
      exit 1
    fi

    echo "Waiting ${HEALTH_SLEEP_S} seconds before retry..."
    sleep "${HEALTH_SLEEP_S}"
  fi
done

echo "✅ Healthcheck OK"

echo "✅ Staging deployed: $IMG_REF"
