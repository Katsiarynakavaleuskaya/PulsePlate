#!/bin/bash

# Clean Python cache files
echo "🧹 Cleaning Python cache files..."

# Remove __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove .pyo files
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove .pyd files (Windows)
find . -type f -name "*.pyd" -delete 2>/dev/null || true

echo "✅ Cache cleanup completed"

# Show git status to verify
echo "📋 Current git status:"
git status --porcelain | head -10
