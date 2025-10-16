#!/bin/bash
set -euo pipefail

# Enhanced Python cache cleanup script
# Cleans all Python cache files and provides detailed reporting

echo "🧹 Enhanced Python Cache Cleanup"
echo "================================="

# Count files before cleanup
echo "📊 Analyzing cache files before cleanup..."

PYCACHE_COUNT=$(find . -path ./.git -prune -o -type d -name "__pycache__" -print | wc -l)
PYC_COUNT=$(find . -path ./.git -prune -o -type f -name "*.pyc" -print | wc -l)
PYO_COUNT=$(find . -path ./.git -prune -o -type f -name "*.pyo" -print | wc -l)
PYD_COUNT=$(find . -path ./.git -prune -o -type f -name "*.pyd" -print | wc -l)

echo "Found:"
echo "  📁 __pycache__ directories: $PYCACHE_COUNT"
echo "  🐍 .pyc files: $PYC_COUNT"
echo "  🐍 .pyo files: $PYO_COUNT"
echo "  🐍 .pyd files: $PYD_COUNT"

if [ "$PYCACHE_COUNT" -eq 0 ] && [ "$PYC_COUNT" -eq 0 ] && [ "$PYO_COUNT" -eq 0 ] && [ "$PYD_COUNT" -eq 0 ]; then
    echo "✅ No cache files found - repository is clean!"
    exit 0
fi

echo ""
echo "🗑️  Starting cleanup..."

# Remove __pycache__ directories (skip .git)
REMOVED_DIRS=0
while IFS= read -r -d '' dir; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "  🗂️  Removed: $dir"
        ((REMOVED_DIRS++))
    fi
done < <(find . -path ./.git -prune -o -depth -type d -name "__pycache__" -print0 2>/dev/null)

# Remove .pyc files (skip .git)
REMOVED_PYC=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYC++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyc" -print0 2>/dev/null)

# Remove .pyo files (skip .git)
REMOVED_PYO=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYO++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyo" -print0 2>/dev/null)

# Remove .pyd files (Windows) (skip .git)
REMOVED_PYD=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYD++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyd" -print0 2>/dev/null)

echo ""
echo "📊 Cleanup Summary:"
echo "  📁 __pycache__ directories removed: $REMOVED_DIRS"
echo "  🐍 .pyc files removed: $REMOVED_PYC"
echo "  🐍 .pyo files removed: $REMOVED_PYO"
echo "  🐍 .pyd files removed: $REMOVED_PYD"

TOTAL_REMOVED=$((REMOVED_DIRS + REMOVED_PYC + REMOVED_PYO + REMOVED_PYD))
echo "  📈 Total items removed: $TOTAL_REMOVED"

echo ""
echo "✅ Cache cleanup completed successfully!"

# Show git status to verify
echo ""
echo "📋 Current git status:"
git status --porcelain | head -10 || echo "  (No git repository or no changes)"
