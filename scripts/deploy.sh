#!/usr/bin/env bash
# Fail-closed staging deploy. Requires Docker Compose and two attested GHCR digests.
set -euo pipefail

STAGING_DEPLOY_CONTRACT_VERSION="2"
STAGING_DEPLOY_MARKER_CONTENT="pulseplate-staging-attested-digest-v1"
CANONICAL_IMAGE_PATTERN='^ghcr\.io/katsiarynakavaleuskaya/pulseplate@sha256:[0-9a-f]{64}$'

usage() {
  cat >&2 <<'EOF'
Usage:
  deploy.sh [--preflight-only] BACKEND_DIGEST_REF CADDY_DIGEST_REF

Both image references must use the canonical PulsePlate GHCR repository and a
lowercase sha256 digest. Floating tags are not accepted.
EOF
}

PREFLIGHT_ONLY=0
if [ "${1:-}" = "--preflight-only" ]; then
  PREFLIGHT_ONLY=1
  shift
fi

if [ "$#" -ne 2 ]; then
  usage
  exit 2
fi

BACKEND_IMAGE_REF="$1"
CADDY_IMAGE_REF="$2"

for image_ref in "$BACKEND_IMAGE_REF" "$CADDY_IMAGE_REF"; do
  if [[ ! "$image_ref" =~ $CANONICAL_IMAGE_PATTERN ]]; then
    echo "❌ Immutable canonical GHCR digest reference required: $image_ref" >&2
    exit 2
  fi
done

if [ "$BACKEND_IMAGE_REF" = "$CADDY_IMAGE_REF" ]; then
  echo "❌ Backend and Caddy image digests must be distinct" >&2
  exit 2
fi

PROJECT_DIR="${PROJECT_DIR:-/srv/pulseplate-staging}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_DIR}/docker-compose.staging.yaml}"
CADDYFILE="${CADDYFILE:-${PROJECT_DIR}/Caddyfile}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
BACKUP_HELPER="${BACKUP_HELPER:-${PROJECT_DIR}/scripts/ops/postgres_backup.sh}"
STAGING_DEPLOY_MARKER="${STAGING_DEPLOY_MARKER:-${PROJECT_DIR}/.attested-digest-deploy-v1}"

if [ -L "$STAGING_DEPLOY_MARKER" ] || [ ! -f "$STAGING_DEPLOY_MARKER" ]; then
  echo "❌ Missing regular non-symlink staging deploy marker: $STAGING_DEPLOY_MARKER" >&2
  exit 1
fi

STAT_BIN="${STAT_BIN:-}"
if [ -z "$STAT_BIN" ]; then
  STAT_BIN="$(command -v stat || :)"
fi
if [ -z "$STAT_BIN" ] || [ ! -x "$STAT_BIN" ]; then
  echo "❌ stat executable is required for staging marker validation" >&2
  exit 1
fi

marker_metadata="$($STAT_BIN -c '%u:%g:%a' "$STAGING_DEPLOY_MARKER")"
if [ "$marker_metadata" != "0:0:644" ]; then
  echo "❌ Staging deploy marker must be root-owned with mode 0644; got $marker_metadata" >&2
  exit 1
fi

marker_size="$(wc -c < "$STAGING_DEPLOY_MARKER" | tr -d '[:space:]')"
marker_content=""
IFS= read -r marker_content < "$STAGING_DEPLOY_MARKER" || [ -n "$marker_content" ]
if [ "$marker_content" != "$STAGING_DEPLOY_MARKER_CONTENT" ] || \
   [ "$marker_size" -ne "${#STAGING_DEPLOY_MARKER_CONTENT}" ]; then
  echo "❌ Staging deploy marker content mismatch" >&2
  exit 1
fi

for required_path in "$ENV_FILE" "$COMPOSE_FILE" "$CADDYFILE"; do
  if [ -L "$required_path" ] || [ ! -f "$required_path" ]; then
    echo "❌ Staging file must be a regular non-symlink file: $required_path" >&2
    exit 1
  fi
done
env_file_mode="$($STAT_BIN -c '%a' "$ENV_FILE")"
if [ "$env_file_mode" != "600" ]; then
  echo "❌ Staging env file must use mode 0600; got $env_file_mode" >&2
  exit 1
fi
if [ -L "$BACKUP_HELPER" ] || [ ! -f "$BACKUP_HELPER" ] || [ ! -x "$BACKUP_HELPER" ]; then
  echo "❌ Postgres backup helper must be a regular executable non-symlink file: $BACKUP_HELPER" >&2
  exit 1
