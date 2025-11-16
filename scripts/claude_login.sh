#!/usr/bin/env bash
# 🔐 Quick login/setup script for Claude/Cursor authentication
# Usage: ./scripts/claude_login.sh

set -euo pipefail

echo "🔐 Claude/Cursor Authentication Setup"
echo "======================================"
echo ""

# Check if Python script exists
if [ ! -f "scripts/update_api_key.py" ]; then
    echo "❌ Error: scripts/update_api_key.py not found"
    echo "   Please run this script from the project root"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

echo "📋 This script will help you set up authentication for Claude/Cursor"
echo ""
echo "Options:"
echo "  1. Set up API key interactively (recommended)"
echo "  2. Check current API key status"
echo "  3. Test API key connection"
echo ""

read -p "Select option (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🔑 Setting up API key..."
        echo ""
        echo "You can get your API key from:"
        echo "  - OpenAI: https://platform.openai.com/api-keys"
        echo "  - Anthropic: https://console.anthropic.com/settings/keys"
        echo ""
        read -p "Enter your API key: " -s api_key
        echo ""
        echo ""

        if [ -z "$api_key" ]; then
            echo "❌ Error: API key cannot be empty"
            unset api_key
            exit 1
        fi

        # Use Python script to update API key securely
        if ! python3 scripts/update_api_key.py <<EOF
