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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Redeploy Caddy Container"
echo "=========================================="
echo ""

# Auto-detect deploy directory (allow override via environment)
DEPLOY_DIR="${DEPLOY_DIR:-}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
DIAG_MAX_ATTEMPTS="${DIAG_MAX_ATTEMPTS:-6}"
DIAG_RETRY_DELAY_SECONDS="${DIAG_RETRY_DELAY_SECONDS:-5}"

# If DEPLOY_DIR is already set, use it
if [ -n "$DEPLOY_DIR" ] && [ -d "$DEPLOY_DIR" ] && [ -f "$DEPLOY_DIR/docker-compose.production.yaml" ]; then
    COMPOSE_FILE="docker-compose.production.yaml"
    echo "✅ Using provided DEPLOY_DIR: $DEPLOY_DIR"
else
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
fi

cd "$DEPLOY_DIR" || exit 1
echo "Working directory: $(pwd)"
echo ""

# Repo root is one level above the canonical nested deploy directory.
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
DIAG_SCRIPT=""

for candidate in \
    "$SCRIPT_DIR/diagnose_web.sh" \
    "$DEPLOY_DIR/scripts/diagnose_web.sh" \
    "$REPO_ROOT/scripts/diagnose_web.sh"
do
    if [ -x "$candidate" ]; then
        DIAG_SCRIPT="$candidate"
        break
    fi
done

if [ -z "${PRODUCTION_DOMAIN:-}" ] && [ -f ".env" ]; then
    PRODUCTION_DOMAIN="$(awk -F= '/^PRODUCTION_DOMAIN=/{print $2; exit}' .env | tr -d '"' | tr -d "'" )"
    export PRODUCTION_DOMAIN
fi

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

echo "=== Step 1: Pull Caddy image (no-op when service uses build:) ==="
$DC_CMD pull caddy || {
    echo "⚠️  Warning: pull failed or skipped (expected when caddy uses compose build: context)"
}

echo ""
echo "=== Step 1b: Pull app image (IMAGE_REF from registry) ==="
$DC_CMD pull app || {
    echo "⚠️  Warning: pull app failed — verify registry auth / IMAGE_REF in .env"
}

echo ""
echo "=== Step 2: Build Caddy image (frontend dist + Caddyfile) ==="
$DC_CMD build caddy || {
    echo "❌ Failed to build Caddy image"
    exit 1
}

echo ""
echo "=== Step 3: Restart Caddy container ==="
$DC_CMD up -d caddy || {
    echo "❌ Failed to start Caddy container"
    exit 1
}

echo ""
echo "=== Step 4: Check Caddy container status ==="
$DC_CMD ps caddy

echo ""
echo "=== Step 5: Show recent Caddy logs ==="
$DC_CMD logs --tail=100 caddy

echo ""
if [ -n "$DIAG_SCRIPT" ] && [ -n "${PRODUCTION_DOMAIN:-}" ]; then
    echo "=== Step 6: Diagnose edge routing ==="
    attempt=1
    while [ "$attempt" -le "$DIAG_MAX_ATTEMPTS" ]; do
        if (
            cd "$(dirname "$DIAG_SCRIPT")"
            BASE_URL="https://${PRODUCTION_DOMAIN}" bash "$DIAG_SCRIPT" --skip-caddy-validate
        ); then
            break
        fi

        if [ "$attempt" -eq "$DIAG_MAX_ATTEMPTS" ]; then
            echo "❌ diagnose_web.sh reported a routing mismatch"
            exit 1
        fi

        echo "⚠️  diagnose_web.sh attempt ${attempt}/${DIAG_MAX_ATTEMPTS} failed; retrying in ${DIAG_RETRY_DELAY_SECONDS}s"
        sleep "$DIAG_RETRY_DELAY_SECONDS"
        attempt=$((attempt + 1))
    done
    echo ""
fi

if [ -n "$DIAG_SCRIPT" ] && [ -z "${PRODUCTION_DOMAIN:-}" ]; then
    echo "⚠️  Warning: PRODUCTION_DOMAIN is unavailable; skipping diagnose_web.sh"
    echo ""
fi

if [ -z "$DIAG_SCRIPT" ]; then
    echo "⚠️  Warning: diagnose_web.sh is unavailable in the detected server/repo layout; skipping automatic diagnosis"
    echo ""
fi

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
echo ""
echo "Run the full web-shell diagnosis:"
echo "  BASE_URL=https://\${PRODUCTION_DOMAIN} bash scripts/diagnose_web.sh"
