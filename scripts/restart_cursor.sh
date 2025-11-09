#!/bin/bash
# 🔄 Restart Cursor IDE
# Usage: ./scripts/restart_cursor.sh [--grace-period SECONDS] [--reopen-delay SECONDS] [--help]

set -euo pipefail

# Default values
GRACE_PERIOD=2
REOPEN_DELAY=1

# Function to print usage and exit
show_help() {
    cat << EOF
🔄 Restart Cursor IDE

Usage:
    ./scripts/restart_cursor.sh [OPTIONS]

Options:
    --grace-period SECONDS    Wait time after graceful quit and after force kill (default: 2)
    --reopen-delay SECONDS    Wait time before reopening Cursor (default: 1)
    --help                    Show this help message and exit

Examples:
    # Use default timings (2s grace, 1s reopen delay)
    ./scripts/restart_cursor.sh

    # Custom grace period of 3 seconds
    ./scripts/restart_cursor.sh --grace-period 3

    # Custom reopen delay of 2 seconds
    ./scripts/restart_cursor.sh --reopen-delay 2

    # Both custom values
    ./scripts/restart_cursor.sh --grace-period 5 --reopen-delay 3

EOF
    exit 0
}

# Function to validate numeric input
is_numeric() {
    local value="$1"
    if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        return 0
    else
        return 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            ;;
        --grace-period)
            if [[ -z "${2:-}" ]]; then
                echo "❌ Error: --grace-period requires a value"
                exit 1
            fi
            if ! is_numeric "$2"; then
                echo "❌ Error: --grace-period must be a numeric value, got: $2"
                exit 1
            fi
            GRACE_PERIOD="$2"
            shift 2
            ;;
        --reopen-delay)
            if [[ -z "${2:-}" ]]; then
                echo "❌ Error: --reopen-delay requires a value"
                exit 1
            fi
            if ! is_numeric "$2"; then
                echo "❌ Error: --reopen-delay must be a numeric value, got: $2"
                exit 1
            fi
            REOPEN_DELAY="$2"
            shift 2
            ;;
        *)
            echo "❌ Error: Unknown option: $1"
            echo "   Use --help for usage information"
            exit 1
            ;;
    esac
done

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
    sleep "$GRACE_PERIOD"

    # Force kill if still running
    if pgrep -x "Cursor" > /dev/null; then
        echo "⚠️  Force closing Cursor..."
        killall "Cursor" 2>/dev/null || true
        sleep "$GRACE_PERIOD"
    fi

    echo "✅ Cursor closed"
else
    echo "ℹ️  Cursor is not running"
fi

# Wait a moment before reopening
sleep "$REOPEN_DELAY"

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
