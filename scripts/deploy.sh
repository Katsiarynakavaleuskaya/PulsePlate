#!/usr/bin/env bash
# RU: Атомарный деплой на staging. Требует: docker, docker-compose, доступ к GHCR.
set -euo pipefail

PROJECT_DIR="/srv/pulseplate-staging"
ENV_FILE="${PROJECT_DIR}/.env"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.staging.yaml"
BACKUP_DIR="${PROJECT_DIR}/backups"
BACKUP_HELPER="${PROJECT_DIR}/scripts/ops/postgres_backup.sh"
COMPOSE=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}")

# RU: Загружаем server-local env до валидации, чтобы backup и migrations видели
# обязательные Postgres переменные.
# EN: Load server-local env before validation so backup and migrations see the
# required Postgres variables.
if [ ! -f "${ENV_FILE}" ]; then
  echo "❌ Missing staging env file: ${ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a

# Validate required environment variables
STAGING_DOMAIN=${STAGING_DOMAIN:?"STAGING_DOMAIN not set"}
GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}
POSTGRES_USER=${POSTGRES_USER:?"POSTGRES_USER not set"}
POSTGRES_DB=${POSTGRES_DB:?"POSTGRES_DB not set"}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?"POSTGRES_PASSWORD not set"}
DATABASE_URL=${DATABASE_URL:?"DATABASE_URL not set"}

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-30}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

IMG_REF="${1:-latest}"         # тег/диджест образа

# Warn if using latest tag (should be specific commit SHA in production)
if [ "$IMG_REF" = "latest" ]; then
  echo "⚠️  WARNING: Using 'latest' tag. For production deployments, use specific commit SHA tags."
  echo "   CD workflow should pass the exact image tag (e.g., git SHA) to ensure consistency."
fi

echo "[1/4] Login GHCR"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/4] Pull image $IMG_REF"
export TAG="$IMG_REF"
"${COMPOSE[@]}" pull app

echo "[3/4] Start stack and DB backup"
# Start Postgres first to ensure backup and app startup use a healthy DB.
echo "Starting postgres first..."
"${COMPOSE[@]}" up -d postgres

echo "Waiting for postgres health..."
max_wait=60
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  POSTGRES_CONTAINER=$("${COMPOSE[@]}" ps -q postgres | tr -d '\n\r ')
  POSTGRES_HEALTH="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${POSTGRES_CONTAINER:-missing}" 2>/dev/null || true)"
  if [ -n "${POSTGRES_CONTAINER:-}" ] && [ "$POSTGRES_HEALTH" = "healthy" ]; then
    echo "Postgres is healthy"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for postgres... ($wait_count/$max_wait)"
  sleep 1
done

if [ $wait_count -eq $max_wait ]; then
  echo "❌ Postgres failed to become healthy within $max_wait seconds"
  exit 1
fi

if [ ! -x "${BACKUP_HELPER}" ]; then
  echo "❌ Missing Postgres backup helper: ${BACKUP_HELPER}"
  exit 1
fi

echo "Creating Postgres backup before migrations..."
PROJECT_DIR="${PROJECT_DIR}" BACKUP_DIR="${BACKUP_DIR}" COMPOSE_FILE="${COMPOSE_FILE}" POSTGRES_USER="${POSTGRES_USER}" POSTGRES_DB="${POSTGRES_DB}" \
  "${BACKUP_HELPER}"

echo "Starting app before exposing traffic..."
"${COMPOSE[@]}" up -d app

echo "[4/4] Run migrations"
echo "Waiting for app readiness..."
max_wait=30
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  APP_CONTAINER=$("${COMPOSE[@]}" ps -q app | tr -d '\n\r ')
  if [ -n "${APP_CONTAINER:-}" ] && docker exec "$APP_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready').read()" 2>/dev/null; then
    echo "App is ready"
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

echo "Starting caddy after successful migrations..."
"${COMPOSE[@]}" up -d caddy

echo "[post] Smoke check with retry"
# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${STAGING_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=0

# Quick non-blocking HTTP smoke check (diagnostic only; expected 308 -> HTTPS redirect)
echo "Smoke check HTTP..."
curl -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" --max-time "${HEALTH_CURL_MAX_TIME_S}" || true

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
