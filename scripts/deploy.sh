#!/usr/bin/env bash
# RU: Атомарный деплой на staging. Требует: docker, docker-compose, доступ к GHCR.
set -euo pipefail

IMG_REF="${1:-latest}"         # тег/диджест образа
COMPOSE="docker compose -f /srv/pulseplate-staging/docker-compose.staging.yaml"

echo "[1/4] Login GHCR"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/4] Pull image $IMG_REF"
export TAG="$IMG_REF"
$COMPOSE pull app

echo "[3/4] DB migrations"
docker run --rm --env-file /srv/pulseplate-staging/.env ghcr.io/katsiarynakavaleuskaya/pulseplate:$TAG alembic upgrade head

echo "[4/4] Restart stack"
$COMPOSE up -d app caddy

echo "[post] Smoke check"
curl -fsS "https://${STAGING_DOMAIN}/health" >/dev/null
echo "✅ Staging deployed: $IMG_REF"
