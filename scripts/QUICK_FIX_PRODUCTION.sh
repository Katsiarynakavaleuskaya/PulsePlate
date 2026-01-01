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

# Detect compose command (v1 priority)
DC_CMD=""
if command -v docker-compose >/dev/null 2>&1; then
    DC_CMD="docker-compose"
    echo "✅ Using: docker-compose (v1)"
elif docker compose version >/dev/null 2>&1; then
    DC_CMD="docker compose"
    echo "✅ Using: docker compose (v2 plugin)"
else
    echo "❌ Neither 'docker-compose' (v1) nor 'docker compose' (v2) is available"
    exit 1
fi

COMPOSE_FILE="docker-compose.production.yaml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Compose file not found: $COMPOSE_FILE"
    exit 1
fi

echo "📍 Compose file: $COMPOSE_FILE"
echo ""

# Check for duplicates
echo "=== Step 1: Check for duplicate env vars ==="
DUPLICATES=$(grep -nE '^(APP_ENV|ENVIRONMENT|POSTGRES_PASSWORD)=' .env 2>/dev/null | wc -l || echo "0")
if [ "$DUPLICATES" -gt 3 ]; then
    echo "⚠️  Found potential duplicates in .env"
    grep -nE '^(APP_ENV|ENVIRONMENT|POSTGRES_PASSWORD)=' .env || true
fi
echo ""

# Backup .env
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backed up .env"
fi

# Clean and set env vars
echo "=== Step 2: Clean and set environment variables ==="
sed -i '/^APP_ENV=/d;/^ENVIRONMENT=/d;/^POSTGRES_PASSWORD=/d' .env 2>/dev/null || true
printf "\nAPP_ENV=production\nENVIRONMENT=production\nPOSTGRES_PASSWORD=dummy\n" >> .env  # pragma: allowlist secret
echo "✅ Set: APP_ENV=production, ENVIRONMENT=production, POSTGRES_PASSWORD=dummy"
echo ""

# Validate compose
echo "=== Step 3: Validate compose file ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    if $DC_CMD -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        echo "✅ Compose file is valid"
    else
        echo "❌ Compose file validation failed"
        $DC_CMD -f "$COMPOSE_FILE" config 2>&1 | head -20 || true
        exit 1
    fi
else
    if $DC_CMD --env-file .env -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
        echo "✅ Compose file is valid"
    else
        echo "❌ Compose file validation failed"
        $DC_CMD --env-file .env -f "$COMPOSE_FILE" config 2>&1 | head -20 || true
        exit 1
    fi
fi
echo ""

# Pull images
echo "=== Step 4: Pull latest images ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    $DC_CMD -f "$COMPOSE_FILE" pull || echo "⚠️  Some images failed to pull (may already be up to date)"
else
    $DC_CMD --env-file .env -f "$COMPOSE_FILE" pull || echo "⚠️  Some images failed to pull (may already be up to date)"
fi
echo ""

# Restart services
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

# Check status
echo "=== Step 6: Service status ==="
if [ "$DC_CMD" = "docker-compose" ]; then
    $DC_CMD -f "$COMPOSE_FILE" ps
else
    $DC_CMD --env-file .env -f "$COMPOSE_FILE" ps
fi
echo ""

# Check env in container
echo "=== Step 7: Environment variables in app container ==="
APP_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'app|pulseplate.*app' | head -1)
if [ -n "$APP_CONTAINER" ]; then
    docker exec -it "$APP_CONTAINER" python -c "import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT')); print('ENV:', os.getenv('ENV'))" 2>/dev/null || echo "⚠️  Could not check env in container"
else
    echo "⚠️  App container not found"
fi
echo ""

# Check health
echo "=== Step 8: Health check ==="
PUBLIC_DOMAIN=$(grep PRODUCTION_DOMAIN .env 2>/dev/null | cut -d'=' -f2 | tr -d '\n\r' || echo "pulseplate.app")
echo "Checking: https://${PUBLIC_DOMAIN}/health"
curl -fsS "https://${PUBLIC_DOMAIN}/health" | jq . 2>/dev/null || curl -fsS "https://${PUBLIC_DOMAIN}/health" || echo "⚠️  Health check failed"
echo ""

echo "=========================================="
echo "Quick Fix Complete"
echo "=========================================="
echo ""
echo "Expected results:"
echo "  - Caddy image: caddy:2.10.2 (or latest)"
echo "  - APP_ENV: production"
echo "  - ENVIRONMENT: production"
echo "  - Health endpoint: environment='production'"
