#!/bin/bash
# scripts/validate-ci-environment.sh
# Validate CI/CD environment and secrets

set -e

# Validate ENVIRONMENT variable early
if [ -z "$ENVIRONMENT" ]; then
    echo "::error::ENVIRONMENT variable is not set."
    echo "Please set ENVIRONMENT to one of: local, staging, production"
    exit 1
fi

if [[ ! "$ENVIRONMENT" =~ ^(staging|production|local)$ ]]; then
    echo "::error::ENVIRONMENT must be set to 'staging', 'production', or 'local'. Got: '$ENVIRONMENT'"
    exit 1
fi

# Configuration paths
OLLAMA_DIR="deploy/ollama-configs"
OLLAMA_LOCAL_ENV="${OLLAMA_DIR}/local.env"
OLLAMA_LOCAL_EXAMPLE="${OLLAMA_DIR}/local.env.example"
AI_CONFIGS_DIR="deploy/ai-configs"
HUGGINGFACE_ENV="${AI_CONFIGS_DIR}/huggingface.env"
HUGGINGFACE_EXAMPLE="${AI_CONFIGS_DIR}/huggingface.env.example"
REQUIREMENTS_FILE="requirements.txt"
REQUIREMENTS_DEV_FILE="requirements-dev.txt"

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

# Initialize arrays for tracking warnings and errors
WARNINGS=()
ERRORS=()
# Allow staging deployments to run in "dry mode" without SSH secrets while infrastructure is pending
# This was relaxed during initial staging infrastructure setup. Set to false once staging is stable
# to ensure CI fails early when SSH secrets are missing.
# Temporary allowance tracking:
# - Issue: https://github.com/Katsiarynakavaleuskaya/PulsePlate/issues/42
# - Review date: 2026-01-15
# - Owner/Team: @pulseplate-team
ALLOW_MISSING_STAGING_SSH=${ALLOW_MISSING_STAGING_SSH:-false}

# Check GHCR_READ_TOKEN
if [ -z "$GHCR_READ_TOKEN" ]; then
    echo "::error::GHCR_READ_TOKEN secret is not configured."
    echo "Please add GHCR_READ_TOKEN to your repository secrets."
    ERRORS+=("GHCR_READ_TOKEN secret is not configured.")
    exit 1
fi

# Basic format validation for GHCR_READ_TOKEN
if [ ${#GHCR_READ_TOKEN} -lt 30 ]; then
    echo "::warning::GHCR_READ_TOKEN appears to be too short."
    echo "Please verify this is a valid GitHub Personal Access Token (minimum 30 characters)."
    WARNINGS+=("GHCR_READ_TOKEN appears to be too short.")
fi

echo "✅ GHCR_READ_TOKEN is configured."

# Function to validate environment-specific secrets
validate_required_secret() {
    local secret_name="$1"
    local environment_name="$2"
    local current_env="$3"

    if [ "$current_env" = "$environment_name" ]; then
        if [ -z "${!secret_name}" ]; then
            if [ "$environment_name" = "staging" ] && [ "$ALLOW_MISSING_STAGING_SSH" = "true" ] && [[ "$secret_name" == SSH_* ]]; then
                local warn_msg="$secret_name secret is not configured for $environment_name. Allowing missing SSH secrets during staging infrastructure transition."
                echo "::warning::$warn_msg"
                WARNINGS+=("$warn_msg")
                return
            fi

            local err_msg="$secret_name secret is not configured for $environment_name."
            echo "::error::$err_msg"
            echo "Please add $secret_name to your repository secrets."
            ERRORS+=("$err_msg")
            return
        fi
        echo "✅ $secret_name is configured for $environment_name."
    else
        echo "ℹ️  $secret_name not required for $current_env environment."
    fi
}

# Normalize LLM_ENABLED (accept only explicit "true")
LLM_ENABLED_NORMALIZED="false"
if [[ "${LLM_ENABLED:-false}" == "true" ]]; then
    LLM_ENABLED_NORMALIZED="true"
fi

# Check LLM secrets (only for production if LLM is enabled)
# Only validate if LLM_ENABLED is set to true or if LLM_PROVIDER is configured
if [ "$LLM_ENABLED_NORMALIZED" = "true" ] || [ -n "${LLM_PROVIDER:-}" ]; then
    # Require secrets based on configured provider
    case "${LLM_PROVIDER:-}" in
        openai)
            validate_required_secret "PULSEPLATE_OPENAI" "production" "$ENVIRONMENT"
            ;;
        ollama)
            validate_required_secret "OLLAMA_API_KEY" "production" "$ENVIRONMENT"
            ;;
        perplexity)
            validate_required_secret "PERPLEXITY_API_KEY" "production" "$ENVIRONMENT"
            ;;
        "")
            # LLM enabled but provider not specified - fail with clear configuration error
            if [ "$LLM_ENABLED_NORMALIZED" = "true" ]; then
                err_msg="LLM_ENABLED=true but LLM_PROVIDER is not set. Set LLM_PROVIDER to 'openai', 'ollama', or 'perplexity' (or disable LLM_ENABLED)."
                echo "::error::$err_msg"
                ERRORS+=("$err_msg")
            fi
            ;;
        *)
            # LLM_PROVIDER set but not recognized
            err_msg="Unsupported LLM_PROVIDER='${LLM_PROVIDER}'. Supported values: openai, ollama, perplexity."
            echo "::error::$err_msg"
            ERRORS+=("$err_msg")
            ;;
    esac
