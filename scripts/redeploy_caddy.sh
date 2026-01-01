#!/usr/bin/env bash
# Redeploy Caddy Container Script
# RU: Скрипт для переразвертывания Caddy контейнера
# EN: Script to redeploy Caddy container
#
# Usage: Run this ON THE SERVER (after ssh or via console)
#   bash scripts/redeploy_caddy.sh
#
# Or copy to server and run:
#   bash redeploy_caddy.sh

set -euo pipefail

echo "=========================================="
echo "Redeploy Caddy Container"
echo "=========================================="
echo ""

# Auto-detect deploy directory
DEPLOY_DIR=""
COMPOSE_FILE=""

# Try common locations first
for dir in "/srv/pulseplate-production" "/opt/pulseplate" "/home/pulseplate" "$HOME/pulseplate-production"; do
    if [ -d "$dir" ] && [ -f "$dir/docker-compose.production.yaml" ]; then
        DEPLOY_DIR="$dir"
        COMPOSE_FILE="docker-compose.production.yaml"
        echo "✅ Found deploy directory: $DEPLOY_DIR"
        break
    fi
done

# If not found, search
if [ -z "$DEPLOY_DIR" ]; then
    echo "Searching for docker-compose.production.yaml..."
    FOUND=$(sudo find / -maxdepth 4 -name "docker-compose.production.yaml" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        DEPLOY_DIR=$(dirname "$FOUND")
        COMPOSE_FILE="docker-compose.production.yaml"
        echo "✅ Found: $DEPLOY_DIR"
    else
        echo "❌ docker-compose.production.yaml not found!"
        echo "   Please specify DEPLOY_DIR manually:"
        echo "   DEPLOY_DIR=/path/to/deploy bash redeploy_caddy.sh"
        exit 1
    fi
fi

cd "$DEPLOY_DIR" || exit 1
echo "Working directory: $(pwd)"
echo ""

# Detect compose command
DC_CMD=""
if docker compose version >/dev/null 2>&1; then
    DC_CMD="docker compose -f $COMPOSE_FILE"
elif command -v docker-compose >/dev/null 2>&1; then
    DC_CMD="docker-compose -f $COMPOSE_FILE"
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is available"
    exit 1
fi

echo "=== Step 1: Pull latest Caddy image ==="
$DC_CMD pull caddy || {
    echo "⚠️  Warning: Failed to pull Caddy image (may already be up to date)"
}

echo ""
echo "=== Step 2: Restart Caddy container ==="
$DC_CMD up -d caddy || {
    echo "❌ Failed to start Caddy container"
    exit 1
}

echo ""
echo "=== Step 3: Check Caddy container status ==="
$DC_CMD ps caddy

echo ""
echo "=== Step 4: Show recent Caddy logs ==="
$DC_CMD logs --tail=100 caddy

echo ""
echo "=========================================="
echo "Caddy redeploy complete"
echo "=========================================="
echo ""
echo "Verify Caddy is running:"
echo "  $DC_CMD ps caddy"
echo ""
echo "Check Caddy logs:"
echo "  $DC_CMD logs --tail=100 caddy"
echo ""
echo "Test health endpoint:"
echo "  curl -fsS https://\${PRODUCTION_DOMAIN}/health | jq ."
