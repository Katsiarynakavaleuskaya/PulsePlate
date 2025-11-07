#!/bin/bash
# 🔄 Restart Cursor IDE
# Usage: ./scripts/restart_cursor.sh

set -euo pipefail

# Check if running on macOS
if [ "$(uname -s)" != "Darwin" ]; then
    echo "❌ Error: This script is macOS-only"
    echo "   Detected OS: $(uname -s)"
    echo "   Please use macOS to run this script"
    exit 1
fi

echo "🔄 Restarting Cursor..."

# Check if Cursor is running
if pgrep -x "Cursor" > /dev/null; then
    echo "📋 Closing Cursor..."
    # Try graceful quit first (saves files)
    osascript -e 'tell application "Cursor" to quit' 2>/dev/null || true

    # Wait a bit for graceful shutdown
    sleep 2

    # Force kill if still running
    if pgrep -x "Cursor" > /dev/null; then
        echo "⚠️  Force closing Cursor..."
        killall "Cursor" 2>/dev/null || true
        sleep 1
    fi

    echo "✅ Cursor closed"
else
    echo "ℹ️  Cursor is not running"
fi

# Wait a moment before reopening
sleep 1

# Open Cursor
echo "🚀 Opening Cursor..."
open -a "Cursor" 2>/dev/null || {
    echo "❌ Error: Could not open Cursor"
    echo "   Please open Cursor manually from Applications"
    exit 1
}

echo "✅ Cursor restarted successfully!"
echo ""
echo "💡 Tips:"
echo "  - Wait a few seconds for Cursor to fully load"
echo "  - Check if your API key is working: Cmd+Shift+P → 'MCP: List Tools'"
echo "  - If MCP tools don't appear, verify ~/.cursor/.env has your API key"
