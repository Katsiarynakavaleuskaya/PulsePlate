#!/bin/bash
# SwiftFormat Setup Script for PulsePlate

set -euo pipefail
IFS=$'\n\t'

echo "🔧 Setting up SwiftFormat for PulsePlate..."

# Resolve iOS root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$IOS_ROOT" || { echo "❌ Failed to cd to $IOS_ROOT"; exit 1; }

# Check for Package.swift in iOS root
if [[ -f "Package.swift" ]]; then
  echo "📦 Building SwiftFormat from Package.swift..."
  swift build -c release --product swift-format
  export SWIFTFORMAT_PATH="$IOS_ROOT/.build/release/swift-format"
  if [[ ! -f "$SWIFTFORMAT_PATH" ]]; then
    echo "❌ SwiftFormat build failed or executable not found at $SWIFTFORMAT_PATH"
    exit 1
  fi
else
  echo "❌ Package.swift not found at $IOS_ROOT. Ensure you run/setup from the iOS project."
  exit 1
fi

# Create SwiftFormat configuration if it doesn't exist
if [ ! -f ".swiftformat" ]; then
    echo "📝 Creating .swiftformat configuration..."
    # Configuration will be created by the main script
fi

echo "✅ SwiftFormat setup complete!"
echo "Usage: $SWIFTFORMAT_PATH"
