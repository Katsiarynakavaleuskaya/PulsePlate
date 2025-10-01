#!/bin/bash
# SwiftLint Setup Script for PulsePlate

set -euo pipefail
IFS=$'\n\t'

echo "🔧 Setting up SwiftLint for PulsePlate..."

# Resolve iOS root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$IOS_ROOT" || { echo "❌ Failed to cd to $IOS_ROOT"; exit 1; }

# Check for Package.swift in iOS root
if [[ -f "Package.swift" ]]; then
  echo "📦 Building SwiftLint from Package.swift..."
  swift build -c release --product swiftlint
  SWIFTLINT_PATH="$IOS_ROOT/.build/release/swiftlint"
  if [[ ! -f "$SWIFTLINT_PATH" ]]; then
    echo "❌ SwiftLint build failed or executable not found at $SWIFTLINT_PATH"
    exit 1
  fi
  echo "export SWIFTLINT_PATH=\"$SWIFTLINT_PATH\"" > .swiftlint_env.sh
  echo "✅ SwiftLint path exported to .swiftlint_env.sh"
  echo "   Source it with: source .swiftlint_env.sh"
else
  echo "❌ Package.swift not found at $IOS_ROOT. Ensure you run/setup from the iOS project."
  exit 1
fi

# Create SwiftLint configuration if it doesn't exist
if [ ! -f ".swiftlint.yml" ]; then
    echo "⚠️  .swiftlint.yml not found. It should be created separately."
    echo "   See ios/.swiftlint.yml for the configuration template."
fi

echo "✅ SwiftLint setup complete!"
echo "Binary: $SWIFTLINT_PATH"
export SWIFTLINT_PATH
echo ""
echo "💡 Add to PATH for convenience:"
echo "  export PATH=\"$(dirname "$SWIFTLINT_PATH"):\$PATH\""
echo ""
echo "Or source the generated env file:"
echo "  source .swiftlint_env.sh"
