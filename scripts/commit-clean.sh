#!/bin/bash

# Clean commit script - automatically cleans cache before committing

echo "🧹 Cleaning cache files before commit..."

# Run cache cleanup
if [ ! -f ./scripts/clean-cache.sh ]; then
    echo "❌ Error: ./scripts/clean-cache.sh not found"
    exit 1
fi

if ! ./scripts/clean-cache.sh; then
    echo "❌ Error: Cache cleanup failed"
    exit 1
fi

# Check if commit message is provided
if [ -z "$1" ]; then
    echo "❌ Error: Commit message required"
    echo "Usage: $0 \"commit message\""
    exit 1
fi

# Check git status
echo "📋 Files to be committed:"
git status --porcelain

# If there are changes, commit them
if [ ! -z "$(git status --porcelain)" ]; then
    echo ""
    echo "💾 Committing changes..."
    git add -u  # Only stage tracked files
    git commit -m "$1"
    echo "✅ Commit completed successfully"
else
    echo "ℹ️  No changes to commit"
fi
