#!/usr/bin/env bash
# Fix Production Environment Script
# RU: Скрипт для исправления environment переменных на production сервере
# EN: Script to fix environment variables on production server
#
# Usage: Run this ON THE SERVER
#   bash scripts/fix_production_env.sh

set -euo pipefail

echo "=========================================="
echo "Fix Production Environment"
echo "=========================================="
echo ""

# Auto-detect deploy directory
DEPLOY_DIR=""
if [ -d "/srv/pulseplate-production" ]; then
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

# Detect compose command (v1 has priority if both exist, as it's more common on servers)
DC_CMD=""
if command -v docker-compose >/dev/null 2>&1; then
    DC_CMD="docker-compose"
    echo "✅ Using: docker-compose (v1)"
elif docker compose version >/dev/null 2>&1; then
    DC_CMD="docker compose"
    echo "✅ Using: docker compose (v2 plugin)"
else
    echo "❌ Neither 'docker-compose' (v1) nor 'docker compose' (v2 plugin) is available"
    exit 1
fi

COMPOSE_FILE="docker-compose.production.yaml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Compose file not found: $COMPOSE_FILE"
    echo "   Current directory: $(pwd)"
    exit 1
fi

echo "📍 Compose file: $COMPOSE_FILE"
echo ""

# Check if postgres service exists in compose file
HAS_POSTGRES=false
if grep -qE "^\s+postgres:" "$COMPOSE_FILE" || grep -qE "^\s+db:" "$COMPOSE_FILE"; then
    HAS_POSTGRES=true
    echo "⚠️  Found postgres/db service in compose file"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found, creating..."
    touch .env
fi

echo "=== Step 1: Check current POSTGRES_PASSWORD ==="
if [ "$HAS_POSTGRES" = true ]; then
    # Try to get password from existing postgres container
    POSTGRES_CONTAINER=$(docker ps -q --filter "name=postgres" --filter "name=db" | head -1)
    if [ -n "$POSTGRES_CONTAINER" ]; then
        echo "✅ Found existing postgres container: $POSTGRES_CONTAINER"
        EXISTING_PASSWORD=$(docker inspect "$POSTGRES_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -E '^POSTGRES_PASSWORD=' | cut -d'=' -f2- || true)
        if [ -n "$EXISTING_PASSWORD" ]; then
            echo "✅ Found existing POSTGRES_PASSWORD in container"
            POSTGRES_PASSWORD_VALUE="$EXISTING_PASSWORD"
        else
            echo "⚠️  POSTGRES_PASSWORD not found in container, will use dummy"
            POSTGRES_PASSWORD_VALUE="dummy"  # pragma: allowlist secret
        fi
    else
        echo "⚠️  No existing postgres container found, will use dummy password"
        POSTGRES_PASSWORD_VALUE="dummy"  # pragma: allowlist secret
    fi
else
    echo "ℹ️  No postgres service in compose file, skipping POSTGRES_PASSWORD"
    POSTGRES_PASSWORD_VALUE=""
fi

echo ""
echo "=== Step 2: Update .env file ==="

# Backup .env
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backed up .env to .env.backup.*"
fi

# Function to clean duplicates and set env var in .env
# This removes ALL occurrences of the key and adds one clean entry
set_env_var() {
    local key="$1"
    local value="$2"
    local file=".env"

    # Remove all occurrences of this key (including duplicates)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "/^${key}=/d" "$file"
    else
        sed -i "/^${key}=/d" "$file"
    fi

    # Add single clean entry
    echo "${key}=${value}" >> "$file"
    echo "   Set: ${key}=${value}"
}

# Set required variables
if [ "$HAS_POSTGRES" = true ] && [ -n "$POSTGRES_PASSWORD_VALUE" ]; then
    set_env_var "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD_VALUE"
fi

set_env_var "APP_ENV" "production"
set_env_var "ENVIRONMENT" "production"

# Check for other required vars from compose
if grep -qE '\$\{PRODUCTION_DOMAIN' "$COMPOSE_FILE"; then
    if ! grep -qE "^PRODUCTION_DOMAIN=" .env 2>/dev/null; then
        echo "⚠️  PRODUCTION_DOMAIN not set in .env (required by compose)"
        echo "   Please add: PRODUCTION_DOMAIN=your-domain.com"
    fi
fi

if grep -qE '\$\{IMAGE_REF' "$COMPOSE_FILE"; then
    if ! grep -qE "^IMAGE_REF=" .env 2>/dev/null; then
        echo "⚠️  IMAGE_REF not set in .env (required by compose)"
        echo "   Please add: IMAGE_REF=ghcr.io/owner/repo@sha256:..."
    fi
fi

echo ""
echo "=== Step 3: Validate compose file ==="
# Note: docker-compose v1 reads .env automatically from current directory
# --env-file is only needed for v2 or custom location
if [ "$DC_CMD" = "docker-compose" ]; then
    # v1: reads .env automatically, no --env-file needed
    if $DC_CMD -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        echo "✅ Compose file is valid"
    else
        echo "❌ Compose file validation failed"
        echo "   Trying to see error:"
        $DC_CMD -f "$COMPOSE_FILE" config 2>&1 | head -20 || true
        exit 1
    fi
else
    # v2: needs --env-file
    if $DC_CMD --env-file .env -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        echo "✅ Compose file is valid"
    else
        echo "❌ Compose file validation failed"
        echo "   Trying to see error:"
        $DC_CMD --env-file .env -f "$COMPOSE_FILE" config 2>&1 | head -20 || true
        exit 1
    fi
fi

echo ""
echo "=== Step 4: Pull latest images ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    $DC_CMD -f "$COMPOSE_FILE" pull || {
        echo "⚠️  Warning: Some images failed to pull (may already be up to date)"
    }
else
    $DC_CMD --env-file .env -f "$COMPOSE_FILE" pull || {
        echo "⚠️  Warning: Some images failed to pull (may already be up to date)"
    }
fi

echo ""
echo "=== Step 5: Restart services ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    $DC_CMD -f "$COMPOSE_FILE" up -d --force-recreate || {
        echo "❌ Failed to restart services"
        exit 1
    }
else
    $DC_CMD --env-file .env -f "$COMPOSE_FILE" up -d --force-recreate || {
        echo "❌ Failed to restart services"
        exit 1
    }
fi

echo ""
echo "=== Step 6: Check service status ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    $DC_CMD -f "$COMPOSE_FILE" ps
else
    $DC_CMD --env-file .env -f "$COMPOSE_FILE" ps
fi

echo ""
echo "=========================================="
echo "Fix Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check health endpoint:"
PROD_DOMAIN="$(grep -E '^PRODUCTION_DOMAIN=' .env 2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '\r\n' || true)"
if [ -z "${PROD_DOMAIN}" ]; then
    PROD_DOMAIN="YOUR_DOMAIN"
fi
echo "   curl -fsS https://${PROD_DOMAIN}/health | jq ."
if [ "${PROD_DOMAIN}" = "YOUR_DOMAIN" ]; then
    echo "   (If it prints YOUR_DOMAIN — set PRODUCTION_DOMAIN in .env)"
fi
echo ""
echo "2. Verify environment is 'production':"
if [ "$DC_CMD" = "docker-compose" ]; then
    echo "   docker-compose -f $COMPOSE_FILE exec app python -c \"import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))\""
else
    echo "   docker compose --env-file .env -f $COMPOSE_FILE exec app python -c \"import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))\""
fi
