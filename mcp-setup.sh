#!/bin/bash
# MCP Setup Script for ChatGPT Integration with Cursor
set -euo pipefail

echo "🔧 Setting up MCP integration for ChatGPT in Cursor..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not available. Please install npm."
    exit 1
fi

echo "✅ Node.js and npm are available"

# Install MCP servers
echo "📦 Installing MCP servers..."

# Install ChatGPT MCP server
echo "Installing ChatGPT MCP server..."
npm install -g mcp-server-chatgpt

# Install OpenAI MCP server
echo "Installing OpenAI MCP server..."
npm install -g mcp-server-openai

# Create MCP configuration directory
mkdir -p ~/.cursor

echo "✅ MCP servers installed successfully"

# Check if .env file already exists
if [ -f ~/.cursor/.env ]; then
    echo "⚠️  Environment file ~/.cursor/.env already exists!"
    echo "📋 Current content:"
    cat ~/.cursor/.env
    echo ""
    echo "🔄 Creating backup and new template..."
    cp ~/.cursor/.env ~/.cursor/.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "💾 Backup created: ~/.cursor/.env.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create environment file template
cat > ~/.cursor/.env << EOF
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
CHATGPT_API_KEY=your_openai_api_key_here

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
echo "1. Edit ~/.cursor/.env and add your OpenAI API key"
echo "2. Restart Cursor"
echo "3. Open Command Palette (Cmd+Shift+P) and run 'MCP: List Tools'"
echo "4. Verify that ChatGPT tools are available"
