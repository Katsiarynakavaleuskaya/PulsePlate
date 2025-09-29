#!/bin/bash
# Project Organization Script for PulsePlate iOS

set -e

echo "🗂️  Organizing PulsePlate iOS project structure..."

# Create directories
mkdir -p scripts docs assets tools config

# Move shell scripts
echo "📁 Moving shell scripts..."
mv *.sh scripts/ 2>/dev/null || echo "No .sh files to move"

# Move documentation
echo "📁 Moving documentation..."
mv *.md docs/ 2>/dev/null || echo "No .md files to move"

# Move Python scripts
echo "📁 Moving Python tools..."
mv *.py tools/ 2>/dev/null || echo "No .py files to move"

# Move media files
echo "📁 Moving media assets..."
mv *.mp4 *.png assets/ 2>/dev/null || echo "No media files to move"

# Move config files
echo "📁 Moving configuration files..."
mv .swiftlint.yml .swiftformat config/ 2>/dev/null || echo "No config files to move"

echo "✅ Project organization complete!"
echo ""
echo "New structure:"
echo "├── scripts/     # Shell scripts"
echo "├── docs/        # Documentation"
echo "├── assets/      # Media files"
echo "├── tools/       # Python tools"
echo "└── config/      # Configuration files"
