#!/bin/bash
# SwiftLint Setup Script for PulsePlate

set -e

echo "🔧 Setting up SwiftLint for PulsePlate..."

# Check if SwiftLint is available via Package.swift
if [ -f "Package.swift" ]; then
    echo "📦 Building SwiftLint from Package.swift..."
    swift build --product SwiftLint
    if [ ! -f ".build/debug/SwiftLint" ]; then
        echo "❌ SwiftLint build failed or executable not found"
        exit 1
    fi
    SWIFTLINT_PATH="$(pwd)/.build/debug/SwiftLint"
    echo "export SWIFTLINT_PATH=\"$SWIFTLINT_PATH\"" > .swiftlint_env.sh
    echo "✅ SwiftLint path exported to .swiftlint_env.sh"
    echo "   Source it with: source .swiftlint_env.sh"
else
    echo "❌ Package.swift not found. Please run this from the iOS project root."
    exit 1
fi

# Create SwiftLint configuration if it doesn't exist
if [ ! -f ".swiftlint.yml" ]; then
    echo "⚠️  .swiftlint.yml not found. It should be created separately."
    echo "   See ios/.swiftlint.yml for the configuration template."
fi

echo "✅ SwiftLint setup complete!"
echo "SwiftLint available at: $SWIFTLINT_PATH"
echo "To use in other scripts: source .swiftlint_env.sh"
