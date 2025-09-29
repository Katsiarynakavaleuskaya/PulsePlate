#!/bin/bash
# SwiftLint Setup Script for PulsePlate

set -e

echo "🔧 Setting up SwiftLint for PulsePlate..."

# Check if SwiftLint is available via Package.swift
if [ -f "Package.swift" ]; then
    echo "📦 Building SwiftLint from Package.swift..."
    swift build --product SwiftLint
    SWIFTLINT_PATH=".build/debug/SwiftLint"
else
    echo "❌ Package.swift not found. Please run this from the iOS project root."
    exit 1
fi

# Create SwiftLint configuration if it doesn't exist
if [ ! -f ".swiftlint.yml" ]; then
    echo "📝 Creating .swiftlint.yml configuration..."
    # Configuration will be created by the main script
fi

echo "✅ SwiftLint setup complete!"
echo "Usage: $SWIFTLINT_PATH"