$api_key
EOF
        then
            echo "❌ Failed to update API key"
            unset api_key
            exit 1
        fi
        unset api_key

        echo ""
        echo "✅ API key updated successfully!"
        echo ""
        echo "Next steps:"
        echo "  1. Restart Cursor if it's running"
        echo "  2. Test connection: ./scripts/claude_login.sh (option 3)"
        ;;

    2)
        echo ""
        echo "📊 Checking API key status..."
        echo ""

        # Check if .env file exists
        if [ -f ~/.cursor/.env ]; then
            echo "✅ Environment file found: ~/.cursor/.env"
            if grep -q "^[[:space:]]*OPENAI_API_KEY=" ~/.cursor/.env; then
                key_line=$(grep "^[[:space:]]*OPENAI_API_KEY=" ~/.cursor/.env | head -1)
                if [[ "$key_line" == *"your_openai_api_key_here"* ]] || [[ "$key_line" == *"encrypted:"* ]]; then
                    if [[ "$key_line" == *"encrypted:"* ]]; then
                        echo "✅ API key is set (encrypted)"
                    else
                        echo "⚠️  API key placeholder detected - please update it"
                    fi
                else
                    echo "✅ API key is set"
                fi
            else
                echo "⚠️  OPENAI_API_KEY not found in .env file"
            fi
        else
            echo "⚠️  Environment file not found: ~/.cursor/.env"
            echo "   Run option 1 to create it"
        fi

        # Check MCP config
        if [ -f ~/.cursor/mcp.json ]; then
            echo "✅ MCP config found: ~/.cursor/mcp.json"
        else
            echo "⚠️  MCP config not found: ~/.cursor/mcp.json"
        fi

        # Check Cursor settings
        if [ -f ~/.cursor/settings.json ]; then
            echo "✅ Cursor settings found: ~/.cursor/settings.json"
        else
            echo "⚠️  Cursor settings not found: ~/.cursor/settings.json"
        fi
        ;;

    3)
        echo ""
        echo "🧪 Testing API key connection..."
        echo ""

        # Try to get API key from environment or file
        # Safely parse .env file without executing arbitrary code
        if [ -f ~/.cursor/.env ]; then
            while IFS= read -r line || [ -n "$line" ]; do
                # Skip blank lines and comments
                line="${line%%#*}"  # Remove comments
                line="${line#"${line%%[![:space:]]*}"}"  # Trim leading whitespace
                line="${line%"${line##*[![:space:]]}"}"  # Trim trailing whitespace
                [ -z "$line" ] && continue

                # Only accept strict KEY=VALUE pattern (keys: A-Z0-9_)
                if [[ "$line" =~ ^([A-Z0-9_]+)=(.*)$ ]]; then
                    key="${BASH_REMATCH[1]}"
                    value="${BASH_REMATCH[2]}"
                    # Strip surrounding quotes from value
                    value="${value#\"}"
                    value="${value%\"}"
                    # Sanitize value: reject control chars, newlines, and command injection chars
                    # Allow only printable ASCII (32-126) excluding dangerous chars: `$();&|<>*?'\" and newlines
                    # Note: In character classes, only ], \, and - need escaping
                    if [[ "$value" =~ [^[:print:]] ]] || [[ "$value" =~ [\`\$\(\)\;\&\|\<\>\*\\\?\'\"] ]]; then
                        echo "⚠️  Warning: Skipping unsafe value for $key (contains control chars or injection chars)" >&2
                        continue
                    fi
                        continue
                    fi
                    # Export sanitized value directly (safer than eval)
                    # POSIX sh and bash support direct export without eval
                    export "$key=$value"
                fi
            done < "$HOME/.cursor/.env"
        fi

        if [ -z "${OPENAI_API_KEY:-}" ]; then
            echo "❌ Error: OPENAI_API_KEY not found"
            echo "   Run option 1 to set it up"
            exit 1
        fi

        # Remove 'encrypted:' prefix if present
        api_key="${OPENAI_API_KEY#encrypted:}"

        # Test OpenAI API (if it's an OpenAI key)
        if [[ "$api_key" == sk-* ]]; then
            echo "Testing OpenAI API connection..."
            # Use curl with timeout flags and separate status code capture
            # Write body to a temporary variable and status code separately
            temp_body=$(mktemp)
            temp_config=$(mktemp)
            # Set restrictive permissions on config file (600 = owner read/write only)
            chmod 600 "$temp_config"
            # Write Authorization header to config file instead of command line
            echo "header = \"Authorization: Bearer $api_key\"" > "$temp_config"
            echo "header = \"Content-Type: application/json\"" >> "$temp_config"
            # Install trap to ensure temp files are cleaned up on exit or signals
            trap 'rm -f "$temp_body" "$temp_config"' EXIT INT TERM
            http_code=$(curl -s -w "%{http_code}" \
                --max-time 10 \
                --connect-timeout 5 \
                --config "$temp_config" \
                -o "$temp_body" \
                https://api.openai.com/v1/models 2>&1) || http_code="000"

            body=$(cat "$temp_body" 2>/dev/null || echo "")
            # Securely delete temp files immediately after use
            rm -f "$temp_body" "$temp_config"
            # Clear trap after manual cleanup to avoid double deletion
            trap - EXIT INT TERM

            if [ "$http_code" = "200" ]; then
                echo "✅ OpenAI API connection successful!"
                # Robust model count using jq if available, otherwise skip count
                if command -v jq &> /dev/null; then
                    # Use jq to properly parse JSON and count models array length
                    model_count=$(echo "$body" | jq -r '.data | length' 2>/dev/null || echo "unknown")
                    if [ "$model_count" != "unknown" ] && [ -n "$model_count" ]; then
                        echo "   Models available: $model_count models"
                    else
                        echo "   Models available: API reachable (count unavailable)"
                    fi
                else
                    # Fallback: just report API is reachable without counting
                    # This avoids fragile grep-based parsing that could miscount
                    echo "   Models available: API reachable (install jq for model count)"
                fi
            else
                echo "❌ OpenAI API connection failed (HTTP $http_code)"
                echo "   Response: $body"
            fi
        elif [[ "$api_key" == claude-* ]] || [[ "$api_key" == sk-ant-* ]]; then
            echo "⚠️  Anthropic API key detected (claude-* or sk-ant-*)"
            echo "   This OpenAI connectivity check does not support Anthropic keys"
            echo "   For testing Anthropic connectivity, see: https://docs.anthropic.com/claude/reference/getting-started-with-the-api"
            echo "   Consider filing an enhancement request to add built-in Anthropic checks to this script"
        else
            echo "⚠️  API key format not recognized (expected sk-...)"
            echo "   This might be an Anthropic key (claude-* or sk-ant-*) or invalid format"
        fi
        ;;

    *)
        echo "❌ Invalid option. Please select 1, 2, or 3"
        exit 1
        ;;
esac

echo ""
echo "✨ Done!"