else
    echo "ℹ️  LLM secrets not required (LLM_ENABLED is not true and LLM_PROVIDER not set)."
    echo "ℹ️  To enable LLM features, set LLM_ENABLED=true and LLM_PROVIDER=openai|ollama|perplexity."
fi

# Check SSH secrets (required for both staging and production when deploying)
# Only validate if DEPLOY_ENABLED is set to true or if we're explicitly deploying
if [ "${DEPLOY_ENABLED:-false}" = "true" ] || [ -n "${DEPLOY_SSH}" ]; then
    validate_required_secret "SSH_USER" "staging" "$ENVIRONMENT"
    validate_required_secret "SSH_KEY" "staging" "$ENVIRONMENT"
    validate_required_secret "SSH_USER" "production" "$ENVIRONMENT"
    validate_required_secret "SSH_KEY" "production" "$ENVIRONMENT"
else
    echo "ℹ️  SSH secrets not required (DEPLOY_ENABLED is not set to true)."
    echo "ℹ️  To enable deployment, set DEPLOY_ENABLED=true or configure SSH secrets."
fi

# Check environment files exist (only for local development)
if [ "$ENVIRONMENT" = "local" ]; then
    echo ""
    echo "Checking environment files..."

    # Check for existing environment files
    if [ -f "$OLLAMA_LOCAL_ENV" ]; then
        echo "✅ $OLLAMA_LOCAL_ENV exists."
    elif [ -f "$OLLAMA_LOCAL_EXAMPLE" ]; then
        echo "✅ $OLLAMA_LOCAL_EXAMPLE exists."
    else
        echo "⚠️  No Ollama environment file found in $OLLAMA_DIR/"
        echo "Consider creating local.env or local.env.example for local development."
        WARNINGS+=("No Ollama environment file found in $OLLAMA_DIR/")
    fi

    # Check for AI configs directory (optional)
    if [ -d "$AI_CONFIGS_DIR" ]; then
        if [ -f "$HUGGINGFACE_ENV" ]; then
            echo "✅ $HUGGINGFACE_ENV exists."
        elif [ -f "$HUGGINGFACE_EXAMPLE" ]; then
            echo "✅ $HUGGINGFACE_EXAMPLE exists."
        else
            echo "⚠️  No Hugging Face environment file found in $AI_CONFIGS_DIR/"
            WARNINGS+=("No Hugging Face environment file found in $AI_CONFIGS_DIR/")
        fi
    else
        echo "ℹ️  $AI_CONFIGS_DIR/ directory not found (optional for local development)."
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
    WARNINGS+=("Docker is not available.")
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "✅ $REQUIREMENTS_FILE exists."
else
    echo "::error::$REQUIREMENTS_FILE not found."
    exit 1
fi

if [ -f "$REQUIREMENTS_DEV_FILE" ]; then
    echo "✅ $REQUIREMENTS_DEV_FILE exists."
else
    echo "::warning::$REQUIREMENTS_DEV_FILE not found."
    WARNINGS+=("$REQUIREMENTS_DEV_FILE not found.")
fi

echo ""

# Summary of validation results
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo "❌ Environment validation failed with errors:"
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
    exit 1
elif [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "⚠️ Environment validation completed with warnings:"
    for warn in "${WARNINGS[@]}"; do
        echo "  - $warn"
    done
    echo ""
    echo "Please review the warnings above before proceeding."
else
    echo "🎉 Environment validation completed successfully!"
fi

echo ""
echo "Next steps:"
echo "1. Ensure all required secrets are configured in GitHub repository settings"
echo "2. Copy example environment files if needed:"
echo "   cp deploy/ollama-configs/local.env.example deploy/ollama-configs/local.env"
echo "   cp deploy/ai-configs/huggingface.env.example deploy/ai-configs/huggingface.env"
echo "3. Set IMAGE_TAG for local testing: export IMAGE_TAG=\$(git rev-parse --short HEAD)"
