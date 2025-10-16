#!/bin/bash

# Clean commit script - automatically cleans cache before committing

echo "🧹 Cleaning cache files before commit..."

# Run cache cleanup
./scripts/clean-cache.sh

# Check git status
echo "📋 Files to be committed:"
git status --porcelain

# If there are changes, commit them
if [ ! -z "$(git status --porcelain)" ]; then
    echo ""
    echo "💾 Committing changes..."
    git add .
    git commit -m "$1"
    echo "✅ Commit completed successfully"
else
    echo "ℹ️  No changes to commit"
fi
