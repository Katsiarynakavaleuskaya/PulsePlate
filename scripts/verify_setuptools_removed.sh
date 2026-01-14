#!/bin/bash
# Verify that setuptools is removed from runtime image
# Usage: ./scripts/verify_setuptools_removed.sh [image-tag]

set -euo pipefail

IMAGE_TAG="${1:-pulseplate:test}"

echo "🔍 Checking if setuptools is present in image: $IMAGE_TAG"

# Check 1: Try to import setuptools (should fail)
echo "Test 1: Import setuptools (should fail)..."
if docker run --rm "$IMAGE_TAG" python -c "import setuptools" 2>/dev/null; then
    echo "❌ FAIL: setuptools can be imported"
    exit 1
else
    echo "✅ PASS: setuptools cannot be imported"
fi

# Check 2: Check if setuptools directory exists in site-packages
echo "Test 2: Check site-packages for setuptools directory..."
if docker run --rm "$IMAGE_TAG" sh -c "ls -d /opt/venv/lib/python*/site-packages/setuptools* 2>/dev/null || true" | grep -q setuptools; then
    echo "❌ FAIL: setuptools directory found in site-packages"
    exit 1
else
    echo "✅ PASS: No setuptools directory in site-packages"
fi

# Check 3: Check for setuptools in pip list
echo "Test 3: Check pip list for setuptools..."
if docker run --rm "$IMAGE_TAG" pip list | grep -qi setuptools; then
    echo "❌ FAIL: setuptools found in pip list"
    exit 1
else
    echo "✅ PASS: setuptools not in pip list"
fi

echo ""
echo "✅ All checks passed: setuptools successfully removed from runtime image"
