#!/bin/bash
# SwiftFormat Setup Script for PulsePlate

set -e

echo "🔧 Setting up SwiftFormat for PulsePlate..."

# Check if SwiftFormat is available via Package.swift
if [ -f "Package.swift" ]; then
    echo "📦 Building SwiftFormat from Package.swift..."
    swift build --product SwiftFormat
    SWIFTFORMAT_PATH=".build/debug/SwiftFormat"
else
    echo "❌ Package.swift not found. Please run this from the iOS project root."
    exit 1
fi

# Create SwiftFormat configuration if it doesn't exist
if [ ! -f ".swiftformat" ]; then
    echo "📝 Creating .swiftformat configuration..."
    # Configuration will be created by the main script
fi

echo "✅ SwiftFormat setup complete!"
echo "Usage: $SWIFTFORMAT_PATH"
