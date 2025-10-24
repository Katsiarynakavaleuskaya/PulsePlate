# 🚀 Developer Checklist

This checklist helps developers set up the project and avoid common CI/CD issues.

## 📋 Pre-Development Setup

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd PulsePlate

# Run the setup script
./scripts/setup-local-dev.sh
```

### 2. Required Secrets (for CI/CD)
Add these secrets to your GitHub repository settings:

#### Required Secrets:
- `GHCR_READ_TOKEN` - GitHub Container Registry read token
- `OLLAMA_API_KEY` - Ollama API key for AI functionality
- `PULSEPLATE_OPENAI` - OpenAI API key for AI functionality

#### Optional Secrets:
- `CODECOV_TOKEN` - Code coverage reporting (optional)

### 3. Environment Files
```bash
# Copy environment files from examples
cp deploy/ollama-configs/local.env.example deploy/ollama-configs/local.env
cp deploy/ai-configs/huggingface.env.example deploy/ai-configs/huggingface.env

# Edit with your actual API keys
nano deploy/ollama-configs/local.env
nano deploy/ai-configs/huggingface.env
```

## 🔧 Development Workflow

### 1. Before Making Changes
```bash
# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install
```

### 2. Making Changes
```bash
# Make your changes
# ...

# Run tests locally
python -m pytest tests/ -v

# Run linting
python -m black .
python -m ruff check .
python -m mypy .

# Run security checks
python -m bandit -r app/ core/
python -m pip-audit --requirement requirements.txt
```

### 3. Before Committing
```bash
# Validate environment
./scripts/validate-ci-environment.sh

# Run all checks
pre-commit run --all-files

# Commit your changes
git add .
git commit -m "feat: your changes"
```

## 🐳 Docker Development

### 1. Local Docker Testing
```bash
# Set environment variables
export IMAGE_TAG=latest
export ENVIRONMENT=development

# Build and run locally
docker-compose up --build
```

### 2. Staging Environment
```bash
# Set staging environment
export ENVIRONMENT=staging
export AI_ROUTER_ENABLED=false

# Run staging tests
docker-compose -f deploy/docker-compose.staging.yaml up
```

## 🚨 Common Issues & Solutions

### Issue: CI/CD fails with "secret not configured"
**Solution:**
1. Check that all required secrets are set in GitHub repository settings
2. Run `./scripts/validate-ci-environment.sh` locally to verify setup
3. Ensure secrets are not empty strings

### Issue: Tests fail with "AttributeError: 'dict' object has no attribute 'response'"
**Solution:**
- This is fixed in the latest version
- Ensure you're using `AIResponse` objects in tests, not dictionaries

### Issue: Security checks fail in nightly workflow
**Solution:**
- The nightly workflow now runs in "informational mode"
- Security issues are reported as warnings, not errors
- Fix actual security issues when found

### Issue: Docker build fails with missing secrets
**Solution:**
1. Ensure environment files exist: `deploy/ollama-configs/local.env`
2. Set `ENVIRONMENT=development` for local testing
3. Use the setup script: `./scripts/setup-local-dev.sh`

### Issue: OWASP ZAP scan fails
**Solution:**
1. Ensure the application starts successfully before scanning
2. Check that health endpoint is accessible: `curl http://localhost:8000/health`
3. Verify all required dependencies are installed

## 📊 CI/CD Pipeline Status

### Workflows that should pass:
- ✅ **CI** - Main continuous integration
- ✅ **Security** - Security scanning
- ✅ **Build** - Docker image building
- ✅ **Nightly** - Security monitoring (informational)

### Workflows that require secrets:
- 🔐 **CD** - Continuous deployment (requires all secrets)
- 🔐 **Docker Image** - Image publishing (requires GHCR_READ_TOKEN)

## 🛠️ Troubleshooting

### Validate Your Setup
```bash
# Run comprehensive validation
./scripts/validate-ci-environment.sh

# Check specific components
python -c "import bandit, pip_audit, ruff, mypy; print('All tools installed')"
docker --version
curl --version
```

### Debug CI/CD Issues
1. Check the "Actions" tab in GitHub
2. Look for specific error messages
3. Verify secrets are set correctly
4. Run the same commands locally

### Get Help
- Check the logs in GitHub Actions
- Run validation scripts locally
- Review this checklist
- Check the main README.md for additional setup instructions

## 📝 Quick Commands Reference

```bash
# Setup everything
./scripts/setup-local-dev.sh

# Validate environment
./scripts/validate-ci-environment.sh

# Run tests
python -m pytest tests/ -v

# Run all quality checks
pre-commit run --all-files

# Build Docker image
docker build -t pulseplate:latest .

# Run with Docker Compose
docker-compose up --build
```

---

**Remember:** Always run the validation script before pushing changes to avoid CI/CD failures!
