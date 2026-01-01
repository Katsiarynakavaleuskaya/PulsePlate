#!/usr/bin/env bash
# Production Server Diagnostic Script
# RU: Скрипт диагностики production сервера для выявления проблем с Cloudflare 521
# EN: Production server diagnostic script to identify Cloudflare 521 issues
#
# Usage: bash diagnose_production.sh
# Run this on the Droplet via SSH

set -euo pipefail

echo "=========================================="
echo "Production Server Diagnostic (Cloudflare 521)"
echo "=========================================="
echo ""

# Detect deploy directory
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

# Use docker-compose.production.yaml (standard name)
COMPOSE_FILE="docker-compose.production.yaml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Compose file not found: $COMPOSE_FILE"
    echo "   Current directory: $(pwd)"
    echo "   Files in directory:"
    ls -la | grep -E "docker-compose|compose" || echo "   (no compose files found)"
    exit 1
fi

echo "📍 Compose file: $COMPOSE_FILE"
echo ""

dc() {
    if docker compose version >/dev/null 2>&1; then
        docker compose -f "$COMPOSE_FILE" "$@"
        return 0
    fi
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose -f "$COMPOSE_FILE" "$@"
        return 0
    fi
    echo "❌ Neither 'docker compose' (v2 plugin) nor 'docker-compose' (v1) is available."
    return 1
}

echo "=========================================="
echo "1. Who is listening on ports 80/443"
echo "=========================================="
sudo ss -lntp | grep -E ':80|:443' || echo "⚠️  No processes listening on ports 80 or 443"
echo ""

echo "=========================================="
echo "2. Docker Containers and Ports"
echo "=========================================="
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' || true
echo ""

echo "=========================================="
echo "3. Compose Services Status"
echo "=========================================="
echo "⚠️  Important: Using compose file in $DEPLOY_DIR"
dc ps || true
echo ""

echo "=========================================="
echo "4. Caddy Container Logs (last 200 lines)"
echo "=========================================="
echo "⚠️  Usually the cause is visible here immediately"
dc logs --tail=200 caddy 2>&1 || echo "⚠️  Could not get Caddy logs (container may not exist)"
echo ""

echo "=========================================="
echo "5. App Container Logs (last 200 lines)"
echo "=========================================="
dc logs --tail=200 app 2>&1 || echo "⚠️  Could not get app logs (container may not exist)"
echo ""

echo "=========================================="
echo "6. Firewall Status (UFW)"
echo "=========================================="
if command -v ufw >/dev/null 2>&1; then
    sudo ufw status || echo "⚠️  UFW command failed"
else
    echo "⚠️  UFW not installed"
fi
echo ""

echo "=========================================="
echo "7. Caddyfile Check"
echo "=========================================="
# Check relative path (preferred, per compose config)
CADDYFILE_RELATIVE="$DEPLOY_DIR/Caddyfile.production"
# Check absolute path (legacy)
CADDYFILE_ABSOLUTE="/srv/pulseplate-production/Caddyfile.production"

if [ -f "$CADDYFILE_RELATIVE" ]; then
    echo "✅ Caddyfile exists (relative): $CADDYFILE_RELATIVE"
    echo "   (This file is mapped into container per compose config: ./Caddyfile.production)"
elif [ -f "$CADDYFILE_ABSOLUTE" ]; then
    echo "⚠️  Caddyfile exists (absolute): $CADDYFILE_ABSOLUTE"
    echo "   Note: Compose expects relative path ./Caddyfile.production in $DEPLOY_DIR"
    echo "   Consider: cp $CADDYFILE_ABSOLUTE $CADDYFILE_RELATIVE"
else
    echo "❌ Caddyfile NOT found"
    echo "   Expected (relative): $CADDYFILE_RELATIVE"
    echo "   Expected (absolute): $CADDYFILE_ABSOLUTE"
    echo "   This is likely the problem!"
fi
echo ""

echo "=========================================="
echo "8. PRODUCTION_DOMAIN Check"
echo "=========================================="
echo "⚠️  Important: PRODUCTION_DOMAIN must be set when compose starts"
echo "   (In GitHub deploy it's exported, but often forgotten in manual runs)"
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    if grep -q "PRODUCTION_DOMAIN" .env 2>/dev/null; then
        echo "✅ PRODUCTION_DOMAIN found in .env:"
        grep "PRODUCTION_DOMAIN" .env || true
    else
        echo "❌ PRODUCTION_DOMAIN NOT found in .env"
        echo "   This is likely the problem!"
    fi
else
    echo "❌ .env file NOT found in $DEPLOY_DIR"
fi

# Check if PRODUCTION_DOMAIN is exported in current shell
if [ -n "${PRODUCTION_DOMAIN:-}" ]; then
    echo "✅ PRODUCTION_DOMAIN is exported in current shell: $PRODUCTION_DOMAIN"
else
    echo "⚠️  PRODUCTION_DOMAIN is NOT exported in current shell"
    echo "   (This is OK if it's in .env and compose reads it)"
fi
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="
echo ""
echo "🔍 Quick Analysis Guide:"
echo ""
echo "If Cloudflare shows 521, check:"
echo ""
echo "1. ✅ Ports 80/443 listening?"
echo "   → Section 1 should show caddy process on :80 and :443"
echo "   → If empty: Caddy container not running or not bound to ports"
echo ""
echo "2. ✅ Caddy container running?"
echo "   → Section 2 should show caddy container with status 'Up'"
echo "   → Section 3 should show caddy service as 'running'"
echo ""
echo "3. ✅ Caddyfile exists?"
echo "   → Section 7: File must exist at ./Caddyfile.production (in deploy directory)"
echo "   → If missing: Copy from repo deploy/Caddyfile.production"
echo ""
echo "4. ✅ PRODUCTION_DOMAIN set?"
echo "   → Section 8: Must be in .env or exported"
echo "   → If missing: Add PRODUCTION_DOMAIN=your-domain.com to .env"
echo ""
echo "5. ✅ Caddy logs show errors?"
echo "   → Section 4: Look for 'no such file', 'environment variable not set', etc."
echo "   → Common errors visible immediately in logs"
echo ""
echo "6. ✅ Firewall blocking?"
echo "   → Section 6: Ports 80/tcp and 443/tcp must be ALLOW"
echo "   → If blocked: sudo ufw allow 80/tcp && sudo ufw allow 443/tcp"
echo ""
echo "💡 Most common issues:"
echo "   - Caddyfile.production missing → Copy from repo"
echo "   - PRODUCTION_DOMAIN not in .env → Add to .env"
echo "   - Caddy container not started → docker compose up -d"
echo "   - Firewall blocking → ufw allow 80/tcp 443/tcp"
