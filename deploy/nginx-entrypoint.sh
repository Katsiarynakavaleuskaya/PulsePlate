#!/bin/bash
# Nginx entrypoint with SSL certificate validation

set -euo pipefail

echo "🔍 Validating SSL certificates..."

# Check if SSL directory exists
if [ ! -d "/etc/nginx/ssl" ]; then
    echo "❌ SSL directory /etc/nginx/ssl not found"
    exit 1
fi

# Check for required SSL files
SSL_KEY="/etc/nginx/ssl/private.key"
SSL_CERT="/etc/nginx/ssl/certificate.crt"

if [ ! -f "$SSL_KEY" ]; then
    echo "❌ SSL private key not found at $SSL_KEY"
    echo "💡 Create with: openssl genrsa -out $SSL_KEY 2048"
    exit 1
fi

if [ ! -f "$SSL_CERT" ]; then
    echo "❌ SSL certificate not found at $SSL_CERT"
    echo "💡 Create with: openssl req -new -x509 -key $SSL_KEY -out $SSL_CERT -days 365"
    exit 1
fi

# Check permissions
KEY_PERMS=$(stat -c "%a" "$SSL_KEY" 2>/dev/null || stat -f "%OLp" "$SSL_KEY" 2>/dev/null)
CERT_PERMS=$(stat -c "%a" "$SSL_CERT" 2>/dev/null || stat -f "%OLp" "$SSL_CERT" 2>/dev/null)

if [ "$KEY_PERMS" != "600" ] && [ "$KEY_PERMS" != "400" ]; then
    echo "❌ SSL private key has incorrect permissions: $KEY_PERMS (expected 600 or 400)"
    echo "💡 Fix with: chmod 600 $SSL_KEY"
    exit 1
fi

if [ "$CERT_PERMS" != "644" ] && [ "$CERT_PERMS" != "640" ]; then
    echo "❌ SSL certificate has incorrect permissions: $CERT_PERMS (expected 644 or 640)"
    echo "💡 Fix with: chmod 644 $SSL_CERT"
    exit 1
fi

echo "✅ SSL certificates validated successfully"

# Test nginx configuration
echo "🔍 Testing nginx configuration..."
nginx -t

echo "🚀 Starting nginx..."
exec nginx -g "daemon off;"

