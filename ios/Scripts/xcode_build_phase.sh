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
    echo "❌ SwiftLint not found. Run: ./install_swift_tools.sh (or: brew install swiftlint)"
    exit 1
fi

if ! command -v swiftformat &> /dev/null; then
    echo "❌ SwiftFormat not found. Run: ./install_swift_tools.sh (or: brew install swiftformat)"
    exit 1
fi

# Run SwiftFormat first (format code)
echo "🎨 Running SwiftFormat..."

# Enable globstar and nullglob for proper glob pattern handling
shopt -s globstar nullglob

# Find Swift files and format them
swift_files=(PulsePlate/**/*.swift)

if [ ${#swift_files[@]} -eq 0 ]; then
    echo "⚠️  No Swift files found in PulsePlate directory"
    echo "   Skipping SwiftFormat"
else
    echo "📁 Found ${#swift_files[@]} Swift files to format"
    swiftformat --config .swiftformat --inplace -- "${swift_files[@]}"
fi

# Disable globstar and nullglob
shopt -u globstar nullglob

# Run SwiftLint (check code quality)
echo "🔍 Running SwiftLint..."
swiftlint lint --config .swiftlint.yml --reporter xcode

echo "✅ Swift tools completed successfully!"
