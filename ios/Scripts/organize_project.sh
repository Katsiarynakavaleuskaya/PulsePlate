#!/bin/bash
# Project Organization Script for PulsePlate iOS

set -e

echo "🗂️  Organizing PulsePlate iOS project structure..."

# Create directories
mkdir -p scripts docs assets tools config

# Move shell scripts (only project-specific ones)
echo "📁 Moving shell scripts..."
for file in *.sh; do
    if [ -f "$file" ] && [[ "$file" =~ ^(setup_|install_|generate_|organize_).*\.sh$ ]]; then
        echo "   Moving $file to scripts/"
        mv "$file" scripts/
    fi
done

# Move documentation (only project-specific ones)
echo "📁 Moving documentation..."
for file in *.md; do
    if [ -f "$file" ] && [[ "$file" =~ ^(README|SETUP|INSTALL|CONTRIBUTING|CHANGELOG).*\.md$ ]]; then
        echo "   Moving $file to docs/"
        mv "$file" docs/
    fi
done

# Move Python scripts (only project-specific ones)
echo "📁 Moving Python tools..."
for file in *.py; do
    if [ -f "$file" ] && [[ "$file" =~ ^(generate_|setup_|install_).*\.py$ ]]; then
        echo "   Moving $file to tools/"
        mv "$file" tools/
    fi
done

# Move media files (only project-specific ones)
echo "📁 Moving media assets..."
for file in *.mp4 *.png; do
    if [ -f "$file" ] && [[ "$file" =~ ^(fitchef_|pulseplate_|app_icon).*\.(mp4|png)$ ]]; then
        echo "   Moving $file to assets/"
        mv "$file" assets/
    fi
done

# Move config files (only project-specific ones)
echo "📁 Moving configuration files..."
for file in .swiftlint.yml .swiftformat; do
    if [ -f "$file" ]; then
        echo "   Moving $file to config/"
        mv "$file" config/
    fi
done

echo "✅ Project organization complete!"
echo ""
echo "New structure:"
echo "├── scripts/     # Shell scripts"
echo "├── docs/        # Documentation"
echo "├── assets/      # Media files"
echo "├── tools/       # Python tools"
echo "└── config/      # Configuration files"
