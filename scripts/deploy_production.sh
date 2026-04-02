#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REF:?IMAGE_REF is required (ghcr.io/<image>@sha256:...)}"
: "${TAG:?TAG is required (prod-vX.Y.Z)}"

DEPLOY_IMAGE_REF="$IMAGE_REF"
DEPLOY_TAG="$TAG"

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-12}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

COMPOSE_FILE="${COMPOSE_FILE:-}"
DEPLOY_DIR="${DEPLOY_DIR:-}"
ENV_FILE="${ENV_FILE:-}"
SHELL_BUNDLE_DIR="${SHELL_BUNDLE_DIR:-}"

resolve_deploy_dir() {
  if [ -n "$DEPLOY_DIR" ]; then
    if [ -d "$DEPLOY_DIR" ]; then
      echo "$DEPLOY_DIR"
      return 0
    fi
    echo "⚠️  DEPLOY_DIR is set but does not exist: $DEPLOY_DIR" >&2
    echo "    Falling back to auto-detect..." >&2
  fi

  if [ -d "/opt/pulseplate" ]; then
    echo "/opt/pulseplate"
    return 0
  fi

  if [ -d "/srv/pulseplate-production" ]; then
    echo "/srv/pulseplate-production"
    return 0
  fi

  return 1
}

DEPLOY_DIR="$(resolve_deploy_dir || true)"
if [ -z "$DEPLOY_DIR" ]; then
  echo "❌ Could not find deploy directory." >&2
  echo "Set DEPLOY_DIR or create /opt/pulseplate or /srv/pulseplate-production." >&2
  exit 1
fi

cd "$DEPLOY_DIR"

compose_args=()
if [ -n "$COMPOSE_FILE" ]; then
  compose_args=(-f "$COMPOSE_FILE")
elif [ -f "docker-compose.production.yaml" ]; then
  compose_args=(-f "docker-compose.production.yaml")
elif [ -f "docker-compose.production.yml" ]; then
  compose_args=(-f "docker-compose.production.yml")
elif [ -f "docker-compose.yml" ]; then
  compose_args=(-f "docker-compose.yml")
elif [ -f "docker-compose.yaml" ]; then
  compose_args=(-f "docker-compose.yaml")
elif [ -f "compose.yml" ]; then
  compose_args=(-f "compose.yml")
elif [ -f "compose.yaml" ]; then
  compose_args=(-f "compose.yaml")
fi

if [ -z "$ENV_FILE" ]; then
  ENV_FILE="$DEPLOY_DIR/.env"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing production env file: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

IMAGE_REF="$DEPLOY_IMAGE_REF"
TAG="$DEPLOY_TAG"
export IMAGE_REF TAG

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${PRODUCTION_DOMAIN:?PRODUCTION_DOMAIN is required}"

export PRODUCTION_DOMAIN

