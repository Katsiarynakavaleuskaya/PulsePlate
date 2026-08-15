#!/usr/bin/env bash
# Quick Fix Production - Clean .env and Restart Services
# RU: Быстрое исправление production: очистка .env и перезапуск сервисов
# EN: Quick production fix: clean .env and restart services
#
# Usage: Run this ON THE SERVER
#   bash scripts/QUICK_FIX_PRODUCTION.sh

set -euo pipefail

echo "=========================================="
echo "Quick Fix Production"
echo "=========================================="
echo ""

# Auto-detect deploy directory unless an explicit operator/test path is provided.
DEPLOY_DIR="${DEPLOY_DIR:-}"
if [ -n "$DEPLOY_DIR" ] && [ ! -d "$DEPLOY_DIR" ]; then
    echo "❌ Explicit deploy directory not found: $DEPLOY_DIR"
    exit 1
elif [ -n "$DEPLOY_DIR" ]; then
    :
elif [ -d "/srv/pulseplate-production" ]; then
    DEPLOY_DIR="/srv/pulseplate-production"
elif [ -d "/opt/pulseplate" ]; then
    DEPLOY_DIR="/opt/pulseplate"
else
    echo "❌ Deploy directory not found. Expected /srv/pulseplate-production or /opt/pulseplate"
    exit 1
fi

echo "📍 Deploy directory: $DEPLOY_DIR"
cd "$DEPLOY_DIR" || exit 1
echo ""

if docker compose version >/dev/null 2>&1; then
    echo "✅ Using: docker compose"
else
    echo "❌ Docker Compose v2 plugin is required: docker compose"
    exit 1
fi

COMPOSE_FILE="docker-compose.production.yaml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Compose file not found: $COMPOSE_FILE"
    exit 1
fi

echo "📍 Compose file: $COMPOSE_FILE"
echo ""

if [ ! -f ".env" ] || [ ! -r ".env" ]; then
    echo "❌ Production environment file is missing or unreadable: .env"
    exit 1
fi

dc() {
    docker compose --env-file .env -f "$COMPOSE_FILE" "$@"
}

# Check for duplicates
echo "=== Step 1: Check for duplicate env vars ==="
DUPLICATE_KEY_LINES="$(awk '
    {
        line = $0
        sub(/\r$/, "", line)
        sub(/^[[:space:]]+/, "", line)
        sub(/^export[[:space:]]+/, "", line)
        if (line ~ /^(APP_ENV|ENVIRONMENT|POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD|DATABASE_URL)[[:space:]]*=/) {
            key = line
            sub(/[[:space:]]*=.*/, "", key)
            count[key]++
            locations[key] = locations[key] sprintf("%d:%s=<redacted>\n", NR, key)
        }
    }
    END {
        for (key in count) {
            if (count[key] > 1) {
                printf "%s", locations[key]
            }
        }
    }
' .env)"
if [ -n "$DUPLICATE_KEY_LINES" ]; then
    echo "❌ Duplicate required environment keys found in .env"
    printf '%s\n' "$DUPLICATE_KEY_LINES"
    exit 1
fi
echo ""

# Backup .env
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backed up .env"
fi

# Clean and set env vars
echo "=== Step 2: Clean and set environment variables ==="
CLEAN_ENV_FILE="$(mktemp "${DEPLOY_DIR}/.env.clean.XXXXXX")"
cleanup_env_temp() {
    if [ -n "${CLEAN_ENV_FILE:-}" ] && [ -f "$CLEAN_ENV_FILE" ]; then
        rm -f "$CLEAN_ENV_FILE"
    fi
}
trap cleanup_env_temp EXIT
if ! cp -p .env "$CLEAN_ENV_FILE"; then
    echo "❌ Failed to preserve production environment metadata"
    exit 1
fi
if ! awk '
    {
        normalized = $0
        sub(/\r$/, "", normalized)
        sub(/^[[:space:]]+/, "", normalized)
        sub(/^export[[:space:]]+/, "", normalized)
        if (normalized ~ /^(APP_ENV|ENVIRONMENT|SUBSCRIPTION_DB_ENABLED|ALLOW_DEV_API_KEY|API_KEY_REQUIRED)[[:space:]]*=/) {
            next
        }
        print
    }
' .env > "$CLEAN_ENV_FILE"; then
    echo "❌ Failed to clean production environment flags"
    exit 1
fi
if ! {
    echo ""
    echo "APP_ENV=production"
    echo "ENVIRONMENT=production"
    echo "SUBSCRIPTION_DB_ENABLED=true"
    echo "ALLOW_DEV_API_KEY=false"
    echo "API_KEY_REQUIRED=true"
} >> "$CLEAN_ENV_FILE"; then
    echo "❌ Failed to write production environment flags"
    exit 1
fi
if ! mv "$CLEAN_ENV_FILE" .env; then
    echo "❌ Failed to replace the production environment file"
    exit 1
fi
CLEAN_ENV_FILE=""
trap - EXIT
echo "✅ Set: APP_ENV=production, ENVIRONMENT=production, SUBSCRIPTION_DB_ENABLED=true, ALLOW_DEV_API_KEY=false, API_KEY_REQUIRED=true"
echo ""

echo "=== Step 2.1: Validate required Postgres env ==="
for key in DATABASE_URL POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    if ! grep -qE "^${key}=" .env 2>/dev/null; then
        echo "❌ Missing required env var: ${key}"
        exit 1
    fi
