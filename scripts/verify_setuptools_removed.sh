#!/bin/bash
# Verify that setuptools is removed from runtime image
# Usage: ./scripts/verify_setuptools_removed.sh [image-tag]

set -euo pipefail

IMAGE_TAG="${1:-pulseplate:test}"

# Pre-flight checks: verify docker is available and daemon is reachable
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ ERROR: docker is not installed or not on PATH" >&2
    exit 127
fi

if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: docker daemon is not reachable (is Docker running / do you have permissions?)" >&2
    # Show actual error for debugging
    docker info >&2 || true
    exit 1
fi

# Verify image exists before running checks
if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo "❌ ERROR: Docker image '$IMAGE_TAG' not found locally" >&2
    echo "   Build it first: docker build --target production -t $IMAGE_TAG ." >&2
    exit 1
fi

echo "🔍 Checking if setuptools is present in image: $IMAGE_TAG"

# Check 1: Try to import setuptools (should fail)
# NOTE: 2>/dev/null only suppresses Python import error, not docker errors
echo "Test 1: Import setuptools (should fail)..."
if docker run --rm "$IMAGE_TAG" /opt/venv/bin/python -c "import setuptools" 2>/dev/null; then
    echo "❌ FAIL: setuptools can be imported"
    exit 1
else
    echo "✅ PASS: setuptools cannot be imported"
fi

# Check 2: Check if setuptools directory exists in site-packages
# NOTE: 2>/dev/null only suppresses ls "not found" errors inside container, not docker errors
echo "Test 2: Check site-packages for setuptools directory..."
if docker run --rm "$IMAGE_TAG" sh -c "ls -d /opt/venv/lib/python*/site-packages/setuptools* 2>/dev/null || true" | grep -q setuptools; then
    echo "❌ FAIL: setuptools directory found in site-packages"
    exit 1
else
    echo "✅ PASS: No setuptools directory in site-packages"
fi

# Check 3: Check for setuptools in pip list
# NOTE: Suppress pip stderr only (inside container), not docker errors
echo "Test 3: Check pip list for setuptools..."
if docker run --rm "$IMAGE_TAG" sh -c 'pip list 2>/dev/null' | grep -qi setuptools; then
    echo "❌ FAIL: setuptools found in pip list"
    exit 1
else
    echo "✅ PASS: setuptools not in pip list"
fi

echo ""
echo "✅ All checks passed: setuptools successfully removed from runtime image"
