#!/usr/bin/env bash
# 🔄 Restart Cursor IDE
# Usage: ./scripts/restart_cursor.sh [--grace-period SECONDS] [--reopen-delay SECONDS] [--verbose|--debug] [--help]

set -euo pipefail

# Default values
GRACE_PERIOD=2
REOPEN_DELAY=1
VERBOSE=false
DRY_RUN=false

# Function to print usage and exit
show_help() {
    cat << EOF
🔄 Restart Cursor IDE

Usage:
    ./scripts/restart_cursor.sh [OPTIONS]

Options:
    --grace-period SECONDS    Wait time after graceful quit and after force kill (default: 2)
    --reopen-delay SECONDS    Wait time before reopening Cursor (default: 1)
    --verbose, --debug        Enable verbose/debug output
    --dry-run                 Show what would be executed without actually running commands
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
    if [[ "$value" =~ ^[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to log debug messages when VERBOSE is enabled
debug_log() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Debug: $*"
    fi
}

# Function to close Cursor application gracefully
# Returns 0 if Cursor was closed (or not running), non-zero on error
close_cursor_app() {
    # Check if Cursor is running
    debug_log "Checking if Cursor is running..."
    if [[ "$DRY_RUN" == "true" ]]; then
        debug_log "DRY RUN: Would check and close Cursor"
        echo "🚀 [DRY RUN] Would close Cursor (if running)"
        return 0
    fi

    if pgrep -x "Cursor" > /dev/null; then
        debug_log "Cursor process found via pgrep"
        echo "📋 Closing Cursor..."
        # Try graceful quit first (saves files)
        debug_log "Attempting graceful quit via osascript..."
        osascript -e 'tell application "Cursor" to quit' 2>/dev/null || true

        # Wait a bit for graceful shutdown
        debug_log "Waiting $GRACE_PERIOD seconds for graceful shutdown..."
        sleep "$GRACE_PERIOD"

        # Force kill if still running
        debug_log "Checking if Cursor is still running..."
        if pgrep -x "Cursor" > /dev/null; then
            debug_log "Cursor still running, force killing..."
            echo "⚠️  Force closing Cursor..."
            killall "Cursor" 2>/dev/null || true
            debug_log "Waiting $GRACE_PERIOD seconds after force kill..."
            sleep "$GRACE_PERIOD"
        else
            debug_log "Cursor closed gracefully"
        fi

        echo "✅ Cursor closed"
    else
        debug_log "Cursor process not found via pgrep"
        echo "ℹ️  Cursor is not running"
    fi

    return 0
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
        --verbose|--debug)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "❌ Error: Unknown option: $1"
            echo "   Use --help for usage information"
            exit 1
            ;;
    esac
done

# Debug: Show parsed arguments
debug_log "Parsed arguments:"
debug_log "  GRACE_PERIOD=$GRACE_PERIOD"
debug_log "  REOPEN_DELAY=$REOPEN_DELAY"
debug_log "  VERBOSE=$VERBOSE"
debug_log "  DRY_RUN=$DRY_RUN"

# Check if running on macOS
debug_log "Checking OS..."
debug_log "Detected OS: $(uname -s)"
if [ "$(uname -s)" != "Darwin" ]; then
    echo "❌ Error: This script is macOS-only"
    echo "   Detected OS: $(uname -s)"
    echo "   Please use macOS to run this script"
    exit 1
fi

echo "🔄 Restarting Cursor..."

# Close Cursor application
close_cursor_app

# Wait a moment before reopening
debug_log "Waiting $REOPEN_DELAY seconds before reopening..."
if [[ "$DRY_RUN" != "true" ]]; then
    sleep "$REOPEN_DELAY"
else
    debug_log "DRY RUN: Skipping $REOPEN_DELAY second delay"
fi

# Open Cursor
if [[ "$DRY_RUN" == "true" ]]; then
    echo "🚀 [DRY RUN] Would execute: open -a Cursor"
    echo "✅ [DRY RUN] Cursor restart simulation completed successfully!"
    echo ""
    echo "💡 [DRY RUN] Tips:"
    echo "  - Wait a few seconds for Cursor to fully load"
    echo "  - Check if your API key is working: Cmd+Shift+P → 'MCP: List Tools'"
    echo "  - If MCP tools don't appear, verify ~/.cursor/.env has your API key"
else
    echo "🚀 Opening Cursor..."
    debug_log "Executing 'open -a Cursor'..."
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
fi
echo ""