done

DATABASE_URL_VALUE="$(grep '^DATABASE_URL=' .env | tail -1 | cut -d'=' -f2- | tr -d '\r\n')"
case "$DATABASE_URL_VALUE" in
    postgresql+psycopg://*) echo "✅ DATABASE_URL uses Postgres DSN" ;;
    *)
        echo "❌ DATABASE_URL must use canonical Postgres DSN (postgresql+psycopg://...)"
        exit 1
        ;;
esac

# Validate compose
echo "=== Step 3: Validate compose file ==="
if dc config >/dev/null 2>&1; then
    echo "✅ Compose file is valid"
else
    echo "❌ Compose file validation failed"
    dc config 2>&1 | head -20 || true
    exit 1
fi
echo ""

# Pull the registry-backed application image and rebuild the local Caddy shell.
echo "=== Step 4: Refresh application and Caddy images ==="
if ! dc pull app; then
    echo "❌ Failed to pull the application image"
    exit 1
fi
if ! dc build caddy; then
    echo "❌ Failed to build the hardened Caddy image"
    exit 1
fi
echo ""

# Restart services
echo "=== Step 5: Restart services ==="
dc up -d --force-recreate || {
    echo "❌ Failed to restart services"
    exit 1
}
echo ""

echo "=== Step 5.1: Verify hardened Caddy runtime ==="
CADDY_VERSION="$(dc exec -T caddy caddy version)"
CADDY_VERSION_TOKEN="${CADDY_VERSION%%[[:space:]]*}"
if [ "$CADDY_VERSION_TOKEN" != "v2.11.4" ]; then
    echo "❌ Expected Caddy v2.11.4, got: $CADDY_VERSION"
    exit 1
fi
echo "✅ Caddy runtime version: $CADDY_VERSION"

CADDY_BUILD_INFO="$(dc exec -T caddy caddy build-info)"
CADDY_GO_VERSION=""
while IFS=$'\t' read -r build_key build_value _; do
    if [ "$build_key" = "go" ]; then
        CADDY_GO_VERSION="$build_value"
        break
    fi
done <<< "$CADDY_BUILD_INFO"
if [ "$CADDY_GO_VERSION" != "go1.26.6" ]; then
    echo "❌ Expected Caddy built with Go 1.26.6, got: ${CADDY_GO_VERSION:-missing}"
    exit 1
fi
echo "✅ Caddy runtime Go toolchain: go1.26.6"
echo ""

# Check status
echo "=== Step 6: Service status ==="
dc ps
echo ""

# Check env in container
echo "=== Step 7: Environment variables in app container ==="
APP_CONTAINER="$(docker ps --format '{{.Names}}' | awk '/app|pulseplate.*app/ { print; exit }')"
if [ -n "$APP_CONTAINER" ]; then
    docker exec "$APP_CONTAINER" python -c "import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT')); print('ENV:', os.getenv('ENV'))" 2>/dev/null || echo "⚠️  Could not check env in container"
else
    echo "⚠️  App container not found"
fi
echo ""

# Check health
echo "=== Step 8: Health check ==="
PUBLIC_DOMAIN="$(grep '^PRODUCTION_DOMAIN=' .env 2>/dev/null | tail -1 | cut -d'=' -f2- | tr -d '\n\r')"
if [[ ! "$PUBLIC_DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "❌ PRODUCTION_DOMAIN must be a non-empty hostname"
    exit 1
fi

HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-6}"
HEALTH_SLEEP_S="${HEALTH_SLEEP_S:-2}"
HEALTH_CURL_MAX_TIME_S="${HEALTH_CURL_MAX_TIME_S:-10}"
if [[ ! "$HEALTH_MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]] || \
   [[ ! "$HEALTH_SLEEP_S" =~ ^[0-9]+$ ]] || \
   [[ ! "$HEALTH_CURL_MAX_TIME_S" =~ ^[1-9][0-9]*$ ]]; then
    echo "❌ Healthcheck retry settings must be non-negative integers with positive attempts and timeout"
    exit 1
fi

echo "Checking: https://${PUBLIC_DOMAIN}/ready"
attempt=1
while [ "$attempt" -le "$HEALTH_MAX_ATTEMPTS" ]; do
    if health_response="$(curl -fsS --max-time "$HEALTH_CURL_MAX_TIME_S" "https://${PUBLIC_DOMAIN}/ready")"; then
        if ! command -v jq >/dev/null 2>&1 || printf '%s\n' "$health_response" | jq .; then
            echo "✅ Production readiness check passed"
            break
        fi
    fi
    if [ "$attempt" -ge "$HEALTH_MAX_ATTEMPTS" ]; then
        echo "❌ Health check failed after ${HEALTH_MAX_ATTEMPTS} attempts"
        exit 1
    fi
    echo "Health check not ready (attempt ${attempt}/${HEALTH_MAX_ATTEMPTS}); retrying in ${HEALTH_SLEEP_S}s"
    attempt=$((attempt + 1))
    sleep "$HEALTH_SLEEP_S"
done
echo ""

echo "=========================================="
echo "Quick Fix Complete"
echo "=========================================="
echo ""
echo "Expected results:"
echo "  - Caddy image: PulsePlate Caddy 2.11.4 rebuilt with Go 1.26.6"
echo "  - APP_ENV: production"
echo "  - ENVIRONMENT: production"
echo "  - Readiness endpoint: environment='production'"