fi
backup_helper_mode="$($STAT_BIN -c '%a' "$BACKUP_HELPER")"
if (( (8#$backup_helper_mode & 8#22) != 0 )); then
  echo "❌ Postgres backup helper must not be group- or world-writable; got mode $backup_helper_mode" >&2
  exit 1
fi

export STAGING_IMAGE_REF="$BACKEND_IMAGE_REF"
export STAGING_CADDY_IMAGE_REF="$CADDY_IMAGE_REF"
export STAGING_ENV_FILE="$ENV_FILE"

STAGING_DOMAIN=${STAGING_DOMAIN:?"STAGING_DOMAIN not set"}

DOCKER_BIN="${DOCKER_BIN:-}"
if [ -z "$DOCKER_BIN" ]; then
  DOCKER_BIN="$(command -v docker || :)"
fi
if [ -z "$DOCKER_BIN" ] || [ ! -x "$DOCKER_BIN" ]; then
  echo "❌ docker executable is required" >&2
  exit 1
fi

COMPOSE=("$DOCKER_BIN" compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

docker_architecture="$($DOCKER_BIN info --format '{{.Architecture}}')"
case "$docker_architecture" in
  amd64|x86_64) ;;
  *)
    echo "❌ Staging artifacts are linux/amd64 only; host reports $docker_architecture" >&2
    exit 1
    ;;
esac

"${COMPOSE[@]}" config --quiet

if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  echo "✅ Staging deploy preflight passed (contract v${STAGING_DEPLOY_CONTRACT_VERSION})"
  exit 0
fi

GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}

CURL_BIN="${CURL_BIN:-}"
if [ -z "$CURL_BIN" ]; then
  CURL_BIN="$(command -v curl || :)"
fi
if [ -z "$CURL_BIN" ] || [ ! -x "$CURL_BIN" ]; then
  echo "❌ curl executable is required" >&2
  exit 1
fi

umask 077
DOCKER_CONFIG="$(mktemp -d "${TMPDIR:-/tmp}/pulseplate-docker-config.XXXXXX")"
export DOCKER_CONFIG
cleanup() {
  rm -rf -- "$DOCKER_CONFIG"
}
trap cleanup EXIT

HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-30}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

echo "[1/5] Login to GHCR with temporary credentials"
printf '%s' "$GHCR_TOKEN" | "$DOCKER_BIN" login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/5] Pull exact backend and Caddy digests"
"${COMPOSE[@]}" pull app caddy
"$DOCKER_BIN" logout ghcr.io >/dev/null
rm -rf -- "$DOCKER_CONFIG"
mkdir -m 700 -- "$DOCKER_CONFIG"
unset GHCR_TOKEN GHCR_USER

echo "[3/5] Start Postgres and create a pre-migration backup"
"${COMPOSE[@]}" up -d postgres

max_wait=60
wait_count=0
while [ "$wait_count" -lt "$max_wait" ]; do
  postgres_container="$("${COMPOSE[@]}" ps -q postgres | tr -d '\n\r ')"
  postgres_health="unknown"
  if [ -n "$postgres_container" ]; then
    if inspected_health="$($DOCKER_BIN inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$postgres_container" 2>/dev/null)"; then
      postgres_health="$inspected_health"
    fi
  fi
  if [ -n "$postgres_container" ] && [ "$postgres_health" = "healthy" ]; then
    echo "Postgres is healthy"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for postgres... ($wait_count/$max_wait)"
  sleep 1
done

if [ "$wait_count" -eq "$max_wait" ]; then
  echo "❌ Postgres failed to become healthy within $max_wait seconds" >&2
  exit 1
fi

echo "Creating Postgres backup before migrations..."
DOCKER_BIN="$DOCKER_BIN" PROJECT_DIR="$PROJECT_DIR" BACKUP_DIR="$BACKUP_DIR" \
  COMPOSE_FILE="$COMPOSE_FILE" \
  "$BACKUP_HELPER"

echo "[4/5] Quiesce public traffic and run migrations before starting the new app"
"${COMPOSE[@]}" stop caddy app

echo "Running database migrations in a one-shot container"
if "${COMPOSE[@]}" run --rm --no-deps app alembic upgrade head; then
  echo "✅ Database migrations completed successfully"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed (exit code: $migration_exit_code)" >&2
  echo "Caddy and app remain stopped; restore the pre-migration backup before retrying if needed" >&2
  exit "$migration_exit_code"
fi

echo "Starting app after successful migrations"
"${COMPOSE[@]}" up -d --pull never app

max_wait=30
wait_count=0
app_container=""
while [ "$wait_count" -lt "$max_wait" ]; do
  app_container="$("${COMPOSE[@]}" ps -q app | tr -d '\n\r ')"
  if [ -n "$app_container" ] && \
     "$DOCKER_BIN" exec "$app_container" python -c \
       "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=5).read()" \
       2>/dev/null; then
    echo "App is ready"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app readiness... ($wait_count/$max_wait)"
  sleep 1
done

if [ "$wait_count" -eq "$max_wait" ]; then
  echo "❌ App failed to become ready within $max_wait seconds" >&2
  exit 1
fi

echo "[5/5] Start Caddy after successful migrations"
"${COMPOSE[@]}" up -d --pull never caddy

DOMAIN="$STAGING_DOMAIN"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=0

echo "Diagnostic HTTP smoke check..."
if "$CURL_BIN" -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" \
  --max-time "$HEALTH_CURL_MAX_TIME_S"; then
  :
else
  echo "⚠️  HTTP redirect diagnostic failed; continuing to the required HTTPS check" >&2
fi

while [ "$attempt" -lt "$HEALTH_MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$HEALTH_MAX_ATTEMPTS..."
  if curl_output="$("$CURL_BIN" -fsS --max-time "$HEALTH_CURL_MAX_TIME_S" \
    "$HEALTH_URL" --resolve "${DOMAIN}:443:127.0.0.1" 2>&1)"; then
    echo "✅ Health check successful"
    break
  else
    curl_exit_code=$?
    echo "❌ Health check failed (exit code: $curl_exit_code)" >&2
    echo "Error details: $curl_output" >&2
    if [ "$attempt" -eq "$HEALTH_MAX_ATTEMPTS" ]; then
      echo "❌ Health check failed after ${HEALTH_MAX_ATTEMPTS} attempts" >&2
      exit 1
    fi
    sleep "$HEALTH_SLEEP_S"
  fi
done

echo "✅ Staging deployed by attested digests"
echo "Backend: $BACKEND_IMAGE_REF"
echo "Caddy:   $CADDY_IMAGE_REF"
