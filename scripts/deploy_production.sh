#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REF:?IMAGE_REF is required (ghcr.io/<image>@sha256:...)}"
: "${TAG:?TAG is required (prod-vX.Y.Z)}"
: "${PRODUCTION_DOMAIN:?PRODUCTION_DOMAIN is required}"

export IMAGE_REF TAG PRODUCTION_DOMAIN

# Healthcheck configuration
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-12}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"

COMPOSE_FILE="${COMPOSE_FILE:-}"
DEPLOY_DIR="${DEPLOY_DIR:-}"

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

echo "Deploy dir: $DEPLOY_DIR"
if [ ${#compose_args[@]} -gt 0 ]; then
  echo "Compose file: ${compose_args[*]}"
else
  echo "Compose file: <default>"
fi
echo "TAG: $TAG"
echo "IMAGE_REF: $IMAGE_REF"

dc() {
  if [ ${#compose_args[@]} -gt 0 ]; then
    docker compose "${compose_args[@]}" "$@"
  else
    docker compose "$@"
  fi
}

dc pull
dc up -d --remove-orphans

# Healthcheck using --resolve to avoid DNS dependency (works even if DNS is temporarily unavailable)
# This checks locally via 127.0.0.1 but uses the domain for Host/SNI headers (TLS works correctly)
DOMAIN="${PRODUCTION_DOMAIN}"
HEALTH_URL="https://${DOMAIN}/health"
attempt=1

# Quick non-blocking HTTP smoke check (diagnostic only; expected 308 -> HTTPS redirect)
echo "Smoke check HTTP..."
curl -sS -o /dev/null -w "HTTP:%{http_code}\n" \
  "http://${DOMAIN}/health" --resolve "${DOMAIN}:80:127.0.0.1" --max-time "${HEALTH_CURL_MAX_TIME_S}" || true

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
