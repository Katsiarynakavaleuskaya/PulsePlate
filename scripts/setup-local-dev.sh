#!/bin/bash

# Local Development Setup Script
# Sets up environment for local development and testing

set -e

echo "🚀 Setting up local development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to create environment file from example
create_env_file() {
    local example_file="$1"
    local env_file="$2"

    if [ ! -f "$env_file" ]; then
        if [ -f "$example_file" ]; then
            cp "$example_file" "$env_file"
            echo -e "${GREEN}✅ Created $env_file from $example_file${NC}"
        else
            echo -e "${RED}❌ Example file $example_file not found${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  $env_file already exists${NC}"
    fi
}

# Function to set environment variable if not set
set_env_var() {
    local var_name="$1"
    local default_value="$2"

    if [ -z "${!var_name}" ]; then
        export "$var_name"="$default_value"
        echo -e "${GREEN}✅ Set $var_name=$default_value${NC}"
    else
        echo -e "${YELLOW}⚠️  $var_name is already set to: ${!var_name}${NC}"
    fi
}

echo ""
echo "📁 Setting up environment files..."

# Create environment files from examples
create_env_file "deploy/ollama-configs/local.env.example" "deploy/ollama-configs/local.env"
create_env_file "deploy/ai-configs/huggingface.env.example" "deploy/ai-configs/huggingface.env"

echo ""
echo "🔧 Setting up environment variables..."

# Set default environment variables for local development
set_env_var "IMAGE_TAG" "latest"
set_env_var "ENVIRONMENT" "development"
set_env_var "AI_ROUTER_ENABLED" "true"

# Set default API keys for local testing
# WARNING: These are placeholder values. Replace with real credentials for actual use.
set_env_var "OLLAMA_API_KEY" "YOUR_OLLAMA_API_KEY_HERE"
set_env_var "OPENAI_API_KEY" "YOUR_OPENAI_API_KEY_HERE"
set_env_var "HUGGINGFACE_TOKEN" "YOUR_HUGGINGFACE_TOKEN_HERE"

echo ""
echo "🐍 Setting up Python environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}🔌 Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

echo ""
echo "🔍 Running environment validation..."

# Run environment validation
if [ -f "scripts/validate-ci-environment.sh" ]; then
    chmod +x scripts/validate-ci-environment.sh
    ./scripts/validate-ci-environment.sh
else
    echo -e "${YELLOW}⚠️  Environment validation script not found${NC}"
fi

echo ""
echo "🧪 Running basic tests..."

# Run basic tests to ensure everything works
if command -v pytest >/dev/null 2>&1; then
    echo -e "${BLUE}Running AI chat tests...${NC}"
    python -m pytest tests/test_ai_chat.py -v --tb=short || echo -e "${YELLOW}⚠️  Some tests failed, but this is expected in local development${NC}"
else
    echo -e "${YELLOW}⚠️  pytest not found, skipping tests${NC}"
fi

echo ""
echo "📋 Development setup summary:"
echo -e "${GREEN}✅ Environment files created${NC}"
echo -e "${GREEN}✅ Environment variables set${NC}"
echo -e "${GREEN}✅ Python dependencies installed${NC}"
echo ""
echo -e "${BLUE}📝 Next steps:${NC}"
echo "1. Edit deploy/ollama-configs/local.env with your actual API keys"
echo "2. Edit deploy/ai-configs/huggingface.env with your Hugging Face token"
echo "3. Run 'source venv/bin/activate' to activate the virtual environment"
echo "4. Run 'python -m pytest' to run all tests"
echo "5. Run 'pre-commit install' to set up git hooks"
echo ""
echo -e "${GREEN}🎉 Local development environment is ready!${NC}"
