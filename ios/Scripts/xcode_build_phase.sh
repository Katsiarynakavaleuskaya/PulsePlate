#!/bin/bash
# Xcode Build Phase Script for SwiftLint + SwiftFormat

# This script should be added as a "Run Script Phase" in Xcode
# Build Phases -> + -> New Run Script Phase

set -e

# Get the project directory
PROJECT_DIR="${SRCROOT}"

# Change to project directory
cd "$PROJECT_DIR"

# Check if we're in debug mode (skip for release builds)
if [ "${CONFIGURATION}" = "Release" ]; then
    echo "⏭️  Skipping Swift tools for Release build"
    exit 0
fi

# Check if tools are available
if ! command -v swiftlint &> /dev/null; then
    echo "❌ SwiftLint not found. Please run: ./install_swift_tools.sh"
    exit 1
fi

if ! command -v swiftformat &> /dev/null; then
    echo "❌ SwiftFormat not found. Please run: ./install_swift_tools.sh"
    exit 1
fi

# Run SwiftFormat first (format code)
echo "🎨 Running SwiftFormat..."
swiftformat --config .swiftformat --inplace PulsePlate/**/*.swift

# Run SwiftLint (check code quality)
echo "🔍 Running SwiftLint..."
swiftlint lint --config .swiftlint.yml --reporter xcode

echo "✅ Swift tools completed successfully!"
