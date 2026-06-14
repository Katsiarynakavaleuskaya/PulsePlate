#!/bin/bash
# MCP Setup Script for OpenAI integration with Cursor
set -euo pipefail

echo "🔧 Setting up OpenAI MCP integration in Cursor..."

# Check if uvx is available for the Python-packaged OpenAI MCP server.
if ! command -v uvx &> /dev/null; then
    echo "❌ uvx is not available. Please install uv first."
    echo "Visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✅ uvx is available"

echo "📦 OpenAI MCP server will run through uvx with exact package pin mcp-server-openai==0.1.4"

# Create MCP configuration directory
mkdir -p ~/.cursor

echo "✅ MCP configuration directory is ready"

# Check if .env file already exists
if [ -f ~/.cursor/.env ]; then
    echo "⚠️  Environment file ~/.cursor/.env already exists!"
    echo "🔄 Creating backup and new template..."
    cp ~/.cursor/.env ~/.cursor/.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "💾 Backup created: ~/.cursor/.env.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create environment file template
cat > ~/.cursor/.env << EOF
# OpenAI API Configuration
OPENAI_ADMIN_API_KEY=replace-me

# MCP Configuration
MCP_ENABLED=true
EOF

# Set restrictive permissions
chmod 600 ~/.cursor/.env

echo "📝 Created environment file template at ~/.cursor/.env"
echo "⚠️  Please edit ~/.cursor/.env and add your actual API keys"

echo ""
echo "🎉 MCP setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit ~/.cursor/.env and add your OpenAI admin API key"
echo "2. Restart Cursor"
echo "3. Open Command Palette (Cmd+Shift+P) and run 'MCP: List Tools'"
echo "4. Verify that OpenAI MCP tools are available"
