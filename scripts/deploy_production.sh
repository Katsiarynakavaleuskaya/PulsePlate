#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REF:?IMAGE_REF is required (ghcr.io/<image>@sha256:...)}"
: "${TAG:?TAG is required (prod-vX.Y.Z)}"
: "${PRODUCTION_DOMAIN:?PRODUCTION_DOMAIN is required}"

export IMAGE_REF TAG PRODUCTION_DOMAIN

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

HEALTH_URL="https://${PRODUCTION_DOMAIN}/health"
attempt=1
max_attempts=12
sleep_s=2
until curl -fsS --max-time 10 "$HEALTH_URL" > /dev/null; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "❌ Healthcheck failed after ${max_attempts} attempts: $HEALTH_URL" >&2
    dc logs --tail=200 || true
    exit 1
  fi
  echo "Healthcheck not ready (attempt ${attempt}/${max_attempts}), retrying in ${sleep_s}s..."
  attempt=$((attempt + 1))
  sleep "$sleep_s"
done

docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | head -n 20