echo "Deploy dir: $DEPLOY_DIR"
if [ ${#compose_args[@]} -gt 0 ]; then
  echo "Compose file: ${compose_args[*]}"
else
  echo "Compose file: <default>"
fi
echo "TAG: $TAG"
echo "IMAGE_REF: $IMAGE_REF"
echo "ENV_FILE: $ENV_FILE"

dc() {
  local base=(docker compose --env-file "$ENV_FILE")
  if [ ${#compose_args[@]} -gt 0 ]; then
    base+=("${compose_args[@]}")
  fi
  "${base[@]}" "$@"
}

sync_shell_bundle() {
  if [ -z "$SHELL_BUNDLE_DIR" ]; then
    return 0
  fi

  if [ -z "$DEPLOY_DIR" ]; then
    echo "❌ DEPLOY_DIR is required when SHELL_BUNDLE_DIR is set" >&2
    exit 1
  fi

  local source_frontend="$SHELL_BUNDLE_DIR/frontend"
  local source_caddyfile="$SHELL_BUNDLE_DIR/deploy/Caddyfile.production"
  local source_diagnose="$SHELL_BUNDLE_DIR/scripts/diagnose_web.sh"
  local shell_root
  shell_root="$(cd "$DEPLOY_DIR/.." && pwd)"

  if [ ! -d "$source_frontend" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing frontend/: $source_frontend" >&2
    exit 1
  fi

  if [ ! -f "$source_caddyfile" ]; then
    echo "❌ SHELL_BUNDLE_DIR is missing deploy/Caddyfile.production: $source_caddyfile" >&2
    exit 1
  fi

  echo "Syncing production shell bundle from: $SHELL_BUNDLE_DIR"
  rm -rf "$shell_root/frontend"
  mkdir -p "$shell_root/frontend" "$shell_root/scripts"
  cp -R "$source_frontend/." "$shell_root/frontend/"
  cp "$source_caddyfile" "$DEPLOY_DIR/Caddyfile.production"
  rm -f "$shell_root/scripts/diagnose_web.sh"

  if [ -f "$source_diagnose" ]; then
    cp "$source_diagnose" "$shell_root/scripts/diagnose_web.sh"
    chmod +x "$shell_root/scripts/diagnose_web.sh"
  fi
}

wait_for_app_ready() {
  local max_wait="${1:-30}"
  local wait_count=0

  while [ "$wait_count" -lt "$max_wait" ]; do
    local app_container
    app_container="$(dc ps -q app | tr -d '\n\r ')"
    if [ -n "${app_container:-}" ] && docker exec "$app_container" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready').read()" 2>/dev/null; then
      echo "app is ready"
      return 0
    fi
    wait_count=$((wait_count + 1))
    echo "Waiting for app readiness... ($wait_count/$max_wait)"
    sleep 1
  done

  echo "❌ App failed to become ready within $max_wait seconds" >&2
  return 1
}

validate_managed_postgres_contract() {
  local compose_file_path=""

  if [ ${#compose_args[@]} -gt 0 ]; then
    compose_file_path="${compose_args[1]}"
  fi

  case "$DATABASE_URL" in
    postgresql+psycopg://*)
      ;;
    *)
      echo "❌ DATABASE_URL must use canonical Postgres DSN (postgresql+psycopg://...)" >&2
      exit 1
      ;;
  esac

  case "$DATABASE_URL" in
    *@postgres:*/* | *@postgres/*)
      echo "❌ Production deploy expects external managed PostgreSQL, not compose-local @postgres" >&2
      exit 1
      ;;
  esac

  if [ -n "$compose_file_path" ] && grep -qE '^[[:space:]]+postgres:' "$compose_file_path"; then
    echo "❌ Production compose still references local postgres; canonical lane is managed PostgreSQL only" >&2
    exit 1
  fi
}

echo "Validating managed PostgreSQL production contract..."
validate_managed_postgres_contract

echo "Pulling production app image..."
dc pull app

echo "Production DB backups are managed outside the deploy script (provider snapshots / PITR)."

echo "Running database migrations via one-shot release container..."
if dc run --rm --no-deps app alembic upgrade head; then
  echo "✅ Database migrations completed successfully"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed (exit code: $migration_exit_code)" >&2
  exit "$migration_exit_code"
fi

sync_shell_bundle

echo "Starting app before exposing traffic..."
dc up -d --remove-orphans app
wait_for_app_ready 30

echo "Starting caddy after successful migrations..."
dc build caddy
dc up -d --remove-orphans caddy

# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${PRODUCTION_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/ready"
attempt=1

# Quick non-blocking HTTP smoke check (diagnostic only; expected 308 -> HTTPS redirect)
echo "Smoke check HTTP..."
curl -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/ready" --resolve "${DOMAIN}:80:127.0.0.1" --max-time "${HEALTH_CURL_MAX_TIME_S}" || true

# Main healthcheck on HTTPS (does not depend on external DNS)
echo "Healthcheck HTTPS (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS})..."
until curl -fsS --max-time "${HEALTH_CURL_MAX_TIME_S}" "$HEALTH_URL" \
    --resolve "${DOMAIN}:443:127.0.0.1" > /dev/null; do
  if [ "$attempt" -ge "$HEALTH_MAX_ATTEMPTS" ]; then
    echo "❌ Healthcheck failed after ${HEALTH_MAX_ATTEMPTS} attempts: $HEALTH_URL" >&2
    echo "Container status:"
    dc ps || true
    echo "Container logs (last 200 lines):"
    dc logs --tail=200 || true
    exit 1
  fi
  echo "Healthcheck not ready (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS}), retrying in ${HEALTH_SLEEP_S}s..."
  attempt=$((attempt + 1))
  sleep "${HEALTH_SLEEP_S}"
done

echo "✅ Healthcheck OK"

docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | head -n 20
