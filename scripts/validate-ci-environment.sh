#!/bin/bash
# scripts/validate-ci-environment.sh
# Validate CI/CD environment and secrets

set -e

echo "🔍 Validating CI/CD environment..."

# Check if we're in CI environment
if [ -n "$CI" ]; then
    echo "✅ Running in CI environment"
else
    echo "⚠️  Not in CI environment - some checks may be skipped"
fi

# Check required secrets for CD workflow
echo ""
echo "Checking required secrets..."

# Check GHCR_READ_TOKEN
if [ -z "$GHCR_READ_TOKEN" ]; then
    echo "::error::GHCR_READ_TOKEN secret is not configured."
    echo "Please add GHCR_READ_TOKEN to your repository secrets."
    exit 1
fi
echo "✅ GHCR_READ_TOKEN is configured."

# Check OLLAMA_API_KEY (only for production)
if [ "$ENVIRONMENT" = "production" ]; then
    if [ -z "$OLLAMA_API_KEY" ]; then
        echo "::error::OLLAMA_API_KEY secret is not configured for production."
        echo "Please add OLLAMA_API_KEY to your repository secrets."
        exit 1
    fi
    echo "✅ OLLAMA_API_KEY is configured for production."
else
    echo "ℹ️  OLLAMA_API_KEY not required for $ENVIRONMENT environment."
fi

# Check PULSEPLATE_OPENAI (only for production)
if [ "$ENVIRONMENT" = "production" ]; then
    if [ -z "$PULSEPLATE_OPENAI" ]; then
        echo "::error::PULSEPLATE_OPENAI secret is not configured for production."
        echo "Please add PULSEPLATE_OPENAI to your repository secrets."
        exit 1
    fi
    echo "✅ PULSEPLATE_OPENAI is configured for production."
else
    echo "ℹ️  PULSEPLATE_OPENAI not required for $ENVIRONMENT environment."
fi

# Check environment files exist (only for local development)
if [ "$ENVIRONMENT" = "local" ]; then
    echo ""
    echo "Checking environment files..."

    # Check for existing environment files
    if [ -f "deploy/ollama-configs/local.env" ]; then
        echo "✅ deploy/ollama-configs/local.env exists."
    elif [ -f "deploy/ollama-configs/local.env.example" ]; then
        echo "✅ deploy/ollama-configs/local.env.example exists."
    else
        echo "⚠️  No Ollama environment file found in deploy/ollama-configs/"
        echo "Consider creating local.env or local.env.example for local development."
    fi

    # Check for AI configs directory (optional)
    if [ -d "deploy/ai-configs" ]; then
        if [ -f "deploy/ai-configs/huggingface.env" ]; then
            echo "✅ deploy/ai-configs/huggingface.env exists."
        elif [ -f "deploy/ai-configs/huggingface.env.example" ]; then
            echo "✅ deploy/ai-configs/huggingface.env.example exists."
        else
            echo "⚠️  No Hugging Face environment file found in deploy/ai-configs/"
        fi
    else
        echo "ℹ️  deploy/ai-configs/ directory not found (optional for local development)."
    fi
else
    echo "ℹ️  Skipping environment file checks for $ENVIRONMENT environment."
fi

# Check Docker is available
echo ""
echo "Checking Docker availability..."
if command -v docker >/dev/null 2>&1; then
    echo "✅ Docker is available."
    docker --version
else
    echo "::warning::Docker is not available. Some tests may be skipped."
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt exists."
else
    echo "::error::requirements.txt not found."
    exit 1
fi

if [ -f "requirements-dev.txt" ]; then
    echo "✅ requirements-dev.txt exists."
else
    echo "::warning::requirements-dev.txt not found."
fi

echo ""
echo "🎉 Environment validation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure all required secrets are configured in GitHub repository settings"
echo "2. Copy example environment files if needed:"
echo "   cp deploy/ollama-configs/local.env.example deploy/ollama-configs/local.env"
echo "   cp deploy/ai-configs/huggingface.env.example deploy/ai-configs/huggingface.env"
echo "3. Set IMAGE_TAG for local testing: export IMAGE_TAG=\$(git rev-parse --short HEAD)"
